"""Parameterised copy of `derive_ord0292_commander_r1.py` - the ELEVEN rules are byte-for-byte the same.

Why a new file instead of editing the original: the original is a cited instrument (its run is in the
ledger and in red-team's own discussion).  Re-pointing it at different blobs while leaving the published
正本 untouched is the rule "改判据不算产品 killer / 已发布件不覆盖".  Every judgement here is derived from
the fetched rows; nothing is taken from a lane's prose.  `--verifier` is optional because a fresh
generation may not have red team's derivation yet - its absence must not be read as a pass or a fail.

Control: run it once on the 0292 coordinates and require the same 7/7 that receipt r1 produced, then run
it on the new coordinates.  A ruler that only ever agrees with whoever last quoted it is not measuring.
"""
import argparse
import hashlib
import json
import sys
import urllib.request

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, ".")

REPO = "Canshu-King/CityNexus"


def token():
    from bus_new import token as t
    return t()


def blob(sha):
    body = None
    for _ in range(5):
        try:
            req = urllib.request.Request(f"https://api.github.com/repos/{REPO}/git/blobs/{sha}", headers={
                "Authorization": "Bearer " + token(), "Accept": "application/vnd.github+json",
                "User-Agent": "cmdr-arms-deriver"})
            with urllib.request.urlopen(req, timeout=120) as r:
                body = json.loads(r.read().decode())["content"]
            break
        except Exception:  # noqa: BLE001
            import time
            time.sleep(2)
    if body is None:
        raise SystemExit(f"could not fetch blob {sha} - refusing to guess")
    import base64
    raw = base64.b64decode(body)
    recomputed = hashlib.sha1(b"blob %d\x00" % len(raw) + raw).hexdigest()
    if recomputed != sha:
        raise SystemExit(f"BLOB MISMATCH for {sha} (recomputed {recomputed})")
    return raw


def red_nodes(att):
    nodes = (att or {}).get("nodes") or {}
    return sorted(k for k, v in nodes.items() if str(v).upper() == "RED")


def derive(arms, frozen):
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
            "triple_sha_is_frozen": tsha == frozen,
            "run_ids_distinct": base.get("runId") != att.get("runId"),
        }
        rows.append({"arm": a.get("name"), "derived_by_commander": "KILLED" if all(checks.values()) else "NOT_DERIVABLE",
                     "claimed_by_lane": a.get("claimed_result"), "red_observed_n": len(observed_red),
                     "failing_checks": [k for k, v in checks.items() if not v], "checks": checks})
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--order", required=True)
    ap.add_argument("--arms", required=True)
    ap.add_argument("--gate", required=True)
    ap.add_argument("--verifier")
    ap.add_argument("--frozen", required=True, help="40-hex sha the arms must name as their tested tree")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    if len(a.frozen) != 40:
        raise SystemExit("--frozen must be a full 40-hex coordinate, not a prefix")

    arms = json.loads(blob(a.arms).decode("utf-8"))
    gate = json.loads(blob(a.gate).decode("utf-8"))
    verifier = json.loads(blob(a.verifier).decode("utf-8")) if a.verifier else None
    rows = derive(arms, a.frozen)

    agree = all((r["derived_by_commander"] == "KILLED") == str(r["claimed_by_lane"]).startswith("KILLED") for r in rows)
    sizes = sorted({r["red_observed_n"] for r in rows})
    killed = sum(1 for r in rows if r["derived_by_commander"] == "KILLED")
    if verifier is not None:
        v_rows = (verifier.get("arms") or verifier.get("per_arm") or [])
        mine = {r["arm"]: r["derived_by_commander"] for r in rows}
        theirs = {}
        for v in v_rows if isinstance(v_rows, list) else []:
            if isinstance(v, dict):
                theirs[v.get("arm") or v.get("nodeid")] = str(v.get("derived_result") or v.get("verdict") or "")
        vs = [{"arm": k, "mine": mine[k], "verifier": theirs.get(k)} for k in sorted(mine)]
        verifier_agreement = sum(1 for x in vs if x["verifier"] and x["mine"] in x["verifier"].upper())
    else:
        vs, verifier_agreement = [], None

    out = {
        "order": a.order,
        "rederived_by": "commander 494abfd7 (independent of lane prose)",
        "instrument": "derive_arms_commander_r2.py (rules identical to derive_ord0292_commander_r1.py)",
        "inputs": {"arms_blob": a.arms, "gate_round_blob": a.gate, "verifier_derivation_blob": a.verifier,
                   "every_input_recomputed_to_its_own_cited_sha1": True},
        "frozen_tip": a.frozen,
        "arms_total": len(rows),
        "killed_by_commander": killed,
        "red_set_sizes": sizes,
        "lane_claims_agree_with_my_derivation": bool(agree),
        "arms_failing_any_check": [r["arm"] for r in rows if r["failing_checks"]],
        "per_arm": rows,
        "green_round": {"verdict": gate.get("verdict") or (gate.get("gate") or {}).get("verdict"),
                        "triples_named": len(gate.get("cells") or gate.get("triples") or []),
                        "problems": len(gate.get("problems") or [])},
        "verifier_comparison": {"present": verifier is not None, "rows": vs,
                                "mine_matching_verifier": verifier_agreement},
        "scope": "Candidate generation named in --frozen only. Per Q24/Q25 these do not transfer to any "
                 "other tip. This file states what MY derivation says; closure still needs the verifier's "
                 "derived_result (B-1), which is why `verifier_comparison.present` is reported, not assumed.",
    }
    json.dump(out, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, sort_keys=True, indent=1)
    print(a.order, "| arms", out["arms_total"], "| killed by me", killed, "| red sizes", sizes,
          "| claims agree", agree, "| verifier present", verifier is not None)
    for r in rows:
        print("  %-34s claimed=%-8s mine=%-12s failing: %s" % (r["arm"], r["claimed_by_lane"],
                                                               r["derived_by_commander"], r["failing_checks"] or "none"))
    print("wrote", a.out)
    return 0 if (killed == out["arms_total"] and agree) else 3


if __name__ == "__main__":
    raise SystemExit(main())
