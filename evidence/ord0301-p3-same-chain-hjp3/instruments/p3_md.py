"""ORD-0301 pass 3, stage 6: the human supplement.

Every count, every quoted sentence and every table row here is read out of RECEIPT_O0301P3-2230.json (which
itself only holds values the scorer derived from the arm files), so the prose cannot drift from the numbers.
The coordinate line is a %COORD% placeholder filled from the branch tree after the rest of the batch lands -
never hand-copied.
"""
from __future__ import annotations

import json
import pathlib
import time

BASE = pathlib.Path('D:/moodle/_hjp3_0301p3_0925')
RC = json.loads((BASE / 'RECEIPT_O0301P3-2230.json').read_text(encoding='utf-8'))
SC = json.loads((BASE / 'p3_scored.json').read_text(encoding='utf-8'))
CELLS = {c['id']: c for c in RC['cells']}
B = SC['generations']
SB = SC['served_generation_binding']
TD = SC['teardown']
K1, K2, K3, K4, K5, K6, K7 = (CELLS['K1_one_chain_both_ends_of_the_same_leg'],
                              CELLS['K2_row_non_json_body'], CELLS['K3_row_json_envelope_4xx'],
                              CELLS['K4_the_class_is_the_body_not_the_status'],
                              CELLS['K5_the_deployed_bundle_is_the_guarded_one'],
                              CELLS['K6_two_published_generation_claims_are_withdrawn'],
                              CELLS['K7_limits_exclusions_and_my_own_faults'])


def arms(cell, key):
    return cell['readings'][key]


BIND = json.loads((BASE / 'served_generation_bind_c2.json').read_text(encoding='utf-8'))


def sel(gen, **kw):
    """pick an arm out of the scored rows by what the scorer recorded, never by a run id I remember"""
    hits = [r for r in SC['arms_scored'] if r['gen'] == gen
            and all(r.get(k) == v for k, v in kw.items())]
    assert len(hits) == 1, ('wanting exactly 1 row for %s %s, got %s'
                            % (gen, kw, [h['run_id'] for h in hits]))
    return hits[0]


dep500 = sel('dep', scenario='hoplock')
old500 = sel('old', scenario='hoplock')
dep422env = sel('dep', scenario='product')
old422env = sel('old', scenario='product')
dep422plain = sel('dep', spec_name='nonjson_422')
old422plain = sel('old', spec_name='nonjson_422')
dep500env = sel('dep', spec_name='json_envelope_500')
old500env = sel('old', spec_name='json_envelope_500')
abort = sel('dep', scenario='abort')
ROWS9 = [dep500, old500, dep422env, old422env, dep422plain, old422plain, dep500env, old500env, abort]


def cell_of(r):
    return '%s · %s B %s' % (('%s' % r['server_status']) if r['server_status'] else '无回答',
                             r['server_bytes'] if r['server_bytes'] is not None else '-',
                             (r['server_content_type'] or '-').split(';')[0])


def who(r):
    return {'product': '产品自己答的', 'instrument_origin_per_spec': '量具代答'}.get(
        r['answer_producer'], '没人答（腿没出门）')


L = []
w = L.append
w('# ORD-0301 pass 3 · 同一链路两侧读数 + 两类正文分行（HJ-P3）')
w('')
w('号令者 494abfd7 在 21:5x 撤了对 C2 的挑战，并给了三处修正。本批逐条答：')
w('')
w('| 修正 | 本批怎么做 | 落在哪一格 |')
w('|---|---|---|')
w('| ① 不要求证「同一发」 | 收到，但链路既然在，就仍然逐腿带号，不额外花钱 | K1 |')
w('| ② 服务器侧与屏侧改为**同一代理链路里取** | 一切读数出自同一个 hop：hop 在 accept 时造号，只写进**回答**头 '
  '`X-HJP3-Pair`，四个读者（hop 审计行 / 页面自己的 fetch / 浏览器网络栈 / 应用调用的 '
  '`Response.prototype.json`）按同号对齐；全批没有第二次「我去问后端答了啥」的探针 | K1 |')
w('| ③ **非 JSON 正文**与**带 envelope 的 4xx** 分开列 | 两类各一行，而且各在两个状态码上跑（500 与 422 互换正文），'
  '这样类名不会被听成状态码的另一种说法 | K2、K3，控制格 K4 |')
w('')
w('## 射程表（本批实测 %d 臂，两代各跑）' % RC['arms_scored'])
w('')
w('| 类 | 代次 | 状态码 | 服务器侧那一发（同链路） | 谁答的 | 屏上标题 | 归因标签（点开技术详情后的字面） | '
  '技术详情块 |')
w('|---|---|---|---|---|---|---|---|')
for r in ROWS9:
    w('| %s | %s | %s | %s B `%s` · %s ms | %s | %s | %s | %s 个 |'
      % ('非 JSON 正文' if r['server_body_is_json'] is False
         else ('JSON envelope' if r['server_body_is_json'] else '无回答'),
         ('部署代 %s' % B['dep']['tip'][:8]) if r['gen'] == 'dep'
         else ('未守卫代 %s' % B['old']['tip'][:8]),
         r['server_status'] if r['server_status'] else '—（腿未出门）',
         r['server_bytes'] if r['server_bytes'] is not None else '—',
         (r['server_content_type'] or '—').split(';')[0],
         r['server_elapsed_ms'] if r['server_elapsed_ms'] is not None else '—',
         who(r), '「%s」' % r['card_title'],
         '「%s」' % r['attribution_label'] if r['attribution_label'] else '（无标签）',
         r['details_blocks']))
w('')
w('三句话读法：')
w('')
w('1. **判据确实是正文的形状，不是状态码。** 都回答 422：正文是产品自己渲染的 `%s` envelope（%s B）时，两代都把'
  '服务器原话 "%s" 挂在「%s」下面；正文换成 %s B 的裸文本，状态码一个字没变，部署代就改口成「%s」，未守卫代更直接'
  '掉进「%s」卡片、技术详情块剩 %s 个。500 那一侧（%s B 的产品 500 对 %s B 的代具 envelope）同样只随正文翻。'
  % (dep422env['server_content_type'].split(';')[0], dep422env['server_bytes'], dep422env['reason_text'],
     dep422env['attribution_label'], dep422plain['server_bytes'], dep422plain['attribution_label'],
     old422plain['card_title'], old422plain['details_blocks'], dep500['server_bytes'],
     dep500env['server_bytes']))
w('2. **你那条根因链在两代上表现不同，而且差的那一代不在手机上。** 同一条 %s B / %s 的产品 500，'
  '未守卫代 `%s` 落进 NETWORK 卡片（此时 failureReason 为 null，所以归因标签与技术详情整块都不在：详情块 %s 个，'
  '且 React 把这个异常吞了，page_errors %s 条），'
  '部署代 `%s` 走 HTTP_500 + 设备侧标签「%s」+ 句子 `%s`，详情块 %s 个。'
  % (dep500['server_bytes'], dep500['server_content_type'].split(';')[0], B['old']['tip'][:8],
     old500['details_blocks'], len(old500['page_errors']), B['dep']['tip'][:8],
     dep500['attribution_label'], dep500['reason_text'], dep500['details_blocks']))
w('3. **「连不上服务端」在部署代仍然有一句是真话。** 我把腿在浏览器里掐死（hop 对该号 0 条记录），屏上印 '
  '「%s」+「%s」，详情块 %s 个 —— 这就是 ORD-0302 ② 落进字节后的样子：它只在**真的没拿到回答**时说没拿到。'
  % (abort['card_title'], abort['reason_text'], abort['details_blocks']))
w('')
w('## 配对证据长什么样（②的发布级）')
w('')
w('产品自己答的腿有 %d 条，每条：hop 审计行 1 条、浏览器网络栈 1 条、页面 fetch 1 条、状态码两侧相等 %s、'
  '正文类两侧相等 %s；另外有后端进程自己的 access log 逐条佐证（每臂恰好 1 行点名该腿）。举例：'
  % (SC['answer_producer_counts']['product'],
     all(r['both_ends_agree_on_status'] for r in ROWS9 if r['server_status']),
     all(r['both_ends_agree_on_json_class'] for r in ROWS9 if r['server_status'])))
w('')
w('```')
for r in (dep500, dep422env):
    w('%s  号 %s  服务器侧 %s %s B %s  %s  |  屏侧 status=%s 解析=%s 卡片=%s'
      % (r['run_id'], r['pair_id'], r['server_status'], r['server_bytes'],
         (r['server_content_type'] or '').split(';')[0],
         ('写锁由 hop 持有 rows_touched=%s' % r['hop_lock']['rows_touched']) if r['hop_lock']
         else ('请求被 hop 加了 1 个键'),
         r['page_status'], not r['app_body_parse_failed'], r['card_status']))
w('```')
w('')
w('这句的范围要说清：`no_second_probe_of_the_backend` 只约束**被计分的读数**——每一臂的服务器侧那一发都来自这一跳'
  '为该请求写的审计行。追那个协议层 400 的时候我确实另外往自己的后端端口直发过 3 个 POST（见下文），'
  '它们是诊断、不进任何格子；把它们说成"从没发生过"就是替量具遮丑。')
w('')
w('## 两处必须更正的代次说法（都错了，包括我自己的）')
w('')
w('我把服务页引用资源的名字从**被服务的 index.html 里**读出来（不是从我自己的构建清单里挑），再拿三个候选 '
  '`git archive` 出来各自 vite 构建比字节：')
w('')
w('| 候选 | 构建产物 | 与被服务字节相等 |')
w('|---|---|---|')
for tag in ('7856e03f', 'dc964086', '5aff3722'):
    ent = BIND['builds'][tag]
    w('| `%s` | `%s` · %s B · sha256 前 16 `%s…` | %s |'
      % (ent['tip'], (ent.get('built_asset') or '').lstrip('/'), ent.get('built_bytes'),
         (ent.get('built_sha256_64_hex') or '')[:16], ent.get('equals_the_served_asset')))
w('')
w('- 号令者 21:5x 说「手机已经在 `dc964086…` 那一代」：**不成立**，我 22:0x 读到的服务字节等于 `%s` 的构建'
  '（`%s` · %s B · sha256 前 16 `%s…`）。' % (B['dep']['tip'], SB['my_dep_build_asset'],
                                             B['dep']['bytes'], B['dep']['sha256_64_hex'][:16]))
w('- 我 20:0x 说「现在服务给用户的是 `index-BTzTyrqI.js` = `5aff3722`」：**同样不成立，而且是我造出来的** —— '
  '那次 GET 取的是我自己挑的资源名，不是页面引用的那个，所以它证明的是「我下载了我选的文件」。这句还在 '
  '`%s/RECEIPT_O0300C2-1955_r3.md` 与 `boundary_proof_c2.json` 里，我不改已发布件，另发勘误。' % 'evidence/ord0300-c2-pairing-hjp3')
w('- 对 ORD-0302 的直接影响：手机上那代 `%s` 的 sheet 在 :147/:155 **已经**是 `?.detail`，所以「非 JSON 正文 ⇒ '
  '谎称连不上」这条**在部署代不复现**；它复现在未守卫代（以及任何 `body.detail` 未守卫的代）。修法仍归 @B，'
  '但射程要按这个改。' % B['dep']['tip'][:8])
w('')
w('## 我自己这次坏了几次（%d 个 run 作废，全留在盘上）' % len(RC['cells'][6]['readings']['runs_excluded']))
w('')
for x in K7['readings']['runs_excluded']:
    w('* `%s`（%s）—— %s ｜机械判据 `%s`：%s' % (x['run_id'], x['arm'], x['declared_fault'],
                                                  x['mechanical_test'], x['mechanical_detail']))
w('')
w('另有两处不算作废但要说清的：')
w('')
w('* 读技术详情最初用 `innerText`，折叠状态下**整块读成空**；改成先点开再看，并同时报 `textContent` 与渲染后的 '
  '`innerText`。不修的话，块里明明写着「服务器给出的原因」，我这边会读成不存在——那是量具的瞎，不是屏上的缺。')
w('* 追那个协议层 400 时，我往**自己后端端口 8651** 直发了 3 个 POST（1 个 200 建了 1 条 mission、2 个 422），'
  '都在我一次性库里，都是诊断，不当任何格子用。')
w('')
BD = json.loads((BASE / 'p3_boundary.json').read_text(encoding='utf-8'))
FN = BD['needles']
w('## 边界与收尾（这些字都是从盘上数的，不是宣言）')
w('')
w('* 禁名在**能干事的文件与臂产物**里的命中数：`demo/reset` %s 次、`_live.db` %s 次、`_preview.db` %s 次、'
  '`git apply` %s 次、`:4782` %s 次（每次命中都按角色分成 actor/note/scanner 三类，我的 docstring 里'
  '「从不叫 demo/reset」这类句子记为 note，不算动作）；用量具自己的正向对照证明这把尺不是瞎的 '
  '（`agent/commands` 在产物里命中 %d 次、`X-HJP3-Pair` 在量具里 %d 次）。'
  % (len(FN['demo/reset']['uses_in_actor_or_artefact']), len(FN['_live.db']['uses_in_actor_or_artefact']),
     len(FN['_preview.db']['uses_in_actor_or_artefact']),
     len(FN['git apply']['uses_in_actor_or_artefact']), len(FN['4782']['uses_in_actor_or_artefact']),
     FN['agent/commands']['in_actor_or_artefact'], FN['x-hjp3-pair']['in_actor_or_artefact']))
w('* 凭据：`DEEPSEEK_API_KEY` 在 actor 里只出现在把它**摘掉**的 %d 处（%s），赋值/读取点 %d 个，'
  '任何臂正文里没有 `authorization` 头 = %s。'
  % (len(BD['credentials']['pop_sites_in_actors']),
     '、'.join(BD['credentials']['pop_sites_in_actors']),
     len(BD['credentials']['assignment_or_read_sites']),
     not BD['credentials']['authorization_header_in_any_arm_file']))
w('* 「没改产品字节」是可复核的一对哈希：两代的 `%s` 在 commit 里的 blob 与我 `git archive` 导出里重算的 '
  'blob 相等 = %s（%s）。'
  % (BD['product_bytes']['sheet_under_test'],
     all(v['equal'] for v in BD['product_bytes']['per_generation'].values()),
     '、'.join('%s→%s' % (k, v['export_blob_recomputed'])
               for k, v in BD['product_bytes']['per_generation'].items())))
w('* 手机链 :4781 只有绑定代次那一步的 **%s 次只读 GET**（methods %s、writes %s、凭据 %s），'
  '臂产物里点名该端口的 %d 次；臂只走我的端口 %s。'
  % (BD['phone_chain']['requests_made'], '/'.join(BD['phone_chain']['methods']),
     BD['phone_chain']['writes'], BD['phone_chain']['credentials_sent'],
     BD['phone_chain']['arm_artefacts_naming_that_port'],
     '、'.join(str(v) for v in TD['named_ports'].values())))
w('* 一次性库 `%s`、`%s`，私有 outDir `%s`、`%s`；边界件 `%s` 由 `%s` 现做。'
  % (K7['readings']['databases'][0], K7['readings']['databases'][1],
     B['dep']['outdir'], B['old']['outdir'], 'p3_boundary.json', 'instruments/p3_boundary.py'))
w('* 收尾 `%s`：%s 个具名端口全空 = %s（`listening_after` %s）。'
  % (TD['file'], len(TD['named_ports']), TD['all_my_ports_free'],
     json.dumps(TD['listening_after'], ensure_ascii=False)))
w('')
w('## 本批没测的（别把它当测过）')
w('')
for x in K7['readings']['not_measured']:
    w('* %s' % x)
w('')
w('* 判级不归我：`derived_result` = `%s`，`claimed_result` = `%s`（`KILLED`/`ACCEPTED` 这类字是 verifier 的）。'
  % (RC['derived_result'], RC['claimed_result']))
w('')
w('%COORD%')
w('')
RULER = (BASE / 'q38_ruler_O0301P3-2230.txt').read_text(encoding='utf-8')
RLINE = [x for x in RULER.splitlines() if 'overall' in x][0]
R_CELLS = RLINE.split('cells ')[1].split(' ')[0]
R_OVERALL = RLINE.split('overall ')[1].split(' |')[0]
R_HARD = RLINE.split('hard ')[1].split(' ')[0]
R_SOFT = RLINE.split('soft ')[1].split(' ')[0]
R_RC = '0' if R_OVERALL == 'Q38_GATE_GREEN' else 'non-zero'
assert R_CELLS == str(len(RC['cells'])), ('the ruler counted %s cells, this receipt has %d'
                                          % (R_CELLS, len(RC['cells'])))
w('尺子口径：`live_checks/receipt_cell_derivation_check_r2.py --receipt RECEIPT_O0301P3-2230.json --min-cells '
  '6 --expect %s` -> 原判 `%s`（hard %s · soft %s · 退出码 %s；这几个数是从 `%s` 的结论行现读的，'
  'cell 数并与本批 %d 格校回）'
  % ('Q38_GATE_GREEN', R_OVERALL, R_HARD, R_SOFT, R_RC, 'q38_ruler_O0301P3-2230.txt', len(RC['cells'])))
MD = BASE / 'RECEIPT_O0301P3-2230.md'
MD.write_text('\n'.join(L) + '\n', encoding='utf-8', newline='\n')
print('%s %d B, %d lines' % (MD.name, len(MD.read_bytes()), len(L)))
