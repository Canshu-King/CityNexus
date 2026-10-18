"""Bounded DRAFT Journey goal tasks backed by the existing Hermes/Gateway tools.

This is deliberately a service layer: signed routes resolve the traveler and
JourneyMember, then pass those verified rows here. A goal task never opens a
RecoveryEpoch, changes Journey status, or activates a plan.
Candidate generation stays separate from selection and activation;
online research is gated by task-scoped consent.
"""

from __future__ import annotations

import json
import re
import time
from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agent.gateway import AgentToolGateway
from app.agent.goal_artifacts import (
    cached_goal_place_sources,
    discover_goal_places,
    discover_nearby_goal_places,
    empty_draft,
    goal_research_lead,
    goal_tool_definitions,
    normalize_draft,
)
from app.agent.goal_adapters import DOMAIN_TOOLS, domain_args, domain_result, compare_stored_routes, route_tool_definition
from app.agent.orchestrator import HermesJourneyAgent
from app.agent.runtime import AgentRuntimeUnavailable
from app.core.audit import record_audit
from app.core.config import settings
from app.db.models import (
    AgentRun,
    AgentRunStep,
    AuditLog,
    Journey,
    JourneyMember,
    JourneyMission,
    PlanVersion,
    Place,
    WebObservation,
)
from app.schemas import AgentToolCall
from app.traveler_principal import _member_is_in_force


GOAL_PLANNING_MODE = "GOAL_PLANNING"
_TASK_KEY = "goal_task"
# The existing Gateway city search is the constrained candidate-to-Place bridge.
# It writes only provider-backed Place/CityService evidence; bootstrap-private
# member-scoped candidates are not promoted by this service.
_ALLOWED_TOOLS = frozenset(
    {"inspect_journey", "search_city_services", "research_place_sources", "discover_places", "discover_nearby_places", "save_draft_itinerary"} | (DOMAIN_TOOLS - {"generate_plans"})
)
_EVENT_ACTION = "agent.goal_task.event"
_MAX_GOAL_LENGTH = 2000
# These are cumulative, opt-in task ceilings, not an eight-turn permanent lock.
# Each continuation is a separate explicit user action with an increased budget.
_MAX_MODEL_TURNS = 64
_MAX_TOOL_CALLS = 128
_MAX_EVENT_PAGE = 100
_REASON_CODE = re.compile(r"^[A-Z][A-Z0-9_]{1,79}$")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _json_load(raw: str | None, fallback: Any) -> Any:
    try:
        return json.loads(raw or "")
    except (TypeError, ValueError):
        return fallback


def _json_dump(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _require_owner_scope(
    session: Session,
    journey: Journey,
    member: JourneyMember,
    *,
    require_draft: bool,
) -> tuple[Journey, JourneyMember]:
    current_journey = session.get(Journey, str(getattr(journey, "id", "")))
    current_member = session.get(JourneyMember, str(getattr(member, "id", "")))
    if current_journey is None or current_member is None:
        raise HTTPException(404, "goal task Journey or member was not found")
    # The model/provider can take seconds. Re-read authority before each next action.
    session.refresh(current_journey)
    session.refresh(current_member)
    if (
        str(getattr(member, "journey_id", "")) != str(current_journey.id)
        or str(current_member.journey_id) != str(current_journey.id)
        or str(getattr(member, "traveler_id", "")) != str(current_member.traveler_id)
        or str(current_member.traveler_id) != str(current_journey.traveler_id)
        or not _member_is_in_force(current_member)
    ):
        raise HTTPException(403, "goal tasks require the in-force Journey owner")
    if require_draft:
        if str(current_journey.status).upper() != "DRAFT" or current_journey.active_plan_version_id:
            raise HTTPException(409, "GOAL_TASK_REQUIRES_DRAFT_JOURNEY")
        # An unselected candidate is an output to improve, not a reason to stop research.
        existing_plan_id = session.scalar(
            select(PlanVersion.id).where(PlanVersion.journey_id == current_journey.id,
                                         PlanVersion.status != "CANDIDATE").limit(1)
        )
        if existing_plan_id is not None:
            raise HTTPException(409, "GOAL_TASK_REQUIRES_DRAFT_WITHOUT_SELECTED_PLAN")
    return current_journey, current_member


def _task_state(mission: JourneyMission) -> dict[str, Any]:
    intent = _json_load(mission.intent_json, {})
    if not isinstance(intent, dict) or intent.get("mode") != GOAL_PLANNING_MODE:
        raise HTTPException(404, "DRAFT goal task was not found")
    task = intent.get(_TASK_KEY)
    if not isinstance(task, dict) or task.get("schema_version") != 1:
        raise HTTPException(409, "GOAL_TASK_STATE_INVALID")
    return intent


def _require_task(
    session: Session,
    journey: Journey,
    member: JourneyMember,
    mission_id: str | UUID,
    *,
    require_draft: bool,
) -> tuple[Journey, JourneyMember, JourneyMission, dict[str, Any], dict[str, Any]]:
    current_journey, current_member = _require_owner_scope(
        session, journey, member, require_draft=require_draft
    )
    mission = session.scalar(
        select(JourneyMission)
        .where(JourneyMission.id == str(mission_id))
        .with_for_update()
    )
    if (
        mission is None
        or str(mission.journey_id) != str(current_journey.id)
        or str(mission.traveler_id) != str(current_member.traveler_id)
        or mission.trigger_event_id is not None
        or mission.requested_autonomy != "PLAN_ONLY"
    ):
        raise HTTPException(404, "DRAFT goal task was not found")
    intent = _task_state(mission)
    task = intent[_TASK_KEY]
    return current_journey, current_member, mission, intent, task


def _emit_event(
    session: Session,
    journey: Journey,
    member: JourneyMember,
    mission: JourneyMission,
    intent: dict[str, Any],
    *,
    event_type: str,
    status: str,
    run_id: str | None = None,
    step_sequence_no: int | None = None,
    model_turn_no: int | None = None,
    tool_name: str | None = None,
    reason_code: str | None = None,
    consent: dict[str, bool] | None = None,
    budget: dict[str, int] | None = None,
) -> dict[str, Any]:
    task = intent[_TASK_KEY]
    sequence = int(task.get("event_sequence") or 0) + 1
    task["event_sequence"] = sequence
    event: dict[str, Any] = {
        "sequence": sequence,
        "event_type": event_type,
        "status": status,
        "run_id": run_id,
        "step_sequence_no": step_sequence_no,
        "model_turn_no": model_turn_no,
        "tool_name": tool_name,
        "reason_code": reason_code if reason_code and _REASON_CODE.fullmatch(reason_code) else None,
        "consent": consent,
        "budget": budget,
    }
    record_audit(
        session,
        action=_EVENT_ACTION,
        entity_type="AgentGoalTask",
        entity_id=mission.id,
        journey_id=journey.id,
        actor_type="TRAVELER" if event_type in {"TASK_ACCEPTED", "TASK_CANCELLED", "TASK_DRAFT_UPDATED", "CONSENT_UPDATED"} else "AI_AGENT",
        actor_id=member.traveler_id if event_type in {"TASK_ACCEPTED", "TASK_CANCELLED", "TASK_DRAFT_UPDATED", "CONSENT_UPDATED"} else "hermes-goal-planning",
        after=event,
    )
    mission.intent_json = _json_dump(intent)
    return event


def _task_payload(
    mission: JourneyMission,
    intent: dict[str, Any],
) -> dict[str, Any]:
    task = intent[_TASK_KEY]
    return {
        "task_id": mission.id,
        "journey_id": mission.journey_id,
        "mode": GOAL_PLANNING_MODE,
        "status": task.get("status"),
        "goal": mission.user_text,
        "consent": dict(task.get("consent") or {}),
        "budget": dict(task.get("budget") or {}),
        "usage": dict(task.get("usage") or {}),
        "latest_run_id": task.get("latest_run_id"),
        "candidate_place_ids": list(task.get("candidate_place_ids") or []),
        "source_observation_ids": list(task.get("source_observation_ids") or []),
        "assistant_summary": task.get("assistant_summary"),
        "research_places": list(task.get("research_places") or []),
        "draft_artifact": task.get("draft_artifact"),
        "failure_code": task.get("failure_code"),
        "created_at": mission.created_at,
        "started_at": mission.started_at,
        "updated_at": task.get("updated_at"),
    }


def _validate_bool(name: str, value: Any) -> bool:
    if type(value) is not bool:
        raise HTTPException(422, f"{name} must be explicitly true or false")
    return value


def _validate_budget(name: str, value: Any, *, minimum: int, maximum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not minimum <= value <= maximum:
        raise HTTPException(422, f"{name} must be between {minimum} and {maximum}")
    return value


def create_goal_task(
    session: Session,
    journey: Journey,
    member: JourneyMember,
    *,
    goal: str,
    model_consent: bool,
    online_research_consent: bool,
    max_model_turns: int,
    max_tool_calls: int,
) -> dict[str, Any]:
    """Accept a bounded DRAFT goal without constructing a provider or AgentRun."""

    journey, member = _require_owner_scope(session, journey, member, require_draft=True)
    model_consent = _validate_bool("model_consent", model_consent)
    online_research_consent = _validate_bool(
        "online_research_consent", online_research_consent
    )
    max_model_turns = _validate_budget(
        "max_model_turns", max_model_turns, minimum=1, maximum=_MAX_MODEL_TURNS
    )
    max_tool_calls = _validate_budget(
        "max_tool_calls", max_tool_calls, minimum=0, maximum=_MAX_TOOL_CALLS
    )
    normalized_goal = " ".join(str(goal or "").split())
    if not normalized_goal or len(normalized_goal) > _MAX_GOAL_LENGTH:
        raise HTTPException(422, "goal must contain 1 to 2000 characters")

    now = _now()
    status = "ACCEPTED" if model_consent else "NEEDS_DECISION"
    task_data = {
        "schema_version": 1,
        "journey_id": journey.id,
        "status": status,
        "consent": {
            "model": model_consent,
            "online_research": online_research_consent,
        },
        "budget": {"max_model_turns": max_model_turns, "max_tool_calls": max_tool_calls},
        "usage": {"model_turns": 0, "tool_calls": 0},
        "event_sequence": 0,
        "latest_run_id": None,
        "candidate_place_ids": [],
        "source_observation_ids": [],
        "assistant_summary": None,
        "research_places": [],
        "draft_artifact": empty_draft(journey),
        "failure_code": "MODEL_CONSENT_REQUIRED" if not model_consent else None,
        "updated_at": now,
    }
    mission = JourneyMission(
        id=str(uuid4()),
        journey_id=journey.id,
        traveler_id=member.traveler_id,
        trigger_event_id=None,
        user_text=normalized_goal,
        objective_codes_json="[]",
        protected_activity_ids_json="[]",
        mutable_activity_ids_json="[]",
        intent_json=_json_dump({"mode": GOAL_PLANNING_MODE, _TASK_KEY: task_data}),
        resolved_intent_json="{}",
        allowed_action_classes_json="[]",
        unresolved_references_json="[]",
        compiler_provider_key="none",
        compiler_model_key="none",
        compiler_confidence=0.0,
        reasoning_summary="",
        is_standing=False,
        parent_mission_id=None,
        max_cost_delta_minor=0,
        max_loss_minor=0,
        max_schedule_drift_min=0,
        preferences_json="{}",
        requested_autonomy="PLAN_ONLY",
        status=status,
        created_at=now,
        started_at=None,
        completed_at=None,
        failure_reason=None,
        clarification_json="{}",
    )
    session.add(mission)
    session.flush()
    intent = _task_state(mission)
    _emit_event(
        session,
        journey,
        member,
        mission,
        intent,
        event_type="TASK_ACCEPTED" if model_consent else "TASK_NEEDS_DECISION",
        status=status,
        reason_code=None if model_consent else "MODEL_CONSENT_REQUIRED",
        consent=dict(task_data["consent"]),
        budget=dict(task_data["budget"]),
    )
    session.commit()
    return _task_payload(mission, intent)


def read_goal_task(
    session: Session,
    journey: Journey,
    member: JourneyMember,
    mission_id: str | UUID,
) -> dict[str, Any]:
    """Read one owner-bound goal task and its materialized Place references."""

    journey, _, mission, intent, task = _require_task(
        session, journey, member, mission_id, require_draft=False
    )
    place_ids = [str(item) for item in task.get("candidate_place_ids") or []]
    places = session.scalars(select(Place).where(Place.id.in_(place_ids))).all() if place_ids else []
    result = _task_payload(mission, intent)
    result["candidate_places"] = [
        {
            "id": place.id,
            "name": place.name,
            "category": place.category,
            "city_code": place.city_code,
            "provider_key": place.provider_key,
            "opening_state": str((_json_load(place.opening_hours_json, {}) or {}).get("status") or "UNKNOWN").upper(),
            "cost_evidence": (
                _json_load(place.metadata_json, {}).get("cost_evidence")
                if isinstance(_json_load(place.metadata_json, {}), dict)
                else None
            ) or {"status": "UNKNOWN", "amount_minor": None},
        }
        for place in places
        if place.city_code == journey.city_code
    ]
    runs = session.scalars(
        select(AgentRun)
        .where(AgentRun.mission_id == mission.id)
        .order_by(AgentRun.created_at, AgentRun.id)
    ).all()
    run_ids = [str(run.id) for run in runs]
    steps = (
        session.scalars(
            select(AgentRunStep)
            .where(AgentRunStep.run_id.in_(run_ids))
            .order_by(AgentRunStep.created_at, AgentRunStep.sequence_no)
        ).all()
        if run_ids
        else []
    )
    result["tool_steps"] = [
        {
            "run_id": str(step.run_id),
            "sequence_no": step.sequence_no,
            "tool_name": step.tool_name,
            "status": step.status,
            "result": _json_load(step.result_json, {}),
            "created_at": step.created_at,
            "completed_at": step.completed_at,
        }
        for step in steps
    ]
    return result


def update_goal_draft(session, journey, member, mission_id, *, days, expected_revision):
    journey, member, mission, intent, task = _require_task(session, journey, member, mission_id, require_draft=True)
    if task.get("status") == "WORKING":
        raise HTTPException(409, "DRAFT_RESEARCH_RUNNING")
    current = task.get("draft_artifact") or empty_draft(journey)
    if current["revision"] != expected_revision:
        raise HTTPException(409, "DRAFT_CHANGED_RELOAD")
    task["draft_artifact"] = normalize_draft(journey, task, days, author="USER")
    task["updated_at"] = _now()
    mission.intent_json = _json_dump(intent)
    _emit_event(session, journey, member, mission, intent, event_type="TASK_DRAFT_UPDATED", status=task["status"])
    session.commit()
    return read_goal_task(session, journey, member, mission.id)


def list_goal_task_events(
    session: Session,
    journey: Journey,
    member: JourneyMember,
    mission_id: str | UUID,
    *,
    after_sequence: int = 0,
    limit: int = 50,
) -> dict[str, Any]:
    """Return stable, free-text-free task events after an integer cursor."""

    _, _, mission, _, _ = _require_task(
        session, journey, member, mission_id, require_draft=False
    )
    if isinstance(after_sequence, bool) or not isinstance(after_sequence, int) or after_sequence < 0:
        raise HTTPException(422, "after_sequence must be a non-negative integer")
    limit = _validate_budget("limit", limit, minimum=1, maximum=_MAX_EVENT_PAGE)
    rows = session.scalars(
        select(AuditLog).where(
            AuditLog.action == _EVENT_ACTION,
            AuditLog.entity_type == "AgentGoalTask",
            AuditLog.entity_id == mission.id,
            AuditLog.journey_id == mission.journey_id,
        )
    ).all()
    events: list[dict[str, Any]] = []
    for row in rows:
        payload = _json_load(row.after_json, {})
        if not isinstance(payload, dict):
            continue
        sequence = payload.get("sequence")
        if not isinstance(sequence, int) or sequence <= after_sequence:
            continue
        events.append(
            {
                key: payload.get(key)
                for key in (
                    "sequence",
                    "event_type",
                    "status",
                    "run_id",
                    "step_sequence_no",
                    "model_turn_no",
                    "tool_name",
                    "reason_code",
                    "consent",
                    "budget",
                )
            }
        )
    events.sort(key=lambda item: int(item["sequence"]))
    page = events[:limit]
    return {
        "task_id": mission.id,
        "events": page,
        "next_cursor": page[-1]["sequence"] if len(events) > len(page) and page else None,
    }


def cancel_goal_task(
    session: Session,
    journey: Journey,
    member: JourneyMember,
    mission_id: str | UUID,
) -> dict[str, Any]:
    """Cancel a DRAFT goal task; this operation does not call the model/provider."""

    journey, member, mission, intent, task = _require_task(
        session, journey, member, mission_id, require_draft=False
    )
    if task.get("status") == "CANCELLED":
        return _task_payload(mission, intent)
    now = _now()
    latest = _latest_run(session, mission.id)
    if latest is not None and latest.status == "RUNNING":
        latest.status = "INTERRUPTED"
        latest.failure_reason = "TASK_CANCELLED"
        latest.completed_at = now
    task["status"] = "CANCELLED"
    task["failure_code"] = None
    task["updated_at"] = now
    mission.status = "CANCELLED"
    mission.completed_at = now
    mission.failure_reason = None
    _emit_event(
        session,
        journey,
        member,
        mission,
        intent,
        event_type="TASK_CANCELLED",
        status="CANCELLED",
        run_id=latest.id if latest is not None else None,
    )
    session.commit()
    return _task_payload(mission, intent)


def _latest_run(session: Session, mission_id: str) -> AgentRun | None:
    return session.scalar(
        select(AgentRun)
        .where(AgentRun.mission_id == mission_id)
        .order_by(AgentRun.created_at.desc(), AgentRun.id.desc())
        .limit(1)
    )


def _run_age_seconds(run: AgentRun, *, now: datetime) -> float:
    try:
        started = datetime.fromisoformat(run.started_at)
        if started.tzinfo is None:
            return 0.0
        return max(0.0, (now - started.astimezone(timezone.utc)).total_seconds())
    except (TypeError, ValueError):
        return 0.0


def _new_goal_agent(tool_allowlist: frozenset[str]) -> HermesJourneyAgent:
    """Do not silently fall back to another provider or model chain."""

    if not settings.ai_enabled:
        raise AgentRuntimeUnavailable("AI is disabled by the operator")
    model = str(settings.hermes_model or "").strip()
    if not model:
        raise AgentRuntimeUnavailable("Hermes goal-planning model is not configured")
    return HermesJourneyAgent(
        model_chain=(model,),
        allow_budget_retry=False,
        tool_allowlist=tool_allowlist,
        extra_tool_definitions=(*goal_tool_definitions(), route_tool_definition()),
    )


def _journey_snapshot(journey: Journey) -> dict[str, Any]:
    return {
        "id": journey.id,
        "status": journey.status,
        "title": journey.title,
        "city_code": journey.city_code,
        "timezone": journey.timezone,
        "start_at": journey.start_at,
        "end_at": journey.end_at,
        "budget": {
            "amount_minor": journey.budget_amount_minor,
            "currency": journey.budget_currency,
        },
        "planning_mode": journey.planning_mode,
    }


def _known_place_context(session: Session, journey: Journey, task: dict[str, Any]) -> list[dict[str, Any]]:
    ids = [str(item) for item in task.get("candidate_place_ids") or []]
    if not ids:
        return []
    rows = session.scalars(select(Place).where(Place.id.in_(ids))).all()
    result = []
    for place in rows:
        if place.city_code != journey.city_code:
            continue
        metadata = _json_load(place.metadata_json, {})
        cost = metadata.get("cost_evidence") if isinstance(metadata, dict) else None
        opening = _json_load(place.opening_hours_json, {})
        result.append(
            {
                "place_id": place.id,
                "name": place.name,
                "category": place.category,
                "provider_key": place.provider_key,
                "opening_hours": opening if isinstance(opening, dict) else {"status": "UNKNOWN"},
                "cost_evidence": cost if isinstance(cost, dict) else {"status": "UNKNOWN", "amount_minor": None},
                "metadata": {
                    key: metadata.get(key)
                    for key in ("provider_provenance", "source_url", "public_access_state")
                    if isinstance(metadata, dict) and metadata.get(key) is not None
                },
            }
        )
    return result


def _known_source_context(session: Session, task: dict[str, Any]) -> list[dict[str, Any]]:
    ids = [str(item) for item in task.get("source_observation_ids") or []]
    if not ids:
        return []
    rows = session.scalars(select(WebObservation).where(WebObservation.id.in_(ids))).all()
    return [
        {
            "observation_id": row.id,
            "url": row.url,
            "domain": row.domain,
            "title": row.title,
            "authority_status": row.authority_status,
            "captured_at": row.captured_at,
        }
        for row in rows
        if row.journey_id == task.get("journey_id")
    ]


def _initial_messages(
    session: Session,
    journey: Journey,
    mission: JourneyMission,
    task: dict[str, Any],
) -> list[dict[str, Any]]:
    system = (
        "You are the CityNexus DRAFT goal-planning assistant. Use the provided goal and current "
        "Journey facts to research useful candidate Places. After every tool result, inspect the "
        "actual result and choose the next tool yourself; do not follow a fixed tool sequence. "
        "Only use the available tools. This is GOAL_PLANNING, not recovery: do not create or infer "
        "an incident, do not select or activate a PlanVersion, and do not book, pay, cancel, or "
        "change Journey state. Keep missing opening hours, prices, and availability UNKNOWN. Treat "
        "source research as non-authoritative unless the server says otherwise. Return a short "
        "Chinese user-facing summary without hidden reasoning, secrets, or tool transcripts. "
        "search_city_services reads the existing catalogue only; discover_places runs one model-selected public Photon or Nominatim query. "
        "discover_nearby_places uses one bounded Overpass request near an actual researched place or area ID. "
        "Use it when a name search misses POIs; the center must come from public_research_places or public_research_areas. "
        "For canonical Place IDs returned in this task, reuse research_place_sources, acquire_place_facts, "
        "and estimate_place_facts. Estimates remain strategy hypotheses. Formal candidate generation belongs to "
        "the separate plan workbench after research. For a public_research_places ID, research_place_sources returns only its cached OSM citation and already-known fields plus not_acquired_fields; it performs no web search and creates no WebObservation. "
        "Do not pass a URL or convert a public research ID into a canonical Place ID. Source observations must come from this task, never invent a URL. compare_routes reads stored "
        "facts only, never live routes. Public geocoder research IDs are tentative leads, not canonical Place IDs. "
        "Use public keywords without personal information. If a Photon search returns no results, you may choose "
        "a different keyword or the Nominatim source within the approved budget; distinguish a new source from "
        "repeating the exact same query. If public data is sparse, continue another part of the trip instead of quitting. "
        "Save useful partial research as an editable draft using save_draft_itinerary, even when every place search fails: "
        "in that case write specific research todos or generic suggestions with no invented Place IDs. "
        "Keep enough budget to save the draft. A place with unknown hours or cost can still be a tentative suggestion."
    )
    user_context = {
        "goal": mission.user_text,
        "journey": _journey_snapshot(journey),
        "known_candidate_places": _known_place_context(session, journey, task),
        "known_non_authoritative_sources": _known_source_context(session, task),
        "public_research_places": task.get("research_places") or [],
        "public_research_areas": task.get("research_areas") or [],
        "draft_artifact": task.get("draft_artifact") or empty_draft(journey),
        "previous_public_queries": task.get("public_queries") or [],
        "consent": dict(task.get("consent") or {}),
        "remaining_budget": {
            "model_turns": max(0, int(task["budget"]["max_model_turns"]) - int(task["usage"]["model_turns"])),
            "tool_calls": max(0, int(task["budget"]["max_tool_calls"]) - int(task["usage"]["tool_calls"])),
        },
    }
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": _json_dump(user_context)},
    ]


def _safe_args(name: str, raw: Any, task: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise HTTPException(422, "TOOL_ARGUMENTS_INVALID")
    if name in DOMAIN_TOOLS:
        return domain_args(name, raw, task)
    if name == "discover_nearby_places":
        if set(raw) - {"center_place_id", "query", "radius_m", "limit", "public_action"}:
            raise HTTPException(422, "TOOL_ARGUMENTS_INVALID")
        return {"center_place_id": str(raw.get("center_place_id") or ""),
                "query": str(raw.get("query") or "").strip()[:120],
                "radius_m": raw.get("radius_m", 1500), "limit": raw.get("limit", 8),
                "public_action": str(raw.get("public_action") or "")[:120]}
    if name == "discover_places":
        if set(raw) - {"query", "public_action", "source"}:
            raise HTTPException(422, "TOOL_ARGUMENTS_INVALID")
        source = str(raw.get("source") or "photon").lower().strip()
        if source not in {"photon", "nominatim"}:
            raise HTTPException(422, "PUBLIC_SOURCE_NOT_SUPPORTED")
        return {"query": str(raw.get("query") or "").strip()[:120],
                "public_action": str(raw.get("public_action") or "")[:120], "source": source}
    if name == "save_draft_itinerary":
        if set(raw) != {"days"}:
            raise HTTPException(422, "TOOL_ARGUMENTS_INVALID")
        return {"days": raw["days"]}
    if name == "inspect_journey":
        if set(raw) - {"journey_id"}:
            raise HTTPException(422, "TOOL_ARGUMENTS_INVALID")
        return {}
    if name == "search_city_services":
        if set(raw) - {"journey_id", "q", "category", "service_type"}:
            raise HTTPException(422, "TOOL_ARGUMENTS_INVALID")
        if any(
            key in raw and raw[key] is not None and not isinstance(raw[key], str)
            for key in ("q", "category", "service_type")
        ):
            raise HTTPException(422, "TOOL_ARGUMENTS_INVALID")
        return {
            key: value.strip()[:120 if key == "q" else 80]
            for key, value in raw.items()
            if key in {"q", "category", "service_type"} and isinstance(value, str) and value.strip()
        }
    if name == "research_place_sources":
        if set(raw) - {"journey_id", "place_id"}:
            raise HTTPException(422, "TOOL_ARGUMENTS_INVALID")
        place_id = raw.get("place_id")
        if not isinstance(place_id, str) or not place_id:
            raise HTTPException(422, "TOOL_ARGUMENTS_INVALID")
        canonical_ids = {str(item) for item in task.get("candidate_place_ids") or []}
        if place_id not in canonical_ids and goal_research_lead(task, place_id) is None:
            raise HTTPException(403, "PLACE_NOT_IN_GOAL_TASK_SCOPE")
        return {"place_id": place_id}
    raise HTTPException(404, "GOAL_TASK_TOOL_NOT_ALLOWED")


def _dispatch_gateway_tool(gateway, name: str, request, task: dict[str, Any], args: dict[str, Any]):
    """Keep canonical research on Gateway; public task leads only expose their local cache."""
    if name == "research_place_sources":
        place_id = args.get("place_id")
        canonical_ids = {str(item) for item in task.get("candidate_place_ids") or []}
        if place_id not in canonical_ids:
            return cached_goal_place_sources(task, str(place_id or ""))
    return gateway.dispatch(name, request)


def _safe_tool_result(name: str, raw: dict[str, Any]) -> dict[str, Any]:
    """Keep model-visible results grounded while omitting member-private fields and excerpts."""

    if name == "research_place_sources" and raw.get("status") == "CACHED_ONLY":
        references = raw.get("cached_references") if isinstance(raw.get("cached_references"), list) else []
        facts = raw.get("cached_facts") if isinstance(raw.get("cached_facts"), dict) else {}
        fields = {"place_id", "provider", "provider_provenance", "name", "category", "latitude",
                  "longitude", "opening_status", "cost_status"}
        safe_references = [
            {key: item[key] for key in ("reference_type", "provider", "url", "authority_status") if key in item}
            for item in references[:5]
            if isinstance(item, dict) and item.get("reference_type") == "OSM_OBJECT"
            and item.get("authority_status") == "NON_AUTHORITATIVE"
            and isinstance(item.get("url"), str)
            and re.fullmatch(r"https://www\.openstreetmap\.org/(?:node|way|relation)/[1-9][0-9]*", item["url"])
        ]
        return {
            "tool": name,
            "status": "CACHED_ONLY",
            "place_id": raw.get("place_id"),
            "authority": "NON_AUTHORITATIVE",
            "reference_status": "PRESENT" if safe_references else "NOT_VERIFIED",
            "cached_references": safe_references,
            "cached_facts": {key: facts[key] for key in fields if key in facts},
            "not_acquired_fields": [
                field for field in raw.get("not_acquired_fields", [])
                if field in {"opening_hours", "cost", "availability", "travel_time"}
            ],
            "source_discovery_attempted": False,
            "acquisition_attempted": False,
        }
    if name in DOMAIN_TOOLS:
        return domain_result(name, raw)
    if name in {"discover_places", "discover_nearby_places", "save_draft_itinerary"}:
        return raw
    if name == "inspect_journey":
        journey = raw.get("journey") if isinstance(raw.get("journey"), dict) else {}
        safe_journey = {
            key: journey.get(key)
            for key in (
                "id",
                "title",
                "city_code",
                "timezone",
                "start_at",
                "end_at",
                "budget_currency",
                "budget_amount_minor",
                "planning_mode",
                "status",
            )
            if key in journey
        }
        return {"tool": name, "journey": safe_journey}
    if name == "search_city_services":
        services = raw.get("services") if isinstance(raw.get("services"), list) else []
        places = raw.get("places") if isinstance(raw.get("places"), list) else []
        safe_places = []
        for item in places[:20]:
            if not isinstance(item, dict):
                continue
            metadata = item.get("metadata") if isinstance(item.get("metadata"), dict) else {}
            safe_places.append(
                {
                    key: item.get(key)
                    for key in ("id", "name", "category", "city_code", "provider_key", "location", "tags", "opening_hours")
                    if key in item
                }
                | {
                    "cost_evidence": metadata.get("cost_evidence") or {"status": "UNKNOWN", "amount_minor": None},
                    "public_access_state": metadata.get("public_access_state"),
                    "source_url": metadata.get("source_url"),
                }
            )
        safe_services = [
            {
                key: item.get(key)
                for key in ("id", "name", "service_type", "place_id", "availability")
                if key in item
            }
            for item in services[:20]
            if isinstance(item, dict)
        ]
        return {
            "tool": name,
            "city_code": raw.get("city_code"),
            "services": safe_services,
            "places": safe_places,
            "discovery": raw.get("discovery") if isinstance(raw.get("discovery"), dict) else None,
        }
    observations = raw.get("observations") if isinstance(raw.get("observations"), list) else []
    return {
        "tool": name,
        "status": raw.get("status"),
        "reason_code": raw.get("reason_code"),
        "authority": raw.get("authority", "NON_AUTHORITATIVE"),
        "observations": [
            {
                key: item.get(key)
                for key in ("id", "url", "domain", "title", "provider", "captured_at", "authority_status")
                if key in item
            }
            for item in observations[:5]
            if isinstance(item, dict)
        ],
    }


def _step_args_summary(name: str, args: dict[str, Any]) -> dict[str, Any]:
    if name == "discover_nearby_places":
        return {"center_place_id": args.get("center_place_id"), "radius_m": args.get("radius_m"),
                "query_length": len(args.get("query") or ""), "provider": "overpass", "public_action": args.get("public_action")}
    if name in {"discover_places", "discover_nearby_places"}:
        return {"query_length": len(args.get("query") or ""), "public_action": args.get("public_action"),
                "provider": args.get("source", "photon")}
    if name == "save_draft_itinerary":
        return {"days": len(args.get("days") or [])}
    if name == "search_city_services":
        return {
            "argument_names": sorted(args),
            "query_length": len(args.get("q") or ""),
            "category_length": len(args.get("category") or ""),
            "service_type_length": len(args.get("service_type") or ""),
        }
    return {"place_id": args.get("place_id")} if name == "research_place_sources" else {}


def _step_result_summary(name: str, result: dict[str, Any]) -> dict[str, Any]:
    if name == "research_place_sources" and result.get("status") == "CACHED_ONLY":
        return {"status": "CACHED_ONLY", "place_id": result.get("place_id"),
                "reference_status": result.get("reference_status"),
                "cached_references": result.get("cached_references") or [],
                "cached_fact_fields": sorted((result.get("cached_facts") or {}).keys()),
                "not_acquired_fields": result.get("not_acquired_fields") or [],
                "source_discovery_attempted": False, "acquisition_attempted": False}
    if name == "compare_routes":
        return {"status": result.get("status"), "option_count": len(result.get("options") or []), "acquisition_attempted": False}
    if name == "generate_plans":
        return {"status": "COMPLETED", "candidate_count": result.get("candidate_count", 0),
                "plan_ids": [plan["id"] for plan in result.get("plans", []) if plan.get("id")], "activation_attempted": False}
    if name in {"acquire_place_facts", "estimate_place_facts"}:
        return {"status": result.get("status", "COMPLETED"), "place_id": result.get("place_id") or (result.get("estimate") or {}).get("place_id")}
    if name in {"discover_places", "discover_nearby_places"}:
        return {"status": result.get("status"), "reason_code": result.get("reason_code"),
                "place_count": len(result.get("places") or []), "http_status": result.get("http_status"),
                "public_action": result.get("public_action"), "provider": result.get("provider"),
                "provider_provenance": result.get("provider_provenance") }
    if name == "save_draft_itinerary":
        return {"status": "COMPLETED", "draft_revision": result["draft_artifact"]["revision"]}
    if result.get("status") in {
        "FAILED",
        "NEEDS_DECISION",
        "FAILED_EXTERNAL",
        "SOURCE_DISCOVERY_UNAVAILABLE",
        "PROVIDER_UNAVAILABLE",
    }:
        return {"status": result.get("status"), "reason_code": result.get("reason_code")}
    if name == "search_city_services":
        places = result.get("places") if isinstance(result.get("places"), list) else []
        services = result.get("services") if isinstance(result.get("services"), list) else []
        place_ids = sorted({str(item["id"]) for item in places if isinstance(item, dict) and item.get("id")})
        service_ids = sorted({str(item["id"]) for item in services if isinstance(item, dict) and item.get("id")})
        discovery = result.get("discovery") if isinstance(result.get("discovery"), dict) else {}
        return {
            "status": "COMPLETED",
            "place_count": len(places),
            "service_count": len(services),
            "place_ids": place_ids[:20],
            "service_ids": service_ids[:20],
            "discovery_attempted": discovery.get("attempted") is True,
        }
    observations = result.get("observations") if isinstance(result.get("observations"), list) else []
    return {"status": result.get("status") or "COMPLETED", "observation_ids": [str(item["id"]) for item in observations if isinstance(item, dict) and item.get("id")][:5]}


def _persist_tool_result_refs(task: dict[str, Any], name: str, result: dict[str, Any]) -> None:
    if name == "search_city_services":
        places = result.get("places") if isinstance(result.get("places"), list) else []
        services = result.get("services") if isinstance(result.get("services"), list) else []
        known = {str(item) for item in task.get("candidate_place_ids") or []}
        for item in places:
            if isinstance(item, dict) and item.get("id"):
                known.add(str(item["id"]))
        for item in services:
            if isinstance(item, dict) and item.get("place_id"):
                known.add(str(item["place_id"]))
        task["candidate_place_ids"] = sorted(known)[:80]
    elif name == "research_place_sources":
        observations = result.get("observations") if isinstance(result.get("observations"), list) else []
        known = {str(item) for item in task.get("source_observation_ids") or []}
        for item in observations:
            if isinstance(item, dict) and item.get("id"):
                known.add(str(item["id"]))
        task["source_observation_ids"] = sorted(known)[:40]


def _reason_from_http(exc: HTTPException) -> str:
    detail = str(exc.detail or "")
    return detail if _REASON_CODE.fullmatch(detail) else "TOOL_UNAVAILABLE"


def _has_research_failure(name: str, result: dict[str, Any]) -> bool:
    if result.get("status") in {
        "FAILED_EXTERNAL",
        "SOURCE_DISCOVERY_UNAVAILABLE",
        "PROVIDER_UNAVAILABLE",
        "PROVIDER_DISABLED",
        "UNAVAILABLE",
    }:
        return True
    if name == "search_city_services":
        discovery = result.get("discovery") if isinstance(result.get("discovery"), dict) else {}
        statuses = discovery.get("provider_status")
        return isinstance(statuses, dict) and any(
            str(value).upper() in {"FAILED_EXTERNAL", "UNAVAILABLE", "DISABLED", "PROVIDER_UNAVAILABLE"}
            for value in statuses.values()
        )
    return False


def _step_sequence(session: Session, run_id: str) -> int:
    current = session.scalar(
        select(AgentRunStep.sequence_no)
        .where(AgentRunStep.run_id == run_id)
        .order_by(AgentRunStep.sequence_no.desc())
        .limit(1)
    )
    return int(current or 0) + 1


def _finish_run(
    session: Session,
    journey: Journey,
    member: JourneyMember,
    mission: JourneyMission,
    run: AgentRun,
    intent: dict[str, Any],
    *,
    status: str,
    event_type: str,
    reason_code: str | None = None,
    outcome_code: str | None = None,
) -> None:
    now = _now()
    task = intent[_TASK_KEY]
    task["status"] = status
    task["failure_code"] = reason_code
    task["updated_at"] = now
    mission.status = status
    mission.failure_reason = reason_code
    mission.completed_at = now
    run.status = {
        "PARTIAL_READY": "COMPLETED",
        "RESUMABLE": "PARTIAL",
        "NEEDS_DECISION": "PARTIAL",
        "FAILED_RECOVERABLE": "FAILED_EXTERNAL",
        "CANCELLED": "INTERRUPTED",
    }.get(status, status)
    run.failure_reason = reason_code if status in {"RESUMABLE", "NEEDS_DECISION", "FAILED_RECOVERABLE", "CANCELLED"} else None
    run.outcome = _json_dump({"status": status, "code": outcome_code or reason_code})
    run.completed_at = now
    _emit_event(
        session,
        journey,
        member,
        mission,
        intent,
        event_type=event_type,
        status=status,
        run_id=run.id,
        reason_code=reason_code or outcome_code,
    )
    session.commit()


def _cancelled_result(
    session: Session,
    mission_id: str,
    run: AgentRun,
) -> dict[str, Any] | None:
    mission = session.get(JourneyMission, mission_id)
    if mission is None:
        return None
    intent = _task_state(mission)
    if intent[_TASK_KEY].get("status") != "CANCELLED":
        return None
    if run.status == "RUNNING":
        run.status = "INTERRUPTED"
        run.failure_reason = "TASK_CANCELLED"
        run.completed_at = _now()
    session.commit()
    return {**_task_payload(mission, intent), "assistant_summary": None}


def resume_goal_task(
    session: Session,
    journey: Journey,
    member: JourneyMember,
    mission_id: str | UUID,
    *,
    model_consent: bool | None = None,
    online_research_consent: bool | None = None,
    max_model_turns: int | None = None,
    max_tool_calls: int | None = None,
) -> dict[str, Any]:
    """Run the model-selected DRAFT research loop, or resume its persisted task."""

    journey, member, mission, intent, task = _require_task(
        session, journey, member, mission_id, require_draft=True
    )
    if task.get("status") in {"CANCELLED", "COMPLETED"}:
        raise HTTPException(409, "GOAL_TASK_NOT_RESUMABLE")
    consent = task.get("consent") if isinstance(task.get("consent"), dict) else {}
    prior_consent = {
        "model": consent.get("model") is True,
        "online_research": consent.get("online_research") is True,
    }
    if model_consent is not None:
        consent["model"] = _validate_bool("model_consent", model_consent)
    if online_research_consent is not None:
        consent["online_research"] = _validate_bool(
            "online_research_consent", online_research_consent
        )
    task["consent"] = {"model": consent.get("model") is True, "online_research": consent.get("online_research") is True}
    budget = task.get("budget") if isinstance(task.get("budget"), dict) else {}
    usage = task.get("usage") if isinstance(task.get("usage"), dict) else {}
    if max_model_turns is not None:
        updated_max = _validate_budget(
            "max_model_turns", max_model_turns, minimum=1, maximum=_MAX_MODEL_TURNS
        )
        if updated_max < int(usage.get("model_turns") or 0):
            raise HTTPException(422, "max_model_turns cannot be lower than prior usage")
        budget["max_model_turns"] = updated_max
    if max_tool_calls is not None:
        updated_max = _validate_budget(
            "max_tool_calls", max_tool_calls, minimum=0, maximum=_MAX_TOOL_CALLS
        )
        if updated_max < int(usage.get("tool_calls") or 0):
            raise HTTPException(422, "max_tool_calls cannot be lower than prior usage")
        budget["max_tool_calls"] = updated_max
    task["budget"] = budget
    task["usage"] = {
        "model_turns": int(usage.get("model_turns") or 0),
        "tool_calls": int(usage.get("tool_calls") or 0),
    }
    task["updated_at"] = _now()
    if task["consent"] != prior_consent:
        _emit_event(
            session,
            journey,
            member,
            mission,
            intent,
            event_type="CONSENT_UPDATED",
            status=str(task.get("status") or mission.status),
            consent=dict(task["consent"]),
            budget=dict(task["budget"]),
        )
    if not task["consent"]["model"]:
        task["status"] = "NEEDS_DECISION"
        task["failure_code"] = "MODEL_CONSENT_REQUIRED"
        mission.status = "NEEDS_DECISION"
        mission.intent_json = _json_dump(intent)
        _emit_event(
            session,
            journey,
            member,
            mission,
            intent,
            event_type="TASK_NEEDS_DECISION",
            status="NEEDS_DECISION",
            reason_code="MODEL_CONSENT_REQUIRED",
        )
        session.commit()
        return {**_task_payload(mission, intent), "assistant_summary": None}

    if int(task["usage"]["model_turns"]) >= int(task["budget"]["max_model_turns"]):
        task["status"] = "RESUMABLE"
        task["failure_code"] = "MODEL_BUDGET_EXHAUSTED"
        task["updated_at"] = _now()
        mission.status = "RESUMABLE"
        mission.completed_at = task["updated_at"]
        mission.intent_json = _json_dump(intent)
        _emit_event(
            session,
            journey,
            member,
            mission,
            intent,
            event_type="TASK_RESUMABLE",
            status="RESUMABLE",
            reason_code="MODEL_BUDGET_EXHAUSTED",
        )
        session.commit()
        return {**_task_payload(mission, intent), "assistant_summary": None}

    previous_run = _latest_run(session, mission.id)
    now_dt = datetime.now(timezone.utc)
    if previous_run is not None and previous_run.status == "RUNNING":
        try:
            stale_after = max(60.0, float(settings.impact_timeout_seconds) * 2.0 + 30.0)
        except (TypeError, ValueError):
            stale_after = 300.0
        if _run_age_seconds(previous_run, now=now_dt) < stale_after:
            raise HTTPException(409, "GOAL_TASK_ALREADY_RUNNING")
        previous_run.status = "INTERRUPTED"
        previous_run.failure_reason = "PROCESS_INTERRUPTED"
        previous_run.completed_at = _now()
        _emit_event(
            session,
            journey,
            member,
            mission,
            intent,
            event_type="RUN_INTERRUPTED",
            status="RESUMABLE",
            run_id=previous_run.id,
            reason_code="PROCESS_INTERRUPTED",
        )
        session.commit()

    online_tools = task["consent"]["online_research"]
    tool_allowlist = frozenset(
        _ALLOWED_TOOLS if online_tools else {"inspect_journey", "save_draft_itinerary"}
    )
    try:
        agent = _new_goal_agent(tool_allowlist)
    except AgentRuntimeUnavailable:
        task["status"] = "FAILED_RECOVERABLE"
        task["failure_code"] = "MODEL_RUNTIME_UNAVAILABLE"
        mission.status = "FAILED_RECOVERABLE"
        mission.failure_reason = "MODEL_RUNTIME_UNAVAILABLE"
        mission.completed_at = _now()
        mission.intent_json = _json_dump(intent)
        _emit_event(
            session,
            journey,
            member,
            mission,
            intent,
            event_type="TASK_NEEDS_DECISION",
            status="FAILED_RECOVERABLE",
            reason_code="MODEL_RUNTIME_UNAVAILABLE",
        )
        session.commit()
        return {**_task_payload(mission, intent), "assistant_summary": None}

    now = _now()
    run = AgentRun(
        id=str(uuid4()),
        mission_id=mission.id,
        journey_id=journey.id,
        provider_key=agent.provider_key,
        model_key=agent.model_key,
        status="RUNNING",
        outcome=None,
        failure_reason=None,
        created_at=now,
        started_at=now,
        completed_at=None,
        recovery_epoch_id=None,
    )
    session.add(run)
    task["status"] = "WORKING"
    task["latest_run_id"] = run.id
    task["failure_code"] = None
    task["updated_at"] = now
    mission.status = "WORKING"
    mission.started_at = mission.started_at or now
    mission.completed_at = None
    mission.failure_reason = None
    _emit_event(
        session,
        journey,
        member,
        mission,
        intent,
        event_type="RUN_STARTED",
        status="WORKING",
        run_id=run.id,
        consent=dict(task["consent"]),
        budget=dict(task["budget"]),
    )
    session.commit()

    messages = _initial_messages(session, journey, mission, task)
    gateway = AgentToolGateway(session, bound_run_id=run.id, allow_live_discovery=False)
    research_failed = False
    assistant_summary: str | None = None
    try:
        while int(task["usage"]["model_turns"]) < int(task["budget"]["max_model_turns"]):
            journey, member = _require_owner_scope(session, journey, member, require_draft=True)
            mission = session.get(JourneyMission, mission.id)
            if mission is None:
                raise HTTPException(404, "DRAFT goal task was not found")
            intent = _task_state(mission)
            task = intent[_TASK_KEY]
            if task.get("status") == "CANCELLED":
                return _cancelled_result(session, mission.id, run) or {
                    **_task_payload(mission, intent),
                    "assistant_summary": None,
                }
            task["status"] = "WORKING"
            mission.status = "WORKING"
            now = _now()
            task["usage"]["model_turns"] += 1
            task["updated_at"] = now
            mission.intent_json = _json_dump(intent)
            _emit_event(
                session,
                journey,
                member,
                mission,
                intent,
                event_type="MODEL_TURN_STARTED",
                status="WORKING",
                run_id=run.id,
                model_turn_no=int(task["usage"]["model_turns"]),
            )
            session.commit()
            try:
                final_turn = int(task["usage"]["model_turns"]) == int(task["budget"]["max_model_turns"])
                agent._tool_allowlist = frozenset({"save_draft_itinerary"}) if final_turn else tool_allowlist
                if final_turn:
                    messages.append({"role": "system", "content":
                        "This is the last approved model turn. Research has ended for this round. "
                        "Use save_draft_itinerary now to deliver the best useful partial multi-day draft from actual results. "
                        "With no verified places, save specific research todos or generic activity suggestions without Place IDs. "
                        "Leave all missing facts unknown. Do not request another external search."})
                message = agent._complete(messages)
            except Exception as exc:
                # Do not persist provider messages, URLs, tokens, or exception text.
                cancelled = _cancelled_result(session, mission.id, run)
                if cancelled is not None:
                    return cancelled
                reason = "MODEL_TIMEOUT" if "Timeout" in type(exc).__name__ else "MODEL_EXTERNAL_ERROR"
                mission = session.get(JourneyMission, mission.id)
                intent = _task_state(mission)
                _finish_run(
                    session,
                    journey,
                    member,
                    mission,
                    run,
                    intent,
                    status="FAILED_RECOVERABLE",
                    event_type="MODEL_FAILED",
                    reason_code=reason,
                )
                return {**_task_payload(mission, intent), "assistant_summary": None}

            cancelled = _cancelled_result(session, mission.id, run)
            if cancelled is not None:
                return cancelled
            mission = session.get(JourneyMission, mission.id)
            intent = _task_state(mission)
            task = intent[_TASK_KEY]
            _emit_event(
                session,
                journey,
                member,
                mission,
                intent,
                event_type="MODEL_TURN_COMPLETED",
                status="WORKING",
                run_id=run.id,
                model_turn_no=int(task["usage"]["model_turns"]),
            )
            session.commit()

            # Keep the model's selected action and actual tool result in-memory for
            # the next choice; never store model reasoning or raw tool transcripts.
            raw_calls = message.get("tool_calls") or []
            if not raw_calls:
                assistant_summary = str(message.get("content") or "").strip()[:2000] or None
                mission = session.get(JourneyMission, mission.id)
                intent = _task_state(mission)
                intent[_TASK_KEY]["assistant_summary"] = assistant_summary
                _finish_run(
                    session,
                    journey,
                    member,
                    mission,
                    run,
                    intent,
                    status="PARTIAL_READY",
                    event_type="TASK_PARTIAL_READY",
                    reason_code="RESEARCH_INCOMPLETE" if research_failed else None,
                    outcome_code="SUMMARY_READY",
                )
                return {**_task_payload(mission, intent), "assistant_summary": assistant_summary}

            raw_call = raw_calls[0] if isinstance(raw_calls[0], dict) else {}
            call_id = str(raw_call.get("id") or f"goal-tool-{uuid4()}")[:128]
            function = raw_call.get("function")
            function = function if isinstance(function, dict) else {}
            tool_name = str(function.get("name") or "")
            step_no = _step_sequence(session, run.id)
            tool_started_at = _now()
            tool_clock = time.perf_counter()
            pause_for_decision: str | None = None
            if tool_name not in tool_allowlist:
                blocked_code = (
                    "ONLINE_CONSENT_REQUIRED"
                    if tool_name in _ALLOWED_TOOLS
                    and tool_name != "inspect_journey"
                    and not task["consent"].get("online_research")
                    else "TOOL_NOT_ALLOWED"
                )
                safe_result = {"tool": tool_name or "unknown", "status": "NEEDS_DECISION", "reason_code": blocked_code}
                args = {}
                dispatch_status = "BLOCKED"
                reason_code = blocked_code
                if blocked_code == "ONLINE_CONSENT_REQUIRED":
                    pause_for_decision = blocked_code
            else:
                try:
                    args_raw = function.get("arguments") or "{}"
                    args_value = json.loads(args_raw) if isinstance(args_raw, str) else args_raw
                    args = _safe_args(tool_name, args_value, task)
                    if tool_name not in {"inspect_journey", "save_draft_itinerary"} and not task["consent"]["online_research"]:
                        raise HTTPException(403, "ONLINE_CONSENT_REQUIRED")
                    if int(task["usage"]["tool_calls"]) >= int(task["budget"]["max_tool_calls"]):
                        exhausted_status = "PARTIAL_READY" if research_failed or any(day.get("slots") for day in (task.get("draft_artifact") or {}).get("days", [])) else "RESUMABLE"
                        _finish_run(
                            session,
                            journey,
                            member,
                            mission,
                            run,
                            intent,
                            status=exhausted_status,
                            event_type=("TASK_PARTIAL_READY" if research_failed else "TASK_RESUMABLE"),
                            reason_code="RESEARCH_INCOMPLETE" if research_failed else "TOOL_BUDGET_EXHAUSTED",
                        )
                        return {**_task_payload(mission, intent), "assistant_summary": None}
                    # The model never chooses an identity or authority scope. Rebind
                    # every call to the verified owner, DRAFT Journey and this mission.
                    request_fields: dict[str, Any] = {
                        "request_id": str(uuid4()),
                        "agent_id": "hermes-goal-planning",
                        "journey_id": UUID(journey.id),
                        "mission_id": UUID(mission.id),
                        **args,
                    }
                    request = (None if tool_name in {"discover_places", "discover_nearby_places", "save_draft_itinerary", "compare_routes"}
                               else AgentToolCall.model_validate(request_fields))
                    _require_owner_scope(session, journey, member, require_draft=True)
                    task["usage"]["tool_calls"] += 1
                    task["updated_at"] = _now()
                    mission.intent_json = _json_dump(intent)
                    _emit_event(session, journey, member, mission, intent, event_type="TOOL_STARTED",
                                status="WORKING", run_id=run.id, step_sequence_no=step_no, tool_name=tool_name)
                    session.commit()
                    try:
                        if tool_name == "compare_routes":
                            raw_result = compare_stored_routes(session, journey, **args)
                        elif tool_name in {"discover_places", "discover_nearby_places"}:
                            discover = discover_goal_places if tool_name == "discover_places" else discover_nearby_goal_places
                            raw_result = discover(session, journey, task, **args)
                            mission.intent_json = _json_dump(intent)
                            session.commit()
                        elif tool_name == "save_draft_itinerary":
                            task["draft_artifact"] = normalize_draft(journey, task, args["days"], author="MODEL_SUGGESTION")
                            raw_result = {"tool": tool_name, "status": "DRAFT_SAVED", "draft_artifact": task["draft_artifact"]}
                            mission.intent_json = _json_dump(intent)
                            session.commit()
                        else:
                            raw_result = _dispatch_gateway_tool(gateway, tool_name, request, task, args)
                        safe_result = _safe_tool_result(tool_name, raw_result)
                        dispatch_status = "COMPLETED"
                        reason_code = None
                        if _has_research_failure(tool_name, raw_result):
                            research_failed = True
                            task["failure_code"] = "RESEARCH_UNAVAILABLE"
                            task["status"] = "PARTIAL_READY"
                        mission = session.get(JourneyMission, mission.id)
                        intent = _task_state(mission)
                        task = intent[_TASK_KEY]
                        if _has_research_failure(tool_name, raw_result):
                            task["failure_code"] = "RESEARCH_UNAVAILABLE"
                            task["status"] = "PARTIAL_READY"
                        _persist_tool_result_refs(task, tool_name, raw_result)
                    except HTTPException as exc:
                        reason_code = _reason_from_http(exc)
                        safe_result = {"tool": tool_name, "status": "FAILED", "reason_code": reason_code}
                        dispatch_status = "FAILED"
                        research_failed = True
                    except Exception as exc:
                        reason_code = "TOOL_EXTERNAL_ERROR" if "Timeout" in type(exc).__name__ else "TOOL_UNAVAILABLE"
                        safe_result = {"tool": tool_name, "status": "FAILED", "reason_code": reason_code}
                        dispatch_status = "FAILED"
                        research_failed = True
                except (ValueError, TypeError, HTTPException) as exc:
                    reason_code = _reason_from_http(exc) if isinstance(exc, HTTPException) else "TOOL_ARGUMENTS_INVALID"
                    safe_result = {"tool": tool_name or "unknown", "status": "NEEDS_DECISION", "reason_code": reason_code}
                    args = {}
                    dispatch_status = "BLOCKED"
                    if reason_code == "ONLINE_CONSENT_REQUIRED":
                        mission = session.get(JourneyMission, mission.id)
                        intent = _task_state(mission)
                        _finish_run(
                            session,
                            journey,
                            member,
                            mission,
                            run,
                            intent,
                            status="NEEDS_DECISION",
                            event_type="TASK_NEEDS_DECISION",
                            reason_code=reason_code,
                        )
                        return {**_task_payload(mission, intent), "assistant_summary": None}

            if research_failed:
                task = intent[_TASK_KEY]
                task["status"] = "PARTIAL_READY"
                task["failure_code"] = "RESEARCH_UNAVAILABLE"
                task["updated_at"] = _now()
                mission.status = "PARTIAL_READY"
            safe_for_storage = _step_result_summary(tool_name, safe_result)
            safe_for_storage["elapsed_ms"] = round((time.perf_counter()-tool_clock)*1000)
            session.add(
                AgentRunStep(
                    id=str(uuid4()),
                    run_id=run.id,
                    sequence_no=step_no,
                    tool_name=tool_name if tool_name in _ALLOWED_TOOLS else "BLOCKED_TOOL",
                    arguments_json=_json_dump(_step_args_summary(tool_name, args)),
                    result_json=_json_dump(safe_for_storage),
                    decision=dispatch_status,
                    status=dispatch_status,
                    created_at=tool_started_at,
                    completed_at=_now(),
                )
            )
            mission.intent_json = _json_dump(intent)
            event_status = "PARTIAL_READY" if research_failed else "WORKING"
            if dispatch_status == "COMPLETED":
                _emit_event(
                    session,
                    journey,
                    member,
                    mission,
                    intent,
                    event_type="TOOL_COMPLETED",
                    status=event_status,
                    run_id=run.id,
                    step_sequence_no=step_no,
                    tool_name=tool_name,
                    reason_code=reason_code,
                )
            else:
                _emit_event(
                    session,
                    journey,
                    member,
                    mission,
                    intent,
                    event_type="TOOL_FAILED",
                    status="NEEDS_DECISION" if dispatch_status == "BLOCKED" else "PARTIAL_READY",
                    run_id=run.id,
                    step_sequence_no=step_no,
                    tool_name=tool_name if tool_name in _ALLOWED_TOOLS else "BLOCKED_TOOL",
                    reason_code=reason_code,
                )
            session.commit()
            if pause_for_decision is not None:
                mission = session.get(JourneyMission, mission.id)
                intent = _task_state(mission)
                _finish_run(
                    session,
                    journey,
                    member,
                    mission,
                    run,
                    intent,
                    status="NEEDS_DECISION",
                    event_type="TASK_NEEDS_DECISION",
                    reason_code=pause_for_decision,
                )
                return {**_task_payload(mission, intent), "assistant_summary": None}
            # Only the selected call is fed back. The next model turn sees the real
            # result projection and decides what to do next.
            if dispatch_status == "BLOCKED":
                messages.append(
                    {
                        "role": "user",
                        "content": _json_dump(
                            {"tool_status": "NEEDS_DECISION", "reason_code": reason_code}
                        ),
                    }
                )
            else:
                assistant_call = {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "id": call_id,
                            "type": "function",
                            "function": {
                                "name": tool_name,
                                "arguments": _json_dump(args),
                            },
                        },
                    ],
                }
                messages.extend(
                    [
                    assistant_call,
                    {
                        "role": "tool",
                        "tool_call_id": call_id,
                        "content": _json_dump(safe_result),
                    },
                    ]
                )
        mission = session.get(JourneyMission, mission.id)
        intent = _task_state(mission)
        exhausted_status = "PARTIAL_READY" if research_failed or any(day.get("slots") for day in (intent[_TASK_KEY].get("draft_artifact") or {}).get("days", [])) else "RESUMABLE"
        _finish_run(
            session,
            journey,
            member,
            mission,
            run,
            intent,
            status=exhausted_status,
            event_type="TASK_PARTIAL_READY" if research_failed else "TASK_RESUMABLE",
            reason_code="RESEARCH_INCOMPLETE" if research_failed else "MODEL_BUDGET_EXHAUSTED",
        )
        return {**_task_payload(mission, intent), "assistant_summary": assistant_summary}
    finally:
        if getattr(agent, "_owns_client", False):
            try:
                agent._client.close()
            except Exception:
                pass
