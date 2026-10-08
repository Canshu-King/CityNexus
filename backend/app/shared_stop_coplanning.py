from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import JourneyMember, JourneyRoleCapability, SharedStopCoPlanningGrant


GRANT_PURPOSE = "R73_SHARED_STOP_ONLY"


def _parse_aware(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    return parsed.astimezone(timezone.utc) if parsed.tzinfo else None


def member_is_in_force(member: JourneyMember | None, *, now: datetime | None = None) -> bool:
    if member is None or member.removed_at:
        return False
    expires_at = _parse_aware(member.expires_at)
    if member.expires_at and expires_at is None:
        return False
    current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    return expires_at is None or expires_at > current


def member_has_capability(session: Session, member: JourneyMember, capability: str) -> bool:
    return session.scalar(
        select(JourneyRoleCapability.role).where(
            JourneyRoleCapability.role == member.role,
            JourneyRoleCapability.capability == capability,
        )
    ) is not None


def grant_status_for_projection(
    grant: SharedStopCoPlanningGrant, *, now: datetime | None = None
) -> str:
    if grant.status != "ACCEPTED":
        return str(grant.status)
    expires_at = _parse_aware(grant.expires_at)
    current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    return "EXPIRED" if expires_at is None or expires_at <= current else "ACCEPTED"


def find_accepted_grant(
    session: Session,
    *,
    journey_id: str,
    invitation_id: str,
    base_plan_version_id: str,
    grantee: JourneyMember,
    promotion_id: str | None = None,
    decision_epoch: str | None = None,
    require_unbound: bool = False,
    now: datetime | None = None,
) -> SharedStopCoPlanningGrant | None:
    current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    rows = session.scalars(
        select(SharedStopCoPlanningGrant)
        .where(
            SharedStopCoPlanningGrant.journey_id == str(journey_id),
            SharedStopCoPlanningGrant.invitation_id == str(invitation_id),
            SharedStopCoPlanningGrant.base_plan_version_id == str(base_plan_version_id),
            SharedStopCoPlanningGrant.grantee_member_id == str(grantee.id),
            SharedStopCoPlanningGrant.purpose == GRANT_PURPOSE,
            SharedStopCoPlanningGrant.status == "ACCEPTED",
        )
        .order_by(
            SharedStopCoPlanningGrant.updated_at.desc(),
            SharedStopCoPlanningGrant.id.desc(),
        )
    ).all()
    if (
        str(grantee.journey_id) != str(journey_id)
        or str(grantee.traveler_id) == ""
        or not member_is_in_force(grantee, now=current)
    ):
        return None
    for grant in rows:
        if require_unbound:
            if grant.promotion_id is not None or grant.decision_epoch is not None:
                continue
        elif promotion_id is not None and str(grant.promotion_id or "") != str(promotion_id):
            continue
        if decision_epoch is not None and str(grant.decision_epoch or "") != str(decision_epoch):
            continue
        expires_at = _parse_aware(grant.expires_at)
        if expires_at is None or expires_at <= current:
            continue
        if str(grant.grantee_traveler_id) != str(grantee.traveler_id):
            continue
        grantor = session.get(JourneyMember, str(grant.grantor_member_id))
        if (
            grantor is None
            or str(grantor.journey_id) != str(journey_id)
            or str(grantor.traveler_id) != str(grant.grantor_traveler_id)
            or not member_is_in_force(grantor, now=current)
            or not member_has_capability(session, grantor, "MEMBER_MANAGE")
        ):
            continue
        return grant
    return None


def decision_scope_facts(
    session: Session,
    *,
    journey_id: str,
    invitation_id: str,
    base_plan_version_id: str,
    promotion_id: str,
    decision_epoch: str | None,
    required_member_ids: list[str],
    bind_unbound: bool = False,
) -> tuple[list[dict[str, Any]], dict[str, SharedStopCoPlanningGrant]]:
    """Resolve current signer authority and produce deterministic epoch material."""
    facts: list[dict[str, Any]] = []
    grants_by_member: dict[str, SharedStopCoPlanningGrant] = {}
    # Validate the complete required cohort before mutating any grant. The
    # caller may mark a promotion BLOCKED and commit after a late 409; an
    # early grant bind would otherwise be accidentally committed with it.
    grants_to_bind: list[SharedStopCoPlanningGrant] = []
    now = datetime.now(timezone.utc)
    for member_id in sorted({str(item) for item in required_member_ids}):
        member = session.get(JourneyMember, member_id)
        if member is None or str(member.journey_id) != str(journey_id) or not member_is_in_force(member, now=now):
            raise HTTPException(409, "SCOPED_COPLANNING_MEMBER_NOT_IN_FORCE")
        if member_has_capability(session, member, "JOURNEY_UPDATE"):
            facts.append({"member_id": member_id, "mode": "ROLE_JOURNEY_UPDATE"})
            continue
        grant = find_accepted_grant(
            session,
            journey_id=journey_id,
            invitation_id=invitation_id,
            base_plan_version_id=base_plan_version_id,
            grantee=member,
            promotion_id=None if bind_unbound else promotion_id,
            decision_epoch=None if bind_unbound else decision_epoch,
            require_unbound=bind_unbound,
            now=now,
        )
        if grant is None:
            raise HTTPException(409, "SCOPED_COPLANNING_GRANT_REQUIRED_OR_STALE")
        if bind_unbound:
            grants_to_bind.append(grant)
        grants_by_member[member_id] = grant
        facts.append(
            {
                "member_id": member_id,
                "mode": "R73_SCOPED_GRANT",
                "grant_id": str(grant.id),
                "journey_id": str(grant.journey_id),
                "invitation_id": str(grant.invitation_id),
                "base_plan_version_id": str(grant.base_plan_version_id),
                "grantee_member_id": str(grant.grantee_member_id),
                "grantee_traveler_id": str(grant.grantee_traveler_id),
                "grantor_member_id": str(grant.grantor_member_id),
                "grantor_traveler_id": str(grant.grantor_traveler_id),
                "purpose": str(grant.purpose),
                "status": str(grant.status),
                "accepted_at": str(grant.accepted_at or ""),
                "expires_at": str(grant.expires_at),
                "promotion_id": str(promotion_id) if bind_unbound else str(grant.promotion_id or ""),
            }
        )
    # This remains one transaction owned by the caller; failed validation
    # above leaves every accepted grant available for a fresh proposal.
    for grant in grants_to_bind:
        grant.promotion_id = str(promotion_id)
        grant.updated_at = now.isoformat()
    return facts, grants_by_member


def require_scoped_response_authority(
    session: Session,
    *,
    journey_id: str,
    promotion_id: str,
    invitation_id: str,
    base_plan_version_id: str,
    decision_epoch: str,
    member: JourneyMember,
    traveler_id: str,
) -> SharedStopCoPlanningGrant:
    if member_has_capability(session, member, "JOURNEY_UPDATE"):
        raise HTTPException(409, "SCOPED_GRANT_NOT_NEEDED_FOR_ROLE_AUTHORITY")
    grant = find_accepted_grant(
        session,
        journey_id=journey_id,
        invitation_id=invitation_id,
        base_plan_version_id=base_plan_version_id,
        grantee=member,
        promotion_id=promotion_id,
        decision_epoch=decision_epoch,
    )
    if grant is None or str(grant.grantee_traveler_id) != str(traveler_id):
        raise HTTPException(403, "SCOPED_COPLANNING_GRANT_REQUIRED_OR_STALE")
    return grant
