"""R34 live context-watch closure.

The harness creates one fresh Journey, captures the active strategy, invokes the
server-owned venue watch once, and only opens Hermes when the watch persisted a
qualified material conflict.
"""
from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from run_r28_live import _api_setup, _configure

ROOT = Path(__file__).resolve().parents[1]


def _jsonable(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_jsonable(item) for item in value]
    return str(value)


def _strategy(journey_id: str) -> dict[str, Any]:
    from sqlalchemy import select
    from app.db.models import Activity, Journey, PlanVersion
    from app.db.session import SessionLocal

    with SessionLocal() as session:
        journey = session.get(Journey, journey_id)
        if journey is None or not journey.active_plan_version_id:
            raise RuntimeError("active Journey/plan missing")
        plan = session.get(PlanVersion, journey.active_plan_version_id)
        activities = session.scalars(
            select(Activity)
            .where(Activity.plan_version_id == journey.active_plan_version_id)
            .order_by(Activity.sequence_no)
        ).all()
        return {
            "journey_id": journey_id,
            "plan_id": plan.id if plan else None,
            "plan_status": plan.status if plan else None,
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


def _evidence(journey_id: str) -> dict[str, Any]:
    from sqlalchemy import select
    from app.db.models import Event, WebObservation
    from app.db.session import SessionLocal

    with SessionLocal() as session:
        observations = session.scalars(
            select(WebObservation)
            .where(WebObservation.journey_id == journey_id, WebObservation.provider_key == "truth-mesh")
            .order_by(WebObservation.captured_at)
        ).all()
        events = session.scalars(
            select(Event)
            .where(Event.journey_id == journey_id, Event.provider_key == "truth-mesh")
            .order_by(Event.detected_at)
        ).all()
        return {
            "observations": [
                {
                    "id": row.id,
                    "provider_key": row.provider_key,
                    "source_class": row.source_class,
                    "authority_status": row.authority_status,
                    "captured_at": row.captured_at,
                    "url": row.url,
                    "domain": row.domain,
                    "content_excerpt": row.content_excerpt,
                }
                for row in observations
            ],
            "events": [
                {
                    "id": row.id,
                    "event_type": row.event_type,
                    "provenance": row.provenance,
                    "affected_activity_id": row.affected_activity_id,
                    "detected_at": row.detected_at,
                    "payload": json.loads(row.payload_json or "{}"),
                }
                for row in events
            ],
        }


def _mutation_receipt(journey_id: str) -> list[dict[str, Any]]:
    from sqlalchemy import select
    from app.db.models import AuditLog
    from app.db.session import SessionLocal

    with SessionLocal() as session:
        rows = session.scalars(
            select(AuditLog)
            .where(AuditLog.journey_id == journey_id)
            .order_by(AuditLog.created_at)
        ).all()
        return [
            {"action": row.action, "created_at": row.created_at, "after": json.loads(row.after_json or "{}")} 
            for row in rows
            if row.action == "replan.accepted"
        ]


def run(output: Path) -> dict[str, Any]:
    if output.exists():
        raise RuntimeError(f"R34 output already exists: {output}")
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
    initial = _strategy(journey_id)
    response = client.post(f"/api/v1/journeys/{journey_id}/context-watch")
    try:
        watch = response.json()
    except ValueError:
        watch = {"raw": response.text}
    result: dict[str, Any] = {
        "schema": "citynexus.r34.live-context-watch.v1",
        "status": "BLOCKED",
        "database": str(db),
        "setup": _jsonable(setup),
        "initial_strategy": _jsonable(initial),
        "watch_http_status": response.status_code,
        "watch": _jsonable(watch),
        "evidence": {},
        "agent": None,
        "final_strategy": None,
        "mutation_count": 0,
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "limitations": ["physical travel is not claimed"],
    }
    if response.status_code >= 400:
        result["blocked_reason"] = "context watch endpoint failed"
    elif watch.get("status") == "NO_MATERIAL_CHANGE":
        result["status"] = "NO_MATERIAL_CHANGE"
        result["final_strategy"] = _jsonable(_strategy(journey_id))
        result["evidence"] = _jsonable(_evidence(journey_id))
        result["limitations"].append("no Hermes Agent was started because no qualified conflict was observed")
    elif watch.get("status") in {"UNKNOWN", "PROVIDER_DEGRADED"}:
        result["status"] = "BLOCKED"
        result["blocked_reason"] = "live venue evidence remained unknown or provider-degraded"
        result["final_strategy"] = _jsonable(_strategy(journey_id))
        result["evidence"] = _jsonable(_evidence(journey_id))
        result["limitations"].append("no Hermes Agent was started from uncertain evidence")
    elif watch.get("status") == "MATERIAL_CONFLICT":
        command = (
            "A server-owned Live Context Watch persisted a qualified venue opening-hours conflict for the active Journey. "
            "Inspect the current Journey, exact conflict evidence, standing goals, completed execution, and protected commitments. "
            "Choose your own grounded recovery strategy under current authority; do not invent facts or approvals."
        )
        agent_response = client.post(
            f"/api/v1/journeys/{journey_id}/agent/commands",
            json={"command": command, "requested_autonomy": "EXECUTE_WITHIN_BOUNDS"},
        )
        try:
            agent_body = agent_response.json()
        except ValueError:
            agent_body = {"raw": agent_response.text}
        run_payload = agent_body.get("run") or {}
        run_id = run_payload.get("run_id") or run_payload.get("id")
        result["status"] = "COMPLETED" if agent_response.status_code < 400 else "AGENT_FAILED"
        result["agent"] = {"status_code": agent_response.status_code, "run_id": run_id, "payload": _jsonable(agent_body)}
        result["final_strategy"] = _jsonable(_strategy(journey_id))
        result["evidence"] = _jsonable(_evidence(journey_id))
        mutations = _mutation_receipt(journey_id)
        result["mutations"] = _jsonable(mutations)
        result["mutation_count"] = len(mutations)
    else:
        result["blocked_reason"] = f"unexpected context watch status: {watch.get('status')}"
        result["final_strategy"] = _jsonable(_strategy(journey_id))
        result["evidence"] = _jsonable(_evidence(journey_id))
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
        "watch_status": result.get("watch", {}).get("status"),
        "agent_run_id": (result.get("agent") or {}).get("run_id"),
        "mutation_count": result.get("mutation_count"),
    }, ensure_ascii=False))
    return 0 if result.get("status") in {"NO_MATERIAL_CHANGE", "COMPLETED"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
