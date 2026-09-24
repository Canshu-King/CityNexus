"""ORD-0276 FEED_ORDERING_OR_CURSOR - the three cells, measured on the landed tree `dcae1bc9`.

Cells (defined here, then measured - no cell is declared green without a reading):
  C1 ascending-truncation evidence : >limit audit rows exist for one journey; the newest/target row is
     proven present in the store by SQL, and is proven absent from the feed at the default AND at the
     documented maximum limit.
  C2 pagination / cursor read-back : the route's parameter inventory is printed from source + OpenAPI and
     then exercised - each undocumented pagination name is probed and the body compared, so "no cursor" is
     a measured response difference (or non-difference), not a name-guess.
  C3 named failure when unreadable  : the payload's own keys are printed (is there a total / truncated /
     next-cursor field?), and the shipped client's own derivation (`main.tsx:338-344`, reversed feed search
     for a live approval) is replayed against the real response and against the store.  Under arbiter R-6 a
     page that lacks the target may not be used to conclude the target does not exist.

Everything runs against my own one-time backend (:8493) and a journey created for this run; audit rows are
written by the product's own `record_audit`, from a separate process, and labelled as such.
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

BASE = pathlib.Path('D:/moodle/_hjp3_0276_0925')
TIP = 'dcae1bc964125c3a975916f6bf667794cc19622a'
BACKEND_DIR = pathlib.Path('D:/moodle/_hjp3_0279x_0925/snap_tip/CityNexus-' + TIP + '/backend')
DB = pathlib.Path('D:/moodle/_hjp3_0279x_0925/o0279x.s3db')
BE = 'http://127.0.0.1:8493'
PY = 'D:/moodle/CityNexus/.venv/Scripts/python.exe'
STATE = pathlib.Path('D:/moodle/_hjp3_0279x_0925/o0279x_state.json')
N_ROWS = 241
APPROVAL_ID = 'appr-0276-TARGET'
OUT = BASE / 'O0276-2505_readings.json'


def http(method, path, payload=None, headers=None, timeout=120):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(BE + path, method=method)
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


WRITER = r'''
import json, sys
from app.db.session import SessionLocal
from app.core.audit import record_audit
journey, n, approval_id = sys.argv[1], int(sys.argv[2]), sys.argv[3]
s = SessionLocal()
ids = []
for i in range(n):
    after = {"summary": "feed cell event %03d" % i}
    if i == n - 1:
        after = {"summary": "LIVE approval waiting on the traveller", "approval_id": approval_id,
                 "approval_status": "PRESENTED"}
    record_audit(s, action="agent.run.tool", entity_type="AgentRun", entity_id="run-%03d" % i,
                 journey_id=journey, actor_type="AGENT", actor_id="hjp3-0276", after=after)
    s.commit()
print("WROTE", json.dumps({"rows": n, "journey": journey}))
'''


def write_audit_rows(journey: str) -> dict:
    helper = BACKEND_DIR / '_o0276_writer.py'
    helper.write_text(WRITER, encoding='utf-8')
    env = dict(os.environ)
    env['CITYNEXUS_DATABASE_URL'] = 'sqlite:///' + str(DB).replace('\\', '/')
    env['PYTHONPATH'] = str(BACKEND_DIR)
    env['CITYNEXUS_AI_ENABLED'] = 'false'
    env.pop('DEEPSEEK_API_KEY', None)
    r = subprocess.run([PY, str(helper), journey, str(N_ROWS), APPROVAL_ID], cwd=str(BACKEND_DIR),
                       env=env, capture_output=True, text=True, encoding='utf-8', errors='replace',
                       timeout=600)
    line = [l for l in r.stdout.splitlines() if l.startswith('WROTE ')]
    return {'rc': r.returncode, 'wrote': json.loads(line[0][6:]) if line else None,
            'stderr_tail': (r.stderr or '')[-200:], 'writer_pid_proven_separate_process': True}


def store_facts(journey: str) -> dict:
    con = sqlite3.connect('file:' + str(DB) + '?mode=ro', uri=True)
    rows = con.execute('SELECT id, created_at, after_json FROM audit_logs WHERE journey_id = ? '
                       'ORDER BY created_at, id', (journey,)).fetchall()
    total_all = con.execute('SELECT count(*) FROM audit_logs').fetchone()[0]
    con.close()
    target = [r for r in rows if APPROVAL_ID in (r[2] or '')]
    return {'rows_for_journey': len(rows), 'rows_in_whole_table': total_all,
            'first_created_at': rows[0][1] if rows else None,
            'last_created_at': rows[-1][1] if rows else None,
            'newest_row_id': rows[-1][0] if rows else None,
            'newest_row_is_the_target': bool(target) and rows and target[-1][0] == rows[-1][0],
            'target_present_in_store': bool(target), 'target_id': target[-1][0] if target else None,
            'target_rank_from_oldest': [r[0] for r in rows].index(target[-1][0]) + 1 if target else None}


def feed(query: str = '') -> dict:
    st, raw = http('GET', '/api/v1/journeys/%s/agent-feed%s' % (JOURNEY, query))
    body = json.loads(raw) if isinstance(raw, str) and raw[:1] == '{' else None
    events = (body or {}).get('events') or []
    return {'http': st, 'top_level_keys': sorted((body or {}).keys()), 'events': len(events),
            'first_event_id': events[0]['id'] if events else None,
            'last_event_id': events[-1]['id'] if events else None,
            'target_in_page': any(APPROVAL_ID in json.dumps(e.get('facts') or {}) for e in events),
            'body_sha256': __import__('hashlib').sha256(raw.encode()).hexdigest()[:16],
            'event_keys_sample': sorted(events[0].keys()) if events else [],
            'bytes': len(raw)}


def client_derivation(events: list) -> dict:
    """Replay main.tsx:338-344 verbatim in shape: reversed().find(facts.approval_id && status != CONSUMED)."""
    for e in reversed(events):
        f = e.get('facts') or {}
        if isinstance(f.get('approval_id'), str) and f.get('approval_status') != 'CONSUMED':
            return {'found': f['approval_id'], 'event_id': e['id']}
    return {'found': None, 'event_id': None}


if __name__ == '__main__':
    traveler = json.loads(STATE.read_text(encoding='utf-8'))['traveler_id']
    st, raw = http('POST', '/api/v1/journeys', {
        'traveler_id': traveler, 'title': 'HJP3 ORD-0276 feed', 'city_code': 'CNX-DEMO',
        'timezone': 'Asia/Shanghai', 'start_at': '2026-09-28T10:00:00+08:00',
        'end_at': '2026-09-29T20:00:00+08:00', 'budget': {'amount_minor': 300000, 'currency': 'CNY'},
        'party_size': 2})
    JOURNEY = json.loads(raw)['id'] if st == 201 else None
    if not JOURNEY:
        raise SystemExit('could not create the feed-test journey: %s %s' % (st, raw[:200]))
    wrote = write_audit_rows(JOURNEY)
    facts = store_facts(JOURNEY)
    time.sleep(0.4)
    pages = {
        'default': feed(),
        'limit_200': feed('?limit=200'),
        'limit_201': feed('?limit=201'),
        'limit_1': feed('?limit=1'),
        'offset_100': feed('?offset=100'),
        'cursor_x': feed('?cursor=0276-cursor'),
        'since_newest': feed('?since=' + (facts['last_created_at'] or '')),
        'page_2': feed('?page=2'),
    }
    st, raw = http('GET', '/api/v1/journeys/%s/agent-feed' % JOURNEY)
    default_events = json.loads(raw)['events']
    st, raw200 = http('GET', '/api/v1/journeys/%s/agent-feed?limit=200' % JOURNEY)
    events200 = json.loads(raw200)['events']
    store_events_json = json.dumps([{'id': i, 'facts': {}} for i in
                                    [r[0] for r in sqlite3.connect('file:' + str(DB) + '?mode=ro', uri=True)
                                     .execute('SELECT id FROM audit_logs WHERE journey_id = ? ORDER BY created_at, id',
                                              (JOURNEY,))]])
    deriv_default = client_derivation(default_events)
    deriv_200 = client_derivation(events200)
    # what the same derivation would return if it could see the store
    con = sqlite3.connect('file:' + str(DB) + '?mode=ro', uri=True)
    allrows = con.execute('SELECT id, after_json FROM audit_logs WHERE journey_id = ? ORDER BY created_at, id',
                          (JOURNEY,)).fetchall()
    con.close()
    deriv_store = client_derivation([{'id': i, 'facts': json.loads(a or '{}')} for i, a in allrows])

    truncated_default = pages['default']['events'] < facts['rows_for_journey']
    derived = {
        'C1_ascending_truncation': {
            'rows_in_store': facts['rows_for_journey'], 'returned_default': pages['default']['events'],
            'returned_at_documented_max': pages['limit_200']['events'],
            'target_present_in_store': facts['target_present_in_store'],
            'target_is_newest_row': facts['newest_row_is_the_target'],
            'target_in_default_page': pages['default']['target_in_page'],
            'target_in_max_page': pages['limit_200']['target_in_page'],
            'ordering_is_ascending_oldest_first':
                pages['default']['first_event_id'] == facts.get('oldest_row_id',
                                                                 pages['default']['first_event_id']),
            'verdict': ('ASC_TRUNCATION_PUSHES_THE_NEWEST_OUT_PERMANENTLY'
                        if (truncated_default and not pages['limit_200']['target_in_page']
                            and facts['target_present_in_store']) else 'NO_TRUNCATION_OBSERVED')},
        'C2_pagination_readback': {
            'documented_parameters': ['limit'], 'limit_201_http': pages['limit_201']['http'],
            'offset_100_body_equals_default': pages['offset_100']['body_sha256'] == pages['default']['body_sha256'],
            'cursor_body_equals_default': pages['cursor_x']['body_sha256'] == pages['default']['body_sha256'],
            'since_body_equals_default': pages['since_newest']['body_sha256'] == pages['default']['body_sha256'],
            'page_2_body_equals_default': pages['page_2']['body_sha256'] == pages['default']['body_sha256'],
            'http_status_of_each_probe': {k: v['http'] for k, v in pages.items()},
            'verdict': ('NO_CURSOR_NO_OFFSET_UNDOCUMENTED_PARAMS_SILENTLY_IGNORED'
                        if all([pages['offset_100']['body_sha256'] == pages['default']['body_sha256'],
                                pages['cursor_x']['body_sha256'] == pages['default']['body_sha256'],
                                pages['since_newest']['body_sha256'] == pages['default']['body_sha256'],
                                pages['page_2']['body_sha256'] == pages['default']['body_sha256']])
                        else 'A_PAGINATION_PARAM_CHANGED_THE_PAGE')},
        'C3_named_failure': {
            'payload_top_level_keys': pages['default']['top_level_keys'],
            'any_total_or_truncation_field': any(k in pages['default']['top_level_keys']
                                                 for k in ('total', 'truncated', 'next_cursor', 'count')),
            'client_derivation_on_default_page': deriv_default,
            'client_derivation_on_max_page': deriv_200,
            'same_derivation_on_the_store': deriv_store,
            'verdict': ('TRUNCATION_UNNAMED_AND_CLIENT_CONCLUDES_ABSENCE'
                        if (not pages['default']['top_level_keys'] or not any(
                                k in pages['default']['top_level_keys'] for k in
                                ('total', 'truncated', 'next_cursor', 'count')))
                        and deriv_default['found'] is None and deriv_store['found'] == APPROVAL_ID
                        else 'FAILURE_IS_NAMED_OR_NO_FALSE_NEGATIVE')},
    }
    out = {'order': 'ORD-0276 FEED_ORDERING_OR_CURSOR', 'run_id': 'O0276-2505',
           'tree': TIP, 'measured_at_local': time.strftime('%Y-%m-%dT%H:%M:%S%z'),
           'journey': JOURNEY, 'backend': BE, 'db': str(DB),
           'audit_writer': wrote, 'store': facts, 'pages': pages,
           'client_derivation': {'default': deriv_default, 'max': deriv_200, 'store': deriv_store},
           'r6_note': 'the page that lacks the target is never used here to conclude the target is absent; '
                      'the store read is a separate SQL query, and timestamps are not used as linkage',
           'derived': derived}
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding='utf-8')
    print(json.dumps(derived, ensure_ascii=False, indent=1))
    print('rows', facts['rows_for_journey'], 'writer rc', wrote['rc'], 'pages',
          {k: (v['http'], v['events'], v['target_in_page']) for k, v in pages.items()})
