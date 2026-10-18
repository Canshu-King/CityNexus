"""Reform 2026-10-18, route acquisition: the write half of route comparison.

The model names no origin and no coordinates. The server resolves the target activity from the
active plan and the grounded origin from the launch contract; when either is missing the answer is a
named refusal. Execution goes through the deployment's mobility capture -- mock when no live provider
is configured -- and lands as a `RouteAcquisitionOperation` row.

The launch context here is a row this test writes (a confirmed planned origin); nothing claims a live
routing provider.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select

import app.main as main_module
from app.agent.mission_plan import build_mission_plan
from app.agent.runtime import _MUTATION_TOOLS
from app.agent.tool_catalog import RUNTIME_MCP_ALLOWLIST_V2, TOOL_BY_NAME
from app.db.models import Journey, JourneyLaunchContext, Place, RouteAcquisitionOperation
from app.db.session import SessionLocal
from demo_stage import demo_reset_headers  # noqa: E402  (ORD-0389)

client = TestClient(main_module.app)
TOOL = "acquire_route"


def _planned_journey() -> tuple[str, str, str]:
    """(journey_id, target_activity_id, target_place_id) from a selected demo plan."""
    ids = client.post("/api/v1/demo/reset", headers=demo_reset_headers()).json()
    journey_id = ids["journey_id"]
    generated = client.post(
        f"/api/v1/journeys/{journey_id}/plans/generate", json={"candidate_count": 1}
    )
    assert generated.status_code == 201, generated.text
    plan = generated.json()[0]
    selected = client.post(f"/api/v1/journeys/{journey_id}/plans/{plan['id']}/select")
    assert selected.status_code == 200, selected.text
    target = next(item for item in plan["activities"] if item.get("place_id"))
    return journey_id, target["id"], target["place_id"]


def _confirm_origin(journey_id: str, target_activity_id: str, target_place_id: str) -> str:
    """Write a user-confirmed planned origin at a different place in the same city."""
    with SessionLocal() as session:
        journey = session.get(Journey, journey_id)
        assert journey is not None
        origin = session.scalar(
            select(Place).where(
                Place.city_code == journey.city_code, Place.id != target_place_id
            ).order_by(Place.id)
        )
        assert origin is not None
        stamp = datetime.now(timezone.utc)
        session.add(
            JourneyLaunchContext(
                journey_id=journey_id,
                source_kind="PLANNED_PLACE",
                authority_kind="USER_CONFIRMED_PLANNED_ORIGIN",
                place_id=origin.id,
                target_activity_id=target_activity_id,
                display_name=origin.name,
                latitude=float(origin.latitude or 39.1),
                longitude=float(origin.longitude or 117.2),
                coordinate_crs="WGS84",
                # A window wide enough for whatever date the demo scene placed the plan on.
                valid_from="2000-01-01T00:00:00+00:00",
                valid_until="2100-01-01T00:00:00+00:00",
                created_at=stamp.isoformat(),
                updated_at=stamp.isoformat(),
            )
        )
        session.commit()
        return origin.id


def _acquire(journey_id: str, **extra: object):
    payload: dict[str, object] = {
        "request_id": "reform-acquire-route-" + str(uuid4()),
        "journey_id": journey_id,
    }
    payload.update(extra)
    return client.post(f"/api/v1/agent/tools/{TOOL}", json=payload)


def test_r1_tool_is_advertised_as_an_action() -> None:
    v1 = {row["name"] for row in client.get("/api/v1/agent/tools").json()}
    v2 = {row["name"] for row in client.get("/api/v1/agent/tools/v2").json()}
    assert TOOL in v2
    assert TOOL not in v1, "new capabilities land in v2; the v1 catalog stays frozen"
    assert TOOL in RUNTIME_MCP_ALLOWLIST_V2
    assert TOOL in _MUTATION_TOOLS
    entry = TOOL_BY_NAME[TOOL].as_dict()
    assert entry["mutates_domain_truth"] is True
    assert entry["changes_money"] is False
    plan_only = build_mission_plan(autonomy="PLAN_ONLY")
    assert TOOL not in set(plan_only.allowed_tools), "a provider call is not a free draft action"
    assert TOOL in set(plan_only.approval_required_tools)


def test_r2_a_draft_without_a_plan_is_refused_by_name() -> None:
    ids = client.post("/api/v1/demo/reset", headers=demo_reset_headers()).json()
    answer = _acquire(ids["journey_id"])
    assert answer.status_code == 409, answer.text
    assert "exact route target is unavailable" in answer.text


def test_r3_a_plan_without_a_grounded_origin_is_refused_by_name() -> None:
    journey_id, _target_id, _place_id = _planned_journey()
    answer = _acquire(journey_id)
    assert answer.status_code == 409, answer.text
    assert "grounded launch origin is unavailable" in answer.text


def test_r4_a_confirmed_origin_produces_one_operation_row() -> None:
    journey_id, target_id, target_place = _planned_journey()
    origin_place = _confirm_origin(journey_id, target_id, target_place)

    answer = _acquire(journey_id, route_mode="walk")
    assert answer.status_code == 200, answer.text
    body = answer.json()
    assert body["origin"]["source"] == "PLANNED_PLACE"
    assert body["origin"]["key"] == origin_place
    assert body["status"] in {"COMPLETED", "UNAVAILABLE", "FAILED"}, body["status"]
    assert body.get("operation_id") or body.get("id"), body

    with SessionLocal() as session:
        rows = session.scalars(
            select(RouteAcquisitionOperation).where(
                RouteAcquisitionOperation.journey_id == journey_id
            )
        ).all()
    assert len(rows) == 1
    assert rows[0].origin_key == origin_place
    assert rows[0].target_key == target_place
    assert rows[0].requested_mode == "WALK"


def test_r5_a_foreign_target_activity_is_refused() -> None:
    journey_id, _target_id, _place_id = _planned_journey()
    answer = _acquire(journey_id, target_activity_id=str(uuid4()))
    assert answer.status_code == 422, answer.text
    assert "not the active exact target" in answer.text
