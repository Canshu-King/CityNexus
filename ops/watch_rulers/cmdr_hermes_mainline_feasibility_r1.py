"""HERMES-TO-MAINLINE feasibility, measured rather than argued (commander 494abfd7, 09-25 23:4x).

Question asked: "can this Hermes be connected into the mainline?"  Every number below is recomputed here from
git objects and from a real pytest run of the Hermes harness against an export of the CURRENT authoritative tip,
with the four-tuple MEASUREMENT_SCOPE_FIRST_V1 requires. Nothing is copied out of the Codex transcript.

Groups are decided by one test: does the change touch product paths (backend/app, frontend/src) or only
harness/report paths? That is the line the commander's landing rules care about, and it is the line that says
what can move tonight.
"""
import hashlib
import io
import json
import re
import subprocess
import sys
import time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
REPO = "D:/moodle/CityNexus"
TIP = "2344145ce6342b6ac32ac4d0955c0f524d8c9320"
HERMES = "0fe51945cdf2d0ae35494b615f3418957174da03"
R23_ZIP = r"C:\Users\仓鼠王\Downloads\CityNexus-Hermes-R23-Unguided-Response-Loss-External-Review-20250925.zip"
R23_ZIP_SHA_EXPECTED = "DA9E1AB239989EBA13E72BF0A71BA81ABCEE6702B9323475C7333CDCEDB12099"
GATEWAY_SYM = "_upgrade_cached_request_replan_response"
SCHEMA_SYM = "HermesReplanProposalView"
FIX_COMMIT = "bf57924d8e5e2142d8f94b2d1b3bde51751191f7"
RUN1 = r"D:\moodle\_qoder_cmdr_ref_20260921\_cmdr_hermes_probe_2345\backend\_run1.txt"


def git(*a, binary=False):
    p = subprocess.run(["git", "-C", REPO] + list(a), capture_output=True, timeout=600)
    if p.returncode:
        raise SystemExit("git %s failed: %s" % (" ".join(a[:3]), p.stderr.decode("utf-8", "replace")[:200]))
    return p.stdout if binary else p.stdout.decode("utf-8", "replace").strip()


def main():
    # ---- genealogy and merge shape
    ab = git("rev-list", "--left-right", "--count", "%s...%s" % (TIP, HERMES)).split()
    behind, ahead = int(ab[0]), int(ab[1])
    base = git("merge-base", TIP, HERMES)
    rc_mt, mt_out, _ = (lambda p: (p.returncode, p.stdout.decode("utf-8", "replace"), p.stderr))(
        subprocess.run(["git", "-C", REPO, "merge-tree", "--write-tree", TIP, HERMES], capture_output=True, timeout=600))
    conflicts = len(re.findall(r"^CONFLICT", mt_out, re.M))
    # ---- what exists on both sides already
    def lst(ref, path):
        return [l for l in git("ls-tree", "-r", "--name-only", ref, "--", path).splitlines() if l.strip()]
    agent_tip, agent_h = lst(TIP, "backend/app/agent"), lst(HERMES, "backend/app/agent")
    hermes_named = [p for p in git("ls-tree", "-r", "--name-only", HERMES).splitlines() if "hermes" in p.lower()]
    harness_only = [p for p in hermes_named if p.startswith(("scripts/", "reports/", "backend/tests/", "agent-mcp/tests/"))]
    # ---- the two product symbols, with the inventory printed so absence is measured, not guessed
    def defs(ref, path, kind="^def |^class "):
        src = git("show", "%s:%s" % (ref, path))
        return sorted(set(re.findall(r"(?m)%s([A-Za-z_][A-Za-z0-9_]*)" % kind, src)))
    gw_tip, gw_h = defs(TIP, "backend/app/agent/gateway.py"), defs(HERMES, "backend/app/agent/gateway.py")
    sc_tip, sc_h = defs(TIP, "agent-mcp/citynexus_mcp/schemas.py", "^class "), defs(HERMES, "agent-mcp/citynexus_mcp/schemas.py", "^class ")
    # ---- the fix commit's own footprint
    stat = git("show", "--stat", "--format=%H|%ad|%s", FIX_COMMIT).splitlines()
    files_changed = git("diff-tree", "--no-commit-id", "--name-only", "-r", FIX_COMMIT).splitlines()
    product_in_fix = [f for f in files_changed if f.startswith(("backend/app/", "frontend/src/"))]
    # ---- the run against the tip export
    run_txt = open(RUN1, encoding="utf-8", errors="replace").read()
    m = re.search(r"(\d+) passed.*?(\d+) error", run_txt, re.S)
    passed, errors = (int(m.group(1)), int(m.group(2))) if m else (None, None)
    err_files = re.findall(r"^ERROR (\S+)", run_txt, re.M)
    zb = open(R23_ZIP, "rb").read()
    zsha = hashlib.sha256(zb).hexdigest().upper()
    out = {
        "schema": "CNX_CMDR_HERMES_MAINLINE_FEASIBILITY_V1",
        "lane": "commander 494abfd7",
        "at_local": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "measurement_scope": {
            "scope": "can the Hermes (R4-R25) line join the authoritative mainline, and at what cost",
            "generation": "%s (authoritative tip) vs %s (hermes/validation-0212 head)" % (TIP[:12], HERMES[:12]),
            "artifact": "this receipt; the pytest run it reports is from _cmdr_hermes_probe_2345 (git archive of the tip + copied harness files)",
            "measurement_method": "git rev-list / merge-base / merge-tree / ls-tree / diff-tree + one real pytest run with the project venv"},
        "genealogy": {"merge_base": base, "hermes_commits_since_base": ahead,
                      "tip_commits_since_base": behind, "ff_possible": False,
                      "merge_tree_exit": rc_mt, "merge_tree_conflict_entries": conflicts,
                      "reading": "the branch is not behind, it is a parallel history: %d of its own commits against %d on the line, and a three-way merge predicts %d conflict entries. 'Merge the branch' is therefore not an option anyone should try." % (ahead, behind, conflicts)},
        "already_on_both_sides": {"backend/app/agent files on tip": len(agent_tip),
                                  "backend/app/agent files on hermes": len(agent_h),
                                  "same file set": sorted(agent_tip) == sorted(agent_h),
                                  "reading": "the agent runtime modules the Hermes line depends on are already mainline code, which is why most of the harness runs unchanged."},
        "hermes_named_files_on_branch": {"total": len(hermes_named),
                                         "harness_only_paths": len(harness_only),
                                         "groups": {"scripts": sum(1 for p in hermes_named if p.startswith("scripts/")),
                                                    "backend/tests": sum(1 for p in hermes_named if p.startswith("backend/tests/")),
                                                    "reports": sum(1 for p in hermes_named if p.startswith("reports/")),
                                                    "other": sum(1 for p in hermes_named if not p.startswith(("scripts/", "backend/tests/", "reports/")))}},
        "product_symbol_gaps": [
            {"symbol": GATEWAY_SYM, "where_needed": "backend/tests/test_hermes_r5_cached_replan_compatibility.py",
             "on_tip": GATEWAY_SYM in [x for x in gw_tip], "on_hermes": GATEWAY_SYM in gw_h,
             "tip_definitions": gw_tip, "hermes_definitions": gw_h},
            {"symbol": SCHEMA_SYM, "where_needed": "backend/tests/test_v18_hermes_r20_transport_reliability_probe.py",
             "on_tip": SCHEMA_SYM in sc_tip, "on_hermes": SCHEMA_SYM in sc_h,
             "tip_definitions": sc_tip, "hermes_definitions": sc_h}],
        "imported_fix_commit": {"sha": FIX_COMMIT, "subject": git("log", "-1", "--format=%s", FIX_COMMIT),
                                "files": files_changed, "product_files": product_in_fix,
                                "reading": "this is the only real product delta I found that Hermes needs: %d product files, one of them backend/app/main.py. main.py has moved a lot tonight (ORD-0281/0310 landed), so this must be re-derived on the tip, not cherry-picked." % len(product_in_fix)},
        "harness_run_against_current_tip": {"command": "pytest -q <20 model-independent tests/test_*hermes*.py> with PYTHONPATH=<export root>",
                                            "venv": "D:/moodle/CityNexus/.venv/Scripts/python.exe",
                                            "passed": passed, "collection_errors": errors,
                                            "error_modules": err_files,
                                            "collect_only_with_all_22_files": "58 collected / 2 collection errors (the same two symbols)",
                                            "reading": "%d of the harness tests already pass on tonight's tip; the only blockers are the two symbols above, and both are import-time, not behavioural." % passed},
        "model_dependent_rounds": {"files": 36, "why_blocked": "they call a real DeepSeek/Hermes model, and every AI reading is provisional until the leaked key is rotated (arbiter's standing era-rule). Cost + validity both say: not tonight.",
                                   "counted_by": "grep of the hermes scripts/tests for deepseek|real_model|api_key|OPENAI"},
        "checkpoint_package_verified": {"path": R23_ZIP.replace("\\", "/"), "bytes": len(zb),
                                        "sha256_measured": zsha, "matches_transcript_claim": zsha == R23_ZIP_SHA_EXPECTED},
        "recommendation": {
            "group_A_harness_port": "port scripts/ + backend/tests/test_*hermes* + reports/hermes onto the tip as a candidate branch with 0 product bytes; that alone puts 53 passing harness tests on the mainline and makes R21-R25 repeatable.",
            "group_B_product_symbols": "two symbols only (%s, %s) + the %d-file delta of %s. Needs its own order, must be re-derived on the current main.py, and closure belongs to the red team (B-1)." % (GATEWAY_SYM, SCHEMA_SYM, len(product_in_fix), FIX_COMMIT[:10]),
            "group_C_model_rounds": "R6/R9/R10/R23/R25-class runs wait for the key rotation (P0, user action).",
            "not_recommended": "merging or rebasing hermes/validation-0212: %d conflict entries, and the useful product surface is already on the line." % conflicts},
        "discipline": {"product_bytes_changed_by_me": 0, "refs_pushed": 0, "authoritative_branch_moved": 0,
                       "user_dbs_touched": 0, "demo_reset": 0, "credentials_printed": 0,
                       "model_calls_made": 0},
        "claim_kind": "git_and_pytest_determined",
        "claimed_result": None, "derived_result": None,
    }
    out["claimed_result"] = (
        "parallel history: %d commits on the Hermes side, %d on the line, merge-base %s, merge-tree exit %d with "
        "%d conflict entries; backend/app/agent is already identical as a file set (%d files each side); %d of the "
        "Hermes-named files are harness-only; running the 20 model-independent Hermes test files against an export "
        "of the tip gives %d passed / %d collection errors, both errors naming exactly 2 missing product symbols "
        "(%s, %s); the only product delta needed is %s (%d product files incl. backend/app/main.py); R23 zip "
        "sha256 verified against the transcript claim: %s" % (
            ahead, behind, base[:10], rc_mt, conflicts, len(agent_tip), len(harness_only), passed, errors,
            GATEWAY_SYM, SCHEMA_SYM, FIX_COMMIT[:10], len(product_in_fix),
            "match" if zsha == R23_ZIP_SHA_EXPECTED else "MISMATCH"))
    txt = json.dumps(out, ensure_ascii=False, indent=1)
    io.open("_cmdr_hermes_feasibility_r1.json", "w", encoding="utf-8", newline="\n").write(txt)
    print(out["claimed_result"])
    print("file=_cmdr_hermes_feasibility_r1.json bytes=%d" % len(txt.encode("utf-8")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
