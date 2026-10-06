"""Deterministic R32 RecoveryEpoch contract tests.

These tests use only the local SQLAlchemy model and never call a provider or
external model.  The database unique index, rather than a process mutex, is
the concurrency arbiter for one OPEN epoch per Journey.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.models import Activity, Base, Event, Journey, PlanVersion, Traveler
from app.recovery_epoch import (
    OPEN,
    RECOVERY_EPOCH_SUPERSEDED,
    RecoveryEpochSuperseded,
    ensure_recovery_epoch,
    recovery_reality_basis,
    recovery_reality_fingerprint,
    semantic_plan_identity,
    validate_recovery_epoch_binding,
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@pytest.fixture()
def session():
    engine = create_engine("sqlite://", future=True)
    Base.metadata.create_all(engine)
    with Session(engine) as value:
        traveler = Traveler(
            id=str(uuid4()), display_name="R32", email=None, locale="zh-CN",
            timezone="Asia/Shanghai", created_at=_now(), updated_at=_now(),
        )
        journey = Journey(
            id=str(uuid4()), traveler_id=traveler.id, title="R32", city_code="KIX",
            timezone="Asia/Tokyo", start_at="2026-10-06T09:00:00+09:00",
            end_at="2026-10-07T18:00:00+09:00", budget_currency="JPY",
            budget_amount_minor=10000, planning_mode="balanced", status="ACTIVE",
            active_plan_version_id=None, current_activity_id=None,
            created_at=_now(), updated_at=_now(), deleted_at=None,
        )
        value.add_all([traveler, journey])
        value.commit()
        yield value, journey


def _event(journey: Journey, *, event_id: str, status: str = "DETECTED", payload=None) -> Event:
    return Event(
        id=event_id, journey_id=journey.id, provider_key="fixture",
        provenance="FIXTURE", event_type="CLOSURE", severity="MAJOR", status=status,
        affected_activity_id=None, occurred_at="2026-10-06T09:00:00+09:00",
        detected_at="2026-10-06T09:01:00+09:00", resolved_at=None,
        payload_json=json.dumps(payload or {}, sort_keys=True), created_at=_now(),
    )


def test_open_epoch_is_idempotent_for_same_reality(session):
    db, journey = session
    first = ensure_recovery_epoch(db, journey)
    db.commit()
    second = ensure_recovery_epoch(db, journey)
    assert first.id == second.id
    assert first.generation == second.generation == 1
    assert second.status == OPEN


def test_relevant_event_change_supersedes_and_opens_next_generation(session):
    db, journey = session
    first = ensure_recovery_epoch(db, journey)
    db.commit()
    db.add(_event(journey, event_id=str(uuid4()), payload={"incident_fingerprint": "A"}))
    db.commit()
    second = ensure_recovery_epoch(db, journey)
    assert second.id != first.id
    assert second.generation == 2
    assert second.status == OPEN
    assert first.status == "SUPERSEDED"
    assert first.superseded_by_recovery_epoch_id == second.id


def test_irrelevant_resolved_event_does_not_change_epoch(session):
    db, journey = session
    first = ensure_recovery_epoch(db, journey)
    db.add(_event(journey, event_id=str(uuid4()), status="RESOLVED"))
    db.commit()
    second = ensure_recovery_epoch(db, journey)
    assert second.id == first.id
    assert recovery_reality_fingerprint(recovery_reality_basis(db, journey)) == first.recovery_reality_fingerprint


def test_bound_agent_cannot_forge_or_switch_epoch(session):
    db, journey = session
    first = ensure_recovery_epoch(db, journey)
    db.add(_event(journey, event_id=str(uuid4()), payload={"incident_fingerprint": "B"}))
    db.commit()
    second = ensure_recovery_epoch(db, journey)
    with pytest.raises(RecoveryEpochSuperseded) as error:
        validate_recovery_epoch_binding(db, journey.id, first.id)
    assert error.value.facts["code"] == RECOVERY_EPOCH_SUPERSEDED
    assert error.value.facts["current_recovery_epoch_id"] == second.id


def test_semantic_plan_identity_excludes_plan_and_proposal_ids(session):
    db, journey = session
    p1 = PlanVersion(
        id=str(uuid4()), journey_id=journey.id, version_no=1, planning_mode="balanced",
        status="CANDIDATE", lifecycle="ACTIVE", trigger_contract_json="{}", source="R32",
        parent_plan_version_id=None, total_cost_minor=100, currency="JPY",
        estimated_duration_min=60, utility_score=1.0, score_breakdown_json="{}",
        explanation_json="{}", mobility_snapshot_id=None, mobility_evidence_json=None,
        created_at=_now(),
    )
    p2 = PlanVersion(
        id=str(uuid4()), journey_id=journey.id, version_no=2, planning_mode="balanced",
        status="CANDIDATE", lifecycle="ACTIVE", trigger_contract_json="{}", source="OTHER",
        parent_plan_version_id=None, total_cost_minor=100, currency="JPY",
        estimated_duration_min=60, utility_score=0.2, score_breakdown_json="{}",
        explanation_json="different model text", mobility_snapshot_id=None,
        mobility_evidence_json=None, created_at=_now(),
    )
    db.add_all([p1, p2])
    db.flush()
    for plan in (p1, p2):
        db.add(Activity(
            id=str(uuid4()), plan_version_id=plan.id, sequence_no=1,
            activity_type="PLACE", title="Same future", place_id=None, city_service_id=None,
            start_at="2026-10-06T10:00:00+09:00", end_at="2026-10-06T11:00:00+09:00",
            travel_from_prev_min=0, estimated_cost_minor=100, currency="JPY",
            status="PLANNED", locked=False, metadata_json="{}", created_at=_now(), updated_at=_now(),
        ))
    db.commit()
    assert semantic_plan_identity(db, p1.id) == semantic_plan_identity(db, p2.id)
