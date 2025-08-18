"""
Moduł do obsługi plików PDF z transkryptami Sejmu
"""
import pypdf
from SejmBotDetektor.logging.logger import get_module_logger

class PDFProcessor:
    """Klasa do przetwarzania plików PDF"""

    def __init__(self, debug: bool = False):
        self.debug = debug
        self.logger = get_module_logger("PDFProcessor")

    def extract_text_from_pdf(self, pdf_path: str) -> str:
        """
        Wyciąga tekst z pliku PDF

        Args:
            pdf_path: Ścieżka do pliku PDF

        Returns:
            Wyciągnięty tekst lub pusty string w przypadku błędu
        """
        try:
            if self.debug:
                self.logger.debug(f"Otwieranie pliku PDF: {pdf_path}")

            with open(pdf_path, 'rb') as file:
                pdf_reader = pypdf.PdfReader(file)
                text = ""

                if self.debug:
                    self.logger.debug(f"Plik PDF ma {len(pdf_reader.pages)} stron")

                for page_num, page in enumerate(pdf_reader.pages):
                    page_text = page.extract_text()
                    text += page_text + "\n"

                    if self.debug and page_num < 3:  # Debugujemy tylko pierwsze 3 strony
                        self.logger.debug(f"Strona {page_num + 1}: {len(page_text)} znaków")

                if self.debug:
                    self.logger.debug(f"Łącznie wyciągnięto {len(text)} znaków")

                return text

        except FileNotFoundError:
            error_msg = f"Plik {pdf_path} nie został znaleziony"
            self.logger.error(error_msg)
            return ""

        except pypdf.errors.PdfReadError as e:
            error_msg = f"Błąd podczas czytania PDF: {e}"
            self.logger.error(error_msg)
            return ""

        except Exception as e:
            error_msg = f"Nieoczekiwany błąd podczas czytania PDF: {e}"
            self.logger.error(error_msg)
            return ""

    def validate_pdf_file(self, pdf_path: str) -> tuple[bool, str]:
        """
        Sprawdza czy plik PDF jest prawidłowy i można go odczytać

        Args:
            pdf_path: Ścieżka do pliku PDF

        Returns:
            Tuple (czy_prawidłowy, komunikat)
        """
        try:
            with open(pdf_path, 'rb') as file:
                pdf_reader = pypdf.PdfReader(file)

                if len(pdf_reader.pages) == 0:
                    return False, "Plik PDF nie zawiera żadnych stron"

                # Próbujemy wyciągnąć tekst z pierwszej strony
                first_page_text = pdf_reader.pages[0].extract_text()

                if len(first_page_text.strip()) == 0:
                    return False, "Nie można wyciągnąć tekstu z pliku PDF"

                if self.debug:
                    self.logger.debug(f"Plik PDF jest prawidłowy - {len(pdf_reader.pages)} stron")

                return True, "Plik PDF jest prawidłowy"

        except FileNotFoundError:
            return False, f"Plik {pdf_path} nie został znaleziony"
        except pypdf.errors.PdfReadError as e:
            return False, f"Błąd formatu PDF: {e}"
        except Exception as e:
            return False, f"Nieoczekiwany błąd: {e}"

    def get_pdf_metadata(self, pdf_path: str) -> dict:
        """
        Wyciąga metadane z pliku PDF

        Args:
            pdf_path: Ścieżka do pliku PDF

        Returns:
            Słownik z metadanymi
        """
        metadata = {
            'pages': 0,
            'title': None,
            'author': None,
            'subject': None,
            'creator': None,
            'producer': None,
            'creation_date': None,
            'modification_date': None
        }

        try:
            with open(pdf_path, 'rb') as file:
                pdf_reader = pypdf.PdfReader(file)

                metadata['pages'] = len(pdf_reader.pages)

                if pdf_reader.metadata:
                    pdf_metadata = pdf_reader.metadata
                    metadata['title'] = pdf_metadata.get('/Title')
                    metadata['author'] = pdf_metadata.get('/Author')
                    metadata['subject'] = pdf_metadata.get('/Subject')
                    metadata['creator'] = pdf_metadata.get('/Creator')
                    metadata['producer'] = pdf_metadata.get('/Producer')
                    metadata['creation_date'] = pdf_metadata.get('/CreationDate')
                    metadata['modification_date'] = pdf_metadata.get('/ModDate')

                if self.debug:
                    self.logger.debug(f"Metadane PDF: {metadata}")

        except Exception as e:
            if self.debug:
                self.logger.debug(f"Nie można wyciągnąć metadanych: {e}")

        return metadata
