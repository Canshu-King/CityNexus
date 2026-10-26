"""Preserve the chosen task draft as a candidate; unresolved source leads stay leads.

The schedule is a human confirmation, not an invented opening window. Place facts
come only from existing task-owned canonical rows. No provider, Place promotion,
selection or activation runs through this door.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo
from typing import Literal

from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.agent.goal_tasks import DRAFT_CHANGED_RELOAD, DRAFT_RESEARCH_RUNNING, _require_task, refuse_draft_edit
from app.agent.goal_draft_patch import (
    is_protected_draft_slot,
    protected_draft_slot_markers,
)
from app.agent import goal_opening_date
from app.agent.goal_artifacts import goal_research_lead
from app.commerce.idempotency import canonical_request_signature
from app.concurrency_guards import journey_write_lock
from app.core.audit import record_audit
from app.db.models import Activity, IdempotencyKey, Journey, Place, PlanVersion
from app.db.session import get_session
from app.services import _place_verified_cost, _place_window
from app.traveler_principal import member_has_capability, resolve_journey_member_principal

# Four different things are meant by one code today, and the traveller is told to retry.
SCHEDULE_ROW_RULES = {
    "end_not_after_start": "ITEM_END_NOT_AFTER_ITEM_START",
    "overlaps_previous_item": "ITEM_STARTS_BEFORE_PREVIOUS_ITEM_END",
    "before_journey_start": "ITEM_STARTS_BEFORE_JOURNEY_START",
    "after_journey_end": "ITEM_ENDS_AFTER_JOURNEY_END",
}


def refuse_schedule_row(*, rule: str, sequence_no: int, title: str, date: str, start_time: str,
                        end_time: str, previous_end_time: str | None,
                        journey_start_at: str, journey_end_at: str) -> HTTPException:
    """Name the row that broke a time rule instead of refusing the whole schedule in one word.

    Measured on the walked screen: the card seeds each row's hour from the row's own time-of-day bucket
    (frontend/src/trial/mobile/DraftDepartureCard.tsx:25), so a draft whose buckets are out of order --
    八达岭 morning, 颐和园 afternoon, 天坛 flexible -- arrives as 09:00, 14:00, 11:00 and the door refuses
    the third row (trial/results/20261022_v3_human_chrome/walk-77-window-readback-1.txt:11, with the
    refusal itself at trial/results/20261022_v3_human_chrome/walk-77-log.txt:32).  The screen then said
    「这次未能保存，时间仍留在这里，可以重试。」 -- and a retry of the same numbers cannot succeed.

    `message` keeps its old verbatim value so no existing reader breaks; the rule, the row's position, its
    title and both times ride as the optional attributes the one envelope already supports
    (app/main.py:884).
    """
    refused = HTTPException(422, "SCHEDULE_OVERLAP_OR_OUTSIDE_JOURNEY")
    refused.reason_code = SCHEDULE_ROW_RULES.get(rule, "SCHEDULE_TIME_RULE_REFUSED")  # type: ignore[attr-defined]
    refused.error_details = {  # type: ignore[attr-defined]
        "rule": rule, "sequence_no": sequence_no, "title": title[:80], "date": date,
        "start_time": start_time, "end_time": end_time, "previous_end_time": previous_end_time,
        "journey_start_at": journey_start_at, "journey_end_at": journey_end_at,
    }
    return refused


def validate_draft_date_constraint(*, draft: dict, date: str, slot: dict, start_time: str) -> None:
    """Reject an exact prepared time that violates this date/block's optional lower bound."""
    constraints = draft.get("date_constraints")
    if constraints is None:
        return
    if not isinstance(constraints, dict):
        raise HTTPException(409, "DRAFT_DATE_CONSTRAINTS_INVALID")
    date_constraints = constraints.get(date)
    if date_constraints is None:
        return
    if not isinstance(date_constraints, dict):
        raise HTTPException(409, "DRAFT_DATE_CONSTRAINTS_INVALID")
    period = slot.get("time_of_day")
    block_constraints = date_constraints.get(period)
    if block_constraints is None:
        return
    if not isinstance(block_constraints, dict):
        raise HTTPException(409, "DRAFT_DATE_CONSTRAINTS_INVALID")
    start_not_before = block_constraints.get("start_not_before")
    if start_not_before is None:
        return
    if not isinstance(start_not_before, str) or not re.fullmatch(
        r"(?:[01]\d|2[0-3]):[0-5]\d", start_not_before
    ):
        raise HTTPException(409, "DRAFT_DATE_CONSTRAINTS_INVALID")
    if start_time >= start_not_before:
        return

    protected = is_protected_draft_slot(slot)
    reason_code = (
        "DRAFT_DATE_CONSTRAINT_REQUIRES_USER_CHOICE"
        if protected else "DRAFT_DATE_CONSTRAINT_VIOLATION"
    )
    refused = HTTPException(status_code=409 if protected else 422, detail=reason_code)
    refused.reason_code = reason_code  # type: ignore[attr-defined]
    refused.error_details = {  # type: ignore[attr-defined]
        "date": date,
        "time_of_day": period,
        "title": str(slot.get("title") or "")[:160],
        "start_time": start_time,
        "start_not_before": start_not_before,
        "protected": protected,
        "choice_required": protected,
        "protected_markers": protected_draft_slot_markers(slot) if protected else {},
    }
    raise refused

router = APIRouter()
PATH = "/api/v1/journeys/{journey_id}/agent/goal-tasks/{task_id}/prepare-plan"

# The four answers a to-do line can honestly give a traveller.  Names of operations, not sentences:
# the screen owns the wording (frontend/src/trial/mobile/departureGaps.ts is the single writer),
# and a code is only offered when the door it points at exists on this card.
ASK_AGENT_TO_FIND_PLACE = "ASK_AGENT_TO_FIND_PLACE"
ASK_AGENT_FOR_PLACE_FACT = "ASK_AGENT_FOR_PLACE_FACT"
ASK_AGENT_TO_MEASURE_HOP = "ASK_AGENT_TO_MEASURE_HOP"
PRICE_HELD_BY_TRAVELLER = "PRICE_HELD_BY_TRAVELLER"
# Two more roads for the same date question: the source serves the day but not the hour, or it serves
# neither and the traveller has to move the visit.
ASK_AGENT_TO_MOVE_HOUR = "ASK_AGENT_TO_MOVE_HOUR"
ASK_AGENT_TO_REPLAN_THE_DAY = "ASK_AGENT_TO_REPLAN_THE_DAY"


class SlotTime(BaseModel):
    model_config = ConfigDict(extra="forbid")
    day_index: int = Field(ge=0)
    slot_index: int = Field(ge=0)
    start_time: str = Field(pattern=r"^([01][0-9]|2[0-3]):[0-5][0-9]$")
    end_time: str = Field(pattern=r"^([01][0-9]|2[0-3]):[0-5][0-9]$")


class PrepareDraft(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_revision: int = Field(ge=0)
    schedule: list[SlotTime] = Field(min_length=1)


class PreparationGap(BaseModel):
    sequence_no: int
    title: str
    kind: str
    place_id: str | None
    status: Literal["UNKNOWN"]
    resolution: str
    detail: dict | None = None


class OpeningCheck(BaseModel):
    """What one confirmed stop's own source says about the day the plan puts the traveller there."""

    sequence_no: int
    title: str
    verdict: str
    reason_code: str | None
    window: list[int] | None = None
    defers_to_notice: bool = False
    source_text: str | None = None


class PreparationResult(BaseModel):
    journey_id: str
    task_id: str
    draft_revision: int
    plan_version_id: str
    status: Literal["CANDIDATE"]
    selected: Literal[False]
    activated: Literal[False]
    slots_count: int
    gaps: list[PreparationGap]
    mobility_frozen: Literal[False]
    # Bands the traveller confirmed but nobody has placed yet.  They stay on the plan as notes and in
    # the to-do list; they are not written as routed activities (see the band branch below, whose
    # reason is a measured selection-gate failure, not a style preference).
    unrouted_count: int = 0
    # What the sources actually gave, in minor units, so the card can put 已知费用 ¥X beside the places
    # nobody answered.  Unknown prices are not inside it and nothing here turns them into 0.
    known_subtotal_minor: int = 0
    # One line per placed stop: 当天开放 / 当天来源说闭馆 / 到达时间在开门时间之外 / 那天没有可靠答案.
    opening_checks: list[OpeningCheck] = []
    idempotency_replay: bool = False


@router.post(PATH, status_code=201, response_model=PreparationResult)
def prepare_plan(journey_id: UUID, task_id: UUID, body: PrepareDraft,
                 request: Request, response: Response,
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
        signature = canonical_request_signature({"task_id": str(task_id), "actor": member.id, **body.model_dump()})
        key = f"goal.prepare:{journey.id}:{idempotency_key}"
        existing = session.get(IdempotencyKey, key)
        if existing:
            if existing.request_hash != signature:
                raise HTTPException(409, "PREPARE_KEY_REUSE_CONFLICT")
            response.headers["Cache-Control"] = "private, no-store"
            return {**json.loads(existing.response_json), "idempotency_replay": True}
        _require_task(session, journey, member, task_id, require_draft=True)
        if task.get("status") == "WORKING":
            raise refuse_draft_edit(DRAFT_RESEARCH_RUNNING)
        draft = task.get("draft_artifact") or {}
        if draft.get("revision") != body.expected_revision:
            raise refuse_draft_edit(DRAFT_CHANGED_RELOAD)
        slots = {(di, si): (day["date"], slot) for di, day in enumerate(draft.get("days", []))
                 for si, slot in enumerate(day.get("slots", [])) if str(slot.get("title") or "").strip()}
        indices = [(row.day_index, row.slot_index) for row in body.schedule]
        if len(set(indices)) != len(indices) or set(indices) != set(slots) or not slots:
            raise HTTPException(422, "SCHEDULE_MUST_COVER_THE_SELECTED_DRAFT")
        if indices != sorted(indices):
            raise HTTPException(422, "SCHEDULE_MUST_PRESERVE_DRAFT_ORDER")
        zone = ZoneInfo(journey.timezone)
        window_start, window_end = datetime.fromisoformat(journey.start_at), datetime.fromisoformat(journey.end_at)
        known = set(task.get("candidate_place_ids") or [])
        now = datetime.now(timezone.utc)
        rows, bands, gaps, total = [], [], [], 0
        checks: list[dict] = []
        previous_end = None
        previous_placed: tuple[str, str] | None = None
        for number, stamp in enumerate(body.schedule, 1):
            date, slot = slots[(stamp.day_index, stamp.slot_index)]
            start = datetime.fromisoformat(f"{date}T{stamp.start_time}").replace(tzinfo=zone)
            end = datetime.fromisoformat(f"{date}T{stamp.end_time}").replace(tzinfo=zone)
            validate_draft_date_constraint(
                draft=draft, date=date, slot=slot, start_time=stamp.start_time
            )
            if end <= start or (previous_end and start < previous_end) or start < window_start or end > window_end:
                # The same four conditions as before, in the same order -- only now the answer says which
                # one and for which row, so a screen can point at the item instead of saying "retry".
                rule = ("end_not_after_start" if end <= start else
                        "overlaps_previous_item" if previous_end and start < previous_end else
                        "before_journey_start" if start < window_start else
                        "after_journey_end")
                raise refuse_schedule_row(
                    rule=rule, sequence_no=number, title=str(slot.get("title") or ""), date=str(date),
                    start_time=stamp.start_time, end_time=stamp.end_time,
                    previous_end_time=previous_end.strftime("%H:%M") if previous_end else None,
                    journey_start_at=window_start.isoformat(), journey_end_at=window_end.isoformat())
            previous_end = end
            source_id = str(slot.get("place_id") or "")
            place = session.get(Place, source_id) if source_id in known else None
            if place is not None and place.city_code != journey.city_code:
                raise HTTPException(409, "PLACE_NOT_IN_JOURNEY_CITY")
            lead = goal_research_lead(task, source_id) if source_id and place is None else None
            if source_id and place is None and (lead is None or lead.get("region_status") == "CONFLICT"):
                raise HTTPException(422, "PLACE_NOT_IN_GOAL_TASK_SCOPE")
            if place is None and lead and lead.get("region_status") == "MATCHED":
                # The research step leaves a canonical row behind for every live lead it kept; binding
                # through that id is the shortest honest path. The provider-key lookup stays as the arm
                # for a task whose lead was recorded before that identity existed.
                canonical = str(lead.get("canonical_place_id") or "")
                place = session.get(Place, canonical) if canonical else None
                if place is None:
                    provider, separator, external_id = source_id.partition(":")
                    if separator and provider == lead.get("provider"):
                        # Bind an already held identity by exact provider key, never a name match.
                        place = session.scalar(select(Place).where(Place.provider_key == provider,
                            Place.external_id.in_([external_id, f"{provider}:{external_id}"]),
                            Place.city_code == journey.city_code))
                if place is not None and place.city_code != journey.city_code:
                    raise HTTPException(409, "PLACE_NOT_IN_JOURNEY_CITY")
            missing = []
            on_date: dict | None = None
            date_ask = ASK_AGENT_FOR_PLACE_FACT
            if place is None:
                # One line, one ask.  A band with no venue has no opening window and no ticket to
                # check, so listing 营业时间 and 门票价格 next to it asked the traveller for facts about
                # a place that does not exist yet -- three to-do rows where only 「让 Agent 找这一处」 is
                # actionable.  Once a place is bound, its own unknowns appear as their own rows.
                missing.append("SOURCE_IDENTITY" if source_id else "PLACE_REQUIRED")
            else:
                if _place_window(place) is None:
                    missing.append("OPENING_HOURS")
                if _place_verified_cost(place) is None:
                    missing.append("ADMISSION_PRICE")
                # The same source sentence read against the day the traveller is actually there, and the
                # hour the plan puts them at the door.  An interval list that says "every day" is not
                # evidence about a Monday, so this never inherits that flattening.
                if _place_window(place) is not None:
                    # Only ask the date question when there is a sentence to ask it of: with no opening
                    # fact at all the 营业时间 row above already names the one thing to do, and a second
                    # row about the same absence is noise on the traveller's list.
                    on_date = goal_opening_date.verdict_for_date(
                        json.loads(place.opening_hours_json or "{}"), date, arrival=start.isoformat())
                if on_date is not None:
                    checks.append({"sequence_no": number, "title": slot["title"],
                                   "verdict": on_date["verdict"], "reason_code": on_date["reason_code"],
                                   "window": list(on_date["window"]) if on_date.get("window") else None,
                                   "defers_to_notice": bool(on_date.get("defers_to_notice")),
                                   "source_text": str(on_date.get("source_text") or "")[:200]})
                if on_date is not None and on_date["verdict"] != goal_opening_date.OPEN_ON_DATE:
                    missing.append("DATE_SPECIFIC_OPENING")
                    date_ask = {goal_opening_date.CLOSED_ON_DATE: ASK_AGENT_TO_REPLAN_THE_DAY,
                                goal_opening_date.TIME_OUTSIDE_WINDOW: ASK_AGENT_TO_MOVE_HOUR}.get(
                                    str(on_date["verdict"]), ASK_AGENT_FOR_PLACE_FACT)
            cost = _place_verified_cost(place) if place else None
            hop: dict | None = None
            if source_id and previous_placed is not None and previous_placed[1] != source_id:
                # The hop the traveller is asked about is the hop the *server* will check when they
                # press 选用: the previous stop that actually has a place, whoever it follows.  Two
                # shapes made the old same-day/previous-slot rule wrong.  (1) A band with no venue --
                # 「19:00 晚餐及自由活动」 -- sat between two stops, and the old rule asked for a hop
                # into it, a hop nothing can route.  (2) The next morning's first stop is checked
                # against the previous day's last one (backend/app/replanning/feasibility.py:966 pairs
                # the plan as one chain), and a candidate that never froze that fact is refused at
                # selection with MOBILITY_DATA_UNAVAILABLE -- measured on the walked journey's own
                # saved candidate: trial/results/20261022_v3_human_chrome/selection-gate-replay-1.txt.
                # So the to-do names it when the Agent has no receipt for it, instead of leaving the
                # traveller with a code and no button.
                hop = next((row for row in task.get("research_routes") or []
                            if isinstance(row, dict) and row.get("from_place_id") == previous_placed[1]
                            and row.get("to_place_id") == source_id), None)
                if hop is None:
                    missing.append("TRANSFER_ROUTE")
            metadata = {"goal_task_id": mission.id, "draft_revision": body.expected_revision,
                        "source_candidate_id": source_id or None, "time_basis": "USER_CONFIRMED_SCHEDULE",
                        "cost_evidence": {"status": "UNKNOWN", "amount_minor": None}, "cost_status": "UNKNOWN",
                        "price_known": cost is not None, "cost_included_in_total": cost is not None,
                        "draft_notes": str(slot.get("notes") or ""), "preparation_gaps": missing}
            protected_markers = protected_draft_slot_markers(slot)
            if protected_markers:
                metadata["draft_protection_markers"] = protected_markers
            if hop is not None:
                metadata["transfer_route"] = {key: hop.get(key) for key in
                    ("from_place_id", "to_place_id", "from_name", "to_name", "provider",
                     "distance_m", "duration_seconds", "captured_at", "source_url")}
            if on_date is not None:
                # Carried on the row so the card can quote the sentence this verdict came from, with the
                # day and window it was read against: a label without its source is what the sprint asks
                # to stop shipping.
                metadata["opening_on_date"] = {"verdict": on_date["verdict"], "reason_code": on_date["reason_code"],
                                               "window": on_date["window"], "weekday": on_date["weekday"],
                                               "defers_to_notice": on_date["defers_to_notice"],
                                               "source_text": str(on_date.get("source_text") or "")[:200]}
            if place:
                metadata["cost_status"] = "KNOWN" if cost is not None else "UNKNOWN"
                metadata["cost_evidence"] = json.loads(place.metadata_json or "{}").get("cost_evidence", metadata["cost_evidence"])
                metadata["opening_hours"] = json.loads(place.opening_hours_json or "{}")
            if lead:
                # These remain task-scoped observations, not canonical Place facts.
                metadata["research_source"] = {key: lead.get(key) for key in ("id", "provider", "source_url", "captured_at", "provider_provenance")}
                url = str(lead.get("source_url") or "")
                if re.match(r"^https?://", url):
                    metadata["source_urls"] = [url]
            if place is None:
                # A band the traveller confirmed that has no venue yet -- 「19:00 晚餐及自由活动」.  It
                # stays in the plan as a row they can see and act on, and declares itself unroutable so
                # the feasibility chain is not asked to place it (app/replanning/feasibility.py reads
                # this marker).  Measured on the walked candidate: as an ordinary location-less row it
                # produced LOCATION_MISSING for itself and MOBILITY_CONTEXT_MISSING for the pair it sat
                # in (trial/results/20261022_v3_human_chrome/selection-gate-replay-1.txt), a refusal no
                # button could answer.
                metadata["routing"] = "NOT_ROUTED"
                bands.append({"title": slot["title"], "start_at": start.isoformat()})
            for kind in missing:
                # A to-do line has to say what the traveller can do about it, not only what is
                # missing.  Three of these roads end at the one real button on this card
                # (「和 Agent 补齐出发资料」 asks for the营业、费用与转场 facts item by item); a price
                # the traveller holds themselves ends with them, because measured across this
                # journey's own city no wired source answers admission price
                # (trial/results/20261022_v3_human_chrome/departure-price-evidence-probe-1.txt:
                # 72 amap rows in the city, 0 of them carrying cost evidence).
                if place is None:
                    resolution = ASK_AGENT_TO_FIND_PLACE
                elif kind == "ADMISSION_PRICE":
                    resolution = PRICE_HELD_BY_TRAVELLER
                elif kind == "TRANSFER_ROUTE":
                    resolution = ASK_AGENT_TO_MEASURE_HOP
                elif kind == "DATE_SPECIFIC_OPENING":
                    resolution = date_ask
                else:
                    resolution = ASK_AGENT_FOR_PLACE_FACT
                gaps.append({"sequence_no": number, "title": slot["title"], "kind": kind,
                             # The identity a traveller's decision has to bind to is the canonical Place
                             # row the plan itself uses (backend/app/db/models.py Activity.place_id), not
                             # the spelling the provider handed over.  A consent receipt that named the
                             # provider id would not survive the place being re-researched under a second
                             # source, and nothing else in the plan reads that spelling.
                             "place_id": (place.id if place is not None else None) or source_id or None,
                             "status": "UNKNOWN", "resolution": resolution,
                             # Only the day question carries its own evidence text: 「当天没核实到开放」
                             # without the provider's sentence is a label nobody can check.
                             "detail": ({"verdict": on_date["verdict"], "reason_code": on_date["reason_code"],
                                         "source_text": str(on_date.get("source_text") or "")[:200]}
                                        if kind == "DATE_SPECIFIC_OPENING" and on_date is not None else None)})
            total += cost or 0
            rows.append((slot, place, start, end, cost, metadata))
            if source_id:
                previous_placed = (date, source_id)
        version = int(session.scalar(select(func.max(PlanVersion.version_no)).where(PlanVersion.journey_id == journey.id)) or 0) + 1
        plan = PlanVersion(id=str(uuid4()), journey_id=journey.id, version_no=version,
                           planning_mode=journey.planning_mode, status="CANDIDATE", source="MANUAL",
                           total_cost_minor=total, currency=journey.budget_currency,
                           estimated_duration_min=sum(int((row[3] - row[2]).total_seconds() / 60) for row in rows),
                           explanation_json=json.dumps({"compose_source": "SELECTED_GOAL_DRAFT", "goal_task_id": mission.id,
                               "draft_revision": body.expected_revision, "authority_state": "PROVISIONAL_UNRESOLVED_FACTS",
                               "unresolved_facts": gaps}), created_at=now.isoformat())
        session.add(plan)
        session.flush()
        for number, (slot, place, start, end, cost, metadata) in enumerate(rows, 1):
            protected_markers = metadata.get("draft_protection_markers") or {}
            locked = bool(protected_markers)
            session.add(Activity(id=str(uuid4()), plan_version_id=plan.id, sequence_no=number,
                                 activity_type="SIGHTSEE" if place is not None else "FREE_TIME", title=slot["title"], place_id=place.id if place else None,
                                 start_at=start.isoformat(), end_at=end.isoformat(), travel_from_prev_min=0,
                                 estimated_cost_minor=cost or 0, currency=journey.budget_currency, status="PLANNED", locked=locked,
                                 metadata_json=json.dumps(metadata, ensure_ascii=False), created_at=now.isoformat(), updated_at=now.isoformat()))
        answer = {"journey_id": journey.id, "task_id": mission.id, "draft_revision": body.expected_revision,
                  "plan_version_id": plan.id, "status": "CANDIDATE", "selected": False, "activated": False,
                  "slots_count": len(rows), "unrouted_count": len(bands), "gaps": gaps,
                  "known_subtotal_minor": total, "mobility_frozen": False, "opening_checks": checks}
        task["prepared_plan"] = {"result": answer, "schedule": [row.model_dump() for row in body.schedule]}
        mission.intent_json = json.dumps(intent, ensure_ascii=False)
        session.add(IdempotencyKey(key=key, operation="goal.prepare", request_hash=signature, response_status=201,
                                  response_json=json.dumps(answer, ensure_ascii=False), created_at=now.isoformat(),
                                  expires_at=(now + timedelta(days=7)).isoformat()))
        record_audit(session, action="goal.draft.prepared", entity_type="PlanVersion", entity_id=plan.id,
                     journey_id=journey.id, actor_type="traveler", actor_id=member.traveler_id,
                     after={"task_id": mission.id, "draft_revision": body.expected_revision, "plan_version_id": plan.id})
        session.commit()
        response.headers["Cache-Control"] = "private, no-store"
        response.headers["Vary"] = "Authorization, X-CityNexus-Traveler-Token"
        return answer
