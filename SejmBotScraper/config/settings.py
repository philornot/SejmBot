"""
Konfiguracja aplikacji SejmBotScraper
Bazuje na zmiennych środowiskowych z fallbackami do wartości domyślnych
"""

import logging
import os
from pathlib import Path
from typing import Dict, Any, Optional, List

from SejmBotScraper.core.exceptions import ConfigError, ConfigValidationError
from SejmBotScraper.core.types import (
    APIConfig, CacheConfig, ScrapingConfig, LoggingConfig, AppConfig,
    ScrapingMode, LogLevel
)


def load_env_file(env_path: str = '.env') -> None:
    """
    Ładuje zmienne środowiskowe z pliku .env

    Args:
        env_path: ścieżka do pliku .env
    """
    env_file = Path(env_path)
    if env_file.exists():
        try:
            with open(env_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = value.strip().strip('"\'')  # usuń cudzysłowy
                        if key and not os.getenv(key):  # nie nadpisuj istniejących zmiennych
                            os.environ[key] = value
        except Exception as e:
            logging.warning(f"Ostrzeżenie: nie można załadować {env_path}: {e}")


def get_bool_env(key: str, default: bool = False) -> bool:
    """Pobiera zmienną środowiskową jako bool"""
    value = os.getenv(key, str(default)).lower()
    return value in ('true', '1', 'yes', 'on', 'tak')


def get_int_env(key: str, default: int) -> int:
    """Pobiera zmienną środowiskową jako int"""
    try:
        return int(os.getenv(key, str(default)))
    except (ValueError, TypeError):
        return default


def get_float_env(key: str, default: float) -> float:
    """Pobiera zmienną środowiskową jako float"""
    try:
        return float(os.getenv(key, str(default)))
    except (ValueError, TypeError):
        return default


def get_list_env(key: str, default: List[str], separator: str = ',') -> List[str]:
    """Pobiera zmienną środowiskową jako listę"""
    value = os.getenv(key)
    if not value:
        return default
    return [item.strip() for item in value.split(separator) if item.strip()]


class Settings:
    """Główna klasa konfiguracji aplikacji"""

    def __init__(self, env_file: Optional[str] = None):
        """
        Inicjalizuje konfigurację

        Args:
            env_file: ścieżka do pliku .env (opcjonalne)
        """
        if env_file:
            load_env_file(env_file)
        else:
            load_env_file()

        self._config = self._load_config()
        self._validate_config()

    @staticmethod
    def _load_config() -> AppConfig:
        """Ładuje konfigurację ze zmiennych środowiskowych"""

        # === KONFIGURACJA API ===
        api_config = APIConfig(
            base_url=os.getenv('API_BASE_URL', 'https://api.sejm.gov.pl'),
            timeout=get_int_env('REQUEST_TIMEOUT', 30),
            delay=get_float_env('REQUEST_DELAY', 1.0),
            max_retries=get_int_env('MAX_RETRIES', 3),
            user_agent=os.getenv('USER_AGENT', 'SejmBotScraper/3.0 (Educational Purpose)')
        )

        # === KONFIGURACJA CACHE ===
        cache_config = CacheConfig(
            memory_ttl_hours=get_int_env('CACHE_MEMORY_TTL_HOURS', 4),
            file_ttl_hours=get_int_env('CACHE_FILE_TTL_HOURS', 24),
            api_ttl_hours=get_int_env('CACHE_API_TTL_HOURS', 6),
            max_memory_entries=get_int_env('CACHE_MAX_MEMORY_ENTRIES', 1000),
            enable_cleanup=get_bool_env('CACHE_ENABLE_CLEANUP', True)
        )

        # === KONFIGURACJA SCRAPOWANIA ===
        scraping_mode_str = os.getenv('SCRAPING_MODE', 'normal').lower()
        try:
            scraping_mode = ScrapingMode(scraping_mode_str)
        except ValueError:
            scraping_mode = ScrapingMode.NORMAL

        scraping_config = ScrapingConfig(
            mode=scraping_mode,
            fetch_full_statements=get_bool_env('FETCH_FULL_STATEMENTS', True),
            download_mp_photos=get_bool_env('DOWNLOAD_MP_PHOTOS', True),
            download_voting_stats=get_bool_env('DOWNLOAD_VOTING_STATS', True),
            base_output_dir=os.getenv('BASE_OUTPUT_DIR', 'data_sejm'),
            concurrent_downloads=get_int_env('CONCURRENT_DOWNLOADS', 3)
        )

        # === KONFIGURACJA LOGOWANIA ===
        log_level_str = os.getenv('LOG_LEVEL', 'INFO').upper()
        try:
            log_level = LogLevel(log_level_str)
        except ValueError:
            log_level = LogLevel.INFO

        logging_config = LoggingConfig(
            level=log_level,
            log_to_file=get_bool_env('LOG_TO_FILE', True),
            log_dir=os.getenv('LOG_DIR', 'logs'),
            max_file_size_mb=get_int_env('LOG_MAX_FILE_SIZE_MB', 50),
            backup_count=get_int_env('LOG_BACKUP_COUNT', 5)
        )

        return AppConfig(
            api=api_config,
            cache=cache_config,
            scraping=scraping_config,
            logging=logging_config,
            default_term=get_int_env('DEFAULT_TERM', 10)
        )

    def _validate_config(self) -> None:
        """Waliduje konfigurację i rzuca wyjątki w przypadku błędów"""
        errors = []

        # Waliduj API
        if not self._config['api']['base_url'].startswith(('http://', 'https://')):
            errors.append("API_BASE_URL musi zaczynać się od http:// lub https://")

        if self._config['api']['timeout'] < 1:
            errors.append(f"REQUEST_TIMEOUT zbyt mały: {self._config['api']['timeout']} (min: 1)")

        if self._config['api']['delay'] < 0.1:
            errors.append(f"REQUEST_DELAY zbyt mały: {self._config['api']['delay']} (min: 0.1)")

        # Waliduj cache
        if self._config['cache']['max_memory_entries'] < 10:
            errors.append(
                f"CACHE_MAX_MEMORY_ENTRIES zbyt mały: {self._config['cache']['max_memory_entries']} (min: 10)")

        # Waliduj scrapowanie
        if self._config['scraping']['concurrent_downloads'] < 1:
            errors.append(
                f"CONCURRENT_DOWNLOADS zbyt mały: {self._config['scraping']['concurrent_downloads']} (min: 1)")

        if self._config['scraping']['concurrent_downloads'] > 10:
            errors.append(
                f"CONCURRENT_DOWNLOADS zbyt duży: {self._config['scraping']['concurrent_downloads']} (max: 10)")

        # Waliduj domyślną kadencję
        if not (1 <= self._config['default_term'] <= 20):
            errors.append(f"DEFAULT_TERM nieprawidłowy: {self._config['default_term']} (oczekiwano 1-20)")

        # Waliduj katalogi
        try:
            output_dir = Path(self._config['scraping']['base_output_dir'])
            log_dir = Path(self._config['logging']['log_dir'])

            # Spróbuj utworzyć katalogi
            output_dir.mkdir(parents=True, exist_ok=True)
            log_dir.mkdir(parents=True, exist_ok=True)

        except Exception as e:
            errors.append(f"Nie można utworzyć katalogów: {e}")

        if errors:
            raise ConfigValidationError(
                f"Znaleziono {len(errors)} błędów konfiguracji",
                details={'validation_errors': errors}
            )

    def get(self, key: str, default: Any = None) -> Any:
        """
        Pobiera wartość konfiguracji

        Args:
            key: klucz w formacie 'section.key' np. 'api.base_url'
            default: wartość domyślna

        Returns:
            Wartość konfiguracji
        """
        try:
            parts = key.split('.')
            value = self._config

            for part in parts:
                value = value[part]

            return value
        except (KeyError, TypeError):
            if default is not None:
                return default
            raise ConfigError(f"Nie znaleziono klucza konfiguracji: {key}")

    def set(self, key: str, value: Any) -> None:
        """
        Ustawia wartość konfiguracji (runtime only)

        Args:
            key: klucz w formacie 'section.key'
            value: wartość
        """
        parts = key.split('.')
        config = self._config

        for part in parts[:-1]:
            if part not in config:
                config[part] = {}
            config = config[part]

        config[parts[-1]] = value

    @property
    def config(self) -> AppConfig:
        """Zwraca pełną konfigurację"""
        return self._config

    def print_summary(self) -> None:
        """Wyświetla podsumowanie konfiguracji"""
        print("=" * 70)
        print("🔧 KONFIGURACJA SEJMBOT SCRAPER v3.0")
        print("=" * 70)
        print(f"API URL:           {self.get('api.base_url')}")
        print(f"Domyślna kadencja: {self.get('default_term')}")
        print(f"Katalog wyjścia:   {self.get('scraping.base_output_dir')}")
        print(f"Katalog logów:     {self.get('logging.log_dir')}")
        print(f"Poziom logów:      {self.get('logging.level').value}")
        print()

        print("📄 STENOGRAMY:")
        print(f"  Pełny tekst:       {'✅' if self.get('scraping.fetch_full_statements') else '❌'}")
        print(f"  Tryb scrapowania: {self.get('scraping.mode').value}")
        print(f"  Równoległe pobieranie: {self.get('scraping.concurrent_downloads')}")
        print()

        print("👥 POSŁOWIE:")
        print(f"  Zdjęcia:           {'✅' if self.get('scraping.download_mp_photos') else '❌'}")
        print(f"  Statystyki:        {'✅' if self.get('scraping.download_voting_stats') else '❌'}")
        print()

        print("💾 CACHE:")
        print(f"  Pamięć (TTL):      {self.get('cache.memory_ttl_hours')}h")
        print(f"  Pliki (TTL):       {self.get('cache.file_ttl_hours')}h")
        print(f"  API (TTL):         {self.get('cache.api_ttl_hours')}h")
        print(f"  Max wpisy pamięci: {self.get('cache.max_memory_entries')}")
        print(f"  Auto czyszczenie:  {'✅' if self.get('cache.enable_cleanup') else '❌'}")
        print()

        print("🌐 ZAPYTANIA:")
        print(f"  Timeout:           {self.get('api.timeout')}s")
        print(f"  Opóźnienie:        {self.get('api.delay')}s")
        print(f"  Powtórzenia:       {self.get('api.max_retries')}")
        print("=" * 70)

    def create_directories(self) -> bool:
        """
        Tworzy wszystkie wymagane katalogi

        Returns:
            True, jeśli sukces
        """
        try:
            dirs_to_create = [
                Path(self.get('scraping.base_output_dir')),
                Path(self.get('logging.log_dir')),
                Path(self.get('scraping.base_output_dir')) / 'stenogramy',
                Path(self.get('scraping.base_output_dir')) / 'poslowie',
                Path(self.get('scraping.base_output_dir')) / 'kluby',
                Path(self.get('scraping.base_output_dir')) / 'cache',
                Path(self.get('scraping.base_output_dir')) / 'temp'
            ]

            for directory in dirs_to_create:
                directory.mkdir(parents=True, exist_ok=True)

            return True

        except Exception as e:
            logging.error(f"Błąd tworzenia katalogów: {e}")
            return False

    def get_validation_errors(self) -> List[str]:
        """
        Zwraca listę błędów walidacji (bez rzucania wyjątków)

        Returns:
            Lista błędów walidacji
        """
        errors = []

        try:
            self._validate_config()
        except ConfigValidationError as e:
            if hasattr(e, 'details') and 'validation_errors' in e.details:
                errors = e.details['validation_errors']
            else:
                errors = [str(e)]

        return errors

    def to_dict(self) -> Dict[str, Any]:
        """Zwraca konfigurację jako słownik (dla serializacji)"""

        def convert_enums(obj):
            if hasattr(obj, 'value'):  # Enum
                return obj.value
            elif isinstance(obj, dict):
                return {k: convert_enums(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_enums(item) for item in obj]
            return obj

        return convert_enums(self._config)


# === GLOBALNA INSTANCJA KONFIGURACJI ===

# Singleton pattern dla globalnej konfiguracji
_settings_instance = None


def get_settings(env_file: Optional[str] = None) -> Settings:
    """
    Zwraca globalną instancję ustawień

    Args:
        env_file: ścieżka do pliku .env (tylko przy pierwszym wywołaniu)

    Returns:
        Instancja Settings
    """
    global _settings_instance

    if _settings_instance is None:
        _settings_instance = Settings(env_file)

    return _settings_instance


def reload_settings(env_file: Optional[str] = None) -> Settings:
    """
    Wymusza przeładowanie konfiguracji

    Args:
        env_file: ścieżka do pliku .env

    Returns:
        Nowa instancja Settings
    """
    global _settings_instance
    _settings_instance = Settings(env_file)
    return _settings_instance


# === FUNKCJE POMOCNICZE ===

def setup_logging(settings: Settings) -> None:
    """
    Konfiguruje system logowania na podstawie ustawień

    Args:
        settings: instancja Settings
    """
    log_level = getattr(logging, settings.get('logging.level').value)
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

    # Konfiguracja podstawowa
    logging.basicConfig(level=log_level, format=log_format)

    # Dodaj handler pliku, jeśli włączony
    if settings.get('logging.log_to_file'):
        from logging.handlers import RotatingFileHandler

        log_dir = Path(settings.get('logging.log_dir'))
        log_dir.mkdir(parents=True, exist_ok=True)

        log_file = log_dir / 'sejmbot_scraper.log'

        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=settings.get('logging.max_file_size_mb') * 1024 * 1024,
            backupCount=settings.get('logging.backup_count'),
            encoding='utf-8'
        )
        file_handler.setLevel(log_level)
        file_handler.setFormatter(logging.Formatter(log_format))

        # Dodaj handler do root loggera
        logging.getLogger().addHandler(file_handler)


def validate_environment() -> List[str]:
    """
    Waliduje środowisko uruchomieniowe

    Returns:
        Lista ostrzeżeń/błędów środowiska
    """
    warnings = []

    # Sprawdź dostępność modułów
    required_modules = ['requests', 'pathlib']
    for module in required_modules:
        try:
            __import__(module)
        except ImportError:
            warnings.append(f"Brakuje wymaganego modułu: {module}")

    # Sprawdź uprawnienia do zapisu
    try:
        test_dir = Path('test_permissions')
        test_dir.mkdir(exist_ok=True)
        test_file = test_dir / 'test.txt'
        test_file.write_text('test')
        test_file.unlink()
        test_dir.rmdir()
    except Exception as e:
        warnings.append(f"Brak uprawnień do zapisu: {e}")

    return warnings
