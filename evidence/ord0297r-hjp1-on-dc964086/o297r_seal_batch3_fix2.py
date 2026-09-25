"""Seal the fourth round of batch 3 that my own seal script missed, and correct the batch's note.

Two defects, both mine, both found by the batch inventory rather than by reading:

1. `o297r_seal_batch3_fix.py` renamed the A-control run id inside SUPERSEDED.json (`155433` -> `155454`)
   but never moved the round's five artifacts, so the batch folder claimed four rounds while holding three,
   and the fourth was still sitting in the deriver's glob where a regenerated receipt could reach it.
2. The note therefore listed a run id that exists nowhere on this machine, which is exactly the kind of
   coordinate that must not survive.

The fix moves the artifacts, recomputes this round's readings from its own files, records was/now and
proves afterwards that the lane glob holds nothing but the four cited runs.
"""
import glob
import hashlib
import io
import json
import os
import shutil
import sys
import time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
LANE = r"D:\moodle\_qoder_hjp1_o207_20260922"
DST = os.path.join(LANE, "o297r_superseded", "batch3_sheet_left_over_nav_by_my_own_walk")
WAS, NOW = "o297r-a_control_update_lands-155433", "o297r-a_control_update_lands-155454"


def arm_readings(rid):
    """Numbers recomputed from this round's own artifact -- never transcribed from memory."""
    src = os.path.join(DST, "o297r_arm_%s.json" % rid)
    if not os.path.exists(src):
        return {"run_id": rid, "artifact": "MISSING " + os.path.basename(src)}
    d = json.load(io.open(src, encoding="utf-8"))
    p4 = (d.get("phases") or {}).get("P4") or {}
    steps = p4.get("in_app_nav_offline") or []
    fs, rl = p4.get("first_screen_offline") or {}, p4.get("reload_offline") or {}
    ui = p4.get("ui_state_before_offline") or {}
    return {"run_id": rid, "arm": d.get("arm"), "precondition_offline": p4.get("precondition"),
            "sheet_boxes_over_nav_before": (ui.get("before") or {}).get("boxes_over_nav"),
            "close_control": ui.get("control"),
            "sheet_boxes_over_nav_after": (ui.get("after") or {}).get("boxes_over_nav"),
            "offline_first_bodyChars": fs.get("bodyChars"), "offline_first_marker": fs.get("marker"),
            "offline_first_executed": fs.get("scripts"),
            "nav_steps": len(steps), "nav_found": sum(1 for s in steps if s.get("found")),
            "nav_tapped": sum(1 for s in steps if s.get("tapped")),
            "nav_path_changed": sum(1 for s in steps if s.get("path_changed")),
            "nav_hit_test_was_self": [s.get("hit_test_was_self") for s in steps],
            "nav_blocked_by": [((s.get("covered_by") or {}).get("tag"),
                                (s.get("covered_by") or {}).get("cls"),
                                (s.get("covered_by") or {}).get("outer"))
                               for s in steps if s.get("found") and not s.get("tapped")],
            "outage_update_attempt": p4.get("update_inside_outage"),
            "reload_bodyChars": rl.get("bodyChars"), "reload_marker": rl.get("marker"),
            "reload_executed": rl.get("scripts")}


moved, absent = [], []
for pat in ["b2_%s.json", "o297r_arm_%s.json", "o297r_run_%s.json",
            "o297r_stdout_%s.json", "o297r_requests_%s.jsonl"]:
    src = os.path.join(LANE, pat % NOW)
    if os.path.exists(src):
        shutil.move(src, os.path.join(DST, os.path.basename(src)))
        moved.append(os.path.basename(src))
    else:
        absent.append(os.path.basename(src))
if os.path.isdir(os.path.join(LANE, "o297r_run", NOW)):
    shutil.move(os.path.join(LANE, "o297r_run", NOW), os.path.join(DST, NOW))
    moved.append(NOW + "/")

note = json.load(io.open(os.path.join(DST, "SUPERSEDED.json"), encoding="utf-8"))
ids = [r if r != WAS else NOW for r in note["run_ids"]]
assert WAS not in ids and NOW in ids, "run id replacement did not take"
note["run_ids"] = ids
note["readings_of_these_rounds"] = [arm_readings(r) for r in ids]
note["instrument_that_produced_them"] = {
    "per_run_fingerprints": [{"run_id": r,
                              **((json.load(io.open(os.path.join(DST, "o297r_run_%s.json" % r),
                                                    encoding="utf-8")).get("instrument") or {}))}
                             for r in ids if os.path.exists(os.path.join(DST, "o297r_run_%s.json" % r))]}
note["instrument_that_produced_them"]["all_runs_same_bytes"] = len(
    {f.get("git_blob_sha1") for f in note["instrument_that_produced_them"]["per_run_fingerprints"]}) == 1
note["corrections"] = (note.get("corrections") or []) + [{
    "stamped": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "was": WAS, "now": NOW,
    "defect_1": ("the earlier fix renamed the run id inside this note but never moved the round's five "
                 "artifacts, so the folder claimed four rounds while holding three"),
    "defect_2": ("a run id listed here existed nowhere on the machine -- a coordinate that must not survive"),
    "found_by": "o297r_sealed_batches.py's mutual-exclusion check, not by reading the note",
    "files_moved_now": moved, "still_absent": absent,
    "no_reading_changed": "every value above is recomputed from these rounds' own artifacts"}]
note["folder_now_holds"] = sorted(os.listdir(DST))
io.open(os.path.join(DST, "SUPERSEDED.json"), "w", encoding="utf-8").write(json.dumps(note, ensure_ascii=False, indent=1))

lane_glob = sorted(os.path.basename(p) for p in glob.glob(os.path.join(LANE, "o297r_run_*.json")))
print(json.dumps({"moved": moved, "still_absent": absent, "run_ids": ids,
                  "folder_file_count": len(note["folder_now_holds"]),
                  "instrument_fingerprints": note["instrument_that_produced_them"],
                  "lane_glob_now": lane_glob,
                  "a_control_readings": [r for r in note["readings_of_these_rounds"] if r["run_id"] == NOW]},
                 ensure_ascii=False, indent=1)[:1800])
assert not absent, "artifacts that should have been in the lane are missing"
assert NOW not in "".join(lane_glob), "the sealed round is still visible to the deriver"
assert all("artifact" not in r for r in note["readings_of_these_rounds"]), "a round in this note is unreadable"
