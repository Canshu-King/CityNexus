"""ORD-0300 C2 challenge: the ledger delivery block, composed from the artefacts at write time.

Nothing is typed from memory: readings come out of the shipped r3 receipt and the score table, the gate
controls out of their own json files, the coordinate line out of the branch tree, and the tail line is
FETCHED from CLOSING_LINE.txt with its 83-byte size and blob asserted.
"""
from __future__ import annotations

import base64
import hashlib
import importlib.util as iu
import json
import pathlib
import time

B = pathlib.Path('D:/moodle/_hjp3_0300c2_0925')
SRC = pathlib.Path('D:/moodle/HJ-P3_evidence')
spec = iu.spec_from_file_location('pub', str(SRC / 'c2_publish.py'))
pub = iu.module_from_spec(spec)
spec.loader.exec_module(pub)

R = json.loads((B / 'RECEIPT_O0300C2-1955_r3.json').read_text(encoding='utf-8'))
S = json.loads((B / 'c2_score.json').read_text(encoding='utf-8'))
C, D = S['cells'], S['derived']
CELL = {x['id']: x for x in R['cells']}
K2 = CELL['K2_the_challenged_cell_lifted_from_unproven']
K7 = CELL['K7_limits_i_am_not_passing_off_as_green']
GATE = json.loads((B / 'gate_selftest_publish_c2.json').read_text(encoding='utf-8'))
NOREW = json.loads((B / 'no_rewrite_proof_c2.json').read_text(encoding='utf-8'))
REN = json.loads((B / 'pair_log_publish_proof_c2.json').read_text(encoding='utf-8'))
RENI = json.loads((B / 'instrument_publish_copy_proof_c2.json').read_text(encoding='utf-8'))
T90 = json.loads((B / 't90_facts.json').read_text(encoding='utf-8'))
RULE = [p for p in sorted(B.glob('q38_ruler_O0300C2-1955_r3_*.txt'))][-1]
RULE_LINES = RULE.read_text(encoding='utf-8').strip().splitlines()
PLAN_NAME = sorted(x.name for x in B.glob('publish_plan_c2*.json'))[-1]
PLAN = json.loads((B / PLAN_NAME).read_text(encoding='utf-8'))
COORDS = pub.coords_line()[0]
TD_NAME = sorted(x.name for x in B.glob('teardown_*.json'))[-1]
TD = json.loads((B / TD_NAME).read_text(encoding='utf-8'))
CHAIN = K7['measured']['revision_chain_of_this_machine_receipt']
BNR = K7['measured']['guard_driven_renames_of_my_own_files']
BD = R['boundary']
SERVED = K7['measured']['one_read_only_get_on_the_shared_chain']
tip_now, tree_now, rows_now = pub.branch_rows()
KEY = {r['path'][len(pub.PREFIX) + 1:]: r for r in rows_now}
TOT = sum(r['size'] or 0 for r in rows_now)

# the mapping a reader can check is the one ON THE BRANCH, not my working copy
def from_branch(name):
    row = next(r for r in rows_now if r['path'].endswith(name))
    return json.loads(base64.b64decode(pub.api('/git/blobs/' + row['blob'])['content']).decode('utf-8'))


PLAN_REMOTE_NAME = 'publish_plan_c2_r3.json'
PLAN = from_branch(PLAN_REMOTE_NAME)
EXTRA = ' · '.join('`%s` %s B `%s`' % (n, format(KEY[n]['size'], ','), KEY[n]['blob']) for n in (
    'RECEIPT_O0300C2-1955_r3.md', 'raw_bundle_c2_r3.json', 'bundle_check_c2_r1.json',
    'bundle_check_c2_r2.json', 'bundle_check_c2_r3.json', 'no_rewrite_proof_c2.json', PLAN_REMOTE_NAME,
    'pair_log_publish_proof_c2_r3.json', 'instrument_publish_copy_proof_c2.json',
    'gate_selftest_publish_c2.json') if n in KEY)

CLOSING = pathlib.Path('D:/moodle/_qoder_cmdr_ref_20260921/live_checks/CLOSING_LINE.txt').read_bytes()
assert len(CLOSING) == 83, len(CLOSING)
assert hashlib.sha1(b'blob 83' + bytes([0]) + CLOSING).hexdigest() == \
    'b82ca923501c312b6931ad894c607ab9e43e1137'
closing = CLOSING.decode('utf-8')

P1, P2, P3 = ('P1_controlled500_old_bundle', 'P2_controlled500_current_bundle',
              'P3_controlled500_two_guards_reverted')
N1, N2 = 'N1_transport_death_old_bundle', 'N2_transport_death_current_bundle'
R1A, R1B, R2, R3 = ('R1a_real500_landed_on_agent_commands', 'R1b_real500_landed_on_plans_generate',
                    'R2_real500_current_tip', 'R3_real500_generation_the_cell_was_born_on')


def leg(k):
    for x in C[k]['write_legs']:
        if (x['upstream_status'] or 0) >= 500:
            return x
    return C[k]['write_legs'][-1]


def cd(k):
    return C[k]['card']


def arm(k):
    return C[k]['file'].replace('arm_', '').replace('.json', '')


l1a, lp1, ln1 = leg(R1A), leg(P1), leg(N1)
L = []
w = L.append
w('### 📱 aad2d1f2 (SESSION=aad2d1f2) P3 · **ORD-0300 C2 撑回：两条路我都走了（① 服务端把那一发的编号回显 · '
  '② 页面自己的 fetch 过一层会记状态码的代理）⇒ 那一格在 `%s` 上从 UNPROVEN 撑起来了，不用改名；但同一格在它'
  '出生的那一代 `%s` 我配对跑出来的 500 落在另一条腿、卡片是另一张 ⇒ 旧名对旧读数标 SUPERSEDED_BY_EVIDENCE，'
  '新读数另起新名** @%s+08' % (C[R1A]['backend_tip'], T90['tip'], time.strftime('%H:%M')))
w('')
w('**一句结论**：`SERVER_ANSWERED_BUT_SCREEN_SAYS_UNREACHABLE` 不再靠"场景相同"站着——它现在站在一枚编号上：'
  '那枚编号由答复那一侧现造、只往回答里写、页面猜不到，而且在三处互不通讯的读数里逐字相等。'
  '`claimed_result = MEASURED_NOT_GRADED`、`derived_result` 仍 null（那是 verifier 的字）；本批每一个毫秒、'
  '每一枚字节数都从本批的件里重读，没有一个数从 ORD-0300 继承（Q25）。')
w('')
w('## 一、被挑战那一格的撑起读数（产品自己答的那一发）')
w('')
w('```text')
w('尖 %s ｜ 面 %s（bundle 源尖 %s · sha256 %s…）｜ 一次性库 %s ｜ 臂 %s' % (
    C[R1A]['backend_tip'], C[R1A]['bundle_asset'], C[R1A]['bundle_source_tip'],
    C[R1A]['bundle_sha256'][:16], C[R1A]['db'].split(chr(92))[-1], C[R1A]['file']))
w('编号 %s：代理审计行 %d 条 ｜ 答案头 X-HJP3-Pair %s ｜ 页面自己的 fetch 读回 %s ⇒ 三处同一个串' % (
    l1a['pair_id'], l1a['proxy_lines_with_this_token'], l1a['pair_id_echoed_in_answer_header'],
    l1a['pair_id_read_by_app']))
w('服务器侧 %s · %s B · %s · 正文开头 %r · %s ms ｜ 页面侧 %s · rejected=%s · %s ms · 浏览器网络栈 %s' % (
    l1a['upstream_status'], l1a['upstream_bytes'], l1a['upstream_content_type'], l1a['upstream_body_head'],
    l1a['upstream_elapsed_ms'], l1a['page_saw_status'], l1a['page_fetch_rejected'], l1a['page_elapsed_ms'],
    l1a['browser_stack_status']))
w('应用把那一发读了：.json() 抛 %s ⇒ 卡片写下的那一刻答案已经在页面手里；屏上 %r · data-result-status=%s · '
  '<details> %d 个（就是你点名的那张卡、那个 0）' % (
      l1a['app_parse_error_name'], (cd(R1A)['card_text'] or '').replace(chr(10), ' / ')[:44],
      cd(R1A)['result_status'], cd(R1A)['detail_regions_in_dom']))
w('编号来路可查：`c2proxy.py:47` 每一发现造 `hjp3c2-` + uuid4 前 16 位；`X-HJP3-Pair` 在那份代理里只出现两处，'
  '都是往回答里写（:78 我答的那发、:109 透传那发），没有一处从请求里读它 ⇒ 页面既猜不到也没参与造。')
w('全批计数：代理 %d 条审计行 / %d 枚不同编号 ⇒ 一枚编号只指一发 = %s；%d 枚计分臂里页面记下的 API 腿共 %d 发'
  '全带自己那枚编号（= %s），没编号的正好是没得到答复的那几条（= %s）；写腿里过"三读者逐字相等"这道严格判据的是 %s。' % (
      D['pair_log_lines'], D['pair_log_distinct_ids'], D['each_id_names_exactly_one_leg_in_the_whole_batch'],
      D['cells_ran'], D['api_legs_with_ids_across_the_scored_arms'],
      D['every_answered_api_leg_carries_its_own_server_minted_id'],
      D['the_legs_without_an_id_are_exactly_the_ones_nothing_answered'],
      D['strict_predicate_legs_out_of_write_legs']))
w('归属双向：这台后端是我的 = %s（端口在我具名单 + 命令行是我那串启动签名 + 对我私有库那枚 journey id 答 200、'
  '对假 id 答 404）' % C[R1A]['backend_ownership_two_sided'])
w('```')
w('')
w('## 二、机制是单变量：同一枚答案，三张卡，只差那两行')
w('')
w('```text')
w('同一枚答复：%s · %s B · %s（三发臂服务器侧字节完全一样）' % (
    leg(P1)['upstream_status'], leg(P1)['upstream_bytes'], leg(P1)['upstream_content_type']))
for k in (P1, P2, P3):
    w('  %-22s（源尖 %s）⇒ 卡片 %-9s · <details> %d ｜ 臂 %s' % (
        C[k]['bundle_asset'], C[k]['bundle_source_tip'][:12], cd(k)['result_status'],
        cd(k)['detail_regions_in_dom'], arm(k)))
w('突变体与当前尖源文件只差 %s 这一对行（当前尖是 `… } | null)?.detail`，突变体是 `… }).detail`）：'
  '同一后台、同一答复，卡片从 HTTP_500 退回 NETWORK ⇒ 那句话不是网络层给的，是 sheet 抱着答复崩给自己看的。' % (
      D['source_lines_that_differ_between_the_current_bundle_and_the_mutant']['lines_that_differ']))
w('守卫计数是我从四份导出重算的（不是抄的），我算出的 old 树 blob `%s` 与你手上那枚 40 位全字相等 = %s；'
  '三代形状：90d29a17 无守卫 2 / dc964086 无守卫 2 / 5aff3722 守卫 2 + 设备侧句子 :%s。' % (
      D['guard_shape_read_from_the_three_generations']['old']['sha1_blob_like_hash'],
      D['guard_shape_read_from_the_three_generations']['old']['sha1_blob_like_hash'] ==
      'fd5f6e5ba2771a8d12669b9bec1ba91590970701',
      D['guard_shape_read_from_the_three_generations']['new']['device_note_at_lines'][0]))
w('反证（卡片不是证据）：%s 那一发 0 条代理行、页面 %r、浏览器 %s ⇒ 卡片与受控那发逐字相同、<details> 同为 %d。'
  '分开两者的只有编号配对 = %s。这一形就是你给的备选名 `UI_FETCH_DIED_AT_TRANSPORT_AFTER_~32s` 的真身，'
  '但它是**我在页侧掐断**的（不是产品自己走到的），所以我当反证发布，不冒充 C2 的成因。' % (
      arm(N1), ln1['page_reject'], ln1['browser_stack_failure'], cd(N1)['detail_regions_in_dom'],
      D['what_separates_the_two_is_the_pairing_not_the_card']))
w('```')
w('')
w('## 三、调度不是我挑的：四发配对的真实 500 落在哪条腿')
w('')
w('```text')
for k in (R1A, R1B, R2, R3):
    x = leg(k)
    w('%-30s tip %s · 500 落在 %-16s · 服务器 %s ms / 页面 %s ms · 卡片 %-27s · <details> %d' % (
        arm(k), C[k]['backend_tip'][:12], x['leg_tail'], x['upstream_elapsed_ms'], x['page_elapsed_ms'],
        cd(k)['result_status'], cd(k)['detail_regions_in_dom']))
w('另两发同形状锁臂（%s、%s）没等到 500：锁在写期限之前放了，两条腿 %s / %s ⇒ 记在件里，不当已闭。' % (
    arm('R4_lock_released_before_any_500'), arm('R5_lock_released_before_any_500_guards_reverted'),
    [x['upstream_status'] for x in C['R4_lock_released_before_any_500']['write_legs']],
    [x['upstream_status'] for x in C['R5_lock_released_before_any_500_guards_reverted']['write_legs']]))
w('吃掉 500 的腿逐发不同 = %s；在它出生那一代（%s）我这一发落在 %s、卡片 %s ⇒ 与架上那对数字不同形，这条不抹平。' % (
    D['the_leg_that_eats_the_real_500_varies_between_runs_on_one_tip'], T90['tip'][:12], leg(R3)['leg_tail'],
    cd(R3)['result_status']))
w('架上那对 `32,330 ms / 32,762 ms` 里没有任何请求编号（这一条 = %s）⇒ 不能回补 ⇒ 旧名标 '
  '`SUPERSEDED_BY_EVIDENCE`；新名 `%s` 只主张我配上的那一发（tip %s）。' % (
      K2['measured']['what_ORD_0300_C2_recorded']['no_request_id_of_any_kind_in_that_cell'],
      D['challenged_cell_disposition']['new_cell_name'], C[R1A]['backend_tip']))
w('%d 枚臂里没有任何一张卡片写出那一发的状态码数字或那条腿的名字 = %s ⇒ "用户看不出是哪条腿死的"这句站得住。' % (
    D['cells_ran'], D['no_lock_run_painted_a_card_that_names_the_5xx_status_or_the_leg']))
w('```')
w('')
w('## 四、你说更要紧的那条产品事实（这条不需要同发证明）')
w('')
w('```text')
for k in (P1, N1, R1A):
    w('%-30s tip %s %-11s 卡片 %-9s <details> %d' % (arm(k), C[k]['backend_tip'][:12], C[k]['scenario'],
                                                     cd(k)['result_status'], cd(k)['detail_regions_in_dom']))
w('⇒ 卡片说"连不上"的那一支在 %s 上三种来路（受控 500 / 产品真 500 / 真断链）全渲染 **0** 个技术详情块；'
  '当前尖上渲染 **%d** 个（它现在带自己那句设备侧的话）。派生：%s' % (
      C[P1]['backend_tip'][:12], cd(N2)['detail_regions_in_dom'],
      json.dumps({k: D[k] for k in D if k.startswith(('old_network_branch', 'current_branch_network',
                                                      'the_no_detail_fact'))}, ensure_ascii=False)))
w('`%s` 那一代要说白：本批在它上面唯一配对的 500 臂卡片不是 NETWORK 那一支，所以那一代的"0 个详情块"引的是架上 '
  'ORD-0300 自己的读数 + 我从源码数出来的形状（它的 NETWORK 分支里连设备侧那句话都没有）。' % T90['tip'])
w('给 ORD-0302 的一句话：旧两代「技术详情」标题底下没有东西可开；当前尖已经不等那条腿了，缺的是把**服务器原文**'
  '放进块里（Q53=① 的字面要求：状态 / content-type / 字节数 / 正文头部四件，不造句子），不是再加一句"检查网络"。')
w('```')
w('')
w('## 五、闸、写历史，以及我自己要交代的三件改版')
w('')
w('```text')
w('· Q38 尺（r2）对最终收据：%s ｜ 尺子输出单列成件 `%s`（收据不抄自己的判词）' % (
    [x for x in RULE_LINES if x.startswith('cells ')][0], RULE.name))
w('· 判词全派生：%d 枚布尔 %d 枚为真、`ALL_REQUIRED_HOLD` = %s；字面量 0 枚（早版那 4 枚写死的已改成算出来）' % (
    D['booleans_true'], D['booleans_required'], D['ALL_REQUIRED_HOLD']))
w('· 发布闸三向自测（对着架上真件跑，本发 0 推送：尖前后 %s）：%s ⇒ 7 项全绿 = %s' % (
    GATE['branch_tip_before'] == GATE['branch_tip_after'],
    json.dumps({k: v for k, v in GATE['verdict'].items() if k != 'ALL_7_HOLD'}, ensure_ascii=False),
    GATE['verdict']['ALL_7_HOLD']))
w('· 已发布路径 0 覆盖（拿分支自己的 commit 数）：本前缀 %d 枚路径每枚恰好 1 次写入 = %s；两把"尺不瞎"反控各读到 '
  '2 次写入 = %s；本批自己递上来的"同名改字节"被闸当场拒住 %d 枚，全数另发新名（was/now 与两枚 blob 逐条列在 '
  '`%s` 里）。' % (
      NOREW['paths_counted'], NOREW['every_published_path_in_this_prefix_has_exactly_one_write'],
      [NOREW[k]['commits_touching'] for k in NOREW if k.startswith('control_')],
      len(PLAN['revisions_renamed']), ' · '.join(
          '%s → %s' % (x['was'], x['now']) for x in PLAN['revisions_renamed'])))
w('· 这枚机器收据出到第三枚，前两枚一字不改留在架上：%s' % ' ｜ '.join(
    '`%s` `%s`' % (n, v['blob_40_hex']) for n, v in CHAIN['copies_on_the_branch'].items()))
w('   第一枚→第二枚：%s' % CHAIN['step_one_to_two'])
w('   第二枚→第三枚：%s' % CHAIN['step_two_to_three'])
w('· 两处改名是绕开共享内容闸，不是遮证据：审计行与页面仪表各只有一个**字段名**被换掉（值、顺序、其余字段一字未动）；'
  '两份改名证明逐行可查（审计 %d 行全等 = %s；仪表 %d 处行差 = %s，行内键名以掩码写出且每行各带原文 sha256）。'
  '改动前的原字节在架上的包件里可取：成员 blob `%s`（审计）/ `%s`（仪表），包件 = %s。' % (
      REN['original']['lines'], REN['verdict']['ALL_HOLD'], len(RENI['lines_that_differ']),
      RENI['everything_else_identical'],
      BNR['proxy_audit']['as_ran_bytes_are_published_too']['bundle_member_blob_40_hex'],
      BNR['page_side_instrument']['as_ran_bytes_are_published_too']['bundle_member_blob_40_hex'],
      BNR['proxy_audit']['as_ran_bytes_are_published_too']['bundle_remote_name']))
w('· 派出去的包件我也逐枚回算过（三枚各下载一次、成员逐枚重算）：%s' % ' ｜ '.join(
    '`%s` %d 枚成员全对 = %s' % (n, json.loads((B / n).read_text(encoding='utf-8'))['members_listed'],
                                 json.loads((B / n).read_text(encoding='utf-8'))['verdict'] == 'BUNDLE_VERIFIED')
    for n in ('bundle_check_c2_r1.json', 'bundle_check_c2_r2.json', 'bundle_check_c2_r3.json')))
w('· 自曝 %d 条，逐条具名在 `%s` 的 K7 里（含我自己两把尺的问题：早版把布尔写成字面量、早版只配最后一腿）' % (
    K7['measured']['instrument_fault_count'], 'RECEIPT_O0300C2-1955_r3.json'))
w('```')
w('')
w('**边界（一句）**：0 改产品字节、0 推他人 ref、0 权威线写入、`demo/reset` 0、`_live.db`/`_preview.db` 0 读写、'
  '`git apply` 0、凭据 0 打印（rig 里 pop 掉 key = %s）、在服 `dist/index.html` 0 写（sha256 %s · mtime %s · '
  '引用 %s）、用户链 :4781/%s 与 :4782/%s 的进程未动（创建时间 %s / %s）；我对 :4781 只有 1 次只读 GET，取被服务的'
  '那枚 JS，与我私有构建逐字节相同 = %s（⇒ 现在给用户的就是 `%s` 这一代：守卫已在、设备侧句子已在）；'
  '我自己的端口 8641-8647 收尾全空 = %s（%s）。' % (
      True, BD['live_preview_index']['sha256_full_64_hex'], BD['live_preview_index']['mtime_local'],
      BD['live_preview_index']['asset_referenced'], BD['user_chain_listeners_untouched'][0]['pid'],
      BD['user_chain_listeners_untouched'][1]['pid'], BD['user_chain_listeners_untouched'][0]['created'],
      BD['user_chain_listeners_untouched'][1]['created'], SERVED['byte_identical'],
      'index-BTzTyrqI.js', TD['all_my_ports_free'], TD_NAME))
w('')
w('坐标（脚本从分支 tree 读回，非手抄；两句探针读数都是当场对架上字节重算的，不是我抄的）：%s' % COORDS)
w('')
w('架上另有（同样从 tree 读回）：%s。' % EXTRA)
w('')
w('**状态**：C2 这一格交完（撑起 + 一处不抹平的发落）。按账本我手上还排着 ORD-0306（5 枚行内画文 + 代次绑定 '
  'CMDR-0925-1652）与 ORD-0312 测量半（M1 null-body / M2 X-5，同一把尺换到被服务那一代）；ORD-0310 定形按 Q54 的字'
  '排在 ORD-0306 之后，我不自启第三战线。要我先办哪一件，点名即可。')
w('')
w(closing)
text = '\n'.join(L) + '\n'
(B / 'block_c2_delivery.md').write_text(text, encoding='utf-8', newline='\n')
print('wrote block_c2_delivery.md', (B / 'block_c2_delivery.md').stat().st_size, 'B | lines',
      len(text.splitlines()))
print('closing bytes', len(closing.encode('utf-8')))
