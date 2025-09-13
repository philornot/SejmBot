# core/exceptions.py
"""
Własne wyjątki dla SejmBotScraper
"""

from typing import Optional, Dict, Any


class SejmScraperError(Exception):
    """Bazowy wyjątek dla wszystkich błędów SejmBotScraper"""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)

    def __str__(self):
        if self.details:
            return f"{self.message} (szczegóły: {self.details})"
        return self.message


# === BŁĘDY API ===

class APIError(SejmScraperError):
    """Błąd komunikacji z API"""
    pass


class APITimeoutError(APIError):
    """Timeout połączenia z API"""
    pass


class APIRateLimitError(APIError):
    """Przekroczono limit zapytań API"""
    pass


class APIResponseError(APIError):
    """Nieprawidłowa odpowiedź API"""

    def __init__(self, message: str, status_code: Optional[int] = None,
                 response_text: Optional[str] = None, **kwargs):
        details = kwargs.get('details', {})
        details.update({
            'status_code': status_code,
            'response_text': response_text
        })
        super().__init__(message, details)


class APIDataError(APIError):
    """Błąd w strukturze danych z API"""
    pass


# === BŁĘDY CACHE ===

class CacheError(SejmScraperError):
    """Błąd cache"""
    pass


class CacheKeyError(CacheError):
    """Nieprawidłowy klucz cache"""
    pass


class CacheSerializationError(CacheError):
    """Błąd serializacji/deserializacji cache"""
    pass


class CacheCorruptionError(CacheError):
    """Uszkodzony cache"""
    pass


class CacheExpiredError(CacheError):
    """Cache wygasł"""
    pass


# === BŁĘDY PLIKÓW ===

class FileError(SejmScraperError):
    """Błąd operacji na plikach"""
    pass


class FileNotFoundError(FileError):
    """Plik nie został znaleziony"""
    pass


class FilePermissionError(FileError):
    """Brak uprawnień do pliku"""
    pass


class FileCorruptionError(FileError):
    """Uszkodzony plik"""
    pass


class DirectoryError(FileError):
    """Błąd katalogów"""
    pass


# === BŁĘDY KONFIGURACJI ===

class ConfigError(SejmScraperError):
    """Błąd konfiguracji"""
    pass


class ConfigValidationError(ConfigError):
    """Błąd walidacji konfiguracji"""
    pass


class ConfigMissingError(ConfigError):
    """Brakująca konfiguracja"""
    pass


# === BŁĘDY SCRAPOWANIA ===

class ScrapingError(SejmScraperError):
    """Błąd scrapowania"""
    pass


class ScrapingValidationError(ScrapingError):
    """Błąd walidacji danych podczas scrapowania"""
    pass


class ScrapingInterruptedError(ScrapingError):
    """Scrapowanie zostało przerwane"""
    pass


class ScrapingResourceError(ScrapingError):
    """Błąd zasobów podczas scrapowania"""
    pass


# === BŁĘDY PRZETWARZANIA DANYCH ===

class DataProcessingError(SejmScraperError):
    """Błąd przetwarzania danych"""
    pass


class DataValidationError(DataProcessingError):
    """Błąd walidacji danych"""

    def __init__(self, message: str, validation_errors: Optional[list] = None, **kwargs):
        details = kwargs.get('details', {})
        details['validation_errors'] = validation_errors or []
        super().__init__(message, details)


class DataEnrichmentError(DataProcessingError):
    """Błąd wzbogacania danych"""
    pass


class DataSerializationError(DataProcessingError):
    """Błąd serializacji danych"""
    pass


# === BŁĘDY LOGIKI BIZNESOWEJ ===

class TermNotFoundError(SejmScraperError):
    """Kadencja nie została znaleziona"""

    def __init__(self, term: int):
        self.term = term
        super().__init__(f"Kadencja {term} nie została znaleziona")


class ProceedingNotFoundError(SejmScraperError):
    """Posiedzenie nie zostało znalezione"""

    def __init__(self, term: int, proceeding: int):
        self.term = term
        self.proceeding = proceeding
        super().__init__(f"Posiedzenie {proceeding} w kadencji {term} nie zostało znalezione")


class MPNotFoundError(SejmScraperError):
    """Poseł nie został znaleziony"""

    def __init__(self, mp_id: int, term: int):
        self.mp_id = mp_id
        self.term = term
        super().__init__(f"Poseł ID {mp_id} w kadencji {term} nie został znaleziony")


class FutureProceedingError(SejmScraperError):
    """Próba scrapowania przyszłego posiedzenia"""

    def __init__(self, proceeding: int, dates: list):
        self.proceeding = proceeding
        self.dates = dates
        super().__init__(f"Posiedzenie {proceeding} jest w przyszłości (daty: {dates})")


# === FUNKCJE POMOCNICZE ===

def handle_api_response(response, url: str):
    """
    Obsługuje odpowiedź API i rzuca odpowiednie wyjątki

    Args:
        response: obiekt Response z requests
        url: URL zapytania

    Raises:
        APIResponseError: dla błędnych kodów odpowiedzi
        APITimeoutError: dla timeoutów
    """
    if response.status_code == 403:
        raise APIResponseError(
            f"Dostęp zabroniony (403) dla {url}",
            status_code=403,
            response_text=response.text[:200]
        )
    elif response.status_code == 404:
        raise APIResponseError(
            f"Zasób nie znaleziony (404) dla {url}",
            status_code=404,
            response_text=response.text[:200]
        )
    elif response.status_code == 429:
        raise APIRateLimitError(
            f"Przekroczono limit zapytań (429) dla {url}",
            details={'status_code': 429, 'url': url}
        )
    elif response.status_code >= 500:
        raise APIResponseError(
            f"Błąd serwera ({response.status_code}) dla {url}",
            status_code=response.status_code,
            response_text=response.text[:200]
        )
    elif not response.ok:
        raise APIResponseError(
            f"Nieprawidłowa odpowiedź ({response.status_code}) dla {url}",
            status_code=response.status_code,
            response_text=response.text[:200]
        )


def validate_term(term: int) -> None:
    """
    Waliduje numer kadencji

    Args:
        term: numer kadencji

    Raises:
        ConfigValidationError: dla nieprawidłowego numeru kadencji
    """
    if not isinstance(term, int) or term < 1 or term > 20:
        raise ConfigValidationError(f"Nieprawidłowy numer kadencji: {term} (oczekiwano 1-20)")


def validate_proceeding(proceeding: int) -> None:
    """
    Waliduje numer posiedzenia

    Args:
        proceeding: numer posiedzenia

    Raises:
        ConfigValidationError: dla nieprawidłowego numeru posiedzenia
    """
    if not isinstance(proceeding, int) or proceeding < 1 or proceeding > 200:
        raise ConfigValidationError(f"Nieprawidłowy numer posiedzenia: {proceeding} (oczekiwano 1-200)")


def validate_date_format(date: str) -> None:
    """
    Waliduje format daty

    Args:
        date: data w formacie YYYY-MM-DD

    Raises:
        ConfigValidationError: dla nieprawidłowego formatu daty
    """
    import re
    from datetime import datetime

    if not isinstance(date, str):
        raise ConfigValidationError(f"Data musi być stringiem, otrzymano {type(date)}")

    date_pattern = r'^\d{4}-\d{2}-\d{2}$'
    if not re.match(date_pattern, date):
        raise ConfigValidationError(f"Nieprawidłowy format daty: {date} (oczekiwano YYYY-MM-DD)")

    try:
        datetime.strptime(date, '%Y-%m-%d')
    except ValueError as e:
        raise ConfigValidationError(f"Nieprawidłowa data: {date} ({e})")


def create_error_context(operation: str, **context) -> Dict[str, Any]:
    """
    Tworzy kontekst błędu dla lepszego debugowania

    Args:
        operation: nazwa operacji
        **context: dodatkowe informacje kontekstowe

    Returns:
        Słownik z kontekstem błędu
    """
    import traceback
    from datetime import datetime

    return {
        'operation': operation,
        'timestamp': datetime.now().isoformat(),
        'traceback': traceback.format_exc(),
        **context
    }
