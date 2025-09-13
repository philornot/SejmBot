"""
Interfejs klienta API Sejmu RP
Mały plik interfejsowy - implementacja w sejm_client.py
"""

import logging
from typing import List, Dict, Optional

from SejmBotScraper.core.types import TermInfo, ProceedingInfo, StatementInfo, MPInfo, ClubInfo

logger = logging.getLogger(__name__)


class SejmAPIInterface:
    """
    Interfejs do komunikacji z API Sejmu RP

    Ten plik zawiera tylko interfejs - rzeczywista implementacja
    znajduje się w sejm_client.py
    """

    def __init__(self, cache_manager=None, config=None):
        """
        Inicjalizuje interfejs API

        Args:
            cache_manager: manager cache (opcjonalny)
            config: konfiguracja API (opcjonalna)
        """
        # Import implementacji dopiero tutaj aby uniknąć circular imports
        from .sejm_client import SejmAPIClient

        self._client = SejmAPIClient(cache_manager, config)
        logger.debug("Zainicjalizowano interfejs API Sejmu")

    # === KADENCJE I POSIEDZENIA ===

    def get_terms(self) -> Optional[List[TermInfo]]:
        """
        Pobiera listę kadencji

        Returns:
            Lista kadencji lub None w przypadku błędu
        """
        logger.debug("Pobieranie listy kadencji")
        return self._client.get_terms()

    def get_term_info(self, term: int) -> Optional[TermInfo]:
        """
        Pobiera informacje o konkretnej kadencji

        Args:
            term: numer kadencji

        Returns:
            Informacje o kadencji lub None
        """
        logger.debug(f"Pobieranie informacji o kadencji {term}")
        return self._client.get_term_info(term)

    def get_proceedings(self, term: int) -> Optional[List[ProceedingInfo]]:
        """
        Pobiera listę posiedzeń kadencji

        Args:
            term: numer kadencji

        Returns:
            Lista posiedzeń lub None
        """
        logger.debug(f"Pobieranie listy posiedzeń kadencji {term}")
        return self._client.get_proceedings(term)

    def get_proceeding_info(self, term: int, proceeding_id: int) -> Optional[ProceedingInfo]:
        """
        Pobiera szczegółowe informacje o posiedzeniu

        Args:
            term: numer kadencji
            proceeding_id: ID posiedzenia

        Returns:
            Informacje o posiedzeniu lub None
        """
        logger.debug(f"Pobieranie informacji o posiedzeniu {proceeding_id} kadencji {term}")
        return self._client.get_proceeding_info(term, proceeding_id)

    # === STENOGRAMY ===

    def get_statements(self, term: int, proceeding: int, date: str) -> Optional[List[StatementInfo]]:
        """
        Pobiera wypowiedzi z danego dnia posiedzenia

        Args:
            term: numer kadencji
            proceeding: ID posiedzenia
            date: data w formacie YYYY-MM-DD

        Returns:
            Lista wypowiedzi lub None
        """
        logger.debug(f"Pobieranie wypowiedzi {term}/{proceeding}/{date}")
        return self._client.get_transcripts_list(term, proceeding, date)

    def get_statement_html(self, term: int, proceeding: int, date: str, statement_num: int) -> Optional[str]:
        """
        Pobiera HTML konkretnej wypowiedzi

        Args:
            term: numer kadencji
            proceeding: ID posiedzenia
            date: data w formacie YYYY-MM-DD
            statement_num: numer wypowiedzi

        Returns:
            HTML wypowiedzi lub None
        """
        logger.debug(f"Pobieranie HTML wypowiedzi {statement_num} z {term}/{proceeding}/{date}")
        return self._client.get_statement_html(term, proceeding, date, statement_num)

    def get_statement_text(self, term: int, proceeding: int, date: str, statement_num: int) -> Optional[str]:
        """
        Pobiera pełną treść konkretnej wypowiedzi jako tekst

        Args:
            term: numer kadencji
            proceeding: ID posiedzenia
            date: data w formacie YYYY-MM-DD
            statement_num: numer wypowiedzi

        Returns:
            Tekst wypowiedzi lub None
        """
        logger.debug(f"Pobieranie tekstu wypowiedzi {statement_num} z {term}/{proceeding}/{date}")
        return self._client.get_statement_full_text(term, proceeding, date, statement_num)

    # === POSŁOWIE ===

    def get_mps(self, term: int) -> Optional[List[MPInfo]]:
        """
        Pobiera listę posłów kadencji

        Args:
            term: numer kadencji

        Returns:
            Lista posłów lub None
        """
        logger.debug(f"Pobieranie listy posłów kadencji {term}")
        return self._client.get_mps(term)

    def get_mp_info(self, term: int, mp_id: int) -> Optional[MPInfo]:
        """
        Pobiera szczegółowe informacje o pośle

        Args:
            term: numer kadencji
            mp_id: ID posła

        Returns:
            Informacje o pośle lub None
        """
        logger.debug(f"Pobieranie informacji o pośle {mp_id} kadencji {term}")
        return self._client.get_mp_info(term, mp_id)

    def get_mp_photo(self, term: int, mp_id: int) -> Optional[bytes]:
        """
        Pobiera zdjęcie posła

        Args:
            term: numer kadencji
            mp_id: ID posła

        Returns:
            Zdjęcie jako bytes lub None
        """
        logger.debug(f"Pobieranie zdjęcia posła {mp_id} kadencji {term}")
        return self._client.get_mp_photo(term, mp_id)

    def get_mp_voting_stats(self, term: int, mp_id: int) -> Optional[Dict]:
        """
        Pobiera statystyki głosowań posła

        Args:
            term: numer kadencji
            mp_id: ID posła

        Returns:
            Statystyki głosowań lub None
        """
        logger.debug(f"Pobieranie statystyk głosowań posła {mp_id} kadencji {term}")
        return self._client.get_mp_voting_stats(term, mp_id)

    # === KLUBY ===

    def get_clubs(self, term: int) -> Optional[List[ClubInfo]]:
        """
        Pobiera listę klubów parlamentarnych

        Args:
            term: numer kadencji

        Returns:
            Lista klubów lub None
        """
        logger.debug(f"Pobieranie listy klubów kadencji {term}")
        return self._client.get_clubs(term)

    def get_club_info(self, term: int, club_id: int) -> Optional[ClubInfo]:
        """
        Pobiera szczegółowe informacje o klubie

        Args:
            term: numer kadencji
            club_id: ID klubu

        Returns:
            Informacje o klubie lub None
        """
        logger.debug(f"Pobieranie informacji o klubie {club_id} kadencji {term}")
        return self._client.get_club_info(term, club_id)

    def get_club_logo(self, term: int, club_id: int) -> Optional[bytes]:
        """
        Pobiera logo klubu

        Args:
            term: numer kadencji
            club_id: ID klubu

        Returns:
            Logo jako bytes lub None
        """
        logger.debug(f"Pobieranie logo klubu {club_id} kadencji {term}")
        return self._client.get_club_logo(term, club_id)

    # === ZARZĄDZANIE CACHE ===

    def clear_cache(self, cache_type: str = "all") -> None:
        """
        Czyści cache API

        Args:
            cache_type: typ cache do wyczyszczenia (all, api, memory, file)
        """
        logger.info(f"Czyszczenie cache: {cache_type}")
        return self._client.clear_cache(cache_type)

    def get_cache_stats(self) -> Dict:
        """
        Zwraca statystyki cache

        Returns:
            Słownik ze statystykami cache
        """
        return self._client.get_cache_stats()

    # === POMOCNICZE METODY ===

    def is_healthy(self) -> bool:
        """
        Sprawdza czy API jest dostępne

        Returns:
            True jeśli API odpowiada
        """
        try:
            terms = self.get_terms()
            return terms is not None
        except Exception:
            return False

    def get_client_info(self) -> Dict:
        """
        Zwraca informacje o kliencie API

        Returns:
            Słownik z informacjami o kliencie
        """
        return {
            'client_type': 'SejmAPIInterface',
            'implementation': 'SejmAPIClient',
            'healthy': self.is_healthy(),
            'cache_stats': self.get_cache_stats()
        }

    def __repr__(self) -> str:
        """Reprezentacja string obiektu"""
        return f"SejmAPIInterface(client={self._client.__class__.__name__})"
