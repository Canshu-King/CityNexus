"""Give the places this task researched a row in the shared place table.

A GoalTask's research keeps provider answers as task-scoped observations (`amap:B000A8UIN8`,
`node/123` with a public source URL). A plan version, though, can only be *selected* when the place
behind a schedule item is a row in `places` keyed by provider and provider object id -- that is what
`services.plan_authority_blocker` checks, and a missing row is reported as `SOURCE_IDENTITY`. Nothing
on this traveller path used to write the row, so every formal candidate saved from an Agent draft came
back unselectable (measured 2026-10-22: `trial/results/20261022_v3_human_chrome/
walk-34-server-readback.txt` lists `SOURCE_IDENTITY` on the four Amap-grounded items while the same
database held no canonical place rows at all).

This module hands each live, region-checked lead to the product's own materialiser --
`materialize_candidates`, the same one the recovery-discovery tool already calls -- and records on the
lead which canonical row now holds it, so the preparation door can bind a confirmed schedule to an
identity instead of a string.

Two rules it does not bend. Stored geometry is WGS-84 and the row says so itself while
`source_coordinate_system` records what the provider actually handed over (`app/db/models.py`,
Arbitration R4 / ORD-0095-1): an Amap GCJ-02 point is converted, never stored twice. And this door
promotes *identity* only: opening hours and admission price stay unknown on the row it writes, so a
traveller's screen cannot inherit a fact nobody checked.
"""
from __future__ import annotations

import math
import re
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select

from app.db.models import Journey, Place
from app.integrations.china.amap import gcj02_to_wgs84
from app.integrations.discovery.real_city import DiscoveryCandidate, materialize_candidates

_OSM_OBJECT = re.compile(r"openstreetmap\.org/(?P<kind>node|way|relation)/(?P<id>\d+)")


def _provider_object_id(lead: dict[str, Any]) -> tuple[str, str] | None:
    """The provider's own object key for this lead -- never a name match."""
    provider = str(lead.get("provider") or "").strip().lower()
    if not provider:
        return None
    object_id = str(lead.get("provider_object_id") or "").strip()
    if not object_id:
        match = _OSM_OBJECT.search(str(lead.get("source_url") or ""))
        if match:
            object_id = f"{match.group('kind')}/{match.group('id')}"
    if not object_id:
        prefix, separator, tail = str(lead.get("id") or "").partition(":")
        if separator and tail.strip():
            object_id = tail.strip()
        elif prefix.strip() and ":" not in str(lead.get("id") or ""):
            return None
    return (provider, object_id[:160]) if object_id else None


def attach_canonical_places(session, journey: Journey, task: dict, leads: list[dict[str, Any]]) -> dict[str, str]:
    """Materialise this task's live leads and let the task own the resulting place ids."""
    pending: list[tuple[dict[str, Any], DiscoveryCandidate, str | None]] = []
    for lead in leads:
        if not isinstance(lead, dict) or str(lead.get("provider_provenance") or "") != "LIVE_PROVIDER":
            continue
        if str(lead.get("region_status") or "UNKNOWN").upper() == "CONFLICT":
            continue
        identity = _provider_object_id(lead)
        name = str(lead.get("name") or "").strip()[:160]
        category = str(lead.get("category") or "").strip()[:80]
        latitude, longitude = lead.get("latitude"), lead.get("longitude")
        if identity is None or not name or not category:
            continue
        if type(latitude) not in (int, float) or type(longitude) not in (int, float):
            continue
        if not (math.isfinite(latitude) and math.isfinite(longitude)):
            continue
        if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
            continue
        provider, object_id = identity
        source_system = str(lead.get("coordinate_system") or "").strip().upper() or None
        if source_system == "GCJ02":
            stored_latitude, stored_longitude = gcj02_to_wgs84(latitude, longitude)
        else:
            stored_latitude, stored_longitude = float(latitude), float(longitude)
        url = str(lead.get("source_url") or "")
        candidate = DiscoveryCandidate(
            provider_key=provider,
            external_id=f"{provider}:{object_id}"[:180],
            name=name,
            category=category,
            latitude=stored_latitude,
            longitude=stored_longitude,
            tags=tuple(sorted({category, "goal_research"})),
            # Whatever AMap answered for this POI is carried, unchanged in meaning: an envelope with a
            # provider sentence and a parsed interval, or an empty one when the provider said nothing.
            # This used to be a literal {}, which is how a place the traveller is actually going to kept
            # coming back as 「营业时间 · 待核实」 on the departure card.
            opening_hours=dict(lead.get("opening_hours") or {}),
            metadata={"source_urls": [url] if url.startswith("http") else [],
                      "public_address": str(lead.get("public_address") or "")[:300],
                      "location_type": str(lead.get("location_type") or "")[:80],
                      # This row is stamped with the journey's own city_code no matter what the point
                      # says, so the row has to carry whether anybody ever checked the region.  An
                      # unconfirmed identity must not be able to pose as a place verified to be here
                      # (see test_a_promoted_lead_says_on_the_row_whether_its_region_was_ever_checked).
                      "region_status": str(lead.get("region_status") or "UNKNOWN").upper()},
            distance_m=None,
            cost_evidence={},
        )
        pending.append((lead, candidate, source_system))
    if not pending:
        return {}
    captured_at = datetime.now(timezone.utc).isoformat()
    materialized = materialize_candidates(
        session, journey, [item[1] for item in pending], captured_at=captured_at, mode="live",
    )
    attached: dict[str, str] = {}
    for lead, candidate, source_system in pending:
        row = next((item for item in materialized
                    if item.get("materialized_place_id") and str(item.get("external_id")) == candidate.external_id),
                   None)
        if row is None:
            continue
        place_id = str(row["materialized_place_id"])
        lead["canonical_place_id"] = place_id
        attached[str(lead.get("id") or "")] = place_id
        if source_system == "GCJ02":
            stored = session.scalar(select(Place).where(Place.id == place_id))
            if stored is not None and not stored.source_coordinate_system:
                stored.source_coordinate_system = "GCJ02"
                stored.coordinate_system = "WGS84"
    # The task owns these ids from now on, which is also what opens the fact-research tool for them:
    # research_place_sources only answers for a place id the task already holds.
    owned = task.setdefault("candidate_place_ids", [])
    for place_id in attached.values():
        if place_id not in owned:
            owned.append(place_id)
    session.flush()
    return attached
