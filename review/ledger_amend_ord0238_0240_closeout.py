"""Append the close-out lines to this lane's own ORD-0238/0240 block, just before the ORDERS anchor.

Mine is the last block in the delivery region, so appending at the end of my region is only safe if
the region really ends at the anchor and holds exactly one of my headings -- both are re-measured in
this run, and the neighbours on either side are re-read after the write.
"""

import hashlib
import sys

LEDGER = "D:/moodle/CITYNEXUS_AGENT_CONTROL.md"
ANCHOR = "## ORDERS（收件箱：worker 每完成一个动作、每开始下一个动作之前先读这里）"
HEAD = "### 🇬🇧 e345b9d6（SESSION=e345b9d6）ORD-0238 + ORD-0240 交付"
NEIGHBOUR = "### 🧩 e345b9d6（SESSION=e345b9d6）ORD-0232 交付"
EXTRA = (
    "**收口补充（同一次运行里续写，坐标都是当场读的）**：总线评论 **`5789046368`**"
    "（`Canshu-King/CityNexus-Workspace#1`，`bus_post.py` 回读 `matches: True`、issue 评论数 318）；"
    "仲裁窗口已敲门，**并在敲门正文里当场自首一条**：我进窗口时页面上有一枚 `停止回答`、而 C 的 A-2 那一轮"
    "只有工具调用没有正文，我按 09-23 早上的重启经验先点了停止 ⇒ **那一轮有可能是我中断的**。"
    "仲裁接到的句子是 `Fetching Latest D and Rerunning A-2 Reviews`（它正在重跑 A-2），"
    "所以这一格不改变任何产品判断，只作为现场事实入账；如果那一轮的结论出现在总线，以总线为准。\n\n"
)


def digest(t: str) -> str:
    return hashlib.sha256(t.encode("utf-8")).hexdigest()[:16]


def main() -> int:
    text = open(LEDGER, encoding="utf-8", newline="").read()
    if EXTRA.strip().split("（")[0] in text:
        print("ABORT: the close-out line is already in the ledger")
        return 3
    if text.count(ANCHOR) != 1 or text.count(HEAD) != 1:
        print(f"ABORT: anchor={text.count(ANCHOR)} head={text.count(HEAD)}")
        return 2
    start, end = text.find(HEAD), text.find(ANCHOR)
    region = text[start:end]
    if [ln for ln in region.splitlines() if ln.startswith("### ") and not ln.startswith(HEAD)]:
        print("ABORT: my region holds a foreign heading")
        return 4
    if not region.rstrip().endswith("我只对「我这一段可逆」负责。"):
        print(f"ABORT: my block does not end where I think it does: ...{region.rstrip()[-40:]}")
        return 5
    updated = text[:end] + EXTRA + text[end:]
    open(LEDGER, "w", encoding="utf-8", newline="").write(updated)

    after = open(LEDGER, encoding="utf-8", newline="").read()
    checks = {
        "block_once": after.count(HEAD) == 1,
        "anchor_unique": after.count(ANCHOR) == 1,
        "extra_once": after.count("收口补充（同一次运行里续写") == 1,
        "neighbour_intact": NEIGHBOUR in after,
        "pure_lf": after.count("\r") == 0,
        "reversible": (after[:end] + after[end + len(EXTRA):]) == text,
    }
    print(
        f"bytes {len(text.encode('utf-8')):,} -> {len(after.encode('utf-8')):,}  "
        f"sha {digest(text)} -> {digest(after)}  "
        + "  ".join(f"{k}={'ok' if v else 'FAIL'}" for k, v in checks.items())
    )
    return 0 if all(checks.values()) else 6


if __name__ == "__main__":
    sys.exit(main())
