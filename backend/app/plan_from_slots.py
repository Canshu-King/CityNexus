"""Turn the slots a caller already holds into a CANDIDATE plan, keeping their dates and order.

This is the write half of the same bridge the departure doors read. The shipped generator
(`POST /api/v1/journeys/{journey_id}/plans/generate`) re-schedules: it takes a list of canonical
place ids and produces its own times, so a draft whose days and slots were already chosen cannot be
turned into a plan with it without lying about what was preserved. This door does the other thing:
it writes the slots it is given, in the order and at the times given, as a `CANDIDATE`.

What it refuses, and why each refusal is the point:

* **a source id** -- `amap:B00140WBI1` names a place in a provider's namespace, not a row in this
  store. Mapping that string to a canonical Place is a lookup this server owns; accepting it here
  would make this door the place that silently pairs a photo or a price with a name, so it is refused
  by name and the caller is pointed at the identity read that gives the canonical id.
* **a described place** -- `title`, `name`, `url`, `query`, `address` and provider payloads are not
  body fields. `activities.title` is NOT NULL, and the only honest writer of it here is the `Place`
  row this slot points at.
* **a place that is not in this journey's city** -- a same-named landmark two cities away would pass
  a naive lookup; the row's `city_code` is compared against the journey's, and a mismatch is a
  refusal rather than a plan.
* **a revision it cannot check** -- `expected_revision` is the journey's current
  `active_plan_version_id`. A caller whose draft was built on a plan that has since moved gets
  `BASE_PLAN_MOVED`: the candidate it would create is not the one the user looked at. The field must
  be *said*; what it says then decides the answer. A journey that has no plan version yet is not a
  caller error -- naming `null` is how a first draft states that, and it is accepted while the
  journey still has none. Naming `null` against a journey that does have one is `BASE_PLAN_MOVED`,
  not an acceptance, and omitting the field is `EXPECTED_REVISION_REQUIRED`.

What it never does: it does not select, start or activate anything -- the row it returns is
`CANDIDATE` and stays that way until the traveller picks it through
`POST /api/v1/journeys/{journey_id}/departure/commit`; it does not ask a provider (no client is
reachable from this module, asserted from the module's own syntax tree), so it cannot spend quota or
become a place-enumeration door; and it does not invent a cost: `activities.estimated_cost_minor` is
`NOT NULL DEFAULT 0` in the shipped DDL, so a slot that declares nothing stores the zero the column
demands and the answer says `cost_declared` false with the gap named.

The per-slot facts in the answer come from the same two predicates the feasibility gate and
`GET .../departure/facts` use (`app.services._place_window`, `_place_verified_cost`), so a slot cannot
be reported as "has hours" to this door and "no hours" to that one.

No migration: `plan_versions`, `activities`, `audit_logs` and `idempotency_keys` already exist.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Header, Request, Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.commerce.idempotency import canonical_request_signature
from app.core.audit import record_audit
from app.db.models import Activity, IdempotencyKey, Place, PlanVersion
from app.db.session import get_session
from app.departure_read import _refuse, _signed_journey
from app.place_media_routes import IDENTITY_PATH
from app.services import _place_verified_cost, _place_window

router = APIRouter()

FROM_SLOTS_PATH = "/api/v1/journeys/{journey_id}/plans/from-slots"
FROM_SLOTS_OPERATION = "plan.from_slots"
FROM_SLOTS_ACTION = "plan.candidate_created_from_slots"

PLAN_STATUS_CANDIDATE = "CANDIDATE"
PLAN_SOURCE_MANUAL = "MANUAL"
ACTIVITY_STATUS_PLANNED = "PLANNED"

#: Body this door reads. `label` is a name for the new version, not a description of a place.
BODY_FIELDS = frozenset({"slots", "planning_mode", "expected_revision"})
SLOT_FIELDS = frozenset({"place_id", "start_at", "end_at", "estimated_cost_minor", "currency",
                         "travel_from_prev_min"})
#: Fields that would let a caller describe a place to the server instead of naming one it holds.
DESCRIPTIVE_FIELDS = frozenset({"title", "name", "url", "query", "address", "provider_key",
                               "external_id", "source_id", "photo", "image", "tags"})
#: Words that name a provider's namespace rather than a row in this store.
SOURCE_ID_MARKER = ":"

PLANNING_MODES = ("balanced", "budget", "explore", "strict_schedule")

REASON_BODY = "FROM_SLOTS_BODY_TAKES_ONLY_THE_SERVERS_OWN_FIELDS"
REASON_DELEGATED_SHAPE = "SLOT_NAMES_A_PROVIDER_ID_NOT_A_CANONICAL_PLACE"
REASON_SLOT_FIELDS = "SLOT_CARRIES_ONLY_SERVER_OWNED_FIELDS"
REASON_SLOT_COUNT = "FROM_SLOTS_NEEDS_AT_LEAST_ONE_SLOT"
REASON_PLACE_NOT_FOUND = "PLACE_ROW_NOT_FOUND"
REASON_PLACE_OTHER_CITY = "PLACE_NOT_IN_THIS_JOURNEYS_CITY"
REASON_TIMES = "SLOT_TIMES_UNORDERED"
REASON_TIMESTAMP = "SLOT_TIMESTAMP_NOT_PARSEABLE"
REASON_REVISION = "BASE_PLAN_MOVED"
REASON_REVISION_MISSING = "EXPECTED_REVISION_REQUIRED"
REASON_KEY_REQUIRED = "IDEMPOTENCY_KEY_REQUIRED"
REASON_KEY_CONFLICT = "IDEMPOTENCY_KEY_REUSE_CONFLICT"
REASON_VERSION_COLLISION = "PLAN_VERSION_NUMBER_UNAVAILABLE"

GAP_HOURS = "OPENING_HOURS_NOT_RECORDED"
GAP_COST = "NO_COST_DECLARED_FOR_THIS_SLOT"
GAP_COORDINATE = "PLACE_HAS_NO_POINT"

NEXT_ACTION_FACTS = "read GET /api/v1/journeys/{journey_id}/departure/facts"
NEXT_ACTION_COMMIT = "select POST /api/v1/journeys/{journey_id}/departure/commit"


#: Characters that would change what a query parameter means if this door echoed the lead into one.
LEAD_QUERY_UNSAFE = "&#+%? "


def identity_pointer(journey_id: str, lead: Any) -> str:
    """The identity read this door points at, spelled the way that router actually serves it.

    The path is `app.place_media_routes.IDENTITY_PATH` -- the constant the GET itself is registered
    with -- because a pointer copied into a second file is a pointer that can drift: this one named
    `/places/{place_id}/identity`, a path no route serves, and it stayed green under a spec that only
    looked for the word `identity`, so a caller who pressed it got a 404. This module imports that
    router's path constant and nothing else from it, and no network client is reachable from here
    (the shipped AST arm keeps that true).

    The refused lead goes in verbatim when it can -- a colon is legal inside a query value, which is
    what every provider id this product holds uses -- and is left out when it cannot, because a
    pointer that silently means something else is the same bug wearing a different hat. The value is
    always in the refusal's own `received`/slot either way.
    """
    head = "map the provider id first with GET " + IDENTITY_PATH.format(journey_id=journey_id)
    text = str(lead)
    if any(character in text for character in LEAD_QUERY_UNSAFE):
        return head + "?lead= (name the refused id from details; this door will not put it in a url)"
    return head + "?lead=" + text


def _parse(moment: str, field: str, sequence_no: int) -> datetime:
    try:
        parsed = datetime.fromisoformat(str(moment))
    except (TypeError, ValueError) as refused:
        raise _refuse(
            422,
            "a slot needs a timestamp this server can read",
            REASON_TIMESTAMP,
            {"slot": sequence_no, "field": field, "received": str(moment)[:40],
             "detail": str(refused)[:80]},
        ) from refused
    return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=timezone.utc)


def _refused_slot_fields(fields: dict[str, Any], allowed: frozenset[str], *, slot: int | None,
                         code: str, message: str) -> None:
    unexpected = sorted(str(name) for name in fields if name not in allowed)
    if unexpected:
        raise _refuse(
            422, message, code,
            {"slot": slot, "accepted_fields": sorted(allowed), "refused_fields": unexpected,
             "descriptive_fields_present": sorted(
                 name for name in unexpected if name in DESCRIPTIVE_FIELDS)},
        )


def _receipt(session: Session, scoped_key: str) -> dict[str, Any] | None:
    row = session.get(IdempotencyKey, scoped_key)
    if row is None or not row.response_json:
        return None
    answer = json.loads(row.response_json)
    answer["idempotency_replay"] = True
    return answer


def _store_receipt(session: Session, *, scoped_key: str, signature: str,
                   answer: dict[str, Any]) -> None:
    now = datetime.now(timezone.utc)
    session.add(
        IdempotencyKey(
            key=scoped_key,
            operation=FROM_SLOTS_OPERATION,
            request_hash=signature,
            response_status=201,
            response_json=json.dumps(answer, sort_keys=True, default=str),
            created_at=now.isoformat(),
            # The shipped DDL makes this column NOT NULL. Omitting it is invisible under the ORM's
            # `create_all` and fails on the first press against the package schema, so the expiry is
            # written here the same way the departure commit door writes it.
            expires_at=(now + timedelta(days=7)).isoformat(),
        )
    )


def _slot_facts(place: Place, slot: dict[str, Any]) -> dict[str, Any]:
    """What this server holds for the place this slot names, judged by the gate's own predicates."""
    gaps: list[str] = []
    window = _place_window(_SlotLike(place))
    if window is None:
        gaps.append(GAP_HOURS)
    verified = _place_verified_cost(place)
    declared = slot.get("estimated_cost_minor")
    if declared is None:
        gaps.append(GAP_COST)
    if place.latitude is None or place.longitude is None:
        gaps.append(GAP_COORDINATE)
    return {
        "place_id": place.id,
        "title": place.name,
        "city_code": place.city_code,
        "has_coordinate": place.latitude is not None and place.longitude is not None,
        "opening_hours_recorded": window is not None,
        "verified_cost_minor": verified,
        "cost_declared": declared is not None,
        "gaps": gaps,
    }


class _SlotLike:
    """`_place_window` reads `opening_hours_json` off whatever it is handed; a Place row is enough.

    The gate's predicate takes a light object elsewhere in this app, so this door presents the same
    shape instead of copying the window parsing -- one writer per judgement, still.
    """

    def __init__(self, place: Place) -> None:
        self.opening_hours_json = place.opening_hours_json


@router.post(FROM_SLOTS_PATH, status_code=201)
def journey_plan_from_slots(
    response: Response,
    request: Request,
    journey_id: UUID,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    body: dict | None = None,
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    """Write the given slots as a CANDIDATE plan version, preserving their order and times."""
    journey, seat = _signed_journey(request, session, journey_id)
    fields = body or {}
    _refused_slot_fields(fields, BODY_FIELDS, slot=None, code=REASON_BODY,
                         message="this door takes slots, a planning mode and a revision")
    slots = fields.get("slots")
    if not isinstance(slots, list) or not slots:
        raise _refuse(422, "a plan needs at least one slot", REASON_SLOT_COUNT,
                      {"journey_id": journey.id, "slots_received": slots if isinstance(
                          slots, list) else type(slots).__name__})
    if idempotency_key is None:
        raise _refuse(
            422,
            "creating a plan version needs an Idempotency-Key so a retry cannot create a second one",
            REASON_KEY_REQUIRED,
            {"header": "Idempotency-Key", "journey_id": journey.id},
        )
    planning_mode = str(fields.get("planning_mode") or "balanced")
    if planning_mode not in PLANNING_MODES:
        raise _refuse(
            422,
            "planning_mode must be a word this server stores",
            REASON_BODY,
            {"accepted_words": list(PLANNING_MODES), "received": planning_mode},
        )
    if "expected_revision" not in fields:
        raise _refuse(
            422,
            "a draft write must say which plan version the draft was read against, "
            "and must say null when there is none",
            REASON_REVISION_MISSING,
            {"journey_id": journey.id, "field": "expected_revision",
             "accepted_values": ["the journey's active_plan_version_id", "null for a first draft"],
             "current_active_plan_version_id": journey.active_plan_version_id},
        )
    # Presence is the contract; the value may be empty. A first journey has no `active_plan_version_id`
    # at all, so a caller that names null is not forgetting the revision -- it is stating the only thing
    # that is true. Before this split the two were one check, and such a draft had no legal request:
    # null was 422 `EXPECTED_REVISION_REQUIRED` and any id was 409 `BASE_PLAN_MOVED`.
    named_revision = "" if fields["expected_revision"] is None else str(
        fields["expected_revision"]).strip()
    in_force = str(journey.active_plan_version_id or "")
    if named_revision != in_force:
        raise _refuse(
            409,
            "the plan this draft was read against is no longer the one in force",
            REASON_REVISION,
            {"journey_id": journey.id, "expected_revision": named_revision,
             "current_active_plan_version_id": journey.active_plan_version_id},
        )

    signature = canonical_request_signature({
        "operation": FROM_SLOTS_OPERATION,
        "journey_id": journey.id,
        "traveler_id": seat["traveler_id"],
        "expected_revision": named_revision,
        "slots": slots,
        "planning_mode": planning_mode,
    })
    scoped_key = f"{FROM_SLOTS_OPERATION}:{idempotency_key}"
    existing = session.get(IdempotencyKey, scoped_key)
    if existing is not None and existing.request_hash != signature:
        raise _refuse(409, "same idempotency key used for a different request",
                      REASON_KEY_CONFLICT, {"journey_id": journey.id,
                                            "idempotency_key": idempotency_key})
    replayed = _receipt(session, scoped_key)
    if replayed is not None:
        response.headers["Cache-Control"] = "private, no-store"
        return replayed

    rows: list[dict[str, Any]] = []
    total_cost = 0
    for index, slot in enumerate(slots, start=1):
        if not isinstance(slot, dict):
            raise _refuse(422, "each slot is an object of the fields this door names",
                          REASON_SLOT_FIELDS, {"slot": index, "received": type(slot).__name__})
        _refused_slot_fields(slot, SLOT_FIELDS, slot=index, code=REASON_SLOT_FIELDS,
                             message="a slot carries the row it points at and its own times")
        raw_place_id = str(slot.get("place_id") or "")
        if not raw_place_id:
            raise _refuse(422, "a slot must name the place row it stands for",
                          REASON_PLACE_NOT_FOUND, {"slot": index, "missing": ["place_id"]})
        if SOURCE_ID_MARKER in raw_place_id:
            raise _refuse(
                422,
                "a provider id is not a place this server holds; map it to a canonical id first",
                REASON_DELEGATED_SHAPE,
                {"slot": index, "accepted_shape": "canonical Place uuid",
                 "refused_shape": "provider_key:external_id",
                 "next_action": identity_pointer(journey.id, raw_place_id),
                 "journey_id": journey.id},
            )
        try:
            place_uuid = UUID(raw_place_id)
        except (TypeError, ValueError) as refused:
            raise _refuse(
                422, "a provider id is not a place this server holds; map it to a canonical id first",
                REASON_DELEGATED_SHAPE,
                {"slot": index, "received": raw_place_id[:40], "detail": str(refused)[:80],
                 "next_action": identity_pointer(journey.id, raw_place_id)},
            ) from refused
        place = session.get(Place, str(place_uuid))
        if place is None:
            raise _refuse(
                404, "the place this slot points at is not in this store",
                REASON_PLACE_NOT_FOUND,
                {"slot": index, "place_id": str(place_uuid), "journey_id": journey.id},
            )
        if str(place.city_code) != str(journey.city_code):
            raise _refuse(
                409,
                "that place belongs to another city than this journey, so it cannot be dropped in "
                "beside a same-named landmark",
                REASON_PLACE_OTHER_CITY,
                {"slot": index, "place_id": place.id, "place_city_code": place.city_code,
                 "journey_city_code": journey.city_code},
            )
        start_at = _parse(slot.get("start_at"), "start_at", index)
        end_at = _parse(slot.get("end_at"), "end_at", index)
        if end_at <= start_at:
            raise _refuse(
                422, "a slot ends after it starts", REASON_TIMES,
                {"slot": index, "start_at": str(slot.get("start_at")),
                 "end_at": str(slot.get("end_at"))},
            )
        declared = slot.get("estimated_cost_minor")
        currency = str(slot.get("currency") or journey.budget_currency)
        travel_min = int(slot.get("travel_from_prev_min") or 0)
        total_cost += int(declared) if isinstance(declared, int) else 0
        rows.append({
            "sequence_no": index,
            "place": place,
            "place_id": place.id,
            "start_at": start_at,
            "end_at": end_at,
            "estimated_cost_minor": int(declared) if isinstance(declared, int) else 0,
            "cost_declared": isinstance(declared, int),
            "currency": currency,
            "travel_from_prev_min": travel_min,
            "facts": _slot_facts(place, slot),
        })

    highest = session.scalar(
        select(func.max(PlanVersion.version_no)).where(PlanVersion.journey_id == journey.id)
    )
    version_no = int(highest or 0) + 1
    now = datetime.now(timezone.utc).isoformat()
    plan = PlanVersion(
        id=str(uuid4()),
        journey_id=journey.id,
        version_no=version_no,
        planning_mode=planning_mode,
        status=PLAN_STATUS_CANDIDATE,
        source=PLAN_SOURCE_MANUAL,
        parent_plan_version_id=journey.active_plan_version_id,
        total_cost_minor=total_cost,
        currency=journey.budget_currency,
        estimated_duration_min=sum(
            int((row["end_at"] - row["start_at"]).total_seconds() // 60) for row in rows
        ),
        created_at=now,
    )
    session.add(plan)
    session.flush()
    if session.scalar(select(func.count()).select_from(PlanVersion).where(
            PlanVersion.journey_id == journey.id,
            PlanVersion.version_no == version_no)) != 1:
        raise _refuse(
            500, "two drafts claimed the same plan version number", REASON_VERSION_COLLISION,
            {"journey_id": journey.id, "version_no": version_no},
        )
    for row in rows:
        session.add(Activity(
            id=str(uuid4()),
            plan_version_id=plan.id,
            sequence_no=row["sequence_no"],
            activity_type="SIGHTSEE",
            title=row["place"].name,
            place_id=row["place_id"],
            city_service_id=None,
            start_at=row["start_at"].isoformat(),
            end_at=row["end_at"].isoformat(),
            travel_from_prev_min=row["travel_from_prev_min"],
            estimated_cost_minor=row["estimated_cost_minor"],
            currency=row["currency"],
            status=ACTIVITY_STATUS_PLANNED,
            locked=False,
            metadata_json="{}",
            created_at=now,
            updated_at=now,
        ))
    record_audit(
        session,
        action=FROM_SLOTS_ACTION,
        entity_type="PlanVersion",
        entity_id=plan.id,
        journey_id=journey.id,
        before={"expected_revision": named_revision,
                "active_plan_version_id": journey.active_plan_version_id,
                "traveler_id": seat["traveler_id"]},
        after={"plan_version_id": plan.id, "status": plan.status, "source": plan.source,
               "version_no": version_no, "slots": len(rows)},
        actor_type="traveler",
        actor_id=seat["traveler_id"],
    )

    answer = {
        "journey_id": journey.id,
        "task_id": None,
        "plan_version_id": plan.id,
        "draft_revision": named_revision or None,
        "status": plan.status,
        "version_no": version_no,
        "planning_mode": plan.planning_mode,
        "created_by_traveler_id": seat["traveler_id"],
        "selected": False,
        "activated": False,
        "slots": [
            {
                "sequence_no": row["sequence_no"],
                "place_id": row["place_id"],
                "start_at": row["start_at"].isoformat(),
                "end_at": row["end_at"].isoformat(),
                "estimated_cost_minor": row["estimated_cost_minor"],
                "cost_declared": row["cost_declared"],
                "currency": row["currency"],
                "facts": row["facts"],
            }
            for row in rows
        ],
        "counts": {
            "slots": len(rows),
            "with_coordinate": sum(1 for row in rows if row["facts"]["has_coordinate"]),
            "hours_recorded": sum(1 for row in rows if row["facts"]["opening_hours_recorded"]),
            "cost_verified": sum(1 for row in rows if row["facts"]["verified_cost_minor"] is not None),
            "cost_declared": sum(1 for row in rows if row["cost_declared"]),
        },
        "gaps": [
            {"sequence_no": row["sequence_no"], "place_id": row["place_id"],
             "gaps": row["facts"]["gaps"]}
            for row in rows if row["facts"]["gaps"]
        ],
        "next_actions": [
            NEXT_ACTION_FACTS.format(journey_id=journey.id),
            NEXT_ACTION_COMMIT.format(journey_id=journey.id),
        ],
        "idempotency_key": scoped_key,
        "created_at": now,
    }
    _store_receipt(session, scoped_key=scoped_key, signature=signature, answer=answer)
    session.commit()
    response.headers["Cache-Control"] = "private, no-store"
    response.headers["Vary"] = "Authorization, X-CityNexus-Traveler-Token"
    return answer
