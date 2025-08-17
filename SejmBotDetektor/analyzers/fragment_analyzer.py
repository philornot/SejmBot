"""
Moduł do analizy i oceny fragmentów tekstu pod kątem humoru
"""
import re
from typing import List, Set
from config.keywords import KeywordsConfig


class FragmentAnalyzer:
    """Klasa do analizy fragmentów pod kątem humoru"""

    def __init__(self, debug: bool = False):
        self.debug = debug
        self.funny_keywords = KeywordsConfig.get_funny_keywords()
        self.exclude_keywords = KeywordsConfig.get_exclude_keywords()

    def find_keywords_in_word(self, word: str) -> List[str]:
        """
        Znajduje słowa kluczowe w pojedynczym słowie

        Args:
            word: Słowo do sprawdzenia

        Returns:
            Lista znalezionych słów kluczowych
        """
        # Czyścimy słowo z interpunkcji
        clean_word = re.sub(r'[^\w\s]', '', word.lower())
        found_keywords = []

        for keyword in self.funny_keywords.keys():
            # Sprawdzamy dokładne dopasowanie lub częściowe (tylko dla dłuższych słów)
            if keyword == clean_word:
                found_keywords.append(keyword)
                if self.debug:
                    print(f"DEBUG: Dokładne dopasowanie '{keyword}' w słowie '{clean_word}'")
            elif len(keyword) > 5 and keyword in clean_word:
                found_keywords.append(keyword)
                if self.debug:
                    print(f"DEBUG: Częściowe dopasowanie '{keyword}' w słowie '{clean_word}'")

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
        verified_keywords = []
        fragment_lower = fragment_text.lower()

        for keyword in keywords:
            if keyword in fragment_lower:
                verified_keywords.append(keyword)
                if self.debug:
                    print(f"DEBUG: Zweryfikowano słowo '{keyword}' w fragmencie")
            else:
                if self.debug:
                    print(f"DEBUG: UWAGA! Słowo '{keyword}' nie występuje w fragmencie!")

        return verified_keywords

    def calculate_confidence(self, fragment_text: str, keywords_found: List[str]) -> float:
        """
        Oblicza poziom pewności że fragment jest śmieszny

        Args:
            fragment_text: Tekst fragmentu
            keywords_found: Lista znalezionych słów kluczowych

        Returns:
            Poziom pewności (0.05-0.95)
        """
        if not keywords_found:
            return 0.05

        # Sprawdzamy czy są słowa wykluczające
        fragment_lower = fragment_text.lower()
        exclude_count = sum(1 for exclude_word in self.exclude_keywords
                            if exclude_word in fragment_lower)

        if exclude_count > 3:  # Za dużo słów wykluczających
            if self.debug:
                print(f"DEBUG: Za dużo słów wykluczających ({exclude_count}), niska pewność")
            return 0.1  # Bardzo niska pewność zamiast 0

        # Sumujemy wagi słów kluczowych
        total_weight = sum(KeywordsConfig.get_keyword_weight(keyword) for keyword in keywords_found)

        # Normalizujemy wynik - ale nie dzielimy przez maksymalną możliwą wagę
        base_score = min(total_weight / 10.0, 0.8)  # Max 0.8 z samych słów kluczowych

        # Kara za słowa wykluczające
        exclude_penalty = exclude_count * 0.15

        # Analiza długości fragmentu
        word_count = len(fragment_text.split())
        if word_count < 10:
            length_penalty = 0.3  # Kara za bardzo krótkie fragmenty
            length_bonus = 0
        elif word_count > 20:
            length_bonus = min(word_count / 200, 0.2)  # Bonus za odpowiednią długość
            length_penalty = 0
        else:
            length_bonus = 0.1
            length_penalty = 0

        # Bonus za występowanie wielu różnych słów kluczowych
        variety_bonus = min(len(set(keywords_found)) * 0.1, 0.3)

        final_score = (base_score - exclude_penalty + length_bonus +
                       variety_bonus - length_penalty)

        # Ograniczamy do zakresu 0.05-0.95
        confidence = max(0.05, min(0.95, final_score))

        if self.debug:
            print(f"DEBUG: Obliczenie pewności:")
            print(f"  - Base score (wagi): {base_score:.2f}")
            print(f"  - Exclude penalty: -{exclude_penalty:.2f}")
            print(f"  - Length bonus: +{length_bonus:.2f}")
            print(f"  - Variety bonus: +{variety_bonus:.2f}")
            print(f"  - Length penalty: -{length_penalty:.2f}")
            print(f"  - Final confidence: {confidence:.2f}")

        return confidence

    def is_duplicate(self, new_fragment: str, existing_fragments: List[str],
                     similarity_threshold: float = 0.8) -> bool:
        """
        Sprawdza czy fragment jest duplikatem istniejącego

        Args:
            new_fragment: Nowy fragment do sprawdzenia
            existing_fragments: Lista istniejących fragmentów
            similarity_threshold: Próg podobieństwa (0-1)

        Returns:
            True jeśli fragment jest duplikatem
        """
        new_words = set(new_fragment.lower().split())

        for existing in existing_fragments:
            existing_words = set(existing.lower().split())

            if len(new_words) == 0 or len(existing_words) == 0:
                continue

            # Obliczamy podobieństwo Jaccarda
            intersection = len(new_words.intersection(existing_words))
            union = len(new_words.union(existing_words))

            similarity = intersection / union if union > 0 else 0

            if similarity > similarity_threshold:
                if self.debug:
                    print(f"DEBUG: Znaleziono duplikat (podobieństwo: {similarity:.2f})")
                return True

        return False

    def should_skip_fragment(self, speaker: str, confidence: float,
                             min_confidence: float) -> tuple[bool, str]:
        """
        Sprawdza czy fragment powinien być pominięty

        Args:
            speaker: Mówca fragmentu
            confidence: Pewność fragmentu
            min_confidence: Minimalny próg pewności

        Returns:
            Tuple (czy_pomijać, powód)
        """
        # Pomijamy fragmenty bez rzeczywistego mówcy (chyba że ma wysoką pewność)
        if speaker == "Nieznany mówca" and confidence < 0.7:
            return True, "Nieznany mówca i niska pewność"

        # Pomijamy fragmenty z niską pewnością
        if confidence < min_confidence:
            return True, f"Pewność za niska ({confidence:.2f} < {min_confidence})"

        return False, ""