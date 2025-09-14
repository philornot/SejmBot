#!/usr/bin/env python3
# main.py
"""
SejmBot Scraper v3.0 - Główny entry-point
Zintegrowany z nową modularną architekturą
"""

import sys
from pathlib import Path

# Dodaj główny katalog do PYTHONPATH
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import argparse
import logging
from typing import Dict, Any

try:
    from SejmBotScraper import (
        # Główne komponenty
        create_scraper, get_settings, setup_logging, validate_installation,
        get_version_info, quick_scrape, quick_health_check,

        # Typy
        ScrapingStats,

        # Wyjątki
        SejmScraperError, ConfigValidationError
    )
except ImportError:
    # Fallback do relatywnych importów jeśli moduł nie jest zainstalowany
    try:
        from core.factory import create_scraper
        from config import get_settings, setup_logging
        from core.exceptions import SejmScraperError, ConfigValidationError
        from core.types import ScrapingStats


        # Mock functions for missing imports
        def validate_installation():
            return {'valid': True, 'issues': [], 'warnings': []}


        def get_version_info():
            return {
                'version': '3.0.0',
                'author': 'SejmBot Team',
                'description': 'Scraper for Polish Parliament transcripts',
                'python_version': sys.version,
                'platform': sys.platform
            }


        def quick_scrape(*args, **kwargs):
            return {}


        def quick_health_check():
            return {'healthy': True, 'components': {}}

    except ImportError as e:
        print(f"Błąd importu: {e}")
        print("Sprawdź czy wszystkie wymagane moduły są dostępne")
        sys.exit(1)

logger = logging.getLogger(__name__)


def print_banner():
    """Wyświetla banner aplikacji"""
    version_info = get_version_info()
    banner = f"""
╔══════════════════════════════════════════════════════════════════╗
║                    SejmBot Scraper v{version_info['version']}                        ║
║                                                                  ║
║               Pobieranie wypowiedzi z Sejmu RP                   ║
║                                                                  ║
╚══════════════════════════════════════════════════════════════════╝
    """
    print(banner)


def print_term_info(scraper, term: int):
    """Wyświetla informacje o kadencji"""
    try:
        # Pobierz informacje o kadencji
        terms = scraper.get_available_terms()
        if terms:
            term_info = next((t for t in terms if t.get('num') == term), None)
            if term_info:
                print(f"📅 Kadencja {term}: {term_info.get('from', '')} - {term_info.get('to', 'obecna')}")

        # Pobierz podsumowanie posiedzeń
        summary = scraper.get_term_proceedings_summary(term)
        if summary:
            total = len(summary)
            future = sum(1 for p in summary if p.get('is_future', False))
            current = sum(1 for p in summary if p.get('current', False))

            print(f"🏛️  Posiedzenia: {total} ogółem")
            if future > 0:
                print(f"⭐  Przyszłe: {future}")
            if current > 0:
                print(f"🔄 Bieżące: {current}")

    except Exception as e:
        logger.warning(f"Nie można pobrać informacji o kadencji: {e}")


def print_cache_stats(scraper):
    """Wyświetla szczegółowe statystyki cache"""
    try:
        stats = scraper.get_cache_stats()

        print("\n" + "=" * 60)
        print("📊 STATYSTYKI CACHE")
        print("=" * 60)

        # Memory cache
        memory_stats = stats.get('memory_cache', {})
        print(f"🧠 Memory Cache:")
        print(f"   Wpisy: {memory_stats.get('entries', 0)}")
        print(f"   Rozmiar: {memory_stats.get('size_mb', 0):.2f} MB")

        # File cache
        file_stats = stats.get('file_cache', {})
        print(f"\n📁 File Cache:")
        print(f"   Wpisy: {file_stats.get('entries', 0)}")
        print(f"   Rozmiar: {file_stats.get('size_mb', 0):.2f} MB")

        print("=" * 60)
    except Exception as e:
        print(f"Nie można pobrać statystyk cache: {e}")


def create_cli_parser():
    """Tworzy parser argumentów CLI"""
    parser = argparse.ArgumentParser(
        description="SejmBot Scraper v3.0 - pobiera wypowiedzi z posiedzeń Sejmu RP",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Przykłady użycia:
  %(prog)s                              # pobierz całą domyślną kadencję
  %(prog)s -t 9                         # pobierz 9. kadencję 
  %(prog)s -t 10 -p 15                  # pobierz konkretne posiedzenie 15
  %(prog)s -t 10 --no-full-text         # bez pełnej treści wypowiedzi (szybciej)
  %(prog)s --list-terms                 # wyświetl dostępne kadencje
  %(prog)s -t 10 --summary              # podsumowanie posiedzeń bez pobierania
  %(prog)s -v --log-file scraper.log    # verbose z zapisem do pliku

Zarządzanie cache:
  %(prog)s --cache-stats                # pokaż statystyki cache
  %(prog)s --clear-cache                # wyczyść cache
  %(prog)s --cleanup-cache              # wyczyść stare wpisy z cache
  %(prog)s --force                      # wymuś pobieranie (omiń cache)

Diagnostyka:
  %(prog)s --health-check               # sprawdź stan aplikacji
  %(prog)s --validate-install           # sprawdź instalację
  %(prog)s --version                    # pokaż wersję

Konfiguracja:
  %(prog)s --config .env.production     # użyj konkretnego pliku konfiguracji
  %(prog)s --show-config                # pokaż aktualną konfigurację
        """
    )

    # Główne opcje
    parser.add_argument(
        '-t', '--term',
        type=int,
        help='Numer kadencji (domyślnie z konfiguracji)'
    )

    parser.add_argument(
        '-p', '--proceeding',
        type=int,
        help='Numer konkretnego posiedzenia do pobrania'
    )

    # Opcje pobierania
    parser.add_argument(
        '--no-full-text',
        action='store_true',
        help='Nie pobieraj pełnej treści wypowiedzi (tylko podstawowe metadane)'
    )

    parser.add_argument(
        '--force',
        action='store_true',
        help='Wymuś pobieranie - omiń cache i pobierz wszystko ponownie'
    )

    # Opcje cache
    parser.add_argument(
        '--clear-cache',
        action='store_true',
        help='Wyczyść cache'
    )

    parser.add_argument(
        '--cache-stats',
        action='store_true',
        help='Wyświetl statystyki cache'
    )

    parser.add_argument(
        '--cleanup-cache',
        action='store_true',
        help='Wyczyść stare i wygasłe wpisy z cache'
    )

    # Opcje informacyjne
    parser.add_argument(
        '--list-terms',
        action='store_true',
        help='Wyświetl dostępne kadencje i zakończ'
    )

    parser.add_argument(
        '--summary',
        action='store_true',
        help='Wyświetl podsumowanie posiedzeń bez pobierania danych'
    )

    # Opcje diagnostyczne
    parser.add_argument(
        '--health-check',
        action='store_true',
        help='Sprawdź stan aplikacji'
    )

    parser.add_argument(
        '--validate-install',
        action='store_true',
        help='Sprawdź instalację aplikacji'
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

    parser.add_argument(
        '--show-config',
        action='store_true',
        help='Wyświetl aktualną konfigurację'
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
        help='Zapisuj logi do pliku'
    )

    return parser


def handle_cache_operations(args: Dict[str, Any], scraper) -> int:
    """Obsługuje operacje cache"""
    if args.get('clear_cache'):
        print("Czyszczenie cache...")
        try:
            scraper.clear_cache()
            print("Cache wyczyszczony")
        except AttributeError:
            print("Brak obsługi cache w tym scraperze")
        return 0

    if args.get('cleanup_cache'):
        print("Czyszczenie starych wpisów z cache...")
        try:
            scraper.cleanup_cache()
            print("Stare wpisy usunięte")
        except AttributeError:
            print("Brak obsługi cleanup cache w tym scraperze")
        return 0

    if args.get('cache_stats'):
        print_cache_stats(scraper)
        return 0

    return 1  # Nie obsłużono


def handle_info_operations(args: Dict[str, Any], scraper) -> int:
    """Obsługuje operacje informacyjne"""
    if args.get('list_terms'):
        print("Dostępne kadencje:")
        print("-" * 40)

        try:
            terms = scraper.get_available_terms()
            if terms:
                for term in reversed(terms):  # Najnowsze na górze
                    term_num = term.get('num', '?')
                    term_from = term.get('from', '')
                    term_to = term.get('to', 'obecna')
                    print(f"  Kadencja {term_num}: {term_from} - {term_to}")
            else:
                print("  Nie można pobrać listy kadencji")
        except Exception as e:
            print(f"  Błąd pobierania kadencji: {e}")
        return 0

    if args.get('summary'):
        term = args.get('term')
        if not term:
            settings = get_settings(args.get('config'))
            term = settings.get('default_term')

        print(f"Podsumowanie kadencji {term}")
        print("-" * 50)

        print_term_info(scraper, term)

        try:
            summary = scraper.get_term_proceedings_summary(term)
            if summary:
                print(f"\nLista posiedzeń:")
                for proc in summary:
                    number = proc.get('number', '?')
                    title = proc.get('title', 'Bez tytułu')
                    dates = ', '.join(proc.get('dates', []))
                    status = ""

                    if proc.get('current'):
                        status = " [BIEŻĄCE]"
                    elif proc.get('is_future'):
                        status = " [PRZYSZŁE]"

                    # Skróć tytuł jeśli za długi
                    if len(title) > 60:
                        title = title[:57] + "..."

                    print(f"  {number:3d}. {title}")
                    print(f"       {dates}{status}")
            else:
                print("Nie można pobrać listy posiedzeń")
        except Exception as e:
            print(f"Błąd pobierania podsumowania: {e}")
        return 0

    return 1  # Nie obsłużono


def handle_diagnostic_operations(args: Dict[str, Any]) -> int:
    """Obsługuje operacje diagnostyczne"""
    if args.get('health_check'):
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

    if args.get('validate_install'):
        print("Walidacja instalacji...")
        report = validate_installation()

        print("\nRAPORT INSTALACJI")
        print("=" * 40)
        print(f"Status: {'POPRAWNA' if report['valid'] else 'PROBLEMY'}")

        if report['issues']:
            print("\nBłędy:")
            for issue in report['issues']:
                print(f"  - {issue}")

        if report['warnings']:
            print("\nOstrzeżenia:")
            for warning in report['warnings']:
                print(f"  - {warning}")

        return 0 if report['valid'] else 1

    if args.get('version'):
        info = get_version_info()
        print(f"\nSejmBotScraper v{info['version']}")
        print(f"Autor: {info['author']}")
        print(f"Opis: {info['description']}")
        print(f"Python: {info['python_version']}")
        print(f"Platforma: {info['platform']}")
        return 0

    return 1  # Nie obsłużono


def handle_config_operations(args: Dict[str, Any]) -> int:
    """Obsługuje operacje konfiguracji"""
    if args.get('show_config'):
        settings = get_settings(args.get('config'))
        settings.print_summary()
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
            # Tymczasowo ustaw logowanie do pliku
            import logging
            from logging.handlers import RotatingFileHandler

            log_file = Path(settings.get('logging.log_dir')) / args['log_file']
            log_file.parent.mkdir(parents=True, exist_ok=True)

            level = logging.DEBUG if args.get('verbose') else logging.INFO

            # Konfiguruj logowanie
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

        # Sprawdź czy to tylko operacje diagnostyczne/informacyjne
        info_ops = ['version', 'health_check', 'validate_install', 'show_config']
        cache_ops = ['clear_cache', 'cache_stats', 'cleanup_cache']
        list_ops = ['list_terms', 'summary']

        is_simple_operation = any(args.get(op) for op in info_ops + cache_ops + list_ops)

        # Wyświetl banner tylko dla głównych operacji
        if not is_simple_operation:
            print_banner()

        # Obsłuż operacje diagnostyczne
        if any(args.get(op) for op in info_ops):
            return handle_diagnostic_operations(args)

        # Obsłuż operacje konfiguracji
        if args.get('show_config'):
            return handle_config_operations(args)

        # Utwórz scraper (dla pozostałych operacji)
        term = args.get('term') or settings.get('default_term')

        # Ustaw tryb scrapowania
        scraping_config = settings.get('scraping').copy()
        if args.get('force'):
            scraping_config['mode'] = 'force_refresh'
            print("TRYB WYMUSZONY - wszystkie dane zostaną pobrane ponownie")

        scraper = create_scraper(args.get('config'))

        # Obsłuż operacje cache
        if any(args.get(op) for op in cache_ops):
            return handle_cache_operations(args, scraper)

        # Obsłuż operacje informacyjne
        if any(args.get(op) for op in list_ops):
            return handle_info_operations(args, scraper)

        # === GŁÓWNE OPERACJE SCRAPOWANIA ===

        # Walidacja parametrów
        if args.get('proceeding') is not None and args['proceeding'] <= 0:
            print(f"Błąd: Numer posiedzenia musi być większy niż 0 (podano: {args['proceeding']})")
            return 1

        logger.info("Rozpoczynanie procesu pobierania wypowiedzi...")

        # Wyświetl info o kadencji
        print_term_info(scraper, term)

        fetch_full_statements = not args.get('no_full_text', False)

        if fetch_full_statements:
            print("Będą pobierane pełne treści wypowiedzi (może potrwać dłużej)")
        else:
            print("Pobieranie tylko metadanych wypowiedzi (szybszy tryb)")

        # Konkretne posiedzenie
        if args.get('proceeding'):
            proceeding = args['proceeding']
            print(f"\nPobieranie posiedzenia {proceeding} z kadencji {term}")

            success = scraper.scrape_proceeding(
                term,
                proceeding,
                fetch_full_statements=fetch_full_statements
            )

            if success:
                print(f"\nPomyślnie pobrano posiedzenie {proceeding}")
                return 0
            else:
                print(f"\nBłąd podczas pobierania posiedzenia {proceeding}")
                return 1

        # Cała kadencja
        else:
            print(f"\nPobieranie całej kadencji {term}")
            print("To może potrwać kilka minut...")

            stats = scraper.scrape_term(
                term,
                fetch_full_statements=fetch_full_statements,
                force_refresh=args.get('force', False)
            )

            print(f"\nPODSUMOWANIE POBIERANIA KADENCJI {term}")
            print("=" * 60)
            print(f"Przetworzone posiedzenia:     {stats.get('proceedings_processed', 0)}")
            print(f"Pominięte przyszłe:           {stats.get('future_proceedings_skipped', 0)}")
            print(f"Przetworzone wypowiedzi:      {stats.get('statements_processed', 0)}")
            print(f"Wypowiedzi z pełną treścią:   {stats.get('statements_with_full_content', 0)}")
            print(f"Zidentyfikowani mówcy:        {stats.get('speakers_identified', 0)}")
            print(f"Wzbogacenia danymi posłów:    {stats.get('mp_data_enrichments', 0)}")
            print(f"Błędy:                        {stats.get('errors', 0)}")
            print("=" * 60)

            if stats.get('errors', 0) > 0:
                print(f"Proces zakończony z {stats['errors']} błędami. Sprawdź logi.")
                return 1
            else:
                print("Proces zakończony pomyślnie!")

        # Wyświetl informację o strukturze danych
        print(f"\nDane zapisane w: {settings.get('scraping.base_output_dir')}")
        print("Struktura:")
        print("   └── kadencja_XX/")
        print("       ├── posiedzenie_XXX_YYYY-MM-DD/")
        print("       │   ├── info_posiedzenia.json")
        print("       │   └── transcripts/")
        print("       │       └── transkrypty_YYYY-MM-DD.json")

        if not fetch_full_statements:
            print("\nWskazówka: Uruchom ponownie bez --no-full-text aby pobrać pełne treści")

        # Wyświetl informacje o cache na koniec
        try:
            cache_stats = scraper.get_cache_stats()
            print("\nCache info:")
            print(f"   Memory: {cache_stats.get('memory_cache', {}).get('entries', 0)} wpisów")
            print(f"   File: {cache_stats.get('file_cache', {}).get('entries', 0)} wpisów")
            print("   Użyj --cache-stats aby zobaczyć szczegóły")
        except:
            pass  # Ignoruj błędy cache stats

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
