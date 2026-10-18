"""Reform 2026-10-18, draft generation: the agent can shape a draft without committing to it.

The order's line is "DRAFT 中必须能研究和形成明确暂定草案". This adapter is that sentence: it takes
server-owned Place IDs and creates CANDIDATE plans. The arms are mostly about what it must not do:

  - it never selects or activates a plan (the journey's active pointer is untouched);
  - it refuses fewer than two places, and places from another city, by name;
  - the answer carries the collective fit projection, with the member list stripped.

The places come from the demo scene's own plan, so the scheduler is arranging rows it already knows
rather than fixtures invented for this test.
"""

from __future__ import annotations

from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select

import app.main as main_module
from app.agent.runtime import _MUTATION_TOOLS
from app.agent.tool_catalog import RUNTIME_MCP_ALLOWLIST_V2, TOOL_BY_NAME
from app.db.models import Journey, Place
from app.db.session import SessionLocal
from demo_stage import demo_reset_headers  # noqa: E402  (ORD-0389)

client = TestClient(main_module.app)
TOOL = "generate_plans"


def _seeded_places() -> tuple[str, str, str, list[str]]:
    """(traveler_id, city_code, timezone, two place ids the scheduler already arranges)."""
    ids = client.post("/api/v1/demo/reset", headers=demo_reset_headers()).json()
    journey_id = ids["journey_id"]
    generated = client.post(
        f"/api/v1/journeys/{journey_id}/plans/generate", json={"candidate_count": 1}
    )
    assert generated.status_code == 201, generated.text
    plan = generated.json()[0]
    place_ids = [item["place_id"] for item in plan["activities"] if item.get("place_id")]
    assert len(place_ids) >= 2, place_ids
    with SessionLocal() as session:
        journey = session.get(Journey, journey_id)
        assert journey is not None
        return journey.traveler_id, journey.city_code, journey.timezone, place_ids[:3]


def _draft_journey(traveler_id: str, city_code: str, timezone_name: str) -> str:
    from datetime import datetime, timedelta, timezone

    start = datetime.now(timezone.utc) + timedelta(days=4)
    created = client.post(
        "/api/v1/journeys",
        json={
            "traveler_id": traveler_id,
            "title": "Reform draft",
            "city_code": city_code,
            "timezone": timezone_name,
            "start_at": start.isoformat(),
            "end_at": (start + timedelta(days=2)).isoformat(),
            "budget": {"amount_minor": 60000, "currency": "CNY"},
        },
    )
    assert created.status_code == 201, created.text
    return created.json()["id"]


def _generate(journey_id: str, place_ids: list[str] | None, **extra: object):
    payload: dict[str, object] = {
        "request_id": "reform-plans-" + str(uuid4()),
        "journey_id": journey_id,
    }
    if place_ids is not None:
        payload["place_ids"] = place_ids
    payload.update(extra)
    return client.post(f"/api/v1/agent/tools/{TOOL}", json=payload)


def test_r1_tool_is_advertised_as_a_mutation() -> None:
    v1 = {row["name"] for row in client.get("/api/v1/agent/tools").json()}
    v2 = {row["name"] for row in client.get("/api/v1/agent/tools/v2").json()}
    assert TOOL in v2
    assert TOOL not in v1, "new capabilities land in v2; the v1 catalog stays frozen"
    assert TOOL in RUNTIME_MCP_ALLOWLIST_V2
    assert TOOL in _MUTATION_TOOLS, "creating plans changes domain truth; inspect comes first"
    entry = TOOL_BY_NAME[TOOL].as_dict()
    assert entry["mutates_domain_truth"] is True
    assert entry["changes_money"] is False


def test_r2_a_draft_gets_candidates_and_keeps_its_active_pointer_empty() -> None:
    traveler_id, city_code, timezone_name, place_ids = _seeded_places()
    journey_id = _draft_journey(traveler_id, city_code, timezone_name)

    answer = _generate(journey_id, place_ids, candidate_count=1)
    assert answer.status_code == 200, answer.text
    body = answer.json()
    assert body["candidate_count"] >= 1
    for plan in body["plans"]:
        assert plan["status"] == "CANDIDATE", plan["status"]
        assert plan["place_ids"], "a candidate that arranges nothing is not a draft"
        assert set(plan["place_ids"]).issubset(set(place_ids))
    assert "members" not in body["collective_mediation"], "the member list is not for the model"

    with SessionLocal() as session:
        draft = session.get(Journey, journey_id)
        assert draft is not None
        assert draft.active_plan_version_id is None, "generation must not activate a candidate"


def test_r3_fewer_than_two_places_is_refused() -> None:
    traveler_id, city_code, timezone_name, place_ids = _seeded_places()
    journey_id = _draft_journey(traveler_id, city_code, timezone_name)
    answer = _generate(journey_id, place_ids[:1])
    assert answer.status_code == 422, answer.text


def test_r4_a_place_outside_the_city_is_named_in_the_refusal() -> None:
    traveler_id, city_code, timezone_name, place_ids = _seeded_places()
    journey_id = _draft_journey(traveler_id, city_code, timezone_name)
    with SessionLocal() as session:
        foreign = session.scalar(
            select(Place).where(Place.city_code != city_code).order_by(Place.id)
        )
    if foreign is None:
        # No second city on this scene: the missing id path still has to be named.
        answer = _generate(journey_id, [place_ids[0], "place-not-on-this-server"])
    else:
        answer = _generate(journey_id, [place_ids[0], foreign.id])
    assert answer.status_code == 422, answer.text
    assert "PLACE_IDS_NOT_IN_JOURNEY_CITY" in answer.text
