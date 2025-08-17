"""
Moduł do analizy i oceny fragmentów tekstu pod kątem humoru
"""
import re
from typing import List, Tuple

from config.keywords import KeywordsConfig


class FragmentAnalyzer:
    """Klasa do analizy fragmentów pod kątem humoru"""

    def __init__(self, debug: bool = False):
        self.debug = debug
        self.funny_keywords = KeywordsConfig.get_funny_keywords()
        self.exclude_keywords = KeywordsConfig.get_exclude_keywords()
        self._compile_keyword_patterns()

    def _compile_keyword_patterns(self):
        """Prekompiluje wzorce regex dla słów kluczowych dla lepszej wydajności"""
        self.keyword_patterns = {}
        for keyword in self.funny_keywords.keys():
            # Tworzymy wzorzec z granicami słów i obsługą polskich znaków
            pattern = r'\b' + re.escape(keyword) + r'[a-ząćęłńóśźż]*\b'
            self.keyword_patterns[keyword] = re.compile(pattern, re.IGNORECASE)

        if self.debug:
            print(f"DEBUG: Skompilowano {len(self.keyword_patterns)} wzorców słów kluczowych")

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
                    print(f"DEBUG: Znaleziono '{keyword}' na pozycji {match.start()}: '{match.group()}'")

        # Sortujemy według pozycji
        found_keywords.sort(key=lambda x: x[1])
        return found_keywords

    def find_keywords_in_word(self, word: str) -> List[str]:
        """
        PRZESTARZAŁE: Używaj find_keywords_in_text
        Znajduje słowa kluczowe w pojedynczym słowie
        """
        # Czyścimy słowo z interpunkcji
        clean_word = re.sub(r'[^\w\s]', '', word.lower())
        found_keywords = []

        for keyword in self.funny_keywords.keys():
            # Sprawdzamy dokładne dopasowanie lub częściowe dla dłuższych słów
            if keyword == clean_word or (len(keyword) > 4 and keyword in clean_word):
                found_keywords.append(keyword)
                if self.debug:
                    print(f"DEBUG: Dopasowanie '{keyword}' w słowie '{clean_word}'")

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
        fragment_lower = fragment_text.lower()

        for keyword in keywords:
            # Używamy wzorca regex dla lepszej weryfikacji
            if keyword in self.keyword_patterns:
                pattern = self.keyword_patterns[keyword]
                if pattern.search(fragment_text):
                    verified_keywords.append(keyword)
                    if self.debug:
                        print(f"DEBUG: Zweryfikowano słowo '{keyword}' w fragmencie")
                else:
                    if self.debug:
                        print(f"DEBUG: UWAGA! Słowo '{keyword}' nie zostało zweryfikowane!")
            else:
                # Fallback dla starych wywołań
                if keyword in fragment_lower:
                    verified_keywords.append(keyword)

        return list(set(verified_keywords))  # Usuwamy duplikaty

    def calculate_confidence(self, fragment_text: str, keywords_found: List[str]) -> float:
        """
        Oblicza poziom pewności że fragment jest śmieszny - uproszczony algorytm

        Args:
            fragment_text: Tekst fragmentu
            keywords_found: Lista znalezionych słów kluczowych

        Returns:
            Poziom pewności (0.1-0.95)
        """
        if not keywords_found or not fragment_text:
            return 0.1

        # Sprawdzamy czy są słowa wykluczające
        fragment_lower = fragment_text.lower()
        exclude_count = sum(1 for exclude_word in self.exclude_keywords
                            if exclude_word in fragment_lower)

        # Jeśli za dużo słów wykluczających, bardzo niska pewność
        if exclude_count > 4:
            if self.debug:
                print(f"DEBUG: Za dużo słów wykluczających ({exclude_count})")
            return 0.1

        # Obliczamy bazowy wynik na podstawie wag słów kluczowych
        total_weight = sum(KeywordsConfig.get_keyword_weight(keyword) for keyword in keywords_found)
        base_score = min(total_weight * 0.15, 0.7)  # Skalujemy do max 0.7

        # Bonus za różnorodność słów kluczowych
        unique_keywords = len(set(keywords_found))
        variety_bonus = min(unique_keywords * 0.05, 0.15)

        # Kara za słowa wykluczające
        exclude_penalty = exclude_count * 0.08

        # Analiza długości fragmentu
        word_count = len(fragment_text.split())
        if word_count < 8:
            length_modifier = 0.8  # Redukcja dla bardzo krótkich
        elif word_count > 50:
            length_modifier = 1.1  # Bonus za dłuższe fragmenty
        else:
            length_modifier = 1.0

        # Obliczamy końcowy wynik
        final_score = (base_score + variety_bonus - exclude_penalty) * length_modifier

        # Ograniczamy do zakresu 0.1-0.95
        confidence = max(0.1, min(0.95, final_score))

        if self.debug:
            print(f"DEBUG: Pewność - base: {base_score:.2f}, variety: +{variety_bonus:.2f}, "
                  f"exclude: -{exclude_penalty:.2f}, length_mod: {length_modifier:.2f}, "
                  f"final: {confidence:.2f}")

        return confidence

    def is_duplicate(self, new_fragment: str, existing_fragments: List[str],
                     similarity_threshold: float = 0.7) -> bool:
        """
        Sprawdza czy fragment jest duplikatem - ulepszona metoda

        Args:
            new_fragment: Nowy fragment do sprawdzenia
            existing_fragments: Lista istniejących fragmentów
            similarity_threshold: Próg podobieństwa (0-1)

        Returns:
            True jeśli fragment jest duplikatem
        """
        if not new_fragment or not existing_fragments:
            return False

        new_words = set(word.lower() for word in new_fragment.split() if len(word) > 3)

        if len(new_words) < 3:  # Za mało słów do porównania
            return False

        for existing in existing_fragments:
            existing_words = set(word.lower() for word in existing.split() if len(word) > 3)

            if len(existing_words) < 3:
                continue

            # Obliczamy podobieństwo Jaccarda tylko dla dłuższych słów
            intersection = len(new_words.intersection(existing_words))
            union = len(new_words.union(existing_words))

            if union == 0:
                continue

            similarity = intersection / union

            # Dodatkowe sprawdzenie - czy fragmenty zaczynają się podobnie
            new_start = ' '.join(new_fragment.split()[:5]).lower()
            existing_start = ' '.join(existing.split()[:5]).lower()
            start_similarity = len(set(new_start.split()).intersection(set(existing_start.split()))) / max(
                len(set(new_start.split())), len(set(existing_start.split())), 1)

            if similarity > similarity_threshold or start_similarity > 0.8:
                if self.debug:
                    print(f"DEBUG: Duplikat - podobieństwo: {similarity:.2f}, start: {start_similarity:.2f}")
                return True

        return False

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

        # Pomijamy fragmenty z niską pewnością
        if confidence < min_confidence:
            return True, f"Pewność za niska ({confidence:.2f} < {min_confidence})"

        # Pomijamy fragmenty bez rzeczywistego mówcy (chyba że ma wysoką pewność)
        if speaker == "Nieznany mówca" and confidence < 0.6:
            return True, "Nieznany mówca i średnia pewność"

        # Sprawdzamy czy fragment nie jest za krótki
        if fragment_text and len(fragment_text.split()) < 5:
            return True, "Fragment za krótki"

        return False, ""

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
            'readability_score': 0
        }

        if keywords:
            weights = [KeywordsConfig.get_keyword_weight(kw) for kw in keywords]
            metrics['avg_keyword_weight'] = sum(weights) / len(weights)

        # Liczba słów wykluczających
        fragment_lower = fragment_text.lower()
        metrics['exclude_word_count'] = sum(1 for exclude_word in self.exclude_keywords
                                            if exclude_word in fragment_lower)

        # Prosta metryka czytelności (stosunek długich słów do wszystkich)
        words = fragment_text.split()
        if words:
            long_words = [w for w in words if len(w) > 6]
            metrics['readability_score'] = len(long_words) / len(words)

        return metrics
