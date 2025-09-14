# config/__init__.py
"""
Moduł konfiguracji - eksport głównych wartości
"""

# Eksportuj wartości domyślne dla backward compatibility
DEFAULT_TERM = 10
API_BASE_URL = 'https://api.sejm.gov.pl'
BASE_OUTPUT_DIR = 'data_sejm'
LOGS_DIR = 'logs'

# Dodaj brakujące wartości z oryginalnego config.py
REQUEST_TIMEOUT = 30
REQUEST_DELAY = 1.0
MAX_RETRIES = 3
RETRY_BASE_DELAY = 5.0
USER_AGENT = 'SejmBotScraper/3.0 (Educational Purpose)'

# Struktura katalogów
DIRS_STRUCTURE = {
    'transcripts': 'stenogramy',
    'mps': 'poslowie',
    'clubs': 'kluby',
    'enriched': 'wzbogacone',
    'final': 'gotowe_zbiory',
    'photos': 'zdjecia_poslow',
    'temp': 'temp'
}

# Konfiguracje domyślne
TRANSCRIPT_CONFIG = {
    'fetch_full_text': False,
    'skip_existing_statements': True,
    'statement_batch_size': 100,
    'max_statement_length': 50000,
    'save_raw_html': False,
}

MP_CONFIG = {
    'download_photos': True,
    'download_voting_stats': True,
    'photo_max_size_mb': 5,
    'skip_existing_photos': True,
}

ENRICHMENT_CONFIG = {
    'enable_enrichment': True,
    'create_final_datasets': True,
    'include_mp_photos_in_final': False,
    'final_json_indent': 2,
    'compress_final_json': False,
}

LOG_LEVEL = 'INFO'
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
LOG_TO_FILE = True
LOG_FILE_MAX_SIZE_MB = 50
LOG_FILE_BACKUP_COUNT = 5

SCHEDULER_CONFIG = {
    'check_interval_minutes': 30,
    'max_proceeding_age_days': 7,
    'enable_health_server': False,
    'health_server_port': 8080,
    'enable_notifications': True,
    'notification_on_errors': True,
    'notification_on_startup': False,
    'notification_webhook': None,
    'auto_enrich_new_data': True,
}

FILE_FORMATS = {
    'statements_json': '.statements.json',
    'mp_data_json': '.mp_data.json',
    'club_data_json': '.club_data.json',
    'enriched_json': '.enriched.json',
    'final_dataset_json': '.dataset.json',
    'temp_suffix': '.tmp',
}

VALIDATION_CONFIG = {
    'validate_json_structure': True,
    'check_data_completeness': True,
    'min_statements_per_proceeding': 10,
    'max_errors_before_abort': 50,
}

PERFORMANCE_CONFIG = {
    'concurrent_downloads': 3,
    'memory_limit_mb': 1024,
    'cleanup_temp_files': True,
    'compress_old_logs': True,
}

# Główne funkcje konfiguracji
try:
    from .settings import get_settings, setup_logging, validate_environment, Settings, get_output_dir

    __all__ = [
        # Backward compatibility values
        'DEFAULT_TERM', 'API_BASE_URL', 'BASE_OUTPUT_DIR', 'LOGS_DIR',
        'REQUEST_TIMEOUT', 'REQUEST_DELAY', 'MAX_RETRIES', 'RETRY_BASE_DELAY', 'USER_AGENT',
        'DIRS_STRUCTURE', 'TRANSCRIPT_CONFIG', 'MP_CONFIG', 'ENRICHMENT_CONFIG',
        'LOG_LEVEL', 'LOG_FORMAT', 'LOG_TO_FILE', 'LOG_FILE_MAX_SIZE_MB', 'LOG_FILE_BACKUP_COUNT',
        'SCHEDULER_CONFIG', 'FILE_FORMATS', 'VALIDATION_CONFIG', 'PERFORMANCE_CONFIG',

        # New settings system
        'get_settings', 'setup_logging', 'validate_environment', 'Settings', 'get_output_dir'
    ]
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


    def get_output_dir(subdir_key=None):
        from pathlib import Path
        base = Path(BASE_OUTPUT_DIR)
        if subdir_key and subdir_key in DIRS_STRUCTURE:
            return base / DIRS_STRUCTURE[subdir_key]
        return base


    class Settings:
        pass


    __all__ = [
        # Backward compatibility values
        'DEFAULT_TERM', 'API_BASE_URL', 'BASE_OUTPUT_DIR', 'LOGS_DIR',
        'REQUEST_TIMEOUT', 'REQUEST_DELAY', 'MAX_RETRIES', 'RETRY_BASE_DELAY', 'USER_AGENT',
        'DIRS_STRUCTURE', 'TRANSCRIPT_CONFIG', 'MP_CONFIG', 'ENRICHMENT_CONFIG',
        'LOG_LEVEL', 'LOG_FORMAT', 'LOG_TO_FILE', 'LOG_FILE_MAX_SIZE_MB', 'LOG_FILE_BACKUP_COUNT',
        'SCHEDULER_CONFIG', 'FILE_FORMATS', 'VALIDATION_CONFIG', 'PERFORMANCE_CONFIG',

        # New settings system
        'get_settings', 'setup_logging', 'validate_environment', 'Settings', 'get_output_dir'
    ]
