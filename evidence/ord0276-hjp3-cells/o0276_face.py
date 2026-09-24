"""Move my ORD-0276 face onto the frozen dist, so another lane's file-sync can't blank my readings.

Stops only the pid my own state file recorded, starts `vite preview` against `dist_frozen`, and proves the
served bundle by asset name + sha256 read out of the running face (not off disk).
"""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import subprocess
import time
import urllib.request

BASE = pathlib.Path('D:/moodle/_hjp3_0276_0925')
FROZEN = BASE / 'dist_frozen'
FACE_CWD = pathlib.Path('D:/moodle/_hjp3_ord0261_0923/snap_e3b0b47/frontend')
PY = 'D:/moodle/CityNexus/.venv/Scripts/python.exe'
BACKEND_PORT, FACE_PORT = 8493, 8494
OLD_PIDS = pathlib.Path('D:/moodle/_hjp3_0279x_0925/o0279x_pids.json')
STATE = BASE / 'face_state.json'
DETACHED = 0x00000008 | 0x00000200


def listening(port):
    out = subprocess.run(['netstat', '-ano'], capture_output=True, text=True,
                         encoding='utf-8', errors='replace').stdout
    return [ln.split()[-1] for ln in out.splitlines()
            if ('127.0.0.1:%d ' % port) in ln and 'LISTENING' in ln]


old = json.loads(OLD_PIDS.read_text(encoding='utf-8'))
killed = {}
r = subprocess.run(['taskkill', '/PID', str(old['face']), '/T', '/F'], capture_output=True, text=True)
killed['old_face'] = {'pid': old['face'], 'rc': r.returncode}
time.sleep(2)

env = dict(os.environ)
env['CITYNEXUS_BACKEND_PORT'] = str(BACKEND_PORT)
env['CITYNEXUS_DATABASE_URL'] = 'sqlite:///D:/moodle/_hjp3_0279x_0925/o0279x.s3db'
env.pop('DEEPSEEK_API_KEY', None)
log = open(BASE / 'face_frozen.log', 'w', encoding='utf-8', errors='replace')
f = subprocess.Popen(['node', 'node_modules/vite/bin/vite.js', 'preview', '--outDir', str(FROZEN),
                      '--port', str(FACE_PORT), '--host', '127.0.0.1', '--strictPort'],
                     cwd=str(FACE_CWD), env=env, creationflags=DETACHED, stdout=log, stderr=subprocess.STDOUT)
for _ in range(90):
    if listening(FACE_PORT):
        break
    time.sleep(1)

req = urllib.request.Request('http://127.0.0.1:%d/' % FACE_PORT)
html = urllib.request.urlopen(req, timeout=60).read().decode('utf-8', 'replace')
import re
asset = re.findall(r'assets/(index-[A-Za-z0-9_-]+\.js)', html)[0]
raw = urllib.request.urlopen('http://127.0.0.1:%d/assets/%s' % (FACE_PORT, asset), timeout=120).read()
disk = (FROZEN / 'assets' / asset).read_bytes()
out = {'killed': killed, 'new_face_pid': f.pid, 'listening_face': listening(FACE_PORT),
       'listening_backend': listening(BACKEND_PORT), 'served_asset': asset,
       'served_bytes': len(raw), 'served_sha256': hashlib.sha256(raw).hexdigest(),
       'matches_frozen_disk_bytes': raw == disk,
       'frozen_proof': json.loads((BASE / 'dist_frozen_proof.json').read_text(encoding='utf-8'))}
STATE.write_text(json.dumps({'face_pid': f.pid, **out}, ensure_ascii=False, indent=1), encoding='utf-8')
print(json.dumps({k: v for k, v in out.items() if k != 'frozen_proof'}, ensure_ascii=False, indent=1))
