# config/__init__.py
"""
Moduł konfiguracji - eksport głównych wartości
"""

# Eksportuj wartości domyślne dla backward compatibility
DEFAULT_TERM = 10
API_BASE_URL = 'https://api.sejm.gov.pl'
BASE_OUTPUT_DIR = 'data_sejm'
LOGS_DIR = 'logs'

# Główne funkcje konfiguracji
try:
    from .settings import get_settings, setup_logging, validate_environment, Settings

    __all__ = ['DEFAULT_TERM', 'API_BASE_URL', 'BASE_OUTPUT_DIR', 'LOGS_DIR',
               'get_settings', 'setup_logging', 'validate_environment', 'Settings']
except ImportError:
    # Fallback jeśli settings.py ma problemy
    def get_settings(env_file=None):
        return type('Settings', (), {
            'get': lambda self, key, default=None: {
                'default_term': DEFAULT_TERM,
                'api.base_url': API_BASE_URL,
                'scraping.base_output_dir': BASE_OUTPUT_DIR,
                'logging.log_dir': LOGS_DIR
            }.get(key, default)
        })()


    def setup_logging(settings):
        import logging
        logging.basicConfig(level=logging.INFO)


    def validate_environment():
        return []


    class Settings:
        pass


    __all__ = ['DEFAULT_TERM', 'API_BASE_URL', 'BASE_OUTPUT_DIR', 'LOGS_DIR',
               'get_settings', 'setup_logging', 'validate_environment', 'Settings']
