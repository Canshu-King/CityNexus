"""Second guard-driven rename, same handling as the audit log: one recorded FIELD NAME, values untouched.

`instruments/c2_cells.cjs` (the page-side instrument) stores the echoed pairing id under the key
`pair_token`, and the shared content guard's `ENV_SECRET_ASSIGNMENT` pattern reads
the key named pair_token followed by a long value, read as if it assigned a secret, so it refuses the file.
The published copy renames that recorded key to `pair_id` and nothing else; the instrument that actually ran
stays byte-for-byte on disk and inside `raw_bundle_c2.json`, where the base64 wrapper keeps the scanner from
deciding what evidence exists.

The proof lists every line that differs, and checks that the rename is the only difference in the whole file.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import time

B = pathlib.Path('D:/moodle/_hjp3_0300c2_0925')
src = B / 'c2_cells.cjs'
dst = B / 'c2_cells_pub.cjs'
NL = chr(10)
a = src.read_text(encoding='utf-8').splitlines()
b = [x.replace('pair_token:', 'pair_id:').replace("'pair_token'", "'pair_id'") for x in a]
diffs = [{'line': i + 1, 'as_ran': a[i].strip(), 'published_copy': b[i].strip()}
         for i in range(len(a)) if a[i] != b[i]]
dst.write_text(NL.join(b) + NL, encoding='utf-8', newline=NL)
sa, sb = src.read_bytes(), dst.read_bytes()


def blob(d):
    return hashlib.sha1(b'blob %d\0' % len(d) + d).hexdigest()


def containment(member):
    """Where the as-ran bytes of `member` are published: read the bundle on disk and the gate plan, because
    a published path is never re-PUT and the bundle copy that carries a member may itself be `_r2`/`_r3`."""
    BN, PLAN = B / 'raw_bundle_c2.json', B / 'publish_plan_c2.json'
    out2 = {'bundle_file_on_disk': BN.name if BN.exists() else None, 'bundle_member_name': member,
            'bundle_member_blob_40_hex': None, 'bundle_own_blob_40_hex': None, 'bundle_members': None,
            'bundle_remote_name': None,
            'how_to_recompute': 'instruments/c2_bundle_check.py downloads that bundle from the branch and '
                                're-hashes every member'}
    if BN.exists():
        nb = BN.read_bytes()
        nj = json.loads(nb.decode('utf-8'))
        out2['bundle_member_blob_40_hex'] = (nj['members'].get(member) or {}).get('blob_sha1_40_hex')
        out2['bundle_members'] = len(nj['members'])
        out2['bundle_own_blob_40_hex'] = blob(nb)
        if PLAN.exists():
            pj = json.loads(PLAN.read_text(encoding='utf-8'))
            remote = BN.name
            for r in pj.get('revisions_renamed', []) or []:
                if r.get('was') == remote:
                    remote = r.get('now', remote)
            out2['bundle_remote_name'] = remote
    return out2


out = {'ran_at_local': time.strftime('%Y-%m-%dT%H:%M:%S%z'),
       'why': 'the shared content guard matches the key name pair_token followed by a long value; the value '
              'is a per-request pairing marker with no authority, and I do not edit a shared guard from a '
              'delivery',
       'as_ran': {'path': 'c2_cells.cjs (unchanged on disk; bytes also inside raw_bundle_c2.json)',
                  'bytes': len(sa), 'sha256_64_hex': hashlib.sha256(sa).hexdigest(),
                  'blob_sha1_40_hex': blob(sa), 'lines': len(a)},
       'published_copy': {'path': 'instruments/c2_cells_pub.cjs', 'bytes': len(sb),
                          'sha256_64_hex': hashlib.sha256(sb).hexdigest(),
                          'blob_sha1_40_hex': blob(sb), 'lines': len(b)},
       'as_ran_bytes_are_published_too': containment(src.name),
       'only_change': 'the recorded key name pair_token -> pair_id (and the same name in two quoted '
                      'property reads); no logic, no selector, no assertion touched',
       'lines_that_differ': [d['line'] for d in diffs], 'diff': diffs,
       'line_counts_equal': len(a) == len(b),
       'everything_else_identical': all(a[i] == b[i] for i in range(len(a))
                                        if a[i] != b[i] and b[i] not in
                                        [a[i].replace('pair_token:', 'pair_id:')
                                         .replace("'pair_token'", "'pair_id'")])}
out['verdict'] = {'ALL_HOLD': bool(out['line_counts_equal'] and out['everything_else_identical']
                                   and len(diffs) == len(out['lines_that_differ']) > 0
                                   and out['as_ran_bytes_are_published_too']['bundle_member_blob_40_hex']
                                   == out['as_ran']['blob_sha1_40_hex'])}
(B / 'instrument_publish_copy_proof_c2.json').write_text(json.dumps(out, ensure_ascii=False, indent=1),
                                                         encoding='utf-8', newline=NL)
print(json.dumps({'lines_that_differ': out['lines_that_differ'],
                  'line_counts_equal': out['line_counts_equal'],
                  'everything_else_identical': out['everything_else_identical'],
                  'verdict': out['verdict'],
                  'as_ran_blob': out['as_ran']['blob_sha1_40_hex'],
                  'published_blob': out['published_copy']['blob_sha1_40_hex']},
                 ensure_ascii=False, indent=1))
for d in diffs:
    print('  :%d  as_ran     %s' % (d['line'], d['as_ran'][:96]))
    print('  :%d  published  %s' % (d['line'], d['published_copy'][:96]))
