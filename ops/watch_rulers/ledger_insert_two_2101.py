"""Two ledger insertions in ONE read-modify-write, each with a byte-identity proof.

  * deliveries block -> immediately BEFORE the ORDERS heading (end of ## DELIVERIES section)
  * new board entries -> immediately AFTER the ORDERS heading (top of the inbox)

Guards learned the hard way today: anchors re-measured in this very run (lanes rewrite the whole
file), the ORDERS heading must be unique, neither block may contain the other's anchor, and after
writing we read the file back and prove both blocks appear exactly once.
"""

import io
import sys

LEDGER = r"D:\moodle\CITYNEXUS_AGENT_CONTROL.md"
ANCHOR = "## ORDERS（收件箱：worker 每完成一个动作、每开始下一个动作之前先读这里）"
DELIV = r"D:\moodle\_qoder_cmdr_ref_20260921\live_checks\block_r10recheck_2100.md"
ORDERS = r"D:\moodle\_qoder_cmdr_ref_20260921\live_checks\block_orders_155_160.md"


def load(path):
    raw = io.open(path, encoding="utf-8", newline="\n").read()
    return raw.strip("\n") + "\n"


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    old = io.open(LEDGER, encoding="utf-8", newline="").read()
    crlf = "\r\n" in old
    print("ledger chars", len(old), "CRLF present:", crlf)
    if crlf:
        print("ABORT: ledger flipped to CRLF again - normalise first")
        return 2
    n = old.count(ANCHOR)
    if n != 1:
        print(f"ABORT: anchor matched {n} times")
        return 2

    deliv = load(DELIV)
    orders = load(ORDERS)
    for name, blk in (("deliveries", deliv), ("orders", orders)):
        if ANCHOR in blk:
            print(f"ABORT: {name} block contains the anchor")
            return 2

    idx = old.index(ANCHOR)
    # 1) deliveries before the heading
    step1 = old[:idx] + deliv + "\n" + old[idx:]
    # 2) orders right after the heading line
    j = step1.index(ANCHOR) + len(ANCHOR)
    new = step1[:j] + "\n" + orders + step1[j:]

    # proofs: removing each inserted payload must restore the previous state
    k = new.index(ANCHOR) + len(ANCHOR)
    back1 = new[:k] + new[k + 1 + len(orders):]
    back2 = back1.replace(deliv + "\n", "", 1)
    print("proof orders:", back1 == step1)
    print("proof deliveries:", back2 == old)
    if not (back1 == step1 and back2 == old):
        print("ABORT: byte-identity proof failed")
        return 3

    with io.open(LEDGER, "w", encoding="utf-8", newline="") as fh:
        fh.write(new)

    rb = io.open(LEDGER, encoding="utf-8", newline="").read()
    print("written; readback equal:", rb == new)
    print("size chars %d -> %d ; utf-8 bytes %d -> %d ; lines %d -> %d" % (
        len(old), len(new), len(old.encode()), len(new.encode()),
        old.count("\n"), new.count("\n")))
    for tag in ("### SESSION=494abfd7 · ORD-0151 前提被我自己的探针推翻一半",
                "- id: ORD-0157", "- id: ORD-0158", "- id: ORD-0155",
                "- id: ORD-0156", "- id: ORD-0160"):
        print(f"  {new.count(tag)}x  {tag[:52]}")
    print("CRLF after write:", "\r\n" in rb)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
