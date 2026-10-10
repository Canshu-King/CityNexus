"""Run one bounded R58 group-recovery experiment against a disposable database.

The caller must configure a fresh SQLite URL, a local traveler-auth secret, and an
explicit Valhalla endpoint before this module is imported. Location samples are
coursework foreground-web inputs, not claims about a real traveller's device.
"""

from __future__ import annotations

import json
import os
import sys
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.core.config import settings
from app.db.models import (
    Activity,
    AgentRun,
    AuditLog,
    Commitment,
    Event,
    Journey,
    JourneyMember,
    JourneyMission,
    Place,
    ReplanProposal,
    Traveler,
)
from app.db.session import SessionLocal
from app.execution.group_presence import rendezvous_target
from app.integrations.hermes.native_client import native_hermes_status
from app.main import app
from app.traveler_principal import issue_traveler_token


def _checked(response, expected: int, operation: str) -> dict:
    if response.status_code != expected:
        raise RuntimeError(
            f"{operation} returned {response.status_code}: {response.text[:500]}"
        )
    return response.json()


def run() -> dict:
    if settings.lab_estimate_authority:
        raise RuntimeError("R58 requires CITYNEXUS_LAB_ESTIMATE_AUTHORITY=false")
    route_provider_url = os.environ.get("CITYNEXUS_R58_ROUTE_PROVIDER_URL")
    if not route_provider_url:
        raise RuntimeError("R58 strike requires CITYNEXUS_R58_ROUTE_PROVIDER_URL")
    if not settings.traveler_auth_secret:
        raise RuntimeError("R58 strike requires a local signed-traveler secret")
    database_url = settings.database_url
    if not database_url.startswith("sqlite:///") or ":memory:" in database_url:
        raise RuntimeError("R58 strike requires a disposable file-backed SQLite URL")
    database_path = database_url.removeprefix("sqlite:///").replace("/", os.sep)
    if not os.path.isfile(database_path):
        raise RuntimeError("R58 strike database was not initialized")
    with SessionLocal() as session:
        existing_journeys = session.scalar(select(func.count()).select_from(Journey)) or 0
    if existing_journeys:
        raise RuntimeError("R58 strike refuses to reuse a database with existing Journeys")

    with TestClient(app) as client:
        seed = _checked(
            client.post(
                "/api/v1/demo/reset",
                headers={
                    "X-Demo-Reset-Token": os.environ["CITYNEXUS_DEMO_RESET_TOKEN"]
                },
            ),
            200,
            "demo catalog seed",
        )
        owner_id = str(seed["traveler_id"])
        # The disposable DB is empty before reset, so the seeded product Journey
        # is fresh for this strike while using the same setup seam as R57.
        journey_id = str(seed["journey_id"])
        plans = _checked(
            client.post(
                f"/api/v1/journeys/{journey_id}/plans/generate",
                json={"candidate_count": 1},
            ),
            201,
            "plan generation",
        )
        if not plans:
            raise RuntimeError("fresh Journey produced no plan candidate")
        plan_id = str(plans[0]["id"])
        _checked(
            client.post(f"/api/v1/journeys/{journey_id}/plans/{plan_id}/select"),
            200,
            "plan selection",
        )
        _checked(client.post(f"/api/v1/journeys/{journey_id}/start"), 200, "Journey start")

        companion_id = str(uuid4())
        companion_member_id = str(uuid4())
        stamp = datetime.now(timezone.utc).isoformat()
        with SessionLocal() as session:
            journey = session.get(Journey, journey_id)
            if journey is None:
                raise RuntimeError("fresh Journey disappeared after start")
            session.add(
                Traveler(
                    id=companion_id,
                    display_name="R58 lab companion",
                    email=None,
                    locale="zh-CN",
                    timezone="Asia/Shanghai",
                    created_at=stamp,
                    updated_at=stamp,
                )
            )
            session.flush()
            session.add(
                JourneyMember(
                    id=companion_member_id,
                    journey_id=journey_id,
                    traveler_id=companion_id,
                    role="COLLABORATOR",
                    invited_by=owner_id,
                    expires_at=None,
                    joined_at=stamp,
                    removed_at=None,
                    preferences_json="{}",
                    created_at=stamp,
                    updated_at=stamp,
                )
            )
            session.flush()
            pair = rendezvous_target(session, journey)
            if pair is None:
                raise RuntimeError("active Journey has no grounded shared stop")
            target_activity, target_place = pair
            commitment = session.scalar(
                select(Commitment).where(
                    Commitment.journey_id == journey_id,
                    Commitment.activity_id == target_activity.id,
                    Commitment.status == "ACTIVE",
                )
            )
            if commitment is None:
                commitment = Commitment(
                    id=str(uuid4()),
                    journey_id=journey_id,
                    activity_id=target_activity.id,
                    kind="APPOINTMENT",
                    level="C4_Anchored",
                    status="ACTIVE",
                    monetary_value_minor=0,
                    monetary_value_status="KNOWN",
                    currency=journey.budget_currency or "CNY",
                    external_ref="R58-LAB-PROTECTED-STOP",
                    policy_json="{}",
                    created_at=stamp,
                    updated_at=stamp,
                )
                session.add(commitment)
            commitment.level = "C4_Anchored"
            commitment.policy_json = json.dumps(
                {
                    "scheduled_start_at": (
                        datetime.now(timezone.utc) + timedelta(minutes=8)
                    ).isoformat(),
                    "safety_buffer_min": 5,
                    "source": "R58_COURSEWORK_SCENARIO",
                },
                sort_keys=True,
            )
            session.commit()
            target_lat = float(target_place.latitude)
            target_lon = float(target_place.longitude)
            journey_state = str(journey.status)
            active_plan_before = str(journey.active_plan_version_id)
            target_activity_id = str(target_activity.id)
            target_title = str(target_activity.title)

        owner_token = issue_traveler_token(owner_id)
        companion_token = issue_traveler_token(companion_id)
        headers_owner = {"Authorization": f"Bearer {owner_token}"}
        headers_companion = {"Authorization": f"Bearer {companion_token}"}
        captured_at = datetime.now(timezone.utc).isoformat()
        owner_location = _checked(
            client.post(
                f"/api/v1/journeys/{journey_id}/location",
                headers=headers_owner,
                json={
                    "latitude": target_lat,
                    "longitude": target_lon,
                    "accuracy_m": 8,
                    "captured_at": captured_at,
                },
            ),
            201,
            "owner foreground location",
        )
        companion_location = _checked(
            client.post(
                f"/api/v1/journeys/{journey_id}/location",
                headers=headers_companion,
                json={
                    "latitude": target_lat + 0.035,
                    "longitude": target_lon + 0.02,
                    "accuracy_m": 8,
                    "captured_at": captured_at,
                },
            ),
            201,
            "companion foreground location",
        )
        # Keep demo plan construction on the repository's default coursework
        # provider. Only the member-specific route operation is switched to the
        # explicit Valhalla service, so that route is a real provider capture.
        route_settings = replace(settings, live_valhalla_url=route_provider_url)
        import app.integrations.mobility.runtime as mobility_runtime
        import app.route_session_operations as route_session_operations

        mobility_runtime.settings = route_settings
        route_session_operations.settings = route_settings
        route = _checked(
            client.post(
                f"/api/v1/journeys/{journey_id}/group-presence/route",
                headers=headers_companion,
                json={
                    "location_observation_id": companion_location["id"],
                    "requested_mode": "WALK",
                },
            ),
            200,
            "member-specific route acquisition",
        )
        projection = _checked(
            client.get(
                f"/api/v1/journeys/{journey_id}/operator", headers=headers_owner
            ),
            200,
            "group recovery projection",
        )
        recovery = projection.get("group_recovery") or {}
        companion_projection = next(
            (
                item
                for item in projection.get("group_presence", {}).get("members", [])
                if item.get("traveler_id") == companion_id
            ),
            {},
        )
        affected = recovery.get("affected_member") or {}
        route_summary = route.get("route") or {}
        summary = {
            "journey_id": journey_id,
            "owner_member_id": next(
                (
                    item.get("member_id")
                    for item in projection.get("group_presence", {}).get("members", [])
                    if item.get("is_viewer")
                ),
                None,
            ),
            "companion_member_id": companion_member_id,
            "companion_traveler_id": companion_id,
            "journey_state": journey_state,
            "active_plan_version_before": active_plan_before,
            "target_activity_id": target_activity_id,
            "target_title": target_title,
            "foreground_location_authority": "ADVISORY_FOREGROUND_WEB_TEST_INPUT",
            "route_status": route.get("status"),
            "route_provider": route_summary.get("provider"),
            "route_provenance": route_summary.get("provenance"),
            "route_eta_minutes": affected.get("eta_minutes"),
            "route_eta_state": affected.get("route_evidence_state"),
            "group_recovery_state_before_request": recovery.get("state"),
            "risk_slack_min": (recovery.get("shared_commitment") or {}).get("slack_after_buffer_min"),
            "native_hermes_ready": bool((native_hermes_status() or {}).get("ready")),
            "physical_execution_evidence": "NONE; API state only",
        }
        if recovery.get("state") != "ADVISORY_MEMBER_LATE":
            summary.update(
                {
                    "stop": "RISK_NOT_GROUNDED_AS_LATE",
                    "active_plan_version_after": active_plan_before,
                    "mutation_count": 0,
                }
            )
            return summary

        requested = _checked(
            client.post(
                f"/api/v1/journeys/{journey_id}/group-recovery/adjust",
                headers=headers_owner,
                json={},
            ),
            200,
            "single user-requested recovery escalation",
        )
        with SessionLocal() as session:
            journey = session.get(Journey, journey_id)
            if journey is None:
                raise RuntimeError("Journey disappeared after recovery request")
            events = session.scalars(
                select(Event).where(Event.journey_id == journey_id)
            ).all()
            mission_rows = session.scalars(
                select(JourneyMission).where(JourneyMission.journey_id == journey_id)
            ).all()
            summary.update(
                {
                    "requested_status": requested.get("status"),
                    "mission_id": (requested.get("mission") or {}).get("id"),
                    "mission_status": (requested.get("mission") or {}).get("status"),
                    "agent_run_id": (requested.get("run") or {}).get("id") if requested.get("run") else None,
                    "agent_run_status": (requested.get("run") or {}).get("status") if requested.get("run") else None,
                    "event_count_after": len(events),
                    "explicit_adjust_request_event_count": sum(
                        event.provider_key == "journey-group-recovery-request"
                        for event in events
                    ),
                    "guardian_handoff_count": session.scalar(
                        select(func.count()).select_from(AuditLog).where(
                            AuditLog.journey_id == journey_id,
                            AuditLog.action == "journey.group_presence.member_risk.guardian_handoff",
                        )
                    )
                    or 0,
                    "agent_run_count": session.scalar(
                        select(func.count()).select_from(AgentRun).where(
                            AgentRun.journey_id == journey_id
                        )
                    )
                    or 0,
                    "proposal_count": session.scalar(
                        select(func.count()).select_from(ReplanProposal).where(
                            ReplanProposal.journey_id == journey_id
                        )
                    )
                    or 0,
                    "active_plan_version_after": str(journey.active_plan_version_id),
                    "plan_unchanged": str(journey.active_plan_version_id) == active_plan_before,
                    "mutation_count": int(str(journey.active_plan_version_id) != active_plan_before),
                    "mission_rows": [
                        {
                            "id": row.id,
                            "status": row.status,
                            "failure_reason": row.failure_reason,
                        }
                        for row in mission_rows
                    ],
                }
            )
        return summary


if __name__ == "__main__":
    print(json.dumps(run(), ensure_ascii=False, sort_keys=True))
