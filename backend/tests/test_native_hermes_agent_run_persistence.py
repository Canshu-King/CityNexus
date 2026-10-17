from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select

import app.main as main_module
from app.agent.runtime_events import normalize_hermes_event
from app.core.audit import record_audit
from app.core.config import settings
from app.db.models import AgentRun, AgentRunStep, Journey, JourneyMember, JourneyMission, Traveler
from app.db.session import SessionLocal
from app.traveler_principal import issue_traveler_token


def test_native_hermes_events_persist_safe_agent_steps_for_the_bound_mobile_member(monkeypatch):
    previous_secret = settings.traveler_auth_secret
    object.__setattr__(settings, "traveler_auth_secret", uuid4().hex + uuid4().hex)
    owner_id = str(uuid4())
    collaborator_id = str(uuid4())
    journey_id = str(uuid4())
    mission_id = str(uuid4())
    run_id = str(uuid4())
    owner_member_id = str(uuid4())
    now = datetime.now(timezone.utc)
    now_text = now.isoformat()

    class _ForbiddenNativeClient:
        def __init__(self):
            raise AssertionError("fixture persistence and timeline reads must not contact Hermes")

    try:
        with TestClient(main_module.app) as client:
            monkeypatch.setattr(main_module, "HermesNativeClient", _ForbiddenNativeClient)
            with SessionLocal() as session:
                session.add_all(
                    [
                        Traveler(
                            id=owner_id,
                            display_name="Hermes run owner fixture",
                            email=None,
                            locale="en-US",
                            timezone="UTC",
                            created_at=now_text,
                            updated_at=now_text,
                        ),
                        Traveler(
                            id=collaborator_id,
                            display_name="Hermes run collaborator fixture",
                            email=None,
                            locale="en-US",
                            timezone="UTC",
                            created_at=now_text,
                            updated_at=now_text,
                        ),
                    ]
                )
                session.flush()
                journey = Journey(
                    id=journey_id,
                    traveler_id=owner_id,
                    title="Native Hermes persistence fixture",
                    city_code="TST",
                    timezone="UTC",
                    start_at=now_text,
                    end_at=(now + timedelta(hours=6)).isoformat(),
                    budget_currency="USD",
                    budget_amount_minor=10000,
                    planning_mode="balanced",
                    status="DRAFT",
                    active_plan_version_id=None,
                    current_activity_id=None,
                    created_at=now_text,
                    updated_at=now_text,
                )
                owner_member = JourneyMember(
                    id=owner_member_id,
                    journey_id=journey_id,
                    traveler_id=owner_id,
                    role="OWNER",
                    invited_by=owner_id,
                    expires_at=None,
                    joined_at=now_text,
                    removed_at=None,
                    preferences_json="{}",
                    created_at=now_text,
                    updated_at=now_text,
                )
                collaborator_member = JourneyMember(
                    id=str(uuid4()),
                    journey_id=journey_id,
                    traveler_id=collaborator_id,
                    role="COLLABORATOR",
                    invited_by=owner_id,
                    expires_at=None,
                    joined_at=now_text,
                    removed_at=None,
                    preferences_json="{}",
                    created_at=now_text,
                    updated_at=now_text,
                )
                mission = JourneyMission(
                    id=mission_id,
                    journey_id=journey_id,
                    traveler_id=owner_id,
                    trigger_event_id=None,
                    user_text="Inspect the current Journey",
                    requested_autonomy="PLAN_ONLY",
                    status="RUNNING",
                    created_at=now_text,
                    started_at=now_text,
                    completed_at=None,
                )
                session.add_all([journey, owner_member, collaborator_member, mission])
                session.flush()
                main_module._persist_native_agent_run_start(
                    session,
                    run_id=run_id,
                    journey=journey,
                    mission=mission,
                    status="running",
                    model_key="fixture-model",
                )
                record_audit(
                    session,
                    action="agent.native_hermes.run_bound",
                    entity_type="HermesNativeRun",
                    entity_id=run_id,
                    journey_id=journey_id,
                    actor_type="TRAVELER",
                    actor_id=owner_id,
                    after={
                        "mission_id": mission_id,
                        "member_id": owner_member_id,
                        "traveler_id": owner_id,
                    },
                )
                session.commit()

            raw_events = [
                {"event_type": "run.started", "event_id": "run-start", "timestamp": now_text},
                {
                    "event_type": "tool.started",
                    "event_id": "tool-start",
                    "sequence": 4,
                    "tool_name": "inspect_journey",
                    "arguments": {"private_query": "never persist this value"},
                    "timestamp": now_text,
                },
                {
                    "event_type": "tool.completed",
                    "event_id": "tool-complete",
                    "sequence": 5,
                    "tool_name": "inspect_journey",
                    "arguments": {"access_token": "fixture-secret-do-not-store"},
                    "result": {
                        "decision": "ALLOW_AUTO",
                        "status": "completed",
                        "executed": True,
                        "proposal_id": "proposal-fixture-1",
                        "message": "private model prose must not persist",
                        "access_token": "fixture-secret-do-not-store",
                    },
                    "timestamp": now_text,
                },
                {"event_type": "run.completed", "event_id": "run-complete", "timestamp": now_text},
            ]
            for raw in raw_events:
                normalized = normalize_hermes_event(raw, run_id=run_id)
                assert normalized is not None
                main_module._persist_native_event(normalized, journey_id=journey_id)

            with SessionLocal() as session:
                persisted_run = session.get(AgentRun, run_id)
                assert persisted_run is not None
                assert persisted_run.status == "COMPLETED"
                assert persisted_run.provider_key == "hermes-native"
                steps = session.scalars(
                    select(AgentRunStep).where(AgentRunStep.run_id == run_id)
                ).all()
                assert len(steps) == 1
                assert steps[0].tool_name == "inspect_journey"
                assert json.loads(steps[0].arguments_json) == {}
                result = json.loads(steps[0].result_json)
                assert result == {
                    "status": "COMPLETED",
                    "summary": {
                        "decision": "ALLOW_AUTO",
                        "executed": True,
                        "status": "COMPLETED",
                    },
                }
                assert "fixture-secret-do-not-store" not in steps[0].result_json
                assert "private model prose" not in steps[0].result_json

            owner_headers = {"Authorization": f"Bearer {issue_traveler_token(owner_id)}"}
            collaborator_headers = {
                "Authorization": f"Bearer {issue_traveler_token(collaborator_id)}"
            }
            latest_path = f"/api/v1/journeys/{journey_id}/agent/hermes/latest-run"
            latest = client.get(latest_path, headers=owner_headers)
            assert latest.status_code == 200, latest.text
            assert latest.json()["run"]["run_id"] == run_id
            assert latest.json()["run"]["runtime_identity"] == "HERMES_NATIVE_MCP"

            timeline_path = f"/api/v1/journeys/{journey_id}/agent/hermes/runs/{run_id}/timeline"
            timeline = client.get(timeline_path, headers=owner_headers)
            assert timeline.status_code == 200, timeline.text
            assert [item["event_type"] for item in timeline.json()["events"]] == [
                "run.started",
                "tool.started",
                "tool.completed",
                "run.completed",
            ]
            assert timeline.json()["observability"]["tool_count"] == 1

            run_path = f"/api/v1/journeys/{journey_id}/agent/runs/{run_id}"
            owner_run = client.get(run_path, headers=owner_headers)
            assert owner_run.status_code == 200, owner_run.text
            assert owner_run.json()["runtime_identity"] == "HERMES_NATIVE_MCP"
            assert owner_run.json()["tool_steps"] == [
                {
                    "id": steps[0].id,
                    "sequence_no": 5,
                    "tool_name": "inspect_journey",
                    "arguments": {},
                    "result": result,
                    "decision": "ALLOW_AUTO",
                    "status": "COMPLETED",
                    "created_at": now_text,
                    "completed_at": now_text,
                }
            ]
            collaborator_run = client.get(run_path, headers=collaborator_headers)
            assert collaborator_run.status_code == 404

            pending_path = f"/api/v1/journeys/{journey_id}/missions/pending"
            owner_pending = client.get(pending_path, headers=owner_headers)
            assert owner_pending.status_code == 200, owner_pending.text
            assert owner_pending.json()["items"][0]["run"]["run_id"] == run_id
            assert owner_pending.json()["items"][0]["run"]["runtime_identity"] == "HERMES_NATIVE_MCP"
            collaborator_pending = client.get(pending_path, headers=collaborator_headers)
            assert collaborator_pending.status_code == 200, collaborator_pending.text
            assert collaborator_pending.json()["items"] == []
    finally:
        object.__setattr__(settings, "traveler_auth_secret", previous_secret)


def test_native_tool_step_replay_with_duplicate_sequence_is_idempotent():
    now = datetime.now(timezone.utc)
    now_text = now.isoformat()
    traveler_id = str(uuid4())
    journey_id = str(uuid4())
    mission_id = str(uuid4())
    run_id = str(uuid4())

    with TestClient(main_module.app):
        with SessionLocal() as session:
            session.add(
                Traveler(
                    id=traveler_id,
                    display_name="Native step replay fixture",
                    email=None,
                    locale="en-US",
                    timezone="UTC",
                    created_at=now_text,
                    updated_at=now_text,
                )
            )
            session.flush()
            journey = Journey(
                id=journey_id,
                traveler_id=traveler_id,
                title="Native step replay fixture",
                city_code="TST",
                timezone="UTC",
                start_at=now_text,
                end_at=(now + timedelta(hours=2)).isoformat(),
                budget_currency="USD",
                budget_amount_minor=0,
                planning_mode="balanced",
                status="DRAFT",
                active_plan_version_id=None,
                current_activity_id=None,
                created_at=now_text,
                updated_at=now_text,
            )
            session.add(journey)
            session.flush()
            mission = JourneyMission(
                id=mission_id,
                journey_id=journey_id,
                traveler_id=traveler_id,
                trigger_event_id=None,
                user_text="Fixture-only native event replay",
                requested_autonomy="PLAN_ONLY",
                status="RUNNING",
                created_at=now_text,
                started_at=now_text,
                completed_at=None,
            )
            session.add(mission)
            session.flush()
            main_module._persist_native_agent_run_start(
                session,
                run_id=run_id,
                journey=journey,
                mission=mission,
                status="running",
                model_key="fixture-model",
            )
            session.commit()

        raw_tool_event = {
            "event_type": "tool.completed",
            "event_id": "tool-event-first",
            "sequence": 9,
            "tool_name": "inspect_journey",
            "result": {"decision": "ALLOW_AUTO", "status": "completed"},
            "timestamp": now_text,
        }
        first = normalize_hermes_event(raw_tool_event, run_id=run_id)
        replay = normalize_hermes_event(
            {**raw_tool_event, "event_id": "tool-event-replayed"},
            run_id=run_id,
        )
        assert first is not None and replay is not None

        with SessionLocal() as session:
            main_module._persist_native_agent_event(session, first)
            session.commit()
            main_module._persist_native_agent_event(session, replay)
            session.commit()
            steps = session.scalars(
                select(AgentRunStep).where(AgentRunStep.run_id == run_id)
            ).all()
            assert len(steps) == 1
            assert steps[0].sequence_no == 9
            assert steps[0].tool_name == "inspect_journey"
