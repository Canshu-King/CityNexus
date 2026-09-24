"""Correction measurement: the candidate DOES bootstrap its schema (ensure_schema -> db/schema.sql).

I had published "no create_all/alembic/init_db entry found in the candidate backend", which was a
negative claim based on probing three names. The real entry is `ensure_schema()` at
app/db/session.py:412, called from app/main.py:418, applying db/schema.sql. Two things to settle:

  1. confirm the entry exists and is called at startup (source read, printed here);
  2. compare the schema it builds on a fresh DB against the sqlite_master of the lane DB I replayed for
     the earlier NARROW rigs, so I can say whether those readings ran on an equivalent schema (and if
     not, say so).
"""
from __future__ import annotations

import json
import os
import pathlib
import re
import sqlite3
import subprocess

TREE = pathlib.Path('D:/moodle/_hjp3_0272_0924/snap_aa29612/CityNexus-aa29612c855c10f1584a333cc19526066813b072/backend')
PY = 'D:/moodle/CityNexus/.venv/Scripts/python.exe'
FRESH = pathlib.Path('D:/moodle/_hjp3_0272_0924/fresh_schema.s3db')
LANE = pathlib.Path('D:/moodle/_lane_aad2d1f2_livecopy.sqlite3')
OUT = pathlib.Path('D:/moodle/_hjp3_0272_0924/schema_bootstrap_correction.json')

for p in (FRESH, pathlib.Path(str(FRESH) + '-wal'), pathlib.Path(str(FRESH) + '-shm')):
    if p.exists():
        p.unlink()

env = dict(os.environ)
env['CITYNEXUS_DATABASE_URL'] = 'sqlite:///' + str(FRESH).replace('\\', '/')
env['CITYNEXUS_ENV'] = 'development'
code = ('import sqlite3;'
        'from app.db.session import ensure_schema;'
        'ensure_schema();'
        'c=sqlite3.connect(r"%s");'
        'print("tables", c.execute("select count(*) from sqlite_master where type=\'table\'").fetchone()[0])' % FRESH)
r = subprocess.run([PY, '-c', code], cwd=str(TREE), env=env, capture_output=True, text=True,
                   encoding='utf-8', errors='replace', timeout=300)
print('ensure_schema run rc=%s out=%r err=%r' % (r.returncode, r.stdout.strip()[:200], r.stderr.strip()[-200:]))


def master(db):
    c = sqlite3.connect(str(db))
    rows = list(c.execute("SELECT type, name, COALESCE(sql,'') FROM sqlite_master WHERE type IN ('table','index','trigger')"))
    c.close()
    return {(t, n): re.sub(r'\s+', ' ', s).strip() for t, n, s in rows}


fresh = master(FRESH)
lane = master(LANE)
only_fresh = sorted(k for k in fresh if k not in lane)
only_lane = sorted(k for k in lane if k not in fresh)
differ = sorted(k for k in fresh if k in lane and fresh[k] != lane[k])

ans = {
    'source_entry': {'def': 'app/db/session.py:412 ensure_schema(target_engine=engine)',
                     'applies': 'db/schema.sql',
                     'called_from': 'app/main.py:418 (module import time)'},
    'my_earlier_claim': 'published in the NARROW segment-1 receipt and MANIFEST: "no create_all/alembic/init_db entry found in the candidate backend therefore a fresh empty DB cannot run the app" -> WRONG (a negative from a three-name probe).',
    'schema_comparison': {
        'fresh_db_from_ensure_schema': {'objects': len(fresh)},
        'lane_db_used_by_my_earlier_rigs': {'objects': len(lane)},
        'only_in_fresh': [list(k) for k in only_fresh][:20],
        'only_in_lane': [list(k) for k in only_lane][:20],
        'same_key_different_sql': [list(k) for k in differ][:20],
        'counts': {'only_in_fresh': len(only_fresh), 'only_in_lane': len(only_lane), 'differing_sql': len(differ)},
        'equivalent': not only_fresh and not only_lane and not differ,
    },
}
json.dump(ans, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(json.dumps(ans['schema_comparison']['counts'], ensure_ascii=False))
print('equivalent =', ans['schema_comparison']['equivalent'])
print('only_in_fresh', ans['schema_comparison']['only_in_fresh'])
print('only_in_lane', ans['schema_comparison']['only_in_lane'])
print('WROTE', OUT)
for p in (FRESH, pathlib.Path(str(FRESH) + '-wal'), pathlib.Path(str(FRESH) + '-shm')):
    if p.exists():
        p.unlink()
print('fresh temp db removed:', not FRESH.exists())
