"""
Główny skrypt (entry-point)
"""
import os
from pathlib import Path

from SejmBotDetektor.detectors.fragment_detector import FragmentDetector
from SejmBotDetektor.generate_output.output_manager import OutputManager
from SejmBotDetektor.logging.logger import logger, Colors, LogLevel


def ensure_output_folder() -> str:
    """
    Zapewnia istnienie folderu output i zwraca jego ścieżkę

    Returns:
        Ścieżka do folderu output
    """
    output_folder = "output"

    try:
        os.makedirs(output_folder, exist_ok=True)
        return output_folder
    except Exception as e:
        logger.error(f"Nie można utworzyć folderu output: {e}")
        logger.warning("Pliki zostaną zapisane w folderze głównym")
        return ""


def main():
    """Główna funkcja programu"""

    # Konfiguracja
    pdf_path = "transkrypty"  # ścieżka do folderu
    min_confidence = 0.3
    max_fragments_per_file = 20
    max_total_fragments = 100  # całkowity limit fragmentów
    context_before = 50
    context_after = 100
    debug_mode = True

    # Ustawiamy poziom logowania
    if debug_mode:
        logger.set_level(LogLevel.DEBUG)
    else:
        logger.set_level(LogLevel.INFO)

    try:
        # Nagłówek aplikacji
        logger.header("DETEKTOR ŚMIESZNYCH FRAGMENTÓW Z SEJMU")

        # Zapewniamy istnienie folderu output
        output_folder = ensure_output_folder()
        if output_folder:
            logger.info(f"Pliki wyjściowe będą zapisane w folderze: {output_folder}")

        # Sprawdzamy, czy istnieje baza posłów
        poslowie_file_exists = any(os.path.exists(path) for path in [
            "poslowie_kluby.json",
            "SejmBotDetektor/data/poslowie_kluby.json",
            "data/poslowie_kluby.json"
        ])

        if not poslowie_file_exists:
            logger.warning("Nie znaleziono pliku poslowie_kluby.json")
            logger.info("Utwórz plik poslowie_kluby.json zgodnie z dokumentacją dla lepszego przypisywania klubów")

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

        output_manager = OutputManager(debug=debug_mode, output_folder=output_folder)
        logger.success("Komponenty zainicjalizowane")

        # Przygotowujemy konfigurację do zapisania w metadanych
        export_config = {
            "min_confidence": min_confidence,
            "max_fragments_per_file": max_fragments_per_file,
            "max_total_fragments": max_total_fragments,
            "context_before": context_before,
            "context_after": context_after,
            "debug_mode": debug_mode
        }

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

            # Wyświetlenie wyników w konsoli
            output_manager.print_folder_results(results, max_files=5)

            # Pobieramy wszystkie fragmenty posortowane według pewności
            fragments = detector.get_all_fragments_sorted(results)

            # Eksport wyników
            logger.section("ZAPIS WYNIKÓW")

            # Eksport w nowym formacie - HTML tylko w trybie debug
            include_html = debug_mode

            if output_manager.export_results(results, "batch_results", include_html, export_config):
                logger.success("Eksport zakończony pomyślnie")
            else:
                logger.warning("Niektóre eksporty mogły się nie powieść")

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

            # Wyświetlenie wyników w konsoli
            output_manager.print_results(fragments, max_fragments=5)

            # Eksport wyników
            logger.section("ZAPIS WYNIKÓW")

            # Eksport w nowym formacie - HTML tylko w trybie debug
            include_html = debug_mode

            if output_manager.export_results(fragments, "fragments", include_html, export_config):
                logger.success("Eksport zakończony pomyślnie")
            else:
                logger.warning("Niektóre eksporty mogły się nie powieść")

        # Wyświetl statystyki fragmentów
        if fragments:
            output_manager.print_summary_stats(fragments)

        # Podsumowanie eksportu
        output_manager.print_export_summary()

        # Statystyki końcowe wydajności (tylko w trybie debug)
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

        if output_folder:
            logger.info(f"Wszystkie pliki wyjściowe zapisano w folderze: {output_folder}")

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

    # Zapewniamy folder output
    output_folder = ensure_output_folder()

    # Konfiguracja dla przetwarzania wielu plików
    detector = FragmentDetector(
        context_before=20,
        context_after=20,
        debug=False
    )

    output_manager = OutputManager(debug=False, output_folder=output_folder)

    try:
        # Przetwarzanie całego folderu
        results = detector.process_pdf_folder(
            folder_path="transkrypty_sejmu",
            min_confidence=0.4,
            max_fragments_per_file=10,  # Mniej fragmentów z każdego pliku
            max_total_fragments=50  # Ale więcej łącznie
        )

        if results:
            print(f"ZNALEZIONO FRAGMENTY W {len(results)} PLIKACH:")

            # Wyświetlamy podsumowanie dla każdego pliku
            for file_name, fragments in results.items():
                avg_confidence = sum(f.confidence_score for f in fragments) / len(fragments)
                print(f"\n📄 {file_name}: {len(fragments)} fragmentów (śr. pewność: {avg_confidence:.2f})")

                # Pokazujemy najlepszy fragment z każdego pliku
                best_fragment = max(fragments, key=lambda f: f.confidence_score)
                print(f"   Najlepszy: {best_fragment.get_short_preview(80)}")

            # Eksportujemy wyniki w nowym formacie
            export_config = {
                "min_confidence": 0.4,
                "max_fragments_per_file": 10,
                "max_total_fragments": 50,
                "example_run": True
            }

            if output_manager.export_results(results, "example_batch", True, export_config):
                print(f"\nWyniki wyeksportowane pomyślnie!")

            # Wyświetlamy podsumowanie
            output_manager.print_export_summary()

    except Exception as e:
        print(f"Błąd w przykładzie: {e}")


def interactive_mode():
    """Tryb interaktywny do eksperymentowania z parametrami"""

    print("=== TRYB INTERAKTYWNY ===\n")

    # Zapewniamy folder output
    output_folder = ensure_output_folder()

    # Pobieranie parametrów od użytkownika
    pdf_path = input("Podaj ścieżkę do pliku PDF lub folderu (Enter = transkrypty): ").strip()
    if not pdf_path:
        pdf_path = "transkrypty"

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

    html_input = input("Generować raport HTML? (t/n, Enter = n): ").strip().lower()
    include_html = html_input in ['t', 'tak', 'true', 'yes']

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
    output_manager = OutputManager(debug=debug_mode, output_folder=output_folder)

    # Konfiguracja do zapisania w metadanych
    export_config = {
        "min_confidence": min_confidence,
        "max_fragments": max_fragments,
        "max_per_file": max_per_file,
        "interactive_mode": True,
        "user_requested_html": include_html
    }

    try:
        if path.is_dir():
            results = detector.process_pdf_folder(
                pdf_path, min_confidence, max_per_file, max_fragments
            )
            if results:
                output_manager.print_folder_results(results)
                fragments = detector.get_all_fragments_sorted(results)

                # Eksport w nowym formacie
                if output_manager.export_results(results, "interactive_batch", include_html, export_config):
                    print("Wyniki z folderu zostały zapisane!")
            else:
                fragments = []
        else:
            fragments = detector.process_pdf(pdf_path, min_confidence, max_fragments)
            if fragments:
                output_manager.print_results(fragments)

                # Eksport w nowym formacie
                if output_manager.export_results(fragments, "interactive_fragments", include_html, export_config):
                    print("Fragmenty zostały zapisane!")

        if fragments:
            output_manager.print_export_summary()

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
    output_folder = "output"

    try:
        os.makedirs(sample_folder, exist_ok=True)
        os.makedirs(output_folder, exist_ok=True)

        # Informacja o tym co użytkownik powinien zrobić
        print(f"Utworzono folder: {sample_folder}")
        print(f"Utworzono folder: {output_folder}")
        print("\nInstrukcje:")
        print("1. Umieść pliki PDF z transkryptami Sejmu w folderze 'transkrypty'")
        print("2. Pliki mogą mieć dowolne nazwy (np. 'posiedzenie_1.pdf', 'sejm_123.pdf')")
        print("3. Uruchom program z konfiguracją pdf_path = 'transkrypty'")
        print("4. Wyniki będą zapisane w folderze 'output'")

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
