from __future__ import annotations

import json
from dataclasses import replace

import httpx
import pytest
from demo_stage import demo_reset_headers
from fastapi.testclient import TestClient

import app.main as main_module
from app.agent.orchestrator import HermesJourneyAgent
from app.agent.runtime import DeepSeekJourneyAgent
from app.core.config import settings as runtime_settings
from app.db.models import AgentRun, Event, JourneyMission, Place
from app.db.session import SessionLocal

client = TestClient(main_module.app)


def test_default_hermes_model_order_is_international_then_domestic_fallbacks():
    assert runtime_settings.hermes_model == "cn:glm-5.3-flash"
    assert runtime_settings.hermes_model_fallbacks == (
        "cn:glm-5.3-flash",
        "cn:deepseek-v4.1-flash",
    )


def _selected_journey() -> str:
    ids = client.post("/api/v1/demo/reset", headers=demo_reset_headers()).json()
    journey_id = ids["journey_id"]
    generated = client.post(
        f"/api/v1/journeys/{journey_id}/plans/generate", json={"candidate_count": 1}
    )
    assert generated.status_code == 201, generated.text
    selected = client.post(
        f"/api/v1/journeys/{journey_id}/plans/{generated.json()[0]['id']}/select"
    )
    assert selected.status_code == 200, selected.text
    return journey_id


def test_natural_language_command_persists_mission_and_external_boundary():
    if runtime_settings.ai_api_key:
        pytest.skip("live model environment is configured")
    journey_id = _selected_journey()
    response = client.post(
        f"/api/v1/journeys/{journey_id}/agent/commands",
        json={
            "command": "下午海河沿线有交通管制，我不想淋雨，游船和晚餐别动，最多多花50元。你自己重新安排。",
            "requested_autonomy": "EXECUTE_WITHIN_BOUNDS",
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["mission"]["requested_autonomy"] == "EXECUTE_WITHIN_BOUNDS"
    assert "PREFER_INDOOR" in body["mission"]["objective_codes"]
    assert body["mission"]["max_cost_delta_minor"] == 5000
    assert body["mission"]["protected_activity_ids"]
    assert body["run"]["status"] == "SKIPPED_EXTERNAL_DEPENDENCY"
    with SessionLocal() as session:
        mission = session.get(JourneyMission, body["mission"]["id"])
        run = session.get(AgentRun, body["run"]["run_id"])
        event = session.get(Event, body["event_id"])
        assert mission is not None
        assert run is not None
        assert event is not None
        assert event.provenance == "USER_REPORTED"
        assert event.event_type == "TRAFFIC_DELAY"


def test_agent_command_reuses_existing_actionable_event_for_same_current_activity():
    journey_id = _selected_journey()
    started = client.post(f"/api/v1/journeys/{journey_id}/start")
    assert started.status_code == 200, started.text
    current_activity_id = client.get(f"/api/v1/journeys/{journey_id}").json()[
        "current_activity_id"
    ]
    original = client.post(
        f"/api/v1/journeys/{journey_id}/events",
        json={
            "event_type": "CLOSURE",
            "severity": "MAJOR",
            "affected_activity_id": current_activity_id,
            "payload": {"reason": "existing closure for idempotency test"},
        },
    )
    assert original.status_code == 201, original.text
    original_id = original.json()["id"]

    response = client.post(
        f"/api/v1/journeys/{journey_id}/agent/commands",
        json={
            "command": "现在下一站临时闭馆，请基于这条已经记录的闭馆事件提出重规划，只生成方案，不接受。",
            "requested_autonomy": "PLAN_ONLY",
        },
    )
    assert response.status_code == 200, response.text
    assert response.json()["event_id"] == original_id
    events = client.get(f"/api/v1/journeys/{journey_id}/events")
    assert events.status_code == 200, events.text
    assert [item["id"] for item in events.json()] == [original_id]


def test_agent_runtime_uses_model_selected_tool_loop_and_reloadable_trace(monkeypatch):
    journey_id = _selected_journey()
    calls: list[dict[str, object]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        calls.append(payload)
        if len(calls) == 1:
            message = {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "id": "call-inspect-journey",
                        "type": "function",
                        "function": {
                            "name": "inspect_journey",
                            "arguments": json.dumps({"journey_id": journey_id}),
                        },
                    }
                ],
            }
        elif len(calls) == 2:
            message = {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "id": "call-inspect-twin",
                        "type": "function",
                        "function": {
                            "name": "inspect_twin",
                            "arguments": json.dumps({"journey_id": journey_id}),
                        },
                    }
                ],
            }
        else:
            message = {
                "role": "assistant",
                "content": "Inspected the current journey and twin; no mutation is needed.",
            }
        return httpx.Response(200, json={"choices": [{"message": message}]})

    fake_client = httpx.Client(transport=httpx.MockTransport(handler))
    fake_agent = object.__new__(DeepSeekJourneyAgent)
    fake_agent.model_key = "deepseek-chat"
    fake_agent._client = fake_client
    fake_agent._owns_client = False
    monkeypatch.setattr(
        main_module,
        "settings",
        replace(runtime_settings, ai_api_key="test-key", ai_model="deepseek/deepseek-chat"),
    )
    monkeypatch.setattr(main_module, "DeepSeekJourneyAgent", lambda: fake_agent)

    response = client.post(
        f"/api/v1/journeys/{journey_id}/agent/commands",
        json={
            "command": "先检查当前行程和实时状态，再告诉我是否需要调整。",
            "requested_autonomy": "PLAN_ONLY",
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert [step["tool_name"] for step in body["run"]["tool_steps"]] == [
        "inspect_journey",
        "inspect_twin",
    ]
    assert body["run"]["status"] == "COMPLETED"
    assert len(calls) == 3

    reloaded = client.get(f"/api/v1/journeys/{journey_id}/agent/runs/{body['run']['run_id']}")
    assert reloaded.status_code == 200, reloaded.text
    assert [step["tool_name"] for step in reloaded.json()["tool_steps"]] == [
        "inspect_journey",
        "inspect_twin",
    ]


def test_agent_runtime_records_truncated_tool_json_instead_of_http_500(monkeypatch):
    journey_id = _selected_journey()
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            message = {
                "role": "assistant",
                "content": "",
                "tool_calls": [{
                    "id": "call-truncated",
                    "type": "function",
                    "function": {"name": "inspect_journey", "arguments": '{"journey_id":"'},
                }],
            }
        else:
            message = {"role": "assistant", "content": "The tool payload was malformed; no action was taken."}
        return httpx.Response(200, json={"choices": [{"message": message}]})

    fake_client = httpx.Client(transport=httpx.MockTransport(handler))
    fake_agent = object.__new__(DeepSeekJourneyAgent)
    fake_agent.model_key = "cn:glm-5.3-flash"
    fake_agent._client = fake_client
    fake_agent._owns_client = False
    monkeypatch.setattr(
        main_module,
        "settings",
        replace(runtime_settings, ai_api_key="test-key", ai_model="cn:glm-5.3-flash"),
    )
    monkeypatch.setattr(main_module, "DeepSeekJourneyAgent", lambda: fake_agent)

    response = client.post(
        f"/api/v1/journeys/{journey_id}/agent/commands",
        json={"command": "请检查当前行程和实时状态。", "requested_autonomy": "PLAN_ONLY"},
    )
    assert response.status_code == 200, response.text
    steps = response.json()["run"]["tool_steps"]
    assert steps[0]["status"] == "TOOL_ERROR"
    assert steps[0]["decision"] == "REJECT_MALFORMED_ARGUMENTS"
    assert response.json()["run"]["status"] == "COMPLETED"


def test_agent_runtime_stops_search_saturation_before_more_domain_calls(monkeypatch):
    journey_id = _selected_journey()
    calls = 0

    def tool_message(name: str, arguments: dict[str, object], call_id: str) -> dict[str, object]:
        return {
            "role": "assistant",
            "content": "",
            "tool_calls": [{
                "id": call_id,
                "type": "function",
                "function": {"name": name, "arguments": json.dumps(arguments)},
            }],
        }

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            message = tool_message("inspect_journey", {"journey_id": journey_id}, "call-journey")
        elif calls == 2:
            message = tool_message("inspect_twin", {"journey_id": journey_id}, "call-twin")
        elif calls in {3, 4, 5, 6}:
            message = tool_message(
                "search_city_services",
                {"journey_id": journey_id, "q": f"museum-{calls}"},
                f"call-search-{calls}",
            )
        else:
            message = {
                "role": "assistant",
                "content": "Search budget is exhausted; I will choose a different strategy.",
            }
        return httpx.Response(200, json={"choices": [{"message": message}]})

    fake_client = httpx.Client(transport=httpx.MockTransport(handler))
    fake_agent = object.__new__(DeepSeekJourneyAgent)
    fake_agent.model_key = "cn:glm-5.3-flash"
    fake_agent._client = fake_client
    fake_agent._owns_client = False
    monkeypatch.setattr(
        main_module,
        "settings",
        replace(runtime_settings, ai_api_key="test-key", ai_model="cn:glm-5.3-flash"),
    )
    monkeypatch.setattr(main_module, "DeepSeekJourneyAgent", lambda: fake_agent)

    response = client.post(
        f"/api/v1/journeys/{journey_id}/agent/commands",
        json={"command": "先检查状态，再搜索合适地点；若搜索没有新增信息就换策略。", "requested_autonomy": "PLAN_ONLY"},
    )
    assert response.status_code == 200, response.text
    steps = response.json()["run"]["tool_steps"]
    assert steps[-1]["tool_name"] == "search_city_services"
    assert steps[-1]["decision"] == "STOP_SEARCH_SATURATION"
    assert steps[-1]["status"] == "TOOL_ERROR"
    assert calls == 7


def test_agent_runtime_limits_batched_city_searches_to_one_per_turn(monkeypatch):
    journey_id = _selected_journey()
    calls = 0

    def call(call_id: str, name: str, arguments: dict[str, object]) -> dict[str, object]:
        return {
            "id": call_id,
            "type": "function",
            "function": {"name": name, "arguments": json.dumps(arguments)},
        }

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            message = {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    call("batch-journey", "inspect_journey", {"journey_id": journey_id}),
                    call("batch-twin", "inspect_twin", {"journey_id": journey_id}),
                    call("batch-search-one", "search_city_services", {"journey_id": journey_id, "q": "museum"}),
                    call("batch-search-two", "search_city_services", {"journey_id": journey_id, "q": "culture"}),
                    call("batch-search-three", "search_city_services", {"journey_id": journey_id, "q": "indoor"}),
                ],
            }
        else:
            message = {"role": "assistant", "content": "Search batch limited; I will reassess using the returned candidates."}
        return httpx.Response(200, json={"choices": [{"message": message}]})

    fake_client = httpx.Client(transport=httpx.MockTransport(handler))
    fake_agent = object.__new__(DeepSeekJourneyAgent)
    fake_agent.model_key = "cn:glm-5.3-flash"
    fake_agent._client = fake_client
    fake_agent._owns_client = False
    monkeypatch.setattr(
        main_module,
        "settings",
        replace(runtime_settings, ai_api_key="test-key", ai_model="cn:glm-5.3-flash"),
    )
    monkeypatch.setattr(main_module, "DeepSeekJourneyAgent", lambda: fake_agent)

    response = client.post(
        f"/api/v1/journeys/{journey_id}/agent/commands",
        json={"command": "检查当前状态后搜索室内地点，并根据结果调整策略。", "requested_autonomy": "PLAN_ONLY"},
    )
    assert response.status_code == 200, response.text
    steps = response.json()["run"]["tool_steps"]
    assert [step["decision"] for step in steps] == [
        "ALLOW_AUTO",
        "ALLOW_AUTO",
        "ALLOW_AUTO",
        "STOP_SEARCH_BATCH",
        "STOP_SEARCH_BATCH",
    ]
    assert calls == 2


def test_hermes_runtime_uses_configured_model_fallback_chain(monkeypatch):
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        calls.append(payload["model"])
        if payload["model"] == "global:deep-model":
            return httpx.Response(503, json={"error": "international unavailable"})
        return httpx.Response(
            200,
            json={"choices": [{"message": {"role": "assistant", "content": "READY"}}]},
        )

    fake_client = httpx.Client(transport=httpx.MockTransport(handler))
    monkeypatch.setattr(
        "app.agent.orchestrator.settings",
        replace(
            runtime_settings,
            hermes_api_url="http://wb2api.test/v1/chat/completions",
            hermes_api_key="test-key",
            hermes_model="global:deep-model",
            hermes_model_fallbacks=("cn:glm-5.3-flash", "cn:deepseek-v4.1-flash"),
        ),
    )
    agent = HermesJourneyAgent(client=fake_client)
    message = agent._complete([])

    assert message["content"] == "READY"
    assert agent.model_key == "cn:glm-5.3-flash"
    assert calls == ["global:deep-model", "cn:glm-5.3-flash"]


def test_hermes_runtime_reaches_domestic_deepseek_after_glm_failure(monkeypatch):
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        model = json.loads(request.content)["model"]
        calls.append(model)
        if model in {"global:deep-model", "cn:glm-5.3-flash"}:
            return httpx.Response(503, json={"error": "model unavailable"})
        return httpx.Response(
            200,
            json={"choices": [{"message": {"role": "assistant", "content": "READY"}}]},
        )

    fake_client = httpx.Client(transport=httpx.MockTransport(handler))
    monkeypatch.setattr(
        "app.agent.orchestrator.settings",
        replace(
            runtime_settings,
            hermes_api_url="http://wb2api.test/v1/chat/completions",
            hermes_api_key="test-key",
            hermes_model="global:deep-model",
            hermes_model_fallbacks=("cn:glm-5.3-flash", "cn:deepseek-v4.1-flash"),
        ),
    )
    agent = HermesJourneyAgent(client=fake_client)
    message = agent._complete([])

    assert message["content"] == "READY"
    assert agent.model_key == "cn:deepseek-v4.1-flash"
    assert calls == [
        "global:deep-model",
        "cn:glm-5.3-flash",
        "cn:deepseek-v4.1-flash",
    ]


def test_hermes_runtime_skips_empty_glm_response_and_reaches_domestic_deepseek(monkeypatch):
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        model = json.loads(request.content)["model"]
        calls.append(model)
        if model == "global:deep-model":
            return httpx.Response(503, json={"error": "international unavailable"})
        if model == "cn:glm-5.3-flash":
            return httpx.Response(200, json={"choices": [{"message": {"role": "assistant"}}]})
        return httpx.Response(
            200,
            json={"choices": [{"message": {"role": "assistant", "content": "READY"}}]},
        )

    fake_client = httpx.Client(transport=httpx.MockTransport(handler))
    monkeypatch.setattr(
        "app.agent.orchestrator.settings",
        replace(
            runtime_settings,
            hermes_api_url="http://wb2api.test/v1/chat/completions",
            hermes_api_key="test-key",
            hermes_model="global:deep-model",
            hermes_model_fallbacks=("cn:glm-5.3-flash", "cn:deepseek-v4.1-flash"),
        ),
    )
    agent = HermesJourneyAgent(client=fake_client)
    message = agent._complete([])

    assert message["content"] == "READY"
    assert agent.model_key == "cn:deepseek-v4.1-flash"


    assert calls == [
        "global:deep-model",
        "cn:glm-5.3-flash",
        "cn:deepseek-v4.1-flash",
    ]


def test_hermes_runtime_consumes_wb2api_streaming_tool_call(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        assert payload["stream"] is True
        body = "".join(
            [
                'data: {"choices":[{"delta":{"role":"assistant","tool_calls":[{"index":0,"id":"call-1","type":"function","function":{"name":"inspect_journey","arguments":"{\\"journey_id\\":\\""}}]}}]}\n\n',
                'data: {"choices":[{"delta":{"tool_calls":[{"index":0,"function":{"arguments":"journey-1\\"}"}}]}}]}\n\n',
                "data: [DONE]\n\n",
            ]
        )
        return httpx.Response(
            200,
            headers={"content-type": "text/event-stream"},
            content=body.encode(),
        )

    fake_client = httpx.Client(transport=httpx.MockTransport(handler))
    monkeypatch.setattr(
        "app.agent.orchestrator.settings",
        replace(
            runtime_settings,
            hermes_api_url="http://wb2api.test/v1/chat/completions",
            hermes_api_key="test-key",
            hermes_model="cn:glm-5.3-flash",
            hermes_model_fallbacks=(),
        ),
    )
    agent = HermesJourneyAgent(client=fake_client)
    message = agent._complete([])

    assert message["tool_calls"][0]["function"]["name"] == "inspect_journey"
    assert json.loads(message["tool_calls"][0]["function"]["arguments"]) == {
        "journey_id": "journey-1"
    }


def test_hermes_runtime_retries_an_empty_stream_without_switching_model(monkeypatch):
    calls: list[bool] = []

    def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        calls.append(bool(payload["stream"]))
        if payload["stream"]:
            return httpx.Response(
                200,
                headers={"content-type": "text/event-stream"},
                content=(
                    'data: {"choices":[{"delta":{"reasoning_content":"partial"}}]}\n\n'
                    "data: [DONE]\n\n"
                ).encode(),
            )
        return httpx.Response(
            200,
            json={"choices": [{"message": {"role": "assistant", "content": "READY"}}]},
        )

    fake_client = httpx.Client(transport=httpx.MockTransport(handler))
    monkeypatch.setattr(
        "app.agent.orchestrator.settings",
        replace(
            runtime_settings,
            hermes_api_url="http://wb2api.test/v1/chat/completions",
            hermes_api_key="test-key",
            hermes_model="cn:glm-5.3-flash",
            hermes_model_fallbacks=("cn:deepseek-v4.1-flash",),
        ),
    )
    agent = HermesJourneyAgent(client=fake_client)
    message = agent._complete([])

    assert message["content"] == "READY"
    assert agent.model_key == "cn:glm-5.3-flash"
    assert calls == [True, False]


def test_estimate_place_facts_is_explicitly_non_authoritative():
    journey_id = _selected_journey()
    response = client.post(
        "/api/v1/agent/tools/estimate_place_facts",
        json={
            "request_id": "estimate-place-facts-1",
            "agent_id": "test-agent",
            "journey_id": journey_id,
            "place_id": "place-riverside-museum",
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["estimate"]["authority_eligible"] is False
    assert body["estimate"]["opening_hours"]["status"] == "ESTIMATED_AGENT"
    assert body["estimate"]["cost_evidence"]["status"] == "ESTIMATED_AGENT"
    assert "cannot make a plan selectable" in body["warning"]
    assert body["estimate"]["cost_evidence"]["currency"] == client.get(
        f"/api/v1/journeys/{journey_id}"
    ).json()["budget"]["currency"]


def test_acquire_place_facts_commits_canonical_observation_before_next_read(monkeypatch):
    journey_id = _selected_journey()

    def fake_acquire(session, journey, *, place_ids=None, source_bindings=None):
        place = session.get(Place, place_ids[0])
        metadata = json.loads(place.metadata_json or "{}")
        metadata["test_committed_fact"] = "VERIFIED_PROVIDER"
        place.metadata_json = json.dumps(metadata)
        session.flush()
        return {"status": "ACQUIRED", "places": [{"place_id": place.id}]}

    monkeypatch.setattr("app.agent.gateway.acquire_place_facts", fake_acquire)
    response = client.post(
        "/api/v1/agent/tools/acquire_place_facts",
        json={
            "request_id": "acquire-commit-1",
            "agent_id": "test-agent",
            "journey_id": journey_id,
            "place_id": "place-riverside-museum",
        },
    )
    assert response.status_code == 200, response.text
    with SessionLocal() as session:
        place = session.get(Place, "place-riverside-museum")
        assert json.loads(place.metadata_json)["test_committed_fact"] == "VERIFIED_PROVIDER"


def test_wb2api_stream_retains_reasoning_for_tool_continuation():
    chunks = [
        {"choices": [{"delta": {"reasoning_content": "protocol-continuation"}}]},
        {"choices": [{"delta": {"content": "OK"}}]},
    ]
    result = HermesJourneyAgent._merge_sse(
        [*("data: " + json.dumps(chunk) for chunk in chunks), "data: [DONE]"]
    )
    assert result["reasoning_content"] == "protocol-continuation"
    assert result["content"] == "OK"
