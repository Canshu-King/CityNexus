"""Durable read-only substitute for the DOM anchor probe that ran without persisting its stdout.

The single allowed re-run of the wizard (`r5_recheck.cjs`) recorded the attribute hits of the screen that follows
the press, but it computed the pre-press attribute scan and then dropped that field, and the separate DOM probe I
wrote afterwards printed before/after lists to my console only. The commander asked for the journey to be walked
ONCE on this generation, so I am not clicking through it a second time to make those two fields durable.

What I can do without touching the chain twice is ask the served bundle itself: a `data-testid` anchor name and the
two sentences the traveller reads are literals inside `index-D6IOFaQS.js`, so their presence, count and byte offset
are measurable by GET alone. That is weaker than a DOM reading and is labelled as such - it can show the anchor
ships in this generation, it cannot show when it mounts.

Boundaries: GET `/` and GET the one asset it names; 0 clicks; 0 writes; 0 credentials; no database; no deploy
action; the tunnel and :4782 are not contacted.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import re
import time
import urllib.request

OUT = pathlib.Path('D:/moodle/_hjp3_0323walk_0926')
CHAIN = 'http://127.0.0.1:4781'
ANCHORS = ('trial-create-error', 'trial-next-reason', 'trial-sticky-cta')
SENTENCES = ('这一步没有成功，行程还没有创建。', '服务器拒绝了这一步（HTTP ')
TESTID_RE = re.compile(r'data-testid')


def get(p):
    r = urllib.request.Request(CHAIN + p)
    r.add_header('User-Agent', 'hjp3-anchor-scan-readonly')
    t0 = time.time()
    with urllib.request.urlopen(r, timeout=60) as f:
        b = f.read()
        return {'path': p, 'http_status': f.status, 'content_type': f.headers.get('content-type'),
                'server_header': f.headers.get('server'), 'bytes': len(b),
                'body_sha256': hashlib.sha256(b).hexdigest(), 'elapsed_ms': int((time.time() - t0) * 1000),
                'body': b}


idx = get('/')
asset = (re.search(r'"(/assets/index-[^"]+\.js)"', idx['body'].decode('utf-8', 'replace')) or [None, None])[1]
js = get(asset) if asset else None
src = js['body'].decode('utf-8', 'replace') if js else ''
rc_all = json.loads((OUT / 'r5_recheck_raw.json').read_text(encoding='utf-8'))
rc = rc_all['binding']

anchors = {a: {'occurrences': src.count(a), 'first_byte_offset': src.find(a)} for a in ANCHORS}
sentences = {s: {'occurrences': src.count(s), 'first_byte_offset': src.find(s)} for s in SENTENCES}
out = {'ran_at_local': time.strftime('%Y-%m-%dT%H:%M:%S%z'), 'chain': CHAIN,
       'method': 'read-only GET of the served shell and of the single JS asset it names, then literal search over '
                 'those bytes; the wizard was NOT walked again in this run',
       'requests_made': 2, 'clicks': 0, 'writes': 0, 'credentials_sent': False,
       'shell': {k: idx[k] for k in ('path', 'http_status', 'content_type', 'server_header', 'bytes',
                                     'body_sha256', 'elapsed_ms')},
       'asset_named_by_the_served_page': asset,
       'asset': ({k: js[k] for k in ('path', 'http_status', 'content_type', 'server_header', 'bytes',
                                     'body_sha256', 'elapsed_ms')} if js else None),
       'asset_equals_what_my_click_pass_hashed': bool(js is not None
                                                      and js['bytes'] == rc['asset_bytes']
                                                      and js['body_sha256'] == rc['asset_sha256_64_hex']),
       'anchor_literals_in_the_served_bundle': anchors,
       'data_testid_attribute_literals_in_the_bundle': src.count('data-testid'),
       'failure_sentences_literals_in_the_served_bundle': sentences,
       'limit_named': 'these are bundle-level literal counts. They show the anchor names and the two sentences ship '
                      'inside this generation; they do NOT show when the anchor mounts in the DOM, which is the '
                      'field my click pass dropped and which is marked NOT_PERSISTED in the scored file',
       'dom_side_readings': {
           'anchors_seen_after_the_press': rc_all['cells']['C1_confirm_create']['attribute_hits'],
           'details_blocks_on_the_failure_screen': rc_all['cells']['C1_confirm_create']['details_count'],
           'anchors_seen_before_the_press': 'NOT_PERSISTED - computed by the click pass and dropped from its '
                                           'output file; the follow-up DOM probe printed to console only, so this '
                                           'field has no bytes to re-hash'}}
(OUT / 'r5_anchor_scan.json').write_text(json.dumps(out, ensure_ascii=False, indent=1),
                                         encoding='utf-8', newline='\n')
print(json.dumps({'asset': asset, 'same_bytes_as_my_click_pass': out['asset_equals_what_my_click_pass_hashed'],
                  'anchors': anchors, 'data_testid_count': out['data_testid_attribute_literals_in_the_bundle'],
                  'sentences': sentences}, ensure_ascii=False, indent=1))
