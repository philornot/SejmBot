"""
Funkcje pomocnicze i publiczny interface dla systemu logowania
"""
from .colors import Colors
from .log_levels import LogLevel
from .logger import logger, Logger, ModuleLogger, get_module_logger


# Funkcje pomocnicze dla szybkiego użycia z globalnym loggerem
def debug(message: str, prefix: str = None):
    """Loguje wiadomość debug"""
    logger.debug(message, prefix)


def info(message: str, prefix: str = None):
    """Loguje wiadomość informacyjną"""
    logger.info(message, prefix)


def success(message: str, prefix: str = None):
    """Loguje wiadomość o sukcesie"""
    logger.success(message, prefix)


def warning(message: str, prefix: str = None):
    """Loguje ostrzeżenie"""
    logger.warning(message, prefix)


def error(message: str, prefix: str = None):
    """Loguje błąd"""
    logger.error(message, prefix)


def critical(message: str, prefix: str = None):
    """Loguje błąd krytyczny"""
    logger.critical(message, prefix)


def header(message: str):
    """Wyświetla nagłówek sekcji"""
    logger.header(message)


def section(message: str):
    """Wyświetla nagłówek podsekcji"""
    logger.section(message)


def progress(current: int, total: int, description: str = ""):
    """Wyświetla pasek postępu"""
    logger.progress(current, total, description)


def table_header(headers: list):
    """Wyświetla nagłówek tabeli"""
    logger.table_header(headers)


def table_row(values: list, highlight_first: bool = False):
    """Wyświetla wiersz tabeli"""
    logger.table_row(values, highlight_first)


def keyvalue(key: str, value: str, key_color: str = None):
    """Wyświetla parę klucz-wartość"""
    logger.keyvalue(key, value, key_color)


def list_item(item: str, level: int = 0, bullet: str = "-"):
    """Wyświetla element listy z wcięciem"""
    logger.list_item(item, level, bullet)


def set_palette(palette_name: str):
    """Ustawia paletę kolorów dla globalnego loggera"""
    return logger.set_palette(palette_name)


def get_available_palettes():
    """Zwraca dostępne palety kolorów"""
    return logger.get_available_palettes()


def get_current_palette():
    """Zwraca nazwę aktualnej palety"""
    return logger.get_current_palette()


def set_log_level(level: LogLevel):
    """Ustawia minimalny poziom logowania dla globalnego loggera"""
    logger.set_level(level)


def demo_palettes():
    """Demonstracja wszystkich dostępnych palet"""
    available_palettes = get_available_palettes()

    for palette_name in available_palettes:
        set_palette(palette_name)
        logger.palette_demo()
        input(f"\nNaciśnij Enter aby zobaczyć następną paletę...")


def create_logger(name: str, enable_colors: bool = True, palette: str = "default") -> Logger:
    """Tworzy nowy logger z podanymi parametrami"""
    return Logger(name, enable_colors, palette)


def supports_colors() -> bool:
    """Sprawdza czy terminal obsługuje kolory"""
    return Colors.supports_color()


def strip_colors(text: str) -> str:
    """Usuwa kody kolorów z tekstu"""
    return Colors.strip_colors(text)


# Eksportowane elementy dla łatwego importu
__all__ = [
    # Klasy główne
    'Logger',
    'ModuleLogger',
    'Colors',
    'LogLevel',

    # Globalny logger
    'logger',

    # Funkcje pomocnicze logowania
    'debug', 'info', 'success', 'warning', 'error', 'critical',
    'header', 'section', 'progress', 'table_header', 'table_row',
    'keyvalue', 'list_item',

    # Funkcje zarządzania paletami
    'set_palette', 'get_available_palettes', 'get_current_palette',
    'demo_palettes',

    # Funkcje pomocnicze
    'create_logger', 'get_module_logger', 'set_log_level',
    'supports_colors', 'strip_colors'
]
