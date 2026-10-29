"""What the hops this plan already measured demand of the hours the traveller chose.

Why this door exists: the freeze step measures a hop and stores its minutes
(:func:`app.agent.goal_route_freeze.freeze_routes`), the selection gate then refuses a plan whose rows
leave less time between two stops than that hop needs
(``backend/app/replanning/feasibility.py:1013``), and all the traveller got was the sentence
「两段安排之间留的赶路时间不够」 with nothing to press about it.  This door answers the question that
sentence implies -- which row has to move, by how much, because of which hop -- and writes nothing.

Applying the answer stays the traveller's own action.  The card sends the proposed rows back through the
same door that saved the plan the first time (``backend/app/agent/goal_preparation.py:141``), which
writes a new ``CANDIDATE`` version and replies ``selected: false, activated: false``, so the plan in
force is never altered behind their back and the 422 feasibility gate stays exactly as binding as it was.

Two id namespaces are kept apart on purpose.  A frozen fact is keyed by the canonical Place row id
(``backend/app/agent/goal_route_freeze.py:371`` writes ``origin.id`` / ``destination.id``), while the
freeze *answer* the client holds keys its edges by the provider's candidate id (``_candidate_id_for``,
same file, :200).  An id-only join across those two silently matches nothing, so this door reads the
rows the plan itself owns and never asks the browser to make that join.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agent.goal_tasks import _require_task
from app.db.models import Activity, Journey, PlanVersion
from app.db.session import get_session
from app.traveler_principal import member_has_capability, resolve_journey_member_principal

router = APIRouter()
PATH = "/api/v1/journeys/{journey_id}/agent/goal-tasks/{task_id}/plans/{plan_version_id}/travel-gaps"

# The latest hour the draft door itself is willing to write (frontend/src/trial/mobile/
# DraftDepartureCard.tsx:49 caps a seeded start at 22), so a proposal that runs past it is refused
# rather than offered: pushing a traveller's evening off the clock the product cannot represent is not
# a re-arrangement, it is a different problem.
LAST_PRACTICAL_HOUR = 22


class TravelGapHop(BaseModel):
    model_config = ConfigDict(extra="forbid")
    origin_title: str
    destination_title: str
    planned_gap_minutes: int | None
    required_minutes: int | None
    short_by_minutes: int
    spans_night: bool
    provider: str | None = None
    reason_code: str | None = None


class TravelGapRow(BaseModel):
    model_config = ConfigDict(extra="forbid")
    day_index: int
    slot_index: int
    title: str
    planned_start: str
    planned_end: str
    proposed_start: str
    proposed_end: str
    extra_minutes: int
    direct_cause: bool


class TravelGapAnswer(BaseModel):
    model_config = ConfigDict(extra="forbid")
    journey_id: str
    task_id: str
    plan_version_id: str
    frozen: bool
    hops: list[TravelGapHop]
    rows: list[TravelGapRow]
    reason_code: str | None = None


def _moment(value: object) -> datetime | None:
    """Read the hour a row stores as text; an unreadable one is *no* hour, never an invented one.

    ``Activity.start_at`` and ``end_at`` are text columns (``backend/app/db/models.py:1483``), which is
    the same shape that once crashed the transit arm of the freeze door, so the conversion lives here
    rather than at each call site.
    """
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def _hhmm(moment: datetime) -> str:
    return moment.strftime("%H:%M")


def travel_gap_answer(task: dict, plan: PlanVersion, rows: list[Activity]) -> dict:
    """Compare each hop's measured minutes with the gap the plan left, and shift the least that fits."""
    evidence = json.loads(plan.mobility_evidence_json or "{}")
    facts = {(str(fact.get("origin_key")), str(fact.get("destination_key"))): fact
             for fact in (evidence.get("facts") or []) if isinstance(fact, dict)}
    placed = [row for row in rows if row.place_id]
    if not facts:
        return {"hops": [], "rows": [], "frozen": False, "reason_code": "MOBILITY_NOT_FROZEN"}

    hops: list[dict] = []
    # A shift is carried per calendar day: the gate pairs consecutive stops within the chain, so
    # moving one row has to move everything after it that same day or the shortfall just lands on the
    # next hop.
    carried: dict[str, timedelta] = {}
    shift_by_sequence: dict[int, tuple[timedelta, bool]] = {}
    blocked: str | None = None

    for previous, current in zip(placed, placed[1:]):
        if previous.place_id == current.place_id:
            continue
        origin_end, current_start, current_end = (_moment(previous.end_at), _moment(current.start_at),
                                                  _moment(current.end_at))
        if origin_end is None or current_start is None or current_end is None:
            hops.append({"origin_title": previous.title, "destination_title": current.title,
                         "planned_gap_minutes": None, "required_minutes": None, "short_by_minutes": 0,
                         "spans_night": False, "reason_code": "PLAN_HOUR_UNREADABLE"})
            continue
        day = str(current_start.date())
        moved = carried.get(day, timedelta(0))
        gap = int((current_start + moved - origin_end).total_seconds() // 60)
        same_day = origin_end.date() == current_start.date()
        fact = facts.get((str(previous.place_id), str(current.place_id)))
        required = fact.get("minutes") if fact else None
        if required is None:
            hops.append({"origin_title": previous.title, "destination_title": current.title,
                         "planned_gap_minutes": gap, "required_minutes": None, "short_by_minutes": 0,
                         "spans_night": not same_day, "reason_code": "MOBILITY_FACT_MISSING_FOR_HOP"})
            continue
        short_by = max(0, int(required) - gap)
        hops.append({"origin_title": previous.title, "destination_title": current.title,
                    "planned_gap_minutes": gap, "required_minutes": int(required),
                    "short_by_minutes": short_by, "spans_night": not same_day,
                    "provider": fact.get("provider")})
        if short_by <= 0:
            continue
        if not same_day:
            # A link that closes one day and opens the next is not fixed by sliding an evening later;
            # saying so is the honest answer here, not a silent no-op.
            blocked = blocked or "OVERNIGHT_HOP_NEEDS_DECISION"
            continue
        candidate = moved + timedelta(minutes=short_by)
        last_end = current_end + candidate
        if (last_end.hour, last_end.minute) > (LAST_PRACTICAL_HOUR, 0):
            blocked = blocked or "DAY_WOULD_RUN_PAST_22:00"
            continue
        carried[day] = candidate
        shift_by_sequence[current.sequence_no] = (candidate, True)
        for later in placed:
            later_start = _moment(later.start_at)
            if later_start is None or later.sequence_no <= current.sequence_no or str(later_start.date()) != day:
                continue
            existing = shift_by_sequence.get(later.sequence_no)
            if existing is None or existing[1] is False:
                shift_by_sequence[later.sequence_no] = (candidate, False)

    schedule = [row for row in ((task.get("prepared_plan") or {}).get("schedule") or [])]
    out_rows: list[dict] = []
    unaligned = 0
    for row in placed:
        entry = shift_by_sequence.get(row.sequence_no)
        if entry is None:
            continue
        wanted, direct = entry
        start, end = _moment(row.start_at), _moment(row.end_at)
        stamp = schedule[row.sequence_no - 1] if 0 < row.sequence_no <= len(schedule) else None
        # The saved schedule is indexed in row order; if the hour on the row does not agree with the
        # hour the card sent, the two lists are not the same plan and no row gets to be guessed.
        if not isinstance(stamp, dict) or start is None or str(stamp.get("start_time")) != _hhmm(start):
            unaligned += 1
            continue
        out_rows.append({"day_index": int(stamp["day_index"]), "slot_index": int(stamp["slot_index"]),
                         "title": row.title, "planned_start": _hhmm(start), "planned_end": _hhmm(end),
                         "proposed_start": _hhmm(start + wanted), "proposed_end": _hhmm(end + wanted),
                         "extra_minutes": int(wanted.total_seconds() // 60), "direct_cause": direct})
    reason = blocked
    if reason is None and unaligned and not out_rows:
        reason = "SCHEDULE_ALIGNMENT_UNVERIFIED"
    return {"hops": hops, "rows": [] if blocked else out_rows, "frozen": True, "reason_code": reason}


@router.get(PATH, response_model=TravelGapAnswer)
def read_travel_gaps(journey_id: UUID, task_id: UUID, plan_version_id: UUID, request: Request,
                     response: Response, session: Session = Depends(get_session)):
    """Ask what the measured hops demand.  Nothing here opens a write lock, because nothing writes."""
    _principal, member = resolve_journey_member_principal(request, session, journey_id=str(journey_id))
    journey = session.get(Journey, str(journey_id))
    if journey is None:
        raise HTTPException(404, "Journey not found")
    if member.traveler_id != journey.traveler_id or not member_has_capability(session, member, "JOURNEY_UPDATE"):
        raise HTTPException(403, "Journey owner update required")
    journey, member, mission, _intent, task = _require_task(session, journey, member, task_id, require_draft=False)
    plan = session.get(PlanVersion, str(plan_version_id))
    if plan is None or plan.journey_id != journey.id:
        raise HTTPException(404, "PLAN_NOT_IN_JOURNEY")
    explanation = json.loads(plan.explanation_json or "{}")
    if explanation.get("compose_source") != "SELECTED_GOAL_DRAFT" or \
            str(explanation.get("goal_task_id") or "") != str(mission.id):
        # This door reads the hops this task saved; it must not be able to describe somebody else's
        # plan version as if it were the traveller's own.
        raise HTTPException(403, "PLAN_NOT_FROM_GOAL_TASK_DRAFT")
    rows = list(session.scalars(select(Activity).where(Activity.plan_version_id == plan.id)
                                .order_by(Activity.sequence_no)))
    answer = travel_gap_answer(task, plan, rows)
    response.headers["Cache-Control"] = "private, no-store"
    response.headers["Vary"] = "Authorization, X-CityNexus-Traveler-Token"
    return {"journey_id": journey.id, "task_id": str(mission.id), "plan_version_id": plan.id, **answer}
