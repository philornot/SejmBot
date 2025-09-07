#!/usr/bin/env python3
# scheduler.py
"""
Automatyczny scheduler do pobierania najnowszych transkryptów Sejmu RP

Ten moduł monitoruje API Sejmu i automatycznie pobiera nowe transkrypty
gdy tylko staną się dostępne. Zmodyfikowany dla nowego workflow bez PDFów.
"""

import argparse
import json
import logging
import sys
import time
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Dict, List

import schedule

from config import DEFAULT_TERM, LOGS_DIR, SCHEDULER_CONFIG
from scraper import SejmScraper
from sejm_api import SejmAPI


class SejmScheduler:
    """Scheduler do automatycznego pobierania transkryptów"""

    def __init__(self, term: int = DEFAULT_TERM):
        self.term = term

        # Konfiguracja logowania
        self._setup_logging()

        self.api = SejmAPI()
        self.scraper = SejmScraper()
        self.state_file = Path("scheduler_state.json")
        self.last_check = None

        # Załaduj konfigurację
        self.config = SCHEDULER_CONFIG

        # Stan schedulera
        self.state = self._load_state()

        self.logger.info(f"Zainicjalizowano scheduler dla kadencji {term}")
        self.logger.info(f"Konfiguracja: interval={self.config['check_interval_minutes']}min, "
                         f"max_age={self.config['max_proceeding_age_days']}dni, "
                         f"notifications={self.config['enable_notifications']}")

    def _setup_logging(self):
        """Konfiguruje logowanie dla schedulera"""
        log_file = Path(LOGS_DIR) / f"scheduler_{self.term}.log"

        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file, encoding='utf-8'),
                logging.StreamHandler(sys.stdout)
            ]
        )

        self.logger = logging.getLogger(__name__)

    def _load_state(self) -> Dict:
        """Ładuje zapisany stan schedulera"""
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r', encoding='utf-8') as f:
                    state = json.load(f)
                    self.logger.info(f"Załadowano stan schedulera: {len(state.get('processed_dates', {}))} dat w cache")
                    return state
            except Exception as e:
                self.logger.warning(f"Nie można załadować stanu schedulera: {e}")

        return {
            'processed_dates': {},  # {proceeding_id: [lista dat]}
            'last_check': None,
            'current_proceedings': [],  # aktualne posiedzenia
            'term': self.term
        }

    def _save_state(self):
        """Zapisuje stan schedulera"""
        try:
            self.state['last_check'] = datetime.now().isoformat()
            with open(self.state_file, 'w', encoding='utf-8') as f:
                json.dump(self.state, f, ensure_ascii=False, indent=2)
            self.logger.debug("Zapisano stan schedulera")
        except Exception as e:
            self.logger.error(f"Błąd zapisywania stanu: {e}")

    def _get_current_proceedings(self) -> List[Dict]:
        """Pobiera listę aktualnych posiedzeń"""
        try:
            proceedings = self.api.get_proceedings(self.term)
            if not proceedings:
                return []

            # Filtruj unikalne posiedzenia (podobnie jak w scraper.py)
            seen_numbers = set()
            unique_proceedings = []

            for proc in proceedings:
                number = proc.get('number')
                if number and number not in seen_numbers:
                    seen_numbers.add(number)
                    unique_proceedings.append(proc)

            return unique_proceedings

        except Exception as e:
            self.logger.error(f"Błąd pobierania listy posiedzeń: {e}")
            return []

    def _is_proceeding_current(self, proceeding: Dict) -> bool:
        """Sprawdza czy posiedzenie jest obecnie aktywne lub zakończyło się niedawno"""
        dates = proceeding.get('dates', [])
        if not dates:
            return False

        today = date.today()
        max_age_days = self.config['max_proceeding_age_days']

        # Sprawdź czy posiedzenie jest oznaczone jako current
        if proceeding.get('current', False):
            return True

        # Sprawdź czy któraś z dat jest w zakresie
        for date_str in dates:
            try:
                proc_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                days_diff = (today - proc_date).days

                # Posiedzenie jest aktualne jeśli:
                # - jest dzisiaj, jutro lub w przyszłości (days_diff <= 0)
                # - zakończyło się nie więcej niż max_age_days temu
                if -1 <= days_diff <= max_age_days:
                    return True

            except ValueError:
                continue

        return False

    def _get_new_transcript_dates(self, proceeding_id: int, dates: List[str]) -> List[str]:
        """
        Zwraca listę dat dla których nie mamy jeszcze transkryptów

        Args:
            proceeding_id: ID posiedzenia
            dates: wszystkie daty posiedzenia

        Returns:
            Lista nowych dat do pobrania
        """
        processed_dates = set(self.state['processed_dates'].get(str(proceeding_id), []))
        today = date.today()

        new_dates = []
        for date_str in dates:
            try:
                proc_date = datetime.strptime(date_str, '%Y-%m-%d').date()

                # Pobieraj tylko daty które:
                # - nie zostały jeszcze przetworzone
                # - są z przeszłości lub dzisiaj (transkrypty są dostępne po zakończeniu dnia)
                if date_str not in processed_dates and proc_date <= today:
                    new_dates.append(date_str)

            except ValueError:
                self.logger.warning(f"Nieprawidłowy format daty: {date_str}")
                continue

        return new_dates

    def _mark_date_processed(self, proceeding_id: int, date_str: str):
        """Oznacza datę jako przetworzoną"""
        proc_id_str = str(proceeding_id)
        if proc_id_str not in self.state['processed_dates']:
            self.state['processed_dates'][proc_id_str] = []

        if date_str not in self.state['processed_dates'][proc_id_str]:
            self.state['processed_dates'][proc_id_str].append(date_str)
            self.logger.debug(f"Oznaczono jako przetworzone: posiedzenie {proceeding_id}, data {date_str}")

    def check_for_new_transcripts(self):
        """Główna metoda sprawdzająca nowe transkrypty"""
        self.logger.info("=== SPRAWDZANIE NOWYCH TRANSKRYPTÓW ===")

        try:
            # Pobierz listę posiedzeń
            proceedings = self._get_current_proceedings()
            if not proceedings:
                self.logger.warning("Brak posiedzeń do sprawdzenia")
                return

            current_proceedings = [p for p in proceedings if self._is_proceeding_current(p)]
            self.logger.info(f"Znaleziono {len(current_proceedings)} aktualnych posiedzeń do sprawdzenia")

            new_downloads = 0
            new_proceedings = []  # Lista nowych posiedzeń dla powiadomienia

            for proceeding in current_proceedings:
                proceeding_id = proceeding.get('number')
                dates = proceeding.get('dates', [])

                if not proceeding_id or not dates:
                    continue

                self.logger.info(f"Sprawdzanie posiedzenia {proceeding_id}")

                # Sprawdź które daty wymagają pobrania
                new_dates = self._get_new_transcript_dates(proceeding_id, dates)

                if not new_dates:
                    self.logger.debug(f"Brak nowych dat dla posiedzenia {proceeding_id}")
                    continue

                self.logger.info(f"Posiedzenie {proceeding_id}: znaleziono {len(new_dates)} nowych dat: {new_dates}")

                # Pobierz transkrypty dla nowych dat
                proceeding_downloads = 0
                for date_str in new_dates:
                    if self._download_transcript_for_date(proceeding_id, date_str, proceeding):
                        new_downloads += 1
                        proceeding_downloads += 1
                        self._mark_date_processed(proceeding_id, date_str)

                # Dodaj do listy nowych posiedzeń jeśli coś pobrano
                if proceeding_downloads > 0:
                    new_proceedings.append({
                        'id': proceeding_id,
                        'dates': new_dates[:proceeding_downloads],  # Tylko te które się udało pobrać
                        'title': proceeding.get('title', f'Posiedzenie {proceeding_id}')
                    })

            # Raportuj wyniki
            if new_downloads > 0:
                self.logger.info(f"Pobrano {new_downloads} nowych transkryptów")

                # Wyślij powiadomienie
                if new_proceedings:
                    message = self._create_notification_message(new_downloads, new_proceedings)
                    self._send_notification(message)
            else:
                self.logger.info("Brak nowych transkryptów do pobrania")

            # Zapisz stan
            self._save_state()

        except Exception as e:
            self.logger.error(f"Błąd podczas sprawdzania transkryptów: {e}")

            # Powiadomienie o błędzie
            if self.config['enable_notifications']:
                self._send_notification(f"Błąd schedulera kadencji {self.term}: {e}")

    def _download_transcript_for_date(self, proceeding_id: int, date_str: str, proceeding: Dict) -> bool:
        """
        Pobiera transkrypt dla konkretnej daty z retry logic
        Zmodyfikowany dla nowego workflow - tylko wypowiedzi

        Returns:
            True jeśli pobrano pomyślnie
        """
        max_retries = 3
        base_delay = 5

        for attempt in range(max_retries):
            try:
                self.logger.info(
                    f"Pobieranie transkryptu: posiedzenie {proceeding_id}, data {date_str} (próba {attempt + 1}/{max_retries})")

                # Pobierz szczegóły posiedzenia, jeśli potrzebne
                detailed_info = self.api.get_proceeding_info(self.term, proceeding_id)
                if not detailed_info:
                    detailed_info = proceeding

                # Zapisz informacje o posiedzeniu (jeśli jeszcze nie istnieją)
                self.scraper.file_manager.save_proceeding_info(self.term, proceeding_id, detailed_info)

                success = False

                # Pobierz listę wypowiedzi - główny cel schedulera
                try:
                    statements = self.api.get_transcripts_list(self.term, proceeding_id, date_str)
                    if statements and statements.get('statements'):
                        # Użyj nowego workflow do przetworzenia dnia posiedzenia
                        self.scraper._process_proceeding_day(
                            self.term,
                            proceeding_id,
                            date_str,
                            detailed_info,
                            fetch_full_statements=True  # Pobierz pełne treści wypowiedzi
                        )

                        statement_count = len(statements.get('statements', []))
                        self.logger.info(f"Pomyślnie pobrano i zapisano {statement_count} wypowiedzi dla {date_str}")
                        success = True
                    else:
                        self.logger.debug(f"Brak wypowiedzi dla {date_str}")

                except Exception as e:
                    if "404" not in str(e):
                        # Sprawdź czy to błąd serwera (5xx)
                        if any(status in str(e) for status in ["500", "502", "503", "504"]):
                            raise  # Podnieś wyjątek żeby uruchomić retry
                        else:
                            self.logger.error(f"Błąd pobierania wypowiedzi dla {date_str}: {e}")
                    else:
                        self.logger.debug(f"Wypowiedzi dla {date_str} jeszcze niedostępne (404)")

                # Jeśli dotarliśmy tutaj bez wyjątku, zakończ pomyślnie
                return success

            except Exception as e:
                # Sprawdź czy to błąd serwera, który warto powtórzyć
                server_error = any(status in str(e) for status in ["500", "502", "503", "504", "timeout", "connection"])

                if server_error and attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt)  # Exponential backoff
                    self.logger.warning(
                        f"Błąd serwera, ponowienie za {delay}s (próba {attempt + 1}/{max_retries}): {e}")
                    time.sleep(delay)
                    continue  # Spróbuj ponownie
                else:
                    # Ostatnia próba lub błąd nie wymagający powtórzenia
                    self.logger.error(
                        f"Błąd pobierania transkryptu dla {date_str} (próba {attempt + 1}/{max_retries}): {e}")
                    return False

        # Jeśli wyczerpaliśmy wszystkie próby
        self.logger.error(f"Wyczerpano wszystkie próby pobierania transkryptu dla {date_str}")
        return False

    def _send_notification(self, message: str):
        """Wysyła powiadomienie o nowych transkryptach"""
        if not self.config['enable_notifications']:
            return

        webhook_url = self.config['notification_webhook']
        if not webhook_url:
            self.logger.debug("Brak skonfigurowanego webhook URL dla powiadomień")
            return

        try:
            import requests

            payload = {
                "text": message,
                "timestamp": datetime.now().isoformat(),
                "scheduler_term": self.term
            }

            response = requests.post(webhook_url, json=payload, timeout=10)
            response.raise_for_status()

            self.logger.info(f"Wysłano powiadomienie: {message}")

        except Exception as e:
            self.logger.warning(f"Nie udało się wysłać powiadomienia: {e}")

    def _create_notification_message(self, total_downloads: int, new_proceedings: List[Dict]) -> str:
        """Tworzy wiadomość powiadomienia"""
        message = f"Nowe stenogramy z Sejmu RP (kadencja {self.term})\n\n"
        message += f"Pobrano łącznie: {total_downloads} transkryptów\n"

        for proc in new_proceedings:
            dates_str = ", ".join(proc['dates'])
            title = proc['title'][:50] + "..." if len(proc['title']) > 50 else proc['title']
            message += f"• Posiedzenie {proc['id']}: {dates_str}\n  {title}\n"

        message += f"\nCzas: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        return message

    def run_continuous(self, check_interval_minutes: int = None):
        """
        Uruchamia scheduler w trybie ciągłym

        Args:
            check_interval_minutes: interwał sprawdzania (nadpisuje konfigurację)
        """
        if check_interval_minutes is None:
            check_interval_minutes = self.config['check_interval_minutes']

        self.logger.info(f"Uruchomiono scheduler w trybie ciągłym (sprawdzanie co {check_interval_minutes} min)")

        # Zaplanuj zadanie
        schedule.every(check_interval_minutes).minutes.do(self.check_for_new_transcripts)

        # Wykonaj pierwsze sprawdzenie od razu
        self.check_for_new_transcripts()

        # Pętla główna
        try:
            while True:
                schedule.run_pending()
                time.sleep(60)  # sprawdzaj co minutę czy jest coś do zrobienia

        except KeyboardInterrupt:
            self.logger.info("Scheduler zatrzymany przez użytkownika (Ctrl+C)")
        except Exception as e:
            self.logger.error(f"Nieoczekiwany błąd schedulera: {e}")

            # Powiadomienie o krytycznym błędzie
            if self.config['enable_notifications']:
                self._send_notification(f"Krytyczny błąd schedulera kadencji {self.term}: {e}")

    def run_once(self):
        """Uruchamia pojedyncze sprawdzenie"""
        self.logger.info("Uruchamiam pojedyncze sprawdzenie transkryptów")
        self.check_for_new_transcripts()

    def cleanup_old_state(self, days_to_keep: int = 30):
        """
        Czyści stary stan z dat starszych niż podana liczba dni

        Args:
            days_to_keep: ile dni wstecz zachować w stanie
        """
        cutoff_date = date.today() - timedelta(days=days_to_keep)

        cleaned_count = 0
        for proc_id, dates in list(self.state['processed_dates'].items()):
            filtered_dates = []
            for date_str in dates:
                try:
                    proc_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                    if proc_date >= cutoff_date:
                        filtered_dates.append(date_str)
                    else:
                        cleaned_count += 1
                except ValueError:
                    # Zachowaj daty z nieprawidłowym formatem
                    filtered_dates.append(date_str)

            self.state['processed_dates'][proc_id] = filtered_dates

        if cleaned_count > 0:
            self.logger.info(f"Usunięto {cleaned_count} starych wpisów ze stanu")
            self._save_state()

    def get_status(self) -> Dict:
        """Zwraca status schedulera"""
        total_dates = sum(len(dates) for dates in self.state['processed_dates'].values())

        return {
            'term': self.term,
            'last_check': self.state.get('last_check'),
            'processed_proceedings': len(self.state['processed_dates']),
            'total_processed_dates': total_dates,
            'state_file': str(self.state_file),
            'state_file_exists': self.state_file.exists()
        }

    def get_health_status(self) -> Dict:
        """Zwraca status zdrowia schedulera"""
        now = datetime.now()
        last_check = self.state.get('last_check')

        if last_check:
            try:
                last_check_dt = datetime.fromisoformat(last_check)
                time_since_check = (now - last_check_dt).total_seconds() / 3600  # godziny

                expected_interval = self.config['check_interval_minutes'] / 60  # zamień na godziny
                health = "healthy" if time_since_check < (expected_interval * 2) else "stale"
            except:
                health = "unknown"
                time_since_check = None
        else:
            health = "unknown"
            time_since_check = None

        total_dates = sum(len(dates) for dates in self.state['processed_dates'].values())

        return {
            'status': health,
            'term': self.term,
            'last_check': last_check,
            'hours_since_check': round(time_since_check, 2) if time_since_check else None,
            'processed_proceedings': len(self.state['processed_dates']),
            'total_processed_dates': total_dates,
            'config': {
                'check_interval_minutes': self.config['check_interval_minutes'],
                'max_proceeding_age_days': self.config['max_proceeding_age_days'],
                'notifications_enabled': self.config['enable_notifications']
            }
        }


def main():
    """Główna funkcja programu"""
    parser = argparse.ArgumentParser(
        description="SejmScheduler - automatyczne pobieranie nowych transkryptów",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Przykłady użycia:
  %(prog)s --once                       # jednorazowe sprawdzenie
  %(prog)s --continuous                 # ciągły tryb (domyślnie co 30 min)
  %(prog)s --continuous --interval 15   # ciągły tryb co 15 min
  %(prog)s --status                     # pokaż status schedulera
  %(prog)s --cleanup                    # wyczyść stary stan
        """
    )

    parser.add_argument(
        '-t', '--term',
        type=int,
        default=DEFAULT_TERM,
        help=f'Numer kadencji (domyślnie: {DEFAULT_TERM})'
    )

    parser.add_argument(
        '--once',
        action='store_true',
        help='Wykonaj jednorazowe sprawdzenie i zakończ'
    )

    parser.add_argument(
        '--continuous',
        action='store_true',
        help='Uruchom w trybie ciągłym'
    )

    parser.add_argument(
        '--interval',
        type=int,
        default=30,
        help='Interwał sprawdzania w minutach (tylko dla --continuous, domyślnie: 30)'
    )

    parser.add_argument(
        '--status',
        action='store_true',
        help='Wyświetl status schedulera i zakończ'
    )

    parser.add_argument(
        '--cleanup',
        action='store_true',
        help='Wyczyść stary stan (starszy niż 30 dni)'
    )

    args = parser.parse_args()

    # Sprawdź czy podano jakąś akcję
    if not any([args.once, args.continuous, args.status, args.cleanup]):
        print("Błąd: Musisz podać jedną z akcji: --once, --continuous, --status, lub --cleanup")
        parser.print_help()
        sys.exit(1)

    # Utwórz scheduler
    scheduler = SejmScheduler(args.term)

    try:
        if args.status:
            status = scheduler.get_status()
            print(f"\nSTATUS SCHEDULERA KADENCJI {status['term']}")
            print("=" * 50)
            print(f"Ostatnie sprawdzenie: {status['last_check'] or 'Nigdy'}")
            print(f"Przetworzone posiedzenia: {status['processed_proceedings']}")
            print(f"Łączna liczba przetworzonych dat: {status['total_processed_dates']}")
            print(f"Plik stanu: {status['state_file']} {'✅' if status['state_file_exists'] else '❌'}")

        elif args.cleanup:
            print("Czyszczenie starego stanu...")
            scheduler.cleanup_old_state()
            print("Zakończono czyszczenie")

        elif args.once:
            print("Uruchamiam jednorazowe sprawdzenie...")
            scheduler.run_once()
            print("Sprawdzenie zakończone")

        elif args.continuous:
            if args.interval < 1:
                print("Błąd: Interwał musi być co najmniej 1 minuta")
                sys.exit(1)

            print(f"Uruchamiam scheduler w trybie ciągłym (co {args.interval} min)...")
            print("Naciśnij Ctrl+C aby zatrzymać")
            scheduler.run_continuous(args.interval)

    except KeyboardInterrupt:
        print("\nScheduler zatrzymany przez użytkownika")
    except Exception as e:
        print(f"\nNieoczekiwany błąd: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
