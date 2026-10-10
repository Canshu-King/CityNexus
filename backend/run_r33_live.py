"""R33-1 open-world Journey adaptation live closure."""
from __future__ import annotations

import argparse
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from run_r28_live import BACKEND, _api_setup, _configure


def _jsonable(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_jsonable(item) for item in value]
    return str(value)


def _initial_strategy(journey_id: str) -> dict[str, Any]:
    from sqlalchemy import select
    from app.db.models import Activity, Journey, PlanVersion
    from app.db.session import SessionLocal

    with SessionLocal() as session:
        journey = session.get(Journey, journey_id)
        if journey is None or not journey.active_plan_version_id:
            raise RuntimeError("initial Journey or active plan missing")
        plan = session.get(PlanVersion, journey.active_plan_version_id)
        activities = session.scalars(
            select(Activity)
            .where(Activity.plan_version_id == journey.active_plan_version_id)
            .order_by(Activity.sequence_no)
        ).all()
        if plan is None or not activities:
            raise RuntimeError("initial active plan has no activities")
        return {
            "journey_id": journey_id,
            "plan_id": plan.id,
            "plan_status": plan.status,
            "strategy": [
                {
                    "sequence_no": item.sequence_no,
                    "id": item.id,
                    "place_id": item.place_id,
                    "title": item.title,
                    "activity_type": item.activity_type,
                    "start_at": item.start_at,
                    "end_at": item.end_at,
                    "status": item.status,
                    "locked": item.locked,
                }
                for item in activities
            ],
        }


def _final_strategy(journey_id: str) -> dict[str, Any]:
    from sqlalchemy import select
    from app.db.models import Activity, Journey, PlanVersion
    from app.db.session import SessionLocal

    with SessionLocal() as session:
        journey = session.get(Journey, journey_id)
        if journey is None:
            return {}
        plan = session.get(PlanVersion, journey.active_plan_version_id) if journey.active_plan_version_id else None
        activities = session.scalars(
            select(Activity)
            .where(Activity.plan_version_id == journey.active_plan_version_id)
            .order_by(Activity.sequence_no)
        ).all() if journey.active_plan_version_id else []
        return {
            "journey_id": journey_id,
            "plan_id": plan.id if plan else None,
            "plan_status": plan.status if plan else None,
            "journey_status": journey.status,
            "strategy": [
                {
                    "sequence_no": item.sequence_no,
                    "id": item.id,
                    "place_id": item.place_id,
                    "title": item.title,
                    "activity_type": item.activity_type,
                    "start_at": item.start_at,
                    "end_at": item.end_at,
                    "status": item.status,
                    "locked": item.locked,
                }
                for item in activities
            ],
        }


def _audit_mutations(journey_id: str) -> list[dict[str, Any]]:
    from sqlalchemy import select
    from app.db.models import AuditLog
    from app.db.session import SessionLocal

    with SessionLocal() as session:
        rows = session.scalars(
            select(AuditLog)
            .where(AuditLog.journey_id == journey_id)
            .order_by(AuditLog.created_at)
        ).all()
        out = []
        for row in rows:
            after = json.loads(row.after_json or "{}") if row.after_json else {}
            text = json.dumps(after, ensure_ascii=False)
            if row.action in {"replan.accepted", "agent.run.completed"} or "domain.mutation" in text:
                out.append({"action": row.action, "created_at": row.created_at, "after": after})
        return out


def _provider_event_receipt(journey_id: str, weather: dict[str, Any]) -> dict[str, Any]:
    from sqlalchemy import select
    from app.db.models import Event, ProviderObservation
    from app.db.session import SessionLocal

    with SessionLocal() as session:
        events = session.scalars(
            select(Event)
            .where(Event.journey_id == journey_id, Event.provider_key == "open-meteo")
            .order_by(Event.detected_at)
        ).all()
        observations = session.scalars(
            select(ProviderObservation)
            .where(ProviderObservation.journey_id == journey_id, ProviderObservation.provider_key == "open-meteo")
            .order_by(ProviderObservation.captured_at)
        ).all()
        event_rows = []
        for row in events:
            event_rows.append({
                "id": row.id,
                "event_type": row.event_type,
                "severity": row.severity,
                "provider_key": row.provider_key,
                "provenance": row.provenance,
                "affected_activity_id": row.affected_activity_id,
                "detected_at": row.detected_at,
                "payload": json.loads(row.payload_json or "{}"),
            })
        observation_rows = []
        for row in observations:
            observation_rows.append({
                "id": row.id,
                "provider_key": row.provider_key,
                "observation_type": row.observation_type,
                "state": row.state,
                "provenance": row.provenance,
                "captured_at": row.captured_at,
                "payload": json.loads(row.payload_json or "{}"),
            })
        return {
            "weather_runtime": weather,
            "provider_events": event_rows,
            "provider_observations": observation_rows,
        }


def run(output: Path) -> dict[str, Any]:
    if output.exists():
        raise RuntimeError(f"R33 output already exists: {output}")
    db = _configure()
    os.environ.update({
        "CITYNEXUS_AI_ENABLED": "false",
        "CITYNEXUS_AI_API_KEY": "",
        "DEEPSEEK_API_KEY": "",
        "CITYNEXUS_HERMES_NATIVE_API_URL": "",
        "CITYNEXUS_HERMES_API_SERVER_KEY": "",
        "CITYNEXUS_LAB_ESTIMATE_AUTHORITY": "false",
    })
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)
    setup = _api_setup(db)
    journey_id = str(setup["journey_id"])
    initial = _initial_strategy(journey_id)
    weather_response = client.post(f"/api/v1/journeys/{journey_id}/weather/refresh")
    weather_body = weather_response.json()
    provider_receipt = _provider_event_receipt(journey_id, weather_body)
    provider_events = provider_receipt["provider_events"]
    provider_observations = provider_receipt["provider_observations"]
    fresh_fact = bool(
        weather_response.status_code == 200
        and weather_body.get("provider") == "open-meteo"
        and weather_body.get("degraded") is False
        and weather_body.get("observation_ids")
        and provider_observations
        and any(row["provenance"] == "PROVIDER_VERIFIED" for row in provider_events)
    )
    if not fresh_fact:
        result = {
            "schema": "citynexus.r33.live-closure.v1",
            "status": "BLOCKED",
            "blocked_reason": "fresh provider-backed weather fact was not persisted with PROVIDER_VERIFIED provenance",
            "database": str(db),
            "setup": _jsonable(setup),
            "initial_strategy": _jsonable(initial),
            "weather": _jsonable(provider_receipt),
            "agent": None,
            "final_strategy": _jsonable(_final_strategy(journey_id)),
            "mutation_count": 0,
            "captured_at": datetime.now(timezone.utc).isoformat(),
        }
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        return result

    command = (
        "Recover the current shared Journey using only server-owned facts and the standing traveler goals. "
        "A fresh provider-backed weather observation has just been captured for the active plan. "
        "Inspect the current Journey, the weather evidence, member preferences, protected commitments, "
        "and grounded options. Choose your own strategy if the new facts make the current strategy unsuitable. "
        "Preserve completed execution and protected commitments. If current server authority permits one "
        "autonomous adaptation, you may execute it; otherwise leave the real human boundary unresolved. "
        "Do not invent facts, approvals, places, or authority."
    )
    agent_response = client.post(
        f"/api/v1/journeys/{journey_id}/agent/commands",
        json={"command": command, "requested_autonomy": "EXECUTE_WITHIN_BOUNDS"},
    )
    agent_body = agent_response.json()
    run_payload = agent_body.get("run") or {}
    run_id = run_payload.get("run_id") or run_payload.get("id")
    mission_id = (agent_body.get("mission") or {}).get("id") or run_payload.get("mission_id")
    final = _final_strategy(journey_id)
    proposals_response = client.get(f"/api/v1/journeys/{journey_id}/replans")
    proposals = proposals_response.json() if proposals_response.status_code == 200 else []
    live_proposals = [item for item in proposals if item.get("source_agent_run_id") == run_id]
    mutations = _audit_mutations(journey_id)
    result = {
        "schema": "citynexus.r33.live-closure.v1",
        "status": "COMPLETED" if agent_response.status_code < 400 else "AGENT_FAILED",
        "database": str(db),
        "setup": _jsonable(setup),
        "initial_strategy": _jsonable(initial),
        "weather": _jsonable(provider_receipt),
        "agent": {
            "status_code": agent_response.status_code,
            "run_id": run_id,
            "mission_id": mission_id,
            "payload": _jsonable(agent_body),
        },
        "public_replans": _jsonable(proposals),
        "live_agent_proposals": _jsonable(live_proposals),
        "final_strategy": _jsonable(final),
        "mutations": _jsonable(mutations),
        "mutation_count": sum(1 for item in mutations if item.get("action") == "replan.accepted"),
        "ui_contract": {
            "source_agent_run_id_projected": any(item.get("source_agent_run_id") == run_id for item in live_proposals),
            "live_agent_origin_testid": "live-agent-origin",
            "live_agent_origin_data_agent_run_id": run_id,
            "live_agent_origin_data_recovery_epoch_id": next((item.get("recovery_epoch_id") for item in live_proposals if item.get("source_agent_run_id") == run_id), None),
        },
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "truth_boundary": "Open-Meteo provider-backed weather ingestion plus WB2api/Hermes Agent runtime; physical travel not claimed.",
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = run(args.output)
    print(json.dumps({
        "output": str(args.output),
        "status": result.get("status"),
        "journey_id": result.get("setup", {}).get("journey_id"),
        "provider_events": len(result.get("weather", {}).get("provider_events", [])),
        "agent_run_id": result.get("agent", {}).get("run_id") if result.get("agent") else None,
        "mutation_count": result.get("mutation_count"),
    }, ensure_ascii=False))
    return 0 if result.get("status") == "COMPLETED" else 2


if __name__ == "__main__":
    raise SystemExit(main())
