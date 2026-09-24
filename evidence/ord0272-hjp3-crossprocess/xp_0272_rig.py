"""ORD-0272 cross-process verifier rig.

F's own test header states the eight gates are single-process and that "真正的跨进程复现归 verifier
(HJ-P3)". This rig is that missing face. Two independent uvicorn PIDs serve ONE fresh temp DB.

Stage recipe is theirs (and I follow it): ensure_schema() + in-process seed_demo() when the demo city is
empty; **never** the /demo/reset HTTP door (it wipes 52 tables and belongs to ~140 modules).

Readings are taken durably from OUTSIDE the app (a second sqlite3 connection) plus the HTTP responses, and
every identity/key question is answered by rows and projection fields, not by status codes.
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

BASE = pathlib.Path('D:/moodle/_hjp3_0272_0924')
TREE = BASE / 'snap_aa29612/CityNexus-aa29612c855c10f1584a333cc19526066813b072/backend'
DB = BASE / 'xp_0272.s3db'
PY = 'D:/moodle/CityNexus/.venv/Scripts/python.exe'
P1, P2 = 8495, 8496
OUT = BASE / 'crossprocess_0272.json'
CMD_A = '我护照丢了，请告诉我怎么办。'
SENT_DIFFERENT = 'same idempotency key used for a different request'
SENT_INCOMPLETE = 'agent idempotency record is incomplete'

for p in (DB, pathlib.Path(str(DB) + '-wal'), pathlib.Path(str(DB) + '-shm')):
    if p.exists():
        p.unlink()


def child_env():
    e = dict(os.environ)
    e['CITYNEXUS_DATABASE_URL'] = 'sqlite:///' + str(DB).replace('\\', '/')
    e['CITYNEXUS_ENV'] = 'development'
    # the gate's precondition: external AI and Hermes must be off, else the durable boundary is not ours
    for k in ('DEEPSEEK_API_KEY', 'CITYNEXUS_AI_API_KEY'):
        e.pop(k, None)
    e['CITYNEXUS_AI_ENABLED'] = 'false'
    return e


snippet = '\n'.join([
    'import json',
    'from app.db.session import ensure_schema, SessionLocal',
    'from app.db.models import Place, Journey',
    'from app.services import seed_demo',
    'from sqlalchemy import func, select',
    'ensure_schema()',
    's = SessionLocal()',
    'n = int(s.scalar(select(func.count()).select_from(Place).where(Place.city_code == "CNX-DEMO")) or 0)',
    'seeded = False',
    'if n == 0:',
    '    seed_demo(s); s.commit(); seeded = True',
    'j = s.scalars(select(Journey).where(Journey.city_code == "CNX-DEMO").order_by(Journey.created_at)).first()',
    'print("SEED", json.dumps({"places": n, "seeded": seeded, "stage": {"city_code": j.city_code, "timezone": j.timezone,',
    '  "start_at": str(j.start_at), "end_at": str(j.end_at), "planning_mode": j.planning_mode,',
    '  "budget": {"amount_minor": j.budget_amount_minor, "currency": j.budget_currency},',
    '  "party_size": getattr(j, "party_size", 2)}}))',
])
r = subprocess.run([PY, '-c', snippet], cwd=str(TREE), env=child_env(), capture_output=True, text=True,
                   encoding='utf-8', errors='replace', timeout=600)
seed_line = [l for l in r.stdout.splitlines() if l.startswith('SEED ')]
print('setup rc=%s' % r.returncode, '| seed:', seed_line[0][:220] if seed_line else 'NONE', '| err:', r.stderr.strip()[-200:])
stage = json.loads(seed_line[0][5:])['stage'] if seed_line else None

procs = []
for port in (P1, P2):
    log = open(BASE / ('xp_backend_%d.log' % port), 'w', encoding='utf-8', errors='replace')
    procs.append((port, subprocess.Popen([PY, '-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1',
                                          '--port', str(port), '--log-level', 'warning'],
                                         cwd=str(TREE), env=child_env(), stdout=log, stderr=subprocess.STDOUT)))

for port in (P1, P2):
    for _ in range(60):
        try:
            urllib.request.urlopen('http://127.0.0.1:%d/api/v1/health' % port, timeout=3).read()
            break
        except Exception:
            time.sleep(1.5)


def call(port, method, path, payload=None, key=None, timeout=120):
    url = 'http://127.0.0.1:%d/api/v1%s' % (port, path)
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(url, method=method, data=data)
    req.add_header('Content-Type', 'application/json')
    if key:
        req.add_header('Idempotency-Key', key)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            b = r.read()
            return {'http': r.status, 'raw': b.decode('utf-8', 'replace')}
    except urllib.error.HTTPError as e:
        return {'http': e.code, 'raw': e.read().decode('utf-8', 'replace')}
    except Exception as e:
        return {'http': 'ERR', 'raw': str(e)[:150]}


def durable(sql, args=()):
    c = sqlite3.connect(str(DB), timeout=30)
    try:
        return list(c.execute(sql, args))
    finally:
        c.close()


def ids(resp):
    try:
        d = json.loads(resp['raw'])
    except Exception:
        return []
    if isinstance(d, list):
        return [str(x.get('id')) for x in d]
    for k in ('candidates', 'plans', 'items', 'top_k'):
        if isinstance(d.get(k), list):
            return [str(x.get('id')) for x in d[k]]
    return []


def msg(resp):
    try:
        return str(json.loads(resp['raw'])['error']['message'])
    except Exception:
        return None


ans = {'db': str(DB), 'ports': [P1, P2], 'stage': stage, 'steps': {}}
tv = call(P1, 'POST', '/travelers', {'display_name': 'HJP3 xp verifier', 'timezone': 'Asia/Shanghai'})
tid = (json.loads(tv['raw']).get('id') if tv['http'] == 201 else None)
jrn = call(P1, 'POST', '/journeys', {'traveler_id': tid, 'title': 'HJP3 xp ' + uuid.uuid4().hex[:8], **stage})
jid = (json.loads(jrn['raw']).get('id') if jrn['http'] == 201 else None)
ans['steps']['seed_my_journey'] = {'traveler_http': tv['http'], 'journey_http': jrn['http'], 'journey': jid}

cmd = call(P1, 'POST', '/journeys/%s/agent/commands' % jid,
           {'command': CMD_A, 'requested_autonomy': 'PLAN_ONLY'})
mission = None
try:
    mission = (json.loads(cmd['raw']).get('mission') or {}).get('id')
except Exception:
    pass
ans['steps']['agent_command'] = {'http': cmd['http'], 'mission': mission, 'raw_head': cmd['raw'][:160]}

# ---- Q1: same identity fired at process 1 then process 2 ----
gen_body = {'candidate_count': 3, 'mission_id': mission}
a = call(P1, 'POST', '/journeys/%s/plans/generate' % jid, gen_body)
rows_after_a = len(durable('SELECT id FROM plan_versions WHERE journey_id=?', (jid,)))
b = call(P2, 'POST', '/journeys/%s/plans/generate' % jid, gen_body)
rows_after_b = len(durable('SELECT id FROM plan_versions WHERE journey_id=?', (jid,)))
ans['steps']['Q1_identity_cross_process'] = {
    'P1': {'http': a['http'], 'ids': ids(a)}, 'P2': {'http': b['http'], 'ids': ids(b)},
    'plan_rows_after_P1': rows_after_a, 'plan_rows_after_P2': rows_after_b,
    'ids_identical': bool(ids(a)) and ids(a) == ids(b),
    'no_second_batch': rows_after_b == rows_after_a,
}

# ---- Q2: same client key across processes (replay), then mismatch, then unfilled ----
key = 'hjp3xp-' + uuid.uuid4().hex[:10]
k1 = call(P1, 'POST', '/journeys/%s/plans/generate' % jid, {'candidate_count': 3, 'mission_id': mission}, key=key)
k2 = call(P2, 'POST', '/journeys/%s/plans/generate' % jid, {'candidate_count': 3, 'mission_id': mission}, key=key)
k3 = call(P2, 'POST', '/journeys/%s/plans/generate' % jid, {'candidate_count': 2, 'mission_id': mission}, key=key)
row = durable('SELECT response_status, COALESCE(response_json, "") FROM idempotency_keys WHERE key=?', (key,))
all_keys = durable('SELECT key, response_status, CASE WHEN response_json IS NULL THEN "NULL" ELSE "json" END FROM idempotency_keys')
# the mission-bound receipt key is `plans.generate:cont:<mission>` (source: _plan_continuation_identity), not a key carrying my header value
cont_key = 'plans.generate:cont:%s' % mission
cont_row = durable('SELECT key, response_status, CASE WHEN response_json IS NULL THEN "NULL" ELSE "json" END FROM idempotency_keys WHERE key=?', (cont_key,))
c = sqlite3.connect(str(DB), timeout=30)
n_blanked = c.execute('UPDATE idempotency_keys SET response_json = NULL WHERE key = ?', (cont_key,)).rowcount
c.commit()
c.close()
k4 = call(P2, 'POST', '/journeys/%s/plans/generate' % jid, {'candidate_count': 3, 'mission_id': mission}, key=key)
ans['steps']['Q2_client_key_cross_process'] = {
    'P1_first': {'http': k1['http'], 'ids': ids(k1)}, 'P2_replay': {'http': k2['http'], 'ids': ids(k2)},
    'replay_same_ids': bool(ids(k1)) and ids(k1) == ids(k2),
    'P2_mismatch_body': {'http': k3['http'], 'message': msg(k3), 'equals_literal': msg(k3) == SENT_DIFFERENT},
    'rows_for_raw_header_key': [list(r) for r in row],
    'all_idempotency_rows': [list(r) for r in all_keys],
    'mission_bound_key': cont_key, 'mission_bound_row_before_blanking': [list(r) for r in cont_row],
    'rows_blanked': n_blanked,
    'P2_after_blanking_receipt': {'http': k4['http'], 'message': msg(k4), 'equals_literal': msg(k4) == SENT_INCOMPLETE},
}

# ---- Q3: is the mission-bound owner readable from the OTHER process ----
feed = call(P2, 'GET', '/journeys/%s/agent-feed?limit=200' % jid)
owner = None
try:
    for ev in json.loads(feed['raw']).get('events', []):
        facts = ev.get('facts') or {}
        if facts.get('continuation_id') == 'cont:%s' % mission:
            owner = facts
            break
except Exception:
    pass
ans['steps']['Q3_owner_readable_cross_process'] = {
    'reader_process': P2, 'http': feed['http'], 'events': len(json.loads(feed['raw']).get('events', [])) if feed['http'] == 200 else None,
    'owner_facts_found': owner is not None, 'owner_facts': owner,
}

# ---- teardown, asserted ----
killed = []
for port, pr in procs:
    pr.terminate()
    try:
        pr.wait(timeout=20)
    except Exception:
        pr.kill()
    killed.append({'port': port, 'pid': pr.pid, 'returncode': pr.returncode})
time.sleep(1.5)
ns = subprocess.run(['netstat', '-ano'], capture_output=True, text=True).stdout
left = sum(1 for ln in ns.splitlines() if ('127.0.0.1:%d ' % P1 in ln or '127.0.0.1:%d ' % P2 in ln) and 'LISTENING' in ln)
for p in (DB, pathlib.Path(str(DB) + '-wal'), pathlib.Path(str(DB) + '-shm')):
    if p.exists():
        p.unlink()
ans['teardown'] = {'killed': killed, 'listeners_left': left, 'db_exists_after_delete': DB.exists()}
ans['teardown']['assert_clean'] = (left == 0 and not DB.exists())

json.dump(ans, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(json.dumps({k: ans['steps'][k] for k in ans['steps']}, ensure_ascii=False, indent=1)[:3000])
print('teardown:', ans['teardown']['assert_clean'], '| WROTE', OUT)
