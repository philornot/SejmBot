"""
Moduł do budowania FunnyFragment z KeywordMatch
Jedna odpowiedzialność: KeywordMatch[] -> FunnyFragment[]
"""
from typing import List, Optional
from dataclasses import dataclass

from SejmBotDetektor.detectors.keyword_detector import KeywordMatch
from SejmBotDetektor.models.funny_fragment import FunnyFragment
from SejmBotDetektor.analyzers.fragment_analyzer import FragmentAnalyzer
from SejmBotDetektor.logging.logger import get_module_logger


@dataclass
class FragmentGroup:
    """Grupa powiązanych KeywordMatch do zbudowania jednego fragmentu"""
    center_match: KeywordMatch  # Główne dopasowanie (najważniejsze)
    related_matches: List[KeywordMatch]  # Powiązane dopasowania w pobliżu
    group_confidence: float  # Pewność całej grupy
    context_start_word: int  # Początek kontekstu (pozycja słowa)
    context_end_word: int  # Koniec kontekstu (pozycja słowa)


class FragmentBuilder:
    """
    Builder do tworzenia FunnyFragment z KeywordMatch
    Jedna odpowiedzialność: KeywordMatch[] -> FunnyFragment[]
    """

    def __init__(self, context_before: int = 50, context_after: int = 100,
                 grouping_distance: int = 50, debug: bool = False):
        """
        Args:
            context_before: Słowa przed słowem kluczowym
            context_after: Słowa po słowie kluczowym
            grouping_distance: Maksymalna odległość między słowami do grupowania
            debug: Tryb debugowania
        """
        self.context_before = context_before
        self.context_after = context_after
        self.grouping_distance = grouping_distance
        self.debug = debug
        self.logger = get_module_logger("FragmentBuilder")

        # Używamy FragmentAnalyzer jako utility do pomocy
        self.analyzer = FragmentAnalyzer(debug=debug)

        self.stats = {
            'input_matches': 0,
            'created_groups': 0,
            'built_fragments': 0,
            'skipped_duplicates': 0,
            'skipped_low_confidence': 0,
            'skipped_too_short': 0,
            'total_confidence': 0.0
        }

    def build_fragments_from_matches(self, matches: List[KeywordMatch],
                                     min_confidence: float = 0.3,
                                     max_fragments: int = 100) -> List[FunnyFragment]:
        """
        Główna metoda: buduje fragmenty z dopasowań słów kluczowych

        Args:
            matches: Lista dopasowań słów kluczowych
            min_confidence: Minimalny próg pewności
            max_fragments: Maksymalna liczba fragmentów

        Returns:
            Lista zbudowanych fragmentów
        """
        if not matches:
            return []

        # Resetujemy statystyki
        self.stats = {k: 0 if not isinstance(v, float) else 0.0 for k, v in self.stats.items()}
        self.stats['input_matches'] = len(matches)

        if self.debug:
            self.logger.debug(f"Budowanie fragmentów z {len(matches)} dopasowań")

        # 1. Grupujemy blisko siebie występujące dopasowania
        groups = self._group_nearby_matches(matches)
        self.stats['created_groups'] = len(groups)

        if self.debug:
            self.logger.debug(f"Utworzono {len(groups)} grup dopasowań")

        # 2. Budujemy fragmenty z każdej grupy
        fragments = []
        existing_texts = []  # Do wykrywania duplikatów

        for group in groups:
            try:
                fragment = self._build_fragment_from_group(group, min_confidence)

                if not fragment:
                    continue

                # Sprawdzamy duplikaty
                if self._is_duplicate_fragment(fragment, existing_texts):
                    self.stats['skipped_duplicates'] += 1
                    if self.debug:
                        self.logger.debug("Fragment jest duplikatem, pomijam")
                    continue

                # Sprawdzamy długość
                if self._is_fragment_too_short(fragment):
                    self.stats['skipped_too_short'] += 1
                    if self.debug:
                        self.logger.debug(f"Fragment za krótki ({len(fragment.text.split())} słów)")
                    continue

                # Sprawdzamy pewność
                if fragment.confidence_score < min_confidence:
                    self.stats['skipped_low_confidence'] += 1
                    if self.debug:
                        self.logger.debug(f"Fragment ma za niską pewność ({fragment.confidence_score:.3f})")
                    continue

                fragments.append(fragment)
                existing_texts.append(fragment.text)

                self.stats['built_fragments'] += 1
                self.stats['total_confidence'] += fragment.confidence_score

                if self.debug:
                    self.logger.debug(f"Zbudowano fragment #{len(fragments)} "
                                      f"(pewność: {fragment.confidence_score:.3f})")

            except Exception as e:
                self.logger.error(f"Błąd budowania fragmentu z grupy: {e}")
                continue

        # 3. Sortujemy według pewności i ograniczamy liczbę
        fragments.sort(key=lambda x: x.confidence_score, reverse=True)
        fragments = fragments[:max_fragments]

        if self.debug:
            self._print_building_stats()

        return fragments

    def _group_nearby_matches(self, matches: List[KeywordMatch]) -> List[FragmentGroup]:
        """
        Grupuje blisko siebie występujące dopasowania

        Args:
            matches: Lista wszystkich dopasowań

        Returns:
            Lista grup dopasowań
        """
        if not matches:
            return []

        # Sortujemy dopasowania według pozycji w wypowiedzi
        sorted_matches = sorted(matches,
                                key=lambda m: (m.speech.speech_index, m.word_position))

        groups = []
        current_group_matches = [sorted_matches[0]]

        for i in range(1, len(sorted_matches)):
            current_match = sorted_matches[i]
            last_match = current_group_matches[-1]

            # Sprawdzamy czy dopasowanie należy do tej samej grupy
            if self._should_group_matches(last_match, current_match):
                current_group_matches.append(current_match)
            else:
                # Finalizujemy obecną grupę
                group = self._create_fragment_group(current_group_matches)
                if group:
                    groups.append(group)

                # Zaczynamy nową grupę
                current_group_matches = [current_match]

        # Dodajemy ostatnią grupę
        if current_group_matches:
            group = self._create_fragment_group(current_group_matches)
            if group:
                groups.append(group)

        return groups

    def _should_group_matches(self, match1: KeywordMatch, match2: KeywordMatch) -> bool:
        """
        Sprawdza czy dwa dopasowania powinny być w tej samej grupie

        Args:
            match1: Pierwsze dopasowanie
            match2: Drugie dopasowanie

        Returns:
            True jeśli powinny być grupowane razem
        """
        # Muszą być z tej samej wypowiedzi
        if match1.speech.speech_index != match2.speech.speech_index:
            return False

        # Sprawdzamy odległość w słowach
        word_distance = abs(match2.word_position - match1.word_position)
        return word_distance <= self.grouping_distance

    def _create_fragment_group(self, matches: List[KeywordMatch]) -> Optional[FragmentGroup]:
        """
        Tworzy grupę fragmentu z listy dopasowań

        Args:
            matches: Lista dopasowań do zgrupowania

        Returns:
            FragmentGroup lub None jeśli nie można utworzyć
        """
        if not matches:
            return None

        # Znajdź najważniejsze dopasowanie (najwyższa pewność)
        center_match = max(matches, key=lambda m: m.confidence_base)
        related_matches = [m for m in matches if m != center_match]

        # Oblicz pewność grupy (średnia ważona)
        total_confidence = sum(m.confidence_base for m in matches)
        group_confidence = total_confidence / len(matches)

        # Określ zakres kontekstu
        speech = center_match.speech
        center_pos = center_match.word_position

        context_start = max(0, center_pos - self.context_before)
        context_end = min(len(speech.content.split()), center_pos + self.context_after)

        return FragmentGroup(
            center_match=center_match,
            related_matches=related_matches,
            group_confidence=group_confidence,
            context_start_word=context_start,
            context_end_word=context_end
        )

    def _build_fragment_from_group(self, group: FragmentGroup,
                                   min_confidence: float) -> Optional[FunnyFragment]:
        """
        Buduje FunnyFragment z FragmentGroup

        Args:
            group: Grupa dopasowań
            min_confidence: Minimalny próg pewności

        Returns:
            FunnyFragment lub None jeśli nie można zbudować
        """
        speech = group.center_match.speech
        words = speech.content.split()

        # Wyciągnij tekst fragmentu z kontekstem
        fragment_words = words[group.context_start_word:group.context_end_word]
        fragment_text = ' '.join(fragment_words).strip()

        if not fragment_text or len(fragment_text) < 10:
            return None

        # Zbierz wszystkie słowa kluczowe z grupy
        all_keywords = [group.center_match.keyword]
        all_keywords.extend([m.keyword for m in group.related_matches])
        unique_keywords = list(set(all_keywords))

        # Oblicz szczegółową pewność używając analyzer
        confidence_details = self.analyzer.calculate_confidence_detailed(
            fragment_text, unique_keywords
        )

        # Określ typ humoru
        humor_type = self.analyzer.determine_humor_type(unique_keywords, fragment_text)

        # Sprawdź czy fragment jest za krótki
        too_short = self.analyzer.is_fragment_too_short(fragment_text, min_words=15)

        # Wyciągnij kontekst zdaniowy z oryginalnego tekstu (jeśli dostępny)
        sentence_context = {'context_before': '', 'context_after': ''}

        # Znajdź pozycję w oryginalnym tekście wypowiedzi
        original_position = speech.position_in_text + group.center_match.char_position

        # Zbuduj informacje o posiedzeniu
        meeting_info = self._build_meeting_info(speech)

        # Utwórz FunnyFragment
        fragment = FunnyFragment(
            text=fragment_text,
            speaker_raw=speech.speaker_with_club,
            meeting_info=meeting_info,
            keywords_found=unique_keywords,
            position_in_text=original_position,
            context_before_words=self.context_before,
            context_after_words=self.context_after,
            confidence_score=confidence_details['confidence'],
            # Szczegółowe score
            keyword_score=confidence_details['keyword_score'],
            context_score=confidence_details['context_score'],
            length_bonus=confidence_details['length_bonus'],
            humor_type=humor_type,
            too_short=too_short,
            context_before=sentence_context['context_before'],
            context_after=sentence_context['context_after']
        )

        return fragment

    def _build_meeting_info(self, speech) -> str:
        """
        Buduje informację o posiedzeniu ze Speech

        Args:
            speech: Obiekt Speech

        Returns:
            Sformatowana informacja o posiedzeniu
        """
        # Jeśli Speech ma informacje o posiedzeniu, użyj ich
        if hasattr(speech, 'meeting_info') and speech.meeting_info:
            return speech.meeting_info

        # Fallback - podstawowa informacja
        return "Posiedzenie Sejmu"

    def _is_duplicate_fragment(self, fragment: FunnyFragment,
                               existing_texts: List[str]) -> bool:
        """
        Sprawdza czy fragment jest duplikatem używając fuzzy matching

        Args:
            fragment: Fragment do sprawdzenia
            existing_texts: Lista istniejących tekstów

        Returns:
            True jeśli jest duplikatem
        """
        return self.analyzer.is_duplicate_fuzzy(fragment.text, existing_texts, threshold=0.85)

    def _is_fragment_too_short(self, fragment: FunnyFragment) -> bool:
        """
        Sprawdza czy fragment jest za krótki

        Args:
            fragment: Fragment do sprawdzenia

        Returns:
            True jeśli za krótki
        """
        return self.analyzer.is_fragment_too_short(fragment.text, min_words=15)

    def build_fragment_from_single_match(self, match: KeywordMatch,
                                         min_confidence: float = 0.3) -> Optional[FunnyFragment]:
        """
        Buduje fragment z pojedynczego dopasowania (utility method)

        Args:
            match: Pojedyncze dopasowanie
            min_confidence: Minimalny próg pewności

        Returns:
            FunnyFragment lub None
        """
        # Utwórz grupę z jednego dopasowania
        group = FragmentGroup(
            center_match=match,
            related_matches=[],
            group_confidence=match.confidence_base,
            context_start_word=max(0, match.word_position - self.context_before),
            context_end_word=min(len(match.speech.content.split()),
                                 match.word_position + self.context_after)
        )

        return self._build_fragment_from_group(group, min_confidence)

    def enhance_fragments_with_context(self, fragments: List[FunnyFragment],
                                       original_text: str = "") -> List[FunnyFragment]:
        """
        Wzbogaca fragmenty o dodatkowy kontekst z oryginalnego tekstu

        Args:
            fragments: Lista fragmentów do wzbogacenia
            original_text: Pełny tekst oryginalny

        Returns:
            Lista wzbogaconych fragmentów
        """
        if not original_text:
            return fragments

        enhanced_fragments = []

        for fragment in fragments:
            try:
                # Znajdź pozycję fragmentu w oryginalnym tekście
                position = fragment.position_in_text

                # Wyciągnij kontekst zdaniowy
                sentence_context = self.analyzer.extract_sentence_context(
                    original_text, position, before_sentences=1, after_sentences=1
                )

                # Zaktualizuj fragment z nowym kontekstem
                enhanced_fragment = FunnyFragment(
                    text=fragment.text,
                    speaker_raw=fragment.speaker_raw,
                    meeting_info=fragment.meeting_info,
                    keywords_found=fragment.keywords_found,
                    position_in_text=fragment.position_in_text,
                    context_before_words=fragment.context_before_words,
                    context_after_words=fragment.context_after_words,
                    confidence_score=fragment.confidence_score,
                    keyword_score=fragment.keyword_score,
                    context_score=fragment.context_score,
                    length_bonus=fragment.length_bonus,
                    humor_type=fragment.humor_type,
                    too_short=fragment.too_short,
                    context_before=sentence_context['context_before'],
                    context_after=sentence_context['context_after']
                )

                enhanced_fragments.append(enhanced_fragment)

            except Exception as e:
                self.logger.error(f"Błąd wzbogacania fragmentu: {e}")
                # Dodaj oryginalny fragment bez zmian
                enhanced_fragments.append(fragment)

        return enhanced_fragments

    def merge_overlapping_fragments(self, fragments: List[FunnyFragment]) -> List[FunnyFragment]:
        """
        Scala nakładające się fragmenty w jeden

        Args:
            fragments: Lista fragmentów do scalenia

        Returns:
            Lista scalonych fragmentów
        """
        if len(fragments) <= 1:
            return fragments

        # Sortuj według pozycji w tekście
        sorted_fragments = sorted(fragments, key=lambda f: f.position_in_text)
        merged = [sorted_fragments[0]]

        for current in sorted_fragments[1:]:
            last_merged = merged[-1]

            # Sprawdź czy fragmenty się nakładają
            if self._fragments_overlap(last_merged, current):
                # Scal fragmenty
                merged_fragment = self._merge_two_fragments(last_merged, current)
                merged[-1] = merged_fragment
            else:
                merged.append(current)

        return merged

    def _fragments_overlap(self, fragment1: FunnyFragment, fragment2: FunnyFragment) -> bool:
        """
        Sprawdza czy dwa fragmenty się nakładają

        Args:
            fragment1: Pierwszy fragment
            fragment2: Drugi fragment

        Returns:
            True jeśli się nakładają
        """
        # Przybliżone pozycje końcowe fragmentów
        f1_end = fragment1.position_in_text + len(fragment1.text)
        f2_start = fragment2.position_in_text

        # Nakładają się jeśli koniec pierwszego jest po początku drugiego
        overlap_threshold = 50  # Minimalne nakładanie się
        return f1_end > f2_start - overlap_threshold

    def _merge_two_fragments(self, fragment1: FunnyFragment, fragment2: FunnyFragment) -> FunnyFragment:
        """
        Scala dwa nakładające się fragmenty

        Args:
            fragment1: Pierwszy fragment
            fragment2: Drugi fragment

        Returns:
            Scalony fragment
        """
        # Wybierz fragment o wyższej pewności jako bazowy
        if fragment1.confidence_score >= fragment2.confidence_score:
            base_fragment = fragment1
            other_fragment = fragment2
        else:
            base_fragment = fragment2
            other_fragment = fragment1

        # Scal słowa kluczowe
        merged_keywords = list(set(base_fragment.keywords_found + other_fragment.keywords_found))

        # Wybierz najlepszy tekst (dłuższy lub o wyższej pewności)
        if len(base_fragment.text) >= len(other_fragment.text):
            merged_text = base_fragment.text
        else:
            merged_text = other_fragment.text

        # Oblicz nową pewność (średnia ważona)
        total_confidence = (base_fragment.confidence_score + other_fragment.confidence_score) / 2

        # Określ nowy typ humoru
        humor_type = self.analyzer.determine_humor_type(merged_keywords, merged_text)

        return FunnyFragment(
            text=merged_text,
            speaker_raw=base_fragment.speaker_raw,
            meeting_info=base_fragment.meeting_info,
            keywords_found=merged_keywords,
            position_in_text=min(fragment1.position_in_text, fragment2.position_in_text),
            context_before_words=base_fragment.context_before_words,
            context_after_words=base_fragment.context_after_words,
            confidence_score=total_confidence,
            keyword_score=(base_fragment.keyword_score + other_fragment.keyword_score) / 2,
            context_score=(base_fragment.context_score + other_fragment.context_score) / 2,
            length_bonus=max(base_fragment.length_bonus, other_fragment.length_bonus),
            humor_type=humor_type,
            too_short=base_fragment.too_short and other_fragment.too_short,
            context_before=base_fragment.context_before or other_fragment.context_before,
            context_after=base_fragment.context_after or other_fragment.context_after
        )

    def _print_building_stats(self):
        """Wyświetla statystyki budowania w trybie debug"""
        self.logger.debug("=== STATYSTYKI BUDOWANIA FRAGMENTÓW ===")
        self.logger.debug(f"Dopasowania wejściowe: {self.stats['input_matches']}")
        self.logger.debug(f"Utworzone grupy: {self.stats['created_groups']}")
        self.logger.debug(f"Zbudowane fragmenty: {self.stats['built_fragments']}")
        self.logger.debug(f"Pominięte duplikaty: {self.stats['skipped_duplicates']}")
        self.logger.debug(f"Pominięte za niską pewność: {self.stats['skipped_low_confidence']}")
        self.logger.debug(f"Pominięte za krótkie: {self.stats['skipped_too_short']}")

        if self.stats['built_fragments'] > 0:
            avg_confidence = self.stats['total_confidence'] / self.stats['built_fragments']
            self.logger.debug(f"Średnia pewność zbudowanych fragmentów: {avg_confidence:.3f}")

    def get_building_stats(self) -> dict:
        """Zwraca statystyki budowania"""
        stats = self.stats.copy()
        if stats['built_fragments'] > 0:
            stats['average_confidence'] = stats['total_confidence'] / stats['built_fragments']
        else:
            stats['average_confidence'] = 0.0
        return stats

    def optimize_fragments_for_output(self, fragments: List[FunnyFragment],
                                      target_count: int = 50) -> List[FunnyFragment]:
        """
        Optymalizuje fragmenty pod kątem wyjścia - wybiera najlepsze

        Args:
            fragments: Lista wszystkich fragmentów
            target_count: Docelowa liczba fragmentów

        Returns:
            Zoptymalizowana lista fragmentów
        """
        if len(fragments) <= target_count:
            return fragments

        # 1. Scal nakładające się fragmenty
        merged_fragments = self.merge_overlapping_fragments(fragments)

        # 2. Sortuj według pewności
        sorted_fragments = sorted(merged_fragments,
                                  key=lambda f: f.confidence_score, reverse=True)

        # 3. Wybierz najlepsze, dbając o różnorodność mówców
        optimized = self._select_diverse_fragments(sorted_fragments, target_count)

        if self.debug:
            self.logger.debug(f"Optymalizacja: {len(fragments)} -> {len(merged_fragments)} -> {len(optimized)}")

        return optimized

    def _select_diverse_fragments(self, fragments: List[FunnyFragment],
                                  target_count: int) -> List[FunnyFragment]:
        """
        Wybiera fragmenty dbając o różnorodność mówców

        Args:
            fragments: Posortowane fragmenty (najlepsze pierwsze)
            target_count: Liczba fragmentów do wybrania

        Returns:
            Lista wybranych fragmentów z różnorodnością
        """
        if len(fragments) <= target_count:
            return fragments

        selected = []
        speaker_counts = {}
        max_per_speaker = max(1, target_count // 10)  # Max 10% fragmentów od jednego mówcy

        for fragment in fragments:
            if len(selected) >= target_count:
                break

            speaker = fragment.speaker_raw
            current_count = speaker_counts.get(speaker, 0)

            # Dodaj fragment jeśli nie przekraczamy limitu na mówcę
            if current_count < max_per_speaker:
                selected.append(fragment)
                speaker_counts[speaker] = current_count + 1

        # Jeśli nie mamy wystarczająco, dodaj pozostałe bez ograniczeń
        if len(selected) < target_count:
            remaining_needed = target_count - len(selected)
            remaining_fragments = [f for f in fragments if f not in selected]
            selected.extend(remaining_fragments[:remaining_needed])

        return selected