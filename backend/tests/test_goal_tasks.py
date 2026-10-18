"""DRAFT goal-task service tests using only an isolated in-memory fixture."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.agent import goal_tasks
from app.db.models import AgentRun, AuditLog, Base, Journey, JourneyMember, Traveler


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@pytest.fixture
def goal_scope():
    engine = create_engine("sqlite://", future=True)
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        traveler = Traveler(
            id=str(uuid4()),
            display_name="TEST_FIXTURE goal owner",
            email=None,
            locale="zh-CN",
            timezone="Asia/Shanghai",
            created_at=_now(),
            updated_at=_now(),
        )
        journey = Journey(
            id=str(uuid4()),
            traveler_id=traveler.id,
            title="TEST_FIXTURE DRAFT goal",
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
            created_at=_now(),
            updated_at=_now(),
            deleted_at=None,
        )
        member = JourneyMember(
            id=str(uuid4()),
            journey_id=journey.id,
            traveler_id=traveler.id,
            role="OWNER",
            invited_by=traveler.id,
            expires_at=None,
            joined_at=_now(),
            removed_at=None,
            preferences_json="{}",
            created_at=_now(),
            updated_at=_now(),
        )
        session.add_all([traveler, journey, member])
        session.commit()
        yield session, journey, member
    engine.dispose()


def _create(session: Session, journey: Journey, member: JourneyMember, **overrides):
    fields = {
        "goal": "Find a relaxed rainy-day afternoon with indoor options",
        "model_consent": True,
        "online_research_consent": False,
        "max_model_turns": 3,
        "max_tool_calls": 4,
    }
    fields.update(overrides)
    return goal_tasks.create_goal_task(session, journey, member, **fields)


def test_create_is_a_draft_mission_without_provider_run(goal_scope, monkeypatch):
    session, journey, member = goal_scope
    monkeypatch.setattr(
        goal_tasks,
        "_new_goal_agent",
        lambda *_args, **_kwargs: pytest.fail("create must not construct or call a provider"),
    )

    created = _create(session, journey, member)

    mission = session.get(goal_tasks.JourneyMission, created["task_id"])
    intent = json.loads(mission.intent_json)
    assert created["status"] == "ACCEPTED"
    assert intent["mode"] == "GOAL_PLANNING"
    assert mission.trigger_event_id is None
    assert mission.requested_autonomy == "PLAN_ONLY"
    assert session.scalar(select(AgentRun).where(AgentRun.mission_id == mission.id)) is None
    assert session.scalar(select(AuditLog).where(AuditLog.action == "agent.goal_task.event")) is not None


def test_missing_model_consent_pauses_without_constructing_runtime(goal_scope, monkeypatch):
    session, journey, member = goal_scope
    created = _create(session, journey, member, model_consent=False)
    monkeypatch.setattr(
        goal_tasks,
        "_new_goal_agent",
        lambda *_args, **_kwargs: pytest.fail("model consent is required before runtime creation"),
    )

    resumed = goal_tasks.resume_goal_task(session, journey, member, created["task_id"])

    assert resumed["status"] == "NEEDS_DECISION"
    assert resumed["failure_code"] == "MODEL_CONSENT_REQUIRED"
    assert session.scalar(select(AgentRun).where(AgentRun.mission_id == created["task_id"])) is None


def test_events_have_stable_fields_and_never_copy_goal_text(goal_scope):
    session, journey, member = goal_scope
    created = _create(
        session,
        journey,
        member,
        goal="Keep PRIVATE_GOAL_SENTINEL out of audit events",
    )

    events = goal_tasks.list_goal_task_events(session, journey, member, created["task_id"])

    assert len(events["events"]) == 1
    event = events["events"][0]
    assert event["event_type"] == "TASK_ACCEPTED"
    assert set(event) == {
        "sequence",
        "event_type",
        "status",
        "run_id",
        "step_sequence_no",
        "model_turn_no",
        "tool_name",
        "reason_code",
        "consent",
        "budget",
    }
    audit = session.scalar(select(AuditLog).where(AuditLog.entity_id == created["task_id"]))
    assert "PRIVATE_GOAL_SENTINEL" not in (audit.after_json or "")


def test_cancel_is_owner_bound_and_makes_task_terminal(goal_scope):
    session, journey, member = goal_scope
    created = _create(session, journey, member)

    cancelled = goal_tasks.cancel_goal_task(session, journey, member, created["task_id"])
    repeated = goal_tasks.cancel_goal_task(session, journey, member, created["task_id"])

    assert cancelled["status"] == "CANCELLED"
    assert repeated["status"] == "CANCELLED"
    with pytest.raises(HTTPException) as error:
        goal_tasks.resume_goal_task(session, journey, member, created["task_id"])
    assert error.value.status_code == 409


def test_create_rechecks_draft_status(goal_scope):
    session, journey, member = goal_scope
    journey.status = "ACTIVE"
    session.commit()

    with pytest.raises(HTTPException) as error:
        _create(session, journey, member)

    assert error.value.status_code == 409


def test_create_rejects_member_who_is_not_journey_owner(goal_scope):
    session, journey, member = goal_scope
    outsider = Traveler(
        id=str(uuid4()),
        display_name="TEST_FIXTURE non-owner",
        email=None,
        locale="zh-CN",
        timezone="Asia/Shanghai",
        created_at=_now(),
        updated_at=_now(),
    )
    outsider_member = JourneyMember(
        id=str(uuid4()),
        journey_id=journey.id,
        traveler_id=outsider.id,
        role="COLLABORATOR",
        invited_by=member.traveler_id,
        expires_at=None,
        joined_at=_now(),
        removed_at=None,
        preferences_json="{}",
        created_at=_now(),
        updated_at=_now(),
    )
    session.add_all([outsider, outsider_member])
    session.commit()

    with pytest.raises(HTTPException) as error:
        _create(session, journey, outsider_member)

    assert error.value.status_code == 403
