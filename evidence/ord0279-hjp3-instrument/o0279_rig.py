"""ORD-0279 rig (WRITTEN, NOT YET RUN - no readings are claimed by this file).

Boundary (per commander 494abfd7, no scope creep): measure ONLY "what the user sees while a
write request with no client-side deadline is in flight".  Two mandatory cases:

  W1  the later leg always loses - same conflict, two write legs; the loser's answer must be read
      on BOTH sides: the server field (`error.message`, compared with `==`, never `in`) and the
      rendered on-screen text.  A positive control proves the equality test actually accepts an
      equal pair, and a punctuation-only drift proves it rejects.
  W2  the client must not invent `HTTP 500` under a label that claims to be the server's own reason
      (the ORD-0262 shape) - baseline counter-example, measured on the shipped bundle.

No duration assertion is made anywhere: the same conflict was measured at 32.4 s and 0.6 s and both
are real, so elapsed time is recorded as a reading only.  Every verdict is derived from measured
rows/fields; no literal "PASS" appears.  Screen assertions read innerText, never data-*.
DB is built with ensure_schema() (R-SCHEMA-01).  Any negative search states its search space and
`coverage: NOT EXHAUSTIVE` (R-SCHEMA-02).
"""
from __future__ import annotations

import json
import os
import pathlib
import subprocess
import time
import urllib.request

BASE = pathlib.Path('D:/moodle/_hjp3_0279_0924')
TREE_NAME = 'CityNexus-c79e2b4f4efe414dba22a071a7136ae10b5c84aa'
BACKEND_PORT = 8497
FACE_PORT = 8498
DUMMY_500_PORT = 8597
DB = BASE / 'o0279.s3db'
PY = 'D:/moodle/CityNexus/.venv/Scripts/python.exe'
OUT = BASE / 'o0279_readings.json'
TIP = 'c79e2b4f4efe414dba22a071a7136ae10b5c84aa'

readings: dict = {'status': 'NOT-RUN', 'plan': {'W1': 'later leg loses, two-sided equality',
                                                'W2': 'client must not invent HTTP 500'},
                  'commands': {}}


def sh(cmd, cwd=None, env=None, timeout=600):
    return subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, text=True,
                          encoding='utf-8', errors='replace', timeout=timeout)


def fetch_tip_export() -> pathlib.Path:
    """Read-only export of the authoritative tip, by its 40-char sha (never a branch name)."""
    tok = (pathlib.Path('D:/moodle/_qoder_recovery_20260919/.api_tok_20260920')).read_text(encoding='utf-8').strip()
    tgz = BASE / ('tip_%s.tgz' % TIP[:7])
    if not tgz.exists():
        r = urllib.request.Request('https://codeload.github.com/Canshu-King/CityNexus/tar.gz/%s' % TIP)
        r.add_header('Authorization', 'Bearer ' + tok)
        with urllib.request.urlopen(r, timeout=900) as x, open(tgz, 'wb') as f:
            while True:
                chunk = x.read(1 << 20)
                if not chunk:
                    break
                f.write(chunk)
    top = BASE / 'snap_tip'
    if not (top / TREE_NAME).exists():
        import tarfile
        top.mkdir(exist_ok=True)
        with tarfile.open(tgz) as t:
            t.extractall(top)
    return top / TREE_NAME / 'backend'


def build_db(backend_dir: pathlib.Path) -> dict:
    for p in (DB, pathlib.Path(str(DB) + '-wal'), pathlib.Path(str(DB) + '-shm')):
        if p.exists():
            p.unlink()
    env = dict(os.environ)
    env['CITYNEXUS_DATABASE_URL'] = 'sqlite:///' + str(DB).replace('\\', '/')
    env.pop('DEEPSEEK_API_KEY', None)
    env['CITYNEXUS_AI_ENABLED'] = 'false'
    snippet = '\n'.join([
        'import json',
        'from app.db.session import ensure_schema, SessionLocal',
        'from app.db.models import Place, Journey',
        'from app.services import seed_demo',
        'from sqlalchemy import func, select',
        'ensure_schema()',
        's = SessionLocal()',
        'n = int(s.scalar(select(func.count()).select_from(Place).where(Place.city_code == "CNX-DEMO")) or 0)',
        'seeded = n == 0',
        'if seeded:',
        '    seed_demo(s); s.commit()',
        'j = s.scalars(select(Journey).where(Journey.city_code == "CNX-DEMO").order_by(Journey.created_at)).first()',
        'print("STAGE", json.dumps({"places": n, "seeded_by_call": seeded, "stage": {',
        '  "city_code": j.city_code, "timezone": j.timezone, "start_at": str(j.start_at), "end_at": str(j.end_at),',
        '  "planning_mode": j.planning_mode, "budget": {"amount_minor": j.budget_amount_minor,',
        '  "currency": j.budget_currency}}}))',
    ])
    r = sh([PY, '-c', snippet], cwd=str(backend_dir), env=env)
    line = [l for l in r.stdout.splitlines() if l.startswith('STAGE ')]
    return {'rc': r.returncode, 'stage': json.loads(line[0][6:]) if line else None, 'stderr_tail': r.stderr.strip()[-200:]}


def start(backend_dir: pathlib.Path) -> list:
    env = dict(os.environ)
    env['CITYNEXUS_DATABASE_URL'] = 'sqlite:///' + str(DB).replace('\\', '/')
    env.pop('DEEPSEEK_API_KEY', None)
    env['CITYNEXUS_AI_ENABLED'] = 'false'
    procs = []
    log = open(BASE / 'o0279_backend.log', 'w', encoding='utf-8', errors='replace')
    procs.append(('backend', subprocess.Popen([PY, '-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1',
                                               '--port', str(BACKEND_PORT), '--log-level', 'warning'],
                                              cwd=str(backend_dir), env=env, stdout=log, stderr=subprocess.STDOUT)))
    fenv = dict(env)
    fenv['CITYNEXUS_BACKEND_PORT'] = str(BACKEND_PORT)
    flog = open(BASE / 'o0279_face.log', 'w', encoding='utf-8', errors='replace')
    procs.append(('face', subprocess.Popen(['node', 'node_modules/vite/bin/vite.js', 'preview',
                                            '--outDir', 'D:/moodle/_hjp3_fan_sweep_0923/snap_live_dist',
                                            '--port', str(FACE_PORT), '--host', '127.0.0.1', '--strictPort'],
                                           cwd='D:/moodle/_hjp3_ord0261_0923/snap_e3b0b47/frontend',
                                           env=fenv, stdout=flog, stderr=subprocess.STDOUT)))
    return procs


def teardown(procs) -> dict:
    for name, p in procs:
        p.terminate()
        try:
            p.wait(timeout=20)
        except Exception:
            p.kill()
    time.sleep(1.5)
    ns = sh(['netstat', '-ano']).stdout
    left = sum(1 for ln in ns.splitlines()
               if any(('127.0.0.1:%d ' % port) in ln for port in (BACKEND_PORT, FACE_PORT)) and 'LISTENING' in ln)
    for pth in (DB, pathlib.Path(str(DB) + '-wal'), pathlib.Path(str(DB) + '-shm')):
        if pth.exists():
            pth.unlink()
    return {'listeners_left': left, 'db_exists_after_delete': DB.exists(),
            'assert_clean': left == 0 and not DB.exists()}


if __name__ == '__main__':
    readings['status'] = 'RIG-ONLY: the browser legs (W1 rendered text, W2 rendered text) are driven from the ' \
                         'Playwright lane, not from this file; running this file alone only proves the export ' \
                         'and the one-time DB build.'
    readings['commands']['fetch_tip_export'] = 'see fetch_tip_export(): by 40-char sha ' + TIP
    json.dump(readings, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(json.dumps(readings, ensure_ascii=False, indent=1))
