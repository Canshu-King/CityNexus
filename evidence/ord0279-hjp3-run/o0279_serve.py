"""ORD-0279 rig, part 2: start / seed / stop the two one-time services, plus ownership proof.

Names are mine and fresh: backend :8497 serves ONLY the one-time DB built by ensure_schema();
face :8498 serves the published-generation bundle copy (index-ChOTTCvB.js) whose proxy target is
pinned to :8497 by CITYNEXUS_BACKEND_PORT.  Nothing here touches :4781/:4782, the user libraries,
or any other lane's port.

  start  spawn detached, wait for both listeners, record pids
  seed   create one traveler + one journey through the FACE (so the proxy is proven in use)
  own    two-way ownership proof: my row answers 200 through the face, a foreign uuid answers 404
  stop   terminate only the pids this file recorded, then re-count listeners
"""
from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys
import time
import urllib.error
import urllib.request
import uuid

BASE = pathlib.Path('D:/moodle/_hjp3_0279_0924')
TIP = 'c79e2b4f4efe414dba22a071a7136ae10b5c84aa'
BACKEND_DIR = BASE / 'snap_tip' / ('CityNexus-' + TIP) / 'backend'
FACE_CWD = pathlib.Path('D:/moodle/_hjp3_ord0261_0923/snap_e3b0b47/frontend')
OUTDIR = pathlib.Path('D:/moodle/_hjp3_fan_sweep_0923/snap_live_dist')
DB = BASE / 'o0279.s3db'
PY = 'D:/moodle/CityNexus/.venv/Scripts/python.exe'
BP, FP = 8497, 8498
FACE = 'http://127.0.0.1:%d' % FP
BE = 'http://127.0.0.1:%d' % BP
PIDS = BASE / 'o0279_pids.json'
STATE = BASE / 'o0279_state.json'
DETACHED = 0x00000008 | 0x00000200  # DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP


def http(method, url, payload=None, timeout=90):
    data = None
    req = urllib.request.Request(url, method=method)
    if payload is not None:
        data = json.dumps(payload).encode()
        req.add_header('Content-Type', 'application/json')
    try:
        with urllib.request.urlopen(req, data, timeout=timeout) as r:
            raw = r.read().decode('utf-8', 'replace')
            return r.status, raw
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode('utf-8', 'replace')
    except Exception as e:  # noqa: BLE001 - transport failure is a reading, not a crash
        return 'ERR', str(e)[:200]


def listening(port):
    out = subprocess.run(['netstat', '-ano'], capture_output=True, text=True,
                         encoding='utf-8', errors='replace').stdout
    return [ln.split()[-1] for ln in out.splitlines()
            if ('127.0.0.1:%d ' % port) in ln and 'LISTENING' in ln]


def env_base():
    env = dict(os.environ)
    env['CITYNEXUS_DATABASE_URL'] = 'sqlite:///' + str(DB).replace('\\', '/')
    env.pop('DEEPSEEK_API_KEY', None)
    env['CITYNEXUS_AI_ENABLED'] = 'false'
    return env


def do_start():
    if listening(BP) or listening(FP):
        raise SystemExit('refusing to start: one of my ports %d/%d is already taken' % (BP, FP))
    env = env_base()
    b = subprocess.Popen([PY, '-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1',
                          '--port', str(BP), '--log-level', 'info'],
                         cwd=str(BACKEND_DIR), env=env, creationflags=DETACHED,
                         stdout=open(BASE / 'o0279_backend.log', 'w', encoding='utf-8', errors='replace'),
                         stderr=subprocess.STDOUT)
    fenv = dict(env)
    fenv['CITYNEXUS_BACKEND_PORT'] = str(BP)
    f = subprocess.Popen(['node', 'node_modules/vite/bin/vite.js', 'preview', '--outDir', str(OUTDIR),
                          '--port', str(FP), '--host', '127.0.0.1', '--strictPort'],
                         cwd=str(FACE_CWD), env=fenv, creationflags=DETACHED,
                         stdout=open(BASE / 'o0279_face.log', 'w', encoding='utf-8', errors='replace'),
                         stderr=subprocess.STDOUT)
    PIDS.write_text(json.dumps({'backend': b.pid, 'face': f.pid}), encoding='utf-8')
    for _ in range(60):
        if listening(BP) and listening(FP):
            break
        time.sleep(1)
    st, raw = http('GET', BE + '/api/v1/travelers', timeout=30)
    print(json.dumps({'backend_pid': b.pid, 'face_pid': f.pid,
                      'listening_backend': listening(BP), 'listening_face': listening(FP),
                      'backend_probe_http': st,
                      'face_root_http': http('GET', FACE + '/', timeout=30)[0]}, ensure_ascii=False))


def _state():
    return json.loads(STATE.read_text(encoding='utf-8')) if STATE.exists() else {}


def do_seed():
    st, raw = http('POST', FACE + '/api/v1/travelers',
                   {'display_name': 'HJP3 ORD-0279 verifier', 'timezone': 'Asia/Shanghai'})
    trav = json.loads(raw) if isinstance(raw, str) and st == 201 else None
    jid = None
    if trav:
        st2, raw2 = http('POST', FACE + '/api/v1/journeys', {
            'traveler_id': trav['id'], 'title': 'HJP3 ORD-0279 one-time', 'city_code': 'CN-BEIJING',
            'timezone': 'Asia/Shanghai', 'start_at': '2026-09-26T10:00:00+08:00',
            'end_at': '2026-09-27T20:00:00+08:00',
            'budget': {'amount_minor': 300000, 'currency': 'CNY'},
            'stay_budget': {'amount_minor': 100000, 'currency': 'CNY'}, 'party_size': 2})
        jid = json.loads(raw2)['id'] if st2 in (200, 201) else None
    out = {'traveler_http': st, 'traveler_id': (trav or {}).get('id'), 'journey_http': st2 if trav else None,
           'journey_id': jid, 'seeded_via': FACE + '/api/v1 (through the face proxy)'}
    s = _state()
    s.update(out)
    STATE.write_text(json.dumps(s, ensure_ascii=False, indent=1), encoding='utf-8')
    print(json.dumps(out, ensure_ascii=False))


def do_own():
    s = _state()
    mine, _ = http('GET', FACE + '/api/v1/journeys/' + s['journey_id'], timeout=30)
    foreign, _ = http('GET', FACE + '/api/v1/journeys/' + str(uuid.UUID(int=0xC0FFEE)), timeout=30)
    direct, _ = http('GET', BE + '/api/v1/journeys/' + s['journey_id'], timeout=30)
    print(json.dumps({'mine_via_face': mine, 'foreign_via_face': foreign, 'mine_direct_backend': direct,
                      'verdict': 'PROXY_IS_MINE' if (mine == 200 and foreign == 404) else 'NOT_OWNED'},
                     ensure_ascii=False))


def do_stop():
    p = json.loads(PIDS.read_text(encoding='utf-8')) if PIDS.exists() else {}
    killed = {}
    for name, pid in p.items():
        r = subprocess.run(['taskkill', '/PID', str(pid), '/T', '/F'], capture_output=True, text=True)
        killed[name] = {'pid': pid, 'rc': r.returncode}
    time.sleep(2)
    print(json.dumps({'killed': killed, 'listening_backend': listening(BP),
                      'listening_face': listening(FP)}, ensure_ascii=False))


if __name__ == '__main__':
    {'start': do_start, 'seed': do_seed, 'own': do_own, 'stop': do_stop}[sys.argv[1]]()
