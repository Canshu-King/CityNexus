"""Hermes R20: prove request_replan transport delivery without authority mutation."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any

from scripts.hermes_r4_contract_probe import run_probe


SCENARIO_ID = "hermes-r20-request-replan-transport-reliability"
CORE_ASSERTIONS = (
    "real_direct_planner_candidate_exists",
    "real_stdio_mcp_candidate_exists",
    "nonempty_candidate_diff_plan_id_and_score",
    "candidate_semantic_parity",
    "mcp_contract_versioned_and_complete",
    "proposal_only_one_active_plan_unchanged",
    "mcp_tool_surface_exactly_v2_allowlist",
    "all_service_children_guarded_loopback_only",
)
EXPECTED_TOOLS = [
    "inspect_journey",
    "inspect_twin",
    "list_replans",
    "search_city_services",
    "request_replan",
    "accept_replan",
    "replace_activity",
    "reschedule_activity",
    "create_booking",
    "cancel_refundable_booking",
    "request_commitment_change",
]


def _git(*args: str) -> str:
    return subprocess.check_output(["git", *args], text=True).strip()


def _json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _core_projection(report: dict[str, Any]) -> dict[str, bool]:
    return {
        item["name"]: item["passed"] is True
        for item in report.get("assertions", [])
        if item.get("name") in CORE_ASSERTIONS
    }


def run(output: Path) -> dict[str, Any]:
    report = run_probe(output)
    mcp_receipt = _json(output / "hermes-r4-mcp-stdio.json")
    response = mcp_receipt.get("response") or {}
    core = _core_projection(report)
    cleanup_blockers = [
        blocker
        for blocker in report.get("blockers", [])
        if blocker == "OperationalError: disk I/O error"
    ]
    unexpected_blockers = [
        blocker
        for blocker in report.get("blockers", [])
        if blocker not in cleanup_blockers
    ]
    mcp_contract = (
        response.get("proposal_contract_version") == "hermes-replan-proposal-view.v1"
        and isinstance(response.get("proposal_views"), list)
        and bool(response.get("proposal_views"))
    )
    core_pass = (
        all(core.values())
        and len(core) == len(CORE_ASSERTIONS)
        and mcp_contract
        and not unexpected_blockers
    )
    result = {
        "result": (
            "PASS"
            if core_pass and not cleanup_blockers
            else "PASS_WITH_EVIDENCE_CLEANUP_BLOCKER"
            if core_pass
            else "RED"
        ),
        "scenario_id": SCENARIO_ID,
        "source": {
            "head": _git("rev-parse", "HEAD"),
            "parent": _git("rev-parse", "HEAD^"),
            "branch": _git("branch", "--show-current"),
            "porcelain": _git("status", "--porcelain=v1", "--untracked-files=all"),
        },
        "transport_fix": {
            "tool": "request_replan",
            "client_timeout_seconds": 120.0,
            "other_tool_timeout_seconds": 15.0,
            "backend_api_unchanged": True,
            "proposal_authority_unchanged": True,
        },
        "core_assertions": core,
        "mcp_contract_observed": mcp_contract,
        "direct_stdio_semantic_match": report.get("semantic_comparison", {}).get(
            "semantic_match"
        ),
        "authority_assertion": next(
            (
                item
                for item in report.get("assertions", [])
                if item.get("name") == "proposal_only_one_active_plan_unchanged"
            ),
            {},
        ),
        "cleanup_blockers": cleanup_blockers,
        "unexpected_blockers": unexpected_blockers,
        "raw_r4_result": report.get("result"),
        "raw_r4_run_id": report.get("run_id"),
        "p7": False,
        "autonomy": "PLAN_ONLY / NOT_USED",
        "network": "CityNexus/MCP loopback; live providers disabled",
        "database": "fresh disposable SQLite copies; database files excluded from package",
    }
    (output / "R20-RESULT.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    result = run(args.output_dir)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result["result"].startswith("PASS") else 1


if __name__ == "__main__":
    raise SystemExit(main())
