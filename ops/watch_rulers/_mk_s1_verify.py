"""Commander-side verification of lane S1's Q64 sweep: rebuild the numbers from my own scan, then check two of
her headline claims against the source lines. Written as a file because nested quotes inside `python -c` through
Git Bash keeps eating my literals."""
import io
import json
import time

GENERATION = "30de4ebe409f49c5e25f4758cb2e5f4e90764a4f"
R2 = "608016f6a538097041554b76cfe3e9a4192f299c"
R3 = "44e062e6ce9c7b5d97d78e09e432072da102292c"

# from my own run of the ruler binary over `git archive` of the generation (see the transcript of this run)
SCAN = {"files_scanned": 74, "hits_r2": 25, "hits_r3": 25, "files_with_hits": 12,
        "per_rule_r3": {"UPSTREAM_READ_DIRECT": 21, "UPSTREAM_TEXT_VIA_HELPER_TO_DOM": 1,
                        "RAW_BODY_TO_DOM": 1, "RAW_TEXT_INTERPOLATION": 1,
                        "UPSTREAM_EXCEPTION_TO_DOM": 1},
        "new_in_r3_vs_r2": 0, "lost_in_r3_vs_r2": 0}
S1 = {"files_scanned": 74, "files_with_hits": 12, "hits_total": 25, "upstream_prose": 16,
      "local_wording": 6, "machine_label": 3,
      "source": "S1-q64sweep_0254.md (ledger block) + evidence/q64-sweep-S1/sweep_r1.json"}


def lines_of(path, a, b):
    src = io.open(path, encoding="utf-8", errors="replace").read().split("\n")
    return [src[i - 1].strip()[:150] for i in range(a, b + 1)]


jiw = lines_of("_cmdr_sweep_r3/frontend/src/features/inbox/JourneyInboxWorkbench.tsx", 87, 89)
peb = lines_of("_cmdr_sweep_r3/frontend/src/components/ProductErrorBoundary.tsx", 103, 106)
checks = [
    {"claim": "JourneyInboxWorkbench.tsx:88 puts server body text into Error.message",
     "cite": "frontend/src/features/inbox/JourneyInboxWorkbench.tsx:87-89", "lines_read": jiw,
     "holds": any("payload.error?.message" in l and "payload.detail" in l for l in jiw)},
    {"claim": "ProductErrorBoundary.tsx:104 renders the error message and React's component stack into a <pre>",
     "cite": "frontend/src/components/ProductErrorBoundary.tsx:103-106", "lines_read": peb,
     "holds": any("String(error?.message" in l for l in peb) and any("info" in l for l in peb)},
]
out = {
    "schema": "CNX_CMDR_S1_SWEEP_VERIFICATION_V1", "lane": "commander 494abfd7",
    "at_local": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "generation": GENERATION,
    "rulers": {"r2": R2, "r3": R3},
    "method": "git archive <generation> frontend/src | tar -x into a commander-private scratch dir, then the ruler "
              "binary itself per 20-file chunk via --file --out; no imports, no rewritten regex, product tree "
              "never touched",
    "independent_scan": {"files_scanned": SCAN["files_scanned"], "hits_r2": SCAN["hits_r2"],
                         "hits_r3": SCAN["hits_r3"], "files_with_hits": SCAN["files_with_hits"],
                         "per_rule_r3": SCAN["per_rule_r3"], "new_in_r3_vs_r2": SCAN["new_in_r3_vs_r2"],
                         "lost_in_r3_vs_r2": SCAN["lost_in_r3_vs_r2"]},
    "s1_reported": S1, "spot_checks": checks,
    "derived": {
        "counts_match_s1": (SCAN["hits_r2"] == S1["hits_total"]
                           and SCAN["files_scanned"] == S1["files_scanned"]
                           and SCAN["files_with_hits"] == S1["files_with_hits"]),
        "classification_sums_to_hits": (S1["upstream_prose"] + S1["local_wording"] + S1["machine_label"]
                                        == S1["hits_total"]),
        "per_rule_sums_to_hits": sum(SCAN["per_rule_r3"].values()) == SCAN["hits_r3"],
        "r3_adds_nothing_on_live_tree": SCAN["hits_r3"] == SCAN["hits_r2"] and SCAN["new_in_r3_vs_r2"] == 0,
        "both_spot_claims_hold": all(c["holds"] for c in checks)},
    "verdict": None, "claim_kind": "recomputation", "claimed_result": None, "derived_result": None,
}
d = out["derived"]
out["verdict"] = "S1_SWEEP_VERIFIED" if all(d.values()) else "S1_SWEEP_MISMATCH"
out["claimed_result"] = ("commander re-scan: %d files / %d hits (r2) / %d hits (r3) / %d files with hits; "
                         "S1 totals equal mine=%s; spot claims hold=%s; verdict=%s"
                         % (SCAN["files_scanned"], SCAN["hits_r2"], SCAN["hits_r3"], SCAN["files_with_hits"],
                            d["counts_match_s1"], d["both_spot_claims_hold"], out["verdict"]))
io.open("_s1_verify.json", "w", encoding="utf-8", newline="\n").write(json.dumps(out, ensure_ascii=False, indent=1))
print(json.dumps(d, ensure_ascii=False))
print(out["claimed_result"])
