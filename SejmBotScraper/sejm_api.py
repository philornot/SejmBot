# sejm_api.py
"""
Klasa do komunikacji z API Sejmu RP
Z zaawansowaną obsługą cache dla optymalizacji wydajności
"""

import logging
import time
from typing import List, Dict, Optional, Any

import requests

from cache_manager import CacheManager
from config import API_BASE_URL, REQUEST_TIMEOUT, REQUEST_DELAY, USER_AGENT

logger = logging.getLogger(__name__)


class SejmAPI:
    """Klasa do komunikacji z API Sejmu RP z obsługą cache"""

    def __init__(self):
        self.base_url = API_BASE_URL
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': USER_AGENT,
            'Accept-Charset': 'utf-8'
        })

        # Dodaj cache manager
        self.cache = CacheManager()

    def _make_request(self, endpoint: str) -> Optional[Any]:
        """
        Wykonuje zapytanie do API z obsługą błędów i poprawnym kodowaniem

        Args:
            endpoint: Endpoint API (bez base URL)

        Returns:
            Odpowiedź JSON lub None w przypadku błędu
        """
        url = f"{self.base_url}{endpoint}"

        try:
            logger.debug(f"Zapytanie do: {url}")
            time.sleep(REQUEST_DELAY)  # Łagodne rate limiting

            response = self.session.get(url, timeout=REQUEST_TIMEOUT)

            # Sprawdź konkretne kody błędów
            if response.status_code == 403:
                logger.debug(f"403 Forbidden dla {url} - endpoint może nie istnieć")
                return None
            elif response.status_code == 404:
                logger.debug(f"404 Not Found dla {url} - zasób nie istnieje")
                return None
            elif response.status_code == 429:
                logger.warning(f"429 Too Many Requests dla {url}")
                time.sleep(5)
                return None

            response.raise_for_status()

            # Upewniamy się o poprawnym kodowaniu
            response.encoding = 'utf-8'

            # Sprawdź, czy to JSON
            content_type = response.headers.get('content-type', '')
            if 'application/json' in content_type:
                try:
                    json_data = response.json()
                    # API Sejmu zwraca {"supportID": "..."} dla nieobsługiwanych endpointów
                    if isinstance(json_data, dict) and 'supportID' in json_data and len(json_data) == 1:
                        logger.debug(f"API zwróciło tylko supportID dla {url} - nieobsługiwany endpoint")
                        return None
                    return json_data
                except ValueError as e:
                    logger.error(f"Błąd parsowania JSON z {url}: {e}")
                    return None
            else:
                return response.content

        except requests.exceptions.RequestException as e:
            logger.error(f"Błąd zapytania do {url}: {e}")
            return None

    # =============================================================================
    # KADENCJE I POSIEDZENIA
    # =============================================================================

    def get_terms(self) -> Optional[List[Dict]]:
        """Pobiera listę kadencji Sejmu z cache'em"""
        endpoint = "/sejm/term"

        # Cache na 24 godziny dla listy kadencji (rzadko się zmienia)
        if self.cache.has_api_cache(endpoint, max_age_hours=24):
            cached_data = self.cache.get_api_cache(endpoint)
            if cached_data:
                logger.debug("Użyto cache dla listy kadencji")
                return cached_data

        # Pobierz z API
        result = self._make_request(endpoint)
        if result:
            self.cache.set_api_cache(endpoint, result, ttl_hours=24)

        return result

    def get_term_info(self, term: int) -> Optional[Dict]:
        """Pobiera informacje o konkretnej kadencji z cache'em"""
        endpoint = f"/sejm/term{term}"

        # Cache na 24 godziny dla informacji o kadencji
        if self.cache.has_api_cache(endpoint, max_age_hours=24):
            cached_data = self.cache.get_api_cache(endpoint)
            if cached_data:
                logger.debug(f"Użyto cache dla informacji o kadencji {term}")
                return cached_data

        # Pobierz z API
        result = self._make_request(endpoint)
        if result:
            self.cache.set_api_cache(endpoint, result, ttl_hours=24)

        return result

    def get_proceedings(self, term: int) -> Optional[List[Dict]]:
        """Pobiera listę posiedzeń z cache'em"""
        endpoint = f"/sejm/term{term}/proceedings"

        # Sprawdź cache (posiedzenia - cache na 6 godzin)
        if self.cache.has_api_cache(endpoint, max_age_hours=6):
            cached_data = self.cache.get_api_cache(endpoint)
            if cached_data:
                logger.debug(f"Użyto cache dla listy posiedzeń kadencji {term}")
                return cached_data

        # Pobierz z API
        try:
            result = self._make_request(endpoint)

            # Zapisz do cache
            if result:
                self.cache.set_api_cache(endpoint, result, ttl_hours=6)
                logger.debug(f"Zapisano do cache listę {len(result)} posiedzeń")

            return result

        except Exception as e:
            logger.error(f"Błąd pobierania posiedzeń: {e}")
            return None

    def get_proceeding_info(self, term: int, proceeding_id: int) -> Optional[Dict]:
        """Pobiera szczegółowe informacje o posiedzeniu z cache'em"""
        endpoint = f"/sejm/term{term}/proceedings/{proceeding_id}"

        # Cache na 24 godziny dla szczegółów posiedzenia
        if self.cache.has_api_cache(endpoint, max_age_hours=24):
            cached_data = self.cache.get_api_cache(endpoint)
            if cached_data:
                logger.debug(f"Użyto cache dla szczegółów posiedzenia {proceeding_id}")
                return cached_data

        # Pobierz z API
        try:
            result = self._make_request(endpoint)

            if result:
                self.cache.set_api_cache(endpoint, result, ttl_hours=24)

            return result

        except Exception as e:
            logger.error(f"Błąd pobierania informacji o posiedzeniu {proceeding_id}: {e}")
            return None

    # =============================================================================
    # STENOGRAMY I WYPOWIEDZI
    # =============================================================================

    def get_transcripts_list(self, term: int, proceeding_id: int, date: str) -> Optional[Dict]:
        """
        Pobiera listę wypowiedzi z danego dnia posiedzenia z cache'em

        Args:
            term: numer kadencji
            proceeding_id: ID posiedzenia
            date: data w formacie YYYY-MM-DD

        Returns:
            Słownik z listą wypowiedzi zawierający metadane o mówcach
        """
        endpoint = f"/sejm/term{term}/proceedings/{proceeding_id}/{date}/transcripts"
        params = {"term": term, "proceeding": proceeding_id, "date": date}

        # Cache na 1 godzinę dla list wypowiedzi
        if self.cache.has_api_cache(endpoint, params, max_age_hours=1):
            cached_data = self.cache.get_api_cache(endpoint, params)
            if cached_data:
                logger.debug(f"Użyto cache dla listy wypowiedzi {proceeding_id}/{date}")
                return cached_data

        # Pobieramy standardowym endpointem (BEZ format=extended)
        try:
            result = self._make_request(endpoint)

            if result:
                self.cache.set_api_cache(endpoint, result, params, ttl_hours=1)

                # Log success with proper count handling
                if isinstance(result, list):
                    logger.debug(f"Pobrano {len(result)} wypowiedzi dla {date}")
                elif isinstance(result, dict) and 'transcripts' in result:
                    transcript_count = len(result['transcripts'])
                    logger.debug(f"Pobrano {transcript_count} wypowiedzi dla {date}")
                else:
                    logger.debug(f"Pobrano dane wypowiedzi dla {date}")
            else:
                logger.warning(f"Brak danych wypowiedzi dla {date}")

            return result

        except Exception as e:
            logger.error(f"Błąd pobierania wypowiedzi dla {date}: {e}")
            return None

    def get_statement_html(self, term: int, proceeding_id: int, date: str, statement_num: int) -> Optional[str]:
        """
        Pobiera konkretną wypowiedź w formacie HTML z cache'em

        Args:
            term: numer kadencji
            proceeding_id: ID posiedzenia
            date: data w formacie YYYY-MM-DD
            statement_num: numer wypowiedzi

        Returns:
            HTML jako string lub None
        """
        endpoint = f"/sejm/term{term}/proceedings/{proceeding_id}/{date}/transcripts/{statement_num}"
        params = {"term": term, "proceeding": proceeding_id, "date": date, "statement": statement_num}

        # Cache na 24 godziny dla konkretnych wypowiedzi (rzadko się zmieniają)
        if self.cache.has_api_cache(endpoint, params, max_age_hours=24):
            cached_data = self.cache.get_api_cache(endpoint, params)
            if cached_data:
                logger.debug(f"Użyto cache dla wypowiedzi {statement_num} z {date}")
                return cached_data

        try:
            content = self._make_request(endpoint)

            if content is not None:
                if isinstance(content, bytes):
                    html_content = content.decode('utf-8', errors='replace')
                else:
                    html_content = content

                # Zapisz do cache
                self.cache.set_api_cache(endpoint, html_content, params, ttl_hours=24)
                logger.debug(f"Pobrano HTML dla wypowiedzi {statement_num} z {date}")
                return html_content
            else:
                logger.warning(f"Brak HTML dla wypowiedzi {statement_num} z {date}")
                return None

        except Exception as e:
            logger.error(f"Błąd pobierania HTML wypowiedzi {statement_num} z {date}: {e}")
            return None

    def get_statement_full_text(self, term: int, proceeding_id: int, date: str, statement_num: int) -> Optional[str]:
        """
        Pobiera pełną treść konkretnej wypowiedzi w formacie tekstowym z cache'em

        Args:
            term: numer kadencji
            proceeding_id: ID posiedzenia
            date: data w formacie YYYY-MM-DD
            statement_num: numer wypowiedzi

        Returns:
            Pełna treść wypowiedzi jako string lub None
        """
        text_endpoint = f"/sejm/term{term}/proceedings/{proceeding_id}/{date}/transcripts/{statement_num}/text"
        params = {"term": term, "proceeding": proceeding_id, "date": date, "statement": statement_num}

        # Cache na 24 godziny dla treści wypowiedzi
        if self.cache.has_api_cache(text_endpoint, params, max_age_hours=24):
            cached_data = self.cache.get_api_cache(text_endpoint, params)
            if cached_data:
                logger.debug(f"Użyto cache dla treści wypowiedzi {statement_num} z {date}")
                return cached_data

        # Próbujemy najpierw dedykowany endpoint tekstowy
        try:
            text_content = self._make_request(text_endpoint)

            if text_content:
                final_text = None
                if isinstance(text_content, bytes):
                    final_text = text_content.decode('utf-8', errors='replace')
                elif isinstance(text_content, dict) and 'text' in text_content:
                    final_text = text_content['text']
                elif isinstance(text_content, str):
                    final_text = text_content

                if final_text:
                    self.cache.set_api_cache(text_endpoint, final_text, params, ttl_hours=24)
                    logger.debug(f"Pobrano tekst dla wypowiedzi {statement_num} z {date}")
                    return final_text

        except Exception as e:
            logger.debug(f"Dedykowany endpoint tekstowy nie działa dla {statement_num}: {e}")

        # Fallback - pobieramy HTML i wyciągamy tekst
        try:
            html_content = self.get_statement_html(term, proceeding_id, date, statement_num)
            if html_content:
                # Podstawowe usunięcie tagów HTML
                import re
                text = re.sub(r'<[^>]+>', '', html_content)
                text = re.sub(r'\s+', ' ', text).strip()

                if text:
                    # Zapisz wynik do cache pod kluczem tekstowym
                    self.cache.set_api_cache(text_endpoint, text, params, ttl_hours=24)
                    logger.debug(f"Wyciągnięto tekst z HTML dla wypowiedzi {statement_num} z {date}")
                    return text

        except Exception as e:
            logger.error(f"Błąd fallback dla wypowiedzi {statement_num} z {date}: {e}")

        return None

    def get_speaker_info(self, term: int, speaker_id: Optional[int] = None, speaker_name: Optional[str] = None) -> \
            Optional[Dict]:
        """
        Pobiera informacje o mówcy na podstawie ID lub nazwy

        Args:
            term: numer kadencji
            speaker_id: ID mówcy (opcjonalne)
            speaker_name: nazwa/imię i nazwisko mówcy (opcjonalne)

        Returns:
            Informacje o mówcy lub None
        """
        if speaker_id is not None:
            # Próbujemy endpoint z ID mówcy
            result = self._make_request(f"/sejm/term{term}/speakers/{speaker_id}")
            if result:
                return result

        if speaker_name is not None:
            # Próbujemy wyszukać po nazwie
            encoded_name = requests.utils.quote(speaker_name.encode('utf-8'), safe='')
            result = self._make_request(f"/sejm/term{term}/speakers?name={encoded_name}")
            if result:
                return result

        # Jeśli dedykowane endpointy nie istnieją, sprawdzamy w liście posłów
        if speaker_name is not None:
            mps = self.get_mps(term)
            if mps:
                for mp in mps:
                    mp_full_name = f"{mp.get('firstName', '')} {mp.get('lastName', '')}".strip()
                    if speaker_name.lower() in mp_full_name.lower() or mp_full_name.lower() in speaker_name.lower():
                        return self.get_mp_info(term, mp['id'])

        return None

    # =============================================================================
    # POSŁOWIE
    # =============================================================================

    def get_mps(self, term: int) -> Optional[List[Dict]]:
        """
        Pobiera listę wszystkich posłów dla danej kadencji z cache'em

        Args:
            term: numer kadencji

        Returns:
            Lista posłów z podstawowymi danymi lub None
        """
        endpoint = f"/sejm/term{term}/MP"

        # Cache na 7 dni dla listy posłów (rzadko się zmienia)
        if self.cache.has_api_cache(endpoint, max_age_hours=168):
            cached_data = self.cache.get_api_cache(endpoint)
            if cached_data:
                logger.debug(f"Użyto cache dla listy posłów kadencji {term}")
                return cached_data

        # Pobierz z API
        try:
            result = self._make_request(endpoint)

            if result:
                self.cache.set_api_cache(endpoint, result, ttl_hours=168)

            return result

        except Exception as e:
            logger.error(f"Błąd pobierania listy posłów: {e}")
            return None

    def get_mp_info(self, term: int, mp_id: int) -> Optional[Dict]:
        """
        Pobiera szczegółowe informacje o pośle

        Args:
            term: numer kadencji
            mp_id: ID posła

        Returns:
            Szczegółowe dane posła lub None
        """
        return self._make_request(f"/sejm/term{term}/MP/{mp_id}")

    def get_mp_photo(self, term: int, mp_id: int) -> Optional[bytes]:
        """
        Pobiera zdjęcie posła

        Args:
            term: numer kadencji
            mp_id: ID posła

        Returns:
            Zdjęcie jako bytes (JPEG/PNG) lub None
        """
        return self._make_request(f"/sejm/term{term}/MP/{mp_id}/photo")

    def get_mp_voting_stats(self, term: int, mp_id: int) -> Optional[Dict]:
        """
        Pobiera statystyki głosowań posła

        Args:
            term: numer kadencji
            mp_id: ID posła

        Returns:
            Statystyki głosowań lub None
        """
        return self._make_request(f"/sejm/term{term}/MP/{mp_id}/votings/stats")

    def get_mp_votings_by_date(self, term: int, mp_id: int, sitting: int, date: str) -> Optional[Dict]:
        """
        Pobiera głosowania posła z konkretnego posiedzenia

        Args:
            term: numer kadencji
            mp_id: ID posła
            sitting: numer posiedzenia
            date: data w formacie YYYY-MM-DD

        Returns:
            Lista głosowań z danego dnia lub None
        """
        return self._make_request(f"/sejm/term{term}/MP/{mp_id}/votings/{sitting}/{date}")

    # =============================================================================
    # KLUBY PARLAMENTARNE
    # =============================================================================

    def get_clubs(self, term: int) -> Optional[List[Dict]]:
        """
        Pobiera listę klubów parlamentarnych

        Args:
            term: numer kadencji

        Returns:
            Lista klubów z podstawowymi danymi lub None
        """
        return self._make_request(f"/sejm/term{term}/clubs")

    def get_club_info(self, term: int, club_id: int) -> Optional[Dict]:
        """
        Pobiera szczegółowe informacje o klubie

        Args:
            term: numer kadencji
            club_id: ID klubu

        Returns:
            Szczegółowe dane klubu lub None
        """
        return self._make_request(f"/sejm/term{term}/clubs/{club_id}")

    def get_club_logo(self, term: int, club_id: int) -> Optional[bytes]:
        """
        Pobiera logo klubu

        Args:
            term: numer kadencji
            club_id: ID klubu

        Returns:
            Logo jako bytes (PNG/JPEG/GIF) lub None
        """
        return self._make_request(f"/sejm/term{term}/clubs/{club_id}/logo")

    # =============================================================================
    # ZARZĄDZANIE CACHE
    # =============================================================================

    def clear_cache(self, cache_type: str = "all"):
        """Czyści cache API"""
        self.cache.reset_cache(cache_type)
        logger.info(f"Wyczyszczono cache: {cache_type}")

    def get_cache_stats(self) -> Dict:
        """Zwraca statystyki cache'u"""
        return self.cache.get_stats()

    def __del__(self):
        """Zapisz cache przy zamykaniu"""
        if hasattr(self, 'cache'):
            try:
                self.cache.save()
            except:
                pass
