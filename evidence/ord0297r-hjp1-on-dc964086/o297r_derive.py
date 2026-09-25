"""ORD-0297r: derive B3 and A on base `dc964086`, four cells, `claimed_result` only.

Differences from my ORD-0297 deriver, each one because the order or an earlier mistake asked for it:

* **run id resolution is explicit and total.** The runner now saves each round under its own run id, so
  this file lists every run id it can find for an arm and judges the newest, while still recording the
  older ones -- a re-run must not be able to hide the round it replaced.
* **`(sha, nodeid, shape)` plus `runId` on every cell**, with `shape` naming the ports, the one-shot DB
  file name and the instrument bytes, so a reader can point at exactly one run.
* **four cells** (B3, its partial-deploy control, A, its in-outage-update control), each `why` rendered
  from its own arm's measured values; nothing shared, so `derived_from` is not needed and the Q38 ruler
  can see per-cell ownership.
* **`derived_result` is null everywhere** -- the red team closes; I only state what I measured.
* the marker channel is read from the build receipt instead of a literal string, because a stale marker
  literal in the instrument is what made that channel dead in the previous round.
"""
import glob
import io
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
LANE = r"D:\moodle\_qoder_hjp1_o207_20260922"
NOT = "NOT_MEASURED"
NOT_RECORDED = "NOT_RECORDED_BY_INSTRUMENT"
BASE = "dc964086c9d412573ac19d70b24b30e6c3ee6168"
OUT = os.environ.get("O297R_OUT", "o297r_derived_r1.json")
BUNDLE = re.compile(r"index-[\w-]+\.js")
WORKERISH = re.compile(r"v10-sw\.js|workbox-")
SPEC = json.load(io.open(os.path.join(LANE, "o297r_arms.json"), encoding="utf-8"))
BUILDS = json.load(io.open(os.path.join(LANE, "o297r_builds.json"), encoding="utf-8"))
REF_TIP = json.load(io.open(os.path.join(LANE, "o297r_ref_tip_read.json"), encoding="utf-8"))
BASES = json.load(io.open(os.path.join(LANE, "o297r_bases.json"), encoding="utf-8"))
MARKER = SPEC["b3_primary"]["marker_value"]

# cell -> (primary arm, its control arm, the fields the control is allowed to differ on)
CELLS = {
    "B3_offline_after_convergence": ("b3_primary", "b3_control_partial",
                                     ("offline_document_boots", "usable_offline",
                                      "stays_on_new_generation_offline", "no_page_origin_contact_offline")),
    "A_never_reconnected": ("a_never_reconnects", "a_control_update_lands",
                            ("usable_offline", "offline_first_marker",
                             "stayed_on_installed_generation_offline", "outage_update_landed")),
}
CONTROL_CELLS = {"B3_control_partial_deploy": "b3_control_partial",
                 "A_control_update_lands": "a_control_update_lands"}


def sha1b(b):
    return hashlib_sha1(b)


def hashlib_sha1(b):
    import hashlib
    return hashlib.sha1(b"blob %d\x00" % len(b) + b).hexdigest()


def kv(pairs):
    names = [n for n, _ in names_distinct(pairs)]
    assert len(names) == len(set(names)), "duplicate label in a why-sentence: %s" % names
    return "; ".join("%s=%s" % (n, json.dumps(v, ensure_ascii=False)
                                if isinstance(v, (list, dict, bool)) else v) for n, v in pairs)


def names_distinct(pairs):
    return pairs


def bundles(scripts):
    got = []
    for s in scripts or []:
        m = BUNDLE.search(s)
        if m:
            got.append(m.group(0))
    return sorted(set(got))


def blocker_of(s):
    """Say, per offline navigation attempt, what stood in the way -- in the reading's own terms.

    'found but not tapped' is three different product facts (covered / disabled / absent), and a cell
    printing only 0-of-3 lets the next reader guess which one it was.
    """
    if s.get("tapped") and s.get("path_changed"):
        return "%s: tapped, path changed" % s.get("label")
    if not s.get("found"):
        return "%s: not on screen (visible buttons: %s)" % (
            s.get("label"), (s.get("visible_buttons_when_missing") or [])[:6])
    if s.get("disabled"):
        return "%s: the button reports disabled" % s.get("label")
    c = s.get("covered_by") or {}
    return ("%s: covered by %s.%s%s at press point %s, button itself at %s in a %s viewport%s"
            % (s.get("label"), c.get("tag") or "?", (c.get("cls") or "??").split(" ")[0],
               " (its text: %r)" % c.get("text") if c.get("text") else "",
               s.get("press_point"), s.get("button_rect"), s.get("viewport"),
               " -- inside the nav element itself" if c.get("in_nav") else ""))


def find_runs(arm):
    """Every run id this machine holds for the arm, newest last; the newest is what is judged."""
    found = []
    for p in sorted(glob.glob(os.path.join(LANE, "o297r_run_*.json"))):
        try:
            rec = json.load(io.open(p, encoding="utf-8"))
        except Exception:                                       # noqa: BLE001
            continue
        if rec.get("arm") != arm:
            continue
        found.append({"run_id": rec.get("run_id"), "started_at": rec.get("started_at"),
                      "run_file": os.path.basename(p),
                      "arm_file": rec.get("arm_artifact_saved_as"),
                      "requests_file": os.path.basename(rec.get("requests_saved_as") or "")})
    found.sort(key=lambda x: (x.get("started_at") or ""))
    return found


def judge(arm):
    runs = find_runs(arm)
    assert runs, "no run of %s on this machine" % arm
    newest = runs[-1]
    run = json.load(io.open(os.path.join(LANE, newest["run_file"]), encoding="utf-8"))
    a = json.load(io.open(os.path.join(LANE, newest["arm_file"]), encoding="utf-8"))
    req = [json.loads(l) for l in io.open(os.path.join(LANE, "o297r_requests_%s.jsonl" % newest["run_id"]),
                                          encoding="utf-8") if l.strip()]
    inst = a.get("instrument") or {}
    p3 = (a.get("phases") or {}).get("P3") or {}
    p4 = (a.get("phases") or {}).get("P4") or {}
    new_b, old_b = run["identity_next"]["bundle"], run["identity_installed"]["bundle"]
    off_at = p4.get("offline_at_epoch") or 0
    in_off = [e for e in req if e.get("t", 0) * 1000 >= off_at]
    off_first, steps, reload_ = p4.get("first_screen_offline") or {}, p4.get("in_app_nav_offline") or [], \
        p4.get("reload_offline") or {}
    j = {
        "arm": arm, "kind": run.get("arm_kind"), "cells_this_arm_judges": run.get("cells_this_arm_judges"),
        "run_id": newest["run_id"], "run_id_started_at": newest["started_at"],
        "all_run_ids_for_this_arm": [r["run_id"] for r in runs],
        "artifacts": {"run": newest["run_file"], "arm": newest["arm_file"],
                      "origin_events": "o297r_requests_%s.jsonl" % newest["run_id"]},
        "base_tip": run["installed_commit"], "next_label": run["next_commit"],
        "expected_marker": MARKER,
        "instrument": run.get("instrument", NOT_RECORDED),
        "arm_artifact_correction": run.get("arm_artifact_correction"),
        "backend_tree": (run.get("backend_tree") or {}).get("dir"),
        "old_bundle": old_b, "new_bundle": new_b,
        "shape": ("one arm of o297r: 390x844 touch / zh-CN persistent profile / one-shot SQLite named "
                  "for the run under the arm dir / ports %s / origin serves shell from current_root.txt and "
                  "/assets from asset_root.txt / instrument bytes named in the receipt")
                 % json.dumps(run.get("ports"), ensure_ascii=False),
        "fatal": a.get("fatal"), "arm_invalid_reason": a.get("arm_invalid_reason"),
        "arm_exit": run.get("arm_exit"), "arm_wall_s": run.get("arm_wall_s"),
        "probe_smoke": inst.get("probe_smoke", NOT),
        "instrument_self_errors": sorted({e for e in inst.get("pageErrors", [])
                                          if re.search(r"is not defined|SNAP_SOURCE|GEN_MARKER|Cannot read", e)}),
        "pageErrors": inst.get("pageErrors", [])[:6],
        "journey_id": p3.get("journey_id"), "retry_presses_made": p3.get("retry_presses_made", NOT),
        "nav_labels_at_creation": p3.get("nav_labels_at_creation"),
        "update_trigger": p3.get("update_trigger"),
        "outage_update_attempt": p4.get("update_inside_outage", NOT),
        # what the screen was shaped like when the outage began: movement counted with a sheet still over
        # the bottom bar is a reading about my leftover state, not about the generation
        "precondition_offline": p4.get("precondition", NOT),
        "ui_state_before_offline": p4.get("ui_state_before_offline", NOT),
        "asset_root_written": (p3.get("assets") or {}).get("asset_root"),
        "pointer_read_back_ok": (p3.get("assets") or {}).get("read_back_ok"),
        "executed_after_transition": bundles((p3.get("after_written") or {}).get("scripts")),
        "marker_after_transition": (p3.get("after_written") or {}).get("marker"),
        "instrument_navigations": [e.get("label") or "goto" for e in inst.get("navEvents", [])
                                   if e.get("mine")],
        "offline_first_bodyChars": off_first.get("bodyChars", NOT),
        "offline_first_leafCount": off_first.get("leafCount", NOT),
        "offline_first_marker": off_first.get("marker", NOT),
        "offline_first_scripts": bundles(off_first.get("scripts")),
        "offline_first_rendered": off_first.get("headings"),
        "nav_steps": len(steps), "nav_tapped": sum(1 for s in steps if s.get("tapped")),
        "nav_found": sum(1 for s in steps if s.get("found")),
        "nav_path_changed": sum(1 for s in steps if s.get("path_changed")),
        "nav_bodyChars": [s.get("bodyChars", NOT) for s in steps],
        # why a tap did not land is part of the reading: a covered button and a dead navigation bar are
        # different product facts, and "0 of 3" alone cannot tell them apart
        "nav_tap_evidence": [{"label": s.get("label"), "found_on_screen": s.get("found"),
                              "tapped": s.get("tapped"), "hit_test_was_self": s.get("hit_test_was_self", NOT),
                              "button_disabled": s.get("disabled", NOT), "press_point": s.get("press_point", NOT),
                              "hit_label": s.get("hit_label"),
                              # what, if anything, sat on top of the button: a blocked destination has
                              # to name its blocker or the cell says nothing about why movement failed
                              "covered_by": s.get("covered_by", NOT_RECORDED),
                              "button_rect": s.get("button_rect", NOT_RECORDED),
                              "viewport": s.get("viewport", NOT_RECORDED),
                              "scroll_settled": s.get("scroll_settled", NOT_RECORDED),
                              "buttons_visible_when_not_found": (s.get("visible_buttons_when_missing")
                                                                 or s.get("onScreen") or [])[:8]}
                             for s in steps],
        "nav_executed": [bundles(s.get("scripts")) for s in steps],
        # one short clause per destination that did not open, naming what stood in its way: the cell that
        # claims "offline movement is lost" has to say by what, not only that a tap was refused
        "nav_blockers": [blocker_of(s) for s in steps],
        "reload_bodyChars": reload_.get("bodyChars", NOT),
        "reload_bundles": bundles(reload_.get("scripts")),
        "reload_marker": reload_.get("marker", NOT),
        "reload_http_status": reload_.get("http_status", NOT),
        "reload_rendered": reload_.get("headings"),
        "origin_hits_during_offline": len(in_off),
        "page_level_hits_offline": [{"kind": e.get("kind"), "path": e.get("path")} for e in in_off
                                    if not WORKERISH.search(e.get("path") or "")],
        "worker_update_hits_offline": sorted({e.get("path") for e in in_off
                                              if WORKERISH.search(e.get("path") or "")}),
        "origin_html_at_js_urls": sorted({e["path"] for e in req if e.get("html_at_js_url")}),
        "journeys_rows_before": ((run.get("db_before") or {}).get("counts") or {}).get("journeys"),
        "journeys_rows_after": ((run.get("db_after") or {}).get("counts") or {}).get("journeys"),
        "tables_measured": (run.get("db_after") or {}).get("tables_measured"),
        "isolation": run.get("isolation"),
        # the arm directory is deleted on purpose, so the DB is named as the path it had, with
        # the deletion proof beside it rather than a claim that a file survived
        "db_file": "o297r_run/%s/one_shot_%s.sqlite3 (deleted with the arm directory; "
                   "rundir_deleted=%s, db_leftovers=%s)" % (
            newest["run_id"], newest["run_id"],
            (run.get("isolation") or {}).get("rundir_deleted"),
            (run.get("isolation") or {}).get("db_leftovers")),
    }
    j["converged_by_executed_bundle"] = new_b in j["executed_after_transition"]
    j["converged_by_marker"] = j["marker_after_transition"] == MARKER
    j["converged_onto_next"] = j["converged_by_executed_bundle"]
    every = [j["offline_first_scripts"]] + j["nav_executed"] + [j["reload_bundles"]]
    j["stays_on_new_generation_offline"] = bool(all(new_b in e for e in every)
                                                and not any(old_b in e for e in every))
    j["stayed_on_installed_generation_offline"] = bool(all(old_b in e for e in every)
                                                       and not any(new_b in e for e in every))
    leaves_off = [x for x in (j["offline_first_rendered"] or []) if x]
    leaves_re = [x for x in (j["reload_rendered"] or []) if x]
    j["offline_document_boots"] = bool(isinstance(j["offline_first_bodyChars"], int)
                                       and j["offline_first_bodyChars"] > 0
                                       and isinstance(j["offline_first_leafCount"], int)
                                       and j["offline_first_leafCount"] > 0
                                       and isinstance(j["reload_bodyChars"], int)
                                       and j["reload_bodyChars"] > 0
                                       and (leaves_off or leaves_re))
    j["offline_reload_is_app_notice"] = bool(isinstance(j["reload_bodyChars"], int)
                                             and j["reload_bodyChars"] > 0
                                             and any("网络不可用" in x for x in leaves_re)
                                             and any(("归因详情" in x or "重试" in x) for x in leaves_re))
    j["offline_app_names_saved_copy"] = bool(any("已保存的只读副本" in x for x in leaves_re)
                                             or any("没有丢失" in x for x in leaves_re))
    j["usable_offline_strict"] = bool(isinstance(j["offline_first_bodyChars"], int)
                                      and j["offline_first_bodyChars"] > 200
                                      and j["nav_steps"] >= 2 and j["nav_path_changed"] == j["nav_steps"]
                                      and all(isinstance(x, int) and x > 100 for x in j["nav_bodyChars"])
                                      and isinstance(j["reload_bodyChars"], int)
                                      and j["reload_bodyChars"] > 200)
    j["usable_offline"] = bool(j["offline_document_boots"] and j["nav_steps"] >= 2
                               and j["nav_path_changed"] == j["nav_steps"] and len(leaves_off) >= 3
                               and j["offline_reload_is_app_notice"])
    # the A cell's claim has two halves that a single boolean would blur: the screen the device is holding
    # must be usable, and it must still be the same generation after an offline re-entry. They measured
    # apart from each other here, so they are recorded apart.
    j["usable_on_held_generation"] = bool(
        isinstance(j["offline_first_bodyChars"], int) and j["offline_first_bodyChars"] > 200
        and j["nav_steps"] >= 2 and j["nav_tapped"] == j["nav_steps"]
        and j["nav_path_changed"] == j["nav_steps"]
        and all(isinstance(x, int) and x > 100 for x in j["nav_bodyChars"])
        and bool(old_b in (j["offline_first_scripts"] or []))
        and j.get("precondition_offline") == "NAV_CLEAR_BEFORE_OUTAGE")
    j["no_page_origin_contact_offline"] = not j["page_level_hits_offline"]
    j["outage_update_landed"] = bool(isinstance(j["outage_update_attempt"], dict)
                                     and j["outage_update_attempt"].get("updated"))
    j["worker_update_hits_during_outage"] = bool(j["worker_update_hits_offline"])
    j["instrument_ok"] = bool(isinstance(j["probe_smoke"], dict) and j["probe_smoke"].get("ok")) \
        and not j["instrument_self_errors"] and j.get("fatal") is None \
        and j.get("precondition_offline") == "NAV_CLEAR_BEFORE_OUTAGE"
    return j


def why_for(x, extra):
    return kv([
        ("arm", x["arm"]), ("kind", x["kind"]), ("run_id", x["run_id"]),
        ("run_started_at", x["run_id_started_at"]), ("base_tip", x["base_tip"]),
        ("backend_tree", x["backend_tree"]), ("expected_marker", x["expected_marker"]),
        ("generation_pair", "%s (installed) vs %s (next)" % (x["old_bundle"], x["new_bundle"])),
        ("instrument_ok", x["instrument_ok"]), ("probe_smoke", x["probe_smoke"]),
        ("instrument_self_errors", x["instrument_self_errors"]), ("pageErrors", x["pageErrors"]),
        ("arm_exit", x["arm_exit"]), ("arm_wall_s", x["arm_wall_s"]),
        ("converged_by_executed_bundle", x["converged_by_executed_bundle"]),
        ("converged_by_marker", x["converged_by_marker"]),
        ("marker_after_transition", x["marker_after_transition"]),
        ("executed_after_transition", x["executed_after_transition"]),
        ("update_trigger", x["update_trigger"]), ("outage_update_attempt", x["outage_update_attempt"]),
        ("outage_update_landed", x["outage_update_landed"]),
        ("asset_root_written", x["asset_root_written"]),
        ("pointer_read_back_ok", x["pointer_read_back_ok"]),
        ("instrument_navigations", x["instrument_navigations"]),
        ("offline_first_bodyChars", x["offline_first_bodyChars"]),
        ("offline_first_leafCount", x["offline_first_leafCount"]),
        ("offline_first_marker", x["offline_first_marker"]),
        ("offline_first_executed", x["offline_first_scripts"]),
        ("nav_tapped_of_steps", "%d/%d" % (x["nav_tapped"], x["nav_steps"])),
        ("nav_path_changed", x["nav_path_changed"]), ("nav_bodyChars", x["nav_bodyChars"]),
        ("nav_blockers", x["nav_blockers"]), ("instrument_fingerprint", x["instrument"]),
        ("nav_executed_per_screen", x["nav_executed"]),
        ("reload_bodyChars", x["reload_bodyChars"]), ("reload_http_status", x["reload_http_status"]),
        ("reload_executed", x["reload_bundles"]), ("reload_marker", x["reload_marker"]),
        ("offline_document_boots", x["offline_document_boots"]),
        ("offline_reload_is_app_notice", x["offline_reload_is_app_notice"]),
        ("offline_app_names_saved_copy", x["offline_app_names_saved_copy"]),
        ("usable_offline", x["usable_offline"]),
        ("usable_on_held_generation", x["usable_on_held_generation"]),
        ("precondition_offline", x["precondition_offline"]),
        ("sheet_boxes_over_nav_before_offline",
         (x["ui_state_before_offline"].get("before") or {}).get("boxes_over_nav")
         if isinstance(x["ui_state_before_offline"], dict) else x["ui_state_before_offline"]),
        ("usable_offline_strict_200_chars", x["usable_offline_strict"]),
        ("stays_on_new_generation_offline", x["stays_on_new_generation_offline"]),
        ("stayed_on_installed_generation_offline", x["stayed_on_installed_generation_offline"]),
        ("origin_hits_during_outage_total", x["origin_hits_during_offline"]),
        ("page_level_hits_during_outage", len(x["page_level_hits_offline"])),
        ("worker_update_hits_during_outage", x["worker_update_hits_offline"]),
        ("origin_html_at_js_urls", x["origin_html_at_js_urls"]),
        ("journeys_rows", "%s before / %s after" % (x["journeys_rows_before"], x["journeys_rows_after"])),
        ("journey_id", x["journey_id"]), ("tables_measured", x["tables_measured"]),
        ("one_shot_db", x["db_file"]), ("rundir_deleted", x["isolation"]["rundir_deleted"]),
        ("nav_labels_at_creation", x["nav_labels_at_creation"]),
        ("retry_presses", x["retry_presses_made"]), ("arm_invalid_reason", x["arm_invalid_reason"]),
    ] + extra) + " | rendered during the outage: " + json.dumps(
        {"first_screen": x["offline_first_rendered"], "after_reload": x["reload_rendered"]},
        ensure_ascii=False)


out = {"order": "ORD-0297r", "base_tip": BASE,
       "why_this_round_exists": ("the authoritative line moved two hops since ORD-0297; four files under "
                                 "frontend/src differ between 5c4608ce and dc964086, so by Q24 the earlier "
                                 "readings are a previous generation's, not this line's"),
       "ref_tip_read": REF_TIP, "bases": BASES,
       "verifier": "1a986a24 HJ-P1",
       "claim_semantics": "claimed_result is mine and computed from the fields printed beside it; "
                          "derived_result is null on every cell because closure belongs to the red team's "
                          "reading, not the deliverer's (B-1)",
       "instrument": {"arms": "o297r_arms.cjs", "runner": "o297r_run.py", "origin": "o297r_origin.py",
                      "spec": "o297r_arms.json", "builder": "o297r_build.py",
                      "marker_channel": ("read from the build receipt (%s); the previous round's "
                                         "instrument compared a stale literal from an earlier order, which "
                                         "silently killed that channel") % MARKER},
       "cells": {}, "arms": {}, "not_run": {}}

J = {}
for arm in sorted(SPEC):
    try:
        J[arm] = judge(arm)
        out["arms"][arm] = J[arm]
    except FileNotFoundError as e:
        out["not_run"][arm] = "artifact missing: " + str(e)[:90]
    except Exception as e:                                      # noqa: BLE001
        out["not_run"][arm] = "judge error: " + str(e)[:120]

for cell, (pa, ca, disc) in CELLS.items():
    P, C = J.get(pa), J.get(ca)
    if not P:
        out["not_run"][cell] = "primary arm %s not run" % pa
        continue
    teeth = []
    if C:
        teeth = [{"arm": ca, "run_id": C["run_id"], "discriminating_field": f,
                  "primary_measured": P[f], "control_measured": C[f]} for f in disc if P.get(f) != C.get(f)]
    if not P.get("instrument_ok") or (C and not C.get("instrument_ok")):
        claim = "ARM_INVALID_INSTRUMENT_FAILED"
    elif cell.startswith("B3"):
        claim = ("CLAIMED_MET_ON_BASE_DC964086" if (P["converged_by_executed_bundle"] and P["usable_offline"]
                 and P["offline_document_boots"] and P["stays_on_new_generation_offline"]
                 and P["no_page_origin_contact_offline"] and P["journeys_rows_after"] == 1)
                 else "CLAIMED_RED_OFFLINE_USABILITY_BROKEN")
    else:
        halves = []
        halves.append("HELD_SCREEN_USABLE_OFFLINE" if P["usable_on_held_generation"]
                      else "HELD_SCREEN_NOT_USABLE_OFFLINE")
        halves.append("STAYS_ON_HELD_GEN_AFTER_REENTRY" if P["stayed_on_installed_generation_offline"]
                      else "OFFLINE_REENTRY_LEFT_HELD_GEN")
        claim = ("CLAIMED_MET_NEVER_RECONNECTED_KEEPS_OLD_GEN" if (
                     P["offline_document_boots"] and P["stayed_on_installed_generation_offline"]
                     and P["usable_offline"] and P["journeys_rows_after"] == 1)
                 else "CLAIMED_RED_NEVER_RECONNECTED_BROKEN__" + "+".join(halves))
    out["cells"][cell] = {
        "claim_under_test": SPEC[pa]["claim"],
        "claimed_result": claim,
        "derived_result": None,
        "claim_scope_limit": (None if not cell.startswith("A_") else (
            "browserContext.setOffline(true) does not stop the service worker's own update fetch (measured "
            "in this lane on the previous base: worker update requests are still logged during the outage). "
            "So this arm does not establish what a radio-off device would do; what it establishes is the "
            "pair named in claimed_result -- whether the screen the device holds is usable, and which "
            "generation an offline re-entry serves.")),
        "why": why_for(P, [("control_arm", ca), ("control_run_id", (C or {}).get("run_id")),
                           ("control_differs_on", [t["discriminating_field"] for t in teeth])]),
        "controls": teeth,
        "control_verdict": (None if not C else ("CONTROL_DISCRIMINATES" if teeth
                                                else "CONTROL_INEFFECTIVE_CLAIM_UNSIGNABLE")),
        "triples": [{"sha": x["base_tip"], "nodeid": k, "run_id": x["run_id"], "shape": x["shape"],
                    "instrument_git_blob_sha1": (x.get("instrument") or {}).get("git_blob_sha1", NOT),
                    "executed_offline": x["offline_first_scripts"],
                    "offline_marker": x["offline_first_marker"],
                    "bodyChars": x["offline_first_bodyChars"]}
                   for k, x in ((pa, P), (ca, C)) if x],
        "same_key_precondition": ("same walk, same typed draft, same base tree, same instrument bytes and "
                                 "the same outage window on both arms; the arms differ only in the field "
                                 "their cell is about -- B3: which root serves /assets/ after the swap "
                                 "(%s vs %s); A: whether a handover is attempted inside the outage "
                                 "(attempted on %s: %s)" % (
                                     P["asset_root_written"], (C or {}).get("asset_root_written"), ca,
                                     (C or {}).get("outage_update_attempt"))),
        "isolation": {k: x["isolation"] for k, x in ((pa, P), (ca, C)) if x},
        "durable_read_back": {"journeys_rows": [P["journeys_rows_after"], (C or {}).get("journeys_rows_after")],
                              "tables_measured": [P["tables_measured"], (C or {}).get("tables_measured")],
                              "one_shot_db": [P["db_file"], (C or {}).get("db_file")],
                              "run_ids": {pa: P["run_id"], ca: (C or {}).get("run_id")}},
    }
    if not C:
        out["not_run"][cell + "__control"] = "control arm %s not run" % ca

PARENT = {"B3_control_partial_deploy": ("B3_offline_after_convergence", "b3_primary"),
          "A_control_update_lands": ("A_never_reconnected", "a_never_reconnects")}
for cell, arm in CONTROL_CELLS.items():
    X = J.get(arm)
    if not X:
        continue
    parent_cell, prim = PARENT[cell]
    pc = out["cells"].get(parent_cell) or {}
    teeth_here = [t for t in (pc.get("controls") or []) if t.get("arm") == arm]
    out["cells"][cell] = {
        "claim_under_test": SPEC[arm]["claim"],
        "claimed_result": ("CONTROL_DISCRIMINATES_BY_" + "+".join(t["discriminating_field"] for t in teeth_here)
                           if teeth_here else "CONTROL_INEFFECTIVE_PRIMARY_UNSIGNABLE"),
        "primary_cell": parent_cell,
        "discriminating_fields": [{"field": t["discriminating_field"],
                                   "primary_measured": t["primary_measured"],
                                   "control_measured": t["control_measured"]} for t in teeth_here],
        "derived_result": None,
        "why": why_for(X, [("primary_arm", prim), ("primary_run_id", (J.get(prim) or {}).get("run_id")),
                           ("differs_from_primary_on", [t["discriminating_field"] for t in teeth_here])]),
        "triples": [{"sha": X["base_tip"], "nodeid": cell, "run_id": X["run_id"], "shape": X["shape"],
                     "instrument_git_blob_sha1": (X.get("instrument") or {}).get("git_blob_sha1", NOT),
                     "executed_offline": X["offline_first_scripts"],
                     "offline_marker": X["offline_first_marker"], "bodyChars": X["offline_first_bodyChars"]}],
        "same_key_precondition": pc.get("same_key_precondition"),
        "isolation": {arm: X["isolation"]},
    }

whys = [v.get("why", "") for v in out["cells"].values()]
dups = sorted({w for w in whys if whys.count(w) > 1})
out["selftest_duplicate_why"] = {"cells": len(whys), "distinct_why_strings": len(set(whys)),
                                 "duplicates": dups, "result": "PASS" if not dups else "FAIL"}
out["derived_result_is_null_everywhere"] = all(v.get("derived_result") is None for v in out["cells"].values())
io.open(os.path.join(LANE, OUT), "w", encoding="utf-8").write(json.dumps(out, ensure_ascii=False, indent=2))
print(json.dumps({"cells": {k: [v["claimed_result"], v.get("control_verdict")] for k, v in out["cells"].items()},
                  "not_run": out["not_run"], "selftest": out["selftest_duplicate_why"],
                  "derived_null_everywhere": out["derived_result_is_null_everywhere"],
                  "run_ids": {k: v["run_id"] for k, v in out["arms"].items()}},
                 ensure_ascii=False, indent=1))
