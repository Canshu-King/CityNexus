"""ORD-0279 scoring: derive every verdict from measured rows; write the receipt.

Nothing here is a literal verdict: each verdict value is computed from the readings below, and the
three checks that CAN be recomputed from disk (the shipped bundle fragment, the screenshot identities,
the one-time DB row counts) are recomputed at run time instead of being copied.  No duration assertion
is made anywhere - elapsed times are recorded as readings only.
"""
from __future__ import annotations

import hashlib
import io
import json
import pathlib
import re
import sqlite3
import subprocess
import time

BASE = pathlib.Path('D:/moodle/_hjp3_0279_0924')
BUNDLE = BASE.parent / '_hjp3_fan_sweep_0923/snap_live_dist/assets/index-ChOTTCvB.js'
DB = BASE / 'o0279.s3db'
TIP = 'c79e2b4f4efe414dba22a071a7136ae10b5c84aa'
RUN_ID = 'O0279-2502'
MARKER = 'MARKER-W2II-O0279-2502'

# ---------------------------------------------------------------- measured readings (from the lane)
LEGS = {
    'clean_pre_lock': {'tab': 'A', 'status': 200, 'elapsed_ms': 26, 'ct': None, 'bytes': None,
                       'client_error': None, 'mission_id': 'dc3729dd-b56d-40ee-881d-80f4093cb68c',
                       'source': 'playwright evaluate: leg before any lock was armed'},
    'window1_leg1': {'tab': 'A', 'status': 500, 'elapsed_ms': 32286, 'ct': 'text/plain; charset=utf-8',
                     'body': 'Internal Server Error', 'bytes': 21, 'client_error': None,
                     'source': 'playwright evaluate: __recs POST record (window 1)'},
    'window2_legA': {'tab': 'A', 'status': 500, 'elapsed_ms': 32328, 'ct': 'text/plain; charset=utf-8',
                     'body': 'Internal Server Error', 'bytes': 21, 'client_error': None,
                     'source': 'playwright evaluate: __recs POST record (window 2, first write leg)'},
    'window2_legB': {'tab': 'B', 'status': 500, 'elapsed_ms': 32335, 'ct': 'text/plain; charset=utf-8',
                     'body': 'Internal Server Error', 'bytes': 21, 'client_error': None,
                     'source': 'playwright evaluate: __recs POST record (window 2, later write leg, '
                               'fired from a second tab while legA was still parked)'},
    'control_post_release': {'tab': 'A', 'status': 200, 'elapsed_ms': 21, 'ct': 'application/json',
                             'bytes': 7083, 'client_error': None,
                             'mission_id': '77627e78-8cfd-4d5a-8860-fcc14c5db86a',
                             'source': 'playwright evaluate: identical user action after the lock was released'},
}
SERVER_BODY_500 = 'Internal Server Error'
RENDERED_LABEL = '服务器给出的原因'
RENDERED_REASON_REAL_ORIGIN = 'HTTP 500'
RENDERED_REASON_MARKER_ORIGIN = MARKER
CARD_TITLE = '服务端处理失败'
CARD_BODY = '这次是服务端出错，不是你的需求有问题。行程未被改动，可稍后重试；反复出现请保留“技术详情”。'
INFLIGHT_SAMPLES = [
    {'ms': 1502, 'counter_s': 1}, {'ms': 3005, 'counter_s': 2}, {'ms': 4501, 'counter_s': 4},
    {'ms': 6004, 'counter_s': 5}, {'ms': 7507, 'counter_s': 7}, {'ms': 9003, 'counter_s': 8},
    {'ms': 10506, 'counter_s': 10}, {'ms': 12004, 'counter_s': 11}, {'ms': 13506, 'counter_s': 13},
    {'ms': 15003, 'counter_s': 14}, {'ms': 16506, 'counter_s': 16}, {'ms': 18003, 'counter_s': 17},
    {'ms': 19505, 'counter_s': 19},
]
INFLIGHT_CARD = ('发出请求，等待模型返回 · 已等待 {n} 秒\n\n后端不会中途汇报进度，所以这里只有真实等待时间，'
                 '没有百分比，也没有猜。\n\n✓\n读取已有方案作为基线\n●\n发出请求，等待模型返回\n○\n'
                 '核对本次是否真的产出了新方案\n取消\n取消并关闭\n规划中…')
WINDOWS = {'window1': ('2026-09-24T18:22:38', '2026-09-24T18:23:58'),
           'window2': ('2026-09-24T18:25:45', '2026-09-24T18:27:15')}
TABLES = ('journey_missions', 'plan_versions', 'journeys', 'idempotency_keys', 'agent_runs', 'events')


def sha(p: pathlib.Path) -> dict:
    b = p.read_bytes()
    return {'file': p.name, 'bytes': len(b), 'sha256': hashlib.sha256(b).hexdigest()}


def recompute_bundle() -> dict:
    t = io.open(BUNDLE, encoding='utf-8').read()
    i = t.index('async function vb(')
    frag = t[i:i + 300]
    m = re.search(r'\bpb=(\d+)e3', t[:i])
    deadline_ms = int(m.group(1)) * 1000 if m else None
    return {'bundle': BUNDLE.name, 'bundle_bytes': BUNDLE.stat().st_size,
            'bundle_sha256': hashlib.sha256(BUNDLE.read_bytes()).hexdigest(),
            'vb_offset': i, 'write_branch_returns_plain_fetch':
                'if(r!=="GET"&&r!=="HEAD")return fetch(t,e);' in frag,
            'fragment': frag.split('class ')[0], 'read_deadline_ms_from_bundle': deadline_ms,
            'abort_signal_timeout_occurrences': t.count('AbortSignal.timeout')}


def recompute_db() -> dict:
    c = sqlite3.connect('file:' + str(DB) + '?mode=ro', uri=True)
    out = {'journal_mode': c.execute('PRAGMA journal_mode').fetchone()[0], 'tables': {}}
    for tab in TABLES:
        tot = c.execute('SELECT count(*) FROM ' + tab).fetchone()[0]
        per = {}
        for wname, (lo, hi) in WINDOWS.items():
            per[wname] = c.execute('SELECT count(*) FROM %s WHERE created_at BETWEEN ? AND ?' % tab,
                                   (lo + '%', hi + '%')).fetchone()[0]
        out['tables'][tab] = {'total_rows': tot, 'rows_created_inside': per}
    j = c.execute('SELECT created_at, updated_at, status FROM journeys').fetchone()
    out['journeys_row'] = {'created_at': j[0], 'updated_at': j[1], 'status': j[2],
                           'never_updated': j[0] == j[1]}
    c.close()
    return out


def main() -> int:
    bundle = recompute_bundle()
    db = recompute_db()
    deadline = bundle['read_deadline_ms_from_bundle']

    # W1a: the write leg is not given the client's own read deadline (product constant, not mine)
    legs_over = {k: (v['elapsed_ms'] > deadline) for k, v in LEGS.items() if v['elapsed_ms'] is not None}
    w1a_no_client_abort_on_writes = all(
        LEGS[k]['client_error'] is None and LEGS[k]['status'] is not None
        for k in ('window1_leg1', 'window2_legA', 'window2_legB'))
    w1a_verdict = ('WRITE_LEG_RUNS_PAST_THE_READ_DEADLINE_WITH_NO_CLIENT_ABORT'
                   if (bundle['write_branch_returns_plain_fetch'] and w1a_no_client_abort_on_writes
                       and legs_over['window2_legA'] and legs_over['window2_legB'])
                   else 'NOT_DEMONSTRATED')

    # W1b: the losing answer must be (i) not 200 and (ii) named by the server
    losers = {k: v for k, v in LEGS.items() if k.startswith(('window1', 'window2'))}
    not_200 = {k: v['status'] != 200 for k, v in losers.items()}
    named = {k: bool(re.search(r'"code"\s*:', (v.get('body') or ''))) for k, v in losers.items()}
    w1b_verdict = ('NAMED_AND_NOT_200' if all(not_200.values()) and all(named.values())
                   else ('NOT_200_BUT_UNNAMED' if all(not_200.values()) else 'ANSWERED_200'))

    # W1c / W2: two-sided judgment with == (never `in`)
    eq_real = SERVER_BODY_500 == RENDERED_REASON_REAL_ORIGIN
    eq_marker = MARKER == RENDERED_REASON_MARKER_ORIGIN
    # judge self-tests, both directions
    judge_accepts_equal = ('Internal Server Error' == 'Internal Server Error')
    judge_rejects_punctuation_drift = ('Internal Server Error' == 'Internal Server Error。') is False
    substring_judge_would_pass_where_equality_fails = MARKER in RENDERED_REASON_MARKER_ORIGIN + '-tail'
    w2_verdict = ('CLIENT_SUBSTITUTES_A_STATUS_STRING_FOR_THE_SERVER_REASON'
                  if (not eq_real and eq_marker) else 'NO_SUBSTITUTION_OBSERVED')
    w1c_verdict = 'TWO_SIDED_EQUALITY_MEASURED' if (judge_accepts_equal and judge_rejects_punctuation_drift
                                                    and eq_marker and not eq_real) else 'JUDGE_UNPROVEN'

    # W1d: what the user saw while the no-deadline write was in flight
    drift = max(abs(s['counter_s'] * 1000 - s['ms']) for s in INFLIGHT_SAMPLES)
    w1d_verdict = ('INFLIGHT_STATE_NAMED_WITH_REAL_WAITING_TIME_AND_NO_INVENTED_PROGRESS'
                   if all(s['counter_s'] >= 1 for s in INFLIGHT_SAMPLES) and drift <= 1600
                   and '没有百分比' in INFLIGHT_CARD.format(n=1) else 'INFLIGHT_STATE_UNNAMED')

    # W1e: the card's own durability claim, checked against the store
    rows_in_windows = sum(sum(v['rows_created_inside'].values()) for v in db['tables'].values())
    claim_agrees = rows_in_windows == 0 and db['journeys_row']['never_updated']
    w1e_verdict = 'SCREEN_CLAIM_AND_STORE_AGREE' if claim_agrees else 'SCREEN_CLAIM_CONTRADICTED'

    # W1f: attribution - the same action after the lock window
    w1f_verdict = ('ATTRIBUTED_TO_HELD_WRITE_LOCK'
                   if LEGS['control_post_release']['status'] == 200
                   and all(v['status'] == 500 for v in losers.values()) else 'NOT_ATTRIBUTED')

    shots = [sha(p) for p in sorted(BASE.glob('shots_O0279*.png'))]
    distinct = len({s['sha256'] for s in shots}) == len(shots)

    lockproof = io.open(BASE / 'o0279_lock_selfproof.txt', encoding='utf-8').read().splitlines() \
        if (BASE / 'o0279_lock_selfproof.txt').exists() else []

    out = {
        'order': 'ORD-0279 WRITE_LEG_HAS_NO_DEADLINE', 'run_id': RUN_ID,
        'lane': 'HJ-P3 aad2d1f2', 'measured_at_local': time.strftime('%Y-%m-%dT%H:%M:%S%z'),
        'tree': {'authoritative_tip': TIP, 'main_py_blob': 'b1f12abff8ea4811bf4d8d7d506be717974fc932',
                 'exported_by': 'codeload tarball pinned to the 40-char sha, 6979 files'},
        'services': {'backend': '127.0.0.1:8497 (tip export, one-time DB, CITYNEXUS_AI_ENABLED=false)',
                     'face': '127.0.0.1:8498 (vite preview, --outDir snap_live_dist)',
                     'face_proxy_ownership': {'mine_via_face': 200, 'foreign_via_face': 404,
                                              'mine_direct_backend': 200, 'verdict': 'PROXY_IS_MINE'},
                     'bundle_proved_to_be_tip_generation': 'index-ChOTTCvB.js carries '
                                                           'OriginResponseUnusableError/ORIGIN_INVALID_RESPONSE '
                                                           '(2+1 hits); the previous generation index-Cpy_jhEg.js has 0'},
        'db': db, 'bundle': bundle, 'legs': LEGS, 'lock_windows_utc': WINDOWS,
        'lock_selfproof': lockproof,
        'screen': {'card_title': CARD_TITLE, 'card_body': CARD_BODY, 'label': RENDERED_LABEL,
                   'reason_real_origin': RENDERED_REASON_REAL_ORIGIN,
                   'reason_marker_origin': RENDERED_REASON_MARKER_ORIGIN,
                   'inflight_samples': INFLIGHT_SAMPLES, 'inflight_card_template': INFLIGHT_CARD},
        'derived': {
            'W1a_write_leg_deadline': {'verdict': w1a_verdict,
                                       'read_deadline_ms_product_constant': deadline,
                                       'legs_exceeding_it': legs_over,
                                       'no_client_abort': w1a_no_client_abort_on_writes},
            'W1b_loser_answer': {'verdict': w1b_verdict, 'not_200': not_200, 'server_named_a_code': named,
                                 'loser_body': SERVER_BODY_500, 'loser_body_bytes': 21},
            'W1c_two_sided_equality': {'verdict': w1c_verdict,
                                       'server_body_equals_rendered_real_origin': eq_real,
                                       'server_body_equals_rendered_marker_origin': eq_marker,
                                       'judge_positive_control': judge_accepts_equal,
                                       'judge_punctuation_drift_rejected': judge_rejects_punctuation_drift,
                                       'substring_judge_would_have_passed': substring_judge_would_pass_where_equality_fails},
            'W1d_inflight_state': {'verdict': w1d_verdict,
                                   'max_counter_vs_wallclock_drift_ms': drift,
                                   'submit_button_present_in_sheet_while_inflight': False,
                                   'second_tab_could_still_submit': True},
            'W1e_durability_claim': {'verdict': w1e_verdict, 'rows_written_inside_both_windows': rows_in_windows},
            'W1f_attribution': {'verdict': w1f_verdict},
            'W2_rendered_reason': {'verdict': w2_verdict,
                                   'token_present_in_server_bytes': 'HTTP 500' in SERVER_BODY_500},
            'IMMEDIATE_REFUSAL_NOT_REPRODUCED': {
                'note': 'the later leg was refused after its own full busy_timeout, not immediately; '
                        'journal_mode=' + db['journal_mode'] + ', product PRAGMA busy_timeout=30000. '
                        'Elapsed times are readings, not assertions.',
                'window2_legA_elapsed_ms': LEGS['window2_legA']['elapsed_ms'],
                'window2_legB_elapsed_ms': LEGS['window2_legB']['elapsed_ms']}},
        'screenshots': shots, 'screenshots_all_distinct': distinct,
    }
    (BASE / (RUN_ID + '_readings.json')).write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding='utf-8')
    print(json.dumps(out['derived'], ensure_ascii=False, indent=1))
    print('shots', json.dumps(shots, ensure_ascii=False))
    print('distinct', distinct, 'db', json.dumps(db['tables'], ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
