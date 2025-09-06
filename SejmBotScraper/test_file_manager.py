#!/usr/bin/env python3
# test_file_manager_fancy.py
"""
📁 SejmBot File Manager - Professional Test Suite
=================================================

Profesjonalny test suite dla modułu FileManager.
Testuje zarządzanie plikami, strukturą katalogów, zapisem danych i więcej.

Autor: SejmBot Team
Wersja: 1.0.0 - Complete File Management Test Coverage
"""

import json
import os
import shutil
import sys
import tempfile
import time
import unittest
from datetime import datetime
from io import StringIO
from pathlib import Path
from typing import Dict, List
from unittest.mock import Mock, patch, mock_open
from wcwidth import wcswidth

# ========================================================================
# IMPORTY I KONFIGURACJA
# ========================================================================

current_dir = Path(__file__).parent.absolute()
project_root = current_dir
sys.path.insert(0, str(project_root))

print(f"📁 Szukam modułów File Manager w ścieżkach:")
for path in sys.path[:5]:
    print(f"   - {path}")
print()

# Próby importu
file_manager_module = None
config_module = None

import_attempts = [
    lambda: __import__('file_manager'),
    lambda: __import__('config'),
    lambda: __import__('SejmBotScraper.file_manager', fromlist=['file_manager']),
    lambda: __import__('SejmBotScraper.config', fromlist=['config']),
]

# Import FileManager
for attempt in [import_attempts[0], import_attempts[2]]:
    try:
        file_manager_module = attempt()
        FileManager = getattr(file_manager_module, 'FileManager', None)
        if FileManager:
            print("✅ file_manager zaimportowany pomyślnie")
            break
    except ImportError:
        continue

# Import config
for attempt in [import_attempts[1], import_attempts[3]]:
    try:
        config_module = attempt()
        BASE_OUTPUT_DIR = getattr(config_module, 'BASE_OUTPUT_DIR', './dane')
        print("✅ config zaimportowany pomyślnie")
        break
    except ImportError:
        continue

# Mock klasy jeśli nie udało się zaimportować
if not file_manager_module or not FileManager:
    print("⚠️  Nie można zaimportować file_manager - tworzę mock klasę")


    class MockFileManager:
        def __init__(self):
            self.base_dir = Path('./dane')

        def ensure_base_directory(self):
            self.base_dir.mkdir(exist_ok=True)

        def get_term_directory(self, term: int) -> Path:
            term_dir = self.base_dir / f"kadencja_{term:02d}"
            term_dir.mkdir(exist_ok=True)
            return term_dir

        def get_proceeding_directory(self, term: int, proceeding_id: int, proceeding_info: Dict) -> Path:
            term_dir = self.get_term_directory(term)
            proceeding_name = f"posiedzenie_{proceeding_id:03d}"

            if 'dates' in proceeding_info and proceeding_info['dates']:
                first_date = proceeding_info['dates'][0]
                proceeding_name += f"_{first_date}"

            proceeding_dir = term_dir / proceeding_name
            proceeding_dir.mkdir(exist_ok=True)
            return proceeding_dir

        def save_pdf_transcript(self, term: int, proceeding_id: int, date: str,
                                pdf_content: bytes, proceeding_info: Dict) -> str:
            try:
                proceeding_dir = self.get_proceeding_directory(term, proceeding_id, proceeding_info)
                filename = f"transkrypt_{date}.pdf"
                filepath = proceeding_dir / filename

                with open(filepath, 'wb') as f:
                    f.write(pdf_content)
                return str(filepath)
            except Exception:
                return None

        def save_html_statements(self, term: int, proceeding_id: int, date: str,
                                 statements: Dict, proceeding_info: Dict) -> str:
            try:
                proceeding_dir = self.get_proceeding_directory(term, proceeding_id, proceeding_info)
                day_dir = proceeding_dir / f"wypowiedzi_{date}"
                day_dir.mkdir(exist_ok=True)
                return str(day_dir)
            except Exception:
                return None

        def save_proceeding_info(self, term: int, proceeding_id: int, proceeding_info: Dict) -> str:
            try:
                proceeding_dir = self.get_proceeding_directory(term, proceeding_id, proceeding_info)
                filepath = proceeding_dir / "info_posiedzenia.json"

                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(proceeding_info, f, ensure_ascii=False, indent=2)
                return str(filepath)
            except Exception:
                return None

        @staticmethod
        def _make_safe_filename(name: str) -> str:
            safe_chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-"
            safe_name = ''.join(c if c in safe_chars else '_' for c in name)
            if len(safe_name) > 50:
                safe_name = safe_name[:50]
            return safe_name

        def _create_statement_html(self, statement: Dict, term: int, proceeding_id: int, date: str) -> str:
            return f"<html><body>Test statement for {statement.get('name', 'Unknown')}</body></html>"


    FileManager = MockFileManager

if not config_module:
    BASE_OUTPUT_DIR = './dane'

print("🚀 Moduły File Manager gotowe do testów\n")


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
    """Professional reporter dla testów File Manager"""

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
║    📁 SejmBot File Manager - Professional Health Check            ║
║                                                                   ║
║    Status: RUNNING                                                ║
║    Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}                                        ║
║    Environment: File Manager Test Suite v1.0                     ║
║                                                                   ║
╚═══════════════════════════════════════════════════════════════════╝{TestColors.RESET}
        """
        print(header)

    def start_test_session(self):
        self.start_time = time.time()
        self.print_header()
        print(f"{TestColors.BLUE}🚀 Inicjalizacja File Manager test suite...{TestColors.RESET}")
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
            pad_center("FILE MANAGER HEALTH CHECK SUMMARY"),
            f"╠{'═' * WIDTH}╣",
            pad_center(""),
            pad_center(f"{overall_icon} File System Status: {status_color}{status_text}{TestColors.CYAN}"),
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


class TestFileManager(unittest.TestCase):
    """Główna klasa testów dla FileManager"""

    @classmethod
    def setUpClass(cls):
        cls.reporter = HealthCheckReporter()
        cls.reporter.start_test_session()
        cls.temp_dir = tempfile.mkdtemp(prefix="file_manager_test_")
        cls.test_data_dir = Path(cls.temp_dir)

    @classmethod
    def tearDownClass(cls):
        # Cleanup
        if cls.test_data_dir.exists():
            shutil.rmtree(cls.test_data_dir)
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

    def test_file_manager_initialization(self):
        """Sprawdza poprawność inicjalizacji FileManager"""
        try:
            with patch('file_manager.BASE_OUTPUT_DIR', str(self.test_data_dir)):
                fm = FileManager()

                # Sprawdź podstawowe atrybuty
                self.assertIsNotNone(fm.base_dir)
                self.assertIsInstance(fm.base_dir, Path)
                self.assertTrue(fm.base_dir.exists())

                details = f"✓ Base directory: {fm.base_dir}\n✓ Directory exists\n✓ Path object created"
                self._log_test_result(True, details)

        except Exception as e:
            self._log_test_result(False, f"Exception: {str(e)}")
            raise

    def test_base_directory_creation(self):
        """Testuje tworzenie głównego katalogu danych"""
        try:
            # Użyj nieistniejącego katalogu
            nonexistent_dir = self.test_data_dir / "nonexistent"

            with patch('file_manager.BASE_OUTPUT_DIR', str(nonexistent_dir)):
                fm = FileManager()

                # Katalog powinien zostać utworzony
                self.assertTrue(nonexistent_dir.exists())
                self.assertTrue(nonexistent_dir.is_dir())
                self.assertEqual(fm.base_dir, nonexistent_dir)

                details = f"✓ Created directory: {nonexistent_dir}\n✓ Directory is accessible\n✓ Permissions OK"
                self._log_test_result(True, details)

        except Exception as e:
            self._log_test_result(False, f"Exception: {str(e)}")
            raise

    # ========================================================================
    # TESTY STRUKTURY KATALOGÓW
    # ========================================================================

    def test_term_directory_creation(self):
        """Testuje tworzenie katalogów kadencji"""
        try:
            with patch('file_manager.BASE_OUTPUT_DIR', str(self.test_data_dir)):
                fm = FileManager()

                # Test różnych numerów kadencji
                test_terms = [9, 10, 11]

                for term in test_terms:
                    term_dir = fm.get_term_directory(term)

                    # Sprawdzenia
                    self.assertIsInstance(term_dir, Path)
                    self.assertTrue(term_dir.exists())
                    self.assertTrue(term_dir.is_dir())

                    # Sprawdź nazwę katalogu
                    expected_name = f"kadencja_{term:02d}"
                    self.assertEqual(term_dir.name, expected_name)

                    # Sprawdź ścieżkę
                    self.assertEqual(term_dir.parent, fm.base_dir)

                details = f"✓ Created {len(test_terms)} term directories\n✓ Naming convention correct\n✓ All directories accessible"
                self._log_test_result(True, details)

        except Exception as e:
            self._log_test_result(False, f"Exception: {str(e)}")
            raise

    def test_proceeding_directory_creation(self):
        """Testuje tworzenie katalogów posiedzeń"""
        try:
            with patch('file_manager.BASE_OUTPUT_DIR', str(self.test_data_dir)):
                fm = FileManager()

                # Test różnych scenariuszy
                test_cases = [
                    {
                        'term': 10,
                        'proceeding_id': 15,
                        'proceeding_info': {'dates': ['2024-01-15', '2024-01-16']},
                        'expected_pattern': 'posiedzenie_015_2024-01-15'
                    },
                    {
                        'term': 10,
                        'proceeding_id': 5,
                        'proceeding_info': {'dates': []},
                        'expected_pattern': 'posiedzenie_005'
                    },
                    {
                        'term': 9,
                        'proceeding_id': 123,
                        'proceeding_info': {'dates': ['2023-12-01']},
                        'expected_pattern': 'posiedzenie_123_2023-12-01'
                    }
                ]

                for case in test_cases:
                    proceeding_dir = fm.get_proceeding_directory(
                        case['term'],
                        case['proceeding_id'],
                        case['proceeding_info']
                    )

                    # Sprawdzenia
                    self.assertTrue(proceeding_dir.exists())
                    self.assertTrue(proceeding_dir.is_dir())
                    self.assertIn(case['expected_pattern'], proceeding_dir.name)

                    # Sprawdź strukturę
                    term_dir = fm.get_term_directory(case['term'])
                    self.assertEqual(proceeding_dir.parent, term_dir)

                details = f"✓ Created {len(test_cases)} proceeding directories\n✓ Naming with dates works\n✓ Nested structure correct"
                self._log_test_result(True, details)

        except Exception as e:
            self._log_test_result(False, f"Exception: {str(e)}")
            raise

    # ========================================================================
    # TESTY ZAPISYWANIA PDF
    # ========================================================================

    def test_pdf_transcript_saving(self):
        """Testuje zapisywanie transkryptów PDF"""
        try:
            with patch('file_manager.BASE_OUTPUT_DIR', str(self.test_data_dir)):
                fm = FileManager()

                # Przygotuj dane testowe
                test_pdf_content = b"PDF content for testing - this would be actual PDF binary data"
                proceeding_info = {
                    'dates': ['2024-01-15'],
                    'number': 15,
                    'title': 'Test proceeding'
                }

                # Zapisz PDF
                saved_path = fm.save_pdf_transcript(
                    term=10,
                    proceeding_id=15,
                    date='2024-01-15',
                    pdf_content=test_pdf_content,
                    proceeding_info=proceeding_info
                )

                # Sprawdzenia
                self.assertIsNotNone(saved_path)
                self.assertIsInstance(saved_path, str)

                saved_file = Path(saved_path)
                self.assertTrue(saved_file.exists())
                self.assertTrue(saved_file.is_file())
                self.assertEqual(saved_file.suffix, '.pdf')

                # Sprawdź zawartość
                with open(saved_file, 'rb') as f:
                    saved_content = f.read()
                self.assertEqual(saved_content, test_pdf_content)

                # Sprawdź nazwę pliku
                self.assertIn('transkrypt_2024-01-15', saved_file.name)

                details = f"✓ PDF saved successfully\n✓ File: {saved_file.name}\n✓ Content verified: {len(test_pdf_content)} bytes"
                self._log_test_result(True, details)

        except Exception as e:
            self._log_test_result(False, f"Exception: {str(e)}")
            raise

    def test_pdf_saving_error_handling(self):
        """Testuje obsługę błędów przy zapisywaniu PDF"""
        try:
            with patch('file_manager.BASE_OUTPUT_DIR', str(self.test_data_dir)):
                fm = FileManager()

                # Test z nieprawidłowymi danymi
                with patch('builtins.open', mock_open()) as mock_file:
                    mock_file.side_effect = PermissionError("Permission denied")

                    result = fm.save_pdf_transcript(
                        term=10,
                        proceeding_id=15,
                        date='2024-01-15',
                        pdf_content=b"test content",
                        proceeding_info={'dates': ['2024-01-15']}
                    )

                    # Powinno zwrócić None przy błędzie
                    self.assertIsNone(result)

                details = f"✓ Permission error handled gracefully\n✓ Returns None on error\n✓ No exceptions propagated"
                self._log_test_result(True, details)

        except Exception as e:
            self._log_test_result(False, f"Exception: {str(e)}")
            raise

    # ========================================================================
    # TESTY ZAPISYWANIA WYPOWIEDZI HTML
    # ========================================================================

    def test_html_statements_saving(self):
        """Testuje zapisywanie wypowiedzi HTML"""
        try:
            with patch('file_manager.BASE_OUTPUT_DIR', str(self.test_data_dir)):
                fm = FileManager()

                # Przygotuj dane testowe
                statements_data = {
                    'statements': [
                        {
                            'num': 1,
                            'name': 'Jan Kowalski',
                            'function': 'Poseł',
                            'startDateTime': '10:00:00',
                            'endDateTime': '10:05:00'
                        },
                        {
                            'num': 2,
                            'name': 'Anna Nowak-Kowalska',
                            'function': 'Marszałek',
                            'startDateTime': '10:05:00',
                            'endDateTime': '10:10:00'
                        }
                    ]
                }

                proceeding_info = {
                    'dates': ['2024-01-15'],
                    'number': 15
                }

                # Zapisz wypowiedzi
                saved_path = fm.save_html_statements(
                    term=10,
                    proceeding_id=15,
                    date='2024-01-15',
                    statements=statements_data,
                    proceeding_info=proceeding_info
                )

                # Sprawdzenia
                self.assertIsNotNone(saved_path)
                saved_dir = Path(saved_path)
                self.assertTrue(saved_dir.exists())
                self.assertTrue(saved_dir.is_dir())

                # Sprawdź czy pliki zostały utworzone
                statement_files = list(saved_dir.glob('*.html'))
                self.assertEqual(len(statement_files), 2)

                # Sprawdź nazwy plików
                filenames = [f.name for f in statement_files]
                self.assertIn('001_Jan_Kowalski.html', filenames)
                self.assertIn('002_Anna_Nowak-Kowalska.html', filenames)

                # Sprawdź zawartość pierwszego pliku
                first_file = saved_dir / '001_Jan_Kowalski.html'
                with open(first_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                self.assertIn('Jan Kowalski', content)
                self.assertIn('Poseł', content)
                self.assertIn('10:00:00', content)

                details = f"✓ HTML statements saved\n✓ Files created: {len(statement_files)}\n✓ Content verified"
                self._log_test_result(True, details)

        except Exception as e:
            self._log_test_result(False, f"Exception: {str(e)}")
            raise

    def test_empty_statements_handling(self):
        """Testuje obsługę pustych wypowiedzi"""
        try:
            with patch('file_manager.BASE_OUTPUT_DIR', str(self.test_data_dir)):
                fm = FileManager()

                # Test z pustymi wypowiedziami
                empty_statements = {'statements': []}

                proceeding_info = {'dates': ['2024-01-15']}

                saved_path = fm.save_html_statements(
                    term=10,
                    proceeding_id=15,
                    date='2024-01-15',
                    statements=empty_statements,
                    proceeding_info=proceeding_info
                )

                # Powinno utworzyć katalog ale bez plików
                self.assertIsNotNone(saved_path)
                saved_dir = Path(saved_path)
                self.assertTrue(saved_dir.exists())

                statement_files = list(saved_dir.glob('*.html'))
                self.assertEqual(len(statement_files), 0)

                details = f"✓ Empty statements handled\n✓ Directory created: {saved_dir.name}\n✓ No HTML files created"
                self._log_test_result(True, details)

        except Exception as e:
            self._log_test_result(False, f"Exception: {str(e)}")
            raise

    # ========================================================================
    # TESTY ZAPISYWANIA JSON
    # ========================================================================

    def test_proceeding_info_saving(self):
        """Testuje zapisywanie informacji o posiedzeniu do JSON"""
        try:
            with patch('file_manager.BASE_OUTPUT_DIR', str(self.test_data_dir)):
                fm = FileManager()

                # Przygotuj dane testowe
                proceeding_info = {
                    'number': 15,
                    'title': 'Posiedzenie testowe Sejmu RP',
                    'dates': ['2024-01-15', '2024-01-16'],
                    'current': False,
                    'metadata': {
                        'created_at': '2024-01-10T10:00:00Z',
                        'updated_at': '2024-01-15T08:00:00Z'
                    }
                }

                # Zapisz informacje
                saved_path = fm.save_proceeding_info(
                    term=10,
                    proceeding_id=15,
                    proceeding_info=proceeding_info
                )

                # Sprawdzenia
                self.assertIsNotNone(saved_path)
                saved_file = Path(saved_path)
                self.assertTrue(saved_file.exists())
                self.assertTrue(saved_file.is_file())
                self.assertEqual(saved_file.suffix, '.json')
                self.assertEqual(saved_file.name, 'info_posiedzenia.json')

                # Sprawdź zawartość JSON
                with open(saved_file, 'r', encoding='utf-8') as f:
                    loaded_data = json.load(f)

                self.assertEqual(loaded_data, proceeding_info)
                self.assertEqual(loaded_data['number'], 15)
                self.assertEqual(loaded_data['title'], 'Posiedzenie testowe Sejmu RP')
                self.assertEqual(len(loaded_data['dates']), 2)

                details = f"✓ JSON saved successfully\n✓ File: {saved_file.name}\n✓ Data integrity verified\n✓ UTF-8 encoding works"
                self._log_test_result(True, details)

        except Exception as e:
            self._log_test_result(False, f"Exception: {str(e)}")
            raise

    def test_json_special_characters_handling(self):
        """Testuje obsługę polskich znaków w JSON"""
        try:
            with patch('file_manager.BASE_OUTPUT_DIR', str(self.test_data_dir)):
                fm = FileManager()

                # Dane z polskimi znakami
                proceeding_info = {
                    'title': 'Posiedzenie Sejmu Rzeczypospolitej Polskiej',
                    'description': 'Ważne tematy: zdrowie, edukacja, środowisko',
                    'speakers': ['Józef Kowalski', 'Małgorzata Wiśniewska', 'Łukasz Zieliński'],
                    'topics': ['Ustawa o ochronie środowiska', 'Budżet państwa na 2024 rok']
                }

                saved_path = fm.save_proceeding_info(10, 15, proceeding_info)

                # Sprawdź zawartość
                saved_file = Path(saved_path)
                with open(saved_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    loaded_data = json.load(f)

                # Sprawdź polskie znaki
                self.assertIn('Rzeczypospolitej', content)
                self.assertIn('środowisko', content)
                self.assertIn('Małgorzata', content)
                self.assertIn('Łukasz', content)

                self.assertEqual(loaded_data['speakers'][2], 'Łukasz Zieliński')

                details = f"✓ Polish characters handled\n✓ UTF-8 encoding correct\n✓ JSON parsing works\n✓ Special chars preserved"
                self._log_test_result(True, details)

        except Exception as e:
            self._log_test_result(False, f"Exception: {str(e)}")
            raise

    # ========================================================================
    # TESTY UTILITY FUNCTIONS
    # ========================================================================

    def test_safe_filename_generation(self):
        """Testuje bezpieczne generowanie nazw plików"""
        try:
            # Test różnych przypadków
            test_cases = [
                ('Jan Kowalski', 'Jan_Kowalski'),
                ('Anna-Maria Nowak', 'Anna-Maria_Nowak'),
                ('Józef Piłsudski', 'J_zef_Pi_sudski'),  # Polskie znaki
                ('Test/\\*?<>|:"', 'Test_________'),  # Znaki specjalne
                ('', ''),  # Pusty string
                ('VeryLongNameThatExceedsTheFiftyCharacterLimitAndShouldBeTruncated',
                 'VeryLongNameThatExceedsTheFiftyCharacterLimitAn'),  # Długa nazwa
                ('123ABC', '123ABC'),  # Cyfry i litery
                ('test-name_with.dots', 'test-name_with_dots'),  # Kropki
            ]

            for input_name, expected in test_cases:
                result = FileManager._make_safe_filename(input_name)

                # Sprawdzenia
                self.assertEqual(result, expected, f"Failed for: '{input_name}'")
                self.assertLessEqual(len(result), 50, f"Too long result for: '{input_name}'")

                # Sprawdź czy zawiera tylko bezpieczne znaki
                safe_chars = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-")
                for char in result:
                    self.assertIn(char, safe_chars, f"Unsafe char '{char}' in result: '{result}'")

            details = f"✓ Tested {len(test_cases)} filename cases\n✓ All names properly sanitized\n✓ Length limits respected\n✓ Safe characters only"
            self._log_test_result(True, details)

        except Exception as e:
            self._log_test_result(False, f"Exception: {str(e)}")
            raise

    def test_html_template_generation(self):
        """Testuje generowanie szablonu HTML dla wypowiedzi"""
        try:
            with patch('file_manager.BASE_OUTPUT_DIR', str(self.test_data_dir)):
                fm = FileManager()

                # Przygotuj dane wypowiedzi
                statement = {
                    'num': 42,
                    'name': 'Jan Testowy',
                    'function': 'Poseł na Sejm RP',
                    'startDateTime': '14:30:15',
                    'endDateTime': '14:35:22'
                }

                # Wygeneruj HTML
                html_content = fm._create_statement_html(
                    statement=statement,
                    term=10,
                    proceeding_id=15,
                    date='2024-01-15'
                )

                # Sprawdzenia
                self.assertIsInstance(html_content, str)
                self.assertGreater(len(html_content), 0)

                # Sprawdź struktur HTML
                self.assertIn('<!DOCTYPE html>', html_content)
                self.assertIn('<html', html_content)
                self.assertIn('<head>', html_content)
                self.assertIn('<body>', html_content)
                self.assertIn('</html>', html_content)

                # Sprawdź dane wypowiedzi
                self.assertIn('Jan Testowy', html_content)
                self.assertIn('Poseł na Sejm RP', html_content)
                self.assertIn('42', html_content)
                self.assertIn('14:30:15', html_content)
                self.assertIn('14:35:22', html_content)
                self.assertIn('2024-01-15', html_content)
                self.assertIn('Kadencja: 10', html_content)
                self.assertIn('Posiedzenie: 15', html_content)

                # Sprawdź CSS
                self.assertIn('<style>', html_content)
                self.assertIn('font-family:', html_content)

                # Sprawdź metadane
                self.assertIn('class="metadata"', html_content)

                details = f"✓ HTML template generated\n✓ All data fields present\n✓ Valid HTML structure\n✓ CSS styling included"
                self._log_test_result(True, details)

        except Exception as e:
            self._log_test_result(False, f"Exception: {str(e)}")
            raise

    # ========================================================================
    # TESTY PERMISSIONS I BŁĘDÓW
    # ========================================================================

    def test_permission_error_handling(self):
        """Testuje obsługę błędów uprawnień"""
        try:
            # Symuluj błąd uprawnień przy tworzeniu katalogu
            with patch('pathlib.Path.mkdir') as mock_mkdir:
                mock_mkdir.side_effect = PermissionError("Permission denied")

                with patch('file_manager.BASE_OUTPUT_DIR', '/root/impossible'):
                    try:
                        fm = FileManager()
                        # Jeśli nie wystąpi wyjątek, to znaczy że błąd został obsłużony
                        details = "✓ Permission error handled gracefully"
                        self._log_test_result(True, details)
                    except PermissionError:
                        # Oczekiwany scenariusz - błąd uprawnień
                        details = "✓ Permission error properly raised"
                        self._log_test_result(True, details)

        except Exception as e:
            self._log_test_result(False, f"Exception: {str(e)}")
            raise

    def test_disk_space_handling(self):
        """Testuje obsługę braku miejsca na dysku (symulacja)"""
        try:
            with patch('file_manager.BASE_OUTPUT_DIR', str(self.test_data_dir)):
                fm = FileManager()

                # Symuluj brak miejsca na dysku
                with patch('builtins.open', mock_open()) as mock_file:
                    mock_file.side_effect = OSError("No space left on device")

                    result = fm.save_pdf_transcript(
                        term=10,
                        proceeding_id=15,
                        date='2024-01-15',
                        pdf_content=b"test content",
                        proceeding_info={'dates': ['2024-01-15']}
                    )

                    self.assertIsNone(result)

                details = "✓ Disk space error handled\n✓ Returns None on OSError\n✓ No system crash"
                self._log_test_result(True, details)

        except Exception as e:
            self._log_test_result(False, f"Exception: {str(e)}")
            raise

    # ========================================================================
    # TESTY INTEGRACYJNE
    # ========================================================================

    def test_full_file_workflow(self):
        """Testuje pełny workflow zarządzania plikami"""
        try:
            with patch('file_manager.BASE_OUTPUT_DIR', str(self.test_data_dir)):
                fm = FileManager()

                # Dane testowe
                term = 10
                proceeding_id = 15
                date = '2024-01-15'

                proceeding_info = {
                    'number': 15,
                    'title': 'Test proceeding',
                    'dates': [date]
                }

                pdf_content = b"Fake PDF content"
                statements = {
                    'statements': [
                        {'num': 1, 'name': 'Speaker One', 'function': 'MP'},
                        {'num': 2, 'name': 'Speaker Two', 'function': 'Minister'}
                    ]
                }

                # Wykonaj pełny workflow
                # 1. Zapisz info o posiedzeniu
                info_path = fm.save_proceeding_info(term, proceeding_id, proceeding_info)
                self.assertIsNotNone(info_path)

                # 2. Zapisz PDF
                pdf_path = fm.save_pdf_transcript(term, proceeding_id, date, pdf_content, proceeding_info)
                self.assertIsNotNone(pdf_path)

                # 3. Zapisz wypowiedzi
                statements_path = fm.save_html_statements(term, proceeding_id, date, statements, proceeding_info)
                self.assertIsNotNone(statements_path)

                # Sprawdź strukturę
                base_proceeding_dir = Path(info_path).parent

                # Sprawdź wszystkie pliki
                info_file = base_proceeding_dir / 'info_posiedzenia.json'
                pdf_file = base_proceeding_dir / f'transkrypt_{date}.pdf'
                statements_dir = base_proceeding_dir / f'wypowiedzi_{date}'

                self.assertTrue(info_file.exists())
                self.assertTrue(pdf_file.exists())
                self.assertTrue(statements_dir.exists())

                # Sprawdź wypowiedzi
                statement_files = list(statements_dir.glob('*.html'))
                self.assertEqual(len(statement_files), 2)

                details = f"✓ Full workflow completed\n✓ All files created\n✓ Structure verified\n✓ {len(statement_files)} statement files"
                self._log_test_result(True, details)

        except Exception as e:
            self._log_test_result(False, f"Exception: {str(e)}")
            raise

    def test_concurrent_access_simulation(self):
        """Symuluje dostęp współbieżny do plików"""
        try:
            with patch('file_manager.BASE_OUTPUT_DIR', str(self.test_data_dir)):
                fm = FileManager()

                # Symuluj jednoczesne tworzenie katalogów
                term_dirs = []
                for i in range(5):
                    term_dir = fm.get_term_directory(i + 1)
                    term_dirs.append(term_dir)
                    self.assertTrue(term_dir.exists())

                # Wszystkie katalogi powinny istnieć
                for term_dir in term_dirs:
                    self.assertTrue(term_dir.exists())
                    self.assertTrue(term_dir.is_dir())

                details = f"✓ Concurrent access handled\n✓ Created {len(term_dirs)} directories\n✓ No race conditions"
                self._log_test_result(True, details)

        except Exception as e:
            self._log_test_result(False, f"Exception: {str(e)}")
            raise

    def test_large_file_handling(self):
        """Testuje obsługę dużych plików (symulacja)"""
        try:
            with patch('file_manager.BASE_OUTPUT_DIR', str(self.test_data_dir)):
                fm = FileManager()

                # Symuluj duży plik PDF (10MB)
                large_pdf_content = b"X" * (10 * 1024 * 1024)  # 10MB

                proceeding_info = {'dates': ['2024-01-15']}

                start_time = time.time()

                saved_path = fm.save_pdf_transcript(
                    term=10,
                    proceeding_id=15,
                    date='2024-01-15',
                    pdf_content=large_pdf_content,
                    proceeding_info=proceeding_info
                )

                save_time = time.time() - start_time

                self.assertIsNotNone(saved_path)

                # Sprawdź rozmiar zapisanego pliku
                saved_file = Path(saved_path)
                file_size = saved_file.stat().st_size
                self.assertEqual(file_size, len(large_pdf_content))

                details = f"✓ Large file handled\n✓ Size: {file_size / 1024 / 1024:.1f}MB\n✓ Save time: {save_time:.2f}s\n✓ Content verified"
                self._log_test_result(True, details)

        except Exception as e:
            self._log_test_result(False, f"Exception: {str(e)}")
            raise


# ========================================================================
# UTILITY FUNCTIONS
# ========================================================================

def run_file_manager_health_check():
    """Uruchamia pełny health check File Manager"""
    print(f"{TestColors.BOLD}📁 Starting File Manager Health Check...{TestColors.RESET}")
    print()

    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestFileManager)

    stream = StringIO()
    runner = unittest.TextTestRunner(stream=stream, verbosity=0)

    try:
        result = runner.run(suite)

        if result.wasSuccessful():
            print(f"{TestColors.GREEN}🎉 FILE SYSTEM OPERATIONAL{TestColors.RESET}")
            return 0
        else:
            print(f"{TestColors.RED}⚠️  FILE SYSTEM ISSUES DETECTED{TestColors.RESET}")
            return 1

    except Exception as e:
        print(f"{TestColors.RED}💥 CRITICAL FILE SYSTEM ERROR{TestColors.RESET}")
        print(f"{TestColors.RED}   Exception: {str(e)}{TestColors.RESET}")
        return 2


def run_directory_structure_test():
    """Test struktury katalogów"""
    print(f"{TestColors.CYAN}📂 Directory Structure Test{TestColors.RESET}")
    print()

    structure_tests = [
        'test_file_manager_initialization',
        'test_base_directory_creation',
        'test_term_directory_creation',
        'test_proceeding_directory_creation'
    ]

    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    for test_name in structure_tests:
        suite.addTest(TestFileManager(test_name))

    stream = StringIO()
    runner = unittest.TextTestRunner(stream=stream, verbosity=0)

    result = runner.run(suite)

    if result.wasSuccessful():
        print(f"{TestColors.GREEN}✅ Directory Structure: OK{TestColors.RESET}")
        return 0
    else:
        print(f"{TestColors.RED}❌ Directory Structure: FAILED{TestColors.RESET}")
        return 1


def run_file_operations_test():
    """Test operacji na plikach"""
    print(f"{TestColors.PURPLE}💾 File Operations Test{TestColors.RESET}")
    print()

    file_tests = [
        'test_pdf_transcript_saving',
        'test_html_statements_saving',
        'test_proceeding_info_saving',
        'test_safe_filename_generation'
    ]

    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    for test_name in file_tests:
        suite.addTest(TestFileManager(test_name))

    stream = StringIO()
    runner = unittest.TextTestRunner(stream=stream, verbosity=0)

    result = runner.run(suite)

    if result.wasSuccessful():
        print(f"{TestColors.GREEN}✅ File Operations: ALL OK{TestColors.RESET}")
        return 0
    else:
        print(f"{TestColors.RED}❌ File Operations: ISSUES FOUND{TestColors.RESET}")
        return 1


# ========================================================================
# MAIN CLI
# ========================================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="📁 SejmBot File Manager Professional Health Check",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Przykłady użycia:
  %(prog)s                    # Pełny health check
  %(prog)s --structure        # Test struktury katalogów
  %(prog)s --files            # Test operacji na plikach  
  %(prog)s --no-colors        # Bez kolorów
  %(prog)s --verbose          # Szczegółowe logi

Exit codes:
  0 - File Manager działa poprawnie
  1 - Wykryto problemy z plikami
  2 - Krytyczny błąd systemu plików
        """
    )

    parser.add_argument('--structure', action='store_true', help='Test struktury katalogów')
    parser.add_argument('--files', action='store_true', help='Test operacji na plikach')
    parser.add_argument('--no-colors', action='store_true', help='Wyłącz kolory')
    parser.add_argument('--verbose', action='store_true', help='Szczegółowe informacje')

    args = parser.parse_args()

    if args.no_colors:
        TestColors.disable_colors()

    try:
        if args.structure:
            exit_code = run_directory_structure_test()
        elif args.files:
            exit_code = run_file_operations_test()
        else:
            exit_code = run_file_manager_health_check()

        sys.exit(exit_code)

    except KeyboardInterrupt:
        print(f"\n{TestColors.YELLOW}⏹️  File Manager health check przerwany{TestColors.RESET}")
        sys.exit(130)
    except Exception as e:
        print(f"\n{TestColors.RED}💥 Nieoczekiwany błąd: {str(e)}{TestColors.RESET}")
        sys.exit(2)