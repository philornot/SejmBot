"""Prosty moduł scoringu na bazie słów kluczowych.

Funkcje zapewniają case-insensitive, token-boundary dopasowanie słów kluczowych
i proste zsumowanie wag (weight * count) dla każdego segmentu.

Oczekiwany format `keywords` (lista obiektów) lub ścieżka do pliku JSON:
[
  {"keyword": "kryzys", "weight": 2.0},
  {"keyword": "pandemia", "weight": 1.5}
]

Główna funkcja:
- score_segments(segments, keywords) -> lista dictów z kluczami {segment, score, matches}

Uwagi:
- `segments` może być listą stringów lub listą słowników zawierających pole `text`.
- Dopasowanie odbywa się na granicach tokenów (\b) z re.IGNORECASE.
"""
from __future__ import annotations

import json
import re
from typing import List, Dict, Any, Union, Iterable


def load_keywords_from_json(path: str) -> List[Dict[str, Any]]:
    """Wczytuje listę słów kluczowych z pliku JSON.

    Zwraca listę obiektów {'keyword': str, 'weight': float}.
    """
    with open(path, 'r', encoding='utf-8') as fh:
        data = json.load(fh)
    # Minimalna walidacja
    out = []
    for item in data:
        if not isinstance(item, dict):
            continue
        kw = item.get('keyword')
        wt = item.get('weight', 1.0)
        if not kw:
            continue
        try:
            wt = float(wt)
        except Exception:
            wt = 1.0
        out.append({'keyword': str(kw), 'weight': wt})
    return out


def _ensure_keywords(keywords: Union[str, Iterable[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    """Normalizuje wejście keywords — przyjmuje ścieżkę lub listę.
    Zwraca listę {'keyword', 'weight'}.
    """
    if isinstance(keywords, str):
        return load_keywords_from_json(keywords)
    # assume iterable
    return [ {'keyword': str(it['keyword']), 'weight': float(it.get('weight', 1.0))} for it in keywords ]


def _compile_keyword_patterns(keywords: List[Dict[str, Any]]):
    """Zwraca listę tupli (keyword, weight, compiled_pattern).

    Kompiluje pattern z użyciem \b i re.IGNORECASE.
    """
    compiled = []
    for k in keywords:
        keyword = k['keyword'].strip()
        if not keyword:
            continue
        # escape to treat keyword literally
        pattern = re.compile(r"\b" + re.escape(keyword) + r"\b", flags=re.IGNORECASE | re.UNICODE)
        compiled.append((keyword, float(k.get('weight', 1.0)), pattern))
    return compiled


def match_keywords_in_text(text: str, keywords: Union[str, Iterable[Dict[str, Any]]]) -> Dict[str, int]:
    """Zwraca słownik {keyword: count} dla dopasowań w `text`.

    Dopasowanie jest case-insensitive i token-boundary.
    """
    kw_list = _ensure_keywords(keywords)
    patterns = _compile_keyword_patterns(kw_list)
    counts: Dict[str, int] = {}
    for keyword, _, pattern in patterns:
        matches = pattern.findall(text or '')
        cnt = len(matches)
        if cnt:
            counts[keyword] = cnt
    return counts


def score_segments(segments: List[Union[str, Dict[str, Any]]], keywords: Union[str, Iterable[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    """Oblicza score dla listy segmentów.

    Każdy wynikowy wpis to:
      { 'segment': <oryginalny segment>, 'score': float, 'matches': [ {keyword, count, weight}, ... ] }

    Wyniki są posortowane malejąco po `score`.
    """
    kw_list = _ensure_keywords(keywords)
    compiled = _compile_keyword_patterns(kw_list)

    results: List[Dict[str, Any]] = []
    for seg in segments:
        # obsłużemy zarówno string jak i dict z polem 'text'
        if isinstance(seg, str):
            text = seg
        elif isinstance(seg, dict):
            # prefer 'text' field, else try 'segment' or fallback to str(seg)
            text = seg.get('text') or seg.get('segment') or str(seg)
        else:
            text = str(seg)

        total = 0.0
        matches_list: List[Dict[str, Any]] = []
        for keyword, weight, pattern in compiled:
            cnt = len(pattern.findall(text or ''))
            if cnt:
                total += cnt * float(weight)
                matches_list.append({'keyword': keyword, 'count': cnt, 'weight': float(weight)})

        results.append({'segment': seg, 'score': float(total), 'matches': matches_list})

    # sort descending by score
    results.sort(key=lambda x: x['score'], reverse=True)
    return results


if __name__ == '__main__':
    # small smoke demonstration when uruchamiany ręcznie
    sample_segments = [
        'Dyskusja o kryzysie energetycznym i inflacji w kraju.',
        'Temat edukacji i zdrowia publicznego.'
    ]
    try:
        kws = load_keywords_from_json('SejmBotDetektor/keywords/keywords.json')
    except Exception:
        kws = [ {'keyword': 'kryzys', 'weight': 2.0}, {'keyword': 'inflacja', 'weight': 2.0} ]
    scored = score_segments(sample_segments, kws)
    for r in scored:
        print(r)
