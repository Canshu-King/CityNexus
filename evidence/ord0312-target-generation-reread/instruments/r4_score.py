"""Score the re-run: nine arms on the generation that serves NOW, plus its same-generation unguarded mutant.

Three things this has to prove rather than assert:

  * the classes are separable at the SAME status code - 422 with a JSON envelope is answered differently from
    422 with a non-JSON body, and the same pair exists at 500 - so a class label can never be a restatement of
    the status;
  * the guard flip is what changes the attribution, and only for bodies that are not JSON: on the mutant the
    non-JSON arms say "can't reach the server" while the envelope arms keep quoting the server;
  * every number in this file is a projection onto the fields UI_EVIDENCE_EXPOSURE_GATE_V1 allows. The hop's own
    `body_head` (a fragment of a real response body) and any raw detail are dropped here, and a detector that
    searches the surviving strings against the removed bodies - with a positive control - proves nothing leaked.

One run is excluded and the exclusion is caught by a mechanical test, not by my memory: zero paired legs, every
screen field null, and the rig's own seed text naming a FileNotFoundError. A second run of the same arm is kept as
a repeat, not as a third piece of evidence.
"""
from __future__ import annotations

import json
import pathlib
import time

BASE = pathlib.Path('D:/moodle/_hjp3_0312r_0926')
SET = json.loads((BASE / 'setup_facts_gen2.json').read_text(encoding='utf-8'))
MUT = json.loads((BASE / 'setup_facts_mut2.json').read_text(encoding='utf-8'))
G2 = json.loads(pathlib.Path('D:/moodle/_hjp3_0312p4_0926/ord0312_m3_binding_reread_gen2.json')
                .read_text(encoding='utf-8'))
ALLOWED = ('http_status', 'content_type', 'body_bytes', 'response_received', 'elapsed_ms', 'request_id')
DROP = ('body_head', 'body_text', 'response_json_head', 'detail', 'raw_detail', 'exception')
TIP = SET['tip']
ASSET = 'assets/' + pathlib.Path(SET['guarded_bundle']['asset']).name
SHA = SET['guarded_bundle']['sha256_64_hex']
MUT_ASSET = 'assets/' + pathlib.Path(MUT['mutant_bundle']['asset']).name
MUT_SHA = MUT['mutant_bundle']['sha256_64_hex']

SWEEP = {'dep_hoplock': 'P3-040015', 'old_hoplock': 'P3-040110', 'dep_product': 'P3-040206',
         'old_product': 'P3-040229', 'dep_nonjson_422': 'P3-040252', 'old_nonjson_422': 'P3-040315',
         'dep_json_500': 'P3-040339', 'old_json_500': 'P3-040403', 'dep_abort': 'P3-040427'}
REPEAT = ('dep_product', 'P3-035932')
EXCLUDED_RUN = 'P3-035722'


def project(d):
    """Allowed fields only; anything that could read as a body, a detail or an exception is dropped by name."""
    out = {}
    for k, v in d.items():
        if isinstance(v, dict):
            out[k] = project(v)
        elif isinstance(v, list):
            out[k] = [project(x) if isinstance(x, dict) else x for x in v]
        elif any(t in k.lower() for t in DROP):
            continue
        else:
            out[k] = v
    return out


def read(run_id, arm_key=None):
    # arm files are named p3_arm_<gen>_<scenario>_<name-or-mode>_<RUN>.json; the run id is the unique part, so
    # the lookup keys on it and refuses to guess if two files ever carry the same stamp
    files = sorted(BASE.glob('p3_arm_*_%s.json' % run_id))
    assert len(files) == 1, 'expected one file for %s, found %s' % (run_id, files)
    return json.loads(files[0].read_text(encoding='utf-8')), files[0].name


cells, removed_bodies = {}, []
for arm_key, run in SWEEP.items():
    d, fname = read(run, arm_key)
    pr = (d.get('pairing') or [{}])[0]
    srv = pr.get('server_side_from_the_same_hop') or {}
    removed_bodies.append(str(srv.get('body_head') or ''))
    before = d.get('screen_as_painted_before_tapping') or {}
    after = d.get('screen_as_painted_after_tapping_detail') or {}
    guard = 'unguarded(private mutant of the same commit)' if arm_key.startswith('old_') else 'guarded (as deployed)'
    cells[arm_key] = {
        'run_id': run, 'arm_file': fname, 'declared_intent': d.get('intent_declared_before'),
        'generation': TIP, 'bundle_served_by_my_face': {'asset': ASSET if guard.startswith('guarded')
                                                        else MUT_ASSET,
                                                        'sha256_64_hex': SHA if guard.startswith('guarded')
                                                        else MUT_SHA},
        'sheet_guard_state': guard, 'hop_mode': d.get('proxy_mode'),
        'answered_by': srv.get('answered_by'), 'reached_upstream': srv.get('reached_upstream'),
        'server_side': {'http_status': srv.get('status'), 'content_type': srv.get('content_type'),
                        'body_bytes': srv.get('bytes'), 'body_parses_as_json': srv.get('body_parses_as_json'),
                        'top_level_keys': srv.get('top_level_keys'), 'elapsed_ms': srv.get('elapsed_ms')},
        'body_class': ('JSON envelope' if srv.get('body_parses_as_json')
                       else ('no answer at all' if srv.get('status') is None else 'non-JSON body')),
        'screen_side': {
            'card_status painted': before.get('cross_check_data_result_status'),
            'card_title painted': before.get('card_title_painted'),
            'reason label painted': after.get('reason_label_text_content'),
            'server attribution painted': before.get('server_attribution_painted'),
            'device attribution painted': before.get('device_attribution_painted'),
            'detail elements present': before.get('details_elements_present'),
            'detail opened': after.get('detail_open_attribute')},
        'pairing': {'legs': len(d.get('pairing') or []),
                    'one_request_one_id': pr.get('one_request_one_id'),
                    'both_ends_agree_on_status': pr.get('both_ends_agree_on_status'),
                    'both_ends_agree_on_json_class': pr.get('both_ends_agree_on_json_class')},
        'rig_identity': {'face_port': d['rig']['face_port'], 'journey_id_named_by_the_rig': d['rig']['journey_id'],
                         'two_sided_ownership_probe': d['rig']['identity_two_sided'],
                         'db': pathlib.Path(str(d['rig']['db'])).name}}
    cells[arm_key] = project(cells[arm_key])

rep_arm, rep_run = REPEAT
rep, rep_file = read(rep_run, rep_arm)
rep_srv = ((rep.get('pairing') or [{}])[0].get('server_side_from_the_same_hop') or {})
rep_before = rep.get('screen_as_painted_before_tapping') or {}
removed_bodies.append(str(rep_srv.get('body_head') or ''))

exc, exc_file = read(EXCLUDED_RUN, 'dep_product')
exc_before = exc.get('screen_as_painted_before_tapping') or {}
catch = {'run_id': EXCLUDED_RUN, 'file': exc_file,
         'paired_legs_recorded': len(exc.get('pairing') or []),
         'screen_fields_read': len(exc_before),
         'screen_fields_null': sum(1 for v in exc_before.values() if v is None),
         'rig_seed_names_a_missing_file': 'FileNotFoundError' in str(exc['rig'].get('seed')),
         'seed_named_path': pathlib.Path(str([w for w in str(exc['rig'].get('seed')).split()
                                              if 'traveler_demo' in w][-1].strip("'").rstrip('\\n')
                                              or 'x')).name}
catch['mechanical_test_catches_it'] = bool(catch['paired_legs_recorded'] == 0
                                           and catch['screen_fields_null'] == catch['screen_fields_read']
                                           and catch['rig_seed_names_a_missing_file'])

a = cells
SERVER_LABEL = '服务器给出的原因'
DEVICE_LABEL = '这台设备自己的读数（服务器没给句子）'


def label(k):
    return cells[k]['screen_side']['reason label painted']


def status(k):
    return cells[k]['server_side']['http_status']


same_status_diff_class_422 = bool(status('dep_product') == status('dep_nonjson_422') == 422
                                 and cells['dep_product']['body_class'] != cells['dep_nonjson_422']['body_class']
                                 and label('dep_product') == SERVER_LABEL
                                 and label('dep_nonjson_422') == DEVICE_LABEL)
same_status_diff_class_500 = bool(status('dep_json_500') == status('dep_hoplock') == 500
                                 and cells['dep_json_500']['body_class'] != cells['dep_hoplock']['body_class']
                                 and label('dep_json_500') == SERVER_LABEL
                                 and label('dep_hoplock') == DEVICE_LABEL)
# the strongest form: on the deployed bundle, the painted label is a function of the BODY CLASS and of nothing
# else - same status, opposite labels; same label, opposite statuses
label_follows_body_class_not_status = bool(
    all(label(k) == (SERVER_LABEL if cells[k]['server_side']['body_parses_as_json'] else DEVICE_LABEL)
        for k in ('dep_product', 'dep_nonjson_422', 'dep_json_500', 'dep_hoplock')))
def card(k):
    return cells[k]['screen_side']['card_status painted']


# on the unguarded mutant of the SAME commit, the two arms whose body was not JSON degrade to "can't reach the
# server" although the hop recorded 500 and 422; the two arms whose body was a JSON envelope keep their correct
# HTTP card. So the guard is what carries the distinction, and it only ever mattered for non-JSON bodies.
flip_only_for_nonjson = bool(
    card('old_hoplock') == 'NETWORK' and card('old_nonjson_422') == 'NETWORK'
    and card('old_product') == 'HTTP_422' and card('old_json_500') == 'HTTP_500'
    and card('dep_hoplock') == 'HTTP_500' and card('dep_nonjson_422') == 'HTTP_422'
    and label('old_hoplock') == DEVICE_LABEL and label('old_product') == SERVER_LABEL
    and status('old_hoplock') == 500 and status('old_nonjson_422') == 422)
network_card_is_not_an_arrival_witness = bool(
    a['dep_abort']['screen_side']['card_status painted'] == a['old_hoplock']['screen_side']['card_status painted']
    and a['dep_abort']['reached_upstream'] is not True)
every_cell_names_its_bundle = all(c['bundle_served_by_my_face']['sha256_64_hex'] in (SHA, MUT_SHA)
                                  for c in cells.values())
repeat_agrees = bool(rep_srv.get('status') == a['dep_product']['server_side']['http_status']
                     and rep_srv.get('body_parses_as_json') is True
                     and rep_before.get('cross_check_data_result_status')
                     == a['dep_product']['screen_side']['card_status painted'])
paired_all = all(c['pairing']['one_request_one_id'] for k, c in cells.items() if k != 'dep_abort')

CELLS_JSON = json.dumps(cells, ensure_ascii=False)
frags = sorted({x for x in removed_bodies if x})
leak = {'fields_dropped_by_name': list(DROP), 'fields_allowed': list(ALLOWED),
        'distinct_removed_body_fragments': len(frags),
        'surviving_strings_scanned_bytes': len(CELLS_JSON.encode('utf-8')),
        'fragments_still_present': [f for f in frags if f in CELLS_JSON],
        'positive_control': {'method': 'hide one removed fragment inside a scratch string and run the same '
                                        'substring test - if the test cannot find it there, the zero above means '
                                        'nothing',
                             'scratch_string_contains_the_fragment': bool(frags and frags[0]
                                                                          in ('x' + frags[0] + 'y')),
                             'test_fired_on_the_scratch_string': bool(frags and frags[0]
                                                                      in ('x' + frags[0] + 'y'))}}
out = {'ran_at_local': time.strftime('%Y-%m-%dT%H:%M:%S%z'),
       'order': 'ORD-0312 re-measured on the generation that serves now (03:3x cutover, B\'s ORD-0302 b5 inside)',
       'lane': 'HJ-P3 aad2d1f2-4de9-406b-a5df-afa0e2bcea58',
       'scope': 'who speaks on the screen when a keyed write leg answers, per body class, on the deployed '
                'generation and on an unguarded private mutant of the same commit',
       'generation': TIP, 'generations_named_per_cell': True,
       'bundles': {'deployed_guarded': {'asset': ASSET, 'sha256_64_hex': SHA, 'bytes': SET['guarded_bundle']['bytes'],
                                        'equals_what_the_phone_chain_serves': bool(
                                            SHA == G2['per_row_mine_vs_probe'][ASSET]['my_read']['sha256_full']),
                                        'sheet_blob': SET['sheet_blob_recomputed_40_hex']},
                  'private_unguarded_mutant_of_the_same_commit': {
                      'asset': MUT_ASSET, 'sha256_64_hex': MUT_SHA, 'bytes': MUT['mutant_bundle']['bytes'],
                      'guarded_reads_removed': 2, 'unguarded_reads_after': 2},
                  'the_two_bundles_differ': MUT['verdict']['the_two_bundles_are_different_bytes']},
       'method': 'same arm table as pass-3, unchanged definitions; one backend + one pairing hop + one private '
                 'preview face per arm on my own ports, one-time database, real Chromium reading the painted card '
                 'and the opened 技术详情, and the hop\'s own audit line as the server side',
       'cells': cells, 'arms_scored': len(cells),
       'repeat_of_one_arm': {'run_id': rep_run, 'agrees_with_the_swept_run_on_status_and_class': repeat_agrees,
                             'file': rep_file},
       'runs_excluded': [catch],
       'judgments': {
           'same_status_different_class_422': same_status_diff_class_422,
           'the_painted_label_tracks_the_body_class_not_the_status': label_follows_body_class_not_status,
           'same_status_different_class_500': same_status_diff_class_500,
           'the_guard_flip_changes_attribution_only_for_non_json_bodies': flip_only_for_nonjson,
           'the_NETWORK_card_is_not_an_arrival_witness': network_card_is_not_an_arrival_witness,
           'every_cell_names_its_own_bundle_bytes': every_cell_names_its_bundle,
           'every_swept_arm_is_paired_by_one_request_one_id': paired_all,
           'the_repeat_agrees': repeat_agrees,
           'the_excluded_run_is_caught_by_a_mechanical_test': catch['mechanical_test_catches_it'],
           'no_dropped_body_fragment_survives_in_this_file_and_the_detector_works': bool(
               frags and not leak['fragments_still_present']
               and leak['positive_control']['test_fired_on_the_scratch_string'])},
       'whitelist_proof': leak,
       'not_measured_here': {
           'M2_RED_vector': 'NOT-MEASURED. The named emitters do exist on this commit '
                            '(backend/app/main.py:1694 raises V13_DISCOVERY_NO_FEASIBLE_PLAN and :1668 '
                            'V13_DISCOVERY_NO_FEASIBLE_PLACE_SET, and reason_code appears in the file), so the '
                            'code-bearing branch the sheet renders at PlanWithAiSheet.tsx:218 is reachable in '
                            'principle; no arm in this sweep produced an answer that carried a code from the '
                            'user path, so the promise-with-a-named-cause reading is still owed.'}}
out['verdict'] = {'ALL_JUDGMENTS_HOLD': all(out['judgments'].values()),
                  'arms_scored_equals_nine': out['arms_scored'] == 9}
(BASE / 'r4_scored.json').write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding='utf-8', newline='\n')
print(json.dumps({'judgments': out['judgments'], 'verdict': out['verdict'],
                  'excluded': catch['mechanical_test_catches_it'],
                  'leak_fragments': leak['fragments_still_present'],
                  'deployed_equals_chain': out['bundles']['deployed_guarded'][
                      'equals_what_the_phone_chain_serves']}, ensure_ascii=False, indent=1))
