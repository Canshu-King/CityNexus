"""Grounded launch-origin projection for the first/next Journey move."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import (
    AccommodationOfferSnapshot,
    Activity,
    Journey,
    JourneyTripContext,
    LocationObservation,
    StayJourneyOption,
)
from app.execution.clock import execution_clock

_MAX_LOCATION_AGE_SECONDS = 300.0
_MAX_LOCATION_ACCURACY_M = 100.0


def _aware(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return parsed.astimezone(timezone.utc)


def _load(value: str | None) -> dict[str, Any]:
    try:
        parsed = json.loads(value or "{}")
    except (TypeError, json.JSONDecodeError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _fresh_location(
    session: Session, journey: Journey, *, now: datetime
) -> LocationObservation | None:
    row = session.scalar(
        select(LocationObservation)
        .where(LocationObservation.journey_id == journey.id)
        .order_by(LocationObservation.captured_at.desc(), LocationObservation.id.desc())
    )
    if row is None:
        return None
    captured = _aware(row.captured_at)
    if captured is None:
        return None
    age = (now - captured).total_seconds()
    if age < -60 or age > _MAX_LOCATION_AGE_SECONDS:
        return None
    if float(row.accuracy_m) > _MAX_LOCATION_ACCURACY_M:
        return None
    return row


def _selected_stay(
    session: Session,
    journey: Journey,
    *,
    target_start: datetime | None,
) -> tuple[StayJourneyOption, AccommodationOfferSnapshot] | None:
    option = session.scalar(
        select(StayJourneyOption)
        .where(
            StayJourneyOption.journey_id == journey.id,
            StayJourneyOption.status == "SELECTED",
        )
        .order_by(StayJourneyOption.rank, StayJourneyOption.id)
    )
    if option is None:
        return None
    offer = session.get(AccommodationOfferSnapshot, option.accommodation_offer_id)
    if offer is None:
        return None
    if target_start is None:
        return None
    check_in = _aware(offer.check_in_at)
    check_out = _aware(offer.check_out_at)
    if check_in is None or check_out is None:
        return None
    if not (check_in <= target_start < check_out):
        return None
    return option, offer


def _arrival_anchor(
    session: Session,
    journey: Journey,
    *,
    target_start: datetime | None,
) -> dict[str, Any] | None:
    context = session.get(JourneyTripContext, journey.id)
    if context is None:
        return None
    anchor = _load(context.arrival_anchor_json)
    if not anchor:
        return None
    at = _aware(str(anchor.get("at") or ""))
    if at is None or target_start is None or at > target_start:
        return None
    if anchor.get("latitude") is None or anchor.get("longitude") is None:
        return None
    return anchor


def grounded_launch_origin(
    session: Session,
    journey: Journey,
    *,
    target_activity: Activity | None,
    previous_activity: Activity | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Resolve one routable launch origin without asserting physical execution."""

    stamp = (now or execution_clock.now()).astimezone(timezone.utc)
    target_start = _aware(target_activity.start_at if target_activity is not None else None)
    target_id = str(target_activity.id) if target_activity is not None else None

    if previous_activity is not None and previous_activity.place_id:
        return {
            "state": "READY",
            "source": "PREVIOUS_ACTIVITY",
            "authority": "PLAN_EXECUTION_CONTEXT",
            "origin_key": str(previous_activity.place_id),
            "name": getattr(previous_activity, "title", None),
            "latitude": None,
            "longitude": None,
            "captured_at": None,
            "provider_key": None,
            "target_activity_id": target_id,
            "reason_code": "PREVIOUS_ACTIVITY_HAS_EXACT_PLACE",
        }

    location = _fresh_location(session, journey, now=stamp)
    if location is not None:
        return {
            "state": "READY",
            "source": "FOREGROUND_LOCATION",
            "authority": "ADVISORY_FOREGROUND",
            "origin_key": f"location:{location.id}",
            "name": "Shared location",
            "latitude": float(location.latitude),
            "longitude": float(location.longitude),
            "captured_at": location.captured_at,
            "provider_key": None,
            "target_activity_id": target_id,
            "reason_code": "FRESH_FOREGROUND_LOCATION",
        }

    stay = _selected_stay(session, journey, target_start=target_start)
    if stay is not None:
        option, offer = stay
        return {
            "state": "READY",
            "source": "SELECTED_STAY",
            "authority": "PLANNED_GROUNDED_ORIGIN",
            "origin_key": f"stay-offer:{offer.id}",
            "name": offer.property_name,
            "latitude": float(offer.latitude),
            "longitude": float(offer.longitude),
            "captured_at": offer.captured_at,
            "provider_key": offer.provider_key,
            "target_activity_id": target_id,
            "reason_code": "SELECTED_STAY_COVERS_TARGET_START",
            "stay_option_id": option.id,
            "stay_offer_id": offer.id,
        }

    anchor = _arrival_anchor(session, journey, target_start=target_start)
    if anchor is not None:
        return {
            "state": "READY",
            "source": "ARRIVAL_ANCHOR",
            "authority": "PLANNED_GROUNDED_ORIGIN",
            "origin_key": str(anchor.get("semantic_key") or anchor.get("reservation_id") or "arrival-anchor"),
            "name": anchor.get("location") or anchor.get("name") or "Arrival point",
            "latitude": float(anchor["latitude"]),
            "longitude": float(anchor["longitude"]),
            "captured_at": anchor.get("at"),
            "provider_key": anchor.get("provider_key"),
            "target_activity_id": target_id,
            "reason_code": "ARRIVAL_ANCHOR_PRECEDES_TARGET",
        }

    return {
        "state": "UNKNOWN_ORIGIN",
        "source": None,
        "authority": "NONE",
        "origin_key": None,
        "name": None,
        "latitude": None,
        "longitude": None,
        "captured_at": None,
        "provider_key": None,
        "target_activity_id": target_id,
        "reason_code": "NO_GROUNDED_LAUNCH_ORIGIN",
    }
