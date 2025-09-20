"""
Interfejs zarządzania plikami i strukturą danych
Mały plik interfejsowy – implementacja w file_operations.py
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, List, Union

from ..core.types import TranscriptData, ProcessedStatement

logger = logging.getLogger(__name__)


class FileManagerInterface:
    """
    Interfejs do zarządzania plikami i strukturą danych

    Odpowiada za:
    - Strukturę katalogów projektu
    - Zapis/odczyt plików JSON
    - Zarządzanie metadanymi plików
    - Organizację danych według kadencji i posiedzeń
    """

    def __init__(self, base_dir: Optional[str] = None):
        """
        Inicjalizuje manager plików

        Args:
            base_dir: katalog bazowy (opcjonalny, pobierze z konfiguracji)
        """
        # Import implementacji dopiero tutaj aby uniknąć circular imports
        from .file_operations import FileOperationsImpl
        from .data_serializers import DataSerializersImpl

        self.operations = FileOperationsImpl(base_dir)
        self.serializers = DataSerializersImpl()

        logger.debug(f"Zainicjalizowano manager plików: {self.operations.get_base_directory()}")

    # === STRUKTURA KATALOGÓW ===

    def get_base_directory(self) -> Path:
        """
        Zwraca katalog bazowy projektu

        Returns:
            Path do katalogu bazowego
        """
        return self.operations.get_base_directory()

    def get_term_directory(self, term: int) -> Path:
        """
        Zwraca katalog kadencji

        Args:
            term: numer kadencji

        Returns:
            Path do katalogu kadencji
        """
        return self.operations.get_term_directory(term)

    def get_proceeding_directory(self, term: int, proceeding_id: int,
                                 proceeding_info: Optional[Dict] = None) -> Path:
        """
        Zwraca katalog posiedzenia

        Args:
            term: numer kadencji
            proceeding_id: ID posiedzenia
            proceeding_info: informacje o posiedzeniu (opcjonalne)

        Returns:
            Path do katalogu posiedzenia
        """
        return self.operations.get_proceeding_directory(term, proceeding_id, proceeding_info or {})

    def get_transcripts_directory(self, term: int, proceeding_id: int,
                                  proceeding_info: Optional[Dict] = None) -> Path:
        """
        Zwraca katalog transkryptów

        Args:
            term: numer kadencji
            proceeding_id: ID posiedzenia
            proceeding_info: informacje o posiedzeniu (opcjonalne)

        Returns:
            Path do katalogu transkryptów
        """
        return self.operations.get_transcripts_directory(term, proceeding_id, proceeding_info or {})

    def ensure_directory_structure(self, term: int) -> bool:
        """
        Zapewnia strukturę katalogów dla kadencji

        Args:
            term: numer kadencji

        Returns:
            True, jeśli sukces
        """
        try:
            base_dir = self.get_base_directory()
            term_dir = self.get_term_directory(term)

            # Utwórz strukturę katalogów
            directories = [
                base_dir,
                term_dir,
                term_dir / "stenogramy",
                term_dir / "poslowie",
                term_dir / "kluby",
                base_dir / "cache",
                base_dir / "temp",
                base_dir / "logs"
            ]

            for directory in directories:
                directory.mkdir(parents=True, exist_ok=True)

            logger.debug(f"Zapewniono strukturę katalogów dla kadencji {term}")
            return True

        except Exception as e:
            logger.error(f"Błąd tworzenia struktury katalogów: {e}")
            return False

    # === OPERACJE NA TRANSKRYPTACH ===

    def save_proceeding_transcripts(self, term: int, proceeding_id: int, date: str,
                                    statements_data: Dict, proceeding_info: Dict,
                                    full_statements: Optional[List[ProcessedStatement]] = None) -> Optional[str]:
        """
        Zapisuje transkrypty z danego dnia posiedzenia

        Args:
            term: numer kadencji
            proceeding_id: ID posiedzenia
            date: data w formacie YYYY-MM-DD
            statements_data: podstawowe dane z API
            proceeding_info: informacje o posiedzeniu
            full_statements: wzbogacone wypowiedzi (opcjonalne)

        Returns:
            Ścieżka do zapisanego pliku lub None w przypadku błędu
        """
        logger.debug(f"Zapisywanie transkryptów {term}/{proceeding_id}/{date}")

        try:
            return self.operations.save_proceeding_transcripts(
                term, proceeding_id, date, statements_data, proceeding_info, full_statements
            )
        except Exception as e:
            logger.error(f"Błąd zapisywania transkryptów: {e}")
            return None

    def load_transcript_file(self, filepath: Union[str, Path]) -> Optional[TranscriptData]:
        """
        Ładuje plik transkryptu

        Args:
            filepath: ścieżka do pliku

        Returns:
            Dane transkryptu lub None
        """
        try:
            data = self.serializers.load_json(filepath)
            if data:
                logger.debug(f"Załadowano transkrypt z: {filepath}")
            return data
        except Exception as e:
            logger.error(f"Błąd ładowania transkryptu {filepath}: {e}")
            return None

    def get_existing_transcripts(self, term: int, proceeding_id: int,
                                 proceeding_info: Optional[Dict] = None) -> List[str]:
        """
        Zwraca listę dat z istniejącymi transkryptami

        Args:
            term: numer kadencji
            proceeding_id: ID posiedzenia
            proceeding_info: informacje o posiedzeniu (opcjonalne)

        Returns:
            Lista dat w formacie YYYY-MM-DD
        """
        try:
            # Bezpieczne wywołanie - sprawdź czy metoda istnieje
            if hasattr(self.operations, 'get_existing_transcripts'):
                return self.operations.get_existing_transcripts(term, proceeding_id, proceeding_info or {})
            else:
                # Fallback - implementuj lokalnie
                transcripts_dir = self.get_transcripts_directory(term, proceeding_id, proceeding_info)
                if not transcripts_dir.exists():
                    return []

                existing_dates = []
                for transcript_file in transcripts_dir.glob("transkrypty_*.json"):
                    # Wyciągnij datę z nazwy pliku
                    filename = transcript_file.stem  # transkrypty_2023-01-15
                    date_part = filename.replace("transkrypty_", "")
                    if len(date_part) == 10:  # YYYY-MM-DD
                        existing_dates.append(date_part)

                return sorted(existing_dates)

        except Exception as e:
            logger.error(f"Błąd pobierania istniejących transkryptów: {e}")
            return []

    def get_transcript_file_path(self, term: int, proceeding_id: int, date: str,
                                 proceeding_info: Optional[Dict] = None) -> Path:
        """
        Zwraca ścieżkę do pliku transkryptu

        Args:
            term: numer kadencji
            proceeding_id: ID posiedzenia
            date: data
            proceeding_info: informacje o posiedzeniu (opcjonalne)

        Returns:
            Path do pliku transkryptu
        """
        transcripts_dir = self.get_transcripts_directory(term, proceeding_id, proceeding_info)
        return transcripts_dir / f"transkrypty_{date}.json"

    # === OPERACJE NA POSIEDZENIACH ===

    def save_proceeding_info(self, term: int, proceeding_id: int, proceeding_info: Dict) -> Optional[str]:
        """
        Zapisuje informacje o posiedzeniu

        Args:
            term: numer kadencji
            proceeding_id: ID posiedzenia
            proceeding_info: dane posiedzenia

        Returns:
            Ścieżka do zapisanego pliku lub None
        """
        logger.debug(f"Zapisywanie informacji o posiedzeniu {term}/{proceeding_id}")

        try:
            # Bezpieczne wywołanie - sprawdź czy metoda istnieje
            if hasattr(self.operations, 'save_proceeding_info'):
                return self.operations.save_proceeding_info(term, proceeding_id, proceeding_info)
            else:
                # Fallback - implementuj lokalnie
                proceeding_dir = self.get_proceeding_directory(term, proceeding_id, proceeding_info)
                proceeding_dir.mkdir(parents=True, exist_ok=True)

                info_file = proceeding_dir / "info_posiedzenia.json"

                # Dodaj metadane
                save_data = {
                    'metadata': {
                        'saved_at': datetime.now().isoformat(),
                        'term': term,
                        'proceeding_id': proceeding_id
                    },
                    'data': proceeding_info
                }

                if self.serializers.save_json(info_file, save_data):
                    return str(info_file)
                return None

        except Exception as e:
            logger.error(f"Błąd zapisywania informacji o posiedzeniu: {e}")
            return None

    def load_proceeding_info(self, term: int, proceeding_id: int,
                             proceeding_info: Optional[Dict] = None) -> Optional[Dict]:
        """
        Ładuje informacje o posiedzeniu

        Args:
            term: numer kadencji
            proceeding_id: ID posiedzenia
            proceeding_info: bazowe info dla ścieżki (opcjonalne)

        Returns:
            Dane posiedzenia lub None
        """
        try:
            proceeding_dir = self.get_proceeding_directory(term, proceeding_id, proceeding_info)
            info_file = proceeding_dir / "info_posiedzenia.json"

            if info_file.exists():
                data = self.serializers.load_json(info_file)
                # Jeśli dane mają strukturę z metadata, zwróć tylko data część
                if isinstance(data, dict) and 'data' in data and 'metadata' in data:
                    return data['data']
                return data
            return None

        except Exception as e:
            logger.error(f"Błąd ładowania informacji o posiedzeniu: {e}")
            return None

    # === OPERACJE NA POSŁACH ===

    def save_mp_data(self, term: int, data: Union[List[Dict], Dict],
                     filename: Optional[str] = None) -> Optional[str]:
        """
        Zapisuje dane posłów

        Args:
            term: numer kadencji
            data: dane do zapisania
            filename: nazwa pliku (opcjonalna)

        Returns:
            Ścieżka do zapisanego pliku lub None
        """
        logger.debug(f"Zapisywanie danych posłów kadencji {term}")

        try:
            term_dir = self.get_term_directory(term)
            mp_dir = term_dir / "poslowie"
            mp_dir.mkdir(parents=True, exist_ok=True)

            if filename is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"poslowie_{term}_{timestamp}.json"

            filepath = mp_dir / filename

            # Dodaj metadane
            save_data = {
                "metadata": {
                    "term": term,
                    "generated_at": datetime.now().isoformat(),
                    "data_type": "mp_data"
                },
                "data": data
            }

            if self.serializers.save_json(filepath, save_data):
                logger.info(f"Zapisano dane posłów: {filepath}")
                return str(filepath)
            return None

        except Exception as e:
            logger.error(f"Błąd zapisywania danych posłów: {e}")
            return None

    def load_mp_data(self, term: int, filename: Optional[str] = None) -> Optional[Dict]:
        """
        Ładuje dane posłów

        Args:
            term: numer kadencji
            filename: nazwa pliku (opcjonalna, znajdzie najnowszy)

        Returns:
            Dane posłów lub None
        """
        try:
            term_dir = self.get_term_directory(term)
            mp_dir = term_dir / "poslowie"

            if not mp_dir.exists():
                return None

            if filename:
                filepath = mp_dir / filename
                if filepath.exists():
                    data = self.serializers.load_json(filepath)
                    # Jeśli dane mają strukturę z metadata, zwróć tylko data część
                    if isinstance(data, dict) and 'data' in data and 'metadata' in data:
                        return data['data']
                    return data
            else:
                # Znajdź najnowszy plik
                mp_files = list(mp_dir.glob("poslowie_*.json"))
                if mp_files:
                    latest_file = max(mp_files, key=lambda p: p.stat().st_mtime)
                    data = self.serializers.load_json(latest_file)
                    if isinstance(data, dict) and 'data' in data and 'metadata' in data:
                        return data['data']
                    return data

            return None

        except Exception as e:
            logger.error(f"Błąd ładowania danych posłów: {e}")
            return None

    # === OPERACJE OGÓLNE ===

    def save_json(self, path: Union[str, Path], data: Dict, add_metadata: bool = True) -> bool:
        """
        Zapisuje dane JSON z opcjonalnymi metadanymi

        Args:
            path: ścieżka do pliku
            data: dane do zapisania
            add_metadata: czy dodać metadane

        Returns:
            True, jeśli sukces
        """
        try:
            if add_metadata and isinstance(data, dict) and 'metadata' not in data:
                save_data = {
                    "metadata": {
                        "generated_at": datetime.now().isoformat(),
                        "scraper_version": "3.0"
                    },
                    "data": data
                }
            else:
                save_data = data

            return self.serializers.save_json(path, save_data)

        except Exception as e:
            logger.error(f"Błąd zapisywania JSON {path}: {e}")
            return False

    def load_json(self, path: Union[str, Path]) -> Optional[Dict]:
        """
        Ładuje dane JSON

        Args:
            path: ścieżka do pliku

        Returns:
            Dane JSON lub None
        """
        try:
            return self.serializers.load_json(path)
        except Exception as e:
            logger.error(f"Błąd ładowania JSON {path}: {e}")
            return None

    @staticmethod
    def file_exists(path: Union[str, Path]) -> bool:
        """Sprawdza, czy plik istnieje"""
        return Path(path).exists()

    @staticmethod
    def get_file_size(path: Union[str, Path]) -> Optional[int]:
        """
        Zwraca rozmiar pliku w bajtach

        Args:
            path: ścieżka do pliku

        Returns:
            Rozmiar w bajtach lub None
        """
        try:
            return Path(path).stat().st_size
        except Exception:
            return None

    @staticmethod
    def delete_file(path: Union[str, Path]) -> bool:
        """
        Usuwa plik

        Args:
            path: ścieżka do pliku

        Returns:
            True, jeśli sukces
        """
        try:
            Path(path).unlink()
            logger.debug(f"Usunięto plik: {path}")
            return True
        except Exception as e:
            logger.error(f"Błąd usuwania pliku {path}: {e}")
            return False

    # === PODSUMOWANIA I STATYSTYKI ===

    def get_proceeding_summary(self, term: int, proceeding_id: int,
                               proceeding_info: Optional[Dict] = None) -> Dict:
        """
        Tworzy podsumowanie posiedzenia

        Args:
            term: numer kadencji
            proceeding_id: ID posiedzenia
            proceeding_info: informacje o posiedzeniu (opcjonalne)

        Returns:
            Słownik z podsumowaniem
        """
        try:
            # Bezpieczne wywołanie - sprawdź czy metoda istnieje
            if hasattr(self.operations, 'get_proceeding_summary'):
                return self.operations.get_proceeding_summary(term, proceeding_id, proceeding_info or {})
            else:
                # Fallback - implementuj lokalnie
                summary = {
                    "term": term,
                    "proceeding_id": proceeding_id,
                    "generated_at": datetime.now().isoformat(),
                    "transcript_files": 0,
                    "total_statements": 0
                }

                try:
                    # Sprawdź czy istnieje katalog transkryptów
                    transcripts_dir = self.get_transcripts_directory(term, proceeding_id, proceeding_info)
                    if transcripts_dir.exists():
                        transcript_files = list(transcripts_dir.glob("transkrypty_*.json"))
                        summary["transcript_files"] = len(transcript_files)

                        # Policz wypowiedzi
                        total_statements = 0
                        for transcript_file in transcript_files:
                            transcript_data = self.load_transcript_file(transcript_file)
                            if transcript_data and isinstance(transcript_data, dict):
                                # Sprawdź różne możliwe struktury danych
                                if 'data' in transcript_data:
                                    statements = transcript_data['data'].get('statements', [])
                                elif 'statements' in transcript_data:
                                    statements = transcript_data['statements']
                                else:
                                    statements = []

                                total_statements += len(statements)

                        summary["total_statements"] = total_statements
                except Exception as inner_e:
                    logger.debug(f"Błąd w fallback implementacji: {inner_e}")

                return summary

        except Exception as e:
            logger.error(f"Błąd tworzenia podsumowania posiedzenia: {e}")
            return {"error": str(e)}

    def get_term_summary(self, term: int) -> Dict:
        """
        Tworzy podsumowanie kadencji

        Args:
            term: numer kadencji

        Returns:
            Słownik z podsumowaniem
        """
        try:
            term_dir = self.get_term_directory(term)

            summary = {
                "term": term,
                "term_directory": str(term_dir),
                "generated_at": datetime.now().isoformat(),
                "proceedings": 0,
                "transcripts": 0,
                "total_statements": 0,
                "mps_data_files": 0,
                "clubs_data_files": 0,
                "total_size_mb": 0
            }

            if term_dir.exists():
                # Policz posiedzenia
                proceeding_dirs = [d for d in term_dir.iterdir() if d.is_dir() and d.name.startswith("posiedzenie_")]
                summary["proceedings"] = len(proceeding_dirs)

                # Policz transkrypty i wypowiedzi
                total_statements = 0
                total_transcripts = 0

                for proc_dir in proceeding_dirs:
                    transcripts_dir = proc_dir / "transcripts"
                    if transcripts_dir.exists():
                        transcript_files = list(transcripts_dir.glob("transkrypty_*.json"))
                        total_transcripts += len(transcript_files)

                        for transcript_file in transcript_files:
                            transcript_data = self.load_transcript_file(transcript_file)
                            if transcript_data:
                                # Sprawdź różne możliwe struktury danych
                                if isinstance(transcript_data, dict):
                                    if 'data' in transcript_data and 'statements' in transcript_data['data']:
                                        statements = transcript_data['data']['statements']
                                    elif 'statements' in transcript_data:
                                        statements = transcript_data['statements']
                                    else:
                                        statements = []

                                    total_statements += len(statements)

                summary["transcripts"] = total_transcripts
                summary["total_statements"] = total_statements

                # Policz pliki posłów i klubów
                mp_dir = term_dir / "poslowie"
                if mp_dir.exists():
                    summary["mps_data_files"] = len(list(mp_dir.glob("*.json")))

                clubs_dir = term_dir / "kluby"
                if clubs_dir.exists():
                    summary["clubs_data_files"] = len(list(clubs_dir.glob("*.json")))

                # Oblicz całkowity rozmiar
                def get_dir_size(directory):
                    return sum(f.stat().st_size for f in directory.rglob('*') if f.is_file())

                summary["total_size_mb"] = round(get_dir_size(term_dir) / (1024 * 1024), 2)

            return summary

        except Exception as e:
            logger.error(f"Błąd tworzenia podsumowania kadencji {term}: {e}")
            return {"error": str(e)}

    def cleanup_temp_files(self) -> int:
        """
        Czyści pliki tymczasowe

        Returns:
            Liczba usuniętych plików
        """
        try:
            temp_dir = self.get_base_directory() / "temp"
            if not temp_dir.exists():
                return 0

            removed = 0
            for temp_file in temp_dir.rglob("*"):
                if temp_file.is_file():
                    try:
                        temp_file.unlink()
                        removed += 1
                    except Exception:
                        pass

            logger.info(f"Usunięto {removed} plików tymczasowych")
            return removed

        except Exception as e:
            logger.error(f"Błąd czyszczenia plików tymczasowych: {e}")
            return 0

    # === DODATKOWE METODY POMOCNICZE ===

    def create_backup(self, term: int, backup_name: Optional[str] = None) -> Optional[str]:
        """
        Tworzy kopię zapasową danych kadencji

        Args:
            term: numer kadencji
            backup_name: nazwa kopii zapasowej (opcjonalna)

        Returns:
            Ścieżka do kopii zapasowej lub None
        """
        try:
            import shutil

            term_dir = self.get_term_directory(term)
            if not term_dir.exists():
                return None

            base_dir = self.get_base_directory()
            backup_dir = base_dir / "backups"
            backup_dir.mkdir(exist_ok=True)

            if backup_name is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_name = f"kadencja_{term:02d}_backup_{timestamp}"

            backup_path = backup_dir / backup_name

            shutil.copytree(term_dir, backup_path)

            logger.info(f"Utworzono kopię zapasową: {backup_path}")
            return str(backup_path)

        except Exception as e:
            logger.error(f"Błąd tworzenia kopii zapasowej: {e}")
            return None

    def restore_backup(self, backup_path: str, term: int) -> bool:
        """
        Przywraca kopię zapasową danych kadencji

        Args:
            backup_path: ścieżka do kopii zapasowej
            term: numer kadencji do przywrócenia

        Returns:
            True jeśli sukces
        """
        try:
            import shutil

            backup_dir = Path(backup_path)
            if not backup_dir.exists():
                logger.error(f"Kopia zapasowa nie istnieje: {backup_path}")
                return False

            term_dir = self.get_term_directory(term)

            # Usuń istniejący katalog kadencji jeśli istnieje
            if term_dir.exists():
                shutil.rmtree(term_dir)

            # Przywróć z kopii
            shutil.copytree(backup_dir, term_dir)

            logger.info(f"Przywrócono kopię zapasową: {backup_path} -> {term_dir}")
            return True

        except Exception as e:
            logger.error(f"Błąd przywracania kopii zapasowej: {e}")
            return False

    def export_term_data(self, term: int, export_format: str = "json") -> Optional[str]:
        """
        Eksportuje dane kadencji do określonego formatu

        Args:
            term: numer kadencji
            export_format: format eksportu (json, csv)

        Returns:
            Ścieżka do pliku eksportu lub None
        """
        try:
            term_dir = self.get_term_directory(term)
            if not term_dir.exists():
                return None

            base_dir = self.get_base_directory()
            export_dir = base_dir / "exports"
            export_dir.mkdir(exist_ok=True)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

            if export_format.lower() == "json":
                export_file = export_dir / f"kadencja_{term:02d}_export_{timestamp}.json"

                # Zbierz wszystkie dane w jeden słownik
                export_data = {
                    "term": term,
                    "export_timestamp": timestamp,
                    "proceedings": []
                }

                # Przejdź przez wszystkie posiedzenia
                for proc_dir in term_dir.glob("posiedzenie_*"):
                    if proc_dir.is_dir():
                        proceeding_data = {
                            "directory_name": proc_dir.name,
                            "transcripts": []
                        }

                        # Ładuj informacje o posiedzeniu
                        info_file = proc_dir / "info_posiedzenia.json"
                        if info_file.exists():
                            proceeding_info = self.serializers.load_json(info_file)
                            proceeding_data["info"] = proceeding_info

                        # Ładuj wszystkie transkrypty
                        transcripts_dir = proc_dir / "transcripts"
                        if transcripts_dir.exists():
                            for transcript_file in transcripts_dir.glob("transkrypty_*.json"):
                                transcript_data = self.serializers.load_json(transcript_file)
                                if transcript_data:
                                    proceeding_data["transcripts"].append(transcript_data)

                        export_data["proceedings"].append(proceeding_data)

                # Zapisz do pliku JSON
                if self.serializers.save_json(export_file, export_data):
                    return str(export_file)

            elif export_format.lower() == "csv":
                export_file = export_dir / f"kadencja_{term:02d}_statements_{timestamp}.csv"

                # Zbierz wszystkie wypowiedzi w listę
                all_statements = []

                for proc_dir in term_dir.glob("posiedzenie_*"):
                    if proc_dir.is_dir():
                        transcripts_dir = proc_dir / "transcripts"
                        if transcripts_dir.exists():
                            for transcript_file in transcripts_dir.glob("transkrypty_*.json"):
                                transcript_data = self.serializers.load_json(transcript_file)
                                if transcript_data and 'statements' in transcript_data:
                                    for stmt in transcript_data['statements']:
                                        csv_row = {
                                            'term': term,
                                            'proceeding_dir': proc_dir.name,
                                            'date': transcript_data.get('metadata', {}).get('date', ''),
                                            'statement_num': stmt.get('num', ''),
                                            'speaker_name': stmt.get('speaker', {}).get('name', ''),
                                            'speaker_function': stmt.get('speaker', {}).get('function', ''),
                                            'speaker_club': stmt.get('speaker', {}).get('club', ''),
                                            'start_time': stmt.get('timing', {}).get('start_datetime', ''),
                                            'end_time': stmt.get('timing', {}).get('end_datetime', ''),
                                            'duration_seconds': stmt.get('timing', {}).get('duration_seconds', ''),
                                            'has_full_content': stmt.get('content', {}).get('has_full_content', False),
                                            'content_preview': (stmt.get('content', {}).get('text', '')[:100] + '...'
                                                                if len(stmt.get('content', {}).get('text', '')) > 100
                                                                else stmt.get('content', {}).get('text', ''))
                                        }
                                        all_statements.append(csv_row)

                # Zapisz do CSV
                if all_statements and self.serializers.save_csv(export_file, all_statements):
                    return str(export_file)

            return None

        except Exception as e:
            logger.error(f"Błąd eksportu danych kadencji {term}: {e}")
            return None

    def __repr__(self) -> str:
        """Reprezentacja string obiektu"""
        return f"FileManagerInterface(base_dir={self.get_base_directory()})"
