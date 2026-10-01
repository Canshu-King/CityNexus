"""ORD-0512 -- one table: which map-gate tests were red in every generation's run.

The containment tool answers "did this order add a red", and it can only do that against a base that is
itself steady. It is not: the tip's bytes were run four times here and the same two ORD-0497 arms are red
in some runs and green in others, so a single base run would either frame me for their flake or let me
claim a fix that isn't mine. This prints the matrix instead of a verdict, per test, per run, so the
reader sees the same rows I did.

usage: python ord0512_family_flap_r1.py [log ...]      (default: the lane's seven family logs)
"""
import io
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ord0512_family_diff_r1 import reds, totals  # noqa: E402

GATE = r"D:/moodle/_qoder_b_ord0417_20260928/evidence/ord0512/gate"
DEFAULT = [
    ("base_run1_tipbytes_r2era", "ord0512fam_base.log"),
    ("base_run2_tipbytes_r2era", "ord0512fam_base2.log"),
    ("candidate_r2era", "ord0512fam_cand.log"),
    ("candidate_r2bytes", "ord0512fam_cand2.log"),
    ("base_tipbytes_run1", "ord0512fam_tipbase.log"),
    ("candidate_tipbytes", "ord0512fam_tipcand.log"),
    ("base_tipbytes_run2", "ord0512fam_tipbase2.log"),
]


def main() -> int:
    args = sys.argv[1:]
    runs = [(os.path.basename(a).replace(".log", ""), a) for a in args] if args else DEFAULT
    rows = {}
    per_run = {}
    for label, name in runs:
        path = os.path.join(GATE, name) if not os.path.isabs(name) else name
        if not os.path.exists(path):
            print("MISSING %s" % path)
            continue
        per_run[label] = totals(path)
        for key in reds(path):
            rows.setdefault(key, set()).add(label)
    order = [label for label, _ in runs if os.path.exists(os.path.join(GATE, _)) or os.path.exists(_)]
    out = []
    out.append("totals per run: " + json.dumps(per_run, ensure_ascii=False))
    stable, flapping, mine = [], [], []
    base_labels = [l for l in order if "base" in l]
    cand_labels = [l for l in order if "candidate" in l]
    for key, seen in sorted(rows.items()):
        on_base = any(l in seen for l in base_labels)
        never_base = all(l not in seen for l in base_labels)
        on_cand = any(l in seen for l in cand_labels)
        line = "%-2s %-2s %-70s %s" % ("B" if on_base else "-", "C" if on_cand else "-", key[:70], sorted(seen))
        out.append(line)
        if never_base and on_cand:
            mine.append(key)
        elif on_base and on_cand and not all(l in seen for l in base_labels):
            flapping.append(key)
        elif on_base:
            stable.append(key)
    out.append("")
    out.append("red in every base run and in the candidate: %d" % len(stable))
    out.append("red in some base runs (the family moves on its own): %d" % len(flapping))
    out.append("red ONLY on the candidate, in no base run: %d -> %s" % (len(mine), mine))
    text = "\n".join(out)
    io.open(r"D:/moodle/_qoder_b_ord0417_20260928/run/ord0512_family_flap_r1.txt", "w", encoding="utf-8").write(text)
    print(text.encode("ascii", "replace").decode()[:1200])
    print("WROTE=run/ord0512_family_flap_r1.txt")
    return 0


if __name__ == "__main__":
    sys.exit(main())
