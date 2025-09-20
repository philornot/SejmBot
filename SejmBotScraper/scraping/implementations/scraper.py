"""
Implementacja scrapera stenogramów - NAPRAWIONA WERSJA
Używa naprawionego API clienta i cache managera
"""

import logging
from datetime import datetime, date
from pathlib import Path
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

# Domyślne ustawienia
DEFAULT_TERM = 10


class SejmScraper:
    """NAPRAWIONA implementacja scrapera stenogramów"""

    def __init__(self, api_client=None, cache_manager=None, config: Optional[Dict] = None):
        """
        Inicjalizuje scraper z naprrawionymi komponentami

        Args:
            api_client: naprawiony API client
            cache_manager: manager cache
            config: konfiguracja scrapera
        """
        self.config = config or {}
        self.api_client = api_client
        self.cache_manager = cache_manager

        # Fallback - jeśli nie podano API clienta, spróbuj zainicjalizować
        if not self.api_client:
            logger.warning("Brak API clienta - inicjalizuję fallback")
            try:
                from ...api.sejm_client import SejmAPIClient
                self.api_client = SejmAPIClient(cache_manager, config)
                logger.info("Fallback API client zainicjalizowany")
            except ImportError as e:
                logger.error(f"Nie można zainicjalizować API clienta: {e}")
                raise RuntimeError("API client jest wymagany")

        # Konfiguracja
        self.force_refresh = self.config.get('force_refresh', False)

        # Cache dla danych MP
        self.mp_data_cache = {}

        # Statystyki
        self.stats = {
            'proceedings_processed': 0,
            'statements_processed': 0,
            'statements_with_full_content': 0,
            'speakers_identified': 0,
            'mp_data_enrichments': 0,
            'errors': 0,
            'future_proceedings_skipped': 0,
            'proceedings_skipped_cache': 0,
            'transcripts_skipped_cache': 0
        }

        # Inicjalizacja file managera
        try:
            from ...storage.file_manager import FileManagerInterface
            self.file_manager = FileManagerInterface(config)
            logger.debug("File manager zainicjalizowany")
        except ImportError as e:
            logger.warning(f"Nie można załadować file managera: {e}")
            self.file_manager = None

        logger.info("SejmScraper implementation zainicjalizowany")
        logger.debug(f"API client: {self.api_client.__class__.__name__}")
        logger.debug(f"Cache manager: {self.cache_manager.__class__.__name__ if self.cache_manager else 'None'}")

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
            mps = self.api_client.get_mps(term)
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
            content = self.api_client.get_statement_html(term, proceeding_id, date, statement_num)
            if content and len(content.strip()) > 0:
                return content.strip()
            return None
        except Exception as e:
            logger.debug(f"Nie udało się pobrać pełnej treści wypowiedzi {statement_num}: {e}")
            return None

    def scrape_term(self, term: int = DEFAULT_TERM, fetch_full_statements: bool = True,
                    force_refresh: bool = False) -> Dict:
        """
        NAPRAWIONA METODA - scrapuje wszystkie stenogramy z danej kadencji

        Args:
            term: numer kadencji
            fetch_full_statements: czy pobierać pełną treść wypowiedzi
            force_refresh: czy wymusić odświeżenie danych

        Returns:
            Statystyki procesu
        """
        logger.info(f"=== ROZPOCZYNANIE SCRAPOWANIA KADENCJI {term} ===")

        # Resetuj statystyki
        self.stats = {
            'proceedings_processed': 0,
            'statements_processed': 0,
            'statements_with_full_content': 0,
            'speakers_identified': 0,
            'mp_data_enrichments': 0,
            'errors': 0,
            'future_proceedings_skipped': 0,
            'proceedings_skipped_cache': 0,
            'transcripts_skipped_cache': 0
        }

        # Zaktualizuj flagę force_refresh
        self.force_refresh = force_refresh
        if force_refresh:
            logger.info("WYMUSZONO ODŚWIEŻENIE - wszystkie dane zostaną pobrane ponownie")

        # Pobierz informacje o kadencji
        logger.info(f"Pobieranie informacji o kadencji {term}...")
        term_info = self.api_client.get_term_info(term)
        if not term_info:
            logger.error(f"Nie można pobrać informacji o kadencji {term}")
            self.stats['errors'] += 1
            return self.stats

        logger.info(f"Kadencja {term}: {term_info.get('from', '')} - {term_info.get('to', 'obecna')}")

        # Pobierz listę posiedzeń - KLUCZOWA CZĘŚĆ
        logger.info(f"Pobieranie listy posiedzeń kadencji {term}...")

        # DEBUGOWANIE: Sprawdź czy API client ma metodę get_proceedings
        if not hasattr(self.api_client, 'get_proceedings'):
            logger.error(f"API client {self.api_client.__class__.__name__} nie ma metody get_proceedings")
            self.stats['errors'] += 1
            return self.stats

        proceedings = self.api_client.get_proceedings(term)

        # SZCZEGÓŁOWE DEBUGOWANIE
        logger.debug(f"get_proceedings zwróciło: {type(proceedings)}")
        logger.debug(f"proceedings is None: {proceedings is None}")
        logger.debug(f"proceedings is empty list: {proceedings == []}")

        if proceedings is None:
            logger.error("API zwróciło None dla listy posiedzeń")
            self.stats['errors'] += 1
            return self.stats

        if len(proceedings) == 0:
            logger.warning("API zwróciło pustą listę posiedzeń")
            logger.info("Możliwe przyczyny:")
            logger.info("1. Kadencja nie ma jeszcze posiedzeń")
            logger.info("2. Problem z API Sejmu")
            logger.info("3. Nieprawidłowy numer kadencji")

            # Spróbuj alternatywnych metod
            logger.info("Próbuję alternatywne metody pobierania...")

            # Test bezpośredni
            if hasattr(self.api_client, 'test_connection'):
                test_result = self.api_client.test_connection()
                logger.info(f"Test połączenia: {test_result.get('proceedings_working', False)}")
                if not test_result.get('proceedings_working', False):
                    logger.error("API nie działa poprawnie - test połączenia nieudany")
                    self.stats['errors'] += 1
                    return self.stats

            return self.stats

        logger.info(f"✓ Znaleziono {len(proceedings)} posiedzeń")

        # Pokaż przykład pierwszego posiedzenia
        if len(proceedings) > 0:
            first_proc = proceedings[0]
            logger.info(f"Przykład pierwszego posiedzenia:")
            logger.info(f"  Numer: {first_proc.get('number', 'brak')}")
            logger.info(f"  Tytuł: {first_proc.get('title', 'brak')[:100]}...")
            logger.info(f"  Daty: {len(first_proc.get('dates', []))} dni")

        # Filtruj duplikaty i utwórz unikalną listę posiedzeń
        unique_proceedings = self._filter_unique_proceedings(proceedings)
        logger.info(f"Po filtrowaniu: {len(unique_proceedings)} unikalnych posiedzeń")

        # Przeładuj dane posłów na początku
        logger.info("Ładowanie danych posłów...")
        self._load_mp_data(term)

        # Przetwarzaj każde posiedzenie
        logger.info("Rozpoczynanie przetwarzania posiedzeń...")

        for i, proceeding in enumerate(unique_proceedings, 1):
            try:
                proceeding_number = proceeding.get('number')
                logger.info(f"[{i}/{len(unique_proceedings)}] Przetwarzanie posiedzenia {proceeding_number}")

                # Sprawdź czy posiedzenie nie jest w przyszłości
                proceeding_dates = proceeding.get('dates', [])
                if self._should_skip_future_proceeding(proceeding_dates):
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

    def _process_proceeding(self, term: int, proceeding: Dict, fetch_full_statements: bool):
        """
        Przetwarza jedno posiedzenie

        Args:
            term: numer kadencji
            proceeding: informacje o posiedzeniu
            fetch_full_statements: czy pobierać pełną treść wypowiedzi
        """
        proceeding_number = proceeding.get('number')
        logger.debug(f"Przetwarzanie posiedzenia {proceeding_number}")

        # Sprawdź czy posiedzenie wymaga odświeżenia (jeśli jest cache)
        proceeding_dates = proceeding.get('dates', [])
        if (not self.force_refresh and self.cache_manager and
                hasattr(self.cache_manager, 'should_refresh_proceeding')):

            should_refresh = self.cache_manager.should_refresh_proceeding(
                term, proceeding_number, proceeding_dates, force=False
            )

            if not should_refresh:
                logger.info(f"Pomijam posiedzenie {proceeding_number} - nie wymaga odświeżenia")
                if hasattr(self.cache_manager, 'mark_proceeding_checked'):
                    self.cache_manager.mark_proceeding_checked(term, proceeding_number, "skipped")
                self.stats['proceedings_skipped_cache'] += 1
                return

        # Pobierz szczegółowe informacje o posiedzeniu
        detailed_info = self.api_client.get_proceeding_info(term, proceeding_number)
        if not detailed_info:
            logger.warning(f"Nie można pobrać szczegółów posiedzenia {proceeding_number}")
            detailed_info = proceeding  # użyj podstawowych informacji

        # Zapisz informacje o posiedzeniu (jeśli file manager dostępny)
        if self.file_manager:
            try:
                self.file_manager.save_proceeding_info(term, proceeding_number, detailed_info)
            except Exception as e:
                logger.warning(f"Nie udało się zapisać info posiedzenia: {e}")

        # Pobierz daty posiedzenia
        dates = detailed_info.get('dates', [])
        if not dates:
            logger.warning(f"Brak dat dla posiedzenia {proceeding_number}")
            return

        # Filtruj tylko przeszłe daty
        past_dates = [d for d in dates if not self._is_date_in_future(d)]
        future_dates = [d for d in dates if self._is_date_in_future(d)]

        if future_dates:
            logger.debug(
                f"Posiedzenie {proceeding_number}: {len(past_dates)} dni w przeszłości, {len(future_dates)} dni w przyszłości")

        if not past_dates:
            logger.info(f"Wszystkie daty posiedzenia {proceeding_number} są w przyszłości - pomijam")
            return

        # Przetwarzaj tylko przeszłe dni posiedzenia
        for date in past_dates:
            self._process_proceeding_day(term, proceeding_number, date, detailed_info, fetch_full_statements)

        # Oznacz posiedzenie jako sprawdzone (jeśli cache jest dostępne)
        if self.cache_manager and hasattr(self.cache_manager, 'mark_proceeding_checked'):
            self.cache_manager.mark_proceeding_checked(term, proceeding_number, "processed")

    def _process_proceeding_day(self, term: int, proceeding_id: int, date: str,
                                proceeding_info: Dict, fetch_full_statements: bool):
        """
        Przetwarza jeden dzień posiedzenia

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
            statements_data = self.api_client.get_transcripts_list(term, proceeding_id, date)

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
                        "duration_seconds": self._calculate_duration(
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

            # Zapisz wzbogacone wypowiedzi (jeśli file manager dostępny)
            if self.file_manager:
                try:
                    saved_path = self.file_manager.save_proceeding_transcripts(
                        term, proceeding_id, date, statements_data, proceeding_info, enriched_statements
                    )

                    if saved_path and self.cache_manager and hasattr(self.cache_manager, 'set_file_cache'):
                        # Zarejestruj plik w cache
                        self.cache_manager.set_file_cache(Path(saved_path), {
                            'term': term,
                            'proceeding_id': proceeding_id,
                            'date': date,
                            'statements_count': len(enriched_statements)
                        })

                    if saved_path:
                        logger.info(f"Zapisano {len(enriched_statements)} wypowiedzi do: {saved_path}")
                    else:
                        logger.warning(f"Nie udało się zapisać wypowiedzi dla {date}")

                except Exception as e:
                    logger.error(f"Błąd zapisywania wypowiedzi dla {date}: {e}")

            self.stats['statements_processed'] += len(enriched_statements)

        except Exception as e:
            if "404" in str(e) and self._is_date_in_future(date):
                logger.debug(f"Wypowiedzi dla przyszłej daty {date} nie są jeszcze dostępne (404)")
            else:
                logger.error(f"Błąd przetwarzania wypowiedzi dla {date}: {e}")
                self.stats['errors'] += 1

    def _enrich_statements_with_full_content(self, statements: List[Dict], term: int,
                                             proceeding_id: int, date: str) -> List[Dict]:
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

    def _calculate_duration(self, start_datetime: Optional[str], end_datetime: Optional[str]) -> Optional[int]:
        """
        Oblicza czas trwania wypowiedzi w sekundach

        Args:
            start_datetime: data i czas rozpoczęcia
            end_datetime: data i czas zakończenia

        Returns:
            Czas trwania w sekundach lub None
        """
        if not start_datetime or not end_datetime:
            return None

        try:
            start = datetime.fromisoformat(start_datetime.replace('T', ' ').replace('Z', ''))
            end = datetime.fromisoformat(end_datetime.replace('T', ' ').replace('Z', ''))
            duration = (end - start).total_seconds()
            return int(duration) if duration >= 0 else None
        except Exception:
            return None

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
        proceedings = self.api_client.get_proceedings(term)
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
            available_numbers = [p.get('number') for p in unique_proceedings]
            logger.info(f"Dostępne posiedzenia: {available_numbers}")
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

    def scrape_proceeding_date(self, term: int, proceeding_id: int, date: str, **options) -> bool:
        """
        Scrapuje konkretny dzień posiedzenia

        Args:
            term: numer kadencji
            proceeding_id: ID posiedzenia
            date: data w formacie YYYY-MM-DD

        Returns:
            True jeśli sukces
        """
        logger.info(f"Scrapowanie dnia {date} posiedzenia {proceeding_id} kadencji {term}")

        try:
            # Sprawdź czy data nie jest w przyszłości
            if self._is_date_in_future(date):
                logger.warning(f"Data {date} jest w przyszłości")
                return False

            # Pobierz info o posiedzeniu
            proceeding_info = self.api_client.get_proceeding_info(term, proceeding_id)
            if not proceeding_info:
                proceeding_info = {'number': proceeding_id, 'dates': [date]}

            # Przeładuj dane posłów
            self._load_mp_data(term)

            # Przetwarzaj dzień
            fetch_full_statements = options.get('fetch_full_statements', True)
            self._process_proceeding_day(term, proceeding_id, date, proceeding_info, fetch_full_statements)

            return True

        except Exception as e:
            logger.error(f"Błąd scrapowania dnia {date}: {e}")
            return False

    def get_term_proceedings_summary(self, term: int) -> Optional[List[Dict]]:
        """
        Pobiera podsumowanie posiedzeń dla kadencji

        Args:
            term: numer kadencji

        Returns:
            Lista z podstawowymi informacjami o posiedzeniach
        """
        proceedings = self.api_client.get_proceedings(term)
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

    def _log_final_stats(self):
        """Loguje końcowe statystyki"""
        logger.info("=== STATYSTYKI KOŃCOWE ===")
        logger.info(f"Przetworzone posiedzenia: {self.stats['proceedings_processed']}")
        logger.info(f"Pominięte przyszłe posiedzenia: {self.stats['future_proceedings_skipped']}")
        logger.info(f"Pominięte posiedzenia (cache): {self.stats['proceedings_skipped_cache']}")
        logger.info(f"Pominięte transkrypty (cache): {self.stats['transcripts_skipped_cache']}")
        logger.info(f"Przetworzone wypowiedzi: {self.stats['statements_processed']}")
        logger.info(f"Wypowiedzi z pełną treścią: {self.stats['statements_with_full_content']}")
        logger.info(f"Zidentyfikowani mówcy: {self.stats['speakers_identified']}")
        logger.info(f"Wzbogacenia danymi posłów: {self.stats['mp_data_enrichments']}")
        logger.info(f"Błędy: {self.stats['errors']}")
        logger.info("=========================")

    # === Metody obsługi cache ===

    def clear_cache(self, cache_type: str = "all"):
        """Czyści cache scrapera"""
        if self.cache_manager:
            if hasattr(self.cache_manager, 'clear'):
                self.cache_manager.clear()
            logger.info(f"Wyczyszczono cache: {cache_type}")
        else:
            logger.warning("Cache manager nie jest dostępny")

    def cleanup_cache(self):
        """Czyści stare wpisy z cache"""
        if self.cache_manager and hasattr(self.cache_manager, 'cleanup_expired'):
            self.cache_manager.cleanup_expired()
        else:
            logger.warning("Cache cleanup nie jest dostępny")

    def get_cache_stats(self) -> Dict:
        """Zwraca statystyki cache"""
        if self.cache_manager and hasattr(self.cache_manager, 'get_stats'):
            return self.cache_manager.get_stats()
        else:
            logger.warning("Cache stats nie są dostępne")
            return {
                'memory_cache': {'entries': 0, 'size_mb': 0},
                'file_cache': {'entries': 0, 'size_mb': 0}
            }

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
