import sys
from pathlib import Path
import json

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from SejmBotDetektor import preprocessing as pp
from SejmBotDetektor import keyword_scoring as ks
from SejmBotDetektor import fragment_extraction as fe


def test_end_to_end_pipeline_on_fixture(tmp_path):
    """End-to-end: clean -> split -> score -> extract (one statement from fixture)

    Asserts presence of expected keys in output fragments and that at least one
    matched keyword from real keywords appears in fragments.
    """
    # Canonical fixture used by tests
    fixtures_p = REPO_ROOT / 'tests' / 'fixtures' / 'transcripts_example.json'
    if not fixtures_p.exists():
        import pytest

        pytest.skip(f'Brak pliku fixture {fixtures_p} — upewnij się, że fixtures są w tests/fixtures')

    data = json.loads(fixtures_p.read_text(encoding='utf-8'))

    assert 'statements' in data and data['statements'], 'Fixture must contain statements'

    # pick a statement that contains a keyword from SejmBotDetektor/keywords/keywords.json
    stmt = data['statements'][2]  # third statement contains 'Śmieszny' according to fixture

    # Step 1: clean HTML
    cleaned = pp.clean_html(stmt.get('text', ''))
    assert cleaned, 'Cleaned text should not be empty'

    # Step 2: split into segments (sentences)
    segments = pp.split_into_sentences(cleaned, max_chars=300)
    assert isinstance(segments, list) and segments, 'Expected non-empty list of segments'

    # Step 3: score segments using real keywords file
    kw_path = Path('SejmBotDetektor') / 'keywords' / 'keywords.json'
    keywords = ks.load_keywords_from_json(str(kw_path))
    # score_segments accepts list[str] or list[dict]; wrap segments as dicts to satisfy typing and
    # to preserve original segment metadata shape
    segments_for_scoring = [{'text': s} for s in segments]
    scored = ks.score_segments(segments_for_scoring, keywords)
    assert isinstance(scored, list), 'Scoring must return a list'

    # Step 4: extract fragments from scored results
    # Build a minimal original_statement dict expected by extract_fragments
    original_stmt = {'num': stmt.get('num'), 'text': stmt.get('text')}
    frags = fe.extract_fragments(scored, original_stmt, context_sentences=1, max_length=400)

    assert isinstance(frags, list), 'extract_fragments must return a list'
    assert frags, 'Expected at least one fragment to be extracted'

    f = frags[0]
    # check presence of required fields
    for key in ('statement_id', 'start_offset', 'end_offset', 'text', 'score', 'matched_keywords'):
        assert key in f, f'Missing expected field in fragment: {key}'

    # matched_keywords should be a list (may be empty if scoring missed)
    assert isinstance(f['matched_keywords'], list), 'matched_keywords must be a list'

    # Ensure at least one of the keywords from keywords.json is present in matched keywords
    kw_set = {k['keyword'] for k in keywords}
    frag_kw_set = {m['keyword'] for m in f['matched_keywords']}
    assert frag_kw_set & kw_set, 'Expected fragment to contain at least one known keyword match'
