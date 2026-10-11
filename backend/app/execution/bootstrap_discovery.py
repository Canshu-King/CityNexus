"""Zero-catalogue discovery before a Journey has a plan.

This path is deliberately separate from the active-Journey live scout.  It accepts a
signed Journey member, records an explicit provider/source consent, keeps the provider
results private until one candidate is selected, and materializes at most one Place.
"""

from __future__ import annotations

import json
import hashlib
import ipaddress
import math
import re
import httpx
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import urlparse
from uuid import NAMESPACE_URL, UUID, uuid4, uuid5

from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import (
    IdempotencyKey,
    Journey,
    MemberDraftPocketWalk,
    MemberDraftResumeIntent,
    MemberDraftShortlistItem,
    Place,
    PlanVersion,
    ProviderCall,
    RealPlaceCandidate,
)
from app.integrations.discovery.real_city import (
    DiscoveryCandidate,
    NominatimGeocoder,
    OverpassPOIProvider,
    PhotonCityGeocoder,
)
from app.integrations.mobility.valhalla_http import (
    ValhallaHTTPMobilityProvider,
    ValhallaProviderError,
)
from app.integrations.provider_config import (
    ExternalProviderSettings,
    trust_environment_for_public_providers,
)
from app.execution.shared_walk import (
    SharedWalkParseError,
    validate_shared_walk_objects,
)


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


def _provider_provenance(attempts: list[dict[str, Any]], *, configured_url: str | None = None) -> str:
    """Grade the provider that actually answered this request.

    A local/explicit test boundary is never promoted to an OSM live claim just
    because it returned HTTP 200.  Unknown endpoints remain unverified until an
    operator can identify them; only configured public endpoints receive the
    generic LIVE_PROVIDER grade.
    """

    answered = [item for item in attempts if item.get("answered")]
    if not answered:
        return "UNVERIFIED"
    endpoint = str(answered[0].get("endpoint") or configured_url or "").strip()
    if endpoint.upper() in {"TEST_PROVIDER", "TEST_PROVIDER_EMULATOR", "CONTROLLED_TEST_PROVIDER"}:
        return "TEST_PROVIDER"
    try:
        parsed = urlparse(endpoint)
        host = (parsed.hostname or "").lower()
    except ValueError:
        return "UNVERIFIED"
    # The authoritative browser suite binds its provider boundary to loopback;
    # a loopback answer is useful evidence, but it is not a public OSM answer.
    if host in {"127.0.0.1", "localhost", "::1"} or host.endswith(".local"):
        return "TEST_PROVIDER"
    # Source grading cannot claim a verified public endpoint over plaintext
    # HTTP (or from a URL with embedded credentials).  Local test fixtures
    # remain TEST_PROVIDER regardless of scheme, above.
    if parsed.scheme.lower() != "https" or parsed.username or parsed.password:
        return "UNVERIFIED"
    if host in {
        "overpass-api.de",
        "overpass.kumi.systems",
        "overpass.private.coffee",
        "overpass.openstreetmap.fr",
        "nominatim.openstreetmap.org",
        "photon.komoot.io",
    }:
        return "LIVE_PROVIDER"
    return "UNVERIFIED"


def _row_provider_provenance(
    row: RealPlaceCandidate, *, scope: dict[str, Any] | None = None
) -> str:
    # One public OSM identity can be independently discovered by a LIVE member
    # and a controlled TEST member. Their request grades must not be shared.
    if scope is not None:
        scoped_grade = scope.get("provider_provenance")
        if scoped_grade in {"LIVE_PROVIDER", "TEST_PROVIDER", "UNVERIFIED"}:
            return str(scoped_grade)
    evidence = json.loads(row.evidence_json or "{}")
    metadata = json.loads(row.metadata_json or "{}")
    for value in (
        evidence.get("provider_provenance"),
        metadata.get("provider_provenance") if isinstance(metadata, dict) else None,
    ):
        if value:
            return str(value)
    return "UNVERIFIED"


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
    viewer_scope = None
    if member_id is not None and traveler_id is not None:
        for scope in _bootstrap_scope_entries(evidence):
            if scope["member_id"] == str(member_id) and scope["traveler_id"] == str(traveler_id):
                viewer_scope = scope
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
        "provider_provenance": _row_provider_provenance(row, scope=viewer_scope),
    }


def _provider_call(
    session: Session,
    *,
    journey: Journey,
    request: dict[str, Any],
    response: dict[str, Any],
    status: str,
    created_at: str,
    provider_key: str = "overpass",
    operation: str = "bootstrap_city_discovery",
) -> None:
    session.add(
        ProviderCall(
            id=str(uuid4()),
            provider_key=provider_key,
            operation=operation,
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


def _resume_payload(intent: MemberDraftResumeIntent, item: MemberDraftShortlistItem) -> dict[str, Any]:
    """Return public identity only; ownership is enforced by the signed lookup."""

    return {
        "shortlist_id": item.id,
        "journey_id": item.journey_id,
        "name": item.name,
        "category": item.category,
        "latitude": item.latitude,
        "longitude": item.longitude,
        "coordinate_system": item.coordinate_system,
        "source_url": item.source_url,
        "source_provenance": item.source_provenance,
        "captured_at": item.captured_at,
        "selected_at": intent.selected_at,
        "status": "CHOSEN",
    }


def _pocket_stop_payload(row: MemberDraftShortlistItem, position: int) -> dict[str, Any]:
    item = _shortlist_payload(row)
    return {
        "position": position,
        "shortlist_id": item["shortlist_id"],
        "name": item["name"],
        "category": item["category"],
        "external_id": item["external_id"],
        "source_url": item["source_url"],
        "source_provenance": item["source_provenance"],
        "captured_at": item["captured_at"],
        "coordinate_system": item["coordinate_system"],
        "opening_state": item["opening_state"],
        "price_state": item["price_state"],
        "route_eta_state": "UNKNOWN",
    }


def _pocket_walk_payload(
    row: MemberDraftPocketWalk | None,
    items: dict[str, MemberDraftShortlistItem],
) -> dict[str, Any] | None:
    if row is None:
        return None
    first = items.get(str(row.first_shortlist_id))
    second = items.get(str(row.second_shortlist_id))
    if first is None or second is None or first.id == second.id:
        return None
    return {
        "status": "POCKET_WALK_SAVED",
        "journey_id": row.journey_id,
        "first_stop": _pocket_stop_payload(first, 1),
        "second_stop": _pocket_stop_payload(second, 2),
        "max_walk_minutes": row.max_walk_minutes,
        "map_authorization": "NONE",
        "explore_state": "DRAFT_EXPLORE_ONLY",
        "shared_fields": [
            "two ordered public shortlist identities",
            "public OSM source URLs",
            "source provenance and capture time",
            "optional human-declared walking budget",
        ],
        "withheld_fields": [
            "member_id",
            "traveler_id",
            "journey_id",
            "foreground GPS",
            "query center",
            "route estimate",
            "navigation URL",
            "provider receipt",
            "private comments",
        ],
        "plan_version_id": None,
        "selected_place_id": None,
    }


def _load_member_pocket_walk(
    session: Session,
    journey: Journey,
    *,
    member: Any,
    traveler_id: str,
    items: list[MemberDraftShortlistItem],
) -> dict[str, Any] | None:
    row = session.scalar(
        select(MemberDraftPocketWalk).where(
            MemberDraftPocketWalk.journey_id == journey.id,
            MemberDraftPocketWalk.member_id == str(member.id),
            MemberDraftPocketWalk.traveler_id == str(traveler_id),
        )
    )
    return _pocket_walk_payload(row, {str(item.id): item for item in items})


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


def _public_walking_url(latitude: float, longitude: float) -> str:
    """Build a destination-only walking URL; the map provider supplies any origin locally."""

    return (
        "https://www.google.com/maps/dir/?api=1&destination="
        f"{float(latitude):.7f}%2C{float(longitude):.7f}&travelmode=walking"
    )


def _public_two_stop_walking_url(
    first_latitude: float,
    first_longitude: float,
    second_latitude: float,
    second_longitude: float,
) -> str:
    """Build a public-to-public walking URL without a traveller origin."""

    return (
        "https://www.google.com/maps/dir/?api=1&origin="
        f"{float(first_latitude):.7f}%2C{float(first_longitude):.7f}"
        "&destination="
        f"{float(second_latitude):.7f}%2C{float(second_longitude):.7f}"
        "&travelmode=walking"
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
                        "provider_provenance": raw.get("provider_provenance"),
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
                "provider_provenance": evidence.get("provider_provenance"),
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
    operation: str = "bootstrap-discovery",
) -> bool:
    """Claim one provider attempt for this signed Journey/member/traveller scope.

    ProviderCall is an audit trail, not a lock: querying it by city was both
    cross-user noisy and racy under two simultaneous confirmations.  The
    durable idempotency row is claimed before the network call, so a retry or
    concurrent tab cannot create a second external attempt inside the window.
    """

    scope_key = f"{operation}:{journey.id}:{member_id}:{traveler_id}"
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
                        operation=operation,
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
            operation=operation,
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


def _city_result_payload(candidate: DiscoveryCandidate, *, provenance: str) -> dict[str, Any]:
    """Return a geocoder lead that can move a camera, never a selected center."""

    external_id = str(candidate.external_id or "")
    provider, _, identity = external_id.partition(":")
    osm_type, _, osm_id = identity.partition("/")
    metadata = candidate.metadata if isinstance(candidate.metadata, dict) else {}
    display_name = str(metadata.get("display_name") or candidate.name).strip()
    return {
        "result_id": external_id,
        "name": str(candidate.name).strip(),
        "display_name": display_name,
        "provider": provider or candidate.provider_key,
        "provider_provenance": provenance,
        "osm_type": osm_type or None,
        "osm_id": osm_id or None,
        "source_url": (
            f"https://www.openstreetmap.org/{osm_type}/{osm_id}"
            if osm_type and osm_id
            else None
        ),
        "latitude": float(candidate.latitude),
        "longitude": float(candidate.longitude),
        "coordinate_system": "WGS84",
        "confidence": "CITY_CENTROID_UNCERTAIN",
        "selection_state": "CAMERA_ONLY_TAP_REQUIRED",
        "uncertainty": "A city result only positions the map; tap a public area to choose the discovery center.",
    }


_CITY_CACHE_PREFIX = "bootstrap-city-search-cache:"
_CITY_RATE_KEY = "bootstrap-city-search-global-rate"


def _city_search_cache_key(provider: str, query: str) -> str:
    normalized = " ".join(query.casefold().split())
    digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
    return f"{_CITY_CACHE_PREFIX}{provider}:{digest}"


def _city_search_cache_get(
    session: Session, *, provider: str, query: str, now: datetime
) -> dict[str, Any] | None:
    row = session.get(IdempotencyKey, _city_search_cache_key(provider, query))
    if row is None or not row.response_json:
        return None
    try:
        expires_at = datetime.fromisoformat(row.expires_at)
        value = json.loads(row.response_json)
    except (TypeError, ValueError, json.JSONDecodeError):
        return None
    if expires_at <= now or not isinstance(value, dict):
        return None
    return value


def _city_search_cache_put(
    session: Session,
    *,
    provider: str,
    query: str,
    value: dict[str, Any],
    now: datetime,
) -> None:
    key = _city_search_cache_key(provider, query)
    expires_at = now + timedelta(seconds=max(1, settings.city_search_cache_ttl_seconds))
    row = session.get(IdempotencyKey, key)
    if row is None:
        session.add(
            IdempotencyKey(
                key=key,
                operation="bootstrap-city-search-cache",
                request_hash=hashlib.sha256(query.casefold().encode("utf-8")).hexdigest(),
                response_status=200,
                response_json=_json(value),
                created_at=_iso(now),
                expires_at=_iso(expires_at),
                claim_token=None,
                claim_deadline=None,
            )
        )
        return
    row.operation = "bootstrap-city-search-cache"
    row.response_status = 200
    row.response_json = _json(value)
    row.created_at = _iso(now)
    row.expires_at = _iso(expires_at)


def _reserve_city_search_global_slot(session: Session, *, now: datetime) -> bool:
    """Reserve the one-per-second public geocoder slot across all members/processes."""

    key = _CITY_RATE_KEY
    row = session.get(IdempotencyKey, key)
    # A public Nominatim deployment must never be configured below the OSMF
    # one-request-per-second application-wide bound. Apply this floor at the
    # enforcement point even if an operator misconfigures the environment.
    minimum_seconds = max(1.0, settings.city_search_global_min_interval_seconds)
    if row is not None:
        try:
            last = datetime.fromisoformat(row.created_at)
        except (TypeError, ValueError):
            last = now - timedelta(seconds=minimum_seconds)
        if (now - last).total_seconds() < minimum_seconds:
            return False
        changed = session.execute(
            update(IdempotencyKey)
            .where(IdempotencyKey.key == key, IdempotencyKey.created_at == row.created_at)
            .values(
                operation="bootstrap-city-search-global-rate",
                request_hash=str(uuid4()),
                response_status=None,
                response_json=None,
                created_at=_iso(now),
                expires_at=_iso(now + timedelta(seconds=3600)),
            )
        )
        return changed.rowcount == 1
    try:
        with session.begin_nested():
            session.add(
                IdempotencyKey(
                    key=key,
                    operation="bootstrap-city-search-global-rate",
                    request_hash=str(uuid4()),
                    response_status=None,
                    response_json=None,
                    created_at=_iso(now),
                    expires_at=_iso(now + timedelta(seconds=3600)),
                    claim_token=None,
                    claim_deadline=None,
                )
            )
            session.flush()
        return True
    except IntegrityError:
        return False


def _city_search_config() -> tuple[str, str | None, str | None] | None:
    """Return an explicitly approved provider, or None without touching the network."""

    if not settings.city_search_enabled:
        return None
    provider = settings.city_search_provider
    if provider not in {"nominatim", "photon"}:
        return None
    base_url = settings.city_search_base_url
    if not base_url:
        return None
    try:
        parsed = urlparse(base_url)
        host = (parsed.hostname or "").lower()
    except ValueError:
        return None
    is_loopback = host in {"127.0.0.1", "localhost", "::1"}
    # A test flag may relax the identifying User-Agent requirement for a
    # deliberately configured fixture, but must never authorize plaintext
    # public-service requests.
    if not host or (parsed.scheme != "https" and not (is_loopback and parsed.scheme == "http")):
        return None
    # The test-mode switch must not strip an external service of the
    # identifying operator contact.  Only an actual loopback endpoint is
    # exempt from the public-facing User-Agent requirement.
    if not is_loopback:
        # A public endpoint must have a real identifying contact in the UA. The
        # built-in localhost placeholder is intentionally not accepted.
        agent = settings.city_search_user_agent
        if not agent or ("mailto:" not in agent.lower() and "@" not in agent):
            return None
    return provider, base_url, settings.city_search_user_agent or None


def search_bootstrap_city(
    session: Session,
    journey: Journey,
    *,
    member: Any,
    traveler_id: str,
    query: str,
    provider_consent: bool,
    limit: int,
) -> dict[str, Any]:
    """Perform one explicit bounded city search for the R95 map camera."""

    if str(journey.status).upper() != "DRAFT":
        raise BootstrapDiscoveryError("BOOTSTRAP_REQUIRES_DRAFT", "city search requires a DRAFT Journey")
    if journey.active_plan_version_id is not None or session.scalar(
        select(PlanVersion.id).where(PlanVersion.journey_id == journey.id).limit(1)
    ):
        raise BootstrapDiscoveryError("BOOTSTRAP_PLAN_ALREADY_EXISTS", "city search requires no PlanVersion")
    if not provider_consent:
        raise BootstrapDiscoveryError(
            "CITY_SEARCH_CONSENT_REQUIRED",
            "explicit city-search provider consent is required before geocoding",
            status_code=422,
        )
    query = str(query or "").strip()[:120]
    if len(query) < 2:
        raise BootstrapDiscoveryError("INVALID_CITY_QUERY", "city search needs at least two characters", status_code=422)
    member_id = str(member.id)
    traveler_id = str(traveler_id)
    now = _now()
    request = {
        "journey_id": str(journey.id),
        "query": query,
        "limit": limit,
        "operation": "bootstrap-city-search",
        "member_id": member_id,
        "traveler_id": traveler_id,
        "provider_consent": True,
    }
    config = _city_search_config()
    if not settings.real_city_enabled or str(settings.real_city_mode).lower() != "live" or config is None:
        _provider_call(
            session,
            journey=journey,
            request=request,
            response={
                "status": "GEOCODER_DISABLED",
                "attempts": [],
                "count": 0,
                "reason": "operator_configuration_missing",
            },
            status="DEGRADED",
            created_at=_iso(now),
            provider_key="city-geocoder",
            operation="bootstrap_city_search",
        )
        return {
            "journey_id": journey.id,
            "status": "GEOCODER_DISABLED",
            "query": query,
            "provider_attempts": [],
            "results": [],
            "provider_provenance": "UNVERIFIED",
        }
    provider_name, configured_url, configured_user_agent = config
    cached = _city_search_cache_get(session, provider=provider_name, query=query, now=now)
    if cached is not None:
        return {
            "journey_id": journey.id,
            "status": str(cached.get("status") or "CITY_RESULTS"),
            "query": query,
            "provider_provenance": str(cached.get("provider_provenance") or "UNVERIFIED"),
            "provider_attempts": [],
            "cache_hit": True,
            "results": list(cached.get("results") or []),
        }
    if _bootstrap_rate_limited(
        session,
        journey,
        now,
        member_id=member_id,
        traveler_id=traveler_id,
        operation="bootstrap-city-search",
    ):
        raise BootstrapDiscoveryError(
            "CITY_SEARCH_RATE_LIMITED",
            "please wait before asking the city provider again",
            status_code=429,
            details={"retry_after_seconds": _BOOTSTRAP_RATE_LIMIT_SECONDS, "provider_consent": True},
        )
    if not _reserve_city_search_global_slot(session, now=now):
        _provider_call(
            session,
            journey=journey,
            request={"query_hash": hashlib.sha256(query.casefold().encode("utf-8")).hexdigest(), "limit": limit},
            response={"status": "GEOCODER_RATE_LIMITED", "attempts": [], "count": 0},
            status="DEGRADED",
            created_at=_iso(now),
            provider_key="city-geocoder",
            operation="bootstrap_city_search",
        )
        return {
            "journey_id": journey.id,
            "status": "GEOCODER_RATE_LIMITED",
            "query": query,
            "provider_provenance": "UNVERIFIED",
            "provider_attempts": [],
            "cache_hit": False,
            "results": [],
        }

    # The global slot is an independent, durable request claim. Commit it
    # before an external HTTP wait: otherwise SQLite holds a writer lock
    # across provider latency, and a rollback could erase the rate boundary.
    session.commit()

    geocoder: NominatimGeocoder | PhotonCityGeocoder
    if provider_name == "nominatim":
        geocoder = NominatimGeocoder(base_url=configured_url, user_agent=configured_user_agent)
    else:
        geocoder = PhotonCityGeocoder(base_url=configured_url, user_agent=configured_user_agent)
    attempts: list[dict[str, Any]] = []
    results: list[DiscoveryCandidate] = []
    try:
        endpoint = getattr(geocoder, "base_url", configured_url)
        started = _now()
        try:
            # One explicit search only; this is never autocomplete and never a
            # second fallback request to a different public service.
            results = geocoder.search(query, city="", limit=limit)
            attempts.append(
                {
                    "provider": provider_name,
                    "endpoint": endpoint,
                    "answered": True,
                    "count": len(results),
                    "elapsed_ms": round((_now() - started).total_seconds() * 1000, 1),
                }
            )
        except Exception as exc:  # keep the public failure shape bounded and screen-safe
            attempts.append(
                {
                    "provider": provider_name,
                    "endpoint": endpoint,
                    "answered": False,
                    "count": 0,
                    "error": type(exc).__name__,
                }
            )
    finally:
        geocoder.close()

    selected = results[:limit]
    provenance = "UNVERIFIED"
    for attempt in attempts:
        if attempt.get("answered"):
            provenance = _provider_provenance([attempt], configured_url=str(attempt.get("endpoint") or ""))
            break
    status = "CITY_RESULTS" if selected else (
        "GEOCODER_UNAVAILABLE" if attempts and not any(item.get("answered") for item in attempts) else "CITY_NO_RESULTS"
    )
    payload = {
        "status": status,
        "provider_provenance": provenance,
        "results": [_city_result_payload(item, provenance=provenance) for item in selected],
    }
    _city_search_cache_put(
        session,
        provider=provider_name,
        query=query,
        value=payload,
        now=now,
    )
    _provider_call(
        session,
        journey=journey,
        request=request,
        response={"status": status, "attempts": attempts, "count": len(selected), "provider_provenance": provenance},
        status="SUCCESS" if selected or any(item.get("answered") for item in attempts) else "DEGRADED",
        created_at=_iso(now),
        provider_key="city-geocoder",
        operation="bootstrap_city_search",
    )
    return {
        "journey_id": journey.id,
        "status": status,
        "query": query,
        "provider_provenance": provenance,
        "provider_attempts": attempts,
        "cache_hit": False,
        "results": payload["results"],
    }


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
            "provider_provenance": "UNVERIFIED",
            "attempts": [],
            "candidates": [],
        }

    provider = OverpassPOIProvider()
    configured_provider_url = provider.base_url
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
            "provider_provenance": "UNVERIFIED",
            "attempts": attempts,
            "candidates": [],
            "failure_code": "PROVIDER_UNAVAILABLE",
        }
    finally:
        provider.close()

    provider_provenance = _provider_provenance(attempts, configured_url=configured_provider_url)

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
                        "provider_provenance": provider_provenance,
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
                        "source": provider_provenance,
                        "provider_provenance": provider_provenance,
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
                                "provider_provenance": provider_provenance,
                                "distance_m": (
                                    float(candidate.distance_m)
                                    if persisted_distance and candidate.distance_m is not None
                                    else None
                                ),
                            }
                        ],
                        "provider_attempts": attempts,
                        "provider_provenance": provider_provenance,
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
            "provider_provenance": provider_provenance,
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
        "provider_provenance": provider_provenance,
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


def lookup_bootstrap_shared_walk(
    session: Session,
    journey: Journey,
    *,
    member: Any,
    traveler_id: str,
    objects: list[dict[str, object]],
    provider_consent: bool,
) -> dict[str, Any]:
    """Verify two public OSM identities for a recipient's own draft Journey.

    The provider sees only the exact public object IDs.  The fresh member scope
    below then flows through the existing shortlist and Pocket Walk gates; no
    sender row, receipt, token or Journey authority is copied.
    """

    if str(journey.status).upper() != "DRAFT":
        raise BootstrapDiscoveryError("BOOTSTRAP_REQUIRES_DRAFT", "shared walk lookup requires a DRAFT Journey")
    if journey.active_plan_version_id is not None or session.scalar(
        select(PlanVersion.id).where(PlanVersion.journey_id == journey.id).limit(1)
    ):
        raise BootstrapDiscoveryError("BOOTSTRAP_PLAN_ALREADY_EXISTS", "shared walk lookup requires no PlanVersion")
    if not provider_consent:
        raise BootstrapDiscoveryError(
            "SHARED_WALK_CONSENT_REQUIRED",
            "explicit exact-object provider consent is required before lookup",
            status_code=422,
        )
    try:
        normalized = validate_shared_walk_objects(objects)
    except SharedWalkParseError as exc:
        raise BootstrapDiscoveryError(exc.code, str(exc), status_code=422) from exc
    member_id = str(member.id)
    traveler_id = str(traveler_id)
    captured_at = _now()
    expires_at = captured_at + timedelta(seconds=settings.real_city_cache_ttl_seconds)
    requested = [(item.osm_type, item.osm_id) for item in normalized]
    request = {
        "operation": "bootstrap_shared_walk_exact_lookup",
        "object_count": len(requested),
        "objects": [{"osm_type": kind, "osm_id": identifier} for kind, identifier in requested],
        "provider_consent": True,
    }
    if not settings.real_city_enabled or str(settings.real_city_mode).lower() != "live":
        _provider_call(
            session,
            journey=journey,
            request=request,
            response={"status": "LOOKUP_BLOCKED", "reason": "PROVIDER_DISABLED", "attempts": [], "count": 0},
            status="DISABLED",
            created_at=_iso(captured_at),
        )
        return {
            "journey_id": journey.id,
            "status": "LOOKUP_BLOCKED",
            "lookup_state": "LOOKUP_BLOCKED",
            "failure_code": "PROVIDER_DISABLED",
            "receipt_id": None,
            "expires_at": None,
            "provider": "overpass",
            "provider_provenance": "UNVERIFIED",
            "attempts": [],
            "candidates": [],
            "verified_count": 0,
        }

    provider = OverpassPOIProvider()
    configured_provider_url = provider.base_url
    attempts: list[dict[str, Any]] = []
    try:
        candidates, attempts = provider.lookup_exact_with_evidence(requested, max_attempts=1)
    except Exception as exc:
        attempts = _attempts(getattr(exc, "provider_attempts", []))
        _provider_call(
            session,
            journey=journey,
            request=request,
            response={"status": "LOOKUP_BLOCKED", "reason": "PROVIDER_UNAVAILABLE", "attempts": attempts, "count": 0},
            status="UNAVAILABLE",
            created_at=_iso(captured_at),
        )
        return {
            "journey_id": journey.id,
            "status": "LOOKUP_BLOCKED",
            "lookup_state": "LOOKUP_BLOCKED",
            "failure_code": "PROVIDER_UNAVAILABLE",
            "receipt_id": None,
            "expires_at": None,
            "provider": "overpass",
            "provider_provenance": "UNVERIFIED",
            "attempts": attempts,
            "candidates": [],
            "verified_count": 0,
        }
    finally:
        provider.close()

    provider_provenance = _provider_provenance(attempts, configured_url=configured_provider_url)
    requested_external = {f"overpass:{kind}/{identifier}" for kind, identifier in requested}
    by_external: dict[str, DiscoveryCandidate] = {}
    for candidate in candidates:
        if candidate.external_id not in requested_external or not _public_candidate(candidate, radius_m=5000):
            continue
        by_external.setdefault(candidate.external_id, candidate)
    usable = [by_external[f"overpass:{item.osm_type}/{item.osm_id}"] for item in normalized if f"overpass:{item.osm_type}/{item.osm_id}" in by_external]

    receipt_id = str(uuid4())
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
                        "source_kind": "SHARED_PUBLIC_REFERENCE",
                        "expires_at": _iso(expires_at),
                        "provider_provenance": provider_provenance,
                        "distance_m": None,
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
                category=str(candidate.category or "public_place"),
                latitude=float(candidate.latitude),
                longitude=float(candidate.longitude),
                tags_json=_json(list(candidate.tags)),
                opening_hours_json=_json(dict(candidate.opening_hours or {"status": "UNKNOWN"})),
                metadata_json=_json(
                    {
                        "source": provider_provenance,
                        "provider_provenance": provider_provenance,
                        "cost_evidence": cost,
                        "public_access_gate": "NO_EXPLICIT_PRIVATE_ACCESS",
                        "osm_tags": tags,
                        "shared_reference": "UNVERIFIED_SHARED_REFERENCE_BEFORE_LOOKUP",
                    }
                ),
                captured_at=_iso(captured_at),
                expires_at=_iso(expires_at),
                distance_m=None,
                evidence_json=_json(
                    {
                        "bootstrap": True,
                        "receipt_id": receipt_id,
                        "member_id": member_id,
                        "traveler_id": traveler_id,
                        "source_kind": "SHARED_PUBLIC_REFERENCE",
                        "bootstrap_scopes": [
                            {
                                "member_id": member_id,
                                "traveler_id": traveler_id,
                                "receipt_id": receipt_id,
                                "source_kind": "SHARED_PUBLIC_REFERENCE",
                                "expires_at": _iso(expires_at),
                                "provider_provenance": provider_provenance,
                                "distance_m": None,
                            }
                        ],
                        "provider_attempts": attempts,
                        "provider_provenance": provider_provenance,
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
            "status": "SHARED_LOOKUP_RESULTS" if usable else "SHARED_LOOKUP_NO_MATCH",
            "attempts": attempts,
            "count": len(usable),
            "requested_count": len(normalized),
            "provider_provenance": provider_provenance,
        },
        status="SUCCESS",
        created_at=_iso(captured_at),
    )
    rows = session.scalars(
        select(RealPlaceCandidate).where(
            RealPlaceCandidate.journey_id == journey.id,
            RealPlaceCandidate.status == "BOOTSTRAP_PRIVATE",
        ).order_by(RealPlaceCandidate.captured_at, RealPlaceCandidate.id)
    ).all()
    return {
        "journey_id": journey.id,
        "status": "SHARED_LOOKUP_RESULTS" if usable else "SHARED_LOOKUP_NO_MATCH",
        "lookup_state": (
            "VERIFIED_PUBLIC_IDENTITIES"
            if len(usable) == len(normalized)
            else "PARTIAL_PUBLIC_IDENTITIES"
            if usable
            else "LOOKUP_BLOCKED"
        ),
        "failure_code": None if usable else "NO_VERIFIED_MATCH",
        "receipt_id": receipt_id if usable else None,
        "expires_at": _iso(expires_at) if usable else None,
        "provider": "overpass",
        "provider_provenance": provider_provenance,
        "attempts": attempts,
        "verified_count": len(usable),
        "candidates": [
            _candidate_payload(row, member_id=member_id, traveler_id=traveler_id)
            for row in rows
            if _candidate_scope_matches(row, member_id=member_id, traveler_id=traveler_id)
            and row.external_id in {candidate.external_id for candidate in usable}
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
        "provider_provenance": _row_provider_provenance(row, scope=matching_scope),
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
    # A Journey-row write lock is the durable serialization point for the bounded
    # three-item invariant.  It works on SQLite (the deployed local store) and is
    # a row lock on engines that support SELECT/UPDATE locking semantics.  The
    # Keep the caller's transaction intact: the lock is an UPDATE and therefore
    # upgrades the existing read transaction without discarding unrelated pending
    # writes.  The endpoint commits the whole bounded operation atomically.
    locked = session.execute(
        update(Journey)
        .where(Journey.id == journey.id)
        .values(updated_at=Journey.updated_at)
    )
    if locked.rowcount != 1:
        raise BootstrapDiscoveryError("BOOTSTRAP_JOURNEY_NOT_FOUND", "Journey disappeared while saving the shortlist", status_code=404)
    session.flush()
    journey = session.get(Journey, journey.id)
    if journey is None:
        raise BootstrapDiscoveryError("BOOTSTRAP_JOURNEY_NOT_FOUND", "Journey disappeared while saving the shortlist", status_code=404)
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
        source_provenance=_row_provider_provenance(row, scope=scope),
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
    resume = session.scalar(
        select(MemberDraftResumeIntent).where(
            MemberDraftResumeIntent.journey_id == journey.id,
            MemberDraftResumeIntent.member_id == str(member.id),
            MemberDraftResumeIntent.traveler_id == str(traveler_id),
        )
    )
    resume_payload = None
    if resume is not None:
        resume_item = next((row for row in rows if row.id == resume.shortlist_id), None)
        if resume_item is None:
            # A removed or otherwise stale item must fail closed on the next
            # signed read; no destination identity is leaked or reused.
            resume_payload = None
        else:
            resume_payload = _resume_payload(resume, resume_item)
    return {
        "journey_id": journey.id,
        "limit": _MAX_SHORTLIST_ITEMS,
        "items": [_shortlist_payload(row) for row in rows],
        "resume": resume_payload,
        "pocket_walk": _load_member_pocket_walk(
            session,
            journey,
            member=member,
            traveler_id=traveler_id,
            items=rows,
        ),
    }


def save_bootstrap_pocket_walk(
    session: Session,
    journey: Journey,
    *,
    member: Any,
    traveler_id: str,
    first_shortlist_id: UUID,
    second_shortlist_id: UUID,
    max_walk_minutes: int | None,
) -> dict[str, Any]:
    """Persist exactly two ordered shortlist identities for a member's DRAFT Journey."""

    locked = session.execute(
        update(Journey)
        .where(Journey.id == journey.id)
        .values(updated_at=Journey.updated_at)
    )
    if locked.rowcount != 1:
        raise BootstrapDiscoveryError(
            "BOOTSTRAP_JOURNEY_NOT_FOUND",
            "Journey disappeared while saving the Pocket Walk",
            status_code=404,
        )
    session.flush()
    journey = session.get(Journey, journey.id)
    if journey is None:
        raise BootstrapDiscoveryError(
            "BOOTSTRAP_JOURNEY_NOT_FOUND",
            "Journey disappeared while saving the Pocket Walk",
            status_code=404,
        )
    if str(journey.status).upper() != "DRAFT":
        raise BootstrapDiscoveryError(
            "BOOTSTRAP_REQUIRES_DRAFT",
            "a Pocket Walk can be saved only for a DRAFT Journey",
        )
    if journey.active_plan_version_id is not None or session.scalar(
        select(PlanVersion.id).where(PlanVersion.journey_id == journey.id).limit(1)
    ):
        raise BootstrapDiscoveryError(
            "BOOTSTRAP_PLAN_ALREADY_EXISTS",
            "a Pocket Walk can be saved only before a PlanVersion exists",
        )
    first_id = str(first_shortlist_id)
    second_id = str(second_shortlist_id)
    if first_id == second_id:
        raise BootstrapDiscoveryError(
            "BOOTSTRAP_POCKET_STOPS_NOT_DISTINCT",
            "a Pocket Walk requires two different saved public places",
            status_code=422,
        )
    if max_walk_minutes is not None and not 1 <= int(max_walk_minutes) <= 180:
        raise BootstrapDiscoveryError(
            "BOOTSTRAP_POCKET_BUDGET_INVALID",
            "the optional walking budget must be between 1 and 180 minutes",
            status_code=422,
        )
    rows = session.scalars(
        select(MemberDraftShortlistItem).where(
            MemberDraftShortlistItem.id.in_([first_id, second_id]),
            MemberDraftShortlistItem.journey_id == journey.id,
            MemberDraftShortlistItem.member_id == str(member.id),
            MemberDraftShortlistItem.traveler_id == str(traveler_id),
            MemberDraftShortlistItem.status == "SAVED",
        )
    ).all()
    by_id = {str(item.id): item for item in rows}
    if first_id not in by_id or second_id not in by_id:
        raise BootstrapDiscoveryError(
            "BOOTSTRAP_POCKET_STOP_NOT_FOUND",
            "both Pocket Walk stops must be saved public places owned by this signed member",
            status_code=403,
        )
    now = _iso(_now())
    pocket = session.scalar(
        select(MemberDraftPocketWalk).where(
            MemberDraftPocketWalk.journey_id == journey.id,
            MemberDraftPocketWalk.member_id == str(member.id),
            MemberDraftPocketWalk.traveler_id == str(traveler_id),
        )
    )
    if pocket is None:
        pocket = MemberDraftPocketWalk(
            id=str(uuid4()),
            journey_id=journey.id,
            member_id=str(member.id),
            traveler_id=str(traveler_id),
            first_shortlist_id=first_id,
            second_shortlist_id=second_id,
            max_walk_minutes=int(max_walk_minutes) if max_walk_minutes is not None else None,
            created_at=now,
            updated_at=now,
        )
        session.add(pocket)
    else:
        pocket.first_shortlist_id = first_id
        pocket.second_shortlist_id = second_id
        pocket.max_walk_minutes = int(max_walk_minutes) if max_walk_minutes is not None else None
        pocket.updated_at = now
    session.flush()
    return _pocket_walk_payload(pocket, by_id) or {}


def clear_bootstrap_pocket_walk(
    session: Session,
    journey: Journey,
    *,
    member: Any,
    traveler_id: str,
) -> dict[str, Any]:
    """Clear only this signed member's saved Pocket Walk intent."""

    row = session.scalar(
        select(MemberDraftPocketWalk).where(
            MemberDraftPocketWalk.journey_id == journey.id,
            MemberDraftPocketWalk.member_id == str(member.id),
            MemberDraftPocketWalk.traveler_id == str(traveler_id),
        )
    )
    if row is not None:
        session.delete(row)
        session.flush()
    return {
        "journey_id": journey.id,
        "cleared": row is not None,
        "pocket_walk": None,
    }


def remember_bootstrap_shortlist_item(
    session: Session,
    journey: Journey,
    *,
    member: Any,
    traveler_id: str,
    shortlist_id: UUID,
) -> dict[str, Any]:
    """Persist one member-private UI choice, never a route or arrival fact."""

    if str(journey.status).upper() != "DRAFT":
        raise BootstrapDiscoveryError(
            "BOOTSTRAP_REQUIRES_DRAFT",
            "a resume intent is available only while the Journey is DRAFT",
        )
    if journey.active_plan_version_id is not None or session.scalar(
        select(PlanVersion.id).where(PlanVersion.journey_id == journey.id).limit(1)
    ):
        raise BootstrapDiscoveryError(
            "BOOTSTRAP_PLAN_ALREADY_EXISTS",
            "a resume intent is unavailable after a PlanVersion exists",
        )
    item = session.scalar(
        select(MemberDraftShortlistItem).where(
            MemberDraftShortlistItem.id == str(shortlist_id),
            MemberDraftShortlistItem.journey_id == journey.id,
            MemberDraftShortlistItem.status == "SAVED",
        )
    )
    if item is None:
        raise BootstrapDiscoveryError("BOOTSTRAP_SHORTLIST_NOT_FOUND", "shortlist item was not found", status_code=404)
    if item.member_id != str(member.id) or item.traveler_id != str(traveler_id):
        raise BootstrapDiscoveryError(
            "BOOTSTRAP_SHORTLIST_MEMBER_MISMATCH",
            "shortlist item belongs to another signed member",
            status_code=403,
        )
    now = _iso(_now())
    intent = session.scalar(
        select(MemberDraftResumeIntent).where(
            MemberDraftResumeIntent.journey_id == journey.id,
            MemberDraftResumeIntent.member_id == str(member.id),
            MemberDraftResumeIntent.traveler_id == str(traveler_id),
        )
    )
    if intent is None:
        intent = MemberDraftResumeIntent(
            id=str(uuid4()),
            journey_id=journey.id,
            member_id=str(member.id),
            traveler_id=str(traveler_id),
            shortlist_id=item.id,
            selected_at=now,
            created_at=now,
            updated_at=now,
        )
        session.add(intent)
    else:
        intent.shortlist_id = item.id
        intent.selected_at = now
        intent.updated_at = now
    session.flush()
    return _resume_payload(intent, item)


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
    resume = session.scalar(
        select(MemberDraftResumeIntent).where(
            MemberDraftResumeIntent.journey_id == journey.id,
            MemberDraftResumeIntent.member_id == str(member.id),
            MemberDraftResumeIntent.traveler_id == str(traveler_id),
            MemberDraftResumeIntent.shortlist_id == row.id,
        )
    )
    if resume is not None:
        session.delete(resume)
    pocket = session.scalar(
        select(MemberDraftPocketWalk).where(
            MemberDraftPocketWalk.journey_id == journey.id,
            MemberDraftPocketWalk.member_id == str(member.id),
            MemberDraftPocketWalk.traveler_id == str(traveler_id),
            (MemberDraftPocketWalk.first_shortlist_id == row.id)
            | (MemberDraftPocketWalk.second_shortlist_id == row.id),
        )
    )
    if pocket is not None:
        session.delete(pocket)
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
    release_purpose: str = "PIN",
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
    if release_purpose not in {"PIN", "WALKING"}:
        raise BootstrapDiscoveryError(
            "BOOTSTRAP_RELEASE_PURPOSE_INVALID",
            "saved destination release purpose is invalid",
            status_code=422,
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
        "release_purpose": release_purpose,
        "navigation_mode": "WALKING_DIRECTIONS" if release_purpose == "WALKING" else "PUBLIC_PIN",
        "navigation_url": _public_walking_url(row.latitude, row.longitude) if release_purpose == "WALKING" else None,
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


def preview_bootstrap_two_stop_walk(
    session: Session,
    journey: Journey,
    *,
    member: Any,
    traveler_id: str,
    first_shortlist_id: UUID,
    second_shortlist_id: UUID,
    public_map_consent: bool,
) -> dict[str, Any]:
    """Release one explicitly ordered public-to-public walking leg.

    This is an ephemeral explore action.  Both saved identities are checked in
    the current signed member scope and the Journey remains a DRAFT with no
    materialized Place, PlanVersion, arrival, or route-time fact.
    """

    if str(journey.status).upper() != "DRAFT":
        raise BootstrapDiscoveryError(
            "BOOTSTRAP_REQUIRES_DRAFT",
            "a two-stop walk requires a DRAFT Journey",
        )
    if journey.active_plan_version_id is not None or session.scalar(
        select(PlanVersion.id).where(PlanVersion.journey_id == journey.id).limit(1)
    ):
        raise BootstrapDiscoveryError(
            "BOOTSTRAP_PLAN_ALREADY_EXISTS",
            "a two-stop walk requires no PlanVersion",
        )
    if not public_map_consent:
        raise BootstrapDiscoveryError(
            "BOOTSTRAP_TWO_STOP_CONSENT_REQUIRED",
            "explicit consent to share both public stop coordinates is required",
            status_code=422,
            details={
                "shared": ["public_stop_one", "public_stop_two"],
                "withheld": [
                    "origin",
                    "foreground_gps",
                    "query_center",
                    "member_id",
                    "traveler_id",
                    "receipt_id",
                    "route_eta",
                ],
                "next_actions": ["CONFIRM_TWO_STOP_PUBLIC_MAP_CONSENT", "CANCEL_TWO_STOP_WALK"],
            },
        )
    if str(first_shortlist_id) == str(second_shortlist_id):
        raise BootstrapDiscoveryError(
            "BOOTSTRAP_TWO_STOP_DISTINCT_REQUIRED",
            "choose two different saved public places",
            status_code=422,
        )
    rows = session.scalars(
        select(MemberDraftShortlistItem).where(
            MemberDraftShortlistItem.id.in_([str(first_shortlist_id), str(second_shortlist_id)]),
            MemberDraftShortlistItem.journey_id == journey.id,
            MemberDraftShortlistItem.status == "SAVED",
        )
    ).all()
    by_id = {str(row.id): row for row in rows}
    first = by_id.get(str(first_shortlist_id))
    second = by_id.get(str(second_shortlist_id))
    if first is None or second is None:
        raise BootstrapDiscoveryError(
            "BOOTSTRAP_SHORTLIST_NOT_FOUND",
            "both saved public places must still exist",
            status_code=404,
        )
    if any(
        row.member_id != str(member.id) or row.traveler_id != str(traveler_id)
        for row in (first, second)
    ):
        raise BootstrapDiscoveryError(
            "BOOTSTRAP_SHORTLIST_MEMBER_MISMATCH",
            "both saved public places must belong to the signed member",
            status_code=403,
        )
    if first.external_id == second.external_id:
        raise BootstrapDiscoveryError(
            "BOOTSTRAP_TWO_STOP_DISTINCT_REQUIRED",
            "choose two different public OSM identities",
            status_code=422,
        )
    _finite_coordinate(float(first.latitude), float(first.longitude))
    _finite_coordinate(float(second.latitude), float(second.longitude))

    def stop_payload(row: MemberDraftShortlistItem, position: int) -> dict[str, Any]:
        return {
            "position": position,
            "shortlist_id": row.id,
            "name": row.name,
            "category": row.category,
            "external_id": row.external_id,
            "source_url": row.source_url,
            "source_provenance": row.source_provenance,
            "latitude": row.latitude,
            "longitude": row.longitude,
            "coordinate_system": row.coordinate_system,
            "opening_state": str(
                (json.loads(row.opening_hours_json or "{}") or {}).get("status") or "UNKNOWN"
            ).upper(),
            "price_state": "UNKNOWN",
            "route_eta_state": "UNKNOWN",
            "captured_at": row.captured_at,
        }

    return {
        "preview_id": str(uuid4()),
        "status": "PUBLIC_TWO_STOP_WALK_READY",
        "journey_id": journey.id,
        "authorization_basis": "TWO_SAVED_PUBLIC_IDENTITIES",
        "release_purpose": "PUBLIC_POI_TO_PUBLIC_POI_WALKING",
        "navigation_mode": "PUBLIC_POI_TO_PUBLIC_POI_WALKING",
        "navigation_url": _public_two_stop_walking_url(
            first.latitude,
            first.longitude,
            second.latitude,
            second.longitude,
        ),
        "first_stop": stop_payload(first, 1),
        "second_stop": stop_payload(second, 2),
        "route_time_state": "UNKNOWN",
        "explore_state": "DRAFT_EXPLORE_ONLY",
        "shared_fields": [
            "public_stop_one",
            "public_stop_two",
            "coordinates",
            "osm_ids",
            "source_urls",
        ],
        "withheld_fields": [
            "foreground_gps",
            "current_location",
            "member_id",
            "traveler_id",
            "receipt_id",
            "query_center",
            "route_eta",
        ],
        "plan_version_id": None,
        "selected_place_id": None,
    }


def preview_bootstrap_two_stop_walkability(
    session: Session,
    journey: Journey,
    *,
    member: Any,
    traveler_id: str,
    first_shortlist_id: UUID,
    second_shortlist_id: UUID,
    public_route_consent: bool,
) -> dict[str, Any]:
    """Check one explicitly authorized public-to-public walking leg.

    The route preview is advisory and ephemeral.  It never creates a Place,
    MobilityFact, PlanVersion, arrival, or execution receipt.  Only the two
    saved public coordinates cross the configured routing-provider boundary.
    """

    if str(journey.status).upper() != "DRAFT":
        raise BootstrapDiscoveryError(
            "BOOTSTRAP_REQUIRES_DRAFT",
            "walking feasibility requires a DRAFT Journey",
        )
    if journey.active_plan_version_id is not None or session.scalar(
        select(PlanVersion.id).where(PlanVersion.journey_id == journey.id).limit(1)
    ):
        raise BootstrapDiscoveryError(
            "BOOTSTRAP_PLAN_ALREADY_EXISTS",
            "walking feasibility requires no PlanVersion",
        )
    if not public_route_consent:
        raise BootstrapDiscoveryError(
            "BOOTSTRAP_WALKABILITY_CONSENT_REQUIRED",
            "explicit consent to share both public stop coordinates with the walking provider is required",
            status_code=422,
            details={
                "shared": ["public_stop_one", "public_stop_two"],
                "withheld": [
                    "origin",
                    "foreground_gps",
                    "query_center",
                    "member_id",
                    "traveler_id",
                    "receipt_id",
                    "private_intent",
                ],
                "next_actions": ["CONFIRM_TWO_STOP_WALKABILITY_CONSENT", "CANCEL_TWO_STOP_WALKABILITY"],
            },
        )
    if str(first_shortlist_id) == str(second_shortlist_id):
        raise BootstrapDiscoveryError(
            "BOOTSTRAP_TWO_STOP_DISTINCT_REQUIRED",
            "choose two different saved public places",
            status_code=422,
        )
    rows = session.scalars(
        select(MemberDraftShortlistItem).where(
            MemberDraftShortlistItem.id.in_([str(first_shortlist_id), str(second_shortlist_id)]),
            MemberDraftShortlistItem.journey_id == journey.id,
            MemberDraftShortlistItem.status == "SAVED",
        )
    ).all()
    by_id = {str(row.id): row for row in rows}
    first = by_id.get(str(first_shortlist_id))
    second = by_id.get(str(second_shortlist_id))
    if first is None or second is None:
        raise BootstrapDiscoveryError(
            "BOOTSTRAP_SHORTLIST_NOT_FOUND",
            "both saved public places must still exist",
            status_code=404,
        )
    if any(
        row.member_id != str(member.id) or row.traveler_id != str(traveler_id)
        for row in (first, second)
    ):
        raise BootstrapDiscoveryError(
            "BOOTSTRAP_SHORTLIST_MEMBER_MISMATCH",
            "both saved public places must belong to the signed member",
            status_code=403,
        )
    if first.external_id == second.external_id:
        raise BootstrapDiscoveryError(
            "BOOTSTRAP_TWO_STOP_DISTINCT_REQUIRED",
            "choose two different public OSM identities",
            status_code=422,
        )
    if str(first.coordinate_system).upper() != "WGS84" or str(second.coordinate_system).upper() != "WGS84":
        raise BootstrapDiscoveryError(
            "BOOTSTRAP_COORDINATE_SYSTEM_UNSUPPORTED",
            "both saved public places must use WGS84 coordinates",
            status_code=422,
        )
    _finite_coordinate(float(first.latitude), float(first.longitude))
    _finite_coordinate(float(second.latitude), float(second.longitude))

    def stop_payload(row: MemberDraftShortlistItem, position: int) -> dict[str, Any]:
        opening = json.loads(row.opening_hours_json or "{}") or {}
        return {
            "position": position,
            "shortlist_id": row.id,
            "name": row.name,
            "category": row.category,
            "external_id": row.external_id,
            "source_url": row.source_url,
            "source_provenance": row.source_provenance,
            "latitude": row.latitude,
            "longitude": row.longitude,
            "coordinate_system": row.coordinate_system,
            "opening_state": str(opening.get("status") or "UNKNOWN").upper(),
            "price_state": "UNKNOWN",
        }

    observed_at = _iso(_now())
    navigation_url = _public_two_stop_walking_url(
        first.latitude,
        first.longitude,
        second.latitude,
        second.longitude,
    )
    first_payload = stop_payload(first, 1)
    second_payload = stop_payload(second, 2)
    shared_fields = ["public_stop_one", "public_stop_two", "coordinates"]
    withheld_fields = [
        "origin",
        "foreground_gps",
        "current_location",
        "query_center",
        "member_id",
        "traveler_id",
        "receipt_id",
        "private_intent",
        "arrival",
    ]

    def unverified(reason_code: str, reason: str, *, provider: str | None = None) -> dict[str, Any]:
        return {
            "preview_id": str(uuid4()),
            "status": "ROUTE_UNVERIFIED",
            "route_state": "ROUTE_UNVERIFIED",
            "journey_id": journey.id,
            "authorization_basis": "TWO_SAVED_PUBLIC_IDENTITIES",
            "release_purpose": "PUBLIC_POI_TO_PUBLIC_POI_WALKABILITY",
            "navigation_mode": "PUBLIC_POI_TO_PUBLIC_POI_WALKING",
            "navigation_url": navigation_url,
            "first_stop": first_payload,
            "second_stop": second_payload,
            "provider": provider,
            "router_profile": "pedestrian",
            "provenance": "UNVERIFIED",
            "reason_code": reason_code,
            "reason": reason,
            "observed_at": observed_at,
            "duration_min": None,
            "distance_m": None,
            "route_time_state": "UNKNOWN",
            "route_distance_state": "UNKNOWN",
            "route_caveats": [
                "No provider-backed walking duration or distance is available.",
                "External public walking directions remain available as a separate action.",
            ],
            "shared_fields": shared_fields,
            "withheld_fields": withheld_fields,
            "explore_state": "DRAFT_EXPLORE_ONLY",
            "plan_version_id": None,
            "selected_place_id": None,
        }

    provider_settings = ExternalProviderSettings()
    base_url = provider_settings.router_base_url or settings.live_valhalla_url
    router_name = str(provider_settings.router_name or "valhalla").strip().casefold()
    profile = str(provider_settings.router_profile or "pedestrian").strip().casefold()
    # A configured live_valhalla_url is itself an explicit opt-in for the
    # existing mobility stack.  The separate real_mobility_enabled flag still
    # gates router-only configuration, preserving the provider policy seam.
    enabled = bool(base_url) and (
        bool(provider_settings.real_mobility_enabled) or bool(settings.live_valhalla_url)
    )
    if not enabled:
        return unverified("ROUTE_PROVIDER_DISABLED", "No authorized walking provider is configured.")
    if router_name not in {"valhalla", "valhalla-http"} or profile not in {"pedestrian", "walking", "walk"}:
        return unverified(
            "ROUTE_PROVIDER_UNSUPPORTED",
            "The configured walking provider does not expose a supported pedestrian route adapter.",
            provider=router_name or None,
        )
    # A remote plaintext router must not receive even the two public stops
    # under a LIVE_PROVIDER_CAPTURE label. Local loopback emulators may use
    # HTTP, but their adapter evidence grade is TEST_PROVIDER_EMULATOR.
    try:
        parsed_router = urlparse(str(base_url))
        host = (parsed_router.hostname or "").rstrip(".").casefold()
        try:
            loopback = ipaddress.ip_address(host).is_loopback
        except ValueError:
            loopback = host in {"localhost", "localhost.localdomain"} or host.endswith(".localhost")
        approved_scheme = parsed_router.scheme.casefold() == "https" or (
            parsed_router.scheme.casefold() == "http" and loopback
        )
        if (
            not host
            or not approved_scheme
            or parsed_router.username is not None
            or parsed_router.password is not None
            or parsed_router.query
            or parsed_router.fragment
        ):
            return unverified(
                "ROUTE_PROVIDER_ENDPOINT_UNTRUSTED",
                "The configured walking router needs HTTPS, or local loopback HTTP for a test emulator.",
                provider=router_name,
            )
    except ValueError:
        return unverified(
            "ROUTE_PROVIDER_ENDPOINT_UNTRUSTED",
            "The walking router address could not be validated.",
            provider=router_name,
        )

    try:
        timeout = min(max(float(settings.real_city_timeout_seconds), 0.5), 10.0)
        with httpx.Client(
            timeout=timeout,
            trust_env=trust_environment_for_public_providers(),
        ) as client:
            provider = ValhallaHTTPMobilityProvider(
                client=client,
                base_url=str(base_url),
                place_lookup=lambda key: {
                    "latitude": first.latitude if str(key) == str(first.id) else second.latitude,
                    "longitude": first.longitude if str(key) == str(first.id) else second.longitude,
                },
                costing="pedestrian",
                timeout_s=timeout,
                test_provider=settings.live_valhalla_test_provider,
            )
            route = provider.estimate(str(first.id), str(second.id))
        # This is the actual response capture timestamp, not when the
        # request started (the router could have taken several seconds).
        observed_at = _iso(_now())
    except (ValhallaProviderError, httpx.HTTPError, ValueError, TypeError) as exc:
        return unverified(
            "ROUTE_PROVIDER_UNAVAILABLE",
            f"The configured walking provider did not return a usable route ({type(exc).__name__}).",
            provider="valhalla-http",
        )
    except Exception as exc:  # external-provider boundary; keep the explore path fail-closed
        return unverified(
            "ROUTE_PROVIDER_UNAVAILABLE",
            f"The configured walking provider did not return a usable route ({type(exc).__name__}).",
            provider="valhalla-http",
        )

    duration_min = int(route.duration_min)
    distance_m = int(route.distance_m) if route.distance_m is not None else None
    provenance = str(getattr(provider, "capture_provenance", "UNVERIFIED") or "UNVERIFIED").upper()
    if duration_min < 0 or distance_m is None or distance_m < 0 or provenance == "UNVERIFIED":
        return unverified(
            "ROUTE_RESPONSE_INVALID",
            "The configured walking provider returned incomplete or unclassified route evidence.",
            provider="valhalla-http",
        )
    return {
        "preview_id": str(uuid4()),
        "status": "ROUTE_VERIFIED",
        "route_state": "ROUTE_VERIFIED",
        "journey_id": journey.id,
        "authorization_basis": "TWO_SAVED_PUBLIC_IDENTITIES",
        "release_purpose": "PUBLIC_POI_TO_PUBLIC_POI_WALKABILITY",
        "navigation_mode": "PUBLIC_POI_TO_PUBLIC_POI_WALKING",
        "navigation_url": navigation_url,
        "first_stop": first_payload,
        "second_stop": second_payload,
        "provider": str(provider.provider_key),
        "router_profile": "pedestrian",
        "provenance": provenance,
        "reason_code": None,
        "reason": None,
        "observed_at": observed_at,
        "duration_min": duration_min,
        "distance_m": distance_m,
        "route_time_state": "PROVIDER_CAPTURED",
        "route_distance_state": "PROVIDER_CAPTURED",
        "route_caveats": [
            "This is advisory provider evidence, not proof of safety, accessibility, opening, arrival, or a guaranteed ETA.",
            "Opening hours and price remain UNKNOWN from this route check.",
        ],
        "shared_fields": shared_fields,
        "withheld_fields": withheld_fields,
        "explore_state": "DRAFT_EXPLORE_ONLY",
        "plan_version_id": None,
        "selected_place_id": None,
    }


def preview_bootstrap_adaptive_short_walk(
    session: Session,
    journey: Journey,
    *,
    member: Any,
    traveler_id: str,
    first_shortlist_id: UUID,
    current_second_shortlist_id: UUID,
    alternative_second_shortlist_id: UUID,
    max_walk_minutes: int,
    public_route_consent: bool,
) -> dict[str, Any]:
    """Compare one saved second stop with one saved alternative.

    This is deliberately a draft-only, ephemeral comparison.  The routing
    boundary receives only the three public WGS84 identities and the two
    public-to-public pedestrian legs.  No route fact, plan, place, receipt, or
    private location is written by this preview.
    """

    if str(journey.status).upper() != "DRAFT":
        raise BootstrapDiscoveryError(
            "BOOTSTRAP_REQUIRES_DRAFT",
            "adaptive walking comparison requires a DRAFT Journey",
        )
    if journey.active_plan_version_id is not None or session.scalar(
        select(PlanVersion.id).where(PlanVersion.journey_id == journey.id).limit(1)
    ):
        raise BootstrapDiscoveryError(
            "BOOTSTRAP_PLAN_ALREADY_EXISTS",
            "adaptive walking comparison requires no PlanVersion",
        )
    if not public_route_consent:
        raise BootstrapDiscoveryError(
            "BOOTSTRAP_ADAPTIVE_WALK_CONSENT_REQUIRED",
            "explicit consent to share the three public stop coordinates with the walking provider is required",
            status_code=422,
            details={
                "shared": ["public_stop_one", "current_public_stop_two", "alternative_public_stop_two"],
                "withheld": [
                    "origin",
                    "foreground_gps",
                    "current_location",
                    "query_center",
                    "member_id",
                    "traveler_id",
                    "journey_id",
                    "receipt_id",
                    "private_intent",
                    "arrival",
                ],
                "next_actions": [
                    "CONFIRM_ADAPTIVE_SHORT_WALK_CONSENT",
                    "CANCEL_ADAPTIVE_SHORT_WALK",
                ],
            },
        )
    if not isinstance(max_walk_minutes, int) or isinstance(max_walk_minutes, bool) or not 1 <= max_walk_minutes <= 180:
        raise BootstrapDiscoveryError(
            "BOOTSTRAP_ADAPTIVE_WALK_BUDGET_INVALID",
            "walking budget must be an integer between 1 and 180 minutes",
            status_code=422,
        )

    requested_ids = [
        str(first_shortlist_id),
        str(current_second_shortlist_id),
        str(alternative_second_shortlist_id),
    ]
    if len(set(requested_ids)) != 3:
        raise BootstrapDiscoveryError(
            "BOOTSTRAP_ADAPTIVE_STOPS_DISTINCT_REQUIRED",
            "choose three different saved public places",
            status_code=422,
        )
    rows = session.scalars(
        select(MemberDraftShortlistItem).where(
            MemberDraftShortlistItem.id.in_(requested_ids),
            MemberDraftShortlistItem.journey_id == journey.id,
            MemberDraftShortlistItem.status == "SAVED",
        )
    ).all()
    by_id = {str(row.id): row for row in rows}
    first = by_id.get(requested_ids[0])
    current_second = by_id.get(requested_ids[1])
    alternative_second = by_id.get(requested_ids[2])
    if first is None or current_second is None or alternative_second is None:
        raise BootstrapDiscoveryError(
            "BOOTSTRAP_SHORTLIST_NOT_FOUND",
            "all three saved public places must still exist",
            status_code=404,
        )
    if any(
        row.member_id != str(member.id) or row.traveler_id != str(traveler_id)
        for row in (first, current_second, alternative_second)
    ):
        raise BootstrapDiscoveryError(
            "BOOTSTRAP_SHORTLIST_MEMBER_MISMATCH",
            "all three saved public places must belong to the signed member",
            status_code=403,
        )
    if len({str(row.external_id) for row in (first, current_second, alternative_second)}) != 3:
        raise BootstrapDiscoveryError(
            "BOOTSTRAP_ADAPTIVE_STOPS_DISTINCT_REQUIRED",
            "choose three different public OSM identities",
            status_code=422,
        )
    for row in (first, current_second, alternative_second):
        if str(row.coordinate_system).upper() != "WGS84":
            raise BootstrapDiscoveryError(
                "BOOTSTRAP_COORDINATE_SYSTEM_UNSUPPORTED",
                "all saved public places must use WGS84 coordinates",
                status_code=422,
            )
        _finite_coordinate(float(row.latitude), float(row.longitude))

    def stop_payload(row: MemberDraftShortlistItem, position: int) -> dict[str, Any]:
        try:
            opening = json.loads(row.opening_hours_json or "{}") or {}
        except (TypeError, ValueError):
            opening = {}
        return {
            "position": position,
            "shortlist_id": str(row.id),
            "name": row.name,
            "category": row.category,
            "external_id": row.external_id,
            "source_url": row.source_url,
            "source_provenance": row.source_provenance,
            "latitude": row.latitude,
            "longitude": row.longitude,
            "coordinate_system": row.coordinate_system,
            "opening_state": str(opening.get("status") or "UNKNOWN").upper(),
            "price_state": "UNKNOWN",
            "captured_at": row.captured_at,
        }

    first_payload = stop_payload(first, 1)
    current_payload = stop_payload(current_second, 2)
    alternative_payload = stop_payload(alternative_second, 2)
    shared_fields = [
        "public_stop_one",
        "current_public_stop_two",
        "alternative_public_stop_two",
        "coordinates",
    ]
    withheld_fields = [
        "origin",
        "foreground_gps",
        "current_location",
        "query_center",
        "member_id",
        "traveler_id",
        "journey_id",
        "receipt_id",
        "private_intent",
        "arrival",
    ]
    current_navigation_url = _public_two_stop_walking_url(
        first.latitude,
        first.longitude,
        current_second.latitude,
        current_second.longitude,
    )
    alternative_navigation_url = _public_two_stop_walking_url(
        first.latitude,
        first.longitude,
        alternative_second.latitude,
        alternative_second.longitude,
    )

    def unverified_leg(
        reason_code: str,
        reason: str,
        *,
        provider: str | None = None,
        observed_at: str | None = None,
    ) -> dict[str, Any]:
        return {
            "status": "ROUTE_UNVERIFIED",
            "route_state": "ROUTE_UNVERIFIED",
            "duration_min": None,
            "distance_m": None,
            "provider": provider,
            "provenance": "UNVERIFIED",
            "reason_code": reason_code,
            "reason": reason,
            "observed_at": observed_at or _iso(_now()),
            "route_time_state": "UNKNOWN",
            "route_distance_state": "UNKNOWN",
            "route_caveats": [
                "No provider-backed walking duration or distance is available.",
                "External public walking directions remain available as a separate action.",
            ],
        }

    def verified_leg(route: Any, provider: Any, observed_at: str) -> dict[str, Any] | None:
        duration_min = int(route.duration_min)
        distance_m = int(route.distance_m) if route.distance_m is not None else None
        provenance = str(getattr(provider, "capture_provenance", "UNVERIFIED") or "UNVERIFIED").upper()
        if duration_min < 0 or distance_m is None or distance_m < 0 or provenance == "UNVERIFIED":
            return None
        return {
            "status": "ROUTE_VERIFIED",
            "route_state": "ROUTE_VERIFIED",
            "duration_min": duration_min,
            "distance_m": distance_m,
            "provider": str(provider.provider_key),
            "provenance": provenance,
            "reason_code": None,
            "reason": None,
            "observed_at": observed_at,
            "route_time_state": "PROVIDER_CAPTURED",
            "route_distance_state": "PROVIDER_CAPTURED",
            "route_caveats": [
                "This is advisory provider evidence, not proof of safety, accessibility, opening, arrival, or a guaranteed ETA.",
                "Opening hours and price remain UNKNOWN from this route check.",
            ],
        }

    provider_settings = ExternalProviderSettings()
    base_url = provider_settings.router_base_url or settings.live_valhalla_url
    router_name = str(provider_settings.router_name or "valhalla").strip().casefold()
    profile = str(provider_settings.router_profile or "pedestrian").strip().casefold()
    enabled = bool(base_url) and (
        bool(provider_settings.real_mobility_enabled) or bool(settings.live_valhalla_url)
    )
    endpoint_reason: tuple[str, str] | None = None
    if not enabled:
        endpoint_reason = ("ROUTE_PROVIDER_DISABLED", "No authorized walking provider is configured.")
    elif router_name not in {"valhalla", "valhalla-http"} or profile not in {"pedestrian", "walking", "walk"}:
        endpoint_reason = (
            "ROUTE_PROVIDER_UNSUPPORTED",
            "The configured walking provider does not expose a supported pedestrian route adapter.",
        )
    else:
        try:
            parsed_router = urlparse(str(base_url))
            host = (parsed_router.hostname or "").rstrip(".").casefold()
            try:
                loopback = ipaddress.ip_address(host).is_loopback
            except ValueError:
                loopback = host in {"localhost", "localhost.localdomain"} or host.endswith(".localhost")
            approved_scheme = parsed_router.scheme.casefold() == "https" or (
                parsed_router.scheme.casefold() == "http" and loopback
            )
            if (
                not host
                or not approved_scheme
                or parsed_router.username is not None
                or parsed_router.password is not None
                or parsed_router.query
                or parsed_router.fragment
            ):
                endpoint_reason = (
                    "ROUTE_PROVIDER_ENDPOINT_UNTRUSTED",
                    "The configured walking router needs HTTPS, or local loopback HTTP for a test emulator.",
                )
        except ValueError:
            endpoint_reason = (
                "ROUTE_PROVIDER_ENDPOINT_UNTRUSTED",
                "The walking router address could not be validated.",
            )

    if endpoint_reason is not None:
        current_leg = unverified_leg(*endpoint_reason, provider=router_name or None)
        alternative_leg = unverified_leg(*endpoint_reason, provider=router_name or None)
    else:
        current_leg: dict[str, Any]
        alternative_leg: dict[str, Any]
        timeout = min(max(float(settings.real_city_timeout_seconds), 0.5), 10.0)
        lookup = {
            str(first.id): {"latitude": first.latitude, "longitude": first.longitude},
            str(current_second.id): {
                "latitude": current_second.latitude,
                "longitude": current_second.longitude,
            },
            str(alternative_second.id): {
                "latitude": alternative_second.latitude,
                "longitude": alternative_second.longitude,
            },
        }
        try:
            with httpx.Client(
                timeout=timeout,
                trust_env=trust_environment_for_public_providers(),
            ) as client:
                provider = ValhallaHTTPMobilityProvider(
                    client=client,
                    base_url=str(base_url),
                    place_lookup=lambda key: lookup[str(key)],
                    costing="pedestrian",
                    timeout_s=timeout,
                    test_provider=settings.live_valhalla_test_provider,
                )
                try:
                    current_route = provider.estimate(str(first.id), str(current_second.id))
                    current_leg = verified_leg(provider=provider, route=current_route, observed_at=_iso(_now())) or unverified_leg(
                        "ROUTE_RESPONSE_INVALID",
                        "The configured walking provider returned incomplete or unclassified route evidence.",
                        provider="valhalla-http",
                    )
                except (ValhallaProviderError, httpx.HTTPError, ValueError, TypeError, KeyError) as exc:
                    current_leg = unverified_leg(
                        "ROUTE_PROVIDER_UNAVAILABLE",
                        f"The configured walking provider did not return a usable route ({type(exc).__name__}).",
                        provider="valhalla-http",
                    )
                try:
                    alternative_route = provider.estimate(str(first.id), str(alternative_second.id))
                    alternative_leg = verified_leg(provider=provider, route=alternative_route, observed_at=_iso(_now())) or unverified_leg(
                        "ROUTE_RESPONSE_INVALID",
                        "The configured walking provider returned incomplete or unclassified route evidence.",
                        provider="valhalla-http",
                    )
                except (ValhallaProviderError, httpx.HTTPError, ValueError, TypeError, KeyError) as exc:
                    alternative_leg = unverified_leg(
                        "ROUTE_PROVIDER_UNAVAILABLE",
                        f"The configured walking provider did not return a usable route ({type(exc).__name__}).",
                        provider="valhalla-http",
                    )
        except (ValhallaProviderError, httpx.HTTPError, ValueError, TypeError, KeyError) as exc:
            current_leg = unverified_leg(
                "ROUTE_PROVIDER_UNAVAILABLE",
                f"The configured walking provider did not return a usable route ({type(exc).__name__}).",
                provider="valhalla-http",
            )
            alternative_leg = unverified_leg(
                "ROUTE_PROVIDER_UNAVAILABLE",
                f"The configured walking provider did not return a usable route ({type(exc).__name__}).",
                provider="valhalla-http",
            )
        except Exception as exc:  # external-provider boundary; keep draft exploration fail-closed
            current_leg = unverified_leg(
                "ROUTE_PROVIDER_UNAVAILABLE",
                f"The configured walking provider did not return a usable route ({type(exc).__name__}).",
                provider="valhalla-http",
            )
            alternative_leg = unverified_leg(
                "ROUTE_PROVIDER_UNAVAILABLE",
                f"The configured walking provider did not return a usable route ({type(exc).__name__}).",
                provider="valhalla-http",
            )

    current_verified = current_leg.get("status") == "ROUTE_VERIFIED"
    alternative_verified = alternative_leg.get("status") == "ROUTE_VERIFIED"
    suggested_id: str | None = None
    if not current_verified or not alternative_verified:
        recommendation_state = "ROUTE_UNVERIFIED"
        recommendation_reason = "A provider-backed comparison is unavailable; no duration is inferred."
    elif int(alternative_leg["duration_min"]) <= max_walk_minutes and int(alternative_leg["duration_min"]) < int(current_leg["duration_min"]):
        recommendation_state = "WITHIN_MY_LEG_BUDGET"
        suggested_id = str(alternative_second.id)
        recommendation_reason = (
            f"The alternative is {alternative_leg['duration_min']} min estimated vs "
            f"{current_leg['duration_min']} min for the current second stop and fits your "
            f"{max_walk_minutes}-min leg budget."
        )
    elif int(current_leg["duration_min"]) <= max_walk_minutes:
        recommendation_state = "WITHIN_MY_LEG_BUDGET"
        recommendation_reason = (
            f"The current second stop is {current_leg['duration_min']} min estimated and fits "
            f"your {max_walk_minutes}-min leg budget; no alternative is suggested."
        )
    else:
        recommendation_state = "LONGER_THAN_REQUESTED"
        recommendation_reason = (
            f"Neither provider estimate fits your {max_walk_minutes}-min leg budget."
        )

    return {
        "preview_id": str(uuid4()),
        "status": "ADAPTIVE_WALK_READY" if current_verified and alternative_verified else "ADAPTIVE_WALK_UNVERIFIED",
        "route_state": "COMPARISON_VERIFIED" if current_verified and alternative_verified else "ROUTE_UNVERIFIED",
        "journey_id": journey.id,
        "authorization_basis": "THREE_SAVED_PUBLIC_IDENTITIES",
        "release_purpose": "PUBLIC_POI_TO_PUBLIC_POI_ADAPTIVE_WALK",
        "navigation_mode": "PUBLIC_POI_TO_PUBLIC_POI_WALKING",
        "navigation_url": current_navigation_url,
        "alternative_navigation_url": alternative_navigation_url,
        "first_stop": first_payload,
        "current_second_stop": current_payload,
        "alternative_second_stop": alternative_payload,
        "max_walk_minutes": max_walk_minutes,
        "current_leg": current_leg,
        "alternative_leg": alternative_leg,
        "recommendation_state": recommendation_state,
        "suggested_second_shortlist_id": suggested_id,
        "recommendation_reason": recommendation_reason,
        "shared_fields": shared_fields,
        "withheld_fields": withheld_fields,
        "explore_state": "DRAFT_EXPLORE_ONLY",
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
            "provider_provenance": _row_provider_provenance(row, scope=matching_scope),
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
                    "provider_provenance": _row_provider_provenance(row, scope=matching_scope),
                    "origin_provider_provenance": _row_provider_provenance(row),
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
        "provider_provenance": _row_provider_provenance(row, scope=matching_scope),
    }
