"""Ship the receipt and the deliverer for the FINAL block text.

The `_r2` copies already on the branch recorded an earlier run of the same gate on an earlier draft of the block,
so they stay exactly as they are; the current verdict goes out under `_r3` names. Instrument paths are never
rewritten, which is why the deliverer is re-shipped rather than updated.
"""
from __future__ import annotations

import importlib.util as iu
import json
import pathlib
import sys
import time

OUT = pathlib.Path('D:/moodle/_hjp3_0312p4_0926')
SRC = pathlib.Path('D:/moodle/HJ-P3_evidence')
spec = iu.spec_from_file_location('gp', str(SRC / 'gated_push.py'))
gp = iu.module_from_spec(spec)
spec.loader.exec_module(gp)
PUB = 'evidence/ord0312-target-generation-reread'
REV = sys.argv[2] if len(sys.argv) > 2 else '3'
SUF = '' if REV == '' else '_r' + REV
LOG = OUT / ('ship_result_p4%s.json' % (SUF or '_r3'))
done = json.loads(LOG.read_text(encoding='utf-8')) if LOG.exists() else {'pushed': []}
seen = {x['remote'] for x in done['pushed']}

PLAN = {
    'a': [(OUT / 'ledger_inbox_proof_p4.json', PUB + '/ledger_inbox_proof_p4' + SUF + '.json',
           'Q43 r4b verdict for the final re-issued block text (new name; the earlier receipt stays)'),
          (SRC / 'p4_deliver.py', PUB + '/instruments/p4_deliver' + SUF + '.py',
           'deliverer of the final block text (new name; instrument paths are never rewritten)')],
    'b': [(SRC / 'p4_bus2.py', PUB + '/instruments/p4_bus2.py',
           'poster of the follow-up bus note for this re-issue (new name)'),
          (SRC / 'p4_push3.py', PUB + '/instruments/p4_push3.py',
           'shipper of these two phases (new name)')],
    'c': [(OUT / 'retired_ruler_scan_p4.json', PUB + '/retired_ruler_scan_p4.json',
           'ORD-0312: byte scan for any surviving citation of the retired Q64 r1 ruler, with its denominators '
           'and its positive control')],
}
phase = sys.argv[1]
assert phase in PLAN, 'phase must be a or b'

for local, remote, msg in PLAN[phase]:
    if remote in seen:
        print('already recorded', remote)
        continue
    rc = gp.push(str(local), remote, 'docs(evidence): HJ-P3 ' + msg)
    done['pushed'].append({'remote': remote, 'local': str(local), 'rc': rc, 'at': time.strftime('%H:%M:%S')})
    if rc != 0:
        done['stopped_at'] = remote
        break

tip = gp.api('/git/ref/heads/commander/control')['object']['sha']
tree = {e['path']: e['sha'] for e in gp.api('/git/trees/' + tip + '?recursive=1')['tree']}
for x in done['pushed']:
    x['blob_on_branch'] = tree.get(x['remote'], 'NOT_ON_BRANCH')
done['branch_tip'] = tip
done['tip_read_at'] = time.strftime('%H:%M:%S')
done['all_rc_zero'] = all(x['rc'] == 0 for x in done['pushed'])
done['every_recorded_path_resolves'] = all(x.get('blob_on_branch') not in (None, 'NOT_ON_BRANCH')
                                           for x in done['pushed'])
LOG.write_text(json.dumps(done, ensure_ascii=False, indent=1), encoding='utf-8', newline='\n')
print(json.dumps({'tip': tip, 'all_rc_zero': done['all_rc_zero'],
                  'resolves': done['every_recorded_path_resolves'],
                  'rows': [{'remote': x['remote'], 'rc': x['rc'], 'blob': x['blob_on_branch']}
                           for x in done['pushed']]}, ensure_ascii=False, indent=1))
if '--exitnonzero-on-failure' in sys.argv and not (done['all_rc_zero']
                                                   and done['every_recorded_path_resolves']):
    raise SystemExit(1)
