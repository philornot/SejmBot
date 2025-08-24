#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ZnajdowaczPoslowInator - scraper do parsowania danych posłów z pliku HTML
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Tuple

from bs4 import BeautifulSoup

try:
    from SejmBotDetektor.logging.logger import get_module_logger
except ImportError:
    import logging


    def get_module_logger(name):
        return logging.getLogger(name)


class ZnajdowaczPoslowInator:
    """
    Klasa do parsowania danych posłów z pliku HTML i konwersji do formatu JSON
    """

    def __init__(self, html_file_path: str = "poslowie.html"):
        """
        Inicjalizacja scrapera

        Args:
            html_file_path (str): Ścieżka do pliku HTML z danymi posłów
        """
        self.html_file_path = Path(html_file_path)
        self.logger = get_module_logger("ZnajdowaczPoslowInator")

        # Mapowanie skrótów klubów na pełne nazwy
        self.kluby_mapping = {
            "PiS": "Prawo i Sprawiedliwość",
            "KO": "Platforma Obywatelska - Koalicja Obywatelska",
            "Polska2050-TD": "Polska 2050 - Trzecia Droga",
            "PSL-TD": "Polskie Stronnictwo Ludowe - Trzecia Droga",
            "Lewica": "Lewica",
            "Konfederacja": "Konfederacja Wolność i Niepodległość",
            "Konfederacja_KP": "Konfederacja Wolność i Niepodległość",
            "Republikanie": "Republikanie",
            "niez.": "Bezpartyjny"
        }

        # Standardowe skróty klubów
        self.kluby_skroty = {
            "Prawo i Sprawiedliwość": ["PiS", "Prawo i Sprawiedliwość"],
            "Platforma Obywatelska - Koalicja Obywatelska": ["PO", "KO", "Platforma Obywatelska",
                                                             "Koalicja Obywatelska"],
            "Polska 2050 - Trzecia Droga": ["P2050", "Polska2050-TD", "Polska 2050", "Trzecia Droga"],
            "Polskie Stronnictwo Ludowe - Trzecia Droga": ["PSL", "PSL-TD", "Polskie Stronnictwo Ludowe"],
            "Lewica": ["Lewica", "SLD", "Razem"],
            "Konfederacja Wolność i Niepodległość": ["Konfederacja", "Konfederacja_KP", "Wolność i Niepodległość"],
            "Republikanie": ["Republikanie"],
            "Bezpartyjny": ["Bezpartyjny", "Niezrzeszony", "niez."]
        }

        self.logger.info(f"Zainicjalizowano ZnajdowaczPoslowInator z plikiem: {self.html_file_path}")

    def wczytaj_html(self) -> BeautifulSoup:
        """
        Wczytuje i parsuje plik HTML

        Returns:
            BeautifulSoup: Sparsowany dokument HTML

        Raises:
            FileNotFoundError: Gdy plik HTML nie zostanie znaleziony
        """
        self.logger.debug("Rozpoczynam wczytywanie pliku HTML")

        if not self.html_file_path.exists():
            self.logger.error(f"Plik HTML nie został znaleziony: {self.html_file_path}")
            raise FileNotFoundError(f"Plik {self.html_file_path} nie istnieje")

        try:
            with open(self.html_file_path, 'r', encoding='utf-8') as file:
                content = file.read()
                self.logger.success(f"Pomyślnie wczytano plik HTML ({len(content)} znaków)")

            soup = BeautifulSoup(content, 'html.parser')
            self.logger.debug("Pomyślnie sparsowano HTML z BeautifulSoup")
            return soup

        except Exception as e:
            self.logger.error(f"Błąd podczas wczytywania pliku HTML: {e}")
            raise

    def zamien_nazwisko_imie(self, name: str) -> str:
        """
        Zamienia kolejność z "Nazwisko Imię" na "Imię Nazwisko"

        Args:
            name (str): Nazwa w formacie "Nazwisko Imię"

        Returns:
            str: Nazwa w formacie "Imię Nazwisko"
        """
        parts = name.split()
        if len(parts) >= 2:
            # Ostatni element to imię, reszta to nazwisko
            imie = parts[-1]
            nazwisko = " ".join(parts[:-1])
            return f"{imie} {nazwisko}"
        return name

    def wyciagnij_dane_posla(self, li_element) -> Optional[Tuple[str, str, str]]:
        """
        Wyciąga dane pojedynczego posła z elementu <li>

        Args:
            li_element: Element <li> zawierający dane posła

        Returns:
            Optional[Tuple[str, str, str]]: (imię_nazwisko, klub, dodatkowe_info) lub None
        """
        try:
            # Szukamy nazwy posła
            name_div = li_element.find('div', class_='deputyName')
            if not name_div:
                self.logger.warning("Nie znaleziono elementu deputyName")
                return None

            name_raw = name_div.get_text(strip=True)
            if not name_raw:
                self.logger.warning("Puste imię i nazwisko posła")
                return None

            # Zamieniamy kolejność na Imię Nazwisko
            name = self.zamien_nazwisko_imie(name_raw)
            self.logger.debug(f"Zamieniono '{name_raw}' na '{name}'")

            # Szukamy klubu parlamentarnego
            club_div = li_element.find('div', class_='deputy-box-details')
            if not club_div:
                self.logger.warning(f"Nie znaleziono klubu dla posła: {name}")
                return None

            club_strong = club_div.find('strong')
            if not club_strong:
                self.logger.warning(f"Nie znaleziono znacznika <strong> z klubem dla posła: {name}")
                return None

            club_short = club_strong.get_text(strip=True)

            # Mapowanie skrótu na pełną nazwę klubu
            club_full = self.kluby_mapping.get(club_short, club_short)

            # Wyciągnij dodatkowe informacje (jeśli są)
            additional_info = ""
            club_text = club_div.get_text(strip=True)
            # Usuwamy klub ze začátku tekstu
            if club_text.startswith(club_short):
                additional_info = club_text[len(club_short):].strip()

            self.logger.debug(f"Przetworzono posła: {name} ({club_full})")

            return name, club_full, additional_info

        except Exception as e:
            self.logger.error(f"Błąd podczas przetwarzania danych posła: {e}")
            return None

    def znajdz_funkcje_specjalne(self, soup: BeautifulSoup) -> Dict:
        """
        Identyfikuje posłów pełniących specjalne funkcje na podstawie dodatkowych informacji

        Args:
            soup: Sparsowany dokument HTML

        Returns:
            Dict: Słownik z funkcjami specjalnymi
        """
        self.logger.section("Szukam funkcji specjalnych")

        funkcje = {
            "Marszałek Sejmu": None,
            "Wicemarszałek Sejmu": [],
            "Przewodniczący klubu PiS": None,
            "Przewodniczący klubu KO": None,
            "Przewodniczący klubu Lewica": None
        }

        try:
            # Szukamy wszystkich elementów z dodatkowymi informacjami
            for li in soup.find_all('li'):
                name_div = li.find('div', class_='deputyName')
                details_div = li.find('div', class_='deputy-box-details')

                if not name_div or not details_div:
                    continue

                name = name_div.get_text(strip=True)
                details_text = details_div.get_text(strip=True).lower()

                # Szukamy przewodniczących klubów
                if "przewodniczący klubu" in details_text:
                    if any(club in details_text for club in ["pis"]):
                        funkcje["Przewodniczący klubu PiS"] = name
                        self.logger.keyvalue("Przewodniczący klubu PiS", name)
                    elif any(club in details_text for club in ["ko"]):
                        funkcje["Przewodniczący klubu KO"] = name
                        self.logger.keyvalue("Przewodniczący klubu KO", name)

                # Szukamy przewodniczącej klubu Lewica
                if "przewodnicząca klubu" in details_text:
                    club_strong = details_div.find('strong')
                    if club_strong and "lewica" in club_strong.get_text(strip=True).lower():
                        funkcje["Przewodniczący klubu Lewica"] = name
                        self.logger.keyvalue("Przewodnicząca klubu Lewica", name)

        except Exception as e:
            self.logger.error(f"Błąd podczas wyszukiwania funkcji specjalnych: {e}")

        return funkcje

    def parsuj_poslowie(self) -> Dict:
        """
        Główna metoda parsująca dane posłów z HTML

        Returns:
            Dict: Słownik z danymi posłów w formacie JSON
        """
        self.logger.header("Rozpoczynam parsowanie danych posłów")

        soup = self.wczytaj_html()

        poslowie_dict = {}
        funkcje_specjalne = self.znajdz_funkcje_specjalne(soup)

        # Znajdujemy wszystkie elementy <li> z danymi posłów
        deputy_elements = soup.find_all('li')
        self.logger.info(f"Znaleziono {len(deputy_elements)} elementów z potencjalnymi danymi posłów")

        przetworzeni_count = 0
        bledy_count = 0

        for li in deputy_elements:
            dane_posla = self.wyciagnij_dane_posla(li)

            if dane_posla:
                name, club, additional_info = dane_posla
                poslowie_dict[name] = club
                przetworzeni_count += 1

                if additional_info:
                    self.logger.debug(f"{name}: {additional_info}")
            else:
                bledy_count += 1

        self.logger.success(f"Przetworzono {przetworzeni_count} posłów")
        if bledy_count > 0:
            self.logger.warning(f"Napotkano {bledy_count} błędów podczas przetwarzania")

        # Tworzenie finalnej struktury danych
        wynik = {
            "metadata": {
                "description": "Baza danych posłów z przypisaniem do klubów parlamentarnych",
                "last_updated": datetime.now().strftime("%Y-%m-%d"),
                "source": "Sejm RP",
                "kadencja": "X",
                "scraped_count": przetworzeni_count
            },
            "poslowie": poslowie_dict,
            "kluby_skroty": self.kluby_skroty,
            "funkcje": funkcje_specjalne
        }

        self.logger.header("Zakończono parsowanie danych")
        return wynik

    def zapisz_json(self, data: Dict, output_file: str = "poslowie_kluby.json"):
        """
        Zapisuje dane do pliku JSON

        Args:
            data (Dict): Dane do zapisania
            output_file (str): Nazwa pliku wyjściowego
        """
        self.logger.section(f"Zapisuję dane do pliku: {output_file}")

        try:
            output_path = Path(output_file)
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            self.logger.success(f"Dane zostały zapisane do: {output_path.absolute()}")
            self.logger.keyvalue("Liczba posłów", len(data.get('poslowie', {})))

        except Exception as e:
            self.logger.error(f"Błąd podczas zapisywania pliku JSON: {e}")
            raise

    def uruchom(self, output_file: str = "poslowie_kluby.json") -> Dict:
        """
        Uruchamia cały proces scrapowania

        Args:
            output_file (str): Nazwa pliku wyjściowego

        Returns:
            Dict: Sparsowane dane
        """
        try:
            self.logger.header("=== ZNAJDOWACZ POSŁÓW INATOR ===")

            # Parsowanie danych
            dane = self.parsuj_poslowie()

            # Zapis do JSON
            self.zapisz_json(dane, output_file)

            # Podsumowanie
            self.logger.section("PODSUMOWANIE")
            self.logger.keyvalue("Przetworzonych posłów", len(dane['poslowie']))
            self.logger.keyvalue("Klubów parlamentarnych", len(set(dane['poslowie'].values())))
            self.logger.keyvalue("Plik wyjściowy", output_file)

            return dane

        except Exception as e:
            self.logger.critical(f"Krytyczny błąd podczas scrapowania: {e}")
            raise


def main():
    """Główna funkcja uruchamiająca scraper"""
    scraper = ZnajdowaczPoslowInator("poslowie.html")
    dane = scraper.uruchom("poslowie_kluby.json")
    return dane


if __name__ == "__main__":
    main()
