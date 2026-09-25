"""Hermes R24: concurrent identical request_replan calls share one result."""

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


SCENARIO_ID = "hermes-r24-concurrent-request-replan-idempotency"
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


def _response(call_result: dict[str, Any]) -> dict[str, Any] | None:
    return _mcp_json(call_result)


def _full_response(value: dict[str, Any] | None) -> bool:
    value = value or {}
    proposals = value.get("proposals")
    views = value.get("proposal_views")
    return (
        value.get("proposal_contract_version")
        == "hermes-replan-proposal-view.v1"
        and isinstance(proposals, list)
        and bool(proposals)
        and isinstance(views, list)
        and bool(views)
        and all(
            isinstance(item, dict) and FULL_REPLAN_FIELDS.issubset(item)
            for item in proposals
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
            f"r24-concurrent-{trial}",
            hermes_bin,
            hermes_python,
            profile,
            provider_key,
            "full",
            "baseline",
        )
        seed = r17._seed_provider_state(arm["backend"], "DEGRADED")
        before = _r7_state(arm["database"], seed["journey_id"])
        request_id = f"r24-concurrent-{trial}-{uuid.uuid4()}"
        arguments = {
            "request_id": request_id,
            "journey_id": seed["journey_id"],
            "trigger_event_id": seed["trigger_event_id"],
            "candidate_count": 1,
        }
        envs = []
        for suffix in ("a", "b"):
            env = dict(arm["mcp_env"])
            env["CITYNEXUS_HERMES_TOOL_TRACE"] = str(
                output / f"R24-trial-{trial}-call-{suffix}.jsonl"
            )
            envs.append(env)

        def call_one(env: dict[str, str]) -> dict[str, Any]:
            try:
                return {
                    "ok": True,
                    "result": _mcp_call(
                        hermes_python,
                        arm["wrapper"],
                        env,
                        "request_replan",
                        arguments,
                    ),
                }
            except Exception as exc:
                return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}

        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            futures = [executor.submit(call_one, env) for env in envs]
            calls = [future.result() for future in futures]

        after = _r7_state(arm["database"], seed["journey_id"])
        before_view = _projection(before)
        after_view = _projection(after)
        responses = [
            _response(item["result"]) if item.get("ok") else None
            for item in calls
        ]
        response_proposal_ids = [
            [
                str(row.get("id"))
                for row in (value or {}).get("proposals", [])
            ]
            for value in responses
        ]
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
        semantic_equal = bool(
            responses[0]
            and responses[1]
            and _sha(responses[0]) == _sha(responses[1])
        )
        guard = _sanitize_guard(
            arm["guard"],
            [provider_key, arm.get("agent_token", ""), arm.get("gateway_key", "")],
        )
        result = {
            "scenario_id": SCENARIO_ID,
            "trial": trial,
            "request": {
                "request_id": request_id,
                "journey_id": seed["journey_id"],
                "trigger_event_id": seed["trigger_event_id"],
                "candidate_count": 1,
            },
            "seed": seed,
            "before": before_view,
            "after": after_view,
            "calls": calls,
            "response_proposal_ids": response_proposal_ids,
            "response_hashes": [
                _sha(value) if value else None for value in responses
            ],
            "new_identity_sets": {
                "proposals": new_proposals,
                "plans": new_plans,
                "events": new_events,
                "idempotency_keys": new_keys,
            },
            "request_related_idempotency_keys": request_keys,
            "network_guard": guard,
            "assertions": {
                "both_mcp_calls_succeeded": all(
                    item.get("ok") and not item["result"].get("is_error")
                    for item in calls
                ),
                "both_responses_full_contract": all(
                    _full_response(value) for value in responses
                ),
                "same_proposal_order_and_identity": (
                    len(response_proposal_ids) == 2
                    and response_proposal_ids[0] == response_proposal_ids[1]
                    and bool(response_proposal_ids[0])
                ),
                "exactly_one_new_proposal": len(new_proposals) == 1,
                "exactly_one_new_plan": len(new_plans) == 1,
                "no_new_event": not new_events,
                "same_semantic_response": semantic_equal,
                "journey_authority_unchanged": (
                    before_view["journey"] == after_view["journey"]
                ),
                "request_id_has_two_scoped_keys": (
                    len(request_keys) == 2
                    and sum(key.startswith("agent.request_replan:") for key in request_keys) == 1
                    and sum(key.startswith("replan.generate:") for key in request_keys) == 1
                ),
                "loopback_only": not any(
                    item.get("event") == "blocked_non_loopback"
                    for item in guard
                ),
            },
        }
        _save_json(output / f"R24-trial-{trial}.json", result)
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
        _save_json(output / "R24-RESULT.json", result)
        return result
    temp_root = Path(tempfile.mkdtemp(prefix="citynexus-hermes-r24-"))
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
                "response_proposal_ids": row["response_proposal_ids"],
            }
            for row in rows
        ],
        "exact_blockers": blockers,
    }
    _save_json(output / "R24-RESULT.json", result)
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
