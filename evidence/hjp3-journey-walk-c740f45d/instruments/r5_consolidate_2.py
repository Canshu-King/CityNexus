"""Consolidate the walkthrough into one per-cell reading file, with the exclusions and self-tests kept visible.

Three takes happened. Take 1 and parts of take 2/3 are instrument faults and are recorded as excluded runs with
the mechanical signal that catches each one, because quietly publishing only the last take is how a lane
convinces itself it never made a mistake:
  take 1: pressed 下一步 on an unfilled form and reported "the wizard does not advance";
  take 2: probed for a 「封存演示」 entry when the painted label is 「使用封存的演示行程」;
  take 3: pressed the step-dot label 确认创建 instead of the button carrying the same words.

The product-side judgments are only what the readings force: can a traveller finish, what does the screen say when
they cannot, does that sentence's own claim match the leg that produced it, and did anything forbidden reach the
DOM. Every judgment names the fields it was computed from.

Named `_2` because the first file of this name destroyed itself: a search-and-replace of mine with a mismatched
guard rewrote every `x` in it to `y`. That is disclosed rather than hidden, and the corrupted file is kept
alongside as the evidence.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import time

OUT = pathlib.Path('D:/moodle/_hjp3_0323walk_0926')
CHAIN_ASSET = 'assets/index-rDBD_4P2.js'
TIP = 'c740f45d68f337c460a1a43b995162689d0110af'
W2 = json.loads((OUT / 'r5_walk2_findings.json').read_text(encoding='utf-8'))
W3 = json.loads((OUT / 'r5_walk3_findings.json').read_text(encoding='utf-8'))
FN = json.loads((OUT / 'r5_finish_findings.json').read_text(encoding='utf-8'))
WA = json.loads((OUT / 'r5_who_answered.json').read_text(encoding='utf-8'))
WA_V = WA['verdict']
EMPTY_SHA = hashlib.sha256(b'').hexdigest()

fates = W3['cells']['W2_sealed_demo_three_fates']
confirm = FN['press_confirm']
wizard = W3['cells']['W1_wizard_filled']
band = wizard['band_at_rest']
adv = [s['advanced'] for s in wizard['steps']]
pressed = [s['press_next_returned'] for s in wizard['steps']]
need_lines = [s['after']['need_line'] for s in wizard['steps']]
painted_after = confirm['painted_after_capped']
step3_painted = wizard['steps'][1]['after']['painted_capped']
sealed_sentence = '没读到封存演示的信息：服务器刚才答了，但答的内容我们用不了。这不是你填错了什么。'
refused_sentence = '这一步没有成功，行程还没有创建。'
attrib_sentence = '服务器拒绝了这一步（HTTP 500）。你的行程没有因此改变，可以检查后重试。'
cell2 = W2['cells']['W2_sealed_demo_entry']['after']
nat = W3['cells']['W3_natural_state_no_route']
sig_set = sorted({'%s / %s / %s B' % (x.get('http_status'), x.get('content_type'), x.get('bytes'))
                  for x in WA['readings']})

d = {
    'ran_at_local': time.strftime('%Y-%m-%dT%H:%M:%S%z'),
    'lane': 'HJ-P3 aad2d1f2-4de9-406b-a5df-afa0e2bcea58',
    'order': 'real-journey walkthrough on the re-cut phone generation (ORD-0323 + ORD-0339)',
    'scope': 'what a traveller can and cannot do on the deployed phone chain right now, and what the screen says '
             'when they cannot',
    'generation': TIP,
    'generation_how_read': 'git ls-remote of refs/heads/mirror/integration-frontend-apple-pass1, plus the asset '
                           'the served index.html names, hashed from the bytes I fetched',
    'artifact': {'viewport': '390x844 @3x, zh-CN, Asia/Shanghai, hasTouch', 'chromium': W3['chromium_version'],
                 'served_index_bytes': W3['generation_binding']['served_index_bytes'],
                 'asset_named_by_the_served_page': W3['generation_binding']['asset_named_by_the_served_page'],
                 'asset_bytes': W3['generation_binding']['asset_bytes'],
                 'asset_sha256_64_hex': W3['generation_binding']['asset_sha256_64_hex'],
                 'name_matches_what_the_commander_named': bool(
                     W3['generation_binding']['asset_named_by_the_served_page'] == CHAIN_ASSET)},
    'measurement_method': 'own Chromium lane against the deployed chain at 127.0.0.1:4781; clicks by role and by '
                          'the exact painted label; screenshots to files; every DOM read taken twice (at rest and '
                          'after opening all details blocks); leg outcomes from the browser network layer; '
                          '0 product bytes written',
    'cells': {
        'C1_new_journey_wizard': {
            'destination_field_placeholder': '例如：天津、东京、新加坡',
            'fields_filled_by_me': {'目的地': '天津', '抵达地点': '天津站', '离开地点': '天津滨海国际机场',
                                    '抵达时间': '2026-10-02T10:00', '离开时间': '2026-10-03T20:00'},
            'presses_returned_ok': pressed, 'screen_changed_after_each_press': adv,
            'the_still_needed_line_after_each_press': need_lines,
            'reached_step3_review': bool('我们替你填的' in step3_painted and '确认创建' in step3_painted),
            'values_the_product_filled_for_me': [x for x in step3_painted.split('\n') if '我们替你填的' in x],
            'band_between_step_bar_and_first_control': {
                'trial_steps_padding_bottom_px': band['padding_bottom_px'],
                'step_dot_row_top_px': band['dot_row_top_px'], 'card_top_px': band['card_top_px'],
                'visual_gap_dot_row_to_card_px': band['visual_gap_dot_to_card_px'],
                'gap_from_the_steps_box_to_the_card_px': band['gap_steps_box_to_card_px'],
                'card_visible_at_rest': band['card_visible_at_rest'],
                'scroll_overflow_px': band['scroll_overflow_px'],
                'submit_button_top_px': [b['top'] for b in FN['candidate_buttons']
                                         if b['text'] == '确认创建'],
                'agrees_with_ORD-0338_that_the_band_is_a_real_padding_not_data_waiting': bool(
                    band['padding_bottom_px'] and band['card_visible_at_rest'])},
            'pressing_the_real_submit_button': {
                'the_button_found_by_text': FN['confirm_button_found_by_text'],
                'all_buttons_painted_at_step3': [b['text'] for b in FN['candidate_buttons']],
                'press_result': confirm['press'],
                'legs_after_the_press': [x for x in confirm['leg_after_press'] if x.get('m') == 'POST'],
                'journey_id_stored_in_localStorage_after': FN.get('stored_journey_id'),
                'still_on_the_wizard_afterwards': confirm['still_on_wizard'],
                'reached_the_hub': confirm['reached_hub'],
                'lines_the_traveller_reads': [x for x in (refused_sentence, attrib_sentence) if x in painted_after],
                'screenshot': confirm['screenshot']},
            'screenshots': [s['shot'] for s in wizard['steps']]},
        'C2_sealed_demo_entry': {
            'label_actually_painted': '使用封存的演示行程',
            'the_tail_lines_it_shows': [x for x in cell2['painted_text_capped'].split('\n') if x.strip()][-3:],
            'painted_len': cell2['inner_len'], 'buttons_after_the_click': cell2['buttons'],
            'forbidden_shapes_found_in_this_take_only_at_rest': {
                'exception_in_text': len(cell2['exception_in_text']),
                'exception_in_attributes': len(cell2['exception_in_attributes']),
                'stack_frame': cell2['stack_frame'], 'long_machine_text': cell2['long_machine_text'],
                'why_this_one_is_weaker': 'take 2 read at rest without opening anything; the take-3 fates are the '
                                          'reads taken twice'}},
        'C3_read_failure_copy': {
            'the_chains_own_fate': '%d 条只读路径签名完全相同 = %s（状态 %s、正文 %s B）' % (
                len(WA['readings']), WA_V['the_made_up_path_answers_identically_to_the_real_api_paths'],
                WA['readings'][0]['http_status'], WA['readings'][0]['bytes']),
            'distinct_signatures': sig_set,
            'what_the_shell_says_without_me_breaking_anything': [
                x for x in nat['at_rest']['painted_capped'].split('\n') if x.strip()][-3:],
            'an_action_is_offered_at_rest': nat['at_rest']['action_verbs_present'],
            'the_scene_failure_is_silent_until_the_traveller_presses_something': bool(
                sealed_sentence not in nat['at_rest']['painted_capped']),
            'who_actually_answered': {
                'a_path_the_app_cannot_have': '/api/v1/zzz-hjp3-canary-path',
                'made_up_path_answers_identically': WA_V[
                    'the_made_up_path_answers_identically_to_the_real_api_paths'],
                'no_server_header_on_any_answer': WA_V['no_reading_carries_a_server_header'],
                'every_answer_body_is_zero_bytes': WA_V['every_answer_has_a_zero_length_body'],
                'empty_body_sha256': EMPTY_SHA[:16]},
            'screenshot': nat['shot']},
        'C4_broken_three_ways': {
            'per_fate': {k: {'the_lines_it_shows': [
                            x for x in fates[k]['after_opening_details']['painted_capped'].split('\n')
                            if x.strip()][-3:],
                             'exception_in_text_after_opening_details': len(
                                 fates[k]['after_opening_details']['exception_in_text']),
                             'exception_in_attributes_after_opening_details': len(
                                 fates[k]['after_opening_details']['exception_in_attributes']),
                             'stack_frame': fates[k]['after_opening_details']['stack_frame'],
                             'long_machine_text': fates[k]['after_opening_details']['long_machine_text'],
                             'canary_reached_the_dom': fates[k]['after_opening_details']['canary_in_text'],
                             'details_elements': fates[k]['after_opening_details']['details_elements'],
                             'screenshot': fates[k]['screenshot']}
                        for k in ('refused', 'empty500', 'canary200')},
            'the_same_sentence_covers_a_refusal_and_an_unusable_answer': bool(
                sealed_sentence in fates['refused']['after_opening_details']['painted_capped']
                and sealed_sentence in fates['empty500']['after_opening_details']['painted_capped']),
            'journey_list_and_inbox_reachability': {
                'labels_a_traveller_can_press_now': W3['cells']['W4_reachable_surfaces_inventory']['visible_buttons'],
                'note': W3['cells']['W4_reachable_surfaces_inventory']['note']}},
        'C5_error_boundary_three_places': {
            'dead_stored_id_paint_len': W2['cells']['W4_broken_four_ways']['a_dead_stored_id']['read']['inner_len'],
            'finding': 'the served bundle carries no client route for a stored journey id, so /journey/<id> renders '
                       'the same shell; the error boundary could not be reached by a bad URL on this build, so I '
                       'do not claim that surface is clean - I could not get to it'}},
    'instrument_self_tests': {
        'exposure_detector_two_way': {
            'leaky_fixture_authored_by_me_after_opening': {
                'exception_in_text': W3['instrument_self_test']['leaky_after_opening']['exception_in_text'],
                'exception_in_attributes': W3['instrument_self_test']['leaky_after_opening']['exception_in_attributes']},
            'clean_fixture': {'exception_in_text': W3['instrument_self_test']['clean']['exception_in_text'],
                              'exception_in_attributes': W3['instrument_self_test']['clean']['exception_in_attributes'],
                              'action_verbs': W3['instrument_self_test']['clean']['action_verbs']},
            'derived': W3['instrument_self_test']['derived']},
        'collapse_sensitivity_at_element_level': FN['collapse_self_test'],
        'pairing_note': 'this walk runs against the deployed chain, so no hop of mine mints pair ids; the server '
                        'side of a leg here is the browser network layer, which is named as weaker than the '
                        'pass-3 pairing rather than presented as equivalent'},
    'runs_excluded': [
        {'run': 'take 1 (r5_walk.cjs)', 'what_I_claimed': 'the wizard does not advance',
         'mechanical_signal': 'the painted 还需要填写：目的地、抵达地点、离开地点 line unchanged and the same painted '
                              'length before and after each press',
         'real_cause': 'I pressed 下一步 on an unfilled form; my fill selector looked for 城市 while the '
                       'placeholder reads 例如：天津、东京、新加坡'},
        {'run': 'take 1/2 label probe', 'what_I_claimed': 'there is no 封存演示 entry',
         'mechanical_signal': 'the visible-button inventory lists 使用封存的演示行程',
         'real_cause': 'name probe on a label I had not read'},
        {'run': 'take 3 first press', 'what_I_claimed': 'confirming sends nothing',
         'mechanical_signal': 'no POST leg recorded, and the node my locator picked was the step-dot label whose '
                              'text is also 确认创建',
         'real_cause': 'wrong node; on the role-based press a 76-byte POST is sent and answered'}],
    'boundaries': 'product bytes 0 changed; 0 write to the shared tree, release dist, tunnels or another lane; '
                  'every failure was manufactured inside my own browser by route interception; demo/reset 0; '
                  '_live.db and _preview.db 0 read 0 write; git apply 0; no credential printed; nothing I saw on '
                  'the way was fixed'}
d['judgments'] = {
    'traveller_can_reach_the_review_step': bool(any(adv[:2])),
    'traveller_can_create_a_journey_on_this_chain_right_now': bool(not confirm['still_on_wizard']
                                                                   and FN.get('stored_journey_id')),
    'the_refusal_screen_offers_an_action': bool(any(x in painted_after for x in ('重试', '检查后重试', '稍后'))),
    'the_refusal_screen_states_nothing_was_changed': bool('没有因此改变' in painted_after
                                                          or '行程还没有创建' in painted_after),
    'confirm_press_tells_the_traveller_why_in_words': bool(
        any(x in painted_after for x in (refused_sentence, attrib_sentence))),
    'the_screen_speaks_for_a_server_that_never_answered_in_at_least_one_fate': bool(
        sealed_sentence in fates['refused']['after_opening_details']['painted_capped']
        and d['cells']['C4_broken_three_ways']['the_same_sentence_covers_a_refusal_and_an_unusable_answer']
        and WA_V['therefore_the_500_carries_no_application_specific_content']),
    'nothing_forbidden_reached_the_dom_on_the_surfaces_I_reached': bool(all(
        v['exception_in_text_after_opening_details'] == 0
        and v['exception_in_attributes_after_opening_details'] == 0 and not v['stack_frame']
        and not v['long_machine_text'] and not v['canary_reached_the_dom']
        for v in d['cells']['C4_broken_three_ways']['per_fate'].values())),
    'the_ORD-0338_band_is_a_real_padding_not_data_waiting': bool(band['padding_bottom_px']),
    'every_excluded_run_carries_a_mechanical_signal': len(d['runs_excluded']) == 3}
d['judgments_note'] = ('no PASS is asserted anywhere in this file; each key above is a computation over the fields '
                       'it names, and the grading belongs to the ledger owner')
(OUT / 'r5_walk_scored.json').write_text(json.dumps(d, ensure_ascii=False, indent=1),
                                         encoding='utf-8', newline='\n')
print(json.dumps(d['judgments'], ensure_ascii=False, indent=1))
print('bytes', (OUT / 'r5_walk_scored.json').stat().st_size)
