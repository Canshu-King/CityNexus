from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

BACKEND = Path(__file__).resolve().parents[1]
SCRIPTS = Path(__file__).resolve().parent
for path in (BACKEND, SCRIPTS):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from sqlalchemy import select  # noqa: E402

from app.agent.gateway import _journey_has_unresolved_collective_mediation  # noqa: E402
from app.db.models import (  # noqa: E402
    AgentRun,
    AgentRunStep,
    AuditLog,
    JourneyMember,
    JourneyMission,
    ReplanProposal,
)
from app.db.session import SessionLocal  # noqa: E402
from r28_machine_verdict import (  # noqa: E402
    CONTRADICTED,
    NOT_PROVEN,
    PROVEN,
    _looks_external,
    build_verdict as build_r28_verdict,
)


_ACTIVE_REALITY_TOOLS = {
    "accept_replan",
    "activate_standby",
    "replace_activity",
    "reschedule_activity",
    "create_booking",
    "cancel_refundable_booking",
    "request_commitment_change",
    "apply_clarified_horizon_choice",
}


def _json(value: str | None, fallback: Any) -> Any:
    try:
        parsed = json.loads(value or "")
    except (TypeError, ValueError, json.JSONDecodeError):
        return fallback
    return parsed


def _after(row: AuditLog) -> dict[str, Any]:
    value = _json(row.after_json, {})
    return value if isinstance(value, dict) else {}


def _verdict(status: str, reason: str, **facts: Any) -> dict[str, Any]:
    return {"status": status, "reason": reason, "facts": facts}


def _response_audits(session, mission_id: str) -> list[AuditLog]:
    return list(
        session.scalars(
            select(AuditLog)
            .where(
                AuditLog.action == "agent.collective_decision.response",
                AuditLog.entity_type == "JourneyMission",
                AuditLog.entity_id == mission_id,
                AuditLog.actor_type == "AUTHENTICATED_TRAVELER",
            )
            .order_by(AuditLog.created_at, AuditLog.id)
        ).all()
    )


def _run_steps(session, run_id: str) -> list[AgentRunStep]:
    return list(
        session.scalars(
            select(AgentRunStep)
            .where(AgentRunStep.run_id == run_id)
            .order_by(AgentRunStep.sequence_no, AgentRunStep.id)
        ).all()
    )


def build_verdict(run_id: str) -> dict[str, Any]:
    r28 = build_r28_verdict(run_id)
    verdicts: dict[str, dict[str, Any]] = {}

    with SessionLocal() as session:
        final_run = session.get(AgentRun, run_id)
        if final_run is None:
            raise SystemExit(f"AgentRun {run_id} was not found")
        final_mission = session.get(JourneyMission, final_run.mission_id)
        if final_mission is None or not final_mission.parent_mission_id:
            raise SystemExit("R29 final AgentRun has no resolved collective parent mission")

        round2 = session.get(JourneyMission, final_mission.parent_mission_id)
        if round2 is None:
            raise SystemExit("R29 mediator/round-2 mission is missing")

        mediation_intent_root = _json(round2.resolved_intent_json, {})
        mediation_intent = (
            mediation_intent_root.get("collective_mediation")
            if isinstance(mediation_intent_root, dict)
            else None
        )
        source_id = (
            str(mediation_intent.get("source_mission_id") or "")
            if isinstance(mediation_intent, dict)
            else ""
        )
        round1 = session.get(JourneyMission, source_id) if source_id else None

        lineage_ok = bool(
            isinstance(mediation_intent, dict)
            and mediation_intent.get("kind") == "DISAGREEMENT_MEDIATION"
            and round1 is not None
            and round2.parent_mission_id == round1.id
            and final_mission.parent_mission_id == round2.id
        )
        verdicts["mediation_lineage"] = _verdict(
            PROVEN if lineage_ok else CONTRADICTED,
            "Final mutation lineage descends from the disagreement mediator."
            if lineage_ok
            else "Final AgentRun is not causally linked to a disagreement mediator.",
            round1_mission_id=round1.id if round1 else None,
            mediator_mission_id=round2.id,
            final_mission_id=final_mission.id,
            mediation_kind=mediation_intent.get("kind") if isinstance(mediation_intent, dict) else None,
        )

        round1_payload = _json(round1.clarification_json, {}) if round1 else {}
        round1_required = {
            str(value) for value in (round1_payload.get("required_member_ids") or [])
        }
        round1_responses = (
            round1_payload.get("responses")
            if isinstance(round1_payload.get("responses"), dict)
            else {}
        )
        round1_choices = {
            str(member_id): str((response or {}).get("proposal_id") or "")
            for member_id, response in round1_responses.items()
            if isinstance(response, dict)
        }
        distinct_round1_choices = {value for value in round1_choices.values() if value}
        disagreement_ok = bool(
            round1
            and round1_payload.get("status") == "MEDIATION_REQUIRED"
            and round1_required
            and round1_required.issubset(set(round1_choices))
            and len(distinct_round1_choices) >= 2
            and not round1_payload.get("selected_proposal_id")
        )
        verdicts["authenticated_disagreement_state"] = _verdict(
            PROVEN if disagreement_ok else CONTRADICTED,
            "Round 1 durably records distinct member choices and no selected winner."
            if disagreement_ok
            else "Round 1 does not prove a genuine unresolved disagreement.",
            status=round1_payload.get("status"),
            required_member_ids=sorted(round1_required),
            member_choices=round1_choices,
            distinct_proposal_ids=sorted(distinct_round1_choices),
            selected_proposal_id=round1_payload.get("selected_proposal_id"),
        )

        round1_runs = (
            list(
                session.scalars(
                    select(AgentRun)
                    .where(AgentRun.mission_id == round1.id)
                    .order_by(AgentRun.created_at, AgentRun.id)
                ).all()
            )
            if round1
            else []
        )
        round1_agent_run = None
        round1_agent_steps: list[AgentRunStep] = []
        for candidate in round1_runs:
            steps = _run_steps(session, candidate.id)
            opened_collective = any(
                step.tool_name == "request_collective_decision"
                and isinstance(_json(step.result_json, {}), dict)
                and _json(step.result_json, {}).get("mission_status")
                == "WAITING_FOR_MEMBERS"
                for step in steps
            )
            if not opened_collective:
                continue
            if round1_agent_run is None:
                round1_agent_run = candidate
                round1_agent_steps = steps
            if _looks_external(candidate.provider_key, candidate.model_key):
                round1_agent_run = candidate
                round1_agent_steps = steps
                break
        round1_external_ok = bool(
            round1_agent_run
            and _looks_external(
                round1_agent_run.provider_key,
                round1_agent_run.model_key,
            )
        )
        verdicts["real_external_round1_agent"] = _verdict(
            PROVEN if round1_external_ok else NOT_PROVEN,
            "A configured external Agent opened the first collective decision."
            if round1_external_ok
            else "No external AgentRun is proven to have opened round 1.",
            run_id=round1_agent_run.id if round1_agent_run else None,
            provider_key=round1_agent_run.provider_key if round1_agent_run else None,
            model_key=round1_agent_run.model_key if round1_agent_run else None,
        )

        round1_options = [
            item
            for item in (round1_payload.get("candidate_options") or [])
            if isinstance(item, dict) and item.get("proposal_id")
        ]
        best_by_member: dict[str, dict[str, Any]] = {}
        preference_driven_ok = bool(round1_required and round1_options)
        for member_id in sorted(round1_required):
            scored: list[tuple[float, str]] = []
            for option in round1_options:
                fits = option.get("member_fits") or {}
                fit = fits.get(member_id) if isinstance(fits, dict) else None
                if not isinstance(fit, dict):
                    continue
                try:
                    score = float(fit.get("effective_fit"))
                except (TypeError, ValueError):
                    continue
                proposal_id = str(option.get("proposal_id") or "")
                if proposal_id:
                    scored.append((score, proposal_id))
            if not scored:
                preference_driven_ok = False
                best_by_member[member_id] = {
                    "chosen_proposal_id": round1_choices.get(member_id),
                    "best_score": None,
                    "best_proposal_ids": [],
                }
                continue
            best_score = max(score for score, _proposal_id in scored)
            best_ids = sorted(
                proposal_id
                for score, proposal_id in scored
                if abs(score - best_score) <= 1e-9
            )
            chosen = round1_choices.get(member_id)
            preference_driven_ok = preference_driven_ok and chosen in best_ids
            best_by_member[member_id] = {
                "chosen_proposal_id": chosen,
                "best_score": best_score,
                "best_proposal_ids": best_ids,
            }
        preference_driven_ok = (
            preference_driven_ok and len(distinct_round1_choices) >= 2
        )
        verdicts["preference_driven_round1_disagreement"] = _verdict(
            PROVEN if preference_driven_ok else CONTRADICTED,
            "Each relevant member chose a server-grounded maximum-fit option and those optima diverged."
            if preference_driven_ok
            else "Round-1 disagreement is not proven to follow each member's server-computed best fit.",
            members=best_by_member,
        )

        round1_audits = _response_audits(session, round1.id) if round1 else []
        round1_audit_members = {
            str(_after(row).get("member_id") or "") for row in round1_audits
        }
        round1_actors = {str(row.actor_id) for row in round1_audits if row.actor_id}
        round1_auth_ok = bool(
            round1_required
            and round1_required.issubset(round1_audit_members)
            and len(round1_actors) >= 2
        )
        verdicts["round1_authenticated_principals"] = _verdict(
            PROVEN if round1_auth_ok else CONTRADICTED,
            "Every required round-1 answer is bound to authenticated traveler audits."
            if round1_auth_ok
            else "Round-1 disagreement lacks distinct authenticated-principal proof.",
            authenticated_member_ids=sorted(round1_audit_members),
            authenticated_traveler_ids=sorted(round1_actors),
        )

        final_proposal_id = str((r28.get("binding") or {}).get("proposal_id") or "")
        disputed_rows = [
            session.get(ReplanProposal, proposal_id)
            for proposal_id in sorted(distinct_round1_choices)
        ]
        no_old_winner = bool(
            distinct_round1_choices
            and final_proposal_id
            and final_proposal_id not in distinct_round1_choices
            and all(
                row is not None and row.status != "ACCEPTED"
                for row in disputed_rows
            )
        )
        verdicts["round1_proposals_not_laundered"] = _verdict(
            PROVEN if no_old_winner else CONTRADICTED,
            "No disputed round-1 proposal became the accepted result."
            if no_old_winner
            else "A disputed round-1 proposal became accepted or remains unverifiable.",
            final_proposal_id=final_proposal_id,
            disputed=[
                {
                    "proposal_id": proposal_id,
                    "status": row.status if row else None,
                }
                for proposal_id, row in zip(sorted(distinct_round1_choices), disputed_rows)
            ],
        )

        mediator_runs = list(
            session.scalars(
                select(AgentRun)
                .where(AgentRun.mission_id == round2.id)
                .order_by(AgentRun.created_at, AgentRun.id)
            ).all()
        )
        mediator_run = None
        mediator_steps: list[AgentRunStep] = []
        for candidate in mediator_runs:
            steps = _run_steps(session, candidate.id)
            reached_round = False
            for step in steps:
                result = _json(step.result_json, {})
                if (
                    step.tool_name == "request_collective_decision"
                    and isinstance(result, dict)
                    and result.get("mission_status") == "WAITING_FOR_MEMBERS"
                ):
                    reached_round = True
                    break
            if not reached_round:
                continue
            if mediator_run is None:
                mediator_run = candidate
                mediator_steps = steps
            if _looks_external(candidate.provider_key, candidate.model_key):
                mediator_run = candidate
                mediator_steps = steps
                break
        mediator_external_ok = bool(
            mediator_run
            and _looks_external(mediator_run.provider_key, mediator_run.model_key)
        )
        verdicts["real_external_mediator"] = _verdict(
            PROVEN if mediator_external_ok else NOT_PROVEN,
            "A configured external Agent produced the fresh collective round."
            if mediator_external_ok
            else "No external mediator AgentRun is proven on the round-2 mission.",
            run_id=mediator_run.id if mediator_run else None,
            provider_key=mediator_run.provider_key if mediator_run else None,
            model_key=mediator_run.model_key if mediator_run else None,
        )

        executed_mediator_mutations = []
        for step in mediator_steps:
            result = _json(step.result_json, {})
            if (
                step.tool_name in _ACTIVE_REALITY_TOOLS
                and isinstance(result, dict)
                and result.get("executed") is True
            ):
                executed_mediator_mutations.append(
                    {"step_id": step.id, "tool": step.tool_name}
                )
        no_mediator_mutation_ok = mediator_run is not None and not executed_mediator_mutations
        verdicts["mediator_did_not_choose_winner"] = _verdict(
            PROVEN if no_mediator_mutation_ok else CONTRADICTED,
            "Mediator changed no active reality before renewed human consent."
            if no_mediator_mutation_ok
            else "Mediator executed an active-reality mutation before renewed consent.",
            executed_mutations=executed_mediator_mutations,
        )

        round2_payload = _json(round2.clarification_json, {})
        progress = (
            round2_payload.get("mediation_progress")
            if isinstance(round2_payload.get("mediation_progress"), dict)
            else {}
        )
        improved_ids = {
            str(value) for value in (progress.get("improved_option_ids") or [])
        }
        progress_ok = bool(
            round2_payload.get("status") == "RESOLVED"
            and progress.get("allowed") is True
            and final_proposal_id
            and final_proposal_id in improved_ids
            and str(round2_payload.get("selected_proposal_id") or "")
            == final_proposal_id
        )
        verdicts["material_decision_surface_progress"] = _verdict(
            PROVEN if progress_ok else CONTRADICTED,
            "The finally accepted proposal is a machine-recorded improved mediation option."
            if progress_ok
            else "The final choice is not proven to come from a materially improved mediation surface.",
            round2_status=round2_payload.get("status"),
            mediation_progress=progress,
            selected_proposal_id=round2_payload.get("selected_proposal_id"),
            final_proposal_id=final_proposal_id,
        )

        snapshots = (
            mediation_intent.get("member_preference_snapshots")
            if isinstance(mediation_intent, dict)
            and isinstance(mediation_intent.get("member_preference_snapshots"), dict)
            else {}
        )
        current_preferences: dict[str, Any] = {}
        preference_matches = bool(snapshots)
        for member_id, baseline in snapshots.items():
            member = session.get(JourneyMember, str(member_id))
            stored = _json(member.preferences_json, {}) if member else {}
            current = stored.get("preferences", []) if isinstance(stored, dict) else []
            current_preferences[str(member_id)] = current
            preference_matches = preference_matches and current == baseline
        verdicts["member_preferences_unchanged"] = _verdict(
            PROVEN if preference_matches else CONTRADICTED,
            "Journey-scoped member preferences match the mediation-start baseline."
            if preference_matches
            else "Member preference state changed or the mediation baseline is missing.",
            baseline=snapshots,
            current=current_preferences,
        )

        round2_required = {
            str(value) for value in (round2_payload.get("required_member_ids") or [])
        }
        source_required = {
            str(value)
            for value in (
                mediation_intent.get("required_member_ids") or []
                if isinstance(mediation_intent, dict)
                else []
            )
        }
        round2_audits = _response_audits(session, round2.id)
        round2_audit_members = {
            str(_after(row).get("member_id") or "") for row in round2_audits
        }
        round2_actors = {str(row.actor_id) for row in round2_audits if row.actor_id}
        renewed_consent_ok = bool(
            round2_required
            and round2_required == source_required
            and round2_required.issubset(round2_audit_members)
            and len(round2_actors) >= 2
            and round2_payload.get("policy")
            == "POST_DISAGREEMENT_REQUIRES_RENEWED_MEMBER_CONSENT"
        )
        verdicts["renewed_authenticated_consent"] = _verdict(
            PROVEN if renewed_consent_ok else CONTRADICTED,
            "The same relevant member set authenticated again on the improved decision surface."
            if renewed_consent_ok
            else "Round-2 consent is incomplete, unauthenticated, or changed the required member set.",
            required_member_ids=sorted(round2_required),
            source_required_member_ids=sorted(source_required),
            authenticated_member_ids=sorted(round2_audit_members),
            authenticated_traveler_ids=sorted(round2_actors),
            policy=round2_payload.get("policy"),
        )

        lock_released = not _journey_has_unresolved_collective_mediation(
            session, final_run.journey_id
        )
        verdicts["journey_social_authority_lock_released"] = _verdict(
            PROVEN if lock_released else CONTRADICTED,
            "The disagreement lock cleared only after the descendant collective round resolved."
            if lock_released
            else "Journey still has unresolved collective mediation after the claimed closure.",
            journey_id=final_run.journey_id,
        )

    r28_ok = (r28.get("summary") or {}).get("overall") == PROVEN
    verdicts["r28_continuation_invariants"] = _verdict(
        PROVEN if r28_ok else CONTRADICTED,
        "R28 same-run approval, accepted-plan, C4 and execution-truth invariants remain proven."
        if r28_ok
        else "The final R29 run violates an inherited R28 closure invariant.",
        r28_summary=r28.get("summary"),
    )

    counts = {PROVEN: 0, NOT_PROVEN: 0, CONTRADICTED: 0}
    for item in verdicts.values():
        counts[item["status"]] = counts.get(item["status"], 0) + 1
    overall = (
        PROVEN
        if counts[CONTRADICTED] == 0 and counts[NOT_PROVEN] == 0
        else CONTRADICTED
        if counts[CONTRADICTED] > 0
        else NOT_PROVEN
    )
    return {
        "schema_version": "R29_MACHINE_VERDICT_V1",
        "inputs": {"final_agent_run_id": run_id},
        "r28_binding": r28.get("binding"),
        "r28_summary": r28.get("summary"),
        "verdicts": verdicts,
        "summary": {**counts, "overall": overall},
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate the machine-derived Revolution R29 disagreement-mediation verdict."
    )
    parser.add_argument(
        "--run-id",
        required=True,
        help="Final post-consensus approval-suspended/resumed AgentRun id",
    )
    parser.add_argument("--output", help="Optional JSON file path")
    args = parser.parse_args()

    report = build_verdict(args.run_id)
    rendered = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True)
    if args.output:
        path = Path(args.output)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    raise SystemExit(0 if report["summary"]["overall"] == PROVEN else 1)


if __name__ == "__main__":
    main()
