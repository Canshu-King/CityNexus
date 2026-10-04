"""Does the anchor-form gate actually bite? Four mutants, two controls, all against scratch text.

The gate can be fed a candidate body, so nothing here touches the worktree: take the real candidate, damage
one property at a time, require the named finding.  Controls prove the honest candidate passes -- a gate that
always refuses is worth nothing, which is the same lesson the page door and the staging door learned.

The four damages are the four ways this rule could be quietly defeated: put a line number back; make the
declaration undiscoverable so nothing gets checked; keep the declaration but name something that no longer
exists; name something that matches twice and pretend it points at one place.
"""
import json
import os
import sys

LANE = r"D:/moodle/_qoder_phone_ord0485_20260930"
sys.path.insert(0, os.path.join(LANE, "tools"))
import anchor_form_gate_r26 as G
from anchor_form_apply_r26 import MANIFEST, candidate

CASES = [
    {"id": "C1_control", "action": "the candidate as written", "expect": None},
    {"id": "M1_numeric_anchor_back", "action": "put a `path:line` citation back into the sentence",
     "expect": "NUMERIC_ANCHOR_FORBIDDEN",
     "edit": ("A screen-side", "A screen-side (`backend/app/main.py:4264`)")},
    {"id": "M2_declaration_undiscoverable", "action": "rename the declaration so the gate cannot find it",
     "expect": "ANCHOR_LINE_PRESENT", "edit": ("Anchor labels (", "anchor notes (")},
    {"id": "M3_label_no_longer_exists", "action": "declare a label that is not in the file it names",
     "expect": "LABEL_RESOLVES",
     "edit": ("`backend/app/main.py::def require(`",
              "`backend/app/main.py::def require_that_no_longer_exists(`")},
    {"id": "M4_label_ambiguous", "action": "declare a label that matches twice, with no qualifier",
     "expect": "LABEL_RESOLVES",
     "edit": ('`backend/app/main.py::"caught_by": "unique_index",`',
              "`backend/app/main.py::existing = session.scalars(`")},
    {"id": "C2_after_revert", "action": "re-judge the untouched candidate", "expect": None},
]


def run(case, tip, base):
    body = base
    if case.get("edit"):
        a, b = case["edit"]
        if body.count(a) != 1:
            return {"id": case["id"], "bite": False, "verdict": "SETUP_ERROR",
                    "expect": case["expect"],
                    "note": "anchor text matched %s times: %r" % (body.count(a), a[:60])}
        body = body.replace(a, b)
    verdict, rows = G.judge(MANIFEST, tip, src=body)
    reds = [r["check"] for r in rows if r["verdict"] == "RED"]
    why = {r["check"]: str(r.get("why")) for r in rows if r["verdict"] == "RED"}
    out = {"id": case["id"], "action": case["action"], "verdict": verdict, "red": reds, "why": why,
           "expect": case["expect"]}
    out["bite"] = (verdict == "GREEN") if case["expect"] is None else (case["expect"] in reds)
    return out


def main():
    tip, base = candidate()
    rows = [run(c, tip, base) for c in CASES]
    mutants = [r for r in rows if str(r["id"]).startswith("M")]
    controls = [r for r in rows if str(r["id"]).startswith("C")]
    every = all(r["bite"] for r in mutants) and all(r["bite"] for r in controls)
    out = {"schema": "CNX_ORD0500_ANCHOR_FORM_MUTANTS_V1", "tool": "anchor_form_gate_mutants_r26",
           "tip": tip, "runs": rows, "mutant_count": len(mutants), "control_count": len(controls),
           "every_arm_bit": bool(every), "worktree_written": False,
           "scratch_note": "the gate is fed candidate bodies in memory; nothing under wt22 is written"}
    dest = os.path.join(LANE, "evidence", "anchor_form_gate_mutants_r26.json")
    json.dump(out, open(dest, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    print(json.dumps({"every_arm_bit": every,
                      "rows": [(r["id"], r["verdict"], r["bite"], r.get("red")) for r in rows]},
                     ensure_ascii=False)[:1200])
    print("WROTE " + dest)
    if not every:
        raise SystemExit("ANCHOR_FORM_MUTANTS_NOT_ALL_BIT")


if __name__ == "__main__":
    main()
