"""ORD-0288 T-1 ledger block, composed from the artefacts - not one number typed from memory.

Everything it quotes is read back at build time from: the shipped receipt, the boundary proof, the
publication gate's own control, the no-rewrite proof taken from the branch's commit history, the manifest
read from the branch tree, the coordinate line read from the branch, and the ORD-0301 `coordinate_basis`
table. The tail line is FETCHED from CLOSING_LINE.txt (83 B, blob asserted), never typed.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import re
import time
import urllib.request

TOK = pathlib.Path('D:/moodle/_qoder_recovery_20260919/.api_tok_20260920').read_text(
    encoding='utf-8').strip()


def gh(path):
    r = urllib.request.Request('https://api.github.com/repos/Canshu-King/CityNexus' + path)
    r.add_header('Authorization', 'Bearer ' + TOK)
    r.add_header('Accept', 'application/vnd.github+json')
    r.add_header('User-Agent', 'hjp3-0288-ledger')
    with urllib.request.urlopen(r, timeout=180) as f:
        return json.loads(f.read().decode())


def read_tree_at(sha):
    """Count real files (blobs only) under my prefix at a named commit."""
    tree = gh('/git/trees/' + sha + '?recursive=1')['tree']
    mine = [e for e in tree if e['path'].startswith(PREFIX + '/') and e.get('size') is not None]
    return sha, len(mine), sum(e['size'] for e in mine)


PREFIX = 'evidence/ord0288-t1-durable-ownership-hjp3'

B = pathlib.Path('D:/moodle/_hjp3_0288t1_0925')
SRC = pathlib.Path('D:/moodle/HJ-P3_evidence')
P3B = pathlib.Path('D:/moodle/_hjp3_0301_0925')
RC = json.loads((B / 'RECEIPT_O0288T1-1730.json').read_text(encoding='utf-8'))
MD = (B / 'RECEIPT_O0288T1-1730.md').read_text(encoding='utf-8')
_mc = re.search(r'读回 commit 尖 `([0-9a-f]{40})`.*?共 ([\d,]+) 件（合计 ([\d,]+) B）', MD)
assert _mc, 'the published supplement has no parseable coordinate line'
TIP_NAMED_IN_MD, COORD_COUNT_IN_MD, COORD_BYTES_IN_MD = _mc.group(1), _mc.group(2), _mc.group(3)
C = {c['id'][:2]: c for c in RC['cells']}
D = RC['derived']
STATE = json.loads((B / 'o0288_state.json').read_text(encoding='utf-8'))
BOUND = json.loads((B / 'boundary_proof_O0288T1.json').read_text(encoding='utf-8'))
GATE = json.loads((B / 'gate_selftest_publish_o0288.json').read_text(encoding='utf-8'))
NOREW = json.loads((B / 'no_rewrite_proof_o0288.json').read_text(encoding='utf-8'))
MAN = json.loads((B / 'evidence_manifest_full40_o0288_r2.json').read_text(encoding='utf-8'))
COORD = (B / 'coords_line_o0288_delivery.txt').read_text(encoding='utf-8').strip()
RULER = (B / 'q38_ruler_O0288T1-1730.txt').read_text(encoding='utf-8').strip().split(chr(10))
T3 = json.loads((P3B / 'table_O0301_p3_coordbasis.json').read_text(encoding='utf-8'))
TIPS = sorted({r['coordinate_basis']['measured_on_tip'] for r in T3['table']})
assert len(TIPS) == 1, 'the range table spans more than one tip: %s' % TIPS
TIP301 = TIPS[0]
OUT_C = RC['r2_notes']['batch_outcome']
TD_NAME = re.search(r'本趟收尾件 = (teardown_O0288T1_[0-9]+\.json)', MD).group(1)
TD = json.loads((B / TD_NAME).read_text(encoding='utf-8'))
CLOSING = pathlib.Path('D:/moodle/_qoder_cmdr_ref_20260921/live_checks/CLOSING_LINE.txt').read_bytes()
assert len(CLOSING) == 83, 'closing line authority changed size'
closing_blob = hashlib.sha1(b'blob 83' + bytes([0]) + CLOSING).hexdigest()
assert closing_blob == 'b82ca923501c312b6931ad894c607ab9e43e1137', closing_blob
closing = CLOSING.decode('utf-8')
KEY = {x['path'].split('/')[-1]: x['blob_sha1_40_hex'] for x in MAN['files']}
m1, m2, m3, m4, m5, m6 = (C['C1']['measured'], C['C2']['measured'], C['C3']['measured'],
                          C['C4']['measured'], C['C5']['measured'], C['C6']['measured'])
pr = {x['tag']: x for x in m1['processes']}
row1, row3 = m1['idempotency_keys_row'], m4['row_written']
eq = m1['equality_basis_of_the_replay_claim']
L = []
w = L.append

w('### 📱 aad2d1f2 (SESSION=aad2d1f2) P3 · **ORD-0288 T-1(a)/(b) 交：(a) 在尖 `%s` 上跨进程/跨重启的耐久所有权 '
  '＝真（按仲裁原话 `observe durable ownership` 落成读数，不预设红）；(b) 路由内拒绝确实落行且带 '
  'response_status、能重放，但**抢到键却没把答案落下去那一发把键永久作废，"还在算"和"已经死"对调用方是'
  '同一句话** ⇒ unknown result 不可判 = %s。另附 ORD-0301 的 `coordinate_basis` 栏：%d 行里 %d 行结论落在 '
  'sheet 本体，全部标不可转移** @%s'
  % (RC['measured_on'], D['unknown_result_is_distinguishable'], T3['rows'],
     len(T3['rows_requiring_remeasurement_on_the_new_tip']),
     time.strftime('%Y-%m-%dT%H:%M', time.localtime()) + '+08'))
w('')
w('**两问的读数**（一次性库 `%s` · 两个 uvicorn 指同一文件 = %s · journey `%s` · measured_on `%s` · '
  '`derived_result` = %s，那是 verifier 的字）'
  % (str(STATE['db']).split(chr(92))[-1], STATE['both_processes_share_one_file'], m1['journey_id'],
     RC['measured_on'], json.dumps(RC['derived_result'])))
w('```text')
w('(a) C1 同键跳进程：这把键在库里 %d 行 · operation %r · response_status %s · response_json %s B · '
  'expires %s；第二发走 %s（pid %s vs %s）答 %s / %s ms ⇒ 所有权在数据库里，不在进程内存里'
  % (m1['rows_holding_this_key'], row1['operation'], row1['response_status'],
     row1['response_json_bytes'], row1['expires_at'][:19], pr['B']['port'], pr['B']['pid'],
     pr['A']['pid'], m1['second_send_other_process']['status'],
     m1['second_send_other_process']['elapsed_ms']))
w('    C6 杀掉写它那个进程、另起一个再重放：仍答 %s / %s B、仍 %d 行 ⇒ 不是"两个活进程互看"'
  % (m6['replay_from_the_fresh_process'], m6['replay_bytes'],
     m6['rows_holding_this_key_after_the_restart']))
w('    C2 同键换体：%s（那一行未被改写 = %s）｜ C3 并发同键：%s/%s 在 %s ms 内、这个键仍 %d 行、'
  '全库 plan_versions %s'
  % (m2['status_when_pristine'], m2['durable_row_untouched_by_the_refusal'], m3['leg_A']['status'],
     m3['leg_B']['status'], m3['wall_ms_both'], m3['rows_holding_this_key'], m3['plan_versions_total']))
w('(b) C4 路由内拒绝：落了行、response_status=%s、%s B，重放拿同一句话（去 trace_id 后 JSON 值相等 = %s）；'
  '抢占**之前**被拒（非法键）：%s、%d 行、不作废这把键（之后一把正常键仍能跑 = %s）'
  % (row3['response_status'], row3['response_json_bytes'],
     m4['replay_of_that_failure']['json_values_equal_after_dropping_trace_id'],
     m4['pre_claim_rejection']['malformed_key_status'],
     len(m4['pre_claim_rejection']['rows_matching_that_key']),
     m4['pre_claim_rejection']['a_later_valid_send_still_works']))
w('    C5 抢占**之后**没落答案（私有副本注入一枚未处理异常）：首发 %s ⇒ 行永远停在 response_status=%r；'
  '同进程重放 %s、换新进程重放 %s，两处同一句话 ⇒ unknown_result_is_distinguishable = %s'
  % (m5['first_send_status'], m5['row_response_status_after_the_crash'],
     m5['replay_same_process']['status'], m5['replay_after_a_fresh_process']['status'],
     D['unknown_result_is_distinguishable']))
w('```')
w('')
w('**两句不藏（射程与比较口径）**')
w('```text')
w('· 本批 %s 发带键请求全在 422/409（%s），六次耐久读里 `plan_versions` 都是 %s ⇒ 我量到的"耐久"是一枚'
  '**拒绝回执**的耐久；200 带方案的回执重放本批 0 次（C7 具名，不当已闭）'
  % (sum(OUT_C['send_count_per_status'].values()),
     json.dumps(OUT_C['send_count_per_status'], ensure_ascii=False),
     sorted(set(OUT_C['plan_versions_rows_per_arm_durable_read'].values()))))
w('· "同一份答案"判的是**去掉 error.trace_id 之后的 JSON 值**；原始字节处处不相等（%s），差在 '
  '`error.details` 重新序列化的键序（%s）⇒ 这句不许被读成"逐字节相同"；两种口径都写进件里 '
  '(`equality_basis_of_the_replay_claim`)'
  % (eq['raw_bytes_equal'], eq['details_key_insertion_order_differs']))
w('```')
w('')
w('**闸与反证（EVIDENCE_INTEGRITY_GATE_V1）**')
w('```text')
w('· 7 格 × positive/negative/mutation 全是句子：字面布尔 %s · 多余键 %s · 跨格引用全可解 = %s'
  % (RC['integrity_gate_selfcheck']['boolean_gates_still_literal'],
     RC['integrity_gate_selfcheck']['gates_blocks_holding_more_than_the_three_named_gates'],
     RC['integrity_gate_selfcheck']['cross_cell_pointers_all_resolving']))
w('· 载体唯一性：删 `_replay_committed_accept` 里那行签名比较 ⇒ %s→%s；删**另一处同名**、这条腿走不到的守卫 '
  '⇒ 仍 %s ⇒ 归到那一枚具名行'
  % (m2['status_when_pristine'],
     m2['mutant_that_removes_the_guard']['different_body_status_after_removing_it'],
     m2['control_mutant_that_removes_another_guard']['different_body_status_still']))
w('· 发布闸三向（合成件 `gate_selftest_publish_o0288.json` blob %s）：%s'
  % (KEY.get('gate_selftest_publish_o0288.json', 'NOT_IN_MANIFEST'),
     json.dumps(GATE['verdict'], ensure_ascii=False)))
w('· **0 覆盖**用分支自己的写历史证（`no_rewrite_proof_o0288.json` blob %s）：本批前缀下 %d 枚文件'
  '每枚只有 1 次写入；反控 = 号令者点名的 ORD-0300 那枚双发件，同一把尺读到 %s 次 ⇒ 这把尺不是瞎的；'
  '突变 = 我这两次"同名改字节"被闸当场拒住、改发新名：%s'
  % (KEY.get('no_rewrite_proof_o0288.json', 'NOT_IN_MANIFEST'),
     len(NOREW['blobs']),
     NOREW['negative_control_method_sees_a_real_double_publish']['commits_touching'],
     json.dumps([{'refused': p['superseded_path'], 'writes': p['superseded_writes'],
                  'new_name': p['revision_path'], 'writes_new': p['revision_writes'],
                  'blobs_differ': p['blobs_differ']} for p in NOREW['pairs']], ensure_ascii=False)))
w('· Q38 尺（r2）对最终收据：`%s` ｜ `%s`；输出单列成件（收据不抄自己的判词）'
  % (RULER[1], RULER[-1]))
w('```')
w('')
w('**ORD-0301 的 `coordinate_basis` 栏（号令者 16:0x 第三条）**')
w('```text')
w('· %d 行里 %d 行结论落在 sheet 本体（错误卡 / 技术详情块 / 归因标签）⇒ 全部 NOT_TRANSFERABLE_TO_NEW_TIP；'
  '其余 %d 行是代理/传输/服务端面，不依赖那枚文件'
  % (T3['rows'], len(T3['rows_requiring_remeasurement_on_the_new_tip']),
     T3['rows'] - len(T3['rows_requiring_remeasurement_on_the_new_tip'])))
w('· 我量的是 `%s` 代：`PlanWithAiSheet.tsx` blob `%s`；号令者点名的新尖上同一文件 blob `%s` ⇒ 两代不混进'
  '一个 claimed'
  % (TIP301, T3['sheet_blob_on_measured_tip'], T3['sheet_blob_on_new_tip']))
w('· 新尖上 :%s 那 %d 处未保护的 `.detail`（原文 %s）我**只读了源码**：0 次执行、0 界面读数；要靠 sheet '
  '本体下结论的行，等号令者点名我在 `dc964086c9d412573ac19d70b24b30e6c3ee6168` 上补测（X′）'
  % ('、:'.join(str(pair[0]) for pair in T3['sheet_line_still_unguarded_on_new_tip']),
     len(T3['sheet_line_still_unguarded_on_new_tip']),
     json.dumps(T3['sheet_line_still_unguarded_on_new_tip'][0][1], ensure_ascii=False)[:78]))
w('· 已发布的两枚 0301 表原样不动，新栏另发（`table_O0301_p3_coordbasis.json`）')
w('```')
w('')
w('**我自曝 8 条**（逐条细节在 `RECEIPT_O0288T1-1730.md` §3，全部另发新件）：')
w('1) 第一遍每臂都报"0 行"——是我的 runner 没读库，整套重跑；废件以 `discarded_*` 上架，本件没有一个数字来自它们。')
w('2) 第一枚突变体拆错了路（replan 那条签名比较），409 照旧 ⇒ 当反例发布，不当击杀。')
w('3) 崩溃注入第一次插在跨行 `def` 之后 ⇒ SyntaxError、突变体起不来（端口拒连才暴露）；改插函数体内并在写盘前 ast.parse。')
w('4) 并发臂 `extra` 里那枚 `exactly_one_row_for_the_key = False` 是我把裸键喂进 `WHERE key LIKE ?` 造的'
  '**假读数**（存的是 `plans.generate:<键>`，那条查询 0 行）；库里那一行在，已连查询语句具名更正。')
w('5) 收据从我第一版算稿改到第 7 版才交（r1→r7 全部上架，逐版 sha256 在件内 `lineage`）；'
  '**臂只跑过一次（16:23–16:32），七版全是重读同一批 cell 文件**，没有一个数字因改版而变。')
w('6) 收尾不能按"我记的 pid"杀：venv 启动器 re-exec，真正握套接字的是**子进程**（8611 我记 %s）。'
  '改成三道证才动手：端口在我具名单 + 命令行是我那串启动签名 + 只对我私有库里那一枚 journey id 答 200、'
  '对一枚假 id 答 404（双向）。' % pr['A']['pid'])
w('7) **我把第一趟收尾件覆盖了**：重排版面时空读数盖掉了逐 pid 证据。那枚空件以原名上架不装无事 '
  '(`teardown_O0288T1_round2_overwrote_round1.json`)，当趟控制台输出转录另存 '
  '(`teardown_O0288T1_round1_restored_from_console.txt`，**是转录、不是原工件、也不是新测量**)，'
  '此后写件一律带时间戳（本趟 `%s`）。' % TD_NAME)
w('8) **尾行口令我上一班漏了半句**：ORD-0301 补交那条总线帖仍按旧短式收尾 ⇒ 按号令者规矩"尾行不匹配＝'
  '未送达"，勘误以新帖走、不改旧帖；本批两处尾行都从 `CLOSING_LINE.txt` 现读（83 B · blob %s），手打 0 次。'
  % closing_blob)
w('')
# The coordinate line inside the published supplement was written by an earlier count that treated the
# `instruments/` DIRECTORY entry as a file. Recomputed here against the very tip that line names.
mtip, mfiles, mbytes = read_tree_at(TIP_NAMED_IN_MD)
w('**还有一条口径账**：架上 `RECEIPT_O0288T1-1730.md` 里那行坐标写"共 %s 件（合计 %s B）"，'
  '它点名尖 `%s` 上真正的文件数是 %d（合计 %s B）⇒ 差的那 1 枚是把 `instruments/` 这条**目录项**当文件数了'
  '进去。修正后的坐标以本块末尾这行为准（只数 blob），清单另发 `_r2` 一枚；旧行不删不改。'
  % (COORD_COUNT_IN_MD, COORD_BYTES_IN_MD, TIP_NAMED_IN_MD, mfiles, format(mbytes, ',')))
assert int(COORD_COUNT_IN_MD.replace(',', '')) - mfiles == 1, (
    'the off-by-one story does not match the branch: %s vs %d' % (COORD_COUNT_IN_MD, mfiles))
assert int(COORD_BYTES_IN_MD.replace(',', '')) == mbytes, 'byte total disagrees'
w('· 顺带一句：`gate_refusal_recorded_o0288.json`（blob %s）是在两次改名落架**之前**跑的，它里面两条事件'
  '写着 `NOT COMPARABLE`、`branch_blob_at_tip` 还是 null —— 原因不是"架上那枚不存在"，是我那台记录器'
  '拿不带前缀的路径去查带前缀的表（键不匹配）。旧件不删不改，这条账由上面那枚写历史件接管。'
  % KEY.get('gate_refusal_recorded_o0288.json', 'NOT_IN_MANIFEST'))
w('')
w('**边界**：一次性库由产品 `ensure_schema()` 建、起面先删；`_live.db` / `_preview.db` / `demo/reset` / '
  '`git apply` / 产品默认库名的**真正调用行 = %s**（另有 %d 处只是我否认句里提到名字、%d 处是扫描器自身，'
  '逐行原文落 `boundary_proof_O0288T1.json`；coverage %s…）；在服 `dist/index.html` 0 写（sha256 %s · '
  'mtime %s · 引用 %s）；用户链 4781/4782 0 触碰（进程创建时间 %s）；凭据 0 打印（rig 里 pop 掉 key = %s，'
  'sk 形状串 %s）；产品字节 0 改动；端口 8611–8614 收尾读数 %s（全空 = %s）；'
  '**已发布路径 0 覆盖**（每枚 1 次写入，见上面的写历史反证）。'
  % (json.dumps({k: v['lines_that_actually_use_it'] for k, v in BOUND['negative_scan'].items()},
                ensure_ascii=False),
     sum(v['lines_that_only_name_it_in_a_denial_sentence'] for v in BOUND['negative_scan'].values()),
     sum(v['lines_excluded_as_self_reference'] for v in BOUND['negative_scan'].values()),
     BOUND['coverage'][:78], BOUND['live_preview_index']['sha256_full_64_hex'],
     BOUND['live_preview_index']['mtime_local'],
     ','.join(BOUND['live_preview_index']['asset_referenced']),
     ', '.join(x['port'] + '=' + x['process_created'][:19] for x in BOUND['user_chain_listeners_untouched']),
     BOUND['credential_handling']['DEEPSEEK_API_KEY_popped_in_rig'],
     BOUND['credential_handling']['sk_shaped_strings_in_my_files'],
     json.dumps(TD['listening_after'], ensure_ascii=False), TD['all_my_ports_free']))
w('')
w(COORD)
w('')
w('**状态**：T-1(a)/(b) 交完。一句话结论：**跨进程、跨重启的所有权是真的；抢到却没落答案的那把键永久作废'
  '且不可判（unknown_result_is_distinguishable = %s）**。`claimed_result = %s`，`derived_result` 仍 null。'
  '手上没有别的活；等号令者点名 ORD-0301 那 %d 行在 `dc964086c9d412573ac19d70b24b30e6c3ee6168` 上补测。'
  % (D['unknown_result_is_distinguishable'], RC['claimed_result'],
     len(T3['rows_requiring_remeasurement_on_the_new_tip'])))
w('')
w(closing)
out = chr(10).join(L) + chr(10)
assert chr(0) not in out, 'NUL byte in the block'
raw = out.encode('utf-8')
(SRC / 'block_0288_t1.md').write_bytes(raw)
back = (SRC / 'block_0288_t1.md').read_bytes()
print('block', len(L), 'lines |', len(back), 'B | CRLF', b'\r' in back,
      '| tail is the fetched closing line:', back.decode('utf-8').rstrip().endswith(closing),
      '| bytes match:', back == raw)
print('sha256', hashlib.sha256(back).hexdigest())
