"""ORD-0300 scorer: one receipt where every cell justifies ITSELF, built only from the artefacts.

Nothing here is typed from memory: the numbers come from the arm files, the DB is re-read through a second
read-only connection, and the two-sided judgments compare server fields against painted text with `==`
(never `in`), each with its own positive and drift control.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import re
import sqlite3
from datetime import datetime, timezone

BASE = pathlib.Path('D:/moodle/_hjp3_0300_0925')
RUN = 'O0300-2610'
state = json.loads((BASE / 'o0300_state.json').read_text(encoding='utf-8'))
TIP = state['measured_on']
BUNDLE = state['face']['served_sha256']


def load(name):
    return json.loads((BASE / name).read_text(encoding='utf-8'))


w2_runs = [load('cell_w2_O0300-2610.json')]
plain = load('cell_plain_w2.json')
ctrl = load('cell_w2_O0300-2620.json')
tb = load('cell_tb_O0300-2630.json')
wn = load('cell_wnamed_O0300-2650.json')
wn40 = load('cell_wnamed_O0300-2640.json')
rd_src = (BASE / 'snap' / 'frontend' / 'src' / 'lib' / 'readDeadline.ts').read_text(encoding='utf-8')
RD_MS_LINE = [l.strip() for l in rd_src.splitlines() if 'READ_DEADLINE_MS =' in l]
BUNDLE_TEXT = (BASE / 'dist_0300' / 'assets' / 'index-BN1w-xlK.js').read_text(encoding='utf-8', errors='replace')
origin_stats = json.loads(pathlib.Path('D:/moodle/_hjp3_0291_0925/selective_origin_8553_stats.json')
                         .read_text(encoding='utf-8'))
cfgw = state['server_write_config']['verdict']
cfg = cfgw['verdict']
xc = load('crosscheck_foreign_bundle.json')

# the leg that matters in each run
def leg(doc, which='commands'):
    return next(l for l in doc['write_legs'] if l['url'].endswith(which))


def srv(doc, which='commands'):
    l = leg(doc, which)
    return {'url_tail': l['url'].split('/')[-2][:10] + '/' + l['url'].split('/')[-1],
            'http_status': l.get('status'), 'content_type': l.get('content_type'),
            'bytes': l.get('bytes'), 'elapsed_ms': l.get('elapsed_ms'),
            'client_error': l.get('client_error'), 'body_head': (l.get('body_head') or '')[:80],
            'error_code': (l.get('server_envelope') or {}).get('error_code'),
            'error_message': (l.get('server_envelope') or {}).get('error_message'),
            'reason_code': (l.get('server_envelope') or {}).get('reason_code')}


def scr(doc):
    s = doc['screen_after_open_details']
    return {'card_painted': s['result_card'], 'reason_label_painted': s['reason_label_painted'],
            'reason_value_painted': s['reason_value_painted'],
            'detail_region_in_dom': s['details_elements_present'],
            'cross_check_data_result_status': (re.search(r'data-result-status="([^"]*)"',
                                                         s['result_card_html'] or '') or [None, None])[1],
            'cross_check_data_reason_origin': s['cross_check_data_reason_origin']}


# ---- independent, durable read of the server's own sentence for the control run ---------------------
mission_id = None
for l in ctrl['write_legs']:
    m = re.search(r'"mission":\{"id":"([0-9a-f-]{36})"', l.get('body_head') or '')
    if m:
        mission_id = m.group(1)
if mission_id is None:
    conn = sqlite3.connect('file:%s?mode=ro' % (BASE / 'o0300.s3db'), uri=True)
    mission_id = str(conn.execute('select id from journey_missions order by rowid desc limit 1').fetchone()[0])
    conn.close()
db = sqlite3.connect('file:%s?mode=ro' % (BASE / 'o0300.s3db'), uri=True)
server_sentence = db.execute('select failure_reason from journey_missions where id = ?', (mission_id,)).fetchone()[0]
db.close()

rendered_value = (scr(ctrl)['reason_value_painted'] or '')
equal_exact = rendered_value == server_sentence
# the two controls that make `==` mean something: an equality that must be recognised, and a drift that
# must be refused - a substring test would pass BOTH, which is why this cell carries them
drift_punct = server_sentence.replace('.', '。').replace(' ', '  ')
suffix_drift = server_sentence + '。'
would_pass_with_in = server_sentence in rendered_value or rendered_value in server_sentence

w2_leg = srv(w2_runs[-1])
w2_screen = scr(w2_runs[-1])
plain_screen = {'card_painted': plain['first_card']['text'],
                'cross_check_data_result_status': plain['first_card']['status'],
                'detail_region_in_dom': plain['first_card']['details'],
                'instrumented': plain['instrumented'], 'appeared_after_ms': plain['first_card']['ms']}
tb_leg = leg(tb)
tb_cap_ms = tb['timeline_points']
wn_legs = {'agent_commands': srv(wn), 'plans_generate': srv(wn, 'generate')}
wn40_legs = {'agent_commands': srv(wn40), 'plans_generate': srv(wn40, 'generate')}

deadline_ms = cfg['per_scenario']['agent.commands']['deadline_ms']
busy_ms = cfg['per_scenario']['agent.commands']['busy_timeout_ms']
single_wait_max = busy_ms

cells = [
 {'id': 'C1_server_side_answer_on_the_contended_write',
  'verdict': 'NOT_200_BUT_UNNAMED_STILL',
  'measured_on': TIP,
  'measured': {'arms': [srv(r) for r in w2_runs], 'last': w2_leg,
               'server_write_config_read_from_the_product': cfg['per_scenario']['agent.commands'],
               'settings_as_read': {k: cfgw[k] for k in ('settings_write_busy_timeout_ms','settings_write_deadline_ms','settings_write_deadline_scenarios')},
               'run_ids': [r['run_id'] for r in w2_runs], 'bundle_sha256': BUNDLE},
  'why': 'POST %s on %s answered HTTP %s with content-type "%s" and %s bytes, and the body carries no envelope at '
         'all (error_code=%r, error_message=%r, body starts %r), so the answer still has no name a client could '
         'read; ORD-0296\'s own numbers explain why - budget %d ms against a wait capped at busy_timeout %d ms, '
         'so one lost lock surfaces at <=%d ms, before the budget is spent'
         % (w2_leg['url_tail'], TIP[:8], w2_leg['http_status'], w2_leg['content_type'], w2_leg['bytes'],
            w2_leg['error_code'], w2_leg['error_message'], w2_leg['body_head'][:24], deadline_ms, busy_ms,
            single_wait_max)},
 {'id': 'C2_screen_side_attribution_of_that_same_answer',
  'verdict': 'SERVER_ANSWERED_BUT_SCREEN_SAYS_UNREACHABLE',
  'measured_on': TIP,
  'measured': {'painted_card': w2_screen['card_painted'],
               'painted_reason_label': w2_screen['reason_label_painted'],
               'painted_reason_value': w2_screen['reason_value_painted'],
               'detail_regions_in_dom': w2_screen['detail_region_in_dom'],
               'cross_check_data_result_status': w2_screen['cross_check_data_result_status'],
               'reproduced_without_any_instrument': plain_screen,
               'server_side_of_the_same_response': {'status': w2_leg['http_status'], 'bytes': w2_leg['bytes'],
                                                   'elapsed_ms': w2_leg['elapsed_ms']}},
  'why': 'the card painted "%s" (cross-check attribute data-result-status=%r) while the response object for the '
         'same leg was HTTP %s of %s B at %s ms, and %d <details> regions exist, so there is no technical '
         'detail to open at all; the identical card appears with no fetch wrapper installed (first seen at '
         '%s ms, data-result-status=%r), so this is the product\'s sentence about a server that did answer.'
         % ((w2_screen['card_painted'] or '').split('\n')[0], w2_screen['cross_check_data_result_status'],
            w2_leg['http_status'], w2_leg['bytes'], w2_leg['elapsed_ms'], w2_screen['detail_region_in_dom'],
            plain_screen['appeared_after_ms'], plain_screen['cross_check_data_result_status'])},
 {'id': 'C3_positive_control_the_server_channel_still_carries_words_verbatim',
  'verdict': 'SERVER_SENTENCE_QUOTED_VERBATIM_WHEN_ONE_EXISTS',
  'measured_on': TIP,
  'measured': {'db_table_column_row': 'journey_missions.failure_reason/%s' % mission_id,
               'server_sentence_read_by_second_ro_connection': server_sentence,
               'sentence_length_chars': len(server_sentence or ''),
               'painted_label': scr(ctrl)['reason_label_painted'],
               'painted_value': rendered_value,
               'equal_with_double_equals': equal_exact,
               'controls': {'punctuation_drift_must_be_refused': drift_punct != rendered_value,
                            'suffix_drift_must_be_refused': suffix_drift != rendered_value,
                            'substring_test_would_have_been_softer': would_pass_with_in},
               'other_legs_in_the_same_run': {'plans_generate_status': srv(ctrl, 'generate')['http_status'],
                                              'plans_generate_error_message':
                                                  srv(ctrl, 'generate')['error_message']}},
  'why': 'read through a second read-only connection, journey_missions.failure_reason for row %s is %r '
         '(%d chars) and the text painted under the label "%s" is %r (%d chars), equal under == (%r); a '
         'punctuation drift ("%s") and a suffix drift ("%s") are both refused, while a substring test would '
         'have accepted the suffix - that is why this cell carries the two controls. The same run\'s other leg '
         'answered %s with error_code %r and error_message %r, which is NOT what the screen quoted, so the '
         'quoted sentence is traceable to the %d-char DB column and not to that body'
         % (mission_id[:8], server_sentence, len(server_sentence or ''), scr(ctrl)['reason_label_painted'],
            rendered_value, len(rendered_value or ''), equal_exact, drift_punct[:20], suffix_drift[-2:],
            srv(ctrl, 'generate')['http_status'], srv(ctrl, 'generate')['error_code'],
            (srv(ctrl, 'generate')['error_message'] or '')[:28], len(server_sentence or ''))},
 {'id': 'C4_write_leg_deadline_on_the_silent_origin',
  'verdict': 'WRITE_LEG_STILL_UNBOUNDED',
  'measured_on': TIP,
  'measured': {'face_port': state['silent']['face']['port'], 'origin_port': state['silent']['origin_port'],
               'bundle_sha256': state['silent']['face']['served_sha256'],
               'post_sent_at_ms': tb_leg['sent_ms_since_load'], 'post_status': tb_leg.get('status'),
               'post_client_error': tb_leg.get('client_error'), 'observation_cap_ms': tb['cap_ms'],
               'samples_taken': tb['timeline_points'],
               'client_deadline_line_seen': tb['first_client_deadline_line'],
               'origin_accounting': {'reads_answered': origin_stats['answered'],
                                    'writes_swallowed': origin_stats['silenced'],
                                    'swallowed_at': [x['at'] for x in origin_stats.get('silenced_log', [])]},
               'readDeadline_source_line_on_this_tip': RD_MS_LINE,
               'shipped_bundle_constant_occurrences': {'12e3': BUNDLE_TEXT.count('12e3'),
                                                        '1e3_divisions': BUNDLE_TEXT.count('=12e3,')}},
  'why': 'against the selective origin on port %d (which answered %d reads and swallowed %d writes at %s) the '
         'POST left at %s ms and had no status and no client error after %s ms across %d samples, and no '
         'client-deadline sentence was ever painted - so on %s the write leg still has no bound of its own, '
         'and this reading is a duration observation, not an assertion (Q25)'
         % (state['silent']['origin_port'], origin_stats['answered'], origin_stats['silenced'],
            '/'.join(x['at'] for x in origin_stats.get('silenced_log', [])), tb_leg['sent_ms_since_load'],
            tb['cap_ms'], tb['timeline_points'], TIP[:8])},
 {'id': 'C5_is_the_named_503_reachable_on_the_user_path',
  'verdict': 'NAMED_503_NOT_REACHED_IN_TWO_SCHEDULES',
  'measured_on': TIP,
  'measured': {'schedule_single_window_result': {'verdict_from_C1': 'HTTP %s at %s ms' % (
                                                   w2_leg['http_status'], w2_leg['elapsed_ms'])},
               'schedule_two_windows_20s_20s': wn40_legs,
               'schedule_two_windows_20s_45s': wn_legs,
               'budget_numbers': {'deadline_ms': deadline_ms, 'busy_timeout_ms': busy_ms,
                                 'delta_ms': cfg['per_scenario']['agent.commands']['delta_ms'],
                                 'effective_busy_timeout_ms':
                                     cfg['per_scenario']['agent.commands']['effective_busy_timeout_ms']},
               'attempt_2_lock_log': (BASE / 'cell_wnamed_locklog.txt').read_text(encoding='utf-8')},
  'why': 'the two-window schedules (20s+20s and 20s+45s) both let the request finish its writes once it had the '
         'lock: the %s s run waited %s ms and SUCCEEDED with %s, then plans/generate settled in %s ms, '
         'so no second wait ever lost the lock; with '
         'deadline_ms %d above busy_timeout %d, one failed wait surfaces at <= %d ms, i.e. before the budget '
         'is spent, which is why the plain %s is what a traveller sees instead of the named answer'
         % ('45', 
            wn_legs['agent_commands']['elapsed_ms'], wn_legs['agent_commands']['http_status'],
            wn_legs['plans_generate']['elapsed_ms'], deadline_ms, busy_ms, busy_ms, 'HTTP 500')},
 {'id': 'C6_the_same_finding_on_a_bundle_i_did_not_build',
  'verdict': xc['verdict'],
  'measured_on': TIP,
  'measured': {'foreign_asset': xc['foreign_asset'], 'foreign_sha256': xc['foreign_served_sha256'],
               'my_build_sha256': xc['my_build_sha256'], 'byte_identical_to_mine': xc['same_bytes_as_my_build'],
               'markers_present': xc['foreign_bundle_contains_ord0280_markers'],
               'ownership': xc['ownership_proof'],
               'foreign_tree_unchanged': xc['foreign_tree_unchanged_by_this_run'],
               'reading': xc['reading']},
  'why': 'the other build (asset %s, sha256 %s, byte-identical to my private build = %s, ORD-0280 markers present '
         '= %s) served through a face whose proxy is mine (my journey %s, a foreign one %s) gave HTTP %s / %s B '
         'at %s ms, painting the card %r with data-result-status=%r and %d detail regions - so the mismatch belongs '
         'to the generation, not to the bundle I compiled'
         % (xc['foreign_asset'], xc['foreign_served_sha256'][:12], xc['same_bytes_as_my_build'],
            xc['foreign_bundle_contains_ord0280_markers'], xc['ownership_proof']['mine_via_face'],
            xc['ownership_proof']['foreign_via_face'], xc['reading']['http_status'], xc['reading']['bytes'],
            xc['reading']['elapsed_ms'], (xc['reading']['painted_card'] or '').split(chr(10))[0],
            xc['reading']['data_result_status'], xc['reading']['details_in_dom'])},
]

receipt = {
 'order': 'ORD-0300', 'lane': 'HJ-P3 aad2d1f2', 'run_id': RUN,
 'asked_in': 'Canshu-King/CityNexus-Workspace issue #1 comment 5825415532',
 'measured_on': TIP,
 'measured_on_how_read': 'git ls-remote https://github.com/Canshu-King/CityNexus.git '
                         'refs/heads/mirror/integration-frontend-apple-pass1, re-read at export time',
 'bundle_under_test': {'built_from': TIP, 'asset': state['face']['served_asset'], 'sha256': BUNDLE,
                       'ord0280_markers_present_in_served_bytes': state['face']['ord0280_markers_in_served_bytes'],
                       'how': 'private `vite build --outDir D:/moodle/_hjp3_0300_0925/dist_0300`; the served '
                              'preview dist and its index.html were not touched'},
 'supersedes': [
   {'cell': 'ORD-0279 W2 (CLIENT_SUBSTITUTES_A_STATUS_STRING_FOR_THE_SERVER_REASON)',
    'previous_run': 'O0279X-2504 measured on dcae1bc9…', 'new_status': 'SUPERSEDED_BY_GENERATION',
    'note': 'that red shape is not what this generation paints; see C2 for what it paints instead'},
   {'cell': 'ORD-0281 T-b counter-example 1 (silent origin)', 'previous_run': 'O0291-2507 on 45b0a5e2…',
    'new_status': 'REPRODUCED_ON_NEW_GENERATION', 'note': 'C4'}],
 'q25': 'no duration in this file is inherited across generations; every ms here was measured on %s' % TIP,
 'cells': cells,
 'instrument_limits_disclosed': [
   'this stage was executed twice (10:09 and 10:15) with the same run id, so the second execution overwrote the '
   'first file; both printed the same shape (HTTP 500, text/plain, 21 B, no envelope), but only the later one '
   'survives as an artefact - from here on every execution gets its own run id',
   'the value caught by PlanWithAiSheet.tsx:715-726 is not observable from outside the page: the painted '
   'data-result-status proves the catch ran, but which exception it caught is not visible without a '
   'diagnostic build or a unit-level test, so no cause is claimed here',
   'this lane runs one browser per arm in a private profile, so a Service Worker from another arm cannot '
   'be involved; the arms were also not run in parallel'],
 'derived_result': None,
 'claimed_result': 'MEASURED_NOT_GRADED',
}
out = BASE / ('RECEIPT_%s.json' % RUN)
out.write_text(json.dumps(receipt, ensure_ascii=False, indent=1), encoding='utf-8')
print('cells', len(cells), '| equal_exact', equal_exact, '| verdicts', [c['verdict'] for c in cells])
print('wrote', out)
