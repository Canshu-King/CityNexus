"""Validate explicitly requested cross-Journey reuse of canonical GoalTask Places.

This module only returns IDs after checking the source task and its live
materialization chain. It never copies source task state or edits any source row.
"""

from __future__ import annotations

import json
import math
from typing import Any
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Journey, JourneyMember, JourneyMission, Place, RealPlaceCandidate
from app.traveler_principal import _member_is_in_force, member_has_capability

_GOAL_PLANNING_MODE = "GOAL_PLANNING"
_MAX_REUSED_PLACE_IDS = 80
_COORDINATE_TOLERANCE = 1e-6


def _json_object(raw: str | None) -> dict[str, Any]:
    try:
        value = json.loads(raw or "{}")
    except (TypeError, ValueError):
        return {}
    return value if isinstance(value, dict) else {}


def _requested_place_ids(days: Any) -> list[str]:
    if not isinstance(days, list) or not 1 <= len(days) <= 14:
        raise HTTPException(422, "DRAFT_DAYS_INVALID")

    place_ids: list[str] = []
    for day in days:
        if not isinstance(day, dict) or not isinstance(day.get("slots"), list):
            continue
        for slot in day["slots"]:
            if not isinstance(slot, dict):
                continue
            value = slot.get("place_id")
            if value is None or value == "":
                continue
            if not isinstance(value, str) or not value or value != value.strip():
                raise HTTPException(422, "SOURCE_PLACE_ID_INVALID")
            if value not in place_ids:
                place_ids.append(value)

    if not place_ids:
        raise HTTPException(422, "SOURCE_PLACE_IDS_REQUIRED")
    if len(place_ids) > _MAX_REUSED_PLACE_IDS:
        raise HTTPException(422, "GOAL_TASK_PLACE_LIMIT_EXCEEDED")
    return place_ids


def _coordinates_match(candidate: RealPlaceCandidate, place: Place) -> bool:
    try:
        candidate_latitude = float(candidate.latitude)
        candidate_longitude = float(candidate.longitude)
        place_latitude = float(place.latitude)
        place_longitude = float(place.longitude)
    except (TypeError, ValueError, OverflowError):
        return False

    values = (candidate_latitude, candidate_longitude, place_latitude, place_longitude)
    if not all(math.isfinite(value) for value in values):
        return False
    if not (
        -90 <= candidate_latitude <= 90
        and -180 <= candidate_longitude <= 180
        and -90 <= place_latitude <= 90
        and -180 <= place_longitude <= 180
    ):
        return False
    return math.isclose(
        candidate_latitude,
        place_latitude,
        rel_tol=0,
        abs_tol=_COORDINATE_TOLERANCE,
    ) and math.isclose(
        candidate_longitude,
        place_longitude,
        rel_tol=0,
        abs_tol=_COORDINATE_TOLERANCE,
    )


def _require_live_canonical_identity(
    session: Session,
    source_journey: Journey,
    target_journey: Journey,
    place_id: str,
) -> None:
    place = session.get(Place, place_id)
    if place is None:
        raise HTTPException(422, "SOURCE_PLACE_IDENTITY_INVALID")

    if (
        str(place.city_code) != str(source_journey.city_code)
        or str(place.city_code) != str(target_journey.city_code)
        or str(place.coordinate_system or "").strip().upper() != "WGS84"
        or not str(place.provider_key or "").strip()
        or not str(place.external_id or "").strip()
    ):
        raise HTTPException(422, "SOURCE_PLACE_IDENTITY_INVALID")

    linked_candidates = session.scalars(
        select(RealPlaceCandidate).where(
            RealPlaceCandidate.journey_id == str(source_journey.id),
            RealPlaceCandidate.materialized_place_id == str(place.id),
        )
    ).all()
    if not linked_candidates:
        raise HTTPException(422, "SOURCE_PLACE_LIVE_EVIDENCE_REQUIRED")
    candidate = next(
        (
            item
            for item in linked_candidates
            if str(item.provider_key) == str(place.provider_key)
            and str(item.external_id) == str(place.external_id)
        ),
        None,
    )
    if candidate is None:
        raise HTTPException(422, "SOURCE_PLACE_IDENTITY_INVALID")

    metadata = _json_object(candidate.metadata_json)
    evidence = _json_object(candidate.evidence_json)
    if (
        str(candidate.status or "").strip().upper() != "DISCOVERED"
        or str(metadata.get("discovery_mode") or "").strip().lower() != "live"
        or str(evidence.get("provenance") or "").strip().upper() != "LIVE_PROVIDER"
        or str(evidence.get("provider") or "").strip() != str(candidate.provider_key)
    ):
        raise HTTPException(422, "SOURCE_PLACE_LIVE_EVIDENCE_REQUIRED")

    if (
        str(candidate.materialized_place_id or "") != str(place.id)
        or str(candidate.city_code) != str(source_journey.city_code)
        or str(candidate.provider_key) != str(place.provider_key)
        or str(candidate.external_id) != str(place.external_id)
        or not _coordinates_match(candidate, place)
    ):
        raise HTTPException(422, "SOURCE_PLACE_IDENTITY_INVALID")


def validate_source_task_place_reuse(
    session: Session,
    target_journey: Journey,
    target_member: JourneyMember,
    target_task_id: str | UUID,
    source_task_id: str | UUID,
    days: Any,
) -> list[str]:
    """Return only explicitly referenced, source-owned canonical Place IDs.

    Scope mismatches are denied before any target task mutation. Each accepted ID
    must be present in the source task's own candidate list and backed by that
    source Journey's live RealPlaceCandidate row for the exact canonical provider
    identity and WGS-84 geometry.
    """
    requested_ids = _requested_place_ids(days)
    if str(source_task_id) == str(target_task_id):
        raise HTTPException(403, "SOURCE_GOAL_TASK_SCOPE_INVALID")
    if str(target_member.traveler_id) != str(target_journey.traveler_id):
        raise HTTPException(403, "SOURCE_GOAL_TASK_SCOPE_INVALID")

    source_mission = session.scalar(
        select(JourneyMission)
        .where(JourneyMission.id == str(source_task_id))
        .with_for_update()
    )
    if source_mission is None:
        raise HTTPException(403, "SOURCE_GOAL_TASK_SCOPE_INVALID")
    source_journey = session.get(Journey, str(source_mission.journey_id))
    if source_journey is None:
        raise HTTPException(403, "SOURCE_GOAL_TASK_SCOPE_INVALID")
    source_owner_member = session.scalar(
        select(JourneyMember).where(
            JourneyMember.journey_id == str(source_journey.id),
            JourneyMember.traveler_id == str(source_journey.traveler_id),
        )
    )

    if (
        str(source_journey.id) == str(target_journey.id)
        or source_journey.deleted_at is not None
        or str(source_mission.traveler_id) != str(target_member.traveler_id)
        or str(source_journey.traveler_id) != str(target_member.traveler_id)
        or source_owner_member is None
        or not _member_is_in_force(source_owner_member)
        or not member_has_capability(session, source_owner_member, "JOURNEY_READ")
        or str(source_journey.city_code) != str(target_journey.city_code)
        or source_mission.trigger_event_id is not None
        or str(source_mission.requested_autonomy or "") != "PLAN_ONLY"
    ):
        raise HTTPException(403, "SOURCE_GOAL_TASK_SCOPE_INVALID")

    source_intent = _json_object(source_mission.intent_json)
    source_task = source_intent.get("goal_task")
    if (
        source_intent.get("mode") != _GOAL_PLANNING_MODE
        or not isinstance(source_task, dict)
        or source_task.get("schema_version") != 1
        or str(source_task.get("journey_id") or "") != str(source_journey.id)
    ):
        raise HTTPException(403, "SOURCE_GOAL_TASK_SCOPE_INVALID")

    raw_owned_ids = source_task.get("candidate_place_ids")
    if not isinstance(raw_owned_ids, list):
        raise HTTPException(403, "SOURCE_GOAL_TASK_SCOPE_INVALID")
    owned_ids = {
        str(value)
        for value in raw_owned_ids
        if isinstance(value, (str, UUID))
    }
    for place_id in requested_ids:
        if place_id not in owned_ids:
            raise HTTPException(403, "SOURCE_PLACE_NOT_IN_TASK_SCOPE")
        _require_live_canonical_identity(
            session,
            source_journey,
            target_journey,
            place_id,
        )

    return requested_ids
