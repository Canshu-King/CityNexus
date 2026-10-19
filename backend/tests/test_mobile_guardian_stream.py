from __future__ import annotations

import json
from datetime import datetime, timezone
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.agent.guardian_stream import guardian_stream, guardian_stream_definition
from app.db.models import (
    Base,
    Event,
    GuardianPulse,
    GuardianRun,
    ImpactAssessment,
    Journey,
    JourneyMission,
    RecoveryEpoch,
    Traveler,
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@pytest.fixture
def isolated_guardian_store():
    engine = create_engine("sqlite://", future=True)
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        traveler = Traveler(
            id="traveler-guardian-stream",
            display_name="TEST_FIXTURE Guardian owner",
            email=None,
            locale="zh-CN",
            timezone="Asia/Shanghai",
            created_at=_now(),
            updated_at=_now(),
        )
        other_traveler = Traveler(
            id="traveler-other-stream",
            display_name="TEST_FIXTURE Other owner",
            email=None,
            locale="zh-CN",
            timezone="Asia/Shanghai",
            created_at=_now(),
            updated_at=_now(),
        )
        journey = Journey(
            id="journey-guardian-stream",
            traveler_id=traveler.id,
            title="TEST_FIXTURE Guardian stream",
            city_code="SHA",
            timezone="Asia/Shanghai",
            start_at="2026-11-01T09:00:00+08:00",
            end_at="2026-11-02T18:00:00+08:00",
            budget_currency="CNY",
            budget_amount_minor=10000,
            planning_mode="balanced",
            status="DRAFT",
            active_plan_version_id=None,
            current_activity_id=None,
            created_at=_now(),
            updated_at=_now(),
            deleted_at=None,
        )
        other_journey = Journey(
            id="journey-other-stream",
            traveler_id=other_traveler.id,
            title="TEST_FIXTURE Other journey",
            city_code="BJS",
            timezone="Asia/Shanghai",
            start_at="2026-11-01T09:00:00+08:00",
            end_at="2026-11-02T18:00:00+08:00",
            budget_currency="CNY",
            budget_amount_minor=10000,
            planning_mode="balanced",
            status="DRAFT",
            active_plan_version_id=None,
            current_activity_id=None,
            created_at=_now(),
            updated_at=_now(),
            deleted_at=None,
        )
        mission = JourneyMission(
            id="mission-guardian-stream",
            journey_id=journey.id,
            traveler_id=traveler.id,
            trigger_event_id=None,
            user_text="TEST_FIXTURE inspect Journey conditions",
            status="CREATED",
            created_at=_now(),
        )
        other_mission = JourneyMission(
            id="mission-other-stream",
            journey_id=other_journey.id,
            traveler_id=other_traveler.id,
            trigger_event_id=None,
            user_text="TEST_FIXTURE another Journey",
            status="CREATED",
            created_at=_now(),
        )
        session.add_all([traveler, other_traveler, journey, other_journey, mission, other_mission])
        session.commit()
        yield session, journey, other_journey, mission, other_mission
    engine.dispose()


def _event(journey_id: str, event_id: str, *, detected_at: str, status: str = "DETECTED", payload: str = "{}") -> Event:
    return Event(
        id=event_id,
        journey_id=journey_id,
        provider_key="fixture-provider",
        provenance="TEST_FIXTURE",
        event_type="WEATHER_ALERT",
        severity="MAJOR",
        status=status,
        affected_activity_id=None,
        occurred_at=detected_at,
        detected_at=detected_at,
        resolved_at=None,
        payload_json=payload,
        created_at=detected_at,
    )


def test_empty_stream_reports_no_observation_and_has_no_side_effects(isolated_guardian_store):
    session, journey, _other_journey, _mission, _other_mission = isolated_guardian_store
    before = session.query(Event).count()
    result = guardian_stream(session, journey)
    assert result["tool"] == "read_guardian_stream"
    assert result["status"] == "WATCH_NOT_RUNNING"
    assert result["watch"]["latest_pulse"] is None
    assert result["watch"]["last_observed_at"] is None
    assert result["recovery_epoch"] is None
    assert result["stream"] == []
    assert result["counts"] == {"events": 0, "open_events": 0, "impacts": 0, "actions": 0}
    assert session.query(Event).count() == before


def test_projects_bounded_events_impacts_actions_pulse_and_open_epoch(isolated_guardian_store):
    session, journey, other_journey, mission, _other_mission = isolated_guardian_store
    old_at = "2026-11-01T10:00:00+08:00"
    latest_at = "2026-11-01T11:00:00+08:00"
    session.add_all([
        _event(journey.id, "event-old", detected_at=old_at, status="RESOLVED"),
        _event(
            journey.id,
            "event-latest",
            detected_at=latest_at,
            payload=json.dumps({"semantic_reason": "PRIVATE_SENTINEL", "model_text": "PRIVATE_SENTINEL"}),
        ),
        _event(other_journey.id, "event-other", detected_at=latest_at),
        GuardianPulse(
            id="pulse-latest",
            journey_id=journey.id,
            status="COMPLETED",
            provider_key="fixture-provider",
            observation_ids_json='["event-latest"]',
            guardian_run_id=None,
            result_json='{"private":"PRIVATE_SENTINEL"}',
            started_at=latest_at,
            completed_at=latest_at,
        ),
        GuardianPulse(
            id="pulse-other",
            journey_id=other_journey.id,
            status="FAILED",
            provider_key="fixture-provider",
            observation_ids_json="[]",
            guardian_run_id=None,
            result_json="{}",
            started_at=latest_at,
            completed_at=latest_at,
        ),
        RecoveryEpoch(
            id="epoch-open",
            journey_id=journey.id,
            generation=2,
            active_plan_version_id_at_open="plan-at-open",
            material_world_epoch_at_open=None,
            recovery_reality_fingerprint="fingerprint-current",
            triggering_event_ids_json='["event-latest"]',
            status="OPEN",
            opened_at=latest_at,
            closed_at=None,
            close_reason=None,
            superseded_by_recovery_epoch_id=None,
        ),
        RecoveryEpoch(
            id="epoch-other",
            journey_id=other_journey.id,
            generation=1,
            active_plan_version_id_at_open=None,
            material_world_epoch_at_open=None,
            recovery_reality_fingerprint="fingerprint-other",
            triggering_event_ids_json='["event-other"]',
            status="OPEN",
            opened_at=latest_at,
            closed_at=None,
            close_reason=None,
            superseded_by_recovery_epoch_id=None,
        ),
        ImpactAssessment(
            id="impact-latest",
            event_id="event-latest",
            journey_id=journey.id,
            provider_key="fixture-provider",
            model_key="fixture-model",
            status="NEEDS_REVIEW",
            maturity_stage="AI_ONLY",
            independent_evidence_count=1,
            uncertain=True,
            reason_codes_json='["OPENING_STATUS_UNKNOWN", "private model phrase"]',
            semantic_reason="PRIVATE_SENTINEL",
            created_at=latest_at,
        ),
        ImpactAssessment(
            id="impact-other",
            event_id="event-other",
            journey_id=other_journey.id,
            provider_key="fixture-provider",
            model_key="fixture-model",
            status="NEEDS_REVIEW",
            maturity_stage="AI_ONLY",
            independent_evidence_count=0,
            uncertain=False,
            reason_codes_json="[]",
            semantic_reason="PRIVATE_SENTINEL",
            created_at=latest_at,
        ),
        GuardianRun(
            id="action-latest",
            journey_id=journey.id,
            standing_mission_id=mission.id,
            trigger_event_id="event-latest",
            agent_run_id=None,
            proposal_id="proposal-latest",
            decision="PROPOSE_REPLAN",
            status="COMPLETED",
            action_status="PROPOSED",
            evidence_fingerprint="fingerprint-action",
            evidence_json='{"private":"PRIVATE_SENTINEL"}',
            reasoning_summary="PRIVATE_SENTINEL",
            active_plan_before_id="plan-before",
            active_plan_after_id="plan-after",
            trigger_kind="REACTIVE",
            resilience_snapshot_id=None,
            recovery_epoch_id="epoch-open",
            created_at=latest_at,
            completed_at=latest_at,
            cooldown_until=None,
        ),
        GuardianRun(
            id="action-other",
            journey_id=other_journey.id,
            standing_mission_id=None,
            trigger_event_id="event-other",
            agent_run_id=None,
            proposal_id="proposal-other",
            decision="PROPOSE_REPLAN",
            status="COMPLETED",
            action_status="PROPOSED",
            evidence_fingerprint="fingerprint-other-action",
            evidence_json="{}",
            reasoning_summary="PRIVATE_SENTINEL",
            active_plan_before_id=None,
            active_plan_after_id=None,
            trigger_kind="REACTIVE",
            resilience_snapshot_id=None,
            recovery_epoch_id="epoch-other",
            created_at=latest_at,
            completed_at=latest_at,
            cooldown_until=None,
        ),
    ])
    session.commit()

    result = guardian_stream(session, journey, mission_id=mission.id, limit=1)
    assert result["mission_id"] == mission.id
    assert result["status"] == "HAS_EVENTS"
    assert result["watch"]["latest_pulse"] == {
        "id": "pulse-latest",
        "status": "COMPLETED",
        "started_at": latest_at,
        "completed_at": latest_at,
    }
    assert result["watch"]["last_observed_at"] == latest_at
    assert result["recovery_epoch"] == {
        "id": "epoch-open",
        "generation": 2,
        "status": "OPEN",
        "triggering_event_ids": ["event-latest"],
        "opened_at": latest_at,
        "active_plan_version_id_at_open": "plan-at-open",
    }
    assert result["counts"] == {"events": 1, "open_events": 1, "impacts": 1, "actions": 1}
    stream_item = result["stream"][0]
    assert stream_item["observation"]["id"] == "event-latest"
    assert stream_item["observation"]["event_type"] == "WEATHER_ALERT"
    assert stream_item["impact"] == {
        "id": "impact-latest",
        "status": "NEEDS_REVIEW",
        "uncertain": True,
        "reason_codes": ["OPENING_STATUS_UNKNOWN"],
        "created_at": latest_at,
    }
    assert stream_item["proposed_action"] == {
        "id": "action-latest",
        "decision": "PROPOSE_REPLAN",
        "status": "COMPLETED",
        "action_status": "PROPOSED",
        "proposal_id": "proposal-latest",
        "created_at": latest_at,
        "completed_at": latest_at,
    }
    assert "PRIVATE_SENTINEL" not in json.dumps(result)


def test_mission_must_belong_to_requested_journey(isolated_guardian_store):
    session, journey, _other_journey, _mission, other_mission = isolated_guardian_store
    with pytest.raises(HTTPException) as rejected:
        guardian_stream(session, journey, mission_id=other_mission.id)
    assert rejected.value.status_code == 404
    assert rejected.value.detail == "MISSION_NOT_FOUND"


def test_limit_is_clamped_and_schema_has_no_model_selected_scope():
    schema = guardian_stream_definition()["function"]
    assert schema["name"] == "read_guardian_stream"
    assert schema["parameters"] == {
        "type": "object",
        "properties": {},
        "required": [],
        "additionalProperties": False,
    }
