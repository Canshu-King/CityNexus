"""One fresh R42 departure activation closure."""
from __future__ import annotations

import argparse
import json
import os
import secrets
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from run_r28_live import _copy_catalog

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"


def _configure() -> Path:
    db = BACKEND / f"r42-live-{secrets.token_hex(8)}.sqlite3"
    os.environ.update(
        {
            "CITYNEXUS_DATABASE_URL": "sqlite:///" + db.as_posix(),
            "CITYNEXUS_DEMO_MODE": "false",
            "CITYNEXUS_TRAVELER_AUTH_SECRET": secrets.token_urlsafe(48),
            "CITYNEXUS_LAB_ESTIMATE_AUTHORITY": "false",
            "CITYNEXUS_GUARDIAN_AUTORUN": "false",
            "CITYNEXUS_AI_ENABLED": "false",
            "CITYNEXUS_AI_API_KEY": "",
            "DEEPSEEK_API_KEY": "",
            "CITYNEXUS_HERMES_NATIVE_API_URL": "",
            "CITYNEXUS_HERMES_API_SERVER_KEY": "",
            "CITYNEXUS_REAL_CITY_ENABLED": "false",
            "CITYNEXUS_REAL_CITY_CACHE_TTL_SECONDS": "86400",
            "CITYNEXUS_LIVE_VALHALLA_URL": "https://valhalla1.openstreetmap.de",
        }
    )
    return db


def _jsonable(value):
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value


def _rows(journey_id: str) -> dict:
    from sqlalchemy import func, select
    from app.db.models import AgentRun, AuditLog, Event, NotificationEvent, ReplanProposal
    from app.db.session import SessionLocal

    with SessionLocal() as session:
        mutation_count = session.scalar(
            select(func.count(AuditLog.id)).where(
                AuditLog.journey_id == journey_id,
                AuditLog.action.in_(("replan.accepted", "replan_auto_accepted")),
            )
        ) or 0
        return {
            "event_ids": list(session.scalars(select(Event.id).where(Event.journey_id == journey_id)).all()),
            "agent_run_ids": list(session.scalars(select(AgentRun.id).where(AgentRun.journey_id == journey_id)).all()),
            "proposal_ids": list(session.scalars(select(ReplanProposal.id).where(ReplanProposal.journey_id == journey_id)).all()),
            "mutation_count": int(mutation_count),
            "notifications": [
                {"id": row.id, "kind": row.kind, "priority": row.priority, "dedupe_key": row.dedupe_key, "occurrence_count": row.occurrence_count, "status": row.status}
                for row in session.scalars(select(NotificationEvent).where(NotificationEvent.journey_id == journey_id)).all()
            ],
        }


class _FrozenClock:
    def __init__(self, value: datetime):
        self.value = value.astimezone(timezone.utc)

    def now(self, timezone_name: str | None = None) -> datetime:
        if timezone_name:
            try:
                return self.value.astimezone(ZoneInfo(timezone_name))
            except (KeyError, ValueError):
                pass
        return self.value


def run(output: Path) -> dict:
    if output.exists():
        raise RuntimeError(f"R42 output already exists: {output}")
    db = _configure()
    from fastapi.testclient import TestClient
    from sqlalchemy import select

    from app.agent.watch_policy import journey_phase_projection
    from app.core.config import settings
    from app.db.models import (
        Activity, AuditLog, Journey, JourneyLaunchContext, JourneyMember, JourneyOutcomeEvent,
        MobilityFact, OfflineJourneySnapshot, PlanVersion, Place, ProviderCall,
        RouteAcquisitionOperation,
    )
    from app.db.session import SessionLocal
    from app.execution.launch_origin import launch_context_projection
    from app.execution.readiness import departure_readiness_projection
    from app.main import app
    from app.traveler_principal import issue_traveler_token

    source_head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()
    client = TestClient(app)
    local_now = datetime.now(ZoneInfo("Asia/Tokyo")).replace(second=0, microsecond=0)
    start_at = local_now + timedelta(hours=12)
    end_at = start_at + timedelta(hours=8)
    owner = client.post("/api/v1/travelers", json={"display_name": "R42 departure owner", "email": None, "locale": "en-GB", "timezone": "Asia/Tokyo"})
    owner.raise_for_status()
    owner_id = owner.json()["id"]
    journey_response = client.post("/api/v1/journeys", json={
        "traveler_id": owner_id, "title": "R42 departure activation", "city_code": "NARA", "timezone": "Asia/Tokyo",
        "start_at": start_at.isoformat(), "end_at": end_at.isoformat(), "budget": {"amount_minor": 100000, "currency": "JPY"},
        "planning_mode": "balanced", "party_size": 1,
    })
    journey_response.raise_for_status()
    journey_id = journey_response.json()["id"]
    with SessionLocal() as session:
        selected_catalog = _copy_catalog(session)
        journey = session.get(Journey, journey_id)
        now = datetime.now(timezone.utc).isoformat()
        member = session.scalar(select(JourneyMember).where(JourneyMember.journey_id == journey_id, JourneyMember.traveler_id == owner_id))
        if member is None:
            member = JourneyMember(
                id=secrets.token_hex(16), journey_id=journey_id, traveler_id=owner_id, role="OWNER",
                invited_by=owner_id, expires_at=None, joined_at=now, removed_at=None,
                preferences_json="{}", created_at=now, updated_at=now,
            )
            session.add(member)
        session.commit()
        member_id = member.id

    plan_response = client.post(f"/api/v1/journeys/{journey_id}/plans/generate", json={
        "candidate_count": 1,
        "place_ids": ["real-place-22cf72809897ff4c7f312fcf", "real-place-a346e8f7f72a4d8f523d81e3"],
    })
    plan_response.raise_for_status()
    plan_body = plan_response.json()
    plans = plan_body.get("plans", []) if isinstance(plan_body, dict) else plan_body
    if not plans:
        raise RuntimeError(f"R42 plan generation returned no plans: {plan_response.text}")
    plan_id = plans[0]["id"]
    client.post(f"/api/v1/journeys/{journey_id}/plans/{plan_id}/select").raise_for_status()
    client.post(f"/api/v1/journeys/{journey_id}/start").raise_for_status()

    initial_setup = client.get(f"/api/v1/journeys/{journey_id}/launch-setup")
    initial_setup.raise_for_status()
    origin_place_id = "real-place-b47a20314c81d5a81381d4a4"
    confirmation = client.post(f"/api/v1/journeys/{journey_id}/launch-origin", json={"source_kind": "PLACE", "place_id": origin_place_id})
    confirmation.raise_for_status()
    route_acquire = client.post(f"/api/v1/journeys/{journey_id}/routes/acquire", json={"requested_mode": "WALK"})
    route_acquire.raise_for_status()
    route_operation = route_acquire.json()
    operation_id = route_operation["operation_id"]
    route_read = client.get(f"/api/v1/journeys/{journey_id}/routes/operations/{operation_id}")
    route_read.raise_for_status()
    route_operation = route_read.json()
    if route_operation.get("status") != "COMPLETED":
        raise RuntimeError(f"R42 setup route did not complete: {route_operation}")

    with SessionLocal() as session:
        journey = session.get(Journey, journey_id)
        plan = session.get(PlanVersion, journey.active_plan_version_id)
        activities = list(session.scalars(select(Activity).where(Activity.plan_version_id == plan.id).order_by(Activity.sequence_no)).all())
        current_activity = session.get(Activity, journey.current_activity_id)
        if current_activity is None:
            raise RuntimeError("R42 current activity is missing")
        target_start = datetime.fromisoformat(current_activity.start_at.replace("Z", "+00:00")).astimezone(timezone.utc)
        route_fact = session.scalar(select(MobilityFact).where(MobilityFact.journey_id == journey_id, MobilityFact.from_key == origin_place_id, MobilityFact.to_key == current_activity.place_id))
        if route_fact is None:
            raise RuntimeError("R42 exact R41 MobilityFact is missing")
        route_before = {"id": route_fact.id, "from_key": route_fact.from_key, "to_key": route_fact.to_key, "mode": route_fact.mode, "duration_min": route_fact.duration_min, "provider_key": route_fact.provider_key, "provenance": route_fact.provenance, "captured_at": route_fact.captured_at, "expires_at": route_fact.expires_at}
        active_plan_before = journey.active_plan_version_id
        activity_before = current_activity.status

    # Use a frozen clock only for deterministic activation/readiness projection.
    # The execution transition still requires the signed traveler principal.
    frozen_now = target_start - timedelta(minutes=int(route_operation["result"]["duration_min"]) + 5)
    frozen = _FrozenClock(frozen_now)
    import app.main as main_module
    import app.execution.readiness as readiness_module
    import app.operations.v9 as v9_module
    import app.agent.watch_policy as watch_module
    import app.execution.launch_origin as launch_module
    clock_modules = (main_module, readiness_module, v9_module, watch_module, launch_module)
    original_clocks = [module.execution_clock for module in clock_modules]
    for module in clock_modules:
        module.execution_clock = frozen
    try:
        readiness_before_response = client.get(f"/api/v1/journeys/{journey_id}/guardian/readiness")
        readiness_before_response.raise_for_status()
        readiness_before = readiness_before_response.json()
        activation_before_response = client.get(f"/api/v1/journeys/{journey_id}/departure-activation")
        activation_before_response.raise_for_status()
        activation_before = activation_before_response.json()
        cue_response = client.post(f"/api/v1/journeys/{journey_id}/guardian/readiness/refresh")
        cue_response.raise_for_status()
        readiness_cued = cue_response.json()
        token = issue_traveler_token(owner_id)
        departure_response = client.post(
            f"/api/v1/journeys/{journey_id}/activities/{current_activity.id}/depart",
            headers={"Authorization": f"Bearer {token}"},
            json={"truth_kind": "OPERATOR_CONFIRMED_EXECUTION", "operator_confirmed": True},
        )
        departure_response.raise_for_status()
        departure_action_count = 1
        readiness_after_response = client.get(f"/api/v1/journeys/{journey_id}/guardian/readiness")
        readiness_after_response.raise_for_status()
        readiness_after = readiness_after_response.json()
        offline_response = client.get(f"/api/v1/journeys/{journey_id}/offline-snapshot")
        offline_response.raise_for_status()
        offline = offline_response.json()
    finally:
        for module, original in zip(clock_modules, original_clocks):
            module.execution_clock = original

    with SessionLocal() as session:
        journey = session.get(Journey, journey_id)
        activity_after_row = session.get(Activity, current_activity.id)
        metadata = json.loads(activity_after_row.metadata_json or "{}")
        execution_truth = metadata.get("execution_truth")
        phase_before = readiness_before.get("next_move", {}).get("journey_phase")
        phase_after = journey_phase_projection(session, journey)
        route_after_fact = session.scalar(select(MobilityFact).where(MobilityFact.id == route_before["id"]))
        route_after = {"id": route_after_fact.id, "from_key": route_after_fact.from_key, "to_key": route_after_fact.to_key, "mode": route_after_fact.mode, "duration_min": route_after_fact.duration_min, "provider_key": route_after_fact.provider_key, "provenance": route_after_fact.provenance, "captured_at": route_after_fact.captured_at, "expires_at": route_after_fact.expires_at} if route_after_fact else None
        outcomes = list(session.scalars(select(JourneyOutcomeEvent).where(JourneyOutcomeEvent.journey_id == journey_id).order_by(JourneyOutcomeEvent.occurred_at_actual, JourneyOutcomeEvent.id)).all())
        provider_calls = list(session.scalars(select(ProviderCall).where(ProviderCall.operation == "ROUTE_ACQUISITION")).all())
        operation_count = len(session.scalars(select(RouteAcquisitionOperation).where(RouteAcquisitionOperation.journey_id == journey_id)).all())
        audit_rows = list(session.scalars(select(AuditLog).where(AuditLog.journey_id == journey_id, AuditLog.action == "journey.outcome.recorded")).all())
        active_plan_after = journey.active_plan_version_id
        activity_after = activity_after_row.status
        after_rows = _rows(journey_id)
        snapshot = session.get(OfflineJourneySnapshot, journey_id)
        snapshot_payload = json.loads(snapshot.payload_json) if snapshot else None
        contract = session.get(JourneyLaunchContext, journey_id)
        confirmed_place = session.get(Place, origin_place_id)

    if activity_before != "ACTIVE" or activity_after != "EN_ROUTE":
        raise RuntimeError(f"R42 activity transition was not ACTIVE->EN_ROUTE: {activity_before}->{activity_after}")
    if execution_truth is None or execution_truth.get("kind") != "OPERATOR_CONFIRMED_EXECUTION":
        raise RuntimeError(f"R42 strong execution truth missing: {execution_truth}")
    if route_before != route_after:
        raise RuntimeError("R42 departure changed the R41 MobilityFact")
    if active_plan_before != active_plan_after or operation_count != 1:
        raise RuntimeError("R42 departure mutated plan or route-operation count")
    if after_rows["event_ids"] or after_rows["agent_run_ids"] or after_rows["proposal_ids"] or after_rows["mutation_count"]:
        raise RuntimeError(f"R42 departure created forbidden rows: {after_rows}")

    outcome_payload = [
        {"id": row.id, "event_type": row.event_type, "actor_type": row.actor_type, "actor_id": row.actor_id}
        for row in outcomes
    ]
    result = {
        "schema": "citynexus.r42.departure-activation.v1",
        "status": "DEPARTURE_CONFIRMED_EN_ROUTE",
        "source_head_before_live": source_head,
        "database": str(db),
        "journey_id": journey_id,
        "fresh_journey": True,
        "active_plan_before": active_plan_before,
        "active_plan_after": active_plan_after,
        "activity": {"id": str(current_activity.id), "title": current_activity.title, "place_id": current_activity.place_id, "status_before": activity_before, "status_after": activity_after},
        "initial_setup": initial_setup.json(),
        "launch_contract": confirmation.json().get("contract"),
        "confirmed_place": {"id": origin_place_id, "name": confirmed_place.name if confirmed_place else None, "provider_key": confirmed_place.provider_key if confirmed_place else None},
        "route_session": {"operation_id": operation_id, "operation_count": operation_count, "status": route_operation.get("status"), "outcome": route_operation.get("outcome"), "provider": route_operation.get("provider"), "duration_min": route_operation.get("result", {}).get("duration_min"), "provider_capture_calls": 1},
        "readiness_before": readiness_before,
        "activation_before": activation_before,
        "cue": readiness_cued.get("departure_activation", {}).get("cue"),
        "must_leave_by": readiness_before.get("must_leave_by"),
        "departure_action_count": departure_action_count,
        "authenticated_principal": {"traveler_id": owner_id, "member_id": member_id, "auth_method": "SIGNED_HMAC_BEARER"},
        "execution_truth": execution_truth,
        "readiness_after": readiness_after,
        "phase_before": phase_before,
        "phase_after": phase_after,
        "journey_outcome_events": outcome_payload,
        "material_event_count": len(after_rows["event_ids"]),
        "agent_run_count": len(after_rows["agent_run_ids"]),
        "proposal_count": len(after_rows["proposal_ids"]),
        "plan_mutation_count": after_rows["mutation_count"],
        "route_fact_before": route_before,
        "route_fact_after": route_after,
        "offline_departure_activation": (snapshot_payload or {}).get("departure_activation"),
        "offline_execution": (snapshot_payload or {}).get("execution"),
        "notifications": after_rows["notifications"],
        "provider_calls": [{"provider_key": row.provider_key, "operation": row.operation, "status": row.status} for row in provider_calls],
        "citynexus_lab_estimate_authority": False,
        "captured_at": datetime.now(timezone.utc).isoformat(),
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(_jsonable(result), ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = run(args.output)
    print(json.dumps({"output": str(args.output), "status": result["status"], "journey_id": result["journey_id"]}, ensure_ascii=False))
    return 0 if result["status"] in {"DEPARTURE_CONFIRMED_EN_ROUTE", "DEPARTURE_CONFIRMATION_BLOCKED_AUTH", "DEPARTURE_CONFIRMATION_REFUSED"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
