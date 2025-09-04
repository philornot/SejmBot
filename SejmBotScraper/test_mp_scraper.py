#!/usr/bin/env python3
# test_mp_scraper.py
"""
Testuje wszystkie funkcjonalności scrapera w kontrolowany sposób
bez potrzeby pobierania pełnych danych.

UŻYCIE:
1. Pełny test:
python test_mp_scraper.py

2. Test tylko API:
python test_mp_scraper.py --test api

3. Test klubów:
python test_mp_scraper.py --test clubs

4. Test scrapera:
python test_mp_scraper.py --test scraper

Inna kadencja:
python test_mp_scraper.py -t 9

Szczegółowe logi:
python test_mp_scraper.py -v
"""

import json
import logging
import sys
import time
from pathlib import Path

from config import DEFAULT_TERM
from mp_scraper import MPScraper
from sejm_api import SejmAPI


def setup_test_logging():
    """Konfiguruje logowanie dla testów"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler(sys.stdout)]
    )


class MPScraperTester:
    """Klasa do testowania MP Scrapera"""

    def __init__(self):
        self.scraper = MPScraper()
        self.api = SejmAPI()
        self.test_results = []

    def run_test(self, test_name: str, test_func, *args, **kwargs):
        """
        Uruchamia pojedynczy test i zbiera wyniki

        Args:
            test_name: nazwa testu
            test_func: funkcja testowa
            *args, **kwargs: argumenty dla funkcji testowej
        """
        print(f"\n{'=' * 60}")
        print(f"🧪 TEST: {test_name}")
        print(f"{'=' * 60}")

        start_time = time.time()

        try:
            result = test_func(*args, **kwargs)
            duration = time.time() - start_time

            if result:
                status = "✅ PASSED"
                print(f"\n{status} - Czas: {duration:.2f}s")
            else:
                status = "❌ FAILED"
                print(f"\n{status} - Czas: {duration:.2f}s")

            self.test_results.append({
                'test': test_name,
                'status': 'PASSED' if result else 'FAILED',
                'duration': duration,
                'result': result
            })

            return result

        except Exception as e:
            duration = time.time() - start_time
            status = "💥 ERROR"
            print(f"\n{status} - Błąd: {e}")
            print(f"Czas: {duration:.2f}s")

            self.test_results.append({
                'test': test_name,
                'status': 'ERROR',
                'duration': duration,
                'error': str(e)
            })

            return False

    def test_api_connection(self) -> bool:
        """Test podstawowej łączności z API"""
        print("Sprawdzanie połączenia z API Sejmu...")

        terms = self.api.get_terms()
        if not terms:
            print("❌ Nie można pobrać listy kadencji")
            return False

        print(f"✅ Pobrano {len(terms)} kadencji")

        # Sprawdź aktualną kadencję
        current_term = None
        for term in terms:
            if term.get('current'):
                current_term = term
                break

        if current_term:
            print(f"📍 Aktualna kadencja: {current_term['num']}")
        else:
            print("⚠️  Nie znaleziono aktualnej kadencji")

        return True

    def test_clubs_api(self, term: int = DEFAULT_TERM) -> bool:
        """Test pobierania klubów przez API"""
        print(f"Testowanie API klubów dla kadencji {term}...")

        clubs = self.api.get_clubs(term)
        if not clubs:
            print("❌ Nie można pobrać listy klubów")
            return False

        print(f"✅ Znaleziono {len(clubs)} klubów")

        # Test szczegółów pierwszego klubu
        if clubs:
            first_club = clubs[0]
            club_id = first_club.get('id')
            club_name = first_club.get('name', 'Unknown')

            print(f"🔍 Testowanie szczegółów klubu: {club_name}")

            club_details = self.api.get_club_info(term, club_id)
            if club_details:
                print(f"✅ Pobrano szczegóły klubu {club_name}")
            else:
                print(f"⚠️  Brak szczegółów dla klubu {club_name}")

            # Test logo klubu
            logo = self.api.get_club_logo(term, club_id)
            if logo and isinstance(logo, bytes):
                print(f"✅ Pobrano logo klubu {club_name} ({len(logo)} bajtów)")
            else:
                print(f"⚠️  Brak logo dla klubu {club_name}")

        return True

    def test_mps_api(self, term: int = DEFAULT_TERM) -> bool:
        """Test pobierania posłów przez API"""
        print(f"Testowanie API posłów dla kadencji {term}...")

        mps = self.api.get_mps(term)
        if not mps:
            print("❌ Nie można pobrać listy posłów")
            return False

        print(f"✅ Znaleziono {len(mps)} posłów")

        # Test szczegółów pierwszego posła
        if mps:
            first_mp = mps[0]
            mp_id = first_mp.get('id')
            mp_name = f"{first_mp.get('lastName', '')} {first_mp.get('firstName', '')}".strip()

            print(f"🔍 Testowanie szczegółów posła: {mp_name}")

            mp_details = self.api.get_mp_info(term, mp_id)
            if mp_details:
                print(f"✅ Pobrano szczegóły posła {mp_name}")
            else:
                print(f"⚠️  Brak szczegółów dla posła {mp_name}")

            # Test zdjęcia posła
            photo = self.api.get_mp_photo(term, mp_id)
            if photo and isinstance(photo, bytes):
                print(f"✅ Pobrano zdjęcie posła {mp_name} ({len(photo)} bajtów)")
            else:
                print(f"⚠️  Brak zdjęcia dla posła {mp_name}")

            # Test statystyk głosowań
            stats = self.api.get_mp_voting_stats(term, mp_id)
            if stats:
                print(f"✅ Pobrano statystyki głosowań posła {mp_name}")
            else:
                print(f"⚠️  Brak statystyk głosowań dla posła {mp_name}")

        return True

    def test_scraper_clubs_only(self, term: int = DEFAULT_TERM) -> bool:
        """Test scrapowania tylko klubów"""
        print(f"Testowanie scrapera - tylko kluby (kadencja {term})...")

        # Reset statystyk
        self.scraper.stats = {
            'mps_downloaded': 0,
            'clubs_downloaded': 0,
            'photos_downloaded': 0,
            'errors': 0,
            'voting_stats_downloaded': 0
        }

        stats = self.scraper.scrape_clubs(term)

        print(f"📊 Wyniki:")
        print(f"   Pobrane kluby: {stats['clubs_downloaded']}")
        print(f"   Błędy: {stats['errors']}")

        if stats['clubs_downloaded'] > 0 and stats['errors'] == 0:
            print("✅ Test klubów zakończony sukcesem")
            return True
        elif stats['clubs_downloaded'] > 0:
            print("⚠️  Test klubów zakończony z błędami")
            return True
        else:
            print("❌ Test klubów nieudany")
            return False

    def test_scraper_specific_mp(self, term: int = DEFAULT_TERM) -> bool:
        """Test pobierania konkretnego posła"""
        print(f"Testowanie pobierania konkretnego posła (kadencja {term})...")

        # Najpierw pobierz listę posłów, żeby mieć jakieś ID
        mps = self.api.get_mps(term)
        if not mps:
            print("❌ Nie można pobrać listy posłów do testu")
            return False

        # Wybierz pierwszego posła
        first_mp = mps[0]
        mp_id = first_mp.get('id')
        mp_name = f"{first_mp.get('lastName', '')} {first_mp.get('firstName', '')}".strip()

        print(f"🎯 Testowanie posła: {mp_name} (ID: {mp_id})")

        # Reset statystyk
        self.scraper.stats = {
            'mps_downloaded': 0,
            'clubs_downloaded': 0,
            'photos_downloaded': 0,
            'errors': 0,
            'voting_stats_downloaded': 0
        }

        success = self.scraper.scrape_specific_mp(
            term,
            mp_id,
            download_photos=True,
            download_voting_stats=True
        )

        stats = self.scraper.stats
        print(f"📊 Wyniki:")
        print(f"   Pobrani posłowie: {stats['mps_downloaded']}")
        print(f"   Pobrane zdjęcia: {stats['photos_downloaded']}")
        print(f"   Pobrane statystyki: {stats['voting_stats_downloaded']}")
        print(f"   Błędy: {stats['errors']}")

        if success:
            print(f"✅ Pomyślnie pobrano posła {mp_name}")
        else:
            print(f"❌ Nie udało się pobrać posła {mp_name}")

        return success

    def test_file_structure(self, term: int = DEFAULT_TERM) -> bool:
        """Test sprawdzania struktury plików"""
        print("Sprawdzanie struktury plików...")

        base_dir = Path(self.scraper.base_dir)
        term_dir = base_dir / f"kadencja_{term:02d}" / "poslowie"

        if not term_dir.exists():
            print("⚠️  Katalog kadencji nie istnieje - uruchom najpierw scraper")
            return True  # To nie jest błąd w tym kontekście

        # Sprawdź podkatalogi
        subdirs = ['zdjecia', 'kluby', 'statystyki_glosowan']
        all_exist = True

        for subdir in subdirs:
            subdir_path = term_dir / subdir
            if subdir_path.exists():
                files_count = len(list(subdir_path.glob('*')))
                print(f"✅ {subdir}/: {files_count} plików")
            else:
                print(f"❌ Brak katalogu: {subdir}/")
                all_exist = False

        # Sprawdź główne pliki
        main_files = ['lista_poslow.json', 'poslowie.csv', 'podsumowanie_poslow.json']
        for file_name in main_files:
            file_path = term_dir / file_name
            if file_path.exists():
                print(f"✅ {file_name}")
            else:
                print(f"⚠️  Brak pliku: {file_name}")

        return all_exist

    def test_scraper_summary(self, term: int = DEFAULT_TERM) -> bool:
        """Test pobierania podsumowania posłów"""
        print(f"Testowanie podsumowania posłów (kadencja {term})...")

        summary = self.scraper.get_mps_summary(term)
        if not summary:
            print("❌ Nie można pobrać podsumowania")
            return False

        print(f"📊 Podsumowanie kadencji {summary['term']}:")
        print(f"   Łączna liczba posłów: {summary['total_mps']}")
        print(f"   Liczba klubów: {summary['clubs_count']}")

        print("\n🏛️  Posłowie według klubów:")
        for club, count in sorted(summary['clubs'].items(),
                                  key=lambda x: x[1], reverse=True):
            print(f"   {club}: {count} posłów")

        return True

    def test_data_integrity(self, term: int = DEFAULT_TERM) -> bool:
        """Test integralności pobranych danych"""
        print("Testowanie integralności danych...")

        base_dir = Path(self.scraper.base_dir)
        term_dir = base_dir / f"kadencja_{term:02d}" / "poslowie"

        if not term_dir.exists():
            print("⚠️  Brak danych do testowania - uruchom najpierw scraper")
            return True

        # Sprawdź plik listy posłów
        mps_list_file = term_dir / "lista_poslow.json"
        if mps_list_file.exists():
            try:
                with open(mps_list_file, 'r', encoding='utf-8') as f:
                    mps_data = json.load(f)
                print(f"✅ lista_poslow.json: {len(mps_data)} posłów")
            except Exception as e:
                print(f"❌ Błąd odczytu lista_poslow.json: {e}")
                return False

        # Sprawdź pliki klubów
        clubs_dir = term_dir / "kluby"
        if clubs_dir.exists():
            club_files = list(clubs_dir.glob("klub_*.json"))
            logo_files = list(clubs_dir.glob("logo_*"))
            print(f"✅ Pliki klubów: {len(club_files)} JSON, {len(logo_files)} logo")

            # Test losowego pliku klubu
            if club_files:
                try:
                    with open(club_files[0], 'r', encoding='utf-8') as f:
                        club_data = json.load(f)
                    print(f"✅ Test integralności pliku klubu: OK")
                except Exception as e:
                    print(f"❌ Błąd odczytu pliku klubu: {e}")
                    return False

        # Sprawdź pliki posłów
        mp_files = list(term_dir.glob("posel_*.json"))
        print(f"📄 Pliki posłów: {len(mp_files)}")

        if mp_files:
            # Test losowego pliku posła
            try:
                with open(mp_files[0], 'r', encoding='utf-8') as f:
                    mp_data = json.load(f)

                required_fields = ['_metadata', 'id', 'firstName', 'lastName']
                missing_fields = [field for field in required_fields
                                  if field not in mp_data]

                if missing_fields:
                    print(f"⚠️  Brakujące pola w pliku posła: {missing_fields}")
                else:
                    print(f"✅ Test integralności pliku posła: OK")

            except Exception as e:
                print(f"❌ Błąd odczytu pliku posła: {e}")
                return False

        return True

    def run_all_tests(self, term: int = DEFAULT_TERM):
        """Uruchomienie wszystkich testów"""
        print("🚀 ROZPOCZYNANIE PEŁNEGO TESTU MP SCRAPER")
        print(f"Kadencja testowa: {term}")

        # Lista testów
        tests = [
            ("Połączenie z API", self.test_api_connection),
            ("API Klubów", self.test_clubs_api, term),
            ("API Posłów", self.test_mps_api, term),
            ("Podsumowanie Posłów", self.test_scraper_summary, term),
            ("Scraper - Tylko Kluby", self.test_scraper_clubs_only, term),
            ("Scraper - Konkretny Poseł", self.test_scraper_specific_mp, term),
            ("Struktura Plików", self.test_file_structure, term),
            ("Integralność Danych", self.test_data_integrity, term),
        ]

        # Uruchom wszystkie testy
        for test_info in tests:
            test_name = test_info[0]
            test_func = test_info[1]
            args = test_info[2:] if len(test_info) > 2 else []

            self.run_test(test_name, test_func, *args)

        # Podsumowanie
        self.print_test_summary()

    def print_test_summary(self):
        """Wydrukowanie podsumowania testów"""
        print(f"\n{'=' * 80}")
        print("📋 PODSUMOWANIE TESTÓW")
        print(f"{'=' * 80}")

        passed = sum(1 for r in self.test_results if r['status'] == 'PASSED')
        failed = sum(1 for r in self.test_results if r['status'] == 'FAILED')
        errors = sum(1 for r in self.test_results if r['status'] == 'ERROR')
        total = len(self.test_results)

        print(f"Łącznie testów: {total}")
        print(f"✅ Zaliczone: {passed}")
        print(f"❌ Nieudane: {failed}")
        print(f"💥 Błędy: {errors}")

        total_time = sum(r['duration'] for r in self.test_results)
        print(f"⏱️  Łączny czas: {total_time:.2f}s")

        if failed > 0 or errors > 0:
            print(f"\n⚠️  PROBLEMY WYKRYTE:")
            for result in self.test_results:
                if result['status'] in ['FAILED', 'ERROR']:
                    status_icon = "💥" if result['status'] == 'ERROR' else "❌"
                    print(f"   {status_icon} {result['test']}")
                    if 'error' in result:
                        print(f"      Błąd: {result['error']}")

        print(f"\n{'=' * 80}")

        if passed == total:
            print("🎉 WSZYSTKIE TESTY ZALICZONE!")
        else:
            print(f"⚠️  {total - passed} testów wymaga uwagi")


def main():
    """Główna funkcja testowa"""
    import argparse

    parser = argparse.ArgumentParser(description="Tester MP Scraper")
    parser.add_argument('-t', '--term', type=int, default=DEFAULT_TERM,
                        help=f'Kadencja do testowania (domyślnie: {DEFAULT_TERM})')
    parser.add_argument('--test', choices=['api', 'clubs', 'mps', 'scraper', 'files', 'integrity'],
                        help='Uruchom konkretny test')
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='Szczegółowe logi')

    args = parser.parse_args()

    # Konfiguruj logowanie
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    setup_test_logging()

    tester = MPScraperTester()

    if args.test:
        # Uruchom konkretny test
        test_map = {
            'api': ("Połączenie z API", tester.test_api_connection),
            'clubs': ("API Klubów", tester.test_clubs_api, args.term),
            'mps': ("API Posłów", tester.test_mps_api, args.term),
            'scraper': ("Scraper Test", tester.test_scraper_clubs_only, args.term),
            'files': ("Struktura Plików", tester.test_file_structure, args.term),
            'integrity': ("Integralność Danych", tester.test_data_integrity, args.term),
        }

        if args.test in test_map:
            test_info = test_map[args.test]
            test_name = test_info[0]
            test_func = test_info[1]
            test_args = test_info[2:] if len(test_info) > 2 else []

            tester.run_test(test_name, test_func, *test_args)
        else:
            print(f"Nieznany test: {args.test}")
            sys.exit(1)
    else:
        # Uruchom wszystkie testy
        tester.run_all_tests(args.term)


if __name__ == "__main__":
    main()
