"""Structured, owner-bound public region handling for goal research."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import select

from app.agent import goal_artifacts
from app.core.config import settings
from app.db.models import JourneyMember, ProviderCall, Traveler
from app.planning.travel_brief import brief_projection, save_brief
from app.schemas import TravelBriefRequest
from test_goal_tasks import goal_scope


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _provider_fakes(monkeypatch, captured):
    class Photon:
        def __init__(self, **_kwargs):
            pass

        def search(self, query, *, city, limit):
            captured.append(("photon", query, city, limit))
            return []

    class Nominatim:
        def __init__(self, **_kwargs):
            pass

        def search(self, query, *, city, limit):
            captured.append(("nominatim", query, city, limit))
            return []

    monkeypatch.setattr(goal_artifacts, "PhotonCityGeocoder", Photon)
    monkeypatch.setattr(goal_artifacts, "NominatimGeocoder", Nominatim)


def test_structured_region_survives_title_change_for_both_provider_paths(goal_scope, monkeypatch):
    session, journey, owner = goal_scope
    journey.city_code = "CN-RV-ABC123DEF456"
    journey.title = "PRIVATE_CUSTOM_TRIP_TITLE"
    save_brief(session, journey, owner, TravelBriefRequest(public_region_label="建宁县"))
    journey.title = "RENAMED_PRIVATE_TITLE"

    captured = []
    _provider_fakes(monkeypatch, captured)
    previous = (settings.real_city_enabled, settings.real_city_mode)
    object.__setattr__(settings, "real_city_enabled", True)
    object.__setattr__(settings, "real_city_mode", "live")
    try:
        task = {}
        for source in ("photon", "nominatim"):
            result = goal_artifacts.discover_goal_places(
                session, journey, task, query="TEST_FIXTURE museum", source=source)
            assert result["status"] == "NO_RESULTS"
        calls = session.scalars(select(ProviderCall).where(
            ProviderCall.operation == "goal_place_discovery")).all()
        assert {json.loads(call.request_json)["city"] for call in calls} == {"建宁县"}
    finally:
        object.__setattr__(settings, "real_city_enabled", previous[0])
        object.__setattr__(settings, "real_city_mode", previous[1])

    assert captured == [
        ("photon", "TEST_FIXTURE museum", "建宁县", 8),
        ("nominatim", "TEST_FIXTURE museum", "建宁县", 8),
    ]
    assert "CN-RV-ABC123DEF456" not in json.dumps([call.request_json for call in calls])
    assert "RENAMED_PRIVATE_TITLE" not in json.dumps([call.request_json for call in calls])


def test_ordinary_brief_update_preserves_public_region(goal_scope):
    session, journey, owner = goal_scope
    first = save_brief(session, journey, owner, TravelBriefRequest(
        goal="寻找安静的博物馆", public_region_label="建宁县"))
    updated = save_brief(session, journey, owner, TravelBriefRequest(goal="改成看古村"))

    assert updated.id == first.id
    assert json.loads(updated.semantic_envelope_json)["public_region_label"] == "建宁县"


def test_public_region_and_brief_projection_are_owner_scoped(goal_scope):
    session, journey, owner = goal_scope
    journey.city_code = "CN-RV-ABC123DEF456"
    save_brief(session, journey, owner, TravelBriefRequest(public_region_label="OWNER_REGION"))

    other_traveler = Traveler(
        id=str(uuid4()), display_name="TEST_FIXTURE other member", email=None,
        locale="zh-CN", timezone="Asia/Shanghai", created_at=_now(), updated_at=_now())
    other_member = JourneyMember(
        id=str(uuid4()), journey_id=journey.id, traveler_id=other_traveler.id,
        role="MEMBER", invited_by=owner.traveler_id, expires_at=None, joined_at=_now(),
        removed_at=None, preferences_json="{}", created_at=_now(), updated_at=_now())
    session.add_all([other_traveler, other_member])
    session.flush()
    save_brief(session, journey, other_member,
               TravelBriefRequest(public_region_label="OTHER_MEMBER_PRIVATE_REGION"))

    assert goal_artifacts.public_city_label(journey, session) == "OWNER_REGION"
    assert brief_projection(session, journey, other_member)["intent"]["public_region_label"] == "OTHER_MEMBER_PRIVATE_REGION"
    assert brief_projection(session, journey, owner)["intent"]["public_region_label"] == "OWNER_REGION"


def test_legacy_random_region_queries_without_title_or_city_code(goal_scope, monkeypatch):
    session, journey, _owner = goal_scope
    journey.city_code = "CN-RV-LEGACY987"
    journey.title = "PRIVATE_LEGACY_TITLE"

    captured = []
    _provider_fakes(monkeypatch, captured)
    previous = (settings.real_city_enabled, settings.real_city_mode)
    object.__setattr__(settings, "real_city_enabled", True)
    object.__setattr__(settings, "real_city_mode", "live")
    try:
        result = goal_artifacts.discover_goal_places(
            session, journey, {}, query="TEST_FIXTURE park", source="photon")
        calls = session.scalars(select(ProviderCall).where(
            ProviderCall.operation == "goal_place_discovery")).all()
    finally:
        object.__setattr__(settings, "real_city_enabled", previous[0])
        object.__setattr__(settings, "real_city_mode", previous[1])

    request = json.loads(calls[0].request_json)
    assert result["status"] == "NO_RESULTS"
    assert captured == [("photon", "TEST_FIXTURE park", "", 8)]
    assert request["city"] is None and request["public_city_label"] == ""
    assert "CN-RV-LEGACY987" not in calls[0].request_json
    assert "PRIVATE_LEGACY_TITLE" not in calls[0].request_json
