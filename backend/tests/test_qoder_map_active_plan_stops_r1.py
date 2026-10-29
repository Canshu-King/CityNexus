"""The map read side must show the stops the traveller already accepted.  Signed API, TEST_FIXTURE facts."""
import json
from datetime import datetime, timezone
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

import app.main as main_module
from app.core.config import settings
from app.db.models import Activity, Journey, Place, PlanVersion
from app.db.session import SessionLocal

AMAP_SOURCE_URL = "https://uri.amap.com/marker?position=116.397463%2C39.909187&name=TEST_FIXTURE"


@pytest.fixture
def _signed_auth():
    previous = settings.traveler_auth_secret
    object.__setattr__(settings, "traveler_auth_secret", uuid4().hex + uuid4().hex)
    try:
        yield
    finally:
        object.__setattr__(settings, "traveler_auth_secret", previous)


def _place(city_code, label, coordinate_system, source_coordinate_system, region_status):
    return Place(
        id=f"real-place-{uuid4().hex[:22]}", provider_key="amap",
        external_id=f"amap:{label}-{uuid4().hex[:8]}", city_code=city_code,
        name=f"TEST_FIXTURE {label}", category="景点", latitude=39.9018, longitude=116.3915,
        opening_hours_json=json.dumps({"status": "VERIFIED_PROVIDER", "source_url": AMAP_SOURCE_URL},
                                      ensure_ascii=False),
        tags_json='["goal_research"]',
        metadata_json=json.dumps({"region_status": region_status, "source_urls": [AMAP_SOURCE_URL],
                                  "cost_evidence": {"status": "UNKNOWN", "currency": "CNY", "source": "amap"}},
                                 ensure_ascii=False),
        updated_at=datetime.now(timezone.utc).isoformat(),
        coordinate_system=coordinate_system, source_coordinate_system=source_coordinate_system,
    )


def _journey_with_active_plan(client, headers, owner_id):
    response = client.post("/api/v1/journeys", headers=headers, json={
        "traveler_id": owner_id, "title": "TEST_FIXTURE accepted plan on the map",
        "city_code": f"TEST-MAP-PLAN-{uuid4().hex[:8]}", "timezone": "Asia/Shanghai",
        "start_at": "2026-12-03T09:00:00+08:00", "end_at": "2026-12-04T18:00:00+08:00",
        "budget": {"amount_minor": 50000, "currency": "CNY"},
    })
    assert response.status_code == 201, response.text
    return response.json()["id"]


def test_accepted_stops_reach_the_map_with_their_own_source(_signed_auth):
    with TestClient(main_module.app) as client:
        owner = client.post("/api/v1/travelers", json={
            "display_name": "TEST_FIXTURE map owner", "timezone": "Asia/Shanghai"}).json()
        headers = {"Authorization": f"Bearer {owner['access_token']}"}
        journey_id = _journey_with_active_plan(client, headers, owner["id"])
        plan_id = str(uuid4())
        now = datetime.now(timezone.utc).isoformat()
        with SessionLocal() as session:
            journey = session.get(Journey, journey_id)
            city_code = journey.city_code
            planned = _place(city_code, " planned stop", "WGS84", "GCJ02", "MATCHED")
            unconverted = _place(city_code, " raw gcj02 stop", "GCJ02", "GCJ02", "MATCHED")
            session.add_all([
                PlanVersion(id=plan_id, journey_id=journey_id, version_no=1, planning_mode="balanced",
                            status="SELECTED", source="MANUAL", total_cost_minor=0, currency="CNY",
                            estimated_duration_min=0, explanation_json='{"source":"TEST_FIXTURE"}', created_at=now),
                planned, unconverted,
            ])
            session.commit()
            session.add_all([
                Activity(id=str(uuid4()), plan_version_id=plan_id, sequence_no=1, activity_type="SIGHTSEE",
                         title=planned.name, place_id=planned.id, start_at="2026-12-03T09:00:00+08:00",
                         end_at="2026-12-03T11:00:00+08:00", travel_from_prev_min=0, estimated_cost_minor=0,
                         currency="CNY", status="PLANNED", locked=False, metadata_json="{}",
                         created_at=now, updated_at=now),
                # An activity without a place row is a schedule line, not a map point.
                Activity(id=str(uuid4()), plan_version_id=plan_id, sequence_no=2, activity_type="MEAL",
                         title="TEST_FIXTURE lunch", place_id=None, start_at="2026-12-03T12:00:00+08:00",
                         end_at="2026-12-03T13:00:00+08:00", travel_from_prev_min=0, estimated_cost_minor=0,
                         currency="CNY", status="PLANNED", locked=False, metadata_json="{}",
                         created_at=now, updated_at=now),
                Activity(id=str(uuid4()), plan_version_id=plan_id, sequence_no=3, activity_type="SIGHTSEE",
                         title=unconverted.name, place_id=unconverted.id, start_at="2026-12-04T09:00:00+08:00",
                         end_at="2026-12-04T11:00:00+08:00", travel_from_prev_min=0, estimated_cost_minor=0,
                         currency="CNY", status="PLANNED", locked=False, metadata_json="{}",
                         created_at=now, updated_at=now),
            ])
            journey.active_plan_version_id = plan_id
            session.commit()

        path = f"/api/v1/journeys/{journey_id}/map-places"
        response = client.get(path, headers=headers)
        assert response.status_code == 200, response.text
        points = response.json()["candidates"]
        assert [point["candidate_id"] for point in points] == [planned.id, unconverted.id]
        assert len({point["candidate_id"] for point in points}) == len(points)
        first = points[0]
        assert first["origin"] == "PLAN_ACTIVITY" and first["place_id"] == planned.id
        assert first["provider"] == "amap" and first["coordinate_system"] == "WGS84"
        assert first["source_coordinate_system"] == "GCJ02"
        assert first["source_url"] == AMAP_SOURCE_URL
        # A stop found by Amap is credited to Amap, never to the OpenStreetMap copyright the
        # bootstrap arm defaults to.
        assert "OpenStreetMap" not in first["source_attribution"]
        assert first["source_attribution"] == "© 高德地图（AMAP）" and first["source_attribution_url"] is None
        assert first["scheduled_start_at"] == "2026-12-03T09:00:00+08:00"
        assert first["observation_expired"] is False
        # The row still stores provider coordinates, so the caller keeps the point out of the basemap.
        assert points[1]["coordinate_system"] == "GCJ02"
        assert "no-store" in response.headers["cache-control"]


def test_a_plan_that_is_not_active_adds_no_map_points(_signed_auth):
    with TestClient(main_module.app) as client:
        owner = client.post("/api/v1/travelers", json={
            "display_name": "TEST_FIXTURE inactive plan owner", "timezone": "Asia/Shanghai"}).json()
        headers = {"Authorization": f"Bearer {owner['access_token']}"}
        journey_id = _journey_with_active_plan(client, headers, owner["id"])
        now = datetime.now(timezone.utc).isoformat()
        with SessionLocal() as session:
            journey = session.get(Journey, journey_id)
            stop = _place(journey.city_code, " dormant stop", "WGS84", "GCJ02", "MATCHED")
            session.add(stop)
            session.commit()
            stop_id = stop.id
        assert client.get(f"/api/v1/journeys/{journey_id}/map-places", headers=headers).json()["candidates"] == []
        with SessionLocal() as session:
            # The same row becomes a map point the moment the traveller's plan is the active one.
            plan = PlanVersion(id=str(uuid4()), journey_id=journey_id, version_no=1, planning_mode="balanced",
                               status="SELECTED", source="MANUAL", total_cost_minor=0, currency="CNY",
                               estimated_duration_min=0, explanation_json='{"source":"TEST_FIXTURE"}', created_at=now)
            session.add(plan)
            session.commit()
            session.add(Activity(id=str(uuid4()), plan_version_id=plan.id, sequence_no=1, activity_type="SIGHTSEE",
                                 title="TEST_FIXTURE dormant stop", place_id=stop_id,
                                 start_at="2026-12-03T09:00:00+08:00", end_at="2026-12-03T11:00:00+08:00",
                                 travel_from_prev_min=0, estimated_cost_minor=0, currency="CNY",
                                 status="PLANNED", locked=False, metadata_json="{}", created_at=now, updated_at=now))
            session.get(Journey, journey_id).active_plan_version_id = plan.id
            session.commit()
        points = client.get(f"/api/v1/journeys/{journey_id}/map-places", headers=headers).json()["candidates"]
        assert [point["candidate_id"] for point in points] == [stop_id]
