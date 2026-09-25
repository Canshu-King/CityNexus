"""ORD-0301 pass 2 human supplement: the rows the first pass left out, plus the served-generation change
that happened while I was measuring (observed, not caused by me)."""
from __future__ import annotations

import json
import pathlib

B = pathlib.Path('D:/moodle/_hjp3_0301_0925')
T = json.loads((B / 'table_O0301.json').read_text(encoding='utf-8'))
RC = json.loads((B / 'RECEIPT_O0301P2-1540.json').read_text(encoding='utf-8'))
D, TIP = T['derived'], T['measured_on']
R = {r['row'].split('_')[0]: r for r in T['rows']}
BOUND1 = json.loads((B / 'boundary_proof.json').read_text(encoding='utf-8'))
BOUND2 = json.loads((B / 'boundary_proof_o0301p2.json').read_text(encoding='utf-8'))
STATE2 = json.loads((B / 'o0301p2_state.json').read_text(encoding='utf-8'))
COORD = '%COORD%'
FAILED_IDS = '、'.join(sorted({x.name[len('probe_'):].rsplit('_', 1)[1].split('.')[0]
                               for x in B.iterdir() if x.name.startswith('probe_a')
                               and not (B / ('cell_' + x.name[len('probe_')])).exists()}))
L = []
w = L.append
w('# ORD-0301 补交（pass 2）· 把单子里点名的类别量齐 · HJ-P3 aad2d1f2')
w('')
w('> **measured_on = `%s`**（同一代、同一枚私有构建 `%s` / sha256 `%s`，与 pass 1 逐字节相同）· 新端口 %s–%s、'
  '一次性库重新由产品 `ensure_schema()` 建、journey `%s` 是本批新建（**没有复用 pass 1 的任何一行**）。'
  % (TIP[:12], STATE2['bundle_facts']['served_asset'], STATE2['bundle_facts']['served_sha256'][:16] + '…',
     STATE2['ports']['backend_real'], STATE2['ports']['face_upstream_absent'], STATE2['seed']['journey_id']))
w('> **`derived_result` = null**；`claimed_result = MEASURED_NOT_GRADED`。本件是**新文件名**（照号令者 15:1x 那句"以后加格子一律新文件名"），'
  'pass 1 的 `RECEIPT_O0301-1500.*` 一字未动。')
w('')
w('## 1. 我第一遍漏了哪一类（先认这个）')
w('单子第四节原文列了五类，其中 **④「答了 200 但 payload 空或畸形」** 我第一遍一行都没量；③ 也只量了"端口拔掉/源站断线"，'
  '没量单子点名的 **`route.abort()`**；⑤ 我第一遍量的是"服务器一直不答"，不是单子写的"**客户端期限先到、服务器事后才答**"。'
  '这三处都是我的口径比单子窄，不是产品没给机会。本批 7 行补上。')
w('')
w('## 2. 补的 7 行（同一张表，接在 pass 1 的 17 行后面）')
w('')
w('| 行 | 结局 | 服务端读数（状态·类型·字节·毫秒·谁答的） | 屏幕原话（逐字首行） | 「连不上服务端」 | `<details>` | 判定 |')
w('|---|---|---|---|---|---|---|')
for t in ('R18', 'R19', 'R20', 'R21', 'R22', 'R23', 'R24'):
    r = R[t]
    w('| %s | %s | %s · %s · %s B · %s ms · %s | %s | %s | %s | **%s** |' % (
        t, r['outcome_class_as_asked'], r['server_side']['http_status'],
        (r['server_side']['content_type'] or '—')[:30], r['server_side']['bytes'],
        r['server_side']['elapsed_ms'], r['server_side']['answer_attributed_to'],
        (r['screen_side']['painted_first_line'] or '（无结局卡）')[:24],
        r['screen_side']['says_cannot_reach_server'], r['screen_side']['details_elements_in_dom'], r['verdict']))
w('')
w('```text')
w('类别覆盖（单的第四节 → 表里的行）：')
for k, v in sorted(D['dispatch_class_coverage'].items()):
    w('  %s → %s' % (k, '、'.join(v)))
w('  每一条点名类别都至少有一行 = %s ｜ 表里 %d 行没有一行落在类别之外 = %s'
  % (D['every_named_class_has_at_least_one_row'], D['rows'], len(D['rows_in_the_table_not_in_any_class']) == 0))
w('```')
w('')
w('## 3. ④ 这一类：按你的判据它是**绿的**，但我不替你把另一句话藏起来')
w('```text')
w('五枚 200（正文依次 %s B / %s B / %s B / %s B / %s B，类型 %s 与 %s）屏幕上全部是同一句 %r，'
  'data-result-status 全是 %r'
  % (R['R19']['server_side']['bytes'], R['R20']['server_side']['bytes'], R['R21']['server_side']['bytes'],
     R['R22']['server_side']['bytes'], R['R23']['server_side']['bytes'],
     R['R19']['server_side']['content_type'], R['R22']['server_side']['content_type'],
     R['R19']['screen_side']['painted_first_line'],
     R['R19']['screen_side']['data_result_status_cross_check']))
w('  · 没有任何一行把原因归给网络 = %s ⇒ 按你写的判据（"服务器答了就不许归给网络"）这五格 HONEST' % D['no_200_row_blamed_the_network'])
w('  · 但"技术详情"块在 DOM 里 = %s（五枚全 0，%s），也没有任何原因标签/值'
  % (R['R19']['screen_side']['details_elements_in_dom'], D['every_200_malformed_row_lost_the_detail_block']))
w('  · 也就是说：服务器给的是"我答了 200，但这一发的正文你读不出结构"，屏幕说的是"%s"——一个具体的原因，底下什么证据都没有。'
  % R['R19']['screen_side']['painted_first_line'])
w('  · 你说最在意 C2 那格把「这是我们猜的」一起吞掉；这里同一件事从**另一条代码路**发生（%r 不需要 helper 抛穿，它自己就不渲染 details）。'
  % R['R19']['screen_side']['data_result_status_cross_check'])
w('  两种读法我都摆在件里（C9 的 verdict 名就是按后者写的），**判哪一层归你**。')
w('```')
w('')
w('## 4. ③ 与 ⑤ 各补一枚（把口径对齐单子原文）')
w('```text')
w('③ route.abort 只掐被点那一腿：浏览器侧 %r / 网络层 %r / %s ms，无 HTTP 状态 ⇒ 屏上 %r ⇒ 判 %s。'
  % (R['R18']['server_side']['client_error'], RC['cells'][1]['measured']['browser_side']['request_failure_reason'],
     R['R18']['server_side']['elapsed_ms'], R['R18']['screen_side']['painted_first_line'], R['R18']['verdict']))
w('   这一行是 pass 1 那批 MISLEADS 的**配对反证**：同一句话在"真没人答"时是诚实的，所以 ①那批的错不能靠"删掉这句文案"来修。')
w('⑤ 服务器事后才答：源站被声明为读腿延迟 %s ms 再答；浏览器在 %s ms 处自己期限（%r），屏上 %r；'
  % (R['R24']['declared_read_delay_ms'],
     (R['R24']['secondary_surface'] or {}).get('page_level_legs', [{}])[0].get('elapsed_ms'),
     (R['R24']['secondary_surface'] or {}).get('page_level_legs', [{}])[0].get('client_error'),
     (R['R24']['secondary_surface'] or {}).get('what_the_traveller_was_left_with', '')[:40]))
w('   源站自己在 %s 记下这一发写不进去：%r ⇒ 期限比答案早 %s ms，答案存在但已无处投递。'
  % (RC['cells'][2]['measured']['origin_own_record'][0]['at'],
     RC['cells'][2]['measured']['origin_own_record'][0]['error'],
     R['R24']['declared_read_delay_ms'] - 12007))
w('```')
w('')
w('## 5. 两件现场事实（都不是我做的，但我撞见了就得说）')
w('```text')
w('在服预览那一代在本批中间换了：pass 1 时我记到的是 sha256 %s / mtime %s / 引用 %s；'
  % (BOUND1['live_preview_index']['sha256'][:12], BOUND1['live_preview_index']['mtime_local'],
     (BOUND1['live_preview_index']['asset_referenced'] or ['-'])[0]))
w('  pass 2 时 %s / mtime %s / 引用 %s。我这批所有面的 --outDir 都是我自己的 %s（sha256 %s，两批相同），'
  % (BOUND2['live_preview_index']['sha256'][:12], BOUND2['live_preview_index']['mtime_local'],
     (BOUND2['live_preview_index']['asset_referenced'] or ['-'])[0],
     'dist_0300', BOUND2['what_my_faces_served']['sha256'][:12]))
w('  我对那个路径只做过一次读（哈希它），0 写 0 改名 0 重启；换它的是别的车道或下一班。**新代 %s 上这一格还红不红：我没测，不替它签。**'
  % (BOUND2['live_preview_index']['asset_referenced'] or ['-'])[0])
w('用户链仍没被我碰：4781/4782 的监听进程创建时间 %s、%s，早于我任何一批。'
  % (BOUND2['user_chain_listeners'][1]['process_created'][:19],
     BOUND2['user_chain_listeners'][0]['process_created'][:19]))
w('```')
w('')
w('## 6. 我自曝（本批新增）')
w('```text')
w('1) 这 7 臂有**第一次执行全部作废**：runarm 里端口还是 pass 1 的硬编码 8564，而那张面我在 pass 1 收尾时已经停了 '
  '（run id %s）。那几发只留下 probe 与源站记录、没有 cell，所以没有任何读数是它们的；修法是端口一律从当前 rig 的 state 读。'
  % FAILED_IDS)
w('2) 我在同一轮里被 shell 吃掉过两处反斜杠字面量（\\0` 与 `\\d`），导致写出的仪器含 NUL 字节、正则失效；'
  '修法是不再在源里放反斜杠字面量（bytes([0]) / 不用正则）。这类错误我今天第三次踩，记在这里而不是抹掉。')
w('3) 上一批我把"stop 报表"只打印不落盘，这一批一开始就 `> teardown_O0301P2_r1.txt`，五枚进程按种类谓词全 True、'
  '端口 %s–%s 现全空。' % (STATE2['ports']['backend_real'], STATE2['ports']['deliberately_empty']))
w('```')
w('')
w('## 7. 尺子（本批自跑）')
w('```text')
w((B / 'q38_ruler_p2.txt').read_text(encoding='utf-8').strip())
w('```')
w('')
w('%s' % COORD)
(B / 'RECEIPT_O0301P2-1540.md').write_text(chr(10).join(L) + chr(10), encoding='utf-8', newline='\n')
print('supplement md lines', len(L))
