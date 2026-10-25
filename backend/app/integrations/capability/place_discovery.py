"""The write half of the place-lead surface: a located lead becomes a `places` row.

`place_leads` answers "where is this place" from whichever provider is allowed to speak; nothing
there touches a Session.  This module is the one place that lands those answers in the catalogue, so
the doors that already read `places` (the POI import resolver, the mobility capture's place lookup,
`GET /api/v1/places`) reach a provider-discovered place without knowing which provider it came from.

Two rules the schema already states and this module keeps:

  * the stored geometry is WGS-84 (`coordinate_system`), while `source_coordinate_system` records what
    the provider actually handed us -- an Amap answer is GCJ-02, so the row says both;
  * identity is `(provider_key, external_id)`, so discovering the same provider item twice updates one
    row instead of minting a second place with a slightly different position.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Iterable
from uuid import NAMESPACE_URL, uuid5

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Place
from app.integrations.capability.place_leads import PlaceLead

# A discovered provider item is a point of interest, not a schedule node: the categories
# `_STRUCTURAL_PLACE_CATEGORIES` names must never be minted here, because a structural row is a
# journey-owned anchor rather than somewhere a traveller can choose to visit.
DISCOVERED_CATEGORY = "poi"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _place_id(source: str, item_id: str) -> str:
    return str(uuid5(NAMESPACE_URL, f"place:{source}:{item_id}"))


def _metadata(lead: PlaceLead) -> dict[str, Any]:
    return {
        "coordinate_crs": lead.coordinate_system,
        "source_coordinate_crs": lead.native_coordinate_system,
        "conversion": lead.conversion,
        "captured_at": lead.captured_at,
        "region": lead.region,
        "adcode": lead.adcode,
        "unknown_fields": list(lead.unknown_fields),
    }


def persist_leads(
    session: Session, leads: Iterable[PlaceLead], *, city_code: str
) -> list[dict[str, Any]]:
    """Upsert every lead that carries a position, keyed by the provider's own item id.

    A lead with no position is deliberately not stored: `places.latitude` is NOT NULL, and inventing
    a coordinate would make a place nobody located routable. It stays in the caller's response with
    `unknown_fields: ["position"]`, which is the difference between "not found" and "not placed".
    """
    persisted: list[dict[str, Any]] = []
    for lead in leads:
        if not lead.has_position():
            continue
        row = session.scalar(
            select(Place).where(
                Place.provider_key == lead.source,
                Place.external_id == lead.provider_item_id,
            )
        )
        if row is None:
            row = Place(
                id=_place_id(lead.source, lead.provider_item_id),
                provider_key=lead.source,
                external_id=lead.provider_item_id,
                city_code=city_code,
                name=lead.name,
                category=DISCOVERED_CATEGORY,
                latitude=float(lead.latitude),
                longitude=float(lead.longitude),
                opening_hours_json="{}",
                tags_json=_json([lead.source]),
                metadata_json=_json(_metadata(lead)),
                updated_at=_now(),
                coordinate_system=lead.coordinate_system,
                source_coordinate_system=lead.native_coordinate_system,
            )
            session.add(row)
        else:
            # The provider item is the identity; its name and position are what the newest answer
            # says. `category` is not overwritten because it was not derived from the provider.
            row.city_code = city_code
            row.name = lead.name
            row.latitude = float(lead.latitude)
            row.longitude = float(lead.longitude)
            row.metadata_json = _json(_metadata(lead))
            row.coordinate_system = lead.coordinate_system
            row.source_coordinate_system = lead.native_coordinate_system
            row.updated_at = _now()
        session.flush()
        persisted.append(
            {
                "place_id": row.id,
                "name": row.name,
                "latitude": row.latitude,
                "longitude": row.longitude,
                "coordinate_system": row.coordinate_system,
                "source_coordinate_system": row.source_coordinate_system,
                "provider_key": row.provider_key,
                "provider_item_id": row.external_id,
                "adcode": lead.adcode,
            }
        )
    return persisted
