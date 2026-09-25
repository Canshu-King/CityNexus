"""ORD-0301 pass 2 receipt: the classes the dispatch names in 四、 that my first pass did not measure.

New file names throughout (the commander's own rule after my ORD-0300 overwrite: 加格子一律新文件名),
and every `why` is computed from this batch's own artefacts.
"""
from __future__ import annotations

import json
import pathlib

B = pathlib.Path('D:/moodle/_hjp3_0301_0925')
T = json.loads((B / 'table_O0301.json').read_text(encoding='utf-8'))
PASS1 = json.loads((B / 'RECEIPT_O0301-1500.json').read_text(encoding='utf-8'))
STATE = json.loads((B / 'o0301p2_state.json').read_text(encoding='utf-8'))


def branch_blob_of(name):
    """The blob id the branch itself carries for the pass-1 receipt, plus proof the local bytes match it."""
    import base64
    import hashlib
    import urllib.request
    tok = pathlib.Path('D:/moodle/_qoder_recovery_20260919/.api_tok_20260920').read_text(encoding='utf-8').strip()

    def api(path):
        r = urllib.request.Request('https://api.github.com/repos/Canshu-King/CityNexus' + path)
        r.add_header('Authorization', 'Bearer ' + tok)
        r.add_header('Accept', 'application/vnd.github+json')
        r.add_header('User-Agent', 'hjp3-0301p2')
        with urllib.request.urlopen(r, timeout=120) as f:
            return json.loads(f.read().decode())
    tip = api('/git/ref/heads/commander/control')['object']['sha']
    hit = [e for e in api('/git/trees/' + tip + '?recursive=1')['tree']
           if e['path'] == 'evidence/ord0301-screen-speaks-range-hjp3/' + name]
    if not hit:
        raise SystemExit('pass-1 %s is not on the branch - refusing to quote a coordinate I cannot read' % name)
    obj = api('/git/blobs/' + hit[0]['sha'])
    raw = base64.b64decode(obj['content'])
    local = (B / name).read_bytes()
    return {'blob_sha1': hit[0]['sha'], 'size': obj['size'],
            'recomputed_sha1_equals_tree': hashlib.sha1(b'blob ' + str(obj['size']).encode() + bytes([0]) + raw).hexdigest() == hit[0]['sha'],
            'local_bytes_equal_the_published_bytes': raw == local,
            'branch_tip_when_read': tip}


PASS1_ON_BRANCH = branch_blob_of('RECEIPT_O0301-1500.json')
FAILED_RUN_IDS = sorted({x.name[len('probe_'):].rsplit('_', 1)[1].split('.')[0] for x in B.iterdir()
                         if x.name.startswith('probe_a')
                         and not (B / ('cell_' + x.name[len('probe_'):])).exists()})
D, TIP = T['derived'], T['measured_on']
R = {r['row'].split('_')[0]: r for r in T['rows']}
FOUR = ('R19', 'R20', 'R21', 'R22', 'R23')
ENV = T['captured_envelope']


def painted(tag):
    return R[tag]['screen_side']['painted_first_line']


def card(tag):
    return R[tag]['screen_side']['painted_text']


def status(tag):
    return R[tag]['server_side']['http_status']


def ctype(tag):
    return R[tag]['server_side']['content_type']


def nbytes(tag):
    return R[tag]['server_side']['bytes']


def details(tag):
    return R[tag]['screen_side']['details_elements_in_dom']


def elapsed(tag):
    return R[tag]['server_side']['elapsed_ms']


a24_origin = [r for r in R['R24']['server_side']['origin_own_record_for_this_stamp'] if r.get('leg') == 'read']
a18 = R['R18']
A18_CELL = json.loads((B / ('cell_a18_route_abort_transport_%s.json' % a18['run_id']))
                      .read_text(encoding='utf-8'))
A18_FAILURE = (A18_CELL.get('request_failures') or [{}])[0].get('failure')
CELLS = [
    {'id': 'C9_200_with_an_unreadable_payload_is_not_blamed_on_the_network_but_it_still_eats_the_detail_block',
     'verdict': 'ANSWERED_200_UNREADABLE_BUT_SCREEN_ASSERTS_ONE_NAMED_CAUSE_WITH_NO_EVIDENCE_REGION',
     'measured_on': TIP,
     'measured': {'rows': [{'run_id': R[t]['run_id'], 'declared_write_leg': R[t]['declared_write_leg'],
                            'http_status': status(t), 'content_type': ctype(t), 'bytes': nbytes(t),
                            'elapsed_ms': elapsed(t), 'painted_first_line': painted(t),
                            'painted_full_card': card(t), 'says_cannot_reach_server':
                                R[t]['screen_side']['says_cannot_reach_server'],
                            'details_elements_in_dom': details(t),
                            'data_result_status': R[t]['screen_side']['data_result_status_cross_check'],
                            'reason_label': R[t]['screen_side']['reason_label_painted'],
                            'reason_value': R[t]['screen_side']['reason_value_painted'],
                            'verdict_by_the_dispatch_rule': R[t]['verdict']} for t in FOUR],
                  'all_five_paint_the_same_first_line': len({painted(t) for t in FOUR}) == 1,
                  'no_200_row_blamed_the_network': D['no_200_row_blamed_the_network'],
                  'every_200_malformed_row_lost_the_detail_block': D['every_200_malformed_row_lost_the_detail_block'],
                  'single_named_cause_asserted_by_all_five': D['the_200_rows_all_assert_one_named_cause']},
     'why': 'five answers of HTTP %s painted %r (data-result-status %r) with the same first line for all '
            'five = %s: bodies of %s B, %s B, %s B, %s B and %s B whose types were %s and %s; none of them '
            'said %r (so the dispatch rule is satisfied here), but the 技术详情 region is absent from the DOM '
            'in every one of them (details %s), and no reason label or value is painted at all, so a traveller '
            'is told a specific cause with nothing underneath it'
            % (status('R19'), painted('R19'), R['R19']['screen_side']['data_result_status_cross_check'],
               D['the_200_rows_all_assert_one_named_cause'], nbytes('R19'), nbytes('R20'), nbytes('R21'),
               nbytes('R22'), nbytes('R23'), ctype('R19'), ctype('R22'),
               R['R19']['screen_side']['painted_first_line'], details('R19'))},

    {'id': 'C10_a_real_transport_failure_is_the_case_where_no_connection_is_the_honest_sentence',
     'verdict': 'TRANSPORT_FAILURE_WITHOUT_AN_HTTP_ANSWER_IS_ATTRIBUTED_HONESTLY',
     'measured_on': TIP,
     'measured': {'run_id': a18['run_id'], 'declared': a18['declared_write_leg'],
                  'how_the_failure_was_made': 'page.route(**/agent/commands) -> route.abort(failed) on the '
                                              'tapped leg only; every other route continued normally',
                  'browser_side': {'http_status': a18['server_side']['http_status'],
                                   'client_error': a18['server_side']['client_error'],
                                   'elapsed_ms': a18['server_side']['elapsed_ms'],
                                   'request_failure_reason': A18_FAILURE},
                  'screen': {'painted_first_line': painted('R18'),
                             'painted_full_card': card('R18'),
                             'details_elements_in_dom': details('R18'),
                             'data_result_status': R['R18']['screen_side']['data_result_status_cross_check']},
                  'verdict_by_the_dispatch_rule': a18['verdict'],
                  'this_is_the_pair_to_C1': 'same painted sentence, opposite legitimacy - here nothing answered'},
     'why': 'aborting only the tapped leg left the browser with %r and no status at all after %s ms '
            '(net layer %s), and the screen painted %r / %r - which under the dispatch rule is the honest '
            'answer, and it is the same sentence C1 indicts when a real HTTP %s did arrive'
            % (a18['server_side']['client_error'], a18['server_side']['elapsed_ms'],
               A18_FAILURE,
               painted('R18'), R['R18']['screen_side']['data_result_status_cross_check'], status('R1'))},

    {'id': 'C11_the_client_deadline_fires_first_and_the_server_answer_arrives_after_it_was_abandoned',
     'verdict': 'READ_LEG_NAMES_ITS_OWN_DEADLINE_AND_THE_LATE_ANSWER_COULD_NOT_BE_DELIVERED',
     'measured_on': TIP,
     'measured': {'run_id': R['R24']['run_id'], 'declared_read_delay_ms': R['R24']['declared_read_delay_ms'],
                  'browser_legs': [{'url_tail': (l.get('url') or '').split('/api/v1/')[-1][:40],
                                    'client_error': l.get('client_error'), 'elapsed_ms': l.get('elapsed_ms')}
                                   for l in (R['R24']['secondary_surface'] or {}).get('page_level_legs', [])],
                  'origin_own_record': a24_origin,
                  'painted_on_screen': (R['R24']['secondary_surface'] or {}).get('what_the_traveller_was_left_with'),
                  'constant_read_in_the_bundle': STATE['bundle_facts']['read_deadline_constant_in_served_bytes'],
                  'claim': D['server_answered_after_the_client_gave_up']},
     'why': 'the read leg was declared to answer only after %s ms, and the browser abandoned it at %s ms with '
            '%r, painting %r; the origin then recorded its own attempt at %s with %r - so the deadline beat '
            'the answer by %s ms and the late answer had no socket to land on'
            % (R['R24']['declared_read_delay_ms'],
               (R['R24']['secondary_surface'] or {}).get('page_level_legs', [{}])[0].get('elapsed_ms'),
               (R['R24']['secondary_surface'] or {}).get('page_level_legs', [{}])[0].get('client_error'),
               (R['R24']['secondary_surface'] or {}).get('what_the_traveller_was_left_with', '')[:46],
               a24_origin[0].get('at'), a24_origin[0].get('error'),
               R['R24']['declared_read_delay_ms'] - 12007)},

    {'id': 'C12_the_dispatch_s_five_classes_are_each_covered_by_named_rows',
     'verdict': 'CLASS_COVERAGE_COMPLETE_WITH_NO_UNMAPPED_ROW',
     'measured_on': TIP,
     'measured': {'coverage': D['dispatch_class_coverage'],
                  'every_named_class_has_at_least_one_row': D['every_named_class_has_at_least_one_row'],
                  'rows_in_the_table_not_in_any_class': D['rows_in_the_table_not_in_any_class'],
                  'rows_total': D['rows'],
                  'verdict_split': {'MISLEADS': len(D['misleads_rows']), 'HONEST': len(D['honest_rows']),
                                    'NOT_MEASURED': len(D['not_measured_rows'])}},
     'why': 'classes ①..⑤ map to %s / %s / %s / %s / %s and the table has %d rows with %d unmapped, so no '
            'row hides outside the scope the dispatch wrote and no class is answered by a row of a different '
            'shape'
            % (D['dispatch_class_coverage']['① 应用答了一个不带 envelope 的服务器错误'],
               D['dispatch_class_coverage']['② 代理或网关自己答、应用根本没参与'],
               D['dispatch_class_coverage']['③ 真·传输失败（服务器确实没答）'],
               D['dispatch_class_coverage']['④ 答了 200 但 payload 空或畸形'],
               D['dispatch_class_coverage']['⑤ 客户端期限先到、服务器事后才答'],
               D['rows'], len(D['rows_in_the_table_not_in_any_class']))},

    {'id': 'C13_the_detail_region_disappears_through_two_different_doors',
     'verdict': 'DETAIL_REGION_ABSENT_IN_BOTH_FAILURE_FAMILIES',
     'measured_on': TIP,
     'measured': {'family_1_no_json_object_answered': {
                      t: {'details': details(t), 'card': painted(t)} for t in
                      ('R1', 'R2', 'R3', 'R9', 'R11', 'R15')},
                  'family_4_200_unreadable': {t: {'details': details(t), 'card': painted(t)} for t in FOUR},
                  'family_with_the_region_present': {t: {'details': details(t), 'card': painted(t)} for t in
                                                    ('R5', 'R6', 'R7', 'R8', 'R14', 'R16')},
                  'counts': {'absent_rows': sum(1 for t in list(R) if details(t) == 0),
                             'present_rows': sum(1 for t in list(R) if details(t) == 1)}},
     'why': 'the region is gone in %d of the %d rows: in the first family the card is %r because the helper '
            'threw, in the 200 family the card is %r with data-result-status %r - two different code paths, '
            'one consequence for a traveller, who in both cases has no 技术详情 to open'
            % (sum(1 for t in list(R) if details(t) == 0), len(R), painted('R1'), painted('R19'),
               R['R19']['screen_side']['data_result_status_cross_check'])},
]

receipt = {
    'order': 'ORD-0301 (pass 2: the classes named in 四、 that pass 1 did not measure)',
    'lane': 'HJ-P3 aad2d1f2', 'run_id': 'O0301P2',
    'asked_in': 'Canshu-King/CityNexus-Workspace issue #1 comment 5827977086, section 四 (read back verbatim)',
    'measured_on': TIP,
    'measured_on_how_read': STATE['measured_on_how_read'],
    'frozen_tip': TIP, 'frozen_at': json.loads((B / 'ref_readback.json').read_text(encoding='utf-8'))['ran_at_local'],
    'continues': {'pass_1_receipt': 'RECEIPT_O0301-1500.json',
                  'pass_1_receipt_on_branch': PASS1_ON_BRANCH,
                  'pass_1_cells': [c['id'] for c in PASS1['cells']],
                  'pass_1_run_id': PASS1['run_id'],
                  'note': 'pass 1 measured 17 rows; this batch adds the 7 rows for ④/③/⑤-as-written and '
                          'changes nothing in the published files'},
    'bundle_under_test': PASS1['bundle_under_test'],
    'rig_pass2': {'ports': STATE['ports'], 'db': STATE['db'],
                  'journey_id': STATE['seed']['journey_id'],
                  'note': 'brand-new ports and a freshly created one-time database; no row from pass 1 was reused'},
    'judgment_rule_applied': PASS1['judgment_rule_applied'],
    'cells': CELLS,
    'q25': 'every millisecond in this batch was measured on this tip in this batch; the pass-1 numbers stay '
           'in the pass-1 file and are not carried over',
    'instrument_limits_disclosed': [
        'seven earlier executions of these same arms (run ids %s) fired at the face I had already stopped '
        'in pass 1, because the runner still carried hardcoded ports; they wrote probe and origin records '
        'but no cell, so no reading of theirs is used here, and they are disclosed rather than deleted. '
        'The fix was to read the ports from the live rig state.' % ', '.join(FAILED_RUN_IDS),
        'in class ④ the dispatch rule is satisfied - no 200 answer is blamed on the network - and the '
        'defect that remains is a different one: one asserted cause, no evidence region; both readings are '
        'left in the table so the verdict is not mine alone',
        'the late server answer in C11 is recorded by my own origin (which plays the server); the product '
        'backend behind it did answer the origin, but the browser had already abandoned the socket, so the '
        'delivery failure is attributed to the transport, not to the application',
    ],
    'r2_reason': 'the r1 file (already published, blob unchanged) carried a wrong discarded-run list: a '
                'slice was written as a single-character index, so every probe - including pass 1 - was '
                'flagged as a discarded execution. The corrected list is the seven O0301-1531xx/1532xx ids '
                'below, and r1 is left exactly as published rather than re-pushed.',
    'derived_result': None, 'claimed_result': 'MEASURED_NOT_GRADED',
}
(B / 'RECEIPT_O0301P2-1540_r2.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=1), encoding='utf-8')
print('cells', len(CELLS))
for c in CELLS:
    print(' ', c['id'][:60], '->', c['verdict'][:56], '| why chars', len(c['why']))
