"""Hermes R21: real-model request_replan retry must be exactly once."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import tempfile
import uuid
from pathlib import Path
from typing import Any

from scripts import hermes_r17_provider_state_reliability_probe as r17
from scripts.hermes_r6_h11_model_probe import (
    PROFILE_NAME,
    _gateway_run,
    _provider_key,
    _read_profile,
    _read_trace,
    _save_json,
    clean_receipt,
    git,
)
from scripts.hermes_r7_human_approval_probe import (
    _mcp_call,
    _mcp_json,
    _r7_state,
    _sanitize_guard,
    _stop_arm,
)
from scripts.hermes_r9_mcp_context_probe import MUTATION_TOOLS, _configure_r9_arm, _read_measurement


SCENARIO_ID = "hermes-r21-request-replan-retry-reliability"
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
SEMANTIC_RESPONSE_FIELDS = (
    "tool",
    "decision",
    "reason_codes",
    "policy_version",
    "request_id",
    "proposal_contract_version",
    "proposal",
    "proposals",
    "proposal_views",
)


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str
    ).encode("utf-8")


def _sha256(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _semantic_response(value: dict[str, Any] | None) -> dict[str, Any]:
    value = value or {}
    return {key: value.get(key) for key in SEMANTIC_RESPONSE_FIELDS if key in value}


def _identity_projection(state: dict[str, Any]) -> dict[str, Any]:
    entities = state.get("entities") or {}
    journey = entities.get("journey") or {}
    plans = [
        {
            "id": str(row.get("id")),
            "status": row.get("status"),
            "journey_id": row.get("journey_id"),
        }
        for row in entities.get("plans", [])
        if row.get("id") is not None
    ]
    events = [
        {
            "id": str(row.get("id")),
            "status": row.get("status"),
            "event_type": row.get("event_type"),
        }
        for row in entities.get("events", [])
        if row.get("id") is not None
    ]
    return {
        "journey": {
            key: journey.get(key)
            for key in ("id", "status", "active_plan_version_id", "current_activity_id")
        },
        "proposal_ids": sorted(
            str(row.get("id")) for row in entities.get("proposals", []) if row.get("id") is not None
        ),
        "plans": sorted(plans, key=lambda row: (row["id"], str(row.get("status")))),
        "events": sorted(events, key=lambda row: (row["id"], str(row.get("status")))),
        "idempotency_keys": sorted(
            str(row.get("key"))
            for row in entities.get("idempotency_keys", [])
            if row.get("key") is not None
        ),
    }


def _full_contract(response: dict[str, Any] | None) -> bool:
    response = response or {}
    proposals = response.get("proposals")
    views = response.get("proposal_views")
    return (
        response.get("proposal_contract_version") == "hermes-replan-proposal-view.v1"
        and isinstance(proposals, list)
        and bool(proposals)
        and isinstance(views, list)
        and bool(views)
        and all(isinstance(item, dict) and FULL_REPLAN_FIELDS.issubset(item) for item in proposals)
    )


def _first_request_and_response(trace: list[dict[str, Any]]) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    request = next(
        (
            item
            for item in trace
            if item.get("kind") == "mcp.request" and item.get("tool_name") == "request_replan"
        ),
        None,
    )
    if request is None:
        return None, None
    request_id = request.get("request_id")
    response = next(
        (
            item.get("response")
            for item in trace
            if item.get("kind") == "mcp.response"
            and item.get("tool_name") == "request_replan"
            and item.get("request_id") == request_id
            and isinstance(item.get("response"), dict)
        ),
        None,
    )
    return request, response


def _run_trial(
    temp_root: Path,
    hermes_bin: Path,
    hermes_python: Path,
    profile: dict[str, Any],
    provider_key: str,
    trial: int,
    output: Path,
) -> dict[str, Any]:
    arm = None
    try:
        arm = _configure_r9_arm(
            temp_root,
            f"r21-proposal-retry-{trial}",
            hermes_bin,
            hermes_python,
            profile,
            provider_key,
            "full",
            "baseline",
        )
        seed = r17._seed_provider_state(arm["backend"], "DEGRADED")
        before = _r7_state(arm["database"], seed["journey_id"])
        mission_id = str(uuid.uuid4())
        session_id = f"citynexus-{seed['journey_id']}-r21-{trial}-{mission_id}"
        user_input = (
            "A simulated mobility provider warning affects my current trip. Inspect the "
            "actual Journey and closure context, then ask CityNexus for a safe replacement "
            "proposal if feasible. Do not accept, book, pay, change commitments, or claim "
            "that anything changed. Journey ID: " + seed["journey_id"]
        )
        instructions = (
            "Use only current CityNexus MCP tools and choose your own reads. This is "
            "PLAN_ONLY. The provider state is a SYNTHETIC_HARNESS_FIXTURE, not LIVE or "
            "PROVIDER_VERIFIED evidence. You may call request_replan once if the server "
            "says it is feasible, but do not call accept_replan or any booking, payment, "
            "commitment, approval, replace, or reschedule tool. Use only server-owned facts. "
            "If request_replan returns successfully, do not call it again. Journey ID: "
            + seed["journey_id"]
            + " Server-owned trigger event ID: "
            + seed["trigger_event_id"]
        )
        run = _gateway_run(
            gateway=arm["gateway"],
            backend=arm["backend"],
            journey_id=seed["journey_id"],
            session_id=session_id,
            mission_id=mission_id,
            run_key=f"r21-proposal-retry-{trial}-{mission_id}",
            user_input=user_input,
            instructions=instructions,
            trace_path=arm["trace_path"],
            tee=arm["tee"],
            api_headers=arm["headers"],
            timeout_seconds=360,
        )
        after_model = _r7_state(arm["database"], seed["journey_id"])
        trace = _read_trace(arm["trace_path"])
        model_request, original_response = _first_request_and_response(trace)
        retry_call: dict[str, Any] | None = None
        retry_response: dict[str, Any] | None = None
        retry_error: str | None = None
        if model_request is not None:
            try:
                # Deliberately discard the first recorded delivery and replay the exact
                # request through a fresh MCP stdio client against the same DB.
                retry_call = _mcp_call(
                    hermes_python,
                    arm["wrapper"],
                    arm["mcp_env"],
                    "request_replan",
                    dict(model_request.get("request") or {}),
                )
                retry_response = _mcp_json(retry_call)
            except Exception as exc:  # preserve the exact retry blocker in evidence
                retry_error = f"{type(exc).__name__}: {exc}"
        after_retry = _r7_state(arm["database"], seed["journey_id"])
        measurement = _read_measurement(trace, run)
        guard = _sanitize_guard(
            arm["guard"], [provider_key, arm.get("agent_token", ""), arm.get("gateway_key", "")]
        )
        before_identity = _identity_projection(before)
        model_identity = _identity_projection(after_model)
        retry_identity = _identity_projection(after_retry)
        model_request_payload = model_request.get("request") if model_request else None
        dangerous_requests = [
            item.get("tool_name")
            for item in trace
            if item.get("kind") == "mcp.request" and item.get("tool_name") in MUTATION_TOOLS
        ]
        retry_semantic_match = bool(
            original_response
            and retry_response
            and _semantic_response(original_response) == _semantic_response(retry_response)
        )
        model_proposal_ids = sorted(
            set(model_identity["proposal_ids"]) - set(before_identity["proposal_ids"])
        )
        retry_new_proposal_ids = sorted(
            set(retry_identity["proposal_ids"]) - set(model_identity["proposal_ids"])
        )
        retry_new_plan_ids = sorted(
            {row["id"] for row in retry_identity["plans"]}
            - {row["id"] for row in model_identity["plans"]}
        )
        retry_new_event_ids = sorted(
            {row["id"] for row in retry_identity["events"]}
            - {row["id"] for row in model_identity["events"]}
        )
        retry_new_idempotency_keys = sorted(
            set(retry_identity["idempotency_keys"])
            - set(model_identity["idempotency_keys"])
        )
        item = {
            "scenario_id": SCENARIO_ID,
            "arm": "real-model-exact-request-retry",
            "trial": trial,
            "run_id": run.get("run_id"),
            "mission_id": mission_id,
            "session_id": session_id,
            "status": run.get("status"),
            "run_status": run.get("run_status"),
            "submission_http_status": run.get("submission_http_status"),
            "submission_response": run.get("submission_response"),
            "exact_blocker": run.get("exact_blocker"),
            "actual_invocation_observed": bool(run.get("actual_invocation_observed")),
            "native_event_stream_event_count": len(run.get("native_event_stream") or []),
            "mcp_call_count": len(run.get("mcp_calls") or []),
            "usage": run.get("usage"),
            "output": run.get("output"),
            "tool_sequence": measurement.get("tool_sequence", []),
            "measurement": {key: value for key, value in measurement.items() if key != "calltool_records"},
            "seed": seed,
            "before": before,
            "after_model": after_model,
            "after_retry": after_retry,
            "identity_sets": {
                "before": before_identity,
                "after_model": model_identity,
                "after_retry": retry_identity,
                "model_new_proposal_ids": model_proposal_ids,
                "retry_new_proposal_ids": retry_new_proposal_ids,
                "retry_new_plan_ids": retry_new_plan_ids,
                "retry_new_event_ids": retry_new_event_ids,
                "retry_new_idempotency_keys": retry_new_idempotency_keys,
            },
            "model_request": model_request,
            "original_response": original_response,
            "retry_call": retry_call,
            "retry_response": retry_response,
            "retry_error": retry_error,
            "network_guard": guard,
            "assertions": {
                "real_model": bool(run.get("actual_invocation_observed")),
                "completed": run.get("status") == "completed",
                "request_replan_observed": model_request is not None,
                "initial_full_contract": _full_contract(original_response),
                "retry_success": bool(retry_response) and not bool(retry_call and retry_call.get("is_error")),
                "retry_full_contract": _full_contract(retry_response),
                "same_request_id": bool(
                    model_request_payload
                    and model_request_payload.get("request_id")
                    and retry_response
                    and retry_response.get("request_id") == model_request_payload.get("request_id")
                ),
                "same_agent_identity": bool(
                    (model_request_payload or {}).get("agent_id", arm["mcp_env"].get("CITYNEXUS_AGENT_ID"))
                    == arm["mcp_env"].get("CITYNEXUS_AGENT_ID")
                ),
                "semantic_match": retry_semantic_match,
                "no_duplicate_proposal": not retry_new_proposal_ids,
                "no_duplicate_plan": not retry_new_plan_ids,
                "no_duplicate_event": not retry_new_event_ids,
                "no_duplicate_idempotency_key": not retry_new_idempotency_keys,
                "journey_authority_unchanged": before_identity["journey"] == retry_identity["journey"],
                "no_mutation_tool": not dangerous_requests,
                "no_accept_replan": "accept_replan" not in dangerous_requests,
                "single_active_plan": sum(row.get("status") == "ACTIVE" for row in after_retry["entities"].get("plans", [])) == 1,
                "loopback_guard_installed": any(entry.get("event") == "guard_installed" for entry in guard),
                "no_non_loopback_connection_attempt": not any(entry.get("event") == "blocked_non_loopback" for entry in guard),
            },
        }
        prefix = output / f"R21-real-model-exact-request-retry-trial-{trial}"
        _save_json(prefix.with_suffix(".json"), item)
        _save_json(prefix.with_name(prefix.name + "-native-events.json"), run.get("native_event_stream") or [])
        _save_json(prefix.with_name(prefix.name + "-network-guard.json"), guard)
        _save_json(prefix.with_name(prefix.name + "-before.json"), before)
        _save_json(prefix.with_name(prefix.name + "-after-model.json"), after_model)
        _save_json(prefix.with_name(prefix.name + "-after-retry.json"), after_retry)
        _save_json(prefix.with_name(prefix.name + "-retry.json"), {"call": retry_call, "response": retry_response, "error": retry_error})
        prefix.with_name(prefix.name + "-chronology.json").write_text(
            json.dumps(trace, ensure_ascii=False, sort_keys=True, indent=2, default=str) + "\n",
            encoding="utf-8",
        )
        return item
    finally:
        if arm:
            _stop_arm(arm)


def _stats(items: list[dict[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for field, getter in {
        "total_tokens": lambda item: (item.get("usage") or {}).get("total_tokens"),
        "mcp_call_count": lambda item: item.get("mcp_call_count"),
        "mcp_response_bytes": lambda item: (item.get("measurement") or {}).get("cumulative_tool_response_bytes"),
    }.items():
        values = sorted(int(value) for item in items if (value := getter(item)) is not None)
        result[field] = {
            "values": values,
            "min": min(values) if values else None,
            "max": max(values) if values else None,
            "median": values[len(values) // 2] if values else None,
        }
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
        result = {
            "result": "BLOCKED",
            "scenario_id": SCENARIO_ID,
            "exact_blockers": ["MODEL_NOT_CONFIGURED"],
            "source": {"pre": source_before, "post": clean_receipt()},
        }
        _save_json(output / "R21-RESULT.json", result)
        return result
    temp_root = Path(tempfile.mkdtemp(prefix="citynexus-hermes-r21-"))
    try:
        rows = [
            _run_trial(temp_root, hermes_bin, hermes_python, profile, provider_key, trial, output)
            for trial in range(1, trials + 1)
        ]
        failures = [
            f"trial-{row.get('trial')}:" + ",".join(
                key for key, value in row.get("assertions", {}).items() if not value
            )
            for row in rows
            if any(not value for value in row.get("assertions", {}).values())
        ]
        result = {
            "result": "PASS" if not failures else "RED",
            "scenario_id": SCENARIO_ID,
            "source": {
                "pre": source_before,
                "post": clean_receipt(),
                "head": git("rev-parse", "HEAD"),
                "parent": git("rev-parse", "HEAD^"),
            },
            "runtime": {
                "profile": PROFILE_NAME,
                "provider": profile["provider"],
                "model": profile["model"],
                "tool_allowlist": profile["tool_allowlist"],
                "autonomy": "PLAN_ONLY",
                "p7": False,
                "database": "fresh disposable SQLite per trial; retry uses the same DB",
                "agent_id": "hermes-test",
                "network": "CityNexus/MCP loopback; configured model provider only",
                "provider_state_provenance": "SYNTHETIC_HARNESS_FIXTURE; not LIVE/provider evidence",
            },
            "retry_boundary": {
                "method": "discard first recorded delivery, then exact MCP request replay",
                "same_request_id_required": True,
                "same_canonical_arguments_required": True,
                "same_agent_identity_required": True,
                "same_disposable_database_required": True,
                "new_proposal_forbidden": True,
                "new_plan_forbidden": True,
                "new_event_forbidden": True,
                "new_idempotency_key_forbidden": True,
                "backend_api_unchanged": True,
                "proposal_authority_unchanged": True,
                "request_replan_timeout_seconds": 120.0,
            },
            "arms": {"real-model-exact-request-retry": {"trials": len(rows), "stats": _stats(rows)}},
            "exact_blockers": failures,
            "model_runs": [
                {
                    "trial": row.get("trial"),
                    "run_id": row.get("run_id"),
                    "mission_id": row.get("mission_id"),
                    "session_id": row.get("session_id"),
                    "status": row.get("status"),
                    "usage": row.get("usage"),
                    "mcp_call_count": row.get("mcp_call_count"),
                }
                for row in rows
            ],
        }
        _save_json(output / "R21-RESULT.json", result)
        _save_json(
            output / "R21-profile-contract.json",
            {
                "profile": PROFILE_NAME,
                "provider": profile["provider"],
                "model": profile["model"],
                "tool_allowlist": profile["tool_allowlist"],
                "disabled_toolsets": profile["disabled_toolsets"],
                "resources": profile["resources"],
                "prompts": profile["prompts"],
                "p7": False,
            },
        )
        return result
    finally:
        shutil.rmtree(temp_root, ignore_errors=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence-dir", type=Path, required=True)
    parser.add_argument("--trials", type=int, default=2, choices=range(1, 4))
    args = parser.parse_args()
    result = run(args.evidence_dir, args.trials)
    print(
        json.dumps(
            {
                "result": result.get("result"),
                "scenario_id": result.get("scenario_id"),
                "evidence_dir": str(args.evidence_dir),
                "exact_blockers": result.get("exact_blockers", []),
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0 if result.get("result") == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
