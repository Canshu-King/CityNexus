"""Derive deploy_bundle_r3.py: a declared gap must not leak its inner RED rows into pf['reds'].

Measured (receipt `receipts/deploy_refused_preflight_0928_181343.json`): after r2 classified the tunnel leg
correctly - `F_pre_user_surfaces = F_REMOTE_LEG_UNREACHABLE`, and every local arm GREEN - the pre-flight was
still BLOCKED with 4 reds rendered as "/assets/index-Doj2alof.js :: " and "/ :: ". Those four are the
*individual probes inside the UNREACHABLE group*: `_reds` walks the whole tree and flags any node whose own
verdict is RED, so a group the operator declared as un-provable still blocks the switch through its children.
The tool already has the right precedent for the other gap names (G_pre's DECLARED_*, F_pre's
F_UNPROBED_DECLARED: "a named gap, not a red"), so this is the same rule applied consistently, not a loosening:
the gap name itself stays out of all_green and is printed in the receipt, while a surface that ANSWERS
WRONGLY (200 + text/html) still produces its reds, because its group verdict is RED, not a gap name.
"""
from __future__ import annotations

import ast
import json
import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "deploy_bundle_r2.py")
DST = os.path.join(HERE, "deploy_bundle_r3.py")

GAPS = '''
# Names that mean "this could not be proven here" - recorded in the receipt, kept out of every green,
# and no longer allowed to block the switch through their child rows (that leak is what this revision fixes).
GAP_VERDICTS = ("F_UNPROBED_DECLARED", "F_REMOTE_LEG_UNREACHABLE", "DECLARED_NO_PRECACHE_ARRAY",
                "DECLARED_NOT_YET_PUBLISHED_PRE_SWITCH", "DECLARED_NO_PRECACHE")


'''

ANCHORS = [
    ("def preflight_before_switch(src: pathlib.Path, serve: pathlib.Path, new_refs: list[str],",
     GAPS + "def preflight_before_switch(src: pathlib.Path, serve: pathlib.Path, new_refs: list[str],"),
    ("""                hits.append(f"{who} :: {str(detail)[:200]}")
            for v in node.values():
                hits += _reds(v)""",
     """                hits.append(f"{who} :: {str(detail)[:200]}")
            if node.get("verdict") in GAP_VERDICTS:
                # a declared gap is reported by its own name elsewhere in the receipt; its child rows are
                # the probes that produced that gap, so counting them as reds would double-punish one fact
                # and, worse, block a switch whose local legs are all green.
                return hits
            for v in node.values():
                hits += _reds(v)"""),
]


def main():
    if os.path.exists(DST):
        print("REFUSED: %s exists; revisions take a new filename (Q57)" % DST, file=sys.stderr)
        return 3
    src = open(SRC, encoding="utf-8").read()
    out = src
    report = []
    for i, (old, new) in enumerate(ANCHORS, 1):
        n = out.count(old)
        if n != 1:
            print("ABORT anchor %d matched %d times: %r" % (i, n, old[:60]), file=sys.stderr)
            return 4
        out = out.replace(old, new, 1)
        report.append({"anchor": i, "matched": n})
    try:
        ast.parse(out)
    except SyntaxError as exc:
        print("ABORT: does not parse: %s" % exc, file=sys.stderr)
        return 5
    with open(DST, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(out)
    back = open(DST, encoding="utf-8").read()
    print(json.dumps({"anchors": report, "src_lines": src.count(chr(10)) + 1,
                      "out_lines": out.count(chr(10)) + 1, "written_bytes": len(back.encode("utf-8")),
                      "readback_matches": back == out,
                      "gap_constant_present": "GAP_VERDICTS" in back,
                      "guard_in_reds_walk": "if node.get(\"verdict\") in GAP_VERDICTS" in back},
                     ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
