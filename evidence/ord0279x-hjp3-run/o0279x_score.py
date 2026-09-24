"""ORD-0279-X scoring: derive every verdict from measured rows, then write the readings artefact.

Only the tree changed versus ORD-0279 (that is the order).  Readings that can be recomputed from disk are
recomputed here (export proof, store facts, screenshot identities, the previous generation's readings), so
the cross-generation table is a diff of two artefacts rather than a paragraph of memory.  No verdict is a
literal; no duration is asserted.
"""
from __future__ import annotations

import hashlib
import io
import json
import pathlib
import re
import time

BASE = pathlib.Path('D:/moodle/_hjp3_0279x_0925')
OLD = pathlib.Path('D:/moodle/_hjp3_0279_0924/O0279-2502_readings.json')
RUN_ID = 'O0279X-2504'
MARKER = 'MARKER-X-0279-2504'
SERVER_BODY_500 = 'Internal Server Error'
LABEL = '服务器给出的原因'

exp = json.loads((BASE / 'o0279x_export_proof.json').read_text(encoding='utf-8'))
store = json.loads((BASE / 'o0279x_dbfacts_final.json').read_text(encoding='utf-8'))
old = json.loads(OLD.read_text(encoding='utf-8'))
locklog = (BASE / 'o0279x_lock_selfproof.txt').read_text(encoding='utf-8').splitlines()
belog = (BASE / 'o0279x_backend.log').read_text(encoding='utf-8', errors='replace')

LEGS = {
    'user_path_agent_commands': {'status': 200, 'elapsed_ms': 67, 'ct': 'application/json', 'bytes': 7083,
                                'client_error': None, 'body': None,
                                'note': 'real tap on the sheet; created mission 4d70080c at 20:20:57Z'},
    'user_path_plans_generate': {'status': 422, 'elapsed_ms': 55, 'ct': 'application/json', 'bytes': 1443,
                                 'client_error': None,
                                 'request_body': '{"candidate_count":3}',
                                 'request_headers_seen_by_page': {'Content-Type': 'application/json'},
                                 'note': 'the sheet\'s own second leg carries no mission_id and no '
                                         'Idempotency-Key, so it never reaches the receipt machinery'},
    'contention_legA': {'status': 500, 'elapsed_ms': 32379, 'ct': 'text/plain; charset=utf-8',
                        'bytes': 21, 'client_error': None, 'body': SERVER_BODY_500},
    'cancel_leg': {'status': None, 'elapsed_ms': 7046, 'ct': None, 'bytes': None,
                   'client_error': 'AbortError: signal is aborted without reason',
                   'body': None, 'note': 'the user pressed 取消 while the write was parked'},
}
REPLAY = {'status_first': 422, 'status_second': 422, 'code_equal': True, 'message_equal': True,
          'message_key_equal': True, 'reason_code': 'CATALOG_INSUFFICIENT',
          'details_key_count_first': 6, 'details_key_count_second': 6,
          'raw_bodies_equal': False, 'trace_ids_equal': False,
          'equal_after_dropping_trace_id': True}
RENDER = {'label': LABEL, 'value_real_origin': 'HTTP 500', 'value_marker_origin': MARKER,
          'real_origin_hit_test': 'CODE', 'real_origin_rect': {'w': 301, 'h': 25},
          'marker_hit_test': 'SECTION'}
CARD = {'failed': '服务端处理失败 / 这次是服务端出错，不是你的需求有问题。行程未被改动，可稍后重试；'
                  '反复出现请保留“技术详情”。',
        'cancelled': '已中止后续核对 / 请求本身已经发出去了，可能已经生成方案。请先刷新确认，不要重复提交。',
        'insufficient': '这次排不出方案：数据不够，不是你说的不对 / 这座城我们手上的地点太少，配不平一天的行程。'
                        '（服务器给的原因编号：CATALOG_INSUFFICIENT）'}

access_lines = len(re.findall(r'"POST /api/v1/journeys/[0-9a-f-]+/agent/commands HTTP/1\.1"', belog))
receipt_rows = store['idempotency_keys']
key_forms = sorted({r['key'].split(':')[1] if r['key'].startswith('plans.generate:cont:') else 'header-key'
                    for r in receipt_rows})
missions = store['counts']['journey_missions']

# --- verdicts, each derived from the readings above -------------------------------------------
loser = LEGS['contention_legA']
not200 = loser['status'] != 200
named = bool(re.search(r'"code"\s*:', loser['body'] or ''))
v_shape = 'NOT_200_BUT_UNNAMED' if (not200 and not named) else ('NAMED_AND_NOT_200' if not200 else 'ANSWERED_200')
old_shape = old['derived']['W1b_loser_answer']['verdict']

user_receipts = [r for r in receipt_rows if r['created_at'] < '2026-09-24T20:22:00']
v_receipt = ('RECEIPT_MACHINERY_LIVE_BUT_NOT_ON_THE_SHEET_LEG'
             if (not user_receipts and len(receipt_rows) >= 2 and all(r['filled'] for r in receipt_rows))
             else 'UNRESOLVED')

failed_new_rows = missions - 1  # the clean leg created exactly one mission row
v_trace = ('NO_DURABLE_TRACE_FOR_FAILED_WRITE_ON_THIS_PATH'
           if (failed_new_rows == 0 and loser['status'] == 500) else 'TRACE_PRESENT')

eq_real = SERVER_BODY_500 == RENDER['value_real_origin']
eq_marker = MARKER == RENDER['value_marker_origin']
v_w2 = ('CLIENT_SUBSTITUTES_A_STATUS_STRING_FOR_THE_SERVER_REASON' if (not eq_real and eq_marker)
        else 'NO_SUBSTITUTION_OBSERVED')
old_w2 = old['derived']['W2_rendered_reason']['verdict']

v_cancel = ('CANCEL_IS_MANUAL_ABORT_ONLY'
            if (LEGS['cancel_leg']['client_error'] and 'Abort' in LEGS['cancel_leg']['client_error']
                and failed_new_rows == 0) else 'CANCEL_SEMANTICS_UNRESOLVED')
v_replay = ('REPLAY_IS_EQUAL_ONCE_TRACE_ID_IS_EXCLUDED' if REPLAY['equal_after_dropping_trace_id']
            and not REPLAY['raw_bodies_equal'] else 'REPLAY_COMPARISON_NEEDS_A_BASIS')

shots = [{'file': p.name, 'bytes': p.stat().st_size, 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()}
         for p in sorted(BASE.glob('shots_O0279X-*.png'))]

out = {
    'order': 'ORD-0279-X WRITE_LEG_HAS_NO_DEADLINE @ landed generation', 'run_id': RUN_ID,
    'lane': 'HJ-P3 aad2d1f2', 'measured_at_local': time.strftime('%Y-%m-%dT%H:%M:%S%z'),
    'variable': 'tree only - backend dcae1bc9 on its own one-time DB; the previous tip stays running as '
                'the control arm, and the served bundle is unchanged because ORD-0272 touched no frontend file',
    'tree': exp, 'services': {'backend': '127.0.0.1:8493', 'face': '127.0.0.1:8494',
                              'proxy_ownership': 'mine_via_face 200 / foreign_via_face 404 / mine_direct 200',
                              'control_pair_left_running': '127.0.0.1:8497 + :8498 (tree c79e2b4)'},
    'lock_windows': {'log_lines': locklog,
                     'self_proved': sum(1 for l in locklog if l.startswith('SELFPROOF')) >= 2},
    'legs': LEGS, 'replay_pair': REPLAY, 'rendered': RENDER, 'cards': CARD,
    'store': store, 'access_log_agent_commands_lines': access_lines,
    'derived': {
        'X_S1_server_answer_shape': {'verdict': v_shape, 'not_200': not200, 'server_named_a_code': named,
                                     'body': loser['body'], 'body_bytes': loser['bytes'],
                                     'previous_generation_verdict': old_shape,
                                     'transfers': v_shape == old_shape},
        'X_S2_idempotency_receipts': {'verdict': v_receipt, 'rows_after_user_path': len(user_receipts),
                                      'rows_now': len(receipt_rows), 'key_forms_present': key_forms,
                                      'all_filled': all(r['filled'] for r in receipt_rows),
                                      'statuses': sorted({r['status'] for r in receipt_rows})},
        'X_S3_failed_write_trace': {'verdict': v_trace, 'new_mission_rows_from_failed_legs': failed_new_rows,
                                    'scope': 'this path (agent/commands under a held write lock); a 422 '
                                             'plans.generate WITH continuation identity does leave a filled '
                                             'receipt, so the previous run\'s blanket sentence is narrowed here',
                                    'narrows_previous_claim': 'NOT_TRANSFERABLE_AS_A_BLANKET_CLAIM'},
        'X_W2_rendered_reason': {'verdict': v_w2, 'server_equals_rendered_real_origin': eq_real,
                                 'server_equals_rendered_marker_origin': eq_marker,
                                 'token_present_in_server_bytes': 'HTTP 500' in SERVER_BODY_500,
                                 'previous_generation_verdict': old_w2, 'transfers': v_w2 == old_w2},
        'X_cancel_semantics': {'verdict': v_cancel,
                               'client_error': LEGS['cancel_leg']['client_error'],
                               'card_says': CARD['cancelled'],
                               'access_log_lines_baseline': 2, 'access_log_lines_now': access_lines,
                               'instrument_gap_named': 'uvicorn writes the access line when the response is '
                                                       'sent, so an aborted request leaves no log line - the '
                                                       'durable store, not the log, is what answers this'},
        'X_replay_equality': {'verdict': v_replay,
                              'correction': 'my first comparison used raw bodies and reported them unequal; '
                                            'the only differing field was trace_id, so the unequal reading '
                                            'had no basis - both arms are recorded here',
                              'raw_bodies_equal': REPLAY['raw_bodies_equal'],
                              'equal_after_dropping_trace_id': REPLAY['equal_after_dropping_trace_id']},
        'X_no_deadline_on_writes': {'note': 'not re-measured on this tree because the emitting file is the '
                                            'same bytes: PlanWithAiSheet.tsx blob equals across the two tips, '
                                            'and the shipped bundle was not rebuilt',
                                    'sheet_blob_matches_commander_quote':
                                        exp['cited']['frontend/src/features/planning/PlanWithAiSheet.tsx']['matches_commander_quote'],
                                    'previous_generation_verdict':
                                        old['derived']['W1a_write_leg_deadline']['verdict']},
    },
    'screenshots': shots, 'screenshots_distinct': len({s['sha256'] for s in shots}) == len(shots),
}
(BASE / (RUN_ID + '_readings.json')).write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding='utf-8')
print(json.dumps(out['derived'], ensure_ascii=False, indent=1))
print('shots', json.dumps(shots, ensure_ascii=False))
print('access lines', access_lines, 'receipt rows', len(receipt_rows), 'missions', missions)
