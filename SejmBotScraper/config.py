# config.py
"""
Konfiguracja dla SejmBotScraper
"""

import os
from pathlib import Path


# Załaduj zmienne z .env jeśli plik istnieje
def load_env_file():
    """Ładuje zmienne środowiskowe z pliku .env"""
    env_file = Path('.env')
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
            print(f"Ostrzeżenie: nie można załadować .env: {e}")


# Załaduj .env przed konfiguracją
load_env_file()


def get_bool_env(key: str, default: bool = False) -> bool:
    """Pobiera zmienną środowiskową jako bool"""
    value = os.getenv(key, str(default)).lower()
    return value in ('true', '1', 'yes', 'on')


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


API_BASE_URL = os.getenv('API_BASE_URL', 'https://api.sejm.gov.pl')
DEFAULT_TERM = get_int_env('DEFAULT_TERM', 10)

BASE_OUTPUT_DIR = os.getenv('BASE_OUTPUT_DIR', 'stenogramy_sejm')
LOGS_DIR = os.getenv('LOGS_DIR', 'logs')

REQUEST_TIMEOUT = get_int_env('REQUEST_TIMEOUT', 30)
REQUEST_DELAY = get_float_env('REQUEST_DELAY', 1.0)  # sekundy między zapytaniami
MAX_RETRIES = get_int_env('MAX_RETRIES', 3)
RETRY_BASE_DELAY = get_float_env('RETRY_BASE_DELAY', 5.0)

TRANSCRIPT_FORMATS = {
    'pdf': '/pdf',
    'html': ''  # individual statements in HTML
}

LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO').upper()
LOG_FORMAT = os.getenv('LOG_FORMAT', '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
LOG_TO_FILE = get_bool_env('LOG_TO_FILE', True)
LOG_FILE_MAX_SIZE_MB = get_int_env('LOG_FILE_MAX_SIZE_MB', 50)
LOG_FILE_BACKUP_COUNT = get_int_env('LOG_FILE_BACKUP_COUNT', 5)

SCHEDULER_CONFIG = {
    'check_interval_minutes': get_int_env('SCHEDULER_INTERVAL', 30),
    'max_proceeding_age_days': get_int_env('MAX_PROCEEDING_AGE', 7),
    'notification_webhook': os.getenv('NOTIFICATION_WEBHOOK'),
    'enable_notifications': get_bool_env('ENABLE_NOTIFICATIONS', False),
    'notification_on_errors': get_bool_env('NOTIFICATION_ON_ERRORS', True),
    'notification_on_startup': get_bool_env('NOTIFICATION_ON_STARTUP', False),
}

# User Agent
USER_AGENT = os.getenv('USER_AGENT', 'SejmBotScraper/1.0 (Educational Purpose)')


def validate_config():
    """Waliduje konfigurację i wyświetla ostrzeżenia"""
    issues = []

    # Sprawdź wymagane katalogi
    for dir_name, dir_path in [('Output', BASE_OUTPUT_DIR), ('Logs', LOGS_DIR)]:
        try:
            os.makedirs(dir_path, exist_ok=True)
        except PermissionError:
            issues.append(f"Brak uprawnień do utworzenia katalogu {dir_name}: {dir_path}")
        except Exception as e:
            issues.append(f"Błąd tworzenia katalogu {dir_name}: {e}")

    # Sprawdź konfigurację schedulera
    if SCHEDULER_CONFIG['enable_notifications'] and not SCHEDULER_CONFIG['notification_webhook']:
        issues.append("Powiadomienia włączone ale brak NOTIFICATION_WEBHOOK")

    if SCHEDULER_CONFIG['check_interval_minutes'] < 1:
        issues.append(f"SCHEDULER_INTERVAL zbyt mały: {SCHEDULER_CONFIG['check_interval_minutes']} (min: 1)")

    if REQUEST_DELAY < 0.1:
        issues.append(f"REQUEST_DELAY zbyt mały: {REQUEST_DELAY} (min: 0.1)")

    return issues


def print_config_summary():
    """Wyświetla podsumowanie konfiguracji"""
    print("=" * 60)
    print("🔧 KONFIGURACJA SEJMBOT SCRAPER")
    print("=" * 60)
    print(f"API URL:           {API_BASE_URL}")
    print(f"Domyślna kadencja: {DEFAULT_TERM}")
    print(f"Katalog wyjścia:   {BASE_OUTPUT_DIR}")
    print(f"Katalog logów:     {LOGS_DIR}")
    print(f"Poziom logów:      {LOG_LEVEL}")
    print()
    print("📅 SCHEDULER:")
    print(f"  Interwał:        {SCHEDULER_CONFIG['check_interval_minutes']} min")
    print(f"  Wiek posiedzeń:  {SCHEDULER_CONFIG['max_proceeding_age_days']} dni")
    print(f"  Powiadomienia:   {'✅' if SCHEDULER_CONFIG['enable_notifications'] else '❌'}")
    if SCHEDULER_CONFIG['enable_notifications']:
        webhook = SCHEDULER_CONFIG['notification_webhook']
        webhook_display = webhook[:50] + "..." if webhook and len(webhook) > 50 else webhook or "BRAK"
        print(f"  Webhook:         {webhook_display}")
    print(f"  Health server:   {'✅' if SCHEDULER_CONFIG['enable_health_server'] else '❌'}")
    if SCHEDULER_CONFIG['enable_health_server']:
        print(f"  Health port:     {SCHEDULER_CONFIG['health_server_port']}")
    print()
    print("🔗 ZAPYTANIA:")
    print(f"  Timeout:         {REQUEST_TIMEOUT}s")
    print(f"  Opóźnienie:      {REQUEST_DELAY}s")
    print(f"  Powtórzenia:     {MAX_RETRIES}")
    print("=" * 60)


# Wykonaj walidację przy imporcie
_validation_issues = validate_config()
if _validation_issues:
    print("⚠️  PROBLEMY KONFIGURACJI:")
    for issue in _validation_issues:
        print(f"   • {issue}")
    print()

# Zmienne dla backwards compatibility
create_directories = lambda: None  # funkcja już wykonana w validate_config
