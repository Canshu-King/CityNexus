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

from run_r28_live import BACKEND, _api_setup, _configure as _base_configure


def _configure_r32() -> Path:
    """Create an isolated R32 process environment before importing app code.

    The strike is specifically about the configured Hermes/WB2api Agent
    runtime.  Ambient DeepSeek/Qwen credentials must not silently insert a
    separate semantic-compiler provider call in front of the Agent command.
    """

    db = _base_configure()
    os.environ.update(
        {
            "CITYNEXUS_AI_ENABLED": "false",
            "CITYNEXUS_AI_API_KEY": "",
            "DEEPSEEK_API_KEY": "",
            # Native Hermes is a different execution surface.  R32 exercises
            # the OpenAI-compatible WB2api runtime only.
            "CITYNEXUS_HERMES_NATIVE_API_URL": "",
            "CITYNEXUS_HERMES_API_SERVER_KEY": "",
        }
    )
    return db


def _runtime_preflight() -> dict[str, Any]:
    """Prove which runtime will receive the strike before any AgentRun starts."""

    from app.agent.orchestrator import HermesJourneyAgent, configured_journey_agent
    from app.core.config import settings
    from app.integrations.hermes.native_client import native_hermes_status

    native = native_hermes_status()
    runtime = configured_journey_agent()
    try:
        runtime_type = type(runtime).__name__
        is_hermes = isinstance(runtime, HermesJourneyAgent)
        receipt = {
            "runtime_type": runtime_type,
            "provider_key": getattr(runtime, "provider_key", None),
            "model_key": getattr(runtime, "model_key", None),
            "hermes_api_url_configured": bool(settings.hermes_api_url),
            "hermes_api_key_configured": bool(settings.hermes_api_key),
            "semantic_ai_api_key_configured": bool(settings.ai_api_key),
            "native_hermes_configured": bool(native.get("configured")),
            "native_hermes_ready": bool(native.get("ready")),
            "selected_openai_compatible_hermes": is_hermes,
        }
    finally:
        runtime.close()

    if receipt["semantic_ai_api_key_configured"]:
        raise RuntimeError(
            "R32 preflight found an ambient semantic AI provider before Hermes"
        )
    if receipt["native_hermes_ready"]:
        raise RuntimeError(
            "R32 preflight found native Hermes ready; strike requires WB2api"
        )
    if not receipt["selected_openai_compatible_hermes"]:
        raise RuntimeError(
            f"R32 preflight selected unexpected runtime: {runtime_type}"
        )
    return receipt


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
        "requested_member_preference": {
            "category": "interest",
            "key": "garden",
            "value": True,
            "weight": 1.0,
        },
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
    db = _configure_r32()
    # Import application modules only after _configure_r32 has installed the
    # fresh DB and isolated WB2api/Hermes settings.
    runtime_preflight = _runtime_preflight()
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
    # TestClient executes sync FastAPI endpoints in AnyIO worker threads, so
    # operating-system/thread names are not a trustworthy Agent identity.
    # The coordinator owns this causal slot: while A's first response is held,
    # A cannot enter a second model turn; after A reaches the boundary and
    # before B starts, the slot advances exactly once to B.
    barrier_phase = {"slot": "A"}

    def current_server_run_binding() -> dict[str, Any]:
        """Resolve the exact durable AgentRun owning the current open epoch."""

        from sqlalchemy import select
        from app.db.models import AgentRun, RecoveryEpoch
        from app.db.session import SessionLocal

        with SessionLocal() as session:
            open_epoch = session.scalar(
                select(RecoveryEpoch)
                .where(
                    RecoveryEpoch.journey_id == journey_id,
                    RecoveryEpoch.status == "OPEN",
                )
                .order_by(
                    RecoveryEpoch.generation.desc(),
                    RecoveryEpoch.id.desc(),
                )
            )
            if open_epoch is None:
                return {
                    "agent_run_id": None,
                    "recovery_epoch_id": None,
                    "resolution": "NO_OPEN_RECOVERY_EPOCH",
                    "candidate_run_ids": [],
                }
            runs = session.scalars(
                select(AgentRun)
                .where(
                    AgentRun.journey_id == journey_id,
                    AgentRun.recovery_epoch_id == open_epoch.id,
                    AgentRun.status == "RUNNING",
                )
                .order_by(AgentRun.created_at, AgentRun.id)
            ).all()
            return {
                "agent_run_id": runs[0].id if len(runs) == 1 else None,
                "recovery_epoch_id": open_epoch.id,
                "recovery_epoch_generation": open_epoch.generation,
                "resolution": (
                    "EXACT_ONE_CURRENT_RUN"
                    if len(runs) == 1
                    else "NO_CURRENT_RUN"
                    if not runs
                    else "AMBIGUOUS_CURRENT_RUN"
                ),
                "candidate_run_ids": [row.id for row in runs],
            }

    def gated_complete(self, messages):
        """Start the real provider call, but hold its response at the boundary."""

        caller_thread = threading.current_thread().name
        with barrier_lock:
            causal_slot = str(barrier_phase["slot"])
        server_binding = current_server_run_binding()
        hit = {
            "thread": caller_thread,
            "causal_slot": causal_slot,
            "agent_run_id": server_binding.get("agent_run_id"),
            "recovery_epoch_id": server_binding.get("recovery_epoch_id"),
            "recovery_epoch_generation": server_binding.get(
                "recovery_epoch_generation"
            ),
            "server_run_resolution": server_binding.get("resolution"),
            "server_run_candidates": server_binding.get(
                "candidate_run_ids", []
            ),
            "model_key": str(getattr(self, "model_key", "unknown")),
            "at": datetime.now(timezone.utc).isoformat(),
            "release_was_set": release.is_set(),
            "provider_call_invoked": False,
            "provider_returned": False,
            "response_released_to_runtime": False,
        }
        provider_done = threading.Event()
        provider_box: dict[str, Any] = {}

        def call_provider():
            with barrier_lock:
                hit["provider_call_invoked"] = True
                hit["provider_call_started_at"] = (
                    datetime.now(timezone.utc).isoformat()
                )
            try:
                provider_box["result"] = original_complete(self, messages)
            except BaseException as exc:
                provider_box["exception"] = exc
                with barrier_lock:
                    hit["provider_exception"] = type(exc).__name__
            finally:
                with barrier_lock:
                    hit["provider_returned"] = "result" in provider_box
                    hit["provider_call_finished_at"] = (
                        datetime.now(timezone.utc).isoformat()
                    )
                    result = provider_box.get("result")
                    if isinstance(result, dict):
                        hit["tool_call_count"] = len(
                            result.get("tool_calls") or []
                        )
                        hit["has_content"] = bool(
                            str(result.get("content") or "").strip()
                        )
                provider_done.set()

        with barrier_lock:
            barrier_hits.append(hit)
        provider_thread = threading.Thread(
            target=call_provider,
            name=f"{caller_thread}-provider",
            daemon=True,
        )
        provider_thread.start()

        # The live coordinator may inject the next shock only after the real
        # provider invocation is durable in this receipt.  The response itself
        # stays outside Runtime until both Agent generations reach the barrier.
        if not release.wait(timeout=180):
            raise RuntimeError("R32 external-response barrier timed out")
        if not provider_done.wait(timeout=240):
            raise RuntimeError("R32 external provider call did not terminate")
        if "exception" in provider_box:
            raise provider_box["exception"]
        result = provider_box.get("result")
        if not isinstance(result, dict):
            raise RuntimeError("R32 external provider returned no model message")
        with barrier_lock:
            hit["response_released_to_runtime"] = True
            hit["response_released_at"] = (
                datetime.now(timezone.utc).isoformat()
            )
        return result

    def wait_for_initial_barrier(
        *,
        run_id: str,
        recovery_epoch_id: str,
        causal_slot: str,
        timeout: float = 45.0,
    ) -> bool:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            with barrier_lock:
                if any(
                    item.get("agent_run_id") == run_id
                    and item.get("recovery_epoch_id") == recovery_epoch_id
                    and item.get("causal_slot") == causal_slot
                    and item.get("server_run_resolution")
                    == "EXACT_ONE_CURRENT_RUN"
                    and item.get("release_was_set") is False
                    and item.get("provider_call_invoked") is True
                    for item in barrier_hits
                ):
                    return True
            time.sleep(0.05)
        return False

    HermesJourneyAgent._complete = gated_complete
    results: dict[str, Any] = {}
    thread_a: threading.Thread | None = None
    thread_b: threading.Thread | None = None
    a_run: dict[str, Any] | None = None
    b_run: dict[str, Any] | None = None
    a_bound = False
    b_bound = False
    shock_b: dict[str, Any] = {}
    r2: dict[str, Any] = {}

    def abort_checkpoint(phase: str, message: str) -> dict[str, Any]:
        """Persist the actual partial strike state instead of hand-building it."""

        release.set()
        for thread in (thread_a, thread_b):
            if thread is not None and thread.is_alive():
                thread.join(timeout=5)
        HermesJourneyAgent._complete = original_complete

        with barrier_lock:
            external_call_outcomes = [dict(item) for item in barrier_hits]
        invoked_slots = sorted(
            {
                str(item.get("causal_slot"))
                for item in external_call_outcomes
                if item.get("provider_call_invoked") is True
                and item.get("causal_slot")
            }
        )
        final = _snapshot(journey_id)
        current_epoch = next(
            (
                row
                for row in final["epochs"]
                if row.get("status") == "OPEN"
            ),
            None,
        )
        return {
            "schema": "citynexus.r32.live-strike.v2.failure.v2",
            "status": "NOT_PROVEN",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "database": str(db),
            "journey_id": journey_id,
            "failure": {
                "phase": phase,
                "error_type": "RuntimeError",
                "message": message,
                "cause": (
                    "The harness stopped at the first unmet causal boundary "
                    "and preserved the durable partial state without injecting "
                    "later shocks or authority."
                ),
            },
            "setup": _jsonable(setup),
            "authority_setup": _jsonable(authority_setup),
            "runtime_preflight": _jsonable(runtime_preflight),
            "source_receipt": source_receipt,
            "runtime": {
                "provider": "WB2api",
                "endpoint": os.getenv("CITYNEXUS_HERMES_API_URL"),
                "configured_model": os.getenv("CITYNEXUS_HERMES_MODEL"),
                "fallback_models": os.getenv(
                    "CITYNEXUS_HERMES_MODEL_FALLBACKS"
                ),
                "external_call_outcomes": external_call_outcomes,
                "provider_invoked_slots": invoked_slots,
                "provider_calls_were_real": bool(invoked_slots),
                "concurrent_external_barrier_proven": False,
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
            "agent_threads_still_running_at_checkpoint": {
                "a": bool(thread_a and thread_a.is_alive()),
                "b": bool(thread_b and thread_b.is_alive()),
            },
            "stale_binding_assertion": {
                "typed": False,
                "detail": "not exercised before a complete R1 -> R2 chronology",
            },
            "current_epoch_id": (
                current_epoch.get("id") if current_epoch else None
            ),
            "final": final,
            "truth_boundary": {
                "shock_source": "SERVER_OWNED_PROVIDER_REPLAY_FIXTURE",
                "external_runtime": (
                    "WB2api OpenAI-compatible Hermes endpoint"
                ),
                "physical_travel_proven": False,
            },
        }

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
    a_barrier_ready = bool(
        a_run
        and wait_for_initial_barrier(
            run_id=str(a_run["id"]),
            recovery_epoch_id=str(r1["id"]),
            causal_slot="A",
        )
    )
    if not a_bound or not a_barrier_ready:
        return abort_checkpoint(
            "A_EXTERNAL_RESPONSE_BOUNDARY",
            "Agent A did not reach the durable R1 external-response boundary",
        )

    # The second provider replay deliberately changes the semantic event
    # family/scope (unscoped weather+mobility disturbance) rather than relying
    # on a new UUID for the same closure.  That is a material recovery reality
    # change and exercises the dedupe boundary honestly.
    shock_b = _fixture_shock(
        journey_id, target_place_id=None, label="SHOCK_B"
    )
    r2 = _open_epoch(journey_id)

    # A is still blocked on its first response, so advancing the coordinator
    # slot here cannot mislabel a later A turn.
    with barrier_lock:
        barrier_phase["slot"] = "B"

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
    b_barrier_ready = bool(
        b_run
        and wait_for_initial_barrier(
            run_id=str(b_run["id"]),
            recovery_epoch_id=str(r2["id"]),
            causal_slot="B",
        )
    )
    if not b_bound or not b_barrier_ready:
        return abort_checkpoint(
            "B_EXTERNAL_RESPONSE_BOUNDARY",
            "Agent B did not reach the durable R2 external-response boundary",
        )

    with barrier_lock:
        hits_before_release = [
            dict(item)
            for item in barrier_hits
            if item.get("release_was_set") is False
        ]
    expected_barrier_slots = {"A", "B"}
    expected_run_ids = {
        str(a_run["id"]) if a_run else "",
        str(b_run["id"]) if b_run else "",
    }
    expected_epoch_ids = {str(r1["id"]), str(r2["id"])}
    concurrent_external_barrier_proven = (
        {item.get("causal_slot") for item in hits_before_release}
        == expected_barrier_slots
        and {str(item.get("agent_run_id") or "") for item in hits_before_release}
        == expected_run_ids
        and {
            str(item.get("recovery_epoch_id") or "")
            for item in hits_before_release
        }
        == expected_epoch_ids
        and len(hits_before_release) == 2
        and all(
            item.get("provider_call_invoked") is True
            and item.get("server_run_resolution")
            == "EXACT_ONE_CURRENT_RUN"
            for item in hits_before_release
        )
    )
    if not concurrent_external_barrier_proven:
        return abort_checkpoint(
            "CONCURRENT_EXTERNAL_BARRIER",
            "R32 barrier did not isolate exactly the two initial external calls",
        )
    release.set()
    thread_a.join(timeout=240)
    thread_b.join(timeout=240)
    HermesJourneyAgent._complete = original_complete

    with barrier_lock:
        external_call_outcomes = [dict(item) for item in barrier_hits]
    provider_calls_were_real = bool(
        a_run
        and b_run
        and all(
            any(
                item.get("agent_run_id") == run_id
                and item.get("provider_call_invoked") is True
                and item.get("server_run_resolution")
                == "EXACT_ONE_CURRENT_RUN"
                for item in external_call_outcomes
            )
            for run_id in (str(a_run["id"]), str(b_run["id"]))
        )
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
        "runtime_preflight": _jsonable(runtime_preflight),
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
    print(json.dumps({"output": str(output), "status": result.get("status", "COMPLETED"), "journey_id": result["journey_id"], "r1": result["r1"], "r2": result["r2"], "agent_a_bound": result["agent_a_bound_before_shock_b"], "agent_b_bound": result["agent_b_bound_after_shock_b"], "stale_typed": result["stale_binding_assertion"].get("typed"), "failure": result.get("failure")}, ensure_ascii=False))
    return 2 if result.get("status") == "NOT_PROVEN" else 0


if __name__ == "__main__":
    raise SystemExit(main())
