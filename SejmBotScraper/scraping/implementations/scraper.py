"""
Naprawiona implementacja scrapera - SKUPIONA NA TREŚCI WYPOWIEDZI
Fixes:
1. Poprawne obsługiwanie parametrów konstruktora
2. Skupienie na pobieraniu treści wypowiedzi
3. Lepsze error handling
4. Uproszczenie logiki
"""

import logging
import time
from datetime import datetime, date
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)


class SejmScraper:
    """NAPRAWIONA implementacja scrapera - focus na treść wypowiedzi"""

    def __init__(self, api_client=None, cache_manager=None, config: Optional[Dict] = None):
        """
        Inicjalizuje scraper

        Args:
            api_client: klient API (wymagany)
            cache_manager: manager cache (opcjonalny)
            config: konfiguracja scrapera (opcjonalna)
        """
        self.config = config or {}
        self.api_client = api_client
        self.cache_manager = cache_manager

        # Sprawdź czy API client jest dostępny
        if not self.api_client:
            raise ValueError("API client jest wymagany")

        # Ustawienia scrapowania z fokusem na treść
        self.force_refresh = self.config.get('force_refresh', False)
        self.fetch_content_by_default = self.config.get('fetch_content', True)

        # Cache dla danych MP
        self.mp_data_cache = {}

        # Statystyki - FOCUS NA TREŚCI
        self.stats = {
            'proceedings_processed': 0,
            'statements_processed': 0,
            'statements_with_full_content': 0,  # KLUCZOWA METRYKA
            'content_fetch_attempts': 0,
            'content_fetch_successes': 0,
            'skipped_no_content': 0,
            'skipped_due_to_limit': 0,
            'speakers_identified': 0,
            'mp_data_enrichments': 0,
            'errors': 0,
            'future_proceedings_skipped': 0,
        }

        # Inicjalizuj file manager jeśli dostępny
        self.file_manager = None
        try:
            from ...storage.file_manager import FileManagerInterface
            storage_config = self.config.get('storage', {})
            base_dir = storage_config.get('base_directory', 'data')

            # FIX: Przekazuj string zamiast dict
            if isinstance(base_dir, dict):
                base_dir = base_dir.get('path', 'data')

            self.file_manager = FileManagerInterface(str(base_dir))
            logger.debug("File manager zainicjalizowany")
        except ImportError as e:
            logger.warning(f"File manager niedostępny: {e}")
        except Exception as e:
            logger.warning(f"Błąd inicjalizacji file managera: {e}")

        logger.info("SejmScraper implementation zainicjalizowana - focus na treści")

    def _is_date_in_future(self, date_str: str) -> bool:
        """Sprawdza czy data jest w przyszłości"""
        try:
            proceeding_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            return proceeding_date > date.today()
        except ValueError:
            logger.warning(f"Nieprawidłowy format daty: {date_str}")
            return False

    def _should_skip_future_proceeding(self, proceeding_dates: List[str]) -> bool:
        """Sprawdza czy posiedzenie jest całkowicie w przyszłości"""
        if not proceeding_dates:
            return False
        return all(self._is_date_in_future(d) for d in proceeding_dates)

    def _load_mp_data(self, term: int) -> Dict:
        """Ładuje dane posłów dla kadencji"""
        if term in self.mp_data_cache:
            return self.mp_data_cache[term]

        logger.info(f"Ładowanie danych posłów dla kadencji {term}")

        try:
            mps = self.api_client.get_mps(term)
            if not mps:
                logger.warning(f"Nie udało się pobrać listy posłów dla kadencji {term}")
                self.mp_data_cache[term] = {}
                return {}

            mp_dict = {}
            for mp in mps:
                first_name = mp.get('firstName', '').strip()
                last_name = mp.get('lastName', '').strip()
                full_name = f"{first_name} {last_name}".strip()

                if full_name:
                    mp_dict[full_name] = mp
                    mp_dict[f"{last_name} {first_name}"] = mp
                    mp_dict[last_name] = mp

            self.mp_data_cache[term] = mp_dict
            logger.info(f"Załadowano dane {len(mps)} posłów dla kadencji {term}")
            return mp_dict

        except Exception as e:
            logger.error(f"Błąd ładowania danych posłów dla kadencji {term}: {e}")
            self.mp_data_cache[term] = {}
            return {}

    def _enrich_statements_with_mp_data(self, statements: List[Dict], term: int) -> List[Dict]:
        """Wzbogaca wypowiedzi o dane posłów"""
        mp_data = self._load_mp_data(term)
        enriched_statements = []
        speakers_found = set()

        for statement in statements:
            enriched_statement = statement.copy()
            speaker_name = statement.get('speaker', {}).get('name', '').strip()

            if speaker_name and speaker_name in mp_data:
                mp_info = mp_data[speaker_name]
                enriched_statement['speaker']['mp_data'] = {
                    'id': mp_info.get('id'),
                    'club': mp_info.get('club', ''),
                    'districtName': mp_info.get('districtName', ''),
                    'districtNum': mp_info.get('districtNum'),
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

        self.stats['speakers_identified'] += len(speakers_found)
        logger.debug(f"Wzbogacono {len(speakers_found)} unikalnych mówców danymi posłów")

        return enriched_statements

    def _fetch_statement_content(self, term: int, proceeding_id: int, date: str, statement_num: int) -> Optional[Dict]:
        """
        KLUCZOWA METODA - pobiera treść wypowiedzi

        Returns:
            Dict z treścią lub None jeśli nie udało się pobrać
        """
        self.stats['content_fetch_attempts'] += 1

        if statement_num is None:
            logger.debug(f"Brak numeru wypowiedzi")
            return None

        try:
            logger.debug(f"Pobieranie treści wypowiedzi {statement_num}")

            # Pobierz HTML
            html_content = self.api_client.get_statement_html(term, proceeding_id, date, statement_num)

            if not html_content or len(html_content.strip()) < 50:
                logger.debug(f"Brak lub za mało HTML dla wypowiedzi {statement_num}")
                return None

            # Pobierz czysty tekst
            text_content = None
            if hasattr(self.api_client, 'get_statement_text'):
                text_content = self.api_client.get_statement_text(term, proceeding_id, date, statement_num)

            # Fallback - wyczyść HTML do tekstu
            if not text_content:
                text_content = self._clean_html_to_text(html_content)

            if text_content and len(text_content.strip()) > 20:
                logger.debug(f"✓ Pobrano treść: HTML {len(html_content)} znaków, tekst {len(text_content)} znaków")
                self.stats['content_fetch_successes'] += 1

                return {
                    'html_content': html_content,
                    'text_content': text_content.strip(),
                    'content_length': len(text_content.strip()),
                    'has_content': True,
                    'source': 'api_success',
                    'fetched_at': datetime.now().isoformat()
                }
            else:
                logger.debug(f"Tekst za krótki po oczyszczeniu")
                return None

        except Exception as e:
            logger.debug(f"Błąd pobierania wypowiedzi {statement_num}: {e}")
            return None

    def _clean_html_to_text(self, html_content: str) -> str:
        """Czyści HTML do tekstu - fallback method"""
        if not html_content:
            return ""

        import re

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
            # Fallback - usuń tylko tagi
            return re.sub(r'<[^>]+>', ' ', html_content).strip()

    def _enrich_statements_with_content(self, statements: List[Dict], term: int,
                                        proceeding_id: int, date: str) -> List[Dict]:
        """
        KLUCZOWA METODA - wzbogaca wypowiedzi o treść
        """
        logger.info(f"🎯 ROZPOCZYNAM POBIERANIE TREŚCI dla {len(statements)} wypowiedzi...")

        # Możemy ograniczyć liczbę wypowiedzi do testowania
        max_statements = self.config.get('max_statements_per_day', len(statements))
        statements_to_process = statements[:max_statements]

        if len(statements_to_process) < len(statements):
            logger.info(f"Ograniczenie do {max_statements} wypowiedzi z {len(statements)}")

        enriched_statements: List[Dict] = []
        successful_fetches = 0
        skipped_no_content = 0

        for i, statement in enumerate(statements_to_process, 1):
            statement_num = statement.get('num')

            # Wyświetl postęp co 10 wypowiedzi
            if i % 10 == 0:
                logger.info(f"Postęp: {i}/{len(statements_to_process)} ({successful_fetches} z treścią)")

            if statement_num is None:
                skipped_no_content += 1
                self.stats['skipped_no_content'] += 1
                logger.debug(f"✗ [{i}] Brak numeru wypowiedzi - pomijam")
                time.sleep(0.05)
                continue

            content_data = self._fetch_statement_content(term, proceeding_id, date, statement_num)

            if content_data:
                enriched_statement = statement.copy()
                enriched_statement['content'] = content_data
                successful_fetches += 1
                self.stats['statements_with_full_content'] += 1

                # Pokaż fragment treści w debug
                text_preview = content_data.get('text_content', '')[:100].replace('\n', ' ')
                logger.debug(f"✓ [{i}] Treść [{content_data.get('content_length', 0)} zn]: {text_preview}...")

                enriched_statements.append(enriched_statement)
            else:
                skipped_no_content += 1
                self.stats['skipped_no_content'] += 1
                logger.debug(f"✗ [{i}] Brak treści dla wypowiedzi {statement_num} - pomijam")

            # Małe opóźnienie między pobieraniami
            time.sleep(0.05)

        # Jeśli ograniczyliśmy liczbę wypowiedzi, zlicz je jako pominięte (nie zapisujemy ich jako metadane)
        skipped_due_to_limit = 0
        if len(statements) > max_statements:
            skipped_due_to_limit = len(statements) - max_statements
            self.stats['skipped_due_to_limit'] += skipped_due_to_limit
            logger.debug(f"Pominięto {skipped_due_to_limit} wypowiedzi z powodu limitu")

        # Podsumowanie z fokusem na treści
        logger.info(f"🎯 POBRANO TREŚĆ dla {successful_fetches}/{len(statements_to_process)} wypowiedzi")
        success_rate = (successful_fetches / len(statements_to_process)) * 100 if statements_to_process else 0
        logger.info(f"📊 Wskaźnik sukcesu treści: {success_rate:.1f}%")

        return enriched_statements

    def _calculate_duration(self, start_datetime: Optional[str], end_datetime: Optional[str]) -> Optional[int]:
        """Oblicza czas trwania wypowiedzi w sekundach"""
        if not start_datetime or not end_datetime:
            return None

        try:
            start = datetime.fromisoformat(start_datetime.replace('T', ' ').replace('Z', ''))
            end = datetime.fromisoformat(end_datetime.replace('T', ' ').replace('Z', ''))
            duration = (end - start).total_seconds()
            return int(duration) if duration >= 0 else None
        except Exception:
            return None

    def scrape_term(self, term: int = 10, **options) -> Dict:
        """
        GŁÓWNA METODA - scrapuje kadencję Z FOKUSEM NA TREŚCI WYPOWIEDZI
        """
        logger.info(f"=== ROZPOCZYNANIE SCRAPOWANIA KADENCJI {term} - FOCUS: TREŚĆ WYPOWIEDZI ===")

        # Pobierz opcje
        fetch_full_statements = options.get('fetch_full_statements', self.fetch_content_by_default)
        force_refresh = options.get('force_refresh', self.force_refresh)
        max_proceedings = options.get('max_proceedings', None)

        # Resetuj statystyki
        self.stats = {key: 0 for key in self.stats.keys()}
        self.force_refresh = force_refresh

        if force_refresh:
            logger.info("🔄 WYMUSZONE ODŚWIEŻENIE - wszystkie dane zostaną pobrane ponownie")

        if not fetch_full_statements:
            logger.warning("⚠️ UWAGA: Wyłączono pobieranie treści wypowiedzi - tylko metadane")
        else:
            logger.info("🎯 GŁÓWNY CEL: Pobieranie pełnej treści wypowiedzi")

        try:
            # Pobierz informacje o kadencji
            logger.info(f"Pobieranie informacji o kadencji {term}...")
            term_info = self.api_client.get_term_info(term) if hasattr(self.api_client, 'get_term_info') else None
            if term_info:
                logger.info(f"Kadencja {term}: {term_info.get('from', '')} - {term_info.get('to', 'obecna')}")

            # Pobierz listę posiedzeń
            logger.info(f"Pobieranie listy posiedzeń kadencji {term}...")
            proceedings = self.api_client.get_proceedings(term)

            if not proceedings:
                logger.error("Nie udało się pobrać listy posiedzeń")
                self.stats['errors'] += 1
                return self.stats

            logger.info(f"✓ Znaleziono {len(proceedings)} posiedzeń")

            # Filtruj unikalne posiedzenia
            unique_proceedings = self._filter_unique_proceedings(proceedings)
            logger.info(f"Po filtrowaniu: {len(unique_proceedings)} unikalnych posiedzeń")

            # Ograniczenie dla testów
            if max_proceedings:
                unique_proceedings = unique_proceedings[:max_proceedings]
                logger.info(f"🔧 Ograniczenie do {max_proceedings} posiedzeń dla testów")

            # Preładuj dane posłów
            logger.info("Ładowanie danych posłów...")
            self._load_mp_data(term)

            # Przetwarzaj posiedzenia
            logger.info("🎯 ROZPOCZYNANIE PRZETWARZANIA POSIEDZEŃ Z FOKUSEM NA TREŚCI...")

            for i, proceeding in enumerate(unique_proceedings, 1):
                try:
                    proceeding_number = proceeding.get('number')
                    logger.info(f"[{i}/{len(unique_proceedings)}] 🎯 Posiedzenie {proceeding_number}")

                    # Sprawdź czy nie jest w przyszłości
                    proceeding_dates = proceeding.get('dates', [])
                    if self._should_skip_future_proceeding(proceeding_dates):
                        logger.info(f"Pomijam przyszłe posiedzenie {proceeding_number}")
                        self.stats['future_proceedings_skipped'] += 1
                        continue

                    self._process_proceeding_with_content_focus(
                        term, proceeding, fetch_full_statements
                    )
                    self.stats['proceedings_processed'] += 1

                except Exception as e:
                    logger.error(f"Błąd przetwarzania posiedzenia {proceeding.get('number', '?')}: {e}")
                    self.stats['errors'] += 1

            self._log_final_stats()
            return self.stats

        except Exception as e:
            logger.error(f"Błąd scrapowania kadencji {term}: {e}")
            self.stats['errors'] += 1
            return self.stats

    def _filter_unique_proceedings(self, proceedings: List[Dict]) -> List[Dict]:
        """Filtruje duplikaty posiedzeń"""
        seen_numbers = set()
        unique_proceedings = []

        for proceeding in proceedings:
            number = proceeding.get('number')

            if number is None or number == 0:
                logger.debug(f"Pomijam posiedzenie z nieprawidłowym numerem: {number}")
                continue

            if number not in seen_numbers:
                seen_numbers.add(number)
                unique_proceedings.append(proceeding)

        # Sortuj według numeru
        unique_proceedings.sort(key=lambda x: x.get('number', 0))
        return unique_proceedings

    def _process_proceeding_with_content_focus(self, term: int, proceeding: Dict, fetch_full_statements: bool):
        """
        Przetwarza posiedzenie Z FOKUSEM NA TREŚCI
        """
        proceeding_number = proceeding.get('number')
        logger.debug(f"🎯 Przetwarzanie posiedzenia {proceeding_number} z fokusem na treści")

        # Pobierz szczegółowe informacje
        detailed_info = proceeding
        if hasattr(self.api_client, 'get_proceeding_info'):
            try:
                detailed_info = self.api_client.get_proceeding_info(term, proceeding_number) or proceeding
            except:
                pass

        # Zapisz informacje o posiedzeniu jeśli file manager dostępny
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

        if not past_dates:
            logger.info(f"Wszystkie daty posiedzenia {proceeding_number} są w przyszłości - pomijam")
            return

        # Ograniczenie dat dla testów
        max_dates = self.config.get('max_dates_per_proceeding', len(past_dates))
        dates_to_process = past_dates[:max_dates]

        if len(dates_to_process) < len(past_dates):
            logger.info(f"Ograniczenie do {max_dates} dni z {len(past_dates)} dla posiedzenia {proceeding_number}")

        # Przetwarzaj dni posiedzenia
        for date_str in dates_to_process:
            self._process_proceeding_day_with_content_focus(
                term, proceeding_number, date_str, detailed_info, fetch_full_statements
            )

    def _process_proceeding_day_with_content_focus(self, term: int, proceeding_id: int, date: str,
                                                   proceeding_info: Dict, fetch_full_statements: bool):
        """
        Przetwarza dzień posiedzenia Z FOKUSEM NA TREŚCI WYPOWIEDZI
        """
        logger.info(f"🎯 Przetwarzanie dnia {date} - FOCUS: treść wypowiedzi")

        try:
            # Pobierz listę wypowiedzi - używaj prawidłowej metody API
            statements_data = None

            # Spróbuj różnych metod API
            if hasattr(self.api_client, 'get_statements'):
                statements_data = self.api_client.get_statements(term, proceeding_id, date)
            elif hasattr(self.api_client, 'get_transcripts_list'):
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

            logger.info(f"🎯 Znaleziono {len(statements)} wypowiedzi dla {date} - POBIERANIE TREŚCI...")

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
                        'text_content': '',
                        'html_content': '',
                        'has_content': False,
                        'source': 'not_fetched'
                    },
                    "technical": {
                        "api_url": f"/sejm/term{term}/proceedings/{proceeding_id}/{date}/transcripts/{statement.get('num')}",
                        "original_data": statement
                    }
                }
                processed_statements.append(processed_statement)

            # Wzbogać wypowiedzi o dane posłów
            enriched_statements = self._enrich_statements_with_mp_data(processed_statements, term)

            # 🎯 KLUCZOWY KROK - POBIERZ TREŚĆ WYPOWIEDZI
            if fetch_full_statements:
                logger.info(f"🎯 ROZPOCZYNAM POBIERANIE TREŚCI WYPOWIEDZI dla {date}")
                enriched_statements = self._enrich_statements_with_content(
                    enriched_statements, term, proceeding_id, date
                )
            else:
                logger.info(f"⏭️ Pomijam pobieranie treści - tylko metadane")

            # Zapisz rezultaty
            if self.file_manager:
                try:
                    saved_path = self.file_manager.save_proceeding_transcripts(
                        term, proceeding_id, date, statements_data, proceeding_info, enriched_statements
                    )

                    if saved_path:
                        content_count = sum(1 for s in enriched_statements if s.get('content', {}).get('has_content'))
                        logger.info(
                            f"💾 Zapisano {len(enriched_statements)} wypowiedzi ({content_count} z treścią) do: {saved_path}")
                    else:
                        # Nie zapisano bo brak treści — zaktualizuj statystyki i log
                        logger.info(f"ℹ️ Plik nie został zapisany (brak wypowiedzi z treścią) dla {date}")
                        # Odejmij zliczone przetworzone wypowiedzi, bo nie zapisujemy metadanych bez treści
                        # (statements_processed będzie zwiększone dalej poza tym blokiem)
                except Exception as e:
                    logger.error(f"Błąd zapisywania wypowiedzi dla {date}: {e}")

            self.stats['statements_processed'] += len(enriched_statements)

        except Exception as e:
            if "404" in str(e) and self._is_date_in_future(date):
                logger.debug(f"Wypowiedzi dla przyszłej daty {date} nie są jeszcze dostępne (404)")
            else:
                logger.error(f"Błąd przetwarzania wypowiedzi dla {date}: {e}")
                self.stats['errors'] += 1

    def _log_final_stats(self):
        """Loguje końcowe statystyki Z FOKUSEM NA TREŚCI"""
        logger.info("=== STATYSTYKI KOŃCOWE - FOCUS: TREŚĆ WYPOWIEDZI ===")
        logger.info(f"Przetworzone posiedzenia: {self.stats['proceedings_processed']}")
        logger.info(f"Pominięte przyszłe posiedzenia: {self.stats['future_proceedings_skipped']}")
        logger.info(f"Przetworzone wypowiedzi: {self.stats['statements_processed']}")
        logger.info(f"🎯 WYPOWIEDZI Z TREŚCIĄ: {self.stats['statements_with_full_content']}")
        logger.info(f"Próby pobierania treści: {self.stats['content_fetch_attempts']}")
        logger.info(f"Udane pobierania treści: {self.stats['content_fetch_successes']}")
        logger.info(f"Zidentyfikowani mówcy: {self.stats['speakers_identified']}")
        logger.info(f"Wzbogacenia danymi posłów: {self.stats['mp_data_enrichments']}")
        logger.info(f"Błędy: {self.stats['errors']}")

        # Wskaźnik sukcesu treści - KLUCZOWA METRYKA
        if self.stats['content_fetch_attempts'] > 0:
            success_rate = (self.stats['content_fetch_successes'] / self.stats['content_fetch_attempts']) * 100
            logger.info(f"🎯 WSKAŹNIK SUKCESU TREŚCI: {success_rate:.1f}%")

            if success_rate >= 70:
                logger.info("🎉 DOSKONAŁY WYNIK - większość wypowiedzi ma treść!")
            elif success_rate >= 50:
                logger.info("✅ DOBRY WYNIK - połowa wypowiedzi ma treść")
            elif success_rate >= 30:
                logger.info("⚠️ ŚREDNI WYNIK - niektóre wypowiedzi mają treść")
            else:
                logger.info("❌ SŁABY WYNIK - mało wypowiedzi z treścią")

        logger.info("=" * 50)

    # Pozostałe metody dla kompatybilności
    def scrape_specific_proceeding(self, term: int, proceeding_number: int,
                                   fetch_full_statements: bool = True) -> bool:
        """Scrapuje konkretne posiedzenie Z FOKUSEM NA TREŚCI"""
        logger.info(f"🎯 SCRAPOWANIE POSIEDZENIA {proceeding_number} - FOCUS: treść wypowiedzi")

        try:
            # Pobierz informacje o posiedzeniu
            proceeding_info = None
            if hasattr(self.api_client, 'get_proceeding_info'):
                proceeding_info = self.api_client.get_proceeding_info(term, proceeding_number)

            if not proceeding_info:
                # Fallback - pobierz z listy posiedzeń
                proceedings = self.api_client.get_proceedings(term)
                if proceedings:
                    proceeding_info = next(
                        (p for p in proceedings if p.get('number') == proceeding_number),
                        None
                    )

            if not proceeding_info:
                logger.error(f"Nie można pobrać informacji o posiedzeniu {proceeding_number}")
                return False

            # Przetworz to posiedzenie
            self._process_proceeding_with_content_focus(term, proceeding_info, fetch_full_statements)

            # Sprawdź czy udało się pobrać jakieś treści
            if fetch_full_statements and self.stats['statements_with_full_content'] > 0:
                logger.info(f"🎉 SUKCES - pobrano treść {self.stats['statements_with_full_content']} wypowiedzi")
                return True
            elif not fetch_full_statements and self.stats['statements_processed'] > 0:
                logger.info(f"✅ SUKCES - pobrano metadane {self.stats['statements_processed']} wypowiedzi")
                return True
            else:
                logger.warning(f"⚠️ Nie pobrano żadnych wypowiedzi z treścią")
                return False

        except Exception as e:
            logger.error(f"Błąd scrapowania posiedzenia {proceeding_number}: {e}")
            return False

    def get_term_proceedings_summary(self, term: int) -> Optional[List[Dict]]:
        """Pobiera podsumowanie posiedzeń dla kadencji"""
        try:
            return self.api_client.get_proceedings(term)
        except Exception as e:
            logger.error(f"Błąd pobierania podsumowania: {e}")
            return None
