"""ORD-0288 T-1 on the CURRENT tip: does the shipped reading transfer, or is it only true of the generation
it was measured on?

Why this exists instead of a re-run of the whole batch: the T-1(a)/(b) cells shipped at 17:30 on
`dc964086…`, and the commander has just named that commit as the online base and asked for the order to be
opened. The one thing my shipped receipt cannot answer is transferability - `backend/app/main.py` differs by
exactly 4 added lines between that commit and the current tip (an ORD-0307 startup gate), and "the code that
decides the answer is unchanged" is an inference, not a measurement. So this instrument re-runs the SHAPE of
C1 + the (b) error-path arm on the current tip, in a fresh one-time database, with two processes, and reports
what the store says.

Nothing new is invented here: the two published instruments are imported and used as libraries, with their
paths pointed at this batch directory. 0 product bytes written (read-only `git archive`), 0 pushes to any
ref, `demo/reset` 0, `_live.db`/`_preview.db` 0, DEEPSEEK_API_KEY popped by the rig before any spawn.
"""
from __future__ import annotations

import importlib.util as iu
import io
import json
import os
import pathlib
import subprocess
import sys
import time

REPO = pathlib.Path('D:/moodle/CityNexus')
SRC = pathlib.Path('D:/moodle/HJ-P3_evidence')
TIP = '2344145ce6342b6ac32ac4d0955c0f524d8c9320'
MEASURED_BEFORE = 'dc964086c9d412573ac19d70b24b30e6c3ee6168'
BASE = pathlib.Path('D:/moodle/_hjp3_0288t1x_0926')
BASE.mkdir(exist_ok=True)
PORTS = {'A': 8621, 'B': 8622}


def load(name, path):
    spec = iu.spec_from_file_location(name, str(path))
    mod = iu.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def load_without_running(name, path, tail='main()'):
    """The published T-1 arms script ends in a bare `main()` call, so importing it would RUN the 17:30
    batch against the old state file. This reads the same source, drops that one trailing statement, and
    executes the rest - the functions are reused verbatim, and the fact that a statement was removed is
    recorded in the reading rather than hidden."""
    src = pathlib.Path(path).read_text(encoding='utf-8')
    lines = [l for l in src.splitlines()]
    idx = max(i for i, l in enumerate(lines) if l.strip() == tail)
    assert lines[idx] == tail, 'the tail line is indented; refusing to strip blindly'
    kept = lines[:idx] + lines[idx + 1:]
    import types
    mod = types.ModuleType(name)
    mod.__file__ = str(path)
    code = compile('\n'.join(kept) + '\n', str(path) + ' [tail main() removed]', 'exec')
    exec(code, mod.__dict__)
    sys.modules[name] = mod
    proof = {'file': str(path), 'statement_removed': tail, 'line_where_it_stood': idx + 1,
             'lines_kept': len(kept), 'bytes_kept': len('\n'.join(kept).encode('utf-8')),
             'full_bytes': len(src.encode('utf-8'))}
    return mod, proof



# the exported tree: read-only archive of the current tip's backend, into my own directory
tree = BASE / 'backend'
if not (tree / 'app' / 'main.py').exists():
    r = subprocess.run(['git', '-C', str(REPO), 'archive', '--format=tar', TIP], capture_output=True)
    assert r.returncode == 0, 'git archive failed: ' + (r.stderr or b'')[-200:].decode('utf-8', 'replace')
    import tarfile
    import io as _io
    with tarfile.open(fileobj=_io.BytesIO(r.stdout)) as tf:
        tf.extractall(path=str(BASE))
    print('exported', TIP[:8], '->', tree, flush=True)
for need in ('data', 'contracts'):
    if not (BASE / need).exists():
        rr = subprocess.run(['git', '-C', str(REPO), 'archive', '--format=tar', TIP, need],
                            capture_output=True)
        import tarfile
        import io as _io
        with tarfile.open(fileobj=_io.BytesIO(rr.stdout)) as tf:
            tf.extractall(path=str(BASE))
        print('also exported', need, flush=True)

rig = load('rigx', SRC / 'o0288_rig.py')
rig.BASE = BASE
rig.TIP = TIP
rig.PRISTINE = tree
rig.DB = BASE / 't1x.s3db'
rig.STATE = BASE / 'o0288t1x_state.json'
rig.PIDS = BASE / 'o0288t1x_pids.json'
rig.PAIRS = dict(PORTS)
rig.do_start()
st = json.loads(rig.STATE.read_text(encoding='utf-8'))

EQ = None
arms, reuse_proof = load_without_running('armsx', SRC / 'o0288_arms.py')
arms.BASE = BASE
arms.STATE = st
arms.TIP = TIP
arms.PA = st['backends'][0]['port']
arms.PB = st['backends'][1]['port']

j = arms.seed_journey()
arms.JOURNEY = j['journey_id']
(BASE / 'seed_journey_t1x.json').write_text(json.dumps(j, ensure_ascii=False, indent=1),
                                            encoding='utf-8', newline='\n')
assert arms.JOURNEY, 'no journey seeded: %s' % json.dumps(j)[:200]
K = 'ord0288-t1x-%s' % time.strftime('%H%M%S')
K2 = 'ord0288-t1x-b-%s' % time.strftime('%H%M%S')
arms.KEYS_THIS_RUN = [K, K2]

r1 = arms.post_gen(arms.PA, K, {'candidate_count': 3})
r2 = arms.post_gen(arms.PB, K, {'candidate_count': 3})
a1 = arms.arm('t1x_same_key_two_processes_on_current_tip', [
    {'intent': 'first send on process A', 'response': r1},
    {'intent': 'same key same body on process B (a different OS process, one shared file)',
     'response': r2, 'replay_identical_payload': arms.canon(r1) == arms.canon(r2),
     'same_status': r1['status'] == r2['status']}],
    extra={'key': K, 'expected_per_the_arbiter': 'observe durable ownership (no preset verdict)'})

r3 = arms.post_gen(arms.PB, K, {'candidate_count': 5})
a2 = arms.arm('t1x_same_key_different_body_on_current_tip',
              [{'intent': 'same key, different candidate_count, other process', 'response': r3,
                'is_409': r3['status'] == 409}], extra={'key': K})

r4 = arms.post_gen(arms.PA, K2, {'candidate_count': 3})
after = arms.rows(st['db'])
r5 = arms.post_gen(arms.PB, K2, {'candidate_count': 3})
a3 = arms.arm('t1x_error_path_records_response_status_on_current_tip',
              [{'intent': 'keyed send the route refuses', 'response': r4},
               {'intent': 'replay of that key from the other process', 'response': r5,
                'replay_identical_payload': arms.canon(r4) == arms.canon(r5)}],
              extra={'key': K2, 'row_for_this_key': [x for x in after['idempotency_keys']
                                                     if x['key'].endswith(K2)],
                     'response_status_is_not_null': all(
                         x['response_status'] is not None for x in after['idempotency_keys']
                         if x['key'].endswith(K2))})

SHIPPED = json.loads((pathlib.Path('D:/moodle/_hjp3_0288t1_0925') / 'RECEIPT_O0288T1-1730.json')
                     .read_text(encoding='utf-8'))
_c1 = [x for x in SHIPPED['cells'] if x['id'].startswith('C1_')][0]
SC1 = _c1.get('readings') or _c1.get('measured')
LOG_A = BASE / 'backend_A.log'
gate = ''
if LOG_A.exists():
    gate = '\n'.join(x for x in LOG_A.read_text(encoding='utf-8', errors='replace').splitlines()
                     if 'REDENTIAL' in x.upper() or 'Application startup' in x)[:600]
rows_after = arms.rows(st['db'], like='%')


def shape(cell):
    d = cell['durable_read_after']['rows_for_this_arms_keys']
    return {'statuses': [s['response']['status'] for s in cell['steps']],
            'rows_for_this_key': len(d),
            'operations': sorted({x['operation'] for x in d}),
            'response_statuses': [x['response_status'] for x in d],
            'response_json_bytes': [x['response_json_bytes'] for x in d]}


def drop_trace(obj):
    """The shipped cell states its replay equality at the JSON-VALUE level, because a fresh trace id on a
    replayed envelope is a fact about the renderer, not about the answer. My first pass of this instrument
    compared canon() with trace_id still inside and reported the replay as unequal - the claim, not the
    product, was at the wrong level, so both levels are computed here and named separately."""
    if isinstance(obj, dict):
        return {k: drop_trace(v) for k, v in obj.items() if k != 'trace_id'}
    if isinstance(obj, list):
        return [drop_trace(v) for v in obj]
    return obj


def eq_level(x, y, strip=False):
    try:
        a, b = json.loads(x['body_text']), json.loads(y['body_text'])
    except Exception:  # noqa: BLE001
        return None
    if strip:
        a, b = drop_trace(a), drop_trace(b)
    return json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)


out = {'ran_at_local': time.strftime('%Y-%m-%dT%H:%M:%S%z'),
       'order': 'ORD-0288 T-1 transfer check - current tip',
       'lane': 'HJ-P3 aad2d1f2-4de9-406b-a5df-afa0e2bcea58',
       'scope': 'the keyed plans/generate write leg of a one-time local backend, two OS processes, one file',
       'generation_under_test': TIP,
       'generation_measured_before_on_branch': MEASURED_BEFORE,
       'how_read': 'git archive of the tip into my own directory (read-only), two uvicorn processes, the '
                   'durable half read through a second READ-ONLY sqlite connection naming file/table/key',
       'artifact': 'o0288t1x_transfer.py (this instrument) + the three cell files it wrote',
       'reuse_of_published_instruments': {'rig': 'o0288_rig.py imported with its paths pointed here',
                                          'arms': reuse_proof},
       'backends': st['backends'], 'db': st['db'],
       'credential_gate_lines_from_the_startup_log': gate,
       'replay_equality_measured_two_ways': {
           'cross_process_pair': {'raw_json_equal': eq_level(r1, r2),
                                  'equal_once_trace_id_dropped': eq_level(r1, r2, True),
                                  'trace_ids': [json.loads(x['body_text'])['error']['trace_id']
                                                if 'error' in json.loads(x['body_text']) else None
                                                for x in (r1, r2)]},
           'error_path_pair': {'raw_json_equal': eq_level(r4, r5),
                               'equal_once_trace_id_dropped': eq_level(r4, r5, True)}},
       'cells': {'t1x_a_same_key_two_processes': shape(a1),
                 't1x_a_same_key_different_body': shape(a2),
                 't1x_b_error_path_records_status': shape(a3)},
       'store_totals_after': {'idempotency_rows_all_keys': rows_after['total_idempotency_rows_all_keys'],
                              'counts': rows_after['counts']},
       'comparison_with_the_shipped_reading': {
           'shipped_cell': 'C1_same_key_across_two_processes_leaves_one_durable_owner_row',
           'shipped_on_tip': MEASURED_BEFORE, 'shipped_key': SC1['key'],
           'shipped_status': SC1['first_send']['status'],
           'shipped_row_count_for_the_key': SC1['rows_holding_this_key'],
           'shipped_operation': SC1['idempotency_keys_row']['operation'],
           'shipped_response_status': SC1['idempotency_keys_row']['response_status'],
           'shipped_response_json_bytes': SC1['idempotency_keys_row']['response_json_bytes'],
           'now': {'statuses': shape(a1)['statuses'], 'rows': shape(a1)['rows_for_this_key'],
                   'operations': shape(a1)['operations'],
                   'response_statuses': shape(a1)['response_statuses'],
                   'response_json_bytes': shape(a1)['response_json_bytes']}},
       'boundary': {'product_bytes_written': 0, 'refs_pushed': 0, 'demo_reset': 0,
                    'live_or_preview_db': 0, 'credentials_printed': 0,
                    'ports': [PORTS['A'], PORTS['B']]}}
o = out['comparison_with_the_shipped_reading']['now']
same = (o['rows'] == out['comparison_with_the_shipped_reading']['shipped_row_count_for_the_key']
        and o['operations'] == [out['comparison_with_the_shipped_reading']['shipped_operation']]
        and o['response_statuses'] == [out['comparison_with_the_shipped_reading']['shipped_response_status']]
        and all(s == out['comparison_with_the_shipped_reading']['shipped_status'] for s in o['statuses']))
out['verdict'] = {
    'durable_ownership_observed_on_the_current_tip': bool(o['rows'] == 1 and o['operations']
                                                          == ['plans.generate']),
    'the_answer_is_a_refusal_not_a_silence': bool(all(s and s >= 400 for s in o['statuses'])),
    'cross_process_replay_equal_at_the_json_value_level': bool(
        out['replay_equality_measured_two_ways']['cross_process_pair']['equal_once_trace_id_dropped']),
    'cross_process_replay_byte_identical': bool(
        out['replay_equality_measured_two_ways']['cross_process_pair']['raw_json_equal']),
    'same_key_different_body_still_refused': bool(a2['steps'][0]['response']['status'] == 409),
    'error_path_row_still_carries_a_response_status': bool(
        a3['extra']['response_status_is_not_null'] and a3['extra']['row_for_this_key']),
    'reading_matches_the_shipped_one_row_for_row': bool(same)}
CLAIMS = ('durable_ownership_observed_on_the_current_tip', 'the_answer_is_a_refusal_not_a_silence',
          'cross_process_replay_equal_at_the_json_value_level', 'same_key_different_body_still_refused',
          'error_path_row_still_carries_a_response_status', 'reading_matches_the_shipped_one_row_for_row')
# `cross_process_replay_byte_identical` is a READING, not a claim: the shipped C6 states equality at the
# JSON-value level precisely because the bytes differ (a fresh trace_id). Folding it into ALL_HOLD would
# turn an honest reading into a false red.
out['verdict']['ALL_HOLD'] = all(out['verdict'][k] for k in CLAIMS)
out['verdict_basis'] = {'claims_aggregated_into_ALL_HOLD': list(CLAIMS),
                        'readings_reported_but_not_aggregated': ['cross_process_replay_byte_identical']}
(BASE / 't1x_transfer_reading.json').write_text(json.dumps(out, ensure_ascii=False, indent=1),
                                                encoding='utf-8', newline='\n')
print(json.dumps(out['verdict'], ensure_ascii=False))
print(json.dumps(out['comparison_with_the_shipped_reading'], ensure_ascii=False)[:500])
print('gate:', (gate or '(none)')[:200])
rig.do_stop()
print('ports after stop:', {p: rig.listening(p) for p in PORTS.values()})
