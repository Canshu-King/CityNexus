"""Derive ORD-0274 B1/B2/B3 verdicts from the campaign artifact - every judgement computed.

Rules I hold myself to here:
  * no verdict string is typed - each is a predicate over measured fields, and the field it
    keys on is printed beside it so a reader can disagree with the arithmetic, not my prose;
  * a field my probe did not carry is reported as NOT_MEASURED, never as a coercible false
    (my first pass did exactly that, and it manufactured a B3 red out of a label bug);
  * only the *shell* revision identifies a generation: sw.js / favicon / manifest carry the
    same revision in both builds, so folding the whole revision set into the label reads as
    "mixed" when it is not.  The shared ones are reported separately, not silently dropped.
"""
import hashlib
import io
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
LANE = r"D:\moodle\_qoder_hjp1_o207_20260922"
RUN = sys.argv[1] if len(sys.argv) > 1 else "camp2"
GEN_A = os.path.join(LANE, "o269_run", "dist_gen")
GEN_B = os.path.join(LANE, "o269_run", "dist_gen_c79e2b4")
UPDATE_NOTICE = re.compile("更新|新版本|刷新|重新加载|升级|重启")
SHELL_REV = re.compile("/index[.]html[?]__WB_REVISION__=([0-9a-f]{32})")

camp = json.load(io.open(os.path.join(LANE, "o274_campaign_%s.json" % RUN), encoding="utf-8"))
runner = json.load(io.open(os.path.join(LANE, "o274_run_%s.json" % RUN), encoding="utf-8"))


def md5(path):
    return hashlib.md5(open(path, "rb").read()).hexdigest()


def sha256(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


def entry_bundle(d):
    html = io.open(os.path.join(d, "index.html"), encoding="utf-8").read()
    return re.search(r"assets/(index-[\w-]+[.]js)", html).group(1)


NEW_BUNDLE, OLD_BUNDLE = entry_bundle(GEN_B), entry_bundle(GEN_A)
NEW_SHELL = md5(os.path.join(GEN_B, "index.html"))
OLD_SHELL = md5(os.path.join(GEN_A, "index.html"))
NEW_WORKER = sha256(os.path.join(GEN_B, "v10-sw.js"))
assert NEW_SHELL != OLD_SHELL and NEW_BUNDLE != OLD_BUNDLE, "the two generations are not separable"


def revisions_of(sample):
    return ((sample or {}).get("caches") or {}).get("revisions") or []


def precache_urls_of(sample):
    return ((sample or {}).get("caches") or {}).get("precacheUrls") or []


def shell_gen_of(sample):
    revs = set(r for r in revisions_of(sample) if r)
    if not revs:
        for u in precache_urls_of(sample):
            m = SHELL_REV.search(u)
            if m:
                revs = set([m.group(1)])
                break
    has_new, has_old = (NEW_SHELL in revs), (OLD_SHELL in revs)
    if has_new and has_old:
        label = "MIXED_old_plus_new"
    elif has_new:
        label = "new"
    elif has_old:
        label = "old"
    else:
        label = "NOT_MEASURED"
    return {"label": label,
            "shared_revisions_that_do_not_identify_a_generation":
                sorted(r for r in revs if r not in (NEW_SHELL, OLD_SHELL))}


def executed(sample):
    return [s for s in ((sample or {}).get("scripts") or []) if re.search(r"index-[\w-]+[.]js", s)]


def lifecycle_names(samples):
    seen = set()
    for s in samples:
        for e in (s.get("lifecycle") or []):
            seen.add(e.get("ev"))
    return sorted(seen)


def regs(sample):
    return (sample or {}).get("registrations") or []


b1, b2, b3 = camp["phases"]["B1"], camp["phases"]["B2"], camp["phases"]["B3"]
p0, p1 = camp["phases"]["P0_setup"], camp["phases"]["P1_transition"]
B1S, B2S = b1["samples"], b2["samples_after_60s"]
B1_last = B1S[-1]
B2_last = B2S[-1] if B2S else B1_last
B3_last = b3["samples"][-1]

all_samples = B1S + B2S + b3["samples"]
notice_hits = [s.get("atMs") for s in all_samples for h in (s.get("headings") or []) if UPDATE_NOTICE.search(h)]
new_worker_active_b1 = any((not r.get("waiting")) and (not r.get("installing")) and r.get("active")
                           for r in regs(B1_last))
nonces_b2 = sorted({s.get("docNonce") for s in B2S})

cells = {}
cells["B1_reconnect_first_navigation"] = {
    "navigations_issued_in_this_cell": len(b1["navigations_issued_in_this_cell"]),
    "executed_bundle_first_sample": executed(B1S[0]),
    "executed_bundle_final_sample": executed(B1S[-1]),
    "worker_lifecycle_events_recorded": lifecycle_names(B1S),
    "registrations_final": regs(B1_last),
    "new_worker_already_active_while_page_still_old": new_worker_active_b1,
    "precache_shell_generation_at_final_sample": shell_gen_of(B1_last),
    "page_usable_and_not_chrome_error": bool(not B1_last.get("chromeError") and (B1_last.get("bodyChars") or 0) > 0),
    "update_or_reload_notice_rendered": bool(notice_hits)}
c1 = cells["B1_reconnect_first_navigation"]
c1["verdict"] = "MET" if (c1["navigations_issued_in_this_cell"] == 1 and c1["worker_lifecycle_events_recorded"]
                          and c1["page_usable_and_not_chrome_error"]) else "INCOMPLETE"

cells["B2_automatic_convergence"] = {
    "watch_window_samples": len(B2S),
    "watch_window_ms": B2S[-1].get("atMs") if B2S else None,
    "executed_bundles_seen_without_any_help": sorted({b for s in B2S for b in executed(s)}),
    "new_bundle_executed_without_any_second_action": any(NEW_BUNDLE in b for s in B2S for b in executed(s)),
    "docNonce_distinct_values_in_watch_window": nonces_b2,
    "auto_reload_or_equivalent_detected": len(nonces_b2) > 1,
    "precache_shell_generation_before_extra_action_from_B1_final": shell_gen_of(B1_last),
    "b2_probes_carried_no_cache_listing": True,
    "manual_navigations_needed_to_reach_new_bundle":
        1 + (1 if b2["recovery_costly"]["needed_a_second_manual_navigation"] else 0),
    "user_actions_the_contract_allows": 1,
    "executed_bundle_after_the_extra_manual_navigation": executed(b2.get("after_extra_navigation") or {})}
c2 = cells["B2_automatic_convergence"]
if c2["new_bundle_executed_without_any_second_action"]:
    c2["verdict"] = "MET"
else:
    c2["verdict"] = ("RED_A_SECOND_MANUAL_NAVIGATION_WAS_REQUIRED"
                     if c2["manual_navigations_needed_to_reach_new_bundle"] > 1
                     else "RED_NEW_GENERATION_NEVER_EXECUTED")

cells["B3_offline_after_convergence"] = {
    "chrome_error": B3_last.get("chromeError"),
    "href": B3_last.get("href"),
    "rendered_leaf_chars": B3_last.get("bodyChars"),
    "executed_scripts": B3_last.get("scripts"),
    "executed_css": B3_last.get("css"),
    "old_bundle_present_in_executed_document": any(OLD_BUNDLE in s for s in (B3_last.get("scripts") or [])),
    "fell_back_to_previous_generation": any(OLD_BUNDLE in b for b in executed(B3_last)),
    "precache_entry_count": len(precache_urls_of(B3_last)),
    "precache_shell_generation": shell_gen_of(B3_last),
    "registrations": regs(B3_last),
    "in_app_navigation_while_offline": ("NOT_MEASURED: this one-shot DB holds 0 journeys, so the offline "
                                        "page renders the create-a-trip wizard and there is no bottom nav to tap"
                                        if "in_app_navigation" not in b3 else b3["in_app_navigation"].get("navigated"))}
c3 = cells["B3_offline_after_convergence"]
c3["verdict"] = "MET" if (not c3["chrome_error"] and (c3["rendered_leaf_chars"] or 0) > 0
                          and c3["precache_shell_generation"]["label"] == "new"
                          and not c3["old_bundle_present_in_executed_document"]) else "RED_OR_INCOMPLETE"

pre = p0.get("precondition") or {}
result = {
    "run": RUN, "campaign_exit": runner.get("campaign"), "surface": runner.get("surface"),
    "identities": {"old_bundle": OLD_BUNDLE, "new_bundle": NEW_BUNDLE,
                   "old_shell_md5": OLD_SHELL, "new_shell_md5": NEW_SHELL,
                   "new_worker_sha256_full": NEW_WORKER,
                   "worker_seen_on_disk_after_the_swap": (p1.get("worker_on_disk_now") or {}).get("sha256"),
                   "worker_matches_new_generation_on_disk":
                       (p1.get("worker_on_disk_now") or {}).get("sha256") == NEW_WORKER},
    "precondition_returning_client_on_old_gen": {
        "executed_scripts": pre.get("scripts"), "controller": pre.get("controller"),
        "precache_shell_generation": shell_gen_of(pre),
        "navigations_used_to_establish_this": p0.get("precondition_navigations_issued"),
        "matches_old_generation": shell_gen_of(pre)["label"] == "old"},
    "generation_flip_timeline": {
        "precache_shell_at_P0_old_page": shell_gen_of(pre)["label"],
        "precache_shell_at_P1_offline": shell_gen_of(p1.get("offline_sample") or {})["label"],
        "precache_shell_at_P1_back_online": shell_gen_of(p1.get("back_online_sample") or {})["label"],
        "precache_shell_at_B1_after_one_navigation": shell_gen_of(B1_last)["label"],
        "executed_bundle_at_B1_after_one_navigation": executed(B1_last)},
    "forbidden_moves": {"unregister_called_by_instrument": camp["forbidden_moves_taken"]["unregister_called"],
                        "cache_clear_called_by_instrument": camp["forbidden_moves_taken"]["cache_clear_called"],
                        "source_audit": runner.get("forbidden_move_audit")},
    "isolation": runner.get("isolation"),
    "instrument_page_errors": camp.get("instrument", {}).get("pageErrors"),
    "update_notice_search": {"pattern": UPDATE_NOTICE.pattern, "samples_scanned": len(all_samples),
                             "hits": notice_hits},
    "cells": cells,
    "summary": {"B1": c1["verdict"], "B2": c2["verdict"], "B3": c3["verdict"],
                "cells_red_releasing_B_write_right":
                    [k for k, v in (("B1", c1), ("B2", c2), ("B3", c3)) if str(v["verdict"]).startswith("RED")]}}
io.open(os.path.join(LANE, "o274_verdict_%s.json" % RUN), "w", encoding="utf-8").write(
    json.dumps(result, ensure_ascii=False, indent=2))
print(json.dumps({"summary": result["summary"], "timeline": result["generation_flip_timeline"],
                  "B1": {k: v for k, v in c1.items() if k != "registrations_final"},
                  "B2": c2, "B3": {k: v for k, v in c3.items() if k != "registrations"},
                  "update_notice": result["update_notice_search"], "identities": result["identities"],
                  "forbidden": result["forbidden_moves"], "isolation": result["isolation"]},
                 ensure_ascii=False, indent=1))
