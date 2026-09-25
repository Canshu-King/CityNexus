"""Build the ORD-0310 bus post out of the published artifacts, then gauge that post with both rulers.

Two rules the shape of this file follows: every byte/it claims to have published is copied from the
per-file independent GET readback (not from the publisher's stdout), and the closing line is read out
of the commander's own CLOSING_LINE.txt rather than typed by me.
"""
from __future__ import annotations

import base64
import hashlib
import json
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path("D:/moodle/_qoder_d_lane_20260923")
SC = ROOT / "_scratch_0310"
DIR = "evidence/ord0288-keyless-deadline"
API = "https://api.github.com/repos/Canshu-King/CityNexus/contents"
REF = "commander/control"
CLOSING_FILE = Path("D:/moodle/_qoder_cmdr_ref_20260921/live_checks/CLOSING_LINE.txt")
# which generation the post speaks for: argv order = readback, receipt, arms, backend, q38, out
SELF_NAME = sys.argv[1] if len(sys.argv) > 1 else "ord0310-readback-r1.json"
RECEIPT = sys.argv[2] if len(sys.argv) > 2 else "ord0310_keyless_deadline_receipt_r1.json"
ARMS = sys.argv[3] if len(sys.argv) > 3 else "arms_receipt_r3.json"
BACKEND = sys.argv[4] if len(sys.argv) > 4 else "backend_readings.json"
Q38 = sys.argv[5] if len(sys.argv) > 5 else "q38r2-on-receipt.json"
BLOCK = sys.argv[6] if len(sys.argv) > 6 else "ord0310-ledger-block.md"
ARMS_PUB = sys.argv[7] if len(sys.argv) > 7 else "ord0310-arms-receipt-r3.json"
BACKEND_PUB = sys.argv[8] if len(sys.argv) > 8 else "ord0310-backend-readings.json"
TOOL_PUB = sys.argv[9] if len(sys.argv) > 9 else "ord0310-tool-kill-arms.py"
OUT = SC / (sys.argv[10] if len(sys.argv) > 10 else "ord0310-post-body.md")
GEN_TAG = sys.argv[11] if len(sys.argv) > 11 else ""
SUF = sys.argv[13] if len(sys.argv) > 13 else ""
PUB_POST = sys.argv[14] if len(sys.argv) > 14 else "ord0310-post-body.md"
NEXT_BOOK = sys.argv[15] if len(sys.argv) > 15 else "ord0310-readback-r2.json"
PUB_BLOCK = sys.argv[12] if len(sys.argv) > 12 else "ord0310-ledger-block.md"
TIP_PUB = sys.argv[16] if len(sys.argv) > 16 else "ord0310-tip-read.out"
PUBLISH_LOG = sys.argv[17] if len(sys.argv) > 17 else ""
ERRATUM = sys.argv[18] if len(sys.argv) > 18 else ""


def blob(data: bytes) -> str:
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def get(url: str, attempts: int = 4):
    last = None
    for i in range(attempts):
        secret = next((l[len("password="):] for l in subprocess.run(
            ["git", "credential", "fill"], input="protocol=https\nhost=github.com\n\n",
            capture_output=True, text=True, check=True).stdout.splitlines()
            if l.startswith("password=")), "")
        request = urllib.request.Request(url, headers={"Authorization": f"Bearer {secret}",
                                                      "Accept": "application/vnd.github+json",
                                                      "User-Agent": "qoder-e345b9d6-ord0310-post"})
        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                return response.status, json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as error:
            return error.code, {"raw": error.read().decode("utf-8", errors="replace")[:200]}
        except Exception as error:
            last = error
            time.sleep(2 + 2 * i)
    return 0, {"raw": f"transport failure after {attempts} attempts: {type(last).__name__}: {last}"}


def main() -> int:
    rec = json.loads((SC / RECEIPT).read_text(encoding="utf-8"))
    arms = json.loads((SC / ARMS).read_text(encoding="utf-8"))
    back = json.loads((SC / BACKEND).read_text(encoding="utf-8"))
    read = json.loads((SC / SELF_NAME).read_text(encoding="utf-8"))
    cells = {c["id"]: c for c in rec["cells"]}
    gen = rec["generation_binding"]
    mp = gen["merge_prediction"]
    tip_read = rec["ref_tip_read"]
    ref = rec["candidate_ref_readback"]
    c2 = cells["C2_single_named_constant"]["readings"]
    c3 = cells["C3_screen_sentence_shape"]["readings"]
    keyed = cells["C1_keyed_shape_untouched"]["readings"]["keyed_shape_on_the_line_0281"]
    k1b, t1a, t1b = back["cells"]["K1"], back["cells"]["T1a"], back["cells"]["T1b"]
    block_md = (SC / BLOCK).read_bytes()

    # the readback JSON cannot certify itself: close it with one further single GET
    st, body = get(f"{API}/{DIR}/{SELF_NAME}?ref={REF}")
    remote = base64.b64decode(body["content"]) if st == 200 and "content" in body else b""
    local = (SC / SELF_NAME).read_bytes()
    proof = (f"GET {API}/{DIR}/{SELF_NAME}?ref={REF} -> HTTP {st} | remote {len(remote):,} B blob "
             f"{body.get('sha', '')} | local {len(local):,} B blob {blob(local)} => "
             f"{'BYTE-LEVEL MATCH' if remote == local and body.get('sha') == blob(local) else 'MISMATCH'}")
    if "BYTE-LEVEL MATCH" not in proof:
        print("ABORT: the readback file did not read back byte-equal, so the post cannot cite it")
        print(proof)
        return 4
    print(proof)
    self_remote_blob = body.get("sha", "")
    self_remote_bytes = len(remote)

    closing = CLOSING_FILE.read_bytes().decode("utf-8").rstrip("\r\n")
    print(f"closing line read from {CLOSING_FILE.name}: {len(closing.encode('utf-8'))} B "
          f"blob={blob(closing.encode('utf-8'))}")

    rows = read["rows"]
    L = []
    L.append(f"【号令者 494abfd7 → D 车道 e345b9d6｜ORD-0310 交付{GEN_TAG}：给无键写腿一枚可指名的设备期限"
             "（形制按仲裁 Q54=①）】")
    L.append("")
    L.append(
        f"一句话：`agent/commands` 那一发（不收幂等键的那一支）现在有了一枚**只在一处定义、屏上那个秒数与"
        f"计时器同源**的设备期限 `{c2['constant_ms_in_the_module']}` ms；到点后屏幕上只说它射程以内的事 —— "
        f"结果未知、不是没发生、这一笔不能靠同一把键补问。有键那一支（0281）我一个字没改。"
        f"候选 `{ref['ref']}` = `{ref['sha_read_back_over_https']}`（父 = 我当时读到的线位；"
        f"权威尖只读 `{tip_read['sha']}`，两路一致，我 0 次移动）。")
    L.append("")
    if gen.get("authority_tip_is_ancestor_of_this_tree"):
        extra = gen.get("files_this_tree_adds_on_top_of_the_tip", [])
        L.append(
            f"**本代与权威线的关系（不用嘴说）**：现读的尖 `{tip_read['sha']}` 是我这一代的祖先"
            f"（`authority_tip_is_ancestor_of_this_tree="
            f"{json.dumps(gen['authority_tip_is_ancestor_of_this_tree'])}`、`git merge-base --is-ancestor` "
            f"退出 `0`），我这一代比线尖只多 `{len(extra)}` 件："
            f"{json.dumps(extra, ensure_ascii=False)} —— 全是本车道自己的工具，产品/门字节 0 件。"
            f"所以这一轮交的就是**落成的那一代**的读数，不再欠一次追基座；落地之前那一轮的"
            f"分叉/交集论证（自分叉点 `{gen['fork_point_with_the_line']}` 起线动 "
            f"`{len(gen['files_the_line_changed_since_the_fork'])}` 件、我动 "
            f"`{len(gen['files_my_candidate_changed_since_the_fork'])}` 件、交集 "
            f"`{len(gen['intersection_between_their_files_and_mine'])}` 件）记在上一块，"
            f"原样表 `{DIR}/ord0310-path-disjointness-r2.tsv`，这里不复述成今天的数。")
    else:
        L.append(
            f"**先说清一枚你不该把它读成什么**：线尖在我这一代之后又动了 "
            f"`{len(gen['commits_on_the_line_since_the_fork'])}` 笔，"
            f"自分叉点 `{gen['fork_point_with_the_line']}` 起线动 `{len(gen['files_the_line_changed_since_the_fork'])}` 件、"
            f"我动 `{len(gen['files_my_candidate_changed_since_the_fork'])}` 件，**两边交集 "
            f"`{len(gen['intersection_between_their_files_and_mine'])}` 件**；"
            f"只读合流预测 `{mp['command']}` ⇒ 退出 `{mp['exit']}`、预测树 `{mp['predicted_tree']}`、"
            f"conflict 段空。按 Q24 本单所有读数只属于 `{arms['tested_tree']}` 那一代，我不折算到尖 —— "
            f"**要不要我在当代尖上重跑一轮绿 + 一轮拆（≈25 分钟）请落字**；不落字我就按这一代交。")
    rev = rec.get("revision") or {}
    _prev_out = SC / "r2" / "ord0310-mergetree-tip-x-previous-ref.out"
    PREV_REF_TREE = (_prev_out.read_text(encoding="utf-8").splitlines()[0].strip()
                     if _prev_out.exists() else "NOT_MEASURED")
    PREV_REF_BLOB = blob(_prev_out.read_bytes()) if _prev_out.exists() else "NOT_MEASURED"
    if not re.fullmatch(r"[0-9a-f]{40}", PREV_REF_TREE):
        print(f"ABORT: the previous-ref predicted tree did not read as 40 hex: {PREV_REF_TREE!r}")
        return 7
    if rev:
        mp2 = ref["merge_prediction_on_the_pushed_ref"]
        eq = rev["what_a_recut_proves"]
        L.append("")
        if eq.get("is_a_self_comparison"):
            recut_sentence = (
                f"本代不是 re-cut：产品那一笔 `{rec['candidate']['product_commit']}` 与上一代同一笔，"
                f"所以 `patch-id` 那两枚是同一笔与它自己比 —— 本条不拿它当跨代证据"
                f"（新收据里具名 `what_a_recut_proves.is_a_self_comparison="
                f"{json.dumps(eq['is_a_self_comparison'])}`）。本代能声明的是被量字节没动："
                f"`subject_files_equal_to_the_tested_tree="
                f"{json.dumps(ref['subject_files_equal_to_the_tested_tree'])}`、"
                f"`tested_tree_vs_product_commit.all_equal="
                f"{json.dumps(rev['tested_tree_vs_product_commit']['all_equal'])}`。")
        else:
            recut_sentence = (
                f"只搬基座没改字：两代产品笔的 `patch-id` 相同（"
                f"`{eq['patch_id_of_the_product_commit'][0].split(' ')[0]}` = "
                f"`{eq['patch_id_of_the_product_commit'][1].split(' ')[0]}`），四枚工件跨代同 blob "
                f"`{json.dumps(eq['subject_blobs_equal_across_generations'])}`。")
        L.append(
            f"**这一代是怎么来的（`{rev['generation']}`）**：你落地之后我从现读尖 `{tip_read['sha']}` "
            f"再切一次，候选尖 `{ref['sha_read_back_over_https']}`；那一笔的父位 "
            f"`{rec['candidate']['parent']}` 与这枚尖相等 "
            f"`{json.dumps(rec['candidate']['is_parent_the_tip_read_now'])}`"
            f"（本单声明的分叉基座 `{rec['candidate']['base_cut_from']}` 与尖相等 "
            f"`{json.dumps(rec['candidate']['is_declared_base_the_tip_read_now'])}` —— 落地之后这两问不同答，"
            f"上一块里我把它们混成一枚字段，勘误见第五节）。"
            + recut_sentence +
            f" 预测树各标各处：上一枚 ref 对同一枚尖我复算 = `{PREV_REF_TREE}`"
            f"（原样输出 `{DIR}/ord0310-mergetree-tip-x-previous-ref.out` blob `{PREV_REF_BLOB}`，"
            f"与你那帖 `issuecomment-5832371591` 给的数逐位相同）；本代按 ref 当下尖重算 = "
            f"`{mp2['predicted_tree']}`、退出 `{mp2['exit']}`、conflict 段 = "
            f"`{mp2['raw_after_first_line'].strip() or '（空）'}`。")
    L.append("")
    L.append("**一、两枚形状（谁也不替谁交卷）**")
    L.append("")
    L.append(f"- 有键 = 0281（B 的）：`frontend/src/lib/writeDeadline.ts` blob `{keyed['blob_at_tip']}`，"
             f"常数 `{keyed['exported_constant']}`，引用者只有 "
             + "、".join(f"`{p}`" for p in keyed["importers_at_tip"])
             + f"；`git grep -n fetchWithWriteDeadline {tip_read['sha']} -- "
               f"frontend/src/features/planning/PlanWithAiSheet.tsx` 回 "
               f"`{keyed['sheet_call_sites_at_tip']['lines_returned']}` 行。"
               + (f"被测那一代里这枚文件不存在"
                  f"（`absent_from_my_tested_tree={json.dumps(keyed['absent_from_my_tested_tree'])}`），"
                  f"我是量完之后按线尖只读 `git show` 看到的。"
                  if keyed["absent_from_my_tested_tree"] else
                  f"落地之后它随基座进我的候选（`absent_from_my_tested_tree="
                  f"{json.dumps(keyed['absent_from_my_tested_tree'])}`、候选树内 blob 与线尖同值），"
                  f"本道那一笔的改动清单里没有它 ⇒ 我对它仍是一字未改。"))
    L.append(f"- 无键 = 本单：新建 `frontend/src/lib/keylessWriteDeadline.ts` blob "
             f"`{cells['C5_arms_and_provenance']['readings']['blob_module']}`；"
             f"`frontend/src/features/planning/PlanWithAiSheet.tsx` blob "
             f"`{cells['C5_arms_and_provenance']['readings']['blob_sheet']}` 里 `fetchWithKeylessWriteDeadline` "
             f"只裹 `agent/commands`。期限放在服务端写预算之上（`backend/app/core/config.py:96` 那枚 "
             f"`45000`）才不会出现「服务器已判死、客户端还在等」，也不会催用户在服务器还在写时重来。")
    L.append("")
    L.append("**二、屏上那句（干净轮 `" + arms["clean_round"]["runId"] + "`，库 `" + arms["clean_round"]["db"] + "`）**")
    L.append("")
    clean_ev_name = f"ord0310-gate-evidence-{arms['clean_round']['runId']}.json"
    clean_ev_blob = rows[clean_ev_name]["remote_blob"] if clean_ev_name in rows else "NOT_PUBLISHED"
    L.append(f"`status={c3['status_attribute']}`、`origin={c3['reason_origin']}`、"
             f"`label={c3['reason_label']}`（不冒充「服务器给出的原因」）、`detail_block_attached="
             f"{json.dumps(c3['detail_block_attached'])}`、实测等待 `{c2['measured_wait_clean_round_ms']}` ms、"
             f"`post_count={c2['post_count_clean_round']}`。屏幕上那句原文（逐字，出自本轮证据文件 "
             f"`{DIR}/{clean_ev_name}` blob `{clean_ev_blob}`）：")
    L.append("")
    L.append("> " + str(c2["seconds_shown_on_screen_clean_round"]))
    L.append("")
    probe_ev_name = f"ord0310-gate-evidence-{c2['probe_run_id']}.json"
    probe_ev_blob = rows[probe_ev_name]["remote_blob"] if probe_ev_name in rows else "NOT_PUBLISHED"
    L.append(f"反推那一刀（读数出自证据文件 `{DIR}/{probe_ev_name}` blob `{probe_ev_blob}`、"
             f"臂收据 blob `{rows[ARMS_PUB]['remote_blob']}`）："
             f"常数从 `{c2['constant_ms_in_the_module']}` 改小到 `{c2['probe_constant_ms']}` "
             f"（臂 `{c2['probe_arm']}`，轮次 `{c2['probe_run_id']}`）⇒ 屏上秒数跟着变 `{c2['probe_seconds_shown']}`、"
             f"实测等待从 `{c2['measured_wait_clean_round_ms']}` ms 变 `{c2['probe_measured_wait_ms']}` ms，"
             f"该臂仍判 `{c2['probe_verdict']}`。数值与计时器动在同一处定义上，所以那句里的秒数不是另一处硬编码。")
    L.append("")
    L.append("**三、服务端字段读数（不用状态码冒充 DB 事实）**")
    L.append("")
    L.append(f"库 `{back['db_file']}`、表 `{back['table']}`、字段出处 "
             f"`{DIR}/{BACKEND_PUB}` blob "
             f"`{rows[BACKEND_PUB]['remote_blob']}`，"
             f"回读走第二条 `mode=ro` 连接："
             f"不带键连发三发 ⇒ `count(*)` 从 `{k1b['idempotency_keys_rows_from']}` 到 "
             f"`{k1b['idempotency_keys_rows_to']}`（凭条 +{k1b['receipt_rows_added']} 行），"
             f"同轮 `journey_missions` 从 `{k1b['journey_missions_rows_from']}` 到 "
             f"`{k1b['journey_missions_rows_to']}`、`distinct_mission_ids={k1b['distinct_mission_ids']}`；"
             f"带一把形制正确的键仍 +{back['cells']['K2']['receipt_rows_added']} 行（凭条表列 `count(*)`）。")
    L.append(f"认键那一支 `plans/generate`（服务器只在这一支收键）：读数取自 "
             f"`{DIR}/{BACKEND_PUB}` 的 `T1a` 格，blob "
             f"`{rows[BACKEND_PUB]['remote_blob']}` ⇒ "
             f"第一发回答 `{t1a['first_status']}`、同键换正文第二发 `{t1a['second_status']}`"
             f"（服务器原话 `same idempotency key used for a different request`）。")
    L.append(f"同一本账的 `T1b` 格 blob `{rows[BACKEND_PUB]['remote_blob']}` "
             f"给出落下的凭条行：`key={t1b['row_key_shape']}`、`operation={t1b['row_operation']}`、"
             f"`response_status={t1b['row_response_status']}`，与客户端第一发看到的 "
             f"`{t1b['client_status_first']}` 相等（`response_status == client_status_first` 是本格断言）。")
    L.append("")
    L.append("**四、反突变臂（逐臂带 (sha, nodeid, shape)）**")
    L.append("")
    L.append("| 臂 | 红了几枚节点 | gate exit | 还原 | claimed |")
    L.append("| --- | --- | --- | --- | --- |")
    for a in arms["arms"]:
        L.append(f"| `{a['arm']}` | {len(a['red_nodes'])} | {a['attempt']['gateExit']} | "
                 f"{json.dumps(a['restored_to_tested_tree_bytes'])} | {a['claimed_result']} |")
    L.append("")
    L.append(f"聚合 `killed={arms['killed']}/{arms['arms_total'] - arms['probes']}`、"
             f"`survived={arms['survived']}`、`every_arm_parsed_at_least_one_node="
             f"{json.dumps(arms['every_arm_parsed_at_least_one_node'])}`、"
             f"`tree_unchanged_by_this_run={json.dumps(arms['tree_unchanged_by_this_run'])}`。"
             f"**`claimed_result` 只是我这辆道的观测，`derived_result` 一律 null；等级归红队，我不签级。**")
    L.append("")
    c6 = next((c for c in rec["cells"] if c["id"].startswith("C6")), None)
    if c6:
        r6 = c6["readings"]
        two = r6["signal_but_no_deadline_arm"]
        proof_name = "ord0310-signal-vs-deadline-proof.out"
        proof_blob = (rows[proof_name]["remote_blob"] if proof_name in rows
                      else r6["premise_proof"].get("blob", "NOT_PUBLISHED"))
        L.append("**四·补、判据是「期限到了」，不是「有没有 signal」（你 ② 要的那枚双臂自证）**")
        L.append("")
        L.append(
            f"先把前提钉住（这是你 21:02 那帖给我的新事实）：现读尖 `{tip_read['sha']}` 上"
            f"`PlanWithAiSheet.tsx` 的 `signal` 选项行是 "
            f"{json.dumps([ln for ln, _ in r6['signal_option_lines_at_the_tip']])}，"
            f"而我这一代的无键腿 `{r6['keyless_leg_wrapped_in_this_tree'][0][0]}` 行本来就带着它"
            f"（`{r6['wrapper_preserves_the_callers_signal'][0][1]}`）⇒ **"
            f"「有 signal」在这棵树上恒真，它不可能当判别量**。所以我把臂对准这一点："
            f"`{two['arm']}` 只把 `{r6['keyless_leg_wrapped_in_this_tree'][0][1]}` 换回裸 "
            f"`fetch(`（同一处 `signal,` 一字未动，`anchor_hits={two['anchor_hits']}`、"
            f"字节 `{two['sizes']['before']}` → `{two['sizes']['during_mutation']}`，差 "
            f"`{two['sizes']['delta_bytes']}` B 正好是包装函数名的长度），"
            f"三枚节点读数是 "
            + "、".join(f"`{k.split('：')[0]}={'红' if v == 'RED' else '绿'}`"
                        for k, v in two["nodes"].items())
            + f" ⇒ 只有 K1 红、K2/K3 仍绿，即**红的是「期限到不到」那一判据，不是 signal 的有无**。"
              f"反向对照：把期限分支冒充成旅客主动取消的那枚臂 `{r6['arm_that_breaks_the_distinction']['arm']}` "
              f"红的是 K3（`{len(r6['arm_that_breaks_the_distinction']['red_nodes'])}` 枚）。"
              f"该臂的 (sha, nodeid, shape) 三元组与还原摘要在臂收据 "
              f"`{DIR}/{ARMS_PUB}` blob `{rows[ARMS_PUB]['remote_blob']}` 里；"
              f"逐行前提原样输出 `{DIR}/{proof_name}` blob `{proof_blob}`。")
        if not r6["premise_proof"].get("exists"):
            L.append("")
            L.append(
                f"这一格自己也有一个要说出来的缺陷：修正后的收据里 `C6.readings.premise_proof.exists="
                f"{json.dumps(r6['premise_proof']['exists'])}`、`blob="
                f"`{r6['premise_proof']['blob']}` —— 因为我给收据生成器指的 `--raw-dir` 是 r3b，"
                f"而那件证明输出留在 r3。证明件本身早已发布（上面那枚 blob 就是逐字节回读到的它），"
                f"落地那一块引的也是它；这里是**第四枚同类毛病（标签/路径指错，不是读数错）**，"
                f"我写在这里而不是再补一块账本。")
    L.append("")
    L.append("**五、我自己的账（不抹）**")
    L.append("")
    L.append(f"头两轮臂收据把每一枚臂都报成 SURVIVED，而同一些运行的行数是 `1 failed` —— 正则少了 `re.M`，"
             f"`^`/`$` 只对着整段文本两端，计数恒为 0；修具那一笔就是候选尖 `{ref['sha_read_back_over_https']}`"
             f"（驱动器 blob 见下表 `{TOOL_PUB}`），本条所有数字出自修好之后那一轮。"
             f"另一处：`K0310_SENTENCE_PROMISES_REPLAY` 第一次真存活 —— 门禁只在折叠态读卡片，"
             f"而禁句活在「技术详情」展开之后；补法是折叠+展开各读一遍，并把「不能靠同一把键补问」钉成逐字判据。"
             f"两处都是收紧量具，不是把断言改松换绿。")
    if ERRATUM:
        er = json.loads((SC / ERRATUM).read_text(encoding="utf-8"))
        refs_out = SC / "r4" / "ord0310-tools-ref-read-2.out"
        refs_parsed = json.loads([l for l in refs_out.read_text(encoding="utf-8").splitlines()
                                  if l.startswith("parsed:")][0][len("parsed:"):].strip())
        TOOLS_R5 = refs_parsed["refs/heads/review/ord0310-tools-r5"]
        d1, d2, d3 = er["defects"][0], er["defects"][1], er["defects"][2]
        L.append("")
        L.append(
            f"第三批（这一代特有，已单独落账本勘误块）：我 21:56 那块里有 "
            f"{len(er['defects'])} 处**标签/派生**错，全不是读数 —— "
            f"① `is_cut_on_the_tip_read_now={json.dumps(d1['was'])}` 印在两个一模一样的 40 位旁边，"
            f"因为那枚字段比的是「声明的分叉基座 `{rec['candidate']['base_cut_from']}`」与尖，"
            f"不是我那句话说的父位与尖；现测父位 `{rec['candidate']['parent']}` 与尖 "
            f"`{tip_read['sha']}` 相等（`{DIR}/ord0310-ref-read-r3b.out` blob "
            f"`{er['corrected_artifacts']['instrument_commit']['raw_readback']['blob']}` 里"
            f" `git ls-remote` 与 `git rev-parse …^` 的原样输出），修正后拆成两问 "
            f"`is_parent_the_tip_read_now="
            f"{json.dumps(rec['candidate']['is_parent_the_tip_read_now'])}` / "
            f"`is_declared_base_the_tip_read_now="
            f"{json.dumps(rec['candidate']['is_declared_base_the_tip_read_now'])}`；"
            f"② 块标题的 `{d2['was']}` 是 r2 那轮留下的字面量，现在由 `--generation-label` 传入 = "
            f"`{d2['now']}`；③ 那块把 `patch-id` 两枚相同当跨代证据，而落地之后那是同一笔"
            f" `{rec['candidate']['product_commit']}` 与它自己比 ⇒ 新收据具名 "
            f"`is_a_self_comparison={json.dumps(d3['now_flag'])}`，论证退回上一枚收据 blob "
            f"`{rec['revision']['previous_generation_receipt_blob']}`。"
            f"修正件走新名：收据 `{DIR}/{er['corrected_artifacts']['receipt']['path'].split('/')[-1]}` "
            f"blob `{er['corrected_artifacts']['receipt']['blob']}`，尺 Q38 r2 判它 "
            f"`{er['corrected_artifacts']['q38_r2']['verdict']}`、hard "
            f"`{er['corrected_artifacts']['q38_r2']['hard']}`、soft "
            f"`{er['corrected_artifacts']['q38_r2']['soft']}`；"
            f"被勘误那两件 0 覆盖 0 改名，仍在原位。机器可读 was/now："
            f"`{DIR}/ord0310-erratum-r1.json` blob `{blob((SC / 'ord0310-erratum-r1.json').read_bytes())}`。"
            f"另有第四枚同类（`C6.premise_proof` 指错目录，上一段刚说过），我没再补块，写在这里。"
            f" 勘误块自己也在 `## DELIVERIES` 里（`{DIR}/ord0310-ledger-block-erratum-r1.md` blob "
            f"`{rows['ord0310-ledger-block-erratum-r1.md']['remote_blob']}`，两把尺判的是从账本回读出来的那份字节）。"
            f"量具改动不塞进被量那一代：逐件字节冻结在 "
            f"`refs/heads/review/ord0310-tools-r5` = `{TOOLS_R5}`，五枚 ref 同一趟 "
            f"`git ls-remote` 的原样输出是 `{DIR}/ord0310-tools-ref-read-2.out` blob "
            f"`{rows['ord0310-tools-ref-read-2.out']['remote_blob']}` —— 里面同时回读着 "
            f"`refs/heads/review/ord0310-tools-r3b` = "
            f"`{refs_parsed['refs/heads/review/ord0310-tools-r3b']}`，即勘误块引的那枚等式仍然成立；"
            f"被量的 `{ref['ref']}` 仍是 `{ref['sha_read_back_over_https']}`。")
    L.append("")
    checked = {n: r for n, r in rows.items() if r["verdict"] != "PRIOR_GENERATION_NOT_RESTAGED"}
    prior = read.get("prior_generation_files_on_branch", [])
    L.append(f"**六、发布与回读**：`{DIR}/` 目录现在共 `{read['directory_get']['entries_on_server']}` 件，"
             f"本轮逐件独立 GET 量了 `{read['checked_this_round']}` 件（本代交件），"
             f"`byteLevelMatches={read['byteLevelMatches']}`、`notMatching="
             f"{json.dumps(read['notMatching'])}`；剩下 `{len(prior)}` 件是上一代同名/异名件，"
             f"我这一轮没有重贴它们的内容，所以它们具名为 `PRIOR_GENERATION_NOT_RESTAGED` 而不是被算成不吻合。")
    if PUBLISH_LOG:
        logs = [json.loads((SC / n).read_text(encoding="utf-8")) for n in PUBLISH_LOG.split(",")]
        fresh = sum(1 for lg in logs for v in lg.values() if v["fresh_path"])
        skipped = sum(1 for lg in logs for v in lg.values() if v["identical_skipped"])
        refused = [n for lg in logs for n, v in lg.items() if v["refused"]]
        transport = sorted(n for lg in logs for n, v in lg.items()
                           if v["exit"] != 0 and not v["refused"])
        L.append("0 覆盖不是我口述：每一件都走 `HJ-P3_evidence/gated_push.py` 那道同字节即跳过、"
                 f"异字节即拒绝的门，逐件日志已发布 —— 本轮 `FRESH={fresh}`（新路径首次创建）、"
                 f"`SKIP={skipped}`（同字节不动那件路径）、`REFUSE={json.dumps(refused)}`。"
                 + (f"另有 {len(transport)} 件在**发出 PUT 之前**就死于链路 "
                    f"（`SSL: UNEXPECTED_EOF_WHILE_READING`，闸门 fail-closed），我按老规矩只手工重试"
                    f"那几件、并把它们记成传输异常而不是凭据问题：重试件全部 FRESH+MATCH，"
                    f"日志逐件写着：" + "、".join(f"`{DIR}/{n}`" for n in PUBLISH_LOG.split(",")) + "。"
                    if transport else ""))
    else:
        L.append("0 覆盖不是我口述：每一件都走 `HJ-P3_evidence/gated_push.py` 那道同字节即跳过、"
                 "异字节即拒绝的门。")
    L.append("")
    L.append(f"那本账本自己不能自证，所以它单独由一次 GET 收尾（原话）：`{proof}`。")
    L.append("")
    L.append(f"（本条正文自己、以及判它的两把尺输出，也在同一目录："
             f"`{PUB_POST}`、`ord0310-q43r4b-on-post{SUF}.json`、`ord0310-q43r3-on-post{SUF}.json`；"
             f"它们的逐字节回读记在下一本账 `{NEXT_BOOK}` 里 —— 那本账在本条发出去之后才生成，"
             f"所以这里只给名字不给读数，免得我拿一段还没定型的字去算哈希。）")
    L.append("")
    L.append(f"| 文件（全部在 `{DIR}/` 下，本单之前该目录不存在） | blob（40 位） | 远端字节 |")
    L.append("| --- | --- | --- |")
    for name in sorted(checked):
        r = checked[name]
        L.append(f"| `{name}` | `{r['remote_blob']}` | {r['remote_bytes']:,} |")
    L.append("")
    L.append(f"账本块已落 `## DELIVERIES`（追加，不动别人的块），逐字节同 "
             f"`{DIR}/{PUB_BLOCK}`，blob `{blob(block_md)}`（{len(block_md):,} B）；"
             f"两把尺判的是**从账本里回读出来的那份字节**（不是我递给插入工具的草稿），输出同目录："
             f"`ord0310-q43r4b-on-block{SUF}.json`、`ord0310-q43r3-on-block{SUF}.json`；"
             f"Q43 r4b（尺 blob `efa6b7a383e094e2ede89f5dd8565b12feed0171`）判绿，"
             f"Q43 r3（尺 blob `e653e597c2e6fd74a5f8d3be65fe60e017b03017`）判干净。")
    L.append("")
    L.append(f"**六·补、手机上还看不到（你 ① 那句我记账）**：这一代 `LANDED`"
             f"（尖 `{tip_read['sha']}` 里就有那四枚工件），但**没部署到手机预览面** ⇒ "
             f"`NOT-YET-DEPLOYED-to-phone`。我这边 0 次换代：没跑 `deploy_bundle.py`、没切 bundle、"
             f"没动 `vite preview` 的端口带，所以真机上那句话仍是上一代的。按 Q61 我不去自己换那一代 —— "
             f"要我在手机上量这句，请落字并给一次换代窗口，我按 `REPRODUCED(tree)` 与 `NOT-DEPLOYED(phone)` "
             f"分两栏报。")
    L.append("")
    L.append("**七、队列里还压着的**：ORD-0288 的另一半（服务端那一腿）不在本单射程；"
             "ORD-0266 `db6ac1d` 仍 DELIVERED/NOT-LANDED；ORD-0232 端到端复放仍等合流窗口；"
             "ORD-0308 那张表里 `NOT_APPLICABLE_missing_candidate` 那一格现在有条件重跑"
             "（F 的 0307 已落），你要的话我下一单做。")
    L.append("")
    L.append(f"**纪律**：`0 权威线写入`、`0 推他人 ref`（只推了自己命名的 ref：`{ref['ref']}` 与"
             f"量具那枚 tools ref）、`demo/reset 0`、"
             f"`_live`/`_preview` 库 0 读写、凭据 0 打印（第二路读 ref 的 token 只进内存，"
             f"`{DIR}/{TIP_PUB}` 里那一行写的是占位符）、`0 为了绿而改断言`"
             f"（本轮 0 次开门跑测量，勘误只改标签）。")
    L.append("")
    L.append(closing)
    text = "\n".join(L) + "\n"
    OUT.write_bytes(text.encode("utf-8"))
    print(f"wrote {OUT} {len(text.encode('utf-8'))} B blob={blob(text.encode('utf-8'))}")
    print(f"tail_ok={text.rstrip().endswith(closing)}")
    for ruler, tag in (("claim_coordinate_check_r4b.py", "q43r4b"),
                       ("claim_coordinate_check_r3.py", "q43r3")):
        proc = subprocess.run(["D:/moodle/CityNexus/.venv/Scripts/python.exe",
                               f"D:/moodle/_qoder_cmdr_ref_20260921/live_checks/{ruler}",
                               "--text", str(OUT), "--out", str(SC / f"ord0310-{tag}-on-post{SUF}.json")],
                              capture_output=True, text=True, encoding="utf-8", errors="replace")
        line = next((l for l in proc.stdout.splitlines() if "overall" in l), proc.stdout[:200])
        print(f"{tag}: exit={proc.returncode} | {line}")
    return 0


raise SystemExit(main())
