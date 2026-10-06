from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from sqlalchemy import select  # noqa: E402

from app.db.models import (  # noqa: E402
    ActionApproval,
    Activity,
    AgentPendingAction,
    AgentRun,
    AgentRunStep,
    AuditLog,
    Commitment,
    CollectiveAuthorityReceipt,
    Journey,
    JourneyMission,
    JourneyOutcomeEvent,
    JourneyMember,
    ReplanProposal,
)
from app.db.session import SessionLocal  # noqa: E402
from app.execution.truth import EXECUTION_TRUTH_KINDS  # noqa: E402


PROVEN = "PROVEN"
NOT_PROVEN = "NOT_PROVEN"
CONTRADICTED = "CONTRADICTED"


def _json(value: str | None, fallback: Any) -> Any:
    try:
        return json.loads(value or "")
    except (TypeError, json.JSONDecodeError):
        return fallback


def _dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return parsed.astimezone(timezone.utc)


def _verdict(status: str, reason: str, **facts: Any) -> dict[str, Any]:
    return {"status": status, "reason": reason, "facts": facts}


def _audit_after(row: AuditLog) -> dict[str, Any]:
    value = _json(row.after_json, {})
    return value if isinstance(value, dict) else {}


def _looks_external(provider_key: str, model_key: str) -> bool:
    text = f"{provider_key} {model_key}".lower()
    forbidden = (
        "local-test",
        "deterministic",
        "mock-model",
        "citynexus-local-agent",
        "fake-model",
    )
    return bool(provider_key and model_key) and not any(token in text for token in forbidden)


def build_verdict(run_id: str) -> dict[str, Any]:
    with SessionLocal() as session:
        run = session.get(AgentRun, run_id)
        if run is None:
            raise SystemExit(f"AgentRun {run_id} was not found")
        journey = session.get(Journey, run.journey_id)
        mission = session.get(JourneyMission, run.mission_id)
        if journey is None or mission is None:
            raise SystemExit("AgentRun lineage is missing Journey or JourneyMission")

        steps = session.scalars(
            select(AgentRunStep)
            .where(AgentRunStep.run_id == run.id)
            .order_by(AgentRunStep.sequence_no, AgentRunStep.id)
        ).all()
        pending = session.scalar(
            select(AgentPendingAction)
            .where(AgentPendingAction.run_id == run.id)
            .order_by(AgentPendingAction.created_at.desc(), AgentPendingAction.id.desc())
        )
        approval = session.get(ActionApproval, pending.approval_id) if pending else None
        proposal = (
            session.get(ReplanProposal, approval.target_id)
            if approval is not None and approval.target_type == "ReplanProposal"
            else None
        )

        verdicts: dict[str, dict[str, Any]] = {}

        outcome = _json(run.outcome, run.outcome)
        terminal_ok = (
            run.status == "COMPLETED"
            and run.completed_at is not None
            and isinstance(outcome, dict)
            and outcome.get("status") == "MUTATION_EXECUTED"
        )
        verdicts["agent_run_terminal"] = _verdict(
            PROVEN if terminal_ok else CONTRADICTED,
            "AgentRun completed with a server-owned mutation outcome."
            if terminal_ok
            else "AgentRun is not a completed mutation lineage.",
            run_id=run.id,
            run_status=run.status,
            outcome=outcome,
            completed_at=run.completed_at,
            provider_key=run.provider_key,
            model_key=run.model_key,
        )

        external_ok = _looks_external(run.provider_key, run.model_key)
        verdicts["real_external_agent_runtime"] = _verdict(
            PROVEN if external_ok else NOT_PROVEN,
            "Runtime identifiers do not match local/deterministic controls."
            if external_ok
            else "Runtime identity looks local/test or is incomplete.",
            provider_key=run.provider_key,
            model_key=run.model_key,
        )

        pending_ok = (
            pending is not None
            and pending.status == "RESUMED"
            and pending.resumed_at is not None
            and pending.run_id == run.id
            and pending.mission_id == run.mission_id
        )
        verdicts["durable_continuation"] = _verdict(
            PROVEN if pending_ok else CONTRADICTED,
            "The same AgentRun owns a durable pending action that reached RESUMED."
            if pending_ok
            else "No completed durable pending action is bound to this AgentRun.",
            pending_action_id=pending.id if pending else None,
            pending_status=pending.status if pending else None,
            resumed_at=pending.resumed_at if pending else None,
            tool_name=pending.tool_name if pending else None,
        )

        resume_step = None
        origin_step = session.get(AgentRunStep, pending.originating_step_id) if pending and pending.originating_step_id else None
        if pending and approval:
            for step in steps:
                args = _json(step.arguments_json, {})
                result = _json(step.result_json, {})
                if (
                    step.tool_name == pending.tool_name
                    and str(args.get("approval_id") or "") == approval.id
                    and result.get("executed") is True
                ):
                    resume_step = step
                    break
        same_lineage_ok = bool(
            pending
            and origin_step is not None
            and origin_step.run_id == run.id
            and resume_step is not None
            and resume_step.run_id == run.id
            and resume_step.sequence_no > origin_step.sequence_no
        )
        verdicts["same_run_resume_step"] = _verdict(
            PROVEN if same_lineage_ok else CONTRADICTED,
            "Original gated call and approved mutation are steps on the same AgentRun."
            if same_lineage_ok
            else "The approved mutation is not demonstrably a later step on the same AgentRun.",
            originating_step_id=origin_step.id if origin_step else None,
            originating_sequence=origin_step.sequence_no if origin_step else None,
            resumed_step_id=resume_step.id if resume_step else None,
            resumed_sequence=resume_step.sequence_no if resume_step else None,
            tool_name=pending.tool_name if pending else None,
        )

        if approval is None:
            verdicts["approval_ordering"] = _verdict(
                CONTRADICTED, "No ActionApproval is bound to the continuation."
            )
            verdicts["authenticated_approver"] = _verdict(
                CONTRADICTED, "No ActionApproval exists."
            )
        else:
            created = _dt(approval.created_at)
            approved = _dt(approval.approved_at)
            consumed = _dt(approval.consumed_at)
            ordering_ok = bool(
                approval.status == "CONSUMED"
                and created is not None
                and approved is not None
                and consumed is not None
                and created <= approved <= consumed
            )
            verdicts["approval_ordering"] = _verdict(
                PROVEN if ordering_ok else CONTRADICTED,
                "Approval timestamps are monotonic and the receipt is CONSUMED."
                if ordering_ok
                else "Approval lifecycle ordering or terminal status disagrees with the closure.",
                approval_id=approval.id,
                approval_status=approval.status,
                created_at=approval.created_at,
                approved_at=approval.approved_at,
                consumed_at=approval.consumed_at,
                approved_by=approval.approved_by,
            )

            principal_audit = session.scalar(
                select(AuditLog)
                .where(
                    AuditLog.action == "agent.action_approval.principal_bound",
                    AuditLog.entity_type == "ActionApproval",
                    AuditLog.entity_id == approval.id,
                    AuditLog.actor_type == "AUTHENTICATED_TRAVELER",
                    AuditLog.actor_id == approval.approved_by,
                )
                .order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
            )
            member = (
                session.scalar(
                    select(JourneyMember).where(
                        JourneyMember.journey_id == journey.id,
                        JourneyMember.traveler_id == approval.approved_by,
                    )
                )
                if approval.approved_by
                else None
            )
            auth_ok = bool(
                approval.approved_by
                and principal_audit is not None
                and member is not None
            )
            verdicts["authenticated_approver"] = _verdict(
                PROVEN if auth_ok else CONTRADICTED,
                "Approval is tied to a member identity that passed the authenticated in-force route boundary at approval time."
                if auth_ok
                else "Approval lacks machine-verifiable authenticated-principal binding.",
                approval_id=approval.id,
                approved_by=approval.approved_by,
                member_id=member.id if member else None,
                principal_audit_id=principal_audit.id if principal_audit else None,
                principal_audit=_audit_after(principal_audit) if principal_audit else None,
            )

        proposal_ok = bool(
            proposal is not None
            and proposal.status == "ACCEPTED"
            and approval is not None
            and approval.target_id == proposal.id
        )
        verdicts["selected_proposal_accepted"] = _verdict(
            PROVEN if proposal_ok else CONTRADICTED,
            "The approval target is the accepted ReplanProposal."
            if proposal_ok
            else "The approved target is not an ACCEPTED ReplanProposal.",
            proposal_id=proposal.id if proposal else None,
            proposal_status=proposal.status if proposal else None,
            approval_target_id=approval.target_id if approval else None,
        )

        accept_audit = (
            session.scalar(
                select(AuditLog)
                .where(
                    AuditLog.action == "agent.accept_replan",
                    AuditLog.entity_type == "ReplanProposal",
                    AuditLog.entity_id == proposal.id,
                )
                .order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
            )
            if proposal is not None
            else None
        )
        resume_args = _json(resume_step.arguments_json, {}) if resume_step else {}
        accept_after = _audit_after(accept_audit) if accept_audit else {}
        exact_request_ok = bool(
            resume_step is not None
            and accept_audit is not None
            and str(resume_args.get("request_id") or "")
            and str(resume_args.get("request_id"))
            == str(accept_after.get("request_id") or "")
            and str(resume_args.get("proposal_id") or "")
            == (proposal.id if proposal else "")
            and accept_after.get("status") == "ACCEPTED"
        )
        verdicts["proposal_accept_request"] = _verdict(
            PROVEN if exact_request_ok else CONTRADICTED,
            "The resumed AgentRun request id is the exact request recorded by the acceptance audit."
            if exact_request_ok
            else "The exact resumed request cannot be matched to the proposal acceptance audit.",
            resumed_step_id=resume_step.id if resume_step else None,
            request_id=resume_args.get("request_id") if resume_step else None,
            proposal_id=resume_args.get("proposal_id") if resume_step else None,
            accept_audit_id=accept_audit.id if accept_audit else None,
            accept_audit_request_id=accept_after.get("request_id") if accept_audit else None,
            accept_audit_status=accept_after.get("status") if accept_audit else None,
        )

        active_plan_ok = bool(
            proposal is not None
            and journey.active_plan_version_id == proposal.proposed_plan_version_id
        )
        verdicts["active_plan_transition"] = _verdict(
            PROVEN if active_plan_ok else CONTRADICTED,
            "Journey active plan equals the accepted proposal plan."
            if active_plan_ok
            else "Journey active plan does not equal the accepted proposal plan.",
            journey_active_plan_version_id=journey.active_plan_version_id,
            proposed_plan_version_id=proposal.proposed_plan_version_id if proposal else None,
        )

        collective = None
        if mission.parent_mission_id:
            maybe_parent = session.get(JourneyMission, mission.parent_mission_id)
            payload = _json(maybe_parent.clarification_json, {}) if maybe_parent else {}
            if isinstance(payload, dict) and payload.get("kind") == "COLLECTIVE_TRADEOFF":
                collective = maybe_parent
        if collective is None:
            own_payload = _json(mission.clarification_json, {})
            if isinstance(own_payload, dict) and own_payload.get("kind") == "COLLECTIVE_TRADEOFF":
                collective = mission

        if collective is None:
            # R30 may continue without a fresh member round only when the
            # server-issued durable dominance receipt matches the exact
            # proposal and plan.  An audit line or model claim is not authority.
            dominance_receipt = (
                session.scalar(
                    select(CollectiveAuthorityReceipt)
                    .where(
                        CollectiveAuthorityReceipt.journey_id == journey.id,
                        CollectiveAuthorityReceipt.proposal_id == (proposal.id if proposal else ""),
                        CollectiveAuthorityReceipt.plan_version_id == (
                            proposal.proposed_plan_version_id if proposal else ""
                        ),
                        CollectiveAuthorityReceipt.authority_mode == "UNANIMOUS_DOMINANCE",
                        CollectiveAuthorityReceipt.classification == "UNANIMOUS_DOMINANCE",
                        CollectiveAuthorityReceipt.invalidated_at.is_(None),
                    )
                    .order_by(CollectiveAuthorityReceipt.issued_at.desc(), CollectiveAuthorityReceipt.id.desc())
                )
                if proposal is not None
                else None
            )
            unanimous_no_round = dominance_receipt is not None
            if unanimous_no_round:
                option_rows = session.scalars(
                    select(ReplanProposal).where(
                        ReplanProposal.journey_id == journey.id,
                        ReplanProposal.base_plan_version_id
                        == proposal.base_plan_version_id,
                        ReplanProposal.trigger_event_id
                        == proposal.trigger_event_id,
                        ReplanProposal.id != proposal.id,
                    )
                ).all()
                terminal_options_ok = all(
                    row.status in {"REJECTED", "INVALIDATED", "EXPIRED"}
                    for row in option_rows
                )
                verdicts["authenticated_collective_responses"] = _verdict(
                    PROVEN,
                    "No fresh member round was required: the accepted mutation carries a durable current UNANIMOUS_DOMINANCE classification.",
                    collective_required=False,
                    authority_receipt_id=dominance_receipt.id,
                    classification=dominance_receipt.classification,
                )
                verdicts["non_selected_proposals_rejected"] = _verdict(
                    PROVEN if terminal_options_ok else NOT_PROVEN,
                    "Every other proposal on the accepted base/trigger surface is terminally non-active."
                    if terminal_options_ok
                    else "A non-selected proposal on the accepted base/trigger surface remains actionable.",
                    proposals=[
                        {"proposal_id": row.id, "status": row.status}
                        for row in option_rows
                    ],
                    authority_receipt_id=dominance_receipt.id,
                )
            else:
                verdicts["authenticated_collective_responses"] = _verdict(
                    CONTRADICTED,
                    "No collective parent mission is reachable from the AgentRun mission.",
                )
                verdicts["non_selected_proposals_rejected"] = _verdict(
                    NOT_PROVEN,
                    "No collective option set is reachable.",
                )
        else:
            collective_payload = _json(collective.clarification_json, {})
            required = {str(item) for item in collective_payload.get("required_member_ids") or []}
            responses = collective_payload.get("responses") or {}
            audits = session.scalars(
                select(AuditLog).where(
                    AuditLog.action == "agent.collective_decision.response",
                    AuditLog.entity_type == "JourneyMission",
                    AuditLog.entity_id == collective.id,
                    AuditLog.actor_type == "AUTHENTICATED_TRAVELER",
                )
            ).all()
            audit_by_member: dict[str, AuditLog] = {}
            for audit in audits:
                after = _audit_after(audit)
                member_id = str(after.get("member_id") or "")
                if member_id:
                    audit_by_member[member_id] = audit
            actors = {row.actor_id for row in audits if row.actor_id}
            collective_ok = bool(
                required
                and required.issubset(set(responses))
                and required.issubset(set(audit_by_member))
                and len(actors) >= 2
                and collective_payload.get("status") == "RESOLVED"
                and str(collective_payload.get("selected_proposal_id") or "")
                == (proposal.id if proposal else "")
            )
            verdicts["authenticated_collective_responses"] = _verdict(
                PROVEN if collective_ok else CONTRADICTED,
                "Every required member response has an authenticated traveler audit."
                if collective_ok
                else "Collective response set is incomplete, unauthenticated, or selects another proposal.",
                collective_mission_id=collective.id,
                collective_status=collective_payload.get("status"),
                required_member_ids=sorted(required),
                response_member_ids=sorted(str(key) for key in responses),
                authenticated_member_ids=sorted(audit_by_member),
                authenticated_traveler_ids=sorted(str(actor) for actor in actors),
                selected_proposal_id=collective_payload.get("selected_proposal_id"),
            )

            option_ids = {
                str(item.get("proposal_id"))
                for item in collective_payload.get("candidate_options") or []
                if isinstance(item, dict) and item.get("proposal_id")
            }
            non_selected = sorted(item for item in option_ids if proposal is None or item != proposal.id)
            non_selected_rows = [
                session.get(ReplanProposal, proposal_id) for proposal_id in non_selected
            ]
            rejected_ok = bool(
                non_selected
                and all(
                    row is not None and row.status in {"REJECTED", "INVALIDATED", "EXPIRED"}
                    for row in non_selected_rows
                )
            )
            verdicts["non_selected_proposals_rejected"] = _verdict(
                PROVEN if rejected_ok else CONTRADICTED,
                "Every non-selected collective proposal is terminally non-active."
                if rejected_ok
                else "At least one non-selected collective proposal remains actionable or is missing.",
                proposals=[
                    {
                        "proposal_id": proposal_id,
                        "status": row.status if row is not None else None,
                    }
                    for proposal_id, row in zip(non_selected, non_selected_rows)
                ],
            )

        c4_rows = session.scalars(
            select(Commitment).where(
                Commitment.journey_id == journey.id,
                Commitment.level == "C4_Anchored",
                Commitment.status == "ACTIVE",
            )
        ).all()
        c4_facts = []
        c4_ok = bool(c4_rows)
        for row in c4_rows:
            activity = session.get(Activity, row.activity_id) if row.activity_id else None
            preserved = bool(
                activity is not None
                and activity.plan_version_id == journey.active_plan_version_id
                and activity.status not in {"CANCELLED", "SKIPPED"}
            )
            c4_ok = c4_ok and preserved
            c4_facts.append(
                {
                    "commitment_id": row.id,
                    "activity_id": row.activity_id,
                    "activity_plan_version_id": activity.plan_version_id if activity else None,
                    "activity_status": activity.status if activity else None,
                    "preserved": preserved,
                }
            )
        verdicts["c4_protected_commitments"] = _verdict(
            PROVEN if c4_ok else CONTRADICTED,
            "Active C4 commitments remain anchored on the active plan."
            if c4_ok
            else "No preserved active C4 commitment is proven on the active plan.",
            commitments=c4_facts,
        )

        execution_events = session.scalars(
            select(JourneyOutcomeEvent)
            .where(
                JourneyOutcomeEvent.journey_id == journey.id,
                JourneyOutcomeEvent.event_type.in_(
                    (
                        "ACTIVITY_DEPARTED",
                        "ACTIVITY_ARRIVED",
                        "ACTIVITY_IN_PROGRESS",
                        "ACTIVITY_COMPLETED",
                    )
                ),
            )
            .order_by(JourneyOutcomeEvent.created_at, JourneyOutcomeEvent.id)
        ).all()
        execution_facts = []
        execution_ok = True
        for event in execution_events:
            payload = _json(event.payload_json, {})
            truth = payload.get("execution_truth") if isinstance(payload, dict) else None
            kind = truth.get("kind") if isinstance(truth, dict) else None
            valid = kind in EXECUTION_TRUTH_KINDS
            execution_ok = execution_ok and valid
            execution_facts.append(
                {
                    "event_id": event.id,
                    "event_type": event.event_type,
                    "planned_start_at": event.planned_start_at,
                    "planned_end_at": event.planned_end_at,
                    "occurred_at_actual": event.occurred_at_actual,
                    "execution_truth_kind": kind,
                    "truth_record_present": valid,
                }
            )
        verdicts["execution_truth"] = _verdict(
            PROVEN if execution_ok else CONTRADICTED,
            (
                "All execution-state transitions carry explicit truth labels."
                if execution_events
                else "No execution-state transitions were performed; no physical execution is claimed."
            )
            if execution_ok
            else "At least one execution transition lacks an allowed execution-truth label.",
            events=execution_facts,
        )

        principal_transport_ok = (
            verdicts.get("authenticated_approver", {}).get("status") == PROVEN
            and verdicts.get("authenticated_collective_responses", {}).get("status") == PROVEN
        )
        verdicts["transport_caller_principal_authentication"] = _verdict(
            PROVEN if principal_transport_ok else CONTRADICTED,
            "Both collective responses and the approval are machine-bound to authenticated traveler principals."
            if principal_transport_ok
            else "At least one human transport action lacks authenticated-principal proof.",
            collective_response_status=verdicts.get("authenticated_collective_responses", {}).get("status"),
            approval_status=verdicts.get("authenticated_approver", {}).get("status"),
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
            "schema_version": "R28_MACHINE_VERDICT_V1",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "inputs": {"agent_run_id": run.id},
            "binding": {
                "journey_id": journey.id,
                "mission_id": mission.id,
                "pending_action_id": pending.id if pending else None,
                "approval_id": approval.id if approval else None,
                "proposal_id": proposal.id if proposal else None,
            },
            "steps": [
                {
                    "id": step.id,
                    "sequence_no": step.sequence_no,
                    "tool_name": step.tool_name,
                    "decision": step.decision,
                    "status": step.status,
                    "arguments": _json(step.arguments_json, {}),
                    "result": _json(step.result_json, {}),
                }
                for step in steps
            ],
            "verdicts": verdicts,
            "summary": {**counts, "overall": overall},
        }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate the machine-derived Revolution R28 closure verdict."
    )
    parser.add_argument("--run-id", required=True, help="Final approval-suspended/resumed AgentRun id")
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
