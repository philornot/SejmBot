"""
Główny interfejs scrapera - orkiestruje wszystkie operacje scrapowania
NAPRAWIONA WERSJA - używa poprawnych implementacji
"""

import logging
from datetime import datetime
from typing import Dict, Optional, List, Union

logger = logging.getLogger(__name__)


class SejmScraper:
    """
    Główny interfejs do scrapowania danych Sejmu
    NAPRAWIONA WERSJA - integruje naprawiony API client i cache
    """

    def __init__(self, config: Optional[Dict] = None):
        """
        Inicjalizuje scraper

        Args:
            config: konfiguracja scrapowania (opcjonalna)
        """
        self.config = config or {}

        # Zainicjalizuj naprawiony cache
        logger.debug("Inicjalizuję naprawiony cache manager...")
        try:
            from ..cache.manager import CacheInterface
            self.cache_manager = CacheInterface(self.config.get('cache', {}))
            logger.info("✓ Cache manager załadowany")
        except ImportError as e:
            logger.warning(f"Nie można załadować cache managera: {e}")
            self.cache_manager = None

        # Zainicjalizuj naprawiony API client
        logger.info("Inicjalizuję naprawiony API client...")
        try:
            from ..api.sejm_client import SejmAPIClient
            self.api_client = SejmAPIClient(
                cache_manager=self.cache_manager,
                config=self.config.get('api', {})
            )

            # Test połączenia
            logger.info("Testowanie połączenia z API...")
            test_result = self.api_client.test_connection()
            if test_result['total_score'] >= 2:
                logger.info("✓ API client działa poprawnie")
            else:
                logger.error("✗ API client ma problemy:")
                for error in test_result.get('errors', []):
                    logger.error(f"  - {error}")

        except ImportError as e:
            logger.error(f"BŁĄD: Nie można załadować naprawionego API clienta: {e}")
            # Fallback do starego interfejsu
            try:
                from ..api.client import SejmAPIInterface
                self.api_client = SejmAPIInterface(self.cache_manager, self.config.get('api', {}))
                logger.warning("Używam starego API interface jako fallback")
            except ImportError:
                raise RuntimeError("Nie można załadować żadnego API clienta")

        # Zainicjalizuj implementację scrapera
        logger.debug("Inicjalizuję implementację scrapera...")
        try:
            from .implementations.scraper import SejmScraper as SejmScraperImpl
            self.scraper_impl = SejmScraperImpl(
                api_client=self.api_client,
                cache_manager=self.cache_manager,
                config=self.config
            )
            logger.info("✓ Implementacja scrapera załadowana")
        except ImportError as e:
            logger.error(f"Nie można załadować implementacji scrapera: {e}")
            raise RuntimeError("Implementacja scrapera nie jest dostępna")

        # Zainicjalizuj MP scraper
        logger.debug("Inicjalizuję MP scraper...")
        try:
            from .implementations.mp_scraper import MPScraper
            self.mp_scraper = MPScraper(self.config.get('scraping', {}))
            logger.debug("✓ MP scraper załadowany")
        except ImportError as e:
            logger.warning(f"Nie można załadować MP scrapera: {e}")
            self.mp_scraper = None

        logger.info("SejmScraper zainicjalizowany pomyślnie")

    # === SCRAPOWANIE STENOGRAMÓW ===

    def scrape_term(self, term: int, **options) -> Dict:
        """Scrapuje wszystkie stenogramy z danej kadencji"""
        logger.info(f"Rozpoczynanie scrapowania stenogramów kadencji {term}")

        start_time = datetime.now()
        try:
            # Deleguj do implementacji
            stats = self.scraper_impl.scrape_term(term, **options)

            # Aktualizuj czasy w statystykach
            if isinstance(stats, dict):
                stats['end_time'] = datetime.now()
                stats['duration_seconds'] = (stats['end_time'] - start_time).total_seconds()

            logger.info(f"Zakończono scrapowanie kadencji {term} w {stats.get('duration_seconds', 0):.1f}s")
            return stats

        except Exception as e:
            logger.error(f"Błąd scrapowania kadencji {term}: {e}")
            stats = {
                'errors': 1,
                'proceedings_processed': 0,
                'statements_processed': 0,
                'statements_with_full_content': 0,
                'speakers_identified': 0,
                'mp_data_enrichments': 0,
                'future_proceedings_skipped': 0,
                'proceedings_skipped_cache': 0,
                'transcripts_skipped_cache': 0,
                'start_time': start_time,
                'end_time': datetime.now(),
                'duration_seconds': (datetime.now() - start_time).total_seconds(),
                'error_message': str(e)
            }
            return stats

    def scrape_proceeding(self, term: int, proceeding: int, **options) -> bool:
        """Scrapuje konkretne posiedzenie"""
        logger.info(f"Scrapowanie posiedzenia {proceeding} kadencji {term}")

        try:
            return self.scraper_impl.scrape_specific_proceeding(term, proceeding, **options)
        except Exception as e:
            logger.error(f"Błąd scrapowania posiedzenia {proceeding}: {e}")
            return False

    def scrape_proceeding_date(self, term: int, proceeding: int, date: str, **options) -> bool:
        """Scrapuje konkretny dzień posiedzenia"""
        logger.info(f"Scrapowanie dnia {date} posiedzenia {proceeding} kadencji {term}")

        try:
            return self.scraper_impl.scrape_proceeding_date(term, proceeding, date, **options)
        except Exception as e:
            logger.error(f"Błąd scrapowania dnia {date}: {e}")
            return False

    # === SCRAPOWANIE POSŁÓW ===

    def scrape_mps(self, term: int, **options) -> Dict:
        """Scrapuje dane posłów z danej kadencji"""
        logger.info(f"Rozpoczynanie scrapowania posłów kadencji {term}")

        if not self.mp_scraper:
            logger.error("MP scraper nie jest dostępny")
            return {
                'mps_downloaded': 0,
                'clubs_downloaded': 0,
                'photos_downloaded': 0,
                'voting_stats_downloaded': 0,
                'errors': 1,
                'error_message': 'MP scraper not available'
            }

        try:
            return self.mp_scraper.scrape_mps(term, **options)
        except Exception as e:
            logger.error(f"Błąd scrapowania posłów kadencji {term}: {e}")
            return {
                'mps_downloaded': 0,
                'clubs_downloaded': 0,
                'photos_downloaded': 0,
                'voting_stats_downloaded': 0,
                'errors': 1,
                'error_message': str(e)
            }

    def scrape_clubs(self, term: int, **options) -> Dict:
        """Scrapuje dane klubów parlamentarnych"""
        logger.info(f"Scrapowanie klubów parlamentarnych kadencji {term}")

        if not self.mp_scraper:
            logger.error("MP scraper nie jest dostępny")
            return {
                'mps_downloaded': 0,
                'clubs_downloaded': 0,
                'photos_downloaded': 0,
                'voting_stats_downloaded': 0,
                'errors': 1,
                'error_message': 'MP scraper not available'
            }

        try:
            return self.mp_scraper.scrape_clubs(term, **options)
        except Exception as e:
            logger.error(f"Błąd scrapowania klubów kadencji {term}: {e}")
            return {
                'mps_downloaded': 0,
                'clubs_downloaded': 0,
                'photos_downloaded': 0,
                'voting_stats_downloaded': 0,
                'errors': 1,
                'error_message': str(e)
            }

    def scrape_specific_mp(self, term: int, mp_id: int, **options) -> bool:
        """Scrapuje dane konkretnego posła"""
        logger.info(f"Scrapowanie posła ID {mp_id} kadencji {term}")

        if not self.mp_scraper:
            logger.error("MP scraper nie jest dostępny")
            return False

        try:
            return self.mp_scraper.scrape_specific_mp(term, mp_id, **options)
        except Exception as e:
            logger.error(f"Błąd scrapowania posła {mp_id}: {e}")
            return False

    # === SCRAPOWANIE KOMPLETNE ===

    def scrape_complete_term(self, term: int, **options) -> Dict[str, Union[Dict, int]]:
        """Scrapuje kompletne dane kadencji - stenogramy, posłowie, kluby"""
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

    def get_available_terms(self) -> Optional[List[Dict]]:
        """Pobiera listę dostępnych kadencji"""
        logger.debug("Pobieranie dostępnych kadencji")
        try:
            if hasattr(self.api_client, 'get_terms'):
                terms = self.api_client.get_terms()
                if terms:
                    logger.info(f"Znaleziono {len(terms)} dostępnych kadencji")
                return terms
            else:
                # Mock data jako fallback
                logger.warning("API client nie ma metody get_terms, używam mock data")
                return [
                    {'num': 9, 'from': '2019-11-12', 'to': '2023-11-12'},
                    {'num': 10, 'from': '2023-11-13', 'to': None}
                ]
        except Exception as e:
            logger.error(f"Błąd pobierania kadencji: {e}")
            return None

    def get_term_proceedings_summary(self, term: int) -> Optional[List[Dict]]:
        """Pobiera podsumowanie posiedzeń kadencji"""
        logger.debug(f"Pobieranie podsumowania posiedzeń kadencji {term}")
        try:
            return self.scraper_impl.get_term_proceedings_summary(term)
        except Exception as e:
            logger.error(f"Błąd pobierania podsumowania: {e}")
            return None

    def get_scraping_stats(self) -> Dict:
        """Zwraca łączne statystyki scrapowania"""
        transcript_stats = getattr(self.scraper_impl, 'stats', {})
        mp_stats = getattr(self.mp_scraper, 'stats', {}) if self.mp_scraper else {}

        return {
            'transcript_scraper': transcript_stats,
            'mp_scraper': mp_stats,
            'timestamp': datetime.now().isoformat(),
            'api_client_type': self.api_client.__class__.__name__,
            'cache_available': self.cache_manager is not None
        }

    # === ZARZĄDZANIE CACHE ===

    def clear_cache(self, cache_type: str = "all") -> None:
        """Czyści cache wszystkich scraperów"""
        logger.info(f"Czyszczenie cache scraperów: {cache_type}")

        if self.cache_manager:
            try:
                if cache_type == "all":
                    self.cache_manager.clear_all()
                elif cache_type == "api":
                    self.cache_manager.clear_api_cache()
                elif cache_type == "file":
                    self.cache_manager.clear_file_cache()
                else:
                    self.cache_manager.clear()

                logger.info("Cache wyczyszczony")
            except Exception as e:
                logger.error(f"Błąd czyszczenia cache: {e}")
        else:
            logger.warning("Cache manager nie jest dostępny")

        # Wyczyść także cache API clienta
        if hasattr(self.api_client, 'clear_cache'):
            try:
                self.api_client.clear_cache(cache_type)
            except Exception as e:
                logger.warning(f"Błąd czyszczenia cache API clienta: {e}")

    def cleanup_cache(self) -> None:
        """Czyści stare wpisy z cache"""
        logger.info("Czyszczenie starych wpisów cache")

        if self.cache_manager:
            try:
                cleaned = self.cache_manager.cleanup_expired()
                total_cleaned = sum(cleaned.values()) if isinstance(cleaned, dict) else cleaned
                logger.info(f"Wyczyszczono {total_cleaned} starych wpisów")
            except Exception as e:
                logger.error(f"Błąd czyszczenia starych wpisów: {e}")
        else:
            logger.warning("Cache manager nie jest dostępny")

    def get_cache_stats(self) -> Dict:
        """Zwraca statystyki cache wszystkich scraperów"""
        if not self.cache_manager:
            return {
                'memory_cache': {'entries': 0, 'size_mb': 0},
                'file_cache': {'entries': 0, 'size_mb': 0},
                'error': 'Cache manager not available'
            }

        try:
            return self.cache_manager.get_stats()
        except Exception as e:
            logger.error(f"Błąd pobierania statystyk cache: {e}")
            return {
                'memory_cache': {'entries': 0, 'size_mb': 0},
                'file_cache': {'entries': 0, 'size_mb': 0},
                'error': str(e)
            }

    # === WALIDACJA I HEALTH CHECK ===

    def validate_term(self, term: int) -> bool:
        """Sprawdza czy kadencja jest dostępna"""
        try:
            terms = self.get_available_terms()
            if not terms:
                return False

            return any(t.get('num') == term for t in terms)
        except Exception:
            return False

    def health_check(self) -> Dict:
        """Sprawdza stan scraperów"""
        health = {
            'healthy': True,
            'timestamp': datetime.now().isoformat(),
            'components': {}
        }

        # Sprawdź API client
        try:
            if hasattr(self.api_client, 'test_connection'):
                api_test = self.api_client.test_connection()
                health['components']['api_client'] = {
                    'healthy': api_test.get('total_score', 0) >= 2,
                    'score': f"{api_test.get('total_score', 0)}/3",
                    'errors': api_test.get('errors', [])
                }
                if not health['components']['api_client']['healthy']:
                    health['healthy'] = False
            else:
                # Podstawowy test
                terms = self.get_available_terms()
                health['components']['api_client'] = {
                    'healthy': terms is not None and len(terms) > 0,
                    'terms_available': len(terms) if terms else 0
                }
                if not health['components']['api_client']['healthy']:
                    health['healthy'] = False
        except Exception as e:
            health['components']['api_client'] = {
                'healthy': False,
                'error': str(e)
            }
            health['healthy'] = False

        # Sprawdź cache manager
        try:
            if self.cache_manager:
                cache_health = self.cache_manager.health_check()
                health['components']['cache_manager'] = cache_health
                if not cache_health.get('healthy', True):
                    health['healthy'] = False
            else:
                health['components']['cache_manager'] = {
                    'healthy': False,
                    'error': 'Cache manager not available'
                }
        except Exception as e:
            health['components']['cache_manager'] = {
                'healthy': False,
                'error': str(e)
            }

        # Sprawdź scraper implementation
        try:
            health['components']['scraper_impl'] = {
                'healthy': self.scraper_impl is not None,
                'type': self.scraper_impl.__class__.__name__ if self.scraper_impl else 'None'
            }
            if not health['components']['scraper_impl']['healthy']:
                health['healthy'] = False
        except Exception as e:
            health['components']['scraper_impl'] = {
                'healthy': False,
                'error': str(e)
            }
            health['healthy'] = False

        # Sprawdź MP scraper
        health['components']['mp_scraper'] = {
            'healthy': self.mp_scraper is not None,
            'type': self.mp_scraper.__class__.__name__ if self.mp_scraper else 'None'
        }

        return health

    def __repr__(self) -> str:
        """Reprezentacja string obiektu"""
        api_type = self.api_client.__class__.__name__ if self.api_client else 'None'
        cache_type = self.cache_manager.__class__.__name__ if self.cache_manager else 'None'

        return f"SejmScraper(api={api_type}, cache={cache_type})"
