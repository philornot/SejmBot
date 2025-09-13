# core/interfaces.py
"""
Definicje protokołów i interfejsów dla całej aplikacji
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Protocol, List, Dict, Optional, Any, Union

from .types import (
    TermInfo, ProceedingInfo, StatementInfo, MPInfo, ClubInfo,
    ScrapingStats, MPScrapingStats, CacheStats, ProcessedStatement,
    TranscriptData, FileCacheEntry, ProcessingResult,
    ValidationResult, JsonSerializable
)


# === PROTOKOŁY API ===

class APIClient(Protocol):
    """Protokół dla klientów API"""

    def get_terms(self) -> Optional[List[TermInfo]]:
        """Pobiera listę kadencji"""
        ...

    def get_term_info(self, term: int) -> Optional[TermInfo]:
        """Pobiera informacje o kadencji"""
        ...

    def get_proceedings(self, term: int) -> Optional[List[ProceedingInfo]]:
        """Pobiera listę posiedzeń"""
        ...

    def get_proceeding_info(self, term: int, proceeding_id: int) -> Optional[ProceedingInfo]:
        """Pobiera szczegóły posiedzenia"""
        ...

    def get_statements(self, term: int, proceeding: int, date: str) -> Optional[List[StatementInfo]]:
        """Pobiera wypowiedzi z danego dnia"""
        ...

    def get_statement_html(self, term: int, proceeding: int, date: str, statement_num: int) -> Optional[str]:
        """Pobiera HTML wypowiedzi"""
        ...

    def get_mps(self, term: int) -> Optional[List[MPInfo]]:
        """Pobiera listę posłów"""
        ...

    def get_mp_info(self, term: int, mp_id: int) -> Optional[MPInfo]:
        """Pobiera szczegóły posła"""
        ...

    def get_clubs(self, term: int) -> Optional[List[ClubInfo]]:
        """Pobiera listę klubów"""
        ...


# === PROTOKOŁY CACHE ===

class CacheManager(Protocol):
    """Protokół dla managerów cache"""

    def get(self, key: str) -> Optional[Any]:
        """Pobiera wartość z cache"""
        ...

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Zapisuje wartość do cache"""
        ...

    def has(self, key: str) -> bool:
        """Sprawdza, czy klucz istnieje w cache"""
        ...

    def delete(self, key: str) -> bool:
        """Usuwa klucz z cache"""
        ...

    def clear(self, pattern: Optional[str] = None) -> None:
        """Czyści cache (opcjonalnie według wzorca)"""
        ...

    def get_stats(self) -> CacheStats:
        """Zwraca statystyki cache"""
        ...


class FileCacheManager(Protocol):
    """Protokół dla cache'u plików"""

    def has_file_cache(self, filepath: Union[str, Path], check_content: bool = False) -> bool:
        """Sprawdza, czy plik istnieje w cache"""
        ...

    def get_file_cache(self, filepath: Union[str, Path]) -> Optional[FileCacheEntry]:
        """Pobiera metadane pliku z cache"""
        ...

    def set_file_cache(self, filepath: Union[str, Path], metadata: Dict[str, Any]) -> None:
        """Zapisuje metadane pliku do cache"""
        ...

    def cleanup_expired(self) -> int:
        """Czyści wygasłe wpisy, zwraca liczbę usuniętych"""
        ...


# === PROTOKOŁY ZARZĄDZANIA PLIKAMI ===

class FileManager(Protocol):
    """Protokół dla zarządzania plikami"""

    def save_json(self, path: Union[str, Path], data: JsonSerializable) -> bool:
        """Zapisuje dane JSON"""
        ...

    def load_json(self, path: Union[str, Path]) -> Optional[JsonSerializable]:
        """Ładuje dane JSON"""
        ...

    def ensure_directory(self, path: Union[str, Path]) -> bool:
        """Zapewnia istnienie katalogu"""
        ...

    def get_file_size(self, path: Union[str, Path]) -> Optional[int]:
        """Zwraca rozmiar pliku"""
        ...

    def file_exists(self, path: Union[str, Path]) -> bool:
        """Sprawdza, czy plik istnieje"""
        ...


class TranscriptFileManager(Protocol):
    """Protokół dla zarządzania plikami transkryptów"""

    def save_proceeding_transcripts(self, term: int, proceeding_id: int, date: str,
                                    statements_data: Dict, proceeding_info: Dict,
                                    full_statements: Optional[List[ProcessedStatement]] = None) -> Optional[str]:
        """Zapisuje transkrypty posiedzenia"""
        ...

    def load_transcript_file(self, filepath: str) -> Optional[TranscriptData]:
        """Ładuje plik transkryptu"""
        ...

    def get_existing_transcripts(self, term: int, proceeding_id: int, proceeding_info: Dict) -> List[str]:
        """Zwraca daty istniejących transkryptów"""
        ...

    def save_proceeding_info(self, term: int, proceeding_id: int, proceeding_info: Dict) -> Optional[str]:
        """Zapisuje informacje o posiedzeniu"""
        ...


# === PROTOKOŁY PRZETWARZANIA DANYCH ===

class DataProcessor(Protocol):
    """Protokół dla procesorów danych"""

    def process(self, data: Any) -> ProcessingResult:
        """Przetwarza dane"""
        ...

    def validate(self, data: Any) -> ValidationResult:
        """Waliduje dane"""
        ...


class StatementEnricher(Protocol):
    """Protokół dla wzbogacania wypowiedzi"""

    def enrich_with_mp_data(self, statements: List[ProcessedStatement], term: int) -> List[ProcessedStatement]:
        """Wzbogaca wypowiedzi o dane posłów"""
        ...

    def enrich_with_full_content(self, statements: List[ProcessedStatement],
                                 term: int, proceeding_id: int, date: str) -> List[ProcessedStatement]:
        """Wzbogaca wypowiedzi o pełną treść"""
        ...


# === PROTOKOŁY SCRAPOWANIA ===

class BaseScraper(Protocol):
    """Podstawowy protokół scrapera"""

    def scrape(self, **kwargs) -> Union[ScrapingStats, MPScrapingStats]:
        """Główna metoda scrapowania"""
        ...

    def get_stats(self) -> Union[ScrapingStats, MPScrapingStats]:
        """Zwraca statystyki"""
        ...

    def clear_cache(self) -> None:
        """Czyści cache scrapera"""
        ...


class TranscriptScraper(Protocol):
    """Protokół scrapera transkryptów"""

    def scrape_term(self, term: int, **options) -> ScrapingStats:
        """Scrapuje całą kadencję"""
        ...

    def scrape_proceeding(self, term: int, proceeding: int, **options) -> bool:
        """Scrapuje konkretne posiedzenie"""
        ...

    def get_available_terms(self) -> Optional[List[TermInfo]]:
        """Pobiera dostępne kadencje"""
        ...


class MPScraper(Protocol):
    """Protokół scrapera posłów"""

    def scrape_mps(self, term: int, **options) -> MPScrapingStats:
        """Scrapuje dane posłów"""
        ...

    def scrape_clubs(self, term: int, **options) -> MPScrapingStats:
        """Scrapuje kluby"""
        ...

    def scrape_specific_mp(self, term: int, mp_id: int, **options) -> bool:
        """Scrapuje konkretnego posła"""
        ...


# === ABSTRAKCYJNE KLASY BAZOWE ===

class BaseCache(ABC):
    """Abstrakcyjna klasa bazowa dla cache"""

    @abstractmethod
    def _generate_key(self, key: str, params: Optional[Dict] = None) -> str:
        """Generuje klucz cache"""
        pass

    @abstractmethod
    def _serialize_value(self, value: Any) -> bytes:
        """Serializuje wartość"""
        pass

    @abstractmethod
    def _deserialize_value(self, data: bytes) -> Any:
        """Deserializuje wartość"""
        pass


class BaseFileManager(ABC):
    """Abstrakcyjna klasa bazowa dla zarządzania plikami"""

    @abstractmethod
    def get_base_directory(self) -> Path:
        """Zwraca katalog bazowy"""
        pass

    @abstractmethod
    def get_term_directory(self, term: int) -> Path:
        """Zwraca katalog kadencji"""
        pass

    @abstractmethod
    def ensure_directory_structure(self) -> bool:
        """Zapewnia strukturę katalogów"""
        pass


class BaseProcessor(ABC):
    """Abstrakcyjna klasa bazowa dla procesorów"""

    @abstractmethod
    def _preprocess(self, data: Any) -> Any:
        """Wstępne przetwarzanie"""
        pass

    @abstractmethod
    def _postprocess(self, data: Any) -> Any:
        """Końcowe przetwarzanie"""
        pass

    @abstractmethod
    def _validate_input(self, data: Any) -> bool:
        """Waliduje dane wejściowe"""
        pass

    @abstractmethod
    def _validate_output(self, data: Any) -> bool:
        """Waliduje dane wyjściowe"""
        pass


# === INTERFEJSY KONFIGURACJI ===

class ConfigProvider(Protocol):
    """Protokół dla dostarczycieli konfiguracji"""

    def get_config(self, key: str, default: Any = None) -> Any:
        """Pobiera wartość konfiguracji"""
        ...

    def set_config(self, key: str, value: Any) -> bool:
        """Ustawia wartość konfiguracji"""
        ...

    def validate_config(self) -> ValidationResult:
        """Waliduje konfigurację"""
        ...


class LoggerProvider(Protocol):
    """Protokół dla loggerów"""

    def debug(self, message: str, **kwargs) -> None:
        """Loguje wiadomość debug"""
        ...

    def info(self, message: str, **kwargs) -> None:
        """Loguje wiadomość info"""
        ...

    def warning(self, message: str, **kwargs) -> None:
        """Loguje ostrzeżenie"""
        ...

    def error(self, message: str, **kwargs) -> None:
        """Loguje błąd"""
        ...

    def critical(self, message: str, **kwargs) -> None:
        """Loguje błąd krytyczny"""
        ...
