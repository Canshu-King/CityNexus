"""ORD-0288 T-1 shipping pass: teardown with ownership proof, boundary proof, ruler, human receipt.

The teardown is the delicate part, so it is not done by "the pid I wrote down": the venv launcher
re-execs, so the process that actually holds the socket is a CHILD of the pid I recorded. Killing only
my recorded pid would leave a listener behind, and killing whatever holds the port without proof would
be someone else's server. A listener is closed only when all three hold:
  1. its host:port is on my named list (8611-8614),
  2. its own command line is the exact launch signature I used for that port,
  3. it answers for a journey id that exists only in my private sqlite file (or an ancestor of it is a
     pid I started).
Nothing here writes to the product tree, the preview dist, or any shared database.
"""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request

B = pathlib.Path('D:/moodle/_hjp3_0288t1_0925')
SRC = pathlib.Path('D:/moodle/HJ-P3_evidence')
RULER = pathlib.Path('D:/moodle/_qoder_cmdr_ref_20260921/live_checks/receipt_cell_derivation_check_r2.py')
PREVIEW = pathlib.Path('D:/moodle/_qoder_preview_20260920/dist/index.html')
RECEIPT = 'RECEIPT_O0288T1-1730.json'
MD = 'RECEIPT_O0288T1-1730.md'
RULER_TXT = 'q38_ruler_O0288T1-1730.txt'
STATE = json.loads((B / 'o0288_state.json').read_text(encoding='utf-8'))
RC = json.loads((B / RECEIPT).read_text(encoding='utf-8'))
DOOR = json.loads((B / 'seed_journey.json').read_text(encoding='utf-8'))
MUT = json.loads((B / 'mutant_arms.json').read_text(encoding='utf-8'))
C = {c['id'][:2]: c for c in RC['cells']}
D = RC['derived']
TIP = RC['measured_on']
MY_PORTS = [8611, 8612, 8613, 8614]
recorded = {}
for b in STATE['backends']:
    recorded[b['port']] = {'pid': b['pid'], 'tag': b['tag']}
for e in MUT:
    recorded.setdefault(e['backend']['port'], {'pid': e['backend']['pid'], 'tag': e['arm']})
journey_for_port = {8611: DOOR['journey_id'], 8612: DOOR['journey_id'],
                    8613: MUT[0]['journey']['journey_id'], 8614: MUT[1]['journey']['journey_id']}
L = []
w = L.append

CLOSING_FILE = pathlib.Path('D:/moodle/_qoder_cmdr_ref_20260921/live_checks/CLOSING_LINE.txt')
closing_bytes = CLOSING_FILE.read_bytes()
assert len(closing_bytes) == 83, f'closing line file is {len(closing_bytes)} B, not the 83 B authority'
closing_blob = hashlib.sha1(b'blob ' + str(len(closing_bytes)).encode() + bytes([0])
                            + closing_bytes).hexdigest()
assert closing_blob == 'b82ca923501c312b6931ad894c607ab9e43e1137', \
    f'closing line blob {closing_blob} is not the recorded authority'
closing = closing_bytes.decode('utf-8')


def ps(script):
    return subprocess.run(['powershell', '-NoProfile', '-Command', script], capture_output=True,
                          text=True, encoding='utf-8', errors='replace').stdout.strip()


def listeners(port):
    out = subprocess.run(['netstat', '-ano'], capture_output=True, text=True,
                         encoding='utf-8', errors='replace').stdout
    return sorted({ln.split()[-1] for ln in out.splitlines()
                   if ('127.0.0.1:%d ' % port) in ln and 'LISTENING' in ln})


def info(pid):
    cmd = ps("Get-CimInstance Win32_Process -Filter 'ProcessId=%s' | "
             'Select-Object -ExpandProperty CommandLine' % pid)
    ppid = ps("Get-CimInstance Win32_Process -Filter 'ProcessId=%s' | "
              'ForEach-Object { $_.ParentProcessId }' % pid)
    created = ps("Get-CimInstance Win32_Process -Filter 'ProcessId=%s' | "
                 'ForEach-Object { $_.CreationDate.ToString("o") }' % pid)
    return {'pid': int(pid), 'ppid': ppid, 'created': created, 'cmdline': cmd[:400]}


def ancestors(pid, depth=6):
    chain, cur = [], str(pid)
    for _ in range(depth):
        if not cur.isdigit():
            break
        i = info(cur)
        chain.append({'pid': i['pid'], 'cmdline_head': i['cmdline'][:120]})
        cur = i['ppid']
    return chain


def journey_echo(port, jid):
    """Two-sided store identity: MY journey id must answer 200 and echo, a bogus one must 404.

    A single 200 on one of my ports proves nothing - it can be another lane's server on a shared port.
    Echoing an id that exists only in my private sqlite file (and refusing one that does not) is what
    ties this listener to my store.
    """
    bogus = '00000000-0000-0000-0000-000000000000'
    out = {}
    for label, key in (('mine', jid), ('bogus', bogus)):
        url = 'http://127.0.0.1:%d/api/v1/journeys/%s' % (port, key)
        try:
            with urllib.request.urlopen(url, timeout=20) as f:
                body = f.read().decode('utf-8', 'replace')
                out[label] = {'url': url, 'status': f.status, 'bytes': len(body),
                              'echoes_the_id': ('"%s"' % key) in body}
        except urllib.error.HTTPError as e:
            out[label] = {'url': url, 'status': e.code,
                          'echoes_the_id': ('"%s"' % key) in (e.read() or b'').decode('utf-8', 'replace')}
        except Exception as e:  # noqa: BLE001
            out[label] = {'url': url, 'status': None, 'echoes_the_id': False, 'error': str(e)[:120]}
    out['proves_this_store'] = bool(out['mine']['status'] == 200 and out['mine']['echoes_the_id']
                                    and out['bogus']['status'] == 404)
    return out


# ---------------------------------------------------------------- teardown with three-way ownership proof
teardown = {'my_named_ports': MY_PORTS, 'listeners': {}}
for port in MY_PORTS:
    for pid in listeners(port):
        i = info(pid)
        sig = ('-m uvicorn app.main:app' in i['cmdline'] and ('--port %d' % port) in i['cmdline']
               and '--host 127.0.0.1' in i['cmdline'])
        echo = journey_echo(port, journey_for_port[port])
        anc = ancestors(pid)
        mine_by_ancestor = (any(str(a['pid']) == str(recorded.get(port, {}).get('pid')) for a in anc)
                            or any(('--port %d' % port) in a['cmdline_head'] for a in anc))
        verdict = {'cmdline_is_my_launch_signature': sig, 'answers_for_my_private_journey': echo,
                   'ancestor_pids': [a['pid'] for a in anc],
                   'ancestor_is_a_pid_i_recorded_or_carries_my_port': mine_by_ancestor,
                   'proven_mine': bool(sig and (echo['proves_this_store'] or mine_by_ancestor)),
                   'identity_probe': {'mine_status': echo['mine']['status'],
                                      'mine_echoes': echo['mine']['echoes_the_id'],
                                      'bogus_status': echo['bogus']['status'],
                                      'two_sided': echo['proves_this_store']}}
        if verdict['proven_mine']:
            r = subprocess.run(['taskkill', '/PID', str(pid), '/T', '/F'], capture_output=True,
                               text=True, encoding='utf-8', errors='replace')
            verdict['taskkill_rc'] = r.returncode
            verdict['taskkill_tail'] = (r.stdout or r.stderr or '').strip()[-120:]
        else:
            verdict['left_alone'] = True
        teardown['listeners'].setdefault(str(port), []).append(dict(i, **verdict))
time.sleep(2)
still = {str(p): listeners(p) for p in MY_PORTS}
teardown['listening_after'] = still
teardown['all_my_ports_free'] = not any(still.values())
# Append-only on disk: a second render of this file must never replace the round that actually killed
# something. The first shipping pass wrote teardown_O0288T1.json and a re-render overwrote it with an
# empty round, so that loss is disclosed in the receipt (self-report 7) and the writer is now stamped.
td_name = 'teardown_O0288T1_%s.json' % time.strftime('%H%M%S')
(B / td_name).write_text(json.dumps(teardown, ensure_ascii=False, indent=1),
                         encoding='utf-8', newline='\n')
teardown['written_to'] = td_name

# ---------------------------------------------------------------- boundary proof
chain = []
for ln in ps('(Get-NetTCPConnection -State Listen | Where-Object {$_.LocalPort -in 4781,4782}) | '
             'Select-Object LocalPort,OwningProcess | Format-Table -HideTableHeaders').splitlines():
    parts = ln.split()
    if len(parts) >= 2:
        chain.append({'port': parts[0], 'pid': parts[1], 'process_created': info(parts[1])['created']})
mine = sorted(list(SRC.glob('o0288_*.py')) + list(B.glob('*.py')))
# A literal-string scan always hits the scanner: the deny-list tuple and the `if needle in x` line.
# Those are self-references, not calls, so they are separated out instead of being counted as usage.
SELF_REF_MARKS = ('needle', "('_live.db'", "'_preview.db'", "'demo/reset'", "'git apply'",
                  "'citynexus.db'")
CALL_MARKS = ('subprocess', 'Popen', 'check_output', 'urlopen', 'requests.', 'sqlite3.connect',
              "['git'", "['taskkill'", 'os.system', 'os.popen')
scan = {}
for needle in ('_live.db', '_preview.db', 'demo/reset', 'git apply', 'citynexus.db'):
    calls, named, self_ref = [], [], 0
    for f in mine:
        for ln in f.read_text(encoding='utf-8', errors='replace').split(chr(10)):
            if needle not in ln:
                continue
            if any(m in ln for m in SELF_REF_MARKS):
                self_ref += 1
            elif any(m in ln for m in CALL_MARKS):
                calls.append({'file': f.name, 'line': ln.strip()[:160]})
            else:
                named.append({'file': f.name, 'line': ln.strip()[:160]})
    scan[needle] = {'lines_that_actually_use_it': len(calls), 'uses': calls,
                    'lines_that_only_name_it_in_a_denial_sentence': len(named), 'named': named[:8],
                    'lines_excluded_as_self_reference': self_ref}
index_html = PREVIEW.read_text(encoding='utf-8', errors='replace')
boundary = {
    'ran_at_local': time.strftime('%Y-%m-%dT%H:%M:%S%z'),
    'live_preview_index': {
        'path': str(PREVIEW), 'sha256_full_64_hex': hashlib.sha256(PREVIEW.read_bytes()).hexdigest(),
        'mtime_local': time.strftime('%Y-%m-%dT%H:%M:%S%z', time.localtime(PREVIEW.stat().st_mtime)),
        'asset_referenced': re.findall(r'assets/(index-[A-Za-z0-9_-]+\.js)', index_html)[:1],
        'touched_by_this_batch': 'no - ORD-0288 T-1 is an HTTP-level batch; it opened no browser and '
                                 'wrote to no dist directory'},
    'user_chain_listeners_untouched': chain,
    'negative_scan': scan,
    'coverage': 'NOT EXHAUSTIVE: %d ORD-0288 instrument files scanned by literal string: %s'
                % (len(mine), [f.name for f in mine]),
    'credential_handling': {
        'DEEPSEEK_API_KEY_popped_in_rig': "e.pop('DEEPSEEK_API_KEY', None)" in
                                          (SRC / 'o0288_rig.py').read_text(encoding='utf-8'),
        'sk_shaped_strings_in_my_files': [f.name for f in mine
                                          if re.search(r'sk-[A-Za-z0-9]{10,}',
                                                       f.read_text(encoding='utf-8', errors='replace'))]},
    'product_tree_written': 'no - the exported tree at %s is read-only for this batch; the crash and '
                            'signature mutants ran in private copies named in C5/C2' % TIP}
(B / 'boundary_proof_O0288T1.json').write_text(json.dumps(boundary, ensure_ascii=False, indent=1),
                                               encoding='utf-8', newline='\n')

# ---------------------------------------------------------------- ruler (its own artefact, never quoted inside the receipt)
rr = subprocess.run([sys.executable, str(RULER), '--receipt', RECEIPT, '--min-cells', '7',
                     '--expect', 'Q38_GATE_GREEN'], cwd=str(B), capture_output=True, text=True,
                    encoding='utf-8', errors='replace')
(B / RULER_TXT).write_text(rr.stdout + chr(10) + 'STDERR:' + (rr.stderr or '')[-300:] +
                           chr(10) + 'EXIT=' + str(rr.returncode) + chr(10),
                           encoding='utf-8', newline='\n')
rl = [x for x in rr.stdout.strip().split(chr(10)) if x.strip()]
ruler_head, ruler_verdict = (rl[0], rl[1]) if len(rl) > 1 else ('', '')
ruler_expect = rl[-1] if rl else ''

# ---------------------------------------------------------------- human receipt
m1, m2, m3, m4, m5, m6 = (C['C1']['measured'], C['C2']['measured'], C['C3']['measured'],
                          C['C4']['measured'], C['C5']['measured'], C['C6']['measured'])
row1, row3 = m1['idempotency_keys_row'], m4['row_written']
procs = {p['tag']: p for p in m1['processes']}
eq = m1['equality_basis_of_the_replay_claim']
out_c = RC['r2_notes']['batch_outcome']

w(f"# ORD-0288 T-1(a)/(b) · 幂等键的耐久所有权与错误路径落行 · HJ-P3 aad2d1f2")
w('')
w(f"> **measured_on = `{TIP}`** · {RC['measured_on_how_read']} · 一次性库 "
  f"`{str(STATE['db']).split(os.sep)[-1]}` 由产品自己的 `ensure_schema()` 建、起面先删（R-SCHEMA-01）· "
  f"两个 uvicorn 进程 {procs['A']['port']}/{procs['B']['port']}（pid {procs['A']['pid']} 与 "
  f"{procs['B']['pid']}）**指向同一个库文件**（`both_processes_point_at_the_same_file = "
  f"{STATE['both_processes_share_one_file']}`）· journey `{DOOR['journey_id']}`。")
w(f"> **`derived_result` = {json.dumps(RC['derived_result'])}**（那是 verifier 的字）· "
  f"`claimed_result = {RC['claimed_result']}`。按仲裁原话执行 (a)：期望写的是 "
  f"`observe durable ownership`，这张表里没有\u201c预计红\u201d三个字，结果由实测定。")
w('')
w('## 0. 大白话（先把好消息和坏消息说清楚，再说这轮的边界）')
w('**好消息是真的**：同一把键跨两个进程发，库里只留一行；杀掉写它的那个进程、重新起一个，那一行还在、'
  '还能被读出来当回执用。**所有权在数据库里，不在进程内存里。**')
w('**坏消息也是真的**：某一发**抢到键却没把答案落下去**（我这轮在私有副本里注入一枚未处理异常造出来），'
  f"那一行就永远停在 `response_status = {m5['row_response_status_after_the_crash']!r}`；此后谁拿这把键再来，"
  f"都只会拿到同一句 {m5['replay_same_process']['status']}「agent idempotency record is incomplete」——"
  '**调用方分不清\u201c对方还在算\u201d和\u201c对方早死了\u201d，而这把键永久作废。**')
w(f"**这轮的射程要说白**：本批共 {sum(out_c['send_count_per_status'].values())} 发带键请求"
  f"（{'、'.join(str(v) + ' 发 ' + k for k, v in sorted(out_c['send_count_per_status'].items()))}），"
  f"`plan_versions` 到收尾仍是 {list(out_c['plan_versions_rows_per_arm_durable_read'].values())} "
  '—— 也就是说\u201c耐久\u201d是在一枚**拒绝回执**上量到的，200 带方案的回执重放本批没测（C7 里具名）。')
w(f"**还有一句不藏**：\u201c同一份答案\u201d我按 JSON 值判（去掉 `error.trace_id`），"
  f"原始字节**并不相等**（`raw_bytes_equal = {eq['raw_bytes_equal']}`），因为 `error.details` 重新序列化时"
  f"键的插入顺序不同（`details_key_insertion_order_differs = "
  f"{eq['details_key_insertion_order_differs']}`）。写进件里，免得这句话被读成\u201c逐字节相同\u201d。")
w('')
w('## 1. 两问的读数（每格自证，Q38 尺对这份件跑过，见 §4）')
w('```text')
for c in RC['cells']:
    w(f"{c['id'].split('_', 1)[0]} ｜ {c['verdict']}")
w('')
w(f"(a) 耐久所有权 C1：键 {m1['key']} 在 {str(m1['database_file']).split(os.sep)[-1]} 里有 "
  f"{m1['rows_holding_this_key']} 行 · operation={row1['operation']!r} · response_status="
  f"{row1['response_status']} · response_json={row1['response_json_bytes']} B · 到期（库里存 UTC）"
  f"{row1['expires_at']}")
w(f"    第二发走 {procs['B']['port']}（另一个 pid {procs['B']['pid']} vs {procs['A']['pid']}）："
  f"{m1['second_send_other_process']['status']} / {m1['second_send_other_process']['elapsed_ms']} ms · "
  f"去 trace_id 后 JSON 值相等={eq['json_values_equal_after_dropping_trace_id']} · 原始字节相等="
  f"{eq['raw_bytes_equal']}")
w(f"    杀掉首发进程 {m6['killed_pid']} 再起重放（C6）：{m6['replay_from_the_fresh_process']} / "
  f"{m6['replay_bytes']} B · 行仍 {m6['rows_holding_this_key_after_the_restart']} 行 ⇒ 耐久不只是\u201c两个活进程互看\u201d")
w(f"    同键换体（C2）：{m2['status_when_pristine']}，正文 {m2['body_refused'][:72]}… · "
  f"该行未被改写={m2['durable_row_untouched_by_the_refusal']}")
keys_listed = m3['gates_three_way']['negative'].split('distinct keys (')[-1].split('), so')[0].split(', ')
w(f"    并发同键（C3）：{m3['leg_A']['status']}/{m3['leg_B']['status']} 在 {m3['wall_ms_both']} ms 内，"
  f"这个键 {m3['rows_holding_this_key']} 行 · 同一次耐久读里全表 {m3['idempotency_rows_all_keys']} 行 / "
  f"{len(keys_listed)} 个不同键（{', '.join(keys_listed)}）")
w(f"    多出来的那一行是上一臂留下的键（"
  f"{[k for k in keys_listed if not k.endswith(m3['key'])]}），不是并发造出来的第二个所有者："
  f"按本臂键后缀过滤仍是 {m3['rows_holding_this_key']} 行；那枚报 False 的臂内标志怎么来的写在 "
  f"C3.arm_flag_discrepancy（见 §3 自曝 4)）")
w('')
w(f"(b) 错误路径 C4：路由内拒绝落了行 response_status={row3['response_status']} · "
  f"{row3['response_json_bytes']} B · 重放 {m4['replay_of_that_failure']['status']}（JSON 值相等="
  f"{m4['replay_of_that_failure']['json_values_equal_after_dropping_trace_id']}）")
w(f"    抢占之前的拒绝（非法键 {m4['pre_claim_rejection']['malformed_key_status']}）：不留行 "
  f"{m4['pre_claim_rejection']['rows_matching_that_key']}、不作废这把键（之后一把正常键仍能跑："
  f"{m4['pre_claim_rejection']['a_later_valid_send_still_works']}）")
w(f"    抢占之后不落答案（C5，私有副本注入）：首发 {m5['first_send_status']} · 行 response_status="
  f"{m5['row_response_status_after_the_crash']!r} · 同进程重放 {m5['replay_same_process']['status']} · "
  f"换新进程重放 {m5['replay_after_a_fresh_process']['status']} · unknown result 可判 = "
  f"{D['unknown_result_is_distinguishable']}")
w('```')
w('')
w('## 2. 每枚布尔闸的三向（EVIDENCE_INTEGRITY_GATE_V1）')
w('```text')
for k in ('C1', 'C2', 'C3', 'C4', 'C5', 'C6'):
    g = C[k]['measured']['gates_three_way']
    w(f"{k} positive : {g['positive']}")
    w(f"{k} negative : {g['negative']}")
    w(f"{k} mutation : {g['mutation']}")
    w('')
w('闸的元数据（本件自跑）：字面布尔闸 '
  f"{RC['integrity_gate_selfcheck']['boolean_gates_still_literal']} · 多余键 "
  f"{RC['integrity_gate_selfcheck']['gates_blocks_holding_more_than_the_three_named_gates']} · "
  f"跨格引用全部可解 {RC['integrity_gate_selfcheck']['cross_cell_pointers_all_resolving']}")
w('```')
w('')
w('## 3. 我自曝（全部另发新件，不覆盖不删）')
w('```text')
w('1) T-1 第一遍每一臂都报\u201c0 行\u201d——不是产品没落行，是我的 arm runner 压根没去读库。改成\u201c每臂必读一次 '
  'store\u201d后整套重跑；第一遍的 cell 文件仍在目录里（run id 更早），本件没有一个数字来自它们。')
w('2) 第一枚突变体拆错了地方：拆的是 replan 那条路的签名比较，而 plans/generate 走的是 '
  '`_replay_committed_accept` ⇒ 409 照旧，那枚\u201c突变\u201d什么也没证明。它被我当反例保留（'
  f"C2.control_mutant_that_removes_another_guard，读数仍是 {m2['control_mutant_that_removes_another_guard']['different_body_status_still']}）。")
w('3) 崩溃注入第一次插在 `def _generate_plans_answer(` 之后（签名跨行 ⇒ SyntaxError ⇒ 突变体起不来，'
  '端口拒绝连接才暴露）；改成插在函数体内那条语句之前，并在写盘前先 ast.parse。')
w('4) 并发臂自己 `extra` 里那枚 `exactly_one_row_for_the_key` 是 **False**，而库里那一行明明在：因为我把裸键 '
  '传进了 `WHERE key LIKE ?`，存的是 `plans.generate:<键>`，那条查询匹配 0 行。**这是我查询写法造的假读数，'
  '不是第二次观测**；C3.arm_flag_discrepancy 里连着查询语句一起写明了，本件用的行数来自同一次耐久读的键过滤。')
w('5) 这份收据从我第一版算稿改到第 7 版才落成要交的 '
  f"`{RECEIPT}`（逐版 sha256 记在件内 `lineage`，7 份都留在本地目录、一个字节没覆盖）："
  'r2 修了\u201c字段名比它算的东西强\u201d和一枚恒真谓词（`... is not None` 当\u201c活下来了\u201d用）；r3/r4 把三向闸从裸布尔写成句子；'
  'r5 把短摘要全部登记成\u201c历史显示值\u201d；r6 把 gates 块清成正好三向；r7 修了一处指错格子的引用（C3 写 C4，实为 C5）。'
  '**臂只跑过一次（16:23–16:32），七版全部只是重读同一批 cell 文件** —— 没有一个数字因为改版而变。')
RESTORED = B / 'teardown_O0288T1_round1_restored_from_console.txt'


def holder_snapshot(port):
    """The pre-teardown listener table, parsed out of the restored console transcription."""
    if not RESTORED.exists():
        return None
    blocks = RESTORED.read_text(encoding='utf-8').split(chr(10) + 'PID ')
    for blk in blocks:
        if ('--port %d' % port) in blk and 'uv\\python' in blk.replace('\\\\', '\\'):
            head = ('PID ' + blk.splitlines()[0]).strip()
            return head
    return None


holders = {str(p): holder_snapshot(p) for p in (8611, 8612, 8613)}
w('6) 收尾不能只按\u201c我记下的 pid\u201d杀：venv 启动器会 re-exec，真正握套接字的是我记下 pid 的**子进程**'
  '（本批我记在 8611 上的 pid = ' + str(recorded.get(8611, {}).get('pid')) + '；第一趟收尾前读到的实际持有者 '
  + json.dumps(holders, ensure_ascii=False) + '，ppid 才是我记的那一枚）。第一趟收尾对每个监听者做了三道证才 '
  'taskkill：端口在我具名单上 + 命令行是我那串启动签名 + 它只对我私有库里那一枚 journey id 答 200、'
  '对一枚假 id 答 404（双向），祖先链里有我记的 pid 也算一条辅证，三样不齐就留着不动。'
  '逐 pid 读数原本写在 `teardown_O0288T1.json`，被后一趟重排时以空读数盖掉（见自曝 7)）；'
  '现已把**当趟控制台输出**转录另存为 `' + RESTORED.name + '` —— 那份是转录、不是原工件，也不是新测量，'
  '上面那三个持有者行就是从它现读出来的。')
w('7) 我覆盖了自己一枚收尾件：第一趟收尾确实关掉了监听进程（三道证都过，逐 pid 读数写在当时的 '
  '`teardown_O0288T1.json` 里）；后一趟只是重排版面，收尾段又跑一次，此时场上已经没有可关的进程，'
  '**于是那份空读数把上一轮的证据盖掉了**（那份空读数现在改名叫 '
  '`teardown_O0288T1_round2_overwrote_round1.json`，留在目录里不装无事）。从这一趟起写件带时间戳（本轮 '
  + td_name + '），本件 §4 里 `listening_after` 四口全空就是这一趟的读数，不是第一趟的。'
  '被盖掉那一轮我只能报"发生过、逐 pid 读数已不在盘上"，不拿空件冒充两轮。')
w('8) 尾行口令我上一班漏了半句：ORD-0301 补交那条总线帖（15:5x）仍按旧短式收尾，而号令者 15:0x 已把它'
  '定成逐字全文（他的规矩：尾行不匹配＝未送达）。这不是产品问题，是我的投递问题——勘误与全文尾行随本批'
  '那条新帖走（新帖、不改旧帖）。本件尾部那一行是从 `' + CLOSING_FILE.name + '` 现读的 '
  + str(len(closing_bytes)) + ' B 原文（blob sha1 ' + closing_blob + '），一个字都没手打。')
w('```')
w('')
w('## 4. 尺子、边界与收尾')
w('```text')
w(f"  {ruler_head}")
w(f"  {ruler_verdict}")
w(f"  {ruler_expect}   （尺输出单列成件：{RULER_TXT}，收据里不抄自己的判词）")
w(f"  在服 dist/index.html：sha256 {boundary['live_preview_index']['sha256_full_64_hex']} · "
  f"mtime {boundary['live_preview_index']['mtime_local']} · 引用 "
  f"{boundary['live_preview_index']['asset_referenced']} · 本批 0 写（这批 HTTP 级，没有一个面）")
w(f"  用户链 4781/4782 我 0 触碰，进程创建时间 "
  f"{', '.join(x['port'] + '=' + x['process_created'][:19] for x in chain)}")
w(f"  负面扫描（{len(mine)} 个仪器文件，逐行原文落件，分类靠调用标记启发式、人工可复核）："
  f"真正调用行 "
  f"{json.dumps({k: v['lines_that_actually_use_it'] for k, v in scan.items()}, ensure_ascii=False)} · "
  f"只在否认句里提到名字 "
  f"{json.dumps({k: v['lines_that_only_name_it_in_a_denial_sentence'] for k, v in scan.items()}, ensure_ascii=False)} · "
  f"扫描器自己那几行另计 "
  f"{json.dumps({k: v['lines_excluded_as_self_reference'] for k, v in scan.items()}, ensure_ascii=False)} · "
  f"coverage {boundary['coverage'][:24]}…")
w(f"  凭据：rig 里 pop 掉 DEEPSEEK_API_KEY = {boundary['credential_handling']['DEEPSEEK_API_KEY_popped_in_rig']} · "
  f"我文件里 sk 形状字符串 = {boundary['credential_handling']['sk_shaped_strings_in_my_files']}")
w(f"  突变体私有副本（hardlink 审计 files_checked="
  f"{STATE['hardlink_audit_pristine']['files_checked']}, nlink>1 = "
  f"{len(STATE['hardlink_audit_pristine']['nlink_gt_1'])}）：产品树与权威线 0 写；"
  f"C5 里 main.py 摘要为全 64 位 = {len(m5['private_copy']['main_py_sha256'])} 位（r1 曾写 16 位，"
  f"前缀吻合 = {m5['private_copy']['r1_short_values_are_prefixes_of_these']}）")
w(f"  收尾：端口 {MY_PORTS} 监听读数 {json.dumps(teardown['listening_after'], ensure_ascii=False)} · "
  f"全空 = {teardown['all_my_ports_free']} · 本趟收尾件 = {td_name}（带时间戳，不覆盖旧件）")
w(f"  尾行口令：现读 {CLOSING_FILE} · {len(closing_bytes)} B · blob sha1 {closing_blob} · sha256 "
  f"{hashlib.sha256(closing_bytes).hexdigest()} · 逐字比对（83 B + 全句两小句）通过才落笔，手打 0 次")
w('```')
w('')
w('%COORD%')
w('')
w(f"**状态**：T-1(a)/(b) 交完。(a) 我按 `observe durable ownership` 落成读数——**跨进程、跨重启的所有权是真的，"
  f"但\u201c同一份答案\u201d只到 JSON 值这一层；抢到却没落答案的那把键永久作废且不可判"
  f"（unknown_result_is_distinguishable = {D['unknown_result_is_distinguishable']}）**。"
  f"手上没有别的活；ORD-0301 那 22 行 sheet 本体读数的 "
  f"`dc964086c9d412573ac19d70b24b30e6c3ee6168` 补测我随叫随开（X'），"
  f"坐标栏在 `table_O0301_p3_coordbasis.json`。")
w('')
# The tail line is FETCHED, never typed: commander set this rule on 2026-09-25 15:0x after mistyping his
# own instruction twice. Byte length and blob are asserted before the file is written.
w(closing)
(B / MD).write_text(chr(10).join(L) + chr(10), encoding='utf-8', newline='\n')
txt = (B / MD).read_text(encoding='utf-8')
print('md', len(L), 'lines |', len(txt.encode('utf-8')), 'B | CRLF',
      (chr(13) in txt), '| NUL', txt.count(chr(0)), '| %COORD% left', '%COORD%' in txt)
print('ruler:', ruler_verdict, '|', ruler_expect, '| exit', rr.returncode)
print('teardown all free:', teardown['all_my_ports_free'], '| listeners now:',
      json.dumps(teardown['listening_after'], ensure_ascii=False))
print('proven-mine verdicts:', json.dumps(
    {p: [{'pid': x['pid'], 'proven': x['proven_mine'], 'two_sided': x['identity_probe']['two_sided'],
          'killed': x.get('taskkill_rc')} for x in v]
     for p, v in teardown['listeners'].items()}, ensure_ascii=False))
raise SystemExit(0)
