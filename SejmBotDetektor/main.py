"""
Główny skrypt (entry-point)
"""
import os
from pathlib import Path

from SejmBotDetektor.detectors.fragment_detector import FragmentDetector
from SejmBotDetektor.utils.logger import logger, Colors, LogLevel
from SejmBotDetektor.utils.output_manager import OutputManager


def main():
    """Główna funkcja programu"""

    # Konfiguracja
    pdf_path = "transkrypty" # ścieżka do folderu
    min_confidence = 0.3
    max_fragments_per_file = 20
    max_total_fragments = 100  # całkowity limit fragmentów
    context_before = 25
    context_after = 25
    debug_mode = True

    # Ustawiamy poziom logowania
    if debug_mode:
        logger.set_level(LogLevel.DEBUG)
    else:
        logger.set_level(LogLevel.INFO)

    try:
        # Nagłówek aplikacji
        logger.header("DETEKTOR ŚMIESZNYCH FRAGMENTÓW Z SEJMU")

        # Walidacja konfiguracji
        from SejmBotDetektor.config.keywords import KeywordsConfig
        issues = KeywordsConfig.validate_keywords()
        if issues:
            logger.warning("Znaleziono problemy w konfiguracji słów kluczowych:")
            for issue in issues:
                logger.list_item(issue, level=1)
            print()

        # Wyświetlanie konfiguracji
        logger.section("KONFIGURACJA")

        # Sprawdzamy czy podana ścieżka to folder czy plik
        path = Path(pdf_path)
        if path.is_dir():
            logger.keyvalue("Folder z PDFami", pdf_path, Colors.CYAN)
            logger.keyvalue("Max fragmentów na plik", str(max_fragments_per_file), Colors.BLUE)
            logger.keyvalue("Max fragmentów łącznie", str(max_total_fragments), Colors.BLUE)
        elif path.is_file():
            logger.keyvalue("Plik PDF", pdf_path, Colors.CYAN)
            logger.keyvalue("Max fragmentów", str(max_fragments_per_file), Colors.BLUE)
        else:
            logger.keyvalue("Ścieżka PDF/Folder", pdf_path, Colors.CYAN)
            logger.info("(Zostanie automatycznie wykryta czy to plik czy folder)")

        logger.keyvalue("Minimalny próg pewności", str(min_confidence), Colors.YELLOW)
        logger.keyvalue("Kontekst słów", f"{context_before}/{context_after}", Colors.MAGENTA)
        logger.keyvalue("Tryb debugowania", "WŁĄCZONY" if debug_mode else "WYŁĄCZONY",
                        Colors.GREEN if debug_mode else Colors.GRAY)

        # Inicjalizacja komponentów
        logger.info("Inicjalizacja komponentów...")
        detector = FragmentDetector(
            context_before=context_before,
            context_after=context_after,
            debug=debug_mode
        )

        output_manager = OutputManager(debug=debug_mode)
        logger.success("Komponenty zainicjalizowane")

        # Przetwarzanie
        if path.is_dir():
            # Przetwarzanie folderu
            results = detector.process_pdf_folder(
                folder_path=pdf_path,
                min_confidence=min_confidence,
                max_fragments_per_file=max_fragments_per_file,
                max_total_fragments=max_total_fragments
            )

            if not results:
                logger.warning("Nie znaleziono fragmentów spełniających kryteria w żadnym pliku")
                _print_suggestions()
                return

            # Pobieramy wszystkie fragmenty posortowane według pewności
            fragments = detector.get_all_fragments_sorted(results)

        else:
            # Przetwarzanie pojedynczego pliku
            fragments = detector.process_pdf(
                pdf_path=pdf_path,
                min_confidence=min_confidence,
                max_fragments=max_fragments_per_file
            )

        if not fragments:
            logger.warning("Nie znaleziono fragmentów spełniających kryteria")
            _print_suggestions()
            return

        # Wyświetlenie najlepszych fragmentów
        logger.section("NAJLEPSZE FRAGMENTY")
        for i, fragment in enumerate(fragments[:5], 1):
            confidence_color = Colors.GREEN if fragment.confidence_score >= 0.7 else \
                Colors.YELLOW if fragment.confidence_score >= 0.4 else Colors.RED

            logger.info(f"Fragment {i}:")
            logger.keyvalue("  Mówca", fragment.speaker, Colors.CYAN)
            logger.keyvalue("  Pewność", f"{fragment.confidence_score:.3f}", confidence_color)
            logger.keyvalue("  Słowa kluczowe", fragment.get_keywords_as_string(), Colors.MAGENTA)

            # Wyświetlamy info o pliku źródłowym jeśli dostępne
            if "| Plik:" in fragment.meeting_info:
                meeting_part, file_part = fragment.meeting_info.split("| Plik:")
                logger.keyvalue("  Plik źródłowy", file_part.strip(), Colors.BLUE)
                logger.keyvalue("  Posiedzenie", meeting_part.strip(), Colors.GRAY)
            else:
                logger.keyvalue("  Posiedzenie", fragment.meeting_info, Colors.GRAY)

            logger.keyvalue("  Podgląd", fragment.get_short_preview(100), Colors.WHITE)
            print()

        # Zapis plików
        logger.section("ZAPIS WYNIKÓW")

        json_filename = "funny_fragments.json"
        if output_manager.save_fragments_to_json(fragments, json_filename):
            logger.success(f"Zapisano do {json_filename}")
        else:
            logger.error(f"Błąd zapisu do {json_filename}")

        csv_filename = "funny_fragments.csv"
        if output_manager.export_fragments_to_csv(fragments, csv_filename):
            logger.success(f"Eksport do {csv_filename}")
        else:
            logger.error(f"Błąd eksportu do {csv_filename}")

        # Dodatkowy zapis z podziałem na pliki (jeśli przetwarzaliśmy folder)
        if path.is_dir() and len(results) > 1:
            logger.info("Zapisywanie wyników z podziałem na pliki źródłowe...")

            for file_name, file_fragments in results.items():
                if file_fragments:
                    clean_name = os.path.splitext(file_name)[0]  # Usuwa rozszerzenie .pdf
                    file_json = f"fragments_{clean_name}.json"

                    if output_manager.save_fragments_to_json(file_fragments, file_json):
                        logger.info(f"  Zapisano {len(file_fragments)} fragmentów z {file_name} do {file_json}")

        # Statystyki końcowe
        if debug_mode:
            logger.section("STATYSTYKI WYDAJNOŚCI")
            stats = detector.get_processing_stats()

            logger.table_header(["Metryka", "Wartość"])

            if path.is_dir():
                logger.table_row(["Przetworzone pliki", str(stats['processed_files'])], True)
                logger.table_row(["Nieudane pliki", str(stats['failed_files'])], True)

            logger.table_row(["Znalezione słowa kluczowe", str(stats['found_keywords'])], True)
            logger.table_row(["Utworzone fragmenty", str(stats['created_fragments'])], True)
            logger.table_row(["Pominięte duplikaty", str(stats['skipped_duplicates'])], True)
            logger.table_row(["Pominięte (niska pewność)", str(stats['skipped_low_confidence'])], True)

            if stats['found_keywords'] > 0:
                efficiency = (stats['created_fragments'] / stats['found_keywords']) * 100
                efficiency_color = Colors.GREEN if efficiency >= 20 else \
                    Colors.YELLOW if efficiency >= 10 else Colors.RED
                logger.keyvalue("Skuteczność konwersji", f"{efficiency:.1f}%", efficiency_color)

        logger.success(f"Analiza zakończona pomyślnie! Znaleziono {len(fragments)} fragmentów wysokiej jakości")

    except ValueError as e:
        logger.critical(f"Błąd konfiguracji: {e}")
    except FileNotFoundError:
        logger.error(f"Ścieżka {pdf_path} nie została znaleziona")
        logger.info("Sprawdź czy ścieżka do pliku PDF lub folderu jest prawidłowa")
    except Exception as e:
        logger.critical(f"Nieoczekiwany błąd: {e}")
        if debug_mode:
            import traceback
            logger.error("Stos wywołań:")
            print(traceback.format_exc())


def _print_suggestions():
    """Wyświetla sugestie gdy nie znaleziono fragmentów"""
    logger.info("Spróbuj dostroić parametry:")
    logger.list_item("Obniż min_confidence", level=1)
    logger.list_item("Zwiększ context_before/context_after", level=1)
    logger.list_item("Sprawdź zawartość plików PDF", level=1)
    logger.list_item("Upewnij się że pliki to transkrypty sejmowe", level=1)


def run_example_with_folder():
    """Przykład uruchomienia z folderem PDFów"""

    print("=== PRZYKŁAD PRZETWARZANIA FOLDERU ===\n")

    # Konfiguracja dla przetwarzania wielu plików
    detector = FragmentDetector(
        context_before=20,
        context_after=20,
        debug=False
    )

    output_manager = OutputManager(debug=False)

    try:
        # Przetwarzanie całego folderu
        results = detector.process_pdf_folder(
            folder_path="transkrypty_sejmu",
            min_confidence=0.4,
            max_fragments_per_file=10,  # Mniej fragmentów z każdego pliku
            max_total_fragments=50  # Ale więcej łącznie
        )

        if results:
            print(f"🔍 ZNALEZIONO FRAGMENTY W {len(results)} PLIKACH:")

            # Wyświetlamy podsumowanie dla każdego pliku
            for file_name, fragments in results.items():
                avg_confidence = sum(f.confidence_score for f in fragments) / len(fragments)
                print(f"\n📄 {file_name}: {len(fragments)} fragmentów (śr. pewność: {avg_confidence:.2f})")

                # Pokazujemy najlepszy fragment z każdego pliku
                best_fragment = max(fragments, key=lambda f: f.confidence_score)
                print(f"   Najlepszy: {best_fragment.get_short_preview(80)}")

            # Zapisujemy wszystkie fragmenty razem
            all_fragments = detector.get_all_fragments_sorted(results)
            output_manager.save_fragments_to_json(all_fragments, "folder_results.json")
            print(f"\n✅ Zapisano {len(all_fragments)} fragmentów do folder_results.json")

    except Exception as e:
        print(f"Błąd w przykładzie: {e}")


def interactive_mode():
    """Tryb interaktywny do eksperymentowania z parametrami"""

    print("=== TRYB INTERAKTYWNY ===\n")

    # Pobieranie parametrów od użytkownika
    pdf_path = input("Podaj ścieżkę do pliku PDF lub folderu (Enter = transkrypty_sejmu): ").strip()
    if not pdf_path:
        pdf_path = "transkrypty_sejmu"

    try:
        min_conf_input = input("Minimalna pewność (Enter = 0.3): ").strip()
        min_confidence = float(min_conf_input) if min_conf_input else 0.3
    except ValueError:
        min_confidence = 0.3

    try:
        max_frag_input = input("Maksymalna liczba fragmentów (Enter = 50): ").strip()
        max_fragments = int(max_frag_input) if max_frag_input else 50
    except ValueError:
        max_fragments = 50

    debug_input = input("Tryb debugowania? (t/n, Enter = n): ").strip().lower()
    debug_mode = debug_input in ['t', 'tak', 'true', 'yes']

    # Sprawdzamy czy to folder
    path = Path(pdf_path)
    if path.is_dir():
        try:
            max_per_file_input = input("Maksymalna liczba fragmentów na plik (Enter = 20): ").strip()
            max_per_file = int(max_per_file_input) if max_per_file_input else 20
        except ValueError:
            max_per_file = 20
    else:
        max_per_file = max_fragments

    # Inicjalizacja i uruchomienie
    detector = FragmentDetector(debug=debug_mode)
    output_manager = OutputManager(debug=debug_mode)

    try:
        if path.is_dir():
            results = detector.process_pdf_folder(
                pdf_path, min_confidence, max_per_file, max_fragments
            )
            fragments = detector.get_all_fragments_sorted(results)
        else:
            fragments = detector.process_pdf(pdf_path, min_confidence, max_fragments)

        if fragments:
            output_manager.print_fragments(fragments)

            save_input = input("\nZapisać wyniki do pliku? (t/n): ").strip().lower()
            if save_input in ['t', 'tak', 'true', 'yes']:
                filename = input("Nazwa pliku (Enter = funny_fragments.json): ").strip()
                if not filename:
                    filename = "funny_fragments.json"
                output_manager.save_fragments_to_json(fragments, filename)

    except Exception as e:
        print(f"Błąd: {e}")


def demo_color_palettes():
    """Demonstracja wszystkich dostępnych palet kolorów"""

    logger.header("DEMONSTRACJA PALET KOLORÓW")

    available_palettes = logger.get_available_palettes()
    logger.info(f"Dostępne palety: {', '.join(available_palettes)}")

    for palette_name in available_palettes:
        logger.set_palette(palette_name)
        logger.palette_demo()

        if palette_name != available_palettes[-1]:  # Nie pyta po ostatniej palecie
            user_input = input(f"\nNaciśnij Enter aby zobaczyć następną paletę (lub 'q' aby zakończyć)...")
            if user_input.lower() == 'q':
                break

    # Powrót do domyślnej palety
    logger.set_palette("default")
    logger.success("Demonstracja zakończona - przywrócono domyślną paletę")


def create_sample_folder_structure():
    """Tworzy przykładową strukturę folderów do testowania"""

    print("=== TWORZENIE PRZYKŁADOWEJ STRUKTURY ===\n")

    sample_folder = "transkrypty"

    try:
        os.makedirs(sample_folder, exist_ok=True)

        # Informacja o tym co użytkownik powinien zrobić
        print(f" Utworzono folder: {sample_folder}")
        print("\nInstrukcje:")
        print("1. Umieść pliki PDF z transkryptami Sejmu w folderze 'transkrypty'")
        print("2. Pliki mogą mieć dowolne nazwy (np. 'posiedzenie_1.pdf', 'sejm_123.pdf')")
        print("3. Uruchom program z konfiguracją pdf_path = 'transkrypty'")

        return sample_folder

    except Exception as e:
        print(f"Błąd podczas tworzenia struktury: {e}")
        return None


if __name__ == "__main__":
    # Możesz wybrać jeden z trybów uruchomienia:

    # 1. Standardowe uruchomienie (obsługuje teraz foldery!)
    main()

    # 2. Przykład z folderem PDFów (odkomentuj poniższą linię)
    # run_example_with_folder()

    # 3. Tryb interaktywny (odkomentuj poniższą linię)
    # interactive_mode()

    # 4. Demonstracja palet kolorów (odkomentuj poniższą linię)
    # demo_color_palettes()

    # 5. Tworzenie przykładowej struktury folderów (odkomentuj poniższą linię)
    # create_sample_folder_structure()
