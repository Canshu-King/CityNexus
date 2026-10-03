from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

import httpx
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agent.ai_availability import (
    ai_availability_state,
    ai_state_from_failure_reason,
    reason_sentence,
)
from app.agent.gateway import AgentToolGateway
from app.agent.mission import mission_payload
from app.agent.runtime_identity import NATIVE_DEEPSEEK_TOOL_LOOP, runtime_identity
from app.agent.tool_catalog import RUNTIME_MCP_ALLOWLIST_V2
from app.core.audit import record_audit
from app.core.config import settings
from app.db.models import AgentRun, AgentRunStep, Journey, JourneyMission
from app.execution.traveler_twin import refresh_snapshot, snapshot_payload
from app.integrations.ai.responses import DeepSeekResponsesClient, DeepSeekResponsesError
from app.observability.tracing import persist_span
from app.schemas import AgentToolCall


class AgentRuntimeUnavailable(RuntimeError):
    """The configured model boundary cannot be used for this run."""


def reconcile_stale_agent_runs(
    session: Session, *, timeout_seconds: int = 900, now: datetime | None = None
) -> dict[str, int]:
    """Close model work left RUNNING by a process restart."""

    clock = now or datetime.now(timezone.utc)
    cutoff = clock.timestamp() - max(1, int(timeout_seconds))

    def old_enough(value: str | None) -> bool:
        try:
            parsed = datetime.fromisoformat(str(value))
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return parsed.timestamp() <= cutoff
        except (TypeError, ValueError):
            return True

    reason = "PROCESS_RESTARTED_DURING_AGENT_RUN"
    interrupted = 0
    missions_aborted = 0
    runs = session.scalars(select(AgentRun).where(AgentRun.status == "RUNNING")).all()
    for run in runs:
        if not old_enough(run.started_at or run.created_at):
            continue
        run.status = "INTERRUPTED"
        run.failure_reason = reason
        run.completed_at = clock.isoformat()
        mission = session.get(JourneyMission, run.mission_id)
        if mission is not None and mission.status in {"CREATED", "RUNNING"}:
            mission.status = "ABORTED"
            mission.failure_reason = reason
            mission.completed_at = clock.isoformat()
            missions_aborted += 1
        interrupted += 1

    # A crash can happen after a mission is marked RUNNING but before its
    # AgentRun row is flushed.
    missions = session.scalars(
        select(JourneyMission).where(JourneyMission.status == "RUNNING")
    ).all()
    for mission in missions:
        if not old_enough(mission.started_at or mission.created_at):
            continue
        live_run = session.scalar(
            select(AgentRun).where(
                AgentRun.mission_id == mission.id,
                AgentRun.status == "RUNNING",
            )
        )
        if live_run is not None:
            continue
        mission.status = "ABORTED"
        mission.failure_reason = reason
        mission.completed_at = clock.isoformat()
        missions_aborted += 1

    if interrupted or missions_aborted:
        session.commit()
    return {"agent_runs_interrupted": interrupted, "missions_aborted": missions_aborted}


_INSPECTION_TOOLS = {"inspect_journey", "inspect_twin", "list_replans"}
_NON_DOMAIN_TOOLS = {"search_city_services", "conclude_recovery"}
_MUTATION_TOOLS = RUNTIME_MCP_ALLOWLIST_V2 - _INSPECTION_TOOLS - _NON_DOMAIN_TOOLS
_RECOVERY_CONCLUSIONS = {
    "MUTATION_EXECUTED",
    "APPROVAL_PENDING",
    "NO_ACTION",
    "UNRESOLVED",
}


def _property(kind: str = "string", **extra: Any) -> dict[str, Any]:
    return {"type": kind, **extra}


def _tool(
    name: str, description: str, properties: dict[str, Any], required: list[str]
) -> dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": {
                "type": "object",
                "additionalProperties": False,
                "properties": properties,
                "required": required,
            },
        },
    }


def citynexus_tool_definitions() -> list[dict[str, Any]]:
    journey = {"journey_id": _property("string", description="Server-owned Journey UUID")}
    return [
        _tool(
            "inspect_journey",
            "Inspect the persisted Journey before acting.",
            journey,
            ["journey_id"],
        ),
        _tool(
            "inspect_twin",
            "Inspect the current JourneyTwin, server-owned standby portfolio, and current trigger compatibility.",
            {**journey, "trigger_event_id": _property("string")},
            ["journey_id"],
        ),
        _tool(
            "list_replans",
            "List existing server-generated recovery proposals.",
            {**journey, "trigger_event_id": _property("string")},
            ["journey_id"],
        ),
        _tool(
            "conclude_recovery",
            "Record the server-owned recovery conclusion after inspection and any chosen action. Prose alone is not a machine-resolved outcome.",
            {
                **journey,
                "outcome": _property(
                    "string",
                    enum=[
                        "MUTATION_EXECUTED",
                        "APPROVAL_PENDING",
                        "NO_ACTION",
                        "UNRESOLVED",
                        "CLARIFICATION_REQUIRED",
                    ],
                ),
                "reason": _property("string"),
                "horizon_decision": _property(
                    "string", enum=["TAKE_NOW", "DEFER", "NO_ACTION"]
                ),
                "question": _property("string", description="One human-value question; never a provider fact request."),
                "option_keys": _property("array", items=_property("string")),
                "preference_dimension": _property("string"),
            },
            ["journey_id", "outcome"],
        ),
        _tool(
            "search_city_services",
            "Search server-owned CityService alternatives; never invent candidate IDs.",
            {
                **journey,
                "q": _property("string"),
                "category": _property("string"),
                "service_type": _property("string"),
            },
            ["journey_id"],
        ),
        _tool(
            "acquire_place_facts",
            "Acquire provider-backed facts for one existing Place; missing facts remain UNKNOWN.",
            {
                **journey,
                "place_id": _property("string"),
                "source_url": _property("string"),
                "source_class": _property(
                    "string",
                    enum=[
                        "OFFICIAL_WEB",
                        "OFFICIAL_OPERATOR",
                        "OFFICIAL_TICKETING",
                        "MUNICIPAL_AUTHORITY",
                    ],
                    description="Use only a verified official or municipal source class; never use OSM/provider as an official source.",
                ),
            },
            ["journey_id", "place_id"],
        ),
        _tool(
            "estimate_place_facts",
            "Estimate opening and cost for strategy comparison. In the coursework lab, the Agent may provide bounded hypotheses when peer evidence is absent; each remains ESTIMATED_AGENT, never canonical/provider truth, and can support selection only inside the explicit isolated lab estimate envelope after live mobility and deterministic gates pass.",
            {
                **journey,
                "place_id": _property("string"),
                "estimated_open_minutes": _property("integer", minimum=0, maximum=1440),
                "estimated_close_minutes": _property("integer", minimum=0, maximum=1440),
                "estimated_cost_minor": _property("integer", minimum=0),
            },
            ["journey_id", "place_id"],
        ),
        _tool(
            "generate_plans",
            "Generate deterministic candidate plans from server-owned Place IDs. This creates candidates only; it never selects or activates a plan.",
            {
                **journey,
                "place_ids": _property("array", items=_property("string")),
                "candidate_count": _property("integer", minimum=1, maximum=5),
                "planning_mode": _property("string"),
            },
            ["journey_id", "place_ids"],
        ),
        _tool(
            "request_replan",
            "Generate deterministic feasible recovery proposals for the disruption.",
            {
                **journey,
                "trigger_event_id": _property("string"),
                "candidate_count": _property("integer", minimum=1, maximum=5),
                "place_ids": _property(
                    "array",
                    items=_property("string"),
                    description="Optional bounded Place hints from search_city_services; the server revalidates every fact.",
                ),
            },
            ["journey_id", "trigger_event_id"],
        ),
        _tool(
            "accept_replan",
            "Accept a feasible proposal only when Gateway policy permits it.",
            {
                **journey,
                "proposal_id": _property("string"),
                "approval_id": _property("string"),
            },
            ["journey_id", "proposal_id"],
        ),
        _tool(
            "activate_standby",
            "Activate one server-owned STANDBY branch through its dedicated Gateway boundary; never use generic select_plan.",
            {**journey, "standby_plan_id": _property("string"), "trigger_event_id": _property("string"), "approval_id": _property("string")},
            ["journey_id", "standby_plan_id", "trigger_event_id"],
        ),
        _tool(
            "replace_activity",
            "Replace a mutable Activity through policy and deterministic feasibility.",
            {
                **journey,
                "activity_id": _property("string"),
                "replacement_activity_id": _property("string"),
                "replacement_place_id": _property(
                    "string",
                    description="Server-owned Place candidate returned by search_city_services",
                ),
                "approval_id": _property("string"),
            },
            ["journey_id", "activity_id"],
        ),
        _tool(
            "reschedule_activity",
            "Reschedule a mutable Activity through policy and deterministic feasibility.",
            {
                **journey,
                "activity_id": _property("string"),
                "start_at": _property("string"),
                "end_at": _property("string"),
                "approval_id": _property("string"),
            },
            ["journey_id", "activity_id", "start_at", "end_at"],
        ),
        _tool(
            "create_booking",
            "Create a provider booking only when the server policy permits it.",
            {
                **journey,
                "activity_id": _property("string"),
                "provider_key": _property("string"),
                "approval_id": _property("string"),
            },
            ["journey_id", "activity_id"],
        ),
        _tool(
            "cancel_refundable_booking",
            "Cancel a refundable booking only when the server policy permits it.",
            {
                **journey,
                "booking_id": _property("string"),
                "approval_id": _property("string"),
            },
            ["journey_id", "booking_id"],
        ),
        _tool(
            "request_commitment_change",
            "Request a protected Commitment change; the Gateway may require stronger proof.",
            {
                **journey,
                "commitment_id": _property("string"),
                "reason": _property("string"),
                "approval_id": _property("string"),
            },
            ["journey_id", "commitment_id", "reason"],
        ),
    ]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _json_text(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)


def _model_name() -> str:
    return settings.ai_model.removeprefix("deepseek/")


def _acceptance_requested(mission: JourneyMission) -> bool:
    """Whether this mission explicitly requires the Agent to accept a proposal."""
    text = str(mission.user_text or "").lower()
    if "不接受" in text or "do not accept" in text:
        return False
    return (
        mission.requested_autonomy != "PLAN_ONLY"
        and "accept_replan" in text
        and any(token in text for token in ("接受", "选择", "select", "accept"))
    )


def _system_prompt(session: Session, mission: JourneyMission, journey: Journey) -> str:
    traveler_twin = snapshot_payload(refresh_snapshot(session, journey.traveler_id))
    return (
        "You are the CityNexus Delegated Autonomous Journey Agent. "
        "Use only the CityNexus tools supplied by the server. "
        "Inspect the Journey and JourneyTwin before any mutation. "
        "Never invent IDs, prices, opening hours, provider status, or commitments. "
        "The Gateway and deterministic feasibility layer are authoritative: follow their decisions. "
        "You may autonomously act on ordinary reversible changes inside both the global policy and this mission. "
        "Protected activities and commitments must remain unchanged unless the Gateway explicitly permits a stronger action. "
        "A mutation is not complete merely because you described it: only the corresponding CityNexus tool response is evidence that it happened. "
        "If inspect_twin returns decision_sensitivity.decision_sensitive=true, do not guess the traveller's value choice. "
        "Call conclude_recovery with outcome CLARIFICATION_REQUIRED, one concise human-value question, and the exact server option_keys. "
        "Ask no question about opening, cost, or mobility; acquire those facts yourself. If decision_sensitive is false, do not ask. "
        "When the user or mission explicitly selects a feasible proposal, call accept_replan with that exact proposal ID before producing a final summary; do not stop after list_replans or claim that acceptance is in progress. "
        "For every mutating tool, summarize the returned executed/decision/result fields and never substitute model prose for the Gateway receipt. "
        "Do not reveal private chain-of-thought; final text should summarize actionable rationale and observed results.\n\n"
        f"Journey ID: {journey.id}\n"
        f"Mission: {_json_text(_model_mission_payload(mission))}\n"
        f"TravelerTwin soft context (not authority): {_json_text(traveler_twin)}\n"
        "Treat LEARNED_SOFT evidence as bounded ranking/explanation context only; "
        "never use it to expand budget, payment, Commitment, or autonomy authority.\n"
        "The current disruption, if any, is discoverable from the server-owned JourneyTwin and event inspection; "
        "do not assume or repeat an event identifier from mission text.\n"
        "If inspection exposes multiple actionable events, do not use recency as relevance: choose one by passing its event_id to inspect_twin or list_replans. "
        "If the bounded remaining-opportunity horizon shows a feasible current window but a higher-value later window would consume the same optional budget, you may choose DEFER by calling conclude_recovery with outcome NO_ACTION and horizon_decision DEFER; this preserves the active plan. "
        "At the end of the recovery attempt, call conclude_recovery with exactly one server-owned outcome: "
        "MUTATION_EXECUTED, APPROVAL_PENDING, NO_ACTION, CLARIFICATION_REQUIRED, or UNRESOLVED; prose alone never resolves the recovery mission.\n"
        "The first tool call should be inspection. "
        "After inspection, choose the safest available CityNexus action within the server-returned capabilities and authority envelope; do not assume an existing future is sufficient, and do not mutate when no intervention is needed. "
        "After real Place IDs are returned, you may acquire or estimate their facts and call generate_plans; generation creates candidates only and never selects or activates them. "
        "Issue at most one tool call per assistant turn. "
        "If a tool reports SEARCH_SATURATION or SEARCH_BATCH_LIMIT, stop searching and choose a different available action. "
        + (
            "This is PLAN_ONLY: do not accept or execute a mutating action."
            if mission.requested_autonomy == "PLAN_ONLY"
            else "The mission permits execution only inside the server policy and envelope."
        )
    )


def _tool_args(raw_arguments: str) -> dict[str, Any]:
    parsed = json.loads(raw_arguments or "{}")
    if not isinstance(parsed, dict):
        raise TypeError("model tool arguments must be a JSON object")
    return parsed


def _model_mission_payload(mission: JourneyMission) -> dict[str, Any]:
    """Keep server-owned trigger identity out of model-visible mission text."""

    payload = dict(mission_payload(mission))
    payload.pop("trigger_event_id", None)
    return payload


def _compact_replan_for_model(item: Any) -> Any:
    """Keep proposal choice facts while removing route geometry from model context.

    The gateway persists the complete evidence receipt in ``AgentRunStep``.  The
    model only needs the proposal identity, deterministic score, feasibility
    deltas, and provider/provenance summaries to choose the next tool.  Feeding
    every captured polyline back into the next model turn made a real recovery
    finish with an empty response before it could call ``accept_replan``.
    """
    if isinstance(item, list):
        return [_compact_replan_for_model(value) for value in item]
    if not isinstance(item, dict):
        return item
    if "snapshot_id" in item and isinstance(item.get("facts"), list):
        fact_fields = {
            "origin_key",
            "destination_key",
            "minutes",
            "provider",
            "captured_at",
            "degraded",
            "fallback_reason",
            "route_provenance",
            "fact_quality",
            "mode",
            "time_basis",
            "distance_m",
            "walking_distance_m",
            "walking_min",
        }
        return {
            key: value
            for key, value in item.items()
            if key != "facts"
        } | {
            "facts": [
                {key: value for key, value in fact.items() if key in fact_fields}
                for fact in item["facts"]
                if isinstance(fact, dict)
            ]
        }
    projected = dict(item)
    for key in (
        "route_geometry",
        "route_geometry_json",
        "encoded_polyline",
        "raw_response",
    ):
        projected.pop(key, None)
    diff = projected.get("diff")
    if isinstance(diff, dict):
        compact_diff = dict(diff)
        compact_diff.pop("opportunity_window_evidence", None)
        evidence = compact_diff.get("verified_evidence")
        if isinstance(evidence, dict):
            compact_evidence = {
                key: value
                for key, value in evidence.items()
                if key not in {"mobility_snapshot", "route_geometry", "route_geometry_json"}
            }
            compact_diff["verified_evidence"] = compact_evidence
        compact_diff = {key: _compact_replan_for_model(value) for key, value in compact_diff.items()}
        projected["diff"] = compact_diff
    explanation = projected.get("explanation")
    if isinstance(explanation, dict):
        projected["explanation"] = {
            key: value
            for key, value in explanation.items()
            if key in {"summary", "reasons", "impact_type", "impact_provider", "source"}
        }
    return {
        key: _compact_replan_for_model(value)
        for key, value in projected.items()
        if key not in {
            "route_geometry",
            "route_geometry_json",
            "encoded_polyline",
            "raw_response",
        }
    }


def _result_for_model(result: Any) -> str:
    if isinstance(result, dict):
        projected = dict(result)
        if projected.get("tool") in {"list_replans", "request_replan"} and isinstance(projected.get("proposals"), list):
            projected["proposals"] = [
                _compact_replan_for_model(item) for item in projected["proposals"]
            ]
        if projected.get("tool") in {"list_replans", "request_replan"} and "proposal" in projected:
            projected["proposal"] = _compact_replan_for_model(projected["proposal"])
        return _json_text(projected)
    return _json_text({"result": result})


def _tool_result_advances_state(tool_name: str, result: Any) -> bool:
    """Return whether a tool result created a new domain observation epoch.

    Inspection calls are intentionally repeatable, but a repeat after a
    successful domain action must not be mistaken for an infinite loop. The
    runtime only advances the epoch on server-owned evidence of change; model
    prose and failed tool calls never reset the repetition guard.
    """

    if not isinstance(result, dict) or result.get("error"):
        return False
    if tool_name == "request_replan":
        proposal = result.get("proposal")
        return isinstance(proposal, dict) and bool(proposal.get("id"))
    return tool_name in _MUTATION_TOOLS and result.get("executed") is True


def _server_completion_contract(
    tool_steps: list[dict[str, Any]], *, run_status: str
) -> dict[str, Any]:
    """Classify recovery completion from persisted server/tool facts only."""

    active_mutations = {
        "accept_replan",
        "activate_standby",
        "replace_activity",
        "reschedule_activity",
        "create_booking",
        "cancel_refundable_booking",
        "request_commitment_change",
    }
    executed = any(
        item.get("tool_name") in active_mutations
        and isinstance(item.get("result"), dict)
        and item["result"].get("executed") is True
        for item in tool_steps
    )
    approval_pending = any(
        isinstance(item.get("result"), dict)
        and (
            item["result"].get("decision") in {"REQUIRE_CONFIRMATION", "REQUIRE_STEP_UP"}
            or item["result"].get("approval_required") is True
        )
        for item in tool_steps
    )
    # A failed request_replan is an attempted strategy, not a live proposal.
    # Only a server-created proposal blocks a typed NO_ACTION conclusion.
    proposal_created = any(
        item.get("tool_name") == "request_replan"
        and isinstance(item.get("result"), dict)
        and isinstance(item["result"].get("proposal"), dict)
        and bool(item["result"]["proposal"].get("id"))
        for item in tool_steps
    )
    conclusions = [
        item.get("result", {}).get("requested_outcome")
        for item in tool_steps
        if item.get("tool_name") == "conclude_recovery"
        and isinstance(item.get("result"), dict)
        and item.get("status") != "TOOL_ERROR"
    ]
    requested = conclusions[-1] if conclusions else None
    if requested == "MUTATION_EXECUTED" and executed:
        return {"kind": requested, "source": "server_trace"}
    if requested == "APPROVAL_PENDING" and approval_pending:
        return {"kind": requested, "source": "server_trace"}
    defer_conclusion = next(
        (item.get("result", {}).get("horizon_decision") for item in tool_steps
         if item.get("tool_name") == "conclude_recovery"
         and isinstance(item.get("result"), dict)
         and item.get("status") != "TOOL_ERROR"),
        None,
    )
    if requested == "NO_ACTION" and not executed and not approval_pending and (
        not proposal_created or defer_conclusion == "DEFER"
    ):
        return {"kind": requested, "source": "server_trace"}
    if requested == "UNRESOLVED":
        return {"kind": requested, "source": "server_trace"}
    if requested == "CLARIFICATION_REQUIRED" and any(
        item.get("tool_name") == "conclude_recovery"
        and isinstance(item.get("result"), dict)
        and item["result"].get("mission_status") == "WAITING_FOR_USER"
        and item["result"].get("clarification", {}).get("clarification_id")
        for item in tool_steps
    ):
        return {"kind": requested, "source": "server_trace", "mission_status": "WAITING_FOR_USER"}
    if executed:
        return {"kind": "MUTATION_EXECUTED", "source": "server_trace"}
    if approval_pending:
        return {"kind": "APPROVAL_PENDING", "source": "server_trace"}
    return {
        "kind": "UNRESOLVED",
        "source": "server_trace",
        "reason_code": "NO_TYPED_RECOVERY_CONCLUSION"
        if run_status == "COMPLETED"
        else "RUN_NOT_RESOLVED",
    }


def persisted_agent_run_payload(session: Session, run: AgentRun) -> dict[str, Any]:
    mission = session.get(JourneyMission, run.mission_id)
    steps = session.scalars(
        select(AgentRunStep).where(AgentRunStep.run_id == run.id).order_by(AgentRunStep.sequence_no)
    ).all()
    step_payloads = [
        {
            "id": step.id,
            "sequence_no": step.sequence_no,
            "tool_name": step.tool_name,
            "arguments": json.loads(step.arguments_json),
            "result": json.loads(step.result_json),
            "decision": step.decision,
            "status": step.status,
            "created_at": step.created_at,
            "completed_at": step.completed_at,
        }
        for step in steps
    ]
    return {
        "run_id": run.id,
        "mission_id": run.mission_id,
        "journey_id": run.journey_id,
        "provider_key": run.provider_key,
        "runtime_identity": (
            NATIVE_DEEPSEEK_TOOL_LOOP
            if run.provider_key == "deepseek"
            else "HERMES_COMPAT_ENDPOINT"
            if run.provider_key == "hermes"
            else runtime_identity()
        ),
        "model_key": run.model_key,
        "status": run.status,
        "completion_contract": _server_completion_contract(
            step_payloads, run_status=run.status
        ),
        "outcome": run.outcome,
        "failure_reason": run.failure_reason,
        # The read route answers with the same enumeration the health endpoint uses. A run that
        # stored a reason reports that reason; a run that stored none reports the current state,
        # which is a statement about the switch and the credential, not about this run.
        "ai_state": (
            ai_state_from_failure_reason(run.failure_reason)
            if run.failure_reason
            else ai_availability_state()
        ),
        "created_at": run.created_at,
        "started_at": run.started_at,
        "completed_at": run.completed_at,
        "mission_status": mission.status if mission else None,
        "mission": mission_payload(mission) if mission else None,
        "tool_steps": step_payloads,
    }


class DeepSeekJourneyAgent:
    provider_key = "deepseek"
    runtime_identity = NATIVE_DEEPSEEK_TOOL_LOOP
    # This is the server-owned identity used for calls emitted by this local
    # tool loop. Native MCP callers use an explicit mcp-client identity.
    agent_id = "citynexus-agent"

    def __init__(self, *, client: httpx.Client | None = None):
        if not settings.ai_api_key:
            raise AgentRuntimeUnavailable("DeepSeek API key is not configured")
        self.model_key = _model_name()
        self._client = client or httpx.Client(timeout=settings.impact_timeout_seconds)
        self._owns_client = client is None
        self._responses = DeepSeekResponsesClient(
            api_key=settings.ai_api_key,
            model=self.model_key,
            base_url=settings.deepseek_api_url,
            reasoning_effort=settings.deepseek_reasoning_effort,
            timeout_seconds=settings.impact_timeout_seconds,
            client=self._client,
        )

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def _complete(self, messages: list[dict[str, Any]]) -> dict[str, Any]:
        try:
            if not hasattr(self, "_responses"):
                self._responses = DeepSeekResponsesClient(
                    api_key=settings.ai_api_key or "compatibility-test-key",
                    model=self.model_key,
                    base_url=settings.deepseek_api_url,
                    reasoning_effort=getattr(settings, "deepseek_reasoning_effort", "high"),
                    timeout_seconds=settings.impact_timeout_seconds,
                    client=self._client,
                )
            result = self._responses.complete(
                messages,
                tools=citynexus_tool_definitions(),
                reasoning_effort=settings.deepseek_reasoning_effort,
            )
            return {
                "content": result.text,
                "tool_calls": list(result.tool_calls),
                "_response_items": list(result.continuation_items),
            }
        except (DeepSeekResponsesError, KeyError, IndexError, TypeError, ValueError) as exc:
            raise AgentRuntimeUnavailable("DeepSeek Agent completion failed") from exc

    def run(
        self,
        session: Session,
        *,
        journey: Journey,
        mission: JourneyMission,
        max_steps: int = 12,
    ) -> dict[str, Any]:
        now = _now()
        trace_id = str(uuid4())
        run = AgentRun(
            id=str(uuid4()),
            mission_id=mission.id,
            journey_id=journey.id,
            provider_key=self.provider_key,
            model_key=self.model_key,
            status="RUNNING",
            created_at=now,
            started_at=now,
        )
        session.add(run)
        mission.status = "RUNNING"
        mission.started_at = now
        record_audit(
            session,
            action="agent.run.started",
            entity_type="AgentRun",
            entity_id=run.id,
            journey_id=journey.id,
            actor_type="AI_AGENT",
            actor_id="deepseek-agent",
            after={"run_id": run.id, "mission_id": mission.id, "model": self.model_key},
            trace_id=trace_id,
        )
        session.flush()
        # The run envelope must survive a process/request interruption before
        # the first external model call. A flush only assigns IDs inside the
        # current transaction; it is not durable evidence.
        session.commit()
        persist_span(
            session,
            journey_id=journey.id,
            trace_id=trace_id,
            name="mission.compile",
            attributes={
                "mission_id": mission.id,
                "compiler_provider_key": mission.compiler_provider_key,
                "compiler_model_key": mission.compiler_model_key,
            },
        )
        persist_span(
            session,
            journey_id=journey.id,
            trace_id=trace_id,
            name="traveler_twin.lookup",
            attributes={
                "traveler_id": journey.traveler_id,
                "source": "server_persisted_snapshot",
            },
        )
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": _system_prompt(session, mission, journey)},
            {
                "role": "user",
                "content": mission.user_text,
            },
        ]
        inspected = False
        final_text = ""
        sequence = 0
        tool_trace: list[dict[str, Any]] = []
        # A repeated inspection is only a loop while the domain state is
        # unchanged. request_replan/accepted mutations advance this epoch so
        # the model can inspect newly-created server facts before deciding.
        state_epoch = 0
        seen_calls: set[tuple[str, str, int]] = set()
        tool_counts: dict[str, int] = {}
        acceptance_nudge_sent = False
        try:
            for _ in range(max_steps):
                batch_search_seen = False
                message = self._complete(messages)
                for receipt in getattr(self, "external_attempts", [])[len(
                    [item for item in tool_trace if item.get("tool_name") == "external_model_call"
                ]):]:
                    sequence += 1
                    step_now = _now()
                    result = {
                        **receipt,
                        "run_id": run.id,
                        "mission_id": mission.id,
                    }
                    session.add(AgentRunStep(
                        id=str(uuid4()), run_id=run.id, sequence_no=sequence,
                        tool_name="external_model_call",
                        arguments_json=_json_text({"provider": receipt.get("provider"), "model": receipt.get("model")}),
                        result_json=_json_text(result), decision="FAILED_EXTERNAL",
                        status="FAILED_EXTERNAL", created_at=step_now, completed_at=step_now,
                    ))
                    tool_trace.append({
                        "sequence_no": sequence, "tool_name": "external_model_call",
                        "arguments": {"provider": receipt.get("provider"), "model": receipt.get("model")},
                        "result": result, "decision": "FAILED_EXTERNAL", "status": "FAILED_EXTERNAL",
                        "created_at": step_now, "completed_at": step_now,
                    })
                session.commit()
                run.model_key = self.model_key
                tool_calls = message.get("tool_calls") or []
                content = message.get("content") or ""
                persist_span(
                    session,
                    journey_id=journey.id,
                    trace_id=trace_id,
                    name="deepseek.call",
                    attributes={
                        "provider_key": self.provider_key,
                        "model_key": self.model_key,
                        "tool_call_count": len(tool_calls),
                    },
                )
                if not tool_calls:
                    accept_executed = any(
                        item.get("tool_name") == "accept_replan"
                        and isinstance(item.get("result"), dict)
                        and item["result"].get("executed") is True
                        for item in tool_trace
                    )
                    has_proposal_evidence = any(
                        item.get("tool_name") in {"request_replan", "list_replans"}
                        for item in tool_trace
                    )
                    if (
                        _acceptance_requested(mission)
                        and has_proposal_evidence
                        and not accept_executed
                        and not acceptance_nudge_sent
                    ):
                        acceptance_nudge_sent = True
                        messages.append(
                            {
                                "role": "user",
                                "content": (
                                    "Your requested acceptance has not been executed. "
                                    "Do not finish with prose. Use the exact feasible proposal ID "
                                    "from the latest CityNexus tool result and emit one accept_replan "
                                    "tool call now; wait for its Gateway response before summarizing."
                                ),
                            }
                        )
                        continue
                    final_text = str(content)
                    break
                assistant_message = {
                    "role": "assistant",
                    "content": content,
                    "tool_calls": tool_calls,
                    "_response_items": message.get("_response_items") or [],
                }
                if message.get("reasoning_content"):
                    assistant_message["reasoning_content"] = message["reasoning_content"]
                messages.append(assistant_message)
                for call in tool_calls:
                    function = call.get("function") or {}
                    tool_name = str(function.get("name") or "")
                    call_id = str(call.get("id") or f"tool-call-{sequence}")
                    raw_arguments = str(function.get("arguments") or "{}")
                    search_batch_limited = tool_name == "search_city_services" and batch_search_seen
                    if tool_name == "search_city_services":
                        batch_search_seen = True
                    try:
                        arguments = _tool_args(raw_arguments)
                    except (TypeError, ValueError, json.JSONDecodeError) as exc:
                        # A streamed provider can terminate a tool-call fragment
                        # mid-JSON.  Never execute guessed arguments and never let
                        # one malformed model frame turn the whole AgentRun into
                        # an unhandled HTTP 500; return a machine-visible tool
                        # error so the model can repair or stop.
                        sequence += 1
                        arguments = {"_raw_arguments": raw_arguments[:1000]}
                        result = {
                            "tool": tool_name,
                            "error": "MALFORMED_TOOL_ARGUMENTS",
                            "detail": type(exc).__name__,
                            "decision": "REJECT_MALFORMED_ARGUMENTS",
                        }
                        step_now = _now()
                        step = AgentRunStep(
                            id=str(uuid4()), run_id=run.id, sequence_no=sequence,
                            tool_name=tool_name, arguments_json=_json_text(arguments),
                            result_json=_json_text(result), decision=result["decision"],
                            status="TOOL_ERROR", created_at=step_now, completed_at=step_now,
                        )
                        session.add(step)
                        tool_trace.append({
                            "sequence_no": sequence, "tool_name": tool_name,
                            "arguments": arguments, "result": result,
                            "decision": result["decision"], "status": "TOOL_ERROR",
                            "created_at": step_now, "completed_at": step_now,
                        })
                        messages.append({
                            "role": "tool", "tool_call_id": call_id,
                            "content": _result_for_model(result),
                        })
                        continue
                    signature = json.dumps(arguments, ensure_ascii=False, sort_keys=True)
                    repetition_key = (tool_name, signature, state_epoch)
                    if repetition_key in seen_calls:
                        result = {
                            "tool": tool_name,
                            "error": "tool loop repetition stopped",
                            "decision": "STOP_REPETITION",
                        }
                        sequence += 1
                        step_now = _now()
                        step = AgentRunStep(
                            id=str(uuid4()), run_id=run.id, sequence_no=sequence,
                            tool_name=tool_name, arguments_json=_json_text(arguments),
                            result_json=_json_text(result), decision="STOP_REPETITION",
                            status="TOOL_ERROR", created_at=step_now, completed_at=step_now,
                        )
                        session.add(step)
                        tool_trace.append({"sequence_no": sequence, "tool_name": tool_name, "arguments": arguments, "result": result, "decision": "STOP_REPETITION", "status": step.status})
                        final_text = "Agent stopped a repeated tool request before another domain action."
                        messages.append({"role": "tool", "tool_call_id": call_id, "content": _result_for_model(result)})
                        continue
                    seen_calls.add(repetition_key)
                    sequence += 1
                    arguments.setdefault("journey_id", journey.id)
                    arguments.setdefault("mission_id", mission.id)
                    arguments["request_id"] = f"agent-run-{run.id}-{sequence}"
                    arguments.setdefault("agent_id", self.agent_id)
                    tool_counts[tool_name] = tool_counts.get(tool_name, 0) + 1
                    search_saturated = (
                        tool_name == "search_city_services"
                        and tool_counts[tool_name] > 3
                    )
                    if search_batch_limited:
                        result = {
                            "tool": tool_name,
                            "error": "SEARCH_BATCH_LIMIT",
                            "decision": "STOP_SEARCH_BATCH",
                            "message": "Only one city search is executed per assistant turn; choose a different action on the next turn.",
                        }
                    elif search_saturated:
                        result = {
                            "tool": tool_name,
                            "error": "SEARCH_SATURATION",
                            "decision": "STOP_SEARCH_SATURATION",
                            "message": "Search budget exhausted for this run; choose a different strategy or source.",
                        }
                    elif tool_name not in RUNTIME_MCP_ALLOWLIST_V2:
                        result: dict[str, Any] = {
                            "tool": tool_name,
                            "error": "tool is outside the CityNexus V2 allowlist",
                        }
                    elif tool_name in _MUTATION_TOOLS and not inspected:
                        result = {
                            "tool": tool_name,
                            "error": "inspect_journey or inspect_twin is required before mutation",
                        }
                    elif mission.requested_autonomy == "PLAN_ONLY" and tool_name in {
                        "accept_replan",
                        "activate_standby",
                        "replace_activity",
                        "reschedule_activity",
                        "create_booking",
                        "cancel_refundable_booking",
                        "request_commitment_change",
                    }:
                        result = {
                            "tool": tool_name,
                            "error": "mission is PLAN_ONLY; proposal generation is allowed but mutation is not",
                        }
                    else:
                        try:
                            if tool_name == "conclude_recovery" and isinstance(
                                arguments.get("reason"), str
                            ) and len(arguments["reason"]) > 500:
                                # The model may explain a long decision, but the
                                # persisted typed conclusion has a strict schema
                                # boundary.  Preserve a bounded receipt instead
                                # of spending another model turn on a 422.
                                arguments["reason"] = arguments["reason"][:497] + "..."
                            payload = AgentToolCall.model_validate(arguments)
                            result = AgentToolGateway(session).dispatch(tool_name, payload)
                            if tool_name in _INSPECTION_TOOLS:
                                inspected = True
                        except HTTPException as exc:
                            result = {
                                "tool": tool_name,
                                "error": str(exc.detail),
                                "status_code": exc.status_code,
                            }
                        except (TypeError, ValueError, KeyError) as exc:
                            result = {
                                "tool": tool_name,
                                "error": str(exc),
                                "status_code": 422,
                            }
                    step_now = _now()
                    step = AgentRunStep(
                        id=str(uuid4()),
                        run_id=run.id,
                        sequence_no=sequence,
                        tool_name=tool_name,
                        arguments_json=_json_text(arguments),
                        result_json=_json_text(result),
                        decision=str(result.get("decision")) if isinstance(result, dict) else None,
                        status="COMPLETED" if "error" not in result else "TOOL_ERROR",
                        created_at=step_now,
                        completed_at=step_now,
                    )
                    session.add(step)
                    tool_trace.append(
                        {
                            "sequence_no": sequence,
                            "tool_name": tool_name,
                            "arguments": arguments,
                            "result": result,
                            "decision": result.get("decision")
                            if isinstance(result, dict)
                            else None,
                            "status": step.status,
                            "created_at": step_now,
                            "completed_at": step_now,
                        }
                    )
                    record_audit(
                        session,
                        action="agent.run.tool",
                        entity_type="AgentRun",
                        entity_id=run.id,
                        journey_id=journey.id,
                        actor_type="AI_AGENT",
                        actor_id="deepseek-agent",
                        after={
                            "run_id": run.id,
                            "sequence_no": sequence,
                            "tool": tool_name,
                            "decision": result.get("decision")
                            if isinstance(result, dict)
                            else None,
                            "status": "TOOL_ERROR" if "error" in result else "COMPLETED",
                        },
                        trace_id=trace_id,
                    )
                    persist_span(
                        session,
                        journey_id=journey.id,
                        trace_id=trace_id,
                        name="agent.tool_call",
                        attributes={
                            "tool_name": tool_name,
                            "status": step.status,
                            "decision": result.get("decision")
                            if isinstance(result, dict)
                            else None,
                        },
                    )
                    if tool_name == "search_city_services":
                        persist_span(
                            session,
                            journey_id=journey.id,
                            trace_id=trace_id,
                            name="real_city.discovery",
                            attributes={"tool_name": tool_name},
                        )
                    if tool_name == "request_replan":
                        persist_span(
                            session,
                            journey_id=journey.id,
                            trace_id=trace_id,
                            name="cp_sat.solve",
                            attributes={
                                "solver_mode": arguments.get("solver_mode"),
                                "proposal_id": result.get("proposal", {}).get("id")
                                if isinstance(result.get("proposal"), dict)
                                else None,
                            },
                        )
                    if tool_name in _MUTATION_TOOLS:
                        persist_span(
                            session,
                            journey_id=journey.id,
                            trace_id=trace_id,
                            name="gateway.policy_decision",
                            attributes={
                                "tool_name": tool_name,
                                "decision": result.get("decision")
                                if isinstance(result, dict)
                                else None,
                            },
                        )
                        if isinstance(result, dict) and result.get("executed"):
                            persist_span(
                                session,
                                journey_id=journey.id,
                                trace_id=trace_id,
                                name="domain.mutation",
                                attributes={"tool_name": tool_name, "executed": True},
                            )
                    if _tool_result_advances_state(tool_name, result):
                        state_epoch += 1
                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": call_id,
                            "content": _result_for_model(result),
                        }
                    )
                session.flush()
                if final_text:
                    break
            else:
                final_text = "Agent reached the configured tool-step limit."
            run.status = "COMPLETED" if final_text else "PARTIAL"
            clarification = any(
                item.get("tool_name") == "conclude_recovery"
                and isinstance(item.get("result"), dict)
                and item["result"].get("requested_outcome") == "CLARIFICATION_REQUIRED"
                and item["result"].get("mission_status") == "WAITING_FOR_USER"
                for item in tool_trace
            )
            mission.status = "WAITING_FOR_USER" if clarification else ("COMPLETED" if run.status == "COMPLETED" else "PARTIAL")
            run.outcome = final_text or "Tool loop completed without a final summary."
        except AgentRuntimeUnavailable as exc:
            for receipt in getattr(self, "external_attempts", []):
                if any(
                    item.get("tool_name") == "external_model_call"
                    and item.get("result", {}).get("model") == receipt.get("model")
                    and item.get("result", {}).get("elapsed_ms") == receipt.get("elapsed_ms")
                    for item in tool_trace
                ):
                    continue
                sequence += 1
                step_now = _now()
                result = {**receipt, "run_id": run.id, "mission_id": mission.id}
                session.add(AgentRunStep(
                    id=str(uuid4()), run_id=run.id, sequence_no=sequence,
                    tool_name="external_model_call",
                    arguments_json=_json_text({"provider": receipt.get("provider"), "model": receipt.get("model")}),
                    result_json=_json_text(result), decision="FAILED_EXTERNAL",
                    status="FAILED_EXTERNAL", created_at=step_now, completed_at=step_now,
                ))
                tool_trace.append({
                    "sequence_no": sequence, "tool_name": "external_model_call",
                    "arguments": {"provider": receipt.get("provider"), "model": receipt.get("model")},
                    "result": result, "decision": "FAILED_EXTERNAL", "status": "FAILED_EXTERNAL",
                })
            run.status = "FAILED_EXTERNAL"
            mission.status = "DEGRADED"
            run.failure_reason = str(exc)
            mission.failure_reason = str(exc)
            raise
        finally:
            completed = _now()
            run.completed_at = completed
            mission.completed_at = completed
            record_audit(
                session,
                action="agent.run.completed",
                entity_type="AgentRun",
                entity_id=run.id,
                journey_id=journey.id,
                actor_type="AI_AGENT",
                actor_id="deepseek-agent",
                after={
                    "run_id": run.id,
                    "mission_id": mission.id,
                    "status": run.status,
                    "outcome": run.outcome,
                    "failure_reason": run.failure_reason,
                },
                trace_id=trace_id,
            )
            session.commit()
        return {
            "run_id": run.id,
            "mission_id": mission.id,
            "status": run.status,
            "completion_contract": _server_completion_contract(
                tool_trace, run_status=run.status
            ),
            "provider_key": run.provider_key,
            "runtime_identity": self.runtime_identity,
            "model_key": run.model_key,
            "outcome": run.outcome,
            "failure_reason": run.failure_reason,
            "trace_id": trace_id,
            "tool_steps": tool_trace,
        }


def unavailable_run_payload(
    session: Session, *, journey: Journey, mission: JourneyMission
) -> dict[str, Any]:
    now = _now()
    run = AgentRun(
        id=str(uuid4()),
        mission_id=mission.id,
        journey_id=journey.id,
        provider_key="deepseek",
        model_key=_model_name(),
        status="SKIPPED_EXTERNAL_DEPENDENCY",
        # r2 stored this fixed literal no matter why the door above declined. The word now comes
        # from the same table `/health` reads, so a run can never claim a missing credential while
        # the operator's switch is what the server actually reports.
        failure_reason=reason_sentence(ai_availability_state()),
        created_at=now,
        started_at=now,
        completed_at=now,
    )
    session.add(run)
    mission.status = "SKIPPED_EXTERNAL_DEPENDENCY"
    mission.failure_reason = run.failure_reason
    mission.completed_at = now
    record_audit(
        session,
        action="agent.run.skipped",
        entity_type="AgentRun",
        entity_id=run.id,
        journey_id=journey.id,
        actor_type="AI_AGENT",
        actor_id="deepseek-agent",
        after={"run_id": run.id, "mission_id": mission.id, "reason": run.failure_reason},
    )
    session.commit()
    return persisted_agent_run_payload(session, run)
