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
            else:
                print('\nSMOKE-RUN: nie znaleziono przykładowego pliku JSON do wczytania')
        except Exception as e:
            print(f'Błąd podczas smoke-run: {e}')

    else:
        print('\nUWAGA: Moduł detektora jest jeszcze w fazie szkicu. Nie wykonano rzeczywistej detekcji.')


if __name__ == '__main__':
    main()
