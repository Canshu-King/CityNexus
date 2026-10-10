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

from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import (
    IdempotencyKey,
    Journey,
    MemberDraftShortlistItem,
    Place,
    PlanVersion,
    ProviderCall,
    RealPlaceCandidate,
)
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
_MAX_SHORTLIST_ITEMS = 3
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


def _candidate_payload(
    row: RealPlaceCandidate,
    *,
    member_id: str | None = None,
    traveler_id: str | None = None,
) -> dict[str, Any]:
    evidence = json.loads(row.evidence_json or "{}")
    opening = json.loads(row.opening_hours_json or "{}")
    if not isinstance(opening, dict):
        opening = {"status": "UNKNOWN"}
    metadata = json.loads(row.metadata_json or "{}")
    if not isinstance(metadata, dict):
        metadata = {}
    osm_tags = metadata.get("osm_tags") or metadata.get("tags") or {}
    if not isinstance(osm_tags, dict):
        osm_tags = {}
    source_tags = {
        key: str(osm_tags[key])
        for key in (
            "opening_hours",
            "website",
            "contact:website",
            "phone",
            "contact:phone",
            "email",
        )
        if osm_tags.get(key) not in (None, "")
    }
    opening_status = str(opening.get("status") or "UNKNOWN").upper()
    kind = str(evidence.get("osm_type") or "node")
    osm_id = str(evidence.get("osm_id") or "")
    source_url = f"https://www.openstreetmap.org/{kind}/{osm_id}" if osm_id else None
    scope_distance = None
    if member_id is not None and traveler_id is not None:
        for scope in _bootstrap_scope_entries(evidence):
            if scope["member_id"] == str(member_id) and scope["traveler_id"] == str(traveler_id):
                scope_distance = scope.get("distance_m")
                break
    if scope_distance is None and len(_bootstrap_scope_entries(evidence)) <= 1:
        scope_distance = row.distance_m
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
        "distance_m": scope_distance,
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
        "opening_hours": opening,
        "opening_observed_at": row.captured_at,
        "opening_source": "OpenStreetMap/Overpass",
        "opening_claim": (
            "OSM_TAG_CLAIM"
            if source_tags.get("opening_hours")
            else "NO_OPENING_TAG"
        ),
        "opening_verification_state": (
            "PROVIDER_GROUNDED"
            if opening_status in _BOOTSTRAP_GROUNDED_OPENING
            else "EXTERNAL_NOT_ATTESTED"
        ),
        "opening_verification_action": "OPEN_SOURCE_PAGE",
        "source_tags": source_tags,
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


def _shortlist_payload(row: MemberDraftShortlistItem) -> dict[str, Any]:
    opening = json.loads(row.opening_hours_json or "{}")
    if not isinstance(opening, dict):
        opening = {"status": "UNKNOWN"}
    cost = json.loads(row.cost_evidence_json or "{}")
    if not isinstance(cost, dict):
        cost = {"status": "UNKNOWN"}
    source_tags = json.loads(row.source_tags_json or "{}")
    if not isinstance(source_tags, dict):
        source_tags = {}
    return {
        "shortlist_id": row.id,
        "journey_id": row.journey_id,
        "provider_key": row.provider_key,
        "external_id": row.external_id,
        "name": row.name,
        "category": row.category,
        "latitude": row.latitude,
        "longitude": row.longitude,
        "coordinate_system": row.coordinate_system,
        "source_url": row.source_url,
        "source_provenance": row.source_provenance,
        "captured_at": row.captured_at,
        "opening_hours": opening,
        "opening_state": str(opening.get("status") or "UNKNOWN").upper(),
        "price_state": str(cost.get("status") or "UNKNOWN").upper(),
        "eta_state": "UNKNOWN",
        "source_tags": source_tags,
        "distance_m": row.distance_m,
        "distance_basis": row.distance_basis,
        "status": row.status,
        "created_at": row.created_at,
        "updated_at": row.updated_at,
    }


def _public_tags_for_candidate(row: RealPlaceCandidate) -> dict[str, str]:
    metadata = json.loads(row.metadata_json or "{}")
    if not isinstance(metadata, dict):
        metadata = {}
    tags = metadata.get("osm_tags") or metadata.get("tags") or {}
    if not isinstance(tags, dict):
        return {}
    return {
        key: str(tags[key])[:512]
        for key in ("opening_hours",)
        if tags.get(key) not in (None, "")
    }


def _public_map_url(latitude: float, longitude: float) -> str:
    return (
        "https://www.openstreetmap.org/?mlat="
        f"{float(latitude):.7f}&mlon={float(longitude):.7f}"
        f"#map=18/{float(latitude):.7f}/{float(longitude):.7f}"
    )


def _bootstrap_scope_entries(evidence: dict[str, Any]) -> list[dict[str, Any]]:
    """Read member-private scopes while retaining compatibility with R87 receipts."""

    raw_scopes = evidence.get("bootstrap_scopes")
    scopes: list[dict[str, Any]] = []
    if isinstance(raw_scopes, list):
        for raw in raw_scopes:
            if not isinstance(raw, dict):
                continue
            member_id = str(raw.get("member_id") or "")
            traveler_id = str(raw.get("traveler_id") or "")
            receipt_id = str(raw.get("receipt_id") or "")
            if member_id and traveler_id and receipt_id:
                scopes.append(
                    {
                        "member_id": member_id,
                        "traveler_id": traveler_id,
                        "receipt_id": receipt_id,
                        "source_kind": str(raw.get("source_kind") or ""),
                        "distance_m": raw.get("distance_m"),
                        "expires_at": str(raw.get("expires_at") or "") or None,
                    }
                )
    if scopes:
        return scopes
    member_id = str(evidence.get("member_id") or "")
    traveler_id = str(evidence.get("traveler_id") or "")
    receipt_id = str(evidence.get("receipt_id") or "")
    if member_id and traveler_id and receipt_id:
        return [
            {
                "member_id": member_id,
                "traveler_id": traveler_id,
                "receipt_id": receipt_id,
                "source_kind": str(evidence.get("source_kind") or ""),
                "distance_m": None,
                "expires_at": None,
            }
        ]
    return []


def _candidate_scope_matches(row: RealPlaceCandidate, *, member_id: str, traveler_id: str) -> bool:
    """Keep bootstrap receipts private while allowing the same public OSM identity to be reused."""

    evidence = json.loads(row.evidence_json or "{}")
    return any(
        scope["member_id"] == str(member_id) and scope["traveler_id"] == str(traveler_id)
        for scope in _bootstrap_scope_entries(evidence)
    )


def _matching_candidate_scope(
    evidence: dict[str, Any],
    *,
    member_id: str,
    traveler_id: str,
    receipt_id: str,
) -> dict[str, Any] | None:
    for scope in _bootstrap_scope_entries(evidence):
        if (
            scope["member_id"] == str(member_id)
            and scope["traveler_id"] == str(traveler_id)
            and scope["receipt_id"] == str(receipt_id)
        ):
            return scope
    return None


def _scope_expired(scope: dict[str, Any] | None, *, now: datetime | None = None) -> bool:
    value = scope.get("expires_at") if scope else None
    if not value:
        return False
    try:
        expires_at = datetime.fromisoformat(str(value)).astimezone(timezone.utc)
    except ValueError:
        return True
    return expires_at <= (now or _now())


def _drop_candidate_scope(row: RealPlaceCandidate, *, member_id: str, traveler_id: str) -> bool:
    """Remove one private receipt without deleting another member's identical OSM result."""

    evidence = json.loads(row.evidence_json or "{}")
    scopes = [
        scope
        for scope in _bootstrap_scope_entries(evidence)
        if not (
            scope["member_id"] == str(member_id)
            and scope["traveler_id"] == str(traveler_id)
        )
    ]
    if not scopes:
        return False
    evidence["bootstrap_scopes"] = scopes
    # Keep the legacy top-level fields pointed at a remaining scope for any old
    # operator tooling that reads the stored evidence directly.
    first = scopes[0]
    evidence.update(
        {
            "member_id": first["member_id"],
            "traveler_id": first["traveler_id"],
            "receipt_id": first["receipt_id"],
            "source_kind": first.get("source_kind") or evidence.get("source_kind"),
        }
    )
    row.evidence_json = _json(evidence)
    return True


def _replace_candidate_scope(
    session: Session,
    *,
    journey_id: str,
    external_id: str,
    member_id: str,
    traveler_id: str,
    scope: dict[str, Any],
) -> bool:
    """CAS-merge one private receipt without losing another member's scope."""

    owner_key = (str(member_id), str(traveler_id))
    for _attempt in range(4):
        row = session.scalar(
            select(RealPlaceCandidate)
            .where(
                RealPlaceCandidate.journey_id == str(journey_id),
                RealPlaceCandidate.provider_key == "overpass",
                RealPlaceCandidate.external_id == str(external_id),
                RealPlaceCandidate.status == "BOOTSTRAP_PRIVATE",
            )
            .execution_options(populate_existing=True)
        )
        if row is None:
            return False
        old_json = row.evidence_json or "{}"
        evidence = json.loads(old_json)
        if not evidence.get("bootstrap"):
            return False
        scopes = [
            existing
            for existing in _bootstrap_scope_entries(evidence)
            if (existing["member_id"], existing["traveler_id"]) != owner_key
        ]
        # A member's new discovery receipt replaces that member's old authority;
        # other members' scopes remain intact.
        scopes.append(dict(scope))
        evidence["bootstrap_scopes"] = scopes
        first = scopes[0]
        evidence.update(
            {
                "member_id": first["member_id"],
                "traveler_id": first["traveler_id"],
                "receipt_id": first["receipt_id"],
                "source_kind": first.get("source_kind") or evidence.get("source_kind"),
            }
        )
        result = session.execute(
            update(RealPlaceCandidate)
            .where(
                RealPlaceCandidate.id == row.id,
                RealPlaceCandidate.status == "BOOTSTRAP_PRIVATE",
                RealPlaceCandidate.evidence_json == old_json,
            )
            .values(evidence_json=_json(evidence))
            .execution_options(synchronize_session=False)
        )
        if result.rowcount == 1:
            session.expire(row, ["evidence_json"])
            return True
        # Another request won the compare-and-swap. Drop any identity-map snapshot
        # and merge against its committed scopes on the next attempt.
        session.expire_all()
    raise BootstrapDiscoveryError(
        "BOOTSTRAP_SCOPE_UPDATE_CONFLICT",
        "member discovery scopes changed concurrently; retry the search",
        status_code=409,
        details={"next_actions": ["SEARCH_AGAIN"]},
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
            if not _drop_candidate_scope(private_row, member_id=member_id, traveler_id=traveler_id):
                session.delete(private_row)
    session.flush()
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
        # The same OSM identity may be returned to two members.  Keep one
        # deterministic row, but append a separate private scope instead of
        # dropping the second member's named result or overwriting the first
        # member's receipt.
        if existing_candidate is not None:
            if existing_candidate.status == "BOOTSTRAP_PRIVATE":
                _replace_candidate_scope(
                    session,
                    journey_id=journey.id,
                    external_id=candidate.external_id,
                    member_id=member_id,
                    traveler_id=traveler_id,
                    scope={
                        "member_id": member_id,
                        "traveler_id": traveler_id,
                        "receipt_id": receipt_id,
                        "source_kind": source_kind,
                        "expires_at": _iso(expires_at),
                        "distance_m": (
                            float(candidate.distance_m)
                            if persisted_distance and candidate.distance_m is not None
                            else None
                        ),
                    },
                )
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
                        "bootstrap_scopes": [
                            {
                                "member_id": member_id,
                                "traveler_id": traveler_id,
                                "receipt_id": receipt_id,
                                "source_kind": source_kind,
                                "expires_at": _iso(expires_at),
                                "distance_m": (
                                    float(candidate.distance_m)
                                    if persisted_distance and candidate.distance_m is not None
                                    else None
                                ),
                            }
                        ],
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
            _candidate_payload(row, member_id=member_id, traveler_id=traveler_id)
            for row in session.scalars(
                select(RealPlaceCandidate).where(
                    RealPlaceCandidate.journey_id == journey.id,
                    RealPlaceCandidate.status == "BOOTSTRAP_PRIVATE",
                ).order_by(RealPlaceCandidate.captured_at, RealPlaceCandidate.id)
            ).all()
            if _candidate_scope_matches(row, member_id=member_id, traveler_id=traveler_id)
        ],
    }


def preview_bootstrap_candidate(
    session: Session,
    journey: Journey,
    *,
    member: Any,
    traveler_id: str,
    receipt_id: UUID,
    candidate_id: UUID,
    public_map_consent: bool,
    latitude: float,
    longitude: float,
) -> dict[str, Any]:
    """Release one public destination to a map without changing Journey truth.

    The returned URL contains only the selected public OSM destination.  The signed
    receipt, member scope, expiry and exact WGS84 coordinates are checked again at the
    release boundary so a stale screen cannot disclose a different candidate or a
    foreground location as an origin.
    """

    if str(journey.status).upper() != "DRAFT":
        raise BootstrapDiscoveryError(
            "BOOTSTRAP_REQUIRES_DRAFT",
            "map preview requires a DRAFT Journey",
        )
    if journey.active_plan_version_id is not None or session.scalar(
        select(PlanVersion.id).where(PlanVersion.journey_id == journey.id).limit(1)
    ):
        raise BootstrapDiscoveryError(
            "BOOTSTRAP_PLAN_ALREADY_EXISTS",
            "map preview requires no PlanVersion",
        )
    if not public_map_consent:
        raise BootstrapDiscoveryError(
            "BOOTSTRAP_PUBLIC_MAP_CONSENT_REQUIRED",
            "explicit per-release public map consent is required",
            status_code=422,
            details={
                "shared": ["public_destination"],
                "withheld": ["origin", "foreground_gps", "query_center"],
                "next_actions": ["CONFIRM_PUBLIC_MAP_CONSENT", "CANCEL_MAP_PREVIEW"],
            },
        )
    _finite_coordinate(float(latitude), float(longitude))
    row = session.scalar(
        select(RealPlaceCandidate).where(
            RealPlaceCandidate.id == str(candidate_id),
            RealPlaceCandidate.journey_id == journey.id,
            RealPlaceCandidate.provider_key == "overpass",
        )
    )
    if row is None:
        raise BootstrapDiscoveryError(
            "BOOTSTRAP_CANDIDATE_NOT_FOUND",
            "bootstrap candidate was not found",
            status_code=404,
        )
    evidence = json.loads(row.evidence_json or "{}")
    if not evidence.get("bootstrap"):
        raise BootstrapDiscoveryError(
            "BOOTSTRAP_RECEIPT_MISMATCH",
            "candidate does not belong to this discovery receipt",
            status_code=403,
        )
    matching_scope = _matching_candidate_scope(
        evidence,
        member_id=str(member.id),
        traveler_id=str(traveler_id),
        receipt_id=str(receipt_id),
    )
    if matching_scope is None:
        raise BootstrapDiscoveryError(
            "BOOTSTRAP_MEMBER_MISMATCH",
            "candidate belongs to another signed member",
            status_code=403,
        )
    if row.status != "BOOTSTRAP_PRIVATE" or row.materialized_place_id is not None:
        raise BootstrapDiscoveryError(
            "BOOTSTRAP_CANDIDATE_UNAVAILABLE",
            "bootstrap candidate is no longer available for map preview",
            status_code=409,
        )
    if _scope_expired(matching_scope):
        raise BootstrapDiscoveryError(
            "BOOTSTRAP_RECEIPT_EXPIRED",
            "the discovery receipt expired; search again before opening a public map",
            status_code=410,
            details={"next_actions": ["SEARCH_AGAIN", "CANCEL_MAP_PREVIEW"]},
        )
    if not matching_scope.get("expires_at") and row.expires_at:
        try:
            expires_at = datetime.fromisoformat(row.expires_at).astimezone(timezone.utc)
        except ValueError:
            expires_at = _now() - timedelta(seconds=1)
        if expires_at <= _now():
            raise BootstrapDiscoveryError(
                "BOOTSTRAP_RECEIPT_EXPIRED",
                "the discovery receipt expired; search again before opening a public map",
                status_code=410,
                details={"next_actions": ["SEARCH_AGAIN", "CANCEL_MAP_PREVIEW"]},
            )
    if not math.isclose(float(latitude), float(row.latitude), abs_tol=1e-6) or not math.isclose(
        float(longitude), float(row.longitude), abs_tol=1e-6
    ):
        raise BootstrapDiscoveryError(
            "BOOTSTRAP_MAP_PREVIEW_COORDINATE_MISMATCH",
            "the pending map destination changed; cancel this preview and choose the candidate again",
            status_code=409,
            details={
                "next_actions": ["CANCEL_MAP_PREVIEW", "CHOOSE_CANDIDATE_AGAIN"],
                "coordinate_system": "WGS84",
            },
        )
    osm = _osm_identity(
        DiscoveryCandidate(
            provider_key=row.provider_key,
            external_id=row.external_id,
            name=row.name,
            category=row.category,
            latitude=row.latitude,
            longitude=row.longitude,
            tags=(),
            opening_hours={},
            metadata={},
        )
    )
    if osm is None:
        raise BootstrapDiscoveryError(
            "BOOTSTRAP_IDENTITY_INVALID",
            "candidate OSM identity is invalid",
            status_code=422,
        )
    osm_type, osm_id = osm
    source_url = f"https://www.openstreetmap.org/{osm_type}/{osm_id}"
    map_url = (
        "https://www.openstreetmap.org/?mlat="
        f"{float(row.latitude):.7f}&mlon={float(row.longitude):.7f}"
        f"#map=18/{float(row.latitude):.7f}/{float(row.longitude):.7f}"
    )
    metadata = json.loads(row.metadata_json or "{}")
    if not isinstance(metadata, dict):
        metadata = {}
    osm_tags = metadata.get("osm_tags") or metadata.get("tags") or {}
    if not isinstance(osm_tags, dict):
        osm_tags = {}
    source_tags = {
        key: str(osm_tags[key])
        for key in (
            "opening_hours",
            "website",
            "contact:website",
            "phone",
            "contact:phone",
            "email",
        )
        if osm_tags.get(key) not in (None, "")
    }
    opening = json.loads(row.opening_hours_json or "{}")
    if not isinstance(opening, dict):
        opening = {"status": "UNKNOWN"}
    opening_status = str(opening.get("status") or "UNKNOWN").upper()
    return {
        "preview_id": str(uuid4()),
        "status": "PUBLIC_DESTINATION_READY",
        "journey_id": journey.id,
        "receipt_id": str(receipt_id),
        "candidate_id": row.id,
        "expires_at": row.expires_at,
        "provider": "overpass",
        "provider_provenance": "LIVE_OPENSTREETMAP_OVERPASS",
        "destination": {
            "name": row.name,
            "external_id": row.external_id,
            "osm_type": osm_type,
            "osm_id": osm_id,
            "latitude": row.latitude,
            "longitude": row.longitude,
            "coordinate_system": "WGS84",
            "source_url": source_url,
            "map_url": map_url,
        },
        "opening": {
            "state": opening_status,
            "raw": opening.get("raw") or source_tags.get("opening_hours"),
            "source_tags": source_tags,
            "source": "OpenStreetMap/Overpass",
            "observed_at": row.captured_at,
            "claim": "OSM_TAG_CLAIM" if source_tags.get("opening_hours") else "NO_OPENING_TAG",
            "verification_state": (
                "PROVIDER_GROUNDED"
                if opening_status in _BOOTSTRAP_GROUNDED_OPENING
                else "EXTERNAL_NOT_ATTESTED"
            ),
            "verification_action": "OPEN_SOURCE_PAGE",
        },
        "explore_state": "DRAFT_EXPLORE_ONLY",
        "shared_fields": ["public_destination", "osm_id", "source_url"],
        "withheld_fields": ["origin", "foreground_gps", "query_center", "member_id", "traveler_id"],
        "plan_version_id": None,
        "selected_place_id": None,
    }


def _bootstrap_scope_for_request(
    row: RealPlaceCandidate,
    *,
    member: Any,
    traveler_id: str,
    receipt_id: UUID,
) -> dict[str, Any]:
    evidence = json.loads(row.evidence_json or "{}")
    if not evidence.get("bootstrap"):
        raise BootstrapDiscoveryError(
            "BOOTSTRAP_RECEIPT_MISMATCH",
            "candidate does not belong to this discovery receipt",
            status_code=403,
        )
    scope = _matching_candidate_scope(
        evidence,
        member_id=str(member.id),
        traveler_id=str(traveler_id),
        receipt_id=str(receipt_id),
    )
    if scope is None:
        raise BootstrapDiscoveryError(
            "BOOTSTRAP_MEMBER_MISMATCH",
            "candidate belongs to another signed member",
            status_code=403,
        )
    if _scope_expired(scope) or (not scope.get("expires_at") and row.expires_at and _scope_expired({"expires_at": row.expires_at})):
        raise BootstrapDiscoveryError(
            "BOOTSTRAP_RECEIPT_EXPIRED",
            "the discovery receipt expired; search again before saving or opening this place",
            status_code=410,
            details={"next_actions": ["SEARCH_AGAIN", "CANCEL_MAP_PREVIEW"]},
        )
    return scope


def save_bootstrap_shortlist_item(
    session: Session,
    journey: Journey,
    *,
    member: Any,
    traveler_id: str,
    receipt_id: UUID,
    candidate_id: UUID,
) -> dict[str, Any]:
    if str(journey.status).upper() != "DRAFT":
        raise BootstrapDiscoveryError("BOOTSTRAP_REQUIRES_DRAFT", "saving a shortlist item requires a DRAFT Journey")
    if journey.active_plan_version_id is not None or session.scalar(
        select(PlanVersion.id).where(PlanVersion.journey_id == journey.id).limit(1)
    ):
        raise BootstrapDiscoveryError("BOOTSTRAP_PLAN_ALREADY_EXISTS", "saving a shortlist item requires no PlanVersion")
    row = session.scalar(
        select(RealPlaceCandidate).where(
            RealPlaceCandidate.id == str(candidate_id),
            RealPlaceCandidate.journey_id == journey.id,
            RealPlaceCandidate.provider_key == "overpass",
        )
    )
    if row is None:
        raise BootstrapDiscoveryError("BOOTSTRAP_CANDIDATE_NOT_FOUND", "bootstrap candidate was not found", status_code=404)
    scope = _bootstrap_scope_for_request(
        row, member=member, traveler_id=traveler_id, receipt_id=receipt_id
    )
    if row.status != "BOOTSTRAP_PRIVATE" or row.materialized_place_id is not None:
        raise BootstrapDiscoveryError(
            "BOOTSTRAP_CANDIDATE_UNAVAILABLE",
            "bootstrap candidate is no longer available to save",
            status_code=409,
        )
    existing = session.scalar(
        select(MemberDraftShortlistItem).where(
            MemberDraftShortlistItem.journey_id == journey.id,
            MemberDraftShortlistItem.member_id == str(member.id),
            MemberDraftShortlistItem.traveler_id == str(traveler_id),
            MemberDraftShortlistItem.external_id == row.external_id,
            MemberDraftShortlistItem.status == "SAVED",
        )
    )
    if existing is not None:
        return _shortlist_payload(existing)
    saved_count = session.scalar(
        select(func.count(MemberDraftShortlistItem.id)).where(
            MemberDraftShortlistItem.journey_id == journey.id,
            MemberDraftShortlistItem.member_id == str(member.id),
            MemberDraftShortlistItem.traveler_id == str(traveler_id),
            MemberDraftShortlistItem.status == "SAVED",
        )
    ) or 0
    if saved_count >= _MAX_SHORTLIST_ITEMS:
        raise BootstrapDiscoveryError(
            "BOOTSTRAP_SHORTLIST_LIMIT",
            "a draft shortlist can contain at most three public places",
            status_code=409,
            details={"limit": _MAX_SHORTLIST_ITEMS, "next_actions": ["REMOVE_A_PLACE", "CHOOSE_ANOTHER_CANDIDATE"]},
        )
    now = _iso(_now())
    evidence = json.loads(row.evidence_json or "{}")
    source_url = str(evidence.get("source_url") or "")
    osm = _osm_identity(
        DiscoveryCandidate(
            provider_key=row.provider_key,
            external_id=row.external_id,
            name=row.name,
            category=row.category,
            latitude=row.latitude,
            longitude=row.longitude,
            tags=(),
            opening_hours={},
            metadata={},
        )
    )
    if osm is None:
        raise BootstrapDiscoveryError("BOOTSTRAP_IDENTITY_INVALID", "candidate OSM identity is invalid", status_code=422)
    source_url = source_url or f"https://www.openstreetmap.org/{osm[0]}/{osm[1]}"
    metadata = json.loads(row.metadata_json or "{}")
    cost = metadata.get("cost_evidence") if isinstance(metadata, dict) else None
    if not isinstance(cost, dict):
        cost = {"status": "UNKNOWN"}
    opening = json.loads(row.opening_hours_json or "{}")
    if not isinstance(opening, dict):
        opening = {"status": "UNKNOWN"}
    source_kind = str(scope.get("source_kind") or "")
    distance_m = scope.get("distance_m") if source_kind == "MANUAL_PUBLIC_CENTER" else None
    item = MemberDraftShortlistItem(
        id=str(uuid4()),
        journey_id=journey.id,
        member_id=str(member.id),
        traveler_id=str(traveler_id),
        provider_key="overpass",
        external_id=row.external_id,
        name=row.name,
        category=row.category,
        latitude=row.latitude,
        longitude=row.longitude,
        coordinate_system="WGS84",
        source_url=source_url,
        source_provenance="LIVE_OPENSTREETMAP_OVERPASS",
        captured_at=row.captured_at,
        opening_hours_json=_json(opening),
        cost_evidence_json=_json(cost),
        source_tags_json=_json(_public_tags_for_candidate(row)),
        distance_m=float(distance_m) if distance_m is not None else None,
        distance_basis=source_kind if distance_m is not None else None,
        status="SAVED",
        created_at=now,
        updated_at=now,
    )
    session.add(item)
    session.flush()
    return _shortlist_payload(item)


def list_bootstrap_shortlist_items(
    session: Session,
    journey: Journey,
    *,
    member: Any,
    traveler_id: str,
) -> dict[str, Any]:
    if str(journey.status).upper() != "DRAFT":
        raise BootstrapDiscoveryError("BOOTSTRAP_REQUIRES_DRAFT", "a shortlist is available only while the Journey is DRAFT")
    if journey.active_plan_version_id is not None or session.scalar(
        select(PlanVersion.id).where(PlanVersion.journey_id == journey.id).limit(1)
    ):
        raise BootstrapDiscoveryError("BOOTSTRAP_PLAN_ALREADY_EXISTS", "a shortlist is unavailable after a PlanVersion exists")
    rows = session.scalars(
        select(MemberDraftShortlistItem)
        .where(
            MemberDraftShortlistItem.journey_id == journey.id,
            MemberDraftShortlistItem.member_id == str(member.id),
            MemberDraftShortlistItem.traveler_id == str(traveler_id),
            MemberDraftShortlistItem.status == "SAVED",
        )
        .order_by(MemberDraftShortlistItem.created_at, MemberDraftShortlistItem.id)
    ).all()
    return {
        "journey_id": journey.id,
        "limit": _MAX_SHORTLIST_ITEMS,
        "items": [_shortlist_payload(row) for row in rows],
    }


def remove_bootstrap_shortlist_item(
    session: Session,
    journey: Journey,
    *,
    member: Any,
    traveler_id: str,
    shortlist_id: UUID,
) -> dict[str, Any]:
    if str(journey.status).upper() != "DRAFT":
        raise BootstrapDiscoveryError("BOOTSTRAP_REQUIRES_DRAFT", "a shortlist is mutable only while the Journey is DRAFT")
    if journey.active_plan_version_id is not None or session.scalar(
        select(PlanVersion.id).where(PlanVersion.journey_id == journey.id).limit(1)
    ):
        raise BootstrapDiscoveryError("BOOTSTRAP_PLAN_ALREADY_EXISTS", "a shortlist is immutable after a PlanVersion exists")
    row = session.scalar(
        select(MemberDraftShortlistItem).where(
            MemberDraftShortlistItem.id == str(shortlist_id),
            MemberDraftShortlistItem.journey_id == journey.id,
        )
    )
    if row is None:
        raise BootstrapDiscoveryError("BOOTSTRAP_SHORTLIST_NOT_FOUND", "shortlist item was not found", status_code=404)
    if row.member_id != str(member.id) or row.traveler_id != str(traveler_id):
        raise BootstrapDiscoveryError("BOOTSTRAP_SHORTLIST_MEMBER_MISMATCH", "shortlist item belongs to another signed member", status_code=403)
    session.delete(row)
    session.flush()
    return {"journey_id": journey.id, "shortlist_id": str(shortlist_id), "removed": True, "place_id": None}


def preview_bootstrap_shortlist_item(
    session: Session,
    journey: Journey,
    *,
    member: Any,
    traveler_id: str,
    shortlist_id: UUID,
    public_map_consent: bool,
) -> dict[str, Any]:
    if str(journey.status).upper() != "DRAFT":
        raise BootstrapDiscoveryError("BOOTSTRAP_REQUIRES_DRAFT", "shortlist map preview requires a DRAFT Journey")
    if journey.active_plan_version_id is not None or session.scalar(
        select(PlanVersion.id).where(PlanVersion.journey_id == journey.id).limit(1)
    ):
        raise BootstrapDiscoveryError("BOOTSTRAP_PLAN_ALREADY_EXISTS", "shortlist map preview requires no PlanVersion")
    if not public_map_consent:
        raise BootstrapDiscoveryError(
            "BOOTSTRAP_PUBLIC_MAP_CONSENT_REQUIRED",
            "explicit per-release public map consent is required",
            status_code=422,
            details={"shared": ["public_destination"], "withheld": ["origin", "foreground_gps"], "next_actions": ["CONFIRM_PUBLIC_MAP_CONSENT", "CANCEL_MAP_PREVIEW"]},
        )
    row = session.scalar(
        select(MemberDraftShortlistItem).where(
            MemberDraftShortlistItem.id == str(shortlist_id),
            MemberDraftShortlistItem.journey_id == journey.id,
            MemberDraftShortlistItem.status == "SAVED",
        )
    )
    if row is None:
        raise BootstrapDiscoveryError("BOOTSTRAP_SHORTLIST_NOT_FOUND", "shortlist item was not found", status_code=404)
    if row.member_id != str(member.id) or row.traveler_id != str(traveler_id):
        raise BootstrapDiscoveryError("BOOTSTRAP_SHORTLIST_MEMBER_MISMATCH", "shortlist item belongs to another signed member", status_code=403)
    opening = json.loads(row.opening_hours_json or "{}")
    if not isinstance(opening, dict):
        opening = {"status": "UNKNOWN"}
    source_tags = json.loads(row.source_tags_json or "{}")
    if not isinstance(source_tags, dict):
        source_tags = {}
    opening_status = str(opening.get("status") or "UNKNOWN").upper()
    return {
        "preview_id": str(uuid4()),
        "status": "PUBLIC_DESTINATION_READY",
        "journey_id": journey.id,
        "shortlist_id": row.id,
        "authorization_basis": "SAVED_PUBLIC_IDENTITY",
        "destination": {
            "name": row.name,
            "external_id": row.external_id,
            "source_url": row.source_url,
            "latitude": row.latitude,
            "longitude": row.longitude,
            "coordinate_system": "WGS84",
            "map_url": _public_map_url(row.latitude, row.longitude),
        },
        "opening": {
            "state": opening_status,
            "raw": opening.get("raw") or source_tags.get("opening_hours"),
            "source_tags": source_tags,
            "source": row.source_provenance,
            "observed_at": row.captured_at,
            "claim": "OSM_TAG_CLAIM" if source_tags.get("opening_hours") else "NO_OPENING_TAG",
            "verification_state": "EXTERNAL_NOT_ATTESTED" if opening_status not in _BOOTSTRAP_GROUNDED_OPENING else "PROVIDER_GROUNDED",
            "verification_action": "OPEN_SOURCE_PAGE",
        },
        "explore_state": "DRAFT_EXPLORE_ONLY",
        "shared_fields": ["public_destination", "osm_id", "source_url"],
        "withheld_fields": ["origin", "foreground_gps", "query_center", "member_id", "traveler_id", "receipt_id"],
        "plan_version_id": None,
        "selected_place_id": None,
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
    if not evidence.get("bootstrap"):
        raise BootstrapDiscoveryError("BOOTSTRAP_RECEIPT_MISMATCH", "candidate does not belong to this discovery receipt", status_code=403)
    matching_scope = _matching_candidate_scope(
        evidence,
        member_id=str(member.id),
        traveler_id=str(traveler_id),
        receipt_id=str(receipt_id),
    )
    if matching_scope is None:
        raise BootstrapDiscoveryError("BOOTSTRAP_MEMBER_MISMATCH", "candidate belongs to another signed member", status_code=403)
    if _scope_expired(matching_scope):
        raise BootstrapDiscoveryError("BOOTSTRAP_CANDIDATE_EXPIRED", "bootstrap candidate receipt expired", status_code=410)
    expires_at = row.expires_at if not matching_scope.get("expires_at") else None
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
