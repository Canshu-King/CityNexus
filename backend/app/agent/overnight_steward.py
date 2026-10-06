"""Overnight Steward projection for multi-day Journey continuity.

Read-only product state. Day-close writes (Twin learning, briefing notification)
must be performed by an explicit server-owned overnight operation.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Iterable
from zoneinfo import ZoneInfo


_EXECUTING = {"EN_ROUTE", "ARRIVED", "IN_PROGRESS"}
_TERMINAL = {"COMPLETED", "SKIPPED", "CANCELLED"}


def _aware(value: str | None, timezone_name: str) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=ZoneInfo(timezone_name))
    return parsed.astimezone(timezone.utc)


def overnight_steward_state(
    *,
    journey_status: str,
    timezone_name: str,
    activities: Iterable[dict[str, Any]],
    now: datetime,
    day_closed: bool = False,
    learning_in_progress: bool = False,
    tomorrow_ready: bool = False,
    tomorrow_needs_attention: bool = False,
    provider_degraded: bool = False,
    brain_blocked: bool = False,
) -> dict[str, Any]:
    """Project whether the same Journey Operator should steward overnight."""

    if str(journey_status).upper() == "COMPLETED":
        return {
            "state": "INACTIVE",
            "reason": "JOURNEY_COMPLETE",
            "local_date": now.astimezone(ZoneInfo(timezone_name)).date().isoformat(),
            "tomorrow_activity_ids": [],
        }

    stamp = now.astimezone(timezone.utc)
    local_now = stamp.astimezone(ZoneInfo(timezone_name))
    rows = [dict(item) for item in activities]

    executing = [
        item for item in rows
        if str(item.get("status") or "").upper() in _EXECUTING
    ]
    if executing:
        return {
            "state": "INACTIVE",
            "reason": "EXECUTION_STILL_ACTIVE",
            "local_date": local_now.date().isoformat(),
            "tomorrow_activity_ids": [],
        }

    tomorrow_rows: list[tuple[datetime, dict[str, Any]]] = []
    for item in rows:
        if str(item.get("status") or "").upper() in _TERMINAL:
            continue
        start = _aware(item.get("start_at"), timezone_name)
        if start is None:
            continue
        local_start = start.astimezone(ZoneInfo(timezone_name))
        if local_start.date() > local_now.date():
            tomorrow_rows.append((start, item))
    tomorrow_rows.sort(key=lambda pair: pair[0])
    tomorrow_ids = [str(item.get("id")) for _start, item in tomorrow_rows[:3]]

    if not tomorrow_rows:
        return {
            "state": "INACTIVE",
            "reason": "NO_FUTURE_LOCAL_DAY",
            "local_date": local_now.date().isoformat(),
            "tomorrow_activity_ids": [],
        }

    if provider_degraded:
        state = "OVERNIGHT_PROVIDER_DEGRADED"
    elif brain_blocked:
        state = "OVERNIGHT_BRAIN_BLOCKED"
    elif learning_in_progress:
        state = "LEARNING_FROM_TODAY"
    elif tomorrow_needs_attention:
        state = "MORNING_NEEDS_ATTENTION"
    elif tomorrow_ready:
        state = "MORNING_READY"
    elif not day_closed:
        state = "DAY_CLOSING"
    else:
        state = "WATCHING_TOMORROW"

    return {
        "state": state,
        "reason": "FUTURE_LOCAL_DAY_AVAILABLE",
        "local_date": local_now.date().isoformat(),
        "next_local_date": tomorrow_rows[0][0].astimezone(ZoneInfo(timezone_name)).date().isoformat(),
        "tomorrow_activity_ids": tomorrow_ids,
    }


def overnight_cycle_key(*, journey_id: str, local_date: str, plan_version_id: str | None) -> str:
    """Stable day-boundary identity; repeated pulses must converge."""
    return f"overnight:{journey_id}:{local_date}:{plan_version_id or 'no-plan'}"
