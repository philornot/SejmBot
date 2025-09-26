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
    print('SejmBotDetektor — szkic entrypointu')
    print(f'  input_dir:  {input_dir}')
    print(f'  output_dir: {output_dir}')
    print(f'  max_statements: {max_statements}')
    print(f'  test_mode: {test_mode}')

    # Upewnij się, że katalog wyników istnieje
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
    except Exception:
        print(f'Nie można utworzyć katalogu output: {output_dir}')

    # Jeśli włączono tryb testowy, wykonaj prosty smoke-run: wczytaj przykładowy JSON i policz wypowiedzi
    if test_mode:
        import json
        from pathlib import Path
        from SejmBotDetektor import preprocessing
        from SejmBotDetektor import keyword_scoring
        from SejmBotDetektor import fragment_extraction
        from SejmBotDetektor import serializers

        # 1) jeśli podano input_dir i znajdują się pliki .json, wybierz pierwszy
        sample_path = None
        try:
            if args.input_dir:
                p = Path(args.input_dir)
                if p.exists() and p.is_dir():
                    json_files = list(p.glob('*.json'))
                    if json_files:
                        sample_path = json_files[0]

            # 2) fallback: wbudowany fixture w pakiecie
            if sample_path is None:
                sample_path = Path(__file__).parent / 'fixtures' / 'transcript_sample.json'

            if sample_path and sample_path.exists():
                with open(sample_path, 'r', encoding='utf-8') as fh:
                    data = json.load(fh)

                statements = data.get('statements') or data.get('statements', [])
                # Be robust: if statements is dict with key 'statements'
                if isinstance(statements, dict):
                    statements = statements.get('statements', [])

                n = len(statements) if isinstance(statements, list) else 0
                print(f"\nSMOKE-RUN: wczytano plik: {sample_path}")
                print(f"SMOKE-RUN: liczba wypowiedzi: {n}")
                # Simple detection pipeline (keyword-based)
                try:
                    print('\nSMOKE-RUN: uruchamiam prosty scoring slow-kluczowych i ekstrakcje fragmentow')

                    # Load keywords
                    kws_path = Path(__file__).parent / 'keywords' / 'keywords.json'
                    try:
                        keywords = keyword_scoring.load_keywords_from_json(str(kws_path))
                    except Exception:
                        print(f'Nie mozna wczytac slow-kluczowych z {kws_path}, uzywam domyslnych')
                        keywords = [ {'keyword': 'humor', 'weight': 1.0}, {'keyword': 'żart', 'weight': 2.0} ]

                    all_fragments = []
                    # Process up to max_statements
                    for stmt in (statements[:max_statements] if isinstance(statements, list) else []):
                        text = stmt.get('text') or stmt.get('segment') or ''
                        cleaned = preprocessing.clean_html(text)
                        normalized = preprocessing.normalize_text(cleaned)
                        segments = preprocessing.split_into_sentences(normalized, max_chars=500)

                        # Score segments
                        scored = keyword_scoring.score_segments(segments, keywords)

                        # Test-mode diagnostics: print per-statement scoring summary
                        try:
                            stmt_num = stmt.get('num')
                        except Exception:
                            stmt_num = None
                        matches = []
                        for s in scored:
                            for m in s.get('matches', []):
                                matches.append({'keyword': m.get('keyword'), 'count': m.get('count', 1)})
                        if test_mode:
                            print(f"DETECTOR DEBUG: stmt={stmt_num} segments={len(segments)} scored_segments={len(scored)} matches={matches}")

                        # Extract fragments from scored segments
                        fragments = fragment_extraction.extract_fragments(scored, {'text': text, 'num': stmt.get('num')})
                        if fragments:
                            all_fragments.extend(fragments)

                    results = {
                        'source_file': str(sample_path),
                        'n_statements': n,
                        'n_fragments': len(all_fragments),
                        'fragments': all_fragments,
                    }

                    # Dump results
                    try:
                        out_path = serializers.dump_results(results, base_dir=str(output_dir))
                        print(f'SMOKE-RUN: zapisano wyniki detektora do: {out_path}')
                    except Exception as e:
                        print(f'Nie udalo sie zapisac wynikow: {e}')
                except Exception as e:
                    print(f'Blad w prostym pipeline detekcji: {e}')
            else:
                print('\nSMOKE-RUN: nie znaleziono przykładowego pliku JSON do wczytania')
        except Exception as e:
            print(f'Błąd podczas smoke-run: {e}')

    else:
        print('\nUWAGA: Moduł detektora jest jeszcze w fazie szkicu. Nie wykonano rzeczywistej detekcji.')


if __name__ == '__main__':
    main()
