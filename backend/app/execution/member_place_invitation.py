from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone, timedelta
from typing import Any
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import (
    Activity,
    Commitment,
    Journey,
    JourneyMember,
    MemberPlaceInvitation,
    MemberPlaceInvitationRecipient,
    MemberSideQuest,
    Place,
    Traveler,
)
from app.execution.clock import execution_clock
from app.execution.group_presence import planned_separation_for_member

INVITATION_TTL_MINUTES = 15
OWNER_QUEST_STATES = {"READY", "EN_ROUTE", "ARRIVED"}
OPEN_QUEST_STATES = {"DESTINATION_UNRESOLVED", "READY", "EN_ROUTE", "ARRIVED"}
PROTECTED_COMMITMENT_LEVELS = {"C3_Guaranteed", "C4_Anchored"}


def _now(value: datetime | None = None) -> datetime:
    result = value or execution_clock.now()
    if result.tzinfo is None:
        return result.replace(tzinfo=timezone.utc)
    return result.astimezone(timezone.utc)


def _iso(value: datetime | None = None) -> str:
    return _now(value).isoformat()


def _stamp(value: str | None) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(str(value or ""))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return parsed.astimezone(timezone.utc)


def _member_in_force(member: JourneyMember | None, now: datetime) -> bool:
    if member is None or member.removed_at:
        return False
    if member.expires_at is None:
        return True
    expiry = _stamp(member.expires_at)
    return expiry is not None and expiry > now


def _current_members(session: Session, journey_id: str, now: datetime) -> list[JourneyMember]:
    rows = session.scalars(
        select(JourneyMember).where(JourneyMember.journey_id == journey_id)
    ).all()
    return [row for row in rows if _member_in_force(row, now)]


def _place_payload(place: Place) -> dict[str, Any]:
    provider = str(place.provider_key or "unknown")
    source = "OpenStreetMap" if provider.casefold() in {"osm", "openstreetmap"} else provider
    return {
        "place_id": str(place.id),
        "name": str(place.name),
        "category": str(place.category or "Place"),
        "source": source,
        "latitude": float(place.latitude),
        "longitude": float(place.longitude),
        "coordinate_system": str(place.coordinate_system or ""),
    }


def _disclosure_snapshot(context: dict[str, Any]) -> dict[str, Any]:
    return {
        "place": _place_payload(context["place"]),
        "rendezvous": {
            "activity_id": str(context["target"].id),
            "title": str(context["target"].title),
            "place_name": str(context["rendezvous"].name),
            "scheduled_at": context["target"].start_at,
        },
    }


def _snapshot_json(snapshot: dict[str, Any]) -> str:
    return json.dumps(snapshot, sort_keys=True, separators=(",", ":"))


def _require_shareable_place(place: Place | None, journey: Journey) -> Place:
    if place is None or str(place.city_code) != str(journey.city_code):
        raise HTTPException(409, "PLACE_INVITATION_TARGET_STALE")
    if str(place.coordinate_system or "").upper() != "WGS84":
        raise HTTPException(409, "PLACE_INVITATION_TARGET_COORDINATES_UNAVAILABLE")
    try:
        latitude = float(place.latitude)
        longitude = float(place.longitude)
    except (TypeError, ValueError):
        raise HTTPException(409, "PLACE_INVITATION_TARGET_COORDINATES_UNAVAILABLE")
    if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
        raise HTTPException(409, "PLACE_INVITATION_TARGET_COORDINATES_UNAVAILABLE")
    return place


def resolve_owner_place_context(
    session: Session,
    *,
    journey: Journey,
    owner: JourneyMember,
    traveler_id: str,
    side_quest_id: str,
    now: datetime | None = None,
) -> dict[str, Any]:
    current = _now(now)
    quest = session.get(MemberSideQuest, str(side_quest_id))
    if (
        quest is None
        or str(quest.journey_id) != str(journey.id)
        or str(quest.member_id) != str(owner.id)
        or str(quest.traveler_id) != str(traveler_id)
    ):
        raise HTTPException(404, "PLACE_INVITATION_SIDE_QUEST_NOT_FOUND")
    if str(journey.status or "").upper() != "ACTIVE" or not journey.active_plan_version_id:
        raise HTTPException(409, "PLACE_INVITATION_JOURNEY_NOT_ACTIVE")
    split = planned_separation_for_member(session, journey, owner, now=current)
    if (
        split is None
        or str(split["intent"].id) != str(quest.planned_separation_intent_id)
        or str(quest.active_plan_version_id) != str(journey.active_plan_version_id)
        or str(quest.rendezvous_activity_id) != str(split["target"].id)
        or str(quest.rendezvous_place_id) != str(split["place"].id)
    ):
        raise HTTPException(409, "PLACE_INVITATION_OWNER_SPLIT_STALE")
    if (
        str(quest.destination_authority) != "EXACT_KNOWN_PLACE"
        or str(quest.state) not in OWNER_QUEST_STATES
        or not quest.side_place_id
    ):
        raise HTTPException(409, "PLACE_INVITATION_REQUIRES_CURRENT_EXACT_STOP")
    place = _require_shareable_place(session.get(Place, str(quest.side_place_id)), journey)
    if str(place.id) != str(quest.side_place_id):
        raise HTTPException(409, "PLACE_INVITATION_TARGET_STALE")
    target = split["target"]
    rendezvous = split["place"]
    if (
        str(target.plan_version_id) != str(journey.active_plan_version_id)
        or str(target.status or "").upper() in {"COMPLETED", "SKIPPED", "CANCELLED"}
    ):
        raise HTTPException(409, "PLACE_INVITATION_RENDEZVOUS_STALE")
    return {"quest": quest, "split": split, "place": place, "target": target, "rendezvous": rendezvous}


def invitation_preview(
    session: Session,
    *,
    journey: Journey,
    owner: JourneyMember,
    traveler_id: str,
    side_quest_id: str,
    now: datetime | None = None,
) -> dict[str, Any]:
    current = _now(now)
    context = resolve_owner_place_context(
        session,
        journey=journey,
        owner=owner,
        traveler_id=traveler_id,
        side_quest_id=side_quest_id,
        now=current,
    )
    companions = [row for row in _current_members(session, journey.id, current) if str(row.id) != str(owner.id)]
    audience_snapshot = _audience_snapshot(
        journey=journey,
        owner=owner,
        context=context,
        companions=companions,
    )
    disclosure_snapshot = _disclosure_snapshot(context)
    return {
        "side_quest_id": str(context["quest"].id),
        "place": disclosure_snapshot["place"],
        "rendezvous": disclosure_snapshot["rendezvous"],
        "recipient_count": len(companions),
        "audience_snapshot": audience_snapshot,
        "expires_in_minutes": INVITATION_TTL_MINUTES,
        "disclosure": (
            "This shares the selected public Place name and exact public pin with current Journey companions. "
            "It does not share your device location, original search coordinates, private note, route, or browsing history."
        ),
    }


def _audience_snapshot(
    *,
    journey: Journey,
    owner: JourneyMember,
    context: dict[str, Any],
    companions: list[JourneyMember],
) -> str:
    material = {
        "journey_id": str(journey.id),
        "owner_member_id": str(owner.id),
        "owner_split_intent_id": str(context["split"]["intent"].id),
        "owner_side_quest_id": str(context["quest"].id),
        "active_plan_version_id": str(journey.active_plan_version_id),
        "place_id": str(context["place"].id),
        "place_provider_key": str(context["place"].provider_key),
        "place_external_id": str(context["place"].external_id),
        "rendezvous_activity_id": str(context["target"].id),
        "rendezvous_place_id": str(context["rendezvous"].id),
        "disclosure_snapshot": _disclosure_snapshot(context),
        "recipient_member_ids": sorted(str(row.id) for row in companions),
    }
    return hashlib.sha256(
        json.dumps(material, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def create_invitation(
    session: Session,
    *,
    journey: Journey,
    owner: JourneyMember,
    traveler_id: str,
    side_quest_id: str,
    expected_audience_snapshot: str,
    now: datetime | None = None,
) -> MemberPlaceInvitation:
    current = _now(now)
    context = resolve_owner_place_context(
        session,
        journey=journey,
        owner=owner,
        traveler_id=traveler_id,
        side_quest_id=side_quest_id,
        now=current,
    )
    companions = [row for row in _current_members(session, journey.id, current) if str(row.id) != str(owner.id)]
    if not companions:
        raise HTTPException(409, "PLACE_INVITATION_NO_COMPANIONS")
    current_audience_snapshot = _audience_snapshot(
        journey=journey,
        owner=owner,
        context=context,
        companions=companions,
    )
    if current_audience_snapshot != str(expected_audience_snapshot):
        raise HTTPException(409, "PLACE_INVITATION_AUDIENCE_CHANGED")
    existing = session.scalar(
        select(MemberPlaceInvitation).where(
            MemberPlaceInvitation.journey_id == journey.id,
            MemberPlaceInvitation.owner_side_quest_id == context["quest"].id,
            MemberPlaceInvitation.state == "OPEN",
        )
    )
    if existing is not None:
        if (_stamp(existing.expires_at) or datetime.min.replace(tzinfo=timezone.utc)) > current:
            same_binding = (
                str(existing.owner_member_id) == str(owner.id)
                and str(existing.owner_split_intent_id) == str(context["split"]["intent"].id)
                and str(existing.active_plan_version_id) == str(journey.active_plan_version_id)
                and str(existing.place_id) == str(context["place"].id)
                and str(existing.place_provider_key) == str(context["place"].provider_key)
                and str(existing.place_external_id) == str(context["place"].external_id)
                and str(existing.rendezvous_activity_id) == str(context["target"].id)
                and str(existing.rendezvous_place_id) == str(context["rendezvous"].id)
                and str(existing.disclosure_snapshot_json or "{}")
                == _snapshot_json(_disclosure_snapshot(context))
            )
            if same_binding:
                existing_recipient_ids = set(session.scalars(
                    select(MemberPlaceInvitationRecipient.recipient_member_id).where(
                        MemberPlaceInvitationRecipient.invitation_id == existing.id
                    )
                ).all())
                current_recipient_ids = {str(member.id) for member in companions}
                if existing_recipient_ids.issubset(current_recipient_ids):
                    stamp = _iso(current)
                    for member in companions:
                        if str(member.id) in existing_recipient_ids:
                            continue
                        session.add(MemberPlaceInvitationRecipient(
                            id=str(uuid4()),
                            invitation_id=existing.id,
                            recipient_member_id=str(member.id),
                            recipient_traveler_id=str(member.traveler_id),
                            state="INVITED",
                            invited_at=stamp,
                            updated_at=stamp,
                        ))
                    session.commit()
                    session.refresh(existing)
                    return existing
                # A removed/expired addressed member makes the old invitation
                # stale. A fresh invitation can still be issued after the owner
                # reviews and confirms the new audience snapshot.
                existing.state = "STALE"
                existing.updated_at = _iso(current)
                session.flush()
            existing.state = "STALE"
            existing.updated_at = _iso(current)
        else:
            existing.state = "EXPIRED"
            existing.updated_at = _iso(current)
        session.flush()

    stamp = _iso(current)
    invitation = MemberPlaceInvitation(
        id=str(uuid4()),
        journey_id=str(journey.id),
        owner_member_id=str(owner.id),
        owner_traveler_id=str(traveler_id),
        owner_split_intent_id=str(context["split"]["intent"].id),
        owner_side_quest_id=str(context["quest"].id),
        active_plan_version_id=str(journey.active_plan_version_id),
        place_id=str(context["place"].id),
        place_provider_key=str(context["place"].provider_key),
        place_external_id=str(context["place"].external_id),
        rendezvous_activity_id=str(context["target"].id),
        rendezvous_place_id=str(context["rendezvous"].id),
        disclosure_snapshot_json=_snapshot_json(_disclosure_snapshot(context)),
        state="OPEN",
        created_at=stamp,
        expires_at=_iso(current + timedelta(minutes=INVITATION_TTL_MINUTES)),
        updated_at=stamp,
    )
    session.add(invitation)
    session.flush()
    for member in companions:
        session.add(
            MemberPlaceInvitationRecipient(
                id=str(uuid4()),
                invitation_id=invitation.id,
                recipient_member_id=str(member.id),
                recipient_traveler_id=str(member.traveler_id),
                state="INVITED",
                invited_at=stamp,
                updated_at=stamp,
            )
        )
    session.commit()
    session.refresh(invitation)
    return invitation


def _invitation_context_is_current(
    session: Session,
    journey: Journey,
    invitation: MemberPlaceInvitation,
    *,
    now: datetime,
) -> bool:
    if (
        str(invitation.journey_id) != str(journey.id)
        or str(journey.status or "").upper() != "ACTIVE"
        or str(invitation.active_plan_version_id) != str(journey.active_plan_version_id or "")
    ):
        return False
    owner = session.get(JourneyMember, str(invitation.owner_member_id))
    if (
        not _member_in_force(owner, now)
        or owner is None
        or str(owner.traveler_id) != str(invitation.owner_traveler_id)
    ):
        return False
    try:
        context = resolve_owner_place_context(
            session,
            journey=journey,
            owner=owner,
            traveler_id=str(invitation.owner_traveler_id),
            side_quest_id=str(invitation.owner_side_quest_id),
            now=now,
        )
    except HTTPException:
        return False
    place = context["place"]
    addressed_recipients = session.scalars(
        select(MemberPlaceInvitationRecipient).where(
            MemberPlaceInvitationRecipient.invitation_id == invitation.id
        )
    ).all()
    if not addressed_recipients:
        return False
    for response in addressed_recipients:
        addressed_member = session.get(JourneyMember, str(response.recipient_member_id))
        if (
            not _member_in_force(addressed_member, now)
            or addressed_member is None
            or str(addressed_member.traveler_id) != str(response.recipient_traveler_id)
        ):
            return False
    try:
        saved_snapshot = json.loads(str(invitation.disclosure_snapshot_json or "{}"))
    except (TypeError, json.JSONDecodeError):
        return False
    return bool(
        str(context["split"]["intent"].id) == str(invitation.owner_split_intent_id)
        and str(context["target"].id) == str(invitation.rendezvous_activity_id)
        and str(context["rendezvous"].id) == str(invitation.rendezvous_place_id)
        and str(place.id) == str(invitation.place_id)
        and str(place.provider_key) == str(invitation.place_provider_key)
        and str(place.external_id) == str(invitation.place_external_id)
        and saved_snapshot == _disclosure_snapshot(context)
    )


def get_recipient_invitation(
    session: Session,
    *,
    journey: Journey,
    recipient: JourneyMember,
    traveler_id: str,
    invitation_id: str,
) -> tuple[MemberPlaceInvitation, MemberPlaceInvitationRecipient]:
    invitation = session.scalar(
        select(MemberPlaceInvitation).where(
            MemberPlaceInvitation.id == str(invitation_id),
            MemberPlaceInvitation.journey_id == str(journey.id),
        ).with_for_update()
    )
    if invitation is None:
        raise HTTPException(404, "PLACE_INVITATION_NOT_FOUND")
    response = session.scalar(
        select(MemberPlaceInvitationRecipient).where(
            MemberPlaceInvitationRecipient.invitation_id == invitation.id,
            MemberPlaceInvitationRecipient.recipient_member_id == str(recipient.id),
            MemberPlaceInvitationRecipient.recipient_traveler_id == str(traveler_id),
        ).with_for_update()
    )
    if response is None:
        # A guessed invitation ID must not reveal whether the Place exists.
        raise HTTPException(404, "PLACE_INVITATION_NOT_FOUND")
    return invitation, response


def validate_invitation_for_acceptance(
    session: Session,
    *,
    journey: Journey,
    recipient: JourneyMember,
    traveler_id: str,
    invitation: MemberPlaceInvitation,
    response: MemberPlaceInvitationRecipient,
    now: datetime | None = None,
) -> dict[str, Any]:
    current = _now(now)
    if not _member_in_force(recipient, current) or str(recipient.traveler_id) != str(traveler_id):
        raise HTTPException(404, "PLACE_INVITATION_NOT_FOUND")
    continuing_accepted_response = response.state == "ACCEPTANCE_NEEDS_COMPLETION"
    if not continuing_accepted_response:
        # Withdrawal, expiry, or a changed source context can stop a new accept,
        # but cannot revoke a response that was durably accepted already.
        if invitation.state != "OPEN":
            raise HTTPException(409, f"PLACE_INVITATION_{invitation.state}")
        if (_stamp(invitation.expires_at) or datetime.min.replace(tzinfo=timezone.utc)) <= current:
            invitation.state = "EXPIRED"
            invitation.updated_at = _iso(current)
            session.commit()
            raise HTTPException(409, "PLACE_INVITATION_EXPIRED")
        if not _invitation_context_is_current(session, journey, invitation, now=current):
            invitation.state = "STALE"
            invitation.updated_at = _iso(current)
            session.commit()
            raise HTTPException(409, "PLACE_INVITATION_STALE")
    elif str(journey.active_plan_version_id or "") != str(invitation.active_plan_version_id):
        raise HTTPException(409, "PLACE_INVITATION_RENDEZVOUS_STALE")
    place = _require_shareable_place(session.get(Place, str(invitation.place_id)), journey)
    target = session.get(Activity, str(invitation.rendezvous_activity_id))
    rendezvous = session.get(Place, str(invitation.rendezvous_place_id))
    if (
        target is None
        or rendezvous is None
        or str(target.plan_version_id) != str(invitation.active_plan_version_id)
        or str(target.place_id or "") != str(invitation.rendezvous_place_id)
        or str(target.status or "").upper() in {"COMPLETED", "SKIPPED", "CANCELLED"}
    ):
        raise HTTPException(409, "PLACE_INVITATION_RENDEZVOUS_STALE")
    return {"place": place, "target": target, "rendezvous": rendezvous}


def recipient_conflict_reason(
    session: Session,
    *,
    journey: Journey,
    recipient: JourneyMember,
    invitation: MemberPlaceInvitation,
    same_invitation_split_id: str | None,
    now: datetime | None = None,
) -> str | None:
    """Return a recoverable block without overwriting the recipient's current trip."""
    current = _now(now)
    split = planned_separation_for_member(session, journey, recipient, now=current)
    if split is not None and str(split["intent"].id) != str(same_invitation_split_id or ""):
        return "INVITATION_RECIPIENT_HAS_ACTIVE_SPLIT"
    open_quest = session.scalar(
        select(MemberSideQuest).where(
            MemberSideQuest.journey_id == journey.id,
            MemberSideQuest.member_id == recipient.id,
            MemberSideQuest.state.in_(tuple(OPEN_QUEST_STATES)),
        ).order_by(MemberSideQuest.created_at.desc(), MemberSideQuest.id.desc())
    )
    if open_quest is not None:
        belongs_to_invitation = (
            str(open_quest.planned_separation_intent_id) == str(same_invitation_split_id or "")
            and str(open_quest.side_place_id or "") == str(invitation.place_id)
        )
        if not belongs_to_invitation:
            return "INVITATION_RECIPIENT_HAS_ACTIVE_SIDE_QUEST"

    rendezvous = session.get(Activity, str(invitation.rendezvous_activity_id))
    if rendezvous is None:
        return "PLACE_INVITATION_RENDEZVOUS_STALE"
    rendezvous_at = _stamp(rendezvous.start_at)
    for commitment in session.scalars(
        select(Commitment).where(
            Commitment.journey_id == journey.id,
            Commitment.status == "ACTIVE",
            Commitment.level.in_(tuple(PROTECTED_COMMITMENT_LEVELS)),
        )
    ).all():
        if str(commitment.activity_id or "") == str(rendezvous.id):
            continue
        activity = session.get(Activity, str(commitment.activity_id or ""))
        if (
            activity is None
            or str(activity.plan_version_id) != str(journey.active_plan_version_id or "")
            or str(activity.status or "").upper() in {"COMPLETED", "SKIPPED", "CANCELLED"}
        ):
            continue
        at = _stamp(activity.start_at)
        if at is not None and at > current and (rendezvous_at is None or at <= rendezvous_at):
            return "INVITATION_RECIPIENT_PROTECTED_COMMITMENT"
    return None


def invitation_projection(
    session: Session,
    journey: Journey,
    *,
    viewer_member_id: str | None,
    now: datetime | None = None,
) -> dict[str, Any] | None:
    if not viewer_member_id:
        return None
    current = _now(now)
    viewer = session.get(JourneyMember, str(viewer_member_id))
    if not _member_in_force(viewer, current):
        return None
    output: dict[str, list[dict[str, Any]]] = {"sent": [], "incoming": []}
    parent_query = select(MemberPlaceInvitation).where(
        MemberPlaceInvitation.journey_id == journey.id
    )
    if str(viewer.id):
        parent_query = parent_query.outerjoin(
            MemberPlaceInvitationRecipient,
            MemberPlaceInvitationRecipient.invitation_id == MemberPlaceInvitation.id,
        ).where(
            (MemberPlaceInvitation.owner_member_id == str(viewer.id))
            | (MemberPlaceInvitationRecipient.recipient_member_id == str(viewer.id))
        ).distinct()
    parents = session.scalars(
        parent_query.order_by(MemberPlaceInvitation.created_at.desc(), MemberPlaceInvitation.id.desc()).limit(30)
    ).all()

    for invitation in parents:
        recipients = session.scalars(
            select(MemberPlaceInvitationRecipient)
            .where(MemberPlaceInvitationRecipient.invitation_id == invitation.id)
            .order_by(MemberPlaceInvitationRecipient.invited_at, MemberPlaceInvitationRecipient.id)
        ).all()
        owner = session.get(JourneyMember, str(invitation.owner_member_id))
        owner_traveler = session.get(Traveler, str(invitation.owner_traveler_id))
        owner_name = str(owner_traveler.display_name if owner_traveler else "Traveller")
        place = session.get(Place, str(invitation.place_id))
        rendezvous_place = session.get(Place, str(invitation.rendezvous_place_id))
        rendezvous_activity = session.get(Activity, str(invitation.rendezvous_activity_id))
        if place is None or rendezvous_place is None or rendezvous_activity is None:
            continue
        parent_state = str(invitation.state)
        if parent_state == "OPEN":
            expiry = _stamp(invitation.expires_at)
            if expiry is None or expiry <= current:
                parent_state = "EXPIRED"
            elif not _invitation_context_is_current(session, journey, invitation, now=current):
                parent_state = "STALE"

        try:
            disclosure_snapshot = json.loads(str(invitation.disclosure_snapshot_json or "{}"))
            place_view = disclosure_snapshot["place"]
            rendezvous_view = disclosure_snapshot["rendezvous"]
            if not isinstance(place_view, dict) or not isinstance(rendezvous_view, dict):
                continue
        except (TypeError, KeyError, json.JSONDecodeError):
            continue
        if str(invitation.owner_member_id) == str(viewer.id):
            recipient_views: list[dict[str, Any]] = []
            for response in recipients:
                member = session.get(JourneyMember, str(response.recipient_member_id))
                traveler = session.get(Traveler, str(response.recipient_traveler_id))
                response_state = str(response.state)
                if response_state == "INVITED":
                    if not _member_in_force(member, current):
                        response_state = "STALE"
                    elif parent_state != "OPEN":
                        response_state = parent_state
                recipient_views.append({
                    "member_id": str(response.recipient_member_id),
                    "display_name": str(traveler.display_name if traveler else "Traveller"),
                    "state": response_state,
                })
            output["sent"].append({
                "invitation_id": str(invitation.id),
                "side_quest_id": str(invitation.owner_side_quest_id),
                "state": parent_state,
                "created_at": invitation.created_at,
                "expires_at": invitation.expires_at,
                "place": place_view,
                "rendezvous": rendezvous_view,
                "recipients": recipient_views,
            })
            continue

        response = next((row for row in recipients if str(row.recipient_member_id) == str(viewer.id)), None)
        if response is None:
            continue
        response_state = str(response.state)
        if response_state == "INVITED":
            if parent_state != "OPEN":
                response_state = parent_state
            elif str(owner.journey_id if owner else "") != str(journey.id) or not _member_in_force(owner, current):
                response_state = "STALE"
        if response_state in {"DECLINED", "ACCEPTED_OWN_STOP_READY"}:
            continue
        output["incoming"].append({
            "invitation_id": str(invitation.id),
            "state": response_state,
            "inviter_display_name": owner_name,
            "created_at": invitation.created_at,
            "expires_at": invitation.expires_at,
            "place": place_view,
            "rendezvous": rendezvous_view,
            "can_respond": (
                response_state == "INVITED" and parent_state == "OPEN"
            ) or response_state == "ACCEPTANCE_NEEDS_COMPLETION",
        })
    return output
