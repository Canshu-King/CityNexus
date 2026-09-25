"""ORD-0297: derive B3 and A on the LANDED generation, and write `claimed_result` only.

Differences from my ORD-0274 deriver, all of them demanded by the order:
  * the trees are the landed ones and every run record carries `ref_tip_read` verbatim -- this receipt
    refuses to be built from candidate-generation readings;
  * `derived_result` is left null on every cell (B-1: closure belongs to someone else's derived
    reading), while `claimed_result` is what my own fields compute -- no string is typed;
  * each cell's `why` is rendered from (label, value) pairs of its own measurements, so no two cells
    can share a sentence and `derived_from` is never needed;
  * a cell whose instrument did not pass its own smoke test reports ARM_INVALID rather than a claim
    about the product, and the paired control is checked for actually differing on the named field.
"""
import io
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
LANE = r"D:\moodle\_qoder_hjp1_o207_20260922"
NOT = "NOT_MEASURED"
OUT = os.environ.get("O297_OUT", "o297_derived_r1.json")
SRC = os.environ.get("O297_SRC", LANE)
BUNDLE = re.compile(r"index-[\w-]+\.js")
WORKERISH = re.compile(r"v10-sw\.js|workbox-")

# cell -> (primary arm, control arm or None, what the control is allowed to differ on)
CELLS = {
    "B3_offline_after_convergence": ("b3_landed_primary", "b3_landed_control",
                                     ("offline_document_boots", "usable_offline",
                                      "stays_on_new_generation_offline", "no_page_origin_contact_offline")),
    "A_never_reconnected": ("a_never_reconnects", "a_control_update_lands",
                            ("offline_document_boots", "usable_offline",
                             "stayed_on_installed_generation_offline", "worker_update_landed",
                             "offline_first_marker")),
}
EXTRA = {"B3_with_backend_6d041dcc": "b3_landed_primary_writebackend"}


def kv(pairs):
    names = [n for n, _ in pairs]
    assert len(names) == len(set(names)), "duplicate label in a why-sentence: %s" % names
    return "; ".join("%s=%s" % (n, json.dumps(v, ensure_ascii=False)
                                if isinstance(v, (list, dict, bool)) else v) for n, v in pairs)


def bundles(scripts):
    out = []
    for s in scripts or []:
        m = BUNDLE.search(s)
        if m:
            out.append(m.group(0))
    return sorted(set(out))


def judge(arm):
    run = json.load(io.open(os.path.join(SRC, "o297_run_%s.json" % arm), encoding="utf-8"))
    a = json.load(io.open(os.path.join(SRC, "b2_%s.json" % arm), encoding="utf-8"))
    req = [json.loads(l) for l in io.open(os.path.join(SRC, "o297_requests_%s.jsonl" % arm),
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
        "installed_sha": run["installed_commit"], "next_sha_label": run["next_commit"],
        "backend_tree": (run.get("backend_tree") or {}).get("dir"),
        "old_bundle": old_b, "new_bundle": new_b,
        "shape": "390x844 touch / zh-CN persistent profile / one-shot sqlite / ports %s"
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
        "asset_root_written": (p3.get("assets") or {}).get("asset_root"),
        "pointer_read_back_ok": (p3.get("assets") or {}).get("read_back_ok"),
        "executed_after_transition": bundles((p3.get("after_written") or {}).get("scripts")),
        "marker_after_transition": (p3.get("after_written") or {}).get("marker"),
        "instrument_navigations": [e.get("label") or "goto" for e in inst.get("navEvents", []) if e.get("mine")],
        "offline_first_bodyChars": off_first.get("bodyChars", NOT),
        "offline_first_leafCount": off_first.get("leafCount", NOT),
        "offline_first_marker": off_first.get("marker", NOT),
        "offline_first_scripts": bundles(off_first.get("scripts")),
        "offline_first_rendered": off_first.get("headings"),
        "nav_steps": len(steps), "nav_tapped": sum(1 for s in steps if s.get("tapped")),
        "nav_path_changed": sum(1 for s in steps if s.get("path_changed")),
        "nav_bodyChars": [s.get("bodyChars", NOT) for s in steps],
        "nav_executed": [bundles(s.get("scripts")) for s in steps],
        "reload_bodyChars": reload_.get("bodyChars", NOT),
        "reload_bundles": bundles(reload_.get("scripts")),
        "reload_marker": reload_.get("marker", NOT),
        "reload_http_status": reload_.get("http_status", NOT),
        "reload_rendered": reload_.get("headings"),
        "origin_hits_during_offline": len(in_off),
        "page_level_hits_offline": [{"kind": e.get("kind"), "path": e.get("path"), "status": e.get("status")}
                                    for e in in_off if not WORKERISH.search(e.get("path") or "")],
        "worker_update_hits_offline": sorted({e.get("path") for e in in_off
                                              if WORKERISH.search(e.get("path") or "")}),
        "origin_html_at_js_urls": sorted({e["path"] for e in req if e.get("html_at_js_url")}),
        "journeys_rows_before": ((run.get("db_before") or {}).get("counts") or {}).get("journeys"),
        "journeys_rows_after": ((run.get("db_after") or {}).get("counts") or {}).get("journeys"),
        "server_logged_201_for_journeys": any('POST /api/v1/journeys" 2' in l
                                             for l in run.get("backend_write_log", [])),
        "tables_measured": (run.get("db_after") or {}).get("tables_measured"),
        "isolation": run.get("isolation"),
    }
    every = [j["offline_first_scripts"]] + j["nav_executed"] + [j["reload_bundles"]]
    j["converged_onto_next"] = new_b in j["executed_after_transition"]
    j["stays_on_new_generation_offline"] = bool(all(new_b in e for e in every) and not any(old_b in e for e in every))
    # A is the mirror image: the never-reconnecting client must STILL be on the generation it has
    j["stayed_on_installed_generation_offline"] = bool(
        all(old_b in e for e in every) and not any(new_b in e for e in every))
    j["offline_document_boots"] = bool(isinstance(j["offline_first_bodyChars"], int)
                                       and j["offline_first_bodyChars"] > 0
                                       and isinstance(j["offline_first_leafCount"], int)
                                       and j["offline_first_leafCount"] > 0
                                       and isinstance(j["reload_bodyChars"], int)
                                       and j["reload_bodyChars"] > 0
                                       and (j["offline_first_rendered"] or j["reload_rendered"]))
    # the strict bar, kept on the record so a reader can see which bar the claim actually used
    j["usable_offline_strict"] = bool(isinstance(j["offline_first_bodyChars"], int)
                                      and j["offline_first_bodyChars"] > 200
                                      and j["nav_steps"] >= 2 and j["nav_path_changed"] == j["nav_steps"]
                                      and all(isinstance(x, int) and x > 100 for x in j["nav_bodyChars"])
                                      and isinstance(j["reload_bodyChars"], int)
                                      and j["reload_bodyChars"] > 200)
    leaves_off = [x for x in (j["offline_first_rendered"] or []) if x]
    leaves_re = [x for x in (j["reload_rendered"] or []) if x]
    # read off what the traveller can see: the app's own offline notice, with its own affordances
    j["offline_reload_is_app_notice"] = bool(
        isinstance(j["reload_bodyChars"], int) and j["reload_bodyChars"] > 0
        and any("网络不可用" in x for x in leaves_re)
        and any(("归因详情" in x or "重试" in x) for x in leaves_re))
    j["offline_app_names_saved_copy"] = bool(any("已保存的只读副本" in x for x in leaves_re)
                                             or any("没有丢失" in x for x in leaves_re))
    j["offline_first_is_app_copy"] = bool(len(leaves_off) >= 3
                                          and isinstance(j["offline_first_bodyChars"], int)
                                          and j["offline_first_bodyChars"] > 0)
    j["usable_offline"] = bool(j["offline_document_boots"] and j["nav_steps"] >= 2
                               and j["nav_path_changed"] == j["nav_steps"]
                               and j["offline_first_is_app_copy"] and j["offline_reload_is_app_notice"])
    j["no_page_origin_contact_offline"] = not j["page_level_hits_offline"]
    j["outage_update_attempt"] = p4.get("update_inside_outage", NOT)
    j["worker_update_landed"] = bool(j["worker_update_hits_offline"])
    j["instrument_ok"] = bool(isinstance(j["probe_smoke"], dict) and j["probe_smoke"].get("ok")) \
        and not j["instrument_self_errors"] and j.get("fatal") is None
    return j


def why_for(j, extra):
    return kv([
        ("arm", j["arm"]), ("kind", j["kind"]), ("installed_sha", j["installed_sha"][:8]),
        ("frontend_under_test", "landed 5c4608ce"), ("backend_tree", j["backend_tree"]),
        ("instrument_ok", j["instrument_ok"]), ("probe_smoke", j["probe_smoke"]),
        ("instrument_self_errors", j["instrument_self_errors"]),
        ("generation_pairs", "%s (installed) vs %s (next)" % (j["old_bundle"], j["new_bundle"])),
        ("executed_after_transition", j["executed_after_transition"]),
        ("marker_after_transition", j["marker_after_transition"]),
        ("update_trigger", j["update_trigger"]),
        ("asset_root_written", j["asset_root_written"]), ("pointer_read_back_ok", j["pointer_read_back_ok"]),
        ("instrument_navigations", j["instrument_navigations"]),
        ("journeys_rows", "%s before / %s after" % (j["journeys_rows_before"], j["journeys_rows_after"])),
        ("tables_measured", j["tables_measured"]),
        ("server_logged_201_for_journeys", j["server_logged_201_for_journeys"]),
        ("journey_id", j["journey_id"]), ("retry_presses", j["retry_presses_made"]),
        ("nav_labels_at_creation", j["nav_labels_at_creation"]),
        ("offline_first_bodyChars", j["offline_first_bodyChars"]),
        ("offline_first_leafCount", j["offline_first_leafCount"]),
        ("offline_first_marker", j["offline_first_marker"]),
        ("offline_first_executed", j["offline_first_scripts"]),
        ("in_app_taps_of_steps", "%d/%d" % (j["nav_tapped"], j["nav_steps"])),
        ("nav_path_changed", j["nav_path_changed"]), ("nav_bodyChars", j["nav_bodyChars"]),
        ("reload_bodyChars", j["reload_bodyChars"]), ("reload_http_status", j["reload_http_status"]),
        ("reload_executed", j["reload_bundles"]),
        ("origin_hits_during_offline_total", j["origin_hits_during_offline"]),
        ("page_level_hits_offline", len(j["page_level_hits_offline"])),
        ("worker_update_hits_offline", j["worker_update_hits_offline"]),
        ("origin_html_at_js_urls", j["origin_html_at_js_urls"]),
        ("nav_executed_per_screen", j["nav_executed"]),
        ("offline_document_boots", j["offline_document_boots"]),
        ("usable_offline", j["usable_offline"]),
        ("usable_offline_strict_200_chars", j["usable_offline_strict"]),
        ("offline_reload_is_app_notice", j["offline_reload_is_app_notice"]),
        ("offline_app_names_saved_copy", j["offline_app_names_saved_copy"]),
        ("outage_update_attempt", j["outage_update_attempt"]),
        ("converged_onto_next", j["converged_onto_next"]),
        ("stays_on_new_generation_offline", j["stays_on_new_generation_offline"]),
        ("stayed_on_installed_generation_offline", j["stayed_on_installed_generation_offline"]),
        ("pageErrors", j["pageErrors"]), ("arm_invalid_reason", j["arm_invalid_reason"]),
    ] + extra) + " | rendered offline sentences: " + json.dumps(
        {"first_screen": j["offline_first_rendered"], "after_reload": j["reload_rendered"]},
        ensure_ascii=False)


out = {"order": "ORD-0297", "revision": OUT.replace(".json", ""),
       "verifier": "1a986a24 HJ-P1",
       "what_is_claimed_and_what_is_not": "claimed_result is mine and computed from the fields printed "
                                           "beside it; derived_result is null on every cell because "
                                           "closure belongs to a verifier reading other than the "
                                           "deliverer's (B-1)",
       "ref_tip_read": None, "trees": None, "cells": {}, "arms": {}, "not_run": {},
       "criterion_boundaries": "the app's own data reads are not cached by the worker on this surface, "
                               "so an offline data fetch failing is reported verbatim in the rendered "
                               "sentences and scored neither as a pass nor as a defect; this receipt "
                               "scores documents (does anything mount, on which generation, can the "
                               "traveller move).  SW update fetches survive Playwright's offline "
                               "emulation, so worker traffic is counted apart from page traffic."}

for arm in [c[0] for c in CELLS.values()] + [c[1] for c in CELLS.values()] + list(EXTRA.values()):
    try:
        out["arms"][arm] = judge(arm)
    except FileNotFoundError:
        out["arms"][arm] = None
    except Exception as e:                                    # noqa: BLE001
        out["arms"][arm] = {"judge_error": str(e)[:160]}

try:
    tip = json.load(io.open(os.path.join(SRC, "o297_ref_tip_read.json"), encoding="utf-8"))
    out["ref_tip_read"] = tip
except FileNotFoundError:
    out["ref_tip_read"] = NOT_MEASURED
try:
    b = json.load(io.open(os.path.join(SRC, "o297_builds.json"), encoding="utf-8"))
    out["trees"] = {"ordered_tip": b["ordered_tip"],
                    "generations": {k: {kk: v.get(kk) for kk in ("commit", "bundle", "shell_md5",
                                                                 "worker_sha256_16", "marker_line_added")}
                                    for k, v in (b.get("trees") or {}).items()},
                    "pairwise_distinct": b.get("pairwise_distinct"),
                    "shell_md5_distinct": b.get("shell_md5_distinct"),
                    "backend_trees": {k: v["commit"] for k, v in (b.get("backend_trees") or {}).items()}}
except FileNotFoundError:
    out["trees"] = NOT_MEASURED

for cell, (pa, ca, disc) in CELLS.items():
    P, C = out["arms"].get(pa), out["arms"].get(ca)
    if not P:
        out["not_run"][cell] = "primary arm %s has no artifacts yet" % pa
        continue
    if not P.get("instrument_ok"):
        claim = "ARM_INVALID_INSTRUMENT_FAILED"
    elif cell.startswith("B3"):
        claim = ("CLAIMED_MET_ON_LANDED_GEN" if (P["converged_onto_next"] and P["usable_offline"]
                 and P["offline_document_boots"]
                 and P["stays_on_new_generation_offline"] and P["no_page_origin_contact_offline"]
                 and P["journeys_rows_after"] == 1)
                 else "CLAIMED_RED_OFFLINE_USABILITY_BROKEN")
    else:
        claim = ("CLAIMED_MET_NEVER_RECONNECTED_KEeps_OLD_GEN" if (P["offline_document_boots"]
                 and P["stayed_on_installed_generation_offline"] and P["no_page_origin_contact_offline"])
                 else "CLAIMED_RED_NEVER_RECONNECTED_BROKEN")
    teeth = []
    if C:
        teeth = [{"arm": ca, "discriminating_field": f, "primary_measured": P[f], "control_measured": C[f]}
                 for f in disc if P.get(f) != C.get(f)]
    out["cells"][cell] = {
        "claim_under_test": (out["arms"].get(pa) or {}).get("cells_this_arm_judges"),
        "claimed_result": claim,
        "derived_result": None,
        "why": why_for(P, [("control_arm", ca), ("control_differs_on", [t["discriminating_field"] for t in teeth])]),
        "controls": teeth,
        "control_verdict": (None if not C else ("CONTROL_DISCRIMINATES" if teeth
                                                else "CONTROL_INEFFECTIVE_CLAIM_UNSIGNABLE")),
        "instrument_state": {"primary_probe_smoke": P["probe_smoke"],
                             "primary_self_errors": P["instrument_self_errors"],
                             "control_probe_smoke": (C or {}).get("probe_smoke"),
                             "control_self_errors": (C or {}).get("instrument_self_errors")},
        "triples": [{"sha": x["installed_sha"], "nodeid": k, "shape": x["shape"],
                     "executed_offline": x["offline_first_scripts"], "bodyChars": x["offline_first_bodyChars"]}
                    for k, x in ((pa, P), (ca, C)) if x],
        "same_key_precondition": "same walk, same typed draft, same trees and same offline window; the "
                                 "arms differ only in the field their cell is about (B3: which root "
                                 "serves /assets/ after the swap -- %s vs %s; A: whether the worker is "
                                 "allowed to land its update while offline)" % (
                                     P["asset_root_written"], (C or {}).get("asset_root_written")),
        "isolation": {k: x["isolation"] for k, x in ((pa, P), (ca, C)) if x},
        "durable_read_back": {"journeys_rows": [P["journeys_rows_after"], (C or {}).get("journeys_rows_after")],
                              "tables_measured": [P["tables_measured"], (C or {}).get("tables_measured")]},
    }
    if not C:
        out["not_run"][cell + "__control"] = "control arm %s has no artifacts yet" % ca

for cell, arm in EXTRA.items():
    X = out["arms"].get(arm)
    if not X:
        out["not_run"][cell] = "arm %s has no artifacts yet" % arm
        continue
    out["cells"][cell] = {
        "claim_under_test": "does the trip screen still answer HTTP 500 when the backend half is the "
                            "next landed jump 6d041dcc (write deadline) instead of 5c4608ce, with the "
                            "frontend bytes identical",
        "claimed_result": ("CLAIMED_HUB_500_CLEARED" if X["nav_steps"] and X["offline_first_bodyChars"] > 200
                           else "CLAIMED_HUB_500_STILL_BLOCKS_THE_NAV"),
        "derived_result": None,
        "why": why_for(X, [("compared_against_arm", "b3_landed_primary"),
                           ("primary_offline_first_bodyChars",
                            (out["arms"].get("b3_landed_primary") or {}).get("offline_first_bodyChars"))]),
        "controls": [], "instrument_state": {"probe_smoke": X["probe_smoke"],
                                             "self_errors": X["instrument_self_errors"]},
        "triples": [{"sha": X["installed_sha"], "nodeid": arm, "shape": X["shape"],
                     "executed_offline": X["offline_first_scripts"], "bodyChars": X["offline_first_bodyChars"]}],
        "isolation": {arm: X["isolation"]},
    }

whys = [v.get("why", "") for v in out["cells"].values()]
dups = sorted({w for w in whys if whys.count(w) > 1})
out["selftest_duplicate_why"] = {"cells": len(whys), "distinct_why_strings": len(set(whys)),
                                 "duplicates": dups, "result": "PASS" if not dups else "FAIL"}
out["derived_result_is_null_everywhere"] = all(v.get("derived_result") is None for v in out["cells"].values())
io.open(os.path.join(LANE, OUT), "w", encoding="utf-8").write(json.dumps(out, ensure_ascii=False, indent=2))
print(json.dumps({"cells": {k: (v["claimed_result"], v.get("control_verdict")) for k, v in out["cells"].items()},
                  "not_run": out["not_run"], "selftest": out["selftest_duplicate_why"],
                  "derived_null_everywhere": out["derived_result_is_null_everywhere"],
                  "ref_tip_read_present": out["ref_tip_read"] != NOT},
                 ensure_ascii=False, indent=1))
