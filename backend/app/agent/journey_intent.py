"""Scoped temporary Journey-intent semantics for live Operator steering."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time, timedelta, timezone
from typing import Any
from zoneinfo import ZoneInfo


@dataclass(frozen=True)
class IntentScope:
    kind: str
    starts_at: str
    ends_at: str | None
    local_date: str | None


def resolve_intent_scope(
    *,
    scope_kind: str,
    now: datetime,
    timezone_name: str,
    journey_end_at: str | None = None,
) -> IntentScope:
    """Resolve model/user temporal meaning into a server-owned bounded scope."""
    zone = ZoneInfo(timezone_name)
    local_now = now.astimezone(zone)
    kind = str(scope_kind or "").upper()

    if kind == "REST_OF_TODAY":
        end_local = datetime.combine(
            local_now.date() + timedelta(days=1),
            time.min,
            tzinfo=zone,
        )
        return IntentScope(
            kind=kind,
            starts_at=now.astimezone(timezone.utc).isoformat(),
            ends_at=end_local.astimezone(timezone.utc).isoformat(),
            local_date=local_now.date().isoformat(),
        )

    if kind == "NEXT_MORNING":
        next_day = local_now.date() + timedelta(days=1)
        start_local = datetime.combine(next_day, time(hour=5), tzinfo=zone)
        end_local = datetime.combine(next_day, time(hour=12), tzinfo=zone)
        return IntentScope(
            kind=kind,
            starts_at=start_local.astimezone(timezone.utc).isoformat(),
            ends_at=end_local.astimezone(timezone.utc).isoformat(),
            local_date=next_day.isoformat(),
        )

    if kind == "NEXT_STOP":
        # This is a semantic scope, not a guessed clock duration. The server
        # should end it when the next targeted activity becomes terminal.
        return IntentScope(
            kind=kind,
            starts_at=now.astimezone(timezone.utc).isoformat(),
            ends_at=None,
            local_date=local_now.date().isoformat(),
        )

    if kind == "REMAINING_JOURNEY":
        return IntentScope(
            kind=kind,
            starts_at=now.astimezone(timezone.utc).isoformat(),
            ends_at=journey_end_at,
            local_date=None,
        )

    raise ValueError("UNRESOLVED_INTENT_SCOPE")


def intent_is_active(
    *,
    status: str,
    starts_at: str,
    ends_at: str | None,
    now: datetime,
) -> bool:
    if str(status).upper() != "ACTIVE":
        return False
    start = datetime.fromisoformat(str(starts_at).replace("Z", "+00:00"))
    if start.tzinfo is None:
        return False
    stamp = now.astimezone(timezone.utc)
    if stamp < start.astimezone(timezone.utc):
        return False
    if ends_at:
        end = datetime.fromisoformat(str(ends_at).replace("Z", "+00:00"))
        if end.tzinfo is None or stamp >= end.astimezone(timezone.utc):
            return False
    return True


def canonical_intent_dimension(
    *,
    intent_kind: str,
    constraints: dict[str, Any] | None = None,
) -> str:
    """Dimension used for supersession, never as a global preference key."""
    kind = str(intent_kind or "GENERAL_GOAL").upper()
    constraint_keys = sorted(str(key).lower() for key in (constraints or {}).keys())
    if kind == "PACE":
        return "journey-intent:pace"
    if kind == "WALKING_LIMIT":
        return "journey-intent:walking"
    if kind == "FOOD_PREFERENCE":
        return "journey-intent:food"
    if kind in {"INDOOR_OUTDOOR", "INTEREST"}:
        return "journey-intent:interest"
    if kind == "TIME_CONSTRAINT":
        return "journey-intent:time"
    if kind == "BUDGET_TIGHTENING":
        return "journey-intent:budget"
    if kind == "REST_BREAK":
        return "journey-intent:rest"
    if kind == "ACCESSIBILITY_NEED":
        return "capability"
    return "journey-intent:" + ("+".join(constraint_keys) if constraint_keys else "general")


def should_require_clarification(
    *,
    confidence: float,
    scope_resolved: bool,
    constraint_count: int,
    intent_kind: str | None,
) -> bool:
    """Fail closed on vague steering rather than launching an unsafe replan."""
    if confidence < 0.55:
        return True
    if not scope_resolved:
        return True
    if not intent_kind:
        return True
    if str(intent_kind).upper() == "GENERAL_GOAL" and constraint_count == 0:
        return True
    return False
