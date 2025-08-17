"""
Główny moduł do wykrywania śmiesznych fragmentów w transkryptach Sejmu
"""
from typing import List
from models.funny_fragment import FunnyFragment
from processors.text_processor import TextProcessor
from processors.pdf_processor import PDFProcessor
from analyzers.fragment_analyzer import FragmentAnalyzer


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
        self.context_before = context_before
        self.context_after = context_after
        self.debug = debug

        # Inicjalizujemy komponenty
        self.text_processor = TextProcessor(debug=debug)
        self.pdf_processor = PDFProcessor(debug=debug)
        self.fragment_analyzer = FragmentAnalyzer(debug=debug)

        if self.debug:
            print(f"DEBUG: Inicjalizowano FragmentDetector z kontekstem: {context_before}/{context_after}")

    def find_funny_fragments(self, text: str, min_confidence: float = 0.3) -> List[FunnyFragment]:
        """
        Znajduje śmieszne fragmenty w tekście

        Args:
            text: Tekst do przeanalizowania
            min_confidence: Minimalny próg pewności

        Returns:
            Lista znalezionych fragmentów
        """
        # Czyścimy tekst
        cleaned_text = self.text_processor.clean_text(text)
        words = cleaned_text.split()

        fragments = []
        existing_texts = []

        if self.debug:
            print(f"DEBUG: Szukam w tekście o długości {len(words)} słów")

        # Wyciągamy informacje o posiedzeniu raz na początku
        meeting_info = self.text_processor.extract_meeting_info(text)

        # Szukamy słów kluczowych
        for i, word in enumerate(words):
            # Sprawdzamy czy słowo zawiera któreś ze słów kluczowych
            found_keywords = self.fragment_analyzer.find_keywords_in_word(word)

            if found_keywords:
                # Wyciągamy fragment z kontekstem
                fragment_text = self.text_processor.extract_context(
                    words, i, self.context_before, self.context_after
                )

                if self.debug:
                    print(f"DEBUG: Fragment zawierający '{found_keywords}': {fragment_text[:100]}...")

                # Weryfikujemy słowa kluczowe w fragmencie
                verified_keywords = self.fragment_analyzer.verify_keywords_in_fragment(
                    fragment_text, found_keywords
                )

                if not verified_keywords:
                    if self.debug:
                        print("DEBUG: Brak zweryfikowanych słów kluczowych, pomijam fragment")
                    continue

                # Obliczamy pewność
                confidence = self.fragment_analyzer.calculate_confidence(
                    fragment_text, verified_keywords
                )

                # Znajdujemy pozycję w oryginalnym tekście
                position = self.text_processor.find_text_position(text, fragment_text, word)

                # Znajdujemy mówcę
                speaker = self.text_processor.find_speaker(text, position if position != -1 else 0)

                # Sprawdzamy czy fragment powinien być pominięty
                should_skip, skip_reason = self.fragment_analyzer.should_skip_fragment(
                    speaker, confidence, min_confidence
                )

                if should_skip:
                    if self.debug:
                        print(f"DEBUG: Pomijam fragment: {skip_reason}")
                    continue

                # Sprawdzamy duplikaty
                if self.fragment_analyzer.is_duplicate(fragment_text, existing_texts):
                    if self.debug:
                        print("DEBUG: Fragment jest duplikatem, pomijam")
                    continue

                # Tworzymy fragment
                fragment = FunnyFragment(
                    text=fragment_text,
                    speaker=speaker,
                    meeting_info=meeting_info,
                    keywords_found=verified_keywords,
                    position_in_text=position,
                    context_before=self.context_before,
                    context_after=self.context_after,
                    confidence_score=confidence
                )

                fragments.append(fragment)
                existing_texts.append(fragment_text)

                if self.debug:
                    print(f"DEBUG: Dodano fragment #{len(fragments)}")

        if self.debug:
            print(f"DEBUG: Znaleziono łącznie {len(fragments)} fragmentów")

        # Sortujemy według pewności (najlepsze pierwsze)
        fragments.sort(key=lambda x: x.confidence_score, reverse=True)

        return fragments

    def process_pdf(self, pdf_path: str, min_confidence: float = 0.3, max_fragments: int = 50) -> List[FunnyFragment]:
        """
        Główna funkcja przetwarzająca PDF

        Args:
            pdf_path: Ścieżka do pliku PDF
            min_confidence: Minimalny próg pewności
            max_fragments: Maksymalna liczba zwracanych fragmentów

        Returns:
            Lista znalezionych fragmentów
        """
        if self.debug:
            print(f"DEBUG: Rozpoczynam przetwarzanie pliku: {pdf_path}")

        # Sprawdzamy czy plik jest prawidłowy
        is_valid, validation_message = self.pdf_processor.validate_pdf_file(pdf_path)
        if not is_valid:
            print(f"Błąd walidacji pliku: {validation_message}")
            return []

        # Wyciągamy tekst
        text = self.pdf_processor.extract_text_from_pdf(pdf_path)
        if not text:
            print("Nie udało się wyciągnąć tekstu z PDF")
            return []

        if self.debug:
            print(f"DEBUG: Wyciągnięto {len(text)} znaków tekstu")

        # Znajdujemy śmieszne fragmenty
        all_fragments = self.find_funny_fragments(text, min_confidence)

        # Ograniczamy liczbę wyników i pokazujemy statystyki
        fragments = all_fragments[:max_fragments]

        if all_fragments:
            avg_confidence = sum(f.confidence_score for f in all_fragments) / len(all_fragments)
            print(f"Znaleziono {len(all_fragments)} fragmentów, zwracam {len(fragments)} najlepszych")
            print(f"Średnia pewność: {avg_confidence:.2f}")
            print(f"Najlepsza pewność: {all_fragments[0].confidence_score:.2f}")
            if len(all_fragments) > 1:
                print(f"Najgorsza pewność: {all_fragments[-1].confidence_score:.2f}")
        else:
            print("Nie znaleziono żadnych fragmentów spełniających kryteria")

        return fragments