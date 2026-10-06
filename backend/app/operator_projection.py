"""User-facing Autonomous Journey Operator projection over durable domain truth."""
from __future__ import annotations

import json
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agent.operator_brain import (
    find_recovery_resume,
    operator_brain_state,
    resume_projection,
    runtime_candidates_for_session,
)
from app.core.config import settings
from app.db.models import (
    ActionApproval,
    AgentPendingAction,
    AgentRun,
    AutopilotEnrollment,
    AuditLog,
    Event,
    GuardianRun,
    Journey,
    JourneyMission,
    ReplanProposal,
    RecoveryDiscoveryAttempt,
    RecoveryExecutionPlan,
    RecoveryEpoch,
)
from app.agent.transactional_operator import execution_plan_projection
from app.execution.continuous_journey import continuous_flow_projection
from app.agent.journey_ahead import journey_ahead_projection
from app.agent.overnight_steward import overnight_steward_projection
from app.agent.journey_intent import active_journey_intents, pending_journey_intent_clarifications
from app.execution.clock import execution_clock
from app.operator_attention import attention_from_operator_projection


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
    if guardian_action_status == "OPERATOR_EXTERNAL_AGENT_BLOCKED":
        return "DEGRADED"
    if pending_status == "RESUMING":
        return "APPLYING"
    if approval_status == "REJECTED":
        return "NEEDS_ATTENTION"
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


def _timeline(session: Session, journey_id: str) -> list[dict[str, Any]]:
    """Turn durable audits into a compact traveller-facing story."""

    rows = session.scalars(
        select(AuditLog)
        .where(AuditLog.journey_id == journey_id)
        .order_by(AuditLog.created_at, AuditLog.id)
    ).all()
    items: list[dict[str, Any]] = []
    for row in rows:
        after = _json(row.after_json, {})
        if not isinstance(after, dict):
            after = {}
        label: str | None = None
        if row.action == "operator.started":
            label = "Watching your trip"
        elif row.action == "operator.stopped":
            label = "Journey Operator paused"
        elif row.action == "city.signal.incident.created":
            label = f"Detected: {str(after.get('event_type') or 'a trip change').replace('_', ' ').title()}"
        elif row.action in {"guardian.mission.compiled", "guardian.scan.started"}:
            label = "Working on a recovery"
        elif row.action == "agent.action_approval.created":
            label = "Waiting for your approval"
        elif row.action == "agent.action_approval.approved":
            label = "Approved"
        elif row.action == "replan.accepted":
            label = "Plan updated"
        elif row.action == "agent.pending_action.resumed":
            label = "Watching your trip again"
        elif row.action == "operator.external_agent_blocked":
            label = "CityNexus could not reach its trip Agent"
        elif row.action == "agent.recovery_discovery.started":
            label = "I’m looking for more recovery options nearby"
        elif row.action == "agent.recovery_discovery.completed":
            label = (
                "I found new places to check"
                if int(after.get("raw_candidate_count") or 0) > 0
                else "I couldn’t find another grounded option"
            )
        if label is None:
            continue
        items.append({"at": row.created_at, "label": label, "kind": row.action})
    return items[-12:]


def operator_projection(
    session: Session,
    journey: Journey,
    *,
    viewer_member_id: str | None = None,
) -> dict[str, Any]:
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
    open_event = None
    for candidate in session.scalars(
        select(Event)
        .where(
            Event.journey_id == journey.id,
            Event.status.in_(("DETECTED", "ACKNOWLEDGED")),
            Event.event_type.in_(("WEATHER", "CLOSURE", "TRAFFIC_DELAY", "SCHEDULE_DELAY")),
        )
        .order_by(Event.detected_at.desc(), Event.id.desc())
    ).all():
        try:
            if bool(json.loads(candidate.payload_json or "{}").get("predictive_only")):
                continue
        except (TypeError, json.JSONDecodeError):
            pass
        open_event = candidate
        break

    enabled = bool(enrollment is not None and enrollment.enabled)
    mission_active = standing is not None
    active_plan_changed = bool(
        guardian is not None
        and guardian.active_plan_before_id
        and journey.active_plan_version_id
        and str(guardian.active_plan_before_id) != str(journey.active_plan_version_id)
    )
    degraded = bool(enrollment is not None and enrollment.last_error)

    # A continuation is a short-lived recovered transition. Once the next
    # Guardian pulse is recorded, the same Journey is back in WATCHING.
    resumed_audit = session.scalar(
        select(AuditLog)
        .where(
            AuditLog.journey_id == journey.id,
            AuditLog.action == "agent.pending_action.resumed",
        )
        .order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
    )
    recovered_transition = bool(
        resumed_audit is not None
        and (
            enrollment is None
            or not enrollment.last_pulse_at
            or str(enrollment.last_pulse_at) <= str(resumed_audit.created_at)
        )
    )
    projected_guardian_action = guardian.action_status if guardian else None
    projected_pending_status = pending.status if pending else None
    if not recovered_transition and projected_pending_status == "RESUMED":
        projected_pending_status = None
    if not recovered_transition and projected_guardian_action == "EXECUTED":
        projected_guardian_action = None

    state = classify_operator_state(
        enabled=enabled,
        mission_active=mission_active,
        guardian_status=guardian.status if guardian else None,
        guardian_action_status=projected_guardian_action,
        agent_status=agent.status if agent else None,
        pending_status=projected_pending_status,
        approval_status=approval.status if approval else None,
        material_event_open=open_event is not None,
        active_plan_changed=active_plan_changed,
        degraded=degraded,
    )

    runtime_candidates = runtime_candidates_for_session(session, settings)
    recovery_epoch_id = (
        guardian.recovery_epoch_id
        if guardian is not None and guardian.recovery_epoch_id
        else session.scalar(
            select(RecoveryEpoch.id)
            .where(
                RecoveryEpoch.journey_id == journey.id,
                RecoveryEpoch.status == "OPEN",
            )
            .order_by(RecoveryEpoch.generation.desc())
        )
    )
    resume = find_recovery_resume(
        session, journey_id=journey.id, recovery_epoch_id=recovery_epoch_id
    )
    brain = operator_brain_state(
        configured_candidates=runtime_candidates,
        selected_runtime=(
            resume.provider_key
            if resume is not None
            and any(
                candidate.key == str(resume.provider_key)
                and candidate.configured
                for candidate in runtime_candidates
            )
            else None
        ),
        active_agent_status=agent.status if agent else None,
        blocked_recovery_pending=bool(
            resume is not None and resume.status in {"PENDING", "RUNNING"}
        ),
        last_failure_reason=(resume.failure_classification if resume is not None else None),
        safe_to_resume=bool(resume is not None and resume.safe_to_resume),
    )
    brain["recovery_resume"] = resume_projection(resume)

    discovery_rows = (
        session.scalars(
            select(RecoveryDiscoveryAttempt)
            .where(
                RecoveryDiscoveryAttempt.journey_id == journey.id,
                RecoveryDiscoveryAttempt.recovery_epoch_id == recovery_epoch_id,
            )
            .order_by(RecoveryDiscoveryAttempt.created_at, RecoveryDiscoveryAttempt.id)
        ).all()
        if recovery_epoch_id
        else []
    )
    latest_discovery = discovery_rows[-1] if discovery_rows else None
    discovery_state = "IDLE"
    if latest_discovery is not None:
        if latest_discovery.status == "DEGRADED":
            discovery_state = "DISCOVERY_DEGRADED"
        elif len(discovery_rows) >= 2 and latest_discovery.raw_candidate_count == 0:
            discovery_state = "DISCOVERY_EXHAUSTED"
        else:
            discovery_state = "DISCOVERY_IN_PROGRESS"
    discovery = {
        "state": discovery_state,
        "attempt_count": len(discovery_rows),
        "max_attempts": 2,
        "raw_candidate_count": latest_discovery.raw_candidate_count if latest_discovery else 0,
        "materialized_place_count": (
            len(_json(latest_discovery.materialized_place_ids_json, []))
            if latest_discovery is not None
            else 0
        ),
        "provider_mode": latest_discovery.provider_mode if latest_discovery else None,
        "runtime_provenance": latest_discovery.runtime_provenance if latest_discovery else None,
        "query": latest_discovery.query if latest_discovery else None,
    }

    execution_plan = session.scalar(
        select(RecoveryExecutionPlan)
        .where(RecoveryExecutionPlan.journey_id == journey.id)
        .order_by(RecoveryExecutionPlan.updated_at.desc(), RecoveryExecutionPlan.id.desc())
    )
    operations = None
    if execution_plan is not None:
        raw_operations = execution_plan_projection(session, execution_plan)
        actions = raw_operations.get("actions") or []
        done = sum(1 for item in actions if item.get("status") in {"CONFIRMED", "CANCELLED", "SUCCEEDED"})
        operations = {
            "plan_id": raw_operations["id"],
            "status": raw_operations["status"],
            "planned_action_count": len(actions),
            "completed_action_count": done,
            "approval_id": raw_operations.get("approval_id"),
            "provider_label": next((item.get("provider_label") for item in actions if item.get("provider_label")), None),
            "actions": [
                {
                    "sequence_no": item["sequence_no"],
                    "kind": item["kind"],
                    "status": item["status"],
                    "provider_label": item.get("provider_label"),
                    "target_type": item["target_type"],
                }
                for item in actions
            ],
        }
        # A completed frozen saga is the stronger operational truth.  A
        # planning runtime may still be unavailable, but once all commerce
        # actions are terminal the Operator is safe to return to monitoring.
        if enabled and operations["status"] == "COMPLETED":
            state = "WATCHING"
        elif operations["status"] in {"PARTIALLY_APPLIED", "FAILED_SAFE", "NEEDS_ATTENTION"}:
            state = "NEEDS_ATTENTION"

    from app.collective_operator import collective_operator_projection

    collective = collective_operator_projection(
        session,
        journey,
        viewer_member_id=viewer_member_id,
    )
    timeline = [*_timeline(session, journey.id), *(collective.get("timeline") or [])]
    timeline.sort(key=lambda item: (str(item.get("at") or ""), str(item.get("kind") or "")))

    unresolved_collective = str(collective.get("state") or "") in {
        "MEDIATING", "COLLECTIVE_STALE", "NEEDS_ATTENTION"
    }
    unresolved_operations = bool(
        operations is not None
        and operations.get("status") in {"PARTIALLY_APPLIED", "FAILED_SAFE", "NEEDS_ATTENTION"}
    )
    activity_incident = bool(
        open_event is not None
        and journey.current_activity_id is not None
        and str(open_event.affected_activity_id or "") == str(journey.current_activity_id)
    )
    flow = continuous_flow_projection(
        session,
        journey,
        operator_needs_attention=bool(
            state == "NEEDS_ATTENTION"
            or unresolved_collective
            or unresolved_operations
            or (activity_incident and state in {"INVESTIGATING", "DEGRADED"})
        ),
    )
    # Journey Ahead is a read-only projection.  Reuse the already persisted
    # predictive Guardian/brain state, but never start a provider call or an
    # action from this GET path.
    prevention_status = None
    if guardian is not None and str(guardian.trigger_kind or "").upper() == "PREDICTIVE":
        predictive_action = str(guardian.action_status or "").upper()
        prevention_status = {
            "PLANNING": "PLANNING",
            "RUNNING": "PLANNING",
            "DISCOVERING": "DISCOVERING",
            "REQUIRE_CONFIRMATION": "WAITING_FOR_APPROVAL",
            "REQUIRE_STEP_UP": "WAITING_FOR_APPROVAL",
            "EXECUTED": "APPLIED",
        }.get(predictive_action)
    resume_projection_state = brain.get("recovery_resume") or {}
    ahead = journey_ahead_projection(
        session,
        journey,
        prevention_status=prevention_status,
        provider_degraded=degraded,
        brain_blocked=bool(
            resume_projection_state.get("pending")
            and not resume_projection_state.get("safe_to_resume")
        ),
    )
    viewer_traveler_id = journey.traveler_id
    if viewer_member_id:
        from app.db.models import JourneyMember

        viewer_member = session.get(JourneyMember, str(viewer_member_id))
        if viewer_member is not None and viewer_member.journey_id == journey.id:
            viewer_traveler_id = viewer_member.traveler_id
    overnight = overnight_steward_projection(
        session, journey, viewer_traveler_id=viewer_traveler_id
    )
    active_intents = active_journey_intents(
        session,
        journey,
        now=execution_clock.now(journey.timezone),
        traveler_id=viewer_traveler_id,
    )
    pending_intents = pending_journey_intent_clarifications(
        session, journey, traveler_id=viewer_traveler_id
    )
    projected_intents = sorted(
        [*active_intents, *pending_intents],
        key=lambda item: (str(item.get("created_at") or ""), str(item.get("id") or "")),
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
    if approval_payload is None and execution_plan is not None and execution_plan.approval_id:
        execution_approval = session.get(ActionApproval, execution_plan.approval_id)
        if execution_approval is not None and execution_approval.status in {"PENDING", "APPROVED"}:
            approval_payload = {
                "required": True,
                "approval_id": execution_approval.id,
                "status": execution_approval.status,
                "action": execution_approval.action,
                "target_type": execution_approval.target_type,
                "target_id": execution_approval.target_id,
                "pending_action_id": None,
                "action_label": "Approve reservation work",
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
            "changes": {
                "removed": proposal_diff.get("removed", []),
                "added": proposal_diff.get("added", []),
                "moved": proposal_diff.get("moved", []),
            },
            "protected_commitments_preserved": bool(
                proposal.locked_commitments_preserved
            ),
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
        "brain": brain,
        "discovery": discovery,
        "operations": operations,
        "flow": flow,
        "ahead": ahead,
        "overnight": overnight,
        "intents": projected_intents,
        "attention": attention_from_operator_projection({
            "operations": operations,
            "approval": approval_payload,
            "collective": collective,
            "intents": projected_intents,
            "flow": flow,
            "overnight": overnight,
            "brain": brain,
        }),
        "quiet_mode": "QUIET",
        "collective": collective,
        "timeline": timeline[-12:],
        "advanced": {
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
            "recovered_transition": recovered_transition,
        },
        "operator": {
            "watching": enabled,
            "will_continue_after_approval": bool(
                approval_payload is not None and pending is not None
            ),
        },
        "active_plan_version_id": journey.active_plan_version_id,
    }
