# cli/commands.py
"""
Interfejs komend CLI - główne komendy dostępne w aplikacji
Mały plik interfejsowy - handlery w osobnych plikach
"""

import logging
from datetime import datetime
from typing import Dict, Any, List

from ..cache.manager import CacheInterface
from ..config.settings import get_settings
from ..scraping.scraper import SejmScraper

logger = logging.getLogger(__name__)


class CLICommands:
    """
    Główne komendy dostępne w CLI

    Każda komenda ma swój handler w osobnym pliku dla lepszej organizacji.
    Ten plik zawiera tylko interfejsy - implementacje w handlers/
    """

    def __init__(self):
        """Inicjalizuje CLI commands"""
        # Załaduj konfigurację
        self.settings = get_settings()

        # Inicjalizuj komponenty
        self.scraper = SejmScraper()
        self.cache = CacheInterface()

        # Statystyki sesji
        self.session_stats = {
            'start_time': datetime.now(),
            'commands_executed': 0,
            'errors': 0
        }

        logger.debug("Zainicjalizowano CLI commands")

    # === KOMENDY SCRAPOWANIA STENOGRAMÓW ===

    def scrape_term(self, args: Dict[str, Any]) -> int:
        """
        Komenda scrapowania całej kadencji

        Args:
            args: argumenty komendy
                - term: int - numer kadencji
                - fetch_full_statements: bool - czy pobierać pełną treść
                - force_refresh: bool - czy wymusić odświeżenie
                - skip_future: bool - czy pomijać przyszłe posiedzenia

        Returns:
            Kod wyjścia (0 = sukces, >0 = błąd)
        """
        logger.info(f"Wykonywanie komendy scrape-term z argumentami: {args}")

        try:
            # Import handlera dopiero tutaj
            from .handlers.scrape_handler import handle_scrape_term

            return handle_scrape_complete(self.scraper, args)

        except Exception as e:
            logger.error(f"Błąd wykonania scrape-complete: {e}")
            self.session_stats['errors'] += 1
            return 1

    # === KOMENDY INFORMACYJNE ===

    def list_terms(self, args: Dict[str, Any]) -> int:
        """
        Komenda listowania dostępnych kadencji

        Args:
            args: argumenty komendy (puste)

        Returns:
            Kod wyjścia
        """
        logger.info("Wykonywanie komendy list-terms")

        try:
            from .handlers.info_handler import handle_list_terms

            self.session_stats['commands_executed'] += 1
            return handle_list_terms(self.scraper, args)

        except Exception as e:
            logger.error(f"Błąd wykonania list-terms: {e}")
            self.session_stats['errors'] += 1
            return 1

    def list_proceedings(self, args: Dict[str, Any]) -> int:
        """
        Komenda listowania posiedzeń kadencji

        Args:
            args: argumenty komendy
                - term: int - numer kadencji
                - show_future: bool - czy pokazywać przyszłe posiedzenia

        Returns:
            Kod wyjścia
        """
        logger.info(f"Wykonywanie komendy list-proceedings: {args}")

        try:
            from .handlers.info_handler import handle_list_proceedings

            self.session_stats['commands_executed'] += 1
            return handle_list_proceedings(self.scraper, args)

        except Exception as e:
            logger.error(f"Błąd wykonania list-proceedings: {e}")
            self.session_stats['errors'] += 1
            return 1

    def show_stats(self, args: Dict[str, Any]) -> int:
        """
        Komenda pokazująca statystyki scrapowania

        Args:
            args: argumenty komendy
                - term: int - numer kadencji (opcjonalny)
                - detailed: bool - czy pokazać szczegółowe statystyki

        Returns:
            Kod wyjścia
        """
        logger.info(f"Wykonywanie komendy show-stats: {args}")

        try:
            from .handlers.info_handler import handle_show_stats

            self.session_stats['commands_executed'] += 1
            return handle_show_stats(self.scraper, args)

        except Exception as e:
            logger.error(f"Błąd wykonania show-stats: {e}")
            self.session_stats['errors'] += 1
            return 1

    # === KOMENDY ZARZĄDZANIA CACHE ===

    def cache_stats(self, args: Dict[str, Any]) -> int:
        """
        Komenda statystyk cache

        Args:
            args: argumenty komendy
                - detailed: bool - czy pokazać szczegółowe statystyki

        Returns:
            Kod wyjścia
        """
        logger.info("Wykonywanie komendy cache-stats")

        try:
            from .handlers.cache_handler import handle_cache_stats

            self.session_stats['commands_executed'] += 1
            return handle_cache_stats(self.cache, args)

        except Exception as e:
            logger.error(f"Błąd wykonania cache-stats: {e}")
            self.session_stats['errors'] += 1
            return 1

    def cache_clear(self, args: Dict[str, Any]) -> int:
        """
        Komenda czyszczenia cache

        Args:
            args: argumenty komendy
                - cache_type: str - typ cache (all, api, file, memory)
                - confirm: bool - potwierdzenie operacji

        Returns:
            Kod wyjścia
        """
        logger.info(f"Wykonywanie komendy cache-clear: {args}")

        try:
            from .handlers.cache_handler import handle_cache_clear

            self.session_stats['commands_executed'] += 1
            return handle_cache_clear(self.cache, args)

        except Exception as e:
            logger.error(f"Błąd wykonania cache-clear: {e}")
            self.session_stats['errors'] += 1
            return 1

    def cache_cleanup(self, args: Dict[str, Any]) -> int:
        """
        Komenda czyszczenia starych wpisów cache

        Args:
            args: argumenty komendy (puste)

        Returns:
            Kod wyjścia
        """
        logger.info("Wykonywanie komendy cache-cleanup")

        try:
            from .handlers.cache_handler import handle_cache_cleanup

            self.session_stats['commands_executed'] += 1
            return handle_cache_cleanup(self.cache, args)

        except Exception as e:
            logger.error(f"Błąd wykonania cache-cleanup: {e}")
            self.session_stats['errors'] += 1
            return 1

    # === KOMENDY KONFIGURACJI ===

    def show_config(self, args: Dict[str, Any]) -> int:
        """
        Komenda pokazująca konfigurację

        Args:
            args: argumenty komendy
                - section: str - sekcja konfiguracji (opcjonalna)

        Returns:
            Kod wyjścia
        """
        logger.info(f"Wykonywanie komendy show-config: {args}")

        try:
            from .handlers.config_handler import handle_show_config

            self.session_stats['commands_executed'] += 1
            return handle_show_config(self.settings, args)

        except Exception as e:
            logger.error(f"Błąd wykonania show-config: {e}")
            self.session_stats['errors'] += 1
            return 1

    def validate_config(self, args: Dict[str, Any]) -> int:
        """
        Komenda walidacji konfiguracji

        Args:
            args: argumenty komendy (puste)

        Returns:
            Kod wyjścia
        """
        logger.info("Wykonywanie komendy validate-config")

        try:
            from .handlers.config_handler import handle_validate_config

            self.session_stats['commands_executed'] += 1
            return handle_validate_config(self.settings, args)

        except Exception as e:
            logger.error(f"Błąd wykonania validate-config: {e}")
            self.session_stats['errors'] += 1
            return 1

    # === KOMENDY DIAGNOSTYCZNE ===

    def health_check(self, args: Dict[str, Any]) -> int:
        """
        Komenda sprawdzania stanu aplikacji

        Args:
            args: argumenty komendy
                - verbose: bool - czy pokazać szczegóły

        Returns:
            Kod wyjścia
        """
        logger.info("Wykonywanie komendy health-check")

        try:
            from .handlers.diagnostic_handler import handle_health_check

            self.session_stats['commands_executed'] += 1
            return handle_health_check(self.scraper, self.cache, self.settings, args)

        except Exception as e:
            logger.error(f"Błąd wykonania health-check: {e}")
            self.session_stats['errors'] += 1
            return 1

    def test_api(self, args: Dict[str, Any]) -> int:
        """
        Komenda testowania połączenia z API

        Args:
            args: argumenty komendy
                - endpoint: str - endpoint do testowania (opcjonalny)

        Returns:
            Kod wyjścia
        """
        logger.info(f"Wykonywanie komendy test-api: {args}")

        try:
            from .handlers.diagnostic_handler import handle_test_api

            self.session_stats['commands_executed'] += 1
            return handle_test_api(self.scraper, args)

        except Exception as e:
            logger.error(f"Błąd wykonania test-api: {e}")
            self.session_stats['errors'] += 1
            return 1

    # === KOMENDY POMOCNICZE ===

    def version(self, args: Dict[str, Any]) -> int:
        """
        Komenda pokazująca wersję aplikacji

        Args:
            args: argumenty komendy (puste)

        Returns:
            Kod wyjścia (zawsze 0)
        """
        try:
            from .handlers.misc_handler import handle_version

            self.session_stats['commands_executed'] += 1
            return handle_version(args)

        except Exception as e:
            logger.error(f"Błąd wykonania version: {e}")
            self.session_stats['errors'] += 1
            return 1

    def help_command(self, args: Dict[str, Any]) -> int:
        """
        Komenda pomocy

        Args:
            args: argumenty komendy
                - command: str - nazwa komendy (opcjonalna)

        Returns:
            Kod wyjścia (zawsze 0)
        """
        try:
            from .handlers.misc_handler import handle_help

            self.session_stats['commands_executed'] += 1
            return handle_help(args)

        except Exception as e:
            logger.error(f"Błąd wykonania help: {e}")
            self.session_stats['errors'] += 1
            return 1

    # === METODY POMOCNICZE ===

    def get_session_stats(self) -> Dict[str, Any]:
        """
        Zwraca statystyki sesji CLI

        Returns:
            Słownik ze statystykami sesji
        """
        current_time = datetime.now()
        duration = (current_time - self.session_stats['start_time']).total_seconds()

        return {
            **self.session_stats,
            'current_time': current_time.isoformat(),
            'duration_seconds': duration,
            'success_rate': (
                                    (self.session_stats['commands_executed'] - self.session_stats['errors']) /
                                    max(self.session_stats['commands_executed'], 1)
                            ) * 100
        }

    @staticmethod
    def validate_args(command: str, args: Dict[str, Any]) -> List[str]:
        """
        Waliduje argumenty komendy

        Args:
            command: nazwa komendy
            args: argumenty do walidacji

        Returns:
            Lista błędów walidacji (pusta jeśli OK)
        """
        from ..core.exceptions import validate_term, validate_proceeding, validate_date_format

        errors = []

        try:
            # Walidacja wspólna dla większości komend
            if 'term' in args:
                validate_term(args['term'])

            if 'proceeding' in args:
                validate_proceeding(args['proceeding'])

            if 'date' in args:
                validate_date_format(args['date'])

            # Walidacje specyficzne dla komend
            if command in ['scrape-term', 'scrape-complete']:
                if args.get('term', 0) < 1:
                    errors.append("Numer kadencji musi być większy od 0")

            if command == 'scrape-proceeding':
                if not args.get('term') or not args.get('proceeding'):
                    errors.append("Wymagane parametry: term, proceeding")

            if command == 'scrape-date':
                required = ['term', 'proceeding', 'date']
                missing = [param for param in required if not args.get(param)]
                if missing:
                    errors.append(f"Brakuje wymaganych parametrów: {', '.join(missing)}")

        except Exception as e:
            errors.append(str(e))

        return errors

    def print_session_summary(self) -> None:
        """Wyświetla podsumowanie sesji CLI"""
        stats = self.get_session_stats()

        print("\n" + "=" * 50)
        print("📊 PODSUMOWANIE SESJI CLI")
        print("=" * 50)
        print(f"Czas rozpoczęcia: {self.session_stats['start_time'].strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Czas trwania: {stats['duration_seconds']:.1f}s")
        print(f"Wykonane komendy: {stats['commands_executed']}")
        print(f"Błędy: {stats['errors']}")
        print(f"Współczynnik sukcesu: {stats['success_rate']:.1f}%")
        print("=" * 50)

    def cleanup(self) -> None:
        """Czyści zasoby przed zakończeniem"""
        try:
            # Zapisz cache
            if hasattr(self.cache, 'save'):
                self.cache.save()

            # Cleanup plików tymczasowych
            if hasattr(self.scraper, 'cleanup_temp_files'):
                self.scraper.cleanup_temp_files()

            logger.debug("Wykonano cleanup CLI commands")

        except Exception as e:
            logger.warning(f"Błąd podczas cleanup: {e}")

    def __enter__(self):
        """Context manager entry"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.cleanup()
        if exc_type is None:
            self.print_session_summary()

    def __repr__(self) -> str:
        """Reprezentacja string obiektu"""
        return f"CLICommands(executed={self.session_stats['commands_executed']}, errors={self.session_stats['errors']})"



def scrape_proceeding(self, args: Dict[str, Any]) -> int:
    """
    Komenda scrapowania konkretnego posiedzenia

    Args:
        args: argumenty komendy
            - term: int - numer kadencji
            - proceeding: int - numer posiedzenia
            - fetch_full_statements: bool - czy pobierać pełną treść

    Returns:
        Kod wyjścia
    """
    logger.info(f"Wykonywanie komendy scrape-proceeding: {args}")

    try:
        from .handlers.scrape_handler import handle_scrape_proceeding

        self.session_stats['commands_executed'] += 1
        return handle_scrape_proceeding(self.scraper, args)

    except Exception as e:
        logger.error(f"Błąd wykonania scrape-proceeding: {e}")
        self.session_stats['errors'] += 1
        return 1


def scrape_date(self, args: Dict[str, Any]) -> int:
    """
    Komenda scrapowania konkretnego dnia posiedzenia

    Args:
        args: argumenty komendy
            - term: int - numer kadencji
            - proceeding: int - numer posiedzenia
            - date: str - data YYYY-MM-DD
            - fetch_full_statements: bool - czy pobierać pełną treść

    Returns:
        Kod wyjścia
    """
    logger.info(f"Wykonywanie komendy scrape-date: {args}")

    try:
        from .handlers.scrape_handler import handle_scrape_date

        self.session_stats['commands_executed'] += 1
        return handle_scrape_date(self.scraper, args)

    except Exception as e:
        logger.error(f"Błąd wykonania scrape-date: {e}")
        self.session_stats['errors'] += 1
        return 1


# === KOMENDY SCRAPOWANIA POSŁÓW ===

def scrape_mps(self, args: Dict[str, Any]) -> int:
    """
    Komenda scrapowania posłów

    Args:
        args: argumenty komendy
            - term: int - numer kadencji
            - download_photos: bool - czy pobierać zdjęcia
            - download_voting_stats: bool - czy pobierać statystyki głosowań

    Returns:
        Kod wyjścia
    """
    logger.info(f"Wykonywanie komendy scrape-mps: {args}")

    try:
        from .handlers.mp_handler import handle_scrape_mps

        self.session_stats['commands_executed'] += 1
        return handle_scrape_mps(self.scraper, args)

    except Exception as e:
        logger.error(f"Błąd wykonania scrape-mps: {e}")
        self.session_stats['errors'] += 1
        return 1


def scrape_clubs(self, args: Dict[str, Any]) -> int:
    """
    Komenda scrapowania klubów parlamentarnych

    Args:
        args: argumenty komendy
            - term: int - numer kadencji

    Returns:
        Kod wyjścia
    """
    logger.info(f"Wykonywanie komendy scrape-clubs: {args}")

    try:
        from .handlers.mp_handler import handle_scrape_clubs

        self.session_stats['commands_executed'] += 1
        return handle_scrape_clubs(self.scraper, args)

    except Exception as e:
        logger.error(f"Błąd wykonania scrape-clubs: {e}")
        self.session_stats['errors'] += 1
        return 1


def scrape_term(self, args: Dict[str, Any]) -> int:
    """
    Komenda scrapowania konkretnej kadencji

    Args:
        args: argumenty komendy
            - term: int — numer kadencji

    Returns:
        Kod wyjścia
    """
    logger.info(f"Wykonywanie komendy scrape-term: {args}")

    try:
        from .handlers.scrape_handler import handle_scrape_term

        self.session_stats['commands_executed'] += 1
        return handle_scrape_term(self.scraper, args)
    except Exception as e:
        logger.error(f"Błąd wykonania scrape-term: {e}")
        self.session_stats['errors'] += 1
        return 1


