"""ORD-0290: sign derived_result for B2a / B2b / B2c from the six arms (B3 and A are named NOT_RUN
until their fixtures exist).

Rules this file is written to obey, because these are the signatures that close someone else's
order:
  * one arm pair per cell - a cell may not borrow a green from a neighbouring arm, and a single
    red arm is never counted as three pieces of evidence;
  * every verdict is computed from measured lines (runner identity, arm snapshots, origin log,
    DB read-back); the string "MET"/"RED" never appears as a literal verdict in the receipt;
  * both directions must be shown: restored-fix arm behaves as claimed AND not-restored arm does
    not.  If the control arm also passes, the cell's green is not attributable and I say so;
  * each claim carries (exact sha, phase/node id, shape) plus the same-key precondition it was
  judged under, and anything not run stays NOT_RUN rather than being folded into a pass.
"""
import io
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
LANE = r"D:\moodle\_qoder_hjp1_o207_20260922"
PAIRS = {"B2a_idle_automatic_convergence": ("b2a_restored", "b2a_notrestored"),
         "B2b_dirty_form_preservation": ("b2b_restored", "b2b_notrestored"),
         "B2c_inflight_write_safe_point": ("b2c_restored", "b2c_notrestored")}
NAMED_KEYS = ("cityName", "arrivalLocation", "departureLocation", "startAt", "endAt",
              "partySize", "budgetMajor", "stayBudgetMajor", "specialRequirements", "currency", "pace")
TYPED_VALUES = {"北京", "北京南站", "北京西站", "2026-10-05T09:30", "2026-10-07T18:00",
                "480", "150", "只看免费和便宜的地方"}


def bundle(sample):
    for s in (sample.get("scripts") or []):
        m = re.search(r"index-[\w-]+\.js", s)
        if m:
            return m.group(0)
    return None


def named(draftwrap):
    d = (draftwrap or {}).get("draft") or {}
    return {k: d.get(k) for k in NAMED_KEYS}, (draftwrap or {}).get("step")


def read(arm):
    r = json.load(io.open(os.path.join(LANE, "o290_run_%s.json" % arm), encoding="utf-8"))
    a = json.load(io.open(os.path.join(LANE, "b2_%s.json" % arm), encoding="utf-8"))
    reqs = []
    rp = os.path.join(LANE, "o290_requests_%s.jsonl" % arm)
    if os.path.exists(rp):
        for ln in io.open(rp, encoding="utf-8"):
            try:
                reqs.append(json.loads(ln))
            except Exception:                                 # noqa: BLE001
                pass
    return r, a, reqs


def judge(arm, r, a, reqs):
    P3 = a["phases"]["P3"]
    before, after = P3["before_action"], P3["after_written"]
    watch = P3["watch"]
    inst, nxt = r["identity_installed"]["bundle"], r["identity_next"]["bundle"]
    navs = len([x for x in P3["nav_events_mine"] if "the-one-navigation" in x])
    conv = [w for w in watch if bundle(w) == nxt]
    nb, sb = named(before.get("draft"))
    na, sa = named(after.get("draft"))
    typed_before = [k for k in NAMED_KEYS if nb.get(k) is not None and str(nb.get(k)) in TYPED_VALUES]
    mismatch = [k for k in NAMED_KEYS if nb.get(k) != na.get(k)]
    mutant = dict(nb); mutant["budgetMajor"] = str(mutant.get("budgetMajor")) + "-MUTATED"
    # run the REAL comparator on the mutant: if a changed value does not show up in its own output,
    # the per-value equality claim below is vacuous and must not be signed.
    mutant_flags = [k for k in NAMED_KEYS if mutant.get(k) != na.get(k)]
    held = [x for x in reqs if x.get("kind") == "write_held"]
    rel = [x for x in reqs if x.get("kind") == "write_released"]
    conv_epoch = (P3.get("watch_started_at_epoch") + conv[0]["atMs"]) if conv else None
    # units, measured the hard way: hold_ms is MILLISECONDS and t is epoch SECONDS. My first pass
    # multiplied hold_ms by 1000 as well, which pushed the settlement ~8000 s into the future and
    # turned a safe-point-respecting reload into a fabricated red against B's candidate.
    settlement_epoch = (held[0]["t"] * 1000.0 + (held[0].get("hold_ms") or 0)) if held else None
    journeys = ((r.get("db_after") or {}).get("counts") or {}).get("journeys")
    api = a["instrument"].get("apiEvents", [])
    got_reply = any(x["ev"] == "response" and x["p"] == "/api/v1/journeys" for x in api)
    # WHEN did the document actually get replaced? The 4 s polling sample cannot answer that, and using
    # it made both arms look identical.  Each of MY navigations also arrives as an unowned
    # framenavigated event, so "not mine" alone is not enough - the product's own reload is the one
    # that happens inside the watch window, after I stopped navigating.
    watch_start = P3.get("watch_started_at_epoch") or 0
    unowned = sorted(e["at"] for e in a["instrument"]["navEvents"]
                     if not e.get("mine") and e["at"] > watch_start)
    reload_epoch = unowned[0] if unowned else None
    rel_to_settlement = (reload_epoch - settlement_epoch) if (reload_epoch and settlement_epoch) else None
    return {
        "arm": arm, "installed_commit": r["installed_commit"], "next_commit": r["next_commit"],
        "shape": "%s + install=%s + write=%s" % (
            r["arm_kind"], a.get("install_mode"), a.get("write_mode")),
        "identity_installed_bundle": inst, "identity_next_bundle": nxt,
        "separable": inst != nxt,
        "executed_before": bundle(before), "executed_after": bundle(after),
        "converged_onto_next": bool(conv),
        "converged_atMs": conv[0]["atMs"] if conv else None,
        "user_navigations_after_transition": navs,
        "document_replaced": before.get("docNonce") != after.get("docNonce"),
        "draft_step_before_after": [sb, sa], "step_preserved": sb == sa,
        "mismatched_named_keys": mismatch, "typed_values_in_before_draft": typed_before,
        "draft_present_after": bool(after.get("draft")),
        "mutant_selftest_detected": "budgetMajor" in mutant_flags,
        "journeys_rows_after": journeys,
        "server_logged_201_for_journeys": bool([l for l in (r.get("backend_write_log") or [])
                                                if re.search(r'"POST /api/v1/journeys[^"]*" 201', l)]),
        "origin_held_writes": len(held), "origin_released": len(rel),
        "client_received_write_reply": got_reply,
        "convergence_epoch": conv_epoch, "write_settlement_epoch": settlement_epoch,
        "actual_reload_epoch": reload_epoch,
        "reload_ms_relative_to_settlement": rel_to_settlement,
        "reload_cut_the_write": (reload_epoch is not None and settlement_epoch is not None
                                 and reload_epoch < settlement_epoch),
        "converged_after_settlement": (reload_epoch is not None and settlement_epoch is not None
                                       and reload_epoch >= settlement_epoch and bool(conv)),
        "arm_invalid_reason": a.get("arm_invalid_reason"), "fatal": a.get("fatal"),
        "isolation_ok": bool(r["isolation"]["rundir_deleted"] and not r["isolation"]["db_leftovers"]
                             and not any(r["isolation"]["ports_final"].values())),
        "tables_measured": (r.get("db_before") or {}).get("tables_measured"),
        "pageErrors": len(a["instrument"]["pageErrors"]),
    }


def cell_verdict(cell, pos, neg):
    """derived_result computed from the two arms' readings."""
    if not pos["separable"] or pos["fatal"] or neg["fatal"]:
        return "ARM_INVALID", "the two generations were not separable, or an arm crashed"
    if cell.startswith("B2a"):
        good = pos["converged_onto_next"] and pos["user_navigations_after_transition"] == 1
        teeth = not neg["converged_onto_next"]
    elif cell.startswith("B2b"):
        good = (pos["converged_onto_next"] and pos["user_navigations_after_transition"] == 0
                and pos["draft_step_before_after"][0] == 3 and pos["step_preserved"]
                and not pos["mismatched_named_keys"] and pos["draft_present_after"]
                and len(pos["typed_values_in_before_draft"]) >= 4 and pos["mutant_selftest_detected"])
        teeth = not neg["converged_onto_next"]
    else:
        good = (not pos["reload_cut_the_write"] and pos["converged_after_settlement"]
                and pos["user_navigations_after_transition"] == 0 and pos["client_received_write_reply"])
        teeth = bool(neg["reload_cut_the_write"])
    if not good:
        return "FIX_NOT_EFFECTIVE", "the restored arm itself does not behave as claimed (see its lines)"
    if not teeth:
        return "VERIFIED_BUT_CONTROL_NOT_DECISIVE", "the not-restored arm did not fail, so this green is not attributable to the diff"
    return "VERIFIED_FIXED_WITH_TWO_WAY_CONTROL", "restored arm MET and not-restored arm RED on the same instrument"


out = {"order": "ORD-0290", "verifier": "1a986a24 HJ-P1 (B-1: only the verifier's derived closes)",
       "candidate_tip_read_by_me_first": "ef277b2da5dfff22ae3f1deaf63b295f5cda678f",
       "how_read": "GET /repos/Canshu-King/CityNexus/git/ref/heads/review/0274-b2c-c -> 200 that sha; "
                   "commits + compare(45b0a5e2...ef277b2) read the same way",
       "cells": {}, "arms": {}, "not_run": {}}
for cell, (pa, na) in PAIRS.items():
    try:
        pr, pa_, pq = read(pa)
        nr, na_, nq = read(na)
    except FileNotFoundError as e:
        out["not_run"][cell] = "arm artifact missing: " + str(e)[:90]
        continue
    P, N = judge(pa, pr, pa_, pq), judge(na, nr, na_, nq)
    verdict, why = cell_verdict(cell, P, N)
    out["arms"][pa] = P
    out["arms"][na] = N
    out["cells"][cell] = {
        "claim_under_test": pr.get("claim_under_test"),
        "derived_result": verdict, "why": why,
        "triples": [
            {"sha": P["installed_commit"], "nodeid": pa, "shape": P["shape"],
             "converged": P["converged_onto_next"], "user_navs": P["user_navigations_after_transition"],
             "executed": [P["executed_before"], P["executed_after"]]},
            {"sha": N["installed_commit"], "nodeid": na, "shape": N["shape"],
             "converged": N["converged_onto_next"], "user_navs": N["user_navigations_after_transition"],
             "executed": [N["executed_before"], N["executed_after"]]}],
        "same_key_precondition": "same instrument, same origin, same persistent-profile procedure, same "
                                 "'next' tree (" + pr["identity_next"]["bundle"] + "); only the installed "
                                 "commit differs",
        "isolation": {pa: pr["isolation"], na: nr["isolation"]},
        "draft_evidence": {"typed_values_in_before_draft": P["typed_values_in_before_draft"],
                           "mismatched_named_keys": P["mismatched_named_keys"],
                           "step_before_after": P["draft_step_before_after"],
                           "mutant_selftest_detected": P["mutant_selftest_detected"]},
        "write_evidence": {"positive": {k: P[k] for k in ("reload_cut_the_write", "converged_after_settlement",
                                                          "client_received_write_reply", "journeys_rows_after",
                                                          "server_logged_201_for_journeys")},
                           "control": {k: N[k] for k in ("reload_cut_the_write", "converged_after_settlement",
                                                         "client_received_write_reply", "journeys_rows_after",
                                                         "server_logged_201_for_journeys")}},
    }
out["not_run"]["B3_offline_after_convergence"] = "fixture built (5 distinct trees); arm not run yet"
out["not_run"]["A_never_reconnected"] = "needs its own arm + the partial-deploy teeth control; not run yet"
io.open(os.path.join(LANE, "o290_derived.json"), "w", encoding="utf-8").write(
    json.dumps(out, ensure_ascii=False, indent=2))
print(json.dumps({k: v["derived_result"] for k, v in out["cells"].items()}, ensure_ascii=False, indent=1))
print(json.dumps(out["not_run"], ensure_ascii=False))
for cell, v in out["cells"].items():
    print(cell, "->", [t["nodeid"] + ":" + str(t["converged"]) + "/nav" + str(t["user_navs"]) for t in v["triples"]])
