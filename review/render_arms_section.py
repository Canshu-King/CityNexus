"""Render the arm table of a guard receipt into ledger markdown, so the numbers in my delivery block
are derived from the measured receipt instead of retyped from memory.

Prints one line per arm plus the two summary lines the acceptance asks for (exclusive killers and
nodes without a killing arm).  Every verdict word comes from the receipt's own fields.
"""

import json
import sys

path = sys.argv[1]
receipt = json.load(open(path, encoding="utf-8"))
lines = []
for arm in receipt["arms"]:
    lines.append(
        f"{arm['claimed_result']:9s} {arm['name']:52s} owner={arm['ownerNode']:12s} "
        f"红集[{','.join(arm['redSet']) or '-'}] 存活[{','.join(arm['survivingNodes']) or '-'}] "
        f"anchor_hits={arm['anchor_hits']} bytes_changed={arm['bytes_changed']} "
        f"restored_exact={arm['restored_exact']} 基线={arm['baseline']['summary']}"
    )
killed = sum(1 for a in receipt["arms"] if a["claimed_result"] == "KILLED")
print(f"```text\n" + "\n".join(lines) + "\n```")
print(
    f"合计 **{killed}/{len(receipt['arms'])} KILLED**；"
    f"`treeUnchangedByThisRun={receipt['treeUnchangedByThisRun']}`；"
    f"`invalidStackArms={receipt['invalidStackArms']}`；"
    f"镜像附带红：{[m for m in receipt['mirrorCollateral'] if m['mirrorRed']] or '无'}"
)
print(f"独占杀手：`{json.dumps(receipt['exclusiveKiller'], ensure_ascii=False)}`")
print(f"没有杀手格的节点：`{receipt['nodesWithoutAKillingArm']}`")
print(
    f"运行形状：{receipt['runShape']}；跑在 tag `{receipt['runTag']}`，"
    f"时刻 {receipt['at']}，文件 sha256 前后一致："
    + ", ".join(f"{k}={v[:10]}…" for k, v in receipt["filesBefore"].items())
)
