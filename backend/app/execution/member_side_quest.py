from __future__ import annotations

import unicodedata
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.audit import record_audit
from app.db.models import Journey, JourneyMember, MemberSideQuest, Place
from app.execution.clock import execution_clock
from app.execution.group_presence import planned_separation_for_member


OPEN_STATES = frozenset({"DESTINATION_UNRESOLVED", "READY", "EN_ROUTE", "ARRIVED"})
TERMINAL_STATES = frozenset({"COMPLETED", "CANCELLED", "INVALIDATED"})
SAME_STATE_ACTIONS = {
    "START": "EN_ROUTE",
    "ARRIVE": "ARRIVED",
    "COMPLETE": "COMPLETED",
    "CANCEL": "CANCELLED",
}


def _stamp(now: datetime | None = None) -> str:
    return (now or execution_clock.now()).astimezone(timezone.utc).isoformat()


def _destination_key(value: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", value).casefold().split())


def _active_split(
    session: Session,
    journey: Journey,
    member: JourneyMember,
    *,
    now: datetime | None = None,
) -> dict:
    if str(journey.status or "").upper() != "ACTIVE" or not journey.active_plan_version_id:
        raise HTTPException(409, "SIDE_QUEST_REQUIRES_ACTIVE_JOURNEY")
    split = planned_separation_for_member(
        session,
        journey,
        member,
        now=(now or execution_clock.now()).astimezone(timezone.utc),
    )
    if split is None:
        raise HTTPException(409, "SIDE_QUEST_REQUIRES_CURRENT_PLANNED_SEPARATION")
    if (
        str(split["target"].plan_version_id) != str(journey.active_plan_version_id)
        or str(split["target"].status or "").upper() in {"COMPLETED", "SKIPPED", "CANCELLED"}
    ):
        raise HTTPException(409, "SIDE_QUEST_REQUIRES_CURRENT_PLANNED_SEPARATION")
    return split


def _quest_rows_for_split(
    session: Session,
    journey_id: str,
    member_id: str,
    split_intent_id: str,
) -> list[MemberSideQuest]:
    return session.scalars(
        select(MemberSideQuest)
        .where(
            MemberSideQuest.journey_id == journey_id,
            MemberSideQuest.member_id == member_id,
            MemberSideQuest.planned_separation_intent_id == split_intent_id,
        )
        .order_by(MemberSideQuest.created_at.desc(), MemberSideQuest.id.desc())
    ).all()


def _resolve_destination(
    session: Session,
    journey: Journey,
    *,
    destination_text: str | None,
    place_id: str | None,
) -> tuple[Place | None, str, str, str]:
    text = " ".join(str(destination_text or "").split())
    requested_place_id = str(place_id or "").strip()
    if requested_place_id:
        place = session.get(Place, requested_place_id)
        if place is None:
            raise HTTPException(404, "SIDE_QUEST_PLACE_NOT_FOUND")
        if str(place.city_code) != str(journey.city_code):
            raise HTTPException(422, "SIDE_QUEST_PLACE_OUTSIDE_JOURNEY_CITY")
        if text and _destination_key(text) != _destination_key(place.name):
            raise HTTPException(422, "SIDE_QUEST_PLACE_LABEL_MISMATCH")
        return place, str(place.name), "EXACT_KNOWN_PLACE", "READY"
    if not text:
        raise HTTPException(422, "SIDE_QUEST_DESTINATION_REQUIRED")

    # A bare name is bound only when it exactly identifies one existing Place in
    # the Journey's city. Ambiguity remains descriptive; no coordinates are made.
    candidates = session.scalars(
        select(Place).where(Place.city_code == str(journey.city_code))
    ).all()
    exact = [row for row in candidates if _destination_key(row.name) == _destination_key(text)]
    if len(exact) == 1:
        return exact[0], str(exact[0].name), "EXACT_KNOWN_PLACE", "READY"
    return None, text, "DESCRIPTIVE_ONLY", "DESTINATION_UNRESOLVED"


def _record_quest_audit(
    session: Session,
    *,
    action: str,
    journey: Journey,
    quest: MemberSideQuest,
    actor_id: str,
    state: str,
    reason_code: str | None = None,
    actor_type: str = "TRAVELER",
) -> None:
    after = {
        "member_id": str(quest.member_id),
        "planned_separation_intent_id": str(quest.planned_separation_intent_id),
        "state": state,
        "physical_presence_verified": False,
    }
    if reason_code:
        after["reason_code"] = reason_code
    record_audit(
        session,
        action=f"journey.member_side_quest.{action}",
        entity_type="MemberSideQuest",
        entity_id=quest.id,
        journey_id=journey.id,
        actor_type=actor_type,
        actor_id=actor_id,
        after=after,
    )


def create_or_replace_member_side_quest(
    session: Session,
    *,
    journey: Journey,
    member: JourneyMember,
    traveler_id: str,
    destination_text: str | None,
    place_id: str | None,
    now: datetime | None = None,
) -> MemberSideQuest:
    stamp = _stamp(now)
    split = _active_split(session, journey, member, now=now)
    place, title, destination_authority, state = _resolve_destination(
        session,
        journey,
        destination_text=destination_text,
        place_id=place_id,
    )
    split_id = str(split["intent"].id)
    rows = _quest_rows_for_split(session, journey.id, member.id, split_id)
    open_quest = next((row for row in rows if row.state in OPEN_STATES), None)
    if open_quest is not None and open_quest.state not in {"DESTINATION_UNRESOLVED", "READY"}:
        raise HTTPException(409, "SIDE_QUEST_ALREADY_IN_PROGRESS")

    if open_quest is None:
        target = split["target"]
        rendezvous_place = split["place"]
        quest = MemberSideQuest(
            id=str(uuid4()),
            journey_id=journey.id,
            member_id=member.id,
            traveler_id=str(traveler_id),
            planned_separation_intent_id=split_id,
            active_plan_version_id=str(journey.active_plan_version_id),
            rendezvous_activity_id=str(target.id),
            rendezvous_place_id=str(rendezvous_place.id),
            rendezvous_title=str(target.title),
            rendezvous_place_name=str(rendezvous_place.name),
            rendezvous_scheduled_at=target.start_at,
            side_place_id=str(place.id) if place is not None else None,
            side_title=title,
            destination_authority=destination_authority,
            state=state,
            created_at=stamp,
            updated_at=stamp,
        )
        session.add(quest)
        session.flush()
        _record_quest_audit(
            session,
            action="created",
            journey=journey,
            quest=quest,
            actor_id=traveler_id,
            state=state,
        )
        session.commit()
        return quest

    if (
        open_quest.side_place_id == (str(place.id) if place is not None else None)
        and open_quest.side_title == title
        and open_quest.destination_authority == destination_authority
        and open_quest.state == state
    ):
        return open_quest

    open_quest.side_place_id = str(place.id) if place is not None else None
    open_quest.side_title = title
    open_quest.destination_authority = destination_authority
    open_quest.state = state
    open_quest.started_at = None
    open_quest.arrived_at = None
    open_quest.completed_at = None
    open_quest.cancelled_at = None
    open_quest.updated_at = stamp
    _record_quest_audit(
        session,
        action="replaced",
        journey=journey,
        quest=open_quest,
        actor_id=traveler_id,
        state=state,
    )
    session.commit()
    return open_quest


def invalidate_member_side_quests_for_intents(
    session: Session,
    *,
    journey: Journey,
    intent_ids: list[str],
    reason_code: str,
    now: datetime | None = None,
) -> int:
    ids = [str(item) for item in intent_ids if str(item)]
    if not ids:
        return 0
    stamp = _stamp(now)
    rows = session.scalars(
        select(MemberSideQuest).where(
            MemberSideQuest.journey_id == journey.id,
            MemberSideQuest.planned_separation_intent_id.in_(ids),
            MemberSideQuest.state.in_(tuple(OPEN_STATES)),
        )
    ).all()
    for quest in rows:
        quest.state = "INVALIDATED"
        quest.invalidated_at = stamp
        quest.updated_at = stamp
        _record_quest_audit(
            session,
            action="invalidated",
            journey=journey,
            quest=quest,
            actor_id="r63-planned-separation",
            state="INVALIDATED",
            reason_code=reason_code,
            actor_type="SYSTEM",
        )
    return len(rows)


def _current_binding_matches(
    session: Session,
    *,
    journey: Journey,
    member: JourneyMember,
    quest: MemberSideQuest,
    now: datetime | None = None,
) -> bool:
    try:
        split = _active_split(session, journey, member, now=now)
    except HTTPException:
        return False
    return bool(
        str(split["intent"].id) == str(quest.planned_separation_intent_id)
        and str(journey.active_plan_version_id) == str(quest.active_plan_version_id)
        and str(split["target"].id) == str(quest.rendezvous_activity_id)
        and str(split["place"].id) == str(quest.rendezvous_place_id)
    )


def transition_member_side_quest(
    session: Session,
    *,
    journey: Journey,
    member: JourneyMember,
    traveler_id: str,
    quest_id: str,
    action: str,
    now: datetime | None = None,
) -> MemberSideQuest:
    normalized_action = str(action or "").upper()
    if normalized_action not in SAME_STATE_ACTIONS:
        raise HTTPException(422, "SIDE_QUEST_ACTION_UNSUPPORTED")
    quest = session.scalar(
        select(MemberSideQuest).where(
            MemberSideQuest.id == str(quest_id),
            MemberSideQuest.journey_id == journey.id,
            MemberSideQuest.member_id == member.id,
            MemberSideQuest.traveler_id == str(traveler_id),
        )
    )
    if quest is None:
        raise HTTPException(404, "SIDE_QUEST_NOT_FOUND")

    target_state = SAME_STATE_ACTIONS[normalized_action]
    if quest.state in TERMINAL_STATES:
        if quest.state == target_state:
            return quest
        raise HTTPException(409, "SIDE_QUEST_IS_TERMINAL")

    stamp = _stamp(now)
    if not _current_binding_matches(
        session, journey=journey, member=member, quest=quest, now=now
    ):
        quest.state = "INVALIDATED"
        quest.invalidated_at = stamp
        quest.updated_at = stamp
        _record_quest_audit(
            session,
            action="invalidated",
            journey=journey,
            quest=quest,
            actor_id=traveler_id,
            state="INVALIDATED",
            reason_code="R63_PLANNED_SEPARATION_NO_LONGER_CURRENT",
        )
        session.commit()
        raise HTTPException(409, "SIDE_QUEST_INVALIDATED_R63_SEPARATION_CHANGED")
    if quest.state == target_state:
        return quest

    transitions = {
        "START": {"READY": "EN_ROUTE"},
        "ARRIVE": {"EN_ROUTE": "ARRIVED"},
        "COMPLETE": {"ARRIVED": "COMPLETED"},
        "CANCEL": {state: "CANCELLED" for state in OPEN_STATES},
    }
    next_state = transitions[normalized_action].get(quest.state)
    if next_state is None:
        if normalized_action == "START" and quest.state == "DESTINATION_UNRESOLVED":
            raise HTTPException(409, "SIDE_QUEST_DESTINATION_NOT_EXACT")
        raise HTTPException(409, "SIDE_QUEST_INVALID_TRANSITION")

    quest.state = next_state
    quest.updated_at = stamp
    if next_state == "EN_ROUTE":
        quest.started_at = stamp
    elif next_state == "ARRIVED":
        quest.arrived_at = stamp
    elif next_state == "COMPLETED":
        quest.completed_at = stamp
    elif next_state == "CANCELLED":
        quest.cancelled_at = stamp
    _record_quest_audit(
        session,
        action=normalized_action.lower(),
        journey=journey,
        quest=quest,
        actor_id=traveler_id,
        state=next_state,
    )
    session.commit()
    return quest


def _owner_payload(
    quest: MemberSideQuest,
    *,
    state: str | None = None,
    return_state: str | None = None,
) -> dict:
    return {
        "id": str(quest.id),
        "state": state or str(quest.state),
        "destination": {
            "place_id": str(quest.side_place_id) if quest.side_place_id else None,
            "title": str(quest.side_title),
            "authority": str(quest.destination_authority),
        },
        "rendezvous": {
            "activity_id": str(quest.rendezvous_activity_id),
            "title": str(quest.rendezvous_title),
            "place_name": str(quest.rendezvous_place_name),
            "scheduled_at": quest.rendezvous_scheduled_at,
        },
        "return_state": return_state or "RETURN_UNKNOWN",
        "shared_plan_changed": False,
        "arrival_claim": (
            "MEMBER_REPORTED_NOT_PHYSICAL_PRESENCE_PROOF"
            if state == "ARRIVED" or (state is None and quest.state == "ARRIVED")
            else None
        ),
        "created_at": quest.created_at,
        "started_at": quest.started_at,
        "arrived_at": quest.arrived_at,
        "completed_at": quest.completed_at,
        "cancelled_at": quest.cancelled_at,
    }


def attach_member_side_quest_projection(
    session: Session,
    journey: Journey,
    *,
    viewer_member_id: str | None,
    group_presence: dict,
) -> dict | None:
    """Add only coarse non-owner states; return destination detail only to its owner."""
    projected_members = group_presence.get("members")
    projected_members = projected_members if isinstance(projected_members, list) else []
    current_splits: dict[str, dict] = {}
    member_rows: dict[str, JourneyMember] = {}
    for item in projected_members:
        member_id = str(item.get("member_id") or "") if isinstance(item, dict) else ""
        member = session.get(JourneyMember, member_id) if member_id else None
        if member is None:
            continue
        member_rows[member_id] = member
        try:
            split = planned_separation_for_member(
                session,
                journey,
                member,
                now=execution_clock.now().astimezone(timezone.utc),
            )
        except HTTPException:
            split = None
        if split is not None:
            current_splits[member_id] = split

    quest_rows = session.scalars(
        select(MemberSideQuest)
        .where(MemberSideQuest.journey_id == journey.id)
        .order_by(MemberSideQuest.created_at, MemberSideQuest.id)
    ).all()
    latest_by_split: dict[tuple[str, str], MemberSideQuest] = {}
    latest_by_member: dict[str, MemberSideQuest] = {}
    for quest in quest_rows:
        latest_by_split[(str(quest.member_id), str(quest.planned_separation_intent_id))] = quest
        latest_by_member[str(quest.member_id)] = quest

    viewer_payload: dict | None = None
    viewer_split = current_splits.get(str(viewer_member_id or ""))
    viewer_member = member_rows.get(str(viewer_member_id or ""))
    viewer_quest = None
    if viewer_split is not None:
        viewer_quest = latest_by_split.get(
            (str(viewer_member_id), str(viewer_split["intent"].id))
        )
    elif viewer_member is not None:
        viewer_quest = latest_by_member.get(str(viewer_member_id))
        if viewer_quest is not None and viewer_quest.state in OPEN_STATES:
            viewer_payload = _owner_payload(
                viewer_quest,
                state="INVALIDATED",
                return_state="RETURN_UNKNOWN",
            )

    for item in projected_members:
        if not isinstance(item, dict):
            continue
        member_id = str(item.get("member_id") or "")
        split = current_splits.get(member_id)
        if split is None:
            continue
        quest = latest_by_split.get((member_id, str(split["intent"].id)))
        if quest is None:
            continue
        if member_id == str(viewer_member_id or ""):
            if viewer_quest is not None:
                planned_row = item.get("return_state")
                viewer_payload = _owner_payload(
                    viewer_quest,
                    return_state=str(planned_row or "RETURN_UNKNOWN"),
                )
            continue
        if quest.state in OPEN_STATES:
            summary_state = "AWAY"
        elif quest.state in {"COMPLETED", "CANCELLED"}:
            summary_state = "RETURNING"
        else:
            continue
        item["personal_stop"] = {
            "planned_personal_stop": True,
            "state": summary_state,
        }

    # An owner may still inspect their latest durable side-quest result when the
    # R63 binding has gone stale. The effective INVALIDATED display never makes it
    # executable or re-targets it to a new shared plan.
    if viewer_payload is None and viewer_member is not None and viewer_split is None:
        viewer_quest = latest_by_member.get(str(viewer_member.id))
        if viewer_quest is not None:
            viewer_payload = _owner_payload(viewer_quest)
    return viewer_payload
