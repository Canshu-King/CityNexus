"""R29 live strike harness; setup reuses the bounded R28 provider-backed fixture."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from run_r28_live import _api_setup, _configure, _wb2api_config_path


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
    return {"status": response.status_code, "payload": response.json(), "setup": setup}


def _run_disagreement_and_mediator(db: str, journey_id: str, mission_id: str) -> dict[str, object]:
    from fastapi.testclient import TestClient
    from sqlalchemy import select
    from app.db.models import JourneyMission
    from app.db.session import SessionLocal
    from app.main import app
    from app.traveler_principal import issue_traveler_token

    client = TestClient(app)
    with SessionLocal() as session:
        mission = session.get(JourneyMission, mission_id)
        if mission is None:
            raise RuntimeError("first mission not found")
        clarification = json.loads(mission.clarification_json or "{}")
    options = clarification.get("candidate_options") or []
    required = clarification.get("required_member_ids") or []
    if len(options) < 2 or len(required) != 2:
        raise RuntimeError("first mission does not contain two options and two members")
    owner_member, admin_member = str(required[0]), str(required[1])
    owner_token = issue_traveler_token(str(_traveler_for_member(owner_member)))
    admin_token = issue_traveler_token(str(_traveler_for_member(admin_member)))
    path = f"/api/v1/journeys/{journey_id}/missions/{mission_id}/collective-clarification"
    first = client.post(
        f"{path}/{owner_member}",
        headers={"Authorization": f"Bearer {owner_token}"},
        json={"clarification_id": clarification["clarification_id"], "proposal_id": options[0]["proposal_id"]},
    )
    if first.status_code >= 400:
        raise RuntimeError(f"owner disagreement response failed: {first.status_code} {first.text}")
    second = client.post(
        f"{path}/{admin_member}",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"clarification_id": clarification["clarification_id"], "proposal_id": options[1]["proposal_id"]},
    )
    if second.status_code >= 400:
        raise RuntimeError(f"admin disagreement response failed: {second.status_code} {second.text}")
    disagreement = second.json()
    child = disagreement.get("child_mission") or {}
    child_id = child.get("id")
    if disagreement.get("status") != "MEDIATION_REQUIRED" or not child_id:
        raise RuntimeError(f"disagreement did not create mediation child: {json.dumps(disagreement)}")
    resumed = client.post(f"/api/v1/journeys/{journey_id}/missions/{child_id}/resume")
    return {
        "db": db,
        "journey_id": journey_id,
        "round1_mission_id": mission_id,
        "round1_status": disagreement.get("status"),
        "mediator_mission_id": child_id,
        "mediator_http_status": resumed.status_code,
        "mediator_payload": resumed.json(),
        "member_choices": [options[0]["proposal_id"], options[1]["proposal_id"]],
    }


def _traveler_for_member(member_id: str) -> str:
    from app.db.models import JourneyMember
    from app.db.session import SessionLocal
    with SessionLocal() as session:
        member = session.get(JourneyMember, member_id)
        if member is None:
            raise RuntimeError(f"member not found: {member_id}")
        return str(member.traveler_id)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-agent", action="store_true")
    parser.add_argument("--full-r29", action="store_true")
    parser.add_argument("--continue-disagreement", nargs=3, metavar=("DB", "JOURNEY_ID", "MISSION_ID"))
    args = parser.parse_args()
    if args.continue_disagreement:
        db, journey_id, mission_id = args.continue_disagreement
        print(json.dumps(_run_disagreement_and_mediator(db, journey_id, mission_id), ensure_ascii=True))
        return 0
    db = _configure()
    try:
        setup = _api_setup(db)
    except Exception as exc:
        print(json.dumps({"status": "SETUP_BLOCKED_BEFORE_AGENT_CALL", "error": str(exc), "db": str(db)}))
        return 2
    if not args.run_agent and not args.full_r29:
        print(json.dumps({"status": "SETUP_READY_NO_AGENT_CALL", **setup}))
        return 0
    try:
        first = _run_first_agent(setup)
        if not args.full_r29:
            print(json.dumps(first, ensure_ascii=True))
            return 0
        payload = first["payload"]
        mission = payload.get("mission") or {}
        result = _run_disagreement_and_mediator(
            str(setup["db"]), str(setup["journey_id"]), str(mission["id"])
        )
        print(json.dumps({"first": first, "r29": result}, ensure_ascii=True))
    except Exception as exc:
        print(json.dumps({"status": "AGENT_CALL_FAILED", "error": str(exc), "setup": setup}))
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
