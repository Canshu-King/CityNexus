"""Read-only, bounded projection of persisted Guardian activity for one Journey."""
from __future__ import annotations

import json
import re
from typing import Any

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core import config
from app.db.models import (
    Event,
    GuardianPulse,
    GuardianRun,
    ImpactAssessment,
    Journey,
    JourneyMission,
)
from app.recovery_epoch import current_open_recovery_epoch


_MAX_LIMIT = 50
_MAX_ASSOCIATED_ROWS = 250
_OPEN_EVENT_STATUSES = frozenset({"DETECTED", "ACKNOWLEDGED", "ACTIVE", "OPEN"})
_SAFE_CODE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,79}$")


def _stable_code(value: Any) -> str:
    if isinstance(value, str) and _SAFE_CODE.fullmatch(value):
        return value
    return "UNKNOWN"


def _stable_code_list(raw: str | None) -> list[str]:
    try:
        values = json.loads(raw or "[]")
    except (TypeError, json.JSONDecodeError):
        return []
    if not isinstance(values, list):
        return []
    result: list[str] = []
    for value in values[:32]:
        if isinstance(value, str) and _SAFE_CODE.fullmatch(value):
            result.append(value)
    return result


def _structural_id(value: Any) -> str | None:
    if isinstance(value, str) and value and len(value) <= 128:
        return value
    return None


def _latest_pulse(session: Session, journey_id: str) -> GuardianPulse | None:
    return session.scalars(
        select(GuardianPulse)
        .where(GuardianPulse.journey_id == str(journey_id))
        .order_by(GuardianPulse.started_at.desc(), GuardianPulse.id.desc())
        .limit(1)
    ).first()


def _recovery_epoch(session: Session, journey_id: str) -> dict[str, Any] | None:
    epoch = current_open_recovery_epoch(session, str(journey_id))
    if epoch is None:
        return None
    return {
        "id": _structural_id(epoch.id),
        "generation": int(epoch.generation),
        "status": _stable_code(epoch.status),
        "triggering_event_ids": _stable_code_list(epoch.triggering_event_ids_json),
        "opened_at": epoch.opened_at,
        "active_plan_version_id_at_open": _structural_id(epoch.active_plan_version_id_at_open),
    }


def _resolution(event: Event) -> dict[str, Any] | None:
    """How this observation was closed, or None while it still stands.

    Only a server-persisted resolution counts: the Event row must say RESOLVED
    *and* carry the `resolved_at` this server wrote when it closed the record.
    Payload text is never the basis -- a client can submit arbitrary payload keys
    on a DETECTED event, so trusting `payload.resolution_reason` there would let
    a report hide that the issue is still open.  The reason code is therefore
    read only after the column timestamp has already established closure.
    """
    status = _stable_code(event.status)
    resolved_at = event.resolved_at
    if status != "RESOLVED" or not isinstance(resolved_at, str) or not resolved_at:
        return None
    try:
        payload = json.loads(event.payload_json or "{}")
        reason = payload.get("resolution_reason") if isinstance(payload, dict) else None
    except (TypeError, json.JSONDecodeError):
        reason = None
    return {
        "reason": _stable_code(reason),
        "decided_at": resolved_at,
    }


def _observation(event: Event) -> dict[str, Any]:
    return {
        "id": _structural_id(event.id),
        "event_type": _stable_code(event.event_type),
        "severity": _stable_code(event.severity),
        "status": _stable_code(event.status),
        "provider": _stable_code(event.provider_key),
        "provenance": _stable_code(event.provenance),
        "detected_at": event.detected_at,
        "affected_activity_id": _structural_id(event.affected_activity_id),
        "resolution": _resolution(event),
    }


def _impact(row: ImpactAssessment | None) -> dict[str, Any] | None:
    if row is None:
        return None
    return {
        "id": _structural_id(row.id),
        "status": _stable_code(row.status),
        "uncertain": bool(row.uncertain),
        "reason_codes": _stable_code_list(row.reason_codes_json),
        "created_at": row.created_at,
    }


def _proposed_action(row: GuardianRun | None) -> dict[str, Any] | None:
    if row is None:
        return None
    return {
        "id": _structural_id(row.id),
        "decision": _stable_code(row.decision),
        "status": _stable_code(row.status),
        "action_status": _stable_code(row.action_status),
        "proposal_id": _structural_id(row.proposal_id),
        "created_at": row.created_at,
        "completed_at": row.completed_at,
    }


def guardian_stream(
    session: Session,
    journey: Journey,
    mission_id: str | None = None,
    limit: int = 20,
) -> dict[str, Any]:
    """Return persisted Guardian rows; this function never starts or writes a watch."""
    if mission_id is None:
        mission = None
    else:
        mission = session.get(JourneyMission, str(mission_id))
        if mission is None or str(mission.journey_id) != str(journey.id):
            raise HTTPException(404, "MISSION_NOT_FOUND")

    try:
        bounded_limit = max(1, min(_MAX_LIMIT, int(limit)))
    except (TypeError, ValueError):
        raise HTTPException(422, "GUARDIAN_STREAM_LIMIT_INVALID") from None

    events = list(
        session.scalars(
            select(Event)
            .where(Event.journey_id == str(journey.id))
            .order_by(Event.detected_at.desc(), Event.id.desc())
            .limit(bounded_limit)
        ).all()
    )
    pulse = _latest_pulse(session, str(journey.id))
    event_ids = [event.id for event in events]

    impact_by_event: dict[str, ImpactAssessment] = {}
    action_by_event: dict[str, GuardianRun] = {}
    if event_ids:
        for row in session.scalars(
            select(ImpactAssessment)
            .where(
                ImpactAssessment.journey_id == str(journey.id),
                ImpactAssessment.event_id.in_(event_ids),
            )
            .order_by(ImpactAssessment.created_at.desc(), ImpactAssessment.id.desc())
            .limit(_MAX_ASSOCIATED_ROWS)
        ).all():
            impact_by_event.setdefault(row.event_id, row)

        for row in session.scalars(
            select(GuardianRun)
            .where(
                GuardianRun.journey_id == str(journey.id),
                GuardianRun.trigger_event_id.in_(event_ids),
            )
            .order_by(GuardianRun.created_at.desc(), GuardianRun.id.desc())
            .limit(_MAX_ASSOCIATED_ROWS)
        ).all():
            if row.trigger_event_id is not None:
                action_by_event.setdefault(row.trigger_event_id, row)

    stream = [
        {
            "observation": _observation(event),
            # The traveller card reads these as current work, not past history.
            # An accepted adjustment must not retain an old UNRESOLVED action.
            "impact": None if _resolution(event) else _impact(impact_by_event.get(event.id)),
            "proposed_action": None if _resolution(event) else _proposed_action(action_by_event.get(event.id)),
            "history": {
                "impact": _impact(impact_by_event.get(event.id)),
                "proposed_action": _proposed_action(action_by_event.get(event.id)),
            } if _resolution(event) else None,
        }
        for event in events
    ]
    last_observed_at = (
        events[0].detected_at
        if events
        else ((pulse.completed_at or pulse.started_at) if pulse is not None else None)
    )
    status = "HAS_EVENTS" if events or pulse is not None else "WATCH_NOT_RUNNING"

    return {
        "tool": "read_guardian_stream",
        "journey_id": str(journey.id),
        "mission_id": str(mission.id) if mission is not None else None,
        "status": status,
        "watch": {
            "configured": bool(config.settings.guardian_autorun),
            "last_observed_at": last_observed_at,
            "latest_pulse": (
                {
                    "id": _structural_id(pulse.id),
                    "status": _stable_code(pulse.status),
                    "started_at": pulse.started_at,
                    "completed_at": pulse.completed_at,
                }
                if pulse is not None
                else None
            ),
        },
        "recovery_epoch": _recovery_epoch(session, str(journey.id)),
        "stream": stream,
        "counts": {
            "events": len(events),
            "open_events": sum(1 for event in events if event.status in _OPEN_EVENT_STATUSES),
            "impacts": sum(1 for item in stream if item["impact"] is not None),
            "actions": sum(1 for item in stream if item["proposed_action"] is not None),
        },
    }


def guardian_stream_definition() -> dict[str, Any]:
    """OpenAI function schema; journey and mission scope are server-bound."""
    return {
        "type": "function",
        "function": {
            "name": "read_guardian_stream",
            "description": "Read the current Journey's persisted Guardian observations, impacts, and proposed actions.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
                "additionalProperties": False,
            },
        },
    }
