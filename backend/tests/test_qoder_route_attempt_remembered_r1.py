"""A half-measured freeze still has to be remembered after the traveller reloads the page.

Why this exists: the departure card asks for the freeze, and the band it prints -- 转场已核实 3/4（其中 1 段
是跨夜衔接，1 段按公共交通核实）-- comes from the answer that door returned.  The frozen case rewrites the
task's stored answer so a refresh keeps saying the truth (backend/app/agent/goal_route_freeze.py, the
`mobility_frozen` write), but a partial answer wrote nothing, so a reload showed
「当天的转场还没有向高德核实过」 and an empty refusal list.  That is measured, not supposed:
trial/results/20261022_v3_human_chrome/walk-83-log.txt:34 against :54 and :55.

These arms pin the record itself: the counts the screen needs, the hop nobody answered with the reason the
provider gave, and -- the part that must not slip -- `mobility_frozen` staying false while no snapshot
exists.  Nothing here needs a network or a key: one hop is answered from a stored receipt, the other is
left unanswered on purpose.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import select

from app.db.models import Activity, JourneyMission
from app.db.session import SessionLocal
from test_bootstrap_place_facts import enabled_settings, signed_place  # noqa: F401  (fixtures are imported on purpose)
from test_goal_route_freeze import (  # noqa: F401  (the screen's own harness is reused on purpose)
    PARK, TOWER, _draft_with_canonical_places, _freeze, _no_live_answer, _store_route, _task)


def _append_one_evening_stop(plan_id: str, place_id: str) -> None:
    """Put one more placed stop at the end of the chain, so the door has a second hop to ask about.

    The saved draft is 塔 09:00 -> 湖 14:00 -> (next day) 湖 09:00, which is one hop plus a place that is not
    a hop from itself.  Adding an evening 塔 makes the chain ask two: 塔 -> 湖, answered here from the
    stored receipt, and 湖 -> 塔, left unanswered on purpose.
    """
    with SessionLocal() as session:
        rows = list(session.scalars(select(Activity).where(Activity.plan_version_id == plan_id)
                                   .order_by(Activity.sequence_no)))
        template = rows[-1]
        session.add(Activity(id=str(uuid4()), plan_version_id=plan_id,
                             sequence_no=max(row.sequence_no for row in rows) + 1,
                             activity_type="visit", title="TEST_FIXTURE 傍晚又去塔", place_id=place_id,
                             city_service_id=None, start_at="2026-11-03T17:00:00+08:00",
                             end_at="2026-11-03T18:00:00+08:00", travel_from_prev_min=0, estimated_cost_minor=0,
                             currency=template.currency, status="PLANNED", locked=False,
                             metadata_json=template.metadata_json,
                             created_at=datetime.now(timezone.utc).isoformat(),
                             updated_at=datetime.now(timezone.utc).isoformat()))
        session.commit()


def _stored_result(task_id: str) -> dict:
    with SessionLocal() as session:
        intent = json.loads(session.get(JourneyMission, task_id).intent_json)
    return intent["goal_task"]["prepared_plan"]["result"]


def test_a_partially_measured_freeze_records_what_it_measured(signed_place, monkeypatch) -> None:
    client, owner, _outsider, journey_id, *_ = signed_place
    _no_live_answer(monkeypatch)
    task_id = _task(client, owner, journey_id)
    root, plan_id, ids = _draft_with_canonical_places(client, owner, journey_id, task_id)
    _store_route(task_id, TOWER["id"], PARK["id"])
    _append_one_evening_stop(plan_id, ids[TOWER["id"]])

    answer = _freeze(client, owner, root, task_id, plan_id)
    assert answer.status_code == 200, answer.text
    body = answer.json()
    assert (body["total"], body["verified"], body["frozen"]) == (2, 1, False), body
    assert body["reason_code"] == "ROUTE_PARTIALLY_VERIFIED", body

    stored = _stored_result(task_id)
    attempt = stored["route_attempt"]
    assert (attempt["verified"], attempt["total"], attempt["frozen"]) == (1, 2, False), attempt
    assert attempt["reason_code"] == "ROUTE_PARTIALLY_VERIFIED", attempt
    # The hop nobody answered is named, with the cause the door recorded for it -- not a bare "incomplete".
    # The names are the places' own, not the slot titles the traveller typed: the door reads Place.name
    # (backend/app/agent/goal_route_freeze.py:352), so the evening stop of the same tower is the tower.
    assert [row["to_name"] for row in attempt["unanswered"]] == ["TEST_FIXTURE 塔"], attempt["unanswered"]
    assert attempt["unanswered"][0]["from_name"] == "TEST_FIXTURE 湖", attempt["unanswered"]
    assert attempt["unanswered"][0]["reason_code"], attempt["unanswered"]
    # A half-measured plan is not a frozen one, and the screen must not be able to read it as one.
    assert stored.get("mobility_frozen") is not True, stored.get("mobility_frozen")


def test_a_fully_measured_freeze_records_zero_unanswered(signed_place, monkeypatch) -> None:
    client, owner, _outsider, journey_id, *_ = signed_place
    _no_live_answer(monkeypatch)
    task_id = _task(client, owner, journey_id)
    root, plan_id, _ids = _draft_with_canonical_places(client, owner, journey_id, task_id)
    _store_route(task_id, TOWER["id"], PARK["id"])

    answer = _freeze(client, owner, root, task_id, plan_id)
    assert answer.status_code == 200, answer.text
    body = answer.json()
    assert (body["total"], body["verified"], body["frozen"]) == (1, 1, True), body

    stored = _stored_result(task_id)
    attempt = stored["route_attempt"]
    assert (attempt["verified"], attempt["total"], attempt["frozen"]) == (1, 1, True), attempt
    assert attempt["unanswered"] == [], attempt
    assert stored["mobility_frozen"] is True and stored["mobility_snapshot_id"], stored
