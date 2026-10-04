"""Build the anchor-form candidate and measure before/after with the gate, in one window.

The candidate is produced by textual replacements on the file AS IT STANDS on the live tip (each old string
must match exactly once, otherwise the script stops rather than editing something I did not read).  The gate
then runs twice -- once on the tip's bytes (the before) and once on the candidate (the after) -- so "the
numeric anchors are gone, the labels resolve, and the declaration lives inside the audited file" is an answer
the tool printed, not a sentence I wrote.
"""
import json
import os
import sys

LANE = r"D:/moodle/_qoder_phone_ord0485_20260930"
sys.path.insert(0, os.path.join(LANE, "tools"))
import anchor_form_gate_r26 as G

FILE = "backend/tests/test_qoder_ord0500_journey_refusal.py"
MAIN = "backend/app/main.py"
LABELS = ["def require(", "The duplicate answer comes", "UNIQUE (journey_id, target_key)",
          '"caught_by": "unique_index",']

EDITS = [
    # 1. the shared helper, cited by its definition instead of by a line number
    ("It came from the shared `require()` helper (`backend/app/main.py:818`), which every door",
     "It came from the shared `require()` helper -- the line `def require(` in `backend/app/main.py`, "
     "which every door"),
    # 2. the two guards: drop the three line-number citations, name the places instead
    ("""    Two guards refuse a second tap on the same stop, both of them on this tip: the door looks
    its own table up first (`backend/app/main.py:4263`), and the `UNIQUE (journey_id,
    target_key)` index catches a race that lookup cannot see (`:4299`), which is the only
    branch that adds `caught_by: unique_index` (`:4316`).  A screen-side check of the""",
     """    Two guards refuse a second tap on the same stop, both of them on this tip: the door looks
    its own table up first (the block that opens with the comment `The duplicate answer comes
    first`), and the `UNIQUE (journey_id, target_key)` index catches a race that lookup cannot
    see -- its branch is the only one that writes `"caught_by": "unique_index",`.  A screen-side
    check of the"""),
    # 3. the declaration the gate reads: inside the audited file, so deleting a label is a visible diff
    ("goes red under that mutation, while the sibling spec keeps the durable half.\n    \"\"\"",
     "goes red under that mutation, while the sibling spec keeps the durable half.\n\n"
     "    Anchor labels (name form; gate: anchor_form_gate_r26.py): %s\n"
     "    The declaration lives inside this file, so dropping a label shows up as a product diff.\n"
     "    \"\"\""
     % "; ".join("`%s::%s`" % (MAIN, lab) for lab in LABELS)),
]

MANIFEST = {"files": [{"path": FILE}]}
# two labels I tried and dropped, so the next hand does not re-claim them: `select(JourneyCheckin).where(`
# and `_checkin_resolve_targets` each match twice in main.py, and a file-order claim between them is false
# (the helper's `def` sits above the handler), so the sentence must not cite them as one place.


def candidate():
    tip = G.live_tip()
    body = G.blob_text(tip, FILE)
    for old, new in EDITS:
        n = body.count(old)
        if n != 1:
            raise SystemExit("ABORT_EDIT_NOT_UNIQUE count=%s for %r" % (n, old[:60]))
        body = body.replace(old, new)
    return tip, body


def main():
    tip, body = candidate()
    open(os.path.join(LANE, "run", "anchor_form_candidate.py"), "w", encoding="utf-8",
         newline="\n").write(body)
    json.dump(MANIFEST, open(os.path.join(LANE, "evidence", "anchor_form_manifest_r26.json"), "w",
                             encoding="utf-8"), indent=2, ensure_ascii=False)
    before_v, before_rows = G.judge(MANIFEST, tip)
    after_v, after_rows = G.judge(MANIFEST, tip, src=body)
    num = lambda rows: sum(r["count"] for r in rows if r["check"] == "NUMERIC_ANCHOR_FORBIDDEN")
    reds = lambda rows: [(r["check"], str(r.get("why") or r.get("label") or "")) for r in rows
                         if r["verdict"] == "RED"]
    out = {"schema": "CNX_ORD0500_ANCHOR_FORM_APPLY_V1", "tool": "anchor_form_apply_r26", "tip": tip,
           "file": FILE,
           "before": {"verdict": before_v, "numeric_anchors": num(before_rows), "red": reds(before_rows)},
           "after": {"verdict": after_v, "numeric_anchors": num(after_rows), "red": reds(after_rows),
                     "labels": [{"label": r.get("label"), "verdict": r["verdict"], "count": r["count"]}
                                for r in after_rows if r["check"] == "LABEL_RESOLVES"],
                     "anchor_line": [r for r in after_rows if r["check"] == "ANCHOR_LINE_PRESENT"]},
           "candidate_bytes": len(body.encode("utf-8")),
           "limitation": "the gate proves the labels this file declares DO resolve; it cannot prove the "
                         "declaration is complete -- that half is a reviewer reading a diff in this file"}
    dest = os.path.join(LANE, "evidence", "anchor_form_apply_r26.json")
    json.dump(out, open(dest, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    print(json.dumps({"tip": tip[:12], "before": out["before"], "after_verdict": out["after"]["verdict"],
                      "after_numeric": out["after"]["numeric_anchors"],
                      "labels": out["after"]["labels"],
                      "anchor_line": out["after"]["anchor_line"]}, ensure_ascii=False, indent=1))
    print("WROTE " + dest)
    if after_v != "GREEN":
        raise SystemExit("ANCHOR_FORM_CANDIDATE_NOT_GREEN")


if __name__ == "__main__":
    main()
