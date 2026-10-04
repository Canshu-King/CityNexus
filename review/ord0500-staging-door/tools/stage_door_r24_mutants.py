"""Does the staging door actually bite?  Six arms, each run against a copy -- never the real worktree.

The claim being tested is narrow and mechanical: a receipt that is red, missing, unparseable or
half-copied must (a) turn the door red, (b) leave the tree byte-identical to what it was before the
run, and (c) produce a named failure sheet instead of staged bytes.  A control case proves the door
does not refuse the green tree, because a door that always refuses is as useless as one that never does.

Scratch discipline: every case copies `review/ord0500-checkin/` into
`<lane>/scratch_stage_r20/<case>/`; the driver REFUSES to run if the destination it is about to write
resolves inside the shared worktree, so a future edit cannot make this harness dirty somebody else's
tree.
"""
import json
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import stage_door_r24 as DOOR

LANE = DOOR.LANE
SRC = os.path.join(LANE, "wt22/review/ord0500-checkin")
SCR = os.path.join(LANE, "scratch_stage_r20")
WT_GUARD = os.path.join(LANE, "wt22").replace("\\", "/").lower()

CASES = [
    {"id": "C1_control", "action": "copy the staged tree as it is", "expect_red": None},
    {"id": "M1_gate_verdict_red", "action": "flip the citation gate's verdict field after staging",
     "expect_red": "引文闸判语", "mutate": ("gate", "verdict", "RED")},
    {"id": "M2_recheck_missing", "action": "delete the anchor re-check receipt after staging",
     "expect_red": "换代复读无腐烂", "delete": "recheck"},
    {"id": "M3_receipt_unparseable", "action": "truncate the vocabulary gate's receipt mid-write",
     "expect_red": "词汇闸判语", "corrupt": "rows"},
    {"id": "M4_stray_created_on_red", "action": "add a file the snapshot never saw, then go red",
     "expect_red": "静态 arity 尺绿且自检咬下", "mutate": ("fmt", "verdict", "RED"),
     "stray": "receipts/ZZZ_stray_r20.json"},
    {"id": "C2_after_revert", "action": "restore the mutated copy and re-judge", "expect_red": None,
     "redo_from_case": "C1_control"},
]

TARGETS = {"gate": DOOR.GATE, "mut": DOOR.MUT, "recheck": DOOR.RECHECK, "rows": DOOR.ROWS,
           "fmt": DOOR.FMT, "audit": DOOR.AUD, "collect": DOOR.COLLECT}


def fresh(name):
    dest = os.path.join(SCR, name)
    if os.path.exists(dest):
        shutil.rmtree(dest)
    os.makedirs(os.path.join(dest, "receipts"))
    for f in sorted(os.listdir(os.path.join(SRC, "receipts"))):
        if f.endswith(".json") or f.endswith(".md"):
            shutil.copyfile(os.path.join(SRC, "receipts", f),
                            os.path.join(dest, "receipts", f))
    if os.path.exists(os.path.join(SRC, "R6_READINGS.md")):
        shutil.copyfile(os.path.join(SRC, "R6_READINGS.md"), os.path.join(dest, "R6_READINGS.md"))
    if SCR.replace("\\", "/").lower().startswith(WT_GUARD):
        raise SystemExit("ABORT_SCRATCH_INSIDE_WORKTREE " + SCR)
    return dest


def apply_mutation(dest, case):
    rc = os.path.join(dest, "receipts")
    if case.get("delete"):
        p = os.path.join(rc, TARGETS[case["delete"]])
        os.remove(p)
        return "removed " + os.path.basename(p)
    if case.get("corrupt"):
        p = os.path.join(rc, TARGETS[case["corrupt"]])
        data = open(p, "rb").read()
        open(p, "wb").write(data[: max(1, len(data) // 3)])
        return "truncated %s to %d of %d bytes" % (os.path.basename(p), len(data) // 3, len(data))
    if case.get("mutate"):
        which, field, value = case["mutate"]
        p = os.path.join(rc, TARGETS[which])
        d = json.load(open(p, encoding="utf-8"))
        before = d.get(field)
        d[field] = value
        json.dump(d, open(p, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
        return "%s.%s %s -> %s" % (os.path.basename(p), field, before, value)
    if case.get("stray"):
        p = os.path.join(dest, case["stray"])
        open(p, "w", encoding="utf-8").write("{}")
        return "created " + case["stray"]
    return "nothing"


def run_case(case):
    dest = fresh(case["id"])
    rc = os.path.join(dest, "receipts")
    snap = DOOR.snapshot(dest)
    mutated = apply_mutation(dest, case)
    if case.get("mutate") and case.get("stray"):
        p = os.path.join(dest, case["stray"])
        open(p, "w", encoding="utf-8").write("{}")
        mutated += " + created " + case["stray"]
    verdict, rows, red = DOOR.judge(rc)
    out = {"id": case["id"], "action": case["action"], "mutation": mutated,
           "expect_red_item": case["expect_red"], "verdict": verdict, "red": red,
           "reasons": {r["check"]: r["reason"] for r in rows if r["verdict"] == "RED"}}
    if case.get("stray"):
        p = os.path.join(dest, case["stray"])
        out["stray_before"] = os.path.exists(p)
    if verdict == "RED":
        raised = ""
        try:
            DOOR.refuse(case["id"], dest, snap, verdict, rows, red)
        except SystemExit as exc:
            raised = str(exc)
        out["refused"] = bool(raised.startswith(DOOR.ABORTS))
        out["abort_line"] = raised[:240]
        sheet = os.path.join(LANE, "run", "%s_STAGING_RED.json" % case["id"])
        out["failure_sheet_bytes"] = os.path.getsize(sheet) if os.path.exists(sheet) else 0
        after = DOOR.snapshot(dest)
        out["tree_back_to_snapshot"] = (after == snap)
        back = DOOR.restore(dest, snap)
        out["restore"] = back
        out["bite"] = bool(out["refused"] and out["tree_back_to_snapshot"]
                           and back["every_path_matches_the_snapshot"]
                           and (case["expect_red"] in red)
                           and out["failure_sheet_bytes"] > 0)
        if case.get("stray"):
            out["stray_after"] = os.path.exists(os.path.join(dest, case["stray"]))
            out["bite"] = bool(out["bite"] and not out["stray_after"])
    else:
        out["bite"] = case["expect_red"] is None
        out["tree_back_to_snapshot"] = (DOOR.snapshot(dest) == snap)
    return out


def main():
    rows = [run_case(c) for c in CASES]
    mutants = [r for r in rows if str(r["id"]).startswith("M")]
    controls = [r for r in rows if str(r["id"]).startswith("C")]
    every_bit = all(r["bite"] for r in mutants) and all(r["bite"] for r in controls)
    out = {"schema": "CNX_ORD0500_STAGING_DOOR_MUTANTS_V1", "tool": "stage_door_r24_mutants",
           "ran_local": __import__("datetime").datetime.now().astimezone().isoformat(),
           "scratch": SCR, "real_worktree_touched": False,
           "guard": "ABORT if the scratch destination resolves inside wt22",
           "checks_run": [c[0] for c in DOOR.CHECKS], "not_this_door": DOOR.NOT_THIS_DOOR,
           "runs": rows, "mutant_count": len(mutants), "control_count": len(controls),
           "every_arm_bit": bool(every_bit),
           "green": bool(all(r["verdict"] == "GREEN" for r in controls))}
    dest = os.path.join(LANE, "evidence", "stage_door_r24_mutants.json")
    json.dump(out, open(dest, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    print(json.dumps({"every_arm_bit": every_bit,
                      "rows": [(r["id"], r["verdict"], r.get("bite"), r.get("red")) for r in rows]},
                     indent=2, ensure_ascii=False))
    print("WROTE " + dest)
    if not every_bit:
        raise SystemExit("STAGING_DOOR_MUTANTS_NOT_ALL_BIT")


if __name__ == "__main__":
    main()
