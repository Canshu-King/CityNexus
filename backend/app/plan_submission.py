"""Offer a CANDIDATE plan version to the people on this journey without applying it to anyone.

The V3 order's third item asks for "submit-without-applying candidates": a plan the traveller chose has
to become something the other members can be asked about, and the shared plan must stay exactly where it
was until their round decides (which is what `app.collective_consent` then enforces). Today the only way
a `replan_proposals` row exists is the shipped generator reacting to an event, so a hand-built candidate
-- including the one `POST /api/v1/journeys/{journey_id}/plans/from-slots` writes -- has no way to reach
a round. This door is that missing half-inch of bridge, and it reuses the domain rows that already exist:
no migration.

What it stores, and who judged each of it -- nothing here is asserted by this module:

* `status` -- `PRESENTED`, the shipped word for a proposal that is asking;
* `hard_constraints_passed` -- `app.services.validate_plan_feasibility`, the same gate `select` runs, and
  its failure codes ride in the answer and in `explanation_json`. That gate does not soften a plan with no
  frozen mobility evidence: it raises `STALE_RECOMPOSE_REQUIRED`, so the stored word for such a candidate
  is not-passed with `gate.judged` false and the gate's own code beside it -- this door never converts a
  refusal into a pass, and never hides one either;
* `locked_commitments_preserved` -- computed: every base slot whose row says `locked` must still be
  carried by the candidate under the same canonical place, otherwise the stored word is false and the
  sequences that were dropped are named;
* `utility_score` / `score_breakdown_json` -- `app.replanning.verified_scoring.score_replan_candidate`,
  fed with counts from the difference below and an envelope built by `app.main._envelope_payload` from
  the rows. Preference fit and opportunity value are passed as None, which that scorer documents as the
  neutral value used instead of inventing evidence;
* `diff_json` -- `app.plan_delta.delta_of`, the same arithmetic the delta read door answers with, so the
  Guardian's own readers (`cost_delta_minor`, `end_time_delta_min`) and this door cannot disagree;
* `trigger_event_id`, `recovery_epoch_id` -- null: a hand-built candidate was not triggered by an event
  and does not belong to a recovery epoch, and this door does not manufacture either.

Refusals, each named: no seat; that version is not on this journey; the journey has no active plan to be
a base against; the candidate is not `CANDIDATE` (an ACTIVE or SUPERSEDED row is not a proposal); base
and candidate being the same row, which the shipped DDL also forbids; the two sides not sharing one
currency, because a mixed pair has no `cost_delta_minor` for the Guardian's bounds to read; this pair
already being PRESENTED; a missing `Idempotency-Key`; and a body carrying fields (everything is read from
rows, so a caller cannot supply a judgement).

What it never does: it does not move `journeys.active_plan_version_id`, does not select, start or
activate, does not touch a `plan_versions.status`, does not reach a provider (asserted from this module's
own syntax tree), and does not write a sentence destined for a screen -- `explanation_json` holds codes.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Header, Request, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.commerce.idempotency import canonical_request_signature
from app.core.audit import record_audit
from app.db.models import Activity, IdempotencyKey, PlanVersion, ReplanProposal
from app.db.session import get_session
from app.departure_facts import REASON_PLAN_NOT_IN_JOURNEY
from app.departure_read import _refuse, _signed_journey
from app.plan_delta import delta_of
from app.replanning.verified_scoring import score_replan_candidate
from app.services import validate_plan_feasibility

router = APIRouter()

SUBMISSION_PATH = "/api/v1/journeys/{journey_id}/plans/{plan_version_id}/submission"
SUBMISSION_OPERATION = "plan.candidate_submission"
STATUS_PRESENTED = "PRESENTED"
CANDIDATE_STATUS = "CANDIDATE"
ACTIONABLE_STATUSES = ("GENERATED", "PRESENTED")
FAMILY = "MANUAL_SUBMISSION"

REASON_KEY_REQUIRED = "SUBMISSION_IDEMPOTENCY_KEY_REQUIRED"
REASON_KEY_CONFLICT = "SUBMISSION_IDEMPOTENCY_KEY_REUSE_CONFLICT"
REASON_BODY = "SUBMISSION_READS_EVERYTHING_FROM_ROWS"
REASON_NOT_CANDIDATE = "SUBMISSION_NEEDS_A_CANDIDATE_VERSION"
REASON_NO_BASE = "SUBMISSION_JOURNEY_HAS_NO_ACTIVE_PLAN"
REASON_SAME = "SUBMISSION_BASE_IS_THE_CANDIDATE"
REASON_CURRENCY = "SUBMISSION_NEEDS_ONE_CURRENCY"
REASON_ALREADY = "SUBMISSION_ALREADY_PRESENTED"

#: The consent door's own path template, kept here so the two halves of the round name each other.
CONSENT_PATH = "/api/v1/journeys/{journey_id}/replan-proposals/{proposal_id}/consent"


def _locked_preserved(session: Session, base: PlanVersion,
                      candidate: PlanVersion) -> tuple[bool, list[int]]:
    """Every locked slot of the base, still carried by the candidate under the same canonical place.

    `activities.locked` is the shipped flag; a lock that vanishes from the candidate is reported as
    unpreserved rather than smoothed over, because the column this feeds
    (`replan_proposals.locked_commitments_preserved`) is a NOT NULL claim.
    """
    carried = {
        str(row.place_id or "")
        for row in session.scalars(
            select(Activity).where(Activity.plan_version_id == candidate.id)
        ).all()
    }
    dropped = [
        int(row.sequence_no)
        for row in session.scalars(
            select(Activity)
            .where(Activity.plan_version_id == base.id, Activity.locked.is_(True))
            .order_by(Activity.sequence_no)
        ).all()
        if str(row.place_id or "") not in carried
    ]
    return not dropped, dropped


def _currencies(session: Session, *plan_ids: str) -> list[str]:
    rows = session.execute(
        select(Activity.currency).where(Activity.plan_version_id.in_(list(plan_ids))).distinct()
    ).all()
    return sorted({str(row[0]) for row in rows})


def _open_proposal(session: Session, journey_id: str, base_id: str,
                   proposed_id: str) -> ReplanProposal | None:
    return session.scalars(
        select(ReplanProposal)
        .where(ReplanProposal.journey_id == journey_id,
               ReplanProposal.base_plan_version_id == base_id,
               ReplanProposal.proposed_plan_version_id == proposed_id,
               ReplanProposal.status.in_(ACTIONABLE_STATUSES))
        .order_by(ReplanProposal.created_at.desc())
    ).first()


def _gate_verdict(session: Session, journey, candidate: PlanVersion) -> dict[str, Any]:
    """The shipped feasibility gate's own answer, including the way it refuses to give one.

    `app.services.validate_plan_feasibility` does not return a soft failure for a plan whose frozen
    mobility evidence is missing or stale -- it raises with a code (`STALE_RECOMPOSE_REQUIRED: …`), which
    is the same wall the select door and the consent round already hit. `app.departure_read` records that
    refusal as "not judged" rather than as a pass, and this door does too: the 0/1 column
    `replan_proposals.hard_constraints_passed` cannot hold a null, so an unjudged candidate stores the
    conservative word (not passed) and the gate's own code travels with it. Nothing here turns a refusal
    into a pass, and nothing hides it: `gate.judged` false is in the answer and in `explanation_json`.
    """
    try:
        gate = validate_plan_feasibility(session, journey, candidate)
    except (ValueError, TypeError) as refused:
        text = str(refused)
        return {
            "judged": False,
            "passed": False,
            "failures": [],
            "refusal_code": text.split(":", 1)[0].strip() or type(refused).__name__,
            "refusal_detail": text,
        }
    return {
        "judged": True,
        "passed": bool(gate.passed),
        "failures": [str(item) for item in gate.failures],
        "refusal_code": None,
        "refusal_detail": None,
    }


@router.post(SUBMISSION_PATH, status_code=201)
def journey_plan_submission(
    response: Response,
    request: Request,
    journey_id: UUID,
    plan_version_id: UUID,
    body: dict[str, Any],
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    """Present this CANDIDATE version to the journey's members; change nothing else."""
    journey, seat = _signed_journey(request, session, journey_id)
    if body:
        raise _refuse(422, "a submission takes its facts from rows, not from a body", REASON_BODY,
                      {"unexpected_fields": sorted(body)})
    if not idempotency_key:
        raise _refuse(422, "a submission writes a proposal, so a retry needs a key",
                      REASON_KEY_REQUIRED, {"header": "Idempotency-Key"})

    candidate = session.get(PlanVersion, str(plan_version_id))
    if candidate is None or candidate.journey_id != journey.id:
        raise _refuse(404, f"PlanVersion {plan_version_id} was not found on this journey",
                      REASON_PLAN_NOT_IN_JOURNEY,
                      {"journey_id": journey.id, "plan_version_id": str(plan_version_id)})
    base_id = str(journey.active_plan_version_id or "")
    if not base_id:
        raise _refuse(409, "this journey has no active plan version to differ from", REASON_NO_BASE,
                      {"journey_id": journey.id})
    if base_id == candidate.id:
        # Named before the CANDIDATE rule: a caller pressing the active version made a pair mistake, and
        # that is the truer answer than "this row is not a candidate".
        raise _refuse(422, "the active version is not a change against itself", REASON_SAME,
                      {"plan_version_id": candidate.id})
    if candidate.status != CANDIDATE_STATUS:
        raise _refuse(409, "only a CANDIDATE version can be offered", REASON_NOT_CANDIDATE,
                      {"plan_version_id": candidate.id, "status": candidate.status})
    base = session.get(PlanVersion, base_id)
    if base is None or base.journey_id != journey.id:
        raise _refuse(404, f"PlanVersion {base_id} was not found on this journey",
                      REASON_PLAN_NOT_IN_JOURNEY,
                      {"journey_id": journey.id, "which": "base", "plan_version_id": base_id})

    currencies = _currencies(session, base.id, candidate.id)
    if len(currencies) != 1:
        raise _refuse(422, "a submitted difference has to be moneyable in one currency",
                      REASON_CURRENCY, {"currencies": currencies,
                                        "read_from": "activities.currency"})

    #: The key is scoped to this journey and this caller's press, not to the plan version, so a key
    #: reused for a different candidate is a conflict instead of a second silent submission.
    scoped_key = f"plan-submission|{journey.id}|{idempotency_key}"
    signature = canonical_request_signature({"journey_id": journey.id,
                                             "plan_version_id": candidate.id})
    stored = session.get(IdempotencyKey, scoped_key)
    if stored is not None:
        if stored.request_hash != signature:
            raise _refuse(409, "this key already carries another submission", REASON_KEY_CONFLICT,
                          {"header": "Idempotency-Key", "journey_id": journey.id})
        replayed = json.loads(stored.response_json or "{}")
        replayed["idempotency_replay"] = True
        response.status_code = int(stored.response_status or 201)
        return replayed

    already = _open_proposal(session, journey.id, base.id, candidate.id)
    if already is not None:
        raise _refuse(409, "this candidate is already presented to the members", REASON_ALREADY,
                      {"proposal_id": already.id, "status": already.status})

    delta = delta_of(session, journey, base, candidate)
    gate_verdict = _gate_verdict(session, journey, candidate)
    preserved, dropped = _locked_preserved(session, base, candidate)
    from app.main import _envelope_payload

    candidate_rows = list(session.scalars(
        select(Activity).where(Activity.plan_version_id == candidate.id)
        .order_by(Activity.sequence_no)).all())
    envelope = _envelope_payload(journey, candidate_rows,
                                 preserved_commitment_count=len(candidate_rows) - len(dropped))
    score = score_replan_candidate(
        base_activity_count=delta["counts"]["from_slots"],
        moved_count=delta["counts"]["moved"],
        removed_count=delta["counts"]["removed"],
        added_count=delta["counts"]["added"],
        travel_delta_min=_travel_delta(session, base.id, candidate.id),
        budget_amount_minor=journey.budget_amount_minor,
        after_envelope=envelope,
        commitments_preserved=preserved,
    )
    proposal = ReplanProposal(
        id=str(uuid4()),
        journey_id=journey.id,
        trigger_event_id=None,
        base_plan_version_id=base.id,
        proposed_plan_version_id=candidate.id,
        status=STATUS_PRESENTED,
        hard_constraints_passed=gate_verdict["passed"],
        locked_commitments_preserved=preserved,
        utility_score=score.total,
        score_breakdown_json=json.dumps(score.breakdown, sort_keys=True),
        diff_json=json.dumps(_stored_diff(delta, envelope), sort_keys=True, default=str),
        explanation_json=json.dumps({
            "source": FAMILY,
            "submitted_by_traveler_id": seat["traveler_id"],
            "gate_judged": gate_verdict["judged"],
            "gate_failures": gate_verdict["failures"],
            "gate_refusal_code": gate_verdict["refusal_code"],
            "locked_slots_dropped": dropped,
            "currency": currencies[0],
        }, sort_keys=True),
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    session.add(proposal)
    record_audit(
        session, action="plan.candidate_submission.presented", entity_type="replan_proposal",
        entity_id=proposal.id, actor_type="traveler", actor_id=seat["traveler_id"],
        journey_id=journey.id,
        after={"proposal_id": proposal.id, "base_plan_version_id": base.id,
               "proposed_plan_version_id": candidate.id, "status": STATUS_PRESENTED},
    )
    answer = {
        "journey_id": journey.id,
        "proposal_id": proposal.id,
        "base_plan_version_id": base.id,
        "proposed_plan_version_id": candidate.id,
        "base_status": base.status,
        "status": STATUS_PRESENTED,
        "submitted_by_traveler_id": seat["traveler_id"],
        "created_at": proposal.created_at,
        "hard_constraints_passed": gate_verdict["passed"],
        "gate": gate_verdict,
        # The one reason a hand-built candidate cannot be judged today, stated as a flag a screen can
        # branch on instead of re-reading the gate's sentence.
        "evidence_gap": gate_verdict["refusal_code"] == "STALE_RECOMPOSE_REQUIRED",
        "locked_commitments_preserved": preserved,
        "locked_slots_dropped": dropped,
        "currency": currencies[0],
        "utility_score": score.total,
        "score_breakdown": dict(score.breakdown),
        "envelope": envelope,
        "delta": delta,
        "applied": False,
        "shared_plan_updated": False,
        "journey_active_plan_version_id": journey.active_plan_version_id,
        "consent_path": CONSENT_PATH.format(journey_id=journey.id, proposal_id=proposal.id),
        "next_actions": [
            "ask this journey's members through POST " + CONSENT_PATH.format(
                journey_id=journey.id, proposal_id=proposal.id),
            "read what this changes with GET /api/v1/journeys/" + journey.id + "/plans/delta",
        ],
    }
    _store(session, scoped_key=scoped_key, signature=signature, answer=answer)
    session.commit()
    response.status_code = 201
    return answer


def _store(session: Session, *, scoped_key: str, signature: str,
           answer: dict[str, Any]) -> None:
    """Write the replay receipt. `idempotency_keys.expires_at` is NOT NULL in the shipped DDL, so the
    expiry is written here the way the departure commit door writes it -- leaving it out is invisible
    under the ORM's `create_all` and fails the first press against the package schema."""
    now = datetime.now(timezone.utc)
    session.add(
        IdempotencyKey(
            key=scoped_key,
            operation=SUBMISSION_OPERATION,
            request_hash=signature,
            response_status=201,
            response_json=json.dumps(answer, sort_keys=True, default=str),
            created_at=now.isoformat(),
            expires_at=(now + timedelta(days=7)).isoformat(),
        )
    )


def _travel_delta(session: Session, base_id: str, candidate_id: str) -> int:
    """Minutes of declared travel added or removed, summed from the rows on both sides."""
    totals = {}
    for label, plan_id in (("base", base_id), ("candidate", candidate_id)):
        totals[label] = sum(
            int(row.travel_from_prev_min)
            for row in session.scalars(select(Activity).where(
                Activity.plan_version_id == plan_id)).all()
        )
    return totals["candidate"] - totals["base"]


def _stored_diff(delta: dict[str, Any], envelope: dict[str, Any]) -> dict[str, Any]:
    """The delta answer plus the two keys the shipped Guardian reads off `diff_json`.

    `verified_evidence` is deliberately absent: a hand-built candidate carries no generator evidence, and
    `_proposal_mobility_snapshot` answers None for a proposal that names no snapshot -- the honest shape
    is a missing key, not an empty one pretending to be an answer.
    """
    return {
        "candidate_family": FAMILY,
        "counts": delta["counts"],
        "sets": delta["sets"],
        "map_delta": delta["map_delta"],
        "budget_delta": delta["budget_delta"],
        "verified_cost": delta["verified_cost"],
        "duration_delta": delta["duration_delta"],
        "evidence": delta["evidence"],
        "cost_delta_minor": delta["budget_delta"]["delta_minor"] or 0,
        "end_time_delta_min": delta["duration_delta"]["delta_min"],
        "journey_end_slack_min": envelope["journey_end_slack_min"],
        "budget_remaining_minor": envelope["budget_remaining_minor"],
        "read_from": "app.plan_delta.delta_of",
    }
