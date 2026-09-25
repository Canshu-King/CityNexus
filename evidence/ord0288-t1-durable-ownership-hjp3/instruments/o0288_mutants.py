"""ORD-0288 T-1(b) hard half + the mutation controls, on private copies.

Two questions the HTTP arms cannot answer on the pristine tree:
  1. what does the store look like when a request dies AFTER claiming the key (the row is inserted with
     response_status = NULL and the code never deletes a placeholder and never reclaims it by
     expires_at) - can a caller tell "still running" from "died here", i.e. is an unknown result
     knowable?  Arm M1 crashes it on purpose, in a private copy, on its own database.
  2. does the 409 for "same key, different body" have a carrier at all? Arm M2 deletes exactly the
     comparison that raises it and the 409 must disappear - a gate nobody can break is not a gate.

Both trees are hardlink-audited copies; the exported pristine tree and the authoritative line are
never written, and each arm names its own .db file.
"""
from __future__ import annotations

import importlib.util as iu
import json
import os
import pathlib
import sqlite3
import subprocess
import sys
import time

BASE = pathlib.Path('D:/moodle/_hjp3_0288t1_0925')
spec = iu.spec_from_file_location('rig', 'D:/moodle/HJ-P3_evidence/o0288_rig.py')
rig = iu.module_from_spec(spec)
spec.loader.exec_module(rig)          # module level only defines functions here
PAIR = {'M1': 8613, 'M2': 8614}
OUT = []


def seed(tree, db):
    helper = BASE / 'seed_any.py'
    helper.write_text(chr(10).join([
        'import json',
        'from app.db.session import ensure_schema, SessionLocal',
        'from app.db.models import Place',
        'from app.services import seed_demo',
        'from sqlalchemy import func, select',
        'ensure_schema()',
        's = SessionLocal()',
        'if not int(s.scalar(select(func.count()).select_from(Place)) or 0):',
        '    seed_demo(s); s.commit()',
        'print("SEEDRESULT", json.dumps({"places": int(s.scalar(select(func.count()).select_from(Place)) or 0)}))',
    ]), encoding='utf-8')
    import ast
    ast.parse(helper.read_text(encoding='utf-8'))
    for p in (db, pathlib.Path(str(db) + '-wal'), pathlib.Path(str(db) + '-shm')):
        if p.exists():
            p.unlink()
    r = subprocess.run([rig.PY, str(helper)], cwd=str(tree), env=rig.env_for(db, tree),
                       capture_output=True, text=True, encoding='utf-8', errors='replace')
    line = [x for x in r.stdout.splitlines() if x.startswith('SEEDRESULT ')]
    return {'rc': r.returncode, 'seed': json.loads(line[0][11:]) if line else r.stderr[-240:]}


def journey(port):
    r = subprocess.run  # noqa: F841  (keep linters off the helper below)
    import urllib.error
    import urllib.request

    def call(method, path, body):
        req = urllib.request.Request('http://127.0.0.1:%d%s' % (port, path), method=method)
        req.add_header('Content-Type', 'application/json')
        try:
            with urllib.request.urlopen(req, json.dumps(body).encode(), timeout=60) as f:
                return f.status, json.loads(f.read().decode())
        except urllib.error.HTTPError as e:
            return e.code, {'raw': e.read().decode('utf-8', 'replace')[:200]}
    st, trav = call('POST', '/api/v1/travelers', {'display_name': 'HJP3 T-1 mutant', 'timezone': 'Asia/Shanghai'})
    st2, j = call('POST', '/api/v1/journeys', {
        'traveler_id': trav.get('id'), 'title': 'HJP3 T-1 mutant one-time', 'city_code': 'CNX-DEMO',
        'timezone': 'Asia/Shanghai', 'start_at': '2026-09-26T10:00:00+08:00',
        'end_at': '2026-09-27T20:00:00+08:00', 'budget': {'amount_minor': 300000, 'currency': 'CNY'},
        'stay_budget': {'amount_minor': 100000, 'currency': 'CNY'}, 'party_size': 2})
    return {'traveler_http': st, 'journey_http': st2, 'journey_id': j.get('id') or j}


def ask(port, jid, key, body):
    import urllib.error
    import urllib.request
    req = urllib.request.Request('http://127.0.0.1:%d/api/v1/journeys/%s/plans/generate' % (port, jid),
                                 method='POST')
    req.add_header('Content-Type', 'application/json')
    req.add_header('Idempotency-Key', key)
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, json.dumps(body).encode(), timeout=90) as f:
            return {'key': key, 'request_body': body, 'status': f.status, 'bytes': len(f.peek(4096)) if hasattr(f, 'peek') else None,
                    'body': f.read().decode('utf-8', 'replace')[:600], 'elapsed_ms': int((time.time() - t0) * 1000),
                    'at': time.strftime('%H:%M:%S')}
    except urllib.error.HTTPError as e:
        raw = e.read()
        return {'key': key, 'request_body': body, 'status': e.code, 'bytes': len(raw),
                'body': raw.decode('utf-8', 'replace')[:600], 'elapsed_ms': int((time.time() - t0) * 1000),
                'at': time.strftime('%H:%M:%S')}
    except Exception as e:  # noqa: BLE001
        return {'key': key, 'request_body': body, 'status': None,
                'error': type(e).__name__ + ': ' + str(e)[:160],
                'elapsed_ms': int((time.time() - t0) * 1000), 'at': time.strftime('%H:%M:%S')}


def dump(db, like='%'):
    con = sqlite3.connect('file:%s?mode=ro' % str(db).replace('\\', '/'), uri=True, timeout=30)
    con.row_factory = sqlite3.Row
    rows = [{'key': r['key'], 'operation': r['operation'], 'response_status': r['response_status'],
             'response_json_bytes': len(r['response_json'] or ''), 'request_hash_head': (r['request_hash'] or '')[:16],
             'created_at': r['created_at'], 'expires_at': r['expires_at'],
             'response_json_head': (r['response_json'] or '')[:160]}
            for r in con.execute('SELECT * FROM idempotency_keys WHERE key LIKE ? ORDER BY created_at', (like,))]
    plans = con.execute('SELECT COUNT(*) FROM plan_versions').fetchone()[0]
    con.close()
    return {'connection': 'file:%s?mode=ro (a SECOND, read-only connection)' % db, 'rows': rows,
            'plan_versions': plans}


def kill(name, pid):
    cmd = rig.cmdline(pid)
    mine = 'app.main:app' in cmd
    rc = subprocess.run(['taskkill', '/PID', str(pid), '/T', '/F'], capture_output=True,
                        text=True, encoding='utf-8', errors='replace').returncode
    return {'killed': name, 'pid': pid, 'rc': rc, 'cmdline_read_before_kill_is_ours': mine}


def run(kind, name, port, patch_fn, label):
    db = BASE / ('t1_%s.s3db' % name)
    tree = BASE / name
    made = rig.make_private_copy(name, patch_fn)
    sd = seed(tree, db)
    b = rig.start_backend(name, port, tree, db)
    j = journey(port)
    steps = []
    key = 'ord0288-%s-%s' % (label, time.strftime('%H%M%S'))
    first = ask(port, j['journey_id'], key, {'candidate_count': 3})
    steps.append({'intent': 'the send that claims the key', 'response': first,
                  'durable_after_this': dump(db)})
    if kind == 'crash':
        second = ask(port, j['journey_id'], key, {'candidate_count': 3})
        steps.append({'intent': 'same key again while the placeholder is still NULL', 'response': second,
                      'is_409_incomplete': second['status'] == 409})
        kill(name, b['pid'])
        b2 = rig.start_backend(name, port, tree, db)
        steps.append({'intent': 'the fresh process I just started for the replay', 'backend': b2})
        third = ask(port, j['journey_id'], key, {'candidate_count': 3})
        steps.append({'intent': 'same key against a FRESH process on the same file (the owner died here)',
                      'response': third, 'still_409_incomplete': third['status'] == 409})
        different_key = ask(port, j['journey_id'], key + '-fresh', {'candidate_count': 3})
        steps.append({'intent': 'a DIFFERENT key on the same journey, to show the journey is still usable',
                      'response': different_key, 'durable_after_this': dump(db)})
        carrier = 'the unhandled RuntimeError inside _generate_plans_answer'
    else:
        other = ask(port, j['journey_id'], key, {'candidate_count': 5})
        steps.append({'intent': 'same key, DIFFERENT body with the signature comparison deleted',
                      'response': other, 'still_409': other['status'] == 409,
                      'durable_after_this': dump(db)})
        carrier = ('the guard `if row.request_hash != signature:` inside _replay_committed_accept, which is '
                   'the comparison plans/generate actually reaches' if kind == 'signature'
                   else 'the replan-route guard `if existing_generation.request_hash != '
                        'generation_signature:` - kept as the NEGATIVE case of a mutation control: deleting '
                        'it does not reach this leg')
    out = {'arm': 't1_%s_mutant_%s' % (kind, name), 'measured_on': rig.TIP, 'private_copy': made,
           'seed': sd, 'backend': b, 'journey': j, 'db': str(db), 'carrier_removed_or_injected': carrier,
           'steps': steps}
    p = BASE / ('cell_%s.json' % out['arm'])
    p.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding='utf-8', newline='\n')
    print(json.dumps({'arm': out['arm'],
                      'statuses': [(st.get('intent') or '')[:30] + '=' + str((st.get('response') or {}).get('status'))
                                   for st in steps],
                      'rows': len(dump(db)['rows']), 'file': p.name}, ensure_ascii=False))
    OUT.append(out)
    kill(name, b['pid'])
    return out


run('crash', 'mut_crash', PAIR['M1'], rig.patch_crash_after_claim, 'crash')
run('signature', 'mut_sig', PAIR['M2'], rig.patch_drop_replay_signature_check, 'sig')
run('wrong_carrier', 'mut_sig_wrong', PAIR['M2'], rig.patch_drop_signature_check, 'sigwrong')
(BASE / 'mutant_arms.json').write_text(json.dumps(OUT, ensure_ascii=False, indent=1), encoding='utf-8',
                                       newline='\n')
print('mutant arms done', [o['arm'] for o in OUT])
