"""ORD-0301 pass 3, stage 3: the arm table, declared before any of it runs.

The two corrections this pass exists to make, written as arms rather than as promises:

  (2) one chain. Every row's "server side" is the audit line this batch's own proxy wrote for THIS request,
      carrying the id it minted for it and echoed in `X-HJP3-Pair`; the "screen side" is what the page's own
      fetch, the browser's own network stack, and the painted card say for that same id. Nothing anywhere in
      this file opens a second connection to the backend to ask "what did you answer" - in the two rows that
      matter most (A1, A3) the answer came from the product itself, in-chain, and `reached_upstream` is true.

  (3) two classes, never merged. 非 JSON 正文 and 带 envelope 的 4xx are separate arms, and each class is run
      at BOTH status codes so the class label cannot be a restatement of the status: A1 is a real non-JSON
      500, A5 is a non-JSON 422, A3 is a real JSON envelope 422, A7 is a JSON envelope 500. Each class is run
      on both generations, because the mechanism under test (an unguarded `body.detail` at PlanWithAiSheet
      :147/:155) is a property of the bundle, and the deployed bundle is not the one the 21:5x note named.

Who produced each answer is part of the row, not a footnote: A1-A4 and A9 are answered by the product (or by
nobody, in A9's case); A5-A8 are answered by this instrument and say `answered_by: instrument_origin_per_spec`
in their own audit line. A9 exists so the card in A1 cannot be read as "the screen knows a 500 happened": if
a true transport death paints the same card as a contentless 500 on a given generation, that card carries no
information about arrival, and only the pairing does.
"""
from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys
import time

BASE = pathlib.Path('D:/moodle/_hjp3_0301p3_0925')
RIG = 'D:/moodle/HJ-P3_evidence/p3_rig.py'
CELLS = 'D:/moodle/HJ-P3_evidence/p3_cells.cjs'
PAIR_LOG = BASE / 'p3_pair_log.jsonl'
READY = BASE / 'p3_sheet_ready.flag'
TIPS = {'dep': '7856e03f6238da3000976eb6e690a448dfa39b9a',
        'old': 'dc964086c9d412573ac19d70b24b30e6c3ee6168'}

# the traveller's own words, passed positionally on purpose: two arms of this pass died when the runner put
# a flag in this slot and the sheet's 8-character gate (PlanWithAiSheet:472) correctly refused to send
REQUEST_TEXT = '想傍晚在老城慢慢走一圈，别太赶'
SPEC_NONJSON_422 = {'name': 'nonjson_422', 'status': 422, 'reason': 'Unprocessable Entity',
                    'content_type': 'text/plain; charset=utf-8', 'body': 'Request validation failed'}
SPEC_JSON_500 = {'name': 'json_envelope_500', 'status': 500, 'reason': 'Internal Server Error',
                 'content_type': 'application/json',
                 'body': {'error': {'code': 'INTERNAL_ERROR',
                                    'message': 'The server could not complete this request',
                                    'message_key': 'error.internal_error',
                                    'trace_id': 'p3-instrument-composed-not-a-product-trace',
                                    'details': None}}}

# gen, scenario, proxy mode, spec, lock plan, what this arm is FOR
ARMS = [
    ('dep', 'hoplock', 'lock_behind_hop', None, None,
     'A1 the product\'s own contentless non-JSON 500 on a contended write, on the generation the shared page '
     'actually serves: does 技术详情 exist, and who does the card say spoke. The contention is created by the '
     'same hop that pairs the leg, because the earlier flag-file recipe lost the click twice (P3-222548, '
     'P3-222650 in runs_excluded)'),
    ('old', 'hoplock', 'lock_behind_hop', None, None,
     'A2 the same real answer on the unguarded generation: the crash branch, paired leg for leg'),
    ('dep', 'product', 'mutate_extra_key', None, None,
     'A3 the product\'s own JSON 4xx envelope on the same leg in the same chain (this hop adds one forbidden '
     'key so the server\'s validator renders its real body): the envelope class on the deployed generation'),
    ('old', 'product', 'mutate_extra_key', None, None,
     'A4 the same real envelope on the unguarded generation: an object body must survive :147/:155'),
    ('dep', 'spec', 'answer_spec', SPEC_NONJSON_422, None,
     'A5 non-JSON body at the SAME status as A3: separates "the body was not JSON" from "it was a 4xx"'),
    ('old', 'spec', 'answer_spec', SPEC_NONJSON_422, None,
     'A6 the same non-JSON 4xx on the unguarded generation'),
    ('dep', 'spec', 'answer_spec', SPEC_JSON_500, None,
     'A7 a JSON envelope at the SAME status as A1: separates "the body was JSON" from "it was a 5xx"'),
    ('old', 'spec', 'answer_spec', SPEC_JSON_500, None,
     'A8 the same JSON 5xx on the unguarded generation'),
    ('dep', 'abort', 'pass', None, None,
     'A9 negative control on the deployed generation: a leg that never reaches the hop. If the card equals '
     'A1\'s, that card proves nothing about arrival and only the pairing does'),
]


def log_offset():
    return PAIR_LOG.stat().st_size if PAIR_LOG.exists() else 0


def new_log_lines(offset):
    if not PAIR_LOG.exists():
        return []
    with PAIR_LOG.open(encoding='utf-8') as f:
        f.seek(offset)
        return [json.loads(x) for x in f.read().splitlines() if x.strip()]


def access_log_for(path, needle='agent/commands'):
    """A third, independent witness for the same leg: the product process' own access log."""
    if not path or not pathlib.Path(path).exists():
        return {'present': False}
    lines = [l for l in pathlib.Path(path).read_text(encoding='utf-8', errors='replace').splitlines()
             if needle in l]
    return {'present': True, 'path': pathlib.Path(path).name, 'lines_naming_the_leg': len(lines),
            'lines': [l[-120:] for l in lines[:4]]}


def pair(legs_all, consumed, cdp, lines):
    """Every write leg of the run, paired with itself by the id this hop minted for it."""
    posts = [l for l in legs_all if l['method'] == 'POST' and l.get('api')]
    out = []
    for w in posts:
        pid = w.get('pair_id')
        srv = [x for x in lines if x.get('pair_id') == pid]
        cons = [c for c in consumed if c.get('pair_id') == pid]
        cdp1 = [c for c in cdp if c.get('pair_id') == pid]
        s = srv[0] if srv else {}
        out.append({
            'leg': w['url'].split('/api/v1/journeys/')[-1].split('?')[0],
            'pair_id': pid,
            'one_request_one_id': bool(pid and len(srv) == 1 and len(cdp1) == 1),
            'server_side_from_the_same_hop': {
                'recorded': bool(srv), 'reached_upstream': s.get('reached_upstream'),
                'answered_by': s.get('answered_by'), 'status': s.get('upstream_status'),
                'content_type': s.get('content_type'), 'bytes': s.get('bytes'),
                'body_parses_as_json': s.get('body_parses_as_json'),
                'top_level_keys': s.get('top_level_keys'), 'body_head': s.get('body_head'),
                'elapsed_ms': s.get('upstream_elapsed_ms'),
                'hop_lock': s.get('hop_lock'),
                'request_mutation': s.get('request_mutation'), 'spec_name': s.get('spec_name')},
            'screen_side_from_the_page': {
                'fetch_rejected': w.get('fetch_rejected'), 'status': w.get('status'),
                'ok': w.get('ok'), 'content_type': w.get('content_type'),
                'elapsed_ms': w.get('elapsed_ms'),
                'app_read_the_body': cons[0] if cons else None,
                'body_parse_failed': bool(cons and cons[0].get('parsed') is False),
                'body_parsed': bool(cons and cons[0].get('parsed')),
                'browser_stack': cdp1[0] if cdp1 else None},
            'both_ends_agree_on_status': bool(srv and w.get('status') == s.get('upstream_status')),
            'both_ends_agree_on_json_class': bool(
                srv and cons and s.get('body_parses_as_json') == cons[0].get('parsed')),
        })
    return out


def run_arm(gen, scenario, mode, spec, lock_plan, intent):
    stamp = time.strftime('%H%M%S')
    run_id = 'P3-%s' % stamp
    out = {'arm': '%s_%s_%s' % (gen, scenario, (spec or {}).get('name') or mode), 'run_id': run_id,
           'intent_declared_before': intent, 'tip': TIPS[gen], 'scenario': scenario,
           'proxy_mode': mode, 'spec': spec, 'lock_plan': lock_plan}
    argv = [sys.executable, RIG, 'start', gen, mode]
    if spec:
        argv.append(json.dumps(spec, ensure_ascii=False))
    r = subprocess.run(argv, capture_output=True, text=True, encoding='utf-8', errors='replace')
    print('  rig: ' + (r.stdout or r.stderr).strip()[-220:], flush=True)
    if r.returncode != 0:
        out['failed'] = 'rig start rc=%d' % r.returncode
        out['rig_tail'] = (r.stdout or '')[-400:] + (r.stderr or '')[-400:]
        (BASE / ('p3_arm_%s_%s.json' % (out['arm'], run_id))).write_text(
            json.dumps(out, ensure_ascii=False, indent=1), encoding='utf-8', newline='\n')
        return out
    st = json.loads((BASE / 'p3_rig_state.json').read_text(encoding='utf-8'))
    assert st['which'] == gen and st['tip'] == TIPS[gen], 'rig state does not name this arm'
    out['rig'] = {'backend_pid': st['backend']['pid'], 'proxy_pid': st['proxy']['pid'],
                  'face_pid': st['face']['pid'], 'face_port': st['face']['port'],
                  'all_up': bool(st['backend']['up'] and st['proxy']['up'] and st['face']['up']),
                  'identity_two_sided': st['identity']['two_sided'],
                  'journey_id': st['seed']['journey_id'], 'seed': st['seed']['seed'],
                  'db': str(BASE / ('p3_%s.s3db' % gen)),
                  'access_log': pathlib.Path(st['backend']['access_log_path']).name,
                  'rig_state_file': 'p3_rig_state_%s_%s_%s.json' % (gen, mode, st['stamp'])}
    off = log_offset()
    if READY.exists():
        READY.unlink()
    lk = None
    if lock_plan:
        lf = open(BASE / ('p3_lock_%s.log' % run_id), 'w', encoding='utf-8')
        lk = subprocess.Popen([sys.executable, RIG, 'lock', gen, lock_plan], stdout=lf,
                              stderr=subprocess.STDOUT)
    cell_path = BASE / ('p3_cell_%s_%s.json' % (out['arm'], run_id))
    cmd = ['node', CELLS, 'http://127.0.0.1:%d' % st['face']['port'], st['seed']['journey_id'],
           str(cell_path), scenario, str(READY), REQUEST_TEXT]
    out['request_text'] = REQUEST_TEXT
    out['request_text_chars'] = len(REQUEST_TEXT.strip())
    if scenario in ('lock', 'hoplock'):
        cmd.append('--shot')
    t0 = time.time()
    try:
        rn = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace',
                           timeout=420, cwd=str(BASE), env=dict(os.environ, PYTHONIOENCODING='utf-8'))
        out['node_rc'] = rn.returncode
        out['node_tail'] = [(rn.stdout or '').strip().splitlines()[-1:]] + (
            ['STDERR:' + rn.stderr[-200:]] if (rn.stderr or '').strip() else [])
    except subprocess.TimeoutExpired:
        out['node_rc'] = 'timeout'
    if lk:
        lk.wait(timeout=180)
    out['wall_seconds'] = int(time.time() - t0)
    cell = json.loads(cell_path.read_text(encoding='utf-8')) if cell_path.exists() else {}
    lines = new_log_lines(off)
    out['pairing'] = pair(cell.get('legs', []), cell.get('consumed', []), cell.get('cdp', []), lines)
    out['write_legs_with_a_5xx_or_4xx'] = [
        {'leg': p['leg'], 'status': p['server_side_from_the_same_hop']['status'],
         'answered_by': p['server_side_from_the_same_hop']['answered_by'],
         'json': p['server_side_from_the_same_hop']['body_parses_as_json'],
         'page_saw': p['screen_side_from_the_page']['status'],
         'rejected': p['screen_side_from_the_page']['fetch_rejected']}
        for p in out['pairing']
        if p['server_side_from_the_same_hop']['status'] and p['server_side_from_the_same_hop']['status'] >= 400]
    SCREEN_KEYS = (
        'result_card_painted', 'result_card_text_content', 'card_title_painted', 'card_body_painted',
        'reason_label_painted', 'reason_value_painted', 'reason_label_text_content',
        'reason_value_text_content', 'details_elements_present', 'details_open_attribute',
        'detail_toggle_present', 'network_card_painted', 'http_failed_card_painted',
        'refused_card_painted', 'server_attribution_painted', 'device_attribution_painted',
        'unreadable_answer_note_painted', 'whole_page_contains_server_label',
        'whole_page_contains_device_label', 'next_step_painted', 'cross_check_data_result_status',
        'cross_check_data_reason_origin')
    out['screen_as_painted_before_tapping'] = {k: (cell.get('after_open') or {}).get(k)
                                               for k in SCREEN_KEYS}
    out['screen_as_painted_after_tapping_detail'] = {k: (cell.get('after_details_opened')
                                                         or cell.get('after_open') or {}).get(k)
                                                     for k in SCREEN_KEYS}
    out['detail_block_open_attempt'] = cell.get('open_attempt')
    out['screen'] = out['screen_as_painted_before_tapping']
    out['page_errors'] = cell.get('page_errors')
    out['waited_ms'] = cell.get('waited_ms')
    out['sample_tail'] = cell.get('samples')
    out['access_log_witness'] = access_log_for(st['backend']['access_log_path'])
    subprocess.run([sys.executable, RIG, 'stop'], capture_output=True, text=True,
                   encoding='utf-8', errors='replace')
    (BASE / ('p3_arm_%s_%s.json' % (out['arm'], run_id))).write_text(
        json.dumps(out, ensure_ascii=False, indent=1), encoding='utf-8', newline='\n')
    s = out['screen_as_painted_before_tapping']
    o = out['screen_as_painted_after_tapping_detail']
    print('  -> %s | card=%s | title=%s | label=%s | reason=%s | details=%s/%s | legs=%d | paired=%s | %s'
          % (out['arm'], s.get('cross_check_data_result_status'), s.get('card_title_painted'),
             o.get('reason_label_text_content'), o.get('reason_value_text_content'),
             s.get('details_elements_present'), s.get('details_open_attribute'),
             len(out['pairing']), all(p['one_request_one_id'] for p in out['pairing']),
             json.dumps(out['write_legs_with_a_5xx_or_4xx'], ensure_ascii=False)[:200]), flush=True)
    return out


if __name__ == '__main__':
    if sys.argv[1] == 'list':
        print(json.dumps([{'arm': '%s/%s' % (a[0], (a[3] or {}).get('name') or a[2]),
                           'intent': a[5]} for a in ARMS], ensure_ascii=False, indent=1))
        raise SystemExit(0)
    idxs = sys.argv[1].split(',') if sys.argv[1] != 'all' else [str(i) for i in range(len(ARMS))]
    summary = []
    for i in idxs:
        a = ARMS[int(i)]
        summary.append(run_arm(*a))
    print(json.dumps([{'arm': x['arm'], 'failed': x.get('failed', False)} for x in summary],
                     ensure_ascii=False))
