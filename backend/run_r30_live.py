"""R30 live consent-epoch shock harness.

This reuses the already-proven R29 social flow, but deliberately stops after
renewed authenticated consent and before that authority is consumed.

The shock is injected through CityNexus's server-owned signal ingestion seam
(set_fixture_state -> refresh_demo_signals), not by editing a candidate plan,
consent JSON, or world-epoch hash. The provider is a deterministic REPLAY
fixture; the external Journey Agents remain real configured runtimes.

R30 truth boundary:
- proves stale social authority against a server-owned provider-replay shock;
- does not claim the shock came from a live public network provider;
- does not claim physical travel.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
from pathlib import Path
from typing import Any

from run_r28_live import BACKEND, ROOT, _api_setup, _configure
from run_r29_live import (
    _approval_id_from_run,
    _owner_member_id,
    _resume_resolved_child_and_approve,
    _signed_member_tokens,
)


def _configure_existing_db(value: str) -> Path:
    _configure()
    db = Path(value).expanduser().resolve()
    if not db.is_file():
        raise RuntimeError(f"R30 strike database was not found: {db}")
    os.environ["CITYNEXUS_DATABASE_URL"] = "sqlite:///" + db.as_posix()
    return db


def _rank_member_choice(options: list[dict[str, Any]], member_id: str) -> str:
    scored: list[tuple[float, str]] = []
    for option in options:
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
        raise RuntimeError(f"no measurable member fit for {member_id}")
    best_score = max(score for score, _proposal_id in scored)
    best_ids = sorted(
        proposal_id
        for score, proposal_id in scored
        if abs(score - best_score) <= 1e-9
    )
    if len(best_ids) != 1:
        raise RuntimeError(
            f"member {member_id} has no unique grounded maximum: {best_ids}"
        )
    return best_ids[0]


def _best_improved_choice(
    options: list[dict[str, Any]],
    improved_ids: list[str],
) -> str:
    rows: list[tuple[float, float, int, str]] = []
    for option in options:
        proposal_id = str(option.get("proposal_id") or "")
        if proposal_id not in improved_ids:
            continue
        fairness = option.get("fairness") or {}
        try:
            minimum_fit = float(fairness.get("minimum_member_fit"))
        except (TypeError, ValueError):
            minimum_fit = -1.0
        try:
            maximum_regret = float(fairness.get("maximum_regret"))
        except (TypeError, ValueError):
            maximum_regret = 1.0
        unacceptable = len(fairness.get("unacceptable_member_ids") or [])
        rows.append((minimum_fit, -maximum_regret, -unacceptable, proposal_id))
    if not rows:
        raise RuntimeError("mediator exposed no improved selectable option")
    rows.sort(reverse=True)
    return rows[0][3]


def _reach_post_consent_interlock(
    *,
    setup: dict[str, Any],
) -> dict[str, Any]:
    """Establish E1/W1 through the normal authenticated product boundary.

    Phase A is deliberately not an Agent-strategy test.  The setup already
    contains a real provider-backed Journey, two grounded proposals, two
    authenticated members with different explicit preferences, a C4 anchor and
    an actionable opportunity event.  This function uses normal CityNexus
    mission/tool/replan/member-response surfaces to establish one durable human
    authority receipt.  The configured external Agent is first invoked only
    after the world shock.
    """

    from fastapi.testclient import TestClient

    from app.agent.mission import create_mission
    from app.db.models import (
        CollectiveAuthorityReceipt,
        Journey,
        JourneyMission,
        ReplanProposal,
    )
    from app.db.session import SessionLocal
    from app.main import app

    client = TestClient(app)
    journey_id = str(setup["journey_id"])
    trigger_event_id = str(setup["opportunity_event_id"])

    # Open the first human decision through the same mission/Gateway surfaces
    # used by the product.  No external model is called here.
    with SessionLocal() as session:
        journey = session.get(Journey, journey_id)
        if journey is None:
            raise RuntimeError("R30 Phase A journey disappeared")
        round1 = create_mission(
            session,
            journey,
            command=(
                "Open the current shared Journey decision for the relevant "
                "members without choosing on their behalf."
            ),
            requested_autonomy="EXECUTE_WITHIN_BOUNDS",
            trigger_event_id=trigger_event_id,
        )
        session.commit()
        round1_id = str(round1.id)

    requested = client.post(
        "/api/v1/agent/tools/v2/request_collective_decision",
        json={
            "request_id": "r30-phase-a-round1-collective",
            "journey_id": journey_id,
            "mission_id": round1_id,
            "trigger_event_id": trigger_event_id,
        },
    )
    if requested.status_code >= 400:
        raise RuntimeError(
            "Phase A round-1 collective decision request failed: "
            f"{requested.status_code} {requested.text}"
        )
    clarification = (requested.json().get("clarification") or {})
    options = [
        item
        for item in clarification.get("candidate_options") or []
        if isinstance(item, dict) and item.get("proposal_id")
    ]
    required = [
        str(item)
        for item in clarification.get("required_member_ids") or []
    ]
    if (
        clarification.get("status") != "WAITING_FOR_MEMBERS"
        or len(options) < 2
        or len(required) != 2
    ):
        raise RuntimeError(
            "Phase A round 1 did not expose the expected grounded human "
            "trade-off surface"
        )

    # These are not model choices.  Each authenticated test principal answers
    # according to its own unique server-grounded maximum.  If the maxima do
    # not differ, this fixture has ceased to prove a real starting trade-off.
    first_choice = _rank_member_choice(options, required[0])
    second_choice = _rank_member_choice(options, required[1])
    if first_choice == second_choice:
        raise RuntimeError(
            "Phase A no longer contains a genuine member-specific trade-off"
        )

    tokens = _signed_member_tokens(required)
    round1_path = (
        f"/api/v1/journeys/{journey_id}/missions/{round1_id}/"
        "collective-clarification"
    )
    first_response = client.post(
        f"{round1_path}/{required[0]}",
        headers={"Authorization": f"Bearer {tokens[required[0]]}"},
        json={
            "clarification_id": clarification["clarification_id"],
            "proposal_id": first_choice,
        },
    )
    if first_response.status_code >= 400:
        raise RuntimeError(
            "Phase A first authenticated response failed: "
            f"{first_response.status_code} {first_response.text}"
        )
    second_response = client.post(
        f"{round1_path}/{required[1]}",
        headers={"Authorization": f"Bearer {tokens[required[1]]}"},
        json={
            "clarification_id": clarification["clarification_id"],
            "proposal_id": second_choice,
        },
    )
    if second_response.status_code >= 400:
        raise RuntimeError(
            "Phase A second authenticated response failed: "
            f"{second_response.status_code} {second_response.text}"
        )
    disagreement = second_response.json()
    mediator = disagreement.get("child_mission") or {}
    mediator_id = str(mediator.get("id") or "")
    if (
        disagreement.get("status") != "MEDIATION_REQUIRED"
        or not mediator_id
    ):
        raise RuntimeError(
            "Phase A authenticated disagreement did not create mediator state"
        )

    # Build a materially improved future through the ordinary server replan
    # product API.  This is explicit fixture setup, not a model fallback and
    # not an imitation of an Agent tool sequence.
    place_roles = setup.get("selected_place_keys") or {}
    compromise_place_ids = sorted(
        str(place_id)
        for place_id, role in place_roles.items()
        if role in {"candidate_garden", "candidate_museum"}
    )
    if len(compromise_place_ids) != 2:
        raise RuntimeError(
            "Phase A setup does not expose the two grounded disputed places"
        )
    improved = client.post(
        f"/api/v1/journeys/{journey_id}/replans",
        headers={"Idempotency-Key": "r30-phase-a-grounded-compromise-001"},
        json={
            "trigger_event_id": trigger_event_id,
            "candidate_count": 1,
            "place_ids": compromise_place_ids,
        },
    )
    if improved.status_code not in {200, 201}:
        raise RuntimeError(
            "Phase A improved future generation failed: "
            f"{improved.status_code} {improved.text}"
        )
    improved_payload = improved.json()
    if not (
        isinstance(improved_payload, dict)
        and improved_payload.get("hard_constraints_passed") is True
        and improved_payload.get("id")
    ):
        raise RuntimeError(
            "Phase A product replan did not create a grounded feasible "
            "improved future"
        )

    renewed_request = client.post(
        "/api/v1/agent/tools/v2/request_collective_decision",
        json={
            "request_id": "r30-phase-a-renewed-collective",
            "journey_id": journey_id,
            "mission_id": mediator_id,
            "trigger_event_id": trigger_event_id,
        },
    )
    if renewed_request.status_code >= 400:
        raise RuntimeError(
            "Phase A renewed collective decision request failed: "
            f"{renewed_request.status_code} {renewed_request.text}"
        )
    round2 = renewed_request.json().get("clarification") or {}
    if round2.get("status") != "WAITING_FOR_MEMBERS":
        raise RuntimeError(
            "Phase A renewed decision did not enter WAITING_FOR_MEMBERS"
        )
    progress = round2.get("mediation_progress") or {}
    improved_ids = [
        str(value)
        for value in progress.get("improved_option_ids") or []
        if value
    ]
    if progress.get("allowed") is not True or not improved_ids:
        raise RuntimeError(
            "Phase A improved future did not pass the server mediation "
            "progress gate"
        )

    round2_required = [
        str(item)
        for item in round2.get("required_member_ids") or []
    ]
    if set(round2_required) != set(required):
        raise RuntimeError(
            "Phase A renewed decision changed the relevant member set"
        )

    renewed_independent_choices = _independent_member_choices(
        round2,
        round2_required,
        allowed_proposal_ids=set(improved_ids),
        phase="pre-shock authenticated authority anchor",
    )
    selected_ids = set(renewed_independent_choices.values())
    if len(selected_ids) != 1:
        raise RuntimeError(
            "Phase A improved surface did not create independent convergence"
        )
    improved_choice = next(iter(selected_ids))

    round2_tokens = _signed_member_tokens(round2_required)
    round2_path = (
        f"/api/v1/journeys/{journey_id}/missions/{mediator_id}/"
        "collective-clarification"
    )
    renewed_responses: list[dict[str, Any]] = []
    for index, member_id in enumerate(round2_required):
        response = client.post(
            f"{round2_path}/{member_id}",
            headers={
                "Authorization": f"Bearer {round2_tokens[member_id]}"
            },
            json={
                "clarification_id": round2["clarification_id"],
                "proposal_id": renewed_independent_choices[member_id],
            },
        )
        if response.status_code >= 400:
            raise RuntimeError(
                f"Phase A renewed consent failed for {member_id}: "
                f"{response.status_code} {response.text}"
            )
        payload = response.json()
        renewed_responses.append(payload)
        if index == 0 and payload.get("status") != "WAITING_FOR_MEMBERS":
            raise RuntimeError(
                "Phase A first renewed response resolved too early"
            )

    resolved = renewed_responses[-1]
    child = resolved.get("child_mission") or {}
    child_id = str(child.get("id") or "")
    authority_receipt_id = str(
        child.get("authority_receipt_id") or ""
    )
    if resolved.get("status") != "RESOLVED" or not child_id:
        raise RuntimeError(
            "Phase A renewed consent did not create a resolved continuation"
        )

    with SessionLocal() as session:
        mediator_row = session.get(JourneyMission, mediator_id)
        if mediator_row is None:
            raise RuntimeError("Phase A mediator mission disappeared")
        stored = json.loads(mediator_row.clarification_json or "{}")
        selected_proposal_id = str(
            stored.get("selected_proposal_id") or ""
        )
        selected_option = next(
            (
                item
                for item in stored.get("candidate_options") or []
                if isinstance(item, dict)
                and str(item.get("proposal_id") or "")
                == selected_proposal_id
            ),
            None,
        )
        selected_plan_id = (
            str(selected_option.get("plan_id") or "")
            if isinstance(selected_option, dict)
            else ""
        )
        proposal = (
            session.get(ReplanProposal, selected_proposal_id)
            if selected_proposal_id
            else None
        )
        decision_epoch = str(stored.get("decision_epoch") or "")
        material_world_epoch = str(
            stored.get("material_world_epoch") or ""
        )
        authority_receipt_id = str(
            stored.get("authority_receipt_id")
            or authority_receipt_id
            or ""
        )
        authority = (
            session.get(
                CollectiveAuthorityReceipt,
                authority_receipt_id,
            )
            if authority_receipt_id
            else None
        )
        if (
            proposal is None
            or proposal.status != "PRESENTED"
            or not selected_plan_id
            or str(proposal.proposed_plan_version_id)
            != selected_plan_id
            or selected_proposal_id != improved_choice
        ):
            raise RuntimeError(
                "Phase A resolved authority lost its exact grounded proposal"
            )
        if (
            authority is None
            or authority.authority_mode
            != "AUTHENTICATED_MEMBER_CONSENT"
            or authority.proposal_id != selected_proposal_id
            or authority.plan_version_id != selected_plan_id
            or authority.decision_epoch != decision_epoch
            or authority.material_world_epoch != material_world_epoch
        ):
            raise RuntimeError(
                "Phase A did not persist the exact authenticated authority "
                "receipt for E1/W1"
            )
        if not decision_epoch or not material_world_epoch:
            raise RuntimeError(
                "Phase A resolved consent did not persist E1/W1"
            )

    return {
        "phase_a_mode": "SERVER_OWNED_AUTHENTICATED_COLLECTIVE_ANCHOR",
        "round1_mission_id": round1_id,
        "round1_required_member_ids": required,
        "round1_choices": {
            required[0]: first_choice,
            required[1]: second_choice,
        },
        "mediator_mission_id": mediator_id,
        "mediator_run_id": None,
        "mediation_progress": progress,
        "renewed_required_member_ids": round2_required,
        "renewed_independent_member_choices": renewed_independent_choices,
        "renewed_responses": renewed_responses,
        "selected_proposal_id": selected_proposal_id,
        "selected_plan_id": selected_plan_id,
        "resolved_child_id": child_id,
        "authority_receipt_id_e1w1": authority_receipt_id,
        "decision_epoch_e1": decision_epoch,
        "material_world_epoch_w1": material_world_epoch,
        "fit_subject_place_ids": list(
            selected_option.get("fit_subject_place_ids") or []
        ),
    }

def _prove_unrelated_observation_control(
    journey_id: str,
    *,
    selected_plan_id: str,
    fit_subject_place_ids: list[str],
) -> dict[str, Any]:
    """Prove ordinary provider churn does not invalidate current consent."""

    from app.agent.signal_pipeline import refresh_demo_signals, set_fixture_state
    from app.collective_mediation import collective_material_world_epoch
    from app.db.models import Journey, PlanVersion
    from app.db.session import SessionLocal
    from app.main import collective_material_world_basis

    with SessionLocal() as session:
        journey = session.get(Journey, journey_id)
        plan = session.get(PlanVersion, selected_plan_id)
        if journey is None or plan is None:
            raise RuntimeError(
                "journey/selected plan disappeared before unrelated control"
            )
        before_basis = collective_material_world_basis(
            session,
            journey,
            plan,
            fit_subject_place_ids=fit_subject_place_ids,
        )
        before_epoch = collective_material_world_epoch(before_basis)

        set_fixture_state(
            session,
            journey,
            state="NORMAL",
            payload={
                "r30_unrelated_observation_control": True,
                "description": (
                    "provider refresh not scoped to the consented candidate"
                ),
            },
        )
        signals = refresh_demo_signals(session, journey)
        session.commit()

    with SessionLocal() as session:
        journey = session.get(Journey, journey_id)
        plan = session.get(PlanVersion, selected_plan_id)
        after_basis = collective_material_world_basis(
            session,
            journey,
            plan,
            fit_subject_place_ids=fit_subject_place_ids,
        )
        after_epoch = collective_material_world_epoch(after_basis)

    if before_epoch != after_epoch:
        raise RuntimeError(
            "unrelated provider observation incorrectly changed the material "
            f"world epoch: {before_epoch} -> {after_epoch}"
        )
    return {
        "unrelated": True,
        "before_epoch": before_epoch,
        "after_epoch": after_epoch,
        "signals": signals.to_dict(),
    }


def _inject_provider_replay_shock(
    journey_id: str,
    *,
    target_place_id: str,
) -> dict[str, Any]:
    """Use the normal server-owned sensing seam; do not write Event rows here."""

    from app.agent.signal_pipeline import refresh_demo_signals, set_fixture_state
    from app.db.models import Journey
    from app.db.session import SessionLocal

    with SessionLocal() as session:
        journey = session.get(Journey, journey_id)
        if journey is None:
            raise RuntimeError("journey disappeared before R30 shock")
        fixture = set_fixture_state(
            session,
            journey,
            state="DISRUPTED",
            payload={
                "r30_post_consent_shock": True,
                "purpose": "CONSENT_WORLD_EPOCH_LIVE_STRIKE",
                "target_place_id": target_place_id,
            },
        )
        signals = refresh_demo_signals(session, journey)
        session.commit()
        return {
            "fixture": {
                "state": fixture.state,
                "revision": fixture.revision,
            },
            "signals": signals.to_dict(),
        }


def _assert_world_stale_at_core(
    *,
    journey_id: str,
    selected_plan_id: str,
    expected_w1: str,
    fit_subject_place_ids: list[str],
) -> dict[str, Any]:
    """Prove the world-epoch layer independently of hard feasibility."""

    from app.collective_mediation import collective_material_world_epoch
    from app.db.models import Journey, PlanVersion
    from app.db.session import SessionLocal
    from app.main import collective_material_world_basis, collective_mutation_gate

    with SessionLocal() as session:
        journey = session.get(Journey, journey_id)
        plan = session.get(PlanVersion, selected_plan_id)
        if journey is None or plan is None:
            raise RuntimeError("journey/selected plan disappeared before stale check")
        basis = collective_material_world_basis(
            session,
            journey,
            plan,
            fit_subject_place_ids=fit_subject_place_ids,
        )
        w2 = collective_material_world_epoch(basis)
        gate = collective_mutation_gate(
            session,
            journey,
            plan,
            hard_feasible_plan_ids={selected_plan_id},
        )
    if expected_w1 == w2:
        raise RuntimeError(
            "server-owned provider shock did not change selected future world epoch"
        )
    if gate.get("code") != "COLLECTIVE_CONSENT_WORLD_EPOCH_STALE":
        raise RuntimeError(
            "core gate did not reject stale world authority: "
            f"{json.dumps(gate, ensure_ascii=True)}"
        )
    return {
        "material_world_epoch_w1": expected_w1,
        "material_world_epoch_w2": w2,
        "core_gate": gate,
    }


def _attempt_old_authority(
    *,
    journey_id: str,
    child_id: str,
    owner_member_id: str,
    selected_proposal_id: str,
) -> dict[str, Any]:
    """Drive the old continuation normally and prove it does not consume E1/W1."""

    from fastapi.testclient import TestClient

    from sqlalchemy import select

    from app.db.models import AuditLog, Journey, ReplanProposal
    from app.db.session import SessionLocal
    from app.main import app

    client = TestClient(app)

    # First spend the old E1/W1 authority through the ordinary public mutation
    # route. This must fail at the same core gate used by production acceptance
    # and must leave a durable collective.mutation.denied audit.
    direct_accept = client.post(
        f"/api/v1/replans/{selected_proposal_id}/accept",
        headers={
            "Idempotency-Key": (
                "r30-stale-consent-" + selected_proposal_id.replace("-", "")[:20]
            )
        },
    )
    direct_accept_payload = (
        direct_accept.json()
        if direct_accept.headers.get("content-type", "").startswith(
            "application/json"
        )
        else {"text": direct_accept.text}
    )
    if direct_accept.status_code != 409:
        raise RuntimeError(
            "old E1/W1 proposal did not fail closed through normal accept route: "
            f"{direct_accept.status_code} "
            f"{json.dumps(direct_accept_payload, ensure_ascii=True)}"
        )

    resumed = client.post(
        f"/api/v1/journeys/{journey_id}/missions/{child_id}/resume"
    )
    resumed_payload = (
        resumed.json()
        if resumed.headers.get("content-type", "").startswith("application/json")
        else {"text": resumed.text}
    )
    run = resumed_payload.get("run") or {}
    approval_id = (
        _approval_id_from_run(run, journey_id)
        if resumed.status_code < 400
        else None
    )
    approval_payload: dict[str, Any] | None = None
    approval_status: int | None = None
    if approval_id:
        owner_token = _signed_member_tokens([owner_member_id])[owner_member_id]
        approval = client.post(
            f"/api/v1/journeys/{journey_id}/agent/approvals/{approval_id}/approve",
            headers={"Authorization": f"Bearer {owner_token}"},
            json={"approval_method": "USER_CONFIRMATION"},
        )
        approval_status = approval.status_code
        approval_payload = (
            approval.json()
            if approval.headers.get("content-type", "").startswith("application/json")
            else {"text": approval.text}
        )

    with SessionLocal() as session:
        journey = session.get(Journey, journey_id)
        proposal = session.get(ReplanProposal, selected_proposal_id)
        denial = session.scalar(
            select(AuditLog)
            .where(
                AuditLog.journey_id == journey_id,
                AuditLog.action == "collective.mutation.denied",
                AuditLog.entity_id == (
                    str(proposal.proposed_plan_version_id) if proposal else ""
                ),
            )
            .order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
        )
        denial_after = (
            json.loads(denial.after_json or "{}") if denial is not None else {}
        )
        state = {
            "active_plan_version_id": journey.active_plan_version_id if journey else None,
            "selected_proposal_status": proposal.status if proposal else None,
            "denial_audit_id": denial.id if denial else None,
            "denial_audit": denial_after,
        }
    if state["selected_proposal_status"] == "ACCEPTED":
        raise RuntimeError("stale E1/W1 authority was incorrectly consumed")
    if state.get("denial_audit", {}).get("code") != (
        "COLLECTIVE_CONSENT_WORLD_EPOCH_STALE"
    ):
        raise RuntimeError(
            "normal stale-authority accept did not persist the expected "
            f"world-epoch denial audit: {json.dumps(state, ensure_ascii=True)}"
        )
    return {
        "direct_accept_status": direct_accept.status_code,
        "direct_accept": direct_accept_payload,
        "resume_status": resumed.status_code,
        "resume": resumed_payload,
        "approval_id": approval_id,
        "approval_status": approval_status,
        "approval": approval_payload,
        "post_attempt_state": state,
    }


def _run_external_recovery(journey_id: str) -> dict[str, Any]:
    """Launch a fresh configured external Agent against the already-ingested shock."""

    from fastapi.testclient import TestClient

    from app.main import app

    client = TestClient(app)
    command = (
        "Inspect the current shared Journey and its unresolved server-owned provider incident. "
        "The members' earlier consent may now be stale. Recover the affected future using current "
        "grounded facts while preserving completed execution and protected commitments. Do not "
        "reuse old member answers as authority. If a material human value choice remains, return "
        "a fresh server-owned collective decision to only the decision-relevant members."
    )
    response = client.post(
        f"/api/v1/journeys/{journey_id}/agent/commands",
        json={
            "command": command,
            "requested_autonomy": "EXECUTE_WITHIN_BOUNDS",
        },
    )
    payload = (
        response.json()
        if response.headers.get("content-type", "").startswith("application/json")
        else {"text": response.text}
    )
    return {"status": response.status_code, "payload": payload}


def _latest_waiting_collective_round(journey_id: str) -> dict[str, Any] | None:
    from sqlalchemy import select

    from app.db.models import JourneyMission
    from app.db.session import SessionLocal

    with SessionLocal() as session:
        rows = session.scalars(
            select(JourneyMission)
            .where(JourneyMission.journey_id == journey_id)
            .order_by(
                JourneyMission.created_at.desc(),
                JourneyMission.id.desc(),
            )
        ).all()
        for row in rows:
            try:
                clarification = json.loads(row.clarification_json or "{}")
            except json.JSONDecodeError:
                continue
            if (
                clarification.get("kind") == "COLLECTIVE_TRADEOFF"
                and clarification.get("status") == "WAITING_FOR_MEMBERS"
            ):
                return {
                    "mission_id": row.id,
                    "clarification": clarification,
                }
    return None


def _journey_owner_member_id(journey_id: str) -> str:
    from sqlalchemy import select

    from app.db.models import JourneyMember
    from app.db.session import SessionLocal

    with SessionLocal() as session:
        rows = list(
            session.scalars(
                select(JourneyMember).where(
                    JourneyMember.journey_id == journey_id,
                    JourneyMember.role == "OWNER",
                    JourneyMember.removed_at.is_(None),
                )
            ).all()
        )
    if len(rows) != 1:
        raise RuntimeError(
            "R30 final approval requires exactly one in-force Journey OWNER: "
            f"{[(row.id, row.role) for row in rows]}"
        )
    return str(rows[0].id)


def _independent_member_choices(
    clarification: dict[str, Any],
    required_member_ids: list[str],
    *,
    allowed_proposal_ids: set[str] | None = None,
    phase: str = "collective round",
) -> dict[str, str]:
    """Derive each test member's choice independently from grounded fit.

    Automated strike code may emulate authenticated principals, but it must
    never manufacture social consensus by choosing one global fairness optimum
    and submitting that answer for everyone. Every relevant member must have
    one unique acceptable grounded maximum on the current decision surface,
    and those independent maxima must converge before automation may close the
    round.

    allowed_proposal_ids lets a mediator narrow the decision surface to
    proposals it has actually improved. The mediator may define that surface;
    it still may not choose on behalf of the people inside it.
    """

    allowed = (
        {str(value) for value in allowed_proposal_ids if value}
        if allowed_proposal_ids is not None
        else None
    )
    options = [
        item
        for item in clarification.get("candidate_options") or []
        if isinstance(item, dict)
        and item.get("proposal_id")
        and item.get("status") == "GROUNDED_FEASIBLE"
        and (
            allowed is None
            or str(item.get("proposal_id") or "") in allowed
        )
    ]
    if not options:
        raise RuntimeError(
            f"{phase} has no grounded feasible options on its allowed surface"
        )

    choices: dict[str, str] = {}
    for member_id in required_member_ids:
        scored: list[tuple[float, str]] = []
        for option in options:
            fits = option.get("member_fits") or {}
            fit = fits.get(member_id) if isinstance(fits, dict) else None
            if not isinstance(fit, dict):
                continue
            fairness = option.get("fairness") or {}
            if member_id in {
                str(value)
                for value in fairness.get("unacceptable_member_ids") or []
            }:
                continue
            try:
                score = float(fit.get("effective_fit"))
            except (TypeError, ValueError):
                continue
            scored.append((score, str(option["proposal_id"])))
        if not scored:
            raise RuntimeError(
                f"{phase} has no acceptable grounded fit for member "
                f"{member_id}"
            )
        best_score = max(score for score, _proposal_id in scored)
        best_ids = sorted(
            proposal_id
            for score, proposal_id in scored
            if abs(score - best_score) <= 1e-9
        )
        if len(best_ids) != 1:
            raise RuntimeError(
                f"{phase} member has no unique grounded maximum; human "
                f"choice remains genuinely open for {member_id}: {best_ids}"
            )
        choices[member_id] = best_ids[0]

    distinct = sorted(set(choices.values()))
    if len(distinct) != 1:
        raise RuntimeError(
            f"{phase} members still prefer different grounded futures; "
            "the harness must not manufacture consensus: "
            f"{choices}"
        )
    return choices

def _close_fresh_collective_round(
    *,
    journey_id: str,
    waiting: dict[str, Any],
) -> dict[str, Any]:
    from fastapi.testclient import TestClient

    from app.main import app

    mission_id = str(waiting.get("mission_id") or "")
    clarification = waiting.get("clarification") or {}
    required = [
        str(value)
        for value in clarification.get("required_member_ids") or []
        if value
    ]
    if not mission_id or not required:
        raise RuntimeError(
            "fresh collective round has no mission or required member scope"
        )
    independent_choices = _independent_member_choices(
        clarification,
        required,
        phase="fresh post-shock recovery round",
    )
    choice = next(iter(set(independent_choices.values())))
    tokens = _signed_member_tokens(required)
    client = TestClient(app)
    path = (
        f"/api/v1/journeys/{journey_id}/missions/{mission_id}/"
        "collective-clarification"
    )
    responses: list[dict[str, Any]] = []
    for index, member_id in enumerate(required):
        response = client.post(
            f"{path}/{member_id}",
            headers={"Authorization": f"Bearer {tokens[member_id]}"},
            json={
                "clarification_id": clarification["clarification_id"],
                "proposal_id": independent_choices[member_id],
            },
        )
        if response.status_code >= 400:
            raise RuntimeError(
                "fresh post-shock consent failed for "
                f"{member_id}: {response.status_code} {response.text}"
            )
        payload = response.json()
        responses.append(payload)
        if index < len(required) - 1:
            if payload.get("status") != "WAITING_FOR_MEMBERS":
                raise RuntimeError(
                    "fresh collective round resolved before every required "
                    "member answered"
                )
            if payload.get("child_mission") is not None:
                raise RuntimeError(
                    "fresh collective round created a continuation child too early"
                )

    resolved = responses[-1]
    child = resolved.get("child_mission") or {}
    child_id = str(child.get("id") or "")
    if resolved.get("status") != "RESOLVED" or not child_id:
        raise RuntimeError(
            "fresh authenticated responses did not resolve the post-shock round"
        )

    owner_member_id = _journey_owner_member_id(journey_id)
    closure = _resume_resolved_child_and_approve(
        client,
        journey_id=journey_id,
        child_id=child_id,
        owner_member_id=owner_member_id,
    )
    return {
        "required_member_ids": required,
        "independent_member_choices": independent_choices,
        "selected_proposal_id": choice,
        "responses": responses,
        "resolved_child_id": child_id,
        **closure,
    }


def _close_unambiguous_recovery(
    *,
    journey_id: str,
    recovery: dict[str, Any],
) -> dict[str, Any] | None:
    from fastapi.testclient import TestClient

    from app.main import app

    payload = recovery.get("payload") or {}
    run = payload.get("run") if isinstance(payload, dict) else None
    if not isinstance(run, dict):
        return None
    run_id = str(run.get("run_id") or "")
    approval_id = _approval_id_from_run(run, journey_id)
    if approval_id:
        owner_member_id = _journey_owner_member_id(journey_id)
        owner_token = _signed_member_tokens([owner_member_id])[
            owner_member_id
        ]
        client = TestClient(app)
        approval = client.post(
            f"/api/v1/journeys/{journey_id}/agent/approvals/"
            f"{approval_id}/approve",
            headers={"Authorization": f"Bearer {owner_token}"},
            json={"approval_method": "USER_CONFIRMATION"},
        )
        if approval.status_code >= 400:
            raise RuntimeError(
                "post-shock unambiguous recovery approval failed: "
                f"{approval.status_code} {approval.text}"
            )
        approval_payload = approval.json()
        final_run_id = str(
            (approval_payload.get("continuation") or {}).get("run_id")
            or run_id
        )
        return {
            "mode": "NO_FRESH_COLLECTIVE_ROUND_APPROVAL",
            "approval_id": approval_id,
            "approval": approval_payload,
            "final_run_id": final_run_id,
        }
    outcome = run.get("outcome")
    if run_id and run.get("status") == "COMPLETED" and isinstance(
        outcome, dict
    ) and outcome.get("status") == "MUTATION_EXECUTED":
        return {
            "mode": "NO_FRESH_COLLECTIVE_ROUND_ALREADY_EXECUTED",
            "final_run_id": run_id,
        }
    return None


def _run_machine_verdict(
    *,
    checkpoint_path: str,
    final_run_id: str | None,
) -> dict[str, Any]:
    verdict_path = (
        ROOT
        / "output"
        / "revolution-r30-live-20261006"
        / "R30_MACHINE_VERDICT.json"
    )
    command = [
        "uv",
        "run",
        "--project",
        ".",
        "python",
        "scripts/r30_machine_verdict.py",
        "--checkpoint",
        str(ROOT / checkpoint_path),
        "--output",
        str(verdict_path),
    ]
    if final_run_id:
        command.extend(["--final-run-id", final_run_id])
    completed = subprocess.run(
        command,
        cwd=BACKEND,
        env=os.environ.copy(),
        capture_output=True,
        text=True,
    )
    parsed = None
    if verdict_path.is_file():
        try:
            parsed = json.loads(verdict_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            parsed = None
    return {
        "exit_code": completed.returncode,
        "path": verdict_path.relative_to(ROOT).as_posix(),
        "summary": (parsed or {}).get("summary"),
        "stdout_tail": completed.stdout[-6000:],
        "stderr_tail": completed.stderr[-6000:],
    }


def _write_checkpoint(result: dict[str, Any]) -> str:
    root = Path(__file__).resolve().parents[1]
    out = root / "output" / "revolution-r30-live-20261006"
    out.mkdir(parents=True, exist_ok=True)
    path = out / "R30_LIVE_CHECKPOINT.json"
    path.write_text(
        json.dumps(result, indent=2, ensure_ascii=False, sort_keys=True),
        encoding="utf-8",
    )
    return path.relative_to(root).as_posix()



def _write_result_markdown(result: dict[str, Any]) -> str:
    """Write the human-readable closeout from machine-derived R30 truth."""

    root = Path(__file__).resolve().parents[1]
    path = root / "REVOLUTION_R30_CONSENT_EPOCH_SHOCK_RECOVERY_RESULT.md"
    verdict = result.get("machine_verdict") or {}
    summary = verdict.get("summary") or {}
    truth = result.get("truth_boundary") or {}
    interlock = result.get("interlock") or {}
    old_attempt = result.get("old_authority_attempt") or {}
    fresh = result.get("fresh_collective_closure")
    unanimous = result.get("unambiguous_recovery_closure")

    authority_mode = (
        "FRESH_AUTHENTICATED_MEMBER_CONVERGENCE"
        if isinstance(fresh, dict)
        else "CURRENT_UNANIMOUS_DOMINANCE"
        if isinstance(unanimous, dict)
        else "UNKNOWN"
    )
    lines = [
        "# Revolution R30 - Consent Epoch Shock Recovery Result",
        "",
        "## Final status",
        "",
        f"- Harness status: {result.get('status')}",
        f"- Machine verdict: {summary.get('overall')}",
        f"- PROVEN: {summary.get('PROVEN', 0)}",
        f"- NOT_PROVEN: {summary.get('NOT_PROVEN', 0)}",
        f"- CONTRADICTED: {summary.get('CONTRADICTED', 0)}",
        f"- Final authority mode: {authority_mode}",
        "",
        "## Evidence",
        "",
        "- output/revolution-r30-live-20261006/R30_LIVE_CHECKPOINT.json",
        "- output/revolution-r30-live-20261006/R30_MACHINE_VERDICT.json",
        "",
        "## Authority chain proven",
        "",
        (
            "- Pre-shock renewed E1/W1 authority was bound to authenticated, "
            "independent relevant-member convergence on one grounded future."
        ),
        (
            "- An unrelated provider observation left the material world epoch "
            "unchanged."
        ),
        (
            "- A server-owned provider-replay closure changed the material "
            "world epoch for the consent-relevant future."
        ),
        (
            "- Old E1/W1 authority failed closed and the selected old proposal "
            "was not accepted."
        ),
        (
            "- Expired authority released the stale selected-plan lock without "
            "transferring value-choice authority to the algorithm."
        ),
        (
            "- Recovery proceeded only through current unanimous dominance or "
            "fresh authenticated independent member authority."
        ),
        (
            "- Final mutation preserved inherited R28 exactly-once approval "
            "and continuation invariants."
        ),
        "",
        "## Bound identifiers",
        "",
        f"- Selected pre-shock proposal: {interlock.get('selected_proposal_id')}",
        f"- Selected pre-shock plan: {interlock.get('selected_plan_id')}",
        f"- E1: {interlock.get('decision_epoch_e1')}",
        f"- W1: {interlock.get('material_world_epoch_w1')}",
        f"- Final AgentRun: {result.get('final_run_id')}",
        "",
        "## Truth boundary",
        "",
        f"- Shock source: {truth.get('shock_source')}",
        f"- External Agent required: {truth.get('external_agent_required')}",
        f"- Physical travel proven: {truth.get('physical_travel_proven')}",
        "",
        (
            "R30 proves consent invalidation and recovery authority against a "
            "server-owned provider-replay shock. It does not claim the shock "
            "came from a live public network provider and does not claim "
            "physical travel."
        ),
        "",
        "## Old-authority refusal",
        "",
        f"- Direct stale accept status: {old_attempt.get('direct_accept_status')}",
        f"- Durable denial audit: {old_attempt.get('denial_audit_id')}",
        "",
        "R30 closes only because the machine verdict is PROVEN.",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")
    return path.relative_to(root).as_posix()

def _run_full() -> dict[str, Any]:
    db = _configure()
    setup = _api_setup(db)
    journey_id = str(setup["journey_id"])
    interlock = _reach_post_consent_interlock(setup=setup)
    owner_member_id = _owner_member_id(
        journey_id,
        list(interlock["renewed_required_member_ids"]),
    )
    fit_subject_place_ids = [
        str(value)
        for value in interlock.get("fit_subject_place_ids") or []
        if value
    ]
    if not fit_subject_place_ids:
        raise RuntimeError(
            "selected renewed-consent option has no decision-relevant Place "
            "for the provider-replay shock"
        )
    unrelated_control = _prove_unrelated_observation_control(
        journey_id,
        selected_plan_id=str(interlock["selected_plan_id"]),
        fit_subject_place_ids=fit_subject_place_ids,
    )
    shock = _inject_provider_replay_shock(
        journey_id,
        target_place_id=fit_subject_place_ids[0],
    )
    stale = _assert_world_stale_at_core(
        journey_id=journey_id,
        selected_plan_id=str(interlock["selected_plan_id"]),
        expected_w1=str(interlock["material_world_epoch_w1"]),
        fit_subject_place_ids=list(interlock["fit_subject_place_ids"]),
    )
    old_attempt = _attempt_old_authority(
        journey_id=journey_id,
        child_id=str(interlock["resolved_child_id"]),
        owner_member_id=owner_member_id,
        selected_proposal_id=str(interlock["selected_proposal_id"]),
    )
    recovery = _run_external_recovery(journey_id)
    waiting = _latest_waiting_collective_round(journey_id)
    fresh_closure = None
    unambiguous_closure = None
    final_run_id = None
    if waiting is not None:
        fresh_closure = _close_fresh_collective_round(
            journey_id=journey_id,
            waiting=waiting,
        )
        final_run_id = str(fresh_closure.get("final_run_id") or "")
    else:
        unambiguous_closure = _close_unambiguous_recovery(
            journey_id=journey_id,
            recovery=recovery,
        )
        final_run_id = str(
            (unambiguous_closure or {}).get("final_run_id") or ""
        )

    status = (
        "R30_FINAL_CANDIDATE_READY"
        if final_run_id
        else "R30_RECOVERY_WAITING_FOR_FRESH_MEMBERS"
        if waiting is not None
        else "R30_RECOVERY_AGENT_RAN"
    )
    result = {
        "status": status,
        "db": str(db),
        "journey_id": journey_id,
        "phase_a_authority_anchor": interlock.get("phase_a_mode"),
        "interlock": interlock,
        "unrelated_observation_control": unrelated_control,
        "shock": shock,
        "stale_authority": stale,
        "old_authority_attempt": old_attempt,
        "external_recovery": recovery,
        "fresh_collective_round": waiting,
        "fresh_collective_closure": fresh_closure,
        "unambiguous_recovery_closure": unambiguous_closure,
        "final_run_id": final_run_id or None,
        "truth_boundary": {
            "shock_source": "SERVER_OWNED_PROVIDER_REPLAY_FIXTURE",
            "external_agent_required": True,
            "physical_travel_proven": False,
        },
    }
    result["checkpoint_path"] = _write_checkpoint(result)
    verdict = _run_machine_verdict(
        checkpoint_path=result["checkpoint_path"],
        final_run_id=final_run_id or None,
    )
    result["machine_verdict"] = verdict
    if (
        verdict.get("exit_code") == 0
        and (verdict.get("summary") or {}).get("overall") == "PROVEN"
    ):
        result["status"] = "R30_PROVEN"
        result["result_path"] = _write_result_markdown(result)
        # Re-write the checkpoint with the final machine status and the
        # generated closeout path for a single self-contained handoff artifact.
        result["checkpoint_path"] = _write_checkpoint(result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--full-r30", action="store_true")
    parser.add_argument(
        "--existing-db",
        help="bind to an existing R30 DB for manual continuation",
    )
    args = parser.parse_args()

    if args.existing_db:
        _configure_existing_db(args.existing_db)

    if not args.full_r30:
        print(
            json.dumps(
                {
                    "status": "R30_HARNESS_READY",
                    "hint": "run with --full-r30",
                },
                ensure_ascii=True,
            )
        )
        return 0
    try:
        result = _run_full()
        print(json.dumps(result, ensure_ascii=True))
        return 0 if result.get("status") == "R30_PROVEN" else 4
    except Exception as exc:
        print(
            json.dumps(
                {
                    "status": "R30_LIVE_CHECKPOINT_FAILED",
                    "error": str(exc),
                },
                ensure_ascii=True,
            )
        )
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
