"""Score the one-pass recheck on `ab12c17a…` against the baseline I set on the previous generation.

The commander re-cut the bundle again and asked for exactly one re-run of the two items I had listed as "a
traveller cannot do", readings only, grading left to E. What is computed here:

  * whether the tip he named is the tip the mirror ref carries right now (my own `git ls-remote`);
  * what the artefact he cited actually contains - it is a render check (`CNX_CMDR_RENDER_CHECK_V1`), which has
    no asset rows and no generation field, so the byte binding of this generation is MY OWN three GETs, not his
    sentence, and that is said out loud rather than hidden;
  * whether baseline item ① moved: leg, node pressed, stored id, and the two sentences compared against the
    stored previous-generation file, not against my recollection;
  * whether baseline item ② moved: measured twice on purpose - once inside the confounded same-context pass and
    once in a fresh context that never touched the wizard - because the first number differed from the baseline
    for a reason that was mine, and a diff over the two painted texts says which line actually changed.

Three instrument faults are recorded instead of smoothed over, each with the signal that caught it.
"""
from __future__ import annotations

import base64
import difflib
import hashlib
import importlib.util as iu
import json
import pathlib
import subprocess
import time

OUT = pathlib.Path('D:/moodle/_hjp3_0323walk_0926')
SRC = pathlib.Path('D:/moodle/HJ-P3_evidence')
spec = iu.spec_from_file_location('pub', str(SRC / 'p3_publish.py'))
pub = iu.module_from_spec(spec)
spec.loader.exec_module(pub)

RC = json.loads((OUT / 'r5_recheck_raw.json').read_text(encoding='utf-8'))
BASE = json.loads((OUT / 'r5_walk_scored.json').read_text(encoding='utf-8'))
BASE_WALK2 = json.loads((OUT / 'r5_walk2_findings.json').read_text(encoding='utf-8'))
FACES = json.loads((OUT / 'r5_faces_get.json').read_text(encoding='utf-8'))
SCAN = json.loads((OUT / 'r5_anchor_scan.json').read_text(encoding='utf-8'))
FRESH = json.loads((OUT / 'r5_deadid_fresh.json').read_text(encoding='utf-8'))
DRIFT = json.loads((OUT / 'r5_tip_drift.json').read_text(encoding='utf-8'))
DRIFT = json.loads((OUT / 'r5_tip_drift.json').read_text(encoding='utf-8'))
PROBE_BLOB = '2fcaaf3e49295a06f3fe9c03db3f54239bf6e610'
NEW_TIP = 'ab12c17a65450c2c3062c9232e27a26c4ae1b485'
NAMED_ASSET = 'index-D6IOFaQS.js'

raw = base64.b64decode(pub.api('/git/blobs/' + PROBE_BLOB)['content'])
recomputed = hashlib.sha1(b'blob %d\0' % len(raw) + raw).hexdigest()
cmdr = json.loads(raw.decode('utf-8'))
lr = subprocess.run(['git', '-C', 'D:/moodle/CityNexus', 'ls-remote', 'origin',
                     'refs/heads/mirror/integration-frontend-apple-pass1'],
                    capture_output=True, text=True, encoding='utf-8', errors='replace')
mirror_sha = ([l.split()[0] for l in (lr.stdout or '').splitlines() if l.strip()] + [None])[0]

c1 = RC['cells']['C1_confirm_create']
c2_walked = RC['cells']['C2_dead_journey_id']
base_c1 = BASE['cells']['C1_new_journey_wizard']['pressing_the_real_submit_button']
base_leg = (base_c1['legs_after_the_press'] or [{}])[0]
now_leg = (c1['legs_after_press'] or [{}])[0]
base_sent = set(base_c1['lines_the_traveller_reads'])
now_sent = set(x for x in c1.get('painted_after_capped', '').split('\n')
               if '这一步没有成功' in x or '服务器拒绝了这一步' in x)
base_dead = BASE_WALK2['cells']['W4_broken_four_ways']['a_dead_stored_id']['read']
base_dead_lines = [l for l in base_dead['painted_text_capped'].split('\n')]
fresh_dead_lines = [l for l in FRESH['painted_before'].split('\n')]
changed_lines = [l for l in difflib.unified_diff(base_dead_lines, fresh_dead_lines, lineterm='', n=0)
                 if (l.startswith('+') or l.startswith('-')) and not l.startswith(('+++', '---'))]
faces_by_path = {r['path']: r for r in FACES['rows']}
js_face = faces_by_path.get(RC['binding']['asset_named_by_the_served_page'] and
                            '/' + RC['binding']['asset_named_by_the_served_page'], {})

d = {'ran_at_local': time.strftime('%Y-%m-%dT%H:%M:%S%z'),
     'lane': 'HJ-P3 aad2d1f2-4de9-406b-a5df-afa0e2bcea58',
     'order': 'one-pass recheck of the two baseline blocked items on the newest phone generation, readings only',
     'measurement_scope': {
         'scope': '① the step-3 确认创建 press on the deployed wizard; ② a journey id that does not exist',
         'generation': NEW_TIP,
         'artifact': 'the files this run wrote under ' + str(OUT) + ' and the branch paths listed at the end of '
                     'the ledger block',
         'measurement_method': 'own Chromium lane against the deployed chain at 127.0.0.1:4781 at 390x844@3 with '
                              'touch and zh-CN; one journey walk, plus GET-only passes over the shell, the assets '
                              'it names and one fresh-context navigation'},
     'generation_how_read': 'git ls-remote of refs/heads/mirror/integration-frontend-apple-pass1 in this run, '
                            'compared with the tip the commander named',
     'mirror_tip_read_at_this_minute': mirror_sha,
     'mirror_equals_the_tip_he_named': mirror_sha == NEW_TIP,
     'mirror_ref_drift_read_separately': {
         'named': DRIFT['generation_named_by_the_commander'],
         'tip_read_now': DRIFT['mirror_tip_read_now'],
         'commits_ahead_of_the_named_generation': DRIFT['commits_ahead'],
         'subjects': [c['subject'] for c in DRIFT['commits']],
         'frontend_files_in_the_drift': DRIFT['frontend_files_changed'],
         'touches_the_wizard_source': DRIFT['touches_the_wizard_source'],
         'what_i_did_not_do': DRIFT['what_i_did_not_do'],
         'how_read': DRIFT['method']},
     'commander_artefact_as_I_READ_IT': {
         'blob_cited': PROBE_BLOB, 'blob_recomputed_from_bytes_i_read': recomputed,
         'cited_equals_recomputed': recomputed == PROBE_BLOB, 'bytes': len(raw),
         'schema': cmdr.get('schema'), 'overall': cmdr.get('overall'),
         'surface_count': len(cmdr.get('surfaces') or []),
         'surface_verdicts': [s.get('verdict') for s in (cmdr.get('surfaces') or [])],
         'visible_text_chars_surface_0': (cmdr['surfaces'][0].get('chars_of_visible_text')
                                          if cmdr.get('surfaces') else None),
         'attr_values_scanned_surface_0': (cmdr['surfaces'][0].get('attr_values_scanned')
                                           if cmdr.get('surfaces') else None),
         'leak_patterns_in_his_ruler': cmdr.get('leak_patterns'),
         'wait_ms': cmdr.get('wait_ms'),
         'dom_bytes_surface_0': (cmdr['surfaces'][0].get('dom_bytes') if cmdr.get('surfaces') else None),
         'png_bytes_surface_0': (cmdr['surfaces'][0].get('png_bytes') if cmdr.get('surfaces') else None),
         'carries_asset_rows': bool(cmdr.get('rows')),
         'names_a_generation': any('generation' in k for k in cmdr.keys()),
         'limit': 'this artefact is a rendering check: it has no asset rows and no generation field, so it cannot '
                  'pin bytes. My generation binding is the GET block below, which I took myself'},
     'faces_i_read_myself_over_get': {
         'shell': FACES['shell'], 'assets_named_by_the_shell': FACES['assets_named_by_the_shell'],
         'rows': FACES['rows'],
         'js_row_equals_the_bytes_my_click_pass_hashed': bool(
             js_face.get('bytes_received') == RC['binding']['asset_bytes']
             and js_face.get('sha256_of_bytes_i_received') == RC['binding']['asset_sha256_64_hex']),
         'js_row_equals_the_bytes_my_anchor_scan_hashed': bool(
             js_face.get('sha256_of_bytes_i_received') == SCAN['asset']['body_sha256']),
         'requests_made': FACES['requests_made'], 'clicks': FACES['clicks'], 'writes': FACES['writes']},
     'anchor_literals_in_the_served_bundle': SCAN['anchor_literals_in_the_served_bundle'],
     'data_testid_attribute_literals_in_the_bundle': SCAN['data_testid_attribute_literals_in_the_bundle'],
     'failure_sentence_literals_in_the_served_bundle': SCAN['failure_sentences_literals_in_the_served_bundle'],
     'bundle_side_scan_limit': SCAN['limit_named'],
     'baseline_items': {
         'B1_confirm_create': {
             'node_pressed_by_role': c1['node_pressed'], 'press_result': c1['press_result'],
             'leg_now': now_leg, 'leg_on_the_previous_generation': base_leg,
             'sentences_now': sorted(now_sent), 'sentences_then': sorted(base_sent),
             'stored_journey_id_now': c1['stored_journey_id'],
             'stored_journey_id_then': base_c1['journey_id_stored_in_localStorage_after'],
             'still_on_wizard_now': c1['still_on_wizard'], 'still_on_wizard_then':
                 base_c1['still_on_the_wizard_afterwards'],
             'exception_text_after_opening_details': c1['exception_in_text_after_opening_details'],
             'details_blocks_on_the_failure_screen': c1['details_count'],
             'attribute_hits_after_the_press': c1['attribute_hits'],
             'screenshots': c1['screenshots']},
         'B2_dead_journey_id': {
             'fresh_context_reading': {
                 'url': FRESH['url_asked'], 'inner_len_before_opening_details':
                     FRESH['before_opening_details']['inner_len'],
                 'text_content_len': FRESH['before_opening_details']['text_content_len'],
                 'details_blocks': FRESH['before_opening_details']['details_count'],
                 'inner_len_after_opening_details': FRESH['after_opening_details']['inner_len'],
                 'buttons': FRESH['before_opening_details']['buttons'],
                 'tail_lines': FRESH['after_opening_details']['tail_lines'],
                 'exception_text': FRESH['after_opening_details']['exception_in_text'],
                 'attribute_hits': FRESH['after_opening_details']['attr_hits'],
                 'localStorage_keys': FRESH['before_opening_details']['localStorage_keys'],
                 'screenshot': FRESH['screenshot'], 'legs': FRESH['legs'],
                 'clicks': FRESH['clicks'], 'keystrokes': FRESH['keystrokes']},
             'baseline_reading_previous_generation': {
                 'inner_len': base_dead['inner_len'], 'text_content_len': base_dead['text_content_len'],
                 'details_blocks': base_dead.get('details_count', 'NOT_RECORDED_BY_THAT_PASS'),
                 'exception_in_text': base_dead.get('exception_in_text'),
                 'exception_in_attributes': base_dead.get('exception_in_attributes')},
             'walked_context_reading_that_I_DO_NOT_USE_AS_THE_NUMBER': {
                 'inner_len': c2_walked['painted_len'],
                 'carries_my_filled_wizard_values': True,
                 'why_it_is_confounded': 'the journey was walked first in this same browser context, so the '
                                         'persisted trial draft was painted instead of a clean shell; the length '
                                         'difference against the baseline is mine, not the product\'s'},
             'text_lines_that_actually_differ_from_the_baseline': changed_lines}},
     'new_on_this_generation': {
         'anchors_seen_after_the_press': c1['attribute_hits'],
         'anchor_names_that_ship_in_the_served_bundle': list(SCAN['anchor_literals_in_the_served_bundle'].keys()),
         'anchors_seen_before_the_press': SCAN['dom_side_readings']['anchors_seen_before_the_press'],
         'details_blocks_on_the_failure_screen': c1['details_count'],
         'details_blocks_on_a_clean_shell': FRESH['before_opening_details']['details_count'],
         'how_the_anchor_names_were_made_durable': 'read-only literal search over the exact asset bytes the shell '
                                                   'names, with byte offsets'},
     'instrument_faults_disclosed': [
         {'fault': 'my single allowed walk painted 287 characters at /journey/<dead id> and I nearly reported '
                   'that as a change',
          'signal_that_caught_it': 'the text carried 天津站 and CNY 3000, which only my own typing put there, and '
                                   'the baseline file shows 158 from a context that never filled the form',
          'what_i_did': 'a fresh-context navigation instrument was added and the confounded number is kept, '
                        'labelled, and not used as the reading'},
         {'fault': 'the walk computed the pre-press attribute scan and then dropped that field from its output, '
                   'and the follow-up DOM probe printed to console without writing bytes',
          'signal_that_caught_it': 'the only durable attribute record in the raw file is the post-press one, '
                                   'whose value hash is the placeholder string deferred_to_node_side',
          'what_i_did': 'substituted a GET-only bundle scan that names the anchor literals and their byte offsets '
                        'in the served asset, and marked the DOM pre-press field NOT_PERSISTED instead of '
                        'guessing it'},
         {'fault': 'my exposure word-list is case-insensitive, so it flags the anchor name trial-create-error for '
                   'containing the word error',
          'signal_that_caught_it': 'the hit\'s attribute is data-testid, a DOM contract hook, and its value has no '
                                   'exception text; the commander\'s own ruler reports 0 hits in attributes on the '
                                   'shell with 17 leak patterns',
          'what_i_did': 'reported both readings side by side and left the wording of Q71 to the arbiter rather '
                        'than grading my own regex'}],
     'boundaries': 'one journey walk on this generation as instructed; every other pass here is GET-only or a '
                   'single navigation with 0 clicks and 0 keystrokes; 0 product bytes changed; 0 writes to the '
                   'authoritative line; no ref pushed that is not mine; no demo/reset; _live.db and _preview.db '
                   'never opened; no credentials printed; the tunnel and :4782 untouched',
     }
d['judgments'] = {
    'his_cited_blob_resolves_to_the_bytes_i_read': recomputed == PROBE_BLOB,
    'his_artefact_carries_neither_asset_rows_nor_a_generation_field': bool(
        not cmdr.get('rows') and not any('generation' in k for k in cmdr.keys())),
    'the_mirror_tip_still_is_the_generation_he_named': mirror_sha == NEW_TIP,
    'the_mirror_has_moved_past_the_generation_i_was_told_to_use': bool(
        DRIFT['mirror_tip_read_now'] != NEW_TIP and (DRIFT['commits_ahead'] or 0) > 0),
    'the_pending_commits_reach_the_wizard_source': bool(DRIFT['touches_the_wizard_source']),
    'the_shell_serves_the_asset_he_named': NAMED_ASSET in (RC['binding']['asset_named_by_the_served_page'] or ''),
    'my_two_independent_gets_of_the_js_asset_agree_with_my_click_pass': bool(
        d['faces_i_read_myself_over_get']['js_row_equals_the_bytes_my_click_pass_hashed']
        and d['faces_i_read_myself_over_get']['js_row_equals_the_bytes_my_anchor_scan_hashed']),
    'B1_press_still_ends_without_a_journey': bool(c1['still_on_wizard'] and not c1['stored_journey_id']),
    'B1_leg_shape_unchanged_from_the_baseline': bool(
        now_leg.get('url') == base_leg.get('url') and now_leg.get('m') == base_leg.get('m')
        and now_leg.get('status') == base_leg.get('status')
        and now_leg.get('req_bytes') == base_leg.get('post_body_len')),
    'B1_sentences_word_for_word_unchanged': now_sent == base_sent,
    'B2_clean_shell_still_shows_no_journey_and_no_message_about_the_id': bool(
        not FRESH['after_opening_details']['exception_in_text']
        and any('还需要填写' in l for l in FRESH['after_opening_details']['tail_lines'])),
    'B2_shell_text_differs_from_the_baseline_by_exactly_one_line': sum(
        1 for l in changed_lines if l.startswith('+')) == 1 and sum(1 for l in changed_lines if
                                                                    l.startswith('-')) == 1,
    'B2_my_walked_number_was_confounded_by_my_own_context': bool(
        c2_walked['painted_len'] != FRESH['before_opening_details']['inner_len']
        and bool(FRESH['before_opening_details']['localStorage_keys'])),
    'nothing_reached_either_screen_as_exception_text': bool(
        not c1['exception_in_text_after_opening_details']
        and not c2_walked['exception_in_text_after_opening_details']
        and not FRESH['after_opening_details']['exception_in_text']),
    'the_failure_screen_that_quotes_a_status_code_carries_no_detail_block': bool(
        c1['details_count'] == 0 and 'HTTP 500' in ' '.join(now_sent))}
d['judgments_note'] = ('readings only; grading belongs to E. Each key above is a computation over the fields it '
                       'names, and the baseline it is compared against is the stored previous-generation file, '
                       'not my recollection')
(OUT / 'r5_recheck_scored.json').write_text(json.dumps(d, ensure_ascii=False, indent=1),
                                            encoding='utf-8', newline='\n')
print(json.dumps(d['judgments'], ensure_ascii=False, indent=1))
print('changed lines:', json.dumps(changed_lines, ensure_ascii=False))
print('faces:', json.dumps([{k: r[k] for k in ('path', 'http_status', 'bytes_received',
                                               'sha256_of_bytes_i_received')} for r in FACES['rows']],
                            ensure_ascii=False))
print('cmdr artefact:', d['commander_artefact_as_I_READ_IT']['schema'],
      '| rows:', d['commander_artefact_as_I_READ_IT']['carries_asset_rows'],
      '| generation field:', d['commander_artefact_as_I_READ_IT']['names_a_generation'])
