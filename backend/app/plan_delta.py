"""What one plan version changes against another: places on the map, money, minutes, and evidence.

The V3 order's third item asks the Guardian surface to show a candidate as a *difference* -- 地图/预算
增量 -- instead of a wall of statuses, and its acceptance chain insists that a real miss stays a named
miss. This read answers that difference for any two versions of one journey the caller holds a seat on.

Three limits, each of which is the point:

* **The two versions are the only inputs, and both must be rows.** Nothing here accepts a place name,
  a URL or a provider id: the slots are `Activity` rows of a `PlanVersion` on this journey, so a delta
  read cannot become a way to enumerate places or spend quota, and it cannot price something this
  server does not hold.
* **Every per-slot judgement is the fact door's.** Identity (canonical id plus `provider_key:external_id`),
  coordinate state, opening window, verified cost and the media door's path come from
  `app.departure_facts._slot`, the same function `GET .../departure/facts` answers with. A delta that
  re-decided any of those would be a second answer waiting to disagree, so a test runs both doors over
  the same rows and compares them.
* **An unpriced slot is counted, never priced.** `budget_delta` sums the numbers the plan rows carry;
  `verified_cost` only ever adds what `app.services._place_verified_cost` says this place states, and
  `unpriced_slots` names how many the difference cannot cover. Two versions in different currencies
  produce no delta at all rather than a subtracted pair.

Matching is by `sequence_no` plus place identity, which is how `app.collective_mediation` already
compares two plans when it decides what a candidate actually changes; a slot that moved to a different
place is `moved`, not an add plus a remove, because the screen needs the pair to draw an arrow.

The frozen-mobility-evidence state of both versions rides along, read through
`app.departure_read.frozen_evidence_of`: this is where a traveller learns why a candidate the plan door
will not accept still says what it is missing, in the door's own words.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Activity, Place, PlanVersion
from app.db.session import get_session
from app.departure_facts import (
    REASON_PLAN_NOT_IN_JOURNEY,
    _slot,
)
from app.departure_read import _refuse, _signed_journey, frozen_evidence_of
from app.services import _place_verified_cost

router = APIRouter()

DELTA_PATH = "/api/v1/journeys/{journey_id}/plans/delta"

REASON_FROM_REQUIRED = "FROM_PLAN_VERSION_ID_REQUIRED"
REASON_TO_REQUIRED = "TO_PLAN_VERSION_ID_REQUIRED"
REASON_SAME_VERSION = "DELTA_NEEDS_TWO_DIFFERENT_VERSIONS"

#: A slot is kept or it is not; `moved`/`added`/`removed` are already the names of the sets they sit in,
#: so the only extra word this door states is a kept slot that has no place on either side.
KIND_KEPT = "KEPT"
KIND_UNPLACED = "KEPT_WITHOUT_PLACE"


def _activities(session: Session, plan_id: str) -> dict[int, Activity]:
    return {
        int(row.sequence_no): row
        for row in session.scalars(
            select(Activity)
            .where(Activity.plan_version_id == plan_id)
            .order_by(Activity.sequence_no)
        ).all()
    }


def _stamp(activity: Activity | None) -> dict[str, Any]:
    """A slot reduced to what the map and the ledger need, with no judgement added here."""
    if activity is None:
        return {}
    return {
        "sequence_no": activity.sequence_no,
        "place_id": activity.place_id,
        "start_at": activity.start_at,
        "end_at": activity.end_at,
        "estimated_cost_minor": activity.estimated_cost_minor,
        "currency": activity.currency,
        "status": activity.status,
    }


def _slot_minutes(session: Session, plan_id: str) -> tuple[int, int]:
    """(wall-clock minutes, slots whose times this door could not read) for one version.

    `activities.start_at` / `end_at` are free-text columns (backend/app/db/models.py:575), so a row
    can carry a time this module cannot parse. Those slots are counted and named in the answer rather
    than skipped -- a duration quietly shortened by one row it did not understand would be a number
    the screen cannot question.
    """
    total = 0
    unreadable = 0
    for row in session.scalars(select(Activity).where(Activity.plan_version_id == plan_id)).all():
        try:
            total += max(
                0,
                int((datetime.fromisoformat(str(row.end_at))
                     - datetime.fromisoformat(str(row.start_at))).total_seconds() // 60),
            )
        except ValueError:
            unreadable += 1
    return total, unreadable


def _currency_of(slots: list[Activity]) -> str | None:
    """The one currency a comparison can be moneyed in, or None when the two halves disagree."""
    currencies = sorted({str(row.currency) for row in slots if row.currency})
    if len(currencies) != 1:
        return None
    return currencies[0]


@router.get(DELTA_PATH)
def journey_plan_delta(
    response: Response,
    request: Request,
    journey_id: UUID,
    from_plan_version_id: str | None = Query(default=None),
    to_plan_version_id: str | None = Query(default=None),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    """The map, budget, duration and evidence difference between two versions of this journey."""
    journey, seat = _signed_journey(request, session, journey_id)
    if not from_plan_version_id:
        raise _refuse(422, "a delta needs the version to compare from", REASON_FROM_REQUIRED,
                      {"journey_id": journey.id, "missing": ["from_plan_version_id"]})
    if not to_plan_version_id:
        raise _refuse(422, "a delta needs the version to compare to", REASON_TO_REQUIRED,
                      {"journey_id": journey.id, "missing": ["to_plan_version_id"]})
    if str(from_plan_version_id) == str(to_plan_version_id):
        raise _refuse(422, "a delta of a version against itself says nothing",
                      REASON_SAME_VERSION, {"plan_version_id": str(from_plan_version_id)})

    plans: dict[str, PlanVersion] = {}
    for label, wanted in (("from", from_plan_version_id), ("to", to_plan_version_id)):
        plan = session.get(PlanVersion, str(wanted))
        if plan is None or plan.journey_id != journey.id:
            # Answered before a single activity row is read, so a foreign id cannot probe a plan.
            raise _refuse(
                404,
                f"PlanVersion {wanted} was not found on this journey",
                REASON_PLAN_NOT_IN_JOURNEY,
                {"journey_id": journey.id, "which": label, "plan_version_id": str(wanted)},
            )
        plans[label] = plan
    answer = delta_of(session, journey, plans["from"], plans["to"])
    answer["asked_by_traveler_id"] = seat["traveler_id"]
    # The difference itself carries no intent; whose door to press next belongs to the door being read.
    answer["next_actions"] = [
        "select this version with POST /api/v1/journeys/" + journey.id + "/departure/commit",
    ]
    response.headers["Cache-Control"] = "private, no-store"
    response.headers["Vary"] = "Authorization, X-CityNexus-Traveler-Token"
    return answer


def delta_of(session: Session, journey: Any, base: PlanVersion,
             candidate: PlanVersion) -> dict[str, Any]:
    """The difference itself, with no request in it.

    Two doors need exactly this: the read door answers with it, and the submission door has to store
    what a candidate changes in `replan_proposals.diff_json`, which the Guardian later reads. A second
    writer of that arithmetic would be a second answer waiting to disagree.
    """
    before = _activities(session, base.id)
    after = _activities(session, candidate.id)

    kept: list[dict[str, Any]] = []
    moved: list[dict[str, Any]] = []
    added: list[dict[str, Any]] = []
    removed: list[dict[str, Any]] = []
    unplaced = 0
    for sequence in sorted(set(before) | set(after)):
        old, new = before.get(sequence), after.get(sequence)
        if old is not None and new is None:
            removed.append({"sequence_no": sequence, "from": _stamp(old),
                            "from_slot": _slot(session, journey, old)})
            continue
        if old is None and new is not None:
            added.append({"sequence_no": sequence, "to": _stamp(new),
                          "to_slot": _slot(session, journey, new)})
            continue
        if str(old.place_id or "") != str(new.place_id or ""):
            if not old.place_id or not new.place_id:
                unplaced += 1
                kept.append({"sequence_no": sequence, "kind": KIND_UNPLACED,
                             "from": _stamp(old), "to": _stamp(new)})
                continue
            moved.append({
                "sequence_no": sequence,
                "from": _stamp(old), "to": _stamp(new),
                "from_slot": _slot(session, journey, old),
                "to_slot": _slot(session, journey, new),
            })
            continue
        kept.append({"sequence_no": sequence, "kind": KIND_KEPT,
                     "from": _stamp(old), "to": _stamp(new)})

    #: A map has to be drawn in the same order every time it is read, so the two point lists are
    #: ordered by the slot's `sequence_no` -- the natural walk of a day -- and never by which set
    #: happened to contribute a place. A moved slot therefore lands between its neighbours on both
    #: sides, which is what lets a screen draw one arrow along the route instead of appending it to
    #: the end of whatever list was built first.
    def views_with_sequence(pairs: list[tuple[int, dict[str, Any]]]) -> list[dict[str, Any]]:
        return [view for _, view in sorted(pairs, key=lambda pair: pair[0])]

    added_views = views_with_sequence(
        [(entry["sequence_no"], entry["to_slot"]) for entry in added]
        + [(entry["sequence_no"], entry["to_slot"]) for entry in moved]
    )
    removed_views = views_with_sequence(
        [(entry["sequence_no"], entry["from_slot"]) for entry in removed]
        + [(entry["sequence_no"], entry["from_slot"]) for entry in moved]
    )

    def points(views: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [
            {
                "sequence_no": view["sequence_no"],
                "place_id": view["identity"]["canonical_id"],
                "source_identity": view["identity"]["source_identity"],
                # The label is the slot's own title, which is what a plan row carries for a place;
                # this door does not go fetch a name it was not given.
                "label": view["title"],
                "coordinate": view["coordinate"],
                "media_door": view.get("media_door"),
            }
            for view in views
        ]

    #: Counted by the state word the fact door actually answered with, so a state this module did not
    #: imagine appears under its own name instead of being folded into "unavailable".
    seen: dict[str, int] = {}
    for view in added_views + removed_views:
        state = str(view["coordinate"]["state"])
        seen[state] = seen.get(state, 0) + 1
    coordinate_states = dict(sorted(seen.items()))

    base_minutes, base_unreadable = _slot_minutes(session, base.id)
    candidate_minutes, candidate_unreadable = _slot_minutes(session, candidate.id)
    before_costs = list(before.values())
    after_costs = list(after.values())
    before_total = sum(row.estimated_cost_minor for row in before_costs)
    after_total = sum(row.estimated_cost_minor for row in after_costs)
    currency = _currency_of(before_costs + after_costs)
    verified_before, verified_after, unpriced = 0, 0, 0
    for row in after_costs:
        place = _place_of(session, row)
        value = _place_verified_cost(place) if place is not None else None
        if value is None:
            unpriced += 1
        else:
            verified_after += value
    for row in before_costs:
        place = _place_of(session, row)
        value = _place_verified_cost(place) if place is not None else None
        if value is not None:
            verified_before += value

    answer = {
        "journey_id": journey.id,
        "from_plan_version_id": base.id,
        "to_plan_version_id": candidate.id,
        "from_status": base.status,
        "to_status": candidate.status,
        "from_version_no": base.version_no,
        "to_version_no": candidate.version_no,
        "counts": {
            "from_slots": len(before),
            "to_slots": len(after),
            "kept": len(kept),
            "moved": len(moved),
            "added": len(added),
            "removed": len(removed),
        },
        "sets": {
            "kept": kept,
            "moved": moved,
            "added": added,
            "removed": removed,
        },
        "map_delta": {
            "points_added": points(added_views),
            "points_removed": points(removed_views),
            "coordinate_states": coordinate_states,
        },
        "budget_delta": {
            "from_total_minor": before_total,
            "to_total_minor": after_total,
            "delta_minor": (after_total - before_total) if currency else None,
            "currency": currency,
            "mixed_or_missing_currency": currency is None,
            "read_from": "activities.estimated_cost_minor",
        },
        "verified_cost": {
            "from_total_minor": verified_before,
            "to_total_minor": verified_after,
            "delta_minor": verified_after - verified_before,
            "priced_slots": len(after_costs) - unpriced,
            "unpriced_slots": unpriced,
            "read_from": "app.services._place_verified_cost",
        },
        "duration_delta": {
            "from_minutes": base_minutes,
            "to_minutes": candidate_minutes,
            "delta_min": candidate_minutes - base_minutes,
            # A version whose rows carry times this door cannot read says so; the number above is the
            # sum of the rows it could read, not a claim that the whole day parsed.
            "from_unreadable_slots": base_unreadable,
            "to_unreadable_slots": candidate_unreadable,
            "read_from": "activities.start_at / end_at",
        },
        "evidence": {
            "from": frozen_evidence_of(base),
            "to": frozen_evidence_of(candidate),
            "read_from": "app.departure_read.frozen_evidence_of",
        },
    }
    return answer


def _place_of(session: Session, activity: Activity):
    """The place row a slot points at, or None -- a slot with no location prices nothing."""
    if not activity.place_id:
        return None
    return session.get(Place, str(activity.place_id))
