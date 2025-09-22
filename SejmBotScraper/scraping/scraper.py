"""
Główny interfejs scrapera - UŻYWA ISTNIEJĄCYCH IMPLEMENTACJI
Skupia się na pobieraniu treści wypowiedzi - używa twoich plików
"""

import logging
from datetime import datetime
from typing import Dict, Optional, List, Any

logger = logging.getLogger(__name__)


class SejmScraper:
    """
    Główny interfejs scrapera - SKUPIONY NA TREŚCI WYPOWIEDZI
    UŻYWA ISTNIEJĄCYCH IMPLEMENTACJI z twoich plików
    """

    def __init__(self, config: Optional[Dict] = None):
        """
        Inicjalizuje scraper z istniejących komponentów

        Args:
            config: konfiguracja scrapera
        """
        self.config = config or {}

        # Inicjalizuj komponenty używając TWOICH implementacji
        self._init_cache()
        self._init_api_client()
        self._init_file_manager()
        self._init_implementation()

        logger.info("SejmScraper zainicjalizowany - używa istniejących implementacji")

    def _init_cache(self):
        """Inicjalizuje cache manager z TWOJEJ implementacji"""
        try:
            # Użyj TWOJEGO cache managera
            from ..cache.manager import CacheInterface
            cache_config = self.config.get('cache', {})
            self.cache_manager = CacheInterface(cache_config)
            logger.debug("Cache manager zainicjalizowany z istniejącej implementacji")
        except ImportError as e:
            logger.warning(f"Cache manager niedostępny: {e}")
            self.cache_manager = None

    def _init_api_client(self):
        """Inicjalizuje API client z TWOJEJ implementacji"""
        try:
            # Użyj TWOJEGO API clienta
            from ..api.client import SejmAPIInterface
            api_config = self.config.get('api', {})
            self.api_client = SejmAPIInterface(self.cache_manager, api_config)

            logger.info("API client zainicjalizowany z istniejącej implementacji")
        except ImportError as e:
            logger.error(f"Nie można zainicjalizować API client: {e}")
            raise RuntimeError(f"API client jest wymagany: {e}")

    def _init_file_manager(self):
        """Inicjalizuje file manager z TWOJEJ implementacji"""
        try:
            # Użyj TWOJEGO file managera
            from ..storage.file_manager import FileManagerInterface
            storage_config = self.config.get('storage', {})
            base_dir = storage_config.get('base_directory', 'data')

            # NAPRAWKA: upewnij się że to string
            if isinstance(base_dir, dict):
                base_dir = base_dir.get('path', 'data')

            self.file_manager = FileManagerInterface(str(base_dir))
            logger.debug("File manager zainicjalizowany z istniejącej implementacji")
        except ImportError as e:
            logger.warning(f"File manager niedostępny: {e}")
            self.file_manager = None

    def _init_implementation(self):
        """Inicjalizuje implementację scrapera z TWOJEJ implementacji"""
        try:
            # Użyj TWOJEJ implementacji
            from .implementations.scraper import SejmScraper as SejmScraperImpl

            self.impl = SejmScraperImpl(
                api_client=self.api_client,
                cache_manager=self.cache_manager,
                config=self.config
            )
            logger.debug("Implementacja scrapera zainicjalizowana z istniejącego kodu")
        except ImportError as e:
            logger.error(f"Nie można zainicjalizować implementacji: {e}")
            # FALLBACK - użyj prostej implementacji
            self.impl = self._create_simple_implementation()

    def _create_simple_implementation(self):
        """Tworzy prostą implementację jako fallback"""
        logger.info("Używam prostej implementacji fallback")

        class SimpleImplementation:
            def __init__(self, api_client, cache_manager, config):
                self.api_client = api_client
                self.cache_manager = cache_manager
                self.config = config or {}
                self.stats = {
                    'proceedings_processed': 0,
                    'statements_processed': 0,
                    'statements_with_full_content': 0,
                    'content_fetch_attempts': 0,
                    'content_fetch_successes': 0,
                    'errors': 0
                }

            def scrape_term(self, term: int, **options):
                logger.info(f"PROSTA IMPLEMENTACJA - scrapowanie kadencji {term}")

                try:
                    # Pobierz posiedzenia
                    proceedings = self.api_client.get_proceedings(term)
                    if not proceedings:
                        logger.error("Nie można pobrać posiedzeń")
                        return self.stats

                    logger.info(f"Znaleziono {len(proceedings)} posiedzeń")

                    # Ogranicz dla testów
                    max_proceedings = options.get('max_proceedings', 2)  # LIMIT
                    test_proceedings = proceedings[:max_proceedings]

                    logger.info(f"Testuję {len(test_proceedings)} posiedzeń")

                    for proceeding in test_proceedings:
                        self._process_simple_proceeding(term, proceeding, **options)
                        self.stats['proceedings_processed'] += 1

                    return self.stats

                except Exception as e:
                    logger.error(f"Błąd simple implementation: {e}")
                    self.stats['errors'] += 1
                    return self.stats

            def _process_simple_proceeding(self, term, proceeding, **options):
                """Prosta implementacja przetwarzania posiedzenia"""
                proc_id = proceeding.get('number')
                dates = proceeding.get('dates', [])[:1]  # Tylko pierwszy dzień

                for date in dates:
                    try:
                        # Pobierz wypowiedzi
                        statements_data = self.api_client.get_statements(term, proc_id, date)
                        if not statements_data or not statements_data.get('statements'):
                            continue

                        statements = statements_data['statements'][:5]  # Tylko 5 wypowiedzi
                        logger.info(f"Przetwarzam {len(statements)} wypowiedzi z {date}")

                        # Test pobierania treści
                        if options.get('fetch_full_statements', True):
                            for stmt in statements:
                                stmt_num = stmt.get('num')
                                if stmt_num is not None:
                                    self.stats['content_fetch_attempts'] += 1

                                    # Pobierz HTML
                                    html = self.api_client.get_statement_html(term, proc_id, date, stmt_num)
                                    if html and len(html.strip()) > 50:
                                        self.stats['content_fetch_successes'] += 1
                                        self.stats['statements_with_full_content'] += 1

                        self.stats['statements_processed'] += len(statements)

                    except Exception as e:
                        logger.error(f"Błąd przetwarzania {date}: {e}")
                        self.stats['errors'] += 1

            def scrape_specific_proceeding(self, term, proceeding_id, **options):
                try:
                    proceedings = self.api_client.get_proceedings(term)
                    proceeding = next((p for p in proceedings if p.get('number') == proceeding_id), None)
                    if proceeding:
                        self._process_simple_proceeding(term, proceeding, **options)
                        return True
                    return False
                except:
                    return False

        return SimpleImplementation(self.api_client, self.cache_manager, self.config)

    # === GŁÓWNE METODY - SKUPIONE NA TREŚCI WYPOWIEDZI ===

    def scrape_term_statements(self, term: int, **options) -> Dict[str, Any]:
        """
        GŁÓWNA METODA - scrapuje wypowiedzi z kadencji z treścią
        UŻYWA PROSTYCH LIMITÓW ŻEBy NIE ZAWIESIĆ
        """
        logger.info(f"Rozpoczynam scrapowanie wypowiedzi kadencji {term}")

        # BEZPIECZNE LIMITY - żeby nie zawiesić
        options.setdefault('fetch_full_statements', True)
        options.setdefault('max_proceedings', 2)  # TYLKO 2 posiedzenia na test
        options.setdefault('max_statements_per_day', 10)  # TYLKO 10 wypowiedzi na dzień

        logger.info("BEZPIECZNE LIMITY: 2 posiedzenia, 10 wypowiedzi na dzień")

        try:
            stats = self.impl.scrape_term(term, **options)

            # Loguj wyniki z fokusem na treści
            statements_total = stats.get('statements_processed', 0)
            statements_with_content = stats.get('statements_with_full_content', 0)

            if statements_total > 0:
                content_percentage = (statements_with_content / statements_total) * 100
                logger.info(f"Pobrano treść dla {content_percentage:.1f}% wypowiedzi")

            return stats

        except Exception as e:
            logger.error(f"Błąd scrapowania kadencji {term}: {e}")
            return {
                'error': str(e),
                'statements_processed': 0,
                'statements_with_full_content': 0,
                'success': False
            }

    def scrape_proceeding_statements(self, term: int, proceeding_id: int, **options) -> bool:
        """Scrapuje wypowiedzi z konkretnego posiedzenia"""
        logger.info(f"Scrapowanie wypowiedzi z posiedzenia {proceeding_id}")

        options.setdefault('fetch_full_statements', True)
        options.setdefault('max_statements_per_day', 20)  # Limit dla pojedynczego posiedzenia

        try:
            return self.impl.scrape_specific_proceeding(term, proceeding_id, **options)
        except Exception as e:
            logger.error(f"Błąd scrapowania posiedzenia {proceeding_id}: {e}")
            return False

    def test_content_fetching(self, term: int = 10, max_tests: int = 3) -> Dict[str, Any]:
        """
        PROSTY test pobierania treści wypowiedzi
        """
        logger.info(f"PROSTY test pobierania treści dla kadencji {term}")

        test_results = {
            'term': term,
            'tests_attempted': 0,
            'tests_successful': 0,
            'success_rate': 0.0,
            'sample_statements': [],
            'errors': []
        }

        try:
            # Pobierz listę posiedzeń
            proceedings = self.api_client.get_proceedings(term)
            if not proceedings:
                test_results['errors'].append("Nie można pobrać listy posiedzeń")
                return test_results

            # Znajdź pierwsze posiedzenie z datami
            test_proceeding = None
            test_date = None

            for proc in proceedings:
                dates = proc.get('dates', [])
                if dates and proc.get('number', 0) > 0:
                    test_proceeding = proc
                    test_date = dates[0]  # Pierwsza data
                    break

            if not test_proceeding:
                test_results['errors'].append("Nie znaleziono posiedzenia do testowania")
                return test_results

            proc_id = test_proceeding.get('number')
            logger.info(f"Test posiedzenia {proc_id} z dnia {test_date}")

            # Pobierz wypowiedzi - użyj prawidłowej metody
            if hasattr(self.api_client, 'get_statements'):
                statements_data = self.api_client.get_statements(term, proc_id, test_date)
            elif hasattr(self.api_client, 'get_transcripts_list'):
                statements_data = self.api_client.get_transcripts_list(term, proc_id, test_date)
            else:
                test_results['errors'].append("API client nie ma metody pobierania wypowiedzi")
                return test_results

            if not statements_data or not statements_data.get('statements'):
                test_results['errors'].append("Nie można pobrać wypowiedzi")
                return test_results

            statements = statements_data['statements'][:max_tests]

            # Testuj pobieranie treści
            for stmt in statements:
                stmt_num = stmt.get('num')
                if stmt_num is not None:
                    test_results['tests_attempted'] += 1

                    # Pobierz HTML
                    html_content = self.api_client.get_statement_html(term, proc_id, test_date, stmt_num)

                    if html_content and len(html_content.strip()) > 50:
                        test_results['tests_successful'] += 1

                        # Pobierz tekst jeśli możliwe
                        text_content = ""
                        if hasattr(self.api_client, 'get_statement_text'):
                            text_content = self.api_client.get_statement_text(term, proc_id, test_date, stmt_num) or ""

                        test_results['sample_statements'].append({
                            'statement_num': stmt_num,
                            'speaker': stmt.get('name', 'Nieznany'),
                            'content_length': len(text_content) if text_content else len(html_content),
                            'preview': (text_content or html_content)[:100] + '...'
                        })

            # Oblicz wskaźnik sukcesu
            if test_results['tests_attempted'] > 0:
                test_results['success_rate'] = (test_results['tests_successful'] / test_results[
                    'tests_attempted']) * 100

            logger.info(f"Test zakończony: {test_results['success_rate']:.1f}% sukcesu")
            return test_results

        except Exception as e:
            test_results['errors'].append(f"Błąd testu: {e}")
            return test_results

    # === METODY POMOCNICZE ===

    def get_available_terms(self) -> Optional[List[Dict]]:
        """Pobiera dostępne kadencje"""
        try:
            if hasattr(self.api_client, 'get_terms'):
                return self.api_client.get_terms()
            return None
        except Exception as e:
            logger.error(f"Błąd pobierania kadencji: {e}")
            return None

    def get_term_proceedings(self, term: int) -> Optional[List[Dict]]:
        """Pobiera posiedzenia kadencji"""
        try:
            return self.api_client.get_proceedings(term)
        except Exception as e:
            logger.error(f"Błąd pobierania posiedzeń: {e}")
            return None

    def get_stats(self) -> Dict[str, Any]:
        """Zwraca statystyki scrapera"""
        stats = {
            'scraper_initialized': True,
            'api_client_available': self.api_client is not None,
            'cache_manager_available': self.cache_manager is not None,
            'file_manager_available': self.file_manager is not None,
            'implementation_available': hasattr(self, 'impl')
        }

        if hasattr(self, 'impl') and hasattr(self.impl, 'stats'):
            stats.update(self.impl.stats)

        return stats

    def health_check(self) -> Dict[str, Any]:
        """PROSTY health check bez blokujących operacji"""
        health = {
            'healthy': True,
            'components': {},
            'focus': 'content_fetching',
            'timestamp': datetime.now().isoformat()
        }

        # Sprawdź komponenty bez wykonywania requestów
        health['components']['api_client'] = {
            'status': 'available' if self.api_client else 'missing',
            'healthy': self.api_client is not None
        }

        health['components']['cache_manager'] = {
            'status': 'available' if self.cache_manager else 'missing',
            'healthy': True  # Cache nie jest krytyczny
        }

        health['components']['file_manager'] = {
            'status': 'available' if self.file_manager else 'missing',
            'healthy': True  # File manager nie jest krytyczny
        }

        if not self.api_client:
            health['healthy'] = False

        return health

    # Aliases dla kompatybilności z istniejącym kodem
    def scrape_term(self, term: int, **options) -> Dict[str, Any]:
        """Alias dla scrape_term_statements"""
        return self.scrape_term_statements(term, **options)

    def scrape_specific_proceeding(self, term: int, proceeding_id: int, **options) -> bool:
        """Alias dla scrape_proceeding_statements"""
        return self.scrape_proceeding_statements(term, proceeding_id, **options)

    def __repr__(self) -> str:
        return f"SejmScraper(focus=content_fetching, components_loaded=True)"
