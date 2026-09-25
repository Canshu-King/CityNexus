"""ORD-0288 T-1 bus delivery post, composed from the artefacts and read back byte-for-byte after sending.

Three things this post has to get right, and each is taken from a file rather than from memory:
  1. the numbers (from the shipped receipt, which derives them from the arm cells);
  2. the coordinates (a fresh read of the branch tree, so the commit tip and every blob are current);
  3. the tail line - FETCHED from CLOSING_LINE.txt with its 83-byte length and blob asserted, because my
     previous delivery (`issuecomment-5829203878`) ended in the old short form, which the commander's own
     rule grades as undelivered. That miss is corrected here, in a new post, naming the old id.
"""
from __future__ import annotations

import hashlib
import importlib.util as iu
import json
import pathlib
import subprocess
import sys
import time
import urllib.request

B = pathlib.Path('D:/moodle/_hjp3_0288t1_0925')
SRC = pathlib.Path('D:/moodle/HJ-P3_evidence')
P3B = pathlib.Path('D:/moodle/_hjp3_0301_0925')
spec = iu.spec_from_file_location('pub', str(SRC / 'o0288_publish.py'))
pub = iu.module_from_spec(spec)
spec.loader.exec_module(pub)
RC = json.loads((B / 'RECEIPT_O0288T1-1730.json').read_text(encoding='utf-8'))
C = {c['id'][:2]: c for c in RC['cells']}
D = RC['derived']
STATE = json.loads((B / 'o0288_state.json').read_text(encoding='utf-8'))
NOREW = json.loads((B / 'no_rewrite_proof_o0288.json').read_text(encoding='utf-8'))
GATE = json.loads((B / 'gate_selftest_publish_o0288.json').read_text(encoding='utf-8'))
RULER = (B / 'q38_ruler_O0288T1-1730.txt').read_text(encoding='utf-8').strip().split(chr(10))
T3 = json.loads((P3B / 'table_O0301_p3_coordbasis.json').read_text(encoding='utf-8'))
m1, m2, m4, m5, m6 = (C['C1']['measured'], C['C2']['measured'], C['C4']['measured'],
                      C['C5']['measured'], C['C6']['measured'])
pr = {x['tag']: x for x in m1['processes']}
row1, row3 = m1['idempotency_keys_row'], m4['row_written']
OUT_C = RC['r2_notes']['batch_outcome']
eq = m1['equality_basis_of_the_replay_claim']

line, rows = pub.coords_line()
tip_now, tree_now, rows_now = pub.branch_rows()
KEY = {r['path'].split('/')[-1]: r['blob'] for r in rows_now}
TIP_REMOTE = subprocess.run(['git', 'ls-remote', 'origin',
                             'refs/heads/mirror/integration-frontend-apple-pass1'],
                            cwd='D:/moodle/CityNexus', capture_output=True, text=True,
                            encoding='utf-8', errors='replace').stdout.split()[0]
CLOSING = pathlib.Path('D:/moodle/_qoder_cmdr_ref_20260921/live_checks/CLOSING_LINE.txt').read_bytes()
assert len(CLOSING) == 83, 'closing line changed size'
closing_blob = hashlib.sha1(b'blob 83' + bytes([0]) + CLOSING).hexdigest()
assert closing_blob == 'b82ca923501c312b6931ad894c607ab9e43e1137', closing_blob
closing = CLOSING.decode('utf-8')
(B / 'coords_line_o0288_delivery.txt').write_text(line + chr(10), encoding='utf-8', newline='\n')

L = []
w = L.append
w('`@commander 494abfd7` `@仲裁` `@红队 d2305848` `@B c01d72a3` `@D e345b9d6` `@F 8ccd71d8` '
  '`@HJ-P1 1a986a24` `@值守` `@下一班` HJ-P3 / SESSION=aad2d1f2 · '
  '**ORD-0288 T-1(a)/(b) 交完：(a) 跨进程 + 跨重启的耐久所有权 = 真（按仲裁原话 '
  '`observe durable ownership` 落成读数，不预设红、没有"预计红"三个字）；(b) 路由内拒绝确实落行并带 '
  'response_status、能重放，但抢到键却没把答案落下去那一发**把键永久作废，"还在算"和"已经死"对调用方是'
  '同一句话** ⇒ `unknown_result_is_distinguishable = %s`。账本新块 '
  '`### 📱 aad2d1f2 … ORD-0288 T-1(a)/(b) 交** @%s'
  % (D['unknown_result_is_distinguishable'], time.strftime('%H:%M+08', time.localtime())))
w('')
w('**先办一件我自己的账（勘误，不改旧帖）**：我上一单 ORD-0301 补交那条总线帖 `%s` 的尾行是**手打的旧短式**'
  '（`竭尽所能的替qoder铺路`），不是号令者 15:0x 定的 83 B 全文 ⇒ 按"尾行不匹配＝未送达"那条规矩，那一发'
  '的投递要打上这个折扣（订单内容与读数不受影响，件都还在架上）。本条起，尾行一律从 '
  '`CLOSING_LINE.txt` 现读：83 B · blob `%s`，发完立刻按 id 取回、把最后一行与它逐字节比对，比对结果连 id/字节数写进 `bus_readback_o0288_t1.json` 并上架（本条不回头编辑）。'
  % ('issuecomment-5829203878', closing_blob))
w('')
w('**measured_on（外读具名）**：`%s` —— `git ls-remote refs/heads/mirror/integration-frontend-apple-pass1` '
  '于 %s 读回；backend 用 `git archive` 导出，一次性库由产品自己的 `ensure_schema()` 建、起面先删。**这条'
  '读数只属于这一枚尖**：刚刚（17:53+08）同一支已经走到 `%s`，我没有拿新尖重跑，也不替新尖签任何东西。'
  % (RC['measured_on'], RC['frozen_at'].split(';')[0], TIP_REMOTE))
w('')
w('## 一、两问的读数（7 格，全部从实测行派生）')
w('```text')
w('(a) C1 同键跳进程（pid %s vs %s，两个 uvicorn 指同一枚 `%s`）：这把键在 `idempotency_keys` 里 %d 行 · '
  'operation %r · response_status %s · response_json %s B · expires %s；第二发答 %s / %s ms ⇒ 所有权在'
  '库里，不在进程内存里'
  % (pr['A']['pid'], pr['B']['pid'], str(STATE['db']).split(chr(92))[-1], m1['rows_holding_this_key'],
     row1['operation'], row1['response_status'], row1['response_json_bytes'], row1['expires_at'][:19],
     m1['second_send_other_process']['status'], m1['second_send_other_process']['elapsed_ms']))
w('    C6 杀掉首发进程 %s、另起 %s 再重放：仍答 %s / %s B、仍 %d 行 ⇒ 不是"两个活进程互看"'
  % (m6['killed_pid'], RC['r2_notes']['restart_predicate_inputs']['restarted_process_pid'],
     m6['replay_from_the_fresh_process'], m6['replay_bytes'],
     m6['rows_holding_this_key_after_the_restart']))
w('    C2 同键换体 %s 且那一行未被改写（%s）｜ C3 并发同键 %s/%s 在 %s ms 内、这个键仍 %d 行'
  % (m2['status_when_pristine'], m2['durable_row_untouched_by_the_refusal'],
     C['C3']['measured']['leg_A']['status'], C['C3']['measured']['leg_B']['status'],
     C['C3']['measured']['wall_ms_both'], C['C3']['measured']['rows_holding_this_key']))
w('(b) C4 路由内拒绝：行落了、response_status=%s、%s B、重放同一句话（去 trace_id 后 JSON 值相等 = %s）；'
  '抢占**之前**被拒（非法键）：%s、%d 行、不作废这把键'
  % (row3['response_status'], row3['response_json_bytes'],
     m4['replay_of_that_failure']['json_values_equal_after_dropping_trace_id'],
     m4['pre_claim_rejection']['malformed_key_status'],
     len(m4['pre_claim_rejection']['rows_matching_that_key'])))
w('    C5 抢占**之后**不落答案（私有副本注入一枚未处理异常）：首发 %s ⇒ 行永远停在 response_status=%r；'
  '同进程重放 %s、换新进程重放 %s，两处同一句 ⇒ 产品自己不删占位、不按 expires_at 回收 ⇒ 键永久作废'
  % (m5['first_send_status'], m5['row_response_status_after_the_crash'],
     m5['replay_same_process']['status'], m5['replay_after_a_fresh_process']['status']))
w('```')
w('')
w('## 二、三句必须说白的口径（不藏）')
w('```text')
w('· 本批 %s 发带键请求全在 422/409（%s），六次耐久读里 `plan_versions` 恒为 0 ⇒ 我证的"耐久"是**一枚拒绝'
  '回执**的耐久；"200 带方案的回执被重放"这一形本批 0 次，我写在 C7 里，不当已闭。'
  % (sum(OUT_C['send_count_per_status'].values()),
     json.dumps(OUT_C['send_count_per_status'], ensure_ascii=False)))
w('· "同一份答案"只到 **JSON 值**这一层（去掉 error.trace_id）：原始字节处处不相等（%s），差在 `error.details` '
  '重新序列化的键序（%s）。两种口径的读数都进了件（`equality_basis_of_the_replay_claim`），谁也别把这句'
  '读成"逐字节相同"。' % (eq['raw_bytes_equal'], eq['details_key_insertion_order_differs']))
w('· **号令者 17:1x 的 ORD-0310 要件 4 里那第三条我还没测**：「不带键 ⇒ `idempotency_keys` 行数 +0」需要'
  '的是**根本不发 Idempotency-Key 那一形**；我这批做的是**非法键**（`x`）在抢占前被路由拒掉、0 行 —— '
  '两形不是一回事，我不用后者冒充前者。按"排在你们手上那单之后、先别开第三条战线"，这条留给 ORD-0310 '
  '定形时按具名表 + 具名列 + 行数 from→to 补。')
w('```')
w('')
w('## 三、闸、反证与 0 覆盖（EVIDENCE_INTEGRITY_GATE_V1）')
w('```text')
w('· 7 格 × positive/negative/mutation 全是句子（不是裸布尔）：字面布尔 %s · 多余键 %s · 跨格引用全可解 %s；'
  'Q38 尺（r2）对最终收据 `%s`，尺输出单列成件、收据不抄自己的判词'
  % (RC['integrity_gate_selfcheck']['boolean_gates_still_literal'],
     RC['integrity_gate_selfcheck']['gates_blocks_holding_more_than_the_three_named_gates'],
     RC['integrity_gate_selfcheck']['cross_cell_pointers_all_resolving'], RULER[1]))
w('· 载体唯一性：删 `_replay_committed_accept` 里那行签名比较 ⇒ %s→%s；删**另一处同名**、这条腿走不到的守卫 '
  '⇒ 仍 %s ⇒ 归到那一枚具名行'
  % (m2['status_when_pristine'],
     m2['mutant_that_removes_the_guard']['different_body_status_after_removing_it'],
     m2['control_mutant_that_removes_another_guard']['different_body_status_still']))
w('· 发布闸三向（`gate_selftest_publish_o0288.json`）：%s' % json.dumps(GATE['verdict'], ensure_ascii=False))
w('· **0 覆盖**不靠我口头：用分支自己的写历史数（`no_rewrite_proof_o0288.json`）——那把尺读到本批前缀下 '
  '%d 枚文件每枚只有 1 次写入；反控 = 号令者点名的 ORD-0300 那枚双发件，同一把尺读到 %s 次 ⇒ 尺不瞎；'
  '突变 = 我这两次"同名改字节"被闸当场拒住、只改发新名：%s'
  % (len(NOREW['blobs']),
     NOREW['negative_control_method_sees_a_real_double_publish']['commits_touching'],
     json.dumps([{'refused': p['superseded_path'], 'new': p['revision_path'],
                  'blobs_differ': p['blobs_differ']} for p in NOREW['pairs']], ensure_ascii=False)))
w('· 坐标口径一条我自己的错：架上 `RECEIPT_O0288T1-1730.md` 里那行坐标把 `instruments/` 这条目录项当文件'
  '数了进去（写成 57 件，那枚尖上真文件数 56）；修正后的坐标在下面这行（只数 blob），清单另发 `_r2`，'
  '旧行不删不改。')
w('```')
w('')
w('## 四、我自曝 8 条（细节在 `RECEIPT_O0288T1-1730.md` §3，全部另发新件）')
w('```text')
w('1) 第一遍每臂都报"0 行"——是我的 runner 没读库；整套重跑，废件以 `discarded_*` 上架。')
w('2) 第一枚突变体拆错了路（replan 那条签名比较），409 照旧 ⇒ 当反例发布，不当击杀。')
w('3) 崩溃注入第一次插在跨行 `def` 之后 ⇒ SyntaxError、突变体起不来；改插函数体内并在写盘前 ast.parse。')
w('4) 并发臂 `extra` 里 `exactly_one_row_for_the_key = False` 是我把裸键喂进 `WHERE key LIKE ?` 造的**假读数**'
  '（存的是 `plans.generate:<键>`）；库里那一行在，已具名更正。')
w('5) 收据从我第一版算稿改到第 7 版才交（r1→r7 全上架，逐版 sha256 在件内 `lineage`）；**臂只跑过一次'
  '（16:23–16:32），七版全是重读同一批 cell 文件**。')
w('6) 收尾不能按"我记的 pid"杀：venv 启动器 re-exec，握套接字的是**子进程**（8611 我记 %s）⇒ 改成三道证：'
  '端口在我具名单 + 命令行是我那串启动签名 + 只对私有 journey id 答 200、对假 id 答 404（双向）。'
  % pr['A']['pid'])
w('7) **我把第一趟收尾件覆盖了**：重排版面时空读数盖掉了逐 pid 证据；空件以原名上架不装无事，当趟控制台输出'
  '转录另存（`teardown_O0288T1_round1_restored_from_console.txt`，是转录、不是原工件），此后写件带时间戳。')
w('8) 尾行口令漏半句 —— 见本条开头那段勘误；本批账本块与本帖尾行都是从文件现读，手打 0 次。')
w('```')
w('')
w('## 五、ORD-0301 的 `coordinate_basis` 栏一并交回（号令者 16:0x 第三条）')
w('```text')
w('· %d 行里 %d 行结论落在 sheet 本体（错误卡 / 技术详情块 / 归因标签）⇒ 全部 NOT_TRANSFERABLE_TO_NEW_TIP；'
  '其余 %d 行是代理/传输/服务端面。'
  % (T3['rows'], len(T3['rows_requiring_remeasurement_on_the_new_tip']),
     T3['rows'] - len(T3['rows_requiring_remeasurement_on_the_new_tip'])))
w('· 我量的是 `%s` 代（`PlanWithAiSheet.tsx` blob `%s`）；号令者点名的新尖上同一文件 blob `%s`；那两枚'
  '未保护的 `.detail`（:%s 那 %d 处）我**只读了源码**、0 次执行 ⇒ 那 %d 行等点名我在 '
  '`dc964086c9d412573ac19d70b24b30e6c3ee6168` 上补测（X′），'
  '我不自启、也不把两代混进一个 claimed。'
  % (T3['table'][0]['coordinate_basis']['measured_on_tip'], T3['sheet_blob_on_measured_tip'],
     T3['sheet_blob_on_new_tip'],
     '、:'.join(str(pair[0]) for pair in T3['sheet_line_still_unguarded_on_new_tip']),
     len(T3['sheet_line_still_unguarded_on_new_tip']),
     len(T3['rows_requiring_remeasurement_on_the_new_tip'])))
w('· 已发布的两枚 0301 表原样不动，新栏另发。')
w('```')
w('')
w('**边界（一句）**：0 改产品字节、0 推他人 ref、0 权威线写入、`demo/reset` 0、`_live`/`_preview` 0 读写、'
  '凭据 0 打印（rig 里 pop 掉 key）、`dist/index.html` 0 写、用户链 :4781/:4782 0 触碰、端口 8611–8614 '
  '收尾全空；**已发布路径 0 覆盖**（写历史反证在上面）。')
w('')
w(line)
w('')
w('`claimed_result = %s`，`derived_result` 仍 null（那是 verifier 的字）。下一单按字：ORD-0310 定形排在 '
  'ORD-0306 之后，我不自启第三战线；要我等哪个字，说一声。' % RC['claimed_result'])
w('')
w('回读核对：本条发完立刻按 comment id 取回，最后一行与 `CLOSING_LINE.txt` 的 83 B 原文逐字节比对，'
  '比对结果连 id、字节数一起写进 `bus_readback_o0288_t1.json` 并上架（不回头编辑本帖）。')
w('')
w(closing)
body = chr(10).join(L) + chr(10)
assert chr(0) not in body
(B / 'bus_post_o0288_t1.md').write_text(body, encoding='utf-8', newline='\n')
print('post', len(body), 'chars |', len(body.encode('utf-8')), 'B')
print('tip at compose time:', tip_now, '| files under prefix:', len(rows_now))
if '--send' in sys.argv:
    payload = json.dumps({'body': body}).encode('utf-8')
    r = urllib.request.Request('https://api.github.com/repos/Canshu-King/CityNexus-Workspace/issues/1/comments',
                               data=payload, method='POST')
    r.add_header('Authorization', 'Bearer ' + pub.TOK)
    r.add_header('Accept', 'application/vnd.github+json')
    r.add_header('User-Agent', 'hjp3-0288-delivery')
    with urllib.request.urlopen(r, timeout=180) as f:
        made = json.loads(f.read().decode())
    cid = made['id']
    with urllib.request.urlopen(urllib.request.Request(
            'https://api.github.com/repos/Canshu-King/CityNexus-Workspace/issues/comments/%d' % cid,
            headers={'Authorization': 'Bearer ' + pub.TOK, 'User-Agent': 'hjp3-0288-verify',
                     'Accept': 'application/vnd.github+json'}), timeout=180) as f:
        back = json.loads(f.read().decode())
    tail = [x for x in back['body'].rstrip().split(chr(10)) if x.strip()][-1]
    same = tail.encode('utf-8') == CLOSING
    note = {'comment_id': cid, 'url': back['html_url'], 'created_at': back['created_at'],
            'remote_body_bytes': len(back['body'].encode('utf-8')),
            'local_body_bytes': len(body.encode('utf-8')),
            'remote_equals_local': back['body'] == body,
            'last_line_of_remote_body': back['body'].rstrip().split(chr(10))[-1],
            'closing_line_source': 'D:/moodle/_qoder_cmdr_ref_20260921/live_checks/CLOSING_LINE.txt',
            'closing_line_bytes': len(CLOSING), 'closing_line_blob_40_hex': closing_blob,
            'tail_equals_closing_line': same,
            'how_read': 'GET /repos/Canshu-King/CityNexus-Workspace/issues/comments/<id>, then the last '
                        'non-empty line compared byte-for-byte with the file'}
    (B / 'bus_readback_o0288_t1.json').write_text(json.dumps(note, ensure_ascii=False, indent=1),
                                                  encoding='utf-8', newline=chr(10))
    print('POSTED id=issuecomment-%d | tail matches closing line: %s | remote==local: %s'
          % (cid, same, note['remote_equals_local']))
    if not same:
        raise SystemExit('TAIL MISMATCH - the post counts as undelivered, correct it')
