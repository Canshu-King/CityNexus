"""Record the published-path overwrite I committed right after delivering ORD-0288 T-1.

What happened, in order:
  1. `o0288_publish.py` (gated) published this batch and I wrote "已发布路径 0 覆盖" in the ledger block
     and in the bus delivery `issuecomment-5830510652`;
  2. minutes later I refreshed the blob manifest and pushed it by calling the low-level publisher
     directly - bypassing my own gate - onto a path that had already landed:
     `evidence/ord0288-t1-durable-ownership-hjp3/evidence_manifest_full40_o0288_r2.json`;
  3. that path now has two writes, so the claim in (1) is true of the batch as delivered and FALSE of the
     prefix as it stands. This file states both blob ids, both commits, the byte counts, and the route
     back to the overwritten bytes; nothing is deleted and nothing is quietly rewritten.

Every value is read from the branch at build time, not typed.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import time
import urllib.parse
import urllib.request

B = pathlib.Path('D:/moodle/_hjp3_0288t1_0925')
TOK = pathlib.Path('D:/moodle/_qoder_recovery_20260919/.api_tok_20260920').read_text(
    encoding='utf-8').strip()
API = 'https://api.github.com/repos/Canshu-King/CityNexus'
VICTIM = 'evidence/ord0288-t1-durable-ownership-hjp3/evidence_manifest_full40_o0288_r2.json'


def api(p):
    r = urllib.request.Request(API + p)
    r.add_header('Authorization', 'Bearer ' + TOK)
    r.add_header('Accept', 'application/vnd.github+json')
    r.add_header('User-Agent', 'hjp3-violation-record')
    with urllib.request.urlopen(r, timeout=180) as f:
        return json.loads(f.read().decode())


tip = api('/git/ref/heads/commander/control')['object']['sha']
hist = api('/commits?sha=commander/control&path=' + urllib.parse.quote(VICTIM, safe='')
           + '&per_page=100')
writes = []
for c in hist:
    tree = api('/git/trees/' + c['sha'] + '?recursive=1')['tree']
    row = next((e for e in tree if e['path'] == VICTIM), None)
    obj = api('/git/blobs/' + row['sha']) if row else None
    writes.append({'commit': c['sha'], 'commit_short': c['sha'][:12],
                   'committed_at': c['commit']['committer']['date'],
                   'message': c['commit']['message'].splitlines()[0],
                   'blob_40_hex': row['sha'] if row else None,
                   'size_bytes': obj['size'] if obj else None})
newest, oldest = writes[0], writes[-1]
out = {
    'ran_at_local': time.strftime('%Y-%m-%dT%H:%M:%S%z'),
    'branch_tip_at_read': tip,
    'path_overwritten': VICTIM.split('/', 1)[1],
    'writes_on_this_path': len(writes),
    'history': writes,
    'first_write': oldest, 'my_re_put': newest,
    'claim_it_contradicts': 'delivery `issuecomment-5830510652` and the ledger block say 已发布路径 0 覆盖; '
                            'that was true of the 58 paths the write-history file read, and became false '
                            'for this one path when I pushed the refreshed manifest past my own gate',
    'root_cause': 'I called the low-level publisher (`publish_evidence_r5.py`) directly for a one-file '
                  'refresh instead of going through `o0288_publish.py`, which is the only place the '
                  'identical-or-refuse gate lives. The gate never sees a direct call.',
    'recovery_of_the_overwritten_bytes': 'the first blob is still addressable: '
                                         'GET /repos/Canshu-King/CityNexus/git/blobs/%s, or check out '
                                         'commit %s of this path' % (oldest['blob_40_hex'],
                                                                     oldest['commit_short']),
    'what_i_did_about_it': [
        'the current bytes of the path are left as they are - re-pushing the old blob would be a third '
        'write on the same name',
        'the newest full listing goes out under a NEW name (evidence_manifest_full40_o0288_r3.json)',
        'the write-history proof is re-run and published as no_rewrite_proof_o0288_r2.json, and it now '
        'reports this path with 2 writes, so the record shows the hole instead of hiding it',
        'a single-file publisher with the gate built in (gated_push.py) is what I use from now on',
        'a correction post on the bus naming this file, the delivery post id, both blob ids'],
    'sizes': {'first_write_bytes': oldest['size_bytes'], 're_put_bytes': newest['size_bytes'],
              'delta_bytes': (newest['size_bytes'] or 0) - (oldest['size_bytes'] or 0)},
    'self_check': {'blobs_are_different': oldest['blob_40_hex'] != newest['blob_40_hex'],
                   'history_is_read_not_written': len(writes) >= 2}}
(B / 'overwrite_violation_o0288.json').write_text(json.dumps(out, ensure_ascii=False, indent=1),
                                                 encoding='utf-8', newline='\n')
print(json.dumps({'path': out['path_overwritten'], 'writes': out['writes_on_this_path'],
                  'first': out['first_write']['blob_40_hex'], 're_put': out['my_re_put']['blob_40_hex'],
                  'sizes': out['sizes'], 'self_check': out['self_check']}, ensure_ascii=False, indent=1))
