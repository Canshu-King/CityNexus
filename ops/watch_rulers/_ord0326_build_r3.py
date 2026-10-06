"""ORD-0326 re-scoped delivery receipt: branch-off sha, the exact files this lane touches, the three-lane
intersection table, and the r5 module-graph before/after for the re-scoped branch.

Counts are read from the r5 artifacts; the intersection is recomputed here from each lane's own merge-base
rather than against the moving tip (a lane whose work already landed otherwise appears to touch nothing,
and a lane based two generations back appears to touch everything).
"""
import collections
import io
import json
import os
import subprocess
import sys
import time

ROOT = "D:/moodle/_qoder_cmdr_ref_20260921/live_checks"
SCRATCH = os.path.join(ROOT, "_sweep_scratch")
REPO = "D:/moodle/CityNexus"
R5 = "ff98091cf3accb0d836ae25ba49820170b92d932"
BRANCH = "agent/S1-q64sweep-candidates-r2"
BRANCH_SHA = "919f09a70a0a140cd0a19a8abeb90f340dfa9f11"
BRANCH_OFF = "0f8b925facabc9df57bab600b86d999dd515bf94"
LANES = {"S1": BRANCH_SHA,
         "B": "e302e4c433712284a23c1c0ab11147fe105e1e22",
         "D": "bff5c462bdea"}


def run(*a):
    r = subprocess.run(["git", "-C", REPO] + list(a), capture_output=True)
    return r.stdout.decode("utf-8", "replace").strip()


def load(name):
    return json.load(io.open(os.path.join(SCRATCH, name), encoding="utf-8"))


def keys(doc):
    return collections.Counter((h["file"].split("/")[-1], h["line"], h["rule"]) for h in doc["hits"])


def main():
    tip = run("ls-remote", "origin", "refs/heads/mirror/integration-frontend-apple-pass1").split()[0]
    assert run("rev-parse", BRANCH) == BRANCH_SHA
    assert run("merge-base", "--is-ancestor", BRANCH_OFF, BRANCH) == "" , "branch is not off the ordered sha"
    committed = load("r5_committed.json")
    at_tip = load("r5_tree_tip.json")
    kt, kc = keys(at_tip), keys(committed)
    removed = sorted("%s:%d|%s" % k for k in (kt - kc))
    added = sorted("%s:%d|%s" % k for k in (kc - kt))

    lanes = {}
    for name, sha in LANES.items():
        mb = run("merge-base", sha, tip)
        files = [f for f in run("diff", "--name-only", mb, sha).split() if f.startswith("frontend/")]
        lanes[name] = {"branch_tip": sha, "branch_off_merge_base_with_current_tip": mb,
                       "frontend_files": files, "file_count": len(files)}
    inter = {"S1_and_B": sorted(set(lanes["S1"]["frontend_files"]) & set(lanes["B"]["frontend_files"])),
             "S1_and_D": sorted(set(lanes["S1"]["frontend_files"]) & set(lanes["D"]["frontend_files"])),
             "B_and_D": sorted(set(lanes["B"]["frontend_files"]) & set(lanes["D"]["frontend_files"])),
             "method": "each lane diffed against its own merge-base with the current tip; the tip is NOT "
                       "used as the base, because D's ORD-0325 already landed into it and B branched two "
                       "generations back"}

    doc = {
     "schema": "CNX_ORD0326_CHANNEL_V3",
     "order": "ORD-0326",
     "lane": "S1-q64sweep",
     "revision": "r3 - re-scoped by commander 04:50; supersedes the scope of channel_r1/r2",
     "at_local": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
     "generation_measured": BRANCH_OFF,
     "authoritative_tip_now": tip,
     "tip_moved": tip != BRANCH_OFF,
     "branch_off_sha_ordered": BRANCH_OFF,
     "candidate_branch": BRANCH,
     "candidate_tip": BRANCH_SHA,
     "candidate_verified_by_ls_remote": run("ls-remote", "origin", "refs/heads/" + BRANCH).split()[0],
     "ruler": R5,
     "ruler_selftest": load("r5_selftest.json")["verdict"],
     "ruler_mode": "--tree over `git archive <sha> frontend/src` exports; per-file --ref reproduces r4 and "
                   "was discarded as a measurement",
     "files_touched_by_this_lane": lanes["S1"]["frontend_files"],
     "yielded_files_confirmed_untouched": {
        "frontend/src/features/stay/HotelsPanel.tsx":
            run("diff", "--name-only", BRANCH_OFF, BRANCH_SHA).count("HotelsPanel") == 0,
        "frontend/src/app/V8Experience.tsx":
            run("diff", "--name-only", BRANCH_OFF, BRANCH_SHA).count("V8Experience") == 0,
        "frontend/src/features/planning/PlanWithAiSheet.tsx":
            run("diff", "--name-only", BRANCH_OFF, BRANCH_SHA).count("PlanWithAiSheet") == 0,
        "frontend/src/features/planning/PlanComparison.tsx":
            run("diff", "--name-only", BRANCH_OFF, BRANCH_SHA).count("PlanComparison") == 0,
        "note": "HotelsPanel was edited on the first branch (b32c0d65) and is reverted per-file to its "
                "branch-off blob here; no whole-branch reset was used",
     },
     "r5_before": {"hits": len(at_tip["hits"]), "files": len({h["file"] for h in at_tip["hits"]}),
                   "per_rule": at_tip["per_rule"], "at_generation": BRANCH_OFF},
     "r5_after": {"hits": len(committed["hits"]), "files": len({h["file"] for h in committed["hits"]}),
                  "per_rule": committed["per_rule"], "measured_on": "the committed tree of " + BRANCH_SHA[:12],
                  "matches_the_worktree_reading": keys(load("r5_tree_cand2.json")) == keys(committed)},
     "sinks_removed_by_this_lane": removed,
     "sinks_added_by_this_lane": added,
     "assigned_scope_accounted": {
        "journey_inbox_cells": ["frontend/src/features/inbox/JourneyInboxWorkbench.tsx:687",
                                "frontend/src/features/inbox/JourneyInboxWorkbench.tsx:691",
                                "frontend/src/features/inbox/JourneyInboxWorkbench.tsx:731"],
        "auto_on_mount_reads_kept": ["frontend/src/features/inbox/JourneyInboxWorkbench.tsx:345",
                                     "frontend/src/features/inbox/JourneyInboxWorkbench.tsx:349"],
        "agent_cells": ["frontend/src/features/agent/AgentComposer.tsx:185",
                        "frontend/src/features/agent/CopilotDock.tsx:450",
                        "frontend/src/features/agent/CopilotDock.tsx:770"],
        "boundary_cell": ["frontend/src/components/ProductErrorBoundary.tsx:104",
                          "frontend/src/components/ProductErrorBoundary.tsx:105"],
        "stack_surface_condition": "the boundary no longer stores or renders a component stack at all - it "
                                   "goes to console.error, so the change closes the stack face rather than "
                                   "opening it",
     },
     "three_lane_intersection": inter,
     "lane_file_sets": lanes,
     "decision_needed": None,
     "verification": {
        "tsc": "node node_modules/typescript/bin/tsc -p tsconfig.typecheck.json --noEmit -> exit 0",
        "spec": "node node_modules/@playwright/test/cli.js test --config playwright.logic.config.ts -> 4 "
                "passed, on a config that starts no server (:8000 is NOT AVAILABLE and would otherwise let "
                "another lane's backend answer for mine)",
        "mutations": "three mutants (sentence into main copy / request_id dropped / multi-line guard "
                     "removed) each turn exactly one assertion red; restored byte-identical",
     },
     "command_i_ran": "git archive <sha> frontend/src | tar -x, then node ui_exposure_taint_ast_r2.cjs "
                      "--tree <export>/frontend/src --out <json>, for the branch-off tip and for the "
                      "committed candidate; lane branches diffed against their own merge-base with the tip",
     "claim_kind": "code_landed_on_candidate_branch",
     "claimed_result": None, "derived_result": None,
    }
    doc["decision_needed"] = (
        "S1 and B now modify the SAME two files (ProductErrorBoundary.tsx, JourneyInboxWorkbench.tsx): "
        "B delivered them at 04:50 on review/0323-two-exposure-cells-b, whose r5 reading is 28 -> 26 "
        "(five sinks removed, three still flagged); this re-scoped branch reads %d -> %d on the same ruler "
        "and mode (%d removed, %d added at the sanctioned slot). One implementation per file has to be "
        "picked - the two are not mergeable by git."
        % (doc["r5_before"]["hits"], doc["r5_after"]["hits"], len(removed), len(added)))
    doc["claimed_result"] = ("%s @ %s off %s: %d frontend files, r5 %d -> %d (%d sinks removed, %d added), "
                             "tsc exit 0, spec 4 passed, S1∩B = %d files, S1∩D = %d"
                             % (BRANCH, BRANCH_SHA[:12], BRANCH_OFF[:12], lanes["S1"]["file_count"],
                                doc["r5_before"]["hits"], doc["r5_after"]["hits"], len(removed), len(added),
                                len(inter["S1_and_B"]), len(inter["S1_and_D"])))
    doc["derived_result"] = "assigned scope closed under the r5 module graph; the only open item is the " \
                            "S1/B two-file overlap the commander must resolve"
    out = os.path.join(ROOT, "_ord0326_channel_r3.json")
    io.open(out, "w", encoding="utf-8", newline="\n").write(json.dumps(doc, ensure_ascii=False, indent=1))
    print(doc["claimed_result"])
    print("removed:", removed)
    print("added:", added)
    print("worktree==committed:", doc["r5_after"]["matches_the_worktree_reading"])
    print("out=%s bytes=%d" % (out, os.path.getsize(out)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
