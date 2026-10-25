"""Run-bound, read-only projection for the classroom Presenter.

Only persisted envelopes are evidence of execution. Configuration is reported
separately and reading this projection never starts a provider or model call.
"""

import json

from fastapi import HTTPException
from sqlalchemy import select

from app.agent.tool_catalog import RUNTIME_MCP_ALLOWLIST_V2
from app.db.models import (
    AgentRun,
    AgentRunStep,
    AuditLog,
    Event,
    GuardianRun,
    JourneyMission,
    ReplanProposal,
)

STEP_STATUSES = frozenset(
    {
        "RUNNING",
        "COMPLETED",
        "FAILED",
        "FAILED_EXTERNAL",
        "TOOL_ERROR",
        "SUPERSEDED",
        "PENDING_APPROVAL",
        "WAITING_APPROVAL",
        "BLOCKED",
        "SKIPPED",
    }
)
AGENT_STATUSES = frozenset(
    {
        "RUNNING",
        "COMPLETED",
        "PARTIAL",
        "FAILED",
        "FAILED_EXTERNAL",
        "INTERRUPTED",
        "SUPERSEDED",
        "PENDING_APPROVAL",
        "WAITING_APPROVAL",
        "BLOCKED",
        "SKIPPED_EXTERNAL_DEPENDENCY",
    }
)
GUARDIAN_ACTIONS = frozenset(
    {
        "NO_ACTION",
        "MISSION_REQUIRED",
        "PLANNING",
        "PROPOSAL_PRESENTED",
        "REQUIRE_CONFIRMATION",
        "EXECUTED",
        "MODEL_NO_ACTION",
        "UNRESOLVED",
        "RETRYABLE_FAILURE",
        "NO_FEASIBLE_RECOVERY",
        "OPERATOR_BRAIN_UNSAFE_TO_FAILOVER",
        "OPERATOR_EXTERNAL_AGENT_BLOCKED",
        "PARTIAL",
    }
)


def scene_event(session, journey, run, event_id):
    event = session.get(Event, event_id) if event_id else None
    if (
        event is None
        or event.journey_id != journey.id
        or event.provenance != "SIMULATED"
        or json.loads(event.payload_json or "{}").get("simulation_run_id") != run.id
    ):
        raise HTTPException(409, "SIMULATION_SCENE_EVENT_MISMATCH")
    return event


def known(value, allowed):
    return value if value in allowed else "UNKNOWN"


def run_progress(session, journey, run, config):
    history = json.loads(run.history_json)
    state = json.loads(run.state_json)
    event_ids = {
        item["event_id"]
        for item in history
        if item.get("event") == "SIM_SCENE_INJECTED" and item.get("event_id")
    }
    events = [scene_event(session, journey, run, eid) for eid in sorted(event_ids)]
    pending = next((event for event in events if event.id == state.get("pending_event_id")), None)
    guardians = (
        list(
            session.scalars(
                select(GuardianRun)
                .where(
                    GuardianRun.journey_id == journey.id,
                    GuardianRun.trigger_event_id.in_(event_ids),
                )
                .order_by(GuardianRun.created_at, GuardianRun.id)
            )
        )
        if event_ids
        else []
    )
    # A model runtime commits AgentRun before Guardian gets its final run ID.
    # The child mission's exact event binding makes those in-flight rows visible.
    agents = (
        list(
            session.scalars(
                select(AgentRun)
                .join(JourneyMission, JourneyMission.id == AgentRun.mission_id)
                .where(
                    AgentRun.journey_id == journey.id,
                    JourneyMission.journey_id == journey.id,
                    JourneyMission.trigger_event_id.in_(event_ids),
                    JourneyMission.is_standing.is_(False),
                )
                .order_by(AgentRun.created_at, AgentRun.id)
            )
        )
        if event_ids
        else []
    )
    agent_ids = {agent.id for agent in agents}
    steps = (
        list(
            session.scalars(
                select(AgentRunStep)
                .where(AgentRunStep.run_id.in_(agent_ids))
                .order_by(AgentRunStep.run_id, AgentRunStep.sequence_no, AgentRunStep.id)
            )
        )
        if agent_ids
        else []
    )
    proposal_ids = {g.proposal_id for g in guardians if g.proposal_id}
    proposals = (
        list(
            session.scalars(
                select(ReplanProposal)
                .where(
                    ReplanProposal.journey_id == journey.id,
                    ReplanProposal.trigger_event_id.in_(event_ids),
                    ReplanProposal.id.in_(proposal_ids),
                )
                .order_by(ReplanProposal.created_at, ReplanProposal.id)
            )
        )
        if proposal_ids
        else []
    )
    acceptances = (
        list(
            session.scalars(
                select(AuditLog)
                .where(
                    AuditLog.journey_id == journey.id,
                    AuditLog.action == "replan.accepted",
                    AuditLog.entity_type == "ReplanProposal",
                    AuditLog.entity_id.in_({p.id for p in proposals}),
                    AuditLog.actor_type == "AUTHENTICATED_TRAVELER",
                    AuditLog.actor_id.is_not(None),
                )
                .order_by(AuditLog.created_at, AuditLog.id)
            )
        )
        if proposals
        else []
    )
    standing = session.scalar(
        select(JourneyMission.id)
        .where(
            JourneyMission.journey_id == journey.id,
            JourneyMission.is_standing.is_(True),
            JourneyMission.status == "ACTIVE",
        )
        .limit(1)
    )
    configured = bool((config.hermes_api_url and config.hermes_api_key) or config.ai_api_key)
    missing = []
    if not configured:
        missing.append("MODEL_CREDENTIALS_MISSING")
    if not standing:
        missing.append("STANDING_MISSION_REQUIRED")
    if pending is None or pending.status not in {"DETECTED", "ACKNOWLEDGED"}:
        missing.append("OPEN_SCENE_EVENT_REQUIRED")
    if run.status not in {
        "PAUSED_FOR_GUARDIAN",
        "PAUSED_MODEL_UNAVAILABLE",
        "PAUSED_REQUIRES_MISSION",
    }:
        missing.append("RUN_NOT_AWAITING_GUARDIAN")
    return {
        "run_id": run.id,
        "journey_id": journey.id,
        "sequence": run.sequence,
        "status": run.status,
        "virtual_now": run.virtual_now,
        "current_active_plan_version_id": journey.active_plan_version_id,
        "current_activity_id": journey.current_activity_id,
        "clock_policy": {"business": "PERSISTED_VIRTUAL", "security_and_audit": "WALL"},
        "readiness": {
            "model_credentials_configured": configured,
            "standing_mission_id": standing,
            "pending_event_id": pending.id if pending else None,
            "missing": missing,
            "model_consent_required": True,
            "network_checked": False,
        },
        "events": [
            {
                "id": e.id,
                "event_type": known(e.event_type, {"CLOSURE", "WEATHER", "SCHEDULE_DELAY"}),
                "status": known(e.status, {"DETECTED", "ACKNOWLEDGED", "RESOLVED", "IGNORED"}),
                "provenance": "SIMULATED",
                "occurred_at": e.occurred_at,
            }
            for e in events
        ],
        "guardian_runs": [
            {
                "id": g.id,
                "event_id": g.trigger_event_id,
                "status": known(
                    g.status, {"RUNNING", "COMPLETED", "INTERRUPTED", "ABORTED", "FAILED"}
                ),
                "action_status": known(g.action_status, GUARDIAN_ACTIONS),
                "agent_run_id": g.agent_run_id if g.agent_run_id in agent_ids else None,
                "proposal_id": g.proposal_id
                if g.proposal_id in {p.id for p in proposals}
                else None,
                "created_at": g.created_at,
                "completed_at": g.completed_at,
            }
            for g in guardians
        ],
        "agent_runs": [
            {
                "id": a.id,
                "status": known(a.status, AGENT_STATUSES),
                "created_at": a.created_at,
                "completed_at": a.completed_at,
            }
            for a in agents
        ],
        "steps": [
            {
                "id": step.id,
                "agent_run_id": step.run_id,
                "sequence": step.sequence_no,
                "tool_name": step.tool_name
                if step.tool_name
                in RUNTIME_MCP_ALLOWLIST_V2 | {"external_model_call", "recovery_epoch_guard"}
                else "unlisted_tool",
                "status": known(step.status, STEP_STATUSES),
                "error_code": "MODEL_REQUEST_FAILED"
                if step.status == "FAILED_EXTERNAL"
                else "TOOL_CALL_FAILED"
                if step.status == "TOOL_ERROR"
                else None,
                "created_at": step.created_at,
                "completed_at": step.completed_at,
            }
            for step in steps
        ],
        "proposals": [
            {
                "id": p.id,
                "status": known(
                    p.status, {"PRESENTED", "ACCEPTED", "REJECTED", "SUPERSEDED", "EXPIRED"}
                ),
                "proposed_plan_version_id": p.proposed_plan_version_id,
                "acceptance_audit_ids": [a.id for a in acceptances if a.entity_id == p.id],
            }
            for p in proposals
        ],
    }
