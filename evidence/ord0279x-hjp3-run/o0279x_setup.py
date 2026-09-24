"""ORD-0279-X setup: export the *landed* generation read-only and build its one-time DB.

Same recipe as ORD-0279, only the tree changes (that is the whole point of the order): the tip is
fetched by its 40-char sha from codeload, nothing is read from any `.git`, and the DB is created with
the product's own `ensure_schema()` (R-SCHEMA-01).  Cited blobs are recomputed per file so a coordinate
in a receipt is mine-measured, not relayed.

  stage export : fetch + extract + per-file blob sha1 for the cited files + commit/tree/parent read back
  stage db     : ensure_schema() into a fresh file, print table/index/row counts
"""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import subprocess
import sys
import tarfile
import urllib.request

BASE = pathlib.Path('D:/moodle/_hjp3_0279x_0925')
TIP = 'dcae1bc964125c3a975916f6bf667794cc19622a'
PARENT = 'c79e2b4f4efe414dba22a071a7136ae10b5c84aa'
TREE_NAME = 'CityNexus-' + TIP
TOKEN = pathlib.Path('D:/moodle/_qoder_recovery_20260919/.api_tok_20260920')
DB = BASE / 'o0279x.s3db'
PY = 'D:/moodle/CityNexus/.venv/Scripts/python.exe'
CITED = ['backend/app/main.py', 'backend/app/schemas.py', 'contracts/openapi.yaml',
         'backend/tests/test_qoder_ord0272_continuation.py',
         'frontend/src/features/planning/PlanWithAiSheet.tsx']
STAGE = sys.argv[1] if len(sys.argv) > 1 else 'export'
# the ids the commander quoted at ledger:14907-14933 - a byte-level agreement is checked, not assumed
EXPECTED = {'backend/app/main.py': '416ea4f210e967130710a900cdecd20e7a1b5eca',
            'frontend/src/features/planning/PlanWithAiSheet.tsx':
                '58c0580bbb603c939592ae8b911c4a291b4eb60a'}


def blob_sha(data: bytes) -> str:
    h = hashlib.sha1()
    h.update(b'blob %d\0' % len(data))
    h.update(data)
    return h.hexdigest()


def api(path):
    req = urllib.request.Request('https://api.github.com/repos/Canshu-King/CityNexus' + path)
    req.add_header('Authorization', 'Bearer ' + TOKEN.read_text(encoding='utf-8').strip())
    req.add_header('Accept', 'application/vnd.github+json')
    req.add_header('User-Agent', 'citynexus-hjp3-0279x')
    with urllib.request.urlopen(req, timeout=180) as r:
        return json.loads(r.read().decode())


def do_export():
    BASE.mkdir(exist_ok=True)
    tgz = BASE / ('tip_%s.tgz' % TIP[:7])
    if not tgz.exists():
        req = urllib.request.Request('https://codeload.github.com/Canshu-King/CityNexus/tar.gz/' + TIP)
        req.add_header('Authorization', 'Bearer ' + TOKEN.read_text(encoding='utf-8').strip())
        with urllib.request.urlopen(req, timeout=900) as r, open(tgz, 'wb') as f:
            while True:
                chunk = r.read(1 << 20)
                if not chunk:
                    break
                f.write(chunk)
    top = BASE / 'snap_tip'
    if not (top / TREE_NAME).exists():
        top.mkdir(parents=True, exist_ok=True)
        with tarfile.open(tgz) as t:
            t.extractall(top)
    root = top / TREE_NAME
    # the hazard F hit: an export nested inside someone else's repo makes a cell-level exact_sha resolve
    # to that repo's HEAD.  Prove there is no .git anywhere on the path or inside the export.
    git_on_path = [str(p) for p in [BASE, BASE.parent, pathlib.Path('D:/'), pathlib.Path('D:/moodle')]
                   if (p / '.git').exists()]
    git_in_export = [str(p) for p in root.rglob('.git')][:5]
    hits = {}
    for rel in CITED:
        p = root / rel
        b = p.read_bytes() if p.exists() else b''
        hits[rel] = {'blob': blob_sha(b) if b else None, 'bytes': len(b),
                     'matches_commander_quote': EXPECTED.get(rel) == blob_sha(b) if rel in EXPECTED else None}
    c = api('/commits/' + TIP)
    out = {'tip': TIP, 'commit_tree': c['commit']['tree']['sha'], 'parents': [p['sha'] for p in c['parents']],
           'parent_is_the_previous_tip': c['parents'][0]['sha'] == PARENT,
           'date': c['commit']['committer']['date'],
           'subject': c['commit']['message'].splitlines()[0],
           'export_files': sum(1 for p in root.rglob('*') if p.is_file()), 'cited': hits,
           'git_dir_on_ancestor_path': git_on_path, 'git_dir_inside_export': git_in_export}
    print(json.dumps(out, ensure_ascii=False, indent=1))
    (BASE / 'o0279x_export_proof.json').write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding='utf-8')


HELPER = '''import json, sqlite3, os, sys
from app.db.session import ensure_schema
ensure_schema()
con = sqlite3.connect(sys.argv[2])
rows = con.execute("SELECT type, name FROM sqlite_master").fetchall()
tables = [n for ty, n in rows if ty == "table"]
counts = {n: con.execute("SELECT count(*) FROM " + chr(34) + n + chr(34)).fetchone()[0] for n in tables}
cols = {n: [r[1] for r in con.execute("PRAGMA table_info(" + n + ")")] for n in
        ("idempotency_keys", "journey_missions", "audit_logs") if n in tables}
print("DBRESULT", json.dumps({"tables": len(tables), "indexes": sum(1 for ty, n in rows if ty == "index"),
                              "rows_total": sum(counts.values()), "columns": cols}, ensure_ascii=False))
'''


def do_db():
    for p in (DB, pathlib.Path(str(DB) + '-wal'), pathlib.Path(str(DB) + '-shm')):
        if p.exists():
            p.unlink()
    env = dict(os.environ)
    env['CITYNEXUS_DATABASE_URL'] = 'sqlite:///' + str(DB).replace('\\', '/')
    env.pop('DEEPSEEK_API_KEY', None)
    env['CITYNEXUS_AI_ENABLED'] = 'false'
    env['PYTHONPATH'] = str(BASE / 'snap_tip' / TREE_NAME / 'backend')
    hp = BASE / 'o0279x_db_helper.py'
    hp.write_text(HELPER, encoding='utf-8')
    import ast
    ast.parse(HELPER)
    r = subprocess.run([PY, str(hp), 'noop', str(DB)], cwd=str(BASE / 'snap_tip' / TREE_NAME / 'backend'),
                       env=env, capture_output=True, text=True, encoding='utf-8', errors='replace')
    print('rc=%d' % r.returncode)
    for line in r.stdout.splitlines():
        if line.startswith('DBRESULT '):
            print(line[9:])
    if r.stderr.strip():
        print('STDERR_TAIL %s' % r.stderr.strip()[-400:])


{'export': do_export, 'db': do_db}[STAGE]()
