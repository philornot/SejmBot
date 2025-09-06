#!/usr/bin/env python3
# mp_main.py
"""
SejmBot MP Scraper - Główny plik do pobierania danych posłów

Narzędzie do pobierania informacji o posłach, klubach i statystykach
z API Sejmu Rzeczypospolitej Polskiej.
"""

import argparse
import logging
import sys
from pathlib import Path

from config import LOG_LEVEL, LOG_FORMAT, LOGS_DIR, DEFAULT_TERM
from mp_scraper import MPScraper


def setup_logging(verbose: bool = False, log_file: str = None):
    """
    Konfiguruje system logowania

    Args:
        verbose: czy wyświetlać szczegółowe logi
        log_file: ścieżka do pliku z logami (opcjonalne)
    """
    level = logging.DEBUG if verbose else getattr(logging, LOG_LEVEL.upper())

    # Usuń istniejące handlery żeby uniknąć duplikatów
    root_logger = logging.getLogger()
    root_logger.handlers.clear()

    # Konfiguracja podstawowa - handler konsoli
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_formatter = logging.Formatter(LOG_FORMAT)
    console_handler.setFormatter(console_formatter)

    # Lista handlerów
    handlers = [console_handler]

    # Dodaj handler pliku jeśli podano
    if log_file:
        # Upewnij się, że katalog logs istnieje
        logs_path = Path(LOGS_DIR)
        logs_path.mkdir(exist_ok=True)

        log_file_path = logs_path / log_file

        try:
            file_handler = logging.FileHandler(log_file_path, encoding='utf-8')
            file_handler.setLevel(level)
            file_formatter = logging.Formatter(LOG_FORMAT)
            file_handler.setFormatter(file_formatter)
            handlers.append(file_handler)

            print(f"Logi będą zapisywane do: {log_file_path.absolute()}")

        except Exception as e:
            print(f"Ostrzeżenie: Nie można utworzyć pliku logów {log_file_path}: {e}")
            print("Kontynuuję tylko z logowaniem do konsoli.")

    # Konfiguruj logger podstawowy z handlerami
    root_logger.setLevel(level)
    for handler in handlers:
        root_logger.addHandler(handler)


def print_banner():
    """Wyświetla banner aplikacji"""
    banner = """
╔══════════════════════════════════════════════════════════════╗
║                    SejmBot MP Scraper                        ║
║                                                              ║
║            Narzędzie do pobierania danych posłów             ║
║                      Wersja 1.0.0                            ║
╚══════════════════════════════════════════════════════════════╝
    """
    print(banner)


def main():
    """Główna funkcja programu"""
    parser = argparse.ArgumentParser(
        description="SejmBot MP Scraper - pobiera dane posłów z API Sejmu RP",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Przykłady użycia:
  %(prog)s                              # pobierz wszystkich posłów z 10. kadencji
  %(prog)s -t 9                         # pobierz posłów z 9. kadencji
  %(prog)s --mp-id 123                  # pobierz konkretnego posła
  %(prog)s --clubs-only                 # pobierz tylko kluby parlamentarne
  %(prog)s --summary                    # wyświetl podsumowanie bez pobierania
  %(prog)s --no-photos --no-stats       # pomiń zdjęcia i statystyki głosowań
  %(prog)s -v --log-file mp_scraper.log # verbose z zapisem do pliku
        """
    )

    # Główne opcje
    parser.add_argument(
        '-t', '--term',
        type=int,
        default=DEFAULT_TERM,
        help=f'Numer kadencji (domyślnie: {DEFAULT_TERM})'
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

    args = parser.parse_args()

    # Konfiguruj logowanie przed jakąkolwiek operacją
    setup_logging(args.verbose, args.log_file)

    # Wyświetl banner
    if not args.summary:
        print_banner()

    # Utwórz scraper
    scraper = MPScraper()

    try:
        # Podsumowanie posłów
        if args.summary:
            summary = scraper.get_mps_summary(args.term)
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
                print(f"Nie można pobrać informacji o posłach kadencji {args.term}.")
            return

        # Walidacja parametrów
        if args.mp_id is not None and args.mp_id <= 0:
            print(f"Błąd: ID posła musi być większe niż 0 (podano: {args.mp_id})")
            sys.exit(1)

        logging.info("Rozpoczynanie procesu pobierania danych posłów...")

        # Konkretny poseł
        if args.mp_id:
            download_photos = not args.no_photos
            download_stats = not args.no_stats

            success = scraper.scrape_specific_mp(
                args.term,
                args.mp_id,
                download_photos,
                download_stats
            )

            if success:
                print(f"\n✅ Pomyślnie pobrano dane posła ID {args.mp_id} z kadencji {args.term}")
            else:
                print(f"\n❌ Błąd podczas pobierania posła ID {args.mp_id}")
                sys.exit(1)

        # Tylko kluby
        elif args.clubs_only:
            print("🏛️  Pobieranie klubów parlamentarnych...")
            stats = scraper.scrape_clubs(args.term)

            print(f"\n📊 PODSUMOWANIE POBIERANIA KLUBÓW")
            print("=" * 50)
            print(f"Pobrane kluby: {stats['clubs_downloaded']}")
            print(f"Błędy: {stats['errors']}")
            print("=" * 50)

            if stats['errors'] > 0:
                print(f"⚠️  Proces zakończony z {stats['errors']} błędami. Sprawdź logi.")
                sys.exit(1)
            else:
                print("✅ Pobieranie klubów zakończone pomyślnie!")

        # Pełne pobieranie lub standardowe
        else:
            download_photos = not args.no_photos
            download_stats = not args.no_stats

            if args.complete:
                print("🎯 Pełne pobieranie: posłowie + kluby + zdjęcia + statystyki...")
                stats = scraper.scrape_complete_term_data(args.term)
            else:
                print("👥 Pobieranie danych posłów...")
                stats = scraper.scrape_mps(args.term, download_photos, download_stats)

            print(f"\n📊 PODSUMOWANIE POBIERANIA KADENCJI {args.term}")
            print("=" * 60)
            print(f"Pobrani posłowie:       {stats['mps_downloaded']}")
            print(f"Pobrane kluby:          {stats['clubs_downloaded']}")
            print(f"Pobrane zdjęcia:        {stats['photos_downloaded']}")
            print(f"Pobrane statystyki:     {stats['voting_stats_downloaded']}")
            print(f"Błędy:                  {stats['errors']}")
            print("=" * 60)

            if stats['errors'] > 0:
                print(f"⚠️  Proces zakończony z {stats['errors']} błędami. Sprawdź logi.")
                sys.exit(1)
            else:
                print("✅ Proces zakończony pomyślnie!")

    except KeyboardInterrupt:
        logging.info("Proces przerwany przez użytkownika (Ctrl+C)")
        print("\n\n⏹️  Proces przerwany przez użytkownika.")
        sys.exit(1)

    except Exception as e:
        logging.exception("Nieoczekiwany błąd programu")
        print(f"\n❌ Nieoczekiwany błąd: {e}")
        print("Sprawdź logi dla szczegółów.")
        sys.exit(1)


if __name__ == "__main__":
    main()
