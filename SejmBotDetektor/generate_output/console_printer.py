"""
Moduł do wyświetlania wyników w konsoli
"""
from typing import List, Dict

from SejmBotDetektor.logging.logger import get_module_logger, Colors
from SejmBotDetektor.models.funny_fragment import FunnyFragment


class ConsolePrinter:
    """Klasa odpowiedzialna za formatowane wyświetlanie wyników w konsoli"""

    def __init__(self, debug: bool = False):
        self.logger = get_module_logger("ConsolePrinter")
        self.debug = debug

    def print_fragments(self, fragments: List[FunnyFragment], max_fragments: int = 10):
        """
        Wyświetla fragmenty w konsoli z kolorowym formatowaniem

        Args:
            fragments: Lista fragmentów do wyświetlenia
            max_fragments: Maksymalna liczba fragmentów do pokazania
        """
        if not fragments:
            self.logger.warning("Brak fragmentów do wyświetlenia")
            return

        self.logger.section(f"NAJLEPSZE FRAGMENTY ({min(len(fragments), max_fragments)} z {len(fragments)})")

        for i, fragment in enumerate(fragments[:max_fragments], 1):
            self._print_single_fragment(fragment, i)

        if len(fragments) > max_fragments:
            remaining = len(fragments) - max_fragments
            self.logger.info(f"\n... i {remaining} więcej fragmentów (zobacz pliki wyjściowe)")

    def print_folder_results(self, results: Dict[str, List[FunnyFragment]], max_files: int = 10):
        """
        Wyświetla wyniki z wielu plików w przejrzysty sposób

        Args:
            results: Słownik {nazwa_pliku: lista_fragmentów}
            max_files: Maksymalna liczba plików do szczegółowego pokazania
        """
        if not results:
            self.logger.warning("Brak wyników do wyświetlenia")
            return

        total_fragments = sum(len(fragments) for fragments in results.values())
        self.logger.section(f"WYNIKI Z {len(results)} PLIKÓW ({total_fragments} fragmentów)")

        # Sortujemy pliki według liczby fragmentów
        sorted_files = sorted(results.items(), key=lambda x: len(x[1]), reverse=True)

        # Pokazujemy podsumowanie wszystkich plików
        self._print_files_summary(sorted_files)

        # Szczegółowe informacje o najlepszych plikach
        self.logger.section("SZCZEGÓŁY NAJLEPSZYCH PLIKÓW")

        for i, (file_name, fragments) in enumerate(sorted_files[:max_files], 1):
            if not fragments:
                continue

            self._print_file_details(file_name, fragments, i)

        if len(results) > max_files:
            remaining = len(results) - max_files
            self.logger.info(f"\n... i {remaining} więcej plików (pełne wyniki w plikach wyjściowych)")

    def print_summary_stats(self, fragments: List[FunnyFragment]):
        """
        Wyświetla podsumowanie statystyk fragmentów

        Args:
            fragments: Lista fragmentów do analizy
        """
        if not fragments:
            self.logger.warning("Brak fragmentów do podsumowania")
            return

        self.logger.section("STATYSTYKI FRAGMENTÓW")

        # Podstawowe statystyki
        confidences = [f.confidence_score for f in fragments]
        avg_confidence = sum(confidences) / len(confidences)

        self.logger.keyvalue("Łączna liczba fragmentów", str(len(fragments)), Colors.CYAN)
        self.logger.keyvalue("Średnia pewność", f"{avg_confidence:.3f}", Colors.YELLOW)
        self.logger.keyvalue("Najwyższa pewność", f"{max(confidences):.3f}", Colors.GREEN)
        self.logger.keyvalue("Najniższa pewność", f"{min(confidences):.3f}", Colors.RED)

        # Rozkład jakości
        high_quality = len([f for f in fragments if f.confidence_score >= 0.7])
        medium_quality = len([f for f in fragments if 0.4 <= f.confidence_score < 0.7])
        low_quality = len([f for f in fragments if f.confidence_score < 0.4])

        print()
        self.logger.info("Rozkład jakości fragmentów:")
        self.logger.keyvalue("  Wysoka jakość (≥0.7)", f"{high_quality} ({high_quality / len(fragments) * 100:.1f}%)",
                             Colors.GREEN)
        self.logger.keyvalue("  Średnia jakość (0.4-0.7)",
                             f"{medium_quality} ({medium_quality / len(fragments) * 100:.1f}%)", Colors.YELLOW)
        self.logger.keyvalue("  Niska jakość (<0.4)", f"{low_quality} ({low_quality / len(fragments) * 100:.1f}%)",
                             Colors.RED)

        # Analiza mówców
        self._print_speakers_analysis(fragments)

        # Analiza słów kluczowych
        self._print_keywords_analysis(fragments)

    def print_processing_progress(self, current_file: str, processed: int, total: int):
        """
        Wyświetla postęp przetwarzania plików

        Args:
            current_file: Nazwa aktualnie przetwarzanego pliku
            processed: Liczba przetworzonych plików
            total: Całkowita liczba plików
        """
        progress = (processed / total) * 100
        self.logger.info(f"[{progress:.1f}%] Przetwarzanie: {current_file}")

    def _print_single_fragment(self, fragment: FunnyFragment, index: int):
        """Wyświetla pojedynczy fragment z kolorowym formatowaniem"""
        confidence_color = Colors.GREEN if fragment.confidence_score >= 0.7 else \
            Colors.YELLOW if fragment.confidence_score >= 0.4 else Colors.RED

        self.logger.info(f"\n--- FRAGMENT {index} ---")
        self.logger.keyvalue("Mówca", fragment.speaker, Colors.CYAN)
        self.logger.keyvalue("Pewność", f"{fragment.confidence_score:.3f}", confidence_color)
        self.logger.keyvalue("Słowa kluczowe", fragment.get_keywords_as_string(), Colors.MAGENTA)

        # Informacja o pliku źródłowym
        source_file, meeting_info = self._extract_file_info(fragment.meeting_info)
        if source_file != "nieznany":
            self.logger.keyvalue("Plik źródłowy", source_file, Colors.BLUE)
            self.logger.keyvalue("Posiedzenie", meeting_info, Colors.GRAY)
        else:
            self.logger.keyvalue("Posiedzenie", meeting_info, Colors.GRAY)

        # Podgląd tekstu - ograniczamy długość dla czytelności
        preview = fragment.get_short_preview(150)
        self.logger.keyvalue("Tekst", preview, Colors.WHITE)

        if fragment.position_in_text != -1:
            self.logger.keyvalue("Pozycja", str(fragment.position_in_text), Colors.GRAY)

    def _print_files_summary(self, sorted_files: List[tuple]):
        """Wyświetla podsumowanie wszystkich plików"""
        self.logger.info("Podsumowanie plików:")

        for i, (file_name, fragments) in enumerate(sorted_files, 1):
            if not fragments:
                continue

            avg_confidence = sum(f.confidence_score for f in fragments) / len(fragments)
            best_confidence = max(f.confidence_score for f in fragments)

            # Kolorujemy według średniej pewności
            color = Colors.GREEN if avg_confidence >= 0.6 else \
                Colors.YELLOW if avg_confidence >= 0.4 else Colors.RED

            summary = f"{file_name}: {len(fragments)} fragmentów (śr. {avg_confidence:.2f}, max {best_confidence:.2f})"
            self.logger.list_item(summary, level=1, color=color)

    def _print_file_details(self, file_name: str, fragments: List[FunnyFragment], file_index: int):
        """Wyświetla szczegóły pojedynczego pliku"""
        avg_confidence = sum(f.confidence_score for f in fragments) / len(fragments)
        best_fragment = max(fragments, key=lambda f: f.confidence_score)

        self.logger.info(f"\n{file_index}. {file_name}")
        self.logger.keyvalue("  Fragmenty", str(len(fragments)), Colors.CYAN)
        self.logger.keyvalue("  Średnia pewność", f"{avg_confidence:.3f}", Colors.YELLOW)
        self.logger.keyvalue("  Najlepszy fragment", f"{best_fragment.confidence_score:.3f} - {best_fragment.speaker}",
                             Colors.GREEN)

        # Pokazujemy podgląd najlepszego fragmentu
        preview = best_fragment.get_short_preview(100)
        self.logger.keyvalue("  Podgląd", f'"{preview}"', Colors.WHITE)

    def _print_speakers_analysis(self, fragments: List[FunnyFragment]):
        """Wyświetla analizę najaktywniejszych mówców"""
        speakers = {}
        for fragment in fragments:
            speakers[fragment.speaker] = speakers.get(fragment.speaker, 0) + 1

        if speakers:
            print()
            self.logger.info("Top 5 najaktywniejszych mówców:")
            sorted_speakers = sorted(speakers.items(), key=lambda x: x[1], reverse=True)

            for i, (speaker, count) in enumerate(sorted_speakers[:5], 1):
                percentage = (count / len(fragments)) * 100
                self.logger.list_item(f"{speaker}: {count} fragmentów ({percentage:.1f}%)", level=1, color=Colors.CYAN)

    def _print_keywords_analysis(self, fragments: List[FunnyFragment]):
        """Wyświetla analizę najczęstszych słów kluczowych"""
        all_keywords = []
        for fragment in fragments:
            all_keywords.extend(fragment.keywords_found)

        if all_keywords:
            keyword_counts = {}
            for keyword in all_keywords:
                keyword_counts[keyword] = keyword_counts.get(keyword, 0) + 1

            print()
            self.logger.info("Top 10 najczęstszych słów kluczowych:")
            sorted_keywords = sorted(keyword_counts.items(), key=lambda x: x[1], reverse=True)

            for keyword, count in sorted_keywords[:10]:
                percentage = (count / len(all_keywords)) * 100
                self.logger.list_item(f"'{keyword}': {count} wystąpień ({percentage:.1f}%)", level=1,
                                      color=Colors.MAGENTA)

    def _extract_file_info(self, meeting_info: str) -> tuple[str, str]:
        """
        Wyciąga informację o pliku źródłowym z meeting_info

        Returns:
            Tuple (nazwa_pliku, info_o_posiedzeniu)
        """
        if "| Plik:" in meeting_info:
            meeting_part, file_part = meeting_info.split("| Plik:", 1)
            return file_part.strip(), meeting_part.strip()
        else:
            return "nieznany", meeting_info

    def print_export_summary(self, fragments_count: int, files_generated: List[str]):
        """
        Wyświetla podsumowanie eksportu plików

        Args:
            fragments_count: Liczba wyeksportowanych fragmentów
            files_generated: Lista nazw wygenerowanych plików
        """
        self.logger.section("PODSUMOWANIE EKSPORTU")

        self.logger.success(f"Pomyślnie przetworzono {fragments_count} fragmentów")

        if files_generated:
            self.logger.info("Wygenerowane pliki:")
            for file_path in files_generated:
                self.logger.list_item(file_path, level=1, color=Colors.GREEN)

        self.logger.info(f"\nSprawdź folder 'output' aby zobaczyć wszystkie wyniki!")
