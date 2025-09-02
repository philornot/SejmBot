"""
Główny orchestrator - zastępuje FragmentDetector nową architekturą
Koordynuje: TranscriptParser → KeywordDetector → FragmentBuilder
"""
import os
from pathlib import Path
from typing import List, Dict

from SejmBotDetektor.logging.logger import get_module_logger, logger, Colors
from SejmBotDetektor.models.funny_fragment import FunnyFragment
from SejmBotDetektor.processors.fragment_builder import FragmentBuilder
from SejmBotDetektor.detectors.keyword_detector import KeywordDetector
from SejmBotDetektor.processors.pdf_processor import PDFProcessor
from SejmBotDetektor.processors.transcript_parser import TranscriptParser


class FunnyDetector:
    """
    Główny orchestrator dla nowej architektury
    Zastępuje FragmentDetector z cleaner pipeline: parse → detect → build
    """

    def __init__(self, context_before: int = 50, context_after: int = 100, debug: bool = False):
        """
        Args:
            context_before: Liczba słów przed słowem kluczowym
            context_after: Liczba słów po słowie kluczowym
            debug: Tryb debugowania
        """
        self.context_before = context_before
        self.context_after = context_after
        self.debug = debug
        self.logger = get_module_logger("FunnyDetector")

        # Inicjalizacja komponentów nowej architektury
        self.transcript_parser = TranscriptParser(debug=debug)
        self.keyword_detector = KeywordDetector(context_radius=10, debug=debug)
        self.fragment_builder = FragmentBuilder(
            context_before=context_before,
            context_after=context_after,
            debug=debug
        )
        self.pdf_processor = PDFProcessor(debug=debug)

        # Statystyki globalne
        self.global_stats = {
            'processed_texts': 0,
            'processed_files': 0,
            'failed_files': 0,
            'total_speeches': 0,
            'total_keyword_matches': 0,
            'total_fragments': 0,
            'parsing_time': 0.0,
            'detection_time': 0.0,
            'building_time': 0.0
        }

    def find_funny_fragments(self, text: str, min_confidence: float = 0.3,
                             source_file: str = None) -> List[FunnyFragment]:
        """
        Główna metoda API - kompatybilna z oryginalnym FragmentDetector
        Implementuje nowy pipeline: parse → detect → build

        Args:
            text: Tekst do przeanalizowania
            min_confidence: Minimalny próg pewności (0.1-0.95)
            source_file: Nazwa pliku źródłowego

        Returns:
            Lista znalezionych fragmentów wysokiej jakości
        """
        if not text or not text.strip():
            if self.debug:
                self.logger.debug("Pusty tekst wejściowy")
            return []

        if not 0.1 <= min_confidence <= 0.95:
            raise ValueError("min_confidence musi być w zakresie 0.1-0.95")

        if self.debug:
            self.logger.debug(f"Rozpoczynam analizę {f'pliku {source_file}' if source_file else 'tekstu'}")
            self.logger.debug(f"Długość tekstu: {len(text)} znaków")

        try:
            # ETAP 1: Parsowanie tekstu na wypowiedzi (jeden przebieg)
            import time
            start_time = time.time()

            parsed_transcript = self.transcript_parser.parse_transcript(text, source_file or "")

            parse_time = time.time() - start_time
            self.global_stats['parsing_time'] += parse_time
            self.global_stats['total_speeches'] += len(parsed_transcript.speeches)

            if not parsed_transcript.speeches:
                if self.debug:
                    self.logger.debug("Nie znaleziono wypowiedzi w tekście")
                return []

            if self.debug:
                self.logger.debug(f"Sparsowano {len(parsed_transcript.speeches)} wypowiedzi "
                                  f"w {parse_time:.2f}s")

            # ETAP 2: Wykrywanie słów kluczowych w wypowiedziach
            start_time = time.time()

            keyword_matches = self.keyword_detector.find_keywords_in_speeches(
                parsed_transcript.speeches, min_speech_words=5
            )

            detect_time = time.time() - start_time
            self.global_stats['detection_time'] += detect_time
            self.global_stats['total_keyword_matches'] += len(keyword_matches)

            if not keyword_matches:
                if self.debug:
                    self.logger.debug("Nie znaleziono słów kluczowych w wypowiedziach")
                return []

            if self.debug:
                self.logger.debug(f"Znaleziono {len(keyword_matches)} dopasowań słów kluczowych "
                                  f"w {detect_time:.2f}s")

            # ETAP 3: Budowanie fragmentów z dopasowań
            start_time = time.time()

            fragments = self.fragment_builder.build_fragments_from_matches(
                keyword_matches, min_confidence=min_confidence, max_fragments=200
            )

            build_time = time.time() - start_time
            self.global_stats['building_time'] += build_time
            self.global_stats['total_fragments'] += len(fragments)

            if self.debug:
                self.logger.debug(f"Zbudowano {len(fragments)} fragmentów w {build_time:.2f}s")

            # ETAP 4: Wzbogacenie fragmentów o kontekst z oryginalnego tekstu
            if fragments:
                fragments = self.fragment_builder.enhance_fragments_with_context(
                    fragments, text
                )

            # ETAP 5: Optymalizacja końcowa
            if len(fragments) > 100:
                fragments = self.fragment_builder.optimize_fragments_for_output(
                    fragments, target_count=100
                )

            self.global_stats['processed_texts'] += 1

            if self.debug:
                total_time = parse_time + detect_time + build_time
                self.logger.debug(f"Łączny czas przetwarzania: {total_time:.2f}s "
                                  f"(parsing: {parse_time:.2f}s, detection: {detect_time:.2f}s, "
                                  f"building: {build_time:.2f}s)")

            return fragments

        except Exception as e:
            self.logger.error(f"Błąd podczas analizy tekstu: {e}")
            if self.debug:
                import traceback
                self.logger.debug(f"Szczegóły błędu: {traceback.format_exc()}")
            return []

    def process_single_pdf(self, pdf_path: str, min_confidence: float = 0.3,
                           max_fragments: int = 50) -> List[FunnyFragment]:
        """
        Przetwarza pojedynczy plik PDF

        Args:
            pdf_path: Ścieżka do pliku PDF
            min_confidence: Minimalny próg pewności
            max_fragments: Maksymalna liczba fragmentów

        Returns:
            Lista fragmentów
        """
        file_name = os.path.basename(pdf_path)

        if self.debug:
            self.logger.debug(f"Rozpoczynam przetwarzanie PDF: {file_name}")

        try:
            # Walidacja pliku PDF
            is_valid, validation_message = self.pdf_processor.validate_pdf_file(pdf_path)
            if not is_valid:
                self.logger.error(f"Walidacja {file_name} nieudana: {validation_message}")
                self.global_stats['failed_files'] += 1
                return []

            # Ekstrakcja tekstu
            text = self.pdf_processor.extract_text_from_pdf(pdf_path)
            if not text:
                self.logger.error(f"Nie udało się wyciągnąć tekstu z {file_name}")
                self.global_stats['failed_files'] += 1
                return []

            if self.debug:
                self.logger.debug(f"Wyciągnięto {len(text)} znaków tekstu z {file_name}")

            # Analiza tekstu używając nowego pipeline
            fragments = self.find_funny_fragments(
                text=text,
                min_confidence=min_confidence,
                source_file=file_name
            )

            # Ograniczenie liczby fragmentów
            fragments = fragments[:max_fragments]

            self.global_stats['processed_files'] += 1

            if self.debug:
                self.logger.debug(f"Zakończono przetwarzanie {file_name}: {len(fragments)} fragmentów")

            return fragments

        except Exception as e:
            self.logger.error(f"Błąd podczas przetwarzania {file_name}: {e}")
            self.global_stats['failed_files'] += 1
            if self.debug:
                import traceback
                self.logger.debug(f"Szczegóły błędu: {traceback.format_exc()}")
            return []

    def process_pdf_folder(self, folder_path: str, min_confidence: float = 0.3,
                           max_fragments_per_file: int = 50,
                           max_total_fragments: int = 200) -> Dict[str, List[FunnyFragment]]:
        """
        Przetwarza wszystkie pliki PDF w folderze

        Args:
            folder_path: Ścieżka do folderu z plikami PDF
            min_confidence: Minimalny próg pewności
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

        if self.debug:
            logger.section("PRZETWARZANIE FOLDERU PDF - NOWA ARCHITEKTURA")
            self.logger.info(f"Folder: {folder_path}")
            self.logger.info(f"Parametry - confidence: {min_confidence}, "
                             f"max/plik: {max_fragments_per_file}, max łącznie: {max_total_fragments}")

        # Znajdź pliki PDF
        pdf_files = self._find_pdf_files(folder_path)
        if not pdf_files:
            self.logger.warning(f"Nie znaleziono plików PDF w folderze {folder_path}")
            return {}

        self.logger.info(f"Znaleziono {len(pdf_files)} plików PDF do przetworzenia")

        results = {}
        total_fragments = 0

        # Przetwarzaj każdy plik
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

                    # Sprawdź limit
                    if total_fragments >= max_total_fragments:
                        self.logger.warning(f"Osiągnięto limit {max_total_fragments} fragmentów")
                        break
                else:
                    self.logger.info(f"Brak fragmentów spełniających kryteria w {file_name}")

            except Exception as e:
                self.logger.error(f"Błąd podczas przetwarzania {file_name}: {e}")
                continue

        # Ograniczenie wyników do max_total_fragments
        if total_fragments > max_total_fragments:
            results = self._limit_total_fragments(results, max_total_fragments)

        # Podsumowanie
        self._print_folder_results_summary(results, pdf_files)

        return results

    def process_pdf(self, pdf_path: str, min_confidence: float = 0.3,
                    max_fragments: int = 50) -> List[FunnyFragment]:
        """
        Główna funkcja przetwarzająca PDF lub folder - kompatybilna z oryginalnym API

        Args:
            pdf_path: Ścieżka do pliku PDF lub folderu z PDFami
            min_confidence: Minimalny próg pewności
            max_fragments: Maksymalna liczba zwracanych fragmentów

        Returns:
            Lista znalezionych fragmentów
        """
        path = Path(pdf_path)

        if path.is_dir():
            self.logger.info(f"Wykryto folder - przetwarzanie wszystkich plików PDF w {pdf_path}")
            results = self.process_pdf_folder(pdf_path, min_confidence, max_fragments, max_fragments)
            return self._get_all_fragments_sorted(results)

        elif path.is_file() and path.suffix.lower() == '.pdf':
            self.logger.info(f"Wykryto plik PDF - przetwarzanie {pdf_path}")
            return self.process_single_pdf(pdf_path, min_confidence, max_fragments)

        else:
            raise ValueError(f"Ścieżka {pdf_path} nie jest ani plikiem PDF ani folderem")

    def _find_pdf_files(self, folder_path: str) -> List[str]:
        """Znajduje wszystkie pliki PDF w folderze"""
        pdf_files = []
        folder = Path(folder_path)

        if not folder.exists():
            self.logger.error(f"Folder {folder_path} nie istnieje")
            return []

        if not folder.is_dir():
            self.logger.error(f"Ścieżka {folder_path} nie jest folderem")
            return []

        for file_path in folder.iterdir():
            if file_path.is_file() and file_path.suffix.lower() == '.pdf':
                pdf_files.append(str(file_path))

        pdf_files.sort()

        if self.debug:
            self.logger.debug(f"Znaleziono {len(pdf_files)} plików PDF w folderze {folder_path}")

        return pdf_files

    @staticmethod
    def _limit_total_fragments(results: Dict[str, List[FunnyFragment]],
                               max_total: int) -> Dict[str, List[FunnyFragment]]:
        """Ogranicza całkowitą liczbę fragmentów zachowując najlepsze"""
        # Zbierz wszystkie fragmenty z informacją o pliku
        all_fragments_with_source = []
        for file_name, fragments in results.items():
            for fragment in fragments:
                all_fragments_with_source.append((fragment, file_name))

        # Sortuj według pewności i weź najlepsze
        all_fragments_with_source.sort(key=lambda x: x[0].confidence_score, reverse=True)
        limited_fragments = all_fragments_with_source[:max_total]

        # Grupuj z powrotem według plików
        new_results = {}
        for fragment, file_name in limited_fragments:
            if file_name not in new_results:
                new_results[file_name] = []
            new_results[file_name].append(fragment)

        return new_results

    @staticmethod
    def _get_all_fragments_sorted(results: Dict[str, List[FunnyFragment]]) -> List[FunnyFragment]:
        """Zwraca wszystkie fragmenty posortowane według pewności"""
        all_fragments = []
        for fragments in results.values():
            all_fragments.extend(fragments)

        all_fragments.sort(key=lambda x: x.confidence_score, reverse=True)
        return all_fragments

    def _print_folder_results_summary(self, results: Dict[str, List[FunnyFragment]],
                                      all_files: List[str]):
        """Wyświetla podsumowanie wyników przetwarzania folderu"""
        logger.section("PODSUMOWANIE PRZETWARZANIA FOLDERU - NOWA ARCHITEKTURA")

        total_fragments = sum(len(fragments) for fragments in results.values())
        successful_files = len(results)
        failed_files = len(all_files) - successful_files

        logger.keyvalue("Przetworzone pliki", str(successful_files), Colors.GREEN)
        logger.keyvalue("Nieudane pliki", str(failed_files),
                        Colors.RED if failed_files > 0 else Colors.GREEN)
        logger.keyvalue("Łączna liczba fragmentów", str(total_fragments), Colors.BLUE)

        # Statystyki wydajności nowej architektury
        if self.global_stats['processed_files'] > 0:
            avg_parse_time = self.global_stats['parsing_time'] / self.global_stats['processed_files']
            avg_detect_time = self.global_stats['detection_time'] / self.global_stats['processed_files']
            avg_build_time = self.global_stats['building_time'] / self.global_stats['processed_files']

            logger.keyvalue("Średni czas parsowania", f"{avg_parse_time:.2f}s", Colors.CYAN)
            logger.keyvalue("Średni czas detekcji", f"{avg_detect_time:.2f}s", Colors.CYAN)
            logger.keyvalue("Średni czas budowania", f"{avg_build_time:.2f}s", Colors.CYAN)

        # Statystyki komponentów
        logger.keyvalue("Łączne wypowiedzi", str(self.global_stats['total_speeches']), Colors.YELLOW)
        logger.keyvalue("Łączne dopasowania słów", str(self.global_stats['total_keyword_matches']), Colors.YELLOW)

        if total_fragments > 0:
            all_fragments = [f for fragments in results.values() for f in fragments]
            avg_confidence = sum(f.confidence_score for f in all_fragments) / len(all_fragments)
            best_confidence = max(f.confidence_score for f in all_fragments)

            logger.keyvalue("Średnia pewność", f"{avg_confidence:.3f}", Colors.YELLOW)
            logger.keyvalue("Najlepsza pewność", f"{best_confidence:.3f}", Colors.GREEN)

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

    def get_processing_stats(self) -> dict:
        """Zwraca szczegółowe statystyki przetwarzania"""
        stats = self.global_stats.copy()

        # Dodaj statystyki komponentów
        stats['transcript_parser_stats'] = self.transcript_parser.stats
        stats['keyword_detector_stats'] = self.keyword_detector.get_detection_stats()
        stats['fragment_builder_stats'] = self.fragment_builder.get_building_stats()

        return stats

    def reset_stats(self):
        """Resetuje wszystkie statystyki"""
        self.global_stats = {k: 0 if not isinstance(v, float) else 0.0
                             for k, v in self.global_stats.items()}
