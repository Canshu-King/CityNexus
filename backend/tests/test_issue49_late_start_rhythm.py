from __future__ import annotations

from copy import deepcopy
from types import SimpleNamespace

from app.agent.goal_draft_patch import replace_draft_slots
from app.planning.day_rhythm import apply_day_rhythm, extract_day_rhythm


LATE_START_REQUEST = "情侣前晚玩到很迟，明天11点才出门，只改第二天上午，第一天/已订活动别动"


def test_late_night_and_eleven_o_clock_departure_constrain_optional_morning() -> None:
    rhythm = extract_day_rhythm(LATE_START_REQUEST)

    assert rhythm is not None
    assert rhythm.wake_minute == 11 * 60
    assert rhythm.late_night is True
    assert "11点才出门" in rhythm.evidence
    assert "late-night activity" in rhythm.evidence

    early = SimpleNamespace(
        role="ACTIVITY",
        title="TEST_FIXTURE 自由活动",
        start_at="2026-11-02T09:00:00+08:00",
        end_at="2026-11-02T10:00:00+08:00",
        locked=False,
        metadata={},
    )
    booked = SimpleNamespace(
        role="ACTIVITY",
        title="TEST_FIXTURE 已订活动",
        start_at="2026-11-02T10:00:00+08:00",
        end_at="2026-11-02T10:30:00+08:00",
        locked=False,
        metadata={"reservation_id": "TEST_FIXTURE-reservation"},
    )
    after_departure = SimpleNamespace(
        role="ACTIVITY",
        title="TEST_FIXTURE 11点后活动",
        start_at="2026-11-02T11:00:00+08:00",
        end_at="2026-11-02T12:00:00+08:00",
        locked=False,
        metadata={},
    )

    assert apply_day_rhythm([early, booked, after_departure], rhythm) == [booked, after_departure]


def test_second_day_morning_patch_preserves_first_day_and_other_periods() -> None:
    journey = SimpleNamespace(
        start_at="2026-11-01T08:00:00+08:00",
        end_at="2026-11-02T21:00:00+08:00",
    )
    first_day = {
        "date": "2026-11-01",
        "slots": [{
            "title": "TEST_FIXTURE 第一天已订活动",
            "time_of_day": "morning",
            "author": "USER",
            "notes": "第一天保持原样",
        }],
        "custom_day_field": "preserve first day",
    }
    second_day_evening = {
        "title": "TEST_FIXTURE 第二天已订晚餐",
        "time_of_day": "evening",
        "author": "USER",
        "notes": "其他时段保持原样",
        "reservation_id": "TEST_FIXTURE-evening-reservation",
    }
    original = {
        "revision": 4,
        "status": "DRAFT",
        "days": [
            deepcopy(first_day),
            {
                "date": "2026-11-02",
                "slots": [
                    {"title": "TEST_FIXTURE 原上午活动", "time_of_day": "morning", "author": "USER"},
                    deepcopy(second_day_evening),
                ],
            },
        ],
    }
    task = {"candidate_place_ids": [], "research_places": [], "research_areas": [], "draft_artifact": original}

    result = replace_draft_slots(
        journey,
        task,
        date="2026-11-02",
        time_of_day="morning",
        slots=[{
            "title": "TEST_FIXTURE 11点后轻松出门",
            "time_of_day": "morning",
            "notes": "11:00前不安排自由活动；晚起后再出门。",
        }],
    )

    assert result["revision"] == 5
    assert result["days"][0] == first_day
    assert result["days"][1]["slots"] == [
        {
            "title": "TEST_FIXTURE 11点后轻松出门",
            "time_of_day": "morning",
            "place_id": None,
            "notes": "11:00前不安排自由活动；晚起后再出门。",
            "author": "MODEL_SUGGESTION",
            "opening_status": "UNKNOWN",
            "cost_status": "UNKNOWN",
            "travel_time_status": "UNKNOWN",
        },
        second_day_evening,
    ]
    assert task["draft_artifact"] == original
