#!/usr/bin/env python3
"""
Test script dla naprawionego scrapera
Sprawdza czy pobieranie treści wypowiedzi działa poprawnie
"""

import logging
import sys
from datetime import datetime, date

# Konfiguracja logowania
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

logger = logging.getLogger(__name__)


def test_api_client():
    """Test naprawionego API clienta"""
    print("\n" + "=" * 50)
    print("TEST 1: NAPRAWIONY API CLIENT")
    print("=" * 50)

    try:
        # Import naprawionego klienta
        from SejmBotScraper.api.sejm_client import SejmAPIClient

        # Utwórz klienta
        client = SejmAPIClient()

        # Test połączenia
        print("1. Test połączenia z API...")
        test_result = client.test_connection()

        print(f"   Wynik: {test_result['total_score']}/5 testów")
        if test_result.get('errors'):
            for error in test_result['errors']:
                print(f"   Błąd: {error}")

        if test_result['total_score'] >= 3:
            print("✅ API client działa poprawnie")
            return client
        else:
            print("❌ API client ma problemy")
            return None

    except Exception as e:
        print(f"❌ Błąd inicjalizacji API clienta: {e}")
        return None


def test_content_fetching(client):
    """Test pobierania treści wypowiedzi"""
    print("\n" + "=" * 50)
    print("TEST 2: POBIERANIE TREŚCI WYPOWIEDZI")
    print("=" * 50)

    try:
        term = 10

        # Pobierz listę posiedzeń
        print(f"1. Pobieranie listy posiedzeń kadencji {term}...")
        proceedings = client.get_proceedings(term)

        if not proceedings:
            print("❌ Nie można pobrać posiedzeń")
            return False

        print(f"✅ Znaleziono {len(proceedings)} posiedzeń")

        # Znajdź posiedzenie z przeszłości
        today = date.today()
        test_proceeding = None
        test_date = None

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
            print("❌ Nie znaleziono posiedzenia z przeszłości")
            return False

        proc_id = test_proceeding.get('number')
        print(f"2. Testowanie posiedzenia {proc_id} z dnia {test_date}")

        # Pobierz listę wypowiedzi
        print("3. Pobieranie listy wypowiedzi...")
        statements_data = client.get_transcripts_list(term, proc_id, test_date)

        if not statements_data or not statements_data.get('statements'):
            print("❌ Nie można pobrać wypowiedzi")
            return False

        statements = statements_data['statements']
        print(f"✅ Znaleziono {len(statements)} wypowiedzi")

        # Test pobierania treści pierwszych 3 wypowiedzi
        print("4. Test pobierania treści (pierwsze 3 wypowiedzi):")
        successful_fetches = 0

        for i, stmt in enumerate(statements[:3], 1):
            stmt_num = stmt.get('num')
            speaker = stmt.get('name', 'Nieznany')

            print(f"   [{i}/3] Wypowiedź {stmt_num} - {speaker}")

            if stmt_num is not None:
                # Test HTML
                html_content = client.get_statement_html(term, proc_id, test_date, stmt_num)

                if html_content and len(html_content.strip()) > 50:
                    print(f"       ✅ HTML: {len(html_content)} znaków")

                    # Test czystego tekstu
                    clean_text = client.get_statement_full_text(term, proc_id, test_date, stmt_num)

                    if clean_text and len(clean_text.strip()) > 20:
                        print(f"       ✅ Tekst: {len(clean_text)} znaków")
                        preview = clean_text[:80].replace('\n', ' ')
                        print(f"       📝 Podgląd: {preview}...")
                        successful_fetches += 1
                    else:
                        print("       ⚠️ Problem z czyszczeniem tekstu")
                else:
                    print("       ❌ Nie można pobrać HTML")
            else:
                print("       ❌ Brak numeru wypowiedzi")

        success_rate = (successful_fetches / 3) * 100
        print(f"\n📊 Wyniki: {successful_fetches}/3 udane ({success_rate:.0f}%)")

        if successful_fetches >= 2:
            print("✅ Test pobierania treści PRZESZEDŁ")
            return True
        else:
            print("❌ Test pobierania treści NIE PRZESZEDŁ")
            return False

    except Exception as e:
        print(f"❌ Błąd testu: {e}")
        return False


def test_scraper_implementation(client):
    """Test implementacji scrapera"""
    print("\n" + "=" * 50)
    print("TEST 3: IMPLEMENTACJA SCRAPERA")
    print("=" * 50)

    try:
        # Import naprawionego scrapera
        from SejmBotScraper.scraping.implementations.scraper import SejmScraper

        # Utwórz scraper z ograniczeniami testowymi
        config = {
            'max_proceedings': 1,  # Tylko 1 posiedzenie
            'max_dates_per_proceeding': 1,  # Tylko 1 dzień
            'max_statements_per_day': 5  # Tylko 5 wypowiedzi
        }

        scraper = SejmScraper(api_client=client, config=config)

        print("1. Test scrapowania z ograniczeniami...")

        # Uruchom scraper
        stats = scraper.scrape_term(
            term=10,
            fetch_full_statements=True,
            max_proceedings=1,
            max_dates_per_proceeding=1,
            max_statements_per_day=5
        )

        print(f"2. Wyniki scrapowania:")
        print(f"   Posiedzenia: {stats.get('proceedings_processed', 0)}")
        print(f"   Wypowiedzi: {stats.get('statements_processed', 0)}")
        print(f"   Z treścią: {stats.get('statements_with_full_content', 0)}")
        print(f"   Błędy: {stats.get('errors', 0)}")

        # Współczynnik sukcesu
        attempts = stats.get('content_fetch_attempts', 0)
        successes = stats.get('content_fetch_successes', 0)
        if attempts > 0:
            success_rate = (successes / attempts) * 100
            print(f"   Sukces pobierania: {success_rate:.1f}%")

        # Sprawdź czy test przeszedł
        if stats.get('statements_with_full_content', 0) > 0:
            print("✅ Test implementacji scrapera PRZESZEDŁ")
            return True
        else:
            print("❌ Test implementacji scrapera NIE PRZESZEDŁ")
            return False

    except Exception as e:
        print(f"❌ Błąd testu: {e}")
        return False


if __name__ == "__main__":
    api_client = test_api_client()

    if api_client:
        # Przejdź do kolejnego testu tylko jeśli klient API działa
        content_fetching_passed = test_content_fetching(api_client)

        if content_fetching_passed:
            # Uruchom test scrapera, jeśli poprzedni test się powiódł
            test_scraper_implementation(api_client)

    print("\n" + "=" * 50)
    print("KONIEC TESTÓW")
    print("=" * 50)
