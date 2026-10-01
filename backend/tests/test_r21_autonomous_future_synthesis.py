from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import uuid4

from app.agent.ai_availability import ai_availability_state
from app.agent.mission_plan import build_mission_plan
from app.agent.predictive import _material_difference_fingerprint
from app.agent.runtime import _system_prompt, reconcile_stale_agent_runs
from app.core.config import settings as runtime_settings
from app.db.models import AgentRun, Journey, JourneyMission, Traveler
from app.db.session import SessionLocal


def test_r21_recovery_envelope_is_capability_neutral():
    plan = build_mission_plan(autonomy="EXECUTE_WITHIN_BOUNDS").as_dict()
    assert [step["id"] for step in plan["steps"][:4]] == [
        "inspect_journey",
        "inspect_twin",
        "inspect_commitments",
        "evaluate_recovery_options",
    ]
    assert all(
        step["tool_name"] not in {"activate_standby", "request_replan"}
        for step in plan["steps"]
    )
    assert "activate_standby" in plan["allowed_tools"]
    assert "request_replan" in plan["allowed_tools"]


def test_r21_material_fingerprint_prunes_only_execution_equivalents():
    base = [
        {
            "place_id": "p1",
            "activity_type": "VISIT",
            "start_at": "2026-10-02T09:00:00+00:00",
            "end_at": "2026-10-02T10:00:00+00:00",
        },
        {
            "place_id": "p2",
            "activity_type": "VISIT",
            "start_at": "2026-10-02T10:30:00+00:00",
            "end_at": "2026-10-02T11:30:00+00:00",
        },
    ]
    same = [dict(item) for item in base]
    retimed = [dict(item) for item in base]
    retimed[1]["start_at"] = "2026-10-02T11:00:00+00:00"
    assert _material_difference_fingerprint(base) == _material_difference_fingerprint(same)
    assert _material_difference_fingerprint(base) != _material_difference_fingerprint(retimed)


def test_r21_stale_running_rows_reconcile_with_named_reason():
    now = datetime.now(timezone.utc)
    old = (now - timedelta(hours=1)).isoformat()
    traveler_id, journey_id, mission_id, run_id = (str(uuid4()) for _ in range(4))
    with SessionLocal() as session:
        session.add(
            Traveler(
                id=traveler_id,
                display_name="R21 stale-run test",
                email=None,
                locale="zh-CN",
                timezone="Asia/Shanghai",
                created_at=old,
                updated_at=old,
            )
        )
        session.flush()
        session.add(
            Journey(
                id=journey_id,
                traveler_id=traveler_id,
                title="R21 stale-run test",
                city_code="R21-TEST",
                timezone="Asia/Shanghai",
                start_at=old,
                end_at=(now + timedelta(days=1)).isoformat(),
                budget_currency="CNY",
                budget_amount_minor=100000,
                planning_mode="balanced",
                status="ACTIVE",
                active_plan_version_id=None,
                current_activity_id=None,
                created_at=old,
                updated_at=old,
            )
        )
        session.flush()
        session.add(
            JourneyMission(
                id=mission_id,
                journey_id=journey_id,
                traveler_id=traveler_id,
                user_text="R21 stale-run test",
                status="RUNNING",
                requested_autonomy="EXECUTE_WITHIN_BOUNDS",
                created_at=old,
                started_at=old,
            )
        )
        session.flush()
        session.add(
            AgentRun(
                id=run_id,
                mission_id=mission_id,
                journey_id=journey_id,
                provider_key="HERMES_COMPAT_ENDPOINT",
                model_key="cn:glm-5.3-flash",
                status="RUNNING",
                created_at=old,
                started_at=old,
            )
        )
        session.commit()
        assert reconcile_stale_agent_runs(session, timeout_seconds=60, now=now) == {
            "agent_runs_interrupted": 1,
            "missions_aborted": 1,
        }
        run = session.get(AgentRun, run_id)
        mission = session.get(JourneyMission, mission_id)
        assert run.status == "INTERRUPTED"
        assert mission.status == "ABORTED"
        assert run.failure_reason == "PROCESS_RESTARTED_DURING_AGENT_RUN"
        session.delete(run)
        session.delete(mission)
        session.delete(session.get(Journey, journey_id))
        session.delete(session.get(Traveler, traveler_id))
        session.commit()


def test_r21_hermes_compat_is_not_reported_as_ops_disabled(monkeypatch):
    monkeypatch.setattr(
        "app.agent.ai_availability.settings",
        replace(
            runtime_settings,
            ai_enabled=False,
            ai_api_key=None,
            hermes_api_url="http://127.0.0.1:7863/v1/chat/completions",
            hermes_api_key="process-only-test-key",
        ),
    )
    assert ai_availability_state() == "CONFIGURED_UNVERIFIED"


def test_r21_model_context_does_not_leak_trigger_identity_or_strategy_hint(monkeypatch):
    mission = SimpleNamespace(
        id="mission-r21-neutral",
        trigger_event_id="event-secret-to-model-context",
        requested_autonomy="EXECUTE_WITHIN_BOUNDS",
    )
    journey = SimpleNamespace(id="journey-r21-neutral", traveler_id="traveler-r21-neutral")
    monkeypatch.setattr("app.agent.runtime.refresh_snapshot", lambda session, traveler_id: {})
    monkeypatch.setattr("app.agent.runtime.snapshot_payload", lambda snapshot: {})
    monkeypatch.setattr(
        "app.agent.runtime.mission_payload",
        lambda value: {"id": value.id, "requested_autonomy": value.requested_autonomy},
    )

    prompt = _system_prompt(None, mission, journey)

    assert "event-secret-to-model-context" not in prompt
    assert "candidate_count to 3" not in prompt
    assert "solver_mode to deterministic" not in prompt
    assert "discoverable from the server-owned JourneyTwin" in prompt
