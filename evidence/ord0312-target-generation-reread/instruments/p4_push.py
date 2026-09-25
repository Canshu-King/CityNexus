"""Ship the three ORD-0316 / ORD-0312 / T-1x artefacts, then attempt the raw original and record the refusal.

Everything goes through `gated_push.py`, which cannot re-PUT a published path. The one deliberate exception to
"only push what the plan listed" is the raw-original attempt: ORD-0316 asks for that file at a new path, and
the honest answer is either a published path or a measured refusal - so I try it, capture the guard's refusal,
and put that in the proof instead of quietly skipping it.
"""
from __future__ import annotations

import importlib.util as iu
import json
import pathlib
import time

OUT = pathlib.Path('D:/moodle/_hjp3_0312p4_0926')
SRC = pathlib.Path('D:/moodle/HJ-P3_evidence')
C2 = pathlib.Path('D:/moodle/_hjp3_0300c2_0925')
spec = iu.spec_from_file_location('gp', str(SRC / 'gated_push.py'))
gp = iu.module_from_spec(spec)
spec.loader.exec_module(gp)
PUB_C2 = 'evidence/ord0300-c2-pairing-hjp3'
PUB_312 = 'evidence/ord0312-target-generation-reread'
PUB_TX = 'evidence/ord0288-t1x-transfer-hjp3'
plan = json.loads((OUT / 'ship_plan_p4.json').read_text(encoding='utf-8'))['planned']
MSGS = {'raw_bundle_o0316.json': 'ORD-0316: the gate-refused original byte-exact as a container member',
        'ord0312_m3_m4_reading.json': 'ORD-0312 M3 stop-and-report + M4 :8000 listener count',
        't1x_transfer_reading_whitelisted.json': 'T-1x transfer reading, whitelisted fields only',
        'instruments': 'instrument of this batch (new name; instrument paths are never rewritten)'}
res = []
for item in plan:
    remote = item['remote']
    name = pathlib.Path(remote).name
    # the whitelisted summary goes up under the plain name, so the local file has to be mapped back
    name = 't1x_transfer_reading_whitelisted.json' if name == 't1x_transfer_reading.json' else name
    local = OUT / name
    if '/instruments/' in remote:
        local = SRC / pathlib.Path(remote).name
    msg = 'docs(evidence): HJ-P3 ' + (MSGS['instruments'] if '/instruments/' in remote
                                      else MSGS.get(pathlib.Path(remote).name, 'artefact'))
    rc = gp.push(str(local), remote, msg)
    res.append({'remote': remote, 'rc': rc})
    if rc != 0:
        raise SystemExit('rc=%d on %s - stopping, nothing retried under an old name' % (rc, remote))

raw_target = PUB_C2 + '/arm_old_old_lock_C2-214340_gate_refused_original.json'
attempt = gp.push(str(C2 / 'arm_old_old_lock_C2-214340.json'), raw_target,
                  'docs(evidence): ORD-0316 attempt - the byte-exact original under its own new name')
proof_path = OUT / 'o0316_proof.json'
proof = json.loads(proof_path.read_text(encoding='utf-8'))
proof['raw_name_under_a_new_path_was_attempted'] = {
    'path_tried': raw_target, 'gated_push_rc': attempt,
    'reading': ('refused as expected - the guard matches these bytes under any name' if attempt != 0
                else 'ACCEPTED - the guard did not refuse it after all, so the original is on the branch'),
    'guard_rules_on_the_raw_bytes': proof['original_identity']['guard_refused_because']}
tip = gp.api('/git/ref/heads/commander/control')['object']['sha']
tree = {e['path']: e['sha'] for e in gp.api('/git/trees/' + tip + '?recursive=1')['tree']}
proof['copy_identity'] = {
    'path': PUB_C2 + '/arm_old_old_lock_C2-214340_pub.json',
    'blob_on_branch': tree.get(PUB_C2 + '/arm_old_old_lock_C2-214340_pub.json'),
    'read_from': 'GET /git/trees/<tip>?recursive=1 at ' + time.strftime('%H:%M:%S')}
proof['container_identity']['blob_on_branch'] = tree.get(PUB_C2 + '/raw_bundle_o0316.json')
proof['three_coordinates'] = {
    'original_bytes': proof['original_identity']['blob_sha1_40_hex'],
    'renamed_copy_on_branch': proof['copy_identity']['blob_on_branch'],
    'proof_file': proof['container_identity']['blob_sha1_40_hex']}
proof['verdict']['original_is_addressable_by_git_cat_file_as_a_path'] = bool(
    attempt == 0)
proof['verdict']['original_is_verifiable_by_rehash_from_a_published_container'] = bool(
    proof['round_trip_decoded_equals_original']['names_the_original_blob']
    and proof['container_identity']['blob_on_branch'])
proof['verdict']['ALL_HOLD'] = all(v for k, v in proof['verdict'].items() if k != 'ALL_HOLD')
proof_path.write_text(json.dumps(proof, ensure_ascii=False, indent=1), encoding='utf-8', newline='\n')
rc = gp.push(str(proof_path), PUB_C2 + '/o0316_gate_refused_original_proof.json',
             'docs(evidence): ORD-0316 proof - original / copy / container, with the measured refusal')
rc2 = gp.push(str(SRC / 'p4_ship.py'), PUB_312 + '/instruments/p4_ship.py',
              'docs(evidence): HJ-P3 instrument of this batch (new name)')
rc3 = gp.push(str(SRC / 'p4_push.py'), PUB_312 + '/instruments/p4_push.py',
              'docs(evidence): HJ-P3 shipper of this batch (new name)')
log = {'pushed': res + [{'remote': raw_target, 'rc': attempt},
                        {'remote': PUB_C2 + '/o0316_gate_refused_original_proof.json', 'rc': rc},
                        {'remote': PUB_312 + '/instruments/p4_ship.py', 'rc': rc2},
                        {'remote': PUB_312 + '/instruments/p4_push.py', 'rc': rc3}],
       'all_zero_except_the_recorded_attempt': all(
           x['rc'] == 0 for x in res) and rc == 0 and rc2 == 0 and rc3 == 0,
       'o0316_verdict': proof['verdict']}
(OUT / 'ship_result_p4.json').write_text(json.dumps(log, ensure_ascii=False, indent=1), encoding='utf-8',
                                        newline='\n')
print(json.dumps(log['o0316_verdict'], ensure_ascii=False))
print('attempt rc', attempt, '| pushed', len(res) + 4, 'files')
