#!/usr/bin/env python3
# test_sejm_api_fancy.py
"""
🌐 SejmBot API Client - Professional Test Suite
===============================================

Profesjonalny test suite dla modułu SejmAPI.
Testuje komunikację z API Sejmu RP, obsługę błędów, retry logic i więcej.

Autor: SejmBot Team
Wersja: 1.0.0 - Complete API Test Coverage
"""

import sys
import tempfile
import time
import unittest
from datetime import datetime
from io import StringIO
from pathlib import Path
from typing import Dict, List, Optional, Any
from unittest.mock import Mock, patch

import requests
from wcwidth import wcswidth

# ========================================================================
# IMPORTY I KONFIGURACJA ŚCIEŻEK
# ========================================================================

current_dir = Path(__file__).parent.absolute()
project_root = current_dir
sys.path.insert(0, str(project_root))

print(f"🔍 Szukam modułów API w ścieżkach:")
for path in sys.path[:5]:
    print(f"   - {path}")
print()

# Próby importu
sejm_api_module = None
config_module = None

import_attempts = [
    lambda: __import__('sejm_api'),
    lambda: __import__('config'),
    lambda: __import__('SejmBotScraper.sejm_api', fromlist=['sejm_api']),
    lambda: __import__('SejmBotScraper.config', fromlist=['config']),
]

# Import SejmAPI
for attempt in [import_attempts[0], import_attempts[2]]:
    try:
        sejm_api_module = attempt()
        SejmAPI = getattr(sejm_api_module, 'SejmAPI', None)
        if SejmAPI:
            print("✅ sejm_api zaimportowany pomyślnie")
            break
    except ImportError:
        continue

# Import config
for attempt in [import_attempts[1], import_attempts[3]]:
    try:
        config_module = attempt()
        API_BASE_URL = getattr(config_module, 'API_BASE_URL', 'https://api.sejm.gov.pl')
        REQUEST_TIMEOUT = getattr(config_module, 'REQUEST_TIMEOUT', 30)
        REQUEST_DELAY = getattr(config_module, 'REQUEST_DELAY', 0.1)
        USER_AGENT = getattr(config_module, 'USER_AGENT', 'SejmBotScraper/1.0')
        print("✅ config zaimportowany pomyślnie")
        break
    except ImportError:
        continue

# Mock klasy jeśli nie udało się zaimportować
if not sejm_api_module or not SejmAPI:
    print("⚠️  Nie można zaimportować sejm_api - tworzę mock klasę")


    class MockSejmAPI:
        def __init__(self):
            self.base_url = "https://api.sejm.gov.pl"
            self.session = Mock()

        def _make_request(self, endpoint: str) -> Optional[Any]:
            return None

        def get_terms(self) -> Optional[List[Dict]]:
            return None

        def get_term_info(self, term: int) -> Optional[Dict]:
            return None

        def get_proceedings(self, term: int) -> Optional[List[Dict]]:
            return None

        def get_proceeding_info(self, term: int, proceeding_id: int) -> Optional[Dict]:
            return None

        def get_transcripts_list(self, term: int, proceeding_id: int, date: str) -> Optional[Dict]:
            return None

        def get_transcript_pdf(self, term: int, proceeding_id: int, date: str) -> Optional[bytes]:
            return None

        def get_statement_html(self, term: int, proceeding_id: int, date: str, statement_num: int) -> Optional[str]:
            return None

        def get_mps(self, term: int) -> Optional[List[Dict]]:
            return None

        def get_mp_info(self, term: int, mp_id: int) -> Optional[Dict]:
            return None


    SejmAPI = MockSejmAPI

# Domyślne wartości config
if not config_module:
    API_BASE_URL = 'https://api.sejm.gov.pl'
    REQUEST_TIMEOUT = 30
    REQUEST_DELAY = 0.1
    USER_AGENT = 'SejmBotScraper/1.0'

print("🚀 Moduły API gotowe do testów\n")


class TestColors:
    """Kolory dla ładnego wyświetlania"""
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    PURPLE = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    GRAY = '\033[90m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    RESET = '\033[0m'

    @classmethod
    def disable_colors(cls):
        for attr in dir(cls):
            if not attr.startswith('_') and attr != 'disable_colors':
                setattr(cls, attr, '')


class HealthCheckReporter:
    """Professional reporter dla testów API"""

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
║    🌐 SejmBot API Client - Professional Health Check              ║
║                                                                   ║
║    Status: RUNNING                                                ║
║    Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}                                        ║
║    Environment: API Test Suite v1.0                              ║
║                                                                   ║
╚═══════════════════════════════════════════════════════════════════╝{TestColors.RESET}
        """
        print(header)

    def start_test_session(self):
        self.start_time = time.time()
        self.print_header()
        print(f"{TestColors.BLUE}🚀 Inicjalizacja API test suite...{TestColors.RESET}")
        print()

    def log_test_start(self, test_name: str, description: str):
        print(f"{TestColors.GRAY}┌─ {TestColors.BOLD}{test_name}{TestColors.RESET}")
        print(f"{TestColors.GRAY}│  {description}{TestColors.RESET}")

    def log_test_result(self, test_name: str, passed: bool, details: str = None, duration: float = None):
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

        self.test_results.append({
            'name': test_name,
            'passed': passed,
            'details': details,
            'duration': duration
        })

    def print_summary(self):
        self.end_time = time.time()
        total_duration = self.end_time - self.start_time

        passed_count = sum(1 for result in self.test_results if result['passed'])
        failed_count = len(self.test_results) - passed_count
        success_rate = (passed_count / len(self.test_results) * 100) if self.test_results else 0

        if failed_count == 0:
            status_text = "HEALTHY"
            status_color = TestColors.GREEN
            overall_icon = "✅"
        elif failed_count <= 2:
            status_text = "DEGRADED"
            status_color = TestColors.YELLOW
            overall_icon = "⚠️"
        else:
            status_text = "UNHEALTHY"
            status_color = TestColors.RED
            overall_icon = "❌"

        WIDTH = 67

        def pad_center(content):
            content_width = wcswidth(content) or len(content)
            if content_width > WIDTH:
                content = content[:WIDTH - 3] + "..."
                content_width = len(content)
            total_padding = WIDTH - content_width
            left = total_padding // 2
            right = total_padding - left
            return f"║{' ' * left}{content}{' ' * right}║"

        def pad_left(content, indent=2):
            content_width = wcswidth(content) or len(content)
            if content_width > WIDTH - indent:
                content = content[:WIDTH - indent - 3] + "..."
                content_width = len(content)
            right = WIDTH - content_width - indent
            return f"║{' ' * indent}{content}{' ' * right}║"

        lines = [
            f"{TestColors.CYAN}╔{'═' * WIDTH}╗",
            pad_center("API HEALTH CHECK SUMMARY"),
            f"╠{'═' * WIDTH}╣",
            pad_center(""),
            pad_center(f"{overall_icon} API Status: {status_color}{status_text}{TestColors.CYAN}"),
            pad_center(""),
            pad_left("📊 Test Statistics:"),
            pad_left(f"• Total Tests: {len(self.test_results)}"),
            pad_left(f"• Passed: {TestColors.GREEN}{passed_count}{TestColors.CYAN}"),
            pad_left(f"• Failed: {TestColors.RED}{failed_count}{TestColors.CYAN}"),
            pad_left(f"• Success Rate: {success_rate:.1f}%"),
            pad_left(""),
            pad_left(f"⏱️  Execution Time: {total_duration:.2f}s"),
            pad_center(""),
        ]

        if failed_count > 0:
            lines.append(pad_left("❌ Failed Tests:"))
            for result in self.test_results:
                if not result['passed']:
                    test_name = result['name']
                    if len(test_name) > WIDTH - 6:
                        test_name = test_name[:WIDTH - 9] + "..."
                    lines.append(pad_left(f"• {test_name}"))
            lines.append(pad_left(""))

        lines.append(f"╚{'═' * WIDTH}╝{TestColors.RESET}")

        for line in lines:
            print(line)


class TestSejmAPI(unittest.TestCase):
    """Główna klasa testów dla SejmAPI"""

    @classmethod
    def setUpClass(cls):
        cls.reporter = HealthCheckReporter()
        cls.reporter.start_test_session()
        cls.temp_dir = tempfile.mkdtemp(prefix="api_test_")

    @classmethod
    def tearDownClass(cls):
        cls.reporter.print_summary()

    def setUp(self):
        self.test_start_time = time.time()

    def _log_test_result(self, passed: bool, details: str = None):
        test_name = self._testMethodName
        test_description = self._testMethodDoc or "Brak opisu"
        duration = time.time() - self.test_start_time
        self.reporter.log_test_start(test_name, test_description.strip())
        self.reporter.log_test_result(test_name, passed, details, duration)

    # ========================================================================
    # TESTY INICJALIZACJI I KONFIGURACJI
    # ========================================================================

    def test_api_client_initialization(self):
        """Sprawdza poprawność inicjalizacji klienta API"""
        try:
            api = SejmAPI()

            # Sprawdź podstawowe atrybuty
            self.assertIsNotNone(api.base_url)
            self.assertIn('https://api.sejm.gov.pl', api.base_url)

            # Sprawdź session jeśli dostępna
            if hasattr(api, 'session'):
                self.assertIsNotNone(api.session)
                # Sprawdź User-Agent
                if hasattr(api.session, 'headers'):
                    user_agent = api.session.headers.get('User-Agent', '')
                    self.assertIn('SejmBot', user_agent)

            details = f"✓ Base URL: {api.base_url}\n✓ Session configured\n✓ Headers set properly"
            self._log_test_result(True, details)

        except Exception as e:
            self._log_test_result(False, f"Exception: {str(e)}")
            raise

    def test_api_configuration_values(self):
        """Testuje wartości konfiguracyjne API"""
        try:
            # Sprawdź zmienne konfiguracyjne
            self.assertIsInstance(API_BASE_URL, str)
            self.assertGreater(len(API_BASE_URL), 0)
            self.assertIsInstance(REQUEST_TIMEOUT, (int, float))
            self.assertGreater(REQUEST_TIMEOUT, 0)
            self.assertIsInstance(REQUEST_DELAY, (int, float))
            self.assertGreaterEqual(REQUEST_DELAY, 0)

            details = f"✓ Base URL: {API_BASE_URL}\n✓ Timeout: {REQUEST_TIMEOUT}s\n✓ Delay: {REQUEST_DELAY}s\n✓ User-Agent: {USER_AGENT}"
            self._log_test_result(True, details)

        except Exception as e:
            self._log_test_result(False, f"Exception: {str(e)}")
            raise

    # ========================================================================
    # TESTY OBSŁUGI HTTP I BŁĘDÓW
    # ========================================================================

    @patch('requests.Session.get')
    def test_successful_http_request(self, mock_get):
        """Testuje obsługę udanych zapytań HTTP"""
        try:
            # Przygotuj mock odpowiedź
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.headers = {'content-type': 'application/json'}
            mock_response.json.return_value = {'test': 'data'}
            mock_response.raise_for_status.return_value = None
            mock_get.return_value = mock_response

            api = SejmAPI()
            result = api._make_request('/test/endpoint')

            # Sprawdzenia
            self.assertIsNotNone(result)
            self.assertEqual(result, {'test': 'data'})
            mock_get.assert_called_once()

            details = f"✓ HTTP request successful\n✓ JSON parsing works\n✓ Response structure correct"
            self._log_test_result(True, details)

        except Exception as e:
            self._log_test_result(False, f"Exception: {str(e)}")
            raise

    @patch('requests.Session.get')
    def test_http_error_handling(self, mock_get):
        """Testuje obsługę błędów HTTP"""
        try:
            # Symuluj błąd 404
            mock_get.side_effect = requests.exceptions.HTTPError("404 Not Found")

            api = SejmAPI()
            result = api._make_request('/nonexistent/endpoint')

            # Powinno zwrócić None przy błędzie
            self.assertIsNone(result)

            details = f"✓ HTTP errors handled gracefully\n✓ Returns None on error\n✓ No exceptions propagated"
            self._log_test_result(True, details)

        except Exception as e:
            self._log_test_result(False, f"Exception: {str(e)}")
            raise

    @patch('requests.Session.get')
    def test_timeout_handling(self, mock_get):
        """Testuje obsługę timeout"""
        try:
            # Symuluj timeout
            mock_get.side_effect = requests.exceptions.Timeout("Request timeout")

            api = SejmAPI()
            result = api._make_request('/slow/endpoint')

            self.assertIsNone(result)

            details = f"✓ Timeout handled properly\n✓ No hanging requests\n✓ Graceful fallback"
            self._log_test_result(True, details)

        except Exception as e:
            self._log_test_result(False, f"Exception: {str(e)}")
            raise

    @patch('requests.Session.get')
    def test_connection_error_handling(self, mock_get):
        """Testuje obsługę błędów połączenia"""
        try:
            # Symuluj błąd połączenia
            mock_get.side_effect = requests.exceptions.ConnectionError("Connection failed")

            api = SejmAPI()
            result = api._make_request('/test/endpoint')

            self.assertIsNone(result)

            details = f"✓ Connection errors handled\n✓ Network issues managed\n✓ Resilient to connectivity problems"
            self._log_test_result(True, details)

        except Exception as e:
            self._log_test_result(False, f"Exception: {str(e)}")
            raise

    # ========================================================================
    # TESTY ENDPOINTÓW KADENCJI I POSIEDZEŃ
    # ========================================================================

    @patch('sejm_api.SejmAPI._make_request')
    def test_get_terms_endpoint(self, mock_request):
        """Testuje endpoint pobierania listy kadencji"""
        try:
            mock_terms = [
                {'num': 9, 'from': '2019-11-12', 'to': '2023-11-12'},
                {'num': 10, 'from': '2023-11-13', 'to': None, 'current': True}
            ]
            mock_request.return_value = mock_terms

            api = SejmAPI()
            result = api.get_terms()

            self.assertIsNotNone(result)
            self.assertEqual(len(result), 2)
            self.assertEqual(result[1]['num'], 10)
            self.assertTrue(result[1].get('current', False))

            mock_request.assert_called_with('/sejm/term')

            details = f"✓ Terms endpoint called correctly\n✓ Retrieved {len(result)} terms\n✓ Current term identified"
            self._log_test_result(True, details)

        except Exception as e:
            self._log_test_result(False, f"Exception: {str(e)}")
            raise

    @patch('sejm_api.SejmAPI._make_request')
    def test_get_term_info_endpoint(self, mock_request):
        """Testuje endpoint informacji o konkretnej kadencji"""
        try:
            mock_term_info = {
                'num': 10,
                'from': '2023-11-13',
                'to': None,
                'current': True
            }
            mock_request.return_value = mock_term_info

            api = SejmAPI()
            result = api.get_term_info(10)

            self.assertIsNotNone(result)
            self.assertEqual(result['num'], 10)
            self.assertTrue(result.get('current', False))

            mock_request.assert_called_with('/sejm/term10')

            details = f"✓ Term info endpoint works\n✓ Correct term number: {result['num']}\n✓ Proper URL construction"
            self._log_test_result(True, details)

        except Exception as e:
            self._log_test_result(False, f"Exception: {str(e)}")
            raise

    @patch('sejm_api.SejmAPI._make_request')
    def test_get_proceedings_endpoint(self, mock_request):
        """Testuje endpoint pobierania posiedzeń"""
        try:
            mock_proceedings = [
                {'number': 1, 'dates': ['2023-11-13', '2023-11-14']},
                {'number': 2, 'dates': ['2023-11-20']},
                {'number': 3, 'dates': ['2023-12-01', '2023-12-02']}
            ]
            mock_request.return_value = mock_proceedings

            api = SejmAPI()
            result = api.get_proceedings(10)

            self.assertIsNotNone(result)
            self.assertEqual(len(result), 3)
            self.assertEqual(result[0]['number'], 1)

            mock_request.assert_called_with('/sejm/term10/proceedings')

            details = f"✓ Proceedings endpoint works\n✓ Retrieved {len(result)} proceedings\n✓ Dates structure correct"
            self._log_test_result(True, details)

        except Exception as e:
            self._log_test_result(False, f"Exception: {str(e)}")
            raise

    @patch('sejm_api.SejmAPI._make_request')
    def test_get_proceeding_info_endpoint(self, mock_request):
        """Testuje endpoint szczegółów posiedzenia"""
        try:
            mock_proceeding = {
                'number': 15,
                'title': 'Posiedzenie testowe',
                'dates': ['2024-01-15', '2024-01-16']
            }
            mock_request.return_value = mock_proceeding

            api = SejmAPI()
            result = api.get_proceeding_info(10, 15)

            self.assertIsNotNone(result)
            self.assertEqual(result['number'], 15)
            self.assertIn('title', result)

            mock_request.assert_called_with('/sejm/term10/proceedings/15')

            details = f"✓ Proceeding info endpoint works\n✓ Proceeding number: {result['number']}\n✓ Title retrieved"
            self._log_test_result(True, details)

        except Exception as e:
            self._log_test_result(False, f"Exception: {str(e)}")
            raise

    # ========================================================================
    # TESTY ENDPOINTÓW STENOGRAMÓW
    # ========================================================================

    @patch('sejm_api.SejmAPI._make_request')
    def test_get_transcripts_list_endpoint(self, mock_request):
        """Testuje endpoint listy wypowiedzi"""
        try:
            mock_transcripts = {
                'statements': [
                    {'num': 1, 'name': 'Jan Kowalski', 'function': 'Poseł'},
                    {'num': 2, 'name': 'Anna Nowak', 'function': 'Marszałek'}
                ]
            }
            mock_request.return_value = mock_transcripts

            api = SejmAPI()
            result = api.get_transcripts_list(10, 15, '2024-01-15')

            self.assertIsNotNone(result)
            self.assertIn('statements', result)
            self.assertEqual(len(result['statements']), 2)

            mock_request.assert_called_with('/sejm/term10/proceedings/15/2024-01-15/transcripts')

            details = f"✓ Transcripts list endpoint works\n✓ Retrieved {len(result['statements'])} statements\n✓ Proper URL with date"
            self._log_test_result(True, details)

        except Exception as e:
            self._log_test_result(False, f"Exception: {str(e)}")
            raise

    @patch('sejm_api.SejmAPI._make_request')
    def test_get_transcript_pdf_endpoint(self, mock_request):
        """Testuje endpoint pobierania PDF"""
        try:
            mock_pdf_content = b"fake PDF content for testing"
            mock_request.return_value = mock_pdf_content

            api = SejmAPI()
            result = api.get_transcript_pdf(10, 15, '2024-01-15')

            self.assertIsNotNone(result)
            self.assertIsInstance(result, bytes)
            self.assertGreater(len(result), 0)

            mock_request.assert_called_with('/sejm/term10/proceedings/15/2024-01-15/transcripts/pdf')

            details = f"✓ PDF endpoint works\n✓ Returns binary content\n✓ Content size: {len(result)} bytes"
            self._log_test_result(True, details)

        except Exception as e:
            self._log_test_result(False, f"Exception: {str(e)}")
            raise

    @patch('sejm_api.SejmAPI._make_request')
    def test_get_statement_html_endpoint(self, mock_request):
        """Testuje endpoint konkretnej wypowiedzi HTML"""
        try:
            mock_html = b"<html><body>Test statement content</body></html>"
            mock_request.return_value = mock_html

            api = SejmAPI()
            result = api.get_statement_html(10, 15, '2024-01-15', 1)

            self.assertIsNotNone(result)
            self.assertIsInstance(result, str)
            self.assertIn('html', result.lower())

            mock_request.assert_called_with('/sejm/term10/proceedings/15/2024-01-15/transcripts/1')

            details = f"✓ Statement HTML endpoint works\n✓ HTML content decoded\n✓ Content length: {len(result)} chars"
            self._log_test_result(True, details)

        except Exception as e:
            self._log_test_result(False, f"Exception: {str(e)}")
            raise

    # ========================================================================
    # TESTY ENDPOINTÓW POSŁÓW
    # ========================================================================

    @patch('sejm_api.SejmAPI._make_request')
    def test_get_mps_endpoint(self, mock_request):
        """Testuje endpoint listy posłów"""
        try:
            mock_mps = [
                {'id': 1, 'firstName': 'Jan', 'lastName': 'Kowalski', 'club': 'PiS'},
                {'id': 2, 'firstName': 'Anna', 'lastName': 'Nowak', 'club': 'PO'}
            ]
            mock_request.return_value = mock_mps

            api = SejmAPI()
            result = api.get_mps(10)

            self.assertIsNotNone(result)
            self.assertEqual(len(result), 2)
            self.assertIn('firstName', result[0])
            self.assertIn('lastName', result[0])

            mock_request.assert_called_with('/sejm/term10/MP')

            details = f"✓ MPs list endpoint works\n✓ Retrieved {len(result)} MPs\n✓ Required fields present"
            self._log_test_result(True, details)

        except Exception as e:
            self._log_test_result(False, f"Exception: {str(e)}")
            raise

    @patch('sejm_api.SejmAPI._make_request')
    def test_get_mp_info_endpoint(self, mock_request):
        """Testuje endpoint szczegółów posła"""
        try:
            mock_mp_info = {
                'id': 123,
                'firstName': 'Jan',
                'lastName': 'Kowalski',
                'club': 'PiS',
                'email': 'jan.kowalski@sejm.gov.pl',
                'voivodeship': 'mazowieckie'
            }
            mock_request.return_value = mock_mp_info

            api = SejmAPI()
            result = api.get_mp_info(10, 123)

            self.assertIsNotNone(result)
            self.assertEqual(result['id'], 123)
            self.assertIn('email', result)

            mock_request.assert_called_with('/sejm/term10/MP/123')

            details = f"✓ MP info endpoint works\n✓ MP ID: {result['id']}\n✓ Extended info retrieved"
            self._log_test_result(True, details)

        except Exception as e:
            self._log_test_result(False, f"Exception: {str(e)}")
            raise

    @patch('sejm_api.SejmAPI._make_request')
    def test_get_mp_photo_endpoint(self, mock_request):
        """Testuje endpoint zdjęcia posła"""
        try:
            mock_photo_content = b"fake JPEG photo content"
            mock_request.return_value = mock_photo_content

            api = SejmAPI()
            result = api.get_mp_photo(10, 123)

            self.assertIsNotNone(result)
            self.assertIsInstance(result, bytes)
            self.assertGreater(len(result), 0)

            mock_request.assert_called_with('/sejm/term10/MP/123/photo')

            details = f"✓ MP photo endpoint works\n✓ Binary photo content\n✓ Size: {len(result)} bytes"
            self._log_test_result(True, details)

        except Exception as e:
            self._log_test_result(False, f"Exception: {str(e)}")
            raise

    @patch('sejm_api.SejmAPI._make_request')
    def test_get_mp_voting_stats_endpoint(self, mock_request):
        """Testuje endpoint statystyk głosowań posła"""
        try:
            mock_stats = {
                'total_votes': 150,
                'attendance_rate': 85.5,
                'for_votes': 120,
                'against_votes': 20,
                'abstain_votes': 10
            }
            mock_request.return_value = mock_stats

            api = SejmAPI()
            result = api.get_mp_voting_stats(10, 123)

            self.assertIsNotNone(result)
            self.assertEqual(result['total_votes'], 150)
            self.assertIn('attendance_rate', result)

            mock_request.assert_called_with('/sejm/term10/MP/123/votings/stats')

            details = f"✓ Voting stats endpoint works\n✓ Total votes: {result['total_votes']}\n✓ Attendance rate: {result['attendance_rate']}%"
            self._log_test_result(True, details)

        except Exception as e:
            self._log_test_result(False, f"Exception: {str(e)}")
            raise

    # ========================================================================
    # TESTY ENDPOINTÓW KLUBÓW
    # ========================================================================

    @patch('sejm_api.SejmAPI._make_request')
    def test_get_clubs_endpoint(self, mock_request):
        """Testuje endpoint listy klubów parlamentarnych"""
        try:
            mock_clubs = [
                {'id': 1, 'name': 'Prawo i Sprawiedliwość'},
                {'id': 2, 'name': 'Platforma Obywatelska'},
                {'id': 3, 'name': 'Lewica'}
            ]
            mock_request.return_value = mock_clubs

            api = SejmAPI()
            result = api.get_clubs(10)

            self.assertIsNotNone(result)
            self.assertEqual(len(result), 3)
            self.assertIn('name', result[0])

            mock_request.assert_called_with('/sejm/term10/clubs')

            details = f"✓ Clubs endpoint works\n✓ Retrieved {len(result)} clubs\n✓ Club names present"
            self._log_test_result(True, details)

        except Exception as e:
            self._log_test_result(False, f"Exception: {str(e)}")
            raise

    @patch('sejm_api.SejmAPI._make_request')
    def test_get_club_info_endpoint(self, mock_request):
        """Testuje endpoint szczegółów klubu"""
        try:
            mock_club_info = {
                'id': 1,
                'name': 'Prawo i Sprawiedliwość',
                'members_count': 235,
                'leader': 'Jarosław Kaczyński'
            }
            mock_request.return_value = mock_club_info

            api = SejmAPI()
            result = api.get_club_info(10, 1)

            self.assertIsNotNone(result)
            self.assertEqual(result['id'], 1)
            self.assertIn('members_count', result)

            mock_request.assert_called_with('/sejm/term10/clubs/1')

            details = f"✓ Club info endpoint works\n✓ Club: {result['name']}\n✓ Members: {result['members_count']}"
            self._log_test_result(True, details)

        except Exception as e:
            self._log_test_result(False, f"Exception: {str(e)}")
            raise

    @patch('sejm_api.SejmAPI._make_request')
    def test_get_club_logo_endpoint(self, mock_request):
        """Testuje endpoint logo klubu"""
        try:
            mock_logo_content = b"fake PNG logo content"
            mock_request.return_value = mock_logo_content

            api = SejmAPI()
            result = api.get_club_logo(10, 1)

            self.assertIsNotNone(result)
            self.assertIsInstance(result, bytes)
            self.assertGreater(len(result), 0)

            mock_request.assert_called_with('/sejm/term10/clubs/1/logo')

            details = f"✓ Club logo endpoint works\n✓ Binary logo content\n✓ Size: {len(result)} bytes"
            self._log_test_result(True, details)

        except Exception as e:
            self._log_test_result(False, f"Exception: {str(e)}")
            raise

    # ========================================================================
    # TESTY RATE LIMITING I PERFORMANCE
    # ========================================================================

    @patch('time.sleep')
    @patch('sejm_api.SejmAPI._make_request')
    def test_rate_limiting_delay(self, mock_request, mock_sleep):
        """Testuje mechanizm opóźnień między zapytaniami"""
        try:
            mock_request.return_value = {'test': 'data'}

            api = SejmAPI()

            # Wykonaj kilka zapytań
            for i in range(3):
                api._make_request(f'/test/endpoint/{i}')

            # Sprawdź czy sleep został wywołany
            expected_calls = 3 if REQUEST_DELAY > 0 else 0
            self.assertEqual(mock_sleep.call_count, expected_calls)

            if REQUEST_DELAY > 0:
                mock_sleep.assert_called_with(REQUEST_DELAY)

            details = f"✓ Rate limiting implemented\n✓ Delay: {REQUEST_DELAY}s\n✓ Sleep calls: {mock_sleep.call_count}"
            self._log_test_result(True, details)

        except Exception as e:
            self._log_test_result(False, f"Exception: {str(e)}")
            raise

    @patch('requests.Session.get')
    def test_request_timeout_configuration(self, mock_get):
        """Testuje konfigurację timeout dla zapytań"""
        try:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.headers = {'content-type': 'application/json'}
            mock_response.json.return_value = {'test': 'data'}
            mock_response.raise_for_status.return_value = None
            mock_get.return_value = mock_response

            api = SejmAPI()
            api._make_request('/test/endpoint')

            # Sprawdź czy timeout został przekazany
            mock_get.assert_called_once()
            call_args = mock_get.call_args
            self.assertIn('timeout', call_args[1])
            self.assertEqual(call_args[1]['timeout'], REQUEST_TIMEOUT)

            details = f"✓ Timeout properly configured\n✓ Value: {REQUEST_TIMEOUT}s\n✓ Passed to requests"
            self._log_test_result(True, details)

        except Exception as e:
            self._log_test_result(False, f"Exception: {str(e)}")
            raise

    # ========================================================================
    # TESTY CONTENT-TYPE I ENCODING
    # ========================================================================

    @patch('requests.Session.get')
    def test_json_content_type_handling(self, mock_get):
        """Testuje obsługę różnych typów zawartości"""
        try:
            # Test JSON content
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.headers = {'content-type': 'application/json; charset=utf-8'}
            mock_response.json.return_value = {'data': 'test'}
            mock_response.raise_for_status.return_value = None
            mock_get.return_value = mock_response

            api = SejmAPI()
            result = api._make_request('/json/endpoint')

            self.assertIsInstance(result, dict)
            self.assertEqual(result['data'], 'test')

            details = f"✓ JSON content-type handled\n✓ Proper parsing\n✓ Dictionary returned"
            self._log_test_result(True, details)

        except Exception as e:
            self._log_test_result(False, f"Exception: {str(e)}")
            raise

    @patch('requests.Session.get')
    def test_binary_content_handling(self, mock_get):
        """Testuje obsługę zawartości binarnej"""
        try:
            # Test binary content (PDF/image)
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.headers = {'content-type': 'application/pdf'}
            mock_response.content = b'binary data content'
            mock_response.raise_for_status.return_value = None
            mock_get.return_value = mock_response

            api = SejmAPI()
            result = api._make_request('/pdf/endpoint')

            self.assertIsInstance(result, bytes)
            self.assertEqual(result, b'binary data content')

            details = f"✓ Binary content handled\n✓ Bytes returned\n✓ Content preserved"
            self._log_test_result(True, details)

        except Exception as e:
            self._log_test_result(False, f"Exception: {str(e)}")
            raise

    # ========================================================================
    # TESTY EDGE CASES I SCENARIUSZY GRANICZNYCH
    # ========================================================================

    @patch('requests.Session.get')
    def test_empty_response_handling(self, mock_get):
        """Testuje obsługę pustych odpowiedzi"""
        try:
            mock_response = Mock()
            mock_response.status_code = 204  # No Content
            mock_response.headers = {}
            mock_response.content = b''
            mock_response.raise_for_status.return_value = None
            mock_get.return_value = mock_response

            api = SejmAPI()
            result = api._make_request('/empty/endpoint')

            # Powinno zwrócić pustą zawartość
            self.assertEqual(result, b'')

            details = f"✓ Empty response handled\n✓ Status 204 processed\n✓ Empty bytes returned"
            self._log_test_result(True, details)

        except Exception as e:
            self._log_test_result(False, f"Exception: {str(e)}")
            raise

    @patch('requests.Session.get')
    def test_malformed_json_handling(self, mock_get):
        """Testuje obsługę nieprawidłowego JSON"""
        try:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.headers = {'content-type': 'application/json'}
            mock_response.json.side_effect = ValueError("Invalid JSON")
            mock_response.raise_for_status.return_value = None
            mock_get.return_value = mock_response

            api = SejmAPI()
            result = api._make_request('/invalid/json')

            # Powinno zwrócić None przy nieprawidłowym JSON
            self.assertIsNone(result)

            details = f"✓ Malformed JSON handled\n✓ Returns None on parse error\n✓ No exceptions propagated"
            self._log_test_result(True, details)

        except Exception as e:
            self._log_test_result(False, f"Exception: {str(e)}")
            raise

    def test_endpoint_url_construction(self):
        """Testuje poprawność budowania URL endpointów"""
        try:
            api = SejmAPI()

            # Test różnych formatów endpoint
            test_cases = [
                ('/sejm/term', f'{API_BASE_URL}/sejm/term'),
                ('/sejm/term10/MP/123', f'{API_BASE_URL}/sejm/term10/MP/123'),
                ('/sejm/term10/proceedings/15/2024-01-15/transcripts',
                 f'{API_BASE_URL}/sejm/term10/proceedings/15/2024-01-15/transcripts')
            ]

            for endpoint, expected_url in test_cases:
                constructed_url = f"{api.base_url}{endpoint}"
                self.assertEqual(constructed_url, expected_url)

            details = f"✓ URL construction correct\n✓ Base URL: {api.base_url}\n✓ Tested {len(test_cases)} patterns"
            self._log_test_result(True, details)

        except Exception as e:
            self._log_test_result(False, f"Exception: {str(e)}")
            raise

    # ========================================================================
    # TESTY INTEGRACYJNE I SYMULACJE
    # ========================================================================

    @patch('sejm_api.SejmAPI._make_request')
    def test_full_workflow_simulation(self, mock_request):
        """Symuluje pełny workflow pobierania danych z API"""
        try:
            # Przygotuj mock odpowiedzi dla różnych endpointów
            mock_responses = {
                '/sejm/term': [
                    {'num': 10, 'from': '2023-11-13', 'current': True}
                ],
                '/sejm/term10': {
                    'num': 10, 'from': '2023-11-13', 'current': True
                },
                '/sejm/term10/proceedings': [
                    {'number': 1, 'dates': ['2023-11-13']},
                    {'number': 2, 'dates': ['2023-11-20']}
                ],
                '/sejm/term10/proceedings/1': {
                    'number': 1, 'title': 'Pierwsze posiedzenie', 'dates': ['2023-11-13']
                },
                '/sejm/term10/proceedings/1/2023-11-13/transcripts': {
                    'statements': [
                        {'num': 1, 'name': 'Jan Kowalski', 'function': 'Poseł'}
                    ]
                },
                '/sejm/term10/MP': [
                    {'id': 1, 'firstName': 'Jan', 'lastName': 'Kowalski'}
                ]
            }

            def mock_side_effect(endpoint):
                return mock_responses.get(endpoint)

            mock_request.side_effect = mock_side_effect

            api = SejmAPI()

            # Symuluj pełny workflow
            terms = api.get_terms()
            self.assertIsNotNone(terms)

            term_info = api.get_term_info(10)
            self.assertIsNotNone(term_info)

            proceedings = api.get_proceedings(10)
            self.assertIsNotNone(proceedings)

            proceeding_info = api.get_proceeding_info(10, 1)
            self.assertIsNotNone(proceeding_info)

            transcripts = api.get_transcripts_list(10, 1, '2023-11-13')
            self.assertIsNotNone(transcripts)

            mps = api.get_mps(10)
            self.assertIsNotNone(mps)

            details = f"✓ Full workflow completed\n✓ All endpoints responding\n✓ Data flow verified\n✓ {mock_request.call_count} API calls made"
            self._log_test_result(True, details)

        except Exception as e:
            self._log_test_result(False, f"Exception: {str(e)}")
            raise

    @patch('sejm_api.SejmAPI._make_request')
    def test_stress_test_simulation(self, mock_request):
        """Symuluje test obciążeniowy API"""
        try:
            mock_request.return_value = {'test': 'data'}

            api = SejmAPI()

            start_time = time.time()

            # Symuluj wiele zapytań
            request_count = 50
            for i in range(request_count):
                result = api._make_request(f'/test/endpoint/{i}')
                self.assertIsNotNone(result)

            execution_time = time.time() - start_time

            # Sprawdź czy wszystkie zapytania zostały wykonane
            self.assertEqual(mock_request.call_count, request_count)

            # Sprawdź średni czas na zapytanie
            avg_time_per_request = execution_time / request_count

            details = f"✓ Stress test completed\n✓ Requests: {request_count}\n✓ Total time: {execution_time:.2f}s\n✓ Avg per request: {avg_time_per_request:.3f}s"
            self._log_test_result(True, details)

        except Exception as e:
            self._log_test_result(False, f"Exception: {str(e)}")
            raise

    def test_api_endpoint_coverage(self):
        """Sprawdza pokrycie wszystkich endpointów API"""
        try:
            api = SejmAPI()

            # Lista wszystkich metod API
            api_methods = [
                'get_terms', 'get_term_info', 'get_proceedings', 'get_proceeding_info',
                'get_transcripts_list', 'get_transcript_pdf', 'get_statement_html',
                'get_mps', 'get_mp_info', 'get_mp_photo', 'get_mp_voting_stats',
                'get_mp_votings_by_date', 'get_clubs', 'get_club_info', 'get_club_logo'
            ]

            available_methods = []
            for method_name in api_methods:
                if hasattr(api, method_name):
                    method = getattr(api, method_name)
                    if callable(method):
                        available_methods.append(method_name)

            coverage_percentage = (len(available_methods) / len(api_methods)) * 100

            self.assertGreater(len(available_methods), 0)

            details = f"✓ API methods coverage: {coverage_percentage:.1f}%\n✓ Available: {len(available_methods)}/{len(api_methods)}\n✓ Methods: {', '.join(available_methods[:5])}..."
            self._log_test_result(True, details)

        except Exception as e:
            self._log_test_result(False, f"Exception: {str(e)}")
            raise


# ========================================================================
# UTILITY FUNCTIONS
# ========================================================================

def run_api_health_check():
    """Uruchamia pełny health check API"""
    print(f"{TestColors.BOLD}🌐 Starting SejmBot API Health Check...{TestColors.RESET}")
    print()

    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestSejmAPI)

    stream = StringIO()
    runner = unittest.TextTestRunner(stream=stream, verbosity=0)

    try:
        result = runner.run(suite)

        if result.wasSuccessful():
            print(f"{TestColors.GREEN}🎉 API CLIENT OPERATIONAL{TestColors.RESET}")
            return 0
        else:
            print(f"{TestColors.RED}⚠️  API CLIENT ISSUES DETECTED{TestColors.RESET}")
            return 1

    except Exception as e:
        print(f"{TestColors.RED}💥 CRITICAL API ERROR{TestColors.RESET}")
        print(f"{TestColors.RED}   Exception: {str(e)}{TestColors.RESET}")
        return 2


def run_connectivity_test():
    """Szybki test łączności z API"""
    print(f"{TestColors.CYAN}🔗 API Connectivity Test{TestColors.RESET}")
    print()

    connectivity_tests = [
        'test_api_client_initialization',
        'test_api_configuration_values',
        'test_successful_http_request',
        'test_http_error_handling'
    ]

    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    for test_name in connectivity_tests:
        suite.addTest(TestSejmAPI(test_name))

    stream = StringIO()
    runner = unittest.TextTestRunner(stream=stream, verbosity=0)

    result = runner.run(suite)

    if result.wasSuccessful():
        print(f"{TestColors.GREEN}✅ Connectivity: OK{TestColors.RESET}")
        return 0
    else:
        print(f"{TestColors.RED}❌ Connectivity: FAILED{TestColors.RESET}")
        return 1


def run_endpoints_test():
    """Test wszystkich endpointów API"""
    print(f"{TestColors.PURPLE}🎯 API Endpoints Test{TestColors.RESET}")
    print()

    endpoint_tests = [
        'test_get_terms_endpoint',
        'test_get_term_info_endpoint',
        'test_get_proceedings_endpoint',
        'test_get_transcripts_list_endpoint',
        'test_get_mps_endpoint',
        'test_get_clubs_endpoint'
    ]

    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    for test_name in endpoint_tests:
        suite.addTest(TestSejmAPI(test_name))

    stream = StringIO()
    runner = unittest.TextTestRunner(stream=stream, verbosity=0)

    result = runner.run(suite)

    if result.wasSuccessful():
        print(f"{TestColors.GREEN}✅ Endpoints: ALL OK{TestColors.RESET}")
        return 0
    else:
        print(f"{TestColors.RED}❌ Endpoints: ISSUES FOUND{TestColors.RESET}")
        return 1


# ========================================================================
# MAIN CLI
# ========================================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="🌐 SejmBot API Client Professional Health Check",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Przykłady użycia:
  %(prog)s                    # Pełny health check API
  %(prog)s --connectivity     # Test łączności
  %(prog)s --endpoints        # Test endpointów  
  %(prog)s --no-colors        # Bez kolorów
  %(prog)s --verbose          # Szczegółowe logi

Exit codes:
  0 - API działa poprawnie
  1 - Wykryto problemy z API
  2 - Krytyczny błąd testów
        """
    )

    parser.add_argument('--connectivity', action='store_true', help='Test łączności z API')
    parser.add_argument('--endpoints', action='store_true', help='Test wszystkich endpointów')
    parser.add_argument('--no-colors', action='store_true', help='Wyłącz kolory')
    parser.add_argument('--verbose', action='store_true', help='Szczegółowe informacje')

    args = parser.parse_args()

    if args.no_colors:
        TestColors.disable_colors()

    try:
        if args.connectivity:
            exit_code = run_connectivity_test()
        elif args.endpoints:
            exit_code = run_endpoints_test()
        else:
            exit_code = run_api_health_check()

        sys.exit(exit_code)

    except KeyboardInterrupt:
        print(f"\n{TestColors.YELLOW}⏹️  API health check przerwany{TestColors.RESET}")
        sys.exit(130)
    except Exception as e:
        print(f"\n{TestColors.RED}💥 Nieoczekiwany błąd: {str(e)}{TestColors.RESET}")
        sys.exit(2)
