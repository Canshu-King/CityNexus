"""Real-model Hermes probe for zero-remaining-budget recovery decisions.

The R13 runner owns the process, trace, and state instrumentation.  This probe
reuses those mechanics with a different server-seeded fixture and its own
receipt names/validator.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import tempfile
import uuid
from pathlib import Path
from typing import Any

import httpx

from scripts import hermes_r13_weather_reliability_probe as r13
from scripts.hermes_r6_h11_model_probe import (
    PROFILE_NAME,
    _event_post,
    _provider_key,
    _read_profile,
    _safe_fields,
    _save_json,
    _schema_and_state,
    clean_receipt,
    git,
)


SCENARIO_ID = "hermes-r14-zero-budget-recovery-reliability"
ARMS = {
    "budget-proposal": {
        "input": (
            "The first place in my current trip is closed and my remaining trip budget "
            "is zero. Inspect the Journey, the closure event, the deterministic "
            "feasibility result, and existing proposals. Request a replacement proposal "
            "only if CityNexus says it fits the budget. Do not accept, book, pay, change "
            "commitments, or claim that anything changed."
        ),
        "instructions": (
            "Use only the current CityNexus MCP tools and choose your own reads. "
            "PLAN_ONLY: request_replan is proposal-only. Treat the server's budget and "
            "hard-constraint result as authoritative; never invent prices or assume a "
            "budget exception. The persisted trigger event ID is supplied as a "
            "server-owned fact. Do not call accept_replan or any booking, payment, "
            "commitment, or approval action; make a bounded decision."
        ),
        "expect_request_replan": True,
    },
    "budget-read-only": {
        "input": (
            "The first place in my current trip is closed and my remaining trip budget "
            "is zero. Give me a read-only report of the Journey budget, the affected "
            "event provenance, current feasibility, and any already persisted proposals. "
            "Do not generate a proposal, accept anything, book, pay, or claim that a "
            "replacement exists unless it was already persisted before this request."
        ),
        "instructions": (
            "Use only CityNexus read tools. Do not call request_replan, accept_replan, "
            "or any mutation tool. Use only server-owned budget and event facts; the "
            "closure is a SYNTHETIC_HARNESS_FIXTURE, not live provider evidence. The "
            "persisted trigger event ID is supplied as a server-owned fact. Make a "
            "bounded read-only report."
        ),
        "expect_request_replan": False,
    },
}


def _seed_budget(backend: Any) -> dict[str, Any]:
    transitions: list[dict[str, Any]] = []
    with httpx.Client(base_url=backend.base_url, timeout=120, trust_env=False) as client:
        reset = client.post("/api/v1/demo/reset")
        if reset.status_code != 200:
            raise RuntimeError(f"RESET/SEED HTTP {reset.status_code}: {reset.text[:1000]}")
        journey_id = str(reset.json()["journey_id"])
        transitions.append({"transition": "RESET -> SEED", "journey_id": journey_id})
        generated = client.post(
            f"/api/v1/journeys/{journey_id}/plans/generate", json={"candidate_count": 1}
        )
        if generated.status_code != 201 or not generated.json():
            raise RuntimeError(f"seed plan generation HTTP {generated.status_code}: {generated.text[:1000]}")
        plan = generated.json()[0]
        plan_id = str(plan["id"])
        plan_cost = int((plan.get("total_cost") or {}).get("amount_minor") or 0)
        currency = str((plan.get("total_cost") or {}).get("currency") or "CNY")
        selected = client.post(f"/api/v1/journeys/{journey_id}/plans/{plan_id}/select")
        if selected.status_code != 200:
            raise RuntimeError(f"seed plan select HTTP {selected.status_code}: {selected.text[:1000]}")
        started = client.post(f"/api/v1/journeys/{journey_id}/start")
        if started.status_code != 200:
            raise RuntimeError(f"seed journey start HTTP {started.status_code}: {started.text[:1000]}")
        journey = client.get(f"/api/v1/journeys/{journey_id}").json()
        activity_id = str(
            started.json().get("current_activity_id")
            or selected.json().get("current_activity_id")
            or journey.get("current_activity_id")
            or ""
        )
        if not activity_id:
            raise RuntimeError("budget seed start did not identify current activity")
        budget = client.patch(
            f"/api/v1/journeys/{journey_id}",
            json={"budget": {"amount_minor": plan_cost, "currency": currency}},
        )
        if budget.status_code != 200:
            raise RuntimeError(f"budget pressure update HTTP {budget.status_code}: {budget.text[:1000]}")
        plan_id = str(budget.json().get("active_plan_version_id") or plan_id)
        state = _schema_and_state(backend.database, journey_id)
        activities = [
            item for item in state["entities"]["activities"]
            if item.get("plan_version_id") == plan_id
        ]
        if len(activities) < 2:
            raise RuntimeError("budget seed does not contain multiple activities")
        transitions.append({
            "transition": "PLAN_SELECTED -> ACTIVE -> ZERO_REMAINING_BUDGET",
            "active_plan_version_id": plan_id,
            "plan_cost_minor": plan_cost,
            "budget_minor": plan_cost,
            "remaining_budget_minor": 0,
        })
        status, event = _event_post(
            backend.base_url,
            journey_id,
            {
                "event_type": "CLOSURE",
                "severity": "MAJOR",
                "provenance": "SIMULATED",
                "affected_activity_id": activity_id,
                "payload": {
                    "kind": "SYNTHETIC_CLOSURE_FIXTURE",
                    "reason": "R14 isolated zero-budget recovery fixture",
                },
            },
        )
        if status != 201:
            raise RuntimeError(f"synthetic closure injection HTTP {status}: {event}")
        transitions.append({"transition": "ACTIVE -> SIMULATED_CLOSURE_EVENT", "event_id": event["id"]})
        return {
            "journey_id": journey_id,
            "active_plan_version_id": plan_id,
            "current_activity_id": activity_id,
            "trigger_event_id": str(event["id"]),
            "transitions": transitions,
            "plan_cost_minor": plan_cost,
            "budget_minor": plan_cost,
            "remaining_budget_minor": 0,
            "activity_count_on_active_plan": len(activities),
            "event": _safe_fields(event, (
                "id", "journey_id", "provider_key", "provenance", "event_type",
                "severity", "status", "affected_activity_id", "payload",
            )),
            "budget_provenance_contract": {
                "budget_source": "server-owned Journey PATCH equal to selected plan cost",
                "remaining_budget_minor": 0,
                "fixture_label": "SYNTHETIC_HARNESS_FIXTURE",
                "live_provider_evidence": False,
            },
        }


def _budget_fixture_truth(seed: dict[str, Any]) -> bool:
    event = seed.get("event") or {}
    return (
        event.get("event_type") == "CLOSURE"
        and event.get("provenance") == "SIMULATED"
        and event.get("provider_key") == "demo-simulator"
        and (event.get("payload") or {}).get("kind") == "SYNTHETIC_CLOSURE_FIXTURE"
        and seed.get("remaining_budget_minor") == 0
        and seed.get("budget_provenance_contract", {}).get("live_provider_evidence") is False
    )


def _proposal_budget_truth(replan: dict[str, Any], mutation_requests: list[Any]) -> bool:
    return (
        not mutation_requests
        and (
            (
                replan["response_count"] > 0
                and replan["full_contract_observed"]
                and replan["all_server_proposal_ids_persisted"]
            )
            or replan["response_count"] == 0
        )
    )


def _read_only_budget_truth(
    before: dict[str, Any], after: dict[str, Any], replan: dict[str, Any],
    mutation_requests: list[Any],
) -> bool:
    return (
        replan["response_count"] == 0
        and not mutation_requests
        and before["entities"].get("proposals", []) == after["entities"].get("proposals", [])
        and before["entities"].get("plans", []) == after["entities"].get("plans", [])
        and before["entities"].get("events", []) == after["entities"].get("events", [])
    )


def _run_trial(
    temp_root: Path, hermes_bin: Path, hermes_python: Path, profile: dict[str, Any],
    provider_key: str, arm_name: str, trial: int, output: Path,
) -> dict[str, Any]:
    # Reuse R13's tested lifecycle instrumentation while swapping only the
    # fixture/arm predicates. The R13 file-prefixes are renamed immediately so
    # the R14 receipt remains independently auditable.
    original = {
        "SCENARIO_ID": r13.SCENARIO_ID,
        "ARMS": r13.ARMS,
        "_seed_weather": r13._seed_weather,
        "_weather_fixture_truth": r13._weather_fixture_truth,
        "_proposal_weather_truth": r13._proposal_weather_truth,
        "_read_only_weather_truth": r13._read_only_weather_truth,
    }
    r13.SCENARIO_ID = SCENARIO_ID
    r13.ARMS = ARMS
    r13._seed_weather = _seed_budget
    r13._weather_fixture_truth = _budget_fixture_truth
    r13._proposal_weather_truth = _proposal_budget_truth
    r13._read_only_weather_truth = _read_only_budget_truth
    try:
        row = r13._run_trial(
            temp_root, hermes_bin, hermes_python, profile, provider_key,
            arm_name, trial, output,
        )
        row["scenario_id"] = SCENARIO_ID
        row["assertions"]["budget_fixture_truth"] = row["assertions"].pop("weather_fixture_truth")
        old = output / f"R13-{arm_name}-trial-{trial}"
        new = output / f"R14-{arm_name}-trial-{trial}"
        for path in output.glob(old.name + "*"):
            path.rename(output / path.name.replace(old.name, new.name, 1))
        _save_json(new.with_suffix(".json"), row)
        return row
    finally:
        for key, value in original.items():
            setattr(r13, key, value)


def _stats(items: list[dict[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for field, getter in {
        "total_tokens": lambda item: (item.get("usage") or {}).get("total_tokens"),
        "mcp_call_count": lambda item: item.get("mcp_call_count"),
        "mcp_response_bytes": lambda item: (item.get("measurement") or {}).get("cumulative_tool_response_bytes"),
    }.items():
        values = sorted(int(value) for item in items if (value := getter(item)) is not None)
        result[field] = {
            "values": values, "min": min(values) if values else None,
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
            "result": "BLOCKED", "scenario_id": SCENARIO_ID,
            "exact_blockers": ["MODEL_NOT_CONFIGURED"],
            "source": {"pre": source_before, "post": clean_receipt()},
        }
        _save_json(output / "R14-RESULT.json", result)
        return result
    temp_root = Path(tempfile.mkdtemp(prefix="citynexus-hermes-r14-"))
    try:
        arms: dict[str, dict[str, Any]] = {}
        model_runs: list[dict[str, Any]] = []
        for arm_name in ARMS:
            rows = [
                _run_trial(temp_root, hermes_bin, hermes_python, profile, provider_key, arm_name, trial, output)
                for trial in range(1, trials + 1)
            ]
            arms[arm_name] = {"trials": rows, "stats": _stats(rows)}
            model_runs.extend({
                "arm": arm_name, "trial": row.get("trial"), "run_id": row.get("run_id"),
                "mission_id": row.get("mission_id"), "session_id": row.get("session_id"),
                "status": row.get("status"), "usage": row.get("usage"),
                "mcp_call_count": row.get("mcp_call_count"),
            } for row in rows)
            _save_json(output / f"R14-{arm_name}-trials.json", arms[arm_name])
        failures = [
            f"{arm_name}-trial-{row.get('trial')}:" + ",".join(
                key for key, value in row.get("assertions", {}).items() if not value
            )
            for arm_name, arm in arms.items() for row in arm["trials"]
            if any(not value for value in row.get("assertions", {}).values())
        ]
        result = {
            "result": "PASS" if not failures else "RED",
            "scenario_id": SCENARIO_ID,
            "source": {
                "pre": source_before, "post": clean_receipt(),
                "head": git("rev-parse", "HEAD"), "parent": git("rev-parse", "HEAD^"),
            },
            "runtime": {
                "profile": PROFILE_NAME, "provider": profile["provider"], "model": profile["model"],
                "tool_allowlist": profile["tool_allowlist"], "autonomy": "PLAN_ONLY", "p7": False,
                "database": "fresh disposable SQLite per arm/trial",
                "network": "CityNexus/MCP loopback; configured model provider only",
                "budget_provenance": "server-owned zero remaining budget; closure is SYNTHETIC_HARNESS_FIXTURE",
            },
            "arms": {name: {"stats": arm["stats"], "trials": len(arm["trials"])} for name, arm in arms.items()},
            "exact_blockers": failures,
            "model_runs": model_runs,
        }
        _save_json(output / "R14-RESULT.json", result)
        _save_json(output / "R14-profile-contract.json", {
            "profile": PROFILE_NAME, "provider": profile["provider"], "model": profile["model"],
            "tool_allowlist": profile["tool_allowlist"], "disabled_toolsets": profile["disabled_toolsets"],
            "resources": profile["resources"], "prompts": profile["prompts"], "p7": False,
        })
        return result
    finally:
        shutil.rmtree(temp_root, ignore_errors=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence-dir", type=Path, required=True)
    parser.add_argument("--trials", type=int, default=2, choices=range(2, 4))
    args = parser.parse_args()
    result = run(args.evidence_dir, args.trials)
    print(json.dumps({
        "result": result.get("result"), "scenario_id": result.get("scenario_id"),
        "evidence_dir": str(args.evidence_dir), "exact_blockers": result.get("exact_blockers", []),
    }, ensure_ascii=False, sort_keys=True))
    return 0 if result.get("result") == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
