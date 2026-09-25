"""ORD-0300 cross-check: does the finding hold on a bundle I did NOT build?

B's lane left an ORD-0280 build on disk (`_qoder_b_lane_20260923/frontend/dist_0280`). Serving THAT read-only
against a backend started from the same one-time DB (no delete, append only) answers the one objection my own
build invites: "maybe your private build is what misbehaves". Nothing here writes to another lane's tree.
"""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import re
import subprocess
import time
import uuid
import urllib.error
import urllib.request

BASE = pathlib.Path('D:/moodle/_hjp3_0300_0925')
SNAP_BACKEND = BASE / 'snap' / 'backend'
B_DIST = pathlib.Path('D:/moodle/_qoder_b_lane_20260923/frontend/dist_0280')
FACE_CWD = pathlib.Path('D:/moodle/_hjp3_ord0261_0923/snap_e3b0b47/frontend')
PY = 'D:/moodle/CityNexus/.venv/Scripts/python.exe'
DB = BASE / 'o0300.s3db'
BP, FP = 8556, 8555
DETACHED = 0x00000008 | 0x00000200
state = json.loads((BASE / 'o0300_state.json').read_text(encoding='utf-8'))
JOURNEY = state['seed']['journey_id']


def listening(port):
    out = subprocess.run(['netstat', '-ano'], capture_output=True, text=True,
                         encoding='utf-8', errors='replace').stdout
    return [l.split()[-1] for l in out.splitlines() if ('127.0.0.1:%d ' % port) in l and 'LISTENING' in l]


def get(url, timeout=90):
    # an HTTP error status is a READING, not a transport failure - conflating them hid the 404 control
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()
    except Exception as e:  # noqa: BLE001
        return 'ERR', str(e)[:160].encode()


env = dict(os.environ)
env['CITYNEXUS_DATABASE_URL'] = 'sqlite:///' + str(DB).replace('\\', '/')
env['PYTHONPATH'] = str(SNAP_BACKEND)
env.pop('DEEPSEEK_API_KEY', None)
env['CITYNEXUS_AI_ENABLED'] = 'false'

assert listening(BP) == [] and listening(FP) == [], 'ports not free'
assert B_DIST.exists() and (B_DIST / 'index.html').exists(), 'no foreign bundle'
before = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in B_DIST.rglob('*.js') if p.is_file()}

blog = open(BASE / 'crosscheck_backend.log', 'w', encoding='utf-8', errors='replace')
b = subprocess.Popen([PY, '-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', str(BP),
                      '--log-level', 'info'], cwd=str(SNAP_BACKEND), env=env, creationflags=DETACHED,
                     stdout=blog, stderr=subprocess.STDOUT)
for _ in range(90):
    if listening(BP):
        break
    time.sleep(1)

fenv = dict(env)
fenv['CITYNEXUS_BACKEND_PORT'] = str(BP)
flog = open(BASE / 'crosscheck_face.log', 'w', encoding='utf-8', errors='replace')
f = subprocess.Popen(['node', 'node_modules/vite/bin/vite.js', 'preview', '--outDir', str(B_DIST),
                      '--port', str(FP), '--host', '127.0.0.1', '--strictPort'],
                     cwd=str(FACE_CWD), env=fenv, creationflags=DETACHED, stdout=flog, stderr=subprocess.STDOUT)
for _ in range(90):
    if listening(FP):
        break
    time.sleep(1)

html = get('http://127.0.0.1:%d/' % FP)[1].decode('utf-8', 'replace')
ref = re.findall(r'assets/(index-[A-Za-z0-9_-]+\.js)', html)[0]
raw = get('http://127.0.0.1:%d/assets/%s' % (FP, ref))[1]
mine = json.loads((BASE / 'bundle_facts.json').read_text(encoding='utf-8'))
ownership = {'mine_via_face': get('http://127.0.0.1:%d/api/v1/journeys/%s' % (FP, JOURNEY))[0],
             'foreign_via_face': get('http://127.0.0.1:%d/api/v1/journeys/%s'
                                     % (FP, str(uuid.UUID(int=0xC0FFEE))))[0]}

os.environ['RUN_ID'] = 'O0300-2700'
os.environ['PORT_OVERRIDE'] = str(FP)
os.environ['CAP_MS'] = '80000'
os.environ['NEED_LOCK'] = '1'
os.environ['BUNDLE_SHA'] = hashlib.sha256(raw).hexdigest()
os.environ['BUNDLE_ASSET'] = ref
for flag in ('sheet_ready.flag', 'lock_armed.flag'):
    p = BASE / flag
    if p.exists():
        p.unlink()
node = subprocess.Popen(['node', str(BASE / 'o0300_cells.cjs'), 'w2'], cwd=str(BASE), env={**os.environ},
                        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding='utf-8',
                        errors='replace')
lock = None
t0 = time.time()
while time.time() - t0 < 90:
    if (BASE / 'sheet_ready.flag').exists():
        lock = subprocess.Popen([PY, str(pathlib.Path('D:/moodle/HJ-P3_evidence/o0300_rig.py')), 'lock', '80'],
                                stdout=open(BASE / 'crosscheck_locklog.txt', 'w', encoding='utf-8'),
                                stderr=subprocess.STDOUT, text=True, encoding='utf-8')
        t1 = time.time()
        while time.time() - t1 < 30:
            if 'ARMED' in (BASE / 'crosscheck_locklog.txt').read_text(encoding='utf-8', errors='replace'):
                (BASE / 'lock_armed.flag').write_text(time.strftime('%H:%M:%S'), encoding='utf-8')
                break
            time.sleep(0.2)
        break
    time.sleep(0.25)

out, _ = node.communicate(timeout=300)
(BASE / 'crosscheck_node.txt').write_text(out or '', encoding='utf-8')
if lock:
    lock.wait(timeout=140)
after = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in B_DIST.rglob('*.js') if p.is_file()}
subprocess.run(['taskkill', '/PID', str(f.pid), '/T', '/F'], capture_output=True)
subprocess.run(['taskkill', '/PID', str(b.pid), '/T', '/F'], capture_output=True)
for flag in ('sheet_ready.flag', 'lock_armed.flag'):
    p = BASE / flag
    if p.exists():
        p.unlink()

cell = json.loads((BASE / 'cell_w2_O0300-2700.json').read_text(encoding='utf-8'))
rec = {
 'question': 'does the ORD-0300 screen finding survive when the bundle is NOT the one I built?',
 'foreign_bundle_dir': str(B_DIST), 'foreign_asset': ref,
 'foreign_served_sha256': hashlib.sha256(raw).hexdigest(),
 'my_build_sha256': mine['sha256'], 'same_bytes_as_my_build': hashlib.sha256(raw).hexdigest() == mine['sha256'],
 'foreign_bundle_contains_ord0280_markers': ('这台设备自己的读数（服务器没给句子）' in raw.decode('utf-8', 'replace')),
 'ownership_proof': ownership,
 'backend_db': str(DB) + ' (same one-time DB, appended; not deleted)',
 'foreign_tree_unchanged_by_this_run': before == after,
 'reading': {'http_status': cell['write_legs'][0].get('status'),
             'content_type': cell['write_legs'][0].get('content_type'),
             'bytes': cell['write_legs'][0].get('bytes'),
             'elapsed_ms': cell['write_legs'][0].get('elapsed_ms'),
             'painted_card': cell['screen_after_open_details']['result_card'],
             'painted_label': cell['screen_after_open_details']['reason_label_painted'],
             'painted_value': cell['screen_after_open_details']['reason_value_painted'],
             'details_in_dom': cell['screen_after_open_details']['details_elements_present'],
             'data_result_status': re.search(r'data-result-status="([^"]*)"',
                                             cell['screen_after_open_details']['result_card_html'] or '')
                                 .group(1) if 'data-result-status' in (cell['screen_after_open_details']['result_card_html'] or '') else None},
 'verdict': None,
 'listening_after': {str(BP): listening(BP), str(FP): listening(FP)},
}
rec['verdict'] = ('SAME_FINDING_ON_A_FOREIGN_BUILD' if rec['reading']['data_result_status'] == 'NETWORK'
                  and rec['reading']['details_in_dom'] == 0 else 'DIFFERENT_ON_FOREIGN_BUILD')
(BASE / 'crosscheck_foreign_bundle.json').write_text(json.dumps(rec, ensure_ascii=False, indent=1),
                                                     encoding='utf-8')
print(json.dumps(rec, ensure_ascii=False, indent=1))
