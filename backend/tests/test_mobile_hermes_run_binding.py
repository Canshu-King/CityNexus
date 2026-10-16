from __future__ import annotations

from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select

import app.main as main_module
from app.agent.mission import create_mission
from app.core.audit import record_audit
from app.core.config import settings
from app.db.models import Journey, JourneyMember
from app.db.session import SessionLocal


class _HermesStatusOnly:
    def __init__(self):
        pass

    def get_run(self, run_id: str):
        return {"run_id": run_id, "status": "running"}

    def close(self):
        pass


def _traveler(client: TestClient, label: str) -> dict[str, str]:
    response = client.post(
        "/api/v1/travelers",
        json={"display_name": label, "timezone": "Asia/Shanghai", "locale": "zh-CN"},
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_native_hermes_timeline_is_bound_to_signed_member_and_journey(monkeypatch):
    previous_secret = settings.traveler_auth_secret
    object.__setattr__(settings, "traveler_auth_secret", "mobile-hermes-binding-test-secret-0123456789")
    monkeypatch.setattr(main_module, "HermesNativeClient", _HermesStatusOnly)
    try:
        with TestClient(main_module.app) as client:
            owner = _traveler(client, f"Mobile owner {uuid4().hex[:6]}")
            collaborator = _traveler(client, f"Mobile collaborator {uuid4().hex[:6]}")
            outsider = _traveler(client, f"Mobile outsider {uuid4().hex[:6]}")
            journey_response = client.post(
                "/api/v1/journeys",
                json={
                    "traveler_id": owner["id"],
                    "title": "Mobile Hermes run binding",
                    "city_code": f"CN-MOB-{uuid4().hex[:8].upper()}",
                    "timezone": "Asia/Shanghai",
                    "start_at": "2026-10-18T10:00:00+08:00",
                    "end_at": "2026-10-19T18:00:00+08:00",
                    "budget": {"amount_minor": 10000, "currency": "CNY"},
                },
            )
            assert journey_response.status_code == 201, journey_response.text
            journey_id = journey_response.json()["id"]

            with SessionLocal() as session:
                journey = session.get(Journey, journey_id)
                assert journey is not None
                owner_member = session.scalar(
                    select(JourneyMember).where(
                        JourneyMember.journey_id == journey_id,
                        JourneyMember.traveler_id == owner["id"],
                    )
                )
                assert owner_member is not None
                session.add(
                    JourneyMember(
                        id=str(uuid4()),
                        journey_id=journey_id,
                        traveler_id=collaborator["id"],
                        role="COLLABORATOR",
                        invited_by=owner["id"],
                        expires_at=None,
                        joined_at="2026-10-16T00:00:00+00:00",
                        removed_at=None,
                        preferences_json="{}",
                        created_at="2026-10-16T00:00:00+00:00",
                        updated_at="2026-10-16T00:00:00+00:00",
                    )
                )
                mission = create_mission(
                    session,
                    journey,
                    command="Prepare a safe replan proposal",
                    requested_autonomy="PLAN_ONLY",
                    trigger_event_id=None,
                    use_model_draft=False,
                )
                run_id = "hermes-mobile-" + uuid4().hex
                record_audit(
                    session,
                    action="agent.native_hermes.run_bound",
                    entity_type="HermesNativeRun",
                    entity_id=run_id,
                    journey_id=journey_id,
                    actor_type="TRAVELER",
                    actor_id=owner["id"],
                    after={
                        "mission_id": mission.id,
                        "member_id": owner_member.id,
                        "traveler_id": owner["id"],
                    },
                )
                session.commit()

            path = f"/api/v1/journeys/{journey_id}/agent/hermes/runs/{run_id}/timeline"
            owner_headers = {"Authorization": f"Bearer {owner['access_token']}"}
            collaborator_headers = {"Authorization": f"Bearer {collaborator['access_token']}"}
            outsider_headers = {"Authorization": f"Bearer {outsider['access_token']}"}

            owner_response = client.get(path, headers=owner_headers)
            assert owner_response.status_code == 200, owner_response.text
            assert owner_response.json()["run_id"] == run_id
            assert owner_response.json()["journey_id"] == journey_id
            assert owner_response.json()["events"] == []

            assert client.get(path).status_code == 401
            assert client.get(path, headers=outsider_headers).status_code == 403
            # A member of the same Journey still cannot read another member's private run.
            assert client.get(path, headers=collaborator_headers).status_code == 404
    finally:
        object.__setattr__(settings, "traveler_auth_secret", previous_secret)
