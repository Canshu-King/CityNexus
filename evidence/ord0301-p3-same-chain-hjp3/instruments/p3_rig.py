"""ORD-0301 pass 3, stage 2: the rig - new name, because instrument paths are never rewritten.

Same boundaries as the published `c2_rig.py`, and stated here rather than inherited:
  * my ports only (8651-8654), listed by name in the teardown;
  * a one-time sqlite file per generation, created by the product's own `ensure_schema()` and deleted before
    the run (R-SCHEMA-01: fresh or no run);
  * private outDirs under my own batch directory, built by me from `git archive` exports - the product tree
    is never written to;
  * the phone chain (:4781/:4782) and the tunnel are not entered by this rig; the shared
    `_live.db` / `_preview.db` are never opened; `demo/reset` is never called;
  * `DEEPSEEK_API_KEY` is popped from every child environment, and AI is disabled, so no credential can be
    sent or printed from an arm;
  * a listener is only closed when its own command line names the exact port I opened, because the socket
    holder is a child of the pid I recorded (the venv launcher re-execs).

Two generations are runnable here and nothing else: `dep` is the commit whose build is byte-identical to the
asset the shared page references (proved in `served_generation_bind_c2.json`), `old` is the unguarded commit
the commander's 21:5x note put the phone on. Which is which is a reading, not a belief: each arm records the
tip it launched from and the bundle it served.
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

BASE = pathlib.Path('D:/moodle/_hjp3_0301p3_0925')
PY = 'D:/moodle/CityNexus/.venv/Scripts/python.exe'
VITE = 'D:/moodle/CityNexus/frontend/node_modules/vite/bin/vite.js'
PROXY_SCRIPT = pathlib.Path('D:/moodle/HJ-P3_evidence/p3proxy.py')
GEN = {'dep': {'tip': '7856e03f6238da3000976eb6e690a448dfa39b9a',
               'snap': BASE / 'snap_7856e03f', 'dist': BASE / 'dist_7856e03f'},
       'old': {'tip': 'dc964086c9d412573ac19d70b24b30e6c3ee6168',
               'snap': BASE / 'snap_dc964086', 'dist': BASE / 'dist_dc964086'}}
PORTS = {'backend': 8651, 'proxy': 8652, 'face_dep': 8653, 'face_old': 8654}
DETACHED = 0x00000008 | 0x00000200
STATE = BASE / 'p3_rig_state.json'
PIDS = BASE / 'p3_rig_pids.json'


def snap(which):
    return GEN[which]['snap']


def dist(which):
    return GEN[which]['dist']


def db_for(which):
    return BASE / ('p3_%s.s3db' % which)


def listening(port):
    out = subprocess.run(['netstat', '-ano'], capture_output=True, text=True,
                         encoding='utf-8', errors='replace').stdout
    return sorted({ln.split()[-1] for ln in out.splitlines()
                   if ('127.0.0.1:%d ' % port) in ln and 'LISTENING' in ln})


def cmdline(pid):
    ps = ("Get-CimInstance Win32_Process -Filter 'ProcessId=%s' | "
          'Select-Object -ExpandProperty CommandLine' % pid)
    return subprocess.run(['powershell', '-NoProfile', '-Command', ps], capture_output=True,
                          text=True, encoding='utf-8', errors='replace').stdout.strip()


def http(method, url, payload=None, timeout=120, headers=None):
    data = json.dumps(payload).encode() if payload is not None else None
    r = urllib.request.Request(url, method=method, data=data)
    for k, v in (headers or {}).items():
        r.add_header(k, v)
    if data:
        r.add_header('Content-Type', 'application/json')
    try:
        with urllib.request.urlopen(r, timeout=timeout) as f:
            return f.status, f.read().decode('utf-8', 'replace')
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode('utf-8', 'replace')
    except Exception as e:  # noqa: BLE001
        return None, str(e)[:200]


def env_base(which, extra=None):
    e = dict(os.environ)
    e['CITYNEXUS_DATABASE_URL'] = 'sqlite:///' + str(db_for(which)).replace('\\', '/')
    e['PYTHONPATH'] = str(snap(which) / 'backend')
    e.pop('DEEPSEEK_API_KEY', None)
    e['CITYNEXUS_AI_ENABLED'] = 'false'
    e.update(extra or {})
    return e


def spawn(args, cwd, env, logfile, tag):
    log = open(BASE / logfile, 'w', encoding='utf-8', errors='replace')
    p = subprocess.Popen(args, cwd=str(cwd), env=env, creationflags=DETACHED, stdout=log,
                         stderr=subprocess.STDOUT)
    return {'tag': tag, 'pid': p.pid, 'cmdline': ' '.join(str(a) for a in args)[:260]}


def wait_port(port, secs=150):
    t0 = time.time()
    while time.time() - t0 < secs:
        if listening(port):
            return True
        time.sleep(1)
    return False


def start_backend(which, stamp):
    close_my_ports()
    for p in (db_for(which), pathlib.Path(str(db_for(which)) + '-wal'),
              pathlib.Path(str(db_for(which)) + '-shm')):
        if p.exists():
            p.unlink()
    if listening(PORTS['backend']):
        raise SystemExit('port %d already taken - refuse to share' % PORTS['backend'])
    # one access log per RUN: a shared filename meant every new backend truncated the previous arm's lines
    name = 'p3_backend_access_%s.log' % stamp
    rec = spawn([PY, '-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1',
                 '--port', str(PORTS['backend']), '--log-level', 'info', '--access-log'],
                snap(which) / 'backend', env_base(which), name, 'backend_' + which)
    rec['up'] = wait_port(PORTS['backend'])
    rec['access_log_path'] = str(BASE / name)
    return rec


def start_proxy(which, mode, spec=None):
    if listening(PORTS['proxy']):
        raise SystemExit('port %d already taken' % PORTS['proxy'])
    env = env_base(which, {'P3_UPSTREAM_PORT': str(PORTS['backend']),
                           'P3_PAIR_LOG': str(BASE / 'p3_pair_log.jsonl'),
                           'P3_PROXY_MODE': mode,
                           'P3_ANSWER_SPEC': json.dumps(spec, ensure_ascii=False) if spec else '',
                           'P3_LOCK_DB': str(db_for(which)) if mode == 'lock_behind_hop' else '',
                           'P3_LOCK_HOLD_SECS': '45',
                           'PYTHONIOENCODING': 'utf-8'})
    rec = spawn(['python', str(PROXY_SCRIPT), str(PORTS['proxy'])], BASE, env, 'p3_proxy.log', 'proxy')
    rec['up'] = wait_port(PORTS['proxy'])
    rec['mode'] = mode
    rec['spec'] = spec
    return rec


def start_face(which):
    port = PORTS['face_' + which]
    if listening(port):
        raise SystemExit('port %d already taken' % port)
    env = env_base(which, {'CITYNEXUS_BACKEND_PORT': str(PORTS['proxy'])})
    rec = spawn(['node', VITE, 'preview', '--outDir', str(dist(which)), '--port', str(port),
                 '--host', '127.0.0.1', '--strictPort'],
                snap(which) / 'frontend', env, 'p3_face_%s.log' % which, 'face_' + which)
    rec['up'] = wait_port(port)
    rec['port'] = port
    rec['served_from'] = str(dist(which))
    return rec


def identity_probe(jid):
    """Two-sided, through the chain: my journey must answer 200 and echo, a bogus one must 404."""
    a, ra = http('GET', 'http://127.0.0.1:%d/api/v1/journeys/%s' % (PORTS['proxy'], jid))
    b, rb = http('GET', 'http://127.0.0.1:%d/api/v1/journeys/00000000-0000-0000-0000-000000000000'
                 % PORTS['proxy'])
    return {'mine_status': a, 'mine_echoes': ('"%s"' % jid) in (ra or ''),
            'bogus_status': b, 'two_sided': bool(a == 200 and ('"%s"' % jid) in (ra or '') and b == 404)}


def seed_journey(which):
    helper = BASE / 'p3_seed_helper.py'
    helper.write_text(chr(10).join([
        'import json',
        'from app.db.session import ensure_schema, SessionLocal',
        'from app.db.models import Place',
        'from app.services import seed_demo',
        'from sqlalchemy import func, select',
        'ensure_schema()',
        's = SessionLocal()',
        'n0 = int(s.scalar(select(func.count()).select_from(Place)) or 0)',
        'n = int(s.scalar(select(func.count()).select_from(Place).where(Place.city_code == "CNX-DEMO")) or 0)',
        'seeded = n == 0',
        'if seeded:',
        '    seed_demo(s); s.commit()',
        'n2 = int(s.scalar(select(func.count()).select_from(Place).where(Place.city_code == "CNX-DEMO")) or 0)',
        'print("SEEDRESULT", json.dumps({"places_before": n0, "demo_places_before": n,',
        '                                "seeded_by_this_call": seeded, "demo_places_after": n2}))',
    ]), encoding='utf-8')
    import ast
    ast.parse(helper.read_text(encoding='utf-8'))
    # seeded against THIS generation's own database with THIS generation's own code
    r = subprocess.run([PY, str(helper)], cwd=str(snap(which) / 'backend'), env=env_base(which),
                       capture_output=True, text=True, encoding='utf-8', errors='replace')
    line = [x for x in r.stdout.splitlines() if x.startswith('SEEDRESULT ')]
    face = 'http://127.0.0.1:%d' % PORTS['proxy']
    st_t, raw_t = http('POST', face + '/api/v1/travelers',
                       {'display_name': 'HJP3 p3 same-chain', 'timezone': 'Asia/Shanghai'})
    trav = json.loads(raw_t) if st_t == 201 else {}
    st_j, raw_j = http('POST', face + '/api/v1/journeys', {
        'traveler_id': trav.get('id'), 'title': 'HJP3 p3 one-time', 'city_code': 'CNX-DEMO',
        'timezone': 'Asia/Shanghai', 'start_at': '2026-09-26T10:00:00+08:00',
        'end_at': '2026-09-27T20:00:00+08:00',
        'budget': {'amount_minor': 300000, 'currency': 'CNY'},
        'stay_budget': {'amount_minor': 100000, 'currency': 'CNY'}, 'party_size': 2})
    jrn = json.loads(raw_j) if st_j == 201 else {}
    return {'seed_rc': r.returncode,
            'seed': json.loads(line[0][11:]) if line else (r.stderr or '')[-300:],
            'traveler_http': st_t, 'journey_http': st_j, 'journey_id': jrn.get('id')}


def do_start(which, mode, spec=None):
    BASE.mkdir(exist_ok=True)
    stamp = time.strftime('%H%M%S')
    if not (snap(which) / 'backend').exists() or not (dist(which) / 'index.html').exists():
        raise SystemExit('run p3_setup.py first: missing %s or %s'
                         % (snap(which) / 'backend', dist(which) / 'index.html'))
    out = {'which': which, 'tip': GEN[which]['tip'], 'proxy_mode': mode, 'spec': spec,
           'started_at': time.strftime('%H:%M:%S'), 'stamp': stamp}
    out['backend'] = start_backend(which, stamp)
    out['proxy'] = start_proxy(which, mode, spec)
    out['face'] = start_face(which)
    out['seed'] = seed_journey(which)
    out['identity'] = identity_probe(out['seed']['journey_id'] or '')
    (BASE / ('p3_rig_state_%s_%s_%s.json' % (which, mode, stamp))).write_text(
        json.dumps(out, ensure_ascii=False, indent=1), encoding='utf-8', newline='\n')
    STATE.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding='utf-8', newline='\n')
    PIDS.write_text(json.dumps({'backend': out['backend']['pid'], 'proxy': out['proxy']['pid'],
                                'face': out['face']['pid']}, ensure_ascii=False), encoding='utf-8')
    print(json.dumps({k: out[k] for k in ('which', 'tip', 'proxy_mode', 'stamp')}, ensure_ascii=False),
          '| backend up:', out['backend']['up'], '| proxy up:', out['proxy']['up'],
          '| face up:', out['face']['up'], '| identity two-sided:', out['identity']['two_sided'])
    if not (out['backend']['up'] and out['proxy']['up'] and out['face']['up']
            and out['identity']['two_sided']):
        raise SystemExit('the rig is not fully mine - nothing will be measured')


def sqlite_conn(which, timeout=30):
    return sqlite3.connect(str(db_for(which)), timeout=timeout, isolation_level=None)


def do_lock(which, spec):
    """Take the write lock AFTER the page has opened the sheet, so the hub still renders and the only
    thing the traveller's press meets is a contended write (the ORD-0301 recipe)."""
    plan = [int(x) for x in str(spec).split(',')]
    ready = BASE / 'p3_sheet_ready.flag'
    if ready.exists():
        ready.unlink()
    for k, secs in enumerate(plan):
        t0 = time.time()
        while not ready.exists():
            if time.time() - t0 > 180:
                raise SystemExit('p3_sheet_ready.flag never appeared')
            time.sleep(0.2)
        h = sqlite_conn(which)
        h.execute('BEGIN IMMEDIATE')
        h.execute('UPDATE journeys SET title = title')
        print('HELD round %d rows_touched=%d' % (k + 1, h.execute('SELECT changes()').fetchone()[0]),
              flush=True)
        p = sqlite_conn(which, timeout=0)
        try:
            p.execute('BEGIN IMMEDIATE')
            print('SELFPROOF FAILED: a second writer got in', flush=True)
        except Exception as e:  # noqa: BLE001
            print('SELFPROOF: second writer refused: %s' % str(e)[:70], flush=True)
        finally:
            p.close()
        time.sleep(secs)
        h.execute('ROLLBACK')
        h.close()
        print('RELEASED round %d' % (k + 1), flush=True)
        ready.unlink()


def mine_signature(cmd, name, port):
    return (('app.main:app' in cmd and ('--port %d' % port) in cmd and '--host 127.0.0.1' in cmd)
            or ('p3proxy.py %d' % port) in cmd
            or ('vite.js' in cmd and ('--port %d' % port) in cmd))


def close_my_ports():
    closed = {}
    for name, port in PORTS.items():
        for pid in listening(port):
            cmd = cmdline(pid)
            mine = mine_signature(cmd, name, port)
            rec = {'pid': int(pid), 'cmdline_is_my_launch_signature_for_this_port': mine,
                   'cmd_head': cmd[:150]}
            if mine:
                r = subprocess.run(['taskkill', '/PID', str(pid), '/T', '/F'], capture_output=True,
                                   text=True, encoding='utf-8', errors='replace')
                rec['taskkill_rc'] = r.returncode
            else:
                rec['left_alone'] = True
            closed.setdefault(name, []).append(rec)
    time.sleep(2)
    return closed


def do_stop():
    out = {'recorded_pids': {}, 'listeners': close_my_ports()}
    pids = json.loads(PIDS.read_text(encoding='utf-8')) if PIDS.exists() else {}
    for tag, pid in pids.items():
        cmd = cmdline(pid)
        r = subprocess.run(['taskkill', '/PID', str(pid), '/T', '/F'], capture_output=True, text=True,
                           encoding='utf-8', errors='replace')
        out['recorded_pids'][tag] = {'pid': pid,
                                     'cmdline_is_mine': ('app.main:app' in cmd or 'p3proxy.py' in cmd
                                                         or 'vite.js' in cmd),
                                     'rc': r.returncode, 'cmd_head': cmd[:120]}
    out['listeners'] = close_my_ports()
    out['listening_after'] = {k: listening(v) for k, v in PORTS.items()}
    out['all_my_ports_free'] = not any(out['listening_after'].values())
    (BASE / ('p3_teardown_%s.json' % time.strftime('%H%M%S'))).write_text(
        json.dumps(out, ensure_ascii=False, indent=1), encoding='utf-8', newline=chr(10))
    print(json.dumps(out, ensure_ascii=False))


def do_ports():
    print(json.dumps({k: listening(v) for k, v in PORTS.items()}, ensure_ascii=False))


if __name__ == '__main__':
    cmd = sys.argv[1]
    if cmd == 'start':
        sp = None
        if len(sys.argv) > 4 and sys.argv[4].startswith('{'):
            sp = json.loads(sys.argv[4])
        elif len(sys.argv) > 4 and pathlib.Path(sys.argv[4]).exists():
            sp = json.loads(pathlib.Path(sys.argv[4]).read_text(encoding='utf-8'))
        do_start(sys.argv[2], sys.argv[3], sp)
    elif cmd == 'lock':
        do_lock(sys.argv[2], sys.argv[3])
    elif cmd == 'stop':
        do_stop()
    elif cmd == 'ports':
        do_ports()
    else:
        raise SystemExit('unknown command')
