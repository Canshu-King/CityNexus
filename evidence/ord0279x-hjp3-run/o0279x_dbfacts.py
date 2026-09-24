"""Durable read-back of the ORD-0279-X one-time DB, from OUTSIDE the app (a second connection).

Prints, per call: the idempotency receipts (key form, operation, status, whether the answer is filled),
the continuation-link audit events, mission rows, plan versions and the journey row.  Read-only; the
window boundaries come from argv so a leg's attribution is a query, not a recollection.

  usage: python o0279x_dbfacts.py [since-UTC-iso ...]
"""
from __future__ import annotations

import json
import sqlite3
import sys

DB = 'D:/moodle/_hjp3_0279x_0925/o0279x.s3db'
SINCE = sys.argv[1:] or [None]
c = sqlite3.connect('file:' + DB + '?mode=ro', uri=True)


def q(sql, args=()):
    return c.execute(sql, args).fetchall()


out = {}
try:
    out['idempotency_keys'] = [{'key': k, 'operation': o, 'status': s, 'filled': f is not None,
                                'answer_head': (f or '')[:90], 'created_at': cr}
                               for k, o, s, f, cr in
                               q('SELECT key, operation, response_status, response_json, created_at '
                                 'FROM idempotency_keys ORDER BY created_at')]
    out['audit_continuation'] = [{'action': a, 'entity_type': e, 'entity_id': i, 'after_head': x[:140]}
                                 for a, e, i, x in
                                 q("SELECT action, entity_type, entity_id, after_json FROM audit_logs "
                                   "WHERE action LIKE '%continuation%' ORDER BY created_at")] \
        if [r for r in q("SELECT name FROM sqlite_master WHERE type='table' AND name='audit_logs'")] else 'NO_AUDIT_TABLE'
    out['counts'] = {t: c.execute('SELECT count(*) FROM ' + t).fetchone()[0] for t in
                     ('journey_missions', 'plan_versions', 'idempotency_keys', 'agent_runs', 'events', 'places')}
    out['missions'] = [{'id': i[:8], 'created_at': cr, 'status': st} for i, cr, st in
                       q('SELECT id, created_at, status FROM journey_missions ORDER BY created_at')]
    out['journeys'] = [{'id': i[:8], 'status': st, 'created_at': cr, 'updated_at': up} for i, st, cr, up in
                       q('SELECT id, status, created_at, updated_at FROM journeys')]
    if SINCE[0]:
        lo = SINCE[0]
        out['window'] = {'since': lo,
                         'receipts_created_after': len([r for r in out['idempotency_keys'] if r['created_at'] >= lo]),
                         'missions_created_after': len([m for m in out['missions'] if m['created_at'] >= lo])}
except sqlite3.OperationalError as e:
    out['query_error'] = str(e)
print(json.dumps(out, ensure_ascii=False, indent=1))
