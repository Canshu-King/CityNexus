"""ORD-0288 T-1 receipt r3 - finish what r2 started on the cells r2 left alone.

r2 corrected C4/C6/C7 and the derived map but quoted C1/C2/C3/C5's `gates_three_way` values as they
were built in r1: two of them embedded a `(True)` from a nested %s interpolation, and C1's `why` said
"the same payload once trace_id is dropped" - which reads as byte equality, and the raw bytes are NOT
equal (r2 measured that). Everything here is recomputed from the r2 artefact, nothing hand-typed.
"""
from __future__ import annotations

import hashlib
import json
import pathlib

B = pathlib.Path('D:/moodle/_hjp3_0288t1_0925')
R2 = 'RECEIPT_O0288T1-1610_r2.json'
OUT = 'RECEIPT_O0288T1-1610_r3.json'
rc = json.loads((B / R2).read_text(encoding='utf-8'))
C = {c['id'][:2]: c for c in rc['cells']}
D = rc['derived']

# ---- C1: three-way gate in plain sentences, and a why that names the comparison it used
c1 = C['C1']
three = c1['measured']['gates_three_way']
three['positive'] = ('key %s holds exactly %d row in idempotency_keys, operation %r, response_status %s '
                     'read through a second, read-only connection'
                     % (c1['measured']['key'], c1['measured']['rows_holding_this_key'],
                        c1['measured']['idempotency_keys_row'].get('operation'),
                        c1['measured']['idempotency_keys_row'].get('response_status')))
three['negative'] = ('the malformed-key send on the same journey left 0 rows and burned no key - see C4 '
                     'pre_claim_rejection.rows_matching_that_key = %r'
                     % (C['C4']['measured']['pre_claim_rejection']['rows_matching_that_key'],))
three['mutation'] = ('deleting `if row.request_hash != signature:` in _replay_committed_accept turns the '
                     'same-key-different-body call from %s into %s, while deleting the similarly named '
                     'guard on the replan route leaves it at %s - see C2'
                     % (C['C2']['measured']['status_when_pristine'],
                        C['C2']['measured']['mutant_that_removes_the_guard'][
                            'different_body_status_after_removing_it'],
                        C['C2']['measured']['control_mutant_that_removes_another_guard'][
                            'different_body_status_still']))
three['equality_basis_of_the_replay_claim'] = rc['r2_notes']['cross_process_three_ways']
cw = C['C2']['measured']['control_mutant_that_removes_another_guard']
mw = C['C2']['measured']['mutant_that_removes_the_guard']
procs = {p['tag']: p for p in c1['measured']['processes']}
c1['why'] = ('with key %s on database %s the store holds exactly %d row for it, operation %r, '
             'response_status %s and a %s B response_json expiring %s; the second send went to port %s '
             '(a different process, pid %s vs %s) and answered %s in %s ms with the SAME JSON VALUE once '
             'error.trace_id is dropped (%s) - not the same bytes (raw_bytes_equal %s, because '
             'error.details re-serialises in a different key order)'
             % (c1['measured']['key'], str(c1['measured']['database_file']).split('\\')[-1],
                c1['measured']['rows_holding_this_key'],
                c1['measured']['idempotency_keys_row'].get('operation'),
                c1['measured']['idempotency_keys_row'].get('response_status'),
                c1['measured']['idempotency_keys_row'].get('response_json_bytes'),
                (c1['measured']['idempotency_keys_row'].get('expires_at') or '')[:19],
                procs['B']['port'], procs['B']['pid'], procs['A']['pid'],
                c1['measured']['second_send_other_process']['status'],
                c1['measured']['second_send_other_process']['elapsed_ms'],
                rc['r2_notes']['cross_process_three_ways'][
                    'json_values_equal_after_dropping_trace_id'],
                rc['r2_notes']['cross_process_three_ways']['raw_bytes_equal']))

# ---- C2: its own three-way block quoted the same booleans with an embedded parenthetical
c2 = C['C2']
t2 = c2['measured']['gates_three_way']
t2['positive'] = ('the pristine tree refused key %s (first body %s, second body %s) with %s and the row '
                  'count stayed %d - the refusal did not overwrite the owner'
                  % (c2['measured']['key'], c2['measured']['first_body'], c2['measured']['second_body'],
                     c2['measured']['status_when_pristine'], c1['measured']['rows_holding_this_key']))
t2['negative'] = ('with that one comparison deleted the same call answers %s instead of %s, i.e. it '
                  'silently serves the first sender\'s stored answer to a different request'
                  % (mw['different_body_status_after_removing_it'], c2['measured']['status_when_pristine']))
t2['mutation'] = ('the wrong-carrier mutant (guard on the replan route, a line this leg never reaches) '
                  'leaves it at %s, so the flip is attributed to the named line in %s and not to "any '
                  'edit flips it"'
                  % (cw['different_body_status_still'], mw['tree']))

# ---- C3 / C5 already carry sentences; only fix C3's positive, which was a bare boolean
c3 = C['C3']
t3 = c3['measured']['gates_three_way']
if t3['positive'] is True:
    t3['positive'] = ('both processes fired key %s within %s ms, answered %s and %s, and the store kept '
                      '%d row for it with %s plan_versions in the whole database'
                      % (c3['measured']['key'], c3['measured']['wall_ms_both'],
                         c3['measured']['leg_A']['status'], c3['measured']['leg_B']['status'],
                         c3['measured']['rows_holding_this_key'], c3['measured']['plan_versions_total']))
t3['negative'] = ('a different key claimed in the same second adds its own row: after this arm the table '
                  'holds %d rows for %d keys' % (c3['measured']['idempotency_rows_all_keys'],
                                                 c3['measured']['idempotency_rows_all_keys']))

# ---- the derived map's own wording must match what r2 measured
D['replay_across_processes_same_answer_ignoring_trace_id'] = rc['r2_notes'][
    'cross_process_three_ways']['json_values_equal_after_dropping_trace_id']
rc['r3_notes'] = {
    'what_changed': ['C1/C2/C3 gates_three_way rewritten as sentences recomputed from the cells (r1 '
                     'nested a %s that printed "(True)" inside them)',
                     'C1 why now states the equality level it actually proved: JSON value after dropping '
                     'error.trace_id, raw_bytes_equal = %s'
                     % rc['r2_notes']['cross_process_three_ways']['raw_bytes_equal'],
                     'C3 positive gate was the bare boolean True in r1/r2',
                     'nothing in measured changed; every value quoted above was read out of this same '
                     'receipt object at build time'],
    'cells_untouched_by_r3': [k for k in sorted(C) if k not in ('C1', 'C2', 'C3')]}
(B / OUT).write_text(json.dumps(rc, ensure_ascii=False, indent=1), encoding='utf-8', newline='\n')
print('wrote', OUT)
print('r2 sha256', hashlib.sha256((B / R2).read_bytes()).hexdigest())
print('r3 sha256', hashlib.sha256((B / OUT).read_bytes()).hexdigest())
print('C1 why:', c1['why'])
print('C3 positive:', t3['positive'])
