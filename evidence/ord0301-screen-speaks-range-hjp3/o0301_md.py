"""Render ORD-0301's human receipt from the same artefacts the machine receipt reads."""
from __future__ import annotations

import json
import pathlib

B = pathlib.Path('D:/moodle/_hjp3_0301_0925')
T = json.loads((B / 'table_O0301.json').read_text(encoding='utf-8'))
STATE = json.loads((B / 'o0301_state.json').read_text(encoding='utf-8'))
CFG = json.loads((B / 'config_default_this_batch.json').read_text(encoding='utf-8'))
BOUND = json.loads((B / 'boundary_proof.json').read_text(encoding='utf-8'))
DOOR = json.loads((B / 'door_test_8000.json').read_text(encoding='utf-8'))
MOVED = json.loads((B / 'tip_moved_readback.json').read_text(encoding='utf-8'))
REF = json.loads((B / 'ref_readback.json').read_text(encoding='utf-8'))
RC = json.loads((B / 'RECEIPT_O0301-1500.json').read_text(encoding='utf-8'))
RULER = (B / 'q38_ruler_run1.txt').read_text(encoding='utf-8') if (B / 'q38_ruler_run1.txt').exists() else '（尺子还没跑）'
D, TIP = T['derived'], T['measured_on']
L = []
w = L.append

w('# ORD-0301 · 把「屏幕替服务器说话」的射程量成一张表 · HJ-P3 aad2d1f2')
w('')
w('> **measured_on = `%s`**（%s，%s 现场重读）· 被测产物 = 我从这棵尖自己 `vite build` 出来的私有件 `%s` / sha256 `%s` · '
  '在服预览那枚 `dist/index.html` **一个字节没动**（sha256 `%s`，mtime %s，引用的是 `%s`，与我面的 `%s` 不是同一枚）。'
  % (TIP[:12] + '…', 'git ls-remote refs/heads/mirror/integration-frontend-apple-pass1',
     STATE.get('measured_on_how_read', 're-read at export time'),
     STATE['bundle_facts']['served_asset'], STATE['bundle_facts']['served_sha256'][:16] + '…',
     BOUND['live_preview_index']['sha256'][:12], BOUND['live_preview_index']['mtime_local'],
     (BOUND['live_preview_index']['asset_referenced'] or ['-'])[0],
     BOUND['what_my_faces_served']['asset'][0]))
w('> **`derived_result` = null**（那是 verifier 的字）；`claimed_result = %s`。Q25：本件每一个毫秒数都是这一代今天量出来的，没有一个从 0300/0291 搬来。'
  % 'MEASURED_NOT_GRADED')
w('')
w('## 0. 一句话（大白话）')
w('服务器**只要答了一个 HTTP 状态**，屏幕上那张卡就必须说是服务器的事。今天这条路上有 %d 枚结局做不到这一点，'
  '而且原因不是"它不认识 500"——**是它拿不到一个 JSON 对象**：`serverReasonSentence` 在 `body` 为 null 的时候直接去读 `body.detail`，'
  '抛出去的错误被整段 try 的大 `catch` 接走，于是写成「连不上服务端」，连「技术详情」整块都不再存在（`<details>` 数 = 0）。'
  % len(D['misleads_rows']))
w('')
w('## 1. 判据怎么落的（不是我事后挑的）')
w('```text')
w('规则原文            ：服务器答了 ⇒ 屏幕不许把原因归给网络')
w('answered            ：被点那一腿在浏览器里拿到了 HTTP 状态（页面 fetch 钩子记的；无钩子那臂用源站自己的记账回读）')
w('blames_network      ：屏上 painted 的第一行 == 连不上服务端（读 innerText，不读 data 属性；data-result-status 只当旁证）')
w('判定                ：answered ∧ blames_network ⇒ MISLEADS ｜ answered ∧ ¬blames_network ⇒ HONEST ｜ ¬answered ⇒ HONEST（确实没人答）')
w('走不到那张卡        ：NOT_MEASURED + 旅客实际停在的另一张卡的原文（secondary_surface）')
w('结局卡从未出现      ：NOT_MEASURED + 观察帽毫秒数')
w('谁答的              ：product ｜ my-origin ｜ vite-proxy ｜ none —— 每一行都点名，因为 500 分两种 500')
w('```')
w('')
w('## 2. 表（每行 = 结局 / 服务端读数 / 屏幕原话 / 是否「连不上服务端」/ details / 判定）')
w('')
w('| # | 结局（下单时那一类） | 服务端读数（状态·类型·字节·毫秒·谁答的） | 屏幕原话（painted 第一行） | 「连不上服务端」 | `<details>` | 判定 |')
w('|---|---|---|---|---|---|---|')
for i, r in enumerate(T['rows'], 1):
    sv, sc = r['server_side'], r['screen_side']
    server = '%s · %s · %s B · %s ms · %s' % (sv['http_status'], (sv['content_type'] or '—')[:34],
                                              sv['bytes'], sv['elapsed_ms'], sv['answer_attributed_to'])
    w('| %d | %s | %s | %s | %s | %s | **%s** |' % (
        i, r['outcome_class_as_asked'], server,
        (sc['painted_first_line'] or '（无结局卡）')[:30],
        sc['says_cannot_reach_server'], sc['details_elements_in_dom'], r['verdict']))
w('')
w('读法说明：第 4 行的字节/毫秒是 None —— 那一臂按设计**不装** fetch 钩子，它的服务端那半来自源站自己的记账'
  '（件里字段 `server_side_reading_from`）；第 12/13 行是"从来没结算"，第 17 行是"头说了 21 B 但只写了 5 B，'
  '浏览器读体永远不结束"，所以它们的字节数列同样是 None，而不是 0。')
w('')
w('```text')
w('判定合计   MISLEADS %d ｜ HONEST %d ｜ NOT_MEASURED %d   （共 %d 行）'
  % (len(D['misleads_rows']), len(D['honest_rows']), len(D['not_measured_rows']), D['rows']))
w('MISLEADS 行 %s' % '、'.join(x.split('_')[0] for x in D['misleads_rows']))
for r in T['rows']:
    if r['secondary_surface']:
        w('%s 走不到结局卡，旅客停在：「%s」→ 同一条规则打在另一张卡上 = %s'
          % (r['row'].split('_')[0], r['secondary_surface']['what_the_traveller_was_left_with'][:70],
             r['secondary_surface']['same_rule_applied_to_this_surface']))
w('```')
w('')
w('## 3. 判别量不是状态码、也不是时长，是"正文能不能交出一个 JSON 对象"')


R = {r['row'].split('_')[0]: r for r in T['rows']}
w('同一枚 HTTP %s：正文 = 产品今天真发的那 %s B 信封 ⇒ %s（标签 %r 下正是服务器原话 %r，逐字相等 = %s）'
  % (R['R5']['server_side']['http_status'], T['captured_envelope']['bytes'], R['R5']['verdict'],
     R['R5']['screen_side']['reason_label_painted'], R['R5']['screen_side']['reason_value_painted'],
     D['envelope_sentence_quoted_verbatim_equals']))
w('同一枚 HTTP %s、同一个 content-type：正文 = %r ⇒ %s（%r）；正文 = %r ⇒ %s（标签改口成 %r，因为服务器确实没给句子）'
  % (R['R15']['server_side']['http_status'], 'null', R['R15']['verdict'],
     R['R15']['screen_side']['painted_first_line'], '{}', R['R16']['verdict'],
     R['R16']['screen_side']['reason_label_painted']))
w('同一枚正文（%s B 纯文本 Internal Server Error）：HTTP %s ⇒ %s、HTTP %s ⇒ %s —— 换状态码不换命运'
  % (R['R1']['server_side']['bytes'], R['R1']['server_side']['http_status'], R['R1']['verdict'],
     R['R9']['server_side']['http_status'], R['R9']['verdict']))
w('时长无关：%s ms（%s B）与 %s ms（%s B）与 %s ms（%s B，产品自己在锁上答的那发）三枚卡片一模一样 ⇒ %s'
  % (R['R2']['server_side']['elapsed_ms'], R['R2']['server_side']['bytes'],
     R['R3']['server_side']['elapsed_ms'], R['R3']['server_side']['bytes'],
     R['R1']['server_side']['elapsed_ms'], R['R1']['server_side']['bytes'],
     D['duration_is_not_the_discriminator']))
w('没有仪器复跑：把 fetch 钩子整段拆掉（只留 localStorage 那一枚行程指针），同一句话、`<details>` 仍是 %s ⇒ %s'
  % (R['R2']['screen_side']['details_elements_in_dom'], D['uninstrumented_reproduction_agrees']))
w('反控两枚都拒（证明我用的是逐字相等不是"包含"）：标点漂移后仍相等 = %s ｜ 后缀漂移后仍相等 = %s'
  % (D['punctuation_drift_still_equals'], D['suffix_drift_still_equals']))
w('机械派生的四条：同一个状态换正文换命 = %s ｜ 不同状态同一正文同命 = %s ｜ null 与 {} 这一对分岔 = %s ｜ '
  '所有 MISLEADS 行都拿不到 JSON 对象 = %s ｜ 所有 HONEST 且被答过的行都没抛 = %s'
  % (D['same_status_different_body_shape_flips_the_verdict'],
     D['different_status_same_body_shape_keeps_the_verdict'], D['null_versus_empty_object_pair_differs'],
     D['every_misleads_row_had_no_json_object_for_the_helper'],
     D['no_honest_answered_row_threw_on_the_body']))
w('```')
w('')
w('## 4. 机制（这一格的红不是"翻译错了"，是一个抛穿）')
w('```text')
for n, rec in sorted(RC['cells'][3]['measured']['source_lines_on_this_tip'].items(),
                     key=lambda x: int(x[0])):
    w('PlanWithAiSheet.tsx:%s  在 %s 里：%s' % (n, rec['inside'].split('{')[0].strip(), rec['line']))
w('两处读的都是 body 这个变量本身（只有上一行的 .error 带 ?）；body 在正文不是 JSON 对象时就是 null ⇒')
w('    catch (cause) { … setResult({status: "NETWORK", failureReason: null})} ⇒ 「连不上服务端」＋没有 details。')
w('浏览器侧的直接证据（我这台仪器 hook 了 Response.prototype.json，把被吞掉的拒绝原样记下来）：')
for e in RC['cells'][3]['measured']['rejections_seen_in_the_browser']:
    w('    %s · content-type %s · %s' % (e['row'].split('_')[0], e['content_type'],
                                         (e['error_message'] or '')[:88]))
w('注意 R15 那发：正文 %r 是合法 JSON，response.json() 不抛，返回 null，仍然在 %s 行抛 —— 所以修的方向是"把 body 当可空"，'
  '不是"把 JSON 解析包一层 try"。' % ('null', 'PlanWithAiSheet.tsx:155'))
w('```')
w('')
w('## 5. 五类结局落在哪（下单点名要的那五类，一类都没换成"等价物"）')
w('```text')
w('① 服务器答 500 且正文无 code/message   ⇒ 真件那一发 %s ms / %s B / %s，屏上 %r ⇒ MISLEADS（与 0300 同形，今天在案）'
  % (R['R1']['server_side']['elapsed_ms'], R['R1']['server_side']['bytes'],
     R['R1']['server_side']['content_type'], R['R1']['screen_side']['painted_first_line']))
w('② 服务器答 500 但正文带具名 code        ⇒ 产品今天这条用户路发不出它（唯一 500 带信封的发射点是 main.py:3075 '
  'stay-options/generate，AI 面板不走它）；我用产品自己那枚真信封的字节把它答成 500 ⇒ %s，'
  '所以这一格的红**不是"引用不了"，是"该引用的时候它说没响应"**' % R['R5']['verdict'])
w('③ 502 / 503 / 504                      ⇒ 带 JSON 信封三枚全 %s（标签 %r、details %s）；'
  '网关那种纯文本 503（%s B）⇒ %s —— 同一个 503，正文决定它会不会被说成网络问题'
  % (R['R6']['verdict'], R['R5']['screen_side']['reason_label_painted'],
     R['R5']['screen_side']['details_elements_in_dom'], R['R9']['server_side']['bytes'], R['R9']['verdict']))
w('④ 连接被拒（后端不在）                  ⇒ 面 %s 的上游端口 %s 上没人听；**vite 代理自己**答 %s / %s / %s B，'
  '结局卡走不到（旅客停在页面级那张 %r，同一条规则打它 = %s）；另一枚"源站收了就断"同样由代理答 %s B，'
  '这张卡就是 %r ⇒ MISLEADS'
  % (STATE['ports']['face_upstream_absent'], STATE['ports']['deliberately_empty'],
     R['R10']['server_side']['sibling_probe_outside_browser']['status'],
     R['R10']['server_side']['sibling_probe_outside_browser']['content_type'],
     R['R10']['server_side']['sibling_probe_outside_browser']['bytes'],
     (R['R10']['secondary_surface'] or {})['what_the_traveller_was_left_with'][:24],
     (R['R10']['secondary_surface'] or {})['same_rule_applied_to_this_surface'],
     R['R11']['server_side']['bytes'], R['R11']['screen_side']['painted_first_line']))
w('⑤ 请求超时（客户端先放弃）              ⇒ 读腿会：GET 被静默时 %s ms 处客户端自己期限，屏上 %r（HONEST，确实没人答）；'
  '写腿不会：POST 被静默到 %s ms 仍没有任何结局卡（details %s）—— 那 12 秒的常量在写分支短路，这一格是 NOT_MEASURED '
  '而不是绿'
  % (json.loads((B / ('cell_a12_ctl_silent_read_%s.json' % R['R13']['run_id']))
                .read_text(encoding='utf-8'))['no_sheet']['legs'][0]['elapsed_ms'],
     (R['R13']['secondary_surface'] or {})['what_the_traveller_was_left_with'][:26],
     R['R12']['cap_ms'], R['R12']['screen_side']['details_elements_in_dom']))
w('⓪ 额外两格（不在单子里但同一条病）      ⇒ 正文 = null 的合法 JSON ⇒ MISLEADS；头说了 21 B 只写 5 B ⇒ '
  '到 %s ms 结局卡根本没出现，屏上停在等待态，既没期限也没名字' % R['R17']['cap_ms'])
w('```')
w('')
w('## 6. ORD-0296 那枚具名 503：今天还是拿不出来，但这次是门拦的')
w('```text')
w('产品自己的数（在进程内读它自己的配置，不是我猜的）  busy_timeout=%s ms · default deadline=%s ms · '
  'delta=%s ms · verdict=%s'
  % (CFG['busy_timeout_ms'], CFG['settings_write_deadline_ms'],
     CFG['verdict']['per_scenario']['agent.commands']['delta_ms'],
     CFG['verdict']['per_scenario']['agent.commands']['verdict']))
w('我这轮把 CITYNEXUS_WRITE_DEADLINE_MS 设成 %s 起了一次面：booted=%s、exit_rc=%s、日志里点名的错 = %s'
  % (DOOR['env_CITYNEXUS_WRITE_DEADLINE_MS'], DOOR['booted'], DOOR['exit_rc'],
     'WriteDeadlineConfigurationError' if DOOR['error_named_in_log'] else None))
w('含义：`main.py:427` 那扇启动门**真的在跑**（0300 我只能说"算术上够不着"，这次是"配置上一开机就死"）；'
  '要让服务器自己把那枚具名 503 发到这条路上，必须先允许一个门会拒绝的配置。')
w('```')
w('')
w('## 7. 现场 · 边界 · 我自曝')
w('```text')
w('端口：后端 %s、真件面 %s、可控源站 %s、可控面 %s、"上游不在"那张面 %s，故意留空的 %s —— 全新一批，'
  '收尾后逐个回读为空（teardown_O0301.json）。' % (STATE['ports']['backend_real'], STATE['ports']['face_real'],
                                                STATE['ports']['outcome_origin'], STATE['ports']['face_controlled'],
                                                STATE['ports']['face_upstream_absent'],
                                                STATE['ports']['deliberately_empty']))
w('库：%s，由产品自己的 ensure_schema() 建、起面先删（R-SCHEMA-01）；`_live.db`/`_preview.db` 0 读写、'
  '`demo/reset` 0 次、`git apply` 0 次 —— 这三句不是空口，boundary_proof.json 里把我九个仪器文件里出现这些词的行'
  '逐行打了出来（唯一命中是本机边界文件的被查字符串清单与 docstring）。' % STATE['db'])
w('用户链没动：在服 `dist/index.html` sha256 %s / mtime %s（引用 %s，与我面的 %s 不同一枚）；'
  '4781/4782 的监听进程创建时间 %s、%s，都早于我这一批 %s ⇒ 0 重启。'
  % (BOUND['live_preview_index']['sha256'][:12], BOUND['live_preview_index']['mtime_local'],
     (BOUND['live_preview_index']['asset_referenced'] or ['-'])[0],
     BOUND['what_my_faces_served']['asset'][0],
     BOUND['user_chain_listeners'][1]['process_created'][:19],
     BOUND['user_chain_listeners'][0]['process_created'][:19], BOUND['batch_start_local'][:19]))
w('凭据：rig 里每个子进程环境都先 pop 掉 DEEPSEEK_API_KEY（=%s），我的文件里没有任何 sk- 形状串（命中 %s 个）；'
  'AI 在我这套面上是关的。'
  % (BOUND['credential_handling']['DEEPSEEK_API_KEY_popped_in_rig'],
     len(BOUND['credential_handling']['printed_anywhere_in_my_files'])))
w('自曝一：第一批臂跑完我发现源站的逐请求日志被我在换策略时 `unlink` 掉了 —— 那等于把每一行"服务端那半"的凭据删了。'
  '改成 append-only + 每臂快照之后，**17 行全部重跑了一遍**，本件所有数字来自第二遍；第一遍的工件留在目录里没删。')
w('自曝二：驱动与仪器我自己写坏过三次 —— `WindowsPath % int`（两处，start 与 policy 各崩一次，崩的时候 backend 已经起来，'
  '我按端口逐个读命令行确认是我自己的进程才杀，没有盲杀）、页内 SCREEN 里引用了 Node 作用域的常量（`NET_CARD is not defined`，'
  '那一轮没有工件产出，run id O0301-143117 作废）、以及无仪器那臂一开始忘了塞行程指针结果停在 onboarding（第一次读数作废，'
  '修好后才是表里 R4）。')
w('自曝三：表里"谁答的"那一列是我事后加硬的口径 —— ④ 那两枚 500 是 vite 代理写的，不是产品写的。'
  '如果按"任何 HTTP 回答都算服务器答了"，R11 记 MISLEADS；如果只算产品自己答，R11 应该降为 NOT_MEASURED。'
  '两种读法我都在件里给了字段（`answer_attributed_to` + `sibling_probe_outside_browser`），**不替你选**。')
w('```')
w('')
w('## 8. 尺子（Q38 口径，交前自己先跑）')
w('```text')
w(RULER.strip())
w('```')
w('')
w('## 9. 代次边界（这条我必须自己先说，不等谁来问）')
w('```text')
w('本件 17 行的 measured_on = %s（下单点名那一枚）。交之前 %s 我现场重读同一条路由：尖已经变成 %s（compare: %s，'
  'ahead_by=%s，total_commits=%s，改动文件里确实有 PlanWithAiSheet.tsx）。'
  % (TIP[:12], MOVED['ran_at_local'][11:19], REF['tip'][:12], MOVED['compare']['status'],
     MOVED['compare']['ahead_by'], MOVED['compare']['total_commits']))
w('新尖上那两行有没有修：blob %s（%s B）里 `PlanWithAiSheet.tsx:147` 与 `:155` 仍是 %s，'
  '`?.detail` 之类的空值守卫 = %s ⇒ **源码层面这一格在新尖上仍然是同一枚洞**。'
  % (MOVED['new_tip']['blob_sha1'], format(MOVED['new_tip']['bytes'], ','),
     MOVED['new_tip']['unguarded_detail_lines'][0][1], MOVED['new_tip']['null_guard_on_detail']))
w('但我今天所有**运行时**读数（含毫秒、卡片文字、`<details>` 数）属于 %s 那棵树的私有构建 `%s`；'
  '新尖的运行时我没跑，不替它签字，也不把上面这些数字搬过去（Q25）。要在新尖上重跑同一套 17 行，我这把 rig 现成。'
  % (TIP[:12], STATE['bundle_facts']['served_asset']))
w('```')
w('')
w('%COORD%')
(B / 'RECEIPT_O0301-1500.md').write_text(chr(10).join(L) + chr(10), encoding='utf-8')
print('md written, lines', len(L))
