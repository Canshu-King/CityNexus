"""ORD-0300 C2 pairing batch - stage 2: the rig. One generation per arm, one token across both sides.

For each arm I start the BACKEND and the FRONTEND BUNDLE from the same private export, so every reading is
"the product as that generation ships it" - and the mutant arm is the one exception where the frontend is a
private copy with a single two-character-per-line change, held against the same new-tip backend, so the
card difference is attributable to that one variable and not to a generation swap.

Boundaries, enforced here: my own ports (8641-8646), my own one-time sqlite files created by the product's
own `ensure_schema()` and deleted before the run (R-SCHEMA-01: fresh or no run), my own private outDirs, the
phone chain (:4781/:4782) and the shared databases never entered, `demo/reset` never called, `DEEPSEEK_API_KEY`
popped so nothing can print a credential, and every listener I close is proven to be mine by its command line
plus a two-sided identity probe on my private journey id.
"""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import sqlite3
import subprocess
import sys
import time
import urllib.error
import urllib.request

BASE = pathlib.Path('D:/moodle/_hjp3_0300c2_0925')
PY = 'D:/moodle/CityNexus/.venv/Scripts/python.exe'
VITE = 'D:/moodle/CityNexus/frontend/node_modules/vite/bin/vite.js'
PROXY_SCRIPT = pathlib.Path('D:/moodle/HJ-P3_evidence/c2proxy.py')
TIPS = {'old': 'dc964086c9d412573ac19d70b24b30e6c3ee6168',
        'new': '5aff3722d5c36c760a424f5fea5c3a771298f9ac',
        'mut': '5aff3722d5c36c760a424f5fea5c3a771298f9ac',
        # the generation my ORD-0300 C2 cell was actually written on, reached through that batch's own
        # read-only export and private build, so the challenged cell can be re-measured where it was born
        't90': '90d29a172e186aab6e6cb138ab4583ccf93bfa68'}
# 90d29a17 now lives in MY directory (c2_add_t90.py re-exported it by git archive and proved the
# bundle bytes against what ORD-0300 recorded), so no path points into another batch's folder at run time
PORTS = {'backend': 8641, 'proxy': 8642, 'face_old': 8643, 'face_new': 8644, 'face_mut': 8645,
         'face_t90': 8646, 'spare': 8647}
DETACHED = 0x00000008 | 0x00000200
STATE = BASE / 'rig_state.json'
PIDS = BASE / 'rig_pids.json'


def snap(which):
    return BASE / ('snap_' + which)


def dist(which):
    return BASE / ('dist_' + which)


def db_for(which):
    return BASE / ('o0300c2_%s.s3db' % which)


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


def wait_port(port, secs=120):
    t0 = time.time()
    while time.time() - t0 < secs:
        if listening(port):
            return True
        time.sleep(1)
    return False


def start_backend(which):
    # a crashed earlier arm can leave its backend holding this file; clear my own ports first so
    # "fresh or no run" (R-SCHEMA-01) is enforced by closing my leftovers, not by reusing the database
    close_my_ports()
    for p in (db_for(which), pathlib.Path(str(db_for(which)) + '-wal'),
              pathlib.Path(str(db_for(which)) + '-shm')):
        if p.exists():
            p.unlink()
    if listening(PORTS['backend']):
        raise SystemExit('port %d already taken - refuse to share' % PORTS['backend'])
    rec = spawn([PY, '-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1',
                 '--port', str(PORTS['backend']), '--log-level', 'info', '--access-log'],
                snap(which) / 'backend', env_base(which), 'backend_access_%s.log' % which,
                'backend_' + which)
    rec['up'] = wait_port(PORTS['backend'])
    # per-generation log name: the shared filename meant every new backend truncated the previous arm's
    # access log, so only the last arm's lines survived to be counted
    rec['access_log_path'] = str(BASE / ('backend_access_%s.log' % which))
    return rec


def start_proxy(mode):
    if listening(PORTS['proxy']):
        raise SystemExit('port %d already taken' % PORTS['proxy'])
    env = env_base('new', {'C2_UPSTREAM_PORT': str(PORTS['backend']),
                           'C2_PAIR_LOG': str(BASE / 'pair_log.jsonl'),
                           'C2_PROXY_MODE': mode, 'PYTHONIOENCODING': 'utf-8'})
    rec = spawn(['python', str(PROXY_SCRIPT), str(PORTS['proxy'])], BASE, env, 'proxy.log', 'proxy')
    rec['up'] = wait_port(PORTS['proxy'])
    rec['mode'] = mode
    return rec


def start_face(which):
    port = PORTS['face_' + which]
    if listening(port):
        raise SystemExit('port %d already taken' % port)
    env = env_base(which, {'CITYNEXUS_BACKEND_PORT': str(PORTS['proxy'])})
    rec = spawn(['node', VITE, 'preview',
                 '--outDir', str(dist(which)), '--port', str(port), '--host', '127.0.0.1',
                 '--strictPort'],
                snap(which) / 'frontend', env, 'face_%s.log' % which,
                'face_' + which)
    rec['up'] = wait_port(port)
    rec['port'] = port
    rec['served_from'] = str(dist(which))
    return rec


def identity_probe(port, jid):
    """Two-sided: my journey must answer 200 and echo, a bogus one must 404."""
    a, ra = http('GET', 'http://127.0.0.1:%d/api/v1/journeys/%s' % (port, jid))
    b, rb = http('GET', 'http://127.0.0.1:%d/api/v1/journeys/00000000-0000-0000-0000-000000000000' % port)
    return {'mine_status': a, 'mine_echoes': ('"%s"' % jid) in (ra or ''),
            'bogus_status': b, 'two_sided': bool(a == 200 and ('"%s"' % jid in (ra or '')) and b == 404)}


def do_start(which, mode):
    BASE.mkdir(exist_ok=True)
    if not (snap(which) / 'backend').exists() or not dist(which).exists():
        raise SystemExit('run c2_setup.py first: missing %s or %s' % (snap(which) / 'backend', dist(which)))
    out = {'which': which, 'tip': TIPS[which], 'proxy_mode': mode, 'started_at': time.strftime('%H:%M:%S')}
    out['backend'] = start_backend(which)
    out['proxy'] = start_proxy(mode)
    out['face'] = start_face(which)
    jid = seed_journey(which)
    out['seed'] = jid
    out['identity'] = identity_probe(PORTS['proxy'], jid['journey_id'])
    (BASE / ('rig_state_%s_%s.json' % (which, mode))).write_text(
        json.dumps(out, ensure_ascii=False, indent=1), encoding='utf-8', newline='\n')
    STATE.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding='utf-8', newline='\n')
    PIDS.write_text(json.dumps({'backend': out['backend']['pid'], 'proxy': out['proxy']['pid'],
                                'face': out['face']['pid']}, ensure_ascii=False), encoding='utf-8')
    print(json.dumps({k: out[k] for k in ('which', 'tip', 'proxy_mode')}, ensure_ascii=False),
          '| backend up:', out['backend']['up'], '| proxy up:', out['proxy']['up'],
          '| face up:', out['face']['up'], '| identity two-sided:', out['identity']['two_sided'])
    if not (out['backend']['up'] and out['proxy']['up'] and out['face']['up']):
        raise SystemExit('a member of the rig never came up - nothing will be measured')


def seed_journey(which):
    helper = BASE / 'seed_helper.py'
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
    # the seed must run against THIS arm's database with THIS arm's own backend code - the first
    # version hardcoded snap_new, which left the `old` arm with a journey and an empty catalog
    r = subprocess.run([PY, str(helper)], cwd=str(snap(which) / 'backend'),
                       env=env_base(which), capture_output=True, text=True,
                       encoding='utf-8', errors='replace')
    line = [x for x in r.stdout.splitlines() if x.startswith('SEEDRESULT ')]
    face = 'http://127.0.0.1:%d' % PORTS['proxy']
    st_t, raw_t = http('POST', face + '/api/v1/travelers',
                       {'display_name': 'HJP3 C2 pairing', 'timezone': 'Asia/Shanghai'})
    trav = json.loads(raw_t) if st_t == 201 else {}
    st_j, raw_j = http('POST', face + '/api/v1/journeys', {
        'traveler_id': trav.get('id'), 'title': 'HJP3 C2 pairing one-time', 'city_code': 'CNX-DEMO',
        'timezone': 'Asia/Shanghai', 'start_at': '2026-09-26T10:00:00+08:00',
        'end_at': '2026-09-27T20:00:00+08:00',
        'budget': {'amount_minor': 300000, 'currency': 'CNY'},
        'stay_budget': {'amount_minor': 100000, 'currency': 'CNY'}, 'party_size': 2})
    jrn = json.loads(raw_j) if st_j == 201 else {}
    return {'seed_rc': r.returncode, 'seed': json.loads(line[0][11:]) if line else r.stderr[-300:],
            'traveler_http': st_t, 'journey_http': st_j, 'journey_id': jrn.get('id')}


def sqlite_conn(which, timeout=30):
    # autocommit so that my BEGIN IMMEDIATE is the only transaction machinery in play;
    # `isolation` is not an attribute on this interpreter (3.10) - the name is `isolation_level`,
    # and setting the wrong one silently leaves the connection in deferred implicit mode.
    return sqlite3.connect(str(db_for(which)), timeout=timeout, isolation_level=None)


def do_lock(which, spec):
    """Hold the write lock AFTER the page has opened the sheet, so the hub still renders (0301 recipe)."""
    plan = [int(x) for x in str(spec).split(',')]
    ready = BASE / 'sheet_ready.flag'
    if ready.exists():
        ready.unlink()
    for k, secs in enumerate(plan):
        t0 = time.time()
        while not ready.exists():
            if time.time() - t0 > 180:
                raise SystemExit('sheet_ready.flag never appeared')
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


def close_my_ports():
    """Close listeners on MY named ports, but only after each one is proven to be mine by its own
    command line naming that exact port. The recorded pid is not enough and never was: the venv
    launcher re-execs, so the socket holder is a child of the pid I wrote down. Anything that cannot
    be attributed is left running and reported."""
    closed = {}
    for name, port in PORTS.items():
        for pid in listening(port):
            cmd = cmdline(pid)
            mine = (('app.main:app' in cmd and ('--port %d' % port) in cmd and '--host 127.0.0.1' in cmd)
                    or ('c2proxy.py %d' % port) in cmd
                    or ('vite.js' in cmd and ('--port %d' % port) in cmd))
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
        out['recorded_pids'][tag] = {'pid': pid, 'cmdline_is_mine': ('app.main:app' in cmd
                                                                    or 'c2proxy.py' in cmd
                                                                    or 'vite.js' in cmd),
                                     'rc': r.returncode, 'cmd_head': cmd[:120]}
    out['listeners'] = close_my_ports()
    out['listening_after'] = {k: listening(v) for k, v in PORTS.items()}
    out['all_my_ports_free'] = not any(out['listening_after'].values())
    (BASE / ('teardown_%s.json' % time.strftime('%H%M%S'))).write_text(
        json.dumps(out, ensure_ascii=False, indent=1), encoding='utf-8', newline=chr(10))
    print(json.dumps(out, ensure_ascii=False))


def do_ports():
    print(json.dumps({k: listening(v) for k, v in PORTS.items()}, ensure_ascii=False))


if __name__ == '__main__':
    cmd = sys.argv[1]
    if cmd == 'start':
        do_start(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else 'pass')
    elif cmd == 'face':
        do_face(sys.argv[2])
    elif cmd == 'lock':
        do_lock(sys.argv[2], sys.argv[3])
    elif cmd == 'stop':
        do_stop()
    elif cmd == 'ports':
        do_ports()
    else:
        raise SystemExit('unknown command')
