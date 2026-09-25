"""ORD-0300 C2 challenge - stage 6: the human receipt. Every number is re-read from the artefacts at
write time; the coordinate line is filled by the publish script, never typed.
"""
from __future__ import annotations

import json
import pathlib
import time

BASE = pathlib.Path('D:/moodle/_hjp3_0300c2_0925')
R = json.loads((BASE / 'RECEIPT_O0300C2-1955.json').read_text(encoding='utf-8'))
S = json.loads((BASE / 'c2_score.json').read_text(encoding='utf-8'))
C, D = S['cells'], S['derived']
BOUND = R['boundary']
SETUP = json.loads((BASE / 'setup_facts.json').read_text(encoding='utf-8'))
T90 = json.loads((BASE / 't90_facts.json').read_text(encoding='utf-8'))
CELL = {x['id']: x for x in R['cells']}
K1, K2 = CELL['K1_pairing_one_leg_seen_by_three_independent_readers'], CELL['K2_the_challenged_cell_lifted_from_unproven']
K3, K4 = CELL['K3_the_mechanism_one_variable_three_bundles'], CELL['K4_negative_control_the_card_is_not_evidence']
K5, K6 = CELL['K5_the_schedule_varies_and_the_generation_it_was_born_on'], CELL['K6_the_product_fact_that_needs_no_same_request_proof']
K7 = CELL['K7_limits_i_am_not_passing_off_as_green']
RULE = [p for p in sorted(BASE.glob('q38_ruler_O0300C2-1955_*.txt'))][-1]
RULE_TXT = RULE.read_text(encoding='utf-8').strip().splitlines()
TD = [p for p in sorted(BASE.glob('teardown_*.json'))][-1]
CLOSING_PATH = pathlib.Path('D:/moodle/_qoder_cmdr_ref_20260921/live_checks/CLOSING_LINE.txt')
CLOSING = CLOSING_PATH.read_text(encoding='utf-8').rstrip('\r\n')
assert len(CLOSING.encode('utf-8')) == 83, len(CLOSING.encode('utf-8'))
SERVED = K7['measured']['one_read_only_get_on_the_shared_chain']

P1, P2, P3 = ('P1_controlled500_old_bundle', 'P2_controlled500_current_bundle',
              'P3_controlled500_two_guards_reverted')
N1, N2 = 'N1_transport_death_old_bundle', 'N2_transport_death_current_bundle'
R1A, R1B, R2, R3 = ('R1a_real500_landed_on_agent_commands', 'R1b_real500_landed_on_plans_generate',
                    'R2_real500_current_tip', 'R3_real500_generation_the_cell_was_born_on')


def L(k):
    for x in C[k]['write_legs']:
        if (x['upstream_status'] or 0) >= 500:
            return x
    return C[k]['write_legs'][-1]


def cd(k):
    return C[k]['card']


def b(x, n=None):
    return (x or '')[:n] if n else x


out = []
w = out.append
w('### 📱 aad2d1f2 (SESSION=aad2d1f2) P3 · **ORD-0300 C2 撑回：两条路都走了（① 服务端编号回显 + ② 页面自己的 '
  'fetch 过会记状态码的代理）⇒ 那一格在 `dc964086c9d412573ac19d70b24b30e6c3ee6168` 上从 UNPROVEN 撑起来了，'
  '不需要改名；但同一格在 `90d29a172e186aab6e6cb138ab4583ccf93bfa68`（它出生那一代）我那一发配对跑出来的 '
  '500 落在 `plans/generate`、卡片是另一张 ⇒ 旧名对旧读数标 SUPERSEDED_BY_EVIDENCE，新读数用新名** @%s+08'
  % time.strftime('%H:%M'))
w('')
w('**先按你的规矩收口**：这一格我不自宣 CLOSED，`claimed_result = MEASURED_NOT_GRADED`、`derived_result` 仍 '
  'null（那是 verifier 的字）。下面每一个毫秒、每一枚字节数都是从本批量出来的件里重读的，没有一个数从 '
  'ORD-0300 继承（Q25）。')
w('')
w('## 一、①+②：同一发请求，一枚页面上猜不出来的编号')
w('')
w('```text')
for k, name in ((P1, '受控那发（我的代理按产品的字节形状答 500）'), (R1A, '产品自己答 500 那一发')):
    l = L(k)
    w('%s · %s · %s' % (name, C[k]['file'], C[k]['arm']))
    w('  后端尖 %s ｜ 面 %s（bundle 源尖 %s，sha256 %s…）｜ 一次性库 %s' % (
        C[k]['backend_tip'], C[k]['bundle_asset'], C[k]['bundle_source_tip'],
        C[k]['bundle_sha256'][:16], C[k]['db'].replace('D:\\moodle\\_hjp3_0300c2_0925\\', '')))
    w('  编号 %s：代理审计行 %d 条 · 答案头 X-HJP3-Pair %s · 页面自己的 fetch 读回 %s ⇒ 三处同一个串' % (
        l['pair_id'], l['proxy_lines_with_this_token'], l['pair_id_echoed_in_answer_header'],
        l['pair_id_read_by_app']))
    w('  服务器侧：status %s · %s B · %s · 正文开头 %r · 上游用时 %s' % (
        l['upstream_status'], l['upstream_bytes'], l['upstream_content_type'], l['upstream_body_head'],
        ('%s ms' % l['upstream_elapsed_ms']) if l['upstream_elapsed_ms'] is not None
        else '没有上游（这一发的答案是按产品字节形状由我的代理给的）'))
    w('  页面侧：status %s · rejected=%s · %s ms · 浏览器网络栈同一枚 %s' % (
        l['page_saw_status'], l['page_fetch_rejected'], l['page_elapsed_ms'], l['browser_stack_status']))
    w('  应用把那一发读了：.json() 抛 %s（%r）⇒ 卡片写下的那一刻，答案在页面手里' % (
        l['app_parse_error_name'], l['upstream_body_head']))
    w('  屏上：data-result-status=%s · <details> 元素 %d 个 · 卡片 %r' % (
        cd(k)['result_status'], cd(k)['detail_regions_in_dom'], b(cd(k)['card_text'], 44)))
    w('')
w('归属双向证明（这台后端是我的）：`%s`' % json.dumps(K1['measured']['backend_ownership_two_sided'],
                                                    ensure_ascii=False))
w('全批计数：代理落了 %d 条审计行、%d 枚不同编号 ⇒ 一枚编号只指一发（%s）。编号的来源可查：'
  'c2proxy.py:47 每发新建 `hjp3c2-` + uuid4 前 16 位；那份代理里 `X-HJP3-Pair` 只出现在两处，都是**往回答里写**'
  '（:78 我答的那发、:109 透传的那发），没有任何一处从请求里读它 ⇒ 页面猜不到、也没参与造。' % (
      D['pair_log_lines'], D['pair_log_distinct_ids'], D['each_id_names_exactly_one_leg_in_the_whole_batch']))
w('```')
w('')
w('## 二、被挑战那一格：在号令者点名的尖上撑起来了')
w('')
l = L(R1A)
w('```text')
w('产品（tip %s）对 %s 这一发答 %s / %s B / %s / %r，用时 %s ms；' % (
    C[R1A]['backend_tip'], l['leg_tail'], l['upstream_status'], l['upstream_bytes'],
    l['upstream_content_type'], l['upstream_body_head'], l['upstream_elapsed_ms']))
w('同一个编号在页面自己的 fetch 上落成 status %s（%s ms，没被拒），浏览器网络栈同一枚 %s；' % (
    l['page_saw_status'], l['page_elapsed_ms'], l['browser_stack_status']))
w('屏上卡片就是你说的那张：%r，data-result-status=%s，<details> %d 个。' % (
    b(cd(R1A)['card_text'], 42), cd(R1A)['result_status'], cd(R1A)['detail_regions_in_dom']))
w('⇒ 派生布尔（全部从上面这些行算出来，没有一个字面量）：%s' % json.dumps(
    {k: D[k] for k in ('the_real_product_answered_500_on_the_agent_commands_leg',
                       'that_same_leg_is_the_one_the_page_saw',
                       'the_card_that_arm_painted_is_the_one_the_challenge_called_into_question',
                      'the_reproduction_is_on_the_tip_the_commander_named',
                       'and_the_server_side_body_is_the_contentless_21_byte_one',
                       'lifted_from_unproven_on_the_named_tip')}, ensure_ascii=False))
w('⇒ 所以：不需要改名成 `UI_FETCH_DIED_AT_TRANSPORT_AFTER_~32s`（那一形我也有，见第四节，但它不是这一格）。')
w('```')
w('')
w('**旧读数怎么处理（不藏）**：架上那对 `32,330 ms / 32,762 ms` 里没有任何请求编号（%s），所以它**不能回补**成'
  '同一发；我把它的名字标成 `SUPERSEDED_BY_EVIDENCE`，新名字 `%s` 只主张我这批配上的那一发（tip %s）。' % (
      json.dumps(K2['measured']['what_ORD_0300_C2_recorded']['no_request_id_of_any_kind_in_that_cell']),
      D['challenged_cell_disposition']['new_cell_name'], C[R1A]['backend_tip']))
w('')
w('## 三、机制是单变量：同一枚答案，三张卡，只差那两行')
w('')
w('```text')
w('同一枚答案：status %s · %s B · %s（三发臂的服务器侧字节完全一样）' % (
    L(P1)['upstream_status'], L(P1)['upstream_bytes'], L(P1)['upstream_content_type']))
for k in (P1, P2, P3):
    w('  %s（源尖 %s）⇒ 卡片 %s · <details> %d' % (
        C[k]['bundle_asset'], C[k]['bundle_source_tip'][:12], cd(k)['result_status'],
        cd(k)['detail_regions_in_dom']))
diff = D['source_lines_that_differ_between_the_current_bundle_and_the_mutant']
w('突变体与当前尖的源文件只差这些行：%s' % diff['lines_that_differ'])
for x in diff['text']:
    w('  :%d 当前尖 %s' % (x['line'], x['new'].strip()))
    w('  :%d 突变体 %s' % (x['line'], x['mut'].strip()))
w('守卫计数是我从四份导出里重算的（不是抄的）：')
for which, g in D['guard_shape_read_from_the_three_generations'].items():
    w('  %-4s blob %s · 无守卫 .detail %s @%s · 带守卫 %s @%s · 设备侧句子 @%s · 共 %d 行' % (
        which, g['sha1_blob_like_hash'], g['unguarded_detail_reads'], g['unguarded_at_lines'],
        g['guarded_detail_reads'], g['guarded_at_lines'], g['device_note_at_lines'], g['lines_total']))
w('我这一台重算出来的 old 树 blob = `%s`，与你手上的 40 位全字一致 = %s' % (
    D['guard_shape_read_from_the_three_generations']['old']['sha1_blob_like_hash'],
    D['guard_shape_read_from_the_three_generations']['old']['sha1_blob_like_hash'] ==
    SETUP['exports']['old']['sheet_blob_expected']))
w('```')
w('')
w('## 四、反证：卡片本身不是证据；另外那条"传输死掉"的形状确实存在')
w('')
w('```text')
n1 = L(N1)
w('N1 %s：那一发 0 条代理行、页面 fetch 直接 %r（浏览器 %s）⇒ 卡片与 P1 **逐字相同**（%s），<details> 同为 %d' % (
    C[N1]['file'], n1['page_reject'], n1['browser_stack_failure'],
    K4['measured']['identical_card_on_the_old_bundle'], cd(N1)['detail_regions_in_dom']))
w('⇒ 分开 P1 与 N1 的只有编号配对：%s' % json.dumps(
    {k: D[k] for k in ('what_separates_the_two_is_the_pairing_not_the_card',
                       'the_transport_death_leg_has_no_server_side_line_at_all',
                       'the_negative_control_is_mine_not_the_products')}, ensure_ascii=False))
w('这一形就是你给的备选名 `UI_FETCH_DIED_AT_TRANSPORT_AFTER_~32s` 的真身 —— 但它是**我自己掐断**的（页侧 route '
  'abort），不是产品自己走到的；所以我把它当反证发布，不把它冒充 C2 的成因。')
w('当前尖上真断链的那一发：卡片仍说"连不上"（%s），但 <details> = %d，因为 NETWORK 分支现在带了自己那句设备侧的'
  '话（源文件 :%s）。' % (cd(N2)['result_status'], cd(N2)['detail_regions_in_dom'],
                          D['guard_shape_read_from_the_three_generations']['new']['device_note_at_lines'][0]))
w('```')
w('')
w('## 五、调度不是我能挑的：四发配对的真实 500 落在哪条腿')
w('')
w('```text')
for k in (R1A, R1B, R2, R3):
    x = L(k)
    w('%-40s tip %s · 500 落在 %-16s · 服务器 %s ms / 页面 %s ms · 卡片 %-28s · <details> %d' % (
        C[k]['file'].replace('arm_', '').replace('.json', ''), C[k]['backend_tip'][:12], x['leg_tail'],
        x['upstream_elapsed_ms'], x['page_elapsed_ms'], cd(k)['result_status'],
        cd(k)['detail_regions_in_dom']))
w('另两发同形状的锁臂（%s、%s）没等到 500：锁在写期限之前放了，两条腿分别 %s / %s ⇒ 记在件里，不当已闭。' % (
    C['R4_lock_released_before_any_500']['file'], C['R5_lock_released_before_any_500_guards_reverted']['file'],
    [x['upstream_status'] for x in C['R4_lock_released_before_any_500']['write_legs']],
    [x['upstream_status'] for x in C['R5_lock_released_before_any_500_guards_reverted']['write_legs']]))
w('')
w('吃掉 500 的那条腿**逐次不同**：%s' % D['the_leg_that_eats_the_real_500_varies_between_runs_on_one_tip'])
w('在它出生那一代（%s）我这一发落在 %s、卡片是 %s ⇒ 与架上 C2 那对数字不同形，这一条我不抹平。' % (
    T90['tip'], L(R3)['leg_tail'], cd(R3)['result_status']))
w('所有卡片里都没有出现状态码数字或那条腿的名字：%s ⇒ 用户看不出是哪条腿死的，这句是可站住的读法。' %
  D['no_lock_run_painted_a_card_that_names_the_5xx_status_or_the_leg'])
w('那一代的 bundle 我按 ORD-0300 记的字节验过：%s == %s = %s（sheet blob %s）' % (
    C[R3]['bundle_sha256'], T90['bundle_sha256'], C[R3]['bundle_sha256'] == T90['bundle_sha256'],
    T90['sheet_blob_40_hex']))
w('```')
w('')
w('## 六、你说更要紧的那条产品事实（这条不需要同发证明）')
w('')
w('```text')
for k in (P1, N1, R1A, P2, N2, P3):
    w('%-40s tip %-13s %-12s 卡片 %-28s <details> %d' % (
        C[k]['file'].replace('arm_', '').replace('.json', ''), C[k]['backend_tip'][:12], C[k]['scenario'],
        cd(k)['result_status'], cd(k)['detail_regions_in_dom']))
w('⇒ 卡片说"连不上"的那一支，在 %s 上三种来路全是 **0** 个技术详情块（受控 500、产品真 500、真断链），在当前尖上'
  '全是 **%d** 个（它现在带自己那句设备侧的话）。' % (C[P1]['backend_tip'][:12], cd(N2)['detail_regions_in_dom']))
w('⇒ `%s` 这一代要说白：本批在它上面唯一配对的 500 臂卡片不是 NETWORK 那一支（第五节），所以那一代"0 个详情块"'
  '引的是架上 ORD-0300 自己的读数 + 我这批从源码数出来的形状：它的 NETWORK 分支里连那句设备侧的话都没有（守卫计数'
  '表 t90 行：设备侧句子 @%s）。' % (
      T90['tip'][:12], D['guard_shape_read_from_the_three_generations']['t90']['device_note_at_lines']))
w('⇒ 派生：%s' % json.dumps({k: D[k] for k in D if k.startswith(('old_network_branch',
                                                                'current_branch_network',
                                                                'the_no_detail_fact'))}, ensure_ascii=False))
w('给 ORD-0302 的一句话：旧两代的「技术详情」标题下没有东西可开；当前尖已经不等那条腿了，缺的是把**服务器原文**'
  '放进来（X-5 那条），不是再加一句"检查网络"。')
w('```')
w('')
w('## 七、闸、反控与自曝')
w('')
w('```text')
w('· Q38 尺（r2）对最终收据：%s' % [x for x in RULE_TXT if x.startswith('cells ')][0])
w('  尺子输出单列成件（%s），收据不抄自己的判词；那一件末行的话是：%s' % (
    RULE.name, [x for x in RULE_TXT if x.startswith('expectation held')][0]))
w('· 全部判词从实测行派生：%d 枚布尔里 %d 枚为真，且 `ALL_REQUIRED_HOLD` = %s。这一批我自改一处：上一版里写死的 '
  '4 枚布尔（3 枚 `..._card_names_that_leg = False` 与 1 枚 `... = True`）全部改成从读数算，算不出来就不许出现在'
  '件里；只配最后一腿的 %d 枚早期臂列进 `runs_excluded`，具名在件里、不删。' % (
      D['booleans_true'], D['booleans_required'], D['ALL_REQUIRED_HOLD'], len(S['runs_excluded'])))
w('· 受控那发的正当性：那一格主张的是"页面手里有没有答案"，我的代理按产品自己的字节形状答（%s B、%s、%s）；'
  '需要**产品**亲自答的场合全在 R1a/R1b/R2/R3 里 —— 那四发都是产品真答出来的 500、每发都带编号配对；落在哪条腿'
  '逐发不同（第五节全表），我不挑一发冒充必然。' % (
      L(P1)['upstream_bytes'], L(P1)['upstream_content_type'], repr(L(P1)['upstream_body_head'])))
w('· 自曝 %d 条（细节在 `RECEIPT_O0300C2-1955.json` 的 K7）：' % K7['measured']['instrument_fault_count'])
for i, s0 in enumerate(K7['measured']['instrument_events_disclosed'], 1):
    w('   %d) %s' % (i, s0[:168]))
w('```')
w('')
w('**边界（一句）**：0 改产品字节、0 推他人 ref、0 权威线写入、`demo/reset` 0、`_live`/`_preview` 0 读写、'
  '凭据 0 打印（rig 里 pop 掉 key）、`git apply` 0、`dist/index.html` 0 写（sha256 %s · mtime %s · 引用 %s）、'
  '端口收尾 %s 全空 = %s（%s）。' % (
      BOUND['live_preview_index']['sha256_full_64_hex'], BOUND['live_preview_index']['mtime_local'],
      BOUND['live_preview_index']['asset_referenced'], TD.name,
      json.loads((BASE / TD).read_text(encoding='utf-8'))['all_my_ports_free'],
      json.dumps(BOUND['user_chain_listeners_untouched'], ensure_ascii=False)))
w('对 :4781 我只有 **1 次只读 GET**（取被服务的那枚 JS，不写、不带凭据）：%s B，sha256 与我私有构建逐字节相同 = %s ⇒ '
  '现在服务给用户的就是 `%s` 这一代（守卫已在、设备侧句子已在）。' % (
      SERVED['bytes'], SERVED['byte_identical'], SETUP['bundles']['new']['asset']))
w('')
w('坐标（发布脚本从分支 tree 读回，非手抄）：@COORD@')
w('')
w(CLOSING)
text = '\n'.join(out) + '\n'
(BASE / 'RECEIPT_O0300C2-1955.md').write_text(text, encoding='utf-8', newline='\n')
print('wrote RECEIPT_O0300C2-1955.md', (BASE / 'RECEIPT_O0300C2-1955.md').stat().st_size, 'B')
print('lines', len(text.splitlines()))
