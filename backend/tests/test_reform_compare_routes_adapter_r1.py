"""Reform 2026-10-18, route comparison (read half): compare what the server already knows.

The urgent instruction names route comparison. Acquisition needs the launch-origin chain this tree
does not have yet, so what is delivered here is the honest read half: the stored `MobilityFact` rows
for one edge, or a named "no edge captured". The arms check the two things that could go wrong --
inventing a route, or hiding an unknown cost.

The facts are rows this test writes: nothing here claims a live provider.
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from fastapi.testclient import TestClient

import app.main as main_module
from app.agent.contracts import AgentAction
from app.agent.delegation_policy import READ_ACTIONS
from app.agent.runtime import _MUTATION_TOOLS
from app.agent.tool_catalog import RUNTIME_MCP_ALLOWLIST_V2, TOOL_BY_NAME
from app.db.models import Journey, MobilityFact
from app.db.session import SessionLocal
from demo_stage import demo_reset_headers  # noqa: E402  (ORD-0389)

client = TestClient(main_module.app)
TOOL = "compare_routes"


def _journey() -> str:
    ids = client.post("/api/v1/demo/reset", headers=demo_reset_headers()).json()
    return ids["journey_id"]


def _fact(journey_id: str, from_key: str, to_key: str, mode: str, *, cost: int | None) -> None:
    with SessionLocal() as session:
        session.add(
            MobilityFact(
                id=f"reform-route-{uuid4()}",
                journey_id=journey_id,
                option_id=None,
                from_key=from_key,
                to_key=to_key,
                mode=mode,
                duration_min=12,
                distance_m=900,
                cost_amount_minor=cost,
                currency="CNY" if cost is not None else None,
                cost_status="KNOWN" if cost is not None else "UNKNOWN",
                walking_min=12,
                transfers=0,
                weather_exposure="LOW",
                reliability_score=0.8,
                provider_key="reform-test",
                provenance="TEST_STORED_FACT",
                captured_at=datetime.now(timezone.utc).isoformat(),
            )
        )
        session.commit()


def _compare(journey_id: str, from_key: str | None, to_key: str | None, **extra: object):
    payload: dict[str, object] = {
        "request_id": "reform-routes-" + str(uuid4()),
        "journey_id": journey_id,
    }
    if from_key is not None:
        payload["from_key"] = from_key
    if to_key is not None:
        payload["to_key"] = to_key
    payload.update(extra)
    return client.post(f"/api/v1/agent/tools/{TOOL}", json=payload)


def test_r1_tool_is_advertised_as_a_read() -> None:
    v1 = {row["name"] for row in client.get("/api/v1/agent/tools").json()}
    v2 = {row["name"] for row in client.get("/api/v1/agent/tools/v2").json()}
    assert TOOL in v2
    assert TOOL not in v1, "new capabilities land in v2; the v1 catalog stays frozen"
    assert TOOL in RUNTIME_MCP_ALLOWLIST_V2
    assert TOOL not in _MUTATION_TOOLS
    assert AgentAction.COMPARE_ROUTES in READ_ACTIONS
    entry = TOOL_BY_NAME[TOOL].as_dict()
    assert entry["mutates_domain_truth"] is False
    assert entry["changes_money"] is False


def test_r2_stored_options_come_back_with_unknown_costs_intact() -> None:
    journey_id = _journey()
    pair = (f"reform-a-{uuid4()}", f"reform-b-{uuid4()}")
    _fact(journey_id, *pair, "WALK", cost=None)
    _fact(journey_id, *pair, "TRANSIT", cost=300)

    answer = _compare(journey_id, *pair)
    assert answer.status_code == 200, answer.text
    body = answer.json()
    assert body["status"] == "STORED_FACTS"
    assert body["counts_as_supply"] is True
    modes = [row["mode"] for row in body["options"]]
    assert modes == ["TRANSIT", "WALK"]
    walk = next(row for row in body["options"] if row["mode"] == "WALK")
    assert walk["cost_amount_minor"] is None
    assert walk["cost_status"] == "UNKNOWN", "an unknown cost must not be filled in"


def test_r3_an_edge_with_no_facts_says_so() -> None:
    journey_id = _journey()
    answer = _compare(journey_id, f"reform-x-{uuid4()}", f"reform-y-{uuid4()}")
    assert answer.status_code == 200, answer.text
    body = answer.json()
    assert body["status"] == "NO_STORED_ROUTE_FACTS"
    assert body["counts_as_supply"] is False
    assert body["options"] == []


def test_r4_a_mode_filter_narrows_the_answer() -> None:
    journey_id = _journey()
    pair = (f"reform-c-{uuid4()}", f"reform-d-{uuid4()}")
    _fact(journey_id, *pair, "WALK", cost=None)
    _fact(journey_id, *pair, "TRANSIT", cost=300)
    answer = _compare(journey_id, *pair, route_mode="transit")
    assert answer.status_code == 200, answer.text
    assert [row["mode"] for row in answer.json()["options"]] == ["TRANSIT"]


def test_r5_both_keys_are_required() -> None:
    journey_id = _journey()
    assert _compare(journey_id, None, "b").status_code == 422
    assert _compare(journey_id, "a", None).status_code == 422
