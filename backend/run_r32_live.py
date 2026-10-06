"""R32 concurrent recovery-mesh live strike.

This harness creates a fresh Journey through the normal product surfaces, injects
two materially different server-owned provider replay shocks while two independent
configured Hermes/WB2api AgentRuns are in flight, and records durable evidence.
It never supplies model tool calls or authority decisions.  The only test seam is
an external-response barrier around the real provider request so Shock B can land
after Agent A has a durable RUNNING/R1 envelope but before either provider call.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from run_r28_live import BACKEND, _api_setup, _configure


def _jsonable(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_jsonable(item) for item in value]
    return str(value)


def _source_receipt() -> dict[str, Any]:
    """Bind the live artifact to the exact source state that executed it."""

    repo = BACKEND.parent

    def git(*args: str) -> str:
        completed = subprocess.run(
            ["git", "-C", str(repo), *args],
            check=True,
            capture_output=True,
            text=True,
        )
        return completed.stdout.strip()

    tracked = [
        "backend/run_r32_live.py",
        "backend/app/agent/runtime.py",
        "backend/app/recovery_epoch.py",
        "backend/app/agent/gateway.py",
        "backend/scripts/r32_machine_verdict.py",
    ]
    hashes: dict[str, str] = {}
    for relative in tracked:
        raw = (repo / relative).read_bytes()
        hashes[relative] = hashlib.sha256(raw).hexdigest()
    dirty = git("status", "--porcelain", "--untracked-files=no")
    return {
        "git_head": git("rev-parse", "HEAD"),
        "tracked_dirty_before_strike": bool(dirty),
        "tracked_dirty_paths_before_strike": dirty.splitlines(),
        "source_sha256": hashes,
    }


def _fixture_shock(journey_id: str, *, target_place_id: str | None, label: str) -> dict[str, Any]:
    from app.agent.signal_pipeline import refresh_demo_signals, set_fixture_state
    from app.db.models import Journey
    from app.db.session import SessionLocal

    with SessionLocal() as session:
        journey = session.get(Journey, journey_id)
        if journey is None:
            raise RuntimeError(f"Journey disappeared before {label}")
        fixture = set_fixture_state(
            session,
            journey,
            state="DISRUPTED",
            payload={
                "r32_live_strike": label,
                "purpose": "AUTONOMOUS_RECOVERY_MESH_CONCURRENCY",
                **({"target_place_id": target_place_id} if target_place_id else {}),
            },
        )
        signals = refresh_demo_signals(session, journey)
        session.commit()
        return {
            "label": label,
            "fixture": {
                "state": fixture.state,
                "revision": fixture.revision,
                "payload": json.loads(fixture.payload_json or "{}"),
            },
            "signals": signals.to_dict(),
        }


def _open_epoch(journey_id: str) -> dict[str, Any]:
    from app.db.models import Journey
    from app.db.session import SessionLocal
    from app.recovery_epoch import ensure_recovery_epoch

    with SessionLocal() as session:
        journey = session.get(Journey, journey_id)
        if journey is None:
            raise RuntimeError("Journey disappeared while opening recovery epoch")
        epoch = ensure_recovery_epoch(session, journey)
        session.commit()
        return {
            "id": epoch.id,
            "generation": epoch.generation,
            "status": epoch.status,
            "fingerprint": epoch.recovery_reality_fingerprint,
            "triggering_event_ids": json.loads(epoch.triggering_event_ids_json or "[]"),
        }


def _run_command(journey_id: str, command: str, box: dict[str, Any], key: str) -> None:
    from fastapi.testclient import TestClient
    from app.main import app

    try:
        response = TestClient(app).post(
            f"/api/v1/journeys/{journey_id}/agent/commands",
            json={"command": command, "requested_autonomy": "EXECUTE_WITHIN_BOUNDS"},
        )
        try:
            payload = response.json()
        except ValueError:
            payload = {"text": response.text}
        box[key] = {"status": response.status_code, "payload": payload}
    except Exception as exc:  # preserve the failure in the machine artifact
        box[key] = {"exception": type(exc).__name__, "error": str(exc)}


def _poll_runs(journey_id: str, *, want: int, timeout: float = 45.0) -> list[dict[str, Any]]:
    from sqlalchemy import select
    from app.db.models import AgentRun
    from app.db.session import SessionLocal

    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        with SessionLocal() as session:
            rows = session.scalars(
                select(AgentRun)
                .where(AgentRun.journey_id == journey_id)
                .order_by(AgentRun.created_at.asc(), AgentRun.id.asc())
            ).all()
            payload = [
                {
                    "id": row.id,
                    "mission_id": row.mission_id,
                    "status": row.status,
                    "provider_key": row.provider_key,
                    "model_key": row.model_key,
                    "recovery_epoch_id": row.recovery_epoch_id,
                    "failure_reason": row.failure_reason,
                }
                for row in rows
            ]
        if len(payload) >= want:
            return payload
        time.sleep(0.15)
    return payload


def _snapshot(journey_id: str) -> dict[str, Any]:
    from sqlalchemy import select
    from app.db.models import (
        ActionApproval,
        AgentPendingAction,
        AgentRun,
        AgentRunStep,
        AuditLog,
        CollectiveAuthorityReceipt,
        Event,
        Journey,
        PlanVersion,
        RecoveryEpoch,
        ReplanProposal,
    )
    from app.db.session import SessionLocal

    with SessionLocal() as session:
        journey = session.get(Journey, journey_id)
        epochs = session.scalars(
            select(RecoveryEpoch).where(RecoveryEpoch.journey_id == journey_id).order_by(RecoveryEpoch.generation)
        ).all()
        runs = session.scalars(
            select(AgentRun).where(AgentRun.journey_id == journey_id).order_by(AgentRun.created_at, AgentRun.id)
        ).all()
        run_ids = [row.id for row in runs]
        steps = session.scalars(
            select(AgentRunStep).where(AgentRunStep.run_id.in_(run_ids)).order_by(AgentRunStep.run_id, AgentRunStep.sequence_no)
        ).all() if run_ids else []
        proposals = session.scalars(
            select(ReplanProposal).where(ReplanProposal.journey_id == journey_id).order_by(ReplanProposal.created_at, ReplanProposal.id)
        ).all()
        receipts = session.scalars(
            select(CollectiveAuthorityReceipt).where(CollectiveAuthorityReceipt.journey_id == journey_id).order_by(CollectiveAuthorityReceipt.issued_at, CollectiveAuthorityReceipt.id)
        ).all()
        approvals = session.scalars(
            select(ActionApproval).where(ActionApproval.journey_id == journey_id).order_by(ActionApproval.created_at, ActionApproval.id)
        ).all()
        pending = session.scalars(
            select(AgentPendingAction).where(AgentPendingAction.journey_id == journey_id).order_by(AgentPendingAction.created_at, AgentPendingAction.id)
        ).all()
        events = session.scalars(
            select(Event).where(Event.journey_id == journey_id).order_by(Event.detected_at, Event.id)
        ).all()
        audits = session.scalars(
            select(AuditLog).where(AuditLog.journey_id == journey_id).order_by(AuditLog.created_at, AuditLog.id)
        ).all()
        plans = session.scalars(
            select(PlanVersion).where(PlanVersion.journey_id == journey_id).order_by(PlanVersion.created_at, PlanVersion.id)
        ).all()
        def row(item: Any, fields: list[str]) -> dict[str, Any]:
            return {field: _jsonable(getattr(item, field, None)) for field in fields}
        step_rows = []
        for item in steps:
            step_rows.append({
                **row(item, ["id", "run_id", "sequence_no", "tool_name", "decision", "status"]),
                "arguments": _jsonable(json.loads(item.arguments_json or "{}")),
                "result": _jsonable(json.loads(item.result_json or "{}")),
            })
        return {
            "journey": row(journey, ["id", "status", "active_plan_version_id", "current_activity_id"]),
            "epochs": [row(item, ["id", "generation", "status", "active_plan_version_id_at_open", "recovery_reality_fingerprint", "triggering_event_ids_json", "opened_at", "closed_at", "close_reason", "superseded_by_recovery_epoch_id"]) for item in epochs],
            "runs": [row(item, ["id", "mission_id", "provider_key", "model_key", "status", "outcome", "failure_reason", "created_at", "completed_at", "recovery_epoch_id"]) for item in runs],
            "steps": step_rows,
            "proposals": [row(item, ["id", "trigger_event_id", "proposed_plan_version_id", "status", "hard_constraints_passed", "locked_commitments_preserved", "created_at", "decided_at", "recovery_epoch_id", "source_agent_run_id", "semantic_identity", "canonical_proposal_id"]) for item in proposals],
            "receipts": [
                row(
                    item,
                    [
                        "id",
                        "proposal_id",
                        "plan_version_id",
                        "authority_mode",
                        "decision_epoch",
                        "material_world_epoch",
                        "candidate_surface_fingerprint",
                        "source_mission_id",
                        "source_agent_run_id",
                        "recovery_epoch_id",
                        "classification",
                        "issued_at",
                        "invalidated_at",
                        "invalidation_code",
                    ],
                )
                for item in receipts
            ],
            "approvals": [
                row(
                    item,
                    [
                        "id",
                        "action",
                        "target_type",
                        "target_id",
                        "status",
                        "required_decision",
                        "approval_method",
                        "approved_by",
                        "recovery_epoch_id",
                        "authority_receipt_id",
                        "created_at",
                        "approved_at",
                        "consumed_at",
                    ],
                )
                for item in approvals
            ],
            "pending_actions": [row(item, ["id", "approval_id", "run_id", "mission_id", "tool_name", "status", "authority_receipt_id", "recovery_epoch_id", "created_at", "resumed_at"]) for item in pending],
            "events": [
                {
                    **row(
                        item,
                        [
                            "id",
                            "provider_key",
                            "provenance",
                            "event_type",
                            "severity",
                            "status",
                            "affected_activity_id",
                            "occurred_at",
                            "detected_at",
                        ],
                    ),
                    "payload": {
                        key: _jsonable(value)
                        for key, value in json.loads(
                            item.payload_json or "{}"
                        ).items()
                        if key
                        in {
                            "incident_fingerprint",
                            "scope_place_id",
                            "fixture_revision",
                            "disruption_class",
                            "target_place_id",
                            "extra_minutes",
                            "source",
                        }
                    },
                }
                for item in events
            ],
            "plans": [row(item, ["id", "status", "created_at", "selected_at", "activated_at"]) for item in plans],
            "audits": [{**row(item, ["id", "action", "entity_type", "entity_id", "actor_type", "actor_id", "created_at"]), "after": _jsonable(json.loads(item.after_json or "{}"))} for item in audits],
        }


def _configure_r32_authority(setup: dict[str, Any]) -> dict[str, Any]:
    """Configure explicit pre-strike values/authority through product APIs.

    This is not an approval of any future action.  Both Journey members publish
    the same standing preference and the owner pre-authorizes a finite
    deterministic autonomy envelope before either shock exists.
    """

    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)
    journey_id = str(setup["journey_id"])
    preference_receipts = []
    for member_id in (
        str(setup["owner_member_id"]),
        str(setup["admin_member_id"]),
    ):
        response = client.put(
            f"/api/v1/journeys/{journey_id}/members/{member_id}/preferences",
            json={
                "preferences": [
                    {
                        "category": "interest",
                        "key": "garden",
                        "value": True,
                        "weight": 1.0,
                    }
                ]
            },
        )
        response.raise_for_status()
        preference_receipts.append(
            {
                "member_id": member_id,
                "status_code": response.status_code,
                "preferences": response.json().get("preferences", []),
            }
        )

    policy_payload = {
        "mode": "AUTONOMOUS",
        "auto_accept_replan": True,
        "max_auto_replan_cost_delta_minor": 25000,
        "max_auto_loss_minor": 25000,
        "max_auto_schedule_drift_min": 240,
        "allowed_activity_types": [],
        "allowed_booking_types": [],
        "protected_commitment_levels": [
            "C3_Guaranteed",
            "C4_Anchored",
        ],
        "allow_auto_commitment_management": False,
        "allow_auto_when_provider_degraded": False,
        "allow_auto_on_critical_event": False,
    }
    policy = client.put(
        f"/api/v1/travelers/{setup['owner_id']}/agent-policy",
        json=policy_payload,
    )
    policy.raise_for_status()
    stored_policy = policy.json()
    return {
        "member_preferences": preference_receipts,
        "owner_policy": {
            key: stored_policy.get(key)
            for key in (
                "mode",
                "auto_accept_replan",
                "max_auto_replan_cost_delta_minor",
                "max_auto_loss_minor",
                "max_auto_schedule_drift_min",
                "protected_commitment_levels",
                "allow_auto_commitment_management",
                "allow_auto_when_provider_degraded",
                "allow_auto_on_critical_event",
                "version",
            )
        },
        "timing": "PRE_SHOCK_STANDING_AUTHORITY",
        "human_action_after_shock": False,
    }


def _stale_binding_assertion(journey_id: str, run_id: str) -> dict[str, Any]:
    """Validate the already persisted old run through the real Gateway binding seam."""
    from fastapi import HTTPException
    from app.agent.gateway import AgentToolGateway
    from app.db.models import AgentRun, Journey
    from app.db.session import SessionLocal
    from app.schemas import AgentToolCall
    from app.recovery_epoch import RECOVERY_EPOCH_SUPERSEDED

    with SessionLocal() as session:
        journey = session.get(Journey, journey_id)
        run = session.get(AgentRun, run_id)
        request = AgentToolCall(request_id="r32-stale-binding-assertion", journey_id=journey_id, mission_id=run.mission_id)
        try:
            AgentToolGateway(session, bound_run_id=run_id)._bound_recovery_epoch_id(request, journey)
        except HTTPException as exc:
            detail = exc.detail if isinstance(exc.detail, dict) else {"detail": exc.detail}
            return {"status_code": exc.status_code, "detail": _jsonable(detail), "typed": detail.get("code") == RECOVERY_EPOCH_SUPERSEDED}
        return {"status_code": 200, "typed": False, "detail": "old run unexpectedly remained current"}


def run() -> dict[str, Any]:
    source_receipt = _source_receipt()
    db = _configure()
    # Import application modules only after _configure has installed the fresh DB
    # and real configured WB2api settings.
    setup = _api_setup(db)
    authority_setup = _configure_r32_authority(setup)
    journey_id = str(setup["journey_id"])
    places = setup["selected_place_keys"]
    place_ids = list(places.keys())
    if len(place_ids) < 3:
        raise RuntimeError("R32 setup does not expose enough canonical places for two shocks")

    shock_a = _fixture_shock(journey_id, target_place_id=place_ids[0], label="SHOCK_A")
    r1 = _open_epoch(journey_id)

    from app.agent.orchestrator import HermesJourneyAgent
    original_complete = HermesJourneyAgent._complete
    release = threading.Event()
    barrier_hits: list[dict[str, Any]] = []
    barrier_lock = threading.Lock()

    def gated_complete(self, messages):
        hit = {
            "thread": threading.current_thread().name,
            "model_key": str(getattr(self, "model_key", "unknown")),
            "at": datetime.now(timezone.utc).isoformat(),
            "release_was_set": release.is_set(),
            "provider_call_invoked": False,
            "provider_returned": False,
        }
        with barrier_lock:
            barrier_hits.append(hit)
        if not release.wait(timeout=180):
            raise RuntimeError("R32 external-response barrier timed out")
        with barrier_lock:
            hit["provider_call_invoked"] = True
            hit["provider_call_started_at"] = (
                datetime.now(timezone.utc).isoformat()
            )
        try:
            result = original_complete(self, messages)
        except Exception as exc:
            with barrier_lock:
                hit["provider_exception"] = type(exc).__name__
                hit["provider_call_finished_at"] = (
                    datetime.now(timezone.utc).isoformat()
                )
            raise
        with barrier_lock:
            hit["provider_returned"] = True
            hit["provider_call_finished_at"] = (
                datetime.now(timezone.utc).isoformat()
            )
            hit["tool_call_count"] = len(result.get("tool_calls") or [])
            hit["has_content"] = bool(str(result.get("content") or "").strip())
        return result

    def wait_for_initial_barrier(thread_name: str, timeout: float = 45.0) -> bool:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            with barrier_lock:
                if any(
                    item.get("thread") == thread_name
                    and item.get("release_was_set") is False
                    for item in barrier_hits
                ):
                    return True
            time.sleep(0.05)
        return False

    HermesJourneyAgent._complete = gated_complete
    results: dict[str, Any] = {}
    command = (
        "Recover the current shared Journey from server-owned provider facts. "
        "Preserve completed execution and protected commitments. Use only the "
        "current Journey state, standing delegation policy, and server-derived "
        "collective authority; never reuse stale consent or invent a human "
        "answer. If current authority permits autonomous execution, you may "
        "execute within that envelope. If a real human value choice remains, "
        "leave it unresolved. Choose your own valid strategy from the live "
        "product state."
    )
    thread_a = threading.Thread(
        target=_run_command,
        args=(journey_id, command, results, "agent_a"),
        name="r32-agent-a",
        daemon=True,
    )
    thread_a.start()
    runs_after_a = _poll_runs(journey_id, want=1)
    a_run = runs_after_a[0] if runs_after_a else None
    a_bound = bool(
        a_run
        and a_run.get("status") == "RUNNING"
        and a_run.get("recovery_epoch_id") == r1["id"]
    )
    a_barrier_ready = wait_for_initial_barrier("r32-agent-a")
    if not a_bound or not a_barrier_ready:
        raise RuntimeError(
            "Agent A did not reach the durable R1 external-response boundary"
        )

    # The second provider replay deliberately changes the semantic event
    # family/scope (unscoped weather+mobility disturbance) rather than relying
    # on a new UUID for the same closure.  That is a material recovery reality
    # change and exercises the dedupe boundary honestly.
    shock_b = _fixture_shock(
        journey_id, target_place_id=None, label="SHOCK_B"
    )
    r2 = _open_epoch(journey_id)

    thread_b = threading.Thread(
        target=_run_command,
        args=(journey_id, command, results, "agent_b"),
        name="r32-agent-b",
        daemon=True,
    )
    thread_b.start()
    runs_after_b = _poll_runs(journey_id, want=2)
    b_run = next(
        (
            item
            for item in runs_after_b
            if a_run is None or item["id"] != a_run["id"]
        ),
        None,
    )
    b_bound = bool(
        b_run
        and b_run.get("status") == "RUNNING"
        and b_run.get("recovery_epoch_id") == r2["id"]
    )
    b_barrier_ready = wait_for_initial_barrier("r32-agent-b")
    if not b_bound or not b_barrier_ready:
        raise RuntimeError(
            "Agent B did not reach the durable R2 external-response boundary"
        )

    with barrier_lock:
        hits_before_release = [
            dict(item)
            for item in barrier_hits
            if item.get("release_was_set") is False
        ]
    expected_barrier_threads = {"r32-agent-a", "r32-agent-b"}
    concurrent_external_barrier_proven = (
        {item.get("thread") for item in hits_before_release}
        == expected_barrier_threads
        and len(hits_before_release) == 2
    )
    if not concurrent_external_barrier_proven:
        raise RuntimeError(
            "R32 barrier did not isolate exactly the two initial external calls"
        )
    release.set()
    thread_a.join(timeout=240)
    thread_b.join(timeout=240)
    HermesJourneyAgent._complete = original_complete

    with barrier_lock:
        external_call_outcomes = [dict(item) for item in barrier_hits]
    provider_calls_were_real = all(
        any(
            item.get("thread") == thread_name
            and item.get("provider_call_invoked") is True
            for item in external_call_outcomes
        )
        for thread_name in ("r32-agent-a", "r32-agent-b")
    )

    final = _snapshot(journey_id)
    stale_assertion = _stale_binding_assertion(journey_id, str(a_run["id"])) if a_run else {"typed": False, "detail": "Agent A run not durable"}
    current_epoch = next((row for row in final["epochs"] if row["status"] == "OPEN"), None)
    result = {
        "schema": "citynexus.r32.live-strike.v2",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "database": str(db),
        "journey_id": journey_id,
        "setup": _jsonable(setup),
        "authority_setup": _jsonable(authority_setup),
        "source_receipt": source_receipt,
        "runtime": {
            "provider": "WB2api",
            "endpoint": os.getenv("CITYNEXUS_HERMES_API_URL"),
            "configured_model": os.getenv("CITYNEXUS_HERMES_MODEL"),
            "fallback_models": os.getenv("CITYNEXUS_HERMES_MODEL_FALLBACKS"),
            "external_barrier_hits_before_release": hits_before_release,
            "external_call_outcomes": external_call_outcomes,
            "concurrent_external_barrier_proven": (
                concurrent_external_barrier_proven
            ),
            "provider_calls_were_real": provider_calls_were_real,
        },
        "shock_a": shock_a,
        "shock_b": shock_b,
        "r1": r1,
        "r2": r2,
        "agent_a_bound_before_shock_b": a_bound,
        "agent_b_bound_after_shock_b": b_bound,
        "agent_a_run_at_barrier": a_run,
        "agent_b_run_at_barrier": b_run,
        "agent_responses": _jsonable(results),
        "harness_wait_boundary_seconds_per_agent": 240,
        "agent_threads_still_running_at_checkpoint": {"a": thread_a.is_alive(), "b": thread_b.is_alive()},
        "stale_binding_assertion": stale_assertion,
        "current_epoch_id": current_epoch["id"] if current_epoch else None,
        "final": final,
        "truth_boundary": {
            "shock_source": "SERVER_OWNED_PROVIDER_REPLAY_FIXTURE",
            "external_runtime": "WB2api OpenAI-compatible Hermes endpoint",
            "physical_travel_proven": False,
        },
    }
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = run()
    output = args.output or (BACKEND / "output" / f"r32-live-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(_jsonable(result), ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({"output": str(output), "journey_id": result["journey_id"], "r1": result["r1"], "r2": result["r2"], "agent_a_bound": result["agent_a_bound_before_shock_b"], "agent_b_bound": result["agent_b_bound_after_shock_b"], "stale_typed": result["stale_binding_assertion"].get("typed")}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
