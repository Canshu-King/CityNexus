"""Two signed reads that let a traveller's screen say "准备出发" from server facts.

`.../members/me` answers the one question every confirm button needs first: does the caller hold a
seat on this journey right now, of what kind, and until when. `.../departure` answers the next one:
which plan variants this journey actually holds, what the server froze for each, and the single gate
word the screen renders -- so a UI never has to infer "departable" from a status code it guesses at.

The door runs first and every refusal uses a status this product already has: unknown journey 404,
no credentials 401, no seat in force 403 -- all before a plan row is read, so neither the answer nor
the traffic can enumerate another traveller's trip.

A read, never a write. Neither door changes a plan, retires a version, or starts a journey: those
decisions stay with `POST .../plans/{id}/select` and `POST .../start`, whose own predicates these
doors describe. Kept in its own module because every other route lives in `app/main.py`, so a router
here keeps the merge surface at two lines plus one file -- the same reason `place_media_routes` exists.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Activity, Journey, JourneyMember, PlanVersion
from app.db.session import get_session
from app.services import validate_plan_feasibility
from app.traveler_principal import resolve_traveler_principal, member_has_capability

router = APIRouter()

DEPARTURE_PATH = "/api/v1/journeys/{journey_id}/departure"
MEMBER_ME_PATH = "/api/v1/journeys/{journey_id}/members/me"

#: Seat answers. `MEMBER_IN_FORCE` / `MEMBER_LAPSED` / `MEMBER_WITHDRAWN` are the same three words
#: the member list already answers with (`app.main._member_state`); this door adds `OWNER`, which is
#: not a membership row but is a seat, and a screen has to be able to tell the two apart.
SEAT_OWNER = "OWNER"
SEAT_MEMBER = "MEMBER"

#: The one word the screen renders. Every value names what the server actually found; nothing here
#: is a re-labelled error, and `READY_TO_DEPART` is only ever answered after the frozen-evidence and
#: feasibility predicates below both hold.
GATE_READY = "READY_TO_DEPART"
GATE_ALREADY_RUNNING = "ALREADY_RUNNING"
GATE_NO_PLAN = "NO_PLAN_SELECTED"
GATE_STALE_EVIDENCE = "STALE_RECOMPOSE_REQUIRED"
GATE_INFEASIBLE = "PLAN_INFEASIBLE"
GATE_WRONG_STATE = "JOURNEY_NOT_PLANNABLE"

REASON_MEMBER_REQUIRED = "JOURNEY_MEMBER_REQUIRED"
# The two 401 words below are the resolver's own, stamped at :123 on the raw 401 it gets back
# from `app.traveler_principal` -- that module on this line raises the sentence and no code, so
# these two strings had no name and every reader had to retype them. One writer, named here.
REASON_CREDENTIALS_MISSING = "TRAVELER_CREDENTIALS_MISSING"
REASON_CREDENTIALS_INVALID = "TRAVELER_CREDENTIALS_INVALID"


def _refuse(status: int, message: str, reason_code: str, details: dict[str, Any]) -> HTTPException:
    """The house shape for a refusal: a status, a sentence, and the reason code the client reads."""
    refused = HTTPException(status, message)
    refused.reason_code = reason_code  # type: ignore[attr-defined]
    refused.error_details = details  # type: ignore[attr-defined]
    return refused


def _membership_state(member: Any, now: datetime) -> str:
    """The same three-state rule the member list uses, asked of the row not re-decided here.

    `app.main._member_state` is the definition; importing it would pull the whole route module in a
    circle, so this function mirrors it and `test_qoder_departure_read_r1.py` pins the two against the
    same rows. A mirror that is not pinned is a second answer waiting to disagree.
    """
    if getattr(member, "removed_at", None):
        return "MEMBER_WITHDRAWN"
    expires_at = getattr(member, "expires_at", None)
    if expires_at:
        try:
            expires = datetime.fromisoformat(str(expires_at))
        except ValueError:
            return "MEMBER_LAPSED"
        if expires.tzinfo is None or expires <= now:
            return "MEMBER_LAPSED"
    return "MEMBER_IN_FORCE"


def _member_row(session: Session, journey_id: str, traveler_id: str):
    return session.scalars(
        select(JourneyMember).where(
            JourneyMember.journey_id == journey_id,
            JourneyMember.traveler_id == traveler_id,
        )
    ).first()


def seat_of(session: Session, journey: Journey, traveler_id: str,
            now: datetime) -> dict[str, Any]:
    """Does this traveller hold this journey, and as what. One answer, used by both doors."""
    member = _member_row(session, journey.id, traveler_id)
    if str(journey.traveler_id) == traveler_id:
        return {
            "traveler_id": traveler_id,
            "seat_kind": SEAT_OWNER,
            "role": "OWNER",
            "member_id": member.id if member is not None else None,
            "member_state": _membership_state(member, now) if member is not None else "MEMBER_IN_FORCE",
            "expires_at": member.expires_at if member is not None else None,
            "in_force": True,
        }
    if member is None:
        return {"traveler_id": traveler_id, "seat_kind": "NONE", "role": None, "member_id": None,
                "member_state": "NO_MEMBERSHIP", "expires_at": None, "in_force": False}
    state = _membership_state(member, now)
    return {"traveler_id": traveler_id, "seat_kind": SEAT_MEMBER, "role": member.role,
            "member_id": member.id, "member_state": state, "expires_at": member.expires_at,
            "in_force": state == "MEMBER_IN_FORCE"}


def _signed_journey(request: Request, session: Session, journey_id: UUID) -> tuple[Journey, dict]:
    """Credentials, then the journey, then the seat -- in that order, before any plan row is read."""
    try:
        principal = resolve_traveler_principal(request, session)
    except HTTPException as exc:
        if exc.status_code == 401 and not getattr(exc, "reason_code", None):
            missing = not (request.headers.get("Authorization")
                             or request.headers.get("X-CityNexus-Traveler-Token"))
            exc.reason_code = REASON_CREDENTIALS_MISSING if missing else REASON_CREDENTIALS_INVALID
        raise

    journey = session.get(Journey, str(journey_id))
    if journey is None:
        raise HTTPException(404, f"Journey {journey_id} was not found")
    traveler_id = str(principal.traveler_id)
    seat = seat_of(session, journey, traveler_id, datetime.now(timezone.utc))
    if not seat["in_force"]:
        raise _refuse(
            403,
            "this journey is not yours to read",
            REASON_MEMBER_REQUIRED,
            {"journey_id": str(journey_id), "traveler_id": traveler_id, "seat": seat},
        )
    if seat["seat_kind"] != SEAT_OWNER:
        member = _member_row(session, journey.id, traveler_id)
        if member is None or not member_has_capability(session, member, "JOURNEY_READ"):
            raise HTTPException(403, "JOURNEY_READ required")
    return journey, seat


def frozen_evidence_of(plan: PlanVersion) -> dict[str, Any]:
    """What the server actually froze for this version, in the words the select door uses.

    Three facts, no judgement about whether the plan is good: is there a snapshot id, when does it
    expire, and is that instant already past. `STALE_RECOMPOSE_REQUIRED` is the same code the write
    door raises for the same two conditions, so a screen that read the gate and a traveller who then
    pressed confirm get the same word either way.
    """
    payload = json.loads(plan.mobility_evidence_json or "{}")
    snapshot_id = str(payload.get("snapshot_id") or "")
    expires_at = payload.get("expires_at")
    expired: Any = None
    detail = None
    if expires_at:
        try:
            expired = datetime.fromisoformat(str(expires_at)) <= datetime.now(timezone.utc)
        except (ValueError, TypeError):
            expired = None
            detail = "EVIDENCE_TIMESTAMP_INVALID"
    # Exactly what `select` compares, and only where select compares it: a frozen snapshot must be the
    # one the row names. An unfrozen row never reaches this rule -- it stops at EVIDENCE_NOT_FROZEN.
    plan_ref = str(plan.mobility_snapshot_id or "")
    reference_consistent = (plan_ref == snapshot_id) if snapshot_id else True
    return {
        "frozen": bool(snapshot_id),
        "snapshot_id": snapshot_id or None,
        "expires_at": expires_at,
        "expired": expired,
        "reference_consistent": reference_consistent,
        "detail": detail,
    }


def _activity_count(session: Session, plan_id: str) -> int:
    return len(session.scalars(select(Activity.id).where(Activity.plan_version_id == plan_id)).all())


def _candidate_row(session: Session, journey: Journey, plan: PlanVersion) -> dict[str, Any]:
    evidence = frozen_evidence_of(plan)
    verdict: dict[str, Any] = {}
    if evidence["frozen"]:
        try:
            gate = validate_plan_feasibility(session, journey, plan)
            verdict = {"feasible": bool(gate.passed), "failures": list(gate.failures)}
        except (ValueError, TypeError) as exc:
            # The evaluator refuses a plan that does not belong to this journey, and that refusal is
            # content: the screen has to say which plan it could not judge.  Anything else propagates
            # -- a read door that swallows a real bug would hide it behind a calm gate word.
            verdict = {"feasible": None, "failures": [], "detail": type(exc).__name__}
    else:
        verdict = {"feasible": None, "failures": [], "detail": "NOT_EVALUATED_WITHOUT_FROZEN_EVIDENCE"}
    return {
        "plan_version_id": plan.id,
        "version_no": plan.version_no,
        "planning_mode": plan.planning_mode,
        "status": plan.status,
        "source": plan.source,
        "currency": plan.currency,
        "total_cost_minor": plan.total_cost_minor,
        "estimated_duration_min": plan.estimated_duration_min,
        "activities_count": _activity_count(session, plan.id),
        "evidence": evidence,
        "feasibility": verdict,
    }


@router.get(MEMBER_ME_PATH)
def journey_member_me(request: Request, response: Response, journey_id: UUID,
                      session: Session = Depends(get_session)) -> dict[str, Any]:
    """The caller's own seat on this journey, in the three words the member list already uses."""
    journey, seat = _signed_journey(request, session, journey_id)
    response.headers["Cache-Control"] = "private, no-store"
    response.headers["Vary"] = "Authorization, X-CityNexus-Traveler-Token"
    return {
        "journey_id": journey.id,
        "traveler_id": seat["traveler_id"],
        "seat": seat,
        "may_confirm_departure": bool(seat["in_force"] and (member := _member_row(session, journey.id, seat["traveler_id"])) is not None and member_has_capability(session, member, "JOURNEY_EXECUTION_UPDATE")),
    }


@router.get(DEPARTURE_PATH)
def journey_departure(request: Request, response: Response, journey_id: UUID,
                      session: Session = Depends(get_session)) -> dict[str, Any]:
    """One projection: which plans exist, what is frozen for each, and the gate word for this journey."""
    journey, seat = _signed_journey(request, session, journey_id)
    response.headers["Cache-Control"] = "private, no-store"
    response.headers["Vary"] = "Authorization, X-CityNexus-Traveler-Token"
    now = datetime.now(timezone.utc)
    plans = session.scalars(
        select(PlanVersion)
        .where(PlanVersion.journey_id == journey.id)
        .order_by(PlanVersion.version_no.desc(), PlanVersion.id)
    ).all()
    rows = [_candidate_row(session, journey, plan) for plan in plans]
    selected = next((row for row in rows if row["plan_version_id"] == journey.active_plan_version_id and row["status"] in {"SELECTED", "ACTIVE"}), None)
    candidates = [row for row in rows if row["status"] == "CANDIDATE"]

    if journey.status == "ACTIVE":
        gate, reason = GATE_ALREADY_RUNNING, None
    elif journey.status not in {"DRAFT", "PLANNED"}:
        gate, reason = GATE_WRONG_STATE, "JOURNEY_STATUS_" + str(journey.status)
    elif selected is None and not candidates:
        gate, reason = GATE_NO_PLAN, "NO_PLAN_VERSION_ROWS"
    elif selected is None:
        gate, reason = GATE_NO_PLAN, "CANDIDATES_ONLY"
    elif not selected["evidence"]["frozen"]:
        gate, reason = GATE_STALE_EVIDENCE, "EVIDENCE_NOT_FROZEN"
    elif selected["evidence"]["expired"] is True:
        gate, reason = GATE_STALE_EVIDENCE, "EVIDENCE_EXPIRED"
    elif selected["evidence"]["reference_consistent"] is False:
        gate, reason = GATE_STALE_EVIDENCE, "EVIDENCE_REFERENCE_INCONSISTENT"
    elif selected["evidence"]["detail"]:
        gate, reason = GATE_STALE_EVIDENCE, selected["evidence"]["detail"]
    elif selected["feasibility"].get("feasible") is False:
        gate, reason = GATE_INFEASIBLE, ", ".join(selected["feasibility"]["failures"]) or None
    elif selected["feasibility"].get("feasible") is not True:
        gate, reason = GATE_INFEASIBLE, "FEASIBILITY_UNAVAILABLE"
    else:
        gate, reason = GATE_READY, None

    next_action = {
        GATE_READY: {"kind": "select_or_start", "door": f"/api/v1/journeys/{journey.id}/start"},
        GATE_ALREADY_RUNNING: {"kind": "none", "door": None},
        GATE_NO_PLAN: {"kind": "generate_plans", "door": f"/api/v1/journeys/{journey.id}/plans/generate"},
        GATE_STALE_EVIDENCE: {"kind": "recompose", "door": f"/api/v1/journeys/{journey.id}/plans/authoritative-compose"},
        GATE_INFEASIBLE: {"kind": "recompose", "door": f"/api/v1/journeys/{journey.id}/plans/generate"},
        GATE_WRONG_STATE: {"kind": "none", "door": None},
    }[gate]

    return {
        "journey_id": journey.id,
        "journey_status": journey.status,
        "active_plan_version_id": journey.active_plan_version_id,
        "current_activity_id": journey.current_activity_id,
        "seat": seat,
        "gate": gate,
        "reason_detail": reason,
        "selected_plan": selected,
        "candidates": candidates,
        "next_action": next_action,
        "observed_at": now.isoformat(),
    }
