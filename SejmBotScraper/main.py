#!/usr/bin/env python3
"""
WERSJA DEBUG - main.py z dodatkowymi logami i timeoutem
Znajdzie miejsce, w którym program może się zawiesić
"""

import argparse
import logging
import sys
import concurrent.futures
import functools
from pathlib import Path

# Dodaj katalog główny do PYTHONPATH
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

logger = logging.getLogger(__name__)


"""Obsługa limitu czasu (cross-platform).

Zamiast używać mechanizmu sygnałów (SIGALRM), który nie jest dostępny na
Windows, korzystamy z ThreadPoolExecutor i metody future.result(timeout=...).
Jeśli wywołanie funkcji przekroczy limit czasu, wypisujemy komunikat i
zwracamy None.
"""


def with_timeout(seconds):
    """Dekorator ustawiający limit czasu dla wywołań funkcji (cross-platform).

    Parametry:
      seconds (int): limit czasu w sekundach

    Zwraca None i wypisuje komunikat w przypadku przekroczenia limitu.
    """

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(func, *args, **kwargs)
                try:
                    return future.result(timeout=seconds)
                except concurrent.futures.TimeoutError:
                    print(
                        f"\n⏰ TIMEOUT - operacja '{func.__name__}' przekroczyła {seconds} sekund"
                    )
                    return None

        return wrapper

    return decorator


def print_banner():
    """Wyświetla banner aplikacji"""
    banner = f"""
╔══════════════════════════════════════════════════════════════════╗
║                    SejmBot Scraper v3.1 DEBUG                   ║
║                                                                  ║
║           POBIERANIE TREŚCI WYPOWIEDZI Z SEJMU RP                ║
║                                                                  ║
╚══════════════════════════════════════════════════════════════════╝
    """
    print(banner)


def create_cli_parser():
    """Tworzy parser argumentów CLI"""
    parser = argparse.ArgumentParser(
        description="SejmBot Scraper v3.1 DEBUG - znajdź gdzie się zawiesza",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "-t", "--term", type=int, default=10, help="Numer kadencji (domyślnie 10)"
    )
    parser.add_argument(
        "-p", "--proceeding", type=int, help="Numer konkretnego posiedzenia"
    )
    parser.add_argument(
        "--max-proceedings",
        type=int,
        default=1,
        help="Maksymalna liczba posiedzeń (domyślnie 1)",
    )
    parser.add_argument(
        "--test-content", action="store_true", help="Test pobierania treści"
    )
    parser.add_argument("--health", action="store_true", help="Sprawdź stan systemu")
    parser.add_argument("--debug", action="store_true", help="Debug mode")
    parser.add_argument(
        "--timeout", type=int, default=60, help="Timeout w sekundach (domyślnie 60)"
    )

    return parser


def setup_logging_debug():
    """Konfiguruje szczegółowe logowanie"""
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )
    print("🔍 Włączono szczegółowe debugowanie")


@with_timeout(30)  # 30 sekund na import
def debug_imports():
    """Testuje importy z timeoutem"""
    print("🔧 KROK 1: Testowanie importów...")

    try:
        print("  - Importowanie core...")
        from SejmBotScraper.core import create_scraper, get_version_info

        print("  ✅ Core zaimportowany")

        return create_scraper, get_version_info
    except Exception as e:
        print(f"  ❌ Błąd importu: {e}")
        return None, None


@with_timeout(30)  # 30 sekund na utworzenie scrapera
def debug_scraper_creation():
    """Testuje utworzenie scrapera z timeoutem"""
    print("🔧 KROK 2: Tworzenie scrapera...")

    create_scraper, get_version_info = debug_imports()
    if not create_scraper:
        return None

    try:
        config = {"max_proceedings": 1}
        print("  - Wywołuję create_scraper...")
        scraper = create_scraper(config)
        print("  ✅ Scraper utworzony")
        return scraper
    except Exception as e:
        print(f"  ❌ Błąd utworzenia scrapera: {e}")
        return None


@with_timeout(60)  # 60 sekund na API test
def debug_api_connection(scraper):
    """Testuje połączenie API z timeoutem"""
    print("🔧 KROK 3: Test połączenia API...")

    try:
        print("  - Sprawdzanie czy API client istnieje...")
        if not hasattr(scraper, "api_client") or not scraper.api_client:
            print("  ❌ Brak API client")
            return False

        print("  ✅ API client istnieje")

        print("  - Test pobierania kadencji...")
        terms = scraper.get_available_terms()
        if terms:
            print(f"  ✅ Pobrano {len(terms)} kadencji")
        else:
            print("  ⚠️ Brak kadencji")

        return True

    except Exception as e:
        print(f"  ❌ Błąd API: {e}")
        return False


@with_timeout(120)  # 2 minuty na pobieranie posiedzeń
def debug_proceedings_fetch(scraper, term):
    """Testuje pobieranie posiedzeń z timeoutem"""
    print(f"🔧 KROK 4: Pobieranie posiedzeń kadencji {term}...")

    try:
        print("  - Wywołuję get_term_proceedings...")
        proceedings = scraper.get_term_proceedings(term)

        if not proceedings:
            print("  ❌ Nie można pobrać posiedzeń")
            return None

        print(f"  ✅ Pobrano {len(proceedings)} posiedzeń")
        print(f"  📋 Pierwsze 3 posiedzenia:")

        for i, proc in enumerate(proceedings[:3], 1):
            proc_id = proc.get("number", "?")
            dates = proc.get("dates", [])
            print(f"    {i}. Posiedzenie {proc_id} - {len(dates)} dni")

        return proceedings

    except Exception as e:
        print(f"  ❌ Błąd pobierania posiedzeń: {e}")
        return None


@with_timeout(180)  # 3 minuty na scrapowanie
def debug_scraping(scraper, term, max_proceedings):
    """Testuje scrapowanie z timeoutem"""
    print(f"🔧 KROK 5: Test scrapowania (limit: {max_proceedings} posiedzeń)...")

    try:
        print("  - Wywołuję scrape_term_statements...")
        print("  ⏳ To może potrwać do 3 minut...")

        stats = scraper.scrape_term_statements(
            term=term, max_proceedings=max_proceedings, fetch_full_statements=True
        )

        print(f"  ✅ Scrapowanie zakończone!")
        print(f"  📊 Wyniki:")
        print(f"    - Posiedzenia: {stats.get('proceedings_processed', 0)}")
        print(f"    - Wypowiedzi: {stats.get('statements_processed', 0)}")
        print(f"    - Z treścią: {stats.get('statements_with_full_content', 0)}")
        print(f"    - Błędy: {stats.get('errors', 0)}")

        return stats

    except Exception as e:
        print(f"  ❌ Błąd scrapowania: {e}")
        import traceback

        traceback.print_exc()
        return None


def debug_workflow(term, max_proceedings):
    """Główny workflow debug z krokami"""
    print("=" * 60)
    print("🐛 DEBUG WORKFLOW - znajdźmy gdzie się zawiesza")
    print("=" * 60)

    # KROK 1: Importy
    scraper = debug_scraper_creation()
    if not scraper:
        print("❌ KONIEC - nie można utworzyć scrapera")
        return False

    # KROK 2: API connection
    api_ok = debug_api_connection(scraper)
    if not api_ok:
        print("❌ KONIEC - problemy z API")
        return False

    # KROK 3: Pobieranie posiedzeń (tu może być problem)
    proceedings = debug_proceedings_fetch(scraper, term)
    if not proceedings:
        print("❌ KONIEC - nie można pobrać posiedzeń")
        return False

    # KROK 4: Scrapowanie (tu też może być problem)
    stats = debug_scraping(scraper, term, max_proceedings)
    if not stats:
        print("❌ KONIEC - błąd scrapowania")
        return False

    print("✅ DEBUG ZAKOŃCZONY - wszystko działa!")
    return True


def main():
    """Główna funkcja DEBUG"""
    parser = create_cli_parser()
    args = vars(parser.parse_args())

    try:
        setup_logging_debug()
        print_banner()

        # Test treści - szybki
        if args.get("test_content"):
            print("🧪 SZYBKI TEST TREŚCI")
            scraper = debug_scraper_creation()
            if scraper:
                results = scraper.test_content_fetching(
                    args.get("term", 10), max_tests=3
                )
                success_rate = results.get("success_rate", 0)
                print(f"Wynik testu: {success_rate:.1f}% sukcesu")
                return 0 if success_rate > 50 else 1
            return 1

        # Health check
        if args.get("health"):
            print("🏥 HEALTH CHECK")
            scraper = debug_scraper_creation()
            if scraper:
                health = scraper.health_check()
                print(f"Status: {'ZDROWY' if health.get('healthy') else 'PROBLEMY'}")
                return 0 if health.get("healthy") else 1
            return 1

        # Główny debug workflow
        term = args.get("term", 10)
        max_proceedings = args.get("max_proceedings", 1)
        timeout_seconds = args.get("timeout", 60)

        print(f"🐛 DEBUG SCRAPOWANIA")
        print(f"   Kadencja: {term}")
        print(f"   Max posiedzeń: {max_proceedings}")
        print(f"   Timeout: {timeout_seconds}s")

        success = debug_workflow(term, max_proceedings)
        return 0 if success else 1

    except KeyboardInterrupt:
        print("\n\n⛔ Proces przerwany przez użytkownika.")
        return 1
    except Exception as e:
        print(f"\n❌ Nieoczekiwany błąd: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
