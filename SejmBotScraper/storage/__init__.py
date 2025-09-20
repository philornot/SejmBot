"""Moduł storage"""
try:
    from .file_manager import FileManagerInterface

    # Alias dla kompatybilności z starym kodem
    FileManager = FileManagerInterface

    __all__ = ['FileManagerInterface', 'FileManager']
except ImportError:
    # Fallback - prosta implementacja FileManager
    import json
    from pathlib import Path
    from datetime import datetime
    from typing import Dict, Optional, List, Union


    class FileManager:
        """Prosta implementacja FileManager jako fallback"""

        def __init__(self, base_dir: Optional[str] = None):
            self.base_dir = Path(base_dir or "data_sejm")

        def get_base_directory(self) -> Path:
            return self.base_dir

        def get_term_directory(self, term: int) -> Path:
            return self.base_dir / f"kadencja_{term:02d}"

        def get_proceeding_directory(self, term: int, proceeding_id: int, proceeding_info: Dict = None) -> Path:
            term_dir = self.get_term_directory(term)
            return term_dir / f"posiedzenie_{proceeding_id:03d}"

        def get_transcripts_directory(self, term: int, proceeding_id: int, proceeding_info: Dict = None) -> Path:
            proc_dir = self.get_proceeding_directory(term, proceeding_id, proceeding_info)
            return proc_dir / "transcripts"

        def save_proceeding_info(self, term: int, proceeding_id: int, proceeding_info: Dict) -> Optional[str]:
            try:
                proc_dir = self.get_proceeding_directory(term, proceeding_id, proceeding_info)
                proc_dir.mkdir(parents=True, exist_ok=True)

                info_file = proc_dir / "info_posiedzenia.json"
                with open(info_file, 'w', encoding='utf-8') as f:
                    json.dump(proceeding_info, f, ensure_ascii=False, indent=2)

                return str(info_file)
            except Exception:
                return None

        def save_proceeding_transcripts(self, term: int, proceeding_id: int, date: str,
                                        statements_data: Dict, proceeding_info: Dict,
                                        full_statements: Optional[List] = None) -> Optional[str]:
            try:
                transcripts_dir = self.get_transcripts_directory(term, proceeding_id, proceeding_info)
                transcripts_dir.mkdir(parents=True, exist_ok=True)

                transcript_file = transcripts_dir / f"transkrypty_{date}.json"

                save_data = {
                    'metadata': {
                        'term': term,
                        'proceeding_id': proceeding_id,
                        'date': date,
                        'saved_at': datetime.now().isoformat()
                    },
                    'original_data': statements_data,
                    'statements': full_statements or statements_data.get('statements', [])
                }

                with open(transcript_file, 'w', encoding='utf-8') as f:
                    json.dump(save_data, f, ensure_ascii=False, indent=2)

                return str(transcript_file)
            except Exception:
                return None

        def load_transcript_file(self, filepath: Union[str, Path]) -> Optional[Dict]:
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                return None

        def _calculate_duration(self, start_time: str, end_time: str) -> int:
            """Oblicza czas trwania w sekundach"""
            try:
                from datetime import datetime
                start = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                end = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
                return int((end - start).total_seconds())
            except Exception:
                return 0


    FileManagerInterface = FileManager
    __all__ = ['FileManager', 'FileManagerInterface']
