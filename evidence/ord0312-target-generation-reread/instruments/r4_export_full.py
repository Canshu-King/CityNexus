"""Re-export the new tip with the directories my own history says I must not leave out.

The first export asked `git archive` for `backend frontend` only, and the demo seed then died on
`snap_gen2/data/mock/traveler_demo.js` - which made an arm come back with every screen reading null. That is an
instrument red wearing a product costume: this project's data and contracts directories sit at the repository
root, not under `backend`, so an export without them cannot run the product at all.

Re-exports `backend frontend data contracts`, re-verifies the sheet blob against the tip's tree, and rebuilds
both bundles (the guarded one and the same-generation unguarded mutant) so the arm table runs against trees that
can actually boot.
"""
from __future__ import annotations

import importlib.util as iu
import json
import pathlib
import shutil
import subprocess
import time

SRC = pathlib.Path('D:/moodle/HJ-P3_evidence')
BASE = pathlib.Path('D:/moodle/_hjp3_0312r_0926')
REPO = pathlib.Path('D:/moodle/CityNexus')
SHEET = 'frontend/src/features/planning/PlanWithAiSheet.tsx'
TIP = '9a669c8bec863fadf31d5158f4a1be66aec49f23'
SHEET_BLOB = 'fc4d6111dc013008b610a240aab096deebe2436f'
PATHS = ['backend', 'frontend', 'data', 'contracts']

spec = iu.spec_from_file_location('cs', str(SRC / 'c2_setup.py'))
cs = iu.module_from_spec(spec)
spec.loader.exec_module(cs)
cs.BASE = BASE


def export_into(snap):
    if snap.exists():
        shutil.rmtree(snap)
    snap.mkdir(parents=True)
    r = subprocess.run(['git', 'archive', '--format=tar', TIP] + PATHS, cwd=str(REPO),
                       capture_output=True, timeout=600)
    assert r.returncode == 0, r.stderr[:300]
    t = subprocess.run(['tar', '-xf', '-'], cwd=str(snap), input=r.stdout, timeout=600)
    assert t.returncode == 0
    return snap


t0 = time.time()
snap = export_into(BASE / 'snap_gen2')
blob = cs.blob_of(snap / SHEET)
text = (snap / SHEET).read_text(encoding='utf-8')
out = {'ran_at_local': time.strftime('%Y-%m-%dT%H:%M:%S%z'), 'tip': TIP, 'paths_exported': PATHS,
       'seconds_export': round(time.time() - t0, 1),
       'sheet_blob_recomputed_40_hex': blob, 'sheet_blob_expected': SHEET_BLOB,
       'sheet_blob_matches_the_tip': blob == SHEET_BLOB,
       'guarded_detail_reads': text.count('(body as { detail?: unknown } | null)?.detail'),
       'unguarded_detail_reads': text.count('(body as { detail?: unknown }).detail'),
       'data_dir_present': (snap / 'data' / 'mock').exists(),
       'contracts_dir_present': (snap / 'contracts').exists()}
assert out['sheet_blob_matches_the_tip'] and out['data_dir_present'] and out['contracts_dir_present']
t1 = time.time()
cs.junction(snap / 'frontend')
b = cs.build('gen2', snap / 'frontend', BASE / 'dist_gen2')
out['guarded_bundle'] = {'asset': b['asset'], 'bytes': b['bytes'], 'sha256_64_hex': b['sha256_64_hex'],
                         'seconds_build': round(time.time() - t1, 1), 'markers': b.get('markers')}

t2 = time.time()
msnap = export_into(BASE / 'snap_mut2')
mf = msnap / SHEET
mt = mf.read_text(encoding='utf-8')
n = mt.count('(body as { detail?: unknown } | null)?.detail')
assert n == 2, 'expected two guarded detail reads, found %d' % n
mt2 = mt.replace('(body as { detail?: unknown } | null)?.detail', '(body as { detail?: unknown }).detail')
assert mt2.count('(body as { detail?: unknown }).detail') == 2 and mt2.count(
    '(body as { detail?: unknown } | null)?.detail') == 0
mf.write_text(mt2, encoding='utf-8', newline='\n')
cs.junction(msnap / 'frontend')
mb = cs.build('mut2', msnap / 'frontend', BASE / 'dist_mut2')
out['mutant_bundle'] = {'asset': mb['asset'], 'bytes': mb['bytes'], 'sha256_64_hex': mb['sha256_64_hex'],
                        'seconds_build': round(time.time() - t2, 1)}
out['verdict'] = {
    'the_two_bundles_are_different_bytes': b['sha256_64_hex'] != mb['sha256_64_hex'],
    'the_mutant_sheet_blob_differs_from_the_shipped_one': cs.blob_of(mf) != blob,
    'the_guarded_tree_is_the_tip': out['sheet_blob_matches_the_tip'],
    'both_trees_can_seed': (snap / 'data' / 'mock').exists() and (msnap / 'data' / 'mock').exists()}
out['verdict']['ALL_HOLD'] = all(out['verdict'].values())
(BASE / 'setup_facts_gen2.json').write_text(json.dumps({**out, 'bundle': out['guarded_bundle'],
                                                        'seconds_build': out['guarded_bundle']['seconds_build']},
                                                       ensure_ascii=False, indent=1),
                                            encoding='utf-8', newline='\n')
(BASE / 'setup_facts_mut2.json').write_text(json.dumps({'ran_at_local': out['ran_at_local'], 'tip': TIP,
                                                        'mutant_bundle': out['mutant_bundle'],
                                                        'sheet_blob_good': blob,
                                                        'guarded_reads_after': 0,
                                                        'unguarded_reads_after': 2,
                                                        'verdict': out['verdict']},
                                                       ensure_ascii=False, indent=1),
                                            encoding='utf-8', newline='\n')
print(json.dumps(out['verdict'], ensure_ascii=False))
print('guarded:', out['guarded_bundle']['asset'], out['guarded_bundle']['bytes'],
      '| mutant:', out['mutant_bundle']['asset'], out['mutant_bundle']['bytes'],
      '| export %.1fs build %.1fs/%.1fs' % (out['seconds_export'], out['guarded_bundle']['seconds_build'],
                                            out['mutant_bundle']['seconds_build']))
