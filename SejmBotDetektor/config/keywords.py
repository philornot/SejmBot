"""
Konfiguracja słów kluczowych dla detektora śmiesznych fragmentów
"""
from typing import Dict, Set


class KeywordsConfig:
    """Konfiguracja słów kluczowych i wykluczających"""

    # Słowa kluczowe z wagami (wyższe = bardziej prawdopodobne że śmieszne)
    FUNNY_KEYWORDS: Dict[str, int] = {
        # Wysokie prawdopodobieństwo (waga 3)
        'śmiech': 3, 'śmieszny': 3, 'zabawny': 3, 'rozbawienie': 3,
        'żart': 3, 'żartuje': 3, 'komiczny': 3, 'humorystyczny': 3,
        'halo': 3, 'ojej': 3, 'ałał': 3, 'ups': 3, 'oops': 3,
        'bzdura': 3, 'nonsens': 3, 'brednie': 3, 'głupota': 3,
        'cyrk': 3, 'kabaret': 3, 'farsa': 3,
        'gafa': 3, 'wpadka': 3, 'lapsus': 3,
        'gwizdy': 3, 'buczenie': 3, 'wrzawa': 3,

        # Średnie prawdopodobieństwo (waga 2)
        'niedorzeczny': 2, 'absurdalny': 2, 'skandaliczny': 2,
        'niewiarygodny': 2, 'szokujący': 2,
        'chaos': 2, 'zamieszanie': 2, 'bałagan': 2, 'awantura': 2,
        'ironiczny': 2, 'sarkastyczny': 2,
        'oklaski': 2, 'brawa': 2,

        # Niskie prawdopodobieństwo - tylko w odpowiednim kontekście (waga 1)
        'teatr': 1, 'show': 1, 'spektakl': 1,
        'naprawdę': 1, 'serio': 1, 'poważnie': 1
    }

    # Słowa wykluczające (jeśli występują w pobliżu, fragment jest odrzucany)
    EXCLUDE_KEYWORDS: Set[str] = {
        'spis', 'treści', 'porządek', 'dzienny', 'punkt', 'ustawa', 'projekt',
        'sprawozdanie', 'stenograficzne', 'posiedzenie', 'kadencja', 'strona',
        'warszawa', 'dnia', 'roku', 'pierwszy', 'drugi', 'trzeci', 'czwarty',
        'piąty', 'szósty', 'siódmy', 'ósmy', 'dziewiąty', 'dziesiąty'
    }

    @classmethod
    def get_funny_keywords(cls) -> Dict[str, int]:
        """Zwraca słownik śmiesznych słów kluczowych"""
        return cls.FUNNY_KEYWORDS.copy()

    @classmethod
    def get_exclude_keywords(cls) -> Set[str]:
        """Zwraca zbiór słów wykluczających"""
        return cls.EXCLUDE_KEYWORDS.copy()

    @classmethod
    def add_funny_keyword(cls, keyword: str, weight: int = 1):
        """Dodaje nowe śmieszne słowo kluczowe"""
        cls.FUNNY_KEYWORDS[keyword.lower()] = weight

    @classmethod
    def remove_funny_keyword(cls, keyword: str):
        """Usuwa śmieszne słowo kluczowe"""
        cls.FUNNY_KEYWORDS.pop(keyword.lower(), None)

    @classmethod
    def add_exclude_keyword(cls, keyword: str):
        """Dodaje nowe słowo wykluczające"""
        cls.EXCLUDE_KEYWORDS.add(keyword.lower())

    @classmethod
    def remove_exclude_keyword(cls, keyword: str):
        """Usuwa słowo wykluczające"""
        cls.EXCLUDE_KEYWORDS.discard(keyword.lower())

    @classmethod
    def get_keyword_weight(cls, keyword: str) -> int:
        """Zwraca wagę słowa kluczowego"""
        return cls.FUNNY_KEYWORDS.get(keyword.lower(), 0)

    @classmethod
    def is_excluded_keyword(cls, keyword: str) -> bool:
        """Sprawdza czy słowo jest wykluczające"""
        return keyword.lower() in cls.EXCLUDE_KEYWORDS


# Wzorce dla różnych funkcji w Sejmie
SPEAKER_PATTERNS = [
    r'Poseł\s+([A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]+(?:\s+[A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]+)*):',
    r'Posłanka\s+([A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]+(?:\s+[A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]+)*):',
    r'([A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]+(?:\s+[A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]+)*)\s*\([^)]*\):',
    r'Wicemarszałek\s+([A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]+(?:\s+[A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]+)*):',
    r'Marszałek\s+([A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]+(?:\s+[A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]+)*):',
    r'Minister\s+([A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]+(?:\s+[A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]+)*):',
    r'Wiceminister\s+([A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]+(?:\s+[A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]+)*):',
    r'Premier\s+([A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]+(?:\s+[A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]+)*):',
    r'Prezes Rady Ministrów\s+([A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]+(?:\s+[A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]+)*):',
]

# Wzorce dla informacji o posiedzeniu
MEETING_INFO_PATTERNS = [
    r'(\d+\.\s*posiedzenie\s*Sejmu.*?w dniu.*?\d{4})',
    r'(Posiedzenie\s*nr\s*\d+.*?\d{4})',
    r'(SEJM\s*RZECZYPOSPOLITEJ\s*POLSKIEJ.*?\d{4})',
    r'(\d{1,2}\s*kadencja.*?posiedzenie.*?\d{4})'
]