#!/usr/bin/env python3
"""
SejmBot - Etap 1: Parser transkryptów Sejmu RP
Automatycznie pobiera i parsuje transkrypty z posiedzeń Sejmu.
"""

import hashlib
import json
import logging
import re
import time
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
    """Reprezentacja posiedzenia Sejmu"""
    session_id: str
    session_number: int
    date: str
    title: str
    url: str
    transcript_url: Optional[str] = None
    transcript_text: Optional[str] = None
    file_type: str = "html"  # html, pdf, docx
    scraped_at: str = ""
    hash: str = ""


class SejmBotConfig:
    """Konfiguracja bota"""

    def __init__(self):
        # todo:
        self.user_agent = "jestem botem :) Mozilla/5.0 (compatible)"
        self.output_dir = Path("transkrypty")
        self.logs_dir = Path("logs")
        self.delay_between_requests = 3  # Zwiększone dla sejm.gov.pl
        self.max_retries = 3
        self.timeout = 30

        # URLs - zaktualizowane na podstawie aktualnej struktury
        self.base_urls = [
            # X kadencja (aktualna) - może być chroniona
            "https://www.sejm.gov.pl/sejm10.nsf/",
            # IX kadencja - sprawdzone jako działające
            "https://www.sejm.gov.pl/sejm9.nsf/",
            # Alternatywne serwery stenogramów
            "https://orka2.sejm.gov.pl/StenogramyX.nsf/",  # X kadencja
            "https://orka2.sejm.gov.pl/Stenogramy9.nsf/",  # IX kadencja
        ]

        # Wzorce do rozpoznawania linków do transkryptów - rozszerzone
        self.transcript_patterns = [
            r"stenogram",
            r"sprawozdanie.*stenograficzne",
            r"przebieg.*posiedzenia",
            r"transkrypcja",
            r"protokół.*obrad",
            r"stenograficzne",
            r"dzień.*posiedzenia"
        ]

        # Dodatkowe nagłówki dla sejm.gov.pl
        self.additional_headers = {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'pl,en-US;q=0.7,en;q=0.3',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }

        self._setup_directories()
        self._setup_logging()

    def _setup_directories(self):
        """Tworzy potrzebne katalogi"""
        self.output_dir.mkdir(exist_ok=True)
        self.logs_dir.mkdir(exist_ok=True)

        # Struktura: transkrypty/YYYY/
        current_year = date.today().year
        (self.output_dir / str(current_year)).mkdir(exist_ok=True)

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
        # todo włącz mnie
        # if config.logger.level <= logging.INFO:
        #     config.logger.setLevel(logging.DEBUG)

    def _debug_page_content(self, url: str, soup: BeautifulSoup):
        """Debug: pokazuje co jest na stronie"""
        self.logger.debug(f"=== DEBUG dla {url} ===")

        # Pokaż wszystkie linki z href
        all_links = soup.find_all('a', href=True)
        self.logger.debug(f"Znaleziono {len(all_links)} linków z href")

        # Pokaż pierwsze 5 linków jako przykład
        for i, link in enumerate(all_links[:10]):
            href = link.get('href', '')
            text = link.get_text(strip=True)[:50]
            classes = link.get('class', [])
            self.logger.debug(f"Link {i + 1}: href='{href[:50]}...' text='{text}' class='{classes}'")

        # Pokaż linki z class="pdf"
        pdf_links = soup.select('a.pdf')
        self.logger.debug(f"Znaleziono {len(pdf_links)} linków z class='pdf'")

        for i, link in enumerate(pdf_links):
            href = link.get('href', '')
            text = link.get_text(strip=True)
            self.logger.debug(f"PDF {i + 1}: '{text}' -> '{href}'")

        self.logger.debug("=== KONIEC DEBUG ===")

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

    def _is_session_link(self, href: str, text: str) -> bool:
        """Sprawdza czy link prowadzi do sesji/stenogramu"""
        href_lower = href.lower()
        text_lower = text.lower()

        # Pozytywne wzorce w URL - dodano PDF i konkretne serwery Sejmu
        positive_url_patterns = [
            'stenogram', 'posiedzenie', 'sesja', 'day_', 'nr_',
            'sprawozdanie', 'transcript', 'meeting',
            'stenointr',  # StenoInter10.nsf
            'ksiazka.pdf',  # pliki stenogramów
            '.pdf',  # wszystkie PDFy
            'steno'  # ogólne wzorce steno
        ]

        # Pozytywne wzorce w tekście - dodano polskie daty
        positive_text_patterns = [
            'posiedzenie', 'stenogram', 'sprawozdanie stenograficzne',
            'sesja', 'dzień', 'nr ', '. posiedzenie', 'stenograficzne',
            'przebieg obrad', 'protokół',
            # Polskie miesiące
            'stycznia', 'lutego', 'marca', 'kwietnia', 'maja', 'czerwca',
            'lipca', 'sierpnia', 'września', 'października', 'listopada', 'grudnia',
            # Dni tygodnia
            'poniedziałek', 'wtorek', 'środa', 'czwartek', 'piątek', 'sobota', 'niedziela',
            # Wzorce dat
            r'\d{1,2}\s+(stycznia|lutego|marca|kwietnia|maja|czerwca|lipca|sierpnia|września|października|listopada|grudnia)\s+\d{4}',
            # Format numeryczny
            r'\d{4}'  # rok w tekście
        ]

        # Negatywne wzorce (wykluczenia) - zmniejszone, bo były zbyt restrykcyjne
        negative_patterns = [
            'komisja', 'menu', 'nav', 'search', 'wyszukaj', 'login',
            'rss', 'mailto:', 'javascript:', 'tel:',
            'facebook', 'twitter', 'youtube', 'instagram',
            'regulamin', 'kontakt', 'cookie'
        ]

        # Sprawdź negatywne wzorce
        for pattern in negative_patterns:
            if pattern in href_lower or pattern in text_lower:
                return False

        # Sprawdź pozytywne wzorce w URL
        url_match = any(pattern in href_lower for pattern in positive_url_patterns)

        # Sprawdź pozytywne wzorce w tekście (w tym regex)
        text_match = False
        for pattern in positive_text_patterns:
            if pattern.startswith('r\'') or '\\d' in pattern:  # regex pattern
                import re
                pattern_clean = pattern.replace('r\'', '').replace('\'', '')
                if re.search(pattern_clean, text_lower):
                    text_match = True
                    break
            else:
                if pattern in text_lower:
                    text_match = True
                    break

        # Dodatkowe sprawdzenie: czy tekst wygląda jak data
        date_like = self._looks_like_date(text)

        return url_match or text_match or date_like

    def _looks_like_date(self, text: str) -> bool:
        """Sprawdza czy tekst wygląda jak data posiedzenia"""
        import re

        text_lower = text.lower().strip()

        # Wzorce polskich dat
        date_patterns = [
            r'\d{1,2}\s+(stycznia|lutego|marca|kwietnia|maja|czerwca|lipca|sierpnia|września|października|listopada|grudnia)\s+\d{4}',
            r'\d{1,2}\.\d{1,2}\.\d{4}',
            r'\d{4}-\d{1,2}-\d{1,2}',
            # Z dniem tygodnia
            r'\d{1,2}\s+(stycznia|lutego|marca|kwietnia|maja|czerwca|lipca|sierpnia|września|października|listopada|grudnia)\s+\d{4}\s+\((poniedziałek|wtorek|środa|czwartek|piątek|sobota|niedziela)\)'
        ]

        for pattern in date_patterns:
            if re.search(pattern, text_lower):
                return True

        # Sprawdź czy zawiera rok i miesiąc
        has_year = re.search(r'20\d{2}', text_lower)
        polish_months = ['stycznia', 'lutego', 'marca', 'kwietnia', 'maja', 'czerwca',
                         'lipca', 'sierpnia', 'września', 'października', 'listopada', 'grudnia']
        has_month = any(month in text_lower for month in polish_months)

        return has_year and has_month

    def _try_extract_date_from_url(self, url: str) -> Optional[str]:
        """Próbuje wyciągnąć datę z URL"""
        import re

        # Wzorce dat w URL
        date_patterns = [
            r'/(\d{4})/(\d{1,2})/(\d{1,2})',  # /2025/01/15/
            r'date=(\d{4})-(\d{1,2})-(\d{1,2})',  # date=2025-01-15
            r'(\d{4})(\d{2})(\d{2})',  # 20250115
            r'year=(\d{4}).*month=(\d{1,2}).*day=(\d{1,2})'  # parametry URL
        ]

        for pattern in date_patterns:
            match = re.search(pattern, url)
            if match:
                try:
                    if len(match.groups()) == 3:
                        year, month, day = match.groups()
                        return f"{year}-{month.zfill(2)}-{day.zfill(2)}"
                except:
                    continue

        return None

    def _make_request(self, url: str, **kwargs) -> Optional[requests.Response]:
        """Wykonuje zapytanie HTTP z retry i error handling"""
        for attempt in range(self.config.max_retries):
            try:
                time.sleep(self.config.delay_between_requests)
                response = self.session.get(
                    url,
                    timeout=self.config.timeout,
                    **kwargs
                )

                if response.status_code == 200:
                    return response
                elif response.status_code == 403:
                    self.logger.warning(f"Dostęp zabroniony (403) dla URL: {url}")
                    return None
                else:
                    self.logger.warning(f"HTTP {response.status_code} dla URL: {url}")

            except requests.RequestException as e:
                self.logger.warning(f"Błąd zapytania (próba {attempt + 1}/{self.config.max_retries}): {e}")
                if attempt < self.config.max_retries - 1:
                    time.sleep(2 ** attempt)  # exponential backoff

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

    def _download_and_parse_file(self, url: str, file_type: str, session_id: str) -> tuple[str, bytes]:
        """
        Pobiera plik i zwraca zarówno tekst jak i oryginalne bajty
        """
        try:
            self.logger.info(f"Pobieranie {file_type.upper()}: {url}")

            response = self._make_request(url)
            if not response:
                return "", b""

            # Pobierz oryginalne bajty
            file_bytes = response.content

            # Sprawdź content-type
            content_type = response.headers.get('content-type', '').lower()

            if file_type == 'pdf':
                if 'application/pdf' not in content_type and not url.endswith('.pdf'):
                    self.logger.warning(f"URL {url} może nie być PDFem (content-type: {content_type})")

                # Parsuj tekst z PDF
                text = self._extract_text_from_pdf_bytes(file_bytes)
                return text, file_bytes

            elif file_type == 'docx':
                # Dla DOCX nie zapisujemy oryginału (mniej przydatny)
                text = self._extract_text_from_docx_bytes(file_bytes)
                return text, b""

        except Exception as e:
            self.logger.error(f"Błąd pobierania/parsowania pliku {url}: {e}")
            return "", b""

        return "", b""

    def _extract_text_from_pdf_bytes(self, pdf_bytes: bytes) -> str:
        """
        Ekstraktuje tekst z PDF z bajtów
        """
        if not PDF_SUPPORT:
            self.logger.error("Brak wsparcia dla PDF - zainstaluj: pip install pdfplumber")
            return ""

        try:
            import io

            with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
                text = ""
                total_pages = len(pdf.pages)

                self.logger.debug(f"PDF ma {total_pages} stron")

                # Najpierw spróbuj standardowego wyciągania tekstu
                pages_with_text = 0
                for i, page in enumerate(pdf.pages):
                    try:
                        page_text = page.extract_text()
                        if page_text and len(page_text.strip()) > 50:  # Sensowna ilość tekstu
                            text += page_text + "\n"
                            pages_with_text += 1

                        # Log co 25 stron
                        if (i + 1) % 25 == 0:
                            self.logger.debug(
                                f"Przetworzono {i + 1}/{total_pages} stron, tekst na {pages_with_text} stronach")

                    except Exception as e:
                        self.logger.warning(f"Błąd parsowania strony {i + 1}: {e}")
                        continue

                cleaned_text = text.strip()

                # Jeśli brak tekstu, może to zeskanowany PDF - spróbuj OCR
                if len(cleaned_text) < 100 and total_pages > 5:
                    self.logger.warning(f"PDF ma {total_pages} stron ale tylko {len(cleaned_text)} znaków tekstu")
                    self.logger.info("🔍 Prawdopodobnie zeskanowany PDF - próbuję OCR...")

                    ocr_text = self._try_ocr_pdf(pdf_bytes)
                    if ocr_text and len(ocr_text) > len(cleaned_text):
                        self.logger.info(f"✅ OCR wydobył {len(ocr_text)} znaków")
                        return ocr_text
                    else:
                        self.logger.warning("❌ OCR nie pomógł lub nie jest dostępny")

                if pages_with_text > 0:
                    self.logger.info(
                        f"📄 Wydobyto {len(cleaned_text)} znaków z PDF ({pages_with_text}/{total_pages} stron z tekstem)")
                else:
                    self.logger.warning(f"⚠️  PDF ma {total_pages} stron ale brak czytelnego tekstu")

                return cleaned_text

        except Exception as e:
            self.logger.error(f"Błąd parsowania PDF z bajtów: {e}")
            return ""

    def _try_ocr_pdf(self, pdf_bytes: bytes) -> str:
        """
        Próbuje OCR na PDF (wymaga tesseract + pdf2image)
        """
        try:
            # Sprawdź czy są dostępne biblioteki OCR
            try:
                from pdf2image import convert_from_bytes
                import pytesseract
            except ImportError:
                self.logger.debug("Brak bibliotek OCR (pdf2image, pytesseract)")
                return ""

            self.logger.info("🔍 Rozpoczynam OCR PDF...")

            # Konwertuj PDF na obrazy (tylko pierwsze 10 stron dla testu)
            images = convert_from_bytes(pdf_bytes, first_page=1, last_page=10)

            ocr_text = ""
            for i, image in enumerate(images):
                try:
                    # OCR na każdym obrazie
                    page_text = pytesseract.image_to_string(image, lang='pol+eng')
                    if page_text and len(page_text.strip()) > 20:
                        ocr_text += page_text + "\n"

                    self.logger.debug(f"OCR strona {i + 1}: {len(page_text)} znaków")

                except Exception as e:
                    self.logger.warning(f"Błąd OCR strony {i + 1}: {e}")
                    continue

            return ocr_text.strip()

        except Exception as e:
            self.logger.warning(f"Błąd OCR: {e}")
            return ""

    def _extract_text_from_pdf(self, file_path: Path) -> str:
        """Ekstraktuje tekst z PDF"""
        if not PDF_SUPPORT:
            self.logger.error("Brak wsparcia dla PDF - zainstaluj pdfplumber")
            return ""

        try:
            with pdfplumber.open(file_path) as pdf:
                text = ""
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
                return text.strip()
        except Exception as e:
            self.logger.error(f"Błąd parsowania PDF {file_path}: {e}")
            return ""

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

    def _download_file(self, url: str, file_path: Path) -> bool:
        """Pobiera plik z URL"""
        try:
            response = self._make_request(url, stream=True)
            if not response:
                return False

            with open(file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            self.logger.info(f"Pobrano plik: {file_path}")
            return True

        except Exception as e:
            self.logger.error(f"Błąd pobierania pliku {url}: {e}")
            return False

    def _find_session_links(self, base_url: str) -> List[Dict[str, str]]:
        """Znajduje linki do posiedzeń na stronie głównej"""
        sessions = []

        # Aktualne URLe dla różnych kadencji
        search_urls = []

        if "sejm10" in base_url:
            search_urls = [
                f"{base_url}stenogramy.xsp",
                f"{base_url}",
                "https://orka2.sejm.gov.pl/StenogramyX.nsf/main",
            ]
        elif "sejm9" in base_url:
            search_urls = [
                f"{base_url}stenogramy.xsp",
                f"{base_url}",
            ]
        else:
            search_urls = [
                f"{base_url}stenogramy.xsp",
                f"{base_url}terminarz.xsp",
                f"{base_url}",
            ]

        for search_url in search_urls:
            self.logger.info(f"Sprawdzam URL: {search_url}")

            time.sleep(3)

            response = self._make_request(search_url)
            if not response:
                continue

            try:
                soup = BeautifulSoup(response.text, 'html.parser')

                # DEBUG: pokaż co jest na stronie
                # todo wlącz mnie jak chcesz
                # if self.logger.level <= logging.DEBUG:
                #     self._debug_page_content(search_url, soup)

                # Rozszerzone wzorce wyszukiwania - DODANO NOWE
                link_patterns = [
                    # SPECJALNE dla sejm.gov.pl
                    {'selector': 'a.pdf', 'type': 'pdf_direct'},  # class="pdf"
                    {'selector': 'a[href*="ksiazka.pdf"]', 'type': 'ksiazka'},  # bezpośrednie PDFy
                    {'selector': 'a[href*="StenoInter"]', 'type': 'stenointr'},  # serwer stenogramów
                    {'selector': 'a[href*=".pdf"]', 'type': 'pdf'},  # wszystkie PDFy

                    # Klasyczne wzorce
                    {'selector': 'a[href*="stenogram"]', 'type': 'stenogram'},
                    {'selector': 'a[href*="Stenogram"]', 'type': 'stenogram'},
                    {'selector': 'a[href*="posiedzenie"]', 'type': 'posiedzenie'},
                    {'selector': 'a[href*="Posiedzenie"]', 'type': 'posiedzenie'},
                    {'selector': 'a[href*="nr"]', 'type': 'numer'},

                    # Ostateczny fallback
                    {'selector': 'a', 'type': 'general'}
                ]

                found_links = []

                for pattern in link_patterns:
                    links = soup.select(pattern['selector'])

                    self.logger.debug(f"Wzorzec '{pattern['selector']}' znalazł {len(links)} linków")

                    for link in links:
                        href = link.get('href', '')
                        text = link.get_text(strip=True)

                        if not href or not text or len(text.strip()) < 3:
                            continue

                        # Dla wzorców PDF/stenogram - mniej restrykcyjne sprawdzanie
                        if pattern['type'] in ['pdf_direct', 'ksiazka', 'stenointr', 'pdf']:
                            if self._is_pdf_session_link(href, text):
                                full_url = urljoin(search_url, href)
                                found_links.append((full_url, text))
                                self.logger.debug(f"PDF link znaleziony: {text[:50]}... -> {full_url}")

                        # Dla pozostałych - standardowe sprawdzanie
                        elif self._is_session_link(href, text):
                            full_url = urljoin(search_url, href)
                            found_links.append((full_url, text))
                            self.logger.debug(f"Session link znaleziony: {text[:50]}... -> {full_url}")

                    # Jeśli znaleźliśmy linki PDF, skończ szukanie
                    if found_links and pattern['type'] in ['pdf_direct', 'ksiazka', 'stenointr']:
                        self.logger.info(f"Znaleziono {len(found_links)} linków PDF, pomijam dalsze wzorce")
                        break

                # Przetwórz znalezione linki
                for full_url, text in found_links:
                    session_number = self._extract_session_number(text)
                    session_id = hashlib.md5(full_url.encode()).hexdigest()[:12]
                    date_found = self._extract_date(text) or self._try_extract_date_from_url(full_url)

                    sessions.append({
                        'id': session_id,
                        'number': session_number if session_number > 0 else len(sessions) + 1,
                        'title': text[:200],
                        'url': full_url,
                        'date': date_found or datetime.now().strftime('%Y-%m-%d')
                    })

                self.logger.info(
                    f"Z {search_url} znaleziono {len([s for s in sessions if s['url'].startswith(search_url) or search_url in s['url']])} linków")

            except Exception as e:
                self.logger.error(f"Błąd parsowania {search_url}: {e}")
                import traceback
                self.logger.debug(f"Pełny błąd: {traceback.format_exc()}")

        # Usuń duplikaty na podstawie URL
        unique_sessions = {}
        for session in sessions:
            unique_sessions[session['url']] = session

        sessions = list(unique_sessions.values())

        # Sortuj według daty/numeru
        sessions.sort(key=lambda x: (x['date'], x['number']), reverse=True)

        self.logger.info(f"Znaleziono łącznie {len(sessions)} unikalnych sesji")
        return sessions

    def _is_pdf_session_link(self, href: str, text: str) -> bool:
        """Sprawdza czy PDF link to stenogram posiedzenia"""
        href_lower = href.lower()
        text_lower = text.lower().strip()

        # Negatywne wzorce dla PDFów (nie chcemy np. regulaminów PDF)
        negative_patterns = [
            'regulamin', 'procedura', 'instrukcja', 'menu', 'nav',
            'statut', 'zarządzenie', 'uchwała', 'regulacja'
        ]

        for pattern in negative_patterns:
            if pattern in href_lower or pattern in text_lower:
                return False

        # Pozytywne wzorce dla PDFów stenogramów
        if 'ksiazka.pdf' in href_lower:  # ksiazka.pdf = stenogram
            return True

        if 'stenointr' in href_lower or 'stenogram' in href_lower:  # serwer stenogramów
            return True

        # Sprawdź czy tekst wygląda jak data posiedzenia
        if self._looks_like_date(text):
            return True

        # Sprawdź wzorce numeryczne
        import re
        if re.search(r'posiedzenie.*\d+', text_lower) or re.search(r'nr.*\d+', text_lower):
            return True

        return False

    def _should_skip_session(self, session_title: str) -> bool:
        """
        Sprawdza czy sesję należy pominąć (fotogalerie, zapowiedzi itp.)
        """
        title_lower = session_title.lower()

        # Wzorce do pomijania
        skip_patterns = [
            '[fotogaleria]',
            'fotogaleria',
            '(zapowiedź)',
            'zapowiedź',
            'spotkanie marszałka',
            'spotkanie wicemarszałek',
            'udział marszałka',
            'galeria zdjęć',
            'zdjęcia z',
            'foto:',
            'fotorelacja',
            'relacja fotograficzna'
        ]

        # Sprawdź czy tytuł zawiera któryś ze wzorców
        for pattern in skip_patterns:
            if pattern in title_lower:
                self.logger.info(f"⏭️  Pominam sesję (fotogaleria/zapowiedź): {session_title[:50]}...")
                return True

        # Sprawdź czy to bardzo krótki tekst (prawdopodobnie nie stenogram)
        if len(session_title.strip()) < 10:
            self.logger.info(f"⏭️  Pominam sesję (za krótki tytuł): {session_title}")
            return True

        return False

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
        Przetwarza pojedynczą sesję z filtrowaniem i PDF
        """
        session_id = session_data['id']

        if session_id in self.processed_sessions:
            self.logger.debug(f"Sesja {session_id} już przetworzona, pomijam")
            return None

        # NOWE: Sprawdź czy to nie fotogaleria/zapowiedź
        if self._should_skip_session(session_data['title']):
            return None

        self.logger.info(f"Przetwarzam sesję: {session_data['title']}")

        # Pobiera stronę sesji
        response = self._make_request(session_data['url'])
        if not response:
            return None

        # Sprawdź czy to bezpośredni link do PDF
        content_type = response.headers.get('content-type', '').lower()
        is_direct_pdf = 'application/pdf' in content_type or session_data['url'].endswith('.pdf')

        transcript_url = None
        file_type = 'html'

        if is_direct_pdf:
            # To jest bezpośredni PDF
            transcript_url = session_data['url']
            file_type = 'pdf'
            self.logger.info(f"Wykryto bezpośredni PDF: {transcript_url}")
        else:
            # Próbuje znaleźć link do transkryptu na stronie HTML
            soup = BeautifulSoup(response.text, 'html.parser')

            # Szuka linków do plików - POPRAWIONE WZORCE
            pdf_patterns = [
                'a[href*=".pdf"]',
                'a[href*="ksiazka"]',
                'a.pdf',
                'a[class*="pdf"]'
            ]

            for pattern in pdf_patterns:
                links = soup.select(pattern)
                for link in links:
                    href = link.get('href', '')
                    text = link.get_text(strip=True).lower()

                    # Sprawdź czy to stenogram
                    if any(word in text for word in ['stenogram', 'posiedzenie', 'księga', 'transkryp']):
                        transcript_url = urljoin(session_data['url'], href)
                        file_type = 'pdf' if href.endswith('.pdf') else 'html'
                        self.logger.info(f"Znaleziono link do PDF: {transcript_url}")
                        break

                if transcript_url:
                    break

            # Jeśli nie znaleziono PDF, sprawdź tradycyjne wzorce HTML
            if not transcript_url:
                for link in soup.find_all('a', href=True):
                    href = link['href']
                    text = link.get_text(strip=True).lower()

                    if any(pattern in text for pattern in self.config.transcript_patterns):
                        if href.endswith('.pdf'):
                            file_type = 'pdf'
                        elif href.endswith('.docx') or href.endswith('.doc'):
                            file_type = 'docx'

                        transcript_url = urljoin(session_data['url'], href)
                        break

        # Jeśli nie znaleziono osobnego linku, użyj tej samej strony
        if not transcript_url:
            transcript_url = session_data['url']
            file_type = 'html'

        # Tworzy obiekt sesji
        session = SejmSession(
            session_id=session_id,
            session_number=session_data['number'],
            date=session_data['date'],
            title=session_data['title'],
            url=session_data['url'],
            transcript_url=transcript_url,
            file_type=file_type,
            scraped_at=datetime.now().isoformat()
        )

        # Pobiera i parsuje treść + zachowuje PDF
        text_content = ""
        pdf_bytes = b""

        try:
            if file_type == 'html':
                # HTML
                if transcript_url == session_data['url']:
                    text_content = self._extract_text_from_html(response.text)
                else:
                    transcript_response = self._make_request(transcript_url)
                    if transcript_response:
                        text_content = self._extract_text_from_html(transcript_response.text)

            elif file_type in ['pdf', 'docx']:
                # NOWE: Pobiera plik i zwraca tekst + oryginalne bajty
                text_content, pdf_bytes = self._download_and_parse_file(
                    transcript_url, file_type, session_id
                )

        except Exception as e:
            self.logger.error(f"Błąd pobierania treści dla sesji {session_id}: {e}")
            return None

        # Sprawdź czy mamy sensowną treść
        if text_content and len(text_content.strip()) > 100:
            session.transcript_text = text_content
            session.hash = hashlib.md5(text_content.encode()).hexdigest()

            # NOWE: Zapisz w obu formatach
            if self._save_session_with_pdf(session, pdf_bytes):
                self._save_processed_session(session_id)

                self.logger.info(f"✅ Pomyślnie przetworzono sesję {session_id}, tekst: {len(text_content)} znaków")
                return session
            else:
                self.logger.error(f"❌ Błąd zapisu sesji {session_id}")
                return None
        else:
            self.logger.warning(f"⚠️  Brak treści lub treść za krótka dla sesji {session_id}")
            return None

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

    def _save_session_with_pdf(self, session: SejmSession, pdf_bytes: bytes = None):
        """
        Zapisuje sesję w JSON + opcjonalnie oryginalny PDF
        """
        year = session.date[:4] if session.date and len(session.date) >= 4 else str(date.today().year)
        year_dir = self.config.output_dir / year
        year_dir.mkdir(exist_ok=True)

        # Katalogi dla różnych formatów
        json_dir = year_dir / "json"
        pdf_dir = year_dir / "pdf"
        json_dir.mkdir(exist_ok=True)
        pdf_dir.mkdir(exist_ok=True)

        base_filename = f"posiedzenie_{session.session_number:03d}_{session.session_id}"

        # 1. Zapisz JSON (jak dotychczas)
        json_filepath = json_dir / f"{base_filename}.json"

        try:
            session_data = asdict(session)
            session_data['text_length'] = len(session.transcript_text) if session.transcript_text else 0
            session_data['word_count'] = len(session.transcript_text.split()) if session.transcript_text else 0

            # Dodaj info o PDF
            if pdf_bytes:
                session_data['original_pdf_available'] = True
                session_data['pdf_size_bytes'] = len(pdf_bytes)
            else:
                session_data['original_pdf_available'] = False

            with open(json_filepath, 'w', encoding='utf-8') as f:
                json.dump(session_data, f, ensure_ascii=False, indent=2)

            self.logger.info(f"💾 JSON: {json_filepath} ({session_data['text_length']} znaków)")

        except Exception as e:
            self.logger.error(f"❌ Błąd zapisu JSON {session.session_id}: {e}")
            return False

        # 2. Zapisz oryginalny PDF (jeśli dostępny)
        if pdf_bytes and len(pdf_bytes) > 1000:  # Sprawdź czy to sensowny PDF
            pdf_filepath = pdf_dir / f"{base_filename}.pdf"

            try:
                with open(pdf_filepath, 'wb') as f:
                    f.write(pdf_bytes)

                self.logger.info(f"📄 PDF: {pdf_filepath} ({len(pdf_bytes)} bajtów)")

            except Exception as e:
                self.logger.error(f"❌ Błąd zapisu PDF {session.session_id}: {e}")

        return True

    def cleanup_broken_sessions(self):
        """Czyści uszkodzone pliki JSON z surowym PDF"""
        broken_count = 0

        for json_file in self.config.output_dir.rglob("*.json"):
            if json_file.name == "processed_sessions.json":
                continue

            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                # Sprawdź czy zawiera binarne dane PDF
                transcript = data.get('transcript_text', '')
                if transcript and ('%PDF-' in transcript or '\u0000' in transcript):
                    self.logger.info(f"🧹 Usuwam uszkodzony plik: {json_file}")
                    json_file.unlink()

                    # Usuń z processed_sessions żeby ponownie przetworzyć
                    session_id = data.get('session_id')
                    if session_id in self.processed_sessions:
                        self.processed_sessions.remove(session_id)

                    broken_count += 1

            except Exception as e:
                self.logger.warning(f"Nie można sprawdzić pliku {json_file}: {e}")

        if broken_count > 0:
            # Zapisz zaktualizowaną listę processed_sessions
            self._save_processed_session("")  # Zapisuje całą listę
            self.logger.info(f"🧹 Wyczyszczono {broken_count} uszkodzonych plików")

        return broken_count

    def run(self) -> int:
        """Główna pętla bota"""
        print("🏛️  SejmBot - Parser transkryptów Sejmu RP")
        print("=" * 50)
        self.logger.info("🚀 Uruchomiono SejmBot")

        total_processed = 0

        for base_url in self.config.base_urls:
            self.logger.info(f"Przeszukuję: {base_url}")

            # Znajduje linki do sesji
            session_links = self._find_session_links(base_url)

            for session_data in session_links:
                try:
                    result = self._process_session(session_data)
                    if result:
                        total_processed += 1
                        self.logger.info(f"✅ Przetworzona sesja: {result.title}")

                except Exception as e:
                    self.logger.error(f"Błąd przetwarzania sesji {session_data.get('title', 'unknown')}: {e}")

        self.logger.info(f"🎉 Zakończono. Przetworzono {total_processed} nowych sesji")
        return total_processed


def main():
    """Punkt wejścia programu"""

    # Inicjalizacja
    config = SejmBotConfig()
    bot = SejmBot(config)

    try:
        # Uruchomienie
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
