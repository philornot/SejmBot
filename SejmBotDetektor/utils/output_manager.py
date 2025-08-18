"""
Moduł do zarządzania wynikami i formatowania wyjścia
"""
import json
from typing import List, Dict

from SejmBotDetektor.models.funny_fragment import FunnyFragment
from SejmBotDetektor.logging.logger import get_module_logger


class OutputManager:
    """Klasa do zarządzania formatowaniem i zapisem wyników"""

    def generate_html_report(self, fragments: List[FunnyFragment], output_file: str = "report.html") -> bool:
        """
        Generuje raport HTML z fragmentami

        Args:
            fragments: Lista fragmentów
            output_file: Nazwa pliku HTML

        Returns:
            True jeśli generowanie się powiodło
        """
        try:
            html_content = self._create_html_report(fragments)

            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(html_content)

            self.logger.info(f"Wygenerowano raport HTML: {output_file}")
            return True

        except Exception as e:
            self.logger.error(f"Błąd podczas generowania raportu HTML: {e}")
            return False

    def generate_folder_html_report(self, results: Dict[str, List[FunnyFragment]],
                                    output_file: str = "folder_report.html") -> bool:
        """
        Generuje raport HTML z wyników z wielu plików

        Args:
            results: Słownik {nazwa_pliku: lista_fragmentów}
            output_file: Nazwa pliku HTML

        Returns:
            True jeśli generowanie się powiodło
        """
        try:
            html_content = self._create_folder_html_report(results)

            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(html_content)

            total_fragments = sum(len(fragments) for fragments in results.values())
            self.logger.info(
                f"Wygenerowano raport HTML z {len(results)} plików ({total_fragments} fragmentów): {output_file}")
            return True

        except Exception as e:
            self.logger.error(f"Błąd podczas generowania raportu HTML folderu: {e}")
            return False

    def _create_html_report(self, fragments: List[FunnyFragment]) -> str:
        """Tworzy treść raportu HTML dla pojedynczych fragmentów"""
        if not fragments:
            return "<html><body><h1>Brak fragmentów do wyświetlenia</h1></body></html>"

        html = """
        <!DOCTYPE html>
        <html lang="pl">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Raport Śmiesznych Fragmentów - Sejm</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }
                .header { background-color: #2c3e50; color: white; padding: 20px; border-radius: 5px; margin-bottom: 20px; }
                .stats { background-color: white; padding: 15px; border-radius: 5px; margin-bottom: 20px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }
                .fragment { background-color: white; margin: 15px 0; padding: 20px; border-radius: 5px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }
                .confidence-high { border-left: 5px solid #27ae60; }
                .confidence-medium { border-left: 5px solid #f39c12; }
                .confidence-low { border-left: 5px solid #e74c3c; }
                .speaker { font-weight: bold; color: #2c3e50; margin-bottom: 10px; }
                .confidence { float: right; padding: 5px 10px; border-radius: 3px; color: white; font-size: 0.9em; }
                .conf-high { background-color: #27ae60; }
                .conf-medium { background-color: #f39c12; }
                .conf-low { background-color: #e74c3c; }
                .keywords { color: #8e44ad; font-style: italic; margin: 10px 0; }
                .text { line-height: 1.6; margin: 15px 0; }
                .meta { font-size: 0.9em; color: #7f8c8d; margin-top: 15px; border-top: 1px solid #ecf0f1; padding-top: 10px; }
                .toc { background-color: white; padding: 15px; border-radius: 5px; margin-bottom: 20px; }
                .toc ul { list-style-type: none; padding: 0; }
                .toc li { padding: 5px 0; border-bottom: 1px solid #ecf0f1; }
                .toc a { text-decoration: none; color: #2c3e50; }
                .toc a:hover { color: #3498db; }
            </style>
        </head>
        <body>
        """

        # Nagłówek
        html += f"""
        <div class="header">
            <h1>️ Detektor Śmiesznych Fragmentów - Sejm RP</h1>
            <p>Raport wygenerowany automatycznie • Łącznie fragmentów: {len(fragments)}</p>
        </div>
        """

        # Statystyki
        if fragments:
            confidences = [f.confidence_score for f in fragments]
            avg_conf = sum(confidences) / len(confidences)
            high_conf = len([f for f in fragments if f.confidence_score >= 0.7])
            medium_conf = len([f for f in fragments if 0.4 <= f.confidence_score < 0.7])
            low_conf = len([f for f in fragments if f.confidence_score < 0.4])

            html += f"""
            <div class="stats">
                <h2> Statystyki</h2>
                <p><strong>Średnia pewność:</strong> {avg_conf:.2f}</p>
                <p><strong>Rozkład jakości:</strong></p>
                <ul>
                    <li>Wysoka jakość (≥0.7): {high_conf} fragmentów</li>
                    <li>Średnia jakość (0.4-0.7): {medium_conf} fragmentów</li>
                    <li>Niska jakość (<0.4): {low_conf} fragmentów</li>
                </ul>
            </div>
            """

        # Spis treści
        html += """
        <div class="toc">
            <h2> Spis treści</h2>
            <ul>
        """

        for i, fragment in enumerate(fragments[:20], 1):  # Maksymalnie 20 w spisie
            conf_class = "high" if fragment.confidence_score >= 0.7 else "medium" if fragment.confidence_score >= 0.4 else "low"
            html += f'<li><a href="#fragment-{i}">Fragment {i} - {fragment.speaker} (pewność: {fragment.confidence_score:.2f})</a></li>'

        if len(fragments) > 20:
            html += f"<li>... i {len(fragments) - 20} więcej fragmentów</li>"

        html += """
            </ul>
        </div>
        """

        # Fragmenty
        for i, fragment in enumerate(fragments, 1):
            conf_class = "high" if fragment.confidence_score >= 0.7 else "medium" if fragment.confidence_score >= 0.4 else "low"

            source_file = "nieznany"
            meeting_info = fragment.meeting_info

            if "| Plik:" in fragment.meeting_info:
                meeting_part, file_part = fragment.meeting_info.split("| Plik:", 1)
                source_file = file_part.strip()
                meeting_info = meeting_part.strip()

            html += f"""
            <div class="fragment confidence-{conf_class}" id="fragment-{i}">
                <div class="speaker">
                     {fragment.speaker}
                    <span class="confidence conf-{conf_class}">{fragment.confidence_score:.3f}</span>
                </div>
                <div class="keywords">️ Słowa kluczowe: {fragment.get_keywords_as_string()}</div>
                <div class="text">{fragment.text}</div>
                <div class="meta">
                     Plik: {source_file}<br>
                    ️ {meeting_info}<br>
                     Pozycja: {fragment.position_in_text if fragment.position_in_text != -1 else 'nieznana'}<br>
                    ⏰ {fragment.timestamp}
                </div>
            </div>
            """

        html += """
        </body>
        </html>
        """

        return html

    def _create_folder_html_report(self, results: Dict[str, List[FunnyFragment]]) -> str:
        """Tworzy treść raportu HTML dla wyników z folderu"""
        if not results:
            return "<html><body><h1>Brak wyników do wyświetlenia</h1></body></html>"

        total_fragments = sum(len(fragments) for fragments in results.values())
        all_fragments = []
        for fragments in results.values():
            all_fragments.extend(fragments)
        all_fragments.sort(key=lambda x: x.confidence_score, reverse=True)

        html = """
        <!DOCTYPE html>
        <html lang="pl">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Raport Śmiesznych Fragmentów - Wiele Plików</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }
                .header { background-color: #2c3e50; color: white; padding: 20px; border-radius: 5px; margin-bottom: 20px; }
                .stats { background-color: white; padding: 15px; border-radius: 5px; margin-bottom: 20px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }
                .file-summary { background-color: white; padding: 15px; border-radius: 5px; margin-bottom: 20px; }
                .file-item { padding: 10px; border-bottom: 1px solid #ecf0f1; }
                .fragment { background-color: white; margin: 15px 0; padding: 20px; border-radius: 5px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }
                .confidence-high { border-left: 5px solid #27ae60; }
                .confidence-medium { border-left: 5px solid #f39c12; }
                .confidence-low { border-left: 5px solid #e74c3c; }
                .speaker { font-weight: bold; color: #2c3e50; margin-bottom: 10px; }
                .confidence { float: right; padding: 5px 10px; border-radius: 3px; color: white; font-size: 0.9em; }
                .conf-high { background-color: #27ae60; }
                .conf-medium { background-color: #f39c12; }
                .conf-low { background-color: #e74c3c; }
                .keywords { color: #8e44ad; font-style: italic; margin: 10px 0; }
                .text { line-height: 1.6; margin: 15px 0; }
                .meta { font-size: 0.9em; color: #7f8c8d; margin-top: 15px; border-top: 1px solid #ecf0f1; padding-top: 10px; }
                .source-file { background-color: #3498db; color: white; padding: 3px 8px; border-radius: 3px; font-size: 0.8em; }
            </style>
        </head>
        <body>
        """

        # Nagłówek
        html += f"""
        <div class="header">
            <h1>️Detektor śmisznych fragmentów</h1>
            <p>Raport wygenerowany automatycznie • {len(results)} plików • {total_fragments} fragmentów</p>
        </div>
        """

        # Podsumowanie plików
        html += """
        <div class="file-summary">
            <h2>Podsumowanie plików</h2>
        """

        sorted_files = sorted(results.items(), key=lambda x: len(x[1]), reverse=True)
        for file_name, fragments in sorted_files:
            if fragments:
                avg_conf = sum(f.confidence_score for f in fragments) / len(fragments)
                best_conf = max(f.confidence_score for f in fragments)
                html += f"""
                <div class="file-item">
                    <strong> {file_name}</strong><br>
                    Fragmenty: {len(fragments)} | Średnia pewność: {avg_conf:.2f} | Najlepsza: {best_conf:.2f}
                </div>
                """

        html += "</div>"

        # Statystyki ogólne
        if all_fragments:
            confidences = [f.confidence_score for f in all_fragments]
            avg_conf = sum(confidences) / len(confidences)
            high_conf = len([f for f in all_fragments if f.confidence_score >= 0.7])
            medium_conf = len([f for f in all_fragments if 0.4 <= f.confidence_score < 0.7])
            low_conf = len([f for f in all_fragments if f.confidence_score < 0.4])

            html += f"""
            <div class="stats">
                <h2> Statystyki ogólne</h2>
                <p><strong>Średnia pewność:</strong> {avg_conf:.2f}</p>
                <p><strong>Rozkład jakości:</strong></p>
                <ul>
                    <li>Wysoka jakość (≥0.7): {high_conf} fragmentów</li>
                    <li>Średnia jakość (0.4-0.7): {medium_conf} fragmentów</li>
                    <li>Niska jakość (<0.4): {low_conf} fragmentów</li>
                </ul>
            </div>
            """

        # Najlepsze fragmenty
        html += "<h2> Najlepsze fragmenty ze wszystkich plików</h2>"

        for i, fragment in enumerate(all_fragments[:50], 1):  # Pokazujemy maksymalnie 50 najlepszych
            conf_class = "high" if fragment.confidence_score >= 0.7 else "medium" if fragment.confidence_score >= 0.4 else "low"

            source_file = "nieznany"
            meeting_info = fragment.meeting_info

            if "| Plik:" in fragment.meeting_info:
                meeting_part, file_part = fragment.meeting_info.split("| Plik:", 1)
                source_file = file_part.strip()
                meeting_info = meeting_part.strip()

            html += f"""
            <div class="fragment confidence-{conf_class}">
                <div class="speaker">
                     {fragment.speaker}
                    <span class="confidence conf-{conf_class}">{fragment.confidence_score:.3f}</span>
                    <span class="source-file">{source_file}</span>
                </div>
                <div class="keywords">️ Słowa kluczowe: {fragment.get_keywords_as_string()}</div>
                <div class="text">{fragment.text}</div>
                <div class="meta">
                    ️ {meeting_info}<br>
                     Pozycja: {fragment.position_in_text if fragment.position_in_text != -1 else 'nieznana'}<br>
                    ⏰ {fragment.timestamp}
                </div>
            </div>
            """

        if len(all_fragments) > 50:
            html += f"<div class='stats'><p>... i {len(all_fragments) - 50} więcej fragmentów</p></div>"

        html += """
        </body>
        </html>
        """

        return html

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

    def save_folder_results_to_json(self, results: Dict[str, List[FunnyFragment]], output_file: str) -> bool:
        """
        Zapisuje wyniki z wielu plików do JSON z zachowaniem struktury

        Args:
            results: Słownik {nazwa_pliku: lista_fragmentów}
            output_file: Ścieżka do pliku wyjściowego

        Returns:
            True jeśli zapis się powiódł
        """
        try:
            # Tworzymy strukturę danych z informacją o plikach źródłowych
            folder_results = {
                "summary": {
                    "total_files": len(results),
                    "total_fragments": sum(len(fragments) for fragments in results.values()),
                    "files_processed": list(results.keys())
                },
                "files": {}
            }

            # Dodajemy fragmenty dla każdego pliku
            for file_name, fragments in results.items():
                folder_results["files"][file_name] = {
                    "fragment_count": len(fragments),
                    "avg_confidence": sum(f.confidence_score for f in fragments) / len(fragments) if fragments else 0,
                    "fragments": [fragment.to_dict() for fragment in fragments]
                }

            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(folder_results, f, ensure_ascii=False, indent=2)

            total_fragments = folder_results["summary"]["total_fragments"]
            self.logger.info(f"Zapisano wyniki z {len(results)} plików ({total_fragments} fragmentów) do {output_file}")

            if self.debug:
                self.logger.debug(f"Pomyślnie zapisano strukturę folderu do JSON: {output_file}")

            return True

        except Exception as e:
            error_msg = f"Błąd podczas zapisywania wyników folderu do {output_file}: {e}"
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
                data = json.load(f)

            # Obsługujemy różne formaty JSON
            fragments = []

            if isinstance(data, list):
                # Prosty format - lista fragmentów
                fragments = [FunnyFragment.from_dict(item) for item in data]
            elif isinstance(data, dict) and "files" in data:
                # Format z wynikami z folderu
                for file_data in data["files"].values():
                    if "fragments" in file_data:
                        fragments.extend([FunnyFragment.from_dict(item) for item in file_data["fragments"]])
            elif isinstance(data, dict) and "fragments" in data:
                # Format z pojedynczymi fragmentami w słowniku
                fragments = [FunnyFragment.from_dict(item) for item in data["fragments"]]

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
            log_message = f"--- FRAGMENT {i + 1} (Pewność: {fragment.confidence_score:.2f}) ---\n"
            log_message += f"Mówca: {fragment.speaker}\n"

            # Wyciągamy informację o pliku źródłowym jeśli jest dostępna
            if "| Plik:" in fragment.meeting_info:
                meeting_part, file_part = fragment.meeting_info.split("| Plik:", 1)
                log_message += f"Plik źródłowy: {file_part.strip()}\n"
                log_message += f"Posiedzenie: {meeting_part.strip()}\n"
            else:
                log_message += f"Posiedzenie: {fragment.meeting_info}\n"

            log_message += f"Słowa kluczowe: {fragment.get_keywords_as_string()}\n"
            log_message += f"Tekst: {fragment.get_short_preview(200)}\n"

            if fragment.position_in_text != -1:
                log_message += f"Pozycja w tekście: {fragment.position_in_text}\n"

            self.logger.info(log_message)

    def print_folder_results(self, results: Dict[str, List[FunnyFragment]], max_files: int = 10):
        """
        Wyświetla wyniki z wielu plików

        Args:
            results: Słownik {nazwa_pliku: lista_fragmentów}
            max_files: Maksymalna liczba plików do szczegółowego pokazania
        """
        if not results:
            self.logger.warning("Brak wyników do wyświetlenia")
            return

        total_fragments = sum(len(fragments) for fragments in results.values())

        self.logger.info(f"\n=== WYNIKI Z {len(results)} PLIKÓW ({total_fragments} fragmentów) ===\n")

        # Sortujemy pliki według liczby fragmentów
        sorted_files = sorted(results.items(), key=lambda x: len(x[1]), reverse=True)

        for i, (file_name, fragments) in enumerate(sorted_files[:max_files], 1):
            if not fragments:
                continue

            avg_confidence = sum(f.confidence_score for f in fragments) / len(fragments)
            best_fragment = max(fragments, key=lambda f: f.confidence_score)

            file_info = (f" {i}. {file_name}\n"
                         f"   Fragmenty: {len(fragments)} | "
                         f"Średnia pewność: {avg_confidence:.2f} | "
                         f"Najlepsza: {best_fragment.confidence_score:.2f}\n"
                         f"   Najlepszy fragment: {best_fragment.get_short_preview(100)}\n")

            self.logger.info(file_info)

        if len(results) > max_files:
            remaining = len(results) - max_files
            self.logger.info(f"... i {remaining} więcej plików")

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

        # Analiza plików źródłowych (jeśli dostępne)
        source_files = {}
        for fragment in fragments:
            if "| Plik:" in fragment.meeting_info:
                file_part = fragment.meeting_info.split("| Plik:", 1)[1].strip()
                source_files[file_part] = source_files.get(file_part, 0) + 1

        if source_files:
            analysis_message = "\n=== ANALIZA PLIKÓW ŹRÓDŁOWYCH ===\n"
            sorted_files = sorted(source_files.items(), key=lambda x: x[1], reverse=True)

            analysis_message += "Fragmenty według plików:\n"
            for file_name, count in sorted_files[:10]:
                analysis_message += f"  {file_name}: {count} fragmentów\n"

            self.logger.info(analysis_message)

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
                    'source_file', 'speaker', 'confidence_score', 'keywords_found', 'text_preview',
                    'position_in_text', 'meeting_info', 'timestamp'
                ]
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

                writer.writeheader()
                for fragment in fragments:
                    # Wyciągamy nazwę pliku źródłowego
                    source_file = "nieznany"
                    meeting_info = fragment.meeting_info

                    if "| Plik:" in fragment.meeting_info:
                        meeting_part, file_part = fragment.meeting_info.split("| Plik:", 1)
                        source_file = file_part.strip()
                        meeting_info = meeting_part.strip()

                    writer.writerow({
                        'source_file': source_file,
                        'speaker': fragment.speaker,
                        'confidence_score': fragment.confidence_score,
                        'keywords_found': fragment.get_keywords_as_string(),
                        'text_preview': fragment.get_short_preview(150),
                        'position_in_text': fragment.position_in_text,
                        'meeting_info': meeting_info,
                        'timestamp': fragment.timestamp
                    })

            self.logger.info(f"Wyeksportowano {len(fragments)} fragmentów do {output_file}")
            return True

        except Exception as e:
            self.logger.error(f"Błąd podczas eksportu do CSV: {e}")
            return False

    def export_folder_results_to_csv(self, results: Dict[str, List[FunnyFragment]], output_file: str) -> bool:
        """
        Eksportuje wyniki z wielu plików do CSV z dodatkową kolumną source_file

        Args:
            results: Słownik {nazwa_pliku: lista_fragmentów}
            output_file: Ścieżka do pliku CSV

        Returns:
            True jeśli eksport się powiódł
        """
        try:
            import csv

            with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = [
                    'source_file', 'speaker', 'confidence_score', 'keywords_found', 'text_preview',
                    'position_in_text', 'meeting_info', 'timestamp'
                ]
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

                writer.writeheader()

                total_exported = 0
                for file_name, fragments in results.items():
                    for fragment in fragments:
                        writer.writerow({
                            'source_file': file_name,
                            'speaker': fragment.speaker,
                            'confidence_score': fragment.confidence_score,
                            'keywords_found': fragment.get_keywords_as_string(),
                            'text_preview': fragment.get_short_preview(150),
                            'position_in_text': fragment.position_in_text,
                            'meeting_info': fragment.meeting_info.split("| Plik:")[
                                0].strip() if "| Plik:" in fragment.meeting_info else fragment.meeting_info,
                            'timestamp': fragment.timestamp
                        })
                        total_exported += 1

            self.logger.info(f"Wyeksportowano {total_exported} fragmentów z {len(results)} plików do {output_file}")
            return True

        except Exception as e:
            self.logger.error(f"Błąd podczas eksportu wyników folderu do CSV: {e}")
            return False
