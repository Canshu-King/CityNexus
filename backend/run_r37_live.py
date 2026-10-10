"""R37 grounded presence and Next Move live closure.

The live closure intentionally does not invent a device coordinate.  It creates
one fresh Journey, binds a provider-backed target, reads the real presence and
watch projections, and records the honest unavailable outcome when no browser
foreground observation is supplied.
"""
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

    from app.db.models import (
        AgentRun,
        AuditLog,
        Event,
        GuardianPulse,
        LocationObservation,
        ReplanProposal,
    )
    from app.db.session import SessionLocal

    with SessionLocal() as session:
        def ids(model: Any) -> list[str]:
            return [str(item) for item in session.scalars(
                select(model.id).where(model.journey_id == journey_id).order_by(model.id)
            ).all()]

        mutations = session.scalar(
            select(func.count(AuditLog.id)).where(
                AuditLog.journey_id == journey_id,
                AuditLog.action.in_(("replan.accepted", "replan_auto_accepted")),
            )
        ) or 0
        return {
            "guardian_pulse_ids": ids(GuardianPulse),
            "location_observation_ids": ids(LocationObservation),
            "events": ids(Event),
            "agent_run_ids": ids(AgentRun),
            "proposal_ids": ids(ReplanProposal),
            "mutation_count": int(mutations),
        }


def run(output: Path) -> dict[str, Any]:
    if output.exists():
        raise RuntimeError(f"R37 output already exists: {output}")

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

    from app.agent.autorun import ensure_enrollment
    from app.agent.watch_policy import adaptive_watch_policy, next_move_projection
    from app.db.models import Activity, AutopilotEnrollment, Journey, Place, PlanVersion
    from app.db.session import SessionLocal
    from app.execution.presence import presence_projection
    from app.main import app

    client = TestClient(app)
    local_now = datetime.now(ZoneInfo("Asia/Tokyo")).replace(second=0, microsecond=0)
    start_at = local_now + timedelta(hours=12)
    end_at = start_at + timedelta(hours=8)

    owner = client.post(
        "/api/v1/travelers",
        json={"display_name": "R37 presence owner", "email": None, "locale": "en-GB", "timezone": "Asia/Tokyo"},
    )
    owner.raise_for_status()
    journey_response = client.post(
        "/api/v1/journeys",
        json={
            "traveler_id": owner.json()["id"],
            "title": "R37 grounded presence next move",
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
        raise RuntimeError(f"R37 plan generation returned no plans: {plan_response.text}")
    plan_id = plan_rows[0]["id"]
    client.post(f"/api/v1/journeys/{journey_id}/plans/{plan_id}/select").raise_for_status()
    client.post(f"/api/v1/journeys/{journey_id}/start").raise_for_status()

    mission_response = client.put(
        f"/api/v1/journeys/{journey_id}/guardian/mission",
        json={
            "command": "关注接下来的行程、天气、路线和地点开放信息；只在真实影响当前安排时进入恢复流程。",
            "requested_autonomy": "EXECUTE_WITHIN_BOUNDS",
        },
    )
    mission_response.raise_for_status()

    with SessionLocal() as session:
        journey = session.get(Journey, journey_id)
        if journey is None:
            raise RuntimeError("R37 Journey disappeared before closure")
        enrollment = ensure_enrollment(session, journey, enabled=True, interval_seconds=3600.0)
        enrollment.last_pulse_at = datetime.now(timezone.utc).isoformat()
        enrollment.updated_at = datetime.now(timezone.utc)
        session.commit()

        journey = session.get(Journey, journey_id)
        plan = session.get(PlanVersion, journey.active_plan_version_id) if journey else None
        activities = list(session.scalars(
            select(Activity).where(Activity.plan_version_id == plan.id).order_by(Activity.sequence_no)
        ).all()) if plan else []
        target = next((row for row in activities if row.status not in {"COMPLETED", "SKIPPED", "CANCELLED"}), None)
        target_place = session.get(Place, target.place_id) if target and target.place_id else None
        initial_strategy = {
            "active_plan_id": journey.active_plan_version_id if journey else None,
            "activity_ids": [str(row.id) for row in activities],
            "next_activity_id": str(target.id) if target else None,
        }
        target_binding = {
            "activity_id": str(target.id) if target else None,
            "activity_title": target.title if target else None,
            "place_id": str(target_place.id) if target_place else None,
            "place_name": target_place.name if target_place else None,
            "provider_key": target_place.provider_key if target_place else None,
            "latitude": target_place.latitude if target_place else None,
            "longitude": target_place.longitude if target_place else None,
        }
        watch_before = adaptive_watch_policy(session, journey, enrollment)
        next_move_before = next_move_projection(session, journey, phase=watch_before)
        presence_before = presence_projection(
            session, journey, target_activity_id=target_binding["activity_id"]
        )
        due_before = watch_before["next_due_at"]

    status_before_response = client.get(f"/api/v1/journeys/{journey_id}/guardian/autopilot/status")
    status_before_response.raise_for_status()
    status_before = status_before_response.json()
    global_before_response = client.get(f"/api/v1/journeys/{journey_id}/guardian/status")
    global_before_response.raise_for_status()

    # No browser permission was granted in this local run.  Do not fabricate a
    # coordinate or retry toward NEAR_TARGET; the valid closure is unavailable.
    location_observation_attempt = {
        "count": 0,
        "path": "FOREGROUND_WEB",
        "outcome": "LIVE_LOCATION_UNAVAILABLE",
        "reason": "NO_BROWSER_FOREGROUND_LOCATION_SUPPLIED",
    }

    with SessionLocal() as session:
        journey = session.get(Journey, journey_id)
        if journey is None:
            raise RuntimeError("R37 Journey disappeared after live closure")
        enrollment = session.get(AutopilotEnrollment, journey_id)
        if enrollment is None:
            raise RuntimeError("R37 enrollment disappeared after live closure")
        watch_after = adaptive_watch_policy(session, journey, enrollment)
        next_move_after = next_move_projection(session, journey, phase=watch_after)
        presence_after = presence_projection(
            session, journey, target_activity_id=target_binding["activity_id"]
        )
        final_active_plan_id = journey.active_plan_version_id

    status_after_response = client.get(f"/api/v1/journeys/{journey_id}/guardian/autopilot/status")
    status_after_response.raise_for_status()
    status_after = status_after_response.json()
    global_after_response = client.get(f"/api/v1/journeys/{journey_id}/guardian/status")
    global_after_response.raise_for_status()
    persisted = _rows(journey_id)

    if presence_after.get("state") != "LOCATION_UNAVAILABLE":
        raise RuntimeError(f"R37 expected unavailable presence, got {presence_after}")
    if persisted["location_observation_ids"]:
        raise RuntimeError("R37 closure unexpectedly persisted a location observation")
    if persisted["agent_run_ids"] or persisted["proposal_ids"] or persisted["mutation_count"]:
        raise RuntimeError(f"R37 closure created forbidden action rows: {persisted}")
    if initial_strategy["active_plan_id"] != final_active_plan_id:
        raise RuntimeError("R37 closure changed the active plan")

    source_head = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True
    ).stdout.strip()
    result = {
        "schema": "citynexus.r37.grounded-presence-next-move.v1",
        "status": "LIVE_LOCATION_UNAVAILABLE",
        "database": str(db),
        "source_head_before_live": source_head,
        "journey_id": journey_id,
        "fresh_journey": True,
        "selected_catalog": selected_catalog,
        "initial_plan": initial_strategy,
        "target_binding": target_binding,
        "standing_mission": mission_response.json(),
        "autopilot_status_before": status_before,
        "guardian_status_before": global_before_response.json(),
        "watch_before": _jsonable(watch_before),
        "next_move_before": _jsonable(next_move_before),
        "presence_before": _jsonable(presence_before),
        "location_observation_attempt": location_observation_attempt,
        "watch_after": _jsonable(watch_after),
        "next_move_after": _jsonable(next_move_after),
        "presence_after": _jsonable(presence_after),
        "autopilot_status_after": status_after,
        "guardian_status_after": global_after_response.json(),
        "persisted": persisted,
        "final_active_plan_id": final_active_plan_id,
        "execution_truth": {
            "physical_arrival_claimed": False,
            "strong_execution_transition": "BLOCKED",
            "trusted_bridge": "UNAVAILABLE_IN_LOCAL_ENVIRONMENT",
            "foreground_web_authority": "ADVISORY_ONLY",
        },
        "proof": {
            "no_spoofed_coordinate": True,
            "no_near_target_retry": True,
            "read_only_projection": True,
            "watch_presence_did_not_create_event": not persisted["events"],
        },
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "limitations": [
            "No browser foreground permission was available in this local closure.",
            "No trusted device attestation bridge is configured.",
            "CITYNEXUS_LAB_ESTIMATE_AUTHORITY=false",
        ],
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(_jsonable(result), ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = run(args.output)
    print(json.dumps({
        "output": str(args.output),
        "status": result["status"],
        "journey_id": result["journey_id"],
        "location_observation_count": len(result["persisted"]["location_observation_ids"]),
        "agent_run_count": len(result["persisted"]["agent_run_ids"]),
        "mutation_count": result["persisted"]["mutation_count"],
    }, ensure_ascii=False))
    return 0 if result["status"] in {
        "LIVE_LOCATION_NEAR_TARGET_ADVISORY",
        "LIVE_LOCATION_AWAY",
        "LIVE_LOCATION_UNAVAILABLE",
        "LIVE_LOCATION_BLOCKED",
    } else 2


if __name__ == "__main__":
    raise SystemExit(main())
