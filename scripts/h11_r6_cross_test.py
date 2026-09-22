"""Harness-owned H11 cross-test for a repaired Revolution Lab tree.

Read-only with respect to the LAB checkout.  It uses one unique disposable DB
and records that the DB path did not exist before importing the product app.
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
from tempfile import mkdtemp
from typing import Any
from uuid import uuid4

F_CAPTURED = "CAPTURED_REPLAY_SYNTHETIC_AUTHORITY_ESCAPE"
F_COST = "UNKNOWN_COST_ZERO_BUDGETING"


def git(root: Path, *args: str) -> str:
    return subprocess.check_output(
        ["git", "-C", str(root), *args], text=True, encoding="utf-8"
    ).strip()


def reason_code(body: Any) -> str | None:
    if isinstance(body, dict):
        if isinstance(body.get("reason_code"), str):
            return body["reason_code"]
        for value in body.values():
            found = reason_code(value)
            if found:
                return found
    if isinstance(body, list):
        for value in body:
            found = reason_code(value)
            if found:
                return found
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--lab-tree", required=True)
    ap.add_argument("--expected-lab-commit", required=True)
    ap.add_argument("--out")
    args = ap.parse_args()

    harness_root = Path(__file__).resolve().parents[1]
    lab_root = Path(args.lab_tree).resolve()
    expected = args.expected_lab_commit.strip()
    harness_commit = git(harness_root, "rev-parse", "HEAD")
    lab_commit = git(lab_root, "rev-parse", "HEAD")
    lab_status = git(lab_root, "status", "--porcelain=v1")
    if lab_commit != expected:
        raise SystemExit(f"LAB commit mismatch: {lab_commit} != {expected}")
    if lab_status:
        raise SystemExit("LAB worktree is not clean")

    run_id = f"h11-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}-{uuid4().hex[:8]}"
    output_dir_preexisted = False
    if args.out:
        out = Path(args.out).resolve()
        run_dir = out.parent
        output_dir_preexisted = run_dir.exists()
        if output_dir_preexisted:
            raise SystemExit(f"refusing non-fresh output directory: {run_dir}")
        run_dir.mkdir(parents=True, exist_ok=True)
    else:
        run_dir = Path(mkdtemp(prefix=f"citynexus-{run_id}-"))
        out = run_dir / "h11-r6-cross-test.json"
    db_path = run_dir / f"{run_id}.sqlite3"
    db_preexisted = db_path.exists() or db_path.with_suffix(db_path.suffix + "-wal").exists()
    if db_preexisted:
        raise SystemExit(f"refusing non-fresh DB path: {db_path}")

    os.environ["CITYNEXUS_DATABASE_URL"] = f"sqlite:///{db_path.as_posix()}"
    os.environ["CITYNEXUS_ENV"] = "test"
    os.environ["CITYNEXUS_DEMO_MODE"] = "true"
    os.environ["CITYNEXUS_AI_ENABLED"] = "false"
    os.environ["CITYNEXUS_GUARDIAN_ENABLED"] = "false"
    os.environ["CITYNEXUS_P7_ENABLED"] = "false"
    sys.path.insert(0, str(lab_root / "backend"))

    from fastapi.testclient import TestClient
    from sqlalchemy import select
    from app.db.models import Place, PlanVersion
    from app.db.session import SessionLocal
    from app.main import app

    client = TestClient(app)

    def make_place(
        pid: str,
        *,
        city: str,
        provider: str,
        mode: str,
        cost_status: str,
        amount_minor: int | None,
        price_known: bool,
    ) -> Place:
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
                    "cost_minor": 0 if amount_minor is None else amount_minor,
                    "price_known": price_known,
                    "cost_evidence": {
                        "status": cost_status,
                        "amount_minor": amount_minor,
                        "currency": "CNY",
                        "source": provider,
                    },
                },
                sort_keys=True,
            ),
            updated_at=datetime.now(timezone.utc).isoformat(),
        )

    def create_journey(city: str, title: str) -> str:
        tr = client.post(
            "/api/v1/travelers",
            json={
                "display_name": "H11 cross-test",
                "locale": "zh-CN",
                "timezone": "Asia/Shanghai",
            },
        )
        tr.raise_for_status()
        jr = client.post(
            "/api/v1/journeys",
            json={
                "traveler_id": tr.json()["id"],
                "title": title,
                "city_code": city,
                "timezone": "Asia/Shanghai",
                "start_at": "2026-10-02T09:00:00+08:00",
                "end_at": "2026-10-02T20:00:00+08:00",
                "party_size": 1,
                "budget": {"amount_minor": 100000, "currency": "CNY"},
            },
        )
        jr.raise_for_status()
        return str(jr.json()["id"])

    def plan_count(journey_id: str) -> int:
        with SessionLocal() as s:
            return len(list(s.scalars(select(PlanVersion).where(PlanVersion.journey_id == journey_id)).all()))

    def arm(
        arm_id: str,
        *,
        city: str,
        provider: str,
        mode: str,
        cost_status: str,
        amount_minor: int | None,
        price_known: bool,
        expected_generate: int,
        expected_selectable: bool | None,
        expected_select: int | None,
        expected_reason: str | None = None,
        expected_activity_cost_status: str | None = None,
    ) -> dict[str, Any]:
        client.post("/api/v1/demo/reset").raise_for_status()
        ids = [f"{arm_id}-a", f"{arm_id}-b"]
        with SessionLocal() as s:
            s.add_all([
                make_place(
                    pid,
                    city=city,
                    provider=provider,
                    mode=mode,
                    cost_status=cost_status,
                    amount_minor=amount_minor,
                    price_known=price_known,
                )
                for pid in ids
            ])
            s.commit()
        jid = create_journey(city, arm_id)
        before_journey = client.get(f"/api/v1/journeys/{jid}").json()
        before_count = plan_count(jid)
        gen = client.post(
            f"/api/v1/journeys/{jid}/plans/generate",
            json={"place_ids": ids, "candidate_count": 1},
        )
        body = gen.json()
        rec: dict[str, Any] = {
            "arm_id": arm_id,
            "inputs": {
                "provider": provider,
                "discovery_mode": mode,
                "cost_evidence_status": cost_status,
                "cost_evidence_amount_minor": amount_minor,
                "compatibility_cost_minor": 0 if amount_minor is None else amount_minor,
                "price_known": price_known,
            },
            "generate": {"status": gen.status_code, "body": body},
            "plan_rows_before": before_count,
            "expected": {
                "generate_status": expected_generate,
                "selectable": expected_selectable,
                "select_status": expected_select,
                "reason_code": expected_reason,
                "activity_cost_status": expected_activity_cost_status,
            },
            "findings": [],
        }
        passed = gen.status_code == expected_generate
        if expected_reason is not None and gen.status_code != 201:
            passed = passed and reason_code(body) == expected_reason
        if gen.status_code == 201:
            plan = body[0]
            statuses = [x.get("cost_status") for x in plan.get("activities", [])]
            rec["candidate"] = {
                "id": plan.get("id"),
                "selectable": plan.get("selectable"),
                "activity_cost_statuses": statuses,
                "total_cost": plan.get("total_cost"),
                "score_breakdown": plan.get("score_breakdown"),
                "mobility_evidence": plan.get("mobility_evidence"),
            }
            if expected_selectable is not None:
                passed = passed and plan.get("selectable") is expected_selectable
            if expected_activity_cost_status is not None:
                passed = passed and bool(statuses) and all(x == expected_activity_cost_status for x in statuses)
            sel = client.post(f"/api/v1/journeys/{jid}/plans/{plan['id']}/select")
            after_journey = client.get(f"/api/v1/journeys/{jid}").json()
            rec["select"] = {"status": sel.status_code, "body": sel.json()}
            if expected_reason is not None and expected_select is not None:
                passed = passed and reason_code(rec["select"]["body"]) == expected_reason
            rec["journey_pointer"] = {
                "before": before_journey.get("active_plan_version_id"),
                "after": after_journey.get("active_plan_version_id"),
            }
            if expected_select is not None:
                passed = passed and sel.status_code == expected_select
            if expected_select == 409:
                passed = passed and rec["journey_pointer"]["before"] == rec["journey_pointer"]["after"]
            if mode == "captured_replay" and (plan.get("selectable") is True or sel.status_code == 200):
                rec["findings"].append(F_CAPTURED)
            if cost_status == "UNKNOWN":
                zero = (plan.get("total_cost") or {}).get("amount_minor") == 0
                budget_fit = (plan.get("score_breakdown") or {}).get("budget_fit")
                if zero or budget_fit == 1.0:
                    rec["findings"].append(F_COST)
        after_count = plan_count(jid)
        rec["plan_rows_after"] = after_count
        if expected_generate == 422:
            passed = passed and after_count == before_count
        rec["result"] = "PASS" if passed else "RED"
        return rec

    arms = [
        arm(
            "live-overpass-known-paid",
            city="H11-LIVE-PAID",
            provider="overpass",
            mode="live",
            cost_status="KNOWN",
            amount_minor=1000,
            price_known=True,
            expected_generate=201,
            expected_selectable=False,
            expected_select=409,
            expected_reason="SYNTHETIC_MOBILITY_NOT_AUTHORITATIVE_FOR_LIVE_CONTENT",
            expected_activity_cost_status="KNOWN_PAID",
        ),
        arm(
            "captured-replay-known-paid",
            city="H11-CAPTURED",
            provider="openstreetmap-replay",
            mode="captured_replay",
            cost_status="KNOWN",
            amount_minor=1000,
            price_known=True,
            expected_generate=201,
            expected_selectable=False,
            expected_select=409,
            expected_reason="SYNTHETIC_MOBILITY_NOT_AUTHORITATIVE_FOR_LIVE_CONTENT",
            expected_activity_cost_status="KNOWN_PAID",
        ),
        arm(
            "live-overpass-unknown-cost",
            city="H11-UNKNOWN",
            provider="overpass",
            mode="live",
            cost_status="UNKNOWN",
            amount_minor=None,
            price_known=False,
            expected_generate=422,
            expected_selectable=None,
            expected_select=None,
            expected_reason="PLACE_COST_UNVERIFIED",
        ),
        arm(
            "live-overpass-known-free",
            city="H11-FREE",
            provider="overpass",
            mode="live",
            cost_status="KNOWN",
            amount_minor=0,
            price_known=True,
            expected_generate=201,
            expected_selectable=False,
            expected_select=409,
            expected_reason="SYNTHETIC_MOBILITY_NOT_AUTHORITATIVE_FOR_LIVE_CONTENT",
            expected_activity_cost_status="KNOWN_FREE",
        ),
    ]

    # Product-owned sealed demo negative control.
    reset = client.post("/api/v1/demo/reset")
    reset.raise_for_status()
    demo = reset.json()
    dg = client.post(
        f"/api/v1/journeys/{demo['journey_id']}/plans/generate",
        json={"candidate_count": 1},
    )
    ctrl: dict[str, Any] = {
        "arm_id": "sealed-demo-negative-control",
        "generate": {"status": dg.status_code, "body": dg.json()},
        "findings": [],
    }
    ctrl_ok = dg.status_code == 201
    if dg.status_code == 201:
        p = dg.json()[0]
        ds = client.post(f"/api/v1/journeys/{demo['journey_id']}/plans/{p['id']}/select")
        ctrl["candidate"] = {"id": p.get("id"), "selectable": p.get("selectable")}
        ctrl["select"] = {"status": ds.status_code, "body": ds.json()}
        ctrl_ok = p.get("selectable") is True and ds.status_code == 200
    ctrl["result"] = "PASS" if ctrl_ok else "RED"
    arms.append(ctrl)

    lab_commit_after = git(lab_root, "rev-parse", "HEAD")
    lab_status_after = git(lab_root, "status", "--porcelain=v1")
    findings = sorted({f for a in arms for f in a.get("findings", [])})
    receipt = {
        "schema": "citynexus.harness.h11-cross-test.v1",
        "run_id": run_id,
        "result": "PASS" if all(a["result"] == "PASS" for a in arms) else "RED",
        "product_findings": findings,
        "environment": {
            "harness_branch": git(harness_root, "branch", "--show-current"),
            "harness_commit": harness_commit,
            "harness_root": str(harness_root),
            "lab_commit": lab_commit,
            "lab_expected_commit": expected,
            "lab_commit_after": lab_commit_after,
            "lab_clean_before": lab_status == "",
            "lab_clean_after": lab_status_after == "",
            "lab_tree": str(lab_root),
            "p7": False,
            "database": {
                "path": str(db_path),
                "disposable": True,
                "output_directory": str(run_dir),
                "output_directory_did_not_exist_before_run": not output_dir_preexisted,
                "path_did_not_exist_before_run": not db_preexisted,
                "sha256": hashlib.sha256(db_path.read_bytes()).hexdigest() if db_path.exists() else None,
            },
        },
        "arms": arms,
    }
    if lab_commit_after != lab_commit or lab_status_after:
        receipt["result"] = "RED"
        receipt.setdefault("measurement_findings", []).append("LAB_TREE_CHANGED_DURING_CROSS_TEST")
    out.write_text(json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if receipt["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
