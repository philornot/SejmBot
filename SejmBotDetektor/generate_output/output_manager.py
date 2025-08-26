"""
Główny moduł do zarządzania eksportem wyników
Koordynuje pracę wszystkich eksporterów i generatorów
"""
import json
import os
from pathlib import Path
from typing import List, Dict, Union

from SejmBotDetektor.detectors.fragment_detector import FragmentDetector
from SejmBotDetektor.generate_output.console_printer import ConsolePrinter
from SejmBotDetektor.generate_output.html_generator import HtmlGenerator
from SejmBotDetektor.generate_output.json_exporter import JsonExporter
from SejmBotDetektor.logging.logger import get_module_logger
from SejmBotDetektor.models.funny_fragment import FunnyFragment


class OutputManager:
    """
    Główna klasa koordynująca eksport wyników do różnych formatów
    """

    def __init__(self, debug: bool = False, output_folder: str = "output"):
        self.logger = get_module_logger("OutputManager")
        self.debug = debug
        self.output_folder = output_folder

        # Inicjalizujemy komponenty
        self.json_exporter = JsonExporter(debug)
        self.html_generator = HtmlGenerator(debug)
        self.console_printer = ConsolePrinter(debug)

        # Zapewniamy istnienie folderu output
        self._ensure_output_folder()

        self.generated_files = []  # Lista wygenerowanych plików

    def export_results(self,
                       fragments_data: Union[List[FunnyFragment], Dict[str, List[FunnyFragment]]],
                       base_name: str = "results",
                       include_html: bool = False,
                       config: Dict = None) -> bool:
        """
        Uniwersalna metoda eksportu - zastępuje wszystkie poprzednie metody eksportu

        Args:
            fragments_data: Lista fragmentów lub słownik {nazwa_pliku: lista_fragmentów}
            base_name: Bazowa nazwa pliku (bez rozszerzenia)
            include_html: Czy generować raport HTML
            config: Opcjonalna konfiguracja do zapisania w metadanych

        Returns:
            True jeśli eksport się powiódł
        """
        if not fragments_data:
            self.logger.warning("Brak danych do eksportu")
            return False

        success_count = 0
        total_exports = 1 + (1 if include_html else 0)  # JSON + opcjonalnie HTML

        # Określamy typ eksportu
        is_batch = isinstance(fragments_data, dict)
        export_type = "batch_processing" if is_batch else "single_file"

        # Ustalamy nazwę pliku JSON
        json_filename = f"{base_name}.json"
        if is_batch and base_name == "results":
            json_filename = "batch_results.json"
        elif not is_batch and base_name == "results":
            json_filename = "fragments.json"

        # Eksport JSON w nowym formacie
        json_path = self._get_output_path(json_filename)
        if self.json_exporter.export_ai_ready_format(fragments_data, json_path, export_type, config):
            self.generated_files.append(json_path)
            success_count += 1
            self.logger.info(f"Wyeksportowano dane do {json_filename}")

        # Opcjonalny HTML
        if include_html:
            html_filename = f"{base_name}_report.html"
            if is_batch and base_name == "results":
                html_filename = "batch_report.html"
            elif not is_batch and base_name == "results":
                html_filename = "fragments_report.html"

            html_path = self._get_output_path(html_filename)

            if is_batch:
                if self.html_generator.generate_folder_report(fragments_data, html_path):
                    self.generated_files.append(html_path)
                    success_count += 1
            else:
                if self.html_generator.generate_report(fragments_data, html_path):
                    self.generated_files.append(html_path)
                    success_count += 1

        # Podsumowanie
        if success_count == total_exports:
            self.logger.success("Eksport zakończony pomyślnie")
            return True
        elif success_count > 0:
            self.logger.warning(f"Zakończono {success_count}/{total_exports} eksportów")
            return True
        else:
            self.logger.error("Eksport nie powiódł się")
            return False

    def print_results(self, fragments: List[FunnyFragment], max_fragments: int = 5):
        """
        Wyświetla fragmenty w konsoli

        Args:
            fragments: Lista fragmentów
            max_fragments: Maksymalna liczba fragmentów do pokazania
        """
        self.console_printer.print_fragments(fragments, max_fragments)

    def print_folder_results(self, results: Dict[str, List[FunnyFragment]], max_files: int = 5):
        """
        Wyświetla wyniki z folderu w konsoli

        Args:
            results: Wyniki z wielu plików
            max_files: Maksymalna liczba plików do szczegółowego pokazania
        """
        self.console_printer.print_folder_results(results, max_files)

    def print_summary_stats(self, fragments: List[FunnyFragment]):
        """Wyświetla statystyki fragmentów"""
        self.console_printer.print_summary_stats(fragments)

    def print_export_summary(self):
        """Wyświetla podsumowanie wygenerowanych plików"""
        total_fragments = self._count_total_fragments()
        self.console_printer.print_export_summary(total_fragments, self.generated_files)

    def load_fragments(self, input_file: str) -> List[FunnyFragment]:
        """
        Wczytuje fragmenty z pliku JSON

        Args:
            input_file: Ścieżka do pliku JSON

        Returns:
            Lista fragmentów
        """
        return self.json_exporter.load_fragments(input_file)

    def _ensure_output_folder(self):
        """Zapewnia istnienie folderu output"""
        try:
            Path(self.output_folder).mkdir(parents=True, exist_ok=True)
            if self.debug:
                self.logger.debug(f"Folder output: {self.output_folder}")
        except Exception as e:
            self.logger.error(f"Nie można utworzyć folderu {self.output_folder}: {e}")
            self.output_folder = ""  # Zapisujemy w bieżącym folderze

    def _get_output_path(self, filename: str) -> str:
        """Zwraca pełną ścieżkę do pliku w folderze output"""
        if self.output_folder:
            return os.path.join(self.output_folder, filename)
        return filename

    def _count_total_fragments(self) -> int:
        """Próbuje policzyć łączną liczbę fragmentów z wygenerowanych plików"""
        total = 0

        for file_path in self.generated_files:
            if file_path.endswith('.json'):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)

                    # Sprawdzamy różne struktury JSON
                    if isinstance(data, dict):
                        if "metadata" in data and "total_fragments" in data["metadata"]:
                            # Nowy format AI-ready
                            total += data["metadata"]["total_fragments"]
                        elif "fragments" in data:
                            # Stary format z listą fragmentów
                            total += len(data["fragments"])
                        elif "summary" in data and "total_fragments" in data["summary"]:
                            # Bardzo stary format
                            total += data["summary"]["total_fragments"]
                    elif isinstance(data, list):
                        # Najstarszy format — prosta lista
                        total += len(data)

                except (FileNotFoundError, json.JSONDecodeError, KeyError) as e:
                    if self.debug:
                        self.logger.debug(f"Nie można odczytać metadanych z {file_path}: {e}")
                    continue

        return total

    # DEPRECATED METHODS — zachowane dla kompatybilności wstecznej
    def export_fragments(self, fragments: List[FunnyFragment], base_filename: str = "funny_fragments") -> bool:
        """DEPRECATED: Użyj export_results()"""
        self.logger.warning("export_fragments jest deprecated - użyj export_results()")
        return self.export_results(fragments, base_filename, include_html=True)

    def export_folder_results(self, results: Dict[str, List[FunnyFragment]],
                              base_filename: str = "folder_results") -> bool:
        """DEPRECATED: Użyj export_results()"""
        self.logger.warning("export_folder_results jest deprecated - użyj export_results()")
        return self.export_results(results, base_filename, include_html=True)

    def save_fragments_to_json(self, fragments: List[FunnyFragment], output_file: str) -> bool:
        """DEPRECATED: Użyj export_results()"""
        self.logger.warning("save_fragments_to_json jest deprecated - użyj export_results()")
        return self.json_exporter.export_ai_ready_format(fragments, output_file, "single_file")

    def generate_html_report(self, fragments: List[FunnyFragment], output_file: str = "report.html") -> bool:
        """DEPRECATED: Użyj export_results() z include_html=True"""
        self.logger.warning("generate_html_report jest deprecated - użyj export_results()")
        return self.html_generator.generate_report(fragments, output_file)

    def print_fragments(self, fragments: List[FunnyFragment], max_fragments: int = 10):
        """DEPRECATED: Użyj print_results()"""
        self.logger.warning("print_fragments jest deprecated - użyj print_results()")
        self.print_results(fragments, max_fragments)

    """
    Dodana metoda process_folder_results do OutputManager
    Lokalizacja: SejmBotDetektor/generate_output/output_manager.py
    """

    def process_folder_results(self, folder_path: str, min_confidence: float = 0.3,
                               max_fragments_per_file: int = 50, max_total_fragments: int = 200,
                               context_before: int = 50, context_after: int = 100) -> Dict[str, List]:
        """
        Kompletny workflow przetwarzania folderu PDF - od skanowania do eksportu

        Args:
            folder_path: Ścieżka do folderu z plikami PDF
            min_confidence: Minimalny próg pewności
            max_fragments_per_file: Maksymalna liczba fragmentów z jednego pliku
            max_total_fragments: Maksymalna całkowita liczba fragmentów
            context_before: Liczba słów kontekstu przed
            context_after: Liczba słów kontekstu po

        Returns:
            Słownik {nazwa_pliku: lista_fragmentów}
        """
        from pathlib import Path

        if self.debug:
            self.logger.debug(f"Rozpoczynam pełny workflow dla folderu: {folder_path}")

        # Walidacja folderu
        folder = Path(folder_path)
        if not folder.exists():
            self.logger.error(f"Folder {folder_path} nie istnieje")
            return {}

        pdf_files = list(folder.glob("*.pdf"))
        if not pdf_files:
            self.logger.warning(f"Nie znaleziono plików PDF w folderze {folder_path}")
            return {}

        self.logger.info(f"Znaleziono {len(pdf_files)} plików PDF do przetworzenia")

        # Inicjalizujemy FragmentDetetector
        fragment_detector = FragmentDetector(debug=self.debug)

        results = {}
        total_fragments = 0

        for i, pdf_path in enumerate(pdf_files, 1):
            file_name = pdf_path.name

            if self.debug:
                self.logger.debug(f"Przetwarzanie {i}/{len(pdf_files)}: {file_name}")
            else:
                self.logger.info(f"Przetwarzanie pliku {i}/{len(pdf_files)}: {file_name}")

            try:
                # Sprawdzamy limit przed przetworzeniem
                if total_fragments >= max_total_fragments:
                    self.logger.warning(f"Osiągnięto limit {max_total_fragments} fragmentów")
                    break

                # Dostosowujemy limit dla tego pliku
                remaining_limit = max_total_fragments - total_fragments
                file_limit = min(max_fragments_per_file, remaining_limit)

                # Przetwarzamy pojedynczy plik przez SpeechProcessor
                fragments = fragment_detector.process_single_pdf(
                    str(pdf_path), min_confidence, file_limit
                )

                if fragments:
                    results[file_name] = fragments
                    total_fragments += len(fragments)
                    self.logger.info(f"Znaleziono {len(fragments)} fragmentów w {file_name}")
                else:
                    if self.debug:
                        self.logger.debug(f"Brak fragmentów w {file_name}")

            except Exception as e:
                self.logger.error(f"Błąd podczas przetwarzania {file_name}: {e}")
                if self.debug:
                    import traceback
                    self.logger.debug(f"Szczegóły błędu: {traceback.format_exc()}")
                continue

        # Ograniczamy wyniki do max_total_fragments jeśli potrzeba
        if total_fragments > max_total_fragments:
            results = self._limit_total_fragments(results, max_total_fragments)

        self.logger.info(f"Zakończono przetwarzanie. Łącznie {sum(len(f) for f in results.values())} fragmentów")
        return results

    def process_single_file_complete(self, pdf_path: str, min_confidence: float = 0.3,
                                     max_fragments: int = 50, include_export: bool = True) -> List:
        """
        Kompletny workflow dla pojedynczego pliku - przetwarzanie + opcjonalny eksport

        Args:
            pdf_path: Ścieżka do pliku PDF
            min_confidence: Minimalny próg pewności
            max_fragments: Maksymalna liczba fragmentów
            include_export: Czy automatycznie eksportować wyniki

        Returns:
            Lista znalezionych fragmentów
        """
        file_name = os.path.basename(pdf_path)

        if self.debug:
            self.logger.debug(f"Rozpoczynam kompletny workflow dla: {file_name}")

        # Przetwarzanie
        fragments = speech_processor.process_single_pdf(
            pdf_path, min_confidence, max_fragments
        )

        if not fragments:
            self.logger.warning("Nie znaleziono fragmentów spełniających kryteria")
            return []

        # Wyświetlenie wyników
        self.print_results(fragments, max_fragments=5)

        # Opcjonalny eksport
        if include_export:
            export_config = {
                "min_confidence": min_confidence,
                "max_fragments": max_fragments,
                "source_file": file_name
            }

            if self.export_results(fragments, "single_file_results", self.debug, export_config):
                self.logger.success("Eksport zakończony pomyślnie")

            self.print_export_summary()

        return fragments

    def _limit_total_fragments(self, results: Dict[str, List], max_total: int) -> Dict[str, List]:
        """
        Ogranicza całkowitą liczbę fragmentów do określonego limitu,
        zachowując te o najwyższej pewności
        """
        all_fragments_with_source = []
        for file_name, fragments in results.items():
            for fragment in fragments:
                all_fragments_with_source.append((fragment, file_name))

        all_fragments_with_source.sort(key=lambda x: x[0].confidence_score, reverse=True)
        limited_fragments = all_fragments_with_source[:max_total]

        new_results = {}
        for fragment, file_name in limited_fragments:
            if file_name not in new_results:
                new_results[file_name] = []
            new_results[file_name].append(fragment)

        return new_results
