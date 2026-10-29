"""The traveller's own question after a hop is measured: does the time I left between two stops fit it?

Written against the door the phone reaches: research -> canonical places -> a saved candidate -> 核实并冻结
今天的转场, then this read-only door.  These arms pin three things the product has to be able to say out
loud, because the 422 feasibility gate (backend/app/replanning/feasibility.py:1013) already refuses the
tighter case with 「两段安排之间留的赶路时间不够」 and gave the traveller nothing to press.

Only the provider is faked, through the freeze file's own helpers: the hours, the facts and the proposal
are all the product's.
"""

from test_bootstrap_place_facts import enabled_settings, signed_place  # noqa: F401  (fixtures imported on purpose)
from test_goal_route_freeze import (PARK, TOWER, _draft_with_canonical_places, _freeze, _no_live_answer,
                                    _store_route, _task)
from app.db.models import Activity, Journey, PlanVersion
from app.db.session import SessionLocal
from sqlalchemy import select

TIGHT = [{"day_index": 0, "slot_index": 0, "start_time": "09:00", "end_time": "10:00"},
         {"day_index": 0, "slot_index": 1, "start_time": "10:00", "end_time": "11:00"},
         {"day_index": 1, "slot_index": 0, "start_time": "09:00", "end_time": "10:00"}]


def _gaps(client, headers, root, task_id, plan_id):
    return client.get(root + f"/agent/goal-tasks/{task_id}/plans/{plan_id}/travel-gaps", headers=headers)


def _frozen_plan(signed_place, monkeypatch, schedule=None, minutes=27):
    client, owner, _outsider, journey_id, *_ = signed_place
    _no_live_answer(monkeypatch)
    task_id = _task(client, owner, journey_id)
    root, plan_id, _ids = _draft_with_canonical_places(client, owner, journey_id, task_id, schedule)
    _store_route(task_id, TOWER["id"], PARK["id"], minutes=minutes)
    answer = _freeze(client, owner, root, task_id, plan_id)
    assert answer.status_code == 200, answer.text
    assert answer.json()["frozen"] is True, answer.text
    return client, owner, root, task_id, plan_id


def test_a_hop_the_hours_already_fit_is_reported_as_fitting(signed_place, monkeypatch):
    client, owner, root, task_id, plan_id = _frozen_plan(signed_place, monkeypatch)
    answer = _gaps(client, owner, root, task_id, plan_id)
    assert answer.status_code == 200, answer.text
    body = answer.json()
    assert body["frozen"] is True, body
    same_day = [hop for hop in body["hops"] if not hop["spans_night"]]
    assert [(hop["origin_title"], hop["destination_title"], hop["planned_gap_minutes"],
             hop["required_minutes"], hop["short_by_minutes"]) for hop in same_day] == [
        ("TEST_FIXTURE 上午塔", "TEST_FIXTURE 下午湖", 240, 27, 0)], same_day
    assert body["rows"] == [], body["rows"]
    assert body["reason_code"] is None, body


def test_a_hop_tighter_than_the_measured_minutes_proposes_the_smallest_shift_and_writes_nothing(
        signed_place, monkeypatch):
    client, owner, root, task_id, plan_id = _frozen_plan(signed_place, monkeypatch, schedule=TIGHT)
    with SessionLocal() as session:
        before = {row.sequence_no: (row.start_at, row.end_at)
                  for row in session.scalars(select(Activity).where(Activity.plan_version_id == plan_id))}

    answer = _gaps(client, owner, root, task_id, plan_id)
    assert answer.status_code == 200, answer.text
    body = answer.json()
    tight = [hop for hop in body["hops"] if hop["short_by_minutes"] > 0]
    assert [(hop["planned_gap_minutes"], hop["required_minutes"], hop["short_by_minutes"])
            for hop in tight] == [(0, 27, 27)], body["hops"]
    assert [(row["title"], row["planned_start"], row["proposed_start"], row["extra_minutes"],
             row["direct_cause"]) for row in body["rows"]] == [
        ("TEST_FIXTURE 下午湖", "10:00", "10:27", 27, True)], body["rows"]

    with SessionLocal() as session:
        after = {row.sequence_no: (row.start_at, row.end_at)
                 for row in session.scalars(select(Activity).where(Activity.plan_version_id == plan_id))}
        assert after == before, "this door reads; it must not move an hour"
        plan = session.get(PlanVersion, plan_id)
        journey = session.get(Journey, plan.journey_id)
        assert plan.status == "CANDIDATE", plan.status
        assert journey.active_plan_version_id is None, journey.active_plan_version_id


def test_a_candidate_nobody_measured_is_asked_nothing_and_says_so(signed_place, monkeypatch):
    client, owner, _outsider, journey_id, *_ = signed_place
    _no_live_answer(monkeypatch)
    task_id = _task(client, owner, journey_id)
    root, plan_id, _ids = _draft_with_canonical_places(client, owner, journey_id, task_id)

    answer = _gaps(client, owner, root, task_id, plan_id)
    assert answer.status_code == 200, answer.text
    assert answer.json()["frozen"] is False, answer.text
    assert answer.json()["reason_code"] == "MOBILITY_NOT_FROZEN", answer.text
    assert answer.json()["rows"] == [], answer.text
