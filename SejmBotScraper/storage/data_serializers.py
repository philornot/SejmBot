"""
Implementacja serializacji i deserializacji danych
Obsługa formatów JSON, CSV i innych
"""

import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any, Union

logger = logging.getLogger(__name__)


class DataSerializersImpl:
    """Implementacja serializacji danych do różnych formatów"""

    def __init__(self):
        """Inicjalizuje serializer danych"""
        logger.debug("Zainicjalizowano DataSerializersImpl")

    def save_json(self, filepath: Union[str, Path], data: Any, indent: int = 2, ensure_ascii: bool = False) -> bool:
        """
        Zapisuje dane do pliku JSON

        Args:
            filepath: ścieżka do pliku
            data: dane do zapisania
            indent: wcięcia w JSON (domyślnie 2)
            ensure_ascii: czy wymuszać ASCII (domyślnie False dla UTF-8)

        Returns:
            True jeśli sukces, False w przypadku błędu
        """
        try:
            filepath = Path(filepath)

            # Upewnij się że katalog istnieje
            filepath.parent.mkdir(parents=True, exist_ok=True)

            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=ensure_ascii, indent=indent, default=self._json_serializer)

            logger.debug(f"Zapisano JSON: {filepath}")
            return True

        except Exception as e:
            logger.error(f"Błąd zapisywania JSON {filepath}: {e}")
            return False

    def load_json(self, filepath: Union[str, Path]) -> Optional[Dict]:
        """
        Ładuje dane z pliku JSON

        Args:
            filepath: ścieżka do pliku

        Returns:
            Dane JSON lub None w przypadku błędu
        """
        try:
            filepath = Path(filepath)

            if not filepath.exists():
                logger.debug(f"Plik nie istnieje: {filepath}")
                return None

            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)

            logger.debug(f"Załadowano JSON: {filepath}")
            return data

        except Exception as e:
            logger.error(f"Błąd ładowania JSON {filepath}: {e}")
            return None

    def _json_serializer(self, obj):
        """
        Niestandardowy serializer dla obiektów JSON

        Args:
            obj: obiekt do serializacji

        Returns:
            Reprezentacja serialowalnego obiektu
        """
        # Obsługa datetime
        if hasattr(obj, 'isoformat'):
            return obj.isoformat()

        # Obsługa Path
        if isinstance(obj, Path):
            return str(obj)

        # Obsługa set
        if isinstance(obj, set):
            return list(obj)

        # Inne obiekty przekonwertuj na string
        return str(obj)

    def save_csv(self, filepath: Union[str, Path], data: list, headers: Optional[list] = None) -> bool:
        """
        Zapisuje dane do pliku CSV

        Args:
            filepath: ścieżka do pliku
            data: lista słowników z danymi
            headers: nagłówki kolumn (opcjonalne)

        Returns:
            True jeśli sukces, False w przypadku błędu
        """
        try:
            import csv

            filepath = Path(filepath)
            filepath.parent.mkdir(parents=True, exist_ok=True)

            if not data:
                logger.warning(f"Brak danych do zapisania w CSV: {filepath}")
                return False

            # Jeśli nie podano nagłówków, użyj kluczy pierwszego elementu
            if headers is None and isinstance(data[0], dict):
                headers = list(data[0].keys())

            with open(filepath, 'w', newline='', encoding='utf-8') as f:
                if headers:
                    writer = csv.DictWriter(f, fieldnames=headers)
                    writer.writeheader()
                    for row in data:
                        # Upewnij się że wszystkie wartości są stringami
                        clean_row = {k: str(v) if v is not None else '' for k, v in row.items()}
                        writer.writerow(clean_row)
                else:
                    writer = csv.writer(f)
                    for row in data:
                        writer.writerow(row)

            logger.info(f"Zapisano CSV: {filepath} ({len(data)} wierszy)")
            return True

        except Exception as e:
            logger.error(f"Błąd zapisywania CSV {filepath}: {e}")
            return False

    def load_csv(self, filepath: Union[str, Path]) -> Optional[list]:
        """
        Ładuje dane z pliku CSV

        Args:
            filepath: ścieżka do pliku

        Returns:
            Lista słowników z danymi lub None w przypadku błędu
        """
        try:
            import csv

            filepath = Path(filepath)

            if not filepath.exists():
                logger.debug(f"Plik CSV nie istnieje: {filepath}")
                return None

            data = []
            with open(filepath, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    data.append(row)

            logger.debug(f"Załadowano CSV: {filepath} ({len(data)} wierszy)")
            return data

        except Exception as e:
            logger.error(f"Błąd ładowania CSV {filepath}: {e}")
            return None

    def save_text(self, filepath: Union[str, Path], text: str, encoding: str = 'utf-8') -> bool:
        """
        Zapisuje tekst do pliku

        Args:
            filepath: ścieżka do pliku
            text: treść do zapisania
            encoding: kodowanie pliku (domyślnie utf-8)

        Returns:
            True jeśli sukces, False w przypadku błędu
        """
        try:
            filepath = Path(filepath)
            filepath.parent.mkdir(parents=True, exist_ok=True)

            with open(filepath, 'w', encoding=encoding) as f:
                f.write(text)

            logger.debug(f"Zapisano tekst: {filepath}")
            return True

        except Exception as e:
            logger.error(f"Błąd zapisywania tekstu {filepath}: {e}")
            return False

    def load_text(self, filepath: Union[str, Path], encoding: str = 'utf-8') -> Optional[str]:
        """
        Ładuje tekst z pliku

        Args:
            filepath: ścieżka do pliku
            encoding: kodowanie pliku (domyślnie utf-8)

        Returns:
            Tekst z pliku lub None w przypadku błędu
        """
        try:
            filepath = Path(filepath)

            if not filepath.exists():
                logger.debug(f"Plik tekstowy nie istnieje: {filepath}")
                return None

            with open(filepath, 'r', encoding=encoding) as f:
                text = f.read()

            logger.debug(f"Załadowano tekst: {filepath}")
            return text

        except Exception as e:
            logger.error(f"Błąd ładowania tekstu {filepath}: {e}")
            return None

    def save_binary(self, filepath: Union[str, Path], data: bytes) -> bool:
        """
        Zapisuje dane binarne do pliku

        Args:
            filepath: ścieżka do pliku
            data: dane binarne

        Returns:
            True jeśli sukces, False w przypadku błędu
        """
        try:
            filepath = Path(filepath)
            filepath.parent.mkdir(parents=True, exist_ok=True)

            with open(filepath, 'wb') as f:
                f.write(data)

            logger.debug(f"Zapisano dane binarne: {filepath} ({len(data)} bajtów)")
            return True

        except Exception as e:
            logger.error(f"Błąd zapisywania danych binarnych {filepath}: {e}")
            return False

    def load_binary(self, filepath: Union[str, Path]) -> Optional[bytes]:
        """
        Ładuje dane binarne z pliku

        Args:
            filepath: ścieżka do pliku

        Returns:
            Dane binarne lub None w przypadku błędu
        """
        try:
            filepath = Path(filepath)

            if not filepath.exists():
                logger.debug(f"Plik binarny nie istnieje: {filepath}")
                return None

            with open(filepath, 'rb') as f:
                data = f.read()

            logger.debug(f"Załadowano dane binarne: {filepath} ({len(data)} bajtów)")
            return data

        except Exception as e:
            logger.error(f"Błąd ładowania danych binarnych {filepath}: {e}")
            return None

    def get_file_info(self, filepath: Union[str, Path]) -> Optional[Dict]:
        """
        Pobiera informacje o pliku

        Args:
            filepath: ścieżka do pliku

        Returns:
            Słownik z informacjami o pliku lub None
        """
        try:
            filepath = Path(filepath)

            if not filepath.exists():
                return None

            stat = filepath.stat()

            return {
                'name': filepath.name,
                'size_bytes': stat.st_size,
                'size_mb': round(stat.st_size / (1024 * 1024), 2),
                'modified_timestamp': stat.st_mtime,
                'created_timestamp': stat.st_ctime,
                'is_file': filepath.is_file(),
                'is_directory': filepath.is_dir(),
                'extension': filepath.suffix,
                'absolute_path': str(filepath.absolute())
            }

        except Exception as e:
            logger.error(f"Błąd pobierania informacji o pliku {filepath}: {e}")
            return None