#!/usr/bin/env python3
"""
SejmBot - Modele danych
Definicje struktur danych używanych w systemie SejmBot.
"""

import hashlib
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Optional, Dict, Any


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

    def __post_init__(self):
        """Walidacja i automatyczne uzupełnienie pól po utworzeniu obiektu"""
        # Automatycznie uzupełnij scraped_at jeśli puste
        if not self.scraped_at:
            self.scraped_at = datetime.now().isoformat()

        # Wygeneruj hash jeśli mamy tekst
        if self.transcript_text and not self.hash:
            self.hash = hashlib.md5(self.transcript_text.encode()).hexdigest()

        # Walidacja session_id
        if not self.session_id:
            raise ValueError("session_id nie może być pusty")

        # Walidacja meeting_number
        if not isinstance(self.meeting_number, int) or self.meeting_number < 0:
            raise ValueError("meeting_number musi być nieujemną liczbą całkowitą")

    def to_dict(self) -> Dict[str, Any]:
        """Konwertuje obiekt do słownika z dodatkowymi metadanymi"""
        data = asdict(self)

        # Dodaj wyliczone metadane
        data.update({
            'text_length': len(self.transcript_text) if self.transcript_text else 0,
            'word_count': len(self.transcript_text.split()) if self.transcript_text else 0,
            'has_content': bool(self.transcript_text and len(self.transcript_text.strip()) > 0),
            'processing_metadata': {
                'bot_version': '2.1',
                'processed_at': self.scraped_at,
                'file_type': self.file_type,
                'source_url': self.url,
                'has_hash': bool(self.hash)
            }
        })

        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SejmSession':
        """Tworzy obiekt SejmSession ze słownika"""
        # Wyciągnij tylko pola które istnieją w dataclass
        valid_fields = {field.name for field in cls.__dataclass_fields__.values()}
        filtered_data = {k: v for k, v in data.items() if k in valid_fields}

        return cls(**filtered_data)

    def get_filename_base(self) -> str:
        """Zwraca bazową nazwę pliku dla tej sesji"""
        if self.day_letter:
            return f"posiedzenie_{self.meeting_number:03d}_{self.day_letter}_{self.session_id}"
        else:
            return f"posiedzenie_{self.meeting_number:03d}_{self.session_id}"

    def get_display_title(self) -> str:
        """Zwraca czytelny tytuł sesji do wyświetlania"""
        if self.day_letter:
            return f"Posiedzenie nr {self.meeting_number} ({self.day_letter}) - {self.date}"
        else:
            return f"Posiedzenie nr {self.meeting_number} - {self.date}"

    def is_valid_content(self) -> bool:
        """Sprawdza czy sesja ma poprawną zawartość"""
        return bool(
            self.transcript_text and
            len(self.transcript_text.strip()) > 500 and
            self.hash
        )

    def get_year(self) -> str:
        """Wyciąga rok z daty sesji"""
        if self.date and len(self.date) >= 4:
            return self.date[:4]
        return str(datetime.now().year)


@dataclass
class SessionParsingResult:
    """Wynik parsowania pojedynczej sesji"""
    session: Optional[SejmSession]
    success: bool
    error_message: Optional[str] = None
    pdf_bytes: Optional[bytes] = None
    processing_time_seconds: Optional[float] = None

    def __post_init__(self):
        """Walidacja wyników parsowania"""
        if self.success and not self.session:
            raise ValueError("Jeśli success=True, session nie może być None")

        if not self.success and not self.error_message:
            self.error_message = "Nieznany błąd podczas parsowania"


@dataclass
class SessionIndex:
    """Indeks sesji dla danej kadencji i roku"""
    kadencja: int
    year: str
    sessions: Dict[str, Dict[str, Any]]
    stats: Dict[str, Any]

    def __post_init__(self):
        """Inicjalizuj statystyki jeśli nie podane"""
        if not self.stats:
            self.stats = {
                'total_sessions': 0,
                'total_characters': 0,
                'total_words': 0,
                'last_updated': None
            }

        self.update_stats()

    def update_stats(self):
        """Aktualizuje statystyki na podstawie bieżących sesji"""
        self.stats.update({
            'total_sessions': len(self.sessions),
            'total_characters': sum(s.get('text_length', 0) for s in self.sessions.values()),
            'total_words': sum(s.get('word_count', 0) for s in self.sessions.values()),
            'last_updated': datetime.now().isoformat()
        })

    def add_session(self, session: SejmSession):
        """Dodaje sesję do indeksu"""
        session_data = session.to_dict()
        self.sessions[session.session_id] = {
            'meeting_number': session.meeting_number,
            'title': session.title[:100],
            'date': session.date,
            'text_length': session_data['text_length'],
            'word_count': session_data['word_count'],
            'file_type': session.file_type,
            'has_pdf': bool(session_data.get('processing_metadata', {}).get('has_pdf', False)),
            'processed_at': session.scraped_at,
            'day_letter': session.day_letter,
            'kadencja': session.kadencja
        }
        self.update_stats()

    def to_dict(self) -> Dict[str, Any]:
        """Konwertuje indeks do słownika do zapisu JSON"""
        return asdict(self)


@dataclass
class ProcessingStats:
    """Statystyki procesu przetwarzania"""
    total_found: int = 0
    processed_new: int = 0
    skipped_existing: int = 0
    failed: int = 0
    connection_errors: int = 0
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None

    def __post_init__(self):
        """Ustaw czas startu jeśli nie podany"""
        if not self.start_time:
            self.start_time = datetime.now()

    def finish(self):
        """Oznacz koniec przetwarzania"""
        self.end_time = datetime.now()

    def get_success_rate(self) -> float:
        """Zwraca wskaźnik sukcesu w procentach"""
        total_attempts = self.processed_new + self.failed
        if total_attempts == 0:
            return 0.0
        return (self.processed_new / total_attempts) * 100

    def get_processing_time(self) -> Optional[float]:
        """Zwraca czas przetwarzania w sekundach"""
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return None

    def get_summary(self) -> str:
        """Zwraca tekstowe podsumowanie statystyk"""
        lines = [
            f"🔍 Znalezionych dni posiedzeń: {self.total_found:3d}",
            f"⏭️  Już przetworzonych:        {self.skipped_existing:3d}",
            f"✅ Nowo przetworzonych:       {self.processed_new:3d}",
            f"❌ Nieudanych:                {self.failed:3d}"
        ]

        if self.connection_errors > 0:
            lines.append(f"🌐 Błędy połączenia:          {self.connection_errors:3d}")

        if self.processed_new > 0:
            lines.append(f"🎯 Wskaźnik sukcesu:          {self.get_success_rate():.1f}%")

        processing_time = self.get_processing_time()
        if processing_time:
            lines.append(f"⏱️  Czas przetwarzania:        {processing_time:.1f}s")

        return "\n".join(lines)


@dataclass
class SessionLink:
    """Reprezentacja linku do posiedzenia znalezionego na stronie"""
    id: str
    meeting_number: int
    title: str
    url: str
    date: str
    kadencja: int
    rok: int
    original_text: str
    day_letter: str = ""
    pdf_direct: bool = False

    def to_session_data(self) -> Dict[str, Any]:
        """Konwertuje do formatu używanego przez _process_session"""
        return {
            'id': self.id,
            'meeting_number': self.meeting_number,
            'day_letter': self.day_letter,
            'title': self.title,
            'url': self.url,
            'date': self.date,
            'kadencja': self.kadencja,
            'rok': self.rok,
            'original_text': self.original_text,
            'pdf_direct': self.pdf_direct
        }
