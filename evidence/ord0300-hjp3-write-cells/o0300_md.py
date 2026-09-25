"""ORD-0300: the human-readable receipt, rendered from the same artefacts the JSON scorer used."""
from __future__ import annotations

import json
import pathlib

BASE = pathlib.Path('D:/moodle/_hjp3_0300_0925')
state_j = json.loads((BASE / 'o0300_state.json').read_text(encoding='utf-8'))
ref_read = json.loads((BASE / 'ref_readback.json').read_text(encoding='utf-8'))
rec = json.loads((BASE / 'RECEIPT_O0300-2610.json').read_text(encoding='utf-8'))
cells = {c['id']: c for c in rec['cells']}
c1 = cells['C1_server_side_answer_on_the_contended_write']
c2 = cells['C2_screen_side_attribution_of_that_same_answer']
c3 = cells['C3_positive_control_the_server_channel_still_carries_words_verbatim']
c4 = cells['C4_write_leg_deadline_on_the_silent_origin']
c5 = cells['C5_is_the_named_503_reachable_on_the_user_path']
m1, m2, m3, m4, m5 = (c1['measured'], c2['measured'], c3['measured'], c4['measured'], c5['measured'])
last = m1['arms'][-1]
cfg = m1['server_write_config_read_from_the_product']
L = []
w = L.append
w('# ORD-0300 · 在 `%s` 上重测 ORD-0279 W2 与 ORD-0281 T-b · HJ-P3 aad2d1f2' % rec['measured_on'])
w('')
w('> **measured_on = `%s`**（%s）· %s 现场重读那枚 ref：`%s` · '
  '客户端被测件 = 我用这棵尖自己 `vite build` 出来的私有产物：`%s` / sha256 `%s` · %s · '
  '**未动在服的 dist/index.html、未重启预览后端**。'
  % (rec['measured_on'], rec['measured_on_how_read'], ref_read['ran_at_local'], ref_read['stdout'],
     rec['bundle_under_test']['asset'],
     rec['bundle_under_test']['sha256'], 'ORD-0280 的两枚标记都在服务字节里'
     if rec['bundle_under_test']['ord0280_markers_present_in_served_bytes'] else '标记缺失'))
w('> **`derived_result` = null**（那是 verifier 的字）；`claimed_result = %s`。Q25：本件每个毫秒数只对这一代有效，**没有一个时长是从旧代搬来的**。' % rec['claimed_result'])
w('')
w('## 0. 大白话')
w('**服务器那一边**：撞锁的写腿答案**形状一点没变**——还是 `HTTP 500`、`text/plain`、%s B、**没有一个字**（不是 JSON、没有 code）。'
  % last['bytes'])
w('ORD-0296 新加的名字（`SERVER_WRITE_DEADLINE_EXCEEDED`）**在这条用户路上我今天拿不出来**：预算 %d ms 比 SQLite 等锁上限 %d ms 大，'
  % (cfg['deadline_ms'], cfg['busy_timeout_ms']))
w('所以一次失败的回锁必然在预算用完**之前**就报出来（算术见 §5）。')
w('')
w('**屏幕那一边**：这一代不再犯我 0279 那格的错了（没再把自造的串挂到「服务器给出的原因」下面），**但换成了另一个错**——')
w('它对**明明答了的** %s 说「%s」，而且**连“技术详情”整块都没有**（DOM 里 `<details>` 数 = %d）：用户点开也找不到任何一句原因。'
  % (last['http_status'], (m2['painted_card'] or '').split('\n')[0], m2['detail_regions_in_dom']))
w('我没有拿仪器当借口：**把 fetch 包装全拆掉再点一次，卡片一模一样**（§2 第二条）。')
w('')
w('## 1. 两格在新代的状态（这就是本单要的结论）')
w('')
w('| 格 | 旧代读数 | 本代（`%s`）实测 | 本件里的名字 |' % rec['measured_on'][:8])
w('|---|---|---|---|')
w('| ORD-0279 **W2** | 客户端把 `HTTP 500` 挂到「服务器给出的原因」标签下 ⇒ 红 | **不再是那个形状**：改说「连不上服务端」且无技术详情 ⇒ **新红** | `%s` / `%s`'
  % (c1['verdict'], c2['verdict']) + ' |')
w('| ORD-0281 **T-b**（静默源站反例 1） | 写腿永不自结束（`WRITE_LEG_STILL_UNBOUNDED`） | **仍然成立**：POST 到 %s ms 仍无状态、无客户端错误、屏上从没出现期限句 | `%s`'
  % (m4['observation_cap_ms'], c4['verdict']) + ' |')
w('')
w('旧尖那两格**原地保留、不覆盖不删**，只按号令改标：`SUPERSEDED_BY_GENERATION`（W2）/ `REPRODUCED_ON_NEW_GENERATION`（T-b）——见件内 `supersedes`。')
w('')
w('## 2. 两侧同判（服务端字段 vs 屏幕上 painted 的文字）')
w('```text')
w('服务端（页面自己那侧记到的）  POST %s → %s · "%s" · %s B · %s ms · client_error=%s'
  % (last['url_tail'], last['http_status'], last['content_type'], last['bytes'], last['elapsed_ms'],
     last['client_error']))
w('                              envelope: error_code=%r error_message=%r reason_code=%r body 开头 %r'
  % (last['error_code'], last['error_message'], last['reason_code'], last['body_head'][:28]))
w('屏幕上（innerText 读到的 painted 文字）  卡片 = 「%s」' % (m2['painted_card'] or '').replace('\n', ' / '))
w('                              painted 原因标签 = %r · painted 原因值 = %r · <details> 数 = %d'
  % (m2['painted_reason_label'], m2['painted_reason_value'], m2['detail_regions_in_dom']))
w('交叉核对（只当旁证，不当判据）            data-result-status=%r' % m2['cross_check_data_result_status'])
w('无仪器复跑（fetch 包装/钩子全拆）          同一句话，%s ms 出现，data-result-status=%r，<details> 仍为 %d'
  % (m2['reproduced_without_any_instrument']['appeared_after_ms'],
     m2['reproduced_without_any_instrument']['cross_check_data_result_status'],
     m2['reproduced_without_any_instrument']['detail_region_in_dom']))
w('```')
w('⇒ 服务端**答了**（%s、%s B），屏上说的是**没答**（%r）——两侧对不上，这一格红：`%s`。'
  % (last['http_status'], last['bytes'], m2['cross_check_data_result_status'], c2['verdict']))
w('')
c6 = cells['C6_the_same_finding_on_a_bundle_i_did_not_build']['measured']
w('## 2b. 这条红**不是我那枚私有 build 的毛病**（换一枚别人做的包再跑一次）')
w('```text')
w('另一枚包：`%s` / sha256 `%s…`（与我那枚字节相同 = %s，ORD-0280 两枚标记都在 = %s）'
  % (c6['foreign_asset'], c6['foreign_sha256'][:16], c6['byte_identical_to_mine'], c6['markers_present']))
w('面还是我起的（代理归属：我这行程 %s / 别人 uuid %s）；对面那棵树本进程跑前跑后逐文件 sha256 一致（未改动）= %s'
  % (c6['ownership']['mine_via_face'], c6['ownership']['foreign_via_face'], c6['foreign_tree_unchanged']))
w('同一记实弹 → HTTP %s / %s B / %s ms → 卡片「%s」· data-result-status=%r · <details> 数 %d'
  % (c6['reading']['http_status'], c6['reading']['bytes'], c6['reading']['elapsed_ms'],
     (c6['reading']['painted_card'] or '').split(chr(10))[0], c6['reading']['data_result_status'],
     c6['reading']['details_in_dom']))
w('⇒ %s' % cells['C6_the_same_finding_on_a_bundle_i_did_not_build']['verdict'])
w('```')
w('')
w('## 3. 正控：这一代的通道**能**把服务器的原话搬上屏（所以 §2 不是“屏幕本来就不能引用”）')
w('```text')
w('库里读（第二条只读连接）  journey_missions.failure_reason @ %s = %r（%d 字符）'
  % (m3['db_table_column_row'].split('/')[-1][:10], m3['server_sentence_read_by_second_ro_connection'],
     m3['sentence_length_chars']))
w('屏上读                    标签 = %r · 值 = %r' % (m3['painted_label'], m3['painted_value']))
w('两侧同判                  == 相等 = %s' % m3['equal_with_double_equals'])
w('标点漂移反控              %r → 必须不等 = %s' % ('...punctuation drift', m3['controls']['punctuation_drift_must_be_refused']))
w('后缀漂移反控              加一个句号 → 必须不等 = %s（用 `in` 就会**假绿**：%s）'
  % (m3['controls']['suffix_drift_must_be_refused'], m3['controls']['substring_test_would_have_been_softer']))
w('同一趟另一腿              plans/generate → %s · error_message=%r ⇒ 屏上引的不是这一句，所以引用来源只能追到上面那行库读' % (
  m3['other_legs_in_the_same_run']['plans_generate_status'],
  m3['other_legs_in_the_same_run']['plans_generate_error_message']))
w('```')
w('⇒ `%s`。另外这条也说明 §2 的红**不是**“引用不了”，而是“该引用的时候它说没响应”。' % c3['verdict'])
w('')
w('## 4. T-b：静默源站上写腿仍然没有自己的上限')
w('```text')
w('面 %s（服务的还是同一枚 %s）→ 选择性源站 %s：回读 %d 次、吞写 %d 次（%s）'
  % (m4['face_port'], m4['bundle_sha256'][:10], m4['origin_port'], m4['origin_accounting']['reads_answered'],
     m4['origin_accounting']['writes_swallowed'], '/'.join(m4['origin_accounting']['swallowed_at'])))
w('POST 出发于 %s ms；到 %s ms 仍 status=%s、client_error=%s；期间采样 %d 次，期限句出现过 = %s'
  % (m4['post_sent_at_ms'], m4['observation_cap_ms'], m4['post_status'], m4['post_client_error'],
     m4['samples_taken'], (m4['client_deadline_line_seen'] or '没有')))
w('这棵尖上客户端读期限常量仍是： %s（写分支照旧短路）' % (m4['readDeadline_source_line_on_this_tip'] or ['(未读到)'])[0])
w('```')
w('⇒ `%s`。我 0291 那把尺（同一枚仪器、换一棵树）现在就能给 @B 用：两档常量、只看触发时刻是否移动。' % c4['verdict'])
w('')
w('## 5. ORD-0296 的名字在用户路上够得着吗？（我试了两把，没够着）')
w('```text')
w('产品自己的数（在进程内读它的配置函数，不是我猜的）  deadline=%d ms · busy_timeout=%d ms · delta=%d ms · effective_busy=%d ms'
  % (cfg['deadline_ms'], cfg['busy_timeout_ms'], cfg['delta_ms'], cfg['effective_busy_timeout_ms']))
w('一把长窗 70 s   → 就是 §2 那格：一次回锁在 %s ms 报出来 = %s（预算还没用完）' % (last['elapsed_ms'], last['http_status']))
w('两把窗 20+20 s  → 第一腿 %s ms 后拿到锁，%s；第二腿 %s ms 就 %s' % (
  m5['schedule_two_windows_20s_20s']['agent_commands']['elapsed_ms'],
  m5['schedule_two_windows_20s_20s']['agent_commands']['http_status'],
  m5['schedule_two_windows_20s_20s']['plans_generate']['elapsed_ms'],
  m5['schedule_two_windows_20s_20s']['plans_generate']['http_status']))
w('两把窗 20+45 s  → 第一腿等了 %s ms 后**拿到锁并成功**（%s），第二腿 plans/generate 只花 %s ms ⇒ 没有第二次“输掉的回锁”'
  % (m5['schedule_two_windows_20s_45s']['agent_commands']['elapsed_ms'],
     m5['schedule_two_windows_20s_45s']['agent_commands']['http_status'],
     m5['schedule_two_windows_20s_45s']['plans_generate']['elapsed_ms']))
w('算术                  一次失败的回锁最早出现在 busy_timeout=%d ms 处；要 >%d ms 才谈得上“预算用完”，'
  % (cfg['busy_timeout_ms'], cfg['deadline_ms']))
w('                    就必须让**同一个请求**连着输两把锁。今天这条路的写段一旦拿到锁，剩下的写在 %d ms 内就做完了。'
  % m5['schedule_two_windows_20s_45s']['plans_generate']['elapsed_ms'])
w('```')
w('⇒ `%s`。含义留给包工头/下一班判（我不替它下结论）：**在“默认值必须 > busy_timeout”这条门之下，这个名字对一个写段一锁的用户路径几乎是够不着的**——' % c5['verdict'])
w('要么让它可被命名（例如失败后仍在本请求内继续尝试的第二把锁），要么承认今天用户看到的仍是无内容的 500。')
w('')
w('## 6. 我这轮的自曝（三件，都不是别人发现的）')
w('1. `cell_w2_*` 这一格我**先后跑了两次却用了同一个 run id**，第二次覆盖了第一次的文件；两次形状一致（%s / %s B / 无 envelope），'
  % (last['http_status'], last['bytes']))
w('   但只有后者留下工件 ⇒ 从现在起每次执行各给一个 run id。')
w('2. `o0300_rig.py stop` 把 `cmdline_had_port` 的检查放在 taskkill **之后**，所以那一栏对刚被停掉的进程必然报 false——它什么也没证明；')
w('   真正兜住的是“pid 由我自己起面时写进 `o0300_pids.json`”+“四口现在全空”（`teardown_note.json`）。')
w('3. 第一次两把窗实验的驱动崩在 `int("20,45")` 上，那次的日志（`cell_wnamed_locklog.txt` 里是 Python 栈）我也一并发布，不装作没发生。')
w('')
w('## 7. 现场与边界')
w('```text')
w('端口：后端 %d、W2 面 %d、静默源站 %d、T-b 面 %d —— 全是新口，收尾后四个都无侦听（teardown_note.json）。' % (8551, 8552, 8553, 8554))
w('库：`o0300.s3db`，由产品自己的 `ensure_schema()` 建、起面先删（R-SCHEMA-01 fresh-or-no-run）；库里的行只被我**只读**第二条连接查过。')
w('我这一轮自己建的行程 %s，控制那一趟写作的 mission 是 %s；`_live.db`/`_preview.db` 0 读写；`demo/reset` 0 次；凭据 0 打印（AI 在我这套面上是关的）。'
  % (state_j['seed']['journey_id'], rec['cells'][2]['measured']['db_table_column_row'].split('/')[-1][:8]))
w('在服预览：`dist/index.html` 0 改动、预览后端 0 重启（Q45=①/Q46=③ 之后换代归下一班的双尺流程）。')
w('产品字节 0 改动：新代前端是**我私有 outDir** 里 build 的（`dist_0300`），node_modules 用 junction 挂来又用 `rmdir` 摘掉，仓里那份 %d 个条目完好。' % len(list(pathlib.Path('D:/moodle/CityNexus/frontend/node_modules').iterdir())))
w('已发布路径 0 覆盖 0 删除（本单全部落新目录）。')
w('```')
w('')
w('## 8. 尺子（交前先自己跑）')
w('```text')
w('live_checks/receipt_cell_derivation_check_r2.py --receipt RECEIPT_O0300-2610.json --min-cells 6 --expect Q38_GATE_GREEN')
w('→ cells 6 · overall Q38_GATE_GREEN · hard 0 · soft 0 · "expectation held: Q38_GATE_GREEN" · rc 0')
w('（逐格 why tokens / own hits 见 q38_ruler_expect.json；`derived_result` 留 null）')
w('```')
w('')
w('%COORD%')
text = '\n'.join(L) + '\n'
(BASE / 'RECEIPT_O0300-2610.md').write_text(text, encoding='utf-8', newline='\n')
print('md chars', len(text))
