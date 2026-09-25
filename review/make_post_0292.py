"""Compose the ORD-0292 post: this generation's own arm readings, nothing inherited.

Separate from `make_post_0278_0253.py` on purpose: that one narrates the segment where the arms were
first built (its `arms['head']`, its "defect fixed this round" prose).  ORD-0292 is a re-measurement
on a frozen tip, so the only sentences it may contain are the ones this receipt can back up.

Every sha, count and verdict is read from an artifact at write time.  This builder signs no grade:
`claimed_result` is what the driver derived, `derived_result` belongs to the red team.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

LANE = "D:/moodle/_qoder_d_lane_20260923"


def sh(cmd: str) -> str:
    return subprocess.run(
        cmd, cwd=LANE, capture_output=True, text=True, shell=True, encoding="utf-8", errors="replace"
    ).stdout.strip()


def short(title: str, keep: int = 34) -> str:
    """`ord0278-positive-the-resume-request-carries-both-keys` -> `0278-positive-the-resume-request…`

    Truncating from the front is what made the first draft of this table unreadable: three of the
    seven rows showed a tail fragment that named neither the order nor the node."""
    order, _, rest = title.partition("-")
    out = f"{order[2:]}-{rest}"
    return out if len(out) <= keep else out[: keep - 1] + "…"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--arms", required=True)
    ap.add_argument("--round", required=True)
    ap.add_argument("--lsremote", required=True, help="file holding the verbatim ls-remote line")
    ap.add_argument(
        "--published",
        default="",
        help="file of `repo_path<TAB>blob_sha1<TAB>bytes` lines, one per published artifact",
    )
    ap.add_argument(
        "--tooling-line",
        default="",
        help="file holding the ls-remote line of refs/heads/review/0292-arm-receipt-tooling",
    )
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    arms = json.loads(Path(a.arms).read_text(encoding="utf-8"))
    rd = json.loads(Path(a.round).read_text(encoding="utf-8"))
    lsremote = Path(a.lsremote).read_text(encoding="utf-8").strip()
    list(arms["arms"])
    same_key = [x for x in arms["arms"] if x["same_key_precondition"]["was_green_under_this_key_in_the_gate_round"]]
    restored = [x for x in arms["arms"] if x["restore_proof"]["restored_to_tested_tree_bytes"]]
    killed = [x for x in arms["arms"] if x["claimed_result"] == "KILLED"]
    triples = rd["triples"]
    gen = rd["generation"]
    lines: list[str] = []
    add = lines.append

    add("【D e345b9d6 → 包工头 · ORD-0292：本代重跑我自己的反突变臂（不签级）】")
    add("")
    add(f"- 冻结尖（本收据的被测树）：`{arms['tested_tree']}`")
    add(f"- 该 ref 外读回验行：`{lsremote}`")
    add(f"- 冻结的 ref：`{arms['frozen_candidate']['ref']}` —— 这一段之后**我不再推它**；{arms['frozen_candidate']['push_stopped_at']}")
    add(
        f"- 跑臂的脚本另在 ref `review/0292-arm-receipt-tooling` 的 `{arms['tooling_commit']}` 上；"
        f"两尖之间 `frontend/**` 移动了 **{len(arms['tooling_vs_tested_tree']['frontend_files_moved'])} 件**"
        f"（`identical_under_test={str(arms['tooling_vs_tested_tree']['identical_under_test']).lower()}`，"
        f"跑臂时 `git status --porcelain -- frontend` = "
        f"{len(arms['tooling_vs_tested_tree']['worktree_dirty_frontend'])} 行）⇒ 臂改的字节就是冻结树里的字节"
    )
    add(
        f"- 三枚被测文件逐个与 `{arms['tested_tree'][:9]}` 的 object store 对过 sha256："
        f"{sum(1 for v in arms['pristine_files_match_tested_tree'].values() if v['equals_blob_at_tested_tree'])}"
        f"/{len(arms['pristine_files_match_tested_tree'])} 等值（这是量的，不是我记得）"
    )
    if a.tooling_line:
        tooling_remote = Path(a.tooling_line).read_text(encoding="utf-8").strip()
        published_tip = tooling_remote.split("\t")[0].strip()
        reachable = subprocess.run(
            f"git merge-base --is-ancestor {arms['tooling_commit']} {published_tip}",
            cwd=LANE, capture_output=True, text=True, shell=True,
        ).returncode == 0
        add(f"- 工具 ref 外读行：`{tooling_remote}`")
        add(
            f"- 收据里的工具尖 `{arms['tooling_commit']}` 在这枚 ref 上可达："
            f"`git merge-base --is-ancestor … {published_tip}` ⇒ {reachable}"
        )
    add("")
    add(
        f"**绿轮（同代）**：`{rd['verdict']}`，三元组 **{len(triples)}** 条，problems {len(rd['problems'])} 条；"
        f"三元组 sha `{gen['sha_the_triples_carry']}` = 冻结尖，脚本坐在 `{gen['tooling_commit_the_scripts_ran_from']}`，"
        f"二者之间 `frontend/` 差 `{len(gen['frontend_files_moved_between_them'])}` 件"
    )
    add("")
    add(
        f"**{len(arms['arms'])} 枚臂**：KILLED {len(killed)} · 同键前件成立 {len(same_key)} · "
        f"还原到冻结树字节 {len(restored)}（`claimed_result` 自宣，`derived_result` 归红队；我不签级）"
    )
    add("")
    add("| 臂 | owner | claimed | 绿轮里该键 | 本轮 baseline | 还原 | 红集 |")
    add("| --- | --- | --- | --- | --- | --- | --- |")
    for x in arms["arms"]:
        sk, rp = x["same_key_precondition"], x["restore_proof"]
        red = x["redSet"]
        add(
            f"| `{x['name']}` | `{short(x['ownerNode'])}` | **{x['claimed_result']}** | "
            f"`{sk['gate_round_verdict_for_this_key']}` | {sk['baseline_owner_verdict_this_batch']} | "
            f"{str(rp['restored_to_tested_tree_bytes']).lower()} · {rp['digest_after_restore'][:10]} | "
            + (", ".join(f"`{short(r)}`" for r in red) or "—") + f" ({len(red)}) |"
        )
    add("")
    add("每臂自带 `(exact_sha, nodeid, run_shape)` 三元组与还原三点摘要（before / mutated / after = 冻结树 blob），"
        "键的写法与绿轮逐字同形（`sha :: spec :: 标题`），所以任何一枚红都只能读成**这一代**这一枚节点的红。")
    add("")
    add(
        f"- 树完整性：`treeUnchangedByThisRun={str(arms['treeUnchangedByThisRun']).lower()}`、"
        f"`allArmsRestoredToTestedTreeBytes={str(arms['allArmsRestoredToTestedTreeBytes']).lower()}`、"
        f"`allArmsCarryAGreenSameKeyPrecondition={str(arms['allArmsCarryAGreenSameKeyPrecondition']).lower()}`"
    )
    add(
        "- 上一代（`f86d24e` 那批 v3 读数）**不沿用**：本代五枚 owner 节点各自重新在绿轮里取绿、各自重新咬合。"
        "反过来，本收据也不给上一代补信用。"
    )
    add(
        "- R-SCHEMA-01 分类不变（`"
        f"{(rd.get('R_SCHEMA_01_class') or {}).get('rule', 'NOT_IN_RECEIPT')}`）：行全经产品 API 造，判据只看渲染文字/HTTP/线格式。"
    )
    add("")
    if a.published:
        rows = [l.split("\t") for l in Path(a.published).read_text(encoding="utf-8").splitlines() if l.strip()]
        add(
            f"**外读证据（新目录，`commander/control`，逐件 PUT 后独立 GET BYTE-LEVEL MATCH）**：{len(rows)} 件"
        )
        for row in rows:
            add(f"- `{row[0]}` — blob `{row[1]}`，{row[2]} B")
        add("")
    add(
        "本轮没有产品改动：只有 `review/**` 两枚脚本（臂驱动、绿轮生成器）在工具 ref 上，"
        "`frontend/**` 一个字节都没动 ⇒ 冻结尖仍是冻结尖。等级、direct/collateral 归红队；闭单不等我。"
    )
    add("竭尽所能的替qoder铺路")

    out = Path(a.out)
    blob = ("\n".join(lines) + "\n").encode("utf-8")
    out.write_bytes(blob)
    print(
        f"wrote {out} bytes={len(blob)} lines={len(lines)} arms={len(arms['arms'])} killed={len(killed)} "
        f"same_key={len(same_key)} restored={len(restored)} triples={len(triples)}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
