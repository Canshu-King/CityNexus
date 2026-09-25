"""ORD-0288 T-1 arms: same key across two processes, and what the error path leaves behind.

Field list is the arbiter's, not mine: `idempotency_keys row / operation / response_status /
replay behavior`. Nothing here is written as "expected red" - every arm records what came back, and
the durable half is read through a second READ-ONLY connection that names the file, the table and the
primary key, because a process's memory is not ownership.
"""
from __future__ import annotations

import json
import os
import pathlib
import sqlite3
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request

BASE = pathlib.Path('D:/moodle/_hjp3_0288t1_0925')
STATE = json.loads((BASE / 'o0288_state.json').read_text(encoding='utf-8'))
TIP = STATE['measured_on']
JOURNEY = None


def http(port, method, path, body=None, headers=None, timeout=90):
    url = 'http://127.0.0.1:%d%s' % (port, path)
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header('Content-Type', 'application/json')
    for k, v in (headers or {}).items():
        req.add_header(k, v)
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read()
            return {'url': url, 'method': method, 'request_body': body, 'sent_headers': dict(headers or {}),
                    'status': r.status, 'content_type': r.headers.get('content-type'),
                    'bytes': len(raw), 'body_text': raw.decode('utf-8', 'replace'),
                    'elapsed_ms': int((time.time() - t0) * 1000), 'at': time.strftime('%H:%M:%S')}
    except urllib.error.HTTPError as e:
        raw = e.read()
        return {'url': url, 'method': method, 'request_body': body, 'sent_headers': dict(headers or {}),
                'status': e.code, 'content_type': e.headers.get('content-type'), 'bytes': len(raw),
                'body_text': raw.decode('utf-8', 'replace'),
                'elapsed_ms': int((time.time() - t0) * 1000), 'at': time.strftime('%H:%M:%S'),
                'http_error': str(e)[:120]}
    except Exception as e:  # noqa: BLE001
        return {'url': url, 'method': method, 'request_body': body, 'sent_headers': dict(headers or {}),
                'status': None, 'error': type(e).__name__ + ': ' + str(e)[:160],
                'elapsed_ms': int((time.time() - t0) * 1000), 'at': time.strftime('%H:%M:%S')}


def rows(db, like='plans.generate:%'):
    """Durable read through a second, read-only connection - the store, not my memory."""
    uri = 'file:%s?mode=ro' % str(db).replace('\\', '/')
    con = sqlite3.connect(uri, uri=True, timeout=30)
    con.row_factory = sqlite3.Row
    out = {'connection_uri': uri, 'db_exists': pathlib.Path(db).exists(),
           'idempotency_keys': [], 'counts': {}}
    for r in con.execute('SELECT key, operation, request_hash, response_status, response_json, created_at,'
                         ' expires_at FROM idempotency_keys WHERE key LIKE ? ORDER BY created_at', (like,)):
        out['idempotency_keys'].append({'key': r['key'], 'operation': r['operation'],
                                        'request_hash_head': (r['request_hash'] or '')[:16],
                                        'response_status': r['response_status'],
                                        'response_json_bytes': len(r['response_json'] or ''),
                                        'response_json_head': (r['response_json'] or '')[:220],
                                        'created_at': r['created_at'], 'expires_at': r['expires_at']})
    for t in ('plan_versions', 'journeys', 'journey_missions', 'audit_logs', 'replan_proposals'):
        try:
            out['counts'][t] = con.execute('SELECT COUNT(*) FROM %s' % t).fetchone()[0]
        except sqlite3.Error as e:
            out['counts'][t] = 'QUERY_FAILED: ' + str(e)[:60]
    out['total_idempotency_rows_all_keys'] = con.execute('SELECT COUNT(*) FROM idempotency_keys').fetchone()[0]
    con.close()
    return out


def seed_journey():
    trav = {}
    for _ in range(2):
        r = http(STATE['backends'][0]['port'], 'POST', '/api/v1/travelers',
                 {'display_name': 'HJP3 T-1', 'timezone': 'Asia/Shanghai'})
        if r['status'] == 201:
            trav = json.loads(r['body_text'])
            break
        time.sleep(1)
    r2 = http(STATE['backends'][0]['port'], 'POST', '/api/v1/journeys', {
        'traveler_id': trav['id'], 'title': 'HJP3 ORD-0288 T-1 one-time', 'city_code': 'CNX-DEMO',
        'timezone': 'Asia/Shanghai', 'start_at': '2026-09-26T10:00:00+08:00',
        'end_at': '2026-09-27T20:00:00+08:00', 'budget': {'amount_minor': 300000, 'currency': 'CNY'},
        'stay_budget': {'amount_minor': 100000, 'currency': 'CNY'}, 'party_size': 2})
    return {'traveler_http': r['status'], 'traveler_id': trav.get('id'),
            'journey_http': r2['status'], 'journey_id': json.loads(r2['body_text']).get('id')
            if r2['status'] == 201 else r2.get('body_text', r2.get('error', ''))[:200]}


def post_gen(port, key, body):
    path = '/api/v1/journeys/%s/plans/generate' % JOURNEY
    return http(port, 'POST', path, body, {'Idempotency-Key': key} if key else {})


def canon(resp):
    """Compare payloads as data, not as bytes: JSON key order is not part of the answer."""
    try:
        return json.dumps(json.loads(resp['body_text']), sort_keys=True)
    except Exception:  # noqa: BLE001
        return resp.get('body_text') or resp.get('error') or ''


def arm(name, steps, db=None, extra=None):
    run = time.strftime('T1-%H%M%S')
    out = {'arm': name, 'run_id': run, 'measured_on': TIP, 'journey_id': JOURNEY,
           'processes': STATE['backends'], 'steps': steps, 'extra': extra or {}}
    # the durable half is read for EVERY arm, not only when one was passed: an absent row is itself
    # the reading, and a print that reports 0 rows because I forgot to look is how a false red is born
    dur = rows(db or STATE['db'], like='%')
    dur['names_the_store'] = str(db or STATE['db'])
    dur['this_arms_keys'] = [k for k in KEYS_THIS_RUN]
    dur['rows_for_this_arms_keys'] = [r for r in dur['idempotency_keys']
                                      if any(r['key'].endswith(k) for k in KEYS_THIS_RUN)]
    out['durable_read_after'] = dur
    p = BASE / ('cell_%s_%s.json' % (name, run))
    p.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding='utf-8', newline='\n')
    print(json.dumps({'arm': name, 'run': run, 'file': p.name,
                      'statuses': [s['response']['status'] for s in steps],
                      'rows': len(out.get('durable_read_after', {}).get('idempotency_keys', []))},
                     ensure_ascii=False))
    return out


PA = STATE['backends'][0]['port']
PB = STATE['backends'][1]['port']


KEYS_THIS_RUN = []


def main():
    global JOURNEY
    j = seed_journey()
    JOURNEY = j['journey_id']
    (BASE / 'seed_journey.json').write_text(json.dumps(j, ensure_ascii=False, indent=1), encoding='utf-8')
    if not JOURNEY:
        raise SystemExit('journey seed failed: %s' % json.dumps(j)[:300])
    global KEYS_THIS_RUN
    keys = {'K1': 'ord0288-t1a-%s' % time.strftime('%H%M%S'),
            'K2': 'ord0288-t1c-%s' % time.strftime('%H%M%S'),
            'K3': 'ord0288-t1b-%s' % time.strftime('%H%M%S')}

    KEYS_THIS_RUN = list(keys.values()) + ['x', 'ord0288-after-badkey']
    # (a) same key, same body, TWO DIFFERENT PROCESSES, one shared database
    r1 = post_gen(PA, keys['K1'], {'candidate_count': 3})
    r2 = post_gen(PB, keys['K1'], {'candidate_count': 3})
    arm('t1a_same_key_two_processes', [
        {'intent': 'first send on process A', 'response': r1},
        {'intent': 'same key same body on process B', 'response': r2,
         'replay_identical_payload': canon(r1) == canon(r2),
         'same_status': r1['status'] == r2['status']}], extra={'key': keys['K1'],
                                                               'expected_per_the_arbiter':
                                                               'observe durable ownership (no preset verdict)'})

    # (a) same key, DIFFERENT body - the signature gate
    r3 = post_gen(PB, keys['K1'], {'candidate_count': 5})
    arm('t1a_same_key_different_body', [{'intent': 'same key, different candidate_count on the other process',
                                         'response': r3,
                                         'is_409': r3['status'] == 409}], extra={'key': keys['K1']})

    # (a) one key fired at both processes at the same moment
    box = {}

    def fire(tag, port):
        box[tag] = post_gen(port, keys['K2'], {'candidate_count': 3})
    tA = threading.Thread(target=fire, args=('A', PA))
    tB = threading.Thread(target=fire, args=('B', PB))
    t0 = time.time()
    tA.start(); tB.start(); tA.join(); tB.join()
    arm('t1a_same_key_concurrent_two_processes',
        [{'intent': 'concurrent send A', 'response': box['A']},
         {'intent': 'concurrent send B', 'response': box['B'],
          'wall_ms_for_both': int((time.time() - t0) * 1000)}],
        extra={'key': keys['K2'],
               'exactly_one_row_for_the_key': sum(1 for r in rows(STATE['db'], keys['K2'])['idempotency_keys']
                                                  if r['key'].endswith(keys['K2'])) == 1})

    # (b) the error path INSIDE the route: a refusal, then the durable row, then a replay
    r4 = post_gen(PA, keys['K3'], {'candidate_count': 3})
    after = rows(STATE['db'])
    r5 = post_gen(PB, keys['K3'], {'candidate_count': 3})
    arm('t1b_error_path_records_response_status',
        [{'intent': 'keyed send that the route refuses', 'response': r4},
         {'intent': 'replay of that same key from the other process', 'response': r5,
          'replay_identical_payload': canon(r4) == canon(r5)}],
        extra={'key': keys['K3'], 'row_for_this_key': [x for x in after['idempotency_keys']
                                                       if x['key'].endswith(keys['K3'])],
               'response_status_is_not_null': all(x['response_status'] is not None for x in
                                                  after['idempotency_keys'] if x['key'].endswith(keys['K3']))})

    # (b) a refusal BEFORE the claim: malformed key -> 422 and no row at all
    r6 = post_gen(PA, 'x', {'candidate_count': 3})
    arm('t1b_failure_before_the_claim_leaves_no_row', [{'intent': 'malformed key rejected', 'response': r6}],
        extra={'malformed_key_rows_now': [x for x in rows(STATE['db'])['idempotency_keys']
                                          if x['key'].endswith(':x')],
               'and_a_later_valid_send_is_unaffected': post_gen(PB, 'ord0288-after-badkey-%s'
                                                                % time.strftime('%H%M%S'),
                                                                {'candidate_count': 3})['status']})

    # (a) durability across a process restart, not just across two live processes
    stopA = subprocess.run(['taskkill', '/PID', str(STATE['backends'][0]['pid']), '/T', '/F'],
                           capture_output=True, text=True)
    time.sleep(1)
    sys.path.insert(0, str(pathlib.Path('D:/moodle/HJ-P3_evidence')))
    env2 = dict(os.environ, PYTHONIOENCODING='utf-8')
    rr = subprocess.run([sys.executable, 'D:/moodle/HJ-P3_evidence/o0288_rig.py', 'restartA'],
                        capture_output=True, text=True, encoding='utf-8', errors='replace', env=env2)
    newA = json.loads((rr.stdout or '{}').strip().splitlines()[-1] if (rr.stdout or '').strip() else '{}')
    (BASE / 'restart_A.json').write_text(rr.stdout + chr(10) + 'STDERR:' + (rr.stderr or '')[-400:],
                                         encoding='utf-8')
    r7 = post_gen(newA.get('port', PA), keys['K1'], {'candidate_count': 3})
    arm('t1a_replay_after_a_process_restart',
        [{'intent': 'replay after the original process was killed and a fresh one started on the same file',
          'response': r7, 'replay_identical_payload': canon(r1) == canon(r7)}],
        extra={'taskkill_rc': stopA.returncode, 'new_process': newA})
    return keys


main()
