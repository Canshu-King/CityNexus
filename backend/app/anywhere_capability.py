"""ORD-0095-1 (CITYNEXUS-ANYWHERE §2/§5/§10): what the backend actually knows about a destination.

Three rules shape this file, and each of them exists because the project has been charged with
breaking it before:

1. **A capability verdict is a server-side policy result, never a count.**
   `READY` requires `readiness_policy_version` to be the thing that decided it, so a destination
   with two museums and no food cannot read "ready for everything" (arbiter v0.2 forbids
   `places.length > 0` explicitly).  The policy is versioned, so "why did this city change state"
   has an answer.

2. **Structure and runtime are two different truths.**  `capability` says what this destination
   *is* (READY / HYDRATABLE / UNAVAILABLE - three values, and deliberately no fourth "unknown":
   "we did not look" is expressed by an *absent* observation, never by a fabricated `OK`).  A
   provider being momentarily unreachable is the other axis and does not make a destination
   structurally unusable, so a resolver failure keeps the destination retryable (R1).

3. **Provenance is never upgraded on the way in.**  Each fact carries the class of source it came
   from (`GOLDEN_FIXTURE` / `REMOTE_PROVIDER` / `SIMULATED` / `REPLAY` / `OFFLINE_SNAPSHOT`) and
   normalisation may only report it, never strengthen it: a simulated row does not become a
   fetched one by passing through a converter.

Everything here reads the database the product already has.  No network: this module answers
"what can we plan with *now*", and a provider cannot make that answer truer.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import CityService, Place

# The three versions that make up a durable fingerprint.  They are constants of *this* file
# because they describe this code's behaviour: changing a bucket mapping or a minimum here is a
# new policy, and the new policy must not silently inherit the old policy's hydrated catalogs.
CATALOG_SCHEMA_VERSION = "catalog-v1"
READINESS_POLICY_VERSION = "readiness-v1"
PROVIDER_POLICY_VERSION = "provider-v1"

# The arbiter's structural axis.  There is no UNKNOWN: "not measured" is absence, not a state.
CAPABILITY_STATES = ("READY", "HYDRATABLE", "UNAVAILABLE")
COVERAGE_STATES = ("READY", "PARTIAL", "MISSING")
COVERAGE_KEYS = ("attractions", "food", "nightlife", "lodging", "mobility", "booking")
# Runtime axis (R2).  Emitted only when an observation actually exists.
PROVIDER_STATUSES = ("OK", "RATE_LIMITED", "UNREACHABLE", "PARTIAL")
SOURCE_KINDS = ("GOLDEN_FIXTURE", "REMOTE_PROVIDER", "SIMULATED", "REPLAY", "OFFLINE_SNAPSHOT")

READY = "READY"
PARTIAL = "PARTIAL"
MISSING = "MISSING"

# Which intent each stored category serves.  This mapping *is* the policy: a category that is not
# listed here serves no intent, which is a decision with a version number, not an oversight.
INTENT_CATEGORIES: dict[str, tuple[str, ...]] = {
    "attractions": ("museum", "heritage", "landmark", "park", "gallery", "attraction", "viewpoint"),
    "food": ("food", "restaurant", "cafe", "street_food"),
    "nightlife": ("nightlife", "bar", "club", "live_music"),
    "lodging": ("lodging", "hotel", "hostel", "apartment"),
    # mobility and booking are not place categories; they are measured below.
    "mobility": (),
    "booking": (),
}
BOOKABLE_SERVICE_TYPES = ("bookable_experience", "tradable_food")
MOBILITY_SERVICE_TYPES = ("mobility_hub", "bike_share", "transit_station", "parking")

# Minimum *usable* material per intent.  Deliberately not one: "at least one" is exactly the
# `places.length > 0` rule the arbitration named as forbidden, and a city with one bar is not a
# city you can plan evenings in.
MIN_READY_CANDIDATES = {
    "attractions": 3,
    "food": 3,
    "nightlife": 2,
    "lodging": 2,
    "mobility": 3,
    "booking": 2,
}
# Share of a destination's place pairs for which we hold an *explicit* travel fact (not the
# fixture's blanket default) before mobility counts as ready.
MOBILITY_EXPLICIT_RATIO_READY = 0.8
STALE_AFTER_DAYS = 90

REASON_CATALOG_CURRENT = "CATALOG_CURRENT"
REASON_COVERAGE_INCOMPLETE = "COVERAGE_INCOMPLETE"
REASON_CATALOG_STALE = "CATALOG_STALE"
REASON_NO_CANONICAL_IDENTITY = "NO_CANONICAL_IDENTITY"
# R1: these are runtime facts and must never be dressed up as the structural verdict.
REASON_RESOLVER_UNAVAILABLE = "DESTINATION_RESOLVER_UNAVAILABLE"
TRANSIENT_REASONS = (
    REASON_RESOLVER_UNAVAILABLE,
    "PROVIDER_RATE_LIMITED",
    "PROVIDER_TIMEOUT",
    "PROVIDER_NETWORK_FAILURE",
    "PROVIDER_SERVER_ERROR",
    "CATALOG_PREPARING",
)

ACTION_START_HYDRATION = "START_HYDRATION"
ACTION_CHOOSE_ANOTHER_DESTINATION = "CHOOSE_ANOTHER_DESTINATION"
ACTION_ACCEPT_PARTIAL_PLAN = "ACCEPT_PARTIAL_PLAN"

# A destination this build cannot name.  The id says so in its own text: an unresolved query must
# not acquire a confident-looking identifier, because that identifier would then be what a
# journey, a fingerprint and a catalog all quietly believe in.
UNRESOLVED_PREFIX = "unresolved:"

_TRAVELER_FACING_LABELS = {
    "CNX-DEMO": ("demo", "演示", "模拟", "cnx-demo"),
}


@dataclass
class DestinationResolution:
    """What a query became, and how sure we are about it."""

    query: str
    canonical_destination_id: str
    city_code: str | None
    method: str
    matched_label: str | None = None
    reason_code: str = ""
    resolver_attempted: bool = False
    resolver_status: str | None = None
    candidates: list[dict[str, Any]] = field(default_factory=list)

    @property
    def resolved(self) -> bool:
        return self.city_code is not None


def _normalise(text: str) -> str:
    return re.sub(r"[\s_\-·、,，.。]+", "", str(text or "")).strip().lower()


def _display_labels() -> dict[str, str]:
    """The traveller-facing names of the city codes, taken from the product's own vocabulary.

    Imported lazily and defensively: `main.py` owns that table today, and a capability answer
    must not crash because the display map moved - it just gets fewer aliases to match on.
    """

    try:
        from app.main import _CITY_DISPLAY_NAMES  # single source, no copy

        return {f"CN-{code}": label for code, label in (_CITY_DISPLAY_NAMES or {}).items()}
    except Exception:  # noqa: BLE001 - absence of a label list is not an error to report as one
        return {}


def resolve_destination(session: Session, query: str) -> DestinationResolution:
    """Turn a query into a canonical destination using only sources already in this process.

    Order matters and is disclosed: a destination the *catalog* names wins over anything a
    provider could later say, because the catalog is what the plan will be built from.  When
    nothing names the query, the answer is an explicitly unresolved identity - not a guess, and
    not a made-up id.
    """

    normalised = _normalise(query)
    if not normalised:
        return DestinationResolution(
            query=str(query or ""),
            canonical_destination_id=f"{UNRESOLVED_PREFIX}empty",
            city_code=None,
            method="none",
            reason_code=REASON_NO_CANONICAL_IDENTITY,
        )

    # 1. the codes the catalog actually holds rows for - the strongest statement we can make.
    held = {
        str(code): int(count or 0)
        for code, count in session.execute(
            select(Place.city_code, func.count(Place.id)).group_by(Place.city_code)
        ).all()
    }
    labels = _display_labels()
    for city_code in sorted(held):
        aliases = {city_code, city_code.replace("CN-", ""), labels.get(city_code, "")}
        for extra, codes in _TRAVELER_FACING_LABELS.items():
            if extra == city_code:
                aliases.update(codes)
        if normalised in {_normalise(item) for item in aliases if item}:
            return DestinationResolution(
                query=str(query),
                canonical_destination_id=city_code,
                city_code=city_code,
                method="catalog",
                matched_label=labels.get(city_code) or city_code,
            )

    # 2. a code the product can *name* but has no rows for: the identity is real, the catalog is
    #    empty.  This is the case a traveller can act on, so it is not "unavailable".
    for city_code, label in sorted(labels.items()):
        aliases = {city_code, city_code.replace("CN-", ""), label}
        if normalised in {_normalise(item) for item in aliases if item}:
            return DestinationResolution(
                query=str(query),
                canonical_destination_id=city_code,
                city_code=city_code,
                method="vocabulary",
                matched_label=label,
            )

    # 3. nothing in this process can name it.
    digest = hashlib.sha1(normalised.encode("utf-8")).hexdigest()[:16]
    return DestinationResolution(
        query=str(query),
        canonical_destination_id=f"{UNRESOLVED_PREFIX}{digest}",
        city_code=None,
        method="unresolved",
        reason_code=REASON_NO_CANONICAL_IDENTITY,
    )


def _source_kind(place: Place) -> str:
    """Classify a row by where it came from - and never strengthen that class."""

    provider_key = str(place.provider_key or "")
    metadata = _loads(getattr(place, "metadata_json", None))
    evidence = str((metadata.get("provenance") or "") if isinstance(metadata, dict) else "")
    if provider_key == "mock-city":
        return "GOLDEN_FIXTURE"
    if provider_key in {"citynexus-demo", "mock-city-demo"}:
        return "SIMULATED"
    if evidence in {"SEALED_REAL_REPLAY", "REPLAY"}:
        return "REPLAY"
    if evidence == "OFFLINE_SNAPSHOT":
        return "OFFLINE_SNAPSHOT"
    if provider_key in {"overpass", "photon", "amap", "valhalla"} or evidence == "LIVE_PROVIDER":
        return "REMOTE_PROVIDER"
    # Unknown origin is reported as unknown-but-weak, never promoted to a stronger class.
    return "OFFLINE_SNAPSHOT"


def _loads(blob: Any) -> dict[str, Any]:
    if isinstance(blob, dict):
        return blob
    try:
        value = json.loads(blob or "{}")
    except (TypeError, ValueError):
        return {}
    return value if isinstance(value, dict) else {}


def _age_days(value: Any) -> float | None:
    moment = None
    try:
        text = str(value)
        moment = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - moment).total_seconds() / 86400.0


def _mobility_evidence(session: Session, city_code: str) -> tuple[int, int]:
    """How many of this destination's place pairs have an explicit travel fact.

    The fixture's blanket `default_minutes` is a constant, not a measurement, so it does not
    count: a destination where every leg answers "20" because the file says so has no mobility
    evidence, however many pairs there are.
    """

    from app.integrations.mock.providers import MOCK_ROOT

    fixture = _loads((MOCK_ROOT / "mobility_matrix.json").read_text(encoding="utf-8"))
    explicit = fixture.get("minutes") if isinstance(fixture.get("minutes"), dict) else {}
    ids = [
        str(item)
        for item in session.scalars(select(Place.id).where(Place.city_code == city_code)).all()
    ]
    pairs = [(origin, destination) for origin in ids for destination in ids if origin != destination]
    covered = sum(1 for origin, destination in pairs if f"{origin}|{destination}" in explicit)
    return covered, len(pairs)


def coverage(session: Session, city_code: str | None) -> dict[str, str]:
    """The flat six-key coverage a screen and a gate both read (`{key: READY|PARTIAL|MISSING}`)."""

    return {key: value["state"] for key, value in coverage_detail(session, city_code).items()}


def coverage_detail(session: Session, city_code: str | None) -> dict[str, dict[str, Any]]:
    """Per-intent counts, quality and provenance, beside the flat states.

    Deliberately a *separate* field: the flat `coverage` map is what the contract pins its enum
    to, and burying the counts inside it would turn every consumer's `coverage["food"]` into a
    dict and break the promise that this surface only ever gains fields.
    """

    detail: dict[str, dict[str, Any]] = {}
    if city_code is None:
        for key in COVERAGE_KEYS:
            detail[key] = {
                "state": MISSING,
                "candidate_count": 0,
                "min_ready": MIN_READY_CANDIDATES[key],
                "source_kinds": [],
                "stale": False,
            }
        return detail

    places = list(session.scalars(select(Place).where(Place.city_code == city_code)).all())
    services = list(
        session.scalars(select(CityService).where(CityService.city_code == city_code)).all()
    )
    by_category: dict[str, list[Place]] = {}
    for place in places:
        by_category.setdefault(str(place.category or ""), []).append(place)

    ages = [
        age
        for age in (_age_days(place.updated_at) for place in places)
        if age is not None
    ]
    stale = bool(places) and all(age > STALE_AFTER_DAYS for age in ages)

    for key in COVERAGE_KEYS:
        if key == "mobility":
            covered, total = _mobility_evidence(session, city_code)
            ratio = (covered / total) if total else 0.0
            count = covered
            state = (
                READY
                if total and ratio >= MOBILITY_EXPLICIT_RATIO_READY and covered >= MIN_READY_CANDIDATES[key]
                else (PARTIAL if covered else MISSING)
            )
        elif key == "booking":
            bookable = [
                item for item in services if str(item.service_type) in BOOKABLE_SERVICE_TYPES
            ]
            count = len(bookable)
            state = _state_for(count, MIN_READY_CANDIDATES[key])
        else:
            rows = [row for cat in INTENT_CATEGORIES[key] for row in by_category.get(cat, [])]
            count = len(rows)
            state = _state_for(count, MIN_READY_CANDIDATES[key])
        detail[key] = {
            "state": state,
            "candidate_count": count,
            "min_ready": MIN_READY_CANDIDATES[key],
            "source_kinds": sorted({_source_kind(place) for place in places}) if places else [],
            "stale": bool(stale),
        }
    return detail


def _state_for(count: int, minimum: int) -> str:
    if count <= 0:
        return MISSING
    if count >= minimum:
        return READY
    return PARTIAL


def capability_fingerprint(canonical_destination_id: str) -> str:
    """The durable idempotency key: which destination, under which three versions.

    Anything that can change the answer is in here; anything that cannot (who asked, when, with
    which idempotency header) is not, so five concurrent requests for one county are one job.
    """

    material = {
        "canonical_destination_id": canonical_destination_id,
        "catalog_schema_version": CATALOG_SCHEMA_VERSION,
        "readiness_policy_version": READINESS_POLICY_VERSION,
        "provider_policy_version": PROVIDER_POLICY_VERSION,
    }
    blob = json.dumps(material, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:32]


def fingerprint_parts(canonical_destination_id: str) -> dict[str, str]:
    """The same four segments, spelled out - a caller must be able to ask *why* keys matched."""

    return {
        "canonical_destination_id": canonical_destination_id,
        "catalog_schema_version": CATALOG_SCHEMA_VERSION,
        "readiness_policy_version": READINESS_POLICY_VERSION,
        "provider_policy_version": PROVIDER_POLICY_VERSION,
    }


def evaluate_capability(
    session: Session,
    query: str,
    *,
    resolution: DestinationResolution | None = None,
    provider_observations: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """The answer `GET /destinations/capability` gives, and the only place it is computed."""

    resolution = resolution or resolve_destination(session, query)
    detail = coverage_detail(session, resolution.city_code)
    flat = {key: value["state"] for key, value in detail.items()}
    missing = [key for key, value in flat.items() if value != READY]
    place_count = int(
        session.scalar(
            select(func.count(Place.id)).where(Place.city_code == resolution.city_code)
        )
        or 0
    ) if resolution.city_code else 0

    if not resolution.resolved:
        # Structural: nothing in this build can name the destination at all.  Note that this
        # branch is *not* reached when a resolver merely failed - R1 keeps that retryable.
        verdict, reason, action = "UNAVAILABLE", REASON_NO_CANONICAL_IDENTITY, ACTION_CHOOSE_ANOTHER_DESTINATION
    elif not missing and not any(detail[key]["stale"] for key in COVERAGE_KEYS):
        verdict, reason, action = READY, REASON_CATALOG_CURRENT, ACTION_ACCEPT_PARTIAL_PLAN
    else:
        # `HYDRATABLE` covers both halves of the arbitration's definition - something missing, or
        # something that has gone stale.  A complete-but-ancient catalog is not "ready": the
        # traveller's answer would be today's plan built from last season's facts.
        verdict = "HYDRATABLE"
        # `STALE` is reserved for "nothing is missing, but what we hold has aged": the two
        # conditions ask for different things from a traveller (prepare more vs refresh), and
        # naming a coverage gap "stale" would send them to the wrong action.
        reason = (
            REASON_CATALOG_STALE
            if not missing and any(detail[key]["stale"] for key in COVERAGE_KEYS)
            else REASON_COVERAGE_INCOMPLETE
        )
        action = ACTION_START_HYDRATION

    places = (
        list(session.scalars(select(Place).where(Place.city_code == resolution.city_code)).all())
        if resolution.city_code
        else []
    )
    source_kinds = sorted({_source_kind(place) for place in places})
    body: dict[str, Any] = {
        "query": str(query),
        "canonical_destination_id": resolution.canonical_destination_id,
        "destination_resolution": resolution.method,
        "matched_label": resolution.matched_label,
        "capability": verdict,
        "reason_code": reason,
        "recommended_action": action,
        "coverage": flat,
        "coverage_detail": detail,
        "missing_categories": missing,
        "place_count": place_count,
        "provenance": {
            "source_kinds": source_kinds,
            "by_category": {
                key: value["source_kinds"] for key, value in detail.items()
            },
            # Stated because it is the rule this file obeys: normalisation reports the class a
            # fact arrived with and never raises it.
            "upgraded_by_normalisation": False,
        },
        "fingerprint": capability_fingerprint(resolution.canonical_destination_id),
        **fingerprint_parts(resolution.canonical_destination_id),
    }
    # R2: an observation exists only if something actually looked.  Absence is the honest way to
    # say "not measured"; a default `OK` would be a fabricated measurement.
    if provider_observations:
        body["provider_status"] = [
            item for item in provider_observations if item.get("status") in PROVIDER_STATUSES
        ]
    if resolution.resolver_status and not body.get("provider_status"):
        body["provider_status"] = [{"status": resolution.resolver_status, "stage": "resolving"}]
    return body
