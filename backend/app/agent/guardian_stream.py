"""Mission-level Guardian stream: observation -> impact -> proposed action.

The rows already exist: `Event` is the observation, `ImpactAssessment` is the
impact, `GuardianRun` is the proposed/executed action.  This module does not
invent a second truth store; it projects those rows into one typed stream so a
Mission canvas can render what actually happened.

If no watch has run, the answer is `WATCH_NOT_RUNNING`, not an empty success.
"""

from __future__ import annotations

import json
from typing import Any

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core import config
from app.db.models import Event, GuardianRun, ImpactAssessment, Journey, JourneyMission
from app.recovery_epoch import current_open_recovery_epoch

_OPEN_STATUSES = ("DETECTED", "ACKNOWLEDGED", "ACTIVE", "OPEN")
_OBSERVATION_KEYS = (
    "summary",
    "reason_code",
    "planned_local_interval",
    "context_resolution",
    "predictive_only",
    "source",
    "source_url",
)


def _load(value: str | None) -> dict[str, Any]:
    try:
        parsed = json.loads(value or "{}")
    except (TypeError, json.JSONDecodeError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _load_list(value: str | None) -> list[Any]:
    try:
        parsed = json.loads(value or "[]")
    except (TypeError, json.JSONDecodeError):
        return []
    return parsed if isinstance(parsed, list) else []


def _require_mission(session: Session, journey: Journey, mission_id: str | None) -> JourneyMission | None:
    if mission_id is None:
        return None
    mission = session.get(JourneyMission, str(mission_id))
    if mission is None or str(mission.journey_id) != str(journey.id):
        raise HTTPException(404, "JourneyMission was not found for this Journey")
    return mission


def _observation(event: Event) -> dict[str, Any]:
    payload = _load(event.payload_json)
    return {
        "id": event.id,
        "event_type": event.event_type,
        "severity": event.severity,
        "status": event.status,
        "provider": event.provider_key,
        "provenance": event.provenance,
        "detected_at": event.detected_at,
        "occurred_at": event.occurred_at,
        "resolved_at": event.resolved_at,
        "affected_activity_id": event.affected_activity_id,
        "evidence": {key: payload[key] for key in _OBSERVATION_KEYS if key in payload},
    }


def _impact(row: ImpactAssessment | None) -> dict[str, Any] | None:
    if row is None:
        return None
    return {
        "id": row.id,
        "status": row.status,
        "maturity_stage": row.maturity_stage,
        "uncertain": bool(row.uncertain),
        "independent_evidence_count": int(row.independent_evidence_count),
        "selected_activity_id": row.selected_activity_id,
        "primary_recovery_target_id": row.primary_recovery_target_id,
        "secondary_risk_activity_ids": _load_list(row.secondary_risk_activity_ids_json),
        "reason_codes": _load_list(row.reason_codes_json),
        "semantic_reason": row.semantic_reason,
        "failure_code": row.failure_code,
        "created_at": row.created_at,
    }


def recovery_epoch_payload(epoch: Any) -> dict[str, Any] | None:
    """The current open recovery reality, or None when no incident opened one."""

    if epoch is None:
        return None
    return {
        "id": epoch.id,
        "generation": int(epoch.generation),
        "status": epoch.status,
        "recovery_reality_fingerprint": epoch.recovery_reality_fingerprint,
        "active_plan_version_id_at_open": epoch.active_plan_version_id_at_open,
        "triggering_event_ids": _load_list(epoch.triggering_event_ids_json),
        "opened_at": epoch.opened_at,
        "closed_at": epoch.closed_at,
        "close_reason": epoch.close_reason,
    }


def _action(row: GuardianRun | None) -> dict[str, Any] | None:
    if row is None:
        return None
    return {
        "id": row.id,
        "decision": row.decision,
        "status": row.status,
        "action_status": row.action_status,
        "proposal_id": row.proposal_id,
        "agent_run_id": row.agent_run_id,
        "reasoning_summary": row.reasoning_summary,
        "trigger_kind": row.trigger_kind,
        "active_plan_before_id": row.active_plan_before_id,
        "active_plan_after_id": row.active_plan_after_id,
        "created_at": row.created_at,
        "completed_at": row.completed_at,
        "cooldown_until": row.cooldown_until,
    }


def guardian_stream(
    session: Session,
    journey: Journey,
    *,
    mission_id: str | None = None,
    limit: int = 20,
) -> dict[str, Any]:
    """Project the last events into one typed stream; never starts a watch."""

    mission = _require_mission(session, journey, mission_id)
    events = list(
        session.scalars(
            select(Event)
            .where(Event.journey_id == journey.id)
            .order_by(Event.detected_at.desc(), Event.id.desc())
            .limit(max(1, min(50, limit)))
        ).all()
    )
    runs = list(
        session.scalars(
            select(GuardianRun)
            .where(GuardianRun.journey_id == journey.id)
            .order_by(GuardianRun.created_at.desc(), GuardianRun.id.desc())
            .limit(max(1, min(50, limit)))
        ).all()
    )
    base: dict[str, Any] = {
        "tool": "read_guardian_stream",
        "journey_id": journey.id,
        "mission_id": mission.id if mission else None,
        "authority": "SERVER_OWNED_EVENTS",
        "watch": {
            "enabled": bool(config.settings.guardian_autorun),
            "last_observed_at": events[0].detected_at if events else None,
        },
        "recovery_epoch": recovery_epoch_payload(
            current_open_recovery_epoch(session, journey.id)
        ),
    }
    if not events and not runs:
        return {
            **base,
            "status": "WATCH_NOT_RUNNING",
            "reason_code": "NO_GUARDIAN_OBSERVATION",
            "stream": [],
            "counts": {"events": 0, "impacts": 0, "actions": 0},
            "next_legal_path": (
                "enable the live context watch and run one refresh; no event is "
                "invented while it has not run"
            ),
        }

    impact_by_event: dict[str, ImpactAssessment] = {}
    for row in session.scalars(
        select(ImpactAssessment)
        .where(ImpactAssessment.journey_id == journey.id)
        .order_by(ImpactAssessment.created_at.desc(), ImpactAssessment.id.desc())
    ).all():
        impact_by_event.setdefault(row.event_id, row)
    action_by_event: dict[str, GuardianRun] = {}
    for row in runs:
        if row.trigger_event_id:
            action_by_event.setdefault(row.trigger_event_id, row)

    stream = []
    for event in events:
        stream.append(
            {
                "observation": _observation(event),
                "impact": _impact(impact_by_event.get(event.id)),
                "proposed_action": _action(action_by_event.get(event.id)),
            }
        )
    open_events = sum(1 for event in events if event.status in _OPEN_STATUSES)
    return {
        **base,
        "status": "HAS_EVENTS",
        "stream": stream,
        "counts": {
            "events": len(events),
            "open_events": open_events,
            "impacts": sum(1 for item in stream if item["impact"] is not None),
            "actions": sum(1 for item in stream if item["proposed_action"] is not None),
        },
    }
