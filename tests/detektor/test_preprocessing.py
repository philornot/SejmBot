import sys
import os
import pytest

# Ensure repository root is on sys.path for imports when running pytest from IDE/CI
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from SejmBotDetektor.preprocessing import normalize_text, clean_html, split_into_sentences


def test_normalize_text_basic():
    s = "  To JEST   Przykład\nZ  nową linią &amp; encją  "
    out = normalize_text(s)
    assert 'to jest przykład' in out
    assert '&' not in out  # entity unescaped


def test_clean_html_basic():
    html = "<html><body><p>Witaj <b>świecie</b>!</p><script>var a=1;</script></body></html>"
    out = clean_html(html)
    assert 'witaj' in out.lower()
    assert 'script' not in out.lower()


def test_split_into_sentences_short_and_long():
    text = (
        "To jest pierwsze zdanie. "
        "To jest drugie zdanie, które zawiera dużo treści, "
        "i które może być dłuższe niż limit, więc musimy je podzielić odpowiednio. "
        "Krótka końcówka."
    )

    segments = split_into_sentences(text, max_chars=80)
    assert isinstance(segments, list)
    # Should produce at least 2 segments
    assert len(segments) >= 2
    # No segment longer than limit
    assert all(len(s) <= 80 for s in segments)
