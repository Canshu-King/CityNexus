"""Observe same-active-plan generic selection while HARD recovery is open."""

from __future__ import annotations

import argparse
import json
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.run_harness import (
    RECOVERY_REPLACEMENT_SCENARIO_ID,
    Harness,
    _git_commit,
    _jsonable,
    _sqlite_logical_snapshot,
)

SCENARIO_ID = "active-same-plan-selection-observation"
FINDING = "ACTIVE_SAME_PLAN_SELECT_IDEMPOTENCY_BYPASSES_REVALIDATION"


def utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def event_snapshot(event_id: str) -> dict[str, Any] | None:
    from app.db.models import Event
    from app.db.session import SessionLocal

    with SessionLocal() as session:
        row = session.get(Event, event_id)
        if row is None:
            return None
        return {
            "id": row.id,
            "status": row.status,
            "resolved_at": row.resolved_at,
            "payload_json": row.payload_json,
        }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence-dir", type=Path, required=True)
    args = parser.parse_args()

    h = Harness(args.evidence_dir, RECOVERY_REPLACEMENT_SCENARIO_ID, None)
    started = utc()
    finding = None
    blocker = None
    result = "PASS"
    observations: dict[str, Any] = {}

    try:
        h.bootstrap()
        ids = h.post("/api/v1/demo/reset")
        journey_id = str(ids["journey_id"])
        h._set_place_accessibility(None)
        plans = h.post(
            f"/api/v1/journeys/{journey_id}/plans/generate",
            {"candidate_count": 1},
        )
        plan_id = str(plans[0]["id"])
        h.post(f"/api/v1/journeys/{journey_id}/plans/{plan_id}/select")
        h.post(f"/api/v1/journeys/{journey_id}/start")
        confirmed = h.post(
            f"/api/v1/journeys/{journey_id}/capabilities/confirm",
            [
                {
                    "code": "STEP_FREE_REQUIRED",
                    "severity": "HARD",
                    "params": {"requirement": "step_free"},
                }
            ],
        )
        recovery = confirmed["recovery"]
        event_id = str(recovery["event_id"])

        journey_before = h.get(f"/api/v1/journeys/{journey_id}")
        plans_before = h._plan_status_snapshot(journey_id)
        experience_before = h.get(f"/api/v1/journeys/{journey_id}/experience")
        event_before = event_snapshot(event_id)

        response = h.client.post(
            f"/api/v1/journeys/{journey_id}/plans/{plan_id}/select"
        )
        body = h.action(
            "POST",
            f"/api/v1/journeys/{journey_id}/plans/{plan_id}/select",
            response,
        )

        journey_after = h.get(f"/api/v1/journeys/{journey_id}")
        plans_after = h._plan_status_snapshot(journey_id)
        experience_after = h.get(f"/api/v1/journeys/{journey_id}/experience")
        event_after = event_snapshot(event_id)
        recovery_open_before = bool(
            experience_before.get("experience_flags", {}).get("recovery_required")
        )
        recovery_open_after = bool(
            experience_after.get("experience_flags", {}).get("recovery_required")
        )
        no_mutation = (
            journey_before == journey_after
            and plans_before == plans_after
            and event_before == event_after
        )
        bypass_observed = bool(
            response.status_code == 200
            and recovery_open_before
            and recovery_open_after
            and no_mutation
        )
        if bypass_observed:
            finding = FINDING
        observations = {
            "same_active_plan_select_status": response.status_code,
            "response": body,
            "hard_recovery_open_before": recovery_open_before,
            "hard_recovery_open_after": recovery_open_after,
            "journey_plans_event_unchanged": no_mutation,
            "feasibility_revalidation_observed": False if bypass_observed else None,
            "finding": finding,
        }
    except Exception as exc:  # noqa: BLE001
        result = "FAIL"
        blocker = {"type": type(exc).__name__, "message": str(exc)}
    finally:
        if h.client is not None:
            h.client.close()

    receipt = {
        "run_id": h.run_id,
        "started_at": started,
        "finished_at": utc(),
        "commit": _git_commit(),
        "scenario_id": SCENARIO_ID,
        "environment_identity": {
            "cwd": str(ROOT),
            "python": sys.version,
            "platform": platform.platform(),
            "mode": "isolated-test",
            "external_actions": False,
        },
        "database_identity": {
            "path": str(h.db_path),
            **_sqlite_logical_snapshot(h.db_path),
            "disposable": True,
        },
        "runtime_provider_identity": {
            "runtime": "CityNexus FastAPI in-process TestClient",
            "accessibility": "SYNTHETIC_HARNESS_FIXTURE",
            "p7": False,
        },
        "inputs": {
            "capability": "STEP_FREE_REQUIRED",
            "severity": "HARD",
            "p7": False,
        },
        "api_tool_actions": h.actions,
        "observations": observations,
        "findings": [finding] if finding else [],
        "result": result,
        "blocker": blocker,
        "provenance": {
            "accessibility": "SYNTHETIC_HARNESS_FIXTURE",
            "live_claim": False,
            "p7": False,
        },
    }
    args.evidence_dir.mkdir(parents=True, exist_ok=True)
    output = args.evidence_dir / "evidence.json"
    output.write_text(
        json.dumps(_jsonable(receipt), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {"result": result, "finding": finding, "evidence": str(output)},
            ensure_ascii=False,
        )
    )
    return 0 if result == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
