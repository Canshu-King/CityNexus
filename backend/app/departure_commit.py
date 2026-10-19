"""One signed, idempotent write door: the variant a traveller picked becomes the formal plan.

This is the commit step the departure screen needs after `GET .../departure` answers
`NO_PLAN_SELECTED` with `candidates[]` in hand. Everything the transition itself decides --
frozen mobility evidence, feasibility, retiring the previous SELECTED row, moving the cursor,
the single-ACTIVE invariant, the `plan.selected` audit event -- belongs to
`POST /api/v1/journeys/{journey_id}/plans/{plan_version_id}/select` and is *not* re-implemented
here: this door calls that same function in-process, which is what `app/main.py` already does for
the seed supply (`app/main.py:1980`) and the staged advance (`app/main.py:2226`). A second
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
from sqlalchemy.orm import Session

from app.commerce.idempotency import canonical_request_signature
from app.core.audit import record_audit
from app.db.models import IdempotencyKey, PlanVersion
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


def _refuse_transition(exc: HTTPException) -> HTTPException:
    """Re-shape the transition's refusal into the house envelope, keeping its sentence."""
    detail = str(exc.detail)
    if detail.startswith(_STALE_PREFIX):
        return _refuse(exc.status_code, detail, GATE_STALE_EVIDENCE,
                       {"detail": detail, "gate": GATE_STALE_EVIDENCE})
    if _INFEASIBLE_PREFIX in detail:
        return _refuse(exc.status_code, detail, "PLAN_INFEASIBLE", {"detail": detail})
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

    # Imported here, not at module scope: `app.main` imports this module to register the door, so a
    # top-level import would be a circle. The same lazy form `app/agent/gateway.py` uses for every
    # effect it needs out of main.py.
    from app.main import select_plan

    try:
        committed = select_plan(UUID(journey.id), UUID(plan_version_id), session)
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
