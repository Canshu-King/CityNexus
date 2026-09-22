"""Run the supplied H7 generic ACTIVE-selection guard test in isolation.

The proposed guard is intentionally not installed by this probe.  A RED result
records the current product response and the state invariants that a future
guard must preserve.
"""

from __future__ import annotations

import argparse
import json
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.run_harness import (
    Harness,
    _git_commit,
    _jsonable,
    _sqlite_logical_snapshot,
)


def utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence-dir", default="output/harness/h7-generic-selection-guard")
    args = parser.parse_args()

    root = ROOT
    run_dir = root / args.evidence_dir
    harness = Harness(run_dir, "h7-generic-active-selection-guard")
    harness.bootstrap()

    harness.transition("RESET")
    ids = harness.post("/api/v1/demo/reset")
    journey_id = ids["journey_id"]
    harness.transition("SEED", ids)
    first = harness.post(
        f"/api/v1/journeys/{journey_id}/plans/generate", {"candidate_count": 1}
    )[0]
    harness.post(f"/api/v1/journeys/{journey_id}/plans/{first['id']}/select")
    harness.post(f"/api/v1/journeys/{journey_id}/start")
    active_before = harness.get(f"/api/v1/journeys/{journey_id}")
    second = harness.post(
        f"/api/v1/journeys/{journey_id}/plans/generate", {"candidate_count": 1}
    )[0]
    plans_before = harness.get(f"/api/v1/journeys/{journey_id}/plans")

    harness.transition("EXECUTE:GENERIC_ACTIVE_REPLACEMENT_SELECT")
    blocked_response = harness.client.post(
        f"/api/v1/journeys/{journey_id}/plans/{second['id']}/select"
    )
    blocked = harness.action(
        "POST",
        f"/api/v1/journeys/{journey_id}/plans/{second['id']}/select",
        blocked_response,
    )
    active_after = harness.get(f"/api/v1/journeys/{journey_id}")
    plans_after = harness.get(f"/api/v1/journeys/{journey_id}/plans")

    detail = str(blocked.get("error", {}).get("message") or blocked)
    authoritative = [
        row for row in plans_after if row.get("status") in {"ACTIVE", "SELECTED"}
    ]
    assertions = [
        {
            "name": "generic_active_selection_returns_governance_409",
            "passed": blocked_response.status_code == 409
            and "ACTIVE_JOURNEY_PLAN_REPLACEMENT_REQUIRES_GOVERNED_REPLAN" in detail,
            "details": {"status_code": blocked_response.status_code, "detail": detail},
        },
        {
            "name": "journey_unchanged_after_blocked_selection",
            "passed": active_after == active_before,
            "details": {"before": active_before, "after": active_after},
        },
        {
            "name": "plans_unchanged_after_blocked_selection",
            "passed": plans_after == plans_before,
            "details": {"before": plans_before, "after": plans_after},
        },
        {
            "name": "single_authoritative_plan_remains",
            "passed": len(authoritative) == 1
            and authoritative[0].get("id") == first["id"]
            and authoritative[0].get("status") == "ACTIVE"
            and next(row for row in plans_after if row["id"] == second["id"])["status"]
            == "CANDIDATE",
            "details": {"authoritative": authoritative, "plans": plans_after},
        },
    ]
    result = "PASS" if all(item["passed"] for item in assertions) else "FAIL"
    classification = []
    if blocked_response.status_code == 200:
        classification.append("ACTIVE_JOURNEY_GENERIC_SELECTION_BYPASSES_REPLAN_GOVERNANCE")
        if len(authoritative) > 1:
            classification.append("MULTIPLE_AUTHORITATIVE_PLAN_OWNERS")
        current_activity = active_after.get("current_activity_id")
        current_plan = next(
            (row for row in plans_after if any(a.get("id") == current_activity for a in row.get("activities", []))),
            None,
        )
        if current_plan and current_plan.get("id") != active_after.get("active_plan_version_id"):
            classification.append("CROSS_PLAN_CURRENT_ACTIVITY_POINTER")

    receipt = {
        "run_id": harness.run_id,
        "started_at": harness.actions[0]["at"],
        "finished_at": utc(),
        "commit": _git_commit(),
        "scenario_id": "h7-generic-active-selection-guard",
        "environment_identity": {
            "cwd": str(root),
            "python": sys.version,
            "platform": platform.platform(),
            "mode": "isolated-test",
            "external_actions": False,
        },
        "database_identity": {
            "path": str(harness.db_path),
            **_sqlite_logical_snapshot(harness.db_path),
            "disposable": True,
        },
        "runtime_provider_identity": {
            "runtime": "CityNexus FastAPI in-process TestClient",
            "providers": {"mobility": "SYNTHETIC_FIXTURE", "mobility_provider": "mock-mobility"},
            "p7": False,
        },
        "inputs": {"candidate_count": 1, "p7": False},
        "state_transitions": harness.transitions,
        "api_tool_actions": harness.actions,
        "assertions": assertions,
        "classification": classification,
        "result": result,
        "blocker": (
            {
                "type": "AssertionError",
                "message": "generic ACTIVE selection was not blocked by governed-replan guard",
            }
            if result == "FAIL"
            else None
        ),
        "artifact_log_paths": {"evidence": str(run_dir / "evidence.json")},
        "provenance": {
            "accessibility": "NOT_USED",
            "mobility": "SYNTHETIC_FIXTURE",
            "live_claim": False,
            "p7": False,
        },
    }
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "evidence.json").write_text(
        json.dumps(_jsonable(receipt), ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({"result": result, "classification": classification, "evidence": str(run_dir / "evidence.json")}))
    return 0 if result == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
