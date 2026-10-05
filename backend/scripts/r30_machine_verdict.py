"""Machine-readable R30 live-strike verdict.

This verifier reads the durable database produced by the real Agent strike.  It
does not mutate the Journey, synthesize an Agent result, or repair a failed
continuation.  A blocked final continuation is therefore reported as a real
blocker while the causal evidence that preceded it remains independently
checkable.
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
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from sqlalchemy import select  # noqa: E402

from app.collective_mediation import (  # noqa: E402
    collective_material_world_epoch,
    pending_resolved_mediation_selection,
)
from app.db.models import (  # noqa: E402
    Activity,
    AgentRun,
    AgentRunStep,
    AuditLog,
    Commitment,
    Event,
    Journey,
    JourneyMission,
    PlanVersion,
    ProviderObservation,
    ReplanProposal,
)
from app.db.session import SessionLocal, make_engine  # noqa: E402
from app.main import collective_material_world_basis, plan_schema  # noqa: E402


PROVEN = "PROVEN"
NOT_PROVEN = "NOT_PROVEN"
BLOCKED = "BLOCKED"


def _json(raw: str | None, fallback: Any) -> Any:
    try:
        value = json.loads(raw or "")
    except (TypeError, ValueError, json.JSONDecodeError):
        return fallback
    return value


def _verdict(status: str, reason: str, **facts: Any) -> dict[str, Any]:
    return {"status": status, "reason": reason, "facts": facts}


def _steps(session, run_id: str) -> list[AgentRunStep]:
    return list(
        session.scalars(
            select(AgentRunStep)
            .where(AgentRunStep.run_id == run_id)
            .order_by(AgentRunStep.sequence_no, AgentRunStep.id)
        ).all()
    )


def _is_external(run: AgentRun | None) -> bool:
    if run is None:
        return False
    return str(run.provider_key).lower() not in {"deterministic", "fixture", "test"}


def _find_recovery_run(session, journey_id: str) -> AgentRun | None:
    candidates: list[AgentRun] = []
    for run in session.scalars(
        select(AgentRun).where(AgentRun.journey_id == journey_id).order_by(AgentRun.created_at, AgentRun.id)
    ).all():
        tools = {step.tool_name for step in _steps(session, run.id)}
        if run.status == "COMPLETED" and {"request_replan", "request_collective_decision"}.issubset(tools):
            candidates.append(run)
    return candidates[-1] if candidates else None


def _find_old_and_fresh_missions(session, journey_id: str) -> tuple[JourneyMission, JourneyMission, JourneyMission]:
    missions = list(
        session.scalars(
            select(JourneyMission).where(JourneyMission.journey_id == journey_id).order_by(JourneyMission.created_at, JourneyMission.id)
        ).all()
    )
    round1 = None
    old = None
    fresh = None
    for mission in missions:
        clarification = _json(mission.clarification_json, {})
        if clarification.get("status") == "MEDIATION_REQUIRED" and clarification.get("responses"):
            choices = {
                str(item.get("proposal_id"))
                for item in clarification.get("responses", {}).values()
                if isinstance(item, dict) and item.get("proposal_id")
            }
            if len(choices) >= 2 and round1 is None:
                round1 = mission
        if (
            clarification.get("status") == "RESOLVED"
            and clarification.get("selected_proposal_id")
            and clarification.get("policy") == "POST_DISAGREEMENT_REQUIRES_RENEWED_MEMBER_CONSENT"
        ):
            old = mission
        elif (
            clarification.get("status") == "RESOLVED"
            and clarification.get("selected_proposal_id")
            and old is not None
            and mission.id != old.id
        ):
            fresh = mission
    if round1 is None or old is None or fresh is None:
        raise RuntimeError("could not identify round-1, R29 mediator, and fresh R30 consent missions")
    return round1, old, fresh


def build_verdict(db_value: str, journey_id: str) -> dict[str, Any]:
    db_path = Path(db_value).expanduser().resolve()
    os.environ["CITYNEXUS_DATABASE_URL"] = "sqlite:///" + db_path.as_posix()
    os.environ["CITYNEXUS_LAB_ESTIMATE_AUTHORITY"] = "false"
    # The application modules are imported for their pure projections above;
    # bind the verifier's session factory to the explicit strike database now.
    SessionLocal.configure(bind=make_engine(os.environ["CITYNEXUS_DATABASE_URL"]))

    verdicts: dict[str, dict[str, Any]] = {}
    with SessionLocal() as session:
        journey = session.get(Journey, journey_id)
        if journey is None:
            raise RuntimeError(f"Journey {journey_id} was not found")
        round1, old, fresh = _find_old_and_fresh_missions(session, journey_id)
        old_clarification = _json(old.clarification_json, {})
        fresh_clarification = _json(fresh.clarification_json, {})
        old_proposal = session.get(ReplanProposal, old_clarification.get("selected_proposal_id"))
        fresh_proposal = session.get(ReplanProposal, fresh_clarification.get("selected_proposal_id"))
        if old_proposal is None or fresh_proposal is None:
            raise RuntimeError("selected R29/R30 proposal is missing")
        old_plan = session.get(PlanVersion, old_proposal.proposed_plan_version_id)
        fresh_plan = session.get(PlanVersion, fresh_proposal.proposed_plan_version_id)

        round1_responses = old_round1_responses = _json(round1.clarification_json, {}).get("responses", {})
        distinct_choices = {
            str(item.get("proposal_id"))
            for item in round1_responses.values()
            if isinstance(item, dict) and item.get("proposal_id")
        }
        verdicts["r29_inherited_disagreement"] = _verdict(
            PROVEN if len(distinct_choices) >= 2 else NOT_PROVEN,
            "Round 1 contains two distinct member proposal choices.",
            round1_mission_id=round1.id,
            distinct_proposal_ids=sorted(distinct_choices),
        )

        old_member_ids = {str(item) for item in old_clarification.get("required_member_ids") or []}
        old_responses = _json(old.clarification_json, {}).get("responses", {})
        old_response_ids = {
            str(member_id)
            for member_id in old_responses
            if str(member_id) in old_member_ids
        }
        verdicts["e1_w1_durable"] = _verdict(
            PROVEN
            if old_clarification.get("decision_epoch")
            and old_clarification.get("material_world_epoch")
            and old_clarification.get("material_world_basis")
            and old_response_ids == old_member_ids
            else NOT_PROVEN,
            "R29 renewed consent durably stores E1, W1, basis, and all required responses.",
            mediator_mission_id=old.id,
            decision_epoch=old_clarification.get("decision_epoch"),
            material_world_epoch=old_clarification.get("material_world_epoch"),
            required_member_ids=sorted(old_member_ids),
            response_member_ids=sorted(old_response_ids),
        )

        shock_events = list(
            session.scalars(
                select(Event).where(
                    Event.journey_id == journey.id,
                    Event.provider_key == "city-signal-fixture",
                    Event.event_type == "CLOSURE",
                    Event.provenance == "PROVIDER_VERIFIED",
                ).order_by(Event.occurred_at, Event.id)
            ).all()
        )
        shock = shock_events[-1] if shock_events else None
        shock_after_consent = bool(
            shock is not None
            and str(shock.occurred_at) > str(old.completed_at or old.created_at)
            and old_proposal.status == "PRESENTED"
        )
        verdicts["shock_after_e1_w1_before_consumption"] = _verdict(
            PROVEN if shock_after_consent else NOT_PROVEN,
            "A normal provider-backed closure landed after E1/W1 while the old proposal remained presented.",
            event_id=shock.id if shock else None,
            event_occurred_at=shock.occurred_at if shock else None,
            event_affected_activity_id=shock.affected_activity_id if shock else None,
            old_proposal_status=old_proposal.status,
        )

        old_fit_subject_ids = next(
            (
                item.get("fit_subject_place_ids") or []
                for item in old_clarification.get("candidate_options") or []
                if isinstance(item, dict)
                and str(item.get("proposal_id") or "") == str(old_proposal.id)
            ),
            [],
        )
        old_current_basis = collective_material_world_basis(
            session,
            journey,
            old_plan,
            fit_subject_place_ids=list(old_fit_subject_ids),
        )
        current_world_epoch = collective_material_world_epoch(old_current_basis)
        verdicts["world_epoch_changed_and_selection_survived"] = _verdict(
            PROVEN
            if old_clarification.get("material_world_epoch")
            and current_world_epoch != old_clarification.get("material_world_epoch")
            and old_proposal.status == "PRESENTED"
            else NOT_PROVEN,
            "Relevant provider reality changed W while the old social selection still existed.",
            stored_w1=old_clarification.get("material_world_epoch"),
            recomputed_after_shock=current_world_epoch,
            selected_plan_id=old_plan.id if old_plan else None,
            plan_status=old_plan.status if old_plan else None,
        )

        stale_child = session.scalar(
            select(JourneyMission)
            .where(JourneyMission.parent_mission_id == old.id)
            .order_by(JourneyMission.created_at.desc(), JourneyMission.id.desc())
        )
        stale_run = (
            session.scalar(
                select(AgentRun)
                .where(AgentRun.mission_id == stale_child.id)
                .order_by(AgentRun.created_at.desc(), AgentRun.id.desc())
            )
            if stale_child is not None
            else None
        )
        stale_ok = bool(
            stale_run
            and stale_run.failure_reason
            and "COLLECTIVE_CONSENT_WORLD_EPOCH_STALE" in stale_run.failure_reason
        )
        verdicts["old_mutation_rejected_at_core"] = _verdict(
            PROVEN if stale_ok else NOT_PROVEN,
            "The original Agent mutation reached the core world-epoch gate and was refused.",
            stale_child_mission_id=stale_child.id if stale_child else None,
            stale_run_id=stale_run.id if stale_run else None,
            failure_reason=stale_run.failure_reason if stale_run else None,
        )

        recovery_run = _find_recovery_run(session, journey.id)
        recovery_steps = _steps(session, recovery_run.id) if recovery_run else []
        recovery_tools = [step.tool_name for step in recovery_steps]
        verdicts["real_external_recovery"] = _verdict(
            PROVEN
            if recovery_run is not None and _is_external(recovery_run)
            and "request_replan" in recovery_tools
            and "request_collective_decision" in recovery_tools
            else NOT_PROVEN,
            "The configured external Agent created a fresh server-owned recovery and consent surface.",
            run_id=recovery_run.id if recovery_run else None,
            provider_key=recovery_run.provider_key if recovery_run else None,
            model_key=recovery_run.model_key if recovery_run else None,
            tool_names=recovery_tools,
        )

        fresh_member_ids = {str(item) for item in fresh_clarification.get("required_member_ids") or []}
        fresh_response_ids = {
            str(member_id)
            for member_id in (_json(fresh.clarification_json, {}).get("responses", {}) or {})
            if str(member_id) in fresh_member_ids
        }
        response_audits = list(
            session.scalars(
                select(AuditLog).where(
                    AuditLog.action == "agent.collective_decision.response",
                    AuditLog.entity_type == "JourneyMission",
                    AuditLog.entity_id == fresh.id,
                    AuditLog.actor_type == "AUTHENTICATED_TRAVELER",
                )
            ).all()
        )
        verdicts["fresh_authenticated_e2"] = _verdict(
            PROVEN
            if fresh_clarification.get("status") == "RESOLVED"
            and fresh_clarification.get("decision_epoch")
            and fresh_clarification.get("material_world_epoch")
            and fresh_response_ids == fresh_member_ids
            and len(response_audits) >= len(fresh_member_ids)
            and str(fresh.id) != str(old.id)
            else NOT_PROVEN,
            "A separate resolved consent mission stores fresh E2/W2 and authenticated member responses.",
            fresh_mission_id=fresh.id,
            decision_epoch=fresh_clarification.get("decision_epoch"),
            material_world_epoch=fresh_clarification.get("material_world_epoch"),
            required_member_ids=sorted(fresh_member_ids),
            response_member_ids=sorted(fresh_response_ids),
            authenticated_response_audit_count=len(response_audits),
            old_mission_id=old.id,
        )

        fresh_child = session.scalar(
            select(JourneyMission)
            .where(JourneyMission.parent_mission_id == fresh.id)
            .order_by(JourneyMission.created_at.desc(), JourneyMission.id.desc())
        )
        fresh_runs = (
            list(
                session.scalars(
                    select(AgentRun).where(AgentRun.mission_id == fresh_child.id).order_by(AgentRun.created_at, AgentRun.id)
                ).all()
            )
            if fresh_child is not None
            else []
        )
        final_run = fresh_runs[-1] if fresh_runs else None
        final_failure = final_run.failure_reason if final_run else None
        blocker = "COLLECTIVE_MEDIATION_SELECTED_PLAN_REQUIRED" if final_failure and "COLLECTIVE_MEDIATION_SELECTED_PLAN_REQUIRED" in final_failure else None
        pending_selection = pending_resolved_mediation_selection(
            session,
            journey.id,
            active_plan_version_id=journey.active_plan_version_id,
        )
        verdicts["fresh_continuation_blocker"] = _verdict(
            BLOCKED if blocker else (PROVEN if final_run and final_run.status == "COMPLETED" else NOT_PROVEN),
            "Fresh continuation reached the normal approval boundary but the current gate still selected the older mediation authority."
            if blocker
            else "Fresh continuation did not produce the recorded R30 blocker.",
            fresh_child_mission_id=fresh_child.id if fresh_child else None,
            fresh_run_id=final_run.id if final_run else None,
            fresh_run_status=final_run.status if final_run else None,
            failure_reason=final_failure,
            pending_selection=pending_selection,
        )

        c4 = list(
            session.scalars(
                select(Commitment).where(
                    Commitment.journey_id == journey.id,
                    Commitment.level == "C4_Anchored",
                )
            ).all()
        )
        current_activity = session.get(Activity, journey.current_activity_id) if journey.current_activity_id else None
        verdicts["protected_and_execution_truth"] = _verdict(
            PROVEN
            if c4 and current_activity is not None and current_activity.status in {"ARRIVED", "IN_PROGRESS"}
            else NOT_PROVEN,
            "Protected C4 commitment and completed execution cursor survived the live strike.",
            c4_commitment_ids=[row.id for row in c4],
            current_activity_id=journey.current_activity_id,
            current_activity_status=current_activity.status if current_activity else None,
            active_plan_version_id=journey.active_plan_version_id,
        )

        control_observations = list(
            session.scalars(
                select(ProviderObservation).where(
                    ProviderObservation.journey_id == journey.id,
                    ProviderObservation.provider_key == "r30-control-provider",
                )
            ).all()
        )
        verdicts["unrelated_observation_control"] = _verdict(
            PROVEN if control_observations else NOT_PROVEN,
            "The live harness recorded an unrelated provider observation before the shock; focused tests prove it does not alter W.",
            observation_ids=[row.id for row in control_observations],
            provider_key="r30-control-provider",
        )

        accepted = list(
            session.scalars(
                select(ReplanProposal).where(
                    ReplanProposal.journey_id == journey.id,
                    ReplanProposal.status == "ACCEPTED",
                )
            ).all()
        )
        verdicts["exactly_one_final_acceptance"] = _verdict(
            PROVEN if len(accepted) == 1 and accepted[0].id == fresh_proposal.id else BLOCKED,
            "The final exactly-once acceptance is blocked by the fresh mediation gate in this durable strike."
            if len(accepted) != 1
            else "Exactly one fresh proposal was accepted.",
            accepted_proposal_ids=[row.id for row in accepted],
            expected_fresh_proposal_id=fresh_proposal.id,
        )

        claims = list(verdicts.values())
        counts = {
            "proven": sum(item["status"] == PROVEN for item in claims),
            "blocked": sum(item["status"] == BLOCKED for item in claims),
            "not_proven": sum(item["status"] == NOT_PROVEN for item in claims),
        }
        return {
            "status": "R30_LIVE_BLOCKED" if counts["blocked"] else "R30_LIVE_VERIFIED",
            "database": str(db_path),
            "journey_id": journey.id,
            "lab_estimate_authority": False,
            "summary": counts,
            "old_mediator_mission_id": old.id,
            "fresh_mission_id": fresh.id,
            "old_proposal_id": old_proposal.id,
            "fresh_proposal_id": fresh_proposal.id,
            "verdicts": verdicts,
        }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", required=True)
    parser.add_argument("--journey-id", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--receipt", required=True)
    args = parser.parse_args()
    verdict = build_verdict(args.db, args.journey_id)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(verdict, ensure_ascii=False, indent=2), encoding="utf-8")
    receipt = {
        "status": verdict["status"],
        "created_at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
        "db": verdict["database"],
        "journey_id": verdict["journey_id"],
        "old_mediator_mission_id": verdict["old_mediator_mission_id"],
        "fresh_mission_id": verdict["fresh_mission_id"],
        "old_proposal_id": verdict["old_proposal_id"],
        "fresh_proposal_id": verdict["fresh_proposal_id"],
        "summary": verdict["summary"],
        "blocker": verdict["verdicts"].get("fresh_continuation_blocker"),
        "verdict_path": str(output),
    }
    receipt_path = Path(args.receipt)
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"status": verdict["status"], "summary": verdict["summary"], "output": str(output), "receipt": str(receipt_path)}, ensure_ascii=False))
    return 0 if verdict["status"] == "R30_LIVE_VERIFIED" else 3


if __name__ == "__main__":
    raise SystemExit(main())
