"""
Moduł do przetwarzania tekstu z transkryptów Sejmu
"""
import re
from typing import List

from SejmBotDetektor.config.keywords import SPEAKER_PATTERNS, MEETING_INFO_PATTERNS
from SejmBotDetektor.logging.logger import get_module_logger


class TextProcessor:
    """Klasa do przetwarzania i analizy tekstu"""

    def __init__(self, debug: bool = False):
        self.logger = get_module_logger("TextProcessor")
        self.debug = debug
        self._speaker_cache = {}
        self.speaker_patterns = SPEAKER_PATTERNS
        self.meeting_patterns = MEETING_INFO_PATTERNS

    def clean_text(self, text: str) -> str:
        """
        Czyści tekst z niepotrzebnych elementów i łączy słowa oddzielone myślnikami
        """
        # 1. Zachowujemy istniejącą logikę usuwania spisu treści
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

            if not skip_toc and len(line) > 10:  # Pomijamy bardzo krótkie linie
                cleaned_lines.append(line)

        cleaned_text = ' '.join(cleaned_lines)

        # 2. NOWA FUNKCJONALNOŚĆ: Łączenie słów rozdzielonych myślnikami
        cleaned_text = self._fix_hyphenated_words(cleaned_text)

        # 3. Dodatkowe czyszczenie formatowania
        cleaned_text = re.sub(r'\s+', ' ', cleaned_text)  # Wielokrotne spacje -> jedna
        cleaned_text = cleaned_text.strip()

        if self.debug:
            self.logger.debug(f"Oczyszczono tekst z {len(text)} do {len(cleaned_text)} znaków")

        return cleaned_text

    @staticmethod
    def _fix_hyphenated_words(text: str) -> str:
        """
        Funkcja pomocnicza: łączy słowa rozdzielone myślnikami

        Args:
            text: Tekst do przetworzenia

        Returns:
            Tekst z połączonymi słowami (np. "par-lament" -> "parlament")
        """
        # Lista wyjątków — słowa, które powinny zachować myślniki
        hyphen_exceptions = ['ex-minister', 'wice-premier', 'post-komunist', 'anty-europejsk',
                             'pro-unijn', 'pseudo-', 'multi-', 'inter-', 'super-'
                             ]

        def should_preserve_hyphen(before_word: str, after_word: str) -> bool:
            """Sprawdza, czy myślnik powinien zostać zachowany"""
            full_phrase = f"{before_word}-{after_word}".lower()
            return any(exception in full_phrase for exception in hyphen_exceptions)

        def replace_hyphen_match(match):
            before_word = match.group(1)
            after_word = match.group(2)

            # Zachowujemy myślnik w nazwach własnych i wyjątkach
            if should_preserve_hyphen(before_word, after_word):
                return f"{before_word}-{after_word}"

            # Łączymy słowa, jeśli to wygląda na przerwany wyraz:
            # - drugie słowo zaczyna się małą literą
            # - pierwsze słowo jest krótkie (prawdopodobnie sylaba)
            # - drugie słowo to typowa końcówka
            typical_endings = ['lament', 'ment', 'owy', 'ny', 'ski', 'cki', 'nej', 'ty', 'nia', 'arz', 'yczny']

            if (after_word and
                    (after_word[0].islower() or
                     len(before_word) <= 4 or
                     any(after_word.lower().endswith(ending) for ending in typical_endings))):
                return f"{before_word}{after_word}"
            else:
                # Zachowujemy myślnik, ale usuwamy zbędne spacje
                return f"{before_word}-{after_word}"

        # Główne wzorce do łączenia słów z myślnikami
        patterns = [
            r'(\w+)\s*-\s*\n\s*(\w+)',  # "słowo-\nslowo"
            r'(\w+)\s*-\s+(\w+)',  # "słowo- słowo"
            r'(\w+)\s+-\s*(\w+)',  # "słowo -słowo"
            r'(\w{2,})-(\w{2,})'  # "słowo-słowo" (bez spacji)
        ]

        result = text
        for pattern in patterns:
            result = re.sub(pattern, replace_hyphen_match, result)

        return result

    def find_speaker(self, text: str, position: int) -> str:
        """
        Znajduje mówcę wraz z klubem parlamentarnym

        Args:
            text: Tekst transkryptu
            position: Pozycja w tekście

        Returns:
            Imię i nazwisko mówcy z klubem lub "Nieznany mówca"
        """
        if not hasattr(self, '_speaker_cache'):
            self._speaker_cache = {}

        # Sprawdzamy cache dla tej pozycji (±100 znaków)
        cache_key = position // 100
        if cache_key in self._speaker_cache:
            cached_speaker, cached_pos = self._speaker_cache[cache_key]
            if abs(cached_pos - position) < 500:  # Cache hit
                return cached_speaker

        # Szukamy we fragmencie tekstu przed pozycją
        search_start = max(0, position - 2000)  # Ograniczamy obszar wyszukiwania
        text_before = text[search_start:position + 100]

        found_speaker = "Nieznany mówca"

        # Szukamy mówców z klubami
        enhanced_patterns = [
            # Wzorce z klubami w nawiasach
            r'Poseł(?:anka)?\s+([^:()]+)\s*\(([^)]+)\)\s*:',
            r'Marszałek\s+([^:()]+)\s*\(([^)]+)\)\s*:',
            r'Wicemarszałek\s+([^:()]+)\s*\(([^)]+)\)\s*:',
            r'Minister\s+([^:()]+)\s*\(([^)]+)\)\s*:',
            r'Przewodniczący\s+([^:()]+)\s*\(([^)]+)\)\s*:',
            r'Sekretarz\s+([^:()]+)\s*\(([^)]+)\)\s*:',

            # Wzorce bez tytułów ale z klubem
            r'([A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]+\s+[A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]+)\s*\(([^)]+)\)\s*:',

            # Fallback - stare wzorce bez klubu (dla kompatybilności)
            r'Poseł(?:anka)?\s+([^:]+?)\s*:',
            r'Marszałek\s+([^:]+?)\s*:',
            r'Wicemarszałek\s+([^:]+?)\s*:',
            r'Minister\s+([^:]+?)\s*:',
            r'Przewodniczący\s+([^:]+?)\s*:',
            r'Sekretarz\s+([^:]+?)\s*:',

            # Wzorzec ogólny - imię nazwisko bez tytułu
            r'([A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]+\s+[A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]+)\s*:'
        ]

        # Dzielimy tekst na linie i szukamy od końca (ostatni mówca)
        lines = text_before.split('\n')
        lines.reverse()

        for line in lines:
            line = line.strip()
            if not line:
                continue

            for pattern in enhanced_patterns:
                match = re.search(pattern, line, re.IGNORECASE)
                if match:
                    if len(match.groups()) >= 2:
                        # Mamy imię i klub
                        name = match.group(1).strip()
                        club = match.group(2).strip()

                        # Czyścimy nazwę z tytułów
                        name = re.sub(r'^(Poseł|Posłanka|Marszałek|Wicemarszałek|Minister|Przewodniczący|Sekretarz)\s+',
                                      '', name, flags=re.IGNORECASE)
                        name = name.strip()

                        if name and club:
                            found_speaker = f"{name} ({club})"
                            if self.debug:
                                self.logger.debug(f"Znaleziono mówcę z klubem: '{found_speaker}'")
                            break
                    else:
                        # Mamy tylko imię
                        name = match.group(1).strip()
                        name = re.sub(r'^(Poseł|Posłanka|Marszałek|Wicemarszałek|Minister|Przewodniczący|Sekretarz)\s+',
                                      '', name, flags=re.IGNORECASE)
                        name = name.strip()

                        if name:
                            # Sprawdźmy czy w tej samej linii nie ma klubu gdzie indziej
                            club_match = re.search(r'\(([^)]+)\)', line)
                            if club_match:
                                club = club_match.group(1).strip()
                                found_speaker = f"{name} ({club})"
                            else:
                                found_speaker = name  # Zwracamy tylko nazwę

                            if self.debug:
                                self.logger.debug(f"Znaleziono mówcę: '{found_speaker}'")
                            break

            if found_speaker != "Nieznany mówca":
                break

        # Fallback — użyj oryginalnych wzorców z self.speaker_patterns
        if found_speaker == "Nieznany mówca":
            for pattern in self.speaker_patterns:
                matches = list(re.finditer(pattern, text_before, re.IGNORECASE))
                if matches:
                    last_match = matches[-1]
                    name = last_match.group(1).strip()

                    # Czyścimy z tytułów
                    name = re.sub(r'^(Poseł|Posłanka|Marszałek|Wicemarszałek|Minister|Przewodniczący|Sekretarz)\s+', '',
                                  name, flags=re.IGNORECASE)
                    found_speaker = name

                    if self.debug:
                        self.logger.debug(f"Fallback - znaleziono mówcę: '{found_speaker}'")
                    break

        # Zapisujemy do cache
        self._speaker_cache[cache_key] = (found_speaker, position)

        return found_speaker

    def extract_meeting_info(self, text: str) -> str:
        """
        Wyciąga informacje o posiedzeniu z tekstu, generując czytelny format bez znaków nowej linii (\n)

        Args:
            text: Tekst transkryptu

        Returns:
            Sformatowane informacje o posiedzeniu (np. "Sejm RP, Kadencja X, 39. posiedzenie, 22 lipca 2025")
        """
        if not text:
            return "Posiedzenie Sejmu"

        # Sprawdzamy pierwsze 1500 znaków gdzie zwykle są metadane
        header_text = text[:1500]

        meeting_info = {
            'sejm': None,
            'kadencja': None,
            'posiedzenie': None,
            'data': None
        }

        # Nowe, bardziej precyzyjne wzorce
        patterns = {
            'sejm': r'sejm\s+rzeczypospolitej\s+polskiej',
            'kadencja': r'kadencja\s+([IVX]+)',
            'posiedzenie': r'(\d+)\.\s*posiedzeni[a-z]*',
            'data': r'w\s+dniu\s+(\d+\s+[a-zA-ZąćęłńóśźżĄĆĘŁŃÓŚŹŻ]+\s+\d{4})'
        }

        # Sprawdzamy też stare wzorce dla kompatybilności
        for pattern in self.meeting_patterns:
            match = re.search(pattern, header_text, re.IGNORECASE | re.DOTALL)
            if match:
                # Parsujemy znaleziony tekst linia po linii
                found_text = match.group(1).strip()
                lines = found_text.split('\n')

                for line in lines:
                    line_clean = line.strip().lower()
                    if not line_clean:
                        continue

                    # Sprawdzamy każdy wzorzec w każdej linii
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
                                    # Czyścimy datę
                                    date_clean = re.sub(r'\s+', ' ', submatch.group(1)).strip()
                                    meeting_info[key] = date_clean
                break

        # Jeśli nie znaleziono przez stare wzorce, próbujemy bezpośrednio w header_text
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

        # Budujemy czytelny ciąg informacji (oddzielony przecinkami, nie \n)
        result_parts = []

        if meeting_info['sejm']:
            result_parts.append(meeting_info['sejm'])
        if meeting_info['kadencja']:
            result_parts.append(meeting_info['kadencja'])
        if meeting_info['posiedzenie']:
            result_parts.append(meeting_info['posiedzenie'])
        if meeting_info['data']:
            result_parts.append(meeting_info['data'])

        if result_parts:
            result = ', '.join(result_parts)
            if self.debug:
                self.logger.debug(f"Sformatowano info o posiedzeniu: {result}")
            return result
        else:
            if self.debug:
                self.logger.debug("Nie znaleziono informacji o posiedzeniu")
            return "Posiedzenie Sejmu"

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

    @staticmethod
    def extract_context(words: List[str], center_index: int,
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
