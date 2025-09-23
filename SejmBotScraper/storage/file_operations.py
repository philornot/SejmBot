"""
Implementacja operacji na plikach i folderach
Bazuje na oryginalnym FileManager z dodatkową funkcjonalnością
"""

import json
import logging
import os
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List

logger = logging.getLogger(__name__)


class FileOperationsImpl:
    """Implementacja operacji na plikach i folderach dla SejmBotScraper"""

    def __init__(self, base_dir: Optional[str] = None):
        """
        Inicjalizuje operacje na plikach

        Args:
            base_dir: katalog bazowy (opcjonalny, domyślnie z konfiguracji)
        """
        if base_dir:
            self.base_dir = Path(base_dir)
        else:
            # Domyślnie używamy katalogu, z którego uruchomiono polecenie (CWD).
            # To upraszcza integrację z CI i uruchomieniami lokalnymi.
            try:
                from ..config.settings import get_settings
                settings = get_settings()
                cfg_dir = settings.get('scraping.base_output_dir', None)
                if cfg_dir:
                    self.base_dir = Path(cfg_dir)
                else:
                    self.base_dir = Path.cwd()
            except Exception:
                self.base_dir = Path.cwd()

        self.ensure_base_directory()
        logger.debug(f"Zainicjalizowano FileOperationsImpl: {self.base_dir}")

    def ensure_base_directory(self):
        """Tworzy główny katalog jeśli nie istnieje"""
        self.base_dir.mkdir(parents=True, exist_ok=True)
        logger.debug(f"Upewniono się o istnieniu katalogu: {self.base_dir}")

    def get_base_directory(self) -> Path:
        """Zwraca katalog bazowy"""
        return self.base_dir

    def get_term_directory(self, term: int) -> Path:
        """
        Zwraca ścieżkę do katalogu kadencji

        Args:
            term: numer kadencji

        Returns:
            Path do katalogu kadencji
        """
        term_dir = self.base_dir / f"kadencja_{term:02d}"
        term_dir.mkdir(parents=True, exist_ok=True)
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
        proceeding_dir.mkdir(parents=True, exist_ok=True)

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
        transcripts_dir.mkdir(parents=True, exist_ok=True)
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

            # Jeśli mamy wzbogacone pełne wypowiedzi, znormalizujmy je do prostego formatu
            statements_to_save = []
            if full_statements:
                for stmt in full_statements:
                    try:
                        # Przyjmujemy, że stmt to dict z możliwymi polami:
                        # 'num', 'speaker' (dict), 'content' lub bezpośrednie 'text'/'html'
                        num = stmt.get('num') if isinstance(stmt, dict) else None

                        # Wyciągnij informacje o mówcy
                        speaker = {}
                        raw_speaker = stmt.get('speaker') if isinstance(stmt, dict) else None
                        if isinstance(raw_speaker, dict):
                            speaker = {
                                'name': raw_speaker.get('name'),
                                'id': raw_speaker.get('id'),
                                'is_mp': raw_speaker.get('is_mp') if 'is_mp' in raw_speaker else None,
                                'club': raw_speaker.get('club') or raw_speaker.get('group')
                            }

                        # Pobierz możliwy tekst (upraszczamy html->tekst jeśli trzeba)
                        text = None
                        content = stmt.get('content') if isinstance(stmt, dict) else {}
                        if isinstance(content, dict):
                            # popularne pola
                            text = content.get('text') or content.get('text_content') or content.get('plain')
                            if not text and content.get('html_content'):
                                text = self._html_to_text(str(content.get('html_content')))
                        else:
                            # bezpośrednie pola
                            text = stmt.get('text') or stmt.get('text_content') or stmt.get('html_content')
                            if text and ('<' in str(text) and '>' in str(text)):
                                text = self._html_to_text(str(text))

                        if text:
                            text = str(text).strip()

                        # Metadane czasu i trwania
                        start = stmt.get('start_time') if isinstance(stmt, dict) else None
                        end = stmt.get('end_time') if isinstance(stmt, dict) else None
                        duration = None
                        if start and end:
                            duration = self._calculate_duration(start, end)

                        # Pomijamy krótkie/nieistotne treści
                        if not text or len(text) < 10:
                            continue

                        canonical = {
                            'num': num,
                            'speaker': speaker,
                            'text': text,
                            'start_time': start,
                            'end_time': end,
                            'duration_seconds': duration,
                            # zachowajemy oryginalną strukturę na wszelki wypadek
                            'original': stmt
                        }

                        statements_to_save.append(canonical)
                    except Exception as e:
                        logger.debug(f"Pominięto wypowiedź przy normalizacji: {e}")

            # Jeśli nic do zapisania — log i zwróć None (nie zapisujemy pustych plików)
            if not statements_to_save:
                logger.info(f"Brak wypowiedzi z treścią dla {date} — nie zapisuję pliku {filename}")
                return None

            # Zbuduj strukturę finalną używając statements_to_save
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

            for stmt in statements_to_save:
                # Zapisujemy znormalizowaną strukturę (ułatwia analizę w detektorze)
                transcript_data['statements'].append({
                    'num': stmt.get('num'),
                    'speaker': stmt.get('speaker', {}),
                    'text': stmt.get('text'),
                    'start_time': stmt.get('start_time'),
                    'end_time': stmt.get('end_time'),
                    'duration_seconds': stmt.get('duration_seconds'),
                    'original': stmt.get('original')
                })

            # Sortuj i zapisz atomowo
            transcript_data['statements'].sort(key=lambda x: x.get('num', 0))

            # Zapis atomowy: najpierw do pliku tymczasowego
            fd, tmp_path = tempfile.mkstemp(prefix=filename, dir=str(transcripts_dir))
            try:
                with os.fdopen(fd, 'w', encoding='utf-8') as f:
                    json.dump(transcript_data, f, ensure_ascii=False, indent=2, default=str)
                # atomic replace
                os.replace(tmp_path, str(filepath))
            except Exception:
                # cleanup temp file
                try:
                    os.unlink(tmp_path)
                except Exception:
                    pass
                raise

            logger.info(
                f"Zapisano transkrypty (tylko z treścią) dla {date}: {len(transcript_data['statements'])} wypowiedzi -> {filepath}")
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

    def _html_to_text(self, html: str) -> str:
        """Proste czyszczenie HTML -> tekst zwykły.

        Nie używamy zewnętrznych zależności; proste zastąpienia i usunięcie tagów
        wystarczą do analizy treści w detektorze.
        """
        try:
            import re

            text = re.sub(r'<(script|style)[^>]*>.*?</\1>', ' ', html, flags=re.DOTALL | re.IGNORECASE)
            text = re.sub(r'<br\s*/?>', '\n', text, flags=re.IGNORECASE)
            text = re.sub(r'<[^>]+>', ' ', text)
            # podstawowe encje
            text = text.replace('&nbsp;', ' ').replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
            text = re.sub(r'\s+', ' ', text)
            return text.strip()
        except Exception:
            return html

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
                from .data_serializers import DataSerializersImpl
                serializer = DataSerializersImpl()

                for file in transcripts_dir.glob("transkrypty_*.json"):
                    transcript_data = serializer.load_json(file)
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
