"""One signed, idempotent write door: the variant a traveller picked becomes the formal plan.

This is the commit step the departure screen needs after `GET .../departure` answers
`NO_PLAN_SELECTED` with `candidates[]` in hand. Everything the transition itself decides --
frozen mobility evidence, feasibility, retiring the previous SELECTED row, moving the cursor,
the single-ACTIVE invariant, the `plan.selected` audit event -- belongs to
`POST /api/v1/journeys/{journey_id}/plans/{plan_version_id}/select` and is *not* re-implemented
here: this door calls that same function in-process, which is how `app.main` already uses it twice --
once for its own seed supply loop and once for the staged advance. A second
implementation of "pick a plan" is the failure this order explicitly closes.

What `select` cannot answer, and this door adds:

* *who* decided -- the caller is resolved through the same verifier every signed door uses
  (`app/traveler_principal.py`) and must hold a seat in force, so a lapsed or withdrawn member
  cannot commit; the answer comes from `departure_read.seat_of`, one writer for both doors.
* *whether this exact request was already applied* -- an `Idempotency-Key` is required and its
  receipt is stored in the existing `idempotency_keys` table, so a retry after a dropped response
  replays the answer instead of committing twice or emitting a second audit event.
* *that nothing else was accepted* -- the body carries one server-owned id and nothing else. Place
  names, URLs and provider payloads are refused by name, so this cannot become a way to describe a
  place to the server.
* *that a round which has not decided is not walked through* -- the V3 order's fourth item says the
  shared plan must not move while its round has not decided, so a proposal about this very candidate in
  `GENERATED` or `PRESENTED` whose round has not reached the consent door's bar makes the commit a
  refusal, not a fact. "Decided" is not this door's word to coin: it asks `app.collective_consent`
  (`round_answer`) who is required and whose answer counts, and lets the commit through when that door
  says the round is fulfilled -- which matters on a journey that has not departed, where
  `_accept_replan_executing` requires an ACTIVE journey, so a fulfilled round cannot apply, no shipped
  door ever writes another status for the row, and refusing here would strand the traveller behind a
  question nobody is waiting on. Measured on a real socket after that lift: the commit press that follows
  a fulfilled-but-unapplied round answers 200 and the journey then starts
  (`_live_v3_chain_1020ex.txt:14`, `:15`). Before the first version of this rule landed, the same press
  answered 200 while the round still showed `outstanding 1`, moved the journey's
  `active_plan_version_id`, superseded the old plan and left the proposal `PRESENTED`, still asking;
  `_live_round_bypass_1020ez.py` re-measures that press and now prints it as a refusal with the pointer
  and the proposal unchanged (`_live_round_bypass_1020ez.txt:8`), which is what a docstring may cite: the
  behaviour as it stands, the history as prose. A round somebody rejected keeps holding the door.

No schema migration: `audit_logs` already carries `actor_type` / `actor_id`, and `traveler` is the
word the member doors already write there, asserted by
`backend/tests/test_qoder_ord0503_member_doors.py`.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.collective_consent import round_answer
from app.commerce.idempotency import canonical_request_signature
from app.core.audit import record_audit
from app.db.models import IdempotencyKey, PlanVersion, ReplanProposal
from app.db.session import get_session
from app.departure_read import GATE_STALE_EVIDENCE, _refuse, _signed_journey

router = APIRouter()

COMMIT_PATH = "/api/v1/journeys/{journey_id}/departure/commit"
COMMIT_OPERATION = "journey.departure.commit"
COMMIT_ACTION = "plan.committed_by_traveler"

#: Refusal codes this door adds. Everything else propagates with the code the transition raised.
REASON_KEY_REQUIRED = "IDEMPOTENCY_KEY_REQUIRED"
REASON_KEY_CONFLICT = "IDEMPOTENCY_KEY_REUSE_CONFLICT"
REASON_BODY_FIELDS = "COMMIT_BODY_TAKES_ONLY_PLAN_VERSION_ID"
REASON_PLAN_NOT_IN_JOURNEY = "PLAN_NOT_IN_JOURNEY"
REASON_NOT_COMMITTABLE = "PLAN_NOT_COMMITTABLE"
REASON_ROUND_IN_FLIGHT = "COMMIT_ROUND_IN_FLIGHT"

#: The words a `replan_proposals` row can hold while its round is still asking.
PROPOSAL_ACTIONABLE_STATUSES = ("GENERATED", "PRESENTED")

#: `select` raises these words; mapping them keeps a screen from learning two vocabularies.
_STALE_PREFIX = "STALE_RECOMPOSE_REQUIRED"
_INFEASIBLE_PREFIX = "is infeasible"
_CANDIDATE_ONLY = "Only a candidate plan can be selected"

_BODY_FIELDS = frozenset({"plan_version_id"})


def _receipt(session: Session, scoped_key: str) -> dict[str, Any] | None:
    """A finished receipt, replayed. An unfinished row is not a receipt and is not hidden."""
    row = session.get(IdempotencyKey, scoped_key)
    if row is None or not row.response_json:
        return None
    receipt = json.loads(row.response_json)
    receipt["idempotency_replay"] = True
    return receipt


def _store_receipt(session: Session, *, scoped_key: str, signature: str,
                   answer: dict[str, Any], status: int) -> None:
    now = datetime.now(timezone.utc)
    session.add(
        IdempotencyKey(
            key=scoped_key,
            operation=COMMIT_OPERATION,
            request_hash=signature,
            response_status=status,
            response_json=json.dumps(answer, sort_keys=True, default=str),
            created_at=now.isoformat(),
            expires_at=(now + timedelta(days=7)).isoformat(),
        )
    )


def _infeasible_failures(detail: str) -> list[str]:
    """Split the gate's own rows out of its sentence; nothing here is invented.

    The shape is written upstream ("PlanVersion <id> is infeasible: " + ", ".join(gate.failures)), and
    each row is a code, optionally with the pair it is about
    (app/replanning/feasibility.py:1013 appends INSUFFICIENT_TRAVEL_GAP:<origin>|<destination>).  A detail
    without that prefix yields no rows, so a screen falls back to its own generic sentence rather than
    guessing at a cause.
    """
    position = detail.find(_INFEASIBLE_PREFIX)
    if position < 0:
        return []
    tail = detail[position + len(_INFEASIBLE_PREFIX):].lstrip(": ")
    return [row.strip() for row in tail.split(",") if row.strip()]


def _refuse_transition(exc: HTTPException) -> HTTPException:
    """Re-shape the transition's refusal into the house envelope, keeping its sentence."""
    detail = str(exc.detail)
    if detail.startswith(_STALE_PREFIX):
        return _refuse(exc.status_code, detail, GATE_STALE_EVIDENCE,
                       {"detail": detail, "gate": GATE_STALE_EVIDENCE})
    if _INFEASIBLE_PREFIX in detail:
        # The reason_code was already on the wire here, and the plan screen ignored it: a traveller who
        # pressed 选用这份方案 was told 这些地点暂时排不成可用方案。回到探索补充或更换地点, which points at
        # the exploration list when the real refusal was 两段安排之间赶路时间不够 -- the thing to move is a
        # time on their own card (trial/results/20261022_v3_human_chrome/walk-84-log.txt:73 against :74).
        # The sentence stays exactly as it was; the gate's rows are added beside it as data.
        return _refuse(exc.status_code, detail, "PLAN_INFEASIBLE",
                       {"detail": detail, "failures": _infeasible_failures(detail)})
    if detail == _CANDIDATE_ONLY:
        return _refuse(exc.status_code, detail, REASON_NOT_COMMITTABLE,
                       {"accepted_statuses": ["CANDIDATE", "SELECTED"]})
    raise exc


@router.post(COMMIT_PATH)
def journey_departure_commit(
    response: Response,
    request: Request,
    journey_id: UUID,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    body: dict | None = None,
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    """Commit the chosen variant as the journey's formal plan, once, for the member who asked."""
    journey, seat = _signed_journey(request, session, journey_id)
    fields = body or {}
    unexpected = sorted(str(name) for name in fields if name not in _BODY_FIELDS)
    if unexpected:
        raise _refuse(
            422,
            "a commit names only the plan version this server already handed out",
            REASON_BODY_FIELDS,
            {"accepted_fields": sorted(_BODY_FIELDS), "refused_fields": unexpected},
        )
    plan_version_id = str(fields.get("plan_version_id") or "")
    if not plan_version_id:
        raise _refuse(422, "plan_version_id is required", REASON_BODY_FIELDS,
                      {"accepted_fields": sorted(_BODY_FIELDS), "missing": ["plan_version_id"]})
    if idempotency_key is None:
        raise _refuse(
            422,
            "a commit needs an Idempotency-Key so a retry cannot apply the same decision twice",
            REASON_KEY_REQUIRED,
            {"header": "Idempotency-Key", "journey_id": journey.id, "rows_protected": True},
        )

    signature = canonical_request_signature({
        "operation": COMMIT_OPERATION,
        "journey_id": journey.id,
        "plan_version_id": plan_version_id,
        "traveler_id": seat["traveler_id"],
    })
    scoped_key = f"{COMMIT_OPERATION}:{idempotency_key}"
    row = session.get(IdempotencyKey, scoped_key)
    if row is not None and row.request_hash != signature:
        raise _refuse(409, "same idempotency key used for a different request", REASON_KEY_CONFLICT,
                      {"journey_id": journey.id, "idempotency_key": idempotency_key})
    replayed = _receipt(session, scoped_key)
    if replayed is not None:
        response.headers["Cache-Control"] = "private, no-store"
        return replayed

    plan = session.get(PlanVersion, plan_version_id)
    if plan is None or plan.journey_id != journey.id:
        # Answered before the transition is entered, so a foreign id cannot probe what select
        # would have said about it.
        raise _refuse(
            404,
            f"PlanVersion {plan_version_id} was not found",
            REASON_PLAN_NOT_IN_JOURNEY,
            {"journey_id": journey.id, "plan_version_id": plan_version_id},
        )

    # A round about this candidate that has not decided is not a suggestion to walk through: the shared
    # plan must stay where it was until the members' round decides (V3's fourth item). "Decided" is the
    # consent door's own word, asked from `app.collective_consent.round_answer` rather than re-derived
    # here, because the rule of who is required and whose answer counts is not this door's to invent. A
    # round that everyone required has approved is answered even when the shipped plan door refused to
    # move the plan -- on a journey that has not departed, `_accept_replan_executing` requires an ACTIVE
    # journey, so the collective path cannot apply and the row stays PRESENTED. Measured on a real socket
    # (`_live_v3_chain_1020ex.txt:15`): refusing there would strand the traveller, who owns the commit
    # door, with a round nobody is still waiting on. A rejected or unanswered round keeps holding it.
    asking = session.scalars(
        select(ReplanProposal)
        .where(ReplanProposal.journey_id == journey.id,
               ReplanProposal.proposed_plan_version_id == plan.id,
               ReplanProposal.status.in_(PROPOSAL_ACTIONABLE_STATUSES))
        .order_by(ReplanProposal.created_at.desc())
    ).all()
    rounds = [round_answer(session, journey, row) for row in asking]
    undecided = [item for item in rounds if not item["fulfilled"]]
    if undecided:
        raise _refuse(
            409,
            "a round is still asking about this plan version, so committing it here would move the "
            "shared plan past the very people the proposal is asking",
            REASON_ROUND_IN_FLIGHT,
            {"journey_id": journey.id, "plan_version_id": plan.id,
             "proposal_ids": [item["proposal_id"] for item in undecided],
             "proposal_statuses": sorted({item["status"] for item in undecided}),
             "rounds": undecided,
             "decided_proposal_ids": [item["proposal_id"] for item in rounds
                                      if item["fulfilled"]],
             "outstanding": True},
        )

    # Imported here, not at module scope: `app.main` imports this module to register the door, so a
    # top-level import would be a circle. The same lazy form `app/agent/gateway.py` uses for every
    # effect it needs out of main.py.
    from app.main import select_plan

    # Named arguments, not positions.  This line's `select_plan` takes a `request` before its
    # `session` (`app/main.py:18029`), while the line this door was written on took only the session,
    # so the positional form bound this door's session to `request` and left `session` on its
    # `Depends` default -- the transition then died on `'Depends' object has no attribute 'scalar'`.
    # Handing over the door's own `Request` is also the honest shape: the plan door gets to run its
    # `JOURNEY_UPDATE` check against the same credentials the traveller actually presented, instead
    # of being handed a session with no principal and having to skip that check.
    try:
        committed = select_plan(UUID(journey.id), UUID(plan_version_id),
                                 request=request, session=session)
    except HTTPException as exc:
        session.rollback()
        raise _refuse_transition(exc) from exc

    record_audit(
        session,
        action=COMMIT_ACTION,
        entity_type="PlanVersion",
        entity_id=plan_version_id,
        journey_id=journey.id,
        before={"traveler_id": seat["traveler_id"], "seat": seat,
                "active_plan_version_id": journey.active_plan_version_id},
        after={"plan_status": plan.status, "committed_plan_version_id": plan_version_id},
        actor_type="traveler",
        actor_id=seat["traveler_id"],
    )
    answer = {
        "journey_id": journey.id,
        "plan_version_id": plan_version_id,
        "committed_by": seat["traveler_id"],
        "seat": seat,
        "idempotency_key": scoped_key,
        "decision_action": COMMIT_ACTION,
        "committed_at": datetime.now(timezone.utc).isoformat(),
        "journey": committed.model_dump(mode="json"),
    }
    _store_receipt(session, scoped_key=scoped_key, signature=signature, answer=answer, status=200)
    session.commit()
    response.headers["Cache-Control"] = "private, no-store"
    response.headers["Vary"] = "Authorization, X-CityNexus-Traveler-Token"
    return answer
