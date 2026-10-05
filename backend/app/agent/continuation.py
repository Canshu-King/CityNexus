from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.audit import record_audit
from app.db.models import (
    ActionApproval,
    AgentPendingAction,
    AgentRun,
    AgentRunStep,
    Journey,
    JourneyMission,
    ReplanProposal,
)
from app.schemas import AgentToolCall


_APPROVAL_DECISIONS = {"REQUIRE_CONFIRMATION", "REQUIRE_STEP_UP"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _json_text(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)


def approval_waiting(result: Any) -> bool:
    """True only for a server-issued approval boundary that has not executed."""

    return (
        isinstance(result, dict)
        and result.get("executed") is not True
        and str(result.get("decision") or "") in _APPROVAL_DECISIONS
        and bool(result.get("approval_id"))
    )


def capture_pending_action(
    session: Session,
    *,
    run: AgentRun,
    mission: JourneyMission,
    step: AgentRunStep,
    tool_name: str,
    arguments: dict[str, Any],
    result: dict[str, Any],
) -> AgentPendingAction | None:
    """Persist the exact Agent-selected action before the model is suspended.

    The model has already decided *what* to do.  Human approval is the only
    missing fact, so the continuation stores server-owned canonical arguments
    and does not ask the model to rediscover the action later.
    """

    if not approval_waiting(result):
        return None
    approval_id = str(result["approval_id"])
    existing = session.scalar(
        select(AgentPendingAction).where(AgentPendingAction.approval_id == approval_id)
    )
    if existing is not None:
        run.status = "WAITING_FOR_APPROVAL"
        mission.status = "WAITING_FOR_APPROVAL"
        run.completed_at = None
        mission.completed_at = None
        return existing

    now = _now()
    canonical_arguments = dict(arguments)
    # A pending continuation is created before approval exists on the resumed
    # call.  Never persist a caller-supplied approval id as action authority.
    canonical_arguments.pop("approval_id", None)
    pending = AgentPendingAction(
        id=str(uuid4()),
        approval_id=approval_id,
        run_id=run.id,
        mission_id=mission.id,
        journey_id=run.journey_id,
        originating_step_id=step.id,
        tool_name=tool_name,
        arguments_json=_json_text(canonical_arguments),
        status="PENDING",
        result_json="{}",
        error_json="{}",
        created_at=now,
        updated_at=now,
    )
    session.add(pending)
    run.status = "WAITING_FOR_APPROVAL"
    run.completed_at = None
    mission.status = "WAITING_FOR_APPROVAL"
    mission.completed_at = None
    record_audit(
        session,
        action="agent.pending_action.created",
        entity_type="AgentPendingAction",
        entity_id=pending.id,
        journey_id=run.journey_id,
        actor_type="AI_AGENT",
        actor_id=str(canonical_arguments.get("agent_id") or "citynexus-agent"),
        after={
            "pending_action_id": pending.id,
            "approval_id": approval_id,
            "run_id": run.id,
            "mission_id": mission.id,
            "tool": tool_name,
            "status": pending.status,
        },
    )
    session.flush()
    return pending


def _next_sequence(session: Session, run_id: str) -> int:
    current = session.scalar(
        select(func.max(AgentRunStep.sequence_no)).where(AgentRunStep.run_id == run_id)
    )
    return int(current or 0) + 1


def _append_resume_step(
    session: Session,
    *,
    pending: AgentPendingAction,
    arguments: dict[str, Any],
    result: dict[str, Any],
    status: str,
) -> AgentRunStep:
    now = _now()
    step = AgentRunStep(
        id=str(uuid4()),
        run_id=pending.run_id,
        sequence_no=_next_sequence(session, pending.run_id),
        tool_name=pending.tool_name,
        arguments_json=_json_text(arguments),
        result_json=_json_text(result),
        decision=str(result.get("decision")) if result.get("decision") is not None else None,
        status=status,
        created_at=now,
        completed_at=now,
    )
    session.add(step)
    return step


def _already_applied_accept_replan(
    session: Session,
    *,
    pending: AgentPendingAction,
    arguments: dict[str, Any],
    approval_id: str,
) -> dict[str, Any] | None:
    """Recover truth after a crash that happened after mutation commit.

    accept_replan can commit the authoritative plan transition before the outer
    continuation row is marked RESUMED.  In that narrow window the approval is
    already CONSUMED, so blindly consuming it again would turn a successful
    mutation into a permanent 409.  Reconstruct success only from durable
    proposal + Journey truth; never from an optimistic local flag.
    """

    if pending.tool_name != "accept_replan":
        return None
    proposal_id = str(arguments.get("proposal_id") or "")
    if not proposal_id:
        return None
    proposal = session.get(ReplanProposal, proposal_id)
    if proposal is None or proposal.journey_id != pending.journey_id:
        return None
    journey = session.get(Journey, pending.journey_id)
    if (
        journey is None
        or proposal.status != "ACCEPTED"
        or journey.active_plan_version_id != proposal.proposed_plan_version_id
    ):
        return None
    return {
        "tool": "accept_replan",
        "decision": "REQUIRE_CONFIRMATION",
        "executed": True,
        "approval_id": approval_id,
        "status": "CONSUMED",
        "proposal_id": proposal.id,
        "result": {
            "status": "ACCEPTED",
            "proposal": {
                "id": proposal.id,
                "status": proposal.status,
                "proposed_plan_version_id": proposal.proposed_plan_version_id,
            },
            "journey": {
                "id": journey.id,
                "active_plan_version_id": journey.active_plan_version_id,
            },
        },
        "continuation_recovered_from_domain_truth": True,
    }


def reconcile_approved_pending_actions(
    session: Session,
    *,
    limit: int = 50,
) -> dict[str, int]:
    """Finish approved continuations that survived a process restart."""

    rows = session.scalars(
        select(AgentPendingAction)
        .where(AgentPendingAction.status.in_(("PENDING", "RESUMING")))
        .order_by(AgentPendingAction.created_at, AgentPendingAction.id)
        .limit(max(1, int(limit)))
    ).all()
    resumed = 0
    waiting = 0
    failed = 0
    for pending in rows:
        approval = session.get(ActionApproval, pending.approval_id)
        if approval is None or approval.status not in {"APPROVED", "CONSUMED"}:
            waiting += 1
            continue
        outcome = resume_pending_action(session, approval_id=pending.approval_id)
        if outcome is None:
            failed += 1
        elif outcome.get("status") == "RESUMED":
            resumed += 1
        elif outcome.get("status") == "FAILED":
            failed += 1
        else:
            waiting += 1
    return {"resumed": resumed, "waiting": waiting, "failed": failed}


def resume_pending_action(
    session: Session,
    *,
    approval_id: str,
) -> dict[str, Any] | None:
    """Resume an Agent-selected action after the human approval is durable.

    The deterministic request id makes repeated approve requests converge on
    the Gateway's existing idempotency boundary.  No new model call is made.
    """

    pending = session.scalar(
        select(AgentPendingAction).where(AgentPendingAction.approval_id == approval_id)
    )
    if pending is None:
        return None

    approval = session.get(ActionApproval, approval_id)
    if approval is None:
        return {
            "status": "FAILED",
            "pending_action_id": pending.id,
            "reason": "APPROVAL_NOT_FOUND",
        }
    if pending.status == "RESUMED":
        try:
            result = json.loads(pending.result_json or "{}")
        except json.JSONDecodeError:
            result = {}
        return {
            "status": "RESUMED",
            "pending_action_id": pending.id,
            "run_id": pending.run_id,
            "mission_id": pending.mission_id,
            "result": result,
            "replayed": True,
        }
    if approval.status not in {"APPROVED", "CONSUMED"}:
        return {
            "status": "WAITING_FOR_APPROVAL",
            "pending_action_id": pending.id,
            "run_id": pending.run_id,
            "mission_id": pending.mission_id,
            "approval_status": approval.status,
        }

    try:
        arguments = json.loads(pending.arguments_json or "{}")
    except json.JSONDecodeError:
        arguments = {}
    arguments["approval_id"] = approval_id
    # Do not reuse the model's original request id: the original Gateway receipt
    # intentionally described the pre-approval call.  This server-owned id is
    # stable across retries and therefore exactly-once at the Gateway boundary.
    arguments["request_id"] = f"agent-resume-{pending.id}"

    recovered = (
        _already_applied_accept_replan(
            session,
            pending=pending,
            arguments=arguments,
            approval_id=approval_id,
        )
        if approval.status == "CONSUMED"
        else None
    )

    pending.status = "RESUMING"
    pending.claimed_at = pending.claimed_at or _now()
    pending.updated_at = _now()
    session.commit()

    try:
        if recovered is not None:
            result = recovered
        else:
            from app.agent.gateway import AgentToolGateway

            request = AgentToolCall.model_validate(arguments)
            result = AgentToolGateway(session).dispatch(pending.tool_name, request)
    except HTTPException as exc:
        session.rollback()
        pending = session.get(AgentPendingAction, pending.id)
        if pending is None:
            return {
                "status": "FAILED",
                "reason": "PENDING_ACTION_DISAPPEARED",
            }
        failure = {
            "error": str(exc.detail),
            "status_code": exc.status_code,
            "decision": "CONTINUATION_FAILED",
        }
        _append_resume_step(
            session,
            pending=pending,
            arguments=arguments,
            result=failure,
            status="TOOL_ERROR",
        )
        pending.status = "FAILED"
        pending.error_json = _json_text(failure)
        pending.updated_at = _now()
        run = session.get(AgentRun, pending.run_id)
        mission = session.get(JourneyMission, pending.mission_id)
        if run is not None:
            run.status = "PARTIAL"
            run.failure_reason = str(exc.detail)
        if mission is not None:
            mission.status = "PARTIAL"
            mission.failure_reason = str(exc.detail)
        record_audit(
            session,
            action="agent.pending_action.failed",
            entity_type="AgentPendingAction",
            entity_id=pending.id,
            journey_id=pending.journey_id,
            actor_type="SYSTEM",
            actor_id="approval-continuation",
            after={
                "pending_action_id": pending.id,
                "approval_id": approval_id,
                "run_id": pending.run_id,
                "status": pending.status,
                **failure,
            },
        )
        session.commit()
        return {
            "status": "FAILED",
            "pending_action_id": pending.id,
            "run_id": pending.run_id,
            "mission_id": pending.mission_id,
            **failure,
        }

    pending = session.get(AgentPendingAction, pending.id)
    if pending is None:
        raise RuntimeError("pending Agent continuation disappeared after Gateway execution")
    _append_resume_step(
        session,
        pending=pending,
        arguments=arguments,
        result=result,
        status="COMPLETED" if result.get("executed") is True else "TOOL_ERROR",
    )
    now = _now()
    pending.result_json = _json_text(result)
    pending.updated_at = now
    run = session.get(AgentRun, pending.run_id)
    mission = session.get(JourneyMission, pending.mission_id)
    executed = result.get("executed") is True
    if executed:
        pending.status = "RESUMED"
        pending.resumed_at = now
        if run is not None:
            run.status = "COMPLETED"
            run.completed_at = now
            run.failure_reason = None
            run.outcome = _json_text(
                {
                    "status": "MUTATION_EXECUTED",
                    "reason_code": "APPROVAL_CONTINUATION_RESUMED",
                    "user_summary": "The approved pending Agent action resumed and executed.",
                    "pending_action_id": pending.id,
                    "approval_id": approval_id,
                }
            )
        if mission is not None:
            mission.status = "COMPLETED"
            mission.completed_at = now
            mission.failure_reason = None
    else:
        pending.status = "FAILED"
        pending.error_json = _json_text(
            {
                "reason": "APPROVED_CONTINUATION_DID_NOT_EXECUTE",
                "result": result,
            }
        )
        if run is not None:
            run.status = "PARTIAL"
            run.failure_reason = "approved continuation did not execute"
            run.completed_at = now
        if mission is not None:
            mission.status = "PARTIAL"
            mission.failure_reason = "approved continuation did not execute"
            mission.completed_at = now

    record_audit(
        session,
        action="agent.pending_action.resumed" if executed else "agent.pending_action.failed",
        entity_type="AgentPendingAction",
        entity_id=pending.id,
        journey_id=pending.journey_id,
        actor_type="SYSTEM",
        actor_id="approval-continuation",
        after={
            "pending_action_id": pending.id,
            "approval_id": approval_id,
            "run_id": pending.run_id,
            "mission_id": pending.mission_id,
            "tool": pending.tool_name,
            "status": pending.status,
            "executed": executed,
        },
    )
    if executed and run is not None:
        record_audit(
            session,
            action="agent.run.completed",
            entity_type="AgentRun",
            entity_id=run.id,
            journey_id=pending.journey_id,
            actor_type="SYSTEM",
            actor_id="approval-continuation",
            after={
                "run_id": run.id,
                "mission_id": pending.mission_id,
                "status": run.status,
                "outcome": run.outcome,
                "failure_reason": run.failure_reason,
                "resumed_from_approval_id": approval_id,
            },
        )
    session.commit()
    return {
        "status": "RESUMED" if executed else "FAILED",
        "pending_action_id": pending.id,
        "run_id": pending.run_id,
        "mission_id": pending.mission_id,
        "result": result,
        "replayed": False,
    }
