import json
import re
from pathlib import Path

p = Path(r"C:\Users\filip\PycharmProjects\SejmBot\data_sejm\detector\results_20250926_222615.json")
obj = json.loads(p.read_text(encoding='utf-8'))
frags = obj.get('data', {}).get('fragments', [])

mismatches = []
for i, f in enumerate(frags[:200]):
    score = float(f.get('score', 0.0))
    mk = f.get('matched_keywords', [])
    sum_meta = 0.0
    sum_counttext = 0.0
    for m in mk:
        try:
            cnt = float(m.get('count', 0))
            wt = float(m.get('weight', 0.0))
        except Exception:
            cnt = float(m.get('count', 0) or 0)
            wt = float(m.get('weight', 0.0) or 0.0)
        sum_meta += cnt * wt
        # count occurrences in fragment text (case-insensitive)
        kw = str(m.get('keyword', '')).lower()
        try:
            occ = len(re.findall(r"\b" + re.escape(kw) + r"\b", f.get('text','').lower()))
        except re.error:
            occ = f.get('text','').lower().count(kw)
        sum_counttext += occ * wt

    if abs(score - sum_meta) > 1e-6 or abs(score - sum_counttext) > 1e-6:
        mismatches.append((i, f.get('statement_id'), score, sum_meta, sum_counttext, f.get('text','')[:120]))

print(f'Total fragments: {len(frags)}')
print(f'Mismatches found: {len(mismatches)}')
for idx, sid, score, meta, counted, text in mismatches[:50]:
    print(idx, sid, 'score=', score, 'meta=', meta, 'counted=', counted, 'text=', repr(text))

# print aggregate stats for top scores
frags_sorted = sorted(frags, key=lambda x: float(x.get('score',0)), reverse=True)
print('\nTop 10 fragments by score:')
for f in frags_sorted[:10]:
    print(f.get('statement_id'), f.get('score'), f.get('matched_keywords'))

