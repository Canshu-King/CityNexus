"""Insert ORD-0161/0162 after the ORDERS heading AND repair my own block's title/status lines.

The title and status line of my 21:0x block still said "ORD-0154 收一半驳一半" after I rewrote
section ② (the claim turned out never to have been filed). Leaving that title standing would
record a dispute with a lane over text that does not exist, so both lines get replaced here,
each with a count-must-be-1 guard and an overall before/after proof.
"""

import io
import sys

LEDGER = r"D:\moodle\CITYNEXUS_AGENT_CONTROL.md"
ANCHOR = "## ORDERS（收件箱：worker 每完成一个动作、每开始下一个动作之前先读这里）"
ORDERS = r"D:\moodle\_qoder_cmdr_ref_20260921\live_checks\block_orders_161_162.md"

OLD_TITLE = "### SESSION=494abfd7 · ORD-0151 前提被我自己的探针推翻一半 + ORD-0154 收一半驳一半 + tip 漂移通告 @本机钟 21:0x"
NEW_TITLE = "### SESSION=494abfd7 · ORD-0151 前提被我自己的探针推翻一半 + 我自己两处行号按新 tip 重测 + tip 漂移通告 @本机钟 21:0x"
OLD_STATUS = "status: commander 亲测交付（① 自撤 R10 前提；② ORD-0154 收①驳②；③ `pending:` 与 canonical=null/NOT NULL 双冲突上呈；④ 未解析县现在答\"换个目的地\"；⑤ 0134② 代码级签收未复跑；⑥ tip 漂移）"
NEW_STATUS = "status: commander 亲测交付（① 自撤 R10 前提；② 自更 ORD-0113 两处行号并记下我\"把转述当交付\"的过程错；③ `pending:` 与 canonical=null/NOT NULL 双冲突上呈；④ 未解析县现在答\"换个目的地\"；⑤ 0134② 代码级签收未复跑；⑥ tip 漂移）"


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    old = io.open(LEDGER, encoding="utf-8", newline="").read()
    if "\r\n" in old:
        print("ABORT: ledger is CRLF")
        return 2
    if old.count(ANCHOR) != 1:
        print("ABORT: anchor count", old.count(ANCHOR))
        return 2
    orders = io.open(ORDERS, encoding="utf-8", newline="\n").read().strip("\n") + "\n"
    if ANCHOR in orders:
        print("ABORT: orders block contains the anchor")
        return 2
    for tag, want in ((OLD_TITLE, 1), (OLD_STATUS, 1), ("ORD-0161", 0), ("ORD-0162", 0)):
        c = old.count(tag)
        if c != want:
            print(f"ABORT: expected {want}x {tag[:40]!r}, found {c}x")
            return 2

    step = old.replace(OLD_TITLE, NEW_TITLE, 1).replace(OLD_STATUS, NEW_STATUS, 1)
    idx = step.index(ANCHOR) + len(ANCHOR)
    new = step[:idx] + "\n" + orders + step[idx:]

    # proofs
    back = new[:new.index(ANCHOR) + len(ANCHOR)] + new[new.index(ANCHOR) + len(ANCHOR) + 1 + len(orders):]
    print("proof orders removed:", back == step)
    if back != step:
        return 3
    with io.open(LEDGER, "w", encoding="utf-8", newline="") as fh:
        fh.write(new)
    rb = io.open(LEDGER, encoding="utf-8", newline="").read()
    print("readback equal:", rb == new)
    print("title fixed:", rb.count(NEW_TITLE) == 1 and rb.count(OLD_TITLE) == 0)
    print("status fixed:", rb.count(NEW_STATUS) == 1 and rb.count(OLD_STATUS) == 0)
    print("size chars %d -> %d ; bytes %d -> %d" % (len(old), len(new),
          len(old.encode()), len(new.encode())))
    for tag in ("- id: ORD-0161", "- id: ORD-0162"):
        print(f"  {new.count(tag)}x  {tag}")
    print("CRLF after write:", "\r\n" in rb)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
