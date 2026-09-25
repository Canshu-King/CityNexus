"""ORD-0300: is there already a bundle built from the ORD-0280 frontend? Search bounded roots for the two
literals that only exist after that change, printing what was looked at so a zero is not a guess."""
from __future__ import annotations

import hashlib
import pathlib
import re
import sys

MARKERS = ['这台设备自己的读数（服务器没给句子）', 'agent/commands -> HTTP']
ROOTS = [p for p in [
    pathlib.Path('D:/moodle/_qoder_preview_20260920'),
    pathlib.Path('D:/moodle/_qoder_integration_20260919/frontend'),
    pathlib.Path('D:/moodle/_qoder_b_lane_20260923'),
    pathlib.Path('D:/moodle/_qoder_b_landing_20260923'),
    pathlib.Path('D:/moodle/_qoder_wt_45b0a5e/frontend'),
    pathlib.Path('D:/moodle/CityNexus/frontend'),
    pathlib.Path('D:/moodle/_hjp3_0300_0925/snap/frontend'),
] if p.exists()]

found = []
looked = []
for root in ROOTS:
    for assets in sorted(root.rglob('assets')):
        if not assets.is_dir() or 'node_modules' in assets.parts:
            continue
        for js in sorted(assets.glob('index-*.js')):
            try:
                txt = js.read_text(encoding='utf-8', errors='replace')
            except Exception:
                continue
            hits = [m for m in MARKERS if m in txt]
            looked.append({'file': str(js), 'bytes': js.stat().st_size,
                           'sha256': hashlib.sha256(js.read_bytes()).hexdigest()[:16],
                           'markers': len(hits)})
            if len(hits) == len(MARKERS):
                found.append(str(js))
print('roots searched', len(ROOTS), '| index assets looked at', len(looked))
for row in looked:
    print('   %-96s %9d B sha %s markers %d' % (row['file'][-96:], row['bytes'], row['sha256'], row['markers']))
print('bundles containing BOTH ORD-0280 markers:', found or 'NONE')
pathlib.Path('D:/moodle/_hjp3_0300_0925/bundle_hunt.json').write_text(
    __import__('json').dumps({'roots': [str(r) for r in ROOTS], 'looked': looked, 'matches': found,
                             'markers': MARKERS,
                             'coverage': 'NOT EXHAUSTIVE - these roots only; a build in another lane\'s private '
                                         'directory would not be seen here'}, ensure_ascii=False, indent=1),
    encoding='utf-8')
