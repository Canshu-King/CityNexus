"""Area adapter contract fixtures. No model, real provider or user DB calls."""
import json
from dataclasses import replace

import httpx
import pytest
from fastapi import HTTPException
from sqlalchemy import select

from app.agent import goal_artifacts, goal_tasks
from app.core.config import settings
from app.db.models import ProviderCall, PlanVersion
from test_goal_tasks import goal_scope, _create, _now


def _task():
    return {"research_places": [{"id": "photon:W/123", "name": "TEST_FIXTURE center",
        "latitude": 31.23, "longitude": 121.47, "source_url": "https://www.openstreetmap.org/way/123",
        "provider_provenance": "LIVE_PROVIDER"}]}


@pytest.mark.parametrize("response_status,elements,expected", [
    (200, [], "NO_RESULTS"),
    (200, [{"type": "node", "id": 456, "lat": 31.231, "lon": 121.471,
            "tags": {"name": "TEST_FIXTURE Museum", "tourism": "museum"}}], "RESULTS"),
    (502, [], "PROVIDER_UNAVAILABLE"),
])
def test_area_query_is_once_bounded_and_persists_source(goal_scope, monkeypatch, response_status, elements, expected):
    session, journey, _ = goal_scope
    sent = []
    def respond(request):
        sent.append(request)
        assert request.method == "POST"
        body = request.content.decode()
        assert "around%3A1500%2C31.23%2C121.47" in body
        assert journey.id not in body and journey.title not in body
        return httpx.Response(response_status, json={"elements": elements})
    real_client = httpx.Client
    monkeypatch.setattr(goal_artifacts.httpx, "Client", lambda **kwargs: real_client(transport=httpx.MockTransport(respond), **kwargs))
    monkeypatch.setattr(goal_artifacts, "settings", replace(settings, real_city_enabled=True, real_city_mode="live"))
    task = _task()
    result = goal_artifacts.discover_nearby_goal_places(session, journey, task,
        center_place_id="photon:W/123", query="museum", radius_m=1500)
    duplicate = goal_artifacts.discover_nearby_goal_places(session, journey, task,
        center_place_id="photon:W/123", query="museum", radius_m=1500)
    assert result["status"] == expected
    assert duplicate["status"] == "QUERY_ALREADY_ATTEMPTED"
    assert len(sent) == 1  # no mirror retry, including on HTTP 502
    session.commit()
    row = session.scalar(select(ProviderCall).where(ProviderCall.operation == "goal_area_discovery"))
    receipt = json.loads(row.request_json)
    assert receipt["max_attempts"] == 1 and receipt["radius_m"] == 1500
    assert receipt["center_source_url"] == "https://www.openstreetmap.org/way/123"
    assert row.latency_ms is not None
    if elements and response_status == 200:
        lead = result["places"][0]
        assert lead["source_url"] == "https://www.openstreetmap.org/node/456"
        assert lead["cost_status"] == lead["opening_status"] == "UNKNOWN"
        assert task["research_places"][-1] == lead
        assert json.loads(row.response_json)["places"][0] == lead
    if response_status == 502:
        other = goal_artifacts.discover_nearby_goal_places(session, journey, task,
            center_place_id="photon:W/123", query="park")
        assert other["status"] == "PROVIDER_UNAVAILABLE" and len(sent) == 1


@pytest.mark.parametrize("fields,status", [
    ({"center_place_id": "other-task"}, 403),
    ({"radius_m": 5001}, 422),
    ({"radius_m": True}, 422),
    ({"limit": 9}, 422),
])
def test_area_scope_and_limits_precede_network(goal_scope, monkeypatch, fields, status):
    session, journey, _ = goal_scope
    monkeypatch.setattr(goal_artifacts.httpx, "Client", lambda **_: pytest.fail("must reject before network"))
    with pytest.raises(HTTPException) as error:
        goal_artifacts.discover_nearby_goal_places(session, journey, _task(),
            **{"center_place_id": "photon:W/123", "query": "museum", **fields})
    assert error.value.status_code == status


def test_existing_candidate_can_continue_research_but_selected_plan_cannot(goal_scope, monkeypatch):
    session, journey, member = goal_scope
    created = _create(session, journey, member)
    plan = PlanVersion(id="TEST_FIXTURE_PLAN", journey_id=journey.id, version_no=1,
        planning_mode="balanced", status="CANDIDATE", source="TEST_FIXTURE", total_cost_minor=0,
        currency="CNY", estimated_duration_min=0, created_at=_now())
    session.add(plan)
    session.commit()
    class Agent:
        provider_key = model_key = "TEST_FIXTURE"
        def _complete(self, messages):
            return {"content": "TEST_FIXTURE research can continue without selecting candidate"}
    monkeypatch.setattr(goal_tasks, "_new_goal_agent", lambda *_: Agent())
    result = goal_tasks.resume_goal_task(session, journey, member, created["task_id"])
    assert result["usage"]["model_turns"] == 1
    assert session.get(PlanVersion, plan.id).status == "CANDIDATE"
    assert journey.active_plan_version_id is None and journey.status == "DRAFT"
    plan.status = "SELECTED"
    session.commit()
    with pytest.raises(HTTPException) as error:
        goal_tasks.resume_goal_task(session, journey, member, created["task_id"])
    assert error.value.status_code == 409
    assert error.value.detail == "GOAL_TASK_REQUIRES_DRAFT_WITHOUT_SELECTED_PLAN"


def test_area_tool_is_supplied_only_in_approved_online_scope():
    definitions = {tool["function"]["name"] for tool in goal_artifacts.goal_tool_definitions()}
    assert "discover_nearby_places" in definitions & goal_tasks._ALLOWED_TOOLS
    with pytest.raises(HTTPException):
        goal_tasks._safe_args("discover_nearby_places", {"center_place_id": "a", "query": "museum", "latitude": 31}, {})


@pytest.mark.parametrize("consented", [True, False])
def test_runtime_dispatches_area_result_and_saves_same_research_place(goal_scope, monkeypatch, consented):
    session, journey, member = goal_scope
    created = _create(session, journey, member, online_research_consent=consented, max_model_turns=3)
    mission = session.get(goal_tasks.JourneyMission, created["task_id"])
    intent = json.loads(mission.intent_json)
    intent["goal_task"].update(_task())
    mission.intent_json = json.dumps(intent)
    session.commit()
    dispatched = []
    class Agent:
        provider_key = model_key = "TEST_FIXTURE"
        turn = 0
        def _complete(self, _messages):
            self.turn += 1
            assert ("discover_nearby_places" in self._tool_allowlist) == (consented and self.turn < 3)
            if not consented or self.turn > 2:
                return {"content": "TEST_FIXTURE partial research saved"}
            if self.turn == 1:
                name, args = "discover_nearby_places", {"center_place_id": "photon:W/123", "query": "museum"}
            else:
                name, args = "save_draft_itinerary", {"days": [{"date": "2026-11-01", "slots": [
                    {"title": "TEST_FIXTURE sourceful museum", "time_of_day": "afternoon", "place_id": "overpass:node/456"}]}]}
            return {"tool_calls": [{"id": f"fixture-{self.turn}", "function": {"name": name, "arguments": json.dumps(args)}}]}
    def discover(_session, _journey, task, **args):
        dispatched.append(args)
        lead = {"id": "overpass:node/456", "name": "TEST_FIXTURE sourceful museum"}
        task["research_places"].append(lead)
        return {"tool": "discover_nearby_places", "provider": "overpass", "status": "RESULTS", "places": [lead]}
    monkeypatch.setattr(goal_tasks, "_new_goal_agent", lambda *_: Agent())
    monkeypatch.setattr(goal_tasks, "discover_nearby_goal_places", discover)
    goal_tasks.resume_goal_task(session, journey, member, created["task_id"])
    restored = goal_tasks.read_goal_task(session, journey, member, created["task_id"])
    assert len(dispatched) == int(consented)
    if consented:
        assert restored["tool_steps"][0]["tool_name"] == "discover_nearby_places"
        assert restored["tool_steps"][0]["result"]["provider"] == "overpass"
        assert restored["draft_artifact"]["days"][0]["slots"][0]["place_id"] == "overpass:node/456"
    assert journey.status == "DRAFT" and journey.active_plan_version_id is None
