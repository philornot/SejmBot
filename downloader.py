#!/usr/bin/env python3
"""
SejmBot - downloader.py
Moduł do pobierania plików z internetu z obsługą retry, alternative URLs i error handling
"""

import logging
import time
from typing import Optional, Tuple, List
from urllib.parse import urlparse

import requests
from requests.exceptions import RequestException, Timeout, ConnectionError


class FileDownloader:
    """Menedżer pobierania plików z zaawansowaną obsługą błędów"""

    def __init__(self, config, logger: logging.Logger):
        self.config = config
        self.logger = logger

        # Konfiguracja sesji HTTP
        self.session = requests.Session()
        self.session.headers.update(config.headers)

        # Dodaj User-Agent z konfiguracji
        self.session.headers['User-Agent'] = config.user_agent

    def download_file(self, url: str, **kwargs) -> Optional[requests.Response]:
        """
        Pobiera plik z obsługą retry, alternative URLs i lepszej obsługi błędów

        Args:
            url: URL do pobrania
            **kwargs: Dodatkowe parametry dla requests

        Returns:
            requests.Response lub None w przypadku błędu
        """
        # Przygotuj listę URLi do wypróbowania
        urls_to_try = self._prepare_alternative_urls(url)

        # Ustaw timeout w zależności od serwera
        timeout = self._get_optimal_timeout(url)
        kwargs.setdefault('timeout', timeout)

        # Próbuj każdy URL z retry
        for url_to_try in urls_to_try:
            response = self._try_download_with_retry(url_to_try, **kwargs)
            if response:
                if url_to_try != url:
                    self.logger.info(f"✅ Sukces z alternatywnym URL: {url_to_try}")
                return response

        self.logger.error(f"❌ Wszystkie próby pobierania nie powiodły się dla: {url}")
        return None

    def download_and_parse_text(self, url: str, file_type: str, session_id: str) -> Tuple[str, bytes]:
        """
        Pobiera plik i zwraca zarówno tekst jak i oryginalne bajty

        Args:
            url: URL do pobrania
            file_type: typ pliku ('pdf', 'docx', 'html')
            session_id: ID sesji dla logowania

        Returns:
            Tuple[tekst, bajty_pliku]
        """
        try:
            self.logger.info(f"📥 Pobieranie {file_type.upper()}: {url}")

            response = self.download_file(url)
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

            # Parsuj zawartość w zależności od typu
            if file_type == 'pdf':
                return self._parse_pdf_bytes(file_bytes, url), file_bytes
            elif file_type == 'docx':
                return self._parse_docx_bytes(file_bytes, url), file_bytes
            else:  # HTML lub inne
                return self._parse_html_text(response.text), response.content

        except Exception as e:
            self.logger.error(f"❌ Błąd pobierania/parsowania pliku {url}: {e}")
            return "", b""

    def _prepare_alternative_urls(self, original_url: str) -> List[str]:
        """Przygotowuje listę alternatywnych URLi do wypróbowania"""
        urls = [original_url]

        # Specjalne przypadki dla problematycznego serwera orka2.sejm.gov.pl
        if 'orka2.sejm.gov.pl' in original_url:
            # Spróbuj HTTPS zamiast HTTP
            if original_url.startswith('http://'):
                https_url = original_url.replace('http://', 'https://')
                urls.append(https_url)
                self.logger.debug(f"Dodano alternatywny HTTPS URL: {https_url}")

            # Spróbuj inne serwery Sejmu (jeśli istnieją)
            alternative_servers = [
                'orka.sejm.gov.pl',
                'www.sejm.gov.pl'
            ]

            parsed_url = urlparse(original_url)
            for alt_server in alternative_servers:
                alt_url = original_url.replace(parsed_url.netloc, alt_server)
                if alt_url != original_url and alt_url not in urls:
                    urls.append(alt_url)
                    self.logger.debug(f"Dodano alternatywny serwer: {alt_url}")

        return urls

    def _get_optimal_timeout(self, url: str) -> int:
        """Zwraca optymalny timeout dla danego serwera"""
        if 'orka2.sejm.gov.pl' in url:
            # Problematyczny serwer - zwiększony timeout
            return 60
        elif '.gov.pl' in url:
            # Inne serwery rządowe - średni timeout
            return 45
        else:
            # Standardowy timeout
            return self.config.timeout

    def _try_download_with_retry(self, url: str, **kwargs) -> Optional[requests.Response]:
        """Próbuje pobrać URL z mechanizmem retry"""

        for attempt in range(self.config.max_retries):
            try:
                # Opóźnienie między zapytaniami
                if attempt > 0:
                    wait_time = min(2 ** attempt, 10)  # Exponential backoff, max 10s
                    self.logger.info(f"⏱️  Czekam {wait_time}s przed próbą {attempt + 1}...")
                    time.sleep(wait_time)
                else:
                    time.sleep(self.config.delay_between_requests)

                self.logger.debug(f"Próba {attempt + 1}/{self.config.max_retries}: {url}")

                response = self.session.get(url, **kwargs)

                if response.status_code == 200:
                    self.logger.debug(f"✅ Sukces pobierania: {url}")
                    return response

                elif response.status_code == 403:
                    self.logger.warning(f"🚫 Dostęp zabroniony (403) dla URL: {url}")
                    break  # Nie próbuj ponownie dla 403

                elif response.status_code == 404:
                    self.logger.warning(f"❌ Nie znaleziono (404) dla URL: {url}")
                    break  # Nie próbuj ponownie dla 404

                elif response.status_code in [500, 502, 503, 504]:
                    self.logger.warning(
                        f"🔧 Błąd serwera ({response.status_code}) dla URL: {url} - próba {attempt + 1}"
                    )
                    # Kontynuuj retry dla błędów serwera

                else:
                    self.logger.warning(f"⚠️  HTTP {response.status_code} dla URL: {url}")
                    if attempt < self.config.max_retries - 1:
                        continue
                    else:
                        break

            except Timeout as e:
                self.logger.warning(
                    f"⏱️  Timeout (próba {attempt + 1}/{self.config.max_retries}) dla {url}: {e}"
                )
                if attempt == self.config.max_retries - 1:
                    self.logger.error(f"❌ Przekroczono maksymalną liczbę prób dla {url}")

            except ConnectionError as e:
                self.logger.warning(
                    f"🌐 Błąd połączenia (próba {attempt + 1}/{self.config.max_retries}) dla {url}: {e}"
                )
                if attempt == self.config.max_retries - 1:
                    self.logger.error(f"❌ Problemy z połączeniem dla {url}")

            except RequestException as e:
                self.logger.warning(
                    f"🔌 Błąd zapytania (próba {attempt + 1}/{self.config.max_retries}): {e}"
                )
                if attempt == self.config.max_retries - 1:
                    self.logger.error(f"❌ Wszystkie próby nie powiodły się")

        self.logger.error(f"❌ Wszystkie próby pobierania nie powiodły się dla: {url}")
        return None

    def _parse_pdf_bytes(self, pdf_bytes: bytes, source_url: str) -> str:
        """Ekstraktuje tekst z PDF z bajtów używając pypdf"""
        try:
            import pypdf
            import io

            if not pdf_bytes or len(pdf_bytes) < 100:
                self.logger.error("❌ PDF jest pusty lub uszkodzony")
                return ""

            if not pdf_bytes.startswith(b'%PDF-'):
                self.logger.error("❌ Plik nie jest prawidłowym PDF")
                return ""

            pdf_stream = io.BytesIO(pdf_bytes)
            text_parts = []

            # Używamy pypdf zamiast pdfplumber
            reader = pypdf.PdfReader(pdf_stream)
            total_pages = len(reader.pages)
            self.logger.info(f"📄 PDF ma {total_pages} stron")

            for page_num, page in enumerate(reader.pages, 1):  # Logika pętli pozostaje ta sama
                try:
                    page_text = page.extract_text()
                    if page_text:
                        text_parts.append(page_text)

                    if page_num % 50 == 0:
                        self.logger.info(f"📖 Przetworzono {page_num}/{total_pages} stron")

                except Exception as e:
                    self.logger.warning(f"⚠️  Błąd na stronie {page_num}: {e}")
                    continue

            full_text = '\n\n'.join(text_parts)
            cleaned_text = self._clean_extracted_text(full_text)

            self.logger.info(f"✅ Wyciągnięto {len(cleaned_text):,} znaków z PDF (pypdf)")
            return cleaned_text

        except ImportError:
            self.logger.error("❌ Brak wsparcia dla PDF - zainstaluj: pip install pypdf")
            return ""
        except Exception as e:
            self.logger.error(f"❌ Błąd parsowania PDF: {e}")
            return ""

    def _parse_docx_bytes(self, docx_bytes: bytes, source_url: str) -> str:
        """
        Ekstraktuje tekst z DOCX z bajtów — WYŁĄCZONE
        :deprecated: Ta funkcja jest przestarzała, obsługa DOCX została usunięta.
        """
        self.logger.warning("⚠️  Obsługa DOCX została wyłączona w tej wersji. Użyj PDF lub HTML.")
        return ""

    def _parse_html_text(self, html_content: str) -> str:
        """Ekstraktuje tekst z HTML"""
        try:
            from bs4 import BeautifulSoup

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
                'main', 'article', '.main-content', '.content', '#content',
                # Fallback
                'body'
            ]

            text_content = ""
            for selector in content_selectors:
                elements = soup.select(selector)
                if elements:
                    element = elements[0]
                    text_content = element.get_text(separator=' ', strip=True)
                    if len(text_content) > 200:
                        self.logger.debug(f"Użyto selektora: {selector}")
                        break

            # Jeśli nadal brak treści, weź cały tekst
            if not text_content or len(text_content) < 200:
                text_content = soup.get_text(separator=' ', strip=True)

            cleaned_text = self._clean_extracted_text(text_content)
            self.logger.info(f"✅ Wyciągnięto {len(cleaned_text):,} znaków z HTML")

            return cleaned_text

        except Exception as e:
            self.logger.error(f"❌ Błąd parsowania HTML: {e}")
            return ""

    def _clean_extracted_text(self, text: str) -> str:
        """Czyści wyciągnięty tekst z PDF/HTML"""
        if not text:
            return ""

        import re

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

    def validate_extracted_text(self, text: str, source_url: str) -> bool:
        """Waliduje czy wyciągnięty tekst jest sensowny stenogram Sejmu"""
        if not text or len(text.strip()) < 500:
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

        if found_keywords < 5:
            self.logger.warning(
                f"⚠️  Tekst może nie być stenogramem - znaleziono tylko {found_keywords} kluczowych słów")
            return False

        # Sprawdź jakość tekstu
        printable_ratio = sum(1 for c in text if c.isprintable() or c.isspace()) / len(text) if text else 0

        if printable_ratio < 0.9:
            self.logger.warning(f"⚠️  Tekst zawiera dużo nieprintable znaków ({printable_ratio:.2%})")
            return False

        # Sprawdź sensowność słów
        words = text.split()
        meaningful_words = sum(1 for word in words if len(word) > 2)
        meaningful_ratio = meaningful_words / len(words) if words else 0

        if meaningful_ratio < 0.7:
            self.logger.warning(f"⚠️  Tekst ma za mało sensownych słów ({meaningful_ratio:.2%})")
            return False

        self.logger.info(
            f"✅ Tekst przeszedł walidację: {len(text):,} znaków, {found_keywords} kluczowych słów")
        return True

    def close(self):
        """Zamyka sesję HTTP"""
        if hasattr(self, 'session'):
            self.session.close()
