"""Member-scoped, privacy-preserving group presence and rendezvous targeting."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
import math
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import (
    Activity,
    Commitment,
    Journey,
    JourneyMember,
    LocationObservation,
    Place,
    RouteAcquisitionOperation,
    Traveler,
)
from app.execution.clock import execution_clock

LOCATION_FRESHNESS_SECONDS = 300
MAX_USEFUL_ACCURACY_M = 100.0
PROTECTED_LEVELS = {"C3_GUARANTEED", "C4_ANCHORED"}


def _stamp(value: str | None) -> datetime | None:
    try:
        result = datetime.fromisoformat(str(value or ""))
    except ValueError:
        return None
    if result.tzinfo is None:
        return None
    return result.astimezone(timezone.utc)


def _member_in_force(member: JourneyMember, now: datetime) -> bool:
    if member.removed_at:
        return False
    expiry = _stamp(member.expires_at)
    return member.expires_at is None or (expiry is not None and expiry > now)


def _distance_m(a: LocationObservation, b: LocationObservation) -> float:
    earth_radius = 6_371_000.0
    lat1, lat2 = math.radians(a.latitude), math.radians(b.latitude)
    dlat = lat2 - lat1
    dlon = math.radians(b.longitude - a.longitude)
    value = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return earth_radius * 2 * math.atan2(math.sqrt(value), math.sqrt(max(0.0, 1 - value)))


def rendezvous_target(session: Session, journey: Journey) -> tuple[Activity, Place] | None:
    """Use the next exact active-plan stop, preferring the next C3/C4 anchor."""
    if not journey.active_plan_version_id:
        return None
    activities = session.scalars(
        select(Activity)
        .where(Activity.plan_version_id == journey.active_plan_version_id)
        .order_by(Activity.sequence_no, Activity.id)
    ).all()
    current = next((row for row in activities if row.id == journey.current_activity_id), None)
    current_state = str(current.status or "").upper() if current else ""
    eligible = [row for row in activities if str(row.status or "").upper() not in {"COMPLETED", "SKIPPED"}]
    if current is not None and current_state in {"ARRIVED", "IN_PROGRESS", "COMPLETED", "SKIPPED"}:
        eligible = [row for row in eligible if row.sequence_no > current.sequence_no]
    # If already en route (or the next activity has not started), that exact stop is the
    # rendezvous. Otherwise use the next uncompleted stop. Never synthesize a midpoint.
    eligible = [row for row in eligible if row.place_id]
    if not eligible:
        return None
    activity_ids = [row.id for row in eligible]
    commitments = session.scalars(
        select(Commitment).where(
            Commitment.journey_id == journey.id,
            Commitment.activity_id.in_(activity_ids),
            Commitment.status == "ACTIVE",
        )
    ).all()
    protected_ids = {
        str(row.activity_id)
        for row in commitments
        if str(row.level or "").upper() in PROTECTED_LEVELS
    }
    target = next((row for row in eligible if row.id in protected_ids), eligible[0])
    place = session.get(Place, str(target.place_id))
    return (target, place) if place is not None else None


def _member_observation(
    session: Session, journey: Journey, member: JourneyMember
) -> LocationObservation | None:
    rows = session.scalars(
        select(LocationObservation)
        .where(
            LocationObservation.journey_id == journey.id,
            LocationObservation.traveler_id == member.traveler_id,
            LocationObservation.journey_member_id == member.id,
        )
    ).all()
    return max(
        rows,
        key=lambda row: (_stamp(row.captured_at) or datetime.min.replace(tzinfo=timezone.utc), row.id),
        default=None,
    )


def _location_state(row: LocationObservation | None, now: datetime) -> tuple[str, int | None]:
    if row is None:
        return "MISSING", None
    captured = _stamp(row.captured_at)
    if captured is None:
        return "UNKNOWN", None
    age = int((now - captured).total_seconds())
    if age < -30:
        return "UNKNOWN", age
    if age > LOCATION_FRESHNESS_SECONDS:
        return "STALE", age
    if float(row.accuracy_m) > MAX_USEFUL_ACCURACY_M:
        return "IMPRECISE", age
    return "RECENT", max(0, age)


def _route_eta(
    session: Session,
    journey: Journey,
    row: LocationObservation | None,
    target_activity: Activity | None,
) -> tuple[int | None, str | None]:
    if row is None or target_activity is None:
        return None, None
    route = session.scalar(
        select(RouteAcquisitionOperation)
        .where(
            RouteAcquisitionOperation.journey_id == journey.id,
            RouteAcquisitionOperation.origin_key == f"location-observation:{row.id}",
            RouteAcquisitionOperation.target_key == str(target_activity.place_id or ""),
            RouteAcquisitionOperation.target_activity_id == target_activity.id,
            RouteAcquisitionOperation.status == "COMPLETED",
        )
        .order_by(RouteAcquisitionOperation.finished_at.desc(), RouteAcquisitionOperation.id.desc())
    )
    if route is None:
        return None, None
    try:
        result = json.loads(route.result_json or "{}")
        provenance = str(result.get("provenance") or "UNKNOWN").upper()
        minutes = result.get("duration_min")
        if minutes is None or provenance != "LIVE_PROVIDER_CAPTURE":
            return None, None
        return max(0, int(minutes)), provenance
    except (TypeError, ValueError, json.JSONDecodeError):
        return None, None


def rendezvous_commitment_risk(
    session: Session,
    journey: Journey,
    target_activity: Activity,
    *,
    route_duration_min: int,
    authority: str,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Project whether this member-specific route threatens the shared protected stop."""

    base = {
        "state": "NO_PROTECTED_RENDEZVOUS_COMMITMENT",
        "authority": authority,
        "next_commitment": None,
        "predicted_arrival_at": None,
        "slack_after_buffer_min": None,
    }
    commitments = session.scalars(
        select(Commitment).where(
            Commitment.journey_id == journey.id,
            Commitment.activity_id == target_activity.id,
            Commitment.status == "ACTIVE",
        )
    ).all()
    commitment = next(
        (
            row
            for row in commitments
            if str(row.level or "").upper() in PROTECTED_LEVELS
        ),
        None,
    )
    if commitment is None:
        return base
    try:
        policy = json.loads(commitment.policy_json or "{}")
    except (TypeError, json.JSONDecodeError):
        policy = {}
    scheduled = _stamp(
        str(policy.get("scheduled_start_at") or target_activity.start_at)
    )
    reference = (now or execution_clock.now()).astimezone(timezone.utc)
    if scheduled is None:
        return {
            **base,
            "state": "COMMITMENT_TIME_UNKNOWN",
            "next_commitment": {
                "commitment_id": commitment.id,
                "activity_id": target_activity.id,
                "title": target_activity.title,
            },
        }
    buffer_min = 5
    for key in ("safety_buffer_min", "required_buffer_min", "resilience_buffer_min"):
        if policy.get(key) is None:
            continue
        try:
            buffer_min = max(0, int(policy[key]))
            break
        except (TypeError, ValueError):
            continue
    duration = max(0, int(route_duration_min))
    predicted = reference + timedelta(minutes=duration)
    slack = int((scheduled - predicted).total_seconds() // 60) - buffer_min
    state = (
        "COMMITMENT_AT_RISK"
        if slack < 0
        else "LOW_BUFFER"
        if slack < max(10, buffer_min * 2)
        else "WITHIN_BUFFER"
    )
    return {
        "state": state,
        "authority": authority,
        "next_commitment": {
            "commitment_id": commitment.id,
            "activity_id": target_activity.id,
            "title": target_activity.title,
            "scheduled_at": scheduled.isoformat(),
            "safety_buffer_min": buffer_min,
        },
        "predicted_arrival_at": predicted.isoformat(),
        "slack_after_buffer_min": slack,
        "route_duration_min": duration,
        "basis": "DIRECT_MEMBER_ROUTE_TO_EXISTING_SHARED_COMMITMENT",
    }


def _group_state(
    *,
    members: list[JourneyMember],
    location_states: dict[str, str],
    coarse_group: dict[str, str],
) -> str:
    """Return one stable group-level fact so every consumer tells the same story."""

    if len(members) <= 1:
        return "SINGLE_TRAVELLER"
    if any(coarse_group.get(member.id) == "SPLIT_FROM_GROUP" for member in members):
        return "GROUP_SPLIT_ADVISORY"
    if all(
        location_states.get(member.id) == "RECENT"
        and coarse_group.get(member.id) == "WITH_GROUP"
        for member in members
    ):
        return "TOGETHER"
    if any(location_states.get(member.id) == "MISSING" for member in members):
        return "MEMBER_LOCATION_MISSING"
    if any(
        location_states.get(member.id) in {"STALE", "IMPRECISE", "UNKNOWN"}
        for member in members
    ):
        return "GROUP_LOCATION_STALE"
    return "GROUP_LOCATION_UNKNOWN"


def group_presence_projection(
    session: Session, journey: Journey, *, viewer_member_id: str | None
) -> dict[str, Any]:
    """Return coarse states only; no coordinates or observation identifiers leave the server."""
    if not viewer_member_id:
        return {
            "state": "MEMBER_IDENTITY_UNAVAILABLE",
            "authority": "SIGNED_TRAVELER_PRINCIPAL_REQUIRED",
            "members": [],
            "rendezvous": None,
            "can_guide": False,
        }
    now = execution_clock.now().astimezone(timezone.utc)
    members = [
        member for member in session.scalars(
            select(JourneyMember).where(JourneyMember.journey_id == journey.id)
        ).all() if _member_in_force(member, now)
    ]
    viewer = next((member for member in members if member.id == str(viewer_member_id)), None)
    if viewer is None:
        return {
            "state": "MEMBER_IDENTITY_UNAVAILABLE",
            "authority": "SIGNED_TRAVELER_PRINCIPAL_REQUIRED",
            "members": [],
            "rendezvous": None,
            "can_guide": False,
        }
    target_pair = rendezvous_target(session, journey)
    target_activity, target_place = target_pair if target_pair else (None, None)
    rows = {member.id: _member_observation(session, journey, member) for member in members}
    location_states = {member_id: _location_state(row, now)[0] for member_id, row in rows.items()}
    coarse_group = {member.id: "UNKNOWN" for member in members}
    precise = [member for member in members if location_states[member.id] == "RECENT"]
    if len(precise) < 2:
        precise = []
    for member in precise:
        comparisons = []
        row = rows[member.id]
        for other in precise:
            if member.id == other.id:
                continue
            other_row = rows[other.id]
            threshold = max(250.0, 3.0 * (float(row.accuracy_m) + float(other_row.accuracy_m)))
            comparisons.append(_distance_m(row, other_row) <= threshold)
        coarse_group[member.id] = "WITH_GROUP" if all(comparisons) else "SPLIT_FROM_GROUP"

    projected = []
    for member in members:
        traveler = session.get(Traveler, member.traveler_id)
        row = rows[member.id]
        state, age = _location_state(row, now)
        eta, eta_provenance = _route_eta(session, journey, row, target_activity)
        projected.append({
            "member_id": member.id,
            "display_name": traveler.display_name if traveler else "Traveller",
            "is_viewer": member.id == viewer.id,
            "location_state": state,
            "group_state": coarse_group[member.id],
            "age_seconds": age,
            "authority": "ADVISORY_FOREGROUND_WEB" if row else "NO_BOUND_LOCATION",
            "route_eta_minutes": eta,
            "route_eta_provenance": eta_provenance,
        })
    state = _group_state(
        members=members,
        location_states=location_states,
        coarse_group=coarse_group,
    )
    rendezvous_ready = target_activity is not None and target_place is not None
    viewer_row = rows.get(viewer.id)
    viewer_eta, viewer_eta_provenance = _route_eta(
        session, journey, viewer_row, target_activity
    )
    return {
        "state": state,
        "authority": "ADVISORY_FOREGROUND_WEB_NOT_DEVICE_ATTESTED",
        "members": projected,
        "rendezvous": (
            {"activity_id": target_activity.id, "title": target_activity.title,
             "place_name": target_place.name, "basis": "ACTIVE_PLAN_EXACT_PLACE"}
            if rendezvous_ready else None
        ),
        "rendezvous_state": (
            "RENDEZVOUS_ROUTE_READY"
            if viewer_eta is not None
            else "RENDEZVOUS_TARGET_READY"
            if rendezvous_ready
            else "RENDEZVOUS_TARGET_UNAVAILABLE"
        ),
        "viewer_route": (
            {
                "eta_minutes": viewer_eta,
                "provenance": viewer_eta_provenance,
            }
            if viewer_eta is not None
            else None
        ),
        "can_guide": bool(
            len(members) > 1
            and
            str(journey.status).upper() == "ACTIVE"
            and rendezvous_ready
        ),
    }
