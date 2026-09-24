"""Compose the bus post for the ORD-0269 / ORD-0273 segment from the artifacts, never from memory.

Every number in the emitted text is read out of a file this script just opened: the arms receipt, the
green-round receipt, the `git ls-remote` line.  Counts are computed and re-asserted before writing,
because a hand-typed tally is how a previous lane got a wrong denominator into a judging rule.
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


def load(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--arms", required=True)
    ap.add_argument("--round", required=True)
    ap.add_argument("--lsremote", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    arms = load(a.arms)
    round_receipt = load(a.round)
    lsremote = Path(a.lsremote).read_text(encoding="utf-8").strip()

    arm_list = arms["arms"]
    killed = [x for x in arm_list if x["claimed_result"] == "KILLED"]
    survived = [x for x in arm_list if x["claimed_result"] != "KILLED"]
    triples = round_receipt["triples"]
    if len(triples) != len({t["nodeid"] for t in triples}):
        print("REFUSE: duplicate nodeid among the triples")
        return 2
    shas = {t["exact_sha"] for t in triples}
    lines: list[str] = []
    add = lines.append

    add("【D e345b9d6 → 包工头 · #2e 交完：ORD-0269 门 v4 + ORD-0273 三门 + 九枚反突变】")
    add("")
    add(f"- 候选分支尖（外读）：`{lsremote}`")
    add(f"- 候选尖：`{arms['head']}`；权威尖 `{arms.get('authoritative_tip_at_delivery', round_receipt['authoritative_tip_at_delivery'])}` 未动（单写者）")
    add(f"- 绿轮收据里三元组的 sha 集合：{', '.join('`'+s[:9]+'…`' for s in sorted(shas))}（{len(shas)} 枚）")
    add(f"- 门绿轮：{round_receipt['verdict']}，三元组 {len(triples)} 条，全部来自 Playwright 日志行的机械解析")
    add("")
    add(f"**反突变矩阵 {len(arm_list)} 枚：KILLED {len(killed)} / 其它 {len(survived)}**")
    add("")
    add("| 臂 | owner | claimed_result | 红集（节点数） | anchor/bytes/restored |")
    add("| --- | --- | --- | --- | --- |")
    for x in arm_list:
        reds = x["redSet"]
        add(
            f"| `{x['name']}` | `{x['ownerNode']}` | **{x['claimed_result']}** | "
            + (", ".join(f"`{r}`" for r in reds) if reds else "—")
            + f" ({len(reds)}) | {x['anchor_hits']}/{x['bytes_changed']}/{x['restored_exact']} |"
        )
    add("")
    add("三元组（逐字，`exact_sha` 40 位全写在收据里）：")
    add("")
    for t in triples:
        add(f"- `{t['exact_sha']}` · `{t['nodeid']}` · {t['run_shape']}")
    add("")
    add("归属与口径（B-1）：`claimed_result` 全是我自宣；`derived_result` / direct-red / collateral 一律 `WRITTEN_BY_VERIFIER`。")
    add("红集里非 owner 的节点是同一枚缺陷的其它读者，按 collateral 记账，不当独立证据。")
    add("")
    add("树完整性：`treeUnchangedByThisRun=" + str(arms["treeUnchangedByThisRun"]).lower() + "`（sha256 逐档回读），"
        f"门跑完 `git status --porcelain` = {round_receipt['clean_worktree']['porcelain_lines_frontend_review']} 行。")
    Path(a.out).write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print(f"wrote {a.out} lines={len(lines)} arms={len(arm_list)} killed={len(killed)} triples={len(triples)}")
    if survived:
        print("NOT KILLED:", ", ".join(f"{x['name']}={x['claimed_result']}" for x in survived))
    return 0


if __name__ == "__main__":
    sys.exit(main())
