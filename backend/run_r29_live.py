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
        "path": str(verdict_path),
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
    first_choice = str(options[0]["proposal_id"])
    second_choice = str(options[1]["proposal_id"])
    if first_choice == second_choice:
        raise RuntimeError("round-1 options are not distinct")

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
    round2_option_ids = {
        str(item.get("proposal_id"))
        for item in (round2.get("candidate_options") or [])
        if isinstance(item, dict) and item.get("proposal_id")
    }
    improved_choice = next(
        (proposal_id for proposal_id in improved_ids if proposal_id in round2_option_ids),
        None,
    )
    if improved_choice is None:
        raise RuntimeError(
            "mediation progress does not point to a selectable renewed option"
        )

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
