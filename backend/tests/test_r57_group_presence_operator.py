from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select

import app.main as main_module
import app.traveler_principal as principal_module
from app.core.config import settings
from app.db.models import Activity, Event, Journey, JourneyMember, LocationObservation, Traveler
from app.db.session import SessionLocal
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
    assert presence["state"] == "GROUP_PRESENCE"
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
    members = response.json()["group_presence"]["members"]
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
    now = datetime.now(timezone.utc)
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
    assert projection.json()["group_presence"]["members"][0]["location_state"] == "STALE"

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
