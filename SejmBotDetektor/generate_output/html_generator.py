"""
Moduł do generowania raportów HTML
"""
from pathlib import Path
from typing import List, Dict

from SejmBotDetektor.logging.logger import get_module_logger
from SejmBotDetektor.models.funny_fragment import FunnyFragment


class HtmlGenerator:
    """Klasa odpowiedzialna za generowanie raportów HTML"""

    def __init__(self, debug: bool = False):
        self.logger = get_module_logger("HtmlGenerator")
        self.debug = debug

    def generate_report(self, fragments: List[FunnyFragment], output_file: str,
                        title: str = "Raport Śmiesznych Fragmentów") -> bool:
        """
        Generuje raport HTML z fragmentami

        Args:
            fragments: Lista fragmentów
            output_file: Nazwa pliku HTML
            title: Tytuł raportu

        Returns:
            True jeśli generowanie się powiodło
        """
        try:
            html_content = self._create_single_file_report(fragments, title)
            self._write_html_file(html_content, output_file)

            self.logger.info(f"Wygenerowano raport HTML: {output_file}")
            return True

        except Exception as e:
            self.logger.error(f"Błąd podczas generowania raportu HTML: {e}")
            return False

    def generate_folder_report(self, results: Dict[str, List[FunnyFragment]], output_file: str) -> bool:
        """
        Generuje raport HTML z wyników z wielu plików

        Args:
            results: Słownik {nazwa_pliku: lista_fragmentów}
            output_file: Nazwa pliku HTML

        Returns:
            True jeśli generowanie się powiodło
        """
        try:
            html_content = self._create_folder_report(results)
            self._write_html_file(html_content, output_file)

            total_fragments = sum(len(fragments) for fragments in results.values())
            self.logger.info(
                f"Wygenerowano raport HTML z {len(results)} plików ({total_fragments} fragmentów): {output_file}")
            return True

        except Exception as e:
            self.logger.error(f"Błąd podczas generowania raportu HTML folderu: {e}")
            return False

    def _create_single_file_report(self, fragments: List[FunnyFragment], title: str) -> str:
        """Tworzy treść raportu HTML dla pojedynczego pliku lub listy fragmentów"""
        if not fragments:
            return self._create_empty_report("Brak fragmentów do wyświetlenia")

        # Podstawowa struktura HTML
        html = self._get_html_template(title, len(fragments))

        # Statystyki
        html += self._generate_stats_section(fragments)

        # Spis treści (tylko dla dłuższych raportów)
        if len(fragments) > 5:
            html += self._generate_toc(fragments)

        # Fragmenty
        html += self._generate_fragments_section(fragments)

        html += "</body></html>"
        return html

    def _create_folder_report(self, results: Dict[str, List[FunnyFragment]]) -> str:
        """Tworzy treść raportu HTML dla wyników z folderu"""
        if not results:
            return self._create_empty_report("Brak wyników do wyświetlenia")

        total_fragments = sum(len(fragments) for fragments in results.values())
        all_fragments = []
        for fragments in results.values():
            all_fragments.extend(fragments)
        all_fragments.sort(key=lambda x: x.confidence_score, reverse=True)

        # Podstawowa struktura
        html = self._get_html_template(f"Raport z {len(results)} plików", total_fragments)

        # Podsumowanie plików
        html += self._generate_file_summary(results)

        # Statystyki ogólne
        html += self._generate_stats_section(all_fragments, "Statystyki ogólne")

        # Najlepsze fragmenty (maksymalnie 30)
        html += "<h2>🏆 Najlepsze fragmenty ze wszystkich plików</h2>"
        html += self._generate_fragments_section(all_fragments[:30], show_source_file=True)

        if len(all_fragments) > 30:
            html += f"<div class='info-box'><p>Pokazano 30 najlepszych fragmentów z {len(all_fragments)}. Pełne wyniki znajdziesz w plikach JSON/CSV.</p></div>"

        html += "</body></html>"
        return html

    def _get_html_template(self, title: str, fragment_count: int) -> str:
        """Zwraca podstawowy szablon HTML"""
        return f"""
        <!DOCTYPE html>
        <html lang="pl">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>{title}</title>
            <style>
                {self._get_css_styles()}
            </style>
        </head>
        <body>
        <div class="header">
            <h1>{title}</h1>
            <p>Raport wygenerowany automatycznie • {fragment_count} fragmentów</p>
        </div>
        """

    def _get_css_styles(self) -> str:
        """Zwraca style CSS dla raportu"""
        return """
                body { font-family: 'Segoe UI', Arial, sans-serif; margin: 20px; background-color: #f8f9fa; line-height: 1.6; }
                .header { background: linear-gradient(135deg, #2c3e50, #3498db); color: white; padding: 25px; border-radius: 8px; margin-bottom: 25px; text-align: center; }
                .header h1 { margin: 0; font-size: 2.2em; }
                .header p { margin: 10px 0 0 0; opacity: 0.9; }
                .stats, .file-summary, .toc, .info-box { background-color: white; padding: 20px; border-radius: 8px; margin-bottom: 25px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
                .stats h2, .file-summary h2, .toc h2 { color: #2c3e50; margin-top: 0; }
                .fragment { background-color: white; margin: 20px 0; padding: 25px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); transition: transform 0.2s; }
                .fragment:hover { transform: translateY(-2px); }
                .confidence-high { border-left: 6px solid #27ae60; }
                .confidence-medium { border-left: 6px solid #f39c12; }
                .confidence-low { border-left: 6px solid #e74c3c; }
                .speaker { font-weight: bold; color: #2c3e50; margin-bottom: 15px; font-size: 1.1em; }
                .confidence { float: right; padding: 8px 15px; border-radius: 20px; color: white; font-size: 0.9em; font-weight: bold; }
                .conf-high { background-color: #27ae60; }
                .conf-medium { background-color: #f39c12; }
                .conf-low { background-color: #e74c3c; }
                .keywords { color: #8e44ad; font-style: italic; margin: 15px 0; background-color: #f8f9ff; padding: 10px; border-radius: 5px; }
                .text { line-height: 1.8; margin: 20px 0; font-size: 1.05em; }
                .meta { font-size: 0.95em; color: #7f8c8d; margin-top: 20px; border-top: 2px solid #ecf0f1; padding-top: 15px; }
                .source-file { background-color: #3498db; color: white; padding: 4px 10px; border-radius: 15px; font-size: 0.8em; margin-left: 10px; }
                .file-item { padding: 15px; border-bottom: 1px solid #ecf0f1; border-radius: 5px; margin-bottom: 10px; }
                .file-item:last-child { border-bottom: none; }
                .file-item:hover { background-color: #f8f9fa; }
                .toc ul { list-style-type: none; padding: 0; }
                .toc li { padding: 8px 0; border-bottom: 1px solid #ecf0f1; }
                .toc a { text-decoration: none; color: #2c3e50; transition: color 0.2s; }
                .toc a:hover { color: #3498db; }
                .info-box { background-color: #e8f4f8; border-left: 4px solid #3498db; }
                .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin-top: 15px; }
                .stat-item { background-color: #f8f9fa; padding: 15px; border-radius: 5px; text-align: center; }
                .stat-value { font-size: 1.8em; font-weight: bold; color: #3498db; }
                .stat-label { color: #7f8c8d; font-size: 0.9em; }
        """

    def _generate_stats_section(self, fragments: List[FunnyFragment], section_title: str = "📊 Statystyki") -> str:
        """Generuje sekcję ze statystykami"""
        if not fragments:
            return ""

        confidences = [f.confidence_score for f in fragments]
        avg_conf = sum(confidences) / len(confidences)
        high_conf = len([f for f in fragments if f.confidence_score >= 0.7])
        medium_conf = len([f for f in fragments if 0.4 <= f.confidence_score < 0.7])
        low_conf = len([f for f in fragments if f.confidence_score < 0.4])

        return f"""
        <div class="stats">
            <h2>{section_title}</h2>
            <div class="stats-grid">
                <div class="stat-item">
                    <div class="stat-value">{avg_conf:.2f}</div>
                    <div class="stat-label">Średnia pewność</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value">{high_conf}</div>
                    <div class="stat-label">Wysoka jakość (≥0.7)</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value">{medium_conf}</div>
                    <div class="stat-label">Średnia jakość (0.4-0.7)</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value">{low_conf}</div>
                    <div class="stat-label">Niska jakość (<0.4)</div>
                </div>
            </div>
        </div>
        """

    def _generate_file_summary(self, results: Dict[str, List[FunnyFragment]]) -> str:
        """Generuje podsumowanie plików"""
        html = """
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
                    <strong>{file_name}</strong><br>
                    <small>Fragmenty: {len(fragments)} | Średnia pewność: {avg_conf:.2f} | Najlepsza: {best_conf:.2f}</small>
                </div>
                """

        html += "</div>"
        return html

    def _generate_toc(self, fragments: List[FunnyFragment]) -> str:
        """Generuje spis treści"""
        html = """
        <div class="toc">
            <h2>Najlepsze fragmenty</h2>
            <ul>
        """

        for i, fragment in enumerate(fragments[:15], 1):
            # Wyświetlanie mówcy w spisie treści
            speaker_info = fragment.speaker
            if speaker_info.get('club'):
                speaker_display = f"{speaker_info['name']} ({speaker_info['club']})"
            else:
                speaker_display = f"{speaker_info['name']} (brak klubu)"

            html += f'<li><a href="#fragment-{i}">Fragment {i}: {speaker_display} (pewność: {fragment.confidence_score:.2f})</a></li>'

        if len(fragments) > 15:
            html += f"<li><em>... i {len(fragments) - 15} więcej fragmentów</em></li>"

        html += """
            </ul>
        </div>
        """
        return html

    def _generate_fragments_section(self, fragments: List[FunnyFragment], show_source_file: bool = False) -> str:
        """Generuje sekcję z fragmentami"""
        html = ""

        for i, fragment in enumerate(fragments, 1):
            conf_class = "high" if fragment.confidence_score >= 0.7 else "medium" if fragment.confidence_score >= 0.4 else "low"

            source_file = "nieznany"
            meeting_info = fragment.meeting_info

            if "| Plik:" in fragment.meeting_info:
                meeting_part, file_part = fragment.meeting_info.split("| Plik:", 1)
                source_file = file_part.strip()
                meeting_info = meeting_part.strip()

            source_file_tag = f'<span class="source-file">{source_file}</span>' if show_source_file else ""

            # Wyświetlanie mówcy
            speaker_info = fragment.speaker  # To zwraca słownik {"name": str, "club": str|None}
            if speaker_info.get('club'):
                speaker_display = f"{speaker_info['name']} ({speaker_info['club']})"
            else:
                speaker_display = f"{speaker_info['name']} (brak klubu)"

            html += f"""
            <div class="fragment confidence-{conf_class}" id="fragment-{i}">
                <div class="speaker">
                    🎤 {speaker_display}
                    <span class="confidence conf-{conf_class}">{fragment.confidence_score:.3f}</span>
                    {source_file_tag}
                </div>
                <div class="keywords">Słowa kluczowe: {fragment.get_keywords_as_string()}</div>
                <div class="text">{fragment.text}</div>
                <div class="meta">
                    Źródło: {source_file if not show_source_file else meeting_info}<br>
                    Pozycja: {fragment.position_in_text if fragment.position_in_text != -1 else 'nieznana'}<br>
                    {fragment.timestamp}
                </div>
            </div>
            """

        return html

    def _create_empty_report(self, message: str) -> str:
        """Tworzy pusty raport z komunikatem"""
        return f"""
        <!DOCTYPE html>
        <html lang="pl">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Raport - Brak Danych</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 50px; text-align: center; }}
                .message {{ background-color: #f8f9fa; padding: 40px; border-radius: 10px; }}
            </style>
        </head>
        <body>
            <div class="message">
                <h1>Raport</h1>
                <p>{message}</p>
            </div>
        </body>
        </html>
        """

    def _write_html_file(self, content: str, output_file: str) -> None:
        """Zapisuje content HTML do pliku"""
        # Upewniamy się że folder docelowy istnieje
        Path(output_file).parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(content)

        if self.debug:
            self.logger.debug(f"Pomyślnie zapisano plik HTML: {output_file}")
