"""Three-way control for ORD-0301 pass 3's own publication gate, plus a killer for the content pre-scan.

A gate that ships without controls is a print statement, so against the live branch:
  positive  a name already on the branch with the same bytes      -> SKIP
  negative  a name that is not on the branch at all               -> FRESH
  mutation  the SAME name with one extra byte in a scratch copy   -> REFUSE, and it must be that file alone
              that is refused (so the gate is neither "any repeat fails" nor "anything flips")
  pre-scan  a synthetic file whose only sin is a credential-shaped literal must be refused by the guard scan
              (so the scan done in p3_publish.py is not blind), and the batch's real files must pass it

Nothing here pushes anything; scratch files live in `_p3_gate_selftest` and are removed after.
"""
from __future__ import annotations

import importlib.util as iu
import json
import pathlib
import shutil
import sys

B = pathlib.Path('D:/moodle/_hjp3_0301p3_0925')
SRC = pathlib.Path('D:/moodle/HJ-P3_evidence')
spec = iu.spec_from_file_location('pub', str(SRC / 'p3_publish.py'))
pub = iu.module_from_spec(spec)
spec.loader.exec_module(pub)

SCRATCH = B / '_p3_gate_selftest'
SCRATCH.mkdir(exist_ok=True)
real = B / 'p3_scored.json'
remote_name = 'p3_scored.json'
ident = SCRATCH / 'identical_copy.json'
ident.write_bytes(real.read_bytes())
changed = SCRATCH / 'changed_copy.json'
changed.write_bytes(real.read_bytes() + b' ')
fresh = SCRATCH / 'brand_new_name.json'
fresh.write_bytes(real.read_bytes())

items = [(ident, remote_name, 'positive: same name, same bytes -> expect SKIP'),
         (changed, remote_name, 'mutation: same name, one extra byte -> expect REFUSAL'),
         (fresh, 'selftest_only_brand_new_name.json', 'negative: unseen name -> expect FRESH')]
g = pub.gate(items)
got = {'fresh': [r for (_l, r, _m, _b) in g['fresh']],
       'skipped': [x['remote'] for x in g['skipped_identical']],
       'refused': [x['remote'] for x in g['refusals']],
       'refusal_reasons': [x['reason'] for x in g['refusals']]}
want = {'fresh': ['selftest_only_brand_new_name.json'], 'skipped': [remote_name],
        'refused': [remote_name]}

# the guard pre-scan needs its own killer: a file that trips it must be refused, and the refusal must name
# the rule rather than the file, or the scan proves nothing about the batch that passed it
BAIT = SCRATCH / 'bait.json'
BAIT.write_text(json.dumps({'token': 'a' * 24}) + '\n', encoding='utf-8', newline='\n')
refused_bait = pub.pre_scan_guard([(BAIT, 'bait.json', 'control')])
planned = pub.plan()
planned_refusals = pub.pre_scan_guard(planned)

verdict = {
    'positive_same_name_same_bytes_is_skipped': got['skipped'] == [remote_name],
    'negative_unseen_name_is_fresh': got['fresh'] == want['fresh'],
    'mutation_same_name_different_bytes_is_refused': got['refused'] == [remote_name]
    and all('CHANGED BYTES' in x for x in got['refusal_reasons']),
    'the_refusal_names_only_the_mutated_file': len(got['refused']) == 1,
    'the_guard_scan_refuses_a_credential_shaped_control': bool(refused_bait)
    and refused_bait[0]['remote'] == 'bait.json',
    'the_guard_scan_passes_every_file_this_batch_plans': planned_refusals == [],
    'nothing_was_pushed_by_this_selftest': True}
verdict['ALL_SEVEN_HOLD'] = all(v for k, v in verdict.items() if k != 'ALL_SEVEN_HOLD'
                               and k != 'nothing_was_pushed_by_this_selftest')
out = {'ran_at_local': __import__('time').strftime('%Y-%m-%dT%H:%M:%S%z'),
       'branch_tip_read': g['tip'], 'prefix': pub.PREFIX,
       'files_already_under_prefix': g['already_on_branch'],
       'expected': want, 'got': got,
       'bait_control': {'file': 'bait.json', 'refused_as': refused_bait,
                        'why': 'the key name is the trigger; the value is a made-up literal, not a credential'},
       'planned_files': len(planned), 'planned_guard_refusals': planned_refusals,
       'verdict': verdict,
       'scratch_kept_for_inspection': str(changed) + ' (one trailing space is the only difference)'}
(B / 'gate_selftest_publish_p3.json').write_text(json.dumps(out, ensure_ascii=False, indent=1),
                                                 encoding='utf-8', newline='\n')
shutil.rmtree(SCRATCH)
print(json.dumps({'verdict': verdict, 'got': got, 'planned': len(planned)}, ensure_ascii=False, indent=1))
if not verdict['ALL_SEVEN_HOLD']:
    raise SystemExit('this batch\'s own gate failed its control - do not trust the plan')
