import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

import json
import tempfile

from SejmBotDetektor import keyword_scoring as ks


def test_load_keywords_from_json_reads_file():
    p = Path('SejmBotDetektor') / 'keywords' / 'keywords.json'
    kws = ks.load_keywords_from_json(str(p))
    assert isinstance(kws, list)
    assert any(k['keyword'] == 'kryzys' for k in kws)


def test_case_insensitive_and_token_boundary_matching():
    keywords = [{'keyword': 'kryzys', 'weight': 2.0}, {'keyword': 'pandemia', 'weight': 1.5}]
    text = 'Kryzys i kryzysowy przypadek. pandemia.'
    counts = ks.match_keywords_in_text(text, keywords)
    # 'Kryzys' appears as a standalone twice? Actually 'kryzysowy' should NOT match due to token-boundary
    assert counts.get('kryzys', 0) == 1
    assert counts.get('pandemia', 0) == 1


def test_multiword_keyword_matching():
    keywords = [{'keyword': 'energetyczny kryzys', 'weight': 3.0}]
    text = 'Mówiono o energetyczny kryzys w regionie.'
    counts = ks.match_keywords_in_text(text, keywords)
    assert counts.get('energetyczny kryzys', 0) == 1


def test_score_segments_counts_and_dict_input():
    keywords = [{'keyword': 'inflacja', 'weight': 2.0}]
    segments = [{'text': 'Inflacja inflacja!'}, {'text': 'Brak tematu.'}]
    scored = ks.score_segments(segments, keywords)
    # first result should have score 4.0 (2 occurrences * weight 2.0)
    assert scored[0]['score'] == 4.0
    assert scored[0]['matches'][0]['count'] == 2


def test_score_sorting_descending():
    keywords = [{'keyword': 'a', 'weight': 1.0}, {'keyword': 'b', 'weight': 2.0}]
    segments = ['a a b', 'b', 'c']
    scored = ks.score_segments(segments, keywords)
    scores = [s['score'] for s in scored]
    assert scores == sorted(scores, reverse=True)


def test_empty_keywords_results_zero_scores():
    segments = ['jakikolwiek tekst', 'inny tekst']
    scored = ks.score_segments(segments, [])
    assert all(s['score'] == 0.0 for s in scored)


def test_loader_ignores_malformed_entries(tmp_path):
    # create a temporary keywords file with some bad entries
    p = tmp_path / 'kw.json'
    data = [
        {'keyword': 'ok', 'weight': 1.0},
        'not-a-dict',
        {'no_keyword': 'x', 'weight': 2.0}
    ]
    p.write_text(json.dumps(data, ensure_ascii=False))
    kws = ks.load_keywords_from_json(str(p))
    assert len(kws) == 1
    assert kws[0]['keyword'] == 'ok'
