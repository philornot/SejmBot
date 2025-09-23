"""
Naprawiona implementacja klienta API Sejmu RP z działającym pobieraniem treści wypowiedzi
Główne poprawki:
1. Uproszczenie logiki pobierania HTML
2. Lepsze error handling i debugowanie
3. Optymalizacja retry logic
4. Walidacja odpowiedzi API
"""

import logging
import re
import time
import random
from typing import List, Dict, Optional, Any

import requests

logger = logging.getLogger(__name__)


class SejmAPIClient:
    """Naprawiona implementacja klienta API Sejmu RP"""

    def __init__(self, cache_manager=None, config=None):
        """Inicjalizuje klient API"""
        self.config = config or {}
        self.base_url = self.config.get('base_url', 'https://api.sejm.gov.pl')
        self.request_timeout = self.config.get('timeout', 30)
        self.request_delay = self.config.get('delay', 0.2)  # Zmniejszone opóźnienie
        self.user_agent = self.config.get('user_agent', 'SejmBotScraper/3.0')

        # Sesja HTTP z lepszymi headerami
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': self.user_agent,
            'Accept': 'application/json, text/html, */*',
            'Accept-Language': 'pl,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive'
        })

        logger.info(f"Zainicjalizowano SejmAPIClient")
        logger.debug(f"Base URL: {self.base_url}")
        logger.debug(f"Cache: {'włączony' if cache_manager else 'wyłączony'}")
        self.cache = cache_manager

        # Backoff config
        self.min_backoff = float(self.config.get('min_backoff', 0.5))
        self.max_backoff = float(self.config.get('max_backoff', 30.0))

        logger.info(f"Zainicjalizowano SejmAPIClient")
        logger.debug(f"Base URL: {self.base_url}")
        logger.debug(f"Cache: {'włączony' if cache_manager else 'wyłączony'}")

    def _make_request(self, endpoint: str, params: Optional[Dict] = None,
                      use_cache: bool = True, retry_count: int = 2,
                      expected_content_type: Optional[str] = None) -> Optional[Any]:
        """
        NAPRAWIONA metoda wykonująca zapytanie do API
        """
        url = f"{self.base_url}{endpoint}"
        cache_key = self._generate_cache_key(endpoint, params)

        # Sprawdź cache jeśli dostępny
        if use_cache and self.cache:
            cached_data = self.cache.get(cache_key)
            if cached_data is not None:
                logger.debug(f"Cache hit: {endpoint}")
                return cached_data

        # Retry / backoff logic with jitter and handling Retry-After
        for attempt in range(retry_count):
            try:
                if attempt > 0:
                    logger.debug(f"Próba {attempt + 1}/{retry_count} dla {endpoint}")

                # Rate limiting small pause
                time.sleep(self.request_delay)

                response = self.session.get(url, params=params, timeout=self.request_timeout)

                logger.debug(f"Request: {url}")
                logger.debug(
                    f"Status: {response.status_code}, Content-Type: {response.headers.get('content-type', 'unknown')}")

                # Handle common HTTP response codes
                if response.status_code in (403, 404):
                    logger.debug(f"{response.status_code} dla {url}")
                    return None

                if response.status_code == 429:
                    # Respect Retry-After header if present
                    retry_after = response.headers.get('Retry-After') or response.headers.get('retry-after')
                    try:
                        wait = float(retry_after) if retry_after else None
                    except Exception:
                        wait = None

                    if wait is None:
                        # exponential backoff with jitter
                        wait = min(self.max_backoff, self.min_backoff * (2 ** attempt))
                        wait = wait + random.random()

                    logger.warning(f"429 Too Many Requests: {url} - retry after {wait}s")
                    if attempt < retry_count - 1:
                        time.sleep(wait)
                        continue
                    return None

                if response.status_code >= 500:
                    # server error - backoff and retry
                    wait = min(self.max_backoff, self.min_backoff * (2 ** attempt))
                    wait = wait + random.random()
                    logger.warning(f"Server Error {response.status_code}: {url} - retrying in {wait}s")
                    if attempt < retry_count - 1:
                        time.sleep(wait)
                        continue
                    return None

                response.raise_for_status()
                response.encoding = 'utf-8'

                if not response.content:
                    logger.debug(f"Pusta odpowiedź z {url}")
                    return None

                # Sprawdź typ zawartości
                content_type = response.headers.get('content-type', '').lower()

                if 'application/json' in content_type:
                    try:
                        json_data = response.json()

                        # Sprawdź czy to nie jest error response z API Sejmu
                        if isinstance(json_data, dict) and 'supportID' in json_data and len(json_data) == 1:
                            logger.debug(f"API zwróciło tylko supportID - endpoint nieobsługiwany")
                            return None

                        # Zapisz do cache
                        if use_cache and self.cache and json_data is not None:
                            ttl = self._get_cache_ttl(endpoint, json_data)
                            self.cache.set(cache_key, json_data, ttl)

                        return json_data

                    except ValueError as e:
                        logger.error(f"Błąd parsowania JSON z {url}: {e}")
                        continue

                elif 'text/html' in content_type:
                    html_content = response.text

                    # Walidacja HTML - czy zawiera sensowną treść
                    if self._validate_html_content(html_content):
                        if use_cache and self.cache:
                            ttl = self._get_cache_ttl(endpoint, html_content)
                            self.cache.set(cache_key, html_content, ttl)
                        return html_content
                    else:
                        logger.debug(f"HTML nie zawiera sensownej treści")
                        return None
                else:
                    # Zawartość binarna
                    if use_cache and self.cache:
                        self.cache.set(cache_key, response.content, 3600)
                    return response.content

            except requests.exceptions.Timeout:
                logger.warning(f"Timeout dla {url}")
                if attempt < retry_count - 1:
                    continue
            except requests.exceptions.RequestException as e:
                logger.error(f"Request error dla {url}: {e}")
                if attempt < retry_count - 1:
                    continue

        logger.error(f"Wszystkie próby nieudane dla {url}")
        return None

    def _validate_html_content(self, html_content: str) -> bool:
        """
        NOWA METODA - waliduje czy HTML zawiera sensowną treść
        """
        if not html_content or len(html_content.strip()) < 50:
            return False

        # Sprawdź czy to nie jest strona błędu
        error_indicators = [
            'error', 'błąd', 'not found', 'nie znaleziono',
            'access denied', 'dostęp zabroniony', 'supportID'
        ]

        content_lower = html_content.lower()
        if any(indicator in content_lower for indicator in error_indicators):
            return False

        # Sprawdź czy zawiera podstawowe znaczniki HTML lub wystarczająco dużo tekstu
        has_html = any(tag in content_lower for tag in ['<html', '<body', '<p', '<div'])
        has_content = len(html_content.strip()) > 200

        return has_html or has_content

    def _clean_html_to_text(self, html_content: str) -> str:
        """
        UPROSZCZONA METODA czyszczenia HTML
        """
        if not html_content:
            return ""

        try:
            # Usuń komentarze, skrypty i style
            html_content = re.sub(r'<!--.*?-->', '', html_content, flags=re.DOTALL)
            html_content = re.sub(r'<script[^>]*>.*?</script>', '', html_content, flags=re.DOTALL | re.IGNORECASE)
            html_content = re.sub(r'<style[^>]*>.*?</style>', '', html_content, flags=re.DOTALL | re.IGNORECASE)

            # Zamień <br> na nowe linie
            html_content = re.sub(r'<(br|BR)[^>]*>', '\n', html_content)
            html_content = re.sub(r'</(p|P|div|DIV)[^>]*>', '\n\n', html_content)

            # Usuń wszystkie znaczniki HTML
            text = re.sub(r'<[^>]+>', ' ', html_content)

            # Dekoduj podstawowe encje HTML
            html_entities = {
                '&nbsp;': ' ', '&amp;': '&', '&lt;': '<', '&gt;': '>',
                '&quot;': '"', '&#39;': "'", '&apos;': "'"
            }

            for entity, replacement in html_entities.items():
                text = text.replace(entity, replacement)

            # Normalizuj białe znaki
            text = re.sub(r'\s+', ' ', text)
            text = re.sub(r'\n\s*\n+', '\n\n', text)

            return text.strip()

        except Exception as e:
            logger.debug(f"Błąd czyszczenia HTML: {e}")
            return re.sub(r'<[^>]+>', ' ', html_content).strip()

    def _generate_cache_key(self, endpoint: str, params: Optional[Dict] = None) -> str:
        """Generuje klucz cache"""
        clean_endpoint = endpoint.replace('/', '_').strip('_')
        if params:
            param_str = "&".join(f"{k}={v}" for k, v in sorted(params.items()))
            return f"api_{clean_endpoint}#{param_str}"
        return f"api_{clean_endpoint}"

    def _get_cache_ttl(self, endpoint: str, data: Any) -> int:
        """Określa TTL dla cache"""
        if '/MP' in endpoint or '/clubs' in endpoint:
            return 12 * 3600  # 12h
        elif endpoint.endswith('/term'):
            return 24 * 3600  # 24h
        elif '/transcripts/' in endpoint:  # Pojedyncze wypowiedzi
            return 24 * 3600  # 24h - stenogramy się nie zmieniają
        elif '/transcripts' in endpoint:  # Lista wypowiedzi
            return 6 * 3600  # 6h
        elif '/proceedings' in endpoint:
            return 3600  # 1h
        else:
            return 1800  # 30min

    # === PODSTAWOWE METODY API ===

    def get_terms(self) -> Optional[List[Dict]]:
        """Pobiera listę kadencji"""
        logger.debug("Pobieranie listy kadencji")
        result = self._make_request("/sejm/term")
        if result:
            logger.info(f"✓ Pobrano {len(result)} kadencji")
        return result

    def get_term_info(self, term: int) -> Optional[Dict]:
        """Pobiera informacje o kadencji"""
        logger.debug(f"Pobieranie informacji o kadencji {term}")
        return self._make_request(f"/sejm/term{term}")

    def get_proceedings(self, term: int) -> Optional[List[Dict]]:
        """Pobiera listę posiedzeń"""
        logger.info(f"Pobieranie listy posiedzeń kadencji {term}")
        result = self._make_request(f"/sejm/term{term}/proceedings")

        if result and isinstance(result, list):
            logger.info(f"✓ Pobrano {len(result)} posiedzeń")
            return result
        else:
            logger.error(f"✗ Nie udało się pobrać posiedzeń dla kadencji {term}")
            return []

    def get_proceeding_info(self, term: int, proceeding_id: int) -> Optional[Dict]:
        """Pobiera informacje o posiedzeniu"""
        logger.debug(f"Pobieranie informacji o posiedzeniu {proceeding_id}")
        return self._make_request(f"/sejm/term{term}/proceedings/{proceeding_id}")

    def get_transcripts_list(self, term: int, proceeding: int, date: str) -> Optional[Dict]:
        """Pobiera listę wypowiedzi z danego dnia"""
        endpoint = f"/sejm/term{term}/proceedings/{proceeding}/{date}/transcripts"
        logger.debug(f"Pobieranie listy wypowiedzi: {endpoint}")

        result = self._make_request(endpoint)
        if result and isinstance(result, dict) and 'statements' in result:
            statements_count = len(result.get('statements', []))
            logger.debug(f"✓ Pobrano {statements_count} wypowiedzi z {date}")
            return result
        else:
            logger.debug(f"✗ Brak wypowiedzi dla {date}")
            return None

    def get_statement_html(self, term: int, proceeding: int, date: str, statement_num: int) -> Optional[str]:
        """
        NAPRAWIONA METODA pobierania HTML wypowiedzi
        """
        endpoint = f"/sejm/term{term}/proceedings/{proceeding}/{date}/transcripts/{statement_num}"
        logger.debug(f"Pobieranie HTML wypowiedzi {statement_num}: {endpoint}")

        # Sprawdź czy to nie jest błędny numer wypowiedzi
        if statement_num is None or statement_num < 0:
            logger.debug(f"Błędny numer wypowiedzi: {statement_num}")
            return None

        try:
            html_content = self._make_request(endpoint, expected_content_type='text/html')

            if html_content and isinstance(html_content, str):
                # Dodatkowa walidacja dla stenogramów
                if len(html_content.strip()) > 100:
                    logger.debug(f"✓ Pobrano HTML wypowiedzi {statement_num}: {len(html_content)} znaków")

                    # Pokaż fragment dla debugowania
                    preview = html_content[:200].replace('\n', ' ')
                    logger.debug(f"Fragment HTML: {preview}...")

                    return html_content
                else:
                    logger.debug(f"HTML za krótki: {len(html_content)} znaków")

            return None

        except Exception as e:
            logger.debug(f"Błąd pobierania HTML wypowiedzi {statement_num}: {e}")
            return None

    def get_statement_full_text(self, term: int, proceeding: int, date: str, statement_num: int) -> Optional[str]:
        """
        NAPRAWIONA METODA pobierania czystego tekstu wypowiedzi
        """
        logger.debug(f"Pobieranie pełnego tekstu wypowiedzi {statement_num}")

        # Pobierz HTML
        html_content = self.get_statement_html(term, proceeding, date, statement_num)

        if html_content:
            try:
                # Wyczyść HTML do tekstu
                clean_text = self._clean_html_to_text(html_content)

                if clean_text and len(clean_text.strip()) > 10:
                    logger.debug(f"✓ Wyczyszczono tekst: {len(clean_text)} znaków")
                    return clean_text
                else:
                    logger.debug("Po oczyszczeniu za mało treści")

            except Exception as e:
                logger.debug(f"Błąd czyszczenia HTML: {e}")

        return None

    # === POSŁOWIE ===

    def get_mps(self, term: int) -> Optional[List[Dict]]:
        """Pobiera listę posłów"""
        logger.debug(f"Pobieranie listy posłów kadencji {term}")
        result = self._make_request(f"/sejm/term{term}/MP")
        if result:
            logger.info(f"✓ Pobrano {len(result)} posłów")
        return result

    def get_mp_info(self, term: int, mp_id: int) -> Optional[Dict]:
        """Pobiera informacje o pośle"""
        return self._make_request(f"/sejm/term{term}/MP/{mp_id}")

    def get_mp_photo(self, term: int, mp_id: int) -> Optional[bytes]:
        """Pobiera zdjęcie posła"""
        content = self._make_request(f"/sejm/term{term}/MP/{mp_id}/photo")
        if isinstance(content, bytes):
            return content
        return None

    # === KLUBY ===

    def get_clubs(self, term: int) -> Optional[List[Dict]]:
        """Pobiera listę klubów"""
        logger.debug(f"Pobieranie listy klubów kadencji {term}")
        result = self._make_request(f"/sejm/term{term}/clubs")
        if result:
            logger.info(f"✓ Pobrano {len(result)} klubów")
        return result

    def get_club_info(self, term: int, club_id: int) -> Optional[Dict]:
        """Pobiera informacje o klubie"""
        return self._make_request(f"/sejm/term{term}/clubs/{club_id}")

    # === CACHE I DIAGNOSTYKA ===

    def clear_cache(self, cache_type: str = "all") -> None:
        """Czyści cache"""
        if self.cache and hasattr(self.cache, 'clear'):
            self.cache.clear()
            logger.info(f"Wyczyszczono cache: {cache_type}")

    def get_cache_stats(self) -> Dict:
        """Zwraca statystyki cache"""
        if self.cache and hasattr(self.cache, 'get_stats'):
            return self.cache.get_stats()
        return {
            'memory_cache': {'entries': 0, 'size_mb': 0},
            'file_cache': {'entries': 0, 'size_mb': 0}
        }

    def test_connection(self) -> Dict:
        """
        ULEPSZONY test połączenia z testowaniem stenogramów
        """
        logger.info("Testowanie połączenia z API Sejmu...")

        test_results = {
            'api_available': False,
            'terms_working': False,
            'proceedings_working': False,
            'statements_working': False,
            'html_content_working': False,  # NOWY TEST
            'total_score': 0,
            'errors': []
        }

        try:
            # Test 1: Podstawowe połączenie
            response = requests.get(f"{self.base_url}/sejm/term", timeout=10)
            if response.status_code == 200:
                test_results['api_available'] = True
                test_results['total_score'] += 1
                logger.info("✓ API Sejmu dostępne")
            else:
                test_results['errors'].append(f"API niedostępne: {response.status_code}")
        except Exception as e:
            test_results['errors'].append(f"Błąd połączenia: {e}")

        try:
            # Test 2: Lista kadencji
            terms = self.get_terms()
            if terms and len(terms) > 0:
                test_results['terms_working'] = True
                test_results['total_score'] += 1
                logger.info(f"✓ Lista kadencji działa ({len(terms)} kadencji)")
            else:
                test_results['errors'].append("Nie można pobrać listy kadencji")
        except Exception as e:
            test_results['errors'].append(f"Błąd pobierania kadencji: {e}")

        try:
            # Test 3: Lista posiedzeń
            proceedings = self.get_proceedings(10)
            if proceedings and len(proceedings) > 0:
                test_results['proceedings_working'] = True
                test_results['total_score'] += 1
                logger.info(f"✓ Lista posiedzeń działa ({len(proceedings)} posiedzeń)")

                # Test 4: NOWY - Test stenogramów
                # Znajdź posiedzenie z przeszłości do testowania
                test_proceeding = None
                test_date = None

                from datetime import datetime, date
                today = date.today()

                for proc in proceedings:
                    if proc.get('dates'):
                        for proc_date in proc['dates']:
                            try:
                                if datetime.strptime(proc_date, '%Y-%m-%d').date() < today:
                                    test_proceeding = proc
                                    test_date = proc_date
                                    break
                            except:
                                continue
                        if test_proceeding:
                            break

                if test_proceeding and test_date:
                    proc_id = test_proceeding.get('number')

                    # Normalizuj i sprawdź proc_id zanim przekażemy je dalej
                    try:
                        if proc_id is None:
                            raise ValueError("proc_id is None")
                        if not isinstance(proc_id, int):
                            proc_id = int(proc_id)
                    except Exception as e:
                        logger.warning(f"Nieprawidłowy identyfikator posiedzenia: {proc_id} ({e})")
                        test_results['errors'].append("Nieprawidłowy identyfikator posiedzenia do testów")
                    else:
                        logger.info(f"Testowanie stenogramów z posiedzenia {proc_id}, dnia {test_date}")

                        # Test listy wypowiedzi
                        statements = self.get_transcripts_list(10, proc_id, test_date)
                        if statements and statements.get('statements'):
                            test_results['statements_working'] = True
                            test_results['total_score'] += 1
                            logger.info(f"✓ Lista wypowiedzi działa ({len(statements['statements'])} wypowiedzi)")

                            # Test 5: NAJWAŻNIEJSZY - Test pobierania treści HTML
                            first_statements = statements['statements'][:3]  # Test pierwszych 3
                            successful_html = 0

                            for stmt in first_statements:
                                stmt_num = stmt.get('num')
                                if stmt_num is not None:
                                    # Normalizuj numer wypowiedzi
                                    try:
                                        if not isinstance(stmt_num, int):
                                            stmt_num = int(stmt_num)
                                    except Exception:
                                        continue

                                    html_content = self.get_statement_html(10, proc_id, test_date, stmt_num)
                                    if html_content and len(html_content.strip()) > 50:
                                        successful_html += 1

                            if successful_html > 0:
                                test_results['html_content_working'] = True
                                test_results['total_score'] += 1
                                logger.info(
                                    f"✓ Pobieranie treści HTML działa ({successful_html}/{len(first_statements)} testów)")
                            else:
                                test_results['errors'].append("Nie można pobrać treści HTML wypowiedzi")
                                logger.error("✗ Pobieranie treści HTML nie działa")
                        else:
                            test_results['errors'].append("Brak wypowiedzi w stenogramie")
                else:
                    test_results['errors'].append("Brak posiedzeń z przeszłości do testowania")
            else:
                test_results['errors'].append("Nie można pobrać listy posiedzeń")
        except Exception as e:
            test_results['errors'].append(f"Błąd testowania posiedzeń/stenogramów: {e}")

        # Podsumowanie
        max_score = 5  # Zwiększyłem liczbę testów
        logger.info(f"Test zakończony: {test_results['total_score']}/{max_score} testów przeszło")

        if test_results['errors']:
            logger.warning("Problemy wykryte podczas testów:")
            for error in test_results['errors']:
                logger.warning(f"  - {error}")

        return test_results
