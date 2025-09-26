"""Entry point for SejmBotDetektor

CLI minimalny szkic — bez implementacji detekcji AI.
"""

import argparse
from pathlib import Path

from SejmBotDetektor.config import get_detector_settings


def create_parser():
    parser = argparse.ArgumentParser(
        description='SejmBotDetektor — przygotowanie i przetwarzanie tekstów przed analizą AI',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument('--input-dir', type=str, help='Katalog z plikami transkryptów (domyślnie z configu)')
    parser.add_argument('--output-dir', type=str, help='Katalog do zapisu wyników (domyślnie z configu)')
    parser.add_argument('--max-statements', type=int, help='Maksymalna liczba wypowiedzi do przetworzenia')
    parser.add_argument('--test-mode', action='store_true', help='Tryb testowy — ograniczone zachowanie i więcej logów')

    parser.add_argument('--version', action='version', version='SejmBotDetektor 0.1.0')

    return parser


def main(argv=None):
    parser = create_parser()
    args = parser.parse_args(argv)

    settings = get_detector_settings()

    input_dir = Path(args.input_dir) if args.input_dir else settings.input_dir
    output_dir = Path(args.output_dir) if args.output_dir else settings.output_dir
    max_statements = args.max_statements if args.max_statements is not None else settings.max_statements
    test_mode = args.test_mode or settings.test_mode

    # Minimalny smoke-run: pokaż parametry i wykonaj prosty test wczytania pliku
    print('SejmBotDetektor — uruchamiam pipeline detektora')
    print(f'  input_dir:  {input_dir}')
    print(f'  output_dir: {output_dir}')
    print(f'  max_statements: {max_statements}')
    print(f'  test_mode: {test_mode}')

    # Upewnij się, że katalog wyników istnieje
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
    except Exception:
        print(f'Nie można utworzyć katalogu output: {output_dir}')

    # Wspólna implementacja prostego pipeline detektora.
    def _run_pipeline(use_test_fixture: bool = False):
        # importy wewnątrz funkcji — lazy imports zgodnie z konwencją repo
        import json
        from pathlib import Path
        from SejmBotDetektor import preprocessing
        from SejmBotDetektor import keyword_scoring
        from SejmBotDetektor import fragment_extraction
        from SejmBotDetektor import serializers

        # przygotuj listę plików wejściowych
        input_paths = []
        if not use_test_fixture and input_dir and input_dir.exists() and input_dir.is_dir():
            json_files = list(Path(input_dir).glob('*.json'))
            input_paths.extend(json_files)

        # jeśli brak plików i tryb testowy lub fallback — spróbuj użyć plików wygenerowanych przez Scraper
        if not input_paths:
            # Szukaj plików JSON wygenerowanych przez SejmBotScraper w repo (data_sejm lub data)
            repo_root = Path(__file__).resolve().parents[1]
            candidate_dirs = [repo_root / 'data_sejm', repo_root / 'data']
            found = []
            for cd in candidate_dirs:
                if cd.exists() and cd.is_dir():
                    # szukamy rekurencyjnie plików JSON — mogą to być zapisy posiedzeń lub output scrappera
                    found.extend([p for p in cd.rglob('*.json') if 'detector' not in str(p).lower()])
            # posortuj, by mieć deterministyczny porządek (najpierw najnowsze według nazwy)
            found = sorted(found)
            if found:
                input_paths.extend(found)
            else:
                # fallback do wbudowanej próbki — tylko jeśli nic nie znaleziono
                fixture_path = Path(__file__).parent / 'fixtures' / 'transcript_sample.json'
                if fixture_path.exists():
                    input_paths.append(fixture_path)
                else:
                    print('Brak plików JSON w input_dir oraz brak plików wygenerowanych przez Scraper i brak wbudowanej próbki. Kończę.')
                    return

        # wczytaj słowa kluczowe (najpierw lokalny plik w pakiecie)
        kws_path = Path(__file__).parent / 'keywords' / 'keywords.json'
        try:
            keywords = keyword_scoring.load_keywords_from_json(str(kws_path))
        except Exception:
            print(f'Nie mozna wczytac slow-kluczowych z {kws_path}, uzywam domyslnych')
            keywords = [{'keyword': 'humor', 'weight': 1.0}, {'keyword': 'żart', 'weight': 2.0}]

        # przetwarzaj kolejne pliki (ogranicz do pierwszego, jeśli test-mode ogranicza)
        for file_p in input_paths:
            try:
                with open(file_p, 'r', encoding='utf-8') as fh:
                    data = json.load(fh)
            except Exception as e:
                print(f'Nie mozna wczytac pliku {file_p}: {e}')
                continue

            statements = data.get('statements') or data
            if isinstance(statements, dict) and 'statements' in statements:
                statements = statements.get('statements', [])
            if not isinstance(statements, list):
                print(f'Nie rozpoznano listy wypowiedzi w pliku {file_p}')
                continue

            # ogranicz liczbę wypowiedzi do max_statements
            stmts_to_process = statements[:max_statements]

            all_fragments = []
            for stmt in stmts_to_process:
                text = stmt.get('text') or stmt.get('segment') or ''
                cleaned = preprocessing.clean_html(text)
                normalized = preprocessing.normalize_text(cleaned)
                segments = preprocessing.split_into_sentences(normalized, max_chars=500)

                scored = keyword_scoring.score_segments([{'text': s} for s in segments], keywords)

                fragments = fragment_extraction.extract_fragments(scored, {'text': text, 'num': stmt.get('num')})
                if fragments:
                    all_fragments.extend(fragments)

            results = {
                'source_file': str(file_p),
                'n_statements': len(statements),
                'n_processed': len(stmts_to_process),
                'n_fragments': len(all_fragments),
                'fragments': all_fragments,
            }

            try:
                out_path = serializers.dump_results(results, base_dir=str(output_dir))
                print(f'Zapisano wyniki detektora do: {out_path}')
            except Exception as e:
                print(f'Nie udalo sie zapisac wynikow dla {file_p}: {e}')

            # Jeśli używamy trybu testowego, przetwórz tylko pierwszy plik
            if use_test_fixture:
                break

    # Uruchom właściwy pipeline: w trybie testowym — bardziej szczegółowy i z fallbackem;
    # w normalnym trybie — przetwórz pliki z input_dir (jeśli brak -> fallback do wbudowanej próbki)
    try:
        if test_mode:
            print('\nTRYB TESTOWY: uruchamiam pipeline detektora (diagnostyka)')
            _run_pipeline(use_test_fixture=True)
        else:
            print('\nUruchamiam pipeline detektora (normalny tryb)')
            _run_pipeline(use_test_fixture=False)
    except Exception as e:
        print(f'Blad podczas uruchamiania pipeline detektora: {e}')


if __name__ == '__main__':
    main()
