"""Independent H10 cross-test of the read-only Revolution Lab R5 checkout.

The probe owns assertions and evidence only.  It never patches the LAB tree.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

EXPECTED_LAB_COMMIT = "e188c5bfc6e01779f14cba1da3497d80075b96ee"
EXPECTED_HARNESS_PARENT = "c1981efbcbec41443eac6eda715fe7b7d945e69a"
FINDING_CAPTURED = "CAPTURED_REPLAY_SYNTHETIC_AUTHORITY_ESCAPE"
FINDING_COST = "UNKNOWN_COST_ZERO_BUDGETING"


def _git(path: Path, *args: str) -> str:
    return subprocess.check_output(
        ["git", "-C", str(path), *args], text=True, encoding="utf-8"
    ).strip()


def _body(response: Any) -> Any:
    return response.json()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--lab-tree", default=r"D:\moodle\CityNexus-RevolutionLab-R5"
    )
    parser.add_argument("--output")
    args = parser.parse_args()

    harness_root = Path(__file__).resolve().parents[1]
    lab_root = Path(args.lab_tree).resolve()
    run_id = f"h10-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}-{uuid4().hex[:8]}"
    output = (
        Path(args.output).resolve()
        if args.output
        else harness_root / "output" / "harness" / run_id / "h10-r5-cross-test.json"
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    db_path = output.parent / "h10-r5-cross-test.sqlite3"

    lab_commit = _git(lab_root, "rev-parse", "HEAD")
    lab_status = _git(lab_root, "status", "--porcelain=v1")
    harness_commit = _git(harness_root, "rev-parse", "HEAD")
    harness_branch = _git(harness_root, "branch", "--show-current")

    os.environ["CITYNEXUS_DATABASE_URL"] = f"sqlite:///{db_path.as_posix()}"
    os.environ["CITYNEXUS_ENV"] = "test"
    os.environ["CITYNEXUS_DEMO_MODE"] = "true"
    os.environ["CITYNEXUS_AI_ENABLED"] = "false"
    os.environ["CITYNEXUS_GUARDIAN_ENABLED"] = "false"
    os.environ["CITYNEXUS_P7_ENABLED"] = "false"
    sys.path.insert(0, str(lab_root / "backend"))

    from app.db.models import Place
    from app.db.session import SessionLocal
    from app.main import app
    from fastapi.testclient import TestClient

    client = TestClient(app)

    def place(
        pid: str,
        *,
        city: str,
        provider: str,
        mode: str,
        cost_status: str = "KNOWN",
    ) -> Any:
        known = cost_status == "KNOWN"
        return Place(
            id=pid,
            provider_key=provider,
            external_id=f"{provider}:{pid}",
            city_code=city,
            name=pid,
            category="park",
            latitude=27.74,
            longitude=98.66 + (0.01 if pid.endswith("b") else 0),
            opening_hours_json=json.dumps({"open": "09:00", "close": "18:00"}),
            tags_json="[]",
            metadata_json=json.dumps(
                {
                    "discovery_mode": mode,
                    "cost_minor": 1000 if known else 0,
                    "cost_evidence": {
                        "status": cost_status,
                        "amount_minor": 1000 if known else None,
                        "currency": "CNY",
                        "source": provider,
                    },
                },
                sort_keys=True,
            ),
            updated_at=datetime.now(timezone.utc).isoformat(),
        )

    def create_journey(city: str, title: str) -> str:
        traveler = client.post(
            "/api/v1/travelers",
            json={
                "display_name": "H10 cross-test",
                "locale": "zh-CN",
                "timezone": "Asia/Shanghai",
            },
        )
        traveler.raise_for_status()
        journey = client.post(
            "/api/v1/journeys",
            json={
                "traveler_id": traveler.json()["id"],
                "title": title,
                "city_code": city,
                "timezone": "Asia/Shanghai",
                "start_at": "2026-10-02T09:00:00+08:00",
                "end_at": "2026-10-02T20:00:00+08:00",
                "party_size": 1,
                "budget": {"amount_minor": 100000, "currency": "CNY"},
            },
        )
        journey.raise_for_status()
        return str(journey.json()["id"])

    def custom_arm(
        *,
        arm_id: str,
        city: str,
        provider: str,
        mode: str,
        cost_status: str,
        expected_generate: int,
        expected_selectable: bool | None,
        expected_select: int | None,
        finding_if_escape: str | None = None,
    ) -> dict[str, Any]:
        reset = client.post("/api/v1/demo/reset")
        reset.raise_for_status()
        ids = [f"{arm_id}-a", f"{arm_id}-b"]
        with SessionLocal() as session:
            session.add_all(
                [
                    place(
                        pid,
                        city=city,
                        provider=provider,
                        mode=mode,
                        cost_status=cost_status,
                    )
                    for pid in ids
                ]
            )
            session.commit()
        journey_id = create_journey(city, arm_id)
        before = client.get(f"/api/v1/journeys/{journey_id}").json()
        generated = client.post(
            f"/api/v1/journeys/{journey_id}/plans/generate",
            json={"place_ids": ids, "candidate_count": 1},
        )
        arm: dict[str, Any] = {
            "arm_id": arm_id,
            "inputs": {
                "provider": provider,
                "discovery_mode": mode,
                "cost_evidence_status": cost_status,
                "compatibility_cost_minor": 1000 if cost_status == "KNOWN" else 0,
                "place_ids": ids,
            },
            "generate": {"status": generated.status_code, "body": _body(generated)},
            "expected": {
                "generate_status": expected_generate,
                "selectable": expected_selectable,
                "select_status": expected_select,
            },
            "findings": [],
        }
        passed = generated.status_code == expected_generate
        if generated.status_code == 201:
            plan = generated.json()[0]
            arm["candidate"] = {
                "id": plan["id"],
                "selectable": plan.get("selectable"),
                "total_cost": plan.get("total_cost"),
                "score_breakdown": plan.get("score_breakdown"),
                "activity_cost_statuses": [
                    {
                        "place_id": activity.get("place_id"),
                        "cost_status": activity.get("cost_status"),
                        "estimated_cost": activity.get("estimated_cost"),
                    }
                    for activity in plan.get("activities", [])
                ],
                "mobility_identity": {
                    "source_provider": plan.get("mobility_evidence", {}).get(
                        "source_provider"
                    ),
                    "aggregate_provenance": plan.get("mobility_evidence", {}).get(
                        "aggregate_provenance"
                    ),
                    "fact_route_provenance": [
                        fact.get("route_provenance")
                        for fact in plan.get("mobility_evidence", {}).get("facts", [])
                    ],
                },
            }
            if expected_selectable is not None:
                passed = passed and plan.get("selectable") is expected_selectable
            selected = client.post(
                f"/api/v1/journeys/{journey_id}/plans/{plan['id']}/select"
            )
            after = client.get(f"/api/v1/journeys/{journey_id}").json()
            arm["select"] = {"status": selected.status_code, "body": _body(selected)}
            arm["journey_pointer"] = {
                "before": before.get("active_plan_version_id"),
                "after": after.get("active_plan_version_id"),
            }
            if expected_select is not None:
                passed = passed and selected.status_code == expected_select
            if expected_select == 409:
                passed = passed and before.get("active_plan_version_id") == after.get(
                    "active_plan_version_id"
                )
            if finding_if_escape and (
                plan.get("selectable") is True or selected.status_code == 200
            ):
                arm["findings"].append(finding_if_escape)
            if cost_status == "UNKNOWN":
                unknown_present = any(
                    row.get("cost_status") == "UNKNOWN"
                    for row in arm["candidate"]["activity_cost_statuses"]
                )
                zero_total = (plan.get("total_cost") or {}).get("amount_minor") == 0
                if unknown_present and zero_total and FINDING_COST not in arm["findings"]:
                    arm["findings"].append(FINDING_COST)
        arm["result"] = "PASS" if passed else "RED"
        return arm

    arms = [
        custom_arm(
            arm_id="live-overpass-mock-mobility",
            city="H10-LIVE",
            provider="overpass",
            mode="live",
            cost_status="KNOWN",
            expected_generate=201,
            expected_selectable=False,
            expected_select=409,
        ),
        custom_arm(
            arm_id="captured-replay-mock-mobility",
            city="H10-CAPTURED",
            provider="openstreetmap-replay",
            mode="captured_replay",
            cost_status="KNOWN",
            expected_generate=201,
            expected_selectable=False,
            expected_select=409,
            finding_if_escape=FINDING_CAPTURED,
        ),
        custom_arm(
            arm_id="unknown-cost-compatibility-zero",
            city="H10-COST",
            provider="overpass",
            mode="live",
            cost_status="UNKNOWN",
            expected_generate=422,
            expected_selectable=None,
            expected_select=None,
            finding_if_escape=FINDING_COST,
        ),
    ]

    reset = client.post("/api/v1/demo/reset")
    reset.raise_for_status()
    demo = reset.json()
    generated = client.post(
        f"/api/v1/journeys/{demo['journey_id']}/plans/generate",
        json={"candidate_count": 1},
    )
    control: dict[str, Any] = {
        "arm_id": "sealed-demo-mock-mobility-negative-control",
        "generate": {"status": generated.status_code, "body": _body(generated)},
        "findings": [],
    }
    control_passed = generated.status_code == 201
    if generated.status_code == 201:
        plan = generated.json()[0]
        selected = client.post(
            f"/api/v1/journeys/{demo['journey_id']}/plans/{plan['id']}/select"
        )
        after = client.get(f"/api/v1/journeys/{demo['journey_id']}").json()
        control.update(
            {
                "candidate": {
                    "id": plan["id"],
                    "selectable": plan.get("selectable"),
                    "source_provider": plan.get("mobility_evidence", {}).get(
                        "source_provider"
                    ),
                },
                "select": {"status": selected.status_code, "body": _body(selected)},
                "journey_pointer_after": after.get("active_plan_version_id"),
            }
        )
        control_passed = (
            plan.get("selectable") is True
            and selected.status_code == 200
            and after.get("active_plan_version_id") == plan["id"]
        )
    control["result"] = "PASS" if control_passed else "RED"
    arms.append(control)

    findings = [finding for arm in arms for finding in arm.get("findings", [])]
    lab_commit_after = _git(lab_root, "rev-parse", "HEAD")
    lab_status_after = _git(lab_root, "status", "--porcelain=v1")
    preconditions_passed = (
        lab_commit == EXPECTED_LAB_COMMIT
        and lab_status == ""
        and lab_commit_after == lab_commit
        and lab_status_after == ""
    )
    receipt = {
        "schema": "citynexus.harness.cross-test.v1",
        "run_id": run_id,
        "scenario_id": "h10-r5-cross-lane-authority",
        "result": "PASS" if all(arm["result"] == "PASS" for arm in arms) else "RED",
        "product_findings": sorted(set(findings)),
        "environment": {
            "harness_branch": harness_branch,
            "harness_commit": harness_commit,
            "harness_expected_parent": EXPECTED_HARNESS_PARENT,
            "lab_tree": str(lab_root),
            "lab_commit": lab_commit,
            "lab_expected_commit": EXPECTED_LAB_COMMIT,
            "lab_clean": lab_status == "",
            "lab_commit_after": lab_commit_after,
            "lab_clean_after": lab_status_after == "",
            "database": {
                "engine": "sqlite",
                "path": str(db_path),
                "disposable": True,
                "identity": hashlib.sha256(db_path.read_bytes()).hexdigest()
                if db_path.exists()
                else None,
            },
            "p7": False,
            "mobility_provider": "mock-mobility / SYNTHETIC_FIXTURE",
        },
        "preconditions": {
            "lab_commit_exact": lab_commit == EXPECTED_LAB_COMMIT,
            "lab_worktree_clean": lab_status == "",
            "lab_commit_unchanged_after": lab_commit_after == lab_commit,
            "lab_worktree_clean_after": lab_status_after == "",
            "lab_tree_read_only_by_contract": True,
        },
        "arms": arms,
        "artifact_paths": {"receipt": str(output), "database": str(db_path)},
    }
    if not preconditions_passed:
        receipt["result"] = "RED"
    output.write_text(json.dumps(receipt, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0 if receipt["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
