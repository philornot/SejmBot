import json
import os
import sys

# Ensure repo root on path
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from SejmBotDetektor.preprocessing import clean_html, normalize_text, split_into_sentences


def load_fixture():
    path = os.path.join(ROOT, 'tests', 'fixtures', 'transcripts_example.json')
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def test_integration_on_transcripts_fixture():
    data = load_fixture()
    statements = data.get('statements', [])
    assert len(statements) == 3

    # Process each statement and ensure functions behave as expected
    for stmt in statements:
        raw = stmt.get('text', '')
        cleaned = clean_html(raw)
        assert isinstance(cleaned, str) and len(cleaned) > 0

        norm = normalize_text(cleaned)
        # normalized text must be lowercased and not contain raw '<' or '>'
        assert norm == norm.lower()
        assert '<' not in norm and '>' not in norm

        segments = split_into_sentences(norm, max_chars=120)
        # Each segment should be non-empty and not exceed limit
        assert all(isinstance(s, str) and 0 < len(s) <= 120 for s in segments)
