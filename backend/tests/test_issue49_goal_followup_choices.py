"""GoalTask dialogue regressions for protected late-start conflicts and narrow follow-ups."""

from __future__ import annotations

from copy import deepcopy
import json
from uuid import uuid4

from app.agent import goal_tasks
from test_goal_tasks import _create, goal_scope


_DAY_ONE = "2026-11-01"
_DAY_TWO = "2026-11-02"
_RESERVATION_ID = "TEST_FIXTURE-issue49-day-two-reservation"


def _schedule_with_protected_reservation():
    return {
        "revision": 5,
        "status": "DRAFT",
        "date_constraints": {
            _DAY_ONE: {"afternoon": {"start_not_before": "13:00"}},
        },
        "days": [
            {
                "date": _DAY_ONE,
                "slots": [{
                    "title": "TEST_FIXTURE 第一天江边散步",
                    "time_of_day": "afternoon",
                    "author": "USER",
                }],
            },
            {
                "date": _DAY_TWO,
                "slots": [
                    {
                        "title": "TEST_FIXTURE 10点已确认预约",
                        "time_of_day": "morning",
                        "start_time": "10:00",
                        "locked": True,
                        "reservation_id": _RESERVATION_ID,
                        "metadata": {"booking_reference": "TEST_FIXTURE-appointment-49"},
                    },
                    {
                        "title": "TEST_FIXTURE 次日下午活动",
                        "time_of_day": "afternoon",
                        "author": "USER",
                    },
                    {
                        "title": "TEST_FIXTURE 原定晚餐",
                        "time_of_day": "evening",
                        "author": "USER",
                    },
                ],
            },
        ],
    }


def _create_task_with_existing_schedule(scope, *, goal: str):
    session, journey, member = scope
    journey.end_at = "2026-11-02T21:00:00+08:00"
    session.commit()
    created = _create(
        session,
        journey,
        member,
        goal=goal,
        max_model_turns=8,
        max_tool_calls=8,
    )
    original = _schedule_with_protected_reservation()
    mission = session.get(goal_tasks.JourneyMission, created["task_id"])
    intent = json.loads(mission.intent_json)
    intent["goal_task"]["draft_artifact"] = deepcopy(original)
    mission.intent_json = json.dumps(intent, ensure_ascii=False)
    session.commit()
    return created, original


def _run_start_conflict_and_choice(scope, monkeypatch, *, goal: str):
    session, journey, member = scope
    created, original = _create_task_with_existing_schedule(scope, goal=goal)

    class ConflictThenChoiceAgent:
        provider_key = model_key = "TEST_FIXTURE"
        _owns_client = False

        def __init__(self):
            self.turn = 0
            self.conflict_received_by_model = None

        def _complete(self, messages):
            self.turn += 1
            if self.turn == 1:
                context = json.loads(messages[1]["content"])
                assert context["draft_artifact"] == original
                return {"tool_calls": [{
                    "id": "TEST_FIXTURE-late-start-conflict",
                    "function": {
                        "name": "replace_draft_slots",
                        "arguments": json.dumps({
                            "date": _DAY_TWO,
                            "time_of_day": "morning",
                            "start_not_before": "11:00",
                            "slots": [{
                                "title": "TEST_FIXTURE 11点后再出发",
                                "time_of_day": "morning",
                            }],
                        }, ensure_ascii=False),
                    },
                }]}

            assert self.turn == 2
            tool_result_message = next(
                message for message in reversed(messages)
                if message.get("role") == "tool"
                and message.get("tool_call_id") == "TEST_FIXTURE-late-start-conflict"
            )
            result = json.loads(tool_result_message["content"])
            self.conflict_received_by_model = deepcopy(result)
            assert result["status"] == "NEEDS_USER_CHOICE"
            assert result["reason_code"] == "PROTECTED_ACTIVITY_BEFORE_START_NOT_BEFORE"
            assert result["date"] == _DAY_TWO
            assert result["time_of_day"] == "morning"
            conflict = result["conflicts"][0]
            assert conflict["start_time"] == "10:00"
            assert conflict["start_not_before"] == "11:00"
            assert conflict["protected_markers"]["reservation_id"] == _RESERVATION_ID

            return {"tool_calls": [{
                "id": "TEST_FIXTURE-ask-about-booking-choice",
                "function": {
                    "name": "ask_traveler",
                    "arguments": json.dumps({
                        "question": "第二天10:00已有预约，与11:00后出发冲突。你想怎么安排？",
                        "options": [
                            {
                                "label": "保留预约，提前出发",
                                "description": "保留10:00预约，第二天提前出发并赶上预约。",
                            },
                            {
                                "label": "自行改约后晚些出发",
                                "description": "请你先确认预约已经调整，再按11:00后出发安排。",
                            },
                        ],
                    }, ensure_ascii=False),
                },
            }]}

    agent = ConflictThenChoiceAgent()

    def make_agent(tools):
        assert "replace_draft_slots" in tools
        assert "ask_traveler" in tools
        assert "save_draft_itinerary" not in tools
        return agent

    monkeypatch.setattr(goal_tasks, "_new_goal_agent", make_agent)
    result = goal_tasks.resume_goal_task(session, journey, member, created["task_id"])
    return created, original, agent, result


def test_late_start_conflict_reaches_model_and_produces_explicit_booking_choices(goal_scope, monkeypatch):
    session, journey, member = goal_scope
    created, original, agent, result = _run_start_conflict_and_choice(
        goal_scope,
        monkeypatch,
        goal="第二天想11点再出发，但早上10点有已确认预约，怎么安排？",
    )

    assert agent.turn == 2
    assert agent.conflict_received_by_model["reason_code"] == "PROTECTED_ACTIVITY_BEFORE_START_NOT_BEFORE"
    assert result["status"] == "NEEDS_DECISION"
    assert result["pending_question"]["question"] == "第二天10:00已有预约，与11:00后出发冲突。你想怎么安排？"
    assert result["pending_question"]["options"] == [
        {
            "label": "保留预约，提前出发",
            "description": "保留10:00预约，第二天提前出发并赶上预约。",
        },
        {
            "label": "自行改约后晚些出发",
            "description": "请你先确认预约已经调整，再按11:00后出发安排。",
        },
    ]
    assert result["draft_artifact"] == original
    session.expire_all()
    restored = goal_tasks.read_goal_task(session, journey, member, created["task_id"])
    assert restored["draft_artifact"] == original
    assert restored["draft_artifact"]["days"][1]["slots"][0]["reservation_id"] == _RESERVATION_ID


def test_followup_only_changes_dinner_and_keeps_next_day_appointment_and_other_blocks(goal_scope, monkeypatch):
    session, journey, member = goal_scope
    created, original = _create_task_with_existing_schedule(
        goal_scope,
        goal="请基于已有安排继续处理我的旅行计划。",
    )
    user_message = "只把第二天晚餐改成附近粤菜，10点预约和下午安排都不动。"

    class DinnerOnlyAgent:
        provider_key = model_key = "TEST_FIXTURE"
        _owns_client = False

        def __init__(self):
            self.turn = 0

        def _complete(self, messages):
            self.turn += 1
            if self.turn == 1:
                context = json.loads(messages[1]["content"])
                assert context["recent_user_instructions"][-1] == user_message
                assert context["draft_artifact"] == original
                return {"tool_calls": [{
                    "id": "TEST_FIXTURE-edit-only-dinner",
                    "function": {
                        "name": "replace_draft_slots",
                        "arguments": json.dumps({
                            "date": _DAY_TWO,
                            "time_of_day": "evening",
                            "slots": [{
                                "title": "TEST_FIXTURE 附近粤菜晚餐",
                                "time_of_day": "evening",
                                "notes": "用户只要求更换晚餐。",
                            }],
                        }, ensure_ascii=False),
                    },
                }]}

            assert self.turn == 2
            tool_result_message = next(
                message for message in reversed(messages)
                if message.get("role") == "tool"
                and message.get("tool_call_id") == "TEST_FIXTURE-edit-only-dinner"
            )
            tool_result = json.loads(tool_result_message["content"])
            assert tool_result == {"status": "COMPLETED", "draft_revision": original["revision"] + 1}
            return {"content": "TEST_FIXTURE 已更新第二天晚餐，预约和下午安排保留。"}

    agent = DinnerOnlyAgent()

    def make_agent(tools):
        assert "replace_draft_slots" in tools
        assert "ask_traveler" in tools
        assert "save_draft_itinerary" not in tools
        return agent

    monkeypatch.setattr(goal_tasks, "_new_goal_agent", make_agent)
    result = goal_tasks.resume_goal_task(
        session,
        journey,
        member,
        created["task_id"],
        user_message=user_message,
        message_id=uuid4(),
    )

    assert agent.turn == 2
    assert result["draft_artifact"]["revision"] == original["revision"] + 1
    assert result["draft_artifact"]["date_constraints"] == original["date_constraints"]
    assert result["draft_artifact"]["days"][0] == original["days"][0]
    saved_day_two = result["draft_artifact"]["days"][1]
    original_day_two = original["days"][1]
    assert saved_day_two["slots"][0] == original_day_two["slots"][0]
    assert saved_day_two["slots"][0]["reservation_id"] == _RESERVATION_ID
    assert saved_day_two["slots"][1] == original_day_two["slots"][1]
    assert saved_day_two["slots"][2]["title"] == "TEST_FIXTURE 附近粤菜晚餐"
    assert saved_day_two["slots"][2]["time_of_day"] == "evening"
    assert [entry["text"] for entry in result["conversation"] if entry["role"] == "user"][-1] == user_message
    session.expire_all()
    restored = goal_tasks.read_goal_task(session, journey, member, created["task_id"])
    assert [entry["text"] for entry in restored["conversation"] if entry["role"] == "user"][-1] == user_message
    assert restored["draft_artifact"] == result["draft_artifact"]
