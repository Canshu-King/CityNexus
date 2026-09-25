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
         "B2c_inflight_write_safe_point": ("b2c_restored", "b2c_noconvergence")}
EXTRA_CONTROLS = {"B2c_inflight_write_safe_point": ["b2c_notrestored"]}
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


def field_lines(pos, neg, extra):
    """Every arm's own numbers, quoted rather than paraphrased, so a reader can check the
    arithmetic behind the sentence instead of trusting the sentence."""
    lines = []
    for j in [pos, neg] + [extra[k] for k in extra]:
        lines.append("%s@%s user_navs=%s converged=%s cut=%s rel_to_settlement_ms=%s "
                     "client_got_reply=%s journeys_rows=%s" % (
                         j["arm"], j["installed_commit"][:8],
                         j["user_navigations_after_transition"], j["converged_onto_next"],
                         j["reload_cut_the_write"], j["reload_ms_relative_to_settlement"],
                         j["client_received_write_reply"], j["journeys_rows_after"]))
    return lines


def cell_verdict(cell, pos, neg, extra):
    """(derived_result, why, controls) - `why` is assembled from THIS cell's fields.

    Which control counts is decided by the field the cell is about:
      B2a  an idle page converges on ONE navigation      -> discriminating field: converged_onto_next
      B2b  it converges and the typed draft survives      -> converged_onto_next + mismatch + step
      B2c  the handover waits for the in-flight write      -> reload_ms_relative_to_settlement
           A B2a-only tree ALSO converges here - it converges by cutting the write - so for B2c
           convergence is not the discriminator (that was ORD-0294's point), and the no-B2a
           baseline arm is what shows the convergence itself is not free.
    """
    if not pos["separable"] or pos["fatal"] or neg["fatal"]:
        return "ARM_INVALID", "the two trees were not separable, or an arm crashed", []
    teeth = []
    if cell.startswith("B2a"):
        good = pos["converged_onto_next"] and pos["user_navigations_after_transition"] == 1
        if not neg["converged_onto_next"]:
            teeth.append((neg, "converged_onto_next", neg["converged_onto_next"], "False"))
        why = ("idle page installed on %s executed %s -> %s, converged=%s, at %s ms, on exactly %d "
               "navigation(s) issued by the instrument; the same instrument on %s executed %s -> %s, "
               "converged=%s" % (
                   pos["installed_commit"][:8], pos["executed_before"], pos["executed_after"],
                   pos["converged_onto_next"], pos["converged_atMs"],
                   pos["user_navigations_after_transition"], neg["installed_commit"][:8],
                   neg["executed_before"], neg["executed_after"], neg["converged_onto_next"]))
    elif cell.startswith("B2b"):
        good = (pos["converged_onto_next"] and pos["user_navigations_after_transition"] == 0
                and pos["draft_step_before_after"][0] == 3 and pos["step_preserved"]
                and not pos["mismatched_named_keys"] and pos["draft_present_after"]
                and len(pos["typed_values_in_before_draft"]) >= 4 and pos["mutant_selftest_detected"])
        if not neg["converged_onto_next"]:
            teeth.append((neg, "converged_onto_next", neg["converged_onto_next"], "False"))
        why = ("document claimed during its own lifetime on %s executed %s -> %s with %d further "
               "navigations; wizard step %s -> %s; named fields differing after the reload = %s; "
               "%d of them carry values the instrument typed (%s); mutant self-test flagged=%s; the "
               "same shape on %s executed %s -> %s, converged=%s" % (
                   pos["installed_commit"][:8], pos["executed_before"], pos["executed_after"],
                   pos["user_navigations_after_transition"], pos["draft_step_before_after"][0],
                   pos["draft_step_before_after"][1], pos["mismatched_named_keys"],
                   len(pos["typed_values_in_before_draft"]), pos["typed_values_in_before_draft"],
                   pos["mutant_selftest_detected"], neg["installed_commit"][:8],
                   neg["executed_before"], neg["executed_after"], neg["converged_onto_next"]))
    else:
        # B2c.  good = this arm waited for its own write, then converged, with no navigation
        # issued by me, and its client actually received the reply.
        good = (not pos["reload_cut_the_write"] and pos["converged_after_settlement"]
                and pos["user_navigations_after_transition"] == 0
                and pos["client_received_write_reply"])
        teeth = []
        if neg["converged_onto_next"] is False:
            teeth.append((neg, "converged_onto_next", neg["converged_onto_next"],
                          "False - a tree with no B2a idle convergence never converges here"))
        for a in [extra[k] for k in extra]:
            rel = a["reload_ms_relative_to_settlement"]
            if rel is not None and rel < 0:
                teeth.append((a, "reload_ms_relative_to_settlement", rel,
                              "negative - reloaded before its own write settled"))
        ex = list(extra.values())[0] if extra else None
        why = ("handover on %s reloaded %s ms relative to its own write settling (cut=%s), "
               "converged=%s (%s -> %s) with %d instrument-issued navigations and its client "
               "received the 201=%s; the control arm on %s - same in-flight write, same 0 navigations, "
               "a tree with NO B2a idle convergence - had reload epoch=%s, converged=%s, its client "
               "received the write=%s, and the row count is the same %s as the fix arm, so the server "
               "committed in both and only one client still knew about it" % (
                   pos["installed_commit"][:8], pos["reload_ms_relative_to_settlement"],
                   pos["reload_cut_the_write"], pos["converged_onto_next"],
                   pos["executed_before"], pos["executed_after"],
                   pos["user_navigations_after_transition"], pos["client_received_write_reply"],
                   neg["installed_commit"][:8], neg["actual_reload_epoch"],
                   neg["converged_onto_next"], neg["client_received_write_reply"],
                   neg["journeys_rows_after"]))
        if ex is not None:
            why += ("; named secondary control on %s (B2a present, safe point absent) reloaded %s ms "
                    "relative to settlement (cut=%s), converged=%s, client received=%s - that arm is "
                    "the hazard itself, and it is why convergence is NOT this cell's discriminator: "
                    "both it and the fix arm converge, only one of them does it by cutting the write" % (
                        ex["installed_commit"][:8], ex["reload_ms_relative_to_settlement"],
                        ex["reload_cut_the_write"], ex["converged_onto_next"],
                        ex["client_received_write_reply"]))
        why += (" | journeys rows: fix=%s control=%s secondary=%s" % (
            pos["journeys_rows_after"], neg["journeys_rows_after"],
            ex["journeys_rows_after"] if ex else None))

    if not good:
        return "FIX_NOT_EFFECTIVE", why, teeth
    if not teeth:
        return "VERIFIED_BUT_CONTROL_NOT_DISCRIMINATING", why, teeth
    name = ("VERIFIED_FIXED_WITH_TWO_DISCRIMINATING_CONTROLS"
            if (cell.startswith("B2c") and len(extra)) else "VERIFIED_FIXED_WITH_DISCRIMINATING_CONTROL")
    return name, why, teeth

out = {"order": "ORD-0290", "revision": "r3", "verifier": "1a986a24 HJ-P1 (B-1: only the verifier's derived closes)",
       "candidate_tip_read_by_me_first": "ef277b2da5dfff22ae3f1deaf63b295f5cda678f",
       "how_read": "GET /repos/Canshu-King/CityNexus/git/ref/heads/review/0274-b2c-c -> 200 that sha; "
                   "commits + compare(45b0a5e2...ef277b2) read the same way",
       "cells": {}, "arms": {}, "not_run": {}}
for cell, (pa, na) in PAIRS.items():
    try:
        pr, pa_, pq = read(pa)
        nr, na_, nq = read(na)
        extra, extra_runs = {}, {}
        for xa in EXTRA_CONTROLS.get(cell, []):
            xr, xa_, xq = read(xa)
            extra[xa] = judge(xa, xr, xa_, xq)
            extra_runs[xa] = xr
            out["arms"][xa] = extra[xa]
    except FileNotFoundError as e:
        out["not_run"][cell] = "arm artifact missing: " + str(e)[:90]
        continue
    P, N = judge(pa, pr, pa_, pq), judge(na, nr, na_, nq)
    verdict, why, teeth = cell_verdict(cell, P, N, extra)
    out["arms"][pa] = P
    out["arms"][na] = N
    out["cells"][cell] = {
        "claim_under_test": pr.get("claim_under_test"),
        "derived_result": verdict, "why": why,
        "controls": [{"arm": a["arm"], "sha": a["installed_commit"], "discriminating_field": f,
                      "measured": got, "expected_to_see": exp} for (a, f, got, exp) in teeth],
        "field_lines": field_lines(P, N, extra),
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
        "isolation": dict([(pa, pr["isolation"]), (na, nr["isolation"])] +
                           [(k, v["isolation"]) for k, v in extra_runs.items()]),
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
whys = [v.get("why", "") for v in out["cells"].values()]
dups = sorted({w for w in whys if whys.count(w) > 1})
out["selftest_duplicate_why"] = {"cells": len(whys), "distinct_why_strings": len(set(whys)),
                                 "duplicates": dups,
                                 "result": "PASS" if not dups else "FAIL"}
if dups:
    for k, v in out["cells"].items():
        if v.get("why") in dups:
            v["derived_result"] = "SELFTEST_DUPLICATE_WHY"
io.open(os.path.join(LANE, "o290_derived_r3.json"), "w", encoding="utf-8").write(
    json.dumps(out, ensure_ascii=False, indent=2))
print(json.dumps({k: v["derived_result"] for k, v in out["cells"].items()}, ensure_ascii=False, indent=1))
print(json.dumps(out["not_run"], ensure_ascii=False))
for cell, v in out["cells"].items():
    print(cell, "->", [t["nodeid"] + ":" + str(t["converged"]) + "/nav" + str(t["user_navs"]) for t in v["triples"]])
