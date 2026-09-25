"""Re-verify raw_bundle_c2.json from the branch copy, not from memory.

Downloads the bundle blob as it sits on `commander/control`, re-decodes every member and recomputes
size / sha256 / git blob sha1, then compares against what the bundle itself claims. A verifier can run
this file as-is; it writes nothing except the report.
"""
from __future__ import annotations

import base64
import hashlib
import json
import pathlib
import sys
import urllib.request

B = pathlib.Path('D:/moodle/_hjp3_0300c2_0925')
TOK = pathlib.Path('D:/moodle/_qoder_recovery_20260919/.api_tok_20260920').read_text(
    encoding='utf-8').strip()
API = 'https://api.github.com/repos/Canshu-King/CityNexus'
BRANCH = 'commander/control'
PREFIX = 'evidence/ord0300-c2-pairing-hjp3'


def api(path):
    r = urllib.request.Request(API + path)
    r.add_header('Authorization', 'Bearer ' + TOK)
    r.add_header('Accept', 'application/vnd.github+json')
    r.add_header('User-Agent', 'hjp3-0300c2-bundle-check')
    with urllib.request.urlopen(r, timeout=300) as f:
        return json.loads(f.read().decode())


tip = api('/git/ref/heads/' + BRANCH)['object']['sha']
entries = api('/git/trees/' + tip + '?recursive=1')['tree']
hit = [e for e in entries if e['path'] == PREFIX + '/raw_bundle_c2.json']
if not hit:
    raise SystemExit('the bundle is not on the branch yet: %s/raw_bundle_c2.json' % PREFIX)
obj = api('/git/blobs/' + hit[0]['sha'])
raw = base64.b64decode(obj['content'])
branch_blob_ok = hashlib.sha1(b'blob %d\0' % obj['size'] + raw).hexdigest() == hit[0]['sha']
body = json.loads(raw.decode('utf-8'))
bad, checked = [], 0
for name, m in body['members'].items():
    d = base64.b64decode(m['base64'])
    checked += 1
    if len(d) != m['size']:
        bad.append((name, 'size'))
    if hashlib.sha256(d).hexdigest() != m['sha256_64_hex']:
        bad.append((name, 'sha256'))
    if hashlib.sha1(b'blob %d\0' % len(d) + d).hexdigest() != m['blob_sha1_40_hex']:
        bad.append((name, 'blob'))
local = B / 'raw_bundle_c2.json'
same_as_local = hashlib.sha256(raw).hexdigest() == hashlib.sha256(local.read_bytes()).hexdigest()
out = {'ran_at_local': __import__('time').strftime('%Y-%m-%dT%H:%M:%S%z'),
       'branch_tip': tip, 'remote_path': PREFIX + '/raw_bundle_c2.json',
       'blob_on_branch_40_hex': hit[0]['sha'], 'bytes_on_branch': obj['size'],
       'blob_sha1_recomputes_from_downloaded_bytes': branch_blob_ok,
       'byte_identical_to_my_local_bundle': same_as_local,
       'members_listed': len(body['members']), 'members_checked': checked,
       'members_that_do_not_match_their_own_record': bad,
       'verdict': 'BUNDLE_VERIFIED' if (branch_blob_ok and same_as_local and not bad) else 'BUNDLE_BROKEN'}
(B / 'bundle_check_c2.json').write_text(json.dumps(out, ensure_ascii=False, indent=1),
                                        encoding='utf-8', newline='\n')
print(json.dumps(out, ensure_ascii=False, indent=1))
sys.exit(0 if out['verdict'] == 'BUNDLE_VERIFIED' else 3)
