"""Traveller-facing collective state for the Journey Operator."""
from __future__ import annotations

import json
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import CollectiveAuthorityReceipt, Journey, JourneyMember, JourneyMission, Traveler


def classify_collective_operator_state(
    *,
    member_count: int,
    status: str | None,
    response_count: int = 0,
    authority_receipt_present: bool = False,
    stale: bool = False,
) -> str:
    if member_count <= 1:
        return "SINGLE_TRAVELLER"
    if stale or str(status or "").upper() == "STALE":
        return "COLLECTIVE_STALE"
    if authority_receipt_present:
        return "COLLECTIVE_AUTHORIZED"
    state = str(status or "").upper()
    if state == "WAITING_FOR_MEMBERS":
        return "WAITING_FOR_MEMBERS"
    if state == "MEDIATION_REQUIRED":
        return "MEDIATING"
    if state == "RESOLVED":
        return "COLLECTIVE_READY"
    if response_count and response_count < member_count:
        return "WAITING_FOR_MEMBERS"
    return "COLLECTIVE_NEEDS_ATTENTION"


def _json(value: str | None, fallback: Any) -> Any:
    try:
        return json.loads(value or "")
    except (TypeError, json.JSONDecodeError):
        return fallback


def collective_operator_projection(
    session: Session,
    journey: Journey,
    *,
    viewer_member_id: str | None = None,
) -> dict[str, Any]:
    members = list(
        session.scalars(
            select(JourneyMember)
            .where(
                JourneyMember.journey_id == journey.id,
                JourneyMember.removed_at.is_(None),
            )
            .order_by(JourneyMember.created_at, JourneyMember.id)
        ).all()
    )
    if len(members) <= 1:
        return {
            "state": "SINGLE_TRAVELLER",
            "required_count": 1,
            "response_count": 0,
            "viewer_has_responded": False,
            "members": [],
            "options": [],
            "mission_id": None,
            "authority_receipt_id": None,
        }

    mission = session.scalar(
        select(JourneyMission)
        .where(
            JourneyMission.journey_id == journey.id,
            JourneyMission.is_standing.is_(False),
            JourneyMission.status.in_(("WAITING_FOR_MEMBERS", "ANSWERED", "RUNNING", "CREATED", "DEGRADED")),
        )
        .order_by(JourneyMission.created_at.desc(), JourneyMission.id.desc())
    )
    if mission is None:
        return {
            "state": "COLLECTIVE_NEEDS_ATTENTION",
            "required_count": len(members),
            "response_count": 0,
            "viewer_has_responded": False,
            "members": [],
            "options": [],
            "mission_id": None,
            "authority_receipt_id": None,
        }

    clarification = _json(mission.clarification_json, {})
    if not isinstance(clarification, dict) or clarification.get("kind") != "COLLECTIVE_TRADEOFF":
        return {
            "state": "COLLECTIVE_NEEDS_ATTENTION",
            "required_count": len(members),
            "response_count": 0,
            "viewer_has_responded": False,
            "members": [],
            "options": [],
            "mission_id": mission.id,
            "authority_receipt_id": None,
        }

    required_ids = [str(item) for item in clarification.get("required_member_ids") or []]
    responses = clarification.get("responses") or {}
    member_rows = [item for item in members if item.id in set(required_ids)]
    member_views = []
    for item in member_rows:
        traveler = session.get(Traveler, item.traveler_id)
        member_views.append(
            {
                "member_id": item.id,
                "display_name": traveler.display_name if traveler is not None else "Traveller",
                "role": item.role,
                "responded": item.id in responses,
                "is_viewer": bool(viewer_member_id and viewer_member_id == item.id),
            }
        )

    authority_receipt_id = clarification.get("authority_receipt_id")
    receipt = (
        session.get(CollectiveAuthorityReceipt, str(authority_receipt_id))
        if authority_receipt_id
        else None
    )
    response_count = len(set(required_ids).intersection(responses))
    state = classify_collective_operator_state(
        member_count=len(required_ids) or len(member_rows),
        status=str(clarification.get("status") or ""),
        response_count=response_count,
        authority_receipt_present=bool(receipt is not None and receipt.invalidated_at is None),
        stale=str(clarification.get("status") or "").upper() == "STALE",
    )
    options = [
        {
            "proposal_id": item.get("proposal_id"),
            "label": item.get("label") or item.get("summary") or "Recovery option",
            "schedule_delta_min": item.get("schedule_delta_min") or item.get("end_time_delta_min"),
            "cost_delta_minor": item.get("cost_delta_minor"),
            "fit_subject_place_ids": item.get("fit_subject_place_ids") or [],
        }
        for item in clarification.get("candidate_options") or []
        if isinstance(item, dict)
    ]
    return {
        "state": state,
        "mission_id": mission.id,
        "clarification_id": clarification.get("clarification_id"),
        "decision_epoch": clarification.get("decision_epoch"),
        "required_count": len(required_ids),
        "response_count": response_count,
        "viewer_member_id": viewer_member_id,
        "viewer_has_responded": bool(viewer_member_id and viewer_member_id in responses),
        "members": member_views,
        "options": options,
        "authority_receipt_id": receipt.id if receipt is not None else None,
        "selected_proposal_id": clarification.get("selected_proposal_id"),
    }
