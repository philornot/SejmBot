#!/usr/bin/env python3
# main.py
"""
SejmBotScraper - Narzędzie do pobierania i przetwarzania danych z Sejmu RP

Główny plik uruchamiający program do pobierania stenogramów,
danych posłów i tworzenia gotowych do analizy zbiorów danych
z API Sejmu Rzeczypospolitej Polskiej.
"""

import argparse
import logging
import sys
from pathlib import Path

from config import LOG_LEVEL, LOG_FORMAT, LOGS_DIR, DEFAULT_TERM
from mp_scraper import MPScraper
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
            print("Kontynuuję tylko z logowaniem do konsoli.")

    # Konfiguruj logger podstawowy z handlerami
    root_logger.setLevel(level)
    for handler in handlers:
        root_logger.addHandler(handler)


def print_banner():
    """Wyświetla banner aplikacji"""
    banner = """
╔══════════════════════════════════════════════════════════════╗
║                     SejmBotScraper v2.0                      ║
║                                                              ║
║     Kompleksowe narzędzie do pobierania danych Sejmu RP      ║
║         • Stenogramy i wypowiedzi                            ║
║         • Dane posłów i klubów                               ║
║         • Gotowe zbiory do analizy                           ║
╚══════════════════════════════════════════════════════════════╝
    """
    print(banner)


def print_workflow_info():
    """Wyświetla informacje o domyślnym workflow"""
    info = """
🔄 DOMYŚLNY WORKFLOW:
1. 👥 Pobieranie danych posłów i klubów
2. 📄 Pobieranie stenogramów i wypowiedzi
3. 🔗 Wzbogacanie wypowiedzi o dane posłów
4. 💾 Generowanie gotowych zbiorów JSON
"""
    print(info)


def create_parser():
    """Tworzy parser argumentów CLI"""
    parser = argparse.ArgumentParser(
        description="SejmBotScraper - kompleksowe pobieranie danych Sejmu RP",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
PRZYKŁADY UŻYCIA:

Podstawowe:
  %(prog)s                                    # pełny workflow dla kadencji 10
  %(prog)s -t 9                               # pełny workflow dla kadencji 9
  %(prog)s -t 10 -p 15                        # tylko posiedzenie 15

Selektywne pobieranie:
  %(prog)s --mps-only                         # tylko dane posłów
  %(prog)s --transcripts-only                 # tylko stenogramy
  %(prog)s --transcripts-only --full-text     # stenogramy z pełnym tekstem
  %(prog)s --no-enrich                        # bez wzbogacania o dane posłów

Informacyjne:
  %(prog)s --list-terms                       # lista kadencji
  %(prog)s --summary                          # podsumowanie posiedzeń
  %(prog)s --mp-summary                       # podsumowanie posłów

Zaawansowane:
  %(prog)s --skip-existing                    # pomiń istniejące pliki
  %(prog)s --enrich-existing                  # wzbogać istniejące dane
  %(prog)s -v --log-file scraper.log          # verbose z logiem
        """
    )

    # === GŁÓWNE OPCJE ===
    main_group = parser.add_argument_group('Główne opcje')

    main_group.add_argument(
        '-t', '--term',
        type=int,
        default=DEFAULT_TERM,
        help=f'Numer kadencji (domyślnie: {DEFAULT_TERM})'
    )

    main_group.add_argument(
        '-p', '--proceeding',
        type=int,
        help='Numer konkretnego posiedzenia'
    )

    # === TRYBY PRACY ===
    mode_group = parser.add_argument_group('Tryby pracy (wykluczają się)')
    mode_exclusive = mode_group.add_mutually_exclusive_group()

    mode_exclusive.add_argument(
        '--mps-only',
        action='store_true',
        help='Pobierz tylko dane posłów i klubów'
    )

    mode_exclusive.add_argument(
        '--transcripts-only',
        action='store_true',
        help='Pobierz tylko stenogramy i wypowiedzi'
    )

    mode_exclusive.add_argument(
        '--enrich-only',
        action='store_true',
        help='Tylko wzbogacanie istniejących danych'
    )

    # === OPCJE POBIERANIA POSŁÓW ===
    mp_group = parser.add_argument_group('Opcje danych posłów')

    mp_group.add_argument(
        '--no-mp-photos',
        action='store_true',
        help='Nie pobieraj zdjęć posłów'
    )

    mp_group.add_argument(
        '--no-mp-stats',
        action='store_true',
        help='Nie pobieraj statystyk głosowań posłów'
    )

    mp_group.add_argument(
        '--mp-id',
        type=int,
        help='Pobierz tylko konkretnego posła (ID)'
    )

    # === OPCJE POBIERANIA STENOGRAMÓW ===
    transcript_group = parser.add_argument_group('Opcje stenogramów')

    transcript_group.add_argument(
        '--full-text',
        action='store_true',
        help='Pobierz pełne teksty wypowiedzi (nie tylko metadane)'
    )

    transcript_group.add_argument(
        '--skip-statements',
        action='store_true',
        help='Nie pobieraj indywidualnych wypowiedzi'
    )

    # === OPCJE WZBOGACANIA ===
    enrich_group = parser.add_argument_group('Opcje wzbogacania danych')

    enrich_group.add_argument(
        '--no-enrich',
        action='store_true',
        help='Nie wzbogacaj wypowiedzi o dane posłów'
    )

    enrich_group.add_argument(
        '--enrich-existing',
        action='store_true',
        help='Wzbogać istniejące dane (bez ponownego pobierania)'
    )

    enrich_group.add_argument(
        '--skip-existing',
        action='store_true',
        help='Pomiń istniejące pliki podczas pobierania'
    )

    # === OPCJE INFORMACYJNE ===
    info_group = parser.add_argument_group('Opcje informacyjne')

    info_group.add_argument(
        '--list-terms',
        action='store_true',
        help='Wyświetl dostępne kadencje'
    )

    info_group.add_argument(
        '--summary',
        action='store_true',
        help='Podsumowanie posiedzeń dla kadencji'
    )

    info_group.add_argument(
        '--mp-summary',
        action='store_true',
        help='Podsumowanie posłów dla kadencji'
    )

    # === OPCJE LOGOWANIA ===
    log_group = parser.add_argument_group('Opcje logowania')

    log_group.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Szczegółowe logi (DEBUG level)'
    )

    log_group.add_argument(
        '--log-file',
        type=str,
        help='Zapisuj logi do pliku (w katalogu logs/)'
    )

    return parser


def validate_args(args):
    """Waliduje argumenty CLI"""
    issues = []

    # Walidacja numerów
    if args.term <= 0:
        issues.append(f"Numer kadencji musi być większy niż 0 (podano: {args.term})")

    if args.proceeding is not None and args.proceeding <= 0:
        issues.append(f"Numer posiedzenia musi być większy niż 0 (podano: {args.proceeding})")

    if args.mp_id is not None and args.mp_id <= 0:
        issues.append(f"ID posła musi być większe niż 0 (podano: {args.mp_id})")

    # Logika trybów
    if args.mp_id and not args.mps_only:
        issues.append("Opcja --mp-id wymaga trybu --mps-only")

    if args.enrich_existing and args.no_enrich:
        issues.append("--enrich-existing i --no-enrich wykluczają się")

    if args.full_text and args.skip_statements:
        issues.append("--full-text i --skip-statements wykluczają się")

    return issues


def run_mps_workflow(args, mp_scraper):
    """Uruchamia workflow pobierania danych posłów"""
    print("👥 POBIERANIE DANYCH POSŁÓW I KLUBÓW")
    print("=" * 60)

    download_photos = not args.no_mp_photos
    download_stats = not args.no_mp_stats

    if args.mp_id:
        # Konkretny poseł
        success = mp_scraper.scrape_specific_mp(
            args.term,
            args.mp_id,
            download_photos,
            download_stats
        )

        if success:
            print(f"✅ Pobrano dane posła ID {args.mp_id}")
            return {'mps_downloaded': 1, 'clubs_downloaded': 0, 'errors': 0}
        else:
            print(f"❌ Błąd pobierania posła ID {args.mp_id}")
            return {'mps_downloaded': 0, 'clubs_downloaded': 0, 'errors': 1}
    else:
        # Pełne pobieranie
        stats = mp_scraper.scrape_complete_term_data(args.term)

        print(f"Pobrani posłowie:    {stats['mps_downloaded']}")
        print(f"Pobrane kluby:       {stats['clubs_downloaded']}")
        print(f"Pobrane zdjęcia:     {stats['photos_downloaded']}")
        print(f"Pobrane statystyki:  {stats['voting_stats_downloaded']}")
        print(f"Błędy:               {stats['errors']}")

        return stats


def run_transcripts_workflow(args, sejm_scraper):
    """Uruchamia workflow pobierania stenogramów"""
    print("📄 POBIERANIE STENOGRAMÓW I WYPOWIEDZI")
    print("=" * 60)

    download_statements = not args.skip_statements

    if args.proceeding:
        # Konkretne posiedzenie
        success = sejm_scraper.scrape_specific_proceeding(
            args.term,
            args.proceeding,
            download_statements,
            args.full_text
        )

        if success:
            print(f"✅ Pobrano posiedzenie {args.proceeding}")
            return {'proceedings_processed': 1, 'errors': 0}
        else:
            print(f"❌ Błąd pobierania posiedzenia {args.proceeding}")
            return {'proceedings_processed': 0, 'errors': 1}
    else:
        # Pełna kadencja
        stats = sejm_scraper.scrape_term(
            args.term,
            download_statements,
            args.full_text,
            skip_existing=args.skip_existing
        )

        print(f"Przetworzone posiedzenia: {stats['proceedings_processed']}")
        print(f"Pominięte przyszłe:       {stats.get('future_proceedings_skipped', 0)}")
        print(f"Zapisane wypowiedzi:      {stats['statements_saved']}")
        print(f"Błędy:                    {stats['errors']}")

        return stats


def run_enrichment_workflow(args, sejm_scraper, mp_scraper):
    """Uruchamia workflow wzbogacania danych"""
    print("🔗 WZBOGACANIE WYPOWIEDZI O DANE POSŁÓW")
    print("=" * 60)

    try:
        # Implementacja wzbogacania - to będzie dodane w scraper.py
        stats = sejm_scraper.enrich_statements_with_mp_data(
            args.term,
            proceeding=args.proceeding
        )

        print(f"Wzbogacone wypowiedzi:  {stats['enriched_statements']}")
        print(f"Utworzone zbiory JSON:  {stats['json_files_created']}")
        print(f"Błędy:                  {stats['errors']}")

        return stats
    except AttributeError:
        print("⚠️  Funkcja wzbogacania nie jest jeszcze zaimplementowana")
        return {'enriched_statements': 0, 'json_files_created': 0, 'errors': 0}


def run_full_workflow(args, sejm_scraper, mp_scraper):
    """Uruchamia pełny workflow"""
    print("🎯 PEŁNY WORKFLOW - KOMPLETNE POBIERANIE I PRZETWARZANIE")
    print("=" * 70)

    total_stats = {
        'mps_downloaded': 0,
        'clubs_downloaded': 0,
        'photos_downloaded': 0,
        'voting_stats_downloaded': 0,
        'proceedings_processed': 0,
        'statements_saved': 0,
        'enriched_statements': 0,
        'json_files_created': 0,
        'errors': 0
    }

    # Krok 1: Posłowie (jeśli nie --transcripts-only)
    print("\n" + "=" * 20 + " KROK 1: DANE POSŁÓW " + "=" * 20)
    mp_stats = run_mps_workflow(args, mp_scraper)

    for key in ['mps_downloaded', 'clubs_downloaded', 'photos_downloaded', 'voting_stats_downloaded', 'errors']:
        if key in mp_stats:
            total_stats[key] += mp_stats[key]

    # Krok 2: Stenogramy
    print("\n" + "=" * 18 + " KROK 2: STENOGRAMY " + "=" * 18)
    transcript_stats = run_transcripts_workflow(args, sejm_scraper)

    for key in ['proceedings_processed', 'statements_saved', 'errors']:
        if key in transcript_stats:
            total_stats[key] += transcript_stats[key]

    # Krok 3: Wzbogacanie (jeśli nie --no-enrich)
    if not args.no_enrich:
        print("\n" + "=" * 18 + " KROK 3: WZBOGACANIE " + "=" * 18)
        enrich_stats = run_enrichment_workflow(args, sejm_scraper, mp_scraper)

        for key in ['enriched_statements', 'json_files_created', 'errors']:
            if key in enrich_stats:
                total_stats[key] += enrich_stats[key]

    return total_stats


def main():
    """Główna funkcja programu"""
    parser = create_parser()
    args = parser.parse_args()

    # Walidacja argumentów
    issues = validate_args(args)
    if issues:
        print("❌ BŁĘDY ARGUMENTÓW:")
        for issue in issues:
            print(f"   • {issue}")
        sys.exit(1)

    # Konfiguruj logowanie
    setup_logging(args.verbose, args.log_file)

    # Wyświetl banner dla głównych operacji
    if not any([args.list_terms, args.summary, args.mp_summary]):
        print_banner()
        if not any([args.mps_only, args.transcripts_only, args.enrich_only]):
            print_workflow_info()

    # Utwórz scrapery
    sejm_scraper = SejmScraper()
    mp_scraper = MPScraper()

    try:
        # === OPCJE INFORMACYJNE ===
        if args.list_terms:
            terms = sejm_scraper.get_available_terms()
            if terms:
                print("Dostępne kadencje Sejmu RP:")
                print("-" * 50)
                for term in terms:
                    current = " (OBECNA)" if term.get('current') else ""
                    print(f"Kadencja {term['num']:2d}: {term.get('from', '?')} - {term.get('to', 'trwa')}{current}")
            else:
                print("Nie można pobrać listy kadencji.")
            return

        if args.summary:
            summary = sejm_scraper.get_term_proceedings_summary(args.term)
            if summary:
                print(f"Posiedzenia kadencji {args.term}:")
                print("-" * 60)
                for proc in summary:
                    current = " [TRWA]" if proc.get('current') else ""
                    future = " [PRZYSZŁE]" if proc.get('is_future') else ""
                    dates_str = ", ".join(proc['dates']) if proc['dates'] else "brak dat"
                    print(f"Posiedzenie {proc['number']:3d}: {dates_str}{current}{future}")
                    if proc.get('title'):
                        print(f"    Tytuł: {proc['title'][:80]}{'...' if len(proc['title']) > 80 else ''}")
                    print()
            else:
                print(f"Nie można pobrać informacji o posiedzeniach kadencji {args.term}.")
            return

        if args.mp_summary:
            summary = mp_scraper.get_mps_summary(args.term)
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

        # === GŁÓWNY PROCES ===
        logging.info("Rozpoczynanie procesu pobierania danych...")

        # Wybór workflow
        if args.mps_only:
            stats = run_mps_workflow(args, mp_scraper)
        elif args.transcripts_only:
            stats = run_transcripts_workflow(args, sejm_scraper)
        elif args.enrich_only or args.enrich_existing:
            stats = run_enrichment_workflow(args, sejm_scraper, mp_scraper)
        else:
            # Pełny workflow
            stats = run_full_workflow(args, sejm_scraper, mp_scraper)

        # Podsumowanie końcowe
        print(f"\n📊 PODSUMOWANIE KOŃCOWE - KADENCJA {args.term}")
        print("=" * 70)

        if not args.transcripts_only and not args.enrich_only:
            print(f"Pobrani posłowie:       {stats.get('mps_downloaded', 0)}")
            print(f"Pobrane kluby:          {stats.get('clubs_downloaded', 0)}")
            print(f"Pobrane zdjęcia:        {stats.get('photos_downloaded', 0)}")
            print(f"Pobrane statystyki:     {stats.get('voting_stats_downloaded', 0)}")

        if not args.mps_only:
            print(f"Przetworzone posiedzenia: {stats.get('proceedings_processed', 0)}")
            print(f"Zapisane wypowiedzi:      {stats.get('statements_saved', 0)}")

        if not args.no_enrich and not args.mps_only and not args.transcripts_only:
            print(f"Wzbogacone wypowiedzi:    {stats.get('enriched_statements', 0)}")
            print(f"Utworzone zbiory JSON:    {stats.get('json_files_created', 0)}")

        print(f"Łączne błędy:             {stats.get('errors', 0)}")
        print("=" * 70)

        if stats.get('errors', 0) > 0:
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
