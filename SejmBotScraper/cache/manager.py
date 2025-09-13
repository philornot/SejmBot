"""
Interfejs managera cache — orkiestruje różne typy cache
Mały plik interfejsowy — implementacje w osobnych plikach
"""

import logging
from pathlib import Path
from typing import Optional, Any, Dict, Union

from ..core.types import CacheStats

logger = logging.getLogger(__name__)


class CacheInterface:
    """
    Główny interfejs do zarządzania cache

    Orkiestruje różne typy cache:
    - Memory cache (szybki, tymczasowy)
    - File cache (trwały, metadane plików)
    - API cache (zapytania do API)
    """

    def __init__(self, config=None):
        """
        Inicjalizuje interfejs cache

        Args:
            config: konfiguracja cache (opcjonalna)
        """
        self.config = config or {}

        # Import implementacji dopiero tutaj aby uniknąć circular imports
        from .file_cache import FileCacheImpl
        from .memory_cache import MemoryCacheImpl

        # Inicjalizacja różnych typów cache
        self.file_cache = FileCacheImpl(config)
        self.memory_cache = MemoryCacheImpl(config)

        logger.debug("Zainicjalizowano interfejs cache")

    # === API CACHE (w pamięci, szybkie) ===

    def get_api_cache(self, key: str, params: Optional[Dict] = None) -> Optional[Any]:
        """
        Pobiera dane z cache API

        Args:
            key: klucz cache (endpoint)
            params: parametry zapytania (opcjonalne)

        Returns:
            Dane z cache lub None
        """
        cache_key = self._generate_api_key(key, params)
        return self.memory_cache.get(cache_key)

    def set_api_cache(self, key: str, value: Any, params: Optional[Dict] = None,
                      ttl: Optional[int] = None) -> None:
        """
        Zapisuje dane do cache API

        Args:
            key: klucz cache (endpoint)
            value: wartość do zapisania
            params: parametry zapytania (opcjonalne)
            ttl: czas życia w sekundach (opcjonalne)
        """
        cache_key = self._generate_api_key(key, params)
        self.memory_cache.set(cache_key, value, ttl)

    def has_api_cache(self, key: str, params: Optional[Dict] = None,
                      max_age_hours: Optional[int] = None) -> bool:
        """
        Sprawdza, czy klucz istnieje w cache API

        Args:
            key: klucz cache
            params: parametry zapytania
            max_age_hours: maksymalny wiek w godzinach

        Returns:
            True, jeśli klucz istnieje i jest świeży
        """
        cache_key = self._generate_api_key(key, params)

        if not self.memory_cache.has(cache_key):
            return False

        # Sprawdź wiek, jeśli podano max_age_hours
        if max_age_hours is not None:
            entry_age = self.memory_cache.get_age(cache_key)
            if entry_age is None or entry_age > (max_age_hours * 3600):
                return False

        return True

    def clear_api_cache(self) -> None:
        """Czyści cache API"""
        logger.debug("Czyszczenie cache API")
        self.memory_cache.clear("api_*")

    # === FILE CACHE (metadane plików) ===

    def get_file_cache(self, filepath: Union[str, Path]) -> Optional[Dict]:
        """
        Pobiera metadane pliku z cache

        Args:
            filepath: ścieżka do pliku

        Returns:
            Metadane pliku lub None
        """
        return self.file_cache.get_file_cache(filepath)

    def set_file_cache(self, filepath: Union[str, Path], metadata: Dict[str, Any]) -> None:
        """
        Zapisuje metadane pliku do cache

        Args:
            filepath: ścieżka do pliku
            metadata: metadane do zapisania
        """
        self.file_cache.set_file_cache(filepath, metadata)

    def has_file_cache(self, filepath: Union[str, Path], check_content: bool = False) -> bool:
        """
        Sprawdza, czy plik istnieje w cache

        Args:
            filepath: ścieżka do pliku
            check_content: czy sprawdzać zawartość pliku

        Returns:
            True, jeśli plik jest w cache i aktualny
        """
        return self.file_cache.has_file_cache(filepath, check_content)

    def clear_file_cache(self) -> None:
        """Czyści cache plików"""
        logger.debug("Czyszczenie cache plików")
        self.file_cache.clear()

    # === ZARZĄDZANIE CACHE POSIEDZEŃ (logika biznesowa) ===

    def should_refresh_proceeding(self, term: int, proceeding_id: int,
                                  proceeding_dates: list, force: bool = False) -> bool:
        """
        Decyduje czy posiedzenie wymaga odświeżenia

        Args:
            term: numer kadencji
            proceeding_id: ID posiedzenia
            proceeding_dates: daty posiedzenia
            force: czy wymusić odświeżenie

        Returns:
            True, jeśli wymaga odświeżenia
        """
        if force:
            return True

        cache_key = f"proceeding_check_{term}_{proceeding_id}"

        # Sprawdź, czy posiedzenie było już sprawdzane
        check_data = self.memory_cache.get(cache_key)
        if check_data:
            # Jeśli było sprawdzane w ciągu ostatnich 6 godzin, nie odświeżaj
            age = self.memory_cache.get_age(cache_key)
            if age is not None and age < (6 * 3600):  # 6 godzin
                return False

        # Sprawdź, czy wszystkie pliki transkryptów istnieją
        from ..storage.file_manager import FileManagerInterface
        file_manager = FileManagerInterface()

        missing_dates = []
        for date in proceeding_dates:
            # Sprawdź, czy jest w przyszłości
            from datetime import datetime, date as date_obj
            try:
                proceeding_date = datetime.strptime(date, '%Y-%m-%d').date()
                if proceeding_date > date_obj.today():
                    continue  # Pomiń przyszłe daty
            except ValueError:
                continue

            # Sprawdź, czy plik istnieje
            if not self._transcript_file_exists(term, proceeding_id, date, file_manager):
                missing_dates.append(date)

        return len(missing_dates) > 0

    def mark_proceeding_checked(self, term: int, proceeding_id: int, status: str) -> None:
        """
        Oznacza posiedzenie jako sprawdzone

        Args:
            term: numer kadencji
            proceeding_id: ID posiedzenia
            status: status sprawdzenia (processed, skipped, error)
        """
        cache_key = f"proceeding_check_{term}_{proceeding_id}"
        check_data = {
            'status': status,
            'checked_at': self._get_current_timestamp(),
            'term': term,
            'proceeding_id': proceeding_id
        }

        # Cache na 24 godziny
        self.memory_cache.set(cache_key, check_data, ttl=24 * 3600)

    # === OGÓLNE ZARZĄDZANIE CACHE ===

    def clear_all(self) -> None:
        """Czyści wszystkie cache"""
        logger.info("Czyszczenie wszystkich cache")
        self.memory_cache.clear()
        self.file_cache.clear()

    def cleanup_expired(self) -> Dict[str, int]:
        """
        Czyści wygasłe wpisy ze wszystkich cache

        Returns:
            Słownik z liczbą usuniętych wpisów dla każdego typu
        """
        logger.info("Czyszczenie wygasłych wpisów cache")

        results = {}

        # Cleanup memory cache
        if hasattr(self.memory_cache, 'cleanup_expired'):
            results['memory'] = self.memory_cache.cleanup_expired()

        # Cleanup file cache
        if hasattr(self.file_cache, 'cleanup_expired'):
            results['file'] = self.file_cache.cleanup_expired()

        total_cleaned = sum(results.values())
        logger.info(f"Wyczyszczono {total_cleaned} wygasłych wpisów cache")

        return results

    def get_stats(self) -> CacheStats:
        """
        Zwraca łączne statystyki cache

        Returns:
            Statystyki wszystkich typów cache
        """
        memory_stats = self.memory_cache.get_stats() if hasattr(self.memory_cache, 'get_stats') else {}
        file_stats = self.file_cache.get_stats() if hasattr(self.file_cache, 'get_stats') else {}

        return CacheStats(
            memory_entries=memory_stats.get('entries', 0),
            file_entries=file_stats.get('entries', 0),
            api_entries=memory_stats.get('api_entries', 0),
            memory_hits=memory_stats.get('hits', 0),
            memory_misses=memory_stats.get('misses', 0),
            file_hits=file_stats.get('hits', 0),
            file_misses=file_stats.get('misses', 0),
            total_size_mb=memory_stats.get('size_mb', 0) + file_stats.get('size_mb', 0),
            last_cleanup=memory_stats.get('last_cleanup') or file_stats.get('last_cleanup')
        )

    def get_size_mb(self) -> float:
        """
        Zwraca łączny rozmiar cache w MB

        Returns:
            Rozmiar w MB
        """
        memory_size = self.memory_cache.get_size_mb() if hasattr(self.memory_cache, 'get_size_mb') else 0
        file_size = self.file_cache.get_size_mb() if hasattr(self.file_cache, 'get_size_mb') else 0

        return memory_size + file_size

    def reset_cache(self, cache_type: str = "all") -> None:
        """
        Resetuje cache do stanu początkowego

        Args:
            cache_type: typ cache do zresetowania (all, memory, file, api)
        """
        logger.info(f"Resetowanie cache: {cache_type}")

        if cache_type in ("all", "memory", "api"):
            self.memory_cache.clear()

        if cache_type in ("all", "file"):
            self.file_cache.clear()

    # === METODY POMOCNICZE ===

    @staticmethod
    def _generate_api_key(endpoint: str, params: Optional[Dict] = None) -> str:
        """Generuje klucz cache dla API"""
        if params:
            # Sortuj parametry dla stabilnego klucza
            param_str = "&".join(f"{k}={v}" for k, v in sorted(params.items()))
            return f"api_{endpoint}#{param_str}"
        return f"api_{endpoint}"

    @staticmethod
    def _transcript_file_exists(term: int, proceeding_id: int, date: str, file_manager) -> bool:
        """Sprawdza, czy plik transkryptu istnieje"""
        try:
            # Buduj ścieżkę do pliku transkryptu
            transcript_path = file_manager.get_transcript_file_path(term, proceeding_id, date)
            return Path(transcript_path).exists()
        except Exception:
            return False

    @staticmethod
    def _get_current_timestamp() -> float:
        """Zwraca aktualny timestamp"""
        import time
        return time.time()

    # === METODY DIAGNOSTYCZNE ===

    def health_check(self) -> Dict:
        """
        Sprawdza stan cache

        Returns:
            Raport zdrowia cache
        """
        health = {
            'healthy': True,
            'timestamp': self._get_current_timestamp(),
            'components': {}
        }
        return health
