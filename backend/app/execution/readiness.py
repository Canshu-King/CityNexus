"""Read-only departure readiness projection for the next meaningful Journey move."""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agent.watch_policy import next_move_projection
from app.db.models import Commitment, Event, Journey, TransportReservation
from app.execution.clock import execution_clock

_MATERIAL_EVENT_TYPES = {"WEATHER", "CLOSURE", "TRAFFIC_DELAY", "SCHEDULE_DELAY"}
_BLOCKING_VENUE_STATES = {"CLOSED_CONFLICT", "OUTSIDE_VERIFIED_HOURS"}
_UNCERTAIN_VENUE_STATES = {"UNKNOWN", "PROVIDER_DEGRADED"}


def _aware(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return parsed.astimezone(timezone.utc)


def _load(value: str | None, fallback: Any) -> Any:
    try:
        return json.loads(value or "")
    except (TypeError, json.JSONDecodeError):
        return fallback


def _open_material_events(session: Session, journey_id: str, activity_id: str | None) -> list[Event]:
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
    relevant: list[Event] = []
    for row in rows:
        try:
            payload = json.loads(row.payload_json or "{}")
        except json.JSONDecodeError:
            payload = {}
        if payload.get("predictive_only"):
            continue
        if activity_id and row.affected_activity_id and str(row.affected_activity_id) != str(activity_id):
            continue
        relevant.append(row)
    return relevant


def _target_commitments(
    session: Session, journey_id: str, activity_id: str | None
) -> list[Commitment]:
    rows = list(
        session.scalars(
            select(Commitment)
            .where(
                Commitment.journey_id == journey_id,
                Commitment.status == "ACTIVE",
                Commitment.level.in_(("C3_Guaranteed", "C4_Anchored")),
            )
            .order_by(Commitment.created_at, Commitment.id)
        ).all()
    )
    if not activity_id:
        return rows
    direct = [row for row in rows if str(row.activity_id or "") == str(activity_id)]
    return direct or rows


def _next_reservation(
    session: Session, journey_id: str, *, now: datetime
) -> TransportReservation | None:
    rows = list(
        session.scalars(
            select(TransportReservation)
            .where(
                TransportReservation.journey_id == journey_id,
                TransportReservation.status.in_(("CONFIRMED", "ACTIVE", "CANCELLED")),
            )
            .order_by(TransportReservation.scheduled_departure_at, TransportReservation.id)
        ).all()
    )
    future: list[tuple[datetime, TransportReservation]] = []
    for row in rows:
        departure = _aware(row.scheduled_departure_at)
        if departure is not None and departure >= now - timedelta(minutes=30):
            future.append((departure, row))
    return min(future, key=lambda item: item[0])[1] if future else None


def departure_readiness_projection(
    session: Session,
    journey: Journey,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Fuse current evidence into one authority-neutral readiness answer."""

    stamp = (now or execution_clock.now()).astimezone(timezone.utc)
    next_move = next_move_projection(session, journey, now=stamp)
    target = next_move.get("next_activity") or next_move.get("current_activity")
    target_id = str((target or {}).get("id") or "") or None
    starts_at = _aware((target or {}).get("start_at"))
    minutes_until_start = (
        round((starts_at - stamp).total_seconds() / 60.0, 1) if starts_at is not None else None
    )

    venue = next_move.get("venue_readiness") or {}
    venue_state = str(venue.get("state") or "UNKNOWN")
    route = next_move.get("route_evidence") or {}
    route_state = str(route.get("state") or "UNKNOWN")
    route_degraded = bool(route.get("degraded"))
    presence = next_move.get("presence") or {}
    presence_state = str(presence.get("state") or "LOCATION_UNAVAILABLE")

    commitments = _target_commitments(session, journey.id, target_id)
    reservation = _next_reservation(session, journey.id, now=stamp)
    events = _open_material_events(session, journey.id, target_id)

    blocking: list[str] = []
    warnings: list[str] = []

    if venue_state in _BLOCKING_VENUE_STATES:
        blocking.append("VENUE_NOT_COMPATIBLE")
    elif venue_state in _UNCERTAIN_VENUE_STATES:
        warnings.append("VENUE_NOT_VERIFIED")

    if route_degraded or route_state.upper() in {"UNKNOWN", "UNAVAILABLE", "DEGRADED"}:
        warnings.append("ROUTE_EVIDENCE_UNCERTAIN")

    critical_events = [row for row in events if str(row.severity).upper() == "CRITICAL"]
    if critical_events:
        blocking.append("CRITICAL_MATERIAL_EVENT")
    elif events:
        warnings.append("OPEN_MATERIAL_EVENT")

    reservation_state = "NONE"
    realtime_state = None
    if reservation is not None:
        reservation_state = str(reservation.status or "UNKNOWN").upper()
        realtime_state = str(reservation.realtime_status or "UNKNOWN_REALTIME").upper()
        if reservation_state == "CANCELLED" or realtime_state == "CANCELLED":
            blocking.append("TRANSPORT_CANCELLED")
        elif realtime_state in {"UNKNOWN_REALTIME", "STALE_REALTIME"}:
            warnings.append("TRANSPORT_REALTIME_UNCERTAIN")

    commitment_state = "PROTECTED" if commitments else "NONE"

    if presence_state in {"LOCATION_STALE", "LOCATION_IMPRECISE"} and (
        minutes_until_start is not None and minutes_until_start <= 60
    ):
        warnings.append("PRESENCE_NOT_FRESH_ENOUGH")
    elif presence_state == "LOCATION_UNAVAILABLE":
        warnings.append("LOCATION_UNAVAILABLE")

    must_leave_by = None
    must_leave_reason = "ROUTE_EVIDENCE_DOES_NOT_EXPOSE_TRAVEL_MINUTES"
    # Only use an explicit duration if the projection already exposes one.
    route_minutes = route.get("minutes") or route.get("duration_min")
    try:
        travel_minutes = int(route_minutes) if route_minutes is not None else None
    except (TypeError, ValueError):
        travel_minutes = None
    if starts_at is not None and travel_minutes is not None and travel_minutes >= 0:
        must_leave_by = (starts_at - timedelta(minutes=travel_minutes + 10)).isoformat()
        must_leave_reason = None

    if not target:
        state = "COMPLETE" if journey.status == "COMPLETED" else "UNKNOWN"
        action = "NONE"
    elif blocking:
        state = "BLOCKED"
        action = "DO_NOT_DEPART"
    elif warnings:
        close = minutes_until_start is not None and minutes_until_start <= 60
        state = "ACTION_NEEDED" if close and any(
            item in {
                "VENUE_NOT_VERIFIED",
                "ROUTE_EVIDENCE_UNCERTAIN",
                "PRESENCE_NOT_FRESH_ENOUGH",
                "OPEN_MATERIAL_EVENT",
            }
            for item in warnings
        ) else "READY_WITH_UNCERTAINTY"
        action = "CHECK_BEFORE_LEAVING" if state == "ACTION_NEEDED" else "LEAVE_ON_SCHEDULE"
    elif minutes_until_start is not None and minutes_until_start > 120:
        state = "NOT_DUE"
        action = "WAIT"
    else:
        state = "READY"
        action = "LEAVE_ON_SCHEDULE"

    return {
        "state": state,
        "target_activity_id": target_id,
        "target_title": (target or {}).get("title"),
        "starts_at": (target or {}).get("start_at"),
        "minutes_until_start": minutes_until_start,
        "must_leave_by": must_leave_by,
        "must_leave_by_absent_reason": must_leave_reason,
        "blocking_reasons": sorted(set(blocking)),
        "warning_reasons": sorted(set(warnings)),
        "checks": {
            "venue": venue_state,
            "route": route_state,
            "reservation": reservation_state,
            "reservation_realtime": realtime_state,
            "commitment": commitment_state,
            "presence": presence_state,
        },
        "recommended_action": action,
        "authority": "READ_ONLY_PROJECTION",
        "next_move": next_move,
        "evidence": {
            "material_event_ids": [row.id for row in events],
            "commitment_ids": [row.id for row in commitments],
            "reservation_id": reservation.id if reservation is not None else None,
        },
    }
