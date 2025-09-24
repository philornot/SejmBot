"""Entry point for SejmBotDetektor

CLI minimalny szkic — bez implementacji detekcji AI.
"""

import argparse
from pathlib import Path
from .config import get_detector_settings


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

    # Minimalny smoke-run: pokaż parametry i zakończ
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

    print('\nUWAGA: Moduł detektora jest jeszcze w fazie szkicu. Nie wykonano rzeczywistej detekcji.')


if __name__ == '__main__':
    main()
