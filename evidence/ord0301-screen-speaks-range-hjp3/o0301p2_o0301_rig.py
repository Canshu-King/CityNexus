"""ORD-0301 rig: one real backend of the landed tip, one manufactured-outcome origin, one face per side.

Nothing shared is touched: my own private outDir (built from this tip by ORD-0300's build, re-verified
byte-for-byte here), my own one-time database created by the product's `ensure_schema()` (R-SCHEMA-01,
fresh-or-no-run), brand-new ports, `demo/reset` never called, and every pid I start is registered so
teardown proves the listener it kills is the one I started - with the command line read BEFORE the
kill, which is the correction to my own ORD-0300 teardown note.

  start                       - backend 8561 + face 8562 (real) + origin 8563 + face 8564 (controlled)
                                + face 8565 (whose upstream port 8566 is deliberately empty)
  capture                     - take a REAL product rejection envelope off 8561 and freeze its bytes
  policy <stamp> <spec.json>  - declare what the write/read legs of the next arm do
  lock <secs>                 - bounded write-lock window on MY db, self-proved by a refused writer
  door <ms>                   - boot attempt with that write deadline (Q36's two-way gate, read-only)
  own                         - two-way ownership proof for each face (my journey 200 / foreign uuid 404)
  stop                        - kill registered pids, then prove every port silent
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

BASE = pathlib.Path('D:/moodle/_hjp3_0301_0925')
SNAP300 = pathlib.Path('D:/moodle/_hjp3_0300_0925')
SNAP = SNAP300 / 'snap'
BACKEND_DIR = SNAP / 'backend'
OUTDIR = SNAP300 / 'dist_0300'                     # my private build of THIS tip, reused not rebuilt
FACE_CWD = pathlib.Path('D:/moodle/_hjp3_ord0261_0923/snap_e3b0b47/frontend')  # only for the vite binary
DB = BASE / 'o0301.s3db'
PY = 'D:/moodle/CityNexus/.venv/Scripts/python.exe'
TIP = '90d29a172e186aab6e6cb138ab4583ccf93bfa68'
PORT_BASE = int(os.environ.get('CNP_PORT_BASE', '8561'))
TAG = os.environ.get('CNX_STATE_TAG', 'o0301')
BP = PORT_BASE
FREAL = PORT_BASE + 1
ORIGIN = PORT_BASE + 2
FCTL = PORT_BASE + 3
FREFUSED = PORT_BASE + 4
DEAD_UPSTREAM = PORT_BASE + 5                     # must stay empty: that IS the refused outcome
DOOR_BP = PORT_BASE + 9
PORTS = (BP, FREAL, ORIGIN, FCTL, FREFUSED, DEAD_UPSTREAM, DOOR_BP)
PIDS = BASE / (TAG + '_pids.json')
STATE = BASE / (TAG + '_state.json')
POLICY = BASE / 'policy.json'
DETACHED = 0x00000008 | 0x00000200


def http(method, url, payload=None, timeout=90, headers=None, raw_body=None):
    data = None
    req = urllib.request.Request(url, method=method)
    if payload is not None:
        data = json.dumps(payload).encode()
        req.add_header('Content-Type', 'application/json')
    elif raw_body is not None:
        data = raw_body if isinstance(raw_body, bytes) else raw_body.encode()
        req.add_header('Content-Type', 'application/json')
    for k, v in (headers or {}).items():
        req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, data, timeout=timeout) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()
    except Exception as e:  # noqa: BLE001
        return 'ERR', str(e).encode()


def get_bytes(url, timeout=90):
    with urllib.request.urlopen(urllib.request.Request(url), timeout=timeout) as r:
        return r.read()


def listening(port):
    out = subprocess.run(['netstat', '-ano'], capture_output=True, text=True,
                         encoding='utf-8', errors='replace').stdout
    return [ln.split()[-1] for ln in out.splitlines()
            if ('127.0.0.1:%d ' % port) in ln and 'LISTENING' in ln]


def cmdline(pid):
    ps = ("Get-CimInstance Win32_Process -Filter 'ProcessId=%d' | "
          'Select-Object -ExpandProperty CommandLine' % int(pid))
    return subprocess.run(['powershell', '-NoProfile', '-Command', ps], capture_output=True,
                          text=True, encoding='utf-8', errors='replace').stdout.strip()


def env_base(extra=None):
    e = dict(os.environ)
    e['CITYNEXUS_DATABASE_URL'] = 'sqlite:///' + str(DB).replace('\\', '/')
    e['PYTHONPATH'] = str(BACKEND_DIR)
    e.pop('DEEPSEEK_API_KEY', None)
    e['CITYNEXUS_AI_ENABLED'] = 'false'
    e.update(extra or {})
    return e


def assert_export():
    facts = {'backend_dir': str(BACKEND_DIR), 'exists': BACKEND_DIR.exists(), 'outdir': str(OUTDIR)}
    p, up = BACKEND_DIR, []
    while p != p.parent:
        if (p / '.git').exists():
            up.append(str(p))
        p = p.parent
    facts['git_on_ancestor_path'] = up
    facts['git_inside_export'] = [str(x) for x in SNAP.rglob('.git')][:3] if SNAP.exists() else []
    if facts['git_on_ancestor_path'] or facts['git_inside_export']:
        raise SystemExit('export is not clean: %s' % facts)
    return facts


def bundle_facts():
    """Re-verify the private build I am serving is this tip's bytes, not whatever a sibling lane left."""
    html = get_bytes('http://127.0.0.1:%d/' % FREAL, timeout=60).decode('utf-8', 'replace')
    ref = re.findall(r'assets/(index-[A-Za-z0-9_-]+\.js)', html)[0]
    raw = get_bytes('http://127.0.0.1:%d/assets/%s' % (FREAL, ref), timeout=120)
    disk = (OUTDIR / 'assets' / ref).read_bytes()
    text = raw.decode('utf-8', 'replace')
    src = (SNAP / 'frontend' / 'src' / 'features' / 'planning' / 'PlanWithAiSheet.tsx').read_text(encoding='utf-8')
    return {'served_asset': ref, 'served_bytes': len(raw), 'served_sha256': hashlib.sha256(raw).hexdigest(),
            'matches_copy_on_disk': raw == disk,
            'ord0280_device_marker_in_served_bytes': '这台设备自己的读数（服务器没给句子）' in text,
            'ord0300_http_branch_marker_in_served_bytes': 'agent/commands -> HTTP ' in text,
            'network_card_marker_in_served_bytes': '连不上服务端' in text,
            'source_has_http_branch': 'status: `HTTP_${response.status}`' in src,
            'source_has_network_fallback': 'status: "NETWORK"' in src,
            'read_deadline_constant_in_served_bytes': '12e3' in text}


def start_face(port, backend_port, logfile, tag):
    if listening(port):
        raise SystemExit('port %d already taken (%s)' % (port, listening(port)))
    env = env_base()
    env['CITYNEXUS_BACKEND_PORT'] = str(backend_port)
    log = open(BASE / logfile, 'w', encoding='utf-8', errors='replace')
    p = subprocess.Popen(['node', 'node_modules/vite/bin/vite.js', 'preview', '--outDir', str(OUTDIR),
                          '--port', str(port), '--host', '127.0.0.1', '--strictPort'],
                         cwd=str(FACE_CWD), env=env, creationflags=DETACHED,
                         stdout=log, stderr=subprocess.STDOUT)
    for _ in range(90):
        if listening(port):
            break
        time.sleep(1)
    return {'port': port, 'pid': p.pid, 'upstream_backend_port': backend_port, 'tag': tag,
            'cmdline_at_start': cmdline(p.pid)[:220]}


def start_backend(port, tag, extra_env=None, wait=90):
    if listening(port):
        raise SystemExit('port %d already taken' % port)
    env = env_base(extra_env)
    log = open(BASE / ('backend_%d.log' % port), 'w', encoding='utf-8', errors='replace')
    p = subprocess.Popen([PY, '-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', str(port),
                          '--log-level', 'info'], cwd=str(BACKEND_DIR), env=env, creationflags=DETACHED,
                         stdout=log, stderr=subprocess.STDOUT)
    up = False
    for _ in range(wait):
        if listening(port):
            up = True
            break
        if p.poll() is not None:
            break
        time.sleep(1)
    tail = open(BASE / ('backend_%d.log' % port), encoding='utf-8', errors='replace').read()
    return {'port': port, 'pid': p.pid, 'tag': tag, 'env_overrides': {k: v for k, v in (extra_env or {}).items()},
            'listening': up, 'exited': p.poll() is not None, 'exit_rc': p.poll(),
            'log_tail': tail[-900:], 'cmdline_at_start': cmdline(p.pid)[:220]}


def do_start():
    if not BACKEND_DIR.exists():
        raise SystemExit('no clean export of the tip at %s' % BACKEND_DIR)
    export = assert_export()
    for p in (DB, pathlib.Path(str(DB) + '-wal'), pathlib.Path(str(DB) + '-shm')):
        if p.exists():
            p.unlink()
    if listening(DEAD_UPSTREAM):
        raise SystemExit('port %d must stay empty - it IS the refused outcome' % DEAD_UPSTREAM)
    b = start_backend(BP, 'real_default_config')
    if not b['listening']:
        raise SystemExit('backend did not come up: %s' % b['log_tail'][-400:])
    POLICY.write_text(json.dumps({'stamp': 'boot-default', 'write': {'mode': 'answer', 'status': 500,
                                                                 'content_type': 'text/plain; charset=utf-8',
                                                                 'body': 'Internal Server Error',
                                                                 'delay_ms': 250},
                                                             'read': {'mode': 'proxy'}}, ensure_ascii=False),
                      encoding='utf-8')
    o = subprocess.Popen([PY, str(pathlib.Path('D:/moodle/HJ-P3_evidence/o0301_origin.py')), 'serve',
                          str(ORIGIN), str(BP)], cwd=str(BASE), creationflags=DETACHED,
                         stdout=open(BASE / ('origin_%d.log' % ORIGIN), 'w', encoding='utf-8', errors='replace'),
                         stderr=subprocess.STDOUT)
    for _ in range(60):
        if listening(ORIGIN):
            break
        time.sleep(1)
    faces = [start_face(FREAL, BP, 'face_real.log', 'real_backend'),
             start_face(FCTL, ORIGIN, 'face_ctl.log', 'outcome_origin'),
             start_face(FREFUSED, DEAD_UPSTREAM, 'face_refused.log', 'upstream_absent')]
    st = {'measured_on': TIP,
          'measured_on_how_read': 'git ls-remote of refs/heads/mirror/integration-frontend-apple-pass1,'
                                  ' re-read at export time by ORD-0300 (same commit, tree reused)',
          'export_facts': export, 'bundle_facts': bundle_facts(),
          'backend': b, 'backend_port': BP, 'db': str(DB),
          'db_created_by': "the product's own ensure_schema() at import; file deleted before start"
                           ' (R-SCHEMA-01 fresh-or-no-run)',
          'origin': {'pid': o.pid, 'port': ORIGIN, 'cmdline_at_start': cmdline(o.pid)[:220]},
          'faces': faces,
          'ports': {'backend_real': BP, 'face_real': FREAL, 'outcome_origin': ORIGIN, 'face_controlled': FCTL,
                    'face_upstream_absent': FREFUSED, 'deliberately_empty': DEAD_UPSTREAM}}
    (BASE / 'current_state_tag.txt').write_text(TAG, encoding='utf-8')
    PIDS.write_text(json.dumps({'backend': b['pid'], 'origin': o.pid,
                               'face_real': faces[0]['pid'], 'face_controlled': faces[1]['pid'],
                               'face_upstream_absent': faces[2]['pid']}, ensure_ascii=False), encoding='utf-8')
    STATE.write_text(json.dumps(st, ensure_ascii=False, indent=1), encoding='utf-8')
    print(json.dumps({'bundle': st['bundle_facts'], 'ports': st['ports'],
                      'backend_up': b['listening']}, ensure_ascii=False, indent=1))


def do_seed():
    helper = BASE / 'o0301_seed_helper.py'
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
    line = [l for l in r.stdout.splitlines() if l.startswith('SEEDRESULT ')]
    face = 'http://127.0.0.1:%d' % FREAL
    st_t, raw_t = http('POST', face + '/api/v1/travelers',
                       {'display_name': 'HJP3 ORD-0301 verifier', 'timezone': 'Asia/Shanghai'})
    trav = json.loads(raw_t) if st_t == 201 else {}
    st_j, raw_j = http('POST', face + '/api/v1/journeys', {
        'traveler_id': trav.get('id'), 'title': 'HJP3 ORD-0301 one-time', 'city_code': 'CNX-DEMO',
        'timezone': 'Asia/Shanghai', 'start_at': '2026-09-26T10:00:00+08:00',
        'end_at': '2026-09-27T20:00:00+08:00',
        'budget': {'amount_minor': 300000, 'currency': 'CNY'},
        'stay_budget': {'amount_minor': 100000, 'currency': 'CNY'}, 'party_size': 2})
    jrn = json.loads(raw_j) if st_j == 201 else {}
    out = {'seed_rc': r.returncode,
           'seed': json.loads(line[0][11:]) if line else r.stderr[-300:],
           'traveler_http': st_t, 'traveler_id': trav.get('id'),
           'journey_http': st_j, 'journey_id': jrn.get('id'), 'journey_city': jrn.get('city_code')}
    st = json.loads(STATE.read_text(encoding='utf-8'))
    st['seed'] = out
    STATE.write_text(json.dumps(st, ensure_ascii=False, indent=1), encoding='utf-8')
    print(json.dumps(out, ensure_ascii=False))


def do_capture():
    """Freeze a REAL rejection envelope off the product, to be reused as manufactured bodies byte-for-byte."""
    st = json.loads(STATE.read_text(encoding='utf-8'))
    jid = st['seed']['journey_id']
    url = 'http://127.0.0.1:%d/api/v1/journeys/%s/plans/generate' % (BP, jid)
    status, raw = http('POST', url, raw_body=b'{"candidate_count":3}', timeout=120)
    out = {'asked': url, 'status': status, 'bytes': len(raw),
           'sha256': hashlib.sha256(raw).hexdigest()}
    if isinstance(raw, bytes) and status == 422:
        (BASE / 'envelope_real.json').write_bytes(raw)
        j = json.loads(raw.decode('utf-8'))
        out.update({'saved': 'envelope_real.json', 'envelope_keys': sorted(j.get('error', {})),
                    'code': j['error']['code'], 'message': j['error']['message'],
                    'message_key': j['error'].get('message_key')})
    else:
        out['head'] = raw[:300] if isinstance(raw, bytes) else raw
    st = json.loads(STATE.read_text(encoding='utf-8'))
    st['captured_envelope'] = out
    STATE.write_text(json.dumps(st, ensure_ascii=False, indent=1), encoding='utf-8')
    print(json.dumps(out, ensure_ascii=False, indent=1))


def do_policy(stamp, spec_file):
    spec = json.loads(pathlib.Path(spec_file).read_text(encoding='utf-8'))
    spec['stamp'] = stamp
    POLICY.write_text(json.dumps(spec, ensure_ascii=False, indent=1), encoding='utf-8')
    # the origin's request log is APPEND-only: deleting it per arm (which the first pass did) destroys
    # the server-side half of every earlier row's provenance
    print(json.dumps({'policy_stamp': stamp, 'written_to': str(POLICY), 'spec': spec,
                      'origin_log_kept': str(BASE / ('origin_%d_log.jsonl' % ORIGIN))}, ensure_ascii=False))


def sqlite_conn(timeout=30):
    import sqlite3
    return sqlite3.connect(str(DB), timeout=timeout, isolation_level=None)


def do_lock(spec, gap=0, rounds=1):
    plan = [int(x) for x in str(spec).split(',')]
    rounds = len(plan)
    ready = BASE / 'sheet_ready.flag'
    armed = BASE / 'lock_armed.flag'
    for k in range(rounds):
        secs = plan[k]
        w0 = time.time()
        while not ready.exists():                    # the browser opens the sheet FIRST, then I take the lock:
            if time.time() - w0 > 150:               # a lock held across the page's own boot reads would stop
                raise SystemExit('sheet_ready.flag never appeared')   # the hub from rendering, which is not the outcome being measured
            time.sleep(0.2)
        if armed.exists():
            armed.unlink()
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
            print('SELFPROOF: second writer refused with %r' % str(e)[:70], flush=True)
        finally:
            p.close()
        (BASE / 'lock_armed.flag').write_text(str(time.time()), encoding='utf-8')
        print('ARMED round %d' % (k + 1), flush=True)
        time.sleep(secs)
        h.execute('ROLLBACK')
        h.close()
        print('RELEASED round %d at %s' % (k + 1, time.strftime('%H:%M:%S')), flush=True)
        if gap:
            time.sleep(gap)


def do_door(ms):
    """Q36's other side, read-only: does the shipped startup door actually refuse a deadline that
    cannot mean anything?  Nothing here edits product bytes; this is one env var on my own process."""
    b = start_backend(DOOR_BP, 'door_test', {'CITYNEXUS_WRITE_DEADLINE_MS': str(ms)}, wait=45)
    helper = BASE / 'o0301_door_verdict_helper.py'
    helper.write_text('\n'.join([
        'import json',
        'from app.db.write_deadline import configuration_verdict',
        'print("VERDICTRESULT", json.dumps(configuration_verdict(), ensure_ascii=False))',
    ]), encoding='utf-8')
    import ast
    ast.parse(helper.read_text(encoding='utf-8'))
    r = subprocess.run([PY, str(helper)], cwd=str(BACKEND_DIR),
                       env=env_base({'CITYNEXUS_WRITE_DEADLINE_MS': str(ms)}),
                       capture_output=True, text=True, encoding='utf-8', errors='replace')
    line = [l for l in r.stdout.splitlines() if l.startswith('VERDICTRESULT ')]
    out = {'env_CITYNEXUS_WRITE_DEADLINE_MS': ms, 'booted': b['listening'], 'exited': b['exited'],
           'exit_rc': b['exit_rc'], 'error_named_in_log': ('WriteDeadlineConfigurationError' in b['log_tail']),
           'log_tail': b['log_tail'][-600:],
           'in_process_verdict': json.loads(line[0][13:]) if line else None,
           'verdict_rc': r.returncode}
    if b['listening']:
        subprocess.run(['taskkill', '/PID', str(b['pid']), '/T', '/F'], capture_output=True)
    (BASE / ('door_test_%s.json' % ms)).write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding='utf-8')
    print(json.dumps({k: out[k] for k in ('env_CITYNEXUS_WRITE_DEADLINE_MS', 'booted', 'exited',
                                         'exit_rc', 'error_named_in_log', 'verdict_rc')}, ensure_ascii=False))
    print('verdict:', json.dumps(out['in_process_verdict'], ensure_ascii=False)[:500] if out['in_process_verdict'] else None)


def do_own():
    st = json.loads(STATE.read_text(encoding='utf-8'))
    jid = st['seed']['journey_id']
    out = {}
    for f in st['faces']:
        face = 'http://127.0.0.1:%d' % f['port']
        mine, _ = http('GET', face + '/api/v1/journeys/' + jid, timeout=30)
        foreign, _ = http('GET', face + '/api/v1/journeys/' + str(uuid.UUID(int=0xC0FFEE)), timeout=30)
        out['face_%d' % f['port']] = {'upstream': f['upstream_backend_port'], 'tag': f['tag'],
                                      'mine': mine, 'foreign_uuid': foreign,
                                      'verdict': 'MINE_AND_ISOLATED' if (mine == 200 and foreign == 404)
                                                 else 'MY_JOURNEY_NOT_READABLE',
                                      'no_upstream_listening_on_target': not listening(f['upstream_backend_port'])}
    direct, _ = http('GET', 'http://127.0.0.1:%d/api/v1/journeys/%s' % (BP, jid), timeout=30)
    out['direct_backend_mine'] = direct
    print(json.dumps(out, ensure_ascii=False, indent=1))


def do_stop():
    p = json.loads(PIDS.read_text(encoding='utf-8')) if PIDS.exists() else {}
    before = {name: cmdline(pid) for name, pid in p.items()}     # read BEFORE the kill (0300 correction)
    killed = {}
    port_of = {'backend': BP, 'origin': ORIGIN, 'face_real': FREAL, 'face_controlled': FCTL,
               'face_upstream_absent': FREFUSED}
    for name, pid in p.items():
        r = subprocess.run(['taskkill', '/PID', str(pid), '/T', '/F'], capture_output=True, text=True)
        port = port_of.get(name)
        killed[name] = {'pid': pid, 'port': port, 'rc': r.returncode,
                        'cmdline_had_port_before_kill': ('--port %s' % port) in before.get(name, '')
                        if port else ('o0301_origin.py serve %d' % port in before.get(name, ''))}
    time.sleep(2)
    print(json.dumps({'killed': killed,
                      'listening_after': {str(x): listening(x) for x in PORTS},
                      'all_my_ports_free': not any(listening(x) for x in PORTS if x != DEAD_UPSTREAM)
                                           and not listening(DEAD_UPSTREAM)}, ensure_ascii=False, indent=1))


cmd = sys.argv[1]
if cmd == 'lock':
    do_lock(sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 0,
            int(sys.argv[4]) if len(sys.argv) > 4 else 1)
elif cmd == 'policy':
    do_policy(sys.argv[2], sys.argv[3])
elif cmd == 'door':
    do_door(sys.argv[2])
else:
    {'start': do_start, 'seed': do_seed, 'capture': do_capture, 'own': do_own, 'stop': do_stop}[cmd]()
