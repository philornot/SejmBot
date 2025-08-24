"""
Konfiguracja słów kluczowych dla detektora śmiesznych fragmentów
POPRAWIONA WERSJA - zgodna z nowymi wymaganiami
"""
import re
from typing import Dict, Set, List


class KeywordsConfig:
    """Konfiguracja słów kluczowych i wykluczających - POPRAWIONA WERSJA"""

    # Słowa kluczowe z wagami (wyższe = bardziej prawdopodobne, że śmieszne)
    FUNNY_KEYWORDS: Dict[str, int] = {
        # Bardzo wysokie prawdopodobieństwo (waga 4) - oczywiste markery humoru
        'śmiech': 4, 'haha': 4, 'hihi': 4, 'lol': 4,
        'śmieszny': 4, 'rozbawienie': 4,
        'żart': 4, 'żartuje': 4, 'żarcik': 4,
        'komiczny': 4, 'humorystyczny': 4, 'dowcip': 4, 'gag': 4,
        'cyrk': 4, 'farsa': 4, 'kabaret': 4, 'opera mydlana': 4,
        'bzdura': 4, 'nonsens': 4, 'brednie': 4, 'absurd': 4,
        'gafa': 4, 'wpadka': 4, 'lapsus': 4, 'autokompromitacja': 4,

        # Wysokie prawdopodobieństwo (waga 3) - silne wskaźniki
        'absurdalny': 3, 'niedorzeczny': 3, 'groteskowy': 3,
        'skandaliczny': 3, 'niewiarygodny': 3, 'szokujący': 3,
        'zabawny': 3, 'rozśmieszać': 3, 'ubaw': 3, 'śmieszyć': 3,
        'teatr': 3, 'spektakl': 3, 'przedstawienie': 3, 'szopka': 3,
        'parodia': 3, 'kpina': 3, 'drwina': 3, 'ironia': 3,
        'groteska': 3, 'skecz': 3,
        'gwizdy': 3, 'buczenie': 3, 'wrzawa': 3, 'tumult': 3, 'chaĺturzenie': 3,

        # Średnie prawdopodobieństwo (waga 2) - kontekstowe wskaźniki
        'chaos': 2, 'zamieszanie': 2, 'bałagan': 2, 'awantura': 2,
        'nieporozumienie': 2, 'pomyłka': 2, 'błąd': 2, 'omyłka': 2,
        'ironiczny': 2, 'sarkastyczny': 2, 'sarkazm': 2, 'kpić': 2, 'kpiarski': 2,
        'dziwny': 2, 'osobliwy': 2, 'niezwykły': 2, 'nietypowy': 2,
        'komentarze z sali': 2, 'docinki': 2, 'śmiesznostka': 2,

        # Niskie prawdopodobieństwo (waga 1) - wymagające kontekstu
        'ciekawy': 1, 'interesujący': 1, 'zaskakujący': 1,
        'naprawdę': 1, 'serio': 1, 'poważnie': 1, 'tak sobie': 1,
        'show': 1, 'występ': 1, 'reality': 1,
        'reakcja': 1, 'odzew': 1, 'odpowiedź': 1,
        'efektowny': 1, 'dziwactwo': 1
    }

    # Słowa wykluczające – wskazujące na formalne części dokumentu
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
        'dziennik', 'ustaw', 'monitor', 'polski',

        # NOWE: Markery stenogramu - używane do filtracji nawiasów
        'oklaski', 'brawa', 'aplauz', 'dzwonek', 'gwizdy', 'buczenie', 'wrzawa', 'tumult'
    }

    # NOWE: Wzorce dla typów humoru
    HUMOR_TYPE_KEYWORDS = {
        'joke': ['żart', 'żartuje', 'żarcik', 'haha', 'hihi', 'śmiech', 'dowcip', 'gag',
                 'komiczny', 'humorystyczny', 'zabawny', 'rozbawienie', 'śmieszny'],
        'sarcasm': ['ironiczny', 'sarkastyczny', 'sarkazm', 'kpić', 'kpina', 'drwina',
                    'ironia', 'kpiarski', 'docinki'],
        'personal_attack': ['kabaret', 'cyrk', 'farsa', 'kpina', 'spektakl', 'teatr',
                            'szopka', 'parodia', 'opera'],
        'chaos': ['gwizdy', 'buczenie', 'wrzawa', 'tumult', 'chaos', 'zamieszanie',
                  'bałagan', 'awantura', 'chaĺturzenie']
    }

    # Cache dla skompilowanych wzorców
    _compiled_patterns = {}
    _exclude_pattern = None
    _stenogram_pattern = None

    @classmethod
    def get_funny_keywords(cls) -> Dict[str, int]:
        """Zwraca słownik śmiesznych słów kluczowych"""
        return cls.FUNNY_KEYWORDS.copy()

    @classmethod
    def get_exclude_keywords(cls) -> Set[str]:
        """Zwraca zbiór słów wykluczających"""
        return cls.EXCLUDE_KEYWORDS.copy()

    @classmethod
    def get_humor_type_keywords(cls) -> Dict[str, List[str]]:
        """Zwraca słowa kluczowe dla typów humoru"""
        return {k: v.copy() for k, v in cls.HUMOR_TYPE_KEYWORDS.items()}

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
    def get_stenogram_markers_pattern(cls) -> re.Pattern:
        """
        NOWE: Zwraca wzorzec regex dla markerów stenogramu w nawiasach
        Używany do filtracji nawiasów [...] i (...) zawierających tylko markery stenogramu
        """
        if cls._stenogram_pattern is None:
            # Lista markerów stenogramu
            stenogram_markers = [
                'oklaski', 'brawa', 'aplauz', 'dzwonek', 'gwizdy',
                'buczenie', 'wrzawa', 'tumult', 'cisza', 'przerwa'
            ]

            # Wzorzec dopasowujący nawiasy zawierające tylko markery stenogramu
            # Pattern explanation:
            # \[ - początek nawiasu kwadratowego
            # (?:\s* - grupa niezapamiętująca ze spacjami
            # (?:oklaski|gwizdy|...) - alternatywa markerów
            # \s*[,\s]* - spacje i przecinki między markerami
            # )+ - jeden lub więcej markerów
            # \] - koniec nawiasu
            markers_escaped = [re.escape(marker) for marker in stenogram_markers]
            markers_pattern = '|'.join(markers_escaped)

            pattern_str = (
                    r'\[(?:\s*(?:' + markers_pattern + r')\s*[,\s]*)+\]|' +
                    r'\((?:\s*(?:' + markers_pattern + r')\s*[,\s]*)+\)'
            )

            cls._stenogram_pattern = re.compile(pattern_str, re.IGNORECASE)

        return cls._stenogram_pattern

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
    def get_humor_type_for_keywords(cls, keywords: List[str]) -> str:
        """
        NOWE: Określa typ humoru na podstawie słów kluczowych

        Args:
            keywords: Lista znalezionych słów kluczowych

        Returns:
            Typ humoru: 'joke', 'sarcasm', 'personal_attack', 'chaos', 'other'
        """
        if not keywords:
            return 'other'

        # Liczymy punkty dla każdego typu humoru
        type_scores = {}

        for humor_type, type_keywords in cls.HUMOR_TYPE_KEYWORDS.items():
            score = 0
            for keyword in keywords:
                if keyword.lower() in [tk.lower() for tk in type_keywords]:
                    # Używamy wagi słowa kluczowego jako mnożnika
                    weight = cls.get_keyword_weight(keyword)
                    score += weight

            type_scores[humor_type] = score

        # Znajdź typ z najwyższym wynikiem
        if max(type_scores.values()) > 0:
            best_type = max(type_scores, key=type_scores.get)
            return best_type

        return 'other'

    @classmethod
    def filter_stenogram_markers(cls, text: str) -> str:
        """
        NOWE: Filtruje markery stenogramu w nawiasach z tekstu

        Args:
            text: Tekst do przefiltrowania

        Returns:
            Tekst bez markerów stenogramu w nawiasach
        """
        pattern = cls.get_stenogram_markers_pattern()
        filtered = pattern.sub('', text)

        # Usuń nadmiarowe spacje
        filtered = re.sub(r'\s+', ' ', filtered).strip()

        return filtered

    @classmethod
    def _invalidate_cache(cls):
        """Unieważnia cache skompilowanych wzorców"""
        cls._compiled_patterns.clear()
        cls._exclude_pattern = None
        cls._stenogram_pattern = None

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

        # NOWE: Sprawdzamy definicje typów humoru
        for humor_type, keywords_list in cls.HUMOR_TYPE_KEYWORDS.items():
            if not keywords_list:
                issues.append(f"Pusty typ humoru: {humor_type}")

        return issues


# Wzorce dla różnych funkcji w Sejmie - POPRAWIONA WERSJA
SPEAKER_PATTERNS = [
    # Podstawowe wzorce dla posłów z uwzględnieniem polskich znaków
    r'Poseł\s+([A-ZĄĆĘŁŃÓŚŹŻa-ząćęłńóśźż\s]+?)(?:\s*\(([^)]+)\))?\s*:',
    r'Posłanka\s+([A-ZĄĆĘŁŃÓŚŹŻa-ząćęłńóśźż\s]+?)(?:\s*\(([^)]+)\))?\s*:',

    # Wzorce dla funkcji państwowych
    r'(?:Vice)?[Mm]arszałek\s+([A-ZĄĆĘŁŃÓŚŹŻa-ząćęłńóśźż\s]+?)(?:\s*\(([^)]+)\))?\s*:',
    r'(?:Vice)?[Mm]inister\s+([A-ZĄĆĘŁŃÓŚŹŻa-ząćęłńóśźż\s]+?)(?:\s*\(([^)]+)\))?\s*:',
    r'Premier\s+([A-ZĄĆĘŁŃÓŚŹŻa-ząćęłńóśźż\s]+?)(?:\s*\(([^)]+)\))?\s*:',

    # Ogólny wzorzec dla nazwisk z nawiasami (info o klubie)
    r'([A-ZĄĆĘŁŃÓŚŹŻa-ząćęłńóśźż\s]+?)\s*\(([^)]+)\)\s*:',

    # Wzorzec fallback dla prostych nazwisk
    r'([A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]+(?:\s+[A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]+)*)\s*:'
]

# Wzorce dla informacji o posiedzeniu - POPRAWIONE
MEETING_INFO_PATTERNS = [
    r'(\d+\.\s*posiedzenie\s*Sejmu.*?w dniu.*?\d{1,2}.*?\d{4})',
    r'(Sejm\s*Rzeczypospolitej\s*Polskiej\s*Kadencja\s*[IVX]+.*?\d{4})',
    r'(Sprawozdanie\s*Stenograficzne\s*z\s*\d+\.\s*posiedzenia.*?\d{4})',
    r'(\d{1,2}\s*kadencja.*?posiedzenie.*?\d{4})',
    # NOWE: Dodatkowe wzorce
    r'(Kadencja\s*[IVX]+.*?posiedzenie\s*\d+.*?\d{4})',
    r'(\d{1,2}\.\d{1,2}\.\d{4}.*?posiedzenie)',
]

# NOWE: Predefiniowane zestawy słów kluczowych dla różnych typów humoru
HUMOR_CATEGORIES = {
    'slapstick': ['cyrk', 'farsa', 'gafa', 'wpadka', 'bałagan'],
    'verbal': ['żart', 'żartuje', 'ironiczny', 'sarkastyczny', 'kpić'],
    'situational': ['chaos', 'zamieszanie', 'nieporozumienie', 'pomyłka'],
    'reaction': ['śmiech', 'oklaski', 'gwizdy', 'buczenie', 'wrzawa'],
    'absurd': ['absurdalny', 'niedorzeczny', 'bzdura', 'nonsens']
}

# NOWE: Wzorce do czyszczenia tekstu
TEXT_CLEANING_PATTERNS = {
    'multiple_spaces': re.compile(r'\s+'),  # Wielokrotne spacje
    'leading_nonword': re.compile(r'^\W+'),  # Nietypowe znaki na początku
    'trailing_nonword': re.compile(r'\W+$'),  # Nietypowe znaki na końcu
    'stenogram_brackets': re.compile(r'\[(?:[oklaski|gwizdy|aplauz|brawa|dzwonek|wrzawa|tumult|buczenie\s,]+)\]',
                                     re.IGNORECASE),
    'stenogram_parens': re.compile(r'\((?:[oklaski|gwizdy|aplauz|brawa|dzwonek|wrzawa|tumult|buczenie\s,]+)\)',
                                   re.IGNORECASE)
}


def clean_text_for_output(text: str) -> str:
    """
    NOWE: Funkcja pomocnicza do czyszczenia tekstu przed zapisem do JSON

    Args:
        text: Surowy tekst do wyczyszczenia

    Returns:
        Wyczyszczony tekst gotowy do zapisu
    """
    if not text:
        return ""

    cleaned = text

    # Usuń markery stenogramu
    cleaned = TEXT_CLEANING_PATTERNS['stenogram_brackets'].sub('', cleaned)
    cleaned = TEXT_CLEANING_PATTERNS['stenogram_parens'].sub('', cleaned)

    # Znormalizuj spacje
    cleaned = TEXT_CLEANING_PATTERNS['multiple_spaces'].sub(' ', cleaned)

    # Usuń nietypowe znaki z końców
    cleaned = TEXT_CLEANING_PATTERNS['leading_nonword'].sub('', cleaned)
    cleaned = TEXT_CLEANING_PATTERNS['trailing_nonword'].sub('', cleaned)

    return cleaned.strip()


def parse_speaker_name_and_club(speaker_raw: str) -> Dict[str, str]:
    """
    NOWE: Parsuje nazwisko i klub mówcy do ujednoliconej struktury

    Args:
        speaker_raw: Surowe dane o mówcy

    Returns:
        Słownik {"name": str, "club": str|None}
    """
    if not speaker_raw or speaker_raw == "Nieznany mówca":
        return {"name": "Nieznany mówca", "club": None}

    # Próbujemy dopasować wzorce z klubami
    for pattern in SPEAKER_PATTERNS:
        match = re.match(pattern, speaker_raw.strip())
        if match:
            if len(match.groups()) >= 2 and match.group(2):
                # Mamy nazwę i klub
                return {
                    "name": match.group(1).strip(),
                    "club": match.group(2).strip()
                }
            else:
                # Tylko nazwa
                return {
                    "name": match.group(1).strip(),
                    "club": None
                }

    # Fallback - zwracamy surowe dane jako nazwę
    return {"name": speaker_raw.strip(), "club": None}
