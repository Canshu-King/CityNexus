"""Geocoder protocol fixtures, never external provider observations."""
import json

import httpx
import pytest
from fastapi import HTTPException

from app.agent import goal_artifacts, goal_tasks
from app.integrations.discovery.real_city import PhotonCityGeocoder, NominatimGeocoder
from app.planning.travel_brief import save_brief
from app.schemas import TravelBriefRequest
from test_goal_tasks import goal_scope, _create


def feature(identifier, name, *, osm_key=None, osm_value=None, location_type="house", **address):
    return {"geometry": {"coordinates": [119.0, 26.9]}, "properties": {
        "osm_type": "N", "osm_id": identifier, "name": name,
        "type": location_type, "osm_key": osm_key, "osm_value": osm_value, **address}}


@pytest.mark.parametrize("properties,category,location_type", [
    ({"osm_key": "tourism", "osm_value": "museum", "location_type": "house"}, "museum", "house"),
    ({"osm_key": "place", "osm_value": "village", "location_type": "district"}, "village", "district"),
    ({}, "unknown", "house"),
])
def test_photon_category_is_osm_value_not_address_granularity(properties, category, location_type):
    payload = {"features": [feature(123, "TEST_FIXTURE place", county="屏南县", city="宁德市",
        state="福建省", district="双溪镇", private_extra="omit", **properties)]}
    with httpx.Client(transport=httpx.MockTransport(lambda _: httpx.Response(200, json=payload))) as client:
        point = PhotonCityGeocoder(client=client).search("TEST_FIXTURE", city="屏南县", limit=8)[0]
    assert point.category == category and point.location_type == location_type
    assert {key: point.metadata[key] for key in ("county", "city", "state", "district")} == {
        "county": "屏南县", "city": "宁德市", "state": "福建省", "district": "双溪镇"}
    assert "private_extra" not in point.metadata


def test_nominatim_preserves_explicit_public_address_and_category():
    rows = [{"lat": "26.9", "lon": "119", "osm_type": "node", "osm_id": 123,
        "display_name": "TEST_FIXTURE village, county", "class": "place", "type": "village",
        "addresstype": "village", "address": {"county": "屏南县", "private_extra": "omit"}}]
    with httpx.Client(transport=httpx.MockTransport(lambda _: httpx.Response(200, json=rows))) as client:
        point = NominatimGeocoder(client=client).search("TEST_FIXTURE", city="屏南县", limit=8)[0]
    assert point.category == "village" and point.location_type == "village"
    assert point.metadata == {"county": "屏南县", "osm_key": "place", "osm_value": "village"}


@pytest.mark.parametrize("region,address,status", [
    ("屏南县", {"county": "屏南县"}, "MATCHED"),
    ("屏南县", {"county": "平南县"}, "CONFLICT"),
    ("连城县", {"city": "上海市", "district": "浦东新区"}, "CONFLICT"),
    ("连城县", {"county": "连城县", "city": "龙岩市"}, "MATCHED"),
    ("连城县", {"county": "连城县", "district": "浦东新区"}, "CONFLICT"),
    ("屏南县", {"city": "宁德市"}, "UNKNOWN"),
    ("宁德市", {"county": "屏南县"}, "UNKNOWN"),
    ("屏南县", {"county": "Pingnan County"}, "UNKNOWN"),
    ("屏南县", {}, "UNKNOWN"),
])
def test_region_comparison_does_not_guess_names_or_mixed_levels(region, address, status):
    assert goal_artifacts._public_region_status(region, address) == status


def test_agent_draft_keeps_conflicting_region_leads_out_of_itinerary(goal_scope):
    session, journey, _member = goal_scope
    draft = goal_artifacts.empty_draft(journey)
    date = draft["days"][0]["date"]
    task = {"research_places": [{"id": "photon:way/123", "region_status": "CONFLICT"}]}
    with pytest.raises(HTTPException) as error:
        goal_artifacts.normalize_draft(journey, task, [{"date": date, "slots": [
            {"title": "TEST_FIXTURE off-region place", "time_of_day": "afternoon", "place_id": "photon:way/123"},
        ]}], author="AGENT")
    assert error.value.status_code == 422
    assert error.value.detail == "DRAFT_PLACE_REGION_CONFLICT"


def test_area_result_survives_signed_task_restore_and_is_editable_without_becoming_poi(goal_scope, monkeypatch):
    session, journey, member = goal_scope
    save_brief(session, journey, member, TravelBriefRequest(public_region_label="屏南县"))
    created = _create(session, journey, member, online_research_consent=True)
    mission = session.get(goal_tasks.JourneyMission, created["task_id"])
    intent = json.loads(mission.intent_json)
    task = intent["goal_task"]
    payload = {"features": [
        feature(123, "TEST_FIXTURE museum", osm_key="tourism", osm_value="museum", county="屏南县"),
        feature(456, "TEST_FIXTURE village", osm_key="place", osm_value="village", location_type="district", county="屏南县"),
        feature(789, "TEST_FIXTURE street", osm_key="highway", osm_value="residential", location_type="street", county="平南县"),
    ]}
    real_client = httpx.Client
    requests = []
    def respond(request):
        requests.append(request)
        return httpx.Response(200, json=payload)
    monkeypatch.setattr(goal_artifacts.httpx, "Client", lambda **kw: real_client(transport=httpx.MockTransport(respond), **kw))
    monkeypatch.setattr(goal_artifacts, "settings", type("Settings", (), {
        "real_city_enabled": True, "real_city_mode": "live", "real_city_timeout_seconds": 5})())
    result = goal_artifacts.discover_goal_places(session, journey, task, query="TEST_FIXTURE county")
    assert len(requests) == 1 and result["status"] == "RESULTS"
    assert [lead["category"] for lead in result["places"]] == ["museum"]
    assert [lead["category"] for lead in result["areas"]] == ["village", "residential"]
    assert result["areas"][1]["region_status"] == "CONFLICT"
    cached = goal_artifacts.cached_goal_place_sources(task, "photon:N/456")
    assert cached["status"] == "CACHED_ONLY" and cached["public_address"] == {"county": "屏南县"}
    projected = goal_tasks._safe_tool_result("research_place_sources", cached)
    assert projected["cached_facts"]["osm_value"] == "village"
    assert projected["public_address"] == {"county": "屏南县"}
    assert goal_tasks._step_result_summary("discover_places", result)["area_count"] == 2
    task["draft_artifact"] = goal_artifacts.normalize_draft(journey, task, [{"date": "2026-11-01", "slots": [
        {"title": "TEST_FIXTURE village walk", "time_of_day": "afternoon", "place_id": "photon:N/456"}]}], author="USER")
    mission.intent_json = json.dumps(intent)
    session.commit()
    restored = goal_tasks.read_goal_task(session, journey, member, created["task_id"])
    assert len(restored["research_places"]) == 1 and len(restored["research_areas"]) == 2
    assert restored["draft_artifact"]["days"][0]["slots"][0]["place_id"] == "photon:N/456"
    with pytest.raises(HTTPException) as error:
        goal_artifacts.discover_nearby_goal_places(session, journey, task,
            center_place_id="photon:N/789", query="museum")
    assert error.value.status_code == 403 and len(requests) == 1
    assert journey.status == "DRAFT" and journey.active_plan_version_id is None
