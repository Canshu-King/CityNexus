"""ORD-0500 r5: print what the two sets of anchors actually say, side by side, on the tip.

A re-anchored comment is only an improvement if the reader can see that the old numbers pointed at
something else.  This reads `backend/app/main.py` on the base tree (byte-identical to the tip) and
prints the line each old citation and each new citation lands on, so the block's sentence
"旧的四处指的不是它说的那件事" is a computed comparison, not my word for it.
"""
import json
import os
import subprocess
import sys
from datetime import datetime

LANE = r"D:/moodle/_qoder_phone_ord0485_20260930"
PAIRS = [("shared require() helper", 797, 810, "def require("),
         ("door's own duplicate lookup", 3812, 3912, "existing = session.scalars("),
         ("index catch branch", 3848, 3948, "except IntegrityError as exc:"),
         ("caught_by marker", 3865, 3965, '"caught_by": "unique_index"')]


def read_rev(rev):
    """The same file as the object store holds it at `rev` -- (returncode, lines)."""
    p = subprocess.run(["git", "-C", r"D:/moodle/CityNexus", "show",
                        "%s:backend/app/main.py" % rev],
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=120)
    if p.returncode != 0:
        return p.returncode, []
    return 0, p.stdout.decode("utf-8", "replace").splitlines()


def main():
    tip = subprocess.run(["git", "-C", os.path.join(LANE, "wt23"), "rev-parse", "HEAD"],
                         stdout=subprocess.PIPE, timeout=60).stdout.decode().strip()
    prev = "514b397f96f3b5165b24865f4a544ab6f8020084"
    origin = "be0ffee216c7d24e48652427d290da848a9195cf"
    rc, prev_lines = read_rev(prev)
    rc2, origin_lines = read_rev(origin)
    lines = open(os.path.join(LANE, "wt23/backend/app/main.py"), encoding="utf-8").read().splitlines()
    rows = []
    for label, old, new, must in PAIRS:
        o = lines[old - 1].strip() if old <= len(lines) else "BEYOND_FILE"
        n = lines[new - 1].strip() if new <= len(lines) else "BEYOND_FILE"
        p = (prev_lines[old - 1].strip() if rc == 0 and old <= len(prev_lines)
             else "PREV_UNREADABLE")
        g = (origin_lines[old - 1].strip() if rc2 == 0 and old <= len(origin_lines)
             else "ORIGIN_UNREADABLE")
        rows.append({"what_the_comment_claims": label,
                     "old_line": old, "old_text": o[:100], "old_carries": must in o,
                     "old_text_on_prev_tip": p[:100], "old_carried_on_prev_tip": must in p,
                     "old_text_on_origin_tip": g[:100], "old_carried_on_origin_tip": must in g,
                     "new_line": new, "new_text": n[:100], "new_carries": must in n})
    out = {"tool": "comment_anchors_r5", "took_local": datetime.now().astimezone().isoformat(),
           "base_tree": "wt23", "tip": tip, "prev_tip": prev if rc == 0 else "UNREADABLE",
           "origin_tip": origin if rc2 == 0 else "UNREADABLE",
           "file": "backend/app/main.py", "total_lines": len(lines), "rows": rows,
           "all_new_verified": all(r["new_carries"] for r in rows),
           "old_still_pointing_at_the_claim": [r["old_line"] for r in rows if r["old_carries"]],
           "old_pointed_at_the_claim_on_prev_tip":
               [r["old_line"] for r in rows if r["old_carried_on_prev_tip"]],
           "old_pointed_at_the_claim_on_origin_tip":
               [r["old_line"] for r in rows if r["old_carried_on_origin_tip"]]}
    path = os.path.join(LANE, "evidence", "comment_anchors_r5.json")
    json.dump(out, open(path, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    print(json.dumps(out, indent=2, ensure_ascii=False))
    print("WROTE " + path)
    return 0 if out["all_new_verified"] else 1


if __name__ == "__main__":
    sys.exit(main())
