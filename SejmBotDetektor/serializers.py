"""Serialization helpers for SejmBotDetektor.

Provides a thin wrapper around the project's FileManagerInterface to save
detector results into the repository's data directories. Uses lazy imports
to avoid circular dependencies.
"""
from datetime import datetime
from typing import Any, Dict
import re
from pathlib import Path


def _init_file_manager(base_dir: str | None = None):
    # lazy import to avoid circular imports
    from SejmBotScraper.storage.file_manager import FileManagerInterface

    return FileManagerInterface(base_dir)


def _safe_filename(s: str) -> str:
    """Sanityzuj string na bezpieczną nazwę pliku (usuń spacje i niedozwolone znaki)."""
    if not s:
        return ''
    s = str(s)
    # keep only alnum, dash, underscore and dot
    s = re.sub(r'[^A-Za-z0-9._-]+', '_', s)
    return s.strip('_')


def dump_results(results: Dict[str, Any], base_dir: str | None = None, filename: str | None = None, add_metadata: bool = True) -> str:
    """Dump results dict using FileManagerInterface into detector results folder.

    Returns the path to written file as string.
    """
    fm = _init_file_manager(base_dir)

    base = fm.get_base_directory()
    detector_dir = base / 'detector'
    detector_dir.mkdir(parents=True, exist_ok=True)

    if filename is None:
        # try to derive a readable name from the source filename if present
        src = results.get('source_file') if isinstance(results, dict) else None
        src_name = ''
        try:
            if src:
                src_name = Path(src).stem
        except Exception:
            src_name = ''
        src_name = _safe_filename(src_name)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
        if src_name:
            filename = f'results_{src_name}_{timestamp}.json'
        else:
            filename = f'results_{timestamp}.json'

    filepath = detector_dir / filename

    success = fm.save_json(filepath, results, add_metadata=add_metadata)
    if success:
        return str(filepath)
    raise RuntimeError('Failed to save results')


__all__ = ['dump_results']
