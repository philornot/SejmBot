#!/usr/bin/env python3
# main.py
"""
SejmBot Scraper - Główny entry-point

Narzędzie do pobierania wypowiedzi z posiedzeń Sejmu RP
bez pobierania PDF-ów - tylko przez API JSON/HTML.
Z zaawansowaną obsługą cache dla wydajności.
"""

import argparse
import logging
import sys
from pathlib import Path

from config import LOG_LEVEL, LOG_FORMAT, LOGS_DIR, DEFAULT_TERM
from scraper import SejmScraper


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
            print("Kontynuję tylko z logowaniem do konsoli.")

    # Konfiguruj logger podstawowy z handlerami
    root_logger.setLevel(level)
    for handler in handlers:
        root_logger.addHandler(handler)


def print_banner():
    """Wyświetla banner aplikacji"""
    banner = """
╔══════════════════════════════════════════════════════════════╗
║                    SejmBot Scraper                           ║
║                                                              ║
║            Pobieranie wypowiedzi z Sejmu RP                  ║
║                  (bez PDF-ów, tylko API)                     ║
║                      Wersja 1.0.0                            ║
╚══════════════════════════════════════════════════════════════╝
    """
    print(banner)


def print_term_info(scraper, term):
    """Wyświetla informacje o kadencji"""
    try:
        # Pobierz informacje o kadencji
        term_info = scraper.api.get_term_info(term)
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
        logging.warning(f"Nie można pobrać informacji o kadencji: {e}")


def print_cache_stats(scraper: SejmScraper):
    """Wyświetla szczegółowe statystyki cache"""
    stats = scraper.get_cache_stats()

    print("\n" + "=" * 60)
    print("📊 STATYSTYKI CACHE")
    print("=" * 60)

    # API Cache
    api_stats = stats['api_cache']
    print(f"🔌 API Cache:")
    print(f"   Łączne wpisy: {api_stats['total_entries']}")
    print(f"   Wygasłe: {api_stats['expired']}")
    print(f"   Przestarzałe (1h): {api_stats['stale_1h']}")
    print(f"   Przestarzałe (24h): {api_stats['stale_24h']}")

    # File Cache
    file_stats = stats['file_cache']
    print(f"\n📄 File Cache:")
    print(f"   Łączne wpisy: {file_stats['total_entries']}")
    print(f"   Pliki istnieją: {file_stats['files_exist']}")
    print(f"   Brakujące pliki: {file_stats['files_missing']}")

    # Disk usage
    disk_stats = stats['disk_usage']
    print(f"\n💾 Użycie dysku:")
    print(f"   Rozmiar cache: {disk_stats['cache_dir_size_mb']:.2f} MB")

    # Recommendations
    print(f"\n💡 Rekomendacje:")
    if api_stats['expired'] > 0:
        print(f"   • Uruchom --cleanup-cache aby usunąć {api_stats['expired']} wygasłych wpisów")

    if file_stats['files_missing'] > 0:
        print(
            f"   • {file_stats['files_missing']} plików z cache nie istnieje - cache zostanie automatycznie wyczyszczony")

    if disk_stats['cache_dir_size_mb'] > 100:
        print(f"   • Cache zajmuje dużo miejsca - rozważ --cleanup-cache")

    print("=" * 60)


def create_cli_parser():
    """Tworzy parser argumentów CLI z obsługą cache"""
    parser = argparse.ArgumentParser(
        description="SejmBot Scraper - pobiera wypowiedzi z posiedzeń Sejmu RP (bez PDF-ów)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Przykłady użycia:
  %(prog)s                              # pobierz całą 10. kadencję (tylko wypowiedzi)
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
  %(prog)s --dry-run                    # tryb testowy - nie zapisuj danych

UWAGA: Program pobiera tylko wypowiedzi przez API (JSON/HTML).
       Nie pobiera PDF-ów stenogramów.
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

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Tryb testowy - nie zapisuj danych, tylko pokaż co byłoby robione'
    )

    # Opcje cache
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
        '--cleanup-cache',
        action='store_true',
        help='Wyczyść stare i wygasłe wpisy z cache'
    )

    parser.add_argument(
        '--cache-type',
        choices=['api', 'files', 'all'],
        default='all',
        help='Typ cache do wyczyszczenia (używane z --clear-cache)'
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


def main():
    """Główna funkcja programu"""
    parser = create_cli_parser()
    args = parser.parse_args()

    # Konfiguruj logowanie przed jakąkolwiek operacją
    setup_logging(args.verbose, args.log_file)

    logger = logging.getLogger(__name__)

    # Sprawdź czy to tylko operacje na cache lub informacyjne
    cache_only_operations = [args.clear_cache, args.cache_stats, args.cleanup_cache]
    info_only_operations = [args.list_terms, args.summary]

    # Wyświetl banner tylko dla głównych operacji
    if not any(cache_only_operations + info_only_operations):
        print_banner()

    try:
        # Utwórz scraper
        scraper = SejmScraper(force_refresh=args.force)

        if args.dry_run:
            print("🧪 TRYB TESTOWY - nie będą zapisywane żadne dane")

        # === OPERACJE TYLKO NA CACHE ===
        if args.clear_cache:
            print(f"🧹 Czyszczenie cache ({args.cache_type})...")
            scraper.clear_cache(args.cache_type)
            print("✅ Cache wyczyszczony")
            return

        if args.cleanup_cache:
            print("🧹 Czyszczenie starych wpisów z cache...")
            scraper.cleanup_cache()
            print("✅ Stare wpisy usunięte")
            return

        if args.cache_stats:
            print_cache_stats(scraper)
            return

        # === OPERACJE INFORMACYJNE ===
        # Lista dostępnych kadencji
        if args.list_terms:
            print("📋 Dostępne kadencje:")
            print("-" * 40)

            terms = scraper.get_available_terms()
            if terms:
                for term in reversed(terms):  # Najnowsze na górze
                    term_num = term.get('num', '?')
                    term_from = term.get('from', '')
                    term_to = term.get('to', 'obecna')
                    print(f"  Kadencja {term_num}: {term_from} - {term_to}")
            else:
                print("  Nie można pobrać listy kadencji")
            return

        # Podsumowanie posiedzeń
        if args.summary:
            print(f"📊 Podsumowanie kadencji {args.term}")
            print("-" * 50)

            print_term_info(scraper, args.term)

            summary = scraper.get_term_proceedings_summary(args.term)
            if summary:
                print(f"\n📄 Lista posiedzeń:")
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
                    print(f"       📅 {dates}{status}")
            else:
                print("Nie można pobrać listy posiedzeń")
            return

        # === GŁÓWNE OPERACJE SCRAPOWANIA ===

        # Walidacja parametrów
        if args.proceeding is not None and args.proceeding <= 0:
            print(f"Błąd: Numer posiedzenia musi być większy niż 0 (podano: {args.proceeding})")
            sys.exit(1)

        if args.force:
            print("⚡ TRYB WYMUSZONY - wszystkie dane zostaną pobrane ponownie")

        logging.info("Rozpoczynanie procesu pobierania wypowiedzi...")

        # Wyświetl info o kadencji
        print_term_info(scraper, args.term)

        fetch_full_statements = not args.no_full_text

        if fetch_full_statements:
            print("📄 Będą pobierane pełne treści wypowiedzi (może potrwać dłużej)")
        else:
            print("⚡ Pobieranie tylko metadanych wypowiedzi (szybszy tryb)")

        # Konkretne posiedzenie
        if args.proceeding:
            print(f"\n🎯 Pobieranie posiedzenia {args.proceeding} z kadencji {args.term}")

            if not args.dry_run:
                success = scraper.scrape_specific_proceeding(
                    args.term,
                    args.proceeding,
                    fetch_full_statements
                )

                if success:
                    print(f"\n✅ Pomyślnie pobrano posiedzenie {args.proceeding}")
                else:
                    print(f"\n❌ Błąd podczas pobierania posiedzenia {args.proceeding}")
                    sys.exit(1)
            else:
                print(f"🧪 Tryb testowy: pobrano by posiedzenie {args.proceeding}")

        # Cała kadencja
        else:
            print(f"\n🏛️  Pobieranie całej kadencji {args.term}")
            print("⏳ To może potrwać kilka minut...")

            if not args.dry_run:
                stats = scraper.scrape_term(args.term, fetch_full_statements, args.force)

                print(f"\n📊 PODSUMOWANIE POBIERANIA KADENCJI {args.term}")
                print("=" * 60)
                print(f"Przetworzone posiedzenia:     {stats['proceedings_processed']}")
                print(f"Pominięte przyszłe:           {stats['future_proceedings_skipped']}")
                print(f"Przetworzone wypowiedzi:      {stats['statements_processed']}")
                print(f"Wypowiedzi z pełną treścią:   {stats['statements_with_full_content']}")
                print(f"Zidentyfikowani mówcy:        {stats['speakers_identified']}")
                print(f"Wzbogacenia danymi posłów:    {stats['mp_data_enrichments']}")
                print(f"Błędy:                        {stats['errors']}")
                print("=" * 60)

                if stats['errors'] > 0:
                    print(f"⚠️  Proces zakończony z {stats['errors']} błędami. Sprawdź logi.")
                    sys.exit(1)
                else:
                    print("✅ Proces zakończony pomyślnie!")
            else:
                print(f"🧪 Tryb testowy: pobrano by całą kadencję {args.term}")

        # Wyświetl informację o strukturze danych
        if not args.dry_run:
            print(f"\n📁 Dane zapisane w: {scraper.file_manager.base_dir}")
            print("📋 Struktura:")
            print("   └── kadencja_XX/")
            print("       ├── posiedzenie_XXX_YYYY-MM-DD/")
            print("       │   ├── info_posiedzenia.json")
            print("       │   └── transcripts/")
            print("       │       └── transkrypty_YYYY-MM-DD.json")

            if not fetch_full_statements:
                print("\n💡 Wskazówka: Uruchom ponownie bez --no-full-text aby pobrać pełne treści")

        # Wyświetl informacje o cache na koniec (tylko dla głównych operacji)
        if not any(cache_only_operations + info_only_operations) and not args.dry_run:
            print("\n💾 Cache info:")
            cache_stats = scraper.get_cache_stats()
            print(f"   API: {cache_stats['api_cache']['total_entries']} wpisów")
            print(f"   Pliki: {cache_stats['file_cache']['total_entries']} wpisów")
            print("   Użyj --cache-stats aby zobaczyć szczegóły")

    except KeyboardInterrupt:
        logging.info("Proces przerwany przez użytkownika (Ctrl+C)")
        print("\n\n⏹️  Proces przerwany przez użytkownika.")
        sys.exit(1)

    except Exception as e:
        logger.error(f"Nieoczekiwany błąd: {e}")
        logging.exception("Nieoczekiwany błąd programu")
        print(f"\n❌ Nieoczekiwany błąd: {e}")
        print("Sprawdź logi dla szczegółów.")
        sys.exit(1)

    return 0


if __name__ == "__main__":
    exit(main())
