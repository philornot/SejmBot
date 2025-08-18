"""
Główny moduł do wykrywania śmiesznych fragmentów w transkryptach Sejmu
"""
import os
from pathlib import Path
from typing import List, Optional, Tuple, Dict

from SejmBotDetektor.analyzers.fragment_analyzer import FragmentAnalyzer
from SejmBotDetektor.models.funny_fragment import FunnyFragment
from SejmBotDetektor.processors.pdf_processor import PDFProcessor
from SejmBotDetektor.processors.text_processor import TextProcessor
from SejmBotDetektor.logging.logger import get_module_logger, logger, Colors


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
        self.logger = get_module_logger("FragmentDetector")

        # Walidacja parametrów
        if not isinstance(context_before, int) or not isinstance(context_after, int):
            raise TypeError("Parametry kontekstu muszą być liczbami całkowitymi")

        if context_before < 5 or context_after < 5:
            error_msg = "Kontekst musi wynosić co najmniej 5 słów z każdej strony"
            self.logger.error(error_msg)
            raise ValueError(error_msg)

        if context_before > 200 or context_after > 200:
            error_msg = "Kontekst nie może przekraczać 200 słów z każdej strony"
            self.logger.error(error_msg)
            raise ValueError(error_msg)

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
            'skipped_low_confidence': 0,
            'processed_files': 0,
            'failed_files': 0
        }

        if self.debug:
            self.logger.debug(f"Inicjalizowano z kontekstem: {context_before}/{context_after}")

    def find_funny_fragments(self, text: str, min_confidence: float = 0.3, source_file: str = None) -> List[
        FunnyFragment]:
        """
        Znajduje śmieszne fragmenty w tekście - ulepszona wersja

        Args:
            text: Tekst do przeanalizowania
            min_confidence: Minimalny próg pewności (0.1-0.95)
            source_file: Nazwa pliku źródłowego (dla debugowania)

        Returns:
            Lista znalezionych fragmentów
        """
        # Walidacja parametrów
        if not text or not text.strip():
            if self.debug:
                self.logger.debug(f"Pusty tekst wejściowy {f'w pliku {source_file}' if source_file else ''}")
            return []

        if not 0.1 <= min_confidence <= 0.95:
            raise ValueError("min_confidence musi być w zakresie 0.1-0.95")

        # Czyścimy tekst
        cleaned_text = self.text_processor.clean_text(text)
        if not cleaned_text:
            if self.debug:
                self.logger.debug(f"Tekst pusty po czyszczeniu {f'w pliku {source_file}' if source_file else ''}")
            return []

        # Używamy nowej metody wyszukiwania słów kluczowych
        keyword_positions = self.fragment_analyzer.find_keywords_in_text(cleaned_text)

        if not keyword_positions:
            if self.debug:
                self.logger.debug(
                    f"Nie znaleziono słów kluczowych w tekście {f'w pliku {source_file}' if source_file else ''}")
            return []

        self.stats['found_keywords'] += len(keyword_positions)

        fragments = []
        existing_texts = []

        if self.debug:
            self.logger.debug(
                f"Znaleziono {len(keyword_positions)} słów kluczowych w tekście {f'({source_file})' if source_file else ''}")

        # Wyciągamy informacje o posiedzeniu raz na początku
        meeting_info = self.text_processor.extract_meeting_info(text)

        # Dodajemy informację o pliku źródłowym do meeting_info
        if source_file:
            meeting_info += f" | Plik: {source_file}"

        # Grupujemy blisko siebie występujące słowa kluczowe
        grouped_keywords = self._group_nearby_keywords(keyword_positions, cleaned_text)

        if self.debug:
            self.logger.debug(f"Pogrupowano w {len(grouped_keywords)} fragmentów")

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
                        self.logger.debug(f"Utworzono fragment #{len(fragments)}")

            except Exception as e:
                self.logger.error(f"Błąd podczas przetwarzania grupy: {e}")
                if self.debug:
                    import traceback
                    self.logger.debug(f"Szczegóły błędu: {traceback.format_exc()}")
                continue

        # Sortujemy według pewności (najlepsze pierwsze)
        fragments.sort(key=lambda x: x.confidence_score, reverse=True)

        if self.debug:
            self.logger.debug(
                f"Znaleziono łącznie {len(fragments)} fragmentów {f'w pliku {source_file}' if source_file else ''}")

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

    @staticmethod
    def _finalize_group(group: List[Tuple[str, int]], text: str) -> Tuple[int, List[str]]:
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
                self.logger.debug("Fragment za krótki, pomijam")
            return None

        # Weryfikujemy słowa kluczowe w fragmencie
        verified_keywords = self.fragment_analyzer.verify_keywords_in_fragment(
            fragment_text, keywords
        )

        if not verified_keywords:
            if self.debug:
                self.logger.debug("Brak zweryfikowanych słów kluczowych")
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
            # spam:
            # if self.debug:
            #     self.logger.debug(f"Pomijam fragment: {skip_reason}")
            if "pewność za niska" in skip_reason.lower():
                self.stats['skipped_low_confidence'] += 1
            return None

        # Sprawdzamy duplikaty
        if self.fragment_analyzer.is_duplicate(fragment_text, existing_texts):
            if self.debug:
                self.logger.debug("Fragment jest duplikatem")
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

    @staticmethod
    def _build_char_to_word_mapping(text: str) -> dict:
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

    def _find_pdf_files(self, folder_path: str) -> List[str]:
        """
        Znajduje wszystkie pliki PDF w folderze

        Args:
            folder_path: Ścieżka do folderu

        Returns:
            Lista ścieżek do plików PDF
        """
        pdf_files = []

        # Konwertujemy na Path object dla lepszej obsługi ścieżek
        folder = Path(folder_path)

        if not folder.exists():
            self.logger.error(f"Folder {folder_path} nie istnieje")
            return []

        if not folder.is_dir():
            self.logger.error(f"Ścieżka {folder_path} nie jest folderem")
            return []

        # Szukamy wszystkich plików i filtrujemy po rozszerzeniu (case-insensitive)
        for file_path in folder.iterdir():
            if file_path.is_file() and file_path.suffix.lower() == '.pdf':
                pdf_files.append(str(file_path))

        # Sortujemy pliki
        pdf_files.sort()

        if self.debug:
            self.logger.debug(f"Znaleziono {len(pdf_files)} plików PDF w folderze {folder_path}")
            for pdf_file in pdf_files:
                self.logger.debug(f"  - {os.path.basename(pdf_file)}")

        return pdf_files

    def process_pdf_folder(self, folder_path: str, min_confidence: float = 0.3,
                           max_fragments_per_file: int = 50, max_total_fragments: int = 200) -> Dict[
        str, List[FunnyFragment]]:
        """
        Przetwarza wszystkie pliki PDF w folderze

        Args:
            folder_path: Ścieżka do folderu z plikami PDF
            min_confidence: Minimalny próg pewności (0.1-0.95)
            max_fragments_per_file: Maksymalna liczba fragmentów z jednego pliku
            max_total_fragments: Maksymalna całkowita liczba fragmentów

        Returns:
            Słownik {nazwa_pliku: lista_fragmentów}
        """
        # Walidacja parametrów
        if not folder_path or not isinstance(folder_path, str):
            raise ValueError("Ścieżka folderu musi być niepustym stringiem")

        if not 0.1 <= min_confidence <= 0.95:
            raise ValueError("min_confidence musi być w zakresie 0.1-0.95")

        if not isinstance(max_fragments_per_file, int) or max_fragments_per_file < 1:
            raise ValueError("max_fragments_per_file musi być dodatnią liczbą całkowitą")

        if not isinstance(max_total_fragments, int) or max_total_fragments < 1:
            raise ValueError("max_total_fragments musi być dodatnią liczbą całkowitą")

        # Resetujemy statystyki
        self.stats = {k: 0 for k in self.stats}

        if self.debug:
            logger.section("PRZETWARZANIE FOLDERU PDF")
            self.logger.info(f"Folder: {folder_path}")
            self.logger.info(
                f"Parametry - confidence: {min_confidence}, max/plik: {max_fragments_per_file}, max łącznie: {max_total_fragments}")

        # Znajdujemy pliki PDF
        pdf_files = self._find_pdf_files(folder_path)

        if not pdf_files:
            self.logger.warning(f"Nie znaleziono plików PDF w folderze {folder_path}")
            return {}

        self.logger.info(f"Znaleziono {len(pdf_files)} plików PDF do przetworzenia")

        results = {}
        total_fragments = 0

        # Przetwarzamy każdy plik
        for i, pdf_path in enumerate(pdf_files, 1):
            file_name = os.path.basename(pdf_path)

            if self.debug:
                logger.section(f"PLIK {i}/{len(pdf_files)}: {file_name}")
            else:
                self.logger.info(f"Przetwarzanie pliku {i}/{len(pdf_files)}: {file_name}")

            try:
                fragments = self.process_single_pdf(
                    pdf_path, min_confidence, max_fragments_per_file
                )

                if fragments:
                    results[file_name] = fragments
                    total_fragments += len(fragments)
                    self.logger.success(f"Znaleziono {len(fragments)} fragmentów w {file_name}")

                    # Sprawdzamy czy nie przekroczyliśmy limitu
                    if total_fragments >= max_total_fragments:
                        self.logger.warning(
                            f"Osiągnięto limit {max_total_fragments} fragmentów, przerywanie przetwarzania")
                        break
                else:
                    self.logger.info(f"Brak fragmentów spełniających kryteria w {file_name}")

                self.stats['processed_files'] += 1

            except Exception as e:
                self.logger.error(f"Błąd podczas przetwarzania {file_name}: {e}")
                self.stats['failed_files'] += 1
                if self.debug:
                    import traceback
                    self.logger.debug(f"Szczegóły błędu: {traceback.format_exc()}")
                continue

        # Ograniczamy wyniki do max_total_fragments
        if total_fragments > max_total_fragments:
            results = self._limit_total_fragments(results, max_total_fragments)

        # Pokazujemy statystyki
        self._print_folder_results_summary(results, pdf_files)

        return results

    def process_single_pdf(self, pdf_path: str, min_confidence: float = 0.3,
                           max_fragments: int = 50) -> List[FunnyFragment]:
        """
        Przetwarza pojedynczy plik PDF

        Args:
            pdf_path: Ścieżka do pliku PDF
            min_confidence: Minimalny próg pewności (0.1-0.95)
            max_fragments: Maksymalna liczba zwracanych fragmentów

        Returns:
            Lista znalezionych fragmentów
        """
        file_name = os.path.basename(pdf_path)

        # Sprawdzamy czy plik jest prawidłowy
        is_valid, validation_message = self.pdf_processor.validate_pdf_file(pdf_path)
        if not is_valid:
            self.logger.error(f"Walidacja {file_name} nieudana: {validation_message}")
            return []

        if self.debug:
            self.logger.debug(f"Plik {file_name} zwalidowany pomyślnie")

        # Wyciągamy tekst
        text = self.pdf_processor.extract_text_from_pdf(pdf_path)
        if not text:
            self.logger.error(f"Nie udało się wyciągnąć tekstu z {file_name}")
            return []

        if self.debug:
            self.logger.debug(f"Wyciągnięto {len(text)} znaków tekstu z {file_name}")

        # Znajdujemy śmieszne fragmenty
        all_fragments = self.find_funny_fragments(text, min_confidence, file_name)

        if not all_fragments:
            if self.debug:
                self.logger.debug(f"Nie znaleziono fragmentów w {file_name}")
            return []

        # Ograniczamy liczbę wyników
        fragments = all_fragments[:max_fragments]

        if self.debug:
            self.logger.debug(f"Zwracam {len(fragments)} najlepszych fragmentów z {file_name}")

        return fragments

    def _limit_total_fragments(self, results: Dict[str, List[FunnyFragment]],
                               max_total: int) -> Dict[str, List[FunnyFragment]]:
        """
        Ogranicza całkowitą liczbę fragmentów do określonego limitu,
        zachowując te o najwyższej pewności
        """
        # Zbieramy wszystkie fragmenty z informacją o pliku źródłowym
        all_fragments_with_source = []
        for file_name, fragments in results.items():
            for fragment in fragments:
                all_fragments_with_source.append((fragment, file_name))

        # Sortujemy według pewności
        all_fragments_with_source.sort(key=lambda x: x[0].confidence_score, reverse=True)

        # Bierzemy tylko najlepsze
        limited_fragments = all_fragments_with_source[:max_total]

        # Grupujemy z powrotem według plików
        new_results = {}
        for fragment, file_name in limited_fragments:
            if file_name not in new_results:
                new_results[file_name] = []
            new_results[file_name].append(fragment)

        return new_results

    def _print_folder_results_summary(self, results: Dict[str, List[FunnyFragment]], all_files: List[str]):
        """Wyświetla podsumowanie wyników przetwarzania folderu"""
        logger.section("PODSUMOWANIE PRZETWARZANIA FOLDERU")

        total_fragments = sum(len(fragments) for fragments in results.values())
        successful_files = len(results)
        failed_files = len(all_files) - successful_files

        logger.keyvalue("Przetworzone pliki", str(successful_files), Colors.GREEN)
        logger.keyvalue("Nieudane pliki", str(failed_files), Colors.RED if failed_files > 0 else Colors.GREEN)
        logger.keyvalue("Łączna liczba fragmentów", str(total_fragments), Colors.BLUE)

        if total_fragments > 0:
            all_fragments = []
            for fragments in results.values():
                all_fragments.extend(fragments)

            avg_confidence = sum(f.confidence_score for f in all_fragments) / len(all_fragments)
            logger.keyvalue("Średnia pewność", f"{avg_confidence:.3f}", Colors.YELLOW)
            logger.keyvalue("Najlepsza pewność", f"{max(f.confidence_score for f in all_fragments):.3f}", Colors.GREEN)

        # Ranking plików
        if results:
            self.logger.info("\nRanking plików według liczby fragmentów:")
            sorted_files = sorted(results.items(), key=lambda x: len(x[1]), reverse=True)

            for i, (file_name, fragments) in enumerate(sorted_files[:10], 1):
                if fragments:
                    avg_conf = sum(f.confidence_score for f in fragments) / len(fragments)
                    logger.keyvalue(f"  {i}. {file_name}",
                                    f"{len(fragments)} fragmentów (śr. pewność: {avg_conf:.2f})",
                                    Colors.CYAN)

    def get_all_fragments_sorted(self, results: Dict[str, List[FunnyFragment]]) -> List[FunnyFragment]:
        """
        Zwraca wszystkie fragmenty z wszystkich plików posortowane według pewności

        Args:
            results: Wyniki z process_pdf_folder

        Returns:
            Posortowana lista wszystkich fragmentów
        """
        all_fragments = []
        for fragments in results.values():
            all_fragments.extend(fragments)

        all_fragments.sort(key=lambda x: x.confidence_score, reverse=True)
        return all_fragments

    def process_pdf(self, pdf_path: str, min_confidence: float = 0.3,
                    max_fragments: int = 50) -> List[FunnyFragment]:
        """
        Główna funkcja przetwarzająca PDF lub folder z PDFami

        Args:
            pdf_path: Ścieżka do pliku PDF lub folderu z PDFami
            min_confidence: Minimalny próg pewności (0.1-0.95)
            max_fragments: Maksymalna liczba zwracanych fragmentów

        Returns:
            Lista znalezionych fragmentów
        """
        path = Path(pdf_path)

        # Sprawdzamy czy to folder czy plik
        if path.is_dir():
            self.logger.info(f"Wykryto folder - przetwarzanie wszystkich plików PDF w {pdf_path}")
            results = self.process_pdf_folder(pdf_path, min_confidence, max_fragments, max_fragments)
            return self.get_all_fragments_sorted(results)

        elif path.is_file() and path.suffix.lower() == '.pdf':
            self.logger.info(f"Wykryto plik PDF - przetwarzanie {pdf_path}")
            return self.process_single_pdf(pdf_path, min_confidence, max_fragments)

        else:
            raise ValueError(f"Ścieżka {pdf_path} nie jest ani plikiem PDF ani folderem")

    def get_processing_stats(self) -> dict:
        """Zwraca statystyki ostatniego przetwarzania"""
        return self.stats.copy()

    def reset_stats(self):
        """Resetuje statystyki przetwarzania"""
        self.stats = {k: 0 for k in self.stats}
