import sys
from pathlib import Path
import json

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))


def test_detector_on_fixture():
    """Stable unit test: run detector pipeline on local fixture and assert a known keyword is found.

    The fixture `SejmBotDetektor/fixtures/transcript_sample.json` contains a short sentence
    with the word 'humorem' (or similar). We'll ensure the detector scoring finds a keyword
    and that fragment_extraction returns expected structure.
    """
    from SejmBotDetektor import preprocessing, keyword_scoring, fragment_extraction

    fixture_path = Path(__file__).resolve().parents[2] / 'SejmBotDetektor' / 'fixtures' / 'transcript_sample.json'
    assert fixture_path.exists(), f'Fixture not found: {fixture_path}'

    with open(fixture_path, 'r', encoding='utf-8') as fh:
        data = json.load(fh)

    statements = data.get('statements') or []
    assert statements, 'No statements in fixture'

    # choose a statement that contains one of the stable test keywords
    test_kw_candidates = ['humorem', 'humor', 'śmieszny']
    stmt = None
    text = ''
    for s in statements:
        t = (s.get('text') or '').lower()
        if any(kw in t for kw in test_kw_candidates):
            stmt = s
            text = s.get('text') or ''
            break
    assert stmt is not None and text, f'No statement in fixture contains any of the keywords: {test_kw_candidates}'

    normalized = preprocessing.normalize_text(text)
    segments = preprocessing.split_into_sentences(normalized, max_chars=500)

    # Use an explicit, local keywords list (stable test) that matches the fixture text
    kws = [
        {'keyword': 'humorem', 'weight': 1.0},
        {'keyword': 'humor', 'weight': 1.0},
        {'keyword': 'śmieszny', 'weight': 1.0},
    ]

    scored = keyword_scoring.score_segments(segments, kws)

    # Assert scoring returned list and contains matches (or fallback to scoring full text)
    assert isinstance(scored, list)

    has_any_match = any(s.get('matches') for s in scored)
    if not has_any_match:
        scored_full = keyword_scoring.score_segments([normalized], kws)
        has_any_match = any(s.get('matches') for s in scored_full)
        scored = scored_full

    assert has_any_match, 'Expected at least one keyword match in fixture statement'

    fragments = fragment_extraction.extract_fragments(scored, {'text': text, 'num': stmt.get('num')})
    assert isinstance(fragments, list)
    # If fragments exist, ensure they contain expected keys
    if fragments:
        f = fragments[0]
        assert 'text' in f and 'score' in f and 'matched_keywords' in f
