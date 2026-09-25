"""Recompute R10 derived metrics from immutable raw trial chronologies.

This intentionally does not touch chronology, native events, or measurements.
It refreshes only the small JSON projections whose post-success proposal
identity metric depends on the current response field names.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from scripts.hermes_r10_tool_planning_probe import _acceptance, _post_success_reads, _stats


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, default=str) + "\n", encoding="utf-8")


def run(evidence: Path) -> dict[str, object]:
    original = evidence / "R10-RESULT.json"
    original_bytes = original.read_bytes()
    result = json.loads(original_bytes.decode("utf-8"))
    variants: dict[str, dict[str, object]] = {}
    for variant in ("baseline", "r10-guided"):
        trials = []
        for number in (1, 2, 3):
            prefix = evidence / f"R10-{variant}-trial-{number}"
            chronology = json.loads(prefix.with_name(prefix.name + "-chronology.json").read_text(encoding="utf-8"))
            reads = _post_success_reads(chronology)
            write_json(prefix.with_name(prefix.name + "-post-success-reads.json"), reads)
            trial = json.loads(prefix.with_suffix(".json").read_text(encoding="utf-8"))
            trial["post_success_reads"] = reads
            write_json(prefix.with_suffix(".json"), trial)
            trials.append(trial)
        stats = _stats(trials)
        aggregate = {"trials": trials, "stats": stats}
        variants[variant] = aggregate
        write_json(evidence / f"R10-{variant}-trials.json", aggregate)

    guided_acceptance = _acceptance(variants["baseline"], variants["r10-guided"])
    result["variants"] = {
        name: {
            "stats": value["stats"],
            "acceptance": guided_acceptance if name == "r10-guided" else None,
            "trials": len(value["trials"]),
        }
        for name, value in variants.items()
    }
    baseline_failures = []
    for item in variants["baseline"]["trials"]:
        failed = [name for name, passed in item.get("assertions", {}).items() if not passed]
        if failed:
            baseline_failures.append(f"baseline-trial-{item.get('trial')}:" + ",".join(failed))
    result["result"] = "PASS" if not baseline_failures else "BLOCKED"
    result["exact_blockers"] = baseline_failures
    result["optimization_decision"] = guided_acceptance["decision"]
    result["variant_rejection_reasons"] = {
        "r10-guided": [
            f"trial-{item.get('trial')}:" + ",".join(
                name for name, passed in item.get("assertions", {}).items() if not passed
            )
            for item in variants["r10-guided"]["trials"]
            if any(not passed for passed in item.get("assertions", {}).values())
        ]
    }
    result.setdefault("source", {})["remeasurement"] = {
        "method": "raw chronology proposal_views[*].proposal_id plus proposals[*].id",
        "measurement_commit": __import__("subprocess").check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
        "original_result_sha256": hashlib.sha256(original_bytes).hexdigest(),
    }
    write_json(original, result)
    report = {
        "result_path": str(original),
        "original_result_sha256": hashlib.sha256(original_bytes).hexdigest(),
        "new_result_sha256": hashlib.sha256(original.read_bytes()).hexdigest(),
        "measurement_commit": result["source"]["remeasurement"]["measurement_commit"],
        "optimization_decision": guided_acceptance["decision"],
        "result": result["result"],
        "exact_blockers": baseline_failures,
    }
    write_json(evidence / "R10-RECOMPUTED-METRICS.json", report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence-dir", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(run(args.evidence_dir), ensure_ascii=False, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
