"""Real-model probe for the Hermes MCP request_id schema alignment."""

from __future__ import annotations

import argparse
import json
import os
import tempfile
from pathlib import Path

from scripts.hermes_r10_tool_planning_probe import _run_trial
from scripts.hermes_r6_h11_model_probe import (
    PROFILE_NAME,
    _provider_key,
    _read_profile,
    clean_receipt,
    git,
)


SCENARIO_ID = "hermes-r10-request-id-schema-alignment"


def save(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, default=str) + "\n", encoding="utf-8")


def run(output: Path, trials: int = 3) -> dict[str, object]:
    output.mkdir(parents=True, exist_ok=True)
    source = clean_receipt()
    hermes_home = Path(os.environ.get("LOCALAPPDATA", "")) / "hermes"
    hermes_bin = hermes_home / "hermes-agent" / ".venv" / "Scripts" / "hermes.exe"
    hermes_python = hermes_home / "hermes-agent" / ".venv" / "Scripts" / "python.exe"
    profile_config = hermes_home / "profiles" / PROFILE_NAME / "config.yaml"
    profile = _read_profile(hermes_python, profile_config)
    provider_key = _provider_key()
    if not provider_key:
        result = {"result": "BLOCKED", "scenario_id": SCENARIO_ID, "exact_blockers": ["MODEL_NOT_CONFIGURED"], "source": source}
        save(output / "R10-REQUEST-ID-RESULT.json", result)
        return result

    temp_root = Path(tempfile.mkdtemp(prefix="citynexus-hermes-request-id-"))
    rows = []
    try:
        for number in range(1, trials + 1):
            row = _run_trial(
                temp_root,
                hermes_bin,
                hermes_python,
                profile,
                provider_key,
                "request-id-schema",
                number,
                output,
            )
            row["scenario_id"] = SCENARIO_ID
            save(output / f"R10-request-id-schema-trial-{number}.json", row)
            chronology_path = output / f"R10-request-id-schema-trial-{number}-chronology.json"
            chronology = json.loads(chronology_path.read_text(encoding="utf-8"))
            adapter_request_ids = [
                str(item.get("request_id"))
                for item in chronology
                if item.get("kind") == "mcp.request" and item.get("request_id") is not None
            ]
            short_ids = [value for value in adapter_request_ids if len(value) < 8]
            row["request_id_observation"] = {
                "adapter_request_count": len(adapter_request_ids),
                "short_request_ids": short_ids,
                "all_adapter_request_ids_valid_length": not short_ids,
            }
            save(output / f"R10-request-id-schema-trial-{number}.json", row)
            rows.append(row)
    finally:
        # _run_trial owns each arm's shutdown; the temporary root is disposable
        # and is intentionally not part of the review package.
        pass

    blockers = []
    for row in rows:
        failed = [name for name, passed in row.get("assertions", {}).items() if not passed]
        if failed:
            blockers.append(f"trial-{row.get('trial')}:" + ",".join(failed))
        if not row.get("request_id_observation", {}).get("all_adapter_request_ids_valid_length"):
            blockers.append(f"trial-{row.get('trial')}:short_adapter_request_id")
    result = {
        "result": "PASS" if not blockers else "BLOCKED",
        "scenario_id": SCENARIO_ID,
        "source": {"pre": source, "post": clean_receipt(), "head": git("rev-parse", "HEAD"), "parent": git("rev-parse", "HEAD^")},
        "runtime": {
            "profile": PROFILE_NAME,
            "provider": profile["provider"],
            "model": profile["model"],
            "autonomy": "PLAN_ONLY",
            "p7": False,
            "mcp_tools": profile["tool_allowlist"],
        },
        "trials": [
            {
                "trial": row.get("trial"),
                "run_id": row.get("run_id"),
                "status": row.get("status"),
                "usage": row.get("usage"),
                "mcp_call_count": row.get("mcp_call_count"),
                "mcp_error_count": row.get("mcp_error_count"),
                "request_id_observation": row.get("request_id_observation"),
                "tool_sequence": row.get("tool_sequence"),
            }
            for row in rows
        ],
        "exact_blockers": blockers,
        "old_observed_failure": "model supplied read-1/read-2 below the server request_id minimum of 8 characters",
    }
    save(output / "R10-REQUEST-ID-RESULT.json", result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence-dir", type=Path, required=True)
    parser.add_argument("--trials", type=int, choices=(3,), default=3)
    args = parser.parse_args()
    print(json.dumps(run(args.evidence_dir, args.trials), ensure_ascii=False, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
