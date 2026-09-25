"""ORD-0301 receipt: eight cells, each `why` computed from that cell's own readings only.

Rule taken from the order and applied without a preset position: an HTTP answer that reached the
browser may not be filed under the network.  Nothing here is typed - statuses, byte counts,
millisecond readings, painted sentences and the two source lines all come out of the artefacts on
disk (table_O0301.json, the door test file, the tip's own source, the state file).
"""
from __future__ import annotations

import json
import pathlib

B = pathlib.Path('D:/moodle/_hjp3_0301_0925')
T = json.loads((B / 'table_O0301.json').read_text(encoding='utf-8'))
STATE = json.loads((B / 'o0301_state.json').read_text(encoding='utf-8'))
DOOR = json.loads((B / 'door_test_8000.json').read_text(encoding='utf-8'))
SRC = pathlib.Path('D:/moodle/_hjp3_0300_0925/snap/frontend/src/features/planning/PlanWithAiSheet.tsx')
ROWS = {r['row'].split('_')[0]: r for r in T['rows']}
D = T['derived']
TIP = T['measured_on']
CFG_DEFAULT = json.loads((B / 'config_default_this_batch.json').read_text(encoding='utf-8'))
ENV = T['captured_envelope']


def src_lines():
    """The two unguarded reads, each named by the function that owns it - so nobody has to guess
    whether line 147 and line 155 are the same helper."""
    lines = SRC.read_text(encoding='utf-8').split(chr(10))
    out = {}
    for n, ln in enumerate(lines, 1):
        if 'body as { detail?: unknown }' in ln:
            owner = next((lines[k].strip() for k in range(n - 1, -1, -1)
                          if lines[k].startswith('function ')), '?')
            out[n] = {'line': ln.strip(), 'inside': owner[:64]}
    return out


def ss(row, *path):
    x = ROWS[row]['screen_side']
    for p in path:
        x = x[p]
    return x


def sv(row, *path):
    x = ROWS[row]['server_side']
    for p in path:
        x = x[p]
    return x


def find_elapsed(key):
    cell = json.loads((B / ('cell_a12_ctl_silent_read_%s.json' % ROWS[key]['run_id']))
                      .read_text(encoding='utf-8'))
    for l in cell.get('no_sheet', {}).get('legs', []):
        if 'experience' in (l.get('url') or ''):
            return l.get('elapsed_ms')
    return None


def brief(key):
    r = ROWS[key]
    return {'row': r['row'], 'run_id': r['run_id'], 'cap_ms': r['cap_ms'],
            'policy_stamp': r['policy_stamp'],
            'declared': r['declared_write_leg'], 'http_status': r['server_side']['http_status'],
            'content_type': r['server_side']['content_type'], 'bytes': r['server_side']['bytes'],
            'elapsed_ms': r['server_side']['elapsed_ms'],
            'client_error': r['server_side']['client_error'],
            'envelope_code': r['server_side']['envelope_code'],
            'answer_attributed_to': r['server_side']['answer_attributed_to'],
            'sibling_probe': r['server_side']['sibling_probe_outside_browser'],
            'origin_own_record': r['server_side']['origin_own_record_for_this_stamp'],
            'painted_first_line': r['screen_side']['painted_first_line'],
            'says_cannot_reach_server': r['screen_side']['says_cannot_reach_server'],
            'details_elements_in_dom': r['screen_side']['details_elements_in_dom'],
            'reason_label': r['screen_side']['reason_label_painted'],
            'reason_value': r['screen_side']['reason_value_painted'],
            'data_result_status': r['screen_side']['data_result_status_cross_check'],
            'verdict': r['verdict'], 'verdict_reason': r['verdict_reason'],
            'syntax_error_count': r['app_threw_on_the_body']['syntax_error_count'],
            'first_rejection_message': r['app_threw_on_the_body']['first_rejection_message'],
            'secondary_surface': r['secondary_surface']}


LINES = src_lines()

CELLS = [
    {'id': 'C1_contentless_500_is_still_relabelled_as_no_connection_on_this_tip',
     'verdict': 'SERVER_ANSWERED_BUT_SCREEN_SAYS_UNREACHABLE_STILL_ON_LANDED_TIP',
     'measured_on': TIP,
     'measured': {'rows': [brief('R1'), brief('R2'), brief('R3'), brief('R4')],
                  'bundle': {'asset': STATE['bundle_facts']['served_asset'],
                             'sha256': STATE['bundle_facts']['served_sha256'],
                             'http_branch_marker_in_served_bytes':
                                 STATE['bundle_facts']['ord0300_http_branch_marker_in_served_bytes']}},
     'why': 'four rows on %s all answered HTTP %s and all four painted %r with data-result-status=%r '
            'and <details> count %s: %s ms / %s B from the product itself under a write lock, %s ms / '
            '%s B and %s ms / %s B from a manufactured answer with the same bytes, and the same card '
            'again with the fetch hook not installed at all'
            % (TIP[:8], sv('R1', 'http_status'), ss('R1', 'painted_first_line'),
               ss('R1', 'data_result_status_cross_check'), ss('R1', 'details_elements_in_dom'),
               sv('R1', 'elapsed_ms'), sv('R1', 'bytes'), sv('R2', 'elapsed_ms'), sv('R2', 'bytes'),
               sv('R3', 'elapsed_ms'), sv('R3', 'bytes'))},

    {'id': 'C2_an_answer_that_carries_a_json_object_is_attributed_to_the_server_at_any_5xx',
     'verdict': 'ANSWER_WITH_A_JSON_OBJECT_IS_QUOTED_AND_ATTRIBUTED_TO_THE_SERVER',
     'measured_on': TIP,
     'measured': {'rows': [brief('R5'), brief('R6'), brief('R7'), brief('R8'), brief('R14')],
                  'captured_envelope': ENV,
                  'equal_to_the_servers_own_sentence': D['envelope_sentence_quoted_verbatim_equals'],
                  'punctuation_drift_equals': D['punctuation_drift_still_equals'],
                  'suffix_drift_equals': D['suffix_drift_still_equals'],
                  'label_on_the_envelope_rows': ss('R5', 'reason_label_painted'),
                  'label_when_the_object_holds_no_sentence': ss('R16', 'reason_label_painted')}},
    {'id': 'C3_the_discriminator_is_the_body_not_the_status_code_and_not_the_clock',
     'verdict': 'DISCRIMINATOR_IS_THE_BODY_SHAPE_NOT_THE_STATUS_NOT_THE_DURATION',
     'measured_on': TIP,
     'measured': {'claims': {k: D[k] for k in
                             ('same_status_different_body_shape_flips_the_verdict',
                              'different_status_same_body_shape_keeps_the_verdict',
                              'duration_is_not_the_discriminator',
                              'null_versus_empty_object_pair_differs',
                              'uninstrumented_reproduction_agrees')},
                  'the_pair': {'both_http_%s' % sv('R15', 'http_status'): {
                      'body': 'null', 'content_type': sv('R15', 'content_type'),
                      'card': ss('R15', 'painted_first_line'), 'verdict': ROWS['R15']['verdict']},
                      'same_but_object': {'body': '{}', 'card': ss('R16', 'painted_first_line'),
                                          'verdict': ROWS['R16']['verdict'],
                                          'label': ss('R16', 'reason_label_painted')}},
                  'statuses_with_the_envelope_body': [sv(k, 'http_status') for k in
                                                      ('R5', 'R6', 'R7', 'R8')]},
     'why': 'the four 5xx rows carrying the %s B envelope (statuses %s) all came out %s while the two '
            'rows whose body is %r or %r came out %s at the same status %s, and a %s ms wait and a '
            '%s ms wait painted the identical card - so what flips the verdict is whether the body '
            'hands the client a JSON object, not the code and not the clock'
            % (ENV['bytes'], '/'.join(str(x) for x in [sv(k, 'http_status') for k in ('R5', 'R6', 'R7', 'R8')]),
               ROWS['R5']['verdict'], 'null', '{}', ROWS['R15']['verdict'], sv('R15', 'http_status'),
               sv('R2', 'elapsed_ms'), sv('R3', 'elapsed_ms'))},
    # why strings must be per cell; C2 carries its own below
    {'id': 'C4_the_relabel_happens_because_the_client_reads_a_property_off_a_null_body',
     'verdict': 'CLIENT_HELPER_THROWS_ON_A_NULL_BODY_AND_THE_CATCH_RELABELS_IT_AS_NETWORK',
     'measured_on': TIP,
     'measured': {'source_lines_on_this_tip': LINES,
                  'source_file': 'frontend/src/features/planning/PlanWithAiSheet.tsx',
                  'rejections_seen_in_the_browser': [
                      {'row': r['row'], 'content_type': r['server_side']['content_type'],
                       'error_message': r['app_threw_on_the_body']['first_rejection_message']}
                      for r in T['rows'] if r['app_threw_on_the_body']['syntax_error_count']],
                  'every_misleads_row_had_no_json_object_for_the_helper':
                      D['every_misleads_row_had_no_json_object_for_the_helper'],
                  'no_honest_answered_row_threw_on_the_body': D['no_honest_answered_row_threw_on_the_body'],
                  'mislead_rows': D['misleads_rows']}},
    {'id': 'C5_the_two_connection_class_outcomes_are_not_the_same_disease',
     'verdict': 'UPSTREAM_ABSENT_VS_RESET_SPLIT_ON_WHO_ANSWERED',
     'measured_on': TIP,
     'measured': {'rows': [brief('R10'), brief('R11')],
                  'face_8565_upstream_port': STATE['ports']['deliberately_empty'],
                  'sibling_probe_says_upstream_listening':
                      (ROWS['R10']['server_side']['sibling_probe_outside_browser'] or {}).get(
                          'upstream_listening'),
                  'who_answered_per_the_probes': [ROWS[k]['server_side']['answer_attributed_to']
                                                  for k in ('R10', 'R11')]}},
    {'id': 'C6_a_silent_leg_still_has_no_client_answer_on_the_write_side_and_a_named_one_on_the_read_side',
     'verdict': 'WRITE_LEG_STILL_UNBOUNDED_READ_LEG_NAMED_AT_THE_12_SECOND_CONSTANT',
     'measured_on': TIP,
     'measured': {'rows': [brief('R12'), brief('R13')],
                 'origin_declared_for_the_write_leg': ROWS['R12']['declared_write_leg'],
                  'write_cap_ms': ROWS['R12']['cap_ms'], 'read_cap_ms': ROWS['R13']['cap_ms'],
                  'read_abort_ms': find_elapsed('R13'),
                  'read_abort_client_error': [l.get('client_error') for l in
                                              (ROWS['R13']['secondary_surface'] or {}).get('page_level_legs', [])],
                  'painted_on_the_read_side': (ROWS['R13']['secondary_surface'] or {})
                  .get('what_the_traveller_was_left_with'),
                  'read_deadline_constant_in_served_bytes':
                      STATE['bundle_facts']['read_deadline_constant_in_served_bytes']}},
    {'id': 'C7_the_named_server_deadline_answer_is_still_not_reachable_on_this_path',
     'verdict': 'NAMED_503_ONLY_REACHABLE_BY_A_CONFIG_THE_SHIPPED_DOOR_REFUSES',
     'measured_on': TIP,
     'measured': {'door_test': {k: DOOR[k] for k in ('env_CITYNEXUS_WRITE_DEADLINE_MS', 'booted', 'exited',
                                                     'exit_rc', 'error_named_in_log')},
                  'in_process_verdict_when_asked': {
                      'busy_timeout_ms': DOOR['in_process_verdict']['busy_timeout_ms'],
                      'default_deadline_ms': DOOR['in_process_verdict']['default_deadline_ms'],
                      'verdict': DOOR['in_process_verdict']['verdict']},
                  'shipped_numbers_read_in_process_this_batch': CFG_DEFAULT,
                  'door_verdict_for_the_default_config': CFG_DEFAULT['verdict']['per_scenario']
                  ['agent.commands']['verdict']}},
    {'id': 'C8_headers_answered_and_the_body_cut_short_leaves_the_traveller_with_no_card_at_all',
     'verdict': 'TRUNCATED_BODY_LEAVES_NO_OUTCOME_CARD_WITHIN_THE_CAP',
     'measured_on': TIP,
     'measured': {'row': brief('R17'), 'declared': ROWS['R17']['declared_write_leg'],
                  'origin_own_record': ROWS['R17']['server_side']['origin_own_record_for_this_stamp'],
                  'cap_ms': ROWS['R17']['cap_ms']}}, 
]

# per-cell why for the cells that did not carry one yet, each quoting only its own readings
CELLS[1]['why'] = ('the same %s B body whose own code is %r was answered as %s, %s, %s and %s and every '
                   'time the screen painted %r with the label %r holding %r verbatim (%s), details count '
                   '%s; the real product rejection of the same day put %r under %r'
                   % (ENV['bytes'], ENV['code'], sv('R5', 'http_status'), sv('R6', 'http_status'),
                      sv('R7', 'http_status'), sv('R8', 'http_status'), ss('R5', 'reason_label_painted'),
                      ss('R5', 'reason_label_painted'), ss('R5', 'reason_value_painted'),
                      D['envelope_sentence_quoted_verbatim_equals'], ss('R5', 'details_elements_in_dom'),
                      ss('R14', 'reason_value_painted'), ss('R14', 'reason_label_painted')))
CELLS[3]['why'] = ('the browser recorded %r rejecting response.json() on rows whose content-type is %s, '
                   'and the tip ships %s: %s - the helper that reads the server sentence touches '
                   '%s without a null guard, so the throw lands in the sheet-wide catch that paints %r '
                   'and every mislead row (%d of them) is one where no JSON object reached that helper'
                   % (CELLS[3]['measured']['rejections_seen_in_the_browser'][0]['error_message'][:64],
                      sv('R1', 'content_type'),
                      ', '.join('%d (%s)' % (n, v['inside'].split('(')[0][:26]) for n, v in sorted(LINES.items(), key=lambda x: int(x[0]))),
                      'line 155 inside serverReasonSentence', '.detail',
                      ss('R1', 'painted_first_line'), len(D['misleads_rows'])))
CELLS[4]['why'] = ('with nothing listening on port %s the vite proxy itself answered %s / %s / %s B and '
                   'the traveller was left on %r which names the server (%s at that surface), while a '
                   'reset upstream produced the same proxy %s answer on the tapped leg and the sheet '
                   'painted %r (%s) - two connection failures, one honest copy and one that is not'
                   % (STATE['ports']['deliberately_empty'],
                      sv('R10', 'http_status'), sv('R10', 'content_type'), sv('R10', 'bytes'),
                      (ROWS['R10']['secondary_surface'] or {})['what_the_traveller_was_left_with'][:40],
                      ROWS['R10']['secondary_surface']['same_rule_applied_to_this_surface'],
                      sv('R11', 'http_status'), ss('R11', 'painted_first_line'), ROWS['R11']['verdict']))
CELLS[5]['why'] = ('the origin record for %s says the POST leg was held with mode %r, and the tapped '
                   'write was still unsettled at the %s ms cap with no outcome card (details %s); the '
                   'same bundle against a silent READ named itself at %s ms in the browser as %r, which '
                   'is the honest shape of the same fact'
                   % (ROWS['R12']['run_id'], (ROWS['R12']['declared_write_leg'] or {}).get('mode'),
                      ROWS['R12']['cap_ms'], ss('R12', 'details_elements_in_dom'),
                      CELLS[5]['measured']['read_abort_ms'],
                      (ROWS['R13']['secondary_surface'] or {})['what_the_traveller_was_left_with'][:56]))
CELLS[6]['why'] = ('booting the shipped backend with CITYNEXUS_WRITE_DEADLINE_MS=%s refused: booted=%s, '
                   'exit_rc=%s, the log names %s, and the in-process verdict for that config is %r with '
                   'busy_timeout=%s against default=%s - so the only way to make the server emit its own '
                   'named 503 is a configuration the startup door itself rejects'
                   % (DOOR['env_CITYNEXUS_WRITE_DEADLINE_MS'], DOOR['booted'], DOOR['exit_rc'],
                      'WriteDeadlineConfigurationError', DOOR['in_process_verdict']['verdict'],
                      DOOR['in_process_verdict']['busy_timeout_ms'],
                      DOOR['in_process_verdict']['default_deadline_ms']))
CELLS[7]['why'] = ('declaring Content-Length %s and writing %s B left the tapped leg with status %s, '
                   'content-type %s, no readable byte count and no rejection, and the screen showed no '
                   'outcome card at all by run %s - the wait has no bound and no named end'
                   % (21, 5, sv('R17', 'http_status'), sv('R17', 'content_type'), ROWS['R17']['run_id']))

receipt = {
    'order': 'ORD-0301', 'lane': 'HJ-P3 aad2d1f2', 'run_id': 'O0301-batch',
    'asked_in': 'ledger 494abfd7 order text 2026-09-25 14:1x (bus comment 5827759480 is my status line)',
    'measured_on': TIP,
    'measured_on_how_read': 'git ls-remote https://github.com/Canshu-King/CityNexus.git '
                            'refs/heads/mirror/integration-frontend-apple-pass1, re-read 2026-09-25T14:09:29+0800',
    'frozen_tip': TIP, 'frozen_at': '2026-09-25T14:09:29+0800',
    'judgment_rule_applied': 'if an HTTP answer reached the browser for the tapped leg, the screen may '
                             'not file the reason under the network; rows are HONEST / MISLEADS / '
                             'NOT_MEASURED by that test only',
    'bundle_under_test': {'built_from': TIP, 'asset': STATE['bundle_facts']['served_asset'],
                          'sha256': STATE['bundle_facts']['served_sha256'],
                          'served_bytes': STATE['bundle_facts']['served_bytes'],
                          'markers': {k: v for k, v in STATE['bundle_facts'].items()
                                      if k.endswith('in_served_bytes') or k.endswith('in_source')}},
    'faces': [{'port': f['port'], 'tag': f['tag'], 'upstream': f['upstream_backend_port']}
              for f in STATE['faces']],
    'table': {'rows': [r['row'] for r in T['rows']], 'derived': D},
    'cells': CELLS,
    'q25': 'every millisecond here was measured in this batch on this tip; none of them is carried over '
           'from ORD-0300 or ORD-0291',
    'instrument_limits_disclosed': [
        'the five outcome classes the order named cannot all be produced by the product on this one '
        'user path: ① and the refused case are real, ②/③ are manufactured from bytes captured off a '
        'real product rejection (envelope_real.json, sha256 %s), and the origin names which leg it '
        'answered in its own log' % ENV['sha256'][:16],
        'the sheet-level verdict for the arms that never reach the sheet is NOT_MEASURED; the page-level '
        'card those travellers were left with is recorded under secondary_surface and judged by the '
        'same rule',
        'the first pass of this batch deleted the origin request log when switching policy (my bug); the '
        'fix was to make it append-only and re-run every arm, so the rows here are from the second pass',
    ],
    'derived_result': None, 'claimed_result': 'MEASURED_NOT_GRADED',
}
(B / 'RECEIPT_O0301-1500.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=1), encoding='utf-8')
print('cells', len(CELLS), '| ids:')
for c in CELLS:
    print(' ', c['id'], '->', c['verdict'], '| why chars', len(c['why']))
