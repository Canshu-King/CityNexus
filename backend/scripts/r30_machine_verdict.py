"""Machine verdict for the R30 consent-epoch shock strike.

The verifier reads the durable strike database and the operator receipt.  It
does not mutate the Journey, manufacture a second world model, or infer
success from the report prose.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any


BACKEND = Path(__file__).resolve().parents[1]
ROOT = BACKEND.parent
PROVEN = "PROVEN"
NOT_PROVEN = "NOT_PROVEN"
CONTRADICTED = "CONTRADICTED"


def _json(raw: str | None, fallback: Any) -> Any:
    try:
        value = json.loads(raw or "")
    except (TypeError, ValueError, json.JSONDecodeError):
        return fallback
    return value


def _external(provider: str | None, model: str | None) -> bool:
    text = f"{provider or ''} {model or ''}".lower()
    forbidden = ("local-test", "deterministic", "mock-model", "citynexus-local-agent", "fake-model")
    return bool(provider and model) and not any(item in text for item in forbidden)


def _verdict(status: str, reason: str, **facts: Any) -> dict[str, Any]:
    return {"status": status, "reason": reason, "facts": facts}


def _run_steps(session, run_id: str):
    from sqlalchemy import select
    from app.db.models import AgentRunStep

    return list(session.scalars(select(AgentRunStep).where(AgentRunStep.run_id == run_id).order_by(AgentRunStep.sequence_no, AgentRunStep.id)).all())


def _response_audits(session, mission_id: str):
    from sqlalchemy import select
    from app.db.models import AuditLog

    return list(session.scalars(select(AuditLog).where(
        AuditLog.action == "agent.collective_decision.response",
        AuditLog.entity_type == "JourneyMission",
        AuditLog.entity_id == mission_id,
    ).order_by(AuditLog.created_at, AuditLog.id)).all())


def _submitted_r29_summary(path: Path) -> dict[str, Any]:
    """Read the already-submitted R29 verdict without rerunning R29."""

    if not path.is_file():
        raise SystemExit(f"submitted R29 machine verdict was not found: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    summary = payload.get("summary") or payload.get("r29_summary") or {}
    if not isinstance(summary, dict):
        raise SystemExit(f"submitted R29 machine verdict has no summary: {path}")
    normalized = {
        "overall": summary.get("overall"),
        "proven": int(summary.get("PROVEN", summary.get("proven", 0)) or 0),
        "not_proven": int(summary.get("NOT_PROVEN", summary.get("not_proven", 0)) or 0),
        "contradicted": int(summary.get("CONTRADICTED", summary.get("contradicted", 0)) or 0),
    }
    if normalized["overall"] != PROVEN or normalized["not_proven"] or normalized["contradicted"]:
        raise SystemExit(f"submitted R29 machine verdict is not PROVEN: {path}")
    return normalized


def build_verdict(
    receipt_path: str | Path,
    r29_verdict_path: str | Path | None = None,
) -> dict[str, Any]:
    receipt_file = Path(receipt_path).expanduser().resolve()
    receipt = json.loads(receipt_file.read_text(encoding="utf-8"))
    if receipt.get("status") != "R30_LIVE_RECEIPT_READY":
        raise SystemExit(f"receipt is not live-ready: {receipt.get('status')}")
    db = Path(str(receipt["db"])).expanduser().resolve()
    if not db.is_file():
        raise SystemExit(f"strike DB was not found: {db}")
    baseline_file = (
        Path(r29_verdict_path).expanduser().resolve()
        if r29_verdict_path
        else ROOT / "output" / "revolution-r29-live-20261005" / "R29_MACHINE_VERDICT.json"
    )
    r29_baseline = _submitted_r29_summary(baseline_file)
    os.environ["CITYNEXUS_DATABASE_URL"] = "sqlite:///" + db.as_posix()
    if str(BACKEND) not in sys.path:
        sys.path.insert(0, str(BACKEND))

    from sqlalchemy import select
    from app.db.models import (
        Activity,
        AgentPendingAction,
        AgentRun,
        AuditLog,
        CitySignalFixture,
        Commitment,
        Event,
        Journey,
        JourneyMember,
        JourneyMission,
        PlanVersion,
        ProviderObservation,
        ReplanProposal,
    )
    from app.db.session import SessionLocal

    journey_id = str(receipt["journey_id"])
    e1 = receipt.get("e1") or {}
    fresh = receipt.get("fresh_round") or {}
    fresh_mission_id = str(fresh.get("mission_id") or receipt.get("recovery_mission_id") or "")
    old_mission_id = str(e1.get("mission_id") or (receipt.get("r29_lineage") or {}).get("mediator_mission_id") or "")
    old_proposal_id = str(e1.get("selected_proposal_id") or "")
    fresh_proposal_id = str(fresh.get("proposal_id") or "")
    fresh_run_id = str((receipt.get("recovery_agent") or {}).get("run_id") or "")
    final_run_id = str(((receipt.get("final_closure") or {}).get("final_run_id")) or "")

    verdicts: dict[str, dict[str, Any]] = {}
    with SessionLocal() as session:
        journey = session.get(Journey, journey_id)
        old_mission = session.get(JourneyMission, old_mission_id)
        fresh_mission = session.get(JourneyMission, fresh_mission_id)
        old_proposal = session.get(ReplanProposal, old_proposal_id)
        fresh_proposal = session.get(ReplanProposal, fresh_proposal_id)
        final_run = session.get(AgentRun, final_run_id) if final_run_id else None
        recovery_run = session.get(AgentRun, fresh_run_id) if fresh_run_id else None
        if journey is None or old_mission is None or fresh_mission is None:
            raise SystemExit("R30 lineage rows are missing")
        recovery_command_run = session.scalar(
            select(AgentRun).where(AgentRun.mission_id == fresh_mission.id).order_by(AgentRun.created_at, AgentRun.id)
        )
        if recovery_command_run is not None:
            command_tools = [step.tool_name for step in _run_steps(session, recovery_command_run.id)]
            if "request_replan" in command_tools:
                recovery_run = recovery_command_run
                fresh_run_id = recovery_run.id
        old_clarification = _json(old_mission.clarification_json, {})
        fresh_clarification = _json(fresh_mission.clarification_json, {})

        round1_id = str((receipt.get("r29_lineage") or {}).get("round1_mission_id") or "")
        round1 = session.get(JourneyMission, round1_id)
        round1_data = _json(round1.clarification_json, {}) if round1 else {}
        round1_responses = round1_data.get("responses") if isinstance(round1_data.get("responses"), dict) else {}
        round1_choices = {
            str(member_id): str((value or {}).get("proposal_id") or "")
            for member_id, value in round1_responses.items()
            if isinstance(value, dict)
        }
        round1_distinct = sorted({value for value in round1_choices.values() if value})
        mediator_run_id = str((receipt.get("r29_lineage") or {}).get("mediator_run_id") or "")
        mediator_run = session.get(AgentRun, mediator_run_id) if mediator_run_id else None
        if mediator_run is None:
            mediator_run = session.scalar(
                select(AgentRun).where(AgentRun.mission_id == old_mission.id).order_by(AgentRun.created_at, AgentRun.id)
            )
            mediator_run_id = mediator_run.id if mediator_run is not None else ""
        mediator_steps = _run_steps(session, mediator_run.id) if mediator_run else []
        mediator_external = bool(mediator_run and _external(mediator_run.provider_key, mediator_run.model_key))
        mediator_opened_round = any(step.tool_name == "request_collective_decision" and _json(step.result_json, {}).get("mission_status") == "WAITING_FOR_MEMBERS" for step in mediator_steps)

        inherited_lineage = round1_data.get("status") == "MEDIATION_REQUIRED" and len(round1_distinct) >= 2 and mediator_external and mediator_opened_round
        verdicts["r29_inherited_causal_invariants"] = _verdict(
            PROVEN if inherited_lineage and r29_baseline["overall"] == PROVEN else CONTRADICTED,
            "The submitted R29 machine verdict is PROVEN and its disagreement/mediator lineage is durably present before the R30 shock." if inherited_lineage else "R29 causal lineage is incomplete.",
            round1_mission_id=round1_id,
            round1_choices=round1_choices,
            mediator_run_id=mediator_run_id,
            mediator_external=mediator_external,
            mediator_opened_round=mediator_opened_round,
            submitted_r29_verdict=str(baseline_file),
            submitted_r29_summary=r29_baseline,
        )

        e1_value = str(e1.get("stored_consent_epoch") or e1.get("recomputed_consent_epoch") or "")
        verdicts["durable_resolved_epoch_e1"] = _verdict(
            PROVEN if old_clarification.get("status") == "RESOLVED" and e1_value and str(old_clarification.get("consent_epoch") or old_clarification.get("decision_epoch")) == e1_value else CONTRADICTED,
            "The resolved R29 renewal stores the exact E1 consent epoch." if old_clarification.get("status") == "RESOLVED" and e1_value else "E1 was not durably attached to the resolved round.",
            mission_id=old_mission.id,
            consent_epoch=e1_value,
            clarification_id=old_clarification.get("clarification_id"),
        )

        shock_event_ids = {str(item) for item in (receipt.get("shock") or {}).get("events") or []}
        shock_observation_ids = {str(item) for item in (receipt.get("shock") or {}).get("observations") or []}
        events = list(session.scalars(select(Event).where(Event.journey_id == journey_id)).all())
        observations = list(session.scalars(select(ProviderObservation).where(ProviderObservation.journey_id == journey_id)).all())
        shock_events = [row for row in events if row.id in shock_event_ids and row.provider_key == "city-signal-fixture"]
        shock_observations = [row for row in observations if row.id in shock_observation_ids]
        fixture = session.get(CitySignalFixture, journey_id)
        fixture_audit = list(session.scalars(select(AuditLog).where(AuditLog.journey_id == journey_id, AuditLog.action == "city.signal.fixture.updated")).all())
        verdicts["provider_shock_after_e1"] = _verdict(
            PROVEN if shock_events and shock_observations and fixture is not None and fixture.state == "DISRUPTED" and fixture_audit else CONTRADICTED,
            "A normal CitySignal fixture transition produced provider observations and Event evidence after E1." if shock_events and shock_observations and fixture is not None and fixture.state == "DISRUPTED" else "The provider shock is not durably evidenced.",
            event_ids=sorted(shock_event_ids),
            observation_ids=sorted(shock_observation_ids),
            fixture_revision=fixture.revision if fixture else None,
            fixture_audit_count=len(fixture_audit),
        )

        e_after = receipt.get("e_after_shock") or {}
        e2_value = str(receipt.get("fresh_consent_epoch") or fresh_clarification.get("consent_epoch") or fresh_clarification.get("decision_epoch") or "")
        material_e1 = str(e1.get("selected_material_fingerprint") or ((e1.get("decision_material") or {}).get("selected_plan") or {}).get("immutable_fingerprint") or "")
        material_after = str(e_after.get("selected_material_fingerprint") or "")
        verdicts["material_world_fingerprint_changed"] = _verdict(
            PROVEN if material_e1 and material_after and material_e1 != material_after and str(e_after.get("recomputed_consent_epoch") or "") != e1_value else CONTRADICTED,
            "The provider shock changes both selected material fingerprint and authority epoch." if material_e1 and material_after and material_e1 != material_after and str(e_after.get("recomputed_consent_epoch") or "") != e1_value else "The material fingerprint/epoch change is not proven.",
            e1_epoch=e1_value,
            post_shock_epoch=e_after.get("recomputed_consent_epoch"),
            e1_material_fingerprint=material_e1,
            post_shock_material_fingerprint=material_after,
        )

        stale_steps = _run_steps(session, str((receipt.get("stale_attempt") or {}).get("run_id") or "")) if (receipt.get("stale_attempt") or {}).get("run_id") else []
        stale_errors = [
            _json(step.result_json, {}) for step in stale_steps
            if step.tool_name == "accept_replan" and step.status == "TOOL_ERROR"
        ]
        stale_pending = list(session.scalars(select(AgentPendingAction).where(AgentPendingAction.journey_id == journey_id, AgentPendingAction.status == "FAILED")).all())
        stale_core = any("COLLECTIVE_CONSENT_EPOCH_STALE" in json.dumps(item, ensure_ascii=False) for item in stale_errors) or "COLLECTIVE_CONSENT_EPOCH_STALE" in str((receipt.get("stale_attempt") or {}).get("failure_reason") or "")
        verdicts["old_consent_rejected_at_core"] = _verdict(
            PROVEN if stale_core and stale_pending else CONTRADICTED,
            "The old resolved child reached the mutation core and persisted COLLECTIVE_CONSENT_EPOCH_STALE." if stale_core and stale_pending else "No durable core stale rejection was found.",
            stale_errors=stale_errors,
            failed_pending_action_ids=[row.id for row in stale_pending],
        )
        verdicts["no_sibling_consumed_e1"] = _verdict(
            PROVEN if old_proposal is not None and old_proposal.status != "ACCEPTED" and old_proposal.id not in [row.id for row in session.scalars(select(ReplanProposal).where(ReplanProposal.journey_id == journey_id, ReplanProposal.status == "ACCEPTED")).all()] else CONTRADICTED,
            "The E1 selected proposal and its siblings did not consume stale authority." if old_proposal is not None and old_proposal.status != "ACCEPTED" else "An E1 proposal was accepted.",
            old_proposal_id=old_proposal_id,
            old_proposal_status=old_proposal.status if old_proposal else None,
        )
        verdicts["no_older_mediation_resurrected"] = _verdict(
            PROVEN if old_proposal is not None and old_proposal.status != "ACCEPTED" and fresh_clarification.get("selected_proposal_id") == fresh_proposal_id else CONTRADICTED,
            "Recovery consumed only the fresh server-owned selection." if old_proposal is not None and old_proposal.status != "ACCEPTED" and fresh_clarification.get("selected_proposal_id") == fresh_proposal_id else "An older mediation resurfaced.",
            old_status=old_proposal.status if old_proposal else None,
            fresh_selected=fresh_clarification.get("selected_proposal_id"),
        )

        recovery_external = bool(recovery_run and _external(recovery_run.provider_key, recovery_run.model_key))
        recovery_steps = _run_steps(session, recovery_run.id) if recovery_run else []
        recovery_tools = [step.tool_name for step in recovery_steps]
        verdicts["external_agent_recovery"] = _verdict(
            PROVEN if recovery_external and "inspect_twin" in recovery_tools and "request_replan" in recovery_tools and "request_collective_decision" in recovery_tools else NOT_PROVEN,
            "A configured external Agent inspected the shock and created the fresh replan/decision surface." if recovery_external and "inspect_twin" in recovery_tools and "request_replan" in recovery_tools and "request_collective_decision" in recovery_tools else "External recovery is incomplete.",
            run_id=fresh_run_id,
            provider_key=recovery_run.provider_key if recovery_run else None,
            model_key=recovery_run.model_key if recovery_run else None,
            tools=recovery_tools,
        )

        active_plan = session.get(PlanVersion, journey.active_plan_version_id) if journey.active_plan_version_id else None
        old_base = session.get(PlanVersion, e1.get("base_plan_version_id")) if e1.get("base_plan_version_id") else None
        old_locked_places = {
            item.place_id for item in session.scalars(select(Activity).where(Activity.plan_version_id == old_base.id, Activity.locked.is_(True))).all()
        } if old_base else set()
        active_locked_places = {
            item.place_id for item in session.scalars(select(Activity).where(Activity.plan_version_id == active_plan.id, Activity.locked.is_(True))).all()
        } if active_plan else set()
        c4_rows = list(session.scalars(select(Commitment).where(Commitment.journey_id == journey_id, Commitment.level == "C4_Anchored", Commitment.status == "ACTIVE")).all())
        verdicts["protected_commitments_survived"] = _verdict(
            PROVEN if active_plan is not None and c4_rows and old_locked_places.intersection(active_locked_places) else CONTRADICTED,
            "The protected locked anchor and active C4 commitment survived recovery." if active_plan is not None and c4_rows and old_locked_places.intersection(active_locked_places) else "Protected commitment continuity is not proven.",
            old_locked_places=sorted(item for item in old_locked_places if item),
            active_locked_places=sorted(item for item in active_locked_places if item),
            active_commitment_ids=[row.id for row in c4_rows],
        )
        current = session.get(Activity, journey.current_activity_id) if journey.current_activity_id else None
        verdicts["completed_execution_truth_survived"] = _verdict(
            PROVEN if current is not None and current.status in {"ACTIVE", "ARRIVED", "IN_PROGRESS", "COMPLETED"} else NOT_PROVEN,
            "The execution cursor remains on the same Journey after recovery." if current is not None and current.status in {"ACTIVE", "ARRIVED", "IN_PROGRESS", "COMPLETED"} else "Execution cursor continuity is not proven.",
            current_activity_id=journey.current_activity_id,
            current_status=current.status if current else None,
            active_plan_version_id=journey.active_plan_version_id,
        )
        fresh_options = fresh_clarification.get("candidate_options") or []
        fresh_response_audits = _response_audits(session, fresh_mission_id)
        verdicts["fresh_server_owned_decision_surface"] = _verdict(
            PROVEN if fresh_clarification.get("kind") == "COLLECTIVE_TRADEOFF" and fresh_clarification.get("status") == "RESOLVED" and len(fresh_options) >= 2 and fresh_response_audits else CONTRADICTED,
            "A new server-owned collective decision surface was resolved after recovery." if fresh_clarification.get("kind") == "COLLECTIVE_TRADEOFF" and fresh_clarification.get("status") == "RESOLVED" and len(fresh_options) >= 2 else "Fresh decision surface is missing.",
            mission_id=fresh_mission_id,
            clarification_id=fresh_clarification.get("clarification_id"),
            candidate_count=len(fresh_options),
        )
        in_force_ids = {row.id for row in session.scalars(select(JourneyMember).where(JourneyMember.journey_id == journey_id, JourneyMember.removed_at.is_(None))).all()}
        required_fresh = {str(item) for item in fresh_clarification.get("required_member_ids") or []}
        verdicts["required_member_scope_recomputed"] = _verdict(
            PROVEN if required_fresh and required_fresh.issubset(in_force_ids) and "request_collective_decision" in recovery_tools else CONTRADICTED,
            "Fresh required members are server-selected in-force Journey principals." if required_fresh and required_fresh.issubset(in_force_ids) and "request_collective_decision" in recovery_tools else "Fresh scope was not proven server-derived.",
            required_member_ids=sorted(required_fresh),
            in_force_member_ids=sorted(in_force_ids),
        )
        verdicts["fresh_server_owned_replan"] = _verdict(
            PROVEN if fresh_proposal is not None and fresh_proposal.trigger_event_id and "request_replan" in recovery_tools else CONTRADICTED,
            "The post-shock external Agent created the fresh replan through request_replan." if fresh_proposal is not None and fresh_proposal.trigger_event_id and "request_replan" in recovery_tools else "Fresh replan construction is not proven.",
            proposal_id=fresh_proposal_id,
            trigger_event_id=fresh_proposal.trigger_event_id if fresh_proposal else None,
        )
        response_actor_ok = bool(fresh_response_audits) and all(row.actor_type == "AUTHENTICATED_TRAVELER" for row in fresh_response_audits)
        old_response_values = {str(value.get("proposal_id")) for value in (old_clarification.get("responses") or {}).values() if isinstance(value, dict)}
        fresh_response_values = {str(value.get("proposal_id")) for value in (fresh_clarification.get("responses") or {}).values() if isinstance(value, dict)}
        verdicts["fresh_authenticated_responses_not_copied"] = _verdict(
            PROVEN if response_actor_ok and fresh_response_values and fresh_response_values == {fresh_proposal_id} and fresh_proposal_id not in old_response_values else CONTRADICTED,
            "Fresh signed member responses point to the new proposal envelope and are not E1 response copies." if response_actor_ok and fresh_response_values and fresh_response_values == {fresh_proposal_id} and fresh_proposal_id not in old_response_values else "Fresh response authentication or non-copying is not proven.",
            response_actor_types=sorted({row.actor_type for row in fresh_response_audits}),
            old_response_values=sorted(old_response_values),
            fresh_response_values=sorted(fresh_response_values),
        )
        verdicts["fresh_epoch_e2_differs"] = _verdict(
            PROVEN if e2_value and e1_value and e2_value != e1_value and fresh_clarification.get("consent_epoch") == e2_value else CONTRADICTED,
            "Fresh consent is bound to E2, which differs from E1." if e2_value and e1_value and e2_value != e1_value else "E2 was not proven distinct from E1.",
            e1=e1_value,
            e2=e2_value,
        )
        accepted = list(session.scalars(select(ReplanProposal).where(ReplanProposal.journey_id == journey_id, ReplanProposal.status == "ACCEPTED")).all())
        verdicts["exactly_one_final_accept"] = _verdict(
            PROVEN if len(accepted) == 1 and accepted[0].id == fresh_proposal_id and journey.active_plan_version_id == accepted[0].proposed_plan_version_id and final_run is not None and final_run.status == "COMPLETED" else CONTRADICTED,
            "Exactly one fresh recovery proposal is accepted and active." if len(accepted) == 1 and accepted[0].id == fresh_proposal_id else "Final acceptance count or active-plan identity is wrong.",
            accepted_proposal_ids=[row.id for row in accepted],
            active_plan_version_id=journey.active_plan_version_id,
            final_run_id=final_run_id,
        )
        control_ids = {str(item) for item in (receipt.get("irrelevant_control") or {}).get("observation_ids") or []}
        material_obs_ids = {str(item.get("id")) for item in (e1.get("decision_material") or {}).get("selected_plan", {}).get("provider_observations") or []}
        verdicts["irrelevant_evidence_churn_does_not_invalidate"] = _verdict(
            PROVEN if control_ids and control_ids.isdisjoint(material_obs_ids) and (receipt.get("control_epoch") or {}).get("unchanged") is True else CONTRADICTED,
            "Unrelated provider churn is outside the decision-material envelope and leaves E1 equivalent." if control_ids and control_ids.isdisjoint(material_obs_ids) else "Control churn entered the material envelope.",
            control_observation_ids=sorted(control_ids),
            material_observation_ids=sorted(material_obs_ids),
            control_epoch=receipt.get("control_epoch"),
        )
        verdicts["same_journey_execution_continued"] = _verdict(
            PROVEN if final_run is not None and final_run.journey_id == journey_id and journey.id == journey_id else CONTRADICTED,
            "Recovery remained on the same Journey." if final_run is not None and final_run.journey_id == journey_id else "Recovery crossed Journey identity.",
            journey_id=journey_id,
            final_run_journey_id=final_run.journey_id if final_run else None,
        )
        verdicts["final_external_continuation_completed"] = _verdict(
            PROVEN if final_run is not None and final_run.status == "COMPLETED" and _external(final_run.provider_key, final_run.model_key) else NOT_PROVEN,
            "The fresh resolved child completed through the configured external Agent and approval continuation." if final_run is not None and final_run.status == "COMPLETED" and _external(final_run.provider_key, final_run.model_key) else "Final external continuation is not proven.",
            final_run_id=final_run_id,
            provider_key=final_run.provider_key if final_run else None,
            model_key=final_run.model_key if final_run else None,
        )

    statuses = {key: value["status"] for key, value in verdicts.items()}
    summary = {
        "overall": PROVEN if all(value == PROVEN for value in statuses.values()) else "NOT_PROVEN",
        "proven": sum(value == PROVEN for value in statuses.values()),
        "not_proven": sum(value == NOT_PROVEN for value in statuses.values()),
        "contradicted": sum(value == CONTRADICTED for value in statuses.values()),
        "claim_count": len(statuses),
    }
    return {
        "verdict": "R30_MACHINE_VERDICT",
        "summary": summary,
        "receipt": str(receipt_file),
        "db": str(db),
        "journey_id": journey_id,
        "r29_baseline": {
            "verdict": str(baseline_file),
            "summary": r29_baseline,
        },
        "claims": verdicts,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--receipt", default=str(ROOT / "output" / "revolution-r30-live-20261006" / "R30_LIVE_RECEIPT.json"))
    parser.add_argument("--r29-verdict", default=str(ROOT / "output" / "revolution-r29-live-20261005" / "R29_MACHINE_VERDICT.json"))
    parser.add_argument("--run-id")
    parser.add_argument("--output")
    args = parser.parse_args()
    result = build_verdict(args.receipt, args.r29_verdict)
    output = Path(args.output).expanduser().resolve() if args.output else Path(args.receipt).with_name("R30_MACHINE_VERDICT.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(json.dumps({"summary": result["summary"], "output": str(output)}, ensure_ascii=True))
    return 0 if result["summary"]["overall"] == PROVEN else 4


if __name__ == "__main__":
    raise SystemExit(main())
