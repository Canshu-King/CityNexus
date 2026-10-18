from __future__ import annotations

import hashlib
import json
import re
from statistics import median
from datetime import datetime, timedelta, timezone
from typing import Any, Callable
from uuid import UUID, uuid4

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.agent.approval import (
    approval_fingerprint,
    approval_payload,
    consume_action_approval,
    create_or_reuse_approval,
)
from app.agent.contracts import (
    AgentAction,
    AuthoritativeActionFacts,
    AuthorizationDecision,
    AuthorizationResult,
)
from app.agent.delegation_policy import (
    evaluate_action,
    get_or_create_policy,
    policy_from_model,
)
from app.agent.tool_catalog import RUNTIME_MCP_ALLOWLIST_V2, tool_catalog, tool_catalog_v2
from app.commerce.idempotency import canonical_request_signature
from app.commerce.service_impl import CommerceConflict, CommerceValidationError
from app.core.audit import record_audit
from app.db.models import (
    Activity,
    Booking,
    CityService,
    Commitment,
    Event,
    IdempotencyKey,
    Journey,
    JourneyMission,
    MobilityFact,
    PaymentTransaction,
    Place,
    PlanVersion,
    ReplanProposal,
    WebObservation,
)
from app.execution.launch_origin import grounded_launch_origin
from app.execution.route_session_contract import (
    ROUTE_PROVIDER_POLICY_VERSION,
    ROUTE_TRUTH_POLICY_VERSION,
    RouteRequest,
)
from app.route_session_operations import operation_payload as route_operation_payload
from app.route_session_operations import submit_operation as submit_route_operation
from app.fact_acquisition import acquire_place_facts
from app.integrations.discovery.real_city import capture_real_city_candidates
from app.schemas import AgentToolCall, ReplanGenerateRequest
from app.services import (
    _place_verified_cost,
    _place_window,
    activity_schema,
    generate_plans as compose_plans,
    journey_schema,
    plan_schema,
    service_schema,
)


def _agent_key(kind: str, *parts: object) -> str:
    material = "|".join(str(part) for part in parts)
    digest = hashlib.sha256(material.encode("utf-8")).hexdigest()
    return f"agent.{kind}:{digest}"


def _read_idempotent(session: Session, key: str, signature: str) -> dict[str, Any] | None:
    row = session.get(IdempotencyKey, key)
    if row is None:
        return None
    if row.request_hash != signature:
        raise HTTPException(409, "same agent request id used for a different request")
    stored = json.loads(row.response_json or "{}")
    if not stored:
        raise HTTPException(409, "agent idempotency record is incomplete")
    return stored


def _write_idempotent(
    session: Session,
    *,
    key: str,
    operation: str,
    signature: str,
    response: dict[str, Any],
) -> None:
    from datetime import datetime, timedelta, timezone

    now = datetime.now(timezone.utc)
    session.add(
        IdempotencyKey(
            key=key,
            operation=operation,
            request_hash=signature,
            response_status=200,
            response_json=json.dumps(response, sort_keys=True, default=str),
            created_at=now.isoformat(),
            expires_at=(now + timedelta(days=7)).isoformat(),
        )
    )


_CURRENT_REPLAN_PROPOSAL_FIELDS = frozenset({
    "id", "journey_id", "trigger_event_id", "base_plan_version_id",
    "proposed_plan_version_id", "status", "hard_constraints_passed",
    "locked_commitments_preserved", "utility_score", "score_breakdown",
    "diff", "explanation",
})
_LEGACY_REPLAN_PROPOSAL_FIELDS = frozenset({
    "id", "status", "hard_constraints_passed", "locked_commitments_preserved",
})
_REPLAN_CACHE_UNAVAILABLE = "AGENT_IDEMPOTENCY_RESPONSE_SCHEMA_UNAVAILABLE"


def _upgrade_cached_request_replan_response(
    session: Session,
    stored: dict[str, Any],
    *,
    journey_id: str,
    trigger_event_id: str,
) -> dict[str, Any]:
    """Project only persisted legacy proposals while keeping frozen response facts."""
    proposals = stored.get("proposals")
    if not isinstance(proposals, list) or not proposals:
        raise HTTPException(409, _REPLAN_CACHE_UNAVAILABLE)

    upgraded: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    changed = False
    for cached in proposals:
        if not isinstance(cached, dict):
            raise HTTPException(409, _REPLAN_CACHE_UNAVAILABLE)
        proposal_id = cached.get("id")
        if not isinstance(proposal_id, str) or not proposal_id.strip() or proposal_id in seen_ids:
            raise HTTPException(409, _REPLAN_CACHE_UNAVAILABLE)
        seen_ids.add(proposal_id)
        if _CURRENT_REPLAN_PROPOSAL_FIELDS.issubset(cached):
            if (
                cached["journey_id"] != journey_id
                or cached["trigger_event_id"] != trigger_event_id
                or not isinstance(cached["status"], str)
                or not isinstance(cached["hard_constraints_passed"], bool)
                or not isinstance(cached["locked_commitments_preserved"], bool)
                or isinstance(cached["utility_score"], bool)
                or not isinstance(cached["utility_score"], (int, float))
                or not isinstance(cached["score_breakdown"], dict)
                or not isinstance(cached["diff"], dict)
                or not isinstance(cached["explanation"], dict)
            ):
                raise HTTPException(409, _REPLAN_CACHE_UNAVAILABLE)
            upgraded.append(cached)
            continue
        if set(cached) != _LEGACY_REPLAN_PROPOSAL_FIELDS:
            raise HTTPException(409, _REPLAN_CACHE_UNAVAILABLE)
        if (
            not isinstance(cached["status"], str)
            or not isinstance(cached["hard_constraints_passed"], bool)
            or not isinstance(cached["locked_commitments_preserved"], bool)
        ):
            raise HTTPException(409, _REPLAN_CACHE_UNAVAILABLE)
        row = session.get(ReplanProposal, proposal_id)
        if (row is None or row.journey_id != journey_id
                or row.trigger_event_id != trigger_event_id):
            raise HTTPException(409, _REPLAN_CACHE_UNAVAILABLE)
        from app.main import _replan_payload

        current = _replan_payload(row)
        for field in ("status", "hard_constraints_passed", "locked_commitments_preserved"):
            current[field] = cached[field]
        upgraded.append(current)
        changed = True
    return {**stored, "proposals": upgraded} if changed else stored


def _json(value: object) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    return value


def _require_journey(session: Session, journey_id: UUID | None) -> Journey:
    if journey_id is None:
        raise HTTPException(422, "journey_id is required for this Agent tool")
    journey = session.get(Journey, str(journey_id))
    if journey is None:
        raise HTTPException(404, f"Journey {journey_id} was not found")
    return journey


def _facts_for_accept(
    session: Session,
    proposal: ReplanProposal,
    journey: Journey,
) -> tuple[AuthoritativeActionFacts, dict[str, Any]]:
    try:
        diff = json.loads(proposal.diff_json or "{}")
    except json.JSONDecodeError:
        diff = {}
    verified = diff.get("verified_evidence", {})
    envelope = diff.get("after_feasibility_envelope", {})
    mobility = verified.get("mobility", {})
    impact_resolution = verified.get("impact_resolution", {})
    trigger = session.get(Event, proposal.trigger_event_id) if proposal.trigger_event_id else None
    preserved = bool(proposal.locked_commitments_preserved)
    preserved = preserved and diff.get("preserved_protected", True) is not False
    preserved = preserved and verified.get("commitment_preservation", {}).get("preserved", True)
    degraded_providers = envelope.get("degraded_providers") or []
    provider_degraded = bool(
        degraded_providers
        or mobility.get("degraded") is True
        or mobility.get("snapshot", {}).get("degraded") is True
    )
    base_current = journey.active_plan_version_id == proposal.base_plan_version_id
    trigger_actionable = trigger is not None and trigger.status in {"DETECTED", "ACKNOWLEDGED"}
    selected_activity_id = impact_resolution.get("selected_activity_id")
    selected_activity = (
        session.get(Activity, str(selected_activity_id)) if selected_activity_id else None
    )
    # Provider-verified incidents may carry an affected Activity directly even
    # when the semantic impact resolver did not produce an independent target.
    # The server still verifies ownership, active-plan membership and state;
    # the model's semantic judgement is allowed to remain AI_ONLY inside the
    # user's autonomy envelope.
    if selected_activity is None and trigger is not None and trigger.affected_activity_id:
        candidate = session.get(Activity, trigger.affected_activity_id)
        if (
            candidate is not None
            and candidate.plan_version_id == proposal.base_plan_version_id
            and candidate.status not in {"COMPLETED", "SKIPPED", "CANCELLED"}
        ):
            selected_activity = candidate
            selected_activity_id = candidate.id
    if selected_activity is None:
        # A semantic model judgement may identify a removable activity only in
        # the candidate diff. The server still owns the final target check:
        # resolve the first removed base-plan activity and verify its state and
        # ownership before applying the autonomy envelope.
        removed_ids = diff.get("removed") or []
        if isinstance(removed_ids, list):
            for raw_id in removed_ids:
                candidate = session.get(Activity, str(raw_id))
                if candidate is None:
                    candidate = session.scalar(
                        select(Activity).where(
                            Activity.plan_version_id == proposal.base_plan_version_id,
                            Activity.place_id == str(raw_id),
                            Activity.status.not_in(("COMPLETED", "SKIPPED", "CANCELLED")),
                        ).order_by(Activity.sequence_no).limit(1)
                    )
                if (
                    candidate is not None
                    and candidate.plan_version_id == proposal.base_plan_version_id
                    and candidate.status not in {"COMPLETED", "SKIPPED", "CANCELLED"}
                ):
                    selected_activity = candidate
                    selected_activity_id = candidate.id
                    break
    impact_target_server_validated = bool(
        selected_activity is not None
        and selected_activity.plan_version_id == proposal.base_plan_version_id
        and selected_activity.status not in {"COMPLETED", "SKIPPED", "CANCELLED"}
    )
    try:
        schedule_drift_min = abs(int(diff.get("end_time_delta_min") or 0))
    except (TypeError, ValueError):
        schedule_drift_min = 0
    try:
        loss_delta_minor = max(0, int(diff.get("loss_delta_minor") or 0))
    except (TypeError, ValueError):
        loss_delta_minor = 0
    facts = AuthoritativeActionFacts(
        hard_constraints_passed=bool(proposal.hard_constraints_passed),
        locked_commitments_preserved=preserved,
        c4_affected=not preserved,
        cost_delta_minor=int(diff.get("cost_delta_minor") or 0),
        provider_degraded=provider_degraded,
        event_severity=trigger.severity if trigger is not None else None,
        proposal_presented=proposal.status == "PRESENTED",
        base_plan_current=base_current,
        trigger_actionable=trigger_actionable,
        impact_maturity=(
            impact_resolution.get("maturity_stage")
            or ("AI_ONLY" if impact_target_server_validated else None)
        ),
        impact_target_server_validated=impact_target_server_validated,
        loss_delta_minor=loss_delta_minor,
        schedule_drift_min=schedule_drift_min,
        affected_activity_type=selected_activity.activity_type if selected_activity else None,
        commitment_management_requested=bool(diff.get("commitment_management_requested")),
        commitment_levels=tuple(
            str(item)
            for item in verified.get("commitment_preservation", {}).get("protected_levels", [])
            if item
        ),
    )
    evidence = {
        "hard_constraints_passed": facts.hard_constraints_passed,
        "locked_commitments_preserved": facts.locked_commitments_preserved,
        "c4_affected": facts.c4_affected,
        "cost_delta_minor": facts.cost_delta_minor,
        "provider_degraded": facts.provider_degraded,
        "event_severity": facts.event_severity,
        "proposal_presented": facts.proposal_presented,
        "base_plan_current": facts.base_plan_current,
        "trigger_actionable": facts.trigger_actionable,
        "impact_maturity": facts.impact_maturity,
        "impact_target_server_validated": facts.impact_target_server_validated,
        "loss_delta_minor": facts.loss_delta_minor,
        "schedule_drift_min": facts.schedule_drift_min,
        "affected_activity_type": facts.affected_activity_type,
        "commitment_management_requested": facts.commitment_management_requested,
        "commitment_levels": list(facts.commitment_levels),
    }
    return facts, evidence


class AgentToolGateway:
    """The only server entry point for the V1 Agent tool surface.

    The gateway accepts typed intent and resolves every policy and feasibility
    fact from CityNexus persistence. It never accepts a client supplied gate
    result, provider state, cost delta, or C4 assertion.
    """

    def __init__(self, session: Session):
        self.session = session

    def _native_plan_boundary(self, request: AgentToolCall) -> bool:
        """Keep native MCP runs proposal-only at the CityNexus boundary.

        Hermes receives the same V2 surface as other agents, but a native MCP
        caller cannot present a user-bound approval receipt merely by choosing
        a tool argument.  Treat the MCP transport identity and an explicit
        PLAN_ONLY mission as confirmation-required even when a traveler policy
        would otherwise allow automatic mutation.
        """

        actor = str(request.agent_id or "").strip().lower()
        if actor in {"mcp-client", "hermes", "hermes-native"}:
            return True
        if request.mission_id is not None:
            mission = self.session.get(JourneyMission, str(request.mission_id))
            return mission is not None and mission.requested_autonomy == "PLAN_ONLY"
        return False

    def _bound_authorization(
        self, request: AgentToolCall, auth: AuthorizationResult
    ) -> AuthorizationResult:
        if self._native_plan_boundary(request) and auth.decision == AuthorizationDecision.ALLOW_AUTO:
            return AuthorizationResult(
                AuthorizationDecision.REQUIRE_CONFIRMATION,
                auth.reason_codes + ("CITYNEXUS_NATIVE_PLAN_ONLY_BOUNDARY",),
                auth.policy_version,
            )
        return auth

    @staticmethod
    def catalog() -> list[dict[str, object]]:
        return tool_catalog()

    @staticmethod
    def catalog_v2() -> list[dict[str, object]]:
        return tool_catalog_v2()

    def dispatch(self, tool_name: str, request: AgentToolCall) -> dict[str, Any]:
        if tool_name not in RUNTIME_MCP_ALLOWLIST_V2:
            raise HTTPException(404, "Agent tool is not in the CityNexus allowlist")
        handlers = {
            "inspect_journey": self.inspect_journey,
            "inspect_twin": self.inspect_twin,
            "list_replans": self.list_replans,
            "search_city_services": self.search_city_services,
            "research_place_sources": self.research_place_sources,
            "estimate_place_facts": self.estimate_place_facts,
            "generate_plans": self.generate_plans,
            "discover_places": self.discover_places,
            "acquire_place_facts": self.acquire_place_facts,
            "compare_routes": self.compare_routes,
            "acquire_route": self.acquire_route,
            "request_replan": self.request_replan,
            "accept_replan": self.accept_replan,
            "replace_activity": self.replace_activity,
            "reschedule_activity": self.reschedule_activity,
            "create_booking": self.create_booking,
            "cancel_refundable_booking": self.cancel_refundable_booking,
            "request_commitment_change": self.request_commitment_change,
        }
        scope_journey_id = request.journey_id
        if scope_journey_id is None and request.proposal_id is not None:
            proposal = self.session.get(ReplanProposal, str(request.proposal_id))
            scope_journey_id = UUID(proposal.journey_id) if proposal is not None else None
        record_audit(
            self.session,
            action="agent_tool_requested",
            entity_type="AgentToolRequest",
            entity_id=request.request_id,
            journey_id=str(scope_journey_id) if scope_journey_id is not None else None,
            actor_type="AI_AGENT",
            actor_id=request.agent_id,
            after={
                "tool": tool_name,
                "request_id": request.request_id,
                "proposal_id": str(request.proposal_id) if request.proposal_id else None,
                "trigger_event_id": str(request.trigger_event_id)
                if request.trigger_event_id
                else None,
            },
        )
        # Persist the request even when the handler later returns a policy
        # denial or an idempotent receipt. This makes the feed an audit
        # projection rather than a React-side activity log.
        self.session.commit()
        return handlers[tool_name](request)

    def inspect_journey(self, request: AgentToolCall) -> dict[str, Any]:
        journey = _require_journey(self.session, request.journey_id)
        commitments = self.session.scalars(
            select(Commitment).where(
                Commitment.journey_id == journey.id,
                Commitment.status == "ACTIVE",
            )
        ).all()
        protected = [
            {
                "id": item.id,
                "activity_id": item.activity_id,
                "kind": item.kind,
                "level": item.level,
                "protected": item.level in {"C3_Guaranteed", "C4_Anchored"},
                "external_ref": item.external_ref,
            }
            for item in commitments
        ]
        return {
            "tool": "inspect_journey",
            "decision": AuthorizationDecision.ALLOW_AUTO.value,
            "journey": _json(journey_schema(journey)),
            "protected_commitments": [item for item in protected if item["protected"]],
        }

    def inspect_twin(self, request: AgentToolCall) -> dict[str, Any]:
        journey = _require_journey(self.session, request.journey_id)
        from app.main import _twin_snapshot

        savepoint = self.session.begin_nested()
        try:
            twin = _twin_snapshot(self.session, journey)
        finally:
            savepoint.rollback()
        return {
            "tool": "inspect_twin",
            "decision": AuthorizationDecision.ALLOW_AUTO.value,
            "twin": twin,
        }

    # The agent surface used to hand back *every* persisted proposal with its full
    # diff / explanation / score breakdown. Measured on the Hermes lane DB (22
    # proposals) one `list_replans` call returned 2,922,724 bytes — a single tool
    # read larger than any model's usable context, so the first thing an agent does
    # after a replan blew the window it was trying to reason about.
    #
    # The bound below degrades the OLDEST rows' heavy fields first (the newest
    # proposal is the one an agent actually acts on) and always says so in the
    # envelope. A small read — which is what every existing witness uses — still
    # gets the untouched 12-field shape, so this is not a contract loosening.
    LIST_REPLANS_MAX_ITEMS = 20
    LIST_REPLANS_BYTE_BUDGET = 200_000
    LIST_REPLANS_HEAVY_FIELDS = ("diff", "explanation", "score_breakdown")

    def list_replans(self, request: AgentToolCall) -> dict[str, Any]:
        journey = _require_journey(self.session, request.journey_id)
        from app.main import _replan_payload

        proposals = self.session.scalars(
            select(ReplanProposal)
            .where(ReplanProposal.journey_id == journey.id)
            .order_by(ReplanProposal.created_at.desc(), ReplanProposal.id.desc())
        ).all()
        total = len(proposals)
        items = [_replan_payload(item) for item in proposals[: self.LIST_REPLANS_MAX_ITEMS]]

        omitted: list[str] = []

        def payload_bytes() -> int:
            return len(json.dumps(items, ensure_ascii=False, default=str).encode("utf-8"))

        for item in reversed(items):
            if payload_bytes() <= self.LIST_REPLANS_BYTE_BUDGET:
                break
            for field in self.LIST_REPLANS_HEAVY_FIELDS:
                if field in item:
                    item.pop(field)
                    omitted.append(f"{item['id']}:{field}")

        return {
            "tool": "list_replans",
            "decision": AuthorizationDecision.ALLOW_AUTO.value,
            "proposals": items,
            "order": "newest_first",
            "total": total,
            "returned": len(items),
            "truncated": total > len(items),
            "byte_budget": self.LIST_REPLANS_BYTE_BUDGET,
            "detail_fields_omitted": omitted,
        }

    def research_place_sources(self, request: AgentToolCall) -> dict[str, Any]:
        """Return bounded, non-authoritative source leads for one server Place.

        Reform 2026-10-18, ported from the Revolution gateway: the agent may research a place
        while the journey is still a draft. The query is built here from the Journey and the
        Place -- the model supplies neither a name nor a URL -- and every captured row is stored
        with `authority_status=NON_AUTHORITATIVE`, so a lead never becomes a fact by being fetched.
        With no configured provider the answer says SOURCE_DISCOVERY_UNAVAILABLE; it does not
        invent leads to look complete.
        """
        if request.journey_id is None or not request.place_id:
            raise HTTPException(422, "journey_id and place_id are required")
        journey = _require_journey(self.session, request.journey_id)
        place = self.session.get(Place, request.place_id)
        if place is None or place.city_code != journey.city_code:
            raise HTTPException(404, "Place is not part of the Journey city")

        from app.core.config import settings
        from app.integrations.ai.responses import DeepSeekResponsesClient, DeepSeekResponsesError
        from app.integrations.ai.web_research import WebResearchProvider
        from app.integrations.web.research_service import build_source_query
        from app.integrations.web.searxng import SearXNGSearchProvider

        query = build_source_query(place, journey)
        drafts: list[Any] = []
        provider_status = "SOURCE_DISCOVERY_UNAVAILABLE"
        if settings.ai_api_key and settings.deepseek_web_search_enabled:
            client = DeepSeekResponsesClient(
                api_key=settings.ai_api_key,
                model=settings.ai_model,
                base_url=settings.deepseek_api_url,
                reasoning_effort="low",
                timeout_seconds=settings.impact_timeout_seconds,
            )
            try:
                drafts = list(WebResearchProvider(client).search(query)[:5])
                provider_status = "CAPTURED" if drafts else "NO_RESULTS"
            except DeepSeekResponsesError:
                provider_status = "FAILED_EXTERNAL"
        elif settings.searxng_url:
            provider = SearXNGSearchProvider(settings.searxng_url)
            try:
                drafts = list(provider.search(query, limit=5))
                provider_status = "CAPTURED" if drafts else "NO_RESULTS"
            except Exception:
                provider_status = "FAILED_EXTERNAL"
            finally:
                provider.close()

        rows: list[WebObservation] = []
        for item in drafts[:5]:
            fingerprint = str(getattr(item, "evidence_fingerprint", "")) or hashlib.sha256(
                f"{item.query}|{item.url}|{item.title}|"
                f"{item.content_excerpt if hasattr(item, 'content_excerpt') else item.content}".encode()
            ).hexdigest()
            existing = self.session.scalar(
                select(WebObservation).where(
                    WebObservation.journey_id == journey.id,
                    WebObservation.evidence_fingerprint == fingerprint,
                )
            )
            if existing is None:
                existing = WebObservation(
                    id=str(uuid4()),
                    journey_id=journey.id,
                    query=item.query,
                    url=item.url,
                    domain=item.domain,
                    title=item.title,
                    source_class=getattr(item, "source_class", "OPEN_WEB"),
                    provider_key=item.provider_key,
                    model_key=getattr(item, "model_key", ""),
                    captured_at=item.captured_at,
                    evidence_fingerprint=fingerprint,
                    content_excerpt=getattr(item, "content_excerpt", getattr(item, "content", ""))[:2000],
                    authority_status="NON_AUTHORITATIVE",
                    created_at=item.captured_at,
                )
                self.session.add(existing)
            rows.append(existing)
        self.session.commit()
        return {
            "tool": "research_place_sources",
            "decision": AuthorizationDecision.ALLOW_AUTO.value,
            "journey_id": journey.id,
            "place_id": place.id,
            "query": query,
            "status": provider_status,
            "authority": "NON_AUTHORITATIVE",
            "observations": [
                {
                    "id": row.id,
                    "url": row.url,
                    "domain": row.domain,
                    "title": row.title,
                    "provider": row.provider_key,
                    "captured_at": row.captured_at,
                    "authority_status": row.authority_status,
                }
                for row in rows[:5]
            ],
        }

    def acquire_route(self, request: AgentToolCall) -> dict[str, Any]:
        """Acquire exactly one server-resolved grounded-origin -> target edge.

        Reform 2026-10-18: the write half of route comparison, using the same launch-origin chain the
        product route uses. The model names no origin and no coordinates; the server resolves the
        target activity and the grounded origin, and refuses when either is not ready. Execution runs
        through the deployment's mobility capture (mock when no live provider is configured), and
        every attempt is an operation row rather than a silent fetch.
        """
        from app.main import _launch_target_activity

        journey = _require_journey(self.session, request.journey_id)
        target = _launch_target_activity(self.session, journey)
        if target is None or not target.place_id:
            raise HTTPException(409, "exact route target is unavailable")
        if request.target_activity_id and str(request.target_activity_id) != str(target.id):
            raise HTTPException(422, "target_activity_id is not the active exact target")
        origin = grounded_launch_origin(self.session, journey, target_activity=target)
        if origin.get("state") != "READY" or not origin.get("origin_key"):
            raise HTTPException(409, "grounded launch origin is unavailable")
        if str(origin.get("source") or "") == "FOREGROUND_LOCATION":
            raise HTTPException(409, "route acquisition requires an exact persisted origin Place")
        route_request = RouteRequest(
            journey_id=str(journey.id),
            origin_key=str(origin["origin_key"]),
            target_key=str(target.place_id),
            target_activity_id=str(target.id),
            requested_mode=(request.route_mode or "TRANSIT").upper(),
            provider_policy_version=ROUTE_PROVIDER_POLICY_VERSION,
            route_truth_policy_version=ROUTE_TRUTH_POLICY_VERSION,
        )
        row, reused = submit_route_operation(self.session, journey, route_request)
        self.session.commit()
        body = route_operation_payload(row, reused=reused)
        return {
            "tool": "acquire_route",
            "decision": AuthorizationDecision.ALLOW_AUTO.value,
            "origin": {
                "key": origin.get("origin_key"),
                "name": origin.get("name"),
                "authority": origin.get("authority"),
                "source": origin.get("source"),
            },
            **body,
        }

    def compare_routes(self, request: AgentToolCall) -> dict[str, Any]:
        """Compare the route facts the server already holds for one edge.

        Reform 2026-10-18: the read half of route comparison. Acquisition needs the launch-origin
        chain this tree does not have yet, so this tool never claims to have looked anything up: it
        answers with the stored `MobilityFact` rows for the pair, or says no edge was captured. An
        unknown cost stays unknown -- the row's own `cost_status` is passed through untouched.
        """
        journey = _require_journey(self.session, request.journey_id)
        if not request.from_key or not request.to_key:
            raise HTTPException(422, "from_key and to_key are required for compare_routes")
        query = select(MobilityFact).where(
            MobilityFact.journey_id == journey.id,
            MobilityFact.from_key == request.from_key,
            MobilityFact.to_key == request.to_key,
        )
        if request.route_mode:
            query = query.where(MobilityFact.mode == request.route_mode.upper())
        rows = self.session.scalars(query.order_by(MobilityFact.mode)).all()
        return {
            "tool": "compare_routes",
            "decision": AuthorizationDecision.ALLOW_AUTO.value,
            "pair": {"from_key": request.from_key, "to_key": request.to_key},
            "status": "STORED_FACTS" if rows else "NO_STORED_ROUTE_FACTS",
            "counts_as_supply": bool(rows),
            "options": [
                {
                    "mode": row.mode,
                    "duration_min": row.duration_min,
                    "distance_m": row.distance_m,
                    "cost_amount_minor": row.cost_amount_minor,
                    "currency": row.currency,
                    "cost_status": row.cost_status,
                    "transfers": row.transfers,
                    "walking_min": row.walking_min,
                    "provider_key": row.provider_key,
                    "provenance": row.provenance,
                    "captured_at": row.captured_at,
                }
                for row in rows
            ],
        }

    def acquire_place_facts(self, request: AgentToolCall) -> dict[str, Any]:
        """Acquire provider-backed facts for one Place, or say why it cannot.

        Reform 2026-10-18, fifth adapter: source-backed details. The provider identity is the
        place's own (`overpass:node/123` and friends); a caller may also bind the acquisition to a
        source observation it already holds. Facts the providers do not answer stay UNKNOWN, and a
        place with no provider identity is reported as such instead of being guessed at. This tool
        writes canonical Place rows, so the runtime requires an inspection before it runs.
        """
        journey = _require_journey(self.session, request.journey_id)
        if not request.place_id:
            raise HTTPException(422, "place_id is required for acquire_place_facts")
        place = self.session.get(Place, request.place_id)
        if place is None or place.city_code != journey.city_code:
            raise HTTPException(404, "Place is not part of the Journey city")
        bindings = None
        binding_origin = "agent"
        if request.source_observation_id is not None:
            observation = self.session.get(WebObservation, str(request.source_observation_id))
            if observation is None or observation.journey_id != journey.id:
                raise HTTPException(409, "SOURCE_OBSERVATION_NOT_OWNED_BY_JOURNEY")
            if observation.authority_status != "NON_AUTHORITATIVE":
                raise HTTPException(409, "SOURCE_OBSERVATION_STATE_INVALID")
            bindings = {
                place.id: {
                    "source_url": observation.url,
                    "source_class": observation.source_class,
                    "source_observation_id": observation.id,
                }
            }
            binding_origin = "agent_observation"
        elif request.source_url:
            bindings = {
                place.id: {
                    "source_url": request.source_url,
                    "source_class": request.source_class,
                }
            }
        receipt = acquire_place_facts(
            self.session,
            journey,
            place_ids=[place.id],
            source_bindings=bindings,
            binding_origin=binding_origin,
        )
        self.session.commit()
        return {
            "tool": "acquire_place_facts",
            "decision": AuthorizationDecision.ALLOW_AUTO.value,
            "place_id": place.id,
            "receipt": receipt,
        }

    def discover_places(self, request: AgentToolCall) -> dict[str, Any]:
        """Provider-backed alternative search, for when a catalogue query found nothing.

        Reform 2026-10-18, fourth adapter. The query budget is the server's own route budget
        (radius 100..5000 m, at most 20 rows per call); widening it without provider evidence is
        exactly what the order forbids. Every call writes a ProviderCall row, and a provider that
        answers with nothing is reported as such -- not raised as a failure of the journey, and not
        turned into an invented place.
        """
        journey = _require_journey(self.session, request.journey_id)
        if not request.query:
            raise HTTPException(422, "query is required for discover_places")
        mode = (request.mode or "captured_replay").lower()
        try:
            result = capture_real_city_candidates(
                self.session,
                journey,
                query=request.query,
                radius_m=request.radius_m or 2500,
                limit=request.limit or 8,
                mode=mode,
            )
        except ValueError as exc:
            # A named refusal (for example, the captured snapshot belongs to another city) is a
            # conflict the caller can act on, not a provider outage.
            raise HTTPException(409, str(exc)) from exc
        except RuntimeError as exc:
            raise HTTPException(503, str(exc)) from exc
        self.session.commit()
        candidates = result.get("candidates") or []
        return {
            "tool": "discover_places",
            "decision": AuthorizationDecision.ALLOW_AUTO.value,
            "query": request.query,
            "mode": result.get("mode", mode),
            "count": len(candidates),
            "counts_as_supply": bool(candidates),
            "provenance": result.get("provenance"),
            "provider_status": result.get("provider_status"),
            "candidates": candidates,
        }

    def generate_plans(self, request: AgentToolCall) -> dict[str, Any]:
        """Generate candidate plans for a draft; selection stays a separate step.

        Reform 2026-10-18, ported from the Revolution gateway. Every plan this returns is a
        CANDIDATE: nothing here selects or activates one, and the active plan (when there is one) is
        read only to compute what a candidate would change. This is the call that lets a draft be
        researched and shaped before anybody commits to it.
        """
        journey = _require_journey(self.session, request.journey_id)
        requested = list(dict.fromkeys(str(item) for item in (request.place_ids or [])))
        if len(requested) < 2:
            raise HTTPException(
                422, "place_ids must contain at least two distinct server-owned Place IDs"
            )
        rows = self.session.scalars(select(Place).where(Place.id.in_(requested))).all()
        found = {row.id: row for row in rows}
        missing = [place_id for place_id in requested if place_id not in found]
        wrong_city = [
            place_id
            for place_id in requested
            if place_id in found and found[place_id].city_code != journey.city_code
        ]
        if missing or wrong_city:
            raise HTTPException(
                422,
                json.dumps(
                    {
                        "code": "PLACE_IDS_NOT_IN_JOURNEY_CITY",
                        "missing_place_ids": missing,
                        "wrong_city_place_ids": wrong_city,
                    }
                ),
            )
        try:
            plans = compose_plans(
                self.session,
                journey,
                request.planning_mode or journey.planning_mode,
                request.candidate_count,
                place_ids=requested,
            )
        except (TypeError, ValueError) as exc:
            self.session.rollback()
            raise HTTPException(422, str(exc)) from exc
        self.session.commit()
        from app.collective_mediation import plan_collective_fit_subject
        from app.main import active_journey_members_with_capabilities

        summaries: list[dict[str, Any]] = []
        collective_windows: list[dict[str, Any]] = []
        active_projection = None
        if journey.active_plan_version_id:
            active_plan = self.session.get(PlanVersion, journey.active_plan_version_id)
            if active_plan is not None:
                active_projection = plan_schema(self.session, active_plan).model_dump(mode="json")
        for plan in plans:
            projected = plan_schema(self.session, plan).model_dump(mode="json")
            explanation = projected.get("explanation") or {}
            mobility = projected.get("mobility_evidence") or {}
            subject = plan_collective_fit_subject(
                (active_projection or {}).get("activities", []),
                projected.get("activities", []),
            )
            activity_place_ids = [
                item.get("place_id")
                for item in projected.get("activities", [])
                if item.get("place_id")
            ]
            fit_place_ids = list(subject["fit_subject_place_ids"])
            places_for_fit = (
                self.session.scalars(select(Place).where(Place.id.in_(fit_place_ids))).all()
                if fit_place_ids
                else []
            )
            tags: list[str] = []
            for place in places_for_fit:
                tags.append(str(place.category or ""))
                tags.extend(json.loads(place.tags_json or "[]"))
            subject["fit_subject_tags"] = sorted(
                {str(tag).strip().lower() for tag in tags if str(tag).strip()}
            )
            hard_status = (
                "GROUNDED_FEASIBLE" if projected["selectable"] else "REVALIDATION_REQUIRED"
            )
            collective_windows.append(
                {
                    "window_id": projected["id"],
                    "status": hard_status,
                    "candidate": {
                        "place_id": projected["id"],
                        "ordered_place_ids": fit_place_ids,
                        "tags": subject["fit_subject_tags"],
                        **subject,
                    },
                }
            )
            summaries.append(
                {
                    "id": projected["id"],
                    "version_no": projected["version_no"],
                    "status": projected["status"],
                    "selectable": projected["selectable"],
                    "place_ids": activity_place_ids,
                    "fit_subject_place_ids": fit_place_ids,
                    "unresolved_facts": explanation.get("unresolved_facts", []),
                    "authority_state": explanation.get("authority_state"),
                    "mobility_provider": mobility.get("source_provider"),
                    "mobility_snapshot_id": projected.get("mobility_snapshot_id"),
                    **subject,
                }
            )
        collective = active_journey_members_with_capabilities(
            self.session, journey, candidate_windows=collective_windows
        )
        for summary, row in zip(summaries, collective.get("candidate_fit_matrix", [])):
            summary["collective_fairness"] = row.get("fairness", {})
            summary["collective_member_fits"] = row.get("member_fits", {})
        collective.pop("members", None)
        return {
            "tool": "generate_plans",
            "decision": AuthorizationDecision.ALLOW_AUTO.value,
            "candidate_count": len(summaries),
            "plans": summaries,
            "collective_mediation": collective,
            "authority_note": "Candidates are awaiting the deterministic selection step.",
        }

    def estimate_place_facts(self, request: AgentToolCall) -> dict[str, Any]:
        """Estimate one Place's hours or cost from same-city verified peers.

        Reform 2026-10-18, ported from the Revolution gateway. The estimate is strategy evidence:
        it lands under `strategy_estimate` in the place's metadata and is never promoted into
        `opening_hours_json` or `cost_evidence`, because a peer median is not this place's fact.
        A number the model supplies is recorded as AGENT_PROVIDED_HYPOTHESIS, with the same
        non-authoritative status.
        """
        journey = _require_journey(self.session, request.journey_id)
        if not request.place_id:
            raise HTTPException(422, "place_id is required for estimate_place_facts")
        place = self.session.get(Place, request.place_id)
        if place is None or place.city_code != journey.city_code:
            raise HTTPException(404, "Place is not part of the Journey city")
        peers = self.session.scalars(
            select(Place).where(
                Place.city_code == journey.city_code, Place.category == place.category
            )
        ).all()
        peer_costs = [
            value
            for peer in peers
            if json.loads(peer.metadata_json or "{}").get("cost_evidence", {}).get("currency")
            == journey.budget_currency
            and (value := _place_verified_cost(peer)) is not None
        ]
        peer_windows = [window for peer in peers if (window := _place_window(peer)) is not None]
        estimate: dict[str, Any] = {
            "place_id": place.id,
            "authority_eligible": False,
            "basis": "same-city verified peers in the same provider category",
            "opening_hours": {"status": "ESTIMATED_AGENT"},
            "cost_evidence": {"status": "ESTIMATED_AGENT", "currency": journey.budget_currency},
        }
        if peer_windows:
            opens = [window[0] for window in peer_windows]
            closes = [window[1] for window in peer_windows]
            estimate["opening_hours"].update(
                {
                    "open_minutes": int(median(opens)),
                    "close_minutes": int(median(closes)),
                    "peer_count": len(peer_windows),
                }
            )
        if peer_costs:
            estimate["cost_evidence"].update(
                {"amount_minor": int(median(peer_costs)), "peer_count": len(peer_costs)}
            )
        if (
            request.estimated_open_minutes is not None
            and request.estimated_close_minutes is not None
            and request.estimated_close_minutes > request.estimated_open_minutes
        ):
            estimate["basis"] = "agent_bounded_hypothesis"
            estimate["opening_hours"].update(
                {
                    "open_minutes": request.estimated_open_minutes,
                    "close_minutes": request.estimated_close_minutes,
                    "basis": "AGENT_PROVIDED_HYPOTHESIS",
                }
            )
        if request.estimated_cost_minor is not None:
            estimate["basis"] = "agent_bounded_hypothesis"
            estimate["cost_evidence"].update(
                {
                    "amount_minor": request.estimated_cost_minor,
                    "basis": "AGENT_PROVIDED_HYPOTHESIS",
                }
            )
        metadata = json.loads(place.metadata_json or "{}") if place.metadata_json else {}
        metadata["strategy_estimate"] = {
            "status": "ESTIMATED_AGENT",
            "authority_eligible": False,
            "basis": estimate["basis"],
            "captured_at": datetime.now(timezone.utc).isoformat(),
            "opening_hours": dict(estimate["opening_hours"]),
            "cost_evidence": dict(estimate["cost_evidence"]),
        }
        place.metadata_json = json.dumps(metadata, ensure_ascii=False, sort_keys=True)
        # Estimates are strategy observations, not canonical Place facts. Persisting them lets the
        # next deterministic compose explain how the decision was made without promoting the
        # numbers into opening_hours_json or cost_evidence.
        self.session.commit()
        return {
            "tool": "estimate_place_facts",
            "decision": AuthorizationDecision.ALLOW_AUTO.value,
            "estimate": estimate,
            "warning": (
                "ESTIMATED_AGENT never becomes canonical/provider truth; it supports strategy only."
            ),
        }

    def search_city_services(self, request: AgentToolCall) -> dict[str, Any]:
        city_code = request.city_code
        if city_code is None and request.journey_id is not None:
            city_code = _require_journey(self.session, request.journey_id).city_code
        if not city_code:
            raise HTTPException(422, "city_code or journey_id is required for this Agent tool")
        services = self.session.scalars(
            select(CityService).where(CityService.city_code == city_code).order_by(CityService.id)
        ).all()
        if request.service_type:
            services = [
                item
                for item in services
                if item.service_type.lower() == request.service_type.lower()
            ]
        if request.q:
            needle = request.q.casefold()
            services = [item for item in services if needle in item.name.casefold()]
        places = self.session.scalars(
            select(Place).where(Place.city_code == city_code).order_by(Place.id)
        ).all()
        if request.category:
            category = request.category.casefold()
            places = [item for item in places if category in item.category.casefold()]
        if request.q:
            needle = request.q.casefold()
            places = [
                item
                for item in places
                if needle in item.name.casefold()
                or needle in item.category.casefold()
                or needle in item.tags_json.casefold()
            ]
        return {
            "tool": "search_city_services",
            "decision": AuthorizationDecision.ALLOW_AUTO.value,
            "city_code": city_code,
            "services": [_json(service_schema(item)) for item in services],
            "places": [
                {
                    "id": item.id,
                    "name": item.name,
                    "category": item.category,
                    "city_code": item.city_code,
                    "location": {"latitude": item.latitude, "longitude": item.longitude},
                    "tags": json.loads(item.tags_json or "[]"),
                    "opening_hours": json.loads(item.opening_hours_json or "{}"),
                    "metadata": json.loads(item.metadata_json or "{}"),
                }
                for item in places
            ],
        }

    def request_replan(self, request: AgentToolCall) -> dict[str, Any]:
        journey = _require_journey(self.session, request.journey_id)
        if request.trigger_event_id is None:
            raise HTTPException(422, "trigger_event_id is required for request_replan")
        policy_row = get_or_create_policy(self.session, journey.traveler_id)
        policy = policy_from_model(policy_row)
        protected_activity_ids: list[UUID] = []
        if request.mission_id is not None:
            mission = self.session.get(JourneyMission, str(request.mission_id))
            if mission is None or mission.journey_id != journey.id:
                raise HTTPException(404, "Journey mission was not found")
            protected_activity_ids = [
                UUID(item) for item in json.loads(mission.protected_activity_ids_json or "[]")
            ]
        auth = evaluate_action(policy, AgentAction.REQUEST_REPLAN, AuthoritativeActionFacts())
        signature = canonical_request_signature(
            {
                "tool": "request_replan",
                "request_id": request.request_id,
                "agent_id": request.agent_id,
                "journey_id": journey.id,
                "trigger_event_id": str(request.trigger_event_id),
                "candidate_count": request.candidate_count,
                "solver_mode": request.solver_mode,
                "mission_id": str(request.mission_id) if request.mission_id else None,
            }
        )
        # request_id is the caller's idempotency scope. Keep the proposal or
        # Journey out of the key so reuse with different arguments becomes a
        # deterministic conflict instead of a second mutation.
        key = _agent_key("request_replan", request.agent_id, request.request_id)
        stored = _read_idempotent(self.session, key, signature)
        if stored is not None:
            return _upgrade_cached_request_replan_response(
                self.session,
                stored,
                journey_id=journey.id,
                trigger_event_id=str(request.trigger_event_id),
            )

        from app.main import generate_replan

        inner_key = _agent_key(
            "replan_generation", request.agent_id, request.request_id, journey.id
        )
        generated = generate_replan(
            UUID(journey.id),
            ReplanGenerateRequest(
                trigger_event_id=request.trigger_event_id,
                candidate_count=request.candidate_count,
                solver_mode=request.solver_mode,
                protected_activity_ids=protected_activity_ids,
            ),
            idempotency_key=inner_key,
            session=self.session,
        )
        proposals = self.session.scalars(
            select(ReplanProposal)
            .where(
                ReplanProposal.journey_id == journey.id,
                ReplanProposal.trigger_event_id == str(request.trigger_event_id),
            )
            .order_by(ReplanProposal.created_at, ReplanProposal.id)
        ).all()
        response = {
            "tool": "request_replan",
            "decision": auth.decision.value,
            "reason_codes": list(auth.reason_codes),
            "policy_version": auth.policy_version,
            "request_id": request.request_id,
            "proposal": generated,
            "proposals": [
                {
                    "id": item.id,
                    "status": item.status,
                    "hard_constraints_passed": bool(item.hard_constraints_passed),
                    "locked_commitments_preserved": bool(item.locked_commitments_preserved),
                }
                for item in proposals
            ],
        }
        record_audit(
            self.session,
            action="agent.request_replan",
            entity_type="ReplanProposal",
            entity_id=str(generated["id"]),
            journey_id=journey.id,
            actor_type="AI_AGENT",
            actor_id=request.agent_id,
            after={
                "tool": "request_replan",
                "policy_version": auth.policy_version,
                "authorization_decision": auth.decision.value,
                "reason_codes": list(auth.reason_codes),
                "before_status": None,
                "after_status": "PRESENTED",
                "request_id": request.request_id,
                "journey_id": journey.id,
            },
        )
        _write_idempotent(
            self.session,
            key=key,
            operation="agent.request_replan",
            signature=signature,
            response=response,
        )
        try:
            self.session.commit()
        except IntegrityError:
            self.session.rollback()
            stored = _read_idempotent(self.session, key, signature)
            if stored is not None:
                return _upgrade_cached_request_replan_response(
                    self.session,
                    stored,
                    journey_id=journey.id,
                    trigger_event_id=str(request.trigger_event_id),
                )
            raise
        return response

    def accept_replan(self, request: AgentToolCall) -> dict[str, Any]:
        if request.proposal_id is None:
            raise HTTPException(422, "proposal_id is required for accept_replan")
        proposal = self.session.get(ReplanProposal, str(request.proposal_id))
        if proposal is None:
            raise HTTPException(404, "Replan proposal was not found")
        journey = _require_journey(self.session, request.journey_id or UUID(proposal.journey_id))
        if proposal.journey_id != journey.id:
            raise HTTPException(403, "proposal does not belong to this Journey")
        policy_row = get_or_create_policy(self.session, journey.traveler_id)
        policy = policy_from_model(policy_row)
        facts, evidence = _facts_for_accept(self.session, proposal, journey)
        auth = self._bound_authorization(
            request, evaluate_action(policy, AgentAction.ACCEPT_REPLAN, facts)
        )
        signature = canonical_request_signature(
            {
                "tool": "accept_replan",
                "request_id": request.request_id,
                "agent_id": request.agent_id,
                "journey_id": journey.id,
                "proposal_id": proposal.id,
                "approval_id": str(request.approval_id) if request.approval_id else None,
            }
        )
        # The request id is the idempotency identity; proposal_id remains in
        # the canonical signature and therefore cannot silently change it.
        key = _agent_key("accept_replan", request.agent_id, request.request_id)
        stored = _read_idempotent(self.session, key, signature)
        if stored is not None:
            return stored

        if not facts.base_plan_current or not facts.trigger_actionable:
            # Staleness is a domain conflict. The policy result is still
            # recorded in the response for a caller that is comparing receipts.
            raise HTTPException(409, "replan proposal is stale or its trigger is resolved")

        try:
            proposal_diff = json.loads(proposal.diff_json or "{}")
        except json.JSONDecodeError:
            proposal_diff = {}
        approval_signature = approval_fingerprint(
            action=AgentAction.ACCEPT_REPLAN.value,
            journey_id=journey.id,
            target_type="ReplanProposal",
            target_id=proposal.id,
            policy_version=auth.policy_version,
            decision=auth.decision.value,
            facts=evidence,
            proposal_diff=proposal_diff,
        )
        approval = None
        if auth.decision in {
            AuthorizationDecision.REQUIRE_CONFIRMATION,
            AuthorizationDecision.REQUIRE_STEP_UP,
        }:
            if request.approval_id is not None:
                approval = consume_action_approval(
                    self.session,
                    approval_id=str(request.approval_id),
                    journey_id=journey.id,
                    action=AgentAction.ACCEPT_REPLAN.value,
                    target_type="ReplanProposal",
                    target_id=proposal.id,
                    request_fingerprint=approval_signature,
                    actor_id=request.agent_id,
                )
            else:
                approval = create_or_reuse_approval(
                    self.session,
                    traveler_id=journey.traveler_id,
                    journey_id=journey.id,
                    action=AgentAction.ACCEPT_REPLAN.value,
                    target_type="ReplanProposal",
                    target_id=proposal.id,
                    request_fingerprint=approval_signature,
                    actor_id=request.agent_id,
                    required_decision=auth.decision.value,
                )

        approved_receipt = approval is not None and approval.status == "CONSUMED"
        if auth.decision == AuthorizationDecision.ALLOW_AUTO or approved_receipt:
            from app.main import _accept_replan_impl

            response_reason_codes = auth.reason_codes + (
                ("USER_APPROVAL_RECEIPT_CONSUMED",) if approved_receipt else ()
            )

            inner_key = _agent_key(
                "replan_accept", request.agent_id, request.request_id, proposal.id
            )
            result = _accept_replan_impl(
                UUID(proposal.id),
                inner_key,
                self.session,
                actor_type="AI_AGENT",
                actor_id=request.agent_id,
                policy_version=auth.policy_version,
                authorization_decision=auth.decision.value,
                reason_codes=response_reason_codes,
            )
            response = {
                "tool": "accept_replan",
                "decision": auth.decision.value,
                "reason_codes": list(response_reason_codes),
                "policy_version": auth.policy_version,
                "request_id": request.request_id,
                "executed": True,
                "user_confirmed": False,
                "facts": evidence,
                "result": result,
            }
            if approval is not None:
                response.update(approval_payload(approval))
            after_status = "ACCEPTED"
        else:
            response = {
                "tool": "accept_replan",
                "decision": auth.decision.value,
                "reason_codes": list(auth.reason_codes),
                "policy_version": auth.policy_version,
                "request_id": request.request_id,
                "executed": False,
                "user_confirmed": False,
                "facts": evidence,
                "proposal_id": proposal.id,
                "status": proposal.status,
            }
            if approval is not None:
                response.update(approval_payload(approval))
            after_status = proposal.status

        record_audit(
            self.session,
            action="agent.accept_replan",
            entity_type="ReplanProposal",
            entity_id=proposal.id,
            journey_id=journey.id,
            actor_type="AI_AGENT",
            actor_id=request.agent_id,
            before={
                "status": "PRESENTED",
                "policy_version": auth.policy_version,
            },
            after={
                "tool": "accept_replan",
                "proposal_id": proposal.id,
                "status": after_status,
                "policy_version": auth.policy_version,
                "authorization_decision": auth.decision.value,
                "reason_codes": response.get("reason_codes", list(auth.reason_codes)),
                "request_id": request.request_id,
                "user_confirmed": False,
                "approval_id": response.get("approval_id"),
                "approval_status": response.get("status"),
            },
        )
        _write_idempotent(
            self.session,
            key=key,
            operation="agent.accept_replan",
            signature=signature,
            response=response,
        )
        self.session.commit()
        return response

    def _typed_activity(self, journey: Journey, activity_id: UUID | None) -> Activity:
        if activity_id is None:
            raise HTTPException(422, "activity_id is required for this Agent tool")
        activity = self.session.get(Activity, str(activity_id))
        if activity is None:
            raise HTTPException(404, "Activity was not found")
        if activity.plan_version_id != journey.active_plan_version_id:
            raise HTTPException(409, "activity does not belong to the active Journey plan")
        if activity.status in {"COMPLETED", "SKIPPED", "CANCELLED"}:
            raise HTTPException(409, "terminal activity cannot be changed")
        return activity

    def _typed_commitments(self, journey: Journey, activity_id: str) -> list[Commitment]:
        return self.session.scalars(
            select(Commitment).where(
                Commitment.journey_id == journey.id,
                Commitment.activity_id == activity_id,
                Commitment.status == "ACTIVE",
            )
        ).all()

    def _typed_facts(
        self,
        *,
        policy,
        activity: Activity | None,
        commitments: list[Commitment],
        cost_delta_minor: int = 0,
        loss_delta_minor: int = 0,
        schedule_drift_min: int = 0,
        action_reversible: bool = True,
        commitment_management_requested: bool = False,
        booking_type: str | None = None,
    ) -> tuple[AuthoritativeActionFacts, dict[str, Any]]:
        protected = any(item.level in policy.protected_commitment_levels for item in commitments)
        c4_affected = bool(activity and activity.locked) or protected
        facts = AuthoritativeActionFacts(
            hard_constraints_passed=True,
            locked_commitments_preserved=not c4_affected,
            c4_affected=c4_affected,
            cost_delta_minor=max(0, int(cost_delta_minor)),
            loss_delta_minor=max(0, int(loss_delta_minor)),
            schedule_drift_min=max(0, int(schedule_drift_min)),
            affected_activity_type=activity.activity_type if activity else None,
            affected_booking_type=booking_type,
            commitment_management_requested=commitment_management_requested,
            commitment_levels=tuple(item.level for item in commitments),
            action_reversible=action_reversible,
        )
        return facts, {
            "hard_constraints_passed": facts.hard_constraints_passed,
            "locked_commitments_preserved": facts.locked_commitments_preserved,
            "c4_affected": facts.c4_affected,
            "cost_delta_minor": facts.cost_delta_minor,
            "loss_delta_minor": facts.loss_delta_minor,
            "schedule_drift_min": facts.schedule_drift_min,
            "affected_activity_type": facts.affected_activity_type,
            "affected_booking_type": facts.affected_booking_type,
            "commitment_management_requested": facts.commitment_management_requested,
            "commitment_levels": list(facts.commitment_levels),
            "action_reversible": facts.action_reversible,
        }

    def _run_typed_mutation(
        self,
        request: AgentToolCall,
        journey: Journey,
        *,
        action: AgentAction,
        target_type: str,
        target_id: str,
        facts: AuthoritativeActionFacts,
        evidence: dict[str, Any],
        arguments: dict[str, Any],
        execute: Callable[[], dict[str, Any]],
    ) -> dict[str, Any]:
        policy = policy_from_model(get_or_create_policy(self.session, journey.traveler_id))
        auth = self._bound_authorization(request, evaluate_action(policy, action, facts))
        tool_name = action.value.lower()
        signature = canonical_request_signature(
            {
                "tool": tool_name,
                "request_id": request.request_id,
                "agent_id": request.agent_id,
                "journey_id": journey.id,
                "arguments": arguments,
                "approval_id": str(request.approval_id) if request.approval_id else None,
            }
        )
        key = _agent_key(tool_name, request.agent_id, request.request_id)
        stored = _read_idempotent(self.session, key, signature)
        if stored is not None:
            return stored

        approval = None
        if auth.decision in {
            AuthorizationDecision.REQUIRE_CONFIRMATION,
            AuthorizationDecision.REQUIRE_STEP_UP,
        }:
            approval_signature = approval_fingerprint(
                action=action.value,
                journey_id=journey.id,
                target_type=target_type,
                target_id=target_id,
                policy_version=auth.policy_version,
                decision=auth.decision.value,
                facts=evidence,
                proposal_diff=arguments,
            )
            if request.approval_id is not None:
                approval = consume_action_approval(
                    self.session,
                    approval_id=str(request.approval_id),
                    journey_id=journey.id,
                    action=action.value,
                    target_type=target_type,
                    target_id=target_id,
                    request_fingerprint=approval_signature,
                    actor_id=request.agent_id,
                )
            else:
                approval = create_or_reuse_approval(
                    self.session,
                    traveler_id=journey.traveler_id,
                    journey_id=journey.id,
                    action=action.value,
                    target_type=target_type,
                    target_id=target_id,
                    request_fingerprint=approval_signature,
                    actor_id=request.agent_id,
                    required_decision=auth.decision.value,
                )

        approved_receipt = approval is not None and approval.status == "CONSUMED"
        executed = auth.decision == AuthorizationDecision.ALLOW_AUTO or approved_receipt
        response: dict[str, Any] = {
            "tool": tool_name,
            "decision": auth.decision.value,
            "reason_codes": list(auth.reason_codes)
            + (["USER_APPROVAL_RECEIPT_CONSUMED"] if approved_receipt else []),
            "policy_version": auth.policy_version,
            "request_id": request.request_id,
            "executed": executed,
            "user_confirmed": False,
            "facts": evidence,
            "target_type": target_type,
            "target_id": target_id,
        }
        if approval is not None:
            approval_view = approval_payload(approval)
            response.update(
                {
                    "approval_id": approval_view["approval_id"],
                    "approval_status": approval_view["status"],
                    "approval_method": approval_view["approval_method"],
                    "approval_expires_at": approval_view["expires_at"],
                }
            )
        if executed:
            try:
                response["result"] = execute()
            except CommerceConflict as exc:
                self.session.rollback()
                raise HTTPException(409, str(exc)) from exc
            except (CommerceValidationError, ValueError) as exc:
                self.session.rollback()
                raise HTTPException(422, str(exc)) from exc

        record_audit(
            self.session,
            action=f"agent.{tool_name}",
            entity_type=target_type,
            entity_id=target_id,
            journey_id=journey.id,
            actor_type="AI_AGENT",
            actor_id=request.agent_id,
            after={
                "tool": tool_name,
                "target_type": target_type,
                "target_id": target_id,
                "status": "EXECUTED" if executed else "PENDING",
                "authorization_decision": auth.decision.value,
                "reason_codes": response["reason_codes"],
                "request_id": request.request_id,
                "approval_id": response.get("approval_id"),
                "approval_status": response.get("approval_status"),
            },
        )
        _write_idempotent(
            self.session,
            key=key,
            operation=f"agent.{tool_name}",
            signature=signature,
            response=response,
        )
        self.session.commit()
        return response

    def replace_activity(self, request: AgentToolCall) -> dict[str, Any]:
        journey = _require_journey(self.session, request.journey_id)
        target = self._typed_activity(journey, request.activity_id)
        replacement = None
        replacement_place = None
        replacement_service = None
        if request.replacement_activity_id is not None:
            replacement = self._typed_activity(journey, request.replacement_activity_id)
            if target.id == replacement.id:
                raise HTTPException(422, "replacement_activity_id must differ from activity_id")
            if replacement.locked:
                raise HTTPException(409, "replacement activity is protected")
            if self._typed_commitments(journey, replacement.id):
                raise HTTPException(409, "replacement activity already has an active commitment")
        elif request.replacement_place_id is not None:
            replacement_place = self.session.get(Place, request.replacement_place_id)
            if replacement_place is None:
                raise HTTPException(404, "replacement Place was not found")
            if replacement_place.city_code != journey.city_code:
                raise HTTPException(409, "replacement Place is outside the Journey city")
            if replacement_place.id == target.place_id:
                raise HTTPException(422, "replacement_place_id must differ from the target Place")
            replacement_service = self.session.scalar(
                select(CityService)
                .where(
                    CityService.city_code == journey.city_code,
                    CityService.place_id == replacement_place.id,
                )
                .order_by(CityService.id)
            )
        else:
            raise HTTPException(
                422,
                "replace_activity requires replacement_activity_id or replacement_place_id",
            )
        commitments = self._typed_commitments(journey, target.id)
        policy = policy_from_model(get_or_create_policy(self.session, journey.traveler_id))
        if replacement is not None:
            replacement_cost_minor = replacement.estimated_cost_minor
            replacement_end_at = datetime.fromisoformat(replacement.end_at)
            replacement_travel_from_prev_min = replacement.travel_from_prev_min
        else:
            assert replacement_place is not None
            metadata = json.loads(replacement_place.metadata_json or "{}")
            duration_min = int(metadata.get("duration_min", 60))
            replacement_cost_minor = int(metadata.get("cost_minor", 0))
            replacement_end_at = datetime.fromisoformat(target.start_at) + timedelta(
                minutes=duration_min
            )
            previous = self.session.scalar(
                select(Activity).where(
                    Activity.plan_version_id == journey.active_plan_version_id,
                    Activity.sequence_no == target.sequence_no - 1,
                )
            )
            previous_location = previous.place_id or previous.city_service_id if previous else None
            if previous_location is None or previous_location == replacement_place.id:
                replacement_travel_from_prev_min = 0
            else:
                from app.integrations.mock.providers import MockMobilityProvider

                replacement_travel_from_prev_min = MockMobilityProvider().estimate_minutes(
                    previous_location,
                    replacement_place.id,
                )
        drift = abs(
            int((replacement_end_at - datetime.fromisoformat(target.end_at)).total_seconds() // 60)
        )
        facts, evidence = self._typed_facts(
            policy=policy,
            activity=target,
            commitments=commitments,
            cost_delta_minor=replacement_cost_minor - target.estimated_cost_minor,
            schedule_drift_min=drift,
            commitment_management_requested=bool(commitments),
        )
        arguments = {
            "activity_id": target.id,
            "replacement_activity_id": replacement.id if replacement is not None else None,
            "replacement_place_id": replacement_place.id if replacement_place is not None else None,
        }

        def execute() -> dict[str, Any]:
            target_snapshot = activity_schema(target).model_dump(mode="json")
            if replacement is not None:
                for field in (
                    "activity_type",
                    "title",
                    "place_id",
                    "city_service_id",
                    "start_at",
                    "end_at",
                    "travel_from_prev_min",
                    "estimated_cost_minor",
                    "currency",
                    "metadata_json",
                ):
                    setattr(target, field, getattr(replacement, field))
                replacement.status = "CANCELLED"
            else:
                assert replacement_place is not None
                target.title = replacement_place.name
                target.place_id = replacement_place.id
                target.city_service_id = (
                    replacement_service.id if replacement_service is not None else None
                )
                target.end_at = replacement_end_at.isoformat()
                target.travel_from_prev_min = replacement_travel_from_prev_min
                target.estimated_cost_minor = replacement_cost_minor
                target.currency = journey.budget_currency
                target.metadata_json = json.dumps(
                    {
                        "replacement_source": "SERVER_PLACE",
                        "place_id": replacement_place.id,
                        "city_service_id": target.city_service_id,
                    },
                    sort_keys=True,
                )
            from app.main import _assert_selected_plan_feasible

            plan = self.session.get(PlanVersion, journey.active_plan_version_id)
            _assert_selected_plan_feasible(self.session, journey, plan)
            return {
                "activity": activity_schema(target).model_dump(mode="json"),
                "replaced_activity": target_snapshot,
                "replacement_source": "SERVER_PLACE"
                if replacement_place is not None
                else "SCHEDULED_ACTIVITY",
            }

        return self._run_typed_mutation(
            request,
            journey,
            action=AgentAction.REPLACE_ACTIVITY,
            target_type="Activity",
            target_id=target.id,
            facts=facts,
            evidence=evidence,
            arguments=arguments,
            execute=execute,
        )

    def reschedule_activity(self, request: AgentToolCall) -> dict[str, Any]:
        journey = _require_journey(self.session, request.journey_id)
        target = self._typed_activity(journey, request.activity_id)
        if request.start_at is None or request.end_at is None:
            raise HTTPException(422, "start_at and end_at are required for reschedule_activity")
        if request.end_at <= request.start_at:
            raise HTTPException(422, "end_at must be after start_at")
        commitments = self._typed_commitments(journey, target.id)
        policy = policy_from_model(get_or_create_policy(self.session, journey.traveler_id))
        drift = max(
            abs(
                int(
                    (request.start_at - datetime.fromisoformat(target.start_at)).total_seconds()
                    // 60
                )
            ),
            abs(
                int((request.end_at - datetime.fromisoformat(target.end_at)).total_seconds() // 60)
            ),
        )
        facts, evidence = self._typed_facts(
            policy=policy,
            activity=target,
            commitments=commitments,
            schedule_drift_min=drift,
            commitment_management_requested=bool(commitments),
        )
        arguments = {
            "activity_id": target.id,
            "start_at": request.start_at.isoformat(),
            "end_at": request.end_at.isoformat(),
        }

        def execute() -> dict[str, Any]:
            target.start_at = request.start_at.isoformat()
            target.end_at = request.end_at.isoformat()
            for commitment in commitments:
                policy_json = json.loads(commitment.policy_json or "{}")
                policy_json.update(
                    {
                        "scheduled_start_at": target.start_at,
                        "scheduled_end_at": target.end_at,
                    }
                )
                commitment.policy_json = json.dumps(policy_json, sort_keys=True)
                commitment.updated_at = datetime.now(timezone.utc).isoformat()
            from app.main import _assert_selected_plan_feasible

            plan = self.session.get(PlanVersion, journey.active_plan_version_id)
            _assert_selected_plan_feasible(self.session, journey, plan)
            return {"activity": activity_schema(target).model_dump(mode="json")}

        return self._run_typed_mutation(
            request,
            journey,
            action=AgentAction.RESCHEDULE_ACTIVITY,
            target_type="Activity",
            target_id=target.id,
            facts=facts,
            evidence=evidence,
            arguments=arguments,
            execute=execute,
        )

    def create_booking(self, request: AgentToolCall) -> dict[str, Any]:
        journey = _require_journey(self.session, request.journey_id)
        activity = self._typed_activity(journey, request.activity_id)
        commitments = self._typed_commitments(journey, activity.id)
        policy = policy_from_model(get_or_create_policy(self.session, journey.traveler_id))
        facts, evidence = self._typed_facts(
            policy=policy,
            activity=activity,
            commitments=commitments,
            cost_delta_minor=activity.estimated_cost_minor,
            commitment_management_requested=True,
            booking_type="booking",
        )
        arguments = {"activity_id": activity.id, "provider_key": request.provider_key}

        def execute() -> dict[str, Any]:
            from app.commerce.service_impl import create_booking as commerce_create_booking
            from app.commerce.strengths_generated import SOURCE_COMMITMENT_STRENGTHS
            from app.main import _assert_selected_plan_feasible, _mock_booking_provider

            provider, provider_failure = _mock_booking_provider(request.provider_key)
            item = commerce_create_booking(
                self.session,
                journey_id=journey.id,
                activity_id=activity.id,
                provider=provider,
                source_strength_codes=SOURCE_COMMITMENT_STRENGTHS,
                booking_source_type_code="booking",
                assert_selected_plan_feasible=_assert_selected_plan_feasible,
                force_failure=provider_failure,
            )
            return {"booking_id": item.id, "status": item.status, "amount_minor": item.amount_minor}

        return self._run_typed_mutation(
            request,
            journey,
            action=AgentAction.CREATE_BOOKING,
            target_type="Activity",
            target_id=activity.id,
            facts=facts,
            evidence=evidence,
            arguments=arguments,
            execute=execute,
        )

    def cancel_refundable_booking(self, request: AgentToolCall) -> dict[str, Any]:
        journey = _require_journey(self.session, request.journey_id)
        if request.booking_id is None:
            raise HTTPException(422, "booking_id is required for cancel_refundable_booking")
        booking = self.session.get(Booking, str(request.booking_id))
        if booking is None or booking.journey_id != journey.id:
            raise HTTPException(404, "Booking was not found for this Journey")
        activity = (
            self._typed_activity(journey, UUID(booking.activity_id))
            if booking.activity_id
            else None
        )
        commitments = self._typed_commitments(journey, activity.id) if activity else []
        cancellation = json.loads(booking.cancellation_policy_json or "{}")
        paid = self.session.scalar(
            select(PaymentTransaction.id).where(
                PaymentTransaction.booking_id == booking.id,
                PaymentTransaction.status == "SUCCEEDED",
            )
        )
        refundable = cancellation.get("cancellable_before_payment") is not False and not paid
        policy = policy_from_model(get_or_create_policy(self.session, journey.traveler_id))
        facts, evidence = self._typed_facts(
            policy=policy,
            activity=activity,
            commitments=commitments,
            loss_delta_minor=max(0, int(cancellation.get("loss_minor", 0) or 0)),
            action_reversible=refundable,
            commitment_management_requested=True,
            booking_type=str(cancellation.get("booking_type") or "booking"),
        )
        arguments = {"booking_id": booking.id, "provider_key": booking.provider_key}

        def execute() -> dict[str, Any]:
            from app.commerce.service_impl import cancel_booking as commerce_cancel_booking
            from app.main import _mock_booking_provider

            provider, provider_failure = _mock_booking_provider(booking.provider_key)
            updated = commerce_cancel_booking(
                self.session,
                booking_id=booking.id,
                provider=provider,
                force_failure=provider_failure,
            )
            return {"booking_id": updated.id, "status": updated.status}

        return self._run_typed_mutation(
            request,
            journey,
            action=AgentAction.CANCEL_REFUNDABLE_BOOKING,
            target_type="Booking",
            target_id=booking.id,
            facts=facts,
            evidence=evidence,
            arguments=arguments,
            execute=execute,
        )

    def request_commitment_change(self, request: AgentToolCall) -> dict[str, Any]:
        journey = _require_journey(self.session, request.journey_id)
        if request.commitment_id is None:
            raise HTTPException(422, "commitment_id is required for request_commitment_change")
        commitment = self.session.get(Commitment, str(request.commitment_id))
        if commitment is None or commitment.journey_id != journey.id:
            raise HTTPException(404, "Commitment was not found for this Journey")
        activity = (
            self._typed_activity(journey, UUID(commitment.activity_id))
            if commitment.activity_id
            else None
        )
        policy = policy_from_model(get_or_create_policy(self.session, journey.traveler_id))
        facts, evidence = self._typed_facts(
            policy=policy,
            activity=activity,
            commitments=[commitment],
            commitment_management_requested=True,
        )
        arguments = {"commitment_id": commitment.id, "reason": request.reason or ""}

        def execute() -> dict[str, Any]:
            record_audit(
                self.session,
                action="agent.commitment_change.requested",
                entity_type="Commitment",
                entity_id=commitment.id,
                journey_id=journey.id,
                actor_type="AI_AGENT",
                actor_id=request.agent_id,
                after={"reason": request.reason, "level": commitment.level, "status": "REQUESTED"},
            )
            return {"commitment_id": commitment.id, "status": "REQUESTED", "reason": request.reason}

        return self._run_typed_mutation(
            request,
            journey,
            action=AgentAction.REQUEST_COMMITMENT_CHANGE,
            target_type="Commitment",
            target_id=commitment.id,
            facts=facts,
            evidence=evidence,
            arguments=arguments,
            execute=execute,
        )

def _latest_actionable_event(
    session: Session, journey_id: str, event_id: str | None = None
) -> Event | None:
    """Resolve only an explicit or unambiguous event; never guess on ambiguity."""

    selected, _events, _error = _resolve_actionable_event(session, journey_id, event_id)
    return selected

def _resolve_actionable_event(
    session: Session, journey_id: str, event_id: str | None = None
) -> tuple[Event | None, list[Event], str | None]:
    events = _actionable_events(session, journey_id)
    if event_id:
        selected = next((item for item in events if item.id == str(event_id)), None)
        if selected is None:
            return None, events, "EVENT_NOT_ACTIONABLE"
        return selected, events, None
    if len(events) == 1:
        return events[0], events, None
    if len(events) > 1:
        return None, events, "EVENT_SELECTION_REQUIRED"
    return None, events, None

def _city_category_terms(category: str | None) -> tuple[str, ...]:
    if not category:
        return ()
    normalized = category.casefold().strip()
    return tuple(dict.fromkeys((normalized, *_CITY_CATEGORY_ALIASES.get(normalized, ()))))

def _city_search_terms(query: str | None) -> tuple[str, ...]:
    if not query:
        return ()
    normalized = query.casefold().strip()
    terms: list[str] = [normalized]
    terms.extend(token for token in re.findall(r"[\w\u4e00-\u9fff]+", normalized) if len(token) > 1)
    for phrase, aliases in _CITY_SEARCH_ALIASES.items():
        if phrase in normalized:
            terms.extend(aliases)
    return tuple(dict.fromkeys(term for term in terms if term))

def _actionable_events(session: Session, journey_id: str) -> list[Event]:
    """Return all open events in deterministic display order.

    Recency is useful for presentation, but it is not a semantic priority rule.
    Callers must therefore keep the complete compact choice set whenever more
    than one event is open.
    """

    return list(
        session.scalars(
            select(Event)
            .where(
                Event.journey_id == journey_id,
                Event.status.in_(("DETECTED", "ACKNOWLEDGED")),
            )
            .order_by(Event.detected_at.desc(), Event.id.desc())
        ).all()
    )

_CITY_CATEGORY_ALIASES: dict[str, tuple[str, ...]] = {
    "culture": ("museum", "gallery", "library", "theatre", "heritage", "attraction"),
    "cultural": ("museum", "gallery", "library", "theatre", "heritage", "attraction"),
    "indoor": ("museum", "gallery", "library", "theatre", "attraction"),
    "outdoor": ("park", "garden", "viewpoint", "heritage", "attraction"),
    # "experience" is the bounded open-world category used by the opportunity
    # mission.  Treat it as a discovery umbrella, not a literal Place
    # category, so the Agent can inspect real provider-backed alternatives.
    "experience": (
        "museum", "gallery", "library", "theatre", "heritage", "attraction",
        "park", "garden", "viewpoint", "restaurant", "cafe",
    ),
}

_CITY_SEARCH_ALIASES: dict[str, tuple[str, ...]] = {
    "博物馆": ("museum",),
    "美术馆": ("gallery", "museum"),
    "图书馆": ("library",),
    "文化": ("culture", "museum", "library", "theatre"),
    "室内": ("indoor", "museum", "library", "theatre"),
    "历史": ("historic", "attraction", "museum"),
    # English category words are common model-generated search queries.  They
    # must expand in the same open-world search path as the Chinese aliases;
    # otherwise q="culture" is applied literally before category="culture"
    # can expose museum/gallery/heritage Places.
    "culture": ("museum", "gallery", "library", "theatre", "heritage", "attraction"),
    "cultural": ("museum", "gallery", "library", "theatre", "heritage", "attraction"),
    "indoor": ("museum", "gallery", "library", "theatre", "attraction"),
    "outdoor": ("park", "garden", "viewpoint", "heritage", "attraction"),
}
