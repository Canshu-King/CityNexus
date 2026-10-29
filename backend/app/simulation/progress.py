"""Run-bound, read-only projection for the classroom Presenter.

Only persisted envelopes are evidence of execution. Configuration is reported
separately and reading this projection never starts a provider or model call.
"""

import json
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from fastapi import HTTPException
from sqlalchemy import select

from app.agent.tool_catalog import RUNTIME_MCP_ALLOWLIST_V2
from app.db.models import (
    AgentRun,
    AgentRunStep,
    AuditLog,
    Activity,
    Event,
    GuardianRun,
    JourneyMission,
    ReplanProposal,
    PlanVersion,
    Place,
)
from app.simulation.coverage import (
    resolve_run_completed_activity_ids,
    summarize_activity_coverage,
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


def _step_duration_ms(started_at, completed_at):
    if not started_at or not completed_at:
        return None
    try:
        duration = datetime.fromisoformat(completed_at) - datetime.fromisoformat(started_at)
    except (TypeError, ValueError):
        return None
    milliseconds = int(duration.total_seconds() * 1000)
    return milliseconds if milliseconds >= 0 else None


def _step_failure_classification(status):
    if status == "FAILED_EXTERNAL":
        return "MODEL_REQUEST_FAILED"
    if status == "TOOL_ERROR":
        return "TOOL_CALL_FAILED"
    return None


def _guardian_outcome(
    *,
    journey_id,
    current_event_id,
    current_event_status,
    configured,
    guardians,
    agents,
    agent_event_ids,
    steps,
    proposals,
):
    """Classify the latest Guardian attempt for this run's current or last scene event."""

    def outcome(code, error_code=None):
        result = {"code": code}
        if error_code is not None:
            result["error_code"] = error_code
        return result

    if not current_event_id:
        return outcome("UNKNOWN")

    event_guardians = [
        guardian
        for guardian in guardians
        if guardian.journey_id == journey_id
        and guardian.trigger_event_id == current_event_id
    ]
    current_guardian = event_guardians[-1] if event_guardians else None
    event_agents = [
        agent
        for agent in agents
        if agent.journey_id == journey_id
        and agent_event_ids.get(agent.id) == current_event_id
    ]
    current_agent = None
    current_source_agent = None
    if current_guardian is not None:
        current_source_agent = next(
            (
                agent
                for agent in event_agents
                if agent.id == current_guardian.agent_run_id
            ),
            None,
        )
        current_agent = current_source_agent
        if current_agent is None:
            recent_attempts = [
                agent
                for agent in event_agents
                if agent.created_at >= current_guardian.created_at
            ]
            if recent_attempts:
                current_agent = recent_attempts[-1]
    elif event_agents:
        current_agent = event_agents[-1]

    current_proposal = None
    if current_guardian is not None and current_guardian.proposal_id:
        current_proposal = next(
            (
                proposal
                for proposal in proposals
                if proposal.id == current_guardian.proposal_id
                and proposal.journey_id == journey_id
                and proposal.trigger_event_id == current_event_id
            ),
            None,
        )
    if current_proposal is not None and current_proposal.status == "PRESENTED":
        return outcome("PROPOSAL_READY")

    current_steps = [
        step for step in steps if current_agent is not None and step.run_id == current_agent.id
    ]
    if current_agent is not None and current_agent.status == "FAILED_EXTERNAL":
        return outcome("EXTERNAL_FAILED", "MODEL_REQUEST_FAILED")

    has_bound_accepted_proposal = (
        current_proposal is not None
        and current_proposal.status == "ACCEPTED"
        and current_event_status == "RESOLVED"
        and current_guardian is not None
        and current_proposal.source_agent_run_id == current_guardian.agent_run_id
        and current_source_agent is not None
    )
    if has_bound_accepted_proposal:
        return outcome("PROPOSAL_ACCEPTED")

    if any(step.status == "FAILED_EXTERNAL" for step in current_steps):
        return outcome("EXTERNAL_FAILED", "MODEL_REQUEST_FAILED")

    if (
        (current_guardian is not None and current_guardian.action_status == "UNRESOLVED")
        or (current_agent is not None and current_agent.status == "PARTIAL")
        or (current_guardian is not None and current_guardian.status == "PARTIAL")
    ):
        return outcome("AGENT_UNRESOLVED")

    if not configured and current_agent is None:
        return outcome("MODEL_NOT_CONFIGURED")
    return outcome("UNKNOWN")


def run_progress(session, journey, run, config):
    history = json.loads(run.history_json)
    state = json.loads(run.state_json)
    scene_event_ids = list(
        dict.fromkeys(
            item["event_id"]
            for item in history
            if item.get("event") == "SIM_SCENE_INJECTED" and item.get("event_id")
        )
    )
    event_ids = set(scene_event_ids)
    events = [scene_event(session, journey, run, eid) for eid in sorted(event_ids)]
    pending_event_id = state.get("pending_event_id")
    pending = next((event for event in events if event.id == pending_event_id), None)
    if pending_event_id:
        current_event_id = pending.id if pending is not None else None
    else:
        current_event_id = scene_event_ids[-1] if scene_event_ids else None
    current_event = next(
        (event for event in events if event.id == current_event_id), None
    )
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
    agent_rows = (
        list(
            session.execute(
                select(AgentRun)
                .add_columns(JourneyMission.trigger_event_id)
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
    agents = [row[0] for row in agent_rows]
    agent_event_ids = {row[0].id: row[1] for row in agent_rows}
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
    guardian_outcome = _guardian_outcome(
        journey_id=journey.id,
        current_event_id=current_event.id if current_event else None,
        current_event_status=current_event.status if current_event else None,
        configured=configured,
        guardians=guardians,
        agents=agents,
        agent_event_ids=agent_event_ids,
        steps=steps,
        proposals=proposals,
    )
    missing = []
    if not config.ai_enabled:
        missing.append("AI_DISABLED")
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
    active_plan = session.scalar(
        select(PlanVersion).where(
            PlanVersion.id == journey.active_plan_version_id,
            PlanVersion.journey_id == journey.id,
        )
    )
    activities = (
        list(session.scalars(select(Activity).where(Activity.plan_version_id == active_plan.id)))
        if active_plan is not None
        else []
    )
    state_completed_ids = {
        str(activity_id).strip()
        for activity_id in state.get("completed_activity_ids", [])
        if activity_id is not None and str(activity_id).strip()
    }
    history_completed_ids = {
        str(item.get("activity_id")).strip()
        for item in history
        if isinstance(item, dict)
        and item.get("event") == "SIM_ACTIVITY_COMPLETED"
        and item.get("activity_id") is not None
        and str(item.get("activity_id")).strip()
    }
    source_activity_ids = state_completed_ids & history_completed_ids
    source_activities = (
        list(
            session.scalars(
                select(Activity)
                .join(PlanVersion, Activity.plan_version_id == PlanVersion.id)
                .join(Place, Activity.place_id == Place.id)
                .where(
                    PlanVersion.journey_id == journey.id,
                    Activity.id.in_(source_activity_ids),
                )
            )
        )
        if source_activity_ids
        else []
    )
    completed_activity_ids = resolve_run_completed_activity_ids(
        run_id=run.id,
        run_sequence=run.sequence,
        run_actor_id=run.actor_id,
        history=history,
        source_activities=source_activities,
        active_activities=activities,
    )
    zone = ZoneInfo(journey.timezone)
    def local_date(value):
        stamp = datetime.fromisoformat(value)
        return (stamp.replace(tzinfo=zone) if stamp.tzinfo is None else stamp.astimezone(zone)).date()
    first_day, last_day = local_date(journey.start_at), local_date(journey.end_at)
    required_dates = [
        (first_day + timedelta(days=offset)).isoformat()
        for offset in range((last_day - first_day).days + 1)
    ]
    activity_coverage = {
        "plan_version_id": active_plan.id if active_plan is not None else None,
        "target_places_per_day": 2,
        "target_kind": "CLASSROOM_DISPLAY_ONLY",
        "days": summarize_activity_coverage(
            activities,
            completed_activity_ids,
            journey_timezone=journey.timezone,
            required_dates=required_dates,
        ),
    }
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
            "ai_enabled": config.ai_enabled,
            "model_credentials_configured": configured,
            "standing_mission_id": standing,
            "pending_event_id": pending.id if pending else None,
            "missing": missing,
            "model_consent_required": True,
            "network_checked": False,
        },
        "guardian_outcome": guardian_outcome,
        "activity_coverage": activity_coverage,
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
                    g.status,
                    {"RUNNING", "COMPLETED", "PARTIAL", "INTERRUPTED", "ABORTED", "FAILED"},
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
                "simulation_run_id": run.id,
                "event_id": agent_event_ids.get(step.run_id),
                "agent_run_id": step.run_id,
                "sequence": step.sequence_no,
                "stage": "TOOL_CALL",
                "tool_name": step.tool_name
                if step.tool_name
                in RUNTIME_MCP_ALLOWLIST_V2 | {"external_model_call", "recovery_epoch_guard"}
                else "unlisted_tool",
                "status": known(step.status, STEP_STATUSES),
                "failure_classification": _step_failure_classification(step.status),
                "error_code": _step_failure_classification(step.status),
                "duration_ms": _step_duration_ms(step.created_at, step.completed_at),
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
