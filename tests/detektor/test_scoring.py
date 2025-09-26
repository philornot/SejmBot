import json
import sys
from pathlib import Path

# ensure repository root is on sys.path so tests can import SejmBotDetektor
REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from SejmBotDetektor.keyword_scoring import score_segments, load_keywords_from_json


FIXTURES_DIR = Path(__file__).resolve().parents[1] / 'fixtures'


def load_transcripts():
    p = FIXTURES_DIR / 'transcripts_example.json'
    with open(p, 'r', encoding='utf-8') as fh:
        data = json.load(fh)
    # data expected to be a list of statements or proceedings with 'text' fields
    # For this test we'll extract a list of statement texts
    texts = []
    # Support common fixture shapes:
    # 1) top-level list of items with 'text' keys
    # 2) top-level dict with 'statements' -> list of {'text': ...}
    if isinstance(data, list):
        for item in data:
            if isinstance(item, dict) and 'text' in item:
                texts.append(item['text'])
    elif isinstance(data, dict):
        if 'statements' in data and isinstance(data['statements'], list):
            for s in data['statements']:
                if isinstance(s, dict) and 'text' in s:
                    texts.append(s['text'])
    return texts


def test_scoring_top_result_contains_expected_keyword():
    texts = load_transcripts()
    assert texts, 'No texts loaded from fixture'

    kw_path = Path('SejmBotDetektor') / 'keywords' / 'keywords.json'
    keywords = load_keywords_from_json(str(kw_path))

    scored = score_segments(texts, keywords)

    # basic assertions
    assert isinstance(scored, list)
    assert all('segment' in s and 'score' in s and 'matches' in s for s in scored)

    # find first non-zero score
    non_zero = [s for s in scored if s['score'] > 0]
    # This test expects that at least one segment matches configured keywords
    assert non_zero, 'Expected at least one segment with non-zero score'

    top = non_zero[0]
    # ensure matches list is not empty and contains known keywords from our sample keywords.json
    assert top['matches'], 'Top result should contain matches'
    # check that at least one of the match keywords is present in the keywords file
    kw_set = {k['keyword'] for k in keywords}
    assert any(m['keyword'] in kw_set for m in top['matches'])
