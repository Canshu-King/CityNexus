from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import json
import re
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.agent import goal_tasks
from app.agent.goal_draft_patch import draft_patch_definition, replace_draft_slots
from app.agent.goal_preparation import validate_draft_date_constraint
from app.agent.goal_tasks import _safe_args, _safe_tool_result, update_goal_draft
from app.db.models import Base, Journey, JourneyMember, JourneyMission, Traveler


def _journey():
    return SimpleNamespace(
        start_at="2026-11-01T08:00:00+08:00",
        end_at="2026-11-02T21:00:00+08:00",
    )


def test_patch_persists_one_date_block_bound_and_carries_protected_slots_forward():
    first_day = {
        "date": "2026-11-01",
        "slots": [{"title": "TEST_FIXTURE 第一天上午", "time_of_day": "morning", "author": "USER"}],
    }
    protected = {
        "title": "TEST_FIXTURE 已订活动",
        "time_of_day": "morning",
        "locked": True,
        "start_time": "11:30",
        "reservation_id": "TEST_FIXTURE-reservation-2",
        "metadata": {"commitment_ids": ["TEST_FIXTURE-commitment-2"]},
    }
    second_evening = {
        "title": "TEST_FIXTURE 第二天晚餐",
        "time_of_day": "evening",
        "author": "USER",
        "notes": "保留原样",
        "booking_id": "TEST_FIXTURE-booking-2",
    }
    original = {
        "revision": 7,
        "status": "DRAFT",
        "date_constraints": {
            "2026-11-01": {"afternoon": {"start_not_before": "13:00"}},
        },
        "days": [
            deepcopy(first_day),
            {
                "date": "2026-11-02",
                "slots": [
                    {"title": "TEST_FIXTURE 原上午活动", "time_of_day": "morning", "author": "USER"},
                    deepcopy(protected),
                    deepcopy(second_evening),
                ],
            },
        ],
    }
    task = {"candidate_place_ids": [], "research_places": [], "research_areas": [], "draft_artifact": original}

    result = replace_draft_slots(
        _journey(),
        task,
        date="2026-11-02",
        time_of_day="morning",
        start_not_before="11:00",
        slots=[{
            "title": "TEST_FIXTURE 11点后自由活动",
            "time_of_day": "morning",
            "notes": "从 11:00 后开始。",
        }],
    )

    assert result["revision"] == 8
    assert result["days"][0] == first_day
    assert result["days"][1]["slots"] == [
        {
            "title": "TEST_FIXTURE 11点后自由活动",
            "time_of_day": "morning",
            "place_id": None,
            "notes": "从 11:00 后开始。",
            "author": "MODEL_SUGGESTION",
            "opening_status": "UNKNOWN",
            "cost_status": "UNKNOWN",
            "travel_time_status": "UNKNOWN",
        },
        protected,
        second_evening,
    ]
    assert result["date_constraints"] == {
        "2026-11-01": {"afternoon": {"start_not_before": "13:00"}},
        "2026-11-02": {"morning": {"start_not_before": "11:00"}},
    }
    assert task["draft_artifact"] == original


def test_known_protected_conflict_returns_choice_fact_without_replacing_draft():
    protected = {
        "title": "TEST_FIXTURE 10点已订活动",
        "time_of_day": "morning",
        "locked": True,
        "start_time": "10:00",
        "reservation_id": "TEST_FIXTURE-reservation-early",
    }
    original = {
        "revision": 3,
        "days": [{
            "date": "2026-11-02",
            "slots": [deepcopy(protected), {"title": "TEST_FIXTURE 原自由活动", "time_of_day": "morning"}],
        }],
    }
    task = {"draft_artifact": original}

    result = replace_draft_slots(
        _journey(),
        task,
        date="2026-11-02",
        time_of_day="morning",
        start_not_before="11:00",
        slots=[{"title": "TEST_FIXTURE 新自由活动", "time_of_day": "morning"}],
    )

    assert result["status"] == "NEEDS_USER_CHOICE"
    assert result["reason_code"] == "PROTECTED_ACTIVITY_BEFORE_START_NOT_BEFORE"
    assert result["conflicts"] == [{
        "date": "2026-11-02",
        "time_of_day": "morning",
        "title": "TEST_FIXTURE 10点已订活动",
        "start_time": "10:00",
        "start_not_before": "11:00",
        "protected_markers": {"locked": True, "reservation_id": "TEST_FIXTURE-reservation-early"},
    }]
    assert task["draft_artifact"] == original
    assert _safe_tool_result("replace_draft_slots", result)["conflicts"] == result["conflicts"]


def test_current_prepared_time_for_protected_slot_returns_choice_fact():
    protected = {
        "title": "TEST_FIXTURE 已订活动",
        "time_of_day": "morning",
        "metadata": {"reservation_id": "TEST_FIXTURE-reservation-prepared"},
    }
    original = {
        "revision": 5,
        "days": [{"date": "2026-11-02", "slots": [deepcopy(protected)]}],
    }
    task = {
        "draft_artifact": original,
        "prepared_plan": {
            "result": {"draft_revision": 5},
            "schedule": [{"day_index": 0, "slot_index": 0, "start_time": "10:00"}],
        },
    }

    result = replace_draft_slots(
        _journey(),
        task,
        date="2026-11-02",
        time_of_day="morning",
        start_not_before="11:00",
        slots=[{"title": "TEST_FIXTURE 新自由活动", "time_of_day": "morning"}],
    )

    assert result["status"] == "NEEDS_USER_CHOICE"
    assert result["conflicts"][0]["start_time"] == "10:00"
    assert task["draft_artifact"] == original


def test_prepare_start_gate_applies_only_to_matching_date_and_block():
    draft = {"date_constraints": {"2026-11-02": {"morning": {"start_not_before": "11:00"}}}}
    free_morning = {"title": "TEST_FIXTURE 自由活动", "time_of_day": "morning"}

    with pytest.raises(HTTPException) as rejected:
        validate_draft_date_constraint(
            draft=draft, date="2026-11-02", slot=free_morning, start_time="10:30"
        )
    assert rejected.value.status_code == 422
    assert rejected.value.reason_code == "DRAFT_DATE_CONSTRAINT_VIOLATION"
    assert rejected.value.error_details["start_not_before"] == "11:00"
    assert rejected.value.error_details["title"] == "TEST_FIXTURE 自由活动"

    validate_draft_date_constraint(
        draft=draft, date="2026-11-01", slot=free_morning, start_time="10:30"
    )
    validate_draft_date_constraint(
        draft=draft,
        date="2026-11-02",
        slot={"title": "TEST_FIXTURE 下午活动", "time_of_day": "afternoon"},
        start_time="10:30",
    )


def test_prepare_protected_conflict_is_named_as_user_choice():
    draft = {"date_constraints": {"2026-11-02": {"morning": {"start_not_before": "11:00"}}}}
    protected = {
        "title": "TEST_FIXTURE 已订活动",
        "time_of_day": "morning",
        "metadata": {"reservation_id": "TEST_FIXTURE-reservation"},
    }

    with pytest.raises(HTTPException) as rejected:
        validate_draft_date_constraint(
            draft=draft, date="2026-11-02", slot=protected, start_time="10:30"
        )
    assert rejected.value.status_code == 409
    assert rejected.value.reason_code == "DRAFT_DATE_CONSTRAINT_REQUIRES_USER_CHOICE"
    assert rejected.value.error_details["choice_required"] is True
    assert rejected.value.error_details["protected_markers"] == {
        "metadata.reservation_id": "TEST_FIXTURE-reservation",
    }


def test_optional_tool_argument_keeps_legacy_calls_valid():
    legacy = {"date": "2026-11-02", "time_of_day": "morning", "slots": []}
    assert _safe_args("replace_draft_slots", legacy, {}) == legacy
    assert _safe_args("replace_draft_slots", {**legacy, "start_not_before": "11:00"}, {}) == {
        **legacy,
        "start_not_before": "11:00",
    }
    with pytest.raises(HTTPException):
        _safe_args("replace_draft_slots", {**legacy, "start_not_before": None}, {})
    parameters = draft_patch_definition()["function"]["parameters"]
    assert parameters["required"] == ["date", "time_of_day", "slots"]
    schema_pattern = parameters["properties"]["start_not_before"]["pattern"]
    assert re.fullmatch(schema_pattern, "11:00")
    assert re.fullmatch(schema_pattern, "25:00") is None


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@pytest.fixture
def user_draft_scope():
    engine = create_engine("sqlite://", future=True)
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        now = _now()
        traveler = Traveler(
            id=str(uuid4()),
            display_name="TEST_FIXTURE Issue49 owner",
            email=None,
            locale="zh-CN",
            timezone="Asia/Shanghai",
            created_at=now,
            updated_at=now,
        )
        journey = Journey(
            id=str(uuid4()),
            traveler_id=traveler.id,
            title="TEST_FIXTURE Issue49 draft",
            city_code="SHA",
            timezone="Asia/Shanghai",
            start_at="2026-11-01T09:00:00+08:00",
            end_at="2026-11-01T18:00:00+08:00",
            budget_currency="CNY",
            budget_amount_minor=50000,
            planning_mode="balanced",
            status="DRAFT",
            active_plan_version_id=None,
            current_activity_id=None,
            created_at=now,
            updated_at=now,
            deleted_at=None,
        )
        member = JourneyMember(
            id=str(uuid4()),
            journey_id=journey.id,
            traveler_id=traveler.id,
            role="OWNER",
            invited_by=traveler.id,
            expires_at=None,
            removed_at=None,
            joined_at=now,
            preferences_json="{}",
            created_at=now,
            updated_at=now,
        )
        session.add_all([traveler, journey, member])
        session.commit()
        created = goal_tasks.create_goal_task(
            session,
            journey,
            member,
            goal="TEST_FIXTURE edit one free activity",
            model_consent=False,
            online_research_consent=False,
            max_model_turns=3,
            max_tool_calls=4,
        )
        yield session, journey, member, created
    engine.dispose()


def _persist_draft(session, task_id, draft):
    mission = session.get(JourneyMission, task_id)
    intent = json.loads(mission.intent_json)
    intent["goal_task"]["draft_artifact"] = deepcopy(draft)
    mission.intent_json = json.dumps(intent, ensure_ascii=False)
    session.commit()
    return mission.intent_json


def _booking_draft():
    return {
        "revision": 4,
        "status": "DRAFT",
        "date_constraints": {
            "2026-11-01": {"morning": {"start_not_before": "11:00"}},
        },
        "days": [{
            "date": "2026-11-01",
            "slots": [
                {
                    "title": "TEST_FIXTURE 已确认预约",
                    "time_of_day": "morning",
                    "start_time": "11:30",
                    "locked": True,
                    "reservation_id": "TEST_FIXTURE-reservation-49",
                    "metadata": {"booking_reference": "TEST_FIXTURE-reference-49"},
                },
                {
                    "title": "TEST_FIXTURE 原自由活动",
                    "time_of_day": "afternoon",
                    "notes": "旧说明",
                },
            ],
        }],
    }


def test_signed_user_full_save_preserves_constraints_and_booking_while_editing_free_slot(user_draft_scope):
    session, journey, member, created = user_draft_scope
    original = _booking_draft()
    _persist_draft(session, created["task_id"], original)

    result = update_goal_draft(
        session,
        journey,
        member,
        created["task_id"],
        expected_revision=4,
        days=[{
            "date": "2026-11-01",
            "slots": [
                {
                    "title": "TEST_FIXTURE 已确认预约",
                    "time_of_day": "morning",
                    "reservation_id": "TEST_FIXTURE-reservation-49",
                },
                {
                    "title": "TEST_FIXTURE 已修改自由活动",
                    "time_of_day": "afternoon",
                    "notes": "用户修改的说明",
                },
                {
                    "title": "TEST_FIXTURE 新增自由活动",
                    "time_of_day": "evening",
                    "notes": "用户新加的活动",
                },
            ],
        }],
    )

    assert result["draft_artifact"]["revision"] == 5
    session.expire_all()
    persisted = json.loads(session.get(JourneyMission, created["task_id"]).intent_json)["goal_task"]["draft_artifact"]
    assert persisted["date_constraints"] == original["date_constraints"]
    assert persisted["days"][0]["slots"][0] == original["days"][0]["slots"][0]
    assert persisted["days"][0]["slots"][1]["title"] == "TEST_FIXTURE 已修改自由活动"
    assert persisted["days"][0]["slots"][1]["notes"] == "用户修改的说明"
    assert persisted["days"][0]["slots"][2]["title"] == "TEST_FIXTURE 新增自由活动"
    assert persisted["days"][0]["slots"][2]["time_of_day"] == "evening"


def test_signed_user_full_save_omitting_booking_returns_choice_and_keeps_persisted_draft(user_draft_scope):
    session, journey, member, created = user_draft_scope
    original = _booking_draft()
    before_json = _persist_draft(session, created["task_id"], original)

    with pytest.raises(HTTPException) as rejected:
        update_goal_draft(
            session,
            journey,
            member,
            created["task_id"],
            expected_revision=4,
            days=[{
                "date": "2026-11-01",
                "slots": [{"title": "TEST_FIXTURE 只保留自由活动", "time_of_day": "afternoon"}],
            }],
        )

    assert rejected.value.status_code == 409
    assert rejected.value.reason_code == "DRAFT_PROTECTED_ACTIVITY_REQUIRES_USER_CHOICE"
    conflict = rejected.value.error_details["conflicts"][0]
    assert conflict["kind"] == "BOOKING_OMITTED"
    assert conflict["date"] == "2026-11-01"
    assert conflict["time_of_day"] == "morning"
    assert conflict["protected_markers"]["reservation_id"] == "TEST_FIXTURE-reservation-49"
    assert conflict["choice_required"] is True
    session.expire_all()
    assert session.get(JourneyMission, created["task_id"]).intent_json == before_json


def test_signed_user_full_save_moving_booking_returns_named_choice_with_requested_block(user_draft_scope):
    session, journey, member, created = user_draft_scope
    original = _booking_draft()
    before_json = _persist_draft(session, created["task_id"], original)

    with pytest.raises(HTTPException) as rejected:
        update_goal_draft(
            session,
            journey,
            member,
            created["task_id"],
            expected_revision=4,
            days=[{
                "date": "2026-11-01",
                "slots": [{
                    "title": "TEST_FIXTURE 已确认预约",
                    "time_of_day": "afternoon",
                    "reservation_id": "TEST_FIXTURE-reservation-49",
                }],
            }],
        )

    assert rejected.value.status_code == 409
    assert rejected.value.reason_code == "DRAFT_PROTECTED_ACTIVITY_REQUIRES_USER_CHOICE"
    conflict = rejected.value.error_details["conflicts"][0]
    assert conflict["kind"] == "BOOKING_MOVED"
    assert conflict["date"] == "2026-11-01"
    assert conflict["time_of_day"] == "morning"
    assert conflict["requested"] == {"date": "2026-11-01", "time_of_day": "afternoon"}
    session.expire_all()
    assert session.get(JourneyMission, created["task_id"]).intent_json == before_json


def test_signed_user_full_save_cannot_forge_new_booking_or_lock_markers(user_draft_scope):
    session, journey, member, created = user_draft_scope
    original = {
        "revision": 2,
        "status": "DRAFT",
        "date_constraints": {"2026-11-01": {"morning": {"start_not_before": "10:00"}}},
        "days": [{"date": "2026-11-01", "slots": []}],
    }
    _persist_draft(session, created["task_id"], original)

    result = update_goal_draft(
        session,
        journey,
        member,
        created["task_id"],
        expected_revision=2,
        days=[{
            "date": "2026-11-01",
            "slots": [{
                "title": "TEST_FIXTURE 用户自由活动",
                "time_of_day": "morning",
                "locked": True,
                "reservation_id": "TEST_FIXTURE-forged-booking",
                "metadata": {
                    "protected": True,
                    "booking_id": "TEST_FIXTURE-forged-booking-2",
                    "commitment_ids": ["TEST_FIXTURE-forged-commitment"],
                },
            }],
        }],
    )

    slot = result["draft_artifact"]["days"][0]["slots"][0]
    assert result["draft_artifact"]["date_constraints"] == original["date_constraints"]
    assert not (set(slot) & {"locked", "protected", "reservation_id", "booking_id", "commitment_ids"})
    assert "metadata" not in slot


def test_signed_user_full_save_keeps_marker_only_locked_slot_once_while_editing_free_slot(user_draft_scope):
    session, journey, member, created = user_draft_scope
    locked = {
        "title": "TEST_FIXTURE 锁定接驳",
        "time_of_day": "morning",
        "start_time": "10:30",
        "locked": True,
    }
    original = {
        "revision": 6,
        "status": "DRAFT",
        "days": [{
            "date": "2026-11-01",
            "slots": [
                deepcopy(locked),
                {"title": "TEST_FIXTURE 原自由活动", "time_of_day": "afternoon"},
            ],
        }],
    }
    _persist_draft(session, created["task_id"], original)

    result = update_goal_draft(
        session,
        journey,
        member,
        created["task_id"],
        expected_revision=6,
        days=[{
            "date": "2026-11-01",
            "slots": [
                deepcopy(locked),
                {"title": "TEST_FIXTURE 更新后的自由活动", "time_of_day": "afternoon"},
            ],
        }],
    )

    saved_slots = result["draft_artifact"]["days"][0]["slots"]
    locked_slots = [slot for slot in saved_slots if slot.get("locked") is True]
    assert locked_slots == [locked]
    assert len(saved_slots) == 2
    assert saved_slots[1]["title"] == "TEST_FIXTURE 更新后的自由活动"


def test_signed_user_full_save_keeps_revision_cas_before_reconciliation(user_draft_scope):
    session, journey, member, created = user_draft_scope
    original = _booking_draft()
    before_json = _persist_draft(session, created["task_id"], original)

    with pytest.raises(HTTPException) as rejected:
        update_goal_draft(
            session,
            journey,
            member,
            created["task_id"],
            expected_revision=3,
            days=[],
        )

    assert rejected.value.reason_code == "DRAFT_CHANGED_RELOAD"
    session.expire_all()
    assert session.get(JourneyMission, created["task_id"]).intent_json == before_json
