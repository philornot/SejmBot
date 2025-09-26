from pathlib import Path
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))


def test_dump_results_writes_file(tmp_path):
    # tmp_path will act as the repository base directory for FileManagerInterface
    from SejmBotDetektor.serializers import dump_results

    results = {'some': 'data'}

    # dump_results expects base_dir as a path string; pass tmp_path as str
    out = dump_results(results, base_dir=str(tmp_path), filename='test_results.json')

    p = Path(out)
    assert p.exists()

    content = json.loads(p.read_text(encoding='utf-8'))
    # FileManagerInterface.save_json wraps data under metadata/data by default
    assert 'metadata' in content or 'data' in content
