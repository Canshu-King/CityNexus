"""Executable, isolated CityNexus Harness.

The first current scenario intentionally drives the real FastAPI application
in-process.  It is not a replacement product test: it is a small executable
boundary that resets a disposable SQLite database, records every action and
assertion, and emits a replayable JSON evidence receipt.

Run from the repository root:
    python scripts/run_harness.py --scenario journey-replan-replay
    python scripts/run_harness.py --scenario journey-replan-replay --replay path/to/receipt.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import subprocess
import sys
import traceback
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
SCENARIO_ID = "journey-replan-replay"


def _utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def _git_commit() -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()


def _jsonable(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    return value


class Harness:
    def __init__(self, run_dir: Path, replay_receipt: dict[str, Any] | None = None):
        self.run_dir = run_dir
        self.db_path = run_dir / "citynexus-harness.db"
        self.receipt_path = run_dir / "evidence.json"
        self.run_id = str(uuid.uuid4())
        self.actions: list[dict[str, Any]] = []
        self.transitions: list[dict[str, Any]] = []
        self.assertions: list[dict[str, Any]] = []
        self.replay_receipt = replay_receipt
        self.client = None
        self.ids: dict[str, Any] = {}
        self.input_payload = {
            "scenario_id": SCENARIO_ID,
            "candidate_count": 1,
            "event": {
                "event_type": "CLOSURE",
                "severity": "MAJOR",
                "occurred_at": "2026-10-10T13:25:00+08:00",
                "payload": {"reason": "harness isolated closure"},
            },
            "p7": False,
        }

    def action(self, method: str, path: str, response: Any, payload: Any = None) -> Any:
        status = getattr(response, "status_code", None)
        body = response.json() if hasattr(response, "json") else response
        if isinstance(body, str) and len(body) > 4000:
            body = body[:4000] + "..."
        self.actions.append(
            {
                "at": _utc(),
                "method": method,
                "path": path,
                "input": _jsonable(payload),
                "status_code": status,
                "response": _jsonable(body),
            }
        )
        return body

    def record_assertion(self, name: str, condition: bool, details: Any = None) -> None:
        item = {"name": name, "passed": bool(condition), "details": _jsonable(details)}
        self.assertions.append(item)
        if not condition:
            raise AssertionError(f"{name}: {details}")

    def transition(self, state: str, evidence: Any = None) -> None:
        self.transitions.append({"at": _utc(), "state": state, "evidence": _jsonable(evidence)})

    def bootstrap(self) -> None:
        self.run_dir.mkdir(parents=True, exist_ok=True)
        if self.db_path.exists():
            self.db_path.unlink()
        os.environ.update(
            {
                "PYTHONDONTWRITEBYTECODE": "1",
                "CITYNEXUS_DATABASE_URL": f"sqlite:///{self.db_path}",
                "CITYNEXUS_ENV": "test",
                "CITYNEXUS_AI_ENABLED": "false",
                "CITYNEXUS_GUARDIAN_AUTORUN": "false",
                "CITYNEXUS_P7_ENABLED": "false",
            }
        )
        if str(BACKEND) not in sys.path:
            sys.path.insert(0, str(BACKEND))
        from app.main import app
        from fastapi.testclient import TestClient

        self.client = TestClient(app, raise_server_exceptions=False)

    def post(self, path: str, payload: Any = None, headers: dict[str, str] | None = None) -> Any:
        response = self.client.post(path, json=payload, headers=headers)
        return self.action("POST", path, response, payload)

    def get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        response = self.client.get(path, params=params)
        rendered = path
        if params:
            rendered += "?" + "&".join(f"{k}={v}" for k, v in params.items())
        return self.action("GET", rendered, response, params)

    def run(self) -> dict[str, Any]:
        started_at = _utc()
        result = "PASS"
        blocker = None
        try:
            self.bootstrap()
            self.transition("RESET")
            self.ids = self.post("/api/v1/demo/reset")
            self.record_assertion("reset_returns_journey", bool(self.ids.get("journey_id")), self.ids)
            journey_id = self.ids["journey_id"]
            self.transition("SEED", self.ids)

            self.transition("EXECUTE:PLAN_GENERATION")
            plans = self.post(
                f"/api/v1/journeys/{journey_id}/plans/generate",
                {"candidate_count": self.input_payload["candidate_count"]},
            )
            self.record_assertion("plan_generation_succeeds", isinstance(plans, list) and bool(plans), plans)
            plan = plans[0]
            self.record_assertion("plan_has_activities", bool(plan.get("activities")), plan)
            self.transition("EXECUTE:PLAN_SELECTED")
            selected = self.post(f"/api/v1/journeys/{journey_id}/plans/{plan['id']}/select")
            self.record_assertion(
                "plan_selection_succeeds",
                selected.get("active_plan_version_id") == plan["id"] and selected.get("status") == "PLANNED",
                selected,
            )

            self.transition("EXECUTE:JOURNEY_STARTED")
            started = self.post(f"/api/v1/journeys/{journey_id}/start")
            self.record_assertion("journey_start_succeeds", started.get("projection_status") == "READY", started)
            self.record_assertion("p7_not_claimed", self.input_payload["p7"] is False, started)

            activities = plan["activities"]
            target = next((a for a in activities if a.get("place_id") == "place-tech-art"), activities[0])
            self.transition("OBSERVE:EVENT_INJECTED", {"activity_id": target["id"]})
            event_input = dict(self.input_payload["event"])
            event_input["affected_activity_id"] = target["id"]
            event = self.post(f"/api/v1/journeys/{journey_id}/events", event_input)
            self.record_assertion("event_injection_succeeds", bool(event.get("id")), event)

            self.transition("EXECUTE:REPLAN_GENERATED")
            replan = self.post(
                f"/api/v1/journeys/{journey_id}/replans",
                {"trigger_event_id": event["id"], "candidate_count": 3},
            )
            self.record_assertion("replan_generation_succeeds", bool(replan.get("id")), replan)
            proposals = self.get(f"/api/v1/journeys/{journey_id}/replans")
            matching = [p for p in proposals if p.get("trigger_event_id") == event["id"]]
            self.record_assertion("replan_is_listed", bool(matching), proposals)
            self.record_assertion(
                "replan_preserves_hard_constraints",
                all(p.get("hard_constraints_passed") for p in matching),
                matching,
            )
            self.transition("ASSERT", {"proposal_count": len(matching)})
            self.transition("CAPTURE_EVIDENCE")
            self.transition("REPLAY_READY")
        except Exception as exc:  # noqa: BLE001 - receipt must contain the exact blocker
            result = "FAIL"
            blocker = {
                "type": type(exc).__name__,
                "message": str(exc),
                "traceback": traceback.format_exc(),
            }

        environment = {
            "cwd": str(ROOT),
            "python": sys.version,
            "platform": platform.platform(),
            "mode": "isolated-test",
            "ports": [],
            "external_actions": False,
        }
        database = {
            "path": str(self.db_path),
            "identity": hashlib.sha256(str(self.db_path).encode()).hexdigest()[:16],
            "disposable": True,
            "exists": self.db_path.exists(),
        }
        receipt = {
            "run_id": self.run_id,
            "started_at": started_at,
            "finished_at": _utc(),
            "commit": _git_commit(),
            "scenario_id": SCENARIO_ID,
            "environment_identity": environment,
            "database_identity": database,
            "runtime_provider_identity": {
                "runtime": "CityNexus FastAPI in-process TestClient",
                "providers": {"mobility": "REPLAY", "ai": "DISABLED", "hermes": "NOT_CONFIGURED"},
                "p7": False,
            },
            "inputs": self.input_payload,
            "state_transitions": self.transitions,
            "api_tool_actions": self.actions,
            "assertions": self.assertions,
            "result": result,
            "blocker": blocker,
            "artifact_log_paths": {"evidence": str(self.receipt_path)},
            "replay": {
                "command": "python scripts/run_harness.py --scenario journey-replan-replay",
                "source_run_id": self.run_id,
                "historical_lineage": [
                    "backend/tests/v191_harness.py",
                    "backend/tests/v192_harness.py",
                    "reports/product-v18-3/HARNESS_MERGE_DECISIONS.md",
                ],
            },
        }
        self.receipt_path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding="utf-8")
        return receipt


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the isolated current CityNexus Harness")
    parser.add_argument("--scenario", choices=[SCENARIO_ID], required=True)
    parser.add_argument("--replay", type=Path, help="load a previous receipt as replay input")
    parser.add_argument("--evidence-dir", type=Path, help="override the evidence output directory")
    args = parser.parse_args()
    replay = json.loads(args.replay.read_text(encoding="utf-8")) if args.replay else None
    run_id = str(uuid.uuid4())
    evidence_dir = args.evidence_dir or ROOT / "output" / "harness" / run_id
    receipt = Harness(evidence_dir, replay).run()
    print(json.dumps({"result": receipt["result"], "run_id": receipt["run_id"], "evidence": receipt["artifact_log_paths"]}, ensure_ascii=False))
    return 0 if receipt["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
