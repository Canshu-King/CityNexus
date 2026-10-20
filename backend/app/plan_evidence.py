"""Freeze the travel facts a CANDIDATE plan was built on, so the round can actually be judged.

``POST /api/v1/journeys/{journey_id}/plans/from-slots`` writes the slots a draft already holds, and it is
deliberately unreachable from any provider -- that ban is policed by ``app/plan_from_slots``'s own syntax
tree test, and this module does not touch it. The consequence was that a hand-built candidate arrived at
``POST .../plans/{plan_version_id}/submission`` with no frozen mobility evidence, where the shipped
feasibility gate raises ``STALE_RECOMPOSE_REQUIRED`` and this project's own honest answer is
"cannot judge" (``gate.judged`` false, ``evidence_gap`` true). Such a candidate could never reach a
traveller's round, so the V3 journey stalled one inch short of the end.

This is that inch: a second, equally narrow, server-owned door that takes one existing CANDIDATE row and
asks the *existing* capture domain for the legs that plan's own slots imply.

* The pairs come from ``activities`` rows of that plan version, in ``sequence_no`` order -- a caller
  supplies no place list, so this cannot become a route-quoting or place-enumeration surface, and no
  client-supplied minute value is ever stored.
* The capture is ``app.integrations.mobility.runtime.capture_runtime_mobility_snapshot``, the same
  primitive ``plans/generate`` uses. This module adds no provider, no fallback rule and no trust level: a
  leg the fixture only covers with its blanket constant comes back tagged ``SYNTHETIC_DEFAULT`` here
  exactly as it does for a generated plan, and the answer says how many legs were hard-eligible.
* What it writes is the two nullable columns that already exist on ``plan_versions``
  (``mobility_snapshot_id``, ``mobility_evidence_json``). No migration, no new table, no status change.

Refusals, each named: no seat; a body with fields (every leg is read from rows); a missing
``Idempotency-Key``; that version not on this journey; the row not being ``CANDIDATE`` (an ACTIVE,
SELECTED or SUPERSEDED plan's evidence is not this door's to rewrite); a round already asking about this
candidate (the proposal was judged on the evidence that candidate had, and swapping facts under people who
are voting is not a capture, it is a silent re-write of their question); evidence that is half-frozen,
which the gate itself refuses to read; a slot whose place carries no point, so no complete matrix exists
for it; a provider that refused a leg (``MOBILITY_PROVIDER_REFUSED_A_LEG``, carrying the domain's own
tail, with nothing written). Re-freezing a CANDIDATE nobody is answering yet is allowed and is recorded:
the answer names the snapshot id it replaces, and the audit row's `before` carries it.

What it never does: it does not select, start, activate or present; it does not move
``journeys.active_plan_version_id``; it does not restate a judgement -- the caller re-reads
``POST .../submission`` or ``GET .../plans/delta`` and the gate answers for itself.

The order is part of the contract: the idempotency receipt is consulted before any state guard, because a
retry of a press that already froze evidence would otherwise be refused by the write it just made (the
round-in-flight guard is one of them). That order is measured, not asserted -- ``_live_evidence_1020eo.py``
presses the same key twice over a candidate that has since been submitted.

One thing this door reports instead of fixing: two consecutive slots naming the same place ask the gate for
a leg from that place to itself, and ``app.integrations.mobility.snapshot_capture`` deliberately freezes no
fact for a pair whose origin equals its destination. The answer names those steps
(``same_place_consecutive_transitions``) and says what the gate will answer. It does not write a
zero-minute measurement to make such a plan look feasible: whether an identity leg should become a fact of
the mobility domain is that domain's call, not this door's.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Request, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.collective_consent import round_answer
from app.commerce.idempotency import canonical_request_signature
from app.core.audit import record_audit
from app.db.models import Activity, IdempotencyKey, Place, PlanVersion, ReplanProposal
from app.db.session import get_session
from app.departure_facts import REASON_PLAN_NOT_IN_JOURNEY
from app.departure_read import _refuse, _signed_journey
from app.integrations.mobility.runtime import capture_runtime_mobility_snapshot
from app.integrations.mobility.snapshot_capture import MobilitySnapshotCaptureError
from app.replanning.provider_snapshots import fact_quality_summary

router = APIRouter()

FREEZE_PATH = "/api/v1/journeys/{journey_id}/plans/{plan_version_id}/mobility-freeze"
FREEZE_OPERATION = "plan.candidate_mobility_freeze"
FREEZE_ACTION = "plan.candidate_mobility_frozen"
CANDIDATE_STATUS = "CANDIDATE"

BODY_FIELDS: frozenset[str] = frozenset()

REASON_KEY_REQUIRED = "FREEZE_IDEMPOTENCY_KEY_REQUIRED"
REASON_KEY_CONFLICT = "FREEZE_IDEMPOTENCY_KEY_REUSE_CONFLICT"
REASON_BODY = "FREEZE_READS_EVERY_LEG_FROM_ROWS"
REASON_NOT_CANDIDATE = "FREEZE_NEEDS_A_CANDIDATE_VERSION"
REASON_HALF_FROZEN = "FREEZE_EVIDENCE_COLUMN_PAIR_IS_SPLIT"
REASON_ROUND_IN_FLIGHT = "FREEZE_PROPOSAL_ALREADY_ASKING"
REASON_NO_POINT = "FREEZE_SLOT_PLACE_HAS_NO_POINT"
REASON_PROVIDER = "MOBILITY_PROVIDER_REFUSED_A_LEG"

#: A proposal that members may still be answering, so its candidate's facts are not this door's to swap.
PROPOSAL_ACTIONABLE_STATUSES = ("GENERATED", "PRESENTED")

#: The two doors that read the evidence this door writes, kept here so the answer can name them.
SUBMISSION_PATH = "/api/v1/journeys/{journey_id}/plans/{plan_version_id}/submission"
DELTA_PATH = "/api/v1/journeys/{journey_id}/plans/delta"


def _coordinate(value: Any, *, axis: str) -> bool:
    """Whether this server holds a usable coordinate, judged inside the axis's own range."""
    try:
        number = float(value)
    except (TypeError, ValueError):
        return False
    limit = 90.0 if axis == "latitude" else 180.0
    return -limit <= number <= limit


def _plan_slots(session: Session, plan_id: str) -> list[dict[str, Any]]:
    """This plan version's own slots, in sequence order, each with the place row behind it."""
    rows = session.scalars(
        select(Activity).where(Activity.plan_version_id == plan_id).order_by(Activity.sequence_no)
    ).all()
    out: list[dict[str, Any]] = []
    for row in rows:
        key = str(row.place_id or row.city_service_id or "")
        place = session.get(Place, str(row.place_id)) if row.place_id else None
        out.append({
            "sequence_no": int(row.sequence_no),
            "routing_key": key,
            "place_id": str(row.place_id or ""),
            "city_service_id": str(row.city_service_id or ""),
            "has_place_row": place is not None,
            "has_point": bool(
                place is not None
                and _coordinate(place.latitude, axis="latitude")
                and _coordinate(place.longitude, axis="longitude")
            ),
        })
    return out


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
            operation=FREEZE_OPERATION,
            request_hash=signature,
            response_status=200,
            response_json=json.dumps(answer, sort_keys=True, default=str),
            created_at=now.isoformat(),
            # The shipped DDL makes this column NOT NULL, the same way the from-slots door writes it.
            expires_at=(now + timedelta(days=7)).isoformat(),
        )
    )


@router.post(FREEZE_PATH)
def journey_plan_mobility_freeze(
    response: Response,
    request: Request,
    journey_id: UUID,
    plan_version_id: UUID,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    body: dict | None = None,
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    """Capture and freeze this CANDIDATE's own legs with the domain the generator already uses."""
    journey, seat = _signed_journey(request, session, journey_id)
    fields = body or {}
    if fields:
        raise _refuse(
            422,
            "this door reads every leg from the plan's own rows, so a body has nothing to give it",
            REASON_BODY,
            {"accepted_fields": sorted(BODY_FIELDS), "received_fields": sorted(str(name)
                                                                              for name in fields)},
        )
    if idempotency_key is None:
        raise _refuse(
            422,
            "freezing evidence needs an Idempotency-Key so a retry replays instead of re-quoting a "
            "provider",
            REASON_KEY_REQUIRED,
            {"header": "Idempotency-Key", "journey_id": journey.id},
        )
    plan = session.get(PlanVersion, str(plan_version_id))
    if plan is None or str(plan.journey_id) != journey.id:
        raise _refuse(
            404,
            "that plan version is not a plan of this journey",
            REASON_PLAN_NOT_IN_JOURNEY,
            {"journey_id": journey.id, "plan_version_id": str(plan_version_id)},
        )

    # The idempotency replay is checked before any state guard: a retry of a press that already
    # succeeded must return that press's receipt, not a refusal raised by the very write it made.
    signature = canonical_request_signature({
        "operation": FREEZE_OPERATION,
        "journey_id": journey.id,
        "traveler_id": seat["traveler_id"],
        "plan_version_id": plan.id,
    })
    scoped_key = f"plan-mobility-freeze|{journey.id}|{idempotency_key}"
    existing = session.get(IdempotencyKey, scoped_key)
    if existing is not None and existing.request_hash != signature:
        raise _refuse(
            409, "same idempotency key used for a different request", REASON_KEY_CONFLICT,
            {"journey_id": journey.id, "idempotency_key": idempotency_key},
        )
    replayed = _receipt(session, scoped_key)
    if replayed is not None:
        response.headers["Cache-Control"] = "private, no-store"
        return replayed

    if plan.status != CANDIDATE_STATUS:
        raise _refuse(
            409,
            "only a CANDIDATE's evidence is this door's to write; a plan in force or already superseded "
            "keeps the evidence it was judged on",
            REASON_NOT_CANDIDATE,
            {"plan_version_id": plan.id, "status": plan.status,
             "accepted_status": CANDIDATE_STATUS},
        )
    has_id = bool(plan.mobility_snapshot_id)
    has_json = bool(plan.mobility_evidence_json)
    if has_id != has_json:
        raise _refuse(
            409,
            "this row carries one of the two evidence columns, which is the state the feasibility gate "
            "itself refuses to read; naming it is this door's job, not papering over it",
            REASON_HALF_FROZEN,
            {"plan_version_id": plan.id,
             "mobility_snapshot_id_present": has_id,
             "mobility_evidence_json_present": has_json,
             "detail": "app.services._snapshot_for_plan raises STALE_RECOMPOSE_REQUIRED here"},
        )

    #: "Is this round still asking?" is the consent door's rule, asked from
    #: `app.collective_consent.round_answer` rather than re-derived here -- the same reason
    #: `app.departure_commit` asks it. A round everybody required has approved is answered even when the
    #: shipped plan door refused to move the plan, and the traveller then has to be able to re-freeze; a
    #: rejected or unanswered round still holds this door, because re-freezing would change the facts
    #: under the people who are voting.
    asking = session.scalars(
        select(ReplanProposal)
        .where(ReplanProposal.journey_id == journey.id,
               ReplanProposal.proposed_plan_version_id == plan.id,
               ReplanProposal.status.in_(PROPOSAL_ACTIONABLE_STATUSES))
        .order_by(ReplanProposal.created_at.desc())
    ).all()
    rounds = [round_answer(session, journey, row) for row in asking]
    voting = [item for item in rounds if not item["fulfilled"]]
    if voting:
        raise _refuse(
            409,
            "a round is already asking about this candidate on the evidence it had; re-freezing here "
            "would change the facts under the people voting",
            REASON_ROUND_IN_FLIGHT,
            {"plan_version_id": plan.id,
             "proposal_ids": [item["proposal_id"] for item in voting],
             "proposal_statuses": sorted({item["status"] for item in voting}),
             "rounds": voting,
             "decided_proposal_ids": [item["proposal_id"] for item in rounds
                                      if item["fulfilled"]]},
        )

    slots = _plan_slots(session, plan.id)
    keys: list[str] = []
    for slot in slots:
        if slot["routing_key"] and slot["routing_key"] not in keys:
            keys.append(slot["routing_key"])
    captured_pairs: tuple[tuple[str, str], ...] = tuple(
        (origin, destination)
        for origin in keys
        for destination in keys
        if origin != destination
    )
    unlocatable = [slot["sequence_no"] for slot in slots if not slot["routing_key"]]
    # Two consecutive slots at one place ask the gate for a leg from that place to itself. The capture
    # domain deliberately freezes no self-pair -- `app.integrations.mobility.snapshot_capture` drops pairs
    # whose origin equals its destination -- so such a plan cannot be judged, and the refusal arrives much
    # later at `select`. Naming it here costs nothing and keeps the cause beside the act.
    repeated = [
        {"from_sequence_no": earlier["sequence_no"], "to_sequence_no": later["sequence_no"],
         "place_id": earlier["place_id"]}
        for earlier, later in zip(slots, slots[1:])
        if earlier["routing_key"] and earlier["routing_key"] == later["routing_key"]
    ]
    no_point = [
        {"sequence_no": slot["sequence_no"], "place_id": slot["place_id"]}
        for slot in slots
        if slot["routing_key"] and slot["has_place_row"] and not slot["has_point"]
    ]
    if no_point:
        raise _refuse(
            409,
            "a slot whose place carries no point cannot be routed, so no complete matrix exists for "
            "this plan",
            REASON_NO_POINT,
            {"plan_version_id": plan.id, "slots_without_coordinate": no_point,
             "journey_id": journey.id},
        )

    try:
        capture = capture_runtime_mobility_snapshot(
            session,
            journey,
            captured_pairs,
            operation_key=f"{FREEZE_OPERATION}:{plan.id}",
        )
    except (MobilitySnapshotCaptureError, KeyError, TypeError, ValueError) as refused:
        raise _refuse(
            503,
            "the mobility source this server uses refused one of this plan's legs, so no evidence was "
            "frozen and nothing was written",
            REASON_PROVIDER,
            {"plan_version_id": plan.id, "error_type": type(refused).__name__,
             "detail": str(refused)[:200], "legs_requested": len(captured_pairs)},
        ) from refused

    snapshot = capture.snapshot
    evidence = snapshot.to_evidence()
    previous_snapshot_id = plan.mobility_snapshot_id
    plan.mobility_snapshot_id = snapshot.snapshot_id
    plan.mobility_evidence_json = json.dumps(evidence, sort_keys=True, default=str)
    session.flush()
    # Read the pair back from the store, not from the objects this function holds: the gate below
    # compares `mobility_snapshot_id` against the snapshot id inside `mobility_evidence_json`, so that
    # is exactly the pair checked here.
    stored_id, stored_json = session.execute(
        select(PlanVersion.mobility_snapshot_id, PlanVersion.mobility_evidence_json)
        .where(PlanVersion.id == plan.id)
    ).one()
    read_back = json.loads(stored_json or "{}")
    if str(stored_id or "") != str(read_back.get("snapshot_id") or "") or not stored_id:
        raise _refuse(
            500,
            "the evidence this door wrote did not read back as the pair the gate requires",
            REASON_HALF_FROZEN,
            {"plan_version_id": plan.id, "stored_snapshot_id": str(stored_id or ""),
             "evidence_snapshot_id": str(read_back.get("snapshot_id") or "")},
        )

    summary = fact_quality_summary(snapshot)
    qualities = summary["fact_qualities"]
    hard_eligible = summary["hard_eligible_legs"]
    record_audit(
        session,
        action=FREEZE_ACTION,
        entity_type="PlanVersion",
        entity_id=plan.id,
        journey_id=journey.id,
        before={"mobility_snapshot_id": previous_snapshot_id, "slots": len(slots)},
        after={"mobility_snapshot_id": snapshot.snapshot_id,
               "source_provider": snapshot.source_provider_key,
               "legs": len(snapshot.facts), "degraded": bool(capture.degraded),
               "hard_eligible_legs": hard_eligible, "traveler_id": seat["traveler_id"]},
        actor_type="traveler",
        actor_id=seat["traveler_id"],
    )

    actions = [
        "judge it with POST " + SUBMISSION_PATH.format(
            journey_id=journey.id, plan_version_id=plan.id),
        "read the difference with GET " + DELTA_PATH.format(
            journey_id=journey.id) + f"?to_plan_version_id={plan.id}",
    ]
    if repeated:
        actions.append(
            "this plan asks the gate for a leg from one place to that same place, and the capture "
            "domain freezes no fact for a pair whose origin equals its destination "
            "(app/integrations/mobility/snapshot_capture.py, the `if a and b` normalisation of pairs): "
            "the gate will answer MOBILITY_DATA_UNAVAILABLE until that rule names a zero-minute self leg")
    answer = {
        "journey_id": journey.id,
        "plan_version_id": plan.id,
        "status": plan.status,
        "mobility_snapshot_id": snapshot.snapshot_id,
        "replaces_snapshot_id": previous_snapshot_id,
        "source_provider": snapshot.source_provider_key,
        "operation_key": snapshot.operation_key,
        "captured_at": snapshot.captured_at,
        "expires_at": evidence.get("expires_at"),
        "degraded": bool(capture.degraded),
        "counts": {
            "slots": len(slots),
            "distinct_places": len(keys),
            "legs_requested": len(captured_pairs),
            "legs_frozen": len(snapshot.facts),
            "hard_eligible_legs": hard_eligible,
            "fallback_legs": len(capture.fallback_pairs),
            "slots_without_a_location_row": len(unlocatable),
            "same_place_consecutive_transitions": len(repeated),
        },
        "same_place_consecutive_transitions": repeated,
        "fact_qualities": dict(sorted(qualities.items())),
        "provider_capabilities": dict(snapshot.provider_capabilities),
        "sequences_without_a_location_row": unlocatable,
        "evidence_columns": ["mobility_snapshot_id", "mobility_evidence_json"],
        "read_from": {
            "capture": "app.integrations.mobility.runtime.capture_runtime_mobility_snapshot",
            "columns": "app.db.models.PlanVersion.mobility_snapshot_id",
            "consumed_by": "app.services._snapshot_for_plan",
        },
        "next_actions": actions,
        "idempotency_key": scoped_key,
        "written_at": datetime.now(timezone.utc).isoformat(),
    }
    _store_receipt(session, scoped_key=scoped_key, signature=signature, answer=answer)
    session.commit()
    response.headers["Cache-Control"] = "private, no-store"
    response.headers["Vary"] = "Authorization, X-CityNexus-Traveler-Token"
    return answer
