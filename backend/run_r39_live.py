"""One bounded R39 grounded-journey-launch refresh on a fresh Journey."""
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


def _rows(journey_id: str) -> dict[str, Any]:
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
        notifications = list(
            session.scalars(
                select(NotificationEvent)
                .where(NotificationEvent.journey_id == journey_id)
                .order_by(NotificationEvent.created_at, NotificationEvent.id)
            ).all()
        )
        return {
            "event_ids": [str(item) for item in session.scalars(select(Event.id).where(Event.journey_id == journey_id)).all()],
            "agent_run_ids": [str(item) for item in session.scalars(select(AgentRun.id).where(AgentRun.journey_id == journey_id)).all()],
            "proposal_ids": [str(item) for item in session.scalars(select(ReplanProposal.id).where(ReplanProposal.journey_id == journey_id)).all()],
            "mutation_count": int(mutation_count),
            "notifications": [
                {
                    "id": row.id,
                    "kind": row.kind,
                    "priority": row.priority,
                    "dedupe_key": row.dedupe_key,
                    "occurrence_count": row.occurrence_count,
                    "status": row.status,
                }
                for row in notifications
            ],
        }


def run(output: Path) -> dict[str, Any]:
    if output.exists():
        raise RuntimeError(f"R39 output already exists: {output}")
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

    from app.agent.watch_policy import next_move_projection
    from app.db.models import Activity, Journey, OfflineJourneySnapshot, PlanVersion, Place
    from app.db.session import SessionLocal
    from app.execution.readiness import departure_readiness_projection, refresh_departure_readiness
    from app.execution.launch_origin import launch_context_projection
    from app.main import app

    source_head = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True
    ).stdout.strip()
    client = TestClient(app)
    local_now = datetime.now(ZoneInfo("Asia/Tokyo")).replace(second=0, microsecond=0)
    # Keep the real venue within its provider-backed opening window.  The
    # target is still a fresh pre-trip next move, so no location is required.
    start_at = local_now + timedelta(hours=12)
    end_at = start_at + timedelta(hours=8)
    owner = client.post(
        "/api/v1/travelers",
        json={"display_name": "R39 readiness owner", "email": None, "locale": "en-GB", "timezone": "Asia/Tokyo"},
    )
    owner.raise_for_status()
    journey_response = client.post(
        "/api/v1/journeys",
        json={
            "traveler_id": owner.json()["id"],
            "title": "R39 departure readiness",
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
    if plan_response.status_code >= 400:
        raise RuntimeError(f"R39 plan generation failed: {plan_response.status_code} {plan_response.text}")
    plan_body = plan_response.json() or {}
    plan_rows = plan_body.get("plans", []) if isinstance(plan_body, dict) else plan_body
    if not plan_rows:
        raise RuntimeError(f"R39 plan generation returned no plans: {plan_response.text}")
    plan_id = plan_rows[0]["id"]
    client.post(f"/api/v1/journeys/{journey_id}/plans/{plan_id}/select").raise_for_status()
    client.post(f"/api/v1/journeys/{journey_id}/start").raise_for_status()

    with SessionLocal() as session:
        journey = session.get(Journey, journey_id)
        plan = session.get(PlanVersion, journey.active_plan_version_id) if journey else None
        activities = list(session.scalars(
            select(Activity).where(Activity.plan_version_id == plan.id).order_by(Activity.sequence_no)
        ).all()) if plan else []
        initial_plan_id = journey.active_plan_version_id if journey else None
        initial_move = next_move_projection(session, journey)
        raw_mobility = json.loads(plan.mobility_evidence_json or "{}") if plan else {}
        route_facts = raw_mobility.get("facts") if isinstance(raw_mobility, dict) else []
        target = initial_move.get("next_activity") or initial_move.get("current_activity")
        target_place = session.get(Place, str((target or {}).get("place_id"))) if target and target.get("place_id") else None
        target_activity = session.get(Activity, str((target or {}).get("id"))) if target else None
        launch_before = launch_context_projection(
            session,
            journey,
            target_activity=target_activity,
            previous_activity=None,
        ) if target_activity is not None else {"origin": {"state": "UNKNOWN_ORIGIN"}, "edge": {"state": "LAUNCH_EDGE_UNAVAILABLE"}}
        before_rows = _rows(journey_id)

    # One bounded read-model refresh.  It may record one deduped briefing when
    # the target is within the 60-minute window; it never calls a provider or
    # starts an agent/recovery path.
    with SessionLocal() as session:
        journey = session.get(Journey, journey_id)
        if journey is None:
            raise RuntimeError("R39 Journey disappeared before refresh")
        readiness = refresh_departure_readiness(
            session,
            journey,
            emit_briefing=True,
            refresh_offline=True,
        )
        session.commit()

    with SessionLocal() as session:
        journey = session.get(Journey, journey_id)
        final_plan_id = journey.active_plan_version_id if journey else None
        pure_after = departure_readiness_projection(session, journey) if journey else {}
        snapshot = session.get(OfflineJourneySnapshot, journey_id)
        snapshot_payload = json.loads(snapshot.payload_json) if snapshot else None
        after_move = next_move_projection(session, journey) if journey else {}
        after_rows = _rows(journey_id)

    if final_plan_id != initial_plan_id:
        raise RuntimeError("R39 readiness refresh changed the active plan")
    if after_rows["event_ids"] or after_rows["agent_run_ids"] or after_rows["proposal_ids"] or after_rows["mutation_count"]:
        raise RuntimeError(f"R39 readiness refresh created forbidden action rows: {after_rows}")
    if snapshot_payload is None or "departure_readiness" not in snapshot_payload:
        raise RuntimeError("R39 offline snapshot did not contain departure readiness")

    launch_origin = (readiness.get("launch_origin") or launch_before.get("origin") or {})
    launch_edge = (readiness.get("launch_edge") or launch_before.get("edge") or {})
    origin_state = str(launch_origin.get("state") or "UNKNOWN_ORIGIN")
    edge_state = str(launch_edge.get("state") or "LAUNCH_EDGE_UNAVAILABLE")
    if edge_state == "LAUNCH_ROUTE_READY":
        launch_status = "LAUNCH_ROUTE_READY"
    elif edge_state == "LAUNCH_ROUTE_READY_FROZEN":
        launch_status = "LAUNCH_ROUTE_READY_FROZEN"
    elif origin_state == "UNKNOWN_ORIGIN":
        launch_status = "LAUNCH_ORIGIN_UNKNOWN"
    elif edge_state == "LAUNCH_PROVIDER_DEGRADED" or bool(launch_edge.get("degraded")):
        launch_status = "LAUNCH_PROVIDER_DEGRADED"
    else:
        launch_status = "LAUNCH_EDGE_UNAVAILABLE"

    result = {
        "schema": "citynexus.r39.grounded-journey-launch.v1",
        "status": launch_status,
        "database": str(db),
        "source_head_before_live": source_head,
        "journey_id": journey_id,
        "fresh_journey": True,
        "selected_catalog": selected_catalog,
        "active_plan_before": initial_plan_id,
        "active_plan_after": final_plan_id,
        "activities": [
            {"id": row.id, "sequence_no": row.sequence_no, "title": row.title, "place_id": row.place_id, "start_at": row.start_at, "end_at": row.end_at}
            for row in activities
        ],
        "target_binding": {
            "activity_id": (target or {}).get("id"),
            "title": (target or {}).get("title"),
            "place_id": (target or {}).get("place_id"),
            "place_name": target_place.name if target_place else None,
            "provider_key": target_place.provider_key if target_place else None,
        },
        "readiness": _jsonable(readiness),
        "readiness_recheck_read_only": _jsonable(pure_after),
        "venue": {
            "state": (readiness.get("checks") or {}).get("venue"),
            "provenance": (readiness.get("next_move") or {}).get("venue_readiness"),
        },
        "route": {
            "readiness_evidence": (readiness.get("next_move") or {}).get("route_evidence"),
            "launch_origin": launch_origin,
            "launch_edge": launch_edge,
            "plan_fact_count": len(route_facts) if isinstance(route_facts, list) else 0,
            "plan_facts": route_facts,
        },
        "reservation": {
            "state": (readiness.get("checks") or {}).get("reservation"),
            "realtime": (readiness.get("checks") or {}).get("reservation_realtime"),
            "id": (readiness.get("evidence") or {}).get("reservation_id"),
        },
        "protected_commitment": {
            "state": (readiness.get("checks") or {}).get("commitment"),
            "ids": (readiness.get("evidence") or {}).get("commitment_ids", []),
        },
        "presence": (readiness.get("checks") or {}).get("presence"),
        "minutes_until_start": readiness.get("minutes_until_start"),
        "must_leave_by": readiness.get("must_leave_by"),
        "must_leave_by_absent_reason": readiness.get("must_leave_by_absent_reason"),
        "safety_buffer_minutes": readiness.get("safety_buffer_minutes"),
        "recommended_action": readiness.get("recommended_action"),
        "notification": readiness.get("notification"),
        "notifications_before": before_rows["notifications"],
        "notifications_after": after_rows["notifications"],
        "offline_snapshot": snapshot_payload.get("departure_readiness"),
        "offline_launch_origin": (snapshot_payload.get("departure_readiness") or {}).get("launch_origin"),
        "offline_launch_edge": (snapshot_payload.get("departure_readiness") or {}).get("launch_edge"),
        "persisted": after_rows,
        "location_observation_count": 0,
        "no_provider_retry": origin_state == "UNKNOWN_ORIGIN",
        "no_location_required": True,
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "limitations": [
            "No foreground location was requested or fabricated.",
            "No trusted device attestation bridge was used.",
            "CITYNEXUS_LAB_ESTIMATE_AUTHORITY=false",
        ],
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(_jsonable(result), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = run(args.output)
    print(json.dumps({"output": str(args.output), "status": result["status"], "journey_id": result["journey_id"], "notification": result["notification"]}, ensure_ascii=False))
    return 0 if result["status"] in {
        "LAUNCH_ROUTE_READY",
        "LAUNCH_ROUTE_READY_FROZEN",
        "LAUNCH_ORIGIN_UNKNOWN",
        "LAUNCH_EDGE_UNAVAILABLE",
        "LAUNCH_PROVIDER_DEGRADED",
    } else 2


if __name__ == "__main__":
    raise SystemExit(main())

\n
