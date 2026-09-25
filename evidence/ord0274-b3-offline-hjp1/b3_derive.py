"""ORD-0274 B3: derive "is the converged generation still usable offline" from measured fields only.

The traveller's version of this cell: the update landed, I have a real trip, then the network goes away
for good -- does the phone still show me my trip, on the generation it just took, or does it hand me a
blank screen or the old app?

Rules this file holds itself to, each one because it was already broken once this session:
  * no verdict is typed.  Every `derived_result` is a predicate over the fields in `field_lines`, and
    each field names the arm and commit it came from;
  * a field my probe did not carry is NOT_MEASURED, never a coercible false;
  * if the instrument itself failed, the arm reads ARM_INVALID rather than dressing up as a product
    finding -- round 2 of this cell produced a page where every snapshot threw `GEN_MARKER is not
    defined`, and a verdict keyed on those readings would have looked like "never converged";
  * the control is judged by whether it DIFFERS from the primary on the fields B3 keys on; a control
    as healthy as the primary makes the judgement worthless, and that is reported as unsignable;
  * sentences are rendered from (label, value) pairs, so a number cannot be retyped wrong.
"""
import io
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
LANE = r"D:\moodle\_qoder_hjp1_o207_20260922"
NOT = "NOT_MEASURED"
# a round already delivered is never rewritten: point B3_SRC at its folder, write a new B3_OUT
SRC = os.environ.get("B3_SRC", LANE)
OUT = os.environ.get("B3_OUT", "o2b3_derived_r1.json")
BUNDLE = re.compile(r"index-[\w-]+\.js")
WORKERISH = re.compile(r"v10-sw\.js|workbox-")
ARMS = {"b3_primary": "B3_offline_after_convergence",
        "b3_control_partial": "B3_control_partial_deploy"}


def kv(pairs):
    names = [n for n, _ in pairs]
    assert len(names) == len(set(names)), "duplicate label in a why-sentence: %s" % names
    return "; ".join("%s=%s" % (n, json.dumps(v, ensure_ascii=False)
                                if isinstance(v, (list, dict, bool)) else v) for n, v in pairs)


def bundles(scripts):
    got = []
    for s in scripts or []:
        m = BUNDLE.search(s)
        if m:
            got.append(m.group(0))
    return sorted(set(got))


def judge(arm):
    run = json.load(io.open(os.path.join(SRC, "o2b3_run_%s.json" % arm), encoding="utf-8"))
    a = json.load(io.open(os.path.join(SRC, "b2_%s.json" % arm), encoding="utf-8"))
    req = [json.loads(l) for l in io.open(os.path.join(SRC, "o2b3_requests_%s.jsonl" % arm),
                                          encoding="utf-8") if l.strip()]
    inst = a.get("instrument") or {}
    p3 = (a.get("phases") or {}).get("P3") or {}
    p4 = (a.get("phases") or {}).get("P4") or {}
    new_b, old_b = run["identity_next"]["bundle"], run["identity_installed"]["bundle"]
    off_at = p4.get("offline_at_epoch") or 0
    in_off = [e for e in req if e.get("t", 0) * 1000 >= off_at]
    off_first = p4.get("first_screen_offline") or {}
    steps = p4.get("in_app_nav_offline") or []
    reload_ = p4.get("reload_offline") or {}
    j = {
        "arm": arm, "kind": run.get("arm_kind"), "cells_this_arm_judges": run.get("cells_this_arm_judges"),
        "installed_commit": run["installed_commit"], "next_commit_label": run["next_commit"],
        "old_bundle": old_b, "new_bundle": new_b,
        "shape": "390x844 touch / zh-CN persistent profile / one-shot sqlite / ports %s"
                 % json.dumps(run.get("ports"), ensure_ascii=False),
        "fatal": a.get("fatal"), "arm_invalid_reason": a.get("arm_invalid_reason"),
        "arm_exit": run.get("arm_exit"), "arm_wall_s": run.get("arm_wall_s"),
        "probe_smoke": inst.get("probe_smoke", NOT),
        "pageErrors": inst.get("pageErrors", [])[:6],
        "instrument_self_errors": sorted({e for e in inst.get("pageErrors", [])
                                          if re.search(r"is not defined|SNAP_SOURCE|GEN_MARKER|Cannot read", e)}),
        "journey_id_in_localStorage": p3.get("journey_id"),
        "retry_presses_made": p3.get("retry_presses_made", NOT),
        "nav_labels_at_creation": p3.get("nav_labels_at_creation"),
        "server_logged_201_for_journeys": any('POST /api/v1/journeys" 2' in l
                                              for l in run.get("backend_write_log", [])),
        "journeys_rows_before": ((run.get("db_before") or {}).get("counts") or {}).get("journeys"),
        "journeys_rows_after": ((run.get("db_after") or {}).get("counts") or {}).get("journeys"),
        "tables_measured": (run.get("db_after") or {}).get("tables_measured"),
        "update_trigger": p3.get("update_trigger"),
        "asset_root_written": (p3.get("assets") or {}).get("asset_root"),
        "pointer_read_back_ok": (p3.get("assets") or {}).get("read_back_ok"),
        "executed_before_transition": bundles((p3.get("before_action") or {}).get("scripts")),
        "executed_after_transition": bundles((p3.get("after_written") or {}).get("scripts")),
        "marker_after_transition": (p3.get("after_written") or {}).get("marker"),
        "instrument_navigations": [e.get("label") or "goto" for e in inst.get("navEvents", []) if e.get("mine")],
        "the_one_navigation": p3.get("the_one_navigation"),
        "offline_first_bodyChars": off_first.get("bodyChars", NOT),
        "offline_first_leafCount": off_first.get("leafCount", NOT),
        "offline_first_marker": off_first.get("marker", NOT),
        "offline_first_scripts": bundles(off_first.get("scripts")),
        "offline_first_rendered": off_first.get("headings"),
        "nav_steps": len(steps),
        "nav_tapped": sum(1 for s in steps if s.get("tapped")),
        "nav_path_changed": sum(1 for s in steps if s.get("path_changed")),
        "nav_labels_tapped": [s.get("label") for s in steps],
        "nav_bodyChars": [s.get("bodyChars", NOT) for s in steps],
        "nav_executed": [bundles(s.get("scripts")) for s in steps],
        "nav_rendered": [[s.get("label")] + list((s.get("headings") or [])[:2]) for s in steps],
        "reload_bodyChars": reload_.get("bodyChars", NOT),
        "reload_bundles": bundles(reload_.get("scripts")),
        "reload_marker": reload_.get("marker", NOT),
        "reload_http_status": reload_.get("http_status", NOT),
        "reload_replaced_document": reload_.get("doc_nonce_before") not in (None, NOT)
                                    and reload_.get("doc_nonce_before") != reload_.get("doc_nonce_after"),
        "reload_rendered": reload_.get("headings"),
        "origin_hits_during_offline": len(in_off),
        "page_level_hits_offline": [{"kind": e.get("kind"), "path": e.get("path"), "status": e.get("status")}
                                    for e in in_off if not WORKERISH.search(e.get("path") or "")],
        "worker_update_hits_offline": sorted({e.get("path") for e in in_off
                                              if WORKERISH.search(e.get("path") or "")}),
        "origin_html_at_js_urls": sorted({e["path"] for e in req if e.get("html_at_js_url")}),
        "isolation": run.get("isolation"),
    }
    j["converged_by_executed_bundle"] = new_b in j["executed_after_transition"]
    j["converged_by_marker"] = j["marker_after_transition"] == "ORD-0290-next"
    j["converged_onto_next"] = j["converged_by_executed_bundle"]
    # every offline document -- first screen, each in-app destination, and the re-entry -- must be the
    # generation that converged; the previous generation appearing anywhere is a fallback
    every = [j["offline_first_scripts"]] + j["nav_executed"] + [j["reload_bundles"]]
    j["stays_on_new_generation_offline"] = bool(all(new_b in e for e in every)
                                                and not any(old_b in e for e in every))
    # does anything at all mount?  a poisoned precache entry (HTML served at a .js URL) leaves a
    # document that lists the right script and runs nothing, so src lists alone cannot carry this
    j["offline_document_boots"] = bool(
        isinstance(j["offline_first_bodyChars"], int) and j["offline_first_bodyChars"] > 0
        and isinstance(j["offline_first_leafCount"], int) and j["offline_first_leafCount"] > 0
        and isinstance(j["reload_bodyChars"], int) and j["reload_bodyChars"] > 0
        and (j["offline_first_rendered"] or j["reload_rendered"]))
    j["usable_offline"] = bool(isinstance(j["offline_first_bodyChars"], int)
                               and j["offline_first_bodyChars"] > 200
                               and j["nav_steps"] >= 2 and j["nav_path_changed"] == j["nav_steps"]
                               and all(isinstance(x, int) and x > 100 for x in j["nav_bodyChars"])
                               and isinstance(j["reload_bodyChars"], int) and j["reload_bodyChars"] > 200)
    j["no_page_origin_contact_offline"] = not j["page_level_hits_offline"]
    j["worker_update_survived_offline_emulation"] = bool(j["worker_update_hits_offline"])
    j["instrument_ok"] = bool(isinstance(j["probe_smoke"], dict) and j["probe_smoke"].get("ok")) \
        and not j["instrument_self_errors"] and j.get("fatal") is None
    j["b3_fields_all_green"] = bool(j["instrument_ok"] and j["converged_onto_next"]
                                    and j["offline_document_boots"] and j["usable_offline"]
                                    and j["stays_on_new_generation_offline"]
                                    and j["no_page_origin_contact_offline"]
                                    and "B2-the-one-navigation" not in j["instrument_navigations"]
                                    and j["journeys_rows_after"] == 1)
    return j


def field_lines(P, C):
    lines = []
    for j in (P, C):
        lines.append(j["arm"] + "@" + j["installed_commit"][:8] + " " + kv([
            ("converged_by_bundle", j["converged_by_executed_bundle"]),
            ("converged_by_marker", j["converged_by_marker"]),
            ("instrument_navigations", j["instrument_navigations"]),
            ("asset_root", j["asset_root_written"]),
            ("offline_first_bodyChars", j["offline_first_bodyChars"]),
            ("offline_first_executed", j["offline_first_scripts"]),
            ("old_bundle_offline", j["old_bundle"] in j["offline_first_scripts"]),
            ("nav_tapped_of_steps", "%d/%d" % (j["nav_tapped"], j["nav_steps"])),
            ("nav_path_changed", j["nav_path_changed"]),
            ("nav_bodyChars", j["nav_bodyChars"]),
            ("reload_bodyChars", j["reload_bodyChars"]),
            ("reload_executed", j["reload_bundles"]),
            ("page_hits_offline", len(j["page_level_hits_offline"])),
            ("worker_update_hits_offline", j["worker_update_hits_offline"]),
            ("origin_html_at_js_urls", j["origin_html_at_js_urls"]),
            ("journeys_rows", "%s/%s" % (j["journeys_rows_before"], j["journeys_rows_after"])),
            ("offline_document_boots", j["offline_document_boots"]),
            ("usable_offline", j["usable_offline"]),
            ("instrument_ok", j["instrument_ok"])]) + "\n")
    return lines


def why_for(j, extra):
    return kv([
        ("arm", j["arm"]), ("installed", j["installed_commit"][:8]),
        ("asset_root_written", j["asset_root_written"]),
        ("pointer_read_back_ok", j["pointer_read_back_ok"]),
        ("instrument_ok", j["instrument_ok"]), ("probe_smoke", j["probe_smoke"]),
        ("instrument_self_errors", j["instrument_self_errors"]),
        ("converged_by_executed_bundle", j["converged_by_executed_bundle"]),
        ("converged_by_marker", j["converged_by_marker"]),
        ("executed_before_transition", j["executed_before_transition"]),
        ("executed_after_transition", j["executed_after_transition"]),
        ("marker_after_transition", j["marker_after_transition"]),
        ("instrument_navigations", j["instrument_navigations"]),
        ("the_one_navigation", j["the_one_navigation"]),
        ("journeys_rows", "%s before / %s after" % (j["journeys_rows_before"], j["journeys_rows_after"])),
        ("tables_measured", j["tables_measured"]),
        ("server_logged_201_for_journeys", j["server_logged_201_for_journeys"]),
        ("journey_id", j["journey_id_in_localStorage"]),
        ("retry_presses", j["retry_presses_made"]),
        ("nav_labels_at_creation", j["nav_labels_at_creation"]),
        ("offline_first_bodyChars", j["offline_first_bodyChars"]),
        ("offline_first_leafCount", j["offline_first_leafCount"]),
        ("offline_first_executed", j["offline_first_scripts"]),
        ("old_bundle_executed_offline", j["old_bundle"] in j["offline_first_scripts"]),
        ("in_app_taps_of_steps", "%d/%d" % (j["nav_tapped"], j["nav_steps"])),
        ("nav_labels_tapped", j["nav_labels_tapped"]),
        ("nav_path_changed", j["nav_path_changed"]),
        ("nav_bodyChars", j["nav_bodyChars"]),
        ("reload_bodyChars", j["reload_bodyChars"]),
        ("reload_http_status", j["reload_http_status"]),
        ("reload_executed", j["reload_bundles"]),
        ("reload_replaced_document", j["reload_replaced_document"]),
        ("origin_hits_during_offline_total", j["origin_hits_during_offline"]),
        ("page_level_hits_offline", len(j["page_level_hits_offline"])),
        ("worker_update_hits_offline", j["worker_update_hits_offline"]),
        ("origin_html_at_js_urls", j["origin_html_at_js_urls"]),
        ("offline_document_boots", j["offline_document_boots"]),
        ("pageErrors", j["pageErrors"]),
        ("arm_invalid_reason", j["arm_invalid_reason"]),
    ] + extra) + " | rendered offline sentences: " + json.dumps(
        {"first_screen": j["offline_first_rendered"], "per_nav_step": j["nav_rendered"],
         "after_reload": j["reload_rendered"]}, ensure_ascii=False)


out = {"order": "ORD-0274", "cell_group": "B3 (offline after convergence) and its discriminating control",
       "verifier": "1a986a24 HJ-P1 (B-1: only the verifier's derived closes)",
       "revision": "b3-" + OUT.replace("o2b3_derived_", "").replace(".json", ""),
       "artifacts_read_from": SRC,
       "candidate_tip_read_by_me_first": "ef277b2da5dfff22ae3f1deaf63b295f5cda678f",
       "instrument": {"arms": "o2b3_arms.cjs",
                      "origin": "o2b3_origin.py (two root pointers: shell root vs asset root)",
                      "runner": "o2b3_run.py", "spec": "o2b3_arms.json",
                      "origin_selftest": "o2b3_origin_selftest.py -- proves the split root can answer a "
                                         ".js URL with 200 + HTML before any browser is started"},
       "cells": {}, "arms": {}, "not_run": {}}

A = {}
for arm, cell in ARMS.items():
    try:
        A[arm] = judge(arm)
        out["arms"][arm] = A[arm]
    except FileNotFoundError as e:
        out["not_run"][cell] = "arm artifact missing under " + SRC + ": " + str(e)[:90]

P, C = A.get("b3_primary"), A.get("b3_control_partial")
if P and C:
    DISCRIM = ("offline_document_boots", "usable_offline", "stays_on_new_generation_offline",
               "no_page_origin_contact_offline", "b3_fields_all_green")
    diff_fields = [f for f in DISCRIM if P[f] != C[f]]
    teeth = [{"arm": C["arm"], "sha": C["installed_commit"], "discriminating_field": f,
              "primary_measured": P[f], "control_measured": C[f]} for f in diff_fields]
    both_ok = bool(P["instrument_ok"] and C["instrument_ok"])
    same_key = ("identical walk, identical typed draft, identical convergence trigger and identical "
                "offline window on both arms; exactly one configured byte differs - the root the origin "
                "serves /assets/ from (primary %s, control %s), each written to a pointer file and read "
                "back before the swap" % (P["asset_root_written"], C["asset_root_written"]))
    out["cells"]["B3_offline_after_convergence"] = {
        "claim_under_test": "a traveller whose client converged onto the new generation, and who really "
                            "has a trip, stays usable offline on that same generation",
        "derived_result": ("ARM_INVALID_INSTRUMENT_FAILED" if not both_ok else
                           ("VERIFIED_FIXED_WITH_DISCRIMINATING_CONTROL"
                            if P["b3_fields_all_green"] and teeth else
                            ("RED_B3_OFFLINE_USABILITY_BROKEN" if not P["b3_fields_all_green"]
                             else "VERIFIED_BUT_CONTROL_NOT_DISCRIMINATING"))),
        "why": why_for(P, [("differs_from_control_on", diff_fields)]),
        "controls": teeth, "field_lines": field_lines(P, C),
        "instrument_state": {"primary_probe_smoke": P["probe_smoke"], "control_probe_smoke": C["probe_smoke"],
                             "primary_self_errors": P["instrument_self_errors"],
                             "control_self_errors": C["instrument_self_errors"]},
        "rendered_offline_text": {
            "primary": {"first_screen": P["offline_first_rendered"], "per_nav_step": P["nav_rendered"],
                        "after_reload": P["reload_rendered"]},
            "control": {"first_screen": C["offline_first_rendered"], "per_nav_step": C["nav_rendered"],
                        "after_reload": C["reload_rendered"]}},
        "criterion_boundaries": "what this cell scores is the document: does it render, on which "
                                "generation, and does moving inside it still work.  The app's own data "
                                "reads are not cached by the worker on this surface, so an offline read "
                                "failing is reported in rendered_offline_text and scored neither as a "
                                "pass nor as a defect here.  Worker update checks survive Playwright's "
                                "offline emulation (measured: %s), so they are counted apart from page "
                                "traffic rather than as proof the app reached the network."
                                % json.dumps(P["worker_update_hits_offline"], ensure_ascii=False),
        "triples": [{"sha": x["installed_commit"], "nodeid": ARMS[k], "shape": x["shape"],
                     "executed_offline": x["offline_first_scripts"], "marker": x["offline_first_marker"],
                     "bodyChars": x["offline_first_bodyChars"]}
                    for k, x in (("b3_primary", P), ("b3_control_partial", C))],
        "same_key_precondition": same_key,
        "isolation": {k: x["isolation"] for k, x in (("b3_primary", P), ("b3_control_partial", C))},
        # type-safe on purpose: a round whose probe never ran carries NOT_MEASURED (a string), and
        # comparing that with > would raise -- which is exactly the coercion this file forbids
        "red_cause_if_any": (None if P["b3_fields_all_green"] else
                             ("hub_never_rendered_a_trip_so_no_nav_to_walk"
                              if (not P["nav_steps"]
                                  and isinstance(P["offline_first_bodyChars"], int)
                                  and 0 < P["offline_first_bodyChars"] <= 200)
                              else ("instrument_failed" if not P["instrument_ok"]
                                    else "see_why_fields"))),
        "durable_read_back": {"tables_measured": [P["tables_measured"], C["tables_measured"]],
                              "journeys_rows": [P["journeys_rows_after"], C["journeys_rows_after"]]},
    }
    out["cells"]["B3_control_partial_deploy"] = {
        "claim_under_test": "the control must be able to break B3: same everything, new shell over old "
                            "assets -- a deploy that does not retain the previous bundles",
        "derived_result": ("ARM_INVALID_INSTRUMENT_FAILED" if not both_ok else
                           ("CONTROL_DISCRIMINATES_BY_" + "+".join(diff_fields) if teeth
                            else "CONTROL_INEFFECTIVE_B3_JUDGEMENT_UNSIGNABLE")),
        "why": why_for(C, [("differs_from_primary_on", diff_fields)]),
        "controls": teeth, "field_lines": field_lines(P, C),
        "triples": [{"sha": C["installed_commit"], "nodeid": "B3_control_partial_deploy",
                     "shape": C["shape"], "executed_offline": C["offline_first_scripts"],
                     "marker": C["offline_first_marker"], "bodyChars": C["offline_first_bodyChars"]}],
        "same_key_precondition": same_key,
        "isolation": {"b3_control_partial": C["isolation"]},
    }

whys = [v.get("why", "") for v in out["cells"].values()]
dups = sorted({w for w in whys if whys.count(w) > 1})
out["selftest_duplicate_why"] = {"cells": len(whys), "distinct_why_strings": len(set(whys)),
                                 "duplicates": dups, "result": "PASS" if not dups else "FAIL"}
if dups:
    for k, v in out["cells"].items():
        if v.get("why") in dups:
            v["derived_result"] = "SELFTEST_DUPLICATE_WHY"
out["not_run"]["A_never_reconnected"] = "a device that never receives the new worker needs its own arm " \
                                        "and its own control; not run in this revision, and written as " \
                                        "not_run rather than inferred from the two arms above"
io.open(os.path.join(LANE, OUT), "w", encoding="utf-8").write(json.dumps(out, ensure_ascii=False, indent=2))
brief = {"verdicts": {k: v["derived_result"] for k, v in out["cells"].items()},
         "diff_fields": diff_fields if P and C else None,
         "selftest": out["selftest_duplicate_why"], "not_run": out["not_run"]}
for tag, x in (("primary", P), ("control", C)):
    if x:
        brief[tag] = {f: x[f] for f in ("instrument_ok", "converged_by_executed_bundle", "converged_by_marker",
                                        "offline_first_bodyChars", "nav_steps", "nav_path_changed",
                                        "nav_bodyChars", "reload_bodyChars", "page_level_hits_offline",
                                        "worker_update_hits_offline", "origin_html_at_js_urls",
                                        "usable_offline", "stays_on_new_generation_offline",
                                        "b3_fields_all_green", "pageErrors")}
print(json.dumps(brief, ensure_ascii=False, indent=1))
