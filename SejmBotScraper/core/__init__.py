"""Moduł core — typy i wyjątki podstawowe"""

from typing import Dict, Any

# === TYPY DANYCH ===

# Podstawowe typy dla API
TermInfo = Dict[str, Any]
ProceedingInfo = Dict[str, Any]
StatementInfo = Dict[str, Any]
MPInfo = Dict[str, Any]
ClubInfo = Dict[str, Any]

# Typy dla przetworzonego contentu
ProcessedStatement = Dict[str, Any]
TranscriptData = Dict[str, Any]

# Typy statystyk
ScrapingStats = Dict[str, int]
MPScrapingStats = Dict[str, int]


def create_empty_transcript_stats() -> ScrapingStats:
    """Tworzy pustą strukturę statystyk scrapowania stenogramów"""
    return {
        'proceedings_processed': 0,
        'statements_processed': 0,
        'statements_with_full_content': 0,
        'speakers_identified': 0,
        'mp_data_enrichments': 0,
        'errors': 0,
        'future_proceedings_skipped': 0,
        'proceedings_skipped_cache': 0,
        'transcripts_skipped_cache': 0
    }


def create_empty_mp_stats() -> MPScrapingStats:
    """Tworzy pustą strukturę statystyk scrapowania posłów"""
    return {
        'mps_downloaded': 0,
        'clubs_downloaded': 0,
        'photos_downloaded': 0,
        'voting_stats_downloaded': 0,
        'errors': 0
    }


# === WYJĄTKI ===

class SejmScraperError(Exception):
    """Bazowy wyjątek dla scraperów Sejmu"""
    pass


class ConfigValidationError(SejmScraperError):
    """Błąd walidacji konfiguracji"""
    pass


class APIError(SejmScraperError):
    """Błąd komunikacji z API"""
    pass


class CacheError(SejmScraperError):
    """Błąd cache"""
    pass


class FileOperationError(SejmScraperError):
    """Błąd operacji na plikach"""
    pass


# === EKSPORTY ===

__all__ = [
    # Typy
    'TermInfo',
    'ProceedingInfo',
    'StatementInfo',
    'MPInfo',
    'ClubInfo',
    'ProcessedStatement',
    'TranscriptData',
    'ScrapingStats',
    'MPScrapingStats',

    # Factory functions
    'create_empty_transcript_stats',
    'create_empty_mp_stats',

    # Wyjątki
    'SejmScraperError',
    'ConfigValidationError',
    'APIError',
    'CacheError',
    'FileOperationError'
]
