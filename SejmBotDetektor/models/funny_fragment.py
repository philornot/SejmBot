"""
Model danych dla śmiesznych fragmentów z Sejmu
POPRAWIONA WERSJA z nowymi polami i strukturą
"""
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import List, Dict, Optional


@dataclass
class FunnyFragment:
    """Klasa reprezentująca wykryty śmieszny fragment - rozszerzona wersja"""
    text: str
    speaker_raw: str  # Surowe dane o mówcy
    meeting_info: str
    keywords_found: List[str]
    position_in_text: int
    context_before_words: int  # ile słów przed (dla kompatybilności)
    context_after_words: int  # ile słów po (dla kompatybilności)
    confidence_score: float  # wynik pewności (0-1)

    # Nowe pola zgodnie z wymaganiami
    keyword_score: float = 0.0
    context_score: float = 0.0
    length_bonus: float = 0.0
    humor_type: str = "other"
    too_short: bool = False

    # Kontekst zdaniowy
    context_before: str = ""
    context_after: str = ""

    # Metadane
    fragment_id: str = None
    timestamp: str = None

    def __post_init__(self):
        """Automatycznie ustawia timestamp i ID jeśli nie podano"""
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()

        if self.fragment_id is None:
            self.fragment_id = str(uuid.uuid4())

    @property
    def speaker(self) -> Dict[str, Optional[str]]:
        """Zwraca ustrukturyzowane informacje o mówcy"""
        return self._parse_speaker_info(self.speaker_raw)

    def _parse_speaker_info(self, speaker_raw: str) -> Dict[str, Optional[str]]:
        """
        Parsuje informacje o mówcy do ujednoliconej struktury

        Args:
            speaker_raw: Surowe dane o mówcy

        Returns:
            Słownik ze strukturą: {"name": str, "club": str|None}
        """
        import re

        if not speaker_raw or speaker_raw == "Nieznany mówca":
            return {"name": "Nieznany mówca", "club": None}

        # Wzorzec dla nazwa (klub)
        club_pattern = re.compile(r'^(.+?)\s*\(([^)]+)\)\s*$')
        match = club_pattern.match(speaker_raw.strip())

        if match:
            name = match.group(1).strip()
            club = match.group(2).strip()
            return {"name": name, "club": club}
        else:
            # Brak klubu w nawiasach
            return {"name": speaker_raw.strip(), "club": None}

    def to_dict(self) -> Dict:
        """Konwertuje obiekt do słownika w nowym formacie"""
        return {
            'id': self.fragment_id,
            'speaker': self.speaker,  # Używa property zwracającego strukturę
            'text': self.text,
            'context_before': self.context_before,
            'context_after': self.context_after,
            'keywords': self.keywords_found,
            'keyword_score': self.keyword_score,
            'context_score': self.context_score,
            'length_bonus': self.length_bonus,
            'confidence': self.confidence_score,
            'humor_type': self.humor_type,
            'too_short': self.too_short,
            'metadata': {
                'meeting_info': self.meeting_info,
                'position_in_text': self.position_in_text,
                'context_words_before': self.context_before_words,
                'context_words_after': self.context_after_words,
                'timestamp': self.timestamp
            }
        }

    def to_legacy_dict(self) -> Dict:
        """Konwertuje obiekt do słownika w starym formacie (kompatybilność)"""
        return {
            'text': self.text,
            'speaker': self.speaker_raw,  # Surowe dane dla kompatybilności
            'meeting_info': self.meeting_info,
            'keywords_found': self.keywords_found,
            'position_in_text': self.position_in_text,
            'context_before': self.context_before_words,
            'context_after': self.context_after_words,
            'confidence_score': self.confidence_score,
            'timestamp': self.timestamp
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'FunnyFragment':
        """Tworzy obiekt ze słownika - obsługuje stary i nowy format"""

        # Sprawdzamy czy to nowy format
        if 'speaker' in data and isinstance(data['speaker'], dict):
            # Nowy format
            speaker_info = data['speaker']
            if speaker_info.get('club'):
                speaker_raw = f"{speaker_info['name']} ({speaker_info['club']})"
            else:
                speaker_raw = speaker_info['name']

            return cls(
                text=data.get('text', ''),
                speaker_raw=speaker_raw,
                meeting_info=data.get('metadata', {}).get('meeting_info', ''),
                keywords_found=data.get('keywords', []),
                position_in_text=data.get('metadata', {}).get('position_in_text', -1),
                context_before_words=data.get('metadata', {}).get('context_words_before', 50),
                context_after_words=data.get('metadata', {}).get('context_words_after', 50),
                confidence_score=data.get('confidence', 0.0),
                keyword_score=data.get('keyword_score', 0.0),
                context_score=data.get('context_score', 0.0),
                length_bonus=data.get('length_bonus', 0.0),
                humor_type=data.get('humor_type', 'other'),
                too_short=data.get('too_short', False),
                context_before=data.get('context_before', ''),
                context_after=data.get('context_after', ''),
                fragment_id=data.get('id'),
                timestamp=data.get('metadata', {}).get('timestamp')
            )
        else:
            # Stary format
            return cls(
                text=data.get('text', ''),
                speaker_raw=data.get('speaker', 'Nieznany mówca'),
                meeting_info=data.get('meeting_info', ''),
                keywords_found=data.get('keywords_found', []),
                position_in_text=data.get('position_in_text', -1),
                context_before_words=data.get('context_before', 50),
                context_after_words=data.get('context_after', 50),
                confidence_score=data.get('confidence_score', 0.0),
                timestamp=data.get('timestamp')
            )

    def get_short_preview(self, max_length: int = 100) -> str:
        """Zwraca skrócony podgląd tekstu"""
        if len(self.text) <= max_length:
            return self.text
        return self.text[:max_length] + "..."

    def get_keywords_as_string(self) -> str:
        """Zwraca słowa kluczowe jako string"""
        return ", ".join(self.keywords_found)

    def is_high_quality(self, min_confidence: float = 0.5) -> bool:
        """Sprawdza czy fragment jest wysokiej jakości"""
        return (not self.too_short and
                self.confidence_score >= min_confidence and
                len(self.keywords_found) > 0)

    def get_quality_summary(self) -> str:
        """Zwraca podsumowanie jakości fragmentu"""
        quality_parts = []

        if self.too_short:
            quality_parts.append("za krótki")
        if self.confidence_score < 0.3:
            quality_parts.append("niska pewność")
        if not self.keywords_found:
            quality_parts.append("brak słów kluczowych")
        if self.humor_type == "other":
            quality_parts.append("nieokreślony typ")

        if not quality_parts:
            quality_parts.append("wysoka jakość")

        return ", ".join(quality_parts)
