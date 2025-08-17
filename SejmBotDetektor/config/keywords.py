"""
Konfiguracja słów kluczowych dla detektora śmiesznych fragmentów
"""
import re
from typing import Dict, Set, List


class KeywordsConfig:
    """Konfiguracja słów kluczowych i wykluczających"""

    # Słowa kluczowe z wagami (wyższe = bardziej prawdopodobne, że śmieszne)
    FUNNY_KEYWORDS: Dict[str, int] = {
        # Bardzo wysokie prawdopodobieństwo (waga 4) - oczywiste markery humoru
        'śmiech': 4, 'haha': 4, 'hihi': 4, 'śmieszny': 4, 'rozbawienie': 4,
        'żart': 4, 'żartuje': 4, 'komiczny': 4, 'humorystyczny': 4,
        'cyrk': 4, 'farsa': 4, 'kabaret': 4,
        'bzdura': 4, 'nonsens': 4, 'brednie': 4,
        'gafa': 4, 'wpadka': 4, 'lapsus': 4,

        # Wysokie prawdopodobieństwo (waga 3) - silne wskaźniki
        'absurdalny': 3, 'niedorzeczny': 3, 'groteskowy': 3,
        'skandaliczny': 3, 'niewiarygodny': 3, 'szokujący': 3,
        'zabawny': 3, 'rozśmieszać': 3, 'ubaw': 3,
        'teatr': 3, 'spektakl': 3, 'przedstawienie': 3,
        'gwizdy': 3, 'buczenie': 3, 'wrzawa': 3, 'tumult': 3,

        # Średnie prawdopodobieństwo (waga 2) - kontekstowe wskaźniki
        'chaos': 2, 'zamieszanie': 2, 'bałagan': 2, 'awantura': 2,
        'nieporozumienie': 2, 'pomyłka': 2, 'błąd': 2,
        'ironiczny': 2, 'sarkastyczny': 2, 'kpić': 2,
        'oklaski': 2, 'brawa': 2, 'aplauz': 2,
        'dziwny': 2, 'osobliwy': 2, 'niezwykły': 2,

        # Niskie prawdopodobieństwo (waga 1) - wymagają kontekstu
        'ciekawy': 1, 'interesujący': 1, 'zaskakujący': 1,
        'naprawdę': 1, 'serio': 1, 'poważnie': 1,
        'show': 1, 'występ': 1,
        'reakcja': 1, 'odzew': 1, 'odpowiedź': 1
    }

    # Słowa wykluczające — wskazujące na formalne części dokumentu
    EXCLUDE_KEYWORDS: Set[str] = {
        # Elementy struktury dokumentu
        'spis', 'treści', 'porządek', 'dzienny', 'punkt', 'ustawa', 'projekt',
        'sprawozdanie', 'stenograficzne', 'posiedzenie', 'kadencja', 'strona',
        'warszawa', 'dnia', 'roku', 'załącznik', 'aneks',

        # Numery i porządkowanie
        'pierwszy', 'drugi', 'trzeci', 'czwarty', 'piąty', 'szósty',
        'siódmy', 'ósmy', 'dziewiąty', 'dziesiąty',
        'art', 'artykuł', 'ustęp', 'punkt', 'litera', 'tiret',

        # Formalne procedury
        'procedura', 'wniosek', 'poprawka', 'komisja', 'podkomisja',
        'głosowanie', 'protokół', 'zaproszenie', 'zawiadomienie',

        # Daty i czasy
        'styczeń', 'luty', 'marzec', 'kwiecień', 'maj', 'czerwiec',
        'lipiec', 'sierpień', 'wrzesień', 'październik', 'listopad', 'grudzień',
        'poniedziałek', 'wtorek', 'środa', 'czwartek', 'piątek', 'sobota', 'niedziela',

        # Prawnicze
        'konstytucja', 'kodeks', 'rozporządzenie', 'obwieszczenie',
        'dziennik', 'ustaw', 'monitor', 'polski'
    }

    # Cache dla skompilowanych wzorców
    _compiled_patterns = {}
    _exclude_pattern = None

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
        """
        Dodaje nowe śmieszne słowo kluczowe

        Args:
            keyword: Słowo kluczowe
            weight: Waga (1-4)
        """
        if not isinstance(weight, int) or weight < 1 or weight > 4:
            raise ValueError("Waga musi być liczbą całkowitą między 1 a 4")

        cls.FUNNY_KEYWORDS[keyword.lower().strip()] = weight
        cls._invalidate_cache()

    @classmethod
    def remove_funny_keyword(cls, keyword: str):
        """Usuwa śmieszne słowo kluczowe"""
        removed = cls.FUNNY_KEYWORDS.pop(keyword.lower().strip(), None)
        if removed:
            cls._invalidate_cache()
        return removed is not None

    @classmethod
    def add_exclude_keyword(cls, keyword: str):
        """Dodaje nowe słowo wykluczające"""
        cls.EXCLUDE_KEYWORDS.add(keyword.lower().strip())
        cls._invalidate_cache()

    @classmethod
    def remove_exclude_keyword(cls, keyword: str):
        """Usuwa słowo wykluczające"""
        removed = keyword.lower().strip() in cls.EXCLUDE_KEYWORDS
        cls.EXCLUDE_KEYWORDS.discard(keyword.lower().strip())
        if removed:
            cls._invalidate_cache()
        return removed

    @classmethod
    def get_keyword_weight(cls, keyword: str) -> int:
        """Zwraca wagę słowa kluczowego"""
        return cls.FUNNY_KEYWORDS.get(keyword.lower().strip(), 0)

    @classmethod
    def is_excluded_keyword(cls, keyword: str) -> bool:
        """Sprawdza czy słowo jest wykluczające"""
        return keyword.lower().strip() in cls.EXCLUDE_KEYWORDS

    @classmethod
    def get_keywords_by_weight(cls, min_weight: int = 1) -> Dict[int, List[str]]:
        """
        Zwraca słowa kluczowe pogrupowane według wagi

        Args:
            min_weight: Minimalna waga do uwzględnienia

        Returns:
            Słownik {waga: [lista_słów]}
        """
        grouped = {}
        for keyword, weight in cls.FUNNY_KEYWORDS.items():
            if weight >= min_weight:
                if weight not in grouped:
                    grouped[weight] = []
                grouped[weight].append(keyword)

        return grouped

    @classmethod
    def get_exclude_pattern(cls) -> re.Pattern:
        """Zwraca skompilowany wzorzec regex dla słów wykluczających"""
        if cls._exclude_pattern is None:
            # Tworzymy wzorzec dla wszystkich słów wykluczających
            exclude_words = [re.escape(word) for word in cls.EXCLUDE_KEYWORDS]
            pattern_str = r'\b(?:' + '|'.join(exclude_words) + r')\b'
            cls._exclude_pattern = re.compile(pattern_str, re.IGNORECASE)

        return cls._exclude_pattern

    @classmethod
    def count_exclude_words_fast(cls, text: str) -> int:
        """
        Szybko liczy słowa wykluczające w tekście używając regex

        Args:
            text: Tekst do przeszukania

        Returns:
            Liczba słów wykluczających
        """
        pattern = cls.get_exclude_pattern()
        matches = pattern.findall(text.lower())
        return len(matches)

    @classmethod
    def _invalidate_cache(cls):
        """Unieważnia cache skompilowanych wzorców"""
        cls._compiled_patterns.clear()
        cls._exclude_pattern = None

    @classmethod
    def validate_keywords(cls) -> List[str]:
        """
        Waliduje konfigurację słów kluczowych

        Returns:
            Lista problemów/ostrzeżeń
        """
        issues = []

        # Sprawdzamy czy są duplikaty między śmiesznymi a wykluczającymi
        funny_set = set(cls.FUNNY_KEYWORDS.keys())
        exclude_set = cls.EXCLUDE_KEYWORDS

        duplicates = funny_set.intersection(exclude_set)
        if duplicates:
            issues.append(f"Duplikaty między śmiesznymi a wykluczającymi: {duplicates}")

        # Sprawdzamy wagi
        invalid_weights = {k: v for k, v in cls.FUNNY_KEYWORDS.items()
                           if not isinstance(v, int) or v < 1 or v > 4}
        if invalid_weights:
            issues.append(f"Nieprawidłowe wagi: {invalid_weights}")

        # Sprawdzamy czy są puste słowa
        empty_funny = [k for k in cls.FUNNY_KEYWORDS.keys() if not k.strip()]
        empty_exclude = [k for k in cls.EXCLUDE_KEYWORDS if not k.strip()]

        if empty_funny:
            issues.append(f"Puste słowa śmieszne: {empty_funny}")
        if empty_exclude:
            issues.append(f"Puste słowa wykluczające: {empty_exclude}")

        return issues


# Wzorce dla różnych funkcji w Sejmie
SPEAKER_PATTERNS = [
    # Podstawowe wzorce dla posłów
    r'Poseł\s+([A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]+(?:\s+[A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]+)*)\s*:',
    r'Posłanka\s+([A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]+(?:\s+[A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]+)*)\s*:',

    # Wzorce dla funkcji państwowych
    r'(?:Vice)?[Mm]arszałek\s+([A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]+(?:\s+[A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]+)*)\s*:',
    r'(?:Vice)?[Mm]inister\s+([A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]+(?:\s+[A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]+)*)\s*:',
    r'Premier\s+([A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]+(?:\s+[A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]+)*)\s*:',

    # Ogólny wzorzec dla nazwisk z nawiasami (info o klubie)
    r'([A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]+(?:\s+[A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]+)*)\s*\([^)]+\)\s*:',
]

# Wzorce dla informacji o posiedzeniu
MEETING_INFO_PATTERNS = [
    r'(\d+\.\s*posiedzenie\s*Sejmu.*?w dniu.*?\d{1,2}.*?\d{4})',
    r'(Sejm\s*Rzeczypospolitej\s*Polskiej\s*Kadencja\s*[IVX]+.*?\d{4})',
    r'(Sprawozdanie\s*Stenograficzne\s*z\s*\d+\.\s*posiedzenia.*?\d{4})',
    r'(\d{1,2}\s*kadencja.*?posiedzenie.*?\d{4})'
]

# Predefiniowane zestawy słów kluczowych dla różnych typów humoru
HUMOR_CATEGORIES = {
    'slapstick': ['cyrk', 'farsa', 'gafa', 'wpadka', 'bałagan'],
    'verbal': ['żart', 'żartuje', 'ironiczny', 'sarkastyczny', 'kpić'],
    'situational': ['chaos', 'zamieszanie', 'nieporozumienie', 'pomyłka'],
    'reaction': ['śmiech', 'oklaski', 'gwizdy', 'buczenie', 'wrzawa'],
    'absurd': ['absurdalny', 'niedorzeczny', 'bzdura', 'nonsens']
}
