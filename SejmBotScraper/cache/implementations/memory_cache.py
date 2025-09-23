"""
Implementacja cache w pamięci
"""

import logging
import time
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)


class MemoryCacheImpl:
    """Implementacja cache w pamięci"""

    def __init__(self, config=None):
        """
        Inicjalizuje cache w pamięci

        Args:
            config: konfiguracja cache
        """
        self.config = config or {}

        # Konfiguracja
        self.default_ttl = self.config.get('default_ttl', 3600)  # 1 godzina
        self.max_entries = self.config.get('max_entries', 10000)

        # Storage
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._stats = {
            'hits': 0,
            'misses': 0,
            'sets': 0,
            'deletes': 0,
            'cleanups': 0
        }

        logger.debug(f"Zainicjalizowano MemoryCacheImpl (max_entries={self.max_entries})")

    def get(self, key: str) -> Optional[Any]:
        """Pobiera wartość z cache"""
        if key not in self._cache:
            self._stats['misses'] += 1
            return None

        entry = self._cache[key]

        # Sprawdź wygaśnięcie
        if self._is_expired(entry):
            del self._cache[key]
            self._stats['misses'] += 1
            return None

        # Aktualizuj last_accessed
        entry['last_accessed'] = time.time()
        self._stats['hits'] += 1

        return entry['value']

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Zapisuje wartość do cache"""
        if ttl is None:
            ttl = self.default_ttl

        now = time.time()
        expires_at = now + ttl if ttl > 0 else None

        # Sprawdź limit
        if len(self._cache) >= self.max_entries:
            self._evict_oldest()

        self._cache[key] = {
            'value': value,
            'created_at': now,
            'last_accessed': now,
            'expires_at': expires_at,
            'ttl': ttl
        }

        self._stats['sets'] += 1

    def delete(self, key: str) -> bool:
        """Usuwa wpis z cache"""
        if key in self._cache:
            del self._cache[key]
            self._stats['deletes'] += 1
            return True
        return False

    def has(self, key: str) -> bool:
        """Sprawdza czy klucz istnieje"""
        if key not in self._cache:
            return False

        entry = self._cache[key]
        if self._is_expired(entry):
            del self._cache[key]
            return False

        return True

    def get_age(self, key: str) -> Optional[float]:
        """Zwraca wiek wpisu w sekundach"""
        if key not in self._cache:
            return None

        entry = self._cache[key]
        if self._is_expired(entry):
            del self._cache[key]
            return None

        return time.time() - entry['created_at']

    def clear(self, pattern: str = None) -> None:
        """Czyści cache lub wpisy pasujące do wzorca"""
        if pattern is None:
            count = len(self._cache)
            self._cache.clear()
            logger.info(f"Wyczyszczono memory cache ({count} wpisów)")
        else:
            # Usuń wpisy pasujące do wzorca
            keys_to_delete = []
            for key in self._cache.keys():
                if pattern.replace('*', '') in key:
                    keys_to_delete.append(key)

            for key in keys_to_delete:
                del self._cache[key]

            logger.debug(f"Usunięto {len(keys_to_delete)} wpisów pasujących do '{pattern}'")

    def cleanup_expired(self) -> int:
        """Usuwa wygasłe wpisy"""
        expired_keys = []

        for key, entry in self._cache.items():
            if self._is_expired(entry):
                expired_keys.append(key)

        for key in expired_keys:
            del self._cache[key]

        if expired_keys:
            logger.debug(f"Usunięto {len(expired_keys)} wygasłych wpisów")

        self._stats['cleanups'] += 1
        return len(expired_keys)

    def get_stats(self) -> Dict[str, Any]:
        """Zwraca statystyki cache"""
        # Oblicz rozmiar
        import sys
        total_size = 0
        for entry in self._cache.values():
            try:
                total_size += sys.getsizeof(entry['value'])
            except:
                total_size += 100  # przybliżenie

        size_mb = total_size / 1024 / 1024

        return {
            'entries': len(self._cache),
            'size_mb': round(size_mb, 2),
            'max_entries': self.max_entries,
            'hits': self._stats['hits'],
            'misses': self._stats['misses'],
            'hit_rate': self._stats['hits'] / max(1, self._stats['hits'] + self._stats['misses']),
            'sets': self._stats['sets'],
            'deletes': self._stats['deletes'],
            'cleanups': self._stats['cleanups'],
            'api_entries': len([k for k in self._cache.keys() if k.startswith('api_')])
        }

    def get_size_mb(self) -> float:
        """Zwraca rozmiar cache w MB"""
        stats = self.get_stats()
        return stats['size_mb']

    def _is_expired(self, entry: Dict[str, Any]) -> bool:
        """Sprawdza czy wpis wygasł"""
        expires_at = entry.get('expires_at')
        if expires_at is None:
            return False
        return time.time() > expires_at

    def _evict_oldest(self) -> None:
        """Usuwa najstarsze wpisy"""
        if not self._cache:
            return

        # Usuń 10% najstarszych
        entries_to_remove = max(1, len(self._cache) // 10)

        # Sortuj według last_accessed
        sorted_entries = sorted(
            self._cache.items(),
            key=lambda x: x[1]['last_accessed']
        )

        for i in range(entries_to_remove):
            key = sorted_entries[i][0]
            del self._cache[key]

        logger.debug(f"Usunięto {entries_to_remove} najstarszych wpisów")

    def get_keys(self) -> List[str]:
        """Zwraca listę kluczy"""
        return list(self._cache.keys())
