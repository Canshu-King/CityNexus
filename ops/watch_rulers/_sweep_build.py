"""Build _q64_sweep_r1.json from the sweep artifacts.

Every count (files_scanned / hits_total / per_rule / classification tallies) is derived from the
ruler's own per-file JSON artifacts. Every basis line quoted for classification is extracted by line
number from the tip tree exported with `git archive`, so no evidence text is transcribed by hand.
"""
import io
import json
import os
import subprocess
import sys
import time

ROOT = "D:/moodle/_qoder_cmdr_ref_20260921/live_checks"
SCRATCH = os.path.join(ROOT, "_sweep_scratch")
TREE = os.path.join(SCRATCH, "tree")
REPO = "D:/moodle/CityNexus"
TIP = "30de4ebe409f49c5e25f4758cb2e5f4e90764a4f"
RULER_BLOB = "608016f6a538097041554b76cfe3e9a4192f299c"
BASELINE = {"path": "frontend/src/features/planning/PlanWithAiSheet.tsx",
            "blob": "3bb6a39067a380c2f75629fd7562f0de8f5d2f2a",
            "rule": "UPSTREAM_TEXT_VIA_HELPER_TO_DOM", "line": 1016,
            "chain_src": "serverReasonSentence", "chain_name": "failureReason"}
NEGCTL = "frontend/src/lib/money.ts"

# classification / (reaches, sinks, basis[(file,line)], why)  -- judgment authored by lane S1
CLS = {
 "frontend/src/app/V8Experience.tsx:320|RAW_BODY_TO_DOM": (
  "local_wording", "no_comment_never_renders",
  [], [("frontend/src/app/V8Experience.tsx", 320)],
  "The match is inside the JSDoc block at 317-326 that explains why UTC slicing was wrong. The "
  "pattern \\braw\\b.*\\bslice\\( fired on prose ABOUT code, not on code; nothing reaches the screen."),
 "frontend/src/app/V8Experience.tsx:833|UPSTREAM_READ_DIRECT": (
  "machine_label", "attribute_only",
  [],
  [("frontend/src/app/V8Experience.tsx", 831), ("frontend/src/app/V8Experience.tsx", 833),
   ("frontend/src/app/V8Experience.tsx", 830), ("frontend/src/features/setup/JourneyTrialSetup.tsx", 1247),
   ("frontend/src/features/setup/JourneyTrialSetup.tsx", 1248),
   ("frontend/src/features/setup/JourneyTrialSetup.tsx", 1250)],
  "error.message is parked in sealedDemoDetail state and reaches the DOM only as the "
  "data-error-message attribute (JourneyTrialSetup 1248). The sentence the traveller reads is the "
  "i18n key trial.sealedUnreadable (830, rendered at 1250). Provenance may carry upstream prose via "
  "rejectionReason, but the sink is an attribute, not text."),
 "frontend/src/app/V8Experience.tsx:1028|UPSTREAM_READ_DIRECT": (
  "upstream_prose", "yes",
  [], [("frontend/src/app/V8Experience.tsx", 1030), ("frontend/src/app/V8Experience.tsx", 1562),
       ("frontend/src/app/V8Experience.tsx", 169), ("frontend/src/app/V8Experience.tsx", 170),
       ("frontend/src/app/V8Experience.tsx", 172)],
  "setMessage(error.message); the throw site is v8RequestInner -> V8Rejection(rejectionReason(body,"
  "status)) and rejectionReason takes body.detail / body.error.message verbatim (169-171) plus the "
  "server validation msgs joined at 163. Rendered as text at 1562."),
 "frontend/src/components/ProductErrorBoundary.tsx:104|UPSTREAM_READ_DIRECT": (
  "upstream_prose", "yes",
  [], [("frontend/src/components/ProductErrorBoundary.tsx", 102),
       ("frontend/src/components/ProductErrorBoundary.tsx", 104),
       ("frontend/src/components/ProductErrorBoundary.tsx", 105)],
  "A pre with data-testid=error-detail renders String(error?.message || error) and React's info "
  "(the component stack) verbatim. The details fold is closed by default, but both strings are in "
  "the DOM the moment the boundary trips."),
 "frontend/src/features/agent/AgentComposer.tsx:95|UPSTREAM_READ_DIRECT": (
  "upstream_prose", "yes",
  [], [("frontend/src/features/agent/AgentComposer.tsx", 95),
       ("frontend/src/features/agent/AgentComposer.tsx", 196),
       ("frontend/src/api/citynexus.ts", 384), ("frontend/src/api/citynexus.ts", 908)],
  "response.message is CopilotResponse.message from POST /copilot/messages (citynexus.ts 384, 908) "
  "stored as the assistant bubble text and rendered in a p at 196. This is the designed content "
  "channel (a model answer), not an error string - flagged so the commander can rule it apart."),
 "frontend/src/features/agent/CopilotDock.tsx:615|UPSTREAM_READ_DIRECT": (
  "upstream_prose", "yes",
  [], [("frontend/src/features/agent/CopilotDock.tsx", 615),
       ("frontend/src/features/agent/CopilotDock.tsx", 743), ("frontend/src/api/citynexus.ts", 384)],
  "Same channel as AgentComposer: server assistant text stored as message text, rendered in a p at "
  "743. Designed content, not an error string."),
 "frontend/src/features/discovery/DestinationPreparationPanel.tsx:75|UPSTREAM_READ_DIRECT": (
  "local_wording", "yes",
  [], [("frontend/src/features/discovery/DestinationPreparationPanel.tsx", 78),
       ("frontend/src/api/citynexus.ts", 680), ("frontend/src/api/citynexus.ts", 684),
       ("frontend/src/features/discovery/DestinationPreparationPanel.tsx", 522)],
  "error.message here is the CityNexusApiError message composed locally at citynexus.ts 680-684 "
  "('CityNexus API ' + status + ': ' + path). The server body is kept on the error object and never "
  "rendered; the else branch of the ternary is this file's own sentence. Rendered at 522. Caveat: "
  "status code and request path do surface."),
 "frontend/src/features/discovery/DestinationPreparationPanel.tsx:99|UPSTREAM_READ_DIRECT": (
  "local_wording", "yes",
  [], [("frontend/src/features/discovery/DestinationPreparationPanel.tsx", 102),
       ("frontend/src/api/citynexus.ts", 680), ("frontend/src/api/citynexus.ts", 684),
       ("frontend/src/features/discovery/DestinationPreparationPanel.tsx", 346)],
  "Same provenance as :75 (locally composed CityNexus API message). Lands in capabilityError, "
  "rendered at 346. No server prose on this path."),
 "frontend/src/features/discovery/DestinationPreparationPanel.tsx:120|UPSTREAM_READ_DIRECT": (
  "local_wording", "yes",
  [], [("frontend/src/features/discovery/DestinationPreparationPanel.tsx", 122),
       ("frontend/src/api/citynexus.ts", 680), ("frontend/src/api/citynexus.ts", 684)],
  "Same provenance as :75: locally composed message plus this file's own zh fallback. actionError "
  "slot, rendered at 522."),
 "frontend/src/features/discovery/DestinationPreparationPanel.tsx:137|UPSTREAM_READ_DIRECT": (
  "local_wording", "yes",
  [], [("frontend/src/features/discovery/DestinationPreparationPanel.tsx", 139),
       ("frontend/src/api/citynexus.ts", 680), ("frontend/src/api/citynexus.ts", 684)],
  "Same provenance as :75: locally composed message plus this file's own zh fallback. actionError "
  "slot, rendered at 522."),
 "frontend/src/features/execution/LiveRecovery.tsx:234|UPSTREAM_READ_DIRECT": (
  "local_wording", "yes",
  [], [("frontend/src/features/execution/LiveRecovery.tsx", 237),
       ("frontend/src/features/execution/LiveRecovery.tsx", 238),
       ("frontend/src/features/execution/LiveRecovery.tsx", 240),
       ("frontend/src/features/execution/LiveRecovery.tsx", 68),
       ("frontend/src/features/execution/LiveRecovery.tsx", 90),
       ("frontend/src/features/execution/LiveRecovery.tsx", 91)],
  "raw does read body.error.message / body.detail (237-238), but it is passed through "
  "humanReplanReason (68), a four-code whitelist whose unmapped branch (90-93) returns this file's "
  "own sentence. The upstream string is used as a match key and never surfaces - the guard the "
  "ruling asks for is present here."),
 "frontend/src/features/inbox/JourneyInboxWorkbench.tsx:691|RAW_TEXT_INTERPOLATION": (
  "upstream_prose", "yes",
  [], [("frontend/src/features/inbox/JourneyInboxWorkbench.tsx", 688),
       ("frontend/src/features/inbox/JourneyInboxWorkbench.tsx", 691),
       ("frontend/src/features/inbox/JourneyInboxWorkbench.tsx", 474),
       ("frontend/src/features/inbox/JourneyInboxWorkbench.tsx", 460),
       ("frontend/src/features/inbox/JourneyInboxWorkbench.tsx", 88)],
  "rawDetail is set at 474 from failure, which 460 took off error.message, and this file's own "
  "requestJson throws new Error(payload.error?.message ?? payload.detail ?? ...) at 88 - the server "
  "sentence verbatim. Rendered inside a code element at 691 when the confirmation did not pass."),
 "frontend/src/features/inbox/JourneyInboxWorkbench.tsx:307|UPSTREAM_READ_DIRECT": (
  "upstream_prose", "yes",
  [], [("frontend/src/features/inbox/JourneyInboxWorkbench.tsx", 308),
       ("frontend/src/features/inbox/JourneyInboxWorkbench.tsx", 88),
       ("frontend/src/features/inbox/JourneyInboxWorkbench.tsx", 687)],
  "setMessage(error.message) where the only thrower on this path is this file's requestJson at 88, "
  "which embeds payload.error.message / payload.detail. Rendered in a role=status p at 687."),
 "frontend/src/features/inbox/JourneyInboxWorkbench.tsx:317|UPSTREAM_READ_DIRECT": (
  "upstream_prose", "yes",
  [], [("frontend/src/features/inbox/JourneyInboxWorkbench.tsx", 318),
       ("frontend/src/features/inbox/JourneyInboxWorkbench.tsx", 88),
       ("frontend/src/features/inbox/JourneyInboxWorkbench.tsx", 687)],
  "Same thrower (88) and same sink (687) as :307, on the loadMemory retry path."),
 "frontend/src/features/inbox/JourneyInboxWorkbench.tsx:336|UPSTREAM_READ_DIRECT": (
  "upstream_prose", "yes",
  [], [("frontend/src/features/inbox/JourneyInboxWorkbench.tsx", 339),
       ("frontend/src/features/inbox/JourneyInboxWorkbench.tsx", 88),
       ("frontend/src/features/inbox/JourneyInboxWorkbench.tsx", 731)],
  "setPendingError(error.message) from the same 88 thrower; pendingError is rendered in a code "
  "element at 731 inside the queue slot."),
 "frontend/src/features/inbox/JourneyInboxWorkbench.tsx:386|UPSTREAM_READ_DIRECT": (
  "upstream_prose", "yes",
  [], [("frontend/src/features/inbox/JourneyInboxWorkbench.tsx", 387),
       ("frontend/src/features/inbox/JourneyInboxWorkbench.tsx", 88),
       ("frontend/src/features/inbox/JourneyInboxWorkbench.tsx", 687)],
  "Text-intake failure: setMessage(error.message) from 88, rendered at 687."),
 "frontend/src/features/inbox/JourneyInboxWorkbench.tsx:407|UPSTREAM_READ_DIRECT": (
  "upstream_prose", "yes",
  [], [("frontend/src/features/inbox/JourneyInboxWorkbench.tsx", 408),
       ("frontend/src/features/inbox/JourneyInboxWorkbench.tsx", 88),
       ("frontend/src/features/inbox/JourneyInboxWorkbench.tsx", 687)],
  "Image-intake failure: setMessage(error.message) from 88, rendered at 687."),
 "frontend/src/features/inbox/JourneyInboxWorkbench.tsx:435|UPSTREAM_READ_DIRECT": (
  "upstream_prose", "yes",
  [], [("frontend/src/features/inbox/JourneyInboxWorkbench.tsx", 436),
       ("frontend/src/features/inbox/JourneyInboxWorkbench.tsx", 88),
       ("frontend/src/features/inbox/JourneyInboxWorkbench.tsx", 687)],
  "Smart-apply failure: setMessage(error.message) from 88, rendered at 687."),
 "frontend/src/features/inbox/JourneyInboxWorkbench.tsx:459|UPSTREAM_READ_DIRECT": (
  "upstream_prose", "yes",
  [], [("frontend/src/features/inbox/JourneyInboxWorkbench.tsx", 460),
       ("frontend/src/features/inbox/JourneyInboxWorkbench.tsx", 88),
       ("frontend/src/features/inbox/JourneyInboxWorkbench.tsx", 474),
       ("frontend/src/features/inbox/JourneyInboxWorkbench.tsx", 691)],
  "confirm(): failure = error.message from the 88 thrower, then 474 stores it in rawDetail and 691 "
  "renders it in a code element. The in-file comment at 466-467 states the intent explicitly: the "
  "raw server string is kept in the technical fold rather than paraphrased."),
 "frontend/src/features/inbox/JourneyInboxWorkbench.tsx:517|UPSTREAM_READ_DIRECT": (
  "upstream_prose", "yes",
  [], [("frontend/src/features/inbox/JourneyInboxWorkbench.tsx", 518),
       ("frontend/src/features/inbox/JourneyInboxWorkbench.tsx", 88),
       ("frontend/src/features/inbox/JourneyInboxWorkbench.tsx", 687)],
  "Corrections-save failure: setMessage(error.message) from 88, rendered at 687."),
 "frontend/src/features/planning/PlanComparison.tsx:92|UPSTREAM_READ_DIRECT": (
  "upstream_prose", "yes",
  [], [("frontend/src/features/planning/PlanComparison.tsx", 95),
       ("frontend/src/features/planning/PlanComparison.tsx", 96),
       ("frontend/src/features/planning/PlanComparison.tsx", 260)],
  "setError(body?.error?.message ?? body?.detail ?? local sentence) read straight off the parsed "
  "select response; error is rendered in a role=alert p at 260. Two-step-free direct upstream read."),
 "frontend/src/features/planning/PlanWithAiSheet.tsx:1016|UPSTREAM_TEXT_VIA_HELPER_TO_DOM": (
  "upstream_prose", "yes",
  [], [("frontend/src/features/planning/PlanWithAiSheet.tsx", 1016),
       ("frontend/src/features/planning/PlanWithAiSheet.tsx", 159),
       ("frontend/src/features/planning/PlanWithAiSheet.tsx", 161),
       ("frontend/src/features/planning/PlanWithAiSheet.tsx", 163),
       ("frontend/src/features/planning/PlanWithAiSheet.tsx", 1013)],
  "The named baseline cell. serverReasonSentence (159) returns error.message (161) or detail (163) "
  "verbatim - the in-file comment above it says so - and the value is rendered in a code element at "
  "1016. Line 1013 shows the local wording that is used only when the server sent no sentence."),
 "frontend/src/features/stay/HotelsPanel.tsx:91|UPSTREAM_READ_DIRECT": (
  "upstream_prose", "yes",
  [], [("frontend/src/features/stay/HotelsPanel.tsx", 93),
       ("frontend/src/features/stay/HotelsPanel.tsx", 104),
       ("frontend/src/features/stay/HotelsPanel.tsx", 229)],
  "raw = String(body?.error?.message ?? body?.detail ?? '') at 93. The conflict branch (97-103) is "
  "local wording, but the else branch at 104 renders raw itself when the code is not one of the two "
  "tested names, and error is shown in a role=alert p at 229. So the whitelist leaks on unmapped "
  "codes - the opposite of LiveRecovery's humanReplanReason."),
 "frontend/src/lib/failureAttribution.ts:160|UPSTREAM_READ_DIRECT": (
  "machine_label", "yes",
  [], [("frontend/src/lib/failureAttribution.ts", 160),
       ("frontend/src/lib/failureAttribution.ts", 92)],
  "The tokens that fired are error.content_type (an allowed field in the ruling's own list) and "
  "error.body_kind, which line 92 types as the closed enum html | not_json | empty. What is "
  "interpolated is a status/machine classification, not an upstream sentence."),
 "frontend/src/main.tsx:1066|UPSTREAM_EXCEPTION_TO_DOM": (
  "machine_label", "yes",
  [], [("frontend/src/main.tsx", 1066), ("frontend/src/main.tsx", 1049)],
  "The pattern fired on the word 'trace' inside a locally written label; what the interpolation at "
  "this line actually renders is agentRun.tool_steps.length, a count. See adjacent_findings: the "
  "server prose on this screen is on 1063-1064 and 1074-1075, which the ruler does not flag."),
}

ADJACENT = [
 ("frontend/src/main.tsx", 1063, "agentRun.outcome is a server column rendered in a p; ruler did not fire"),
 ("frontend/src/main.tsx", 1064, "agentRun.failure_reason is a server column rendered in a p; ruler did not fire"),
 ("frontend/src/main.tsx", 1074, "step.result.error tested for string-ness then rendered; server run record"),
 ("frontend/src/main.tsx", 1421, "item.explanation rendered with a local fallback; server field"),
 ("frontend/src/app/V8Experience.tsx", 1025, "locally written abort sentence (evidence that 1024-1026 is local_wording)"),
]


def read_line(tree_path, n):
    with io.open(tree_path, encoding="utf-8", errors="replace") as fh:
        lines = fh.read().splitlines()
    if not 1 <= n <= len(lines):
        raise SystemExit("BASIS_LINE_OUT_OF_RANGE %s:%d (%d lines)" % (tree_path, n, len(lines)))
    return lines[n - 1].strip()


def git(*a):
    r = subprocess.run(["git", "-C", REPO] + list(a), capture_output=True)
    if r.returncode:
        raise SystemExit("GIT_FAILED %s" % " ".join(a))
    return r.stdout.decode("utf-8", "replace").strip()


def main():
    agg = json.load(io.open(os.path.join(SCRATCH, "aggregate.json"), encoding="utf-8"))
    base = json.load(io.open(os.path.join(SCRATCH, "baseline_planwithai.json"), encoding="utf-8"))
    neg = json.load(io.open(os.path.join(SCRATCH, "negctl_money.json"), encoding="utf-8"))

    tip_now = git("ls-remote", "origin", "refs/heads/mirror/integration-frontend-apple-pass1").split()[0]
    ruler_remote = git("rev-parse", "origin/commander/control:"
                       "evidence/cmdr-ui-exposure-r2-0059/ui_exposure_field_check_r2.py")
    assert agg["ruler"] == ruler_remote == RULER_BLOB, "ruler blob drift"

    # (a) baseline reproduction, derived from the ruler artifact
    bh = base["hits"]
    baseline_ok = (len(bh) == 1 and bh[0]["rule"] == BASELINE["rule"] and bh[0]["line"] == BASELINE["line"]
                   and BASELINE["chain_src"] in bh[0]["taint_chain"]
                   and BASELINE["chain_name"] in bh[0]["taint_chain"])
    # (b) negative control
    neg_ok = (neg["verdict"] == "NO_EXPOSURE_SHAPE_FOUND" and len(neg["hits"]) == 0
              and neg["targets_scanned"] == ["%s:%s" % (TIP[:12], NEGCTL)])

    hits = []
    missing = []
    for h in agg["hits"]:
        key = "%s:%d|%s" % (h["path"], h["line"], h["rule"])
        if key not in CLS:
            missing.append(key)
            continue
        cls, reaches, _sinks, basis, why = CLS[key]
        hits.append({
            "file": h["path"], "blob": h["blob"], "line": h["line"], "rule": h["rule"],
            "taint_chain": h["taint_chain"], "snippet": h["snippet"],
            "classification": cls, "reaches_dom": reaches,
            "basis": [{"file": bf, "line": bn, "text": read_line(os.path.join(TREE, bf), bn)}
                      for bf, bn in basis],
            "why": why,
        })
    if missing:
        raise SystemExit("UNCLASSIFIED_HITS %s" % missing)

    tally = {}
    for x in hits:
        tally[x["classification"]] = tally.get(x["classification"], 0) + 1
    per_rule = {}
    for x in hits:
        per_rule[x["rule"]] = per_rule.get(x["rule"], 0) + 1

    doc = {
     "schema": "CNX_Q64_SWEEP_V1",
     "lane": "S1-q64sweep",
     "at_local": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
     "generation": TIP,
     "tip_moved": (tip_now != TIP),
     "tip_readback_now": tip_now,
     "ruler": RULER_BLOB,
     "ruler_route": "commander/control:evidence/cmdr-ui-exposure-r2-0059/ui_exposure_field_check_r2.py",
     "ruler_local_git_hash_object": subprocess.run(
        ["git", "hash-object", os.path.join(ROOT, "ui_exposure_field_check_r2.py")],
        capture_output=True, cwd=ROOT).stdout.decode().strip(),
     "scope": "frontend/src *.ts/*.tsx at the tip; node_modules / dist / frontend/node_modules excluded",
     "publish_route": "commander/control:evidence/q64-sweep-S1/sweep_r1.json",
     "self_reference_note": "this file cannot carry its own blob (a file's blob is computed over its bytes), so the "
                            "independent read-back number is published beside it at "
                            "commander/control:evidence/q64-sweep-S1/readback_proof_r1.json",
     "excluded_paths_named": ["node_modules", "dist", "frontend/node_modules (junction, untouched)"],
     "files_scanned": len(agg["files"]),
     "files_failed": agg["files_failed"],
     "bytes_scanned": agg["bytes_total"],
     "files_with_hits": len(set(x["file"] for x in hits)),
     "hits_total": len(hits),
     "per_rule": per_rule,
     "classification_tally": tally,
     "selftest": json.load(io.open(os.path.join(ROOT, "_sweep_selftest.json"), encoding="utf-8")),
     "baseline_expectation": BASELINE,
     "baseline_observed": {"n_hits": len(bh), "rule": bh[0]["rule"] if bh else None,
                           "line": bh[0]["line"] if bh else None,
                           "taint_chain": bh[0]["taint_chain"] if bh else None},
     "baseline_reproduced": bool(baseline_ok),
     "negative_control": {"file": NEGCTL, "verdict": neg["verdict"], "n_hits": len(neg["hits"]),
                          "why_chosen": "no fetch / XMLHttpRequest / axios / detail / body / message / resp "
                                        "token anywhere in it (grep -icE over git show at the tip = 0), and it "
                                        "is pure currency arithmetic"},
     "negative_control_clean": bool(neg_ok),
     "verdict": "SWEEP_VALID" if (baseline_ok and neg_ok) else "SWEEP_INVALID",
     "method": "ruler invoked once per file as a subprocess: python -X utf8 "
               "ui_exposure_field_check_r2.py --ref <tip> --path <tree path> --out <scratch json>. "
               "The ruler reads bytes via git show, so the product working tree was never the input and "
               "was never written. Aggregation reads only the ruler's own artifacts.",
     "instrument_notes": [
       "The ruler reports the line where its match OPENS, which for UPSTREAM_READ_DIRECT is often a "
       "block-brace (} catch (error) {, } else {, if (!r.ok) {) rather than the offending text. Every "
       "cell below therefore carries the real lines it read as basis, and the hit line is kept as the "
       "ruler's own anchor.",
       "1 hit (V8Experience.tsx:320) fired on a JSDoc comment, not on code.",
       "adjacent_findings are lines where server prose demonstrably reaches the DOM and the ruler does "
       "NOT fire. They are not counted in hits_total because hits_total is ruler-derived.",
     ],
     "adjacent_findings": [{"file": f, "line": n, "text": read_line(os.path.join(TREE, f), n), "note": t}
                           for f, n, t in ADJACENT],
     "hits": hits,
     "claim_kind": "pattern_determined",
     "claimed_result": None,
     "derived_result": None,
    }
    doc["claimed_result"] = ("%s: %d files scanned, %d hit(s) in %d file(s), classification %s"
                             % (doc["verdict"], doc["files_scanned"], doc["hits_total"],
                                doc["files_with_hits"], json.dumps(doc["classification_tally"])))
    if doc["verdict"] == "SWEEP_VALID":
        doc["derived_result"] = "Q64 r2 exposure inventory published for tip %s" % TIP[:12]
    out = os.path.join(ROOT, "_q64_sweep_r1.json")
    io.open(out, "w", encoding="utf-8", newline="\n").write(json.dumps(doc, ensure_ascii=False, indent=1))
    print("verdict=%s files_scanned=%d hits_total=%d files_with_hits=%d per_rule=%s tally=%s"
          % (doc["verdict"], doc["files_scanned"], doc["hits_total"], doc["files_with_hits"],
             json.dumps(per_rule, sort_keys=True), json.dumps(tally, sort_keys=True)))
    print("baseline_reproduced=%s negative_control_clean=%s tip_moved=%s at_local=%s"
          % (doc["baseline_reproduced"], doc["negative_control_clean"], doc["tip_moved"], doc["at_local"]))
    print("ruler=%s generation=%s" % (doc["ruler"], doc["generation"]))
    print("out=%s bytes=%d" % (out, os.path.getsize(out)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
