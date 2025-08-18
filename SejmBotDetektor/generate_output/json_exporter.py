"""
Moduł do eksportu danych do formatów JSON
Nowa wersja przygotowana pod integrację z OpenAI API
"""
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Union

from SejmBotDetektor.logging.logger import get_module_logger
from SejmBotDetektor.models.funny_fragment import FunnyFragment


class JsonExporter:
    """Klasa odpowiedzialna za eksport danych do formatu JSON kompatybilnego z OpenAI API"""

    def __init__(self, debug: bool = False):
        self.logger = get_module_logger("JsonExporter")
        self.debug = debug

    def export_ai_ready_format(self,
                               fragments_data: Union[List[FunnyFragment], Dict[str, List[FunnyFragment]]],
                               output_file: str,
                               export_type: str = "single_file",
                               config: Dict = None) -> bool:
        """
        Eksportuje fragmenty w formacie gotowym pod OpenAI API

        Args:
            fragments_data: Lista fragmentów lub słownik {nazwa_pliku: lista_fragmentów}
            output_file: Ścieżka do pliku wyjściowego
            export_type: "single_file" lub "batch_processing"
            config: Opcjonalna konfiguracja

        Returns:
            True jeśli eksport się powiódł
        """
        try:
            # Przygotowujemy fragmenty do eksportu
            if isinstance(fragments_data, dict):
                # Przypadek batch processing
                all_fragments = []
                for file_name, fragments in fragments_data.items():
                    for fragment in fragments:
                        all_fragments.append(self._prepare_fragment_for_ai(fragment, file_name))

                export_data = self._create_batch_export_structure(all_fragments, fragments_data, config)

            else:
                # Przypadek single file
                prepared_fragments = [self._prepare_fragment_for_ai(fragment) for fragment in fragments_data]
                export_data = self._create_single_file_export_structure(prepared_fragments, config)

            self._write_json_file(export_data, output_file)

            fragment_count = len(export_data["fragments"])
            self.logger.info(f"Wyeksportowano {fragment_count} fragmentów w formacie AI-ready do {output_file}")
            return True

        except Exception as e:
            self.logger.error(f"Błąd podczas eksportu do formatu AI-ready: {e}")
            return False

    def load_fragments(self, input_file: str) -> List[FunnyFragment]:
        """
        Wczytuje fragmenty z pliku JSON (kompatybilność z nowymi i starymi formatami)

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
                fragments = [self._convert_from_dict(item) for item in data]

            elif isinstance(data, dict):
                if "fragments" in data:
                    # Nowy format AI-ready lub stary z metadanymi
                    fragments = [self._convert_from_dict(item) for item in data["fragments"]]

                elif "files" in data:
                    # Stary format z wynikami z folderu
                    for file_data in data["files"].values():
                        if "fragments" in file_data:
                            fragments.extend([self._convert_from_dict(item) for item in file_data["fragments"]])

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

    def _prepare_fragment_for_ai(self, fragment: FunnyFragment, source_file: str = None) -> dict:
        """Przygotowuje fragment w formacie AI-ready"""

        # Wyciągamy informacje o pliku źródłowym
        if source_file:
            actual_source_file = source_file
            meeting_info = fragment.meeting_info
        else:
            actual_source_file, meeting_info = self._extract_file_info(fragment.meeting_info)

        # Generujemy unikalny ID jeśli fragment go nie ma
        fragment_id = getattr(fragment, 'id', None) or str(uuid.uuid4())

        return {
            "id": fragment_id,
            "source_file": actual_source_file,
            "speaker": fragment.speaker,
            "text": fragment.text,
            "confidence_score": fragment.confidence_score,
            "keywords_found": fragment.keywords_found,
            "context": {
                "meeting_info": meeting_info,
                "position_in_text": fragment.position_in_text,
                "timestamp": fragment.timestamp
            },
            "ai_ready": {
                "prompt_context": "Fragment z polskiego parlamentu do analizy humoru",
                "classification_hints": self._generate_classification_hints(fragment),
                "processing_ready": True
            }
        }

    def _create_single_file_export_structure(self, fragments: List[dict], config: Dict = None) -> dict:
        """Tworzy strukturę eksportu dla pojedynczego pliku"""
        return {
            "metadata": {
                "export_type": "single_file",
                "total_fragments": len(fragments),
                "processing_date": datetime.now().isoformat(),
                "config": config or {},
                "ai_integration": {
                    "format_version": "1.0",
                    "openai_compatible": True,
                    "ready_for_batch_processing": True
                }
            },
            "fragments": fragments
        }

    def _create_batch_export_structure(self, all_fragments: List[dict],
                                       original_data: Dict[str, List[FunnyFragment]],
                                       config: Dict = None) -> dict:
        """Tworzy strukturę eksportu dla batch processing"""

        # Statystyki plików
        file_stats = {}
        for file_name, fragments in original_data.items():
            if fragments:
                confidences = [f.confidence_score for f in fragments]
                file_stats[file_name] = {
                    "fragment_count": len(fragments),
                    "avg_confidence": round(sum(confidences) / len(confidences), 3),
                    "max_confidence": round(max(confidences), 3),
                    "min_confidence": round(min(confidences), 3)
                }

        return {
            "metadata": {
                "export_type": "batch_processing",
                "total_files": len(original_data),
                "total_fragments": len(all_fragments),
                "processing_date": datetime.now().isoformat(),
                "config": config or {},
                "file_stats": file_stats,
                "files_processed": list(original_data.keys()),
                "ai_integration": {
                    "format_version": "1.0",
                    "openai_compatible": True,
                    "ready_for_batch_processing": True,
                    "batch_size": len(all_fragments)
                }
            },
            "fragments": all_fragments
        }

    def _generate_classification_hints(self, fragment: FunnyFragment) -> List[str]:
        """Generuje hinty klasyfikacyjne dla AI"""
        hints = ["political_humor", "parliamentary_speech"]

        # Na podstawie słów kluczowych
        high_confidence_keywords = ["śmiech", "żart", "bzdura", "cyrk", "gafa"]
        if any(keyword in fragment.keywords_found for keyword in high_confidence_keywords):
            hints.append("high_humor_potential")

        if fragment.confidence_score >= 0.7:
            hints.append("high_confidence")
        elif fragment.confidence_score >= 0.4:
            hints.append("medium_confidence")
        else:
            hints.append("low_confidence")

        # Długość tekstu
        if len(fragment.text.split()) > 50:
            hints.append("long_text")
        elif len(fragment.text.split()) < 20:
            hints.append("short_text")

        return hints

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

    def _convert_from_dict(self, data: dict) -> FunnyFragment:
        """Konwertuje dane z dictionary na FunnyFragment (kompatybilność)"""

        # Obsługa nowego formatu AI-ready
        if "context" in data:
            meeting_info = data["context"].get("meeting_info", "")
            position = data["context"].get("position_in_text", -1)
            timestamp = data["context"].get("timestamp", "")

            # Rekonstruujemy meeting_info z source_file jeśli potrzeba
            if data.get("source_file") and data["source_file"] != "nieznany":
                meeting_info = f"{meeting_info} | Plik: {data['source_file']}"

        else:
            # Stary format
            meeting_info = data.get("meeting_info", "")
            position = data.get("position_in_text", -1)
            timestamp = data.get("timestamp", "")

        # Tworzymy fragment używając FunnyFragment.from_dict jeśli istnieje
        if hasattr(FunnyFragment, 'from_dict'):
            return FunnyFragment.from_dict(data)
        else:
            # Fallback - tworzymy ręcznie
            return FunnyFragment(
                speaker=data.get("speaker", ""),
                text=data.get("text", ""),
                keywords_found=data.get("keywords_found", []),
                confidence_score=data.get("confidence_score", 0.0),
                meeting_info=meeting_info,
                position_in_text=position,
                timestamp=timestamp
            )

    def _write_json_file(self, data: dict, output_file: str) -> None:
        """Zapisuje dane do pliku JSON z odpowiednim formatowaniem"""
        # Upewniamy się że folder docelowy istnieje
        Path(output_file).parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        if self.debug:
            self.logger.debug(f"Pomyślnie zapisano plik JSON: {output_file}")

    # DEPRECATED METHODS - zachowane dla kompatybilności
    def export_fragments(self, fragments: List[FunnyFragment], output_file: str) -> bool:
        """DEPRECATED: Użyj export_ai_ready_format()"""
        self.logger.warning("export_fragments jest deprecated - użyj export_ai_ready_format()")
        return self.export_ai_ready_format(fragments, output_file, "single_file")

    def export_folder_results(self, results: Dict[str, List[FunnyFragment]], output_file: str) -> bool:
        """DEPRECATED: Użyj export_ai_ready_format()"""
        self.logger.warning("export_folder_results jest deprecated - użyj export_ai_ready_format()")
        return self.export_ai_ready_format(results, output_file, "batch_processing")
