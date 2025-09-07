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
        self.mp_data_cache = {}  # Cache dla danych posłów
        self.stats = {
            'proceedings_processed': 0,
            'statements_processed': 0,
            'statements_with_full_content': 0,
            'speakers_identified': 0,
            'mp_data_enrichments': 0,
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

    def _load_mp_data(self, term: int) -> Dict:
        """
        Ładuje i cache'uje dane posłów dla danej kadencji

        Args:
            term: numer kadencji

        Returns:
            Słownik mapujący imię+nazwisko -> dane posła
        """
        if term in self.mp_data_cache:
            return self.mp_data_cache[term]

        logger.info(f"Ładowanie danych posłów dla kadencji {term}")

        try:
            # Pobierz listę posłów
            mps = self.api.get_mps(term)
            if not mps:
                logger.warning(f"Nie udało się pobrać listy posłów dla kadencji {term}")
                self.mp_data_cache[term] = {}
                return {}

            mp_dict = {}
            for mp in mps:
                # Tworzenie kluczy do wyszukiwania (różne warianty imion/nazwisk)
                first_name = mp.get('firstName', '').strip()
                last_name = mp.get('lastName', '').strip()
                full_name = f"{first_name} {last_name}".strip()

                # Dodaj różne warianty nazw do słownika
                if full_name:
                    mp_dict[full_name] = mp
                    mp_dict[f"{last_name} {first_name}"] = mp  # odwrócona kolejność
                    mp_dict[last_name] = mp  # samo nazwisko

            self.mp_data_cache[term] = mp_dict
            logger.info(f"Załadowano dane {len(mps)} posłów dla kadencji {term}")
            return mp_dict

        except Exception as e:
            logger.error(f"Błąd ładowania danych posłów dla kadencji {term}: {e}")
            self.mp_data_cache[term] = {}
            return {}

    def _enrich_statements_with_mp_data(self, statements: List[Dict], term: int) -> List[Dict]:
        """
        Wzbogaca wypowiedzi o dane posłów (klub, okręg, funkcja)

        Args:
            statements: lista wypowiedzi
            term: numer kadencji

        Returns:
            Lista wzbogaconych wypowiedzi
        """
        mp_data = self._load_mp_data(term)
        enriched_statements = []
        speakers_found = set()

        for statement in statements:
            enriched_statement = statement.copy()

            # Pobierz dane o mówcy
            speaker_name = statement.get('speaker', {}).get('name', '').strip()

            if speaker_name and speaker_name in mp_data:
                mp_info = mp_data[speaker_name]

                # Wzbogać dane o mówcy
                enriched_statement['speaker']['mp_data'] = {
                    'id': mp_info.get('id'),
                    'club': mp_info.get('club', ''),
                    'districtName': mp_info.get('districtName', ''),
                    'districtNum': mp_info.get('districtNum'),
                    'educationLevel': mp_info.get('educationLevel', ''),
                    'numberOfVotes': mp_info.get('numberOfVotes'),
                    'profession': mp_info.get('profession', ''),
                    'voivodeship': mp_info.get('voivodeship', '')
                }

                enriched_statement['speaker']['is_mp'] = True
                speakers_found.add(speaker_name)
                self.stats['mp_data_enrichments'] += 1
            else:
                enriched_statement['speaker']['mp_data'] = None
                enriched_statement['speaker']['is_mp'] = False

            enriched_statements.append(enriched_statement)

        # Aktualizuj statystyki
        unique_speakers = len(
            {stmt.get('speaker', {}).get('name', '') for stmt in statements if stmt.get('speaker', {}).get('name', '')})
        self.stats['speakers_identified'] += len(speakers_found)

        logger.debug(f"Wzbogacono {len(speakers_found)}/{unique_speakers} unikalnych mówców danymi posłów")

        return enriched_statements

    def _can_fetch_full_statement(self, term: int, proceeding_id: int, date: str, statement_num: int) -> bool:
        """
        Sprawdza czy można pobrać pełną treść wypowiedzi przez API

        Args:
            term: numer kadencji
            proceeding_id: ID posiedzenia
            date: data
            statement_num: numer wypowiedzi

        Returns:
            True jeśli można pobrać pełną treść
        """
        try:
            # Szybkie sprawdzenie HEAD request (jeśli API to wspiera)
            # Dla uproszczenia sprawdzamy przez próbę pobrania
            content = self.api.get_statement_html(term, proceeding_id, date, statement_num)
            return content is not None and len(content.strip()) > 0
        except:
            return False

    def _fetch_full_statement_content(self, term: int, proceeding_id: int, date: str, statement_num: int) -> Optional[
        str]:
        """
        Pobiera pełną treść wypowiedzi przez API

        Args:
            term: numer kadencji
            proceeding_id: ID posiedzenia
            date: data
            statement_num: numer wypowiedzi

        Returns:
            Pełna treść wypowiedzi jako HTML lub None
        """
        try:
            content = self.api.get_statement_html(term, proceeding_id, date, statement_num)
            if content and len(content.strip()) > 0:
                return content.strip()
            return None
        except Exception as e:
            logger.debug(f"Nie udało się pobrać pełnej treści wypowiedzi {statement_num}: {e}")
            return None

    def _enrich_statements_with_full_content(self, statements: List[Dict], term: int, proceeding_id: int, date: str) -> \
            List[Dict]:
        """
        Próbuje pobrać pełną treść dla wypowiedzi

        Args:
            statements: lista wypowiedzi
            term: numer kadencji
            proceeding_id: ID posiedzenia
            date: data

        Returns:
            Lista wypowiedzi wzbogaconych o pełną treść
        """
        enriched_statements = []

        for statement in statements:
            enriched_statement = statement.copy()
            statement_num = statement.get('num')

            if statement_num:
                # Sprawdź czy można pobrać pełną treść
                full_content = self._fetch_full_statement_content(term, proceeding_id, date, statement_num)

                if full_content:
                    enriched_statement['content']['text'] = full_content
                    enriched_statement['content']['has_full_content'] = True
                    enriched_statement['content']['content_source'] = 'api_html'
                    self.stats['statements_with_full_content'] += 1
                    logger.debug(f"Pobrano pełną treść wypowiedzi {statement_num}")
                else:
                    enriched_statement['content']['text'] = ''
                    enriched_statement['content']['has_full_content'] = False
                    enriched_statement['content']['content_source'] = 'not_available'

            enriched_statements.append(enriched_statement)

        return enriched_statements

    def scrape_term(self, term: int = DEFAULT_TERM, fetch_full_statements: bool = True) -> Dict:
        """
        Scrapuje wszystkie stenogramy z danej kadencji

        Args:
            term: numer kadencji
            fetch_full_statements: czy pobierać pełną treść wypowiedzi

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

        # Przeładuj dane posłów na początku
        self._load_mp_data(term)

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

                self._process_proceeding(term, proceeding, fetch_full_statements)
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
                                   fetch_full_statements: bool = True) -> bool:
        """
        Scrapuje konkretne posiedzenie

        Args:
            term: numer kadencji
            proceeding_number: numer posiedzenia
            fetch_full_statements: czy pobierać pełną treść wypowiedzi

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

        # Przeładuj dane posłów
        self._load_mp_data(term)

        try:
            self._process_proceeding(term, target_proceeding, fetch_full_statements)
            self.stats['proceedings_processed'] += 1
            logger.info(f"Zakończono przetwarzanie posiedzenia {proceeding_number}")
            return True
        except Exception as e:
            logger.error(f"Błąd przetwarzania posiedzenia {proceeding_number}: {e}")
            self.stats['errors'] += 1
            return False

    def _process_proceeding(self, term: int, proceeding: Dict, fetch_full_statements: bool):
        """
        Przetwarza jedno posiedzenie

        Args:
            term: numer kadencji
            proceeding: informacje o posiedzeniu
            fetch_full_statements: czy pobierać pełną treść wypowiedzi
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
            self._process_proceeding_day(term, proceeding_number, date, detailed_info, fetch_full_statements)

    def _process_proceeding_day(self, term: int, proceeding_id: int, date: str,
                                proceeding_info: Dict, fetch_full_statements: bool):
        """
        Przetwarza jeden dzień posiedzenia - pobiera i wzbogaca wypowiedzi

        Args:
            term: numer kadencji
            proceeding_id: ID posiedzenia
            date: data w formacie YYYY-MM-DD
            proceeding_info: informacje o posiedzeniu
            fetch_full_statements: czy pobierać pełną treść wypowiedzi
        """
        logger.info(f"Przetwarzanie dnia {date} posiedzenia {proceeding_id}")

        try:
            # Pobierz listę wypowiedzi
            statements_data = self.api.get_transcripts_list(term, proceeding_id, date)

            if not statements_data or 'statements' not in statements_data:
                if self._is_date_in_future(date):
                    logger.debug(f"Wypowiedzi dla przyszłej daty {date} nie są jeszcze dostępne")
                else:
                    logger.warning(f"Brak wypowiedzi dla {date}")
                return

            statements = statements_data['statements']
            if not statements:
                logger.info(f"Brak wypowiedzi do przetworzenia dla {date}")
                return

            logger.info(f"Znaleziono {len(statements)} wypowiedzi dla {date}")

            # Przekształć wypowiedzi do standardowej struktury
            processed_statements = []
            for statement in statements:
                processed_statement = {
                    "num": statement.get('num'),
                    "speaker": {
                        "name": statement.get('name', 'Nieznany'),
                        "function": statement.get('function', ''),
                        "club": statement.get('club', ''),
                        "first_name": statement.get('firstName', ''),
                        "last_name": statement.get('lastName', '')
                    },
                    "timing": {
                        "start_datetime": statement.get('startDateTime', ''),
                        "end_datetime": statement.get('endDateTime', ''),
                        "duration_seconds": self.file_manager._calculate_duration(
                            statement.get('startDateTime'),
                            statement.get('endDateTime')
                        )
                    },
                    "content": {
                        "text": '',
                        "has_full_content": False,
                        "content_source": 'not_fetched'
                    },
                    "technical": {
                        "api_url": f"/sejm/term{term}/proceedings/{proceeding_id}/{date}/transcripts/{statement.get('num')}",
                        "original_data": statement
                    }
                }
                processed_statements.append(processed_statement)

            # Wzbogać wypowiedzi o dane posłów
            enriched_statements = self._enrich_statements_with_mp_data(processed_statements, term)

            # Pobierz pełną treść wypowiedzi jeśli wymagane
            if fetch_full_statements:
                logger.info(f"Pobieranie pełnej treści wypowiedzi dla {date}")
                enriched_statements = self._enrich_statements_with_full_content(
                    enriched_statements, term, proceeding_id, date
                )

            # Zapisz wzbogacone wypowiedzi
            saved_path = self.file_manager.save_proceeding_transcripts(
                term, proceeding_id, date, statements_data, proceeding_info, enriched_statements
            )

            if saved_path:
                self.stats['statements_processed'] += len(enriched_statements)
                logger.info(f"Zapisano {len(enriched_statements)} wzbogaconych wypowiedzi do: {saved_path}")
            else:
                logger.warning(f"Nie udało się zapisać wypowiedzi dla {date}")

        except Exception as e:
            if "404" in str(e) and self._is_date_in_future(date):
                logger.debug(f"Wypowiedzi dla przyszłej daty {date} nie są jeszcze dostępne (404)")
            else:
                logger.error(f"Błąd przetwarzania wypowiedzi dla {date}: {e}")
                self.stats['errors'] += 1

    def _log_final_stats(self):
        """Loguje końcowe statystyki"""
        logger.info("=== STATYSTYKI KOŃCOWE ===")
        logger.info(f"Przetworzone posiedzenia: {self.stats['proceedings_processed']}")
        logger.info(f"Pominięte przyszłe posiedzenia: {self.stats['future_proceedings_skipped']}")
        logger.info(f"Przetworzone wypowiedzi: {self.stats['statements_processed']}")
        logger.info(f"Wypowiedzi z pełną treścią: {self.stats['statements_with_full_content']}")
        logger.info(f"Zidentyfikowani mówcy: {self.stats['speakers_identified']}")
        logger.info(f"Wzbogacenia danymi posłów: {self.stats['mp_data_enrichments']}")
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

    def clear_mp_cache(self):
        """Czyści cache danych posłów"""
        self.mp_data_cache.clear()
        logger.debug("Wyczyszczono cache danych posłów")

    def get_mp_cache_info(self) -> Dict:
        """
        Zwraca informacje o cache'u danych posłów

        Returns:
            Słownik z informacjami o cache'u
        """
        return {
            'cached_terms': list(self.mp_data_cache.keys()),
            'total_cached_mps': sum(len(data) for data in self.mp_data_cache.values())
        }
