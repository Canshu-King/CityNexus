"""The schedule door names the row it refused, instead of refusing the whole plan in one word.

Why this file exists: walk-77 is a first-time traveller's own path.  The Agent's draft put 八达岭 in the
morning, 颐和园 in the afternoon and 天坛 as "flexible" on the same day, the card seeded per-bucket hours
(09:00, 14:00, 11:00), and the door refused with one lumped code while the screen said
「这次未能保存，时间仍留在这里，可以重试。」 -- readings at
trial/results/20261022_v3_human_chrome/walk-77-window-readback-1.txt:11 (the row that broke) and
trial/results/20261022_v3_human_chrome/walk-77-log.txt:32-33 (the refusal and the sentence).  Before this
file, no test in the suite asserted that refusal at all -- the door's own four-condition check
(backend/app/agent/goal_preparation.py:187) had no arm covering any of it.  The readback that produced
line 11 needed a second attempt: the first one copied only the .db without its -wal sibling and therefore
read an older draft, which is why it is written as r3 in the scratch instrument rather than quoted here.

These arms pin what the answer must now carry -- which rule, which row, its title, its two times and the
end it collided with -- and keep one control arm proving a properly ordered schedule still saves, so the
door cannot pass by refusing everything.
"""
from __future__ import annotations

import json
from uuid import uuid4

from test_bootstrap_place_facts import enabled_settings, signed_place  # noqa: E402,F401  (fixtures are imported on purpose)

ROOT = "/api/v1/journeys"
DATE = "2026-12-03"


def _window(journey_id: str, *, start: str, end: str) -> None:
    from app.db.models import Journey
    from app.db.session import SessionLocal

    with SessionLocal() as session:
        trip = session.get(Journey, journey_id)
        trip.start_at = f"{DATE}T{start}+08:00"
        trip.end_at = f"{DATE}T{end}+08:00"
        session.commit()


def _task_with_slots(client, owner, journey_id, titles) -> str:
    root = f"{ROOT}/{journey_id}"
    task_id = client.post(root + "/agent/goal-tasks", headers=owner, json={
        "goal": "TEST_FIXTURE 一天两站", "model_consent": False, "online_research_consent": False}).json()["task_id"]
    draft = client.put(root + f"/agent/goal-tasks/{task_id}/draft", headers=owner, json={
        "expected_revision": 0,
        "days": [{"date": DATE, "slots": [{"title": title, "time_of_day": "morning", "notes": ""} for title in titles]}]})
    assert draft.status_code == 200, draft.text
    return task_id


def _prepare(client, owner, journey_id, task_id, rows):
    return client.post(f"{ROOT}/{journey_id}/agent/goal-tasks/{task_id}/prepare-plan",
                       headers={**owner, "Idempotency-Key": str(uuid4())},
                       json={"expected_revision": 1, "schedule": rows})


def _row(slot_index: int, start: str, end: str) -> dict:
    return {"day_index": 0, "slot_index": slot_index, "start_time": start, "end_time": end}


def _envelope(answer) -> dict:
    assert answer.status_code == 422, answer.text
    body = json.loads(answer.text)
    return body["error"]


def test_a_row_that_starts_before_the_row_above_it_ends_names_that_row_and_both_times(signed_place) -> None:
    client, owner, _outsider, journey_id, *_ = signed_place
    _window(journey_id, start="09:00", end="18:00")
    task_id = _task_with_slots(client, owner, journey_id, ["TEST_FIXTURE 八达岭", "TEST_FIXTURE 天坛"])
    error = _envelope(_prepare(client, owner, journey_id, task_id,
                               [_row(0, "14:00", "15:00"), _row(1, "11:00", "12:00")]))
    assert error["code"] == "VALIDATION_ERROR"
    # The message stays what it was, so every existing reader of this door keeps working.
    assert error["message"] == "SCHEDULE_OVERLAP_OR_OUTSIDE_JOURNEY"
    assert error["reason_code"] == "ITEM_STARTS_BEFORE_PREVIOUS_ITEM_END"
    details = error["details"]
    assert details["rule"] == "overlaps_previous_item"
    assert details["sequence_no"] == 2 and details["title"] == "TEST_FIXTURE 天坛"
    assert details["start_time"] == "11:00" and details["end_time"] == "12:00"
    assert details["previous_end_time"] == "15:00"


def test_a_row_whose_end_is_not_after_its_start_is_its_own_answer(signed_place) -> None:
    client, owner, _outsider, journey_id, *_ = signed_place
    _window(journey_id, start="09:00", end="18:00")
    task_id = _task_with_slots(client, owner, journey_id, ["TEST_FIXTURE 故宫"])
    error = _envelope(_prepare(client, owner, journey_id, task_id, [_row(0, "10:00", "10:00")]))
    assert error["reason_code"] == "ITEM_END_NOT_AFTER_ITEM_START"
    assert error["details"]["rule"] == "end_not_after_start" and error["details"]["sequence_no"] == 1
    assert error["details"]["previous_end_time"] is None


def test_a_row_that_ends_after_the_journey_is_named_rather_than_lumped(signed_place) -> None:
    client, owner, _outsider, journey_id, *_ = signed_place
    _window(journey_id, start="09:00", end="18:00")
    task_id = _task_with_slots(client, owner, journey_id, ["TEST_FIXTURE 鸟巢灯光"])
    error = _envelope(_prepare(client, owner, journey_id, task_id, [_row(0, "18:30", "19:30")]))
    assert error["reason_code"] == "ITEM_ENDS_AFTER_JOURNEY_END"
    assert error["details"]["journey_end_at"].startswith("2026-12-03T18:00")


def test_a_row_that_starts_before_the_journey_is_its_own_answer(signed_place) -> None:
    client, owner, _outsider, journey_id, *_ = signed_place
    _window(journey_id, start="09:00", end="18:00")
    task_id = _task_with_slots(client, owner, journey_id, ["TEST_FIXTURE 升旗"])
    error = _envelope(_prepare(client, owner, journey_id, task_id, [_row(0, "08:00", "08:30")]))
    assert error["reason_code"] == "ITEM_STARTS_BEFORE_JOURNEY_START"
    assert error["details"]["journey_start_at"].startswith("2026-12-03T09:00")


def test_rows_in_order_still_save_so_the_door_cannot_pass_by_refusing_everything(signed_place) -> None:
    client, owner, _outsider, journey_id, *_ = signed_place
    _window(journey_id, start="09:00", end="18:00")
    task_id = _task_with_slots(client, owner, journey_id, ["TEST_FIXTURE 上午", "TEST_FIXTURE 下午"])
    answer = _prepare(client, owner, journey_id, task_id,
                      [_row(0, "09:00", "10:00"), _row(1, "14:00", "15:00")])
    assert answer.status_code == 201, answer.text
    body = answer.json()
    assert body["slots_count"] == 2 and body["mobility_frozen"] is False
    # Unplaced rows are named as their own kind of gap; this door still does not invent places.  The kind
    # is the one the preparation door actually writes (read off the same answer, not guessed).
    assert {gap["kind"] for gap in body["gaps"]} == {"PLACE_REQUIRED"}
