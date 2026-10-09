"""Roll back MY OWN duplicate insertion of 00:0x.

What happened: at 00:0x I re-did work that this session had already done and already logged at
21:0x, and I appended a second copy of both blocks.  Proof it was a duplicate, measured in the
same command that inserted it: `- id: ORD-0157` was already present once before the write.

This removes exactly the two payloads I appended, byte for byte, and refuses to write unless each
matches once.  It does NOT touch the older, correct blocks (different wording), and it does not
touch anything a lane appended after me - which is why the result cannot equal the pre-insert
snapshot: the ledger grew while I was diagnosing.
"""

import io
import sys

LEDGER = r"D:\moodle\CITYNEXUS_AGENT_CONTROL.md"
DELIV = r"D:\moodle\_qoder_cmdr_ref_20260921\live_checks\block_r10recheck_2100.md"
ORDERS = r"D:\moodle\_qoder_cmdr_ref_20260921\live_checks\block_orders_155_160.md"


def load(path):
    return io.open(path, encoding="utf-8", newline="\n").read().strip("\n") + "\n"


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    old = io.open(LEDGER, encoding="utf-8", newline="").read()
    print("before: chars", len(old), "lines", old.count("\n") + 1, "CRLF", "\r\n" in old)

    deliv = load(DELIV)
    orders = load(ORDERS)
    targets = [("deliveries", "\n" + deliv), ("orders", "\n" + orders)]
    new = old
    for name, payload in targets:
        n = new.count(payload)
        print(f"{name}: payload occurrences = {n}")
        if n != 1:
            print(f"ABORT: {name} matched {n} times, refusing")
            return 2
        new = new.replace(payload, "", 1)

    for probe, want in (
        ("### SESSION=494abfd7 · ORD-0151 前提被我自己的探针推翻一半 + ORD-0154 收一半驳一半", 0),
        ("### SESSION=494abfd7 · ORD-0151 前提被我自己的探针推翻一半 + 我自己两处行号按新 tip 重测", 1),
        ("- id: ORD-0157", 1),
        ("- id: ORD-0158", 1),
        ("- id: ORD-0155", 1),
        ("- id: ORD-0156", 1),
        ("- id: ORD-0160", 1),
        ("- id: ORD-0159", 0),
    ):
        got = new.count(probe)
        print(f"  count {got} (want {want})  {probe[:56]}")
        if got != want:
            print("ABORT: post-condition failed, not writing")
            return 3

    with io.open(LEDGER, "w", encoding="utf-8", newline="") as fh:
        fh.write(new)
    rb = io.open(LEDGER, encoding="utf-8", newline="").read()
    print("after: chars", len(rb), "lines", rb.count("\n") + 1, "CRLF", "\r\n" in rb)
    print("readback equal:", rb == new, "| removed chars:", len(old) - len(rb))
    print("ORDERS heading occurrences:", rb.count("## ORDERS（收件箱"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
