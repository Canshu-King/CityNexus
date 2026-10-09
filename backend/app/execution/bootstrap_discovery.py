"""Zero-catalogue discovery before a Journey has a plan.

This path is deliberately separate from the active-Journey live scout.  It accepts a
signed Journey member, records an explicit provider/source consent, keeps the provider
results private until one candidate is selected, and materializes at most one Place.
"""

from __future__ import annotations

import json
import hashlib
import math
import re
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import NAMESPACE_URL, UUID, uuid4, uuid5

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import IdempotencyKey, Journey, Place, PlanVersion, ProviderCall, RealPlaceCandidate
from app.integrations.discovery.real_city import DiscoveryCandidate, OverpassPOIProvider


_OSM_EXTERNAL_ID = re.compile(r"^overpass:(node|way|relation)/([1-9][0-9]*)$")
_PRIVATE_ACCESS = {
    "private",
    "no",
    "restricted",
    "staff",
    "customers",
    "permit",
    "residents",
    "members",
}
_BOOTSTRAP_GROUNDED_OPENING = frozenset(
    {"NORMALIZED_VALID", "VERIFIED_PROVIDER", "OFFICIAL_WEB_VERIFIED"}
)
_MAX_QUERY = 120
_BOOTSTRAP_RATE_LIMIT_SECONDS = 5


class BootstrapDiscoveryError(ValueError):
    def __init__(self, code: str, message: str, *, status_code: int = 409, details: dict[str, Any] | None = None):
        super().__init__(message)
        self.code = code
        self.status_code = status_code
        self.details = details or {}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(value: datetime) -> str:
    return value.isoformat()


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)


def _finite_coordinate(latitude: float, longitude: float) -> None:
    if not math.isfinite(latitude) or not math.isfinite(longitude):
        raise BootstrapDiscoveryError("INVALID_PUBLIC_CENTER", "coordinates must be finite", status_code=422)
    if not -90 <= latitude <= 90 or not -180 <= longitude <= 180:
        raise BootstrapDiscoveryError("INVALID_PUBLIC_CENTER", "coordinates must be WGS84", status_code=422)


def _rounded_center(latitude: float, longitude: float) -> dict[str, float]:
    # A foreground location is used only as a transient provider input.  The audit
    # row gets a coarse center so it cannot become a location observation.
    return {"latitude": round(latitude, 3), "longitude": round(longitude, 3)}


def _osm_identity(candidate: DiscoveryCandidate) -> tuple[str, str] | None:
    match = _OSM_EXTERNAL_ID.fullmatch(str(candidate.external_id or ""))
    if not match:
        return None
    kind, raw_id = match.groups()
    return kind, raw_id


def _candidate_tags(candidate: DiscoveryCandidate) -> dict[str, Any]:
    tags = candidate.metadata.get("tags") if isinstance(candidate.metadata, dict) else None
    return dict(tags) if isinstance(tags, dict) else {}


def _public_candidate(candidate: DiscoveryCandidate, *, radius_m: int) -> bool:
    if _osm_identity(candidate) is None:
        return False
    tags = _candidate_tags(candidate)
    name = str(tags.get("name") or candidate.name or "").strip()
    if not name or name.casefold().startswith("osm "):
        return False
    if not math.isfinite(float(candidate.latitude)) or not math.isfinite(float(candidate.longitude)):
        return False
    if not -90 <= float(candidate.latitude) <= 90 or not -180 <= float(candidate.longitude) <= 180:
        return False
    if candidate.distance_m is not None and float(candidate.distance_m) > radius_m:
        return False
    for key in ("access", "access:conditional", "entrance", "membership"):
        value = str(tags.get(key) or "").strip().casefold()
        if value in _PRIVATE_ACCESS:
            return False
    return True


def _attempts(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    result: list[dict[str, Any]] = []
    for item in value[:4]:
        if not isinstance(item, dict):
            continue
        result.append(
            {
                "endpoint": str(item.get("endpoint") or "")[:240],
                "answered": bool(item.get("answered")),
                "http_status": item.get("http_status"),
                "elements": item.get("elements"),
                "error": str(item.get("error") or "")[:160] or None,
            }
        )
    return result


def _candidate_payload(row: RealPlaceCandidate) -> dict[str, Any]:
    evidence = json.loads(row.evidence_json or "{}")
    opening = json.loads(row.opening_hours_json or "{}")
    if not isinstance(opening, dict):
        opening = {"status": "UNKNOWN"}
    opening_status = str(opening.get("status") or "UNKNOWN").upper()
    kind = str(evidence.get("osm_type") or "node")
    osm_id = str(evidence.get("osm_id") or "")
    source_url = f"https://www.openstreetmap.org/{kind}/{osm_id}" if osm_id else None
    return {
        "candidate_id": row.id,
        "name": row.name,
        "category": row.category,
        "external_id": row.external_id,
        "osm_type": kind,
        "osm_id": osm_id,
        "source_url": source_url,
        "latitude": row.latitude,
        "longitude": row.longitude,
        "coordinate_system": "WGS84",
        "distance_m": row.distance_m,
        "opening_state": opening_status,
        "selection_state": (
            "READY_FOR_NATIVE_PLAN"
            if opening_status in _BOOTSTRAP_GROUNDED_OPENING
            else "OPENING_UNVERIFIED"
        ),
        "selection_action": (
            None
            if opening_status in _BOOTSTRAP_GROUNDED_OPENING
            else "VERIFY_OPENING_SOURCE_OR_CHOOSE_ANOTHER_CANDIDATE"
        ),
        "availability_confidence": "UNVERIFIED",
        "price_state": "UNKNOWN",
        "eta_state": "UNKNOWN",
        "tags": json.loads(row.tags_json or "[]"),
    }


def _provider_call(
    session: Session,
    *,
    journey: Journey,
    request: dict[str, Any],
    response: dict[str, Any],
    status: str,
    created_at: str,
) -> None:
    session.add(
        ProviderCall(
            id=str(uuid4()),
            provider_key="overpass",
            operation="bootstrap_city_discovery",
            request_json=_json(request),
            response_json=_json(response),
            status=status,
            latency_ms=None,
            created_at=created_at,
        )
    )


def _candidate_scope_matches(row: RealPlaceCandidate, *, member_id: str, traveler_id: str) -> bool:
    """Keep bootstrap receipts private to the signed member that created them."""

    evidence = json.loads(row.evidence_json or "{}")
    return (
        str(evidence.get("member_id") or "") == str(member_id)
        and str(evidence.get("traveler_id") or "") == str(traveler_id)
    )


def _bootstrap_rate_limited(
    session: Session,
    journey: Journey,
    now: datetime,
    *,
    member_id: str,
    traveler_id: str,
) -> bool:
    """Claim one provider attempt for this signed Journey/member/traveller scope.

    ProviderCall is an audit trail, not a lock: querying it by city was both
    cross-user noisy and racy under two simultaneous confirmations.  The
    durable idempotency row is claimed before the network call, so a retry or
    concurrent tab cannot create a second external attempt inside the window.
    """

    scope_key = f"bootstrap-discovery:{journey.id}:{member_id}:{traveler_id}"
    request_hash = hashlib.sha256(
        _json(
            {
                "journey_id": str(journey.id),
                "member_id": str(member_id),
                "traveler_id": str(traveler_id),
            }
        ).encode("utf-8")
    ).hexdigest()
    expires_at = _iso(now + timedelta(days=30))
    row = session.get(IdempotencyKey, scope_key)
    if row is None:
        try:
            with session.begin_nested():
                session.add(
                    IdempotencyKey(
                        key=scope_key,
                        operation="bootstrap-discovery",
                        request_hash=request_hash,
                        response_status=None,
                        response_json=None,
                        created_at=_iso(now),
                        expires_at=expires_at,
                        claim_token=None,
                        claim_deadline=None,
                    )
                )
                session.flush()
        except IntegrityError:
            row = session.get(IdempotencyKey, scope_key)
        else:
            # The claim must survive a provider timeout and the endpoint's
            # later rollback; this is the durable at-most-one-attempt boundary.
            session.commit()
            return False
    if row is None:
        return True
    try:
        created = datetime.fromisoformat(str(row.created_at)).astimezone(timezone.utc)
    except (TypeError, ValueError):
        created = now
    if (now - created).total_seconds() < _BOOTSTRAP_RATE_LIMIT_SECONDS:
        return True
    claimed = session.execute(
        update(IdempotencyKey)
        .where(
            IdempotencyKey.key == scope_key,
            IdempotencyKey.created_at == row.created_at,
        )
        .values(
            operation="bootstrap-discovery",
            request_hash=request_hash,
            created_at=_iso(now),
            expires_at=expires_at,
        )
    )
    if claimed.rowcount != 1:
        session.rollback()
        return True
    session.commit()
    return False


def discover_bootstrap_candidates(
    session: Session,
    journey: Journey,
    *,
    member: Any,
    traveler_id: str,
    query: str,
    radius_m: int,
    limit: int,
    source_kind: str,
    provider_consent: bool,
    latitude: float,
    longitude: float,
    accuracy_m: float | None,
) -> dict[str, Any]:
    if str(journey.status).upper() != "DRAFT":
        raise BootstrapDiscoveryError("BOOTSTRAP_REQUIRES_DRAFT", "bootstrap discovery requires a DRAFT Journey")
    if journey.active_plan_version_id is not None or session.scalar(
        select(PlanVersion.id).where(PlanVersion.journey_id == journey.id).limit(1)
    ):
        raise BootstrapDiscoveryError("BOOTSTRAP_PLAN_ALREADY_EXISTS", "bootstrap discovery requires no PlanVersion")
    if source_kind not in {"FOREGROUND_GPS", "MANUAL_PUBLIC_CENTER"}:
        raise BootstrapDiscoveryError("INVALID_SOURCE_KIND", "source_kind is invalid", status_code=422)
    if not provider_consent:
        raise BootstrapDiscoveryError(
            "PROVIDER_CONSENT_REQUIRED",
            "explicit provider disclosure consent is required before discovery",
            status_code=422,
        )
    _finite_coordinate(float(latitude), float(longitude))
    query = str(query or "").strip()[:_MAX_QUERY]
    if not query:
        raise BootstrapDiscoveryError("INVALID_QUERY", "query is required", status_code=422)
    captured_at = _now()
    member_id = str(member.id)
    traveler_id = str(traveler_id)
    if _bootstrap_rate_limited(
        session,
        journey,
        captured_at,
        member_id=member_id,
        traveler_id=traveler_id,
    ):
        raise BootstrapDiscoveryError(
            "BOOTSTRAP_RATE_LIMITED",
            "please wait before starting another public discovery request",
            status_code=429,
            details={
                "retry_after_seconds": _BOOTSTRAP_RATE_LIMIT_SECONDS,
                "scope": "journey_member_traveler",
                "journey_id": str(journey.id),
                "member_id": member_id,
                "traveler_id": traveler_id,
                "provider_consent": True,
            },
        )
    expires_at = captured_at + timedelta(seconds=settings.real_city_cache_ttl_seconds)
    request = {
        "journey_id": str(journey.id),
        "city_code": journey.city_code,
        "query": query,
        "radius_m": radius_m,
        "limit": limit,
        "mode": "live",
        "source_kind": source_kind,
        "center": _rounded_center(float(latitude), float(longitude)),
        "accuracy_m": round(float(accuracy_m), 1) if accuracy_m is not None else None,
        "member_id": member_id,
        "traveler_id": traveler_id,
        "provider_consent": True,
    }
    if not settings.real_city_enabled or str(settings.real_city_mode).lower() != "live":
        _provider_call(
            session,
            journey=journey,
            request=request,
            response={"status": "PROVIDER_DISABLED", "attempts": [], "count": 0},
            status="DISABLED",
            created_at=_iso(captured_at),
        )
        return {
            "journey_id": journey.id,
            "status": "PROVIDER_DISABLED",
            "receipt_id": None,
            "expires_at": None,
            "source_kind": source_kind,
            "provider": "overpass",
            "provider_provenance": "LIVE_OPENSTREETMAP_OVERPASS",
            "attempts": [],
            "candidates": [],
        }

    provider = OverpassPOIProvider()
    attempts: list[dict[str, Any]] = []
    try:
        candidates, attempts = provider.search_with_evidence(
            query,
            latitude=float(latitude),
            longitude=float(longitude),
            radius_m=radius_m,
            limit=limit,
            max_attempts=1,
        )
    except Exception as exc:  # provider failures become a truthful unavailable state
        attempts = _attempts(getattr(exc, "provider_attempts", []))
        _provider_call(
            session,
            journey=journey,
            request=request,
            response={"status": "PROVIDER_UNAVAILABLE", "attempts": attempts, "count": 0},
            status="UNAVAILABLE",
            created_at=_iso(captured_at),
        )
        return {
            "journey_id": journey.id,
            "status": "PROVIDER_UNAVAILABLE",
            "receipt_id": None,
            "expires_at": None,
            "source_kind": source_kind,
            "provider": "overpass",
            "provider_provenance": "LIVE_OPENSTREETMAP_OVERPASS",
            "attempts": attempts,
            "candidates": [],
            "failure_code": "PROVIDER_UNAVAILABLE",
        }
    finally:
        provider.close()

    usable: list[DiscoveryCandidate] = []
    seen: set[str] = set()
    for candidate in candidates:
        if not _public_candidate(candidate, radius_m=radius_m):
            continue
        if candidate.external_id in seen:
            continue
        seen.add(candidate.external_id)
        usable.append(candidate)
        if len(usable) >= limit:
            break

    receipt_id = str(uuid4())
    persisted_distance = source_kind == "MANUAL_PUBLIC_CENTER"
    # A new request supersedes only still-private rows from an earlier cancelled/abandoned
    # screen.  Selected rows remain immutable and therefore cannot disappear from the catalogue.
    private_rows = session.scalars(
        select(RealPlaceCandidate).where(
            RealPlaceCandidate.journey_id == journey.id,
            RealPlaceCandidate.materialized_place_id.is_(None),
            RealPlaceCandidate.status == "BOOTSTRAP_PRIVATE",
        )
    ).all()
    for private_row in private_rows:
        if _candidate_scope_matches(private_row, member_id=member_id, traveler_id=traveler_id):
            session.delete(private_row)
    for candidate in usable:
        osm = _osm_identity(candidate)
        if osm is None:
            continue
        osm_type, osm_id = osm
        existing_candidate = session.scalar(
            select(RealPlaceCandidate).where(
                RealPlaceCandidate.journey_id == journey.id,
                RealPlaceCandidate.provider_key == "overpass",
                RealPlaceCandidate.external_id == candidate.external_id,
            )
        )
        # The same OSM identity may be returned to two members.  Do not overwrite
        # the first member's private receipt or let a duplicate violate the
        # Journey/provider/external identity constraint.
        if existing_candidate is not None:
            continue
        tags = _candidate_tags(candidate)
        cost = dict(candidate.cost_evidence or {"status": "UNKNOWN"})
        cost.setdefault("status", "UNKNOWN")
        row_id = str(uuid4())
        session.add(
            RealPlaceCandidate(
                id=row_id,
                journey_id=journey.id,
                provider_key="overpass",
                external_id=candidate.external_id,
                city_code=journey.city_code,
                name=str(tags.get("name") or candidate.name).strip(),
                category=str(candidate.category or "service"),
                latitude=float(candidate.latitude),
                longitude=float(candidate.longitude),
                tags_json=_json(list(candidate.tags)),
                opening_hours_json=_json(
                    dict(candidate.opening_hours or {"status": "UNKNOWN"})
                ),
                metadata_json=_json(
                    {
                        "source": "LIVE_OPENSTREETMAP_OVERPASS",
                        "cost_evidence": cost,
                        "public_access_gate": "NO_EXPLICIT_PRIVATE_ACCESS",
                        "osm_tags": tags,
                    }
                ),
                captured_at=_iso(captured_at),
                expires_at=_iso(expires_at),
                # A foreground fix is a transient provider input.  Do not persist
                # a distance that could be used to infer that private fix later.
                distance_m=(
                    float(candidate.distance_m)
                    if persisted_distance and candidate.distance_m is not None
                    else None
                ),
                evidence_json=_json(
                    {
                        "bootstrap": True,
                        "receipt_id": receipt_id,
                        "member_id": member_id,
                        "traveler_id": traveler_id,
                        "source_kind": source_kind,
                        "provider_attempts": attempts,
                        "candidate_id": row_id,
                        "osm_type": osm_type,
                        "osm_id": osm_id,
                        "source_url": f"https://www.openstreetmap.org/{osm_type}/{osm_id}",
                    }
                ),
                materialized_place_id=None,
                status="BOOTSTRAP_PRIVATE",
            )
        )
    _provider_call(
        session,
        journey=journey,
        request=request,
        response={
            "status": "LIVE_RESULTS" if usable else "LIVE_ZERO_RESULTS",
            "attempts": attempts,
            "count": len(usable),
        },
        status="SUCCESS",
        created_at=_iso(captured_at),
    )
    return {
        "journey_id": journey.id,
        "status": "LIVE_RESULTS" if usable else "LIVE_ZERO_RESULTS",
        "receipt_id": receipt_id,
        "expires_at": _iso(expires_at),
        "source_kind": source_kind,
        "provider": "overpass",
        "provider_provenance": "LIVE_OPENSTREETMAP_OVERPASS",
        "attempts": attempts,
        "candidates": [
            _candidate_payload(row)
            for row in session.scalars(
                select(RealPlaceCandidate).where(
                    RealPlaceCandidate.journey_id == journey.id,
                    RealPlaceCandidate.status == "BOOTSTRAP_PRIVATE",
                ).order_by(RealPlaceCandidate.captured_at, RealPlaceCandidate.id)
            ).all()
            if _candidate_scope_matches(row, member_id=member_id, traveler_id=traveler_id)
        ],
    }


def select_bootstrap_candidate(
    session: Session,
    journey: Journey,
    *,
    member: Any,
    traveler_id: str,
    receipt_id: UUID,
    candidate_id: UUID,
) -> dict[str, Any]:
    if str(journey.status).upper() != "DRAFT":
        raise BootstrapDiscoveryError("BOOTSTRAP_REQUIRES_DRAFT", "bootstrap selection requires a DRAFT Journey")
    if journey.active_plan_version_id is not None or session.scalar(
        select(PlanVersion.id).where(PlanVersion.journey_id == journey.id).limit(1)
    ):
        raise BootstrapDiscoveryError("BOOTSTRAP_PLAN_ALREADY_EXISTS", "bootstrap selection requires no PlanVersion")
    row = session.scalar(
        select(RealPlaceCandidate).where(
            RealPlaceCandidate.id == str(candidate_id),
            RealPlaceCandidate.journey_id == journey.id,
            RealPlaceCandidate.provider_key == "overpass",
        )
    )
    if row is None:
        raise BootstrapDiscoveryError("BOOTSTRAP_CANDIDATE_NOT_FOUND", "bootstrap candidate was not found", status_code=404)
    evidence = json.loads(row.evidence_json or "{}")
    if not evidence.get("bootstrap") or str(evidence.get("receipt_id")) != str(receipt_id):
        raise BootstrapDiscoveryError("BOOTSTRAP_RECEIPT_MISMATCH", "candidate does not belong to this discovery receipt", status_code=403)
    if str(evidence.get("member_id")) != str(member.id) or str(evidence.get("traveler_id")) != str(traveler_id):
        raise BootstrapDiscoveryError("BOOTSTRAP_MEMBER_MISMATCH", "candidate belongs to another signed member", status_code=403)
    expires_at = row.expires_at
    if expires_at:
        try:
            if datetime.fromisoformat(expires_at).astimezone(timezone.utc) <= _now():
                raise BootstrapDiscoveryError("BOOTSTRAP_CANDIDATE_EXPIRED", "bootstrap candidate expired", status_code=410)
        except ValueError:
            raise BootstrapDiscoveryError("BOOTSTRAP_CANDIDATE_EXPIRED", "bootstrap candidate expiry is invalid", status_code=410)
    opening = json.loads(row.opening_hours_json or "{}")
    opening_state = str(opening.get("status") or "UNKNOWN").upper() if isinstance(opening, dict) else "UNKNOWN"
    source_url = str(evidence.get("source_url") or "") or None
    if opening_state not in _BOOTSTRAP_GROUNDED_OPENING:
        code = "BOOTSTRAP_PLACE_CLOSED" if opening_state == "CLOSED" else "BOOTSTRAP_OPENING_UNVERIFIED"
        message = (
            "OpenStreetMap reports this place as closed; choose another candidate"
            if code == "BOOTSTRAP_PLACE_CLOSED"
            else "OpenStreetMap did not provide grounded opening hours; verify the source or choose another candidate"
        )
        raise BootstrapDiscoveryError(
            code,
            message,
            status_code=422,
            details={
                "opening_state": opening_state,
                "source_url": source_url,
                "next_actions": ["VERIFY_OPENING_SOURCE", "CHOOSE_ANOTHER_CANDIDATE"],
            },
        )
    if row.materialized_place_id and row.status == "BOOTSTRAP_SELECTED":
        return {
            "journey_id": journey.id,
            "selected_place_id": row.materialized_place_id,
            "plan_version_id": None,
            "journey_status": journey.status,
            "provider_provenance": "LIVE_OPENSTREETMAP_OVERPASS",
        }
    other_selected = session.scalar(
        select(RealPlaceCandidate.id).where(
            RealPlaceCandidate.journey_id == journey.id,
            RealPlaceCandidate.status == "BOOTSTRAP_SELECTED",
            RealPlaceCandidate.id != row.id,
        ).limit(1)
    )
    if other_selected:
        raise BootstrapDiscoveryError("BOOTSTRAP_ALREADY_SELECTED", "this Journey already has its first selected Place")
    if row.status != "BOOTSTRAP_PRIVATE" or row.materialized_place_id is not None:
        raise BootstrapDiscoveryError("BOOTSTRAP_CANDIDATE_UNAVAILABLE", "bootstrap candidate is no longer selectable")
    claimed = session.execute(
        update(RealPlaceCandidate)
        .where(
            RealPlaceCandidate.id == row.id,
            RealPlaceCandidate.journey_id == journey.id,
            RealPlaceCandidate.materialized_place_id.is_(None),
            RealPlaceCandidate.status == "BOOTSTRAP_PRIVATE",
        )
        .values(status="BOOTSTRAP_SELECTING")
    )
    if claimed.rowcount != 1:
        raise BootstrapDiscoveryError("BOOTSTRAP_CANDIDATE_RACE", "bootstrap candidate changed while selecting")
    session.flush()
    osm = _osm_identity(row)
    if osm is None:
        raise BootstrapDiscoveryError("BOOTSTRAP_IDENTITY_INVALID", "candidate OSM identity is invalid", status_code=422)
    existing = session.scalar(
        select(Place).where(Place.provider_key == "overpass", Place.external_id == row.external_id)
    )
    if existing is not None and existing.city_code != journey.city_code:
        raise BootstrapDiscoveryError("BOOTSTRAP_IDENTITY_CONFLICT", "OSM identity belongs to another city")
    place = existing
    if place is None:
        metadata = json.loads(row.metadata_json or "{}")
        cost = metadata.get("cost_evidence") or {"status": "UNKNOWN", "amount_minor": None}
        opening_hours = json.loads(row.opening_hours_json or "{}")
        if not isinstance(opening_hours, dict):
            opening_hours = {"status": "UNKNOWN"}
        opening_hours.setdefault("status", "UNKNOWN")
        place = Place(
            id=str(uuid5(NAMESPACE_URL, f"citynexus:bootstrap:{row.provider_key}:{row.external_id}")),
            provider_key="overpass",
            external_id=row.external_id,
            city_code=journey.city_code,
            name=row.name,
            category=row.category,
            latitude=row.latitude,
            longitude=row.longitude,
            opening_hours_json=_json(opening_hours),
            tags_json=row.tags_json,
            metadata_json=_json(
                {
                    "discovery_mode": "live",
                    "provider_provenance": "LIVE_OPENSTREETMAP_OVERPASS",
                    "cost_evidence": cost,
                    "price_known": str(cost.get("status") or "UNKNOWN").upper() in {"KNOWN", "VERIFIED_PROVIDER"},
                    "source_url": json.loads(row.evidence_json or "{}").get("source_url"),
                }
            ),
            updated_at=_iso(_now()),
            coordinate_system="WGS84",
            source_coordinate_system="WGS84",
        )
        session.add(place)
        try:
            session.flush()
        except IntegrityError:
            session.rollback()
            place = session.scalar(
                select(Place).where(Place.provider_key == "overpass", Place.external_id == row.external_id)
            )
            if place is None:
                raise BootstrapDiscoveryError("BOOTSTRAP_MATERIALIZATION_FAILED", "Place materialization failed")
    evidence["selected"] = True
    evidence["selected_place_id"] = place.id
    row.materialized_place_id = place.id
    row.status = "BOOTSTRAP_SELECTED"
    row.evidence_json = _json(evidence)
    session.flush()
    return {
        "journey_id": journey.id,
        "selected_place_id": place.id,
        "plan_version_id": None,
        "journey_status": journey.status,
        "provider_provenance": "LIVE_OPENSTREETMAP_OVERPASS",
    }
