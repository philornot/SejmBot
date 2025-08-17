#!/usr/bin/env python3
"""
SejmBot - main.py
Główny moduł orkiestrujący pobieranie i przetwarzanie transkryptów Sejmu RP
"""

import argparse
import sys
import time
from datetime import datetime
from pathlib import Path

from SejmBotScraper.config import SejmBotConfig
from SejmBotScraper.downloader import FileDownloader
from SejmBotScraper.models import SejmSession, ProcessingStats
from SejmBotScraper.parsers import ParsingManager
from SejmBotScraper.session_finder import SessionFinder
from SejmBotScraper.storage import SessionStorage, ProcessedSessionsTracker, IndexManager

# Dodaj aktualny katalog do PYTHONPATH
sys.path.append(str(Path(__file__).parent))


class SejmBot:
    """
    Główna klasa bota do pobierania transkryptów Sejmu RP
    Orkiestruje wszystkie komponenty systemu
    """

    def __init__(self):
        self.config = SejmBotConfig()
        self.logger = self.config.logger

        # Inicjalizacja komponentów
        self.session_storage = SessionStorage(self.config, self.logger)
        self.processed_tracker = ProcessedSessionsTracker(self.config, self.logger)
        self.index_manager = IndexManager(self.config, self.logger)
        self.session_finder = SessionFinder(self.config, self.logger)
        self.downloader = FileDownloader(self.config, self.logger)
        self.parsing_manager = ParsingManager(self.logger)

        # Statystyki przetwarzania
        self.stats = ProcessingStats()

    def run(self, test_mode: bool = False) -> int:
        """
        Główna pętla bota - pobiera i przetwarza posiedzenia Sejmu RP

        Args:
            test_mode: Tryb testowy - ogranicza przetwarzanie

        Returns:
            int: Liczba nowo przetworzonych posiedzeń
        """
        try:
            self._print_banner()

            # KROK 1: Sprawdź zależności
            if not self._check_dependencies():
                return 0

            # KROK 2: Cleanup uszkodzonych plików
            self._cleanup_broken_files()

            # KROK 3: Znajdź wszystkie posiedzenia do przetworzenia
            session_links = self._find_all_sessions()
            if not session_links:
                self.logger.warning("❌ Nie znaleziono żadnych posiedzeń do przetworzenia")
                return 0

            # KROK 4: Przetwarzaj posiedzenia
            return self._process_all_sessions(session_links, test_mode)

        except KeyboardInterrupt:
            print(f"\n⏹️  Przerwano przez użytkownika")
            return self.stats.processed_new

        except Exception as e:
            self.logger.error(f"❌ Błąd krytyczny: {e}")
            import traceback
            self.logger.debug(f"Szczegóły błędu:\n{traceback.format_exc()}")
            return 0

        finally:
            # Zawsze wyczyść zasoby
            self._cleanup_resources()

    def _print_banner(self):
        """Wypisuje banner aplikacji"""
        print("🏛️  SejmBot v2.1 - Parser transkryptów posiedzeń Sejmu RP")
        print("=" * 60)
        print(f"🎯 Aktywne kadencje: {self.config.active_kadencje}")

        for kad_nr in self.config.active_kadencje:
            kad_info = self.config.kadencje.get(kad_nr, {})
            lata = kad_info.get('lata', [])
            if lata:
                print(f"📅 Kadencja {kad_nr}: {min(lata)}-{max(lata)}")

        stored_count = self.session_storage.get_stored_sessions_count()
        print(f"💾 Już zapisanych sesji: {stored_count}")
        print("=" * 60)
        self.logger.info("🚀 Uruchomiono SejmBot v2.1")

    def _check_dependencies(self) -> bool:
        """Sprawdza dostępność wymaganych bibliotek"""
        parsing_stats = self.parsing_manager.get_parsing_stats()
        missing = parsing_stats['missing_dependencies']

        if missing:
            print("⚠️  Brakujące biblioteki:")
            for dep in missing:
                print(f"   📦 {dep}")
            print("💡 Zainstaluj: pip install " + " ".join(missing))

            # W trybie produkcyjnym kontynuuj z ograniczoną funkcjonalnością
            self.logger.warning(f"Kontynuuję z ograniczoną funkcjonalnością - brak: {missing}")

        return True  # Zawsze kontynuuj - podstawowa funkcjonalność HTML zawsze działa

    def _cleanup_broken_files(self):
        """Czyści uszkodzone pliki z poprzednich wersji"""
        try:
            self.logger.info("🧹 Sprawdzam uszkodzone pliki...")
            broken_count = self.session_storage.cleanup_broken_sessions()

            if broken_count > 0:
                print(f"🧹 Wyczyszczono {broken_count} uszkodzonych plików z poprzednich wersji")
                self.logger.info(f"Wyczyszczono {broken_count} uszkodzonych plików")

        except Exception as e:
            self.logger.warning(f"Błąd podczas cleanup: {e}")

    def _find_all_sessions(self) -> list:
        """Znajduje wszystkie posiedzenia do przetworzenia"""
        try:
            self.logger.info("🔍 Rozpoczynam wyszukiwanie posiedzeń...")
            session_links = self.session_finder.find_all_sessions()

            self.stats.total_found = len(session_links)
            already_processed = sum(1 for s in session_links
                                    if self.processed_tracker.is_processed(s.get('id', '')))

            self.stats.skipped_existing = already_processed

            print(f"📊 Znaleziono {self.stats.total_found} dni posiedzeń")
            print(f"⏭️  Już przetworzonych: {already_processed}")
            print(f"🆕 Do przetworzenia: {self.stats.total_found - already_processed}")

            return session_links

        except Exception as e:
            self.logger.error(f"❌ Błąd podczas wyszukiwania posiedzeń: {e}")
            print(f"❌ Błąd krytyczny podczas wyszukiwania: {e}")
            return []

    def _process_all_sessions(self, session_links: list, test_mode: bool = False) -> int:
        """Przetwarza wszystkie znalezione posiedzenia"""
        # W trybie testowym ogranicz do kilku pierwszych
        if test_mode:
            session_links = session_links[:3]
            print(f"🧪 Tryb testowy - przetwarzam tylko {len(session_links)} posiedzeń")

        total_sessions = len(session_links)

        if total_sessions == 0:
            print("✅ Wszystkie posiedzenia już przetworzone")
            return 0

        print(f"⚙️  Rozpoczynam przetwarzanie {total_sessions} posiedzeń...")

        for i, session_data in enumerate(session_links, 1):
            try:
                session_id = session_data.get('id', '')

                # Sprawdź czy już przetworzona
                if self.processed_tracker.is_processed(session_id):
                    self.stats.skipped_existing += 1
                    self.logger.debug(f"⏭️  Posiedzenie {session_id} już przetworzone ({i}/{total_sessions})")
                    continue

                # Pokaż postęp
                title = session_data.get('title', 'Nieznany tytuł')[:80]
                print(f"📖 [{i}/{total_sessions}] Przetwarzam: {title}...")

                # Przetwórz posiedzenie
                session = self._process_single_session(session_data)

                if session:
                    self.stats.processed_new += 1
                    text_len = len(session.transcript_text) if session.transcript_text else 0
                    print(f"✅ [{i}/{total_sessions}] Sukces! Tekst: {text_len:,} znaków")

                    # Pokaż statystyki co 5 posiedzeń
                    if self.stats.processed_new % 5 == 0:
                        success_rate = self.stats.get_success_rate()
                        print(f"📈 Postęp: {self.stats.processed_new} przetworzonych, {success_rate:.1f}% sukces")
                else:
                    self.stats.failed += 1
                    print(f"❌ [{i}/{total_sessions}] Błąd przetwarzania")

                # Opóźnienie między posiedzeniami
                time.sleep(self.config.delay_between_requests)

            except KeyboardInterrupt:
                print(f"\n⏹️  Przerwano przez użytkownika na posiedzeniu {i}/{total_sessions}")
                break

            except Exception as e:
                self.stats.failed += 1
                title = session_data.get('title', 'unknown')
                self.logger.error(f"❌ Błąd przetwarzania posiedzenia {title}: {e}")
                print(f"❌ [{i}/{total_sessions}] Błąd: {str(e)[:60]}...")

        # Zakończ statystyki
        self.stats.finish()

        # Podsumowanie
        self._print_summary()

        # Aktualizuj globalne statystyki jeśli były nowe posiedzenia
        if self.stats.processed_new > 0:
            try:
                self.index_manager.save_global_stats()
                print("📊 Zaktualizowano globalne statystyki")
            except Exception as e:
                self.logger.warning(f"Błąd aktualizacji statystyk: {e}")

        return self.stats.processed_new

    def _process_single_session(self, session_data: dict) -> SejmSession:
        """Przetwarza pojedyncze posiedzenie"""
        session_id = session_data.get('id', '')
        transcript_url = session_data.get('url', '')

        if not transcript_url:
            self.logger.error(f"❌ Brak URL dla posiedzenia {session_id}")
            return None

        self.logger.info(f"🔄 Przetwarzam: {session_data.get('title', 'Bez tytułu')}")

        # Utwórz obiekt posiedzenia
        try:
            session = SejmSession(
                session_id=session_id,
                meeting_number=session_data.get('meeting_number', 0),
                day_letter=session_data.get('day_letter', ''),
                date=session_data.get('date', ''),
                title=session_data.get('title', ''),
                url=transcript_url,
                transcript_url=transcript_url,
                file_type=session_data.get('file_type', 'pdf'),
                scraped_at=datetime.now().isoformat(),
                kadencja=session_data.get('kadencja', 10)
            )
        except Exception as e:
            self.logger.error(f"❌ Błąd tworzenia obiektu sesji {session_id}: {e}")
            return None

        # Pobierz i przetwórz plik
        try:
            text_content, pdf_bytes = self._download_and_parse(transcript_url, session.file_type, session_id)

            if not text_content:
                self.logger.error(f"❌ Nie udało się wyciągnąć tekstu z {transcript_url}")
                self.stats.connection_errors += 1
                return None

            # Walidacja jakości tekstu
            if not self.parsing_manager.validate_text_quality(text_content, transcript_url):
                self.logger.warning(f"⚠️  Tekst nie przeszedł walidacji jakości dla {session_id}")
                # Kontynuuj mimo wszystko - może to być fałszywy alarm

            # Uzupełnij obiekt posiedzenia
            session.transcript_text = text_content
            import hashlib
            session.hash = hashlib.md5(text_content.encode()).hexdigest()

            # Zapisz posiedzenie
            if self.session_storage.save_session(session, pdf_bytes):
                self.processed_tracker.mark_processed(session_id)
                self.logger.info(f"✅ Pomyślnie zapisano posiedzenie {session_id}")
                return session
            else:
                self.logger.error(f"❌ Błąd zapisu posiedzenia {session_id}")
                return None

        except Exception as e:
            self.logger.error(f"❌ Błąd przetwarzania posiedzenia {session_id}: {e}")
            import traceback
            self.logger.debug(f"Szczegóły błędu:\n{traceback.format_exc()}")
            self.stats.connection_errors += 1
            return None

    def _download_and_parse(self, url: str, file_type: str, session_id: str) -> tuple:
        """Pobiera i parsuje plik"""
        try:
            self.logger.info(f"📥 Pobieranie pliku: {url}")

            # Pobierz plik
            response = self.downloader.download_file(url)
            if not response:
                self.logger.error(f"❌ Nie udało się pobrać pliku: {url}")
                return "", b""

            file_bytes = response.content
            if not file_bytes or len(file_bytes) < 100:
                self.logger.error(f"❌ Plik pusty lub za mały: {len(file_bytes)} bajtów")
                return "", b""

            # Wykryj rzeczywisty typ pliku i parsuj
            text_content, detected_type = self.parsing_manager.parse_file_content(
                file_bytes, url, file_type
            )

            if detected_type != file_type:
                self.logger.info(f"🔍 Wykryto inny typ pliku: {detected_type} zamiast {file_type}")

            if not text_content:
                self.logger.error(f"❌ Nie udało się wyciągnąć tekstu z pliku")
                return "", b""

            self.logger.info(f"✅ Pomyślnie wyciągnięto {len(text_content):,} znaków tekstu")

            # Zwróć tekst i oryginalne bajty (jeśli to PDF)
            if detected_type == 'pdf':
                return text_content, file_bytes
            else:
                return text_content, b""

        except Exception as e:
            self.logger.error(f"❌ Błąd pobierania/parsowania {url}: {e}")
            import traceback
            self.logger.debug(f"Szczegóły błędu:\n{traceback.format_exc()}")
            return "", b""

    def _print_summary(self):
        """Wypisuje podsumowanie działania bota"""
        print("\n" + "=" * 60)
        print("📋 PODSUMOWANIE PRZETWARZANIA")
        print("=" * 60)

        summary = self.stats.get_summary()
        print(summary)

        if self.stats.processed_new > 0:
            print(f"\n🎉 Pomyślnie przetworzono {self.stats.processed_new} nowych posiedzeń!")
        elif self.stats.total_found > 0:
            print(f"\n✅ Wszystkie posiedzenia już przetworzone")
        else:
            print(f"\n⚠️  Nie znaleziono posiedzeń do przetworzenia")

        # Pokaż statystyki globalne
        try:
            global_stats = self.index_manager.get_global_stats()
            print(f"\n📊 STATYSTYKI GLOBALNE:")
            print(f"   Łącznie sesji: {global_stats['total_sessions']}")
            print(f"   Łącznie znaków: {global_stats['total_characters']:,}")
            print(f"   Łącznie słów: {global_stats['total_words']:,}")
        except Exception as e:
            self.logger.debug(f"Błąd pobierania statystyk globalnych: {e}")

        print("=" * 60)

    def _cleanup_resources(self):
        """Czyści zasoby na koniec działania"""
        try:
            if hasattr(self.downloader, 'close'):
                self.downloader.close()
        except Exception as e:
            self.logger.debug(f"Błąd czyszczenia zasobów: {e}")

    def test_run(self) -> bool:
        """
        Uruchamia test podstawowej funkcjonalności bota

        Returns:
            bool: True jeśli test przeszedł pomyślnie
        """
        try:
            print("🧪 Uruchamiam test SejmBot...")

            # Test 1: Sprawdź konfigurację
            urls = self.config.get_stenogramy_urls()
            if not urls:
                print("❌ Brak URLi do sprawdzenia")
                return False
            print(f"✅ Konfiguracja OK - {len(urls)} URLi do sprawdzenia")

            # Test 2: Sprawdź połączenie sieciowe
            try:
                first_url = urls[0]
                response = self.downloader.download_file(first_url)
                if response and response.status_code == 200:
                    print("✅ Połączenie sieciowe OK")
                else:
                    print("❌ Problemy z połączeniem sieciowym")
                    return False
            except Exception as e:
                print(f"❌ Błąd połączenia: {e}")
                return False

            # Test 3: Sprawdź parsery
            parsing_stats = self.parsing_manager.get_parsing_stats()
            print(
                f"✅ Parsery: HTML=✅, PDF={'✅' if parsing_stats['pdf_support'] else '❌'}, DOCX={'✅' if parsing_stats['docx_support'] else '❌'}")

            # Test 4: Sprawdź zapisy
            try:
                test_dir = self.config.output_dir / "test"
                test_dir.mkdir(exist_ok=True)
                test_file = test_dir / "test.txt"
                test_file.write_text("test", encoding='utf-8')
                test_file.unlink()
                test_dir.rmdir()
                print("✅ Zapis plików OK")
            except Exception as e:
                print(f"❌ Problemy z zapisem: {e}")
                return False

            print("🎉 Wszystkie testy przeszły pomyślnie!")
            return True

        except Exception as e:
            print(f"❌ Błąd podczas testów: {e}")
            return False


def main():
    """Główna funkcja programu"""
    parser = argparse.ArgumentParser(
        description='SejmBot - Parser transkryptów posiedzeń Sejmu RP'
    )
    parser.add_argument(
        '--test',
        action='store_true',
        help='Uruchom w trybie testowym (tylko kilka posiedzeń)'
    )
    parser.add_argument(
        '--check',
        action='store_true',
        help='Sprawdź tylko czy bot działa poprawnie'
    )

    args = parser.parse_args()

    try:
        bot = SejmBot()

        if args.check:
            # Tryb sprawdzenia
            success = bot.test_run()
            sys.exit(0 if success else 1)
        else:
            # Normalny tryb działania
            processed_count = bot.run(test_mode=args.test)

            if processed_count > 0:
                print(f"\n✅ Zakończono pomyślnie - przetworzono {processed_count} posiedzeń")
                sys.exit(0)
            else:
                print(f"\n⚠️  Zakończono bez przetwarzania nowych posiedzeń")
                sys.exit(0)

    except KeyboardInterrupt:
        print("\n⏹️  Przerwano przez użytkownika")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Błąd krytyczny: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
