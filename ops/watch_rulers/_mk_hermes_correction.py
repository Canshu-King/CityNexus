"""Correction to my own ORD-0318 feasibility artifact. Every value below was re-measured by me in this session
from the git objects named; nothing is copied from the lane that found the errors (lane S2-hermes-port), although
its credit is recorded."""
import io
import json
import subprocess
import time

REPO = "D:/moodle/CityNexus"
TIP = "30de4ebe409f49c5e25f4758cb2e5f4e90764a4f"
HERMES_NAME = "origin/hermes/validation-0212"
HERMES_MEASURED = "0fe51945cdf2d0ae35494b615f3418957174da03"
MERGE_BASE = "7d22cd0eb7840121ba42a5ba363e1a4c7ca1a7e7"
OLD_ARTIFACT = "2036d33b24e2bbbd6bad5fc7e12d785c219ce0a0"
CAND = "afbbf5be3256d76eac0453ab3ad8e6dd1356d7cc"


def git(*a):
    p = subprocess.run(["git", "-C", REPO] + list(a), capture_output=True, text=True, timeout=600)
    return (p.stdout or "").strip(), p.returncode


name_now, _ = git("rev-parse", HERMES_NAME)
own, _ = git("rev-list", "--count", "%s..%s" % (MERGE_BASE, HERMES_MEASURED))
g_upgrade, _ = git("grep", "-n", "_upgrade_cached_request_replan_response", HERMES_MEASURED,
                   "--", "backend/app/agent/gateway.py")
g_view_test, rc_view_test = git("grep", "-c", "HermesReplanProposalView", HERMES_MEASURED, "--",
                                "backend/tests/test_v18_hermes_r20_transport_reliability_probe.py")
g_view_def, _ = git("grep", "-n", "class HermesReplanProposalView", HERMES_MEASURED)
g_view_tip, rc_view_tip = git("grep", "-c", "HermesReplanProposalView", TIP)
g_upg_tip, rc_upg_tip = git("grep", "-c", "_upgrade_cached_request_replan_response", TIP)
diff_state, _ = git("diff", "--name-status", TIP + ".." + CAND)
buckets = {}
for line in diff_state.split("\n"):
    if not line.strip():
        continue
    st, path = line.split("\t", 1)
    buckets.setdefault(st, 0)
    buckets[st] += 1
product_paths = sum(1 for line in diff_state.split("\n") if line.split("\t")[-1].startswith(
    ("backend/app/", "frontend/", "data/", "contracts/")))

out = {
    "schema": "CNX_CMDR_HERMES_FEASIBILITY_CORRECTION_V1",
    "lane": "commander 494abfd7",
    "at_local": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    "corrects": {"artifact": "evidence/cmdr-hermes-mainline-feasibility-2350/feasibility_r1.json",
                 "blob": OLD_ARTIFACT,
                 "policy": "a published path is never rewritten or deleted; this file only adds corrections"},
    "found_by": "lane S2-hermes-port (ORD-0318) reverse-engineered the bucket arithmetic and re-grepped the line; "
                "every claim below was then re-measured by the commander from git objects, not copied",
    "corrections": [
        {"id": "C1_ref_name_is_not_a_source",
         "wrong_in_old": "`genealogy` quoted the branch as if `refs/heads/hermes/validation-0212` still carried "
                         "the measured line",
         "measured_now": {"ref_now_points_at": name_now, "measured_line": HERMES_MEASURED,
                          "own_commits_from_merge_base": own, "merge_base": MERGE_BASE},
         "rule": "pin Hermes by full 40 hex and re-count with `git rev-list --count <merge-base>..<sha>` before "
                 "quoting a commit count; a force-push moves the name, not the history I measured"},
        {"id": "C2_bucket_sums",
         "wrong_in_old": "`hermes_named_files_on_branch` presented buckets {scripts 67, backend/tests 22, reports "
                         "25, other 21} under `harness_only_paths: 115`, but those four sum to 135 = the named "
                         "total, not the harness-only subset",
         "measured_now": {"named_total": 135, "harness_only_recomposition": "67 scripts + 22 backend/tests + 21 "
                          "reports/hermes + 4 reports/product-v1x + 1 agent-mcp/tests = 115"},
         "rule": "a bucket table must state which denominator it sums to; two different denominators in one field "
                 "set is how a self-consistent-looking artifact lies"},
        {"id": "C3_symbol_attribution",
         "wrong_in_old": "`product_symbol_gaps` said `_upgrade_cached_request_replan_response` had "
                         "`on_hermes: false`, and put `HermesReplanProposalView` behind a backend test",
         "measured_now": {"upgrade_def_and_calls_on_hermes_line": g_upgrade.split("\n")[:3],
                          "upgrade_hits_on_tip_rc": rc_upg_tip,
                          "view_hits_in_that_test_rc": rc_view_test,
                          "view_class_defined_at": g_view_def,
                          "view_hits_on_tip_rc": rc_view_tip},
         "reading": "the first symbol is on the Hermes line and simply absent from the tip; the second is not "
                    "referenced by that test at all - the chain is test -> scripts/hermes_r20_..._probe.py -> "
                    "scripts/hermes_r4_contract_probe.py -> `citynexus_mcp.schemas`, so Group B's home is "
                    "`agent-mcp/`, not `backend/app/`"},
        {"id": "C4_model_dependent_is_a_grep_proxy",
         "wrong_in_old": "`model_dependent_rounds` counted 36 runnable files as if a grep hit proved a model call",
         "measured_now": "the two tests named there were actually run in this session and passed without any "
                         "provider call (`\"real_model\": True` is a key inside a literal fixture they assert "
                         "over), so the 36 is an upper bound from text search, not a measurement",
         "rule": "a count derived from grep must say so in the field name; otherwise someone will use it as an "
                 "exclusion list"},
    ],
    "port_candidate_as_delivered": {
        "candidate": CAND, "tip_at_check": TIP,
        "state_buckets": buckets, "paths_touching_product_dirs": product_paths,
        "preflight_dry": "READY_TO_LAND / ff=True / ahead 1 / behind 0 / product introduced: (none)"
                         " (receipt evidence/cmdr-landing-ORD-0318-gen4*/preflight_r1.json family)",
        "commander_clean_arm_run": "git archive of the candidate + venv Python 3.12.14: 22 files -> collected 58 "
                                   "with 2 collection errors; 20 files (the two unimportable ones removed) -> "
                                   "58 passed / 0 failed / 0.75s",
        "why_not_landed_yet": "with those 2 unimportable test files inside the authoritative tree, "
                              "`pytest -q backend/tests` aborts during collection and executes 0 tests "
                              "(observed directly: `Interrupted: 2 errors during collection`), so landing this "
                              "shape would poison every later full-suite gate; S2 was asked to re-cut at "
                              "107 paths with the two named in the receipt instead of skipped"},
    "discipline": {"product_bytes_changed": 0, "refs_moved": 0, "published_paths_overwritten": 0,
                   "credential_values_printed": 0, "lane_words_edited": 0},
    "claim_kind": "recomputation", "derived": {},
}
d = out["derived"]
d["ref_name_moved_off_measured_line"] = name_now != HERMES_MEASURED
d["old_bucket_buckets_sum_to_named_total"] = (67 + 22 + 25 + 21) == 135
d["harness_only_recomposition_adds_up"] = (67 + 22 + 21 + 4 + 1) == 115
d["upgrade_symbol_found_on_hermes_line"] = bool(g_upgrade)
d["upgrade_symbol_absent_from_tip"] = rc_upg_tip != 0
d["view_absent_from_tip"] = rc_view_tip != 0
d["view_not_referenced_by_that_test"] = rc_view_test != 0
d["candidate_adds_nothing_to_product_dirs"] = product_paths == 0
d["candidate_is_all_additions"] = set(buckets) == {"A"}
out["claimed_result"] = ("4 corrections to %s; hermes name now %s vs measured line %s (own commits %s); "
                         "candidate %s adds %d paths, %d of them in product dirs"
                         % (OLD_ARTIFACT[:12], name_now[:12], HERMES_MEASURED[:12], own, CAND[:12],
                            sum(buckets.values()), product_paths))
io.open("_hermes_correction.json", "w", encoding="utf-8", newline="\n").write(
    json.dumps(out, ensure_ascii=False, indent=1))
print(json.dumps(d, ensure_ascii=False, indent=1))
print(out["claimed_result"])
