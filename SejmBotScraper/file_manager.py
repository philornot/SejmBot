# file_manager.py
"""
Zarządzanie plikami i folderami dla SejmBotScraper
"""

import logging
from pathlib import Path
from typing import Optional, Dict

from config import BASE_OUTPUT_DIR

logger = logging.getLogger(__name__)


class FileManager:
    """Zarządzanie strukturą plików i zapisem"""

    def __init__(self):
        self.base_dir = Path(BASE_OUTPUT_DIR)
        self.ensure_base_directory()

    def ensure_base_directory(self):
        """Tworzy główny katalog jeśli nie istnieje"""
        self.base_dir.mkdir(exist_ok=True)
        logger.debug(f"Upewniono się o istnieniu katalogu: {self.base_dir}")

    def get_term_directory(self, term: int) -> Path:
        """
        Zwraca ścieżkę do katalogu kadencji

        Args:
            term: numer kadencji

        Returns:
            Path do katalogu kadencji
        """
        term_dir = self.base_dir / f"kadencja_{term:02d}"
        term_dir.mkdir(exist_ok=True)
        return term_dir

    def get_proceeding_directory(self, term: int, proceeding_id: int, proceeding_info: Dict) -> Path:
        """
        Zwraca ścieżkę do katalogu posiedzenia

        Args:
            term: numer kadencji
            proceeding_id: ID posiedzenia
            proceeding_info: informacje o posiedzeniu z API

        Returns:
            Path do katalogu posiedzenia
        """
        term_dir = self.get_term_directory(term)

        # Tworzymy nazwę katalogu z numerem posiedzenia
        proceeding_name = f"posiedzenie_{proceeding_id:03d}"

        # Dodajemy daty jeśli są dostępne
        if 'dates' in proceeding_info and proceeding_info['dates']:
            first_date = proceeding_info['dates'][0]
            proceeding_name += f"_{first_date}"

        proceeding_dir = term_dir / proceeding_name
        proceeding_dir.mkdir(exist_ok=True)

        logger.debug(f"Utworzono katalog posiedzenia: {proceeding_dir}")
        return proceeding_dir

    def save_pdf_transcript(self, term: int, proceeding_id: int, date: str,
                            pdf_content: bytes, proceeding_info: Dict) -> Optional[str]:
        """
        Zapisuje transkrypt PDF

        Args:
            term: numer kadencji
            proceeding_id: ID posiedzenia
            date: data
            pdf_content: zawartość PDF
            proceeding_info: informacje o posiedzeniu

        Returns:
            Ścieżka do zapisanego pliku lub None w przypadku błędu
        """
        try:
            proceeding_dir = self.get_proceeding_directory(term, proceeding_id, proceeding_info)
            filename = f"transkrypt_{date}.pdf"
            filepath = proceeding_dir / filename

            with open(filepath, 'wb') as f:
                f.write(pdf_content)

            logger.info(f"Zapisano transkrypt PDF: {filepath}")
            return str(filepath)

        except Exception as e:
            logger.error(f"Błąd zapisywania PDF dla {date}: {e}")
            return None

    def save_html_statements(self, term: int, proceeding_id: int, date: str,
                             statements: Dict, proceeding_info: Dict) -> Optional[str]:
        """
        Zapisuje wypowiedzi HTML

        Args:
            term: numer kadencji
            proceeding_id: ID posiedzenia
            date: data
            statements: lista wypowiedzi
            proceeding_info: informacje o posiedzeniu

        Returns:
            Ścieżka do katalogu z wypowiedziami lub None w przypadku błędu
        """
        try:
            proceeding_dir = self.get_proceeding_directory(term, proceeding_id, proceeding_info)

            # Tworzymy podkatalog dla tego dnia
            day_dir = proceeding_dir / f"wypowiedzi_{date}"
            day_dir.mkdir(exist_ok=True)

            if 'statements' not in statements:
                logger.warning(f"Brak wypowiedzi dla {date}")
                return str(day_dir)

            # Zapisujemy każdą wypowiedź jako osobny plik
            for statement in statements['statements']:
                statement_num = statement.get('num', 0)
                speaker_name = statement.get('name', 'nieznany')

                # Czyścimy nazwę dla nazwy pliku
                safe_name = self._make_safe_filename(speaker_name)
                filename = f"{statement_num:03d}_{safe_name}.html"

                # Dodajemy metadane na początku pliku
                html_content = self._create_statement_html(statement, term, proceeding_id, date)

                filepath = day_dir / filename
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(html_content)

            logger.info(f"Zapisano {len(statements['statements'])} wypowiedzi do: {day_dir}")
            return str(day_dir)

        except Exception as e:
            logger.error(f"Błąd zapisywania wypowiedzi HTML dla {date}: {e}")
            return None

    def _make_safe_filename(self, name: str) -> str:
        """
        Czyści nazwę dla bezpiecznej nazwy pliku

        Args:
            name: oryginalna nazwa

        Returns:
            Bezpieczna nazwa pliku
        """
        # Usuwa niebezpieczne znaki
        safe_chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-"
        safe_name = ''.join(c if c in safe_chars else '_' for c in name)

        # Skraca jeśli za długie
        if len(safe_name) > 50:
            safe_name = safe_name[:50]

        return safe_name

    def _create_statement_html(self, statement: Dict, term: int, proceeding_id: int, date: str) -> str:
        """
        Tworzy HTML dla wypowiedzi z metadanymi

        Args:
            statement: informacje o wypowiedzi
            term: kadencja
            proceeding_id: ID posiedzenia
            date: data

        Returns:
            HTML jako string
        """
        html_template = """<!DOCTYPE html>
<html lang="pl">
<head>
    <meta charset="UTF-8">
    <title>Wypowiedź - {name}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .metadata {{ background: #f5f5f5; padding: 10px; margin-bottom: 20px; border: 1px solid #ddd; }}
        .content {{ line-height: 1.6; }}
    </style>
</head>
<body>
    <div class="metadata">
        <h2>Metadane wypowiedzi</h2>
        <p><strong>Mówca:</strong> {name}</p>
        <p><strong>Funkcja:</strong> {function}</p>
        <p><strong>Numer wypowiedzi:</strong> {num}</p>
        <p><strong>Data:</strong> {date}</p>
        <p><strong>Czas rozpoczęcia:</strong> {start_time}</p>
        <p><strong>Czas zakończenia:</strong> {end_time}</p>
        <p><strong>Kadencja:</strong> {term}</p>
        <p><strong>Posiedzenie:</strong> {proceeding_id}</p>
    </div>
    <div class="content">
        <h3>Treść wypowiedzi</h3>
        <p><em>Uwaga: Pełna treść wypowiedzi zostanie pobrana w osobnym zapytaniu do API.</em></p>
        <p>Aby pobrać pełną treść, użyj endpointu: /sejm/term{term}/proceedings/{proceeding_id}/{date}/transcripts/{num}</p>
    </div>
</body>
</html>"""

        return html_template.format(
            name=statement.get('name', 'Nieznany'),
            function=statement.get('function', ''),
            num=statement.get('num', 0),
            date=date,
            start_time=statement.get('startDateTime', ''),
            end_time=statement.get('endDateTime', ''),
            term=term,
            proceeding_id=proceeding_id
        )

    def save_proceeding_info(self, term: int, proceeding_id: int, proceeding_info: Dict) -> Optional[str]:
        """
        Zapisuje informacje o posiedzeniu do pliku JSON

        Args:
            term: numer kadencji
            proceeding_id: ID posiedzenia
            proceeding_info: informacje o posiedzeniu

        Returns:
            Ścieżka do zapisanego pliku lub None w przypadku błędu
        """
        try:
            import json

            proceeding_dir = self.get_proceeding_directory(term, proceeding_id, proceeding_info)
            filepath = proceeding_dir / "info_posiedzenia.json"

            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(proceeding_info, f, ensure_ascii=False, indent=2)

            logger.debug(f"Zapisano informacje o posiedzeniu: {filepath}")
            return str(filepath)

        except Exception as e:
            logger.error(f"Błąd zapisywania informacji o posiedzeniu {proceeding_id}: {e}")
            return None
