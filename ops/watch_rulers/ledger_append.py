"""Generic ledger inserter: append board entries after the ORDERS heading and/or a block before it.

Usage:  python ledger_append.py <orders_file> [deliveries_file]
Every guard that burned me today is enforced: anchors re-measured in this run, CRLF refused,
anchor uniqueness, inserted text must not contain the anchor, ids must be new, and both removal
proofs must restore the previous bytes exactly.
"""

import io
import re
import sys

LEDGER = r"D:\moodle\CITYNEXUS_AGENT_CONTROL.md"
ANCHOR = "## ORDERS（收件箱：worker 每完成一个动作、每开始下一个动作之前先读这里）"


def load(path):
    return io.open(path, encoding="utf-8", newline="\n").read().strip("\n") + "\n"


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    orders_file = sys.argv[1]
    deliv_file = sys.argv[2] if len(sys.argv) > 2 else None

    old = io.open(LEDGER, encoding="utf-8", newline="").read()
    if "\r\n" in old:
        print("ABORT: ledger is CRLF - normalise first")
        return 2
    if old.count(ANCHOR) != 1:
        print("ABORT: anchor count", old.count(ANCHOR))
        return 2

    orders = load(orders_file)
    deliv = load(deliv_file) if deliv_file else ""
    for name, blk in (("orders", orders), ("deliveries", deliv)):
        if blk and ANCHOR in blk:
            print(f"ABORT: {name} block contains the anchor")
            return 2
    new_ids = re.findall(r"^- id: (ORD-\d+)", orders, re.M)
    for oid in new_ids:
        if oid in old:
            print(f"ABORT: {oid} already exists in the ledger")
            return 2
    if deliv:
        head = deliv.splitlines()[0][:60]
        if old.count(head):
            print("ABORT: deliveries heading already present:", head)
            return 2

    step = old
    if deliv:
        i = step.index(ANCHOR)
        step = step[:i] + deliv + "\n" + step[i:]
    j = step.index(ANCHOR) + len(ANCHOR)
    new = step[:j] + "\n" + orders + step[j:]

    back = new[:j] + new[j + 1 + len(orders):]
    assert back == step, "orders removal proof failed"
    if deliv:
        assert back.replace(deliv + "\n", "", 1) == old, "deliveries removal proof failed"
    print("removal proofs: OK")

    io.open(LEDGER, "w", encoding="utf-8", newline="").write(new)
    rb = io.open(LEDGER, encoding="utf-8", newline="").read()
    print("readback equal:", rb == new)
    print("ids: %s" % ", ".join(new_ids))
    for oid in new_ids:
        print("  %dx  - id: %s" % (new.count("- id: " + oid), oid))
    print("bytes %d -> %d ; lines %d -> %d ; CRLF: %s" % (
        len(old.encode()), len(new.encode()), old.count("\n"), new.count("\n"), "\r\n" in rb))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
