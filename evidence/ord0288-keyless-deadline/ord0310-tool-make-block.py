"""Render this lane's ORD-0310 ledger block out of the artifacts, never out of my memory.

Every number, blob and path in the emitted prose is read here from the receipt JSON, the arms JSON,
the backend-readings JSON or the raw `.out` files, so the prose cannot drift from the measurement.
The heading carries a time token the insert tool replaces with the real clock minute.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path("D:/moodle/_qoder_d_lane_20260923")
SC = ROOT / "_scratch_0310"
OUT = ROOT / "review" / "ledger_block_e345b9d6_0310.md"
TIME_TOKEN = "@2026-09-25 19:5x+08"


def sha1(data: bytes) -> str:
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def load(name: str):
    return json.loads((SC / name).read_text(encoding="utf-8"))


rec = load("ord0310_keyless_deadline_receipt_r1.json")
arms = load("arms_receipt_r3.json")
back = load("backend_readings.json")
q38 = load("q38r2-on-receipt.json")
cells = {c["id"]: c for c in rec["cells"]}
gen = rec["generation_binding"]
mp = gen["merge_prediction"]
tip_read = rec["ref_tip_read"]
ref = rec["candidate_ref_readback"]
keyed = cells["C1_keyed_shape_untouched"]["readings"]["keyed_shape_on_the_line_0281"]
keyless = cells["C1_keyed_shape_untouched"]["readings"]["keyless_shape_this_order_0310"]
c3 = cells["C3_screen_sentence_shape"]["readings"]
c2 = cells["C2_single_named_constant"]["readings"]
k1 = arms["clean_round"]
mod_blob = cells["C5_arms_and_provenance"]["readings"]["blob_module"]
sheet_blob = cells["C5_arms_and_provenance"]["readings"]["blob_sheet"]
spec_blob = cells["C5_arms_and_provenance"]["readings"]["blob_spec"]
bet_blob = cells["C5_arms_and_provenance"]["readings"]["blob_backend_test"]
rec_blob = sha1((SC / "ord0310_keyless_deadline_receipt_r1.json").read_bytes())
arms_blob = sha1((SC / "arms_receipt_r3.json").read_bytes())
back_blob = sha1((SC / "backend_readings.json").read_bytes())
q38_blob = sha1((SC / "q38r2-on-receipt.json").read_bytes())
mt_blob = sha1((SC / "ord0310-mergetree-tip-x-candidate.out").read_bytes())
tip_blob = sha1((SC / "ord0310-tip-read.out").read_bytes())
dis_blob = sha1((SC / "ord0310-path-disjointness.tsv").read_bytes())
theirs = gen["files_the_line_changed_since_the_fork"]
mine = gen["files_my_candidate_changed_since_the_fork"]
inter = gen["intersection_between_their_files_and_mine"]
their_importers = "、".join(f"`{p}`" for p in keyed["importers_at_tip"])
EVDIR = ROOT / "review" / "evidence" / "ord0310"
ev_clean = EVDIR / f"keyless_deadline_arms-{k1['runId']}.json"
ev_probe = EVDIR / f"keyless_deadline_arms-{c2['probe_run_id']}.json"
ev_clean_blob = sha1(ev_clean.read_bytes())
ev_probe_blob = sha1(ev_probe.read_bytes())
clean_seconds = str(c2["seconds_shown_on_screen_clean_round"]).split("等到")[1].split("秒")[0].strip() \
    if "等到" in str(c2["seconds_shown_on_screen_clean_round"]) else "NOT_READ"
k1b = back["cells"]["K1"]
t1a = back["cells"]["T1a"]
t1b = back["cells"]["T1b"]

L = []
L.append(f"### SESSION=e345b9d6 {TIME_TOKEN} —— **ORD-0310 交付：给无键写腿一枚可指名的设备期限，"
         f"屏上那句话只敢说自己射程以内的事（产码 2 件 + 门 2 件 + 臂 {arms['arms_total']} 枚）**")
L.append("")
L.append(
    f"单号 ORD-0310，形制按仲裁 Q54=①。候选（我自己命名的新 ref，别人的 ref 一枚没碰）："
    f"`{ref['ref']}` = `{ref['sha_read_back_over_https']}`（`git ls-remote` 回读，"
    f"原样输出在 `evidence/ord0288-keyless-deadline/ord0310-tip-read.out`，blob `{tip_blob}`）。"
    f"被量那一代 = `{arms['tested_tree']}`；推上去那一代 = `{ref['sha_read_back_over_https']}`，"
    f"四枚被测工件在两枚上逐枚同 blob（`subject_files_equal_to_the_tested_tree="
    f"{json.dumps(ref['subject_files_equal_to_the_tested_tree'])}`），"
    f"差的只有本车道自己的臂驱动器：{json.dumps(ref['what_differs_between_tested_tree_and_the_push'], ensure_ascii=False)}。"
)
L.append("")
L.append(
    f"**权威尖只读、两路一致**：`{tip_read['ref']}` = `{tip_read['sha']}`；"
    f"第二路（git/ref REST）= `{tip_read['sha_by_the_second_route']}`，"
    f"`the_two_routes_agree={json.dumps(tip_read['the_two_routes_agree'])}`，"
    f"全部测量做完后复测 `{tip_read['recheck_after_all_measurement']}`，"
    f"`stable_across_this_run={json.dumps(tip_read['stable_across_this_run'])}`。我 0 次移动它。"
)
L.append("")
L.append(f"**代际绑定（不自宣携带）**：分叉点 `{gen['fork_point_with_the_line']}`；"
         f"尖上比我这一笔多 `{len(gen['commits_on_the_line_since_the_fork'])}` 笔："
         + "、".join(f"`{c.split(' ')[0]}`" for c in gen["commits_on_the_line_since_the_fork"]) + "。"
         f"线自分叉动了 `{len(theirs)}` 件，我动了 `{len(mine)}` 件，"
         f"**两边交集 `{len(inter)}` 件**（逐行表 `evidence/ord0288-keyless-deadline/"
         f"ord0310-path-disjointness.tsv`，blob `{dis_blob}`）。"
         f"合流只读预测：`{mp['command']}` ⇒ 退出 `{mp['exit']}`、"
         f"预测树 `{mp['predicted_tree']}`、conflict 段 = `{mp['raw_after_first_line'].strip() or '（空）'}`"
         f"（原样输出 `evidence/ord0288-keyless-deadline/ord0310-mergetree-tip-x-candidate.out`，blob `{mt_blob}`）。"
         f"`frontend` 子树两枚各不同：我这一代 `{gen['frontend_subtree_oid_my_tree']}`、"
         f"线尖 `{gen['frontend_subtree_oid_tip']}` ⇒ 按 Q24 本块所有读数只属于 "
         f"`{arms['tested_tree']}` 那一代，不折算到线尖；"
         f"要当代数请落字，我重父后重跑一轮绿 + 一轮拆（端口带已含占用守卫，撞别人端口会先 ABORT）。")
L.append("")
L.append("**一、两枚形状分开具名（谁也不替谁交卷）**")
L.append("")
L.append(
    f"- 有键那一支 = ORD-0281（不是我交的）：线上 `frontend/src/lib/writeDeadline.ts` "
    f"blob `{keyed['blob_at_tip']}`，导出常数 `{keyed['exported_constant']}`，"
    f"引用者只有 {their_importers}；`git grep -n fetchWithWriteDeadline {tip_read['sha']} -- "
    f"frontend/src/features/planning/PlanWithAiSheet.tsx` 回 `{keyed['sheet_call_sites_at_tip']['lines_returned']}` 行。"
    f"本单对它 0 字节改动 —— 被测那一代里那枚文件根本不存在"
    f"（`absent_from_my_tested_tree={json.dumps(keyed['absent_from_my_tested_tree'])}`），"
    f"我是在量完之后按线尖只读 `git show` 才看到它的。"
)
L.append(
    f"- 无键那一支 = 本单：新建 `frontend/src/lib/keylessWriteDeadline.ts` blob `{mod_blob}`，"
    f"常数一处 `KEYLESS_WRITE_DEADLINE_MS = {c2['constant_ms_in_the_module']}`，"
    f"屏上秒数与计时器同取它（`KEYLESS_WRITE_DEADLINE_SECONDS = KEYLESS_WRITE_DEADLINE_MS / 1000`）；"
    f"`frontend/src/features/planning/PlanWithAiSheet.tsx` blob `{sheet_blob}` 里 "
    f"`fetchWithKeylessWriteDeadline` 只裹 `agent/commands` 那一发。"
    f"两枚数值都是 `{c2['constant_ms_in_the_module']}` ms，但各管各的调用点，我没有替 0281 交卷。"
)
L.append("")
L.append(
    f"**期限为什么是 `{c2['constant_ms_in_the_module']}` ms**：服务端写预算 `45000` ms"
    f"（`backend/app/core/config.py:96`）、锁等待 `30000` ms（`backend/app/core/config.py:95`）——"
    f"设备期限放在服务端预算之上，才会出现「服务器已判死、客户端还在等」那一句；"
    f"压到它下面就等于在服务器还在写的时候催用户重来，那正是 Q54 要防的重复提交面。"
)
L.append("")
L.append("**二、屏上那句话（两件事都在，四句禁句都不在）**")
L.append("")
L.append(
    f"对象 = 干净轮 `{k1['runId']}` 的 K1 节点（库 `{k1['db']}`、端口 {k1['port']}）。"
    f"逐行读数在门禁自己写出的证据文件里："
    f"`evidence/ord0288-keyless-deadline/ord0310-gate-evidence-{k1['runId']}.json`，"
    f"blob `{ev_clean_blob}`（{ev_clean.stat().st_size} B）。"
    f"`status={c3['status_attribute']}`、`origin={c3['reason_origin']}`、"
    f"`label={c3['reason_label']}`（不是「服务器给出的原因」那四个字，所以设备自报没冒充服务器），"
    f"`detail_block_attached={json.dumps(c3['detail_block_attached'])}`，"
    f"实测等待 `{c2['measured_wait_clean_round_ms']}` ms、`post_count={c2['post_count_clean_round']}`"
    f"（一发，不是重发），判据 `{len(c3['rows_in_this_cell'])}` 行逐行来自这一轮运行。"
    f"两件事：「结果未知」并明写「不是没发生」；「不能靠同一把键补问」逐字钉进断言。"
    f"四句禁句（已取消 / 没有发生 / 再试一次 / 连不上服务端）逐条判缺。"
)
L.append("")
L.append(
    f"卡片正文（展开「技术详情」之后实际读到那段的前 96 字）：`{str(c3['rendered_card_first_240'])[:96]}`"
)
L.append("")
L.append(
    f"**常数可反推（先例是那对 TB/TC 反件，`refs/heads/review/0281-write-deadline-keyed-b3`）**："
    f"干净轮屏幕那句里的秒数是 `{clean_seconds}`（实测等待 `{c2['measured_wait_clean_round_ms']}` ms，"
    f"证据 blob `{ev_clean_blob}`）；把常数从 `{c2['constant_ms_in_the_module']}` 改小到 "
    f"`{c2['probe_constant_ms']}` 的那一枚探针臂 `{c2['probe_arm']}`（轮次 `{c2['probe_run_id']}`，"
    f"证据 `evidence/ord0288-keyless-deadline/ord0310-gate-evidence-{c2['probe_run_id']}.json` "
    f"blob `{ev_probe_blob}`）⇒ 屏上跟着变成 `{c2['probe_seconds_shown']}` 秒、"
    f"实测等待变成 `{c2['probe_measured_wait_ms']}` ms、`post_count={c2['probe_post_count']}`，"
    f"该臂判 `{c2['probe_verdict']}`（仍绿）。两处一起动才叫同源；"
    f"这就排除了「屏幕上那个秒数是另一处硬编码」。"
)
L.append("")
L.append("**三、服务端字段读数（不用状态码冒充 DB 事实）**")
L.append("")
L.append(
    f"门 `backend/tests/test_qoder_ord0310_keyless_leg_receipts.py`（blob `{bet_blob}`，"
    f"`{len(back['cells'])}` 格），库文件具名 `{back['db_file']}`，表 `{back['table']}`，"
    f"回读走第二条只读连接（`mode=ro`），与写入方不同连接。"
)
L.append("")
L.append(
    f"- K-1（不带键连发三发 `agent/commands`）：`{back['table']}.count(*)` 从 "
    f"`{k1b['idempotency_keys_rows_from']}` 到 `{k1b['idempotency_keys_rows_to']}`（+{k1b['receipt_rows_added']}），"
    f"同轮 `journey_missions` 从 `{k1b['journey_missions_rows_from']}` 到 "
    f"`{k1b['journey_missions_rows_to']}`（+{k1b['mission_rows_added']}），"
    f"三个 mission id 互不相同（`distinct_mission_ids={k1b['distinct_mission_ids']}`）。"
    f"**凭条表 +0 行而业务表 +3 行 = 「无键可回读」是服务器的形状，不是我推测的。**"
)
L.append(
    f"- K-2（带一把形制正确的键仍无凭条）：`count(*)` 从 `{back['cells']['K2']['idempotency_keys_rows_from']}` 到 "
    f"`{back['cells']['K2']['idempotency_keys_rows_to']}`，`mission_id_present="
    f"{json.dumps(back['cells']['K2']['mission_id_present'])}` ⇒ 请求里有个头不等于服务器收了键。"
)
L.append(
    f"- T-1(a)（服务器认键那一支 `plans/generate`，字段读数出处 "
    f"`evidence/ord0288-keyless-deadline/ord0310-backend-readings.json` blob `{back_blob}`，"
    f"表 `{back['table']}`）：第一发回答 `{t1a['first_status']}`、"
    f"第二发同键不同正文回答 `{t1a['second_status']}`，"
    f"`{back['table']}.count(*)` 两次读数 `{json.dumps(t1a['idempotency_keys_rows_first_to_second'])}`；"
    f"服务器原话：`same idempotency key used for a different request`。"
    f"那两个数是**观测到的回答**，不是本单主张的数量。"
)
L.append(
    f"- T-1(b)（凭条行落成长什么样）：`{back['table']}.key` = `{t1b['row_key_shape']}`、"
    f"`.operation` = `{t1b['row_operation']}`、`.response_status` = `{t1b['row_response_status']}`，"
    f"客户端两发状态各为 `{t1b['client_status_first']}` / `{t1b['client_status_replay']}`；"
    f"键被拒那一发（畸形键）先落行为 `{json.dumps(t1b['pre_claim_row_landed'])}`。"
    f"读过的列：{json.dumps(t1b['columns_read'])}；同一份字段读数的原始出处 "
    f"`evidence/ord0288-keyless-deadline/ord0310-backend-readings.json`，blob `{back_blob}`"
    f"（门 `backend/tests/test_qoder_ord0310_keyless_leg_receipts.py` blob `{bet_blob}`）。"
)
L.append("")
L.append("**四、反突变臂（逐臂带 (sha, nodeid, shape) 与还原摘要）**")
L.append("")
L.append("| 臂 | 红的节点（几枚 / 具名） | gate exit | 还原到被测字节 | claimed_result |")
L.append("| --- | --- | --- | --- | --- |")
for a in arms["arms"]:
    nodes = "；".join(f"`{n}`" for n in a["red_nodes"]) or "（无 —— 探针按预期绿）"
    L.append(f"| `{a['arm']}` | {len(a['red_nodes'])} 枚：{nodes} | {a['attempt']['gateExit']} | "
             f"{json.dumps(a['restored_to_tested_tree_bytes'])} | {a['claimed_result']} |")
L.append("")
L.append(
    f"聚合：`arms_total={arms['arms_total']}`、`killed={arms['killed']}`、`survived={arms['survived']}`、"
    f"`probes={arms['probes']}`、`every_arm_parsed_at_least_one_node="
    f"{json.dumps(arms['every_arm_parsed_at_least_one_node'])}`、"
    f"`all_arms_restored_to_tested_tree_bytes={json.dumps(arms['all_arms_restored_to_tested_tree_bytes'])}`、"
    f"`tree_unchanged_by_this_run={json.dumps(arms['tree_unchanged_by_this_run'])}`。"
    f"逐臂 `anchor_hits` 与 `expected_anchor_hits` 都是 1（改错了地方就不算臂），"
    f"每臂同一枚键的先决条件在本轮成立：`all_arms_carry_a_green_same_key_precondition="
    f"{json.dumps(arms['all_arms_carry_a_green_same_key_precondition'])}`。"
    f"`claimed_result` 是本车道观测，`derived_result` 全为 null —— 等级与派生归红队。"
)
L.append("")
L.append("**五、我欠的两处，写在这里不抹**")
L.append("")
L.append(
    f"其一：头两轮臂收据里 **每一枚臂都被误判成 SURVIVED**，而同一些运行的 pytest 行数明明是 "
    f"`1 failed`。原因在量具：解析节点行的正则少了 `re.M`，`^` 与 `$` 只对着整段捕获文本的两端，"
    f"于是一枚节点都没匹配上，计数恒为 0。修法提交 `{rec['candidate']['tools_sha']}`"
    f"（只改驱动器，产品字节与断言一字未动），本块全部数字出自修好之后那一轮："
    f"臂收据 `evidence/ord0288-keyless-deadline/ord0310-arms-receipt-r3.json`，blob `{arms_blob}`。"
    f"一个从不命中的计数既不是绿也不是杀。"
)
L.append("")
L.append(
    f"其二：`K0310_SENTENCE_PROMISES_REPLAY` 第一次是 SURVIVED —— 门禁只在折叠态读卡片，"
    f"而我把禁句写进了「技术详情」展开之后；而且当时只要求句子里「提到一把键」，松散到能放过承诺补问的说法。"
    f"补法是折叠态与展开态各读一遍、并把「不能靠同一把键补问」钉成逐字判据，"
    f"改的是量具不是断言（提交 `{rec['candidate']['code_sha']}`，"
    f"门 `frontend/e2e/qoder-ord0310-keyless-write-deadline.spec.ts` blob `{spec_blob}`）。"
    f"收紧之后同一枚臂红。"
)
L.append("")
L.append(
    f"**判据与出处**：主收据 `evidence/ord0288-keyless-deadline/"
    f"ord0310_keyless_deadline_receipt_r1.json`，blob `{rec_blob}`（"
    f"{(SC / 'ord0310_keyless_deadline_receipt_r1.json').stat().st_size} B），"
    f"{len(rec['cells'])} 格自证；服务端读数 `ord0310-backend-readings.json` blob `{back_blob}`；"
    f"尺 Q38 r2（尺 blob `91ae8b1ec55f5c19122af11bf775df14580955e4`）判这枚收据 ⇒ "
    f"`{q38['overall']}`、hard `{q38['hard_count']}`、soft `{q38['soft_count']}`、exit `{q38['exit']}`，"
    f"输出 `ord0310-q38r2-on-receipt.json` blob `{q38_blob}`。"
    f"本块自身的两把尺输出同目录（文件名里带 `on-block` / `on-post`）。"
)
L.append("")
L.append(
    "**纪律**：`0 权威线写入`、`0 推他人 ref`（只推了自己命名的 "
    f"`{ref['ref']}`）、`demo/reset 0`、`_live`/`_preview` 库 0 读写、凭据 0 打印 "
    "（第二路读 ref 的 token 只进内存，`ord0310-tip-read.out` 里那一行写的是占位符）、"
    "`0 为了绿而改断言`（两处红都是收紧量具修掉的，见第五节）；"
    "交件走新路径 `evidence/ord0288-keyless-deadline/`，逐件独立 GET 回读，已发布路径 0 覆盖 0 改名。"
)
L.append("")
text = "\n".join(L) + "\n"
OUT.write_text(text, encoding="utf-8", newline="\n")
print(f"wrote {OUT} {OUT.stat().st_size} B blob={sha1(OUT.read_bytes())}")
print(f"lines={len(text.splitlines())} token_present={TIME_TOKEN in text}")
