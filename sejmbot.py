#!/usr/bin/env python3
"""
SejmBot - Etap 1: Parser transkryptów Sejmu RP
Automatycznie pobiera i parsuje transkrypty z posiedzeń Sejmu.
"""

import hashlib
import json
import logging
import re
from dataclasses import dataclass, asdict
from datetime import datetime, date
from pathlib import Path
from typing import List, Dict, Optional, Set
from urllib.parse import urljoin

import requests
# Importy do parsowania różnych formatów
from bs4 import BeautifulSoup

try:
    import pdfplumber

    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False

try:
    import docx2txt

    DOCX_SUPPORT = True
except ImportError:
    DOCX_SUPPORT = False

# Opcjonalnie Selenium dla dynamicznych stron
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC

    SELENIUM_SUPPORT = True
except ImportError:
    SELENIUM_SUPPORT = False


@dataclass
class SejmSession:
    """Reprezentacja dnia posiedzenia Sejmu"""
    session_id: str
    meeting_number: int  # numer posiedzenia (np. 39)
    day_letter: str = ""  # litera dnia (a, b, c, d...)
    date: str = ""
    title: str = ""
    url: str = ""
    transcript_url: Optional[str] = None
    transcript_text: Optional[str] = None
    file_type: str = "pdf"  # prawie zawsze PDF dla stenogramów
    scraped_at: str = ""
    hash: str = ""
    kadencja: int = 10


class SejmBotConfig:
    """Konfiguracja bota oparta na rzeczywistej strukturze Sejmu"""

    def __init__(self):
        self.user_agent = "SejmBot/2.1 (+https://github.com/sejmbot) Mozilla/5.0 (compatible)"
        self.output_dir = Path("transkrypty")
        self.logs_dir = Path("logs")
        self.delay_between_requests = 3  # Zwiększone dla problematycznych serwerów
        self.max_retries = 4  # Zwiększone
        self.timeout = 45  # Zwiększone

        # Struktura URLi oparta na rzeczywistej architekturze Sejmu
        self.kadencje = {
            10: {
                'base_url': 'https://www.sejm.gov.pl/Sejm10.nsf/',
                'stenogramy_url': 'https://www.sejm.gov.pl/Sejm10.nsf/stenogramy.xsp',
                'pdf_server': 'https://orka2.sejm.gov.pl/StenoInter10.nsf/',
                'lata': list(range(2023, 2026))  # 13.11.2023 - nadal trwa
            },
            9: {
                'base_url': 'https://www.sejm.gov.pl/Sejm9.nsf/',
                'stenogramy_url': 'https://www.sejm.gov.pl/Sejm9.nsf/stenogramy.xsp',
                'pdf_server': 'https://orka2.sejm.gov.pl/StenoInter9.nsf/',
                'lata': list(range(2019, 2024))  # 12.11.2019 – 12.11.2023
            },
            8: {
                'base_url': 'https://www.sejm.gov.pl/Sejm8.nsf/',
                'stenogramy_url': 'https://www.sejm.gov.pl/Sejm8.nsf/stenogramy.xsp',
                'pdf_server': 'https://orka2.sejm.gov.pl/StenoInter8.nsf/',
                'lata': list(range(2015, 2020))  # 12.11.2015 – 11.11.2019
            },
            7: {
                'base_url': 'https://www.sejm.gov.pl/Sejm7.nsf/',
                'stenogramy_url': 'https://www.sejm.gov.pl/Sejm7.nsf/stenogramy.xsp',
                'pdf_server': 'https://orka2.sejm.gov.pl/StenoInter7.nsf/',
                'lata': list(range(2011, 2016))  # 08.11.2011 – 11.11.2015
            },
            6: {
                'base_url': 'https://www.sejm.gov.pl/Sejm6.nsf/',
                'stenogramy_url': 'https://www.sejm.gov.pl/Sejm6.nsf/stenogramy.xsp',
                'pdf_server': 'https://orka2.sejm.gov.pl/StenoInter6.nsf/',
                'lata': list(range(2007, 2012))  # 05.11.2007 – 07.11.2011
            }
        }

        # Skupiamy się na najnowszych kadencjach
        self.active_kadencje = [10, 9]
        self.current_year = datetime.now().year

        # Selektory CSS - rozszerzone o alternatywne
        self.pdf_selectors = [
            'a.pdf[href*="ksiazka.pdf"]',  # Główny selektor
            'a[href*="ksiazka.pdf"]',  # Bez klasy
            'a.pdf',  # Tylko klasa pdf
            'a[href*="StenoInter"]',  # Serwer stenogramów
            'a[href*=".pdf"][title*="stenograficzne"]'  # PDF z "stenograficzne" w title
        ]

        # Wzorce dat - rozszerzone
        self.date_patterns = [
            r'(\d{1,2})\s+(stycznia|lutego|marca|kwietnia|maja|czerwca|lipca|sierpnia|września|października|listopada|grudnia)\s+(\d{4})\s*\([^)]+\)',
            r'(\d{1,2})\s+(stycznia|lutego|marca|kwietnia|maja|czerwca|lipca|sierpnia|września|października|listopada|grudnia)\s+(\d{4})',
            r'(\d{1,2})\.(\d{1,2})\.(\d{4})',
            r'(\d{4})-(\d{1,2})-(\d{1,2})'
        ]

        # Polskie miesiące do konwersji
        self.polish_months = {
            'stycznia': '01', 'lutego': '02', 'marca': '03', 'kwietnia': '04',
            'maja': '05', 'czerwca': '06', 'lipca': '07', 'sierpnia': '08',
            'września': '09', 'października': '10', 'listopada': '11', 'grudnia': '12'
        }

        # Nagłówki HTTP - rozszerzone
        self.headers = {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'pl-PL,pl;q=0.9,en-US;q=0.7,en;q=0.3',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache'
        }

        # Wzorce do pomijania
        self.skip_patterns = [
            'fotogaleria', '[fotogaleria]', 'zapowiedź', '(zapowiedź)',
            'spotkanie marszałka', 'galeria zdjęć', 'zdjęcia z',
            'fotorelacja', 'relacja fotograficzna', 'video', 'film'
        ]

        self._setup_directories()
        self._setup_logging()

    def get_stenogramy_urls(self) -> List[str]:
        """Zwraca listę URLi do sprawdzenia - od najnowszych kadencji i lat"""
        urls = []

        # Sortuj kadencje od najnowszych (10, 9, 8...)
        for kadencja_nr in sorted(self.active_kadencje, reverse=True):
            kadencja = self.kadencje.get(kadencja_nr)
            if not kadencja:
                continue

            # Dla każdej kadencji, sprawdź tylko lata z tej kadencji, od najnowszych
            lata_kadencji = sorted(kadencja['lata'], reverse=True)

            for rok in lata_kadencji:
                url = f"{kadencja['stenogramy_url']}?rok={rok}"
                urls.append(url)

        return urls

    def _setup_directories(self):
        """Tworzy strukturę katalogów tylko dla rzeczywistych lat każdej kadencji"""
        self.output_dir.mkdir(exist_ok=True)
        self.logs_dir.mkdir(exist_ok=True)

        # Struktura: transkrypty/kadencja_X/YYYY/ - tylko dla rzeczywistych lat
        for kadencja_nr in self.active_kadencje:
            kadencja_info = self.kadencje.get(kadencja_nr)
            if not kadencja_info:
                continue

            kadencja_dir = self.output_dir / f"kadencja_{kadencja_nr}"
            kadencja_dir.mkdir(exist_ok=True)

            # Katalogi tylko dla lat tej konkretnej kadencji
            for rok in kadencja_info['lata']:
                (kadencja_dir / str(rok)).mkdir(exist_ok=True)

    def _setup_logging(self):
        """Konfiguruje logowanie"""
        log_file = self.logs_dir / f"sejmbot_{datetime.now().strftime('%Y%m%d')}.log"

        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file, encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)


class SejmBot:
    """Główna klasa bota do pobierania transkryptów"""

    def __init__(self, config: SejmBotConfig):
        self.config = config
        self.logger = config.logger
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': config.user_agent,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'pl,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        })

        # Śledzenie już pobranych sesji
        self.processed_sessions: Set[str] = set()
        self._load_processed_sessions()

        # Włącz debug logging jeśli potrzeba szczegółów
        if config.logger.level <= logging.INFO:
            config.logger.setLevel(logging.DEBUG)

    def run(self) -> int:
        """
        Główna pętla bota - pobiera posiedzenia Sejmu RP
        """
        print("🏛️  SejmBot v2.0 - Parser transkryptów posiedzeń Sejmu RP")
        print("=" * 60)
        print(f"🎯 Aktywne kadencje: {self.config.active_kadencje}")

        # Pokaż lata dla każdej kadencji
        for kad_nr in self.config.active_kadencje:
            kad_info = self.config.kadencje.get(kad_nr, {})
            lata = kad_info.get('lata', [])
            if lata:
                print(f"📅 Kadencja {kad_nr}: {min(lata)}-{max(lata)}")

        print("=" * 60)
        self.logger.info("🚀 Uruchomiono SejmBot v2.0")

        total_processed = 0

        # KROK 1: Cleanup uszkodzonych posiedzeń z poprzednich wersji
        try:
            broken_count = self.cleanup_broken_sessions()
            if broken_count > 0:
                print(f"🧹 Wyczyszczono {broken_count} uszkodzonych plików z poprzednich wersji")
        except Exception as e:
            self.logger.warning(f"Błąd podczas cleanup: {e}")

        # KROK 2: Znajdź wszystkie posiedzenia
        try:
            self.logger.info("🔍 Rozpoczynam wyszukiwanie posiedzeń...")
            meeting_links = self._find_session_links()
            total_found = len(meeting_links)

            print(f"📊 Znaleziono {total_found} dni posiedzeń do sprawdzenia")

            if total_found == 0:
                print("❌ Nie znaleziono żadnych posiedzeń do przetworzenia")
                print("\n💡 Możliwe przyczyny:")
                print("   • Problemy z połączeniem internetowym")
                print("   • Serwer Sejmu tymczasowo niedostępny")
                print("   • Zmiana struktury strony Sejmu")
                return 0

        except Exception as e:
            self.logger.error(f"❌ Błąd podczas wyszukiwania posiedzeń: {e}")
            print(f"\n❌ Błąd krytyczny podczas wyszukiwania: {e}")
            print("💡 Sprawdź połączenie internetowe i spróbuj ponownie")
            return 0

        # KROK 3: Przetwarzaj posiedzenia
        processed_in_run = 0
        skipped_already_processed = 0
        failed_processing = 0
        connection_errors = 0

        print(f"⚙️  Rozpoczynam przetwarzanie posiedzeń...")

        for i, meeting_data in enumerate(meeting_links, 1):
            try:
                session_id = meeting_data['id']

                # Sprawdź czy już przetworzona
                if session_id in self.processed_sessions:
                    skipped_already_processed += 1
                    self.logger.debug(f"⏭️  Posiedzenie {session_id} już przetworzone ({i}/{total_found})")
                    continue

                # Pokaż postęp
                print(f"📖 [{i}/{total_found}] Przetwarzam: {meeting_data['title'][:80]}...")

                # Przetwórz posiedzenie
                result = self._process_session(meeting_data)

                if result:
                    processed_in_run += 1
                    total_processed += 1
                    print(f"✅ [{i}/{total_found}] Sukces! Tekst: {len(result.transcript_text):,} znaków")

                    # Pokaż statystyki co 5 posiedzeń
                    if processed_in_run % 5 == 0:
                        success_rate = (processed_in_run / (processed_in_run + failed_processing)) * 100 if (
                                                                                                                    processed_in_run + failed_processing) > 0 else 0
                        print(f"📈 Postęp: {processed_in_run} przetworzonych, {success_rate:.1f}% sukces")
                else:
                    failed_processing += 1
                    # Sprawdź czy to błąd połączenia
                    if 'timeout' in str(meeting_data.get('last_error', '')).lower() or 'connection' in str(
                            meeting_data.get('last_error', '')).lower():
                        connection_errors += 1
                    print(f"❌ [{i}/{total_found}] Błąd przetwarzania")

            except KeyboardInterrupt:
                print(f"\n⏹️  Przerwano przez użytkownika na posiedzeniu {i}/{total_found}")
                break

            except Exception as e:
                failed_processing += 1
                self.logger.error(f"❌ Błąd przetwarzania posiedzenia {meeting_data.get('title', 'unknown')}: {e}")
                print(f"❌ [{i}/{total_found}] Błąd: {str(e)[:60]}...")
                continue

        # KROK 4: Podsumowanie
        print("\n" + "=" * 60)
        print("📊 PODSUMOWANIE DZIAŁANIA BOTA")
        print("=" * 60)
        print(f"🔍 Znalezionych dni posiedzeń: {total_found:3d}")
        print(f"⏭️  Już przetworzonych:        {skipped_already_processed:3d}")
        print(f"✅ Nowo przetworzonych:       {processed_in_run:3d}")
        print(f"❌ Nieudanych:                {failed_processing:3d}")
        if connection_errors > 0:
            print(f"🌐 Błędy połączenia:          {connection_errors:3d}")
        print(f"📁 Łącznie w bazie:           {len(self.processed_sessions):3d}")

        if processed_in_run > 0:
            success_rate = (processed_in_run / (processed_in_run + failed_processing)) * 100
            print(f"🎯 Wskaźnik sukcesu:          {success_rate:.1f}%")
            print(f"💾 Pliki zapisane w:          {self.config.output_dir}")
            print(f"📋 Logi dostępne w:           {self.config.logs_dir}")

        print("=" * 60)

        # Dodatkowe informacje dla użytkownika
        if processed_in_run > 0:
            print(f"\n🎉 Zakończono pomyślnie! Przetworzono {processed_in_run} nowych dni posiedzeń")
            print("💡 Kolejne uruchomienie pominie już przetworzone pliki")

            if failed_processing > 0:
                if connection_errors > 0:
                    print(
                        f"⚠️  {failed_processing} dni posiedzeń nie udało się przetworzyć (w tym {connection_errors} błędów połączenia)")
                    print("🌐 Spróbuj uruchomić ponownie - problemy z serwerem orka2.sejm.gov.pl są częste")
                else:
                    print(f"⚠️  {failed_processing} dni posiedzeń nie udało się przetworzyć - sprawdź logi")
        elif skipped_already_processed > 0:
            print("📋 Wszystkie posiedzenia już zostały przetworzone")
            print("🔄 Uruchom ponownie za kilka dni aby sprawdzić nowe posiedzenia")
        else:
            print("❌ Nie udało się przetworzyć żadnego posiedzenia - sprawdź logi")
            if connection_errors > 0:
                print("🌐 Główną przyczyną są problemy z połączeniem - spróbuj ponownie")

        self.logger.info(
            f"🏁 SejmBot zakończył pracę. Nowe: {processed_in_run}, "
            f"Pominięte: {skipped_already_processed}, Błędy: {failed_processing}"
        )

        return processed_in_run

    def _load_processed_sessions(self):
        """Ładuje listę już przetworzonych sesji"""
        processed_file = self.config.output_dir / "processed_sessions.json"
        if processed_file.exists():
            try:
                with open(processed_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.processed_sessions = set(data.get('sessions', []))
                self.logger.info(f"Załadowano {len(self.processed_sessions)} już przetworzonych sesji")
            except Exception as e:
                self.logger.warning(f"Nie można załadować listy przetworzonych sesji: {e}")

    def _save_processed_session(self, session_id: str):
        """Zapisuje ID sesji jako przetworzoną"""
        self.processed_sessions.add(session_id)
        processed_file = self.config.output_dir / "processed_sessions.json"

        try:
            data = {
                'sessions': list(self.processed_sessions),
                'last_updated': datetime.now().isoformat()
            }
            with open(processed_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.logger.error(f"Nie można zapisać listy przetworzonych sesji: {e}")

    def _make_request(self, url: str, **kwargs) -> Optional[requests.Response]:
        """Wykonuje zapytanie HTTP z retry, error handling i alternatywnymi serwerami"""

        # Sprawdź czy to problematyczny serwer orka2 i spróbuj alternatywne URLe
        original_url = url
        alternative_urls = []

        if 'orka2.sejm.gov.pl' in url:
            # Spróbuj HTTPS zamiast HTTP
            if url.startswith('http://'):
                alternative_urls.append(url.replace('http://', 'https://'))

            # Zwiększ timeout dla problematycznego serwera
            kwargs.setdefault('timeout', 60)
        else:
            kwargs.setdefault('timeout', self.config.timeout)

        urls_to_try = [original_url] + alternative_urls

        for url_to_try in urls_to_try:
            for attempt in range(self.config.max_retries):
                try:
                    time.sleep(self.config.delay_between_requests)

                    self.logger.debug(f"Próba {attempt + 1}/{self.config.max_retries}: {url_to_try}")

                    response = self.session.get(url_to_try, **kwargs)

                    if response.status_code == 200:
                        if url_to_try != original_url:
                            self.logger.info(f"✅ Sukces z alternatywnym URL: {url_to_try}")
                        return response
                    elif response.status_code == 403:
                        self.logger.warning(f"Dostęp zabroniony (403) dla URL: {url_to_try}")
                        break  # Nie próbuj ponownie dla 403
                    else:
                        self.logger.warning(f"HTTP {response.status_code} dla URL: {url_to_try}")

                except requests.exceptions.Timeout as e:
                    self.logger.warning(
                        f"Timeout (próba {attempt + 1}/{self.config.max_retries}) dla {url_to_try}: {e}")
                    if attempt < self.config.max_retries - 1:
                        wait_time = min(2 ** attempt, 10)  # Max 10 sekund
                        self.logger.info(f"Czekam {wait_time}s przed kolejną próbą...")
                        time.sleep(wait_time)

                except requests.RequestException as e:
                    self.logger.warning(f"Błąd zapytania (próba {attempt + 1}/{self.config.max_retries}): {e}")
                    if attempt < self.config.max_retries - 1:
                        time.sleep(2 ** attempt)  # exponential backoff

        self.logger.error(f"❌ Wszystkie próby nie powiodły się dla: {original_url}")
        return None

    def _extract_text_from_html(self, html_content: str) -> str:
        """Ekstraktuje tekst z HTML"""
        soup = BeautifulSoup(html_content, 'html.parser')

        # Usuwa zbędne elementy
        for element in soup(['script', 'style', 'nav', 'header', 'footer', 'aside']):
            element.decompose()

        # Szuka głównej treści oraz wzorców dla stron Sejmu
        content_selectors = [
            # Specjalne dla Sejmu
            'div[id*="stenogram"]',
            'div[class*="stenogram"]',
            'div[class*="transcript"]',
            'div[class*="protokol"]',
            'div[id*="protokol"]',
            '.stenogram-content',
            '.transcript-content',

            # Ogólne wzorce
            'main',
            'article',
            '.main-content',
            '.content',
            '#content',
            '.post-content',

            # Fallback - cała treść body bez nav/header/footer
            'body'
        ]

        text_content = ""
        for selector in content_selectors:
            elements = soup.select(selector)
            if elements:
                # Weź pierwszy znaleziony element
                element = elements[0]
                text_content = element.get_text(separator=' ', strip=True)
                if len(text_content) > 200:  # Sprawdź czy to sensowna treść
                    self.logger.debug(f"Użyto selektora: {selector}, tekst: {len(text_content)} znaków")
                    break

        # Jeśli nadal brak treści, weź cały tekst
        if not text_content or len(text_content) < 200:
            text_content = soup.get_text(separator=' ', strip=True)

        # Czyszczenie tekstu
        import re

        # Usuń nadmiarowe białe znaki
        text_content = re.sub(r'\s+', ' ', text_content)

        # Usuń typowe śmieci z stron gov.pl
        text_content = re.sub(r'(JavaScript.*?włącz|Cookie|Mapa strony|Kontakt)', '', text_content)

        # Usuń menu/nawigację
        text_content = re.sub(r'(Menu główne|Nawigacja|Przejdź do|Skip to)', '', text_content)

        text_content = text_content.strip()

        self.logger.debug(f"HTML -> tekst: {len(text_content)} znaków")
        return text_content

    def _extract_text_from_pdf_bytes(self, pdf_bytes: bytes) -> str:
        """Ekstraktuje tekst z PDF z bajtów z obsługą różnych problemów"""
        if not PDF_SUPPORT:
            self.logger.error("❌ Brak wsparcia dla PDF - zainstaluj: pip install pdfplumber")
            return ""

        if not pdf_bytes or len(pdf_bytes) < 100:
            self.logger.error("❌ PDF jest pusty lub uszkodzony")
            return ""

        try:
            import io

            # Sprawdź czy to rzeczywiście PDF
            if not pdf_bytes.startswith(b'%PDF-'):
                self.logger.error("❌ Plik nie jest prawidłowym PDF")
                return ""

            pdf_stream = io.BytesIO(pdf_bytes)
            text_parts = []

            with pdfplumber.open(pdf_stream) as pdf:
                self.logger.info(f"📄 PDF ma {len(pdf.pages)} stron")

                for page_num, page in enumerate(pdf.pages, 1):
                    try:
                        page_text = page.extract_text()
                        if page_text:
                            text_parts.append(page_text)

                        # Pokaż postęp dla dużych PDFów
                        if page_num % 50 == 0:
                            self.logger.info(f"📖 Przetworzono {page_num}/{len(pdf.pages)} stron")

                    except Exception as e:
                        self.logger.warning(f"⚠️  Błąd na stronie {page_num}: {e}")
                        continue

            full_text = '\n\n'.join(text_parts)
            cleaned_text = self._clean_extracted_text(full_text)

            self.logger.info(f"✅ Wyciągnięto {len(cleaned_text):,} znaków z PDF")
            return cleaned_text

        except Exception as e:
            self.logger.error(f"❌ Błąd parsowania PDF: {e}")
            return ""

    def _download_and_parse_file(self, url: str, file_type: str, session_id: str) -> tuple[str, bytes]:
        """
        Pobiera plik i zwraca zarówno tekst jak i oryginalne bajty
        USUNIĘTO OCR zgodnie z prośbą użytkownika
        """
        try:
            self.logger.info(f"📥 Pobieranie {file_type.upper()}: {url}")

            response = self._make_request(url)
            if not response:
                self.logger.error(f"❌ Nie udało się pobrać pliku: {url}")
                return "", b""

            # Pobierz oryginalne bajty
            file_bytes = response.content

            # Sprawdź rozmiar pliku
            file_size_mb = len(file_bytes) / (1024 * 1024)
            self.logger.info(f"📦 Rozmiar pliku: {file_size_mb:.2f} MB")

            # Sprawdź content-type
            content_type = response.headers.get('content-type', '').lower()
            self.logger.debug(f"Content-Type: {content_type}")

            if file_type == 'pdf':
                if 'application/pdf' not in content_type and not url.endswith('.pdf'):
                    self.logger.warning(f"⚠️  URL {url} może nie być PDFem (content-type: {content_type})")

                # Parsuj tekst z PDF
                text = self._extract_text_from_pdf_bytes(file_bytes)
                return text, file_bytes

            elif file_type == 'docx':
                text = self._extract_text_from_docx_bytes(file_bytes)
                return text, file_bytes

            else:  # HTML lub inne
                text = response.text
                return text, b""

        except Exception as e:
            self.logger.error(f"❌ Błąd pobierania/parsowania pliku {url}: {e}")
            return "", b""

    def _clean_extracted_text(self, text: str) -> str:
        """
        Czyści wyciągnięty tekst z PDF/HTML
        """
        if not text:
            return ""

        # Usuń nadmiarowe białe znaki
        text = re.sub(r'\s+', ' ', text)

        # Usuń typowe śmieci z dokumentów
        cleanup_patterns = [
            r'JavaScript.*?włącz',
            r'Cookie.*?polityka',
            r'Mapa strony',
            r'Menu główne',
            r'Nawigacja',
            r'Przejdź do',
            r'Skip to',
            r'Strona \d+ z \d+',  # Numery stron
            r'www\.sejm\.gov\.pl',
            r'© Kancelaria Sejmu',
        ]

        for pattern in cleanup_patterns:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE)

        # Normalizuj polskie znaki
        text = text.replace('\u00a0', ' ')  # non-breaking space
        text = text.replace('\u2013', '-')  # en dash
        text = text.replace('\u2014', '--')  # em dash
        text = text.replace('\u2019', "'")  # right single quotation mark
        text = text.replace('\u201c', '"')  # left double quotation mark
        text = text.replace('\u201d', '"')  # right double quotation mark

        # Końcowe czyszczenie
        text = text.strip()
        text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)  # Usuń nadmierne puste linie

        return text

    def _extract_text_from_docx_bytes(self, docx_bytes: bytes) -> str:
        """Ekstraktuje tekst z DOCX z bajtów"""
        if not DOCX_SUPPORT:
            self.logger.error("❌ Brak wsparcia dla DOCX - zainstaluj: pip install docx2txt")
            return ""

        try:
            import io
            import tempfile

            # docx2txt wymaga pliku na dysku
            with tempfile.NamedTemporaryFile(suffix='.docx', delete=False) as tmp_file:
                tmp_file.write(docx_bytes)
                tmp_file_path = tmp_file.name

            try:
                text = docx2txt.process(tmp_file_path)
                return self._clean_extracted_text(text) if text else ""
            finally:
                # Usuń plik tymczasowy
                try:
                    os.unlink(tmp_file_path)
                except:
                    pass

        except Exception as e:
            self.logger.error(f"❌ Błąd parsowania DOCX z bajtów: {e}")
            return ""

    def _validate_extracted_text(self, text: str, source_url: str) -> bool:
        """
        Waliduje czy wyciągnięty tekst jest sensowny stenogram Sejmu
        """
        if not text or len(text.strip()) < 500:  # Zwiększony próg
            self.logger.warning(f"⚠️  Tekst za krótki ({len(text)} znaków) dla {source_url}")
            return False

        # Sprawdź czy tekst zawiera polskie słowa charakterystyczne dla stenogramów
        polish_keywords = [
            'posiedzenie', 'marszałek', 'poseł', 'posłanka', 'sejm', 'głosowanie',
            'komisja', 'sprawozdanie', 'ustawa', 'interpelacja', 'punkt', 'porządku',
            'obrady', 'wicemarszałek', 'przewodniczący', 'sekretarz', 'protokół',
            'rada ministrów', 'rząd', 'minister', 'klub', 'koło', 'poselski'
        ]

        text_lower = text.lower()
        found_keywords = sum(1 for keyword in polish_keywords if keyword in text_lower)

        if found_keywords < 5:  # Zwiększony próg
            self.logger.warning(
                f"⚠️  Tekst może nie być stenogramem - znaleziono tylko {found_keywords} kluczowych słów")
            return False

        # Sprawdź czy nie jest to głównie śmieci/kod
        printable_ratio = sum(1 for c in text if c.isprintable() or c.isspace()) / len(text) if text else 0

        if printable_ratio < 0.9:  # Zwiększony próg jakości
            self.logger.warning(f"⚠️  Tekst zawiera dużo nieprintable znaków ({printable_ratio:.2%})")
            return False

        # Sprawdź czy tekst nie składa się głównie z pojedynczych liter/cyfr
        words = text.split()
        meaningful_words = sum(1 for word in words if len(word) > 2)
        meaningful_ratio = meaningful_words / len(words) if words else 0

        if meaningful_ratio < 0.7:
            self.logger.warning(f"⚠️  Tekst ma za mało sensownych słów ({meaningful_ratio:.2%})")
            return False

        # Sprawdź typowe błędy OCR/parsingu
        suspicious_patterns = [
            r'^[^a-ząćęłńóśźż]*$',  # Brak polskich liter w całym tekście
            r'^\d+\s*$',  # Tylko cyfry
            r'^[^\w\s]*$',  # Tylko znaki specjalne
        ]

        for pattern in suspicious_patterns:
            if re.match(pattern, text_lower):
                self.logger.warning(f"⚠️  Tekst pasuje do podejrzanego wzorca: {pattern}")
                return False

        self.logger.info(
            f"✅ Tekst przeszedł walidację: {len(text):,} znaków, {found_keywords} kluczowych słów, {meaningful_ratio:.1%} sensownych słów")
        return True

    def _extract_text_from_docx(self, file_path: Path) -> str:
        """Ekstraktuje tekst z DOCX"""
        if not DOCX_SUPPORT:
            self.logger.error("Brak wsparcia dla DOCX - zainstaluj docx2txt")
            return ""

        try:
            return docx2txt.process(str(file_path))
        except Exception as e:
            self.logger.error(f"Błąd parsowania DOCX {file_path}: {e}")
            return ""

    def _find_session_links(self) -> List[Dict[str, str]]:
        """
        Znajduje linki do posiedzeń wykorzystując strukturę URLi Sejmu z debugowaniem
        """
        sessions = []

        # Pobierz wszystkie URLe do sprawdzenia
        urls_to_check = self.config.get_stenogramy_urls()

        self.logger.info(f"🔍 Sprawdzam {len(urls_to_check)} stron stenogramów...")

        for stenogramy_url in urls_to_check:
            self.logger.info(f"📄 Analizuję: {stenogramy_url}")

            # Wyciągnij kadencję i rok z URL dla kontekstu
            kadencja_match = re.search(r'Sejm(\d+)\.nsf', stenogramy_url)
            rok_match = re.search(r'rok=(\d{4})', stenogramy_url)

            kadencja_nr = int(kadencja_match.group(1)) if kadencja_match else 0
            rok = int(rok_match.group(1)) if rok_match else datetime.now().year

            # Pobierz stronę
            time.sleep(self.config.delay_between_requests)
            response = self._make_request(stenogramy_url)

            if not response:
                self.logger.warning(f"❌ Nie udało się pobrać: {stenogramy_url}")
                continue

            try:
                soup = BeautifulSoup(response.text, 'html.parser')

                # DEBUGOWANIE: sprawdź co faktycznie znajdziemy na stronie
                self._debug_page_content(soup, stenogramy_url)

                page_sessions = self._extract_sessions_from_page(soup, stenogramy_url, kadencja_nr, rok)

                sessions.extend(page_sessions)
                self.logger.info(
                    f"✅ Znaleziono {len(page_sessions)} sesji na stronie (kadencja {kadencja_nr}, rok {rok})")

            except Exception as e:
                self.logger.error(f"❌ Błąd parsowania strony {stenogramy_url}: {e}")
                import traceback
                self.logger.debug(f"Szczegóły błędu: {traceback.format_exc()}")
                continue

        # Usuń duplikaty na podstawie URL
        unique_sessions = {}
        for session in sessions:
            unique_sessions[session['url']] = session

        sessions = list(unique_sessions.values())

        # Sortuj według daty i kadencji (najnowsze pierwsze)
        sessions.sort(key=lambda x: (x.get('kadencja', 0), x.get('date', ''), x.get('meeting_number', 0)), reverse=True)

        # DEBUGOWANIE: pokaż co znaleźliśmy
        self._debug_found_sessions(sessions)

        self.logger.info(f"🎯 Znaleziono łącznie {len(sessions)} unikalnych sesji")
        return sessions

    def _extract_sessions_from_page(self, soup: BeautifulSoup, base_url: str, kadencja_nr: int, rok: int) -> List[
        Dict[str, str]]:
        """
        Wyciąga posiedzenia z pojedynczej strony stenogramów
        POPRAWIONA wersja - używa rzeczywistych selektorów z logów
        """
        posiedzenia = []

        # POPRAWKA: Szukaj wszystkich linków PDF z klasą 'pdf' (nie tylko ksiazka.pdf)
        pdf_links = soup.select('a.pdf[href]')

        self.logger.debug(f"Znaleziono {len(pdf_links)} linków PDF z klasą 'pdf'")

        for link in pdf_links:
            try:
                href = link.get('href', '')
                text = link.get_text(strip=True)
                title = link.get('title', '')

                if not href or not text:
                    continue

                # Sprawdź czy link zawiera datę (oznacza stenogram)
                if not self._text_contains_date(text):
                    self.logger.debug(f"Pomijam link bez daty: {text[:50]}")
                    continue

                # Sprawdź czy to stenogram (nie fotogaleria, zapowiedź itp.)
                if self._should_skip_link(text.lower()):
                    self.logger.debug(f"Pomijam link (skip pattern): {text[:50]}")
                    continue

                # Sprawdź tytuł linku - powinien zawierać "stenograficzne"
                if title and 'stenograficzne' not in title.lower():
                    self.logger.debug(f"Pomijam - brak 'stenograficzne' w title: {title[:50]}")
                    continue

                posiedzenie_data = self._parse_posiedzenie_link(link, base_url, kadencja_nr, rok)
                if posiedzenie_data:
                    posiedzenia.append(posiedzenie_data)
                    self.logger.debug(f"✅ Dodano posiedzenie: {posiedzenie_data['title'][:60]}")

            except Exception as e:
                self.logger.warning(f"Błąd parsowania linku PDF: {e}")
                continue

        # Sortuj według daty - najnowsze pierwsze
        posiedzenia.sort(
            key=lambda x: (x.get('date', ''), x.get('meeting_number', 0)),
            reverse=True
        )

        self.logger.info(f"🎯 Wyciągnięto {len(posiedzenia)} posiedzeń z {len(pdf_links)} linków PDF")
        return posiedzenia

    def _text_contains_date(self, text: str) -> bool:
        """Sprawdza czy tekst zawiera polską datę"""
        import re

        # Wzorzec polskich dat z dniami tygodnia
        date_pattern = r'\d{1,2}\s+(stycznia|lutego|marca|kwietnia|maja|czerwca|lipca|sierpnia|września|października|listopada|grudnia)\s+\d{4}\s*\([^)]+\)'

        return bool(re.search(date_pattern, text.lower()))

    def _parse_posiedzenie_link(self, link, base_url: str, kadencja_nr: int, rok: int) -> Optional[Dict[str, str]]:
        """
        Parsuje pojedynczy link do posiedzenia Sejmu
        POPRAWIONA wersja dla rzeczywistych URLi z logów
        """
        href = link.get('href', '')
        text = link.get_text(strip=True)
        title = link.get('title', '')

        if not href or not text:
            return None

        # Utwórz pełny URL
        if href.startswith('http'):
            full_url = href
        else:
            full_url = urljoin(base_url, href)

        # POPRAWKA: Wyciągnij numer posiedzenia z rzeczywistych URLi
        # Przykład z logów: https://orka2.sejm.gov.pl/StenoInter10.nsf/0/BFDA6C1F1332329...
        meeting_number = self._extract_meeting_number_from_url_new(href, text)

        # POPRAWKA: Wyciągnij literę dnia z tekstu lub URL
        day_letter = self._extract_day_letter_from_text(text)

        # Parsuj datę z tekstu linku (np. "18 grudnia 2024 (środa)")
        meeting_date = self._extract_date_from_text(text)
        if not meeting_date:
            meeting_date = f"{rok}-01-01"  # Fallback

        # Stwórz unikalny ID na podstawie kadencji, daty i URL hash
        url_hash = hashlib.md5(full_url.encode()).hexdigest()[:8]
        session_id = f"{kadencja_nr}_{meeting_date.replace('-', '')}_{url_hash}"

        # Przygotuj tytuł posiedzenia
        if meeting_number > 0:
            if day_letter:
                session_title = f"Posiedzenie nr {meeting_number} ({day_letter}) - {text}"
            else:
                session_title = f"Posiedzenie nr {meeting_number} - {text}"
        else:
            session_title = f"Sesja {meeting_date} - {text}"

        return {
            'id': session_id,
            'meeting_number': meeting_number,
            'day_letter': day_letter,
            'title': session_title,
            'url': full_url,
            'date': meeting_date,
            'kadencja': kadencja_nr,
            'rok': rok,
            'original_text': text,
            'pdf_direct': True  # Zawsze PDF dla stenogramów
        }

    def _extract_meeting_number_from_url_new(self, url: str, text: str) -> int:
        """
        Wyciąga numer posiedzenia z rzeczywistych URLi Sejmu
        Przykład URL z logów: https://orka2.sejm.gov.pl/StenoInter10.nsf/0/BFDA6C1F1332329...
        """
        import re

        # METODA 1: Spróbuj wyciągnąć z tekstu linku
        # Tekst z logów: "18 grudnia 2024 (środa)" - brak numeru posiedzenia
        # Szukaj wzorców w tekście
        text_patterns = [
            r'posiedzenie\s+nr\s*(\d+)',
            r'posiedzenie\s+(\d+)',
            r'sesja\s+(\d+)',
            r'nr\s*(\d+)',
            r'(\d+)\s*posiedzenie'
        ]

        text_lower = text.lower()
        for pattern in text_patterns:
            match = re.search(pattern, text_lower)
            if match:
                try:
                    number = int(match.group(1))
                    self.logger.debug(f"Numer posiedzenia z tekstu: {number}")
                    return number
                except (ValueError, IndexError):
                    continue

        # METODA 2: Analiza struktury URL
        # Przykład: StenoInter10.nsf/0/HASH/%24File/nazwa_pliku.pdf
        url_patterns = [
            r'/(\d+)_[a-z]_[^/]*\.pdf$',  # XXX_a_nazwa.pdf
            r'/(\d+)_[^/]*\.pdf$',  # XXX_nazwa.pdf
            r'_(\d+)_[^/]*\.pdf$',  # prefix_XXX_nazwa.pdf
            r'/(\d+)[^/]*\.pdf$',  # XXXnazwa.pdf
        ]

        for pattern in url_patterns:
            match = re.search(pattern, url.lower())
            if match:
                try:
                    number = int(match.group(1))
                    # Sprawdź czy to sensowny numer posiedzenia (1-200)
                    if 1 <= number <= 200:
                        self.logger.debug(f"Numer posiedzenia z URL: {number}")
                        return number
                except (ValueError, IndexError):
                    continue

        # METODA 3: Spróbuj odgadnąć na podstawie daty i kadencji
        # Sesje Sejmu zazwyczaj mają kilkadziesiąt posiedzeń rocznie
        date_str = self._extract_date_from_text(text)
        if date_str:
            try:
                from datetime import datetime
                date_obj = datetime.strptime(date_str, '%Y-%m-%d')

                # Przybliżona heurystyka na podstawie dat
                if date_obj.year >= 2024:
                    # Najnowsza kadencja - może być 1-100+
                    estimated = min((date_obj.month - 1) * 4 + 1, 100)
                    self.logger.debug(f"Szacowany numer posiedzenia na podstawie daty: {estimated}")
                    return estimated

            except ValueError:
                pass

        # FALLBACK: Jeśli nic nie działa, zwróć 1
        self.logger.warning(f"Nie udało się wyciągnąć numeru posiedzenia z URL/tekstu: {url[:60]}")
        return 1

    def _extract_day_letter_from_text(self, text: str) -> str:
        """
        Wyciąga literę dnia z tekstu linku
        Tekst z logów: "18 grudnia 2024 (środa)" - dzień tygodnia można zamienić na literę
        """
        import re

        # METODA 1: Bezpośrednia litera w tekście (rzadko)
        direct_letter_match = re.search(r'\b([a-z])\b', text.lower())
        if direct_letter_match:
            letter = direct_letter_match.group(1)
            if letter in 'abcdefgh':  # Typowe litery dla dni posiedzeń
                return letter

        # METODA 2: Na podstawie dnia tygodnia
        day_mapping = {
            'poniedziałek': 'a',
            'wtorek': 'b',
            'środa': 'c',
            'czwartek': 'd',
            'piątek': 'e',
            'sobota': 'f',
            'niedziela': 'g'
        }

        text_lower = text.lower()
        for day_name, letter in day_mapping.items():
            if day_name in text_lower:
                self.logger.debug(f"Dzień tygodnia '{day_name}' -> litera '{letter}'")
                return letter

        # METODA 3: Na podstawie wzorców w URL (jeśli przyszły w tekście)
        url_pattern_match = re.search(r'_([a-h])_', text)
        if url_pattern_match:
            return url_pattern_match.group(1)

        # METODA 4: Heurystyka na podstawie kolejności w tygodniu
        # Jeśli mamy datę, sprawdź dzień tygodnia
        date_str = self._extract_date_from_text(text)
        if date_str:
            try:
                from datetime import datetime
                date_obj = datetime.strptime(date_str, '%Y-%m-%d')
                weekday = date_obj.weekday()  # 0=poniedziałek, 6=niedziela

                # Mapuj dzień tygodnia na literę
                weekday_letters = ['a', 'b', 'c', 'd', 'e', 'f', 'g']
                if 0 <= weekday < len(weekday_letters):
                    letter = weekday_letters[weekday]
                    self.logger.debug(f"Dzień tygodnia {weekday} -> litera '{letter}'")
                    return letter

            except ValueError:
                pass

        # Brak litery dnia
        return ""

    def _parse_session_link(self, link, base_url: str, kadencja_nr: int, rok: int) -> Optional[Dict[str, str]]:
        """
        Parsuje pojedynczy link do sesji
        """
        href = link.get('href', '')
        text = link.get_text(strip=True)
        title_attr = link.get('title', '')

        if not href or not text:
            return None

        # Sprawdź czy to nie jest link do pominięcia
        if self._should_skip_link(text.lower()):
            return None

        # Utwórz pełny URL
        if href.startswith('http'):
            full_url = href
        else:
            full_url = urljoin(base_url, href)

        # Wyciągnij numer posiedzenia
        session_number = self._extract_session_number_from_text(text)
        if session_number == 0:
            # Spróbuj wyciągnąć z URL
            session_number = self._extract_session_number_from_url(href)

        # Wyciągnij datę
        session_date = self._extract_date_from_text(text)
        if not session_date:
            session_date = f"{rok}-01-01"  # Fallback na rok z URL

        # Stwórz unikalny ID
        session_id = hashlib.md5(f"{kadencja_nr}_{session_number}_{full_url}".encode()).hexdigest()[:12]

        # Przygotuj tytuł sesji
        if session_number > 0:
            session_title = f"Kadencja {kadencja_nr} - Posiedzenie nr {session_number} - {text}"
        else:
            session_title = f"Kadencja {kadencja_nr} - {text}"

        return {
            'id': session_id,
            'number': session_number,
            'title': session_title,
            'url': full_url,
            'date': session_date,
            'kadencja': kadencja_nr,
            'rok': rok,
            'original_text': text,
            'pdf_direct': href.endswith('.pdf')
        }

    def _should_skip_link(self, text_lower: str) -> bool:
        """Sprawdza czy link należy pominąć"""
        for pattern in self.config.skip_patterns:
            if pattern.lower() in text_lower:
                return True
        return False

    def _extract_session_number_from_text(self, text: str) -> int:
        """Wyciąga numer posiedzenia z tekstu"""
        # Wzorce dla numerów posiedzeń
        patterns = [
            r'posiedzenie\s+nr\s+(\d+)',
            r'posiedzenie\s+(\d+)',
            r'nr\s+(\d+)',
            r'(\d+)\s*\.\s*posiedzenie',
            r'sesja\s+(\d+)'
        ]

        text_lower = text.lower()

        for pattern in patterns:
            match = re.search(pattern, text_lower)
            if match:
                try:
                    return int(match.group(1))
                except (ValueError, IndexError):
                    continue

        return 0

    def _extract_session_number_from_url(self, url: str) -> int:
        """Wyciąga numer posiedzenia z URL"""
        # Wzorce w URL - np. w nazwach plików PDF
        patterns = [
            r'(\d+)_a_ksiazka',  # 25_a_ksiazka_bis.pdf
            r'ksiazka_(\d+)',
            r'stenogram_(\d+)',
            r'posiedzenie_(\d+)',
            r'/(\d+)/'
        ]

        for pattern in patterns:
            match = re.search(pattern, url.lower())
            if match:
                try:
                    return int(match.group(1))
                except (ValueError, IndexError):
                    continue

        return 0

    def _extract_date_from_text(self, text: str) -> Optional[str]:
        """
        Wyciąga datę z tekstu używając wzorców polskich dat
        """
        import re

        # Rozszerzone wzorce dat
        date_patterns = [
            # "22 lipca 2025 (wtorek)" - główny wzorzec dla Sejmu
            r'(\d{1,2})\s+(stycznia|lutego|marca|kwietnia|maja|czerwca|lipca|sierpnia|września|października|listopada|grudnia)\s+(\d{4})\s*\([^)]+\)',
            # "22 lipca 2025"
            r'(\d{1,2})\s+(stycznia|lutego|marca|kwietnia|maja|czerwca|lipca|sierpnia|września|października|listopada|grudnia)\s+(\d{4})',
            # "22.07.2025"
            r'(\d{1,2})\.(\d{1,2})\.(\d{4})',
            # "2025-07-22"
            r'(\d{4})-(\d{1,2})-(\d{1,2})'
        ]

        text_lower = text.lower()

        for pattern in date_patterns:
            match = re.search(pattern, text_lower)
            if match:
                try:
                    groups = match.groups()

                    if len(groups) >= 3:
                        if any(month in pattern for month in self.config.polish_months.keys()):
                            # Format polski: "22 lipca 2025"
                            day = groups[0].zfill(2)
                            month_name = groups[1]
                            year = groups[2]

                            month_num = self.config.polish_months.get(month_name, '01')
                            return f"{year}-{month_num}-{day}"

                        elif '.' in pattern:
                            # Format DD.MM.YYYY
                            day, month, year = groups
                            return f"{year}-{month.zfill(2)}-{day.zfill(2)}"

                        elif '-' in pattern:
                            # Format YYYY-MM-DD
                            year, month, day = groups
                            return f"{year}-{month.zfill(2)}-{day.zfill(2)}"

                except (ValueError, IndexError, AttributeError) as e:
                    self.logger.debug(f"Błąd parsowania daty z '{text}': {e}")
                    continue

        return None

    def _extract_session_number(self, text: str) -> int:
        """Wyciąga numer posiedzenia z tekstu"""
        # Szuka wzorców jak "Nr 15", "posiedzenie 23", "sesja 5"
        patterns = [
            r'nr\s*(\d+)',
            r'posiedzenie\s*(\d+)',
            r'sesja\s*(\d+)',
            r'(\d+)\s*posiedzenie',
            r'(\d+)\.'
        ]

        for pattern in patterns:
            match = re.search(pattern, text.lower())
            if match:
                return int(match.group(1))

        return 0  # Jeśli nie znaleziono numeru

    def _extract_date(self, text: str) -> Optional[str]:
        """Wyciąga datę z tekstu"""
        # Wzorce polskich dat
        date_patterns = [
            r'(\d{1,2})\s*(stycznia|lutego|marca|kwietnia|maja|czerwca|lipca|sierpnia|września|października|listopada|grudnia)\s*(\d{4})',
            r'(\d{1,2})\.(\d{1,2})\.(\d{4})',
            r'(\d{4})-(\d{1,2})-(\d{1,2})'
        ]

        polish_months = {
            'stycznia': '01', 'lutego': '02', 'marca': '03', 'kwietnia': '04',
            'maja': '05', 'czerwca': '06', 'lipca': '07', 'sierpnia': '08',
            'września': '09', 'października': '10', 'listopada': '11', 'grudnia': '12'
        }

        for pattern in date_patterns:
            match = re.search(pattern, text.lower())
            if match:
                try:
                    if 'stycznia' in pattern:  # wzorzec polski
                        day, month_name, year = match.groups()
                        month = polish_months.get(month_name, '01')
                        return f"{year}-{month.zfill(2)}-{day.zfill(2)}"
                    elif '.' in pattern:  # DD.MM.YYYY
                        day, month, year = match.groups()
                        return f"{year}-{month.zfill(2)}-{day.zfill(2)}"
                    else:  # YYYY-MM-DD
                        return match.group(0)
                except:
                    continue

        return None

    def _process_session(self, session_data: Dict[str, str]) -> Optional[SejmSession]:
        """
        Przetwarza pojedyncze posiedzenie Sejmu z lepszą obsługą błędów
        """
        session_id = session_data['id']

        if session_id in self.processed_sessions:
            self.logger.debug(f"Posiedzenie {session_id} już przetworzone, pomijam")
            return None

        self.logger.info(f"🔄 Przetwarzam: {session_data['title']}")

        # Dla stenogramów URL to zawsze bezpośredni link do PDF
        transcript_url = session_data['url']
        file_type = 'pdf'

        self.logger.info(f"📄 Typ: {file_type.upper()}, URL: {transcript_url}")

        # Utwórz obiekt posiedzenia
        session = SejmSession(
            session_id=session_id,
            meeting_number=session_data['meeting_number'],
            day_letter=session_data.get('day_letter', ''),
            date=session_data['date'],
            title=session_data['title'],
            url=session_data['url'],
            transcript_url=transcript_url,
            file_type=file_type,
            scraped_at=datetime.now().isoformat(),
            kadencja=session_data['kadencja']
        )

        # Pobierz i przetwórz PDF z lepszą obsługą błędów
        pdf_bytes = b""
        text_content = ""
        last_error = None

        try:
            self.logger.info(f"⬇️  Pobieranie dokumentu z: {transcript_url}")
            text_content, pdf_bytes = self._download_and_parse_file(
                transcript_url, file_type, session_id
            )

            if not text_content:
                error_msg = f"Nie udało się wyciągnąć tekstu z {transcript_url}"
                last_error = error_msg
                self.logger.error(f"❌ {error_msg}")

                # Zapisz informację o błędzie
                session_data['last_error'] = error_msg
                return None

        except requests.exceptions.Timeout as e:
            error_msg = f"Timeout przy pobieraniu {transcript_url}: {e}"
            last_error = error_msg
            self.logger.error(f"⏱️  {error_msg}")
            session_data['last_error'] = error_msg
            return None

        except requests.exceptions.ConnectionError as e:
            error_msg = f"Błąd połączenia dla {transcript_url}: {e}"
            last_error = error_msg
            self.logger.error(f"🌐 {error_msg}")
            session_data['last_error'] = error_msg
            return None

        except Exception as e:
            error_msg = f"Błąd pobierania treści dla posiedzenia {session_id}: {e}"
            last_error = error_msg
            self.logger.error(f"❌ {error_msg}")
            session_data['last_error'] = error_msg
            return None

        # Walidacja treści
        if not self._validate_extracted_text(text_content, transcript_url):
            self.logger.warning(f"⚠️  Tekst nie przeszedł walidacji dla {session_id}")
            return None

        # Uzupełnij obiekt posiedzenia
        session.transcript_text = text_content
        session.hash = hashlib.md5(text_content.encode()).hexdigest()

        # Zapisz posiedzenie
        try:
            if self._save_session_with_pdf(session, pdf_bytes):
                self._save_processed_session(session_id)

                pdf_size_info = f"PDF {len(pdf_bytes):,} B" if pdf_bytes else "brak PDF"
                self.logger.info(
                    f"✅ Posiedzenie {session_id} zapisane pomyślnie: "
                    f"{len(text_content):,} znaków, {pdf_size_info}"
                )
                return session
            else:
                self.logger.error(f"❌ Błąd zapisu posiedzenia {session_id}")
                return None

        except Exception as e:
            self.logger.error(f"❌ Błąd zapisu posiedzenia {session_id}: {e}")
            return None

    def _find_transcript_on_page(self, page_url: str) -> tuple[str, str]:
        """
        Szuka linków do transkryptów na stronie HTML sesji
        Zwraca: (transcript_url, file_type)
        """
        try:
            response = self._make_request(page_url)
            if not response:
                return "", "html"

            soup = BeautifulSoup(response.text, 'html.parser')

            # Szukaj linków PDF używając selektorów z konfiguracji
            for selector in self.config.pdf_selectors:
                links = soup.select(selector)

                for link in links:
                    href = link.get('href', '')
                    text = link.get_text(strip=True).lower()

                    # Sprawdź czy to link do stenogramu
                    if any(word in text for word in
                           ['stenogram', 'posiedzenie', 'księga', 'transkryp', 'sprawozdanie']):
                        full_url = urljoin(page_url, href)

                        if href.endswith('.pdf'):
                            self.logger.info(f"🔍 Znaleziono PDF na stronie: {full_url}")
                            return full_url, 'pdf'
                        elif href.endswith(('.docx', '.doc')):
                            self.logger.info(f"🔍 Znaleziono DOCX na stronie: {full_url}")
                            return full_url, 'docx'

            # Jeśli nie znaleziono PDF, szukaj tradycyjnych linków
            for link in soup.find_all('a', href=True):
                href = link['href']
                text = link.get_text(strip=True).lower()

                # Sprawdź wzorce transkryptów
                transcript_keywords = [
                    'stenogram', 'sprawozdanie stenograficzne', 'transkryp',
                    'przebieg posiedzenia', 'protokół obrad'
                ]

                if any(keyword in text for keyword in transcript_keywords):
                    full_url = urljoin(page_url, href)

                    if href.endswith('.pdf'):
                        return full_url, 'pdf'
                    elif href.endswith(('.docx', '.doc')):
                        return full_url, 'docx'
                    else:
                        return full_url, 'html'

        except Exception as e:
            self.logger.warning(f"⚠️  Błąd wyszukiwania transkryptu na {page_url}: {e}")

        return "", "html"

    def _should_skip_session(self, session_title: str) -> bool:
        """
        Sprawdza czy sesję należy pominąć (fotogalerie, zapowiedzi itp.)
        ROZSZERZONA wersja
        """
        title_lower = session_title.lower()

        # Sprawdź wzorce z konfiguracji
        for pattern in self.config.skip_patterns:
            if pattern.lower() in title_lower:
                return True

        # Dodatkowe sprawdzenia
        # Sprawdź czy to bardzo krótki tekst
        if len(session_title.strip()) < 10:
            return True

        # Sprawdź czy zawiera tylko liczby/daty (prawdopodobnie błędny parsing)
        import re
        if re.match(r'^[\d\s\.\-/]+$', session_title.strip()):
            return True

        # Sprawdź czy to link nawigacyjny
        nav_keywords = ['menu', 'nawigacja', 'strona główna', 'wstecz', 'dalej', 'poprzedni', 'następny']
        if any(keyword in title_lower for keyword in nav_keywords):
            return True

        return False

    def _save_session(self, session: SejmSession):
        """Zapisuje sesję do pliku z walidacją"""
        year = session.date[:4] if session.date and len(session.date) >= 4 else str(date.today().year)
        year_dir = self.config.output_dir / year
        year_dir.mkdir(exist_ok=True)

        filename = f"posiedzenie_{session.session_number:03d}_{session.session_id}.json"
        filepath = year_dir / filename

        try:
            # Przygotuj dane do zapisu - BEZ surowych danych PDF!
            session_data = asdict(session)

            # Dodaj metadane
            session_data['text_length'] = len(session.transcript_text) if session.transcript_text else 0
            session_data['word_count'] = len(session.transcript_text.split()) if session.transcript_text else 0

            # Sprawdź czy tekst nie jest binarny (zabezpieczenie)
            if session.transcript_text:
                try:
                    # Próba zakodowania - jeśli się nie uda, tekst może być uszkodzony
                    session.transcript_text.encode('utf-8')
                except UnicodeEncodeError:
                    self.logger.error(f"Tekst sesji {session.session_id} zawiera nieprawidłowe znaki!")
                    session_data['transcript_text'] = "[BŁĄD: Nieprawidłowe znaki w tekście]"

            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(session_data, f, ensure_ascii=False, indent=2)

            self.logger.info(f"💾 Zapisano sesję: {filepath} ({session_data['text_length']} znaków)")

        except Exception as e:
            self.logger.error(f"❌ Błąd zapisu sesji {session.session_id}: {e}")
            import traceback
            self.logger.debug(f"Pełny błąd zapisu: {traceback.format_exc()}")

    def _save_session_with_pdf(self, session: SejmSession, pdf_bytes: bytes = None) -> bool:
        """
        Zapisuje posiedzenie w zorganizowanej strukturze katalogów
        """
        try:
            kadencja_nr = session.kadencja
            year = session.date[:4] if session.date and len(session.date) >= 4 else str(date.today().year)

            # Struktura katalogów
            base_dir = self.config.output_dir / f"kadencja_{kadencja_nr}" / year
            json_dir = base_dir / "json"
            pdf_dir = base_dir / "pdf"

            # Utwórz katalogi
            json_dir.mkdir(parents=True, exist_ok=True)
            pdf_dir.mkdir(parents=True, exist_ok=True)

            # Nazwa bazowa pliku z literą dnia
            if session.day_letter:
                base_filename = f"posiedzenie_{session.meeting_number:03d}_{session.day_letter}_{session.session_id}"
            else:
                base_filename = f"posiedzenie_{session.meeting_number:03d}_{session.session_id}"

            # 1. ZAPISZ JSON
            json_filepath = json_dir / f"{base_filename}.json"

            session_data = asdict(session)

            # Dodaj metadane
            session_data.update({
                'text_length': len(session.transcript_text) if session.transcript_text else 0,
                'word_count': len(session.transcript_text.split()) if session.transcript_text else 0,
                'file_paths': {
                    'json': str(json_filepath.relative_to(self.config.output_dir)),
                    'pdf': str(
                        (pdf_dir / f"{base_filename}.pdf").relative_to(self.config.output_dir)) if pdf_bytes else None
                },
                'processing_info': {
                    'bot_version': '2.0',
                    'processed_at': datetime.now().isoformat(),
                    'original_pdf_available': bool(pdf_bytes and len(pdf_bytes) > 1000),
                    'pdf_size_bytes': len(pdf_bytes) if pdf_bytes else 0
                }
            })

            # Sprawdź jakość tekstu przed zapisem
            if session.transcript_text:
                try:
                    session.transcript_text.encode('utf-8')
                except UnicodeEncodeError as e:
                    self.logger.error(f"❌ Problemy z kodowaniem tekstu posiedzenia {session.session_id}: {e}")
                    session_data['transcript_text'] = "[BŁĄD: Nieprawidłowe kodowanie tekstu]"
                    session_data['processing_info']['encoding_error'] = True

            # Zapisz JSON
            with open(json_filepath, 'w', encoding='utf-8') as f:
                json.dump(session_data, f, ensure_ascii=False, indent=2)

            self.logger.info(
                f"💾 JSON: {json_filepath.relative_to(self.config.output_dir)} ({session_data['text_length']:,} znaków)")

            # 2. ZAPISZ ORYGINALNY PDF
            if pdf_bytes and len(pdf_bytes) > 1000:
                pdf_filepath = pdf_dir / f"{base_filename}.pdf"

                try:
                    with open(pdf_filepath, 'wb') as f:
                        f.write(pdf_bytes)

                    self.logger.info(
                        f"📄 PDF: {pdf_filepath.relative_to(self.config.output_dir)} ({len(pdf_bytes):,} bajtów)")

                except Exception as e:
                    self.logger.error(f"❌ Błąd zapisu PDF {session.session_id}: {e}")

            # 3. UAKTUALNIJ INDEKS POSIEDZEŃ
            self._update_session_index(kadencja_nr, year, session_data)

            return True

        except Exception as e:
            self.logger.error(f"❌ Błąd zapisu posiedzenia {session.session_id}: {e}")
            import traceback
            self.logger.debug(f"Szczegóły błędu zapisu: {traceback.format_exc()}")
            return False

    def _extract_kadencja_from_session(self, session: SejmSession) -> int:
        """Wyciąga numer kadencji z sesji"""
        # Sprawdź tytuł
        if 'kadencja' in session.title.lower():
            match = re.search(r'kadencja\s+(\d+)', session.title.lower())
            if match:
                return int(match.group(1))

        # Sprawdź URL
        if hasattr(session, 'url') and session.url:
            match = re.search(r'sejm(\d+)\.nsf', session.url.lower())
            if match:
                return int(match.group(1))

        # Fallback na podstawie daty
        if session.date:
            year = int(session.date[:4])
            if year >= 2019:
                return 10  # X kadencja
            elif year >= 2015:
                return 9  # IX kadencja
            elif year >= 2011:
                return 8  # VIII kadencja

        return 10  # Domyślnie aktualna kadencja

    def _update_session_index(self, kadencja_nr: int, year: str, session_data: dict):
        """Aktualizuje indeks sesji dla danej kadencji i roku - POPRAWIONA wersja"""
        try:
            index_dir = self.config.output_dir / f"kadencja_{kadencja_nr}" / year
            index_file = index_dir / "index.json"

            # Wczytaj istniejący indeks lub utwórz nowy
            if index_file.exists():
                with open(index_file, 'r', encoding='utf-8') as f:
                    index_data = json.load(f)
            else:
                index_data = {
                    'kadencja': kadencja_nr,
                    'year': year,
                    'sessions': {},
                    'stats': {
                        'total_sessions': 0,
                        'total_characters': 0,
                        'total_words': 0,
                        'last_updated': None
                    }
                }

            # POPRAWKA: Używaj prawidłowych kluczy z session_data
            session_id = session_data['session_id']

            # Bezpieczne wyciągnięcie wartości z fallback
            meeting_number = session_data.get('meeting_number', 0)  # POPRAWKA: session_number -> meeting_number

            index_data['sessions'][session_id] = {
                'meeting_number': meeting_number,  # POPRAWKA
                'title': session_data.get('title', 'Bez tytułu')[:100],
                'date': session_data.get('date', 'Brak daty'),
                'text_length': session_data.get('text_length', 0),
                'word_count': session_data.get('word_count', 0),
                'file_type': session_data.get('file_type', 'pdf'),
                'has_pdf': session_data.get('processing_info', {}).get('original_pdf_available', False),
                'processed_at': session_data.get('processing_info', {}).get('processed_at', datetime.now().isoformat()),
                'day_letter': session_data.get('day_letter', ''),  # Dodane
                'kadencja': kadencja_nr
            }

            # Uaktualnij statystyki
            index_data['stats']['total_sessions'] = len(index_data['sessions'])
            index_data['stats']['total_characters'] = sum(
                s.get('text_length', 0) for s in index_data['sessions'].values()
            )
            index_data['stats']['total_words'] = sum(
                s.get('word_count', 0) for s in index_data['sessions'].values()
            )
            index_data['stats']['last_updated'] = datetime.now().isoformat()

            # Zapisz indeks
            with open(index_file, 'w', encoding='utf-8') as f:
                json.dump(index_data, f, ensure_ascii=False, indent=2)

            self.logger.debug(f"📇 Uaktualniono indeks: {index_file.relative_to(self.config.output_dir)}")

        except Exception as e:
            self.logger.warning(f"⚠️  Błąd aktualizacji indeksu: {e}")
            # Dodaj więcej szczegółów do debugowania
            import traceback
            self.logger.debug(f"Pełny błąd indeksu: {traceback.format_exc()}")
            self.logger.debug(f"Dane session_data: {list(session_data.keys())}")

    def cleanup_broken_sessions(self) -> int:
        """
        Czyści uszkodzone pliki JSON z poprzednich wersji
        ROZSZERZONA wersja dla nowej struktury katalogów
        """
        broken_count = 0
        fixed_count = 0

        # Sprawdź zarówno starą jak i nową strukturę
        search_patterns = [
            self.config.output_dir / "*.json",  # Stara struktura
            self.config.output_dir / "*" / "*.json",  # Rok/plik.json
            self.config.output_dir / "*" / "*" / "json" / "*.json"  # Nowa struktura
        ]

        for pattern in search_patterns:
            for json_file in self.config.output_dir.glob(str(pattern).replace(str(self.config.output_dir) + "/", "")):
                if json_file.name == "processed_sessions.json" or json_file.name == "index.json":
                    continue

                try:
                    with open(json_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)

                    transcript = data.get('transcript_text', '')

                    # Sprawdź czy zawiera binarne dane PDF
                    if transcript and ('%PDF-' in transcript[:100] or '\u0000' in transcript[:1000]):
                        self.logger.info(f"🧹 Usuwam uszkodzony plik: {json_file.relative_to(self.config.output_dir)}")
                        json_file.unlink()

                        # Usuń z processed_sessions
                        session_id = data.get('session_id')
                        if session_id and session_id in self.processed_sessions:
                            self.processed_sessions.remove(session_id)

                        broken_count += 1

                    # Sprawdź czy plik ma starą strukturę i można go przenieść
                    elif 'kadencja' not in str(json_file.parent):
                        # To jest plik ze starej struktury - można spróbować przenieść
                        if self._try_migrate_old_file(json_file, data):
                            fixed_count += 1

                except Exception as e:
                    self.logger.warning(f"⚠️  Nie można sprawdzić pliku {json_file}: {e}")

        if broken_count > 0 or fixed_count > 0:
            # Zapisz zaktualizowaną listę processed_sessions
            self._save_processed_session("")  # Zapisuje całą listę

            if broken_count > 0:
                self.logger.info(f"🧹 Wyczyszczono {broken_count} uszkodzonych plików")
            if fixed_count > 0:
                self.logger.info(f"🔄 Przeniesiono {fixed_count} plików do nowej struktury")

        return broken_count + fixed_count

    def _try_migrate_old_file(self, old_file: Path, data: dict) -> bool:
        """Próbuje przenieść plik ze starej struktury do nowej"""
        try:
            # Wyciągnij informacje potrzebne do migracji
            kadencja_nr = self._extract_kadencja_from_data(data)
            year = data.get('date', '2024-01-01')[:4]

            # Nowa lokalizacja
            new_dir = self.config.output_dir / f"kadencja_{kadencja_nr}" / year / "json"
            new_dir.mkdir(parents=True, exist_ok=True)

            new_file = new_dir / old_file.name

            # Przenieś plik
            old_file.rename(new_file)

            self.logger.info(f"🔄 Migracja: {old_file.name} -> {new_file.relative_to(self.config.output_dir)}")
            return True

        except Exception as e:
            self.logger.warning(f"⚠️  Nie udało się zmigrować {old_file}: {e}")
            return False

    def _extract_kadencja_from_data(self, data: dict) -> int:
        """Wyciąga kadencję z danych sesji"""
        # Sprawdź czy jest już w danych
        if 'kadencja' in data:
            return data['kadencja']

        # Sprawdź tytuł
        title = data.get('title', '').lower()
        if 'kadencja' in title:
            match = re.search(r'kadencja\s+(\d+)', title)
            if match:
                return int(match.group(1))

        # Sprawdź URL
        url = data.get('url', '') or data.get('transcript_url', '')
        if url:
            match = re.search(r'sejm(\d+)\.nsf', url.lower())
            if match:
                return int(match.group(1))

        # Fallback na podstawie daty
        date_str = data.get('date', '2024-01-01')
        if date_str:
            year = int(date_str[:4])
            if year >= 2019:
                return 10
            elif year >= 2015:
                return 9
            elif year >= 2011:
                return 8

        return 10  # Domyślnie

    def _debug_found_sessions(self, sessions: List[Dict[str, str]]):
        """Debuguje znalezione posiedzenia do analizy problemów"""
        if not sessions:
            self.logger.info("🔍 BRAK znalezionych posiedzeń - możliwe przyczyny:")
            self.logger.info("   • Zmiana struktury strony Sejmu")
            self.logger.info("   • Błędne selektory CSS")
            self.logger.info("   • Problemy z połączeniem")
            return

        self.logger.info(f"🔍 ZNALEZIONE POSIEDZENIA ({len(sessions)}):")

        # Grupuj według kadencji i roku
        by_kadencja = {}
        for session in sessions:
            kadencja = session.get('kadencja', 0)
            rok = session.get('rok', 0)

            key = f"Kadencja {kadencja} ({rok})"
            if key not in by_kadencja:
                by_kadencja[key] = []
            by_kadencja[key].append(session)

        # Wypisz statystyki
        for key, kadencja_sessions in by_kadencja.items():
            self.logger.info(f"   📊 {key}: {len(kadencja_sessions)} posiedzeń")

            # Pokaż przykłady
            for i, session in enumerate(kadencja_sessions[:3]):  # Max 3 przykłady
                title = session.get('title', '')[:60]
                date = session.get('date', 'brak daty')
                meeting_num = session.get('meeting_number', 0)

                self.logger.info(f"      • Posiedzenie {meeting_num} ({date}): {title}...")

            if len(kadencja_sessions) > 3:
                self.logger.info(f"      ... i {len(kadencja_sessions) - 3} więcej")

        # Sprawdź najnowsze i najstarsze daty
        dates = [s.get('date', '') for s in sessions if s.get('date')]
        if dates:
            dates.sort()
            self.logger.info(f"📅 Zakres dat: {dates[0]} - {dates[-1]}")

        # Sprawdź czy są najnowsze posiedzenia z 2024-2025
        recent_sessions = [s for s in sessions if s.get('date', '').startswith(('2024', '2025'))]
        if recent_sessions:
            self.logger.info(f"✅ Znaleziono {len(recent_sessions)} najnowszych posiedzeń (2024-2025)")
        else:
            self.logger.warning("⚠️  BRAK najnowszych posiedzeń z 2024-2025!")
            self.logger.warning("   • Sprawdź czy strona Sejmu działa poprawnie")
            self.logger.warning("   • Możliwa zmiana struktury URLi lub selektorów")

    def _debug_page_content(self, soup: BeautifulSoup, url: str):
        """Debuguje zawartość strony aby zdiagnozować problemy z parsowaniem"""

        # Sprawdź ile jest linków PDF
        all_pdf_links = soup.select('a[href*=".pdf"]')
        ksiazka_pdf_links = soup.select('a[href*="ksiazka.pdf"]')
        pdf_class_links = soup.select('a.pdf')

        self.logger.debug(f"🔍 ANALIZA STRONY: {url}")
        self.logger.debug(f"   📎 Wszystkie linki PDF: {len(all_pdf_links)}")
        self.logger.debug(f"   📚 Linki do ksiazka.pdf: {len(ksiazka_pdf_links)}")
        self.logger.debug(f"   🎯 Linki z klasą 'pdf': {len(pdf_class_links)}")

        # Pokaż kilka przykładów linków PDF
        for i, link in enumerate(pdf_class_links[:3]):
            href = link.get('href', '')
            text = link.get_text(strip=True)
            title = link.get('title', '')

            self.logger.debug(
                f"   📄 PDF {i + 1}: href='{href[:60]}...', text='{text[:40]}...', title='{title[:40]}...'")

        # Sprawdź czy strona zawiera jakieś błędy
        error_indicators = [
            'The requested URL was rejected',
            'Access Denied',
            'Error',
            'Błąd',
            'Brak dostępu'
        ]

        page_text = soup.get_text()
        for error in error_indicators:
            if error in page_text:
                self.logger.warning(f"⚠️  Strona może zawierać błąd: '{error}'")

        # Sprawdź czy są jakieś oznaki dat
        dates_found = re.findall(
            r'\d{1,2}\s+(stycznia|lutego|marca|kwietnia|maja|czerwca|lipca|sierpnia|września|października|listopada|grudnia)\s+\d{4}',
            page_text.lower())
        if dates_found:
            self.logger.debug(f"📅 Znalezione daty na stronie: {len(dates_found)} (pierwsze: {dates_found[:3]})")
        else:
            self.logger.warning("⚠️  BRAK polskich dat na stronie - może być problem z parsowaniem")

        # Sprawdź czy są numery posiedzeń
        meeting_numbers = re.findall(r'posiedzenie\s+(\d+)', page_text.lower())
        if meeting_numbers:
            numbers = sorted(set(int(n) for n in meeting_numbers), reverse=True)
            self.logger.debug(f"🔢 Numery posiedzeń na stronie: {numbers[:5]}")
        else:
            self.logger.warning("⚠️  BRAK numerów posiedzeń na stronie")


# Dodaj na końcu pliku sejmbot.py, przed main():

import signal
import time
from threading import Event


class SejmBotDaemon:
    """Daemon mode for continuous operation"""

    def __init__(self, config: SejmBotConfig):
        self.config = config
        self.logger = config.logger
        self.stop_event = Event()

        # Interval between runs (in seconds) - 4 hours
        self.run_interval = 4 * 60 * 60  # 4 hours = 14400 seconds

        # Setup signal handlers
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        self.logger.info(f"📡 Otrzymano sygnał {signum}, graceful shutdown...")
        self.stop_event.set()

    def run_daemon(self):
        """Main daemon loop"""
        self.logger.info("🔄 Uruchomiono SejmBot w trybie daemon")
        self.logger.info(f"⏰ Interval: {self.run_interval / 3600:.1f} godzin")

        # First run immediately
        self._run_bot_cycle()

        while not self.stop_event.is_set():
            try:
                # Wait for interval or stop signal
                if self.stop_event.wait(timeout=self.run_interval):
                    # Stop signal received
                    break

                # Run bot cycle
                self._run_bot_cycle()

            except Exception as e:
                self.logger.error(f"❌ Błąd w daemon loop: {e}")
                # Continue running even if single cycle fails
                time.sleep(300)  # Wait 5 minutes before retry

        self.logger.info("🛑 Daemon zatrzymany")

    def _run_bot_cycle(self):
        """Single bot execution cycle"""
        try:
            self.logger.info("🚀 Rozpoczynam cykl pobierania...")

            bot = SejmBot(self.config)
            processed = bot.run()

            if processed > 0:
                self.logger.info(f"✅ Cykl zakończony: {processed} nowych transkryptów")
            else:
                self.logger.info("📋 Cykl zakończony: brak nowych transkryptów")

        except Exception as e:
            self.logger.error(f"❌ Błąd w cyklu bota: {e}")


def main():
    """Punkt wejścia programu"""
    import argparse

    parser = argparse.ArgumentParser(description='SejmBot - Parser transkryptów Sejmu')
    parser.add_argument('--daemon', action='store_true',
                        help='Uruchom w trybie daemon (ciągła praca)')
    args = parser.parse_args()

    # Inicjalizacja
    config = SejmBotConfig()

    if args.daemon:
        # Tryb daemon
        daemon = SejmBotDaemon(config)
        try:
            daemon.run_daemon()
        except KeyboardInterrupt:
            print("\n⏹️  Daemon przerwany przez użytkownika")
    else:
        # Pojedyncze uruchomienie
        bot = SejmBot(config)
        try:
            processed_count = bot.run()
            if processed_count > 0:
                print(f"\n✅ Sukces! Przetworzono {processed_count} nowych transkryptów")
            else:
                print("\n📋 Brak nowych transkryptów do przetworzenia")
        except KeyboardInterrupt:
            print("\n⏹️  Przerwano przez użytkownika")
        except Exception as e:
            print(f"\n❌ Błąd krytyczny: {e}")
            logging.error(f"Błąd krytyczny: {e}", exc_info=True)


if __name__ == "__main__":
    main()
