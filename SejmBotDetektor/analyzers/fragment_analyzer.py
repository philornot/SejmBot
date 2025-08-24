"""
Moduł do analizy i oceny fragmentów tekstu pod kątem humoru
"""
import re
from difflib import SequenceMatcher
from typing import List, Tuple, Dict, Optional

from SejmBotDetektor.config.keywords import KeywordsConfig
from SejmBotDetektor.logging.logger import get_module_logger


class FragmentAnalyzer:
    """Klasa do analizy fragmentów pod kątem humoru"""

    def __init__(self, debug: bool = False):
        self.debug = debug
        self.logger = get_module_logger("FragmentAnalyzer")
        self.funny_keywords = KeywordsConfig.get_funny_keywords()
        self.exclude_keywords = KeywordsConfig.get_exclude_keywords()
        self._compile_keyword_patterns()

        # Definiujemy typy humoru z ich charakterystycznymi słowami
        self.humor_types = {
            'joke': ['żart', 'żartuje', 'żarcik', 'haha', 'hihi', 'śmiech', 'dowcip', 'gag', 'komiczny',
                     'humorystyczny', 'zabawny', 'rozbawienie', 'śmieszny'],
            'sarcasm': ['ironiczny', 'sarkastyczny', 'sarkazm', 'kpić', 'kpina', 'drwina', 'ironia', 'kpiarski',
                        'docinki'],
            'personal_attack': ['kabaret', 'cyrk', 'farsa', 'kpina', 'spektakl', 'teatr', 'szopka', 'parodia',
                                'opera'],
            'chaos': ['gwizdy', 'buczenie', 'wrzawa', 'tumult', 'chaos', 'zamieszanie', 'bałagan', 'awantura',
                      'chałturzenie']
        }

        # Wzorce dla usuwania nawiasów z markerami stenogramu
        self.stenogram_pattern = re.compile(
            r'\[(?:\s*(?:oklaski|gwizdy|aplauz|brawa|dzwonek|wrzawa|tumult|buczenie)\s*[,\s]*)+\]|'
            r'\((?:\s*(?:oklaski|gwizdy|aplauz|brawa|dzwonek|wrzawa|tumult|buczenie)\s*[,\s]*)+\)',
            re.IGNORECASE
        )

    def _compile_keyword_patterns(self):
        """Prekompiluje wzorce regex dla słów kluczowych dla lepszej wydajności"""
        self.keyword_patterns = {}
        for keyword in self.funny_keywords.keys():
            pattern = r'\b' + re.escape(keyword) + r'[a-ząćęłńóśźż]*\b'
            self.keyword_patterns[keyword] = re.compile(pattern, re.IGNORECASE)

        if self.debug:
            self.logger.debug(f"Skompilowano {len(self.keyword_patterns)} wzorców słów kluczowych")

    def clean_fragment_text(self, text: str) -> str:
        """
        Czyści tekst fragmentu przed zapisem do JSON-a

        Args:
            text: Surowy tekst fragmentu

        Returns:
            Oczyszczony tekst
        """
        if not text:
            return ""

        # Usuwamy markery stenogramu w nawiasach
        cleaned = self.stenogram_pattern.sub('', text)

        # Usuwamy nadmiarowe spacje, entery i nietypowe znaki
        cleaned = re.sub(r'\s+', ' ', cleaned)  # Wielokrotne spacje na pojedyncze
        cleaned = re.sub(r'^\W+', '', cleaned)  # Nietypowe znaki na początku
        cleaned = re.sub(r'\W+$', '', cleaned)  # Nietypowe znaki na końcu
        cleaned = cleaned.strip()

        return cleaned

    def find_keywords_in_text(self, text: str) -> List[Tuple[str, int]]:
        """
        Znajduje wszystkie słowa kluczowe w tekście wraz z ich pozycjami

        Args:
            text: Tekst do przeszukania

        Returns:
            Lista tupli (słowo_kluczowe, pozycja)
        """
        found_keywords = []

        for keyword, pattern in self.keyword_patterns.items():
            matches = pattern.finditer(text)
            for match in matches:
                found_keywords.append((keyword, match.start()))
                if self.debug:
                    self.logger.debug(f"Znaleziono '{keyword}' na pozycji {match.start()}: '{match.group()}'")

        found_keywords.sort(key=lambda x: x[1])
        return found_keywords

    def verify_keywords_in_fragment(self, fragment_text: str, keywords: List[str]) -> List[str]:
        """
        Weryfikuje czy słowa kluczowe rzeczywiście występują w fragmencie

        Args:
            fragment_text: Tekst fragmentu
            keywords: Lista słów kluczowych do weryfikacji

        Returns:
            Lista zweryfikowanych słów kluczowych
        """
        if not fragment_text or not keywords:
            return []

        verified_keywords = []

        for keyword in keywords:
            if keyword in self.keyword_patterns:
                pattern = self.keyword_patterns[keyword]
                if pattern.search(fragment_text):
                    verified_keywords.append(keyword)
            else:
                # Fallback dla starych wywołań
                if keyword in fragment_text.lower():
                    verified_keywords.append(keyword)

        return list(set(verified_keywords))

    def calculate_confidence_detailed(self, fragment_text: str, keywords_found: List[str]) -> Dict[str, float]:
        """
        Oblicza szczegółowy poziom pewności z rozbiciem na składowe

        Args:
            fragment_text: Tekst fragmentu
            keywords_found: Lista znalezionych słów kluczowych

        Returns:
            Słownik ze składowymi pewności
        """
        if not keywords_found or not fragment_text:
            return {
                'keyword_score': 0.0,
                'context_score': 0.0,
                'length_bonus': 0.0,
                'confidence': 0.1
            }

        # 1. Keyword score - suma wag słów kluczowych
        total_weight = sum(KeywordsConfig.get_keyword_weight(keyword) for keyword in keywords_found)
        keyword_score = min(total_weight * 0.15, 0.6)  # Max 0.6 z keywords

        # 2. Context score - dodatkowe punkty za kontekst
        context_score = 0.0

        # Bonus za różnorodność słów kluczowych
        unique_keywords = len(set(keywords_found))
        variety_bonus = min(unique_keywords * 0.05, 0.15)
        context_score += variety_bonus

        # Sprawdzamy czy są słowa wykluczające
        fragment_lower = fragment_text.lower()
        exclude_count = KeywordsConfig.count_exclude_words_fast(fragment_text)
        exclude_penalty = min(exclude_count * 0.08, 0.2)
        context_score -= exclude_penalty

        # Bonus za obecność wielu różnych typów markerów humoru
        humor_markers = sum(1 for humor_type, words in self.humor_types.items()
                            if any(word in keywords_found for word in words))
        if humor_markers > 1:
            context_score += 0.1

        context_score = max(0.0, min(0.25, context_score))  # Max 0.25 z kontekstu

        # 3. Length bonus - dodatkowe punkty za długość
        word_count = len(fragment_text.split())
        if word_count >= 30:
            length_bonus = min((word_count - 30) * 0.01, 0.15)  # Max 0.15 za długość
        elif word_count < 15:
            length_bonus = -0.1  # Kara za krótkie fragmenty
        else:
            length_bonus = 0.0

        # 4. Obliczamy końcowy confidence
        confidence = keyword_score + context_score + length_bonus
        confidence = max(0.1, min(0.95, confidence))

        return {
            'keyword_score': round(keyword_score, 3),
            'context_score': round(context_score, 3),
            'length_bonus': round(length_bonus, 3),
            'confidence': round(confidence, 3)
        }

    def calculate_confidence(self, fragment_text: str, keywords_found: List[str]) -> float:
        """
        Zachowana kompatybilność - zwraca tylko końcowy confidence score
        """
        scores = self.calculate_confidence_detailed(fragment_text, keywords_found)
        return scores['confidence']

    def determine_humor_type(self, keywords_found: List[str], fragment_text: str = "") -> str:
        """
        Określa typ humoru na podstawie słów kluczowych i kontekstu

        Args:
            keywords_found: Lista znalezionych słów kluczowych
            fragment_text: Tekst fragmentu (opcjonalny)

        Returns:
            Typ humoru: 'joke', 'sarcasm', 'personal_attack', 'chaos', 'other'
        """
        if not keywords_found:
            return 'other'

        # Liczymy punkty dla każdego typu humoru
        type_scores = {}

        for humor_type, type_keywords in self.humor_types.items():
            score = 0
            for keyword in keywords_found:
                if keyword in type_keywords:
                    # Używamy wagi słowa kluczowego jako mnożnika
                    weight = KeywordsConfig.get_keyword_weight(keyword)
                    score += weight

            type_scores[humor_type] = score

        # Znajdź typ z najwyższym wynikiem
        if max(type_scores.values()) > 0:
            best_type = max(type_scores, key=type_scores.get)
            return best_type

        return 'other'

    def is_fragment_too_short(self, fragment_text: str, min_words: int = 15) -> bool:
        """
        Sprawdza czy fragment jest za krótki

        Args:
            fragment_text: Tekst fragmentu
            min_words: Minimalna liczba słów

        Returns:
            True jeśli fragment jest za krótki
        """
        if not fragment_text:
            return True

        word_count = len(fragment_text.split())
        is_too_short = word_count < min_words

        if is_too_short and self.debug:
            self.logger.debug(f"Fragment za krótki: {word_count} słów (wymagane: {min_words})")

        return is_too_short

    def is_duplicate_fuzzy(self, new_fragment: str, existing_fragments: List[str],
                           similarity_threshold: float = 0.85) -> bool:
        """
        Sprawdza czy fragment jest duplikatem używając fuzzy matching

        Args:
            new_fragment: Nowy fragment do sprawdzenia
            existing_fragments: Lista istniejących fragmentów
            similarity_threshold: Próg podobieństwa (0-1)

        Returns:
            True jeśli fragment jest duplikatem
        """
        if not new_fragment or not existing_fragments:
            return False

        new_clean = self.clean_fragment_text(new_fragment)
        if len(new_clean.split()) < 5:  # Za mało słów do porównania
            return False

        for existing in existing_fragments:
            existing_clean = self.clean_fragment_text(existing)

            if len(existing_clean.split()) < 5:
                continue

            # Używamy SequenceMatcher do obliczenia podobieństwa
            similarity = SequenceMatcher(None, new_clean.lower(), existing_clean.lower()).ratio()

            if similarity > similarity_threshold:
                if self.debug:
                    self.logger.debug(f"Duplikat znaleziony - podobieństwo: {similarity:.2f}")
                return True

        return False

    def extract_sentence_context(self, full_text: str, fragment_position: int,
                                 sentences_before: int = 1, sentences_after: int = 1) -> Dict[str, str]:
        """
        Wyciąga kontekst zdaniowy przed i po fragmencie

        Args:
            full_text: Pełny tekst źródłowy
            fragment_position: Pozycja fragmentu w tekście
            sentences_before: Liczba zdań przed
            sentences_after: Liczba zdań po

        Returns:
            Słownik z kontekstem przed i po
        """
        if not full_text or fragment_position < 0:
            return {'context_before': '', 'context_after': ''}

        # Dzielimy tekst na zdania (prosty podział po kropkach/wykrzyknikach/pytajnikach)
        sentence_endings = re.compile(r'[.!?]+\s+')
        sentences = sentence_endings.split(full_text)

        # Znajdź zdanie zawierające fragment
        current_sentence_idx = -1
        char_position = 0

        for i, sentence in enumerate(sentences):
            if char_position <= fragment_position < char_position + len(sentence):
                current_sentence_idx = i
                break
            char_position += len(sentence) + 2  # +2 for sentence ending and space

        if current_sentence_idx == -1:
            return {'context_before': '', 'context_after': ''}

        # Wyciągnij kontekst przed
        start_idx = max(0, current_sentence_idx - sentences_before)
        context_before = ' '.join(sentences[start_idx:current_sentence_idx]).strip()

        # Wyciągnij kontekst po
        end_idx = min(len(sentences), current_sentence_idx + sentences_after + 1)
        context_after = ' '.join(sentences[current_sentence_idx + 1:end_idx]).strip()

        return {
            'context_before': self.clean_fragment_text(context_before)[:200],  # Limit 200 znaków
            'context_after': self.clean_fragment_text(context_after)[:200]
        }

    def should_skip_fragment(self, speaker: str, confidence: float,
                             min_confidence: float, fragment_text: str = "") -> Tuple[bool, str]:
        """
        Sprawdza czy fragment powinien być pominięty - rozszerzona walidacja

        Args:
            speaker: Mówca fragmentu
            confidence: Pewność fragmentu
            min_confidence: Minimalny próg pewności
            fragment_text: Tekst fragmentu (opcjonalny)

        Returns:
            Tuple (czy_pomijać, powód)
        """
        # Walidacja parametrów
        if not isinstance(confidence, (int, float)) or not isinstance(min_confidence, (int, float)):
            return True, "Nieprawidłowe wartości pewności"

        if confidence < 0 or confidence > 1 or min_confidence < 0 or min_confidence > 1:
            return True, "Wartości pewności poza zakresem 0-1"

        # Sprawdzamy długość fragmentu
        if fragment_text and self.is_fragment_too_short(fragment_text):
            return True, "Fragment za krótki"

        # Pomijamy fragmenty z niską pewnością
        if confidence < min_confidence:
            return True, f"Pewność za niska ({confidence:.2f} < {min_confidence})"

        # Pomijamy fragmenty bez rzeczywistego mówcy (chyba że ma wysoką pewność)
        if speaker == "Nieznany mówca" and confidence < 0.6:
            return True, "Nieznany mówca i średnia pewność"

        return False, ""

    def parse_speaker_info(self, speaker_raw: str) -> Dict[str, Optional[str]]:
        """
        Parsuje informacje o mówcy do ujednoliconej struktury

        Args:
            speaker_raw: Surowe dane o mówcy

        Returns:
            Słownik ze strukturą: {"name": str, "club": str|None}
        """
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

    def get_fragment_quality_metrics(self, fragment_text: str, keywords: List[str]) -> dict:
        """
        Zwraca szczegółowe metryki jakości fragmentu

        Args:
            fragment_text: Tekst fragmentu
            keywords: Znalezione słowa kluczowe

        Returns:
            Słownik z metrykami
        """
        metrics = {
            'word_count': len(fragment_text.split()),
            'char_count': len(fragment_text),
            'keyword_count': len(keywords),
            'unique_keywords': len(set(keywords)),
            'avg_keyword_weight': 0,
            'exclude_word_count': 0,
            'readability_score': 0,
            'too_short': self.is_fragment_too_short(fragment_text)
        }

        if keywords:
            weights = [KeywordsConfig.get_keyword_weight(kw) for kw in keywords]
            metrics['avg_keyword_weight'] = sum(weights) / len(weights)

        # Liczba słów wykluczających - używamy nowej szybkiej metody
        metrics['exclude_word_count'] = KeywordsConfig.count_exclude_words_fast(fragment_text)

        # Prosta metryka czytelności (stosunek długich słów do wszystkich)
        words = fragment_text.split()
        if words:
            long_words = [w for w in words if len(w) > 6]
            metrics['readability_score'] = len(long_words) / len(words)

        return metrics

    def filter_protocol_markers(self, text: str) -> str:
        """
        Filtruje markery protokołu z tekstu

        Args:
            text: Tekst do przefiltrowania

        Returns:
            Tekst bez markerów protokołu
        """
        # Usuń nawiasy zawierające tylko markery stenogramu
        filtered = self.stenogram_pattern.sub('', text)

        # Usuń nadmiarowe spacje
        filtered = re.sub(r'\s+', ' ', filtered).strip()

        return filtered

    # Zachowana kompatybilność z poprzednimi metodami
    def is_duplicate(self, new_fragment: str, existing_fragments: List[str],
                     similarity_threshold: float = 0.7) -> bool:
        """
        PRZESTARZAŁE: Użyj is_duplicate_fuzzy z threshold 0.85
        """
        return self.is_duplicate_fuzzy(new_fragment, existing_fragments, 0.85)
