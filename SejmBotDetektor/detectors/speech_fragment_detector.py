"""
Moduł do dzielenia transkryptów na wypowiedzi i przypisywania mówców
"""
import re
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass

from SejmBotDetektor.data.poslowie_manager import PoslowieManager
from SejmBotDetektor.logging.logger import get_module_logger


@dataclass
class Speech:
    """Klasa reprezentująca pojedynczą wypowiedź"""
    speaker_raw: str  # Surowa nazwa mówcy z transkryptu
    speaker_name: str  # Oczyszczona nazwa mówcy
    speaker_club: Optional[str]  # Klub parlamentarny
    content: str  # Treść wypowiedzi
    position_in_text: int  # Pozycja w oryginalnym tekście
    speech_index: int  # Numer wypowiedzi w transkrypcie

    @property
    def speaker_with_club(self) -> str:
        """Zwraca mówcę z klubem w formacie 'Imię Nazwisko (Klub)'"""
        if self.speaker_club:
            return f"{self.speaker_name} ({self.speaker_club})"
        return f"{self.speaker_name} (brak klubu)"

    def get_word_count(self) -> int:
        """Zwraca liczbę słów w wypowiedzi"""
        return len(self.content.split())

    def get_preview(self, max_chars: int = 100) -> str:
        """Zwraca podgląd treści wypowiedzi"""
        if len(self.content) <= max_chars:
            return self.content
        return self.content[:max_chars].strip() + "..."


class SpeechProcessor:
    """Klasa do dzielenia transkryptów na wypowiedzi"""

    def __init__(self, debug: bool = False):
        self.debug = debug
        self.logger = get_module_logger("SpeechProcessor")
        self.poslowie_manager = PoslowieManager(debug=debug)

        # Wzorce do rozpoznawania mówców
        self.speaker_patterns = [
            # Poseł/Posłanka z tytułem
            r'Poseł(?:anka)?\s+([^:()]+?)(?:\s*\([^)]+\))?\s*:',
            # Marszałek i Wicemarszałek
            r'(?:Wice)?marszałek\s+([^:()]+?)(?:\s*\([^)]+\))?\s*:',
            # Minister
            r'Minister\s+([^:()]+?)(?:\s*\([^)]+\))?\s*:',
            # Przewodniczący
            r'Przewodniczący\s+([^:()]+?)(?:\s*\([^)]+\))?\s*:',
            # Sekretarz
            r'Sekretarz\s+([^:()]+?)(?:\s*\([^)]+\))?\s*:',
            # Tylko imię i nazwisko (bez tytułu)
            r'^([A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]+\s+[A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]+(?:\s+[A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]+)?)\s*:',
        ]

        # Wzorce do pomijania (protokolarne elementy)
        self.skip_patterns = [
            r'^\s*\(.*\)\s*$',  # Tylko nawiasy z komentarzami
            r'^\s*\[.*\]\s*$',  # Tylko nawiasy kwadratowe
            r'^\s*Głos z sali\s*:',  # Głos z sali
            r'^\s*Głosy z sali\s*:',  # Głosy z sali
            r'^\s*\d+\.\s*$',  # Same numery punktów
            r'^\s*Punkt\s+\d+',  # Punkt porządku dziennego
            r'^\s*Przerwa\s*$',  # Przerwy
            r'^\s*Koniec\s+posiedzenia',  # Koniec posiedzenia
        ]

        self.stats = {
            'total_speeches': 0,
            'speeches_with_club': 0,
            'speeches_without_club': 0,
            'unknown_speakers': 0,
            'skipped_protocol_elements': 0,
            'total_words': 0
        }

    def split_text_into_speeches(self, text: str, meeting_info: str = "") -> List[Speech]:
        """
        Dzieli tekst transkryptu na wypowiedzi

        Args:
            text: Tekst transkryptu
            meeting_info: Informacje o posiedzeniu

        Returns:
            Lista wypowiedzi
        """
        if not text or not text.strip():
            return []

        # Resetujemy statystyki
        self.stats = {k: 0 for k in self.stats}

        if self.debug:
            self.logger.debug(f"Dzielenie tekstu na wypowiedzi (długość: {len(text)} znaków)")

        speeches = []
        lines = text.split('\n')
        current_speaker_raw = None
        current_speaker_name = None
        current_speaker_club = None
        current_content_lines = []
        current_position = 0
        speech_index = 0

        for line_num, line in enumerate(lines):
            line = line.strip()

            # Pomijamy puste linie
            if not line:
                current_position += 1  # \n
                continue

            # Sprawdzamy czy to protokolarne elementy do pominięcia
            if self._should_skip_line(line):
                self.stats['skipped_protocol_elements'] += 1
                current_position += len(line) + 1
                continue

            # Sprawdzamy czy to nowy mówca
            speaker_match = self._find_speaker_in_line(line)

            if speaker_match:
                # Zapisujemy poprzednią wypowiedź (jeśli była)
                if current_speaker_raw and current_content_lines:
                    speech = self._create_speech(
                        current_speaker_raw,
                        current_speaker_name,
                        current_speaker_club,
                        current_content_lines,
                        current_position - sum(len(l) + 1 for l in current_content_lines),
                        speech_index
                    )
                    if speech:
                        speeches.append(speech)
                        speech_index += 1

                # Przygotowujemy nową wypowiedź
                current_speaker_raw = speaker_match.group(0).replace(':', '').strip()
                current_speaker_name, current_speaker_club = self._process_speaker(speaker_match.group(1))
                current_content_lines = []

                # Sprawdzamy czy po dwukropku jest jeszcze treść w tej samej linii
                colon_pos = line.find(':')
                if colon_pos != -1 and colon_pos < len(line) - 1:
                    remaining_content = line[colon_pos + 1:].strip()
                    if remaining_content:
                        current_content_lines.append(remaining_content)

                if self.debug:
                    self.logger.debug(f"Nowy mówca: {current_speaker_name} (klub: {current_speaker_club})")

            else:
                # To część wypowiedzi obecnego mówcy
                if current_speaker_raw:  # Mamy już mówcę
                    current_content_lines.append(line)
                # Jeśli nie mamy mówcy, pomijamy linię (prawdopodobnie nagłówek/stopka)

            current_position += len(line) + 1

        # Zapisujemy ostatnią wypowiedź
        if current_speaker_raw and current_content_lines:
            speech = self._create_speech(
                current_speaker_raw,
                current_speaker_name,
                current_speaker_club,
                current_content_lines,
                current_position - sum(len(l) + 1 for l in current_content_lines),
                speech_index
            )
            if speech:
                speeches.append(speech)

        self._update_stats(speeches)

        if self.debug:
            self.logger.debug(f"Podzielono na {len(speeches)} wypowiedzi")
            self._print_stats()

        return speeches

    def _find_speaker_in_line(self, line: str) -> Optional[re.Match]:
        """Sprawdza czy linia zawiera nowego mówcę"""
        for pattern in self.speaker_patterns:
            match = re.match(pattern, line, re.IGNORECASE)
            if match:
                return match
        return None

    def _should_skip_line(self, line: str) -> bool:
        """Sprawdza czy linia powinna być pominięta"""
        for pattern in self.skip_patterns:
            if re.match(pattern, line, re.IGNORECASE):
                return True
        return False

    def _process_speaker(self, raw_speaker_name: str) -> Tuple[str, Optional[str]]:
        """
        Przetwarza surową nazwę mówcy i znajduje klub

        Args:
            raw_speaker_name: Surowa nazwa z wzorca regex

        Returns:
            Tuple (oczyszczona_nazwa, klub)
        """
        # Czyścimy nazwę z tytułów
        cleaned_name = re.sub(
            r'^(Poseł|Posłanka|Marszałek|Wicemarszałek|Minister|Przewodniczący|Sekretarz)\s+',
            '', raw_speaker_name, flags=re.IGNORECASE
        ).strip()

        # Usuwamy ewentualne informacje o klubie z nawiasów (będziemy szukać w bazie)
        cleaned_name = re.sub(r'\s*\([^)]+\)\s*$', '', cleaned_name).strip()

        # Używamy PoslowieManager do znalezienia klubu
        final_name, club = self.poslowie_manager.find_club_for_speaker(cleaned_name)

        return final_name, club

    def _create_speech(self, speaker_raw: str, speaker_name: str, speaker_club: Optional[str],
                      content_lines: List[str], position: int, speech_index: int) -> Optional[Speech]:
        """Tworzy obiekt Speech z zebranych danych"""

        if not content_lines:
            return None

        # Łączymy linie w jeden tekst
        content = ' '.join(content_lines).strip()

        # Pomijamy bardzo krótkie wypowiedzi (prawdopodobnie błędy parsowania)
        if len(content.split()) < 3:
            return None

        return Speech(
            speaker_raw=speaker_raw,
            speaker_name=speaker_name,
            speaker_club=speaker_club,
            content=content,
            position_in_text=max(0, position),
            speech_index=speech_index
        )

    def _update_stats(self, speeches: List[Speech]):
        """Aktualizuje statystyki"""
        self.stats['total_speeches'] = len(speeches)

        for speech in speeches:
            self.stats['total_words'] += speech.get_word_count()

            if speech.speaker_name == "Nieznany mówca":
                self.stats['unknown_speakers'] += 1
            elif speech.speaker_club:
                self.stats['speeches_with_club'] += 1
            else:
                self.stats['speeches_without_club'] += 1

    def _print_stats(self):
        """Wyświetla statystyki w trybie debug"""
        self.logger.debug("=== STATYSTYKI PODZIAŁU ===")
        self.logger.debug(f"Łączna liczba wypowiedzi: {self.stats['total_speeches']}")
        self.logger.debug(f"Wypowiedzi z klubem: {self.stats['speeches_with_club']}")
        self.logger.debug(f"Wypowiedzi bez klubu: {self.stats['speeches_without_club']}")
        self.logger.debug(f"Nieznani mówcy: {self.stats['unknown_speakers']}")
        self.logger.debug(f"Pominięte elementy protokolarne: {self.stats['skipped_protocol_elements']}")
        self.logger.debug(f"Łączna liczba słów: {self.stats['total_words']}")

        if self.stats['total_speeches'] > 0:
            avg_words = self.stats['total_words'] / self.stats['total_speeches']
            self.logger.debug(f"Średnia długość wypowiedzi: {avg_words:.1f} słów")

    def filter_speeches_by_length(self, speeches: List[Speech],
                                 min_words: int = 10, max_words: int = 5000) -> List[Speech]:
        """
        Filtruje wypowiedzi według długości

        Args:
            speeches: Lista wypowiedzi
            min_words: Minimalna liczba słów
            max_words: Maksymalna liczba słów

        Returns:
            Przefiltrowana lista wypowiedzi
        """
        filtered = []

        for speech in speeches:
            word_count = speech.get_word_count()
            if min_words <= word_count <= max_words:
                filtered.append(speech)
            elif self.debug:
                if word_count < min_words:
                    self.logger.debug(f"Pominięto za krótką wypowiedź: {word_count} słów")
                else:
                    self.logger.debug(f"Pominięto za długą wypowiedź: {word_count} słów")

        if self.debug:
            self.logger.debug(f"Przefiltrowano z {len(speeches)} do {len(filtered)} wypowiedzi")

        return filtered

    def get_speeches_by_club(self, speeches: List[Speech]) -> Dict[str, List[Speech]]:
        """Grupuje wypowiedzi według klubów parlamentarnych"""
        clubs = {}

        for speech in speeches:
            club_key = speech.speaker_club or "Bez klubu"
            if club_key not in clubs:
                clubs[club_key] = []
            clubs[club_key].append(speech)

        return clubs

    def get_stats(self) -> dict:
        """Zwraca statystyki przetwarzania"""
        stats = self.stats.copy()
        stats['poslowie_manager_stats'] = self.poslowie_manager.get_stats()
        return stats

    def print_speeches_summary(self, speeches: List[Speech], max_speeches: int = 10):
        """Wyświetla podsumowanie wypowiedzi"""
        self.logger.info(f"=== PODSUMOWANIE {len(speeches)} WYPOWIEDZI ===")

        # Sortujemy według długości (najdłuższe pierwsze)
        sorted_speeches = sorted(speeches, key=lambda s: s.get_word_count(), reverse=True)

        for i, speech in enumerate(sorted_speeches[:max_speeches], 1):
            word_count = speech.get_word_count()
            preview = speech.get_preview(80)

            self.logger.info(f"{i}. {speech.speaker_with_club}")
            self.logger.info(f"   Słów: {word_count}, Podgląd: {preview}")

        if len(speeches) > max_speeches:
            self.logger.info(f"... i {len(speeches) - max_speeches} więcej")

        # Statystyki klubów
        clubs = self.get_speeches_by_club(speeches)
        self.logger.info(f"\n=== STATYSTYKI KLUBÓW ===")

        sorted_clubs = sorted(clubs.items(), key=lambda x: len(x[1]), reverse=True)
        for club, club_speeches in sorted_clubs[:10]:
            total_words = sum(s.get_word_count() for s in club_speeches)
            self.logger.info(f"{club}: {len(club_speeches)} wypowiedzi, {total_words} słów")