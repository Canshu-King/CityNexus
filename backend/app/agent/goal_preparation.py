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
from app.agent.goal_artifacts import goal_research_lead
from app.commerce.idempotency import canonical_request_signature
from app.concurrency_guards import journey_write_lock
from app.core.audit import record_audit
from app.db.models import Activity, IdempotencyKey, Journey, Place, PlanVersion
from app.db.session import get_session
from app.services import _place_verified_cost, _place_window
from app.traveler_principal import member_has_capability, resolve_journey_member_principal

router = APIRouter()
PATH = "/api/v1/journeys/{journey_id}/agent/goal-tasks/{task_id}/prepare-plan"

# The four answers a to-do line can honestly give a traveller.  Names of operations, not sentences:
# the screen owns the wording (frontend/src/trial/mobile/departureGaps.ts is the single writer),
# and a code is only offered when the door it points at exists on this card.
ASK_AGENT_TO_FIND_PLACE = "ASK_AGENT_TO_FIND_PLACE"
ASK_AGENT_FOR_PLACE_FACT = "ASK_AGENT_FOR_PLACE_FACT"
ASK_AGENT_TO_MEASURE_HOP = "ASK_AGENT_TO_MEASURE_HOP"
PRICE_HELD_BY_TRAVELLER = "PRICE_HELD_BY_TRAVELLER"


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
        rows, gaps, total = [], [], 0
        previous_end = None
        for number, stamp in enumerate(body.schedule, 1):
            date, slot = slots[(stamp.day_index, stamp.slot_index)]
            start = datetime.fromisoformat(f"{date}T{stamp.start_time}").replace(tzinfo=zone)
            end = datetime.fromisoformat(f"{date}T{stamp.end_time}").replace(tzinfo=zone)
            if end <= start or (previous_end and start < previous_end) or start < window_start or end > window_end:
                raise HTTPException(422, "SCHEDULE_OVERLAP_OR_OUTSIDE_JOURNEY")
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
            if place is None:
                missing.append("SOURCE_IDENTITY" if source_id else "PLACE_REQUIRED")
            if place is None or _place_window(place) is None:
                missing.append("OPENING_HOURS")
            cost = _place_verified_cost(place) if place else None
            if cost is None:
                missing.append("ADMISSION_PRICE")
            hop: dict | None = None
            if number > 1 and slots[indices[number - 2]][0] == date:
                # This line used to append TRANSFER_ROUTE unconditionally for every same-day pair, so
                # the traveller's to-do complained about hops the Agent had already had AMap route.
                # Measured in the walked journey (trial/results/20261022_v3_human_chrome/
                # research-routes-in-walked-journey-1.txt): five same-day hops, four of them carrying a
                # real provider route (3385 m / 2708 s and friends), and the screen named all five as
                # missing.  The routes the task acquired live in task["research_routes"]
                # (backend/app/agent/goal_amap.py:210), keyed by these very place ids, so the to-do can
                # now point at the hop that genuinely has no evidence -- and nothing here changes
                # whether a candidate is selectable, which services.py decides elsewhere.
                previous_slot = slots[indices[number - 2]][1]
                previous_source = str(previous_slot.get("place_id") or "")
                hop = next((row for row in task.get("research_routes") or []
                            if isinstance(row, dict) and row.get("from_place_id") == previous_source
                            and row.get("to_place_id") == source_id), None)
                if hop is None:
                    missing.append("TRANSFER_ROUTE")
            metadata = {"goal_task_id": mission.id, "draft_revision": body.expected_revision,
                        "source_candidate_id": source_id or None, "time_basis": "USER_CONFIRMED_SCHEDULE",
                        "cost_evidence": {"status": "UNKNOWN", "amount_minor": None}, "cost_status": "UNKNOWN",
                        "price_known": cost is not None, "cost_included_in_total": cost is not None,
                        "draft_notes": str(slot.get("notes") or ""), "preparation_gaps": missing}
            if hop is not None:
                metadata["transfer_route"] = {key: hop.get(key) for key in
                    ("from_place_id", "to_place_id", "from_name", "to_name", "provider",
                     "distance_m", "duration_seconds", "captured_at", "source_url")}
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
                else:
                    resolution = ASK_AGENT_FOR_PLACE_FACT
                gaps.append({"sequence_no": number, "title": slot["title"], "kind": kind,
                             "place_id": source_id or None, "status": "UNKNOWN",
                             "resolution": resolution})
            total += cost or 0
            rows.append((slot, place, start, end, cost, metadata))
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
            session.add(Activity(id=str(uuid4()), plan_version_id=plan.id, sequence_no=number,
                                 activity_type="SIGHTSEE", title=slot["title"], place_id=place.id if place else None,
                                 start_at=start.isoformat(), end_at=end.isoformat(), travel_from_prev_min=0,
                                 estimated_cost_minor=cost or 0, currency=journey.budget_currency, status="PLANNED", locked=False,
                                 metadata_json=json.dumps(metadata, ensure_ascii=False), created_at=now.isoformat(), updated_at=now.isoformat()))
        answer = {"journey_id": journey.id, "task_id": mission.id, "draft_revision": body.expected_revision,
                  "plan_version_id": plan.id, "status": "CANDIDATE", "selected": False, "activated": False,
                  "slots_count": len(rows), "gaps": gaps, "mobility_frozen": False}
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
