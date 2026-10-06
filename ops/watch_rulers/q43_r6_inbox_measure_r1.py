"""Measure ORD-0371's real effect: run the door's current ruler and r6 over every pending inbox block.

Both arms run in the SAME process over the SAME bytes, so the delta is the arm, not the input. Nothing here
rewrites a block; it only records verdicts. This is the denominator the ledger block will cite.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
PY = sys.executable
INBOX = r"D:/moodle/_qoder_ledger_inbox"
OLD = os.path.join(HERE, "claim_coordinate_check_r4c.py")
NEW = os.path.join(HERE, "claim_coordinate_check_r6.py")


def run(ruler, path):
    p = subprocess.run([PY, ruler, "--text", path], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    txt = p.stdout or ""
    verdict = None
    for tok in ("Q43_GATE_GREEN_CITED", "Q43_GATE_GREEN", "Q43_GATE_RED", "NO_CLAIM_FOUND"):
        if '"verdict": "%s"' % tok in txt or "%s" % tok in txt:
            verdict = tok
            break
    claims = None
    for line in txt.splitlines():
        if line.strip().startswith('"claims_checked"'):
            claims = line.split(":", 1)[1].strip().strip(",").strip('"')
    return p.returncode, verdict, claims, len(txt)


def main():
    rows = []
    for name in sorted(os.listdir(INBOX)):
        if not name.endswith(".md"):
            continue
        path = os.path.join(INBOX, name)
        rc_old, v_old, c_old, _ = run(OLD, path)
        rc_new, v_new, c_new, _ = run(NEW, path)
        rows.append({"block": name, "old_rc": rc_old, "old_verdict": v_old,
                     "new_rc": rc_new, "new_verdict": v_new, "flipped": v_old != v_new})
    tally = {}
    for r in rows:
        k = "%s -> %s" % (r["old_verdict"], r["new_verdict"])
        tally[k] = tally.get(k, 0) + 1
    out = {"blocks": len(rows), "tally_by_transition": tally,
           "flipped_count": sum(1 for r in rows if r["flipped"]),
           "new_green": sum(1 for r in rows if r["new_verdict"] in ("Q43_GATE_GREEN", "Q43_GATE_GREEN_CITED")),
           "new_red": sum(1 for r in rows if r["new_verdict"] == "Q43_GATE_RED"),
           "rows": rows}
    dst = os.path.join(HERE, "_q43_r6_inbox_measurement.json")
    with open(dst, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
    print(json.dumps({k: v for k, v in out.items() if k != "rows"}, ensure_ascii=False, indent=1))
    print("receipt=%s (%d B)" % (dst, os.path.getsize(dst)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
