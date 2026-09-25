"""ORD-0300 C2 challenge - stage 4: derive every verdict from paired readings, one variable at a time.

The commander's word was: 同果 ≠ 同一发请求. So a leg only counts here when ONE token ties together the
proxy's audit line, the browser's own network stack and the app's own fetch resolution - never from a
look-alike card, never from two elapsed times that merely sit near each other.

Every boolean is computed from the arm files, including the guard table, which is read out of the four
source exports rather than typed in.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import re

BASE = pathlib.Path('D:/moodle/_hjp3_0300c2_0925')
SHEET = 'frontend/src/features/planning/PlanWithAiSheet.tsx'

# key -> arm file. One cell per paired run; the schedule is not mine to choose, so every real-500 run
# that produced per-leg tokens gets its own row instead of "the last one wins".
SPEC = [
    ('P1_controlled500_old_bundle', 'arm_old_old_origin500_C2-184534.json'),
    ('P2_controlled500_current_bundle', 'arm_new_new_origin500_C2-184551.json'),
    ('P3_controlled500_two_guards_reverted', 'arm_new_mut_origin500_C2-184607.json'),
    ('N1_transport_death_old_bundle', 'arm_old_old_abort_C2-184626.json'),
    ('N2_transport_death_current_bundle', 'arm_new_new_abort_C2-184300.json'),
    ('N3_transport_death_guards_reverted', 'arm_new_mut_abort_C2-184317.json'),
    ('R1a_real500_landed_on_agent_commands', 'arm_old_old_lock_C2-184018.json'),
    ('R1b_real500_landed_on_plans_generate', 'arm_old_old_lock_C2-184643.json'),
    ('R2_real500_current_tip', 'arm_new_new_lock_C2-184736.json'),
    ('R3_real500_generation_the_cell_was_born_on', 'arm_t90_t90_lock_C2-191014.json'),
    ('R4_lock_released_before_any_500', 'arm_new_new_lock_C2-184112.json'),
    ('R5_lock_released_before_any_500_guards_reverted', 'arm_new_mut_lock_C2-184205.json'),
]


def load(fname):
    return json.loads((BASE / fname).read_text(encoding='utf-8'))


def card_of(a):
    s = a['screen']
    return {
        'result_status': s.get('cross_check_data_result_status'),
        'card_text': s.get('result_card_painted'),
        'network_words_painted': bool(s.get('network_card_painted')),
        'server_failure_words_painted': bool(s.get('http500_card_painted')),
        'detail_regions_in_dom': s.get('details_elements_present'),
        'reason_label_painted': s.get('reason_label_painted'),
        'reason_value_painted': s.get('reason_value_painted'),
    }


def legs_of(a, tip_backend):
    """Per write leg: the three witnesses and the verdict that they describe ONE request."""
    out = []
    for l in a['pairing']['write_legs']:
        tok = l.get('token')
        b_tok = (l.get('browser_stack_saw') or {}).get('pair_token')
        a_tok = (l.get('app_read_the_body') or {}).get('pair_token')
        out.append({
            'leg': l.get('leg'),
            'leg_tail': (l.get('leg') or '').split('/', 1)[1] if '/' in (l.get('leg') or '') else '',
            'token': tok,
            'proxy_lines_with_this_token': l.get('proxy_lines_with_this_token'),
            'reached_upstream': l.get('reached_upstream'),
            'upstream_status': l.get('upstream_status'),
            'upstream_bytes': l.get('upstream_bytes'),
            'upstream_content_type': l.get('upstream_content_type'),
            'upstream_body_head': l.get('upstream_body_head'),
            'upstream_elapsed_ms': l.get('upstream_elapsed_ms'),
            'page_saw_status': l.get('page_saw_status'),
            'page_saw_ok': l.get('page_saw_ok'),
            'page_fetch_rejected': l.get('page_fetch_rejected'),
            'page_reject': l.get('page_reject'),
            'page_elapsed_ms': l.get('page_elapsed_ms'),
            'browser_stack_status': (l.get('browser_stack_saw') or {}).get('status'),
            'browser_stack_failure': (l.get('browser_stack_saw') or {}).get('failure'),
            'token_echoed_by_the_answer': b_tok,
            'token_read_by_the_app_itself': a_tok,
            # the pairing the challenge asked for: one id, seen identically by three independent readers,
            # and exactly one server-side line carrying it
            'one_request_one_id': bool(tok and l.get('proxy_lines_with_this_token') == 1
                                        and b_tok == tok and a_tok == tok),
            'arrived_at_the_page': bool(l.get('page_saw_status') is not None
                                        and not l.get('page_fetch_rejected')),
            'body_read_and_json_parse_threw': bool(l.get('app_body_parse_failed')),
            'app_parse_error_name': (l.get('app_read_the_body') or {}).get('error_name'),
        })
    return out


def who_answered(leg, proxy_mode):
    if not leg['reached_upstream'] and (leg['proxy_lines_with_this_token'] or 0) == 0:
        return 'nobody - the leg was killed in the browser before any answer existed'
    if leg['reached_upstream']:
        return 'the product backend itself (the proxy only witnessed it)'
    return ('my pairing proxy answered it byte-for-byte in the shape the product uses '
            '(21 B text/plain "Internal Server Error"), no upstream call')


def guard_shape(which):
    """Count the guard shapes out of the export I measured on - never typed in by hand."""
    p = BASE / ('snap_%s' % which) / SHEET
    txt = p.read_text(encoding='utf-8')
    lines = txt.splitlines()
    unguarded = [i + 1 for i, t in enumerate(lines) if re.search(r'unknown \}\)\.detail', t)]
    guarded = [i + 1 for i, t in enumerate(lines) if re.search(r'\| null\)\?\.detail', t)]
    note = [i + 1 for i, t in enumerate(lines) if 'no readable answer reached this device' in t]
    return {
        'path': SHEET, 'sha1_blob_like_hash': hashlib.sha1(
            b'blob %d\0' % len(txt.encode('utf-8')) + txt.encode('utf-8')).hexdigest(),
        'lines_total': len(lines),
        'unguarded_detail_reads': len(unguarded), 'unguarded_at_lines': unguarded,
        'guarded_detail_reads': len(guarded), 'guarded_at_lines': guarded,
        'device_note_present': len(note) >= 1, 'device_note_at_lines': note,
    }


def source_diff(wh1, wh2):
    """Line-level difference between two exports, so 'only those two lines' is a reading, not a claim."""
    t1 = (BASE / ('snap_%s' % wh1) / SHEET).read_text(encoding='utf-8').splitlines()
    t2 = (BASE / ('snap_%s' % wh2) / SHEET).read_text(encoding='utf-8').splitlines()
    diff = [{'line': i + 1, wh1: t1[i], wh2: t2[i]} for i in range(min(len(t1), len(t2))) if t1[i] != t2[i]]
    return {'compared': '%s vs %s of %s' % (wh1, wh2, SHEET), 'lines_that_differ': [d['line'] for d in diff],
            'lines_total_%s' % wh1: len(t1), 'lines_total_%s' % wh2: len(t2), 'text': diff}


A = {}
out = {'order': 'ORD-0300 C2 challenge - same-request pairing instead of same-outcome',
       'lane': 'HJ-P3 aad2d1f2',
       'asked_in': 'commander 494abfd7, this session 18:1x+08: 同果 ≠ 同一发请求；要么 ① 服务端把那一发的编号回显、'
                   '要么 ② 让页面自己的 fetch 过一个会记状态码的本地代理；两项都做不到就改名 '
                   'UI_FETCH_DIED_AT_TRANSPORT_AFTER_~32s 并把旧名标 SUPERSEDED_BY_EVIDENCE，'
                   '另保留 NETWORK 分支不渲染技术详情这条产品事实',
       'cells': {}, 'derived': {}, 'runs_excluded': []}

for key, fname in SPEC:
    p = BASE / fname
    if not p.exists():
        out['cells'][key] = {'ran': False}
        continue
    a = load(fname)
    lg = legs_of(a, a['tip_backend'])
    fifties = [l for l in lg if (l['upstream_status'] or 0) >= 500]
    c = {'ran': True, 'file': fname, 'arm': a['arm'], 'run_id': a['run_id'],
         'intent_declared_before_running': a['intent_declared_before'],
         'backend_tip': a['tip_backend'], 'bundle_source_tip': a['tip_bundle_source'],
         'bundle_asset': a['bundle']['asset'], 'bundle_sha256': a['bundle']['sha256_64_hex'],
         'scenario': a['mode'], 'proxy_mode_declared': a['rig'].get('proxy_mode_declared'),
         'proxy_mode_matches_plan': a['rig'].get('proxy_mode_matches_plan'),
         'journey_id': a['rig'].get('journey_id'), 'db': a['rig'].get('db'),
         'backend_ownership_two_sided': a['rig'].get('identity_two_sided'),
         'waited_ms': a['waited_ms'], 'card': card_of(a), 'write_legs': lg,
         'legs_that_arrived_with_a_5xx': [l['leg_tail'] for l in fifties
                                         if l['one_request_one_id'] and l['arrived_at_the_page']],
         'any_leg_paired': any(l['one_request_one_id'] for l in lg),
         'proxy_lines_recorded_in_this_arm': a.get('proxy_lines_in_this_arm'),
         'page_errors': a.get('page_errors')}
    if fifties:
        c['who_answered_the_5xx'] = who_answered(fifties[0], c['proxy_mode_declared'])
        c['pairing_of_the_5xx_leg'] = {k: fifties[0][k] for k in
                                      ('token', 'token_echoed_by_the_answer', 'token_read_by_the_app_itself',
                                       'proxy_lines_with_this_token', 'page_saw_status', 'page_elapsed_ms',
                                       'upstream_status', 'upstream_elapsed_ms', 'browser_stack_status',
                                       'body_read_and_json_parse_threw', 'app_parse_error_name')}
    out['cells'][key] = c

# the three early runs on the old tip were taken before the per-leg token existed (single-leg shape)
for p in sorted(BASE.glob('arm_old_old_lock_C2-18*.json')):
    if p.name in [f for _, f in SPEC]:
        continue
    a = load(p.name)
    out['runs_excluded'].append({
        'file': p.name, 'arm': a['arm'],
        'reason': 'its `pairing` block has no `write_legs`, so it records one leg only - superseded inside '
                  'this batch by the per-leg token capture',
        'pairing_keys': sorted(a.get('pairing', {})), 'card': card_of(a)})

C = out['cells']


def cell(k):
    return C.get(k, {})


def fifty(k):
    c = cell(k)
    for l in c.get('write_legs', []):
        if (l['upstream_status'] or 0) >= 500:
            return l
    return {}


def card(k):
    return cell(k).get('card', {})


def paired_arrival(k):
    l = fifty(k)
    return bool(l and l['one_request_one_id'] and l['arrived_at_the_page'])


ran = [k for k in C if cell(k).get('ran')]
D = out['derived']
source_diff_new_vs_mut = source_diff('new', 'mut')

# ---- 1. the two routes the commander named, both taken -------------------------------------------
D['route_2_page_own_fetch_read_the_status_code'] = all(paired_arrival(k) for k in [
    'P1_controlled500_old_bundle', 'P2_controlled500_current_bundle', 'P3_controlled500_two_guards_reverted',
    'R1a_real500_landed_on_agent_commands', 'R1b_real500_landed_on_plans_generate',
    'R2_real500_current_tip', 'R3_real500_generation_the_cell_was_born_on'])
D['route_1_one_id_seen_by_three_independent_readers'] = all(
    fifty(k)['token'] == fifty(k)['token_echoed_by_the_answer'] == fifty(k)['token_read_by_the_app_itself']
    and fifty(k)['proxy_lines_with_this_token'] == 1 for k in [
        'P1_controlled500_old_bundle', 'R1a_real500_landed_on_agent_commands',
        'R2_real500_current_tip', 'R3_real500_generation_the_cell_was_born_on'])
D['the_answer_was_read_by_the_app_and_json_parse_threw_inside_it'] = all(
    fifty(k)['body_read_and_json_parse_threw'] and fifty(k)['app_parse_error_name'] == 'SyntaxError'
    for k in ('P1_controlled500_old_bundle', 'R1a_real500_landed_on_agent_commands'))

# ---- 2. the challenged cell, at the leg level, off the real product -------------------------------
D['the_real_product_answered_500_on_the_agent_commands_leg'] = bool(
    fifty('R1a_real500_landed_on_agent_commands')['leg_tail'] == 'agent/commands'
    and fifty('R1a_real500_landed_on_agent_commands')['reached_upstream'])
D['that_same_leg_is_the_one_the_page_saw'] = bool(
    fifty('R1a_real500_landed_on_agent_commands')['page_saw_status'] == 500
    and not fifty('R1a_real500_landed_on_agent_commands')['page_fetch_rejected'])
D['the_card_that_arm_painted_is_the_one_the_challenge_called_into_question'] = bool(
    card('R1a_real500_landed_on_agent_commands')['result_status'] == 'NETWORK'
    and card('R1a_real500_landed_on_agent_commands')['network_words_painted']
    and card('R1a_real500_landed_on_agent_commands')['detail_regions_in_dom'] == 0)
D['the_reproduction_is_on_the_tip_the_commander_named'] = bool(
    cell('R1a_real500_landed_on_agent_commands')['backend_tip']
    == 'dc964086c9d412573ac19d70b24b30e6c3ee6168')
D['and_the_server_side_body_is_the_contentless_21_byte_one'] = bool(
    fifty('R1a_real500_landed_on_agent_commands')['upstream_bytes'] == 21
    and fifty('R1a_real500_landed_on_agent_commands')['upstream_body_head'] == 'Internal Server Error')

# ---- 3. what the schedule did, honestly -----------------------------------------------------------
real_locks = ['R1a_real500_landed_on_agent_commands', 'R1b_real500_landed_on_plans_generate',
              'R2_real500_current_tip', 'R3_real500_generation_the_cell_was_born_on']
D['which_leg_the_real_product_answered_with_a_500'] = {k: fifty(k)['leg_tail'] for k in real_locks}
D['the_leg_that_eats_the_real_500_varies_between_runs_on_one_tip'] = bool(
    len({fifty(k)['leg_tail'] for k in
         ('R1a_real500_landed_on_agent_commands', 'R1b_real500_landed_on_plans_generate')}) == 2)
D['on_the_generation_the_cell_was_born_on_my_paired_run_answered_on_a_different_leg'] = bool(
    fifty('R3_real500_generation_the_cell_was_born_on')['leg_tail'] == 'plans/generate'
    and card('R3_real500_generation_the_cell_was_born_on')['result_status'] != 'NETWORK')
D['no_lock_run_painted_a_card_that_names_the_5xx_status_or_the_leg'] = all(
    str(fifty(k)['upstream_status']) not in (card(k).get('card_text') or '')
    and fifty(k)['leg_tail'] not in (card(k).get('card_text') or '') for k in real_locks)
# the published pair cannot be retro-paired: read the original cell and show it carries no request id
ORIG = json.loads((pathlib.Path('D:/moodle/_hjp3_0300_0925') / 'RECEIPT_O0300-2610.json')
                  .read_text(encoding='utf-8'))
oc2 = [x for x in ORIG['cells'] if x['id'] == 'C2_screen_side_attribution_of_that_same_answer'][0]
oc1 = [x for x in ORIG['cells'] if x['id'].startswith('C1_')][0]
D['the_original_pair_in_the_published_cell_is_still_not_retro_pairable'] = bool(
    not re.search(r'token|request_id|pair|trace', json.dumps(oc2['measured'], ensure_ascii=False))
    and 'elapsed_ms' in json.dumps(oc1['measured']) and 'elapsed_ms' in json.dumps(oc2['measured']))
D['the_original_cell_named_this_leg'] = {
    'server_side_url_tail_in_C1': [a['url_tail'] for a in oc1['measured']['arms']],
    'server_side_status': [a['http_status'] for a in oc1['measured']['arms']],
    'server_side_elapsed_ms': [a['elapsed_ms'] for a in oc1['measured']['arms']],
    'screen_side_status_in_C2': oc2['measured']['cross_check_data_result_status'],
    'screen_side_detail_regions': oc2['measured']['detail_regions_in_dom'],
    'screen_side_uninstrumented_appeared_after_ms':
        oc2['measured']['reproduced_without_any_instrument']['appeared_after_ms'],
    'measured_on': oc2['measured_on']}

# ---- 4. the mechanism, one variable ---------------------------------------------------------------
D['old_bundle_paints_the_unreachable_card_on_an_arrived_500'] = bool(
    card('P1_controlled500_old_bundle')['result_status'] == 'NETWORK'
    and card('P1_controlled500_old_bundle')['detail_regions_in_dom'] == 0)
D['current_bundle_paints_the_server_failure_card_for_the_same_answer'] = bool(
    card('P2_controlled500_current_bundle')['result_status'] == 'HTTP_500'
    and card('P2_controlled500_current_bundle')['detail_regions_in_dom'] >= 1)
D['reverting_only_those_two_lines_puts_the_unreachable_card_back'] = bool(
    card('P3_controlled500_two_guards_reverted')['result_status'] == 'NETWORK'
    and card('P3_controlled500_two_guards_reverted')['network_words_painted'])
D['the_two_bundles_differ_only_by_those_two_lines'] = bool(
    source_diff_new_vs_mut['lines_that_differ'] == [147, 155]
    and guard_shape('new')['guarded_detail_reads'] == 2
    and guard_shape('new')['unguarded_detail_reads'] == 0
    and guard_shape('mut')['unguarded_detail_reads'] == 2
    and guard_shape('mut')['guarded_detail_reads'] == 0
    and guard_shape('mut')['device_note_present'] == guard_shape('new')['device_note_present'])
D['source_lines_that_differ_between_the_current_bundle_and_the_mutant'] = source_diff_new_vs_mut
D['same_answer_three_bundles_three_card_shapes'] = bool(
    len({(card(k)['result_status'], card(k)['detail_regions_in_dom'])
         for k in ('P1_controlled500_old_bundle', 'P2_controlled500_current_bundle',
                   'P3_controlled500_two_guards_reverted')}) == 3
    and len({fifty(k)['upstream_status'] for k in ('P1_controlled500_old_bundle',
                                                   'P2_controlled500_current_bundle',
                                                   'P3_controlled500_two_guards_reverted')}) == 1
    and len({fifty(k)['upstream_bytes'] for k in ('P1_controlled500_old_bundle',
                                                  'P2_controlled500_current_bundle',
                                                  'P3_controlled500_two_guards_reverted')}) == 1)
D['the_current_authority_tip_backend_is_the_same_bytes_for_the_mutant_arm'] = bool(
    cell('P2_controlled500_current_bundle')['backend_tip']
    == cell('P3_controlled500_two_guards_reverted')['backend_tip'])

# ---- 5. the negative control: the card alone is not evidence --------------------------------------
D['a_true_transport_death_paints_the_identical_card_on_the_old_bundle'] = bool(
    card('N1_transport_death_old_bundle')['result_status']
    == card('P1_controlled500_old_bundle')['result_status']
    and card('N1_transport_death_old_bundle')['card_text'] == card('P1_controlled500_old_bundle')['card_text']
    and card('N1_transport_death_old_bundle')['detail_regions_in_dom'] == 0)
D['the_transport_death_leg_has_no_server_side_line_at_all'] = bool(
    all(l['proxy_lines_with_this_token'] == 0 and l['page_fetch_rejected']
        for l in cell('N1_transport_death_old_bundle')['write_legs']))
D['what_separates_the_two_is_the_pairing_not_the_card'] = bool(
    paired_arrival('P1_controlled500_old_bundle')
    and not any(l['one_request_one_id'] for l in cell('N1_transport_death_old_bundle')['write_legs']))
D['the_negative_control_is_mine_not_the_products'] = bool(
    cell('N1_transport_death_old_bundle')['scenario'] == 'abort'
    and all(l['page_reject'] and 'Failed to fetch' in l['page_reject']
            and l['browser_stack_failure'] == 'net::ERR_FAILED'
            for l in cell('N1_transport_death_old_bundle')['write_legs']))

# ---- 6. the product fact the commander says matters more ------------------------------------------
D['old_network_branch_renders_no_technical_detail'] = bool(
    all(card(k)['detail_regions_in_dom'] == 0 for k in
        ('P1_controlled500_old_bundle', 'N1_transport_death_old_bundle',
         'R1a_real500_landed_on_agent_commands')))
D['current_branch_network_card_does_render_a_device_note'] = bool(
    card('N2_transport_death_current_bundle')['network_words_painted']
    and card('N2_transport_death_current_bundle')['detail_regions_in_dom'] >= 1)
# the same DOM count shows up whether or not an answer arrived, so this fact does not lean on the pairing
D['the_no_detail_fact_holds_with_and_without_a_paired_arrival'] = bool(
    card('P1_controlled500_old_bundle')['detail_regions_in_dom'] == 0
    and card('N1_transport_death_old_bundle')['detail_regions_in_dom'] == 0
    and card('R1a_real500_landed_on_agent_commands')['detail_regions_in_dom'] == 0)

# ---- 7. the guard table, counted out of the four exports -------------------------------------------
D['guard_shape_read_from_the_three_generations'] = {w: guard_shape(w) for w in
                                                   ('old', 'new', 'mut', 't90')}

# ---- 8. the disposition the challenge asks for -----------------------------------------------------
D['lifted_from_unproven_on_the_named_tip'] = bool(
    D['the_real_product_answered_500_on_the_agent_commands_leg']
    and D['that_same_leg_is_the_one_the_page_saw']
    and D['the_card_that_arm_painted_is_the_one_the_challenge_called_into_question']
    and D['the_reproduction_is_on_the_tip_the_commander_named']
    and D['and_the_server_side_body_is_the_contentless_21_byte_one']
    and D['route_1_one_id_seen_by_three_independent_readers']
    and D['route_2_page_own_fetch_read_the_status_code'])
BOOLS = [k for k, v in D.items() if isinstance(v, bool)]
D['challenged_cell_disposition'] = {
    'old_cell_id': 'C2_screen_side_attribution_of_that_same_answer',
    'old_verdict': 'SERVER_ANSWERED_BUT_SCREEN_SAYS_UNREACHABLE',
    'old_measured_on': '90d29a172e186aab6e6cb138ab4583ccf93bfa68',
    'why_it_was_open': 'the pair 32330 ms (server) / 32762 ms (screen) rested on the scene, not on one request',
    'pairing_routes_achieved': ['① one token minted by my proxy on the server side, echoed back in the answer '
                                'header and read there by the browser stack and by the app own fetch',
                                '② the page own fetch crossed a proxy that records the status code per leg'],
    'lifted_from_unproven_on_the_named_tip': D['lifted_from_unproven_on_the_named_tip'],
    'new_cell_name': 'C2b_SERVER_ANSWERED_500_ON_THE_SAME_LEG_THE_PAGE_PAINTS_UNREACHABLE_paired_by_one_token',
    'old_name_marked': 'SUPERSEDED_BY_EVIDENCE - the 90d29a17 pair itself is still unpaired (my one paired '
                       'run on that generation put the 500 on plans/generate and painted a different card), '
                       'and the claim is re-made on dc964086 with a per-request id',
    'rename_to_UI_FETCH_DIED_AT_TRANSPORT_AFTER_~32s_needed': bool(
        not D['lifted_from_unproven_on_the_named_tip']),
    'product_fact_kept_without_any_same_request_proof': 'the NETWORK branch renders no technical detail at all '
                                                        'on 90d29a17 and on dc964086 (0 <details> elements in '
                                                        'the DOM); the current tip renders a device note there'}

# ---- 9. bookkeeping, last, so the disposition is inside the count ----------------------------------
D['cells_ran'] = len(ran)
D['cells_expected'] = len(SPEC)
D['arms_that_did_not_run'] = [k for k in C if not cell(k).get('ran')]
BOOLS = [k for k, v in D.items() if isinstance(v, bool)]
D['booleans_required'] = len(BOOLS)
D['booleans_true'] = sum(1 for k in BOOLS if D[k])
D['ALL_REQUIRED_HOLD'] = bool(not D['arms_that_did_not_run'] and D['cells_ran'] == D['cells_expected']
                              and len(BOOLS) >= 20 and D['booleans_true'] == len(BOOLS))

(BASE / 'c2_score.json').write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding='utf-8',
                                    newline='\n')
print(json.dumps({'cells': {k: bool(cell(k).get('ran')) for k in C},
                  'which_leg_ate_the_real_500': D['which_leg_the_real_product_answered_with_a_500'],
                  'derived': {k: v for k, v in D.items() if isinstance(v, bool)},
                  'not_all': [k for k in BOOLS if not D[k]] if not D['ALL_REQUIRED_HOLD'] else [],
                  'excluded_runs': [r['file'] for r in out['runs_excluded']]},
                 ensure_ascii=False, indent=1))
print('\nwrote c2_score.json  (%d B)' % (BASE / 'c2_score.json').stat().st_size)
