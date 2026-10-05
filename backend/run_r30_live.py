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
from pathlib import Path
from typing import Any

from run_r28_live import _api_setup, _configure
from run_r29_live import (
    _approval_id_from_run,
    _first_mission_id,
    _owner_member_id,
    _run_first_agent,
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
    journey_id: str,
    round1_mission_id: str,
) -> dict[str, Any]:
    """Run R29 social causality, but stop before the resolved child is resumed."""

    from fastapi.testclient import TestClient

    from app.db.models import JourneyMission, ReplanProposal
    from app.db.session import SessionLocal
    from app.main import app

    client = TestClient(app)
    with SessionLocal() as session:
        round1 = session.get(JourneyMission, round1_mission_id)
        if round1 is None:
            raise RuntimeError("round-1 mission not found")
        clarification = json.loads(round1.clarification_json or "{}")

    options = [
        item
        for item in (clarification.get("candidate_options") or [])
        if isinstance(item, dict) and item.get("proposal_id")
    ]
    required = [str(item) for item in clarification.get("required_member_ids") or []]
    if clarification.get("status") != "WAITING_FOR_MEMBERS":
        raise RuntimeError(
            "round-1 mission is not waiting for members: "
            f"{clarification.get('status')}"
        )
    if len(options) < 2 or len(required) != 2:
        raise RuntimeError(
            f"R30 needs two relevant members and >=2 options; "
            f"required={required} options={len(options)}"
        )

    first_choice = _rank_member_choice(options, required[0])
    second_choice = _rank_member_choice(options, required[1])
    if first_choice == second_choice:
        raise RuntimeError(
            "R30 setup did not reproduce genuine preference-driven disagreement"
        )

    tokens = _signed_member_tokens(required)
    path = (
        f"/api/v1/journeys/{journey_id}/missions/{round1_mission_id}/"
        "collective-clarification"
    )
    first_response = client.post(
        f"{path}/{required[0]}",
        headers={"Authorization": f"Bearer {tokens[required[0]]}"},
        json={
            "clarification_id": clarification["clarification_id"],
            "proposal_id": first_choice,
        },
    )
    if first_response.status_code >= 400:
        raise RuntimeError(
            f"first disagreement response failed: "
            f"{first_response.status_code} {first_response.text}"
        )
    second_response = client.post(
        f"{path}/{required[1]}",
        headers={"Authorization": f"Bearer {tokens[required[1]]}"},
        json={
            "clarification_id": clarification["clarification_id"],
            "proposal_id": second_choice,
        },
    )
    if second_response.status_code >= 400:
        raise RuntimeError(
            f"second disagreement response failed: "
            f"{second_response.status_code} {second_response.text}"
        )
    disagreement = second_response.json()
    mediator = disagreement.get("child_mission") or {}
    mediator_id = str(mediator.get("id") or "")
    if disagreement.get("status") != "MEDIATION_REQUIRED" or not mediator_id:
        raise RuntimeError("genuine disagreement did not produce mediator child")

    mediator_resume = client.post(
        f"/api/v1/journeys/{journey_id}/missions/{mediator_id}/resume"
    )
    if mediator_resume.status_code >= 400:
        raise RuntimeError(
            f"mediator resume failed: "
            f"{mediator_resume.status_code} {mediator_resume.text}"
        )
    mediator_run = mediator_resume.json().get("run") or {}

    with SessionLocal() as session:
        mediator_row = session.get(JourneyMission, mediator_id)
        if mediator_row is None:
            raise RuntimeError("mediator mission disappeared")
        round2 = json.loads(mediator_row.clarification_json or "{}")

    if round2.get("status") != "WAITING_FOR_MEMBERS":
        raise RuntimeError(
            "external mediator did not open renewed member round: "
            f"{round2.get('status')}"
        )
    progress = round2.get("mediation_progress") or {}
    improved_ids = [
        str(value) for value in progress.get("improved_option_ids") or [] if value
    ]
    if progress.get("allowed") is not True or not improved_ids:
        raise RuntimeError("mediator did not prove material decision-surface progress")

    round2_required = [str(item) for item in round2.get("required_member_ids") or []]
    if set(round2_required) != set(required):
        raise RuntimeError(
            f"R29/R30 renewed member set drifted: {required} -> {round2_required}"
        )
    round2_options = [
        item
        for item in round2.get("candidate_options") or []
        if isinstance(item, dict) and item.get("proposal_id")
    ]
    improved_choice = _best_improved_choice(round2_options, improved_ids)

    round2_tokens = _signed_member_tokens(round2_required)
    round2_path = (
        f"/api/v1/journeys/{journey_id}/missions/{mediator_id}/"
        "collective-clarification"
    )
    renewed_responses: list[dict[str, Any]] = []
    for index, member_id in enumerate(round2_required):
        response = client.post(
            f"{round2_path}/{member_id}",
            headers={"Authorization": f"Bearer {round2_tokens[member_id]}"},
            json={
                "clarification_id": round2["clarification_id"],
                "proposal_id": improved_choice,
            },
        )
        if response.status_code >= 400:
            raise RuntimeError(
                f"renewed consent failed for {member_id}: "
                f"{response.status_code} {response.text}"
            )
        payload = response.json()
        renewed_responses.append(payload)
        if index == 0 and payload.get("status") != "WAITING_FOR_MEMBERS":
            raise RuntimeError("first renewed response incorrectly resolved the round")

    resolved = renewed_responses[-1]
    child = resolved.get("child_mission") or {}
    child_id = str(child.get("id") or "")
    if resolved.get("status") != "RESOLVED" or not child_id:
        raise RuntimeError("renewed consent did not create a resolved continuation child")

    with SessionLocal() as session:
        mediator_row = session.get(JourneyMission, mediator_id)
        stored = json.loads(mediator_row.clarification_json or "{}")
        selected_proposal_id = str(stored.get("selected_proposal_id") or "")
        selected_option = next(
            (
                item
                for item in stored.get("candidate_options") or []
                if isinstance(item, dict)
                and str(item.get("proposal_id") or "") == selected_proposal_id
            ),
            None,
        )
        if not selected_proposal_id or not isinstance(selected_option, dict):
            raise RuntimeError("resolved round lost its selected server-owned option")
        selected_plan_id = str(selected_option.get("plan_id") or "")
        proposal = session.get(ReplanProposal, selected_proposal_id)
        if (
            proposal is None
            or proposal.status != "PRESENTED"
            or not selected_plan_id
            or str(proposal.proposed_plan_version_id) != selected_plan_id
        ):
            raise RuntimeError("R30 interlock is not a pending selected proposal")
        decision_epoch = str(stored.get("decision_epoch") or "")
        material_world_epoch = str(stored.get("material_world_epoch") or "")
        if not decision_epoch or not material_world_epoch:
            raise RuntimeError(
                "R30 resolved consent did not persist both semantic and world epochs"
            )

    return {
        "round1_mission_id": round1_mission_id,
        "round1_required_member_ids": required,
        "round1_choices": {
            required[0]: first_choice,
            required[1]: second_choice,
        },
        "mediator_mission_id": mediator_id,
        "mediator_run_id": mediator_run.get("run_id"),
        "mediation_progress": progress,
        "renewed_required_member_ids": round2_required,
        "renewed_responses": renewed_responses,
        "selected_proposal_id": selected_proposal_id,
        "selected_plan_id": selected_plan_id,
        "resolved_child_id": child_id,
        "decision_epoch_e1": decision_epoch,
        "material_world_epoch_w1": material_world_epoch,
        "fit_subject_place_ids": list(
            selected_option.get("fit_subject_place_ids") or []
        ),
    }


def _inject_provider_replay_shock(journey_id: str) -> dict[str, Any]:
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

    from app.db.models import Journey, ReplanProposal
    from app.db.session import SessionLocal
    from app.main import app

    client = TestClient(app)
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
        state = {
            "active_plan_version_id": journey.active_plan_version_id if journey else None,
            "selected_proposal_status": proposal.status if proposal else None,
        }
    if state["selected_proposal_status"] == "ACCEPTED":
        raise RuntimeError("stale E1/W1 authority was incorrectly consumed")
    return {
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


def _run_full() -> dict[str, Any]:
    db = _configure()
    setup = _api_setup(db)
    first = _run_first_agent(setup)
    if int(first["status"]) >= 400:
        raise RuntimeError(
            f"first external Agent failed: {first['status']} "
            f"{json.dumps(first['payload'], ensure_ascii=True)}"
        )
    journey_id = str(setup["journey_id"])
    interlock = _reach_post_consent_interlock(
        journey_id=journey_id,
        round1_mission_id=_first_mission_id(first),
    )
    owner_member_id = _owner_member_id(
        journey_id,
        list(interlock["renewed_required_member_ids"]),
    )
    shock = _inject_provider_replay_shock(journey_id)
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
    status = (
        "R30_RECOVERY_WAITING_FOR_FRESH_MEMBERS"
        if waiting is not None
        else "R30_RECOVERY_AGENT_RAN"
    )
    result = {
        "status": status,
        "db": str(db),
        "journey_id": journey_id,
        "first_agent_run": first,
        "interlock": interlock,
        "shock": shock,
        "stale_authority": stale,
        "old_authority_attempt": old_attempt,
        "external_recovery": recovery,
        "fresh_collective_round": waiting,
        "truth_boundary": {
            "shock_source": "SERVER_OWNED_PROVIDER_REPLAY_FIXTURE",
            "external_agent_required": True,
            "physical_travel_proven": False,
        },
    }
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
        # This harness intentionally stops at the post-shock recovery boundary.
        # Machine-PROVEN closure still requires fresh authority (when needed),
        # exactly-once final acceptance, and the R30 verifier.
        return 0
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
