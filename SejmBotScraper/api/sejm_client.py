"""
Implementacja klienta API Sejmu RP - NAPRAWIONA WERSJA
Rozwiązuje problem z pustą listą posiedzeń
"""

import logging
import time
from typing import List, Dict, Optional, Any

import requests

logger = logging.getLogger(__name__)


class SejmAPIClient:
    """NAPRAWIONA implementacja klienta API Sejmu RP"""

    def __init__(self, cache_manager=None, config=None):
        """
        Inicjalizuje klient API

        Args:
            cache_manager: manager cache (opcjonalny)
            config: konfiguracja API (opcjonalna)
        """
        # Konfiguracja domyślna
        self.config = config or {}
        self.base_url = self.config.get('base_url', 'https://api.sejm.gov.pl')
        self.request_timeout = self.config.get('timeout', 30)
        self.request_delay = self.config.get('delay', 0.5)  # Zmniejszone opóźnienie
        self.user_agent = self.config.get('user_agent', 'SejmBotScraper/3.0')

        # Sesja HTTP z lepszymi headerami
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': self.user_agent,
            'Accept': 'application/json, */*',
            'Accept-Language': 'pl,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate',
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive'
        })

        # Cache manager
        self.cache = cache_manager

        logger.info(f"Zainicjalizowano SejmAPIClient")
        logger.debug(f"Base URL: {self.base_url}")
        logger.debug(f"Cache: {'włączony' if cache_manager else 'wyłączony'}")

    def _make_request(self, endpoint: str, params: Optional[Dict] = None,
                      use_cache: bool = True, retry_count: int = 3) -> Optional[Any]:
        """
        NAPRAWIONA metoda wykonująca zapytanie do API z retry logic
        """
        url = f"{self.base_url}{endpoint}"

        # Cache key
        cache_key = self._generate_cache_key(endpoint, params)

        # Sprawdź cache jeśli dostępny
        if use_cache and self.cache:
            cached_data = self.cache.get(cache_key)
            if cached_data is not None:
                logger.debug(f"Cache hit: {endpoint}")
                return cached_data

        # Retry logic
        for attempt in range(retry_count):
            try:
                if attempt > 0:
                    logger.debug(f"Próba {attempt + 1}/{retry_count} dla {endpoint}")

                logger.debug(f"Zapytanie API: {url}")
                if params:
                    logger.debug(f"Parametry: {params}")

                time.sleep(self.request_delay)  # Rate limiting

                response = self.session.get(url, params=params, timeout=self.request_timeout)

                logger.debug(f"Response: {response.status_code} {response.headers.get('content-type', 'unknown')}")
                logger.debug(f"Content-Length: {response.headers.get('content-length', 'unknown')}")

                # Obsługa kodów błędów z retry dla 5xx
                if response.status_code == 403:
                    logger.debug(f"403 Forbidden - endpoint może nie istnieć: {url}")
                    return None
                elif response.status_code == 404:
                    logger.debug(f"404 Not Found - zasób nie istnieje: {url}")
                    return None
                elif response.status_code == 429:
                    logger.warning(f"429 Too Many Requests: {url}")
                    time.sleep(5)
                    if attempt < retry_count - 1:
                        continue
                    return None
                elif response.status_code >= 500:
                    logger.warning(f"5xx Server Error {response.status_code}: {url}")
                    if attempt < retry_count - 1:
                        time.sleep(2 ** attempt)  # Exponential backoff
                        continue
                    return None

                response.raise_for_status()
                response.encoding = 'utf-8'

                # Sprawdź czy odpowiedź nie jest pusta
                if not response.content:
                    logger.warning(f"Pusta odpowiedź z {url}")
                    return None

                # Sprawdź typ zawartości
                content_type = response.headers.get('content-type', '').lower()

                if 'application/json' in content_type or 'text/json' in content_type:
                    try:
                        json_data = response.json()

                        # Szczegółowe logowanie
                        if isinstance(json_data, list):
                            logger.debug(f"Otrzymano listę: {len(json_data)} elementów")
                            if len(json_data) > 0:
                                first_item = json_data[0]
                                if isinstance(first_item, dict):
                                    logger.debug(f"Pierwszy element - klucze: {list(first_item.keys())[:5]}")
                        elif isinstance(json_data, dict):
                            logger.debug(f"Otrzymano dict z kluczami: {list(json_data.keys())[:10]}")
                        else:
                            logger.debug(f"Otrzymano dane typu: {type(json_data)}")

                        # API Sejmu zwraca {"supportID": "..."} dla nieobsługiwanych endpointów
                        if isinstance(json_data, dict) and 'supportID' in json_data and len(json_data) == 1:
                            logger.debug(f"API zwróciło tylko supportID - endpoint nieobsługiwany")
                            return None

                        # Zapisz do cache jeśli dostępny i dane są poprawne
                        if use_cache and self.cache and json_data is not None:
                            ttl = self._get_cache_ttl(endpoint, json_data)
                            self.cache.set(cache_key, json_data, ttl)
                            logger.debug(f"Zapisano do cache: {cache_key} (ttl={ttl}s)")

                        return json_data

                    except ValueError as e:
                        logger.error(f"Błąd parsowania JSON z {url}: {e}")
                        logger.debug(f"Raw response (first 1000 chars): {response.text[:1000]}")
                        if attempt < retry_count - 1:
                            continue
                        return None

                elif 'text/html' in content_type:
                    if '/transcripts/' in endpoint:
                        logger.debug(f"Otrzymano HTML (oczekiwane) z {url}")
                    else:
                        logger.warning(f"Otrzymano HTML zamiast JSON z {url}")
                    if attempt < retry_count - 1:
                        continue
                    return None
                else:
                    # Zwróć surową zawartość dla plików binarnych
                    content = response.content
                    if use_cache and self.cache:
                        self.cache.set(cache_key, content, 3600)  # 1h dla binaries
                    return content

            except requests.exceptions.Timeout as e:
                logger.warning(f"Timeout dla {url}: {e}")
                if attempt < retry_count - 1:
                    time.sleep(2)
                    continue
                return None

            except requests.exceptions.ConnectionError as e:
                logger.warning(f"Connection error dla {url}: {e}")
                if attempt < retry_count - 1:
                    time.sleep(2)
                    continue
                return None

            except requests.exceptions.RequestException as e:
                logger.error(f"Request error dla {url}: {e}")
                if attempt < retry_count - 1:
                    continue
                return None

        logger.error(f"Wszystkie próby nieudane dla {url}")
        return None

    def _generate_cache_key(self, endpoint: str, params: Optional[Dict] = None) -> str:
        """Generuje stabilny klucz cache"""
        clean_endpoint = endpoint.replace('/', '_').strip('_')
        if params:
            param_str = "&".join(f"{k}={v}" for k, v in sorted(params.items()))
            return f"api_{clean_endpoint}#{param_str}"
        return f"api_{clean_endpoint}"

    def _get_cache_ttl(self, endpoint: str, data: Any) -> int:
        """Określa TTL dla cache na podstawie typu danych"""
        # Posłowie i kluby - rzadko się zmieniają
        if '/MP' in endpoint or '/clubs' in endpoint:
            return 12 * 3600  # 12h

        # Lista kadencji - bardzo rzadko się zmienia
        if endpoint.endswith('/term'):
            return 24 * 3600  # 24h

        # Info o kadencji - rzadko się zmienia
        if '/term' in endpoint and '/proceedings' not in endpoint:
            return 12 * 3600  # 12h

        # Posiedzenia - mogą się aktualizować
        if '/proceedings' in endpoint and len(endpoint.split('/')) <= 4:  # Lista posiedzeń
            return 1800  # 30 min

        # Szczegóły posiedzenia
        if '/proceedings/' in endpoint and len(endpoint.split('/')) > 4:
            return 3600  # 1h

        # Stenogramy - rzadko się zmieniają po opublikowaniu
        if '/transcripts' in endpoint:
            return 6 * 3600  # 6h

        # Domyślnie
        return 1800  # 30 min

    # === IMPLEMENTACJA ENDPOINTÓW ===

    def get_terms(self) -> Optional[List[Dict]]:
        """Pobiera listę kadencji"""
        logger.info("Pobieranie listy kadencji")
        result = self._make_request("/sejm/term")
        if result:
            logger.info(f"✓ Pobrano {len(result)} kadencji")
        else:
            logger.error("✗ Nie udało się pobrać listy kadencji")
        return result

    def get_term_info(self, term: int) -> Optional[Dict]:
        """Pobiera informacje o konkretnej kadencji"""
        logger.debug(f"Pobieranie informacji o kadencji {term}")
        result = self._make_request(f"/sejm/term{term}")
        if result:
            logger.debug(f"✓ Pobrano info kadencji {term}")
        return result

    def get_proceedings(self, term: int) -> Optional[List[Dict]]:
        """
        Pobiera listę posiedzeń - NAPRAWIONA WERSJA z wieloma strategiami
        """
        logger.info(f"Pobieranie listy posiedzeń kadencji {term}")

        # Lista endpointów do wypróbowania w kolejności priorytetów
        endpoints_to_try = [
            f"/sejm/term{term}/proceedings",
            f"/sejm/term{term}/proceedings/",
        ]

        for i, endpoint in enumerate(endpoints_to_try):
            logger.debug(f"Strategia {i + 1}: próbuję endpoint {endpoint}")

            result = self._make_request(endpoint, use_cache=False)  # Wyłącz cache dla debugowania

            if result is not None and isinstance(result, list):
                logger.info(f"✓ SUKCES! Strategia {i + 1} zadziałała - znaleziono {len(result)} posiedzeń")

                if len(result) > 0:
                    first_proc = result[0]
                    if isinstance(first_proc, dict):
                        logger.debug(f"Przykład pierwszego posiedzenia:")
                        logger.debug(f"  Klucze: {list(first_proc.keys())}")
                        logger.debug(f"  Numer: {first_proc.get('number', 'brak')}")
                        logger.debug(f"  Tytuł: {first_proc.get('title', 'brak')[:100]}")
                        logger.debug(f"  Daty: {first_proc.get('dates', 'brak')}")

                # Teraz zapisz do cache
                if self.cache:
                    cache_key = self._generate_cache_key(endpoint)
                    ttl = self._get_cache_ttl(endpoint, result)
                    self.cache.set(cache_key, result, ttl)
                    logger.debug(f"Zapisano do cache: {len(result)} posiedzeń")

                return result
            else:
                logger.debug(f"Strategia {i + 1} nieudana - otrzymano: {type(result)}")

        # Jeśli standardowe endpointy nie działają, spróbuj alternatywne metody
        logger.warning("Standardowe endpointy nie działają, próbuję metody awaryjne...")

        # Metoda awaryjna - czasami API wymaga konkretnych headerów
        original_headers = self.session.headers.copy()
        try:
            # Zmień headery na bardziej "browserowe"
            self.session.headers.update({
                'Accept': 'application/json, text/plain, */*',
                'Accept-Language': 'pl-PL,pl;q=0.9,en;q=0.8',
                'Referer': f'{self.base_url}/sejm/term{term}',
                'X-Requested-With': 'XMLHttpRequest'
            })

            result = self._make_request(f"/sejm/term{term}/proceedings", use_cache=False, retry_count=5)

            if result and isinstance(result, list):
                logger.info(f"✓ Metoda awaryjna zadziałała! Znaleziono {len(result)} posiedzeń")
                return result

        except Exception as e:
            logger.debug(f"Metoda awaryjna nie zadziałała: {e}")
        finally:
            # Przywróć oryginalne headery
            self.session.headers = original_headers

        # Ostatnia metoda - spróbuj bez cache i z minimalnym delay
        logger.warning("Ostatnia próba - bez cache i z minimalnym opóźnieniem...")
        original_delay = self.request_delay
        try:
            self.request_delay = 0.1
            result = self._make_request(f"/sejm/term{term}/proceedings", use_cache=False, retry_count=1)

            if result and isinstance(result, list):
                logger.info(f"✓ Ostatnia próba zadziałała! Znaleziono {len(result)} posiedzeń")
                return result
        finally:
            self.request_delay = original_delay

        logger.error(f"✗ BŁĄD: Nie udało się pobrać posiedzeń dla kadencji {term} żadną metodą")
        logger.error("Sprawdź:")
        logger.error("1. Połączenie internetowe")
        logger.error("2. Dostępność API Sejmu")
        logger.error("3. Poprawność numeru kadencji")

        return []  # Zwróć pustą listę zamiast None

    def get_proceeding_info(self, term: int, proceeding_id: int) -> Optional[Dict]:
        """Pobiera szczegółowe informacje o posiedzeniu"""
        logger.debug(f"Pobieranie informacji o posiedzeniu {proceeding_id} kadencji {term}")
        result = self._make_request(f"/sejm/term{term}/proceedings/{proceeding_id}")
        if result:
            logger.debug(f"✓ Pobrano info posiedzenia {proceeding_id}")
        return result

    # === STENOGRAMY ===

    def get_transcripts_list(self, term: int, proceeding: int, date: str) -> Optional[Dict]:
        """Pobiera listę wypowiedzi z danego dnia"""
        endpoint = f"/sejm/term{term}/proceedings/{proceeding}/{date}/transcripts"
        logger.debug(f"Pobieranie listy wypowiedzi: {endpoint}")
        result = self._make_request(endpoint)
        if result and isinstance(result, dict) and 'statements' in result:
            statements_count = len(result.get('statements', []))
            logger.debug(f"✓ Pobrano {statements_count} wypowiedzi z {date}")
        return result

    def get_statement_html(self, term: int, proceeding: int, date: str, statement_num: int) -> Optional[str]:
        """Pobiera HTML konkretnej wypowiedzi"""
        endpoint = f"/sejm/term{term}/proceedings/{proceeding}/{date}/transcripts/{statement_num}"
        logger.debug(f"Pobieranie HTML wypowiedzi {statement_num}")

        # Użyj _make_request, ale nie loguj ostrzeżeń o HTML
        content = self._make_request(endpoint)

        if content is not None:
            if isinstance(content, bytes):
                return content.decode('utf-8', errors='replace')
            elif isinstance(content, str):
                return content
            # Jeśli to dict/json, znaczy, że endpoint zwrócił JSON zamiast HTML
            return str(content)
        return None

    def get_statement_full_text(self, term: int, proceeding: int, date: str, statement_num: int) -> Optional[str]:
        """Pobiera pełną treść wypowiedzi"""
        # Najpierw spróbuj dedykowany endpoint tekstowy
        text_endpoint = f"/sejm/term{term}/proceedings/{proceeding}/{date}/transcripts/{statement_num}/text"

        try:
            text_content = self._make_request(text_endpoint)

            if text_content:
                if isinstance(text_content, bytes):
                    return text_content.decode('utf-8', errors='replace')
                elif isinstance(text_content, dict) and 'text' in text_content:
                    return text_content['text']
                elif isinstance(text_content, str):
                    return text_content
        except Exception as e:
            logger.debug(f"Dedykowany endpoint tekstowy nie działa: {e}")

        # Fallback - pobierz HTML i wyciągnij tekst
        try:
            html_content = self.get_statement_html(term, proceeding, date, statement_num)
            if html_content:
                import re
                text = re.sub(r'<[^>]+>', '', html_content)
                text = re.sub(r'\s+', ' ', text).strip()
                return text if text else None
        except Exception as e:
            logger.debug(f"Błąd fallback dla wypowiedzi {statement_num}: {e}")

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
        """Pobiera szczegółowe informacje o pośle"""
        return self._make_request(f"/sejm/term{term}/MP/{mp_id}")

    def get_mp_photo(self, term: int, mp_id: int) -> Optional[bytes]:
        """Pobiera zdjęcie posła"""
        content = self._make_request(f"/sejm/term{term}/MP/{mp_id}/photo")
        if isinstance(content, bytes):
            return content
        return None

    def get_mp_voting_stats(self, term: int, mp_id: int) -> Optional[Dict]:
        """Pobiera statystyki głosowań posła"""
        return self._make_request(f"/sejm/term{term}/MP/{mp_id}/votings/stats")

    # === KLUBY ===

    def get_clubs(self, term: int) -> Optional[List[Dict]]:
        """Pobiera listę klubów parlamentarnych"""
        logger.debug(f"Pobieranie listy klubów kadencji {term}")
        result = self._make_request(f"/sejm/term{term}/clubs")
        if result:
            logger.info(f"✓ Pobrano {len(result)} klubów")
        return result

    def get_club_info(self, term: int, club_id: int) -> Optional[Dict]:
        """Pobiera szczegółowe informacje o klubie"""
        return self._make_request(f"/sejm/term{term}/clubs/{club_id}")

    def get_club_logo(self, term: int, club_id: int) -> Optional[bytes]:
        """Pobiera logo klubu"""
        content = self._make_request(f"/sejm/term{term}/clubs/{club_id}/logo")
        if isinstance(content, bytes):
            return content
        return None

    # === ZARZĄDZANIE CACHE ===

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

    # === DIAGNOSTYKA ===

    def test_connection(self) -> Dict:
        """Testuje połączenie z API"""
        logger.info("Testowanie połączenia z API Sejmu...")

        test_results = {
            'api_available': False,
            'terms_working': False,
            'proceedings_working': False,
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
                logger.error(f"✗ API niedostępne: {response.status_code}")
        except Exception as e:
            test_results['errors'].append(f"Błąd połączenia: {e}")
            logger.error(f"✗ Błąd połączenia: {e}")

        try:
            # Test 2: Lista kadencji
            terms = self.get_terms()
            if terms and len(terms) > 0:
                test_results['terms_working'] = True
                test_results['total_score'] += 1
                logger.info(f"✓ Lista kadencji działa ({len(terms)} kadencji)")
            else:
                test_results['errors'].append("Nie można pobrać listy kadencji")
                logger.error("✗ Nie można pobrać listy kadencji")
        except Exception as e:
            test_results['errors'].append(f"Błąd pobierania kadencji: {e}")
            logger.error(f"✗ Błąd pobierania kadencji: {e}")

        try:
            # Test 3: Lista posiedzeń dla kadencji 10
            proceedings = self.get_proceedings(10)
            if proceedings and len(proceedings) > 0:
                test_results['proceedings_working'] = True
                test_results['total_score'] += 1
                logger.info(f"✓ Lista posiedzeń działa ({len(proceedings)} posiedzeń)")
            else:
                test_results['errors'].append("Nie można pobrać listy posiedzeń")
                logger.error("✗ Nie można pobrać listy posiedzeń")
        except Exception as e:
            test_results['errors'].append(f"Błąd pobierania posiedzeń: {e}")
            logger.error(f"✗ Błąd pobierania posiedzeń: {e}")

        # Podsumowanie
        max_score = 3
        logger.info(f"Test zakończony: {test_results['total_score']}/{max_score} testów przeszło")

        return test_results
