"""Deterministic adaptive scheduling policy for Guardian Autopilot."""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Activity, AutopilotEnrollment, Event, Journey

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

    stamp = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    configured = max(0.05, float(enrollment.interval_seconds))
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
    stamp = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    policy = adaptive_watch_policy(session, journey, enrollment, now=stamp)
    due = _as_aware(str(policy.get("next_due_at") or ""))
    return bool(due is None or due <= stamp)
