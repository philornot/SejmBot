# cache_manager.py
"""
Inteligentny system cache'u dla SejmBot Scraper
Obsługuje cache na poziomie plików, danych (hash/checksum) i API calls
"""

import hashlib
import json
import logging
from dataclasses import dataclass, asdict
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any

from config import get_output_dir


@dataclass
class CacheEntry:
    """Wpis w cache'u"""
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


class CacheManager:
    """Menedżer cache'u dla scrapera"""

    def __init__(self, cache_dir: str = "cache"):
        self.cache_dir = get_output_dir() / cache_dir
        self.cache_dir.mkdir(exist_ok=True)

        # Pliki cache'u
        self.api_cache_file = self.cache_dir / "api_cache.json"
        self.file_cache_file = self.cache_dir / "file_cache.json"
        self.metadata_file = self.cache_dir / "cache_metadata.json"

        # Cache w pamięci
        self.api_cache: Dict[str, CacheEntry] = {}
        self.file_cache: Dict[str, CacheEntry] = {}
        self.metadata: Dict = {}

        self.logger = logging.getLogger(__name__)

        # Załaduj istniejące cache
        self._load_cache()

    def _load_cache(self):
        """Ładuje cache z dysku"""
        try:
            # API Cache
            if self.api_cache_file.exists():
                with open(self.api_cache_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.api_cache = {k: CacheEntry(**v) for k, v in data.items()}

            # File Cache
            if self.file_cache_file.exists():
                with open(self.file_cache_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.file_cache = {k: CacheEntry(**v) for k, v in data.items()}

            # Metadata
            if self.metadata_file.exists():
                with open(self.metadata_file, 'r', encoding='utf-8') as f:
                    self.metadata = json.load(f)

            self.logger.debug(f"Załadowano cache: {len(self.api_cache)} API, {len(self.file_cache)} plików")

        except Exception as e:
            self.logger.warning(f"Błąd ładowania cache: {e}")
            self._reset_cache()

    def _save_cache(self):
        """Zapisuje cache na dysk"""
        try:
            # API Cache
            api_data = {k: asdict(v) for k, v in self.api_cache.items()}
            with open(self.api_cache_file, 'w', encoding='utf-8') as f:
                json.dump(api_data, f, ensure_ascii=False, indent=2)

            # File Cache
            file_data = {k: asdict(v) for k, v in self.file_cache.items()}
            with open(self.file_cache_file, 'w', encoding='utf-8') as f:
                json.dump(file_data, f, ensure_ascii=False, indent=2)

            # Metadata
            with open(self.metadata_file, 'w', encoding='utf-8') as f:
                json.dump(self.metadata, f, ensure_ascii=False, indent=2)

        except Exception as e:
            self.logger.error(f"Błąd zapisywania cache: {e}")

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

    def _make_api_key(self, endpoint: str, params: Dict = None) -> str:
        """Tworzy klucz dla cache'u API"""
        if params:
            params_str = json.dumps(params, sort_keys=True)
            return f"api:{endpoint}:{hashlib.md5(params_str.encode()).hexdigest()}"
        return f"api:{endpoint}"

    def _make_file_key(self, filepath: Path) -> str:
        """Tworzy klucz dla cache'u plików"""
        return f"file:{filepath.as_posix()}"

    def has_api_cache(self, endpoint: str, params: Dict = None, max_age_hours: int = 1) -> bool:
        """Sprawdza czy mamy świeży cache dla API call"""
        key = self._make_api_key(endpoint, params)

        if key not in self.api_cache:
            return False

        entry = self.api_cache[key]

        # Sprawdź wygaśnięcie
        if entry.is_expired():
            del self.api_cache[key]
            return False

        # Sprawdź czy nie jest za stary
        if entry.is_stale(max_age_hours):
            return False

        return True

    def get_api_cache(self, endpoint: str, params: Dict = None) -> Optional[Any]:
        """Pobiera dane z cache'u API"""
        key = self._make_api_key(endpoint, params)

        if key not in self.api_cache:
            return None

        entry = self.api_cache[key]

        # Aktualizuj last_accessed
        entry.last_accessed = datetime.now().isoformat()

        # Zwróć dane z metadanych
        return entry.metadata.get('data') if entry.metadata else None

    def set_api_cache(self, endpoint: str, data: Any, params: Dict = None, ttl_hours: int = 1):
        """Zapisuje dane do cache'u API"""
        key = self._make_api_key(endpoint, params)
        now = datetime.now()

        entry = CacheEntry(
            key=key,
            data_hash=self._generate_hash(data),
            created_at=now.isoformat(),
            last_accessed=now.isoformat(),
            expires_at=(now + timedelta(hours=ttl_hours)).isoformat(),
            metadata={'data': data, 'endpoint': endpoint, 'params': params}
        )

        self.api_cache[key] = entry
        self.logger.debug(f"Zapisano do cache API: {key}")

    def has_file_cache(self, filepath: Path, check_content: bool = True) -> bool:
        """Sprawdza czy plik istnieje i czy się nie zmienił"""
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

    def set_file_cache(self, filepath: Path, metadata: Dict = None):
        """Rejestruje plik w cache'u"""
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
        self.logger.debug(f"Zarejestrowano plik: {filepath}")

    def should_refresh_proceeding(self, term: int, proceeding_id: int,
                                  proceeding_dates: List[str], force: bool = False) -> bool:
        """
        Sprawdza czy posiedzenie wymaga odświeżenia

        Args:
            term: numer kadencji
            proceeding_id: ID posiedzenia
            proceeding_dates: daty posiedzenia
            force: wymuś odświeżenie

        Returns:
            True jeśli należy odświeżyć
        """
        if force:
            return True

        # Sprawdź czy posiedzenie jest w przyszłości
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

        if key not in self.api_cache:
            return True

        entry = self.api_cache[key]
        return entry.is_stale(max_age_hours=24)  # Raz dziennie

    def _should_refresh_completed_proceeding(self, term: int, proceeding_id: int,
                                             dates: List[str]) -> bool:
        """Logika dla zakończonych posiedzeń"""
        # Sprawdź czy mamy już wszystkie transkrypty
        from file_manager import FileManager
        fm = FileManager()

        # Symulacja sprawdzenia - czy mamy pliki dla wszystkich dat
        try:
            proceeding_info = {'dates': dates}  # Mock
            existing_dates = fm.get_existing_transcripts(term, proceeding_id, proceeding_info)

            if len(existing_dates) >= len(dates):
                # Mamy wszystkie dni - rzadko sprawdzaj
                key = f"completed_check:{term}:{proceeding_id}"

                if key not in self.api_cache:
                    return True

                entry = self.api_cache[key]
                return entry.is_stale(max_age_hours=168)  # Raz w tygodniu
        except:
            pass

        return True  # W przypadku wątpliwości odśwież

    def _should_refresh_ongoing_proceeding(self, term: int, proceeding_id: int) -> bool:
        """Logika dla trwających posiedzeń - częste sprawdzanie"""
        key = f"ongoing_check:{term}:{proceeding_id}"

        if key not in self.api_cache:
            return True

        entry = self.api_cache[key]
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

        self.api_cache[key] = entry

    def cleanup_expired(self):
        """Usuwa wygasłe wpisy z cache'u"""
        # API Cache
        expired_api = [k for k, v in self.api_cache.items() if v.is_expired()]
        for key in expired_api:
            del self.api_cache[key]

        # File Cache - usuń wpisy dla nieistniejących plików
        missing_files = []
        for key, entry in self.file_cache.items():
            if key.startswith("file:"):
                filepath = Path(key[5:])  # Usuń prefix "file:"
                if not filepath.exists():
                    missing_files.append(key)

        for key in missing_files:
            del self.file_cache[key]

        if expired_api or missing_files:
            self.logger.info(f"Wyczyszczono cache: {len(expired_api)} API, {len(missing_files)} plików")

    def cleanup_old_entries(self, max_age_days: int = 30):
        """Usuwa stare wpisy z cache'u"""
        cutoff = datetime.now() - timedelta(days=max_age_days)

        old_api = []
        for key, entry in self.api_cache.items():
            created = datetime.fromisoformat(entry.created_at)
            if created < cutoff:
                old_api.append(key)

        for key in old_api:
            del self.api_cache[key]

        old_files = []
        for key, entry in self.file_cache.items():
            created = datetime.fromisoformat(entry.created_at)
            if created < cutoff:
                old_files.append(key)

        for key in old_files:
            del self.file_cache[key]

        if old_api or old_files:
            self.logger.info(f"Usunięto stare wpisy: {len(old_api)} API, {len(old_files)} plików")

    def get_stats(self) -> Dict:
        """Zwraca statystyki cache'u"""
        now = datetime.now()

        # API Cache stats
        api_expired = sum(1 for entry in self.api_cache.values() if entry.is_expired())
        api_stale_1h = sum(1 for entry in self.api_cache.values() if entry.is_stale(1))
        api_stale_24h = sum(1 for entry in self.api_cache.values() if entry.is_stale(24))

        # File Cache stats - sprawdź które pliki nadal istnieją
        files_exist = 0
        for key in self.file_cache.keys():
            if key.startswith("file:"):
                filepath = Path(key[5:])
                if filepath.exists():
                    files_exist += 1

        return {
            'api_cache': {
                'total_entries': len(self.api_cache),
                'expired': api_expired,
                'stale_1h': api_stale_1h,
                'stale_24h': api_stale_24h,
            },
            'file_cache': {
                'total_entries': len(self.file_cache),
                'files_exist': files_exist,
                'files_missing': len(self.file_cache) - files_exist,
            },
            'disk_usage': {
                'cache_dir_size_mb': sum(f.stat().st_size for f in self.cache_dir.rglob('*') if f.is_file()) / (
                        1024 * 1024),
            }
        }

    def _reset_cache(self):
        """Resetuje cache do stanu początkowego"""
        self.api_cache.clear()
        self.file_cache.clear()
        self.metadata.clear()

        # Usuń pliki cache'u
        for cache_file in [self.api_cache_file, self.file_cache_file, self.metadata_file]:
            if cache_file.exists():
                cache_file.unlink()

        self.logger.info("Cache został zresetowany")

    def reset_cache(self, cache_type: str = "all"):
        """
        Publiczna metoda resetowania cache'u

        Args:
            cache_type: "api", "files", "all"
        """
        if cache_type in ("api", "all"):
            self.api_cache.clear()
            if self.api_cache_file.exists():
                self.api_cache_file.unlink()

        if cache_type in ("files", "all"):
            self.file_cache.clear()
            if self.file_cache_file.exists():
                self.file_cache_file.unlink()

        if cache_type == "all":
            self.metadata.clear()
            if self.metadata_file.exists():
                self.metadata_file.unlink()

        self.logger.info(f"Cache '{cache_type}' został zresetowany")

    def save(self):
        """Zapisuje cache na dysk"""
        self._save_cache()

    def __enter__(self):
        """Context manager entry"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - automatyczny zapis"""
        self._save_cache()
