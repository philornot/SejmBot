# core/types.py
"""
Definicje typów danych dla SejmBotScraper
Wszystkie struktury danych używane w aplikacji
"""

from datetime import datetime
from enum import Enum
from typing import TypedDict, List, Dict, Optional, Any, Union


class CacheType(Enum):
    """Typy cache dostępne w systemie"""
    API = "api"
    FILE = "file"
    MEMORY = "memory"
    ALL = "all"


class ScrapingMode(Enum):
    """Tryby scrapowania"""
    NORMAL = "normal"
    FORCE_REFRESH = "force_refresh"
    CACHE_ONLY = "cache_only"
    INCREMENTAL = "incremental"


class LogLevel(Enum):
    """Poziomy logowania"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


# === STRUKTURY DANYCH API ===

class TermInfo(TypedDict, total=False):
    """Informacje o kadencji"""
    num: int
    from_date: str  # Zmienione z 'from' na 'from_date'
    to: Optional[str]
    current: bool


class ProceedingInfo(TypedDict, total=False):
    """Informacje o posiedzeniu"""
    number: int
    title: str
    dates: List[str]
    current: bool
    num: int


class StatementInfo(TypedDict, total=False):
    """Informacje o wypowiedzi"""
    num: int
    name: str
    function: str
    club: str
    firstName: str
    lastName: str
    startDateTime: str
    endDateTime: str


class MPInfo(TypedDict, total=False):
    """Informacje o pośle"""
    id: int
    firstName: str
    lastName: str
    club: str
    districtName: str
    districtNum: int
    educationLevel: str
    numberOfVotes: int
    profession: str
    voivodeship: str
    email: str


class ClubInfo(TypedDict, total=False):
    """Informacje o klubie"""
    id: int
    name: str
    membersCount: int
    phone: str
    fax: str
    email: str


# === STRUKTURY WEWNĘTRZNE ===

class SpeakerData(TypedDict, total=False):
    """Dane mówcy w wypowiedzi"""
    name: str
    function: str
    club: str
    first_name: str
    last_name: str
    is_mp: bool
    mp_data: Optional[Dict[str, Any]]


class TimingData(TypedDict, total=False):
    """Dane czasowe wypowiedzi"""
    start_datetime: str
    end_datetime: str
    duration_seconds: Optional[int]


class ContentData(TypedDict, total=False):
    """Zawartość wypowiedzi"""
    text: str
    has_full_content: bool
    content_source: str


class TechnicalData(TypedDict, total=False):
    """Dane techniczne wypowiedzi"""
    api_url: str
    original_data: Dict[str, Any]


class ProcessedStatement(TypedDict):
    """Przetworzona wypowiedź"""
    num: int
    speaker: SpeakerData
    timing: TimingData
    content: ContentData
    technical: TechnicalData


class TranscriptMetadata(TypedDict):
    """Metadane transkryptu"""
    term: int
    proceeding_id: int
    date: str
    generated_at: str
    proceeding_info: Dict[str, Any]


class TranscriptData(TypedDict):
    """Kompletne dane transkryptu"""
    metadata: TranscriptMetadata
    statements: List[ProcessedStatement]


# === KONFIGURACJA ===

class APIConfig(TypedDict, total=False):
    """Konfiguracja API"""
    base_url: str
    timeout: int
    delay: float
    max_retries: int
    user_agent: str


class CacheConfig(TypedDict, total=False):
    """Konfiguracja cache"""
    memory_ttl_hours: int
    file_ttl_hours: int
    api_ttl_hours: int
    max_memory_entries: int
    enable_cleanup: bool


class ScrapingConfig(TypedDict, total=False):
    """Konfiguracja scrapowania"""
    mode: ScrapingMode
    fetch_full_statements: bool
    download_mp_photos: bool
    download_voting_stats: bool
    base_output_dir: str
    concurrent_downloads: int


class LoggingConfig(TypedDict, total=False):
    """Konfiguracja logowania"""
    level: LogLevel
    log_to_file: bool
    log_dir: str
    max_file_size_mb: int
    backup_count: int


class AppConfig(TypedDict, total=False):
    """Główna konfiguracja aplikacji"""
    api: APIConfig
    cache: CacheConfig
    scraping: ScrapingConfig
    logging: LoggingConfig
    default_term: int


# === STATYSTYKI ===

class ScrapingStats(TypedDict, total=False):
    """Statystyki scrapowania"""
    proceedings_processed: int
    statements_processed: int
    statements_with_full_content: int
    speakers_identified: int
    mp_data_enrichments: int
    errors: int
    future_proceedings_skipped: int
    proceedings_skipped_cache: int
    transcripts_skipped_cache: int
    start_time: datetime
    end_time: Optional[datetime]
    duration_seconds: Optional[float]


class CacheStats(TypedDict, total=False):
    """Statystyki cache"""
    memory_entries: int
    file_entries: int
    api_entries: int
    memory_hits: int
    memory_misses: int
    file_hits: int
    file_misses: int
    total_size_mb: float
    last_cleanup: Optional[str]


class MPScrapingStats(TypedDict, total=False):
    """Statystyki scrapowania posłów"""
    mps_downloaded: int
    clubs_downloaded: int
    photos_downloaded: int
    voting_stats_downloaded: int
    errors: int


# === CACHE ENTRIES ===

class CacheEntry(TypedDict):
    """Wpis w cache"""
    key: str
    value: Any
    timestamp: float
    ttl: Optional[float]
    size_bytes: Optional[int]


class FileCacheEntry(TypedDict, total=False):
    """Wpis cache'u plików"""
    path: str
    last_modified: float
    size: int
    checksum: Optional[str]
    metadata: Dict[str, Any]


# === POMOCNICZE TYPY ===

JsonSerializable = Union[Dict, List, str, int, float, bool, None]

ProcessingResult = TypedDict('ProcessingResult', {
    'success': bool,
    'data': Optional[Any],
    'error': Optional[str],
    'metadata': Dict[str, Any]
})

ValidationResult = TypedDict('ValidationResult', {
    'valid': bool,
    'errors': List[str],
    'warnings': List[str]
})


# === FUNKCJE POMOCNICZE ===

def create_empty_stats() -> ScrapingStats:
    """Tworzy pusty obiekt statystyk scrapowania"""
    return ScrapingStats(
        proceedings_processed=0,
        statements_processed=0,
        statements_with_full_content=0,
        speakers_identified=0,
        mp_data_enrichments=0,
        errors=0,
        future_proceedings_skipped=0,
        proceedings_skipped_cache=0,
        transcripts_skipped_cache=0,
        start_time=datetime.now(),
        end_time=None,
        duration_seconds=None
    )


def create_empty_mp_stats() -> MPScrapingStats:
    """Tworzy pusty obiekt statystyk scrapowania posłów"""
    return MPScrapingStats(
        mps_downloaded=0,
        clubs_downloaded=0,
        photos_downloaded=0,
        voting_stats_downloaded=0,
        errors=0
    )


def create_processing_result(success: bool, data: Any = None,
                             error: str = None, **metadata) -> ProcessingResult:
    """Tworzy standardowy wynik przetwarzania"""
    return ProcessingResult(
        success=success,
        data=data,
        error=error,
        metadata=metadata
    )


def create_validation_result(valid: bool, errors: List[str] = None,
                             warnings: List[str] = None) -> ValidationResult:
    """Tworzy wynik walidacji"""
    return ValidationResult(
        valid=valid,
        errors=errors or [],
        warnings=warnings or []
    )
