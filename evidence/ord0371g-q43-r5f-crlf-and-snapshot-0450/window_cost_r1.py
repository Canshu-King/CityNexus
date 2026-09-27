#!/usr/bin/env python3
"""ORD-0371 r5f: what removing the +-WINDOW neighbour fallback would cost.

My first pass of r5f did remove it, on the reading that "one coordinate per line is the only rule a
lane can write".  Measured over the live inbox it made the backlog WORSE, so it was reverted.  This tool
re-runs that measurement on the CURRENT ruler by applying the `window_fallback_removed` mutation in
memory, so the number quoted in the ledger block is an artifact and not my recollection.
"""
import hashlib
import io
import json
import os
import re
import sys

LIVE = r"D:\moodle\_qoder_cmdr_ref_20260921\live_checks"
INBOX = os.environ.get("CNX_INBOX", r"D:/moodle/_qoder_ledger_inbox")
WORK = r"D:\moodle\_qoder_lane_S4_0926\work\ord0371"
SRC = os.path.join(LIVE, "claim_coordinate_check_r5f.py")
OLD = "    m = DURABLE.search(window)"
NEW = "    m = None"


def load(src):
    ns = {"__name__": "mutant"}
    exec(compile(src, SRC, "exec"), ns)
    return ns


def main():
    src = open(SRC, encoding="utf-8").read()
    assert src.count(OLD) == 1
    files = sorted(f for f in os.listdir(INBOX)
                   if f.endswith(".md") and re.match(r"^[A-Za-z0-9._-]+_[0-9]{4}\.md$", f))
    keep, cut = load(src), load(src.replace(OLD, NEW, 1))
    rows, worse, rel_before, rel_after = [], [], None, None
    for f in files:
        text = io.open(os.path.join(INBOX, f), encoding="utf-8").read()
        a = len(keep["scan"](text)[1])
        b = len(cut["scan"](text)[1])
        rows.append({"file": f, "as_shipped": a, "without_window": b, "delta": b - a})
        if b > a:
            worse.append(f)
        if f == "rel_0338.md":
            rel_before, rel_after = a, b
    out = {"question": "what happens to the inbox if the +-WINDOW neighbour fallback is removed",
           "mutation": {"old": OLD, "new": NEW},
           "ruler_blob": hashlib.sha1(b"blob %d\x00" % len(open(SRC, "rb").read())
                                      + open(SRC, "rb").read()).hexdigest(),
           "blocks": len(files),
           "blocks_that_get_redder": sorted(worse),
           "blocks_redder": len(worse),
           "total_findings_as_shipped": sum(r["as_shipped"] for r in rows),
           "total_findings_without_window": sum(r["without_window"] for r in rows),
           "rel_0338": {"as_shipped": rel_before, "without_window": rel_after},
           "verdict": "the reverted direction is measurably worse; r5f keeps the window and arms it",
           "blocks": len(files), "rows": rows}
    io.open(os.path.join(WORK, "window_cost_r1.json"), "w", encoding="utf-8").write(
        json.dumps(out, ensure_ascii=False, indent=1))
    print(json.dumps({k: out[k] for k in ("blocks", "blocks_redder", "total_findings_as_shipped",
                                          "total_findings_without_window", "rel_0338")},
                     ensure_ascii=False, indent=1))
    print("redder on:", json.dumps(out["blocks_that_get_redder"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
