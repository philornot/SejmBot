"""
Kolorowy system logowania dla SejmBot Detektora
"""
import sys
from enum import Enum


class Colors:
    """Kody kolorów ANSI dla terminala"""
    # Kolory tekstu
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    GRAY = '\033[90m'

    # Kolory tła
    BG_RED = '\033[101m'
    BG_GREEN = '\033[102m'
    BG_YELLOW = '\033[103m'
    BG_BLUE = '\033[104m'

    # Formatowanie
    BOLD = '\033[1m'
    DIM = '\033[2m'
    UNDERLINE = '\033[4m'

    # Reset
    RESET = '\033[0m'

    @classmethod
    def strip_colors(cls, text: str) -> str:
        """Usuwa kody kolorów z tekstu"""
        import re
        ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
        return ansi_escape.sub('', text)


class LogLevel(Enum):
    """Poziomy logowania"""
    DEBUG = ("DEBUG", Colors.GRAY)
    INFO = ("INFO", Colors.WHITE)
    SUCCESS = ("SUCCESS", Colors.GREEN)
    WARNING = ("WARNING", Colors.YELLOW)
    ERROR = ("ERROR", Colors.RED)
    CRITICAL = ("CRITICAL", Colors.BG_RED + Colors.WHITE)


class Logger:
    """Kolorowy logger dla aplikacji"""

    def __init__(self, name: str = "SejmBot", enable_colors: bool = True):
        self.name = name
        self.enable_colors = enable_colors and self._supports_color()
        self.min_level = LogLevel.INFO

    def _supports_color(self) -> bool:
        """Sprawdza czy terminal obsługuje kolory"""
        # Windows
        if sys.platform.startswith('win'):
            try:
                import colorama
                colorama.init()
                return True
            except ImportError:
                # Próbujemy włączyć obsługę ANSI w Windows 10+
                import os
                os.system('color')
                return True

        # Unix/Linux/macOS
        return hasattr(sys.stdout, 'isatty') and sys.stdout.isatty()

    def set_level(self, level: LogLevel):
        """Ustawia minimalny poziom logowania"""
        self.min_level = level

    def _should_log(self, level: LogLevel) -> bool:
        """Sprawdza czy wiadomość powinna być zalogowana"""
        levels_order = [LogLevel.DEBUG, LogLevel.INFO, LogLevel.SUCCESS,
                        LogLevel.WARNING, LogLevel.ERROR, LogLevel.CRITICAL]
        return levels_order.index(level) >= levels_order.index(self.min_level)

    def _format_message(self, level: LogLevel, message: str, prefix: str = None) -> str:
        """Formatuje wiadomość z kolorami"""
        level_name, color = level.value

        if not self.enable_colors:
            if prefix:
                return f"[{self.name}] [{level_name}] {prefix}: {message}"
            return f"[{self.name}] [{level_name}] {message}"

        # Kolorowa wersja
        level_colored = f"{color}[{level_name}]{Colors.RESET}"
        name_colored = f"{Colors.BOLD}{Colors.CYAN}[{self.name}]{Colors.RESET}"

        if prefix:
            prefix_colored = f"{Colors.BOLD}{prefix}{Colors.RESET}"
            return f"{name_colored} {level_colored} {prefix_colored}: {message}"

        return f"{name_colored} {level_colored} {message}"

    def debug(self, message: str, prefix: str = None):
        """Loguje wiadomość debug"""
        if self._should_log(LogLevel.DEBUG):
            formatted = self._format_message(LogLevel.DEBUG, message, prefix)
            print(formatted)

    def info(self, message: str, prefix: str = None):
        """Loguje wiadomość informacyjną"""
        if self._should_log(LogLevel.INFO):
            formatted = self._format_message(LogLevel.INFO, message, prefix)
            print(formatted)

    def success(self, message: str, prefix: str = None):
        """Loguje wiadomość o sukcesie"""
        if self._should_log(LogLevel.SUCCESS):
            formatted = self._format_message(LogLevel.SUCCESS, message, prefix)
            print(formatted)

    def warning(self, message: str, prefix: str = None):
        """Loguje ostrzeżenie"""
        if self._should_log(LogLevel.WARNING):
            formatted = self._format_message(LogLevel.WARNING, message, prefix)
            print(formatted)

    def error(self, message: str, prefix: str = None):
        """Loguje błąd"""
        if self._should_log(LogLevel.ERROR):
            formatted = self._format_message(LogLevel.ERROR, message, prefix)
            print(formatted, file=sys.stderr)

    def critical(self, message: str, prefix: str = None):
        """Loguje błąd krytyczny"""
        if self._should_log(LogLevel.CRITICAL):
            formatted = self._format_message(LogLevel.CRITICAL, message, prefix)
            print(formatted, file=sys.stderr)

    def header(self, message: str):
        """Wyświetla nagłówek sekcji"""
        if not self.enable_colors:
            separator = "=" * len(message)
            print(f"\n{separator}")
            print(message)
            print(f"{separator}\n")
            return

        # Kolorowa wersja
        separator = f"{Colors.BLUE}{'=' * (len(message) + 4)}{Colors.RESET}"
        header_text = f"{Colors.BOLD}{Colors.BLUE}  {message}  {Colors.RESET}"

        print(f"\n{separator}")
        print(header_text)
        print(f"{separator}\n")

    def section(self, message: str):
        """Wyświetla nagłówek podsekcji"""
        if not self.enable_colors:
            print(f"\n--- {message} ---")
            return

        section_text = f"{Colors.BOLD}{Colors.CYAN}--- {message} ---{Colors.RESET}"
        print(f"\n{section_text}")

    def progress(self, current: int, total: int, description: str = ""):
        """Wyświetla pasek postępu"""
        if total == 0:
            return

        percentage = (current / total) * 100
        filled_length = int(30 * current // total)

        if not self.enable_colors:
            bar = '█' * filled_length + '-' * (30 - filled_length)
            print(f"\r[{bar}] {percentage:.1f}% {description}", end='', flush=True)
            return

        # Kolorowy pasek
        filled = f"{Colors.GREEN}█{Colors.RESET}" * filled_length
        empty = f"{Colors.GRAY}-{Colors.RESET}" * (30 - filled_length)
        percentage_text = f"{Colors.BOLD}{percentage:.1f}%{Colors.RESET}"

        print(f"\r[{filled}{empty}] {percentage_text} {description}", end='', flush=True)

        if current == total:
            print()  # Nowa linia na końcu

    def table_header(self, headers: list):
        """Wyświetla nagłówek tabeli"""
        if not self.enable_colors:
            print(" | ".join(headers))
            print("-" * (sum(len(h) for h in headers) + 3 * (len(headers) - 1)))
            return

        colored_headers = [f"{Colors.BOLD}{Colors.YELLOW}{h}{Colors.RESET}" for h in headers]
        print(" | ".join(colored_headers))

        separator = f"{Colors.GRAY}{'-' * (sum(len(h) for h in headers) + 3 * (len(headers) - 1))}{Colors.RESET}"
        print(separator)

    def table_row(self, values: list, highlight_first: bool = False):
        """Wyświetla wiersz tabeli"""
        if not self.enable_colors or not highlight_first:
            print(" | ".join(str(v) for v in values))
            return

        # Pierwszy element wyróżniony
        colored_values = [f"{Colors.BOLD}{Colors.CYAN}{values[0]}{Colors.RESET}"]
        colored_values.extend(str(v) for v in values[1:])
        print(" | ".join(colored_values))

    def keyvalue(self, key: str, value: str, key_color: str = None):
        """Wyświetla parę klucz-wartość"""
        if not self.enable_colors:
            print(f"{key}: {value}")
            return

        if key_color is None:
            key_color = Colors.MAGENTA

        key_colored = f"{Colors.BOLD}{key_color}{key}{Colors.RESET}"
        print(f"{key_colored}: {value}")

    def list_item(self, item: str, level: int = 0, bullet: str = "-"):
        """Wyświetla element listy z wcięciem"""
        indent = "  " * level

        if not self.enable_colors:
            print(f"{indent}{bullet} {item}")
            return

        bullet_colored = f"{Colors.BLUE}{bullet}{Colors.RESET}"
        print(f"{indent}{bullet_colored} {item}")


# Globalny logger dla całej aplikacji
logger = Logger("SejmBot")


# Funkcje pomocnicze dla szybkiego użycia
def debug(message: str, prefix: str = None):
    logger.debug(message, prefix)


def info(message: str, prefix: str = None):
    logger.info(message, prefix)


def success(message: str, prefix: str = None):
    logger.success(message, prefix)


def warning(message: str, prefix: str = None):
    logger.warning(message, prefix)


def error(message: str, prefix: str = None):
    logger.error(message, prefix)


def critical(message: str, prefix: str = None):
    logger.critical(message, prefix)


def header(message: str):
    logger.header(message)


def section(message: str):
    logger.section(message)


# Specjalne loggery dla różnych modułów
class ModuleLogger:
    """Logger dla konkretnego modułu"""

    def __init__(self, module_name: str, parent_logger: Logger = None):
        self.module_name = module_name
        self.parent = parent_logger or logger

    def debug(self, message: str):
        self.parent.debug(message, self.module_name)

    def info(self, message: str):
        self.parent.info(message, self.module_name)

    def success(self, message: str):
        self.parent.success(message, self.module_name)

    def warning(self, message: str):
        self.parent.warning(message, self.module_name)

    def error(self, message: str):
        self.parent.error(message, self.module_name)

    def critical(self, message: str):
        self.parent.critical(message, self.module_name)


def get_module_logger(module_name: str) -> ModuleLogger:
    """Tworzy logger dla konkretnego modułu"""
    return ModuleLogger(module_name)