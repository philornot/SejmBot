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
from typing import Optional

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

    # Production-oriented options
    parser.add_argument("--bulk", action="store_true", help="Production: scrape a whole term (bulk)")
    parser.add_argument(
        "--output-dir",
        type=str,
        help="Zastąp katalog wyjściowy dla zebranych danych",
    )
    parser.add_argument(
        "--fetch-full-statements",
        action="store_true",
        help="Upewnij się, że pobierana jest pełna treść wyciągu",
    )
    parser.add_argument(
        "--concurrent-downloads",
        type=int,
        default=3,
        help="Liczba jednoczesnych pobrań w trybie masowym",
    )
    parser.add_argument(
        "--ignore-venv",
        action="store_true",
        help="Zignoruj sprawdzenie aktywnego virtualenv",
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


def setup_production_logging(settings=None, log_file: Optional[str] = None):
    """Konfiguracja logowania dla produkcji (używa core.setup_logging gdy dostępne)."""
    try:
        from SejmBotScraper.core import setup_logging

        level = logging.INFO
        if settings:
            try:
                lv = settings.get('logging.level')
                level = getattr(logging, lv.value) if hasattr(lv, 'value') else getattr(logging, str(lv).upper(), logging.INFO)
            except Exception:
                level = logging.INFO

        setup_logging(level=level, log_file=log_file)
    except Exception:
        # Fallback
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')


def check_dependencies() -> bool:
    """Szybkie sprawdzenie wymaganych pakietów środowiska.

    Zwraca True gdy wymagane pakiety są dostępne. W przeciwnym wypadku
    wypisuje instrukcję instalacji i zwraca False.
    """
    missing = []
    try:
        # Bezpieczne użycie importlib.util
        from importlib import util as importlib_util

        for pkg in ('requests', 'schedule'):
            if importlib_util.find_spec(pkg) is None:
                missing.append(pkg)
    except Exception:
        # Jeśli importlib.util nie jest dostępny, pomiń sprawdzenie
        pass

    if missing:
        print("❌ Brakuje wymaganych pakietów:", ", ".join(missing))
        print("Zainstaluj je uruchamiając:")
        print("  python -m pip install -r SejmBotScraper/requirements.txt")
        return False

    return True


def check_venv_active() -> bool:
    r"""Sprawdza czy virtualenv jest aktywny.

    Dla PowerShell (Windows) zwykle trzeba uruchomić:
      .\.venv\Scripts\activate

    Zwraca True jeśli wirtualne środowisko wygląda na aktywne, False w przeciwnym wypadku.
    """

    # Jeśli sys.prefix różni się od systemowego, najpewniej venv jest aktywny
    try:
        import sys as _sys

        base_prefix = getattr(_sys, 'base_prefix', None) or getattr(_sys, 'real_prefix', None)
        prefix = getattr(_sys, 'prefix', None)
        if prefix and base_prefix and prefix != base_prefix:
            return True

        # Dodatkowo sprawdź standardowe location .venv/Scripts/Activate.ps1
        venv_marker = Path('.venv') / 'Scripts' / 'Activate.ps1'
        if venv_marker.exists() and ('.venv' in Path(_sys.executable).as_posix()):
            return True

        return False
    except Exception:
        return False


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
        # If running in debug mode, keep verbose logging and debug workflow
        if args.get("debug"):
            setup_logging_debug()
        else:
            # Try to setup production logging (may use settings)
            try:
                from SejmBotScraper.config.settings import get_settings

                settings = get_settings()
            except Exception:
                settings = None

            setup_production_logging(settings=settings)

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

        # Production bulk workflow
        if args.get("bulk"):
            # Run production scraper for a term (bulk)
            term = args.get("term", 10)
            output_dir = args.get("output_dir")
            fetch_full = args.get("fetch_full_statements", False)
            concurrent = args.get("concurrent_downloads", 3)

            # Sprawdź aktywność venv (chyba że użytkownik wymusi ignorowanie)
            if not args.get('ignore_venv') and not check_venv_active():
                print("⚠️ Wygląda na to, że virtualenv nie jest aktywny.")
                print("W PowerShell uruchom:")
                print("  & .\\.venv\\Scripts\\Activate.ps1")
                print("Lub uruchom z --ignore-venv jeśli wiesz co robisz.")
                return 1

            print(f"🚀 TRYB PRODUKCYJNY (bulk) — kadencja={term} katalog_wyj={output_dir}")

            try:
                from SejmBotScraper.core import create_scraper
                from SejmBotScraper.config.settings import get_settings

                settings = get_settings()
                config_override = {}
                if output_dir:
                    config_override.setdefault('storage', {})
                    config_override['storage']['base_directory'] = output_dir
                config_override.setdefault('scraping', {})
                config_override['scraping']['fetch_full_statements'] = fetch_full
                config_override['scraping']['concurrent_downloads'] = concurrent

                scraper = create_scraper(settings.to_dict() if hasattr(settings, 'to_dict') else None, config_override=config_override)

                stats = scraper.scrape_term_statements(term=term, max_proceedings=args.get('max_proceedings', 5), fetch_full_statements=fetch_full)

                print("📈 Production scrape finished")
                print(f"  - proceedings: {stats.get('proceedings_processed', 0)}")
                print(f"  - statements: {stats.get('statements_processed', 0)}")
                print(f"  - with_content: {stats.get('statements_with_full_content', 0)}")
                print(f"  - errors: {stats.get('errors', 0)}")

                return 0 if stats.get('errors', 0) == 0 else 2

            except Exception as e:
                logger.exception("Production bulk failed")
                print(f"❌ Production bulk failed: {e}")
                return 1

        # Otherwise run debug workflow
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
