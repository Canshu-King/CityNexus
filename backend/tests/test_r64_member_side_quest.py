from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import httpx
import pytest
from demo_stage import demo_reset_headers
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import func, select

import app.main as main_module
from app.core.config import settings
from app.db.models import (
    ActionApproval,
    AgentRun,
    Activity,
    AuditLog,
    Commitment,
    Event,
    GuardianPulse,
    Journey,
    JourneyIntent,
    JourneyMember,
    LocationObservation,
    MemberLiveMomentScoutReceipt,
    MemberSideQuest,
    MemberSideQuestReturnReport,
    PlannedSplitMeetupHandshake,
    MobilityFact,
    Place,
    PlanVersion,
    ProviderCall,
    RealPlaceCandidate,
    RecoveryEpoch,
    ReplanProposal,
    RouteAcquisitionOperation,
    Traveler,
)
from app.db.session import SessionLocal
from app.execution.clock import execution_clock
from app.integrations.mobility import runtime as mobility_runtime
from app.traveler_principal import issue_traveler_token

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


@pytest.fixture(autouse=True)
def _restore_live_place_provider_settings():
    previous_enabled = settings.real_city_enabled
    previous_mode = settings.real_city_mode
    try:
        yield
    finally:
        object.__setattr__(settings, "real_city_enabled", previous_enabled)
        object.__setattr__(settings, "real_city_mode", previous_mode)


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



def test_r66_dense_catalog_cap_preserves_nearest_even_if_older(monkeypatch):
    # Bounded shortlist must not be newest-records-first: older nearby venues
    # are valid discoveries when a dense city has many newer, farther rows.
    import app.execution.moment_scout as scout_module

    journey_id, _owner_id, _other_id = _active_shared_journey()
    with SessionLocal() as session:
        journey = session.get(Journey, journey_id)
        assert journey is not None
        nearby_id, farther_id = str(uuid4()), str(uuid4())
        common = {
            "city_code": journey.city_code,
            "category": "cafe",
            "opening_hours_json": "{}",
            "tags_json": "[]",
            "metadata_json": "{}",
            "coordinate_system": "WGS84",
        }
        session.add_all([
            Place(
                id=nearby_id,
                provider_key="r66-locality-regression",
                external_id=nearby_id,
                name="Older nearest venue",
                latitude=70.0,
                longitude=30.0,
                updated_at="2000-01-01T00:00:00+00:00",
                **common,
            ),
            Place(
                id=farther_id,
                provider_key="r66-locality-regression",
                external_id=farther_id,
                name="Newer but distant venue",
                latitude=70.04,
                longitude=30.0,
                updated_at="2100-01-01T00:00:00+00:00",
                **common,
            ),
        ])
        session.commit()
        monkeypatch.setattr(scout_module, "MAX_CITY_SHORTLIST_ROWS", 1)
        rows = scout_module._bounded_place_query(
            session,
            city_code=journey.city_code,
            latitude=70.0,
            longitude=30.0,
        )
        assert [row.id for row in rows] == [nearby_id]


def test_r66_moment_scout_is_private_read_only_and_revalidates_explicit_selection():
    journey_id, owner_id, other_id = _active_shared_journey()
    place = _private_place(journey_id)
    # Put one fixture-backed known Place at the consented sample so ranking has
    # a deterministic nearest result without asking an external provider.
    with SessionLocal() as session:
        place = session.get(Place, place.id)
        assert place is not None
        place.latitude = 35.123456
        place.longitude = 135.123456
        place.category = "cafe"
        place.provider_key = "r66-fixture"
        session.commit()

    sample = client.post(
        f"/api/v1/journeys/{journey_id}/location",
        headers=_auth(owner_id),
        json={
            "latitude": 35.123456,
            "longitude": 135.123456,
            "accuracy_m": 8,
            "captured_at": execution_clock.now().astimezone(timezone.utc).isoformat(),
        },
    )
    assert sample.status_code == 201, sample.text
    observation_id = sample.json()["id"]
    with SessionLocal() as session:
        other_member = session.scalar(
            select(JourneyMember).where(
                JourneyMember.journey_id == journey_id,
                JourneyMember.traveler_id == other_id,
            )
        )
        assert other_member is not None
        foreign_observation_id = str(uuid4())
        session.add(LocationObservation(
            id=foreign_observation_id,
            journey_id=journey_id,
            traveler_id=other_id,
            journey_member_id=other_member.id,
            latitude=35.123456,
            longitude=135.123456,
            accuracy_m=8,
            captured_at=execution_clock.now().astimezone(timezone.utc).isoformat(),
            source="FOREGROUND_WEB",
        ))
        session.commit()
    with SessionLocal() as session:
        journey = session.get(Journey, journey_id)
        assert journey is not None
        active_plan_id = str(journey.active_plan_version_id)
        before = {
            "journey": (journey.active_plan_version_id, journey.current_activity_id),
            "plan_count": _count(PlanVersion, PlanVersion.journey_id == journey_id),
            "activity_count": _count(Activity, Activity.plan_version_id == active_plan_id),
            "intent_count": _count(JourneyIntent, JourneyIntent.journey_id == journey_id),
            "quest_count": _count(MemberSideQuest, MemberSideQuest.journey_id == journey_id),
        }

    scout = client.post(
        f"/api/v1/journeys/{journey_id}/moment-scout",
        headers=_auth(owner_id),
        json={
            "location_observation_id": observation_id,
            "budget_minutes": 30,
            "interest": "COFFEE_FOOD",
        },
    )
    assert scout.status_code == 200, scout.text
    result = scout.json()
    assert result["scout_state"] == "OPTIONS_AVAILABLE"
    assert 1 <= len(result["candidates"]) <= 3
    assert result["rendezvous"]["activity_id"]
    assert result["candidates"][0]["place_id"] == place.id
    assert result["candidates"][0]["straight_line_distance_m"] == 0
    assert result["candidates"][0]["place_provenance"] == "DEMO_FIXTURE"
    assert all(item["opening_state"] == "UNKNOWN" for item in result["candidates"])
    assert all(item["fit_authority"] == "UNVERIFIED" for item in result["candidates"])
    assert result["rendezvous"]["time_state"] == "AVAILABLE"
    assert isinstance(result["rendezvous"]["minutes_until"], int)
    assert "latitude" not in json.dumps(result) and "longitude" not in json.dumps(result)
    assert "ROUTE" in result["evidence_boundary"] and "GUARANTEE" in result["evidence_boundary"]

    with pytest.raises(HTTPException) as passed_rendezvous:
        main_module.select_moment_scout_candidate(
            current_scout={
                "scout_context": "f" * 64,
                "candidates": [{"place_id": place.id}],
                "rendezvous": {"time_state": "PAST"},
            },
            scout_context="f" * 64,
            place_id=place.id,
        )
    assert passed_rendezvous.value.status_code == 409
    assert passed_rendezvous.value.detail == "MOMENT_SCOUT_RENDEZVOUS_TIME_PASSED"

    foreign_observation = client.post(
        f"/api/v1/journeys/{journey_id}/moment-scout",
        headers=_auth(owner_id),
        json={"location_observation_id": foreign_observation_id},
    )
    assert foreign_observation.status_code == 403
    assert place.name not in foreign_observation.text

    unauthorized = client.post(
        f"/api/v1/journeys/{journey_id}/moment-scout",
        headers=_auth(other_id),
        json={"location_observation_id": observation_id},
    )
    assert unauthorized.status_code in {403, 409}
    assert place.name not in unauthorized.text

    with SessionLocal() as session:
        journey = session.get(Journey, journey_id)
        assert journey is not None
        assert (journey.active_plan_version_id, journey.current_activity_id) == before["journey"]
        assert _count(PlanVersion, PlanVersion.journey_id == journey_id) == before["plan_count"]
        assert _count(Activity, Activity.plan_version_id == active_plan_id) == before["activity_count"]
        assert _count(JourneyIntent, JourneyIntent.journey_id == journey_id) == before["intent_count"]
        assert _count(MemberSideQuest, MemberSideQuest.journey_id == journey_id) == before["quest_count"]
        assert _count(
            AuditLog,
            AuditLog.journey_id == journey_id,
            AuditLog.action.like("journey.moment_scout.%"),
        ) == 0

    selection_path = f"/api/v1/journeys/{journey_id}/moment-scout/select"
    selection_data = {
        "location_observation_id": observation_id,
        "budget_minutes": 30,
        "interest": "COFFEE_FOOD",
        "place_id": place.id,
        "scout_context": "0" * 64,
    }
    stale = client.post(selection_path, headers=_auth(owner_id), json=selection_data)
    assert stale.status_code == 409
    assert "MOMENT_SCOUT_CONTEXT_STALE" in stale.text
    assert _count(MemberSideQuest, MemberSideQuest.journey_id == journey_id) == 0

    selection_data["scout_context"] = result["scout_context"]
    selected = client.post(selection_path, headers=_auth(owner_id), json=selection_data)
    assert selected.status_code == 201, selected.text
    assert selected.json()["member_side_quest"]["state"] == "READY"
    assert selected.json()["member_side_quest"]["destination"]["place_id"] == place.id
    assert selected.json()["member_side_quest"]["rendezvous"]["activity_id"] == result["rendezvous"]["activity_id"]
    assert selected.json()["group_presence"]["planned_separation"] is not None
    collaborator_view = client.get(
        f"/api/v1/journeys/{journey_id}/operator", headers=_auth(other_id)
    )
    assert collaborator_view.status_code == 200, collaborator_view.text
    assert place.name not in collaborator_view.text
    with SessionLocal() as session:
        selected_quest = session.get(MemberSideQuest, selected.json()["member_side_quest"]["id"])
        assert selected_quest is not None
        selected_quest.state = "COMPLETED"
        session.commit()
    after_private_stop = client.post(
        f"/api/v1/journeys/{journey_id}/moment-scout",
        headers=_auth(owner_id),
        json={"location_observation_id": observation_id},
    )
    assert after_private_stop.status_code == 409
    assert "MOMENT_SCOUT_RETURN_TO_SHARED_GROUP_FIRST" in after_private_stop.text
    with SessionLocal() as session:
        member = session.scalar(
            select(JourneyMember).where(
                JourneyMember.journey_id == journey_id,
                JourneyMember.traveler_id == other_id,
            )
        )
        assert member is not None
        member.removed_at = execution_clock.now().astimezone(timezone.utc).isoformat()
        session.commit()
    removed_member = client.post(
        f"/api/v1/journeys/{journey_id}/moment-scout",
        headers=_auth(other_id),
        json={"location_observation_id": observation_id},
    )
    assert removed_member.status_code in {403, 404}
    assert place.name not in removed_member.text


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


def test_r65_head_back_is_idempotent_without_location_and_only_coarsely_shared():
    journey_id, owner_id, other_id = _active_shared_journey()
    split = _start_split(journey_id, owner_id)
    place = _private_place(journey_id, split.get("rendezvous_place_id"))
    created = client.post(
        f"/api/v1/journeys/{journey_id}/member-side-quests",
        headers=_auth(owner_id),
        json={"place_id": place.id},
    )
    assert created.status_code == 201, created.text
    quest_id = created.json()["member_side_quest"]["id"]
    for action in ("start", "arrive", "complete"):
        advanced = client.post(
            f"/api/v1/journeys/{journey_id}/member-side-quests/{quest_id}/{action}",
            headers=_auth(owner_id),
        )
        assert advanced.status_code == 200, advanced.text

    with SessionLocal() as session:
        journey = session.get(Journey, journey_id)
        assert journey is not None
        plan_id = str(journey.active_plan_version_id)

    endpoint = f"/api/v1/journeys/{journey_id}/member-side-quests/{quest_id}/head-back"
    first = client.post(endpoint, headers=_auth(owner_id))
    assert first.status_code == 200, first.text
    report = first.json()["member_side_quest"]["return_report"]
    assert report["status"] == "RETURN_STARTED_REPORTED"
    assert report["physical_presence_verified"] is False

    repeated = client.post(endpoint, headers=_auth(owner_id))
    assert repeated.status_code == 200, repeated.text
    assert repeated.json()["member_side_quest"]["return_report"]["reported_at"] == report["reported_at"]
    assert _count(
        MemberSideQuestReturnReport,
        MemberSideQuestReturnReport.side_quest_id == quest_id,
    ) == 1
    assert _count(
        AuditLog,
        AuditLog.journey_id == journey_id,
        AuditLog.action == "journey.member_side_quest.return_started_reported",
    ) == 1

    with SessionLocal() as session:
        owner_member = session.scalar(select(JourneyMember).where(
            JourneyMember.journey_id == journey_id,
            JourneyMember.traveler_id == owner_id,
        ))
        assert owner_member is not None
        owner_member_id = owner_member.id
    collaborator = client.get(
        f"/api/v1/journeys/{journey_id}/operator", headers=_auth(other_id)
    )
    assert collaborator.status_code == 200, collaborator.text
    collaborator_json = collaborator.json()
    owner_summary = next(
        item for item in collaborator_json["group_presence"]["members"]
        if item["member_id"] == owner_member_id
    )
    assert owner_summary["personal_stop"] == {
        "planned_personal_stop": True,
        "state": "RETURN_STARTED_REPORTED",
    }
    assert place.name not in json.dumps(collaborator_json, ensure_ascii=False)
    assert "physical_presence_verified" not in json.dumps(collaborator_json)

    # A later private stop in the same split must not inherit the previous stop's report.
    next_place = _private_place(journey_id, place.id, split.get("rendezvous_place_id"))
    replacement = client.post(
        f"/api/v1/journeys/{journey_id}/member-side-quests",
        headers=_auth(owner_id),
        json={"place_id": next_place.id},
    )
    assert replacement.status_code == 201, replacement.text
    next_summary = client.get(
        f"/api/v1/journeys/{journey_id}/operator", headers=_auth(other_id)
    ).json()
    next_owner_summary = next(
        item for item in next_summary["group_presence"]["members"]
        if item["member_id"] == owner_member_id
    )
    assert next_owner_summary["personal_stop"]["state"] == "PLANNED"
    assert next_place.name not in json.dumps(next_summary, ensure_ascii=False)

    with SessionLocal() as session:
        journey = session.get(Journey, journey_id)
        assert journey is not None and str(journey.active_plan_version_id) == plan_id


def test_r65_private_navigation_and_fit_preview_reject_synthetic_routes_without_shared_records(monkeypatch):
    journey_id, owner_id, other_id = _active_shared_journey()
    split = _start_split(journey_id, owner_id)
    place = _private_place(journey_id, split.get("rendezvous_place_id"))
    created = client.post(
        f"/api/v1/journeys/{journey_id}/member-side-quests",
        headers=_auth(owner_id),
        json={"place_id": place.id},
    )
    assert created.status_code == 201, created.text
    quest_id = created.json()["member_side_quest"]["id"]
    sample = client.post(
        f"/api/v1/journeys/{journey_id}/location",
        headers=_auth(owner_id),
        json={
            "latitude": 35.0,
            "longitude": 135.0,
            "accuracy_m": 8,
            "captured_at": execution_clock.now().astimezone(timezone.utc).isoformat(),
        },
    )
    assert sample.status_code == 201, sample.text
    observation_id = sample.json()["id"]
    now = execution_clock.now().astimezone(timezone.utc)
    with SessionLocal() as session:
        target = session.get(Activity, split["rendezvous_activity_id"])
        assert target is not None
        session.add(Commitment(
            id=str(uuid4()),
            journey_id=journey_id,
            activity_id=target.id,
            kind="APPOINTMENT",
            level="C4_Anchored",
            status="ACTIVE",
            monetary_value_minor=0,
            monetary_value_status="KNOWN",
            currency="JPY",
            external_ref="R65-PRIVATE-DETOUR-FIT-FIXTURE",
            policy_json=json.dumps({
                "scheduled_start_at": (now + timedelta(hours=3)).isoformat(),
                "safety_buffer_min": 15,
                "source": "R65_TEST_ONLY_CONTROLLED_COMMITMENT",
            }),
            created_at=now.isoformat(),
            updated_at=now.isoformat(),
        ))
        session.commit()

    captured_pairs = []

    def synthetic_capture(_session, _journey, pairs, **kwargs):
        pair = tuple(pairs[0])
        captured_pairs.append((pair, kwargs["operation_key"]))
        fact = type("SyntheticFact", (), {
            "provider_key": "mock-mobility",
            "route_provenance": "SYNTHETIC_FIXTURE",
            "fact_quality": "SYNTHETIC_FIXTURE",
            "minutes": 5,
            "distance_m": 100,
            "captured_at": execution_clock.now().astimezone(timezone.utc),
            "mode": kwargs.get("requested_mode") or "WALK",
            "route_geometry": [[135.0, 35.0], [135.1, 35.1]],
        })()
        return type("Capture", (), {
            "snapshot": type("Snapshot", (), {"facts": {pair: fact}})(),
        })()

    monkeypatch.setattr(mobility_runtime, "capture_runtime_mobility_snapshot", synthetic_capture)
    before_route_ops = _count(RouteAcquisitionOperation, RouteAcquisitionOperation.journey_id == journey_id)
    before_mobility_facts = _count(MobilityFact, MobilityFact.journey_id == journey_id)

    preview = client.post(
        f"/api/v1/journeys/{journey_id}/member-side-quests/{quest_id}/fit-preview",
        headers=_auth(owner_id),
        json={"location_observation_id": observation_id, "dwell_minutes": 20},
    )
    assert preview.status_code == 200, preview.text
    assert preview.json()["state"] == "UNKNOWN"
    assert preview.json()["reason_code"] == "QUALIFYING_LIVE_ROUTE_EVIDENCE_UNAVAILABLE"
    assert preview.json()["outbound_eta_minutes"] is None
    assert preview.json()["return_eta_minutes"] is None
    assert preview.json()["plan_unchanged"] is True

    navigation = client.post(
        f"/api/v1/journeys/{journey_id}/member-side-quests/{quest_id}/navigate",
        headers=_auth(owner_id),
        json={"location_observation_id": observation_id},
    )
    assert navigation.status_code == 200, navigation.text
    assert navigation.json()["status"] == "UNKNOWN"
    assert navigation.json()["route"] is None
    assert navigation.json()["plan_unchanged"] is True
    assert len(captured_pairs) == 3  # outbound + hypothetical return + one navigation leg
    assert all(key.startswith("private-side-quest:") for _pair, key in captured_pairs)
    assert _count(RouteAcquisitionOperation, RouteAcquisitionOperation.journey_id == journey_id) == before_route_ops
    assert _count(MobilityFact, MobilityFact.journey_id == journey_id) == before_mobility_facts

    def live_capture(_session, _journey, pairs, **kwargs):
        pair = tuple(pairs[0])
        fact = type("LiveTestFact", (), {
            "provider_key": "valhalla-r65-test-fixture",
            "route_provenance": "LIVE_PROVIDER_CAPTURE",
            "fact_quality": "LIVE_PROVIDER_CAPTURE",
            "minutes": 10 if pair[1] == place.id else 15,
            "distance_m": 900,
            "captured_at": execution_clock.now().astimezone(timezone.utc),
            "mode": kwargs.get("requested_mode") or "WALK",
            "route_geometry": [[135.0, 35.0], [135.1, 35.1]],
        })()
        return type("Capture", (), {
            "snapshot": type("Snapshot", (), {"facts": {pair: fact}})(),
        })()

    monkeypatch.setattr(mobility_runtime, "capture_runtime_mobility_snapshot", live_capture)
    before_guardian = _count(GuardianPulse, GuardianPulse.journey_id == journey_id)
    before_events = _count(Event, Event.journey_id == journey_id)
    grounded_preview = client.post(
        f"/api/v1/journeys/{journey_id}/member-side-quests/{quest_id}/fit-preview",
        headers=_auth(owner_id),
        json={"location_observation_id": observation_id, "dwell_minutes": 20},
    )
    assert grounded_preview.status_code == 200, grounded_preview.text
    grounded = grounded_preview.json()
    assert grounded["state"] == "FITS_WITH_BUFFER"
    assert grounded["outbound_eta_minutes"] == 10
    assert grounded["return_eta_minutes"] == 15
    assert grounded["recommended_leave_by"] is not None
    assert grounded["safety_buffer_minutes"] == 15
    assert grounded["provenance"]["outbound"]["provenance"] == "LIVE_PROVIDER_CAPTURE"
    assert grounded["provenance"]["return"]["provenance"] == "LIVE_PROVIDER_CAPTURE"
    assert grounded["origin_basis"]["outbound"] == "AUTHENTICATED_FRESH_MEMBER_LOCATION"
    assert grounded["origin_basis"]["return"] == "HYPOTHETICAL_SIDE_PLACE"
    assert grounded["plan_unchanged"] is True
    assert _count(GuardianPulse, GuardianPulse.journey_id == journey_id) == before_guardian
    assert _count(Event, Event.journey_id == journey_id) == before_events

    # A mathematical leave-by is not useful guidance once it cannot be met.
    # Capture receipts here remain controlled test-only provider fixtures.
    with SessionLocal() as session:
        commitment = session.scalar(select(Commitment).where(
            Commitment.journey_id == journey_id,
            Commitment.external_ref == "R65-PRIVATE-DETOUR-FIT-FIXTURE",
        ))
        assert commitment is not None
        policy = json.loads(commitment.policy_json or "{}")
        policy["scheduled_start_at"] = (
            execution_clock.now().astimezone(timezone.utc) + timedelta(minutes=48)
        ).isoformat()
        commitment.policy_json = json.dumps(policy)
        session.commit()
    tight = client.post(
        f"/api/v1/journeys/{journey_id}/member-side-quests/{quest_id}/fit-preview",
        headers=_auth(owner_id),
        json={"location_observation_id": observation_id, "dwell_minutes": 20},
    )
    assert tight.status_code == 200, tight.text
    assert tight.json()["state"] == "TIGHT_RETURN"
    assert tight.json()["recommended_leave_by"] is None

    with SessionLocal() as session:
        commitment = session.scalar(select(Commitment).where(
            Commitment.journey_id == journey_id,
            Commitment.external_ref == "R65-PRIVATE-DETOUR-FIT-FIXTURE",
        ))
        assert commitment is not None
        policy = json.loads(commitment.policy_json or "{}")
        policy["scheduled_start_at"] = (
            execution_clock.now().astimezone(timezone.utc) + timedelta(minutes=2)
        ).isoformat()
        commitment.policy_json = json.dumps(policy)
        session.commit()
    impossible = client.post(
        f"/api/v1/journeys/{journey_id}/member-side-quests/{quest_id}/fit-preview",
        headers=_auth(owner_id),
        json={"location_observation_id": observation_id, "dwell_minutes": 20},
    )
    assert impossible.status_code == 200, impossible.text
    assert impossible.json()["state"] == "DOES_NOT_FIT"
    assert impossible.json()["recommended_leave_by"] is None
    assert impossible.json()["reason_code"] == "INSUFFICIENT_TIME_FOR_PRIVATE_DETOUR"

    other_sample = client.post(
        f"/api/v1/journeys/{journey_id}/location",
        headers=_auth(other_id),
        json={
            "latitude": 35.1,
            "longitude": 135.1,
            "accuracy_m": 8,
            "captured_at": execution_clock.now().astimezone(timezone.utc).isoformat(),
        },
    )
    assert other_sample.status_code == 201, other_sample.text
    foreign_observation = client.post(
        f"/api/v1/journeys/{journey_id}/member-side-quests/{quest_id}/navigate",
        headers=_auth(owner_id),
        json={"location_observation_id": other_sample.json()["id"]},
    )
    assert foreign_observation.status_code == 403

    # A group member cannot use the owner's private quest or its captured location.
    forbidden = client.post(
        f"/api/v1/journeys/{journey_id}/member-side-quests/{quest_id}/navigate",
        headers=_auth(other_id),
        json={"location_observation_id": observation_id},
    )
    assert forbidden.status_code == 404

    def cancel_during_capture(session, _journey, pairs, **_kwargs):
        current = session.get(MemberSideQuest, quest_id)
        assert current is not None
        current.state = "CANCELLED"
        session.flush()
        pair = tuple(pairs[0])
        return type("Capture", (), {
            "snapshot": type("Snapshot", (), {"facts": {pair: None}})(),
        })()

    monkeypatch.setattr(mobility_runtime, "capture_runtime_mobility_snapshot", cancel_during_capture)
    stale = client.post(
        f"/api/v1/journeys/{journey_id}/member-side-quests/{quest_id}/navigate",
        headers=_auth(owner_id),
        json={"location_observation_id": observation_id},
    )
    assert stale.status_code == 409
    with SessionLocal() as session:
        current = session.get(MemberSideQuest, quest_id)
        assert current is not None and current.state == "READY"


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


def test_r68_navigation_target_is_owner_only_exact_and_read_only(monkeypatch):
    import app.agent.autorun as autorun_module

    autorun_module.stop_autorun()
    monkeypatch.setattr(main_module, "start_autorun", lambda **_kwargs: {"enabled": False})
    journey_id, owner_id, other_id = _active_shared_journey()
    split = _start_split(journey_id, owner_id)
    private_place = _private_place(journey_id, split.get("rendezvous_place_id"))
    created = client.post(
        f"/api/v1/journeys/{journey_id}/member-side-quests",
        headers=_auth(owner_id),
        json={"place_id": private_place.id},
    )
    assert created.status_code == 201, created.text
    quest_id = created.json()["member_side_quest"]["id"]
    endpoint = f"/api/v1/journeys/{journey_id}/member-side-quests/{quest_id}/navigation-targets"

    shared_models = (PlanVersion, Activity, ReplanProposal, GuardianPulse, AgentRun)

    def shared_snapshot() -> dict[str, tuple[tuple[object, ...], ...]]:
        with SessionLocal() as session:
            result: dict[str, tuple[tuple[object, ...], ...]] = {}
            for model in shared_models:
                if model is Activity:
                    rows = session.scalars(select(Activity).where(
                        Activity.plan_version_id.in_(
                            select(PlanVersion.id).where(PlanVersion.journey_id == journey_id)
                        )
                    )).all()
                else:
                    rows = session.scalars(
                        select(model).where(model.journey_id == journey_id)
                    ).all()
                result[model.__name__] = tuple(sorted(
                    [
                        tuple(getattr(row, column.name) for column in model.__table__.columns)
                        for row in rows
                    ],
                    key=repr,
                ))
            return result

    before_read = shared_snapshot()
    owner_target = client.get(endpoint, headers=_auth(owner_id))
    assert owner_target.status_code == 200, owner_target.text
    private_target = owner_target.json()["target"]
    assert private_target == {
        "kind": "PRIVATE_STOP",
        "place_id": private_place.id,
        "name": private_place.name,
        "latitude": private_place.latitude,
        "longitude": private_place.longitude,
        "coordinate_system": "WGS84",
        "provenance": {
            "provider_key": private_place.provider_key,
            "external_id": private_place.external_id,
            "source_coordinate_system": private_place.source_coordinate_system,
        },
        "navigation_available": True,
        "unavailable_reason": None,
    }
    serialized_target = json.dumps(owner_target.json(), ensure_ascii=False).casefold()
    assert "origin" not in serialized_target
    assert "location_observation" not in serialized_target
    assert shared_snapshot() == before_read

    foreign = client.get(endpoint, headers=_auth(other_id))
    assert foreign.status_code == 404
    collaborator_projection = client.get(
        f"/api/v1/journeys/{journey_id}/operator", headers=_auth(other_id)
    )
    assert collaborator_projection.status_code == 200
    assert private_place.name not in json.dumps(collaborator_projection.json(), ensure_ascii=False)

    for action in ("start", "arrive", "complete"):
        advanced = client.post(
            f"/api/v1/journeys/{journey_id}/member-side-quests/{quest_id}/{action}",
            headers=_auth(owner_id),
        )
        assert advanced.status_code == 200, advanced.text
    return_target = client.get(endpoint, headers=_auth(owner_id))
    assert return_target.status_code == 200, return_target.text
    rendezvous = return_target.json()["target"]
    with SessionLocal() as session:
        rendezvous_activity = session.get(Activity, split["rendezvous_activity_id"])
        journey = session.get(Journey, journey_id)
        assert rendezvous_activity is not None and journey is not None
        rendezvous_place = session.get(Place, rendezvous_activity.place_id)
        assert rendezvous_place is not None
        assert str(journey.active_plan_version_id) == split["active_plan_version_id"]
    assert rendezvous["kind"] == "SHARED_RENDEZVOUS"
    assert rendezvous["place_id"] == rendezvous_place.id
    assert rendezvous["latitude"] == rendezvous_place.latitude
    assert rendezvous["longitude"] == rendezvous_place.longitude
    assert _count(MemberSideQuestReturnReport, MemberSideQuestReturnReport.journey_id == journey_id) == 0
    owner_projection = client.get(
        f"/api/v1/journeys/{journey_id}/operator", headers=_auth(owner_id)
    ).json()
    assert owner_projection["member_side_quest"]["return_state"] == "RETURN_UNKNOWN"
    assert owner_projection["member_side_quest"]["return_report"] is None


def test_r68_navigation_rejects_descriptive_and_stale_targets():
    journey_id, owner_id, _other_id = _active_shared_journey()
    split = _start_split(journey_id, owner_id)
    created = client.post(
        f"/api/v1/journeys/{journey_id}/member-side-quests",
        headers=_auth(owner_id),
        json={"destination_text": "the little blue room beside the station"},
    )
    assert created.status_code == 201, created.text
    quest_id = created.json()["member_side_quest"]["id"]
    endpoint = f"/api/v1/journeys/{journey_id}/member-side-quests/{quest_id}/navigation-targets"
    unresolved = client.get(endpoint, headers=_auth(owner_id))
    assert unresolved.status_code == 409

    place = _private_place(journey_id, split.get("rendezvous_place_id"))
    exact = client.post(
        f"/api/v1/journeys/{journey_id}/member-side-quests",
        headers=_auth(owner_id),
        json={"place_id": place.id},
    )
    assert exact.status_code == 201, exact.text
    stale_endpoint = (
        f"/api/v1/journeys/{journey_id}/member-side-quests/"
        f"{exact.json()['member_side_quest']['id']}/navigation-targets"
    )
    assert client.get(stale_endpoint, headers=_auth(owner_id)).status_code == 200

    ended = client.post(
        f"/api/v1/journeys/{journey_id}/agent/commands",
        headers=_auth(owner_id),
        json={"command": "I'm back with the group.", "requested_autonomy": "PLAN_ONLY"},
    )
    assert ended.status_code == 200, ended.text
    assert client.get(stale_endpoint, headers=_auth(owner_id)).status_code == 409

    replacement_split = _start_split(journey_id, owner_id)
    replacement_place = _private_place(journey_id, replacement_split.get("rendezvous_place_id"))
    replacement = client.post(
        f"/api/v1/journeys/{journey_id}/member-side-quests",
        headers=_auth(owner_id),
        json={"place_id": replacement_place.id},
    )
    assert replacement.status_code == 201, replacement.text
    replacement_endpoint = (
        f"/api/v1/journeys/{journey_id}/member-side-quests/"
        f"{replacement.json()['member_side_quest']['id']}/navigation-targets"
    )
    with SessionLocal() as session:
        journey = session.get(Journey, journey_id)
        member = session.scalar(select(JourneyMember).where(
            JourneyMember.journey_id == journey_id,
            JourneyMember.traveler_id == owner_id,
        ))
        assert journey is not None and member is not None
        active_plan_id = str(journey.active_plan_version_id)
        rendezvous_activity = session.get(Activity, replacement.json()["member_side_quest"]["rendezvous"]["activity_id"])
        assert rendezvous_activity is not None
        original_activity_status = rendezvous_activity.status
        rendezvous_activity.status = "COMPLETED"
        session.commit()
    assert client.get(replacement_endpoint, headers=_auth(owner_id)).status_code == 409
    with SessionLocal() as session:
        journey = session.get(Journey, journey_id)
        rendezvous_activity = session.get(Activity, replacement.json()["member_side_quest"]["rendezvous"]["activity_id"])
        assert journey is not None and rendezvous_activity is not None
        rendezvous_activity.status = original_activity_status
        journey.active_plan_version_id = None
        session.commit()
    assert client.get(replacement_endpoint, headers=_auth(owner_id)).status_code == 409
    with SessionLocal() as session:
        journey = session.get(Journey, journey_id)
        member = session.scalar(select(JourneyMember).where(
            JourneyMember.journey_id == journey_id,
            JourneyMember.traveler_id == owner_id,
        ))
        assert journey is not None and member is not None
        journey.active_plan_version_id = active_plan_id
        member.removed_at = datetime.now(timezone.utc).isoformat()
        session.commit()
    assert client.get(replacement_endpoint, headers=_auth(owner_id)).status_code != 200


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


def _r67_location(
    journey_id: str,
    traveler_id: str,
    *,
    latitude: float = 5.123456,
    longitude: float = 10.654321,
    accuracy: float = 8,
    age_seconds: int = 0,
) -> str:
    captured_at = (
        execution_clock.now().astimezone(timezone.utc) - timedelta(seconds=age_seconds)
    ).isoformat()
    response = client.post(
        f"/api/v1/journeys/{journey_id}/location",
        headers=_auth(traveler_id),
        json={
            "latitude": latitude,
            "longitude": longitude,
            "accuracy_m": accuracy,
            "captured_at": captured_at,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def _r67_candidate(
    *,
    osm_id: str = "123456789",
    name: str = "R67 controlled-provider museum",
    latitude: float = 5.123956,
    longitude: float = 10.654321,
):
    from app.integrations.discovery.real_city import DiscoveryCandidate

    return DiscoveryCandidate(
        provider_key="overpass",
        external_id=f"overpass:node/{osm_id}",
        name=name,
        category="museum",
        latitude=latitude,
        longitude=longitude,
        tags=("museum", "real_city"),
        opening_hours={"status": "UNKNOWN"},
        metadata={"osm_id": f"node/{osm_id}", "tags": {"name": name, "tourism": "museum"}},
        distance_m=None,
    )


def _install_r67_provider(monkeypatch, *, candidates=None, attempts=None, error=None):
    import app.execution.live_moment_scout as live_module

    calls = []

    class ControlledOverpassProvider:
        def search_with_evidence(self, query, **kwargs):
            calls.append({"query": query, **kwargs})
            if error is not None:
                raise error
            return list(candidates or []), list(attempts or [])

        def close(self):
            return None

    monkeypatch.setattr(live_module, "OverpassPOIProvider", ControlledOverpassProvider)
    object.__setattr__(settings, "real_city_enabled", True)
    object.__setattr__(settings, "real_city_mode", "live")
    return calls


def _r67_live_request(
    journey_id: str,
    traveler_id: str,
    observation_id: str,
    *,
    consent: bool | None = True,
):
    payload = {
        "location_observation_id": observation_id,
        "interest": "CULTURE",
        "budget_minutes": 30,
        "radius_m": 1200,
    }
    if consent is not None:
        payload["consent_external_location"] = consent
    return client.post(
        f"/api/v1/journeys/{journey_id}/moment-scout/live",
        headers=_auth(traveler_id),
        json=payload,
    )


def test_r67_live_search_requires_consent_and_rejects_unusable_location_without_provider_call(monkeypatch):
    journey_id, owner_id, other_id = _active_shared_journey()
    observation_id = _r67_location(journey_id, owner_id)
    calls = _install_r67_provider(
        monkeypatch,
        candidates=[_r67_candidate()],
        attempts=[{
            "endpoint": "https://overpass.example/api/interpreter",
            "answered": True,
            "http_status": 200,
        }],
    )

    missing_consent = _r67_live_request(journey_id, owner_id, observation_id, consent=None)
    declined = _r67_live_request(journey_id, owner_id, observation_id, consent=False)
    assert missing_consent.status_code == 422
    assert declined.status_code == 422
    assert calls == []

    object.__setattr__(settings, "real_city_enabled", False)
    disabled = _r67_live_request(journey_id, owner_id, observation_id)
    assert disabled.status_code == 200, disabled.text
    assert disabled.json()["scout_state"] == "PROVIDER_DISABLED"
    assert calls == []
    object.__setattr__(settings, "real_city_enabled", True)

    foreign_observation_id = _r67_location(journey_id, other_id)
    foreign = _r67_live_request(journey_id, owner_id, foreign_observation_id)
    stale_observation_id = _r67_location(journey_id, owner_id, age_seconds=900)
    stale = _r67_live_request(journey_id, owner_id, stale_observation_id)
    imprecise_observation_id = _r67_location(
        journey_id, owner_id, accuracy=10_000
    )
    imprecise = _r67_live_request(journey_id, owner_id, imprecise_observation_id)
    assert foreign.status_code == stale.status_code == imprecise.status_code == 200
    assert all(
        response.json()["scout_state"] == "LOCATION_UNAVAILABLE"
        for response in (foreign, stale, imprecise)
    )
    assert calls == []


def test_r67_live_zero_and_provider_failure_are_distinct_and_unnamed_osm_is_not_actionable(monkeypatch):
    journey_id, owner_id, _other_id = _active_shared_journey()
    observation_id = _r67_location(journey_id, owner_id)
    failed_calls = _install_r67_provider(
        monkeypatch,
        error=httpx.ReadTimeout("request data must not be echoed"),
    )
    failed = _r67_live_request(journey_id, owner_id, observation_id)
    assert failed.status_code == 200, failed.text
    assert failed.json()["scout_state"] == "PROVIDER_UNAVAILABLE"
    assert "request data must not be echoed" not in failed.text
    assert len(failed_calls) == 1

    answered_attempt = [{
        "endpoint": "https://overpass.example/api/interpreter?token=secret",
        "answered": True,
        "http_status": 200,
        "elapsed_ms": 14,
        "elements": 1,
    }]
    zero_calls = _install_r67_provider(
        monkeypatch, candidates=[], attempts=answered_attempt
    )
    zero = _r67_live_request(journey_id, owner_id, observation_id)
    assert zero.json()["scout_state"] == "LIVE_ZERO_RESULTS"
    assert zero.json()["candidates"] == []
    assert "token=secret" not in zero.text
    assert len(zero_calls) == 1

    unnamed_calls = _install_r67_provider(
        monkeypatch,
        candidates=[_r67_candidate(name="OSM museum")],
        attempts=answered_attempt,
    )
    unnamed = _r67_live_request(journey_id, owner_id, observation_id)
    assert unnamed.json()["scout_state"] == "LIVE_ZERO_RESULTS"
    assert unnamed.json()["empty_reason"] == "NO_ACTIONABLE_POIS"
    assert unnamed.json()["candidates"] == []
    assert len(unnamed_calls) == 1



def test_r67_live_scout_excludes_shared_plan_stops_and_rendezvous(monkeypatch):
    journey_id, owner_id, _other_id = _active_shared_journey()
    observation_id = _r67_location(journey_id, owner_id)
    shared_external_id = "overpass:node/88990011"
    with SessionLocal() as session:
        journey = session.get(Journey, journey_id)
        assert journey is not None
        activity = session.scalar(
            select(Activity).where(
                Activity.plan_version_id == str(journey.active_plan_version_id),
                Activity.place_id.is_not(None),
            ).order_by(Activity.sequence_no)
        )
        assert activity is not None
        shared_place = session.get(Place, activity.place_id)
        assert shared_place is not None
        shared_place.provider_key = "overpass"
        shared_place.external_id = shared_external_id
        shared_place.name = "R67 shared itinerary museum"
        shared_place.category = "museum"
        shared_place.latitude = 5.123956
        shared_place.longitude = 10.654321
        session.commit()

    candidates = [
        _r67_candidate(
            osm_id="88990011",
            name="R67 shared itinerary museum",
            latitude=5.123956,
            longitude=10.654321,
        ),
        _r67_candidate(
            osm_id="88990012",
            name="R67 genuinely new museum",
            latitude=5.124456,
            longitude=10.654321,
        ),
    ]
    _install_r67_provider(
        monkeypatch,
        candidates=candidates,
        attempts=[{"endpoint": "https://overpass.example/api/interpreter", "answered": True, "http_status": 200}],
    )
    response = _r67_live_request(journey_id, owner_id, observation_id)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["scout_state"] == "LIVE_RESULTS"
    assert [item["name"] for item in body["candidates"]] == ["R67 genuinely new museum"]


def test_r67_live_scout_cannot_select_after_shared_rendezvous_has_passed(monkeypatch):
    journey_id, owner_id, _other_id = _active_shared_journey()
    observation_id = _r67_location(journey_id, owner_id)
    candidate = _r67_candidate(osm_id="88990013", name="R67 late-night museum")
    _install_r67_provider(
        monkeypatch,
        candidates=[candidate],
        attempts=[{"endpoint": "https://overpass.example/api/interpreter", "answered": True, "http_status": 200}],
    )
    response = _r67_live_request(journey_id, owner_id, observation_id)
    assert response.status_code == 200, response.text
    receipt_id = response.json()["receipt_id"]
    candidate_id = response.json()["candidates"][0]["candidate_id"]
    with SessionLocal() as session:
        receipt = session.get(MemberLiveMomentScoutReceipt, receipt_id)
        assert receipt is not None
        activity = session.get(Activity, receipt.rendezvous_activity_id)
        assert activity is not None
        activity.start_at = (
            execution_clock.now().astimezone(timezone.utc) - timedelta(minutes=1)
        ).isoformat()
        session.commit()
    selection = client.post(
        f"/api/v1/journeys/{journey_id}/moment-scout/live/select",
        headers=_auth(owner_id),
        json={
            "receipt_id": receipt_id,
            "candidate_id": candidate_id,
            "confirm_return_to_rendezvous": True,
        },
    )
    assert selection.status_code == 409, selection.text
    assert "LIVE_MOMENT_SCOUT_RENDEZVOUS_TIME_PASSED" in selection.text
    assert _count(MemberSideQuest, MemberSideQuest.journey_id == journey_id) == 0
    assert _count(Place, Place.provider_key == "overpass", Place.external_id == candidate.external_id) == 0


def test_r67_live_osm_selection_materializes_only_after_owner_confirmation_and_is_idempotent(monkeypatch):
    journey_id, owner_id, other_id = _active_shared_journey()
    observation_id = _r67_location(journey_id, owner_id)
    candidate = _r67_candidate(
        osm_id="987654321", name="R67 controlled-provider museum"
    )
    attempts = [{
        "endpoint": "https://overpass.example/api/interpreter?lat=private",
        "answered": True,
        "http_status": 200,
        "elapsed_ms": 17,
        "elements": 1,
    }]
    calls = _install_r67_provider(monkeypatch, candidates=[candidate], attempts=attempts)
    with SessionLocal() as session:
        journey = session.get(Journey, journey_id)
        assert journey is not None
        active_plan_id = str(journey.active_plan_version_id)
    place_count_before = _count(
        Place,
        Place.provider_key == "overpass",
        Place.external_id == candidate.external_id,
    )
    plan_count_before = _count(PlanVersion, PlanVersion.journey_id == journey_id)
    intent_count_before = _count(JourneyIntent, JourneyIntent.journey_id == journey_id)
    quest_count_before = _count(MemberSideQuest, MemberSideQuest.journey_id == journey_id)
    event_count_before = _count(Event, Event.journey_id == journey_id)
    public_candidate_count_before = _count(
        RealPlaceCandidate, RealPlaceCandidate.journey_id == journey_id
    )
    provider_call_count_before = _count(ProviderCall)

    discovered = _r67_live_request(journey_id, owner_id, observation_id)
    assert discovered.status_code == 200, discovered.text
    result = discovered.json()
    assert result["scout_state"] == "LIVE_RESULTS"
    assert result["provider_provenance"] == "LIVE_OPENSTREETMAP_OVERPASS"
    assert result["attribution"] == "© OpenStreetMap contributors"
    assert len(result["candidates"]) == 1
    assert result["candidates"][0]["name"] == candidate.name
    assert result["candidates"][0]["opening_state"] == "UNKNOWN"
    assert result["candidates"][0]["fit_authority"] == "UNVERIFIED"
    assert "5.123456" not in discovered.text and "10.654321" not in discovered.text
    assert "lat=private" not in discovered.text
    assert calls == [{
        "query": "museum",
        "latitude": 5.123,
        "longitude": 10.654,
        "radius_m": 1200,
        "limit": 12,
    }]
    assert _count(
        Place,
        Place.provider_key == "overpass",
        Place.external_id == candidate.external_id,
    ) == place_count_before
    assert _count(PlanVersion, PlanVersion.journey_id == journey_id) == plan_count_before
    assert _count(JourneyIntent, JourneyIntent.journey_id == journey_id) == intent_count_before
    assert _count(MemberSideQuest, MemberSideQuest.journey_id == journey_id) == quest_count_before
    assert _count(
        RealPlaceCandidate, RealPlaceCandidate.journey_id == journey_id
    ) == public_candidate_count_before
    assert _count(ProviderCall) == provider_call_count_before
    assert _count(Event, Event.journey_id == journey_id) == event_count_before

    receipt_id = result["receipt_id"]
    candidate_id = result["candidates"][0]["candidate_id"]
    foreign_select = client.post(
        f"/api/v1/journeys/{journey_id}/moment-scout/live/select",
        headers=_auth(other_id),
        json={
            "receipt_id": receipt_id,
            "candidate_id": candidate_id,
            "confirm_return_to_rendezvous": True,
        },
    )
    assert foreign_select.status_code == 404

    collaborator_projection = client.get(
        f"/api/v1/journeys/{journey_id}/operator", headers=_auth(other_id)
    )
    assert collaborator_projection.status_code == 200
    assert candidate.name not in collaborator_projection.text
    assert candidate.external_id not in collaborator_projection.text
    assert receipt_id not in collaborator_projection.text

    selected = client.post(
        f"/api/v1/journeys/{journey_id}/moment-scout/live/select",
        headers=_auth(owner_id),
        json={
            "receipt_id": receipt_id,
            "candidate_id": candidate_id,
            "confirm_return_to_rendezvous": True,
        },
    )
    assert selected.status_code == 201, selected.text
    assert selected.json()["member_side_quest"]["state"] == "READY"
    assert selected.json()["member_side_quest"]["destination"]["title"] == candidate.name
    collaborator_after = client.get(
        f"/api/v1/journeys/{journey_id}/operator", headers=_auth(other_id)
    )
    assert candidate.name not in collaborator_after.text
    assert candidate.external_id not in collaborator_after.text

    with SessionLocal() as session:
        receipt = session.get(MemberLiveMomentScoutReceipt, receipt_id)
        assert receipt is not None
        assert receipt.status == "SELECTED"
        assert receipt.side_quest_id == selected.json()["member_side_quest"]["id"]
        assert "5.123456" not in receipt.provider_attempts_json
        assert "10.654321" not in receipt.provider_attempts_json
        current_journey = session.get(Journey, journey_id)
        assert current_journey is not None
        assert str(current_journey.active_plan_version_id) == active_plan_id
    assert _count(
        Place,
        Place.provider_key == "overpass",
        Place.external_id == candidate.external_id,
    ) == 1
    assert _count(PlanVersion, PlanVersion.journey_id == journey_id) == plan_count_before
    assert _count(JourneyIntent, JourneyIntent.journey_id == journey_id) == intent_count_before + 1
    assert _count(MemberSideQuest, MemberSideQuest.journey_id == journey_id) == quest_count_before + 1
    assert _count(
        RealPlaceCandidate, RealPlaceCandidate.journey_id == journey_id
    ) == public_candidate_count_before
    assert _count(ProviderCall) == provider_call_count_before
    assert _count(Event, Event.journey_id == journey_id) == event_count_before

    repeated = client.post(
        f"/api/v1/journeys/{journey_id}/moment-scout/live/select",
        headers=_auth(owner_id),
        json={
            "receipt_id": receipt_id,
            "candidate_id": candidate_id,
            "confirm_return_to_rendezvous": True,
        },
    )
    assert repeated.status_code == 201, repeated.text
    assert repeated.json()["member_side_quest"]["id"] == selected.json()["member_side_quest"]["id"]
    assert _count(
        Place,
        Place.provider_key == "overpass",
        Place.external_id == candidate.external_id,
    ) == 1
    assert _count(JourneyIntent, JourneyIntent.journey_id == journey_id) == intent_count_before + 1
    assert _count(MemberSideQuest, MemberSideQuest.journey_id == journey_id) == quest_count_before + 1


def test_r69_meetup_handshake_requires_peer_and_ends_only_the_owners_split():
    journey_id, owner_id, peer_id = _active_shared_journey()
    split = _start_split(journey_id, owner_id)
    private_place = _private_place(journey_id, split.get("rendezvous_place_id"))
    created = client.post(
        f"/api/v1/journeys/{journey_id}/member-side-quests",
        headers=_auth(owner_id),
        json={"place_id": private_place.id},
    )
    assert created.status_code == 201, created.text
    quest_id = created.json()["member_side_quest"]["id"]
    for action in ("start", "arrive", "complete"):
        response = client.post(
            f"/api/v1/journeys/{journey_id}/member-side-quests/{quest_id}/{action}",
            headers=_auth(owner_id),
        )
        assert response.status_code == 200, response.text

    plan_before = client.get(f"/api/v1/journeys/{journey_id}/experience").json()["active_plan"]["id"]
    report_path = f"/api/v1/journeys/{journey_id}/member-side-quests/{quest_id}/meetup-report"
    reported = client.post(report_path, headers=_auth(owner_id))
    assert reported.status_code == 200, reported.text
    handshake = reported.json()["group_presence"]["meetup_handshake"]["owner"]
    assert handshake["state"] == "PENDING"
    handshake_id = handshake["id"]
    assert handshake["physical_presence_verified"] is False
    repeated = client.post(report_path, headers=_auth(owner_id))
    assert repeated.status_code == 200, repeated.text
    assert repeated.json()["group_presence"]["meetup_handshake"]["owner"]["id"] == handshake_id
    assert _count(
        PlannedSplitMeetupHandshake,
        PlannedSplitMeetupHandshake.journey_id == journey_id,
    ) == 1
    first_handshake_id = handshake_id

    peer_view = client.get(
        f"/api/v1/journeys/{journey_id}/operator", headers=_auth(peer_id)
    )
    assert peer_view.status_code == 200, peer_view.text
    assert private_place.name not in peer_view.text
    incoming = peer_view.json()["group_presence"]["meetup_handshake"]["incoming"]
    assert len(incoming) == 1
    assert incoming[0]["id"] == first_handshake_id

    replacement_place = _private_place(
        journey_id, split.get("rendezvous_place_id"), private_place.id
    )
    replacement = client.post(
        f"/api/v1/journeys/{journey_id}/member-side-quests",
        headers=_auth(owner_id),
        json={"place_id": replacement_place.id},
    )
    assert replacement.status_code == 201, replacement.text
    replacement_quest_id = replacement.json()["member_side_quest"]["id"]
    stale_ack = client.post(
        f"/api/v1/journeys/{journey_id}/meetup-handshakes/{first_handshake_id}/acknowledge",
        headers=_auth(peer_id),
    )
    assert stale_ack.status_code == 409
    assert client.get(f"/api/v1/journeys/{journey_id}/experience").json()["active_plan"]["id"] == plan_before
    for action in ("start", "arrive", "complete"):
        response = client.post(
            f"/api/v1/journeys/{journey_id}/member-side-quests/{replacement_quest_id}/{action}",
            headers=_auth(owner_id),
        )
        assert response.status_code == 200, response.text
    report_path = f"/api/v1/journeys/{journey_id}/member-side-quests/{replacement_quest_id}/meetup-report"
    renewed = client.post(report_path, headers=_auth(owner_id))
    assert renewed.status_code == 200, renewed.text
    declined_handshake_id = renewed.json()["group_presence"]["meetup_handshake"]["owner"]["id"]
    assert declined_handshake_id != first_handshake_id
    peer_view = client.get(
        f"/api/v1/journeys/{journey_id}/operator", headers=_auth(peer_id)
    )
    assert peer_view.status_code == 200, peer_view.text
    incoming = peer_view.json()["group_presence"]["meetup_handshake"]["incoming"]
    assert len(incoming) == 1 and incoming[0]["id"] == declined_handshake_id

    not_yet = client.post(
        f"/api/v1/journeys/{journey_id}/meetup-handshakes/{declined_handshake_id}/not-yet",
        headers=_auth(peer_id),
    )
    assert not_yet.status_code == 200, not_yet.text
    declined_owner_view = client.get(
        f"/api/v1/journeys/{journey_id}/operator", headers=_auth(owner_id)
    )
    assert declined_owner_view.json()["group_presence"]["meetup_handshake"]["owner"]["state"] == "NOT_CONFIRMED"
    assert declined_owner_view.json()["group_presence"]["planned_separation"] is not None
    assert client.get(f"/api/v1/journeys/{journey_id}/experience").json()["active_plan"]["id"] == plan_before

    renewed = client.post(report_path, headers=_auth(owner_id))
    assert renewed.status_code == 200, renewed.text
    handshake_id = renewed.json()["group_presence"]["meetup_handshake"]["owner"]["id"]
    assert handshake_id != declined_handshake_id

    self_ack = client.post(
        f"/api/v1/journeys/{journey_id}/meetup-handshakes/{handshake_id}/acknowledge",
        headers=_auth(owner_id),
    )
    assert self_ack.status_code == 403
    acknowledged = client.post(
        f"/api/v1/journeys/{journey_id}/meetup-handshakes/{handshake_id}/acknowledge",
        headers=_auth(peer_id),
    )
    assert acknowledged.status_code == 200, acknowledged.text
    acked = client.get(
        f"/api/v1/journeys/{journey_id}/operator", headers=_auth(owner_id)
    )
    assert acked.status_code == 200, acked.text
    assert acked.json()["group_presence"]["meetup_handshake"]["owner"]["state"] == "PEER_ACKNOWLEDGED"
    assert acked.json()["group_presence"]["meetup_handshake"]["owner"]["physical_presence_verified"] is False
    assert acked.json()["group_presence"]["planned_separation"] is None
    assert client.get(f"/api/v1/journeys/{journey_id}/experience").json()["active_plan"]["id"] == plan_before
    with SessionLocal() as session:
        intent = session.get(JourneyIntent, split["intent_id"])
        assert intent is not None and intent.status == "CANCELLED"
        row = session.get(PlannedSplitMeetupHandshake, handshake_id)
        assert row is not None
        assert row.state == "PEER_ACKNOWLEDGED"
        assert row.responder_traveler_id == peer_id
        first_row = session.get(PlannedSplitMeetupHandshake, first_handshake_id)
        assert first_row is not None and first_row.state == "INVALIDATED"
        declined_row = session.get(PlannedSplitMeetupHandshake, declined_handshake_id)
        assert declined_row is not None and declined_row.state == "NOT_CONFIRMED"

    duplicate_ack = client.post(
        f"/api/v1/journeys/{journey_id}/meetup-handshakes/{handshake_id}/acknowledge",
        headers=_auth(peer_id),
    )
    assert duplicate_ack.status_code == 200, duplicate_ack.text
    assert _count(
        AuditLog,
        AuditLog.journey_id == journey_id,
        AuditLog.action == "journey.planned_split_meetup.peer_acknowledged",
    ) == 1


def test_r69_respects_r62_waiting_gate_and_does_not_fabricate_a_peer(monkeypatch):
    from app.execution import planned_split_meetup_handshake as handshake_module

    journey_id, owner_id, peer_id = _active_shared_journey()
    split = _start_split(journey_id, owner_id)
    private_place = _private_place(journey_id, split.get("rendezvous_place_id"))
    created = client.post(
        f"/api/v1/journeys/{journey_id}/member-side-quests",
        headers=_auth(owner_id),
        json={"place_id": private_place.id},
    )
    assert created.status_code == 201, created.text
    quest_id = created.json()["member_side_quest"]["id"]
    for action in ("start", "arrive", "complete"):
        response = client.post(
            f"/api/v1/journeys/{journey_id}/member-side-quests/{quest_id}/{action}",
            headers=_auth(owner_id),
        )
        assert response.status_code == 200, response.text

    monkeypatch.setattr(
        handshake_module,
        "active_group_recovery_spend",
        lambda *_args, **_kwargs: (object(), {}, {"state": "RECOVERY_APPLIED_REJOIN_PENDING"}),
    )
    monkeypatch.setattr(
        handshake_module,
        "followthrough_projection",
        lambda *_args, **_kwargs: {"state": "REJOIN_IN_PROGRESS"},
    )
    report_path = f"/api/v1/journeys/{journey_id}/member-side-quests/{quest_id}/meetup-report"
    blocked_by_r62 = client.post(report_path, headers=_auth(owner_id))
    assert blocked_by_r62.status_code == 409
    assert "R62_REJOIN_REQUIRED" in blocked_by_r62.text
    assert _count(
        PlannedSplitMeetupHandshake,
        PlannedSplitMeetupHandshake.journey_id == journey_id,
    ) == 0
    monkeypatch.undo()
    with SessionLocal() as session:
        peer = session.scalar(
            select(JourneyMember).where(
                JourneyMember.journey_id == journey_id,
                JourneyMember.traveler_id == peer_id,
            )
        )
        assert peer is not None
        peer.removed_at = execution_clock.now().astimezone(timezone.utc).isoformat()
        session.commit()
    no_peer = client.post(report_path, headers=_auth(owner_id))
    assert no_peer.status_code == 409
    assert "MEETUP_HANDSHAKE_REQUIRES_CURRENT_PEER" in no_peer.text
    assert _count(
        PlannedSplitMeetupHandshake,
        PlannedSplitMeetupHandshake.journey_id == journey_id,
    ) == 0


def test_r69_one_peer_ack_in_three_person_journey_does_not_claim_group_together():
    journey_id, owner_id, other_peer_id = _active_shared_journey()
    third_id = str(uuid4())
    now = datetime.now(timezone.utc).isoformat()
    with SessionLocal() as session:
        journey = session.get(Journey, journey_id)
        assert journey is not None
        session.add(Traveler(
            id=third_id,
            display_name="R69 Third Member",
            email=None,
            locale="en-US",
            timezone="UTC",
            created_at=now,
            updated_at=now,
        ))
        session.flush()
        session.add(JourneyMember(
            id=str(uuid4()),
            journey_id=journey_id,
            traveler_id=third_id,
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
    split = _start_split(journey_id, owner_id)
    private_place = _private_place(journey_id, split.get("rendezvous_place_id"))
    created = client.post(
        f"/api/v1/journeys/{journey_id}/member-side-quests",
        headers=_auth(owner_id),
        json={"place_id": private_place.id},
    )
    assert created.status_code == 201, created.text
    quest_id = created.json()["member_side_quest"]["id"]
    for action in ("start", "arrive", "complete"):
        response = client.post(
            f"/api/v1/journeys/{journey_id}/member-side-quests/{quest_id}/{action}",
            headers=_auth(owner_id),
        )
        assert response.status_code == 200, response.text
    plan_before = client.get(f"/api/v1/journeys/{journey_id}/experience").json()["active_plan"]["id"]
    report = client.post(
        f"/api/v1/journeys/{journey_id}/member-side-quests/{quest_id}/meetup-report",
        headers=_auth(owner_id),
    )
    assert report.status_code == 200, report.text
    handshake_id = report.json()["group_presence"]["meetup_handshake"]["owner"]["id"]
    acknowledged = client.post(
        f"/api/v1/journeys/{journey_id}/meetup-handshakes/{handshake_id}/acknowledge",
        headers=_auth(third_id),
    )
    assert acknowledged.status_code == 200, acknowledged.text

    group_view = client.get(
        f"/api/v1/journeys/{journey_id}/operator", headers=_auth(other_peer_id)
    )
    assert group_view.status_code == 200, group_view.text
    presence = group_view.json()["group_presence"]
    assert presence["planned_separation"] is None
    assert presence["state"] != "TOGETHER"
    resolved = presence["meetup_handshake"]["resolved"]
    assert len(resolved) == 1
    assert resolved[0]["physical_presence_verified"] is False
    assert resolved[0]["planned_split_state"] == "PLANNED_SPLIT_ENDED"
    assert client.get(f"/api/v1/journeys/{journey_id}/experience").json()["active_plan"]["id"] == plan_before


def test_r69_expired_request_cannot_be_acknowledged_and_can_be_resent():
    journey_id, owner_id, peer_id = _active_shared_journey()
    split = _start_split(journey_id, owner_id)
    private_place = _private_place(journey_id, split.get("rendezvous_place_id"))
    created = client.post(
        f"/api/v1/journeys/{journey_id}/member-side-quests",
        headers=_auth(owner_id),
        json={"place_id": private_place.id},
    )
    assert created.status_code == 201, created.text
    quest_id = created.json()["member_side_quest"]["id"]
    for action in ("start", "arrive", "complete"):
        response = client.post(
            f"/api/v1/journeys/{journey_id}/member-side-quests/{quest_id}/{action}",
            headers=_auth(owner_id),
        )
        assert response.status_code == 200, response.text
    report_path = f"/api/v1/journeys/{journey_id}/member-side-quests/{quest_id}/meetup-report"
    first = client.post(report_path, headers=_auth(owner_id))
    assert first.status_code == 200, first.text
    first_id = first.json()["group_presence"]["meetup_handshake"]["owner"]["id"]
    with SessionLocal() as session:
        row = session.get(PlannedSplitMeetupHandshake, first_id)
        assert row is not None
        row.expires_at = (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat()
        session.commit()

    owner_view = client.get(
        f"/api/v1/journeys/{journey_id}/operator", headers=_auth(owner_id)
    )
    assert owner_view.json()["group_presence"]["meetup_handshake"]["owner"]["state"] == "EXPIRED"
    stale_ack = client.post(
        f"/api/v1/journeys/{journey_id}/meetup-handshakes/{first_id}/acknowledge",
        headers=_auth(peer_id),
    )
    assert stale_ack.status_code == 409
    resent = client.post(report_path, headers=_auth(owner_id))
    assert resent.status_code == 200, resent.text
    resent_id = resent.json()["group_presence"]["meetup_handshake"]["owner"]["id"]
    assert resent_id != first_id
    assert resent.json()["group_presence"]["meetup_handshake"]["owner"]["state"] == "PENDING"
    with SessionLocal() as session:
        expired = session.get(PlannedSplitMeetupHandshake, first_id)
        assert expired is not None and expired.state == "EXPIRED"
        pending = session.get(PlannedSplitMeetupHandshake, resent_id)
        assert pending is not None and pending.state == "PENDING"
