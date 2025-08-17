"""
Główny moduł do wykrywania śmiesznych fragmentów w transkryptach Sejmu
"""
from typing import List, Optional, Tuple

from analyzers.fragment_analyzer import FragmentAnalyzer
from models.funny_fragment import FunnyFragment
from processors.pdf_processor import PDFProcessor
from processors.text_processor import TextProcessor


class FragmentDetector:
    """Główna klasa do wykrywania śmiesznych fragmentów"""

    def __init__(self, context_before: int = 50, context_after: int = 49, debug: bool = False):
        """
        Inicjalizacja detektora

        Args:
            context_before: Liczba słów przed słowem kluczowym
            context_after: Liczba słów po słowie kluczowym
            debug: Tryb debugowania
        """
        # Walidacja parametrów
        if not isinstance(context_before, int) or not isinstance(context_after, int):
            raise TypeError("Parametry kontekstu muszą być liczbami całkowitymi")

        if context_before < 5 or context_after < 5:
            raise ValueError("Kontekst musi wynosić co najmniej 5 słów z każdej strony")

        if context_before > 200 or context_after > 200:
            raise ValueError("Kontekst nie może przekraczać 200 słów z każdej strony")

        self.context_before = context_before
        self.context_after = context_after
        self.debug = debug

        # Inicjalizujemy komponenty
        self.text_processor = TextProcessor(debug=debug)
        self.pdf_processor = PDFProcessor(debug=debug)
        self.fragment_analyzer = FragmentAnalyzer(debug=debug)

        # Statystyki wydajności
        self.stats = {
            'processed_texts': 0,
            'found_keywords': 0,
            'created_fragments': 0,
            'skipped_duplicates': 0,
            'skipped_low_confidence': 0
        }

        if self.debug:
            print(f"DEBUG: Inicjalizowano FragmentDetector z kontekstem: {context_before}/{context_after}")

    def find_funny_fragments(self, text: str, min_confidence: float = 0.3) -> List[FunnyFragment]:
        """
        Znajduje śmieszne fragmenty w tekście - ulepszona wersja

        Args:
            text: Tekst do przeanalizowania
            min_confidence: Minimalny próg pewności (0.1-0.95)

        Returns:
            Lista znalezionych fragmentów
        """
        # Walidacja parametrów
        if not text or not text.strip():
            if self.debug:
                print("DEBUG: Pusty tekst wejściowy")
            return []

        if not 0.1 <= min_confidence <= 0.95:
            raise ValueError("min_confidence musi być w zakresie 0.1-0.95")

        # Czyścimy tekst
        cleaned_text = self.text_processor.clean_text(text)
        if not cleaned_text:
            if self.debug:
                print("DEBUG: Tekst pusty po czyszczeniu")
            return []

        # Używamy nowej metody wyszukiwania słów kluczowych
        keyword_positions = self.fragment_analyzer.find_keywords_in_text(cleaned_text)

        if not keyword_positions:
            if self.debug:
                print("DEBUG: Nie znaleziono słów kluczowych w tekście")
            return []

        self.stats['found_keywords'] = len(keyword_positions)

        fragments = []
        existing_texts = []

        if self.debug:
            print(f"DEBUG: Znaleziono {len(keyword_positions)} słów kluczowych w tekście")

        # Wyciągamy informacje o posiedzeniu raz na początku
        meeting_info = self.text_processor.extract_meeting_info(text)

        # Grupujemy blisko siebie występujące słowa kluczowe
        grouped_keywords = self._group_nearby_keywords(keyword_positions, cleaned_text)

        if self.debug:
            print(f"DEBUG: Pogrupowano w {len(grouped_keywords)} fragmentów")

        # Przetwarzamy każdą grupę słów kluczowych
        for group_center, keywords_in_group in grouped_keywords:
            try:
                fragment_result = self._process_keyword_group(
                    cleaned_text, text, group_center, keywords_in_group,
                    meeting_info, min_confidence, existing_texts
                )

                if fragment_result:
                    fragments.append(fragment_result)
                    existing_texts.append(fragment_result.text)
                    self.stats['created_fragments'] += 1

                    if self.debug:
                        print(f"DEBUG: Utworzono fragment #{len(fragments)}")

            except Exception as e:
                if self.debug:
                    print(f"DEBUG: Błąd podczas przetwarzania grupy: {e}")
                continue

        # Sortujemy według pewności (najlepsze pierwsze)
        fragments.sort(key=lambda x: x.confidence_score, reverse=True)

        if self.debug:
            print(f"DEBUG: Znaleziono łącznie {len(fragments)} fragmentów")
            self._print_processing_stats()

        return fragments

    def _group_nearby_keywords(self, keyword_positions: List[Tuple[str, int]],
                               text: str, max_distance: int = 200) -> List[Tuple[int, List[str]]]:
        """
        Grupuje blisko siebie występujące słowa kluczowe

        Args:
            keyword_positions: Lista (słowo, pozycja)
            text: Tekst źródłowy
            max_distance: Maksymalna odległość między słowami w grupie

        Returns:
            Lista (pozycja_środkowa, lista_słów_kluczowych)
        """
        if not keyword_positions:
            return []

        groups = []
        current_group = [keyword_positions[0]]

        for i in range(1, len(keyword_positions)):
            current_keyword, current_pos = keyword_positions[i]
            last_keyword, last_pos = current_group[-1]

            # Jeśli słowa są blisko siebie, dodajemy do obecnej grupy
            if current_pos - last_pos <= max_distance:
                current_group.append(keyword_positions[i])
            else:
                # Zamykamy obecną grupę i zaczynamy nową
                groups.append(self._finalize_group(current_group, text))
                current_group = [keyword_positions[i]]

        # Dodajemy ostatnią grupę
        if current_group:
            groups.append(self._finalize_group(current_group, text))

        return groups

    def _finalize_group(self, group: List[Tuple[str, int]], text: str) -> Tuple[int, List[str]]:
        """
        Finalizuje grupę słów kluczowych

        Args:
            group: Lista (słowo, pozycja)
            text: Tekst źródłowy

        Returns:
            (pozycja_środkowa, unikalne_słowa)
        """
        positions = [pos for _, pos in group]
        keywords = [keyword for keyword, _ in group]

        # Pozycja środkowa grupy
        center_position = sum(positions) // len(positions)

        # Unikalne słowa kluczowe
        unique_keywords = list(set(keywords))

        return center_position, unique_keywords

    def _process_keyword_group(self, cleaned_text: str, original_text: str,
                               center_position: int, keywords: List[str],
                               meeting_info: str, min_confidence: float,
                               existing_texts: List[str]) -> Optional[FunnyFragment]:
        """
        Przetwarza grupę słów kluczowych w fragment

        Returns:
            FunnyFragment lub None jeśli fragment odrzucony
        """
        # Konwertujemy pozycję z tekstu oczyszczonego na słowa
        words = cleaned_text.split()
        char_to_word_pos = self._build_char_to_word_mapping(cleaned_text)

        # Znajdujemy pozycję słowa odpowiadającą pozycji znaku
        word_position = char_to_word_pos.get(center_position, len(words) // 2)

        # Wyciągamy fragment z kontekstem
        fragment_text = self.text_processor.extract_context(
            words, word_position, self.context_before, self.context_after
        )

        if not fragment_text or len(fragment_text.strip()) < 20:
            if self.debug:
                print("DEBUG: Fragment za krótki, pomijam")
            return None

        # Weryfikujemy słowa kluczowe w fragmencie
        verified_keywords = self.fragment_analyzer.verify_keywords_in_fragment(
            fragment_text, keywords
        )

        if not verified_keywords:
            if self.debug:
                print("DEBUG: Brak zweryfikowanych słów kluczowych")
            return None

        # Obliczamy pewność
        confidence = self.fragment_analyzer.calculate_confidence(
            fragment_text, verified_keywords
        )

        # Znajdujemy pozycję w oryginalnym tekście
        original_position = self.text_processor.find_text_position(
            original_text, fragment_text, verified_keywords[0]
        )

        # Znajdujemy mówcę
        speaker = self.text_processor.find_speaker(
            original_text, original_position if original_position != -1 else 0
        )

        # Sprawdzamy czy fragment powinien być pominięty
        should_skip, skip_reason = self.fragment_analyzer.should_skip_fragment(
            speaker, confidence, min_confidence, fragment_text
        )

        if should_skip:
            if self.debug:
                print(f"DEBUG: Pomijam fragment: {skip_reason}")
            if "pewność za niska" in skip_reason.lower():
                self.stats['skipped_low_confidence'] += 1
            return None

        # Sprawdzamy duplikaty
        if self.fragment_analyzer.is_duplicate(fragment_text, existing_texts):
            if self.debug:
                print("DEBUG: Fragment jest duplikatem")
            self.stats['skipped_duplicates'] += 1
            return None

        # Tworzymy fragment
        fragment = FunnyFragment(
            text=fragment_text,
            speaker=speaker,
            meeting_info=meeting_info,
            keywords_found=verified_keywords,
            position_in_text=original_position,
            context_before=self.context_before,
            context_after=self.context_after,
            confidence_score=confidence
        )

        return fragment

    def _build_char_to_word_mapping(self, text: str) -> dict:
        """
        Buduje mapowanie pozycji znaków na pozycje słów

        Args:
            text: Tekst źródłowy

        Returns:
            Słownik {pozycja_znaku: pozycja_słowa}
        """
        mapping = {}
        words = text.split()
        char_pos = 0

        for word_idx, word in enumerate(words):
            # Znajdujemy pozycję słowa w tekście
            word_start = text.find(word, char_pos)
            if word_start != -1:
                # Mapujemy zakres znaków słowa na jego indeks
                for i in range(word_start, word_start + len(word)):
                    mapping[i] = word_idx
                char_pos = word_start + len(word)

        return mapping

    def process_pdf(self, pdf_path: str, min_confidence: float = 0.3,
                    max_fragments: int = 50) -> List[FunnyFragment]:
        """
        Główna funkcja przetwarzająca PDF - ulepszona wersja

        Args:
            pdf_path: Ścieżka do pliku PDF
            min_confidence: Minimalny próg pewności (0.1-0.95)
            max_fragments: Maksymalna liczba zwracanych fragmentów

        Returns:
            Lista znalezionych fragmentów
        """
        # Walidacja parametrów
        if not pdf_path or not isinstance(pdf_path, str):
            raise ValueError("Ścieżka PDF musi być niepustym stringiem")

        if not 0.1 <= min_confidence <= 0.95:
            raise ValueError("min_confidence musi być w zakresie 0.1-0.95")

        if not isinstance(max_fragments, int) or max_fragments < 1:
            raise ValueError("max_fragments musi być dodatnią liczbą całkowitą")

        # Resetujemy statystyki
        self.stats = {k: 0 for k in self.stats}
        self.stats['processed_texts'] = 1

        if self.debug:
            print(f"DEBUG: Rozpoczynam przetwarzanie pliku: {pdf_path}")
            print(f"DEBUG: Parametry - confidence: {min_confidence}, max: {max_fragments}")

        # Sprawdzamy czy plik jest prawidłowy
        is_valid, validation_message = self.pdf_processor.validate_pdf_file(pdf_path)
        if not is_valid:
            error_msg = f"Błąd walidacji pliku: {validation_message}"
            print(error_msg)
            if self.debug:
                print(f"DEBUG ERROR: {error_msg}")
            return []

        # Wyciągamy tekst
        text = self.pdf_processor.extract_text_from_pdf(pdf_path)
        if not text:
            error_msg = "Nie udało się wyciągnąć tekstu z PDF"
            print(error_msg)
            if self.debug:
                print(f"DEBUG ERROR: {error_msg}")
            return []

        if self.debug:
            print(f"DEBUG: Wyciągnięto {len(text)} znaków tekstu")

        try:
            # Znajdujemy śmieszne fragmenty
            all_fragments = self.find_funny_fragments(text, min_confidence)

            if not all_fragments:
                print("Nie znaleziono żadnych fragmentów spełniających kryteria")
                self._suggest_parameter_adjustments(min_confidence, text)
                return []

            # Ograniczamy liczbę wyników
            fragments = all_fragments[:max_fragments]

            # Pokazujemy statystyki
            self._print_results_summary(all_fragments, fragments, min_confidence)

            return fragments

        except Exception as e:
            error_msg = f"Błąd podczas przetwarzania: {e}"
            print(error_msg)
            if self.debug:
                print(f"DEBUG ERROR: {error_msg}")
                import traceback
                traceback.print_exc()
            return []

    def _suggest_parameter_adjustments(self, current_min_confidence: float, text: str):
        """Sugeruje zmiany parametrów jeśli nie znaleziono fragmentów"""
        print("\nSugestie zmian parametrów:")

        if current_min_confidence > 0.3:
            print(f"- Obniż min_confidence z {current_min_confidence} do {max(0.2, current_min_confidence - 0.2)}")

        # Sprawdzamy czy w ogóle są słowa kluczowe
        keywords_found = self.fragment_analyzer.find_keywords_in_text(text.lower())
        if keywords_found:
            print(f"- W tekście znaleziono {len(keywords_found)} słów kluczowych")
            print("- Spróbuj zwiększyć context_before/context_after")
        else:
            print("- Nie znaleziono słów kluczowych w tekście")
            print("- Sprawdź czy plik zawiera właściwy transkrypt")

    def _print_results_summary(self, all_fragments: List[FunnyFragment],
                               returned_fragments: List[FunnyFragment],
                               min_confidence: float):
        """Wyświetla podsumowanie wyników"""
        if all_fragments:
            avg_confidence = sum(f.confidence_score for f in all_fragments) / len(all_fragments)
            print(f"\n=== PODSUMOWANIE WYNIKÓW ===")
            print(f"Znaleziono: {len(all_fragments)} fragmentów, zwracam: {len(returned_fragments)}")
            print(f"Średnia pewność: {avg_confidence:.3f}")
            print(f"Najlepsza pewność: {all_fragments[0].confidence_score:.3f}")

            if len(all_fragments) > 1:
                print(f"Najgorsza pewność: {all_fragments[-1].confidence_score:.3f}")

            # Podsumowanie jakości
            high_quality = len([f for f in all_fragments if f.confidence_score >= 0.7])
            medium_quality = len([f for f in all_fragments if 0.4 <= f.confidence_score < 0.7])
            low_quality = len([f for f in all_fragments if f.confidence_score < 0.4])

            print(f"Jakość fragmentów - wysoka (≥0.7): {high_quality}, "
                  f"średnia (0.4-0.7): {medium_quality}, niska (<0.4): {low_quality}")

    def _print_processing_stats(self):
        """Wyświetla statystyki przetwarzania"""
        print(f"\nDEBUG - Statystyki przetwarzania:")
        print(f"  Znalezione słowa kluczowe: {self.stats['found_keywords']}")
        print(f"  Utworzone fragmenty: {self.stats['created_fragments']}")
        print(f"  Pominięte duplikaty: {self.stats['skipped_duplicates']}")
        print(f"  Pominięte (niska pewność): {self.stats['skipped_low_confidence']}")

    def get_processing_stats(self) -> dict:
        """Zwraca statystyki ostatniego przetwarzania"""
        return self.stats.copy()

    def reset_stats(self):
        """Resetuje statystyki przetwarzania"""
        self.stats = {k: 0 for k in self.stats}
