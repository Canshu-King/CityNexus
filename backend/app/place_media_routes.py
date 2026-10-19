"""Two GETs about one place in one journey, both answered before any image provider is asked.

`.../places/{place_id}/media` answers the PlaceMedia contract. `.../place-identity?lead=` maps a
workspace source lead onto a `Place.id` from stored identity only -- the map carries a lead, not an
id, and the client may not fix that by sending place text or a picture url.

The door runs first, and every refusal uses a status this product already has: unknown journey 404,
no credentials 401, no seat in force 403, a place this journey does not hold 404 -- all before any
outbound request, so neither the answer nor the traffic can enumerate another traveller's trip.

A read, never a write. Kept in its own module because every other route lives in `app/main.py`, so a
router here keeps the merge surface at two lines plus one file.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from urllib.parse import quote
from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app import place_source_lead
from app.db.models import Journey, Place
from app.db.session import get_session
from app.integrations.media import place_media
from app.traveler_principal import resolve_traveler_principal

router = APIRouter()

LIVE_TIMEOUT_SECONDS = 15.0

#: The two doors, named so the identity read can hand back the exact path the other one serves.
MEDIA_PATH = "/api/v1/journeys/{journey_id}/places/{place_id}/media"
IDENTITY_PATH = "/api/v1/journeys/{journey_id}/place-identity"

#: Named so the screen can read the reason out of the envelope instead of guessing from the status.
REASON_MEMBER_REQUIRED = "JOURNEY_MEMBER_REQUIRED"
REASON_PLACE_OUT_OF_SCOPE = "PLACE_NOT_IN_JOURNEY"


def media_path_for(journey_id: str, place_id: str) -> str:
    """The media door for one place, carrying the id THIS server resolved.

    A source lead can hold a `/` (`photon:node/2`), which cannot survive a path segment, so a client
    holding such a lead used to have to know which leads need a first hop.  It does not have to know
    that any more: the identity read answers with this path, already substituted and already escaped.
    """
    return MEDIA_PATH.format(journey_id=journey_id, place_id=quote(place_id, safe=""))


def _media_client() -> httpx.AsyncClient:
    """Overridable in tests; in production each read gets its own short-lived client."""
    return httpx.AsyncClient(timeout=LIVE_TIMEOUT_SECONDS)


def _refuse(status: int, message: str, reason_code: str, details: dict[str, Any]) -> HTTPException:
    """The house shape for a refusal: a status, a sentence, and the reason code the client reads."""
    refused = HTTPException(status, message)
    refused.reason_code = reason_code  # type: ignore[attr-defined]
    refused.error_details = details  # type: ignore[attr-defined]
    return refused


def _signed_journey_read(request: Request, session: Session, journey_id: UUID) -> Journey:
    """Who is allowed to read this journey, decided before any provider or place is touched.

    Three answers, all of them already used elsewhere in this product: no credentials is 401 with the
    resolver's own named reason, an unknown journey is 404, and a caller who holds no seat is 403. The
    seat question is asked of `app.main`'s single membership definition -- see
    `place_source_lead` for why two doors must not hold two answers to "still a member".
    """
    journey = session.get(Journey, str(journey_id))
    if journey is None:
        raise HTTPException(404, f"Journey {journey_id} was not found")

    principal = resolve_traveler_principal(request, session)
    traveler_id = str(principal.traveler_id)
    if traveler_id != str(journey.traveler_id) and not _membership_is_in_force(
        session, str(journey_id), traveler_id, datetime.now(timezone.utc)
    ):
        raise _refuse(
            403,
            "this journey is not yours to read",
            REASON_MEMBER_REQUIRED,
            {"journey_id": str(journey_id), "traveler_id": traveler_id},
        )
    return journey


def _membership_is_in_force(session: Session, journey_id: str, traveler_id: str,
                            now: datetime) -> bool:
    """Does this traveller still hold this journey -- borrowed from `app/main.py`, not re-decided.

    Two doors holding two definitions of membership is how a withdrawn member keeps reading. The
    import sits inside the call because `app.main` imports this router; a rename would therefore
    surface at request time, so `tests/test_qoder_place_media_authorization_r1.py` pins the name.
    """
    from app.main import _member_is_in_force

    return bool(_member_is_in_force(session, journey_id, traveler_id, now))


def _out_of_scope(journey_id: str, lead: str) -> HTTPException:
    return _refuse(
        404,
        f"Place {lead} was not found in this journey",
        REASON_PLACE_OUT_OF_SCOPE,
        {"journey_id": journey_id, "place_id": lead},
    )


def _place_of_lead(session: Session, journey_id: str, lead: str) -> Place:
    """Turn whatever the client holds into a row THIS journey actually has, or refuse the same way.

    One status for "no such row", "that is not a place lead", and "not in this journey": telling the
    three apart would turn the endpoint into a way to find out which ids belong to somebody else's trip.
    """
    reading = place_source_lead.resolve_place_lead(session, lead, journey_id=journey_id)
    if not reading.resolved or reading.region_conflict:
        raise _out_of_scope(journey_id, lead)
    row = session.get(Place, str(reading.place_id))
    if row is None:
        raise _out_of_scope(journey_id, lead)
    return row


@router.get(MEDIA_PATH)
async def journey_place_media(
    request: Request,
    journey_id: UUID,
    place_id: str,
    session: Session = Depends(get_session),
    client: httpx.AsyncClient = Depends(_media_client),
) -> dict[str, Any]:
    """The PlaceMedia contract for one place this journey actually holds.

    A place that exists with nothing showable is a 200 carrying NO_IMAGE / NO_PERMISSION /
    UNAVAILABLE, never a 4xx: the failure status is content the screen has to render.
    """
    _signed_journey_read(request, session, journey_id)
    row = _place_of_lead(session, str(journey_id), place_id)

    try:
        result = await place_media.collect_place_media(
            place_id=str(row.id),
            label=str(row.name),
            region=str(row.city_code or ""),
            provider_object_id=str(row.external_id or ""),
            client=client,
        )
    finally:
        # The provider read can fail; the socket still has to go back.
        await client.aclose()
    payload = result.as_payload()
    payload["journey_id"] = str(journey_id)
    payload["place_name"] = str(row.name)
    payload["coordinate_system"] = str(row.coordinate_system or "")
    return payload


@router.get(IDENTITY_PATH)
async def journey_place_identity(
    request: Request,
    journey_id: UUID,
    lead: str,
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    """Which place is this map point? Answer with the ids, the region, and the next path to call.

    One indexed lookup, no network, no provider spend. `media_path` is the media door with the
    resolved id already substituted, so a lead that cannot live in a path segment stops being the
    client's problem, and place text or image urls are refused rather than looked up by name.
    """
    _signed_journey_read(request, session, journey_id)
    reading = place_source_lead.resolve_place_lead(session, lead, journey_id=str(journey_id))
    payload = reading.as_payload()
    payload["journey_id"] = str(journey_id)
    if not reading.resolved:
        raise _refuse(
            404,
            f"{lead} is not a place this journey holds",
            reading.reason_code,
            {"journey_id": str(journey_id), "lead": lead, "lead_shape": reading.shape},
        )
    if reading.region_conflict:
        # Identity found but its own region columns disagree: say REGION_CONFLICT rather than let the
        # caller assume the row is trustworthy and put another city's picture on this landmark.
        raise _refuse(
            409,
            f"{lead} carries two different regions",
            "LEAD_REGION_CONFLICT",
            {"journey_id": str(journey_id), "lead": lead, "region": reading.city_code},
        )
    payload["media_path"] = media_path_for(str(journey_id), str(reading.place_id))
    return payload
