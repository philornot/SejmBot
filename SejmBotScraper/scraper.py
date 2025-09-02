# scraper.py
"""
Główna logika scrapowania stenogramów Sejmu RP
"""

import logging
from datetime import datetime, date
from typing import List, Dict, Optional

from config import DEFAULT_TERM
from file_manager import FileManager
from sejm_api import SejmAPI

logger = logging.getLogger(__name__)


class SejmScraper:
    """Główna klasa do scrapowania stenogramów Sejmu"""

    def __init__(self):
        self.api = SejmAPI()
        self.file_manager = FileManager()
        self.stats = {
            'proceedings_processed': 0,
            'pdfs_downloaded': 0,
            'statements_saved': 0,
            'errors': 0,
            'future_proceedings_skipped': 0
        }

    def _is_date_in_future(self, date_str: str) -> bool:
        """
        Sprawdza czy data jest w przyszłości

        Args:
            date_str: data w formacie YYYY-MM-DD

        Returns:
            True jeśli data jest w przyszłości
        """
        try:
            proceeding_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            today = date.today()
            return proceeding_date > today
        except ValueError:
            logger.warning(f"Nieprawidłowy format daty: {date_str}")
            return False

    def _should_skip_future_proceeding(self, proceeding_dates: List[str]) -> bool:
        """
        Sprawdza czy posiedzenie jest w przyszłości i powinno być pominięte

        Args:
            proceeding_dates: lista dat posiedzenia

        Returns:
            True jeśli wszystkie daty są w przyszłości
        """
        if not proceeding_dates:
            return False

        # Jeśli wszystkie daty są w przyszłości, pomiń
        future_dates = [d for d in proceeding_dates if self._is_date_in_future(d)]
        return len(future_dates) == len(proceeding_dates)

    def scrape_term(self, term: int = DEFAULT_TERM, download_pdfs: bool = True,
                    download_statements: bool = False) -> Dict:
        """
        Scrapuje wszystkie stenogramy z danej kadencji

        Args:
            term: numer kadencji
            download_pdfs: czy pobierać pliki PDF
            download_statements: czy pobierać poszczególne wypowiedzi HTML

        Returns:
            Statystyki procesu
        """
        logger.info(f"Rozpoczynanie scrapowania kadencji {term}")

        # Pobierz informacje o kadencji
        term_info = self.api.get_term_info(term)
        if not term_info:
            logger.error(f"Nie można pobrać informacji o kadencji {term}")
            return self.stats

        logger.info(f"Kadencja {term}: {term_info.get('from', '')} - {term_info.get('to', 'obecna')}")

        # Pobierz listę posiedzeń
        proceedings = self.api.get_proceedings(term)
        if not proceedings:
            logger.error(f"Nie można pobrać listy posiedzeń dla kadencji {term}")
            return self.stats

        # Filtruj duplikaty i utwórz unikalną listę posiedzeń
        unique_proceedings = self._filter_unique_proceedings(proceedings)
        logger.info(f"Znaleziono {len(proceedings)} pozycji na liście, {len(unique_proceedings)} unikalnych posiedzeń")

        # Przetwarzaj każde posiedzenie
        for proceeding in unique_proceedings:
            try:
                # Sprawdź czy posiedzenie nie jest w przyszłości
                proceeding_dates = proceeding.get('dates', [])
                if self._should_skip_future_proceeding(proceeding_dates):
                    proceeding_number = proceeding.get('number')
                    logger.info(f"Pomijam przyszłe posiedzenie {proceeding_number} (daty: {proceeding_dates})")
                    self.stats['future_proceedings_skipped'] += 1
                    continue

                self._process_proceeding(term, proceeding, download_pdfs, download_statements)
                self.stats['proceedings_processed'] += 1
            except Exception as e:
                logger.error(f"Błąd przetwarzania posiedzenia {proceeding.get('number', '?')}: {e}")
                self.stats['errors'] += 1

        self._log_final_stats()
        return self.stats

    def _filter_unique_proceedings(self, proceedings: List[Dict]) -> List[Dict]:
        """
        Filtruje duplikaty posiedzeń na podstawie numeru posiedzenia

        Args:
            proceedings: lista wszystkich posiedzeń z API

        Returns:
            Lista unikalnych posiedzeń
        """
        seen_numbers = set()
        unique_proceedings = []

        for proceeding in proceedings:
            number = proceeding.get('number')

            # Pomiń posiedzenia bez numeru lub z numerem 0 (które wydają się być błędne)
            if number is None or number == 0:
                logger.warning(f"Pomijam posiedzenie z nieprawidłowym numerem: {number}")
                continue

            # Dodaj tylko jeśli nie widzieliśmy tego numeru wcześniej
            if number not in seen_numbers:
                seen_numbers.add(number)
                unique_proceedings.append(proceeding)
            else:
                logger.debug(f"Pomijam duplikat posiedzenia {number}")

        # Sortuj według numeru posiedzenia dla lepszego porządku
        unique_proceedings.sort(key=lambda x: x.get('number', 0))

        return unique_proceedings

    def scrape_specific_proceeding(self, term: int, proceeding_number: int,
                                   download_pdfs: bool = True, download_statements: bool = False) -> bool:
        """
        Scrapuje konkretne posiedzenie

        Args:
            term: numer kadencji
            proceeding_number: numer posiedzenia
            download_pdfs: czy pobierać pliki PDF
            download_statements: czy pobierać poszczególne wypowiedzi HTML

        Returns:
            True jeśli sukces, False w przeciwnym przypadku
        """
        logger.info(f"Scrapowanie posiedzenia {proceeding_number} z kadencji {term}")

        # Sprawdź czy numer posiedzenia jest poprawny
        if proceeding_number <= 0:
            logger.error(f"Nieprawidłowy numer posiedzenia: {proceeding_number}")
            return False

        # Znajdź posiedzenie o danym numerze
        proceedings = self.api.get_proceedings(term)
        if not proceedings:
            logger.error(f"Nie można pobrać listy posiedzeń dla kadencji {term}")
            return False

        # Przefiltruj unikalne posiedzenia
        unique_proceedings = self._filter_unique_proceedings(proceedings)

        target_proceeding = None
        for proceeding in unique_proceedings:
            if proceeding.get('number') == proceeding_number:
                target_proceeding = proceeding
                break

        if not target_proceeding:
            logger.error(f"Nie znaleziono posiedzenia {proceeding_number} w kadencji {term}")
            logger.info(f"Dostępne posiedzenia: {[p.get('number') for p in unique_proceedings]}")
            return False

        # Sprawdź czy posiedzenie nie jest w przyszłości
        proceeding_dates = target_proceeding.get('dates', [])
        if self._should_skip_future_proceeding(proceeding_dates):
            logger.warning(f"Posiedzenie {proceeding_number} jest zaplanowane na przyszłość (daty: {proceeding_dates})")
            logger.warning("Stenogramy będą dostępne dopiero po zakończeniu posiedzenia")
            self.stats['future_proceedings_skipped'] += 1
            return False

        try:
            self._process_proceeding(term, target_proceeding, download_pdfs, download_statements)
            self.stats['proceedings_processed'] += 1
            logger.info(f"Zakończono przetwarzanie posiedzenia {proceeding_number}")
            return True
        except Exception as e:
            logger.error(f"Błąd przetwarzania posiedzenia {proceeding_number}: {e}")
            self.stats['errors'] += 1
            return False

    def _process_proceeding(self, term: int, proceeding: Dict,
                            download_pdfs: bool, download_statements: bool):
        """
        Przetwarza jedno posiedzenie

        Args:
            term: numer kadencji
            proceeding: informacje o posiedzeniu
            download_pdfs: czy pobierać PDF-y
            download_statements: czy pobierać wypowiedzi HTML
        """
        proceeding_number = proceeding.get('number')
        logger.info(f"Przetwarzanie posiedzenia {proceeding_number}")

        # Pobierz szczegółowe informacje o posiedzeniu
        detailed_info = self.api.get_proceeding_info(term, proceeding_number)
        if not detailed_info:
            logger.warning(f"Nie można pobrać szczegółów posiedzenia {proceeding_number}")
            detailed_info = proceeding  # użyj podstawowych informacji

        # Zapisz informacje o posiedzeniu
        self.file_manager.save_proceeding_info(term, proceeding_number, detailed_info)

        # Pobierz daty posiedzenia
        dates = detailed_info.get('dates', [])
        if not dates:
            logger.warning(f"Brak dat dla posiedzenia {proceeding_number}")
            return

        # Filtruj tylko przeszłe daty
        past_dates = [d for d in dates if not self._is_date_in_future(d)]
        future_dates = [d for d in dates if self._is_date_in_future(d)]

        if future_dates:
            logger.info(
                f"Posiedzenie {proceeding_number}: {len(past_dates)} dni w przeszłości, {len(future_dates)} dni w przyszłości")
        else:
            logger.info(f"Posiedzenie {proceeding_number} trwało {len(dates)} dni: {dates}")

        if not past_dates:
            logger.info(f"Wszystkie daty posiedzenia {proceeding_number} są w przyszłości - pomijam")
            return

        # Przetwarzaj tylko przeszłe dni posiedzenia
        for date in past_dates:
            self._process_proceeding_day(term, proceeding_number, date,
                                         detailed_info, download_pdfs, download_statements)

    def _process_proceeding_day(self, term: int, proceeding_id: int, date: str,
                                proceeding_info: Dict, download_pdfs: bool, download_statements: bool):
        """
        Przetwarza jeden dzień posiedzenia

        Args:
            term: numer kadencji
            proceeding_id: ID posiedzenia
            date: data w formacie YYYY-MM-DD
            proceeding_info: informacje o posiedzeniu
            download_pdfs: czy pobierać PDF
            download_statements: czy pobierać wypowiedzi HTML
        """
        logger.info(f"Przetwarzanie dnia {date} posiedzenia {proceeding_id}")

        # Pobierz transkrypt PDF jeśli wymagany
        if download_pdfs:
            self._download_pdf_transcript(term, proceeding_id, date, proceeding_info)

        # Pobierz wypowiedzi HTML jeśli wymagane
        if download_statements:
            self._download_html_statements(term, proceeding_id, date, proceeding_info)

    def _download_pdf_transcript(self, term: int, proceeding_id: int, date: str, proceeding_info: Dict):
        """Pobiera transkrypt PDF dla danego dnia"""
        try:
            logger.debug(f"Pobieranie PDF dla {date}")
            pdf_content = self.api.get_transcript_pdf(term, proceeding_id, date)

            if pdf_content:
                saved_path = self.file_manager.save_pdf_transcript(
                    term, proceeding_id, date, pdf_content, proceeding_info
                )
                if saved_path:
                    self.stats['pdfs_downloaded'] += 1
                    logger.info(f"Pobrano PDF: {saved_path}")
                else:
                    logger.warning(f"Nie udało się zapisać PDF dla {date}")
            else:
                # To może być normalne dla przyszłych dat
                if self._is_date_in_future(date):
                    logger.debug(f"PDF dla przyszłej daty {date} nie jest jeszcze dostępny")
                else:
                    logger.warning(f"Brak treści PDF dla {date}")

        except Exception as e:
            # Nie liczymy błędów 404 dla przyszłych dat jako prawdziwych błędów
            if "404" in str(e) and self._is_date_in_future(date):
                logger.debug(f"PDF dla przyszłej daty {date} nie jest jeszcze dostępny (404)")
            else:
                logger.error(f"Błąd pobierania PDF dla {date}: {e}")
                self.stats['errors'] += 1

    def _download_html_statements(self, term: int, proceeding_id: int, date: str, proceeding_info: Dict):
        """Pobiera wypowiedzi HTML dla danego dnia"""
        try:
            logger.debug(f"Pobieranie wypowiedzi HTML dla {date}")
            statements = self.api.get_transcripts_list(term, proceeding_id, date)

            if statements:
                saved_path = self.file_manager.save_html_statements(
                    term, proceeding_id, date, statements, proceeding_info
                )
                if saved_path:
                    statement_count = len(statements.get('statements', []))
                    self.stats['statements_saved'] += statement_count
                    logger.info(f"Zapisano {statement_count} wypowiedzi do: {saved_path}")
                else:
                    logger.warning(f"Nie udało się zapisać wypowiedzi dla {date}")
            else:
                if self._is_date_in_future(date):
                    logger.debug(f"Wypowiedzi dla przyszłej daty {date} nie są jeszcze dostępne")
                else:
                    logger.warning(f"Brak wypowiedzi dla {date}")

        except Exception as e:
            # Nie liczymy błędów 404 dla przyszłych dat jako prawdziwych błędów
            if "404" in str(e) and self._is_date_in_future(date):
                logger.debug(f"Wypowiedzi dla przyszłej daty {date} nie są jeszcze dostępne (404)")
            else:
                logger.error(f"Błąd pobierania wypowiedzi HTML dla {date}: {e}")
                self.stats['errors'] += 1

    def _log_final_stats(self):
        """Loguje końcowe statystyki"""
        logger.info("=== STATYSTYKI KOŃCOWE ===")
        logger.info(f"Przetworzone posiedzenia: {self.stats['proceedings_processed']}")
        logger.info(f"Pominięte przyszłe posiedzenia: {self.stats['future_proceedings_skipped']}")
        logger.info(f"Pobrane PDF-y: {self.stats['pdfs_downloaded']}")
        logger.info(f"Zapisane wypowiedzi: {self.stats['statements_saved']}")
        logger.info(f"Błędy: {self.stats['errors']}")
        logger.info("=========================")

    def get_available_terms(self) -> Optional[List[Dict]]:
        """
        Pobiera listę dostępnych kadencji

        Returns:
            Lista kadencji lub None w przypadku błędu
        """
        return self.api.get_terms()

    def get_term_proceedings_summary(self, term: int) -> Optional[List[Dict]]:
        """
        Pobiera podsumowanie posiedzeń dla kadencji

        Args:
            term: numer kadencji

        Returns:
            Lista z podstawowymi informacjami o posiedzeniach
        """
        proceedings = self.api.get_proceedings(term)
        if not proceedings:
            return None

        # Filtruj duplikaty również w podsumowaniu
        unique_proceedings = self._filter_unique_proceedings(proceedings)

        summary = []
        for proc in unique_proceedings:
            proc_dates = proc.get('dates', [])
            is_future = self._should_skip_future_proceeding(proc_dates)

            summary.append({
                'number': proc.get('number'),
                'title': proc.get('title', ''),
                'dates': proc_dates,
                'current': proc.get('current', False),
                'is_future': is_future
            })

        return summary
