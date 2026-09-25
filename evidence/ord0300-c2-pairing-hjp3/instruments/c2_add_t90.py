"""ORD-0300 C2 pairing batch - stage 1b: bring the 90d29a17 generation into MY directory.

The challenged cell was born on `90d29a17…`, so it has to be re-measured there. Rather than start a
process whose cwd is another batch's folder (and rather than junction `node_modules` into it, which is how
worktrees get destroyed elsewhere in this project), this copies that batch's export and its private bundle
into my own directory and PROVES the copy is the same bytes:

  - backend/ + data/ + frontend source: re-exported from the tip by `git archive`, so nothing is trusted
    from a sibling folder at all;
  - the bundle: copied from ORD-0300's private build and compared against the sha256 that batch recorded in
    its own `bundle_facts.json` - if the bytes differ, this stage refuses.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import shutil
import subprocess
import tarfile
import time

BASE = pathlib.Path('D:/moodle/_hjp3_0300c2_0925')
REPO = pathlib.Path('D:/moodle/CityNexus')
OTHER = pathlib.Path('D:/moodle/_hjp3_0300_0925')
TIP90 = '90d29a172e186aab6e6cb138ab4583ccf93bfa68'
SHEET = 'frontend/src/features/planning/PlanWithAiSheet.tsx'
BLOB90 = 'c22cf42506a4175db992bde387ed8d9c6f1ffb9d'
NM_SRC = REPO / 'frontend' / 'node_modules'


def sha(p):
    return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()


def blob(p):
    d = pathlib.Path(p).read_bytes()
    return hashlib.sha1(b'blob %d' % len(d) + bytes([0]) + d).hexdigest()


snap = BASE / 'snap_t90'
if snap.exists():
    shutil.rmtree(snap)
snap.mkdir(parents=True)
r = subprocess.run(['git', 'archive', '--format=tar', TIP90, 'backend', 'frontend', 'data', 'contracts'],
                   cwd=str(REPO), capture_output=True, timeout=900)
assert r.returncode == 0, 'git archive failed: ' + (r.stderr or b'')[-200:].decode('utf-8', 'replace')
with tarfile.open(fileobj=subprocess.io.BytesIO(r.stdout)) as t:
    t.extractall(path=str(snap))
gits = [str(x) for x in snap.rglob('.git')]
assert not gits, 'a .git appeared inside my export: %s' % gits[:3]

sheet = snap / SHEET
assert blob(sheet) == BLOB90, 'sheet blob mismatch: %s != %s' % (blob(sheet), BLOB90)
assert sheet.read_text(encoding='utf-8').count('(body as { detail?: unknown }).detail;') == 2, \
    'the two unguarded reads are not where the challenge says they are'

# the bundle: copy ORD-0300's private build, then verify it against that batch's own recorded sha256
dist = BASE / 'dist_t90'
if dist.exists():
    shutil.rmtree(dist)
shutil.copytree(str(OTHER / 'dist_0300'), str(dist))
recorded = json.loads((OTHER / 'bundle_facts.json').read_text(encoding='utf-8'))
raw = (dist / 'assets' / recorded['asset']).read_bytes()
facts = {'ran_at_local': time.strftime('%Y-%m-%dT%H:%M:%S%z'), 'tip': TIP90, 'snap': str(snap),
         'sheet_blob_40_hex': blob(sheet), 'sheet_expected_blob': BLOB90,
         'unguarded_detail_reads': 2,
         'bundle_copied_from': str(OTHER / 'dist_0300'),
         'bundle_asset': recorded['asset'], 'bundle_bytes': len(raw),
         'bundle_sha256': hashlib.sha256(raw).hexdigest(),
         'sha256_recorded_by_that_batch': recorded['sha256'],
         'data_present': (snap / 'data/v9/city_operations.json').exists(),
         'backend_main_py_sha256': sha(snap / 'backend/app/main.py')}
facts['bundle_matches_that_batchs_record'] = (facts['bundle_sha256'] == facts['sha256_recorded_by_that_batch']
                                              if facts['sha256_recorded_by_that_batch'] else None)
# node_modules: a junction in MY directory pointing at the repo's install, never the other way round
nm = snap / 'frontend' / 'node_modules'
if not nm.exists():
    j = subprocess.run(['cmd', '/c', 'mklink', '/J', str(nm), str(NM_SRC)], capture_output=True, text=True,
                       encoding='utf-8', errors='replace')
    facts['node_modules_junction'] = {'made': nm.exists(), 'target': str(NM_SRC),
                                      'note': 'a junction in my own export; the repo install is read '
                                             'through it and never written by this batch'}
html = (dist / 'index.html').read_text(encoding='utf-8', errors='replace')
import re
asset = re.findall(r'assets/(index-[A-Za-z0-9_-]+\.js)', html)
facts['index_html_references'] = asset[:1]
facts['referenced_asset_is_the_verified_one'] = bool(asset) and asset[0] == recorded['asset']
(BASE / 't90_facts.json').write_text(json.dumps(facts, ensure_ascii=False, indent=1), encoding='utf-8',
                                      newline='\n')
print(json.dumps(facts, ensure_ascii=False, indent=1))
assert facts['bundle_matches_that_batchs_record'] is not False, 'the copied bundle is not those bytes'
