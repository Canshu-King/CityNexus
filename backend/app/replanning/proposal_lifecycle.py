from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.audit import record_audit
from app.db.models import PlanVersion, ReplanProposal


def invalidate_pending_replans_for_event(
    session: Session,
    *,
    event_id: str,
    journey_id: str,
    decided_at: str,
    reason: str,
) -> tuple[str, ...]:
    """Retire proposals whose trigger is no longer actionable.

    The proposal and its candidate plan remain in history, but neither may be
    presented or accepted after the server-owned trigger has resolved.
    """

    pending = session.scalars(
        select(ReplanProposal).where(
            ReplanProposal.journey_id == str(journey_id),
            ReplanProposal.trigger_event_id == str(event_id),
            ReplanProposal.status.in_(("GENERATED", "PRESENTED")),
        )
    ).all()
    invalidated: list[str] = []
    for proposal in pending:
        proposal.status = "INVALIDATED"
        proposal.decided_at = decided_at
        candidate = session.get(PlanVersion, proposal.proposed_plan_version_id)
        if candidate is not None and candidate.status == "CANDIDATE":
            candidate.status = "REJECTED"
        record_audit(
            session,
            action="replan.invalidated",
            entity_type="ReplanProposal",
            entity_id=proposal.id,
            journey_id=str(journey_id),
            actor_type="SYSTEM",
            after={
                "status": proposal.status,
                "reason": reason,
                "trigger_event_id": str(event_id),
            },
        )
        invalidated.append(proposal.id)
    return tuple(invalidated)

def invalidate_pending_replans_for_journey(
    session: Session,
    *,
    journey_id: str,
    decided_at: str,
    reason: str,
) -> tuple[str, ...]:
    """Close proposals that cannot act after the Journey has finished.

    A completed Journey has no executable cursor left.  Leaving a presented
    recovery candidate in that Journey's read model makes the UI offer a
    change that the authority boundary must reject, and repeated agent runs
    turn that stale offer into a stack of identical advisories.  Keep the
    proposal row and its evidence for history, but make the terminal state
    explicit and reject its still-candidate plan.
    """

    pending = session.scalars(
        select(ReplanProposal).where(
            ReplanProposal.journey_id == str(journey_id),
            ReplanProposal.status.in_(("GENERATED", "PRESENTED")),
        )
    ).all()
    invalidated: list[str] = []
    for proposal in pending:
        proposal.status = "INVALIDATED"
        proposal.decided_at = decided_at
        candidate = session.get(PlanVersion, proposal.proposed_plan_version_id)
        if candidate is not None and candidate.status == "CANDIDATE":
            candidate.status = "REJECTED"
        record_audit(
            session,
            action="replan.invalidated",
            entity_type="ReplanProposal",
            entity_id=proposal.id,
            journey_id=str(journey_id),
            actor_type="SYSTEM",
            after={
                "status": proposal.status,
                "reason": reason,
            },
        )
        invalidated.append(proposal.id)
    return tuple(invalidated)
