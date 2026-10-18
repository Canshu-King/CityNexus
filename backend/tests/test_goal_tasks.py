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


def test_domain_adapters_scope_and_model_tool_supply(goal_scope):
    from app.agent.goal_adapters import DOMAIN_TOOLS, domain_args, route_tool_definition
    from app.agent.runtime import citynexus_tool_definitions
    names = {item["function"]["name"] for item in [*citynexus_tool_definitions(), route_tool_definition()]}
    assert DOMAIN_TOOLS <= names
    assert (DOMAIN_TOOLS - {"generate_plans"}) <= goal_tasks._ALLOWED_TOOLS
    assert "generate_plans" not in goal_tasks._ALLOWED_TOOLS
    task = {"candidate_place_ids": ["a", "b"], "source_observation_ids": ["obs"]}
    for name in ("estimate_place_facts", "acquire_place_facts"):
        assert domain_args(name, {"place_id": "a"}, task) == {"place_id": "a"}
        with pytest.raises(HTTPException) as rejected:
            domain_args(name, {"place_id": "other-journey"}, task)
        assert rejected.value.status_code == 403
    assert domain_args("generate_plans", {"place_ids": ["a", "b"]}, task)["place_ids"] == ["a", "b"]
    with pytest.raises(HTTPException):
        domain_args("generate_plans", {"place_ids": ["a", "other-journey"]}, task)
    with pytest.raises(HTTPException):
        domain_args("acquire_place_facts", {"place_id": "a", "source_observation_id": "other"}, task)
    with pytest.raises(HTTPException):
        domain_args("acquire_place_facts", {"place_id": "a", "source_url": "https://invented.example"}, task)


def test_qoder_stored_route_projection_is_journey_bound(goal_scope):
    from app.agent.goal_adapters import compare_stored_routes
    from app.db.models import MobilityFact
    session, journey, _member = goal_scope
    assert compare_stored_routes(session, journey, from_key="a", to_key="b")["status"] == "NO_STORED_ROUTE_FACTS"
    session.add(MobilityFact(id=str(uuid4()), journey_id=journey.id, from_key="a", to_key="b",
        mode="WALK", duration_min=20, distance_m=900, cost_amount_minor=None, currency=None,
        cost_status="UNKNOWN", walking_min=20, transfers=0, weather_exposure="OUTDOOR",
        reliability_score=0.8, provider_key="TEST_FIXTURE", provenance="TEST_PROVIDER", captured_at=_now()))
    session.commit()
    result = compare_stored_routes(session, journey, from_key="a", to_key="b")
    assert result["status"] == "STORED_FACTS"
    assert result["acquisition_attempted"] is False
    assert result["options"][0]["cost_amount_minor"] is None
    assert result["options"][0]["cost_status"] == "UNKNOWN"
    assert compare_stored_routes(session, journey, from_key="b", to_key="a")["options"] == []


def test_goal_plan_projection_omits_collective_member_fields():
    result = goal_tasks._safe_tool_result("generate_plans", {"candidate_count": 1, "collective_mediation": {"members": ["PRIVATE"]},
        "plans": [{"id": "candidate", "status": "CANDIDATE", "selectable": False,
                   "unresolved_facts": ["OPENING_UNKNOWN"], "collective_member_fits": {"PRIVATE": "profile"}}]})
    assert "PRIVATE" not in json.dumps(result)
    assert result["activation_attempted"] is False
    assert result["plans"][0]["unresolved_facts"] == ["OPENING_UNKNOWN"]


def test_goal_runtime_dispatches_existing_domain_tools_without_activation(goal_scope, monkeypatch):
    session, journey, member = goal_scope
    created = _create(session, journey, member, online_research_consent=True, max_model_turns=6, max_tool_calls=8)
    mission = session.get(goal_tasks.JourneyMission, created["task_id"])
    intent = json.loads(mission.intent_json)
    intent["goal_task"]["candidate_place_ids"] = ["a", "b"]
    mission.intent_json = json.dumps(intent)
    session.commit()
    calls = []
    class Gateway:
        def __init__(self, *_args, **_kwargs): pass
        def dispatch(self, name, request):
            assert str(request.journey_id) == journey.id
            assert str(request.mission_id) == mission.id
            calls.append(name)
            return {"tool": name, "estimate": {"place_id": "a"}, "receipt": {"status": "TEST_FIXTURE"},
                    "candidate_count": 0, "plans": []}
    class Agent:
        provider_key = model_key = "TEST_FIXTURE"
        turn = 0
        def _complete(self, _messages):
            self.turn += 1
            entries = [("acquire_place_facts", {"place_id": "a"}), ("estimate_place_facts", {"place_id": "a"}),
                ("compare_routes", {"from_key": "a", "to_key": "b"}),
                ("save_draft_itinerary", {"days": [{"date": "2026-11-01", "slots": [{"title": "TEST_FIXTURE待查交通", "time_of_day": "afternoon"}]}]})]
            if self.turn > len(entries): return {"content": "TEST_FIXTURE阶段成果"}
            name, args = entries[self.turn - 1]
            return {"tool_calls": [{"id": f"fixture-{self.turn}", "function": {"name": name, "arguments": json.dumps(args)}}]}
    monkeypatch.setattr(goal_tasks, "AgentToolGateway", Gateway)
    monkeypatch.setattr(goal_tasks, "_new_goal_agent", lambda *_: Agent())
    result = goal_tasks.resume_goal_task(session, journey, member, created["task_id"])
    assert calls == ["acquire_place_facts", "estimate_place_facts"]
    restored = goal_tasks.read_goal_task(session, journey, member, created["task_id"])
    assert len(restored["tool_steps"]) == 4
    assert restored["tool_steps"][2]["result"]["status"] == "NO_STORED_ROUTE_FACTS"
    assert session.get(Journey, journey.id).status == "DRAFT"
    assert session.get(Journey, journey.id).active_plan_version_id is None


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


def test_model_sees_zero_result_then_saves_a_durable_editable_draft(goal_scope, monkeypatch):
    """Scripted model/tool fixtures verify the loop and persistence, not live autonomy."""
    session, journey, member = goal_scope
    created = _create(session, journey, member, online_research_consent=True, max_model_turns=4)
    class FixtureAgent:
        provider_key = "TEST_FIXTURE"
        model_key = "TEST_FIXTURE"
        turn = 0
        def _complete(self, messages):
            self.turn += 1
            if self.turn == 2:
                assert json.loads(messages[-1]["content"])["status"] == "NO_RESULTS"
            if self.turn in {1, 2}:
                name, args = "discover_places", {"query": f"TEST_FIXTURE keyword {self.turn}"}
            elif self.turn == 3:
                name, args = "save_draft_itinerary", {"days": [{"date":"2026-11-01", "slots":[{
                    "title":"TEST_FIXTURE 午后文化行程", "time_of_day":"afternoon", "place_id":"photon:node/123", "notes":"营业待查"}]}]}
            else:
                assert self._tool_allowlist == frozenset({"save_draft_itinerary"})
                return {"content":"TEST_FIXTURE 阶段安排已保存"}
            return {"tool_calls":[{"id":f"fixture-{self.turn}", "function":{"name":name,"arguments":json.dumps(args)}}]}
    def fixture_discovery(_session, _journey, task, **args):
        if args["query"].endswith("1"):
            return {"tool":"discover_places", "status":"NO_RESULTS", "places":[], "http_status":200}
        place = {"id":"photon:node/123", "name":"TEST_FIXTURE 文化地点", "source_url":"https://www.openstreetmap.org/node/123"}
        task["research_places"] = [place]
        return {"tool":"discover_places", "status":"RESULTS", "places":[place], "http_status":200}
    monkeypatch.setattr(goal_tasks, "_new_goal_agent", lambda *_: FixtureAgent())
    monkeypatch.setattr(goal_tasks, "discover_goal_places", fixture_discovery)
    result = goal_tasks.resume_goal_task(session, journey, member, created["task_id"])
    assert result["status"] == "PARTIAL_READY"
    session.expire_all()
    restored = goal_tasks.read_goal_task(session, journey, member, created["task_id"])
    assert len(restored["tool_steps"]) == 3
    assert restored["tool_steps"][0]["result"]["place_count"] == 0
    assert restored["draft_artifact"]["days"][0]["slots"][0]["place_id"] == "photon:node/123"
    assert restored["assistant_summary"] == "TEST_FIXTURE 阶段安排已保存"


def test_research_budget_can_be_extended_without_starting_a_provider(goal_scope):
    """The old 8/16 hard ceiling was a demo limit, not a service capability."""
    session, journey, member = goal_scope
    created = _create(session, journey, member, max_model_turns=32, max_tool_calls=64,
                      model_consent=False)
    assert created["budget"] == {"max_model_turns": 32, "max_tool_calls": 64}
    assert created["status"] == "NEEDS_DECISION"
    assert goal_tasks._safe_args("discover_places",
        {"query": "TEST_FIXTURE", "source": "nominatim"}, {})["source"] == "nominatim"
    with pytest.raises(HTTPException) as unsupported:
        goal_tasks._safe_args("discover_places",
            {"query": "TEST_FIXTURE", "source": "invented-provider"}, {})
    assert unsupported.value.status_code == 422
    with pytest.raises(HTTPException) as over_limit:
        _create(session, journey, member, max_model_turns=257)
    assert over_limit.value.status_code == 422



def test_followup_reuses_same_goal_task_and_model_reads_latest_user_message(goal_scope, monkeypatch):
    """A second chat turn continues the persisted Mission; it does not create a new one."""
    session, journey, member = goal_scope
    created = _create(session, journey, member, max_model_turns=8, max_tool_calls=8)
    calls = []

    class ReplyAgent:
        provider_key = model_key = "TEST_FIXTURE"
        _owns_client = False

        def _complete(self, messages):
            context = json.loads(messages[1]["content"])
            calls.append(context)
            assert context["goal"] == created["goal"]
            if len(calls) == 2:
                assert context["recent_user_instructions"][-1] == "把第二天下午改成轻松的自然景点"
            return {"content": "TEST_FIXTURE 第一次摘要" if len(calls) == 1 else "TEST_FIXTURE 已接收新的偏好"}

    monkeypatch.setattr(goal_tasks, "_new_goal_agent", lambda *_: ReplyAgent())
    first = goal_tasks.resume_goal_task(session, journey, member, created["task_id"])
    assert first["status"] == "PARTIAL_READY"
    assert first["task_id"] == created["task_id"]
    first_revision = first["draft_artifact"]["revision"]

    message_id = str(uuid4())
    second = goal_tasks.resume_goal_task(
        session, journey, member, created["task_id"],
        user_message="把第二天下午改成轻松的自然景点",
        message_id=message_id,
    )
    assert second["task_id"] == created["task_id"]
    assert second["draft_artifact"]["revision"] == first_revision
    assert [item["role"] for item in second["conversation"]] == ["user", "assistant", "user", "assistant"]
    assert second["conversation"][-2]["text"] == "把第二天下午改成轻松的自然景点"
    assert second["conversation"][-1]["text"] == "TEST_FIXTURE 已接收新的偏好"
    assert len(calls) == 2

    # Duplicate network delivery of the same message ID never starts a third model run.
    retried = goal_tasks.resume_goal_task(
        session, journey, member, created["task_id"],
        user_message="把第二天下午改成轻松的自然景点",
        message_id=message_id,
    )
    assert retried["task_id"] == created["task_id"]
    assert len(retried["conversation"]) == 4
    assert len(calls) == 2
    owner_events = goal_tasks.list_goal_task_events(session, journey, member, created["task_id"])
    assert sum(event["event_type"] == "USER_MESSAGE_ADDED" for event in owner_events["events"]) == 1
    assert "把第二天下午" not in json.dumps(owner_events, ensure_ascii=False)
    assert session.query(goal_tasks.JourneyMission).filter_by(journey_id=journey.id).count() == 1


def test_followup_must_be_owner_message_with_unique_uuid_and_not_after_cancel(goal_scope):
    session, journey, member = goal_scope
    created = _create(session, journey, member, model_consent=False)
    for message, message_id in [("", str(uuid4())), ("  ", str(uuid4())), ("a" * 2001, str(uuid4())),
                                ("continue", None), ("continue", "not-a-uuid")]:
        with pytest.raises(HTTPException) as error:
            goal_tasks.resume_goal_task(session, journey, member, created["task_id"],
                                        user_message=message, message_id=message_id)
        assert error.value.status_code == 422
    cancelled = goal_tasks.cancel_goal_task(session, journey, member, created["task_id"])
    assert cancelled["status"] == "CANCELLED"
    with pytest.raises(HTTPException) as error:
        goal_tasks.resume_goal_task(session, journey, member, created["task_id"],
                                    user_message="continue", message_id=str(uuid4()))
    assert error.value.status_code == 409
