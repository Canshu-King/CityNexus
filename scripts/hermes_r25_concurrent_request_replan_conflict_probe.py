"""Hermes R25: concurrent same request_id with different arguments conflicts."""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import os
import tempfile
import uuid
from pathlib import Path
from typing import Any

from scripts import hermes_r17_provider_state_reliability_probe as r17
from scripts.hermes_r6_h11_model_probe import (
    PROFILE_NAME,
    _provider_key,
    _read_profile,
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
from scripts.hermes_r9_mcp_context_probe import _configure_r9_arm


SCENARIO_ID = "hermes-r25-concurrent-request-replan-signature-conflict"
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


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")


def _sha(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _projection(state: dict[str, Any]) -> dict[str, Any]:
    entities = state.get("entities") or {}
    journey = entities.get("journey") or {}
    return {
        "journey": {
            key: journey.get(key)
            for key in (
                "id",
                "status",
                "active_plan_version_id",
                "current_activity_id",
            )
        },
        "proposal_ids": sorted(
            str(row.get("id"))
            for row in entities.get("proposals", [])
            if row.get("id") is not None
        ),
        "plan_ids": sorted(
            str(row.get("id"))
            for row in entities.get("plans", [])
            if row.get("id") is not None
        ),
        "event_ids": sorted(
            str(row.get("id"))
            for row in entities.get("events", [])
            if row.get("id") is not None
        ),
        "idempotency_keys": sorted(
            str(row.get("key"))
            for row in entities.get("idempotency_keys", [])
            if row.get("key") is not None
        ),
    }


def _full_response(value: dict[str, Any] | None) -> bool:
    value = value or {}
    proposals = value.get("proposals")
    return (
        value.get("proposal_contract_version")
        == "hermes-replan-proposal-view.v1"
        and isinstance(proposals, list)
        and bool(proposals)
        and all(
            isinstance(item, dict) and FULL_REPLAN_FIELDS.issubset(item)
            for item in proposals
        )
    )


def _trace_http_status(path: Path) -> int | None:
    for line in path.read_text(encoding="utf-8").splitlines():
        event = json.loads(line)
        if event.get("kind") == "backend.http":
            return int(event["http_status"])
    return None


def _trace_error(path: Path) -> str | None:
    for line in path.read_text(encoding="utf-8").splitlines():
        event = json.loads(line)
        if event.get("kind") == "mcp.error":
            return str(event["error"])
    return None


def _is_mcp_error(call: dict[str, Any]) -> bool:
    return bool(
        call.get("result", {}).get("is_error")
        or call.get("trace_error")
        or (
            call.get("backend_http_status") is not None
            and call.get("backend_http_status") != 200
        )
    )


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
            f"r25-conflict-{trial}",
            hermes_bin,
            hermes_python,
            profile,
            provider_key,
            "full",
            "baseline",
        )
        seed = r17._seed_provider_state(arm["backend"], "DEGRADED")
        warmup_request_id = f"r25-policy-warmup-{trial}-{uuid.uuid4()}"
        warmup_env = dict(arm["mcp_env"])
        warmup_env["CITYNEXUS_HERMES_TOOL_TRACE"] = str(
            output / f"R25-trial-{trial}-policy-warmup.jsonl"
        )
        warmup = _mcp_call(
            hermes_python,
            arm["wrapper"],
            warmup_env,
            "request_replan",
            {
                "request_id": warmup_request_id,
                "journey_id": seed["journey_id"],
                "trigger_event_id": seed["trigger_event_id"],
                "candidate_count": 1,
            },
        )
        before = _r7_state(arm["database"], seed["journey_id"])
        request_id = f"r25-conflict-{trial}-{uuid.uuid4()}"
        arguments = [
            {
                "request_id": request_id,
                "journey_id": seed["journey_id"],
                "trigger_event_id": seed["trigger_event_id"],
                "candidate_count": 1,
            },
            {
                "request_id": request_id,
                "journey_id": seed["journey_id"],
                "trigger_event_id": seed["trigger_event_id"],
                "candidate_count": 2,
            },
        ]
        envs = []
        for suffix in ("a", "b"):
            env = dict(arm["mcp_env"])
            env["CITYNEXUS_HERMES_TOOL_TRACE"] = str(
                output / f"R25-trial-{trial}-call-{suffix}.jsonl"
            )
            envs.append(env)

        def call_one(index: int) -> dict[str, Any]:
            try:
                value = _mcp_call(
                    hermes_python,
                    arm["wrapper"],
                    envs[index],
                    "request_replan",
                    arguments[index],
                )
                return {
                    "index": index,
                    "ok": True,
                    "request": arguments[index],
                    "result": value,
                    "json": _mcp_json(value),
                }
            except Exception as exc:
                return {
                    "index": index,
                    "ok": False,
                    "request": arguments[index],
                    "error": f"{type(exc).__name__}: {exc}",
                }

        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            futures = [executor.submit(call_one, index) for index in (0, 1)]
            calls = [future.result() for future in futures]

        for suffix, call in zip(("a", "b"), calls):
            trace = output / f"R25-trial-{trial}-call-{suffix}.jsonl"
            call["backend_http_status"] = _trace_http_status(trace)
            call["trace_error"] = _trace_error(trace)

        after = _r7_state(arm["database"], seed["journey_id"])
        before_view = _projection(before)
        after_view = _projection(after)
        new_proposals = sorted(
            set(after_view["proposal_ids"]) - set(before_view["proposal_ids"])
        )
        new_plans = sorted(
            set(after_view["plan_ids"]) - set(before_view["plan_ids"])
        )
        new_events = sorted(
            set(after_view["event_ids"]) - set(before_view["event_ids"])
        )
        new_keys = sorted(
            set(after_view["idempotency_keys"])
            - set(before_view["idempotency_keys"])
        )
        request_keys = [
            key
            for key in new_keys
            if key.startswith("agent.request_replan:")
            or key.startswith("replan.generate:")
        ]
        successes = [
            call for call in calls
            if call.get("ok") and not _is_mcp_error(call)
        ]
        failures = [
            call for call in calls
            if not call.get("ok") or _is_mcp_error(call)
        ]
        success_response = successes[0].get("json") if successes else None
        failure_error = (
            failures[0].get("trace_error")
            or " ".join(failures[0].get("result", {}).get("texts", []))
            or failures[0].get("error", "")
            if failures
            else ""
        )
        winning_proposals = (
            success_response.get("proposals", [])
            if isinstance(success_response, dict)
            else []
        )
        winning_proposal_ids = [
            str(item["id"])
            for item in winning_proposals
            if isinstance(item, dict) and item.get("id") is not None
        ]
        winning_plan_ids = [
            str(item["proposed_plan_version_id"])
            for item in winning_proposals
            if isinstance(item, dict)
            and item.get("proposed_plan_version_id") is not None
        ]
        before_proposal_ids = set(before_view["proposal_ids"])
        before_plan_ids = set(before_view["plan_ids"])
        after_proposal_ids = set(after_view["proposal_ids"])
        after_plan_ids = set(after_view["plan_ids"])
        guard = _sanitize_guard(
            arm["guard"],
            [provider_key, arm.get("agent_token", ""), arm.get("gateway_key", "")],
        )
        result = {
            "scenario_id": SCENARIO_ID,
            "trial": trial,
            "request_id": request_id,
            "arguments": arguments,
            "warmup": {
                "request_id": warmup_request_id,
                "is_error": warmup.get("is_error"),
                "proposal_count": len(_mcp_json(warmup).get("proposals", [])),
            },
            "seed": seed,
            "before": before_view,
            "after": after_view,
            "calls": calls,
            "new_identity_sets": {
                "proposals": new_proposals,
                "plans": new_plans,
                "events": new_events,
                "idempotency_keys": new_keys,
            },
            "request_related_idempotency_keys": request_keys,
            "network_guard": guard,
            "assertions": {
                "one_successful_full_response": (
                    len(successes) == 1 and _full_response(success_response)
                ),
                "one_deterministic_409_conflict": (
                    len(failures) == 1
                    and failures[0].get("backend_http_status") == 409
                    and "different request" in failure_error
                ),
                "winning_response_proposals_backed_by_persisted": (
                    set(winning_proposal_ids).issubset(after_proposal_ids)
                ),
                "winning_response_plans_backed_by_persisted": (
                    set(winning_plan_ids).issubset(after_plan_ids)
                ),
                "winning_new_proposals_match_persisted": (
                    sorted(set(winning_proposal_ids) - before_proposal_ids)
                    == sorted(new_proposals)
                ),
                "winning_new_plans_match_persisted": (
                    sorted(set(winning_plan_ids) - before_plan_ids)
                    == sorted(new_plans)
                ),
                "no_new_event": not new_events,
                "journey_authority_unchanged": (
                    before_view["journey"] == after_view["journey"]
                ),
                "request_id_has_two_scoped_keys": (
                    len(request_keys) == 2
                    and sum(
                        key.startswith("agent.request_replan:")
                        for key in request_keys
                    )
                    == 1
                    and sum(
                        key.startswith("replan.generate:")
                        for key in request_keys
                    )
                    == 1
                ),
                "loopback_only": not any(
                    item.get("event") == "blocked_non_loopback"
                    for item in guard
                ),
            },
            "success_response_sha256": _sha(success_response)
            if success_response
            else None,
        }
        _save_json(output / f"R25-trial-{trial}.json", result)
        return result
    finally:
        if arm:
            _stop_arm(arm)


def run(output: Path, trials: int = 3) -> dict[str, Any]:
    output.mkdir(parents=True, exist_ok=True)
    source = clean_receipt()
    hermes_home = Path(os.environ.get("LOCALAPPDATA", "")) / "hermes"
    hermes_bin = hermes_home / "hermes-agent" / ".venv" / "Scripts" / "hermes.exe"
    hermes_python = hermes_home / "hermes-agent" / ".venv" / "Scripts" / "python.exe"
    profile = _read_profile(
        hermes_python,
        hermes_home / "profiles" / PROFILE_NAME / "config.yaml",
    )
    provider_key = _provider_key()
    if not provider_key:
        result = {
            "result": "BLOCKED",
            "scenario_id": SCENARIO_ID,
            "exact_blockers": ["MODEL_NOT_CONFIGURED"],
            "source": source,
        }
        _save_json(output / "R25-RESULT.json", result)
        return result
    temp_root = Path(tempfile.mkdtemp(prefix="citynexus-hermes-r25-"))
    rows = [
        _run_trial(
            temp_root,
            hermes_bin,
            hermes_python,
            profile,
            provider_key,
            trial,
            output,
        )
        for trial in range(1, trials + 1)
    ]
    blockers = [
        f"trial-{row['trial']}:" + ",".join(
            name for name, passed in row["assertions"].items() if not passed
        )
        for row in rows
        if any(not passed for passed in row["assertions"].values())
    ]
    result = {
        "result": "PASS" if not blockers else "RED",
        "scenario_id": SCENARIO_ID,
        "source": {
            "pre": source,
            "post": clean_receipt(),
            "head": git("rev-parse", "HEAD"),
            "parent": git("rev-parse", "HEAD^"),
        },
        "runtime": {
            "profile": PROFILE_NAME,
            "provider": profile["provider"],
            "model": profile["model"],
            "autonomy": "PLAN_ONLY",
            "p7": False,
            "mcp_tools": profile["tool_allowlist"],
        },
        "trial_count": len(rows),
        "trials": [
            {
                "trial": row["trial"],
                "assertions": row["assertions"],
                "new_identity_sets": row["new_identity_sets"],
            }
            for row in rows
        ],
        "exact_blockers": blockers,
    }
    _save_json(output / "R25-RESULT.json", result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence-dir", type=Path, required=True)
    parser.add_argument("--trials", type=int, choices=(1, 2, 3), default=3)
    args = parser.parse_args()
    print(
        json.dumps(
            run(args.evidence_dir, args.trials),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
