"""
Główny skrypt (entry-point)
"""
from SejmBotDetektor.detectors.fragment_detector import FragmentDetector
from SejmBotDetektor.utils.logger import logger, Colors, LogLevel
from SejmBotDetektor.utils.output_manager import OutputManager


def main():
    """Główna funkcja programu"""

    # Konfiguracja
    pdf_path = "transkrypt_sejmu.pdf"
    min_confidence = 0.3
    max_fragments = 20
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
        from config.keywords import KeywordsConfig
        issues = KeywordsConfig.validate_keywords()
        if issues:
            logger.warning("Znaleziono problemy w konfiguracji słów kluczowych:")
            for issue in issues:
                logger.list_item(issue, level=1)
            print()

        # Wyświetlanie konfiguracji
        logger.section("KONFIGURACJA")
        logger.keyvalue("Plik PDF", pdf_path, Colors.CYAN)
        logger.keyvalue("Minimalny próg pewności", str(min_confidence), Colors.YELLOW)
        logger.keyvalue("Maksymalna liczba fragmentów", str(max_fragments), Colors.BLUE)
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
        fragments = detector.process_pdf(
            pdf_path=pdf_path,
            min_confidence=min_confidence,
            max_fragments=max_fragments
        )

        if not fragments:
            logger.warning("Nie znaleziono fragmentów spełniających kryteria")
            logger.info("Spróbuj dostroić parametry:")
            logger.list_item("Obniż min_confidence", level=1)
            logger.list_item("Zwiększ context_before/context_after", level=1)
            logger.list_item("Sprawdź zawartość pliku PDF", level=1)
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

        # Statystyki końcowe
        if debug_mode:
            logger.section("STATYSTYKI WYDAJNOŚCI")
            stats = detector.get_processing_stats()

            logger.table_header(["Metryka", "Wartość"])
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
        logger.error(f"Plik {pdf_path} nie został znaleziony")
        logger.info("Umieść plik PDF w folderze ze skryptem lub zmień ścieżkę")
    except Exception as e:
        logger.critical(f"Nieoczekiwany błąd: {e}")
        if debug_mode:
            import traceback
            logger.error("Stos wywołań:")
            print(traceback.format_exc())


def run_example_with_custom_config():
    """Przykład uruchomienia z niestandardową konfiguracją"""

    print("=== PRZYKŁAD Z NIESTANDARDOWĄ KONFIGURACJĄ ===\n")

    # Konfiguracja dla bardzo restrykcyjnego wyszukiwania
    detector = FragmentDetector(
        context_before=20,  # Mniej kontekstu
        context_after=20,
        debug=False  # Bez debugowania
    )

    output_manager = OutputManager(debug=False)

    try:
        fragments = detector.process_pdf(
            pdf_path="transkrypt_sejmu.pdf",
            min_confidence=0.6,  # Wyższa pewność
            max_fragments=5  # Tylko najlepsze
        )

        if fragments:
            print("🔍 NAJBARDZIEJ PEWNE FRAGMENTY:")
            output_manager.print_fragments(fragments, max_fragments=5)

    except Exception as e:
        print(f"Błąd w przykładzie: {e}")


def interactive_mode():
    """Tryb interaktywny do eksperymentowania z parametrami"""

    print("=== TRYB INTERAKTYWNY ===\n")

    # Pobieranie parametrów od użytkownika
    pdf_path = input("Podaj ścieżkę do pliku PDF (Enter = transkrypt_sejmu.pdf): ").strip()
    if not pdf_path:
        pdf_path = "transkrypt_sejmu.pdf"

    try:
        min_conf_input = input("Minimalna pewność (Enter = 0.3): ").strip()
        min_confidence = float(min_conf_input) if min_conf_input else 0.3
    except ValueError:
        min_confidence = 0.3

    try:
        max_frag_input = input("Maksymalna liczba fragmentów (Enter = 20): ").strip()
        max_fragments = int(max_frag_input) if max_frag_input else 20
    except ValueError:
        max_fragments = 20

    debug_input = input("Tryb debugowania? (t/n, Enter = n): ").strip().lower()
    debug_mode = debug_input in ['t', 'tak', 'true', 'yes']

    # Inicjalizacja i uruchomienie
    detector = FragmentDetector(debug=debug_mode)
    output_manager = OutputManager(debug=debug_mode)

    try:
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


if __name__ == "__main__":
    # Możesz wybrać jeden z trybów uruchomienia:

    # 1. Standardowe uruchomienie
    main()

    # 2. Przykład z niestandardową konfiguracją (odkomentuj poniższą linię)
    # run_example_with_custom_config()

    # 3. Tryb interaktywny (odkomentuj poniższą linię)
    # interactive_mode()

    # 4. Demonstracja palet kolorów (odkomentuj poniższą linię)
    # demo_color_palettes()