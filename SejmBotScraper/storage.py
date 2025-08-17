#!/usr/bin/env python3
"""
SejmBot - storage.py (dokończenie)
Zarządzanie plikami i indeksami posiedzeń Sejmu RP
"""

import json
import logging
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Set

from models import SejmSession


class SessionStorage:
    """Zarządzanie zapisywaniem sesji w strukturze katalogów"""

    def __init__(self, config, logger: logging.Logger):
        self.config = config
        self.logger = logger
        self.base_dir = config.output_dir

    def save_session(self, session: SejmSession, pdf_bytes: bytes = None) -> bool:
        """
        Zapisuje posiedzenie w zorganizowanej strukturze katalogów

        Args:
            session: Obiekt sesji do zapisania
            pdf_bytes: Opcjonalne dane PDF

        Returns:
            bool: True jeśli zapisano pomyślnie
        """
        try:
            # Określ strukturę katalogów
            kadencja_nr = session.kadencja
            year = session.date[:4] if session.date and len(session.date) >= 4 else str(datetime.now().year)

            # Katalogi
            kadencja_dir = self.base_dir / f"kadencja_{kadencja_nr}"
            year_dir = kadencja_dir / year
            json_dir = year_dir / "json"
            pdf_dir = year_dir / "pdf"

            # Utwórz katalogi
            json_dir.mkdir(parents=True, exist_ok=True)
            pdf_dir.mkdir(parents=True, exist_ok=True)

            # Nazwa bazowa pliku
            base_filename = self._generate_filename(session)

            # 1. ZAPISZ JSON z metadanymi
            json_success = self._save_json(session, json_dir, base_filename, pdf_bytes)

            # 2. ZAPISZ PDF jeśli dostępny
            pdf_success = True
            if pdf_bytes and len(pdf_bytes) > 1000:
                pdf_success = self._save_pdf(pdf_bytes, pdf_dir, base_filename)

            # 3. AKTUALIZUJ INDEKS
            if json_success:
                self._update_session_index(kadencja_nr, year, session)

            return json_success and pdf_success

        except Exception as e:
            self.logger.error(f"❌ Błąd zapisu sesji {session.session_id}: {e}")
            return False

    def _generate_filename(self, session: SejmSession) -> str:
        """Generuje nazwę bazową pliku"""
        if session.day_letter:
            return f"posiedzenie_{session.meeting_number:03d}_{session.day_letter}_{session.session_id}"
        else:
            return f"posiedzenie_{session.meeting_number:03d}_{session.session_id}"

    def _save_json(self, session: SejmSession, json_dir: Path, base_filename: str, pdf_bytes: bytes) -> bool:
        """Zapisuje JSON z sesją"""
        try:
            json_filepath = json_dir / f"{base_filename}.json"

            # Przygotuj dane
            session_data = asdict(session)

            # Dodaj metadane
            session_data.update({
                'text_length': len(session.transcript_text) if session.transcript_text else 0,
                'word_count': len(session.transcript_text.split()) if session.transcript_text else 0,
                'file_paths': {
                    'json': str(json_filepath.relative_to(self.base_dir)),
                    'pdf': str((json_dir.parent / "pdf" / f"{base_filename}.pdf").relative_to(
                        self.base_dir)) if pdf_bytes else None
                },
                'processing_info': {
                    'bot_version': '2.0',
                    'processed_at': datetime.now().isoformat(),
                    'original_pdf_available': bool(pdf_bytes and len(pdf_bytes) > 1000),
                    'pdf_size_bytes': len(pdf_bytes) if pdf_bytes else 0
                }
            })

            # Walidacja tekstu
            if session.transcript_text:
                try:
                    session.transcript_text.encode('utf-8')
                except UnicodeEncodeError as e:
                    self.logger.error(f"❌ Problemy z kodowaniem tekstu {session.session_id}: {e}")
                    session_data['transcript_text'] = "[BŁĄD: Nieprawidłowe kodowanie tekstu]"
                    session_data['processing_info']['encoding_error'] = True

            # Zapisz JSON
            with open(json_filepath, 'w', encoding='utf-8') as f:
                json.dump(session_data, f, ensure_ascii=False, indent=2)

            self.logger.info(
                f"💾 JSON: {json_filepath.relative_to(self.base_dir)} ({session_data['text_length']:,} znaków)")
            return True

        except Exception as e:
            self.logger.error(f"❌ Błąd zapisu JSON {session.session_id}: {e}")
            return False

    def _save_pdf(self, pdf_bytes: bytes, pdf_dir: Path, base_filename: str) -> bool:
        """Zapisuje plik PDF"""
        try:
            pdf_filepath = pdf_dir / f"{base_filename}.pdf"

            with open(pdf_filepath, 'wb') as f:
                f.write(pdf_bytes)

            self.logger.info(f"📄 PDF: {pdf_filepath.relative_to(self.base_dir)} ({len(pdf_bytes):,} bajtów)")
            return True

        except Exception as e:
            self.logger.error(f"❌ Błąd zapisu PDF: {e}")
            return False

    def _update_session_index(self, kadencja_nr: int, year: str, session: SejmSession):
        """Aktualizuje indeks sesji dla kadencji i roku"""
        try:
            index_dir = self.base_dir / f"kadencja_{kadencja_nr}" / year
            index_file = index_dir / "index.json"

            # Wczytaj lub utwórz indeks
            if index_file.exists():
                with open(index_file, 'r', encoding='utf-8') as f:
                    index_data = json.load(f)
            else:
                index_data = {
                    'kadencja': kadencja_nr,
                    'year': year,
                    'sessions': {},
                    'stats': {
                        'total_sessions': 0,
                        'total_characters': 0,
                        'total_words': 0,
                        'last_updated': None
                    }
                }

            # Dodaj sesję do indeksu
            index_data['sessions'][session.session_id] = {
                'meeting_number': session.meeting_number,
                'day_letter': session.day_letter,
                'title': session.title[:100] if session.title else 'Bez tytułu',
                'date': session.date,
                'text_length': len(session.transcript_text) if session.transcript_text else 0,
                'word_count': len(session.transcript_text.split()) if session.transcript_text else 0,
                'file_type': session.file_type,
                'processed_at': datetime.now().isoformat(),
                'kadencja': kadencja_nr
            }

            # Uaktualnij statystyki
            index_data['stats']['total_sessions'] = len(index_data['sessions'])
            index_data['stats']['total_characters'] = sum(
                s.get('text_length', 0) for s in index_data['sessions'].values()
            )
            index_data['stats']['total_words'] = sum(
                s.get('word_count', 0) for s in index_data['sessions'].values()
            )
            index_data['stats']['last_updated'] = datetime.now().isoformat()

            # Zapisz indeks
            with open(index_file, 'w', encoding='utf-8') as f:
                json.dump(index_data, f, ensure_ascii=False, indent=2)

            self.logger.debug(f"📇 Uaktualniono indeks: {index_file.relative_to(self.base_dir)}")

        except Exception as e:
            self.logger.warning(f"⚠️  Błąd aktualizacji indeksu: {e}")

    def get_stored_sessions_count(self) -> int:
        """Zwraca liczbę już zapisanych sesji"""
        count = 0
        try:
            for kadencja_dir in self.base_dir.glob("kadencja_*"):
                for year_dir in kadencja_dir.glob("*"):
                    json_dir = year_dir / "json"
                    if json_dir.exists():
                        count += len(list(json_dir.glob("*.json")))
        except Exception as e:
            self.logger.warning(f"Błąd liczenia sesji: {e}")

        return count

    def cleanup_broken_sessions(self) -> int:
        """Czyści uszkodzone pliki JSON z poprzednich wersji"""
        broken_count = 0

        # Sprawdź zarówno starą jak i nową strukturę
        search_patterns = [
            "*.json",  # Stara struktura
            "*/*.json",  # Rok/plik.json
            "*/*/json/*.json"  # Nowa struktura
        ]

        for pattern in search_patterns:
            for json_file in self.base_dir.glob(pattern):
                if json_file.name in ["processed_sessions.json", "index.json"]:
                    continue

                try:
                    with open(json_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)

                    transcript = data.get('transcript_text', '')

                    # Sprawdź czy zawiera binarne dane PDF
                    if transcript and ('%PDF-' in transcript[:100] or '\u0000' in transcript[:1000]):
                        self.logger.info(f"🧹 Usuwam uszkodzony plik: {json_file.relative_to(self.base_dir)}")
                        json_file.unlink()
                        broken_count += 1

                except Exception as e:
                    self.logger.warning(f"⚠️  Nie można sprawdzić pliku {json_file}: {e}")

        return broken_count


class ProcessedSessionsTracker:
    """Śledzenie już przetworzonych sesji"""

    def __init__(self, config, logger: logging.Logger):
        self.config = config
        self.logger = logger
        self.processed_file = config.output_dir / "processed_sessions.json"
        self.processed_sessions: Set[str] = set()
        self._load_processed_sessions()

    def _load_processed_sessions(self):
        """Ładuje listę już przetworzonych sesji"""
        if self.processed_file.exists():
            try:
                with open(self.processed_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.processed_sessions = set(data.get('sessions', []))
                self.logger.info(f"Załadowano {len(self.processed_sessions)} już przetworzonych sesji")
            except Exception as e:
                self.logger.warning(f"Nie można załadować listy przetworzonych sesji: {e}")
                self.processed_sessions = set()

    def is_processed(self, session_id: str) -> bool:
        """Sprawdza czy sesja była już przetworzona"""
        return session_id in self.processed_sessions

    def mark_processed(self, session_id: str):
        """Oznacza sesję jako przetworzoną"""
        self.processed_sessions.add(session_id)
        self._save_processed_sessions()

    def _save_processed_sessions(self):
        """Zapisuje listę przetworzonych sesji"""
        try:
            # Utwórz katalog jeśli nie istnieje
            self.processed_file.parent.mkdir(parents=True, exist_ok=True)

            data = {
                'sessions': list(self.processed_sessions),
                'last_updated': datetime.now().isoformat(),
                'total_processed': len(self.processed_sessions)
            }

            with open(self.processed_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

        except Exception as e:
            self.logger.error(f"Błąd zapisu listy przetworzonych sesji: {e}")

    def remove_processed(self, session_id: str):
        """Usuwa sesję z listy przetworzonych (np. po cleanup)"""
        if session_id in self.processed_sessions:
            self.processed_sessions.remove(session_id)
            self._save_processed_sessions()


class IndexManager:
    """Zarządzanie indeksami posiedzeń"""

    def __init__(self, config, logger: logging.Logger):
        self.config = config
        self.logger = logger
        self.base_dir = config.output_dir

    def get_global_stats(self) -> dict:
        """Zwraca globalne statystyki wszystkich posiedzeń"""
        stats = {
            'total_sessions': 0,
            'total_characters': 0,
            'total_words': 0,
            'by_kadencja': {},
            'by_year': {},
            'last_updated': datetime.now().isoformat()
        }

        try:
            for kadencja_dir in self.base_dir.glob("kadencja_*"):
                kadencja_nr = kadencja_dir.name.replace('kadencja_', '')
                stats['by_kadencja'][kadencja_nr] = {
                    'sessions': 0,
                    'characters': 0,
                    'words': 0,
                    'years': []
                }

                for year_dir in kadencja_dir.glob("*"):
                    if not year_dir.is_dir() or not year_dir.name.isdigit():
                        continue

                    year = year_dir.name
                    index_file = year_dir / "index.json"

                    if index_file.exists():
                        try:
                            with open(index_file, 'r', encoding='utf-8') as f:
                                index_data = json.load(f)

                            year_stats = index_data.get('stats', {})
                            sessions_count = year_stats.get('total_sessions', 0)
                            chars_count = year_stats.get('total_characters', 0)
                            words_count = year_stats.get('total_words', 0)

                            # Globalne statystyki
                            stats['total_sessions'] += sessions_count
                            stats['total_characters'] += chars_count
                            stats['total_words'] += words_count

                            # Statystyki kadencji
                            stats['by_kadencja'][kadencja_nr]['sessions'] += sessions_count
                            stats['by_kadencja'][kadencja_nr]['characters'] += chars_count
                            stats['by_kadencja'][kadencja_nr]['words'] += words_count
                            stats['by_kadencja'][kadencja_nr]['years'].append(year)

                            # Statystyki roku
                            if year not in stats['by_year']:
                                stats['by_year'][year] = {
                                    'sessions': 0,
                                    'characters': 0,
                                    'words': 0
                                }

                            stats['by_year'][year]['sessions'] += sessions_count
                            stats['by_year'][year]['characters'] += chars_count
                            stats['by_year'][year]['words'] += words_count

                        except Exception as e:
                            self.logger.warning(f"Błąd czytania indeksu {index_file}: {e}")

        except Exception as e:
            self.logger.error(f"Błąd generowania globalnych statystyk: {e}")

        return stats

    def save_global_stats(self):
        """Zapisuje globalne statystyki do pliku"""
        try:
            stats = self.get_global_stats()
            stats_file = self.base_dir / "global_stats.json"

            with open(stats_file, 'w', encoding='utf-8') as f:
                json.dump(stats, f, ensure_ascii=False, indent=2)

            self.logger.info(f"📊 Zapisano globalne statystyki: {stats['total_sessions']} sesji")

        except Exception as e:
            self.logger.error(f"Błąd zapisu globalnych statystyk: {e}")
