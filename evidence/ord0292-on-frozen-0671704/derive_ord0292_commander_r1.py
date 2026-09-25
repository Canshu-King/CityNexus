"""Commander's independent re-derivation of the ORD-0292 arm verdicts.

Inputs are the two PUBLISHED artifacts (read by 40-hex blob and re-hashed here); nothing in the
verdicts below is copied from either lane's prose -- each is recomputed from the arm's own fields.
Rules (mine, matching what I asked for):
  baseline exitCode == 0; attempt exitCode != 0; stack started; no missing nodes;
  owner node GREEN in baseline and RED in attempt; redSet == the nodes actually RED in the attempt run;
  anchor_hits >= 1; restored_exact; triple.exact_sha == the frozen tip; runIds distinct per arm.
"""
import hashlib
import json
import sys
import urllib.request

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, ".")
from bus_new import token  # noqa: E402

REPO = "Canshu-King/CityNexus"
ARMS_BLOB = "cb9270671adc323ff2816d406739e04518b9d05f"
GATE_BLOB = "0160e8db0295e600b44a5e5ff021d5da507bc7d2"
DERIV_BLOB = "7fa7946a4f154aadf5fbc5132374640129440cb7"
FROZEN = "0671704546f9c9ea1d1b57627b059124c7800803"
OUT = "receipts/ord0292_commander_rederivation_r1.json"


def blob(sha):
    req = urllib.request.Request("https://api.github.com/repos/%s/git/blobs/%s" % (REPO, sha),
                                 headers={"Authorization": "Bearer " + token(),
                                          "Accept": "application/vnd.github+json",
                                          "User-Agent": "commander-rederive"})
    import base64
    body = base64.b64decode(json.load(urllib.request.urlopen(req, timeout=120))["content"])
    recomputed = hashlib.sha1(b"blob %d\x00" % len(body) + body).hexdigest()
    if recomputed != sha:
        raise SystemExit("BLOB MISMATCH for %s (recomputed %s)" % (sha, recomputed))
    return body


def red_nodes(run):
    return sorted([n for n, v in (run.get("nodes") or {}).items() if str(v).upper() == "RED"])


def main():
    arms = json.loads(blob(ARMS_BLOB).decode("utf-8"))
    gate = json.loads(blob(GATE_BLOB).decode("utf-8"))
    e_verdicts = json.loads(blob(DERIV_BLOB).decode("utf-8"))
    rows = []
    for a in arms["arms"]:
        base, att = a["baseline"], a["attempt"]
        owner = a["ownerNode"]
        observed_red = red_nodes(att)
        claimed_red = sorted(x for x in (a.get("redSet") or []))
        triple = a.get("triple") or {}
        tsha = triple.get("exact_sha") if isinstance(triple, dict) else (triple[0] if isinstance(triple, list) else None)
        checks = {
            "baseline_exitCode_zero": base.get("exitCode") == 0,
            "attempt_exitCode_nonzero": att.get("exitCode") not in (0, None),
            "both_stacks_started": bool(base.get("stackStarted")) and bool(att.get("stackStarted")),
            "no_missing_nodes": not base.get("missingNodes") and not att.get("missingNodes"),
            "owner_green_in_baseline": str((base.get("nodes") or {}).get(owner, "")).upper() == "GREEN",
            "owner_red_in_attempt": str((att.get("nodes") or {}).get(owner, "")).upper() == "RED",
            "redSet_equals_observed": claimed_red == observed_red,
            "anchor_hits_ge_1": (a.get("anchor_hits") or 0) >= 1,
            "restored_exact": a.get("restored_exact") is True,
            "triple_sha_is_frozen": tsha == FROZEN,
            "run_ids_distinct": base.get("runId") != att.get("runId"),
        }
        derived = "KILLED" if all(checks.values()) else "NOT_DERIVABLE"
        rows.append({"arm": a.get("name"), "derived_by_commander": derived,
                     "claimed_by_lane": a.get("claimed_result"),
                     "red_observed_n": len(observed_red), "checks": checks})
    run_ids = [r["arm"] for r in rows if not all(r["checks"].values())]
    agree = all((r["derived_by_commander"] == "KILLED") == str(r["claimed_by_lane"]).startswith("KILLED") for r in rows)
    comp = [r["red_observed_n"] for r in rows]
    result = {
        "order": "ORD-0292", "rederived_by": "commander 494abfd7 (independent of lane prose)",
        "inputs": {"arms_blob": ARMS_BLOB, "gate_round_blob": GATE_BLOB, "verifier_derivation_blob": DERIV_BLOB,
                   "all_three_recomputed_sha1_equal": True},
        "frozen_tip": FROZEN, "arms": rows, "arms_total": len(rows),
        "killed_by_commander": sum(1 for r in rows if r["derived_by_commander"] == "KILLED"),
        "red_set_sizes": sorted(set(comp)),
        "lane_claims_agree_with_my_derivation": bool(agree),
        "arms_failing_any_check": run_ids,
        "green_round": {"verdict": (gate.get("verdict") or gate.get("gate", {}).get("verdict")),
                        "triples_named": len(gate.get("cells", gate.get("triples", {})) or {}),
                        "problems": len(gate.get("problems", []) or [])},
        "generation_scope": "candidate generation %s only -- per Q24/Q25 these do NOT transfer to the landed "
                             "tip 5c4608ce; ORD-0298 (lane D re-parent + rerun) is the path" % FROZEN[:12],
        "independent_evidence_counting": "4 exclusive K278 arms + 1 compound K253 cut-set (3 arms red on the "
                                         "same 3-node spec) = 5 pieces of evidence, not 7",
    }
    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        json.dump(result, f, ensure_ascii=False, sort_keys=True, indent=1)
    print("arms", result["arms_total"], "| killed by my own derivation", result["killed_by_commander"],
          "| red-set sizes", result["red_set_sizes"], "| claims agree", result["lane_claims_agree_with_my_derivation"])
    for r in rows:
        bad = [k for k, v in r["checks"].items() if not v]
        print("  %-32s claimed=%-8s mine=%-12s failing checks: %s" % (r["arm"], r["claimed_by_lane"],
                                                                       r["derived_by_commander"], bad or "none"))
    print("wrote", OUT, len(json.dumps(result)), "B json")
    return 0 if result["killed_by_commander"] == result["arms_total"] and agree else 3


sys.exit(main())
