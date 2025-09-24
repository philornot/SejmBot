"""Konfiguracja dla SejmBotDetektor

Prosty helper zwracający domyślne ustawienia. Używaj `get_detector_settings()`
zamiast hardcodowania wartości w kodzie.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional
import os


@dataclass
class DetectorSettings:
    input_dir: Path = Path('data')
    output_dir: Path = Path('detector_results')
    max_statements: int = 100
    test_mode: bool = False


def _from_env() -> DetectorSettings:
    """Wczytuje ustawienia z zmiennych środowiskowych (prefiks DETECTOR_)."""
    input_dir = os.getenv('DETECTOR_INPUT_DIR')
    output_dir = os.getenv('DETECTOR_OUTPUT_DIR')
    max_statements = os.getenv('DETECTOR_MAX_STATEMENTS')
    test_mode = os.getenv('DETECTOR_TEST_MODE')

    return DetectorSettings(
        input_dir=Path(input_dir) if input_dir else DetectorSettings.input_dir,
        output_dir=Path(output_dir) if output_dir else DetectorSettings.output_dir,
        max_statements=int(max_statements) if max_statements and max_statements.isdigit() else DetectorSettings.max_statements,
        test_mode=(test_mode.lower() in ('1', 'true', 'yes', 'on')) if test_mode else DetectorSettings.test_mode,
    )


def get_detector_settings() -> DetectorSettings:
    """Zwraca konfigurację detektora.

    Najpierw próbuje pobrać ustawienia z `SejmBotScraper.config.settings.get_settings()`
    (jeśli pakiet jest dostępny). W przeciwnym razie używa zmiennych środowiskowych
    (prefiks `DETECTOR_`) lub wartości domyślnych.
    """
    try:
        # Try to reuse global settings from SejmBotScraper when available
        from SejmBotScraper.config.settings import get_settings as _get_settings

        settings = _get_settings()
        # Map a few useful values if present
        try:
            base_output = settings.get('scraping.base_output_dir')
        except Exception:
            base_output = None

        return DetectorSettings(
            input_dir=Path(base_output) if base_output else DetectorSettings.input_dir,
            output_dir=Path(base_output) if base_output else DetectorSettings.output_dir,
            max_statements=DetectorSettings.max_statements,
            test_mode=False,
        )
    except Exception:
        # Fallback to environment variables and defaults
        return _from_env()
