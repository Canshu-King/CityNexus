"""N1/N2 runtime rig for the 0262-NARROW candidate: does a named busy rejection actually ship
inside the product's own error() envelope, and does every reachable write site get there
(or escape to the framework's bare 21-byte face)?

Isolation as ordered: one-time SQLite file, one-time named ports, only my own seeded
1 traveler + 1 journey, nothing read from or written to _live.db/_preview.db or any lane DB.
At the end the listener is really killed, the DB file is deleted and its absence is asserted.
"""
from __future__ import annotations

import json
import os
import pathlib
import sqlite3
import subprocess
import time
import urllib.error
import urllib.request
import uuid

BASE = pathlib.Path('D:/moodle/_hjp3_narrow_0924')
TREE = BASE / 'snap_3093eea/CityNexus-3093eea773c79fa00744fe72d1f2c43b4d0bd75e/backend'
DB = BASE / 'one_time_n1.db'
PY = 'C:/Users/仓鼠王/AppData/Roaming/uv/python/cpython-3.12.14-windows-x86_64-none/python.exe'
PORT = 8491
API = 'http://127.0.0.1:%d/api/v1' % PORT
OUT = BASE / 'n1_n2_runtime.json'

if DB.exists():
    DB.unlink()

env = dict(os.environ)
env['CITYNEXUS_DATABASE_URL'] = 'sqlite:///' + str(DB).replace('\\', '/')
env['CITYNEXUS_ENV'] = 'development'
env['PYTHONUNBUFFERED'] = '1'
log = open(BASE / 'one_time_backend.log', 'w', encoding='utf-8', errors='replace')
srv = subprocess.Popen([PY, '-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', str(PORT),
                        '--log-level', 'warning'], cwd=str(TREE), env=env, stdout=log, stderr=subprocess.STDOUT)

report = {'port': PORT, 'db': str(DB), 'tree': str(TREE), 'uvicorn_pid': srv.pid, 'steps': []}


def call(method, path, payload=None, timeout=90):
    url = API + path
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(url, method=method, data=data)
    req.add_header('Content-Type', 'application/json')
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            b = r.read()
            return {'method': method, 'path': path, 'http': r.status, 'ctype': r.headers.get('content-type'),
                    'bytes': len(b), 'secs': round(time.time() - t0, 2), 'body': b[:400].decode('utf-8', 'replace')}
    except urllib.error.HTTPError as e:
        b = e.read()
        return {'method': method, 'path': path, 'http': e.code, 'ctype': e.headers.get('content-type'),
                'bytes': len(b), 'secs': round(time.time() - t0, 2), 'body': b[:400].decode('utf-8', 'replace')}
    except Exception as e:
        return {'method': method, 'path': path, 'http': 'ERR', 'secs': round(time.time() - t0, 2),
                'err': type(e).__name__ + ':' + str(e)[:120]}


# wait for the one-time backend to come up
for _ in range(40):
    if srv.poll() is not None:
        report['steps'].append({'fatal': 'uvicorn exited early, see one_time_backend.log'})
        break
    try:
        urllib.request.urlopen('http://127.0.0.1:%d/api/v1/health' % PORT, timeout=3).read()
        break
    except Exception:
        time.sleep(1.5)

report['steps'].append(('health', call('GET', '/health')))

trav = call('POST', '/travelers', {'display_name': 'HJP3 verifier one-time', 'timezone': 'Asia/Shanghai'})
report['steps'].append(('traveler', trav))
traveler_id = None
try:
    traveler_id = json.loads(trav['body'])['id']
except Exception:
    pass
jrn = call('POST', '/journeys', {'traveler_id': traveler_id, 'title': 'HJP3 one-time N1',
                                 'city_code': 'CN-BEIJING', 'timezone': 'Asia/Shanghai',
                                 'start_at': '2026-09-25T10:00:00+08:00', 'end_at': '2026-09-26T20:00:00+08:00',
                                 'budget': {'amount_minor': 300000, 'currency': 'CNY'},
                                 'stay_budget': {'amount_minor': 100000, 'currency': 'CNY'},
                                 'party_size': 2})
report['steps'].append(('journey', jrn))
journey_id = None
try:
    journey_id = json.loads(jrn['body'])['id']
except Exception:
    pass

# control round: nobody holds the lock, so a 2xx here proves the 503 below is caused by contention
report['steps'].append(('R2_control_generate', call('POST', '/journeys/%s/stay-options/generate' % journey_id,
                                                    {'city_code': 'CN-BEIJING'})))

# hold an exclusive write transaction on the same file from a second connection
holder = sqlite3.connect(str(DB), isolation_level=None)
holder.execute('BEGIN IMMEDIATE')
holder.execute('UPDATE journeys SET title = title WHERE id = ?', (journey_id,))
report['steps'].append(('R3_generate_under_lock', call('POST', '/journeys/%s/stay-options/generate' % journey_id,
                                                       {'city_code': 'CN-BEIJING'})))
report['steps'].append(('R4_hydration_under_lock', call('POST', '/catalog-hydrations',
                                                        {'query': '护国寺小吃', 'journey_id': journey_id})))
report['steps'].append(('R5_agent_commands_under_lock', call('POST', '/journeys/%s/agent/commands' % journey_id,
                                                             {'user_text': '加一场傍晚的相声，别加钱。'})))
holder.execute('ROLLBACK')
holder.close()
report['steps'].append(('R6_control_after_release', call('POST', '/journeys/%s/stay-options/generate' % journey_id,
                                                         {'city_code': 'CN-BEIJING'})))

srv.terminate()
try:
    srv.wait(timeout=20)
except Exception:
    srv.kill()
time.sleep(1.5)
listeners = subprocess.run(['netstat', '-ano'], capture_output=True, text=True).stdout
port_still_open = any(('127.0.0.1:%d ' % PORT) in ln and 'LISTENING' in ln for ln in listeners.splitlines())
if DB.exists():
    DB.unlink()
for suffix in ('-wal', '-shm'):
    p = pathlib.Path(str(DB) + suffix)
    if p.exists():
        p.unlink()
report['cleanup'] = {'port_still_listening': port_still_open, 'db_exists_after_delete': DB.exists(),
                     'uvicorn_returncode': srv.returncode}
json.dump(report, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
for name, s in report['steps']:
    print('%-32s http=%-5s ctype=%-28s bytes=%-7s secs=%s' % (name, s.get('http'), str(s.get('ctype'))[:28],
                                                               s.get('bytes'), s.get('secs')))
    if 'R3' in name or 'R4' in name or 'R5' in name or 'R2' in name:
        print('    body:', str(s.get('body'))[:260])
print('cleanup:', report['cleanup'])
print('WROTE', OUT)
