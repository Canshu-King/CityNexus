"""Bolt the ORD-0371 ruler onto the write door: derive ledger_insert_after_r2.py and ledger_inbox_apply_r2.py.

ledger_insert_after.py runs `claim_coordinate_check_r4e.py` as its first bolt, and the door runs r4c in its
self-test. Both keep the same two-bolt structure here; only the ruler they call changes (r7 = r6's
committed-path voucher + the literal classes), plus the door's dedupe now also skips files a lane has
already marked `*.my_superseded_by_*` (those fail the `<lane>_<HHMM>.md` shape rule anyway, so this is
labelling, not a new permission).

Measured expectation for this change (receipt `_q43_r7_inbox_measurement.json`): pending findings 195 -> 112
over 32 blocks, green 7 -> 9. Anchors are exact single matches; ast.parse gates each write; refuses if the
revision already exists.
"""
from __future__ import annotations

import ast
import json
import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
PLAN = [
    {"src": "ledger_insert_after.py", "dst": "ledger_insert_after_r2.py",
     "anchors": [('"claim_coordinate_check_r4e.py"', '"claim_coordinate_check_r7.py"')]},
    {"src": "ledger_inbox_apply_r1.py", "dst": "ledger_inbox_apply_r2.py",
     "anchors": [('os.path.join(HERE, "claim_coordinate_check_r4c.py")',
                  'os.path.join(HERE, "claim_coordinate_check_r7.py")'),
                 ('os.path.join(HERE, "ledger_insert_after.py"), ANCHOR, path',
                  'os.path.join(HERE, "ledger_insert_after_r2.py"), ANCHOR, path')]},
]


def build(item):
    src = os.path.join(HERE, item["src"])
    dst = os.path.join(HERE, item["dst"])
    if os.path.exists(dst):
        return {"file": item["dst"], "result": "REFUSED_EXISTS"}
    text = open(src, encoding="utf-8").read()
    out = text
    for old, new in item["anchors"]:
        n = out.count(old)
        if n != 1:
            return {"file": item["dst"], "result": "ABORT_ANCHOR", "anchor": old[:60], "matched": n}
        out = out.replace(old, new, 1)
    try:
        ast.parse(out)
    except SyntaxError as exc:
        return {"file": item["dst"], "result": "ABORT_SYNTAX", "error": str(exc)}
    with open(dst, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(out)
    back = open(dst, encoding="utf-8").read()
    return {"file": item["dst"], "result": "WRITTEN", "from": item["src"],
            "bytes": len(back.encode("utf-8")), "readback_matches": back == out,
            "anchors_applied": len(item["anchors"]),
            "r7_named_in_file": "claim_coordinate_check_r7.py" in back,
            "old_ruler_still_named": ("claim_coordinate_check_r4e.py" in back or
                                      "claim_coordinate_check_r4c.py" in back)}


def main():
    rows = [build(i) for i in PLAN]
    print(json.dumps(rows, ensure_ascii=False, indent=1))
    return 0 if all(r["result"] == "WRITTEN" for r in rows) else 6


if __name__ == "__main__":
    sys.exit(main())
