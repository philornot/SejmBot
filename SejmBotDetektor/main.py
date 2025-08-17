"""
Główny skrypt (entry-point)
"""
from detectors.fragment_detector import FragmentDetector
from utils.output_manager import OutputManager


def main():
    """Główna funkcja programu - ulepszona wersja"""

    # Konfiguracja z walidacją
    pdf_path = "transkrypt_sejmu.pdf"
    min_confidence = 0.3  # Obniżono domyślny próg
    max_fragments = 20
    context_before = 25  # Zmniejszono dla lepszej wydajności
    context_after = 25
    debug_mode = True

    try:
        # Walidacja konfiguracji słów kluczowych
        from config.keywords import KeywordsConfig
        issues = KeywordsConfig.validate_keywords()
        if issues:
            print("OSTRZEŻENIA konfiguracji słów kluczowych:")
            for issue in issues:
                print(f"  - {issue}")
            print()

        # Inicjalizacja komponentów
        detector = FragmentDetector(
            context_before=context_before,
            context_after=context_after,
            debug=debug_mode
        )

        output_manager = OutputManager(debug=debug_mode)

        print("=== DETEKTOR ŚMIESZNYCH FRAGMENTÓW Z SEJMU v2.0 ===\n")
        print(f"Przetwarzanie: {pdf_path}")
        print(
            f"Konfiguracja: confidence≥{min_confidence}, max={max_fragments}, kontekst={context_before}/{context_after}")

        # Przetworzenie PDF z obsługą błędów
        fragments = detector.process_pdf(
            pdf_path=pdf_path,
            min_confidence=min_confidence,
            max_fragments=max_fragments
        )

        if not fragments:
            return

        # Wyświetlenie wyników z lepszym formatowaniem
        output_manager.print_fragments(fragments, max_fragments=8)
        output_manager.print_fragments_summary(fragments)

        # Zapis wyników
        json_filename = "funny_fragments.json"
        if output_manager.save_fragments_to_json(fragments, json_filename):
            print(f"✅ Zapisano do {json_filename}")

        csv_filename = "funny_fragments.csv"
        if output_manager.export_fragments_to_csv(fragments, csv_filename):
            print(f"✅ Eksport do {csv_filename}")

        # Wyświetlenie statystyk wydajności
        if debug_mode:
            stats = detector.get_processing_stats()
            print(f"\n📊 Statystyki wydajności:")
            print(f"  Skuteczność: {stats['created_fragments']}/{stats['found_keywords']} słów→fragmenty")

        print(f"\n🎉 Analiza zakończona! Znaleziono {len(fragments)} wysokiej jakości fragmentów.")

    except ValueError as e:
        print(f"❌ Błąd konfiguracji: {e}")
    except FileNotFoundError:
        print(f"❌ Plik {pdf_path} nie został znaleziony.")
        print("💡 Umieść plik PDF w folderze ze skryptem lub zmień ścieżkę w zmiennej 'pdf_path'.")
    except Exception as e:
        print(f"❌ Nieoczekiwany błąd: {e}")
        if debug_mode:
            import traceback
            traceback.print_exc()


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


if __name__ == "__main__":
    # Możesz wybrać jeden z trybów uruchomienia:

    # 1. Standardowe uruchomienie
    main()

    # 2. Przykład z niestandardową konfiguracją (odkomentuj poniższą linię)
    # run_example_with_custom_config()

    # 3. Tryb interaktywny (odkomentuj poniższą linię)
    # interactive_mode()
