"""Re-read every block this session reported as INSERTED and say which ones actually landed.

The applier printed INSERTED for the #359 block while the ledger held zero hits, so a reported
insertion is not proof of delivery.  Now that the landing gate exists, the same family of claims gets
re-checked: for each archived block carrying this session's flower name, the gate is run again and any
RED is named.

Selftest: the census must also be able to call a title that nobody ever posted RED, otherwise a whole
sheet of GREENs would mean nothing.
"""

import datetime
import io
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "trial", "human_walk"))

import _cmdr_ledger_landing_check_r300 as gate  # noqa: E402

PROCESSED = gate.PROCESSED
SESSION = "494abfd7"
RECEIPT = os.path.join(ROOT, "trial", "results", "20261026_gozero",
                       "bw301-this-sessions-blocks-landed.txt")


def heading_of(path):
    for line in io.open(path, encoding="utf-8", errors="replace").read().split("\n"):
        if line.startswith("### "):
            return line[4:].strip()
    return ""


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    today = datetime.date.today().isoformat()
    rows = []
    for name in sorted(os.listdir(PROCESSED)):
        if not name.startswith(SESSION) or ".inserted_" not in name:
            continue
        path = os.path.join(PROCESSED, name)
        stamp = datetime.date.fromtimestamp(os.path.getmtime(path)).isoformat()
        if stamp != today:
            continue
        rows.append((name, stamp, heading_of(path)))

    out = ["BLOCKS THIS SESSION REPORTED AS INSERTED - RE-READ AGAINST THE LEDGER bw301",
           "LEDGER %s" % gate.LEDGER,
           "SESSION %s | archive files dated %s: %d" % (SESSION, today, len(rows))]
    red = []
    for name, stamp, heading in rows:
        out.append("  %s  (%s)" % (name, stamp))
        out.append("      heading %r" % heading[:90])
        printed = io.StringIO()
        real, sys.stdout = sys.stdout, printed
        try:
            rc = gate.check(heading)
        finally:
            sys.stdout = real
        verdict = "GREEN" if rc == 0 else "RED"
        out.append("      gate: %s  %s" % (verdict, printed.getvalue().strip()))
        if rc != 0:
            red.append((name, heading))

    # negative control: a title nobody posted must read RED, or every GREEN above is hollow
    bogus = "这张标题从未进过任何账本_zzz_control"
    printed = io.StringIO()
    real, sys.stdout = sys.stdout, printed
    try:
        bogus_rc = gate.check(bogus)
    finally:
        sys.stdout = real
    bites = bogus_rc == 7
    out.append("NEGATIVE_CONTROL unseen title reads %s (%s)"
               % ("RED as required" if bites else "GREEN - the gate is blind",
                  printed.getvalue().strip()))
    out.append("TALLY checked=%d green=%d red=%d" % (len(rows), len(rows) - len(red), len(red)))
    if red:
        out.append("BLOCKS THAT DID NOT LAND (re-insert required):")
        for name, heading in red:
            out.append("  %s  %r" % (name, heading[:80]))
    else:
        out.append("BLOCKS_THAT_DID_NOT_LAND none")
    verdict_ok = bites and not red
    out.append("VERDICT %s" % ("every block this session claimed as delivered is in the ledger, and "
                               "the gate can still see a red" if verdict_ok else
                               "see the RED rows above - a reported insertion without a ledger hit"))
    io.open(RECEIPT, "w", encoding="utf-8", newline="\n").write("\n".join(out) + "\n")
    for row in out:
        print(row)
    print("WROTE %s" % RECEIPT)
    return 0 if verdict_ok else 7


if __name__ == "__main__":
    sys.exit(main())
