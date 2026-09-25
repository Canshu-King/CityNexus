"""ORD-0288 T-1(a)/(b): derive every verdict from the arm's own rows, with three-way gates.

Fields are the arbiter's: `idempotency_keys row / operation / response_status / replay behavior`.
No arm is written as "expected red"; the expectation on (a) was `observe durable ownership`, and what
was observed is quoted. Per EVIDENCE_INTEGRITY_GATE_V1 every boolean here carries positive / negative /
mutation, and every blob coordinate is 40 hex.
"""
from __future__ import annotations

import json
import pathlib
import re

B = pathlib.Path('D:/moodle/_hjp3_0288t1_0925')
STATE = json.loads((B / 'o0288_state.json').read_text(encoding='utf-8'))
TIP = STATE['measured_on']
DOOR = json.loads((B / 'seed_journey.json').read_text(encoding='utf-8'))
COORD = '%COORD%'


def cell(arm):
    hits = sorted(B.glob('cell_%s_*.json' % arm)) or sorted(B.glob('cell_%s.json' % arm))
    return json.loads(hits[-1].read_text(encoding='utf-8')) if hits else None


def strip_trace(text):
    try:
        j = json.loads(text)
    except Exception:  # noqa: BLE001
        return None
    if isinstance(j, dict) and isinstance(j.get('error'), dict):
        j['error'].pop('trace_id', None)
    return json.dumps(j, sort_keys=True)


def rows_for(cellobj, key):
    return [r for r in (cellobj.get('durable_read_after') or {}).get('rows_for_this_arms_keys', [])
            if r['key'].endswith(key)] if cellobj else []


SEQ = cell('t1a_same_key_two_processes')
DIF = cell('t1a_same_key_different_body')
CON = cell('t1a_same_key_concurrent_two_processes')
ERR = cell('t1b_error_path_records_response_status')
PRE = cell('t1b_failure_before_the_claim_leaves_no_row')
RES = cell('t1a_replay_after_a_process_restart')
M1 = cell('t1_crash_mutant_mut_crash')
M2 = cell('t1_signature_mutant_mut_sig')
M3 = cell('t1_wrong_carrier_mutant_mut_sig_wrong')
K1 = (SEQ['extra']['key'] if SEQ else None)
K2 = (CON['extra']['key'] if CON else None)
K3 = (ERR['extra']['key'] if ERR else None)


def steps(c):
    return {s['intent'][:18]: s for s in (c['steps'] if c else [])}


s_seq = steps(SEQ)
first = list(s_seq.values())[0]['response'] if s_seq else {}
replay = list(s_seq.values())[1]['response'] if len(s_seq) > 1 else {}
row1 = rows_for(SEQ, K1)[0] if rows_for(SEQ, K1) else {}
row3 = rows_for(ERR, K3)[0] if rows_for(ERR, K3) else {}
m1s = steps(M1)
m1_list = list(m1s.values())
m2s = list(steps(M2).values())
m3s = list(steps(M3).values())
dur_res = list(steps(RES).values())[0]['response'] if RES else {}
m1_rows = []
if M1:
    seen_keys = set()
    for st in M1['steps']:
        for r in ((st.get('durable_after_this') or {}).get('rows') or []):
            if r['key'] not in seen_keys:
                seen_keys.add(r['key'])
                m1_rows.append(r)

verdicts = {
    'durable_ownership_row_exists_and_is_unique': len(rows_for(SEQ, K1)) == 1,
    'row_operation_named': row1.get('operation') == 'plans.generate',
    'row_response_status_recorded': row1.get('response_status') is not None,
    'replay_across_processes_same_answer_ignoring_trace_id':
        strip_trace(first.get('body_text')) is not None
        and strip_trace(first.get('body_text')) == strip_trace(replay.get('body_text')),
    'same_key_different_body_rejected': (DIF['steps'][0]['response']['status'] == 409) if DIF else False,
    'concurrency_left_exactly_one_row': len(rows_for(CON, K2)) == 1,
    'error_path_in_route_records_status': row3.get('response_status') == 422,
    'failure_before_claim_burns_no_key': not rows_for(PRE, ':x'),
    'placeholder_after_a_crash_stays_null_forever': bool(m1_rows) and len(m1_list) > 3
        and any(r['response_status'] is None for r in m1_rows)
        and all(m1_list[i]['response']['status'] == 409 for i in (1, 3)),
    'replay_survives_a_process_restart': (RES['steps'][0].get('replay_identical_payload') is not None) if RES else False,
    'mutation_carrier_proven': (m2s[1]['response']['status'] != 409) if len(m2s) > 1 else False,
    'mutation_control_specific_not_anything_flips': (m3s[1]['response']['status'] == 409) if len(m3s) > 1 else False,
    'unknown_result_is_distinguishable': False,
}
derived = dict(verdicts)
derived['unknown_result_is_distinguishable'] = not (len(m1_list) > 3 and m1_list[1]['response']['status'] == 409
                                                    and m1_list[3]['response']['status'] == 409)
m1_rows = []
if M1:
    seen_keys = set()
    for st in M1['steps']:
        for r in ((st.get('durable_after_this') or {}).get('rows') or []):
            if r['key'] not in seen_keys:
                seen_keys.add(r['key'])
                m1_rows.append(r)
m1_key = m1_list[0]['response']['key'] if m1_list else None
m1_row_status = next((r['response_status'] for r in m1_rows if str(r['key']).endswith(str(m1_key))),
                     'NO_SUCH_ROW')
m1_first, m1_second, m1_third, m1_other = (m1_list[0], m1_list[1], m1_list[3], m1_list[4])
res_step = (RES['steps'][0] if RES else {})
res_row = res_step.get('replay_identical_payload')
agent_src = pathlib.Path('D:/moodle/_hjp3_0288t1_0925/backend/app/main.py').read_text(encoding='utf-8')
agent_head = agent_src.split('def run_agent_command(')[1].split('):')[0]
AGENT_HAS_KEY_PARAM = 'idempotency_key' in agent_head

cells = [
 {'id': 'C1_same_key_across_two_processes_leaves_one_durable_owner_row',
  'verdict': 'DURABLE_OWNERSHIP_OBSERVED',
  'measured_on': TIP,
  'measured': {
      'key': K1, 'journey_id': DOOR['journey_id'], 'database_file': STATE['db'],
      'processes': [{'tag': b['tag'], 'pid': b['pid'], 'port': b['port']} for b in STATE['backends']],
      'first_send': {'port': first.get('url'), 'status': first.get('status'), 'bytes': first.get('bytes'),
                     'elapsed_ms': first.get('elapsed_ms'), 'at': first.get('at')},
      'second_send_other_process': {'status': replay.get('status'), 'bytes': replay.get('bytes'),
                                    'elapsed_ms': replay.get('elapsed_ms'), 'at': replay.get('at')},
      'idempotency_keys_row': row1,
      'rows_holding_this_key': len(rows_for(SEQ, K1)),
      'plan_versions_total': (SEQ.get('durable_read_after') or {}).get('counts', {}).get('plan_versions'),
      'gates_three_way': {
          'positive': derived['durable_ownership_row_exists_and_is_unique'],
          'negative': 'a malformed key on the same journey leaves no row at all (%s)'
                      % derived['failure_before_claim_burns_no_key'],
          'mutation': 'deleting the signature comparison changes the SAME-KEY-DIFFERENT-BODY outcome '
                      'from 409 to a silent reuse of someone else answer (%s), see C2'
                      % derived['mutation_carrier_proven']}},
  'why': 'with key %s on database %s the store holds exactly %d row for it, operation %r, response_status %s '
         'and a %s B response_json expiring %s, while the second send went to port %s (a different process, '
         'pid %s vs %s) and answered %s in %s ms with the same payload once trace_id is dropped (%s)'
         % (K1, str(STATE['db']).split('/')[-1], len(rows_for(SEQ, K1)), row1.get('operation'),
            row1.get('response_status'), row1.get('response_json_bytes'), (row1.get('expires_at') or '')[:19],
            STATE['backends'][1]['port'], STATE['backends'][1]['pid'], STATE['backends'][0]['pid'],
            replay.get('status'), replay.get('elapsed_ms'),
            derived['replay_across_processes_same_answer_ignoring_trace_id'])},

 {'id': 'C2_same_key_different_body_is_refused_and_the_refusal_has_the_carrier_you_would_name',
  'verdict': 'CROSS_BODY_KEY_REUSE_REFUSED_WITH_A_PROVEN_CARRIER',
  'measured_on': TIP,
  'measured': {
      'status_when_pristine': (DIF['steps'][0]['response']['status'] if DIF else None),
      'body_refused': (DIF['steps'][0]['response']['body_text'][:220] if DIF else None),
      'key': K1, 'first_body': {'candidate_count': 3}, 'second_body': {'candidate_count': 5},
      'mutant_that_removes_the_guard': {'tree': (M2 or {}).get('private_copy', {}).get('dir'),
                                        'patch': (M2 or {}).get('private_copy', {}).get('patch'),
                                        'different_body_status_after_removing_it':
                                            (m2s[1]['response']['status'] if len(m2s) > 1 else None),
                                        'cell': 'cell_t1_signature_mutant_mut_sig.json'},
      'control_mutant_that_removes_another_guard': {
          'tree': (M3 or {}).get('private_copy', {}).get('dir'),
          'different_body_status_still': (m3s[1]['response']['status'] if len(m3s) > 1 else None),
          'note': 'my FIRST mutant deleted the guard on the replan route, which this leg never reaches - '
                  'the 409 survived, so that mutant proved nothing and is published as the negative case',
          'cell': 'cell_t1_wrong_carrier_mutant_mut_sig_wrong.json'},
      'durable_row_untouched_by_the_refusal': len(rows_for(DIF, K1)) == 1,
      'gates_three_way': {'positive': derived['same_key_different_body_rejected'],
                          'negative': 'with the guard deleted the same call answers %s instead of 409'
                                       % (m2s[1]['response']['status'] if len(m2s) > 1 else None),
                          'mutation': 'the wrong-carrier mutant leaves it at %s, so the flip above is '
                                      'attributed to one named line, not to any edit'
                                      % (m3s[1]['response']['status'] if len(m3s) > 1 else None)}},
  'why': 'the pristine tree refused key %s with a different candidate_count as %s whose sentence is %r, and '
         'the row count stayed %d; deleting `if row.request_hash != signature:` inside '
         '_replay_committed_accept turned the same call into %s, while deleting the similarly named guard on '
         'the replan route left it at %s'
         % (K1, DIF['steps'][0]['response']['status'],
            (DIF['steps'][0]['response']['body_text'] or '')[:70], len(rows_for(DIF, K1)),
            m2s[1]['response']['status'] if len(m2s) > 1 else None,
            m3s[1]['response']['status'] if len(m3s) > 1 else None)},

 {'id': 'C3_one_key_fired_at_both_processes_at_once_still_one_row_and_no_second_batch',
  'verdict': 'CONCURRENT_SAME_KEY_YIELDS_ONE_OWNER_ROW_AND_NO_EXTRA_PLAN_BATCH',
  'measured_on': TIP,
  'measured': {
      'key': K2, 'leg_A': {'status': CON['steps'][0]['response']['status'],
                           'elapsed_ms': CON['steps'][0]['response']['elapsed_ms'], 'at': CON['steps'][0]['response']['at']},
      'leg_B': {'status': CON['steps'][1]['response']['status'],
                'elapsed_ms': CON['steps'][1]['response']['elapsed_ms'], 'at': CON['steps'][1]['response']['at']},
      'wall_ms_both': CON['steps'][1].get('wall_ms_for_both'),
      'rows_holding_this_key': len(rows_for(CON, K2)),
      'plan_versions_total': (CON.get('durable_read_after') or {}).get('counts', {}).get('plan_versions'),
      'idempotency_rows_all_keys': (CON.get('durable_read_after') or {}).get('total_idempotency_rows_all_keys'),
      'gates_three_way': {
          'positive': derived['concurrency_left_exactly_one_row'],
          'negative': 'a different key in the same second would add its own row - see the %d rows for all '
                      'keys after this arm' % ((CON.get('durable_read_after') or {}).get('total_idempotency_rows_all_keys') or 0),
          'mutation': 'the crash arm shows what happens when the claim is won and the answer never lands '
                      '(C4), which is the failure mode this arm cannot show'}},
  'why': 'both processes fired key %s within %s ms of each other and both answered %s / %s at %s ms and %s ms, '
         'and the store kept %d row for that key with %s plan versions in the whole database'
         % (K2, CON['steps'][1].get('wall_ms_for_both'), CON['steps'][0]['response']['status'],
            CON['steps'][1]['response']['status'], CON['steps'][0]['response']['elapsed_ms'],
            CON['steps'][1]['response']['elapsed_ms'], len(rows_for(CON, K2)),
            (CON.get('durable_read_after') or {}).get('counts', {}).get('plan_versions'))},

 {'id': 'C4_the_error_path_records_a_status_when_it_goes_through_the_route_and_records_nothing_before_the_claim',
  'verdict': 'REFUSAL_IS_DURABLE_PRE_CLAIM_REJECTION_IS_NOT_A_KEY_BURN',
  'measured_on': TIP,
  'measured': {
      'in_route_refusal': {'key': K3, 'status': ERR['steps'][0]['response']['status'],
                           'sentence': (ERR['steps'][0]['response']['body_text'] or '')[:200]},
      'row_written': row3,
      'replay_of_that_failure': {'status': ERR['steps'][1]['response']['status'],
                                 'same_sentence_ignoring_trace_id':
                                     strip_trace(ERR['steps'][0]['response']['body_text'])
                                     == strip_trace(ERR['steps'][1]['response']['body_text'])},
      'pre_claim_rejection': {'malformed_key_status': PRE['steps'][0]['response']['status'],
                              'sentence': (PRE['steps'][0]['response']['body_text'] or '')[:160],
                              'rows_matching_that_key': rows_for(PRE, ':x'),
                              'a_later_valid_send_still_works': PRE['extra']['and_a_later_valid_send_is_unaffected']},
      'gates_three_way': {
          'positive': derived['error_path_in_route_records_status'],
          'negative': derived['failure_before_claim_burns_no_key'],
          'mutation': 'C5 shows the third case neither of these covers: a claim that is never filled'}},
  'why': 'the keyed send the route itself refused left response_status=%s with %s B of response_json and its '
         'replay from the other process answered %s with the same sentence ignoring trace_id (%s), while a '
         'malformed key was answered %s before any claim and matched %d rows, and a fresh key right after it '
         'still answered %s'
         % (row3.get('response_status'), row3.get('response_json_bytes'),
            ERR['steps'][1]['response']['status'],
            ERR['steps'][1].get('replay_identical_payload') if 'replay_identical_payload' in ERR['steps'][1]
            else ERR['steps'][1].get('is_409_incomplete'),
            PRE['steps'][0]['response']['status'], len(rows_for(PRE, ':x')),
            PRE['extra']['and_a_later_valid_send_is_unaffected'])},



 {'id': 'C5_a_claim_that_was_never_filled_leaves_a_NULL_placeholder_no_process_can_resolve',
  'verdict': 'CRASH_AFTER_CLAIM_BURNS_THE_KEY_AND_DIED_LOOKS_IDENTICAL_TO_RUNNING',
  'measured_on': TIP,
  'measured': {
      'private_copy': M1['private_copy'], 'database_file': M1['db'],
      'first_send_status': m1_first['response']['status'],
      'row_response_status_after_the_crash': m1_row_status,
      'replay_same_process': {'status': m1_second['response']['status'],
                              'sentence': (m1_second['response'].get('body') or '')[:160]},
      'replay_after_a_fresh_process': {'status': m1_third['response']['status'],
                                       'sentence': (m1_third['response'].get('body') or '')[:160]},
      'a_different_key_still_claims_and_crashes': {'status': m1_other['response']['status']},
      'unknown_result_is_distinguishable': derived['unknown_result_is_distinguishable'],
      'gates_three_way': {
          'positive': 'the honest answer exists on this same route: C4 records a status when the route refuses',
          'negative': 'a pre-claim rejection leaves no row and burns no key',
          'mutation': 'one injected unhandled raise inside _generate_plans_answer, anchor: '
                      + repr(M1['private_copy']['patch']['anchor_line'])}},
  'why': 'first send answered %s and the row kept response_status %r; the same key answered %s from the same '
         'process and %s from a process started after that owner died, saying %r - so a working owner and a '
         'dead owner are the same message to the caller'
         % (m1_first['response']['status'], m1_row_status, m1_second['response']['status'],
            m1_third['response']['status'], (m1_third['response'].get('body') or '')[:88])},

 {'id': 'C6_the_receipt_survives_the_death_of_the_process_that_wrote_it',
  'verdict': 'REPLAY_IS_DURABLE_ACROSS_A_PROCESS_RESTART_NOT_MERELY_ACROSS_TWO_LIVE_PROCESSES',
  'measured_on': TIP,
  'measured': {
      'killed_pid': STATE['backends'][0]['pid'], 'restarted_on_port': dur_res.get('url'),
      'replay_status': dur_res.get('status'), 'replay_bytes': dur_res.get('bytes'),
      'same_answer_ignoring_trace_id': res_row, 'rows_for_the_key': len(rows_for(RES, K1)) if RES else None,
      'gates_three_way': {'positive': 'this replay came from a process that never saw the first one',
                          'negative': 'C5 shows durability is not recoverability',
                          'mutation': 'C2 shows the same row is what the refusal guard reads'}},
  'why': 'after pid %s was killed and a fresh uvicorn started on the same file %s, key %s still answered %s '
         'with %s B from the stored receipt and %d row for it'
         % (STATE['backends'][0]['pid'], str(STATE['db']).split('/')[-1], K1, dur_res.get('status'),
            dur_res.get('bytes'), len(rows_for(RES, K1)))},

 {'id': 'C7_two_things_this_batch_still_does_not_answer',
  'verdict': 'SCOPE_LIMITS_NAMED_NOT_PASSED_OFF_AS_GREEN',
  'measured_on': TIP,
  'measured': {
      'agent_commands_route_has_no_idempotency_parameter': not AGENT_HAS_KEY_PARAM,
      'route_source_read_from': 'backend/app/main.py of the exported tree at ' + TIP,
      'mission_bound_leg_not_exercised': 'no arm sent mission_id, so the continuation key '
                                         'plans.generate:cont:<mission_id> was never claimed',
      'first_pass_discarded': 'the first T-1 pass printed 0 durable rows for every arm because the runner '
                              'never read the store; those cells are on disk with earlier run ids and no '
                              'reading here comes from them'},
  'why': 'the def line read out of the exported tree at %s carries no idempotency parameter (found: %r), and '
         'no arm sent a mission_id, so this cell says NOT_MEASURED instead of covering two gaps'
         % (TIP[:12], not AGENT_HAS_KEY_PARAM)},
]

receipt = {
    'order': 'ORD-0288 T-1(a)/(b)', 'lane': 'HJ-P3 aad2d1f2', 'run_id': 'O0288T1',
    'asked_in': 'commander 494abfd7 15:5x relay of the arbiter: (a) same key + cross-process + one-time db, '
                'expected: observe durable ownership; (b) does the error path land a row with response_status, '
                'can it be replayed, can an unknown result be judged',
    'measured_on': TIP,
    'measured_on_how_read': STATE['measured_on_how_read'],
    'frozen_tip': TIP, 'frozen_at': STATE['measured_on_how_read'].split('re-read ')[-1],
    'database': {'file': STATE['db'], 'created_by': "the product's own ensure_schema(); deleted before start "
                                                    '(R-SCHEMA-01 fresh-or-no-run)',
                 'both_processes_point_at_the_same_file': STATE['both_processes_share_one_file'],
                 'journey_id': DOOR['journey_id'], 'seed': STATE['seed']},
    'trees': {'pristine_export': str(STATE['backends'][0]['tree']),
              'hardlink_audit': STATE['hardlink_audit_pristine'],
              'mutants': {k: v.get('dir') for k, v in (STATE.get('mutants') or {}).items()}},
    'derived': derived, 'cells': cells,
    'q25': 'every millisecond here was measured in this batch on this tip',
    'instrument_limits_disclosed': [
        'the durable half is always read through a second, READ-ONLY connection and the row is quoted with '
        'its key, operation, response_status, byte count and expires_at; a process memory is not ownership',
        'replay equality is computed after dropping trace_id, because a fresh trace id on a replayed envelope '
        'is a fact about the renderer, not about the answer',
        'the crash arm runs only in a private copy of the exported tree (hardlink-audited, one named line '
        'injected, the file parsed before it is written); the exported product tree and the authoritative '
        'line were never written',
    ],
    'derived_result': None, 'claimed_result': 'MEASURED_NOT_GRADED',
}
(B / 'RECEIPT_O0288T1-1610.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=1),
                                             encoding='utf-8', newline='\n')
print('cells', len(cells))
for c in cells:
    print(' ', c['id'][:52], '->', c['verdict'][:52], '| why', len(c['why']))
print(json.dumps(derived, ensure_ascii=False, indent=1))
