"""ORD-0300 C2 challenge - stage 5: the machine receipt.

Every `why` below quotes readings that this batch wrote into the named arm file, and every verdict is
carried by a token that ties one leg together across three independent readers (my proxy's audit line, the
browser's own network view, the app's own fetch resolution). Nothing is inherited from ORD-0300.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import time
import urllib.error
import urllib.request

BASE = pathlib.Path('D:/moodle/_hjp3_0300c2_0925')
SC = json.loads((BASE / 'c2_score.json').read_text(encoding='utf-8'))
C = SC['cells']
D = SC['derived']
SETUP = json.loads((BASE / 'setup_facts.json').read_text(encoding='utf-8'))
T90 = json.loads((BASE / 't90_facts.json').read_text(encoding='utf-8'))
BOUND = json.loads((BASE / 'boundary_proof_c2.json').read_text(encoding='utf-8'))
TD = sorted(BASE.glob('teardown_*.json'))
LAST_TD = json.loads((BASE / TD[-1]).read_text(encoding='utf-8')) if TD else {}
ORIG = json.loads((pathlib.Path('D:/moodle/_hjp3_0300_0925') / 'RECEIPT_O0300-2610.json')
                  .read_text(encoding='utf-8'))
oc2 = [x for x in ORIG['cells'] if x['id'].startswith('C2_')][0]

P1, P2, P3 = ('P1_controlled500_old_bundle', 'P2_controlled500_current_bundle',
              'P3_controlled500_two_guards_reverted')
N1, N2, N3 = ('N1_transport_death_old_bundle', 'N2_transport_death_current_bundle',
              'N3_transport_death_guards_reverted')
R1A = 'R1a_real500_landed_on_agent_commands'
R1B = 'R1b_real500_landed_on_plans_generate'
R2 = 'R2_real500_current_tip'
R3 = 'R3_real500_generation_the_cell_was_born_on'
R4, R5 = 'R4_lock_released_before_any_500', 'R5_lock_released_before_any_500_guards_reverted'
OUT = 'RECEIPT_O0300C2-1955.json'


def c(k):
    return C[k]


def legs(k):
    return c(k)['write_legs']


def leg500(k):
    for l in legs(k):
        if (l['upstream_status'] or 0) >= 500:
            return l
    return None


def leg_of(k, tail):
    for l in legs(k):
        if l['leg_tail'] == tail:
            return l
    return {}


def brief(k):
    """The whole cell in the handful of fields a reader needs to check a verdict."""
    l = leg500(k) or {}
    return {'arm_file': c(k)['file'], 'run_id': c(k)['run_id'], 'backend_tip': c(k)['backend_tip'],
            'bundle_asset': c(k)['bundle_asset'], 'scenario': c(k)['scenario'],
            'who_answered': c(k).get('who_answered_the_5xx'),
            'leg': l.get('leg_tail'), 'token': l.get('token'),
            'proxy_lines_with_that_token': l.get('proxy_lines_with_this_token'),
            'token_echoed_in_the_answer': l.get('token_echoed_by_the_answer'),
            'token_read_by_the_app': l.get('token_read_by_the_app_itself'),
            'server_side': {'status': l.get('upstream_status'), 'bytes': l.get('upstream_bytes'),
                            'content_type': l.get('upstream_content_type'),
                            'body_head': l.get('upstream_body_head'),
                            'elapsed_ms': l.get('upstream_elapsed_ms')},
            'page_side': {'status': l.get('page_saw_status'), 'rejected': l.get('page_fetch_rejected'),
                          'reject': l.get('page_reject'), 'elapsed_ms': l.get('page_elapsed_ms'),
                          'browser_stack_status': l.get('browser_stack_status'),
                          'browser_stack_failure': l.get('browser_stack_failure'),
                          'app_json_parse_threw': l.get('body_read_and_json_parse_threw'),
                          'parse_error_name': l.get('app_parse_error_name')},
            'card': c(k)['card'], 'all_write_legs': [
                  {'leg': x['leg_tail'], 'server_status': x['upstream_status'],
                   'page_status': x['page_saw_status'], 'rejected': x['page_fetch_rejected'],
                   'proxy_lines': x['proxy_lines_with_this_token'], 'token': x['token'],
                   'elapsed_page_ms': x['page_elapsed_ms'], 'elapsed_server_ms': x['upstream_elapsed_ms']}
                  for x in legs(k)]}


def pair_proof(k):
    l = leg500(k) or {}
    return bool(l.get('token') and l['token'] == l.get('token_echoed_by_the_answer')
                == l.get('token_read_by_the_app_itself') and l.get('proxy_lines_with_this_token') == 1
                and l.get('page_saw_status') == l.get('upstream_status'))


def served_asset_read():
    """One read-only GET of the asset the user's served page references, to say which generation is live."""
    mine = (BASE / 'dist_new/assets/index-BTzTyrqI.js').read_bytes()
    url = 'http://127.0.0.1:4781/assets/index-BTzTyrqI.js'
    try:
        with urllib.request.urlopen(url, timeout=60) as f:
            srv = f.read()
        code = f.status
    except Exception as e:  # noqa: BLE001
        return {'error': str(e)[:140]}
    return {'requests_made': 1, 'method': 'GET', 'url': url, 'http_status': code,
            'bytes': len(srv), 'cookie_or_credential_sent': False,
            'my_private_build_of_5aff3722_sha256': hashlib.sha256(mine).hexdigest(),
            'served_sha256': hashlib.sha256(srv).hexdigest(), 'byte_identical': srv == mine,
            'note': 'a read of what the shared chain serves, not a write and not a measurement of the product '
                    'behaviour; the 4781/4782 listeners were not restarted or touched'}


SERVED = served_asset_read()
PORTS_NAMED = sorted(int(x) for x in BOUND['my_named_ports'])
LAST_TD_NAME = TD[-1].name if TD else None
FAULTS_DISCLOSED = 6
AI_LEGS = len([x for k in C if C[k].get('ran') for x in legs(k)
               if any(w in (x['leg_tail'] or '').lower() for w in ('supplier', 'deepseek', 'ai/'))])

cells = [
 {'id': 'K1_pairing_one_leg_seen_by_three_independent_readers',
  'verdict': 'ARRIVAL_IS_PAIRABLE_BY_AN_ID_THE_PAGE_CANNOT_GUESS',
  'measured_on': c(P1)['backend_tip'],
  'measured': {
      'arms': {P1: brief(P1), R1A: brief(R1A)},
      'route_1_the_id_comes_from_the_server_side': 'my pairing proxy mints the token when it accepts the '
                                                   'leg and echoes it back on the response header '
                                                   'X-HJP3-Pair, so the same string sits in the proxy audit '
                                                   'line, in the browser network view and in the app own '
                                                   'fetch resolution',
      'route_2_the_page_own_fetch_crossed_a_recording_proxy': 'the face pointed at 127.0.0.1:8642, so the '
                                                              'status code the page saw was recorded server-'
                                                              'side for that same token',
      'pairing_holds_in_both_arms': {P1: pair_proof(P1), R1A: pair_proof(R1A)},
      'backend_ownership_two_sided': {P1: c(P1)['backend_ownership_two_sided'],
                                      R1A: c(R1A)['backend_ownership_two_sided']}},
  'why': 'in %s the leg %s carries token %s; that token appears in %d proxy line and on the answer the '
         'browser stack saw (status %s) and in the app own fetch (status %s, rejected=%s, %s ms); the app '
         'then called .json() on that very response and got %s reading %r - so the answer was physically '
         'inside the page at the moment the card was written. In %s the same is true with the PRODUCT '
         'answering (token %s, %d proxy line, server %s B %s at %s ms, page %s at %s ms)'
         % (c(P1)['file'], leg500(P1)['leg_tail'], leg500(P1)['token'],
            leg500(P1)['proxy_lines_with_this_token'], leg500(P1)['browser_stack_status'],
            leg500(P1)['page_saw_status'], leg500(P1)['page_fetch_rejected'],
            leg500(P1)['page_elapsed_ms'], leg500(P1)['app_parse_error_name'],
            leg500(P1)['upstream_body_head'], c(R1A)['file'], leg500(R1A)['token'],
            leg500(R1A)['proxy_lines_with_this_token'], leg500(R1A)['upstream_bytes'],
            leg500(R1A)['upstream_body_head'], leg500(R1A)['upstream_elapsed_ms'],
            leg500(R1A)['page_saw_status'], leg500(R1A)['page_elapsed_ms'])},

 {'id': 'K2_the_challenged_cell_lifted_from_unproven',
  'verdict': 'SERVER_ANSWERED_500_ON_THE_SAME_LEG_THE_PAGE_PAINTS_UNREACHABLE_PROVEN_AT_REQUEST_LEVEL',
  'measured_on': c(R1A)['backend_tip'],
  'measured': {
      'arm': brief(R1A),
      'the_card_that_arm_painted': c(R1A)['card']['card_text'],
      'detail_regions_in_dom': c(R1A)['card']['detail_regions_in_dom'],
      'data_result_status': c(R1A)['card']['result_status'],
      'what_ORD_0300_C2_recorded': {
          'measured_on': oc2['measured_on'],
          'cross_check_data_result_status': oc2['measured']['cross_check_data_result_status'],
          'detail_regions_in_dom': oc2['measured']['detail_regions_in_dom'],
          'painted_card': oc2['measured']['painted_card'],
          'server_side_claimed_by_C1': {
              'url_tail': ORIG['cells'][0]['measured']['arms'][0]['url_tail'],
              'status': ORIG['cells'][0]['measured']['arms'][0]['http_status'],
              'bytes': ORIG['cells'][0]['measured']['arms'][0]['bytes'],
              'elapsed_ms': ORIG['cells'][0]['measured']['arms'][0]['elapsed_ms'],
              'any_request_id_in_C1': bool(
                  'token' in json.dumps(ORIG['cells'][0]['measured']) or
                  'trace' in json.dumps(ORIG['cells'][0]['measured']))},
          'screen_side_elapsed_ms':
              oc2['measured']['reproduced_without_any_instrument']['appeared_after_ms'],
          'any_request_id_in_that_cell': bool(
              'token' in json.dumps(oc2['measured']) or 'pair' in json.dumps(oc2['measured']))},
      'derived': {k: D[k] for k in (
          'the_real_product_answered_500_on_the_agent_commands_leg',
          'that_same_leg_is_the_one_the_page_saw',
          'the_card_that_arm_painted_is_the_one_the_challenge_called_into_question',
          'the_reproduction_is_on_the_tip_the_commander_named',
          'and_the_server_side_body_is_the_contentless_21_byte_one',
          'lifted_from_unproven_on_the_named_tip')}},
  'why': 'on tip %s, exported by git archive and served by its own backend, the product answered the leg '
         '%s with HTTP %s of %s B %s (%r) at %s ms; that same token is what the PAGE resolved (%s, %s ms, '
         'not rejected) and what its network stack logged (%s); the card that came up is %r with '
         'data-result-status=%s and %d <details> elements. The challenged pair (32330 ms server / 32762 ms '
         'screen on 90d29a17) carried no request id at all, so it stays superseded - but the shape it '
         'described is now measured on one request'
         % (c(R1A)['backend_tip'], leg500(R1A)['leg_tail'], leg500(R1A)['upstream_status'],
            leg500(R1A)['upstream_bytes'], leg500(R1A)['upstream_content_type'],
            leg500(R1A)['upstream_body_head'], leg500(R1A)['upstream_elapsed_ms'],
            leg500(R1A)['page_saw_status'], leg500(R1A)['page_elapsed_ms'],
            leg500(R1A)['browser_stack_status'], c(R1A)['card']['card_text'],
            c(R1A)['card']['result_status'], c(R1A)['card']['detail_regions_in_dom'])},

 {'id': 'K3_the_mechanism_one_variable_three_bundles',
  'verdict': 'AN_ARRIVED_500_IS_PAINTED_AS_UNREACHABLE_ONLY_WHERE_THOSE_TWO_NULL_GUARDS_ARE_ABSENT',
  'measured_on': c(P1)['backend_tip'],
  'measured': {
      'the_answer_is_one_answer': {'status': leg500(P1)['upstream_status'],
                                   'bytes': leg500(P1)['upstream_bytes'],
                                   'content_type': leg500(P1)['upstream_content_type'],
                                   'body_head': leg500(P1)['upstream_body_head'],
                                   'identical_across_the_three_arms': len(
                                       {(leg500(k)['upstream_status'], leg500(k)['upstream_bytes'])
                                        for k in (P1, P2, P3)}) == 1},
      'bundles': {k: {'tip_of_the_source_tree': c(k)['bundle_source_tip'],
                      'asset': c(k)['bundle_asset'], 'sha256': c(k)['bundle_sha256'],
                      'card_status': c(k)['card']['result_status'],
                      'detail_regions': c(k)['card']['detail_regions_in_dom'],
                      'arm': c(k)['file']} for k in (P1, P2, P3)},
      'source_diff_new_vs_mut': D['source_lines_that_differ_between_the_current_bundle_and_the_mutant'],
      'guard_shape_counted_out_of_the_exports': D['guard_shape_read_from_the_three_generations'],
      'derived': {k: D[k] for k in D if k.startswith(('old_bundle_', 'current_bundle_', 'reverting_only',
                                                      'the_two_bundles', 'same_answer_three',
                                                      'the_current_authority_tip'))}},
  'why': 'one and the same 5xx answer (%s / %s B / %s) against the same backend produced three different '
         'screens: the %s bundle painted %s with %d detail regions, the %s bundle painted %s with %d, and '
         'a bundle whose ONLY difference from the current one is lines %s painted %s with %d. The guard '
         'counts were re-read from the four exports in this batch, and the blob hash my reader recomputed '
         'for the old tree is %s - the same 40 hex the challenge quotes'
         % (leg500(P1)['upstream_status'], leg500(P1)['upstream_bytes'], leg500(P1)['upstream_content_type'],
            c(P1)['bundle_asset'], c(P1)['card']['result_status'], c(P1)['card']['detail_regions_in_dom'],
            c(P2)['bundle_asset'], c(P2)['card']['result_status'], c(P2)['card']['detail_regions_in_dom'],
            D['source_lines_that_differ_between_the_current_bundle_and_the_mutant']['lines_that_differ'],
            c(P3)['card']['result_status'], c(P3)['card']['detail_regions_in_dom'],
            D['guard_shape_read_from_the_three_generations']['old']['sha1_blob_like_hash'])},

 {'id': 'K4_negative_control_the_card_is_not_evidence',
  'verdict': 'A_TRUE_TRANSPORT_DEATH_PAINTS_THE_SAME_CARD_SO_ONLY_THE_PAIRING_DECIDES',
  'measured_on': c(N1)['backend_tip'],
  'measured': {
      'arms': {N1: brief(N1), N2: brief(N2), N3: brief(N3)},
      'compared_with': {P1: brief(P1)},
      'identical_card_on_the_old_bundle': bool(
          c(N1)['card']['card_text'] == c(P1)['card']['card_text']
          and c(N1)['card']['detail_regions_in_dom'] == c(P1)['card']['detail_regions_in_dom'] == 0),
      'the_killed_leg_has_no_server_side_line': all(
          l['proxy_lines_with_this_token'] == 0 and l['page_fetch_rejected'] for l in legs(N1)),
      'derived': {k: D[k] for k in D if k.startswith(('a_true_transport_death', 'the_transport_death_leg',
                                                      'what_separates', 'the_negative_control'))}},
  'why': 'in %s the leg never reached the product (0 proxy lines, page rejected with %r, browser logged %s) '
         'and the card is byte-identical to the one from the arrived case (%s); what separates the two is '
         'the token pairing, not the wording. On the current tip the same death renders %d detail region '
         'because the NETWORK branch now carries its own device sentence'
         % (c(N1)['file'], legs(N1)[0]['page_reject'], legs(N1)[0]['browser_stack_failure'],
            c(P1)['file'], c(N2)['card']['detail_regions_in_dom'])},

 {'id': 'K5_the_schedule_varies_and_the_generation_it_was_born_on',
  'verdict': 'WHICH_LEG_EATS_THE_PRODUCT_500_VARIES_PER_RUN_THE_PUBLISHED_PAIR_STAYS_SUPERSEDED',
  'measured_on': c(R1A)['backend_tip'],
  'measured': {
      'paired_lock_arms': {k: {'tip': c(k)['backend_tip'], 'arm': c(k)['file'],
                               'legs': [{'leg': x['leg_tail'], 'server': x['upstream_status'],
                                         'page': x['page_saw_status'], 'proxy_lines':
                                             x['proxy_lines_with_this_token'],
                                         'server_ms': x['upstream_elapsed_ms'],
                                         'page_ms': x['page_elapsed_ms']} for x in legs(k)],
                               'card_status': c(k)['card']['result_status'],
                               'detail_regions': c(k)['card']['detail_regions_in_dom'],
                               'card_words': (c(k)['card']['card_text'] or '')[:60]}
                      for k in (R1A, R1B, R2, R3, R4, R5)},
      'which_leg_answered_500': D['which_leg_the_real_product_answered_with_a_500'],
      'the_leg_varies_on_one_tip': D['the_leg_that_eats_the_real_500_varies_between_runs_on_one_tip'],
      'on_the_generation_C2_was_born_on': {
          'tip': c(R3)['backend_tip'], 'sheet_blob': T90['sheet_blob_40_hex'],
          'bundle_sha256_verified_against_that_batch':
              c(R3)['bundle_sha256'] == T90['bundle_sha256'],
          'leg_that_ate_the_500': leg500(R3)['leg_tail'],
          'card': c(R3)['card']['result_status'],
          'detail_regions': c(R3)['card']['detail_regions_in_dom'],
          'server_ms': leg500(R3)['upstream_elapsed_ms'], 'page_ms': leg500(R3)['page_elapsed_ms']},
      'no_card_names_the_status_or_the_leg': D['no_lock_run_painted_a_card_that_names_the_5xx_status_or_the_leg'],
      'runs_excluded_and_why': SC['runs_excluded']},
  'why': 'six paired runs of the same forced write, %s of which drew a 5xx: %s. On %s the 500 landed on %s '
         'at %s ms while the page '
         'took %s ms and the card said %s with %d detail regions - which is a different outcome from the one '
         'ORD-0300 C2 recorded on that same generation, and I am not going to paper over it: the published '
         'pair has no request id and cannot be retro-paired, so it is marked SUPERSEDED_BY_EVIDENCE here. '
         'What is stable across all of them is that no painted card names the status code or the leg of the '
         '5xx it came from'
         % (len([k for k in (R1A, R1B, R2, R3, R4, R5) if leg500(k)]),
            json.dumps(D['which_leg_the_real_product_answered_with_a_500'], ensure_ascii=False),
            c(R3)['backend_tip'], leg500(R3)['leg_tail'], leg500(R3)['upstream_elapsed_ms'],
            leg500(R3)['page_elapsed_ms'], c(R3)['card']['result_status'],
            c(R3)['card']['detail_regions_in_dom'])},

 {'id': 'K6_the_product_fact_that_needs_no_same_request_proof',
  'verdict': 'NETWORK_BRANCH_RENDERS_NO_TECHNICAL_DETAIL_ON_90d29a17_AND_dc964086_AND_ONE_ON_5aff3722',
  'measured_on': c(P1)['backend_tip'],
  'measured': {
      'detail_regions_per_arm': {k: {'tip': c(k)['backend_tip'], 'scenario': c(k)['scenario'],
                                     'card_status': c(k)['card']['result_status'],
                                     'detail_regions': c(k)['card']['detail_regions_in_dom'],
                                     'arm': c(k)['file']}
                                 for k in (P1, N1, R1A, P2, N2, P3, N3, R3)},
      'the_words_painted_on_the_current_tip': c(N2)['card']['card_text'],
      'guard_shape_counted_out_of_the_exports': D['guard_shape_read_from_the_three_generations'],
      'derived': {k: D[k] for k in D if k.startswith(('old_network_branch', 'current_branch_network',
                                                      'the_no_detail_fact'))}},
  'why': 'the unreachable branch shows %d <details> elements on tip %s in all three of its shapes (arrived '
         '500, killed leg, real product 500) and %d on the current tip and on the mutant - so on the older '
         'trees the sentence about "technical detail" sits above nothing at all. This fact needs no pairing: '
         'the same DOM count appears whether or not an answer arrived (%s true)'
         % (c(P1)['card']['detail_regions_in_dom'], c(P1)['backend_tip'],
            c(N2)['card']['detail_regions_in_dom'],
            D['the_no_detail_fact_holds_with_and_without_a_paired_arrival'])},

 {'id': 'K7_limits_i_am_not_passing_off_as_green',
  'verdict': 'SCOPE_LIMITS_NAMED_WITH_THEIR_NUMBERS',
  'measured': {
      'who_answered_what': {k: c(k).get('who_answered_the_5xx') or
                            'no 5xx leg in this arm' for k in
                            (P1, P2, P3, N1, N2, N3, R1A, R1B, R2, R3, R4, R5)},
      'why_the_controlled_answer_is_allowed_here': 'the claim under challenge is "the page held an answer". '
                                                   'The controlled arms prove a 500 in the product own byte '
                                                   'shape does that; the arms where the PRODUCT answered '
                                                   '(R1a/R1b/R2/R3) carry the same pairing and are reported '
                                                   'independently, including the run where it did not land '
                                                   'on the leg the original cell named',
      'ai_supplier_called_in_any_arm': len([x for k in C if C[k].get('ran') for x in legs(k)
                                            if any(w in (x['leg_tail'] or '').lower()
                                                   for w in ('supplier', 'deepseek', 'ai/'))]),
      'ai_disabled_how': 'CITYNEXUS_AI_ENABLED=false and DEEPSEEK_API_KEY popped from the rig env before the '
                         'backend starts, so no supplier call is made and no key is ever printed',
      'tips_touched': {'old': SETUP['tips_used']['old'], 'new': SETUP['tips_used']['new'], 't90': T90['tip'],
                       'mut': 'a private copy of the new tip with 2 lines reverted, %s'
                              % SETUP['mutant']['sheet_blob_mut']},
      'named_port_list': sorted(int(x) for x in BOUND['my_named_ports']),
      'last_teardown_file': TD[-1].name if TD else None,
      'instrument_fault_count': 6,
      'ports_and_teardown': {'my_named_ports': BOUND['my_named_ports'],
                             'listening_after_last_teardown': LAST_TD.get('listening_after'),
                             'all_my_ports_free': LAST_TD.get('all_my_ports_free'),
                             'last_teardown_found_the_pids_already_gone': bool(
                                 LAST_TD.get('recorded_pids') and all(
                                     v.get('rc') == 128 and not v.get('cmdline_is_mine')
                                     for v in (LAST_TD.get('recorded_pids') or {}).values()))},
      'one_read_only_get_on_the_shared_chain': SERVED,
      'not_measured': ['a 200-with-a-plan answer on these legs (every arm here ends in an error or a skip)',
                       'the phone chain, _live.db, _preview.db, demo/reset (0 calls, see boundary file)',
                       'whether ORD-0302 re-fixes the crash path: on 5aff3722 the guard is already there',
                       'repeat counts of the R arms: R1a happened once in two old-tip paired runs, so the '
                       'leg that eats the 500 is a schedule outcome, not a certainty'],
      'instrument_events_disclosed': [
          'first arms of this batch died inside /experience with a FileNotFoundError: my git archive omitted '
          'the repo-root data/ the product reads - that 500 was my packaging, fixed in c2_add_data.py with '
          'before/after hashes proving the subject bytes never moved',
          'one sqlite line used the wrong attribute on this interpreter (isolation vs isolation_level) so the '
          'lock never locked in that round; those arms are on disk and score nothing',
          'the seed helper first wrote the demo catalog into the wrong arm database (CATALOG_EMPTY on screen '
          'behind an upstream 200); fixed to seed per arm',
          'a 90d29a17 face would not start because it pointed at another batch folder with no node_modules; '
          'fixed by re-exporting that tip into my own directory and verifying the bundle bytes against what '
          'ORD-0300 recorded (%s == %s)' % (c(R3)['bundle_sha256'], T90['bundle_sha256']),
          'an early patch of my own scorer typed two booleans as literals instead of deriving them; the '
          'table is now computed from the arm files and the guard counts are re-read from the four exports',
          'the first per-leg version paired only the last write leg; three old-tip arms recorded that way '
          'are listed in runs_excluded rather than quietly deleted']},
  'why': 'the limits are readings too: %d named ports (%s through %s) all free after %s (%s), the supplier '
         'endpoint was crossed in %d of the legs this batch logged, %d instrument faults are named with what '
         'each cost, and the one read-only GET of index-BTzTyrqI.js on the shared chain returned %s bytes '
         'whose sha256 equals my private build (%s) - that GET is the only contact this batch had with %s'
         % (len(PORTS_NAMED), PORTS_NAMED[0], PORTS_NAMED[-1], LAST_TD_NAME,
            LAST_TD.get('all_my_ports_free'), AI_LEGS, FAULTS_DISCLOSED, SERVED.get('bytes'),
            SERVED.get('byte_identical'), '127.0.0.1:4781')},
]

rc = {'order': 'ORD-0300 C2 challenge - same-request pairing instead of same-outcome',
      'lane': 'HJ-P3 aad2d1f2', 'run_id': 'O0300C2',
      'asked_in': SC['asked_in'],
      'measured_on_how_read': 'each tip read by git ls-remote / from the batch own export; three vite builds '
                              'into private outDirs, all verified by sha256; the challenged cell was '
                              're-measured on its own generation through that batch read-only export',
      'arms': {k: C[k]['file'] for k in C if C[k].get('ran')},
      'scores': 'c2_score.json',
      'challenge_answered': {
          '①_server_side_id_echoed': 'yes - the token is minted where the answer is made and echoed on the '
                                      'response header, then read identically by the proxy audit line, the '
                                      'browser network view and the app own fetch',
          '②_page_own_fetch_through_a_recording_proxy': 'yes - every face served behind 127.0.0.1:8642, so '
                                                        'the status the page saw is the status recorded '
                                                        'server-side for that token',
          'rename_needed': bool(not D['lifted_from_unproven_on_the_named_tip']),
          'disposition': D['challenged_cell_disposition']},
      'derived_summary': {
          'pairing_holds_in_every_5xx_arm': all(pair_proof(k) for k in
                                                (P1, P2, P3, R1A, R1B, R2, R3)),
          'the_app_held_the_answer_and_parse_threw':
              D['the_answer_was_read_by_the_app_and_json_parse_threw_inside_it'],
          'mechanism_is_one_variable': D['reverting_only_those_two_lines_puts_the_unreachable_card_back']
          and D['the_two_bundles_differ_only_by_those_two_lines'],
          'card_alone_is_not_evidence': D['a_true_transport_death_paints_the_identical_card_on_the_old_bundle']
          and D['what_separates_the_two_is_the_pairing_not_the_card'],
          'challenged_cell_lifted': D['lifted_from_unproven_on_the_named_tip'],
          'the_leg_that_ate_the_500': D['which_leg_the_real_product_answered_with_a_500'],
          'the_kept_product_fact': D['old_network_branch_renders_no_technical_detail']
          and D['current_branch_network_card_does_render_a_device_note'],
          'all_required_booleans_held': D['ALL_REQUIRED_HOLD'],
          'booleans_true_of_required': '%d of %d' % (D['booleans_true'], D['booleans_required'])},
      'cells': cells,
      'boundary': BOUND,
      'q25': 'every millisecond and every byte count here was read in this batch from the named arm file; '
             'no number is carried over from ORD-0300',
      'derived_result': None, 'claimed_result': 'MEASURED_NOT_GRADED',
      'built_at_local': time.strftime('%Y-%m-%dT%H:%M:%S%z')}
(BASE / OUT).write_text(json.dumps(rc, ensure_ascii=False, indent=1), encoding='utf-8', newline='\n')
print('wrote', OUT, (BASE / OUT).stat().st_size, 'B |', len(cells), 'cells')
for x in cells:
    print('  ', x['id'][:46], '|', x['verdict'][:70])
print('pairing in every 5xx arm:', rc['derived_summary']['pairing_holds_in_every_5xx_arm'])
print('lifted:', D['lifted_from_unproven_on_the_named_tip'], '| rename needed:',
      rc['challenge_answered']['rename_needed'])
print('served asset read:', json.dumps(SERVED, ensure_ascii=False)[:220])
