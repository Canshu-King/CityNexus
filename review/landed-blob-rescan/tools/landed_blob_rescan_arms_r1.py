"""Arms for the landed-content re-scan: it must not confuse "missing", "different" and "I could not look".

The ruler already produced a true positive on first use (one of this lane's landed hands is gone from the
line), so what still needs proving is the failure modes: a wrong blob must not read as SAME, a path that is
not there must not read as CHANGED, and a broken read must never be folded into either answer -- it is its
own answer.  The control is the case where nothing is wrong: it has to say HELD, or the tool is just noise.
"""
import json
import os
import subprocess
import sys

LANE = r"D:/moodle/_qoder_phone_ord0485_20260930"
sys.path.insert(0, os.path.join(LANE, "tools"))
import landed_blob_rescan_r1 as L


def blob_of(tip, path):
    rc, out, _e = L.git("rev-parse", "%s:%s" % (tip, path))
    m = out.strip()[:40]
    return m if len(m) == 40 else None


def rows_for(tip, coords):
    return L.scan(tip, {"coords": coords})


def main():
    tip = L.live_tip()
    held_path = "review/ord0500-staging-door/tools/stage_readings_r7.py"
    held_blob = blob_of(tip, held_path)
    cases = []

    # C1 control: the coordinate as it stands on the line
    v1 = rows_for(tip, [{"path": held_path, "expect": held_blob}])[0]["verdict"] if held_blob else "NO_FIXTURE"
    cases.append({"id": "C1_control", "expect_verdict": "SAME", "got": v1,
                  "bite": v1 == "SAME", "note": held_path})

    # M1: right path, wrong blob -> must be CHANGED, never SAME
    wrong = "0" * 40 if held_blob and held_blob[0] != "0" else "1" * 40
    v2 = rows_for(tip, [{"path": held_path, "expect": wrong}])[0]["verdict"]
    cases.append({"id": "M1_wrong_blob", "expect_verdict": "CHANGED", "got": v2, "bite": v2 == "CHANGED"})

    # M2: path that is not on the line -> must be ABSENT, not CHANGED
    gone = "review/ord0500-anchor-form/tools/anchor_form_gate_r27.py"
    v3 = rows_for(tip, [{"path": gone, "expect": "e" * 40}])[0]["verdict"]
    cases.append({"id": "M2_path_absent", "expect_verdict": "ABSENT", "got": v3, "bite": v3 == "ABSENT"})

    # M3: an unreadable ref -> NOT_REACHED, and it is never a pass
    cs, why = L.coordinates("refs/heads/review/0afdb49b-this-ref-does-not-exist-r9")
    cases.append({"id": "M3_ref_unreadable", "expect_verdict": "NOT_REACHED",
                  "got": "NOT_REACHED" if cs is None else "READ_OK", "bite": cs is None, "why": why})

    # M4: an unreadable revision must not be answered as "the path is missing" -- the fatal line repeats
    # the sha and says `does not exist`, so a sloppy reader reports ABSENT for a read that never happened
    bogus = "deadbeef" * 5
    r4 = rows_for(bogus, [{"path": held_path, "expect": held_blob or "0" * 40}])[0]["verdict"]
    cases.append({"id": "M4_broken_read_not_absent", "expect_verdict": "UNREADABLE_ON_LINE",
                  "got": r4, "bite": r4 == "UNREADABLE_ON_LINE"})

    every = all(c["bite"] for c in cases)
    out = {"schema": "CNX_LANDED_BLOB_RESCAN_ARMS_V1", "tool": "landed_blob_rescan_arms_r1",
           "live_tip": tip, "ran_local": __import__("datetime").datetime.now().astimezone().isoformat(),
           "every_arm_bit": bool(every), "runs": cases,
           "note": "M2's fixture is a real path this lane published on a ref that the line no longer carries"}
    dest = os.path.join(LANE, "evidence", "landed_blob_rescan_arms_r1.json")
    json.dump(out, open(dest, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    print(json.dumps({"every_arm_bit": every, "tip": tip[:12],
                      "runs": [(c["id"], c["expect_verdict"], c["got"], c["bite"]) for c in cases]},
                     ensure_ascii=False, indent=1))
    print("WROTE " + dest)
    if not every:
        raise SystemExit("RESCAN_ARMS_NOT_ALL_BIT")


if __name__ == "__main__":
    main()
