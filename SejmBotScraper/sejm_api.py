# sejm_api.py
"""
Klasa do komunikacji z API Sejmu RP
"""

import logging
import time
from typing import List, Dict, Optional, Any

import requests

from config import API_BASE_URL, REQUEST_TIMEOUT, REQUEST_DELAY

logger = logging.getLogger(__name__)


class SejmAPI:
    """Klasa do komunikacji z API Sejmu RP"""

    def __init__(self):
        self.base_url = API_BASE_URL
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'SejmBotScraper/1.0 (Educational Purpose)'
        })

    def _make_request(self, endpoint: str) -> Optional[Any]:
        """
        Wykonuje zapytanie do API z obsługą błędów

        Args:
            endpoint: Endpoint API (bez base URL)

        Returns:
            Odpowiedź JSON lub None w przypadku błędu
        """
        url = f"{self.base_url}{endpoint}"

        try:
            logger.debug(f"Zapytanie do: {url}")
            time.sleep(REQUEST_DELAY)  # Gentle rate limiting

            response = self.session.get(url, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()

            # Sprawdz czy to JSON
            if 'application/json' in response.headers.get('content-type', ''):
                return response.json()
            else:
                return response.content

        except requests.exceptions.RequestException as e:
            logger.error(f"Błąd zapytania do {url}: {e}")
            return None

    def get_terms(self) -> Optional[List[Dict]]:
        """Pobiera listę kadencji Sejmu"""
        return self._make_request("/sejm/term")

    def get_term_info(self, term: int) -> Optional[Dict]:
        """Pobiera informacje o konkretnej kadencji"""
        return self._make_request(f"/sejm/term{term}")

    def get_proceedings(self, term: int) -> Optional[List[Dict]]:
        """Pobiera listę posiedzeń dla danej kadencji"""
        return self._make_request(f"/sejm/term{term}/proceedings")

    def get_proceeding_info(self, term: int, proceeding_id: int) -> Optional[Dict]:
        """Pobiera szczegółowe informacje o posiedzeniu"""
        return self._make_request(f"/sejm/term{term}/proceedings/{proceeding_id}")

    def get_transcripts_list(self, term: int, proceeding_id: int, date: str) -> Optional[Dict]:
        """
        Pobiera listę wypowiedzi z danego dnia posiedzenia

        Args:
            term: numer kadencji
            proceeding_id: ID posiedzenia
            date: data w formacie YYYY-MM-DD
        """
        return self._make_request(f"/sejm/term{term}/proceedings/{proceeding_id}/{date}/transcripts")

    def get_transcript_pdf(self, term: int, proceeding_id: int, date: str) -> Optional[bytes]:
        """
        Pobiera transkrypt całego dnia w formacie PDF

        Args:
            term: numer kadencji
            proceeding_id: ID posiedzenia
            date: data w formacie YYYY-MM-DD

        Returns:
            Zawartość PDF jako bytes lub None
        """
        return self._make_request(f"/sejm/term{term}/proceedings/{proceeding_id}/{date}/transcripts/pdf")

    def get_statement_html(self, term: int, proceeding_id: int, date: str, statement_num: int) -> Optional[str]:
        """
        Pobiera konkretną wypowiedź w formacie HTML

        Args:
            term: numer kadencji
            proceeding_id: ID posiedzenia
            date: data w formacie YYYY-MM-DD
            statement_num: numer wypowiedzi

        Returns:
            HTML jako string lub None
        """
        content = self._make_request(f"/sejm/term{term}/proceedings/{proceeding_id}/{date}/transcripts/{statement_num}")
        if isinstance(content, bytes):
            return content.decode('utf-8')
        return content
