"""Hermes R19: exercise the actual degraded mobility fallback path."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any

from scripts import hermes_r18_unavailable_proposal_reliability_probe as r18
from scripts.hermes_r6_h11_model_probe import PROFILE_NAME, _provider_key, _read_profile, _save_json, clean_receipt, git


SCENARIO_ID = "hermes-r19-runtime-mobility-fallback-reliability"
BLACKHOLE_VALHALLA_URL = "http://127.0.0.1:1"
ARMS = r18.ARMS
FULL_REPLAN_FIELDS = frozenset(
    {
        "id",
        "journey_id",
        "trigger_event_id",
        "base_plan_version_id",
        "proposed_plan_version_id",
        "status",
        "hard_constraints_passed",
        "locked_commitments_preserved",
        "utility_score",
        "score_breakdown",
        "diff",
        "explanation",
    }
)


def _walk(value: Any):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from _walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk(child)


def _runtime_fallback_observation(trace: list[dict[str, Any]]) -> dict[str, Any]:
    degraded = []
    synthetic = False
    live = []
    for item in trace:
        if item.get("kind") != "mcp.response":
            continue
        response = item.get("response") if isinstance(item.get("response"), dict) else {}
        for node in _walk(response):
            if node.get("degraded") is True and isinstance(node.get("facts"), list):
                degraded.append({"snapshot_id": node.get("snapshot_id"), "source_provider": node.get("source_provider"), "route_provenance": node.get("route_provenance"), "fact_count": len(node.get("facts") or [])})
            synthetic = synthetic or node.get("route_provenance") == "SYNTHETIC_FIXTURE"
            for field in ("provenance", "provider_provenance", "route_provenance", "capture_provenance"):
                if node.get(field) in {"LIVE_PROVIDER_CAPTURE", "PROVIDER_VERIFIED"}:
                    live.append({"field": field, "value": node.get(field)})
    return {"degraded_snapshots": degraded, "runtime_fallback_observed": bool(degraded), "synthetic_fallback_route_observed": synthetic, "live_structured_claims": live, "no_live_provider_claim": not live}


def _proposal_boundary_observation(
    trace: list[dict[str, Any]], row: dict[str, Any]
) -> dict[str, Any]:
    requests = [
        item
        for item in trace
        if item.get("kind") == "mcp.request"
        and item.get("tool_name") == "request_replan"
    ]
    direct_responses = [
        item
        for item in trace
        if item.get("kind") == "mcp.response"
        and item.get("tool_name") == "request_replan"
    ]
    listed: list[dict[str, Any]] = []
    for item in trace:
        if item.get("kind") != "mcp.response" or item.get("tool_name") != "list_replans":
            continue
        response = item.get("response")
        if not isinstance(response, dict) or not isinstance(response.get("proposals"), list):
            continue
        listed.extend(proposal for proposal in response["proposals"] if isinstance(proposal, dict))

    listed_ids = [str(item.get("id") or "") for item in listed if item.get("id")]
    persisted_ids = {
        str(item)
        for item in (row.get("replan_observation") or {}).get(
            "proposal_ids_persisted_after", []
        )
    }
    complete = bool(listed) and all(FULL_REPLAN_FIELDS.issubset(item) for item in listed)
    persisted = bool(listed_ids) and set(listed_ids).issubset(persisted_ids)
    transport_gap = bool(requests) and not direct_responses and complete and persisted
    direct_full = bool(direct_responses) and all(
        isinstance(item.get("response"), dict)
        and item["response"].get("proposal_contract_version")
        == "hermes-replan-proposal-view.v1"
        for item in direct_responses
    )
    return {
        "request_replan_request_count": len(requests),
        "request_replan_response_count": len(direct_responses),
        "direct_full_contract_observed": direct_full,
        "list_replans_full_contract_observed": complete,
        "listed_proposal_ids": listed_ids,
        "listed_proposals_persisted": persisted,
        "server_proposal_contract_observed": (direct_full or complete) and persisted,
        "request_replan_transport_gap": transport_gap,
        "finding": (
            "REQUEST_REPLAN_RESPONSE_TIMEOUT_WITH_PERSISTED_PROPOSALS"
            if transport_gap
            else None
        ),
    }


def _run_trial(temp_root: Path, hermes_bin: Path, hermes_python: Path, profile: dict[str, Any], provider_key: str, arm_name: str, trial: int, output: Path) -> dict[str, Any]:
    original = {"SCENARIO_ID": r18.SCENARIO_ID, "ARMS": r18.ARMS, "url": os.environ.get("CITYNEXUS_LIVE_VALHALLA_URL")}
    os.environ["CITYNEXUS_LIVE_VALHALLA_URL"] = BLACKHOLE_VALHALLA_URL
    r18.SCENARIO_ID = SCENARIO_ID
    r18.ARMS = ARMS
    try:
        row = r18._run_trial(temp_root, hermes_bin, hermes_python, profile, provider_key, arm_name, trial, output)
        old = output / f"R18-{arm_name}-trial-{trial}"
        new = output / f"R19-{arm_name}-trial-{trial}"
        for path in output.glob(old.name + "*"):
            path.rename(output / path.name.replace(old.name, new.name, 1))
        trace = json.loads((output / f"R19-{arm_name}-trial-{trial}-chronology.json").read_text(encoding="utf-8"))
        observation = _runtime_fallback_observation(trace)
        proposal_boundary = _proposal_boundary_observation(trace, row)
        proposal_arm = arm_name == "provider-unavailable-proposal"
        row["scenario_id"] = SCENARIO_ID
        row["runtime_fallback_observation"] = observation
        row["proposal_boundary_observation"] = proposal_boundary
        row["product_findings"] = (
            [proposal_boundary["finding"]]
            if proposal_boundary.get("finding")
            else []
        )
        row["assertions"]["runtime_provider_fallback_observed"] = observation["runtime_fallback_observed"] if proposal_arm else True
        row["assertions"]["synthetic_fallback_route_observed"] = observation["synthetic_fallback_route_observed"] if proposal_arm else True
        row["assertions"]["no_live_provider_claim"] = observation["no_live_provider_claim"]
        row["assertions"]["unavailable_proposal_boundary"] = (
            proposal_boundary["server_proposal_contract_observed"]
            if proposal_arm
            else proposal_boundary["request_replan_request_count"] == 0
        )
        # R17's generic proposal predicate requires a direct request_replan
        # response. R19 deliberately measures the real runtime case where that
        # response can time out after the server has persisted the full proposal;
        # the server-owned list_replans contract is the authoritative recovery
        # evidence for this probe, while the transport gap remains a finding.
        row["assertions"]["intent_and_truth_grounding"] = (
            row["assertions"].get("provider_state_fixture_truth") is True
            and row["assertions"].get("provider_state_seen_in_server_response") is True
            and row["assertions"].get("synthetic_provider_not_live") is True
            and row["assertions"]["runtime_provider_fallback_observed"]
            and row["assertions"]["synthetic_fallback_route_observed"]
            and row["assertions"]["no_live_provider_claim"]
            and row["assertions"]["unavailable_proposal_boundary"]
        )
        _save_json(output / f"R19-{arm_name}-trial-{trial}.json", row)
        return row
    finally:
        for key, value in (("SCENARIO_ID", original["SCENARIO_ID"]), ("ARMS", original["ARMS"])):
            setattr(r18, key, value)
        if original["url"] is None:
            os.environ.pop("CITYNEXUS_LIVE_VALHALLA_URL", None)
        else:
            os.environ["CITYNEXUS_LIVE_VALHALLA_URL"] = original["url"]


def _stats(items: list[dict[str, Any]]) -> dict[str, Any]:
    result = {}
    for field, getter in {"total_tokens": lambda item: (item.get("usage") or {}).get("total_tokens"), "mcp_call_count": lambda item: item.get("mcp_call_count"), "mcp_response_bytes": lambda item: (item.get("measurement") or {}).get("cumulative_tool_response_bytes")}.items():
        values = sorted(int(value) for item in items if (value := getter(item)) is not None)
        result[field] = {"values": values, "min": min(values) if values else None, "max": max(values) if values else None, "median": values[len(values) // 2] if values else None}
    return result


def run(output: Path, trials: int = 2) -> dict[str, Any]:
    output.mkdir(parents=True, exist_ok=True)
    source_before = clean_receipt()
    hermes_home = Path(os.environ.get("LOCALAPPDATA", "")) / "hermes"
    hermes_bin = hermes_home / "hermes-agent" / ".venv" / "Scripts" / "hermes.exe"
    hermes_python = hermes_home / "hermes-agent" / ".venv" / "Scripts" / "python.exe"
    profile = _read_profile(hermes_python, hermes_home / "profiles" / PROFILE_NAME / "config.yaml")
    provider_key = _provider_key()
    if not provider_key:
        result = {"result": "BLOCKED", "scenario_id": SCENARIO_ID, "exact_blockers": ["MODEL_NOT_CONFIGURED"], "source": {"pre": source_before, "post": clean_receipt()}}
        _save_json(output / "R19-RESULT.json", result)
        return result
    temp_root = Path(tempfile.mkdtemp(prefix="citynexus-hermes-r19-"))
    try:
        arms, model_runs = {}, []
        for arm_name in ARMS:
            rows = [_run_trial(temp_root, hermes_bin, hermes_python, profile, provider_key, arm_name, trial, output) for trial in range(1, trials + 1)]
            arms[arm_name] = {"trials": rows, "stats": _stats(rows)}
            model_runs.extend({"arm": arm_name, "trial": row.get("trial"), "run_id": row.get("run_id"), "mission_id": row.get("mission_id"), "session_id": row.get("session_id"), "status": row.get("status"), "usage": row.get("usage"), "mcp_call_count": row.get("mcp_call_count")} for row in rows)
            _save_json(output / f"R19-{arm_name}-trials.json", arms[arm_name])
        failures = [f"{name}-trial-{row.get('trial')}:" + ",".join(key for key, value in row.get("assertions", {}).items() if not value) for name, arm in arms.items() for row in arm["trials"] if any(not value for value in row.get("assertions", {}).values())]
        result = {"result": "PASS" if not failures else "RED", "scenario_id": SCENARIO_ID, "source": {"pre": source_before, "post": clean_receipt(), "head": git("rev-parse", "HEAD"), "parent": git("rev-parse", "HEAD^")}, "runtime": {"profile": PROFILE_NAME, "provider": profile["provider"], "model": profile["model"], "tool_allowlist": profile["tool_allowlist"], "autonomy": "PLAN_ONLY", "p7": False, "database": "fresh disposable SQLite per arm/trial", "network": "CityNexus/MCP loopback; loopback Valhalla blackhole; configured model provider only", "valhalla_url": BLACKHOLE_VALHALLA_URL, "provider_state": "UNAVAILABLE", "provider_state_provenance": "SYNTHETIC_HARNESS_FIXTURE; runtime fallback is a loopback failure fixture; not LIVE/provider evidence"}, "arms": {name: {"stats": arm["stats"], "trials": len(arm["trials"])} for name, arm in arms.items()}, "exact_blockers": failures, "model_runs": model_runs}
        _save_json(output / "R19-RESULT.json", result)
        _save_json(output / "R19-profile-contract.json", {"profile": PROFILE_NAME, "provider": profile["provider"], "model": profile["model"], "tool_allowlist": profile["tool_allowlist"], "disabled_toolsets": profile["disabled_toolsets"], "resources": profile["resources"], "prompts": profile["prompts"], "p7": False})
        return result
    finally:
        shutil.rmtree(temp_root, ignore_errors=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence-dir", type=Path, required=True)
    parser.add_argument("--trials", type=int, default=2, choices=range(1, 4))
    args = parser.parse_args()
    result = run(args.evidence_dir, args.trials)
    print(json.dumps({"result": result.get("result"), "scenario_id": result.get("scenario_id"), "evidence_dir": str(args.evidence_dir), "exact_blockers": result.get("exact_blockers", [])}, ensure_ascii=False, sort_keys=True))
    return 0 if result.get("result") == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
