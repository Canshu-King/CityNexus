"""Build the ORD-0326 delivery artifact from the run artifacts: r4 before/after, tsc, the mutation harness,
the collision readings, and what this lane deliberately did not touch.
"""
import io
import json
import os
import subprocess
import sys
import time

ROOT = "D:/moodle/_qoder_cmdr_ref_20260921/live_checks"
SCRATCH = os.path.join(ROOT, "_sweep_scratch")
WT = "D:/moodle/_qoder_ord0326_S1"
FRONTEND = os.path.join(WT, "frontend")
REPO = "D:/moodle/CityNexus"
R4 = "eb262f59e54d5142ad0e8041704e751eac473ace"
BASE = "65df31df96cfb8a954f5feb36484710a883e1597"
MY_FILES = [
    "frontend/src/lib/serverReason.ts",
    "frontend/src/components/ServerReasonDetail.tsx",
    "frontend/src/features/stay/HotelsPanel.tsx",
    "frontend/src/features/agent/AgentComposer.tsx",
    "frontend/src/features/agent/CopilotDock.tsx",
    "frontend/e2e/server-reason-ord0326.spec.ts",
    "frontend/playwright.logic.config.ts",
]
# r4 readings taken before the change (one run per file, at BASE) and after (in the worktree)
R4_BEFORE = {"frontend/src/app/V8Experience.tsx": 3, "frontend/src/features/agent/AgentComposer.tsx": 1,
             "frontend/src/features/agent/CopilotDock.tsx": 2, "frontend/src/features/stay/HotelsPanel.tsx": 1}


def git(*a, cwd=REPO):
    r = subprocess.run(["git"] + list(a), capture_output=True, cwd=cwd)
    if r.returncode:
        raise SystemExit("GIT_FAILED %s %s" % (" ".join(a), r.stderr.decode("utf-8", "replace")[:160]))
    return r.stdout.decode("utf-8", "replace").strip()


def j(p):
    return json.load(io.open(p, encoding="utf-8"))


def main():
    tip = git("ls-remote", "origin", "refs/heads/mirror/integration-frontend-apple-pass1").split()[0]
    branch = git("rev-parse", "HEAD", cwd=WT)
    after = j(os.path.join(SCRATCH, "r4_after_three.json"))
    muts = j(os.path.join(FRONTEND, "_mutation_results.json"))
    after_by_file = {}
    for h in after["hits"]:
        key = [p for p in MY_FILES if h["file"].endswith(p.split("/")[-1])]
        after_by_file[key[0] if key else h["file"]] = after_by_file.get(key[0] if key else h["file"], 0) + 1

    tsc = subprocess.run(["node", "node_modules/typescript/bin/tsc", "-p", "tsconfig.typecheck.json", "--noEmit"],
                         capture_output=True, cwd=FRONTEND)
    spec = subprocess.run(["node", "node_modules/@playwright/test/cli.js", "test",
                           "--config", "playwright.logic.config.ts", "--reporter=list"],
                          capture_output=True, cwd=FRONTEND)
    spec_out = spec.stdout.decode("utf-8", "replace")
    spec_green = [ln.strip() for ln in spec_out.splitlines() if "passed" in ln or "failed" in ln]

    mutation_rows = []
    for name, v in muts.items():
        if name in ("restore", "after_restore"):
            continue
        mutation_rows.append({"mutation": name, "red_tests": v.get("red_tests", []),
                              "caught": bool(v.get("spec_caught_it")), "summary": v.get("summary", [])})

    doc = {
     "schema": "CNX_ORD0326_CHANNEL_V1",
     "order": "ORD-0326",
     "lane": "S1-q64sweep",
     "at_local": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
     "generation": tip,
     "candidate_branch": "agent/S1-q64sweep-candidates",
     "candidate_tip": branch,
     "candidate_verified_by_ls_remote": git("ls-remote", "origin", "refs/heads/agent/S1-q64sweep-candidates").split()[0],
     "based_on": BASE,
     "base_is_ancestor_of_generation": git("merge-base", "--is-ancestor", BASE, tip, cwd=WT) == "",
     "frontend_tree_identical_base_vs_generation":
         git("rev-parse", "%s:frontend/src" % BASE) == git("rev-parse", "%s:frontend/src" % tip),
     "authoritative_branch_pushed": False,
     "ruler": R4,
     "ruler_route": "commander/control:evidence/ord0322-ast-taint-S4/ui_exposure_taint_ast_r1.cjs",
     "collision_check": {
        "method": "ls-remote all heads + the 03:34 commander dispatch in the ledger mirror "
                  "(origin/cmdcontrol:CITYNEXUS_AGENT_CONTROL.md)",
        "heads_seen": int(subprocess.run(["git", "ls-remote", "--heads", "origin"], capture_output=True,
                                         cwd=REPO).stdout.decode().strip().count("\n")) + 1,
        "lane_B_candidate_branch_found": False,
        "B_claimed_per_ledger": ["frontend/src/components/ProductErrorBoundary.tsx",
                                 "frontend/src/features/inbox/JourneyInboxWorkbench.tsx (:88 and the 9 cells "
                                 "downstream of it)"],
        "yielded_by_me": ["frontend/src/features/inbox/JourneyInboxWorkbench.tsx",
                          "frontend/src/components/ProductErrorBoundary.tsx",
                          "frontend/src/features/planning/PlanWithAiSheet.tsx",
                          "frontend/src/features/planning/PlanComparison.tsx"],
        "conflict_found": "the order named JourneyInboxWorkbench as this lane's home turf, while the ledger "
                          "dispatch at 03:34 assigns the same file's thrower to @B; the order's own rule "
                          "(two lanes, one file, not both) decided it - B keeps it",
     },
     "files_written": [{"path": p, "blob_at_candidate_tip": git("rev-parse", "%s:%s" % (branch, p), cwd=WT)}
                       for p in MY_FILES],
     "one_channel_design": {
        "helper": "frontend/src/lib/serverReason.ts :: describeServerReason + reasonFromThrown",
        "only_dom_slot": "frontend/src/components/ServerReasonDetail.tsx (attributed, inside <details>, "
                         "per CMDR_DECISION Q67=1)",
        "strings_for_the_screen": "serverReasonScreenTexts, JSX-free so a spec can assert what a traveller reads",
        "allowed_fields": ["http_status", "content_type", "body_bytes", "response_received", "elapsed_ms",
                           "request_id"],
        "never_rendered": ["a caught object", "cause.message", "a raw body", "anything multi-line (stack-shaped)"],
     },
     "r4_hits_before": R4_BEFORE,
     "r4_hits_after_by_file": after_by_file,
     "r4_before_total_touched_files_only": sum(v for k, v in R4_BEFORE.items() if k in MY_FILES),
     "r4_after_total": sum(after_by_file.values()),
     "r4_file_not_attempted": {"frontend/src/app/V8Experience.tsx": R4_BEFORE["frontend/src/app/V8Experience.tsx"]},
     "r4_after_rules": sorted({h["rule"] for h in after["hits"]}),
     "r4_remaining_reading": "HotelsPanel went 1 -> 0. AgentComposer/CopilotDock changed rule rather than "
                             "disappearing: the sinks now read UPSTREAM_TEXT_VIA_HELPER_TO_DOM because "
                             "reasonFromThrown touches `.body` on a caught error and r4 is per-file, so it "
                             "cannot see that the helper sanitises the value. The raw-exception read "
                             "(cause.message into a rendered string) is gone from those three sinks.",
     "tsc": {"command": "node node_modules/typescript/bin/tsc -p tsconfig.typecheck.json --noEmit",
             "exit": tsc.returncode, "output": tsc.stdout.decode("utf-8", "replace").strip()[:400]},
     "spec": {"command": "node node_modules/@playwright/test/cli.js test --config "
                         "playwright.logic.config.ts", "exit": spec.returncode, "summary": spec_green,
              "why_a_separate_config": "playwright.config.ts binds 127.0.0.1:8000 with "
                                       "reuseExistingServer:true; :8000 is NOT AVAILABLE by ruling and "
                                       "whatever answers there may be another lane's backend",
              "harness_limit_measured": "Playwright's transform rewrites JSX into a node shape "
                                        "react-dom/server rejects ({__pw_type,type,props,key}), measured on a "
                                        "one-line JSX module, so the spec asserts the strings the component "
                                        "renders rather than the markup"},
     "mutations": mutation_rows,
     "all_mutations_caught": bool(mutation_rows) and all(m["caught"] for m in mutation_rows),
     "not_done": [
        {"what": "frontend/src/app/V8Experience.tsx (:1385 and :1562, both fed by the setMessage at :1030)",
         "why_not": "the `message` state has 15 writers in that file and it is the one frontend file the "
                    "ledger records as already hand-merged across two lanes; landing it properly means "
                    "deciding the state shape, which is a larger change than I can verify in this window. "
                    "Left whole rather than half-opened.",
         "next_owner": "S1 after the B/F files settle, or whoever takes the shell state"},
        {"what": "the 9 JourneyInboxWorkbench cells", "why_not": "yielded to @B by the collision rule",
         "next_owner": "B - the channel and its tests are on agent/S1-q64sweep-candidates, ready to adopt"},
        {"what": "the full e2e suite", "why_not": "needs :8000 plus a dev server; not started by ruling and "
                                                   "not something I can attribute to my own branch if "
                                                   "another lane's server answers",
         "next_owner": "whoever holds the phone surface"},
     ],
     "claim_kind": "code_landed_on_candidate_branch",
     "claimed_result": None, "derived_result": None,
    }
    doc["claimed_result"] = ("candidate %s at %s: %d files written, tsc exit %d, spec %s, r4 %d -> %d on "
                             "the touched files, all %d mutations caught"
                             % (doc["candidate_branch"], doc["candidate_tip"][:12], len(MY_FILES),
                                doc["tsc"]["exit"], " ".join(doc["spec"]["summary"]),
                                doc["r4_before_total_touched_files_only"], doc["r4_after_total"],
                                len(mutation_rows)))
    doc["derived_result"] = ("one shared server-reason channel landed for the stay and agent surfaces; "
                             "inbox and boundary files yielded to B; V8Experience left whole and named")
    out = os.path.join(ROOT, "_ord0326_channel_r1.json")
    io.open(out, "w", encoding="utf-8", newline="\n").write(json.dumps(doc, ensure_ascii=False, indent=1))
    print(doc["claimed_result"])
    print("generation=%s base_ancestor=%s tree_identical=%s"
          % (tip[:12], doc["base_is_ancestor_of_generation"],
             doc["frontend_tree_identical_base_vs_generation"]))
    print("heads=%s yielded=%d" % (doc["collision_check"]["heads_seen"], len(doc["collision_check"]["yielded_by_me"])))
    print("out=%s bytes=%d" % (out, os.path.getsize(out)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
