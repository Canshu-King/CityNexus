"""Ship the write-time served re-check (phase 1) and the re-issued inbox receipt (phase 3).

Phase order exists because the block cites the served re-check by its BRANCH blob: the file has to be on the
branch before the deliverer reads the tree, while the Q43 receipt and the deliverer itself cannot cite
themselves, so their 40-hex go in the bus note that follows.

Nothing here re-PUTs a published path: `gated_push.py` refuses byte-identical repeats and refuses changed bytes
under an old name, and both new artefacts therefore get brand-new remote names.
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
LOG = OUT / 'ship_result_p4_r2.json'
done = json.loads(LOG.read_text(encoding='utf-8')) if LOG.exists() else {'pushed': []}
seen = {x['remote'] for x in done['pushed']}

PHASES = {
    '1': [(sorted(OUT.glob('served_generation_recheck_p4_*.json'))[-1],
           PUB + '/ord0312_served_recheck_at_block_write.json',
           'ORD-0312 M3: write-time read-only re-check that the chain still serves the probe-pinned bytes'),
          (SRC / 'p4_served_now.py', PUB + '/instruments/p4_served_now.py',
           'HJ-P3 instrument of this batch (new name; instrument paths are never rewritten)')],
    '3': [(OUT / 'ledger_inbox_proof_p4.json', PUB + '/ledger_inbox_proof_p4_r2.json',
           'ORD-0312/0316 re-issued block: its own Q43 r4b verdict (new name, old block untouched)'),
          (SRC / 'p4_deliver.py', PUB + '/instruments/p4_deliver_r2.py',
           'HJ-P3 deliverer of this batch, re-issued under a new name'),
          (SRC / 'p4_push2.py', PUB + '/instruments/p4_push2.py',
           'HJ-P3 shipper of these two phases (new name)')],
}

phase = sys.argv[1]
assert phase in PHASES
for local, remote, msg in PHASES[phase]:
    if remote in seen:
        print('ALREADY RECORDED, skipping', remote)
        continue
    rc = gp.push(str(local), remote, 'docs(evidence): HJ-P3 ' + msg)
    done['pushed'].append({'remote': remote, 'local': str(local), 'rc': rc,
                           'at': time.strftime('%H:%M:%S')})
    if rc != 0:
        done['stopped_at'] = remote
        break
tip = gp.api('/git/ref/heads/commander/control')['object']['sha']
tree = {e['path']: e['sha'] for e in gp.api('/git/trees/' + tip + '?recursive=1')['tree']}
for x in done['pushed']:
    x['blob_on_branch'] = tree.get(x['remote'], 'NOT_ON_BRANCH')
done['tip_read_at'] = time.strftime('%H:%M:%S')
done['branch_tip'] = tip
done['every_recorded_path_resolves'] = all(x.get('blob_on_branch') not in (None, 'NOT_ON_BRANCH')
                                           for x in done['pushed'])
done['all_rc_zero'] = all(x['rc'] == 0 for x in done['pushed'])
LOG.write_text(json.dumps(done, ensure_ascii=False, indent=1), encoding='utf-8', newline='\n')
print(json.dumps({'phase': phase, 'tip': tip, 'all_rc_zero': done['all_rc_zero'],
                  'every_recorded_path_resolves': done['every_recorded_path_resolves'],
                  'rows': [{'remote': x['remote'], 'rc': x['rc'], 'blob': x['blob_on_branch']}
                           for x in done['pushed'][-4:]]}, ensure_ascii=False, indent=1))
