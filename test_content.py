#!/usr/bin/env python3
"""
Skrypt testowy - weryfikuje czy naprawione pobieranie treści wypowiedzi działa
"""

import logging
import sys
from datetime import datetime, date
from pathlib import Path

# Konfiguracja logowania
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_content_fetching():
    """Test pobierania treści wypowiedzi"""
    print("🧪 TEST POBIERANIA TREŚCI WYPOWIEDZI")
    print("=" * 50)

    try:
        # Import naprawionych komponentów
        from SejmBotScraper.api.sejm_client import SejmAPIClient
        from SejmBotScraper.cache.manager import CacheInterface

        print("✓ Zaimportowano naprawione komponenty")

        # Inicjalizacja
        print("\n1. Inicjalizacja...")
        cache = CacheInterface()
        api_client = SejmAPIClient(cache)

        # Test połączenia
        print("\n2. Test połączenia z API...")
        connection_test = api_client.test_connection()
        print(f"   Wynik testu: {connection_test['total_score']}/4 testów przeszło")

        if connection_test['total_score'] < 2:
            print("❌ API nie działa poprawnie - przerywam test")
            return False

        # Znajdź odpowiednie posiedzenie do testowania
        print("\n3. Wyszukiwanie posiedzenia do testowania...")
        proceedings = api_client.get_proceedings(10)

        if not proceedings:
            print("❌ Nie można pobrać listy posiedzeń")
            return False

        print(f"   Znaleziono {len(proceedings)} posiedzeń")

        # Znajdź posiedzenie z przeszłości
        test_proceeding = None
        test_date = None
        today = date.today()

        for proc in proceedings:
            if proc.get('dates') and proc.get('number', 0) > 0:
                for proc_date in proc['dates']:
                    try:
                        if datetime.strptime(proc_date, '%Y-%m-%d').date() < today:
                            test_proceeding = proc
                            test_date = proc_date
                            break
                    except:
                        continue
                if test_proceeding:
                    break

        if not test_proceeding:
            print("❌ Nie znaleziono odpowiedniego posiedzenia do testowania")
            return False

        proc_id = test_proceeding.get('number')
        print(f"   Wybrano posiedzenie {proc_id}, dzień {test_date}")

        # Test pobierania listy wypowiedzi
        print("\n4. Test pobierania listy wypowiedzi...")
        statements_data = api_client.get_transcripts_list(10, proc_id, test_date)

        if not statements_data or not statements_data.get('statements'):
            print("❌ Nie można pobrać listy wypowiedzi")
            return False

        statements = statements_data['statements']
        print(f"   Znaleziono {len(statements)} wypowiedzi")

        # Test pobierania treści wypowiedzi
        print("\n5. Test pobierania treści wypowiedzi...")
        success_count = 0
        test_count = min(5, len(statements))  # Testuj maksymalnie 5 wypowiedzi

        for i in range(test_count):
            stmt = statements[i]
            stmt_num = stmt.get('num')
            speaker = stmt.get('name', 'Nieznany')

            if not stmt_num:
                print(f"      Wypowiedź {i + 1}: Brak numeru - pomijam")
                continue

            print(f"      Wypowiedź {i + 1}/{test_count}: {speaker} (nr {stmt_num})")

            # Test HTML
            html_content = api_client.get_statement_html(10, proc_id, test_date, stmt_num)

            if html_content and len(html_content.strip()) > 50:
                # Test czyszczenia do tekstu
                clean_text = api_client._clean_html_to_text(html_content)

                if clean_text and len(clean_text.strip()) > 30:
                    success_count += 1
                    preview = clean_text[:100].replace('\n', ' ')
                    print(f"        ✓ Pobrano treść: {len(clean_text)} znaków")
                    print(f"        Preview: {preview}...")
                else:
                    print(f"        ⚠ HTML pobrane ({len(html_content)} zn.) ale po czyszczeniu za mało treści")
            else:
                print(f"        ❌ Nie pobrano treści HTML")

            # Test pełnego tekstu
            full_text = api_client.get_statement_full_text(10, proc_id, test_date, stmt_num)
            if full_text and len(full_text.strip()) > 30:
                print(f"        ✓ Metoda pełnego tekstu: {len(full_text)} znaków")

        print(f"\n📊 WYNIKI TESTÓW:")
        print(f"   Testowane wypowiedzi: {test_count}")
        print(f"   Udane pobierania: {success_count}")
        print(f"   Wskaźnik sukcesu: {(success_count / test_count) * 100:.1f}%")

        if success_count > 0:
            print("✅ TEST PRZESZEDŁ - pobieranie treści działa!")

            # Test integracji z scraperem
            print("\n6. Test integracji z scraperem...")

            try:
                from SejmBotScraper.scraping.implementations.scraper import SejmScraper

                scraper = SejmScraper(api_client=api_client, cache_manager=cache)

                # Test przetwarzania jednego dnia
                print(f"   Testowanie scrapera dla {test_date}...")

                result = scraper.scrape_proceeding_date(10, proc_id, test_date, fetch_full_statements=True)

                if result:
                    stats = scraper.stats
                    print(f"   ✓ Scraper przetworył {stats.get('statements_processed', 0)} wypowiedzi")
                    print(f"   ✓ Z treścią: {stats.get('statements_with_full_content', 0)}")
                    print(f"   ✓ Próby pobierania: {stats.get('content_fetch_attempts', 0)}")
                    print(f"   ✓ Udane pobierania: {stats.get('content_fetch_successes', 0)}")

                    if stats.get('statements_with_full_content', 0) > 0:
                        print("✅ INTEGRACJA Z SCRAPEREM DZIAŁA!")
                    else:
                        print("⚠ Scraper nie pobrał treści wypowiedzi")

                else:
                    print("❌ Scraper nie przetworzył danych")

            except Exception as e:
                print(f"❌ Błąd testowania scrapera: {e}")

            return True
        else:
            print("❌ TEST NIEUDANY - nie udało się pobrać żadnej treści")
            return False

    except ImportError as e:
        print(f"❌ Błąd importu: {e}")
        print("Upewnij się, że jesteś w odpowiednim katalogu i masz zainstalowane zależności")
        return False
    except Exception as e:
        print(f"❌ Nieoczekiwany błąd: {e}")
        return False


def test_specific_statement():
    """Test konkretnej wypowiedzi dla debugowania"""
    print("\n🔍 TEST KONKRETNEJ WYPOWIEDZI")
    print("=" * 50)

    try:
        from SejmBotScraper.api.sejm_client import SejmAPIClient

        # Parametry testowe - można dostosować
        term = 10
        proceeding = 1  # Pierwsze posiedzenie
        date = "2023-11-14"  # Data z logów
        statement_num = 1  # Pierwsza wypowiedź

        print(f"Testowanie wypowiedzi:")
        print(f"  Kadencja: {term}")
        print(f"  Posiedzenie: {proceeding}")
        print(f"  Data: {date}")
        print(f"  Numer wypowiedzi: {statement_num}")

        api_client = SejmAPIClient()

        # Test każdej metody osobno
        print(f"\n1. Test get_transcripts_list...")
        statements_data = api_client.get_transcripts_list(term, proceeding, date)

        if statements_data and statements_data.get('statements'):
            statements = statements_data['statements']
            print(f"   ✓ Pobrano {len(statements)} wypowiedzi")

            # Znajdź wypowiedź o podanym numerze
            target_statement = None
            for stmt in statements:
                if stmt.get('num') == statement_num:
                    target_statement = stmt
                    break

            if target_statement:
                print(f"   ✓ Znaleziono wypowiedź {statement_num}")
                print(f"   Mówca: {target_statement.get('name', 'Nieznany')}")
                print(f"   Funkcja: {target_statement.get('function', 'Brak')}")
            else:
                print(f"   ❌ Nie znaleziono wypowiedzi o numerze {statement_num}")
                if statements:
                    available = [s.get('num') for s in statements[:5]]
                    print(f"   Dostępne numery (pierwsze 5): {available}")
                return False
        else:
            print("   ❌ Nie pobrano listy wypowiedzi")
            return False

        print(f"\n2. Test get_statement_html...")
        html_content = api_client.get_statement_html(term, proceeding, date, statement_num)

        if html_content:
            print(f"   ✓ Pobrano HTML: {len(html_content)} znaków")

            # Pokaż fragment
            preview = html_content[:300].replace('\n', ' ').replace('\r', ' ')
            print(f"   Fragment HTML: {preview}...")

            # Test czyszczenia
            print(f"\n3. Test czyszczenia HTML...")
            clean_text = api_client._clean_html_to_text(html_content)

            if clean_text:
                print(f"   ✓ Po oczyszczeniu: {len(clean_text)} znaków")

                clean_preview = clean_text[:200].replace('\n', ' ')
                print(f"   Czysty tekst: {clean_preview}...")

                if len(clean_text.strip()) > 50:
                    print("✅ POBIERANIE TREŚCI DZIAŁA POPRAWNIE!")
                    return True
                else:
                    print("⚠ Treść za krótka po oczyszczeniu")
            else:
                print("❌ Czyszczenie HTML nie powiodło się")
        else:
            print("❌ Nie pobrano HTML")

        print(f"\n4. Test get_statement_full_text...")
        full_text = api_client.get_statement_full_text(term, proceeding, date, statement_num)

        if full_text:
            print(f"   ✓ Metoda pełnego tekstu: {len(full_text)} znaków")
            text_preview = full_text[:200].replace('\n', ' ')
            print(f"   Tekst: {text_preview}...")
            return True
        else:
            print("❌ Metoda pełnego tekstu nieudana")

        return False

    except Exception as e:
        print(f"❌ Błąd testu: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Główna funkcja testowa"""
    print("🚀 TESTY NAPRAWIONEGO POBIERANIA TREŚCI WYPOWIEDZI")
    print("=" * 60)

    # Sprawdź czy jesteśmy w odpowiednim katalogu
    if not Path("SejmBotScraper").exists():
        print("❌ Nie znaleziono katalogu SejmBotScraper")
        print("Upewnij się, że uruchamiasz skrypt z głównego katalogu projektu")
        return 1

    # Test ogólny
    print("\n" + "=" * 60)
    general_success = test_content_fetching()

    # Test konkretnej wypowiedzi
    print("\n" + "=" * 60)
    specific_success = test_specific_statement()

    # Podsumowanie
    print("\n" + "=" * 60)
    print("📋 PODSUMOWANIE TESTÓW:")
    print(f"   Test ogólny: {'✅ PRZESZEDŁ' if general_success else '❌ NIEUDANY'}")
    print(f"   Test konkretny: {'✅ PRZESZEDŁ' if specific_success else '❌ NIEUDANY'}")

    if general_success or specific_success:
        print("\n🎉 NAPRAWKI DZIAŁAJĄ! Pobieranie treści wypowiedzi zostało naprawione.")
        print("\nMożesz teraz uruchomić główny scraper:")
        print("  python SejmBotScraper/main.py")
        return 0
    else:
        print("\n❌ TESTY NIEUDANE. Sprawdź:")
        print("  1. Połączenie internetowe")
        print("  2. Dostępność API Sejmu")
        print("  3. Poprawność implementacji")
        return 1


if __name__ == "__main__":
    sys.exit(main())
