"""
Moduł do przetwarzania tekstu z transkryptów Sejmu
"""
import re
from typing import List

from SejmBotDetektor.config.keywords import SPEAKER_PATTERNS, MEETING_INFO_PATTERNS
from SejmBotDetektor.utils.logger import get_module_logger


class TextProcessor:
    """Klasa do przetwarzania i analizy tekstu"""

    def __init__(self, debug: bool = False):
        self.debug = debug
        self.logger = get_module_logger("TextProcessor")
        self.speaker_patterns = SPEAKER_PATTERNS
        self.meeting_patterns = MEETING_INFO_PATTERNS

    def clean_text(self, text: str) -> str:
        """
        Czyści tekst z niepotrzebnych elementów

        Args:
            text: Surowy tekst z PDF

        Returns:
            Oczyszczony tekst
        """
        # Usuwa spis treści (zwykle pierwsza strona)
        lines = text.split('\n')
        cleaned_lines = []
        skip_toc = False

        for line in lines:
            line = line.strip()

            # Pomijamy spis treści
            if any(keyword in line.lower() for keyword in ['spis', 'porządek dziennego', 'punkt 1.', 'punkt 2.']):
                skip_toc = True
                continue

            # Kończymy pomijanie gdy trafimy na faktyczną wypowiedź
            if skip_toc and any(pattern_part in line for pattern_part in ['Poseł ', 'Minister ', 'Marszałek ']):
                skip_toc = False

            if not skip_toc and len(line) > 10:  # Pomijamy bardzo krótkie linie
                cleaned_lines.append(line)

        cleaned_text = ' '.join(cleaned_lines)

        if self.debug:
            self.logger.debug(f"Oczyszczono tekst z {len(text)} do {len(cleaned_text)} znaków")

        return cleaned_text

    def find_speaker(self, text: str, position: int) -> str:
        """
        Znajduje mówcę - ulepszona wersja z cache

        Args:
            text: Tekst transkryptu
            position: Pozycja w tekście

        Returns:
            Imię i nazwisko mówcy lub "Nieznany mówca"
        """
        if not hasattr(self, '_speaker_cache'):
            self._speaker_cache = {}

        # Sprawdzamy cache dla tej pozycji (±100 znaków)
        cache_key = position // 100
        if cache_key in self._speaker_cache:
            cached_speaker, cached_pos = self._speaker_cache[cache_key]
            if abs(cached_pos - position) < 500:  # Cache hit
                return cached_speaker

        # Szukamy w fragmencie tekstu przed pozycją
        search_start = max(0, position - 2000)  # Ograniczamy obszar wyszukiwania
        text_before = text[search_start:position + 100]

        found_speaker = "Nieznany mówca"

        for pattern in self.speaker_patterns:
            matches = list(re.finditer(pattern, text_before, re.IGNORECASE))
            if matches:
                last_match = matches[-1]
                found_speaker = last_match.group(1).strip()

                if self.debug:
                    self.logger.debug(f"Znaleziono mówcę '{found_speaker}'")
                break

        # Zapisujemy do cache
        self._speaker_cache[cache_key] = (found_speaker, position)

        return found_speaker

    def extract_meeting_info(self, text: str) -> str:
        """
        Wyciąga informacje o posiedzeniu z tekstu

        Args:
            text: Tekst transkryptu

        Returns:
            Informacje o posiedzeniu
        """
        # Sprawdzamy pierwsze 1000 znaków gdzie zwykle są metadane
        header_text = text[:1000]

        for pattern in self.meeting_patterns:
            match = re.search(pattern, header_text, re.IGNORECASE | re.DOTALL)
            if match:
                meeting_info = match.group(1).strip()

                if self.debug:
                    self.logger.debug(f"Znaleziono info o posiedzeniu: {meeting_info[:50]}...")

                return meeting_info

        if self.debug:
            self.logger.debug("Nie znaleziono informacji o posiedzeniu")

        return "Informacje o posiedzeniu nie zostały znalezione"

    def find_text_position(self, full_text: str, fragment_text: str, fallback_word: str) -> int:
        """
        Znajduje pozycję fragmentu w pełnym tekście

        Args:
            full_text: Pełny tekst dokumentu
            fragment_text: Fragment do znalezienia
            fallback_word: Słowo zapasowe do wyszukania

        Returns:
            Pozycja w tekście lub -1 jeśli nie znaleziono
        """
        # Próbujemy znaleźć pierwsze 50 znaków fragmentu
        search_phrase = fragment_text[:50].strip()
        position = full_text.find(search_phrase)

        if position != -1:
            if self.debug:
                self.logger.debug(f"Znaleziono pozycję fragmentu: {position}")
            return position

        # Jeśli nie, szukamy pojedynczego słowa
        position = full_text.find(fallback_word)

        if self.debug:
            if position != -1:
                self.logger.debug(f"Znaleziono pozycję słowa '{fallback_word}': {position}")
            else:
                self.logger.debug(f"Nie znaleziono pozycji dla fragmentu ani słowa '{fallback_word}'")

        return position

    def extract_context(self, words: List[str], center_index: int,
                        context_before: int, context_after: int) -> str:
        """
        Wyciąga kontekst wokół słowa

        Args:
            words: Lista słów
            center_index: Indeks centralnego słowa
            context_before: Ile słów przed
            context_after: Ile słów po

        Returns:
            Fragment tekstu z kontekstem
        """
        start_idx = max(0, center_index - context_before)
        end_idx = min(len(words), center_index + context_after + 1)

        fragment_words = words[start_idx:end_idx]
        fragment_text = ' '.join(fragment_words)

        # spam:
        # if self.debug:
        #     self.logger.debug(f"Wyciągnięto kontekst [{start_idx}:{end_idx}] = {len(fragment_words)} słów")

        return fragment_text
