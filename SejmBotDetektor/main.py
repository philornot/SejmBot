"""
Główny skrypt (entry-point) - wersja zrefaktorowana
Deleguje całą logikę do odpowiednich komponentów
"""
import os
from pathlib import Path

from SejmBotDetektor.generate_output.output_manager import OutputManager
from SejmBotDetektor.logging.colors import Colors
from SejmBotDetektor.logging.logger import logger, LogLevel


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


def validate_environment():
    """
    Sprawdza czy środowisko jest poprawnie skonfigurowane
    """
    # Sprawdzamy czy istnieje baza posłów
    poslowie_file_exists = any(os.path.exists(path) for path in [
        "poslowie_kluby.json",
        "SejmBotDetektor/data/poslowie_kluby.json",
        "data/poslowie_kluby.json"
    ])

    if not poslowie_file_exists:
        logger.warning("Nie znaleziono pliku poslowie_kluby.json")
        logger.info("Utwórz plik poslowie_kluby.json zgodnie z dokumentacją dla lepszego przypisywania klubów")

    # Walidacja konfiguracji słów kluczowych
    try:
        from SejmBotDetektor.config.keywords import KeywordsConfig
        issues = KeywordsConfig.validate_keywords()
        if issues:
            logger.warning("Znaleziono problemy w konfiguracji słów kluczowych:")
            for issue in issues:
                logger.list_item(issue, level=1)
            print()
    except ImportError:
        logger.warning("Nie można zwalidować konfiguracji słów kluczowych")


def print_configuration(pdf_path: str, min_confidence: float, max_fragments_per_file: int,
                        max_total_fragments: int, context_before: int, context_after: int, debug_mode: bool):
    """
    Wyświetla konfigurację aplikacji
    """
    logger.section("KONFIGURACJA")

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


def print_suggestions():
    """Wyświetla sugestie gdy nie znaleziono fragmentów"""
    logger.info("Spróbuj dostroić parametry:")
    logger.list_item("Obniż min_confidence", level=1)
    logger.list_item("Zwiększ context_before/context_after", level=1)
    logger.list_item("Sprawdź zawartość plików PDF", level=1)
    logger.list_item("Upewnij się że pliki to transkrypty sejmowe", level=1)


def main():
    """Główna funkcja programu - czysty entry-point delegujący do OutputManager"""

    # Konfiguracja
    pdf_path = "transkrypty"
    min_confidence = 0.3
    max_fragments_per_file = 20
    max_total_fragments = 100
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

        # Inicjalizacja środowiska
        output_folder = ensure_output_folder()
        if output_folder:
            logger.info(f"Pliki wyjściowe będą zapisane w folderze: {output_folder}")

        validate_environment()
        print_configuration(pdf_path, min_confidence, max_fragments_per_file,
                            max_total_fragments, context_before, context_after, debug_mode)

        # Przygotowujemy konfigurację do zapisania w metadanych
        export_config = {
            "min_confidence": min_confidence,
            "max_fragments_per_file": max_fragments_per_file,
            "max_total_fragments": max_total_fragments,
            "context_before": context_before,
            "context_after": context_after,
            "debug_mode": debug_mode
        }

        logger.info("Rozpoczynam przetwarzanie...")

        # Inicjalizacja OutputManager - to on teraz zarządza całym procesem
        output_manager = OutputManager(debug=debug_mode, output_folder=output_folder)

        path = Path(pdf_path)
        if path.is_dir():
            # Przetwarzanie folderu - wszystko w OutputManager
            results = output_manager.process_folder_results(
                folder_path=pdf_path,
                min_confidence=min_confidence,
                max_fragments_per_file=max_fragments_per_file,
                max_total_fragments=max_total_fragments,
                context_before=context_before,
                context_after=context_after
            )

            if not results:
                logger.warning("Nie znaleziono fragmentów spełniających kryteria w żadnym pliku")
                print_suggestions()
                return

            # Wyświetlenie wyników
            output_manager.print_folder_results(results, max_files=5)

            # Eksport wyników
            logger.section("ZAPIS WYNIKÓW")
            include_html = debug_mode  # HTML tylko w trybie debug

            if output_manager.export_results(results, "batch_results", include_html, export_config):
                logger.success("Eksport zakończony pomyślnie")
            else:
                logger.warning("Niektóre eksporty mogły się nie powieść")

            # Statystyki
            all_fragments = [f for fragments in results.values() for f in fragments]
            if all_fragments:
                output_manager.print_summary_stats(all_fragments)

        else:
            # Przetwarzanie pojedynczego pliku
            fragments = output_manager.process_single_file_complete(
                pdf_path=pdf_path,
                min_confidence=min_confidence,
                max_fragments=max_fragments_per_file,
                include_export=True
            )

            if not fragments:
                logger.warning("Nie znaleziono fragmentów spełniających kryteria")
                print_suggestions()
                return

            # Statystyki
            output_manager.print_summary_stats(fragments)

        # Podsumowanie eksportu
        output_manager.print_export_summary()
        logger.success("Analiza zakończona pomyślnie!")

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


def interactive_mode():
    """Tryb interaktywny wykorzystujący OutputManager"""
    print("=== TRYB INTERAKTYWNY ===\n")

    output_folder = ensure_output_folder()
    output_manager = OutputManager(debug=False, output_folder=output_folder)

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

    # Aktualizujemy OutputManager z debug mode
    output_manager = OutputManager(debug=debug_mode, output_folder=output_folder)

    path = Path(pdf_path)
    if path.is_dir():
        try:
            max_per_file_input = input("Maksymalna liczba fragmentów na plik (Enter = 20): ").strip()
            max_per_file = int(max_per_file_input) if max_per_file_input else 20
        except ValueError:
            max_per_file = 20
    else:
        max_per_file = max_fragments

    # Konfiguracja eksportu
    export_config = {
        "min_confidence": min_confidence,
        "max_fragments": max_fragments,
        "max_per_file": max_per_file,
        "interactive_mode": True,
        "user_requested_html": include_html
    }

    try:
        if path.is_dir():
            results = output_manager.process_folder_results(
                folder_path=pdf_path,
                min_confidence=min_confidence,
                max_fragments_per_file=max_per_file,
                max_total_fragments=max_fragments
            )

            if results:
                output_manager.print_folder_results(results)
                if output_manager.export_results(results, "interactive_batch", include_html, export_config):
                    print("Wyniki z folderu zostały zapisane!")

                all_fragments = [f for fragments in results.values() for f in fragments]
                if all_fragments:
                    output_manager.print_summary_stats(all_fragments)
        else:
            fragments = output_manager.process_single_file_complete(
                pdf_path=pdf_path,
                min_confidence=min_confidence,
                max_fragments=max_fragments,
                include_export=include_html
            )

            if fragments:
                if include_html:
                    if output_manager.export_results(fragments, "interactive_fragments", include_html, export_config):
                        print("Fragmenty zostały zapisane!")

        output_manager.print_export_summary()

    except Exception as e:
        print(f"Błąd: {e}")


if __name__ == "__main__":
    # Można wybrać tryb uruchomienia:

    # 1. Standardowe uruchomienie
    main()

    # 2. Tryb interaktywny (odkomentuj poniższą linię)
    # interactive_mode()
