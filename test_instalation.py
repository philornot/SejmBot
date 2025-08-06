#!/usr/bin/env python3
"""
Test instalacji SejmBot
Sprawdza czy wszystkie komponenty działają poprawnie
"""

import importlib
import sys
from pathlib import Path

import requests


def test_python_version():
    """Sprawdza wersję Python"""
    version = sys.version_info
    print(f"🐍 Python: {version.major}.{version.minor}.{version.micro}")

    if version.major < 3 or (version.major == 3 and version.minor < 7):
        print("❌ Wymagany Python 3.7+")
        return False
    else:
        print("✅ Wersja Python OK")
        return True


def test_required_libraries():
    """Sprawdza wymagane biblioteki"""
    required = [
        'requests',
        'bs4',  # install: `pip install beautifulsoup4`
        'lxml',
        'json',
        'pathlib',
        'logging'
    ]

    optional = [
        ('pdfplumber', 'PDF support'),
        ('docx2txt', 'DOCX support'),
        ('selenium', 'Dynamic pages support')
    ]

    print("\n📚 Sprawdzanie bibliotek:")

    all_good = True
    for lib in required:
        try:
            importlib.import_module(lib)
            print(f"✅ {lib}")
        except ImportError:
            print(f"❌ {lib} - BRAK (wymagane)")
            all_good = False

    for lib, desc in optional:
        try:
            importlib.import_module(lib)
            print(f"✅ {lib} - {desc}")
        except ImportError:
            print(f"⚠️  {lib} - BRAK ({desc})")

    return all_good


def test_internet_connection():
    """Sprawdza połączenie internetowe"""
    print("\n🌐 Sprawdzanie połączenia internetowego:")

    test_urls = [
        "https://www.sejm.gov.pl",
        "https://httpbin.org/get"
    ]

    for url in test_urls:
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                print(f"✅ {url} - OK")
            else:
                print(f"⚠️  {url} - HTTP {response.status_code}")
        except Exception as e:
            print(f"❌ {url} - Błąd: {e}")
            return False

    return True


def test_file_structure():
    """Sprawdza strukturę plików"""
    print("\n📁 Sprawdzanie struktury plików:")

    required_files = [
        'sejmbot.py',
        'scheduler.py',
        'requirements.txt',
        'setup.sh'
    ]

    required_dirs = [
        'transkrypty',
        'logs'
    ]

    all_good = True

    for file in required_files:
        if Path(file).exists():
            print(f"✅ {file}")
        else:
            print(f"❌ {file} - BRAK")
            all_good = False

    for dir_name in required_dirs:
        if Path(dir_name).is_dir():
            print(f"✅ {dir_name}/")
        else:
            print(f"❌ {dir_name}/ - BRAK")
            all_good = False

    return all_good


def test_sejmbot_import():
    """Sprawdza czy można zaimportować SejmBot"""
    print("\n🤖 Sprawdzanie importu SejmBot:")

    try:
        from sejmbot import SejmBotConfig, SejmBot
        print("✅ Import SejmBot - OK")

        # Test tworzenia konfiguracji
        config = SejmBotConfig()
        print("✅ Tworzenie konfiguracji - OK")

        # Test tworzenia bota (bez uruchamiania)
        bot = SejmBot(config)
        print("✅ Tworzenie instancji bota - OK")

        return True

    except Exception as e:
        print(f"❌ Import SejmBot - Błąd: {e}")
        return False


def test_write_permissions():
    """Sprawdza uprawnienia do zapisu"""
    print("\n📝 Sprawdzanie uprawnień do zapisu:")

    test_dirs = ['transkrypty', 'logs']

    for dir_name in test_dirs:
        try:
            test_file = Path(dir_name) / "test_write.tmp"
            test_file.write_text("test")
            test_file.unlink()
            print(f"✅ {dir_name}/ - zapis OK")
        except Exception as e:
            print(f"❌ {dir_name}/ - Błąd zapisu: {e}")
            return False

    return True


def run_mini_test():
    """Uruchamia mini-test parsowania"""
    print("\n🧪 Mini-test parsowania:")

    try:
        from sejmbot import SejmBot, SejmBotConfig

        config = SejmBotConfig()
        bot = SejmBot(config)

        # Test parsowania prostego HTML
        test_html = """
        <html>
            <body>
                <div class="content">
                    <p>Test posiedzenia Sejmu</p>
                    <p>Marszałek: Otwieram posiedzenie</p>
                </div>
            </body>
        </html>
        """

        text = bot._extract_text_from_html(test_html)
        if "Test posiedzenia" in text and "Marszałek" in text:
            print("✅ Parsing HTML - OK")
        else:
            print("⚠️  Parsing HTML - Wynik niepełny")

        # Test wzorców dat
        test_dates = [
            "15 stycznia 2025",
            "23.12.2024",
            "2025-01-15"
        ]

        dates_ok = 0
        for test_date in test_dates:
            result = bot._extract_date(test_date)
            if result:
                dates_ok += 1
                print(f"✅ Data '{test_date}' -> '{result}'")
            else:
                print(f"⚠️  Data '{test_date}' -> Nie rozpoznano")

        if dates_ok >= 2:
            print("✅ Rozpoznawanie dat - OK")
        else:
            print("⚠️  Rozpoznawanie dat - Problemy")

        return True

    except Exception as e:
        print(f"❌ Mini-test - Błąd: {e}")
        return False


def main():
    """Główna funkcja testowa"""
    print("🔧 SejmBot - Test instalacji")
    print("=" * 40)

    tests = [
        ("Wersja Python", test_python_version),
        ("Biblioteki", test_required_libraries),
        ("Połączenie internetowe", test_internet_connection),
        ("Struktura plików", test_file_structure),
        ("Import SejmBot", test_sejmbot_import),
        ("Uprawnienia zapisu", test_write_permissions),
        ("Mini-test funkcji", run_mini_test)
    ]

    results = []

    for test_name, test_func in tests:
        print(f"\n{'=' * 40}")
        print(f"Test: {test_name}")
        print("-" * 40)

        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ Błąd krytyczny w teście: {e}")
            results.append((test_name, False))

    # Podsumowanie
    print(f"\n{'=' * 40}")
    print("📊 PODSUMOWANIE TESTÓW")
    print("=" * 40)

    passed = 0
    total = len(results)

    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
        if result:
            passed += 1

    print(f"\nWynik: {passed}/{total} testów zaliczonych")

    if passed == total:
        print("\n🎉 Wszystkie testy przeszły! SejmBot gotowy do pracy.")
        return 0
    elif passed >= total * 0.8:
        print("\n⚠️  Większość testów przeszła. SejmBot powinien działać.")
        return 0
    else:
        print("\n❌ Zbyt wiele błędów. Sprawdź instalację.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
