"""Reform 2026-10-18: one permission source, so the prompt and the loop agree.

GPT's P0-1: the runtime advertised seventeen tool definitions while the mission plan granted five, and
the loop did not enforce that grant at all. These arms pin both halves of the fix:

  - a PLAN_ONLY plan grants the six DRAFT tools and still withholds the payment/commitment actions;
  - the loop actually runs a granted draft tool, and refuses an ungranted one by name.

The refusal arm is the negative control: if the grant were not enforced, `create_booking` would reach
the Gateway and fail for a different reason.
"""

from __future__ import annotations

import json
from dataclasses import replace
from uuid import uuid4

import httpx
from fastapi.testclient import TestClient

import app.main as main_module
from app.agent.mission_plan import build_mission_plan
from app.agent.runtime import DeepSeekJourneyAgent
from app.core.config import settings as runtime_settings
from app.db.session import SessionLocal
from demo_stage import demo_reset_headers  # noqa: E402  (ORD-0389)

client = TestClient(main_module.app)
DRAFT_TOOLS = (
    "research_place_sources",
    "estimate_place_facts",
    "discover_places",
    "acquire_place_facts",
    "generate_plans",
    "compare_routes",
)


def _selected_plan() -> tuple[str, dict]:
    ids = client.post("/api/v1/demo/reset", headers=demo_reset_headers()).json()
    journey_id = ids["journey_id"]
    generated = client.post(
        f"/api/v1/journeys/{journey_id}/plans/generate", json={"candidate_count": 1}
    )
    assert generated.status_code == 201, generated.text
    plan = generated.json()[0]
    selected = client.post(f"/api/v1/journeys/{journey_id}/plans/{plan['id']}/select")
    assert selected.status_code == 200, selected.text
    return journey_id, plan


def test_r1_plan_only_grants_the_draft_tools_and_still_withholds_actions() -> None:
    plan = build_mission_plan(autonomy="PLAN_ONLY")
    allowed = set(plan.allowed_tools)
    assert set(DRAFT_TOOLS) <= allowed
    assert "create_booking" not in allowed
    assert "cancel_refundable_booking" not in allowed
    assert "accept_replan" not in allowed

    read_only = set(plan.read_only_tools)
    assert {"research_place_sources", "estimate_place_facts", "compare_routes"} <= read_only
    assert "generate_plans" not in read_only
    assert "create_booking" in set(plan.approval_required_tools)


def test_r2_the_loop_runs_a_granted_tool_and_refuses_an_ungranted_one(monkeypatch) -> None:
    journey_id, plan = _selected_plan()
    target = next(item for item in plan["activities"] if item.get("place_id"))
    calls: list[dict] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(json.loads(request.content))
        if len(calls) == 1:
            message = {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "id": "call-estimate",
                        "type": "function",
                        "function": {
                            "name": "estimate_place_facts",
                            "arguments": json.dumps(
                                {"journey_id": journey_id, "place_id": target["place_id"]}
                            ),
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
                        "id": "call-book",
                        "type": "function",
                        "function": {
                            "name": "create_booking",
                            "arguments": json.dumps(
                                {
                                    "journey_id": journey_id,
                                    "activity_id": target["id"],
                                    "provider_key": "mock-booking",
                                }
                            ),
                        },
                    }
                ],
            }
        else:
            message = {"role": "assistant", "content": "Estimated the place; did not book."}
        return httpx.Response(200, json={"choices": [{"message": message}]})

    fake_agent = object.__new__(DeepSeekJourneyAgent)
    fake_agent.model_key = "deepseek-chat"
    fake_agent._client = httpx.Client(transport=httpx.MockTransport(handler))
    fake_agent._owns_client = False
    monkeypatch.setattr(
        main_module,
        "settings",
        replace(runtime_settings, ai_api_key="test-key", ai_model="deepseek/deepseek-chat"),
    )
    monkeypatch.setattr(main_module, "DeepSeekJourneyAgent", lambda: fake_agent)

    answer = client.post(
        f"/api/v1/journeys/{journey_id}/agent/commands",
        json={"command": "先估一下这个地点的资料，别下单。", "requested_autonomy": "PLAN_ONLY"},
    )
    assert answer.status_code == 200, answer.text
    steps = answer.json()["run"]["tool_steps"]
    assert [step["tool_name"] for step in steps] == ["estimate_place_facts", "create_booking"]

    granted = steps[0]["result"]
    assert "not granted" not in json.dumps(granted, ensure_ascii=False)
    assert granted.get("estimate"), granted

    refused = steps[1]["result"]
    assert refused.get("error") == "tool is not granted by this mission plan", refused
