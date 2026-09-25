"""Seal a superseded batch of ORD-0297r rounds by name, with its readings recomputed.

Same rule every time: a round is never deleted and never quietly dropped.  It moves out of the
deriver's glob, keeps every artifact, and carries a note saying which instrument produced it, what it
measured (recomputed from its own files, not typed), and why it cannot be cited.
"""
import hashlib
import io
import json
import os
import shutil
import sys
import time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
LANE = r"D:\moodle\_qoder_hjp1_o207_20260922"

SPEC = {
    "batch1": {
        "folder": "batch1_no_tap_decision_recorded",
        "run_ids": ["o297r-b3_primary-151812", "o297r-b3_control_partial-151943",
                    "o297r-a_never_reconnects-152057", "o297r-a_control_update_lands-152311"],
        "why": ("the instrument of this batch computed the tap decision (hit-test-self, disabled, press "
                "point) but pushed only found/tapped into the artifact, so the A arm's 'found on screen, "
                "0 of 3 reached' could not be told apart from a covered button, a disabled button or a "
                "dead navigation bar -- three different product facts. These rounds also carry the "
                "arm_artifact_correction stamp: their saved arm file had first been copied from "
                "b2_<ARM>.json, which belongs to ORD-0297, not to this order."),
        "change": ("the runner began naming the arm artifact after the run id (b2_<RUN_ID>.json) and the "
                   "step record began carrying the tap decision fields"),
    },
    "batch3": {
        "folder": "batch3_sheet_left_over_nav_by_my_own_walk",
        "run_ids": ["o297r-b3_primary-154949", "o297r-b3_control_partial-155122",
                    "o297r-a_never_reconnects-155239", "o297r-a_control_update_lands-155454"],
        "why": ("this batch is the batch that found the confound: with the covering element now named, "
                "the A arm's offline navigation is blocked by BUTTON.v8-primary-button "
                "(data-testid=plan-ai-submit, aria-disabled=true) inside DIV.v8-sheet-backdrop -- a "
                "plan-AI sheet my own walk left open. A modal sitting over the bottom bar is by design, "
                "so '0 of 3 destinations' would have described my leftover UI state and not the "
                "generation under test. The instrument now normalises that state before the outage and "
                "records it as a precondition; batch 4 is measured with it in place."),
        "change": ("added closeOpenSheet()/sheetState() before ctx.setOffline(true) on every P4 arm, "
                   "phases.P4.precondition + ui_state_before_offline recorded, and the deriver treats a "
                   "nav still covered at that moment as ARM_INVALID rather than as a product verdict"),
    }}

name = sys.argv[1]
spec = SPEC[name]
DST = os.path.join(LANE, "o297r_superseded", spec["folder"])
os.makedirs(DST, exist_ok=True)


def arm_readings(rid):
    """Numbers recomputed from this round's own artifact, never typed."""
    src = os.path.join(LANE, "o297r_arm_%s.json" % rid)
    if not os.path.exists(src):
        return {"run_id": rid, "artifact": "MISSING " + os.path.basename(src)}
    d = json.load(io.open(src, encoding="utf-8"))
    p4 = (d.get("phases") or {}).get("P4") or {}
    steps = p4.get("in_app_nav_offline") or []
    fs, rl = p4.get("first_screen_offline") or {}, p4.get("reload_offline") or {}
    return {"run_id": rid, "arm": d.get("arm"),
            "offline_first_bodyChars": fs.get("bodyChars"), "offline_first_marker": fs.get("marker"),
            "offline_first_executed": fs.get("scripts"),
            "nav_steps": len(steps), "nav_found": sum(1 for s in steps if s.get("found")),
            "nav_tapped": sum(1 for s in steps if s.get("tapped")),
            "nav_path_changed": sum(1 for s in steps if s.get("path_changed")),
            "nav_hit_test_was_self": [s.get("hit_test_was_self") for s in steps],
            "nav_disabled": [s.get("disabled") for s in steps],
            "nav_blocked_by": [((s.get("covered_by") or {}).get("tag"),
                                (s.get("covered_by") or {}).get("cls"),
                                (s.get("covered_by") or {}).get("testid"),
                                (s.get("covered_by") or {}).get("text"),
                                (s.get("covered_by") or {}).get("aria_disabled"),
                                (s.get("covered_by") or {}).get("in_nav"))
                               for s in steps if s.get("found") and not s.get("tapped")],
            "nav_bodyChars_after_each": [s.get("bodyChars") for s in steps],
            "reload_bodyChars": rl.get("bodyChars"), "reload_marker": rl.get("marker"),
            "reload_executed": rl.get("scripts"),
            "origin_html_at_js_urls": sorted({e.get("path") for e in
                                              (p4.get("origin_saw_during_offline") or {}).get("sample", [])
                                              if e.get("html_at_js_url")})}


computed = [arm_readings(r) for r in spec["run_ids"]]
moved, missing = [], []
for rid in spec["run_ids"]:
    for pat in ["b2_%s.json", "o297r_arm_%s.json", "o297r_run_%s.json",
                "o297r_stdout_%s.json", "o297r_requests_%s.jsonl"]:
        src = os.path.join(LANE, pat % rid)
        (shutil.move(src, os.path.join(DST, os.path.basename(src))) if os.path.exists(src)
         else missing.append(os.path.basename(src)))
        moved.append(os.path.basename(src))
    rd = os.path.join(LANE, "o297r_run", rid)
    if os.path.isdir(rd):
        shutil.move(rd, os.path.join(DST, rid))
        moved.append(rid + "/")

inst = open(os.path.join(LANE, "o297r_arms.cjs"), "rb").read()
# the fingerprint has to come from the rounds themselves -- the runner recorded the bytes it launched,
# and hashing the file I have already edited here would attribute a later instrument to this batch
named = []
for rid in spec["run_ids"]:
    p = os.path.join(LANE, "o297r_run_%s.json" % rid)
    if os.path.exists(p):
        r = (json.load(io.open(p, encoding="utf-8")).get("instrument") or {})
        named.append({"run_id": rid, "git_blob_sha1": r.get("git_blob_sha1"), "bytes": r.get("bytes")})
agree = len({n["git_blob_sha1"] for n in named}) == 1 and all(n["git_blob_sha1"] for n in named)
note = {"batch": name, "stamped": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "run_ids": spec["run_ids"],
        "why_superseded": spec["why"], "instrument_change": spec["change"],
        "readings_of_these_rounds": computed,
        "what_these_readings_are": ("recomputed from these rounds' own artifacts at seal time so a "
                                    "superseded batch stays auditable; they are readings, not verdicts -- "
                                    "no cell was derived from them and neither ruler ran over them"),
        "instrument_that_produced_them": {"per_run_fingerprints": named, "all_runs_same_bytes": agree,
                                          "hash_of_the_file_at_seal_time_which_is_NOT_this_batch":
                                              hashlib.sha1(b"blob %d\0" % len(inst) + inst).hexdigest()},
        "moved_or_missing": {"moved": sorted(moved), "not_present": sorted(missing)},
        "folder_now_holds": sorted(os.listdir(DST))}
io.open(os.path.join(DST, "SUPERSEDED.json"), "w", encoding="utf-8").write(json.dumps(note, ensure_ascii=False, indent=1))
print(json.dumps({"batch": name, "run_ids": spec["run_ids"], "not_present": sorted(missing),
                  "instrument_per_run": named, "all_same_bytes": agree,
                  "readings": computed}, ensure_ascii=False, indent=1)[:3200])
print("files in folder:", len(note["folder_now_holds"]))
