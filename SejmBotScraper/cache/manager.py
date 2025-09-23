"""
Naprawiony interfejs managera cache
Integruje naprawione implementacje cache
"""

import logging
from pathlib import Path
from typing import Optional, Any, Dict, Union

logger = logging.getLogger(__name__)


class CacheInterface:
    """
    Główny interfejs do zarządzania cache
    NAPRAWIONA WERSJA - używa poprawnych implementacji
    """

    def __init__(self, config=None):
        """
        Inicjalizuje interfejs cache

        Args:
            config: konfiguracja cache (opcjonalna)
        """
        self.config = config or {}

        # Import naprawionych implementacji
        try:
            from .file_cache import FileCacheImpl
            self.file_cache = FileCacheImpl(config)
            logger.debug("Załadowano FileCacheImpl")
        except ImportError as e:
            logger.warning(f"Nie można załadować FileCacheImpl: {e}")
            self.file_cache = self._create_fallback_file_cache()

        try:
            from .implementations.memory_cache import MemoryCacheImpl
            self.memory_cache = MemoryCacheImpl(config)
            logger.debug("Załadowano MemoryCacheImpl")
        except ImportError as e:
            logger.warning(f"Nie można załadować MemoryCacheImpl: {e}")
            self.memory_cache = self._create_fallback_memory_cache()

        logger.debug("Zainicjalizowano naprawiony interfejs cache")

    def _create_fallback_memory_cache(self):
        """Tworzy fallback memory cache"""

        class FallbackMemoryCache:
            def __init__(self):
                self._cache = {}

            def get(self, key): return self._cache.get(key)

            def set(self, key, value, ttl=None): self._cache[key] = value

            def has(self, key): return key in self._cache

            def clear(self, pattern=None): self._cache.clear()

            def get_age(self, key): return None

            def cleanup_expired(self): return 0

            def get_stats(self):
                return {
                    'entries': len(self._cache),
                    'size_mb': 0,
                    'api_entries': len([k for k in self._cache.keys() if k.startswith('api_')])
                }

        return FallbackMemoryCache()

    def _create_fallback_file_cache(self):
        """Tworzy fallback file cache"""

        class FallbackFileCache:
            def has_file_cache(self, filepath, check_content=False): return False

            def get_file_cache(self, filepath): return None

            def set_file_cache(self, filepath, metadata): pass

            def cleanup_expired(self): return 0

            def clear(self): pass

            def get_stats(self): return {'entries': 0, 'size_mb': 0}

            def should_refresh_proceeding(self, *args, **kwargs): return True

            def mark_proceeding_checked(self, *args, **kwargs): pass

        return FallbackFileCache()

    # === API CACHE (w pamięci, szybkie) ===

    def get(self, key: str) -> Optional[Any]:
        """
        Pobiera dane z cache (głównie dla API)

        Args:
            key: klucz cache

        Returns:
            Dane z cache lub None
        """
        return self.memory_cache.get(key)

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """
        Zapisuje dane do cache (głównie dla API)

        Args:
            key: klucz cache
            value: wartość do zapisania
            ttl: czas życia w sekundach
        """
        return self.memory_cache.set(key, value, ttl)

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
        result = self.memory_cache.get(cache_key)
        if result is not None:
            logger.debug(f"Cache API hit: {key}")
        return result

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
        logger.debug(f"Cache API set: {key}")

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
        return self.file_cache.should_refresh_proceeding(term, proceeding_id, proceeding_dates, force)

    def mark_proceeding_checked(self, term: int, proceeding_id: int, status: str) -> None:
        """
        Oznacza posiedzenie jako sprawdzone

        Args:
            term: numer kadencji
            proceeding_id: ID posiedzenia
            status: status sprawdzenia (processed, skipped, error)
        """
        self.file_cache.mark_proceeding_checked(term, proceeding_id, status)

    # === OGÓLNE ZARZĄDZANIE CACHE ===

    def clear(self) -> None:
        """Czyści wszystkie cache"""
        logger.info("Czyszczenie wszystkich cache")
        self.memory_cache.clear()
        self.file_cache.clear()

    def clear_all(self) -> None:
        """Alias dla clear()"""
        self.clear()

    def cleanup_expired(self) -> Dict[str, int]:
        """
        Czyści wygasłe wpisy ze wszystkich cache

        Returns:
            Słownik z liczbą usuniętych wpisów dla każdego typu
        """
        logger.info("Czyszczenie wygasłych wpisów cache")

        results = {}

        # Cleanup memory cache
        try:
            results['memory'] = self.memory_cache.cleanup_expired()
        except Exception as e:
            logger.warning(f"Błąd cleanup memory cache: {e}")
            results['memory'] = 0

        # Cleanup file cache
        try:
            results['file'] = self.file_cache.cleanup_expired()
        except Exception as e:
            logger.warning(f"Błąd cleanup file cache: {e}")
            results['file'] = 0

        total_cleaned = sum(results.values())
        logger.info(f"Wyczyszczono {total_cleaned} wygasłych wpisów cache")

        return results

    def get_stats(self) -> Dict:
        """
        Zwraca łączne statystyki cache

        Returns:
            Statystyki wszystkich typów cache
        """
        memory_stats = {}
        file_stats = {}

        try:
            memory_stats = self.memory_cache.get_stats()
        except Exception as e:
            logger.warning(f"Nie można pobrać memory stats: {e}")

        try:
            file_stats = self.file_cache.get_stats()
        except Exception as e:
            logger.warning(f"Nie można pobrać file stats: {e}")

        return {
            'memory_cache': {
                'entries': memory_stats.get('entries', 0),
                'size_mb': memory_stats.get('size_mb', 0),
                'api_entries': memory_stats.get('api_entries', 0),
                'hits': memory_stats.get('hits', 0),
                'misses': memory_stats.get('misses', 0),
                'hit_rate': memory_stats.get('hit_rate', 0)
            },
            'file_cache': {
                'entries': file_stats.get('entries', 0),
                'size_mb': file_stats.get('size_mb', 0),
                'files_exist': file_stats.get('files_exist', 0),
                'files_missing': file_stats.get('files_missing', 0)
            }
        }

    def get_size_mb(self) -> float:
        """
        Zwraca łączny rozmiar cache w MB

        Returns:
            Rozmiar w MB
        """
        memory_size = 0
        file_size = 0

        try:
            memory_size = self.memory_cache.get_size_mb()
        except:
            pass

        try:
            file_size = self.file_cache.get_size_mb()
        except:
            pass

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

    # === METODY DIAGNOSTYCZNE ===

    def health_check(self) -> Dict:
        """
        Sprawdza stan cache

        Returns:
            Raport zdrowia cache
        """
        import time

        health = {
            'healthy': True,
            'timestamp': time.time(),
            'components': {
                'memory_cache': {'healthy': True},
                'file_cache': {'healthy': True}
            },
            'stats': self.get_stats()
        }

        # Test memory cache
        try:
            test_key = f"health_test_{int(time.time())}"
            self.memory_cache.set(test_key, "test", ttl=1)
            test_val = self.memory_cache.get(test_key)
            if test_val != "test":
                health['components']['memory_cache'] = {'healthy': False, 'error': 'Test failed'}
                health['healthy'] = False
            self.memory_cache.delete(test_key)
        except Exception as e:
            health['components']['memory_cache'] = {'healthy': False, 'error': str(e)}
            health['healthy'] = False

        return health
