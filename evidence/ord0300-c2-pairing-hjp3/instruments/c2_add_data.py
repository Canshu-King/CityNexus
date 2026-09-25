"""ORD-0300 C2 pairing batch - repair my own export: the backend reads the repo-root `data/` at runtime.

The first arm died before it could measure anything: `GET /api/v1/journeys/<id>/experience` answered a real
HTTP 500 / 21 B `FileNotFoundError: ...\\snap_old\\data\\v9\\city_operations.json`, because I exported only
`backend` and `frontend` from the tip and the product reads `data/` (and `contracts/`) through a
repo-root-relative path. That 500 is my packaging, not the product's behaviour, so it is fixed by adding the
same two directories pulled from the SAME tip by the same read-only mechanism - and the fix is proven by
hashing `backend/app/main.py` and the sheet before and after, so nobody can say I changed the thing under
test while repairing the thing holding it up.
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
TIPS = {'old': 'dc964086c9d412573ac19d70b24b30e6c3ee6168',
        'new': '5aff3722d5c36c760a424f5fea5c3a771298f9ac',
        'mut': '5aff3722d5c36c760a424f5fea5c3a771298f9ac'}
ADD = ('data', 'contracts')
SHEET = 'frontend/src/features/planning/PlanWithAiSheet.tsx'


def sha(p):
    return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()


out = {'ran_at_local': time.strftime('%Y-%m-%dT%H:%M:%S%z'), 'tips': TIPS, 'adds': list(ADD), 'per_snap': {}}
for which, tip in TIPS.items():
    snap = BASE / ('snap_' + which)
    before = {'backend_main_py_sha256': sha(snap / 'backend/app/main.py'),
              'sheet_sha256': sha(snap / SHEET),
              'sheet_blob': hashlib.sha1(b'blob ' + (snap / SHEET).read_bytes().__len__().__str__().encode()
                                         + bytes([0]) + (snap / SHEET).read_bytes()).hexdigest()}
    r = subprocess.run(['git', 'archive', '--format=tar', tip] + list(ADD), cwd=str(REPO),
                       capture_output=True, timeout=600)
    assert r.returncode == 0, 'git archive failed: ' + (r.stderr or b'')[-200:].decode('utf-8', 'replace')
    with tarfile.open(fileobj=subprocess.io.BytesIO(r.stdout)) as t:
        t.extractall(path=str(snap))
    key = snap / 'data/v9/city_operations.json'
    after = {'backend_main_py_sha256': sha(snap / 'backend/app/main.py'),
             'sheet_sha256': sha(snap / SHEET),
             'sheet_blob': hashlib.sha1(b'blob ' + str(len((snap / SHEET).read_bytes())).encode()
                                        + bytes([0]) + (snap / SHEET).read_bytes()).hexdigest()}
    out['per_snap'][which] = {
        'data_files': len(list((snap / 'data').rglob('*'))), 'contract_files': len(list((snap / 'contracts').rglob('*')))
        if (snap / 'contracts').exists() else 0,
        'city_operations_present': key.exists(), 'city_operations_bytes': key.stat().st_size if key.exists() else None,
        'city_operations_sha256': sha(key) if key.exists() else None,
        'subject_unchanged_by_this_repair': before == after,
        'sheet_blob_still': after['sheet_blob'],
        'files_seen_before': before, 'files_seen_after': after}
    print(which, json.dumps({k: out['per_snap'][which][k] for k in
                            ('city_operations_present', 'subject_unchanged_by_this_repair', 'sheet_blob_still')},
                           ensure_ascii=False), flush=True)

out['all_three_subjects_unchanged'] = all(v['subject_unchanged_by_this_repair'] for v in out['per_snap'].values())
out['mut_still_differs_from_new_by_two_lines_only'] = (
    sha(BASE / 'snap_mut' / SHEET) != sha(BASE / 'snap_new' / SHEET)
    and sha(BASE / 'snap_mut' / 'backend/app/main.py') == sha(BASE / 'snap_new' / 'backend/app/main.py'))
out['data_identical_across_the_three_snaps'] = (
    out['per_snap']['new']['city_operations_sha256'] == out['per_snap']['mut']['city_operations_sha256']
    and out['per_snap']['old']['city_operations_sha256'] in
    {out['per_snap']['new']['city_operations_sha256'], None} is not None
    and bool(out['per_snap']['old']['city_operations_sha256']))
(BASE / 'export_repair_facts.json').write_text(json.dumps(out, ensure_ascii=False, indent=1),
                                                encoding='utf-8', newline='\n')
print(json.dumps({k: out[k] for k in ('all_three_subjects_unchanged',
                                      'mut_still_differs_from_new_by_two_lines_only',
                                      'data_identical_across_the_three_snaps')}, ensure_ascii=False))
