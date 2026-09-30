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
from app.db.models import AgentRun, Event, JourneyMission
from app.db.session import SessionLocal

client = TestClient(main_module.app)


def test_default_hermes_model_order_is_international_then_domestic_fallbacks():
    assert runtime_settings.hermes_model == "global:deep-model"
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
