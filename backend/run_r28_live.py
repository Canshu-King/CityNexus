"""R28 live-closure harness.

This operator-side harness creates a fresh product database and stops before
any external Agent call unless all closure preconditions are machine-true.
"""

from __future__ import annotations

import argparse
import json
import os
import secrets
import sqlite3
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
SOURCE_DB = BACKEND / "r27-agent-closure-20261005.sqlite3"
WB2API_CONFIG = Path(r"C:\Users\仓鼠王\WorkBuddy\2026-09-15-15-47-27\wb2api\config.json")


def _configure() -> Path:
    cfg = json.loads(WB2API_CONFIG.read_text(encoding="utf-8"))
    db = BACKEND / f"r28-live-{secrets.token_hex(8)}.sqlite3"
    os.environ.update(
        {
            "CITYNEXUS_DATABASE_URL": "sqlite:///" + db.as_posix(),
            "CITYNEXUS_DEMO_MODE": "false",
            "CITYNEXUS_TRAVELER_AUTH_SECRET": secrets.token_urlsafe(48),
            "CITYNEXUS_LAB_ESTIMATE_AUTHORITY": "false",
            "CITYNEXUS_HERMES_API_URL": "http://127.0.0.1:7863/v1/chat/completions",
            "CITYNEXUS_HERMES_API_KEY": str(cfg["api_key"]),
            "CITYNEXUS_HERMES_MODEL": "cn:glm-5.3-flash",
            "CITYNEXUS_HERMES_MODEL_FALLBACKS": "cn:glm-5.3-flash,cn:deepseek-v4.1-flash",
            "CITYNEXUS_IMPACT_TIMEOUT_SECONDS": "120",
            "CITYNEXUS_HERMES_NATIVE_API_URL": "",
            "CITYNEXUS_HERMES_BINARY": "",
            "CITYNEXUS_GUARDIAN_AUTORUN": "false",
            "CITYNEXUS_IMPACT_PROVIDER": "disabled",
            "CITYNEXUS_REAL_CITY_ENABLED": "false",
            "CITYNEXUS_LIVE_VALHALLA_URL": "https://valhalla1.openstreetmap.de",
        }
    )
    return db


def _copy_catalog(session) -> dict[str, str]:
    from app.db.models import CityService, Place

    source = sqlite3.connect(SOURCE_DB)
    source.row_factory = sqlite3.Row
    selected = {
        "real-place-22cf72809897ff4c7f312fcf": "current_garden",
        "real-place-b47a20314c81d5a81381d4a4": "c4_craft",
        "real-place-ebd30de67691cab346be66ec": "candidate_garden",
        "real-place-8c09b32224152e3e1ae12843": "candidate_museum",
    }
    try:
        columns = {column.name for column in Place.__table__.columns}
        rows = source.execute(
            "SELECT * FROM places WHERE id IN (?,?,?,?)", tuple(selected)
        ).fetchall()
        if len(rows) != len(selected):
            raise RuntimeError(f"captured provider world is incomplete: {len(rows)} place rows")
        session.execute(Place.__table__.insert(), [
            {key: row[key] for key in row.keys() if key in columns} for row in rows
        ])
        service_columns = {column.name for column in CityService.__table__.columns}
        services = source.execute(
            "SELECT * FROM city_services WHERE place_id IN (?,?,?,?)", tuple(selected)
        ).fetchall()
        if services:
            session.execute(CityService.__table__.insert(), [
                {key: row[key] for key in row.keys() if key in service_columns} for row in services
            ])
        session.flush()
    finally:
        source.close()
    return selected


def _api_setup(db: Path) -> dict[str, object]:
    from fastapi.testclient import TestClient
    from sqlalchemy import select

    from app.db.models import Activity, Commitment, Event, Journey
    from app.db.session import SessionLocal
    from app.main import app

    client = TestClient(app)
    owner = client.post(
        "/api/v1/travelers",
        json={"display_name": "R28 owner", "email": None, "locale": "en-GB", "timezone": "Asia/Tokyo"},
    )
    owner.raise_for_status()
    owner_id = owner.json()["id"]
    admin = client.post(
        "/api/v1/travelers",
        json={"display_name": "R28 admin", "email": None, "locale": "en-GB", "timezone": "Asia/Tokyo"},
    )
    admin.raise_for_status()
    admin_id = admin.json()["id"]
    journey = client.post(
        "/api/v1/journeys",
        json={
            "traveler_id": owner_id,
            "title": "R28 fresh authenticated collective continuity",
            "city_code": "NARA",
            "timezone": "Asia/Tokyo",
            "start_at": "2026-10-08T09:00:00+09:00",
            "end_at": "2026-10-08T18:00:00+09:00",
            "budget": {"amount_minor": 100000, "currency": "JPY"},
            "planning_mode": "balanced",
            "party_size": 2,
        },
    )
    journey.raise_for_status()
    journey_id = journey.json()["id"]
    member = client.post(
        f"/api/v1/journeys/{journey_id}/members",
        json={"traveler_id": admin_id, "role": "ADMIN", "invited_by": owner_id},
    )
    member.raise_for_status()
    admin_member_id = member.json()["id"]
    members = client.get(f"/api/v1/journeys/{journey_id}/members")
    members.raise_for_status()
    member_rows = members.json()
    owner_member_id = next(row["id"] for row in member_rows if row["role"] == "OWNER")
    for member_id, preference in (
        (owner_member_id, {"category": "interest", "key": "garden", "value": True, "weight": 1.0}),
        (admin_member_id, {"category": "interest", "key": "museum", "value": True, "weight": 1.0}),
    ):
        response = client.put(
            f"/api/v1/journeys/{journey_id}/members/{member_id}/preferences",
            json={"preferences": [preference]},
        )
        response.raise_for_status()

    with SessionLocal() as session:
        selected = _copy_catalog(session)
        session.commit()

    current_plan = client.post(
        f"/api/v1/journeys/{journey_id}/plans/generate",
        json={"candidate_count": 1, "place_ids": [
            "real-place-22cf72809897ff4c7f312fcf",
            "real-place-b47a20314c81d5a81381d4a4",
        ]},
    )
    if current_plan.status_code not in {200, 201}:
        raise RuntimeError(f"initial plan generation failed: {current_plan.status_code} {current_plan.text}")
    plan_rows = current_plan.json()
    if isinstance(plan_rows, dict):
        plan_rows = plan_rows.get("plans") or plan_rows.get("top_k") or []
    if not plan_rows:
        raise RuntimeError(f"initial plan generation returned no plans: {current_plan.text}")
    plan_id = plan_rows[0]["id"]
    chosen = client.post(f"/api/v1/journeys/{journey_id}/plans/{plan_id}/select")
    chosen.raise_for_status()
    started = client.post(f"/api/v1/journeys/{journey_id}/start")
    started.raise_for_status()

    with SessionLocal() as session:
        journey_row = session.get(Journey, journey_id)
        activities = session.scalars(
            select(Activity).where(Activity.plan_version_id == plan_id).order_by(Activity.sequence_no)
        ).all()
        if len(activities) < 2:
            raise RuntimeError(f"active plan has no protected successor: {len(activities)} activities")
        current_activity = activities[0]
        anchor = activities[-1]
        anchor.activity_type = "C4"
        anchor.locked = True
        anchor.start_at = "2026-10-08T15:00:00+09:00"
        anchor.end_at = "2026-10-08T16:00:00+09:00"
        anchor.metadata_json = json.dumps({**json.loads(anchor.metadata_json or "{}"), "r28_c4_anchor": True})
        now = datetime.now(timezone.utc).isoformat()
        session.add(Commitment(
            id=str(uuid4()), journey_id=journey_id, activity_id=anchor.id,
            kind="APPOINTMENT", level="C4_Anchored", status="ACTIVE",
            monetary_value_minor=0, monetary_value_status="KNOWN", currency="JPY",
            external_ref="R28-C4-ANCHOR", policy_json=json.dumps({
                "semantic_key": anchor.place_id, "scheduled_start_at": anchor.start_at,
                "source": "R28_OPERATOR_SETUP_PROVIDER_BACKED",
            }), created_at=now, updated_at=now,
        ))
        session.flush()
        journey_row.current_activity_id = current_activity.id
        journey_row.updated_at = now
        session.commit()
        current_activity_id = current_activity.id
        anchor_id = anchor.id

    for action in ("depart", "arrive"):
        response = client.post(f"/api/v1/journeys/{journey_id}/activities/{current_activity_id}/{action}")
        response.raise_for_status()

    twin = client.post(
        "/api/v1/agent/tools/v2/inspect_twin",
        json={"request_id": "r28-setup-opportunity", "journey_id": journey_id},
    )
    twin.raise_for_status()
    twin_payload = twin.json()
    event = twin_payload.get("event") or {}
    event_id = event.get("id") or twin_payload.get("event_id")
    if not event_id:
        with SessionLocal() as session:
            event_id = session.scalar(
                select(Event.id).where(
                    Event.journey_id == journey_id,
                    Event.event_type == "OPPORTUNITY_WINDOW",
                    Event.status == "DETECTED",
                ).order_by(Event.detected_at.desc())
            )
    if not event_id:
        raise RuntimeError(f"setup did not produce a system opportunity event: {twin.text}")

    proposal_items = []
    for index, place_id in enumerate((
        "real-place-ebd30de67691cab346be66ec",
        "real-place-8c09b32224152e3e1ae12843",
    ), start=1):
        proposals = client.post(
            f"/api/v1/journeys/{journey_id}/replans",
            json={"trigger_event_id": event_id, "candidate_count": 1, "place_ids": [place_id]},
            headers={"Idempotency-Key": f"r28-setup-replan-{index:03d}"},
        )
        if proposals.status_code not in {200, 201}:
            raise RuntimeError(f"setup replan generation failed: {proposals.status_code} {proposals.text}")
        payload = proposals.json()
        if isinstance(payload, dict) and payload.get("hard_constraints_passed"):
            proposal_items.append(payload)
    if len(proposal_items) < 2:
        raise RuntimeError(f"setup produced fewer than two grounded proposals: {json.dumps(proposal_items, ensure_ascii=True)}")
    if not all(item.get("hard_constraints_passed") for item in proposal_items[:2]):
        raise RuntimeError(f"setup proposals are not hard-feasible: {json.dumps(proposal_items, ensure_ascii=True)}")
    fingerprints = {tuple(item.get("diff", {}).get("added", [])) for item in proposal_items[:2]}
    if len(fingerprints) < 2:
        raise RuntimeError("setup proposals are not materially distinct")
    return {
        "db": str(db), "journey_id": journey_id, "owner_id": owner_id, "admin_id": admin_id,
        "owner_member_id": owner_member_id, "admin_member_id": admin_member_id,
        "active_plan_id": plan_id, "current_activity_id": current_activity_id, "c4_activity_id": anchor_id,
        "opportunity_event_id": event_id, "proposal_count": len(proposal_items),
        "proposal_fingerprints": len(fingerprints), "selected_place_keys": selected,
        "estimate_authority": os.environ["CITYNEXUS_LAB_ESTIMATE_AUTHORITY"],
        "mobility_provider": os.environ["CITYNEXUS_LIVE_VALHALLA_URL"],
    }


def _run_agent_closure(result: dict[str, object]) -> dict[str, object]:
    """Run the real model only after the setup receipt has passed."""
    from fastapi.testclient import TestClient
    from sqlalchemy import select

    from app.db.models import ActionApproval, Activity, AgentRun, Journey, JourneyMission, PlanVersion
    from app.db.session import SessionLocal
    from app.main import app
    from app.traveler_principal import issue_traveler_token

    client = TestClient(app)
    journey_id = str(result["journey_id"])
    command = (
        "Use the current shared Journey well. Inspect each member separately and respect the server's "
        "collective mediation and authority boundaries. If the current real opportunity presents "
        "grounded choices with a material human value trade-off, return the decision to the relevant "
        "members instead of choosing for them. Use only server facts, and do not invent facts or social authority."
    )
    first = client.post(
        f"/api/v1/journeys/{journey_id}/agent/commands",
        json={"command": command, "requested_autonomy": "EXECUTE_WITHIN_BOUNDS"},
    )
    first.raise_for_status()
    first_payload = first.json()
    first_run = first_payload.get("run") or {}
    first_mission_id = str((first_payload.get("mission") or {}).get("id") or first_run.get("mission_id"))
    if not first_mission_id:
        raise RuntimeError(f"real Agent did not persist a mission: {first.text}")

    with SessionLocal() as session:
        mission = session.get(JourneyMission, first_mission_id)
        if mission is None:
            raise RuntimeError("first Agent mission disappeared from durable state")
        clarification = json.loads(mission.clarification_json or "{}")
    if clarification.get("status") != "WAITING_FOR_MEMBERS":
        return {"status": "AGENT_DID_NOT_REACH_COLLECTIVE_WAIT", "first": first_payload}
    options = clarification.get("candidate_options") or []
    if len(options) < 2:
        raise RuntimeError("Agent reached member wait without two server-derived options")
    selected_proposal = str(options[0]["proposal_id"])
    owner_token = issue_traveler_token(str(result["owner_id"]))
    admin_token = issue_traveler_token(str(result["admin_id"]))
    response_results = []
    for member_id, token in (
        (str(result["owner_member_id"]), owner_token),
        (str(result["admin_member_id"]), admin_token),
    ):
        response = client.post(
            f"/api/v1/journeys/{journey_id}/missions/{first_mission_id}/collective-clarification/{member_id}",
            headers={"Authorization": f"Bearer {token}"},
            json={"clarification_id": clarification["clarification_id"], "proposal_id": selected_proposal},
        )
        response.raise_for_status()
        response_results.append(response.json())
    child = response_results[-1].get("child_mission")
    if not child:
        raise RuntimeError("aligned authenticated responses did not create a child mission")
    child_id = str(child["id"])
    resumed = client.post(f"/api/v1/journeys/{journey_id}/missions/{child_id}/resume")
    resumed.raise_for_status()
    resumed_payload = resumed.json()
    approval_id = None
    resumed_run = resumed_payload.get("run") or {}
    for step in resumed_run.get("tool_steps") or []:
        result_payload = step.get("result") or {}
        if result_payload.get("approval_id"):
            approval_id = result_payload["approval_id"]
    if approval_id is None:
        with SessionLocal() as session:
            approval_id = session.scalar(
                select(ActionApproval.id).where(
                    ActionApproval.journey_id == journey_id,
                    ActionApproval.status == "PENDING",
                ).order_by(ActionApproval.created_at.desc())
            )
    approval_result = None
    if approval_id:
        approval = client.post(
            f"/api/v1/journeys/{journey_id}/agent/approvals/{approval_id}/approve",
            headers={"Authorization": f"Bearer {owner_token}"},
            json={"approval_method": "USER_CONFIRMATION"},
        )
        approval.raise_for_status()
        approval_result = approval.json()
    with SessionLocal() as session:
        journey = session.get(Journey, journey_id)
        active_id = journey.active_plan_version_id if journey else None
        activities = session.scalars(
            select(Activity).where(Activity.plan_version_id == active_id).order_by(Activity.sequence_no)
        ).all() if active_id else []
        activity_ids = [item.id for item in activities]
        current_id = journey.current_activity_id if journey else None
    # State-machine execution is deliberately labelled simulated by the product.
    for activity_id in activity_ids:
        with SessionLocal() as session:
            row = session.get(Activity, activity_id)
            status = row.status if row else None
        actions = {
            # Plan activation marks the first/current activity ACTIVE.  The
            # authoritative execution graph permits ACTIVE -> EN_ROUTE;
            # treating it as already complete skips the real state machine
            # and makes the next activity look like the current one.
            "ACTIVE": ("depart", "arrive", "begin", "complete"),
            "PLANNED": ("depart", "arrive", "begin", "complete"),
            "DEPARTED": ("arrive", "begin", "complete"),
            "ARRIVED": ("begin", "complete"),
            "IN_PROGRESS": ("complete",),
        }.get(status, ())
        for action in actions:
            response = client.post(f"/api/v1/journeys/{journey_id}/activities/{activity_id}/{action}")
            if response.status_code >= 400:
                raise RuntimeError(f"execution transition {activity_id}/{action}: {response.status_code} {response.text}")
    final_run_id = str((approval_result or {}).get("continuation", {}).get("run_id") or resumed_run.get("run_id") or first_run.get("run_id"))
    verdict_path = ROOT / "output" / "revolution-r28-live-20261005" / "R28_MACHINE_VERDICT.json"
    verdict_path.parent.mkdir(parents=True, exist_ok=True)
    verdict = subprocess.run(
        ["uv", "run", "--project", ".", "python", "scripts/r28_machine_verdict.py", "--run-id", final_run_id, "--output", str(verdict_path)],
        cwd=BACKEND, env=os.environ.copy(), capture_output=True, text=True,
    )
    return {
        "status": "AGENT_CLOSURE_ATTEMPTED",
        "first": first_payload,
        "responses": response_results,
        "resumed": resumed_payload,
        "approval": approval_result,
        "final_run_id": final_run_id,
        "verdict_exit": verdict.returncode,
        "verdict_stdout": verdict.stdout[-4000:],
        "verdict_stderr": verdict.stderr[-4000:],
        "verdict_path": str(verdict_path),
        "execution_truth": "SIMULATED_STATE_TRANSITION; PHYSICAL_EXECUTION_NOT_PROVEN",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-agent", action="store_true")
    args = parser.parse_args()
    db = _configure()
    try:
        result = _api_setup(db)
    except Exception as exc:  # setup gate must identify the exact pre-Agent boundary
        print(json.dumps({"status": "SETUP_BLOCKED_BEFORE_AGENT_CALL", "error": str(exc), "db": str(db)}, ensure_ascii=True))
        return 2
    if not args.run_agent:
        print(json.dumps({"status": "SETUP_READY_NO_AGENT_CALL", **result}, ensure_ascii=True))
        return 0
    try:
        print(json.dumps(_run_agent_closure(result), ensure_ascii=True))
    except Exception as exc:  # keep exact runtime boundary without relabelling it as success
        print(json.dumps({"status": "AGENT_CLOSURE_BLOCKED", "error": str(exc), "setup": result}, ensure_ascii=True))
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
