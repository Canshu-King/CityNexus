"""Pre-flight every 40-hex in a block against the remote, before the commander's door rejects the whole file.

His applier fetches every branch and resolves each hex it finds; one unresolvable token bounces the block. So the
block builder is followed by this: extract every 40-hex from the block text, ask GitHub what it is (blob, then
commit), and refuse to call the block delivered until each one resolves. Read-only, and it never invents a name for
a token it cannot find.
"""
from __future__ import annotations

import importlib.util as iu
import json
import pathlib
import re
import sys
import time

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
OUT = pathlib.Path('D:/moodle/_hjp3_d3j0_0926')
SRC = pathlib.Path('D:/moodle/HJ-P3_evidence')
spec = iu.spec_from_file_location('pub', str(SRC / 'p3_publish.py'))
pub = iu.module_from_spec(spec)
spec.loader.exec_module(pub)
block = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else 'D:/moodle/_qoder_ledger_inbox/aad2d1f2_1900.md')
text = block.read_text(encoding='utf-8')
hexes = sorted(set(re.findall(r'\b[0-9a-f]{40}\b', text)))


def kind(sha):
    for route, label in (('/git/blobs/', 'blob'), ('/commits/', 'commit')):
        try:
            pub.api(route + sha)
            return label
        except Exception:  # noqa: BLE001
            continue
    return 'UNRESOLVED'


rows = {h: kind(h) for h in hexes}
bad = sorted([h for h, v in rows.items() if v == 'UNRESOLVED'])
out = {'ran_at_local': time.strftime('%Y-%m-%dT%H:%M:%S%z'), 'block': str(block),
       'block_bytes': block.stat().st_size, 'method': 'GET /git/blobs/<sha> then GET /commits/<sha> over the API; '
                                                      '0 local writes, 0 refs touched',
       'hexes_found': len(hexes), 'resolved': {h: rows[h] for h in hexes}, 'unresolved': bad,
       'verdict': {'every_hex_in_the_block_resolves': not bad}}
(OUT / 'r7_hex_preflight.json').write_text(json.dumps(out, ensure_ascii=False, indent=1),
                                                encoding='utf-8', newline='\n')
print(json.dumps({'hexes': len(hexes), 'unresolved': bad, 'kinds': sorted(set(rows.values()))},
                 ensure_ascii=False))
raise SystemExit(0 if not bad else 7)
