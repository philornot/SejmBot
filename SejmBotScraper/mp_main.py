#!/usr/bin/env python3
# mp_main.py
"""
SejmBot MP Scraper v3.0 - Entry point dla scrapowania posłów
Zintegrowany z nową modularną architekturą
"""

import sys
from pathlib import Path

# Dodaj główny katalog do PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent))

import argparse
import logging
from typing import Dict, Any

from sejmbot_scraper import (
    # Główne komponenty
    SejmScraper, get_settings, setup_logging,
    get_version_info, validate_installation,

    # Typy
    MPScrapingStats,

    # Wyjątki
    SejmScraperError, ConfigValidationError
)

logger = logging.getLogger(__name__)


def print_banner():
    """Wyświetla banner aplikacji"""
    version_info = get_version_info()
    banner = f"""
╔══════════════════════════════════════════════════════════════════╗
║                    SejmBot MP Scraper v{version_info['version']}                        ║
║                                                                  ║
║            Narzędzie do pobierania danych posłów                 ║
║                                                                  ║
╚══════════════════════════════════════════════════════════════════╝
    """
    print(banner)


def create_cli_parser():
    """Tworzy parser argumentów CLI"""
    parser = argparse.ArgumentParser(
        description="SejmBot MP Scraper v3.0 - pobiera dane posłów z API Sejmu RP",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Przykłady użycia:
  %(prog)s                              # pobierz wszystkich posłów z domyślnej kadencji
  %(prog)s -t 9                         # pobierz posłów z 9. kadencji
  %(prog)s --mp-id 123                  # pobierz konkretnego posła
  %(prog)s --clubs-only                 # pobierz tylko kluby parlamentarne
  %(prog)s --summary                    # wyświetl podsumowanie bez pobierania
  %(prog)s --no-photos --no-stats       # pomiń zdjęcia i statystyki głosowań
  %(prog)s --complete                   # pobierz wszystko: posłów, kluby, zdjęcia i statystyki
  %(prog)s -v --log-file mp_scraper.log # verbose z zapisem do pliku

Diagnostyka:
  %(prog)s --health-check               # sprawdź stan aplikacji
  %(prog)s --version                    # pokaż wersję

Konfiguracja:
  %(prog)s --config .env.production     # użyj konkretnego pliku konfiguracji
        """
    )

    # Główne opcje
    parser.add_argument(
        '-t', '--term',
        type=int,
        help='Numer kadencji (domyślnie z konfiguracji)'
    )

    parser.add_argument(
        '--mp-id',
        type=int,
        help='ID konkretnego posła do pobrania'
    )

    # Opcje pobierania
    parser.add_argument(
        '--clubs-only',
        action='store_true',
        help='Pobierz tylko kluby parlamentarne (bez posłów)'
    )

    parser.add_argument(
        '--no-photos',
        action='store_true',
        help='Nie pobieraj zdjęć posłów'
    )

    parser.add_argument(
        '--no-stats',
        action='store_true',
        help='Nie pobieraj statystyk głosowań'
    )

    parser.add_argument(
        '--complete',
        action='store_true',
        help='Pobierz wszystko: posłów, kluby, zdjęcia i statystyki'
    )

    # Opcje informacyjne
    parser.add_argument(
        '--summary',
        action='store_true',
        help='Wyświetl podsumowanie posłów bez pobierania danych'
    )

    # Opcje diagnostyczne
    parser.add_argument(
        '--health-check',
        action='store_true',
        help='Sprawdź stan aplikacji'
    )

    parser.add_argument(
        '--version',
        action='store_true',
        help='Pokaż informacje o wersji'
    )

    # Opcje konfiguracji
    parser.add_argument(
        '--config',
        type=str,
        help='Ścieżka do pliku konfiguracji (.env)'
    )

    # Opcje logowania
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Szczegółowe logi (DEBUG level)'
    )

    parser.add_argument(
        '--log-file',
        type=str,
        help='Zapisuj logi do pliku (w katalogu logs/)'
    )

    return parser


def get_mps_summary(scraper, term: int) -> Dict:
    """Pobiera podsumowanie posłów dla kadencji"""
    try:
        # Użyj API do pobrania podstawowych informacji
        mps = scraper.api.get_mps(term) if hasattr(scraper, 'api') else None

        if not mps:
            return None

        clubs = {}
        for mp in mps:
            club = mp.get('club', 'Brak klubu')
            if club not in clubs:
                clubs[club] = 0
            clubs[club] += 1

        return {
            'term': term,
            'total_mps': len(mps),
            'clubs': clubs,
            'clubs_count': len(clubs)
        }

    except Exception as e:
        logger.error(f"Błąd pobierania podsumowania posłów: {e}")
        return None


def handle_diagnostic_operations(args: Dict[str, Any]) -> int:
    """Obsługuje operacje diagnostyczne"""
    if args.get('health_check'):
        from sejmbot_scraper import quick_health_check

        print("Sprawdzanie stanu aplikacji...")
        health = quick_health_check()

        print("\nSTAN APLIKACJI")
        print("=" * 40)
        print(f"Status: {'ZDROWA' if health.get('healthy') else 'PROBLEMY'}")

        components = health.get('components', {})
        for name, status in components.items():
            status_text = 'OK' if status.get('healthy') else 'BŁĄD'
            print(f"{name}: {status_text}")
            if not status.get('healthy') and 'error' in status:
                print(f"  -> {status['error']}")

        return 0 if health.get('healthy') else 1

    if args.get('version'):
        info = get_version_info()
        print(f"\nSejmBotScraper v{info['version']}")
        print(f"Autor: {info['author']}")
        print(f"Opis: {info['description']}")
        print(f"Python: {info['python_version']}")
        print(f"Platforma: {info['platform']}")
        return 0

    return 1  # Nie obsłużono


def main():
    """Główna funkcja programu"""
    parser = create_cli_parser()
    args = vars(parser.parse_args())

    try:
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

        # Obsłuż operacje diagnostyczne
        if any(args.get(op) for op in ['version', 'health_check']):
            return handle_diagnostic_operations(args)

        # Wyświetl banner dla głównych operacji
        if not args.get('summary'):
            print_banner()

        # Pobierz term z konfiguracji jeśli nie podano
        term = args.get('term') or settings.get('default_term')

        # Utwórz scraper
        scraper = SejmScraper()

        # Podsumowanie posłów
        if args.get('summary'):
            summary = get_mps_summary(scraper, term)
            if summary:
                print(f"Podsumowanie posłów kadencji {summary['term']}:")
                print("-" * 60)
                print(f"Łączna liczba posłów: {summary['total_mps']}")
                print(f"Liczba klubów: {summary['clubs_count']}")
                print("\nPosłowie według klubów:")

                for club, count in sorted(summary['clubs'].items(),
                                          key=lambda x: x[1], reverse=True):
                    print(f"  {club}: {count} posłów")
            else:
                print(f"Nie można pobrać informacji o posłach kadencji {term}.")
            return 0

        # Walidacja parametrów
        if args.get('mp_id') is not None and args['mp_id'] <= 0:
            print(f"Błąd: ID posła musi być większe niż 0 (podano: {args['mp_id']})")
            return 1

        logger.info("Rozpoczynanie procesu pobierania danych posłów...")

        # Konkretny poseł
        if args.get('mp_id'):
            download_photos = not args.get('no_photos', False)
            download_stats = not args.get('no_stats', False)

            success = scraper.scrape_specific_mp(
                term,
                args['mp_id'],
                download_photos=download_photos,
                download_voting_stats=download_stats
            )

            if success:
                print(f"\nPomyślnie pobrano dane posła ID {args['mp_id']} z kadencji {term}")
                return 0
            else:
                print(f"\nBłąd podczas pobierania posła ID {args['mp_id']}")
                return 1

        # Tylko kluby
        elif args.get('clubs_only'):
            print("Pobieranie klubów parlamentarnych...")
            stats = scraper.scrape_clubs(term)

            print(f"\nPODSUMOWANIE POBIERANIA KLUBÓW")
            print("=" * 50)
            print(f"Pobrane kluby: {stats.get('clubs_downloaded', 0)}")
            print(f"Błędy: {stats.get('errors', 0)}")
            print("=" * 50)

            if stats.get('errors', 0) > 0:
                print(f"Proces zakończony z {stats['errors']} błędami. Sprawdź logi.")
                return 1
            else:
                print("Pobieranie klubów zakończone pomyślnie!")
                return 0

        # Pełne pobieranie lub standardowe
        else:
            download_photos = not args.get('no_photos', False)
            download_stats = not args.get('no_stats', False)

            if args.get('complete'):
                print("Pełne pobieranie: posłowie + kluby + zdjęcia + statystyki...")

                # Najpierw kluby
                clubs_stats = scraper.scrape_clubs(term)

                # Następnie posłowie
                mps_stats = scraper.scrape_mps(
                    term,
                    download_photos=download_photos,
                    download_voting_stats=download_stats
                )

                # Połącz statystyki
                stats = {
                    'mps_downloaded': mps_stats.get('mps_downloaded', 0),
                    'clubs_downloaded': clubs_stats.get('clubs_downloaded', 0),
                    'photos_downloaded': mps_stats.get('photos_downloaded', 0),
                    'voting_stats_downloaded': mps_stats.get('voting_stats_downloaded', 0),
                    'errors': mps_stats.get('errors', 0) + clubs_stats.get('errors', 0)
                }
            else:
                print("Pobieranie danych posłów...")
                stats = scraper.scrape_mps(
                    term,
                    download_photos=download_photos,
                    download_voting_stats=download_stats
                )

            print(f"\nPODSUMOWANIE POBIERANIA KADENCJI {term}")
            print("=" * 60)
            print(f"Pobrani posłowie:       {stats.get('mps_downloaded', 0)}")
            print(f"Pobrane kluby:          {stats.get('clubs_downloaded', 0)}")
            print(f"Pobrane zdjęcia:        {stats.get('photos_downloaded', 0)}")
            print(f"Pobrane statystyki:     {stats.get('voting_stats_downloaded', 0)}")
            print(f"Błędy:                  {stats.get('errors', 0)}")
            print("=" * 60)

            if stats.get('errors', 0) > 0:
                print(f"Proces zakończony z {stats['errors']} błędami. Sprawdź logi.")
                return 1
            else:
                print("Proces zakończony pomyślnie!")
                return 0

    except ConfigValidationError as e:
        print(f"\nBłąd konfiguracji: {e}")
        return 1

    except SejmScraperError as e:
        print(f"\nBłąd scrapera: {e}")
        return 1

    except KeyboardInterrupt:
        logger.info("Proces przerwany przez użytkownika (Ctrl+C)")
        print("\n\nProces przerwany przez użytkownika.")
        return 1

    except Exception as e:
        logger.error(f"Nieoczekiwany błąd: {e}")
        print(f"\nNieoczekiwany błąd: {e}")
        print("Sprawdź logi dla szczegółów.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
