"""
Moduł do eksportu danych do formatów JSON
"""
import json
from pathlib import Path
from typing import List, Dict

from SejmBotDetektor.logging.logger import get_module_logger
from SejmBotDetektor.models.funny_fragment import FunnyFragment


class JsonExporter:
    """Klasa odpowiedzialna za eksport danych do formatu JSON"""

    def __init__(self, debug: bool = False):
        self.logger = get_module_logger("JsonExporter")
        self.debug = debug

    def export_fragments(self, fragments: List[FunnyFragment], output_file: str) -> bool:
        """
        Eksportuje fragmenty do pliku JSON w prostym formacie

        Args:
            fragments: Lista fragmentów do zapisania
            output_file: Ścieżka do pliku wyjściowego

        Returns:
            True jeśli eksport się powiódł
        """
        try:
            # Przygotowujemy dane z metadanymi
            export_data = {
                "metadata": {
                    "total_fragments": len(fragments),
                    "export_format": "simple",
                    "version": "1.0"
                },
                "fragments": [fragment.to_dict() for fragment in fragments]
            }

            self._write_json_file(export_data, output_file)

            self.logger.info(f"Wyeksportowano {len(fragments)} fragmentów do {output_file}")
            return True

        except Exception as e:
            self.logger.error(f"Błąd podczas eksportu fragmentów do JSON: {e}")
            return False

    def export_folder_results(self, results: Dict[str, List[FunnyFragment]], output_file: str) -> bool:
        """
        Eksportuje wyniki z wielu plików do JSON z zachowaniem struktury

        Args:
            results: Słownik {nazwa_pliku: lista_fragmentów}
            output_file: Ścieżka do pliku wyjściowego

        Returns:
            True jeśli eksport się powiódł
        """
        try:
            total_fragments = sum(len(fragments) for fragments in results.values())

            # Struktura danych dla wyników z folderu
            export_data = {
                "metadata": {
                    "total_files": len(results),
                    "total_fragments": total_fragments,
                    "export_format": "folder_structure",
                    "version": "1.0",
                    "files_processed": list(results.keys())
                },
                "files": {}
            }

            # Dodajemy fragmenty dla każdego pliku z podstawowymi statystykami
            for file_name, fragments in results.items():
                file_stats = self._calculate_file_stats(fragments)
                export_data["files"][file_name] = {
                    "stats": file_stats,
                    "fragments": [fragment.to_dict() for fragment in fragments]
                }

            self._write_json_file(export_data, output_file)

            self.logger.info(
                f"Wyeksportowano wyniki z {len(results)} plików ({total_fragments} fragmentów) do {output_file}")
            return True

        except Exception as e:
            self.logger.error(f"Błąd podczas eksportu wyników folderu do JSON: {e}")
            return False

    def load_fragments(self, input_file: str) -> List[FunnyFragment]:
        """
        Wczytuje fragmenty z pliku JSON (obsługuje różne formaty)

        Args:
            input_file: Ścieżka do pliku JSON

        Returns:
            Lista fragmentów lub pusta lista w przypadku błędu
        """
        try:
            with open(input_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            fragments = []

            # Obsługujemy różne formaty JSON
            if isinstance(data, list):
                # Stary format - lista fragmentów
                fragments = [FunnyFragment.from_dict(item) for item in data]

            elif isinstance(data, dict):
                if "fragments" in data:
                    # Nowy format z metadanymi
                    fragments = [FunnyFragment.from_dict(item) for item in data["fragments"]]

                elif "files" in data:
                    # Format z wynikami z folderu
                    for file_data in data["files"].values():
                        if "fragments" in file_data:
                            fragments.extend([FunnyFragment.from_dict(item) for item in file_data["fragments"]])

            if self.debug:
                self.logger.debug(f"Wczytano {len(fragments)} fragmentów z {input_file}")

            return fragments

        except FileNotFoundError:
            self.logger.error(f"Plik {input_file} nie został znaleziony")
            return []
        except json.JSONDecodeError as e:
            self.logger.error(f"Błąd parsowania JSON w pliku {input_file}: {e}")
            return []
        except Exception as e:
            self.logger.error(f"Błąd podczas wczytywania z {input_file}: {e}")
            return []

    def _write_json_file(self, data: dict, output_file: str) -> None:
        """Zapisuje dane do pliku JSON z odpowiednim formatowaniem"""
        # Upewniamy się że folder docelowy istnieje
        Path(output_file).parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        if self.debug:
            self.logger.debug(f"Pomyślnie zapisano plik JSON: {output_file}")

    def _calculate_file_stats(self, fragments: List[FunnyFragment]) -> dict:
        """Oblicza podstawowe statystyki dla pliku"""
        if not fragments:
            return {
                "fragment_count": 0,
                "avg_confidence": 0.0,
                "max_confidence": 0.0,
                "min_confidence": 0.0
            }

        confidences = [f.confidence_score for f in fragments]

        return {
            "fragment_count": len(fragments),
            "avg_confidence": round(sum(confidences) / len(confidences), 3),
            "max_confidence": round(max(confidences), 3),
            "min_confidence": round(min(confidences), 3)
        }
