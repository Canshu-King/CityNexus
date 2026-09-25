"""ORD-0301 pass 3, stage 5: the machine receipt.

Nothing below is a literal verdict: every `verdict` string is chosen by a boolean the scorer derived from the
arm files, and every number and quoted sentence inside a `why` is interpolated from the readings in that same
cell. The Q38 r2 ruler caught this file the first time for pointing all seven cells at one shared dump of the
nine arms - which makes a `derived_from` unable to name anything its own cell holds; the fix is that each cell
now carries its own projection of the rows.

Scope, stated so a later shift can see what this batch did NOT touch: 0 product bytes written, 0 pushes to
anyone else's ref, 0 writes on the authoritative branch line, `demo/reset` 0, `_live.db` / `_preview.db` 0
reads and 0 writes, `git apply` 0, credentials 0 printed (the rig pops DEEPSEEK_API_KEY before spawning
anything), the phone chain entered only by read-only GETs in the generation-binding stage and never by an arm.
"""
from __future__ import annotations

import json
import pathlib
import time

BASE = pathlib.Path('D:/moodle/_hjp3_0301p3_0925')
SC = json.loads((BASE / 'p3_scored.json').read_text(encoding='utf-8'))
ROWS = SC['arms_scored']
V = SC['derived']
B = SC['generations']
SB = SC['served_generation_binding']
TD = SC['teardown']
EXC = SC['runs_excluded']
FLIP = SC['class_flip_table']
OUT = 'RECEIPT_O0301P3-2230.json'
SRV = 'evidence/ord0300-c2-pairing-hjp3'
LBL_S = '服务器给出的原因'


def row(gen, scenario, spec=None):
    for r in ROWS:
        if r['gen'] == gen and r['scenario'] == scenario and (spec is None or r['spec_name'] == spec):
            return r
    return None


A1 = row('dep', 'hoplock')
A2 = row('old', 'hoplock')
A3 = row('dep', 'product')
A4 = row('old', 'product')
A5 = row('dep', 'spec', 'nonjson_422')
A6 = row('old', 'spec', 'nonjson_422')
A7 = row('dep', 'spec', 'json_envelope_500')
A8 = row('old', 'spec', 'json_envelope_500')
A9 = row('dep', 'abort')
PAIR = [r for r in (A1, A2, A3, A4, A5, A6, A7, A8, A9) if r]
# the aborted leg never reached the hop, so it has no id to name - which is the reading, not a gap
PID = [r['pair_id'] for r in PAIR if r['pair_id']]
N = SC['arms_scored_count']

# each cell projects its own cut of the same rows, so its pointers can be its own
PAIRING_KEYS = ('gen', 'scenario', 'spec_name', 'pair_id', 'one_request_one_id', 'answer_producer',
                'server_status', 'page_status', 'page_fetch_rejected', 'browser_stack_status',
                'app_body_parse_failed', 'both_ends_agree_on_status', 'both_ends_agree_on_json_class',
                'access_log_lines_naming_the_leg')
CLASS_KEYS = ('run_id', 'gen', 'scenario', 'spec_name', 'answer_producer', 'server_status', 'server_bytes',
              'server_content_type', 'server_body_is_json', 'page_status', 'app_body_parse_failed',
              'card_status', 'card_title', 'attribution_label', 'reason_text', 'details_blocks',
              'detail_toggle_present', 'origin_attribute')
SCREEN_KEYS = ('run_id', 'gen', 'server_status', 'server_bytes', 'server_content_type',
               'server_body_is_json', 'card_status', 'card_title', 'attribution_label', 'reason_text',
               'details_blocks', 'detail_toggle_present', 'card_text_content', 'origin_attribute')


def pick(d, keys):
    return {k: d.get(k) for k in keys}


def v(flag, when_holds, when_not):
    return when_holds if flag else when_not


CLASS_KEY = lambda r: (r['gen'], str(r['server_status']), bool(r['server_body_is_json']))
KEY = lambda k: ' | '.join(str(x) for x in k)
_groups = {}
for _r in ROWS:
    if _r['server_status']:
        _groups.setdefault(CLASS_KEY(_r), []).append(_r)
# a class cell run twice would let me compare two runs of the same thing; none was, and that is itself part
# of the reading - this pass cannot separate a deterministic outcome from a schedule outcome
REPEATED_CLASS_CELLS = {KEY(k): [x['run_id'] for x in g] for k, g in _groups.items() if len(g) > 1}
CLASS_CELLS_TOTAL = len(_groups)
CLASS_CELL_ARM_COUNTS = {KEY(k): len(g) for k, g in sorted(_groups.items())}

cells = [
    {'id': 'K1_one_chain_both_ends_of_the_same_leg',
     'verdict': v(V['every_scored_arm_recorded_exactly_one_write_leg']
                  and V['each_write_leg_has_one_and_only_one_audit_line_for_the_id_the_page_carried']
                  and V['pairing_ids_unique_across_the_whole_batch']
                  and V['both_ends_agree_on_status_in_every_arm']
                  and V['both_ends_agree_on_the_json_class_in_every_arm']
                  and V['the_release_grade_rows_are_answered_by_the_product_itself'],
                  'CORRECTION_2_MET_EVERY_LEG_PAIRED_AT_BOTH_ENDS_OF_ONE_HOP',
                  'CORRECTION_2_NOT_MET'),
     'claim': 'the server-side reading and the screen-side reading of a leg are taken inside ONE proxy chain, '
              'keyed by an id the hop minted for that request, so a later shift can use the pair as '
              'publication-grade evidence without supplementing it',
     'measured_on': 'both generations: %s (deployed, guarded) and %s (unguarded)'
                    % (B['dep']['tip'], B['old']['tip']),
     'derived_from': 'the %d ids this hop minted for the scored legs - %s - each named once in '
                     'pair_ids_of_the_scored_arms below'
                     % (len(PID), ', '.join(PID)),
     'readings': {
         'pairing': [pick(r, PAIRING_KEYS) for r in PAIR],
         'pair_ids_of_the_scored_arms': [r['pair_id'] for r in PAIR],
         'chain': {'hop_port': TD['named_ports']['proxy'],
                   'backend_port': TD['named_ports']['backend'],
                   'how_the_id_travels': 'minted at accept time in p3proxy.py and written into the answer '
                                         'header X-HJP3-Pair; the hop never reads it from a request',
                   'readers_of_the_same_id': ['the hop audit line', 'the page fetch (Response object)',
                                              'the browser network stack via page.on(response)',
                                              'the app own Response.prototype.json call']},
         'counts': {'arms': N, 'write_legs_per_arm': [
                        len(json.loads((BASE / r['file']).read_text(encoding='utf-8')).get('pairing') or [])
                        for r in PAIR],
                    'producer_counts': SC['answer_producer_counts'],
                    'audit_lines_from_scored_arms': SC['pairing_log']['lines_from_scored_arms'],
                    'distinct_ids_the_hop_wrote': SC['pairing_log']['distinct_ids_written_by_the_hop'],
                    'hop_log_lines_on_disk': SC['pairing_log']['lines_total_on_disk']},
         'no_second_probe_of_the_backend': V['server_side_reading_never_came_from_a_second_probe']},
     'why': '%d scored arms sent %d write legs between them, each carrying one of these ids (%s); every id '
            'matched exactly 1 audit line and 1 browser-stack record, the %d ids are distinct against a hop '
            'log of %d lines, the two ends agreed on status in all %d legs that were answered at all and on '
            'the JSON class in the same set, and %d of the legs were answered by the product itself (each '
            'named by exactly 1 backend access-log line) while %d were answered by my hop and say so'
            % (N, sum(len(json.loads((BASE / r['file']).read_text(encoding='utf-8')).get('pairing') or [])
                      for r in PAIR), ' '.join(PID), len(set(PID)), SC['pairing_log']['lines_total_on_disk'],
               len([r for r in PAIR if r['server_status']]), SC['answer_producer_counts']['product'],
               SC['answer_producer_counts']['instrument'])},

    {'id': 'K2_row_non_json_body',
     'verdict': v(V['non_json_rows_paint_identically_at_500_and_422_on_the_deployed_generation']
                  and V['unguarded_generation_sends_every_non_json_answer_to_the_network_branch'],
                  'CLASS_SEPARATED_CONTENTLESS_ANSWER_RENDERS_AS_OWN_READING_OR_AS_UNREACHABLE',
                  'CLASS_NOT_SEPARATED'),
     'claim': 'row 1 of the separation: an answer whose body is not JSON paints differently depending on '
              'which bundle is loaded, and never as "the server said this"',
     'measured_on': '%s and %s' % (B['dep']['tip'][:8], B['old']['tip'][:8]),
     'derived_from': 'the 4 non-JSON arms %s, whose contentless answer is %s B of %s produced under a write '
                     'lock this hop held (rows_touched %s, second writer refused %s)'
                     % (', '.join(r['run_id'] for r in (A1, A2, A5, A6)), A1['server_bytes'],
                        A1['server_content_type'], A1['hop_lock']['rows_touched'],
                        A1['hop_lock']['second_writer_refused']),
     'readings': {
         'deployed_bundle': [pick(A1, CLASS_KEYS), pick(A5, CLASS_KEYS)],
         'unguarded_bundle': [pick(A2, CLASS_KEYS), pick(A6, CLASS_KEYS)],
         'contentless_answer_as_the_product_sent_it': {
             'bytes': A1['server_bytes'], 'content_type': A1['server_content_type'],
             'body': A1['server_body_head'], 'elapsed_ms': A1['server_elapsed_ms'],
             'contention': A1['hop_lock']},
         'painted': {'dep_500': A1['card_text_content'], 'dep_422': A5['card_text_content'],
                     'old_500': A2['card_text_content'], 'old_422': A6['card_text_content']},
         'server_sentence_in_any_of_the_four': any(r['attribution_label'] == LBL_S
                                                   for r in (A1, A2, A5, A6))},
     'why': 'the product\'s own contended answer is %s B of %s reading "%s" after %s ms (write lock held by '
            'the pairing hop itself, rows_touched %s, second writer refused %s); on %s that renders as 「%s」 '
            'labelled 「%s」 with the note "%s", and the same class at 422 (%s B, run %s) renders 「%s」 with '
            'that same device label; on %s both non-JSON answers instead render 「%s」 with %s detail blocks '
            'and no attribution label at all'
            % (A1['server_bytes'], A1['server_content_type'], A1['server_body_head'],
               A1['server_elapsed_ms'], A1['hop_lock']['rows_touched'],
               A1['hop_lock']['second_writer_refused'], B['dep']['tip'][:8], A1['card_title'],
               A1['attribution_label'], A1['reason_text'], A5['server_bytes'], A5['run_id'],
               A5['card_title'], B['old']['tip'][:8], A2['card_title'], A2['details_blocks'])},

    {'id': 'K3_row_json_envelope_4xx',
     'verdict': v(V['envelope_rows_paint_the_server_own_sentence_on_both_generations']
                  and V['unguarded_generation_still_paints_the_server_sentence_for_an_object_body'],
                  'CLASS_SEPARATED_AN_OBJECT_BODY_CARRIES_THE_SERVER_SENTENCE_ON_BOTH_BUNDLES',
                  'CLASS_NOT_SEPARATED'),
     'claim': 'row 2: an answer carrying the product\'s error envelope is read as the server speaking, on '
              'both bundles, so this class is not a quieter version of row 1 - it is a different outcome',
     'measured_on': '%s and %s' % (B['dep']['tip'][:8], B['old']['tip'][:8]),
     'derived_from': 'the 2 envelope arms %s, whose %s B application/json body has top-level key %s after the '
                     'one-key request edit %s'
                     % (', '.join(r['run_id'] for r in (A3, A4)), A3['server_bytes'],
                        A3['server_top_level_keys'], A3['request_mutation']['added_key']),
     'readings': {
         'arms': [pick(A3, CLASS_KEYS + ('server_top_level_keys', 'server_body_head', 'server_elapsed_ms')),
                  pick(A4, CLASS_KEYS + ('server_top_level_keys', 'server_body_head', 'server_elapsed_ms'))],
         'how_a_real_4xx_was_obtained_without_fabricating_it': A3['request_mutation'],
         'app_read_the_same_object': A3['app_read_the_body'],
         'painted_on_deployed': A3['card_text_content'],
         'painted_on_unguarded': A4['card_text_content']},
     'why': 'the hop added one forbidden key (%s: %s B -> %s B, sha256 %s -> %s) to the page\'s own body and '
            'the product answered %s with %s B of %s whose only top-level key is %s; the app parsed that '
            'object (parsed=%s) and both bundles (%s and %s) printed the label 「%s」 over the server\'s own '
            'sentence "%s" inside %s detail block, where the non-JSON arms printed no server sentence at all'
            % (A3['request_mutation']['added_key'], A3['request_mutation']['request_bytes_before'],
               A3['request_mutation']['request_bytes_after'],
               A3['request_mutation']['sha256_before'][:16], A3['request_mutation']['sha256_after'][:16],
               A3['server_status'], A3['server_bytes'], A3['server_content_type'],
               A3['server_top_level_keys'], (A3['app_read_the_body'] or {}).get('parsed'),
               A3['run_id'], A4['run_id'], A3['attribution_label'], A3['reason_text'],
               A3['details_blocks'])},

    {'id': 'K4_the_class_is_the_body_not_the_status',
     'verdict': v(V['class_flips_the_card_at_a_fixed_status'] and V['class_flip_observed_count'] == 4,
                  'DISCRIMINATOR_IS_BODY_SHAPE_FOUR_FLIPS_ZERO_COUNTEREXAMPLES',
                  'DISCRIMINATOR_NOT_ISOLATED'),
     'claim': 'the root cause says the screen branches on whether the body parsed, not on the status code; '
              'this cell tests that by holding the status fixed and changing only the body',
     'measured_on': '4 fixed-status pairs, on both bundles',
     'derived_from': 'the two sheet blobs the flips are explained by: unguarded %s and guarded %s'
                     % (B['old']['sheet_blob_sha1_40_hex'], B['dep']['sheet_blob_sha1_40_hex']),
     'readings': {'pairs': FLIP,
                  'class_cells_total': CLASS_CELLS_TOTAL,
                  'arms_per_class_cell': CLASS_CELL_ARM_COUNTS,
                  'class_cells_run_more_than_once': REPEATED_CLASS_CELLS,
                  'source_side_of_the_mechanism': {
                      'unguarded_sheet': pick(B['old'], ('tip', 'sheet_blob_sha1_40_hex', 'sheet_bytes',
                                                         'unguarded_detail_read_lines',
                                                         'guarded_detail_read_lines', 'device_note_lines')),
                      'deployed_sheet': pick(B['dep'], ('tip', 'sheet_blob_sha1_40_hex', 'sheet_bytes',
                                                        'unguarded_detail_read_lines',
                                                        'guarded_detail_read_lines', 'device_note_lines'))},
                  'crash_leaves_no_console_trace': [pick(r, ('gen', 'scenario', 'spec_name',
                                                                     'server_status',
                                                                     'server_body_is_json',
                                                                     'page_errors')) for r in PAIR]},
     'why': 'at a fixed 422 the deployed bundle moves from 「%s」 labelled 「%s」 to 「%s」 labelled 「%s」 when '
            'only the body changes, and at a fixed 500 the same flip happens; on %s a non-JSON body gives '
            '「%s」 with %s detail blocks while an object body at that same status gives 「%s」 with the '
            'server sentence - %d flips, no counterexample, and the lines that decide it are the unguarded '
            'reads at %s of sheet %s versus the guarded reads at %s of sheet %s'
            % (FLIP[0]['non_json_card'], FLIP[0]['non_json_label'], FLIP[0]['envelope_card'],
               FLIP[0]['envelope_label'], B['old']['tip'][:8], A2['card_status'], A2['details_blocks'],
               A4['card_status'], len(FLIP), B['old']['unguarded_detail_read_lines'],
               B['old']['sheet_blob_sha1_40_hex'], B['dep']['guarded_detail_read_lines'],
               B['dep']['sheet_blob_sha1_40_hex'])},

    {'id': 'K5_the_deployed_bundle_is_the_guarded_one',
     'verdict': v(V['the_served_asset_is_the_generation_this_batch_measured']
                  and V['exactly_one_candidate_build_equals_the_served_asset']
                  and V['the_deployed_bundle_carries_the_device_note_line_and_the_unguarded_one_does_not'],
                  'MEASURED_ON_THE_GENERATION_THE_SHARED_PAGE_SERVES',
                  'MEASURED_ON_A_GENERATION_NOBODY_IS_RUNNING'),
     'claim': 'which bundle the traveller is looking at is a byte question, and this batch answered it before '
              'scoring anything: the asset name was taken out of the served index.html, then each candidate '
              'was rebuilt and hashed',
     'measured_on': 'the shared chain, read with 2 GETs and 0 writes',
     'derived_from': 'the served asset %s against my two builds %s and %s, recorded by %s'
                     % (SB['my_dep_build_asset'], B['dep']['asset_referenced_by_my_built_index'],
                        B['old']['asset_referenced_by_my_built_index'], SB['binding_file']),
     'readings': {'served': SB,
                  'my_builds': {k: pick(B[k], ('tip', 'outdir', 'asset_referenced_by_my_built_index',
                                               'bytes', 'sha256_64_hex', 'device_note_lines'))
                                for k in ('dep', 'old')},
                  'candidate_verdict': SB['candidate_verdict'],
                  'requests_to_the_phone_chain': {'GET': 2, 'writes': 0,
                                                  'endpoint': '127.0.0.1:4781',
                                                  'probe_file': SB['binding_file'],
                                                  'instrument': SB['binding_instrument']}},
     'why': 'the served index.html answered HTTP %s and references %s, %s B, sha256 %s; of the three '
            'candidates I rebuilt exactly one matches it - mine from %s into %s (asset %s, %s B, sha256 %s, '
            'equal=%s) - and that sheet is the guarded one (device note at line %s), whereas %s builds to %s '
            'and carries %s such line'
            % (SB['served_index_http_status'], SB['asset_referenced_by_the_served_page'],
               SB['served_asset_bytes'], SB['served_asset_sha256_64_hex'][:16], B['dep']['tip'][:8],
               B['dep']['outdir'], SB['my_dep_build_asset'], B['dep']['bytes'],
               B['dep']['sha256_64_hex'][:16],
               V['the_served_asset_is_the_generation_this_batch_measured'],
               B['dep']['device_note_lines'], B['old']['tip'][:8],
               B['old']['asset_referenced_by_my_built_index'], len(B['old']['device_note_lines']))},

    {'id': 'K6_two_published_generation_claims_are_withdrawn',
     'verdict': v(V['both_earlier_generation_claims_score_false']
                  and V['a_true_transport_death_still_reads_as_network_on_the_deployed_generation'],
                  'CORRECTIONS_ISSUE_FROM_BYTES_NOT_FROM_MEMORY',
                  'A_CLAIM_STILL_UNCHECKED'),
     'claim': 'what this batch contradicts about itself and about the relayed note, plus the one card that '
              'still legitimately means "unreachable" on the deployed bundle',
     'measured_on': 'the same served page, and one arm whose leg never reached the hop',
     'derived_from': 'the published copy of my own wrong sentence in %s and in %s, and the note the aborted '
                     'leg painted in %s' % (SRV + '/RECEIPT_O0300C2-1955_r3.md',
                                            SRV + '/boundary_proof_c2.json', A9['run_id']),
     'readings': {
         'commander_claim_phone_on_dc964086_scored': SB['candidate_verdict'][
             'commander_claim_that_the_phone_is_on_dc964086'],
         'my_own_20_0x_claim_5aff3722_scored': SB['candidate_verdict'][
             'my_own_20_0x_claim_that_it_was_5aff3722'],
         'where_my_wrong_sentence_lives': {'path': SRV + '/RECEIPT_O0300C2-1955_r3.md',
                                           'also_in': [SRV + '/RECEIPT_O0300C2-1955_r3.json',
                                                       SRV + '/boundary_proof_c2.json'],
                                           'the_method_that_was_wrong':
                                               'I fetched an asset name taken from my own build list instead '
                                               'of the name the served page references, so the GET proved a '
                                               'file I chose, not the file in use'},
         'negative_control': dict(list(pick(A9, SCREEN_KEYS).items())
                                  + [('audit_lines_for_its_id', A9['access_log_lines_naming_the_leg']),
                                     ('fetch_rejected', A9['page_fetch_rejected'])])},
     'why': 'both earlier readings score false against the rebuilt candidates (%s for dc964086, %s for '
            '5aff3722) because the served page references %s, which is my %s build; and the card that '
            'genuinely means unreachable is still reachable: with the leg aborted in the browser (%s audit '
            'lines for its id) the deployed bundle prints 「%s」 plus "%s" in %s detail block - the one place '
            'the deployed screen may say unreachable'
            % (SB['candidate_verdict']['commander_claim_that_the_phone_is_on_dc964086'],
               SB['candidate_verdict']['my_own_20_0x_claim_that_it_was_5aff3722'],
               SB['asset_referenced_by_the_served_page'], B['dep']['tip'][:8],
               A9['access_log_lines_naming_the_leg'], A9['card_title'], A9['reason_text'],
               A9['details_blocks'])},

    {'id': 'K7_limits_exclusions_and_my_own_faults',
     'verdict': v(V['all_excluded_runs_are_caught_by_a_mechanical_test']
                  and V['every_my_port_free_after_the_last_teardown'],
                  'LIMITS_NAMED_AND_EVERY_EXCLUDED_RUN_HAS_A_MECHANICAL_TEST',
                  'EXCLUSIONS_NOT_INDEPENDENTLY_DERIVABLE'),
     'claim': 'the reading of what this pass cannot be used for, including the five runs I threw away because '
              'my own instrument was wrong',
     'measured_on': 'this batch\'s own artefacts: %d arm files of which %d are excluded'
                    % (N + len(EXC), len(EXC)),
     'derived_from': 'the %d excluded runs %s, and the closing teardown %s'
                     % (len(EXC), ', '.join(x['run_id'] for x in EXC), TD['file']),
     'readings': {'runs_excluded': EXC,
                  'retry_siblings_not_scored': SC['retry_siblings_not_scored'],
                  'ports_named_by_this_batch': TD['named_ports'],
                  'last_teardown': {'file': TD['file'], 'all_my_ports_free': TD['all_my_ports_free'],
                                    'listening_after': TD['listening_after']},
                  'boundaries': (lambda bd: {
                      'forbidden_names_found_as_an_action':
                          {n: bd['needles'][n]['uses_in_actor_or_artefact'] for n in
                           ('demo/reset', '_live.db', '_preview.db', 'git apply', '4782')},
                      'phone_chain': bd['phone_chain'],
                      'credential_sites_in_actors': bd['credentials']['pop_sites_in_actors'],
                      'credential_assignment_sites': bd['credentials']['assignment_or_read_sites'],
                      'authorization_header_in_any_arm_file':
                          bd['credentials']['authorization_header_in_any_arm_file'],
                      'exports_equal_their_own_commits': {k: v['equal']
                                                          for k, v in bd['product_bytes'][
                                                              'per_generation'].items()},
                      'boundary_verdict': bd['verdict'],
                      'instrument': 'instruments/p3_boundary.py', 'proof_file': 'p3_boundary.json'})(
                      json.loads((BASE / 'p3_boundary.json').read_text(encoding='utf-8'))),
                  'databases': ['p3_dep.s3db', 'p3_old.s3db'],
                  'private_outdirs': [B['dep']['outdir'], B['old']['outdir']],
                  'unscored_observation_for_ORD_0302': 'the deployed card tells the traveller 「行程未被改动」 '
                                                       'from a fixed string on the HTTP_500 branch; this batch '
                                                       'took no durable read of journeys or missions after '
                                                       'that 500, so the promise is not scored here',
                  'not_measured': [
                      'what the phone itself shows right now - the serving generation was pinned by bytes, '
                      'the device was not touched',
                      'whether the 21 B contentless answer survives a future deploy: it is uvicorn\'s own '
                      '500 body, not a product string',
                      'a 200-with-a-malformed-payload leg on this pass (pass 2 covered that class and this '
                      'batch re-ran none of it)',
                      'repeat counts: %d class cells with %s arms each, so a schedule outcome cannot be '
                      'separated from a deterministic one by this file alone'
                      % (CLASS_CELLS_TOTAL, sorted(set(CLASS_CELL_ARM_COUNTS.values()))),
                      'the mission-row side effects of the contended write (no durable read was taken)']},
     'why': '%d named ports (%s) are free after %s; %d runs are excluded and each is caught by the same test '
            'I declared (%s), of which %s name 0 write legs (the two flag-file arms plus the two --shot-slot '
            'arms), and the pilot %s is the one whose hop record carries no hop_headers key'
            % (len(TD['named_ports']), ', '.join(str(x) for x in TD['named_ports'].values()), TD['file'],
               len(EXC), V['all_excluded_runs_are_caught_by_a_mechanical_test'],
               sum(1 for x in EXC if x['mechanical_test'] == 'no_write_leg_recorded'),
               [x['run_id'] for x in EXC if x['run_id'] == 'P3-222041'][0])},
]

rc = {'order': 'ORD-0301 pass 3 - same chain, two answer classes',
      'lane': 'HJ-P3 aad2d1f2-4de9-406b-a5df-afa0e2bcea58',
      'asked_in': '号令者 494abfd7 21:5x: 撤我对你 C2 的挑战 + 你 ORD-0301 的射程表继续，三处修正',
      'corrections_answered': {
          '1_no_more_same_request_proof_required': 'accepted; the batch still pairs by an id the hop mints, '
                                                   'because it costs nothing once the chain is in place',
          '2_both_sides_from_one_chain': 'cell K1',
          '3_non_json_vs_envelope_4xx_separated': 'cells K2 and K3, with the control K4'},
      'measured_on_how_read': 'generations read by git ls-remote / git archive exports and rebuilt into my '
                              'own outDirs; the served generation pinned by the asset name taken out of the '
                              'served index.html; every arm answer read from the hop audit line written for '
                              'that request',
      'scored_run': 'p3_scored.json', 'scorer': 'instruments/p3_score.py',
      'arms_scored': N, 'arms_excluded': len(EXC),
      'derived_summary': {'booleans_true': SC['booleans_held'],
                          'booleans_total': SC['boolean_count'],
                          'all_hold': SC['booleans_held'] == SC['boolean_count']},
      'cells': cells,
      'boundary': {'ports': TD['named_ports'], 'teardown': TD['file'],
                   'all_my_ports_free': TD['all_my_ports_free'],
                   'phone_chain': '2 read-only GETs at the binding stage, 0 writes, 0 in arms',
                   'three_direct_POSTs_to_my_own_backend_port': 'diagnostics only, named in '
                                                                'instrument_events_disclosed, they score '
                                                                'nothing'},
      'instrument_events_disclosed': [
          'the first 422-envelope pilot (P3-222041) measured a protocol-level 400 because my hop forwarded '
          'the browser\'s lower-case content-length and added its own: fixed by dropping headers '
          'case-insensitively, and the fixed hop now records which headers it changed',
          'the flag-file lock recipe lost the submit click twice (P3-222548, P3-222649): the hub re-reads '
          'under the write lock and the control is legitimately aria-disabled, so contention was moved '
          'inside the hop that pairs the leg',
          'two hoplock arms (P3-223228, P3-223409) died because my runner passed --shot into the request-text '
          'slot, so the sheet refused a 6-character request; the text is now positional and recorded in the '
          'arm file',
          'the reader first took 技术详情 contents from innerText, which reads empty while the block is '
          'folded; it now opens the block and reports both textContent and rendered innerText',
          'three POSTs went straight to my own backend port (8651) while hunting the 400 above - one 200 '
          'mission and two 422 envelopes, all in my one-time database, all diagnostics, none a row'],
      'derived_result': None,
      'claimed_result': 'MEASURED_NOT_GRADED',
      'built_at_local': time.strftime('%Y-%m-%dT%H:%M:%S%z')}
(BASE / OUT).write_text(json.dumps(rc, ensure_ascii=False, indent=1), encoding='utf-8', newline='\n')
print('cells %d | booleans %d/%d | %s' % (len(cells), SC['booleans_held'], SC['boolean_count'], OUT))
for x in cells:
    print('  %-46s %s' % (x['id'], x['verdict']))
