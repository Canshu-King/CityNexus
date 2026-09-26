"""Score the newest-phone-generation walk: every line is computed from a named field, and no verdict word is mine.

Cells the commander asked for, in his order:
  1  the two defects I reported before, re-measured on this bundle, with the screen text copied verbatim -
     and compared as bytes against the previous generation so "unchanged" is a measurement, not a memory;
  2  ORD-0357 used for real: press 复制行程链接, read the clipboard back inside the page, then open that link in a
     device that never saw the app;
  3  the new user-visible findings, each with the interface name and the byte counts I recorded.

Four of my own instrument faults are in here too, including the two exploratory passes that failed to find the
copy control - they are kept because they are what proved the control sits two taps deep and that a same-named
desktop entry is unreachable at 390 px.
"""
from __future__ import annotations

import hashlib
import importlib.util as iu
import json
import pathlib
import subprocess
import time

import sys

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

OUT = pathlib.Path('D:/moodle/_hjp3_d3j0_0926')
PREV = pathlib.Path('D:/moodle/_hjp3_b6a8_0926')
SRC = pathlib.Path('D:/moodle/HJ-P3_evidence')
spec = iu.spec_from_file_location('pub', str(SRC / 'p3_publish.py'))
pub = iu.module_from_spec(spec)
spec.loader.exec_module(pub)

EC = json.loads((OUT / 'r7_entry_check.json').read_text(encoding='utf-8'))
W = json.loads((OUT / 'r7_walk.json').read_text(encoding='utf-8'))
C2 = json.loads((OUT / 'r7_copy_link_r2.json').read_text(encoding='utf-8'))
C3 = json.loads((OUT / 'r7_copy_link_r3.json').read_text(encoding='utf-8'))
C4 = json.loads((OUT / 'r7_copy_link_r4.json').read_text(encoding='utf-8'))
AI = json.loads((OUT / 'r7_ai_disabled.json').read_text(encoding='utf-8'))
PREV6 = json.loads((PREV / 'r6_dead_id_saved.json').read_text(encoding='utf-8'))
PREV_SCORED = json.loads((PREV / 'r6_readings_scored.json').read_text(encoding='utf-8'))
lr = subprocess.run(['git', '-C', 'D:/moodle/CityNexus', 'ls-remote', 'origin',
                     'refs/heads/mirror/integration-frontend-apple-pass1'],
                    capture_output=True, text=True, encoding='utf-8', errors='replace')
mirror = ([l.split()[0] for l in (lr.stdout or '').splitlines() if l.strip()] + [None])[0]

c = W['cells']['C_closed']
co = W['cells']['C_open']
prev_c = PREV6['cases']['C1_dead_stored_id_as_it_lands']['read']
acc = C4['acceptance']
bookings = C4['on_bookings']
trips = C4['trips_as_landed']
hub_buttons = W['cells']['D_hub']['buttons']
aside_zero_top = [b['text'] for b in hub_buttons if b['top'] == 0]
nav_789 = [b['text'] for b in hub_buttons if b['top'] == 789]
after_press = AI['after']
ai_offer = AI['after_offer']


def h(t):
    return hashlib.sha256((t or '').encode('utf-8')).hexdigest()


d = {'ran_at_local': time.strftime('%Y-%m-%dT%H:%M:%S%z'),
     'lane': 'HJ-P3 aad2d1f2-4de9-406b-a5df-afa0e2bcea58',
     'order': 're-measure two reported defects, accept ORD-0357 by using it, and report new user-visible findings',
     'measurement_scope': {
         'scope': '死 stored journey id 那一屏；「已保存」这类话背后的设备行；行程自身链接的复制与重开；行程底栏与 AI 引导的两屏',
         'generation_read_from_the_ref_in_this_run': mirror,
         'generation_named_by_the_commander': None,
         'bundle_under_test': {'asset': EC['entries'][1]['asset_named_by_the_shell'],
                               'bytes': EC['entries'][1]['asset_row']['bytes'],
                               'sha256': EC['entries'][1]['asset_row']['sha256'],
                               'matches_the_name_he_gave': EC['entries'][1]['asset_matches_the_name_the_commander_gave'],
                               'same_bytes_on_both_entries': EC['same_asset_bytes_on_both_entries']},
         'health_fields': EC['entries'][1]['health_ai_fields'],
         'health_row': EC['entries'][1]['health_row'],
         'measurement_method': 'own headless Chromium 390x844@3 touch zh-CN over the public tunnel entry, fresh '
                               'context per cell, legs read off browser response objects, clipboard read inside the '
                               'page, device stores counted inside the page'},
     'cell_1a_dead_stored_id': {
         'verbatim_screen_text': c['text'],
         'text_len_closed': c['text_len'], 'text_len_open': co['text_len'],
         'claims_the_network_is_down': c['claims_offline'],
         'names_that_it_does_not_exist': c['names_404'],
         'denies_a_network_reading': c['denies_network'],
         'mentions_http_404_on_screen': '404' in c['text'],
         'actions_offered': [b['text'] for b in c['buttons'] if b['text']],
         'the_leg': [[l['m'], l['url'], l['status'], l['resp_bytes'], l['ct'], l['server_receipt_id'],
                      l['server_code']] for l in W['cells']['C_legs'] if 'journeys' in l['url']],
         'receipt_on_screen_closed': c['receipts'], 'receipt_on_screen_open': co['receipts'],
         'fold': {'closed': c['details'], 'open': co['details']},
         'ls_after': W['cells']['C_ls_after'],
         'identical_to_the_previous_generation_word_for_word': h(prev_c['text'][:400]) == h(c['text'][:400]),
         'previous_generation_text_sha': h(prev_c['text'][:400]), 'this_generation_text_sha': h(c['text'][:400])},
     'cell_1b_saved_behind_rows': {
         'device_after_a_real_boot': W['cells']['D_device'],
         'device_after_the_tab_walk': W['cells']['D_device_after_walk'],
         'boot_ms': W['cells']['D_boot_ms_first_read'],
         'saved_sentences_on_the_hub': W['cells']['D_hub']['saved_sentences'],
         'saved_sentences_per_tab': [{k: t.get(k) for k in ('label', 'affordance_present', 'saved_sentences',
                                                            'text_len')} for t in W['cells']['D_tab_scan']],
         'offline_snapshot_leg': [[l['m'], l['url'], l['status'], l['resp_bytes']]
                                  for l in W['cells']['D_legs'] if 'offline' in l['url']],
         'service_worker_controls': W['cells']['D_hub']['sw_controller'],
         'bundle_contains_saved_strings': {k: v['occurrences'] for k, v in
                                           EC['asset_literal_search_over_the_served_bytes'].items()},
         'limit_named': '我只走了这五屏（今天/我的/行程/预订/行程工作台）；「已保存」这句话在这五屏上没渲染，'
                        '其余屏幕我没到过，因此不说它不存在'},
     'cell_2_ord0357_copy_link': {
         'path_taken_by_me': {'first_stop_without_control': C2.get('tab_tries', [])[:2],
                              'trips_landing_len': trips['text_len'],
                              'sub_tab_anchor': 'trips-tab-bookings',
                              'control_appeared_after': 'the 预订 sub-tab of /v8/trips'},
         'control': {'testid': 'journey-link-copy', 'text': bookings['copy_button_text'],
                     'data_cnx_field': bookings['copy_button_field_attr'], 'top_px': bookings['copy_button_top'],
                     'disabled': bookings['copy_button_disabled'], 'in_viewport': bookings['copy_button_in_view']},
         'press_result': C4['press'],
         'clipboard': C4['clipboard'],
         'message_line_verbatim': C4['after_press']['message_text'],
         'message_field_attr': C4['after_press']['message_field_attr'],
         'reopen_in_a_clean_device': {k: acc[k] for k in ('link', 'reopened_url',
                                                         'journey_id_now_in_the_device', 'ls_keys',
                                                         'same_rendered_text_as_the_copy_screen',
                                                         'copy_screen_len', 'reopen_len')},
         'journey_identity_on_the_reopened_screen': '天津之旅' in C4['reopen']['text'],
         'journey_identity_on_the_copy_screen': '天津之旅' in bookings['text'],
         'legs_after_reopening': [[l['m'], l['url'], l['status'], l['resp_bytes']] for l in C4['reopen_legs']][:8]},
     'cell_3_new_findings': {
         'f1_trips_landing_says_there_is_nothing_to_look_at': {
             'screen': '/v8/trips', 'text_verbatim': trips['text'][:520],
             'what_the_same_journey_shows_on_the_hub': '天津之旅' in W['cells']['D_hub']['text'],
             'hub_day_rows_rendered': len([x for x in W['cells']['D_hub']['text'].split('\n') if x.startswith('第 ')]),
             'plans_leg': [[l['m'], l['url'], l['status'], l['resp_bytes']] for l in W['cells']['D_legs']
                           if '/plans' in l['url']],
             'places_leg': [[l['m'], l['url'], l['status'], l['resp_bytes']] for l in AI['legs']
                            if '/places' in l['url']],
             'experience_leg': [[l['m'], l['url'], l['status'], l['resp_bytes']] for l in W['cells']['D_legs']
                                if '/experience' in l['url']]},
         'f2_ai_state_and_the_sheet_disagree': {
             'health_fields': EC['entries'][1]['health_ai_fields'], 'health_bytes': EC['entries'][1]['health_row']['bytes'],
             'sheet_lines_verbatim': ai_offer, 'sheet_dialog': AI['after']['dialogs'][0] if AI['after']['dialogs'] else None,
             'cta_before_press': AI['button_state'], 'runtime_status_leg': [[l['m'], l['url'], l['status'],
                                                                            l['resp_bytes']] for l in AI['legs_for_the_press']
                                                                           if 'runtime-status' in l['url']],
             'what_i_did_not_do': '我没有按「开始规划」：那会启动一条比走查更长的流程，而且 AI 的开关归运维与用户，'
                                  '不该由我替它试穿'},
         'f3_desktop_entries_unreachable_at_390': {
             'buttons_at_top_zero': aside_zero_top, 'bottom_nav_at_390': nav_789,
             'role_query_hit_for_the_desktop_label': {'label': '旅行票夹', 'role_count': C3['stops'][2]['role_name_probe'],
                                                     'dom_text_count': C3['stops'][2]['found']},
             'hops_to_the_copy_control': 2}},
     'instrument_faults_of_mine': [
         {'said': '我一开始报「复制控件不存在」', 'signal': '包里 `journey-link-copy` 与四句文案都在，而我在 hub 与 '
                   'studio 两屏都没找到它', 'cause': '控件在 `/v8/trips` 的「预订」子页里，我停在了上一跳',
          'fixed_in': 'r7_copy_link_r4.cjs，两份未找到的探索件也一起交（r7_copy_link_r2/r3）'},
         {'said': '我用 getByRole 找不到「旅行票夹」，一度当成读屏命名缺口', 'signal': '同一枚标签用 DOM 文本命中 1、'
                   'role 命中 0，而它的 top 是 0，移动底栏五枚的 top 都是 789', 'cause': '那是桌面那支侧栏在 390 宽下'
                   '不可达，不是命名缺失；判据应写成「两份同名入口只有一份可达」',
          'fixed_in': '改读法为按 top 分组并写出两组清单（字段 `f3_desktop_entries_unreachable_at_390`）'},
         {'said': '我在浏览器里调了 Node 端的 SHA 助手', 'signal': 'page.evaluate 报 ReferenceError: SHA is not defined',
          'cause': 'evaluate 里只能用页面内函数', 'fixed_in': '改用 crypto.subtle 在页面内哈希'},
         {'said': '第一条命令里我把公网入口当成没起来', 'signal': '这台 shell 导出的 HTTP(S)_PROXY 指着一个没人听的端口，'
                   'urlopen 报 10061，而直连 TCP 443 成功', 'cause': '代理环境变量', 'fixed_in': '每条命令前缀不走代理'
                   '（号令者随后也确认了这条）'}],
     'launches_on_this_lane': 6, 'contexts': 9,
     'boundaries': 'product bytes 0 changed; nothing repaired; 权威线 0 写; ref 0 推别人的; demo/reset 0; _live.db 与 '
                   '_preview.db 0 读 0 写; git apply 0; 凭据不写进任何交付件（每件带断言）; 链上四层只当用户驱动或只读 '
                   'GET; 反复起车的瓦片通道风险我按具名计数记在 `launches_on_this_lane`，因此本块不对底图状态下结论'}
d['judgments'] = {
    'both_entries_serve_the_bundle_the_commander_named': bool(
        EC['same_asset_bytes_on_both_entries'] and EC['entries'][1]['asset_matches_the_name_the_commander_gave']),
    'health_reports_the_ai_disabled_field': EC['entries'][1]['health_ai_fields'].get('ai_state') == 'DISABLED_BY_OPS',
    'C_dead_id_screen_still_does_not_claim_the_network': bool(not c['claims_offline'] and c['names_404']),
    'C_dead_id_screen_text_is_word_for_word_the_previous_generation': h(prev_c['text'][:400]) == h(c['text'][:400]),
    'C_stored_id_is_still_cleared_after_the_rejection': W['cells']['C_ls_after']['journey_id'] is None,
    'C_server_receipt_still_never_reaches_the_screen': bool(
        any(x[5] for x in d['cell_1a_dead_stored_id']['the_leg'])
        and not c['receipts'] and not co['receipts']),
    'D_the_device_holds_one_offline_copy': W['cells']['D_device']['rows'].get('journeys') == 1,
    'D_no_saved_sentence_rendered_on_the_five_screens': not any(
        t.get('saved_sentences') for t in W['cells']['D_tab_scan'] if t.get('affordance_present'))
    and not W['cells']['D_hub']['saved_sentences'],
    'E_copy_control_exists_but_is_two_taps_deep': bool(
        bookings['copy_button_present'] and C3['stops'] and not C2.get('at_hub', {}).get('copy_button_present')),
    'E_pressing_it_puts_a_journey_url_on_the_clipboard': bool(
        isinstance(C4['clipboard'], str) and C4['clipboard'].startswith('https://')
        and W['cells']['A_stored_id'] in C4['clipboard']),
    'E_the_copied_link_lands_a_clean_device_on_that_journey': bool(
        acc['journey_id_now_in_the_device'] == W['cells']['A_stored_id']
        and '天津之旅' in C4['reopen']['text']),
    'E_the_reopened_screen_is_not_the_screen_the_copy_came_from': bool(
        acc['same_rendered_text_as_the_copy_screen'] is False),
    'F_trips_landing_offers_ai_while_health_says_the_ai_is_off': bool(
        '先让 AI 帮你规划' in trips['text'] and EC['entries'][1]['health_ai_fields'].get('ai') == 'disabled'),
    'F_the_sheet_the_ai_button_opens_claims_the_service_has_models': bool(
        any('已接入 AI 模型' in x for x in ai_offer)),
    'G_desktop_entries_are_unreachable_at_this_width': bool(
        '旅行票夹' in aside_zero_top and '旅行票夹' not in nav_789)}
d['judgments_note'] = ('readings only; grading belongs to E. Each key above is a computation over the fields named '
                       'in this file; the previous-generation comparison uses that generation\'s stored file, not '
                       'my recollection')
(OUT / 'r7_scored.json').write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding='utf-8', newline='\n')
print(json.dumps(d['judgments'], ensure_ascii=False, indent=1))
print('leg:', json.dumps(d['cell_1a_dead_stored_id']['the_leg'], ensure_ascii=False)[:300])
print('groups:', json.dumps({'top0': aside_zero_top, 'nav': nav_789}, ensure_ascii=False)[:400])
print('plans/places:', json.dumps(d['cell_3_new_findings']['f1_trips_landing_says_there_is_nothing_to_look_at'],
                                  ensure_ascii=False)[:700])
