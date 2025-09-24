"""Preprocessing utilities for SejmBotDetektor.

Zadanie: przygotować tekst (normalizacja, czyszczenie HTML, segmentacja)
bez użycia modeli AI.

Funkcje:
- normalize_text(text) -> str
- clean_html(html) -> str
- split_into_sentences(text, max_chars=500) -> List[str]
"""

from typing import List
import re
import html


def normalize_text(text: str) -> str:
    """Normalize text for downstream processing.

    - Lowercase (polskie znaki pozostają)
    - Strip leading/trailing whitespace
    - Collapse multiple whitespace to single space
    - Normalize Unicode NFKC form (if necessary)

    Args:
        text: wejściowy tekst

    Returns:
        Normalizowany tekst
    """
    if text is None:
        return ''

    # Ensure str
    t = str(text)

    # HTML unescape common entities
    t = html.unescape(t)

    # Replace ampersand with Polish ' i ' to avoid raw '&' in text
    t = t.replace('&', ' i ')

    # Normalize whitespace
    t = t.strip()
    t = re.sub(r"\s+", " ", t)

    # Lowercase (preserve Polish diacritics)
    t = t.lower()

    return t
    


def clean_html(html_content: str) -> str:
    """Remove HTML tags, scripts and styles and return plain text.

    Args:
        html_content: raw HTML

    Returns:
        Plain text with whitespace normalized
    """
    if not html_content:
        return ''

    # Remove script/style blocks
    text = re.sub(r'<script[^>]*>.*?</script>', ' ', html_content, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<style[^>]*>.*?</style>', ' ', text, flags=re.DOTALL | re.IGNORECASE)

    # Replace <br> and block tags with newlines
    text = re.sub(r'<br\s*/?>', '\n', text, flags=re.IGNORECASE)
    # fix: properly close the character class for h1-h6 and include li, ul, ol
    text = re.sub(r'</(p|div|h[1-6]|li|ul|ol)[^>]*>', '\n', text, flags=re.IGNORECASE)

    # Strip all tags
    text = re.sub(r'<[^>]+>', ' ', text)

    # Unescape HTML entities and normalize whitespace
    text = html.unescape(text)
    text = re.sub(r'\s+', ' ', text).strip()

    return text


def split_into_sentences(text: str, max_chars: int = 500) -> List[str]:
    """Split text into sentence-like segments and ensure each segment <= max_chars.

    Simple heuristic:
    - Split on sentence-ending punctuation (., !, ?) followed by whitespace and capital letter or EOL.
    - If a resulting segment is longer than max_chars, split it on commas or spaces to fit.

    Args:
        text: input plain text (should be pre-cleaned)
        max_chars: maximum characters per segment

    Returns:
        List of segments
    """
    if not text:
        return []

    t = normalize_text(text)

    # Basic sentence split (keep delimiters)
    parts = re.split(r'(?<=[\.\!\?])\s+', t)

    segments: List[str] = []

    for part in parts:
        part = part.strip()
        if not part:
            continue

        if len(part) <= max_chars:
            segments.append(part)
            continue

        # If too long, try to split by commas
        subparts = re.split(r',\s+', part)
        buffer = ''
        for sp in subparts:
            if not buffer:
                buffer = sp
            elif len(buffer) + 2 + len(sp) <= max_chars:
                buffer = buffer + ', ' + sp
            else:
                segments.append(buffer)
                buffer = sp

        if buffer:
            # If still too long, hard-split on spaces
            if len(buffer) <= max_chars:
                segments.append(buffer)
            else:
                # split by space into chunks
                words = buffer.split(' ')
                chunk = ''
                for w in words:
                    if not chunk:
                        chunk = w
                    elif len(chunk) + 1 + len(w) <= max_chars:
                        chunk = chunk + ' ' + w
                    else:
                        segments.append(chunk)
                        chunk = w
                if chunk:
                    segments.append(chunk)

    return segments
