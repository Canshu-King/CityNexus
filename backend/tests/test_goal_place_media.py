"""Source-media contract and signed scope. All external answers are TEST_FIXTURE."""
import asyncio
import json
from copy import deepcopy

import httpx
import pytest

from app.agent import goal_media
from app.db.models import JourneyMission
from app.db.session import SessionLocal
from test_bootstrap_place_facts import enabled_settings, signed_place

LEAD = {"id": "photon:W/12345", "name": "TEST_FIXTURE 景点", "provider": "photon",
    "provider_provenance": "LIVE_PROVIDER", "latitude": 31.2, "longitude": 121.4,
    "coordinate_system": "WGS84", "region_status": "MATCHED",
    "source_url": "https://www.openstreetmap.org/way/12345"}


def media_result(place_id=LEAD["id"]):
    return {"candidate_id": place_id, "place_id": place_id, "status": "REAL_POI_PHOTO",
        "identity_status": "BOUND_SOURCE_ENTITY_ID", "media": {
            "place_id": place_id, "image_url": "https://upload.wikimedia.org/test.jpg",
            "thumb_url": "https://upload.wikimedia.org/thumb/test.jpg", "author": "TEST_FIXTURE 作者",
            "license": "CC BY-SA 4.0", "source_url": "https://commons.wikimedia.org/wiki/File:Test.jpg",
            "can_show": True}}


def create_task(client, headers, journey_id, *, consent=True):
    task = client.post(f"/api/v1/journeys/{journey_id}/agent/goal-tasks", headers=headers, json={
        "goal": "TEST_FIXTURE 去看景点", "model_consent": False,
        "online_research_consent": consent, "max_model_turns": 4, "max_tool_calls": 8}).json()
    with SessionLocal() as session:
        row = session.get(JourneyMission, task["task_id"])
        intent = json.loads(row.intent_json)
        intent["goal_task"]["research_places"] = [deepcopy(LEAD)]
        row.intent_json = json.dumps(intent)
        session.commit()
    return task


def test_signed_source_read_reuses_one_receipt_and_rejects_foreign_scope(signed_place, monkeypatch):
    client, owner, outsider, journey_id, *_ = signed_place
    task = create_task(client, owner, journey_id)
    calls = []
    async def collect(lead, region):
        calls.append(lead["id"])
        return media_result()
    monkeypatch.setattr(goal_media, "_collect", collect)
    url = f"/api/v1/journeys/{journey_id}/agent/goal-tasks/{task['task_id']}/place-media"
    params = {"candidate_id": LEAD["id"]}
    assert client.get(url, params=params).status_code == 401
    assert client.get(url, params=params, headers=outsider).status_code == 403
    assert client.get(url, params={"candidate_id": "photon:W/99999"}, headers=owner).status_code == 404
    assert not calls
    result = client.get(url, params=params, headers=owner)
    assert result.status_code == 200, result.text
    assert result.json()["media"]["place_id"] == LEAD["id"]
    assert result.json()["task_id"] == task["task_id"]
    assert "no-store" in result.headers["cache-control"]
    assert client.get(url, params=params, headers=owner).json()["cache_hit"] is True
    assert calls == [LEAD["id"]]
    second = create_task(client, owner, journey_id)
    with SessionLocal() as session:
        row = session.get(JourneyMission, second["task_id"])
        intent = json.loads(row.intent_json); intent["goal_task"]["research_places"] = []
        row.intent_json = json.dumps(intent); session.commit()
    other_url = url.replace(task["task_id"], second["task_id"])
    assert client.get(other_url, params=params, headers=owner).status_code == 404
    assert len(calls) == 1


def test_without_research_consent_no_media_provider_is_called(signed_place, monkeypatch):
    client, owner, _, journey_id, *_ = signed_place
    task = create_task(client, owner, journey_id, consent=False)
    async def forbidden(*args):
        raise AssertionError("provider must not be called")
    monkeypatch.setattr(goal_media, "_collect", forbidden)
    result = client.get(f"/api/v1/journeys/{journey_id}/agent/goal-tasks/{task['task_id']}/place-media",
        params={"candidate_id": LEAD["id"]}, headers=owner)
    assert result.status_code == 200
    assert result.json()["status"] == "NO_PERMISSION" and result.json()["media"] is None


@pytest.mark.parametrize("change", ["author", "license", "source", "image", "identity"])
def test_non_displayable_media_has_an_ordinary_fallback(change):
    result = media_result()
    if change == "author": result["media"]["author"] = None
    if change == "license": result["media"]["license"] = "All rights reserved"
    if change == "source": result["media"]["source_url"] = "javascript:alert(1)"
    if change == "image": result["media"]["image_url"] = "https://elsewhere.invalid/p.jpg"
    if change == "identity": result["media"]["place_id"] = "another-place"
    safe = goal_media.displayable_media(result, LEAD["id"])
    assert safe["status"] == "NO_PERMISSION" and safe["media"] is None
    assert safe["blocked_itinerary"] is False


@pytest.mark.parametrize("bound", [True, False])
def test_osm_object_binds_wikidata_instead_of_trusting_a_matching_name(monkeypatch, bound):
    seen = []
    def answer(request):
        seen.append(str(request.url))
        if request.url.host == "www.openstreetmap.org":
            return httpx.Response(200, json={"elements": [{"type": "way", "id": 12345,
                "tags": {"wikidata": "Q123"} if bound else {}}]})
        if request.url.params.get("action") == "wbsearchentities":
            return httpx.Response(200, json={"search": [{"id": "Q123", "label": LEAD["name"]}]})
        if request.url.path.endswith("Q123.json"):
            return httpx.Response(200, json={"entities": {"Q123": {
                "labels": {"zh": {"value": LEAD["name"]}},
                "claims": {"P18": [{"mainsnak": {"datavalue": {"value": "Test.jpg"}}}]}}}})
        return httpx.Response(200, json={"query": {"pages": {"1": {"imageinfo": [{
            "url": "https://upload.wikimedia.org/test.jpg",
            "descriptionurl": "https://commons.wikimedia.org/wiki/File:Test.jpg",
            "extmetadata": {"Artist": {"value": "<b>TEST_FIXTURE 作者</b>"},
                "LicenseShortName": {"value": "CC BY-SA 4.0"}}}]}}}})
    real = httpx.AsyncClient
    monkeypatch.setattr(goal_media.httpx, "AsyncClient", lambda **kwargs: real(
        transport=httpx.MockTransport(answer), **kwargs))
    result = asyncio.run(goal_media._collect(LEAD, "TEST_FIXTURE 城市"))
    assert result["candidate_id"] == LEAD["id"]
    if bound:
        assert result["media"]["can_show"] and result["media"]["author"] == "TEST_FIXTURE 作者"
        assert result["source_wikidata_id"] == "Q123"
    else:
        assert result["media"] is None
        assert not any("commons.wikimedia.org" in url for url in seen)


def test_model_can_select_the_media_tool_under_the_existing_task_budget(goal_scope, monkeypatch):
    from app.agent import goal_tasks
    from test_goal_tasks import _create
    session, journey, member = goal_scope
    created = _create(session, journey, member, online_research_consent=True, max_model_turns=3)
    row = session.get(JourneyMission, created["task_id"])
    intent = json.loads(row.intent_json)
    intent["goal_task"]["research_places"] = [deepcopy(LEAD)]
    row.intent_json = json.dumps(intent); session.commit()
    class Agent:
        provider_key = model_key = "TEST_FIXTURE"
        turn = 0
        def _complete(self, _messages):
            self.turn += 1
            if self.turn > 1: return {"content": "TEST_FIXTURE 照片已准备"}
            return {"tool_calls": [{"id": "fixture-photo", "function": {
                "name": "research_place_media", "arguments": json.dumps({"place_id": LEAD["id"]})}}]}
    monkeypatch.setattr(goal_tasks, "_new_goal_agent", lambda *_: Agent())
    monkeypatch.setattr(goal_tasks, "read_source_media", lambda *args: media_result())
    goal_tasks.resume_goal_task(session, journey, member, created["task_id"])
    session.expire_all()
    result = goal_tasks.read_goal_task(session, journey, member, created["task_id"])
    assert result["usage"]["tool_calls"] == 1
    assert result["tool_steps"][0]["tool_name"] == "research_place_media"
    assert result["tool_steps"][0]["result"]["identity_status"] == "BOUND_SOURCE_ENTITY_ID"

from test_goal_tasks import goal_scope
