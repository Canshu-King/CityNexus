"""Durable execution-lease generation for distributed Journey Agents.

RecoveryEpoch fences *world* authority.  This module independently fences
*execution ownership*.  A process, PID or in-memory lock is never the authority
token; the persisted lease id + generation is.

Validation is deliberately causally inert: discovering a stale/expired lease
never creates a successor lease.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import AgentExecutionLease


ACTIVE = "ACTIVE"
EXPIRED = "EXPIRED"
SUPERSEDED = "SUPERSEDED"
RELEASED = "RELEASED"

AGENT_EXECUTION_LEASE_SUPERSEDED = "AGENT_EXECUTION_LEASE_SUPERSEDED"


def _clock(value: datetime | None = None) -> datetime:
    stamp = value or datetime.now(timezone.utc)
    if stamp.tzinfo is None:
        stamp = stamp.replace(tzinfo=timezone.utc)
    return stamp.astimezone(timezone.utc)


def _iso(value: datetime) -> str:
    return _clock(value).isoformat()


def _parse(value: str) -> datetime:
    stamp = datetime.fromisoformat(value)
    if stamp.tzinfo is None:
        stamp = stamp.replace(tzinfo=timezone.utc)
    return stamp.astimezone(timezone.utc)


def _ttl_deadline(now: datetime, ttl_seconds: float) -> str:
    ttl = float(ttl_seconds)
    if ttl <= 0:
        raise ValueError("execution lease ttl_seconds must be positive")
    return _iso(now + timedelta(seconds=ttl))


def latest_execution_lease(
    session: Session, mission_id: str
) -> AgentExecutionLease | None:
    return session.scalars(
        select(AgentExecutionLease)
        .where(AgentExecutionLease.mission_id == str(mission_id))
        .order_by(
            AgentExecutionLease.generation.desc(),
            AgentExecutionLease.id.desc(),
        )
        .limit(1)
    ).first()


def current_execution_lease(
    session: Session,
    mission_id: str,
    *,
    now: datetime | None = None,
) -> AgentExecutionLease | None:
    """Return the currently spendable lease without mutating durable state."""

    row = session.scalars(
        select(AgentExecutionLease)
        .where(
            AgentExecutionLease.mission_id == str(mission_id),
            AgentExecutionLease.status == ACTIVE,
        )
        .order_by(AgentExecutionLease.generation.desc())
        .limit(1)
    ).first()
    if row is None:
        return None
    if _parse(row.expires_at) <= _clock(now):
        return None
    return row


class ExecutionLeaseConflict(RuntimeError):
    """A new owner cannot be granted while another lease is spendable."""

    def __init__(self, lease: AgentExecutionLease, *, reason: str):
        self.lease = lease
        self.reason = reason
        super().__init__(
            f"execution lease generation {lease.generation} is still current: "
            f"{reason}"
        )


class ExecutionLeaseSuperseded(RuntimeError):
    """Typed rejection for stale/expired execution ownership."""

    def __init__(
        self,
        *,
        bound: AgentExecutionLease | None,
        current: AgentExecutionLease | None,
        reason: str,
    ):
        self.bound = bound
        self.current = current
        self.reason = reason
        self.facts: dict[str, Any] = {
            "code": AGENT_EXECUTION_LEASE_SUPERSEDED,
            "reason": reason,
            "stale_execution_lease_id": bound.id if bound else None,
            "stale_execution_lease_generation": (
                bound.generation if bound else None
            ),
            "stale_worker_id": bound.owner_worker_id if bound else None,
            "current_execution_lease_id": current.id if current else None,
            "current_execution_lease_generation": (
                current.generation if current else None
            ),
            "current_worker_id": (
                current.owner_worker_id if current else None
            ),
        }
        super().__init__(
            f"{AGENT_EXECUTION_LEASE_SUPERSEDED}: {reason}"
        )


def acquire_execution_lease(
    session: Session,
    *,
    mission_id: str,
    journey_id: str,
    worker_id: str,
    recovery_epoch_id: str | None,
    ttl_seconds: float = 30.0,
    now: datetime | None = None,
) -> AgentExecutionLease:
    """Acquire generation 1 for a mission with no prior lease lineage."""

    existing = latest_execution_lease(session, mission_id)
    if existing is not None:
        raise ExecutionLeaseConflict(
            existing,
            reason="LEASE_LINEAGE_ALREADY_EXISTS_USE_TAKEOVER",
        )
    stamp = _clock(now)
    row = AgentExecutionLease(
        id=str(uuid4()),
        mission_id=str(mission_id),
        journey_id=str(journey_id),
        generation=1,
        owner_worker_id=str(worker_id),
        recovery_epoch_id_at_acquire=(
            str(recovery_epoch_id) if recovery_epoch_id else None
        ),
        status=ACTIVE,
        acquired_at=_iso(stamp),
        heartbeat_at=_iso(stamp),
        expires_at=_ttl_deadline(stamp, ttl_seconds),
        released_at=None,
        superseded_by_lease_id=None,
    )
    session.add(row)
    session.flush()
    return row


def validate_execution_lease_binding(
    session: Session,
    *,
    mission_id: str,
    lease_id: str | None,
    generation: int | None,
    worker_id: str | None = None,
    now: datetime | None = None,
) -> AgentExecutionLease:
    """Validate exact current ownership without opening a successor lease."""

    bound = (
        session.get(AgentExecutionLease, str(lease_id))
        if lease_id
        else None
    )
    current = current_execution_lease(session, mission_id, now=now)

    if bound is None:
        raise ExecutionLeaseSuperseded(
            bound=None,
            current=current,
            reason="BOUND_EXECUTION_LEASE_MISSING",
        )

    if bound.mission_id != str(mission_id):
        raise ExecutionLeaseSuperseded(
            bound=bound,
            current=current,
            reason="BOUND_EXECUTION_LEASE_MISSION_MISMATCH",
        )

    if generation is None or bound.generation != int(generation):
        raise ExecutionLeaseSuperseded(
            bound=bound,
            current=current,
            reason="BOUND_EXECUTION_LEASE_GENERATION_MISMATCH",
        )

    if worker_id is not None and bound.owner_worker_id != str(worker_id):
        raise ExecutionLeaseSuperseded(
            bound=bound,
            current=current,
            reason="BOUND_EXECUTION_LEASE_WORKER_MISMATCH",
        )

    if bound.status != ACTIVE:
        raise ExecutionLeaseSuperseded(
            bound=bound,
            current=current,
            reason=f"BOUND_EXECUTION_LEASE_{bound.status}",
        )

    if _parse(bound.expires_at) <= _clock(now):
        raise ExecutionLeaseSuperseded(
            bound=bound,
            current=current,
            reason="BOUND_EXECUTION_LEASE_EXPIRED",
        )

    if current is None or current.id != bound.id:
        raise ExecutionLeaseSuperseded(
            bound=bound,
            current=current,
            reason="BOUND_EXECUTION_LEASE_NOT_CURRENT",
        )

    return bound


def renew_execution_lease(
    session: Session,
    *,
    mission_id: str,
    lease_id: str,
    generation: int,
    worker_id: str,
    ttl_seconds: float = 30.0,
    now: datetime | None = None,
) -> AgentExecutionLease:
    """Extend only the exact current generation; never creates a successor."""

    stamp = _clock(now)
    row = validate_execution_lease_binding(
        session,
        mission_id=mission_id,
        lease_id=lease_id,
        generation=generation,
        worker_id=worker_id,
        now=stamp,
    )
    row.heartbeat_at = _iso(stamp)
    row.expires_at = _ttl_deadline(stamp, ttl_seconds)
    session.flush()
    return row


def take_over_execution_lease(
    session: Session,
    *,
    mission_id: str,
    journey_id: str,
    worker_id: str,
    recovery_epoch_id: str | None,
    ttl_seconds: float = 30.0,
    now: datetime | None = None,
) -> AgentExecutionLease:
    """Atomically advance ownership after the previous generation is dead.

    The database's one-ACTIVE and mission/generation unique indexes are the
    final race arbiters across processes.  Callers must treat IntegrityError /
    serialization conflicts as a lost takeover race and rediscover current
    state; they must not blindly mint another generation.
    """

    stamp = _clock(now)
    previous = latest_execution_lease(session, mission_id)
    if previous is None:
        raise RuntimeError(
            "execution lease takeover requires an existing lease lineage"
        )

    live = current_execution_lease(session, mission_id, now=stamp)
    if live is not None:
        raise ExecutionLeaseConflict(
            live,
            reason="CURRENT_EXECUTION_LEASE_NOT_EXPIRED",
        )

    successor_id = str(uuid4())
    if previous.status == ACTIVE:
        # Expiry made it non-spendable before this transaction.  Takeover now
        # durably fences that generation.
        previous.status = SUPERSEDED
        previous.released_at = _iso(stamp)
        previous.superseded_by_lease_id = successor_id
    elif previous.status in {EXPIRED, RELEASED, SUPERSEDED}:
        previous.superseded_by_lease_id = (
            previous.superseded_by_lease_id or successor_id
        )
    else:  # defensive against future status expansion
        raise ExecutionLeaseConflict(
            previous,
            reason=f"UNSUPPORTED_PREDECESSOR_STATUS_{previous.status}",
        )

    row = AgentExecutionLease(
        id=successor_id,
        mission_id=str(mission_id),
        journey_id=str(journey_id),
        generation=int(previous.generation) + 1,
        owner_worker_id=str(worker_id),
        recovery_epoch_id_at_acquire=(
            str(recovery_epoch_id) if recovery_epoch_id else None
        ),
        status=ACTIVE,
        acquired_at=_iso(stamp),
        heartbeat_at=_iso(stamp),
        expires_at=_ttl_deadline(stamp, ttl_seconds),
        released_at=None,
        superseded_by_lease_id=None,
    )
    session.add(row)
    session.flush()
    return row


def release_execution_lease(
    session: Session,
    *,
    mission_id: str,
    lease_id: str,
    generation: int,
    worker_id: str,
    now: datetime | None = None,
) -> AgentExecutionLease:
    """Release only the exact current owner."""

    stamp = _clock(now)
    row = validate_execution_lease_binding(
        session,
        mission_id=mission_id,
        lease_id=lease_id,
        generation=generation,
        worker_id=worker_id,
        now=stamp,
    )
    row.status = RELEASED
    row.released_at = _iso(stamp)
    row.heartbeat_at = _iso(stamp)
    session.flush()
    return row
