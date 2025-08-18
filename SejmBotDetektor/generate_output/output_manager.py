"""
Główny moduł do zarządzania eksportem wyników
Koordynuje pracę wszystkich eksporterów i generatorów
"""
import os
from pathlib import Path
from typing import List, Dict

from SejmBotDetektor.generate_output.console_printer import ConsolePrinter
from SejmBotDetektor.generate_output.csv_exporter import CsvExporter
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

        # Inicjalizujemy wszystkie komponenty
        self.json_exporter = JsonExporter(debug)
        self.csv_exporter = CsvExporter(debug)
        self.html_generator = HtmlGenerator(debug)
        self.console_printer = ConsolePrinter(debug)

        # Zapewniamy istnienie folderu output
        self._ensure_output_folder()

        self.generated_files = []  # Lista wygenerowanych plików

    def export_fragments(self, fragments: List[FunnyFragment], base_filename: str = "funny_fragments") -> bool:
        """
        Eksportuje fragmenty do wszystkich dostępnych formatów

        Args:
            fragments: Lista fragmentów do eksportu
            base_filename: Bazowa nazwa pliku (bez rozszerzenia)

        Returns:
            True jeśli wszystkie eksporty się powiodły
        """
        if not fragments:
            self.logger.warning("Brak fragmentów do eksportu")
            return False

        success_count = 0
        total_exports = 3  # JSON, CSV, HTML

        # JSON
        json_path = self._get_output_path(f"{base_filename}.json")
        if self.json_exporter.export_fragments(fragments, json_path):
            self.generated_files.append(json_path)
            success_count += 1

        # CSV
        csv_path = self._get_output_path(f"{base_filename}.csv")
        if self.csv_exporter.export_fragments(fragments, csv_path):
            self.generated_files.append(csv_path)
            success_count += 1

        # HTML
        html_path = self._get_output_path(f"{base_filename}_report.html")
        if self.html_generator.generate_report(fragments, html_path):
            self.generated_files.append(html_path)
            success_count += 1

        # Podsumowanie
        if success_count == total_exports:
            self.logger.success(f"Wszystkie formaty eksportu zakończone pomyślnie")
            return True
        elif success_count > 0:
            self.logger.warning(f"Zakończono {success_count}/{total_exports} eksportów")
            return True
        else:
            self.logger.error("Wszystkie eksporty nie powiodły się")
            return False

    def export_folder_results(self, results: Dict[str, List[FunnyFragment]],
                              base_filename: str = "folder_results") -> bool:
        """
        Eksportuje wyniki z wielu plików do wszystkich formatów

        Args:
            results: Słownik {nazwa_pliku: lista_fragmentów}
            base_filename: Bazowa nazwa pliku

        Returns:
            True jeśli eksporty się powiodły
        """
        if not results:
            self.logger.warning("Brak wyników do eksportu")
            return False

        success_count = 0
        total_exports = 3

        # JSON ze strukturą folderu
        json_path = self._get_output_path(f"{base_filename}.json")
        if self.json_exporter.export_folder_results(results, json_path):
            self.generated_files.append(json_path)
            success_count += 1

        # CSV ze wszystkimi fragmentami
        csv_path = self._get_output_path(f"{base_filename}.csv")
        if self.csv_exporter.export_folder_results(results, csv_path):
            self.generated_files.append(csv_path)
            success_count += 1

        # HTML raport folderu
        html_path = self._get_output_path(f"{base_filename}_report.html")
        if self.html_generator.generate_folder_report(results, html_path):
            self.generated_files.append(html_path)
            success_count += 1

        # Dodatkowo: eksportujemy każdy plik osobno (tylko JSON, żeby nie zaśmiecać)
        if self.debug:
            self._export_individual_files(results)

        return success_count > 0

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

    def _export_individual_files(self, results: Dict[str, List[FunnyFragment]]):
        """Eksportuje każdy plik osobno (tylko w trybie debug)"""
        self.logger.info("Eksport indywidualnych plików (tryb debug)...")

        for file_name, fragments in results.items():
            if fragments:
                # Czyścimy nazwę pliku
                clean_name = Path(file_name).stem
                individual_path = self._get_output_path(f"individual_{clean_name}.json")

                if self.json_exporter.export_fragments(fragments, individual_path):
                    self.generated_files.append(individual_path)
                    if self.debug:
                        self.logger.debug(f"Wyeksportowano {len(fragments)} fragmentów z {file_name}")

    def _count_total_fragments(self) -> int:
        """Próbuje policzyć łączną liczbę fragmentów z metadanych"""
        # To jest przybliżona wartość - w prawdziwej implementacji
        # moglibyśmy przechowywać tę informację
        return 0

    # Metody kompatybilności z poprzednim API (deprecated)
    def save_fragments_to_json(self, fragments: List[FunnyFragment], output_file: str) -> bool:
        """Metoda kompatybilności - użyj export_fragments()"""
        self.logger.warning("save_fragments_to_json jest deprecated - użyj export_fragments()")
        return self.json_exporter.export_fragments(fragments, output_file)

    def generate_html_report(self, fragments: List[FunnyFragment], output_file: str = "report.html") -> bool:
        """Metoda kompatybilności - użyj export_fragments()"""
        self.logger.warning("generate_html_report jest deprecated - użyj export_fragments()")
        return self.html_generator.generate_report(fragments, output_file)

    def export_fragments_to_csv(self, fragments: List[FunnyFragment], output_file: str) -> bool:
        """Metoda kompatybilności - użyj export_fragments()"""
        self.logger.warning("export_fragments_to_csv jest deprecated - użyj export_fragments()")
        return self.csv_exporter.export_fragments(fragments, output_file)

    def print_fragments(self, fragments: List[FunnyFragment], max_fragments: int = 10):
        """Metoda kompatybilności - użyj print_results()"""
        self.logger.warning("print_fragments jest deprecated - użyj print_results()")
        self.print_results(fragments, max_fragments)
