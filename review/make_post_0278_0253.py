"""Compose the ORD-0278 / ORD-0253 delivery post from its own receipts.

Deliberately a separate file from the ORD-0269/0273 post builder: that one carries prose about the
round it was written for ("the defect fixed this segment", its arm lineage), and reusing it here
would put another segment's sentences in front of the commander as if they belonged to this one.

Every number, sha and count is read from an artifact at write time.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

LANE = "D:/moodle/_qoder_d_lane_20260923"
INTEGRATION = "D:/moodle/_qoder_integration_20260919"
BRANCH = "review/0278-on-0269-rebased"


def sh(cmd: str, cwd: str = LANE) -> tuple[int, str]:
    p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, shell=True, encoding="utf-8", errors="replace")
    return p.returncode, ((p.stdout or "") + (p.stderr or "")).strip()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--arms", required=True)
    ap.add_argument("--round", required=True)
    ap.add_argument("--lsremote", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument(
        "--supersedes",
        default="",
        help="ref@sha of the branch generation this one replaces; it is left in place, not moved",
    )
    a = ap.parse_args()

    arms = json.loads(Path(a.arms).read_text(encoding="utf-8"))
    rd = json.loads(Path(a.round).read_text(encoding="utf-8"))
    lsremote = Path(a.lsremote).read_text(encoding="utf-8").strip()
    mirror = sh(
        "git ls-remote https://github.com/Canshu-King/CityNexus.git refs/heads/mirror/integration-frontend-apple-pass1"
    )[1].split("\t")[0].strip()
    coll = rd.get("collection") or {}
    proof = coll.get("base_proof", {})
    groups = rd.get("landing_groups") or {}
    arms_list = arms["arms"]
    killed = [x for x in arms_list if x["claimed_result"] == "KILLED"]
    triples = rd["triples"]
    lines: list[str] = []
    add = lines.append

    add("【D e345b9d6 → 包工头 · ORD-0278 交 + ORD-0253 客户端半件交（两条分开，未并一次修复）】")
    add("")
    add(f"- 候选分支尖（外读）：`{lsremote}`")
    if a.supersedes:
        add(
            f"- 取代：`{a.supersedes}` —— 那是 re-parent 之前那一代，我**没有 force-push 改它**，"
            "原样留着；两代的读数各归各的坐标，不互相折算"
        )

    add(f"- 权威尖（外读 mirror ref）：`{mirror or '?'}`；本分支起点 `{proof.get('base_tip','?')}`（= 上一段 0269/0273 的交付尖）")
    add(
        f"- 代界只说我量得起的那句：`git merge-base --is-ancestor {str(proof.get('landed_tip',''))[:9]}… HEAD` ⇒ "
        f"`{proof.get('candidate_is_descendant')}`，领先 {proof.get('commits_ahead')} 笔；相对分支起点 `frontend/` 改了 "
        f"**{len(proof.get('frontend_files_differring_from_base', []))} 件**（这是本段自己的改动，不是 re-parent 搬的）"
    )
    head_now = sh("git rev-parse HEAD")[1]
    after_round = sh(f"git diff --name-only {rd['candidate_tip']} HEAD -- frontend")[1].splitlines()
    add(
        f"- 反突变尖 `{arms['head']}`；绿轮三元组 sha `{rd['candidate_tip']}`；绿轮 {rd['verdict']}，"
        f"三元组 {len(triples)} 条，problems {len(rd['problems'])}"
    )
    add(
        f"- 发帖时分支尖 `{head_now}`：绿轮之后 `frontend/` 又改了 **{len([l for l in after_round if l.strip()])} 件**"
        "（0 件才意味着三元组指向的字节一件没动）"
    )
    add("")
    add(f"**反突变 {len(arms_list)} 枚：KILLED {len(killed)} / 其它 {len(arms_list) - len(killed)}**（`claimed_result` 自宣，`derived_result` 归红队）")
    add("")
    add("| 臂 | owner | claimed | 红集 | anchor/bytes/restored |")
    add("| --- | --- | --- | --- | --- |")
    for x in arms_list:
        red = x["redSet"]
        add(
            f"| `{x['name']}` | `{x['ownerNode']}` | **{x['claimed_result']}** | "
            + (", ".join(f"`{r.split('-')[1]}`" for r in red) or "—") + f" ({len(red)}) | "
            f"{x['anchor_hits']}/{x['bytes_changed']}/{x['restored_exact']} |"
        )
    add("")
    add("三条我自己这一轮的账（都具名，不抹）：")
    add(
        "- `K278_CLEAR_BEFORE_SEND` 第一版**臂是错的**：我把「accepted 才清」改成「无条件清」，清的动作仍在发送**之后**，"
        "根本不是 clause 5 禁止的形状 ⇒ v1 全绿存活（`ord0278-0253-arms-0278-0253-v1-c657403.json` 原样留着）。"
        "改成在 await 之前 erase 之后，v2 才由 cell1 咬住。这是臂的错，不是门的错，也不是产品的错。"
    )
    add(
        "- 一处真产品缺陷是本段的门抓出来的：续发的结果句原来挂在待续卡**里面**，而 accepted 会清 marker ⇒ 卡片卸载，"
        "「成功续发」反而一个字都不说。修法是把结果段挪到卡片外面（commit `edbfdaa0be9326045b86493baf00d4b2f6f8ac41`）。"
    )
    add(
        "- 还有一处是我上一段自己埋的：`hub.continuation*` 三枚键的**英文**词典值当时直接抄了中文（和 ORD-0273 那枚同类、"
        "同一个人）。现在改成整块扫描：`en` 块内含 CJK 的值必须为 0，例外只允许 `nav.language`（语言开关用该语言自己的文字写），"
        "例外是在扫描里**点名减去**的一枚键，不是通配放行；我没有把「与 zhCN 同键逐字节相等」这条也断言下去——"
        "那要再加一道检查才有资格说，这里只说我现在量到的。"
    )
    add("")
    if coll:
        pc = coll["commands"]["playwright_list"]
        bc = coll["commands"]["backend_collect_only"]
        add("**收集数（与收据同进程实测）**")
        add(f"- Playwright：`{coll['playwright_total_line']}` ⇒ 判据节点 **{coll['playwright_node_count']}** 个（余下为 real-seed setup）")
        add(f"  - `{pc['cmd']}`（cwd `{pc['cwd']}`，rc={pc['rc']}）")
        add(f"- 后端：`{coll['backend_collected_line']}` ⇒ **{coll['backend_collected']}** 条")
        add(f"  - `{bc['cmd']}`（cwd `{bc['cwd']}`，解释器 `{bc['interpreter']}`，rc={bc['rc']}）")
        add("")
    if groups:
        c = groups["counts"]
        add(f"**落地按组取**：{c['total']} 件 = 主线 {c['landing']} 件（`frontend/**`） + 车道脚手架 {c['lane_scaffolding']} 件（`review/**`）")
        for f in groups["mainline_needs"]:
            add(f"- `{f['status']}` +{f['added']}/-{f['removed']} `{f['path']}` — blob `{f['blob_at_head']}`")
        add("")
    add("**R-SCHEMA-01**：本轮四枚门同上一段 —— 行全部经产品 API 造（real-seed setup + R-4 的 POST /travelers、/journeys），"
        f"无 DDL 重放、无直调 ensure_schema() ⇒ `{(rd.get('R_SCHEMA_01_class') or {}).get('rule','NOT_IN_RECEIPT')}`，不重跑 schema。")
    add(
        f"- 树完整性：`treeUnchangedByThisRun={str(arms['treeUnchangedByThisRun']).lower()}`；"
        f"跑门时 `git status --porcelain` = {rd['clean_worktree']['porcelain_lines_frontend_review']} 行。"
    )
    add("")
    add("归属：`claimed_result` 全我自宣；primary/collateral 由红队定；闭单不等我，也不等我把话说满。")
    add("下一件按队列走：ORD-0266（`db6ac1d`）仍 DELIVERED/NOT-LANDED，等你的窗口；ORD-0253 客户端半件已在本分支，不再挂在「待 F」名下——F 那半已落地，这一腿现在带键。")

    out = Path(a.out)
    blob = ("\n".join(lines) + "\n").encode("utf-8")
    out.write_bytes(blob)
    print(f"wrote {out} bytes={len(blob)} lines={len(lines)} arms={len(arms_list)} killed={len(killed)} triples={len(triples)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
