"""Idempotent guard for the ledger's `## ORDERS` anchor.

Why this exists: the heading was eaten by whole-file rewrites twice within an hour (23:4x and 00:3x),
which silently breaks every line-anchored writer — the damage shows up as a lane's insert aborting,
not as a visible error. Lanes must not hand-edit structure, so this script lets any of them (and
patrol) repair it without a human in the loop.

Usage:
  python ledger_anchor_guard.py            # report
  python ledger_anchor_guard.py --fix      # restore if missing (proves byte-reversibility first)
"""

import io
import sys

LEDGER = r"D:\moodle\CITYNEXUS_AGENT_CONTROL.md"
HEADING = "## ORDERS（收件箱：worker 每完成一个动作、每开始下一个动作之前先读这里）"


def board_start(lines):
    """First `- id: ORD-` line that begins a run of board entries (its non-blank predecessor is
    neither a board line nor the heading). Returns index, or None."""
    for i, line in enumerate(lines):
        if not line.startswith("- id: ORD-"):
            continue
        j = i - 1
        while j >= 0 and lines[j].strip() == "":
            j -= 1
        prev = lines[j] if j >= 0 else ""
        if prev.startswith("- id: ORD-") or prev.startswith("CLAIMED:") or prev.startswith("  ") or prev == HEADING:
            continue
        return i
    return None


def main():
    fix = "--fix" in sys.argv
    raw = io.open(LEDGER, encoding="utf-8", newline="").read()
    n = raw.count(HEADING)
    print(f"anchor occurrences: {n}  (expected exactly 1)")
    if n == 1:
        print("HEALTHY: nothing to do")
        return 0
    if n > 1:
        print("ABORT: duplicate anchors — a merge went wrong; dedupe by hand, this tool will not guess.")
        return 2
    if not fix:
        print("ANCHOR_MISSING — run with --fix to restore it before writing.")
        return 3

    lines = raw.split("\n")
    at = board_start(lines)
    if at is None:
        print("ABORT: cannot locate the board's first entry — refusing to insert blind.")
        return 4
    lines.insert(at, HEADING)
    new = "\n".join(lines)
    # proof: deleting exactly the inserted heading line must reproduce the original bytes
    rebuilt = "\n".join(l for i, l in enumerate(new.split("\n")) if not (i == at and l == HEADING))
    if rebuilt != raw:
        print("ABORT: reversibility proof failed — nothing written.")
        return 5
    if "\r\n" in new:
        print("ABORT: file is CRLF — normalise first (ledger rule).")
        return 6
    io.open(LEDGER, "w", encoding="utf-8", newline="").write(new)
    rb = io.open(LEDGER, encoding="utf-8", newline="").read()
    print(f"restored before line {at + 1} | readback anchor count: {rb.count(HEADING)} | "
          f"remove-proof: {'ok' if rb == new else 'MISMATCH'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
