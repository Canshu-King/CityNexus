from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

import app.main as main_module
from app.core.config import settings
from app.db.models import (
    ActionApproval,
    Activity,
    AuditLog,
    Commitment,
    Event,
    Journey,
    JourneyMember,
    LocationObservation,
    MemberSideQuest,
    Place,
    PlanVersion,
    ReplanProposal,
    RecoveryEpoch,
    RouteAcquisitionOperation,
    Traveler,
)
from app.db.session import SessionLocal
from app.execution.clock import execution_clock
from app.traveler_principal import issue_traveler_token
from demo_stage import demo_reset_headers


client = TestClient(main_module.app)
TEST_SECRET = "r64-member-side-quest-test-secret-0123456789"


@pytest.fixture(autouse=True)
def _signed_traveler_tokens():
    previous_secret = settings.traveler_auth_secret
    object.__setattr__(settings, "traveler_auth_secret", TEST_SECRET)
    try:
        yield
    finally:
        object.__setattr__(settings, "traveler_auth_secret", previous_secret)


def _auth(traveler_id: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {issue_traveler_token(traveler_id)}"}


def _active_shared_journey() -> tuple[str, str, str]:
    reset = client.post("/api/v1/demo/reset", headers=demo_reset_headers())
    assert reset.status_code == 200, reset.text
    journey_id = reset.json()["journey_id"]
    plans = client.post(
        f"/api/v1/journeys/{journey_id}/plans/generate",
        json={"candidate_count": 1},
    )
    assert plans.status_code == 201, plans.text
    plan_id = plans.json()[0]["id"]
    assert client.post(f"/api/v1/journeys/{journey_id}/plans/{plan_id}/select").status_code == 200
    assert client.post(f"/api/v1/journeys/{journey_id}/start").status_code == 200
    now = datetime.now(timezone.utc).isoformat()
    other_id = str(uuid4())
    with SessionLocal() as session:
        journey = session.get(Journey, journey_id)
        assert journey is not None
        owner_id = str(journey.traveler_id)
        session.add(Traveler(
            id=other_id,
            display_name="R64同行者",
            email=None,
            locale="zh-CN",
            timezone="UTC",
            created_at=now,
            updated_at=now,
        ))
        session.flush()
        session.add(JourneyMember(
            id=str(uuid4()),
            journey_id=journey_id,
            traveler_id=other_id,
            role="COLLABORATOR",
            invited_by=owner_id,
            expires_at=None,
            joined_at=now,
            removed_at=None,
            preferences_json="{}",
            created_at=now,
            updated_at=now,
        ))
        session.commit()
    started = client.post(
        f"/api/v1/journeys/{journey_id}/operator/start",
        headers=_auth(owner_id),
        json={"interval_seconds": 3600},
    )
    assert started.status_code == 200, started.text
    return journey_id, owner_id, other_id


def _start_split(journey_id: str, traveler_id: str) -> dict:
    response = client.post(
        f"/api/v1/journeys/{journey_id}/agent/commands",
        headers=_auth(traveler_id),
        json={
            "command": "I want to go alone for a while and meet at the next shared stop.",
            "requested_autonomy": "PLAN_ONLY",
        },
    )
    assert response.status_code == 200, response.text
    result = response.json()["planned_separation_result"]
    assert result["outcome"] == "PLANNED_SPLIT_CREATED"
    return result


def _private_place(journey_id: str, *excluded_place_ids: str | None) -> Place:
    with SessionLocal() as session:
        journey = session.get(Journey, journey_id)
        assert journey is not None
        excluded = {str(value) for value in excluded_place_ids if value}
        excluded.update(
            str(value)
            for value in session.scalars(select(Activity.place_id).where(
                Activity.plan_version_id == journey.active_plan_version_id,
                Activity.place_id.is_not(None),
            )).all()
        )
        places = session.scalars(
            select(Place)
            .where(Place.city_code == journey.city_code)
            .order_by(Place.name, Place.id)
        ).all()
        place = next((item for item in places if item.id not in excluded), None)
        assert place is not None, "the demo city needs at least one known side destination"
        return place


def _count(model, *criteria) -> int:
    with SessionLocal() as session:
        return int(session.scalar(select(func.count()).select_from(model).where(*criteria)) or 0)


def test_private_lifecycle_is_member_bound_and_leaves_shared_execution_unchanged():
    journey_id, owner_id, other_id = _active_shared_journey()
    split = _start_split(journey_id, owner_id)
    place = _private_place(journey_id, split.get("rendezvous_place_id"))

    with SessionLocal() as session:
        journey = session.get(Journey, journey_id)
        assert journey is not None
        plan_id = str(journey.active_plan_version_id)
        baseline = {
            "plans": len(session.scalars(select(PlanVersion).where(PlanVersion.journey_id == journey_id)).all()),
            "activities": len(session.scalars(select(Activity).where(Activity.plan_version_id == plan_id)).all()),
            "proposals": len(session.scalars(select(ReplanProposal).where(ReplanProposal.journey_id == journey_id)).all()),
            "approvals": len(session.scalars(select(ActionApproval).where(ActionApproval.journey_id == journey_id)).all()),
            "recovery_epochs": len(session.scalars(select(RecoveryEpoch).where(RecoveryEpoch.journey_id == journey_id)).all()),
            "events": len(session.scalars(select(Event).where(Event.journey_id == journey_id)).all()),
        }

    spoof = client.post(
        f"/api/v1/journeys/{journey_id}/member-side-quests",
        headers=_auth(other_id),
        json={"place_id": place.id, "traveler_id": owner_id, "member_id": "owner"},
    )
    assert spoof.status_code == 422

    created = client.post(
        f"/api/v1/journeys/{journey_id}/member-side-quests",
        headers=_auth(owner_id),
        json={"place_id": place.id},
    )
    assert created.status_code == 201, created.text
    owner_quest_id = created.json()["member_side_quest"]["id"]
    cannot_advance_owners_quest = client.post(
        f"/api/v1/journeys/{journey_id}/member-side-quests/{owner_quest_id}/start",
        headers=_auth(other_id),
    )
    assert cannot_advance_owners_quest.status_code == 404
    quest = created.json()["member_side_quest"]
    assert quest["state"] == "READY"
    assert quest["destination"] == {
        "place_id": place.id,
        "title": place.name,
        "authority": "EXACT_KNOWN_PLACE",
    }
    assert quest["rendezvous"]["activity_id"] == split["rendezvous_activity_id"]
    quest_id = quest["id"]

    started = client.post(
        f"/api/v1/journeys/{journey_id}/member-side-quests/{quest_id}/start",
        headers=_auth(owner_id),
    )
    assert started.status_code == 200, started.text
    assert started.json()["member_side_quest"]["state"] == "EN_ROUTE"
    repeated_start = client.post(
        f"/api/v1/journeys/{journey_id}/member-side-quests/{quest_id}/start",
        headers=_auth(owner_id),
    )
    assert repeated_start.status_code == 200, repeated_start.text
    assert _count(
        AuditLog,
        AuditLog.journey_id == journey_id,
        AuditLog.entity_type == "MemberSideQuest",
        AuditLog.action == "journey.member_side_quest.start",
    ) == 1

    arrived = client.post(
        f"/api/v1/journeys/{journey_id}/member-side-quests/{quest_id}/arrive",
        headers=_auth(owner_id),
    )
    assert arrived.status_code == 200, arrived.text
    arrival_projection = arrived.json()["member_side_quest"]
    assert arrival_projection["state"] == "ARRIVED"
    assert arrival_projection["arrival_claim"] == "MEMBER_REPORTED_NOT_PHYSICAL_PRESENCE_PROOF"
    assert "physical_reunion_claimed" not in arrival_projection

    completed = client.post(
        f"/api/v1/journeys/{journey_id}/member-side-quests/{quest_id}/complete",
        headers=_auth(owner_id),
    )
    assert completed.status_code == 200, completed.text
    final_projection = completed.json()
    assert final_projection["member_side_quest"]["state"] == "COMPLETED"
    assert final_projection["member_side_quest"]["return_state"] == "RETURN_UNKNOWN"
    assert final_projection["member_side_quest"]["shared_plan_changed"] is False
    assert final_projection["group_presence"]["planned_separation"] is not None
    assert "physical_reunion_claimed" not in final_projection["group_presence"]

    with SessionLocal() as session:
        journey = session.get(Journey, journey_id)
        assert journey is not None
        assert str(journey.active_plan_version_id) == plan_id
        assert len(session.scalars(select(PlanVersion).where(PlanVersion.journey_id == journey_id)).all()) == baseline["plans"]
        assert len(session.scalars(select(Activity).where(Activity.plan_version_id == plan_id)).all()) == baseline["activities"]
        assert len(session.scalars(select(ReplanProposal).where(ReplanProposal.journey_id == journey_id)).all()) == baseline["proposals"]
        assert len(session.scalars(select(ActionApproval).where(ActionApproval.journey_id == journey_id)).all()) == baseline["approvals"]
        assert len(session.scalars(select(RecoveryEpoch).where(RecoveryEpoch.journey_id == journey_id)).all()) == baseline["recovery_epochs"]
        assert len(session.scalars(select(Event).where(Event.journey_id == journey_id)).all()) == baseline["events"]


def test_trusted_r63_return_risk_remains_the_only_recovery_handoff(monkeypatch):
    journey_id, owner_id, _other_id = _active_shared_journey()
    split = _start_split(journey_id, owner_id)
    rendezvous_id = split["rendezvous_activity_id"]
    private_place = _private_place(journey_id, split.get("rendezvous_place_id"))
    created = client.post(
        f"/api/v1/journeys/{journey_id}/member-side-quests",
        headers=_auth(owner_id),
        json={"place_id": private_place.id},
    )
    assert created.status_code == 201, created.text
    quest_id = created.json()["member_side_quest"]["id"]

    now = execution_clock.now().astimezone(timezone.utc)
    sample = client.post(
        f"/api/v1/journeys/{journey_id}/location",
        headers=_auth(owner_id),
        json={
            "latitude": 35.0,
            "longitude": 135.0,
            "accuracy_m": 8,
            "captured_at": now.isoformat(),
        },
    )
    assert sample.status_code == 201, sample.text
    with SessionLocal() as session:
        journey = session.get(Journey, journey_id)
        target = session.get(Activity, rendezvous_id)
        observation = session.get(LocationObservation, sample.json()["id"])
        assert journey is not None and target is not None and observation is not None
        observation.source = "DEVICE_ATTESTED"
        session.add(Commitment(
            id=str(uuid4()),
            journey_id=journey_id,
            activity_id=rendezvous_id,
            kind="APPOINTMENT",
            level="C4_Anchored",
            status="ACTIVE",
            monetary_value_minor=0,
            monetary_value_status="KNOWN",
            currency="JPY",
            external_ref="R64-TRUSTED-RENDEZVOUS-RISK",
            policy_json=json.dumps({
                "scheduled_start_at": (now + timedelta(minutes=5)).isoformat(),
                "safety_buffer_min": 5,
                "source": "R64_DETERMINISTIC_REGRESSION_FIXTURE",
            }),
            created_at=now.isoformat(),
            updated_at=now.isoformat(),
        ))
        plan_id = str(journey.active_plan_version_id)
        session.commit()

    def fake_submit(session, journey, route_request):
        operation_id = str(uuid4())
        stamp = execution_clock.now().astimezone(timezone.utc).isoformat()
        session.add(RouteAcquisitionOperation(
            id=operation_id,
            journey_id=journey.id,
            fingerprint=str(uuid4()),
            origin_key=route_request.origin_key,
            target_key=route_request.target_key,
            target_activity_id=route_request.target_activity_id,
            requested_mode=route_request.requested_mode,
            provider_policy_version=route_request.provider_policy_version,
            route_truth_policy_version=route_request.route_truth_policy_version,
            status="COMPLETED",
            phase="COMPLETED",
            outcome="ROUTE_READY",
            request_json="{}",
            result_json=json.dumps({
                "duration_min": 30,
                "distance_m": 2400,
                "provider": "valhalla-http",
                "provenance": "LIVE_PROVIDER_CAPTURE",
            }),
            error_json="{}",
            queued_at=stamp,
            started_at=stamp,
            finished_at=stamp,
            updated_at=stamp,
        ))
        session.flush()
        return session.get(RouteAcquisitionOperation, operation_id), False

    monkeypatch.setattr(main_module, "submit_route_operation", fake_submit)
    monkeypatch.setattr(main_module, "route_operation_payload", lambda *_args, **_kwargs: {
        "status": "COMPLETED",
        "outcome": "ROUTE_READY",
        "provider": "valhalla-http",
        "provider_provenance": "LIVE_PROVIDER_CAPTURE",
        "result": {
            "duration_min": 30,
            "distance_m": 2400,
            "provider": "valhalla-http",
            "provenance": "LIVE_PROVIDER_CAPTURE",
        },
    })
    monkeypatch.setattr(main_module, "scan_guardian", lambda *_args, **_kwargs: {"status": "COMPLETED"})
    routed = client.post(
        f"/api/v1/journeys/{journey_id}/group-presence/route",
        headers=_auth(owner_id),
        json={"location_observation_id": sample.json()["id"], "requested_mode": "WALK"},
    )
    assert routed.status_code == 200, routed.text
    assert routed.json()["shared_commitment_risk"]["state"] == "COMMITMENT_AT_RISK"
    assert routed.json()["guardian_triggered"] is True

    before = client.get(f"/api/v1/journeys/{journey_id}/operator", headers=_auth(owner_id))
    assert before.status_code == 200, before.text
    before_json = before.json()
    assert before_json["group_recovery"]["state"] == "VERIFIED_MEMBER_RISK"
    assert before_json["group_presence"]["state"] == "PLANNED_SPLIT_RETURN_RISK"
    assert before_json["member_side_quest"]["return_state"] == "RETURN_RISK"
    recovery_epochs_before = _count(RecoveryEpoch, RecoveryEpoch.journey_id == journey_id)
    proposals_before = _count(ReplanProposal, ReplanProposal.journey_id == journey_id)

    for action in ("start", "arrive", "complete"):
        advanced = client.post(
            f"/api/v1/journeys/{journey_id}/member-side-quests/{quest_id}/{action}",
            headers=_auth(owner_id),
        )
        assert advanced.status_code == 200, advanced.text
    after = client.get(f"/api/v1/journeys/{journey_id}/operator", headers=_auth(owner_id))
    assert after.status_code == 200, after.text
    after_json = after.json()
    assert after_json["group_recovery"]["state"] == "VERIFIED_MEMBER_RISK"
    assert after_json["group_recovery"]["can_request_planning"] is True
    assert after_json["member_side_quest"]["return_state"] == "RETURN_RISK"
    assert after_json["member_side_quest"]["state"] == "COMPLETED"
    assert after_json["member_side_quest"]["shared_plan_changed"] is False
    assert _count(RecoveryEpoch, RecoveryEpoch.journey_id == journey_id) == recovery_epochs_before
    assert _count(ReplanProposal, ReplanProposal.journey_id == journey_id) == proposals_before
    with SessionLocal() as session:
        journey = session.get(Journey, journey_id)
        assert journey is not None and str(journey.active_plan_version_id) == plan_id


def test_other_member_sees_only_coarse_private_stop_state_and_can_own_an_independent_stop():
    journey_id, owner_id, other_id = _active_shared_journey()
    owner_split = _start_split(journey_id, owner_id)
    owner_place = _private_place(journey_id, owner_split.get("rendezvous_place_id"))
    created = client.post(
        f"/api/v1/journeys/{journey_id}/member-side-quests",
        headers=_auth(owner_id),
        json={"place_id": owner_place.id},
    )
    assert created.status_code == 201, created.text

    with SessionLocal() as session:
        owner_member = session.scalar(select(JourneyMember).where(
            JourneyMember.journey_id == journey_id,
            JourneyMember.traveler_id == owner_id,
        ))
        assert owner_member is not None
        owner_member_id = owner_member.id
    collaborator_projection = client.get(
        f"/api/v1/journeys/{journey_id}/operator", headers=_auth(other_id)
    )
    assert collaborator_projection.status_code == 200, collaborator_projection.text
    other_json = collaborator_projection.json()
    assert other_json["member_side_quest"] is None
    owner_summary = next(
        item for item in other_json["group_presence"]["members"]
        if item["member_id"] == owner_member_id
    )
    assert owner_summary["personal_stop"] == {
        "planned_personal_stop": True,
        "state": "PLANNED",
    }
    assert owner_place.name not in json.dumps(other_json, ensure_ascii=False)

    # Only an authenticated start report advances the coarse member status.
    started = client.post(
        f"/api/v1/journeys/{journey_id}/member-side-quests/{created.json()['member_side_quest']['id']}/start",
        headers=_auth(owner_id),
    )
    assert started.status_code == 200, started.text
    active_projection = client.get(
        f"/api/v1/journeys/{journey_id}/operator", headers=_auth(other_id)
    ).json()
    active_summary = next(
        item for item in active_projection["group_presence"]["members"]
        if item["member_id"] == owner_member_id
    )
    assert active_summary["personal_stop"]["state"] == "ACTIVE_SELF_REPORTED"
    assert owner_place.name not in json.dumps(active_projection, ensure_ascii=False)

    other_split = _start_split(journey_id, other_id)
    other_place = _private_place(
        journey_id,
        other_split.get("rendezvous_place_id"),
        owner_place.id,
    )
    assert other_place.id != owner_place.id
    other_created = client.post(
        f"/api/v1/journeys/{journey_id}/member-side-quests",
        headers=_auth(other_id),
        json={"place_id": other_place.id},
    )
    assert other_created.status_code == 201, other_created.text
    assert other_created.json()["member_side_quest"]["destination"]["title"] == other_place.name

    owner_projection = client.get(
        f"/api/v1/journeys/{journey_id}/operator", headers=_auth(owner_id)
    )
    assert owner_projection.status_code == 200, owner_projection.text
    owner_json = owner_projection.json()
    assert owner_json["member_side_quest"]["destination"]["title"] == owner_place.name
    assert other_place.name not in json.dumps(owner_json, ensure_ascii=False)


def test_descriptive_destination_and_invalid_transitions_never_fabricate_a_place():
    journey_id, owner_id, _other_id = _active_shared_journey()
    _start_split(journey_id, owner_id)
    description = "the tiny blue dessert room behind the station"
    unresolved = client.post(
        f"/api/v1/journeys/{journey_id}/member-side-quests",
        headers=_auth(owner_id),
        json={"destination_text": description},
    )
    assert unresolved.status_code == 201, unresolved.text
    quest = unresolved.json()["member_side_quest"]
    assert quest["state"] == "DESTINATION_UNRESOLVED"
    assert quest["destination"] == {
        "place_id": None,
        "title": description,
        "authority": "DESCRIPTIVE_ONLY",
    }
    quest_id = quest["id"]

    cannot_start = client.post(
        f"/api/v1/journeys/{journey_id}/member-side-quests/{quest_id}/start",
        headers=_auth(owner_id),
    )
    assert cannot_start.status_code == 409
    cannot_complete = client.post(
        f"/api/v1/journeys/{journey_id}/member-side-quests/{quest_id}/complete",
        headers=_auth(owner_id),
    )
    assert cannot_complete.status_code == 409

    exact_place = _private_place(journey_id)
    replaced = client.post(
        f"/api/v1/journeys/{journey_id}/member-side-quests",
        headers=_auth(owner_id),
        json={"place_id": exact_place.id},
    )
    assert replaced.status_code == 201, replaced.text
    assert replaced.json()["member_side_quest"]["state"] == "READY"
    assert replaced.json()["member_side_quest"]["id"] == quest_id
    assert replaced.json()["member_side_quest"]["destination"]["place_id"] == exact_place.id


def test_r63_end_invalidates_the_side_quest_and_removed_members_cannot_advance():
    journey_id, owner_id, _other_id = _active_shared_journey()
    _start_split(journey_id, owner_id)
    with SessionLocal() as session:
        journey = session.get(Journey, journey_id)
        assert journey is not None
        plan_id = str(journey.active_plan_version_id)
    place = _private_place(journey_id)
    created = client.post(
        f"/api/v1/journeys/{journey_id}/member-side-quests",
        headers=_auth(owner_id),
        json={"place_id": place.id},
    )
    assert created.status_code == 201, created.text
    quest_id = created.json()["member_side_quest"]["id"]

    ended = client.post(
        f"/api/v1/journeys/{journey_id}/agent/commands",
        headers=_auth(owner_id),
        json={"command": "I'm back with the group.", "requested_autonomy": "PLAN_ONLY"},
    )
    assert ended.status_code == 200, ended.text
    assert ended.json()["planned_separation_result"]["physical_reunion_claimed"] is False
    with SessionLocal() as session:
        quest = session.get(MemberSideQuest, quest_id)
        assert quest is not None and quest.state == "INVALIDATED"
    stale = client.post(
        f"/api/v1/journeys/{journey_id}/member-side-quests/{quest_id}/start",
        headers=_auth(owner_id),
    )
    assert stale.status_code == 409

    _start_split(journey_id, owner_id)
    replacement = client.post(
        f"/api/v1/journeys/{journey_id}/member-side-quests",
        headers=_auth(owner_id),
        json={"place_id": place.id},
    )
    assert replacement.status_code == 201, replacement.text
    replacement_quest_id = replacement.json()["member_side_quest"]["id"]

    with SessionLocal() as session:
        journey = session.get(Journey, journey_id)
        assert journey is not None
        journey.active_plan_version_id = None
        session.commit()
    plan_changed = client.post(
        f"/api/v1/journeys/{journey_id}/member-side-quests/{replacement_quest_id}/start",
        headers=_auth(owner_id),
    )
    assert plan_changed.status_code == 409
    with SessionLocal() as session:
        quest = session.get(MemberSideQuest, replacement_quest_id)
        assert quest is not None and quest.state == "INVALIDATED"

    with SessionLocal() as session:
        journey = session.get(Journey, journey_id)
        assert journey is not None
        journey.active_plan_version_id = plan_id
        session.commit()
    after_plan_change = client.post(
        f"/api/v1/journeys/{journey_id}/member-side-quests",
        headers=_auth(owner_id),
        json={"place_id": place.id},
    )
    assert after_plan_change.status_code == 201, after_plan_change.text
    next_quest_id = after_plan_change.json()["member_side_quest"]["id"]
    with SessionLocal() as session:
        member = session.scalar(select(JourneyMember).where(
            JourneyMember.journey_id == journey_id,
            JourneyMember.traveler_id == owner_id,
        ))
        assert member is not None
        member.removed_at = datetime.now(timezone.utc).isoformat()
        session.commit()
    removed = client.post(
        f"/api/v1/journeys/{journey_id}/member-side-quests/{next_quest_id}/start",
        headers=_auth(owner_id),
    )
    assert removed.status_code == 403
