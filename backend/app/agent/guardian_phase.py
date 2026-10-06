from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Activity, Journey
from app.execution.clock import execution_clock

_TERMINAL = {"COMPLETED", "SKIPPED", "CANCELLED"}
_EXPLICIT_TRANSIT = {"EN_ROUTE"}
_EXPLICIT_ACTIVITY = {"ARRIVED", "IN_PROGRESS"}
_APPROACH_WINDOW_MIN = 90


@dataclass(frozen=True)
class GuardianPhasePolicy:
    phase: str
    reason_code: str
    current_activity_id: str | None
    next_activity_id: str | None
    monitored_activity_ids: tuple[str, ...]
    lookahead_minutes: int
    interval_seconds: float
    authority: str = "CONTROL_PLANE_ONLY"

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["monitored_activity_ids"] = list(self.monitored_activity_ids)
        return payload


_POLICY = {
    "PRE_TRIP": (300.0, 12 * 60),
    "APPROACHING_NEXT": (30.0, 180),
    "IN_TRANSIT": (30.0, 180),
    "IN_ACTIVITY": (120.0, 240),
    "BETWEEN_ACTIVITIES": (90.0, 240),
    "OVERNIGHT": (900.0, 12 * 60),
    "JOURNEY_COMPLETE": (24 * 60 * 60.0, 0),
    "UNKNOWN": (120.0, 180),
}


def _local(value: str, zone: ZoneInfo) -> datetime:
    parsed = datetime.fromisoformat(str(value))
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=zone)
    return parsed.astimezone(zone)


def _scope(
    phase: str,
    activities: list[Activity],
    *,
    current: Activity | None,
    next_activity: Activity | None,
) -> tuple[str, ...]:
    active = [item for item in activities if item.status not in _TERMINAL]
    if not active:
        return ()

    if phase == "IN_ACTIVITY" and current is not None:
        index = active.index(current) if current in active else -1
        selected = [current]
        if index >= 0 and index + 1 < len(active):
            selected.append(active[index + 1])
        return tuple(str(item.id) for item in selected)

    if next_activity is not None:
        index = active.index(next_activity) if next_activity in active else -1
        selected = [next_activity]
        if index >= 0 and index + 1 < len(active):
            selected.append(active[index + 1])
        return tuple(str(item.id) for item in selected)

    return tuple(str(item.id) for item in active[:2])


def derive_guardian_phase(
    session: Session,
    journey: Journey,
    *,
    now: datetime | None = None,
) -> GuardianPhasePolicy:
    """Derive monitoring urgency/scope without claiming physical-world execution truth."""

    try:
        zone = ZoneInfo(journey.timezone)
    except Exception:
        zone = ZoneInfo("UTC")
    current_time = (now or execution_clock.now(journey.timezone)).astimezone(zone)

    activities = list(
        session.scalars(
            select(Activity)
            .where(Activity.plan_version_id == journey.active_plan_version_id)
            .order_by(Activity.sequence_no)
        ).all()
        if journey.active_plan_version_id
        else []
    )
    active = [item for item in activities if item.status not in _TERMINAL]

    explicit_transit = [item for item in active if item.status in _EXPLICIT_TRANSIT]
    explicit_activity = [item for item in active if item.status in _EXPLICIT_ACTIVITY]
    if len(explicit_transit) + len(explicit_activity) > 1:
        interval, horizon = _POLICY["UNKNOWN"]
        return GuardianPhasePolicy(
            phase="UNKNOWN",
            reason_code="CONTRADICTORY_EXECUTION_TRUTH",
            current_activity_id=None,
            next_activity_id=str(active[0].id) if active else None,
            monitored_activity_ids=tuple(str(item.id) for item in active[:2]),
            lookahead_minutes=horizon,
            interval_seconds=interval,
        )

    if explicit_transit:
        current = explicit_transit[0]
        interval, horizon = _POLICY["IN_TRANSIT"]
        return GuardianPhasePolicy(
            phase="IN_TRANSIT",
            reason_code="EXPLICIT_EN_ROUTE_EXECUTION_TRUTH",
            current_activity_id=str(current.id),
            next_activity_id=str(current.id),
            monitored_activity_ids=_scope(
                "IN_TRANSIT", activities, current=None, next_activity=current
            ),
            lookahead_minutes=horizon,
            interval_seconds=interval,
        )

    if explicit_activity:
        current = explicit_activity[0]
        next_activity = next(
            (
                item
                for item in active
                if item.sequence_no > current.sequence_no
            ),
            None,
        )
        interval, horizon = _POLICY["IN_ACTIVITY"]
        return GuardianPhasePolicy(
            phase="IN_ACTIVITY",
            reason_code="EXPLICIT_ACTIVE_EXECUTION_TRUTH",
            current_activity_id=str(current.id),
            next_activity_id=str(next_activity.id) if next_activity else None,
            monitored_activity_ids=_scope(
                "IN_ACTIVITY", activities, current=current, next_activity=next_activity
            ),
            lookahead_minutes=horizon,
            interval_seconds=interval,
        )

    if not active:
        interval, horizon = _POLICY["JOURNEY_COMPLETE"]
        return GuardianPhasePolicy(
            phase="JOURNEY_COMPLETE",
            reason_code="NO_NONTERMINAL_ACTIVITIES",
            current_activity_id=None,
            next_activity_id=None,
            monitored_activity_ids=(),
            lookahead_minutes=horizon,
            interval_seconds=interval,
        )

    timed = [(item, _local(item.start_at, zone), _local(item.end_at, zone)) for item in active]
    current = next((item for item, start, end in timed if start <= current_time < end), None)
    upcoming = next((item for item, start, _end in timed if start > current_time), None)

    if current is not None:
        next_activity = next(
            (item for item in active if item.sequence_no > current.sequence_no),
            None,
        )
        interval, horizon = _POLICY["IN_ACTIVITY"]
        return GuardianPhasePolicy(
            phase="IN_ACTIVITY",
            reason_code="CLOCK_WITHIN_PLANNED_ACTIVITY_WINDOW",
            current_activity_id=str(current.id),
            next_activity_id=str(next_activity.id) if next_activity else None,
            monitored_activity_ids=_scope(
                "IN_ACTIVITY", activities, current=current, next_activity=next_activity
            ),
            lookahead_minutes=horizon,
            interval_seconds=interval,
        )

    if upcoming is None:
        interval, horizon = _POLICY["JOURNEY_COMPLETE"]
        return GuardianPhasePolicy(
            phase="JOURNEY_COMPLETE",
            reason_code="PLAN_WINDOW_ELAPSED",
            current_activity_id=None,
            next_activity_id=None,
            monitored_activity_ids=(),
            lookahead_minutes=horizon,
            interval_seconds=interval,
        )

    next_start = _local(upcoming.start_at, zone)
    minutes_to_next = (next_start - current_time).total_seconds() / 60.0
    prior = [
        (item, start, end)
        for item, start, end in timed
        if end <= current_time
    ]

    if current_time < _local(journey.start_at, zone):
        phase = "APPROACHING_NEXT" if minutes_to_next <= _APPROACH_WINDOW_MIN else "PRE_TRIP"
        reason = (
            "NEXT_ACTIVITY_WITHIN_APPROACH_WINDOW"
            if phase == "APPROACHING_NEXT"
            else "JOURNEY_NOT_STARTED"
        )
    elif (
        next_start.date() > current_time.date()
        and (current_time.hour >= 20 or current_time.hour < 6)
    ):
        phase = "OVERNIGHT"
        reason = "NEXT_ACTIVITY_ON_FUTURE_LOCAL_DAY"
    elif prior:
        phase = "APPROACHING_NEXT" if minutes_to_next <= _APPROACH_WINDOW_MIN else "BETWEEN_ACTIVITIES"
        reason = (
            "NEXT_ACTIVITY_WITHIN_APPROACH_WINDOW"
            if phase == "APPROACHING_NEXT"
            else "CLOCK_BETWEEN_PLANNED_ACTIVITIES"
        )
    else:
        phase = "APPROACHING_NEXT" if minutes_to_next <= _APPROACH_WINDOW_MIN else "PRE_TRIP"
        reason = (
            "NEXT_ACTIVITY_WITHIN_APPROACH_WINDOW"
            if phase == "APPROACHING_NEXT"
            else "BEFORE_FIRST_ACTIVITY"
        )

    interval, horizon = _POLICY[phase]
    return GuardianPhasePolicy(
        phase=phase,
        reason_code=reason,
        current_activity_id=None,
        next_activity_id=str(upcoming.id),
        monitored_activity_ids=_scope(
            phase, activities, current=None, next_activity=upcoming
        ),
        lookahead_minutes=horizon,
        interval_seconds=interval,
    )


def effective_guardian_interval(
    enrollment_interval_seconds: float,
    phase: GuardianPhasePolicy,
) -> float:
    """Enrollment cadence is an operator ceiling; phase may tighten, never relax, it."""

    return min(float(enrollment_interval_seconds), float(phase.interval_seconds))
