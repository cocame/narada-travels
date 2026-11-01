#!/usr/bin/env python3
"""Вносит переводы из _en/tr/*.json ({номер строки: перевод}) в _en/strings.json."""
import glob, json, os
here = os.path.dirname(os.path.abspath(__file__))
p = os.path.join(here, 'strings.json')
rows = json.load(open(p, encoding='utf-8'))
n = 0
for f in sorted(glob.glob(os.path.join(here, 'tr', '*.json'))):
    for k, v in json.load(open(f, encoding='utf-8')).items():
        if rows[int(k)][1] != v: rows[int(k)][1] = v; n += 1
with open(p, 'w', encoding='utf-8') as f:
    f.write('[\n' + ',\n'.join(json.dumps(r, ensure_ascii=False) for r in rows) + '\n]\n')
print('обновлено переводов:', n, '· без перевода:', sum(1 for r in rows if not r[1]))
