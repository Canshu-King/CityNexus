"""One traveller's explicit, recorded decision about prices nobody could verify.

The sprint's second baton (`trial/tasks/20261023_QODER_AMAP_TO_JOURNEY_PRODUCT_SPRINT.md`) asks for
exactly this and nothing more: measured over the walked city's own catalogue, no wired source answers
admission price -- 72 AMap rows there and 0 of them carry cost evidence
(trial/results/20261022_v3_human_chrome/departure-price-evidence-probe-1.txt:16) -- and AMap's
`business.cost` is a per-person spend figure that appears for restaurants
(trial/results/20261022_v3_human_chrome/amap-business-fields-1.txt:38), never as a ticket price, so it
is not usable here.  A candidate whose price is unknown was therefore unselectable with no operation on
the screen at all.

What this door does, and what it refuses to do:

* It writes the state the product already defines and the authority function already reads --
  `COST_UNKNOWN_ACCEPTED` plus `USER_ACCEPTS_UNKNOWN_PRICE_NOT_INCLUDED` (`app/services.py:605`, `:606`,
  consumed at `:771`) -- through a signed, idempotent, plan-version-bound action.  It does not copy the
  generic-composition branch that sets the same state, because that branch is scoped to its own
  bootstrap scene.
* It is a statement about money only.  Opening hours, place identity, walked hops, calendar conflicts
  and collective consent keep blocking as before: the answer this route reports is computed by the same
  server rule selection goes through, and `unknown_cost_included` stays false so no screen can read
  "the budget is safe" out of it.
* It belongs to the one saved candidate.  Saving a new version starts without an acknowledgement, which
  is why the traveller confirms again instead of having the decision inherited.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agent.goal_tasks import _require_task
from app.commerce.idempotency import canonical_request_signature
from app.concurrency_guards import journey_write_lock
from app.core.audit import record_audit
from app.db.models import Activity, IdempotencyKey, Journey, Place, PlanVersion
from app.db.session import get_session
from app.services import (
    COST_UNKNOWN_ACCEPTED,
    COST_UNKNOWN_USER_POLICY,
    _plan_staleness,
    _place_verified_cost,
    plan_authority_blocker,
    plan_unresolved_activity_facts,
)
from app.traveler_principal import member_has_capability, resolve_journey_member_principal

router = APIRouter()
PATH = "/api/v1/journeys/{journey_id}/agent/goal-tasks/{task_id}/plans/{plan_version_id}/accept-unknown-price"


class UnknownPriceRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    # The traveller names what they are accepting; the server re-derives the same list from its own
    # rows and refuses a body that claims a smaller one.
    unknown_place_ids: list[str] = Field(min_length=1, max_length=64)


class UnknownPriceResult(BaseModel):
    journey_id: str
    task_id: str
    plan_version_id: str
    accepted: bool
    unknown_place_ids: list[str]
    unknown_count: int
    known_subtotal_minor: int
    currency: str
    unknown_cost_included: bool
    authority_state: str
    mobility_snapshot_id: str | None
    selectable_after: bool
    blocker_after: str | None
    confirmed_at: str
    idempotency_replay: bool = False


def unknown_price_place_ids(plan: PlanVersion) -> list[str]:
    """The places on this candidate whose price no source answered, read from the plan's own rows."""
    rows: list[str] = []
    for gap in plan_unresolved_activity_facts(plan):
        place_id = str(gap.get("place_id") or "")
        if str(gap.get("kind")) == "ADMISSION_PRICE" and place_id and place_id not in rows:
            rows.append(place_id)
    return rows


def _selectable_now(session: Session, journey: Journey, plan: PlanVersion) -> tuple[bool, str | None]:
    """Ask the server's own rules, so the screen never promises more than selection will allow."""
    activities = list(session.scalars(select(Activity).where(Activity.plan_version_id == plan.id)
                                     .order_by(Activity.sequence_no)))
    places = {place.id: place for place in session.scalars(
        select(Place).where(Place.city_code == journey.city_code))}
    blocker = plan_authority_blocker(plan, places,
                                     used_place_ids=[str(a.place_id or a.city_service_id or "") for a in activities])
    if blocker is not None:
        return False, blocker
    stale, stale_reason = _plan_staleness(plan)
    if stale:
        return False, stale_reason
    if not json.loads(plan.mobility_evidence_json or "{}").get("snapshot_id"):
        return False, "STALE_RECOMPOSE_REQUIRED: no frozen provider evidence"
    return True, None


def accept_unknown_price(session: Session, journey: Journey, task: dict, plan: PlanVersion,
                         traveler_id: str, claimed: list[str]) -> dict:
    unknown = unknown_price_place_ids(plan)
    if not unknown:
        raise HTTPException(422, "NO_UNKNOWN_PRICE_ON_THIS_PLAN")
    if set(claimed) != set(unknown):
        raise HTTPException(409, "UNKNOWN_PRICE_LIST_MISMATCH")
    subtotal = 0
    for activity in session.scalars(select(Activity).where(Activity.plan_version_id == plan.id)):
        place = session.get(Place, str(activity.place_id or "")) if activity.place_id else None
        if place is not None:
            subtotal += _place_verified_cost(place) or 0
    now = datetime.now(timezone.utc)
    explanation = json.loads(plan.explanation_json or "{}")
    explanation.update({
        "authority_state": COST_UNKNOWN_ACCEPTED,
        "cost_unknown_policy": COST_UNKNOWN_USER_POLICY,
        "cost_summary": {
            "known_subtotal_minor": subtotal,
            "unknown_item_count": len(unknown),
            "unknown_place_ids": unknown,
            "unknown_cost_included": False,
            "total_is_not_free": True,
            "accepted_by_traveler_id": traveler_id,
            "accepted_at": now.isoformat(),
        },
    })
    plan.explanation_json = json.dumps(explanation, ensure_ascii=False)
    session.flush()
    selectable, blocker = _selectable_now(session, journey, plan)
    stored = (task.get("prepared_plan") or {}).get("result")
    if isinstance(stored, dict):
        stored["price_unknown_accepted"] = {"plan_version_id": plan.id, "unknown_place_ids": unknown,
                                            "accepted_at": now.isoformat(), "known_subtotal_minor": subtotal,
                                            "currency": plan.currency}
    return {"journey_id": journey.id, "task_id": str(task.get("task_id") or ""), "plan_version_id": plan.id,
            "accepted": True, "unknown_place_ids": unknown, "unknown_count": len(unknown),
            "known_subtotal_minor": subtotal, "currency": plan.currency, "unknown_cost_included": False,
            "authority_state": COST_UNKNOWN_ACCEPTED, "mobility_snapshot_id": plan.mobility_snapshot_id,
            "selectable_after": selectable, "blocker_after": blocker, "confirmed_at": now.isoformat()}


@router.post(PATH, response_model=UnknownPriceResult)
def accept_unknown_price_route(journey_id: UUID, task_id: UUID, plan_version_id: UUID,
                               body: UnknownPriceRequest, request: Request, response: Response,
                               idempotency_key: str = Header(alias="Idempotency-Key", min_length=1, max_length=160),
                               session: Session = Depends(get_session)):
    with journey_write_lock(str(journey_id)):
        _principal, member = resolve_journey_member_principal(request, session, journey_id=str(journey_id))
        journey = session.get(Journey, str(journey_id))
        if journey is None:
            raise HTTPException(404, "Journey not found")
        if member.traveler_id != journey.traveler_id or not member_has_capability(session, member, "JOURNEY_UPDATE"):
            raise HTTPException(403, "Journey owner update required")
        journey, member, mission, intent, task = _require_task(session, journey, member, task_id, require_draft=False)
        signature = canonical_request_signature({"task_id": str(task_id), "plan_version_id": str(plan_version_id),
                                                 "actor": member.id, "unknown_place_ids": sorted(body.unknown_place_ids)})
        key = f"goal.price-accept:{journey.id}:{idempotency_key}"
        existing = session.get(IdempotencyKey, key)
        if existing:
            if existing.request_hash != signature:
                raise HTTPException(409, "PRICE_ACCEPT_KEY_REUSE_CONFLICT")
            response.headers["Cache-Control"] = "private, no-store"
            return {**json.loads(existing.response_json), "idempotency_replay": True}
        plan = session.get(PlanVersion, str(plan_version_id))
        if plan is None or plan.journey_id != journey.id:
            raise HTTPException(404, "PLAN_NOT_IN_JOURNEY")
        explanation = json.loads(plan.explanation_json or "{}")
        if explanation.get("compose_source") != "SELECTED_GOAL_DRAFT" or \
                str(explanation.get("goal_task_id") or "") != str(mission.id):
            raise HTTPException(403, "PLAN_NOT_FROM_GOAL_TASK_DRAFT")
        answer = accept_unknown_price(session, journey, task, plan, str(member.traveler_id),
                                      body.unknown_place_ids)
        answer["task_id"] = str(mission.id)
        mission.intent_json = json.dumps(intent, ensure_ascii=False)
        now = datetime.now(timezone.utc)
        session.add(IdempotencyKey(key=key, operation="goal.price-accept", request_hash=signature,
                                   response_status=200, response_json=json.dumps(answer, ensure_ascii=False),
                                   created_at=now.isoformat(), expires_at=(now + timedelta(days=7)).isoformat()))
        record_audit(session, action="goal.price.unknown.accepted", entity_type="PlanVersion", entity_id=plan.id,
                     journey_id=journey.id, actor_type="traveler", actor_id=member.traveler_id,
                     after={"task_id": mission.id, "plan_version_id": plan.id,
                            "unknown_count": answer["unknown_count"], "authority_state": COST_UNKNOWN_ACCEPTED,
                            "selectable_after": answer["selectable_after"]})
        session.commit()
        response.headers["Cache-Control"] = "private, no-store"
        response.headers["Vary"] = "Authorization, X-CityNexus-Traveler-Token"
        return answer
