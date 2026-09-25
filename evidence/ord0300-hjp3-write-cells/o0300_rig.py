"""ORD-0300 rig: the landed tip's backend and the landed tip's freshly-built bundle, on one-time ports.

Nothing shared is touched: the outDir is MY private build, the DB is created here by the product's own
`ensure_schema()` (R-SCHEMA-01, fresh-or-no-run), `demo/reset` is never called, and every process this
file starts is recorded by pid so teardown can prove the listener it kills is the one it started.
"""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
import uuid

BASE = pathlib.Path('D:/moodle/_hjp3_0300_0925')
SNAP = BASE / 'snap'
BACKEND_DIR = SNAP / 'backend'
OUTDIR = BASE / 'dist_0300'
FACE_CWD = pathlib.Path('D:/moodle/_hjp3_ord0261_0923/snap_e3b0b47/frontend')
DB = BASE / 'o0300.s3db'
PY = 'D:/moodle/CityNexus/.venv/Scripts/python.exe'
TIP = '90d29a172e186aab6e6cb138ab4583ccf93bfa68'
BP, FP = 8551, 8552                       # W2 arm: healthy backend + the new bundle
ORIGIN, SFP = 8553, 8554                  # T-b arm: selective origin + the same bundle
FACE = 'http://127.0.0.1:%d' % FP
SFACE = 'http://127.0.0.1:%d' % SFP
BE = 'http://127.0.0.1:%d' % BP
PIDS = BASE / 'o0300_pids.json'
STATE = BASE / 'o0300_state.json'
DETACHED = 0x00000008 | 0x00000200


def http(method, url, payload=None, timeout=90, headers=None):
    data = None
    req = urllib.request.Request(url, method=method)
    if payload is not None:
        data = json.dumps(payload).encode()
        req.add_header('Content-Type', 'application/json')
    for k, v in (headers or {}).items():
        req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, data, timeout=timeout) as r:
            return r.status, r.read().decode('utf-8', 'replace')
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode('utf-8', 'replace')
    except Exception as e:  # noqa: BLE001
        return 'ERR', str(e)[:200]


def get_bytes(url, timeout=90):
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def listening(port):
    out = subprocess.run(['netstat', '-ano'], capture_output=True, text=True,
                         encoding='utf-8', errors='replace').stdout
    return [ln.split()[-1] for ln in out.splitlines()
            if ('127.0.0.1:%d ' % port) in ln and 'LISTENING' in ln]


def cmdline(pid):
    ps = ("Get-CimInstance Win32_Process -Filter 'ProcessId=%d' | "
          'Select-Object -ExpandProperty CommandLine' % pid)
    return subprocess.run(['powershell', '-NoProfile', '-Command', ps], capture_output=True,
                          text=True, encoding='utf-8', errors='replace').stdout.strip()


def env_base():
    e = dict(os.environ)
    e['CITYNEXUS_DATABASE_URL'] = 'sqlite:///' + str(DB).replace('\\', '/')
    e['PYTHONPATH'] = str(BACKEND_DIR)
    e.pop('DEEPSEEK_API_KEY', None)
    e['CITYNEXUS_AI_ENABLED'] = 'false'
    return e


def assert_export():
    """The tree must be a plain export with no repository reachable from it, or a helper reading `git rev-parse`
    would silently measure the wrong generation."""
    facts = {'backend_dir': str(BACKEND_DIR), 'exists': BACKEND_DIR.exists()}
    p = BACKEND_DIR
    up = []
    while p != p.parent:
        if (p / '.git').exists():
            up.append(str(p))
        p = p.parent
    facts['git_on_ancestor_path'] = up
    facts['git_inside_export'] = [str(x) for x in SNAP.rglob('.git')][:3] if SNAP.exists() else []
    # the two files ORD-0296 / ORD-0280 are supposed to have added or changed
    wd = BACKEND_DIR / 'app' / 'db' / 'write_deadline.py'
    sheet = SNAP / 'frontend' / 'src' / 'features' / 'planning' / 'PlanWithAiSheet.tsx'
    facts['ord0296_module_present'] = wd.exists()
    facts['ord0280_marker_in_source'] = 'failureNote(' in sheet.read_text(encoding='utf-8')
    if facts['git_on_ancestor_path'] or facts['git_inside_export']:
        raise SystemExit('export is not clean: %s' % facts)
    return facts


def server_config_verdict():
    """Ask the product what numbers it is running with - not what I think the defaults are."""
    helper = BASE / 'o0300_cfg_helper.py'
    helper.write_text('\n'.join([
        'import json',
        'from app.core.config import settings',
        'from app.db.write_deadline import configuration_verdict, busy_timeout_ms, deadline_ms, SCENARIOS',
        'print("CFGRESULT", json.dumps({',
        '  "settings_write_busy_timeout_ms": int(settings.write_busy_timeout_ms),',
        '  "settings_write_deadline_ms": int(settings.write_deadline_ms),',
        '  "settings_write_deadline_scenarios": settings.write_deadline_scenarios,',
        '  "scenarios": list(SCENARIOS), "busy_timeout_ms": busy_timeout_ms(),',
        '  "deadline_per_scenario": {s: deadline_ms(s) for s in SCENARIOS},',
        '  "verdict": configuration_verdict()}, ensure_ascii=False))',
    ]), encoding='utf-8')
    import ast
    ast.parse(helper.read_text(encoding='utf-8'))
    r = subprocess.run([PY, str(helper)], cwd=str(BACKEND_DIR), env=env_base(),
                       capture_output=True, text=True, encoding='utf-8', errors='replace')
    line = [l for l in r.stdout.splitlines() if l.startswith('CFGRESULT ')]
    return {'rc': r.returncode, 'verdict': json.loads(line[0][10:]) if line else None,
            'stderr_tail': r.stderr[-300:] if not line else ''}


def start_face(outdir, port, backend_port, logfile):
    if listening(port):
        raise SystemExit('face port %d taken' % port)
    env = env_base()
    env['CITYNEXUS_BACKEND_PORT'] = str(backend_port)
    log = open(BASE / logfile, 'w', encoding='utf-8', errors='replace')
    p = subprocess.Popen(['node', 'node_modules/vite/bin/vite.js', 'preview', '--outDir', str(outdir),
                          '--port', str(port), '--host', '127.0.0.1', '--strictPort'],
                         cwd=str(FACE_CWD), env=env, creationflags=DETACHED,
                         stdout=log, stderr=subprocess.STDOUT)
    for _ in range(90):
        if listening(port):
            break
        time.sleep(1)
    html = get_bytes('http://127.0.0.1:%d/' % port, timeout=60).decode('utf-8', 'replace')
    ref = re.findall(r'assets/(index-[A-Za-z0-9_-]+\.js)', html)[0]
    raw = get_bytes('http://127.0.0.1:%d/assets/%s' % (port, ref), timeout=120)
    disk = (outdir / 'assets' / ref).read_bytes()
    facts = json.loads((BASE / 'bundle_facts.json').read_text(encoding='utf-8'))
    return {'port': port, 'pid': p.pid, 'backend_port': int(backend_port), 'served_asset': ref,
            'served_bytes': len(raw), 'served_sha256': hashlib.sha256(raw).hexdigest(),
            'matches_copy_on_disk': raw == disk, 'is_the_ord0300_build': hashlib.sha256(raw).hexdigest()
            == facts['sha256'], 'cmdline': cmdline(p.pid),
            'ord0280_markers_in_served_bytes': ('这台设备自己的读数（服务器没给句子）' in raw.decode('utf-8', 'replace'))}


def do_start():
    if not BACKEND_DIR.exists():
        raise SystemExit('no export at %s' % BACKEND_DIR)
    export = assert_export()
    cfg = server_config_verdict()
    for p in (DB, pathlib.Path(str(DB) + '-wal'), pathlib.Path(str(DB) + '-shm')):
        if p.exists():
            p.unlink()
    if listening(BP):
        raise SystemExit('backend port %d taken' % BP)
    env = env_base()
    log = open(BASE / 'o0300_backend.log', 'w', encoding='utf-8', errors='replace')
    b = subprocess.Popen([PY, '-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', str(BP),
                          '--log-level', 'info'], cwd=str(BACKEND_DIR), env=env, creationflags=DETACHED,
                         stdout=log, stderr=subprocess.STDOUT)
    for _ in range(90):
        if listening(BP):
            break
        time.sleep(1)
    face = start_face(OUTDIR, FP, BP, 'o0300_face.log')
    st = {'measured_on': TIP, 'export_facts': export, 'server_write_config': cfg,
          'backend_pid': b.pid, 'backend_port': BP, 'db': str(DB),
          'db_created_by': 'app.db.session.ensure_schema() at import; file deleted before start (fresh-or-no-run)',
          'face': face}
    PIDS.write_text(json.dumps({'backend': b.pid, 'face': face['pid']}, ensure_ascii=False), encoding='utf-8')
    STATE.write_text(json.dumps(st, ensure_ascii=False, indent=1), encoding='utf-8')
    print(json.dumps({k: st[k] for k in ('measured_on', 'backend_pid', 'backend_port', 'db')},
                     ensure_ascii=False))
    print(json.dumps({'face': face, 'config': cfg['verdict']}, ensure_ascii=False)[:1200])


def do_seed():
    helper = BASE / 'o0300_seed_helper.py'
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
                       {'display_name': 'HJP3 ORD-0300 verifier', 'timezone': 'Asia/Shanghai'})
    trav = json.loads(raw_t) if st_t == 201 else {}
    st_j, raw_j = http('POST', FACE + '/api/v1/journeys', {
        'traveler_id': trav.get('id'), 'title': 'HJP3 ORD-0300 one-time', 'city_code': 'CNX-DEMO',
        'timezone': 'Asia/Shanghai', 'start_at': '2026-09-26T10:00:00+08:00',
        'end_at': '2026-09-27T20:00:00+08:00',
        'budget': {'amount_minor': 300000, 'currency': 'CNY'},
        'stay_budget': {'amount_minor': 100000, 'currency': 'CNY'}, 'party_size': 2})
    jrn = json.loads(raw_j) if st_j == 201 else {}
    out = {'seed_rc': r.returncode, 'seed': json.loads(seed_line[0][11:]) if seed_line else r.stderr[-300:],
           'traveler_http': st_t, 'traveler_id': trav.get('id'),
           'journey_http': st_j, 'journey_id': jrn.get('id'), 'journey_city': jrn.get('city_code')}
    st = json.loads(STATE.read_text(encoding='utf-8'))
    st['seed'] = out
    STATE.write_text(json.dumps(st, ensure_ascii=False, indent=1), encoding='utf-8')
    print(json.dumps(out, ensure_ascii=False))


def do_own():
    st = json.loads(STATE.read_text(encoding='utf-8'))
    jid = st['seed']['journey_id']
    out = {}
    for name, face_url in (('W2_face', FACE), ('Tb_face', SFACE)):
        mine, _ = http('GET', face_url + '/api/v1/journeys/' + jid, timeout=30)
        foreign, _ = http('GET', face_url + '/api/v1/journeys/' + str(uuid.UUID(int=0xC0FFEE)), timeout=30)
        out[name] = {'via_face_mine': mine, 'via_face_foreign': foreign,
                     'verdict': 'PROXY_IS_MINE' if (mine == 200 and foreign == 404) else 'NOT_OWNED'}
    direct, _ = http('GET', BE + '/api/v1/journeys/' + jid, timeout=30)
    out['direct_backend_mine'] = direct
    print(json.dumps(out, ensure_ascii=False))


def do_lock(spec, gap: int = 0, rounds: int = 1):
    """Bounded write-lock window(s) on MY db, each self-proved by a second writer being refused.
     is one number or a comma list, so a schedule like 20,45 arms a short first window and a long
    second one - which is what it takes to push one request past its own write budget."""
    plan = [int(x) for x in str(spec).split(',')] if isinstance(spec, str) and ',' in str(spec) else [int(spec)] * rounds
    rounds = len(plan)
    for k in range(rounds):
        secs = plan[k]
        h = sqlite_conn()
        h.execute('BEGIN IMMEDIATE')
        h.execute('UPDATE journeys SET title = title')
        print('HELD round %d at %s rows_touched=%d' % (k + 1, time.strftime('%H:%M:%S'),
                                                       h.execute('SELECT changes()').fetchone()[0]), flush=True)
        p = sqlite_conn(timeout=0)
        try:
            p.execute('BEGIN IMMEDIATE')
            p.commit()
            print('SELFPROOF FAILED: second writer wrote', flush=True)
        except Exception as e:  # noqa: BLE001
            print('SELFPROOF: second writer refused with %r' % str(e)[:60], flush=True)
        finally:
            p.close()
        print('ARMED round %d - browser legs may fire now' % (k + 1), flush=True)
        time.sleep(secs)
        h.execute('ROLLBACK')
        h.close()
        print('RELEASED round %d at %s' % (k + 1, time.strftime('%H:%M:%S')), flush=True)
        if gap:
            time.sleep(gap)


def sqlite_conn(timeout=30):
    import sqlite3
    return sqlite3.connect(str(DB), timeout=timeout, isolation_level=None)


def do_silent():
    """T-b arm: a selective origin in front of MY backend (reads answered, POST accepted and never
    answered), plus a second face serving the SAME bundle so the only difference is the origin."""
    if listening(ORIGIN):
        raise SystemExit('origin port %d taken' % ORIGIN)
    olog = open(BASE / 'o0300_origin.log', 'w', encoding='utf-8', errors='replace')
    o = subprocess.Popen([PY, str(pathlib.Path('D:/moodle/HJ-P3_evidence/o0291_selective_origin.py')),
                          'serve', str(ORIGIN), str(BP)], cwd=str(BASE), creationflags=DETACHED,
                         stdout=olog, stderr=subprocess.STDOUT)
    for _ in range(60):
        if listening(ORIGIN):
            break
        time.sleep(1)
    face = start_face(OUTDIR, SFP, ORIGIN, 'o0300_silent_face.log')
    st = json.loads(STATE.read_text(encoding='utf-8'))
    st['silent'] = {'origin_pid': o.pid, 'origin_port': ORIGIN, 'face': face,
                    'origin_probe_get': http('GET', 'http://127.0.0.1:%d/api/v1/health' % ORIGIN, timeout=30)[0]}
    STATE.write_text(json.dumps(st, ensure_ascii=False, indent=1), encoding='utf-8')
    p = json.loads(PIDS.read_text(encoding='utf-8'))
    p.update({'silent_origin': o.pid, 'silent_face': face['pid']})
    PIDS.write_text(json.dumps(p, ensure_ascii=False), encoding='utf-8')
    print(json.dumps(st['silent'], ensure_ascii=False, indent=1))


def do_stop():
    p = json.loads(PIDS.read_text(encoding='utf-8')) if PIDS.exists() else {}
    killed = {}
    for name, pid in p.items():
        r = subprocess.run(['taskkill', '/PID', str(pid), '/T', '/F'], capture_output=True, text=True)
        port = {'backend': BP, 'face': FP, 'silent_face': SFP, 'silent_origin': ORIGIN}.get(name)
        killed[name] = {'pid': pid, 'port': port, 'rc': r.returncode, 'cmdline_had_port': ('--port %s' % port) in cmdline(pid) if port else None}
    time.sleep(2)
    print(json.dumps({'killed': killed, 'listening_after': {str(x): listening(x)
                                                            for x in (BP, FP, ORIGIN, SFP)}},
                     ensure_ascii=False))


cmd = sys.argv[1]
if cmd == 'lock':
    do_lock(sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 0,
            int(sys.argv[4]) if len(sys.argv) > 4 else 1)
else:
    {'start': do_start, 'seed': do_seed, 'silent': do_silent, 'own': do_own, 'stop': do_stop}[cmd]()
