#!/usr/bin/env python3
"""
SejmBot Scheduler - Harmonogram uruchamiania bota
Uruchamia SejmBot w regularnych odstępach czasu
"""

import schedule
import logging
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

# Import głównego bota
try:
    from sejmbot import SejmBotConfig, SejmBot

    DIRECT_IMPORT = True
except ImportError:
    DIRECT_IMPORT = False


class SejmBotScheduler:
    """Scheduler dla SejmBot"""

    def __init__(self):
        self.logs_dir = Path("logs")
        self.logs_dir.mkdir(exist_ok=True)

        # Konfiguracja logowania
        log_file = self.logs_dir / f"scheduler_{datetime.now().strftime('%Y%m%d')}.log"
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file, encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)

    def run_bot_direct(self):
        """Uruchamia bota bezpośrednio (import)"""
        try:
            self.logger.info("🚀 Uruchamianie SejmBot (bezpośrednio)")

            config = SejmBotConfig()
            bot = SejmBot(config)
            processed = bot.run()

            self.logger.info(f"✅ Bot zakończył pracę. Przetworzono: {processed} sesji")

        except Exception as e:
            self.logger.error(f"❌ Błąd uruchomienia bota: {e}")

    def run_bot_subprocess(self):
        """Uruchamia bota jako subprocess"""
        try:
            self.logger.info("🚀 Uruchamianie SejmBot (subprocess)")

            result = subprocess.run(
                [sys.executable, "sejmbot.py"],
                capture_output=True,
                text=True,
                cwd=Path.cwd()
            )

            if result.returncode == 0:
                self.logger.info("✅ Bot zakończył pracę pomyślnie")
                if result.stdout:
                    self.logger.info(f"Stdout: {result.stdout}")
            else:
                self.logger.error(f"❌ Bot zakończył się błędem: {result.returncode}")
                if result.stderr:
                    self.logger.error(f"Stderr: {result.stderr}")

        except Exception as e:
            self.logger.error(f"❌ Błąd uruchomienia subprocess: {e}")

    def run_bot(self):
        """Główna funkcja uruchamiania bota"""
        if DIRECT_IMPORT:
            self.run_bot_direct()
        else:
            self.run_bot_subprocess()

    def setup_schedule(self):
        """Konfiguruje harmonogram uruchamiania"""

        # Uruchamiaj co 4 godziny w dni robocze
        schedule.every(4).hours.do(self.run_bot).tag('regular')

        # Uruchamiaj codziennie o 8:00
        schedule.every().day.at("08:00").do(self.run_bot).tag('daily')

        # Uruchamiaj w dni robocze o 14:00 (podczas sesji)
        schedule.every().monday.at("14:00").do(self.run_bot).tag('session')
        schedule.every().tuesday.at("14:00").do(self.run_bot).tag('session')
        schedule.every().wednesday.at("14:00").do(self.run_bot).tag('session')
        schedule.every().thursday.at("14:00").do(self.run_bot).tag('session')
        schedule.every().friday.at("14:00").do(self.run_bot).tag('session')

        self.logger.info("📅 Skonfigurowano harmonogram:")
        for job in schedule.get_jobs():
            self.logger.info(f"   - {job}")

    def run_scheduler(self):
        """Główna pętla schedulera"""
        self.logger.info("🕐 Uruchomiono SejmBot Scheduler")
        self.setup_schedule()

        # Pierwsze uruchomienie od razu
        self.logger.info("🎬 Pierwsze uruchomienie bota...")
        self.run_bot()

        # Główna pętla
        try:
            while True:
                schedule.run_pending()
                time.sleep(60)  # Sprawdzaj co minutę
        except KeyboardInterrupt:
            self.logger.info("⏹️  Scheduler zatrzymany przez użytkownika")
        except Exception as e:
            self.logger.error(f"❌ Błąd krytyczny schedulera: {e}")


def main():
    """Punkt wejścia schedulera"""
    import argparse

    parser = argparse.ArgumentParser(description='SejmBot Scheduler')
    parser.add_argument('--once', action='store_true', help='Uruchom bota tylko raz')
    parser.add_argument('--schedule', action='store_true', help='Uruchom scheduler (domyślne)')
    args = parser.parse_args()

    scheduler = SejmBotScheduler()

    if args.once:
        print("🚀 Uruchamianie SejmBot (jednorazowo)")
        scheduler.run_bot()
    else:
        print("📅 Uruchamianie SejmBot Scheduler")
        scheduler.run_scheduler()


if __name__ == "__main__":
    main()
