"""ORD-0300 C2 challenge - stage 6b: pack the per-arm raw files into ONE published artefact.

Why a bundle and not 60 separate paths: every one of these files is a witness, not a verdict, and a
verifier only needs them together with the arm table in the receipt. Each member therefore carries its own
size, sha256 and git blob sha1 recomputed from the bytes that go in, and `c2_bundle_check.py` recomputes
them again from whatever is on the branch, so packing costs nothing in checkability.
"""
from __future__ import annotations

import base64
import hashlib
import json
import pathlib

BASE = pathlib.Path('D:/moodle/_hjp3_0300c2_0925')
GROUPS = {
    'arm': sorted(p.name for p in BASE.glob('arm_*C2-*.json')),
    'cell': sorted(p.name for p in BASE.glob('cell_*C2-*.json')),
    'teardown': sorted(p.name for p in BASE.glob('teardown_*.json')),
    'rig_state': sorted(p.name for p in BASE.glob('rig_state*.json')) + ['rig_pids.json'],
    'lock_log': sorted(p.name for p in BASE.glob('lock_*.log')),
    'face_log': sorted(p.name for p in BASE.glob('face_*.log')),
    'build_log': sorted(p.name for p in BASE.glob('build_*.log')),
    'proxy_log': ['proxy.log'],
    'arms_log': sorted(p.name for p in BASE.glob('arms_run*.log')),
}
body = {'order': 'ORD-0300 C2 challenge', 'lane': 'HJ-P3 aad2d1f2',
        'packed_at_local': __import__('time').strftime('%Y-%m-%dT%H:%M:%S%z'),
        'how_to_check': 'run instruments/c2_bundle_check.py: it reads this file back off the branch, '
                        're-decodes every member and recomputes size/sha256/blob sha1',
        'groups': {k: len(v) for k, v in GROUPS.items()}, 'members': {}}
missing = []
for group, names in GROUPS.items():
    for n in names:
        p = BASE / n
        if not p.exists():
            missing.append(n)
            continue
        d = p.read_bytes()
        body['members'][n] = {'group': group, 'size': len(d),
                              'sha256_64_hex': hashlib.sha256(d).hexdigest(),
                              'blob_sha1_40_hex': hashlib.sha1(b'blob %d\0' % len(d) + d).hexdigest(),
                              'base64': base64.b64encode(d).decode()}
out = BASE / 'raw_bundle_c2.json'
out.write_text(json.dumps(body, ensure_ascii=False, indent=1), encoding='utf-8', newline='\n')
# re-read what just landed and recompute, so the manifest of the bundle is not a claim about memory
back = json.loads(out.read_text(encoding='utf-8'))
bad = [n for n, m in back['members'].items()
       if hashlib.sha1(b'blob %d\0' % m['size'] + base64.b64decode(m['base64'])).hexdigest()
       != m['blob_sha1_40_hex'] or len(base64.b64decode(m['base64'])) != m['size']]
print('members=%d missing=%d bytes=%d' % (len(back['members']), len(missing), out.stat().st_size))
print('recomputed_from_disk_all_match =', not bad, '| mismatched:', bad)
print('groups:', json.dumps(back['groups']))
if missing:
    print('MISSING', missing)
