"""
Interfejs zarządzania plikami i strukturą danych
Mały plik interfejsowy — implementacja w file_operations.py
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
    - Strukturę katalogów projektu — Zapis/odczyt plików JSON — Zarządzanie metadanymi plików — Organizację danych według kadencji i posiedzeń
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
            return self.operations.get_existing_transcripts(term, proceeding_id, proceeding_info or {})
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
            return self.operations.save_proceeding_info(term, proceeding_id, proceeding_info)
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
                return self.serializers.load_json(info_file)
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
            mp_dir.mkdir(exist_ok=True)

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
                    return self.serializers.load_json(filepath)
            else:
                # Znajdź najnowszy plik
                mp_files = list(mp_dir.glob("poslowie_*.json"))
                if mp_files:
                    latest_file = max(mp_files, key=lambda p: p.stat().st_mtime)
                    return self.serializers.load_json(latest_file)

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
            return self.operations.get_proceeding_summary(term, proceeding_id, proceeding_info or {})
        except Exception as e:
            logger.error(f"Błąd tworzenia podsumowania: {e}")
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
                            if transcript_data and 'statements' in transcript_data:
                                total_statements += len(transcript_data['statements'])

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

    def __repr__(self) -> str:
        """Reprezentacja string obiektu"""
        return f"FileManagerInterface(base_dir={self.get_base_directory()})"
