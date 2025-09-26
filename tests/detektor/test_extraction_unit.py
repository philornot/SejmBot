import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from SejmBotDetektor.fragment_extraction import extract_fragments


def test_extract_fragments_basic():
    stmt = {
        'num': 1,
        'text': 'To jest testowy tekst. Mamy też kryzys energetyczny i inflacja.'
    }

    # simulate scores: keyword 'kryzys' weight 2.0, 'inflacja' weight 1.5
    scores = [
        {'segment': stmt['text'], 'score': 0.0, 'matches': [
            {'keyword': 'kryzys', 'count': 1, 'weight': 2.0},
            {'keyword': 'inflacja', 'count': 1, 'weight': 1.5},
        ]}
    ]

    frags = extract_fragments(scores, stmt, context_sentences=1, max_length=200)
    assert isinstance(frags, list)
    assert frags, 'Expected at least one fragment'

    f = frags[0]
    # matched_keywords should contain entries for kryzys and inflacja
    kws = {m['keyword'] for m in f['matched_keywords']}
    assert 'kryzys' in kws
    assert 'inflacja' in kws

    # score should be sum of counts*weights = 1*2.0 + 1*1.5 = 3.5
    assert abs(f['score'] - 3.5) < 1e-6
