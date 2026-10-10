"""R35 bounded open-world Guardian pulse closure."""
from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from run_r28_live import _api_setup, _configure
from run_r34_live import _jsonable, _strategy

ROOT = Path(__file__).resolve().parents[1]


def _rows(journey_id: str) -> dict[str, Any]:
    from sqlalchemy import select
    from app.db.models import AgentRun, AuditLog, Event, GuardianRun, ProviderObservation, WebObservation
    from app.db.session import SessionLocal

    with SessionLocal() as session:
        providers = session.scalars(
            select(ProviderObservation)
            .where(ProviderObservation.journey_id == journey_id)
            .order_by(ProviderObservation.captured_at, ProviderObservation.id)
        ).all()
        web = session.scalars(
            select(WebObservation)
            .where(WebObservation.journey_id == journey_id)
            .order_by(WebObservation.captured_at, WebObservation.id)
        ).all()
        events = session.scalars(
            select(Event)
            .where(Event.journey_id == journey_id)
            .order_by(Event.detected_at, Event.id)
        ).all()
        guardian_runs = session.scalars(
            select(GuardianRun)
            .where(GuardianRun.journey_id == journey_id)
            .order_by(GuardianRun.created_at, GuardianRun.id)
        ).all()
        agent_runs = session.scalars(
            select(AgentRun)
            .where(AgentRun.journey_id == journey_id)
            .order_by(AgentRun.created_at, AgentRun.id)
        ).all()
        mutations = session.scalars(
            select(AuditLog)
            .where(AuditLog.journey_id == journey_id, AuditLog.action == "replan.accepted")
            .order_by(AuditLog.created_at, AuditLog.id)
        ).all()
        return {
            "provider_observations": [
                {
                    "id": row.id,
                    "provider_key": row.provider_key,
                    "observation_type": row.observation_type,
                    "state": row.state,
                    "provenance": row.provenance,
                    "captured_at": row.captured_at,
                    "payload": json.loads(row.payload_json or "{}"),
                }
                for row in providers
            ],
            "venue_observations": [
                {
                    "id": row.id,
                    "provider_key": row.provider_key,
                    "provider_entity": next(
                        (json.loads(row.content_excerpt or "{}").get("provider_entity") for _ in [0]),
                        None,
                    ),
                    "source_class": row.source_class,
                    "authority_status": row.authority_status,
                    "captured_at": row.captured_at,
                    "url": row.url,
                }
                for row in web
            ],
            "events": [
                {
                    "id": row.id,
                    "event_type": row.event_type,
                    "provider_key": row.provider_key,
                    "provenance": row.provenance,
                    "status": row.status,
                    "affected_activity_id": row.affected_activity_id,
                }
                for row in events
            ],
            "guardian_runs": [
                {
                    "id": row.id,
                    "decision": row.decision,
                    "status": row.status,
                    "action_status": row.action_status,
                    "trigger_event_id": row.trigger_event_id,
                    "agent_run_id": row.agent_run_id,
                    "proposal_id": row.proposal_id,
                }
                for row in guardian_runs
            ],
            "agent_runs": [
                {
                    "id": row.id,
                    "status": row.status,
                    "provider_key": row.provider_key,
                    "model_key": row.model_key,
                    "recovery_epoch_id": row.recovery_epoch_id,
                }
                for row in agent_runs
            ],
            "mutation_count": len(mutations),
        }


def run(output: Path) -> dict[str, Any]:
    if output.exists():
        raise RuntimeError(f"R35 output already exists: {output}")
    db = _configure()
    os.environ.update(
        {
            "CITYNEXUS_GUARDIAN_SIGNAL_PROVIDER": "open-meteo",
            "CITYNEXUS_GUARDIAN_AUTORUN": "false",
            "CITYNEXUS_LAB_ESTIMATE_AUTHORITY": "false",
            "CITYNEXUS_AI_ENABLED": "false",
            "CITYNEXUS_AI_API_KEY": "",
            "DEEPSEEK_API_KEY": "",
            "CITYNEXUS_HERMES_NATIVE_API_URL": "",
            "CITYNEXUS_HERMES_API_SERVER_KEY": "",
        }
    )
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)
    setup = _api_setup(db)
    journey_id = str(setup["journey_id"])
    initial = _strategy(journey_id)
    mission_response = client.put(
        f"/api/v1/journeys/{journey_id}/guardian/mission",
        json={
            "command": "持续检查天气、路线和地点开放信息；只有真实影响当前安排时才在权限范围内恢复。",
            "requested_autonomy": "EXECUTE_WITHIN_BOUNDS",
        },
    )
    mission_body = mission_response.json() if mission_response.content else {}
    pulse_response = client.post(f"/api/v1/journeys/{journey_id}/guardian/pulse")
    pulse_body = pulse_response.json() if pulse_response.content else {"raw": pulse_response.text}
    latest_response = client.get(f"/api/v1/journeys/{journey_id}/guardian/pulse/latest")
    latest_body = latest_response.json() if latest_response.content else {}
    rows = _rows(journey_id)
    context = (pulse_body.get("context_watch") or {}) if isinstance(pulse_body, dict) else {}
    signals = (pulse_body.get("signals") or {}) if isinstance(pulse_body, dict) else {}
    if pulse_response.status_code >= 400:
        status = "BLOCKED"
    elif context.get("status") in {"UNKNOWN", "PROVIDER_DEGRADED"} or signals.get("degraded"):
        status = "LIVE_CONTEXT_DEGRADED"
    elif context.get("status") == "MATERIAL_CONFLICT":
        status = "MATERIAL_CONFLICT_HANDOFF" if rows["agent_runs"] else "EXTERNAL_AGENT_REQUIRED"
    else:
        status = "ALL_CLEAR"
    result = {
        "schema": "citynexus.r35.open-world-guardian-pulse.v1",
        "status": status,
        "database": str(db),
        "source_head_before_live": os.popen("git rev-parse HEAD").read().strip(),
        "setup": _jsonable(setup),
        "journey_id": journey_id,
        "initial_strategy": _jsonable(initial),
        "standing_mission": {
            "http_status": mission_response.status_code,
            "id": mission_body.get("id"),
            "requested_autonomy": mission_body.get("requested_autonomy"),
        },
        "pulse": _jsonable(pulse_body),
        "latest_pulse_read": _jsonable(latest_body),
        "persisted": rows,
        "final_strategy": _jsonable(_strategy(journey_id)),
        "mutation_count": rows["mutation_count"],
        "live_surface": {
            "state": (
                "CHECKED_ALL_CLEAR"
                if status == "ALL_CLEAR"
                else "VERIFICATION_INCOMPLETE"
                if status == "LIVE_CONTEXT_DEGRADED"
                else "RECOVERY"
            ),
            "traveller_copy": (
                "刚刚检查了天气、路线和地点开放信息，目前的安排仍然可行。"
                if status == "ALL_CLEAR"
                else "部分实时信息暂时无法确认，因此没有自动修改你的行程。"
                if status == "LIVE_CONTEXT_DEGRADED"
                else "发现真实变化，正在进入恢复流程。"
            ),
        },
        "limitations": ["software/provider execution only; no physical travel claimed"],
        "captured_at": datetime.now(timezone.utc).isoformat(),
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
        "journey_id": result.get("journey_id"),
        "pulse_id": (result.get("pulse") or {}).get("pulse_id"),
        "mutation_count": result.get("mutation_count"),
    }, ensure_ascii=False))
    return 0 if result.get("status") in {"ALL_CLEAR", "MATERIAL_CONFLICT_HANDOFF", "LIVE_CONTEXT_DEGRADED", "EXTERNAL_AGENT_REQUIRED"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
