# mp_scraper.py
"""
Scraper danych posłów z API Sejmu RP
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional

from config import DEFAULT_TERM, BASE_OUTPUT_DIR
from sejm_api import SejmAPI

logger = logging.getLogger(__name__)


class MPScraper:
    """Scraper do pobierania i zarządzania danymi posłów"""

    def __init__(self):
        self.api = SejmAPI()
        self.base_dir = Path(BASE_OUTPUT_DIR)
        self.stats = {
            'mps_downloaded': 0,
            'clubs_downloaded': 0,
            'photos_downloaded': 0,
            'errors': 0,
            'voting_stats_downloaded': 0
        }

    def _ensure_mp_directory(self, term: int) -> Path:
        """Tworzy strukturę katalogów dla danych posłów"""
        mp_dir = self.base_dir / f"kadencja_{term:02d}" / "poslowie"
        mp_dir.mkdir(parents=True, exist_ok=True)

        # Podkatalogi
        (mp_dir / "zdjecia").mkdir(exist_ok=True)
        (mp_dir / "kluby").mkdir(exist_ok=True)
        (mp_dir / "statystyki_glosowan").mkdir(exist_ok=True)

        return mp_dir

    @staticmethod
    def _save_json(data: Dict, filepath: Path) -> bool:
        """Zapisuje dane do pliku JSON"""
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.debug(f"Zapisano JSON: {filepath}")
            return True
        except Exception as e:
            logger.error(f"Błąd zapisywania {filepath}: {e}")
            return False

    def _download_mp_photo(self, term: int, mp_id: int, mp_dir: Path) -> Optional[str]:
        """
        Pobiera zdjęcie posła

        Args:
            term: numer kadencji
            mp_id: ID posła
            mp_dir: katalog dla danych posłów

        Returns:
            Ścieżka do zapisanego zdjęcia lub None
        """
        try:
            logger.debug(f"Pobieranie zdjęcia posła {mp_id}")
            photo_content = self.api._make_request(f"/sejm/term{term}/MP/{mp_id}/photo")

            if photo_content and isinstance(photo_content, bytes):
                # Sprawdź typ zawartości po pierwszych bajtach
                if photo_content.startswith(b'\x89PNG'):
                    ext = 'png'
                elif photo_content.startswith(b'\xff\xd8'):
                    ext = 'jpg'
                else:
                    ext = 'jpg'  # domyślnie

                photo_path = mp_dir / "zdjecia" / f"posel_{mp_id:03d}.{ext}"

                with open(photo_path, 'wb') as f:
                    f.write(photo_content)

                logger.debug(f"Zapisano zdjęcie: {photo_path}")
                self.stats['photos_downloaded'] += 1
                return str(photo_path.relative_to(self.base_dir))
            else:
                logger.debug(f"Brak zdjęcia dla posła {mp_id}")
                return None

        except Exception as e:
            logger.warning(f"Błąd pobierania zdjęcia posła {mp_id}: {e}")
            return None

    def _download_mp_voting_stats(self, term: int, mp_id: int, mp_dir: Path) -> Optional[str]:
        """
        Pobiera statystyki głosowań posła

        Args:
            term: numer kadencji
            mp_id: ID posła
            mp_dir: katalog dla danych posłów

        Returns:
            Ścieżka do zapisanych statystyk lub None
        """
        try:
            logger.debug(f"Pobieranie statystyk głosowań posła {mp_id}")
            stats = self.api._make_request(f"/sejm/term{term}/MP/{mp_id}/votings/stats")

            if stats:
                stats_path = mp_dir / "statystyki_glosowan" / f"posel_{mp_id:03d}_statystyki.json"

                if self._save_json(stats, stats_path):
                    self.stats['voting_stats_downloaded'] += 1
                    return str(stats_path.relative_to(self.base_dir))

            return None

        except Exception as e:
            logger.warning(f"Błąd pobierania statystyk głosowań posła {mp_id}: {e}")
            return None

    @staticmethod
    def _safe_format_id(id_value, default_width=2):
        """
        Bezpiecznie formatuje ID - może być string lub int

        Args:
            id_value: wartość ID (string lub int)
            default_width: szerokość formatowania dla int

        Returns:
            Sformatowane ID jako string
        """
        try:
            # Spróbuj przekonwertować na int i sformatować
            id_int = int(id_value)
            return f"{id_int:0{default_width}d}"
        except (ValueError, TypeError):
            # Jeśli nie da się przekonwertować, użyj jako string
            return str(id_value)

    def scrape_clubs(self, term: int = DEFAULT_TERM) -> Dict:
        """
        Pobiera informacje o klubach parlamentarnych

        Args:
            term: numer kadencji

        Returns:
            Statystyki procesu
        """
        logger.info(f"Pobieranie klubów parlamentarnych kadencji {term}")

        mp_dir = self._ensure_mp_directory(term)
        clubs_dir = mp_dir / "kluby"

        try:
            # Pobierz listę klubów
            clubs = self.api._make_request(f"/sejm/term{term}/clubs")
            if not clubs:
                logger.error("Nie można pobrać listy klubów")
                return self.stats

            logger.info(f"Znaleziono {len(clubs)} klubów")

            # Zapisz pełną listę klubów
            clubs_list_path = clubs_dir / "lista_klubow.json"
            self._save_json(clubs, clubs_list_path)

            # Pobierz szczegóły każdego klubu
            for club in clubs:
                club_id = club.get('id')
                club_name = club.get('name', f'klub_{club_id}')

                if not club_id:
                    continue

                try:
                    logger.info(f"Pobieranie szczegółów klubu: {club_name}")

                    # Szczegóły klubu
                    club_details = self.api._make_request(f"/sejm/term{term}/clubs/{club_id}")
                    if club_details:
                        safe_name = self._make_safe_filename(club_name)
                        # Bezpieczne formatowanie ID
                        formatted_id = self._safe_format_id(club_id, 2)
                        club_path = clubs_dir / f"klub_{formatted_id}_{safe_name}.json"
                        self._save_json(club_details, club_path)

                    # Logo klubu
                    logo_content = self.api._make_request(f"/sejm/term{term}/clubs/{club_id}/logo")
                    if logo_content and isinstance(logo_content, bytes):
                        # Określ rozszerzenie na podstawie zawartości
                        if logo_content.startswith(b'\x89PNG'):
                            ext = 'png'
                        elif logo_content.startswith(b'\xff\xd8'):
                            ext = 'jpg'
                        elif logo_content.startswith(b'GIF'):
                            ext = 'gif'
                        else:
                            ext = 'png'  # domyślnie

                        safe_name = self._make_safe_filename(club_name)
                        formatted_id = self._safe_format_id(club_id, 2)
                        logo_path = clubs_dir / f"logo_{formatted_id}_{safe_name}.{ext}"
                        with open(logo_path, 'wb') as f:
                            f.write(logo_content)
                        logger.debug(f"Zapisano logo klubu: {logo_path}")

                    self.stats['clubs_downloaded'] += 1

                except Exception as e:
                    logger.error(f"Błąd pobierania klubu {club_name}: {e}")
                    self.stats['errors'] += 1

            logger.info(f"Zakończono pobieranie klubów: {self.stats['clubs_downloaded']} pobranych")

        except Exception as e:
            logger.error(f"Błąd pobierania klubów: {e}")
            self.stats['errors'] += 1

        return self.stats

    def scrape_mps(self, term: int = DEFAULT_TERM, download_photos: bool = True,
                   download_voting_stats: bool = True) -> Dict:
        """
        Pobiera dane wszystkich posłów z danej kadencji

        Args:
            term: numer kadencji
            download_photos: czy pobierać zdjęcia posłów
            download_voting_stats: czy pobierać statystyki głosowań

        Returns:
            Statystyki procesu
        """
        logger.info(f"Rozpoczynanie pobierania danych posłów kadencji {term}")

        mp_dir = self._ensure_mp_directory(term)

        try:
            # Pobierz listę posłów
            mps = self.api._make_request(f"/sejm/term{term}/MP")
            if not mps:
                logger.error("Nie można pobrać listy posłów")
                return self.stats

            logger.info(f"Znaleziono {len(mps)} posłów")

            # Zapisz pełną listę posłów
            mps_list_path = mp_dir / "lista_poslow.json"
            self._save_json(mps, mps_list_path)

            # Pobierz szczegóły każdego posła
            for i, mp in enumerate(mps, 1):
                mp_id = mp.get('id')
                mp_name = f"{mp.get('lastName', '')} {mp.get('firstName', '')}".strip()

                if not mp_id:
                    continue

                logger.info(f"[{i}/{len(mps)}] Pobieranie danych posła: {mp_name} (ID: {mp_id})")

                try:
                    # Pobierz szczegółowe dane posła
                    mp_details = self.api._make_request(f"/sejm/term{term}/MP/{mp_id}")
                    if mp_details:
                        # Dodaj dodatkowe metadane
                        mp_details['_metadata'] = {
                            'scraped_at': datetime.now().isoformat(),
                            'term': term,
                            'scraper_version': '1.0'
                        }

                        # Ścieżki do dodatkowych plików
                        mp_details['_files'] = {}

                        # Pobierz zdjęcie, jeśli wymagane
                        if download_photos:
                            photo_path = self._download_mp_photo(term, mp_id, mp_dir)
                            if photo_path:
                                mp_details['_files']['photo'] = photo_path

                        # Pobierz statystyki głosowań, jeśli wymagane
                        if download_voting_stats:
                            stats_path = self._download_mp_voting_stats(term, mp_id, mp_dir)
                            if stats_path:
                                mp_details['_files']['voting_stats'] = stats_path

                        # Zapisz dane posła
                        safe_name = self._make_safe_filename(mp_name)
                        mp_path = mp_dir / f"posel_{mp_id:03d}_{safe_name}.json"

                        if self._save_json(mp_details, mp_path):
                            self.stats['mps_downloaded'] += 1
                        else:
                            self.stats['errors'] += 1
                    else:
                        logger.warning(f"Nie można pobrać szczegółów posła {mp_name}")
                        self.stats['errors'] += 1

                except Exception as e:
                    logger.error(f"Błąd pobierania danych posła {mp_name}: {e}")
                    self.stats['errors'] += 1

            # Utwórz podsumowanie
            self._create_summary_report(term, mp_dir, mps)

            logger.info("=== STATYSTYKI POBIERANIA POSŁÓW ===")
            logger.info(f"Pobrani posłowie: {self.stats['mps_downloaded']}")
            logger.info(f"Pobrane zdjęcia: {self.stats['photos_downloaded']}")
            logger.info(f"Pobrane statystyki głosowań: {self.stats['voting_stats_downloaded']}")
            logger.info(f"Błędy: {self.stats['errors']}")
            logger.info("===================================")

        except Exception as e:
            logger.error(f"Błąd podczas pobierania posłów: {e}")
            self.stats['errors'] += 1

        return self.stats

    def _create_summary_report(self, term: int, mp_dir: Path, mps: List[Dict]):
        """Tworzy raport podsumowujący pobrane dane"""
        try:
            # Grupuj posłów według klubów
            clubs_summary = {}
            by_voivodeship = {}

            for mp in mps:
                club = mp.get('club')
                voivodeship = mp.get('voivodeship')

                # Grupowanie po klubach
                if club:
                    if club not in clubs_summary:
                        clubs_summary[club] = {'count': 0, 'members': []}
                    clubs_summary[club]['count'] += 1
                    clubs_summary[club]['members'].append({
                        'id': mp.get('id'),
                        'firstName': mp.get('firstName'),
                        'lastName': mp.get('lastName')
                    })

                # Grupowanie po województwach
                if voivodeship:
                    if voivodeship not in by_voivodeship:
                        by_voivodeship[voivodeship] = {'count': 0, 'members': []}
                    by_voivodeship[voivodeship]['count'] += 1
                    by_voivodeship[voivodeship]['members'].append({
                        'id': mp.get('id'),
                        'firstName': mp.get('firstName'),
                        'lastName': mp.get('lastName'),
                        'club': club
                    })

            summary = {
                'term': term,
                'generated_at': datetime.now().isoformat(),
                'total_mps': len(mps),
                'stats': self.stats.copy(),
                'by_clubs': clubs_summary,
                'by_voivodeships': by_voivodeship,
                'clubs_count': len(clubs_summary),
                'voivodeships_count': len(by_voivodeship)
            }

            summary_path = mp_dir / "podsumowanie_poslow.json"
            self._save_json(summary, summary_path)

            # Utwórz także prosty CSV dla łatwego importu
            self._create_csv_export(mp_dir, mps)

        except Exception as e:
            logger.error(f"Błąd tworzenia raportu podsumowującego: {e}")

    @staticmethod
    def _create_csv_export(mp_dir: Path, mps: List[Dict]):
        """Tworzy eksport CSV z podstawowymi danymi posłów"""
        try:
            import csv

            csv_path = mp_dir / "poslowie.csv"

            with open(csv_path, 'w', newline='', encoding='utf-8') as f:
                fieldnames = [
                    'id', 'firstName', 'lastName', 'club', 'voivodeship',
                    'districtName', 'districtNum', 'numberOfVotes', 'email'
                ]

                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()

                for mp in mps:
                    row = {field: mp.get(field, '') for field in fieldnames}
                    writer.writerow(row)

            logger.info(f"Utworzono eksport CSV: {csv_path}")

        except Exception as e:
            logger.warning(f"Nie udało się utworzyć eksportu CSV: {e}")

    @staticmethod
    def _make_safe_filename(name: str) -> str:
        """Czyści nazwę dla bezpiecznej nazwy pliku"""
        safe_chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-"
        safe_name = ''.join(c if c in safe_chars else '_' for c in name)

        # Skraca, jeśli za długie
        if len(safe_name) > 50:
            safe_name = safe_name[:50]

        return safe_name

    def scrape_specific_mp(self, term: int, mp_id: int, download_photos: bool = True,
                           download_voting_stats: bool = True) -> bool:
        """
        Pobiera dane konkretnego posła

        Args:
            term: numer kadencji
            mp_id: ID posła
            download_photos: czy pobrać zdjęcie
            download_voting_stats: czy pobrać statystyki głosowań

        Returns:
            True, jeśli sukces
        """
        logger.info(f"Pobieranie danych posła ID {mp_id} z kadencji {term}")

        mp_dir = self._ensure_mp_directory(term)

        try:
            # Pobierz dane posła
            mp_details = self.api._make_request(f"/sejm/term{term}/MP/{mp_id}")
            if not mp_details:
                logger.error(f"Nie można pobrać danych posła {mp_id}")
                return False

            mp_name = f"{mp_details.get('lastName', '')} {mp_details.get('firstName', '')}".strip()
            logger.info(f"Pobieranie danych posła: {mp_name}")

            # Dodaj metadane
            mp_details['_metadata'] = {
                'scraped_at': datetime.now().isoformat(),
                'term': term,
                'scraper_version': '1.0'
            }

            mp_details['_files'] = {}

            # Pobierz zdjęcie
            if download_photos:
                photo_path = self._download_mp_photo(term, mp_id, mp_dir)
                if photo_path:
                    mp_details['_files']['photo'] = photo_path

            # Pobierz statystyki głosowań
            if download_voting_stats:
                stats_path = self._download_mp_voting_stats(term, mp_id, mp_dir)
                if stats_path:
                    mp_details['_files']['voting_stats'] = stats_path

            # Zapisz dane posła
            safe_name = self._make_safe_filename(mp_name)
            mp_path = mp_dir / f"posel_{mp_id:03d}_{safe_name}.json"

            if self._save_json(mp_details, mp_path):
                logger.info(f"Zapisano dane posła: {mp_path}")
                self.stats['mps_downloaded'] += 1
                return True
            else:
                return False

        except Exception as e:
            logger.error(f"Błąd pobierania posła {mp_id}: {e}")
            self.stats['errors'] += 1
            return False

    def get_mps_summary(self, term: int = DEFAULT_TERM) -> Optional[Dict]:
        """
        Zwraca podsumowanie posłów bez pobierania szczegółów

        Args:
            term: numer kadencji

        Returns:
            Słownik z podsumowaniem lub None
        """
        try:
            mps = self.api._make_request(f"/sejm/term{term}/MP")
            if mps is None:  # Sprawdzaj explicite None
                return None

            clubs = {}
            for mp in mps:
                club = mp.get('club', 'Brak klubu')
                if club not in clubs:
                    clubs[club] = 0
                clubs[club] += 1

            return {
                'term': term,
                'total_mps': len(mps),
                'clubs': clubs,
                'clubs_count': len(clubs)
            }

        except Exception as e:
            logger.error(f"Błąd pobierania podsumowania posłów: {e}")
            return None

    def scrape_complete_term_data(self, term: int = DEFAULT_TERM) -> Dict:
        """
        Pobiera wszystkie dane związane z posłami dla danej kadencji

        Args:
            term: numer kadencji

        Returns:
            Statystyki procesu
        """
        logger.info(f"Rozpoczynanie pobierania pełnych danych kadencji {term}")

        # Pobierz kluby
        self.scrape_clubs(term)

        # Pobierz posłów
        self.scrape_mps(term, download_photos=True, download_voting_stats=True)

        return self.stats
