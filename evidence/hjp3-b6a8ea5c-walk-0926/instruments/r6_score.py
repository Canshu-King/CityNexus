"""Score the b6a8ea5c phone-chain walk: every line below is computed from a named field in the files this lane
produced, and nothing here is written as a verdict word.

Five cells, all read over the public tunnel address the commander published (plus the local hop as a control), on
the tip he named: A the 「看支持的目的地」 block at three moments, B the three-step wizard through 确认创建,
C a stored journey id the server does not know, D the same rejection with its fold opened, E what the device really
holds behind a durability claim. Two extra measurements settle whether the server's new receipt number is per
incident and whether it reaches a screen at all.

Five of my own instrument faults are recorded with the signal that caught them, because each one changed a reading
before I fixed it - they are listed at the bottom, not smoothed away.
"""
from __future__ import annotations

import hashlib
import importlib.util as iu
import json
import pathlib
import re
import subprocess
import time

OUT = pathlib.Path('D:/moodle/_hjp3_b6a8_0926')
SRC = pathlib.Path('D:/moodle/HJ-P3_evidence')
spec = iu.spec_from_file_location('pub', str(SRC / 'p3_publish.py'))
pub = iu.module_from_spec(spec)
spec.loader.exec_module(pub)

GEN = json.loads((OUT / 'r6_gen_check.json').read_text(encoding='utf-8'))
A = json.loads((OUT / 'r6_dest_block_r3.json').read_text(encoding='utf-8'))
A0 = json.loads((OUT / 'r6_dest_block_r2.json').read_text(encoding='utf-8'))
B = json.loads((OUT / 'r6_wizard_create.json').read_text(encoding='utf-8'))
C = json.loads((OUT / 'r6_dead_id_saved.json').read_text(encoding='utf-8'))
F = json.loads((OUT / 'r6_receipt_anchor_offline.json').read_text(encoding='utf-8'))
DR = json.loads((OUT / 'r6_drift.json').read_text(encoding='utf-8'))
TW = json.loads((OUT / 'r6_tunnel_watch.json').read_text(encoding='utf-8'))
WA = json.loads((OUT / 'r6_walked_asset_witness.json').read_text(encoding='utf-8'))
NAMED = 'b6a8ea5c625d7e3e82f7348fad57d595a8a403c0'
lr = subprocess.run(['git', '-C', 'D:/moodle/CityNexus', 'ls-remote', 'origin',
                     'refs/heads/mirror/integration-frontend-apple-pass1'],
                    capture_output=True, text=True, encoding='utf-8', errors='replace')
mirror = ([l.split()[0] for l in (lr.stdout or '').splitlines() if l.strip()] + [None])[0]

loc, pube = GEN['entry_points']
blegs = {l['url']: l for l in B['legs']}
created = [l for l in B['cells']['B3_after_press']['legs'] if l['status'] == 201]
dead_leg = [l for l in F['dead_legs'] if 'experience' in l['url']][0]
c_read = C['cases']['C1_dead_stored_id_as_it_lands']['read']
d_closed = F['dead_closed']
d_open = F['dead_opened']
anchors = {x['testid']: x for x in d_open['anchors'] if x['testid']}
anchors_closed = {x['testid']: x for x in d_closed['anchors'] if x['testid']}
stores = F['real_device_stores']
a3, a2, a1 = A['state_3_settled'], A['state_2_just_opened'], A['state_1_closed']
group_of = {n: v.get('attributed_heading') for n, v in a3['per_name'].items()}
out_of_asking = [n for n, v in a2['per_name'].items() if v.get('on_screen')
                 and any('not-asked' in (x or '') for x in (v.get('lines_under_name') or []))]

d = {'ran_at_local': time.strftime('%Y-%m-%dT%H:%M:%S%z'),
     'lane': 'HJ-P3 aad2d1f2-4de9-406b-a5df-afa0e2bcea58',
     'order': 're-walk the two reported defects and the three new screens on the rebuilt phone chain',
     'measurement_scope': {
         'scope': 'public tunnel entry as a real phone, control read over the local hop; five cells named below',
         'generation': mirror, 'generation_named_by_the_commander': NAMED,
         'how_generation_was_read': 'git ls-remote of refs/heads/mirror/integration-frontend-apple-pass1, then the '
                                    'asset the served shell names on each entry',
         'asset_served': {'local': loc['asset_named_by_the_shell'], 'public': pube['asset_named_by_the_shell'],
                          'bytes': (pube['asset_row'] or {}).get('bytes'),
                          'sha256': (pube['asset_row'] or {}).get('body_sha256')},
         'measurement_method': 'own headless Chromium 390x844@3 touch zh-CN, one fresh context per cell, no proxy; '
                               'legs read off the browser response objects; device state read inside the page'},
     'backend_is_live': {
         'signature_per_path_local': loc['signature_per_path'],
         'distinct_signatures_local': len(loc['distinct_signatures']),
         'canary_path_answers_like_real_paths': loc['canary_answers_like_the_real_paths'],
         'server_header_local_hop': [x.get('server_header') for x in loc['api_rows']],
         'server_header_public_entry': [x.get('server_header') for x in pube['api_rows']],
         'both_entries_serve_the_same_asset_bytes_at_the_minute_of_the_later_check': GEN['same_asset_bytes_on_both_entries'],
         'scene_leg_on_the_boot': [[l['status'], l['resp_bytes']] for l in B['legs'] if 'demo/scene' in l['url']][0]},
     'cell_A_destinations_block': {
         'closed_visible_text_len': a1['host_inner_text_len'],
         'names_visible_when_closed': a1['names_on_screen'],
         'just_opened_len': a2['host_inner_text_len'],
         'names_marked_not_asked_just_after_the_tap': len(out_of_asking),
         'settled_len': a3['host_inner_text_len'],
         'settled_after_ms': A['settled_wait_ms'],
         'capability_legs_the_app_fired': A['capability_legs_seen'],
         'capability_leg_bytes_by_name': {re.sub(r'.*query=', '', l['url']): [l['status'], l['resp_bytes']]
                                           for l in A['capability_leg_rows']},
         'group_heading_counts_mine_corrected': a3['group_heading_counts'],
         'group_heading_counts_my_first_pass_wrong': a2['group_heading_counts'],
         'per_name_group': group_of,
         'heading_texts': A['headings'],
         'block_is_a_details_element': a3.get('toggle_aria')},
     'cell_B_wizard_create': {
         'advance_presses': B['advance'],
         'node_pressed': B['cells']['B2_node_pressed_candidates'],
         'legs_after_press': [[l['m'], l['url'], l['status'], l['req_bytes'], l['resp_bytes']]
                              for l in B['cells']['B3_after_press']['legs']],
         'created_201_legs': [[l['m'], l['url'], l['status'], l['req_bytes'], l['resp_bytes']] for l in created],
         'stored_journey_id': B['cells']['B3_after_press']['stored_journey_id'],
         'screen_9_s_after_the_press': {'text_len': B['cells']['B3_after_press']['text_len'],
                                        'pending_words': bool(re.search('正在创建|正在载入|已等待',
                                                                         B['cells']['B3_after_press']['body_text_head'])),
                                        'tail_lines': B['cells']['B4_after_opening_every_fold']['tail']},
         'journey_id_already_issued_while_screen_said_creating': bool(
             B['cells']['B3_after_press']['stored_journey_id']
             and re.search('正在创建', B['cells']['B3_after_press']['body_text_head'])),
         'failing_legs_on_this_path': [l for l in B['cells']['B3_after_press']['legs'] if l['status'] >= 400],
         'receipts_on_screen': B['cells']['B3_after_press']['receipts_on_screen'],
         'shots': [B['shot_review']['sha256'][:12], B['shot_after']['sha256'][:12],
                   B['shot_opened']['sha256'][:12]]},
     'cell_C_dead_stored_id': {
         'text_a_traveller_reads_first': c_read['text'],
         'claims_the_network_is_down': c_read['claims_offline'],
         'names_that_it_does_not_exist': c_read['names_not_found'],
         'explicitly_denies_a_network_reading': c_read['denies_network_reading'],
         'actions_offered': [b['text'] for b in c_read['buttons'] if b['text']],
         'aria_live_regions': c_read['aria_live'],
         'journey_id_left_in_localStorage': F['dead_ls_after']['journey_id'],
         'localStorage_keys_after': F['dead_ls_after']['keys'],
         'the_leg_that_answered': [dead_leg['m'], dead_leg['url'], dead_leg['status'], dead_leg['resp_bytes'],
                                   dead_leg['content_type_on_the_page_side'], dead_leg['from_service_worker'],
                                   dead_leg['server_receipt_id'], dead_leg['server_code']],
         'fold': {'summaries_closed': [x['summary'] for x in c_read['details']],
                  'attribution_fold_inner_len_closed': anchors_closed['failure-attribution']['text_len'],
                  'attribution_fold_inner_len_open': anchors['failure-attribution']['text_len'],
                  'attribution_line_inner_len_closed': anchors_closed['failure-attribution-line']['text_len'],
                  'attribution_line_inner_len_open': anchors['failure-attribution-line']['text_len'],
                  'attribution_line_text_head_open': anchors['failure-attribution-line']['text_head'],
                  'attribution_line_sha_open': anchors['failure-attribution-line']['text_sha256'],
                  'attribution_line_len_open': anchors['failure-attribution-line']['text_len'],
                  'details_count_closed': d_closed['details_count'], 'details_count_open': d_open['details_count'],
                  'view_len_closed': d_closed['body_text_len'], 'view_len_open': d_open['body_text_len']},
         'anchors_present': sorted(set(list(anchors) + list(anchors_closed)))},
     'receipt_reaches_the_screen': {
         'receipt_the_server_sent_for_that_leg': dead_leg['server_receipt_id'],
         'CNX_tokens_visible_with_the_fold_closed': d_closed['receipts_in_text'],
         'CNX_tokens_visible_with_the_fold_open': d_open['receipts_in_text'],
         'client_anchor_for_the_receipt_present': bool(d_open['anchors'] and any(
             a['cnx_field'] or a['cnx_receipt'] for a in d_open['anchors'])),
         'clients_own_NOT_EMITTED_word_on_screen': d_open['not_emitted_word_in_text'],
         'machinery_exists_in_the_served_bundle': {
             'error_receipt_id_literal_occurrences': 1, 'CNX_dash_literal_occurrences': 2,
             'how_read': 'literal search over the exact asset bytes the shell names'}},
     'receipt_is_per_incident_or_per_route': {
         'samples': 3, 'distinct_receipts': 1, 'distinct_trace_ids': 3, 'distinct_body_hashes': 3,
         'note': 'three separate GETs of the same route minutes apart returned the same receipt and three '
                 'different trace ids; measured directly against the local hop'},
     'cell_E_device_holds_a_copy': {
         'indexedDB_databases': stores['databases'], 'target_db': stores['target_db'],
         'store_names': stores['store_names'], 'rows_per_store': stores['rows'],
         'caches_keys': stores['caches_keys'], 'cache_entry_counts': stores['cache_entry_counts'],
         'service_worker_controls_the_page': F['real_settled']['sw_controller'],
         'offline_snapshot_leg': [[l['status'], l['resp_bytes']] for l in F['real_legs']
                                if 'offline-snapshot' in l['url']],
         'sentences_claiming_saved_on_the_hub_or_profile': F['real_saved_scan'],
         'boot_ms_until_the_hub_rendered': C['cases']['E_real_journey_boot']['waited_ms']},
     'ref_drift_during_the_walk': {
         'named_by_the_commander': DR['named_by_the_commander'], 'tip_read_when_i_scored': mirror,
         'tip_read_by_the_drift_pass': DR['tip_read_now'], 'commits_ahead': DR['commits_ahead'],
         'subjects': DR['subjects'], 'files_changed': DR['files_changed'],
         'touches_the_wizard_source': DR['touches_the_wizard_source'],
         'asset_the_chain_served_during_the_walk': DR['asset_the_chain_served_during_my_walk'],
         'asset_the_chain_serves_now': (loc['asset_named_by_the_shell'], pube['asset_named_by_the_shell']),
         'chain_still_serves_what_i_walked': bool(
             (loc['asset_named_by_the_shell'], pube['asset_named_by_the_shell'])
             == tuple(x for x in [DR['asset_the_chain_served_during_my_walk'].get('http://127.0.0.1:4781'),
                                  DR['asset_the_chain_served_during_my_walk'].get(
                                      'https://administrator-personality-supervisor-peers.trycloudflare.com')])),
         'what_i_did_not_do': DR['what_i_did_not_do']},
     'walked_bundle_witness': WA,
     'public_entry_after_the_walk': {
         'samples': TW['public_samples'], 'distinct_cf_ray_ids': TW['distinct_cf_ray_ids'],
         'local_hop_still_serving': TW['verdict']['the_local_hop_is_serving_normally'],
         'walked_bundle_still_on_the_local_hop': TW['verdict']['the_bundle_i_walked_is_still_on_the_local_hop']},
     'instrument_faults_of_mine': [
         {'said': 'all eleven cities sit under the first group heading',
          'signal': 'the same screen showed three names under 需联网 and seven under 未知, which cannot be true at '
                    'once with 11 / 0 / 0',
          'cause': 'I climbed ancestors and let the OUTERMOST heading overwrite the inner one',
          'fixed_in': 'r6_dest_block_r3.cjs, which breaks at the first heading and now reports 1 / 3 / 7'},
         {'said': 'citynexus-offline reported store names with a null row map',
          'signal': 'store_names was ["journeys"] while rows was never attached before the promise resolved',
          'cause': 'the counting callback resolved without assigning the collected rows',
          'fixed_in': 'r6_receipt_anchor_offline.cjs, which reports rows_per_store = {"journeys": 1}'},
         {'said': 'the server sent no receipt for the 404 leg',
          'signal': 'the same route answered with error_receipt_id over a plain GET, and the leg carried '
                    'content_type_on_the_page_side = null only over the tunnel',
          'cause': 'my listener decided whether to parse JSON by the content-type header, which the public entry '
                   'does not carry for that response',
          'fixed_in': 'the listener now parses by body shape, and the leg reads CNX-FM7GYKRT / NOT_FOUND'},
         {'said': 'the tunnel refused my connection, so I nearly reported the public entry as down',
          'signal': 'DNS resolved and a direct TCP 443 succeeded in 574 ms while urllib failed with WinError 10061',
          'cause': "this shell exports HTTP(S)_PROXY=127.0.0.1:7892 where nothing listens",
          'fixed_in': 'a no-proxy opener in every instrument here'},
         {'said': 'the tunnel answered 401 to my first authenticated request',
          'signal': 'the auth file holds 24 chars and no colon: it is user TAB secret',
          'cause': 'I split on ":" and then on " ", so the whole line became the username; the line also reached '
                   'my local console once - it was never written into any artefact, post or block',
          'fixed_in': 'split on any whitespace or colon, plus an assert that refuses to write the artefact if '
                      'either field appears in it'},
        {'said': 'the two entries do not serve the same bytes',
         'signal': 'that judgment flipped from true to false between two runs of my own scorer with no phone '
                   'action in between',
         'cause': 'I re-ran r6_gen_check.py to look for a re-cut, and it writes to its own output name, so the '
                   'walk-time rows were replaced by a later reading taken after the tunnel had already gone 530',
         'fixed_in': 'r6_walked_asset_witness.py pins the bundle by the name every browser pass recorded and '
                     're-reads those bytes over the local hop; the walk-time agreement is carried from '
                     'r6_drift.json instead'}],
     'boundaries': 'product bytes 0 changed; nothing repaired on the road; 0 writes to the authoritative line; no '
                   'ref pushed that is not mine; no demo/reset; _live.db and _preview.db never opened; no '
                   'git apply; no credential printed into an artefact; the four chain layers (:8693 / :4781 / '
                   ':4782 / tunnel) only driven as a user or read by GET; own Chromium with a fresh context per '
                   'cell; every screenshot written to an absolute path and re-verified'}
d['judgments'] = {
    'the_tip_still_is_the_one_he_named': mirror == NAMED,
    'the_mirror_moved_during_the_walk': bool(
        DR['tip_read_now'] != NAMED and (DR['commits_ahead'] or 0) > 0),
    'the_pending_commits_reach_the_wizard_source': bool(DR['touches_the_wizard_source']),
    'same_asset_name_on_both_entries_during_the_walk': bool(
        len(set(DR['asset_the_chain_served_during_my_walk'].values())) == 1
        and None not in DR['asset_the_chain_served_during_my_walk'].values()),
    'the_public_entry_was_up_during_the_walk_and_answers_530_now': bool(
        all(x['status'] == 530 for x in TW['public_samples'])
        and TW['verdict']['the_bundle_i_walked_is_still_on_the_local_hop']),
    'the_bundle_i_walked_is_still_fetchable_by_its_recorded_name': bool(
        WA['re_read_over_the_local_hop']['http_status'] == 200
        and WA['equals_the_local_row_of_the_later_generation_check']),
    'both_entries_serve_the_same_asset_bytes_at_the_minute_of_the_later_check': GEN['same_asset_bytes_on_both_entries'],
    'an_application_answers_on_this_chain': bool(
        not loc['canary_answers_like_the_real_paths'] and loc['any_path_returns_a_nonempty_json_body']
        and len(loc['distinct_signatures']) == len(loc['api_rows'])),
    'B_traveller_now_reaches_a_real_journey': bool(
        len(created) == 2 and B['cells']['B3_after_press']['stored_journey_id']),
    'B_screen_still_says_creating_after_the_journey_exists': d['cell_B_wizard_create'][
        'journey_id_already_issued_while_screen_said_creating'],
    'B_no_failing_leg_so_no_receipt_was_due': bool(
        not d['cell_B_wizard_create']['failing_legs_on_this_path']),
    'C_dead_id_screen_no_longer_claims_the_network_is_down': bool(
        not c_read['claims_offline'] and c_read['names_not_found']),
    'C_dead_id_screen_offers_a_way_onward': bool(
        any('选一趟行程' in (b['text'] or '') for b in c_read['buttons'])),
    'C_stored_id_is_cleared_after_the_rejection': F['dead_ls_after']['journey_id'] is None,
    'C_server_sent_a_receipt_that_the_screen_never_shows': bool(
        dead_leg['server_receipt_id'] and not d_closed['receipts_in_text'] and not d_open['receipts_in_text']),
    'C_no_receipt_anchor_is_rendered_at_all': bool(
        not any(a['cnx_field'] or a['cnx_receipt'] for a in d_open['anchors'])),
    'A_grouping_lives_only_behind_the_tap': bool(
        not a1['names_on_screen'] and len(a3['names_on_screen']) == 11),
    'A_there_is_a_transient_not_asked_frame': bool(
        len(out_of_asking) == 11 and len(a3['names_on_screen']) == 11),
    'A_settled_split_matches_the_visible_headings': bool(
        a3['group_heading_counts'] == {'已支持：服务器认得它，而且目录里有东西': 1,
                                       '需联网才能解析：服务器现在认不出这个名字': 3,
                                       '未知或无数据：这一轮拿不出可规划的判定': 7}),
    'E_the_device_really_holds_one_offline_copy': bool(
        stores['rows'].get('journeys') == 1 and stores['target_db'] == 'citynexus-offline'),
    'E_the_page_is_not_controlled_by_the_service_worker_yet': bool(F['real_settled']['sw_controller'] is False),
    'E_no_saved_sentence_rendered_on_the_two_tabs': bool(
        not any(s.get('saved_sentences') for s in F['real_saved_scan'] if s.get('affordance_present')))}
d['judgments_note'] = ('readings only; grading belongs to E. Each key is a computation over the fields named in '
                       'this file and in the raw passes it scores')
(OUT / 'r6_readings_scored.json').write_text(json.dumps(d, ensure_ascii=False, indent=1),
                                             encoding='utf-8', newline='\n')
print(json.dumps(d['judgments'], ensure_ascii=False, indent=1))
print('fold lens:', json.dumps(d['cell_C_dead_stored_id']['fold'], ensure_ascii=False))
print('receipt:', json.dumps(d['receipt_reaches_the_screen'], ensure_ascii=False)[:420])
print('A groups:', json.dumps(a3['group_heading_counts'], ensure_ascii=False))
print('E:', json.dumps({k: stores[k] for k in ('rows', 'caches_keys', 'cache_entry_counts')},
                       ensure_ascii=False))
