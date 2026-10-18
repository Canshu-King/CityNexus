"""Reform 2026-10-18, fact completion: the agent can estimate a place from its city peers.

The order's first product slice was source research; this is the next one it names -- fact
completion. The value of this tool is not that it produces numbers; it is that the numbers stay
strategy evidence. So the arms check both halves:

  - with verified peers, the median of their hours and costs comes back with `peer_count`;
  - the place's canonical columns (`opening_hours_json`, `cost_evidence` inside metadata) do not
    change -- only `strategy_estimate` is written;
  - a number the model supplies is recorded as AGENT_PROVIDED_HYPOTHESIS;
  - with no peers, no amount appears at all: an estimate that has nothing to stand on says so.

Peers are rows this test writes, not a provider: nothing here claims a live catalogue.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select

import app.main as main_module
from app.agent.delegation_policy import READ_ACTIONS
from app.agent.contracts import AgentAction
from app.agent.tool_catalog import RUNTIME_MCP_ALLOWLIST_V2, TOOL_BY_NAME
from app.db.models import Journey, Place
from app.db.session import SessionLocal
from demo_stage import demo_reset_headers  # noqa: E402  (ORD-0389)

client = TestClient(main_module.app)
TOOL = "estimate_place_facts"


def _journey() -> tuple[str, str, str]:
    ids = client.post("/api/v1/demo/reset", headers=demo_reset_headers()).json()
    journey_id = ids["journey_id"]
    with SessionLocal() as session:
        journey = session.get(Journey, journey_id)
        assert journey is not None
        return journey_id, journey.city_code, journey.budget_currency


def _place(
    city_code: str,
    category: str,
    name: str,
    *,
    hours: dict | None = None,
    cost: dict | None = None,
) -> str:
    with SessionLocal() as session:
        place = Place(
            id=f"reform-place-{uuid4()}",
            provider_key="reform-test",
            external_id=f"reform-{uuid4()}",
            city_code=city_code,
            name=name,
            category=category,
            opening_hours_json=json.dumps(hours or {}),
            tags_json="{}",
            metadata_json=json.dumps({"cost_evidence": cost} if cost else {}),
            updated_at=datetime.now(timezone.utc).isoformat(),
        )
        session.add(place)
        session.commit()
        return place.id


def _estimate(journey_id: str, place_id: str | None, **extra: object):
    payload: dict[str, object] = {
        "request_id": "reform-estimate-" + str(uuid4()),
        "journey_id": journey_id,
    }
    if place_id is not None:
        payload["place_id"] = place_id
    payload.update(extra)
    return client.post(f"/api/v1/agent/tools/{TOOL}", json=payload)


def test_r1_tool_is_advertised_as_strategy_evidence() -> None:
    v1 = {row["name"] for row in client.get("/api/v1/agent/tools").json()}
    v2 = {row["name"] for row in client.get("/api/v1/agent/tools/v2").json()}
    assert TOOL in v2
    assert TOOL not in v1, "new capabilities land in v2; the v1 catalog stays frozen"
    assert TOOL in RUNTIME_MCP_ALLOWLIST_V2
    assert AgentAction.ESTIMATE_PLACE_FACTS in READ_ACTIONS
    entry = TOOL_BY_NAME[TOOL].as_dict()
    assert entry["mutates_domain_truth"] is False
    assert entry["changes_money"] is False


def test_r2_peers_give_a_median_and_canonical_columns_stay_put() -> None:
    journey_id, city_code, currency = _journey()
    category = f"reform-cafe-{uuid4()}"
    _place(city_code, category, "peer one", hours={"open": "09:00", "close": "18:00"},
           cost={"status": "KNOWN", "amount_minor": 3000, "currency": currency})
    _place(city_code, category, "peer two", hours={"open": "10:00", "close": "20:00"},
           cost={"status": "VERIFIED_PROVIDER", "amount_minor": 5000, "currency": currency})
    target = _place(city_code, category, "target")

    answer = _estimate(journey_id, target)
    assert answer.status_code == 200, answer.text
    estimate = answer.json()["estimate"]
    assert estimate["authority_eligible"] is False
    assert estimate["opening_hours"]["status"] == "ESTIMATED_AGENT"
    assert estimate["opening_hours"]["open_minutes"] == 570
    assert estimate["opening_hours"]["close_minutes"] == 1140
    assert estimate["opening_hours"]["peer_count"] == 2
    assert estimate["cost_evidence"]["amount_minor"] == 4000
    assert estimate["cost_evidence"]["peer_count"] == 2

    with SessionLocal() as session:
        row = session.get(Place, target)
        assert row is not None
        assert json.loads(row.opening_hours_json or "{}") == {}, "canonical hours must not be written"
        metadata = json.loads(row.metadata_json or "{}")
        assert "cost_evidence" not in metadata, "canonical cost must not be written"
        assert metadata["strategy_estimate"]["status"] == "ESTIMATED_AGENT"
        assert metadata["strategy_estimate"]["authority_eligible"] is False


def test_r3_a_model_number_is_recorded_as_a_hypothesis() -> None:
    journey_id, city_code, _currency = _journey()
    category = f"reform-bar-{uuid4()}"
    target = _place(city_code, category, "target")
    answer = _estimate(
        journey_id,
        target,
        estimated_open_minutes=660,
        estimated_close_minutes=1380,
        estimated_cost_minor=2500,
    )
    assert answer.status_code == 200, answer.text
    estimate = answer.json()["estimate"]
    assert estimate["basis"] == "agent_bounded_hypothesis"
    assert estimate["opening_hours"]["basis"] == "AGENT_PROVIDED_HYPOTHESIS"
    assert estimate["opening_hours"]["open_minutes"] == 660
    assert estimate["cost_evidence"]["basis"] == "AGENT_PROVIDED_HYPOTHESIS"
    assert estimate["cost_evidence"]["amount_minor"] == 2500
    assert estimate["authority_eligible"] is False


def test_r4_no_peers_means_no_invented_number() -> None:
    journey_id, city_code, _currency = _journey()
    target = _place(city_code, f"reform-alone-{uuid4()}", "target")
    answer = _estimate(journey_id, target)
    assert answer.status_code == 200, answer.text
    estimate = answer.json()["estimate"]
    assert estimate["opening_hours"]["status"] == "ESTIMATED_AGENT"
    assert "open_minutes" not in estimate["opening_hours"]
    assert "amount_minor" not in estimate["cost_evidence"]
    assert estimate["authority_eligible"] is False


def test_r5_refusals_are_named() -> None:
    journey_id, _city_code, _currency = _journey()
    missing = _estimate(journey_id, None)
    assert missing.status_code == 422, missing.text
    foreign = _estimate(journey_id, "place-not-in-this-city")
    assert foreign.status_code == 404, foreign.text
