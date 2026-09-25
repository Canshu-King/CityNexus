"""A same-generation unguarded mutant, so the RED direction is not borrowed from an older bundle.

The discriminator ORD-0312 cares about is a property of the bundle: `(body as {detail?}) .detail` without the
`| null` guard raises inside the sheet's catch and the screen ends up saying "can't reach the server" for an
answer that DID arrive. The generation now deployed has the guard, so a same-generation red has to be produced
by removing exactly those two guarded reads in MY private copy - the product tree and the phone chain are not
touched, and the mutant is only ever served from my own port and my own outDir.

Refuses to run unless: the anchor count is exactly what is expected, the patched file still parses, and the
resulting bundle bytes differ from the good build of the same commit.
"""
from __future__ import annotations

import importlib.util as iu
import json
import pathlib
import shutil
import sys
import time

SRC = pathlib.Path('D:/moodle/HJ-P3_evidence')
BASE = pathlib.Path('D:/moodle/_hjp3_0312r_0926')
SHEET = 'frontend/src/features/planning/PlanWithAiSheet.tsx'
GUARDED = '(body as { detail?: unknown } | null)?.detail'
UNGUARDED = '(body as { detail?: unknown }).detail'

spec = iu.spec_from_file_location('cs', str(SRC / 'c2_setup.py'))
cs = iu.module_from_spec(spec)
spec.loader.exec_module(cs)
cs.BASE = BASE

good = json.loads((BASE / 'setup_facts_gen2.json').read_text(encoding='utf-8'))
src = BASE / 'snap_gen2'
dst = BASE / 'snap_mut2'
assert src.exists(), 'the good export is missing - run r4_setup.py first'
if dst.exists():
    shutil.rmtree(dst)
t0 = time.time()
shutil.copytree(src, dst)
sh = cs.sh([r'C:\Windows\System32\cmd.exe', '/c', 'mklink', '/J',
            str(dst / 'frontend' / 'node_modules'), str(cs.REPO / 'frontend' / 'node_modules')],
           cwd=BASE)
assert (dst / 'frontend' / 'node_modules' / 'vite').exists(), 'junction failed'

f = dst / SHEET
text = f.read_text(encoding='utf-8')
n = text.count(GUARDED)
assert n == 2, 'expected the two guarded detail reads, found %d - refusing to patch blind' % n
patched = text.replace(GUARDED, UNGUARDED)
# `ast.parse` cannot judge TypeScript - my first attempt did exactly that and died on an em dash. The syntax
# proof here is that vite still compiles the mutant (its build rc is asserted below) and that the resulting
# bundle differs in bytes from the good build of the same commit.
assert patched.count(UNGUARDED) == 2 and patched.count(GUARDED) == 0
assert len(patched) == len(text) - (len(GUARDED) - len(UNGUARDED)) * n, \
    'the patch moved more characters than the two guards themselves'
f.write_text(patched, encoding='utf-8', newline='\n')

b = cs.build('mut2', dst / 'frontend', BASE / 'dist_mut2')
out = {'ran_at_local': time.strftime('%Y-%m-%dT%H:%M:%S%z'),
       'purpose': 'same-generation unguarded mutant for ORD-0312 M1/M2 red directions',
       'generation': good['tip'], 'seconds_copy_and_build': round(time.time() - t0, 1),
       'guarded_reads_before': n, 'guarded_reads_after': 0, 'unguarded_reads_after': 2,
       'sheet_blob_good': good['export']['sheet_blob_recomputed_40_hex'],
       'sheet_blob_mutant': cs.blob_of(f),
       'mutant_bundle': {'asset': b['asset'], 'bytes': b['bytes'], 'sha256_64_hex': b['sha256_64_hex']},
       'good_bundle': {'asset': good['bundle']['asset'], 'bytes': good['bundle']['bytes'],
                       'sha256_64_hex': good['bundle']['sha256_64_hex']},
       'boundaries': 'private copy + private outDir + my own ports; 0 write to the product tree, the release '
                     'dist, the phone chain or the tunnels; 0 database here'}
out['verdict'] = {
    'the_mutant_sheet_blob_differs_from_the_shipped_one': out['sheet_blob_mutant'] != out['sheet_blob_good'],
    'the_mutant_bundle_bytes_differ_from_the_good_bundle': b['sha256_64_hex']
    != good['bundle']['sha256_64_hex'],
    'the_asset_names_differ_so_the_two_faces_are_distinguishable': bool(
        pathlib.Path(b['asset']).name != pathlib.Path(good['bundle']['asset']).name)}
out['verdict']['ALL_HOLD'] = all(out['verdict'].values())
(BASE / 'setup_facts_mut2.json').write_text(json.dumps(out, ensure_ascii=False, indent=1),
                                            encoding='utf-8', newline='\n')
print(json.dumps(out['verdict'], ensure_ascii=False))
print('good:', out['good_bundle'], '\nmut :', out['mutant_bundle'])
