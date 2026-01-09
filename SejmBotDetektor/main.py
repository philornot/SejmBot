"""
Entry point for SejmBotDetektor
AI-powered humor detection.
"""

import argparse
from pathlib import Path
from typing import Optional, Sequence

from SejmBotDetektor.config import get_detector_settings


def create_parser():
    parser = argparse.ArgumentParser(
        description='SejmBotDetektor — wykrywanie i ocena humoru w stenogramach',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument('--input-dir', type=str, help='Katalog z plikami transkryptów')
    parser.add_argument('--output-dir', type=str, help='Katalog do zapisu wyników')
    parser.add_argument('--max-statements', type=int, help='Maksymalna liczba wypowiedzi do przetworzenia')
    parser.add_argument('--test-mode', action='store_true', help='Tryb testowy — ograniczone zachowanie')

    # NEW: AI evaluation flags
    parser.add_argument('--ai-evaluate', action='store_true',
                        help='🤖 Użyj AI (OpenAI/Claude) do oceny humoru fragmentów')
    parser.add_argument('--ai-provider', choices=['openai', 'claude', 'auto'], default='auto',
                        help='Preferowany provider AI (auto = fallback)')
    parser.add_argument('--ai-min-score', type=float, default=1.0,
                        help='Minimalny score fragmentu do oceny AI (oszczędność API calls)')
    parser.add_argument('--top-n', type=int, default=100,
                        help='Oceń tylko top N fragmentów (oszczędność kosztów)')

    parser.add_argument('--version', action='version', version='SejmBotDetektor 0.2.0-AI')

    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = create_parser()
    args = parser.parse_args(argv)

    settings = get_detector_settings()

    input_dir = Path(args.input_dir) if args.input_dir else settings.input_dir
    output_dir = Path(args.output_dir) if args.output_dir else settings.output_dir
    max_statements = args.max_statements if args.max_statements is not None else settings.max_statements
    test_mode = args.test_mode or settings.test_mode

    # NEW: AI evaluation settings
    ai_evaluate = args.ai_evaluate
    ai_provider = args.ai_provider
    ai_min_score = args.ai_min_score
    top_n = args.top_n

    # Setup
    print('SejmBotDetektor — uruchamiam pipeline detektora')
    if ai_evaluate:
        print('🤖 AI evaluation ENABLED')
        print(f'   Provider: {ai_provider}')
        print(f'   Min score: {ai_min_score}')
        print(f'   Top N: {top_n}')

    print(f'  input_dir:  {input_dir}')
    print(f'  output_dir: {output_dir}')
    print(f'  max_statements: {max_statements}')

    try:
        output_dir.mkdir(parents=True, exist_ok=True)
    except OSError:
        print(f'Nie można utworzyć katalogu output: {output_dir}')
        return 1

    # Run pipeline
    def _run_pipeline(use_test_fixture: bool = False) -> None:
        import json
        from SejmBotDetektor import preprocessing
        from SejmBotDetektor import keyword_scoring
        from SejmBotDetektor import fragment_extraction
        from SejmBotDetektor import serializers

        # NEW: Initialize AI evaluator if requested
        ai_evaluator = None
        if ai_evaluate:
            try:
                from SejmBotDetektor.ai_evaluator import AIEvaluator
                print('🤖 Inicjalizacja AI evaluator...')

                config = {'primary_api': ai_provider} if ai_provider != 'auto' else {}
                ai_evaluator = AIEvaluator(config)
                print(f'✓ AI evaluator ready (cache: {len(ai_evaluator.cache)} entries)')
            except ImportError as e:
                from SejmBotDetektor import ai_evaluator as _ai_mod
                AIEvaluator = None  # zapewnia istnienie symbolu w tej gałęzi
                print(f'⚠️  AI evaluation disabled - missing dependencies: {e}')
                print('   Install: pip install openai anthropic')
                ai_evaluator = None
            except Exception as e:
                print(f'⚠️  AI evaluator init failed: {e}')
                ai_evaluator = None  # wyłącz AI, kontynuuj bez oceny AI

        input_paths = []
        if not use_test_fixture and input_dir and input_dir.exists() and input_dir.is_dir():
            json_files = list(input_dir.glob('*.json'))
            input_paths.extend(json_files)

        if not input_paths:
            # Fallback: search for Scraper output
            repo_root = Path(__file__).resolve().parents[1]
            candidate_dirs = [repo_root / 'data_sejm', repo_root / 'data']
            found = []
            for cd in candidate_dirs:
                if cd.exists() and cd.is_dir():
                    found.extend([p for p in cd.rglob('*.json') if 'detector' not in str(p).lower()])
            found = sorted(found)
            if found:
                input_paths.extend(found)
            else:
                # Use fixture
                fixture_path = Path(__file__).parent / 'fixtures' / 'transcript_sample.json'
                if fixture_path.exists():
                    input_paths.append(fixture_path)
                else:
                    print('Brak plików wejściowych. Kończę.')
                    return

        # Load keywords
        kws_path = Path(__file__).parent / 'keywords' / 'keywords.json'
        try:
            keywords = keyword_scoring.load_keywords_from_json(str(kws_path))
        except Exception:
            print(f'Nie można wczytać słów kluczowych z {kws_path}')
            keywords = [{'keyword': 'humor', 'weight': 1.0}, {'keyword': 'żart', 'weight': 2.0}]

        # Process files
        for file_p in input_paths:
            try:
                with open(file_p, 'r', encoding='utf-8') as fh:
                    data = json.load(fh)
            except (OSError, json.JSONDecodeError) as e:
                print(f'Nie można wczytać pliku {file_p}: {e}')
                continue

            statements = data.get('statements') or data
            if isinstance(statements, dict) and 'statements' in statements:
                statements = statements.get('statements', [])
            if not isinstance(statements, list):
                print(f'Nie rozpoznano listy wypowiedzi w pliku {file_p}')
                continue

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

            # Sort fragments by score
            all_fragments.sort(key=lambda x: x.get('score', 0), reverse=True)

            print(f'\n📊 Znaleziono {len(all_fragments)} fragmentów')

            # NEW: AI evaluation
            if ai_evaluate and ai_evaluator and all_fragments:
                print(f'\n🤖 URUCHAMIAM AI EVALUATION')
                print(f'   Filtr: score >= {ai_min_score}')
                print(f'   Limit: top {top_n} fragmentów')

                # Filter and limit
                fragments_for_ai = [
                    f for f in all_fragments
                    if f.get('score', 0) >= ai_min_score
                ][:top_n]

                print(f'   Do oceny: {len(fragments_for_ai)} fragmentów')

                if fragments_for_ai:
                    # Evaluate with AI
                    evaluated_fragments = ai_evaluator.evaluate_fragments_batch(fragments_for_ai)

                    # Replace with evaluated versions
                    all_fragments = evaluated_fragments + [
                        f for f in all_fragments if f not in fragments_for_ai
                    ]

                    # Stats
                    funny_count = sum(
                        1 for f in evaluated_fragments
                        if f.get('ai_evaluation', {}).get('is_funny')
                    )
                    print(f'\n✨ WYNIKI AI:')
                    print(f'   Śmieszne: {funny_count}/{len(evaluated_fragments)}')
                    print(f'   Cache hit rate: {ai_evaluator.get_stats()["cache_size"]}/{len(evaluated_fragments)}')

            results = {
                'source_file': str(file_p),
                'n_statements': len(statements),
                'n_processed': len(stmts_to_process),
                'n_fragments': len(all_fragments),
                'fragments': all_fragments,
            }

            # Add AI stats if used
            if ai_evaluate and ai_evaluator:
                results['ai_stats'] = ai_evaluator.get_stats()

            try:
                out_path = serializers.dump_results(results, base_dir=str(output_dir))
                print(f'\n💾 Zapisano wyniki do: {out_path}')
            except Exception as e:
                print(f'Nie udało się zapisać wyników dla {file_p}: {e}')

            if use_test_fixture:
                break

    try:
        if test_mode:
            print('\nTRYB TESTOWY: uruchamiam pipeline detektora (diagnostyka)')
            _run_pipeline(use_test_fixture=True)
        else:
            print('\nUruchamiam pipeline detektora (normalny tryb)')
            _run_pipeline(use_test_fixture=False)
    except Exception as e:
        print(f'Błąd podczas uruchamiania pipeline detektora: {e}')
        return 1

    return 0


if __name__ == '__main__':
    import sys

    sys.exit(main())
