"""
Główny interfejs scrapera — orkiestruje wszystkie operacje scrapowania
Mały plik interfejsowy — implementacje w osobnych plikach
"""

import logging
from datetime import datetime
from typing import Dict, Optional, List, Union

from ..core.types import ScrapingStats, MPScrapingStats, ScrapingConfig, TermInfo

logger = logging.getLogger(__name__)


class SejmScraper:
    """
    Główny interfejs do scrapowania danych Sejmu

    Orkiestruje wszystkie operacje scrapowania - stenogramów, posłów, klubów.
    Implementacje znajdują się w osobnych plikach.
    """

    def __init__(self, config: Optional[ScrapingConfig] = None):
        """
        Inicjalizuje scraper

        Args:
            config: konfiguracja scrapowania (opcjonalna)
        """
        self.config = config or {}

        # Import implementacji dopiero tutaj aby uniknąć circular imports
        from SejmBotScraper import MPScraper
        from SejmBotScraper import SejmScraper

        self.scraper = SejmScraper(config)
        self.mp_scraper = MPScraper(config)

        logger.debug("Zainicjalizowano główny scraper")

    # === SCRAPOWANIE STENOGRAMÓW ===

    def scrape_term(self, term: int, **options) -> ScrapingStats:
        """
        Scrapuje wszystkie stenogramy z danej kadencji

        Args:
            term: numer kadencji
            **options: dodatkowe opcje scrapowania
                - fetch_full_statements: bool - czy pobierać pełną treść
                - force_refresh: bool - czy wymusić odświeżenie
                - skip_future: bool - czy pomijać przyszłe posiedzenia

        Returns:
            Statystyki scrapowania
        """
        logger.info(f"Rozpoczynanie scrapowania stenogramów kadencji {term}")

        start_time = datetime.now()
        try:
            stats = self.scraper.scrape_term(term, **options)

            # Aktualizuj czasy w statystykach
            stats['end_time'] = datetime.now()
            stats['duration_seconds'] = (stats['end_time'] - start_time).total_seconds()

            logger.info(f"Zakończono scrapowanie kadencji {term} w {stats['duration_seconds']:.1f}s")
            return stats

        except Exception as e:
            logger.error(f"Błąd scrapowania kadencji {term}: {e}")
            # Zwróć stats z błędem
            from ..core.types import create_empty_stats
            stats = create_empty_stats()
            stats['errors'] = 1
            stats['end_time'] = datetime.now()
            stats['duration_seconds'] = (stats['end_time'] - start_time).total_seconds()
            return stats

    def scrape_proceeding(self, term: int, proceeding: int, **options) -> bool:
        """
        Scrapuje konkretne posiedzenie

        Args:
            term: numer kadencji
            proceeding: numer posiedzenia
            **options: dodatkowe opcje scrapowania

        Returns:
            True jeśli sukces, False w przypadku błędu
        """
        logger.info(f"Scrapowanie posiedzenia {proceeding} kadencji {term}")

        try:
            return self.scraper.scrape_proceeding(term, proceeding, **options)
        except Exception as e:
            logger.error(f"Błąd scrapowania posiedzenia {proceeding}: {e}")
            return False

    def scrape_proceeding_date(self, term: int, proceeding: int, date: str, **options) -> bool:
        """
        Scrapuje konkretny dzień posiedzenia

        Args:
            term: numer kadencji
            proceeding: numer posiedzenia
            date: data w formacie YYYY-MM-DD
            **options: dodatkowe opcje

        Returns:
            True jeśli sukces
        """
        logger.info(f"Scrapowanie dnia {date} posiedzenia {proceeding} kadencji {term}")

        try:
            return self.scraper.scrape_proceeding_date(term, proceeding, date, **options)
        except Exception as e:
            logger.error(f"Błąd scrapowania dnia {date}: {e}")
            return False

    # === SCRAPOWANIE POSŁÓW ===

    def scrape_mps(self, term: int, **options) -> MPScrapingStats:
        """
        Scrapuje dane posłów z danej kadencji

        Args:
            term: numer kadencji
            **options: dodatkowe opcje scrapowania
                - download_photos: bool - czy pobierać zdjęcia
                - download_voting_stats: bool - czy pobierać statystyki głosowań

        Returns:
            Statystyki scrapowania posłów
        """
        logger.info(f"Rozpoczynanie scrapowania posłów kadencji {term}")

        try:
            return self.mp_scraper.scrape_mps(term, **options)
        except Exception as e:
            logger.error(f"Błąd scrapowania posłów kadencji {term}: {e}")
            from ..core.types import create_empty_mp_stats
            stats = create_empty_mp_stats()
            stats['errors'] = 1
            return stats

    def scrape_clubs(self, term: int, **options) -> MPScrapingStats:
        """
        Scrapuje dane klubów parlamentarnych

        Args:
            term: numer kadencji
            **options: dodatkowe opcje scrapowania

        Returns:
            Statystyki scrapowania klubów
        """
        logger.info(f"Scrapowanie klubów parlamentarnych kadencji {term}")

        try:
            return self.mp_scraper.scrape_clubs(term, **options)
        except Exception as e:
            logger.error(f"Błąd scrapowania klubów kadencji {term}: {e}")
            from ..core.types import create_empty_mp_stats
            stats = create_empty_mp_stats()
            stats['errors'] = 1
            return stats

    def scrape_specific_mp(self, term: int, mp_id: int, **options) -> bool:
        """
        Scrapuje dane konkretnego posła

        Args:
            term: numer kadencji
            mp_id: ID posła
            **options: dodatkowe opcje

        Returns:
            True jeśli sukces
        """
        logger.info(f"Scrapowanie posła ID {mp_id} kadencji {term}")

        try:
            return self.mp_scraper.scrape_specific_mp(term, mp_id, **options)
        except Exception as e:
            logger.error(f"Błąd scrapowania posła {mp_id}: {e}")
            return False

    # === SCRAPOWANIE KOMPLETNE ===

    def scrape_complete_term(self, term: int, **options) -> Dict[str, Union[ScrapingStats, MPScrapingStats]]:
        """
        Scrapuje kompletne dane kadencji - stenogramy, posłowie, kluby

        Args:
            term: numer kadencji
            **options: opcje scrapowania dla wszystkich komponentów

        Returns:
            Słownik ze statystykami wszystkich komponentów
        """
        logger.info(f"Rozpoczynanie kompletnego scrapowania kadencji {term}")

        results = {}
        start_time = datetime.now()

        # 1. Scrapuj kluby (szybkie, potrzebne do wzbogacania)
        logger.info("Krok 1/3: Scrapowanie klubów parlamentarnych")
        results['clubs'] = self.scrape_clubs(term, **options)

        # 2. Scrapuj posłów (potrzebne do wzbogacania stenogramów)
        logger.info("Krok 2/3: Scrapowanie danych posłów")
        results['mps'] = self.scrape_mps(term, **options)

        # 3. Scrapuj stenogramy (najdłuższe)
        logger.info("Krok 3/3: Scrapowanie stenogramów")
        results['transcripts'] = self.scrape_term(term, **options)

        total_duration = (datetime.now() - start_time).total_seconds()
        logger.info(f"Zakończono kompletne scrapowanie kadencji {term} w {total_duration:.1f}s")

        # Dodaj podsumowanie
        results['summary'] = {
            'term': term,
            'total_duration_seconds': total_duration,
            'completed_at': datetime.now().isoformat(),
            'success': all(
                result.get('errors', 0) == 0 for result in results.values()
                if isinstance(result, dict) and 'errors' in result
            )
        }

        return results

    # === INFORMACJE I POMOCNICZE ===

    def get_available_terms(self) -> Optional[List[TermInfo]]:
        """
        Pobiera listę dostępnych kadencji

        Returns:
            Lista kadencji lub None w przypadku błędu
        """
        logger.debug("Pobieranie dostępnych kadencji")
        return self.scraper.get_available_terms()

    def get_term_proceedings_summary(self, term: int) -> Optional[List[Dict]]:
        """
        Pobiera podsumowanie posiedzeń kadencji

        Args:
            term: numer kadencji

        Returns:
            Lista z podstawowymi informacjami o posiedzeniach
        """
        logger.debug(f"Pobieranie podsumowania posiedzeń kadencji {term}")
        return self.scraper.get_term_proceedings_summary(term)

    def get_scraping_stats(self) -> Dict:
        """
        Zwraca łączne statystyki scrapowania

        Returns:
            Słownik ze statystykami
        """
        transcript_stats = getattr(self.scraper, 'stats', {})
        mp_stats = getattr(self.mp_scraper, 'stats', {})

        return {
            'transcript_scraper': transcript_stats,
            'mp_scraper': mp_stats,
            'timestamp': datetime.now().isoformat()
        }

    # === ZARZĄDZANIE CACHE ===

    def clear_cache(self, cache_type: str = "all") -> None:
        """
        Czyści cache wszystkich scraperów

        Args:
            cache_type: typ cache do wyczyszczenia
        """
        logger.info(f"Czyszczenie cache scraperów: {cache_type}")

        try:
            self.scraper.clear_cache()
            self.mp_scraper.clear_cache()
        except Exception as e:
            logger.warning(f"Błąd czyszczenia cache: {e}")

    def cleanup_cache(self) -> None:
        """Czyści stare wpisy z cache"""
        logger.info("Czyszczenie starych wpisów cache")

        try:
            if hasattr(self.scraper, 'cleanup_cache'):
                self.scraper.cleanup_cache()
            if hasattr(self.mp_scraper, 'cleanup_cache'):
                self.mp_scraper.cleanup_cache()
        except Exception as e:
            logger.warning(f"Błąd czyszczenia starych wpisów: {e}")

    def get_cache_stats(self) -> Dict:
        """
        Zwraca statystyki cache wszystkich scraperów

        Returns:
            Łączne statystyki cache
        """
        stats = {}

        try:
            if hasattr(self.scraper, 'get_cache_stats'):
                stats['transcript_scraper'] = self.scraper.get_cache_stats()
        except Exception as e:
            logger.debug(f"Nie można pobrać stats transcript_scraper: {e}")
            stats['transcript_scraper'] = {}

        try:
            if hasattr(self.mp_scraper, 'get_cache_stats'):
                stats['mp_scraper'] = self.mp_scraper.get_cache_stats()
        except Exception as e:
            logger.debug(f"Nie można pobrać stats mp_scraper: {e}")
            stats['mp_scraper'] = {}

        return stats

    # === WALIDACJA I HEALTH CHECK ===

    def validate_term(self, term: int) -> bool:
        """
        Sprawdza czy kadencja jest dostępna

        Args:
            term: numer kadencji

        Returns:
            True jeśli kadencja istnieje
        """
        try:
            terms = self.get_available_terms()
            if not terms:
                return False

            return any(t.get('num') == term for t in terms)
        except Exception:
            return False

    def health_check(self) -> Dict:
        """
        Sprawdza stan scraperów

        Returns:
            Słownik ze stanem zdrowia
        """
        health = {
            'healthy': True,
            'timestamp': datetime.now().isoformat(),
            'components': {}
        }

        # Sprawdź transcript scraper
        try:
            terms = self.get_available_terms()
            health['components']['transcript_scraper'] = {
                'healthy': terms is not None,
                'terms_available': len(terms) if terms else 0
            }
        except Exception as e:
            health['components']['transcript_scraper'] = {
                'healthy': False,
                'error': str(e)
            }
            health['healthy'] = False

        # Sprawdź mp scraper
        try:
            # Próbuj pobrać listę posłów dla domyślnej kadencji
            from ..config.settings import get_settings
            settings = get_settings()
            default_term = settings.get('default_term')

            mps = self.mp_scraper.get_mps_summary(default_term)
            health['components']['mp_scraper'] = {
                'healthy': mps is not None,
                'default_term': default_term
            }
        except Exception as e:
            health['components']['mp_scraper'] = {
                'healthy': False,
                'error': str(e)
            }
            health['healthy'] = False

        return health

    def __repr__(self) -> str:
        """Reprezentacja string obiektu"""
        return f"SejmScraper(transcript={self.scraper.__class__.__name__}, mp={self.mp_scraper.__class__.__name__})"
