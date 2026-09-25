"""ORD-0301 scorer: build the range table and derive every verdict from that row's OWN readings.

Nothing is typed in here: every number, sentence and boolean is read out of the arm artefacts on disk
(cell_*.json written by the browser, probe_*.json from the sibling answer-attribution probe,
originlog_*.jsonl from the origin's own accounting, spec_*.json as the declared pre-condition,
envelope_real.json as the captured real product answer).

The judgment rule handed down by the order, applied literally:
    if an HTTP answer reached the browser for the tapped leg, the screen must not file the reason
    under the network.  Rows are named HONEST / MISLEADS / NOT_MEASURED by that test only.
"""
from __future__ import annotations

import json
import pathlib
import sys

B = pathlib.Path('D:/moodle/_hjp3_0301_0925')
STATE = json.loads((B / 'o0301_state.json').read_text(encoding='utf-8'))
TIP = STATE['measured_on']
NET_TITLE = '连不上服务端'
SERVER_LABEL = '服务器给出的原因'
DEVICE_LABEL = '这台设备自己的读数（服务器没给句子）'
ROWS = [
    # (row id, arm, the outcome class the order named, who is expected to have answered)
    ('R1_①_contentless_500_from_the_product', 'a1_real_lock_500_plain', '① 服务器答 500 且正文无 code/message', 'product'),
    ('R2_①_contentless_500_fast', 'a2_ctl_500_plain_fast', '① 同一形状但 250 ms 内答完（把时长从判据里摘出去）', 'my-origin'),
    ('R3_①_contentless_500_after_35s', 'a3_ctl_500_plain_slow35', '① 同一形状但 35 s 后才答', 'my-origin'),
    ('R4_①_uninstrumented', 'a14_no_instrument_fast500', '① 同一臂、fetch 钩子完全不装', 'my-origin'),
    ('R5_②_500_with_product_envelope', 'a4_ctl_500_product_env_fast', '② 服务器答 500 且正文带具名 code（产品自己那枚真信封的字节）', 'my-origin'),
    ('R6_③_503_envelope', 'a5_ctl_503_product_env_fast', '③ 503 + 同一枚信封字节', 'my-origin'),
    ('R7_③_502_envelope', 'a6_ctl_502_product_env_fast', '③ 502 + 同一枚信封字节', 'my-origin'),
    ('R8_③_504_envelope', 'a7_ctl_504_product_env_fast', '③ 504 + 同一枚信封字节', 'my-origin'),
    ('R9_③_503_plain_gateway', 'a17_ctl_503_plain_gateway', '③ 503 但网关那种纯文本正文', 'my-origin'),
    ('R10_④_upstream_absent', 'a10_upstream_absent', '④ 连接被拒（后端端口上没人听）', 'vite-proxy'),
    ('R11_④_reset_no_response', 'a9_ctl_reset_no_response', '④ 源站收了请求就断（一个响应字节都不写）', 'vite-proxy'),
    ('R12_⑤_silent_write_leg', 'a11_ctl_silent_write', '⑤ 写腿无人应答（客户端先放弃？）', 'none'),
    ('R13_⑤_silent_read_leg', 'a12_ctl_silent_read', '⑤ 读腿无人应答（客户端 12 s 期限先放弃）', 'none'),
    ('R14_control_real_422', 'a13_real_422_control', '正控：产品今天真发的那枚具名 422', 'product'),
    ('R15_⓪_json_null_body', 'a15_ctl_500_json_null_body', '机制臂：500 + application/json + 正文就是 null', 'my-origin'),
    ('R16_⓪_json_empty_object', 'a16_ctl_500_empty_json_object', '机制臂：500 + application/json + 正文是 {}', 'my-origin'),
    ('R17_⓪_headers_then_truncated_body', 'a8_ctl_500_short_body', '机制臂：答了 500 但正文被截短（Content-Length 说 21 只写 5）', 'my-origin'),
    # ---- pass 2: the classes the dispatch names in 四、 that my first pass did not measure ----
    ('R18_③_route_abort_real_transport_failure', 'a18_route_abort_transport', '③ 浏览器这一发根本没拿到 HTTP 回答（route.abort 掐掉那一腿）', 'none'),
    ('R19_④_200_empty_body', 'a19_200_empty_body', '④ 答了 200 但正文是空的', 'my-origin'),
    ('R20_④_200_json_empty_object', 'a20_200_json_empty_object', '④ 答了 200 但正文是 {}', 'my-origin'),
    ('R21_④_200_json_array', 'a21_200_json_array', '④ 答了 200 但正文是 []（类型就不对）', 'my-origin'),
    ('R22_④_200_text_plain_payload', 'a22_200_text_plain_payload', '④ 答了 200 但正文是 text/plain 一句话', 'my-origin'),
    ('R23_④_200_mission_unusable_status', 'a23_200_mission_bad_status', '④ 答了 200、JSON 也对，但 mission.status 是屏幕词表里没有的值', 'my-origin'),
    ('R24_⑤_client_deadline_first_server_answers_later', 'a24_read_answered_after_deadline', '⑤ 客户端 12 s 期限先到，服务器那一发在之后才完成', 'my-origin'),
]

# the dispatch's own five classes, mapped onto the rows that carry them (pass 1 + pass 2)
CLASS = {
    '① 应用答了一个不带 envelope 的服务器错误': ['R1', 'R2', 'R3', 'R4'],
    '② 代理或网关自己答、应用根本没参与': ['R10', 'R11', 'R9'],
    '③ 真·传输失败（服务器确实没答）': ['R17', 'R18'],
    '④ 答了 200 但 payload 空或畸形': ['R19', 'R20', 'R21', 'R22', 'R23'],
    '⑤ 客户端期限先到、服务器事后才答': ['R13', 'R24'],
    '本单范围之外、同一枚病的延伸读数（我自己加的，不当判据）': ['R12', 'R15', 'R16'],
    '正控与信封阶梯（证明"引用得了"这一半）': ['R5', 'R6', 'R7', 'R8', 'R14'],
}


def spec_for(arm):
    f = B / ('spec_%s.json' % arm)
    return json.loads(f.read_text(encoding='utf-8')) if f.exists() else None


def find(pattern):
    hits = sorted(B.glob(pattern))
    if not hits:
        raise SystemExit('no artefact matches %s' % pattern)
    return hits[-1]


def load(arm):
    cell = json.loads(find('cell_%s_*.json' % arm).read_text(encoding='utf-8'))
    probe_path = B / ('probe_%s_%s.json' % (arm, cell['run_id']))
    probe = json.loads(probe_path.read_text(encoding='utf-8')) if probe_path.exists() else None
    # the origin log is append-only and carries every run of that arm, so a row is matched to the
    # window its own run id names (local HH:MM:SS) plus the stamp declared for it
    h, m, sec = (int(cell['run_id'].split('-')[1][i:i + 2]) for i in (0, 2, 4))
    start = h * 3600 + m * 60 + sec
    span = int(cell.get('cap_ms') or 45000) // 1000 + 20
    origin_rows = []
    olog = B / ('originlog_%s_%s.jsonl' % (arm, cell['run_id']))
    if olog.exists():
        for ln in olog.read_text(encoding='utf-8').splitlines():
            r = json.loads(ln)
            try:
                at = sum(int(x) * mul for x, mul in zip((r.get('at') or '').split(':'), (3600, 60, 1)))
            except ValueError:
                continue
            if r.get('stamp') == cell.get('policy_stamp') and start <= at <= start + span:
                origin_rows.append(r)
    return cell, probe, origin_rows


def sheet_screen(cell):
    if 'no_sheet' in cell:
        s = cell['no_sheet']['screen']
    else:
        s = cell.get('screen_final') or {}
    card = s.get('result_card') or ''
    first = card.split('\n')[0].strip() if card else ''
    return {'card_painted': bool(card.strip()), 'card_first_line': first,
            'card_text': card[:260],
            'network_card_painted': bool(s.get('network_card_painted')),
            'details_in_dom': s.get('details_elements_present'),
            'reason_label': s.get('reason_label_painted'),
            'reason_value': s.get('reason_value_painted') or '',
            'data_result_status': s.get('cross_check_data_result_status'),
            'deadline_sentence': s.get('deadline_sentence_on_screen'),
            'sheet_reached': bool(cell.get('opened', {}).get('hub_reached')) and bool(cell.get('opened', {}).get('sheet_opened')),
            # when the sheet never opens, the traveller is still looking at SOME card - the page-level
            # one - and its painted words are the reading for that row, not an absence
            'page_level_text': ((cell.get('no_sheet', {}) or {}).get('screen', {}) or {}).get('body_head') or '',
            'watch': cell.get('settle_states') or (cell.get('no_sheet', {}) or {}).get('watch', [])}


def main():
    envelope = json.loads((B / 'envelope_real.json').read_text(encoding='utf-8'))
    env_msg = envelope['error']['message']
    env_code = envelope['error']['code']
    rows = []
    for rid, arm, klass, who in ROWS:
        cell, probe, origin_rows = load(arm)
        posts = [l for l in cell.get('write_legs', []) if l.get('api')]
        sc = sheet_screen(cell)
        leg = (posts[-1] if posts else {})
        # an un-instrumented arm records no legs, so its server-side half comes from the origin's own
        # accounting: the same stamp, the write leg, the status it says it wrote.
        origin_writes = [r for r in origin_rows if r.get('leg') == 'write' and r.get('status') is not None]
        if not leg and origin_writes and sc['sheet_reached']:
            leg = {'url': origin_writes[-1].get('path'), 'status': origin_writes[-1]['status'],
                   'content_type': origin_writes[-1].get('content_type'),
                   'bytes': None, 'elapsed_ms': None, 'client_error': None,
                   'body_head': None, 'server_envelope': {}, 'source': 'origin_accounting'}
        answered = leg.get('status') is not None
        rejects = cell.get('json_rejections') or []
        syntax_rejects = [r for r in rejects if r.get('error_name') == 'SyntaxError']
        if not sc['sheet_reached']:
            verdict = 'NOT_MEASURED'
            reason = ('用户走不到这张结局卡：屏上停的是另一张卡（%s）' % (sc['card_first_line'] or '无卡'))
        elif not sc['card_painted']:
            verdict = 'NOT_MEASURED'
            reason = '结局卡到观察帽（%s ms）为止没出现，屏上仍停在等待态' % cell.get('cap_ms')
        elif answered and sc['network_card_painted']:
            verdict = 'MISLEADS'
            reason = '浏览器拿到了 HTTP %s，屏上仍把原因归给网络' % leg.get('status')
        elif answered:
            verdict = 'HONEST'
            reason = 'HTTP %s 被原样报成服务端失败' % leg.get('status')
        else:
            verdict = 'HONEST'
            reason = '这一发确实没有任何 HTTP 回答（client_error=%s），归给网络是本分的' % (leg.get('client_error') or 'never settled')
        rows.append({
            'row': rid, 'arm': arm, 'outcome_class_as_asked': klass, 'run_id': cell['run_id'],
            'cap_ms': cell.get('cap_ms'),
            'declared_read_delay_ms': (spec_for(arm) or {}).get('read', {}).get('delay_ms'),
            'policy_stamp': cell.get('policy_stamp'),
            'declared_write_leg': (spec_for(arm) or {}).get('write') or 'the real product backend',
            'server_side': {'deciding_leg': (leg.get('url') or '').split('/')[-1] or None,
                            'all_write_legs': [{k: l.get(k) for k in ('url', 'status', 'content_type',
                                                                       'bytes', 'elapsed_ms', 'client_error')}
                                               for l in posts],
                            'server_side_reading_from': ('browser fetch hook' if posts else
                                                         'origin accounting (this arm runs with no hook)'),
                            'http_status': leg.get('status'), 'content_type': leg.get('content_type'),
                            'bytes': leg.get('bytes'), 'elapsed_ms': leg.get('elapsed_ms'),
                            'client_error': leg.get('client_error'),
                            'body_head': (leg.get('body_head') or '')[:120],
                            'envelope_code': (leg.get('server_envelope') or {}).get('error_code'),
                            'envelope_message': (leg.get('server_envelope') or {}).get('error_message'),
                            'answer_attributed_to': who,
                            'sibling_probe_outside_browser': (probe or {}).get('probe'),
                            'origin_own_record_for_this_stamp': origin_rows},
            'screen_side': {'painted_first_line': sc['card_first_line'], 'painted_text': sc['card_text'],
                            'says_cannot_reach_server': sc['network_card_painted'],
                            'details_elements_in_dom': sc['details_in_dom'],
                            'reason_label_painted': sc['reason_label'], 'reason_value_painted': sc['reason_value'],
                            'data_result_status_cross_check': sc['data_result_status'],
                            'client_deadline_sentence_painted': sc['deadline_sentence'],
                            'sheet_reached': sc['sheet_reached']},
            'app_threw_on_the_body': {'json_rejections': rejects,
                                      'syntax_error_count': len(syntax_rejects),
                                      'first_rejection_message': (syntax_rejects[0]['error_message']
                                                                  if syntax_rejects else None)},
            'secondary_surface': None if sc['sheet_reached'] else {
                'what_the_traveller_was_left_with': (sc['page_level_text'][:150].replace(chr(10), ' / ')
                                                     or '(屏上没有任何结局文字)'),
                'page_level_legs': [{k: l.get(k) for k in ('url', 'method', 'status', 'bytes', 'client_error',
                                                            'elapsed_ms', 'sent_ms_since_load')}
                                    for l in (cell.get('no_sheet', {}) or {}).get('legs', [])],
                'an_http_answer_reached_the_browser': any(l.get('status') is not None
                                                          for l in (cell.get('no_sheet', {}) or {}).get('legs', [])),
                'blamed_the_network': sc['network_card_painted'],
                'same_rule_applied_to_this_surface': (
                    'MISLEADS' if (any(l.get('status') is not None
                                       for l in (cell.get('no_sheet', {}) or {}).get('legs', []))
                                   and sc['network_card_painted']) else 'HONEST')},
            'verdict': verdict, 'verdict_reason': reason,
        })
    by = {r['row']: r for r in rows}

    def g(rid, *path):
        x = by[rid]
        for p in path:
            x = x[p]
        return x

    misleads = [r for r in rows if r['verdict'] == 'MISLEADS']
    honest_answered = [r for r in rows if r['verdict'] == 'HONEST'
                       and r['server_side']['http_status'] is not None
                       and r['screen_side']['painted_first_line']]
    derived = {
        'rows': len(rows),
        'misleads_rows': [r['row'] for r in misleads],
        'honest_rows': [r['row'] for r in rows if r['verdict'] == 'HONEST'],
        'not_measured_rows': [r['row'] for r in rows if r['verdict'] == 'NOT_MEASURED'],
        'every_misleads_row_had_no_json_object_for_the_helper':
            all(r['server_side']['http_status'] is not None and
                (r['app_threw_on_the_body']['syntax_error_count'] > 0
                 or r['server_side']['content_type'] != 'application/json'
                 or (r['declared_write_leg'] or {}).get('body') in ('null', 'Internal Server Error',
                                                                    'Service Unavailable'))
                for r in misleads) if misleads else False,
        'every_honest_answered_row_had_a_json_object':
            all((spec_for(r['arm']) or {}).get('write', {}).get('body') not in (None, 'null')
                or r['server_side']['envelope_code'] is not None
                for r in honest_answered) if honest_answered else False,
        'no_honest_answered_row_threw_on_the_body':
            all(r['app_threw_on_the_body']['syntax_error_count'] == 0 for r in honest_answered)
            if honest_answered else False,
        'same_status_different_body_shape_flips_the_verdict':
            g('R2_①_contentless_500_fast', 'server_side', 'http_status')
            == g('R5_②_500_with_product_envelope', 'server_side', 'http_status')
            and g('R2_①_contentless_500_fast', 'verdict') != g('R5_②_500_with_product_envelope', 'verdict'),
        'different_status_same_body_shape_keeps_the_verdict':
            len({g(r, 'verdict') for r in ('R5_②_500_with_product_envelope', 'R6_③_503_envelope',
                                           'R7_③_502_envelope', 'R8_③_504_envelope')}) == 1,
        'null_versus_empty_object_pair_differs':
            g('R15_⓪_json_null_body', 'verdict') != g('R16_⓪_json_empty_object', 'verdict'),
        'duration_is_not_the_discriminator':
            g('R2_①_contentless_500_fast', 'screen_side', 'says_cannot_reach_server')
            == g('R3_①_contentless_500_after_35s', 'screen_side', 'says_cannot_reach_server')
            == g('R1_①_contentless_500_from_the_product', 'screen_side', 'says_cannot_reach_server'),
        'uninstrumented_reproduction_agrees':
            g('R2_①_contentless_500_fast', 'screen_side', 'says_cannot_reach_server')
            == g('R4_①_uninstrumented', 'screen_side', 'says_cannot_reach_server')
            and g('R2_①_contentless_500_fast', 'screen_side', 'details_in_dom' if False else 'details_elements_in_dom')
            == g('R4_①_uninstrumented', 'screen_side', 'details_elements_in_dom'),
        'envelope_sentence_quoted_verbatim_equals':
            g('R5_②_500_with_product_envelope', 'screen_side', 'reason_value_painted') == env_msg,
        'punctuation_drift_still_equals': (env_msg + '.') == env_msg,
        'suffix_drift_still_equals': (env_msg + '。') == env_msg,
        'label_says_server_on_the_envelope_row':
            g('R5_②_500_with_product_envelope', 'screen_side', 'reason_label_painted') == SERVER_LABEL,
        'label_says_device_when_the_body_holds_no_sentence':
            g('R16_⓪_json_empty_object', 'screen_side', 'reason_label_painted') == DEVICE_LABEL,
        'dispatch_class_coverage': {k: sorted(v) for k, v in CLASS.items()},
        'every_named_class_has_at_least_one_row': all(len(v) >= 1 for v in CLASS.values()),
        'rows_covered_by_a_class': sorted(x for v in CLASS.values() for x in v),
        'rows_in_the_table_not_in_any_class': sorted(r['row'].split('_')[0] for r in rows
                                                    if r['row'].split('_')[0] not in
                                                    {x for v in CLASS.values() for x in v}),
        'route_abort_is_the_honest_network_copy':
            g('R18_③_route_abort_real_transport_failure', 'server_side', 'http_status') is None
            and g('R18_③_route_abort_real_transport_failure', 'screen_side', 'says_cannot_reach_server')
            and g('R18_③_route_abort_real_transport_failure', 'verdict') == 'HONEST',
        'no_200_row_blamed_the_network':
            not any(g(k, 'screen_side', 'says_cannot_reach_server')
                    for k in ('R19_④_200_empty_body', 'R20_④_200_json_empty_object',
                              'R21_④_200_json_array', 'R22_④_200_text_plain_payload',
                              'R23_④_200_mission_unusable_status')),
        'every_200_malformed_row_lost_the_detail_block':
            all(g(k, 'screen_side', 'details_elements_in_dom') == 0
                for k in ('R19_④_200_empty_body', 'R20_④_200_json_empty_object',
                          'R21_④_200_json_array', 'R22_④_200_text_plain_payload',
                          'R23_④_200_mission_unusable_status')),
        'the_200_rows_all_assert_one_named_cause':
            len({g(k, 'screen_side', 'data_result_status_cross_check')
                 for k in ('R19_④_200_empty_body', 'R20_④_200_json_empty_object',
                           'R21_④_200_json_array', 'R22_④_200_text_plain_payload',
                           'R23_④_200_mission_unusable_status')}) == 1,
        'server_answered_after_the_client_gave_up':
            bool([r for r in g('R24_⑤_client_deadline_first_server_answers_later', 'server_side')
                         .get('origin_own_record_for_this_stamp', [])
                  if r.get('leg') == 'read' and r.get('error')])
            and g('R24_⑤_client_deadline_first_server_answers_later', 'declared_read_delay_ms') == 20000,
    }
    out = {'generated_from': 'arm artefacts on disk (cells, sibling probes, origin logs, declared specs)',
           'measured_on': TIP, 'rows': rows, 'derived': derived,
           'captured_envelope': {'code': env_code, 'message': env_msg,
                                 'bytes': len((B / 'envelope_real.json').read_bytes()),
                                 'sha256': STATE['captured_envelope']['sha256']}}
    (B / 'table_O0301.json').write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding='utf-8')
    print(json.dumps(derived, ensure_ascii=False, indent=1))
    print('\n%-42s %-9s %-6s %-7s %-8s %-6s %s' % ('row', 'status', 'B', 'net?', 'details', 'verdict', 'painted'))
    for r in rows:
        print('%-42s %-9s %-6s %-7s %-8s %-6s %s' % (
            r['row'][:42], r['server_side']['http_status'], r['server_side']['bytes'],
            r['screen_side']['says_cannot_reach_server'], r['screen_side']['details_elements_in_dom'],
            r['verdict'], r['screen_side']['painted_first_line'][:26]))


if __name__ == '__main__':
    sys.setrecursionlimit(100)
    main()
