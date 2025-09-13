#!/usr/bin/env python3
# scheduler_main.py
"""
SejmBot Scheduler v3.0 - Entry point dla automatycznego schedulera
Zintegrowany z nową modularną architekturą
"""

import sys
from pathlib import Path

# Dodaj główny katalog do PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent))

import argparse
import logging

from sejmbot_scraper import get_settings, setup_logging, get_version_info
from scheduler.scheduler import SejmScheduler

logger = logging.getLogger(__name__)


def print_banner():
    """Wyświetla banner aplikacji"""
    version_info = get_version_info()
    banner = f"""
╔══════════════════════════════════════════════════════════════════╗
║                    SejmBot Scheduler v{version_info['version']}                        ║
║                                                                  ║
║            Automatyczne pobieranie nowych transkryptów          ║
║                                                                  ║
╚══════════════════════════════════════════════════════════════════╝
    """
    print(banner)


def create_cli_parser():
    """Tworzy parser argumentów CLI dla schedulera"""
    parser = argparse.ArgumentParser(
        description="SejmBot Scheduler v3.0 - automatyczne pobieranie nowych transkryptów",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Przykłady użycia:
  %(prog)s --once                       # jednorazowe sprawdzenie
  %(prog)s --continuous                 # ciągły tryb (domyślnie z konfiguracji)
  %(prog)s --continuous --interval 15   # ciągły tryb co 15 min
  %(prog)s --status                     # pokaż status schedulera
  %(prog)s --cleanup                    # wyczyść stary stan
  %(prog)s --clear-cache                # wyczyść cache
  %(prog)s --cache-stats                # pokaż statystyki cache
  %(prog)s --health                     # sprawdź stan zdrowia schedulera

Konfiguracja:
  %(prog)s --config .env.production     # użyj konkretnego pliku konfiguracji
        """
    )

    parser.add_argument(
        '-t', '--term',
        type=int,
        help='Numer kadencji (domyślnie z konfiguracji)'
    )

    parser.add_argument(
        '--once',
        action='store_true',
        help='Wykonaj jednorazowe sprawdzenie i zakończ'
    )

    parser.add_argument(
        '--continuous',
        action='store_true',
        help='Uruchom w trybie ciągłym'
    )

    parser.add_argument(
        '--interval',
        type=int,
        help='Interwał sprawdzania w minutach (tylko dla --continuous)'
    )

    parser.add_argument(
        '--status',
        action='store_true',
        help='Wyświetl status schedulera i zakończ'
    )

    parser.add_argument(
        '--health',
        action='store_true',
        help='Sprawdź stan zdrowia schedulera'
    )

    parser.add_argument(
        '--cleanup',
        action='store_true',
        help='Wyczyść stary stan (starszy niż 30 dni)'
    )

    parser.add_argument(
        '--clear-cache',
        action='store_true',
        help='Wyczyść cache API i plików'
    )

    parser.add_argument(
        '--cache-stats',
        action='store_true',
        help='Wyświetl statystyki cache'
    )

    parser.add_argument(
        '--config',
        type=str,
        help='Ścieżka do pliku konfiguracji (.env)'
    )

    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Szczegółowe logi (DEBUG level)'
    )

    parser.add_argument(
        '--log-file',
        type=str,
        help='Zapisuj logi do pliku'
    )

    parser.add_argument(
        '--version',
        action='store_true',
        help='Pokaż informacje o wersji'
    )

    return parser


def print_status(scheduler: SejmScheduler):
    """Wyświetla status schedulera"""
    status = scheduler.get_status()

    print(f"\nSTATUS SCHEDULERA KADENCJI {status['term']}")
    print("=" * 50)
    print(f"Ostatnie sprawdzenie: {status['last_check'] or 'Nigdy'}")
    print(f"Przetworzone posiedzenia: {status['processed_proceedings']}")
    print(f"Łączna liczba przetworzonych dat: {status['total_processed_dates']}")
    print(f"Plik stanu: {status['state_file']} {'✅' if status['state_file_exists'] else '❌'}")
    print(f"Migracja do cache: {'✅' if status.get('migrated_to_cache') else '❌'}")

    if status.get('migration_date'):
        print(f"Data migracji: {status['migration_date']}")

    # Konfiguracja
    config = status.get('config', {})
    print(f"\nKonfiguracja:")
    print(f"  Interwał sprawdzania: {config.get('check_interval_minutes', '?')} min")
    print(f"  Maksymalny wiek posiedzeń: {config.get('max_proceeding_age_days', '?')} dni")
    print(f"  Powiadomienia: {'włączone' if config.get('notifications_enabled') else 'wyłączone'}")

    # Cache stats
    cache_stats = status.get('cache_stats', {})
    if cache_stats:
        print(f"\nCache:")
        print(f"  Memory: {cache_stats.get('memory_entries', 0)} wpisów")
        print(f"  File: {cache_stats.get('file_entries', 0)} wpisów")


def print_health(scheduler: SejmScheduler):
    """Wyświetla status zdrowia schedulera"""
    health = scheduler.get_health_status()

    print(f"\nSTAN ZDROWIA SCHEDULERA KADENCJI {health['term']}")
    print("=" * 50)

    status = health['status']
    status_icon = "✅" if status == "healthy" else "⚠️" if status == "stale" else "❌"
    print(f"Status: {status_icon} {status.upper()}")

    print(f"Ostatnie sprawdzenie: {health['last_check'] or 'Nigdy'}")
    if health.get('hours_since_check'):
        print(f"Czas od sprawdzenia: {health['hours_since_check']:.1f}h")

    print(f"Przetworzone posiedzenia: {health['processed_proceedings']}")
    print(f"Przetworzone daty: {health['total_processed_dates']}")

    # Cache health
    cache_health = health.get('cache_health', {})
    print(f"\nCache:")
    print(f"  Memory entries: {cache_health.get('memory_entries', 0)}")
    print(f"  File entries: {cache_health.get('file_entries', 0)}")
    print(f"  Memory hits: {cache_health.get('memory_hits', 0)}")
    print(f"  Memory misses: {cache_health.get('memory_misses', 0)}")


def print_cache_stats(scheduler: SejmScheduler):
    """Wyświetla statystyki cache"""
    stats = scheduler.cache.get_stats()

    print(f"\nSTATYSTYKI CACHE")
    print("=" * 50)

    print(f"Memory Cache:")
    print(f"  Wpisy: {stats.get('memory_entries', 0)}")
    print(f"  Hits: {stats.get('memory_hits', 0)}")
    print(f"  Misses: {stats.get('memory_misses', 0)}")

    print(f"\nFile Cache:")
    print(f"  Wpisy: {stats.get('file_entries', 0)}")
    print(f"  File hits: {stats.get('file_hits', 0)}")
    print(f"  File misses: {stats.get('file_misses', 0)}")

    print(f"\nRozmiar łączny: {stats.get('total_size_mb', 0):.2f} MB")
    if stats.get('last_cleanup'):
        print(f"Ostatnie czyszczenie: {stats['last_cleanup']}")


def main():
    """Główna funkcja programu"""
    parser = create_cli_parser()
    args = vars(parser.parse_args())

    # Sprawdź czy podano jakąś akcję
    actions = ['once', 'continuous', 'status', 'health', 'cleanup', 'clear_cache', 'cache_stats', 'version']
    if not any(args.get(action) for action in actions):
        print("Błąd: Musisz podać jedną z akcji.")
        parser.print_help()
        return 1

    try:
        # Obsłuż wersję od razu
        if args.get('version'):
            info = get_version_info()
            print(f"\nSejmBotScheduler v{info['version']}")
            print(f"Autor: {info['author']}")
            print(f"Opis: {info['description']}")
            return 0

        # Załaduj konfigurację
        settings = get_settings(args.get('config'))

        # Konfiguruj logowanie
        if args.get('log_file'):
            import logging
            from logging.handlers import RotatingFileHandler

            log_file = Path(settings.get('logging.log_dir')) / args['log_file']
            log_file.parent.mkdir(parents=True, exist_ok=True)

            level = logging.DEBUG if args.get('verbose') else logging.INFO

            logging.basicConfig(
                level=level,
                format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                handlers=[
                    logging.StreamHandler(sys.stdout),
                    RotatingFileHandler(log_file, maxBytes=10 * 1024 * 1024, backupCount=3, encoding='utf-8')
                ]
            )

            print(f"Logi będą zapisywane do: {log_file}")
        else:
            setup_logging(settings)
            if args.get('verbose'):
                logging.getLogger().setLevel(logging.DEBUG)

        # Pobierz term
        term = args.get('term') or settings.get('default_term')

        # Utwórz scheduler
        scheduler = SejmScheduler(term, args.get('config'))

        # Wyświetl banner dla głównych operacji
        if args.get('continuous') or args.get('once'):
            print_banner()

        # Operacje cache
        if args.get('clear_cache'):
            print("Czyszczenie cache...")
            scheduler.clear_cache()
            print("Cache wyczyszczony")
            return 0

        if args.get('cache_stats'):
            print_cache_stats(scheduler)
            return 0

        # Operacje stanu
        if args.get('status'):
            print_status(scheduler)
            return 0

        if args.get('health'):
            print_health(scheduler)
            health = scheduler.get_health_status()
            return 0 if health['status'] == 'healthy' else 1

        if args.get('cleanup'):
            print("Czyszczenie starego stanu...")
            scheduler.cleanup_old_state()
            print("Zakończono czyszczenie")
            return 0

        # Główne operacje
        if args.get('once'):
            print("Uruchamiam jednorazowe sprawdzenie...")
            scheduler.run_once()
            print("Sprawdzenie zakończone")
            return 0

        if args.get('continuous'):
            interval = args.get('interval')
            if interval and interval < 1:
                print("Błąd: Interwał musi być co najmniej 1 minuta")
                return 1

            if interval:
                print(f"Uruchamiam scheduler w trybie ciągłym (co {interval} min)...")
            else:
                interval = scheduler._get_check_interval()
                print(f"Uruchamiam scheduler w trybie ciągłym (co {interval} min)...")

            print("Naciśnij Ctrl+C aby zatrzymać")
            scheduler.run_continuous(interval)
            return 0

    except KeyboardInterrupt:
        print("\nScheduler zatrzymany przez użytkownika")
        return 0

    except Exception as e:
        logger.error(f"Nieoczekiwany błąd: {e}")
        print(f"\nNieoczekiwany błąd: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
