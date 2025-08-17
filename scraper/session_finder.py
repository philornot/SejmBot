#!/usr/bin/env python3
"""
SejmBot - session_finder.py
Moduł do wyszukiwania i parsowania linków do posiedzeń Sejmu RP
"""

import hashlib
import logging
import re
import time
from datetime import datetime
from typing import List, Dict, Optional
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


class SessionFinder:
    """Główna klasa do znajdowania linków do sesji Sejmu"""

    def __init__(self, config, logger: logging.Logger):
        self.config = config
        self.logger = logger

        # Konfiguracja sesji HTTP
        self.session = requests.Session()
        self.session.headers.update(config.headers)
        self.session.headers['User-Agent'] = config.user_agent

    def find_all_sessions(self) -> List[Dict[str, str]]:
        """
        Znajduje wszystkie posiedzenia ze wszystkich aktywnych kadencji

        Returns:
            Lista słowników z danymi posiedzeń
        """
        sessions = []

        # Pobierz wszystkie URLe do sprawdzenia
        urls_to_check = self.config.get_stenogramy_urls()

        self.logger.info(f"🔍 Sprawdzam {len(urls_to_check)} stron stenogramów...")

        for stenogramy_url in urls_to_check:
            self.logger.info(f"📄 Analizuję: {stenogramy_url}")

            # Wyciągnij kadencję i rok z URL
            kadencja_match = re.search(r'Sejm(\d+)\.nsf', stenogramy_url)
            rok_match = re.search(r'rok=(\d{4})', stenogramy_url)

            kadencja_nr = int(kadencja_match.group(1)) if kadencja_match else 0
            rok = int(rok_match.group(1)) if rok_match else datetime.now().year

            # Pobierz stronę z retry
            time.sleep(self.config.delay_between_requests)
            response = self._make_request(stenogramy_url)

            if not response:
                self.logger.warning(f"❌ Nie udało się pobrać: {stenogramy_url}")
                continue

            try:
                soup = BeautifulSoup(response.text, 'html.parser')

                # Debuguj zawartość strony
                self._debug_page_content(soup, stenogramy_url)

                # Wyciągnij sesje z tej strony
                page_sessions = self._extract_sessions_from_page(soup, stenogramy_url, kadencja_nr, rok)

                sessions.extend(page_sessions)
                self.logger.info(
                    f"✅ Znaleziono {len(page_sessions)} sesji na stronie (kadencja {kadencja_nr}, rok {rok})")

            except Exception as e:
                self.logger.error(f"❌ Błąd parsowania strony {stenogramy_url}: {e}")
                import traceback
                self.logger.debug(f"Szczegóły błędu: {traceback.format_exc()}")
                continue

        # Usuń duplikaty i posortuj
        unique_sessions = self._deduplicate_sessions(sessions)
        sorted_sessions = self._sort_sessions(unique_sessions)

        # Debuguj znalezione sesje
        self._debug_found_sessions(sorted_sessions)

        self.logger.info(f"🎯 Znaleziono łącznie {len(sorted_sessions)} unikalnych sesji")
        return sorted_sessions

    def _extract_sessions_from_page(self, soup: BeautifulSoup, base_url: str, kadencja_nr: int, rok: int) -> List[
        Dict[str, str]]:
        """
        Wyciąga posiedzenia z pojedynczej strony stenogramów
        """
        posiedzenia = []

        # Szukaj linków PDF z klasą 'pdf' - główny selektor dla stenogramów
        pdf_links = soup.select('a.pdf[href]')

        self.logger.debug(f"Znaleziono {len(pdf_links)} linków PDF z klasą 'pdf'")

        for link in pdf_links:
            try:
                href = link.get('href', '')
                text = link.get_text(strip=True)
                title = link.get('title', '')

                if not href or not text:
                    continue

                # Sprawdź czy link zawiera datę (oznacza stenogram)
                if not self._text_contains_date(text):
                    self.logger.debug(f"Pomijam link bez daty: {text[:50]}")
                    continue

                # Sprawdź czy to stenogram (nie fotogaleria, zapowiedź itp.)
                if self._should_skip_link(text.lower()):
                    self.logger.debug(f"Pomijam link (skip pattern): {text[:50]}")
                    continue

                # Sprawdź tytuł linku - powinien zawierać "stenograficzne"
                if title and 'stenograficzne' not in title.lower():
                    self.logger.debug(f"Pomijam - brak 'stenograficzne' w title: {title[:50]}")
                    continue

                # Parsuj dane posiedzenia z linku
                posiedzenie_data = self._parse_session_link(link, base_url, kadencja_nr, rok)
                if posiedzenie_data:
                    posiedzenia.append(posiedzenie_data)
                    self.logger.debug(f"✅ Dodano posiedzenie: {posiedzenie_data['title'][:60]}")

            except Exception as e:
                self.logger.warning(f"Błąd parsowania linku PDF: {e}")
                continue

        self.logger.info(f"🎯 Wyciągnięto {len(posiedzenia)} posiedzeń z {len(pdf_links)} linków PDF")
        return posiedzenia

    def _parse_session_link(self, link, base_url: str, kadencja_nr: int, rok: int) -> Optional[Dict[str, str]]:
        """Parsuje pojedynczy link do posiedzenia Sejmu"""
        href = link.get('href', '')
        text = link.get_text(strip=True)
        title = link.get('title', '')

        if not href or not text:
            return None

        # Utwórz pełny URL
        if href.startswith('http'):
            full_url = href
        else:
            full_url = urljoin(base_url, href)

        # Wyciągnij numer posiedzenia
        meeting_number = self._extract_meeting_number(href, text)

        # Wyciągnij literę dnia
        day_letter = self._extract_day_letter(text)

        # Parsuj datę z tekstu linku
        meeting_date = self._extract_date_from_text(text)
        if not meeting_date:
            meeting_date = f"{rok}-01-01"  # Fallback

        # Stwórz unikalny ID
        url_hash = hashlib.md5(full_url.encode()).hexdigest()[:8]
        session_id = f"{kadencja_nr}_{meeting_date.replace('-', '')}_{url_hash}"

        # Przygotuj tytuł posiedzenia
        if meeting_number > 0:
            if day_letter:
                session_title = f"Posiedzenie nr {meeting_number} ({day_letter}) - {text}"
            else:
                session_title = f"Posiedzenie nr {meeting_number} - {text}"
        else:
            session_title = f"Sesja {meeting_date} - {text}"

        return {
            'id': session_id,
            'meeting_number': meeting_number,
            'day_letter': day_letter,
            'title': session_title,
            'url': full_url,
            'date': meeting_date,
            'kadencja': kadencja_nr,
            'rok': rok,
            'original_text': text,
            'pdf_direct': True
        }

    def _text_contains_date(self, text: str) -> bool:
        """Sprawdza czy tekst zawiera polską datę"""
        # Wzorzec polskich dat z dniami tygodnia
        date_pattern = r'\d{1,2}\s+(stycznia|lutego|marca|kwietnia|maja|czerwca|lipca|sierpnia|września|października|listopada|grudnia)\s+\d{4}\s*\([^)]+\)'
        return bool(re.search(date_pattern, text.lower()))

    def _should_skip_link(self, text_lower: str) -> bool:
        """Sprawdza czy link należy pominąć"""
        for pattern in self.config.skip_patterns:
            if pattern.lower() in text_lower:
                return True
        return False

    def _extract_meeting_number(self, url: str, text: str) -> int:
        """Wyciąga numer posiedzenia z URL lub tekstu"""
        # METODA 1: Spróbuj wyciągnąć z tekstu linku
        text_patterns = [
            r'posiedzenie\s+nr\s*(\d+)',
            r'posiedzenie\s+(\d+)',
            r'sesja\s+(\d+)',
            r'nr\s*(\d+)',
            r'(\d+)\s*posiedzenie'
        ]

        text_lower = text.lower()
        for pattern in text_patterns:
            match = re.search(pattern, text_lower)
            if match:
                try:
                    number = int(match.group(1))
                    self.logger.debug(f"Numer posiedzenia z tekstu: {number}")
                    return number
                except (ValueError, IndexError):
                    continue

        # METODA 2: Analiza struktury URL
        url_patterns = [
            r'/(\d+)_[a-z]_[^/]*\.pdf$',
            r'/(\d+)_[^/]*\.pdf$',
            r'_(\d+)_[^/]*\.pdf$',
            r'/(\d+)[^/]*\.pdf$',
        ]

        for pattern in url_patterns:
            match = re.search(pattern, url.lower())
            if match:
                try:
                    number = int(match.group(1))
                    if 1 <= number <= 200:  # Sprawdź czy to sensowny numer
                        self.logger.debug(f"Numer posiedzenia z URL: {number}")
                        return number
                except (ValueError, IndexError):
                    continue

        # METODA 3: Heurystyka na podstawie daty
        date_str = self._extract_date_from_text(text)
        if date_str:
            try:
                date_obj = datetime.strptime(date_str, '%Y-%m-%d')
                # Przybliżona heurystyka - w roku jest ok. 30-50 posiedzeń
                estimated = min((date_obj.month - 1) * 3 + 1, 50)
                self.logger.debug(f"Szacowany numer z daty: {estimated}")
                return estimated
            except ValueError:
                pass

        # FALLBACK: Zwróć 1
        self.logger.debug(f"Nie udało się wyciągnąć numeru, używam fallback: 1")
        return 1

    def _extract_day_letter(self, text: str) -> str:
        """Wyciąga literę dnia z tekstu"""
        # Szukaj bezpośrednio litery w nawiasie lub po przecinku
        letter_patterns = [
            r'\(([a-h])\)',  # (a), (b), itp.
            r',\s*([a-h])\s*$',  # kończy się ", a"
            r'\s([a-h])\s*$',  # kończy się " a"
        ]

        for pattern in letter_patterns:
            match = re.search(pattern, text.lower())
            if match:
                return match.group(1)

        # Mapowanie dni tygodnia na litery
        day_mapping = {
            'poniedziałek': 'a', 'wtorek': 'b', 'środa': 'c', 'czwartek': 'd',
            'piątek': 'e', 'sobota': 'f', 'niedziela': 'g'
        }

        text_lower = text.lower()
        for day_name, letter in day_mapping.items():
            if day_name in text_lower:
                return letter

        return ""  # Brak litery

    def _extract_date_from_text(self, text: str) -> Optional[str]:
        """Wyciąga datę z tekstu"""
        # Wzorce polskich dat
        date_patterns = [
            r'(\d{1,2})\s+(stycznia|lutego|marca|kwietnia|maja|czerwca|lipca|sierpnia|września|października|listopada|grudnia)\s+(\d{4})\s*\([^)]+\)',
            r'(\d{1,2})\s+(stycznia|lutego|marca|kwietnia|maja|czerwca|lipca|sierpnia|września|października|listopada|grudnia)\s+(\d{4})',
            r'(\d{1,2})\.(\d{1,2})\.(\d{4})',
            r'(\d{4})-(\d{1,2})-(\d{1,2})'
        ]

        text_lower = text.lower()

        for pattern in date_patterns:
            match = re.search(pattern, text_lower)
            if match:
                try:
                    groups = match.groups()

                    if len(groups) >= 3:
                        if any(month in pattern for month in self.config.polish_months.keys()):
                            # Format polski: "22 lipca 2025"
                            day = groups[0].zfill(2)
                            month_name = groups[1]
                            year = groups[2]

                            month_num = self.config.polish_months.get(month_name, '01')
                            return f"{year}-{month_num}-{day}"

                        elif '.' in pattern:
                            # Format DD.MM.YYYY
                            day, month, year = groups
                            return f"{year}-{month.zfill(2)}-{day.zfill(2)}"

                        elif '-' in pattern:
                            # Format YYYY-MM-DD
                            year, month, day = groups
                            return f"{year}-{month.zfill(2)}-{day.zfill(2)}"

                except (ValueError, IndexError, AttributeError) as e:
                    self.logger.debug(f"Błąd parsowania daty z '{text}': {e}")
                    continue

        return None

    def _make_request(self, url: str) -> Optional[requests.Response]:
        """Wykonuje zapytanie HTTP z retry"""
        for attempt in range(self.config.max_retries):
            try:
                response = self.session.get(url, timeout=self.config.timeout)
                if response.status_code == 200:
                    return response
                else:
                    self.logger.warning(f"HTTP {response.status_code} dla {url}")

            except requests.exceptions.Timeout:
                self.logger.warning(f"Timeout (próba {attempt + 1}/{self.config.max_retries}) dla {url}")
                if attempt < self.config.max_retries - 1:
                    time.sleep(2 ** attempt)

            except requests.RequestException as e:
                self.logger.warning(f"Błąd zapytania (próba {attempt + 1}): {e}")
                if attempt < self.config.max_retries - 1:
                    time.sleep(2 ** attempt)

        return None

    def _deduplicate_sessions(self, sessions: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """Usuwa duplikaty sesji na podstawie URL"""
        unique_sessions = {}
        for session in sessions:
            url = session['url']
            if url not in unique_sessions:
                unique_sessions[url] = session
            else:
                # Zachowaj sesję z więcej danych
                existing = unique_sessions[url]
                if len(session.get('title', '')) > len(existing.get('title', '')):
                    unique_sessions[url] = session

        return list(unique_sessions.values())

    def _sort_sessions(self, sessions: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """Sortuje sesje według kadencji, daty i numeru posiedzenia"""
        return sorted(sessions,
                     key=lambda x: (
                         x.get('kadencja', 0),
                         x.get('date', ''),
                         x.get('meeting_number', 0)
                     ),
                     reverse=True)

    def _debug_page_content(self, soup: BeautifulSoup, url: str):
        """Debuguje zawartość strony"""
        all_pdf_links = soup.select('a[href*=".pdf"]')
        pdf_class_links = soup.select('a.pdf')

        self.logger.debug(f"🔍 ANALIZA STRONY: {url}")
        self.logger.debug(f"   📎 Wszystkie linki PDF: {len(all_pdf_links)}")
        self.logger.debug(f"   🎯 Linki z klasą 'pdf': {len(pdf_class_links)}")

        # Pokaż przykłady
        for i, link in enumerate(pdf_class_links[:3]):
            href = link.get('href', '')
            text = link.get_text(strip=True)
            self.logger.debug(f"   📄 PDF {i + 1}: href='{href[:60]}...', text='{text[:40]}...'")

    def _debug_found_sessions(self, sessions: List[Dict[str, str]]):
        """Debuguje znalezione sesje"""
        if not sessions:
            self.logger.warning("🔍 BRAK znalezionych sesji!")
            return

        # Grupuj według kadencji
        by_kadencja = {}
        for session in sessions:
            kadencja = session.get('kadencja', 0)
            if kadencja not in by_kadencja:
                by_kadencja[kadencja] = []
            by_kadencja[kadencja].append(session)

        self.logger.info(f"🔍 ZNALEZIONE SESJE ({len(sessions)}):")
        for kadencja, kad_sessions in by_kadencja.items():
            self.logger.info(f"   📊 Kadencja {kadencja}: {len(kad_sessions)} sesji")

            # Pokaż przykłady
            for session in kad_sessions[:2]:
                title = session.get('title', '')[:50]
                date = session.get('date', 'brak daty')
                self.logger.info(f"      • {date}: {title}...")