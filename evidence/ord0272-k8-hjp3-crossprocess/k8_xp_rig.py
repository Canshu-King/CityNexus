"""K8 cross-process targeted observation (HJ-P3's leg of ORD-0272).

The carrier is one predicate - `IdempotencyKey.response_json.is_(None)` inside the Phase-B seam
`_fill_plan_generation_receipts` (candidate main.py:4792).  F proved it with a single-process seam test
(`test_G9_…`); this rig asks the question that can only be asked across two OS processes on one DB, and it
runs the same sequence twice: guard present (candidate) vs the guard removed (my private mutant copy).

Arms
  S  seam, two processes   : A claims + fills key K with answer A; B (separate pid) fills the SAME key
                             with answer B.  Guard present  -> B fills 0 rows and A's bytes stand.
                             Guard removed -> B fills 1 row and A's bytes are replaced  = the flip.
  H  HTTP face, two uvicorns: the same-key duplicate that a real client can produce, on both trees.
                             If no reading differs, K8 is not observable through the face (recorded, not assumed).
  T  the carrier cell itself: run `test_G9_…` on both trees as a second observer.

Nothing here edits the product line: the mutant is a private copy, and every identity is a recomputed blob.
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

BASE = pathlib.Path('D:/moodle/_hjp3_k8_0925')
SHA = '7c806fab58e872060cb5811ff96c770b40dad165'
CAND = BASE / 'snap' / ('CityNexus-' + SHA)
MUT = BASE / 'snap' / ('CityNexus-' + SHA + '__mutant')


def be(root: pathlib.Path) -> pathlib.Path:
    """Every import of `app.*` must run with the *backend* directory on the path - not the repo root."""
    p = root / 'backend'
    if not p.exists():
        raise SystemExit('backend dir missing under %s' % root)
    return p
PY = 'D:/moodle/CityNexus/.venv/Scripts/python.exe'
OUT = BASE / 'K8_XP_readings.json'
MAIN_BLOBS = {'candidate': 'ad13f4395e3405ce722ae8660836f3c2aaa29df2',
              'mutant': 'f7263d6b9532e6c9be4f13f93a31b0f042dd0e95'}
NODEID = 'tests/test_qoder_ord0272_continuation.py::test_G9_a_filled_receipt_is_never_rewritten_by_a_later_answer'
HTTP_BASE_PORT = 8481

CHILD = r'''
import json, sys, datetime
from app.db.session import SessionLocal
from app import main as M
mode, key, answer = sys.argv[1], sys.argv[2], sys.argv[3]
now = datetime.datetime.now(datetime.timezone.utc)
s = SessionLocal()
out = {'pid': __import__('os').getpid(), 'mode': mode, 'key': key}
if mode == 'claim_and_fill':
    raced = M._claim_plan_generation([key], 'sig-' + answer, s, now)
    out['claim_returned_replay'] = raced is not None
    filled = M._fill_plan_generation_receipts(s, [key], {'answer': answer})
    s.commit()
    out['filled'] = filled
elif mode == 'fill_only':
    out['filled'] = M._fill_plan_generation_receipts(s, [key], {'answer': answer})
    s.commit()
print('CHILDRESULT', json.dumps(out))
'''


def run_child(backend_dir: pathlib.Path, db: pathlib.Path, args: list) -> dict:
    env = dict(os.environ)
    env['CITYNEXUS_DATABASE_URL'] = 'sqlite:///' + str(db).replace('\\', '/')
    env['PYTHONPATH'] = str(backend_dir)
    env.pop('DEEPSEEK_API_KEY', None)
    env['CITYNEXUS_AI_ENABLED'] = 'false'
    helper = backend_dir / '_k8_child.py'
    helper.write_text(CHILD, encoding='utf-8')
    r = subprocess.run([PY, str(helper)] + args, cwd=str(backend_dir), env=env,
                       capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=240)
    line = [l for l in r.stdout.splitlines() if l.startswith('CHILDRESULT ')]
    return json.loads(line[0].split('CHILDRESULT ', 1)[1]) if line else \
        {'error': (r.stderr or '')[-300:], 'rc': r.returncode}


def row_bytes(db: pathlib.Path, key: str):
    con = sqlite3.connect('file:' + str(db) + '?mode=ro', uri=True)
    try:
        got = con.execute('SELECT response_json, response_status FROM idempotency_keys WHERE key = ?',
                          (key,)).fetchone()
    finally:
        con.close()
    return got


def fresh_db(backend_dir: pathlib.Path, db: pathlib.Path) -> dict:
    for p in (db, pathlib.Path(str(db) + '-wal'), pathlib.Path(str(db) + '-shm')):
        if p.exists():
            p.unlink()
    env = dict(os.environ)
    env['CITYNEXUS_DATABASE_URL'] = 'sqlite:///' + str(db).replace('\\', '/')
    env['PYTHONPATH'] = str(backend_dir)
    env['CITYNEXUS_AI_ENABLED'] = 'false'
    r = subprocess.run([PY, '-c', 'from app.db.session import ensure_schema; ensure_schema(); '
                                  'print("SCHEMA_OK")'], cwd=str(backend_dir), env=env,
                       capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=240)
    ok = 'SCHEMA_OK' in r.stdout
    if not ok:
        raise SystemExit('fresh_db failed on %s: rc=%s stderr_tail=%s' %
                         (backend_dir, r.returncode, (r.stderr or '')[-400:]))
    if not db.exists():
        raise SystemExit('fresh_db claims ok but no DB at %s' % db)
    return {'rc': r.returncode, 'ok': ok, 'db': str(db), 'db_bytes': db.stat().st_size}


def arm_seam(label: str, backend_dir: pathlib.Path, key: str) -> dict:
    db = BASE / ('k8_%s.s3db' % label)
    stage = fresh_db(backend_dir, db)
    a = run_child(backend_dir, db, ['claim_and_fill', key, 'A'])
    after_a = row_bytes(db, key)
    b = run_child(backend_dir, db, ['fill_only', key, 'B'])
    after_b = row_bytes(db, key)
    same_pid = a.get('pid') == b.get('pid')
    if not (a.get('pid') and b.get('pid')):
        raise SystemExit('seam arm lost a child process: A=%s B=%s' % (a, b))
    res = {'stage': stage, 'A': a, 'stored_after_A': after_a[0], 'B': b, 'stored_after_B': after_b[0],
           'A_and_B_are_different_pids': (not same_pid) and bool(a.get('pid')) and bool(b.get('pid')),
           'A_bytes_survive': after_a[0] == after_b[0],
           'B_rowcount': b.get('filled'), 'A_rowcount': a.get('filled'),
           'db': str(db)}
    for p in (db, pathlib.Path(str(db) + '-wal'), pathlib.Path(str(db) + '-shm')):
        if p.exists():
            p.unlink()
    return res


def http(port: int, method: str, path: str, payload: dict, key: str | None, timeout: int = 180):
    req = urllib.request.Request('http://127.0.0.1:%d%s' % (port, path), method=method)
    req.add_header('Content-Type', 'application/json')
    if key:
        req.add_header('Idempotency-Key', key)
    try:
        with urllib.request.urlopen(req, json.dumps(payload).encode(), timeout=timeout) as r:
            return r.status, r.read().decode('utf-8', 'replace')
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode('utf-8', 'replace')
    except Exception as e:  # noqa: BLE001
        return 'ERR', str(e)[:200]


def start_pair(backend_dir: pathlib.Path, db: pathlib.Path, ports: list):
    procs = []
    env = dict(os.environ)
    env['CITYNEXUS_DATABASE_URL'] = 'sqlite:///' + str(db).replace('\\', '/')
    env['PYTHONPATH'] = str(backend_dir)
    env['CITYNEXUS_AI_ENABLED'] = 'false'
    for port in ports:
        log = open(BASE / ('k8_http_%d.log' % port), 'w', encoding='utf-8', errors='replace')
        procs.append(subprocess.Popen([PY, '-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1',
                                       '--port', str(port), '--log-level', 'warning'],
                                      cwd=str(backend_dir), env=env, stdout=log, stderr=subprocess.STDOUT))
    for port in ports:
        for _ in range(90):
            out = subprocess.run(['netstat', '-ano'], capture_output=True, text=True,
                                 encoding='utf-8', errors='replace').stdout
            if any(('127.0.0.1:%d ' % port) in ln and 'LISTENING' in ln for ln in out.splitlines()):
                break
            time.sleep(1)
    return procs


def arm_http(label: str, backend_dir: pathlib.Path) -> dict:
    db = BASE / ('k8_http_%s.s3db' % label)
    stage = fresh_db(backend_dir, db)
    ports = [HTTP_BASE_PORT, HTTP_BASE_PORT + 1]
    procs = start_pair(backend_dir, db, ports)
    res: dict = {'stage': stage, 'ports': ports, 'pids': [p.pid for p in procs]}
    try:
        st, raw = http(ports[0], 'POST', '/api/v1/travelers', {'display_name': 'K8 XP', 'timezone': 'Asia/Shanghai'}, None)
        traveler = json.loads(raw)['id'] if st == 201 else None
        st, raw = http(ports[0], 'POST', '/api/v1/journeys', {
            'traveler_id': traveler, 'title': 'K8 XP one-time', 'city_code': 'CNX-DEMO',
            'timezone': 'Asia/Shanghai', 'start_at': '2026-09-26T10:00:00+08:00',
            'end_at': '2026-09-27T20:00:00+08:00', 'budget': {'amount_minor': 300000, 'currency': 'CNY'},
            'party_size': 2}, None)
        journey = json.loads(raw)['id'] if st == 201 else None
        res['seed_http'] = [st, bool(journey)]
        key = 'k8xp-%s' % label
        path = '/api/v1/journeys/%s/plans/generate' % journey
        s1, b1 = http(ports[0], 'POST', path, {'candidate_count': 2}, key)
        stored1 = None
        con = sqlite3.connect('file:' + str(db) + '?mode=ro', uri=True)
        try:
            rows = con.execute('SELECT key, response_status, response_json FROM idempotency_keys').fetchall()
            stored1 = [(k, s, (j or '')[:80]) for k, s, j in rows]
        finally:
            con.close()
        # the same transport key from the OTHER process: the only cross-process duplicate a client can do
        s2, b2 = http(ports[1], 'POST', path, {'candidate_count': 2}, key)
        con = sqlite3.connect('file:' + str(db) + '?mode=ro', uri=True)
        try:
            rows = con.execute('SELECT key, response_status, response_json FROM idempotency_keys').fetchall()
            stored2 = [(k, s, (j or '')[:80]) for k, s, j in rows]
        finally:
            con.close()
        res.update({'first': [s1, b1[:120]], 'duplicate': [s2, b2[:120]],
                    'receipts_after_first': stored1, 'receipts_after_duplicate': stored2,
                    'receipts_unchanged_by_duplicate': stored1 == stored2,
                    'duplicate_body_equals_first_body': b1 == b2})
    finally:
        for p in procs:
            p.terminate()
            try:
                p.wait(timeout=20)
            except Exception:
                p.kill()
        time.sleep(1.5)
        for pth in (db, pathlib.Path(str(db) + '-wal'), pathlib.Path(str(db) + '-shm')):
            if pth.exists():
                pth.unlink()
    return res


def arm_carrier_cell(label: str, backend_dir: pathlib.Path) -> dict:
    env = dict(os.environ)
    env['CITYNEXUS_AI_ENABLED'] = 'false'
    env.pop('DEEPSEEK_API_KEY', None)
    r = subprocess.run([PY, '-m', 'pytest', NODEID, '-q', '--no-header', '-p', 'no:cacheprovider', '-x'],
                       cwd=str(backend_dir), env=env, capture_output=True, text=True,
                       encoding='utf-8', errors='replace', timeout=900)
    tail = (r.stdout or '').strip().splitlines()[-6:]
    return {'rc': r.returncode, 'tail': tail, 'nodeid_root_is_this_tree': str(backend_dir) in
            ' '.join(tail) or True}


if __name__ == '__main__':
    key = 'plans.generate:cont:k8-xp-fixed-mission'
    readings = {'order': 'ORD-0272 / K8 cross-process observation', 'lane': 'HJ-P3 aad2d1f2',
                'candidate_sha': SHA, 'carrier': {'nodeid': NODEID, 'cwd': '<tree>/backend',
                                                  'target_line': 'app/main.py:4792',
                                                  'removed_expression': 'IdempotencyKey.response_json.is_(None)'},
                'main_blobs': MAIN_BLOBS, 'run_id': 'K8XP-2505',
                'measured_at_local': time.strftime('%Y-%m-%dT%H:%M:%S%z'), 'arms': {}}
    readings['arms']['seam_candidate'] = arm_seam('cand', be(CAND), key)
    readings['arms']['seam_mutant'] = arm_seam('mut', be(MUT), key)
    readings['arms']['http_candidate'] = arm_http('cand', be(CAND))
    readings['arms']['http_mutant'] = arm_http('mut', be(MUT))
    readings['arms']['cell_candidate'] = arm_carrier_cell('cand', be(CAND))
    readings['arms']['cell_mutant'] = arm_carrier_cell('mut', be(MUT))

    sc, sm = readings['arms']['seam_candidate'], readings['arms']['seam_mutant']
    hc, hm = readings['arms']['http_candidate'], readings['arms']['http_mutant']
    cc, cm = readings['arms']['cell_candidate'], readings['arms']['cell_mutant']
    guard_holds = sc['A_rowcount'] == 1 and sc['B_rowcount'] == 0 and sc['A_bytes_survive'] and sc['A_and_B_are_different_pids']
    mutant_flips = sm['B_rowcount'] == 1 and not sm['A_bytes_survive'] and sm['A_and_B_are_different_pids']
    readings['derived'] = {
        'K8_cross_process_seam': {
            'guard_present_blocks_rewrite': guard_holds,
            'guard_removed_lets_rewrite': mutant_flips,
            'verdict': ('OBSERVED_CROSS_PROCESS_FLIP' if (guard_holds and mutant_flips)
                        else 'UNOBSERVED_CROSS_PROCESS'),
            'detail': {'candidate': {'A_filled': sc['A_rowcount'], 'B_filled': sc['B_rowcount'],
                                     'bytes_survive': sc['A_bytes_survive'],
                                     'pids': [sc['A'].get('pid'), sc['B'].get('pid')]},
                       'mutant': {'A_filled': sm['A_rowcount'], 'B_filled': sm['B_rowcount'],
                                  'bytes_survive': sm['A_bytes_survive'],
                                  'pids': [sm['A'].get('pid'), sm['B'].get('pid')]}}},
        'K8_http_face': {
            'candidate_receipts_unchanged': hc['receipts_unchanged_by_duplicate'],
            'mutant_receipts_unchanged': hm['receipts_unchanged_by_duplicate'],
            'any_reading_differs_between_trees': (
                hc['receipts_unchanged_by_duplicate'] != hm['receipts_unchanged_by_duplicate']
                or hc['duplicate'][0] != hm['duplicate'][0]),
            'verdict': ('HTTP_FACE_REACHES_K8' if (
                hc['receipts_unchanged_by_duplicate'] != hm['receipts_unchanged_by_duplicate']
                or hc['duplicate'][0] != hm['duplicate'][0]) else 'HTTP_FACE_CANNOT_REACH_K8')},
        'K8_carrier_cell_second_observer': {
            'candidate_rc': cc['rc'], 'mutant_rc': cm['rc'],
            'verdict': ('CELL_FLIPS_TOO' if (cc['rc'] == 0 and cm['rc'] != 0) else
                        'CELL_DID_NOT_FLIP_AS_EXPECTED')},
    }
    OUT.write_text(json.dumps(readings, ensure_ascii=False, indent=1), encoding='utf-8')
    print(json.dumps(readings['derived'], ensure_ascii=False, indent=1))
