"""R33 deterministic distributed execution-lease contract tests.

These tests deliberately use independent durable rows rather than process
mutexes.  RecoveryEpoch and ExecutionLease are separate authority dimensions.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.agent.execution_lease import (
    ACTIVE,
    AGENT_EXECUTION_LEASE_SUPERSEDED,
    RELEASED,
    SUPERSEDED,
    ExecutionLeaseConflict,
    ExecutionLeaseSuperseded,
    acquire_execution_lease,
    current_execution_lease,
    release_execution_lease,
    renew_execution_lease,
    take_over_execution_lease,
    validate_execution_lease_binding,
)
from app.db.models import (
    AgentExecutionLease,
    AgentRun,
    Base,
    Journey,
    JourneyMission,
    RecoveryEpoch,
    Traveler,
)


BASE_TIME = datetime(2026, 10, 6, 6, 30, tzinfo=timezone.utc)


def _at(seconds: int = 0) -> datetime:
    return BASE_TIME + timedelta(seconds=seconds)


@pytest.fixture()
def lease_session():
    engine = create_engine("sqlite://", future=True)
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        traveler = Traveler(
            id=str(uuid4()),
            display_name="R33",
            email=None,
            locale="zh-CN",
            timezone="Asia/Tokyo",
            created_at=_at().isoformat(),
            updated_at=_at().isoformat(),
        )
        journey = Journey(
            id=str(uuid4()),
            traveler_id=traveler.id,
            title="R33 distributed lease",
            city_code="NRT",
            timezone="Asia/Tokyo",
            start_at="2026-10-08T09:00:00+09:00",
            end_at="2026-10-08T18:00:00+09:00",
            budget_currency="JPY",
            budget_amount_minor=100000,
            planning_mode="balanced",
            status="ACTIVE",
            active_plan_version_id=None,
            current_activity_id=None,
            created_at=_at().isoformat(),
            updated_at=_at().isoformat(),
            deleted_at=None,
        )
        mission = JourneyMission(
            id=str(uuid4()),
            journey_id=journey.id,
            traveler_id=traveler.id,
            trigger_event_id=None,
            user_text="Recover the Journey under durable execution ownership.",
            objective_codes_json="[]",
            protected_activity_ids_json="[]",
            mutable_activity_ids_json="[]",
            intent_json="{}",
            resolved_intent_json="{}",
            allowed_action_classes_json="[]",
            unresolved_references_json="[]",
            compiler_provider_key="deterministic",
            compiler_model_key="r33-fixture",
            compiler_confidence=1.0,
            reasoning_summary="",
            is_standing=False,
            parent_mission_id=None,
            max_cost_delta_minor=0,
            max_loss_minor=0,
            max_schedule_drift_min=0,
            preferences_json="{}",
            requested_autonomy="EXECUTE_WITHIN_BOUNDS",
            status="CREATED",
            created_at=_at().isoformat(),
            started_at=None,
            completed_at=None,
            failure_reason=None,
            clarification_json="{}",
        )
        epoch = RecoveryEpoch(
            id=str(uuid4()),
            journey_id=journey.id,
            generation=1,
            active_plan_version_id_at_open=None,
            material_world_epoch_at_open=None,
            recovery_reality_fingerprint="r33-world-1",
            triggering_event_ids_json="[]",
            status="OPEN",
            opened_at=_at().isoformat(),
            closed_at=None,
            close_reason=None,
            superseded_by_recovery_epoch_id=None,
        )
        db.add_all([traveler, journey, mission, epoch])
        db.commit()
        yield db, journey, mission, epoch


def _acquire(db, journey, mission, epoch, *, worker="worker-a", now=None):
    row = acquire_execution_lease(
        db,
        mission_id=mission.id,
        journey_id=journey.id,
        worker_id=worker,
        recovery_epoch_id=epoch.id,
        ttl_seconds=10,
        now=now or _at(),
    )
    db.commit()
    return row


def test_first_acquire_is_generation_one_and_server_current(lease_session):
    db, journey, mission, epoch = lease_session
    lease = _acquire(db, journey, mission, epoch)

    assert lease.generation == 1
    assert lease.status == ACTIVE
    assert lease.owner_worker_id == "worker-a"
    assert lease.recovery_epoch_id_at_acquire == epoch.id
    assert current_execution_lease(db, mission.id, now=_at(1)).id == lease.id


def test_renew_preserves_generation_and_extends_current_owner(lease_session):
    db, journey, mission, epoch = lease_session
    lease = _acquire(db, journey, mission, epoch)
    original_expiry = lease.expires_at

    renewed = renew_execution_lease(
        db,
        mission_id=mission.id,
        lease_id=lease.id,
        generation=lease.generation,
        worker_id="worker-a",
        ttl_seconds=30,
        now=_at(5),
    )
    db.commit()

    assert renewed.id == lease.id
    assert renewed.generation == 1
    assert renewed.expires_at > original_expiry
    rows = db.scalars(
        select(AgentExecutionLease).where(
            AgentExecutionLease.mission_id == mission.id
        )
    ).all()
    assert len(rows) == 1


def test_takeover_before_expiry_is_rejected(lease_session):
    db, journey, mission, epoch = lease_session
    lease = _acquire(db, journey, mission, epoch)

    with pytest.raises(ExecutionLeaseConflict) as error:
        take_over_execution_lease(
            db,
            mission_id=mission.id,
            journey_id=journey.id,
            worker_id="worker-b",
            recovery_epoch_id=epoch.id,
            ttl_seconds=10,
            now=_at(9),
        )

    assert error.value.lease.id == lease.id
    assert lease.status == ACTIVE


def test_expired_l1_takeover_creates_monotonic_l2(lease_session):
    db, journey, mission, epoch = lease_session
    l1 = _acquire(db, journey, mission, epoch)

    l2 = take_over_execution_lease(
        db,
        mission_id=mission.id,
        journey_id=journey.id,
        worker_id="worker-b",
        recovery_epoch_id=epoch.id,
        ttl_seconds=10,
        now=_at(11),
    )
    db.commit()

    db.refresh(l1)
    assert l1.status == SUPERSEDED
    assert l1.superseded_by_lease_id == l2.id
    assert l2.generation == 2
    assert l2.status == ACTIVE
    assert l2.owner_worker_id == "worker-b"
    assert current_execution_lease(db, mission.id, now=_at(12)).id == l2.id


def test_zombie_l1_validation_is_typed_and_does_not_mint_l3(lease_session):
    db, journey, mission, epoch = lease_session
    l1 = _acquire(db, journey, mission, epoch)
    l2 = take_over_execution_lease(
        db,
        mission_id=mission.id,
        journey_id=journey.id,
        worker_id="worker-b",
        recovery_epoch_id=epoch.id,
        ttl_seconds=30,
        now=_at(11),
    )
    db.commit()

    with pytest.raises(ExecutionLeaseSuperseded) as error:
        validate_execution_lease_binding(
            db,
            mission_id=mission.id,
            lease_id=l1.id,
            generation=1,
            worker_id="worker-a",
            now=_at(12),
        )

    assert error.value.facts["code"] == AGENT_EXECUTION_LEASE_SUPERSEDED
    assert error.value.facts["stale_execution_lease_id"] == l1.id
    assert error.value.facts["current_execution_lease_id"] == l2.id
    assert error.value.facts["current_execution_lease_generation"] == 2

    rows = db.scalars(
        select(AgentExecutionLease)
        .where(AgentExecutionLease.mission_id == mission.id)
        .order_by(AgentExecutionLease.generation)
    ).all()
    assert [row.generation for row in rows] == [1, 2]


def test_zombie_heartbeat_cannot_renew_after_takeover(lease_session):
    db, journey, mission, epoch = lease_session
    l1 = _acquire(db, journey, mission, epoch)
    l2 = take_over_execution_lease(
        db,
        mission_id=mission.id,
        journey_id=journey.id,
        worker_id="worker-b",
        recovery_epoch_id=epoch.id,
        ttl_seconds=30,
        now=_at(11),
    )
    db.commit()

    with pytest.raises(ExecutionLeaseSuperseded):
        renew_execution_lease(
            db,
            mission_id=mission.id,
            lease_id=l1.id,
            generation=1,
            worker_id="worker-a",
            ttl_seconds=30,
            now=_at(12),
        )

    assert current_execution_lease(db, mission.id, now=_at(12)).id == l2.id


def test_database_rejects_two_active_leases_for_one_mission(lease_session):
    db, journey, mission, epoch = lease_session
    l1 = _acquire(db, journey, mission, epoch)

    duplicate = AgentExecutionLease(
        id=str(uuid4()),
        mission_id=mission.id,
        journey_id=journey.id,
        generation=2,
        owner_worker_id="worker-b",
        recovery_epoch_id_at_acquire=epoch.id,
        status=ACTIVE,
        acquired_at=_at(1).isoformat(),
        heartbeat_at=_at(1).isoformat(),
        expires_at=_at(30).isoformat(),
        released_at=None,
        superseded_by_lease_id=None,
    )
    db.add(duplicate)
    with pytest.raises(IntegrityError):
        db.flush()
    db.rollback()

    current = current_execution_lease(db, mission.id, now=_at(2))
    assert current is not None
    assert current.id == l1.id


def test_release_is_nonspendable_and_next_generation_requires_takeover(
    lease_session,
):
    db, journey, mission, epoch = lease_session
    l1 = _acquire(db, journey, mission, epoch)

    released = release_execution_lease(
        db,
        mission_id=mission.id,
        lease_id=l1.id,
        generation=1,
        worker_id="worker-a",
        now=_at(2),
    )
    db.commit()

    assert released.status == RELEASED
    assert current_execution_lease(db, mission.id, now=_at(3)) is None
    with pytest.raises(ExecutionLeaseSuperseded):
        validate_execution_lease_binding(
            db,
            mission_id=mission.id,
            lease_id=l1.id,
            generation=1,
            worker_id="worker-a",
            now=_at(3),
        )

    l2 = take_over_execution_lease(
        db,
        mission_id=mission.id,
        journey_id=journey.id,
        worker_id="worker-b",
        recovery_epoch_id=epoch.id,
        ttl_seconds=20,
        now=_at(3),
    )
    db.commit()
    assert l2.generation == 2


def test_agent_run_can_bind_exact_lease_identity_without_retargeting(
    lease_session,
):
    db, journey, mission, epoch = lease_session
    lease = _acquire(db, journey, mission, epoch)

    run = AgentRun(
        id=str(uuid4()),
        mission_id=mission.id,
        journey_id=journey.id,
        provider_key="hermes",
        model_key="r33-fixture",
        status="RUNNING",
        outcome=None,
        failure_reason=None,
        created_at=_at(1).isoformat(),
        started_at=_at(1).isoformat(),
        completed_at=None,
        recovery_epoch_id=epoch.id,
        execution_lease_id=lease.id,
        execution_lease_generation=lease.generation,
        worker_id=lease.owner_worker_id,
    )
    db.add(run)
    db.commit()

    persisted = db.get(AgentRun, run.id)
    assert persisted is not None
    assert persisted.execution_lease_id == lease.id
    assert persisted.execution_lease_generation == 1
    assert persisted.worker_id == "worker-a"
