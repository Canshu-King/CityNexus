from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import func, select

import app.execution.bootstrap_discovery as bootstrap_module
import app.main as main_module
from app.core.config import settings
from app.db.models import (
    AgentRun,
    Booking,
    GuardianRun,
    JourneyMember,
    MemberDraftShortlistItem,
    MobilityFact,
    Place,
    PlanVersion,
    ProviderCall,
    RouteAcquisitionOperation,
)
from app.db.session import SessionLocal


client: TestClient | None = None


def _traveler(label: str) -> dict:
    assert client is not None
    response = client.post(
        "/api/v1/travelers",
        json={"display_name": label, "timezone": "Asia/Shanghai", "locale": "en-GB"},
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_r99_adaptive_short_walk_compares_two_public_legs_without_persistence(monkeypatch):
    global client
    previous_secret = settings.traveler_auth_secret
    previous_valhalla_url = settings.live_valhalla_url
    object.__setattr__(settings, "traveler_auth_secret", "r99-adaptive-walk-secret-012345678901")
    object.__setattr__(settings, "live_valhalla_url", "http://127.0.0.1:8999")
    client = TestClient(main_module.app)
    owner = _traveler(f"R99 adaptive owner {uuid4().hex[:6]}")
    bystander = _traveler(f"R99 adaptive bystander {uuid4().hex[:6]}")
    city_code = f"CN-R99-{uuid4().hex[:8].upper()}"
    journey_response = client.post(
        "/api/v1/journeys",
        json={
            "traveler_id": owner["id"],
            "title": "R99 adaptive short walk draft",
            "city_code": city_code,
            "timezone": "Asia/Shanghai",
            "start_at": "2026-10-17T10:00:00+08:00",
            "end_at": "2026-10-18T18:00:00+08:00",
            "budget": {"amount_minor": 10000, "currency": "CNY"},
        },
    )
    assert journey_response.status_code == 201, journey_response.text
    journey_id = journey_response.json()["id"]
    owner_headers = {"Authorization": f"Bearer {owner['access_token']}"}
    bystander_headers = {"Authorization": f"Bearer {bystander['access_token']}"}
    calls: list[tuple[str, str]] = []

    class FakeValhalla:
        provider_key = "valhalla-http"
        capture_provenance = "TEST_PROVIDER_EMULATOR"
        response_pair_swapped = False
        mutate_during_call = False
        mutation_done = False

        def __init__(self, **kwargs):
            self._lookup = kwargs["place_lookup"]

        def estimate(self, origin: str, destination: str):
            first = self._lookup(origin)
            second = self._lookup(destination)
            if self.mutate_during_call and not type(self).mutation_done:
                with SessionLocal() as raced_session:
                    raced_row = raced_session.get(MemberDraftShortlistItem, current_id)
                    assert raced_row is not None
                    raced_row.updated_at = "2026-10-11T10:00:01+00:00"
                    raced_session.commit()
                type(self).mutation_done = True
            calls.append(
                (
                    f"{first['latitude']},{first['longitude']}",
                    f"{second['latitude']},{second['longitude']}",
                )
            )
            if float(second["longitude"]) == 121.474:
                duration_min, distance_m = 42, 3100
            else:
                duration_min, distance_m = 13, 900
            response_origin, response_destination = origin, destination
            request_locations = (
                (float(first["latitude"]), float(first["longitude"])),
                (float(second["latitude"]), float(second["longitude"])),
            )
            response_locations = request_locations
            if self.response_pair_swapped:
                response_locations = (request_locations[1], request_locations[0])
            return SimpleNamespace(
                duration_min=duration_min,
                distance_m=distance_m,
                origin_place_id=response_origin,
                destination_place_id=response_destination,
                request_locations=request_locations,
                response_locations=response_locations,
            )

    monkeypatch.setattr(bootstrap_module, "ValhallaHTTPMobilityProvider", FakeValhalla)
    try:
        with SessionLocal() as session:
            owner_member = session.scalar(
                select(JourneyMember).where(
                    JourneyMember.journey_id == journey_id,
                    JourneyMember.traveler_id == owner["id"],
                )
            )
            assert owner_member is not None
            stamp = "2026-10-11T10:00:00+00:00"
            session.add(
                JourneyMember(
                    id=str(uuid4()),
                    journey_id=journey_id,
                    traveler_id=bystander["id"],
                    role="COLLABORATOR",
                    invited_by=owner["id"],
                    expires_at=None,
                    joined_at=stamp,
                    removed_at=None,
                    preferences_json="{}",
                    created_at=stamp,
                    updated_at=stamp,
                )
            )
            first_id = str(uuid4())
            current_id = str(uuid4())
            alternative_id = str(uuid4())
            for item_id, external_id, name, latitude, longitude in (
                (first_id, "overpass:node/99001", "R99 Museum", 31.2304, 121.4737),
                (current_id, "overpass:node/99002", "R99 Gallery", 31.2310, 121.4740),
                (alternative_id, "overpass:node/99003", "R99 Park", 31.2315, 121.4745),
            ):
                session.add(
                    MemberDraftShortlistItem(
                        id=item_id,
                        journey_id=journey_id,
                        member_id=owner_member.id,
                        traveler_id=owner["id"],
                        provider_key="overpass",
                        external_id=external_id,
                        name=name,
                        category="public",
                        latitude=latitude,
                        longitude=longitude,
                        coordinate_system="WGS84",
                        source_url=f"https://www.openstreetmap.org/node/{external_id.rsplit('/', 1)[1]}",
                        source_provenance="TEST_PROVIDER",
                        captured_at=stamp,
                        opening_hours_json='{"status":"UNKNOWN"}',
                        cost_evidence_json='{"status":"UNKNOWN"}',
                        source_tags_json="{}",
                        distance_m=None,
                        distance_basis=None,
                        status="SAVED",
                        created_at=stamp,
                        updated_at=stamp,
                    )
                )
            session.commit()

        no_consent = client.post(
            f"/api/v1/journeys/{journey_id}/bootstrap-shortlist/adaptive-short-walk",
            headers=owner_headers,
            json={
                "first_shortlist_id": first_id,
                "current_second_shortlist_id": current_id,
                "alternative_second_shortlist_id": alternative_id,
                "max_walk_minutes": 20,
                "public_route_consent": False,
            },
        )
        assert no_consent.status_code == 422, no_consent.text

        grounded = client.post(
            f"/api/v1/journeys/{journey_id}/bootstrap-shortlist/adaptive-short-walk",
            headers=owner_headers,
            json={
                "first_shortlist_id": first_id,
                "current_second_shortlist_id": current_id,
                "alternative_second_shortlist_id": alternative_id,
                "max_walk_minutes": 20,
                "public_route_consent": True,
            },
        )
        assert grounded.status_code == 200, grounded.text
        body = grounded.json()
        assert body["status"] == "ADAPTIVE_WALK_READY"
        assert body["route_state"] == "COMPARISON_VERIFIED"
        assert body["authorization_basis"] == "THREE_SAVED_PUBLIC_IDENTITIES"
        assert body["navigation_mode"] == "PUBLIC_POI_TO_PUBLIC_POI_WALKING"
        assert body["max_walk_minutes"] == 20
        assert body["current_leg"]["duration_min"] == 42
        assert body["alternative_leg"]["duration_min"] == 13
        assert body["current_leg"]["distance_m"] == 3100
        assert body["alternative_leg"]["distance_m"] == 900
        assert body["current_leg"]["provenance"] == "TEST_PROVIDER_EMULATOR"
        assert body["alternative_leg"]["provenance"] == "TEST_PROVIDER_EMULATOR"
        assert body["recommendation_state"] == "WITHIN_MY_LEG_BUDGET"
        assert body["suggested_second_shortlist_id"] == alternative_id
        assert "13 min" in body["recommendation_reason"]
        assert calls == [
            ("31.2304,121.4737", "31.231,121.474"),
            ("31.2304,121.4737", "31.2315,121.4745"),
        ]
        grounded_calls = list(calls)
        for forbidden in (
            "origin",
            "foreground_gps",
            "current_location",
            "query_center",
            "member_id",
            "traveler_id",
            "journey_id",
            "receipt_id",
            "private_intent",
            "arrival",
        ):
            assert forbidden in body["withheld_fields"]
        for private_token in (journey_id, owner["id"], bystander["id"]):
            assert private_token not in body["navigation_url"]
            assert private_token not in body["alternative_navigation_url"]
        assert body["explore_state"] == "DRAFT_EXPLORE_ONLY"
        assert body["plan_version_id"] is None
        assert body["selected_place_id"] is None

        FakeValhalla.response_pair_swapped = True
        swapped_pair = client.post(
            f"/api/v1/journeys/{journey_id}/bootstrap-shortlist/adaptive-short-walk",
            headers=owner_headers,
            json={
                "first_shortlist_id": first_id,
                "current_second_shortlist_id": current_id,
                "alternative_second_shortlist_id": alternative_id,
                "max_walk_minutes": 20,
                "public_route_consent": True,
            },
        )
        assert swapped_pair.status_code == 200, swapped_pair.text
        swapped_body = swapped_pair.json()
        assert swapped_body["status"] == "ADAPTIVE_WALK_UNVERIFIED"
        assert swapped_body["route_state"] == "ROUTE_UNVERIFIED"
        assert swapped_body["suggested_second_shortlist_id"] is None
        assert swapped_body["current_leg"]["route_state"] == "ROUTE_UNVERIFIED"
        assert swapped_body["alternative_leg"]["route_state"] == "ROUTE_UNVERIFIED"
        FakeValhalla.response_pair_swapped = False

        FakeValhalla.mutate_during_call = True
        FakeValhalla.mutation_done = False
        raced_snapshot = client.post(
            f"/api/v1/journeys/{journey_id}/bootstrap-shortlist/adaptive-short-walk",
            headers=owner_headers,
            json={
                "first_shortlist_id": first_id,
                "current_second_shortlist_id": current_id,
                "alternative_second_shortlist_id": alternative_id,
                "max_walk_minutes": 20,
                "public_route_consent": True,
            },
        )
        assert raced_snapshot.status_code == 409, raced_snapshot.text
        assert "BOOTSTRAP_ADAPTIVE_STALE" in raced_snapshot.text
        calls_after_race = list(calls)
        FakeValhalla.mutate_during_call = False
        with SessionLocal() as session:
            current_row = session.get(MemberDraftShortlistItem, current_id)
            assert current_row is not None
            current_row.updated_at = stamp
            session.commit()

        identity_payload = {
            "first_shortlist_id": first_id,
            "current_second_shortlist_id": current_id,
            "alternative_second_shortlist_id": alternative_id,
            "max_walk_minutes": 20,
            "public_route_consent": True,
        }

        with SessionLocal() as session:
            current_row = session.get(MemberDraftShortlistItem, current_id)
            assert current_row is not None
            current_row.provider_key = "fixture"
            session.commit()
        invalid_provider = client.post(
            f"/api/v1/journeys/{journey_id}/bootstrap-shortlist/adaptive-short-walk",
            headers=owner_headers,
            json=identity_payload,
        )
        assert invalid_provider.status_code == 422, invalid_provider.text
        assert "BOOTSTRAP_IDENTITY_INVALID" in invalid_provider.text
        assert calls == calls_after_race

        with SessionLocal() as session:
            current_row = session.get(MemberDraftShortlistItem, current_id)
            assert current_row is not None
            current_row.provider_key = "overpass"
            current_row.external_id = "fixture:node/99002"
            session.commit()
        invalid_external_id = client.post(
            f"/api/v1/journeys/{journey_id}/bootstrap-shortlist/adaptive-short-walk",
            headers=owner_headers,
            json=identity_payload,
        )
        assert invalid_external_id.status_code == 422, invalid_external_id.text
        assert "BOOTSTRAP_IDENTITY_INVALID" in invalid_external_id.text
        assert calls == calls_after_race

        with SessionLocal() as session:
            current_row = session.get(MemberDraftShortlistItem, current_id)
            assert current_row is not None
            current_row.external_id = "overpass:node/99002"
            current_row.coordinate_system = "EPSG:4326"
            session.commit()
        invalid_coordinate_system = client.post(
            f"/api/v1/journeys/{journey_id}/bootstrap-shortlist/adaptive-short-walk",
            headers=owner_headers,
            json=identity_payload,
        )
        assert invalid_coordinate_system.status_code == 422, invalid_coordinate_system.text
        assert "BOOTSTRAP_COORDINATE_SYSTEM_UNSUPPORTED" in invalid_coordinate_system.text
        assert calls == calls_after_race

        with SessionLocal() as session:
            current_row = session.get(MemberDraftShortlistItem, current_id)
            assert current_row is not None
            current_row.coordinate_system = "WGS84"
            session.commit()

        cross_member = client.post(
            f"/api/v1/journeys/{journey_id}/bootstrap-shortlist/adaptive-short-walk",
            headers=bystander_headers,
            json={
                "first_shortlist_id": first_id,
                "current_second_shortlist_id": current_id,
                "alternative_second_shortlist_id": alternative_id,
                "max_walk_minutes": 20,
                "public_route_consent": True,
            },
        )
        assert cross_member.status_code == 403, cross_member.text

        object.__setattr__(settings, "live_valhalla_url", None)
        unavailable = client.post(
            f"/api/v1/journeys/{journey_id}/bootstrap-shortlist/adaptive-short-walk",
            headers=owner_headers,
            json={
                "first_shortlist_id": first_id,
                "current_second_shortlist_id": current_id,
                "alternative_second_shortlist_id": alternative_id,
                "max_walk_minutes": 20,
                "public_route_consent": True,
            },
        )
        assert unavailable.status_code == 200, unavailable.text
        unavailable_body = unavailable.json()
        assert unavailable_body["status"] == "ADAPTIVE_WALK_UNVERIFIED"
        assert unavailable_body["route_state"] == "ROUTE_UNVERIFIED"
        assert unavailable_body["recommendation_state"] == "ROUTE_UNVERIFIED"
        assert unavailable_body["suggested_second_shortlist_id"] is None
        assert unavailable_body["current_leg"]["duration_min"] is None
        assert unavailable_body["alternative_leg"]["duration_min"] is None
        assert len(calls) == len(calls_after_race)

        with SessionLocal() as session:
            assert session.scalar(select(func.count(Place.id)).where(Place.city_code == city_code)) == 0
            assert session.scalar(select(func.count(PlanVersion.id)).where(PlanVersion.journey_id == journey_id)) == 0
            assert session.scalar(select(func.count(MobilityFact.id)).where(MobilityFact.journey_id == journey_id)) == 0
            assert session.scalar(select(func.count(RouteAcquisitionOperation.id)).where(RouteAcquisitionOperation.journey_id == journey_id)) == 0
            assert session.scalar(
                select(func.count(ProviderCall.id)).where(ProviderCall.request_json.like(f"%{journey_id}%"))
            ) == 0
            assert session.scalar(select(func.count(AgentRun.id)).where(AgentRun.journey_id == journey_id)) == 0
            assert session.scalar(select(func.count(GuardianRun.id)).where(GuardianRun.journey_id == journey_id)) == 0
            assert session.scalar(select(func.count(Booking.id)).where(Booking.journey_id == journey_id)) == 0
    finally:
        object.__setattr__(settings, "traveler_auth_secret", previous_secret)
        object.__setattr__(settings, "live_valhalla_url", previous_valhalla_url)
