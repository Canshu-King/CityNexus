from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select

import app.main as main_module
import app.traveler_principal as principal_module
from app.core.config import settings
from app.db.models import (
    Activity,
    AuditLog,
    AutopilotEnrollment,
    Commitment,
    Event,
    Journey,
    JourneyMember,
    LocationObservation,
    RouteAcquisitionOperation,
    Traveler,
)
from app.db.session import SessionLocal
from app.execution.clock import execution_clock
from app.traveler_principal import issue_traveler_token
from demo_stage import demo_reset_headers

client = TestClient(main_module.app)


def _auth(traveler_id: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {issue_traveler_token(traveler_id)}"}


def _shared_active_journey() -> tuple[str, str, str]:
    reset = client.post("/api/v1/demo/reset", headers=demo_reset_headers())
    assert reset.status_code == 200, reset.text
    journey_id = reset.json()["journey_id"]
    plans = client.post(f"/api/v1/journeys/{journey_id}/plans/generate", json={"candidate_count": 1})
    assert plans.status_code == 201, plans.text
    plan_id = plans.json()[0]["id"]
    assert client.post(f"/api/v1/journeys/{journey_id}/plans/{plan_id}/select").status_code == 200
    assert client.post(f"/api/v1/journeys/{journey_id}/start").status_code == 200
    second_id = str(uuid4())
    now = datetime.now(timezone.utc).isoformat()
    with SessionLocal() as session:
        journey = session.get(Journey, journey_id)
        assert journey is not None
        owner_id = journey.traveler_id
        session.add(Traveler(
            id=second_id, display_name="R57同行者", email=None, locale="zh-CN",
            timezone="UTC", created_at=now, updated_at=now,
        ))
        session.flush()
        session.add(JourneyMember(
            id=str(uuid4()), journey_id=journey_id, traveler_id=second_id,
            role="COLLABORATOR", invited_by=owner_id, expires_at=None,
            joined_at=now, removed_at=None, preferences_json="{}",
            created_at=now, updated_at=now,
        ))
        session.commit()
    return journey_id, owner_id, second_id


def test_r57_location_rows_bind_to_signed_members_and_operator_hides_coordinates(monkeypatch):
    isolated = replace(settings, traveler_auth_secret="r57-test-secret-0123456789abcdef")
    monkeypatch.setattr(main_module, "settings", isolated)
    monkeypatch.setattr(principal_module, "settings", isolated)
    journey_id, owner_id, other_id = _shared_active_journey()
    now = datetime.now(timezone.utc).isoformat()
    owner_sample = client.post(
        f"/api/v1/journeys/{journey_id}/location", headers=_auth(owner_id),
        json={"latitude": 35.0, "longitude": 135.0, "accuracy_m": 8, "captured_at": now},
    )
    other_sample = client.post(
        f"/api/v1/journeys/{journey_id}/location", headers=_auth(other_id),
        json={"latitude": 35.1, "longitude": 135.1, "accuracy_m": 10, "captured_at": now},
    )
    assert owner_sample.status_code == 201, owner_sample.text
    assert other_sample.status_code == 201, other_sample.text
    with SessionLocal() as session:
        owner_row = session.get(LocationObservation, owner_sample.json()["id"])
        other_row = session.get(LocationObservation, other_sample.json()["id"])
        assert owner_row and other_row
        assert owner_row.traveler_id == owner_id and owner_row.journey_member_id
        assert other_row.traveler_id == other_id and other_row.journey_member_id

    projection = client.get(
        f"/api/v1/journeys/{journey_id}/operator", headers=_auth(owner_id)
    )
    assert projection.status_code == 200, projection.text
    presence = projection.json()["group_presence"]
    assert presence["state"] == "GROUP_SPLIT_ADVISORY"
    assert presence["rendezvous_state"] == "RENDEZVOUS_TARGET_READY"
    assert len(presence["members"]) == 2
    assert {member["location_state"] for member in presence["members"]} == {"RECENT"}
    assert any(member["group_state"] == "SPLIT_FROM_GROUP" for member in presence["members"])
    assert all("latitude" not in member and "longitude" not in member for member in presence["members"])
    serialized = str(presence)
    assert owner_sample.json()["id"] not in serialized
    assert other_sample.json()["id"] not in serialized
    assert "35.0" not in serialized and "135.0" not in serialized
    assert presence["rendezvous"] is not None


def test_r57_location_identity_cannot_be_claimed_in_body_and_route_is_member_bound(monkeypatch):
    isolated = replace(settings, traveler_auth_secret="r57-test-secret-0123456789abcdef")
    monkeypatch.setattr(main_module, "settings", isolated)
    monkeypatch.setattr(principal_module, "settings", isolated)
    journey_id, owner_id, other_id = _shared_active_journey()
    now = datetime.now(timezone.utc).isoformat()
    owner_sample = client.post(
        f"/api/v1/journeys/{journey_id}/location", headers=_auth(owner_id),
        json={"latitude": 35.0, "longitude": 135.0, "accuracy_m": 8, "captured_at": now},
    )
    other_sample = client.post(
        f"/api/v1/journeys/{journey_id}/location", headers=_auth(other_id),
        json={"latitude": 35.1, "longitude": 135.1, "accuracy_m": 10, "captured_at": now},
    )
    assert owner_sample.status_code == 201, owner_sample.text
    assert other_sample.status_code == 201, other_sample.text
    with SessionLocal() as session:
        event_ids_before_route = set(session.scalars(
            select(Event.id).where(Event.journey_id == journey_id)
        ).all())
    spoof = client.post(
        f"/api/v1/journeys/{journey_id}/location", headers=_auth(owner_id),
        json={"latitude": 35.0, "longitude": 135.0, "accuracy_m": 8,
              "captured_at": now, "member_id": "somebody-else", "traveler_id": other_id},
    )
    assert spoof.status_code == 422

    captured = []

    class _Result:
        status = "UNAVAILABLE"

    def fake_submit(_session, _journey, route_request):
        captured.append(route_request)
        return _Result(), False

    monkeypatch.setattr(main_module, "submit_route_operation", fake_submit)
    monkeypatch.setattr(main_module, "route_operation_payload", lambda *_args, **_kwargs: {
        "status": "UNAVAILABLE", "outcome": "ROUTE_UNAVAILABLE", "result": {},
    })
    payload = {"location_observation_id": owner_sample.json()["id"], "requested_mode": "WALK"}
    owner_route = client.post(
        f"/api/v1/journeys/{journey_id}/group-presence/route",
        headers=_auth(owner_id), json=payload,
    )
    assert owner_route.status_code == 200, owner_route.text
    assert captured and captured[0].origin_key == f"location-observation:{owner_sample.json()['id']}"
    assert captured[0].origin_evidence["traveler_id"] == owner_id
    assert captured[0].origin_evidence["journey_member_id"]
    assert owner_route.json()["guardian_triggered"] is False
    assert owner_route.json()["plan_unchanged"] is True

    other_route = client.post(
        f"/api/v1/journeys/{journey_id}/group-presence/route",
        headers=_auth(other_id),
        json={"location_observation_id": other_sample.json()["id"], "requested_mode": "WALK"},
    )
    assert other_route.status_code == 200, other_route.text
    assert captured[1].origin_key == f"location-observation:{other_sample.json()['id']}"
    assert captured[1].origin_key != captured[0].origin_key

    cross_member = client.post(
        f"/api/v1/journeys/{journey_id}/group-presence/route",
        headers=_auth(other_id), json=payload,
    )
    assert cross_member.status_code == 403
    assert len(captured) == 2
    with SessionLocal() as session:
        event_ids_after_route = set(session.scalars(
            select(Event.id).where(Event.journey_id == journey_id)
        ).all())
    assert event_ids_after_route == event_ids_before_route


def test_r57_operator_does_not_infer_presence_for_unidentified_viewer(monkeypatch):
    isolated = replace(settings, traveler_auth_secret="r57-test-secret-0123456789abcdef")
    monkeypatch.setattr(main_module, "settings", isolated)
    monkeypatch.setattr(principal_module, "settings", isolated)
    journey_id, _owner_id, _other_id = _shared_active_journey()
    from app.operator_projection import operator_projection

    with SessionLocal() as session:
        journey = session.get(Journey, journey_id)
        assert journey is not None
        presence = operator_projection(session, journey)["group_presence"]
    assert presence["state"] == "MEMBER_IDENTITY_UNAVAILABLE"
    assert presence["members"] == []


def test_r57_missing_member_location_is_unknown_not_a_split(monkeypatch):
    isolated = replace(settings, traveler_auth_secret="r57-test-secret-0123456789abcdef")
    monkeypatch.setattr(main_module, "settings", isolated)
    monkeypatch.setattr(principal_module, "settings", isolated)
    journey_id, owner_id, _other_id = _shared_active_journey()
    response = client.get(
        f"/api/v1/journeys/{journey_id}/operator", headers=_auth(owner_id)
    )
    assert response.status_code == 200, response.text
    presence = response.json()["group_presence"]
    assert presence["state"] == "MEMBER_LOCATION_MISSING"
    members = presence["members"]
    assert len(members) == 2
    assert all(member["location_state"] == "MISSING" for member in members)
    assert all(member["group_state"] == "UNKNOWN" for member in members)
    assert response.json()["group_presence"]["can_guide"] is True


def test_r57_expired_members_and_historical_unbound_locations_are_not_projected(monkeypatch):
    isolated = replace(settings, traveler_auth_secret="r57-test-secret-0123456789abcdef")
    monkeypatch.setattr(main_module, "settings", isolated)
    monkeypatch.setattr(principal_module, "settings", isolated)
    journey_id, owner_id, _other_id = _shared_active_journey()
    expired_id = str(uuid4())
    now = execution_clock.now().astimezone(timezone.utc)
    with SessionLocal() as session:
        journey = session.get(Journey, journey_id)
        assert journey
        second_member = session.scalar(select(JourneyMember).where(
            JourneyMember.journey_id == journey_id,
            JourneyMember.traveler_id == _other_id,
        ))
        assert second_member
        second_member.removed_at = now.isoformat()
        session.add(Traveler(
            id=expired_id, display_name="Expired R57 member", email=None, locale="en-US",
            timezone="UTC", created_at=now.isoformat(), updated_at=now.isoformat(),
        ))
        session.flush()
        session.add(JourneyMember(
            id=str(uuid4()), journey_id=journey_id, traveler_id=expired_id,
            role="COLLABORATOR", invited_by=owner_id,
            expires_at=(now - timedelta(minutes=1)).isoformat(),
            joined_at=(now - timedelta(hours=1)).isoformat(),
            removed_at=None, preferences_json="{}", created_at=now.isoformat(), updated_at=now.isoformat(),
        ))
        session.add(LocationObservation(
            id=str(uuid4()), journey_id=journey_id, traveler_id=None, journey_member_id=None,
            latitude=35.555, longitude=135.555, accuracy_m=5,
            captured_at=now.isoformat(), source="FOREGROUND_WEB",
        ))
        session.commit()
    now_text = datetime.now(timezone.utc).isoformat()
    for inactive_traveler_id in (_other_id, expired_id):
        rejected = client.post(
            f"/api/v1/journeys/{journey_id}/location",
            headers=_auth(inactive_traveler_id),
            json={"latitude": 35.0, "longitude": 135.0, "accuracy_m": 8, "captured_at": now_text},
        )
        assert rejected.status_code == 403, rejected.text
    response = client.get(
        f"/api/v1/journeys/{journey_id}/operator", headers=_auth(owner_id)
    )
    assert response.status_code == 200, response.text
    presence = response.json()["group_presence"]
    assert len(presence["members"]) == 1
    assert presence["state"] == "SINGLE_TRAVELLER"
    assert all(member["display_name"] != "Expired R57 member" for member in presence["members"])
    assert "35.555" not in str(presence) and "135.555" not in str(presence)


def test_r57_stale_member_location_is_visible_as_stale_but_cannot_start_route(monkeypatch):
    isolated = replace(settings, traveler_auth_secret="r57-test-secret-0123456789abcdef")
    monkeypatch.setattr(main_module, "settings", isolated)
    monkeypatch.setattr(principal_module, "settings", isolated)
    journey_id, owner_id, _other_id = _shared_active_journey()
    old = (datetime.now(timezone.utc) - timedelta(minutes=12)).isoformat()
    saved = client.post(
        f"/api/v1/journeys/{journey_id}/location", headers=_auth(owner_id),
        json={"latitude": 35.0, "longitude": 135.0, "accuracy_m": 8, "captured_at": old},
    )
    assert saved.status_code == 201, saved.text
    projection = client.get(
        f"/api/v1/journeys/{journey_id}/operator", headers=_auth(owner_id)
    )
    assert projection.status_code == 200, projection.text
    presence = projection.json()["group_presence"]
    # Keep the stale viewer evidence visible, but report the whole-group gap:
    # another in-force member has no location at all.
    assert presence["state"] == "MEMBER_LOCATION_MISSING"
    assert presence["members"][0]["location_state"] == "STALE"

    called = False
    def should_not_route(*_args, **_kwargs):
        nonlocal called
        called = True
        raise AssertionError("stale member location must not reach route acquisition")
    monkeypatch.setattr(main_module, "submit_route_operation", should_not_route)
    response = client.post(
        f"/api/v1/journeys/{journey_id}/group-presence/route",
        headers=_auth(owner_id),
        json={"location_observation_id": saved.json()["id"], "requested_mode": "WALK"},
    )
    assert response.status_code == 409
    assert "GROUP_RENDEZVOUS_LOCATION_STALE" in response.text
    assert called is False


def test_r57_close_member_locations_are_together_and_other_journey_observation_is_rejected(monkeypatch):
    isolated = replace(settings, traveler_auth_secret="r57-test-secret-0123456789abcdef")
    monkeypatch.setattr(main_module, "settings", isolated)
    monkeypatch.setattr(principal_module, "settings", isolated)
    journey_id, owner_id, other_id = _shared_active_journey()
    now = datetime.now(timezone.utc).isoformat()
    owner_sample = client.post(
        f"/api/v1/journeys/{journey_id}/location", headers=_auth(owner_id),
        json={"latitude": 35.0, "longitude": 135.0, "accuracy_m": 8, "captured_at": now},
    )
    other_sample = client.post(
        f"/api/v1/journeys/{journey_id}/location", headers=_auth(other_id),
        json={"latitude": 35.0001, "longitude": 135.0001, "accuracy_m": 10, "captured_at": now},
    )
    assert owner_sample.status_code == other_sample.status_code == 201
    presence = client.get(
        f"/api/v1/journeys/{journey_id}/operator", headers=_auth(owner_id)
    ).json()["group_presence"]
    assert presence["state"] == "TOGETHER"
    assert {member["group_state"] for member in presence["members"]} == {"WITH_GROUP"}

    foreign = client.post("/api/v1/journeys", json={
        "traveler_id": owner_id,
        "title": "Other journey for R57 isolation",
        "city_code": "NARA",
        "timezone": "Asia/Tokyo",
        "start_at": "2026-10-07T09:00:00+09:00",
        "end_at": "2026-10-07T18:00:00+09:00",
        "budget": {"amount_minor": 5000, "currency": "JPY"},
        "party_size": 1,
    })
    assert foreign.status_code == 201, foreign.text
    foreign_journey_id = foreign.json()["id"]
    foreign_observation_id = str(uuid4())
    with SessionLocal() as session:
        session.add(LocationObservation(
            id=foreign_observation_id, journey_id=foreign_journey_id,
            traveler_id=owner_id, journey_member_id=None, latitude=35.0, longitude=135.0,
            accuracy_m=8, captured_at=now, source="FOREGROUND_WEB",
        ))
        session.commit()
    foreign_route = client.post(
        f"/api/v1/journeys/{journey_id}/group-presence/route",
        headers=_auth(owner_id),
        json={"location_observation_id": foreign_observation_id, "requested_mode": "WALK"},
    )
    assert foreign_route.status_code == 404
    assert "LOCATION_OBSERVATION_NOT_FOUND" in foreign_route.text


def test_r57_without_an_exact_active_plan_place_has_no_invented_rendezvous(monkeypatch):
    isolated = replace(settings, traveler_auth_secret="r57-test-secret-0123456789abcdef")
    monkeypatch.setattr(main_module, "settings", isolated)
    monkeypatch.setattr(principal_module, "settings", isolated)
    journey_id, owner_id, _other_id = _shared_active_journey()
    now = datetime.now(timezone.utc).isoformat()
    sample = client.post(
        f"/api/v1/journeys/{journey_id}/location", headers=_auth(owner_id),
        json={"latitude": 35.0, "longitude": 135.0, "accuracy_m": 8, "captured_at": now},
    )
    assert sample.status_code == 201, sample.text
    with SessionLocal() as session:
        journey = session.get(Journey, journey_id)
        assert journey and journey.active_plan_version_id
        activities = session.scalars(select(Activity).where(
            Activity.plan_version_id == journey.active_plan_version_id
        )).all()
        assert activities
        for activity in activities:
            activity.place_id = None
        session.commit()

    projection = client.get(
        f"/api/v1/journeys/{journey_id}/operator", headers=_auth(owner_id)
    ).json()["group_presence"]
    assert projection["rendezvous"] is None
    assert projection["rendezvous_state"] == "RENDEZVOUS_TARGET_UNAVAILABLE"
    assert projection["can_guide"] is False

    called = False
    def should_not_route(*_args, **_kwargs):
        nonlocal called
        called = True
        raise AssertionError("no grounded active-plan place means no invented rendezvous route")
    monkeypatch.setattr(main_module, "submit_route_operation", should_not_route)
    response = client.post(
        f"/api/v1/journeys/{journey_id}/group-presence/route",
        headers=_auth(owner_id),
        json={"location_observation_id": sample.json()["id"], "requested_mode": "WALK"},
    )
    assert response.status_code == 409
    assert "GROUP_RENDEZVOUS_TARGET_UNAVAILABLE" in response.text
    assert called is False


def _r57_risky_shared_target(journey_id: str) -> tuple[str, str, str]:
    from app.execution.group_presence import rendezvous_target

    now = execution_clock.now().astimezone(timezone.utc)
    with SessionLocal() as session:
        journey = session.get(Journey, journey_id)
        assert journey is not None
        pair = rendezvous_target(session, journey)
        assert pair is not None
        target, place = pair
        scheduled = (now + timedelta(minutes=5)).isoformat()
        commitment = session.scalar(
            select(Commitment).where(
                Commitment.journey_id == journey_id,
                Commitment.activity_id == target.id,
                Commitment.status == "ACTIVE",
                Commitment.level.in_(("C3_Guaranteed", "C4_Anchored")),
            )
        )
        if commitment is None:
            commitment = Commitment(
                id=str(uuid4()),
                journey_id=journey_id,
                activity_id=target.id,
                kind="APPOINTMENT",
                level="C4_Anchored",
                status="ACTIVE",
                monetary_value_minor=0,
                monetary_value_status="KNOWN",
                currency="JPY",
                external_ref="R57-SHARED-RENDEZVOUS",
                policy_json="{}",
                created_at=now.isoformat(),
                updated_at=now.isoformat(),
            )
            session.add(commitment)
        commitment.policy_json = __import__("json").dumps(
            {
                "scheduled_start_at": scheduled,
                "safety_buffer_min": 5,
                "source": "R57_TEST_PROTECTED_SHARED_STOP",
            },
            sort_keys=True,
        )
        enrollment = session.get(AutopilotEnrollment, journey_id)
        if enrollment is None:
            session.add(
                AutopilotEnrollment(
                    journey_id=journey_id,
                    enabled=True,
                    interval_seconds=60.0,
                    provider_mesh_json="{}",
                    last_pulse_at=None,
                    last_error=None,
                    created_at=now.isoformat(),
                    updated_at=now.isoformat(),
                )
            )
        else:
            enrollment.enabled = True
        session.commit()
        return target.id, place.id, commitment.id


def test_r57_advisory_member_risk_never_creates_guardian_event(monkeypatch):
    isolated = replace(settings, traveler_auth_secret="r57-test-secret-0123456789abcdef")
    monkeypatch.setattr(main_module, "settings", isolated)
    monkeypatch.setattr(principal_module, "settings", isolated)
    journey_id, owner_id, _other_id = _shared_active_journey()
    _r57_risky_shared_target(journey_id)
    now = datetime.now(timezone.utc).isoformat()
    sample = client.post(
        f"/api/v1/journeys/{journey_id}/location",
        headers=_auth(owner_id),
        json={"latitude": 35.0, "longitude": 135.0, "accuracy_m": 8, "captured_at": now},
    )
    assert sample.status_code == 201, sample.text

    class _Route:
        id = "r57-advisory-route"
        status = "COMPLETED"

    monkeypatch.setattr(main_module, "submit_route_operation", lambda *_args, **_kwargs: (_Route(), False))
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
    guardian_calls: list[str] = []
    monkeypatch.setattr(
        main_module,
        "scan_guardian",
        lambda *_args, **_kwargs: guardian_calls.append("called") or {"status": "COMPLETED"},
    )

    response = client.post(
        f"/api/v1/journeys/{journey_id}/group-presence/route",
        headers=_auth(owner_id),
        json={"location_observation_id": sample.json()["id"], "requested_mode": "WALK"},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["authority"] == "ADVISORY_FOREGROUND_LOCATION"
    assert body["shared_commitment_risk"]["state"] == "COMMITMENT_AT_RISK"
    assert body["member_risk_event_id"] is None
    assert body["guardian_triggered"] is False
    assert guardian_calls == []
    with SessionLocal() as session:
        events = session.scalars(
            select(Event).where(
                Event.journey_id == journey_id,
                Event.provider_key == "journey-group-presence",
            )
        ).all()
        assert events == []


def test_r57_trusted_member_risk_is_one_event_and_one_guardian_handoff(monkeypatch):
    isolated = replace(settings, traveler_auth_secret="r57-test-secret-0123456789abcdef")
    monkeypatch.setattr(main_module, "settings", isolated)
    monkeypatch.setattr(principal_module, "settings", isolated)
    journey_id, owner_id, _other_id = _shared_active_journey()
    target_activity_id, _target_place_id, commitment_id = _r57_risky_shared_target(journey_id)

    with SessionLocal() as session:
        owner_member = session.scalar(
            select(JourneyMember).where(
                JourneyMember.journey_id == journey_id,
                JourneyMember.traveler_id == owner_id,
            )
        )
        assert owner_member is not None
        owner_member_id = owner_member.id

    def add_trusted_observation() -> str:
        observation_id = str(uuid4())
        with SessionLocal() as session:
            session.add(
                LocationObservation(
                    id=observation_id,
                    journey_id=journey_id,
                    traveler_id=owner_id,
                    journey_member_id=owner_member_id,
                    latitude=35.0,
                    longitude=135.0,
                    accuracy_m=8,
                    captured_at=execution_clock.now().astimezone(timezone.utc).isoformat(),
                    source="DEVICE_ATTESTED",
                )
            )
            session.commit()
        return observation_id

    route_counter = {"value": 0}

    class _Route:
        status = "COMPLETED"

        def __init__(self):
            route_counter["value"] += 1
            self.id = f"r57-trusted-route-{route_counter['value']}"

    monkeypatch.setattr(main_module, "submit_route_operation", lambda *_args, **_kwargs: (_Route(), False))
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
    guardian_calls: list[str] = []
    monkeypatch.setattr(
        main_module,
        "scan_guardian",
        lambda *_args, **_kwargs: guardian_calls.append("called")
        or {"status": "COMPLETED", "action_status": "NO_ACTION"},
    )

    first_observation = add_trusted_observation()
    first = client.post(
        f"/api/v1/journeys/{journey_id}/group-presence/route",
        headers=_auth(owner_id),
        json={"location_observation_id": first_observation, "requested_mode": "WALK"},
    )
    assert first.status_code == 200, first.text
    first_body = first.json()
    assert first_body["authority"] == "TRUSTED_MEMBER_LOCATION_ROUTE"
    assert first_body["shared_commitment_risk"]["state"] == "COMMITMENT_AT_RISK"
    assert first_body["shared_commitment_risk"]["next_commitment"]["commitment_id"] == commitment_id
    assert first_body["member_risk_event_id"]
    assert first_body["guardian_triggered"] is True
    assert first_body["guardian_deduplicated"] is False
    assert guardian_calls == ["called"]
    event_id = first_body["member_risk_event_id"]

    second_observation = add_trusted_observation()
    second = client.post(
        f"/api/v1/journeys/{journey_id}/group-presence/route",
        headers=_auth(owner_id),
        json={"location_observation_id": second_observation, "requested_mode": "WALK"},
    )
    assert second.status_code == 200, second.text
    second_body = second.json()
    assert second_body["member_risk_event_id"] == event_id
    assert second_body["guardian_triggered"] is False
    assert second_body["guardian_deduplicated"] is True
    assert guardian_calls == ["called"]

    with SessionLocal() as session:
        events = session.scalars(
            select(Event).where(
                Event.journey_id == journey_id,
                Event.provider_key == "journey-group-presence",
                Event.event_type == "TRAFFIC_DELAY",
            )
        ).all()
        assert len(events) == 1
        payload = __import__("json").loads(events[0].payload_json)
        assert payload["journey_member_id"] == owner_member_id
        assert payload["rendezvous_activity_id"] == target_activity_id
        assert payload["affected_commitment_id"] == commitment_id
        assert events[0].affected_activity_id is None

        handoffs = session.scalars(
            select(AuditLog).where(
                AuditLog.action == "journey.group_presence.member_risk.guardian_handoff",
                AuditLog.entity_id == event_id,
            )
        ).all()
        assert len(handoffs) == 1

        first_payload = __import__("json").loads(events[0].payload_json)
        semantic_key = first_payload["incident_semantic_key"]
        assert first_payload["incident_episode"] == 1

        events[0].status = "RESOLVED"
        events[0].resolved_at = execution_clock.now().astimezone(timezone.utc).isoformat()
        session.commit()

    third_observation = add_trusted_observation()
    third = client.post(
        f"/api/v1/journeys/{journey_id}/group-presence/route",
        headers=_auth(owner_id),
        json={"location_observation_id": third_observation, "requested_mode": "WALK"},
    )
    assert third.status_code == 200, third.text
    third_body = third.json()
    assert third_body["member_risk_event_id"] != event_id
    assert third_body["guardian_triggered"] is True
    assert third_body["guardian_deduplicated"] is False
    assert guardian_calls == ["called", "called"]

    with SessionLocal() as session:
        episodes = session.scalars(
            select(Event).where(
                Event.journey_id == journey_id,
                Event.provider_key == "journey-group-presence",
                Event.event_type == "TRAFFIC_DELAY",
            )
        ).all()
        assert len(episodes) == 2
        parsed = [__import__("json").loads(row.payload_json) for row in episodes]
        assert {item["incident_episode"] for item in parsed} == {1, 2}
        assert {item["incident_semantic_key"] for item in parsed} == {semantic_key}
        assert len({item["incident_fingerprint"] for item in parsed}) == 2


def _r58_store_route_receipt(
    journey_id: str,
    traveler_id: str,
    *,
    source: str = "FOREGROUND_WEB",
    provenance: str = "CAPTURED_REPLAY",
    provider: str = "valhalla-http",
    duration_min: int = 30,
) -> tuple[str, str]:
    from app.execution.group_presence import rendezvous_target

    now = datetime.now(timezone.utc).isoformat()
    with SessionLocal() as session:
        journey = session.get(Journey, journey_id)
        assert journey is not None
        member = session.scalar(select(JourneyMember).where(
            JourneyMember.journey_id == journey_id,
            JourneyMember.traveler_id == traveler_id,
            JourneyMember.removed_at.is_(None),
        ))
        assert member is not None
        target_pair = rendezvous_target(session, journey)
        assert target_pair is not None
        target, place = target_pair
        observation_id = str(uuid4())
        session.add(LocationObservation(
            id=observation_id,
            journey_id=journey_id,
            traveler_id=traveler_id,
            journey_member_id=member.id,
            latitude=35.001,
            longitude=135.002,
            accuracy_m=8,
            captured_at=now,
            source=source,
        ))
        session.flush()
        session.add(RouteAcquisitionOperation(
            id=str(uuid4()),
            journey_id=journey_id,
            fingerprint=str(uuid4()),
            origin_key=f"location-observation:{observation_id}",
            target_key=str(place.id),
            target_activity_id=target.id,
            requested_mode="WALK",
            provider_policy_version="R58_TEST_PROVIDER_POLICY",
            route_truth_policy_version="R58_TEST_TRUTH_POLICY",
            status="COMPLETED",
            outcome="ROUTE_READY",
            request_json="{}",
            result_json=__import__("json").dumps({
                "duration_min": duration_min,
                "provider": provider,
                "provenance": provenance,
            }),
            error_json="{}",
            queued_at=now,
            started_at=now,
            finished_at=now,
            updated_at=now,
        ))
        session.commit()
        return observation_id, member.id


def test_r58_trusted_location_row_projects_trusted_authority_not_browser_advisory(monkeypatch):
    isolated = replace(settings, traveler_auth_secret="r58-test-secret-0123456789abcdef")
    monkeypatch.setattr(main_module, "settings", isolated)
    monkeypatch.setattr(principal_module, "settings", isolated)
    journey_id, owner_id, _other_id = _shared_active_journey()
    with SessionLocal() as session:
        journey = session.get(Journey, journey_id)
        assert journey is not None
        member = session.scalar(select(JourneyMember).where(
            JourneyMember.journey_id == journey_id,
            JourneyMember.traveler_id == owner_id,
        ))
        assert member is not None
        now = datetime.now(timezone.utc).isoformat()
        session.add(LocationObservation(
            id=str(uuid4()), journey_id=journey_id, traveler_id=owner_id,
            journey_member_id=member.id, latitude=35.0, longitude=135.0,
            accuracy_m=8, captured_at=now, source="LOCATION_ATTESTED",
        ))
        session.commit()
    projection = client.get(
        f"/api/v1/journeys/{journey_id}/operator", headers=_auth(owner_id)
    )
    assert projection.status_code == 200, projection.text
    owner = next(item for item in projection.json()["group_presence"]["members"] if item["is_viewer"])
    assert owner["authority"] == "TRUSTED_MEMBER_LOCATION"


def test_r58_replay_eta_is_visible_with_exact_non_live_provenance(monkeypatch):
    isolated = replace(settings, traveler_auth_secret="r58-test-secret-0123456789abcdef")
    monkeypatch.setattr(main_module, "settings", isolated)
    monkeypatch.setattr(principal_module, "settings", isolated)
    journey_id, owner_id, _other_id = _shared_active_journey()
    _r57_risky_shared_target(journey_id)
    _r58_store_route_receipt(
        journey_id, owner_id, provenance="CAPTURED_REPLAY", provider="valhalla-http", duration_min=30
    )
    projection = client.get(
        f"/api/v1/journeys/{journey_id}/operator", headers=_auth(owner_id)
    )
    assert projection.status_code == 200, projection.text
    body = projection.json()
    owner = next(item for item in body["group_presence"]["members"] if item["is_viewer"])
    assert owner["route_eta_minutes"] == 30
    assert owner["route_eta_provenance"] == "CAPTURED_REPLAY"
    assert owner["route_eta_state"] == "CAPTURED_REPLAY"
    assert body["group_recovery"]["state"] == "ADVISORY_MEMBER_LATE"
    assert body["group_recovery"]["affected_member"]["route_provenance"] == "CAPTURED_REPLAY"


def test_r58_mock_route_cannot_become_member_eta_or_recovery_truth(monkeypatch):
    isolated = replace(settings, traveler_auth_secret="r58-test-secret-0123456789abcdef")
    monkeypatch.setattr(main_module, "settings", isolated)
    monkeypatch.setattr(principal_module, "settings", isolated)
    journey_id, owner_id, _other_id = _shared_active_journey()
    _r57_risky_shared_target(journey_id)
    _r58_store_route_receipt(
        journey_id, owner_id, provenance="LIVE_PROVIDER_CAPTURE", provider="mock-mobility", duration_min=30
    )
    projection = client.get(
        f"/api/v1/journeys/{journey_id}/operator", headers=_auth(owner_id)
    )
    assert projection.status_code == 200, projection.text
    body = projection.json()
    owner = next(item for item in body["group_presence"]["members"] if item["is_viewer"])
    assert owner["route_eta_minutes"] is None
    assert owner["route_eta_state"] == "NON_PRODUCT_PROVIDER"
    assert body["group_recovery"]["state"] == "INSUFFICIENT_MEMBER_TRUTH"


def test_r58_advisory_adjust_is_one_plan_only_hermes_run_and_not_a_gps_disruption(monkeypatch):
    isolated = replace(settings, traveler_auth_secret="r58-test-secret-0123456789abcdef")
    monkeypatch.setattr(main_module, "settings", isolated)
    monkeypatch.setattr(principal_module, "settings", isolated)
    journey_id, owner_id, _other_id = _shared_active_journey()
    _r57_risky_shared_target(journey_id)
    _r58_store_route_receipt(journey_id, owner_id, duration_min=30)
    from app.agent import mission as mission_module
    monkeypatch.setattr(
        mission_module, "_model_draft",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("R58 must not spend a second model call compiling the mission")),
    )
    monkeypatch.setattr(main_module, "native_hermes_status", lambda: {"ready": True})
    created_runs: list[dict[str, object]] = []

    class _Run:
        run_id = "r58-hermes-run"
        status = "queued"

    class _Native:
        def create_run(self, **kwargs):
            created_runs.append(kwargs)
            return _Run()

        def close(self):
            return None

    monkeypatch.setattr(main_module, "HermesNativeClient", _Native)
    before = client.get(
        f"/api/v1/journeys/{journey_id}/operator", headers=_auth(owner_id)
    ).json()
    assert before["group_recovery"]["state"] == "ADVISORY_MEMBER_LATE"
    with SessionLocal() as session:
        prior_group_events = session.scalars(select(Event).where(
            Event.journey_id == journey_id,
            Event.provider_key == "journey-group-presence",
        )).all()
        assert prior_group_events == []
        journey = session.get(Journey, journey_id)
        active_before = journey.active_plan_version_id

    first = client.post(
        f"/api/v1/journeys/{journey_id}/group-recovery/adjust",
        headers=_auth(owner_id), json={},
    )
    assert first.status_code == 200, first.text
    first_body = first.json()
    assert first_body["status"] == "RECOVERY_OPTIONS_READY"
    assert first_body["run"]["runtime_identity"] == "HERMES_NATIVE_MCP"
    assert first_body["run"]["mission_plan"]["autonomy"] == "PLAN_ONLY"
    assert len(created_runs) == 1
    assert "ADVISORY_FOREGROUND_WEB" in created_runs[0]["instructions"]
    assert "coordinates" in created_runs[0]["instructions"]
    assert "35.001" not in created_runs[0]["instructions"]
    assert "135.002" not in created_runs[0]["instructions"]

    replay = client.post(
        f"/api/v1/journeys/{journey_id}/group-recovery/adjust",
        headers=_auth(owner_id), json={},
    )
    assert replay.status_code == 200, replay.text
    assert replay.json()["reused"] is True
    assert replay.json()["mission"]["id"] == first_body["mission"]["id"]
    assert len(created_runs) == 1

    with SessionLocal() as session:
        journey = session.get(Journey, journey_id)
        assert journey.active_plan_version_id == active_before
        explicit_requests = session.scalars(select(Event).where(
            Event.journey_id == journey_id,
            Event.provider_key == "journey-group-recovery-request",
        )).all()
        assert len(explicit_requests) == 1
        request_context = __import__("json").loads(explicit_requests[0].payload_json)
        assert request_context["physical_presence_claim"] is False
        assert request_context["location_authority"] == "ADVISORY_FOREGROUND_WEB"


def test_r58_unavailable_native_agent_is_durable_blocked_without_plan_mutation(monkeypatch):
    isolated = replace(settings, traveler_auth_secret="r58-test-secret-0123456789abcdef")
    monkeypatch.setattr(main_module, "settings", isolated)
    monkeypatch.setattr(principal_module, "settings", isolated)
    journey_id, owner_id, _other_id = _shared_active_journey()
    _r57_risky_shared_target(journey_id)
    _r58_store_route_receipt(journey_id, owner_id, duration_min=30)
    monkeypatch.setattr(main_module, "native_hermes_status", lambda: {"ready": False})

    class _MustNotStart:
        def __init__(self):
            raise AssertionError("an unready native Agent must not be called")

    monkeypatch.setattr(main_module, "HermesNativeClient", _MustNotStart)
    with SessionLocal() as session:
        journey = session.get(Journey, journey_id)
        assert journey is not None
        active_before = journey.active_plan_version_id

    response = client.post(
        f"/api/v1/journeys/{journey_id}/group-recovery/adjust",
        headers=_auth(owner_id),
        json={},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "RECOVERY_EXTERNAL_AGENT_BLOCKED"
    assert body["mission"]["status"] == "FAILED_EXTERNAL"
    assert body["mission"]["failure_reason"] == "NATIVE_HERMES_UNAVAILABLE_FOR_GROUP_RECOVERY"
    assert body["run"] is None

    with SessionLocal() as session:
        journey = session.get(Journey, journey_id)
        assert journey is not None
        assert journey.active_plan_version_id == active_before
        request_events = session.scalars(select(Event).where(
            Event.journey_id == journey_id,
            Event.provider_key == "journey-group-recovery-request",
        )).all()
        assert len(request_events) == 1
        payload = __import__("json").loads(request_events[0].payload_json)
        assert payload["user_requested"] is True
        assert payload["physical_presence_claim"] is False
