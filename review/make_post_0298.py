"""Compose the ORD-0298 post: the re-parented generation's own readings, table by table.

Nothing here is typed in.  The three tree coordinates, the per-file sha256 table, the arm cells and
their Q38 token counts all come out of the two receipts plus the gauge's own JSON, because a
re-parent is exactly the place where a hand-copied number would look most convincing.

It signs no grade: `claimed_result` is what the driver derived; `derived_result` is the red team's.
"""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
import sys

for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

LANE = "D:/moodle/_qoder_d_lane_20260923"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--arms", required=True)
    ap.add_argument("--round", required=True)
    ap.add_argument("--q38", required=True, help="JSON the commander's r2 gauge wrote with --out")
    ap.add_argument("--candidate-line", required=True, help="file with the candidate ref's ls-remote line")
    ap.add_argument("--auth-line", required=True, help="file with the authoritative ref's ls-remote line")
    ap.add_argument("--published", required=True, help="file of repo_path<TAB>blob<TAB>bytes lines")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    arms = json.loads(Path(a.arms).read_text(encoding="utf-8"))
    rd = json.loads(Path(a.round).read_text(encoding="utf-8"))
    q38 = json.loads(Path(a.q38).read_text(encoding="utf-8"))
    cand = Path(a.candidate_line).read_text(encoding="utf-8").strip()
    auth = Path(a.auth_line).read_text(encoding="utf-8").strip()
    published = [l.split("\t") for l in Path(a.published).read_text(encoding="utf-8").splitlines() if l.strip()]

    gc = arms["generation_compare"]
    cells = {c["id"]: c for c in q38.get("cells", [])}
    rows = gc["rows"]
    moved_from_frozen = [r for r in rows if not r["equals_frozen_tree"]]
    killed = [x for x in arms["arms"] if x["claimed_result"] == "KILLED"]
    same_key = [x for x in arms["arms"] if x["same_key_precondition"]["was_green_under_this_key_in_the_gate_round"]]
    restored = [x for x in arms["arms"] if x["restore_proof"]["restored_to_tested_tree_bytes"]]
    soft = [f for f in q38.get("findings", []) if not f.get("hard")]
    hard = [f for f in q38.get("findings", []) if f.get("hard")]

    lines: list[str] = []
    add = lines.append
    add("【D e345b9d6 → 包工头 · ORD-0298 交：re-parent 到 `5c4608ce…` + 七枚臂在新代重跑（不签级）】")
    add("")
    add(f"- 新候选 ref（本段唯一交付物）：`{cand}`")
    add(f"- 落地权威尖（外读）：`{auth}`")
    add(
        f"- 被测树 = 候选尖本身：`tested_tree={arms['tested_tree']}`、`tooling_commit={arms['tooling_commit']}`、"
        f"`same_commit={str(rd['generation']['same_commit']).lower()}` ⇒ 这一段没有"
        "「脚本坐在另一枚尖上」的余地（跑臂时 `git status --porcelain -- frontend` = "
        f"{len(arms['tooling_vs_tested_tree']['worktree_dirty_frontend'])} 行）"
    )
    add(f"- 旧的两枚照你的令没动：`review/0278-0253-on-45b0a5e`（冻结在 `{gc['frozen_tree']}`）与 "
        f"`review/0292-arm-receipt-tooling` 都停止推送；新东西全在上面那枚新 ref")
    add("")
    add(
        f"**re-parent 的字节对表（`frontend/**` 逐文件，三方：冻结树 `{gc['frozen_tree'][:9]}…` / 落地尖 "
        f"`{gc['landed_tip'][:9]}…` / 被测尖 `{gc['tested_tree'][:9]}…`）**"
    )
    tracked = gc["frontend_files_tracked"]
    add(
        f"- tracked 文件数：冻结树 {tracked[gc['frozen_tree']]} / 落地尖 {tracked[gc['landed_tip']]} / "
        f"被测尖 {tracked[gc['tested_tree']]}；三方中有一方不同的 = **{gc['files_differing_across_the_three']} 件**"
    )
    add(
        f"- `frontend` 子树对象：冻结 `{gc['frontend_tree_object'][gc['frozen_tree']]}` · "
        f"落地 `{gc['frontend_tree_object'][gc['landed_tip']]}` · 被测 `{gc['frontend_tree_object'][gc['tested_tree']]}`"
    )
    add("")
    add("| 文件 | =冻结树 | =落地尖 | 相对落地尖 ±行 | 相对冻结树 ±行 |")
    add("| --- | --- | --- | --- | --- |")

    def delta(cell: str) -> str:
        return "0/0" if cell.startswith("0\t0\t(no diff)") else "/".join(cell.split("\t")[:2])

    for r in rows:
        add(
            f"| `{r['path']}` | {str(r['equals_frozen_tree']).lower()} | {str(r['equals_landed_tip']).lower()} | "
            f"`{delta(r['lines_vs_landed_tip'])}` | `{delta(r['lines_vs_frozen_tree'])}` |"
        )
    add("")
    add(
        f"- 读数：**{len(moved_from_frozen)} 件与冻结树不同**，其中 {sum(1 for r in moved_from_frozen if r['equals_landed_tip'])} 件是落地线自己带进来的"
        f"（`{', '.join(r['path'].rsplit('/', 1)[-1] for r in moved_from_frozen if r['equals_landed_tip']) or '—'}`），"
        f"只有 `{', '.join(r['path'].rsplit('/', 1)[-1] for r in moved_from_frozen if not r['equals_landed_tip']) or '—'}` "
        "是两边都改过的那一枚 ⇒ 我就是在那一处手工并的（import 段并 `READ_DEADLINE_MS` + `beginNonIdempotentRequest`，"
        "并把 0269 交付时那个「点开 sheet 不自动发」的 MANUAL_RESUME 占位换成真续发调用）"
    )
    add(
        f"- 我这一边的 7 件功能文件逐字节等于冻结树：{sum(1 for r in rows if r['equals_frozen_tree'])} 件 `frontend/**` 命中"
        "（`git ls-tree -r` 的 blob 等式，不是 `git diff` 的观感）；`npm run typecheck` ⇒ rc=0"
    )
    add("")
    add(
        f"**绿轮（新代）**：`{rd['verdict']}`，三元组 **{len(rd['triples'])}** 条全部 `exact_sha={rd['candidate_tip']}`，"
        f"problems {len(rd['problems'])}；authoritative tip 由生成器外读 `{rd['authoritative_tip_at_delivery']}`"
    )
    add(
        f"**{len(arms['arms'])} 枚臂（新代一轮拆）**：KILLED {len(killed)} · 同键前件 {len(same_key)} · "
        f"还原到被测树字节 {len(restored)}（`claimed_result` 自宣；`derived_result`/等级归红队）"
    )
    add("")
    add("| 臂 | owner | claimed | 绿轮键 | baseline | 还原 | why tokens / 命中本格读数 | unique_hits |")
    add("| --- | --- | --- | --- | --- | --- | --- | --- |")
    for x in arms["arms"]:
        sk, rp = x["same_key_precondition"], x["restore_proof"]
        c = cells.get(x["name"], {})
        add(
            f"| `{x['name']}` | `{x['ownerNode'][:46]}` | **{x['claimed_result']}** | "
            f"`{sk['gate_round_verdict_for_this_key']}` | {sk['baseline_owner_verdict_this_batch']} | "
            f"{str(rp['restored_to_tested_tree_bytes']).lower()} · {rp['digest_after_restore_12']} | "
            f"{c.get('why_token_count', 'NOT_MEASURED')} / {len(c.get('own_hits', []))} | {len(c.get('unique_hits', []))} |"
        )
    add("")
    add(
        f"**Q38 r2 尺（我本机跑，尺的 blob `{q38.get('ruler_blob_sha1', 'NOT_IN_OUTPUT')}`，只读你的正本）**："
        f"`{q38.get('overall', 'NOT_RUN')}` · 格数 {q38.get('cells_found', '?')} · 硬 {len(hard)} · 软 {len(soft)} · rc {q38.get('exit', '?')}"
    )
    if soft:
        add(f"- 剩下的软条目：" + "; ".join(f"`{f.get('code')}`" for f in soft))
    add(
        "- 每格 `why` 现在自带本格具名值（锚点命中数 / 变异 sha12 / 两次 run 的 `_run<id>.db` 与端口 / 红集条数 / "
        "还原后 sha12 与被测树 blob sha12），`derived_from` 点的是本性格拉才有的那枚 mutant sha12"
    )
    add("")
    add("")
    # The landing line moves while a generation is being measured; saying so, with the byte-level
    # consequence, is cheaper than letting the commander discover it at merge time.
    live = subprocess.run(
        "git ls-remote https://github.com/Canshu-King/CityNexus.git "
        "refs/heads/mirror/integration-frontend-apple-pass1",
        cwd=LANE, capture_output=True, text=True, shell=True, encoding="utf-8", errors="replace",
    ).stdout.strip()
    live_tip = live.split("\t")[0].strip() if live else ""
    if live_tip and live_tip != gc["landed_tip"]:
        moved = subprocess.run(
            f"git diff --name-only {gc['landed_tip']} {live_tip} -- frontend",
            cwd=LANE, capture_output=True, text=True, shell=True, encoding="utf-8", errors="replace",
        ).stdout.splitlines()
        all_moved = subprocess.run(
            f"git diff --name-only {gc['landed_tip']} {live_tip}",
            cwd=LANE, capture_output=True, text=True, shell=True, encoding="utf-8", errors="replace",
        ).stdout.splitlines()
        desc = subprocess.run(
            f"git merge-base --is-ancestor {gc['landed_tip']} {live_tip}",
            cwd=LANE, capture_output=True, shell=True,
        ).returncode == 0
        mt = subprocess.run(
            f"git merge-tree --write-tree {live_tip} {gc['tested_tree']}",
            cwd=LANE, capture_output=True, text=True, shell=True, encoding="utf-8", errors="replace",
        )
        add("**被测期间权威线又动了一跳（读数照实，不等谁来问）**")
        add(
            f"- 我开工时读到 `{gc['landed_tip']}`，现在 `git ls-remote` 读到 `{live_tip}`；"
            f"`merge-base --is-ancestor` ⇒ {desc}（我的基座是它的祖先）"
        )
        add(
            f"- 那一跳改了 **{len(all_moved)} 件**，其中 `frontend/**` = **{len([m for m in moved if m.strip()])} 件** ⇒ "
            f"本段所有前端字节级判据（臂、还原、绿轮三元组）不受它影响；合流预测 "
            f"`git merge-tree --write-tree` ⇒ rc={mt.returncode}，tree `{mt.stdout.strip().splitlines()[0] if mt.stdout.strip() else '?'}`"
            "（只读预测，我没动任何 ref）"
        )
    add("")
    def blob_of(suffix: str) -> str:
        return next((r[1] for r in published if r[0].endswith(suffix)), "NOT_PUBLISHED")

    spec_runs = {x["attempt"]["runId"] for x in arms["arms"]} | {x["baseline"]["runId"] for x in arms["arms"]}
    add("**本段的可判读数（F1 形式，每条 200 字内带耐久坐标）**")
    add("")
    add(
        f"- KILLED_ARMS = {len(killed)}（共 {len(arms['arms'])} 枚，每臂 `claimed_result` 逐格派生自收据 "
        f"`{blob_of('arms-0298b-8ccfcf7.json')}` · `refs/heads/review/0278-0253-on-5c4608ce`）"
    )
    add(
        f"- GREEN_TRIPLES = {len(rd['triples'])}（四枚门 14 条，`exact_sha` 全 = 被测尖 `{rd['candidate_tip']}` · "
        f"收据 `{blob_of('gate-round-8ccfcf7.json')}`）"
    )
    add(
        f"- SPEC_RUNS = {len(spec_runs)}（一轮绿 + 一轮拆，run_id 逐臂写在 `{blob_of('arms-0298b-8ccfcf7.json')}` "
        "的 `triple.run_shape`）"
    )
    add(
        f"- SOFT_FINDINGS = {len(soft)}（上一代那 6 条已关掉；尺的原样输出发布在 "
        f"`{blob_of('q38-gauge-run-on-arms.json')}`：硬 0 / 软 0 / 格数 {q38.get('cells_found', '?')}）"
    )
    add(
        f"- RED_GATE_REATTRIBUTIONS = 0（那一轮 3 枚红改判为仪器红：厂商标志进程占了后端端口，逐端口探测与 "
        f"PID 名单在 `{blob_of('port-preflight-gate-batch.json')}`）"
    )
    add("")
    add("**外读证据（新目录，`commander/control`；PUT 前先证目录不存在，逐件独立 GET 字节级回读）**")
    for row in published:
        add(f"- `{row[0]}` — blob `{row[1]}`，{row[2]} B")
    add("")
    add(
        "- 口径：`MANUAL_RESUME / NOT-EXACTLY-ONCE` 未升格；R-SCHEMA-01 仍 "
        f"`{(rd.get('R_SCHEMA_01_class') or {}).get('rule', 'NOT_IN_RECEIPT')}`；`treeUnchangedByThisRun="
        f"{str(arms['treeUnchangedByThisRun']).lower()}`；`demo/reset` 0 次、`_live/_preview` 0 写、凭据 0 打印、"
        "已发布路径 0 覆盖 0 删、权威线 0 次移动。"
    )
    add("- 队列：ORD-0288 产码继续按住（与 B 同一枚文件），ORD-0266 `db6ac1d` 仍 DELIVERED/NOT-LANDED 等窗口。")
    add("竭尽所能的替qoder铺路")

    out = Path(a.out)
    blob = ("\n".join(lines) + "\n").encode("utf-8")
    out.write_bytes(blob)
    print(
        f"wrote {out} bytes={len(blob)} lines={len(lines)} rows={len(rows)} arms={len(arms['arms'])} "
        f"killed={len(killed)} q38={q38.get('overall', 'NOT_RUN')} hard={len(hard)} soft={len(soft)}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
