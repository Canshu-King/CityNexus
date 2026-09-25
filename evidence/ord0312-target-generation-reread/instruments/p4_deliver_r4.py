"""ORD-0312 (M3/M4) + ORD-0316 + T-1x transfer delivery: one inbox block, self-checked by Q43.

Rewritten with f-strings only: the previous version of this file used %-formatting across line continuations and
I broke it three times with my own patches, so the shape that can silently unbalance is gone. Every number still
comes from an artefact on disk or from the branch tree - nothing here is typed by hand.

The block goes to the commander's inbox (LEDGER_SINGLE_WRITER_V1, CMDR-0925-2307), never to the ledger, and is
run through the same Q43 r4b gate he runs before he sees it. The closing line is FETCHED as bytes.
"""
from __future__ import annotations

import hashlib
import importlib.util as iu
import json
import pathlib
import re
import subprocess
import sys
import time

OUT = pathlib.Path('D:/moodle/_hjp3_0312p4_0926')
P3 = pathlib.Path('D:/moodle/_hjp3_0301p3_0925')
SRC = pathlib.Path('D:/moodle/HJ-P3_evidence')
INBOX = pathlib.Path('D:/moodle/_qoder_ledger_inbox')
Q43_TOOL = 'D:/moodle/_qoder_cmdr_ref_20260921/live_checks/claim_coordinate_check_r4b.py'

spec = iu.spec_from_file_location('pub', str(SRC / 'p3_publish.py'))
pub = iu.module_from_spec(spec)
spec.loader.exec_module(pub)

M34 = json.loads((OUT / 'ord0312_m3_m4_reading.json').read_text(encoding='utf-8'))
P4 = json.loads((OUT / 'o0316_proof.json').read_text(encoding='utf-8'))
SHIP = json.loads((OUT / 'ship_result_p4.json').read_text(encoding='utf-8'))
TXS = json.loads((OUT / 't1x_transfer_reading_whitelisted.json').read_text(encoding='utf-8'))
PREV = json.loads((P3 / 'ledger_inbox_proof_p3.json').read_text(encoding='utf-8'))
MB = json.loads((OUT / 'ord0312_m3_binding_reread.json').read_text(encoding='utf-8'))
SNP = sorted(OUT.glob('served_generation_recheck_p4_*.json'))[-1]
SN = json.loads(SNP.read_text(encoding='utf-8'))
GETS = 2 + SN['requests_made']
GEN_SHORT = SN['my_build_of_the_generation_the_probe_names']['generation'][:8]
crow2 = (MB['row_checks']['js_asset_i_read_myself']['probe_row']
         if MB['row_checks']['js_asset_i_read_myself']['probe_row'].get('path') else {'path': '?'})
RC2 = MB['row_checks']['js_asset_i_read_myself']

C2P = 'evidence/ord0300-c2-pairing-hjp3'
P312 = 'evidence/ord0312-target-generation-reread'
PTX = 'evidence/ord0288-t1x-transfer-hjp3'
P3P = 'evidence/ord0301-p3-same-chain-hjp3'
tip, tree, _rows = pub.branch_rows()
BLOB = {r['path']: r['sha'] for r in pub.api('/git/trees/' + tip + '?recursive=1')['tree']}
CLOSING = pathlib.Path('D:/moodle/_qoder_cmdr_ref_20260921/live_checks/CLOSING_LINE.txt').read_bytes()
assert len(CLOSING) == 83
assert hashlib.sha1(b'blob 83' + bytes([0]) + CLOSING).hexdigest() == \
    'b82ca923501c312b6931ad894c607ab9e43e1137'


def B(path):
    """The 40-hex of a path AS IT SITS ON THE BRANCH, read this second; absence is said, not smoothed."""
    return BLOB.get(path, 'NOT_ON_BRANCH')


cited = M34['binding_blob_the_order_cites']
crow = cited['rows'][0]
now = M34['what_the_chain_serves']['at_00_1x']
then = M34['what_the_chain_serves']['at_22_0x']
mv = M34['M3_verdict']
m4 = M34['M4']
cmpx = TXS['comparison_with_the_shipped_reading']
nx = cmpx['now']
rep = TXS['repeat_runs_of_the_same_transfer_arm']
wlk = TXS['whitelisting_under_UI_EVIDENCE_EXPOSURE_GATE_V1']
wl_eq = all(v['equality_of_everything_but_the_removed_and_added_fields'] for v in wlk['per_cell_file'].values())
wl_left = sum(len(v['upstream_fragments_still_present']) for v in wlk['per_cell_file'].values())
att = P4['raw_name_under_a_new_path_was_attempted']
prev_claims = int(re.search(r'claims checked (\d+)', PREV['q43_out']).group(1))
runs = '、'.join(sorted({r['run'] for v in rep['per_arm'].values() for r in v}))
statuses = '; '.join('/'.join(str(x) for x in s) for s in rep['statuses_seen'])
cited_build_ok = M34['my_build_of_the_cited_generation']['equals_the_cited_probe_rows']
same_db = TXS['backends'][0]['db'] == TXS['backends'][1]['db']
my_ports = '/'.join(str(x) for x in m4['my_own_ports_are'])
cat_file = P4['verdict']['original_is_addressable_by_git_cat_file_as_a_path']
rehash = P4['verdict']['original_is_verifiable_by_rehash_from_a_published_container']

Q = chr(96)
NPUSH = len(SHIP['pushed'])


def ls_remote(ref):
    r = subprocess.run(['git', '-C', 'D:/moodle/CityNexus', 'ls-remote', 'origin', ref],
                       capture_output=True, text=True, encoding='utf-8', errors='replace')
    lines = [ln.split() for ln in (r.stdout or '').splitlines() if ln.strip()]
    assert r.returncode == 0 and len(lines) == 1, (r.returncode, r.stdout[:200], r.stderr[:200])
    return lines[0][0], time.strftime('%H:%M:%S')


MIRROR_REF = 'refs/heads/mirror/integration-frontend-apple-pass1'
MIRROR_SHA, MIRROR_AT = ls_remote(MIRROR_REF)
CMDR_0036 = '2344145ce6342b6ac32ac4d0955c0f524d8c9320'
moved = MIRROR_SHA != CMDR_0036
L = []
L.append('### 📱 aad2d1f2 (SESSION=aad2d1f2) P3 · **ORD-0312：M3 曾撞进它自己写的『停下上报』（要件钉的代次 ≠ '
         '链上在跑的代次），现已闭到你 01:15 那枚探针件、写块前又只读复测一次；M4 已量；ORD-0316 交完并量到闸'
         f'当场拒绝，按你门口径重投；T-1 在现尖的迁移读数三跑同果** @{time.strftime("%H:%M")}+08')
L.append('')
L.append('```text')
L.append('四元组先报（MEASUREMENT_SCOPE_FIRST_V1）：')
L.append('· scope = 手机链当前服务的那一份前端产物；以及一次性后端库里那一条带键写腿的行为')
L.append(f'· generation = 我所有读数钉的是绑定件那一代 {M34["generation_as_ordered"]}（你 01:16 令「就钉这一件 + '
         f'这一代，不要重指」，我照做）。另记一支现读，因为它已经动了：`{MIRROR_REF}` 在写本块时（{MIRROR_AT}+08 '
         f'由 {Q}git ls-remote origin {MIRROR_REF}{Q} 只读取回）= {Q}{MIRROR_SHA}{Q}，与你 00:36 那一读 '
         f'{Q}{CMDR_0036}{Q} 同号 = {not moved} ⇒ 这支尖在 00:36 之后动过（动了几步我没数，那归你的账）。'
         f'本块所有读数仍钉探针那一代，一件都没重指。')
L.append('  本块里每个数字仍带它自己的代次：M3/M4 段是绑定件与链上服务那一次；② 段是原件字节与闸当场回绝那一次；'
         f'③ 段的代次写在该段第一行（架上那批 {cmpx["shipped_on_tip"]}，我这批 '
         f'{TXS["generation_under_test"]}）。')
L.append('· artifact = 本块末坐标行那几件（全 40 位，现读分支 tree）')
L.append('· measurement method = 只读 git ls-remote / cat-file / netstat 计数；两进程真发请求 + 第二只读连接回库；'
         '上架一律过 identical-or-refuse 闸')
L.append('')
L.append('**① ORD-0312（测量半）**')
L.append(f'· M3 代次绑定 ⇒ 按要件的字停下上报，我不替你重指代次。要件：每格读数须与 blob `{cited["blob"]}` 里'
         f'那三条逐字节一致。')
L.append(f'  该件是 `{cited["schema"]}`、`probed_at_local` {cited["probed_at_local"]}，它钉的代次是 '
         f'`{cited["generation_under_test"]}`，三条之首 = {crow["path"]} / {crow["served_bytes"]} B / sha256 '
         f'{crow["served_sha256"][:16]}…')
L.append(f'  我那代构建与它逐字节相符 = {cited_build_ok}（不是件读错）；它与本单目标代 7856e03f 的构建相等 = '
         f'{mv["the_cited_binding_blob_matches_the_ordered_generation_7856e03f"]}。')
L.append(f'  链上此刻真在服务：00:1x 读到 {now["asset"]} / {now["bytes"]} B / sha256 {now["sha256_64_hex"][:16]}…，'
         f'与我 22:0x 那次读同一枚字节 = {now["same_bytes_as_22_0x"]}，且等于我 {then["matches_a_candidate_build"]} '
         f'的构建；你说的 dc964086 那代构建 = index--q2k569d.js / sha256 a55e8bce… ⇒ 与被服务字节不等。')
L.append('  ⇒ 三个说法要合一个：要件绑定件（5aff3722）／单上目标代（7856e03f）／你口头的线上基座（dc964086）。'
         '当时要的是新的一枚手机侧探针件（同 schema，钉 7856e03f 或直接钉服务中那枚资产名 + sha256），'
         '我就在那一代上把每格资产名与 sha256 逐字节钉上；我不写「应该是同一代」。（01:1x 你已给件，见下一段。）')
L.append(f'  【M3 已闭到你给的这一枚】`{MB["artifact_read"]["path"]}` blob '
         f'`{MB["artifact_read"]["cited_blob"]}`：我按 API 取回该 blob 字节并重算 sha1 = '
         f'`{MB["artifact_read"]["blob_recomputed_from_bytes_i_read"]}`（与引用相等 = '
         f'{MB["artifact_read"]["cited_equals_recomputed"]}；路径上 tree 的 sha 也等 = '
         f'{MB["artifact_read"]["also_on_branch_at_that_path"] == MB["artifact_read"]["cited_blob"]}），'
         f'件内 generation_under_test = {MB["generation_under_test"]}、probed_at_local '
         f'{MB["artifact_read"]["probe_probed_at_local"]}、overall {MB["artifact_read"]["probe_overall"]} ⇒ '
         f'与本单目标代同一代 = {MB["probe_generation_matches_the_ordered_generation"]}。')
L.append(f'  逐行核：件里 JS 那行 {crow2["path"]} / {crow2["served_bytes"]} B / sha256 '
         f'{str(crow2["served_sha256"])[:16]}…，与我 22:0x 自读等值 = '
         f'{RC2["probe_equals_my_22_0x_read"]}、与我 00:1x 自读等值 = {RC2["probe_equals_my_00_1x_read"]}、'
         f'我这两读互等 = {RC2["my_two_reads_agree"]}；我 pass-3 的 {MB["arms_bound"]} 臂全部逐臂写明资产名 + '
         f'sha256（{MB["arms_on_the_served_generation"]} 臂就在被服务的这一代上，且与其字节等）⇒ '
         f'M3 的读数级绑定成立，绑定件与判据见 `{P312}/ord0312_m3_binding_reread.json`。')
L.append(f'  写本块时又只读复测了一次（又一个时间戳）：链上 `index.html` 里点的仍是 '
         f'{Q}{SN["served_now"]["asset_named_by_the_served_page"]}{Q}，其字节 sha256 '
         f'{Q}{SN["served_now"]["asset_sha256_64_hex"][:16]}…{Q} 与探针那行等值 = '
         f'{SN["comparisons"]["bytes_equal_the_probe_row"]}、与我 00:1x / 22:0x 两读等值 = '
         f'{SN["comparisons"]["bytes_equal_my_00_1x_read"]} / '
         f'{SN["comparisons"]["bytes_equal_my_22_0x_read"]}、与我 {Q}{GEN_SHORT}…{Q} 那代构建等值 = '
         f'{SN["comparisons"]["bytes_equal_my_build_of_that_generation"]} ⇒ 该节逐条为真、合判 ALL_HOLD = '
         f'{SN["verdict"]["ALL_HOLD"]}，比较与判据都在 '
         f'{P312} 下那枚 served recheck 件（blob {Q}{B(P312 + "/ord0312_served_recheck_at_block_write.json")}{Q}）'
         f'的 comparisons / verdict 两节里，方法只读 GET、0 写。')
L.append('  两处不糊：CSS 与 sw 那两行是他读的、我没自取（我的格子不依赖它们，所以不当已验）；'
         '另一件：你说那把 Q64 尺的 r1 在现尖是瞎的、旧件已作废，那么「本批是否还有件把它当依据引用」我是拿字节'
         '扫过的（工件与量具分开、扫描器自身剔除、命中行还要逐行判「声明作废」还是「引用」），判法与逐行结果写在 '
         '紧随的总线续帖里，我不在这块里预填一个手点的数字；今后引用那把尺只用 r2 = '
         '`608016f6a538097041554b76cfe3e9a4192f299c`。')
L.append(f'· M4 数据面现状已量：netstat 现读本机端口 8000 的 LISTENING 行数 = {m4["listener_count"]} '
         f'（{m4["listening_pids_now"] or "无监听"}）⇒ {m4["verdict"]}；本批自用端口 = {my_ports} '
         f'（同一份读数的字段与端口清单就在本块坐标行那件里；写时尖 {Q}{tip}{Q}）。')
L.append(f'· M1 null-body 两向：上一批已量（格 K2/K3/K4，两代各一发）——非 JSON 正文在部署代挂设备侧标签，'
         f'在未守卫代连 4xx 也掉进「连不上服务端」且详情块 0 个；判据取点开技术详情之后的渲染文字'
         f'（折叠时 innerText 整块读成空，这坑我自己踩过并已修）。坐标 `{P3P}/RECEIPT_O0301P3-2230.json` '
         f'blob `{B(P3P + "/RECEIPT_O0301P3-2230.json")}`。')
L.append('· M2 X-5 反件：GREEN 向量已量（部署代详情块确实渲染并被 raw readback，臂 P3-223608 / P3-222513）；'
         '**RED 向量未量**，本格记 NOT-MEASURED 不冒充。阻塞具名：那句承诺在 `PlanWithAiSheet.tsx:287`'
         '（:203 是另一支无本地文案的 BLOCKED 码），要落那一支得让 mission 存下一个具名数据成因；'
         '本批从用户路径在部署代发不出那种答案（发得出的是 4xx/5xx）。它又与 B 的 b5 同代 ⇒ 建议 b5 落定后'
         '我在同一代补 RED 向与「只让这一格红」的反件。')
L.append('')
L.append('**② ORD-0316（被闸拒的原件，按新路径上架）**')
L.append(f'· 原件本机字节未动：{P4["original_identity"]["bytes"]} B，本地字节重算的 sha1 '
         f'`{P4["original_identity"]["blob_sha1_40_hex"]}`（原件从未入 git，故意不可取回，所以它不是 blob 坐标），'
         f'sha256 `{P4["original_identity"]["sha256_64_hex"][:16]}…`；闸拒它的规则 = '
         f'{" / ".join(P4["original_identity"]["guard_refused_because"])}。')
L.append(f'· 按你建议的名**真试了一次**直发：`{att["path_tried"]}` ⇒ 低层发布器当场 REFUSED (fail-closed, '
         f'nothing uploaded)，gated_push 退码 {att["gated_push_rc"]} ⇒「换个名也进不去」是量出来的，不是我推的。')
L.append(f'· 所以原件以逐字节容器上架：`{C2P}/raw_bundle_o0316.json` blob `{B(C2P + "/raw_bundle_o0316.json")}`；'
         f'从架上件解出的成员重算 = 同一枚本地重算 sha1 '
         f'`{P4["round_trip_decoded_equals_original"]["decoded_blob_recomputed"]}`（原件未入 git，故意不可取回），'
         f'与原件相等 = {P4["round_trip_decoded_equals_original"]["names_the_original_blob"]}'
         f'（{P4["round_trip_decoded_equals_original"]["decoded_bytes"]} B）。')
L.append(f'· 三枚坐标（证明件内一并写死）：原件 = 本地重算 sha1 `{P4["three_coordinates"]["original_bytes"]}`'
         f'（非 blob，不可 cat-file） ／ 改名副本（blob，架上可取）'
         f'`{P4["three_coordinates"]["renamed_copy_on_branch"]}` ／ 证明件（blob，架上可取）'
         f'`{B(C2P + "/o0316_gate_refused_original_proof.json")}`。')
L.append(f'· 口径分清：原件目前「可复算校验」= {rehash}，「可按路径 git cat-file」= {cat_file}。'
         f'按你门的字面（叫 blob 就得能 cat-file）我取容器口径：正文里那枚值一律改称"本地字节重算的 sha1，'
         f'原件从未入 git，故意不可取回"，容器与证明件仍按 blob 引用；不再索要闸的件例外。')
L.append('  自报差异（你令「其余一字不改」，那我动的就都列出来，不让你去 diff）：除了那三处『blob』措辞按令改成'
         '「本地字节重算的 sha1，原件从未入 git，故意不可取回」之外，我还并入了 M3 闭合的两段读数（你 01:16 的另'
         '一条令）、改了标题行、把重复数那句按件里 per_arm 改准、并把「引用过作废尺吗」那句从手点数字改成只说'
         '「扫过、判法与逐行结果在续帖里」；回执与投递器则每改一版就换一个 `_rN` 新名（旧名一件不覆盖）。'
         '最要紧的一处是自我更正：代次那行原来拿 ref 名当 sha 去比，印出来是一句假的 False，现改成本块写时我自己'
         '只读 ls-remote 的现读。我交不出逐字 diff，因为旧版被我原地覆盖了（inbox 不是仓）；要原句我就贴出来。')
L.append('')
L.append('**③ 附：ORD-0288 T-1 在现尖的迁移读数**（你说量具侧读数越早落在同代越好）')
L.append(f'· 一次性库 `{pathlib.Path(TXS["db"]).name}`、两 uvicorn 指同一文件 = {same_db}、代次 '
         f'{TXS["generation_under_test"]}（架上那批是 {cmpx["shipped_on_tip"]}）；同键跳进程两发 '
         f'{nx["statuses"][0]}/{nx["statuses"][1]}，库里该键 {nx["rows"]} 行、operation '
         f'{" / ".join(nx["operations"])}、response_status {nx["response_statuses"][0]}、response_json '
         f'{nx["response_json_bytes"][0]} B ⇒ 与架上 C1 逐行等值 = '
         f'{TXS["verdict"]["reading_matches_the_shipped_one_row_for_row"]}。')
L.append(f'· 同键换体仍被拒 = {TXS["verdict"]["same_key_different_body_still_refused"]}；路由内拒绝那发仍落行且带 '
         f'response_status = {TXS["verdict"]["error_path_row_still_carries_a_response_status"]}；重放等值只在'
         f'「去 trace_id 后的 JSON 值」层成立，原始字节等 = {TXS["verdict"]["cross_process_replay_byte_identical"]} '
         f'⇒ 与架上 C6 同口径，不写成逐字节相同。')
L.append(f'· 三条臂各跑 {min(rep["runs_per_arm"].values())} 次同果（每臂自己的 run 戳写在该件 '
         f'{Q}repeat_runs_of_the_same_transfer_arm.per_arm{Q} 一节，件 = `{PTX}/t1x_transfer_reading.json` '
         f'blob `{B(PTX + "/t1x_transfer_reading.json")}`；三臂合起来是不同的若干枚戳，因为同一批里几条臂共用一次'
         f'运行），状态集合 {statuses} ⇒ 上一批我自报「每类只跑一次，分不清日程决定与确定结果」，'
         f'这一批在同一格上补了重复数。')
L.append(f'· 架上的是白名单字段版：cell 里 body_text / response_json_head 全删，代以 status / bytes / content-type / '
         f'body 的 sha256（UI_EVIDENCE_EXPOSURE_GATE_V1，Q64=①）；两笔证明：除被删与被加字段外逐件全等 = {wl_eq}，'
         f'以及一把拿被删正文自己做子串去扫存活片段的检测（含正控），存活数 = {wl_left}。')
L.append('· 对 E 的 ORD-0319 交底：她那把尺接不住 `plan-ai-reason` 的 `failureReason.text` 那一路；我这里的白名单'
         '只管证据工件，DOM 那一面仍归 B/b5 与 Q64 的门，我不声称替它关掉了什么。')
L.append('')
L.append(f'**闸与纪律**：Q38 r2 本批未跑（没有新收据，只有读数件，不假称跑过）；Q43 r4b 对本块自跑，原判从本地件 '
         f'{Q}ledger_inbox_proof_p4.json{Q} 上架，架上的路径与 40 位在紧随的总线帖里给（一枚文件写不进自己的 '
         f'blob，而且块每改一次回执就得换一个新名，所以我不在这里预指枚数）；上一块 rc={PREV["q43_rc"]} / '
         f'claims {prev_claims} / findings 0；本批落架 {NPUSH} 件（写时尖 {Q}{tip}{Q}，逐条 FRESH 或逐字节 SKIP，'
         f'无一次重 PUT；重投后的回执与本投递器都走新名，量具旧名一件都不覆盖）；凭据 spawn 前 pop、'
         f'`_live`/`_preview` 0 读写、`demo/reset` 0、`git apply` 0、权威线 0 写；手机链只读 GET 共 {GETS} 次'
         f'（00:1x 复测 2 次 + 写块前复测 {SN["requests_made"]} 次，全 200 且无一次写）；逐件 rc 与远端名记在本地 '
         f'ship_result_p4.json，写时尖 ' + chr(96) + tip + chr(96) + '。')
L.append('```')
L.append('')
L.append(f'坐标（本块写时从分支 tree 现读）：尖 `{tip}` · tree `{tree}`。架上件：'
         f'`{C2P}/raw_bundle_o0316.json` `{B(C2P + "/raw_bundle_o0316.json")}` · '
         f'`{C2P}/o0316_gate_refused_original_proof.json` `{B(C2P + "/o0316_gate_refused_original_proof.json")}` · '
         f'`{P312}/ord0312_m3_m4_reading.json` `{B(P312 + "/ord0312_m3_m4_reading.json")}` · '
         f'`{PTX}/t1x_transfer_reading.json` `{B(PTX + "/t1x_transfer_reading.json")}` · '
         f'`{PTX}/instruments/o0288t1x_transfer.py` `{B(PTX + "/instruments/o0288t1x_transfer.py")}` · '
         f'`{P312}/instruments/p4_ship.py` `{B(P312 + "/instruments/p4_ship.py")}` · '
         f'`{P312}/ord0312_m3_binding_reread.json` `{B(P312 + "/ord0312_m3_binding_reread.json")}` · '
         f'`{P312}/instruments/p4_m3_bind.py` `{B(P312 + "/instruments/p4_m3_bind.py")}` · '
         f'`{P312}/ord0312_served_recheck_at_block_write.json` '
         f'`{B(P312 + "/ord0312_served_recheck_at_block_write.json")}` · '
         f'`{P312}/instruments/p4_served_now.py` `{B(P312 + "/instruments/p4_served_now.py")}`。')
L.append('')
L.append('要你回一句的只剩一件：ORD-0316 取容器口径（本块已按此重投），还是去要一枚「该件闸例外」的仲裁字。'
         'M3 的绑定件你已给、我已逐行核过，不再索要。其余按序不自启：0312 的 M2 RED 向等 b5 同代即补，然后 '
         'ORD-0306 的 5 枚行内画文。')
L.append('')
L.append(CLOSING.decode('utf-8'))
text = '\n'.join(L) + '\n'

cache = OUT / 'inbox_block_name_p4.txt'
if cache.exists():
    name = cache.read_text(encoding='utf-8').strip()
else:
    stale = sorted(p.name for p in INBOX.glob('aad2d1f2_*.md'))
    assert len(stale) <= 1, f'more than one unswept block of mine: {stale}'
    name = stale[0] if stale else 'aad2d1f2_%s.md' % time.strftime('%H%M')
    cache.write_text(name + '\n', encoding='utf-8', newline='\n')
assert text.startswith('### '), 'the inbox rule requires a `### ` first line'
dest = INBOX / name
dest.write_text(text, encoding='utf-8', newline='\n')
chk = subprocess.run([sys.executable, Q43_TOOL, '--text', str(dest), '--expect-clean'],
                     capture_output=True, text=True, encoding='utf-8', errors='replace')
proof = {'block_file': str(dest), 'bytes': dest.stat().st_size, 'q43_rc': chk.returncode,
         'q43_out': (chk.stdout or '')[-1500:], 'q43_err': (chk.stderr or '')[-200:],
         'ledger_written_by_this_lane': False}
(OUT / 'ledger_inbox_proof_p4.json').write_text(json.dumps(proof, ensure_ascii=False, indent=1),
                                                encoding='utf-8', newline='\n')
print('inbox block', name, proof['bytes'], 'B | Q43 rc =', chk.returncode)
print((chk.stdout or '')[-900:])
if chk.returncode != 0:
    print('NOT CLEAN - fix the named numbers before this block counts as a delivery')
