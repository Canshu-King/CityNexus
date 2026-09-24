"""ORD-0279 setup, phase 1 (read-only export of the authoritative tip + one-time DB via ensure_schema()).

Runs no browser legs and claims no product verdict.  Prints machine-readable lines only for what it
actually measured; every artefact it writes is a fresh name under its own dir.

  stage export : fetch codeload tarball by 40-char sha, recompute git blob sha1 for the cited files
  stage db     : build a one-time SQLite with app.db.session.ensure_schema() (R-SCHEMA-01), print
                 table count and the rows each relevant table holds BEFORE any leg
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

BASE = pathlib.Path('D:/moodle/_hjp3_0279_0924')
TIP = 'c79e2b4f4efe414dba22a071a7136ae10b5c84aa'
TREE_NAME = 'CityNexus-' + TIP
TOKEN = pathlib.Path('D:/moodle/_qoder_recovery_20260919/.api_tok_20260920')
DB = BASE / 'o0279.s3db'
PY = 'D:/moodle/CityNexus/.venv/Scripts/python.exe'
CITED = ['backend/app/main.py', 'backend/app/db/session.py', 'backend/app/api/v1/routers.py']
STAGE = sys.argv[1] if len(sys.argv) > 1 else 'export'


def blob_sha(data: bytes) -> str:
    h = hashlib.sha1()
    h.update(b'blob %d\0' % len(data))
    h.update(data)
    return h.hexdigest()


def do_export():
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
    print('TARBALL bytes=%d sha256=%s' % (tgz.stat().st_size,
                                          hashlib.sha256(tgz.read_bytes()).hexdigest()[:16]))
    top = BASE / 'snap_tip'
    if not (top / TREE_NAME).exists():
        top.mkdir(parents=True, exist_ok=True)
        with tarfile.open(tgz) as t:
            t.extractall(top)
    root = top / TREE_NAME
    files = sorted(p for p in root.rglob('*') if p.is_file())
    total = len(files)
    hits = {}
    for rel in CITED:
        p = root / rel
        if p.exists():
            b = p.read_bytes()
            hits[rel] = {'blob': blob_sha(b), 'bytes': len(b)}
        else:
            hits[rel] = {'missing': True, 'bytes': 0}
    print('EXPORT files=%d  root=%s' % (total, root))
    print(json.dumps(hits, ensure_ascii=False, indent=1))
    # independent cross-check: does GitHub's own tree object agree with my local per-file blob ids?
    req = urllib.request.Request('https://api.github.com/repos/Canshu-King/CityNexus/commits/' + TIP)
    req.add_header('Authorization', 'Bearer ' + TOKEN.read_text(encoding='utf-8').strip())
    with urllib.request.urlopen(req, timeout=120) as r:
        c = json.loads(r.read().decode())
    print('COMMIT sha=%s tree=%s parents=%s date=%s' % (c['sha'][:12], c['commit']['tree']['sha'],
          [p['sha'][:8] for p in c['parents']], c['commit']['committer']['date']))
    print('SUBJECT %s' % c['commit']['message'].splitlines()[0])


HELPER = '''import json, sqlite3, os, sys
from app.db.session import ensure_schema
ensure_schema()
con = sqlite3.connect(sys.argv[2], uri=False)
rows = con.execute("SELECT type, name FROM sqlite_master").fetchall()
tables = [n for ty, n in rows if ty == "table"]
counts = {n: con.execute("SELECT count(*) FROM " + chr(34) + n + chr(34)).fetchone()[0] for n in tables}
print("DBRESULT", json.dumps({"tables": len(tables),
                              "indexes": sum(1 for ty, n in rows if ty == "index"),
                              "rows_total": sum(counts.values()),
                              "nonzero_tables": {k: v for k, v in counts.items() if v},
                              "db_bytes": os.path.getsize(sys.argv[2])}, ensure_ascii=False))
'''


def do_db():
    for p in (DB, pathlib.Path(str(DB) + '-wal'), pathlib.Path(str(DB) + '-shm')):
        if p.exists():
            p.unlink()
    env = dict(os.environ)
    env['CITYNEXUS_DATABASE_URL'] = 'sqlite:///' + str(DB).replace('\\', '/')
    env.pop('DEEPSEEK_API_KEY', None)
    env['CITYNEXUS_AI_ENABLED'] = 'false'
    # running a helper *file* puts its own directory on sys.path, not the cwd -> app was unimportable
    env['PYTHONPATH'] = str(BASE / 'snap_tip' / TREE_NAME / 'backend')
    hp = BASE / 'o0279_db_helper.py'
    hp.write_text(HELPER, encoding='utf-8')
    import ast
    ast.parse(HELPER)                      # lint before running (quote-escape trap)
    r = subprocess.run([PY, str(hp), 'noop', str(DB)], cwd=str(BASE / 'snap_tip' / TREE_NAME / 'backend'),
                       env=env, capture_output=True, text=True, encoding='utf-8', errors='replace')
    print('rc=%d' % r.returncode)
    for line in r.stdout.splitlines():
        if line.startswith('DBRESULT '):
            print(line[9:])
    if r.stderr.strip():
        print('STDERR_TAIL %s' % r.stderr.strip()[-400:])


if STAGE == 'export':
    do_export()
elif STAGE == 'db':
    do_db()
else:
    raise SystemExit('unknown stage')
