"""Protocol fixtures for task research; these tests never use external services."""
import json

import httpx
from sqlalchemy import select

from app.agent import goal_artifacts
from app.agent.orchestrator import HermesJourneyAgent
from app.core.config import settings
from app.db.models import ProviderCall
from test_goal_tasks import goal_scope


def test_public_query_zero_result_is_recorded_and_exact_query_is_not_repeated(goal_scope, monkeypatch):
    session, journey, _ = goal_scope
    requests = []
    def respond(request):
        requests.append(request)
        features = [] if "no-match" in request.url.params["q"] else [{
            "geometry":{"coordinates":[116.0,26.0]},
            "properties":{"osm_type":"N","osm_id":123,"name":"TEST_FIXTURE Museum","osm_value":"museum"},
        }]
        return httpx.Response(200, json={"features":features})
    real_client = httpx.Client
    monkeypatch.setattr(goal_artifacts.httpx, "Client", lambda **kwargs: real_client(transport=httpx.MockTransport(respond), **kwargs))
    previous = (settings.real_city_enabled, settings.real_city_mode)
    object.__setattr__(settings,"real_city_enabled",True)
    object.__setattr__(settings,"real_city_mode","live")
    try:
        task = {}
        zero = goal_artifacts.discover_goal_places(session,journey,task,query="TEST_FIXTURE no-match")
        duplicate = goal_artifacts.discover_goal_places(session,journey,task,query="TEST_FIXTURE no-match")
        found = goal_artifacts.discover_goal_places(session,journey,task,query="TEST_FIXTURE museum")
        session.commit()
        assert zero["status"] == "NO_RESULTS" and zero["http_status"] == 200
        assert duplicate["status"] == "QUERY_ALREADY_ATTEMPTED"
        assert len(requests) == 2
        assert found["places"][0]["source_url"] == "https://www.openstreetmap.org/node/123"
        assert found["places"][0]["cost_status"] == "UNKNOWN"
        assert len(session.scalars(select(ProviderCall).where(ProviderCall.operation=="goal_place_discovery")).all()) == 2
    finally:
        object.__setattr__(settings,"real_city_enabled",previous[0])
        object.__setattr__(settings,"real_city_mode",previous[1])


def test_goal_tools_reach_the_compat_chat_completions_payload():
    previous = (settings.hermes_api_url,settings.hermes_api_key)
    object.__setattr__(settings,"hermes_api_url","https://fixture.invalid/v1/chat/completions")
    object.__setattr__(settings,"hermes_api_key","TEST_FIXTURE_TOKEN")
    def respond(request):
        payload=json.loads(request.content)
        assert payload["tool_choice"] == "auto"
        assert [item["function"]["name"] for item in payload["tools"]] == ["discover_places","save_draft_itinerary"]
        return httpx.Response(200,json={"choices":[{"finish_reason":"tool_calls","message":{
            "tool_calls":[{"id":"fixture","function":{"name":"discover_places","arguments":"{\"query\":\"TEST_FIXTURE\"}"}}]}}]})
    try:
        with httpx.Client(transport=httpx.MockTransport(respond)) as client:
            agent=HermesJourneyAgent(client=client,model_chain=("TEST_FIXTURE",),allow_budget_retry=False,
                tool_allowlist=frozenset({"discover_places","save_draft_itinerary"}),extra_tool_definitions=goal_artifacts.goal_tool_definitions())
            assert agent._complete([{"role":"user","content":"TEST_FIXTURE"}])["tool_calls"][0]["function"]["name"] == "discover_places"
    finally:
        object.__setattr__(settings,"hermes_api_url",previous[0])
        object.__setattr__(settings,"hermes_api_key",previous[1])
