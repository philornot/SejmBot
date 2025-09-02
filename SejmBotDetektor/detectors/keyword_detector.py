"""
Moduł do wyszukiwania słów kluczowych w gotowych wypowiedziach
Jedna odpowiedzialność: przekształca Speech[] -> KeywordMatch[]
"""
import re
from dataclasses import dataclass
from typing import List, Tuple, Optional

from SejmBotDetektor.config.keywords import KeywordsConfig
from SejmBotDetektor.logging.logger import get_module_logger
from SejmBotDetektor.processors.transcript_parser import Speech


@dataclass
class KeywordMatch:
    """Pojedyncze dopasowanie słowa kluczowego w wypowiedzi"""
    keyword: str  # Znalezione słowo kluczowe
    speech: Speech  # Wypowiedź w której znaleziono
    word_position: int  # Pozycja słowa w wypowiedzi (indeks)
    char_position: int  # Pozycja znaku w treści wypowiedzi
    context_words: List[str]  # Słowa wokół znalezionego słowa
    keyword_category: str  # Kategoria słowa (z KeywordsConfig)
    confidence_base: float  # Podstawowa pewność dla tego słowa


class KeywordDetector:
    """
    Detektor słów kluczowych w strukturze wypowiedzi
    Jedna odpowiedzialność: Speech[] -> KeywordMatch[]
    """

    def __init__(self, context_radius: int = 10, debug: bool = False):
        """
        Args:
            context_radius: Ile słów wokół słowa kluczowego zapisać jako kontekst
            debug: Tryb debugowania
        """
        self.context_radius = context_radius
        self.debug = debug
        self.logger = get_module_logger("KeywordDetector")

        # Ładujemy konfigurację słów kluczowych
        try:
            self.keywords_config = KeywordsConfig()
            self.compiled_patterns = self._compile_keyword_patterns()
        except Exception as e:
            self.logger.error(f"Błąd ładowania konfiguracji słów: {e}")
            self.keywords_config = None
            self.compiled_patterns = {}

        self.stats = {
            'processed_speeches': 0,
            'total_matches': 0,
            'matches_by_category': {},
            'skipped_short_speeches': 0,
            'processing_errors': 0
        }

    def find_keywords_in_speeches(self, speeches: List[Speech],
                                  min_speech_words: int = 5) -> List[KeywordMatch]:
        """
        Główna metoda: znajduje słowa kluczowe we wszystkich wypowiedziach

        Args:
            speeches: Lista wypowiedzi do przeanalizowania
            min_speech_words: Minimalna długość wypowiedzi (w słowach)

        Returns:
            Lista znalezionych dopasowań słów kluczowych
        """
        if not speeches:
            return []

        # Resetujemy statystyki
        self.stats = {k: 0 if isinstance(v, int) else {} for k, v in self.stats.items()}

        if self.debug:
            self.logger.debug(f"Rozpoczynam wyszukiwanie w {len(speeches)} wypowiedziach")

        all_matches = []

        for speech in speeches:
            try:
                # Pomijamy za krótkie wypowiedzi
                if speech.get_word_count() < min_speech_words:
                    self.stats['skipped_short_speeches'] += 1
                    continue

                # Znajdź słowa kluczowe w tej wypowiedzi
                matches = self._find_keywords_in_single_speech(speech)
                all_matches.extend(matches)

                self.stats['processed_speeches'] += 1
                self.stats['total_matches'] += len(matches)

                if self.debug and matches:
                    self.logger.debug(f"Wypowiedź {speech.speech_index} ({speech.speaker_name}): "
                                      f"{len(matches)} dopasowań")

            except Exception as e:
                self.logger.error(f"Błąd przetwarzania wypowiedzi {speech.speech_index}: {e}")
                self.stats['processing_errors'] += 1
                continue

        if self.debug:
            self._print_detection_stats()

        return all_matches

    def _find_keywords_in_single_speech(self, speech: Speech) -> List[KeywordMatch]:
        """
        Znajduje słowa kluczowe w pojedynczej wypowiedzi

        Args:
            speech: Wypowiedź do przeanalizowania

        Returns:
            Lista dopasowań w tej wypowiedzi
        """
        if not self.compiled_patterns:
            return []

        content = speech.content
        words = content.split()
        matches = []

        # Przeszukujemy każdą kategorię słów kluczowych
        for category, patterns in self.compiled_patterns.items():
            category_matches = self._search_patterns_in_text(
                content, words, patterns, category, speech
            )
            matches.extend(category_matches)

            # Aktualizujemy statystyki kategorii
            if category not in self.stats['matches_by_category']:
                self.stats['matches_by_category'][category] = 0
            self.stats['matches_by_category'][category] += len(category_matches)

        return matches

    def _search_patterns_in_text(self, content: str, words: List[str],
                                 patterns: List[Tuple[re.Pattern, str, float]],
                                 category: str, speech: Speech) -> List[KeywordMatch]:
        """
        Przeszukuje tekst używając skompilowanych wzorców

        Args:
            content: Treść wypowiedzi
            words: Słowa wypowiedzi
            patterns: Skompilowane wzorce dla kategorii
            category: Nazwa kategorii
            speech: Obiekt wypowiedzi

        Returns:
            Lista dopasowań dla tej kategorii
        """
        matches = []

        for pattern, keyword, base_confidence in patterns:
            # Znajdź wszystkie wystąpienia tego wzorca
            for match in pattern.finditer(content):
                char_pos = match.start()
                word_pos = self._char_to_word_position(content, char_pos)

                if word_pos is not None:
                    # Wyciągnij kontekst
                    context = self._extract_word_context(words, word_pos)

                    keyword_match = KeywordMatch(
                        keyword=keyword,
                        speech=speech,
                        word_position=word_pos,
                        char_position=char_pos,
                        context_words=context,
                        keyword_category=category,
                        confidence_base=base_confidence
                    )

                    matches.append(keyword_match)

                    if self.debug:
                        self.logger.debug(f"Znaleziono '{keyword}' w pozycji {word_pos} "
                                          f"({speech.speaker_name})")

        return matches

    def _compile_keyword_patterns(self) -> dict:
        """
        Kompiluje wzorce regex dla wszystkich słów kluczowych

        Returns:
            Dict {kategoria: [(compiled_pattern, keyword, confidence), ...]}
        """
        if not self.keywords_config:
            return {}

        compiled = {}

        try:
            # Pobieramy wszystkie kategorie słów kluczowych
            all_keywords = self.keywords_config.get_all_keywords_by_category()

            for category, keywords_data in all_keywords.items():
                compiled[category] = []

                for keyword_info in keywords_data:
                    keyword = keyword_info.get('word', '')
                    confidence = keyword_info.get('confidence', 0.5)

                    if keyword:
                        # Tworzymy wzorzec regex dla słowa (word boundaries)
                        pattern = re.compile(
                            r'\b' + re.escape(keyword) + r'\b',
                            re.IGNORECASE
                        )
                        compiled[category].append((pattern, keyword, confidence))

            if self.debug:
                total_patterns = sum(len(patterns) for patterns in compiled.values())
                self.logger.debug(f"Skompilowano {total_patterns} wzorców w {len(compiled)} kategoriach")

        except Exception as e:
            self.logger.error(f"Błąd kompilacji wzorców: {e}")
            return {}

        return compiled

    @staticmethod
    def _char_to_word_position(content: str, char_position: int) -> Optional[int]:
        """
        Konwertuje pozycję znaku na pozycję słowa

        Args:
            content: Treść tekstowa
            char_position: Pozycja znaku

        Returns:
            Pozycja słowa lub None jeśli nie można ustalić
        """
        # Podziel tekst na słowa i znajdź pozycję
        words = content.split()
        current_char = 0

        for word_idx, word in enumerate(words):
            word_start = content.find(word, current_char)
            if word_start <= char_position < word_start + len(word):
                return word_idx
            current_char = word_start + len(word)

        return None

    def _extract_word_context(self, words: List[str], word_position: int) -> List[str]:
        """
        Wyciąga kontekst wokół słowa

        Args:
            words: Lista wszystkich słów
            word_position: Pozycja centralnego słowa

        Returns:
            Lista słów tworzących kontekst
        """
        start_idx = max(0, word_position - self.context_radius)
        end_idx = min(len(words), word_position + self.context_radius + 1)

        return words[start_idx:end_idx]

    def filter_matches_by_confidence(self, matches: List[KeywordMatch],
                                     min_confidence: float = 0.3) -> List[KeywordMatch]:
        """
        Filtruje dopasowania według pewności

        Args:
            matches: Lista wszystkich dopasowań
            min_confidence: Minimalny próg pewności

        Returns:
            Przefiltrowana lista
        """
        filtered = [match for match in matches if match.confidence_base >= min_confidence]

        if self.debug:
            self.logger.debug(f"Przefiltrowano z {len(matches)} do {len(filtered)} dopasowań "
                              f"(min_confidence: {min_confidence})")

        return filtered

    def group_matches_by_speech(self, matches: List[KeywordMatch]) -> dict:
        """
        Grupuje dopasowania według wypowiedzi

        Args:
            matches: Lista dopasowań

        Returns:
            Dict {speech_index: [matches]}
        """
        grouped = {}

        for match in matches:
            speech_idx = match.speech.speech_index
            if speech_idx not in grouped:
                grouped[speech_idx] = []
            grouped[speech_idx].append(match)

        return grouped

    def get_matches_by_category(self, matches: List[KeywordMatch]) -> dict:
        """
        Grupuje dopasowania według kategorii słów kluczowych

        Args:
            matches: Lista dopasowań

        Returns:
            Dict {category: [matches]}
        """
        categorized = {}

        for match in matches:
            category = match.keyword_category
            if category not in categorized:
                categorized[category] = []
            categorized[category].append(match)

        return categorized

    def _print_detection_stats(self):
        """Wyświetla statystyki wykrywania w trybie debug"""
        self.logger.debug("=== STATYSTYKI WYKRYWANIA SŁÓW KLUCZOWYCH ===")
        self.logger.debug(f"Przetworzone wypowiedzi: {self.stats['processed_speeches']}")
        self.logger.debug(f"Łączna liczba dopasowań: {self.stats['total_matches']}")
        self.logger.debug(f"Pominięte krótkie wypowiedzi: {self.stats['skipped_short_speeches']}")
        self.logger.debug(f"Błędy przetwarzania: {self.stats['processing_errors']}")

        if self.stats['matches_by_category']:
            self.logger.debug("Dopasowania według kategorii:")
            for category, count in sorted(self.stats['matches_by_category'].items(),
                                          key=lambda x: x[1], reverse=True):
                self.logger.debug(f"  {category}: {count}")

    def get_detection_stats(self) -> dict:
        """Zwraca statystyki wykrywania"""
        return self.stats.copy()

    def find_keywords_near_position(self, speeches: List[Speech],
                                    target_position: int,
                                    search_radius: int = 500) -> List[KeywordMatch]:
        """
        Znajduje słowa kluczowe w pobliżu określonej pozycji w tekście

        Args:
            speeches: Lista wypowiedzi
            target_position: Docelowa pozycja w tekście
            search_radius: Promień wyszukiwania

        Returns:
            Lista dopasowań w okolicy pozycji
        """
        nearby_matches = []

        for speech in speeches:
            # Sprawdź czy wypowiedź jest w pobliżu target_position
            speech_start = speech.position_in_text
            speech_end = speech_start + len(speech.content)

            if (speech_start - search_radius <= target_position <= speech_end + search_radius):
                matches = self._find_keywords_in_single_speech(speech)
                nearby_matches.extend(matches)

        return nearby_matches
