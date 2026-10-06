"""R36 bounded Adaptive Journey Watch closure."""
from __future__ import annotations

import argparse
import json
import os
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from run_r28_live import _configure, _copy_catalog

ROOT = Path(__file__).resolve().parents[1]


def _jsonable(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value


def _traveller_watch_copy(watch: dict[str, Any] | None) -> str:
    state = str((watch or {}).get("watch_state") or "QUIET")
    return {
        "INCIDENT_ACTIVE": "A live issue needs closer attention, so Guardian is checking more often.",
        "APPROACHING": "Your next activity is within two hours, so Guardian is checking more often.",
        "TODAY": "You have an activity later today, so Guardian is keeping a closer watch.",
        "DAY_AHEAD": "An activity is planned for tomorrow, so Guardian is checking periodically.",
    }.get(state, "Nothing important is near, so Guardian is checking at a calmer pace.")


def _rows(journey_id: str) -> dict[str, Any]:
    from sqlalchemy import select

    from app.db.models import (
        AgentRun,
        AuditLog,
        AutopilotEnrollment,
        Event,
        GuardianPulse,
        GuardianRun,
        RecoveryEpoch,
        ReplanProposal,
        ProviderObservation,
        WebObservation,
    )
    from app.db.session import SessionLocal

    with SessionLocal() as session:
        enrollment = session.get(AutopilotEnrollment, journey_id)
        pulses = session.scalars(
            select(GuardianPulse)
            .where(GuardianPulse.journey_id == journey_id)
            .order_by(GuardianPulse.started_at, GuardianPulse.id)
        ).all()
        providers = session.scalars(
            select(ProviderObservation)
            .where(ProviderObservation.journey_id == journey_id)
            .order_by(ProviderObservation.captured_at, ProviderObservation.id)
        ).all()
        web = session.scalars(
            select(WebObservation)
            .where(WebObservation.journey_id == journey_id)
            .order_by(WebObservation.captured_at, WebObservation.id)
        ).all()
        events = session.scalars(
            select(Event)
            .where(Event.journey_id == journey_id)
            .order_by(Event.detected_at, Event.id)
        ).all()
        guardian_runs = session.scalars(
            select(GuardianRun)
            .where(GuardianRun.journey_id == journey_id)
            .order_by(GuardianRun.created_at, GuardianRun.id)
        ).all()
        agent_runs = session.scalars(
            select(AgentRun)
            .where(AgentRun.journey_id == journey_id)
            .order_by(AgentRun.created_at, AgentRun.id)
        ).all()
        epochs = session.scalars(
            select(RecoveryEpoch)
            .where(RecoveryEpoch.journey_id == journey_id)
            .order_by(RecoveryEpoch.opened_at, RecoveryEpoch.id)
        ).all()
        proposals = session.scalars(
            select(ReplanProposal)
            .where(ReplanProposal.journey_id == journey_id)
            .order_by(ReplanProposal.created_at, ReplanProposal.id)
        ).all()
        mutations = session.scalars(
            select(AuditLog)
            .where(
                AuditLog.journey_id == journey_id,
                AuditLog.action.in_(("replan.accepted", "replan_auto_accepted")),
            )
            .order_by(AuditLog.created_at, AuditLog.id)
        ).all()

        def payload(row: Any) -> dict[str, Any]:
            try:
                raw = getattr(row, "payload_json", None) or getattr(row, "result_json", None) or "{}"
                return json.loads(raw)
            except (TypeError, json.JSONDecodeError):
                return {}

        def content(row: Any) -> dict[str, Any]:
            try:
                return json.loads(row.content_excerpt or "{}")
            except (TypeError, json.JSONDecodeError):
                return {}

        return {
            "enrollment": (
                {
                    "journey_id": enrollment.journey_id,
                    "enabled": bool(enrollment.enabled),
                    "interval_seconds": enrollment.interval_seconds,
                    "last_pulse_at": enrollment.last_pulse_at,
                    "last_error": enrollment.last_error,
                }
                if enrollment is not None
                else None
            ),
            "guardian_pulses": [
                {
                    "id": row.id,
                    "status": row.status,
                    "provider_key": row.provider_key,
                    "observation_ids": json.loads(row.observation_ids_json or "[]"),
                    "guardian_run_id": row.guardian_run_id,
                    "started_at": row.started_at,
                    "completed_at": row.completed_at,
                    "result": payload(row),
                }
                for row in pulses
            ],
            "provider_observations": [
                {
                    "id": row.id,
                    "provider_key": row.provider_key,
                    "observation_type": row.observation_type,
                    "state": row.state,
                    "provenance": row.provenance,
                    "captured_at": row.captured_at,
                    "payload": payload(row),
                }
                for row in providers
            ],
            "venue_observations": [
                {
                    "id": row.id,
                    "provider_key": row.provider_key,
                    "provider_entity": content(row).get("provider_entity"),
                    "source_class": row.source_class,
                    "authority_status": row.authority_status,
                    "captured_at": row.captured_at,
                    "url": row.url,
                }
                for row in web
            ],
            "events": [
                {
                    "id": row.id,
                    "event_type": row.event_type,
                    "provider_key": row.provider_key,
                    "provenance": row.provenance,
                    "severity": row.severity,
                    "status": row.status,
                    "affected_activity_id": row.affected_activity_id,
                }
                for row in events
            ],
            "guardian_runs": [
                {
                    "id": row.id,
                    "decision": row.decision,
                    "status": row.status,
                    "action_status": row.action_status,
                    "trigger_event_id": row.trigger_event_id,
                    "agent_run_id": row.agent_run_id,
                    "proposal_id": row.proposal_id,
                }
                for row in guardian_runs
            ],
            "agent_runs": [
                {
                    "id": row.id,
                    "status": row.status,
                    "provider_key": row.provider_key,
                    "model_key": row.model_key,
                    "recovery_epoch_id": row.recovery_epoch_id,
                }
                for row in agent_runs
            ],
            "recovery_epochs": [
                {"id": row.id, "status": row.status, "close_reason": row.close_reason}
                for row in epochs
            ],
            "proposals": [
                {"id": row.id, "status": row.status, "trigger_event_id": row.trigger_event_id}
                for row in proposals
            ],
            "mutation_count": len(mutations),
        }


def run(output: Path) -> dict[str, Any]:
    if output.exists():
        raise RuntimeError(f"R36 output already exists: {output}")
    db = _configure()
    os.environ.update(
        {
            "CITYNEXUS_GUARDIAN_SIGNAL_PROVIDER": "open-meteo",
            "CITYNEXUS_GUARDIAN_AUTORUN": "false",
            "CITYNEXUS_LAB_ESTIMATE_AUTHORITY": "false",
            "CITYNEXUS_AI_ENABLED": "false",
            "CITYNEXUS_AI_API_KEY": "",
            "DEEPSEEK_API_KEY": "",
            "CITYNEXUS_HERMES_NATIVE_API_URL": "",
            "CITYNEXUS_HERMES_API_SERVER_KEY": "",
        }
    )
    from fastapi.testclient import TestClient
    from sqlalchemy import select

    from app.agent.autorun import ensure_enrollment, run_once
    from app.agent.watch_policy import adaptive_watch_policy, watch_is_due
    from app.db.models import Activity, AutopilotEnrollment, Journey, PlanVersion
    from app.db.session import SessionLocal
    from app.main import app

    client = TestClient(app)
    local_now = datetime.now(ZoneInfo("Asia/Tokyo")).replace(second=0, microsecond=0)
    start_at = local_now + timedelta(hours=12)
    end_at = start_at + timedelta(hours=8)

    owner = client.post(
        "/api/v1/travelers",
        json={"display_name": "R36 watch owner", "email": None, "locale": "en-GB", "timezone": "Asia/Tokyo"},
    )
    owner.raise_for_status()
    owner_id = owner.json()["id"]
    journey_response = client.post(
        "/api/v1/journeys",
        json={
            "traveler_id": owner_id,
            "title": "R36 adaptive journey watch",
            "city_code": "NARA",
            "timezone": "Asia/Tokyo",
            "start_at": start_at.isoformat(),
            "end_at": end_at.isoformat(),
            "budget": {"amount_minor": 100000, "currency": "JPY"},
            "planning_mode": "balanced",
            "party_size": 1,
        },
    )
    journey_response.raise_for_status()
    journey_id = journey_response.json()["id"]

    with SessionLocal() as session:
        selected_catalog = _copy_catalog(session)
        session.commit()

    plan_response = client.post(
        f"/api/v1/journeys/{journey_id}/plans/generate",
        json={
            "candidate_count": 1,
            "place_ids": [
                "real-place-22cf72809897ff4c7f312fcf",
                "real-place-a346e8f7f72a4d8f523d81e3",
            ],
        },
    )
    plan_response.raise_for_status()
    plans = plan_response.json()
    plan_rows = plans.get("plans") if isinstance(plans, dict) else plans
    if not plan_rows:
        raise RuntimeError(f"R36 plan generation returned no plans: {plan_response.text}")
    plan_id = plan_rows[0]["id"]
    client.post(f"/api/v1/journeys/{journey_id}/plans/{plan_id}/select").raise_for_status()
    client.post(f"/api/v1/journeys/{journey_id}/start").raise_for_status()

    mission_response = client.put(
        f"/api/v1/journeys/{journey_id}/guardian/mission",
        json={
            "command": "持续关注接下来的行程、天气、路线和地点开放信息；只在真实影响当前安排时进入恢复流程。",
            "requested_autonomy": "EXECUTE_WITHIN_BOUNDS",
        },
    )
    mission_response.raise_for_status()
    mission_body = mission_response.json()

    pulse_due_seed = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
    with SessionLocal() as session:
        journey = session.get(Journey, journey_id)
        if journey is None:
            raise RuntimeError("R36 Journey disappeared before enrollment")
        enrollment = ensure_enrollment(session, journey, enabled=True, interval_seconds=3600.0)
        enrollment.last_pulse_at = pulse_due_seed
        enrollment.updated_at = datetime.now(timezone.utc).isoformat()
        session.commit()
        plan = session.get(PlanVersion, journey.active_plan_version_id)
        activities = session.scalars(
            select(Activity).where(Activity.plan_version_id == plan.id).order_by(Activity.sequence_no)
        ).all() if plan is not None else []
        initial_plan_activity_ids = [item.id for item in activities]
        initial_next_activity = next(
            (item for item in activities if item.status not in {"COMPLETED", "SKIPPED", "CANCELLED"}),
            None,
        )
        initial_plan_id = journey.active_plan_version_id
        initial_strategy = {
            "active_plan_id": initial_plan_id,
            "activity_ids": initial_plan_activity_ids,
            "next_activity_id": initial_next_activity.id if initial_next_activity else None,
        }

    initial_status = client.get(f"/api/v1/journeys/{journey_id}/guardian/autopilot/status")
    initial_status.raise_for_status()
    initial_watch = initial_status.json().get("watch") or {}
    with SessionLocal() as session:
        journey = session.get(Journey, journey_id)
        enrollment = session.get(AutopilotEnrollment, journey_id)
        if journey is None or enrollment is None:
            raise RuntimeError("R36 enrollment disappeared before scheduled pulse")
        due_before_pulse = watch_is_due(session, journey, enrollment)
        computed_before = adaptive_watch_policy(session, journey, enrollment)

    if not due_before_pulse:
        raise RuntimeError(f"R36 setup did not produce a due watch: {computed_before}")

    source_head = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True
    ).stdout.strip()
    scheduled_results = run_once(enrolled_only=True, respect_schedule=True)
    if len(scheduled_results) != 1:
        raise RuntimeError(f"R36 expected one scheduled pulse, got {len(scheduled_results)}")
    pulse_body = scheduled_results[0]
    latest_response = client.get(f"/api/v1/journeys/{journey_id}/guardian/pulse/latest")
    latest_response.raise_for_status()
    latest_body = latest_response.json()
    final_status = client.get(f"/api/v1/journeys/{journey_id}/guardian/autopilot/status")
    final_status.raise_for_status()
    final_status_body = final_status.json()
    rows = _rows(journey_id)
    final_strategy = {
        "active_plan_id": None,
    }
    with SessionLocal() as session:
        journey = session.get(Journey, journey_id)
        final_strategy["active_plan_id"] = journey.active_plan_version_id if journey else None

    context = pulse_body.get("context_watch") or {}
    signals = pulse_body.get("signals") or {}
    if context.get("status") == "MATERIAL_CONFLICT":
        outcome = "WATCH_MATERIAL_CONFLICT_HANDOFF" if rows["agent_runs"] else "WATCH_EXTERNAL_AGENT_REQUIRED"
    elif context.get("status") in {"UNKNOWN", "PROVIDER_DEGRADED"} or signals.get("degraded"):
        outcome = "WATCH_DEGRADED"
    elif not rows["agent_runs"] and not rows["proposals"] and rows["mutation_count"] == 0:
        outcome = "WATCH_ALL_CLEAR"
    else:
        outcome = "WATCH_EXTERNAL_AGENT_REQUIRED"

    result = {
        "schema": "citynexus.r36.adaptive-journey-watch.v1",
        "status": outcome,
        "database": str(db),
        "source_head_before_live": source_head,
        "journey_id": journey_id,
        "initial_plan": initial_strategy,
        "standing_mission": {
            "http_status": mission_response.status_code,
            "id": mission_body.get("id"),
            "requested_autonomy": mission_body.get("requested_autonomy"),
        },
        "autopilot_enrollment": rows["enrollment"],
        "configured_interval_seconds": rows["enrollment"]["interval_seconds"] if rows["enrollment"] else None,
        "initial_watch": initial_watch,
        "initial_watch_due": due_before_pulse,
        "initial_watch_policy": computed_before,
        "pulse": _jsonable(pulse_body),
        "latest_pulse_read": _jsonable(latest_body),
        "persisted": rows,
        "final_strategy": final_strategy,
        "final_watch": final_status_body.get("watch"),
        "traveller_visible_watch": {
            "enabled": bool((final_status_body.get("enrollment") or {}).get("enabled")),
            "copy": _traveller_watch_copy(final_status_body.get("watch")),
            "next_due_at": (final_status_body.get("watch") or {}).get("next_due_at"),
        },
        "mutation_count": rows["mutation_count"],
        "limitations": [
            "software/provider execution only; no physical travel claimed",
            "one scheduled live Guardian pulse; no recurring worker started",
            "CITYNEXUS_LAB_ESTIMATE_AUTHORITY=false",
        ],
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "selected_catalog": selected_catalog,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(_jsonable(result), ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = run(args.output)
    print(
        json.dumps(
            {
                "output": str(args.output),
                "status": result.get("status"),
                "journey_id": result.get("journey_id"),
                "pulse_id": (result.get("pulse") or {}).get("pulse_id"),
                "mutation_count": result.get("mutation_count"),
            },
            ensure_ascii=False,
        )
    )
    return 0 if result.get("status") in {
        "WATCH_ALL_CLEAR",
        "WATCH_DEGRADED",
        "WATCH_MATERIAL_CONFLICT_HANDOFF",
        "WATCH_EXTERNAL_AGENT_REQUIRED",
    } else 2


if __name__ == "__main__":
    raise SystemExit(main())
