"""ORD-0279-X services: the LANDED generation on its own one-time ports.

Only the tree changes versus ORD-0279: backend :8493 runs `dcae1bc9…` against a fresh ensure_schema() DB,
face :8494 serves the same published bundle bytes with its proxy pinned to :8493.  The previous pair
(:8497/:8498, tree c79e2b4) is left running on purpose - it is the control arm of this comparison and
the commander asked me not to stop it.

  start / seed / own / stop        - as named; ownership is proved two-way before any leg is believed
  lock <seconds>                   - bounded write-lock holder on MY new DB, self-proved in the same run
"""
from __future__ import annotations

import json
import os
import pathlib
import sqlite3
import subprocess
import sys
import time
import urllib.error
import urllib.request
import uuid

BASE = pathlib.Path('D:/moodle/_hjp3_0279x_0925')
TIP = 'dcae1bc964125c3a975916f6bf667794cc19622a'
BACKEND_DIR = BASE / 'snap_tip' / ('CityNexus-' + TIP) / 'backend'
FACE_CWD = pathlib.Path('D:/moodle/_hjp3_ord0261_0923/snap_e3b0b47/frontend')
OUTDIR = pathlib.Path('D:/moodle/_hjp3_fan_sweep_0923/snap_live_dist')
DB = BASE / 'o0279x.s3db'
PY = 'D:/moodle/CityNexus/.venv/Scripts/python.exe'
BP, FP = 8493, 8494
FACE = 'http://127.0.0.1:%d' % FP
BE = 'http://127.0.0.1:%d' % BP
PIDS = BASE / 'o0279x_pids.json'
STATE = BASE / 'o0279x_state.json'
DETACHED = 0x00000008 | 0x00000200


def http(method, url, payload=None, timeout=90):
    data = None
    req = urllib.request.Request(url, method=method)
    if payload is not None:
        data = json.dumps(payload).encode()
        req.add_header('Content-Type', 'application/json')
    try:
        with urllib.request.urlopen(req, data, timeout=timeout) as r:
            return r.status, r.read().decode('utf-8', 'replace')
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode('utf-8', 'replace')
    except Exception as e:  # noqa: BLE001
        return 'ERR', str(e)[:200]


def listening(port):
    out = subprocess.run(['netstat', '-ano'], capture_output=True, text=True,
                         encoding='utf-8', errors='replace').stdout
    return [ln.split()[-1] for ln in out.splitlines()
            if ('127.0.0.1:%d ' % port) in ln and 'LISTENING' in ln]


def env_base():
    e = dict(os.environ)
    e['CITYNEXUS_DATABASE_URL'] = 'sqlite:///' + str(DB).replace('\\', '/')
    e['PYTHONPATH'] = str(BACKEND_DIR)
    e.pop('DEEPSEEK_API_KEY', None)
    e['CITYNEXUS_AI_ENABLED'] = 'false'
    return e


def do_start():
    if listening(BP) or listening(FP):
        raise SystemExit('refusing to start: %d/%d already taken' % (BP, FP))
    for p in (DB, pathlib.Path(str(DB) + '-wal'), pathlib.Path(str(DB) + '-shm')):
        if p.exists():
            p.unlink()
    env = env_base()
    log = open(BASE / 'o0279x_backend.log', 'w', encoding='utf-8', errors='replace')
    b = subprocess.Popen([PY, '-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', str(BP),
                          '--log-level', 'info'], cwd=str(BACKEND_DIR), env=env, creationflags=DETACHED,
                         stdout=log, stderr=subprocess.STDOUT)
    fenv = dict(env)
    fenv['CITYNEXUS_BACKEND_PORT'] = str(BP)
    flog = open(BASE / 'o0279x_face.log', 'w', encoding='utf-8', errors='replace')
    f = subprocess.Popen(['node', 'node_modules/vite/bin/vite.js', 'preview', '--outDir', str(OUTDIR),
                          '--port', str(FP), '--host', '127.0.0.1', '--strictPort'],
                         cwd=str(FACE_CWD), env=fenv, creationflags=DETACHED,
                         stdout=flog, stderr=subprocess.STDOUT)
    PIDS.write_text(json.dumps({'backend': b.pid, 'face': f.pid}), encoding='utf-8')
    for _ in range(90):
        if listening(BP) and listening(FP):
            break
        time.sleep(1)
    print(json.dumps({'backend_pid': b.pid, 'face_pid': f.pid, 'listening_backend': listening(BP),
                      'listening_face': listening(FP),
                      'face_root_http': http('GET', FACE + '/', timeout=30)[0]}, ensure_ascii=False))


def do_seed():
    """Catalog for the demo city in-process (the 0272 rig's stage recipe), journey over HTTP."""
    helper = BASE / 'o0279x_seed_helper.py'
    helper.write_text('\n'.join([
        'import json',
        'from app.db.session import ensure_schema, SessionLocal',
        'from app.db.models import Place',
        'from app.services import seed_demo',
        'from sqlalchemy import func, select',
        'ensure_schema()',
        's = SessionLocal()',
        'n = int(s.scalar(select(func.count()).select_from(Place).where(Place.city_code == "CNX-DEMO")) or 0)',
        'seeded = n == 0',
        'if seeded:',
        '    seed_demo(s); s.commit()',
        'n2 = int(s.scalar(select(func.count()).select_from(Place).where(Place.city_code == "CNX-DEMO")) or 0)',
        'print("SEEDRESULT", json.dumps({"places_before": n, "seeded_by_this_call": seeded, "places_after": n2}))',
    ]), encoding='utf-8')
    import ast
    ast.parse(helper.read_text(encoding='utf-8'))
    r = subprocess.run([PY, str(helper)], cwd=str(BACKEND_DIR), env=env_base(),
                       capture_output=True, text=True, encoding='utf-8', errors='replace')
    seed_line = [l for l in r.stdout.splitlines() if l.startswith('SEEDRESULT ')]
    st_t, raw_t = http('POST', FACE + '/api/v1/travelers',
                       {'display_name': 'HJP3 ORD-0279-X verifier', 'timezone': 'Asia/Shanghai'})
    trav = json.loads(raw_t) if st_t == 201 else {}
    st_j, raw_j = http('POST', FACE + '/api/v1/journeys', {
        'traveler_id': trav.get('id'), 'title': 'HJP3 ORD-0279-X one-time', 'city_code': 'CNX-DEMO',
        'timezone': 'Asia/Shanghai', 'start_at': '2026-09-26T10:00:00+08:00',
        'end_at': '2026-09-27T20:00:00+08:00',
        'budget': {'amount_minor': 300000, 'currency': 'CNY'},
        'stay_budget': {'amount_minor': 100000, 'currency': 'CNY'}, 'party_size': 2})
    jrn = json.loads(raw_j) if st_j == 201 else {}
    out = {'seed_rc': r.returncode, 'seed': json.loads(seed_line[0][11:]) if seed_line else r.stderr[-300:],
           'traveler_http': st_t, 'traveler_id': trav.get('id'),
           'journey_http': st_j, 'journey_id': jrn.get('id'), 'journey_city': jrn.get('city_code')}
    STATE.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding='utf-8')
    print(json.dumps(out, ensure_ascii=False))


def do_own():
    s = json.loads(STATE.read_text(encoding='utf-8'))
    mine, _ = http('GET', FACE + '/api/v1/journeys/' + s['journey_id'], timeout=30)
    foreign, _ = http('GET', FACE + '/api/v1/journeys/' + str(uuid.UUID(int=0xC0FFEE)), timeout=30)
    direct, _ = http('GET', BE + '/api/v1/journeys/' + s['journey_id'], timeout=30)
    print(json.dumps({'mine_via_face': mine, 'foreign_via_face': foreign, 'mine_direct_backend': direct,
                      'verdict': 'PROXY_IS_MINE' if (mine == 200 and foreign == 404) else 'NOT_OWNED'},
                     ensure_ascii=False))


def do_lock(secs: int):
    h = sqlite3.connect(str(DB), isolation_level=None)
    h.execute('BEGIN IMMEDIATE')
    h.execute('UPDATE journeys SET title = title')
    print('HELD at %s rows_touched=%d' % (time.strftime('%H:%M:%S'),
                                          h.execute('SELECT changes()').fetchone()[0]), flush=True)
    p = sqlite3.connect(str(DB), timeout=0)
    try:
        p.execute('BEGIN IMMEDIATE')
        p.execute('UPDATE journeys SET title = title')
        p.commit()
        print('SELFPROOF: second writer WROTE - instrument did NOT hold the lock', flush=True)
    except sqlite3.OperationalError as e:
        print('SELFPROOF: second writer refused with %r at %s' % (str(e), time.strftime('%H:%M:%S')), flush=True)
    finally:
        p.close()
    print('ARMED - browser legs may fire now', flush=True)
    time.sleep(secs)
    h.execute('ROLLBACK')
    h.close()
    print('RELEASED at %s' % time.strftime('%H:%M:%S'), flush=True)


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
    cmd = sys.argv[1]
    {'start': do_start, 'seed': do_seed, 'own': do_own, 'stop': do_stop}[cmd]() if cmd != 'lock' \
        else do_lock(int(sys.argv[2]))
