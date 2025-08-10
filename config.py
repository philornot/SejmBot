#!/usr/bin/env python3
"""
SejmBot - Konfiguracja
Zawiera wszystkie ustawienia i stałe dla bota do parsowania transkryptów Sejmu RP.
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict


class SejmBotConfig:
    """Konfiguracja bota oparta na rzeczywistej strukturze Sejmu"""

    def __init__(self):
        # Podstawowe ustawienia
        self.user_agent = "SejmBot/2.1 (+https://github.com/philornot/SejmBot) Mozilla/5.0 (compatible)"
        self.output_dir = Path("transkrypty")
        self.logs_dir = Path("logs")

        # Ustawienia sieciowe
        self.delay_between_requests = 3  # Zwiększone dla problematycznych serwerów
        self.max_retries = 4  # Zwiększone
        self.timeout = 45  # Zwiększone

        # Struktura URLi oparta na rzeczywistej architekturze Sejmu
        self.kadencje = {
            10: {
                'base_url': 'https://www.sejm.gov.pl/Sejm10.nsf/',
                'stenogramy_url': 'https://www.sejm.gov.pl/Sejm10.nsf/stenogramy.xsp',
                'pdf_server': 'https://orka2.sejm.gov.pl/StenoInter10.nsf/',
                'lata': list(range(2023, 2026))  # 13.11.2023 - nadal trwa
            },
            9: {
                'base_url': 'https://www.sejm.gov.pl/Sejm9.nsf/',
                'stenogramy_url': 'https://www.sejm.gov.pl/Sejm9.nsf/stenogramy.xsp',
                'pdf_server': 'https://orka2.sejm.gov.pl/StenoInter9.nsf/',
                'lata': list(range(2019, 2024))  # 12.11.2019 – 12.11.2023
            },
            8: {
                'base_url': 'https://www.sejm.gov.pl/Sejm8.nsf/',
                'stenogramy_url': 'https://www.sejm.gov.pl/Sejm8.nsf/stenogramy.xsp',
                'pdf_server': 'https://orka2.sejm.gov.pl/StenoInter8.nsf/',
                'lata': list(range(2015, 2020))  # 12.11.2015 – 11.11.2019
            },
            7: {
                'base_url': 'https://www.sejm.gov.pl/Sejm7.nsf/',
                'stenogramy_url': 'https://www.sejm.gov.pl/Sejm7.nsf/stenogramy.xsp',
                'pdf_server': 'https://orka2.sejm.gov.pl/StenoInter7.nsf/',
                'lata': list(range(2011, 2016))  # 08.11.2011 – 11.11.2015
            },
            6: {
                'base_url': 'https://www.sejm.gov.pl/Sejm6.nsf/',
                'stenogramy_url': 'https://www.sejm.gov.pl/Sejm6.nsf/stenogramy.xsp',
                'pdf_server': 'https://orka2.sejm.gov.pl/StenoInter6.nsf/',
                'lata': list(range(2007, 2012))  # 05.11.2007 – 07.11.2011
            }
        }

        # Skupiamy się na najnowszych kadencjach
        self.active_kadencje = [10, 9]
        self.current_year = datetime.now().year

        # Selektory CSS - rozszerzone o alternatywne
        self.pdf_selectors = [
            'a.pdf[href*="ksiazka.pdf"]',  # Główny selektor
            'a[href*="ksiazka.pdf"]',  # Bez klasy
            'a.pdf',  # Tylko klasa pdf
            'a[href*="StenoInter"]',  # Serwer stenogramów
            'a[href*=".pdf"][title*="stenograficzne"]'  # PDF z "stenograficzne" w title
        ]

        # Wzorce dat - rozszerzone
        self.date_patterns = [
            r'(\d{1,2})\s+(stycznia|lutego|marca|kwietnia|maja|czerwca|lipca|sierpnia|września|października|listopada|grudnia)\s+(\d{4})\s*\([^)]+\)',
            r'(\d{1,2})\s+(stycznia|lutego|marca|kwietnia|maja|czerwca|lipca|sierpnia|września|października|listopada|grudnia)\s+(\d{4})',
            r'(\d{1,2})\.(\d{1,2})\.(\d{4})',
            r'(\d{4})-(\d{1,2})-(\d{1,2})'
        ]

        # Polskie miesiące do konwersji
        self.polish_months = {
            'stycznia': '01', 'lutego': '02', 'marca': '03', 'kwietnia': '04',
            'maja': '05', 'czerwca': '06', 'lipca': '07', 'sierpnia': '08',
            'września': '09', 'października': '10', 'listopada': '11', 'grudnia': '12'
        }

        # Nagłówki HTTP - rozszerzone
        self.headers = {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'pl-PL,pl;q=0.9,en-US;q=0.7,en;q=0.3',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache'
        }

        # Wzorce do pomijania
        self.skip_patterns = [
            'fotogaleria', '[fotogaleria]', 'zapowiedź', '(zapowiedź)',
            'spotkanie marszałka', 'galeria zdjęć', 'zdjęcia z',
            'fotorelacja', 'relacja fotograficzna', 'video', 'film'
        ]

        # Słowa kluczowe do walidacji stenogramów
        self.polish_keywords = [
            'posiedzenie', 'marszałek', 'poseł', 'posłanka', 'sejm', 'głosowanie',
            'komisja', 'sprawozdanie', 'ustawa', 'interpelacja', 'punkt', 'porządku',
            'obrady', 'wicemarszałek', 'przewodniczący', 'sekretarz', 'protokół',
            'rada ministrów', 'rząd', 'minister', 'klub', 'koło', 'poselski'
        ]

        # Wzorce czyszczenia tekstu
        self.cleanup_patterns = [
            r'JavaScript.*?włącz',
            r'Cookie.*?polityka',
            r'Mapa strony',
            r'Menu główne',
            r'Nawigacja',
            r'Przejdź do',
            r'Skip to',
            r'Strona \d+ z \d+',  # Numery stron
            r'www\.sejm\.gov\.pl',
            r'© Kancelaria Sejmu',
        ]

        # Progi walidacji
        self.validation_thresholds = {
            'min_text_length': 500,
            'min_keywords': 5,
            'min_printable_ratio': 0.9,
            'min_meaningful_ratio': 0.7,
            'min_pdf_size': 1000  # bajty
        }

        # Mapowanie dni tygodnia na litery
        self.day_mapping = {
            'poniedziałek': 'a',
            'wtorek': 'b',
            'środa': 'c',
            'czwartek': 'd',
            'piątek': 'e',
            'sobota': 'f',
            'niedziela': 'g'
        }

        # Wzorce błędów na stronach
        self.error_indicators = [
            'The requested URL was rejected',
            'Access Denied',
            'Error',
            'Błąd',
            'Brak dostępu'
        ]

        # Inicjalizacja
        self._setup_directories()
        self._setup_logging()

    def get_stenogramy_urls(self) -> List[str]:
        """Zwraca listę URLi do sprawdzenia - od najnowszych kadencji i lat"""
        urls = []

        # Sortuj kadencje od najnowszych (10, 9, 8...)
        for kadencja_nr in sorted(self.active_kadencje, reverse=True):
            kadencja = self.kadencje.get(kadencja_nr)
            if not kadencja:
                continue

            # Dla każdej kadencji, sprawdź tylko lata z tej kadencji, od najnowszych
            lata_kadencji = sorted(kadencja['lata'], reverse=True)

            for rok in lata_kadencji:
                url = f"{kadencja['stenogramy_url']}?rok={rok}"
                urls.append(url)

        return urls

    def _setup_directories(self):
        """Tworzy strukturę katalogów tylko dla rzeczywistych lat każdej kadencji"""
        self.output_dir.mkdir(exist_ok=True)
        self.logs_dir.mkdir(exist_ok=True)

        # Struktura: transkrypty/kadencja_X/YYYY/ - tylko dla rzeczywistych lat
        for kadencja_nr in self.active_kadencje:
            kadencja_info = self.kadencje.get(kadencja_nr)
            if not kadencja_info:
                continue

            kadencja_dir = self.output_dir / f"kadencja_{kadencja_nr}"
            kadencja_dir.mkdir(exist_ok=True)

            # Katalogi tylko dla lat tej konkretnej kadencji
            for rok in kadencja_info['lata']:
                year_dir = kadencja_dir / str(rok)
                year_dir.mkdir(exist_ok=True)

                # Podkatalogi dla JSON i PDF
                (year_dir / "json").mkdir(exist_ok=True)
                (year_dir / "pdf").mkdir(exist_ok=True)

    def _setup_logging(self):
        """Konfiguruje logowanie"""
        log_file = self.logs_dir / f"sejmbot_{datetime.now().strftime('%Y%m%d')}.log"

        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file, encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)

    def get_session_headers(self) -> Dict[str, str]:
        """Zwraca nagłówki HTTP z User-Agent"""
        return {
            'User-Agent': self.user_agent,
            **self.headers
        }
