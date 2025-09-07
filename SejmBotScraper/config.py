# config.py
"""
Konfiguracja dla SejmBotScraper v2.0
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


# === API CONFIGURATION ===
API_BASE_URL = os.getenv('API_BASE_URL', 'https://api.sejm.gov.pl')
DEFAULT_TERM = get_int_env('DEFAULT_TERM', 10)

# === DIRECTORIES ===
BASE_OUTPUT_DIR = os.getenv('BASE_OUTPUT_DIR', 'data_sejm')
LOGS_DIR = os.getenv('LOGS_DIR', 'logs')

# Struktura katalogów
DIRS_STRUCTURE = {
    'transcripts': 'stenogramy',  # Stenogramy i wypowiedzi
    'mps': 'poslowie',  # Dane posłów
    'clubs': 'kluby',  # Kluby parlamentarne
    'enriched': 'wzbogacone',  # Wzbogacone dane
    'final': 'gotowe_zbiory',  # Finalne JSON-y do analizy
    'photos': 'zdjecia_poslow',  # Zdjęcia posłów
    'temp': 'temp'  # Pliki tymczasowe
}

# === REQUEST SETTINGS ===
REQUEST_TIMEOUT = get_int_env('REQUEST_TIMEOUT', 30)
REQUEST_DELAY = get_float_env('REQUEST_DELAY', 1.0)  # sekundy między zapytaniami
MAX_RETRIES = get_int_env('MAX_RETRIES', 3)
RETRY_BASE_DELAY = get_float_env('RETRY_BASE_DELAY', 5.0)

# User Agent
USER_AGENT = os.getenv('USER_AGENT', 'SejmBotScraper/2.0 (Educational Purpose)')

# === TRANSCRIPT PROCESSING ===
TRANSCRIPT_CONFIG = {
    'fetch_full_text': get_bool_env('FETCH_FULL_TEXT', False),
    'skip_existing_statements': get_bool_env('SKIP_EXISTING_STATEMENTS', True),
    'statement_batch_size': get_int_env('STATEMENT_BATCH_SIZE', 100),
    'max_statement_length': get_int_env('MAX_STATEMENT_LENGTH', 50000),  # chars
    'save_raw_html': get_bool_env('SAVE_RAW_HTML', False),
}

# === MP DATA PROCESSING ===
MP_CONFIG = {
    'download_photos': get_bool_env('DOWNLOAD_MP_PHOTOS', True),
    'download_voting_stats': get_bool_env('DOWNLOAD_MP_VOTING_STATS', True),
    'photo_max_size_mb': get_int_env('MP_PHOTO_MAX_SIZE_MB', 5),
    'skip_existing_photos': get_bool_env('SKIP_EXISTING_PHOTOS', True),
}

# === ENRICHMENT SETTINGS ===
ENRICHMENT_CONFIG = {
    'enable_enrichment': get_bool_env('ENABLE_ENRICHMENT', True),
    'create_final_datasets': get_bool_env('CREATE_FINAL_DATASETS', True),
    'include_mp_photos_in_final': get_bool_env('INCLUDE_MP_PHOTOS_FINAL', False),
    'final_json_indent': get_int_env('FINAL_JSON_INDENT', 2),
    'compress_final_json': get_bool_env('COMPRESS_FINAL_JSON', False),
}

# === LOGGING ===
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO').upper()
LOG_FORMAT = os.getenv('LOG_FORMAT', '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
LOG_TO_FILE = get_bool_env('LOG_TO_FILE', True)
LOG_FILE_MAX_SIZE_MB = get_int_env('LOG_FILE_MAX_SIZE_MB', 50)
LOG_FILE_BACKUP_COUNT = get_int_env('LOG_FILE_BACKUP_COUNT', 5)

# === SCHEDULER (for automated runs) ===
SCHEDULER_CONFIG = {
    'check_interval_minutes': get_int_env('SCHEDULER_INTERVAL', 30),
    'max_proceeding_age_days': get_int_env('MAX_PROCEEDING_AGE', 7),
    'enable_health_server': get_bool_env('ENABLE_HEALTH_SERVER', False),
    'health_server_port': get_int_env('HEALTH_SERVER_PORT', 8080),
    'enable_notifications': get_bool_env('NOTIFICATION_ON_ERRORS', True),
    'notification_on_errors': get_bool_env('NOTIFICATION_ON_ERRORS', True),
    'notification_on_startup': get_bool_env('NOTIFICATION_ON_STARTUP', False),
    'notification_webhook': os.getenv('NOTIFICATION_WEBHOOK'),  # Dodany brakujący klucz
    'auto_enrich_new_data': get_bool_env('AUTO_ENRICH_NEW_DATA', True),
}

# === FILE FORMATS ===
FILE_FORMATS = {
    'statements_json': '.statements.json',
    'mp_data_json': '.mp_data.json',
    'club_data_json': '.club_data.json',
    'enriched_json': '.enriched.json',
    'final_dataset_json': '.dataset.json',
    'temp_suffix': '.tmp',
}

# === DATA VALIDATION ===
VALIDATION_CONFIG = {
    'validate_json_structure': get_bool_env('VALIDATE_JSON_STRUCTURE', True),
    'check_data_completeness': get_bool_env('CHECK_DATA_COMPLETENESS', True),
    'min_statements_per_proceeding': get_int_env('MIN_STATEMENTS_PER_PROCEEDING', 10),
    'max_errors_before_abort': get_int_env('MAX_ERRORS_BEFORE_ABORT', 50),
}

# === PERFORMANCE ===
PERFORMANCE_CONFIG = {
    'concurrent_downloads': get_int_env('CONCURRENT_DOWNLOADS', 3),
    'memory_limit_mb': get_int_env('MEMORY_LIMIT_MB', 1024),
    'cleanup_temp_files': get_bool_env('CLEANUP_TEMP_FILES', True),
    'compress_old_logs': get_bool_env('COMPRESS_OLD_LOGS', True),
}


def get_output_dir(subdir_key: str = None) -> Path:
    """
    Zwraca ścieżkę do katalogu wyjściowego

    Args:
        subdir_key: klucz z DIRS_STRUCTURE lub None dla głównego katalogu

    Returns:
        Path: ścieżka do katalogu
    """
    base = Path(BASE_OUTPUT_DIR)

    if subdir_key and subdir_key in DIRS_STRUCTURE:
        return base / DIRS_STRUCTURE[subdir_key]

    return base


def create_output_directories():
    """Tworzy wszystkie wymagane katalogi wyjściowe"""
    try:
        # Główny katalog
        base_dir = Path(BASE_OUTPUT_DIR)
        base_dir.mkdir(exist_ok=True)

        # Podkatalogi
        for subdir in DIRS_STRUCTURE.values():
            (base_dir / subdir).mkdir(exist_ok=True)

        # Katalog logów
        Path(LOGS_DIR).mkdir(exist_ok=True)

        return True

    except Exception as e:
        print(f"Błąd tworzenia katalogów: {e}")
        return False


def get_file_path(term: int, proceeding: int = None, file_type: str = 'statements_json',
                  subdir: str = 'transcripts') -> Path:
    """
    Generuje ścieżkę do pliku danych

    Args:
        term: numer kadencji
        proceeding: numer posiedzenia (opcjonalne)
        file_type: typ pliku z FILE_FORMATS
        subdir: podkatalog z DIRS_STRUCTURE

    Returns:
        Path: ścieżka do pliku
    """
    output_dir = get_output_dir(subdir)
    term_dir = output_dir / f"kadencja_{term:02d}"
    term_dir.mkdir(exist_ok=True)

    if proceeding:
        filename = f"posiedzenie_{proceeding:03d}{FILE_FORMATS.get(file_type, '.json')}"
    else:
        filename = f"kadencja_{term:02d}{FILE_FORMATS.get(file_type, '.json')}"

    return term_dir / filename


def validate_config():
    """Waliduje konfigurację i zwraca listę problemów"""
    issues = []

    # Sprawdź katalogi
    if not create_output_directories():
        issues.append("Nie można utworzyć katalogów wyjściowych")

    # Sprawdź konfigurację schedulera - poprawione klucze
    if SCHEDULER_CONFIG['enable_notifications'] and not SCHEDULER_CONFIG['notification_webhook']:
        issues.append("Powiadomienia włączone ale brak NOTIFICATION_WEBHOOK")

    if SCHEDULER_CONFIG['check_interval_minutes'] < 1:
        issues.append(f"SCHEDULER_INTERVAL zbyt mały: {SCHEDULER_CONFIG['check_interval_minutes']} (min: 1)")

    # Sprawdź limity
    if REQUEST_DELAY < 0.1:
        issues.append(f"REQUEST_DELAY zbyt mały: {REQUEST_DELAY} (min: 0.1)")

    if TRANSCRIPT_CONFIG['statement_batch_size'] < 1:
        issues.append(f"STATEMENT_BATCH_SIZE zbyt mały: {TRANSCRIPT_CONFIG['statement_batch_size']}")

    if PERFORMANCE_CONFIG['concurrent_downloads'] < 1:
        issues.append(f"CONCURRENT_DOWNLOADS zbyt mały: {PERFORMANCE_CONFIG['concurrent_downloads']}")

    # Sprawdź limity pamięci
    if PERFORMANCE_CONFIG['memory_limit_mb'] < 128:
        issues.append(f"MEMORY_LIMIT_MB zbyt mały: {PERFORMANCE_CONFIG['memory_limit_mb']} (min: 128)")

    return issues


def print_config_summary():
    """Wyświetla podsumowanie konfiguracji"""
    print("=" * 70)
    print("🔧 KONFIGURACJA SEJMBOT SCRAPER v2.0")
    print("=" * 70)
    print(f"API URL:           {API_BASE_URL}")
    print(f"Domyślna kadencja: {DEFAULT_TERM}")
    print(f"Katalog wyjścia:   {BASE_OUTPUT_DIR}")
    print(f"Katalog logów:     {LOGS_DIR}")
    print(f"Poziom logów:      {LOG_LEVEL}")
    print()

    print("📄 STENOGRAMY:")
    print(f"  Pełny tekst:       {'✅' if TRANSCRIPT_CONFIG['fetch_full_text'] else '❌'}")
    print(f"  Batch size:        {TRANSCRIPT_CONFIG['statement_batch_size']}")
    print(f"  Pomijaj istniejące: {'✅' if TRANSCRIPT_CONFIG['skip_existing_statements'] else '❌'}")
    print()

    print("👥 POSŁOWIE:")
    print(f"  Zdjęcia:           {'✅' if MP_CONFIG['download_photos'] else '❌'}")
    print(f"  Statystyki:        {'✅' if MP_CONFIG['download_voting_stats'] else '❌'}")
    print(f"  Max rozmiar zdjęć:  {MP_CONFIG['photo_max_size_mb']} MB")
    print()

    print("🔗 WZBOGACANIE:")
    print(f"  Włączone:          {'✅' if ENRICHMENT_CONFIG['enable_enrichment'] else '❌'}")
    print(f"  Finalne zbiory:    {'✅' if ENRICHMENT_CONFIG['create_final_datasets'] else '❌'}")
    print(f"  Kompresja JSON:    {'✅' if ENRICHMENT_CONFIG['compress_final_json'] else '❌'}")
    print()

    print("⚡ WYDAJNOŚĆ:")
    print(f"  Równoległe pobieranie: {PERFORMANCE_CONFIG['concurrent_downloads']}")
    print(f"  Limit pamięci:         {PERFORMANCE_CONFIG['memory_limit_mb']} MB")
    print(f"  Sprzątanie temp:       {'✅' if PERFORMANCE_CONFIG['cleanup_temp_files'] else '❌'}")
    print()

    print("📅 SCHEDULER:")
    print(f"  Interwał:          {SCHEDULER_CONFIG['check_interval_minutes']} min")
    print(f"  Wiek posiedzeń:    {SCHEDULER_CONFIG['max_proceeding_age_days']} dni")
    print(f"  Powiadomienia:     {'✅' if SCHEDULER_CONFIG['enable_notifications'] else '❌'}")
    print(f"  Auto-wzbogacanie:  {'✅' if SCHEDULER_CONFIG['auto_enrich_new_data'] else '❌'}")
    if SCHEDULER_CONFIG['enable_notifications']:
        webhook = SCHEDULER_CONFIG['notification_webhook']
        webhook_display = webhook[:50] + "..." if webhook and len(webhook) > 50 else webhook or "BRAK"
        print(f"  Webhook:           {webhook_display}")
    print(f"  Health server:     {'✅' if SCHEDULER_CONFIG['enable_health_server'] else '❌'}")
    if SCHEDULER_CONFIG['enable_health_server']:
        print(f"  Health port:       {SCHEDULER_CONFIG['health_server_port']}")
    print()

    print("🔗 ZAPYTANIA:")
    print(f"  Timeout:           {REQUEST_TIMEOUT}s")
    print(f"  Opóźnienie:        {REQUEST_DELAY}s")
    print(f"  Powtórzenia:       {MAX_RETRIES}")
    print("=" * 70)


def print_directories_structure():
    """Wyświetla strukturę katalogów"""
    print("📁 STRUKTURA KATALOGÓW:")
    print("-" * 40)
    base = Path(BASE_OUTPUT_DIR)
    print(f"📂 {base}")
    for key, subdir in DIRS_STRUCTURE.items():
        print(f"  📁 {subdir}/ ({key})")

        # Przykładowe pliki dla każdego typu
        if key == 'transcripts':
            print(f"     📄 kadencja_10/")
            print(f"        📄 posiedzenie_001.statements.json")
            print(f"        📄 posiedzenie_002.statements.json")
        elif key == 'mps':
            print(f"     👤 kadencja_10.mp_data.json")
            print(f"     📊 kadencja_10_statystyki.json")
        elif key == 'clubs':
            print(f"     🏛️  kadencja_10.club_data.json")
        elif key == 'enriched':
            print(f"     🔗 kadencja_10/")
            print(f"        📄 posiedzenie_001.enriched.json")
        elif key == 'final':
            print(f"     🎯 kadencja_10_kompletny_zbior.dataset.json")
            print(f"     📊 kadencja_10_statystyki.dataset.json")
        elif key == 'photos':
            print(f"     🖼️  kadencja_10/")
            print(f"        📸 posel_12345.jpg")


# Wykonaj walidację przy imporcie
_validation_issues = validate_config()
if _validation_issues:
    print("⚠️  PROBLEMY KONFIGURACJI:")
    for issue in _validation_issues:
        print(f"   • {issue}")
    print()
