"""Extraction of context fragments around keyword matches.

This module provides `extract_fragments(scores, original_statement, context_sentences=1, max_length=500)`
which returns list of fragments with metadata:
  { statement_id, start_offset, end_offset, text, score, matched_keywords }

Notes:
- `scores` is expected to be one of the outputs from `keyword_scoring.score_segments`.
- `original_statement` is a dict-like object representing the full statement and should contain
  'text' and optional 'id' or 'num' field.
"""

from typing import List, Dict, Any

from .preprocessing import clean_html, split_into_sentences, normalize_text
import re


def _get_statement_id(stmt: Dict[str, Any]) -> Any:
    return stmt.get("id") or stmt.get("num") or stmt.get("statement_id")


def extract_fragments(
    scores: List[Dict[str, Any]],
    original_statement: Dict[str, Any],
    context_sentences: int = 1,
    max_length: int = 500,
) -> List[Dict[str, Any]]:
    """Extracts fragments from original_statement around matched keywords in scores.

    Args:
        scores: list of scoring entries as returned by `score_segments` (for this statement)
        original_statement: dict containing at least 'text' and optional id fields
        context_sentences: number of sentences of context to include before/after match
        max_length: maximum allowed length of fragment text (characters)

    Returns:
        List of fragments: {statement_id, start_offset, end_offset, text, score, matched_keywords}
    """
    text_html = (
        original_statement.get("text") or original_statement.get("segment") or ""
    )
    # remove html to get plain text for offsets
    plain = clean_html(text_html)

    # Normalize cleaned text to match how split_into_sentences works
    # (it lowercases and replaces entities). We'll use the normalized text as the
    # base for offsets and returned fragment text to ensure consistency.
    plain_norm = normalize_text(plain)
    sentences = split_into_sentences(plain_norm, max_chars=max_length)
    plain_lower = plain_norm  # already normalized and lowercased

    fragments: List[Dict[str, Any]] = []

    # We expect scores to contain matches with 'keyword' and counts, but also 'segment' that equals original text
    # For each match in scores, determine which sentence contains the keyword and take context
    # Build a simple index of sentence start offsets
    offsets = []  # list of (start, end, sentence)
    cur = 0
    for s in sentences:
        # sentences returned by split_into_sentences are normalized/lowercased
        # so search in the lowercased full text to find accurate positions
        start = plain_lower.find(s, cur)
        if start == -1:
            # fallback: approximate by current cursor
            start = cur
        end = start + len(s)
        offsets.append((start, end, s))
        cur = end

    stmt_id = _get_statement_id(original_statement)

    # If no offsets (no sentences), consider the whole normalized text as one fragment
    if not offsets:
        fragments.append(
            {
                "statement_id": stmt_id,
                "start_offset": 0,
                "end_offset": len(plain_norm),
                "text": plain_norm,
                "score": 0.0,
                "matched_keywords": [],
            }
        )
        return fragments

    # Flatten all matched keywords from scores
    matched_keywords = []
    for s in scores:
        for m in s.get("matches", []):
            kw = m.get("keyword")
            if kw and kw not in matched_keywords:
                matched_keywords.append(kw)

    # For each sentence that contains any matched keyword, create a fragment with context
    for idx, (start, end, sent) in enumerate(offsets):
        # 'sent' is already normalized/lowercased by split_into_sentences
        sent_lower = sent
        # use token-boundary regex matching for keywords to avoid substring matches
        matched_here = False
        for kw in matched_keywords:
            try:
                if re.search(r"\b" + re.escape(kw.lower()) + r"\b", sent_lower, flags=re.UNICODE):
                    matched_here = True
                    break
            except re.error:
                # fallback to simple substring if regex fails for some keyword
                if kw.lower() in sent_lower:
                    matched_here = True
                    break
        if not matched_here:
            continue
            # compute context window
            from_idx = max(0, idx - context_sentences)
            to_idx = min(len(offsets) - 1, idx + context_sentences)

            frag_start = offsets[from_idx][0]
            frag_end = offsets[to_idx][1]

            # Slice from the original plain text to preserve casing
            # Use normalized text slice to match how sentences were found
            frag_text = plain_norm[frag_start:frag_end].strip()
            if len(frag_text) > max_length:
                frag_text = frag_text[:max_length].rsplit(" ", 1)[0]
                frag_end = frag_start + len(frag_text)

            # compute score as sum of scores entries (best-effort)
            total_score = sum(s.get("score", 0.0) for s in scores)

            fragments.append(
                {
                    "statement_id": stmt_id,
                    "start_offset": frag_start,
                    "end_offset": frag_end,
                    "text": frag_text,
                    "score": float(total_score),
                    "matched_keywords": matched_keywords,
                }
            )

    return fragments


__all__ = ["extract_fragments"]
