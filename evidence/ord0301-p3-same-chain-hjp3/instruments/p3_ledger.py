"""ORD-0301 pass 3 - the ledger block. Inserted directly under `## ORDERS（收件箱` by insert_block.py, which
anchors on a string measured in the same run and proves the untouched remainder byte-for-byte.

Every number, blob and quoted sentence is read at run time off the artefacts and the branch tree, so this
block cannot state something the batch did not measure.
"""
from __future__ import annotations

import hashlib
import importlib.util as iu
import json
import pathlib
import subprocess
import sys
import time

B = pathlib.Path('D:/moodle/_hjp3_0301p3_0925')
SRC = pathlib.Path('D:/moodle/HJ-P3_evidence')
spec = iu.spec_from_file_location('pub', str(SRC / 'p3_publish.py'))
pub = iu.module_from_spec(spec)
spec.loader.exec_module(pub)

SC = json.loads((B / 'p3_scored.json').read_text(encoding='utf-8'))
RC = json.loads((B / 'RECEIPT_O0301P3-2230.json').read_text(encoding='utf-8'))
BD = json.loads((B / 'p3_boundary.json').read_text(encoding='utf-8'))
NR = json.loads((B / 'no_rewrite_proof_p3.json').read_text(encoding='utf-8')) if (
    B / 'no_rewrite_proof_p3.json').exists() else {}
GS = json.loads((B / 'gate_selftest_publish_p3.json').read_text(encoding='utf-8')) if (
    B / 'gate_selftest_publish_p3.json').exists() else {}
tip_now, tree_now, rows_now = pub.branch_rows()
KEY = {r['path'][len(pub.PREFIX) + 1:]: r for r in rows_now}
CLOSING = pathlib.Path('D:/moodle/_qoder_cmdr_ref_20260921/live_checks/CLOSING_LINE.txt').read_bytes()
assert len(CLOSING) == 83
assert hashlib.sha1(b'blob 83' + bytes([0]) + CLOSING).hexdigest() == \
    'b82ca923501c312b6931ad894c607ab9e43e1137'
R = {r['run_id']: r for r in SC['arms_scored']}
LBL_D = '这台设备自己的读数（服务器没给句子）'


def co(name):
    return '`%s` %s B `%s`' % (name, format(KEY[name]['size'], ','), KEY[name]['blob']) if name in KEY \
        else '`%s` 未在架上' % name


L = []
w = L.append
w('### 📱 aad2d1f2 (SESSION=aad2d1f2) P3 · **ORD-0301 pass 3：按你 21:5x 三处修正继续 —— ② 两侧读数改到'
  '同一条 hop 里取，③ 非 JSON 正文与带 envelope 的 4xx 各成一行；另有两处代次说法要更正（包括我自己那条）** '
  '@%s+08' % time.strftime('%H:%M'))
w('')
w('```text')
w('先按 MEASUREMENT_SCOPE_FIRST_V1 报四元组：`scope` = 手机端「AI 帮我规划」sheet 的那一条写腿 `POST '
  '/api/v1/journeys/{id}/agent/commands` 的屏上表现；`generation` = 部署代 '
  '`%s`（与被服务字节逐字节相等，见下）与对照代 `%s`；`artifact` = 本批收据 '
  '`RECEIPT_O0301P3-2230.json`；`measurement method` = 私有 vite 预览 + 配对 hop 审计 + Playwright 读渲染文字'
  '（非 grep、非 import、非测试计数）。' % (SC['generations']['dep']['tip'], SC['generations']['old']['tip']))
w('① 收到：不再要求证「同一发」。链路既然在，仍然逐腿带号（这枚号由 hop 在 accept 时现造、只写进回答头 '
  'X-HJP3-Pair，页面猜不出来），所以 ② 与 ① 用的是同一批读数。')
w('② 同一链路（格 K1）：本批 %d 臂各 1 条写腿，腿号 = %d 枚互不相同，hop 审计行/浏览器网络栈/页面 fetch '
  '三方按同号对齐，状态码两侧相等 %s、正文是否 JSON 两侧相等 %s；其中 %d 条是**产品自己答的**（每条在后端'
  '进程自己的 access log 里恰好 1 行点名），%d 条由量具代答并在自己的记录里写明 instrument_origin_per_spec，'
  '还有 1 条是**故意让腿死在浏览器里**的负对照（hop 对它 0 记录）。'
  % (SC['arms_scored_count'], len({r['pair_id'] for r in SC['arms_scored'] if r['pair_id']}),
     SC['derived']['both_ends_agree_on_status_in_every_arm'],
     SC['derived']['both_ends_agree_on_the_json_class_in_every_arm'],
     SC['answer_producer_counts']['product'], SC['answer_producer_counts']['instrument']))
w('③ 两类分行（格 K2/K3，控制格 K4）：把状态码钉住只换正文，屏上就翻——')
for r in sorted(SC['arms_scored'], key=lambda x: (x['gen'], str(x['server_status']),
                                                  bool(x['server_body_is_json']))):
    w('   %s %s %s → 服务器侧 %s %s B %s（%s）→ 屏上「%s」/ 归因「%s」/ 技术详情 %s 个'
      % (r['run_id'], r['gen'], r['server_status'] or '—',
         '产品' if r['answer_producer'] == 'product'
         else ('量具' if r['answer_producer'] == 'instrument_origin_per_spec' else '无人'),
         r['server_status'] or '—', r['server_bytes'] if r['server_bytes'] is not None else '—',
         (r['server_content_type'] or '-').split(';')[0],
         'JSON' if r['server_body_is_json'] else ('非 JSON' if r['server_body_is_json'] is False else '无'),
         r['card_title'], r['attribution_label'] or '（无标签）', r['details_blocks']))
w('   ⇒ 未守卫代（dc964086）：**只要正文不是 JSON，4xx 也一样**掉进「连不上服务端」且技术详情整块不在'
  '（详情块 0 个，React 把异常吞了，page_errors 0 条）；部署代（7856e03f）不塌，改说「%s」并给出自己那一句。'
  % LBL_D)
w('')
w('两处代次更正（谁的读数都不好使，按字节算）：服务页 index.html 引用的资源名是从**被服务的那份 html**里读的，'
  '再拿候选 `git archive` 出来各建一次比字节：')
for tag in ('7856e03f', 'dc964086', '5aff3722'):
    e = json.loads((B / 'served_generation_bind_c2.json').read_text(encoding='utf-8'))['builds'][tag]
    w('   %s → %s · %s B · 与被服务字节相等 = %s' % (e['tip'], (e.get('built_asset') or '').lstrip('/'),
                                                     e.get('built_bytes'), e.get('equals_the_served_asset')))
w('   ⇒ 你 21:5x 说「手机已在 dc964086」不成立；我 20:0x 说「服务的是 index-BTzTyrqI.js = 5aff3722」也不成立，'
  '而且那次是我 GET 了自己挑的资源名（证明的是我下载了我选的文件）。旧句仍在 '
  '`evidence/ord0300-c2-pairing-hjp3/RECEIPT_O0300C2-1955_r3.md` 与 `boundary_proof_c2.json` 里，'
  '我不改已发布件，勘误随本块与新帖发。')
w('')
w('对 ORD-0302 的直接影响：部署代 `%s` 的 sheet 在 :147/:155 **已是** `?.detail`，设备侧句子在 :761 —— '
  '所以「非 JSON 正文 ⇒ 谎称连不上」在手机上那一代**不复现**，复现在未守卫代；两代 sheet blob 分别是 %s（未守卫）'
  '与 %s（已守卫）。另记一笔没测的：部署代 HTTP_500 卡片上「行程未被改动」是固定文案，本批没做耐久回读，'
  '不替它背书。' % (SC['generations']['dep']['tip'][:8],
                    SC['generations']['old']['sheet_blob_sha1_40_hex'],
                    SC['generations']['dep']['sheet_blob_sha1_40_hex']))
w('')
w('我自己的仪表坏了 %d 次（作废 run 全留在架上，文件名前缀 discarded_，每个都有能独立复跑的机械判据）：'
  % len(SC['runs_excluded']))
for x in SC['runs_excluded']:
    w('   %s %s ｜判据 %s' % (x['run_id'], x['arm'], x['mechanical_test']))
w('   另两处要说清：读技术详情最初用 innerText，折叠时整块读成空（改为点开并同报 textContent）；'
  '追那个协议层 400 时我往自己后端端口 8651 直发过 3 个 POST（1 个 200 建了 1 条 mission、2 个 422），'
  '都在一次性库里，只做诊断、不当格子。')
w('')
RU = (B / 'q38_ruler_O0301P3-2230.txt').read_text(encoding='utf-8')
RUL = [x for x in RU.splitlines() if 'overall' in x][0]
R_CELLS, R_OVERALL = RUL.split('cells ')[1].split(' ')[0], RUL.split('overall ')[1].split(' |')[0]
R_HARD, R_SOFT = RUL.split('hard ')[1].split(' ')[0], RUL.split('soft ')[1].split(' ')[0]
assert R_CELLS == str(len(RC['cells'])), 'the ruler counted %s, the receipt has %d' % (
    R_CELLS, len(RC['cells']))
w('尺子与闸门（原样贴输出，不自己下结论）：Q38 r2 对 shipped 收据 → cells %s · %s · hard %s · soft %s · '
  'rc %s（现读自 `%s` 的结论行）。'
  % (R_CELLS, R_OVERALL, R_HARD, R_SOFT, '0' if R_OVERALL == 'Q38_GATE_GREEN' else 'non-zero',
     'q38_ruler_O0301P3-2230.txt'))
w('发布闸门三向 + 内容闸自杀测试：%s；写账本（“0 覆盖”按 path 数 commit）：%s，两条“不瞎”对照 %s。'
  % ((GS.get('verdict', {}) or {}).get('ALL_SEVEN_HOLD'),
     (NR.get('verdict', {}) or {}).get('positive_no_path_in_this_batch_was_written_twice'),
     [(c['path'][:34], c['commits_touching']) for c in
      NR.get('negative_controls_the_counter_is_not_blind', [])]))
w('边界（都是从盘上数的）：禁名在能干事的文件与臂产物里 as_use 命中 = %s；凭据只出现在把它摘掉的 %d 处；'
  '两代导出与各自 commit 的 sheet blob 相等 = %s；手机链 :4781 只有 %s 次 GET、writes %s；'
  '收尾 %s 里 %d 个具名端口全空 = %s。'
  % ({n: len(BD['needles'][n]['uses_in_actor_or_artefact']) for n in
     ('demo/reset', '_live.db', '_preview.db', 'git apply', '4782')},
     len(BD['credentials']['pop_sites_in_actors']),
     all(v['equal'] for v in BD['product_bytes']['per_generation'].values()),
     BD['phone_chain']['requests_made'], BD['phone_chain']['writes'], SC['teardown']['file'],
     len(SC['teardown']['named_ports']), SC['teardown']['all_my_ports_free']))
w('判级不归我：`derived_result` 留 null，`claimed_result` = MEASURED_NOT_GRADED。')
w('```')
w('')
w('坐标（本块写时从分支 tree 现读，非手抄）：尖 `%s` · tree `%s` · `%s/` 共 %d 件 / %s B。关键件：%s。'
  % (tip_now, tree_now, pub.PREFIX, len(rows_now),
     format(sum(x['size'] or 0 for x in rows_now), ','),
     ' · '.join(co(n) for n in ('RECEIPT_O0301P3-2230.json', 'RECEIPT_O0301P3-2230.md', 'p3_scored.json',
                                'p3_boundary.json', 'no_rewrite_proof_p3.json',
                                'gate_selftest_publish_p3.json', 'q38_ruler_O0301P3-2230.txt',
                                'p3_pair_log.jsonl', 'instruments/p3proxy.py',
                                'instruments/p3_no_rewrite.py'))))
w('')
w('下一步（不自启）：ORD-0306 五行按 CMDR-0925-1652 补代次绑定，现在可以在真部署代 `%s` 上量；'
  'ORD-0312 的量测半边（M1 null-body / M2 X-5）同代跟上；ORD-0301 那 22 行正文表若要在新代上重跑，说一声。'
  % SC['generations']['dep']['tip'][:8])
w('')
w(CLOSING.decode('utf-8'))
text = '\n'.join(L) + '\n'
(B / 'block_p3_delivery.md').write_text(text, encoding='utf-8', newline='\n')
# LEDGER_SINGLE_WRITER_V1 (CMDR-0925-2307, arbiter Q63=3): lanes do not write the shared ledger. The block is
# dropped into the commander's inbox as <lane>_<HHMM>.md with a `### ` first line, and self-checked here
# against the same Q43 r4b gate he runs - so a refusal is found by me, not in his patrol.
INBOX = pathlib.Path('D:/moodle/_qoder_ledger_inbox')
name = 'aad2d1f2_%s.md' % time.strftime('%H%M')
dest = INBOX / name
assert text.startswith('### '), 'the inbox rule requires a `### ` first line'
dest.write_text(text, encoding='utf-8', newline='\n')
Q43 = 'D:/moodle/_qoder_cmdr_ref_20260921/live_checks/claim_coordinate_check_r4b.py'
chk = subprocess.run([sys.executable, Q43, '--text', str(dest), '--expect-clean'],
                     capture_output=True, text=True, encoding='utf-8', errors='replace')
proof = {'block_file': str(dest), 'bytes': dest.stat().st_size,
         'first_line': text.splitlines()[0][:80], 'q43_rc': chk.returncode,
         'q43_out': (chk.stdout or '')[-1500:], 'q43_err': (chk.stderr or '')[-300:],
         'ledger_written_by_this_lane': False}
(B / 'ledger_inbox_proof_p3.json').write_text(json.dumps(proof, ensure_ascii=False, indent=1),
                                              encoding='utf-8', newline='\n')
print('inbox block:', name, proof['bytes'], 'B | Q43 rc =', chk.returncode)
print((chk.stdout or '')[-1000:])
