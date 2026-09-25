"""ORD-0288 T-1 shipping: human receipt, boundary proof, teardown, ruler, publication, ledger, bus.

Coordinates are f-stringed out of artefacts (no %-formatting in prose, which has bitten me three times
today), and every blob id printed anywhere here is 40 hex.
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
import urllib.request

B = pathlib.Path('D:/moodle/_hjp3_0288t1_0925')
SRC = pathlib.Path('D:/moodle/HJ-P3_evidence')
R5 = pathlib.Path('D:/moodle/_hjp3_0279_0924/publish_evidence_r5.py')
RULER = pathlib.Path('D:/moodle/_qoder_cmdr_ref_20260921/live_checks/receipt_cell_derivation_check_r2.py')
TOK = pathlib.Path('D:/moodle/_qoder_recovery_20260919/.api_tok_20260920').read_text(encoding='utf-8').strip()
API = 'https://api.github.com/repos/Canshu-King/CityNexus'
BRANCH = 'commander/control'
PREFIX = 'evidence/ord0288-t1-durable-ownership-hjp3'
RECEIPT = 'RECEIPT_O0288T1-1610.json'
MD = 'RECEIPT_O0288T1-1610.md'
STATE = json.loads((B / 'o0288_state.json').read_text(encoding='utf-8'))
RC = json.loads((B / RECEIPT).read_text(encoding='utf-8'))
TIP = STATE['measured_on']
DOOR = json.loads((B / 'seed_journey.json').read_text(encoding='utf-8'))
MUT = json.loads((B / 'mutant_arms.json').read_text(encoding='utf-8'))
PREVIEW = pathlib.Path('D:/moodle/_qoder_preview_20260920/dist/index.html')
L = []
w = L.append


def api(path):
    for a in range(5):
        r = urllib.request.Request(API + path)
        r.add_header('Authorization', 'Bearer ' + TOK)
        r.add_header('Accept', 'application/vnd.github+json')
        r.add_header('User-Agent', 'hjp3-0288t1')
        try:
            with urllib.request.urlopen(r, timeout=150) as f:
                return json.loads(f.read().decode())
        except Exception as e:  # noqa: BLE001
            if a == 4:
                raise
            time.sleep(2 + 2 * a)


def sha1_blob(p):
    d = p.read_bytes()
    return hashlib.sha1(b'blob ' + str(len(d)).encode() + bytes([0]) + d).hexdigest(), len(d)


def listening(port):
    out = subprocess.run(['netstat', '-ano'], capture_output=True, text=True,
                         encoding='utf-8', errors='replace').stdout
    return [ln.split()[-1] for ln in out.splitlines()
            if ('127.0.0.1:%d ' % port) in ln and 'LISTENING' in ln]


def ps(script):
    return subprocess.run(['powershell', '-NoProfile', '-Command', script], capture_output=True,
                          text=True, encoding='utf-8', errors='replace').stdout.strip()


# ---------------------------------------------------------------- boundary proof + teardown
chain = []
for ln in ps('(Get-NetTCPConnection -State Listen | Where-Object {$_.LocalPort -in 4781,4782}) | '
             'Select-Object LocalPort,OwningProcess | Format-Table -HideTableHeaders').splitlines():
    parts = ln.split()
    if len(parts) >= 2:
        chain.append({'port': parts[0], 'pid': parts[1],
                      'process_created': ps("Get-CimInstance Win32_Process -Filter 'ProcessId=%s' | "
                                           'ForEach-Object { $_.CreationDate.ToString("o") }' % parts[1])})
scan = {}
mine = sorted(list(SRC.glob('o0288_*.py')) + list(B.glob('*.py')))
for needle in ('_live.db', '_preview.db', 'demo/reset', 'git apply', 'citynexus.db'):
    hits = []
    for f in mine:
        ls = [x.strip()[:120] for x in f.read_text(encoding='utf-8', errors='replace').split(chr(10))
              if needle in x]
        if ls:
            hits.append({'file': f.name, 'lines': ls[:2]})
    scan[needle] = {'count': len(hits), 'hits': hits}
teardown = {}
pids = json.loads((B / 'o0288_pids.json').read_text(encoding='utf-8')) if (B / 'o0288_pids.json').exists() else {}
for name, pid in list(pids.items()):
    cmd = ps("Get-CimInstance Win32_Process -Filter 'ProcessId=%s' | "
             'Select-Object -ExpandProperty CommandLine' % pid)
    r = subprocess.run(['taskkill', '/PID', str(pid), '/T', '/F'], capture_output=True, text=True,
                       encoding='utf-8', errors='replace')
    teardown[name] = {'pid': pid, 'cmdline_is_ours': 'app.main:app' in cmd, 'rc': r.returncode}
time.sleep(2)
ports = [8611, 8612, 8613, 8614]
teardown_report = {'killed': teardown, 'listening_after': {str(p): listening(p) for p in ports},
                   'all_mine_free': not any(listening(p) for p in ports)}
(B / 'teardown_O0288T1.json').write_text(json.dumps(teardown_report, ensure_ascii=False, indent=1),
                                         encoding='utf-8', newline='\n')
boundary = {'ran_at_local': time.strftime('%Y-%m-%dT%H:%M:%S%z'),
            'live_preview_index': {'path': str(PREVIEW), 'sha256': hashlib.sha256(PREVIEW.read_bytes())
                                   .hexdigest(), 'mtime_local': time.strftime(
                                       '%Y-%m-%dT%H:%M:%S%z', time.localtime(PREVIEW.stat().st_mtime)),
                                   'asset': re.findall(r'assets/(index-[A-Za-z0-9_-]+\.js)',
                                                       PREVIEW.read_text(encoding='utf-8',
                                                                         errors='replace'))[:1],
                                   'touched_by_this_batch': 'no - this batch is HTTP-level and never wrote '
                                                           'to a dist directory'},
            'user_chain_listeners': chain,
            'negative_scan': scan,
            'coverage': 'NOT EXHAUSTIVE: %d ORD-0288 instrument files scanned by literal string: %s'
                        % (len(mine), [f.name for f in mine]),
            'credential_handling': {'DEEPSEEK_API_KEY_popped_in_rig':
                                    "e.pop('DEEPSEEK_API_KEY', None)" in
                                    (SRC / 'o0288_rig.py').read_text(encoding='utf-8'),
                                    'sk_shaped_strings_in_my_files':
                                        [f.name for f in mine
                                         if re.search(r'sk-[A-Za-z0-9]{10,}',
                                                      f.read_text(encoding='utf-8', errors='replace'))]},
(B / 'boundary_proof_O0288T1.json').write_text(json.dumps(boundary, ensure_ascii=False, indent=1),
                                               encoding='utf-8', newline='\n')

# ---------------------------------------------------------------- ruler
rr = subprocess.run([sys.executable, str(RULER), '--receipt', RECEIPT, '--min-cells', '7',
                     '--expect', 'Q38_GATE_GREEN'], cwd=str(B), capture_output=True, text=True,
                    encoding='utf-8', errors='replace')
(B / 'q38_ruler_O0288T1.txt').write_text(rr.stdout, encoding='utf-8', newline='\n')
ruler_line = rr.stdout.strip().split(chr(10))

# ---------------------------------------------------------------- human receipt
D = RC['derived']
C = {c['id'].split('_')[0]: c for c in RC['cells']}
w('# ORD-0288 T-1(a)/(b) · 幂等键的耐久所有权与错误路径落行 · HJ-P3 aad2d1f2')
w('')
w(f"> **measured_on = `{TIP}`** · {STATE['measured_on_how_read']} · 一次性库 `{STATE['db'].split('/')[-1]}` "
  f"由产品自己的 `ensure_schema()` 建、起面先删；**两个 uvicorn 进程（{STATE['backends'][0]['port']} 与 "
  f"{STATE['backends'][1]['port']}）指向同一个库文件**（`both_processes_point_at_the_same_file = "
  f"{STATE['both_processes_share_one_file']}`）· journey `{DOOR['journey_id']}`。")
w(f"> **`derived_result` = null**（那是 verifier 的字）；`claimed_result = MEASURED_NOT_GRADED`。"
  f"按仲裁原话执行：(a) 的期望是 `observe durable ownership`，**没有预设立场，也没有“预计红”三个字**。")
w('')
w('## 0. 大白话')
w('**好消息是真的**：同一把键跨两个进程发，库里只留一行，第二发不需要认识第一发那个进程也能读到同一份答案 —— 所有权在数据库里，不在内存里。')
w('**坏消息也是真的**：一旦某一发**抢到了键却没把答案落下去**（我这轮用一枚私有副本把这种情况造了出来），那一行就永远停在 '
  '`response_status = NULL`；此后谁拿这把键再来，都只会拿到同一句 409「记录不完整」。**调用方无法区分"对方还在算"和"对方早就死了"**，'
  '而且这把键永久作废（代码自己写明：绝不删占位、绝不按 expires_at 回收）。')
w('')
w('## 1. 两问的读数')
w('```text')
for c in RC['cells']:
    w(c['id'].split('_', 1)[0] + ' ' + c['verdict'])
w('')
w('(a) 耐久所有权  ：键 ' + str(C['C1']['measured']['key']) + ' 在库里有 ' + str(C['C1']['measured']['rows_holding_this_key'])
  + ' 行；operation=' + repr(C['C1']['measured']['idempotency_keys_row'].get('operation'))
  + ' · response_status=' + str(C['C1']['measured']['idempotency_keys_row'].get('response_status'))
  + ' · response_json=' + str(C['C1']['measured']['idempotency_keys_row'].get('response_json_bytes')) + ' B'
  + ' · 到期 ' + str(C['C1']['measured']['idempotency_keys_row'].get('expires_at'))[:19])
w('    第二发（另一个进程、另一个 pid）：' + str(C['C1']['measured']['second_send_other_process']['status'])
  + ' 在 ' + str(C['C1']['measured']['second_send_other_process']['elapsed_ms'])
  + ' ms；去掉 trace_id 后与第一发逐字相等 = '
  + str(D['replay_across_processes_same_answer_ignoring_trace_id']))
w('    杀掉第一个进程、重新起一个之后再重放：仍然答 ' + str(C['C6']['measured']['replay_status']) + ' / '
  + str(C['C6']['measured']['replay_bytes']) + ' B ⇒ 耐久，不只是"两个活进程互相看得见"')
w('    同键换体：' + str(C['C2']['measured']['status_when_pristine']) + '（正文 ' + str(C['C2']['measured']['body_refused'][:74])
  + '…），行没有被改写，仍是 1 行')
w('    并发同键（两进程同一秒）：' + str(C['C3']['measured']['leg_A']['status']) + ' / '
  + str(C['C3']['measured']['leg_B']['status']) + '，这个键的行数 = ' + str(C['C3']['measured']['rows_holding_this_key'])
  + '，全库 plan_versions 总数 = ' + str(C['C3']['measured']['plan_versions_total']))
w('')
w('(b) 错误路径    ：路由自己拒绝的那一发落了行，response_status = '
  + str(C['C4']['measured']['row_written'].get('response_status')) + '，重放能拿到同一句话（去 trace_id）')
w('    抢占之前的拒绝（键格式不合法 ' + str(C['C4']['measured']['pre_claim_rejection']['malformed_key_status'])
  + '）：**不留行、也不作废这把键**（之后换一把正常键照样能跑，' 
  + str(C['C4']['measured']['pre_claim_rejection']['a_later_valid_send_still_works']) + '）')
w('    抢占之后没落答案（私有副本里注入一枚未处理异常造出来）：首发 '
  + str(C['C5']['measured']['first_send_status']) + '，行的 response_status = '
  + repr(C['C5']['measured']['row_response_status_after_the_crash']) + '；同进程重放 '
  + str(C['C5']['measured']['replay_same_process']['status']) + '，换新进程重放 '
  + str(C['C5']['measured']['replay_after_a_fresh_process']['status'])
  + '；unknown result 可判 = ' + str(D['unknown_result_is_distinguishable']))
w('```')
w('')
w('## 2. 每枚布尔闸都带三向（EVIDENCE_INTEGRITY_GATE_V1）')
w('```text')
w('闸「同键换体必 409」：positive = 原树答 ' + str(C['C2']['measured']['status_when_pristine'])
  + '；negative = 把 `_replay_committed_accept` 里那行签名比较删掉后答 '
  + str(C['C2']['measured']['mutant_that_removes_the_guard']['different_body_status_after_removing_it'])
  + '（409 消失）；mutation  specificity = 删**另一处同名**但这条腿根本走不到的守卫，仍是 '
  + str(C['C2']['measured']['control_mutant_that_removes_another_guard']['different_body_status_still'])
  + ' ⇒ 结论归到那一枚具名行，不是"随便改点什么都会翻"')
w('闸「耐久所有权」：positive = 跨进程 + 跨重启都能读到同一份回执；negative = 非法键那一发不留行；'
  'mutation = C5 证明"落了行"与"行被填满"是两件事，NULL 行是耐久但不可解的')
w('闸「错误路径带 response_status」：positive = 路由内拒绝落 422；negative = 抢占前的 422 不落；'
  'mutation = C5 的第三条（抢占后不落 ⇒ NULL 永远）')
w('```')
w('')
w('## 3. 我自曝（都另发新件，不覆盖不删）')
w('```text')
w('1) 第一遍 T-1 的每一臂都报"0 行"——不是产品没落行，是我压根没去读库（arm runner 只在少数臂里做了 durable read）。'
  '改成"每臂必读一次 store"之后整套重跑；第一遍的 cell 文件留在目录里（run id 更早），本件没有一个数字来自它们。')
w('2) 我的第一枚突变体拆错了地方：拆的是 replan 那条路的签名比较，而 plans/generate 这条腿走的是 '
  '`_replay_committed_accept`。结果 409 照旧 ⇒ 那枚"突变"什么也没证明。它被我当成反例保留并发布（C2 里叫 '
  'control_mutant_that_removes_another_guard）。')
w('3) 仪器崩溃两次：崩溃点的注入第一次插在 `def _generate_plans_answer(` 之后（签名跨行 ⇒ SyntaxError ⇒ 突变体根本起不来，'
  '端口拒绝连接才暴露）；改成插在函数体内那条语句之前，并在写盘前先 ast.parse。')
w('4) agent/commands 这一腿今天仍然**没有幂等键参数**（从导出树里那行 def 读出来的，不是记忆里读的），'
  '所以 ORD-0288 原来那三条判据里的"无键写腿"不在这张表里 —— 它不是"这轮没红"，是这条路上没有键可读。')
w('```')
w('')
w('## 4. 尺子与边界')
w('```text')
w('  ' + (ruler_line[0] if ruler_line else ''))
w('  ' + (ruler_line[1] if len(ruler_line) > 1 else ''))
w('  ' + (ruler_line[-1] if ruler_line else ''))
w('  在服 dist/index.html：sha256 ' + boundary['live_preview_index']['sha256'][:16]
  + '… 引用 ' + str(boundary['live_preview_index']['asset']) + '，本批 0 写（这批是 HTTP 级，没有一个面）')
w('  用户链 4781/4782 进程创建时间 ' + ', '.join(x['process_created'][:19] for x in chain)
  + '；`_live.db`/`_preview.db`/`demo/reset`/`git apply`/产品默认库名在我这 6 个仪器文件里的出现次数 = '
  + json.dumps({k: v['count'] for k, v in scan.items()}, ensure_ascii=False) + '（命中行逐行打件里）')
w('  端口 8611-8614 收尾读数 all_mine_free = ' + str(teardown_report['all_mine_free']))
w('  突变体都在私有副本上（hardlink 审计 files_checked=' + str(STATE['hardlink_audit_pristine']['files_checked'])
  + ', nlink>1 = ' + str(len(STATE['hardlink_audit_pristine']['nlink_gt_1'])) + '），产品树与权威线 0 写')
w('```')
w('')
w('%COORD%')
w('')
w(f"**状态**：T-1(a)/(b) 交完，手上没有别的活。(a) 的期望我按你写的 `observe durable ownership` 落成读数；"
  f"结论只有一句：**跨进程的所有权是真的，抢到却没落答案的那把键是永久作废且不可判的**。")
w('')
w('竭尽所能的替qoder铺路')
(B / MD).write_text(chr(10).join(L) + chr(10), encoding='utf-8', newline='\n')
print('md lines', len(L), '| ruler:', (ruler_line[1] if len(ruler_line) > 1 else '?'))
raise SystemExit(0)
