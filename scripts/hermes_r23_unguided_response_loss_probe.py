"""Hermes R23: response-loss recovery without transport-specific guidance."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from scripts import hermes_r22_response_loss_recovery_probe as r22


SCENARIO_ID = r22.R23_SCENARIO_ID


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence-dir", type=Path, required=True)
    parser.add_argument("--trials", type=int, default=2, choices=range(1, 4))
    args = parser.parse_args()
    result = r22.run(
        args.evidence_dir,
        args.trials,
        guided=False,
        scenario_id=SCENARIO_ID,
        file_prefix="R23",
    )
    print(json.dumps({
        "result": result.get("result"),
        "scenario_id": result.get("scenario_id"),
        "evidence_dir": str(args.evidence_dir),
        "exact_blockers": result.get("exact_blockers", []),
    }, ensure_ascii=False, sort_keys=True))
    return 0 if result.get("result") == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
