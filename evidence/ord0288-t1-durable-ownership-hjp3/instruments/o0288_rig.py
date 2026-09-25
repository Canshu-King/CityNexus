"""ORD-0288 T-1 rig: two backend PROCESSES on one one-time database, plus private mutants.

Why two processes: the claim in `_claim_plan_generation` is decided by a UNIQUE index, and an
in-process test can never tell "the guard caught it" from "my own session happened to see it". The
arbiter's word for this order is `expected: observe durable ownership`, so ownership is read back from
the store through a second, READ-ONLY connection - never from what a process remembers.

Every tree behind a mutant is a private copy (hardlink-audited before use); the exported product tree
and the authoritative line are never written.
"""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import shutil
import sqlite3
import subprocess
import sys
import time
import urllib.error
import urllib.request

BASE = pathlib.Path('D:/moodle/_hjp3_0288t1_0925')
TIP = 'dc964086c9d412573ac19d70b24b30e6c3ee6168'
PRISTINE = BASE / 'backend'          # git archive of the tip
PY = 'D:/moodle/CityNexus/.venv/Scripts/python.exe'
DB = BASE / 't1.s3db'
STATE = BASE / 'o0288_state.json'
PIDS = BASE / 'o0288_pids.json'
PAIRS = {'A': 8611, 'B': 8612}
DETACHED = 0x00000008 | 0x00000200


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


def env_for(db, tree):
    e = dict(os.environ)
    e['CITYNEXUS_DATABASE_URL'] = 'sqlite:///' + str(db).replace('\\', '/')
    e['PYTHONPATH'] = str(tree)
    e.pop('DEEPSEEK_API_KEY', None)
    e['CITYNEXUS_AI_ENABLED'] = 'false'
    return e


def hardlink_audit(tree):
    """A copy is a copy only if no file in it shares an inode with anything outside it."""
    bad = []
    for p in list(tree.rglob('*.py'))[:400]:
        st = p.stat()
        if getattr(st, 'st_nlink', 1) > 1:
            bad.append(p.name)
    return {'files_checked': min(400, len(list(tree.rglob('*.py')))), 'nlink_gt_1': bad,
            'verdict': 'PRIVATE_COPY' if not bad else 'SHARED_INODES_REFUSE_TO_RUN'}


def make_private_copy(name, patch=None):
    dst = BASE / name
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(PRISTINE, dst)
    applied = None
    if patch:
        applied = patch(dst / 'app' / 'main.py')
    return {'dir': str(dst), 'hardlink_audit': hardlink_audit(dst), 'patch': applied,
            'main_py_sha256': hashlib.sha256((dst / 'app' / 'main.py').read_bytes()).hexdigest()[:16],
            'pristine_main_py_sha256': hashlib.sha256((PRISTINE / 'app' / 'main.py')
                                                       .read_bytes()).hexdigest()[:16],
            'only_file_changed': [str(x.relative_to(dst)) for x in dst.rglob('*.py')
                                  if x.name == 'main.py'
                                  and x.read_bytes() != (PRISTINE / 'app' / 'main.py').read_bytes()]}


def patch_crash_after_claim(main_py):
    """One line, inside _generate_plans_answer: an UNHANDLED failure after Phase A has claimed.

    The anchor is a statement, not the def line: a def can span lines, and injecting after the def
    produced a SyntaxError in my first attempt - the mutant then refused to boot, which is the only
    reason I noticed. The patched file is parsed before it is ever written.
    """
    import ast as _ast
    src = main_py.read_text(encoding='utf-8')
    anchor = '    planning_mode = request.planning_mode or journey.planning_mode'
    assert src.count(anchor) == 1, 'anchor count = %d, refusing to patch blind' % src.count(anchor)
    injected = src.replace(anchor,
                            '    raise RuntimeError("ORD-0288 T-1 probe: unhandled after the claim")'
                            + chr(10) + anchor, 1)
    _ast.parse(injected)
    main_py.write_text(injected, encoding='utf-8', newline='\n')
    return {'anchor_line': anchor.strip(),
            'inserted_before_it': 'raise RuntimeError("ORD-0288 T-1 probe: unhandled after the claim")',
            'lines_added': injected.count(chr(10)) - src.count(chr(10)),
            'patched_file_parses': True}


def patch_drop_replay_signature_check(main_py):
    """The guard `plans/generate` actually reaches: the comparison inside `_replay_committed_accept`.

    My first mutant deleted the check in the OTHER keyed route (replan generate, main.py:7808) and the
    409 still happened - a mutant that changes nothing is not a control, so this is the corrected one.
    """
    import ast as _ast
    src = main_py.read_text(encoding='utf-8')
    old = '            if row.request_hash != signature:'
    assert src.count(old) == 1, 'carrier count = %d, refusing to patch blind' % src.count(old)
    src = src.replace(old, '            if False and row.request_hash != signature:')
    _ast.parse(src)
    main_py.write_text(src, encoding='utf-8', newline=chr(10))
    return {'carrier_removed': old.strip(), 'replaced_with': 'if False and row.request_hash != signature:',
            'why_this_one': 'plans/generate reaches _replay_committed_accept, not the replan route guard'}


def patch_drop_signature_check(main_py):
    src = main_py.read_text(encoding='utf-8')
    old = 'if existing_generation.request_hash != generation_signature:'
    assert old in src, 'signature guard line moved; refusing to patch blind'
    src = src.replace(old, 'if False and existing_generation.request_hash != generation_signature:')
    main_py.write_text(src, encoding='utf-8', newline='\n')
    return {'removed_carrier': old, 'replaced_with': 'if False and ...'}


def start_backend(tag, port, tree, db):
    if listening(port):
        raise SystemExit('port %d taken' % port)
    log = open(BASE / ('backend_%s.log' % tag), 'w', encoding='utf-8', errors='replace')
    p = subprocess.Popen([PY, '-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', str(port),
                          '--log-level', 'info'], cwd=str(tree), env=env_for(db, tree),
                         creationflags=DETACHED, stdout=log, stderr=subprocess.STDOUT)
    for _ in range(120):
        if listening(port) or p.poll() is not None:
            break
        time.sleep(1)
    return {'tag': tag, 'pid': p.pid, 'port': port, 'tree': str(tree), 'db': str(db),
            'listening': bool(listening(port)), 'exited': p.poll() is not None,
            'cmdline_at_start': cmdline(p.pid)[:200]}


def do_start():
    for p in (DB, pathlib.Path(str(DB) + '-wal'), pathlib.Path(str(DB) + '-shm')):
        if p.exists():
            p.unlink()
    helper = BASE / 'seed_helper.py'
    helper.write_text(chr(10).join([
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
        'print("SEEDRESULT", json.dumps({"places_after": int(s.scalar(select(func.count()).select_from(Place)) or 0),',
        '                                "demo_places": n, "seeded_by_this_call": seeded}))',
    ]), encoding='utf-8')
    import ast
    ast.parse(helper.read_text(encoding='utf-8'))
    r = subprocess.run([PY, str(helper)], cwd=str(PRISTINE.parent / 'backend'),
                       env=env_for(DB, PRISTINE), capture_output=True, text=True,
                       encoding='utf-8', errors='replace')
    line = [x for x in r.stdout.splitlines() if x.startswith('SEEDRESULT ')]
    a = start_backend('A', PAIRS['A'], PRISTINE, DB)
    b = start_backend('B', PAIRS['B'], PRISTINE, DB)
    st = {'measured_on': TIP,
          'measured_on_how_read': 'git ls-remote refs/heads/mirror/integration-frontend-apple-pass1 '
                                  're-read 2026-09-25T16:16:59+0800; backend exported with git archive',
          'seed': json.loads(line[0][11:]) if line else r.stderr[-300:], 'seed_rc': r.returncode,
          'db': str(DB), 'backends': [a, b],
          'both_processes_share_one_file': a['db'] == b['db'],
          'hardlink_audit_pristine': hardlink_audit(PRISTINE)}
    STATE.write_text(json.dumps(st, ensure_ascii=False, indent=1), encoding='utf-8', newline='\n')
    PIDS.write_text(json.dumps({x['tag']: x['pid'] for x in (a, b)}, ensure_ascii=False), encoding='utf-8')
    print(json.dumps(st, ensure_ascii=False, indent=1)[:1200])


def do_make(name, kind):
    st = json.loads(STATE.read_text(encoding='utf-8'))
    patch = {'crash': patch_crash_after_claim, 'signature': patch_drop_signature_check}[kind]
    made = make_private_copy(name, patch)
    st.setdefault('mutants', {})[name] = made
    STATE.write_text(json.dumps(st, ensure_ascii=False, indent=1), encoding='utf-8', newline='\n')
    print(json.dumps(made, ensure_ascii=False, indent=1))


def do_stop(tag=None, port=None):
    p = json.loads(PIDS.read_text(encoding='utf-8')) if PIDS.exists() else {}
    killed = {}
    items = [(tag, p[tag])] if tag else list(p.items())
    for name, pid in items:
        cmd = cmdline(pid)
        r = subprocess.run(['taskkill', '/PID', str(pid), '/T', '/F'], capture_output=True, text=True)
        killed[name] = {'pid': pid, 'rc': r.returncode,
                        'cmdline_read_before_kill_is_ours': 'app.main:app' in cmd,
                        'port': str(PAIRS.get(name, port or '')),
                        'cmdline': cmd[:160]}
        p.pop(name, None)
    PIDS.write_text(json.dumps(p, ensure_ascii=False), encoding='utf-8')
    time.sleep(2)
    print(json.dumps({'killed': killed, 'listening_after': {str(x): listening(x) for x in
                                                            (8611, 8612, 8613, 8614)}},
                     ensure_ascii=False, indent=1))


def do_restart_a():
    st = json.loads(STATE.read_text(encoding='utf-8'))
    b = start_backend('A', PAIRS['A'], PRISTINE, pathlib.Path(st['db']))
    p = json.loads(PIDS.read_text(encoding='utf-8')) if PIDS.exists() else {}
    p['A'] = b['pid']
    PIDS.write_text(json.dumps(p, ensure_ascii=False), encoding='utf-8')
    print(json.dumps(b, ensure_ascii=False))


if __name__ == '__main__':
    cmd = sys.argv[1]
    {'start': do_start, 'make': lambda: do_make(sys.argv[2], sys.argv[3]),
     'restartA': do_restart_a,
     'stop': lambda: do_stop(sys.argv[2] if len(sys.argv) > 2 else None)}[cmd]()
