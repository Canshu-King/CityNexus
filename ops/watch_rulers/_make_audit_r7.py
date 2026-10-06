"""Build audit_closure_coordinates_r7.py from the intact r6 plus the newest receipts.

Two kinds of cells, and the difference is *labelled* rather than hidden:
  * "cited-by" cells - someone (a lane or I) put a blob/size in a post, so a mismatch is a real defect;
  * "ENUMERATED(existence only)" cells - I took the blob and the size out of the directory listing
    itself, so `declared == remote` can never fail. Counting those as verified declarations would be
    exactly the vacuous-cell class the red team bit me on tonight (ORD-0283/A7: 0 cells read as 0 failures).
The runner reports the split; nobody has to read this comment to see it.
"""
import ast
import importlib.util
import io
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) or ".")
import read_remote_file as rr  # noqa: E402

SRC = "audit_closure_coordinates_r6.py"
DST = "audit_closure_coordinates_r7.py"

# (path, blob, bytes) - quoted by a human in a bus post or a ledger block, therefore auditable.
DECLARED = [
    ("live_checks/receipt_consistency_o0285_r1.py", "ed25f445392f246be9c63c23458e5a842b7f2066", 3495,
     "commander 06:5x (0285 rollup recomputation)"),
    ("live_checks/overnight_manifest_r1.py", "0a503cc936404bb6e1c8e4537fc6f0a27c1b8a79", 6635,
     "commander 07:0x (manifest generator)"),
    ("evidence/commander-overnight-manifest/manifest_r1.md", "fa82ef2674a09e1ec6c5a8025e74cbb319436780", 16386,
     "commander 07:0x (morning manifest)"),
    ("evidence/ord0285-cmdr-fix-reverify/reverify_d2305848.json", "47424f18eaea96d6977804e92f141c4afc052122", 6297,
     "lane E bus 5823334130 (ORD-0285 reverify)"),
    ("evidence/ord0288-shape-hjp3/SHAPE_ORD-0288.md", "072077ced7bd27fe1a355645ba8872024bfe6ba6", 7602,
     "lane HJ-P3 bus 5823596418 (ORD-0288 shape)"),
    ("evidence/ord0278-0253-on-landed-f86d24e/", None, None, "lane D - see enumerated cells below"),
]
DECLARED = [d for d in DECLARED if d[1]]

ENUM_DIRS = [
    ("evidence/ord0288-shape-hjp3", "lane HJ-P3"),
    ("evidence/ord0278-0253-on-landed-f86d24e", "lane D"),
    ("evidence/ord0274-reparent-laneB", "lane B"),
    ("evidence/ord0285-cmdr-fix-reverify", "lane E"),
]


def listing(d):
    items = rr.get(f"{rr.API}/repos/{rr.REPO}/contents/{d}?ref={rr.BRANCH}")
    return [(f"{d}/{it['name']}", it["sha"], it["size"]) for it in items if "name" in it]


def main():
    src = io.open(SRC, encoding="utf-8", newline="").read()
    ns = {}
    exec(compile(src.split("def main()")[0], "r6-head", "exec"), ns)
    old = list(ns["CLAIMS"])
    declared_paths = {p for p, _, _, _ in DECLARED}
    new = []
    for p, sha, size, who in DECLARED:
        new.append((p, sha, size, who))
    for d, who in ENUM_DIRS:
        for p, sha, size in listing(d):
            if p in declared_paths:
                continue
            new.append((p, sha, size, "ENUMERATED(existence only, nobody declared this size): " + who))
    marker = '    ("evidence/ord0276-hjp3-cells/shots_O0276-v8-surface-clean-port.png", "23f1ad6723b9b00ba6ceaa74cbad52e50635959f", 69332, "lane HJ-P3 ORD-0276 shot (v8 surface)"),\n'
    assert src.count(marker) == 1, "anchor count %d" % src.count(marker)
    add = "".join('    ("%s", "%s", %d, "%s"),\n' % t for t in new)
    out = src.replace(marker, marker + add, 1)
    ast.parse(out)
    io.open(DST, "w", encoding="utf-8", newline="").write(out)
    ns2 = {}
    exec(compile(out.split("def main()")[0], "r7-head", "exec"), ns2)
    claims = list(ns2["CLAIMS"])
    enum = sum(1 for c in claims if c[3].startswith("ENUMERATED"))
    print("appended", len(new), "-> claims", len(claims))
    print("  of which citable declarations:", len(claims) - enum, " existence-only enumerations:", enum)
    print("  r6 had", len(old))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
