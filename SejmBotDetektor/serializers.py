"""Serialization helpers for SejmBotDetektor.

Provides a thin wrapper around the project's FileManagerInterface to save
detector results into the repository's data directories. Uses lazy imports
to avoid circular dependencies.
"""
from datetime import datetime
from typing import Any, Dict


def _init_file_manager(base_dir: str | None = None):
    # lazy import to avoid circular imports
    from SejmBotScraper.storage.file_manager import FileManagerInterface

    return FileManagerInterface(base_dir)


def dump_results(results: Dict[str, Any], base_dir: str | None = None, filename: str | None = None, add_metadata: bool = True) -> str:
    """Dump results dict using FileManagerInterface into detector results folder.

    Returns the path to written file as string.
    """
    fm = _init_file_manager(base_dir)

    base = fm.get_base_directory()
    detector_dir = base / 'detector'
    detector_dir.mkdir(parents=True, exist_ok=True)

    if filename is None:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'results_{timestamp}.json'

    filepath = detector_dir / filename

    success = fm.save_json(filepath, results, add_metadata=add_metadata)
    if success:
        return str(filepath)
    raise RuntimeError('Failed to save results')


__all__ = ['dump_results']
