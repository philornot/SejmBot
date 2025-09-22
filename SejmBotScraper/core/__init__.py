"""
Core module for SejmBotScraper
Naprawiona wersja z działającą factory function
"""

import logging
from typing import Dict, Optional, Any

logger = logging.getLogger(__name__)


def create_scraper(config: Optional[Dict] = None, config_override: Optional[Dict] = None, **kwargs) -> 'SejmScraper':
    """
    NAPRAWIONA factory function - tworzy główny scraper

    Args:
        config: konfiguracja scrapera (opcjonalna)
        **kwargs: dodatkowe opcje konfiguracji (np. config_override, max_proceedings, etc.)

    Returns:
        Skonfigurowany scraper
    """
    logger.info("Tworzenie scrapera...")

    # Połącz config z kwargs
    final_config = config or {}

    # Obsługa config_override z main.py
    if config_override and isinstance(config_override, dict):
        final_config.update(config_override)

    # Dodaj pozostałe kwargs do konfiguracji
    final_config.update(kwargs)

    try:
        # Import głównego scrapera - UŻYWA TWOJEJ ŚCIEŻKI
        from ..scraping.scraper import SejmScraper

        scraper = SejmScraper(config=final_config)
        logger.info("Scraper utworzony pomyślnie")
        return scraper

    except ImportError as e:
        logger.error(f"Błąd importu scrapera: {e}")
        raise RuntimeError(f"Nie można zainicjalizować scrapera: {e}")


def get_version_info() -> Dict[str, str]:
    """Zwraca informacje o wersji"""
    return {
        'version': '3.1.0-fixed',
        'author': 'SejmBot Team',
        'description': 'Fixed Scraper for Polish Parliament transcripts',
        'focus': 'Content fetching from statements'
    }


def setup_logging(level: int = logging.INFO, log_file: Optional[str] = None) -> None:
    """
    Konfiguruje logowanie dla aplikacji

    Args:
        level: poziom logowania
        log_file: plik do logów (opcjonalny)
    """
    import sys
    from pathlib import Path

    handlers = [logging.StreamHandler(sys.stdout)]

    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        from logging.handlers import RotatingFileHandler
        file_handler = RotatingFileHandler(
            log_path, maxBytes=10 * 1024 * 1024, backupCount=3, encoding='utf-8'
        )
        handlers.append(file_handler)

    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=handlers
    )


def quick_health_check() -> Dict[str, Any]:
    """
    Szybkie sprawdzenie stanu komponentów

    Returns:
        Słownik ze stanem komponentów
    """
    health = {
        'healthy': True,
        'components': {}
    }

    # Test importów
    components_to_test = [
        ('api.client', 'SejmAPIInterface'),
        ('cache.manager', 'CacheInterface'),
        ('scraping.scraper', 'SejmScraper'),
        ('storage.file_manager', 'FileManagerInterface')
    ]

    for module_path, class_name in components_to_test:
        try:
            module_parts = module_path.split('.')
            module = __import__(f"..{module_path}", fromlist=[class_name], level=1)
            getattr(module, class_name)
            health['components'][module_path] = {'status': 'ok', 'importable': True}
        except ImportError as e:
            health['components'][module_path] = {'status': 'error', 'error': str(e)}
            health['healthy'] = False
        except AttributeError as e:
            health['components'][module_path] = {'status': 'error', 'error': f"Class {class_name} not found"}
            health['healthy'] = False

    return health


def get_settings() -> Dict[str, Any]:
    """
    Zwraca domyślne ustawienia aplikacji

    Returns:
        Słownik z ustawieniami
    """
    return {
        'api': {
            'base_url': 'https://api.sejm.gov.pl',
            'timeout': 30,
            'delay': 0.2,
            'user_agent': 'SejmBotScraper/3.1'
        },
        'cache': {
            'enabled': True,
            'memory_limit_mb': 100,
            'file_cache_enabled': True,
            'default_ttl': 3600
        },
        'scraping': {
            'default_term': 10,
            'fetch_content': True,
            'max_retries': 2,
            'rate_limit_delay': 0.1
        },
        'storage': {
            'base_directory': 'data',
            'create_backups': True,
            'compress_old_files': False
        }
    }
