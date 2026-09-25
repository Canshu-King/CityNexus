"""Three-way control for THIS batch's publication gate (EVIDENCE_INTEGRITY_GATE_V1).

The gate decides, per planned remote name: FREE / byte-IDENTICAL (skip) / CHANGED (refuse). A boolean gate
without controls is a print statement, so:

  positive  a name already on the branch with the same bytes      -> SKIP
  negative  a name that is nowhere on the branch                  -> FRESH
  mutation  the SAME name, one extra byte in a scratch copy        -> REFUSE, and that file alone is refused

plus a two-sided check that the selftest itself pushed nothing: the branch tip is read before and after,
and the tip must be unchanged by this run.

Scratch files live in `_gate_selftest` and are removed at the end; nothing here writes to the branch.
"""
from __future__ import annotations

import hashlib
import importlib.util as iu
import json
import pathlib
import shutil
import sys
import time

SRC = pathlib.Path('D:/moodle/HJ-P3_evidence')
B = pathlib.Path('D:/moodle/_hjp3_0300c2_0925')
spec = iu.spec_from_file_location('pub', str(SRC / 'c2_publish.py'))
pub = iu.module_from_spec(spec)
spec.loader.exec_module(pub)

SCRATCH = B / '_gate_selftest'
SCRATCH.mkdir(exist_ok=True)
tip_before, tree_before, rows = pub.branch_rows()
landed = [r for r in rows if r['path'].endswith('RECEIPT_O0300C2-1955.json')]
assert landed, 'the control needs this batch receipt already on the branch - run it after `rest`'
remote_name = 'RECEIPT_O0300C2-1955.json'
real_local = B / remote_name

ident = SCRATCH / 'identical_copy.json'
ident.write_bytes(real_local.read_bytes())
changed = SCRATCH / 'changed_copy.json'
changed.write_bytes(real_local.read_bytes() + b' ')
fresh = SCRATCH / 'brand_new_name.json'
fresh.write_bytes(real_local.read_bytes())

cases = [(ident, remote_name, 'positive: same name, same bytes -> expect SKIP'),
         (changed, remote_name, 'mutation: same name, one extra byte -> expect REFUSAL'),
         (fresh, 'selftest_only_brand_new_name.json', 'negative: unseen name -> expect FRESH')]
g = pub.gate(cases)
tip_after, tree_after, rows_after = pub.branch_rows()
got = {'fresh': [r for (_l, r, _m, _b) in g['fresh']],
       'skipped': [x['remote'] for x in g['skipped_identical']],
       'refused': [x['remote'] for x in g['refusals']],
       'refusal_reasons': [x['reason'] for x in g['refusals']],
       'refusal_names_both_blobs': [{'me': x['me'], 'branch': x['branch']} for x in g['refusals']]}
verdict = {
    'positive_same_name_same_bytes_is_skipped': got['skipped'] == [remote_name],
    'negative_unseen_name_is_fresh': got['fresh'] == ['selftest_only_brand_new_name.json'],
    'mutation_same_name_different_bytes_is_refused': got['refused'] == [remote_name]
    and all('CHANGED BYTES' in x for x in got['refusal_reasons']),
    'the_refusal_names_only_the_mutated_file': len(got['refused']) == 1,
    'the_refusal_carries_both_blob_ids': bool(got['refusal_names_both_blobs'])
    and all(x['me'] != x['branch'] for x in got['refusal_names_both_blobs']),
    'nothing_was_pushed_by_this_selftest': tip_before == tip_after and len(rows) == len(rows_after)}
verdict['ALL_SIX_HOLD'] = all(verdict[k] for k in verdict if k != 'ALL_SIX_HOLD')
out = {'ran_at_local': time.strftime('%Y-%m-%dT%H:%M:%S%z'), 'branch_tip_before': tip_before,
       'branch_tip_after': tip_after, 'files_under_prefix_before': len(rows),
       'files_under_prefix_after': len(rows_after), 'prefix': pub.PREFIX,
       'cases': [c[2] for c in cases], 'got': got, 'verdict': verdict,
       'mutated_file_sha256': hashlib.sha256(changed.read_bytes()).hexdigest(),
       'original_file_sha256': hashlib.sha256(real_local.read_bytes()).hexdigest(),
       'what_differs': 'one trailing space in a scratch copy; the published file was never opened for '
                       'writing'}
(B / 'gate_selftest_publish_c2.json').write_text(json.dumps(out, ensure_ascii=False, indent=1),
                                                 encoding='utf-8', newline='\n')
shutil.rmtree(SCRATCH)
print(json.dumps({'verdict': verdict, 'tip_unchanged': tip_before == tip_after}, ensure_ascii=False,
                 indent=1))
print('written gate_selftest_publish_c2.json; scratch removed:', not SCRATCH.exists())
sys.exit(0 if verdict['ALL_SIX_HOLD'] else 3)
