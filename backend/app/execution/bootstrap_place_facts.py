"""Read one chosen OSM element's tags for an existing signed discovery receipt."""
from __future__ import annotations

import json
import time
from typing import Any
from uuid import UUID, uuid4

import httpx
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import Journey, PlanVersion, ProviderCall, RealPlaceCandidate
from app.execution import bootstrap_discovery as discovery
from app.integrations.discovery.provider_identity import PROVIDER_USER_AGENT
from app.integrations.discovery.real_city import cost_evidence_from_tags, normalize_opening_hours
from app.integrations.provider_config import trust_environment_for_public_providers

OSM_API = "https://api.openstreetmap.org/api/0.6"
_MAX_BYTES = 262_144
_FACT_TAGS = frozenset({
    "name", "opening_hours", "fee", "charge", "charge:adult", "price", "currency",
    "currency:code", "access", "access:conditional", "entrance", "membership",
    "visibility", "public", "indoor", "website", "contact:website", "phone", "contact:phone",
})


def current_bootstrap_discovery(session: Session, journey: Journey, *, member: Any, traveler_id: str) -> dict[str, Any] | None:
    """Restore only this member's current, unexpired private search, without I/O."""
    if journey.status != "DRAFT" or journey.active_plan_version_id or session.scalar(
        select(PlanVersion.id).where(PlanVersion.journey_id == journey.id).limit(1)
    ):
        return None
    observed = []
    for row in session.scalars(select(RealPlaceCandidate).where(
        RealPlaceCandidate.journey_id == journey.id, RealPlaceCandidate.status == "BOOTSTRAP_PRIVATE",
        RealPlaceCandidate.materialized_place_id.is_(None),
        RealPlaceCandidate.provider_key.in_(("photon", "overpass")),
    )):
        for scope in discovery._bootstrap_scope_entries(json.loads(row.evidence_json or "{}")):
            if (scope["member_id"] == str(member.id) and scope["traveler_id"] == traveler_id
                    and scope.get("source_kind") == "MANUAL_PUBLIC_CENTER"
                    and not discovery._scope_expired(scope)
                    and not (not scope.get("expires_at") and row.expires_at and discovery._scope_expired({"expires_at": row.expires_at}))):
                observed.append((str(scope.get("captured_at") or row.captured_at), row, scope))
    if not observed:
        return None
    _captured, latest, scope = max(observed, key=lambda item: item[0])
    region_label = discovery._public_region_label(session, journey)
    candidates = [discovery._candidate_payload(row, member_id=str(member.id), traveler_id=traveler_id,
                                                public_region_label=region_label)
                  for _time, row, item in observed if item["receipt_id"] == scope["receipt_id"]]
    return {"journey_id": journey.id, "status": "LIVE_RESULTS", "source_kind": "MANUAL_PUBLIC_CENTER",
            "result_state": "FOUND_2+" if len(candidates) > 1 else "PARTIAL_1",
            "receipt_id": scope["receipt_id"], "expires_at": scope.get("expires_at") or latest.expires_at,
            "provider": latest.provider_key, "provider_provenance": scope.get("provider_provenance") or "UNVERIFIED",
            "attempts": [], "candidates": candidates}


def read_osm_tags(kind: str, osm_id: str) -> dict[str, str]:
    # Identity comes from the server's candidate, never from a client URL.
    if kind not in {"node", "way", "relation"} or not osm_id.isascii() or not osm_id.isdigit():
        raise ValueError("invalid OSM identity")
    deadline = time.monotonic() + 7
    with httpx.Client(timeout=5, follow_redirects=False, trust_env=trust_environment_for_public_providers(), headers={
        "User-Agent": PROVIDER_USER_AGENT, "Accept": "application/json",
    }) as client:
        with client.stream("GET", f"{OSM_API}/{kind}/{osm_id}.json") as response:
            response.raise_for_status()
            body = bytearray()
            for chunk in response.iter_bytes():
                body.extend(chunk)
                if len(body) > _MAX_BYTES or time.monotonic() > deadline:
                    raise ValueError("OSM response exceeded limit")
    data = json.loads(body)
    elements = data.get("elements") if isinstance(data, dict) else None
    if not isinstance(elements, list) or len(elements) != 1:
        raise ValueError("expected one OSM element")
    element = elements[0]
    if (not isinstance(element, dict) or element.get("type") != kind
            or type(element.get("id")) is not int or str(element["id"]) != osm_id
            or element.get("visible") is False or not isinstance(element.get("tags"), dict)):
        raise ValueError("OSM element identity mismatch")
    return {key: value for key, value in element["tags"].items()
            if key in _FACT_TAGS and isinstance(value, str) and len(value) <= 255}


def refresh_bootstrap_place_facts(
    session: Session, journey: Journey, *, member: Any, traveler_id: str,
    receipt_id: UUID, candidate_id: UUID, provider_consent: bool,
) -> dict[str, Any]:
    if not provider_consent:
        raise discovery.BootstrapDiscoveryError("PROVIDER_CONSENT_REQUIRED", "Confirm the OSM detail lookup", status_code=422)
    if not settings.real_city_enabled or settings.real_city_mode != "live":
        raise discovery.BootstrapDiscoveryError("PROVIDER_DISABLED", "Public place details are not enabled", status_code=409)
    if journey.status != "DRAFT" or journey.active_plan_version_id or session.scalar(
        select(PlanVersion.id).where(PlanVersion.journey_id == journey.id).limit(1)
    ):
        raise discovery.BootstrapDiscoveryError("BOOTSTRAP_REQUIRES_DRAFT", "Choose details before creating a plan")
    row = session.scalar(select(RealPlaceCandidate).where(
        RealPlaceCandidate.id == str(candidate_id), RealPlaceCandidate.journey_id == journey.id,
        RealPlaceCandidate.provider_key.in_(("photon", "overpass")),
    ))
    if row is None:
        raise discovery.BootstrapDiscoveryError("BOOTSTRAP_CANDIDATE_NOT_FOUND", "Place not found", status_code=404)
    scope = discovery._bootstrap_scope_for_request(row, member=member, traveler_id=traveler_id, receipt_id=receipt_id)
    if row.status != "BOOTSTRAP_PRIVATE" or row.materialized_place_id:
        raise discovery.BootstrapDiscoveryError("BOOTSTRAP_CANDIDATE_UNAVAILABLE", "Place already selected")
    if scope.get("provider_provenance") != "LIVE_PROVIDER":
        raise discovery.BootstrapDiscoveryError("LIVE_SOURCE_REQUIRED", "This lookup requires a public source", status_code=422)
    osm = discovery._osm_identity(row)
    if osm is None:
        raise discovery.BootstrapDiscoveryError("BOOTSTRAP_IDENTITY_INVALID", "Missing public OSM identity", status_code=422)
    if scope.get("osm_facts"):
        return {"journey_id": journey.id, "candidate": discovery._candidate_payload(
            row, member_id=str(member.id), traveler_id=traveler_id,
            public_region_label=discovery._public_region_label(session, journey)), "cached": True}
    now = discovery._now()
    if discovery._bootstrap_rate_limited(session, journey, now, member_id=str(member.id), traveler_id=traveler_id,
                               operation=f"bootstrap-facts:{receipt_id}:{candidate_id}"):
        raise discovery.BootstrapDiscoveryError("RATE_LIMITED", "The place lookup is already in progress", status_code=429)
    started = time.monotonic()
    status = "SUCCESS"
    failure_code = None
    try:
        tags = read_osm_tags(*osm)
    except (httpx.HTTPError, ValueError, TypeError) as error:
        status = "UNAVAILABLE"
        tags = None
        if isinstance(error, httpx.HTTPStatusError):
            failure_code = f"OSM_HTTP_{error.response.status_code}"
        elif isinstance(error, httpx.TimeoutException):
            failure_code = "OSM_TIMEOUT"
        elif isinstance(error, httpx.TransportError):
            failure_code = "OSM_UNREACHABLE"
        else:
            failure_code = "OSM_INVALID_RESPONSE"
    # Re-read after network I/O: a newer search or selection must not be overwritten.
    session.refresh(row)
    scope = discovery._bootstrap_scope_for_request(row, member=member, traveler_id=traveler_id, receipt_id=receipt_id)
    if row.status != "BOOTSTRAP_PRIVATE" or row.materialized_place_id:
        raise discovery.BootstrapDiscoveryError("BOOTSTRAP_CANDIDATE_UNAVAILABLE", "Place changed during lookup")
    scope = dict(scope)
    checked_at = discovery._iso(discovery._now())
    scope["osm_facts"] = {"status": status, "checked_at": checked_at, "source": "OSM_ELEMENT_API", "failure_code": failure_code}
    if tags is not None:
        scope.update({
            "osm_tags": tags,
            "opening_hours": normalize_opening_hours(tags.get("opening_hours")),
            "cost_evidence": cost_evidence_from_tags(tags, source="osm_element_api"),
            "public_access_state": discovery._public_access_state(tags),
            "captured_at": checked_at,
        })
        if tags.get("name"):
            scope["observed_name"] = tags["name"]
    old_json = row.evidence_json
    evidence = json.loads(old_json)
    evidence["bootstrap_scopes"] = [
        scope if item["member_id"] == str(member.id) and item["traveler_id"] == traveler_id else item
        for item in discovery._bootstrap_scope_entries(evidence)
    ]
    changed = session.execute(update(RealPlaceCandidate).where(
        RealPlaceCandidate.id == row.id, RealPlaceCandidate.status == "BOOTSTRAP_PRIVATE",
        RealPlaceCandidate.evidence_json == old_json,
    ).values(evidence_json=discovery._json(evidence)).execution_options(synchronize_session=False))
    if changed.rowcount != 1:
        raise discovery.BootstrapDiscoveryError("BOOTSTRAP_RECEIPT_CHANGED", "Place changed during lookup")
    session.add(ProviderCall(
        id=str(uuid4()), provider_key="osm_element_api", operation="bootstrap_place_facts",
        request_json=discovery._json({"osm_type": osm[0], "osm_id": osm[1], "provider_consent": True}),
        response_json=discovery._json({"status": status, "failure_code": failure_code,
                                      "source_url": f"https://www.openstreetmap.org/{osm[0]}/{osm[1]}"}),
        status="SUCCESS" if status == "SUCCESS" else "FAILURE",
        latency_ms=int((time.monotonic() - started) * 1000), created_at=checked_at,
    ))
    session.flush()
    session.expire(row, ["evidence_json"])
    return {"journey_id": journey.id, "candidate": discovery._candidate_payload(
        row, member_id=str(member.id), traveler_id=traveler_id,
        public_region_label=discovery._public_region_label(session, journey)), "cached": False}
