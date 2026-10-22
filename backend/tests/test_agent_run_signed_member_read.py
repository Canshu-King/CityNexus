from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

from fastapi.testclient import TestClient

import app.main as main_module
from app.core.config import settings
from app.db.models import AgentRun, Journey, JourneyMember, JourneyMission, Traveler
from app.db.session import SessionLocal
from app.traveler_principal import issue_traveler_token


client = TestClient(main_module.app)


def _seed_agent_run() -> dict[str, str]:
    owner_id = str(uuid4())
    outsider_id = str(uuid4())
    journey_id = str(uuid4())
    mission_id = str(uuid4())
    run_id = str(uuid4())
    now = datetime.now(timezone.utc)
    now_text = now.isoformat()

    with SessionLocal() as session:
        session.add_all(
            [
                Traveler(
                    id=owner_id,
                    display_name="Agent run reader",
                    email=None,
                    locale="en-US",
                    timezone="UTC",
                    created_at=now_text,
                    updated_at=now_text,
                ),
                Traveler(
                    id=outsider_id,
                    display_name="Agent run outsider",
                    email=None,
                    locale="en-US",
                    timezone="UTC",
                    created_at=now_text,
                    updated_at=now_text,
                ),
            ]
        )
        session.flush()
        session.add(
            Journey(
                id=journey_id,
                traveler_id=owner_id,
                title="Signed Agent run read",
                city_code="TST",
                timezone="UTC",
                start_at=now_text,
                end_at=(now + timedelta(hours=6)).isoformat(),
                budget_currency="USD",
                budget_amount_minor=10000,
                planning_mode="balanced",
                status="ACTIVE",
                active_plan_version_id=None,
                current_activity_id=None,
                created_at=now_text,
                updated_at=now_text,
            )
        )
        session.flush()
        session.add_all(
            [
                JourneyMember(
                    id=str(uuid4()),
                    journey_id=journey_id,
                    traveler_id=owner_id,
                    role="OWNER",
                    invited_by=owner_id,
                    expires_at=None,
                    joined_at=now_text,
                    removed_at=None,
                    preferences_json="{}",
                    created_at=now_text,
                    updated_at=now_text,
                ),
                JourneyMission(
                    id=mission_id,
                    journey_id=journey_id,
                    traveler_id=owner_id,
                    trigger_event_id=None,
                    user_text="Inspect this Journey",
                    requested_autonomy="PLAN_ONLY",
                    status="COMPLETED",
                    created_at=now_text,
                    started_at=now_text,
                    completed_at=now_text,
                ),
            ]
        )
        session.flush()
        session.add(
            AgentRun(
                id=run_id,
                mission_id=mission_id,
                journey_id=journey_id,
                provider_key="fixture",
                model_key="fixture-model",
                status="COMPLETED",
                outcome="{}",
                failure_reason=None,
                created_at=now_text,
                started_at=now_text,
                completed_at=now_text,
            )
        )
        session.commit()

    return {
        "owner_id": owner_id,
        "outsider_id": outsider_id,
        "journey_id": journey_id,
        "run_id": run_id,
    }


def test_agent_run_read_requires_signed_journey_member_when_secret_is_configured():
    previous_secret = settings.traveler_auth_secret
    test_secret = uuid4().hex + uuid4().hex
    object.__setattr__(settings, "traveler_auth_secret", test_secret)
    try:
        seeded = _seed_agent_run()
        route = (
            f"/api/v1/journeys/{seeded['journey_id']}/agent/runs/"
            f"{seeded['run_id']}"
        )

        anonymous = client.get(route)
        assert anonymous.status_code == 401, anonymous.text

        outsider_token = issue_traveler_token(seeded["outsider_id"])
        outsider = client.get(
            route,
            headers={"Authorization": f"Bearer {outsider_token}"},
        )
        assert outsider.status_code == 403, outsider.text

        owner_token = issue_traveler_token(seeded["owner_id"])
        authorized = client.get(
            route,
            headers={"Authorization": f"Bearer {owner_token}"},
        )
        assert authorized.status_code == 200, authorized.text
        assert authorized.json()["run_id"] == seeded["run_id"]
        assert authorized.headers["cache-control"] == "private, no-store, max-age=0"
        assert authorized.headers["vary"] == "Authorization, X-CityNexus-Traveler-Token"
    finally:
        object.__setattr__(settings, "traveler_auth_secret", previous_secret)


def test_agent_run_read_preserves_legacy_mode_without_traveler_secret():
    previous_secret = settings.traveler_auth_secret
    try:
        seeded = _seed_agent_run()
        route = (
            f"/api/v1/journeys/{seeded['journey_id']}/agent/runs/"
            f"{seeded['run_id']}"
        )
        object.__setattr__(settings, "traveler_auth_secret", "")
        response = client.get(route)
        assert response.status_code == 200, response.text
        assert response.json()["run_id"] == seeded["run_id"]
    finally:
        object.__setattr__(settings, "traveler_auth_secret", previous_secret)
