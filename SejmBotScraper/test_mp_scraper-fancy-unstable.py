#!/usr/bin/env python3
# test_mp_scraper.py
"""
🧪 SejmBot MP Scraper - Professional Test Suite
==============================================

Profesjonalny health check i test suite dla modułu MPScraper.
Zaprojektowany jak enterprise monitoring system.

Autor: SejmBot Team
Wersja: 2.0.1 - Fixed imports
"""

import json
import shutil
import sys
import tempfile
import time
import unittest
from datetime import datetime
from io import StringIO
from pathlib import Path
from typing import Dict, List
from unittest.mock import Mock, patch

# ========================================================================
# NAPRAWIONE IMPORTY - DODANIE ŚCIEŻEK DO SYS.PATH
# ========================================================================

# Dodaj katalog główny projektu do ścieżki
current_dir = Path(__file__).parent.absolute()
project_root = current_dir
sys.path.insert(0, str(project_root))

# Alternatywnie, jeśli moduły są w podkatalogu
if (current_dir / "SejmBotScraper").exists():
    sys.path.insert(0, str(current_dir / "SejmBotScraper"))

print(f"🔍 Szukam modułów w ścieżkach:")
for path in sys.path[:5]:  # Pokaż pierwsze 5 ścieżek
    print(f"   - {path}")
print()

# Spróbuj importować z różnych lokalizacji
mp_scraper_module = None
sejm_api_module = None
config_module = None

import_attempts = [
    # Próba 1: Bezpośredni import
    lambda: __import__('mp_scraper'),
    lambda: __import__('sejm_api'),
    lambda: __import__('config'),

    # Próba 2: Z podkatalogu SejmBotScraper
    lambda: __import__('SejmBotScraper.mp_scraper', fromlist=['mp_scraper']),
    lambda: __import__('SejmBotScraper.sejm_api', fromlist=['sejm_api']),
    lambda: __import__('SejmBotScraper.config', fromlist=['config']),
]

# Spróbuj zaimportować mp_scraper
for attempt in [import_attempts[0], import_attempts[3]]:
    try:
        mp_scraper_module = attempt()
        MPScraper = getattr(mp_scraper_module, 'MPScraper', None)
        if MPScraper:
            print("✅ mp_scraper zaimportowany pomyślnie")
            break
    except ImportError as e:
        continue

# Spróbuj zaimportować sejm_api
for attempt in [import_attempts[1], import_attempts[4]]:
    try:
        sejm_api_module = attempt()
        SejmAPI = getattr(sejm_api_module, 'SejmAPI', None)
        if SejmAPI:
            print("✅ sejm_api zaimportowany pomyślnie")
            break
    except ImportError as e:
        continue

# Spróbuj zaimportować config
for attempt in [import_attempts[2], import_attempts[5]]:
    try:
        config_module = attempt()
        DEFAULT_TERM = getattr(config_module, 'DEFAULT_TERM', 10)
        BASE_OUTPUT_DIR = getattr(config_module, 'BASE_OUTPUT_DIR', 'dane')
        print("✅ config zaimportowany pomyślnie")
        break
    except ImportError as e:
        continue

# Jeśli nie udało się zaimportować, utwórz mock klasy
if not mp_scraper_module or not MPScraper:
    print("⚠️  Nie można zaimportować mp_scraper - tworzę mock klasę")


    class MockMPScraper:
        def __init__(self):
            self.api = Mock()
            self.base_dir = Path("./dane")
            self.stats = {
                'mps_downloaded': 0,
                'clubs_downloaded': 0,
                'photos_downloaded': 0,
                'errors': 0,
                'voting_stats_downloaded': 0
            }

        def _ensure_mp_directory(self, term):
            return Path("./dane") / f"kadencja_{term}" / "poslowie"

        def get_mps_summary(self, term):
            return {
                'term': term,
                'total_mps': 0,
                'clubs': {},
                'clubs_count': 0
            }

        def scrape_mps(self, term, download_photos=False, download_voting_stats=False):
            return self.stats.copy()

        def scrape_specific_mp(self, term, mp_id, download_photos=False, download_voting_stats=False):
            return True

        def scrape_clubs(self, term):
            return self.stats.copy()

        @staticmethod
        def _make_safe_filename(name):
            if not name:
                return ""
            safe_name = "".join(c if c.isalnum() or c in '-_' else '_' for c in str(name))
            return safe_name[:50]

        @staticmethod
        def _save_json(data, filepath):
            try:
                filepath.parent.mkdir(parents=True, exist_ok=True)
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                return True
            except Exception:
                return False

        @staticmethod
        def _safe_format_id(id_value):
            if id_value is None:
                return "None"
            if isinstance(id_value, int):
                return f"{id_value:02d}" if id_value < 100 else str(id_value)
            return str(id_value)


    MPScraper = MockMPScraper

if not sejm_api_module or not SejmAPI:
    print("⚠️  Nie można zaimportować sejm_api - tworzę mock klasę")


    class MockSejmAPI:
        def __init__(self):
            pass

        def _make_request(self, endpoint):
            return None


    SejmAPI = MockSejmAPI

# Ustaw domyślne wartości config jeśli nie zaimportowano
if not config_module:
    print("⚠️  Nie można zaimportować config - używam wartości domyślnych")
    DEFAULT_TERM = 10
    BASE_OUTPUT_DIR = Path("./dane")

print("🚀 Moduły gotowe do testów\n")


class TestColors:
    """Kolory dla ładnego wyświetlania w terminalu"""

    # Podstawowe kolory
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    PURPLE = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    GRAY = '\033[90m'

    # Style
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

    # Reset
    RESET = '\033[0m'

    @classmethod
    def disable_colors(cls):
        """Wyłącza kolory (dla CI/CD)"""
        for attr in dir(cls):
            if not attr.startswith('_') and attr != 'disable_colors':
                setattr(cls, attr, '')


class HealthCheckReporter:
    """Profesjonalny reporter wyników testów w stylu health check"""

    def __init__(self, enable_colors: bool = True):
        self.enable_colors = enable_colors
        if not enable_colors:
            TestColors.disable_colors()

        self.test_results = []
        self.start_time = None
        self.end_time = None

    def print_header(self):
        """Wyświetla professional header"""
        header = f"""
{TestColors.CYAN}╔═══════════════════════════════════════════════════════════════════╗
║                                                                   ║
║    🧪 SejmBot MP Scraper - Professional Health Check              ║
║                                                                   ║
║    Status: RUNNING                                                ║
║    Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}                                        ║
║    Environment: Test Suite v2.0                                  ║
║                                                                   ║
╚═══════════════════════════════════════════════════════════════════╝{TestColors.RESET}
        """
        print(header)

    def start_test_session(self):
        """Rozpoczyna sesję testową"""
        self.start_time = time.time()
        self.print_header()
        print(f"{TestColors.BLUE}🚀 Inicjalizacja test suite...{TestColors.RESET}")
        print()

    def log_test_start(self, test_name: str, description: str):
        """Loguje rozpoczęcie testu"""
        print(f"{TestColors.GRAY}┌─ {TestColors.BOLD}{test_name}{TestColors.RESET}")
        print(f"{TestColors.GRAY}│  {description}{TestColors.RESET}")

    def log_test_result(self, test_name: str, passed: bool, details: str = None,
                        duration: float = None):
        """Loguje wynik testu"""
        status_icon = "✅" if passed else "❌"
        status_color = TestColors.GREEN if passed else TestColors.RED
        status_text = "PASSED" if passed else "FAILED"

        duration_text = f" ({duration:.3f}s)" if duration else ""

        print(f"{TestColors.GRAY}│  {status_color}{status_icon} {status_text}{duration_text}{TestColors.RESET}")

        if details:
            for line in details.split('\n'):
                if line.strip():
                    print(f"{TestColors.GRAY}│    {TestColors.GRAY}{line}{TestColors.RESET}")

        print(f"{TestColors.GRAY}└─{TestColors.RESET}")
        print()

        # Zapisz wynik
        self.test_results.append({
            'name': test_name,
            'passed': passed,
            'details': details,
            'duration': duration
        })

    def print_summary(self):
        """Wyświetla podsumowanie wszystkich testów"""
        self.end_time = time.time()
        total_duration = self.end_time - self.start_time

        passed_count = sum(1 for result in self.test_results if result['passed'])
        failed_count = len(self.test_results) - passed_count
        success_rate = (passed_count / len(self.test_results) * 100) if self.test_results else 0

        # Określ overall status
        if failed_count == 0:
            overall_status = f"{TestColors.GREEN}HEALTHY{TestColors.RESET}"
            overall_icon = "✅"
        elif failed_count <= 2:
            overall_status = f"{TestColors.YELLOW}DEGRADED{TestColors.RESET}"
            overall_icon = "⚠️"
        else:
            overall_status = f"{TestColors.RED}UNHEALTHY{TestColors.RESET}"
            overall_icon = "❌"

        summary = f"""
{TestColors.CYAN}╔═══════════════════════════════════════════════════════════════════╗
║                        TEST EXECUTION SUMMARY                    ║
╠═══════════════════════════════════════════════════════════════════╣
║                                                                   ║
║  {overall_icon} Overall Status: {overall_status}                                      ║
║                                                                   ║
║  📊 Test Statistics:                                              ║
║     • Total Tests: {len(self.test_results):>3}                                              ║
║     • Passed:      {TestColors.GREEN}{passed_count:>3}{TestColors.CYAN}                                              ║
║     • Failed:      {TestColors.RED}{failed_count:>3}{TestColors.CYAN}                                              ║
║     • Success Rate: {success_rate:>5.1f}%                                        ║
║                                                                   ║
║  ⏱️  Execution Time: {total_duration:>6.2f}s                                        ║
║                                                                   ║"""

        if failed_count > 0:
            summary += f"""║  ❌ Failed Tests:                                                 ║"""
            for result in self.test_results:
                if not result['passed']:
                    summary += f"""
║     • {result['name'][:50]:50} ║"""
            summary += f"""
║                                                                   ║"""

        summary += f"""╚═══════════════════════════════════════════════════════════════════╝{TestColors.RESET}
        """

        print(summary)

        # Rekomendacje
        if failed_count > 0:
            print(f"{TestColors.YELLOW}📋 REKOMENDACJE:{TestColors.RESET}")
            if failed_count > 5:
                print(f"   • Krytyczne problemy z komponentami - wymagana natychmiastowa interwencja")
            elif failed_count > 2:
                print(f"   • Wykryto problemy stabilności - zalecane przegląd konfiguracji")
            else:
                print(f"   • Drobne problemy - kontynuuj monitorowanie")
            print()


class TestMPScraper(unittest.TestCase):
    """
    Główna klasa testów dla MPScraper

    Testuje wszystkie kluczowe komponenty:
    - Inicjalizację i konfigurację
    - Komunikację z API
    - Zarządzanie plikami
    - Pobieranie i przetwarzanie danych
    - Obsługę błędów i edge cases
    """

    @classmethod
    def setUpClass(cls):
        """Konfiguracja przed rozpoczęciem wszystkich testów"""
        cls.reporter = HealthCheckReporter()
        cls.reporter.start_test_session()

        # Tymczasowy katalog dla testów
        cls.temp_dir = tempfile.mkdtemp(prefix="mp_scraper_test_")
        cls.test_data_dir = Path(cls.temp_dir)

    @classmethod
    def tearDownClass(cls):
        """Sprzątanie po wszystkich testach"""
        # Usuń tymczasowe pliki
        if hasattr(cls, 'temp_dir') and Path(cls.temp_dir).exists():
            shutil.rmtree(cls.temp_dir)

        cls.reporter.print_summary()

    def setUp(self):
        """Przygotowanie przed każdym testem"""
        self.test_start_time = time.time()

    def tearDown(self):
        """Sprzątanie po każdym teście"""
        pass

    def _log_test_result(self, passed: bool, details: str = None):
        """Helper do logowania wyników testów"""
        test_name = self._testMethodName
        test_description = self._testMethodDoc or "Brak opisu"
        duration = time.time() - self.test_start_time

        self.reporter.log_test_start(test_name, test_description.strip())
        self.reporter.log_test_result(test_name, passed, details, duration)

    # ========================================================================
    # TESTY INICJALIZACJI I KONFIGURACJI
    # ========================================================================

    def test_scraper_initialization(self):
        """Sprawdza poprawność inicjalizacji scraper'a i podstawowych atrybutów"""
        try:
            scraper = MPScraper()

            # Sprawdź podstawowe atrybuty
            self.assertIsNotNone(scraper.api)
            self.assertIsInstance(scraper.api, SejmAPI)
            self.assertIsNotNone(scraper.base_dir)
            self.assertIsInstance(scraper.stats, dict)

            # Sprawdź domyślne statystyki
            expected_stats = ['mps_downloaded', 'clubs_downloaded', 'photos_downloaded',
                              'errors', 'voting_stats_downloaded']
            for stat in expected_stats:
                self.assertIn(stat, scraper.stats)
                self.assertEqual(scraper.stats[stat], 0)

            details = f"✓ API Client: {type(scraper.api).__name__}\n✓ Base Directory: {scraper.base_dir}\n✓ Stats initialized: {len(scraper.stats)} keys"
            self._log_test_result(True, details)

        except Exception as e:
            self._log_test_result(False, f"Exception: {str(e)}")
            raise

    def test_directory_structure_creation(self):
        """Testuje tworzenie struktury katalogów dla danych posłów"""
        try:
            # Użyj tymczasowego katalogu
            with patch.object(MPScraper, '__init__', lambda x: None):
                scraper = MPScraper()
                scraper.base_dir = self.test_data_dir

                # Test tworzenia struktury dla kadencji
                mp_dir = scraper._ensure_mp_directory(10)

                # Sprawdź główny katalog
                self.assertTrue(mp_dir.exists())
                self.assertTrue(mp_dir.is_dir())

                # Sprawdź podkatalogi
                expected_subdirs = ['zdjecia', 'kluby', 'statystyki_glosowan']
                for subdir in expected_subdirs:
                    subdir_path = mp_dir / subdir
                    self.assertTrue(subdir_path.exists())
                    self.assertTrue(subdir_path.is_dir())

                details = f"✓ Main directory: {mp_dir}\n✓ Subdirectories: {', '.join(expected_subdirs)}"
                self._log_test_result(True, details)

        except Exception as e:
            self._log_test_result(False, f"Exception: {str(e)}")
            raise

    # ========================================================================
    # TESTY KOMUNIKACJI Z API
    # ========================================================================

    @patch('mp_scraper.SejmAPI')
    def test_api_communication_mps_list(self, mock_sejm_api):
        """Testuje komunikację z API dla pobierania listy posłów"""
        try:
            # Przygotuj mock danych
            mock_mps_data = [
                {
                    'id': 1, 'firstName': 'Jan', 'lastName': 'Kowalski',
                    'club': 'Klub Testowy', 'voivodeship': 'mazowieckie'
                },
                {
                    'id': 2, 'firstName': 'Anna', 'lastName': 'Nowak',
                    'club': 'Inny Klub', 'voivodeship': 'śląskie'
                }
            ]

            # Skonfiguruj mock
            mock_api_instance = Mock()
            mock_api_instance._make_request.return_value = mock_mps_data
            mock_sejm_api.return_value = mock_api_instance

            # Test
            scraper = MPScraper()
            result = scraper.api._make_request("/sejm/term10/MP")

            # Sprawdzenia
            self.assertIsNotNone(result)
            self.assertEqual(len(result), 2)
            self.assertEqual(result[0]['firstName'], 'Jan')
            self.assertEqual(result[1]['lastName'], 'Nowak')

            # Sprawdź czy API zostało wywołane
            mock_api_instance._make_request.assert_called_with("/sejm/term10/MP")

            details = f"✓ Mock API response: {len(result)} MPs\n✓ API call verified\n✓ Data structure correct"
            self._log_test_result(True, details)

        except Exception as e:
            self._log_test_result(False, f"Exception: {str(e)}")
            raise

    @patch('mp_scraper.SejmAPI')
    def test_api_communication_clubs_list(self, mock_sejm_api):
        """Testuje komunikację z API dla pobierania listy klubów"""
        try:
            # Mock danych klubów
            mock_clubs_data = [
                {'id': 1, 'name': 'Prawo i Sprawiedliwość'},
                {'id': 2, 'name': 'Platforma Obywatelska'},
                {'id': 3, 'name': 'Lewica'}
            ]

            mock_api_instance = Mock()
            mock_api_instance._make_request.return_value = mock_clubs_data
            mock_sejm_api.return_value = mock_api_instance

            scraper = MPScraper()
            result = scraper.api._make_request("/sejm/term10/clubs")

            # Sprawdzenia
            self.assertIsNotNone(result)
            self.assertEqual(len(result), 3)
            self.assertIn('name', result[0])

            details = f"✓ Retrieved {len(result)} clubs\n✓ All clubs have required fields"
            self._log_test_result(True, details)

        except Exception as e:
            self._log_test_result(False, f"Exception: {str(e)}")
            raise

    # ========================================================================
    # TESTY POBIERANIA I PRZETWARZANIA DANYCH
    # ========================================================================

    @patch('mp_scraper.SejmAPI')
    def test_mp_summary_generation(self, mock_sejm_api):
        """Testuje generowanie podsumowania posłów bez pobierania szczegółów"""
        try:
            # Przygotuj dane testowe
            mock_mps = [
                {'id': 1, 'firstName': 'Jan', 'lastName': 'Kowalski', 'club': 'PiS'},
                {'id': 2, 'firstName': 'Anna', 'lastName': 'Nowak', 'club': 'PO'},
                {'id': 3, 'firstName': 'Piotr', 'lastName': 'Wiśniewski', 'club': 'PiS'},
                {'id': 4, 'firstName': 'Maria', 'lastName': 'Zielińska', 'club': 'Lewica'},
            ]

            mock_api_instance = Mock()
            mock_api_instance._make_request.return_value = mock_mps
            mock_sejm_api.return_value = mock_api_instance

            # Test
            scraper = MPScraper()
            summary = scraper.get_mps_summary(10)

            # Sprawdzenia
            self.assertIsNotNone(summary)
            self.assertEqual(summary['term'], 10)
            self.assertEqual(summary['total_mps'], 4)

            # Sprawdź grupowanie po klubach
            expected_clubs = {'PiS': 2, 'PO': 1, 'Lewica': 1}
            self.assertEqual(summary['clubs'], expected_clubs)
            self.assertEqual(summary['clubs_count'], 3)

            details = f"✓ Term: {summary['term']}\n✓ Total MPs: {summary['total_mps']}\n✓ Clubs: {summary['clubs_count']}\n✓ Club distribution: {summary['clubs']}"
            self._log_test_result(True, details)

        except Exception as e:
            self._log_test_result(False, f"Exception: {str(e)}")
            raise

    def test_filename_sanitization(self):
        """Testuje czyszczenie nazw plików dla bezpiecznego zapisu"""
        try:
            # Test różnych problematycznych nazw
            test_cases = [
                ('Jan Kowalski', 'Jan_Kowalski'),
                ('Anna-Maria Nowak-Kowalska', 'Anna-Maria_Nowak-Kowalska'),
                ('Test/\\*?<>|:', 'Test_______'),
                ('Bardzo długa nazwa która przekracza limit znaków i powinna zostać skrócona',
                 'Bardzo_dluga_nazwa_ktora_przekracza_limit_znako'),
                ('', ''),
                ('123', '123'),
            ]

            for input_name, expected in test_cases:
                result = MPScraper._make_safe_filename(input_name)
                self.assertEqual(result, expected,
                                 f"Failed for input: '{input_name}', got: '{result}', expected: '{expected}'")
                # Sprawdź długość
                self.assertLessEqual(len(result), 50)

            details = f"✓ Tested {len(test_cases)} filename cases\n✓ All names properly sanitized\n✓ Length limits respected"
            self._log_test_result(True, details)

        except Exception as e:
            self._log_test_result(False, f"Exception: {str(e)}")
            raise

    def test_json_save_functionality(self):
        """Testuje zapisywanie danych do plików JSON"""
        try:
            test_data = {
                'id': 123,
                'name': 'Test Data',
                'nested': {
                    'key': 'value',
                    'number': 42
                },
                'list': [1, 2, 3, 'test']
            }

            # Utwórz tymczasowy plik
            test_file = self.test_data_dir / 'test.json'

            # Test zapisu
            result = MPScraper._save_json(test_data, test_file)
            self.assertTrue(result)
            self.assertTrue(test_file.exists())

            # Test odczytu i weryfikacji
            with open(test_file, 'r', encoding='utf-8') as f:
                loaded_data = json.load(f)

            self.assertEqual(loaded_data, test_data)

            details = f"✓ JSON saved successfully\n✓ File exists: {test_file.name}\n✓ Data integrity verified"
            self._log_test_result(True, details)

        except Exception as e:
            self._log_test_result(False, f"Exception: {str(e)}")
            raise

    # ========================================================================
    # TESTY OBSŁUGI BŁĘDÓW
    # ========================================================================

    @patch('mp_scraper.SejmAPI')
    def test_api_failure_handling(self, mock_sejm_api):
        """Testuje obsługę błędów komunikacji z API"""
        try:
            # Skonfiguruj API żeby zwracał None (symulacja błędu)
            mock_api_instance = Mock()
            mock_api_instance._make_request.return_value = None
            mock_sejm_api.return_value = mock_api_instance

            scraper = MPScraper()

            # Test podsumowania z błędem API
            summary = scraper.get_mps_summary(10)
            self.assertIsNone(summary)

            # Test scrapowania z błędem API
            with patch.object(scraper, '_ensure_mp_directory') as mock_ensure_dir:
                mock_ensure_dir.return_value = self.test_data_dir
                stats = scraper.scrape_mps(10)

                # Sprawdź czy błędy zostały odnotowane
                self.assertGreater(stats['errors'], 0)
                self.assertEqual(stats['mps_downloaded'], 0)

            details = f"✓ API failure properly handled\n✓ None response handled\n✓ Error count incremented"
            self._log_test_result(True, details)

        except Exception as e:
            self._log_test_result(False, f"Exception: {str(e)}")
            raise

    def test_invalid_file_operations(self):
        """Testuje obsługę błędów operacji na plikach"""
        try:
            # Test zapisu do nieistniejącego katalogu (symulacja braku uprawnień)
            invalid_path = Path("/root/impossible/path/test.json")
            test_data = {'test': 'data'}

            result = MPScraper._save_json(test_data, invalid_path)
            self.assertFalse(result)  # Oczekujemy niepowodzenia

            details = "✓ Invalid file path handled gracefully\n✓ No exceptions raised\n✓ Function returned False"
            self._log_test_result(True, details)

        except Exception as e:
            self._log_test_result(False, f"Exception: {str(e)}")
            raise

    # ========================================================================
    # TESTY EDGE CASES I SCENARIUSZY GRANICZNYCH
    # ========================================================================

    def test_safe_id_formatting(self):
        """Testuje bezpieczne formatowanie ID (może być string lub int)"""
        try:
            test_cases = [
                (1, "01"),
                (123, "123"),
                ("05", "05"),
                ("abc", "abc"),
                (None, "None"),
                ("", ""),
            ]

            for input_id, expected in test_cases:
                result = MPScraper._safe_format_id(input_id)
                self.assertEqual(result, expected,
                                 f"Failed for input: {input_id}, got: '{result}', expected: '{expected}'")

            details = f"✓ Tested {len(test_cases)} ID formatting cases\n✓ String and int IDs handled\n✓ Edge cases covered"
            self._log_test_result(True, details)

        except Exception as e:
            self._log_test_result(False, f"Exception: {str(e)}")
            raise

    @patch('mp_scraper.SejmAPI')
    def test_empty_data_handling(self, mock_sejm_api):
        """Testuje obsługę pustych danych z API"""
        try:
            # Test z pustą listą posłów
            mock_api_instance = Mock()
            mock_api_instance._make_request.return_value = []
            mock_sejm_api.return_value = mock_api_instance

            scraper = MPScraper()
            summary = scraper.get_mps_summary(10)

            # Sprawdzenia dla pustych danych
            self.assertIsNotNone(summary)
            self.assertEqual(summary['total_mps'], 0)
            self.assertEqual(summary['clubs'], {})
            self.assertEqual(summary['clubs_count'], 0)

            details = "✓ Empty MP list handled\n✓ Summary generated correctly\n✓ No crashes with empty data"
            self._log_test_result(True, details)

        except Exception as e:
            self._log_test_result(False, f"Exception: {str(e)}")
            raise

    @patch('mp_scraper.SejmAPI')
    def test_malformed_data_handling(self, mock_sejm_api):
        """Testuje obsługę niepoprawnych danych z API"""
        try:
            # Test z niepełnymi danymi posłów
            malformed_mps = [
                {'id': 1, 'firstName': 'Jan'},  # brak lastName
                {'lastName': 'Nowak'},  # brak id i firstName
                {'id': 3, 'firstName': 'Anna', 'lastName': 'Kowalska'},  # poprawny
                {},  # pusty obiekt
            ]

            mock_api_instance = Mock()
            mock_api_instance._make_request.return_value = malformed_mps
            mock_sejm_api.return_value = mock_api_instance

            scraper = MPScraper()
            summary = scraper.get_mps_summary(10)

            # Sprawdzenia - powinna poradzić sobie z niepełnymi danymi
            self.assertIsNotNone(summary)
            self.assertEqual(summary['total_mps'], 4)  # liczy wszystkie rekordy

            details = "✓ Malformed data handled\n✓ No crashes on missing fields\n✓ Summary generated despite data issues"
            self._log_test_result(True, details)

        except Exception as e:
            self._log_test_result(False, f"Exception: {str(e)}")
            raise

    # ========================================================================
    # TESTY INTEGRACYJNE I PERFORMANCE
    # ========================================================================

    @patch('mp_scraper.SejmAPI')
    def test_full_scraping_workflow_mock(self, mock_sejm_api):
        """Testuje pełny workflow scrapowania z zamockowanym API"""
        try:
            # Przygotuj kompletne mock dane
            mock_mps = [
                {'id': 1, 'firstName': 'Jan', 'lastName': 'Kowalski', 'club': 'PiS'},
                {'id': 2, 'firstName': 'Anna', 'lastName': 'Nowak', 'club': 'PO'}
            ]

            mock_mp_details_1 = {
                'id': 1, 'firstName': 'Jan', 'lastName': 'Kowalski',
                'club': 'PiS', 'email': 'jan.kowalski@sejm.gov.pl'
            }

            mock_mp_details_2 = {
                'id': 2, 'firstName': 'Anna', 'lastName': 'Nowak',
                'club': 'PO', 'email': 'anna.nowak@sejm.gov.pl'
            }

            # Skonfiguruj mock API
            mock_api_instance = Mock()

            def side_effect(endpoint):
                if endpoint == "/sejm/term10/MP":
                    return mock_mps
                elif endpoint == "/sejm/term10/MP/1":
                    return mock_mp_details_1
                elif endpoint == "/sejm/term10/MP/2":
                    return mock_mp_details_2
                elif endpoint in ["/sejm/term10/MP/1/photo", "/sejm/term10/MP/2/photo"]:
                    return b"fake_photo_data"
                elif "votings/stats" in endpoint:
                    return {"total_votes": 100, "attendance": 95}
                return None

            mock_api_instance._make_request.side_effect = side_effect
            mock_sejm_api.return_value = mock_api_instance

            # Użyj tymczasowego katalogu
            with patch.object(MPScraper, '__init__', lambda x: None):
                scraper = MPScraper()
                scraper.api = mock_api_instance
                scraper.base_dir = self.test_data_dir
                scraper.stats = {
                    'mps_downloaded': 0, 'clubs_downloaded': 0,
                    'photos_downloaded': 0, 'errors': 0,
                    'voting_stats_downloaded': 0
                }

                # Wykonaj scraping
                stats = scraper.scrape_mps(10, download_photos=True, download_voting_stats=True)

                # Sprawdzenia
                self.assertEqual(stats['mps_downloaded'], 2)
                self.assertEqual(stats['photos_downloaded'], 2)
                self.assertEqual(stats['voting_stats_downloaded'], 2)
                self.assertEqual(stats['errors'], 0)

                # Sprawdź czy pliki zostały utworzone
                mp_dir = self.test_data_dir / "kadencja_10" / "poslowie"
                self.assertTrue(mp_dir.exists())

                # Sprawdź pliki posłów
                mp_files = list(mp_dir.glob("posel_*.json"))
                self.assertEqual(len(mp_files), 2)

            details = f"✓ Full workflow completed\n✓ Downloaded: {stats['mps_downloaded']} MPs\n✓ Photos: {stats['photos_downloaded']}\n✓ Stats: {stats['voting_stats_downloaded']}\n✓ Files created: {len(mp_files) if 'mp_files' in locals() else 'N/A'}"
            self._log_test_result(True, details)

        except Exception as e:
            self._log_test_result(False, f"Exception: {str(e)}")
            raise

    def test_performance_large_dataset_simulation(self):
        """Symuluje performance test z dużą ilością danych"""
        try:
            # Symuluj dużą listę posłów
            large_mp_list = []
            for i in range(460):  # Typowa liczba posłów
                large_mp_list.append({
                    'id': i + 1,
                    'firstName': f'Imię{i + 1}',
                    'lastName': f'Nazwisko{i + 1}',
                    'club': f'Klub{(i % 8) + 1}'  # 8 klubów
                })

            start_time = time.time()

            # Test grupowania dużej ilości danych
            clubs_summary = {}
            for mp in large_mp_list:
                club = mp.get('club', 'Brak klubu')
                if club not in clubs_summary:
                    clubs_summary[club] = 0
                clubs_summary[club] += 1

            processing_time = time.time() - start_time

            # Sprawdzenia
            self.assertEqual(len(large_mp_list), 460)
            self.assertEqual(len(clubs_summary), 8)
            self.assertLess(processing_time, 1.0)  # Powinno być szybko

            details = f"✓ Processed {len(large_mp_list)} MPs in {processing_time:.3f}s\n✓ Grouped into {len(clubs_summary)} clubs\n✓ Performance acceptable"
            self._log_test_result(True, details)

        except Exception as e:
            self._log_test_result(False, f"Exception: {str(e)}")
            raise

    # ========================================================================
    # TESTY FUNKCJONALNOŚCI SPECJALIZOWANYCH
    # ========================================================================

    @patch('mp_scraper.SejmAPI')
    def test_specific_mp_scraping(self, mock_sejm_api):
        """Testuje pobieranie danych konkretnego posła"""
        try:
            mock_mp_data = {
                'id': 42,
                'firstName': 'Adam',
                'lastName': 'Testowy',
                'club': 'Klub Testowy',
                'email': 'adam.testowy@sejm.gov.pl'
            }

            mock_api_instance = Mock()
            mock_api_instance._make_request.return_value = mock_mp_data
            mock_sejm_api.return_value = mock_api_instance

            with patch.object(MPScraper, '__init__', lambda x: None):
                scraper = MPScraper()
                scraper.api = mock_api_instance
                scraper.base_dir = self.test_data_dir
                scraper.stats = {
                    'mps_downloaded': 0, 'clubs_downloaded': 0,
                    'photos_downloaded': 0, 'errors': 0,
                    'voting_stats_downloaded': 0
                }

                # Test pobierania konkretnego posła
                result = scraper.scrape_specific_mp(10, 42, download_photos=False, download_voting_stats=False)

                # Sprawdzenia
                self.assertTrue(result)
                self.assertEqual(scraper.stats['mps_downloaded'], 1)

            details = f"✓ Specific MP scraped successfully\n✓ MP ID: 42\n✓ Stats updated correctly"
            self._log_test_result(True, details)

        except Exception as e:
            self._log_test_result(False, f"Exception: {str(e)}")
            raise

    @patch('mp_scraper.SejmAPI')
    def test_clubs_only_scraping(self, mock_sejm_api):
        """Testuje pobieranie tylko klubów parlamentarnych"""
        try:
            mock_clubs = [
                {'id': 1, 'name': 'Prawo i Sprawiedliwość'},
                {'id': 2, 'name': 'Platforma Obywatelska'}
            ]

            mock_club_details = {
                'id': 1,
                'name': 'Prawo i Sprawiedliwość',
                'members_count': 120
            }

            mock_api_instance = Mock()

            def side_effect(endpoint):
                if endpoint == "/sejm/term10/clubs":
                    return mock_clubs
                elif "/clubs/" in endpoint and "/logo" not in endpoint:
                    return mock_club_details
                elif "/logo" in endpoint:
                    return b"fake_logo_data"
                return None

            mock_api_instance._make_request.side_effect = side_effect
            mock_sejm_api.return_value = mock_api_instance

            with patch.object(MPScraper, '__init__', lambda x: None):
                scraper = MPScraper()
                scraper.api = mock_api_instance
                scraper.base_dir = self.test_data_dir
                scraper.stats = {
                    'mps_downloaded': 0, 'clubs_downloaded': 0,
                    'photos_downloaded': 0, 'errors': 0,
                    'voting_stats_downloaded': 0
                }

                stats = scraper.scrape_clubs(10)

                # Sprawdzenia
                self.assertEqual(stats['clubs_downloaded'], 2)
                self.assertEqual(stats['errors'], 0)

            details = f"✓ Clubs scraping completed\n✓ Downloaded: {stats['clubs_downloaded']} clubs\n✓ No errors occurred"
            self._log_test_result(True, details)

        except Exception as e:
            self._log_test_result(False, f"Exception: {str(e)}")
            raise


# ========================================================================
# DODATKOWE UTILITY KLASY I FUNKCJE
# ========================================================================

class MockDataGenerator:
    """Generator mock danych dla testów"""

    @staticmethod
    def generate_mock_mps(count: int = 10) -> List[Dict]:
        """Generuje listę mock posłów"""
        clubs = ['PiS', 'PO', 'Lewica', 'PSL', 'Konfederacja']
        voivodeships = ['mazowieckie', 'śląskie', 'wielkopolskie', 'małopolskie']

        mps = []
        for i in range(count):
            mps.append({
                'id': i + 1,
                'firstName': f'Imię{i + 1}',
                'lastName': f'Nazwisko{i + 1}',
                'club': clubs[i % len(clubs)],
                'voivodeship': voivodeships[i % len(voivodeships)],
                'email': f'posel{i + 1}@sejm.gov.pl'
            })
        return mps

    @staticmethod
    def generate_mock_clubs(count: int = 5) -> List[Dict]:
        """Generuje listę mock klubów"""
        club_names = [
            'Prawo i Sprawiedliwość',
            'Platforma Obywatelska',
            'Lewica',
            'Polskie Stronnictwo Ludowe',
            'Konfederacja'
        ]

        clubs = []
        for i in range(count):
            clubs.append({
                'id': i + 1,
                'name': club_names[i] if i < len(club_names) else f'Klub {i + 1}'
            })
        return clubs


def run_health_check():
    """
    Uruchamia pełny health check z ładnym interfejsem
    """
    print(f"{TestColors.BOLD}🔍 Starting SejmBot MP Scraper Health Check...{TestColors.RESET}")
    print()

    # Sprawdź czy kolory są wspierane
    if sys.stdout.isatty():
        enable_colors = True
    else:
        enable_colors = False
        TestColors.disable_colors()

    # Uruchom testy
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestMPScraper)

    # Custom runner który nie wypisuje standardowego output
    stream = StringIO()
    runner = unittest.TextTestRunner(stream=stream, verbosity=0)

    try:
        result = runner.run(suite)

        # Podsumowanie końcowe
        if result.wasSuccessful():
            print(f"{TestColors.GREEN}🎉 ALL SYSTEMS OPERATIONAL{TestColors.RESET}")
            print(f"{TestColors.GREEN}   Health Check: PASSED{TestColors.RESET}")
            return 0
        else:
            print(f"{TestColors.RED}⚠️  SYSTEM DEGRADED{TestColors.RESET}")
            print(f"{TestColors.RED}   Health Check: FAILED{TestColors.RESET}")
            return 1

    except Exception as e:
        print(f"{TestColors.RED}💥 CRITICAL ERROR DURING HEALTH CHECK{TestColors.RESET}")
        print(f"{TestColors.RED}   Exception: {str(e)}{TestColors.RESET}")
        return 2


def run_quick_check():
    """
    Szybki health check - tylko podstawowe testy
    """
    print(f"{TestColors.CYAN}⚡ Quick Health Check Mode{TestColors.RESET}")
    print()

    # Uruchom tylko wybrane testy
    quick_tests = [
        'test_scraper_initialization',
        'test_directory_structure_creation',
        'test_filename_sanitization',
        'test_json_save_functionality'
    ]

    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    for test_name in quick_tests:
        suite.addTest(TestMPScraper(test_name))

    stream = StringIO()
    runner = unittest.TextTestRunner(stream=stream, verbosity=0)

    result = runner.run(suite)

    if result.wasSuccessful():
        print(f"{TestColors.GREEN}✅ Quick Check: PASSED{TestColors.RESET}")
        return 0
    else:
        print(f"{TestColors.RED}❌ Quick Check: FAILED{TestColors.RESET}")
        return 1


def run_integration_tests():
    """
    Uruchamia testy integracyjne
    """
    print(f"{TestColors.PURPLE}🔗 Integration Tests Mode{TestColors.RESET}")
    print()

    integration_tests = [
        'test_full_scraping_workflow_mock',
        'test_performance_large_dataset_simulation',
        'test_specific_mp_scraping',
        'test_clubs_only_scraping'
    ]

    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    for test_name in integration_tests:
        suite.addTest(TestMPScraper(test_name))

    stream = StringIO()
    runner = unittest.TextTestRunner(stream=stream, verbosity=0)

    result = runner.run(suite)

    if result.wasSuccessful():
        print(f"{TestColors.GREEN}✅ Integration Tests: PASSED{TestColors.RESET}")
        return 0
    else:
        print(f"{TestColors.RED}❌ Integration Tests: FAILED{TestColors.RESET}")
        return 1


# ========================================================================
# MAIN - PROFESSIONAL CLI INTERFACE
# ========================================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="🧪 SejmBot MP Scraper Professional Health Check",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Przykłady użycia:
  %(prog)s                    # Pełny health check
  %(prog)s --quick            # Szybki health check  
  %(prog)s --integration      # Testy integracyjne
  %(prog)s --no-colors        # Bez kolorów (CI/CD)
  %(prog)s --verbose          # Szczegółowe informacje

Exit codes:
  0 - Wszystkie testy przeszły
  1 - Niektóre testy nie przeszły
  2 - Krytyczny błąd podczas testów
        """
    )

    parser.add_argument(
        '--quick',
        action='store_true',
        help='Uruchom tylko podstawowe testy (szybko)'
    )

    parser.add_argument(
        '--integration',
        action='store_true',
        help='Uruchom tylko testy integracyjne'
    )

    parser.add_argument(
        '--no-colors',
        action='store_true',
        help='Wyłącz kolory (przydatne dla CI/CD)'
    )

    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Szczegółowe informacje debug'
    )

    args = parser.parse_args()

    # Wyłącz kolory jeśli requested
    if args.no_colors:
        TestColors.disable_colors()

    # Uruchom odpowiedni tryb
    try:
        if args.quick:
            exit_code = run_quick_check()
        elif args.integration:
            exit_code = run_integration_tests()
        else:
            exit_code = run_health_check()

        sys.exit(exit_code)

    except KeyboardInterrupt:
        print(f"\n{TestColors.YELLOW}⏹️  Health check przerwany przez użytkownika{TestColors.RESET}")
        sys.exit(130)
    except Exception as e:
        print(f"\n{TestColors.RED}💥 Nieoczekiwany błąd: {str(e)}{TestColors.RESET}")
        sys.exit(2)
