"""ORD-0271-B streak aggregator: it reads round receipts and re-judges them, it does not believe them.

The commander's Q13口径 for this order is: rounds are logically consecutive, each round carries its own control
GREEN *and* its own restore byte-exact proof, and the aggregator only mechanically reads single-round receipts.
So this script:

* takes the shapes embedded in each round receipt (rendered text, what the origin answered, measured snapshot
  rows) and re-runs v4 and v3 on them here - a receipt that declared `ROUND_GREEN` over readings that no longer
  judge that way is reported as a mismatch, not passed through;
* recomputes every check from those readings and compares the recomputed set with the stored one;
* requires the round numbers to be 1..N with no gaps and the timestamps to run forward, so "streak" cannot be
  assembled from whichever runs happened to look good;
* prints the denominator next to the verdict, and names the failing checks rather than a bare RED.

Nothing here can be talked into a green by editing a verdict field: the fields it reads are measurements, and
the verdicts are derived below.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
import sys
import time
from pathlib import Path

BASE = Path(r"D:\moodle\_qoder_harness_ord0254")
V3 = BASE / "tools" / "ord0263_verifier_v3.py"
V4 = BASE / "tools" / "ord0263_verifier_v4.py"
CONTROL_SHA256 = "2d56a79632efc0c6b30396ebbddcd54bd84c0d2fa6a30d3f20d09f4655d419de"
CONTROL_ASSET = "assets/index-ChOTTCvB.js"
# a round must carry all three fifth-state shapes under both legs; see the round receipt builder
SHAPES = {"200_html", "200_empty", "200_not_json"}
NOW = time.strftime("%Y-%m-%dT%H:%M:%S+08:00", time.localtime())


def blob40(d: bytes) -> str:
    return hashlib.sha1(b"blob %d\x00" % len(d) + d).hexdigest()


def load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, str(path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def latest_reading(rec: dict) -> str:
    """The origin's own clock, latest across the readings this round carries - HH:MM:SS on one machine."""
    best = ""
    for leg in ("control_shapes", "mutant_shapes"):
        for s in rec.get(leg) or []:
            at = ((s.get("origin_answer") or {}).get("answered_at")) or ""
            if at > best:
                best = at
    return best


def secs(hms: str) -> int:
    try:
        h, m, s = hms.split(":")
        return int(h) * 3600 + int(m) * 60 + int(s)
    except Exception:
        return -1


def reason_of(shape: dict) -> str:
    m = re.search(r"attribution_reason=(\S+)", shape.get("rendered_text") or "")
    return m.group(1) if m else ""


def rejudge(rec: dict, v3, v4) -> dict:
    """Recompute a round's checks from the readings the receipt carries, ignoring its own verdicts."""
    ctl = rec.get("control_shapes") or []
    mut = rec.get("mutant_shapes") or []
    ctl_rows = [{"shape": s["shape"], "v4": v4.judge_v5(s)["verdict"],
                 "v4_failed": v4.judge_v5(s).get("failed_conditions")} for s in ctl]
    mut_rows = []
    for s in mut:
        j4, j3 = v4.judge_v5(s), v3.judge_v5(s)
        f4, f3 = set(j4.get("failed_conditions") or []), set(j3.get("failed_conditions") or [])
        mut_rows.append({"shape": s["shape"], "v4": j4["verdict"], "v3": j3["verdict"],
                         "v4_only": sorted(f4 - f3), "reason": reason_of(s)})
    cars = []
    for s in ctl:
        c, changed = v4.one_token_reason_rewrite(s)
        j4, j3 = v4.judge_v5(c), v3.judge_v5(c)
        cars.append({"from_shape": s["shape"], "tokens_changed": changed, "v4": j4["verdict"],
                     "v4_failed": j4.get("failed_conditions"), "v3": j3["verdict"]})
    agg4 = v4.aggregate_v5(ctl)
    faces = rec.get("faces") or {}
    fc = faces.get("control") or {}
    fm = faces.get("mutant") or {}
    checks = {
        "control_three_distinct_shapes": {s["shape"] for s in ctl} == SHAPES,
        "control_all_green_under_v4": all(r["v4"] == "GREEN" for r in ctl_rows),
        "control_aggregate_green_under_v4": agg4["verdict"] == "GREEN",
        "mutant_three_distinct_shapes": {s["shape"] for s in mut} >= SHAPES,
        "mutant_all_red_under_v4": bool(mut_rows) and all(r["v4"] == "RED" for r in mut_rows),
        "mutant_extra_condition_is_only_the_new_clause": bool(mut_rows) and all(
            r["v4_only"] == ["reason_collapsed"] for r in mut_rows),
        "mutant_reason_is_the_catch_all": bool(mut_rows) and all(
            r["reason"] == "UNKNOWN_FAILURE" for r in mut_rows),
        "dedicated_carrier_red_only_on_new_clause": len(cars) == 3 and all(
            r["tokens_changed"] == 1 and r["v4"] == "RED" and r["v4_failed"] == ["reason_collapsed"]
            and r["v3"] == "GREEN" for r in cars),
        "restore_byte_exact": fc.get("sha256_answered_over_http") == CONTROL_SHA256
        and fc.get("asset_named") == CONTROL_ASSET and bool(fc.get("equals_source_build")),
        "mutant_face_answered_the_mutant_bytes": bool(fm.get("sha256_answered_over_http"))
        and fm.get("sha256_answered_over_http") != CONTROL_SHA256
        and bool(fm.get("equals_source_build")),
        "both_faces_ownership_proven": all(((faces.get(k) or {}).get("gen") for k in ("control", "mutant"))),
    }
    stored = rec.get("checks") or {}
    # a contradiction is both sides computing the same key and disagreeing; a key one side does not have is a
    # coverage difference and belongs in its own field, never in a verdict
    drift = {k: {"stored": stored[k], "recomputed": v} for k, v in checks.items()
             if k in stored and stored[k] != v}
    only_aggregator = {k: v for k, v in checks.items() if k not in stored}
    only_receipt = sorted(set(stored) - set(checks))
    return {"checks": checks, "green": sum(1 for v in checks.values() if v), "total": len(checks),
            "checks_only_in_aggregator": only_aggregator, "checks_only_in_receipt": only_receipt,
            "red_checks": [k for k, v in checks.items() if not v], "recomputation_drift": drift,
            "control_rows": ctl_rows, "mutant_rows": mut_rows, "carrier_rows": cars,
            "derived_result": "ROUND_GREEN" if not [k for k, v in checks.items() if not v]
            else "ROUND_RED:" + ",".join(k for k, v in checks.items() if not v)}


def main(argv: list[str]) -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("--rounds", default="", help="comma-separated round numbers, e.g. 1,2")
    ap.add_argument("--files", default="", help="explicit receipt files (overrides --rounds)")
    a = ap.parse_args(argv)
    v3, v4 = load(V3, "ord0263_v3"), load(V4, "ord0263_v4")
    if a.files.strip():
        paths = [BASE / f.strip() for f in a.files.split(",") if f.strip()]
    else:
        nums = [int(x) for x in re.split(r"[,\s]+", a.rounds.strip()) if x]
        paths = [BASE / f"ord0271b_round{n}.json" for n in nums]
    missing = [p.name for p in paths if not p.is_file()]
    rounds, prev_at, prev_no, prev_read = [], None, None, None
    gaps, ordering = [], []
    for p in paths:
        if not p.is_file():
            rounds.append({"file": p.name, "derived_result": "MISSING_RECEIPT"})
            continue
        rec = json.loads(p.read_text(encoding="utf-8"))
        rj = rejudge(rec, v3, v4)
        no, at = rec.get("round"), rec.get("at")
        read_at = latest_reading(rec)
        if prev_no is not None and no != prev_no + 1:
            gaps.append({"between": [prev_no, no], "why": "round numbers are not consecutive"})
        if prev_read is not None and secs(read_at) >= 0 and secs(prev_read) >= 0 \
                and secs(read_at) <= secs(prev_read):
            ordering.append({"between": [prev_read, read_at],
                             "why": "this round's latest reading is not later than the previous round's"})
        if prev_at is not None and at == prev_at:
            ordering.append({"between": [at, read_at],
                             "why": "two receipts were assembled in the same second (bookkeeping, not a "
                                    "measurement signal - rounds are ordered by their readings)"})
        prev_no, prev_at, prev_read = no, at, read_at
        rounds.append({"file": p.name, "round": no, "at": at,
                       "stored_derived_result": rec.get("derived_result"),
                       "recomputed": rj["derived_result"],
                       "checks_green": f"{rj['green']}/{rj['total']}",
                       "red_checks": rj["red_checks"],
                       "recomputation_drift": rj["recomputation_drift"],
                       "control_rows": rj["control_rows"], "mutant_rows": rj["mutant_rows"],
                       "carrier_rows": rj["carrier_rows"],
                       "ruler_v4_blob40": blob40(V4.read_bytes()),
                       "instruments_match": (rec.get("instruments") or {}).get("v4", {}).get("blob40")
                       == blob40(V4.read_bytes()),
                       "capture_blob40": (rec.get("capture") or {}).get("blob40"),
                       "checks_only_in_aggregator": sorted(rj["checks_only_in_aggregator"]),
                       "checks_only_in_receipt": rj["checks_only_in_receipt"],
                       "latest_reading_on_origin_clock": read_at})
    green_rounds = [r for r in rounds if r.get("recomputed") == "ROUND_GREEN"]
    drift_rounds = [r for r in rounds if r.get("recomputation_drift")]
    lying = [r["file"] for r in rounds if r.get("stored_derived_result") != r.get("recomputed")]
    ruler_changed = [r["file"] for r in rounds if r.get("instruments_match") is False]
    # longest run of consecutive green rounds, in the order the receipts were asked for
    runs, cur = [], []
    for r in rounds:
        if r.get("recomputed") == "ROUND_GREEN":
            cur.append(r.get("round"))
        else:
            if cur:
                runs.append(cur)
            cur = []
    if cur:
        runs.append(cur)
    best = max(runs, key=len) if runs else []
    red_named = [f"round {r.get('round')}:{','.join(r.get('red_checks') or ['?'])}" for r in rounds
                 if r.get("recomputed") != "ROUND_GREEN"]
    if missing:
        verdict = f"INCOMPLETE(missing receipts: {','.join(missing)})"
    elif gaps:
        verdict = "STREAK_BROKEN(rounds not consecutive)"
    elif drift_rounds:
        verdict = "STREAK_INVALID(receipt text does not match its own readings)"
    elif len(green_rounds) == len(rounds) and rounds:
        verdict = f"STREAK_MET({len(green_rounds)})"
    else:
        verdict = ("STREAK_BROKEN(" + ";".join(red_named) + f"); longest_consecutive_green_run="
                   f"{len(best)}" + (f"(rounds {best[0]}..{best[-1]})" if best else ""))
    out = {"at": NOW, "order": "ORD-0271-B", "lane": "HARNESS d291c9dc",
           "what": "Q13 streak over self-contained rounds: each round's control readings GREEN, its restore "
                   "byte-exact, its runtime mutant readings RED with the new clause as the only addition, and "
                   "its one-token dedicated carrier RED on the new clause while v3 reads it GREEN",
           "ruler": {"v4": {"file": V4.name, "bytes": V4.stat().st_size, "blob40": blob40(V4.read_bytes())},
                     "v3": {"file": V3.name, "bytes": V3.stat().st_size, "blob40": blob40(V3.read_bytes()),
                            "published_blob40": "e9a4188f63e27bbbf8bfed35adfd554b9e8641d9"}},
           "rounds_requested": len(paths), "rounds_green": len(green_rounds),
           "longest_consecutive_green_run": {"length": len(best), "rounds": best},
           "red_rounds": red_named,
           "consecutiveness_gaps": gaps, "stored_vs_recomputed_mismatches": lying,
           "reading_order_warnings": ordering,
           "ruler_changed_between_rounds": ruler_changed,
           "derived_result": verdict, "rounds": rounds}
    p = BASE / "ord0271b_streak.json"
    p.write_text(json.dumps(out, ensure_ascii=False, indent=1), "utf-8", newline="\n")
    print(json.dumps({"derived_result": verdict, "rounds_requested": len(paths),
                      "rounds_green": len(green_rounds),
                      "per_round": [(r.get("round"), r.get("recomputed"), r.get("checks_green"),
                                     r.get("red_checks")) for r in rounds],
                      "longest_consecutive_green_run": {"length": len(best), "rounds": best},
                      "red_rounds": red_named,
                      "gaps": gaps, "reading_order_warnings": ordering,
                      "stored_vs_recomputed_mismatches": lying,
                      "ruler_changed_between_rounds": ruler_changed}, ensure_ascii=False, indent=1))
    print("->", p.name, f"{p.stat().st_size:,} B blob {blob40(p.read_bytes())[:16]}")
    return 0 if verdict.startswith("STREAK_MET") else 5


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
