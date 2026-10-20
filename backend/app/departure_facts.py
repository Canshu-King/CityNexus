"""One signed read that answers, per slot of a plan, which place facts this server actually holds.

The V3 order's first item asks for 地点事实统一: source candidate identity, media licence and author,
opening hours, price, and the time the fact was taken, in one typed answer, with unknowns named
instead of filled in. This door is that answer for the slots a traveller is actually looking at --
the activities of one plan version on one journey the caller holds a seat on.

Three deliberate limits:

* **Bounded by durable rows.** The set of slots comes from `Activity` rows of a `PlanVersion` that
  belongs to this journey; nothing here accepts a place name, a URL or a provider id to go and look
  up. That is what keeps a fact read from becoming the cross-user place/network enumeration the
  13:42 order forbids. A slot that points at a row the store does not hold is not a case this door
  answers, because the package schema will not let it happen: `activities.place_id` is a foreign key
  `ON DELETE SET NULL`, so a removed place leaves the slot pointing at nothing, which is the
  `SLOT_HAS_NO_LOCATION` arm below.
* **No provider is asked.** Everything is read out of the rows this server already holds, so the door
  cannot become a way to spend quota or to leak a query. Where a fact is genuinely absent the answer
  is the product's own word for absent, never a plausible number.
* **One writer per judgement.** Whether a row "says when it is open" and whether a row "says what it
  costs" are decided by `app.services._place_window` and `app.services._place_verified_cost`, the
  same two predicates the feasibility gate and the catalogue use; a pinned test keeps this door from
  quietly re-deciding them.

The status words are the ones this product already ships: `KNOWN` / `UNKNOWN` for the two facts
(`app/fact_acquisition.py` closes cost statuses to KNOWN / VERIFIED_PROVIDER, and the same file
answers an unparseable window with `UNKNOWN`), `READY` / `UNAVAILABLE` for a coordinate
(`app/schemas.py` declares the coordinate states), and media stays behind its own door
(`place_media_routes`) because licence and author are that door's business, not this one's.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from types import SimpleNamespace
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Activity, CityService, Place, PlanVersion
from app.db.session import get_session
from app.departure_read import _refuse, _signed_journey
from app.services import _place_verified_cost, _place_window

router = APIRouter()

FACTS_PATH = "/api/v1/journeys/{journey_id}/departure/facts"
REASON_PLAN_REQUIRED = "PLAN_VERSION_ID_REQUIRED"
REASON_PLAN_NOT_IN_JOURNEY = "PLAN_NOT_IN_JOURNEY"

#: The two words this door ever answers for a held fact, plus the coordinate states.
STATE_KNOWN = "KNOWN"
STATE_UNKNOWN = "UNKNOWN"
COORD_READY = "READY"
COORD_UNAVAILABLE = "UNAVAILABLE"

#: Named reasons for an absence. Each one says which row was missing what, so a screen can show
#: "this server has no opening hours for this place" rather than an empty cell. An absence that the
#: row itself declares ("never recorded") is named apart from one it hands us broken ("not an
#: interval"), because those two need different words on a screen and different follow-up orders.
REASON_SLOT_HAS_NO_LOCATION = "SLOT_HAS_NO_LOCATION"
REASON_PLACE_HAS_NO_POINT = "PLACE_ROW_HAS_NO_COORDINATE"
REASON_WINDOW_NOT_RECORDED = "OPENING_HOURS_NOT_RECORDED"
REASON_WINDOW_NOT_AN_INTERVAL = "OPENING_WINDOW_NOT_AN_INTERVAL"
REASON_NO_COST_EVIDENCE = "NO_COST_EVIDENCE_OBJECT"
REASON_COST_NOT_KNOWN = "COST_EVIDENCE_STATUS_NOT_KNOWN"
REASON_SERVICE_HAS_NO_POINT = "CITY_SERVICE_CARRIES_NO_POINT"
REASON_SERVICE_WINDOW_NOT_RECORDED = "SERVICE_AVAILABILITY_NOT_RECORDED"
REASON_SERVICE_WINDOW_UNKNOWN = "SERVICE_AVAILABILITY_NOT_AN_INTERVAL"

MEDIA_DOOR = "/api/v1/journeys/{journey_id}/places/{place_id}/media"


def _identity(row: Any) -> dict[str, Any]:
    """How this server names the thing a slot points at, and what it cannot name."""
    if row is None:
        return {"canonical_id": None, "provider_key": None, "external_id": None,
                "source_identity": None, "detail": REASON_SLOT_HAS_NO_LOCATION}
    provider_key = str(getattr(row, "provider_key", "") or "")
    external_id = str(getattr(row, "external_id", "") or "")
    return {
        "canonical_id": row.id,
        "provider_key": provider_key or None,
        "external_id": external_id or None,
        # The pair is the identity a provider handed us; the canonical id is ours. Showing both is
        # the point: a screen can say which one it is holding, and a draft that only carries the
        # provider half cannot be mistaken for a resolved place.
        "source_identity": f"{provider_key}:{external_id}" if provider_key and external_id else None,
        "detail": None,
    }


def _coordinate(row: Any) -> dict[str, Any]:
    latitude = getattr(row, "latitude", None)
    longitude = getattr(row, "longitude", None)
    if latitude is None or longitude is None:
        reason = (REASON_SERVICE_HAS_NO_POINT if isinstance(row, CityService)
                  else REASON_PLACE_HAS_NO_POINT)
        return {"state": COORD_UNAVAILABLE, "reason": reason,
                "coordinate_system": getattr(row, "coordinate_system", None)}
    return {"state": COORD_READY, "reason": None,
            "coordinate_system": getattr(row, "coordinate_system", None) or "WGS84"}


def _hours(row: Any) -> dict[str, Any]:
    """`_place_window` decides; this only reports which way it decided and what was there."""
    service = isinstance(row, CityService)
    raw = getattr(row, "availability_json", None) if service else getattr(row, "opening_hours_json", None)
    window = _place_window(SimpleNamespace(opening_hours_json=raw))
    if window is not None:
        return {"state": STATE_KNOWN, "detail": None, "open_minutes": window[0],
                "close_minutes": window[1]}
    parsed = json.loads(raw or "{}")
    recorded = bool(parsed.get("open") or parsed.get("close"))
    absent = ((REASON_SERVICE_WINDOW_UNKNOWN if recorded else REASON_SERVICE_WINDOW_NOT_RECORDED)
              if service else
              (REASON_WINDOW_NOT_AN_INTERVAL if recorded else REASON_WINDOW_NOT_RECORDED))
    return {"state": STATE_UNKNOWN, "detail": absent, "open_minutes": None, "close_minutes": None}


def _cost(row: Any, activity: Activity) -> dict[str, Any]:
    """The verified cost of the place, kept apart from whatever number the plan row happens to carry."""
    verified = _place_verified_cost(row)
    detail = None
    if verified is None:
        evidence = json.loads(getattr(row, "metadata_json", None) or "{}").get("cost_evidence")
        detail = REASON_NO_COST_EVIDENCE if not isinstance(evidence, dict) else REASON_COST_NOT_KNOWN
    return {"state": STATE_KNOWN if verified is not None else STATE_UNKNOWN, "detail": detail,
            "verified_amount_minor": verified,
            "activity_estimate_minor": activity.estimated_cost_minor,
            "currency": activity.currency}


def _source_time(row: Any) -> str | None:
    """When the server took the fact, only if the row itself records it."""
    metadata = json.loads(getattr(row, "metadata_json", None) or "{}") if row is not None else {}
    evidence = metadata.get("cost_evidence") or {}
    taken = evidence.get("retrieved_at") or metadata.get("retrieved_at")
    return str(taken) if taken else None


def _slot(session: Session, journey: Any, activity: Activity) -> dict[str, Any]:
    place = session.get(Place, str(activity.place_id)) if activity.place_id else None
    service = (session.get(CityService, str(activity.city_service_id))
               if activity.city_service_id else None)
    row = place if place is not None else service
    return {
        "activity_id": activity.id,
        "sequence_no": activity.sequence_no,
        "activity_type": activity.activity_type,
        "title": activity.title,
        "starts_at": activity.start_at,
        "ends_at": activity.end_at,
        "locked": bool(activity.locked),
        "status": activity.status,
        "location_kind": ("PLACE" if place is not None else
                          "CITY_SERVICE" if service is not None else "NONE"),
        "identity": _identity(row),
        # With no row to report on, all three absences carry the one name that says why there is no row.
        "coordinate": _coordinate(row) if row is not None else {
            "state": COORD_UNAVAILABLE, "reason": REASON_SLOT_HAS_NO_LOCATION,
            "coordinate_system": None},
        "opening_hours": _hours(row) if row is not None else {
            "state": STATE_UNKNOWN, "detail": REASON_SLOT_HAS_NO_LOCATION,
            "open_minutes": None, "close_minutes": None},
        "cost": _cost(row, activity) if row is not None else {
            "state": STATE_UNKNOWN, "detail": REASON_SLOT_HAS_NO_LOCATION,
            "verified_amount_minor": None,
            "activity_estimate_minor": activity.estimated_cost_minor,
            "currency": activity.currency},
        "fact_retrieved_at": _source_time(row),
        # Licence and author stay one door away, on purpose: this door says which facts a row holds,
        # the media door answers what may be shown and who to credit.
        "media_door": MEDIA_DOOR.format(journey_id=journey.id, place_id=place.id) if place is not None else None,
    }


@router.get(FACTS_PATH)
def journey_departure_facts(
    response: Response,
    request: Request,
    journey_id: UUID,
    plan_version_id: str | None = Query(default=None),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    """Per-slot place facts for one plan version of one journey the caller holds a seat on."""
    journey, seat = _signed_journey(request, session, journey_id)
    if plan_version_id is None:
        raise _refuse(422, "plan_version_id is required", REASON_PLAN_REQUIRED,
                      {"query": "plan_version_id", "rows_read": 0})
    plan = session.get(PlanVersion, str(plan_version_id))
    if plan is None or plan.journey_id != journey.id:
        # Answered before any activity row is read: a foreign id must not buy a count of slots.
        raise _refuse(404, f"PlanVersion {plan_version_id} was not found",
                      REASON_PLAN_NOT_IN_JOURNEY,
                      {"journey_id": journey.id, "plan_version_id": plan_version_id})
    activities = session.scalars(
        select(Activity).where(Activity.plan_version_id == plan.id).order_by(Activity.sequence_no)
    ).all()
    slots = [_slot(session, journey, activity) for activity in activities]
    counted = {"known": 0, "unknown": 0}
    for slot in slots:
        for fact in ("opening_hours", "cost"):
            counted["known" if slot[fact]["state"] == STATE_KNOWN else "unknown"] += 1
    response.headers["Cache-Control"] = "private, no-store"
    response.headers["Vary"] = "Authorization, X-CityNexus-Traveler-Token"
    return {
        "journey_id": journey.id,
        "plan_version_id": plan.id,
        "plan_status": plan.status,
        "seat": seat,
        "slots": slots,
        "facts_counted": {"known": counted["known"], "unknown": counted["unknown"]},
        "observed_at": datetime.now(timezone.utc).isoformat(),
    }
