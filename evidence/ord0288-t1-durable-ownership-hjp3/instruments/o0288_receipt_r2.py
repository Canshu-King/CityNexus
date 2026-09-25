"""ORD-0288 T-1 receipt r2 - five things I found wrong in my own r1 before shipping it.

r1 (RECEIPT_O0288T1-1610.json) stays on disk byte-for-byte; this writes
RECEIPT_O0288T1-1610_r2.json and records was/now per field. Every `now` is recomputed here from the
arm cell files - no literal verdicts, no value carried over by hand.

Corrections:
 1. r1's derived `replay_survives_a_process_restart` was `(... .get('replay_identical_payload') is not
    None)` - true whenever the field existed, even when its value was False. Vacuous gate.
 2. r1's C6 field `same_answer_ignoring_trace_id` was filled from the RAW-TEXT comparison, which does
    not ignore trace_id. The name asserted less than it computed.
 3. r1's C4 `why` quoted `replay_identical_payload` (False) while the same cell's measured flag
    `same_sentence_ignoring_trace_id` said True - the sentence contradicted its own reading.
 4. r1 carried main.py digests truncated to 16 hex (mutant_arms.json). Under
    EVIDENCE_INTEGRITY_GATE_V1 coordinates go out full length; recomputed from the files on disk.
 5. r1 never said plainly that every keyed send in this batch answered 422 and the database holds 0
    plan_versions - so the durable ownership observed is a durable REFUSAL receipt, not a plan.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import re

B = pathlib.Path('D:/moodle/_hjp3_0288t1_0925')
R1 = 'RECEIPT_O0288T1-1610.json'
OUT = 'RECEIPT_O0288T1-1610_r2.json'
STATE = json.loads((B / 'o0288_state.json').read_text(encoding='utf-8'))
MUT = json.loads((B / 'mutant_arms.json').read_text(encoding='utf-8'))
rc = json.loads((B / R1).read_text(encoding='utf-8'))


def cell(arm):
    hits = sorted(B.glob('cell_%s_*.json' % arm)) or sorted(B.glob('cell_%s.json' % arm))
    return json.loads(hits[-1].read_text(encoding='utf-8')) if hits else None


def rows_for(cellobj, key):
    if not cellobj:
        return []
    return [r for r in (cellobj.get('durable_read_after') or {}).get('rows_for_this_arms_keys', [])
            if r['key'].endswith(key)]


def canonical(text):
    """json value with error.trace_id dropped and keys sorted - the comparison that ignores trace_id."""
    if text is None:
        return None
    try:
        j = json.loads(text)
    except Exception:  # noqa: BLE001
        return None
    if isinstance(j, dict) and isinstance(j.get('error'), dict):
        j['error'].pop('trace_id', None)
    return json.dumps(j, sort_keys=True)


def masked(text):
    """raw text with only the trace_id VALUES blanked - ordering and fields stay visible."""
    if text is None:
        return None
    return re.sub(r'"trace_id":\s*"[0-9a-fA-F-]+"', '"trace_id":"X"', text)


def compare(body_a, body_b):
    """The three readings a replay-equality claim can mean, computed side by side."""
    da = json.loads(body_a)['error'] if body_a else {}
    db = json.loads(body_b)['error'] if body_b else {}
    return {
        'raw_bytes_equal': body_a == body_b,
        'equal_after_blanking_only_trace_id_values': masked(body_a) == masked(body_b),
        'json_values_equal_after_dropping_trace_id': canonical(body_a) is not None
        and canonical(body_a) == canonical(body_b),
        'details_key_insertion_order_differs': list((da or {}).get('details', {}).keys())
        != list((db or {}).get('details', {}).keys()),
        'a_bytes': len(body_a or ''), 'b_bytes': len(body_b or ''),
        'method': 'both bodies read from the arm cell on disk; canonical() drops error.trace_id and '
                  'sorts keys, masked() only blanks trace_id values, raw compares the bytes as sent',
    }


SEQ = cell('t1a_same_key_two_processes')
DIF = cell('t1a_same_key_different_body')
CON = cell('t1a_same_key_concurrent_two_processes')
ERR = cell('t1b_error_path_records_response_status')
PRE = cell('t1b_failure_before_the_claim_leaves_no_row')
RES = cell('t1a_replay_after_a_process_restart')
K1 = SEQ['extra']['key']
K2 = CON['extra']['key']
K3 = ERR['extra']['key']

seq_first_body = SEQ['steps'][0]['response']['body_text']
seq_replay_body = SEQ['steps'][1]['response']['body_text']
res_body = RES['steps'][0]['response']['body_text']
err_first_body = ERR['steps'][0]['response']['body_text']
err_replay_body = ERR['steps'][1]['response']['body_text']

cmp_restart = compare(seq_first_body, res_body)
cmp_crossproc = compare(seq_first_body, seq_replay_body)
cmp_err = compare(err_first_body, err_replay_body)

res_rows = rows_for(RES, K1)
res_status = RES['steps'][0]['response']['status']
seq_status = SEQ['steps'][0]['response']['status']

# ---------------------------------------------------- 1. de-vacuate the restart predicate
restart_now = {
    'restarted_process_pid': RES['extra']['new_process']['pid'],
    'killed_process_pid': STATE['backends'][0]['pid'],
    'rows_holding_the_key_after_the_restart': len(res_rows),
    'status_from_the_fresh_process': res_status,
    'status_from_the_original_process': seq_status,
    'derived_replay_survives_a_process_restart': bool(
        len(res_rows) == 1 and res_status == seq_status
        and cmp_restart['json_values_equal_after_dropping_trace_id']),
}

# ---------------------------------------------------- 5. what this batch's sends actually were
main_db_arms = {'same_key_two_processes': SEQ, 'same_key_different_body': DIF,
                'concurrent_two_processes': CON, 'error_path_records_response_status': ERR,
                'failure_before_the_claim_leaves_no_row': PRE,
                'replay_after_a_process_restart': RES}
statuses = {}
for arm, c in main_db_arms.items():
    if not c:
        continue
    for st in c['steps']:
        statuses.setdefault(str(st['response']['status']), []).append(arm)
plan_version_counts = {}
for arm, c in main_db_arms.items():
    cnt = ((c or {}).get('durable_read_after') or {}).get('counts', {}).get('plan_versions')
    if cnt is not None:
        plan_version_counts[arm] = cnt

outcome_now = {
    'statuses_seen_on_the_shared_database': {k: sorted(set(v)) for k, v in sorted(statuses.items())},
    'send_count_per_status': {k: len(v) for k, v in sorted(statuses.items())},
    'plan_versions_rows_per_arm_durable_read': plan_version_counts,
    'every_keyed_send_answered_422_or_409': set(statuses) <= {'422', '409'},
    'not_one_plan_version_row_in_the_database_after_these_arms': all(v == 0 for v in plan_version_counts.values())
    and bool(plan_version_counts),
    'what_that_means': 'the durable ownership this receipt proves is ownership of a REFUSAL receipt '
                       '(422 "No feasible plan candidates satisfy the journey constraints"); a replay '
                       'of a 200-with-plans receipt was never exercised in this batch',
}

# ---------------------------------------------------- 4. full-length digests, recomputed from disk
digests = {'pristine_export_backend_app_main_py':
           hashlib.sha256((B / 'backend' / 'app' / 'main.py').read_bytes()).hexdigest()}
for entry in MUT:
    tree = pathlib.Path(entry['private_copy']['dir'])
    rel = entry['private_copy']['only_file_changed'][0]
    p = tree / pathlib.Path(rel.replace('\\', '/'))
    digests[tree.name + '_' + rel] = {
        'path': str(p), 'sha256_64_hex': hashlib.sha256(p.read_bytes()).hexdigest(),
        'r1_value_was': entry['private_copy']['main_py_sha256'],
        'r1_value_is_a_prefix_of_this': hashlib.sha256(p.read_bytes()).hexdigest().startswith(
            entry['private_copy']['main_py_sha256']),
    }
digests['pristine_export_backend_app_main_py_matches_r1_prefix'] = digests[
    'pristine_export_backend_app_main_py'].startswith(
    MUT[0]['private_copy']['pristine_main_py_sha256'])

# ---------------------------------------------------- apply to a copy of r1
cells = {c['id'][:2]: c for c in rc['cells']}
for c in rc['cells']:
    if c['id'].startswith('C4'):
        c['measured']['replay_of_that_failure'] = {
            'status': ERR['steps'][1]['response']['status'],
            'json_values_equal_after_dropping_trace_id':
                cmp_err['json_values_equal_after_dropping_trace_id'],
            'raw_bytes_equal': cmp_err['raw_bytes_equal'],
            'equality_reading_used_for_the_claim': 'json_values_equal_after_dropping_trace_id',
            'comparison_detail': cmp_err}
        c['why'] = ('the keyed send the route itself refused left response_status=%s with %s B of '
                    'response_json, and its replay from the other process answered %s with the same '
                    'JSON once error.trace_id is dropped (%s) - though the raw bytes are NOT equal '
                    '(%s), because error.details carries the same fields in a different insertion order '
                    '(%s); a malformed key was answered %s before any claim and matched %d rows, and a '
                    'fresh key right after it still answered %s'
                    % (c['measured']['row_written'].get('response_status'),
                       c['measured']['row_written'].get('response_json_bytes'),
                       ERR['steps'][1]['response']['status'],
                       cmp_err['json_values_equal_after_dropping_trace_id'],
                       cmp_err['raw_bytes_equal'], cmp_err['details_key_insertion_order_differs'],
                       PRE['steps'][0]['response']['status'],
                       len(rows_for(PRE, ':x')),
                       PRE['extra']['and_a_later_valid_send_is_unaffected']))
    if c['id'].startswith('C6'):
        c['measured'].pop('same_answer_ignoring_trace_id', None)
        c['measured'].update({
            'replay_from_the_fresh_process': res_status,
            'replay_bytes': RES['steps'][0]['response']['bytes'],
            'rows_holding_this_key_after_the_restart': len(res_rows),
            'three_ways_of_saying_the_same_answer': cmp_restart,
            'equality_reading_used_for_the_claim': 'json_values_equal_after_dropping_trace_id'})
        c['why'] = ('after pid %s was killed and a fresh uvicorn (pid %s) started on the same file %s, '
                    'key %s still answered %s with %s B and %d row in idempotency_keys; that replay is '
                    'the same JSON as the original answer once error.trace_id is dropped (%s), but its '
                    'raw bytes are not equal (%s) - error.details re-serialises with a different key '
                    'insertion order (%s), so the equality claim is stated at the JSON-value level and '
                    'not as "the same bytes"'
                    % (STATE['backends'][0]['pid'], RES['extra']['new_process']['pid'],
                       str(STATE['db']).split('/')[-1], K1, res_status,
                       RES['steps'][0]['response']['bytes'], len(res_rows),
                       cmp_restart['json_values_equal_after_dropping_trace_id'],
                       cmp_restart['raw_bytes_equal'],
                       cmp_restart['details_key_insertion_order_differs']))
    if c['id'].startswith('C7'):
        c['measured']['only_refusal_receipts_were_ever_replayed'] = {
            'every_keyed_send_answered_422_or_409': outcome_now['every_keyed_send_answered_422_or_409'],
            'plan_versions_rows': outcome_now['plan_versions_rows_per_arm_durable_read'],
            'reading': 'no arm in this batch reached a 200, so a stored 200 receipt replay is NOT measured here'}

rc['derived']['replay_survives_a_process_restart'] = restart_now[
    'derived_replay_survives_a_process_restart']
rc['derived']['replay_is_identical_bytes_across_the_restart'] = cmp_restart['raw_bytes_equal']
rc['derived']['replay_across_processes_same_answer_ignoring_trace_id'] = \
    cmp_crossproc['json_values_equal_after_dropping_trace_id']
rc['derived'].update({k: v for k, v in outcome_now.items() if isinstance(v, bool)})

rc['r2_notes'] = {
    'cross_process_three_ways': cmp_crossproc,
    'error_path_three_ways': cmp_err,
    'restart_three_ways': cmp_restart,
    'restart_predicate_inputs': restart_now,
    'batch_outcome': outcome_now,
    'full_length_digests': digests,
    'cell_ids_r1_still_holds': [c['id'][:2] for c in cells.values()],
}
rc['r1_diff'] = [
    {'field': "derived['replay_survives_a_process_restart']",
     'was': 'r1 computed it as `(RES[steps][0].get("replay_identical_payload") is not None)`, i.e. true '
            'whenever the field existed - it was True while that very field read False',
     'now': restart_now['derived_replay_survives_a_process_restart'],
     'derived_from': 'cell_t1a_replay_after_a_process_restart_*.json + the durable row count and the '
                     'JSON-value equality recomputed here'},
    {'field': "C6.measured['same_answer_ignoring_trace_id']",
     'was': "filled from the raw-text comparison (value False) under a name that promised trace_id was ignored",
     'now': {'raw_bytes_equal': cmp_restart['raw_bytes_equal'],
             'json_values_equal_after_dropping_trace_id':
                 cmp_restart['json_values_equal_after_dropping_trace_id'],
             'equal_after_blanking_only_trace_id_values':
                 cmp_restart['equal_after_blanking_only_trace_id_values']},
     'derived_from': 'both response bodies as stored in the arm cells'},
    {'field': "C4.why['...answered 422 with the same sentence ignoring trace_id']",
     'was': 'quoted replay_identical_payload (False), contradicting the same cell\'s measured flag (True)',
     'now': 'quotes json_values_equal_after_dropping_trace_id (%s) and discloses raw_bytes_equal (%s)'
            % (cmp_err['json_values_equal_after_dropping_trace_id'], cmp_err['raw_bytes_equal']),
     'derived_from': 'cell_t1b_error_path_records_response_status_*.json bodies'},
    {'field': "C5.measured['private_copy']['main_py_sha256'] and mutants in trees",
     'was': '16 hex characters (a display truncation carried into a machine field)',
     'now': {k: (v['sha256_64_hex'] if isinstance(v, dict) else v) for k, v in digests.items()},
     'derived_from': 'sha256 recomputed from the files on disk; every r1 short value is a prefix of the '
                     'full value here (%s)' % digests['pristine_export_backend_app_main_py_matches_r1_prefix']},
    {'field': 'the batch never said what its sends actually were',
     'was': 'absent from r1',
     'now': outcome_now['what_that_means'],
     'derived_from': 'statuses and plan_versions counts recomputed from all six main-database arm cells'},
]
rc['receipt_r2_of'] = {'file': R1,
                       'sha256': hashlib.sha256((B / R1).read_bytes()).hexdigest(),
                       'r1_left_untouched_on_disk': True}
(B / OUT).write_text(json.dumps(rc, ensure_ascii=False, indent=1), encoding='utf-8', newline='\n')
print('wrote', OUT)
print('restart predicate now:', restart_now['derived_replay_survives_a_process_restart'])
print('cross-process:', json.dumps({k: v for k, v in cmp_crossproc.items() if k != 'method'},
                                   ensure_ascii=False))
print('restart:', json.dumps({k: v for k, v in cmp_restart.items() if k != 'method'}, ensure_ascii=False))
print('error path:', json.dumps({k: v for k, v in cmp_err.items() if k != 'method'}, ensure_ascii=False))
print('outcome:', json.dumps(outcome_now['statuses_seen_on_the_shared_database'], ensure_ascii=False),
      '| sends per status', json.dumps(outcome_now['send_count_per_status'], ensure_ascii=False))
print('all 422/409:', outcome_now['every_keyed_send_answered_422_or_409'],
      '| 0 plan_versions:', outcome_now['not_one_plan_version_row_in_the_database_after_these_arms'])
print('digests:', json.dumps({k: (str(v)[:20] + '...' if isinstance(v, str) else v)
                              for k, v in digests.items()}, ensure_ascii=False))
raise SystemExit(0)
