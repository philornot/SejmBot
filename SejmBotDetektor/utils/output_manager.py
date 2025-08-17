"""
Moduł do zarządzania wynikami i formatowania wyjścia
"""
import json
from typing import List

from SejmBotDetektor.models.funny_fragment import FunnyFragment
from SejmBotDetektor.utils.logger import get_module_logger


class OutputManager:
    """Klasa do zarządzania formatowaniem i zapisem wyników"""

    def __init__(self, debug: bool = False):
        self.logger = get_module_logger("OutputManager")
        self.debug = debug

    def save_fragments_to_json(self, fragments: List[FunnyFragment], output_file: str) -> bool:
        """
        Zapisuje fragmenty do pliku JSON

        Args:
            fragments: Lista fragmentów do zapisania
            output_file: Ścieżka do pliku wyjściowego

        Returns:
            True jeśli zapis się powiódł
        """
        try:
            fragments_dict = [fragment.to_dict() for fragment in fragments]

            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(fragments_dict, f, ensure_ascii=False, indent=2)

            self.logger.info(f"Zapisano {len(fragments)} fragmentów do {output_file}")

            if self.debug:
                self.logger.debug(f"Pomyślnie zapisano plik JSON: {output_file}")

            return True

        except Exception as e:
            error_msg = f"Błąd podczas zapisywania do {output_file}: {e}"
            self.logger.error(error_msg)
            return False

    def load_fragments_from_json(self, input_file: str) -> List[FunnyFragment]:
        """
        Wczytuje fragmenty z pliku JSON

        Args:
            input_file: Ścieżka do pliku JSON

        Returns:
            Lista fragmentów lub pusta lista w przypadku błędu
        """
        try:
            with open(input_file, 'r', encoding='utf-8') as f:
                fragments_data = json.load(f)

            fragments = [FunnyFragment.from_dict(data) for data in fragments_data]

            if self.debug:
                self.logger.debug(f"Wczytano {len(fragments)} fragmentów z {input_file}")

            return fragments

        except FileNotFoundError:
            self.logger.error(f"Plik {input_file} nie został znaleziony")
            return []
        except json.JSONDecodeError as e:
            self.logger.error(f"Błąd parsowania JSON w pliku {input_file}: {e}")
            return []
        except Exception as e:
            self.logger.error(f"Błąd podczas wczytywania z {input_file}: {e}")
            return []

    def print_fragments(self, fragments: List[FunnyFragment], max_fragments: int = 10):
        """
        Wyświetla fragmenty w konsoli

        Args:
            fragments: Lista fragmentów do wyświetlenia
            max_fragments: Maksymalna liczba fragmentów do pokazania
        """
        if not fragments:
            self.logger.warning("Brak fragmentów do wyświetlenia")
            return

        self.logger.info(
            f"\n=== NAJLEPSZE FRAGMENTY (pokazano {min(len(fragments), max_fragments)} z {len(fragments)}) ===\n")

        for i, fragment in enumerate(fragments[:max_fragments]):
            log_message = (
                f"--- FRAGMENT {i + 1} (Pewność: {fragment.confidence_score:.2f}) ---\n"
                f"Mówca: {fragment.speaker}\n"
                f"Słowa kluczowe: {fragment.get_keywords_as_string()}\n"
                f"Tekst: {fragment.get_short_preview(200)}\n"
            )
            if fragment.position_in_text != -1:
                log_message += f"Pozycja w tekście: {fragment.position_in_text}\n"

            self.logger.info(log_message)

    def print_fragments_summary(self, fragments: List[FunnyFragment]):
        """
        Wyświetla podsumowanie statystyk fragmentów

        Args:
            fragments: Lista fragmentów do analizy
        """
        if not fragments:
            self.logger.warning("Brak fragmentów do podsumowania")
            return

        summary_message = (
            f"\n=== PODSUMOWANIE FRAGMENTÓW ===\n"
            f"Łączna liczba fragmentów: {len(fragments)}\n"
        )

        if fragments:
            confidences = [f.confidence_score for f in fragments]
            avg_confidence = sum(confidences) / len(confidences)
            min_confidence = min(confidences)
            max_confidence = max(confidences)

            summary_message += (
                f"Średnia pewność: {avg_confidence:.2f}\n"
                f"Minimalna pewność: {min_confidence:.2f}\n"
                f"Maksymalna pewność: {max_confidence:.2f}\n"
            )

        self.logger.info(summary_message)

        # Analiza mówców
        speakers = {}
        for fragment in fragments:
            speakers[fragment.speaker] = speakers.get(fragment.speaker, 0) + 1

        analysis_message = "\n=== ANALIZA FRAGMENTÓW ===\n"

        # Top 5 mówców
        analysis_message += "\nTop 5 mówców:\n"
        sorted_speakers = sorted(speakers.items(), key=lambda x: x[1], reverse=True)
        for speaker, count in sorted_speakers[:5]:
            analysis_message += f"  {speaker}: {count} fragmentów\n"

        # Analiza słów kluczowych
        all_keywords = []
        for fragment in fragments:
            all_keywords.extend(fragment.keywords_found)

        if all_keywords:
            keyword_counts = {}
            for keyword in all_keywords:
                keyword_counts[keyword] = keyword_counts.get(keyword, 0) + 1

            analysis_message += "\nNajczęściej występujące słowa kluczowe:\n"
            sorted_keywords = sorted(keyword_counts.items(), key=lambda x: x[1], reverse=True)
            for keyword, count in sorted_keywords[:10]:
                analysis_message += f"  '{keyword}': {count} razy\n"

        self.logger.info(analysis_message)

    def export_fragments_to_csv(self, fragments: List[FunnyFragment], output_file: str) -> bool:
        """
        Eksportuje fragmenty do pliku CSV

        Args:
            fragments: Lista fragmentów do eksportu
            output_file: Ścieżka do pliku CSV

        Returns:
            True jeśli eksport się powiódł
        """
        try:
            import csv

            with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = [
                    'speaker', 'confidence_score', 'keywords_found', 'text_preview',
                    'position_in_text', 'meeting_info', 'timestamp'
                ]
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

                writer.writeheader()
                for fragment in fragments:
                    writer.writerow({
                        'speaker': fragment.speaker,
                        'confidence_score': fragment.confidence_score,
                        'keywords_found': fragment.get_keywords_as_string(),
                        'text_preview': fragment.get_short_preview(150),
                        'position_in_text': fragment.position_in_text,
                        'meeting_info': fragment.meeting_info,
                        'timestamp': fragment.timestamp
                    })

            self.logger.info(f"Wyeksportowano {len(fragments)} fragmentów do {output_file}")
            return True

        except Exception as e:
            self.logger.error(f"Błąd podczas eksportu do CSV: {e}")
            return False
