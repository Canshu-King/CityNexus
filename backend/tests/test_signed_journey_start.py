from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

import app.main as main_module
import app.traveler_principal as traveler_principal
from app.core.config import settings
from app.db.models import Journey, JourneyMember, JourneyRoleCapability, Traveler
from app.db.session import SessionLocal
from app.traveler_principal import issue_traveler_token


client = TestClient(main_module.app)


@pytest.fixture
def _signed_traveler_auth():
    previous = settings.traveler_auth_secret
    object.__setattr__(settings, "traveler_auth_secret", uuid4().hex + uuid4().hex)
    try:
        yield
    finally:
        object.__setattr__(settings, "traveler_auth_secret", previous)


def _seed_active_journey() -> dict[str, str]:
    owner_id = str(uuid4())
    outsider_id = str(uuid4())
    journey_id = str(uuid4())
    now = datetime.now(timezone.utc)
    now_text = now.isoformat()
    with SessionLocal() as session:
        session.add_all(
            [
                Traveler(
                    id=owner_id,
                    display_name="Start-route owner fixture",
                    email=None,
                    locale="en-US",
                    timezone="UTC",
                    created_at=now_text,
                    updated_at=now_text,
                ),
                Traveler(
                    id=outsider_id,
                    display_name="Start-route outsider fixture",
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
                title="Signed start-route fixture",
                city_code="TEST-START-AUTH",
                timezone="UTC",
                start_at=now_text,
                end_at=(now + timedelta(hours=2)).isoformat(),
                budget_currency="USD",
                budget_amount_minor=0,
                planning_mode="balanced",
                status="ACTIVE",
                active_plan_version_id=None,
                current_activity_id=None,
                created_at=now_text,
                updated_at=now_text,
            )
        )
        session.flush()
        session.add(
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
            )
        )
        if session.get(
            JourneyRoleCapability, ("OWNER", "JOURNEY_EXECUTION_UPDATE")
        ) is None:
            session.add(
                JourneyRoleCapability(
                    role="OWNER",
                    capability="JOURNEY_EXECUTION_UPDATE",
                    scope_message_key="member.scope.owner",
                    created_at=now_text,
                )
            )
        session.commit()
    return {"journey_id": journey_id, "owner_id": owner_id, "outsider_id": outsider_id}


def _auth_headers(traveler_id: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {issue_traveler_token(traveler_id)}"}


def test_active_start_requires_signed_member_and_allows_authorized_owner(
    _signed_traveler_auth,
):
    seeded = _seed_active_journey()
    path = f"/api/v1/journeys/{seeded['journey_id']}/start"

    anonymous = client.post(path)
    assert anonymous.status_code == 401, anonymous.text

    outsider = client.post(path, headers=_auth_headers(seeded["outsider_id"]))
    assert outsider.status_code == 403, outsider.text

    owner = client.post(path, headers=_auth_headers(seeded["owner_id"]))
    assert owner.status_code == 200, owner.text
    assert owner.json()["journey_id"] == seeded["journey_id"]
    assert owner.json()["active_plan_version_id"] is None


def test_active_start_requires_journey_execution_update_capability(
    _signed_traveler_auth, monkeypatch: pytest.MonkeyPatch
):
    seeded = _seed_active_journey()
    checked: list[str] = []

    def deny_capability(_session, _member, capability: str) -> bool:
        checked.append(capability)
        return False

    monkeypatch.setattr(traveler_principal, "member_has_capability", deny_capability)
    response = client.post(
        f"/api/v1/journeys/{seeded['journey_id']}/start",
        headers=_auth_headers(seeded["owner_id"]),
    )

    assert response.status_code == 403, response.text
    assert checked == ["JOURNEY_EXECUTION_UPDATE"]
