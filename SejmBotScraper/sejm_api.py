# sejm_api.py
"""
Klasa do komunikacji z API Sejmu RP
"""

import logging
import time
from typing import List, Dict, Optional, Any

import requests

from config import API_BASE_URL, REQUEST_TIMEOUT, REQUEST_DELAY, USER_AGENT

logger = logging.getLogger(__name__)


class SejmAPI:
    """Klasa do komunikacji z API Sejmu RP"""

    def __init__(self):
        self.base_url = API_BASE_URL
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': USER_AGENT
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

            # Sprawdź czy to JSON
            if 'application/json' in response.headers.get('content-type', ''):
                return response.json()
            else:
                return response.content

        except requests.exceptions.RequestException as e:
            logger.error(f"Błąd zapytania do {url}: {e}")
            return None

    # =============================================================================
    # KADENCJE I POSIEDZENIA
    # =============================================================================

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

    # =============================================================================
    # STENOGRAMY I WYPOWIEDZI
    # =============================================================================

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

    # =============================================================================
    # POSŁOWIE
    # =============================================================================

    def get_mps(self, term: int) -> Optional[List[Dict]]:
        """
        Pobiera listę wszystkich posłów dla danej kadencji

        Args:
            term: numer kadencji

        Returns:
            Lista posłów z podstawowymi danymi lub None
        """
        return self._make_request(f"/sejm/term{term}/MP")

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
