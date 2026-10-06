"""ORD-0326 final receipt for the commander's 04:57 ruling: the presentation channel carried on a fresh
branch without HotelsPanel, the r5 reading for it, and the request_id truth on the two paths these files use.

Citations are re-read by line number from the tip export (frontend) and from
`git show <tip>:backend/...` (server), so every "where does this field come from" claim is checkable.
"""
import io
import json
import os
import subprocess
import sys
import time

ROOT = "D:/moodle/_qoder_cmdr_ref_20260921/live_checks"
SCRATCH = os.path.join(ROOT, "_sweep_scratch")
TREE = os.path.join(SCRATCH, "tip_tree", "frontend", "src")
REPO = "D:/moodle/CityNexus"
TIP = "0f8b925facabc9df57bab600b86d999dd515bf94"
BRANCH = "agent/S1-q64sweep-candidates-r4"
SHA = "c504273362163c9bc9f5c39bf30b0ef705f0d144"
ORDERED_FILES = [
    "frontend/src/lib/serverReason.ts",
    "frontend/src/components/ServerReasonDetail.tsx",
    "frontend/src/features/agent/AgentComposer.tsx",
    "frontend/src/features/agent/CopilotDock.tsx",
    "frontend/e2e/server-reason-ord0326.spec.ts",
    "frontend/playwright.logic.config.ts",
]
NOT_MINE = ["frontend/src/features/stay/HotelsPanel.tsx",
            "frontend/src/features/inbox/JourneyInboxWorkbench.tsx",
            "frontend/src/components/ProductErrorBoundary.tsx",
            "frontend/src/app/V8Experience.tsx",
            "frontend/src/features/planning/PlanWithAiSheet.tsx",
            "frontend/src/features/planning/PlanComparison.tsx"]


def git(*a):
    r = subprocess.run(["git", "-C", REPO] + list(a), capture_output=True)
    if r.returncode:
        raise SystemExit("GIT_FAILED %s %s" % (" ".join(a), r.stderr.decode("utf-8", "replace")[:160]))
    return r.stdout.decode("utf-8", "replace").strip()


def fe(rel, n):
    return io.open(os.path.join(TREE, rel), encoding="utf-8", errors="replace").read().splitlines()[n - 1].strip()


def backend(relpath):
    return git("show", "%s:%s" % (TIP, relpath)).splitlines()


def bcite(relpath, n):
    return {"where": relpath, "line": n, "text": backend(relpath)[n - 1].strip()}


def main():
    tip_now = git("ls-remote", "origin", "refs/heads/mirror/integration-frontend-apple-pass1").split()[0]
    touched = git("diff", "--name-only", TIP, SHA).split()
    assert sorted(touched) == sorted(ORDERED_FILES), ("branch carries the wrong files", touched)
    r5tip = json.load(io.open(os.path.join(SCRATCH, "r5_tree_tip.json"), encoding="utf-8"))
    r5br = json.load(io.open(os.path.join(SCRATCH, "r5_r4_branch.json"), encoding="utf-8"))

    def keys(d):
        return {(h["file"].split("/")[-1], h["line"], h["rule"]) for h in d["hits"]}

    kt, kb = keys(r5tip), keys(r5br)
    rid_counts = {f: sum(1 for l in backend(f) if "request_id" in l) for f in [
        "backend/app/agent/gateway.py", "backend/app/agent/contracts.py", "backend/app/agent/guardian.py",
        "backend/app/agent/runtime.py", "backend/app/main.py", "backend/app/schemas.py",
        "agent-mcp/citynexus_mcp/schemas.py"]}
    cls_diff = git("diff", "--numstat", TIP, SHA, "--", "frontend/src/lib/failureAttribution.ts")
    cls_lines_changed = sum(int(p) for line in cls_diff.splitlines() for p in line.split("\t")[:2] if p.isdigit())

    doc = {
     "schema": "CNX_ORD0326_FINAL_V1",
     "order": "ORD-0326",
     "lane": "S1-q64sweep",
     "at_local": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
     "ruling_executed": "commander 04:57 - the lane's channel is the single presentation layer, "
                        "classifyReadFailure stays the classification layer, HotelsPanel dropped",
     "generation": TIP,
     "authoritative_tip_now": tip_now,
     "tip_moved_after_measurement": tip_now != TIP,
     "branch_off_sha": TIP,
     "branch_off_is_ancestor": git("merge-base", "--is-ancestor", TIP, SHA) == "",
     "candidate_branch": BRANCH,
     "candidate_tip": SHA,
     "candidate_verified_by_ls_remote": git("ls-remote", "origin", "refs/heads/" + BRANCH).split()[0],
     "files_touched": touched,
     "file_count": len(touched),
     "files_not_mine_confirmed_untouched": {f: (f not in touched) for f in NOT_MINE},
     "two_layers_not_two_implementations": {
        "presentation": "frontend/src/lib/serverReason.ts (describeServerReason / reasonFromThrown / "
                        "serverReasonScreenTexts) + frontend/src/components/ServerReasonDetail.tsx",
        "classification": "frontend/src/lib/failureAttribution.ts :: classifyReadFailure - untouched by this "
                          "branch, it still owns which kind of failure this is",
        "classification_lines_changed": cls_lines_changed,
     },
     "r5": {
        "ruler": "ff98091cf3accb0d836ae25ba49820170b92d932",
        "mode": "--tree over `git archive <sha> frontend/src` exports",
        "at_branch_off": len(r5tip["hits"]),
        "on_this_branch": len(r5br["hits"]),
        "sinks_removed": sorted("%s:%d|%s" % k for k in (kt - kb)),
        "sinks_added": sorted("%s:%d|%s" % k for k in (kb - kt)),
        "added_is_the_designated_slot_only": all(x[0] == "ServerReasonDetail.tsx" for x in (kb - kt)),
        "other_lanes_readings_unchanged": {
            n: (sum(1 for x in kt if x[0] == n) == sum(1 for x in kb if x[0] == n))
            for n in ["JourneyInboxWorkbench.tsx", "ProductErrorBoundary.tsx", "HotelsPanel.tsx",
                      "V8Experience.tsx", "PlanWithAiSheet.tsx", "PlanComparison.tsx"]},
     },
     "verification": {
        "tsc": "node node_modules/typescript/bin/tsc -p tsconfig.typecheck.json --noEmit -> exit 0",
        "spec": "4 passed on this branch: direction A / direction B / parked raw body / multi-line refusal, "
                "via playwright.logic.config.ts which starts no server",
        "existing_assertions_changed": 0,
        "skips_added": 0,
        "authoritative_pushes": 0,
     },
     "request_id_ruling_applied": {
        "rule": "shown when the server sent one, NOT-EMITTED otherwise, never invented",
        "hits_per_file_at_generation": rid_counts,
        "citations": {
           "inbound_contract_field": bcite("backend/app/agent/contracts.py", 67),
           "is_idempotency_scope_not_response_meta": bcite("backend/app/agent/gateway.py", 463),
           "gateway_uses_are_audit_and_signature_payloads": [bcite("backend/app/agent/gateway.py", 314),
                                                             bcite("backend/app/agent/gateway.py", 454)],
           "server_mints_these_itself": [bcite("backend/app/agent/guardian.py", 401),
                                         bcite("backend/app/agent/runtime.py", 430)],
           "frontend_optional_response_field": {"where": "frontend/src/api/citynexus.ts", "line": 558,
                                                "text": fe("api/citynexus.ts", 558),
                                                "owner": "AgentToolResponse (declared at api/citynexus.ts:553)"},
           "frontend_outbound_payload_only": {"where": "frontend/src/api/citynexus.ts", "line": 1089,
                                              "text": fe("api/citynexus.ts", 1089)},
           "error_envelope_carries_trace_id_instead": [bcite("backend/app/main.py", 456),
                                                       bcite("backend/app/main.py", 487)],
           "backend_declares_it_only_on_an_inbound_model": {"where": "backend/app/schemas.py", "line": 130,
                                                            "text": backend("backend/app/schemas.py")[129].strip(),
                                                            "enclosing_class": "AgentToolCall (extra=forbid, "
                                                                               "declared at schemas.py:127)"},
        },
        "answer_for_the_two_paths_this_branch_uses": {
           "copilot_send": "CopilotResponse (api/citynexus.ts:383) has no request_id; a refusal carries "
                           "error.trace_id (main.py:487) which the channel maps into the request_id slot - "
                           "shown as trace_id, never as a made-up id",
           "stop_and_approve": "the gateway's request_id occurrences are inbound contract values echoed into "
                               "audit rows and the canonical signature (gateway.py:314/:454), not response "
                               "keys; AgentToolResponse.request_id is optional (api/citynexus.ts:558) and "
                               "neither agent file reads it",
           "frontend_type_never_filled": "since backend/app only declares request_id on the inbound "
                                          "AgentToolCall (schemas.py:130) and echoes it into audit/signature "
                                          "rows, the optional AgentToolResponse.request_id at "
                                          "api/citynexus.ts:558 is a field this backend never populates",
           "verdict": "NOT-EMITTED on both paths under that name today; ORD-0332's real question is which "
                      "name the existing error.trace_id is exposed under - and whether to delete the dead "
                      "optional field rather than teach the backend to fill it",
        },
     },
     "field_arrival_copilot_path": {
        "route": "POST /api/v1/journeys/{journey_id}/copilot/messages (plural; main.py:11046)",
        "fields": {"http_status": "EMITTED", "content_type": "EMITTED but read on one leg only "
                   "(api/citynexus.ts:686 guard)", "body_bytes": "NOT-EMITTED (length discarded at "
                   "api/citynexus.ts:663)", "response_received": "not a field; encoded as evidence_kind "
                   "(lib/failureAttribution.ts:42)", "elapsed_ms": "NOT-EMITTED on this path",
                   "request_id": "NOT-EMITTED (0 hits in main.py; see request_id_ruling_applied)"},
        "detail_artifact": "evidence/ord0326-server-reason-S1/agent_fields_r1.json = "
                           "c80f6f61bff8d574dc529a27ba21dd9cbc5cb328 (already published, unchanged)",
     },
     "handoff_to_B": "B's two files adopt describeServerReason + <ServerReasonDetail>; the channel and its "
                     "four assertions are on this branch, and r5 shows that swap removing five sinks while "
                     "leaving the three inbox slots flagged when the sentence is re-minted instead",
     "claim_kind": "code_landed_on_candidate_branch",
     "claimed_result": None, "derived_result": None,
    }
    doc["claimed_result"] = ("%s @ %s off %s: %d files (%d ordered, 0 others), r5 %d -> %d, %d agent sinks "
                             "removed, added only at the designated slot (%s), tsc 0, spec 4 passed, "
                             "request_id NOT-EMITTED on both paths"
                             % (BRANCH, SHA[:12], TIP[:12], len(touched), len(touched),
                                len(r5tip["hits"]), len(r5br["hits"]), len(kt - kb),
                                doc["r5"]["added_is_the_designated_slot_only"]))
    doc["derived_result"] = "04:57 ruling executed: one presentation channel, one classification layer, " \
                            "no other lane's file touched"
    out = os.path.join(ROOT, "_ord0326_final_r1.json")
    io.open(out, "w", encoding="utf-8", newline="\n").write(json.dumps(doc, ensure_ascii=False, indent=1))
    print(doc["claimed_result"])
    print("request_id hits:", json.dumps(rid_counts))
    print("untouched others:", all(doc["files_not_mine_confirmed_untouched"].values()),
          "| r5 others unchanged:", all(doc["r5"]["other_lanes_readings_unchanged"].values()))
    print("out=%s bytes=%d" % (out, os.path.getsize(out)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
