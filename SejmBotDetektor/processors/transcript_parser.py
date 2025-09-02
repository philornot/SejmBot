"""
Główny parser transkryptów - jeden przebieg tekstu, pełna struktura wypowiedzi
Łączy funkcjonalność SpeechProcessor i TextProcessor.find_speaker()
"""
import re
from dataclasses import dataclass
from typing import List, Optional, Tuple

from SejmBotDetektor.data.poslowie_manager import PoslowieManager
from SejmBotDetektor.logging.logger import get_module_logger


@dataclass
class Speech:
    """Klasa reprezentująca pojedynczą wypowiedź w transkrypcie"""
    speaker_raw: str  # Surowa nazwa mówcy z transkryptu
    speaker_name: str  # Oczyszczona nazwa mówcy
    speaker_club: Optional[str]  # Klub parlamentarny
    content: str  # Treść wypowiedzi (oczyszczona)
    content_raw: str  # Oryginalna treść (nieoczyszczona)
    position_in_text: int  # Pozycja w oryginalnym tekście
    speech_index: int  # Numer wypowiedzi w transkrypcie
    word_positions: List[int]  # Pozycje poszczególnych słów w content

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

    def get_word_at_position(self, word_index: int) -> Optional[str]:
        """Zwraca słowo na określonej pozycji"""
        words = self.content.split()
        if 0 <= word_index < len(words):
            return words[word_index]
        return None


@dataclass
class ParsedTranscript:
    """Wynik parsowania transkryptu"""
    speeches: List[Speech]
    meeting_info: str
    total_words: int
    parsing_stats: dict


class TranscriptParser:
    """
    Główny parser transkryptów - wykonuje jeden przebieg tekstu i zwraca pełną strukturę
    Łączy funkcjonalność z SpeechProcessor i części TextProcessor
    """

    def __init__(self, debug: bool = False):
        self.debug = debug
        self.logger = get_module_logger("TranscriptParser")
        self.poslowie_manager = PoslowieManager(debug=debug)

        # Wzorce do rozpoznawania mówców (z obu źródeł)
        self.speaker_patterns = [
            # Poseł/Posłanka z tytułem i klubem
            r'Poseł(?:anka)?\s+([^:()]+)\s*\(([^)]+)\)\s*:',
            # Marszałek z klubem
            r'(?:Wice)?marszałek\s+([^:()]+)\s*\(([^)]+)\)\s*:',
            # Minister z klubem
            r'Minister\s+([^:()]+)\s*\(([^)]+)\)\s*:',
            # Przewodniczący z klubem
            r'Przewodniczący\s+([^:()]+)\s*\(([^)]+)\)\s*:',
            # Sekretarz z klubem
            r'Sekretarz\s+([^:()]+)\s*\(([^)]+)\)\s*:',
            # Imię nazwisko z klubem (bez tytułu)
            r'^([A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]+\s+[A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]+(?:\s+[A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]+)?)\s*\(([^)]+)\)\s*:',

            # Wzorce bez klubu (fallback)
            r'Poseł(?:anka)?\s+([^:()]+?)(?:\s*\([^)]+\))?\s*:',
            r'(?:Wice)?marszałek\s+([^:()]+?)(?:\s*\([^)]+\))?\s*:',
            r'Minister\s+([^:()]+?)(?:\s*\([^)]+\))?\s*:',
            r'Przewodniczący\s+([^:()]+?)(?:\s*\([^)]+\))?\s*:',
            r'Sekretarz\s+([^:()]+?)(?:\s*\([^)]+\))?\s*:',
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

        # Wzorce dla meeting info
        self.meeting_patterns = [
            r'sejm\s+rzeczypospolitej\s+polskiej.*?(\d+\s+[a-zA-ZąćęłńóśźżĄĆĘŁŃÓŚŹŻ]+\s+\d{4})',
            r'kadencja\s+([IVX]+).*?(\d+)\.\s*posiedzeni[a-z]*.*?(\d+\s+[a-zA-ZąćęłńóśźżĄĆĘŁŃÓŚŹŻ]+\s+\d{4})',
            r'(\d+)\.\s*posiedzeni[a-z]*.*?kadencj[a-z]*\s+([IVX]+).*?(\d+\s+[a-zA-ZąćęłńóśźżĄĆĘŁŃÓŚŹŻ]+\s+\d{4})'
        ]

        self.stats = {
            'total_speeches': 0,
            'speeches_with_club': 0,
            'speeches_without_club': 0,
            'unknown_speakers': 0,
            'skipped_protocol_elements': 0,
            'total_words': 0,
            'club_matches': 0,
            'club_misses': 0
        }

    def parse_transcript(self, text: str, source_file: str = "") -> ParsedTranscript:
        """
        Główna metoda - jedyny przebieg tekstu zwracający pełną strukturę

        Args:
            text: Tekst transkryptu
            source_file: Nazwa pliku źródłowego

        Returns:
            ParsedTranscript z wypowiedziami i metadanymi
        """
        if not text or not text.strip():
            return ParsedTranscript([], "Posiedzenie Sejmu", 0, {})

        # Resetujemy statystyki
        self.stats = {k: 0 for k in self.stats}

        if self.debug:
            self.logger.debug(f"Parsowanie transkryptu (długość: {len(text)} znaków)")

        # 1. Czyścimy tekst (jedna operacja)
        cleaned_text = self._clean_text_comprehensive(text)

        # 2. Wyciągamy meeting info z oryginału (przed czyszczeniem)
        meeting_info = self._extract_meeting_info(text, source_file)

        # 3. Dzielimy na wypowiedzi w jednym przebiegu
        speeches = self._split_into_speeches(cleaned_text, text)

        # 4. Aktualizujemy statystyki
        self._update_stats(speeches)

        if self.debug:
            self.logger.debug(f"Sparsowano {len(speeches)} wypowiedzi")
            self._print_stats()

        return ParsedTranscript(
            speeches=speeches,
            meeting_info=meeting_info,
            total_words=self.stats['total_words'],
            parsing_stats=self.stats.copy()
        )

    def _clean_text_comprehensive(self, text: str) -> str:
        """
        Kompleksowe czyszczenie tekstu - łączy logikę z TextProcessor
        """
        # 1. Usuwamy spis treści (z TextProcessor)
        lines = text.split('\n')
        cleaned_lines = []
        skip_toc = False

        for line in lines:
            line = line.strip()

            # Pomijamy spis treści
            if any(keyword in line.lower() for keyword in ['spis', 'porządek dziennego', 'punkt 1.', 'punkt 2.']):
                skip_toc = True
                continue

            # Kończymy pomijanie, gdy trafimy na faktyczną wypowiedź
            if skip_toc and any(pattern_part in line for pattern_part in ['Poseł ', 'Minister ', 'Marszałek ']):
                skip_toc = False

            if not skip_toc and len(line) > 10:
                cleaned_lines.append(line)

        cleaned_text = '\n'.join(cleaned_lines)  # Zachowujemy \n dla speech splitting

        # 2. Łączenie słów rozdzielonych myślnikami (z TextProcessor)
        cleaned_text = self._fix_hyphenated_words(cleaned_text)

        # 3. Podstawowe czyszczenie spacji (ale zachowujemy \n)
        cleaned_text = re.sub(r'[ \t]+', ' ', cleaned_text)  # Tylko poziome spacje

        return cleaned_text

    @staticmethod
    def _fix_hyphenated_words(text: str) -> str:
        """
        Łączy słowa rozdzielone myślnikami (z TextProcessor)
        """
        hyphen_exceptions = ['ex-minister', 'wice-premier', 'post-komunist', 'anty-europejsk',
                             'pro-unijn', 'pseudo-', 'multi-', 'inter-', 'super-']

        def should_preserve_hyphen(before_word: str, after_word: str) -> bool:
            full_phrase = f"{before_word}-{after_word}".lower()
            return any(exception in full_phrase for exception in hyphen_exceptions)

        def replace_hyphen_match(match):
            before_word = match.group(1)
            after_word = match.group(2)

            if should_preserve_hyphen(before_word, after_word):
                return f"{before_word}-{after_word}"

            typical_endings = ['lament', 'ment', 'owy', 'ny', 'ski', 'cki', 'nej', 'ty', 'nia', 'arz', 'yczny']

            if (after_word and
                    (after_word[0].islower() or
                     len(before_word) <= 4 or
                     any(after_word.lower().endswith(ending) for ending in typical_endings))):
                return f"{before_word}{after_word}"
            else:
                return f"{before_word}-{after_word}"

        patterns = [
            r'(\w+)\s*-\s*\n\s*(\w+)',  # "słowo-\nslowo"
            r'(\w+)\s*-\s+(\w+)',  # "słowo- słowo"
            r'(\w+)\s+-\s*(\w+)',  # "słowo -słowo"
            r'(\w{2,})-(\w{2,})'  # "słowo-słowo"
        ]

        result = text
        for pattern in patterns:
            result = re.sub(pattern, replace_hyphen_match, result)

        return result

    def _extract_meeting_info(self, text: str, source_file: str = "") -> str:
        """
        Wyciąga informacje o posiedzeniu z tekstu (z TextProcessor)
        """
        if not text:
            return "Posiedzenie Sejmu"

        header_text = text[:1500]

        meeting_info = {
            'sejm': None,
            'kadencja': None,
            'posiedzenie': None,
            'data': None
        }

        patterns = {
            'sejm': r'sejm\s+rzeczypospolitej\s+polskiej',
            'kadencja': r'kadencja\s+([IVX]+)',
            'posiedzenie': r'(\d+)\.\s*posiedzeni[a-z]*',
            'data': r'w\s+dniu\s+(\d+\s+[a-zA-ZąćęłńóśźżĄĆĘŁŃÓŚŹŻ]+\s+\d{4})'
        }

        # Sprawdzamy wzorce meeting_patterns
        for pattern in self.meeting_patterns:
            match = re.search(pattern, header_text, re.IGNORECASE | re.DOTALL)
            if match:
                found_text = match.group(1).strip() if len(match.groups()) > 0 else match.group(0)
                lines = found_text.split('\n')

                for line in lines:
                    line_clean = line.strip().lower()
                    if not line_clean:
                        continue

                    for key, pattern_regex in patterns.items():
                        if meeting_info[key] is None:
                            submatch = re.search(pattern_regex, line_clean, re.IGNORECASE)
                            if submatch:
                                if key == 'sejm':
                                    meeting_info[key] = 'Sejm RP'
                                elif key == 'kadencja':
                                    meeting_info[key] = f"Kadencja {submatch.group(1).upper()}"
                                elif key == 'posiedzenie':
                                    meeting_info[key] = f"{submatch.group(1)}. posiedzenie"
                                elif key == 'data':
                                    date_clean = re.sub(r'\s+', ' ', submatch.group(1)).strip()
                                    meeting_info[key] = date_clean
                break

        # Fallback - sprawdzamy bezpośrednio w header_text
        if all(v is None for v in meeting_info.values()):
            for key, pattern_regex in patterns.items():
                if meeting_info[key] is None:
                    match = re.search(pattern_regex, header_text, re.IGNORECASE)
                    if match:
                        if key == 'sejm':
                            meeting_info[key] = 'Sejm RP'
                        elif key == 'kadencja':
                            meeting_info[key] = f"Kadencja {match.group(1).upper()}"
                        elif key == 'posiedzenie':
                            meeting_info[key] = f"{match.group(1)}. posiedzenie"
                        elif key == 'data':
                            date_clean = re.sub(r'\s+', ' ', match.group(1)).strip()
                            meeting_info[key] = date_clean

        # Budujemy wynik
        result_parts = []
        for key in ['sejm', 'kadencja', 'posiedzenie', 'data']:
            if meeting_info[key]:
                result_parts.append(meeting_info[key])

        if source_file:
            result_parts.append(f"Plik: {source_file}")

        result = ', '.join(result_parts) if result_parts else "Posiedzenie Sejmu"

        if self.debug:
            self.logger.debug(f"Meeting info: {result}")

        return result

    def _split_into_speeches(self, cleaned_text: str, original_text: str) -> List[Speech]:
        """
        Dzieli oczyszczony tekst na wypowiedzi w jednym przebiegu
        """
        speeches = []
        lines = cleaned_text.split('\n')

        current_speaker_raw = None
        current_speaker_name = None
        current_speaker_club = None
        current_content_lines = []
        current_position = 0
        speech_index = 0

        # Mapowanie dla pozycji w oryginalnym tekście
        original_position = 0

        for line_num, line in enumerate(lines):
            line = line.strip()
            line_length = len(line) + 1  # +1 for \n

            # Pomijamy puste linie
            if not line:
                current_position += line_length
                original_position = self._sync_position(original_text, current_position, cleaned_text)
                continue

            # Sprawdzamy czy to protokolarne elementy do pominięcia
            if self._should_skip_line(line):
                self.stats['skipped_protocol_elements'] += 1
                current_position += line_length
                original_position = self._sync_position(original_text, current_position, cleaned_text)
                continue

            # Sprawdzamy czy to nowy mówca
            speaker_match, speaker_name, speaker_club = self._find_speaker_in_line(line)

            if speaker_match:
                # Zapisujemy poprzednią wypowiedź (jeśli była)
                if current_speaker_raw and current_content_lines:
                    speech = self._create_speech(
                        current_speaker_raw,
                        current_speaker_name,
                        current_speaker_club,
                        current_content_lines,
                        original_position - sum(len(l) + 1 for l in current_content_lines),
                        speech_index,
                        original_text
                    )
                    if speech:
                        speeches.append(speech)
                        speech_index += 1

                # Przygotowujemy nową wypowiedź
                current_speaker_raw = speaker_match.replace(':', '').strip()
                current_speaker_name = speaker_name
                current_speaker_club = speaker_club
                current_content_lines = []

                # Sprawdzamy czy po dwukropku jest jeszcze treść
                colon_pos = line.find(':')
                if colon_pos != -1 and colon_pos < len(line) - 1:
                    remaining_content = line[colon_pos + 1:].strip()
                    if remaining_content:
                        current_content_lines.append(remaining_content)

                if self.debug:
                    self.logger.debug(f"Nowy mówca: {current_speaker_name} (klub: {current_speaker_club})")

            else:
                # To część wypowiedzi obecnego mówcy
                if current_speaker_raw:
                    current_content_lines.append(line)
                # Jeśli nie mamy mówcy, pomijamy linię

            current_position += line_length
            original_position = self._sync_position(original_text, current_position, cleaned_text)

        # Zapisujemy ostatnią wypowiedź
        if current_speaker_raw and current_content_lines:
            speech = self._create_speech(
                current_speaker_raw,
                current_speaker_name,
                current_speaker_club,
                current_content_lines,
                original_position - sum(len(l) + 1 for l in current_content_lines),
                speech_index,
                original_text
            )
            if speech:
                speeches.append(speech)

        return speeches

    def _find_speaker_in_line(self, line: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """
        Sprawdza czy linia zawiera nowego mówcę i wyciąga jego dane

        Returns:
            Tuple (speaker_match_text, processed_name, club)
        """
        for pattern in self.speaker_patterns:
            match = re.match(pattern, line, re.IGNORECASE)
            if match:
                groups = match.groups()

                if len(groups) >= 2:
                    # Mamy imię i klub w wzorcu
                    raw_name = groups[0].strip()
                    raw_club = groups[1].strip()

                    # Czyścimy nazwę z tytułów
                    cleaned_name = self._clean_speaker_name(raw_name)

                    # Sprawdzamy klub w PoslowieManager (może mamy lepsze dane)
                    final_name, manager_club = self.poslowie_manager.find_club_for_speaker(cleaned_name)

                    # Preferujemy klub z managera, ale używamy z wzorca jako fallback
                    final_club = manager_club or raw_club

                    return match.group(0), final_name, final_club

                else:
                    # Mamy tylko imię, szukamy klubu w managerze
                    raw_name = groups[0].strip()
                    cleaned_name = self._clean_speaker_name(raw_name)
                    final_name, club = self.poslowie_manager.find_club_for_speaker(cleaned_name)

                    return match.group(0), final_name, club

        return None, None, None

    def _clean_speaker_name(self, raw_name: str) -> str:
        """Czyści nazwę mówcy z tytułów"""
        cleaned = re.sub(
            r'^(Poseł|Posłanka|Marszałek|Wicemarszałek|Minister|Przewodniczący|Sekretarz)\s+',
            '', raw_name, flags=re.IGNORECASE
        ).strip()

        # Usuwamy informacje o klubie z nawiasów (jeśli są)
        cleaned = re.sub(r'\s*\([^)]+\)\s*$', '', cleaned).strip()

        return cleaned

    def _should_skip_line(self, line: str) -> bool:
        """Sprawdza czy linia powinna być pominięta"""
        for pattern in self.skip_patterns:
            if re.match(pattern, line, re.IGNORECASE):
                return True
        return False

    def _sync_position(self, original_text: str, cleaned_position: int, cleaned_text: str) -> int:
        """
        Synchronizuje pozycję między oczyszczonym a oryginalnym tekstem
        """
        # Prosta heurystyka - szukamy podobnej pozycji
        ratio = len(original_text) / max(len(cleaned_text), 1)
        estimated_position = int(cleaned_position * ratio)
        return max(0, min(estimated_position, len(original_text) - 1))

    def _create_speech(self, speaker_raw: str, speaker_name: str, speaker_club: Optional[str],
                       content_lines: List[str], position: int, speech_index: int,
                       original_text: str) -> Optional[Speech]:
        """
        Tworzy obiekt Speech z zebranych danych
        """
        if not content_lines:
            return None

        # Łączymy linie w jeden tekst
        content_raw = ' '.join(content_lines)
        content = content_raw.strip()

        # Pomijamy bardzo krótkie wypowiedzi
        if len(content.split()) < 3:
            return None

        # Budujemy mapowanie pozycji słów
        words = content.split()
        word_positions = []
        current_pos = position

        for word in words:
            word_positions.append(current_pos)
            current_pos += len(word) + 1  # +1 for space

        # Aktualizujemy statystyki klubów
        if speaker_club:
            self.stats['club_matches'] += 1
        else:
            self.stats['club_misses'] += 1

        return Speech(
            speaker_raw=speaker_raw,
            speaker_name=speaker_name or "Nieznany mówca",
            speaker_club=speaker_club,
            content=content,
            content_raw=content_raw,
            position_in_text=max(0, position),
            speech_index=speech_index,
            word_positions=word_positions
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
        self.logger.debug("=== STATYSTYKI PARSOWANIA ===")
        self.logger.debug(f"Łączna liczba wypowiedzi: {self.stats['total_speeches']}")
        self.logger.debug(f"Wypowiedzi z klubem: {self.stats['speeches_with_club']}")
        self.logger.debug(f"Wypowiedzi bez klubu: {self.stats['speeches_without_club']}")
        self.logger.debug(f"Nieznani mówcy: {self.stats['unknown_speakers']}")
        self.logger.debug(
            f"Kluby - znalezione: {self.stats['club_matches']}, nie znalezione: {self.stats['club_misses']}")
        self.logger.debug(f"Pominięte elementy: {self.stats['skipped_protocol_elements']}")
        self.logger.debug(f"Łączna liczba słów: {self.stats['total_words']}")

        if self.stats['total_speeches'] > 0:
            avg_words = self.stats['total_words'] / self.stats['total_speeches']
            self.logger.debug(f"Średnia długość wypowiedzi: {avg_words:.1f} słów")
