"""
Główna klasa Logger dla SejmBot Detektora
"""
import sys

from SejmBotDetektor.utils.colors import Colors
from SejmBotDetektor.utils.log_levels import LogLevel


class Logger:
    """Kolorowy logger dla aplikacji z obsługą palet"""

    def __init__(self, name: str = "SejmBot", enable_colors: bool = True, palette: str = "default"):
        self.name = name
        self.enable_colors = enable_colors and Colors.supports_color()
        self.min_level = LogLevel.INFO
        Colors.set_palette(palette)

    def set_palette(self, palette_name: str):
        """Ustawia paletę kolorów"""
        return Colors.set_palette(palette_name)

    def get_available_palettes(self):
        """Zwraca dostępne palety kolorów"""
        return Colors.get_available_palettes()

    def get_current_palette(self):
        """Zwraca nazwę aktualnej palety"""
        return Colors.get_current_palette_name()

    def set_level(self, level: LogLevel):
        """Ustawia minimalny poziom logowania"""
        self.min_level = level

    def _should_log(self, level: LogLevel) -> bool:
        """Sprawdza czy wiadomość powinna być zalogowana"""
        return level >= self.min_level

    def _get_level_color(self, level: LogLevel) -> str:
        """Pobiera kolor dla danego poziomu logowania"""
        if level.value == "DEBUG":
            return Colors.get_debug_color()
        elif level.value == "INFO":
            return Colors.get_info_color()
        elif level.value == "SUCCESS":
            return Colors.get_success_color()
        elif level.value == "WARNING":
            return Colors.get_warning_color()
        elif level.value == "ERROR":
            return Colors.get_error_color()
        elif level.value == "CRITICAL":
            return Colors.get_critical_color()
        else:
            return Colors.get_info_color()

    def _format_message(self, level: LogLevel, message: str, prefix: str = None) -> str:
        """Formatuje wiadomość z kolorami"""
        level_name = level.value

        if not self.enable_colors:
            if prefix:
                return f"[{self.name}] [{level_name}] {prefix}: {message}"
            return f"[{self.name}] [{level_name}] {message}"

        # Kolorowa wersja
        level_color = self._get_level_color(level)
        level_colored = f"{level_color}[{level_name}]{Colors.RESET}"
        name_colored = f"{Colors.get_app_name_color()}[{self.name}]{Colors.RESET}"

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
        header_color = Colors.get_header_color()
        separator = f"{header_color}{'=' * (len(message) + 4)}{Colors.RESET}"
        header_text = f"{header_color}  {message}  {Colors.RESET}"

        print(f"\n{separator}")
        print(header_text)
        print(f"{separator}\n")

    def section(self, message: str):
        """Wyświetla nagłówek podsekcji"""
        if not self.enable_colors:
            print(f"\n--- {message} ---")
            return

        section_color = Colors.get_section_color()
        section_text = f"{section_color}--- {message} ---{Colors.RESET}"
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
        fill_color = Colors.get_progress_fill_color()
        empty_color = Colors.get_progress_empty_color()

        filled = f"{fill_color}█{Colors.RESET}" * filled_length
        empty = f"{empty_color}-{Colors.RESET}" * (30 - filled_length)
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

        header_color = Colors.get_table_header_color()
        colored_headers = [f"{header_color}{h}{Colors.RESET}" for h in headers]
        print(" | ".join(colored_headers))

        separator = f"{Colors.GRAY}{'-' * (sum(len(h) for h in headers) + 3 * (len(headers) - 1))}{Colors.RESET}"
        print(separator)

    def table_row(self, values: list, highlight_first: bool = False):
        """Wyświetla wiersz tabeli"""
        if not self.enable_colors or not highlight_first:
            print(" | ".join(str(v) for v in values))
            return

        # Pierwszy element wyróżniony
        highlight_color = Colors.get_table_highlight_color()
        colored_values = [f"{highlight_color}{values[0]}{Colors.RESET}"]
        colored_values.extend(str(v) for v in values[1:])
        print(" | ".join(colored_values))

    def keyvalue(self, key: str, value: str, key_color: str = None):
        """Wyświetla parę klucz-wartość"""
        if not self.enable_colors:
            print(f"{key}: {value}")
            return

        if key_color is None:
            key_color = Colors.get_key_color()

        key_colored = f"{Colors.BOLD}{key_color}{key}{Colors.RESET}"
        print(f"{key_colored}: {value}")

    def list_item(self, item: str, level: int = 0, bullet: str = "-"):
        """Wyświetla element listy z wcięciem"""
        indent = "  " * level

        if not self.enable_colors:
            print(f"{indent}{bullet} {item}")
            return

        bullet_color = Colors.get_list_bullet_color()
        bullet_colored = f"{bullet_color}{bullet}{Colors.RESET}"
        print(f"{indent}{bullet_colored} {item}")

    def palette_demo(self):
        """Demonstracja aktualnej palety kolorów"""
        current_palette = self.get_current_palette()
        self.header(f"Demonstracja palety: {current_palette}")

        # Poziomy logowania
        self.section("Poziomy logowania")
        self.debug("To jest wiadomość debug")
        self.info("To jest wiadomość informacyjna")
        self.success("To jest wiadomość o sukcesie")
        self.warning("To jest ostrzeżenie")
        self.error("To jest błąd")
        self.critical("To jest błąd krytyczny")

        # Demonstracja z różnymi kolorami wartości (kompatybilność z istniejącym kodem)
        self.section("Pary klucz-wartość (styl main.py)")
        self.keyvalue("Plik PDF", "transkrypt_sejmu.pdf", Colors.CYAN)
        self.keyvalue("Minimalny próg pewności", "0.3", Colors.YELLOW)
        self.keyvalue("Maksymalna liczba fragmentów", "20", Colors.BLUE)
        self.keyvalue("Kontekst słów", "25/25", Colors.MAGENTA)
        self.keyvalue("Tryb debugowania", "WŁĄCZONY", Colors.GREEN)

        # Tabela
        self.section("Tabela")
        self.table_header(["Kolumna 1", "Kolumna 2", "Kolumna 3"])
        self.table_row(["Wiersz 1A", "Wiersz 1B", "Wiersz 1C"], highlight_first=True)
        self.table_row(["Wiersz 2A", "Wiersz 2B", "Wiersz 2C"])

        # Lista
        self.section("Lista")
        self.list_item("Element 1")
        self.list_item("Element 2 zagnieżdżony", level=1)
        self.list_item("Element 3 głęboko zagnieżdżony", level=2)

        # Pasek postępu
        self.section("Pasek postępu")
        for i in range(0, 101, 25):
            self.progress(i, 100, f"Ładowanie... {i}%")

        print()


class ModuleLogger:
    """Logger dla konkretnego modułu"""

    def __init__(self, module_name: str, parent_logger: Logger = None):
        self.module_name = module_name
        self.parent = parent_logger

    def debug(self, message: str):
        if self.parent:
            self.parent.debug(message, self.module_name)

    def info(self, message: str):
        if self.parent:
            self.parent.info(message, self.module_name)

    def success(self, message: str):
        if self.parent:
            self.parent.success(message, self.module_name)

    def warning(self, message: str):
        if self.parent:
            self.parent.warning(message, self.module_name)

    def error(self, message: str):
        if self.parent:
            self.parent.error(message, self.module_name)

    def critical(self, message: str):
        if self.parent:
            self.parent.critical(message, self.module_name)


# Globalny logger dla całej aplikacji
logger = Logger("SejmBot", enable_colors=True, palette="default")

# żeby sprawdzić dostępne palety, zobacz `PALETTES` w SejmBotDetektor/utils/colors.py
# "default"
# "high_contrast"
# "minimal"
# "matrix"
# "neon"


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


def set_palette(palette_name: str):
    return logger.set_palette(palette_name)


def get_available_palettes():
    return logger.get_available_palettes()


def get_module_logger(module_name: str) -> ModuleLogger:
    return ModuleLogger(module_name, logger)
