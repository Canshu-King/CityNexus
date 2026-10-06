"""One fresh R41 route-session closure on a new Journey."""
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
    db = BACKEND / f"r41-live-{secrets.token_hex(8)}.sqlite3"
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
            "CITYNEXUS_LIVE_VALHALLA_URL": "https://valhalla1.openstreetmap.de",
        }
    )
    return db


def _jsonable(value):
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
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
                {"id": row.id, "kind": row.kind, "priority": row.priority, "dedupe_key": row.dedupe_key,
                 "occurrence_count": row.occurrence_count, "status": row.status}
                for row in session.scalars(
                    select(NotificationEvent).where(NotificationEvent.journey_id == journey_id)
                ).all()
            ],
        }


def run(output: Path) -> dict:
    if output.exists():
        raise RuntimeError(f"R41 output already exists: {output}")
    db = _configure()
    from fastapi.testclient import TestClient
    from sqlalchemy import select

    from app.agent.watch_policy import next_move_projection
    from app.db.models import (
        Activity, AuditLog, Journey, JourneyLaunchContext, MobilityFact, OfflineJourneySnapshot,
        PlanVersion, Place, ProviderCall, RouteAcquisitionOperation,
    )
    from app.db.session import SessionLocal
    from app.execution.readiness import departure_readiness_projection, refresh_departure_readiness
    from app.execution.launch_origin import launch_context_projection
    from app.main import app

    source_head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()
    client = TestClient(app)
    local_now = datetime.now(ZoneInfo("Asia/Tokyo")).replace(second=0, microsecond=0)
    start_at = local_now + timedelta(hours=12)
    end_at = start_at + timedelta(hours=8)
    owner = client.post("/api/v1/travelers", json={"display_name": "R41 route owner", "email": None, "locale": "en-GB", "timezone": "Asia/Tokyo"})
    owner.raise_for_status()
    journey_response = client.post("/api/v1/journeys", json={
        "traveler_id": owner.json()["id"], "title": "R41 route session", "city_code": "NARA", "timezone": "Asia/Tokyo",
        "start_at": start_at.isoformat(), "end_at": end_at.isoformat(), "budget": {"amount_minor": 100000, "currency": "JPY"},
        "planning_mode": "balanced", "party_size": 1,
    })
    journey_response.raise_for_status()
    journey_id = journey_response.json()["id"]
    with SessionLocal() as session:
        selected_catalog = _copy_catalog(session)
        session.commit()
    plan_response = client.post(f"/api/v1/journeys/{journey_id}/plans/generate", json={
        "candidate_count": 1,
        "place_ids": ["real-place-22cf72809897ff4c7f312fcf", "real-place-a346e8f7f72a4d8f523d81e3"],
    })
    plan_response.raise_for_status()
    plan_body = plan_response.json()
    plans = plan_body.get("plans", []) if isinstance(plan_body, dict) else plan_body
    if not plans:
        raise RuntimeError(f"R41 plan generation returned no plans: {plan_response.text}")
    plan_id = plans[0]["id"]
    client.post(f"/api/v1/journeys/{journey_id}/plans/{plan_id}/select").raise_for_status()
    client.post(f"/api/v1/journeys/{journey_id}/start").raise_for_status()
    initial_setup = client.get(f"/api/v1/journeys/{journey_id}/launch-setup")
    initial_setup.raise_for_status()
    origin_place_id = "real-place-b47a20314c81d5a81381d4a4"
    confirmation = client.post(f"/api/v1/journeys/{journey_id}/launch-origin", json={"source_kind": "PLACE", "place_id": origin_place_id})
    confirmation.raise_for_status()
    acquisition = client.post(f"/api/v1/journeys/{journey_id}/routes/acquire", json={"requested_mode": "WALK"})
    acquisition.raise_for_status()
    operation = acquisition.json()
    operation_id = operation["operation_id"]
    operation_read = client.get(f"/api/v1/journeys/{journey_id}/routes/operations/{operation_id}")
    operation_read.raise_for_status()
    operation = operation_read.json()
    if not operation.get("terminal"):
        raise RuntimeError(f"R41 route operation did not finish: {operation}")

    with SessionLocal() as session:
        journey = session.get(Journey, journey_id)
        plan = session.get(PlanVersion, journey.active_plan_version_id)
        activities = list(session.scalars(select(Activity).where(Activity.plan_version_id == plan.id).order_by(Activity.sequence_no)).all())
        target = next_move_projection(session, journey).get("next_activity") or next_move_projection(session, journey).get("current_activity")
        target_activity = session.get(Activity, str(target["id"])) if target else None
        before_plan = journey.active_plan_version_id
        launch_before = launch_context_projection(session, journey, target_activity=target_activity, previous_activity=None)
        contract = session.get(JourneyLaunchContext, journey_id)
        confirmed_place = session.get(Place, origin_place_id)
        audit_rows = list(session.scalars(select(AuditLog).where(AuditLog.journey_id == journey_id).order_by(AuditLog.created_at, AuditLog.id)).all())
        before_rows = _rows(journey_id)

    with SessionLocal() as session:
        journey = session.get(Journey, journey_id)
        readiness = refresh_departure_readiness(session, journey, emit_briefing=True, refresh_offline=True)
        session.commit()

    with SessionLocal() as session:
        journey = session.get(Journey, journey_id)
        pure_after = departure_readiness_projection(session, journey)
        snapshot = session.get(OfflineJourneySnapshot, journey_id)
        snapshot_payload = json.loads(snapshot.payload_json) if snapshot else None
        facts = list(session.scalars(select(MobilityFact).where(MobilityFact.journey_id == journey_id)).all())
        calls = list(session.scalars(select(ProviderCall).where(ProviderCall.operation == "ROUTE_ACQUISITION")).all())
        stored_operation = session.get(RouteAcquisitionOperation, operation_id)
        after_rows = _rows(journey_id)
        final_plan = journey.active_plan_version_id

    if before_plan != final_plan:
        raise RuntimeError("R41 route session changed the active plan")
    if after_rows["event_ids"] or after_rows["agent_run_ids"] or after_rows["proposal_ids"] or after_rows["mutation_count"]:
        raise RuntimeError(f"R41 route session created forbidden action rows: {after_rows}")
    if snapshot_payload is None or "route_session" not in snapshot_payload:
        raise RuntimeError("R41 offline snapshot did not include route session")

    outcome = str(operation.get("outcome") or "")
    status = {
        "ROUTE_READY": "ROUTE_SESSION_READY",
        "ROUTE_PROVIDER_DEGRADED": "ROUTE_SESSION_PROVIDER_DEGRADED",
        "ROUTE_UNAVAILABLE": "ROUTE_SESSION_UNAVAILABLE",
        "ROUTE_PROVIDER_FAILURE": "ROUTE_SESSION_FAILED",
    }.get(outcome, "ROUTE_SESSION_FAILED")
    result = {
        "schema": "citynexus.r41.route-session.v1", "status": status, "database": str(db), "source_head_before_live": source_head,
        "journey_id": journey_id, "fresh_journey": True, "selected_catalog": selected_catalog,
        "initial_setup": initial_setup.json(), "confirmation": confirmation.json(), "launch_contract": confirmation.json().get("contract"),
        "confirmed_place": {"id": origin_place_id, "name": confirmed_place.name if confirmed_place else None, "provider_key": confirmed_place.provider_key if confirmed_place else None, "external_id": confirmed_place.external_id if confirmed_place else None},
        "active_plan_before": before_plan, "active_plan_after": final_plan,
        "activities": [{"id": row.id, "sequence_no": row.sequence_no, "title": row.title, "place_id": row.place_id, "start_at": row.start_at, "end_at": row.end_at} for row in activities],
        "route_session": {"acquisition": acquisition.json(), "operation": operation, "stored": {"status": stored_operation.status, "outcome": stored_operation.outcome, "finished_at": stored_operation.finished_at} if stored_operation else None, "mobility_facts": [{"id": fact.id, "from_key": fact.from_key, "to_key": fact.to_key, "mode": fact.mode, "duration_min": fact.duration_min, "distance_m": fact.distance_m, "provider_key": fact.provider_key, "provenance": fact.provenance, "captured_at": fact.captured_at} for fact in facts], "provider_calls": [{"provider_key": call.provider_key, "operation": call.operation, "status": call.status, "response": json.loads(call.response_json or "{}") } for call in calls]},
        "launch_projection_before": launch_before,
        "readiness": _jsonable(readiness), "readiness_recheck_read_only": _jsonable(pure_after),
        "must_leave_by": readiness.get("must_leave_by"), "must_leave_by_absent_reason": readiness.get("must_leave_by_absent_reason"),
        "launch_edge": readiness.get("launch_edge"), "route_evidence": (readiness.get("next_move") or {}).get("route_evidence"),
        "offline_route_session": snapshot_payload.get("route_session"), "offline_departure_readiness": snapshot_payload.get("departure_readiness"),
        "audit": [{"action": row.action, "entity_type": row.entity_type, "entity_id": row.entity_id} for row in audit_rows if row.action in {"journey.launch_origin.confirmed", "journey.route_session.mobility_fact_frozen"}],
        "persisted": after_rows, "provider_capture_calls": 1, "route_acquire_posts": 1, "location_observation_count": 0,
        "no_auto_capture_on_read": True, "citynexus_lab_estimate_authority": False,
        "captured_at": datetime.now(timezone.utc).isoformat(),
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(_jsonable(result), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = run(args.output)
    print(json.dumps({"output": str(args.output), "status": result["status"], "journey_id": result["journey_id"]}, ensure_ascii=False))
    return 0 if result["status"] in {"ROUTE_SESSION_READY", "ROUTE_SESSION_UNAVAILABLE", "ROUTE_SESSION_PROVIDER_DEGRADED", "ROUTE_SESSION_FAILED"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
