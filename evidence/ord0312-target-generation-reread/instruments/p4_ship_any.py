"""Ship whatever a plan file names, and record what the branch says afterwards.

Every earlier shipper in this lane hard-coded its own list, which meant a new batch needed a new file and the old
file went stale on disk. This one takes `--plan <json>` holding `[local, remote, message]` triples, pushes each
through `gated_push.py` (the only door that can refuse a re-PUT), then re-reads the branch tree and writes the
blob it actually sees next to each row - so the coordinates in a block or a bus post come from the branch, not
from what this process believed.
"""
from __future__ import annotations

import argparse
import importlib.util as iu
import json
import pathlib
import sys
import time

SRC = pathlib.Path('D:/moodle/HJ-P3_evidence')
spec = iu.spec_from_file_location('gp', str(SRC / 'gated_push.py'))
gp = iu.module_from_spec(spec)
spec.loader.exec_module(gp)

ap = argparse.ArgumentParser()
ap.add_argument('--plan', required=True)
ap.add_argument('--out', required=True)
a = ap.parse_args()
plan = json.loads(pathlib.Path(a.plan).read_text(encoding='utf-8'))
LOG = pathlib.Path(a.out)
done = json.loads(LOG.read_text(encoding='utf-8')) if LOG.exists() else {'pushed': []}
seen = {x['remote'] for x in done['pushed']}

for item in plan:
    local, remote, msg = item[0], item[1], item[2]
    if remote in seen:
        print('ALREADY RECORDED', remote)
        continue
    rc = gp.push(local, remote, 'docs(evidence): HJ-P3 ' + msg)
    done['pushed'].append({'remote': remote, 'local': local, 'rc': rc, 'at': time.strftime('%H:%M:%S')})
    if rc != 0:
        done['stopped_at'] = remote
        break

tip = gp.api('/git/ref/heads/commander/control')['object']['sha']
tree = {e['path']: e['sha'] for e in gp.api('/git/trees/' + tip + '?recursive=1')['tree']}
for x in done['pushed']:
    x['blob_on_branch'] = tree.get(x['remote'], 'NOT_ON_BRANCH')
    x['local_bytes_now'] = pathlib.Path(x['local']).stat().st_size
    x['local_matches_branch_bytes'] = bool(
        x['local_bytes_now'] == gp.api('/git/blobs/' + x['blob_on_branch']).get('size')
        if x['blob_on_branch'] not in (None, 'NOT_ON_BRANCH') else False)
done['branch_tip'] = tip
done['tip_read_at'] = time.strftime('%H:%M:%S')
done['all_rc_zero'] = all(x['rc'] == 0 for x in done['pushed'])
done['every_recorded_path_resolves'] = all(x.get('blob_on_branch') not in (None, 'NOT_ON_BRANCH')
                                           for x in done['pushed'])
done['every_local_copy_still_matches_the_branch'] = all(x['local_matches_branch_bytes'] for x in done['pushed'])
LOG.write_text(json.dumps(done, ensure_ascii=False, indent=1), encoding='utf-8', newline='\n')
print(json.dumps({'tip': tip, 'rows': len(done['pushed']), 'all_rc_zero': done['all_rc_zero'],
                  'resolves': done['every_recorded_path_resolves'],
                  'local_matches_branch': done['every_local_copy_still_matches_the_branch']},
                 ensure_ascii=False))
for x in done['pushed'][-4:]:
    print(x['rc'], x['blob_on_branch'], x['remote'])
sys.exit(0 if (done['all_rc_zero'] and done['every_recorded_path_resolves']) else 1)
