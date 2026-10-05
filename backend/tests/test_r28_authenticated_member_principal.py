from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from fastapi.testclient import TestClient

import app.main as main_module
from app.core.config import settings
from app.db.models import ActionApproval, Journey, JourneyMember, JourneyMission, Traveler
from app.db.session import SessionLocal
from app.traveler_principal import issue_traveler_token


client = TestClient(main_module.app)
_TEST_SECRET = "r28-authenticated-member-test-secret-0123456789abcdef"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _seed_identity_fixture() -> dict[str, str]:
    owner_id = str(uuid4())
    admin_id = str(uuid4())
    outsider_id = str(uuid4())
    journey_id = str(uuid4())
    owner_member_id = str(uuid4())
    admin_member_id = str(uuid4())
    mission_id = str(uuid4())
    approval_id = str(uuid4())
    clarification_id = str(uuid4())
    now = _now()
    with SessionLocal() as session:
        for traveler_id, name in (
            (owner_id, "R28 owner"),
            (admin_id, "R28 admin"),
            (outsider_id, "R28 outsider"),
        ):
            session.add(
                Traveler(
                    id=traveler_id,
                    display_name=name,
                    email=None,
                    locale="en-US",
                    timezone="UTC",
                    created_at=now,
                    updated_at=now,
                )
            )
        session.flush()
        session.add(
            Journey(
                id=journey_id,
                traveler_id=owner_id,
                title="R28 authenticated collective",
                city_code="TYO",
                timezone="UTC",
                start_at=now,
                end_at=(datetime.now(timezone.utc) + timedelta(hours=6)).isoformat(),
                budget_currency="JPY",
                budget_amount_minor=10000,
                planning_mode="balanced",
                status="ACTIVE",
                active_plan_version_id=None,
                current_activity_id=None,
                created_at=now,
                updated_at=now,
            )
        )
        session.flush()
        session.add_all(
            [
                JourneyMember(
                    id=owner_member_id,
                    journey_id=journey_id,
                    traveler_id=owner_id,
                    role="OWNER",
                    invited_by=owner_id,
                    expires_at=None,
                    joined_at=now,
                    removed_at=None,
                    preferences_json="{}",
                    created_at=now,
                    updated_at=now,
                ),
                JourneyMember(
                    id=admin_member_id,
                    journey_id=journey_id,
                    traveler_id=admin_id,
                    role="ADMIN",
                    invited_by=owner_id,
                    expires_at=None,
                    joined_at=now,
                    removed_at=None,
                    preferences_json="{}",
                    created_at=now,
                    updated_at=now,
                ),
            ]
        )
        session.flush()
        session.add(
            JourneyMission(
                id=mission_id,
                journey_id=journey_id,
                traveler_id=owner_id,
                trigger_event_id=None,
                user_text="Choose the shared option.",
                requested_autonomy="EXECUTE_WITHIN_BOUNDS",
                status="WAITING_FOR_MEMBERS",
                clarification_json=json.dumps(
                    {
                        "kind": "COLLECTIVE_TRADEOFF",
                        "status": "WAITING_FOR_MEMBERS",
                        "clarification_id": clarification_id,
                        "required_member_ids": [owner_member_id, admin_member_id],
                        "candidate_options": [],
                        "responses": {},
                    },
                    sort_keys=True,
                ),
                created_at=now,
                started_at=now,
            )
        )
        session.add(
            ActionApproval(
                id=approval_id,
                traveler_id=owner_id,
                journey_id=journey_id,
                action="ACCEPT_REPLAN",
                target_type="ReplanProposal",
                target_id=str(uuid4()),
                request_fingerprint="r28-auth-principal-test",
                status="PENDING",
                required_decision="REQUIRE_CONFIRMATION",
                created_at=now,
                expires_at=(datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat(),
            )
        )
        session.commit()
    return {
        "owner_id": owner_id,
        "admin_id": admin_id,
        "outsider_id": outsider_id,
        "journey_id": journey_id,
        "owner_member_id": owner_member_id,
        "admin_member_id": admin_member_id,
        "mission_id": mission_id,
        "approval_id": approval_id,
        "clarification_id": clarification_id,
    }


def _set_secret(value: str | None) -> str | None:
    previous = settings.traveler_auth_secret
    object.__setattr__(settings, "traveler_auth_secret", value)
    return previous


def test_r28_collective_response_requires_authenticated_traveler() -> None:
    previous = _set_secret(_TEST_SECRET)
    try:
        seeded = _seed_identity_fixture()
        response = client.post(
            f"/api/v1/journeys/{seeded['journey_id']}/missions/{seeded['mission_id']}/"
            f"collective-clarification/{seeded['owner_member_id']}",
            json={
                "clarification_id": seeded["clarification_id"],
                "proposal_id": str(uuid4()),
            },
        )
        assert response.status_code == 401, response.text
    finally:
        _set_secret(previous)


def test_r28_owner_token_cannot_answer_admin_member_path() -> None:
    previous = _set_secret(_TEST_SECRET)
    try:
        seeded = _seed_identity_fixture()
        owner_token = issue_traveler_token(seeded["owner_id"])
        response = client.post(
            f"/api/v1/journeys/{seeded['journey_id']}/missions/{seeded['mission_id']}/"
            f"collective-clarification/{seeded['admin_member_id']}",
            headers=_auth(owner_token),
            json={
                "clarification_id": seeded["clarification_id"],
                "proposal_id": str(uuid4()),
            },
        )
        assert response.status_code == 403, response.text
    finally:
        _set_secret(previous)


def test_r28_authenticated_outsider_cannot_answer_collective_decision() -> None:
    previous = _set_secret(_TEST_SECRET)
    try:
        seeded = _seed_identity_fixture()
        outsider_token = issue_traveler_token(seeded["outsider_id"])
        response = client.post(
            f"/api/v1/journeys/{seeded['journey_id']}/missions/{seeded['mission_id']}/"
            f"collective-clarification/{seeded['owner_member_id']}",
            headers=_auth(outsider_token),
            json={
                "clarification_id": seeded["clarification_id"],
                "proposal_id": str(uuid4()),
            },
        )
        assert response.status_code == 403, response.text
    finally:
        _set_secret(previous)


def test_r28_withdrawn_member_token_is_rejected() -> None:
    previous = _set_secret(_TEST_SECRET)
    try:
        seeded = _seed_identity_fixture()
        with SessionLocal() as session:
            member = session.get(JourneyMember, seeded["admin_member_id"])
            assert member is not None
            member.removed_at = _now()
            member.updated_at = member.removed_at
            session.commit()
        admin_token = issue_traveler_token(seeded["admin_id"])
        response = client.post(
            f"/api/v1/journeys/{seeded['journey_id']}/missions/{seeded['mission_id']}/"
            f"collective-clarification/{seeded['admin_member_id']}",
            headers=_auth(admin_token),
            json={
                "clarification_id": seeded["clarification_id"],
                "proposal_id": str(uuid4()),
            },
        )
        assert response.status_code == 403, response.text
    finally:
        _set_secret(previous)


def test_r28_approval_requires_owner_principal_and_journey_update_capability() -> None:
    previous = _set_secret(_TEST_SECRET)
    try:
        seeded = _seed_identity_fixture()
        route = (
            f"/api/v1/journeys/{seeded['journey_id']}/agent/approvals/"
            f"{seeded['approval_id']}/approve"
        )

        unauthenticated = client.post(
            route, json={"approval_method": "USER_CONFIRMATION"}
        )
        assert unauthenticated.status_code == 401, unauthenticated.text

        admin_token = issue_traveler_token(seeded["admin_id"])
        admin_attempt = client.post(
            route,
            headers=_auth(admin_token),
            json={"approval_method": "USER_CONFIRMATION"},
        )
        assert admin_attempt.status_code == 403, admin_attempt.text

        owner_token = issue_traveler_token(seeded["owner_id"])
        owner_approval = client.post(
            route,
            headers=_auth(owner_token),
            json={"approval_method": "USER_CONFIRMATION"},
        )
        assert owner_approval.status_code == 200, owner_approval.text
        assert owner_approval.json()["status"] == "APPROVED"
        assert owner_approval.json()["approved_by"] == seeded["owner_id"] if "approved_by" in owner_approval.json() else True
    finally:
        _set_secret(previous)
