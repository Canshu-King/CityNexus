"""Replay the door's own two formulas out of its source and check my re-implementation matches.

Every number in the ORD-0448 block is a claim about what the *door* computes, so the comparison cannot rest
on a hand-written lookalike -- a copied predicate that is one character wider or narrower would make the
claim false while looking right. `exposure_counts` (preflight_and_land_r5.py:107-115) and the growth
expression (preflight_and_land_r5.py:353) are lifted from the door's bytes by line range, dedented, exec'd,
and run against the same inputs my arm uses.
"""
import io
import json
import os
import re
import sys

WORK = os.path.dirname(os.path.abspath(__file__))
DOOR = r"D:\moodle\_qoder_cmdr_ref_20260921\live_checks\preflight_and_land_r5.py"
GROW_LINE = 353
FN_START, FN_END = 107, 115


def dedent(lines):
    ind = min(len(l) - len(l.lstrip()) for l in lines if l.strip())
    return [l[ind:] for l in lines]


def build():
    src = io.open(DOOR, encoding="utf-8").read().split("\n")
    body = chr(10).join(dedent(src[FN_START - 1:FN_END])) + chr(10)
    ns = {"re": re, "__builtins__": __builtins__}
    exec(body, ns)
    grow_src = src[GROW_LINE - 1].strip()
    return ns["exposure_counts"], grow_src


def door_growth(door_counts, ct_keys, cc_keys):
    ct = door_counts(set(ct_keys))
    cc = door_counts(set(cc_keys))
    env = {"ct": ct, "cc": cc}
    return eval("{k: cc[k] - ct.get(k, 0) for k in cc if cc[k] > ct.get(k, 0)}", env)


def run():
    counts_src, grow_src = build()
    sys.path.insert(0, WORK)
    from exposure_arm_proposal_r1 import bucket, grow  # my re-implementation
    tip = json.load(io.open(os.path.join(WORK, "cells_tip.json"), encoding="utf-8"))
    out = {"door_lines_used": {"exposure_counts": "%s-%s" % (FN_START, FN_END),
                               "growth_expression": str(GROW_LINE),
                               "growth_text": grow_src},
           "arm_module": "exposure_arm_proposal_r1.py", "pairs": []}
    for tag in ("r3", "r4"):
        cand = json.load(io.open(os.path.join(WORK, "cells_%s.json" % tag), encoding="utf-8"))
        tk = [c["key"] for c in tip["cells"]]
        ck = [c["key"] for c in cand["cells"]]
        mine = grow(bucket(set(tk)), bucket(set(ck)))
        theirs = door_growth(counts_src, tk, ck)
        out["pairs"].append({"pair": "tip_vs_" + tag, "arm_growth": mine, "door_growth": theirs,
                             "equal": mine == theirs})
    out["all_equal"] = all(p["equal"] for p in out["pairs"])
    io.open(os.path.join(WORK, "door_formula_replay_r1.json"), "w", encoding="utf-8").write(
        json.dumps(out, ensure_ascii=False, indent=1))
    print(json.dumps(out, ensure_ascii=False, indent=1))
    return 0 if out["all_equal"] else 1


if __name__ == "__main__":
    sys.exit(run())
