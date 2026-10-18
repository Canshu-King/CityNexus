"""Reform 2026-10-18, place details: acquire what the providers answer, and say what they did not.

The order asks for "地点细节获取" and for an honest failure when a source cannot answer. This
adapter wraps the deployment's own `acquire_place_facts`, so the arms are about the two states that
matter before any network call is made:

  - a place with no provider identity (`overpass:node/123` and friends) is reported as
    NO_PROVIDER_ENTITIES, with zero facts written and its canonical columns untouched;
  - an observation bound to another journey is refused by name.

The provider itself is not called here: the arm deliberately uses a place the providers have no
identity for, which is the honest "cannot acquire" answer rather than a stubbed success.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from uuid import uuid4

from fastapi.testclient import TestClient

import app.main as main_module
from app.agent.runtime import _MUTATION_TOOLS
from app.agent.tool_catalog import RUNTIME_MCP_ALLOWLIST_V2, TOOL_BY_NAME
from app.db.models import Journey, Place
from app.db.session import SessionLocal
from demo_stage import demo_reset_headers  # noqa: E402  (ORD-0389)

client = TestClient(main_module.app)
TOOL = "acquire_place_facts"


def _journey_and_place() -> tuple[str, str]:
    ids = client.post("/api/v1/demo/reset", headers=demo_reset_headers()).json()
    journey_id = ids["journey_id"]
    with SessionLocal() as session:
        journey = session.get(Journey, journey_id)
        assert journey is not None
        place = Place(
            id=f"reform-acq-{uuid4()}",
            provider_key="reform-test",
            external_id=f"reform-{uuid4()}",
            city_code=journey.city_code,
            name="no provider identity",
            category="cafe",
            opening_hours_json="{}",
            tags_json="[]",
            metadata_json="{}",
            updated_at=datetime.now(timezone.utc).isoformat(),
        )
        session.add(place)
        session.commit()
        return journey_id, place.id


def _acquire(journey_id: str, place_id: str | None, **extra: object):
    payload: dict[str, object] = {
        "request_id": "reform-acquire-" + str(uuid4()),
        "journey_id": journey_id,
    }
    if place_id is not None:
        payload["place_id"] = place_id
    payload.update(extra)
    return client.post(f"/api/v1/agent/tools/{TOOL}", json=payload)


def test_r1_tool_is_advertised_as_a_domain_mutation() -> None:
    v1 = {row["name"] for row in client.get("/api/v1/agent/tools").json()}
    v2 = {row["name"] for row in client.get("/api/v1/agent/tools/v2").json()}
    assert TOOL in v2
    assert TOOL not in v1, "new capabilities land in v2; the v1 catalog stays frozen"
    assert TOOL in RUNTIME_MCP_ALLOWLIST_V2
    assert TOOL in _MUTATION_TOOLS, "it writes canonical Place rows; inspect comes first"
    entry = TOOL_BY_NAME[TOOL].as_dict()
    assert entry["mutates_domain_truth"] is True
    assert entry["changes_money"] is False


def test_r2_a_place_without_provider_identity_is_an_honest_refusal() -> None:
    journey_id, place_id = _journey_and_place()
    with SessionLocal() as session:
        before = session.get(Place, place_id)
        assert before is not None
        before_metadata = before.metadata_json
        before_hours = before.opening_hours_json

    answer = _acquire(journey_id, place_id)
    assert answer.status_code == 200, answer.text
    receipt = answer.json()["receipt"]
    assert receipt["status"] == "NO_PROVIDER_ENTITIES"
    assert receipt["known_opening_count"] == 0
    assert receipt["known_cost_count"] == 0

    with SessionLocal() as session:
        after = session.get(Place, place_id)
        assert after is not None
        assert after.metadata_json == before_metadata, "a refusal must not write facts"
        assert after.opening_hours_json == before_hours


def test_r3_refusals_are_named() -> None:
    journey_id, _place_id = _journey_and_place()
    missing = _acquire(journey_id, None)
    assert missing.status_code == 422, missing.text
    foreign = _acquire(journey_id, "place-not-in-this-city")
    assert foreign.status_code == 404, foreign.text


def test_r4_an_observation_from_another_journey_is_refused() -> None:
    journey_id, place_id = _journey_and_place()
    answer = _acquire(journey_id, place_id, source_observation_id=str(uuid4()))
    assert answer.status_code == 409, answer.text
    assert "SOURCE_OBSERVATION_NOT_OWNED_BY_JOURNEY" in answer.text
