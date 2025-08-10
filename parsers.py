#!/usr/bin/env python3
"""
SejmBot - parsers.py
Moduły do parsowania i ekstrakcji tekstu z różnych formatów dokumentów
"""

import io
import logging
import os
import re
import tempfile

from bs4 import BeautifulSoup

# Importy opcjonalne - sprawdzamy dostępność bibliotek
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


class HTMLParser:
    """Parser dla stron HTML z transkryptami"""

    def __init__(self, logger: logging.Logger):
        self.logger = logger

    def extract_text(self, html_content: str) -> str:
        """Ekstraktuje tekst z HTML"""
        if not html_content:
            return ""

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
        cleaned_text = TextCleaner.clean_extracted_text(text_content)

        self.logger.debug(f"HTML -> tekst: {len(cleaned_text)} znaków")
        return cleaned_text


class PDFParser:
    """Parser dla dokumentów PDF"""

    def __init__(self, logger: logging.Logger):
        self.logger = logger

        if not PDF_SUPPORT:
            self.logger.warning("⚠️  Brak wsparcia dla PDF - zainstaluj: pip install pdfplumber")

    def extract_text_from_bytes(self, pdf_bytes: bytes) -> str:
        """Ekstraktuje tekst z PDF z bajtów z obsługą różnych problemów"""
        if not PDF_SUPPORT:
            self.logger.error("❌ Brak wsparcia dla PDF - zainstaluj: pip install pdfplumber")
            return ""

        if not pdf_bytes or len(pdf_bytes) < 100:
            self.logger.error("❌ PDF jest pusty lub uszkodzony")
            return ""

        try:
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
            cleaned_text = TextCleaner.clean_extracted_text(full_text)

            self.logger.info(f"✅ Wyciągnięto {len(cleaned_text):,} znaków z PDF")
            return cleaned_text

        except Exception as e:
            self.logger.error(f"❌ Błąd parsowania PDF: {e}")
            return ""


class DOCXParser:
    """Parser dla dokumentów DOCX"""

    def __init__(self, logger: logging.Logger):
        self.logger = logger

        if not DOCX_SUPPORT:
            self.logger.warning("⚠️  Brak wsparcia dla DOCX - zainstaluj: pip install docx2txt")

    def extract_text_from_bytes(self, docx_bytes: bytes) -> str:
        """Ekstraktuje tekst z DOCX z bajtów"""
        if not DOCX_SUPPORT:
            self.logger.error("❌ Brak wsparcia dla DOCX - zainstaluj: pip install docx2txt")
            return ""

        try:
            # docx2txt wymaga pliku na dysku
            with tempfile.NamedTemporaryFile(suffix='.docx', delete=False) as tmp_file:
                tmp_file.write(docx_bytes)
                tmp_file_path = tmp_file.name

            try:
                text = docx2txt.process(tmp_file_path)
                cleaned_text = TextCleaner.clean_extracted_text(text) if text else ""

                self.logger.info(f"✅ Wyciągnięto {len(cleaned_text):,} znaków z DOCX")
                return cleaned_text

            finally:
                # Usuń plik tymczasowy
                try:
                    os.unlink(tmp_file_path)
                except:
                    pass

        except Exception as e:
            self.logger.error(f"❌ Błąd parsowania DOCX z bajtów: {e}")
            return ""

    def extract_text_from_file(self, file_path: str) -> str:
        """Ekstraktuje tekst z pliku DOCX na dysku"""
        if not DOCX_SUPPORT:
            self.logger.error("❌ Brak wsparcia dla DOCX - zainstaluj docx2txt")
            return ""

        try:
            text = docx2txt.process(file_path)
            cleaned_text = TextCleaner.clean_extracted_text(text) if text else ""

            self.logger.info(f"✅ Wyciągnięto {len(cleaned_text):,} znaków z DOCX")
            return cleaned_text

        except Exception as e:
            self.logger.error(f"❌ Błąd parsowania DOCX {file_path}: {e}")
            return ""


class TextCleaner:
    """Klasa statyczna do czyszczenia i normalizacji tekstu"""

    @staticmethod
    def clean_extracted_text(text: str) -> str:
        """
        Czyści wyciągnięty tekst z PDF/HTML/DOCX
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

        # Normalizuj polskie znaki i typografię
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

    @staticmethod
    def normalize_polish_text(text: str) -> str:
        """Normalizuje polski tekst dla lepszej analizy"""
        if not text:
            return ""

        # Zamień typowe skróty parlamentarne na pełne formy
        replacements = {
            r'\bp\.\s*pos\.': 'pan poseł',
            r'\bp\.\s*pos\.\s*': 'pani posłanka',
            r'\bmin\.': 'minister',
            r'\bmarszałek\s+sejmu': 'marszałek Sejmu',
            r'\bwicemarszałek': 'wicemarszałek',
            r'\br\.m\.': 'rada ministrów',
        }

        for pattern, replacement in replacements.items():
            text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)

        return text


class TextValidator:
    """Walidator jakości wyciągniętego tekstu"""

    def __init__(self, logger: logging.Logger):
        self.logger = logger

    def validate_stenogram_text(self, text: str, source_url: str = "") -> bool:
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
                f"⚠️  Tekst może nie być stenogramem - znaleziono tylko {found_keywords} kluczowych słów"
            )
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
            f"✅ Tekst przeszedł walidację: {len(text):,} znaków, "
            f"{found_keywords} kluczowych słów, {meaningful_ratio:.1%} sensownych słów"
        )
        return True

    def detect_encoding_issues(self, text: str) -> bool:
        """Wykrywa problemy z kodowaniem tekstu"""
        if not text:
            return False

        # Sprawdź problematyczne znaki
        problematic_chars = [
            '\ufffd',  # replacement character
            '\x00',  # null bytes
            '\x01',  # control characters
        ]

        for char in problematic_chars:
            if char in text:
                self.logger.warning(f"⚠️  Wykryto problematyczny znak w tekście: {repr(char)}")
                return True

        # Sprawdź czy można zakodować do UTF-8
        try:
            text.encode('utf-8')
            return False
        except UnicodeEncodeError as e:
            self.logger.warning(f"⚠️  Błąd kodowania UTF-8: {e}")
            return True


class ContentTypeDetector:
    """Wykrywa typ zawartości pliku"""

    def __init__(self, logger: logging.Logger):
        self.logger = logger

    def detect_from_bytes(self, content_bytes: bytes, url: str = "", content_type: str = "") -> str:
        """
        Wykrywa typ pliku na podstawie jego zawartości
        Zwraca: 'pdf', 'docx', 'html', 'unknown'
        """
        if not content_bytes:
            return "unknown"

        # Sprawdź pierwsze bajty (magic numbers)
        if content_bytes.startswith(b'%PDF-'):
            self.logger.debug("Wykryto PDF na podstawie magic number")
            return "pdf"

        # DOCX to ZIP z określoną strukturą
        if content_bytes.startswith(b'PK\x03\x04'):
            # Sprawdź czy to DOCX (zawiera word/ folder)
            try:
                if b'word/' in content_bytes[:2048]:
                    self.logger.debug("Wykryto DOCX na podstawie struktury ZIP")
                    return "docx"
            except:
                pass

        # HTML - sprawdź czy zawiera tagi HTML
        try:
            text_start = content_bytes[:2048].decode('utf-8', errors='ignore').lower()
            if any(tag in text_start for tag in ['<html', '<head', '<body', '<!doctype']):
                self.logger.debug("Wykryto HTML na podstawie tagów")
                return "html"
        except:
            pass

        # Fallback na podstawie URL i content-type
        if url:
            if url.lower().endswith('.pdf'):
                return "pdf"
            elif url.lower().endswith(('.docx', '.doc')):
                return "docx"
            elif url.lower().endswith(('.html', '.htm')):
                return "html"

        if content_type:
            if 'pdf' in content_type.lower():
                return "pdf"
            elif 'officedocument' in content_type.lower() or 'docx' in content_type.lower():
                return "docx"
            elif 'html' in content_type.lower():
                return "html"

        self.logger.warning(f"⚠️  Nie można wykryć typu pliku dla URL: {url[:60]}")
        return "unknown"


class UniversalParser:
    """Uniwersalny parser łączący wszystkie typy dokumentów"""

    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self.html_parser = HTMLParser(logger)
        self.pdf_parser = PDFParser(logger)
        self.docx_parser = DOCXParser(logger)
        self.detector = ContentTypeDetector(logger)
        self.validator = TextValidator(logger)

    def parse_content(self, content_bytes: bytes, url: str = "", content_type: str = "") -> tuple[str, str]:
        """
        Uniwersalne parsowanie zawartości
        Zwraca: (extracted_text, detected_file_type)
        """
        if not content_bytes:
            self.logger.error("❌ Brak danych do parsowania")
            return "", "unknown"

        # Wykryj typ pliku
        file_type = self.detector.detect_from_bytes(content_bytes, url, content_type)

        self.logger.info(f"🔍 Wykryto typ pliku: {file_type} dla URL: {url[:60]}...")

        # Parsuj według typu
        text = ""

        if file_type == "pdf":
            text = self.pdf_parser.extract_text_from_bytes(content_bytes)

        elif file_type == "docx":
            text = self.docx_parser.extract_text_from_bytes(content_bytes)

        elif file_type == "html":
            try:
                html_content = content_bytes.decode('utf-8', errors='replace')
                text = self.html_parser.extract_text(html_content)
            except Exception as e:
                self.logger.error(f"❌ Błąd dekodowania HTML: {e}")
                return "", file_type

        else:
            # Próba dekodowania jako tekst
            try:
                text = content_bytes.decode('utf-8', errors='replace')
                text = TextCleaner.clean_extracted_text(text)
                self.logger.info("📝 Przetworzono jako zwykły tekst")
            except Exception as e:
                self.logger.error(f"❌ Nie można zdekodować zawartości: {e}")
                return "", "unknown"

        # Walidacja jakości tekstu
        if text and not self.validator.validate_stenogram_text(text, url):
            self.logger.warning(f"⚠️  Tekst nie przeszedł walidacji jakości")

        return text, file_type


class ParsingManager:
    """Manager zarządzający wszystkimi parserami"""

    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self.universal_parser = UniversalParser(logger)

        # Sprawdź dostępność bibliotek
        self._check_dependencies()

    def _check_dependencies(self):
        """Sprawdza dostępność bibliotek parsujących"""
        missing = []

        if not PDF_SUPPORT:
            missing.append("pdfplumber (dla PDF)")

        if not DOCX_SUPPORT:
            missing.append("docx2txt (dla DOCX)")

        if missing:
            self.logger.warning(f"⚠️  Brakujące biblioteki: {', '.join(missing)}")
            self.logger.info("💡 Zainstaluj: pip install pdfplumber docx2txt")
        else:
            self.logger.info("✅ Wszystkie biblioteki parsujące dostępne")

    def parse_file_content(self, content_bytes: bytes, url: str = "",
                           expected_type: str = "") -> tuple[str, str]:
        """
        Główna metoda parsowania - deleguje do odpowiedniego parsera

        Args:
            content_bytes: Zawartość pliku w bajtach
            url: URL źródłowy (dla kontekstu)
            expected_type: Oczekiwany typ pliku ('pdf', 'docx', 'html')

        Returns:
            tuple[str, str]: (extracted_text, actual_file_type)
        """
        return self.universal_parser.parse_content(content_bytes, url, expected_type)

    def validate_text_quality(self, text: str, source_url: str = "") -> bool:
        """Waliduje jakość wyciągniętego tekstu"""
        return self.validator.validate_stenogram_text(text, source_url)

    def get_parsing_stats(self) -> dict:
        """Zwraca statystyki dostępności parserów"""
        return {
            'pdf_support': PDF_SUPPORT,
            'docx_support': DOCX_SUPPORT,
            'html_support': True,  # BeautifulSoup zawsze dostępne
            'missing_dependencies': self._get_missing_dependencies()
        }

    def _get_missing_dependencies(self) -> list:
        """Zwraca listę brakujących zależności"""
        missing = []

        if not PDF_SUPPORT:
            missing.append("pdfplumber")

        if not DOCX_SUPPORT:
            missing.append("docx2txt")

        return missing
