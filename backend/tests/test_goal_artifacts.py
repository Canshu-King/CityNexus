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


def test_public_search_can_switch_to_nominatim_after_photon_zero(goal_scope, monkeypatch):
    """Provider zero is not a global prohibition on alternative geocoders."""
    session, journey, _ = goal_scope
    journey.city_code = "CN-RV-ABC123DEF456"
    journey.title = "建宁县 · 2日行程"
    requests = []
    def respond(request):
        requests.append(str(request.url.path))
        assert "建宁县" in request.url.params["q"]
        assert "RV" not in request.url.params["q"]
        assert "ABC123" not in request.url.params["q"]
        if str(request.url.path).endswith("/api/"):
            return httpx.Response(200, json={"features": []})
        if str(request.url.path).endswith("/search"):
            assert request.headers["User-Agent"] == "CityNexus TEST_FIXTURE contact@example.invalid"
            return httpx.Response(200, json=[{
                "lat": "26.5", "lon": "116.7", "osm_type": "way", "osm_id": 987,
                "display_name": "TEST_FIXTURE 古城, 福建省, 中国", "type": "historic",
            }])
        return httpx.Response(404)
    real_client = httpx.Client
    monkeypatch.setattr(goal_artifacts.httpx, "Client",
        lambda **kwargs: real_client(transport=httpx.MockTransport(respond), **kwargs))
    previous = (settings.real_city_enabled, settings.real_city_mode, settings.city_search_user_agent)
    object.__setattr__(settings, "real_city_enabled", True)
    object.__setattr__(settings, "real_city_mode", "live")
    object.__setattr__(settings, "city_search_user_agent", "CityNexus TEST_FIXTURE contact@example.invalid")
    try:
        task = {}
        zero = goal_artifacts.discover_goal_places(
            session, journey, task, query="TEST_FIXTURE 古城", source="photon")
        found = goal_artifacts.discover_goal_places(
            session, journey, task, query="TEST_FIXTURE 古城", source="nominatim")
        duplicate = goal_artifacts.discover_goal_places(
            session, journey, task, query="TEST_FIXTURE 古城", source="nominatim")
        session.commit()
        assert zero["status"] == "NO_RESULTS"
        assert zero["provider"] == "photon"
        assert found["status"] == "RESULTS"
        assert found["provider"] == "nominatim"
        assert found["places"][0]["provider"] == "nominatim"
        assert found["places"][0]["source_url"] == "https://www.openstreetmap.org/way/987"
        assert found["places"][0]["opening_status"] == "UNKNOWN"
        assert duplicate["status"] == "QUERY_ALREADY_ATTEMPTED"
        assert requests == ["/api/", "/search"]
        calls = session.scalars(select(ProviderCall).where(
            ProviderCall.operation == "goal_place_discovery")).all()
        assert {call.provider_key for call in calls} == {"photon", "nominatim"}
    finally:
        object.__setattr__(settings, "real_city_enabled", previous[0])
        object.__setattr__(settings, "real_city_mode", previous[1])
        object.__setattr__(settings, "city_search_user_agent", previous[2])


def test_random_city_code_never_becomes_a_public_search_label(goal_scope):
    _session, journey, _member = goal_scope
    journey.city_code = "CN-RV-ABC123DEF456"
    journey.title = "PRIVATE_CUSTOM_TRIP_TITLE"
    assert goal_artifacts.public_city_label(journey) == ""
