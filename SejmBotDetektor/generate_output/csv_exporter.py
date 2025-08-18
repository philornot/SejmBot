"""
Moduł do eksportu danych do formatu CSV
"""
import csv
from pathlib import Path
from typing import List, Dict

from SejmBotDetektor.logging.logger import get_module_logger
from SejmBotDetektor.models.funny_fragment import FunnyFragment


class CsvExporter:
    """Klasa odpowiedzialna za eksport danych do formatu CSV"""

    def __init__(self, debug: bool = False):
        self.logger = get_module_logger("CsvExporter")
        self.debug = debug

    def export_fragments(self, fragments: List[FunnyFragment], output_file: str) -> bool:
        """
        Eksportuje fragmenty do pliku CSV

        Args:
            fragments: Lista fragmentów do eksportu
            output_file: Ścieżka do pliku CSV

        Returns:
            True jeśli eksport się powiódł
        """
        try:
            # Upewniamy się że folder docelowy istnieje
            Path(output_file).parent.mkdir(parents=True, exist_ok=True)

            fieldnames = [
                'source_file', 'speaker', 'confidence_score', 'keywords_found',
                'text_preview', 'position_in_text', 'meeting_info', 'timestamp'
            ]

            with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()

                for fragment in fragments:
                    source_file, meeting_info = self._extract_file_info(fragment.meeting_info)

                    writer.writerow({
                        'source_file': source_file,
                        'speaker': fragment.speaker,
                        'confidence_score': fragment.confidence_score,
                        'keywords_found': fragment.get_keywords_as_string(),
                        'text_preview': fragment.get_short_preview(150),
                        'position_in_text': fragment.position_in_text,
                        'meeting_info': meeting_info,
                        'timestamp': fragment.timestamp
                    })

            self.logger.info(f"Wyeksportowano {len(fragments)} fragmentów do {output_file}")
            return True

        except Exception as e:
            self.logger.error(f"Błąd podczas eksportu do CSV: {e}")
            return False

    def export_folder_results(self, results: Dict[str, List[FunnyFragment]], output_file: str) -> bool:
        """
        Eksportuje wyniki z wielu plików do CSV

        Args:
            results: Słownik {nazwa_pliku: lista_fragmentów}
            output_file: Ścieżka do pliku CSV

        Returns:
            True jeśli eksport się powiódł
        """
        try:
            # Upewniamy się że folder docelowy istnieje
            Path(output_file).parent.mkdir(parents=True, exist_ok=True)

            fieldnames = [
                'source_file', 'speaker', 'confidence_score', 'keywords_found',
                'text_preview', 'position_in_text', 'meeting_info', 'timestamp'
            ]

            with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()

                total_exported = 0
                for file_name, fragments in results.items():
                    for fragment in fragments:
                        _, meeting_info = self._extract_file_info(fragment.meeting_info)

                        writer.writerow({
                            'source_file': file_name,
                            'speaker': fragment.speaker,
                            'confidence_score': fragment.confidence_score,
                            'keywords_found': fragment.get_keywords_as_string(),
                            'text_preview': fragment.get_short_preview(150),
                            'position_in_text': fragment.position_in_text,
                            'meeting_info': meeting_info,
                            'timestamp': fragment.timestamp
                        })
                        total_exported += 1

            self.logger.info(f"Wyeksportowano {total_exported} fragmentów z {len(results)} plików do {output_file}")
            return True

        except Exception as e:
            self.logger.error(f"Błąd podczas eksportu wyników folderu do CSV: {e}")
            return False

    def _extract_file_info(self, meeting_info: str) -> tuple[str, str]:
        """
        Wyciąga informację o pliku źródłowym z meeting_info

        Args:
            meeting_info: String z informacją o posiedzeniu

        Returns:
            Tuple (nazwa_pliku, info_o_posiedzeniu)
        """
        if "| Plik:" in meeting_info:
            meeting_part, file_part = meeting_info.split("| Plik:", 1)
            return file_part.strip(), meeting_part.strip()
        else:
            return "nieznany", meeting_info
