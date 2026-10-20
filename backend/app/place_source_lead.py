"""Read a map-point source lead back into this product's place identity -- or refuse.

A `candidate_id` can be a minted `Place.id` (`real-place-<hex>`), a provider object id
(`photon:node/123`) or a discovery candidate (`rpc-<hex>`); only the first is a media path segment.
Making the others "work" by searching the visible name would attach one city's photograph to another
city's same-named landmark, silently -- so resolution runs here against stored identity, and every
shape that cannot name a place comes back as a named refusal.

Two rules callers can rely on:
  * no text matching -- not names, not descriptions, not URLs; identity columns only;
  * with a journey supplied, the answer is bounded by that journey, so the read cannot be used to
    discover which places somebody else's trip holds.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Activity, JourneyCheckin, Place, PlanVersion, RealPlaceCandidate

#: Lead shapes, decided from the stored id columns' own formals -- not from what the caller says.
SHAPE_PLACE_ID = "PLACE_ID"
SHAPE_CANDIDATE_ID = "CANDIDATE_ID"
SHAPE_PROVIDER_OBJECT_ID = "PROVIDER_OBJECT_ID"
SHAPE_NOT_A_LEAD = "NOT_A_LEAD"

#: Reason codes the client renders. RESOLVED travels with a place_id; the rest never do.
REASON_RESOLVED = "LEAD_RESOLVED"
REASON_NOT_A_LEAD = "LEAD_NOT_A_PLACE_LEAD"
REASON_AMBIGUOUS = "LEAD_AMBIGUOUS"
REASON_NOT_MATERIALIZED = "CANDIDATE_NOT_MATERIALIZED"
REASON_NOT_IN_JOURNEY = "PLACE_NOT_IN_JOURNEY"
#: The lead is well-shaped and this store simply has no row carrying that identity. Kept apart from
#: `PLACE_NOT_IN_JOURNEY` because the two send the caller to different doors: one says "attach a place
#: this trip already holds", the other says "no such place row exists yet -- go materialize it".
REASON_NO_ROW_FOR_LEAD = "LEAD_HAS_NO_PLACE_ROW"

STATUS_RESOLVED = "RESOLVED"
STATUS_UNRESOLVED = "UNRESOLVED"

_MINTED_CANDIDATE = re.compile(r"^rpc-[0-9a-f]{24}$")
_PROVIDER_OBJECT = re.compile(r"^[A-Za-z][A-Za-z0-9_]{1,40}:[A-Za-z0-9_.:/+-]{1,150}$")
#: An id-shaped lead: the characters this product's own primary keys are minted from. Text with a
#: space, a slash or a non-ascii letter in it is a name or a url, and those have no column to look up.
_ID_LIKE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{2,159}$")


def minted_place_id(provider_key: str, external_id: str) -> str:
    """The id discovery mints for a provider object, restated so the mapping is checkable.

    `real_city` writes ``real-place-<sha1(provider_key|external_id)[:24]>``. Repeating the formula here
    is not a second definition -- nothing is written from this function -- it is the assertion the tests
    run: the lead a map point carries and the row a media read needs come out of the same two columns,
    so the pairing cannot drift when a name is edited.
    """
    digest = hashlib.sha1(f"{provider_key}|{external_id}".encode()).hexdigest()
    return f"real-place-{digest[:24]}"


def classify_lead(lead: str) -> str:
    """Which identity column could ever hold this string? Free text and URLs answer NONE.

    A lead that only *looks* like a place -- the landmark's name, a page url -- has no column to be
    looked up in, and inventing a name search is how a same-named landmark in another city gets the
    wrong photograph. Refusing is the correct answer, so the caller gets a reason instead of a guess.
    """
    raw = (lead or "").strip()
    if "://" in raw:
        # A url is a page about a place, not a place this product stores. It never gets looked up.
        return SHAPE_NOT_A_LEAD
    if _MINTED_CANDIDATE.match(raw):
        return SHAPE_CANDIDATE_ID
    if _PROVIDER_OBJECT.match(raw):
        return SHAPE_PROVIDER_OBJECT_ID
    if _ID_LIKE.match(raw):
        return SHAPE_PLACE_ID
    return SHAPE_NOT_A_LEAD


def place_is_in_journey(session: Session, journey_id: str, place_id: str) -> bool:
    """Is this place reachable from THIS journey -- as a scheduled stop or as a stamp on one?

    The catalogue is global: a `Place` row says nothing about whose journey it belongs to, so "the row
    exists" cannot be the scope test. Both links are read here rather than inferred from what the
    client claims to be looking at.
    """
    scheduled = session.scalars(
        select(Activity.id)
        .join(PlanVersion, Activity.plan_version_id == PlanVersion.id)
        .where(PlanVersion.journey_id == journey_id, Activity.place_id == place_id)
        .limit(1)
    ).first()
    if scheduled is not None:
        return True
    stamped = session.scalars(
        select(JourneyCheckin.id).where(
            JourneyCheckin.journey_id == journey_id,
            JourneyCheckin.place_id == place_id,
        ).limit(1)
    ).first()
    return stamped is not None


@dataclass(frozen=True)
class PlaceLead:
    lead: str
    shape: str
    status: str
    reason_code: str
    place_id: str | None = None
    provider_key: str | None = None
    external_id: str | None = None
    city_code: str | None = None
    name: str | None = None
    matched_by: str | None = None
    region_conflict: bool = False
    note: str = ""

    @property
    def resolved(self) -> bool:
        return self.status == STATUS_RESOLVED

    def as_payload(self) -> dict[str, Any]:
        return {
            "lead": self.lead,
            "lead_shape": self.shape,
            "status": self.status,
            "reason_code": self.reason_code,
            "place_id": self.place_id,
            "provider_key": self.provider_key,
            "provider_object_id": self.external_id,
            "region": self.city_code,
            "place_name": self.name,
            "matched_by": self.matched_by,
            "region_conflict": self.region_conflict,
        }


def _unresolved(lead: str, shape: str, reason: str, note: str) -> PlaceLead:
    return PlaceLead(lead=lead, shape=shape, status=STATUS_UNRESOLVED, reason_code=reason, note=note)


def _from_row(row: Place, *, matched_by: str, lead: str, shape: str,
              candidate_region: str | None = None) -> PlaceLead:
    return PlaceLead(
        lead=lead,
        shape=shape,
        status=STATUS_RESOLVED,
        reason_code=REASON_RESOLVED,
        place_id=row.id,
        provider_key=row.provider_key,
        external_id=row.external_id,
        city_code=row.city_code,
        name=row.name,
        matched_by=matched_by,
        # A candidate row and its materialised place should carry one region. When they do not, the
        # lead is not trustworthy for imagery even though a row was found: say so rather than pick.
        region_conflict=bool(candidate_region and candidate_region != row.city_code),
    )


def resolve_place_lead(session: Session, lead: str, *,
                       journey_id: str | None = None) -> PlaceLead:
    """Map one source lead onto at most one Place, using stored identity columns only.

    Resolution arms, in the order they are trusted: a ``RealPlaceCandidate`` row joined on its own
    (provider_key, external_id), then ``Place.external_id`` equality, then the (provider_key, object)
    pair when the lead carries a provider prefix, then the minted ``Place.id``. A lead's shape picks
    the vocabulary, not the column -- an id-shaped string can be a row's ``external_id`` -- so every
    non-candidate shape goes through the same three equality arms. Scope runs last and never widens
    the set: with a journey supplied, only places that journey holds can be answered about.
    """
    raw = (lead or "").strip()
    shape = classify_lead(raw)
    if shape == SHAPE_NOT_A_LEAD:
        return _unresolved(raw, shape, REASON_NOT_A_LEAD,
                           "this product stores places by id and by provider object id, not by text")

    if shape == SHAPE_CANDIDATE_ID:
        candidate = session.get(RealPlaceCandidate, raw)
        if candidate is None:
            return _unresolved(raw, shape, REASON_NOT_A_LEAD, "no candidate row carries this id")
        candidate_journey = str(candidate.journey_id or "")
        if journey_id and candidate_journey not in ("", str(journey_id)):
            # Another trip's discovery evidence: it is not this caller's to resolve.
            return _unresolved(raw, shape, REASON_NOT_IN_JOURNEY,
                               "the candidate belongs to another journey")
        row = session.scalar(
            select(Place).where(
                Place.provider_key == candidate.provider_key,
                Place.external_id == candidate.external_id,
            )
        )
        if row is None:
            return _unresolved(raw, shape, REASON_NOT_MATERIALIZED,
                               "the candidate has no place row yet")
        if journey_id and not place_is_in_journey(session, journey_id, row.id):
            return _unresolved(raw, shape, REASON_NOT_IN_JOURNEY,
                               "the journey does not hold this place")
        return _from_row(row, matched_by="candidate_identity", lead=raw, shape=shape,
                         candidate_region=candidate.city_code)

    #: The three identity columns a lead may name, tried in this order and never by text. Two real
    #: shapes reach this one path, because a lead's shape does not tell which column holds it:
    #: `real_city._external_id()` stores the full `provider:object` in `Place.external_id` while the
    #: Photon writer keeps the provider in `Place.provider_key` and the object part alone in
    #: `external_id`, and a fixture writer (`mock-city`) stores short codes like `P001` in
    #: `external_id` while its primary key is a different string again. So one lead is tried against
    #: `external_id` whole, against the (provider_key, object) pair when it carries a prefix, and
    #: against the primary key -- three equality lookups on stored identity columns, no name, no
    #: search, no url.
    rows: dict[str, Place] = {}
    matched_by: dict[str, str] = {}

    def _collect(arm_rows: Any, word: str) -> None:
        for row in arm_rows:
            rows.setdefault(row.id, row)
            matched_by.setdefault(row.id, word)

    _collect(session.scalars(select(Place).where(Place.external_id == raw)), "provider_object_id")
    provider_word, _, object_part = raw.partition(":")
    if object_part:
        _collect(session.scalars(select(Place).where(
            Place.provider_key == provider_word, Place.external_id == object_part)),
            "provider_key_and_object_id")
    pk_row = session.get(Place, raw)
    if pk_row is not None:
        # The same string can also be the row's own primary key (seeded and legacy ids carry a colon).
        _collect([pk_row], "place_id")
    candidates = list(rows.values())
    if not candidates:
        # Nothing in this store carries that identity. Saying `PLACE_NOT_IN_JOURNEY` here -- which is
        # what a journey-scoped call used to get -- blamed the trip for a missing row and sent callers
        # to attach a place that does not exist. The absence is the answer; scope is only reported
        # when a row actually matched.
        return _unresolved(raw, shape, REASON_NO_ROW_FOR_LEAD,
                           "no place row carries this identity")
    if journey_id:
        candidates = [row for row in candidates if place_is_in_journey(session, journey_id, row.id)]
        if not candidates:
            return _unresolved(raw, shape, REASON_NOT_IN_JOURNEY,
                               "the journey does not hold this place")
    if len(candidates) > 1:
        # Two rows claim one provider object id. Choosing by name or by "the first one" is exactly the
        # silent cross-city pairing, so the answer is a refusal that names how many collided -- and
        # which columns matched is withheld, because picking one of them is what is being refused.
        return _unresolved(raw, shape, REASON_AMBIGUOUS,
                           f"{len(candidates)} place rows carry this provider object id")
    row = candidates[0]
    return _from_row(row, matched_by=matched_by[row.id], lead=raw, shape=shape)
