"""Erratum for the A cell published under ORD-0297, computed from both rounds' own artifacts.

Published paths are never edited or deleted, so this is a new file in the new package carrying was / now
/ the endpoint and blob of each side.  What it corrects is the *cause* I attributed, not the pixel count:
the earlier round really did render 789 characters and really did tap 0 of 3 destinations.  What was wrong
is that I read that as the never-reconnected generation being unable to move, when the covering element --
once my instrument was made to name it -- is the plan-AI sheet my own walk left open, which is an
aria-modal dialog whose backdrop is documented to sit over the bottom bar.
"""
import hashlib
import io
import json
import os
import sys
import time
import urllib.request

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
LANE = r"D:\moodle\_qoder_hjp1_o207_20260922"
TOK = io.open(r"D:\moodle\_qoder_recovery_20260919\.api_tok_20260920", encoding="utf-8").read().strip()
H = {"Authorization": "Bearer " + TOK, "Accept": "application/vnd.github+json", "User-Agent": "hjp1-verifier"}
OLD_DIR = "evidence/ord0297-hjp1-0274-post-landing/"
OLD_RECEIPT = "o297_derived_r1.json"
OLD_BLOB = "230525a007e8b08cd59cb42e1e6f716dc18db43f"


def sha1b(b):
    return hashlib.sha1(b"blob %d\x00" % len(b) + b).hexdigest()


def fetch_blob(sha):
    req = urllib.request.Request("https://api.github.com/repos/Canshu-King/CityNexus/git/blobs/" + sha,
                                 headers=H)
    with urllib.request.urlopen(req, timeout=120) as f:
        m = json.load(f)
    import base64
    return base64.b64decode(m["content"])


was_remote = fetch_blob(OLD_BLOB)
was = json.loads(was_remote.decode("utf-8"))
wa = was["arms"]["a_never_reconnects"]
wc = was["cells"]["A_never_reconnected"]

new_arm = json.load(io.open(os.path.join(LANE, "o297r_arm_o297r-a_never_reconnects-160433.json"),
                            encoding="utf-8"))
np4 = (new_arm.get("phases") or {}).get("P4") or {}
steps = np4.get("in_app_nav_offline") or []
sheet = np4.get("ui_state_before_offline") or {}

now = json.load(io.open(os.path.join(LANE, "o297r_derived_r1.json"), encoding="utf-8"))
na = now["arms"].get("a_never_reconnects", {})

OUT = {
    "kind": "ERRATUM_ON_A_PUBLISHED_READING",
    "stamped": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    "what_is_wrong": ("attribution of the cause, not the measurement: the ORD-0297 A cell reported "
                      "offline navigation as lost on the held generation (0 of 3 destinations) and I "
                      "wrote that up as a property of a device that never reconnects"),
    "was": {
        "order": "ORD-0297", "published_dir": OLD_DIR, "file": OLD_RECEIPT, "blob40": OLD_BLOB,
        "bytes_retrieved": len(was_remote), "retrieved_sha1_matches_cited_blob": sha1b(was_remote) == OLD_BLOB,
        "base_tip": wc["triples"][0]["sha"], "run_shape": wa["shape"],
        "claimed_result": wc["claimed_result"],
        "offline_first_bodyChars": wa["offline_first_bodyChars"],
        "nav_found": wa.get("nav_found"), "nav_tapped": wa["nav_tapped"], "nav_steps": wa["nav_steps"],
        "executed_offline": wa["offline_first_scripts"],
        "why_this_side_is_still_valid": ("every number above is what that round measured, and the round "
                                         "is reproducible from the published instrument; nothing here "
                                         "retroactively falsifies a reading")},
    "now": {
        "order": "ORD-0297r", "base_tip": now["base_tip"],
        "run_id": na.get("run_id"), "instrument_git_blob_sha1": (na.get("instrument") or {}).get("git_blob_sha1"),
        "offline_first_bodyChars": na.get("offline_first_bodyChars"),
        "nav_found": na.get("nav_found", sum(1 for s in steps if s.get("found"))),
        "nav_tapped": na.get("nav_tapped"), "nav_steps": na.get("nav_steps"),
        "nav_path_changed": na.get("nav_path_changed"),
        "executed_offline": na.get("offline_first_scripts"),
        "claimed_result": (now["cells"].get("A_never_reconnected") or {}).get("claimed_result"),
        "precondition_offline": na.get("precondition_offline"),
        "sheet_found_before_offline": (sheet.get("before") or {}).get("visible_boxes"),
        "close_control_used": sheet.get("control"),
        "boxes_over_nav_after_closing": (sheet.get("after") or {}).get("boxes_over_nav"),
        "blockers_named_when_it_was_still_covered": [s.get("covered_by") for s in steps
                                                     if s.get("found") and not s.get("tapped")] or
                                                    ["none: every step tapped once the sheet was closed"]},
    "code_side_evidence": ("the covering node is the plan-AI sheet's submit button and the sheet is a modal: "
                           "frontend/src/features/planning/PlanWithAiSheet.tsx blob "
                           "fd5f6e5ba2771a8d12669b9bec1ba91590970701 lines 775 (v8-sheet-backdrop, "
                           "role=dialog, aria-modal=true) and 1027 (data-testid=plan-ai-submit) at tip "
                           + str(now["base_tip"])),
    "what_survives_of_the_old_finding": [
        "an offline re-entry (full reload) on the held generation lands on the NEXT generation even though "
        "the page never reconnected -- that part of the A reading is reproduced on the new base and is now "
        "the cell's live content",
        "the partial-deploy control still bricks the client (0 characters), which is the DEPLOY_BUNDLE_RETENTION tooth",
    ],
    "what_does_not_survive": [
        "'in-app movement is lost on the never-reconnected generation' -- with the modal closed by its own "
        "close control, 3 of 3 destinations open offline on that generation",
    ],
    "instrument_limit_this_erratum_exposes": ("Playwright's setOffline(true) does not stop the service "
                                              "worker's own update fetch, so this arm cannot distinguish "
                                              "'the device never reconnected' from 'the device reconnected "
                                              "for the worker only'. The A cell therefore keeps its "
                                              "direction-reversal reading but loses any claim about what a "
                                              "truly radio-off device would do."),
    "method": ("both sides were read from bytes, not from memory: the WAS side is the published blob "
               "fetched by its 40-hex id and re-hashed, the NOW side is this package's own artifact")}
io.open(os.path.join(LANE, "o297r_erratum_on_ord0297_a.json"), "w", encoding="utf-8").write(
    json.dumps(OUT, ensure_ascii=False, indent=1))
print(json.dumps({"was_blob_match": OUT["was"]["retrieved_sha1_matches_cited_blob"],
                  "was": {k: OUT["was"][k] for k in ("base_tip", "claimed_result", "offline_first_bodyChars",
                                                     "nav_tapped", "nav_steps")},
                  "now": {k: OUT["now"][k] for k in ("base_tip", "claimed_result", "offline_first_bodyChars",
                                                     "nav_tapped", "nav_steps", "nav_path_changed",
                                                     "precondition_offline")},
                  "boxes_over_nav_after_closing": OUT["now"]["boxes_over_nav_after_closing"]},
                 ensure_ascii=False, indent=1))
assert OUT["was"]["retrieved_sha1_matches_cited_blob"], "the published blob is not the bytes I am citing"
