"""Member-bound consent for a shared future: approve, reject, status -- and the arithmetic that decides.

This is the door the V3 order's fourth item names. Before it, the shipped accept door
(`POST /api/v1/replans/{proposal_id}/accept`) took *no identity at all*: its actor defaults to
`system`, so the first person who happened to know a proposal id moved everyone's plan. That is the
defect, not a missing feature: the arithmetic for "who must agree" already ships in
`backend/app/collective_mediation.py` (`classify_group_decision`, `collective_decision_epoch`,
`collective_mutation_decision`), and the two predicates that answer "in force" and "what may this role
do" already ship in `backend/app/main.py` as `_member_state` and `_role_capabilities` -- the latter
reading `journey_role_capabilities`, the same table the shipped roster projection
`active_journey_members_with_capabilities` consults for its `can_authorize_mutation` field. What had no
door was the human act bound to a credential, and the durable record of it.

Three rules, each decided by a row rather than by a sentence in this file:

* **consent belongs to the traveller who pressed it** -- the id comes from `resolve_traveler_principal`
  through `_signed_journey`, so the body carries no principal field. A body that tries to name one is
  refused by name (`CONSENT_DELEGATION_REFUSED`): an organiser cannot confirm for a member, and this
  door has no code path that would let them.
* **the rule is unanimity among the in-force members who hold mutation authority** -- `fulfilled` is
  `required is a subset of approved and no required member stands rejected`. Two of three leaves
  `fulfilled` false, no receipt issued, and the shared plan untouched; the third press is what
  attempts the transition.
* **the shared plan moves only through the door that already validates it** -- on fulfillment this
  module calls `_accept_replan_impl`, the same function `POST /api/v1/replans/{id}/accept` calls, so
  feasibility, the stale-base predicate, locked commitments, the single-ACTIVE invariant and the
  accept receipt are one writer. Its refusal is reported as its own field: social authority being
  complete and the physical transition being applyable are two facts and are never merged into one
  boolean.

No migration: `audit_logs` holds each press (its `actor_type` / `actor_id` are the binding),
`collective_authority_receipts` holds the authority boundary the fulfillment produced -- its
`required_member_ids_json` / `principal_actor_ids_json` / `response_audit_ids_json` columns exist for
exactly this and had no writer before now -- and `idempotency_keys` makes a retry after a dropped
response replay instead of recording the same human act twice.

What this door does not do: it does not create proposals (the shipped replan generator owns those
rows), it does not rank options or compute fairness (that is `collective_mediation`'s arithmetic,
imported not re-implemented), and it does not speak to a provider -- a consent read or press spends
no quota and cannot enumerate another traveller's journey, because every path starts at a seat.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.commerce.idempotency import canonical_request_signature
from app.core.audit import record_audit
from app.db.models import (
    AuditLog,
    CollectiveAuthorityReceipt,
    IdempotencyKey,
    Journey,
    JourneyMember,
    PlanVersion,
    ReplanProposal,
)
from app.db.session import get_session
from app.departure_read import _refuse, _signed_journey

router = APIRouter()

CONSENT_PATH = "/api/v1/journeys/{journey_id}/replan-proposals/{proposal_id}/consent"
CONSENT_OPERATION = "collective.consent"

#: The audit action every press writes. Reading the round means reading these rows, so the ledger
#: of who said what is the same ledger the rest of the product already walks.
ACTION_RECORDED = "collective.consent.recorded"
ACTION_APPLIED = "collective.consent.apply_recorded"
ACTION_RECEIPT_ISSUED = "collective.authority_receipt.issued"
ACTION_RECEIPT_INVALIDATED = "collective.authority_receipt.invalidated"

DECISION_APPROVE = "APPROVE"
DECISION_REJECT = "REJECT"
DECISIONS = (DECISION_APPROVE, DECISION_REJECT)

#: `collective_authority_receipts.authority_mode` has no CHECK in the shipped DDL, so the word this
#: door writes is declared here and pinned by the spec against the column's own comment.
AUTHORITY_MODE = "MEMBER_CONSENT"

#: The capability a role must hold for its member's answer to bind the shared plan. The same word the
#: shipped roster projection tests for its `can_authorize_mutation` field.
REQUIRED_CAPABILITY = "JOURNEY_UPDATE"

#: Words the shipped DDL allows in `journey_members.role` / `.member_state`. The owner arm below
#: writes the role of the traveller who holds the journey itself, so both are named here rather than
#: typed inline at two places.
OWNER_ROLE = "OWNER"
MEMBER_IN_FORCE = "MEMBER_IN_FORCE"

REASON_BODY = "CONSENT_BODY_TAKES_ONLY_DECISION"
REASON_DELEGATION = "CONSENT_DELEGATION_REFUSED"
REASON_DECISION_WORD = "CONSENT_DECISION_WORD_UNKNOWN"
REASON_KEY_REQUIRED = "CONSENT_IDEMPOTENCY_KEY_REQUIRED"
REASON_KEY_CONFLICT = "CONSENT_IDEMPOTENCY_KEY_REUSE_CONFLICT"
REASON_PROPOSAL_NOT_IN_JOURNEY = "PROPOSAL_NOT_IN_JOURNEY"
REASON_PROPOSAL_NOT_ACTIONABLE = "PROPOSAL_NOT_ACTIONABLE"
REASON_APPLY_REFUSED = "COLLECTIVE_APPLY_REFUSED_BY_PLAN_DOOR"
#: Verbatim from the shipped mediation fallback in `active_journey_members_with_capabilities`, so a
#: screen that already handles "nobody in this roster can authorize" keeps handling it.
REASON_NO_AUTHORITY = "NO_IN_FORCE_MEMBER_CAN_AUTHORIZE_JOURNEY_UPDATE"

INVALIDATED_BY_REJECT = "COLLECTIVE_MEMBER_REJECTED"
INVALIDATED_BY_REVISION = "COLLECTIVE_CONSENT_WITHDRAWN"

#: Fields that would let one credential answer for another. Refused by name rather than ignored, so
#: a client that thinks it is delegating learns that it cannot.
DELEGATION_FIELDS = frozenset({
    "member_id", "traveler_id", "traveler", "for_traveler_id", "on_behalf_of",
    "proxy_traveler_id", "actor_id", "as_member",
})
BODY_FIELDS = frozenset({"decision"})

#: Words `replan_proposals.status` allows for a proposal a member may still answer. The shipped
#: pending-replan sweep uses the same pair, so this door does not invent a third state.
ACTIONABLE_STATUSES = ("GENERATED", "PRESENTED")

#: A proposal's option surface for the shipped epoch arithmetic: two ids and the status, which is
#: all this door can honestly claim about a row it did not generate.
EPOCH_TRIGGER = "MEMBER_CONSENT_ROUND"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def required_authority(session: Session, journey) -> tuple[list[str], list[dict[str, Any]]]:
    """Which travellers must answer: in force, and holding the capability that moves the plan.

    Both judgements are read through the functions that already own them in `backend/app/main.py` --
    `_member_state` decides lapsed and withdrawn, `_role_capabilities` reads `journey_role_capabilities`
    rather than a role list written into this function. So if operations narrow the capability table,
    the consent round follows it the same instant.

    This deliberately does not call `active_journey_members_with_capabilities`, which answers the same
    roster question *plus* each member's twin snapshot and preference items. That projection writes a
    snapshot row for every member it projects, and a status read that spends storage is the defect this
    project already names for `GET /experience`. The two answers are pinned against each other over the
    same rows in the spec, so a drift between them goes red rather than quiet.
    """

    from app.main import _member_state, _role_capabilities

    now = _now()
    rows: list[dict[str, Any]] = []
    for member in session.scalars(
        select(JourneyMember).where(JourneyMember.journey_id == journey.id)
        .order_by(JourneyMember.created_at, JourneyMember.id)
    ).all():
        state = _member_state(member, now)
        capabilities = sorted(_role_capabilities(session, member.role))
        rows.append(
            {
                "member_id": member.id,
                "traveler_id": member.traveler_id,
                "role": member.role,
                "member_state": state,
                "capabilities": capabilities,
                "can_authorize_mutation": REQUIRED_CAPABILITY in capabilities,
            }
        )

    # The journey's own holder may never have got a `journey_members` row: `seat_of` treats
    # `journeys.traveler_id` as a seat in force for exactly that case, so a consent round that only
    # looked at member rows could never be answered by the person who owns the trip. The capability
    # is still read from `journey_role_capabilities` for the OWNER role, never assumed, so narrowing
    # that table takes the owner out of the round the same instant it takes an ADMIN out.
    owner_id = str(journey.traveler_id or "")
    if owner_id and not any(str(row["traveler_id"]) == owner_id for row in rows):
        owner_capabilities = sorted(_role_capabilities(session, OWNER_ROLE))
        rows.insert(
            0,
            {
                "member_id": None,
                "traveler_id": owner_id,
                "role": OWNER_ROLE,
                "member_state": MEMBER_IN_FORCE,
                "capabilities": owner_capabilities,
                "can_authorize_mutation": REQUIRED_CAPABILITY in owner_capabilities,
            },
        )

    required = sorted(
        str(row["traveler_id"]) for row in rows
        if row["member_state"] == MEMBER_IN_FORCE and row["can_authorize_mutation"]
    )
    return required, rows


def _presses(session: Session, proposal_id: str) -> list[AuditLog]:
    return list(
        session.scalars(
            select(AuditLog)
            .where(
                AuditLog.entity_type == "ReplanProposal",
                AuditLog.entity_id == proposal_id,
                AuditLog.action == ACTION_RECORDED,
            )
            .order_by(AuditLog.created_at, AuditLog.id)
        ).all()
    )


def _latest_by_traveler(rows: list[AuditLog]) -> dict[str, dict[str, Any]]:
    """One answer per traveller -- the last one, with the earlier one kept as `revised_from`."""
    answers: dict[str, dict[str, Any]] = {}
    for row in rows:
        actor_id = str(row.actor_id or "")
        if not actor_id:
            continue
        payload = json.loads(row.after_json or "{}")
        answer = {
            "traveler_id": actor_id,
            "decision": payload.get("decision"),
            "recorded_at": row.created_at,
            "audit_id": row.id,
            "counts_toward_fulfillment": bool(payload.get("counts_toward_fulfillment", False)),
            "revised_from": None,
        }
        previous = answers.get(actor_id)
        if previous is not None:
            answer["revised_from"] = {
                "decision": previous.get("decision"),
                "audit_id": previous.get("audit_id"),
                "recorded_at": previous.get("recorded_at"),
            }
        answers[actor_id] = answer
    return answers


def _live_receipt(session: Session, journey_id: str, proposal_id: str):
    return session.scalar(
        select(CollectiveAuthorityReceipt)
        .where(
            CollectiveAuthorityReceipt.journey_id == journey_id,
            CollectiveAuthorityReceipt.proposal_id == proposal_id,
            CollectiveAuthorityReceipt.invalidated_at.is_(None),
        )
        .order_by(CollectiveAuthorityReceipt.issued_at.desc())
    )


def _receipt_payload(row) -> dict[str, Any]:
    return {
        "receipt_id": row.id,
        "authority_mode": row.authority_mode,
        "classification": row.classification,
        "required_traveler_ids": json.loads(row.required_member_ids_json or "[]"),
        "principal_actor_ids": json.loads(row.principal_actor_ids_json or "[]"),
        "response_audit_ids": json.loads(row.response_audit_ids_json or "[]"),
        "decision_epoch": row.decision_epoch,
        "material_world_epoch": row.material_world_epoch,
        "recovery_epoch_id": row.recovery_epoch_id,
        "issued_at": row.issued_at,
    }


def shared_plan_state(proposal, journey, proposed_plan) -> dict[str, Any]:
    """Did the shared plan actually move, read off the rows -- never from this request's intent."""
    active_now = bool(
        proposed_plan is not None
        and proposed_plan.status == "ACTIVE"
        and str(journey.active_plan_version_id or "") == str(proposal.proposed_plan_version_id)
    )
    return {
        "base_plan_version_id": proposal.base_plan_version_id,
        "proposed_plan_version_id": proposal.proposed_plan_version_id,
        "proposal_status": proposal.status,
        "journey_active_plan_version_id": journey.active_plan_version_id,
        "proposed_plan_status": proposed_plan.status if proposed_plan is not None else None,
        "shared_plan_updated": active_now,
    }


def _refuse_transition(exc: HTTPException) -> dict[str, Any]:
    """The plan door's own refusal, reported as a field instead of becoming this door's answer.

    A member's consent is a human act that happened; a rejected transition is a physical fact about
    the plan. Collapsing the two would erase the first whenever the second fails.
    """

    return {
        "attempted": True,
        "applied": False,
        "refusal_status": exc.status_code,
        "refusal_detail": str(exc.detail),
        "reason_code": REASON_APPLY_REFUSED,
    }


def _receipt(session: Session, scoped_key: str) -> dict[str, Any] | None:
    row = session.get(IdempotencyKey, scoped_key)
    if row is None or not row.response_json:
        return None
    answer = json.loads(row.response_json)
    answer["idempotency_replay"] = True
    return answer


def _store_receipt(session: Session, *, scoped_key: str, answer: dict[str, Any]) -> None:
    """Write or refresh this press's receipt, so the durable answer is the final one.

    Upserted rather than inserted twice: the row is first written before the plan transition is
    attempted -- so a press that was answered but whose transition the plan door refused still has
    its receipt -- and refreshed with the plan's final state after it.
    """

    now = _now()
    payload = json.dumps(answer, sort_keys=True, default=str)
    signature = canonical_request_signature(
        {
            "operation": CONSENT_OPERATION,
            "journey_id": answer.get("journey_id"),
            "proposal_id": answer.get("proposal_id"),
            "traveler_id": answer.get("recorded_by_traveler_id"),
            "decision": answer.get("decision"),
        }
    )
    row = session.get(IdempotencyKey, scoped_key)
    if row is not None:
        row.response_json = payload
        row.response_status = 200
        return
    session.add(
        IdempotencyKey(
            key=scoped_key,
            operation=CONSENT_OPERATION,
            request_hash=signature,
            response_status=200,
            response_json=payload,
            created_at=now.isoformat(),
            expires_at=(now + timedelta(days=7)).isoformat(),
        )
    )


def _issue_receipt(
    session: Session,
    *,
    journey,
    proposal,
    required: list[str],
    answers: dict[str, dict[str, Any]],
    roster: list[dict[str, Any]],
    classification: str | None,
) -> CollectiveAuthorityReceipt:
    """Mint the authority boundary the fulfilled rule produced, using the shipped epoch arithmetic."""

    from app.collective_mediation import collective_decision_epoch

    approved = sorted(
        traveler_id
        for traveler_id, answer in answers.items()
        if answer.get("decision") == DECISION_APPROVE
        and answer.get("counts_toward_fulfillment")
    )
    members = [
        {
            "member_id": row.get("member_id"),
            "role": row.get("role"),
            "capabilities": row.get("capabilities") or [],
            "member_state": row.get("member_state"),
        }
        for row in roster
    ]
    epoch = collective_decision_epoch(
        journey_id=str(journey.id),
        mission_id=EPOCH_TRIGGER,
        trigger_event_id=str(proposal.id),
        base_plan_version_id=proposal.base_plan_version_id,
        options=[
            {
                "proposal_id": str(proposal.id),
                "plan_id": str(proposal.proposed_plan_version_id),
                "status": proposal.status,
            }
        ],
        required_member_ids=required,
        members=members,
    )
    row = CollectiveAuthorityReceipt(
        id=str(uuid4()),
        journey_id=journey.id,
        proposal_id=proposal.id,
        plan_version_id=proposal.proposed_plan_version_id,
        authority_mode=AUTHORITY_MODE,
        decision_epoch=epoch,
        material_world_epoch=canonical_request_signature(
            {
                "base_plan_version_id": proposal.base_plan_version_id,
                "proposed_plan_version_id": proposal.proposed_plan_version_id,
                "hard_constraints_passed": proposal.hard_constraints_passed,
                "locked_commitments_preserved": proposal.locked_commitments_preserved,
            }
        ),
        candidate_surface_fingerprint=canonical_request_signature(
            {"proposal_ids": [str(proposal.id)]}
        ),
        recovery_epoch_id=proposal.recovery_epoch_id,
        required_member_ids_json=json.dumps(required),
        response_audit_ids_json=json.dumps(
            sorted(str(answers[item]["audit_id"]) for item in approved)
        ),
        principal_actor_ids_json=json.dumps(approved),
        classification=classification or AUTHORITY_MODE,
        issued_at=_now().isoformat(),
    )
    session.add(row)
    record_audit(
        session,
        action=ACTION_RECEIPT_ISSUED,
        entity_type="CollectiveAuthorityReceipt",
        entity_id=row.id,
        journey_id=journey.id,
        after=_receipt_payload(row),
        actor_type="traveler",
        actor_id=approved[-1] if approved else None,
    )
    return row


def _invalidate_receipt(session: Session, row, *, code: str, actor_id: str | None) -> None:
    row.invalidated_at = _now().isoformat()
    row.invalidation_code = code
    record_audit(
        session,
        action=ACTION_RECEIPT_INVALIDATED,
        entity_type="CollectiveAuthorityReceipt",
        entity_id=row.id,
        journey_id=row.journey_id,
        after={
            "receipt_id": row.id,
            "proposal_id": row.proposal_id,
            "invalidation_code": code,
            "invalidated_at": row.invalidated_at,
        },
        actor_type="traveler",
        actor_id=actor_id,
    )


def _round(
    session: Session,
    *,
    journey,
    proposal,
    required: list[str],
    roster: list[dict[str, Any]],
    classification: str | None,
) -> dict[str, Any]:
    """The answer both doors give: who must say it, who has, and what the rule therefore decides."""

    answers = _latest_by_traveler(_presses(session, proposal.id))
    approved = sorted(
        item["traveler_id"]
        for item in answers.values()
        if item["decision"] == DECISION_APPROVE and item["counts_toward_fulfillment"]
    )
    rejected = sorted(
        item["traveler_id"]
        for item in answers.values()
        if item["decision"] == DECISION_REJECT and item["counts_toward_fulfillment"]
    )
    outstanding = sorted(set(required) - set(approved) - set(rejected))
    fulfilled = bool(required) and set(required) <= set(approved) and not rejected
    proposed_plan = session.get(PlanVersion, proposal.proposed_plan_version_id)
    receipt = _live_receipt(session, journey.id, proposal.id)
    return {
        "journey_id": journey.id,
        "proposal_id": proposal.id,
        "authority_mode": AUTHORITY_MODE,
        "authority_basis": "journey_role_capabilities",
        "required_traveler_ids": required,
        "required_count": len(required),
        "roster": [
            {
                "traveler_id": row.get("traveler_id"),
                "member_id": row.get("member_id"),
                "role": row.get("role"),
                "member_state": row.get("member_state"),
                "can_authorize_mutation": bool(row.get("can_authorize_mutation")),
                "decision": answers.get(str(row.get("traveler_id")), {}).get("decision"),
            }
            for row in roster
        ],
        "answers": [answers[key] for key in sorted(answers)],
        "counts": {
            "required": len(required),
            "approved": len(approved),
            "rejected": len(rejected),
            "outstanding": len(outstanding),
        },
        "approved_traveler_ids": approved,
        "rejected_traveler_ids": rejected,
        "outstanding_traveler_ids": outstanding,
        "fulfilled": fulfilled,
        "classification": classification,
        "receipt": _receipt_payload(receipt) if receipt is not None else None,
        "shared_plan": shared_plan_state(proposal, journey, proposed_plan),
    }


def round_answer(session: Session, journey, proposal) -> dict[str, Any]:
    """This door's own fulfilment arithmetic for one proposal, asked from outside the consent routes.

    `app.departure_commit` and `app.plan_evidence` each have to know whether a round about a candidate
    still holds the shared plan where it was. Who is required, whose answer counts, and what unanimity
    means are this module's rule, so those doors ask here instead of re-deriving it -- the answer they get
    is the same one `GET .../consent` answers with, computed by the same `_round` call.
    """
    required, roster = required_authority(session, journey)
    answer = _round(
        session, journey=journey, proposal=proposal, required=required, roster=roster,
        classification=_classification_for(session, journey, proposal),
    )
    return {
        "proposal_id": answer["proposal_id"],
        "status": str(proposal.status),
        "fulfilled": bool(answer["fulfilled"]),
        "counts": dict(answer["counts"]),
        "outstanding_traveler_ids": list(answer["outstanding_traveler_ids"]),
        "rejected_traveler_ids": list(answer["rejected_traveler_ids"]),
        "read_from": "app.collective_consent._round",
    }


def _proposal_and_journey(request: Request, session: Session, journey_id: UUID, proposal_id: str):
    """Seat first, then the proposal, then whether anyone in this roster may answer at all."""

    journey, seat = _signed_journey(request, session, journey_id)
    proposal = session.get(ReplanProposal, str(proposal_id))
    if proposal is None or proposal.journey_id != journey.id:
        raise _refuse(
            404,
            "Replan proposal was not found on this journey",
            REASON_PROPOSAL_NOT_IN_JOURNEY,
            {"journey_id": journey.id, "proposal_id": str(proposal_id)},
        )
    return journey, seat, proposal


def _classification_for(session: Session, journey, proposal) -> str | None:
    """The mediation classification a mission round recorded for this exact proposal, if any.

    Only `journey_missions.resolved_intent_json` is read here. The shipped mediation readers in
    `app.collective_mediation` look at `mission.clarification_json`, and this package's schema has no
    such column on `journey_missions` -- neither in `app/db/models.py` nor in `db/schema.sql` -- so
    those two functions raise `AttributeError` the moment they are handed a real mission row. Both
    facts are pinned by name in the spec rather than worked around quietly: this door reports the
    classification a mission recorded in a column that exists, and answers None when none did.
    """

    from app.db.models import JourneyMission

    for mission in session.scalars(
        select(JourneyMission).where(JourneyMission.journey_id == journey.id)
    ).all():
        try:
            recorded = json.loads(mission.resolved_intent_json or "{}")
        except ValueError:
            continue
        mediation = recorded.get("collective_mediation")
        if not isinstance(mediation, dict):
            continue
        if str(mediation.get("selected_proposal_id") or "") != str(proposal.id):
            continue
        word = str(mediation.get("classification") or "")
        if word:
            return word
    return None


@router.get(CONSENT_PATH)
def journey_consent_status(
    response: Response,
    request: Request,
    journey_id: UUID,
    proposal_id: UUID,
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    """Who must agree to this shared future, who has, and whether the plan moved."""
    journey, seat, proposal = _proposal_and_journey(request, session, journey_id, str(proposal_id))
    required, roster = required_authority(session, journey)
    answer = _round(
        session,
        journey=journey,
        proposal=proposal,
        required=required,
        roster=roster,
        classification=_classification_for(session, journey, proposal),
    )
    answer["asked_by_traveler_id"] = seat["traveler_id"]
    if not required:
        answer["blocking_code"] = REASON_NO_AUTHORITY
    response.headers["Cache-Control"] = "private, no-store"
    response.headers["Vary"] = "Authorization, X-CityNexus-Traveler-Token"
    return answer


@router.post(CONSENT_PATH)
def journey_consent_press(
    response: Response,
    request: Request,
    journey_id: UUID,
    proposal_id: UUID,
    body: dict | None = None,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    """Record one member's APPROVE or REJECT for one proposal, as themselves, once."""
    journey, seat, proposal = _proposal_and_journey(request, session, journey_id, str(proposal_id))
    fields = body or {}
    named_principals = sorted(str(name) for name in fields if name in DELEGATION_FIELDS)
    if named_principals:
        raise _refuse(
            422,
            "a consent belongs to the credential that pressed it, not to a traveller named in the body",
            REASON_DELEGATION,
            {
                "journey_id": journey.id,
                "proposal_id": proposal.id,
                "refused_fields": named_principals,
                "pressing_traveler_id": seat["traveler_id"],
            },
        )
    unexpected = sorted(str(name) for name in fields if name not in BODY_FIELDS)
    if unexpected:
        raise _refuse(
            422,
            "a consent carries one decision word and nothing else",
            REASON_BODY,
            {"accepted_fields": sorted(BODY_FIELDS), "refused_fields": unexpected},
        )
    decision = str(fields.get("decision") or "")
    if decision not in DECISIONS:
        raise _refuse(
            422,
            "decision must be one of the words this door records",
            REASON_DECISION_WORD,
            {"accepted_words": list(DECISIONS), "received": decision or None},
        )
    if idempotency_key is None:
        raise _refuse(
            422,
            "a consent needs an Idempotency-Key so a retry cannot record the same act twice",
            REASON_KEY_REQUIRED,
            {"header": "Idempotency-Key", "proposal_id": proposal.id},
        )
    if proposal.status not in ACTIONABLE_STATUSES:
        raise _refuse(
            409,
            "this proposal is no longer one a member can answer",
            REASON_PROPOSAL_NOT_ACTIONABLE,
            {"proposal_status": proposal.status, "actionable_statuses": list(ACTIONABLE_STATUSES)},
        )

    scoped_key = f"{CONSENT_OPERATION}:{idempotency_key}"
    signature = canonical_request_signature(
        {
            "operation": CONSENT_OPERATION,
            "journey_id": journey.id,
            "proposal_id": proposal.id,
            "traveler_id": seat["traveler_id"],
            "decision": decision,
        }
    )
    existing = session.get(IdempotencyKey, scoped_key)
    if existing is not None and existing.request_hash != signature:
        raise _refuse(
            409,
            "same idempotency key used for a different consent",
            REASON_KEY_CONFLICT,
            {"journey_id": journey.id, "idempotency_key": idempotency_key},
        )
    replayed = _receipt(session, scoped_key)
    if replayed is not None:
        response.headers["Cache-Control"] = "private, no-store"
        return replayed

    required, roster = required_authority(session, journey)
    if not required:
        raise _refuse(
            409,
            "no in-force member of this journey can authorize a plan mutation, so a consent "
            "round cannot bind one",
            REASON_NO_AUTHORITY,
            {
                "journey_id": journey.id,
                "proposal_id": proposal.id,
                "roles_in_roster": sorted({str(row.get("role")) for row in roster}),
                "capability_read_from": "journey_role_capabilities",
                "required_capability": REQUIRED_CAPABILITY,
            },
        )

    standing = seat["traveler_id"] in required
    audit_payload = {
        "decision": decision,
        "proposal_status": proposal.status,
        "base_plan_version_id": proposal.base_plan_version_id,
        "proposed_plan_version_id": proposal.proposed_plan_version_id,
        "required_traveler_ids": required,
        "counts_toward_fulfillment": standing,
        "seat": {
            "seat_kind": seat["seat_kind"],
            "role": seat["role"],
            "member_id": seat["member_id"],
            "member_state": seat["member_state"],
        },
    }
    audit_id = str(uuid4())
    session.add(
        AuditLog(
            id=audit_id,
            actor_type="traveler",
            actor_id=seat["traveler_id"],
            journey_id=journey.id,
            action=ACTION_RECORDED,
            entity_type="ReplanProposal",
            entity_id=proposal.id,
            before_json=None,
            after_json=json.dumps(audit_payload, ensure_ascii=False),
            trace_id=str(uuid4()),
            created_at=_now().isoformat(),
        )
    )
    # Flushed before the round is read back: this session does not autoflush, so without this the
    # answer a member gets would lag their own press by one -- the round would say 2/3 right after
    # the third person pressed it. The arm that caught this is the 2-of-3 arm in the spec.
    session.flush()

    classification = _classification_for(session, journey, proposal)
    live = _live_receipt(session, journey.id, proposal.id)
    answer = _round(
        session,
        journey=journey,
        proposal=proposal,
        required=required,
        roster=roster,
        classification=classification,
    )
    answer["recorded_by_traveler_id"] = seat["traveler_id"]
    answer["counts_toward_fulfillment"] = standing
    answer["decision"] = decision

    if live is not None and not answer["fulfilled"]:
        code = INVALIDATED_BY_REJECT if decision == DECISION_REJECT else INVALIDATED_BY_REVISION
        _invalidate_receipt(session, live, code=code, actor_id=seat["traveler_id"])
        answer["receipt"] = None
        answer["receipt_invalidated"] = {"receipt_id": live.id, "invalidation_code": code}
    elif answer["fulfilled"] and live is None:
        issued = _issue_receipt(
            session,
            journey=journey,
            proposal=proposal,
            required=required,
            answers=_latest_by_traveler(_presses(session, proposal.id)),
            roster=roster,
            classification=classification,
        )
        answer["receipt"] = _receipt_payload(issued)

    # The social act is committed before the physical transition is attempted: a refused plan change
    # must not roll back a real answer, and the plan door owns its own transaction and receipt.
    _store_receipt(session, scoped_key=scoped_key, answer=answer)
    session.commit()

    answer["plan_apply"] = {"attempted": False, "applied": False}
    if answer["fulfilled"]:
        from app.main import _accept_replan_impl

        apply_key = f"collective-consent-{answer['receipt']['receipt_id']}" if answer["receipt"] \
            else f"collective-consent-{proposal.id}"
        try:
            applied = _accept_replan_impl(
                UUID(proposal.id),
                apply_key,
                session,
                actor_type="traveler",
                actor_id=seat["traveler_id"],
            )
        except HTTPException as exc:
            session.rollback()
            answer["plan_apply"] = _refuse_transition(exc)
        else:
            # The plan door answers with its own three sections. They are named here, not unpacked:
            # the shared plan's state is re-read from the rows below rather than taken on trust from
            # a response body, and the rows and the body agreeing is what the spec pins.
            sections = sorted(str(key) for key in applied)
            record_audit(
                session,
                action=ACTION_APPLIED,
                entity_type="ReplanProposal",
                entity_id=proposal.id,
                journey_id=journey.id,
                after={"apply_receipt_key": apply_key, "apply_answer_sections": sections},
                actor_type="traveler",
                actor_id=seat["traveler_id"],
            )
            session.commit()
            answer["plan_apply"] = {
                "attempted": True,
                "applied": True,
                "apply_receipt_key": apply_key,
                "apply_answer_sections": sections,
            }
        refreshed = _round(
            session,
            journey=session.get(Journey, journey.id),
            proposal=session.get(ReplanProposal, proposal.id),
            required=required,
            roster=roster,
            classification=classification,
        )
        answer["shared_plan"] = refreshed["shared_plan"]
        answer["fulfilled"] = refreshed["fulfilled"]
        answer["receipt"] = refreshed["receipt"]

    _store_receipt(session, scoped_key=scoped_key, answer=answer)
    session.commit()
    response.headers["Cache-Control"] = "private, no-store"
    response.headers["Vary"] = "Authorization, X-CityNexus-Traveler-Token"
    return answer
