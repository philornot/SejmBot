"""Konfiguracja dla SejmBotDetektor

Prosty helper zwracający domyślne ustawienia. Używaj `get_detector_settings()`
zamiast hardcodowania wartości w kodzie.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class DetectorSettings:
    input_dir: Path = Path('data')
    output_dir: Path = Path('detector_results')
    max_statements: int = 100
    test_mode: bool = False


def get_detector_settings() -> DetectorSettings:
    """Zwraca domyślną konfigurację detektora.

    Można ją rozszerzyć, aby wczytywać `.env` lub `get_settings()` z SejmBotScraper.
    """
    return DetectorSettings()
