"""Durable server-owned recovery reality epochs (R32).

The epoch is deliberately independent from the R31 E/W/S authority values.  It
binds a model run and every authority-bearing continuation to the Journey
reality that was current when the run started.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Mapping
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.models import Activity, Event, Journey, PlanVersion, RecoveryEpoch

OPEN = "OPEN"
SUPERSEDED = "SUPERSEDED"
COMMITTED = "COMMITTED"
ABANDONED = "ABANDONED"
RECOVERY_EPOCH_SUPERSEDED = "RECOVERY_EPOCH_SUPERSEDED"
_ACTIONABLE_EVENT_STATUSES = {"DETECTED", "ACKNOWLEDGED", "ACTIVE", "OPEN"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _payload_fingerprint(payload_json: str | None) -> str | None:
    try:
        payload = json.loads(payload_json or "{}")
    except (TypeError, ValueError):
        return None
    if not isinstance(payload, Mapping):
        return None
    for key in ("incident_fingerprint", "incidentFingerprint", "fingerprint"):
        value = payload.get(key)
        if value:
            return str(value)
    return None


def recovery_reality_basis(session: Session, journey: Journey) -> dict[str, Any]:
    """Return only decision-material, canonical Journey facts.

    Observation timestamps, raw payloads and model output are intentionally
    excluded.  Event ids remain in the basis so a new actionable fact changes
    the epoch while irrelevant observation churn does not.
    """

    rows = session.scalars(
        select(Event)
        .where(Event.journey_id == journey.id)
        .order_by(Event.id.asc())
    ).all()
    events: list[dict[str, Any]] = []
    for event in rows:
        if str(event.status or "").upper() not in _ACTIONABLE_EVENT_STATUSES:
            continue
        events.append(
            {
                "id": str(event.id),
                "provider_key": str(event.provider_key or ""),
                "provenance": str(event.provenance or ""),
                "event_type": str(event.event_type or ""),
                "severity": str(event.severity or ""),
                "status": str(event.status or ""),
                "affected_activity_id": str(event.affected_activity_id or ""),
                "incident_fingerprint": _payload_fingerprint(event.payload_json),
            }
        )
    return {
        "schema": "citynexus.recovery-reality.v1",
        "journey_id": str(journey.id),
        "active_plan_version_id": str(journey.active_plan_version_id or ""),
        "current_activity_id": str(journey.current_activity_id or ""),
        "events": events,
    }


def recovery_reality_fingerprint(basis: Mapping[str, Any]) -> str:
    encoded = json.dumps(dict(basis), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def current_open_recovery_epoch(session: Session, journey_id: str) -> RecoveryEpoch | None:
    return session.scalars(
        select(RecoveryEpoch)
        .where(RecoveryEpoch.journey_id == str(journey_id), RecoveryEpoch.status == OPEN)
        .order_by(RecoveryEpoch.generation.desc())
        .limit(1)
    ).first()


class RecoveryEpochSuperseded(RuntimeError):
    code = RECOVERY_EPOCH_SUPERSEDED

    def __init__(self, *, bound: RecoveryEpoch | None, current: RecoveryEpoch | None, reason: str = ""):
        self.bound = bound
        self.current = current
        self.facts = {
            "code": self.code,
            "bound_recovery_epoch_id": getattr(bound, "id", None),
            "stale_recovery_epoch_id": getattr(bound, "id", None),
            "current_recovery_epoch_id": getattr(current, "id", None),
            "bound_generation": getattr(bound, "generation", None),
            "stale_generation": getattr(bound, "generation", None),
            "current_generation": getattr(current, "generation", None),
            "bound_recovery_reality_fingerprint": getattr(bound, "recovery_reality_fingerprint", None),
            "stale_recovery_reality_fingerprint": getattr(bound, "recovery_reality_fingerprint", None),
            "current_recovery_reality_fingerprint": getattr(current, "recovery_reality_fingerprint", None),
            "reason": reason or "bound recovery epoch is no longer current",
        }
        super().__init__(self.facts["reason"])


def ensure_recovery_epoch(session: Session, journey: Journey) -> RecoveryEpoch:
    basis = recovery_reality_basis(session, journey)
    fingerprint = recovery_reality_fingerprint(basis)
    current = current_open_recovery_epoch(session, journey.id)
    if current is not None and (
        current.recovery_reality_fingerprint == fingerprint
        and current.active_plan_version_id_at_open == journey.active_plan_version_id
    ):
        return current

    now = _now()
    if current is not None:
        current.status = SUPERSEDED
        current.closed_at = now
        current.close_reason = "RECOVERY_REALITY_CHANGED"
    max_generation = session.scalar(
        select(func.max(RecoveryEpoch.generation)).where(RecoveryEpoch.journey_id == journey.id)
    ) or 0
    epoch = RecoveryEpoch(
        id=str(uuid4()),
        journey_id=journey.id,
        generation=int(max_generation) + 1,
        active_plan_version_id_at_open=journey.active_plan_version_id,
        recovery_reality_fingerprint=fingerprint,
        triggering_event_ids_json=json.dumps(
            sorted(str(item["id"]) for item in basis["events"]), separators=(",", ":")
        ),
        status=OPEN,
        opened_at=now,
    )
    if current is not None:
        current.superseded_by_recovery_epoch_id = epoch.id
    session.add(epoch)
    try:
        session.flush()
    except IntegrityError:
        # The partial unique index is the concurrency arbiter.  A concurrent
        # winner already created the same open epoch; reload it rather than a
        # process-local mutex or a caller-selected retarget.
        session.rollback()
        winner = current_open_recovery_epoch(session, journey.id)
        if winner is not None:
            return winner
        raise
    return epoch


def validate_recovery_epoch_binding(
    session: Session,
    journey_id: str,
    bound_recovery_epoch_id: str | None,
    *,
    expected_status: str = OPEN,
) -> RecoveryEpoch:
    current = current_open_recovery_epoch(session, journey_id)
    bound = session.get(RecoveryEpoch, str(bound_recovery_epoch_id)) if bound_recovery_epoch_id else None
    if bound is None or current is None or bound.id != current.id or bound.status != expected_status:
        raise RecoveryEpochSuperseded(bound=bound, current=current)
    return current


def close_recovery_epoch(
    session: Session, epoch: RecoveryEpoch, *, status: str, reason: str
) -> RecoveryEpoch:
    epoch.status = status
    epoch.closed_at = _now()
    epoch.close_reason = reason
    session.flush()
    return epoch


def supersede_recovery_epoch(session: Session, journey: Journey, reason: str) -> RecoveryEpoch | None:
    """Close the current open epoch as superseded without retargeting callers."""

    current = current_open_recovery_epoch(session, journey.id)
    if current is None:
        return None
    return close_recovery_epoch(session, current, status=SUPERSEDED, reason=reason)


def commit_recovery_epoch(session: Session, epoch: RecoveryEpoch, reason: str = "COMMITTED") -> RecoveryEpoch:
    return close_recovery_epoch(session, epoch, status=COMMITTED, reason=reason)


def semantic_plan_identity(session: Session, plan_version_id: str) -> str:
    """Canonical executable plan identity, excluding proposal/run metadata."""

    plan = session.get(PlanVersion, str(plan_version_id))
    if plan is None:
        return ""
    rows = session.scalars(
        select(Activity).where(Activity.plan_version_id == plan.id).order_by(Activity.sequence_no.asc())
    ).all()
    activities = [
        {
            "sequence_no": int(row.sequence_no),
            "activity_type": str(row.activity_type or ""),
            "place_id": str(row.place_id or ""),
            "city_service_id": str(row.city_service_id or ""),
            "start_at": str(row.start_at or ""),
            "end_at": str(row.end_at or ""),
            "travel_from_prev_min": int(row.travel_from_prev_min or 0),
            "estimated_cost_minor": int(row.estimated_cost_minor or 0),
            "currency": str(row.currency or ""),
            "locked": bool(row.locked),
        }
        for row in rows
    ]
    material = {"schema": "citynexus.executable-plan.v1", "activities": activities}
    encoded = json.dumps(material, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()
