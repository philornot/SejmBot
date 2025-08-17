"""
Model danych dla śmiesznych fragmentów z Sejmu
"""
from dataclasses import dataclass
from typing import List, Dict
from datetime import datetime


@dataclass
class FunnyFragment:
    """Klasa reprezentująca wykryty śmieszny fragment"""
    text: str
    speaker: str
    meeting_info: str
    keywords_found: List[str]
    position_in_text: int
    context_before: int  # ile słów przed
    context_after: int  # ile słów po
    confidence_score: float  # wynik pewności (0-1)
    timestamp: str = None

    def __post_init__(self):
        """Automatycznie ustawia timestamp jeśli nie podano"""
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()

    def to_dict(self) -> Dict:
        """Konwertuje obiekt do słownika"""
        return {
            'text': self.text,
            'speaker': self.speaker,
            'meeting_info': self.meeting_info,
            'keywords_found': self.keywords_found,
            'position_in_text': self.position_in_text,
            'context_before': self.context_before,
            'context_after': self.context_after,
            'confidence_score': self.confidence_score,
            'timestamp': self.timestamp
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'FunnyFragment':
        """Tworzy obiekt ze słownika"""
        return cls(
            text=data['text'],
            speaker=data['speaker'],
            meeting_info=data['meeting_info'],
            keywords_found=data['keywords_found'],
            position_in_text=data['position_in_text'],
            context_before=data['context_before'],
            context_after=data['context_after'],
            confidence_score=data['confidence_score'],
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