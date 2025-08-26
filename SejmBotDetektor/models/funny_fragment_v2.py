"""
Nowy model FunnyFragment z pełną wypowiedzią jako kontekstem
"""
from dataclasses import dataclass
from typing import List, Dict, Optional


@dataclass
class FunnyFragmentV2:
    """
    Nowy model śmiesznego fragmentu z pełną wypowiedzią jako kontekstem
    """
    # Podstawowe informacje o fragmencie
    fragment_text: str  # Znaleziony śmieszny fragment
    fragment_position_in_speech: int  # Pozycja fragmentu w wypowiedzi
    keywords_found: List[str]  # Znalezione słowa kluczowe

    # Informacje o wypowiedzi (pełny kontekst)
    full_speech_content: str  # Pełna treść wypowiedzi
    speech_index: int  # Numer wypowiedzi w transkrypcie
    speech_word_count: int  # Liczba słów w całej wypowiedzi

    # Informacje o mówcy
    speaker_name: str  # Oczyszczona nazwa mówcy
    speaker_club: Optional[str]  # Klub parlamentarny
    speaker_raw: str  # Surowa nazwa z transkryptu

    # Informacje o posiedzeniu
    meeting_info: str  # Informacje o posiedzeniu
    source_file: Optional[str] = None  # Plik źródłowy

    # Metryki pewności i jakości
    confidence_score: float = 0.0  # Ogólna pewność (0-1)
    keyword_score: float = 0.0  # Punkty za słowa kluczowe
    context_score: float = 0.0  # Punkty za kontekst
    length_bonus: float = 0.0  # Bonus/kara za długość

    # Dodatkowe metadane
    humor_type: str = 'other'  # Typ humoru
    fragment_word_count: int = 0  # Liczba słów w fragmencie

    def __post_init__(self):
        """Oblicza dodatkowe metryki po inicjalizacji"""
        if not self.fragment_word_count:
            self.fragment_word_count = len(self.fragment_text.split())

    @property
    def speaker_with_club(self) -> str:
        """Zwraca mówcę z klubem w formacie 'Imię Nazwisko (Klub)'"""
        if self.speaker_club:
            return f"{self.speaker_name} ({self.speaker_club})"
        return f"{self.speaker_name} (brak klubu)"

    @property
    def speaker_info(self) -> Dict[str, Optional[str]]:
        """Zwraca informacje o mówcy jako słownik"""
        return {
            "name": self.speaker_name,
            "club": self.speaker_club,
            "raw": self.speaker_raw
        }

    def get_fragment_preview(self, max_chars: int = 100) -> str:
        """Zwraca podgląd fragmentu"""
        if len(self.fragment_text) <= max_chars:
            return self.fragment_text
        return self.fragment_text[:max_chars].strip() + "..."

    def get_speech_preview(self, max_chars: int = 200) -> str:
        """Zwraca podgląd pełnej wypowiedzi"""
        if len(self.full_speech_content) <= max_chars:
            return self.full_speech_content
        return self.full_speech_content[:max_chars].strip() + "..."

    def get_fragment_context(self, words_before: int = 20, words_after: int = 20) -> Dict[str, str]:
        """
        Zwraca kontekst fragmentu w ramach wypowiedzi

        Args:
            words_before: Liczba słów przed fragmentem
            words_after: Liczba słów po fragmencie

        Returns:
            Słownik z kontekstem przed i po fragmencie
        """
        speech_words = self.full_speech_content.split()
        fragment_words = self.fragment_text.split()

        # Próbujemy znaleźć pozycję fragmentu w wypowiedzi
        fragment_start_word = -1
        for i in range(len(speech_words) - len(fragment_words) + 1):
            if ' '.join(speech_words[i:i + len(fragment_words)]) == self.fragment_text:
                fragment_start_word = i
                break

        if fragment_start_word == -1:
            # Fallback - używamy pozycji znaku
            char_pos = self.full_speech_content.find(self.fragment_text)
            if char_pos != -1:
                # Przybliżona pozycja słowa
                words_before_char = self.full_speech_content[:char_pos].split()
                fragment_start_word = len(words_before_char)
            else:
                # Ostateczny fallback - środek wypowiedzi
                fragment_start_word = len(speech_words) // 2

        # Wyciągamy kontekst
        context_start = max(0, fragment_start_word - words_before)
        context_end = min(len(speech_words), fragment_start_word + len(fragment_words) + words_after)

        before_words = speech_words[context_start:fragment_start_word]
        after_words = speech_words[fragment_start_word + len(fragment_words):context_end]

        return {
            'context_before': ' '.join(before_words),
            'context_after': ' '.join(after_words)
        }

    def calculate_fragment_density(self) -> float:
        """Oblicza gęstość fragmentu względem wypowiedzi (0-1)"""
        if self.speech_word_count == 0:
            return 0.0
        return min(1.0, self.fragment_word_count / self.speech_word_count)

    def get_keywords_summary(self) -> str:
        """Zwraca podsumowanie znalezionych słów kluczowych"""
        if not self.keywords_found:
            return "Brak słów kluczowych"

        if len(self.keywords_found) <= 3:
            return ", ".join(self.keywords_found)
        else:
            return f"{', '.join(self.keywords_found[:3])} i {len(self.keywords_found) - 3} więcej"

    def to_dict(self) -> dict:
        """Konwertuje fragment do słownika (dla JSON)"""
        return {
            # Fragment
            'fragment_text': self.fragment_text,
            'fragment_position_in_speech': self.fragment_position_in_speech,
            'fragment_word_count': self.fragment_word_count,
            'keywords_found': self.keywords_found,
            'keywords_summary': self.get_keywords_summary(),

            # Pełna wypowiedź (kontekst)
            'full_speech_content': self.full_speech_content,
            'speech_index': self.speech_index,
            'speech_word_count': self.speech_word_count,
            'fragment_density': round(self.calculate_fragment_density(), 3),

            # Mówca
            'speaker': {
                'name': self.speaker_name,
                'club': self.speaker_club,
                'raw': self.speaker_raw,
                'with_club': self.speaker_with_club
            },

            # Metadane
            'meeting_info': self.meeting_info,
            'source_file': self.source_file,

            # Metryki
            'confidence_score': round(self.confidence_score, 3),
            'keyword_score': round(self.keyword_score, 3),
            'context_score': round(self.context_score, 3),
            'length_bonus': round(self.length_bonus, 3),
            'humor_type': self.humor_type,

            # Dodatkowe podglądy
            'fragment_preview': self.get_fragment_preview(100),
            'speech_preview': self.get_speech_preview(200)
        }

    def to_csv_row(self) -> dict:
        """Konwertuje fragment do wiersza CSV"""
        return {
            'source_file': self.source_file or '',
            'speech_index': self.speech_index,
            'speaker_name': self.speaker_name,
            'speaker_club': self.speaker_club or '',
            'confidence_score': round(self.confidence_score, 3),
            'humor_type': self.humor_type,
            'keywords_found': ', '.join(self.keywords_found),
            'fragment_word_count': self.fragment_word_count,
            'speech_word_count': self.speech_word_count,
            'fragment_text': self.fragment_text,
            'speech_preview': self.get_speech_preview(300),
            'meeting_info': self.meeting_info
        }

    @classmethod
    def from_speech_and_fragment(cls, speech, fragment_text: str, fragment_pos: int,
                                 keywords: List[str], confidence_details: dict,
                                 humor_type: str = 'other', meeting_info: str = '',
                                 source_file: str = None):
        """
        Tworzy FunnyFragmentV2 z obiektu Speech i danych fragmentu

        Args:
            speech: Obiekt Speech
            fragment_text: Tekst fragmentu
            fragment_pos: Pozycja fragmentu w wypowiedzi
            keywords: Znalezione słowa kluczowe
            confidence_details: Szczegóły pewności z FragmentAnalyzer
            humor_type: Typ humoru
            meeting_info: Informacje o posiedzeniu
            source_file: Plik źródłowy
        """
        return cls(
            # Fragment
            fragment_text=fragment_text,
            fragment_position_in_speech=fragment_pos,
            keywords_found=keywords,

            # Wypowiedź
            full_speech_content=speech.content,
            speech_index=speech.speech_index,
            speech_word_count=speech.get_word_count(),

            # Mówca
            speaker_name=speech.speaker_name,
            speaker_club=speech.speaker_club,
            speaker_raw=speech.speaker_raw,

            # Metadane
            meeting_info=meeting_info,
            source_file=source_file,

            # Metryki
            confidence_score=confidence_details.get('confidence', 0.0),
            keyword_score=confidence_details.get('keyword_score', 0.0),
            context_score=confidence_details.get('context_score', 0.0),
            length_bonus=confidence_details.get('length_bonus', 0.0),
            humor_type=humor_type
        )

    def __str__(self) -> str:
        """String representation"""
        return (f"Fragment({self.speaker_name}, confidence={self.confidence_score:.2f}, "
                f"words={self.fragment_word_count}/{self.speech_word_count})")

    def __repr__(self) -> str:
        """Detailed representation"""
        return (f"FunnyFragmentV2(speaker='{self.speaker_name}', club='{self.speaker_club}', "
                f"confidence={self.confidence_score:.2f}, keywords={len(self.keywords_found)}, "
                f"fragment_words={self.fragment_word_count}, speech_words={self.speech_word_count})")


# Pomocnicze funkcje
def fragments_to_json_structure(fragments: List[FunnyFragmentV2]) -> dict:
    """Konwertuje listę fragmentów do struktury JSON"""
    if not fragments:
        return {
            'summary': {
                'total_fragments': 0,
                'average_confidence': 0.0,
                'humor_types': {},
                'clubs': {}
            },
            'fragments': []
        }

    # Statystyki
    total_fragments = len(fragments)
    avg_confidence = sum(f.confidence_score for f in fragments) / total_fragments

    # Typy humoru
    humor_types = {}
    for fragment in fragments:
        humor_type = fragment.humor_type
        humor_types[humor_type] = humor_types.get(humor_type, 0) + 1

    # Kluby
    clubs = {}
    for fragment in fragments:
        club = fragment.speaker_club or "Bez klubu"
        clubs[club] = clubs.get(club, 0) + 1

    return {
        'summary': {
            'total_fragments': total_fragments,
            'average_confidence': round(avg_confidence, 3),
            'humor_types': humor_types,
            'clubs': dict(sorted(clubs.items(), key=lambda x: x[1], reverse=True))
        },
        'fragments': [fragment.to_dict() for fragment in fragments]
    }
