"""ORD-0326 re-cut receipt: the two agent files, the r5 both-directions proof, and the field-arrival
table that ORD-0332 should be built on.

Every cited line is re-read from the tip export (frontend) or `git show <tip>:backend/app/main.py`
(server) and its text carried along, so a claim about where a field comes from is checkable without
trusting this file's prose.
"""
import io
import json
import os
import subprocess
import sys
import time

ROOT = "D:/moodle/_qoder_cmdr_ref_20260921/live_checks"
SCRATCH = os.path.join(ROOT, "_sweep_scratch")
REPO = "D:/moodle/CityNexus"
TREE = os.path.join(SCRATCH, "tip_tree", "frontend", "src")
TIP = "0f8b925facabc9df57bab600b86d999dd515bf94"
BRANCH = "agent/S1-q64sweep-candidates-r3"
BRANCH_SHA = "08a651e7fc25cf1ccaa0617e97a313b45aad3066"
R5 = "ff98091cf3accb0d836ae25ba49820170b92d932"


def git(*a):
    r = subprocess.run(["git", "-C", REPO] + list(a), capture_output=True)
    if r.returncode:
        raise SystemExit("GIT_FAILED %s %s" % (" ".join(a), r.stderr.decode("utf-8", "replace")[:160]))
    return r.stdout.decode("utf-8", "replace").strip()


def fe(rel, n):
    lines = io.open(os.path.join(TREE, rel), encoding="utf-8", errors="replace").read().splitlines()
    return lines[n - 1].strip()


def be(n):
    lines = io.open(os.path.join(SCRATCH, "backend_main.py"), encoding="utf-8", errors="replace").read().splitlines()
    return lines[n - 1].strip()


def cite(kind, where, n):
    return {"kind": kind, "where": where, "line": n,
            "text": (be(n) if kind == "backend" else fe(where, n))}


FIELDS = [
 {"field": "http_status",
  "verdict": "EMITTED",
  "produced_by": [("backend", "backend/app/main.py", 492)],
  "read_by_client": [("frontend", "api/citynexus.ts", 681), ("frontend", "api/citynexus.ts", 689)],
  "channel_key": [("frontend", "lib/failureAttribution.ts", 57), ("frontend", "lib/failureAttribution.ts", 123)],
  "on_screen_via": [("frontend", "lib/failureAttribution.ts", 358), ("frontend", "lib/failureAttribution.ts", 133)],
  "note": "the status is the HTTP status line, not a body key; it reaches the traveller inside "
          "copyFor's device sentence and inside Attribution.telemetry"},
 {"field": "content_type",
  "verdict": "EMITTED_BUT_ONLY_READ_ON_ONE_LEG",
  "produced_by": [("backend", "backend/app/main.py", 492)],
  "read_by_client": [("frontend", "api/citynexus.ts", 687)],
  "channel_key": [("frontend", "lib/failureAttribution.ts", 68)],
  "on_screen_via": [("frontend", "lib/failureAttribution.ts", 378)],
  "note": "the client reads the header only inside the guard at api/citynexus.ts:686 "
          "(parse failed, or a 2xx with no bytes). A plain 4xx with a valid JSON body never reads it, "
          "so Attribution.content_type stays undefined on that leg and the telemetry line omits the "
          "key rather than showing an empty one"},
 {"field": "body_bytes",
  "verdict": "NOT_EMITTED_ANYWHERE",
  "produced_by": [],
  "read_by_client": [],
  "channel_key": [],
  "on_screen_via": [],
  "note": "the only place a byte count could exist is api/citynexus.ts:663, which reads the whole body "
          "as text and then throws the length away. The server never sends one. Requiring this field on "
          "screen today asks the product to state a number nobody measured"},
 {"field": "response_received",
  "verdict": "NOT_EMITTED_AS_A_FIELD_ALREADY_COVERED_UNDER_ANOTHER_NAME",
  "produced_by": [],
  "read_by_client": [],
  "channel_key": [("frontend", "lib/failureAttribution.ts", 42)],
  "on_screen_via": [("frontend", "lib/failureAttribution.ts", 132)],
  "note": "the existing channel encodes the same fact as evidence_kind = HTTP_RESPONSE | TRANSPORT "
          "(and HEALTH_PROBE). Adding a boolean that duplicates it would widen Attribution for no new "
          "information - that is a semantics change and per the order I report it instead of doing it"},
 {"field": "elapsed_ms",
  "verdict": "NOT_EMITTED_ON_THIS_PATH",
  "produced_by": [],
  "read_by_client": [],
  "channel_key": [],
  "on_screen_via": [],
  "note": "the name does exist in the codebase at api/citynexus.ts:730, but it belongs to the execution-"
          "clock payload, not to a copilot failure, and the comment at api/citynexus.ts:757 records that "
          "the backend refuses to invent that denominator. Nothing times the copilot request today"},
 {"field": "request_id",
  "verdict": "NOT_EMITTED",
  "produced_by": [("backend", "backend/app/main.py", 487), ("backend", "backend/app/main.py", 456)],
  "read_by_client": [],
  "channel_key": [],
  "on_screen_via": [],
  "note": "lane B's measurement reproduces: request_id appears 0 times in backend/app/main.py, and there "
          "is no X-Request-Id header and no middleware that adds one (0 hits for request-id/middleware in "
          "the whole file). The server does mint an id for every refusal - error.trace_id, produced by "
          "trace_id() - but the client never reads it and the channel has no slot for it. ORD-0332's real "
          "question is therefore not 'emit request_id' but 'expose the trace_id that already exists, under "
          "which name'"},
]


def main():
    backend_lines = io.open(os.path.join(SCRATCH, "backend_main.py"),
                            encoding="utf-8", errors="replace").read().splitlines()
    rid_hits = sum(1 for l in backend_lines if "request_id" in l)
    hdr_hits = sum(1 for l in backend_lines
                   if "x-request-id" in l.lower() or "middleware" in l)
    tip_now = git("ls-remote", "origin", "refs/heads/mirror/integration-frontend-apple-pass1").split()[0]
    clean = json.load(io.open(os.path.join(SCRATCH, "r5_r3_clean.json"), encoding="utf-8"))
    mutant = json.load(io.open(os.path.join(SCRATCH, "r5_r3_mutant.json"), encoding="utf-8"))
    at_tip = json.load(io.open(os.path.join(SCRATCH, "r5_tree_tip.json"), encoding="utf-8"))
    touched = git("diff", "--name-only", TIP, BRANCH_SHA).split()
    doc = {
     "schema": "CNX_ORD0326_AGENT_AND_FIELDS_V1",
     "order": "ORD-0326",
     "lane": "S1-q64sweep",
     "at_local": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
     "generation": TIP,
     "authoritative_tip_now": tip_now,
     "tip_moved_after_my_measurement": tip_now != TIP,
     "branch_off_sha_ordered": TIP,
     "candidate_branch": BRANCH,
     "candidate_tip": BRANCH_SHA,
     "candidate_verified_by_ls_remote": git("ls-remote", "origin", "refs/heads/" + BRANCH).split()[0],
     "branch_is_off_the_ordered_sha": git("merge-base", "--is-ancestor", TIP, BRANCH_SHA) == "",
     "files_touched": touched,
     "no_new_lib_module": not any(f.startswith("frontend/src/lib/") or f.startswith("frontend/src/components/")
                                  for f in touched),
     "yielded_files_confirmed_untouched": {
        f: (git("diff", "--name-only", TIP, BRANCH_SHA).count(f) == 0)
        for f in ["frontend/src/features/inbox/JourneyInboxWorkbench.tsx",
                  "frontend/src/components/ProductErrorBoundary.tsx",
                  "frontend/src/features/stay/HotelsPanel.tsx",
                  "frontend/src/app/V8Experience.tsx",
                  "frontend/src/features/planning/PlanWithAiSheet.tsx",
                  "frontend/src/features/planning/PlanComparison.tsx"]},
     "ruler": R5,
     "ruler_mode": "--tree over git archive exports of the tip and of the candidate tree",
     "r5_readings": {"at_tip": len(at_tip["hits"]), "with_my_change": len(clean["hits"]),
                     "sinks_removed": sorted("%s:%d" % (h["file"].split("/")[-1], h["line"])
                                             for h in at_tip["hits"]
                                             if (h["file"], h["line"]) not in
                                             {(x["file"], x["line"]) for x in clean["hits"]}),
                     "anything_added": sorted("%s:%d" % (h["file"].split("/")[-1], h["line"])
                                              for h in clean["hits"]
                                              if (h["file"], h["line"]) not in
                                              {(x["file"], x["line"]) for x in at_tip["hits"]})},
     "two_direction_proof": {
        "clean": "r5 on the candidate tree: agent files flagged = 0",
        "mutant": "restoring `cause.message` at the CopilotDock send site re-flags the render sink",
        "mutant_hits": len(mutant["hits"]),
        "mutant_reflag": ["%s:%d|%s" % (h["file"].split("/")[-1], h["line"], h["rule"])
                          for h in mutant["hits"]
                          if h["file"].endswith("CopilotDock.tsx")],
        "note": "the mutant was applied to a scratch copy of the tree, never to the branch",
     },
     "verification": {
        "tsc": "node node_modules/typescript/bin/tsc -p tsconfig.typecheck.json --noEmit -> exit 0",
        "existing_assertions_untouched": "no existing spec file was edited; no skip/fixme added",
        "authoritative_pushes": 0,
     },
     "field_arrival_table_copilot_path": {
        "route_as_it_actually_is": "POST /api/v1/journeys/{journey_id}/copilot/messages",
        "route_as_written_in_the_order": "/copilot/message (singular) - the handler is plural at "
                                         "backend/app/main.py:11046, so an ORD-0332 cite should use the "
                                         "plural or it will not find the code",
        "request_id_hits_in_main_py": rid_hits,
        "request_id_header_or_middleware_hits": hdr_hits,
        "backend_lines_scanned": len(backend_lines),
        "fields": [{**f, "citations": [cite(k, w, n) for k, w, n in
                                       f["produced_by"] + f["read_by_client"] + f["channel_key"] +
                                       f["on_screen_via"]]} for f in FIELDS],
        "summary": None,
     },
     "claim_kind": "code_landed_plus_field_measurement",
     "claimed_result": None, "derived_result": None,
    }
    summ = {}
    for f in doc["field_arrival_table_copilot_path"]["fields"]:
        summ[f["verdict"]] = summ.get(f["verdict"], 0) + 1
    doc["field_arrival_table_copilot_path"]["summary"] = summ
    doc["claimed_result"] = ("%s @ %s: %d files, r5 %d -> %d (%d agent sinks removed, %d added), tsc 0, "
                             "of the six allowed fields %s"
                             % (BRANCH, BRANCH_SHA[:12], len(touched), len(at_tip["hits"]),
                                len(clean["hits"]), len(doc["r5_readings"]["sinks_removed"]),
                                len(doc["r5_readings"]["anything_added"]), json.dumps(summ, sort_keys=True)))
    doc["derived_result"] = ("the two assigned agent files are clean under r5 in both directions; three of "
                             "the six allowed fields cannot be shown at all today, so ORD-0332 is the "
                             "order that decides whether they get produced")
    out = os.path.join(ROOT, "_ord0326_agent_fields_r1.json")
    io.open(out, "w", encoding="utf-8", newline="\n").write(json.dumps(doc, ensure_ascii=False, indent=1))
    print(doc["claimed_result"])
    print("files:", touched)
    print("sinks removed:", doc["r5_readings"]["sinks_removed"])
    print("yielded untouched:", all(doc["yielded_files_confirmed_untouched"].values()),
          doc["yielded_files_confirmed_untouched"])
    print("out=%s bytes=%d" % (out, os.path.getsize(out)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
