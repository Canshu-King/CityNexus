"""ORD-0301 pass 3, stage 4: score the arms. Every number and every boolean here is recomputed from the
arm files on disk; nothing in this file is a literal verdict.

Two sets of runs are named and kept, not deleted:
  * `scoreable` - an arm whose page really sent the leg, whose hop is the fixed hop, and whose answer is
    attributable to one of the two producers this batch recognises (`product` or `instrument_origin_per_spec`),
    or to nobody at all in the abort arm's case;
  * `runs_excluded` - five of my own instrument faults, each with the mechanical test that catches it, so a
    later shift can re-derive the exclusion instead of trusting my prose.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import re
import time

BASE = pathlib.Path('D:/moodle/_hjp3_0301p3_0925')
SRC = pathlib.Path('D:/moodle/HJ-P3_evidence')
TIPS = {'dep': '7856e03f6238da3000976eb6e690a448dfa39b9a',
        'old': 'dc964086c9d412573ac19d70b24b30e6c3ee6168'}
SHEET = 'frontend/src/features/planning/PlanWithAiSheet.tsx'
PORTS = {'backend': 8651, 'proxy': 8652, 'face_dep': 8653, 'face_old': 8654}
LABEL_SERVER = '服务器给出的原因'
LABEL_DEVICE = '这台设备自己的读数'


def blob_of(p):
    d = pathlib.Path(p).read_bytes()
    return hashlib.sha1(b'blob %d\0' % len(d) + d).hexdigest(), len(d)


def sha256(p):
    return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()


def gen_of(arm):
    return arm.split('_')[0]


# ---- declared faults of my own instrument, each with the test that catches it -------------------------
DECLARED_FAULTS = {
    '222041': 'my hop forwarded the browser\'s lower-case content-length AND added its own, so the two '
              'values disagreed and h11 answered 400 "Invalid HTTP request received." in 1 ms - the record '
              'has no hop_headers key because that key was added by the fix',
    '222548': 'the flag-file lock recipe: a separate process took the write lock on sight of a flag, the '
              'hub re-read under that lock, and the submit control was aria-disabled when Playwright asked, '
              'so no leg left the page',
    '222649': 'same flag-file recipe on the other generation, same outcome (0 write legs)',
    '223228': 'the runner put the --shot flag in the request-text slot, so the traveller\'s sentence became '
              '"--shot" (6 chars), the sheet\'s own 8-character gate refused to send, and the arm timed out',
    '223409': 'same --shot-slot fault on the other generation',
}


AUDIT = {}
for _f in (BASE / 'p3_pair_log.jsonl').read_text(encoding='utf-8').splitlines():
    if _f.strip():
        _j = json.loads(_f)
        AUDIT[_j.get('pair_id')] = _j


def classify_fault(run_id, arm):
    """Re-derive, from the artefact rather than from my prose, why this run cannot be scored."""
    legs = arm.get('pairing') or []
    if not legs:
        return ('no_write_leg_recorded',
                'the page never sent the leg (node_rc=%s), so there is nothing on either end to pair'
                % arm.get('node_rc'))
    pid = legs[0].get('pair_id')
    line = AUDIT.get(pid)
    if line is None:
        return ('no_audit_line_for_the_id_the_page_carried', 'pair_id %s' % pid)
    if 'hop_headers' not in line:
        return ('hop_forwarded_before_the_header_fix',
                'the hop answered in %s ms with %s B of %s: %s'
                % (line.get('upstream_elapsed_ms') if 'upstream_elapsed_ms' in line
                   else legs[0]['server_side_from_the_same_hop'].get('elapsed_ms'),
                   line.get('bytes'), line.get('content_type'), line.get('body_head')))
    return ('no_fault_found', None)


arms = {}
for f in sorted(BASE.glob('p3_arm_*.json')):
    a = json.loads(f.read_text(encoding='utf-8'))
    a['_file'] = f.name
    arms[f.name[-11:-5]] = a

scoreable, excluded = {}, []
for run, a in sorted(arms.items()):
    best = None      # the newest good run for this arm key wins; superseded siblings are reported too
    if run in DECLARED_FAULTS:
        code, detail = classify_fault(run, a)
        excluded.append({'run_id': 'P3-' + run, 'arm': a['arm'], 'file': a['_file'],
                         'declared_fault': DECLARED_FAULTS[run],
                         'mechanical_test': code, 'mechanical_detail': detail,
                         'agrees_with_declared': code != 'no_fault_found'})
        continue
    legs = a.get('pairing') or []
    if not legs:
        excluded.append({'run_id': 'P3-' + run, 'arm': a['arm'], 'file': a['_file'],
                         'declared_fault': None, 'mechanical_test': 'no_write_leg_recorded',
                         'mechanical_detail': 'node_rc=%s' % a.get('node_rc'),
                         'agrees_with_declared': False})
        continue
    scoreable[run] = a

# the newest run per arm key is the scored one; an older sibling of the same key is a retry, not a reading
by_key = {}
for run, a in scoreable.items():
    by_key.setdefault(a['arm'], []).append(run)
retries = {k: sorted(v)[:-1] for k, v in by_key.items() if len(v) > 1}
scored = {k: sorted(v)[-1] for k, v in by_key.items()}

rows = []
for key, run in sorted(scored.items()):
    a = arms[run]
    leg = (a.get('pairing') or [{}])[0]
    srv = leg.get('server_side_from_the_same_hop') or {}
    pg = leg.get('screen_side_from_the_page') or {}
    o = a.get('screen_as_painted_after_tapping_detail') or {}
    s = a.get('screen_as_painted_before_tapping') or {}
    rows.append({
        'arm_key': key, 'run_id': 'P3-' + run, 'file': a['_file'], 'gen': gen_of(key),
        'tip': a['tip'], 'scenario': a['scenario'], 'proxy_mode': a['proxy_mode'],
        'spec_name': srv.get('spec_name') or (a.get('spec') or {}).get('name'),
        'pair_id': leg.get('pair_id'),
        'one_request_one_id': leg.get('one_request_one_id'),
        'answer_producer': srv.get('answered_by') or 'nobody_answered_this_leg',
        'server_status': srv.get('status'), 'server_bytes': srv.get('bytes'),
        'server_content_type': srv.get('content_type'),
        'server_body_is_json': srv.get('body_parses_as_json'),
        'server_top_level_keys': srv.get('top_level_keys'), 'server_body_head': srv.get('body_head'),
        'server_elapsed_ms': srv.get('elapsed_ms'),
        'hop_lock': srv.get('hop_lock'), 'request_mutation': srv.get('request_mutation'),
        'page_status': pg.get('status'), 'page_fetch_rejected': pg.get('fetch_rejected'),
        'page_reject_name': (pg.get('app_read_the_body') or {}).get('error_name')
        if pg.get('body_parse_failed') else None,
        'app_read_the_body': pg.get('app_read_the_body'),
        'app_body_parse_failed': pg.get('body_parse_failed'),
        'browser_stack_status': (pg.get('browser_stack') or {}).get('status'),
        'both_ends_agree_on_status': leg.get('both_ends_agree_on_status'),
        'both_ends_agree_on_json_class': leg.get('both_ends_agree_on_json_class'),
        'card_status': s.get('cross_check_data_result_status'),
        'card_title': s.get('card_title_painted'),
        'attribution_label': o.get('reason_label_text_content'),
        'attribution_label_rendered': o.get('reason_label_painted'),
        'reason_text': o.get('reason_value_text_content'),
        'details_blocks': s.get('details_elements_present'),
        'detail_toggle_present': s.get('detail_toggle_present'),
        'detail_block_open_attempt': a.get('detail_block_open_attempt'),
        'card_text_content': o.get('result_card_text_content'),
        'origin_attribute': s.get('cross_check_data_reason_origin'),
        'access_log_lines_naming_the_leg': (a.get('access_log_witness') or {}).get('lines_naming_the_leg'),
        'access_log_line': ((a.get('access_log_witness') or {}).get('lines') or [None])[0],
        'page_errors': a.get('page_errors'), 'waited_ms': a.get('waited_ms'),
        'wall_seconds': a.get('wall_seconds'), 'rig': a.get('rig'),
    })
rows.sort(key=lambda r: (r['gen'], r['scenario'], str(r['spec_name'])))

# ---- bundle and source facts, recomputed from the bytes I built and exported --------------------------
bundles = {}
for gen, tip in TIPS.items():
    tag = tip[:8]
    dist = BASE / ('dist_%s' % tag)
    html = (dist / 'index.html').read_text(encoding='utf-8', errors='replace')
    asset = re.search(r'''["'](/assets/index-[^"']+\.js)["']''', html).group(1)
    raw = (dist / asset.lstrip('/')).read_bytes()
    text = raw.decode('utf-8', 'replace')
    sheet = BASE / ('snap_%s' % tag) / SHEET
    sb, sb_len = blob_of(sheet)
    lines = sheet.read_text(encoding='utf-8').splitlines()
    bundles[gen] = {
        'tip': tip, 'outdir': dist.name, 'asset_referenced_by_my_built_index': asset,
        'bytes': len(raw), 'sha256_64_hex': hashlib.sha256(raw).hexdigest(),
        'sheet_path': SHEET, 'sheet_blob_sha1_40_hex': sb, 'sheet_bytes': sb_len,
        'unguarded_detail_read_lines': [i + 1 for i, x in enumerate(lines)
                                        if re.search(r'unknown \}\)\.detail', x)],
        'guarded_detail_read_lines': [i + 1 for i, x in enumerate(lines)
                                      if re.search(r'\| null\)\?\.detail', x)],
        'device_note_lines': [i + 1 for i, x in enumerate(lines)
                              if 'no readable answer reached this device' in x],
        'network_branch_wording_present': '连不上服务端' in text,
        'server_attribution_wording_present': LABEL_SERVER in text,
        'device_attribution_wording_present': LABEL_DEVICE in text}

bind = json.loads((BASE / 'served_generation_bind_c2.json').read_text(encoding='utf-8'))
served = bind['served']
dep_asset = bundles['dep']['asset_referenced_by_my_built_index'].lstrip('/')
served_asset = (served.get('asset_referenced_by_the_served_page') or '').lstrip('/')

# ---- the boundary and teardown ledger, read off disk ---------------------------------------------------
teardowns = sorted(BASE.glob('p3_teardown_*.json'))
td = json.loads(teardowns[-1].read_text(encoding='utf-8')) if teardowns else {}
audit = [json.loads(x) for x in (BASE / 'p3_pair_log.jsonl').read_text(encoding='utf-8').splitlines()
         if x.strip()]

# ---- derived predicates ------------------------------------------------------------------------------
prod = [r for r in rows if r['answer_producer'] == 'product']
inst = [r for r in rows if r['answer_producer'] == 'instrument_origin_per_spec']
dead = [r for r in rows if r['answer_producer'] == 'nobody_answered_this_leg']
pair_ids = [r['pair_id'] for r in rows if r['pair_id']]
by_gp = {}
for r in rows:
    by_gp[(r['gen'], str(r['server_status']), bool(r['server_body_is_json']))] = r


def row(gen, status, is_json):
    return by_gp.get((gen, str(status), is_json))


V = {}
V['every_scored_arm_recorded_exactly_one_write_leg'] = all(
    len(json.loads((BASE / r['file']).read_text(encoding='utf-8')).get('pairing') or []) == 1
    for r in rows)
V['each_write_leg_has_one_and_only_one_audit_line_for_the_id_the_page_carried'] = all(
    r['one_request_one_id'] for r in rows if r['pair_id'])
V['pairing_ids_unique_across_the_whole_batch'] = len(pair_ids) == len(set(pair_ids))
V['server_side_reading_never_came_from_a_second_probe'] = all(
    (json.loads((BASE / r['file']).read_text(encoding='utf-8')).get('pairing') or [{}])[0]
    .get('server_side_from_the_same_hop', {}).get('recorded') or r['scenario'] == 'abort' for r in rows)
V['both_ends_agree_on_status_in_every_arm'] = all(r['both_ends_agree_on_status'] for r in rows
                                                  if r['server_status'])
V['both_ends_agree_on_the_json_class_in_every_arm'] = all(r['both_ends_agree_on_json_class'] for r in rows
                                                          if r['server_status'])
V['every_product_answered_leg_is_also_recorded_by_the_backend_own_access_log'] = all(
    r['access_log_lines_naming_the_leg'] == 1 for r in prod)
V['the_release_grade_rows_are_answered_by_the_product_itself'] = len(prod) == 4
V['instrument_answered_rows_are_labelled_as_such'] = all(
    r['answer_producer'] == 'instrument_origin_per_spec' and not r['hop_lock'] for r in inst)
V['the_negative_control_leg_reached_no_hop_at_all'] = bool(dead) and all(
    r['server_status'] is None and r['page_fetch_rejected'] for r in dead)

# ③ the two classes, and the control that keeps the class label from being a restatement of the status
V['non_json_rows_paint_identically_at_500_and_422_on_the_deployed_generation'] = bool(
    row('dep', 500, False) and row('dep', 422, False)
    and row('dep', 500, False)['card_status'] == 'HTTP_500'
    and row('dep', 422, False)['card_status'] == 'HTTP_422'
    and all(LABEL_DEVICE in str(r['attribution_label']) for r in (row('dep', 500, False),
                                                                  row('dep', 422, False))))
V['envelope_rows_paint_the_server_own_sentence_on_both_generations'] = bool(
    row('dep', 422, True) and row('old', 422, True) and row('dep', 500, True) and row('old', 500, True)
    and all(LABEL_SERVER == r['attribution_label'] for r in (row('dep', 422, True), row('old', 422, True),
                                                             row('dep', 500, True), row('old', 500, True))))
flips = []
for gen, status in (('dep', 422), ('dep', 500), ('old', 422), ('old', 500)):
    a, b = row(gen, status, False), row(gen, status, True)
    if a and b:
        flips.append({'gen': gen, 'status': status,
                      'non_json_label': a['attribution_label'], 'non_json_card': a['card_status'],
                      'envelope_label': b['attribution_label'], 'envelope_card': b['card_status'],
                      'card_or_label_differs': (a['card_status'], a['attribution_label'])
                      != (b['card_status'], b['attribution_label'])})
V['class_flips_the_card_at_a_fixed_status'] = bool(flips) and all(f['card_or_label_differs'] for f in flips)
V['class_flip_observed_count'] = len(flips)
V['unguarded_generation_sends_every_non_json_answer_to_the_network_branch'] = all(
    r['card_status'] == 'NETWORK' and r['details_blocks'] == 0
    for r in rows if r['gen'] == 'old' and r['server_body_is_json'] is False)
V['unguarded_generation_still_paints_the_server_sentence_for_an_object_body'] = all(
    r['card_status'] != 'NETWORK' and LABEL_SERVER == r['attribution_label']
    for r in rows if r['gen'] == 'old' and r['server_body_is_json'] is True)
V['deployed_generation_never_lands_in_the_network_branch_for_an_answered_leg'] = all(
    r['card_status'] != 'NETWORK' for r in rows
    if r['gen'] == 'dep' and r['server_status'] and not r['page_fetch_rejected'])
V['a_true_transport_death_still_reads_as_network_on_the_deployed_generation'] = bool(
    dead and all(r['card_status'] == 'NETWORK' for r in dead))

V['exactly_one_candidate_build_equals_the_served_asset'] = bool(
    bind['verdict']['exactly_one_candidate_build_equals_the_served_asset'])
V['the_served_asset_is_the_generation_this_batch_measured'] = bool(
    served_asset and dep_asset == served_asset
    and served['asset_sha256_64_hex'] == bundles['dep']['sha256_64_hex'])
V['both_earlier_generation_claims_score_false'] = bool(
    bind['verdict']['commander_claim_that_the_phone_is_on_dc964086'] is False
    and bind['verdict']['my_own_20_0x_claim_that_it_was_5aff3722'] is False)
V['mechanism_line_numbers_recomputed_from_the_two_exported_sheets'] = bool(
    bundles['old']['unguarded_detail_read_lines'] == [147, 155]
    and not bundles['old']['guarded_detail_read_lines']
    and bundles['dep']['guarded_detail_read_lines'] == [147, 155]
    and not bundles['dep']['unguarded_detail_read_lines'])
V['the_deployed_bundle_carries_the_device_note_line_and_the_unguarded_one_does_not'] = bool(
    bundles['dep']['device_note_lines'] and not bundles['old']['device_note_lines'])
V['all_excluded_runs_are_caught_by_a_mechanical_test'] = all(
    x['agrees_with_declared'] for x in excluded) and len(excluded) == len(DECLARED_FAULTS)
V['every_my_port_free_after_the_last_teardown'] = bool(td.get('all_my_ports_free'))
V['no_page_error_was_raised_by_the_crash_branch'] = all(not r['page_errors'] for r in rows)

out = {
    'ran_at_local': time.strftime('%Y-%m-%dT%H:%M:%S%z'),
    'order': 'ORD-0301 pass 3 - one chain, two answer classes',
    'lane': 'HJ-P3 aad2d1f2-4de9-406b-a5df-afa0e2bcea58',
    'what_this_pass_answers': {
        'correction_2': 'the server-side and screen-side readings of one leg come from the same hop',
        'correction_3': 'a non-JSON body and a JSON 4xx envelope are separate rows, at both statuses and '
                        'on both generations'},
    'generations': bundles,
    'served_generation_binding': {'served_index_http_status': served.get('index_http_status'),
                                  'asset_referenced_by_the_served_page': served_asset,
                                  'served_asset_bytes': served.get('asset_bytes'),
                                  'served_asset_sha256_64_hex': served.get('asset_sha256_64_hex'),
                                  'my_dep_build_asset': dep_asset,
                                  'my_dep_build_sha256_64_hex': bundles['dep']['sha256_64_hex'],
                                  'candidate_verdict': bind['verdict'],
                                  'binding_instrument': 'instruments/p3_setup.py',
                                  'binding_file': 'served_generation_bind_c2.json'},
    'arms_scored': rows, 'arms_scored_count': len(rows),
    'runs_excluded': excluded,
    'retry_siblings_not_scored': retries,
    'answer_producer_counts': {'product': len(prod), 'instrument': len(inst),
                               'never_answered': len(dead)},
    'class_flip_table': flips,
    'pairing_log': {'lines_total_on_disk': len(audit),
                    'lines_from_scored_arms': len([x for x in audit if x.get('pair_id') in pair_ids]),
                    'distinct_ids_written_by_the_hop': len({x.get('pair_id') for x in audit}),
                    'hop_port': PORTS['proxy'], 'backend_port': PORTS['backend'],
                    'face_ports': [PORTS['face_dep'], PORTS['face_old']]},
    'teardown': {'file': teardowns[-1].name if teardowns else None,
                 'all_my_ports_free': td.get('all_my_ports_free'),
                 'listening_after': td.get('listening_after'),
                 'named_ports': {k: v for k, v in PORTS.items()}},
    'derived': V}
out['all_derived_hold'] = {k: v for k, v in V.items() if isinstance(v, bool)}
out['booleans_held'] = sum(1 for v in V.values() if v is True)
out['boolean_count'] = len([v for v in V.values() if isinstance(v, bool)])
(BASE / 'p3_scored.json').write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding='utf-8',
                                     newline='\n')
print('scored arms %d | excluded %d | booleans %d/%d'
      % (len(rows), len(excluded), out['booleans_held'], out['boolean_count']))
for k, v in V.items():
    if v is not True:
        print('  NOT TRUE:', k, '=', v)
print('class flip table:', json.dumps(flips, ensure_ascii=False))
print('producers:', json.dumps(out['answer_producer_counts']))
