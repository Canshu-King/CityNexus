"""Which bundle did I actually walk, and can that still be shown after I overwrote my own first record of it?

Self-fault that produced this file: after the five cells were done I re-ran `r6_gen_check.py` to see whether the
chain had re-cut, and that instrument writes to its own output name - so the walk-time copy of its rows (the ones
that showed BOTH entries serving the same bytes at the same minute) was replaced by the later reading, in which the
public entry was already answering 530. A judgment computed from the newer file then read "the two entries do not
serve the same bytes", which describes the tunnel's state at 18:1x, not my walk.

What is recoverable without touching the phone chain again: every browser pass stored the asset URL it loaded, so
the bundle name under test is on record; and the bundle is still on the local hop, so its bytes and sha256 can be
re-read now and pinned against that name. This file writes exactly that witness, and says what it is not.

Read-only GETs; 0 clicks; 0 writes anywhere on the chain.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import time
import urllib.request

OUT = pathlib.Path('D:/moodle/_hjp3_b6a8_0926')
LOC = 'http://127.0.0.1:4781'
DIRECT = urllib.request.build_opener(urllib.request.ProxyHandler({}))

walk_urls = {}
for name in ('r6_wizard_create.json', 'r6_dest_block.json', 'r6_dest_block_r2.json',
              'r6_dest_block_r3.json'):
    d = json.loads((OUT / name).read_text(encoding='utf-8'))
    if d.get('served_asset'):
        walk_urls[name] = d['served_asset']
from_b = list(walk_urls.values())[0]
asset_path = '/' + from_b.split('.com/')[-1] if '.com/' in from_b else from_b

r = urllib.request.Request(LOC + asset_path)
r.add_header('User-Agent', 'hjp3-r6-walked-asset-witness')
t0 = time.time()
with DIRECT.open(r, timeout=60) as f:
    b = f.read()
    status, ctype = f.status, f.headers.get('content-type')
gc = json.loads((OUT / 'r6_gen_check.json').read_text(encoding='utf-8'))
loc_row = gc['entry_points'][0]['asset_row'] or {}
out = {'ran_at_local': time.strftime('%Y-%m-%dT%H:%M:%S%z'),
       'asset_path_recorded_by_the_browser_passes': asset_path,
       'recorded_by': walk_urls,
       're_read_over_the_local_hop': {'path': asset_path, 'http_status': status, 'content_type': ctype,
                                      'bytes': len(b), 'sha256': hashlib.sha256(b).hexdigest(),
                                      'elapsed_ms': int((time.time() - t0) * 1000)},
       'equals_the_local_row_of_the_later_generation_check': bool(
           loc_row.get('bytes') == len(b) and loc_row.get('body_sha256') == hashlib.sha256(b).hexdigest()),
       'public_entry_state_at_that_minute': gc['entry_points'][1]['shell'],
       'what_this_is_not': 'this re-read proves which bytes sit behind that name on the local hop now; it is not a '
                           'second reading of the public entry during the walk, and the walk-time public row was '
                           'overwritten by my own re-run of r6_gen_check.py - named as an instrument fault'}
(OUT / 'r6_walked_asset_witness.json').write_text(json.dumps(out, ensure_ascii=False, indent=1),
                                                 encoding='utf-8', newline='\n')
print(json.dumps({k: out[k] for k in ('asset_path_recorded_by_the_browser_passes', 're_read_over_the_local_hop',
                                      'equals_the_local_row_of_the_later_generation_check')},
                 ensure_ascii=False, indent=1))
