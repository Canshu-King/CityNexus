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
import uuid
from collections.abc import Iterable
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
    "attractions": (
        "museum", "heritage", "landmark", "park", "gallery", "attraction", "attractions",
        "viewpoint", "tourist_attraction", "sights", "monument", "temple", "garden", "景点", "景区",
    ),
    "food": ("food", "foods", "restaurant", "restaurants", "cafe", "street_food", "fast_food",
             "bakery", "美食", "餐饮"),
    "nightlife": ("nightlife", "night_life", "bar", "pub", "club", "live_music", "酒馆", "夜生活"),
    "lodging": ("lodging", "hotel", "hostel", "apartment", "guest_house", "motel", "resort",
                "accommodation", "住宿", "酒店"),
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
# Two codes name this query and no winner may be guessed (arbiter `e4b7faa3` state AMBIGUOUS).
# It is a fact about the *request*, which is why it is a reason code and not a fourth `capability`.
REASON_DESTINATION_AMBIGUOUS = "DESTINATION_AMBIGUOUS"
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

# ---------------------------------------------------------------------------------------------
# ORD-0167 (arbiter `e4b7faa3`): what a destination *request* is allowed to become.
#
# Freeze sentence: *Unknown destination text may identify a request to resolve a destination; it
# does not identify a destination.*  Until this commit the build broke that sentence twice over:
# it wrote `pending:<the traveller's own words>` into `canonical_destination_id`, and it wrote the
# words *after* `_normalise` had eaten their punctuation.  So an identity column held a text
# derivative, and a fingerprint, an idempotency rule and a catalog join all quietly believed it.
#
# Nothing below is written into an identity column any more.  The prefix survives only so the
# migration can recognise rows the old build created.
LEGACY_PENDING_PREFIX = "pending:"

# What the resolver concluded about a request.  This is a third axis, deliberately separate from
# `capability` (what the destination *is*) and `provider_status` (what a provider said just now).
DESTINATION_STATES = ("RESOLVED", "AMBIGUOUS", "NO_MATCH", "RUNTIME_FAILURE")

# Fingerprint namespace for a request whose destination is still unnamed.  Naming the material in
# the key is the point: it is a fingerprint *of a request to resolve*, never a place identifier.
PENDING_REQUEST_NAMESPACE = "pending-request-v1"
# The request surface a pending fingerprint is scoped to.  Hydration jobs are destination-scoped
# by design (a journey-less tap and a journey-bearing tap must converge on one provider chain), so
# the scope is the surface, not the caller - the caller's id must not split one job in two.
PENDING_REQUEST_SCOPE = "catalog-hydration-v1"

# How much trust the stored label earns.  A legacy row whose only surviving text had already been
# normalised is marked as such rather than being presented as the traveller's exact words.
PENDING_LABEL_EXACT_RAW = "EXACT_RAW"
PENDING_LABEL_LEGACY_NORMALIZED = "LEGACY_NORMALIZED"
PENDING_LABEL_FIDELITIES = (PENDING_LABEL_EXACT_RAW, PENDING_LABEL_LEGACY_NORMALIZED)

# Suffixes a traveller types that do not change which place is meant.  They are tolerated when
# *matching* a query against names the catalog already holds, and are never applied to a stored
# label: matching may normalise, testimony may not.  Longest first, so 自治县 is not cut to 自治.
_ADMINISTRATIVE_SUFFIXES = (
    "特别行政区", "自治区", "自治州", "自治县", "地区", "林区", "省", "市", "区", "县",
)

_TRAVELER_FACING_LABELS = {
    "CNX-DEMO": ("demo", "演示", "模拟", "cnx-demo"),
}


@dataclass
class DestinationResolution:
    """What a query became, how sure we are about it, and what may be stored where.

    `canonical_destination_id` is the only identity field, and it is **null whenever this build
    cannot name a real place**.  The traveller's words belong in `pending_destination_label`,
    verbatim; the folded form used for matching belongs in `resolver_query_normalized`; and the
    opaque `destination_pending_key` is correlation material for one operation.  None of the last
    three is an identifier, and none may be joined on.
    """

    query: str
    canonical_destination_id: str | None
    city_code: str | None
    method: str
    state: str = "RESOLVED"
    matched_label: str | None = None
    reason_code: str = ""
    resolver_attempted: bool = False
    resolver_status: str | None = None
    candidates: list[dict[str, Any]] = field(default_factory=list)
    retryable: bool = False
    pending_destination_label: str | None = None
    resolver_query_normalized: str | None = None
    destination_pending_key: str | None = None
    pending_label_fidelity: str | None = None

    @property
    def resolved(self) -> bool:
        return self.canonical_destination_id is not None and self.city_code is not None


def _normalise(text: str) -> str:
    """Fold a spelling for *comparison*.  Never store this as what the user wrote."""

    return re.sub(r"[\s_\-·、,，.。]+", "", str(text or "")).strip().lower()


def _match_forms(text: str) -> set[str]:
    """The spellings a query may be matched under - and never the spellings it is stored under.

    `北京市` and `北京` are one place, and until now the resolver answered as if they were two:
    the suffixed form fell through to the unresolved branch, where its text became an identity.
    Stripping a closed list of administrative suffixes fixes the match without inventing
    anything - the winner still has to be a code the catalog or the vocabulary actually holds.
    """

    base = _normalise(text)
    forms = {base} if base else set()
    for suffix in _ADMINISTRATIVE_SUFFIXES:  # declared longest-first
        if base.endswith(suffix) and len(base) > len(suffix):
            forms.add(base[: -len(suffix)])
    return {form for form in forms if form}


def pending_correlation_key(operation_id: str) -> str:
    """An opaque token for one unresolved operation - correlation material, never identity.

    Derived from the *operation's* id, and deliberately not from the query text: a text-derived
    token would be a fingerprint wearing an identity's clothes, and it would collide two
    travellers' requests into each other's row.  Stability comes from the row, so a re-read of
    the same job names the same token, and a capability answer - which has no job yet - has none.
    The deterministic convergence a repeated request needs is the fingerprint
    (`capability_fingerprint`), a separate concept on purpose.
    """

    return f"pend-{operation_id}"


def _unresolved_identity(query: str) -> dict[str, Any]:
    """The non-identity columns an unresolved request is recorded with.

    No `destination_pending_key` here: that token names an operation, and an answer on a read has
    not opened one.  Inventing one per read would mint a per-response identifier for a request that
    has no work behind it - the same mistake, one column further along.
    """

    raw = str(query if query is not None else "")
    return {
        "pending_destination_label": raw,
        "resolver_query_normalized": _normalise(raw) or None,
        "destination_pending_key": None,
        "pending_label_fidelity": PENDING_LABEL_EXACT_RAW,
    }


def _resolved_identity(query: str) -> dict[str, Any]:
    """A resolved request keeps the raw words for audit and mints no pending token."""

    raw = str(query if query is not None else "")
    return {
        "pending_destination_label": raw,
        "resolver_query_normalized": _normalise(raw) or None,
        "destination_pending_key": None,
        "pending_label_fidelity": PENDING_LABEL_EXACT_RAW,
    }


def identity_fields(resolution: "DestinationResolution") -> dict[str, Any]:
    """The one place the five identity columns are assembled.

    The store and the wire must not drift into telling two stories about one request, so both
    read this - and `canonical_destination_id` is the only key in here that is ever an identity.
    """

    return {
        "canonical_destination_id": resolution.canonical_destination_id,
        "pending_destination_label": resolution.pending_destination_label,
        "resolver_query_normalized": resolution.resolver_query_normalized,
        "destination_pending_key": resolution.destination_pending_key,
        "pending_label_fidelity": resolution.pending_label_fidelity,
    }


def backfill_pending_identity_row(
    canonical_destination_id: str | None,
    request_json: str | None,
    fingerprint: str | None = None,
    operation_id: str | None = None,
) -> dict[str, Any]:
    """What one pre-ORD-0167 row becomes - decided where the vocabulary lives, not in the DDL.

    The rule the arbiter wrote (`e4b7faa3`, migration 1-5): keep the operation and its history,
    null the invented identity, and backfill the label from the **best available raw source**.
    For this product that source is the job's own `request_json.query`, which was always written
    verbatim; only when nothing but the already-folded `pending:` payload survives does the label
    come from there - and then it is marked `LEGACY_NORMALIZED`, because calling a folded string
    "what the user typed" would be the database forging a witness statement.

    The fingerprint is recomputed under `pending-request-v1` so a repeat of the same request still
    converges on *this* row instead of opening a second job beside it.  The old key is kept in
    `legacy_fingerprint` rather than dropped: an operation's history is not scratch space.
    """

    identity = str(canonical_destination_id or "")
    carried = request_json
    raw_from_request: str | None = None
    try:
        payload = json.loads(carried or "{}")
        if isinstance(payload, dict) and isinstance(payload.get("query"), str):
            raw_from_request = payload["query"]
    except (TypeError, ValueError):
        raw_from_request = None

    if not identity.startswith(LEGACY_PENDING_PREFIX):
        # A real identity stays exactly where it is; the raw words are attached for audit only.
        label = raw_from_request
        return {
            "canonical_destination_id": identity or None,
            "pending_destination_label": label,
            "resolver_query_normalized": _normalise(label or "") or None,
            "destination_pending_key": None,
            "pending_label_fidelity": PENDING_LABEL_EXACT_RAW if label is not None else None,
            "legacy_fingerprint": None,
            "fingerprint": fingerprint,
        }

    survivor = identity[len(LEGACY_PENDING_PREFIX) :]
    if survivor == "(blank)":
        survivor = ""
    if raw_from_request:
        label, fidelity = raw_from_request, PENDING_LABEL_EXACT_RAW
    else:
        label, fidelity = survivor, PENDING_LABEL_LEGACY_NORMALIZED
    normalised = _normalise(label) or (survivor or None)
    return {
        "canonical_destination_id": None,
        "pending_destination_label": label,
        "resolver_query_normalized": normalised,
        "destination_pending_key": pending_correlation_key(
            operation_id or uuid.uuid4().hex
        ),
        "pending_label_fidelity": fidelity,
        "legacy_fingerprint": fingerprint,
        "fingerprint": capability_fingerprint(None, resolver_query_normalized=normalised),
    }


def _alias_forms(aliases: Iterable[object]) -> set[str]:
    return {form for item in aliases if (form := _normalise(str(item or "")))}


def _catalog_holdings(session: Session) -> dict[str, int]:
    """Codes the catalog really holds rows for - the strongest statement this build can make."""

    return {
        str(code): int(count or 0)
        for code, count in session.execute(
            select(Place.city_code, func.count(Place.id)).group_by(Place.city_code)
        ).all()
    }


def _display_labels() -> dict[str, str]:
    """The traveller-facing names of the city codes, taken from the product's own vocabulary.

    Imported lazily because `main.py` owns that table today (single source, no copy).  It is *not*
    swallowed any more: until ORD-0167 a failure here returned `{}`, which quietly turned "one of
    my sources broke" into "this destination does not exist" - R1's forbidden laundering, in the
    one place no provider is involved and so nothing else would ever notice.
    """

    from app.main import _CITY_DISPLAY_NAMES  # single source, no copy

    return {f"CN-{code}": label for code, label in (_CITY_DISPLAY_NAMES or {}).items()}


def resolve_destination(session: Session, query: str) -> DestinationResolution:
    """Turn a query into a canonical destination using only sources already in this process.

    Four answers, and they are not interchangeable:

    * **RESOLVED** - exactly one code names this query, and that code is the identity.  A
      destination the *catalog* holds rows for wins over one the vocabulary merely names, because
      the catalog is what the plan will be built from.
    * **AMBIGUOUS** - two codes name it.  No winner is guessed; candidates stay in their own
      field and the identity is null.
    * **NO_MATCH** - nothing here can name it.  Identity null, the words kept verbatim, and a
      request fingerprint so a repeat of the same question finds the same job.
    * **RUNTIME_FAILURE** - reading a source itself failed.  Retryable, named, and *not* a
      structural verdict.

    What is absent from all four: text-derived identity.  No digest, no raw text, no prefix.
    """

    raw = str(query if query is not None else "")
    unresolved = _unresolved_identity(raw)
    forms = _match_forms(raw)
    if not forms:
        return DestinationResolution(
            query=raw,
            canonical_destination_id=None,
            city_code=None,
            method="none",
            state="NO_MATCH",
            reason_code=REASON_NO_CANONICAL_IDENTITY,
            **unresolved,
        )

    try:
        held = _catalog_holdings(session)
        labels = _display_labels()
    except Exception as exc:  # noqa: BLE001 - named below, never laundered into NO_MATCH
        return DestinationResolution(
            query=raw,
            canonical_destination_id=None,
            city_code=None,
            method="resolver_error",
            state="RUNTIME_FAILURE",
            reason_code=REASON_RESOLVER_UNAVAILABLE,
            retryable=True,
            candidates=[],
            **unresolved,
        )

    def matches(source: dict[str, str]) -> list[tuple[str, str]]:
        found: list[tuple[str, str]] = []
        for city_code, label in sorted(source.items()):
            aliases = {city_code, city_code.replace("CN-", ""), label}
            if city_code == "CNX-DEMO":
                for extra, extra_aliases in _TRAVELER_FACING_LABELS.items():
                    if extra == city_code:
                        aliases.update(extra_aliases)
            if forms & _alias_forms(aliases):
                found.append((city_code, label))
        return found

    # 1. codes the catalog holds rows for.
    hits = matches({code: labels.get(code, "") for code in held})
    source = "catalog"
    if not hits:
        # 2. a code the product can *name* but has no rows for: the identity is real, the catalog
        #    is empty.  This is the case a traveller can act on, so it is not "unavailable".
        hits = matches(labels)
        source = "vocabulary"

    distinct = sorted({code for code, _label in hits})
    if len(distinct) > 1:
        return DestinationResolution(
            query=raw,
            canonical_destination_id=None,
            city_code=None,
            method="ambiguous",
            state="AMBIGUOUS",
            reason_code=REASON_DESTINATION_AMBIGUOUS,
            candidates=[
                {
                    "city_code": code,
                    "label": labels.get(code) or code,
                    "source": source,
                    "places_held": int(held.get(code) or 0),
                }
                for code, _label in hits
            ],
            **unresolved,
        )
    if distinct:
        city_code = distinct[0]
        return DestinationResolution(
            query=raw,
            canonical_destination_id=city_code,
            city_code=city_code,
            method=source,
            state="RESOLVED",
            matched_label=labels.get(city_code) or city_code,
            **_resolved_identity(raw),
        )

    # 3. nothing in this process can name it - and the answer is a null identity plus the words,
    #    not a placeholder that a fingerprint or a join would go on believing.
    return DestinationResolution(
        query=raw,
        canonical_destination_id=None,
        city_code=None,
        method="unresolved",
        state="NO_MATCH",
        reason_code=REASON_NO_CANONICAL_IDENTITY,
        **unresolved,
    )


def _classify_source(provider_key: object, evidence: object) -> str:
    """One rule for one class of source, shared by places and services.

    The list is closed on purpose: an unrecognised provider is reported as the *weakest* thing it
    could honestly be (`OFFLINE_SNAPSHOT`), because inventing `REMOTE_PROVIDER` for a row nobody
    can account for is how a fixture ends up on screen as live data.
    """

    key = str(provider_key or "")
    mark = str(evidence or "")
    if key == "mock-city":
        return "GOLDEN_FIXTURE"
    if key in {"citynexus-demo", "mock-city-demo"}:
        return "SIMULATED"
    if mark in {"SEALED_REAL_REPLAY", "REPLAY"}:
        return "REPLAY"
    if mark == "OFFLINE_SNAPSHOT":
        return "OFFLINE_SNAPSHOT"
    if key in {"overpass", "photon", "amap", "valhalla"} or mark == "LIVE_PROVIDER":
        return "REMOTE_PROVIDER"
    return "OFFLINE_SNAPSHOT"


def _source_kind(place: Place) -> str:
    """Classify a row by where it came from - and never strengthen that class."""

    metadata = _loads(getattr(place, "metadata_json", None))
    evidence = metadata.get("provenance") if isinstance(metadata, dict) else ""
    return _classify_source(getattr(place, "provider_key", ""), evidence)


def _service_source_kind(service: CityService) -> str:
    """The same classification for a bookable service row: `FIXTURE` is not `OSM_FETCHED`."""

    metadata = _loads(getattr(service, "metadata_json", None))
    evidence = metadata.get("provenance") if isinstance(metadata, dict) else ""
    return _classify_source(getattr(service, "provider_key", ""), evidence)


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
    places_by_id = {str(place.id): place for place in places}
    # A bookable service is about a place, so its source can be named: the service row first,
    # and the linked place if the service itself carries no provider of its own.
    places_by_service = {
        str(service.id): places_by_id.get(str(service.place_id))
        for service in services
        if service.place_id
    }

    ages = [
        age
        for age in (_age_days(place.updated_at) for place in places)
        if age is not None
    ]
    stale = bool(places) and all(age > STALE_AFTER_DAYS for age in ages)

    for key in COVERAGE_KEYS:
        contributors: list[Place] = []
        if key == "mobility":
            covered, total = _mobility_evidence(session, city_code)
            ratio = (covered / total) if total else 0.0
            count = covered
            state = (
                READY
                if total and ratio >= MOBILITY_EXPLICIT_RATIO_READY and covered >= MIN_READY_CANDIDATES[key]
                else (PARTIAL if covered else MISSING)
            )
            # The legs are computed between catalogue places, so the places they connect are the
            # source of this axis - and a fixture leg is not an OSM leg.
            contributors = places
        elif key == "booking":
            bookable = [
                item for item in services if str(item.service_type) in BOOKABLE_SERVICE_TYPES
            ]
            count = len(bookable)
            state = _state_for(count, MIN_READY_CANDIDATES[key])
            contributors = [
                places_by_service.get(str(item.id))
                for item in bookable
                if places_by_service.get(str(item.id)) is not None
            ]
            if contributors:
                kinds = sorted({_service_source_kind(item) for item in bookable})
            else:
                contributors = []
                kinds = []
        else:
            rows = [row for cat in INTENT_CATEGORIES[key] for row in by_category.get(cat, [])]
            count = len(rows)
            state = _state_for(count, MIN_READY_CANDIDATES[key])
            contributors = rows
        if key != "booking":
            kinds = sorted({_source_kind(place) for place in contributors})
        detail[key] = {
            "state": state,
            "candidate_count": count,
            "min_ready": MIN_READY_CANDIDATES[key],
            "source_kinds": kinds,
            "stale": bool(stale),
        }
    return detail


def _state_for(count: int, minimum: int) -> str:
    if count <= 0:
        return MISSING
    if count >= minimum:
        return READY
    return PARTIAL


def unclassified_material(session: Session, city_code: str | None) -> dict[str, int]:
    """Categories the readiness policy does not name, and how many rows each holds.

    Without this, a destination whose rows carry an unexpected category string reads as "zero
    candidates" in every intent - the same shape as an empty catalog, which is how a capability
    answer can lie while every number in it is technically true.  The map is reported, not merged
    into `coverage`: the six keys are what the contract promises, and a seventh would break that.
    """

    if not city_code:
        return {}
    named = {category for bucket in INTENT_CATEGORIES.values() for category in bucket}
    counts: dict[str, int] = {}
    for category in session.scalars(
        select(Place.category).where(Place.city_code == city_code)
    ).all():
        key = str(category or "")
        if key and key not in named:
            counts[key] = counts.get(key, 0) + 1
    return counts


def fingerprint_material(
    canonical_destination_id: str | None,
    *,
    resolver_query_normalized: str | None = None,
    scope: str = PENDING_REQUEST_SCOPE,
) -> dict[str, Any]:
    """The exact bytes a fingerprint is made of, spelled out for both halves of the contract.

    * Destination named -> the four segments arbitration v0.2 froze: canonical destination plus
      the three policy versions.  Unchanged from before ORD-0167, on purpose: an existing job's
      key must not move under it because the resolver learned a new column.
    * Destination unnamed -> a **request** fingerprint, namespaced `pending-request-v1` and built
      from the *normalised* query plus the request scope and the same three versions.  It contains
      no canonical identity (there is none), no verbatim label (the punctuation is the traveller's,
      not the machine's) and no `destination_pending_key` (correlation, not convergence).
    """

    versions = {
        "catalog_schema_version": CATALOG_SCHEMA_VERSION,
        "readiness_policy_version": READINESS_POLICY_VERSION,
        "provider_policy_version": PROVIDER_POLICY_VERSION,
    }
    if canonical_destination_id:
        return {"canonical_destination_id": canonical_destination_id, **versions}
    return {
        "namespace": PENDING_REQUEST_NAMESPACE,
        "scope": scope,
        "canonical_destination_id": None,
        "resolver_query_normalized": _normalise(resolver_query_normalized or "") or None,
        **versions,
    }


def capability_fingerprint(
    canonical_destination_id: str | None,
    *,
    resolver_query_normalized: str | None = None,
    scope: str = PENDING_REQUEST_SCOPE,
) -> str:
    """The durable idempotency key: which destination, under which three versions.

    Anything that can change the answer is in here; anything that cannot (who asked, when, with
    which idempotency header) is not, so five concurrent requests for one county are one job -
    and five concurrent requests for one *unnamed* county are one job too, which is the whole
    reason the unnamed branch above is deterministic without ever being an identity.
    """

    material = fingerprint_material(
        canonical_destination_id, resolver_query_normalized=resolver_query_normalized, scope=scope
    )
    blob = json.dumps(material, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:32]


def fingerprint_parts(
    canonical_destination_id: str | None,
    *,
    resolver_query_normalized: str | None = None,
    scope: str = PENDING_REQUEST_SCOPE,
) -> dict[str, Any]:
    """The segments spelled out - a caller must be able to ask *why* keys matched."""

    return fingerprint_material(
        canonical_destination_id, resolver_query_normalized=resolver_query_normalized, scope=scope
    )


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

    if resolution.state == "RUNTIME_FAILURE":
        # R1 applied to our own sources: a lookup that broke is a *runtime* fact, so the answer
        # stays retryable.  The bug this replaces swallowed the exception into `{}` and let the
        # branch below report "this destination cannot be planned" about a database hiccup.
        verdict, reason, action = "HYDRATABLE", REASON_RESOLVER_UNAVAILABLE, ACTION_START_HYDRATION
    elif resolution.state == "AMBIGUOUS":
        # Unusable *as typed*, which is not the same claim as "unusable" about either candidate:
        # the reason names ambiguity and `candidates` carries what to choose between.
        verdict, reason, action = (
            "UNAVAILABLE",
            REASON_DESTINATION_AMBIGUOUS,
            ACTION_CHOOSE_ANOTHER_DESTINATION,
        )
    elif not resolution.resolved:
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
        **identity_fields(resolution),
        "destination_state": resolution.state,
        "destination_resolution": resolution.method,
        "retryable": resolution.retryable,
        "candidates": resolution.candidates,
        "matched_label": resolution.matched_label,
        "capability": verdict,
        "reason_code": reason,
        "recommended_action": action,
        "coverage": flat,
        "coverage_detail": detail,
        "missing_categories": missing,
        # Named rather than swallowed: if a category exists but no intent names it, a reader must
        # be able to see that we have material we failed to classify, not infer an empty catalog.
        "unclassified_categories": unclassified_material(session, resolution.city_code),
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
        "fingerprint": capability_fingerprint(
            resolution.canonical_destination_id,
            resolver_query_normalized=resolution.resolver_query_normalized,
        ),
        **fingerprint_parts(
            resolution.canonical_destination_id,
            resolver_query_normalized=resolution.resolver_query_normalized,
        ),
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
