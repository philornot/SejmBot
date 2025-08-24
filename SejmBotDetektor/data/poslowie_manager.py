"""
Menadżer bazy danych posłów do przypisywania klubów parlamentarnych
"""
import json
import os
import re
from difflib import SequenceMatcher
from typing import Dict, Optional, Tuple

from SejmBotDetektor.logging.logger import get_module_logger


class PoslowieManager:
    """Klasa do zarządzania bazą posłów i przypisywania klubów"""

    def __init__(self, debug: bool = False):
        self.debug = debug
        self.logger = get_module_logger("PoslowieManager")

        # Dane z pliku JSON
        self.poslowie_data = {}
        self.poslowie_dict = {}  # {imie_nazwisko: klub}
        self.kluby_skroty = {}  # {klub_pelny: [lista_skrotow]}
        self.funkcje = {}  # {funkcja: osoba/lista_osob}

        # Cache do szybszego wyszukiwania
        self.name_cache = {}  # {normalized_name: original_name}
        self.fuzzy_cache = {}  # Cache dla fuzzy matching

        # Ładujemy dane
        self._load_poslowie_data()

    def _load_poslowie_data(self) -> bool:
        """Ładuje dane posłów z pliku JSON"""
        # Szukamy pliku w różnych lokalizacjach
        possible_paths = [
            "poslowie_kluby.json",
            "SejmBotDetektor/data/poslowie_kluby.json",
            "data/poslowie_kluby.json",
            os.path.join(os.path.dirname(__file__), "..", "data", "poslowie_kluby.json")
        ]

        data_file = None
        for path in possible_paths:
            if os.path.exists(path):
                data_file = path
                break

        if not data_file:
            self.logger.warning("Nie znaleziono pliku poslowie_kluby.json - tworząc pusty")
            self._create_empty_data()
            return False

        try:
            with open(data_file, 'r', encoding='utf-8') as f:
                self.poslowie_data = json.load(f)

            self.poslowie_dict = self.poslowie_data.get('poslowie', {})
            self.kluby_skroty = self.poslowie_data.get('kluby_skroty', {})
            self.funkcje = self.poslowie_data.get('funkcje', {})

            # Budujemy cache nazw
            self._build_name_cache()

            if self.debug:
                self.logger.debug(f"Załadowano {len(self.poslowie_dict)} posłów z pliku {data_file}")

            return True

        except (json.JSONDecodeError, FileNotFoundError) as e:
            self.logger.error(f"Błąd podczas ładowania danych posłów: {e}")
            self._create_empty_data()
            return False

    def _create_empty_data(self):
        """Tworzy pustą strukturę danych"""
        self.poslowie_data = {
            "metadata": {"description": "Pusta baza posłów", "last_updated": ""},
            "poslowie": {},
            "kluby_skroty": {},
            "funkcje": {}
        }
        self.poslowie_dict = {}
        self.kluby_skroty = {}
        self.funkcje = {}

    def _build_name_cache(self):
        """Buduje cache znormalizowanych nazw dla szybszego wyszukiwania"""
        self.name_cache = {}

        for full_name in self.poslowie_dict.keys():
            # Różne warianty normalizacji
            normalized_variants = [
                self._normalize_name(full_name),
                self._normalize_name(full_name, remove_titles=True),
                self._normalize_name(full_name, remove_titles=True, remove_hyphens=True)
            ]

            for variant in normalized_variants:
                if variant and variant not in self.name_cache:
                    self.name_cache[variant] = full_name

        if self.debug:
            self.logger.debug(f"Zbudowano cache nazw: {len(self.name_cache)} wariantów")

    def _normalize_name(self, name: str, remove_titles: bool = False, remove_hyphens: bool = False) -> str:
        """
        Normalizuje nazwę osoby do porównywania

        Args:
            name: Nazwa do normalizacji
            remove_titles: Czy usunąć tytuły (Dr, Prof, itp.)
            remove_hyphens: Czy usunąć myślniki z nazwisk

        Returns:
            Znormalizowana nazwa
        """
        if not name:
            return ""

        # Podstawowe czyszczenie
        normalized = name.strip()

        # Usuwanie tytułów
        if remove_titles:
            titles = ['dr', 'prof', 'mgr', 'inż', 'ks', 'gen']
            for title in titles:
                normalized = re.sub(rf'\b{title}\.?\s+', '', normalized, flags=re.IGNORECASE)

        # Usuwanie myślników z nazwisk złożonych
        if remove_hyphens:
            # Zachowujemy myślniki w imionach typu "Anna-Maria", ale usuwamy z "Kowalski-Nowak"
            parts = normalized.split()
            if len(parts) >= 2:
                # Zakładamy że ostatnia część to nazwisko
                lastname = parts[-1].replace('-', '')
                normalized = ' '.join(parts[:-1] + [lastname])

        # Finalne czyszczenie
        normalized = re.sub(r'\s+', ' ', normalized).strip().lower()

        return normalized

    def find_club_for_speaker(self, speaker_raw: str) -> Tuple[str, Optional[str]]:
        """
        Główna metoda - znajduje klub dla mówcy

        Args:
            speaker_raw: Surowa nazwa mówcy z tekstu

        Returns:
            Tuple (cleaned_name, club_name) lub (speaker_raw, None) jeśli nie znaleziono
        """
        if not speaker_raw or speaker_raw == "Nieznany mówca":
            return "Nieznany mówca", None

        # Sprawdzamy cache
        if speaker_raw in self.fuzzy_cache:
            return self.fuzzy_cache[speaker_raw]

        # Czyścimy nazwę mówcy
        cleaned_name = self._extract_name_from_speaker(speaker_raw)

        if not cleaned_name or cleaned_name == "Nieznany mówca":
            result = (speaker_raw, None)
            self.fuzzy_cache[speaker_raw] = result
            return result

        # 1. Próbujemy exact match
        club = self._find_exact_match(cleaned_name)
        if club:
            result = (cleaned_name, club)
            self.fuzzy_cache[speaker_raw] = result
            if self.debug:
                self.logger.debug(f"Exact match: '{cleaned_name}' -> '{club}'")
            return result

        # 2. Próbujemy fuzzy matching
        club = self._find_fuzzy_match(cleaned_name)
        if club:
            result = (cleaned_name, club)
            self.fuzzy_cache[speaker_raw] = result
            if self.debug:
                self.logger.debug(f"Fuzzy match: '{cleaned_name}' -> '{club}'")
            return result

        # 3. Nie znaleziono
        result = (cleaned_name, None)
        self.fuzzy_cache[speaker_raw] = result

        if self.debug:
            self.logger.debug(f"Nie znaleziono klubu dla: '{cleaned_name}'")

        return result

    def _extract_name_from_speaker(self, speaker_raw: str) -> str:
        """Wyciąga czyste imię i nazwisko z surowej nazwy mówcy"""
        if not speaker_raw:
            return ""

        # Usuwamy rzeczy w nawiasach (stare kluby)
        name = re.sub(r'\([^)]*\)', '', speaker_raw).strip()

        # Usuwamy tytuły urzędowe
        titles_pattern = r'^(Poseł|Posłanka|Marszałek|Wicemarszałek|Minister|Przewodniczący|Sekretarz)\s+'
        name = re.sub(titles_pattern, '', name, flags=re.IGNORECASE).strip()

        # Usuwamy "brak klubu" jeśli zostało
        name = re.sub(r'\bbrak\s+klubu\b', '', name, flags=re.IGNORECASE).strip()

        return name

    def _find_exact_match(self, name: str) -> Optional[str]:
        """Szuka dokładnego dopasowania w cache nazw"""
        normalized = self._normalize_name(name)

        # Sprawdzamy różne warianty normalizacji
        variants = [
            normalized,
            self._normalize_name(name, remove_titles=True),
            self._normalize_name(name, remove_titles=True, remove_hyphens=True)
        ]

        for variant in variants:
            if variant in self.name_cache:
                original_name = self.name_cache[variant]
                return self.poslowie_dict.get(original_name)

        return None

    def _find_fuzzy_match(self, name: str, threshold: float = 0.8) -> Optional[str]:
        """Szuka dopasowania z użyciem fuzzy string matching"""
        if not name:
            return None

        normalized_input = self._normalize_name(name, remove_titles=True)
        best_match = None
        best_score = 0

        for db_name in self.poslowie_dict.keys():
            normalized_db = self._normalize_name(db_name)

            # SequenceMatcher ratio
            score = SequenceMatcher(None, normalized_input, normalized_db).ratio()

            if score > best_score and score >= threshold:
                best_score = score
                best_match = db_name

        if best_match:
            return self.poslowie_dict[best_match]

        return None

    def get_club_abbreviation(self, full_club_name: str) -> str:
        """Zwraca skrót klubu lub pełną nazwę jeśli nie ma skrótu"""
        if not full_club_name:
            return ""

        # Sprawdzamy czy mamy mapowanie skrótów
        for club_full, abbreviations in self.kluby_skroty.items():
            if club_full == full_club_name:
                # Zwracamy pierwszy (główny) skrót
                return abbreviations[0] if abbreviations else full_club_name

        return full_club_name

    def add_missing_deputy(self, name: str, club: str) -> bool:
        """
        Dodaje brakującego posła do bazy (runtime, nie zapisuje do pliku)

        Args:
            name: Imię i nazwisko
            club: Nazwa klubu

        Returns:
            True jeśli dodano pomyślnie
        """
        if not name or not club:
            return False

        # Dodajemy do runtime cache
        self.poslowie_dict[name] = club

        # Aktualizujemy cache nazw
        normalized_variants = [
            self._normalize_name(name),
            self._normalize_name(name, remove_titles=True),
            self._normalize_name(name, remove_titles=True, remove_hyphens=True)
        ]

        for variant in normalized_variants:
            if variant and variant not in self.name_cache:
                self.name_cache[variant] = name

        # Czyścimy fuzzy cache żeby przeliczyć
        self.fuzzy_cache.clear()

        if self.debug:
            self.logger.debug(f"Dodano brakującego posła: '{name}' -> '{club}'")

        return True

    def get_stats(self) -> Dict:
        """Zwraca statystyki bazy posłów"""
        return {
            'total_deputies': len(self.poslowie_dict),
            'total_clubs': len(set(self.poslowie_dict.values())),
            'cache_size': len(self.name_cache),
            'fuzzy_cache_size': len(self.fuzzy_cache),
            'clubs': list(set(self.poslowie_dict.values()))
        }

    def clear_cache(self):
        """Czyści cache wyszukiwania"""
        self.fuzzy_cache.clear()
        if self.debug:
            self.logger.debug("Wyczyszczono cache wyszukiwania")

    def reload_data(self) -> bool:
        """Przeładowuje dane z pliku"""
        self.clear_cache()
        return self._load_poslowie_data()
