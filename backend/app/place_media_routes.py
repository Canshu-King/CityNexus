"""One GET that answers "what may we actually show for this place" -- nothing else.

Why this file exists: every other route in this product lives in `app/main.py`, and asking Codex to
merge a media endpoint means asking them to merge into a 15k-line file. A router in its own module keeps
the merge surface at two lines in `main.py` plus one new file, which is also what the 17:20 order asked
for as "接线方式".

The route is a read on the same journey-scoped family the other member reads use, it never starts a
write, and it always answers with the media contract -- including when the answer is NO_IMAGE.

Authorization came later than the shape, and the order that asked for it names the hole precisely:
confirming that two rows exist is not the same question as "may this caller see them".  Without the
door below, the path was a way to spend another traveller's money and another traveller's places:
anyone who could guess two uuids got an outbound Wikimedia lookup and a payload about a POI that is
not theirs.  So the door runs BEFORE any provider is asked, and every refusal answers with a status
this product already uses, so the answer cannot be turned into a scanner.

The second GET answers "which place is this map point" for the same journey, from stored identity only.
It exists because the workspace map hands round a source lead, not a `Place.id`, and the client is not
allowed to fix that by passing place text or a picture url.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
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

#: Named so the screen can read the reason out of the envelope instead of guessing from the status.
REASON_MEMBER_REQUIRED = "JOURNEY_MEMBER_REQUIRED"
REASON_PLACE_OUT_OF_SCOPE = "PLACE_NOT_IN_JOURNEY"


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
    """One definition of "does this traveller still hold this journey", borrowed, not re-decided.

    The predicate already exists in `app/main.py` next to the share grants that use it, and two doors
    holding two definitions of membership is how a withdrawn member keeps reading.  It is imported
    inside the call because `app.main` imports this router: a module-level import would be a cycle.
    The cost of the lazy form is that a rename surfaces at request time, so
    `tests/test_qoder_place_media_authorization_r1.py` pins the name it reaches for.
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


@router.get("/api/v1/journeys/{journey_id}/places/{place_id}/media")
async def journey_place_media(
    request: Request,
    journey_id: UUID,
    place_id: str,
    session: Session = Depends(get_session),
    client: httpx.AsyncClient = Depends(_media_client),
) -> dict[str, Any]:
    """Return the PlaceMedia contract for one place this journey actually holds.

    A missing row is 404 -- there is nothing to attribute -- but a place that exists and has no
    showable photograph is a 200 with NO_IMAGE/NO_PERMISSION/UNAVAILABLE, never a 4xx: the traveller's
    screen still has to render the place, and a failure status is content, not an error.

    The order the door comes from is written down: unknown journey 404, no credentials 401, a caller
    who holds no seat 403, and a place this journey does not know 404 -- all of them BEFORE any
    outbound request, so neither the answer nor the traffic can be used to probe somebody else's trip.
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
    payload["coordinate_system"] = str(getattr(row, "coordinate_system", "") or "")
    return payload


@router.get("/api/v1/journeys/{journey_id}/place-identity")
async def journey_place_identity(
    request: Request,
    journey_id: UUID,
    lead: str,
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    """Which place is this map point? Answer with the ids and the region, and ask no provider.

    Codex's map carries a source lead (`real-place-<hex>`, `photon:node/<id>`, `rpc-<hex>`), which is
    not a `Place.id`. This read maps it server-side so the client never has to hand over a place name
    or an image url to get imagery, and it costs one indexed lookup -- no network, no provider spend.
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
    return payload
