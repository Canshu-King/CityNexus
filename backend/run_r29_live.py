"""R29 live disagreement strike harness.

The harness owns only setup and authenticated human response transport. The
external Agent must discover the trade-off, create mediation progress, and
drive both Agent turns through normal CityNexus tools. No compromise proposal
id or tool sequence is handed to the model.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
from pathlib import Path
from typing import Any

from run_r28_live import BACKEND, ROOT, _api_setup, _configure


def _configure_existing_db(value: str) -> Path:
    """Configure provider/auth environment, then bind this process to an existing strike DB."""
    # _configure is intentionally called before importing app modules. It sets
    # the working external-provider/auth environment but does not create the DB.
    _configure()
    db = Path(value).expanduser().resolve()
    if not db.is_file():
        raise RuntimeError(f"R29 strike database was not found: {db}")
    os.environ["CITYNEXUS_DATABASE_URL"] = "sqlite:///" + db.as_posix()
    return db


def _run_first_agent(setup: dict[str, object]) -> dict[str, object]:
    from fastapi.testclient import TestClient

    from app.main import app

    client = TestClient(app)
    journey_id = str(setup["journey_id"])
    command = (
        "Use the current shared Journey well. Inspect each member separately and respect the "
        "server's collective mediation and authority boundaries. If grounded choices create a "
        "material human value trade-off, return the decision to the relevant members instead of "
        "choosing for them. Use only server facts, and do not invent facts or social authority."
    )
    response = client.post(
        f"/api/v1/journeys/{journey_id}/agent/commands",
        json={"command": command, "requested_autonomy": "EXECUTE_WITHIN_BOUNDS"},
    )
    payload = response.json()
    return {
        "status": response.status_code,
        "payload": payload,
        "setup": setup,
    }


def _traveler_for_member(member_id: str) -> str:
    from app.db.models import JourneyMember
    from app.db.session import SessionLocal

    with SessionLocal() as session:
        member = session.get(JourneyMember, member_id)
        if member is None:
            raise RuntimeError(f"member not found: {member_id}")
        return str(member.traveler_id)


def _signed_member_tokens(member_ids: list[str]) -> dict[str, str]:
    from app.traveler_principal import issue_traveler_token

    return {
        member_id: issue_traveler_token(_traveler_for_member(member_id))
        for member_id in member_ids
    }


def _owner_member_id(journey_id: str, required_member_ids: list[str]) -> str:
    from sqlalchemy import select

    from app.db.models import JourneyMember
    from app.db.session import SessionLocal

    with SessionLocal() as session:
        rows = list(
            session.scalars(
                select(JourneyMember).where(
                    JourneyMember.journey_id == journey_id,
                    JourneyMember.id.in_(required_member_ids),
                )
            ).all()
        )
    owners = [row.id for row in rows if row.role == "OWNER"]
    if len(owners) != 1:
        raise RuntimeError(
            "renewed-consent member set does not contain exactly one OWNER: "
            f"{[(row.id, row.role) for row in rows]}"
        )
    return str(owners[0])


def _approval_id_from_run(run_payload: dict[str, Any], journey_id: str) -> str | None:
    from sqlalchemy import select

    from app.db.models import ActionApproval
    from app.db.session import SessionLocal

    for step in run_payload.get("tool_steps") or []:
        result = step.get("result") or {}
        approval_id = result.get("approval_id")
        if approval_id:
            return str(approval_id)
    with SessionLocal() as session:
        return session.scalar(
            select(ActionApproval.id)
            .where(
                ActionApproval.journey_id == journey_id,
                ActionApproval.status == "PENDING",
            )
            .order_by(ActionApproval.created_at.desc(), ActionApproval.id.desc())
        )


def _resume_resolved_child_and_approve(
    client,
    *,
    journey_id: str,
    child_id: str,
    owner_member_id: str,
) -> dict[str, Any]:
    resumed = client.post(
        f"/api/v1/journeys/{journey_id}/missions/{child_id}/resume"
    )
    if resumed.status_code >= 400:
        raise RuntimeError(
            f"resolved child resume failed: {resumed.status_code} {resumed.text}"
        )
    resumed_payload = resumed.json()
    resumed_run = resumed_payload.get("run") or {}
    approval_id = _approval_id_from_run(resumed_run, journey_id)
    if not approval_id:
        raise RuntimeError(
            "resolved child did not reach an approval boundary; "
            f"run={json.dumps(resumed_run, ensure_ascii=True)}"
        )

    owner_token = _signed_member_tokens([owner_member_id])[owner_member_id]
    approval = client.post(
        f"/api/v1/journeys/{journey_id}/agent/approvals/{approval_id}/approve",
        headers={"Authorization": f"Bearer {owner_token}"},
        json={"approval_method": "USER_CONFIRMATION"},
    )
    if approval.status_code >= 400:
        raise RuntimeError(
            f"owner approval failed: {approval.status_code} {approval.text}"
        )
    approval_payload = approval.json()
    final_run_id = str(
        (approval_payload.get("continuation") or {}).get("run_id")
        or resumed_run.get("run_id")
        or ""
    )
    if not final_run_id:
        raise RuntimeError("approval did not expose the continued AgentRun id")
    return {
        "resolved_child_resume": resumed_payload,
        "approval": approval_payload,
        "final_run_id": final_run_id,
    }


def _run_r29_verdict(final_run_id: str) -> dict[str, Any]:
    verdict_path = (
        ROOT
        / "output"
        / "revolution-r29-live-20261005"
        / "R29_MACHINE_VERDICT.json"
    )
    verdict_path.parent.mkdir(parents=True, exist_ok=True)
    verdict = subprocess.run(
        [
            "uv",
            "run",
            "--project",
            ".",
            "python",
            "scripts/r29_machine_verdict.py",
            "--run-id",
            final_run_id,
            "--output",
            str(verdict_path),
        ],
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
        "exit_code": verdict.returncode,
        "path": verdict_path.relative_to(ROOT).as_posix(),
        "summary": (parsed or {}).get("summary"),
        "stdout_tail": verdict.stdout[-6000:],
        "stderr_tail": verdict.stderr[-6000:],
    }


def _run_disagreement_to_closure(
    db: str,
    journey_id: str,
    round1_mission_id: str,
) -> dict[str, object]:
    from fastapi.testclient import TestClient

    from app.db.models import JourneyMission
    from app.db.session import SessionLocal
    from app.main import app

    client = TestClient(app)

    # Round 1: two authenticated humans deliberately choose different options.
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
    required = [str(item) for item in (clarification.get("required_member_ids") or [])]
    if clarification.get("status") != "WAITING_FOR_MEMBERS":
        raise RuntimeError(
            "round-1 mission is not waiting for members: "
            f"{clarification.get('status')}"
        )
    if len(options) < 2 or len(required) != 2:
        raise RuntimeError(
            "round-1 mission must expose at least two options and exactly two "
            f"required members: options={len(options)} required={required}"
        )
    tokens = _signed_member_tokens(required)
    scored_choices: list[str] = []
    for member_id in required:
        scored = []
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
            raise RuntimeError(
                f"round-1 options have no measurable member fit for {member_id}"
            )
        best_score = max(score for score, _proposal_id in scored)
        best_ids = sorted(
            proposal_id
            for score, proposal_id in scored
            if abs(score - best_score) <= 1e-9
        )
        if len(best_ids) != 1:
            raise RuntimeError(
                "provider-backed setup does not prove a unique preference-driven "
                f"choice for member {member_id}; tied best proposals={best_ids}"
            )
        scored_choices.append(best_ids[0])
    first_choice, second_choice = scored_choices
    if first_choice == second_choice:
        raise RuntimeError(
            "provider-backed setup did not produce genuine preference-driven "
            f"disagreement; both members independently prefer {first_choice}"
        )

    round1_path = (
        f"/api/v1/journeys/{journey_id}/missions/{round1_mission_id}/"
        "collective-clarification"
    )
    owner_response = client.post(
        f"{round1_path}/{required[0]}",
        headers={"Authorization": f"Bearer {tokens[required[0]]}"},
        json={
            "clarification_id": clarification["clarification_id"],
            "proposal_id": first_choice,
        },
    )
    if owner_response.status_code >= 400:
        raise RuntimeError(
            f"first disagreement response failed: "
            f"{owner_response.status_code} {owner_response.text}"
        )
    admin_response = client.post(
        f"{round1_path}/{required[1]}",
        headers={"Authorization": f"Bearer {tokens[required[1]]}"},
        json={
            "clarification_id": clarification["clarification_id"],
            "proposal_id": second_choice,
        },
    )
    if admin_response.status_code >= 400:
        raise RuntimeError(
            f"second disagreement response failed: "
            f"{admin_response.status_code} {admin_response.text}"
        )
    disagreement = admin_response.json()
    mediator = disagreement.get("child_mission") or {}
    mediator_id = str(mediator.get("id") or "")
    if disagreement.get("status") != "MEDIATION_REQUIRED" or not mediator_id:
        raise RuntimeError(
            "round-1 disagreement did not create a mediator child: "
            f"{json.dumps(disagreement, ensure_ascii=True)}"
        )

    # The real configured external Agent must create a materially improved
    # decision surface. The harness does not tell it which proposal to build.
    mediator_resume = client.post(
        f"/api/v1/journeys/{journey_id}/missions/{mediator_id}/resume"
    )
    if mediator_resume.status_code >= 400:
        raise RuntimeError(
            f"mediator resume failed: "
            f"{mediator_resume.status_code} {mediator_resume.text}"
        )
    mediator_payload = mediator_resume.json()
    mediator_run = mediator_payload.get("run") or {}

    with SessionLocal() as session:
        mediator_row = session.get(JourneyMission, mediator_id)
        if mediator_row is None:
            raise RuntimeError("mediator mission disappeared")
        round2 = json.loads(mediator_row.clarification_json or "{}")

    if round2.get("status") != "WAITING_FOR_MEMBERS":
        return {
            "status": "MEDIATOR_DID_NOT_OPEN_RENEWED_ROUND",
            "db": db,
            "journey_id": journey_id,
            "round1_mission_id": round1_mission_id,
            "mediator_mission_id": mediator_id,
            "mediator_run": mediator_run,
            "mediator_clarification": round2,
        }

    progress = (
        round2.get("mediation_progress")
        if isinstance(round2.get("mediation_progress"), dict)
        else {}
    )
    improved_ids = [
        str(value) for value in (progress.get("improved_option_ids") or []) if value
    ]
    if progress.get("allowed") is not True or not improved_ids:
        raise RuntimeError(
            "renewed round lacks machine-proven mediation progress: "
            f"{json.dumps(progress, ensure_ascii=True)}"
        )
    round2_required = [
        str(item) for item in (round2.get("required_member_ids") or [])
    ]
    if set(round2_required) != set(required):
        raise RuntimeError(
            "renewed round changed the required member set: "
            f"round1={required} round2={round2_required}"
        )
    round2_options = [
        item
        for item in (round2.get("candidate_options") or [])
        if isinstance(item, dict) and item.get("proposal_id")
    ]
    round2_option_ids = {
        str(item.get("proposal_id")) for item in round2_options
    }
    candidates = []
    for option in round2_options:
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
        unacceptable_count = len(fairness.get("unacceptable_member_ids") or [])
        candidates.append(
            (minimum_fit, -maximum_regret, -unacceptable_count, proposal_id)
        )
    if not candidates or not any(
        proposal_id in round2_option_ids for proposal_id in improved_ids
    ):
        raise RuntimeError(
            "mediation progress does not point to a selectable renewed option"
        )
    candidates.sort(reverse=True)
    improved_choice = candidates[0][3]

    # Round 2: the same relevant principals independently renew consent. The
    # first response must remain WAITING_FOR_MEMBERS; only the second may
    # create the server-resolved child.
    round2_tokens = _signed_member_tokens(round2_required)
    round2_path = (
        f"/api/v1/journeys/{journey_id}/missions/{mediator_id}/"
        "collective-clarification"
    )
    renewed_responses = []
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
                f"renewed consent {member_id} failed: "
                f"{response.status_code} {response.text}"
            )
        payload = response.json()
        renewed_responses.append(payload)
        if index == 0:
            if payload.get("status") != "WAITING_FOR_MEMBERS":
                raise RuntimeError(
                    "first renewed response advanced too far: "
                    f"{json.dumps(payload, ensure_ascii=True)}"
                )
            if payload.get("child_mission") is not None:
                raise RuntimeError(
                    "first renewed response created a child before all members consented"
                )

    resolved = renewed_responses[-1]
    child = resolved.get("child_mission") or {}
    resolved_child_id = str(child.get("id") or "")
    if resolved.get("status") != "RESOLVED" or not resolved_child_id:
        raise RuntimeError(
            "renewed consent did not produce a resolved child: "
            f"{json.dumps(resolved, ensure_ascii=True)}"
        )

    owner_member_id = _owner_member_id(journey_id, round2_required)
    closure = _resume_resolved_child_and_approve(
        client,
        journey_id=journey_id,
        child_id=resolved_child_id,
        owner_member_id=owner_member_id,
    )
    verdict = _run_r29_verdict(str(closure["final_run_id"]))

    return {
        "status": (
            "R29_PROVEN"
            if verdict.get("exit_code") == 0
            and (verdict.get("summary") or {}).get("overall") == "PROVEN"
            else "R29_VERDICT_NOT_PROVEN"
        ),
        "db": db,
        "journey_id": journey_id,
        "round1_mission_id": round1_mission_id,
        "round1_choices": {
            required[0]: first_choice,
            required[1]: second_choice,
        },
        "mediator_mission_id": mediator_id,
        "mediator_run_id": mediator_run.get("run_id"),
        "mediation_progress": progress,
        "improved_choice": improved_choice,
        "round2_required_member_ids": round2_required,
        "round2_responses": renewed_responses,
        "resolved_child_id": resolved_child_id,
        **closure,
        "verdict": verdict,
        "execution_truth": (
            "NO_POST_ACCEPT_EXECUTION_TRANSITION_PERFORMED; "
            "PHYSICAL_EXECUTION_NOT_PROVEN"
        ),
    }


def _write_proven_result(result: dict[str, object]) -> str | None:
    verdict = result.get("verdict") or {}
    summary = verdict.get("summary") if isinstance(verdict, dict) else None
    if result.get("status") != "R29_PROVEN" or not isinstance(summary, dict):
        return None

    path = ROOT / "REVOLUTION_R29_LIVE_DISAGREEMENT_MEDIATION_RESULT.md"
    progress = result.get("mediation_progress") or {}
    progress_policy = (
        progress.get("progress_policy")
        if isinstance(progress, dict)
        else None
    )
    lines = [
        "# Revolution R29 — Live Disagreement Mediation Result",
        "",
        "## Verdict",
        "",
        "**PROVEN** by the generated R29 machine verdict.",
        "",
        "## Causal closure",
        "",
        f"- Round-1 mission: `{result.get('round1_mission_id')}`",
        f"- Mediator mission: `{result.get('mediator_mission_id')}`",
        f"- Real mediator AgentRun: `{result.get('mediator_run_id')}`",
        f"- Improved compromise proposal: `{result.get('improved_choice')}`",
        f"- Resolved child mission: `{result.get('resolved_child_id')}`",
        f"- Final approval/continuation AgentRun: `{result.get('final_run_id')}`",
        f"- Mediation progress policy: `{progress_policy}`",
        f"- Machine verdict: `{verdict.get('path')}`",
        f"- Machine summary: `{json.dumps(summary, sort_keys=True)}`",
        "",
        "The live strike proved a preference-driven first-round disagreement, "
        "a server-owned Journey social-authority lock, an external-Agent "
        "mediation turn that created a materially improved non-regressing "
        "decision surface, renewed consent from the same relevant signed "
        "Journey principals, and the inherited R28 same-run approval "
        "continuation into exactly-once proposal acceptance.",
        "",
        "## Truth boundaries",
        "",
        "- The harness chose each round-1 response from that member's highest "
        "server-computed grounded fit; it did not manufacture disagreement by "
        "proposal array position.",
        "- The improved compromise was chosen only after the external mediator "
        "run, from server-recorded `mediation_progress.improved_option_ids`; "
        "no compromise proposal ID was supplied to the model.",
        "- Authenticated-member proof is proof of distinct signed Journey "
        "principals at the CityNexus boundary. It is not proof that two "
        "physically distinct people operated two separate devices.",
        "- No post-accept physical travel is claimed. Physical execution is "
        "NOT PROVEN unless separately attested.",
        "",
        "## Stop rule",
        "",
        "R29 is closed only for this causal contract. Do not reopen it as "
        "R29.1 merely to accumulate more receipts.",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")
    return str(path)


def _first_mission_id(first: dict[str, object]) -> str:
    payload = first.get("payload") or {}
    if not isinstance(payload, dict):
        raise RuntimeError("first Agent response is not an object")
    mission = payload.get("mission") or {}
    run = payload.get("run") or {}
    mission_id = (
        mission.get("id") if isinstance(mission, dict) else None
    ) or (
        run.get("mission_id") if isinstance(run, dict) else None
    )
    if not mission_id:
        raise RuntimeError(
            "first external Agent call did not expose a persisted mission id"
        )
    return str(mission_id)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-agent", action="store_true")
    parser.add_argument("--full-r29", action="store_true")
    parser.add_argument(
        "--continue-disagreement",
        nargs=3,
        metavar=("DB", "JOURNEY_ID", "MISSION_ID"),
    )
    args = parser.parse_args()

    if args.continue_disagreement:
        db_value, journey_id, mission_id = args.continue_disagreement
        try:
            db = _configure_existing_db(db_value)
            result = _run_disagreement_to_closure(
                str(db),
                journey_id,
                mission_id,
            )
            result_path = _write_proven_result(result)
            if result_path:
                result["result_path"] = result_path
            print(json.dumps(result, ensure_ascii=True))
            return 0 if result.get("status") == "R29_PROVEN" else 4
        except Exception as exc:
            print(
                json.dumps(
                    {
                        "status": "R29_CONTINUATION_FAILED",
                        "error": str(exc),
                        "db": db_value,
                        "journey_id": journey_id,
                        "mission_id": mission_id,
                    },
                    ensure_ascii=True,
                )
            )
            return 3

    db = _configure()
    try:
        setup = _api_setup(db)
    except Exception as exc:
        print(
            json.dumps(
                {
                    "status": "SETUP_BLOCKED_BEFORE_AGENT_CALL",
                    "error": str(exc),
                    "db": str(db),
                },
                ensure_ascii=True,
            )
        )
        return 2

    if not args.run_agent and not args.full_r29:
        print(
            json.dumps(
                {"status": "SETUP_READY_NO_AGENT_CALL", **setup},
                ensure_ascii=True,
            )
        )
        return 0

    try:
        first = _run_first_agent(setup)
        if first["status"] >= 400:
            raise RuntimeError(
                f"first external Agent call failed: {first['status']} "
                f"{json.dumps(first['payload'], ensure_ascii=True)}"
            )
        if not args.full_r29:
            print(json.dumps(first, ensure_ascii=True))
            return 0

        result = _run_disagreement_to_closure(
            str(setup["db"]),
            str(setup["journey_id"]),
            _first_mission_id(first),
        )
        result_path = _write_proven_result(result)
        if result_path:
            result["result_path"] = result_path
        print(
            json.dumps(
                {"first": first, "r29": result},
                ensure_ascii=True,
            )
        )
        return 0 if result.get("status") == "R29_PROVEN" else 4
    except Exception as exc:
        print(
            json.dumps(
                {
                    "status": "R29_LIVE_STRIKE_FAILED",
                    "error": str(exc),
                    "setup": setup,
                },
                ensure_ascii=True,
            )
        )
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
