"""
Implementacja cache plików z funkcjami z oryginalnego cache_manager.py
Dostosowana do nowej modularnej architektury
"""

import hashlib
import json
import logging
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Union

from ..config.settings import get_settings
from ..core.types import FileCacheEntry

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """Wpis w cache"""
    key: str
    data_hash: str
    created_at: str
    last_accessed: str
    expires_at: Optional[str] = None
    metadata: Dict = None

    def is_expired(self) -> bool:
        """Sprawdza czy wpis wygasł"""
        if not self.expires_at:
            return False
        return datetime.fromisoformat(self.expires_at) < datetime.now()

    def is_stale(self, max_age_hours: int = 24) -> bool:
        """Sprawdza czy wpis jest przestarzały"""
        created = datetime.fromisoformat(self.created_at)
        return (datetime.now() - created).total_seconds() > (max_age_hours * 3600)


class FileCacheImpl:
    """
    Implementacja cache plików

    Bazuje na oryginalnym CacheManager ale dostosowana do nowej architektury.
    Obsługuje cache na poziomie plików i metadanych.
    """

    def __init__(self, config=None):
        """
        Inicjalizuje cache plików

        Args:
            config: konfiguracja cache (opcjonalna)
        """
        self.config = config or {}

        # Pobierz ustawienia
        settings = get_settings()
        cache_dir = self.config.get('cache_dir') or Path(settings.get('scraping.base_output_dir')) / 'cache'

        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Pliki cache
        self.file_cache_file = self.cache_dir / "file_cache.json"
        self.metadata_file = self.cache_dir / "cache_metadata.json"

        # Cache w pamięci
        self.file_cache: Dict[str, CacheEntry] = {}
        self.metadata: Dict = {}

        logger.debug(f"Zainicjalizowano FileCacheImpl: {self.cache_dir}")

        # Załaduj istniejący cache
        self._load_cache()

    def _load_cache(self):
        """Ładuje cache z dysku"""
        try:
            # File Cache
            if self.file_cache_file.exists():
                with open(self.file_cache_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.file_cache = {k: CacheEntry(**v) for k, v in data.items()}

            # Metadata
            if self.metadata_file.exists():
                with open(self.metadata_file, 'r', encoding='utf-8') as f:
                    self.metadata = json.load(f)

            logger.debug(f"Załadowano cache: {len(self.file_cache)} plików")

        except Exception as e:
            logger.warning(f"Błąd ładowania cache: {e}")
            self._reset_cache()

    def _save_cache(self):
        """Zapisuje cache na dysk"""
        try:
            # File Cache
            file_data = {k: asdict(v) for k, v in self.file_cache.items()}
            with open(self.file_cache_file, 'w', encoding='utf-8') as f:
                json.dump(file_data, f, ensure_ascii=False, indent=2)

            # Metadata
            with open(self.metadata_file, 'w', encoding='utf-8') as f:
                json.dump(self.metadata, f, ensure_ascii=False, indent=2)

        except Exception as e:
            logger.error(f"Błąd zapisywania cache: {e}")

    def _generate_hash(self, data: Any) -> str:
        """Generuje hash dla danych"""
        if isinstance(data, (dict, list)):
            data_str = json.dumps(data, sort_keys=True, ensure_ascii=False)
        elif isinstance(data, Path):
            # Hash na podstawie zawartości pliku
            try:
                with open(data, 'rb') as f:
                    return hashlib.sha256(f.read()).hexdigest()
            except:
                return hashlib.sha256(str(data).encode()).hexdigest()
        else:
            data_str = str(data)

        return hashlib.sha256(data_str.encode('utf-8')).hexdigest()

    def _make_file_key(self, filepath: Union[str, Path]) -> str:
        """Tworzy klucz dla cache plików"""
        return f"file:{Path(filepath).as_posix()}"

    # === IMPLEMENTACJA INTERFEJSU FileCacheManager ===

    def has_file_cache(self, filepath: Union[str, Path], check_content: bool = True) -> bool:
        """Sprawdza czy plik istnieje w cache i czy się nie zmienił"""
        filepath = Path(filepath)

        if not filepath.exists():
            return False

        key = self._make_file_key(filepath)

        if not check_content:
            return True  # Plik istnieje, wystarczy

        if key not in self.file_cache:
            return False

        entry = self.file_cache[key]

        # Sprawdź hash zawartości
        current_hash = self._generate_hash(filepath)
        return current_hash == entry.data_hash

    def get_file_cache(self, filepath: Union[str, Path]) -> Optional[FileCacheEntry]:
        """Pobiera metadane pliku z cache"""
        key = self._make_file_key(filepath)

        if key not in self.file_cache:
            return None

        entry = self.file_cache[key]

        # Aktualizuj last_accessed
        entry.last_accessed = datetime.now().isoformat()

        # Konwertuj na FileCacheEntry
        filepath_obj = Path(filepath)
        return FileCacheEntry(
            path=str(filepath_obj),
            last_modified=filepath_obj.stat().st_mtime if filepath_obj.exists() else 0,
            size=filepath_obj.stat().st_size if filepath_obj.exists() else 0,
            checksum=entry.data_hash,
            metadata=entry.metadata or {}
        )

    def set_file_cache(self, filepath: Union[str, Path], metadata: Dict[str, Any]) -> None:
        """Zapisuje metadane pliku do cache"""
        filepath = Path(filepath)
        key = self._make_file_key(filepath)
        now = datetime.now()

        entry = CacheEntry(
            key=key,
            data_hash=self._generate_hash(filepath),
            created_at=now.isoformat(),
            last_accessed=now.isoformat(),
            metadata=metadata or {}
        )

        self.file_cache[key] = entry
        logger.debug(f"Zarejestrowano plik: {filepath}")

    def cleanup_expired(self) -> int:
        """Czyści wygasłe wpisy ze cache, zwraca liczbę usuniętych"""
        # File Cache - usuń wpisy dla nieistniejących plików
        missing_files = []
        for key, entry in self.file_cache.items():
            if key.startswith("file:"):
                filepath = Path(key[5:])  # Usuń prefix "file:"
                if not filepath.exists():
                    missing_files.append(key)

        for key in missing_files:
            del self.file_cache[key]

        if missing_files:
            logger.info(f"Wyczyszczono cache: {len(missing_files)} nieistniejących plików")

        return len(missing_files)

    # === METODY LOGIKI BIZNESOWEJ ===

    def should_refresh_proceeding(self, term: int, proceeding_id: int,
                                  proceeding_dates: List[str], force: bool = False) -> bool:
        """
        Sprawdza czy posiedzenie wymaga odświeżenia

        Implementacja logiki z oryginalnego cache_manager.py
        """
        if force:
            return True

        # Sprawdź czy posiedzenie jest w przyszłości
        from datetime import date
        today = date.today()
        future_dates = []
        past_dates = []

        for date_str in proceeding_dates:
            try:
                proc_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                if proc_date > today:
                    future_dates.append(date_str)
                else:
                    past_dates.append(date_str)
            except ValueError:
                continue

        # Przyszłe posiedzenia - nie odświeżaj za często
        if future_dates and not past_dates:
            return self._should_refresh_future_proceeding(term, proceeding_id)

        # Zakończone posiedzenia - rzadko odświeżaj
        if past_dates and not future_dates:
            return self._should_refresh_completed_proceeding(term, proceeding_id, past_dates)

        # Trwające posiedzenia - odświeżaj częściej
        return self._should_refresh_ongoing_proceeding(term, proceeding_id)

    def _should_refresh_future_proceeding(self, term: int, proceeding_id: int) -> bool:
        """Logika dla przyszłych posiedzeń - raz dziennie wystarczy"""
        key = f"proceeding_check:{term}:{proceeding_id}"

        if key not in self.file_cache:
            return True

        entry = self.file_cache[key]
        return entry.is_stale(max_age_hours=24)  # Raz dziennie

    def _should_refresh_completed_proceeding(self, term: int, proceeding_id: int,
                                             dates: List[str]) -> bool:
        """Logika dla zakończonych posiedzeń"""
        # Sprawdź czy mamy już wszystkie transkrypty
        try:
            from ..storage.file_manager import FileManagerInterface
            fm = FileManagerInterface()

            # Sprawdź czy mamy pliki dla wszystkich dat
            proceeding_info = {'dates': dates}  # Mock
            existing_dates = fm.get_existing_transcripts(term, proceeding_id, proceeding_info)

            if len(existing_dates) >= len(dates):
                # Mamy wszystkie dni - rzadko sprawdzaj
                key = f"completed_check:{term}:{proceeding_id}"

                if key not in self.file_cache:
                    return True

                entry = self.file_cache[key]
                return entry.is_stale(max_age_hours=168)  # Raz w tygodniu
        except:
            pass

        return True  # W przypadku wątpliwości odśwież

    def _should_refresh_ongoing_proceeding(self, term: int, proceeding_id: int) -> bool:
        """Logika dla trwających posiedzeń - częste sprawdzanie"""
        key = f"ongoing_check:{term}:{proceeding_id}"

        if key not in self.file_cache:
            return True

        entry = self.file_cache[key]
        return entry.is_stale(max_age_hours=2)  # Co 2 godziny

    def mark_proceeding_checked(self, term: int, proceeding_id: int, status: str = "checked"):
        """Oznacza posiedzenie jako sprawdzone"""
        key = f"{status}_check:{term}:{proceeding_id}"
        now = datetime.now()

        entry = CacheEntry(
            key=key,
            data_hash="",
            created_at=now.isoformat(),
            last_accessed=now.isoformat(),
            metadata={'status': status, 'term': term, 'proceeding_id': proceeding_id}
        )

        self.file_cache[key] = entry

    # === ZARZĄDZANIE CACHE ===

    def cleanup_old_entries(self, max_age_days: int = 30) -> int:
        """Usuwa stare wpisy z cache"""
        cutoff = datetime.now() - timedelta(days=max_age_days)

        old_files = []
        for key, entry in self.file_cache.items():
            created = datetime.fromisoformat(entry.created_at)
            if created < cutoff:
                old_files.append(key)

        for key in old_files:
            del self.file_cache[key]

        if old_files:
            logger.info(f"Usunięto stare wpisy: {len(old_files)} plików")

        return len(old_files)

    def get_stats(self) -> Dict:
        """Zwraca statystyki cache plików"""
        # Sprawdź które pliki nadal istnieją
        files_exist = 0
        for key in self.file_cache.keys():
            if key.startswith("file:"):
                filepath = Path(key[5:])
                if filepath.exists():
                    files_exist += 1

        return {
            'entries': len(self.file_cache),
            'files_exist': files_exist,
            'files_missing': len(self.file_cache) - files_exist,
            'size_mb': sum(f.stat().st_size for f in self.cache_dir.rglob('*') if f.is_file()) / (1024 * 1024)
        }

    def get_size_mb(self) -> float:
        """Zwraca rozmiar cache w MB"""
        try:
            return sum(f.stat().st_size for f in self.cache_dir.rglob('*') if f.is_file()) / (1024 * 1024)
        except Exception:
            return 0.0

    def clear(self) -> None:
        """Czyści cały cache plików"""
        self.file_cache.clear()
        if self.file_cache_file.exists():
            self.file_cache_file.unlink()
        logger.info("Wyczyszczono cache plików")

    def _reset_cache(self):
        """Resetuje cache do stanu początkowego"""
        self.file_cache.clear()
        self.metadata.clear()

        # Usuń pliki cache
        for cache_file in [self.file_cache_file, self.metadata_file]:
            if cache_file.exists():
                cache_file.unlink()

        logger.info("Cache plików został zresetowany")

    def save(self):
        """Zapisuje cache na dysk"""
        self._save_cache()

    def __enter__(self):
        """Context manager entry"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - automatyczny zapis"""
        self._save_cache()

    def __repr__(self) -> str:
        """Reprezentacja string obiektu"""
        return f"FileCacheImpl(entries={len(self.file_cache)}, dir={self.cache_dir})"
