"""
System kolorów i palet dla SejmBot Detektora
"""
import sys


class ColorPalette:
    """Bazowa klasa dla palet kolorów"""
    # Kolory podstawowe ANSI
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    GRAY = '\033[90m'
    BLACK = '\033[30m'

    # Kolory o wysokim kontraście
    BRIGHT_RED = '\033[1;31m'
    BRIGHT_GREEN = '\033[1;32m'
    BRIGHT_YELLOW = '\033[1;33m'
    BRIGHT_BLUE = '\033[1;34m'
    BRIGHT_MAGENTA = '\033[1;35m'
    BRIGHT_CYAN = '\033[1;36m'
    BRIGHT_WHITE = '\033[1;37m'

    # Kolory tła
    BG_RED = '\033[101m'
    BG_GREEN = '\033[102m'
    BG_YELLOW = '\033[103m'
    BG_BLUE = '\033[104m'
    BG_MAGENTA = '\033[105m'
    BG_CYAN = '\033[106m'
    BG_WHITE = '\033[107m'
    BG_GRAY = '\033[100m'

    # Formatowanie
    BOLD = '\033[1m'
    DIM = '\033[2m'
    ITALIC = '\033[3m'
    UNDERLINE = '\033[4m'
    REVERSE = '\033[7m'

    # Reset
    RESET = '\033[0m'


class DefaultPalette(ColorPalette):
    """Domyślna paleta kolorów - zbilansowana"""

    # Kolory dla poziomów logowania
    DEBUG_COLOR = ColorPalette.GRAY
    INFO_COLOR = ColorPalette.BRIGHT_WHITE
    SUCCESS_COLOR = ColorPalette.BRIGHT_GREEN
    WARNING_COLOR = ColorPalette.BRIGHT_YELLOW
    ERROR_COLOR = ColorPalette.BRIGHT_RED
    CRITICAL_COLOR = ColorPalette.BG_RED + ColorPalette.BRIGHT_WHITE

    # Kolory funkcjonalne
    APP_NAME = ColorPalette.BOLD + ColorPalette.BRIGHT_CYAN
    HEADER = ColorPalette.BOLD + ColorPalette.BRIGHT_BLUE
    SECTION = ColorPalette.BOLD + ColorPalette.CYAN
    KEY = ColorPalette.BOLD + ColorPalette.MAGENTA
    VALUE_HIGH = ColorPalette.BRIGHT_CYAN
    VALUE_MEDIUM = ColorPalette.BRIGHT_YELLOW
    VALUE_LOW = ColorPalette.BLUE
    VALUE_SPECIAL = ColorPalette.BRIGHT_MAGENTA
    PROGRESS_FILL = ColorPalette.BRIGHT_GREEN
    PROGRESS_EMPTY = ColorPalette.DIM + ColorPalette.GRAY
    TABLE_HEADER = ColorPalette.BOLD + ColorPalette.BRIGHT_YELLOW
    TABLE_HIGHLIGHT = ColorPalette.BOLD + ColorPalette.CYAN
    LIST_BULLET = ColorPalette.BLUE


class HighContrastPalette(ColorPalette):
    """Paleta o wysokim kontraście - dla lepszej czytelności"""

    # Kolory dla poziomów logowania (mocniejsze)
    DEBUG_COLOR = ColorPalette.DIM + ColorPalette.WHITE
    INFO_COLOR = ColorPalette.BRIGHT_WHITE
    SUCCESS_COLOR = ColorPalette.BG_GREEN + ColorPalette.BLACK
    WARNING_COLOR = ColorPalette.BG_YELLOW + ColorPalette.BLACK
    ERROR_COLOR = ColorPalette.BG_RED + ColorPalette.BRIGHT_WHITE
    CRITICAL_COLOR = ColorPalette.BG_RED + ColorPalette.BRIGHT_YELLOW + ColorPalette.BOLD

    # Kolory funkcjonalne (mocniejsze kontrasty)
    APP_NAME = ColorPalette.BOLD + ColorPalette.BG_CYAN + ColorPalette.BLACK
    HEADER = ColorPalette.BOLD + ColorPalette.UNDERLINE + ColorPalette.BRIGHT_WHITE
    SECTION = ColorPalette.BOLD + ColorPalette.BRIGHT_CYAN
    KEY = ColorPalette.BOLD + ColorPalette.BRIGHT_MAGENTA
    VALUE_HIGH = ColorPalette.BOLD + ColorPalette.BRIGHT_CYAN
    VALUE_MEDIUM = ColorPalette.BOLD + ColorPalette.BRIGHT_YELLOW
    VALUE_LOW = ColorPalette.BOLD + ColorPalette.BRIGHT_BLUE
    VALUE_SPECIAL = ColorPalette.BOLD + ColorPalette.BRIGHT_MAGENTA
    PROGRESS_FILL = ColorPalette.BG_GREEN + ColorPalette.BRIGHT_WHITE
    PROGRESS_EMPTY = ColorPalette.BG_GRAY + ColorPalette.WHITE
    TABLE_HEADER = ColorPalette.BG_YELLOW + ColorPalette.BLACK + ColorPalette.BOLD
    TABLE_HIGHLIGHT = ColorPalette.BOLD + ColorPalette.BRIGHT_CYAN
    LIST_BULLET = ColorPalette.BRIGHT_BLUE


class MinimalPalette(ColorPalette):
    """Paleta minimalna - subtelne kolory"""

    # Kolory dla poziomów logowania (subtelniejsze)
    DEBUG_COLOR = ColorPalette.DIM + ColorPalette.GRAY
    INFO_COLOR = ColorPalette.WHITE
    SUCCESS_COLOR = ColorPalette.GREEN
    WARNING_COLOR = ColorPalette.YELLOW
    ERROR_COLOR = ColorPalette.RED
    CRITICAL_COLOR = ColorPalette.BOLD + ColorPalette.RED

    # Kolory funkcjonalne (subtelne)
    APP_NAME = ColorPalette.BOLD + ColorPalette.CYAN
    HEADER = ColorPalette.BOLD + ColorPalette.BLUE
    SECTION = ColorPalette.CYAN
    KEY = ColorPalette.MAGENTA
    VALUE_HIGH = ColorPalette.CYAN
    VALUE_MEDIUM = ColorPalette.YELLOW
    VALUE_LOW = ColorPalette.BLUE
    VALUE_SPECIAL = ColorPalette.MAGENTA
    PROGRESS_FILL = ColorPalette.GREEN
    PROGRESS_EMPTY = ColorPalette.GRAY
    TABLE_HEADER = ColorPalette.BOLD + ColorPalette.YELLOW
    TABLE_HIGHLIGHT = ColorPalette.BOLD + ColorPalette.CYAN
    LIST_BULLET = ColorPalette.BLUE


class MatrixPalette(ColorPalette):
    """Paleta w stylu Matrix - zielone odcienie"""

    # Kolory dla poziomów logowania
    DEBUG_COLOR = ColorPalette.DIM + ColorPalette.GREEN
    INFO_COLOR = ColorPalette.BRIGHT_GREEN
    SUCCESS_COLOR = ColorPalette.BG_GREEN + ColorPalette.BLACK
    WARNING_COLOR = ColorPalette.BRIGHT_YELLOW
    ERROR_COLOR = ColorPalette.BRIGHT_RED
    CRITICAL_COLOR = ColorPalette.BG_RED + ColorPalette.BRIGHT_GREEN

    # Kolory funkcjonalne
    APP_NAME = ColorPalette.BOLD + ColorPalette.BRIGHT_GREEN
    HEADER = ColorPalette.BOLD + ColorPalette.BRIGHT_GREEN
    SECTION = ColorPalette.GREEN
    KEY = ColorPalette.BRIGHT_GREEN
    VALUE_HIGH = ColorPalette.BRIGHT_WHITE
    VALUE_MEDIUM = ColorPalette.BRIGHT_GREEN
    VALUE_LOW = ColorPalette.GREEN
    VALUE_SPECIAL = ColorPalette.BRIGHT_CYAN
    PROGRESS_FILL = ColorPalette.BRIGHT_GREEN
    PROGRESS_EMPTY = ColorPalette.DIM + ColorPalette.GREEN
    TABLE_HEADER = ColorPalette.BOLD + ColorPalette.BRIGHT_GREEN
    TABLE_HIGHLIGHT = ColorPalette.BRIGHT_WHITE
    LIST_BULLET = ColorPalette.GREEN


class NeonPalette(ColorPalette):
    """Paleta neonowa - żywe kolory"""

    # Kolory dla poziomów logowania
    DEBUG_COLOR = ColorPalette.DIM + ColorPalette.MAGENTA
    INFO_COLOR = ColorPalette.BRIGHT_CYAN
    SUCCESS_COLOR = ColorPalette.BOLD + ColorPalette.BRIGHT_GREEN
    WARNING_COLOR = ColorPalette.BOLD + ColorPalette.BRIGHT_YELLOW
    ERROR_COLOR = ColorPalette.BOLD + ColorPalette.BRIGHT_MAGENTA
    CRITICAL_COLOR = ColorPalette.BG_MAGENTA + ColorPalette.BRIGHT_YELLOW + ColorPalette.BOLD

    # Kolory funkcjonalne
    APP_NAME = ColorPalette.BOLD + ColorPalette.BRIGHT_MAGENTA
    HEADER = ColorPalette.BOLD + ColorPalette.BRIGHT_CYAN
    SECTION = ColorPalette.BRIGHT_MAGENTA
    KEY = ColorPalette.BRIGHT_CYAN
    VALUE_HIGH = ColorPalette.BRIGHT_YELLOW
    VALUE_MEDIUM = ColorPalette.BRIGHT_MAGENTA
    VALUE_LOW = ColorPalette.BRIGHT_CYAN
    VALUE_SPECIAL = ColorPalette.BRIGHT_GREEN
    PROGRESS_FILL = ColorPalette.BRIGHT_MAGENTA
    PROGRESS_EMPTY = ColorPalette.DIM + ColorPalette.CYAN
    TABLE_HEADER = ColorPalette.BOLD + ColorPalette.BRIGHT_YELLOW
    TABLE_HIGHLIGHT = ColorPalette.BOLD + ColorPalette.BRIGHT_MAGENTA
    LIST_BULLET = ColorPalette.BRIGHT_CYAN


# Mapowanie nazw palet do klas
PALETTES = {
    'default': DefaultPalette,
    'high_contrast': HighContrastPalette,
    'minimal': MinimalPalette,
    'matrix': MatrixPalette,
    'neon': NeonPalette
}


class Colors:
    """Klasa zarządzająca kolorami z obsługą palet"""
    _current_palette = DefaultPalette

    @classmethod
    def set_palette(cls, palette_name: str):
        """Ustawia aktualną paletę kolorów"""
        if palette_name.lower() in PALETTES:
            cls._current_palette = PALETTES[palette_name.lower()]
            return True
        return False

    @classmethod
    def get_available_palettes(cls):
        """Zwraca dostępne palety kolorów"""
        return list(PALETTES.keys())

    @classmethod
    def get_current_palette_name(cls):
        """Zwraca nazwę aktualnej palety"""
        for name, palette_class in PALETTES.items():
            if palette_class == cls._current_palette:
                return name
        return 'unknown'

    # Kolory dla poziomów logowania
    @classmethod
    def get_debug_color(cls):
        return cls._current_palette.DEBUG_COLOR

    @classmethod
    def get_info_color(cls):
        return cls._current_palette.INFO_COLOR

    @classmethod
    def get_success_color(cls):
        return cls._current_palette.SUCCESS_COLOR

    @classmethod
    def get_warning_color(cls):
        return cls._current_palette.WARNING_COLOR

    @classmethod
    def get_error_color(cls):
        return cls._current_palette.ERROR_COLOR

    @classmethod
    def get_critical_color(cls):
        return cls._current_palette.CRITICAL_COLOR

    # Kolory funkcjonalne
    @classmethod
    def get_app_name_color(cls):
        return cls._current_palette.APP_NAME

    @classmethod
    def get_header_color(cls):
        return cls._current_palette.HEADER

    @classmethod
    def get_section_color(cls):
        return cls._current_palette.SECTION

    @classmethod
    def get_key_color(cls):
        return cls._current_palette.KEY

    @classmethod
    def get_value_high_color(cls):
        return cls._current_palette.VALUE_HIGH

    @classmethod
    def get_value_medium_color(cls):
        return cls._current_palette.VALUE_MEDIUM

    @classmethod
    def get_value_low_color(cls):
        return cls._current_palette.VALUE_LOW

    @classmethod
    def get_value_special_color(cls):
        return cls._current_palette.VALUE_SPECIAL

    @classmethod
    def get_progress_fill_color(cls):
        return cls._current_palette.PROGRESS_FILL

    @classmethod
    def get_progress_empty_color(cls):
        return cls._current_palette.PROGRESS_EMPTY

    @classmethod
    def get_table_header_color(cls):
        return cls._current_palette.TABLE_HEADER

    @classmethod
    def get_table_highlight_color(cls):
        return cls._current_palette.TABLE_HIGHLIGHT

    @classmethod
    def get_list_bullet_color(cls):
        return cls._current_palette.LIST_BULLET

    # Stałe kolory podstawowe (dla kompatybilności wstecznej)
    RED = ColorPalette.RED
    GREEN = ColorPalette.GREEN
    YELLOW = ColorPalette.YELLOW
    BLUE = ColorPalette.BLUE
    MAGENTA = ColorPalette.MAGENTA
    CYAN = ColorPalette.CYAN
    WHITE = ColorPalette.WHITE
    GRAY = ColorPalette.GRAY

    BOLD = ColorPalette.BOLD
    DIM = ColorPalette.DIM
    UNDERLINE = ColorPalette.UNDERLINE
    RESET = ColorPalette.RESET

    @classmethod
    def strip_colors(cls, text: str) -> str:
        """Usuwa kody kolorów z tekstu"""
        import re
        ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
        return ansi_escape.sub('', text)

    @classmethod
    def supports_color(cls) -> bool:
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
