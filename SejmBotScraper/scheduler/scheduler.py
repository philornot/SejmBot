# scheduler/scheduler.py
"""
Automatyczny scheduler do pobierania najnowszych transkryptów Sejmu RP
Zintegrowany z nową modularną architekturą
"""

import json
import logging
import time
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Dict, List, Optional

import schedule

from ..api.client import SejmAPIInterface
from ..cache.manager import CacheInterface
from ..config.settings import get_settings
from ..scraping.scraper import SejmScraper

logger = logging.getLogger(__name__)


class SejmScheduler:
    """
    Scheduler do automatycznego pobierania transkryptów

    Zintegrowany z nową architekturą modularną:
    - Używa SejmScraper z interfejsami
    - Wykorzystuje CacheInterface
    - Konfiguracja przez settings
    """

    def __init__(self, term: Optional[int] = None, config_path: Optional[str] = None):
        """
        Inicjalizuje scheduler

        Args:
            term: numer kadencji (domyślnie z konfiguracji)
            config_path: ścieżka do pliku .env (opcjonalna)
        """
        # Załaduj konfigurację
        self.settings = get_settings(config_path)
        self.term = term or self.settings.get('default_term')

        # Inicjalizuj komponenty
        self.scraper = SejmScraper()
        self.cache = CacheInterface()
        self.api = SejmAPIInterface()

        # Stan schedulera
        self.state_file = Path("scheduler_state.json")
        self.state = self._load_state()

        # Migracja stanu do cache managera
        self._migrate_state_to_cache()

        logger.info(f"Zainicjalizowano scheduler dla kadencji {self.term}")
        logger.info(f"Konfiguracja: interval={self._get_check_interval()}min")

    def _get_check_interval(self) -> int:
        """Pobiera interval sprawdzania z konfiguracji"""
        return self.settings.get('scheduler.check_interval_minutes', 30)

    def _get_max_proceeding_age(self) -> int:
        """Pobiera maksymalny wiek posiedzenia z konfiguracji"""
        return self.settings.get('scheduler.max_proceeding_age_days', 7)

    def _is_notifications_enabled(self) -> bool:
        """Sprawdza czy powiadomienia są włączone"""
        return self.settings.get('scheduler.enable_notifications', False)

    def _get_notification_webhook(self) -> Optional[str]:
        """Pobiera URL webhook dla powiadomień"""
        return self.settings.get('scheduler.notification_webhook')

    def _load_state(self) -> Dict:
        """Ładuje zapisany stan schedulera"""
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r', encoding='utf-8') as f:
                    state = json.load(f)
                    logger.info(f"Załadowano stan schedulera: {len(state.get('processed_dates', {}))} dat w cache")
                    return state
            except Exception as e:
                logger.warning(f"Nie można załadować stanu schedulera: {e}")

        return {
            'processed_dates': {},
            'last_check': None,
            'current_proceedings': [],
            'term': self.term,
            'migrated_to_cache': False,
            'migration_date': None
        }

    def _save_state(self):
        """Zapisuje stan schedulera"""
        try:
            self.state['last_check'] = datetime.now().isoformat()
            with open(self.state_file, 'w', encoding='utf-8') as f:
                json.dump(self.state, f, ensure_ascii=False, indent=2)
            logger.debug("Zapisano stan schedulera")
        except Exception as e:
            logger.error(f"Błąd zapisywania stanu: {e}")

    def _migrate_state_to_cache(self):
        """Migruje stary stan schedulera do nowego cache managera"""
        if not self.state.get('processed_dates') or self.state.get('migrated_to_cache'):
            return

        logger.info("Migracja stanu schedulera do nowego cache managera...")

        migrated_count = 0
        for proc_id_str, dates in self.state['processed_dates'].items():
            try:
                proc_id = int(proc_id_str)
                for date_str in dates:
                    # Oznacz w cache jako przetworzone
                    self.cache.mark_proceeding_checked(self.term, proc_id, f"migrated_{date_str}")
                    migrated_count += 1
            except (ValueError, TypeError):
                continue

        self.state['migrated_to_cache'] = True
        self.state['migration_date'] = datetime.now().isoformat()
        self._save_state()

        logger.info(f"Zmigrowano {migrated_count} wpisów do nowego cache managera")

    def _get_current_proceedings(self) -> List[Dict]:
        """Pobiera listę aktualnych posiedzeń"""
        try:
            proceedings = self.api.get_proceedings(self.term)
            if not proceedings:
                return []

            # Filtruj unikalne posiedzenia
            seen_numbers = set()
            unique_proceedings = []

            for proc in proceedings:
                number = proc.get('number')
                if number and number not in seen_numbers:
                    seen_numbers.add(number)
                    unique_proceedings.append(proc)

            return unique_proceedings

        except Exception as e:
            logger.error(f"Błąd pobierania listy posiedzeń: {e}")
            return []

    def _is_proceeding_current(self, proceeding: Dict) -> bool:
        """Sprawdza czy posiedzenie jest obecnie aktywne lub zakończyło się niedawno"""
        dates = proceeding.get('dates', [])
        if not dates:
            return False

        today = date.today()
        max_age_days = self._get_max_proceeding_age()

        # Sprawdź czy posiedzenie jest oznaczone jako current
        if proceeding.get('current', False):
            return True

        # Sprawdź czy któraś z dat jest w zakresie
        for date_str in dates:
            try:
                proc_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                days_diff = (today - proc_date).days

                if -1 <= days_diff <= max_age_days:
                    return True

            except ValueError:
                continue

        return False

    def _get_new_transcript_dates(self, proceeding_id: int, dates: List[str]) -> List[str]:
        """Zwraca listę dat dla których nie mamy jeszcze transkryptów"""
        today = date.today()
        new_dates = []

        for date_str in dates:
            try:
                proc_date = datetime.strptime(date_str, '%Y-%m-%d').date()

                if proc_date <= today:
                    # Sprawdź w cache czy posiedzenie wymaga odświeżenia
                    if self.cache.should_refresh_proceeding(
                            self.term, proceeding_id, [date_str], force=False
                    ):
                        new_dates.append(date_str)

            except ValueError:
                logger.warning(f"Nieprawidłowy format daty: {date_str}")
                continue

        return new_dates

    def _mark_date_processed(self, proceeding_id: int, date_str: str):
        """Oznacza datę jako przetworzoną w cache managerze"""
        self.cache.mark_proceeding_checked(self.term, proceeding_id, f"processed_{date_str}")

        # Zachowaj również w starym systemie dla kompatybilności
        proc_id_str = str(proceeding_id)
        if proc_id_str not in self.state['processed_dates']:
            self.state['processed_dates'][proc_id_str] = []

        if date_str not in self.state['processed_dates'][proc_id_str]:
            self.state['processed_dates'][proc_id_str].append(date_str)
            logger.debug(f"Oznaczono jako przetworzone: posiedzenie {proceeding_id}, data {date_str}")

    def check_for_new_transcripts(self):
        """Główna metoda sprawdzająca nowe transkrypty"""
        logger.info("=== SPRAWDZANIE NOWYCH TRANSKRYPTÓW ===")

        try:
            # Wyczyść stare wpisy z cache na początku
            self.cache.cleanup_expired()

            # Pobierz listę posiedzeń
            proceedings = self._get_current_proceedings()
            if not proceedings:
                logger.warning("Brak posiedzeń do sprawdzenia")
                return

            current_proceedings = [p for p in proceedings if self._is_proceeding_current(p)]
            logger.info(f"Znaleziono {len(current_proceedings)} aktualnych posiedzeń do sprawdzenia")

            new_downloads = 0
            new_proceedings = []

            for proceeding in current_proceedings:
                proceeding_id = proceeding.get('number')
                dates = proceeding.get('dates', [])

                if not proceeding_id or not dates:
                    continue

                logger.info(f"Sprawdzanie posiedzenia {proceeding_id}")

                # Sprawdź które daty wymagają pobrania
                new_dates = self._get_new_transcript_dates(proceeding_id, dates)

                if not new_dates:
                    logger.debug(f"Brak nowych dat dla posiedzenia {proceeding_id}")
                    continue

                logger.info(f"Posiedzenie {proceeding_id}: znaleziono {len(new_dates)} nowych dat: {new_dates}")

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
                        'dates': new_dates[:proceeding_downloads],
                        'title': proceeding.get('title', f'Posiedzenie {proceeding_id}')
                    })

            # Raportuj wyniki
            if new_downloads > 0:
                logger.info(f"Pobrano {new_downloads} nowych transkryptów")

                # Wyślij powiadomienie
                if new_proceedings:
                    message = self._create_notification_message(new_downloads, new_proceedings)
                    self._send_notification(message)
            else:
                logger.info("Brak nowych transkryptów do pobrania")

            # Zapisz stan
            self._save_state()

        except Exception as e:
            logger.error(f"Błąd podczas sprawdzania transkryptów: {e}")

            # Powiadomienie o błędzie
            if self._is_notifications_enabled():
                self._send_notification(f"Błąd schedulera kadencji {self.term}: {e}")

    def _download_transcript_for_date(self, proceeding_id: int, date_str: str, proceeding: Dict) -> bool:
        """Pobiera transkrypt dla konkretnej daty"""
        max_retries = 3
        base_delay = 5

        for attempt in range(max_retries):
            try:
                logger.info(
                    f"Pobieranie transkryptu: posiedzenie {proceeding_id}, data {date_str} (próba {attempt + 1}/{max_retries})")

                # Użyj scrapera do pobrania dnia posiedzenia
                success = self.scraper.scrape_proceeding_date(
                    self.term,
                    proceeding_id,
                    date_str,
                    fetch_full_statements=True
                )

                if success:
                    logger.info(f"Pomyślnie pobrano transkrypt dla {date_str}")
                    return True
                else:
                    logger.warning(f"Nie udało się pobrać transkryptu dla {date_str}")

            except Exception as e:
                # Sprawdź czy to błąd serwera, który warto powtórzyć
                server_error = any(status in str(e) for status in ["500", "502", "503", "504", "timeout", "connection"])

                if server_error and attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt)  # Exponential backoff
                    logger.warning(
                        f"Błąd serwera, ponowienie za {delay}s (próba {attempt + 1}/{max_retries}): {e}")
                    time.sleep(delay)
                    continue
                else:
                    logger.error(
                        f"Błąd pobierania transkryptu dla {date_str} (próba {attempt + 1}/{max_retries}): {e}")
                    return False

        logger.error(f"Wyczerpano wszystkie próby pobierania transkryptu dla {date_str}")
        return False

    def _send_notification(self, message: str):
        """Wysyła powiadomienie o nowych transkryptach"""
        if not self._is_notifications_enabled():
            return

        webhook_url = self._get_notification_webhook()
        if not webhook_url:
            logger.debug("Brak skonfigurowanego webhook URL dla powiadomień")
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

            logger.info(f"Wysłano powiadomienie: {message}")

        except Exception as e:
            logger.warning(f"Nie udało się wysłać powiadomienia: {e}")

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

    def run_continuous(self, check_interval_minutes: Optional[int] = None):
        """Uruchamia scheduler w trybie ciągłym"""
        if check_interval_minutes is None:
            check_interval_minutes = self._get_check_interval()

        logger.info(f"Uruchomiono scheduler w trybie ciągłym (sprawdzanie co {check_interval_minutes} min)")

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
            logger.info("Scheduler zatrzymany przez użytkownika (Ctrl+C)")
        except Exception as e:
            logger.error(f"Nieoczekiwany błąd schedulera: {e}")

            # Powiadomienie o krytycznym błędzie
            if self._is_notifications_enabled():
                self._send_notification(f"Krytyczny błąd schedulera kadencji {self.term}: {e}")

    def run_once(self):
        """Uruchamia pojedyncze sprawdzenie"""
        logger.info("Uruchamiam pojedyncze sprawdzenie transkryptów")
        self.check_for_new_transcripts()

    def cleanup_old_state(self, days_to_keep: int = 30):
        """Czyści stary stan"""
        # Wyczyść cache manager
        self.cache.cleanup_expired()

        # Wyczyść stary stan schedulera
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
            logger.info(f"Usunięto {cleaned_count} starych wpisów ze stanu")
            self._save_state()

    def clear_cache(self):
        """Czyści cache schedulera"""
        self.cache.clear_all()
        logger.info("Wyczyszczono cache schedulera")

    def get_status(self) -> Dict:
        """Zwraca status schedulera"""
        total_dates = sum(len(dates) for dates in self.state['processed_dates'].values())
        cache_stats = self.cache.get_stats()

        return {
            'term': self.term,
            'last_check': self.state.get('last_check'),
            'processed_proceedings': len(self.state['processed_dates']),
            'total_processed_dates': total_dates,
            'state_file': str(self.state_file),
            'state_file_exists': self.state_file.exists(),
            'cache_stats': cache_stats,
            'migrated_to_cache': self.state.get('migrated_to_cache', False),
            'migration_date': self.state.get('migration_date'),
            'config': {
                'check_interval_minutes': self._get_check_interval(),
                'max_proceeding_age_days': self._get_max_proceeding_age(),
                'notifications_enabled': self._is_notifications_enabled()
            }
        }

    def get_health_status(self) -> Dict:
        """Zwraca status zdrowia schedulera"""
        now = datetime.now()
        last_check = self.state.get('last_check')

        if last_check:
            try:
                last_check_dt = datetime.fromisoformat(last_check)
                time_since_check = (now - last_check_dt).total_seconds() / 3600  # godziny

                expected_interval = self._get_check_interval() / 60  # zamień na godziny
                health = "healthy" if time_since_check < (expected_interval * 2) else "stale"
            except:
                health = "unknown"
                time_since_check = None
        else:
            health = "unknown"
            time_since_check = None

        total_dates = sum(len(dates) for dates in self.state['processed_dates'].values())
        cache_stats = self.cache.get_stats()

        return {
            'status': health,
            'term': self.term,
            'last_check': last_check,
            'hours_since_check': round(time_since_check, 2) if time_since_check else None,
            'processed_proceedings': len(self.state['processed_dates']),
            'total_processed_dates': total_dates,
            'config': {
                'check_interval_minutes': self._get_check_interval(),
                'max_proceeding_age_days': self._get_max_proceeding_age(),
                'notifications_enabled': self._is_notifications_enabled()
            },
            'cache_health': {
                'memory_entries': cache_stats.get('memory_entries', 0),
                'file_entries': cache_stats.get('file_entries', 0),
                'memory_hits': cache_stats.get('memory_hits', 0),
                'memory_misses': cache_stats.get('memory_misses', 0)
            }
        }

    def __repr__(self) -> str:
        """Reprezentacja string obiektu"""
        return f"SejmScheduler(term={self.term}, interval={self._get_check_interval()}min)"
