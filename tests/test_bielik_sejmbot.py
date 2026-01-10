"""
Test Bielika z SejmBotem - analiza śmiesznych wypowiedzi.
"""

import sys
import logging
from pathlib import Path

# Dodaj ścieżkę do modułów SejmBot
sys.path.insert(0, str(Path(__file__).parent))

# Importuj klienta Ollama
from SejmBotDetektor.ollama_client import OllamaClient

# Setup logów
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s: %(message)s'
)


def test_basic():
    """Podstawowy test - czy Bielik działa."""
    print("🧪 TEST 1: Podstawowy test Bielika")
    print("=" * 60)

    client = OllamaClient()

    # Health check
    if not client.health_check():
        print("❌ Bielik niedostępny!")
        return False

    # Test pojedynczej wypowiedzi
    test_text = "Budżet państwa jest abstrakcyjny jak teoria kwantowa"
    print(f"\n📝 Testuję: '{test_text}'")

    result = client.is_statement_funny(test_text)

    print(f"\n🤖 Wynik analizy:")
    print(f"   Śmieszne: {'✓ TAK' if result.is_funny else '✗ NIE'}")
    print(f"   Pewność: {result.confidence:.0%}")
    print(f"   Kategoria: {result.category.value}")
    print(f"   Powód: {result.reason}")

    return result.is_funny


def test_batch():
    """Test wsadowy - analiza wielu wypowiedzi."""
    print("\n\n🧪 TEST 2: Analiza wielu wypowiedzi")
    print("=" * 60)

    client = OllamaClient()

    # Przykładowe wypowiedzi z Sejmu
    statements = [
        {
            'text': 'Budżet państwa jest abstrakcyjny jak teoria kwantowa.',
            'speaker': {'name': 'Jan Kowalski', 'club': 'PO'},
            'metadata': {'date': '2024-01-15'}
        },
        {
            'text': 'Przystępujemy do głosowania nad projektem ustawy.',
            'speaker': {'name': 'Marszałek Sejmu', 'club': None},
            'metadata': {'date': '2024-01-15'}
        },
        {
            'text': 'Panie marszałku, proponuję przerwę na kawę, bo głodny poseł to zły poseł!',
            'speaker': {'name': 'Anna Nowak', 'club': 'Lewica'},
            'metadata': {'date': '2024-01-15'}
        },
        {
            'text': 'Ta regulacja jest niespójna sama ze sobą. To tak jakby powiedzieć: '
                    'woda jest mokra ale czasem sucha.',
            'speaker': {'name': 'Piotr Testowy', 'club': 'PSL'},
            'metadata': {'date': '2024-01-16'}
        },
        {
            'text': 'Dziękuję panu ministrowi za wyczerpującą odpowiedź.',
            'speaker': {'name': 'Krzysztof Przykładowy', 'club': 'PiS'},
            'metadata': {'date': '2024-01-16'}
        }
    ]

    print(f"\n📊 Analizuję {len(statements)} wypowiedzi...\n")

    # Analiza batch z progiem 60%
    funny_statements = client.analyze_batch(statements, threshold=0.6)

    print(f"\n✅ Znaleziono {len(funny_statements)} śmiesznych wypowiedzi:\n")

    for i, stmt in enumerate(funny_statements, 1):
        analysis = stmt['ai_analysis']
        print(f"{i}. [{analysis['confidence']:.0%}] {analysis['category']}")
        print(f"   '{stmt['text'][:80]}...'")
        print(f"   Powód: {analysis['reason']}\n")

    return len(funny_statements)


def test_integration():
    """Test integracji z istniejącymi danymi SejmBot."""
    print("\n\n🧪 TEST 3: Integracja z danymi SejmBot")
    print("=" * 60)

    # Sprawdź czy istnieją dane
    data_dir = Path("data_sejm/kadencja_10")

    if not data_dir.exists():
        print("⚠️ Brak danych - uruchom najpierw scraper")
        print("   python -m SejmBotScraper.main --term 10 --max-proceedings 1")
        return False

    # Znajdź pierwszy plik z transkryptami
    transcript_files = list(data_dir.rglob("transkrypty_*.json"))

    if not transcript_files:
        print("⚠️ Brak plików transkryptów")
        return False

    print(f"✓ Znaleziono {len(transcript_files)} plików transkryptów")

    # Wczytaj pierwszy plik
    import json

    transcript_file = transcript_files[0]
    print(f"📂 Analizuję: {transcript_file.name}")

    with open(transcript_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    statements = data.get('statements', [])

    if not statements:
        print("⚠️ Brak wypowiedzi w pliku")
        return False

    print(f"✓ Wczytano {len(statements)} wypowiedzi")

    # Analizuj pierwsze 5 wypowiedzi
    print("\n🔍 Analizuję pierwsze 5 wypowiedzi...")

    client = OllamaClient()

    # Przygotuj dane w odpowiednim formacie
    formatted_statements = []
    for stmt in statements[:5]:
        formatted_statements.append({
            'text': stmt.get('text', ''),
            'speaker': stmt.get('speaker', {}),
            'metadata': data.get('metadata', {})
        })

    funny = client.analyze_batch(formatted_statements, threshold=0.65)

    print(f"\n🎉 Znaleziono {len(funny)} śmiesznych wypowiedzi!")

    for stmt in funny:
        analysis = stmt['ai_analysis']
        speaker_name = stmt.get('speaker', {}).get('name', 'Nieznany')
        print(f"\n📌 {speaker_name} [{analysis['confidence']:.0%}]")
        print(f"   {stmt['text'][:100]}...")

    return True


def main():
    """Główna funkcja testowa."""
    print("╔" + "=" * 58 + "╗")
    print("║" + " " * 10 + "🇵🇱 SEJMBOT + BIELIK - TESTY" + " " * 19 + "║")
    print("╚" + "=" * 58 + "╝\n")

    try:
        # Test 1: Podstawowy
        success1 = test_basic()

        # Test 2: Batch
        count = test_batch()

        # Test 3: Integracja (opcjonalny)
        print("\n" + "─" * 60)
        print("Czy chcesz przetestować integrację z istniejącymi danymi?")
        print("(wymaga uprzedniego uruchomienia scrapera)")
        response = input("Kontynuować? [t/N]: ").strip().lower()

        if response == 't':
            test_integration()

        # Podsumowanie
        print("\n\n" + "=" * 60)
        print("📊 PODSUMOWANIE")
        print("=" * 60)

        print(f"✓ Test podstawowy: {'PASSED' if success1 else 'FAILED'}")
        print(f"✓ Test wsadowy: {count} śmiesznych wypowiedzi znalezionych")

        # Statystyki klienta
        client = OllamaClient()
        stats = client.get_stats()

        if stats['total_analyzed'] > 0:
            print(f"\n📈 Statystyki Bielika:")
            print(f"   Przeanalizowano: {stats['total_analyzed']}")
            print(f"   Znaleziono śmiesznych: {stats['funny_found']}")
            print(f"   Wskaźnik śmieszności: {stats['funny_rate']:.1f}%")
            print(f"   Średnia pewność: {stats['avg_confidence']:.0%}")
            print(f"   Błędy: {stats['errors']}")

        print("\n✅ Wszystkie testy zakończone!")
        print("\n💡 Następne kroki:")
        print("   1. Zintegruj z SejmBotDetektor (dodaj AI jako drugi etap)")
        print("   2. Dostosuj próg pewności (threshold) dla swoich potrzeb")
        print("   3. Eksperymentuj z promptem w ollama_client.py")

    except KeyboardInterrupt:
        print("\n\n⛔ Przerwano przez użytkownika")
    except Exception as e:
        print(f"\n\n❌ Błąd: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()