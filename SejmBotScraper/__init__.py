# __init__.py
"""
SejmBotScraper v3.0 - Modularny scraper danych Sejmu RP

Główny pakiet aplikacji - udostępnia czyste interfejsy dla użytkowników.
Implementacje znajdują się w odpowiednich modułach.

Przykłady użycia:

    # Podstawowe scrapowanie
    from SejmBotScraper import SejmScraper

    scraper = SejmScraper()
    stats = scraper.scrape_term(10)
    print(f"Przetworzone wypowiedzi: {stats['statements_processed']}")

    # Konfiguracja
    from SejmBotScraper import get_settings, setup_logging

    settings = get_settings()
    setup_logging(settings)
    settings.print_summary()

    # API
    from SejmBotScraper import SejmAPIInterface

    api = SejmAPIInterface()
    terms = api.get_terms()

    # Cache
    from SejmBotScraper import CacheInterface

    cache = CacheInterface()
    stats = cache.get_stats()

    # File Manager
    from SejmBotScraper import FileManagerInterface

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
try:
    from .scraping.scraper import SejmScraper
except ImportError:
    # Fallback - użyj oryginalnego scrapera z root
    try:
        from scraper import SejmScraper
    except ImportError:
        # Mock scraper jeśli nic nie działa
        class SejmScraper:
            def __init__(self, config=None):
                self.config = config or {}

            def scrape_term(self, term, **kwargs):
                return {'errors': 1, 'message': 'Scraper not available'}

            def get_available_terms(self):
                return []

            def get_term_proceedings_summary(self, term):
                return []

            def get_cache_stats(self):
                return {'memory_cache': {'entries': 0}, 'file_cache': {'entries': 0}}

            def clear_cache(self):
                pass

            def cleanup_cache(self):
                pass

# API Client
try:
    from .api.client import SejmAPIInterface
except ImportError:
    # Mock API Interface
    class SejmAPIInterface:
        def __init__(self, cache=None, config=None):
            pass

        def get_terms(self):
            return []

        def is_healthy(self):
            return False

# Cache Manager
try:
    from .cache.manager import CacheInterface
except ImportError:
    # Mock Cache Interface
    class CacheInterface:
        def __init__(self, config=None):
            pass

        def get_stats(self):
            return {}

# File Manager
try:
    from .storage.file_manager import FileManagerInterface
except ImportError:
    # Mock File Manager Interface
    class FileManagerInterface:
        def __init__(self, config=None):
            pass

        def get_term_summary(self, term):
            return []

# CLI Commands
try:
    from .cli.commands import CLICommands
except ImportError:
    # Mock CLI Commands
    class CLICommands:
        def __init__(self, config=None):
            pass

# Konfiguracja
from .config.settings import get_settings, setup_logging, validate_environment

# Typy danych
try:
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
except ImportError:
    # Fallback types - podstawowe definicje
    ScrapingStats = dict
    MPScrapingStats = dict
    CacheStats = dict
    TermInfo = dict
    ProceedingInfo = dict
    StatementInfo = dict
    MPInfo = dict
    ClubInfo = dict
    ProcessedStatement = dict
    TranscriptData = dict
    ScrapingConfig = dict
    APIConfig = dict
    CacheConfig = dict
    LoggingConfig = dict
    AppConfig = dict


    def create_empty_stats():
        return {'errors': 0, 'statements_processed': 0}


    def create_empty_mp_stats():
        return {'errors': 0, 'mps_downloaded': 0}


    def create_processing_result(success, data=None, error=None, **metadata):
        return {'success': success, 'data': data, 'error': error, 'metadata': metadata}


    def create_validation_result(valid, errors=None, warnings=None):
        return {'valid': valid, 'errors': errors or [], 'warnings': warnings or []}

# Wyjątki
try:
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
except ImportError:
    # Fallback exceptions
    class SejmScraperError(Exception):
        pass


    class APIError(SejmScraperError):
        pass


    class APITimeoutError(APIError):
        pass


    class APIRateLimitError(APIError):
        pass


    class APIResponseError(APIError):
        pass


    class CacheError(SejmScraperError):
        pass


    class CacheKeyError(CacheError):
        pass


    class CacheSerializationError(CacheError):
        pass


    class FileError(SejmScraperError):
        pass


    class FileNotFoundError(FileError):
        pass


    class FilePermissionError(FileError):
        pass


    class ConfigError(SejmScraperError):
        pass


    class ConfigValidationError(ConfigError):
        pass


    class ScrapingError(SejmScraperError):
        pass


    class DataProcessingError(ScrapingError):
        pass


    class DataValidationError(ScrapingError):
        pass


    class TermNotFoundError(SejmScraperError):
        pass


    class ProceedingNotFoundError(SejmScraperError):
        pass


    class MPNotFoundError(SejmScraperError):
        pass


    def validate_term(term):
        return isinstance(term, int) and 1 <= term <= 20


    def validate_proceeding(proceeding):
        return isinstance(proceeding, int) and proceeding > 0


    def validate_date_format(date):
        return isinstance(date, str) and len(date) == 10


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
    try:
        if config_path:
            settings = get_settings(config_path)
            setup_logging(settings)
        else:
            settings = get_settings()
            setup_logging(settings)

        # Utwórz katalogi
        settings.create_directories()

        # Utwórz scraper z konfiguracją
        return SejmScraper(settings.get('scraping'))
    except Exception:
        # Fallback dla braku modułowej konfiguracji
        settings = get_settings()
        return SejmScraper()


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
    try:
        if config_path:
            settings = get_settings(config_path)
        else:
            settings = get_settings()

        cache = CacheInterface(settings.get('cache'))
        return SejmAPIInterface(cache, settings.get('api'))
    except Exception:
        return SejmAPIInterface()


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

    # Wyjątki główne
    'SejmScraperError', 'APIError', 'CacheError', 'FileError', 'ConfigError', 'ScrapingError',
    'TermNotFoundError', 'ProceedingNotFoundError', 'MPNotFoundError',

    # Funkcje pomocnicze
    'create_scraper', 'create_api_client', 'quick_scrape', 'quick_health_check',
    'get_version_info', 'validate_installation',
    'create_empty_stats', 'create_empty_mp_stats',
    'validate_term', 'validate_proceeding', 'validate_date_format',
]
