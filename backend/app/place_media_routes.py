"""One GET that answers "what may we actually show for this place" -- nothing else.

Why this file exists: every other route in this product lives in `app/main.py`, and asking Codex to
merge a media endpoint means asking them to merge into a 15k-line file. A router in its own module keeps
the merge surface at two lines in `main.py` plus one new file, which is also what the 17:20 order asked
for as "接线方式".

The route is a read on the same journey-scoped family the other member reads use, it never starts a
write, and it always answers with the media contract -- including when the answer is NO_IMAGE.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.models import Journey, Place
from app.db.session import get_session
from app.integrations.media import place_media

router = APIRouter()

LIVE_TIMEOUT_SECONDS = 15.0


def _media_client() -> httpx.AsyncClient:
    """Overridable in tests; in production each read gets its own short-lived client."""
    return httpx.AsyncClient(timeout=LIVE_TIMEOUT_SECONDS)


@router.get("/api/v1/journeys/{journey_id}/places/{place_id}/media")
async def journey_place_media(
    journey_id: UUID,
    place_id: str,
    session: Session = Depends(get_session),
    client: httpx.AsyncClient = Depends(_media_client),
) -> dict[str, Any]:
    """Return the PlaceMedia contract for one place row this journey knows about.

    A missing row is 404 -- there is nothing to attribute -- but a place that exists and has no
    showable photograph is a 200 with NO_IMAGE/NO_PERMISSION/UNAVAILABLE, never a 4xx: the traveller's
    screen still has to render the place, and a failure status is content, not an error.
    """
    # A journey-scoped read has to say so: an unknown journey is 404 before any provider is asked,
    # otherwise a typo'd journey id still spends a live outbound request.
    if session.get(Journey, str(journey_id)) is None:
        raise HTTPException(404, f"Journey {journey_id} was not found")
    row = session.get(Place, str(place_id))
    if row is None:
        raise HTTPException(404, f"Place {place_id} was not found")
    try:
        result = await place_media.collect_place_media(
            place_id=str(row.id),
            label=str(row.name),
            region=str(row.city_code or ""),
            provider_object_id=str(row.external_id or ""),
            client=client,
        )
    finally:
        await client.aclose()
    payload = result.as_payload()
    payload["journey_id"] = str(journey_id)
    payload["place_name"] = str(row.name)
    payload["coordinate_system"] = str(getattr(row, "coordinate_system", "") or "")
    return payload
