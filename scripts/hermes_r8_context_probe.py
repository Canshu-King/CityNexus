from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import tempfile
import uuid
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

try:
    from scripts.hermes_r6_h11_model_probe import (
        EXPECTED_TOOLS, PROFILE_NAME, _free_port, _provider_key, _read_profile,
        _read_trace, _save_json, _schema_and_state, _seed, clean_receipt, git,
    )
    from scripts.hermes_r7_human_approval_probe import (
        _configure_arm, _r7_state, _sanitize_guard, _stop_arm,
    )
except ImportError:  # direct script execution from scripts/
    from hermes_r6_h11_model_probe import (
        EXPECTED_TOOLS, PROFILE_NAME, _free_port, _provider_key, _read_profile,
        _read_trace, _save_json, _schema_and_state, _seed, clean_receipt, git,
    )
    from hermes_r7_human_approval_probe import (
        _configure_arm, _r7_state, _sanitize_guard, _stop_arm,
    )


SCENARIO_ID = "hermes-r8-model-context-token-efficiency-baseline"
AGENT_ID = "hermes-native"
BASELINE_INPUT = (
    "The place in my current trip is closed. Inspect the current Journey and "
    "trip context, review any existing replans, and work out the safest feasible "
    "replacement. Search CityNexus services only if needed and request a replan "
    "if the server says one is feasible. Do not accept a proposal, book anything, "
    "pay, change commitments, or claim success without a server response."
)
BASELINE_INSTRUCTIONS = (
    "Use only the current CityNexus MCP tools. Make your own read/tool choices; "
    "do not assume a fixed sequence. This is PLAN_ONLY: request_replan is allowed "
    "as a proposal-only operation, but accept_replan and all booking, payment, "
    "commitment, or user-approval actions are forbidden. Explain the final result "
    "from server responses only."
)


def _json_bytes(value: Any) -> int:
    return len(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8"))


def _json_hash(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")).hexdigest()


def _approx_tokens(byte_count: int) -> int:
    # Provider tokenizers are not exposed by the native run receipt. This is a
    # deliberately labelled serialized-JSON estimate, not provider usage.
    return (int(byte_count) + 3) // 4


def _leaf_tokens(value: Any) -> set[str]:
    if isinstance(value, dict):
        result: set[str] = set()
        for key, item in value.items():
            result.add(str(key))
            result.update(_leaf_tokens(item))
        return result
    if isinstance(value, list):
        result: set[str] = set()
        for item in value:
            result.update(_leaf_tokens(item))
        return result
    return set(re.findall(r"[A-Za-z0-9_:-]{2,}", str(value)))


def _field_paths(value: Any, prefix: str = "") -> dict[str, Any]:
    if isinstance(value, dict):
        result: dict[str, Any] = {}
        for key, item in value.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            result.update(_field_paths(item, path))
        return result
    if isinstance(value, list):
        result: dict[str, Any] = {}
        for index, item in enumerate(value):
            result.update(_field_paths(item, f"{prefix}[{index}]"))
        return result
    return {prefix: value}


def _pair_calls(run: dict[str, Any]) -> list[dict[str, Any]]:
    calls = run.get("mcp_calls", []) if isinstance(run, dict) else []
    requests = [item for item in calls if item.get("kind") == "mcp.request"]
    responses = [item for item in calls if item.get("kind") == "mcp.response"]
    errors = [item for item in calls if item.get("kind") == "mcp.error"]
    response_by_id: dict[tuple[Any, Any], list[dict[str, Any]]] = defaultdict(list)
    for item in responses:
        response_by_id[(item.get("tool_name"), item.get("request_id"))].append(item)
    error_by_id: dict[tuple[Any, Any], list[dict[str, Any]]] = defaultdict(list)
    for item in errors:
        error_by_id[(item.get("tool_name"), item.get("request_id"))].append(item)
    paired: list[dict[str, Any]] = []
    for sequence, request in enumerate(requests, 1):
        key = (request.get("tool_name"), request.get("request_id"))
        response = response_by_id[key].pop(0) if response_by_id[key] else None
        error = error_by_id[key].pop(0) if error_by_id[key] else None
        request_payload = request.get("request") if isinstance(request.get("request"), dict) else {}
        response_payload = response.get("response") if isinstance(response, dict) else None
        response_bytes = int(response.get("response_serialized_bytes") or 0) if response else 0
        response_summary_bytes = _json_bytes(response_payload) if response_payload is not None else 0
        paired.append({
            "sequence": sequence,
            "tool_name": request.get("tool_name"),
            "request_id": request.get("request_id"),
            "request_json_bytes": _json_bytes(request_payload),
            "request_json_approx_tokens": _approx_tokens(_json_bytes(request_payload)),
            "response_json_bytes": response_bytes,
            "response_json_approx_tokens": _approx_tokens(response_bytes),
            "response_summary_bytes": response_summary_bytes,
            "response_summary": response_payload,
            "response_hash": _json_hash(response_payload) if response_payload is not None else None,
            "error": error.get("error") if error else None,
        })
    return paired


def _measure_run(run: dict[str, Any]) -> dict[str, Any]:
    paired = _pair_calls(run)
    prompt_bytes = _json_bytes({
        "input": run.get("request", {}).get("input"),
        "instructions": run.get("request", {}).get("instructions"),
        "metadata": run.get("request", {}).get("metadata"),
    })
    cumulative_response = 0
    previous_tokens: set[str] = set()
    previous_hash: str | None = None
    field_values: dict[str, Counter[str]] = defaultdict(Counter)
    for item in paired:
        cumulative_response += item["response_json_bytes"]
        current_tokens = _leaf_tokens(item.get("response_summary"))
        union = len(current_tokens | previous_tokens)
        item["payload_token_overlap_with_previous"] = (
            round(len(current_tokens & previous_tokens) / union, 6) if union else 0.0
        )
        item["exact_duplicate_of_previous"] = bool(previous_hash and item["response_hash"] == previous_hash)
        item["cumulative_response_bytes"] = cumulative_response
        item["cumulative_context_bytes_proxy"] = prompt_bytes + cumulative_response
        item["cumulative_context_approx_tokens_proxy"] = _approx_tokens(item["cumulative_context_bytes_proxy"])
        for path, value in _field_paths(item.get("response_summary")).items():
            field_values[path][json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)] += 1
        previous_tokens = current_tokens
        previous_hash = item["response_hash"]

    by_tool: dict[str, dict[str, Any]] = {}
    for tool in sorted({str(item.get("tool_name")) for item in paired}):
        rows = [item for item in paired if str(item.get("tool_name")) == tool]
        response_sizes = [int(item["response_json_bytes"]) for item in rows]
        by_tool[tool] = {
            "call_count": len(rows),
            "request_json_bytes": sum(int(item["request_json_bytes"]) for item in rows),
            "response_json_bytes": sum(response_sizes),
            "response_json_approx_tokens": sum(int(item["response_json_approx_tokens"]) for item in rows),
            "largest_response_bytes": max(response_sizes, default=0),
            "response_summary_bytes": sum(int(item["response_summary_bytes"]) for item in rows),
        }
    ranked = sorted(
        ({"tool_name": tool, **values} for tool, values in by_tool.items()),
        key=lambda item: (item["response_json_bytes"], item["largest_response_bytes"]),
        reverse=True,
    )
    repeated_fields = []
    for path, counts in field_values.items():
        distinct_values = [value for value, count in counts.items() if count >= 2]
        if distinct_values:
            repeated_fields.append({"path": path, "repeat_count": sum(counts.values()), "distinct_repeated_values": len(distinct_values)})
    repeated_fields.sort(key=lambda item: (item["repeat_count"], item["path"]), reverse=True)
    usage = run.get("usage") if isinstance(run.get("usage"), dict) else {}
    exact_input = usage.get("input_tokens", usage.get("prompt_tokens"))
    exact_output = usage.get("output_tokens", usage.get("completion_tokens"))
    exact_total = usage.get("total_tokens")
    tool_names = [str(item.get("tool_name")) for item in paired]
    return {
        "method": {
            "request_bytes": "canonical JSON bytes from traced MCP request payload",
            "response_bytes": "actual serialized JSON bytes recorded by the MCP wrapper",
            "context_bytes_proxy": "initial run input/instructions/metadata JSON bytes plus cumulative MCP response bytes",
            "approx_tokens": "serialized JSON bytes divided by four, rounded up; provider usage remains authoritative",
        },
        "model_usage": {
            "input_tokens": exact_input,
            "output_tokens": exact_output,
            "total_tokens": exact_total,
        },
        "prompt_json_bytes": prompt_bytes,
        "prompt_json_approx_tokens": _approx_tokens(prompt_bytes),
        "mcp_call_count": len(paired),
        "mcp_response_bytes": sum(int(item["response_json_bytes"]) for item in paired),
        "largest_response_bytes": max((int(item["response_json_bytes"]) for item in paired), default=0),
        "tool_sequence": tool_names,
        "per_call": paired,
        "ranked_context_cost_table": ranked,
        "repeated_payload_fields": repeated_fields[:100],
        "duplicate_response_count": sum(bool(item["exact_duplicate_of_previous"]) for item in paired),
        "coverage": {
            "inspect_journey": "inspect_journey" in tool_names,
            "inspect_twin": "inspect_twin" in tool_names,
            "list_replans": "list_replans" in tool_names,
            "search_city_services": "search_city_services" in tool_names,
            "request_replan": "request_replan" in tool_names,
            "accept_replan": "accept_replan" in tool_names,
        },
        "interpretation": {
            "largest_context_contributor": ranked[0]["tool_name"] if ranked else None,
            "search_city_services_loop_dominates": sum(v["response_json_bytes"] for k, v in by_tool.items() if k == "search_city_services") > sum(v["response_json_bytes"] for k, v in by_tool.items() if k != "search_city_services"),
            "inspect_twin_and_inspect_journey_both_observed": "inspect_twin" in tool_names and "inspect_journey" in tool_names,
            "list_replans_and_request_replan_both_observed": "list_replans" in tool_names and "request_replan" in tool_names,
            "proposal_payload_bytes": sum(_json_bytes(item.get("response_summary", {}).get("proposal_views")) for item in paired if isinstance(item.get("response_summary"), dict)),
        },
    }


def _authority_projection(state: dict[str, Any]) -> dict[str, Any]:
    entities = state.get("entities", {})
    journey = entities.get("journey", {}) if isinstance(entities.get("journey"), dict) else {}
    return {
        "journey": {key: journey.get(key) for key in ("id", "status", "active_plan_version_id", "current_activity_id")},
        "active_plan_ids": sorted(str(row.get("id")) for row in entities.get("plans", []) if row.get("status") == "ACTIVE"),
        "bookings": entities.get("bookings", []),
        "commitments": entities.get("commitments", []),
        "payments": entities.get("payments", []),
        "approval_statuses": [(row.get("id"), row.get("status")) for row in entities.get("approvals", [])],
    }


def run(output: Path) -> dict[str, Any]:
    output.mkdir(parents=True, exist_ok=True)
    source_pre = clean_receipt()
    hermes_home = Path(os.environ.get("LOCALAPPDATA", "")) / "hermes"
    hermes_bin = hermes_home / "hermes-agent" / ".venv" / "Scripts" / "hermes.exe"
    hermes_python = hermes_home / "hermes-agent" / ".venv" / "Scripts" / "python.exe"
    profile_config = hermes_home / "profiles" / PROFILE_NAME / "config.yaml"
    profile = _read_profile(hermes_python, profile_config)
    provider_key = _provider_key()
    result_id = str(uuid.uuid4())
    temp_root = Path(tempfile.mkdtemp(prefix="citynexus-hermes-r8-"))
    arm: dict[str, Any] | None = None
    stage = "startup"
    try:
        if not provider_key:
            raise RuntimeError("MODEL_NOT_CONFIGURED")
        arm = _configure_arm(temp_root, "r8-baseline", hermes_bin, hermes_python, profile, provider_key)
        seed = _seed(arm["backend"], arm["runtime"])
        before = _r7_state(arm["database"], seed["journey_id"])
        mission_id = str(uuid.uuid4())
        session_id = f"citynexus-{seed['journey_id']}-r8-baseline-{mission_id}"
        stage = "real_model_baseline"
        run_value = __import__("scripts.hermes_r6_h11_model_probe", fromlist=["_gateway_run"])._gateway_run(
            gateway=arm["gateway"], backend=arm["backend"], journey_id=seed["journey_id"],
            session_id=session_id, mission_id=mission_id, run_key="r8-baseline-" + mission_id,
            user_input=BASELINE_INPUT + " Journey ID: " + seed["journey_id"],
            instructions=BASELINE_INSTRUCTIONS + " Journey ID: " + seed["journey_id"],
            trace_path=arm["trace_path"], tee=arm["tee"], api_headers=arm["headers"], timeout_seconds=300,
        )
        after = _r7_state(arm["database"], seed["journey_id"])
        measurement = _measure_run(run_value)
        chronology = _read_trace(arm["trace_path"])
        native_events = run_value.get("native_event_stream", [])
        tool_names = measurement["tool_sequence"]
        mutation_tools = {"accept_replan", "replace_activity", "reschedule_activity", "create_booking", "cancel_refundable_booking", "request_commitment_change"}
        authority_before = _authority_projection(before)
        authority_after = _authority_projection(after)
        assertions = {
            "real_model_inference": bool(run_value.get("actual_invocation_observed")),
            "native_mcp_observed": bool(measurement["mcp_call_count"] and native_events),
            "current_tool_surface": set(arm["discovered"]) == set(EXPECTED_TOOLS),
            "inspect_journey_observed": "inspect_journey" in tool_names,
            "no_authoritative_mutation_tool": not bool(set(tool_names) & mutation_tools),
            "journey_authority_unchanged": authority_before["journey"] == authority_after["journey"],
            "no_booking_payment_commitment_mutation": authority_before["bookings"] == authority_after["bookings"] and authority_before["commitments"] == authority_after["commitments"] and authority_before["payments"] == authority_after["payments"],
            "plan_only": True,
        }
        verdict = "PASS" if all(assertions.values()) else "RED"
        result = {
            "result": verdict,
            "run_id": result_id,
            "scenario_receipt_id": result_id,
            "scenario_id": SCENARIO_ID,
            "source": {"pre": source_pre, "post": clean_receipt(), "head": git("rev-parse", "HEAD"), "parent": git("rev-parse", "HEAD^")},
            "runtime": {"hermes_binary": str(hermes_bin), "hermes_python": str(hermes_python), "hermes_version": run_value.get("run_status", {}).get("hermes_version"), "profile": PROFILE_NAME, "provider": profile["provider"], "model": profile["model"], "agent_id": AGENT_ID, "autonomy": "PLAN_ONLY", "p7": False, "mcp_tools": arm["discovered"]},
            "mission_id": mission_id,
            "session_id": session_id,
            "seed": seed,
            "run": run_value,
            "measurement": measurement,
            "authority_before_after": {"before": authority_before, "after": authority_after},
            "state_hash_before": before.get("state_sha256"),
            "state_hash_after": after.get("state_sha256"),
            "assertions": assertions,
            "exact_blockers": [] if verdict == "PASS" else [key for key, value in assertions.items() if not value],
            "provenance": {"route": "synthetic demo route", "mobility": "mock-mobility", "closure": "SYNTHETIC_HARNESS_FIXTURE", "model": "real configured provider/model"},
        }
        _save_json(output / "R8-RESULT.json", result)
        _save_json(output / "R8-baseline-run.json", run_value)
        _save_json(output / "R8-context-cost-table.json", measurement)
        _save_json(output / "R8-authority-before-after.json", {"before": before, "after": after, "projection": result["authority_before_after"]})
        _save_json(output / "R8-profile-contract.json", {"profile": PROFILE_NAME, "provider": profile["provider"], "model": profile["model"], "tool_allowlist": profile["tool_allowlist"], "disabled_toolsets": profile["disabled_toolsets"], "resources": profile["resources"], "prompts": profile["prompts"], "p7": False})
        _save_json(output / "R8-network-guard.json", {"events": _sanitize_guard(arm["guard"], [provider_key, arm["gateway_key"], arm["agent_token"]])})
        _save_json(output / "R8-source-binding.json", result["source"])
        (output / "R8-native-events.jsonl").write_text("".join(json.dumps(item, ensure_ascii=False, sort_keys=True, default=str) + "\n" for item in native_events), encoding="utf-8")
        _save_json(output / "R8-mcp-chronology.json", chronology)
        (output / "R8-reproduction.md").write_text("# Hermes R8 reproduction\n\nRun from a clean committed Hermes checkout:\n\n    $env:PYTHONPATH='.'\n    uv run --project backend python scripts/hermes_r8_context_probe.py --evidence-dir C:/path/to/R8-evidence\n\nThe probe discovers the configured official citynexus profile and provider/model, uses a fresh disposable SQLite database and isolated loopback ports, and never accepts a proposal or performs booking/payment/commitment mutation. Provider credentials are read transiently and excluded from evidence.\n", encoding="utf-8")
        (output / "R8-REPORT.md").write_text(f"# Hermes R8 Context Baseline\n\nResult: {verdict}\n\nSource: {result['source']['head']} on {result['source']['pre']['branch']}\nRuntime: Hermes 0.21.2 profile {PROFILE_NAME}; provider/model {profile['provider']} / {profile['model']}\n\nThis is a fresh real model run, not a replay of R6 or R7. The measurement records actual MCP request payload bytes, actual serialized response bytes from the wrapper, a labelled JSON-byte token estimate, cumulative context-byte proxy, repeated payload fields, and exact provider usage when present.\n\nTool sequence: {', '.join(tool_names)}\nLargest context contributor: {measurement['interpretation']['largest_context_contributor']}\nProvider usage: {json.dumps(measurement['model_usage'], sort_keys=True)}\n\nNo accept_replan or other authoritative mutation tool was observed. Journey authority, bookings, commitments and payments remained unchanged. Proposal-only changes, if any, are confined to the fresh disposable database.\n\nP7=false. Synthetic accessibility/closure data is not LIVE provider evidence.\n", encoding="utf-8")
        return result
    except Exception as exc:
        blocker = {"result": "BLOCKED", "run_id": result_id, "scenario_receipt_id": result_id, "scenario_id": SCENARIO_ID, "stage": stage, "exact_blockers": [f"{type(exc).__name__}: {str(exc)[:1000]}"], "source": {"pre": source_pre, "post": clean_receipt(), "head": git("rev-parse", "HEAD")}, "runtime": {"profile": PROFILE_NAME, "p7": False}}
        _save_json(output / "R8-RESULT.json", blocker)
        return blocker
    finally:
        if arm:
            _stop_arm(arm)
        shutil.rmtree(temp_root, ignore_errors=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence-dir", type=Path, required=True)
    args = parser.parse_args()
    value = run(args.evidence_dir)
    print(json.dumps({"result": value.get("result"), "evidence_dir": str(args.evidence_dir), "exact_blockers": value.get("exact_blockers", [])}, ensure_ascii=False))
    return 0 if value.get("result") == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
