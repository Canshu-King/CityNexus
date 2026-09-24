"""ORD-0288 定形的现场依据：`agent/commands` 这一支今天到底有没有凭条、重发会不会堆副作用。

All reads are against my own one-time backend (:8493, tree dcae1bc9) and a journey created here; row counts
come from a second sqlite connection (durable), never from the response text.  Nothing is asserted about
durations (Q25).
"""
from __future__ import annotations

import json
import pathlib
import sqlite3
import urllib.error
import urllib.request
import uuid

DB = pathlib.Path('D:/moodle/_hjp3_0279x_0925/o0279x.s3db')
BE = 'http://127.0.0.1:8493'
STATE = pathlib.Path('D:/moodle/_hjp3_0279x_0925/o0279x_state.json')
OUT = pathlib.Path('D:/moodle/_hjp3_0288_0925/keyless_leg_facts.json')
TABLES = ('journey_missions', 'agent_runs', 'idempotency_keys', 'audit_logs', 'plan_versions')


def http(method, path, payload=None, headers=None):
    req = urllib.request.Request(BE + path, method=method)
    req.add_header('Content-Type', 'application/json')
    for k, v in (headers or {}).items():
        req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, json.dumps(payload).encode() if payload else None, timeout=120) as r:
            return r.status, dict(r.headers), r.read().decode('utf-8', 'replace')
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers), e.read().decode('utf-8', 'replace')


def counts(journey):
    con = sqlite3.connect('file:' + str(DB) + '?mode=ro', uri=True)
    out = {}
    for t in TABLES:
        if journey and t in ('journey_missions', 'agent_runs', 'audit_logs'):
            col = 'journey_id'
            out[t] = con.execute('SELECT count(*) FROM %s WHERE %s = ?' % (t, col), (journey,)).fetchone()[0]
        else:
            out[t] = con.execute('SELECT count(*) FROM ' + t).fetchone()[0]
    out['mission_ids'] = [r[0][:8] for r in con.execute(
        'SELECT id FROM journey_missions WHERE journey_id = ? ORDER BY created_at', (journey,))] \
        if journey else []
    con.close()
    return out


traveler = json.loads(STATE.read_text(encoding='utf-8'))['traveler_id']
st, _, raw = http('POST', '/api/v1/journeys', {
    'traveler_id': traveler, 'title': 'HJP3 ORD-0288 keyless leg', 'city_code': 'CNX-DEMO',
    'timezone': 'Asia/Shanghai', 'start_at': '2026-09-30T10:00:00+08:00',
    'end_at': '2026-10-01T20:00:00+08:00', 'budget': {'amount_minor': 300000, 'currency': 'CNY'},
    'party_size': 2})
J = json.loads(raw)['id'] if st == 201 else None
report = {'journey': J, 'schema_idempotency_keys_columns': None, 'baseline': counts(J), 'runs': []}

con = sqlite3.connect('file:' + str(DB) + '?mode=ro', uri=True)
report['schema_idempotency_keys_columns'] = [r[1] for r in con.execute('PRAGMA table_info(idempotency_keys)')]
report['schema_journey_missions_columns'] = [r[1] for r in con.execute('PRAGMA table_info(journey_missions)')]
con.close()

CMD = '两天，想慢慢逛，吃小吃'
key = 'hjp3-0288-' + uuid.uuid4().hex[:12]
for label, headers in (('no_key x3', None), ('with_Idempotency-Key x3', {'Idempotency-Key': key}),
                       ('same key again', {'Idempotency-Key': key})):
    reps = []
    n = 3 if 'x3' in label else 1
    for _ in range(n):
        s, h, b = http('POST', '/api/v1/journeys/%s/agent/commands' % J, {'command': CMD}, headers)
        j = None
        try:
            j = json.loads(b)
        except Exception:
            pass
        reps.append({'http': s, 'bytes': len(b), 'echoed_idempotency_key_header': h.get('idempotency-key')
                     or h.get('Idempotency-Key') or None,
                     'trace_id_in_body': (j or {}).get('trace_id') or (j or {}).get('error', {}).get('trace_id')
                     if isinstance(j, dict) else None,
                     'mission_id': ((j or {}).get('mission') or {}).get('id') if isinstance(j, dict) else None,
                     'response_headers': sorted(h.keys())[:12]})
    report['runs'].append({'label': label, 'requests': reps, 'counts_after': counts(J)})

# and the shape the key machinery DOES have on the leg that uses it, for comparison
s2, _, b2 = http('POST', '/api/v1/journeys/%s/plans/generate' % J, {'candidate_count': 2},
                 {'Idempotency-Key': 'hjp3-0288-cmp-' + uuid.uuid4().hex[:8]})
con = sqlite3.connect('file:' + str(DB) + '?mode=ro', uri=True)
rows = [list(r) for r in con.execute('SELECT key, operation, response_status, substr(response_json,1,60) '
                                     'FROM idempotency_keys ORDER BY created_at')]
con.close()
report['comparison_plans_generate'] = {'http': s2, 'receipt_rows_now': rows}
OUT.write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding='utf-8')
print(json.dumps({'journey': J, 'columns': report['schema_idempotency_keys_columns'],
                  'baseline': report['baseline']['journey_missions'],
                  'after': [(r['label'], r['counts_after']['journey_missions'],
                             r['counts_after']['agent_runs'], r['counts_after']['idempotency_keys'])
                            for r in report['runs']],
                  'plans_generate_receipts': len(rows)}, ensure_ascii=False, indent=1))
