# __init__.py
"""
SejmBotScraper v3.0 - Modularny scraper danych Sejmu RP

Główny pakiet aplikacji - udostępnia czyste interfejsy dla użytkowników.
Implementacje znajdują się w odpowiednich modułach.

Przykłady użycia:

    # Podstawowe scrapowanie
    from sejmbot_scraper import SejmScraper

    scraper = SejmScraper()
    stats = scraper.scrape_term(10)
    print(f"Przetworzone wypowiedzi: {stats['statements_processed']}")

    # Konfiguracja
    from sejmbot_scraper import get_settings, setup_logging

    settings = get_settings()
    setup_logging(settings)
    settings.print_summary()

    # API
    from sejmbot_scraper import SejmAPIInterface

    api = SejmAPIInterface()
    terms = api.get_terms()

    # Cache
    from sejmbot_scraper import CacheInterface

    cache = CacheInterface()
    stats = cache.get_stats()

    # File Manager
    from sejmbot_scraper import FileManagerInterface

    file_mgr = FileManagerInterface()
    summary = file_mgr.get_term_summary(10)
"""

import logging
import sys
from pathlib import Path

# Wersja aplikacji
__version__ = "3.0.0"
__author__ = "SejmBot Team"
__description__ = "Modularny scraper danych Sejmu Rzeczypospolitej Polskiej"

# Dodaj główny katalog do sys.path jeśli potrzeba
_current_dir = Path(__file__).parent
if str(_current_dir) not in sys.path:
    sys.path.insert(0, str(_current_dir))

# Konfiguruj logging dla całej aplikacji
logging.getLogger(__name__).addHandler(logging.NullHandler())

# === GŁÓWNE INTERFEJSY ===

# Scraper - główny punkt wejścia
from .scraping.scraper import SejmScraper

# API Client
from .api.client import SejmAPIInterface

# Cache Manager
from .cache.manager import CacheInterface

# File Manager
from .storage.file_manager import FileManagerInterface

# CLI Commands
from .cli.commands import CLICommands

# Konfiguracja
from .config.settings import get_settings, setup_logging, validate_environment

# Typy danych
from .core.types import (
    # Główne typy
    ScrapingStats, MPScrapingStats, CacheStats,
    TermInfo, ProceedingInfo, StatementInfo, MPInfo, ClubInfo,
    ProcessedStatement, TranscriptData,

    # Konfiguracja
    ScrapingConfig, APIConfig, CacheConfig, LoggingConfig, AppConfig,

    # Enums
    ScrapingMode, CacheType, LogLevel,

    # Pomocnicze
    create_empty_stats, create_empty_mp_stats,
    create_processing_result, create_validation_result
)

# Wyjątki
from .core.exceptions import (
    # Główny wyjątek
    SejmScraperError,

    # Wyjątki API
    APIError, APITimeoutError, APIRateLimitError, APIResponseError,

    # Wyjątki Cache
    CacheError, CacheKeyError, CacheSerializationError,

    # Wyjątki plików
    FileError, FileNotFoundError, FilePermissionError,

    # Wyjątki konfiguracji
    ConfigError, ConfigValidationError,

    # Wyjątki scrapowania
    ScrapingError, DataProcessingError, DataValidationError,

    # Wyjątki logiki biznesowej
    TermNotFoundError, ProceedingNotFoundError, MPNotFoundError,

    # Pomocnicze
    validate_term, validate_proceeding, validate_date_format
)


# === FUNKCJE POMOCNICZE ===

def create_scraper(config_path: str = None) -> SejmScraper:
    """
    Tworzy skonfigurowany scraper

    Args:
        config_path: ścieżka do pliku .env (opcjonalna)

    Returns:
        Skonfigurowany SejmScraper

    Example:
        scraper = create_scraper('.env.production')
        stats = scraper.scrape_term(10)
    """
    if config_path:
        settings = get_settings(config_path)
        setup_logging(settings)
    else:
        settings = get_settings()
        setup_logging(settings)

    # Utwórz katalogi
    settings.create_directories()

    return SejmScraper(settings.get('scraping'))


def create_api_client(config_path: str = None) -> SejmAPIInterface:
    """
    Tworzy skonfigurowany klient API

    Args:
        config_path: ścieżka do pliku .env (opcjonalna)

    Returns:
        Skonfigurowany SejmAPIInterface

    Example:
        api = create_api_client()
        terms = api.get_terms()
    """
    if config_path:
        settings = get_settings(config_path)
    else:
        settings = get_settings()

    cache = CacheInterface(settings.get('cache'))
    return SejmAPIInterface(cache, settings.get('api'))


def quick_scrape(term: int, fetch_full_statements: bool = True, **kwargs) -> ScrapingStats:
    """
    Szybkie scrapowanie kadencji z domyślną konfiguracją

    Args:
        term: numer kadencji
        fetch_full_statements: czy pobierać pełną treść wypowiedzi
        **kwargs: dodatkowe opcje

    Returns:
        Statystyki scrapowania

    Example:
        stats = quick_scrape(10, fetch_full_statements=True)
        print(f"Pobrano {stats['statements_processed']} wypowiedzi")
    """
    scraper = create_scraper()
    return scraper.scrape_term(term, fetch_full_statements=fetch_full_statements, **kwargs)


def quick_health_check() -> dict:
    """
    Szybkie sprawdzenie stanu aplikacji

    Returns:
        Raport zdrowia aplikacji

    Example:
        health = quick_health_check()
        if health['healthy']:
            print("Wszystko działa prawidłowo")
    """
    try:
        scraper = create_scraper()
        return scraper.health_check()
    except Exception as e:
        return {
            'healthy': False,
            'error': str(e),
            'timestamp': str(Path(__file__).stat().st_mtime)
        }


def get_version_info() -> dict:
    """
    Zwraca informacje o wersji aplikacji

    Returns:
        Słownik z informacjami o wersji

    Example:
        info = get_version_info()
        print(f"SejmBotScraper v{info['version']}")
    """
    return {
        'version': __version__,
        'author': __author__,
        'description': __description__,
        'python_version': sys.version,
        'platform': sys.platform
    }


def validate_installation() -> dict:
    """
    Waliduje instalację aplikacji

    Returns:
        Raport walidacji instalacji

    Example:
        report = validate_installation()
        if not report['valid']:
            print("Problemy:", report['issues'])
    """
    issues = []
    warnings = []

    try:
        # Sprawdź konfigurację
        settings = get_settings()
        config_errors = settings.get_validation_errors()
        if config_errors:
            issues.extend(config_errors)

        # Sprawdź środowisko
        env_warnings = validate_environment()
        warnings.extend(env_warnings)

        # Sprawdź API
        try:
            api = create_api_client()
            if not api.is_healthy():
                warnings.append("API Sejmu nie odpowiada")
        except Exception as e:
            issues.append(f"Błąd inicjalizacji API: {e}")

        # Sprawdź uprawnienia do katalogów
        try:
            settings.create_directories()
        except Exception as e:
            issues.append(f"Nie można utworzyć katalogów: {e}")

    except Exception as e:
        issues.append(f"Krytyczny błąd walidacji: {e}")

    return {
        'valid': len(issues) == 0,
        'issues': issues,
        'warnings': warnings,
        'version': __version__
    }


# === INICJALIZACJA ===

def _initialize_logging():
    """Inicjalizacja podstawowego logowania"""
    try:
        # Podstawowa konfiguracja logowania
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )

        # Ustaw poziom logowania dla zewnętrznych bibliotek
        logging.getLogger('requests').setLevel(logging.WARNING)
        logging.getLogger('urllib3').setLevel(logging.WARNING)

    except Exception:
        # Jeśli nie można skonfigurować logowania, kontynuuj bez niego
        pass


# Zainicjalizuj podstawowe logowanie przy imporcie
_initialize_logging()

# Logger dla tego modułu
logger = logging.getLogger(__name__)
logger.debug(f"Zainicjalizowano SejmBotScraper v{__version__}")

# === EKSPORTOWANE SYMBOLE ===

__all__ = [
    # Wersja
    '__version__', '__author__', '__description__',

    # Główne klasy
    'SejmScraper', 'SejmAPIInterface', 'CacheInterface', 'FileManagerInterface', 'CLICommands',

    # Konfiguracja
    'get_settings', 'setup_logging', 'validate_environment',

    # Typy danych
    'ScrapingStats', 'MPScrapingStats', 'CacheStats',
    'TermInfo', 'ProceedingInfo', 'StatementInfo', 'MPInfo', 'ClubInfo',
    'ProcessedStatement', 'TranscriptData',
    'ScrapingConfig', 'APIConfig', 'CacheConfig', 'LoggingConfig', 'AppConfig',
    'ScrapingMode', 'CacheType', 'LogLevel',

    # Wyjątki główne
    'SejmScraperError', 'APIError', 'CacheError', 'FileError', 'ConfigError', 'ScrapingError',
    'TermNotFoundError', 'ProceedingNotFoundError', 'MPNotFoundError',

    # Funkcje pomocnicze
    'create_scraper', 'create_api_client', 'quick_scrape', 'quick_health_check',
    'get_version_info', 'validate_installation',
    'create_empty_stats', 'create_empty_mp_stats',
    'validate_term', 'validate_proceeding', 'validate_date_format',
]
