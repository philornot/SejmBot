# file_manager.py
"""
Zarządzanie plikami i folderami dla SejmBotScraper
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List

from config import BASE_OUTPUT_DIR

logger = logging.getLogger(__name__)


class FileManager:
    """Zarządzanie strukturą plików i zapisem strukturyzowanych danych wypowiedzi"""

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

    def get_transcripts_directory(self, term: int, proceeding_id: int, proceeding_info: Dict) -> Path:
        """
        Zwraca ścieżkę do katalogu transkryptów

        Args:
            term: numer kadencji
            proceeding_id: ID posiedzenia
            proceeding_info: informacje o posiedzeniu

        Returns:
            Path do katalogu transkryptów
        """
        proceeding_dir = self.get_proceeding_directory(term, proceeding_id, proceeding_info)
        transcripts_dir = proceeding_dir / "transcripts"
        transcripts_dir.mkdir(exist_ok=True)
        return transcripts_dir

    def save_proceeding_transcripts(self, term: int, proceeding_id: int, date: str,
                                    statements_data: Dict, proceeding_info: Dict,
                                    full_statements: Optional[List[Dict]] = None) -> Optional[str]:
        """
        Zapisuje wszystkie wypowiedzi z danego dnia jako strukturyzowany JSON

        Args:
            term: numer kadencji
            proceeding_id: ID posiedzenia
            date: data (format YYYY-MM-DD)
            statements_data: podstawowe dane wypowiedzi z API
            proceeding_info: informacje o posiedzeniu
            full_statements: pełne treści wypowiedzi (opcjonalne)

        Returns:
            Ścieżka do zapisanego pliku lub None w przypadku błędu
        """
        try:
            transcripts_dir = self.get_transcripts_directory(term, proceeding_id, proceeding_info)
            filename = f"transkrypty_{date}.json"
            filepath = transcripts_dir / filename

            # Tworzymy strukturę danych
            transcript_data = {
                "metadata": {
                    "term": term,
                    "proceeding_id": proceeding_id,
                    "date": date,
                    "generated_at": datetime.now().isoformat(),
                    "proceeding_info": {
                        "title": proceeding_info.get('title', ''),
                        "dates": proceeding_info.get('dates', []),
                        "num": proceeding_info.get('num', proceeding_id)
                    }
                },
                "statements": []
            }

            # Przetwarzamy wypowiedzi
            if 'statements' in statements_data:
                full_statements_dict = {}
                if full_statements:
                    # Tworzymy mapę pełnych wypowiedzi dla szybkiego dostępu
                    full_statements_dict = {stmt.get('num'): stmt for stmt in full_statements}

                for statement in statements_data['statements']:
                    statement_num = statement.get('num')

                    # Łączymy podstawowe dane z pełną treścią
                    full_statement = full_statements_dict.get(statement_num, {})

                    processed_statement = {
                        "num": statement_num,
                        "speaker": {
                            "name": statement.get('name', 'Nieznany'),
                            "function": statement.get('function', ''),
                            "club": statement.get('club', ''),
                            "first_name": statement.get('firstName', ''),
                            "last_name": statement.get('lastName', '')
                        },
                        "timing": {
                            "start_datetime": statement.get('startDateTime', ''),
                            "end_datetime": statement.get('endDateTime', ''),
                            "duration_seconds": self._calculate_duration(
                                statement.get('startDateTime'),
                                statement.get('endDateTime')
                            )
                        },
                        "content": {
                            "text": full_statement.get('text', ''),
                            "has_full_content": bool(full_statement.get('text')),
                            "content_source": "api" if full_statement.get('text') else "not_available"
                        },
                        "technical": {
                            "api_url": f"/sejm/term{term}/proceedings/{proceeding_id}/{date}/transcripts/{statement_num}",
                            "original_data": statement  # zachowujemy oryginalne dane dla referencji
                        }
                    }

                    transcript_data["statements"].append(processed_statement)

            # Sortujemy wypowiedzi według numeru
            transcript_data["statements"].sort(key=lambda x: x.get("num", 0))

            # Zapisujemy do pliku
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(transcript_data, f, ensure_ascii=False, indent=2, default=str)

            logger.info(
                f"Zapisano transkrypty dla {date}: {len(transcript_data['statements'])} wypowiedzi -> {filepath}")
            return str(filepath)

        except Exception as e:
            logger.error(f"Błąd zapisywania transkryptów dla {date}: {e}")
            return None

    def _calculate_duration(self, start_time: str, end_time: str) -> Optional[int]:
        """
        Oblicza czas trwania wypowiedzi w sekundach

        Args:
            start_time: czas rozpoczęcia (ISO format)
            end_time: czas zakończenia (ISO format)

        Returns:
            Czas trwania w sekundach lub None jeśli nie można obliczyć
        """
        try:
            if not start_time or not end_time:
                return None

            start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
            end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))

            duration = (end_dt - start_dt).total_seconds()
            return int(duration) if duration >= 0 else None

        except Exception as e:
            logger.debug(f"Nie można obliczyć czasu trwania: {e}")
            return None

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
            proceeding_dir = self.get_proceeding_directory(term, proceeding_id, proceeding_info)
            filepath = proceeding_dir / "info_posiedzenia.json"

            # Wzbogacamy informacje o metadane
            enhanced_info = {
                "metadata": {
                    "term": term,
                    "proceeding_id": proceeding_id,
                    "generated_at": datetime.now().isoformat()
                },
                "proceeding_data": proceeding_info
            }

            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(enhanced_info, f, ensure_ascii=False, indent=2, default=str)

            logger.debug(f"Zapisano informacje o posiedzeniu: {filepath}")
            return str(filepath)

        except Exception as e:
            logger.error(f"Błąd zapisywania informacji o posiedzeniu {proceeding_id}: {e}")
            return None

    def get_existing_transcripts(self, term: int, proceeding_id: int, proceeding_info: Dict) -> List[str]:
        """
        Zwraca listę dat, dla których już istnieją transkrypty

        Args:
            term: numer kadencji
            proceeding_id: ID posiedzenia
            proceeding_info: informacje o posiedzeniu

        Returns:
            Lista dat w formacie YYYY-MM-DD
        """
        try:
            transcripts_dir = self.get_transcripts_directory(term, proceeding_id, proceeding_info)

            if not transcripts_dir.exists():
                return []

            existing_dates = []
            for file in transcripts_dir.glob("transkrypty_*.json"):
                # Wyciągamy datę z nazwy pliku
                date_part = file.stem.replace("transkrypty_", "")
                if len(date_part) == 10 and date_part.count('-') == 2:  # format YYYY-MM-DD
                    existing_dates.append(date_part)

            return sorted(existing_dates)

        except Exception as e:
            logger.error(f"Błąd sprawdzania istniejących transkryptów: {e}")
            return []

    def load_transcript_file(self, filepath: str) -> Optional[Dict]:
        """
        Ładuje plik transkryptu

        Args:
            filepath: ścieżka do pliku

        Returns:
            Dane transkryptu lub None w przypadku błędu
        """
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Błąd wczytywania transkryptu {filepath}: {e}")
            return None

    def get_proceeding_summary(self, term: int, proceeding_id: int, proceeding_info: Dict) -> Dict:
        """
        Tworzy podsumowanie posiedzenia na podstawie zapisanych transkryptów

        Args:
            term: numer kadencji
            proceeding_id: ID posiedzenia
            proceeding_info: informacje o posiedzeniu

        Returns:
            Słownik z podsumowaniem
        """
        try:
            transcripts_dir = self.get_transcripts_directory(term, proceeding_id, proceeding_info)

            summary = {
                "term": term,
                "proceeding_id": proceeding_id,
                "total_days": 0,
                "total_statements": 0,
                "total_speakers": set(),
                "dates": [],
                "files": []
            }

            if transcripts_dir.exists():
                for file in transcripts_dir.glob("transkrypty_*.json"):
                    transcript_data = self.load_transcript_file(str(file))
                    if transcript_data:
                        summary["total_days"] += 1
                        summary["total_statements"] += len(transcript_data.get("statements", []))
                        summary["dates"].append(transcript_data["metadata"]["date"])
                        summary["files"].append(str(file))

                        # Zbieramy unikatowych mówców
                        for stmt in transcript_data.get("statements", []):
                            speaker_name = stmt.get("speaker", {}).get("name", "")
                            if speaker_name:
                                summary["total_speakers"].add(speaker_name)

            summary["total_speakers"] = len(summary["total_speakers"])
            summary["dates"].sort()

            return summary

        except Exception as e:
            logger.error(f"Błąd tworzenia podsumowania: {e}")
            return {"error": str(e)}
