"""User-facing Autonomous Journey Operator projection over durable domain truth."""
from __future__ import annotations

import json
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import (
    ActionApproval,
    AgentPendingAction,
    AgentRun,
    AutopilotEnrollment,
    Event,
    GuardianRun,
    Journey,
    JourneyMission,
    ReplanProposal,
)


def classify_operator_state(
    *,
    enabled: bool,
    mission_active: bool,
    guardian_status: str | None = None,
    guardian_action_status: str | None = None,
    agent_status: str | None = None,
    pending_status: str | None = None,
    approval_status: str | None = None,
    material_event_open: bool = False,
    active_plan_changed: bool = False,
    degraded: bool = False,
) -> str:
    """Collapse existing durable states into one traveller-facing operator state."""

    if not enabled or not mission_active:
        return "OFF"
    if degraded:
        return "DEGRADED"
    if pending_status == "RESUMING":
        return "APPLYING"
    if (
        pending_status == "PENDING"
        and approval_status not in {"APPROVED", "CONSUMED"}
    ):
        return "WAITING_FOR_APPROVAL"
    if pending_status == "RESUMED" or (
        guardian_action_status == "EXECUTED" and active_plan_changed
    ):
        return "RECOVERED"
    if guardian_status == "RUNNING" or agent_status in {"RUNNING", "PLANNING"}:
        return "INVESTIGATING"
    if guardian_action_status in {"REQUIRE_CONFIRMATION", "REQUIRE_STEP_UP"}:
        return "WAITING_FOR_APPROVAL"
    if material_event_open:
        if guardian_action_status in {"NO_FEASIBLE_RECOVERY", "UNRESOLVED"}:
            return "NEEDS_ATTENTION"
        return "INVESTIGATING"
    if guardian_status in {"FAILED_RETRYABLE", "INTERRUPTED"} or agent_status in {
        "FAILED",
        "FAILED_EXTERNAL",
        "PARTIAL",
    }:
        return "DEGRADED"
    return "WATCHING"


def _json(value: str | None, fallback: Any) -> Any:
    try:
        return json.loads(value or "")
    except (TypeError, json.JSONDecodeError):
        return fallback


def operator_projection(session: Session, journey: Journey) -> dict[str, Any]:
    """Join Guardian/Agent/approval truth without creating a second control plane."""

    enrollment = session.get(AutopilotEnrollment, journey.id)
    standing = session.scalar(
        select(JourneyMission)
        .where(
            JourneyMission.journey_id == journey.id,
            JourneyMission.is_standing.is_(True),
            JourneyMission.status == "ACTIVE",
        )
        .order_by(JourneyMission.created_at.desc(), JourneyMission.id.desc())
    )
    guardian = session.scalar(
        select(GuardianRun)
        .where(GuardianRun.journey_id == journey.id)
        .order_by(GuardianRun.created_at.desc(), GuardianRun.id.desc())
    )
    agent = (
        session.get(AgentRun, guardian.agent_run_id)
        if guardian is not None and guardian.agent_run_id
        else None
    )
    pending = (
        session.scalar(
            select(AgentPendingAction)
            .where(
                AgentPendingAction.journey_id == journey.id,
                AgentPendingAction.run_id == agent.id,
                AgentPendingAction.status.in_(
                    ("PENDING", "RESUMING", "RESUMED", "FAILED", "SUPERSEDED")
                ),
            )
            .order_by(AgentPendingAction.updated_at.desc(), AgentPendingAction.id.desc())
        )
        if agent is not None
        else None
    )
    approval = (
        session.get(ActionApproval, pending.approval_id)
        if pending is not None
        else None
    )
    proposal = (
        session.get(ReplanProposal, guardian.proposal_id)
        if guardian is not None and guardian.proposal_id
        else None
    )
    open_event = session.scalar(
        select(Event)
        .where(
            Event.journey_id == journey.id,
            Event.status.in_(("DETECTED", "ACKNOWLEDGED")),
            Event.event_type.in_(("WEATHER", "CLOSURE", "TRAFFIC_DELAY", "SCHEDULE_DELAY")),
        )
        .order_by(Event.detected_at.desc(), Event.id.desc())
    )

    enabled = bool(enrollment is not None and enrollment.enabled)
    mission_active = standing is not None
    active_plan_changed = bool(
        guardian is not None
        and guardian.active_plan_before_id
        and journey.active_plan_version_id
        and str(guardian.active_plan_before_id) != str(journey.active_plan_version_id)
    )
    degraded = bool(enrollment is not None and enrollment.last_error)

    state = classify_operator_state(
        enabled=enabled,
        mission_active=mission_active,
        guardian_status=guardian.status if guardian else None,
        guardian_action_status=guardian.action_status if guardian else None,
        agent_status=agent.status if agent else None,
        pending_status=pending.status if pending else None,
        approval_status=approval.status if approval else None,
        material_event_open=open_event is not None,
        active_plan_changed=active_plan_changed,
        degraded=degraded,
    )

    proposal_diff = _json(proposal.diff_json, {}) if proposal is not None else {}
    approval_payload = None
    if approval is not None and pending is not None and pending.status in {"PENDING", "RESUMING"}:
        approval_payload = {
            "required": True,
            "approval_id": approval.id,
            "status": approval.status,
            "action": approval.action,
            "target_type": approval.target_type,
            "target_id": approval.target_id,
            "pending_action_id": pending.id,
            "action_label": "Approve change",
        }

    incident = (
        {
            "id": open_event.id,
            "kind": open_event.event_type,
            "severity": open_event.severity,
            "activity_id": open_event.affected_activity_id,
            "provenance": open_event.provenance,
        }
        if open_event is not None
        else None
    )
    decision = (
        {
            "proposal_id": proposal.id,
            "status": proposal.status,
            "summary": proposal_diff.get("summary")
            or proposal_diff.get("explanation")
            or (guardian.reasoning_summary if guardian else None),
            "cost_delta_minor": proposal_diff.get("cost_delta_minor"),
            "schedule_delta_min": proposal_diff.get("end_time_delta_min"),
        }
        if proposal is not None
        else None
    )

    headlines = {
        "OFF": "Journey Operator is off.",
        "WATCHING": "I’m watching your trip.",
        "INVESTIGATING": "I noticed a change and I’m working out what to do.",
        "WAITING_FOR_APPROVAL": "I found a recovery and need your approval.",
        "APPLYING": "Applying the change you approved.",
        "RECOVERED": "Change applied. I’m watching the trip again.",
        "NEEDS_ATTENTION": "I found a problem but could not safely resolve it.",
        "DEGRADED": "Journey Operator needs attention.",
    }

    return {
        "journey_id": journey.id,
        "state": state,
        "headline": headlines[state],
        "enabled": enabled,
        "standing_mission_id": standing.id if standing else None,
        "autonomy": standing.requested_autonomy if standing else None,
        "incident": incident,
        "decision": decision,
        "approval": approval_payload,
        "guardian": (
            {
                "run_id": guardian.id,
                "status": guardian.status,
                "action_status": guardian.action_status,
                "agent_run_id": guardian.agent_run_id,
            }
            if guardian is not None
            else None
        ),
        "agent": (
            {
                "run_id": agent.id,
                "provider_key": agent.provider_key,
                "model_key": agent.model_key,
                "status": agent.status,
            }
            if agent is not None
            else None
        ),
        "operator": {
            "watching": enabled,
            "will_continue_after_approval": bool(
                approval_payload is not None and pending is not None
            ),
        },
        "active_plan_version_id": journey.active_plan_version_id,
    }
