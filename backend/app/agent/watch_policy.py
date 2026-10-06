"""Deterministic adaptive scheduling policy for Guardian Autopilot."""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Activity, AutopilotEnrollment, Event, Journey
from app.execution.clock import execution_clock

_TERMINAL_ACTIVITY = {"COMPLETED", "SKIPPED", "CANCELLED"}
_MATERIAL_EVENT_TYPES = {"WEATHER", "CLOSURE", "TRAFFIC_DELAY", "SCHEDULE_DELAY"}


def _as_aware(value: str | None, *, timezone_name: str = "UTC") -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=ZoneInfo(timezone_name))
    return parsed.astimezone(timezone.utc)


def _is_predictive(event: Event) -> bool:
    try:
        return bool(json.loads(event.payload_json or "{}").get("predictive_only"))
    except (TypeError, json.JSONDecodeError):
        return False


def _next_activity(
    session: Session,
    journey: Journey,
    *,
    now: datetime,
) -> tuple[Activity | None, float | None]:
    if not journey.active_plan_version_id:
        return None, None
    rows = list(
        session.scalars(
            select(Activity)
            .where(Activity.plan_version_id == journey.active_plan_version_id)
            .order_by(Activity.sequence_no)
        ).all()
    )
    candidates: list[tuple[float, Activity]] = []
    for row in rows:
        if row.status in _TERMINAL_ACTIVITY:
            continue
        start = _as_aware(row.start_at, timezone_name=journey.timezone)
        end = _as_aware(row.end_at, timezone_name=journey.timezone)
        if start is None:
            continue
        if end is not None and end <= now:
            continue
        horizon = max(0.0, (start - now).total_seconds())
        candidates.append((horizon, row))
    if not candidates:
        return None, None
    horizon, row = min(candidates, key=lambda item: (item[0], item[1].sequence_no))
    return row, horizon


def _open_material_events(session: Session, journey_id: str) -> list[Event]:
    rows = list(
        session.scalars(
            select(Event)
            .where(
                Event.journey_id == journey_id,
                Event.status.in_(("DETECTED", "ACKNOWLEDGED")),
                Event.event_type.in_(tuple(_MATERIAL_EVENT_TYPES)),
            )
            .order_by(Event.detected_at, Event.id)
        ).all()
    )
    return [row for row in rows if not _is_predictive(row)]



def journey_phase_projection(
    session: Session,
    journey: Journey,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Derive control-plane Journey phase and bounded monitoring scope.

    Clock inference is allowed to change watch urgency/scope only. It is never
    physical execution truth and never grants mutation authority.
    """

    stamp = (now or execution_clock.now()).astimezone(timezone.utc)
    if not journey.active_plan_version_id:
        return {
            "journey_phase": "UNKNOWN",
            "phase_reason_code": "NO_ACTIVE_PLAN",
            "phase_authority": "CONTROL_PLANE_ONLY",
            "current_activity_id": None,
            "monitored_activity_ids": [],
        }

    rows = list(
        session.scalars(
            select(Activity)
            .where(Activity.plan_version_id == journey.active_plan_version_id)
            .order_by(Activity.sequence_no)
        ).all()
    )
    active = [row for row in rows if row.status not in _TERMINAL_ACTIVITY]
    explicit_transit = [row for row in active if row.status == "EN_ROUTE"]
    explicit_activity = [row for row in active if row.status in {"ARRIVED", "IN_PROGRESS"}]

    def bounded_from(anchor: Activity | None, include_anchor: bool = True) -> list[str]:
        if anchor is None:
            return [str(row.id) for row in active[:2]]
        try:
            index = active.index(anchor)
        except ValueError:
            return [str(anchor.id)]
        selected = active[index : index + 2] if include_anchor else active[index + 1 : index + 3]
        return [str(row.id) for row in selected]

    if len(explicit_transit) + len(explicit_activity) > 1:
        return {
            "journey_phase": "UNKNOWN",
            "phase_reason_code": "CONTRADICTORY_EXECUTION_TRUTH",
            "phase_authority": "CONTROL_PLANE_ONLY",
            "current_activity_id": None,
            "monitored_activity_ids": [str(row.id) for row in active[:2]],
        }
    if explicit_transit:
        row = explicit_transit[0]
        return {
            "journey_phase": "IN_TRANSIT",
            "phase_reason_code": "EXPLICIT_EN_ROUTE_EXECUTION_TRUTH",
            "phase_authority": "EXECUTION_TRUTH",
            "current_activity_id": str(row.id),
            "monitored_activity_ids": bounded_from(row),
        }
    if explicit_activity:
        row = explicit_activity[0]
        return {
            "journey_phase": "IN_ACTIVITY",
            "phase_reason_code": "EXPLICIT_ACTIVE_EXECUTION_TRUTH",
            "phase_authority": "EXECUTION_TRUTH",
            "current_activity_id": str(row.id),
            "monitored_activity_ids": bounded_from(row),
        }
    if not active:
        return {
            "journey_phase": "JOURNEY_COMPLETE",
            "phase_reason_code": "NO_NONTERMINAL_ACTIVITIES",
            "phase_authority": "CONTROL_PLANE_ONLY",
            "current_activity_id": None,
            "monitored_activity_ids": [],
        }

    timed: list[tuple[Activity, datetime | None, datetime | None]] = [
        (
            row,
            _as_aware(row.start_at, timezone_name=journey.timezone),
            _as_aware(row.end_at, timezone_name=journey.timezone),
        )
        for row in active
    ]
    current = next(
        (
            row
            for row, start, end in timed
            if start is not None and end is not None and start <= stamp < end
        ),
        None,
    )
    if current is not None:
        return {
            "journey_phase": "IN_ACTIVITY",
            "phase_reason_code": "CLOCK_WITHIN_PLANNED_ACTIVITY_WINDOW",
            "phase_authority": "CONTROL_PLANE_ONLY",
            "current_activity_id": str(current.id),
            "monitored_activity_ids": bounded_from(current),
        }

    future = [(row, start) for row, start, _end in timed if start is not None and start > stamp]
    next_row, next_start = min(future, key=lambda item: item[1]) if future else (None, None)
    if next_row is None or next_start is None:
        return {
            "journey_phase": "JOURNEY_COMPLETE",
            "phase_reason_code": "PLAN_WINDOW_ELAPSED",
            "phase_authority": "CONTROL_PLANE_ONLY",
            "current_activity_id": None,
            "monitored_activity_ids": [],
        }

    local_now = stamp.astimezone(ZoneInfo(journey.timezone))
    local_next = next_start.astimezone(ZoneInfo(journey.timezone))
    horizon = (next_start - stamp).total_seconds()
    if local_next.date() > local_now.date() and (local_now.hour >= 20 or local_now.hour < 6):
        phase, reason = "OVERNIGHT", "NEXT_ACTIVITY_ON_FUTURE_LOCAL_DAY"
    elif horizon <= 2 * 3600:
        phase, reason = "APPROACHING_NEXT", "NEXT_ACTIVITY_WITHIN_2H"
    else:
        prior_ended = any(end is not None and end <= stamp for _row, _start, end in timed)
        phase = "BETWEEN_ACTIVITIES" if prior_ended else "PRE_TRIP"
        reason = "CLOCK_BETWEEN_PLANNED_ACTIVITIES" if prior_ended else "BEFORE_FIRST_ACTIVITY"

    return {
        "journey_phase": phase,
        "phase_reason_code": reason,
        "phase_authority": "CONTROL_PLANE_ONLY",
        "current_activity_id": None,
        "monitored_activity_ids": bounded_from(next_row),
    }

def adaptive_watch_policy(
    session: Session,
    journey: Journey,
    enrollment: AutopilotEnrollment,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Return current server-owned watch urgency and effective cadence.

    interval_seconds remains the maximum requested interval. The adaptive
    policy may shorten it as a meaningful activity approaches or while a
    material incident remains unresolved.
    """

    stamp = (now or execution_clock.now()).astimezone(timezone.utc)
    configured = max(0.05, float(enrollment.interval_seconds))
    phase = journey_phase_projection(session, journey, now=stamp)
    next_activity, horizon = _next_activity(session, journey, now=stamp)
    incidents = _open_material_events(session, journey.id)

    if incidents:
        state = "INCIDENT_ACTIVE"
        policy_interval = 60.0
        reason = "UNRESOLVED_MATERIAL_INCIDENT"
    elif horizon is not None and horizon <= 2 * 3600:
        state = "APPROACHING"
        policy_interval = 5 * 60.0
        reason = "NEXT_ACTIVITY_WITHIN_2H"
    elif horizon is not None and horizon <= 8 * 3600:
        state = "TODAY"
        policy_interval = 15 * 60.0
        reason = "NEXT_ACTIVITY_WITHIN_8H"
    elif horizon is not None and horizon <= 24 * 3600:
        state = "DAY_AHEAD"
        policy_interval = 30 * 60.0
        reason = "NEXT_ACTIVITY_WITHIN_24H"
    else:
        state = "QUIET"
        policy_interval = configured
        reason = "NO_NEAR_TERM_ACTIVITY_OR_MATERIAL_INCIDENT"

    effective = min(configured, policy_interval)
    previous = _as_aware(enrollment.last_pulse_at)
    next_due = stamp if previous is None else previous + timedelta(seconds=effective)

    event_newer_than_last_pulse = False
    if incidents:
        detected = [_as_aware(row.detected_at) for row in incidents]
        detected = [item for item in detected if item is not None]
        newest = max(detected, default=None)
        if newest is not None and (previous is None or newest > previous):
            event_newer_than_last_pulse = True
            next_due = stamp

    return {
        "watch_state": state,
        "reason_code": reason,
        "configured_interval_seconds": configured,
        "effective_interval_seconds": effective,
        "next_due_at": next_due.isoformat(),
        "next_activity_id": next_activity.id if next_activity is not None else None,
        "next_activity_start_at": next_activity.start_at if next_activity is not None else None,
        "next_activity_horizon_seconds": horizon,
        "open_material_event_ids": [row.id for row in incidents],
        "event_newer_than_last_pulse": event_newer_than_last_pulse,
        **phase,
    }


def watch_is_due(
    session: Session,
    journey: Journey,
    enrollment: AutopilotEnrollment,
    *,
    now: datetime | None = None,
) -> bool:
    if not enrollment.enabled:
        return False
    stamp = (now or execution_clock.now()).astimezone(timezone.utc)
    policy = adaptive_watch_policy(session, journey, enrollment, now=stamp)
    due = _as_aware(str(policy.get("next_due_at") or ""))
    return bool(due is None or due <= stamp)
