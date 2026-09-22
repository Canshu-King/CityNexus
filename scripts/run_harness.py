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
import copy
import hashlib
import json
import os
import platform
import sqlite3
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
C4_SCENARIO_ID = "c4-commitment-replay"
CAPABILITY_SCENARIO_ID = "capability-fail-closed-replay"
SCENARIOS = (SCENARIO_ID, C4_SCENARIO_ID, CAPABILITY_SCENARIO_ID)


def _utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def _git_commit() -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()


def _jsonable(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, bytes):
        return {"__bytes_sha256__": hashlib.sha256(value).hexdigest(), "length": len(value)}
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    return value


def _sha256_json(value: Any) -> str:
    raw = json.dumps(_jsonable(value), ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _file_sha256(path: Path) -> str | None:
    if not path.exists():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _quote_sqlite_identifier(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def _sqlite_logical_snapshot(db_path: Path) -> dict[str, Any]:
    """Hash committed logical SQLite state, including data still resident in WAL.

    Hashing only the main .db file is unsound when SQLite is in WAL mode: committed
    rows can live in ``-wal`` while the main file remains byte-identical.  A normal
    SQLite reader sees the committed logical state across both files, so we hash a
    canonical table/row representation instead.
    """
    if not db_path.exists():
        return {
            "logical_state_sha256": hashlib.sha256(b"").hexdigest(),
            "actual_schema_sha256": hashlib.sha256(b"").hexdigest(),
            "table_row_counts": {},
            "migration_identity": None,
        }

    uri = f"file:{db_path.as_posix()}?mode=ro"
    with sqlite3.connect(uri, uri=True) as conn:
        tables = [
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master "
                "WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
            )
        ]
        schema_rows = list(
            conn.execute(
                "SELECT type, name, tbl_name, COALESCE(sql, '') FROM sqlite_master "
                "WHERE name NOT LIKE 'sqlite_%' ORDER BY type, name"
            )
        )
        schema_payload = [list(row) for row in schema_rows]
        table_payload: dict[str, Any] = {}
        row_counts: dict[str, int] = {}
        for table in tables:
            qtable = _quote_sqlite_identifier(table)
            columns = [row[1] for row in conn.execute(f"PRAGMA table_info({qtable})")]
            rows = []
            for raw_row in conn.execute(f"SELECT * FROM {qtable}"):
                row = {column: _jsonable(value) for column, value in zip(columns, raw_row)}
                rows.append(row)
            rows.sort(key=lambda item: json.dumps(item, ensure_ascii=False, sort_keys=True, default=str))
            table_payload[table] = {"columns": columns, "rows": rows}
            row_counts[table] = len(rows)

        migration_identity = None
        if "alembic_version" in tables:
            values = [row[0] for row in conn.execute("SELECT version_num FROM alembic_version ORDER BY version_num")]
            migration_identity = values

    conn.close()

    return {
        "logical_state_sha256": _sha256_json(table_payload),
        "actual_schema_sha256": _sha256_json(schema_payload),
        "table_row_counts": row_counts,
        "migration_identity": migration_identity,
    }


def _stable_commitment_semantics(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Normalize C4 snapshots for cross-run replay comparison.

    Generated row/activity/plan IDs are intentionally excluded.  Business identity,
    protected time/money/status, place, and booking/provider semantics remain.
    """
    fields = (
        "kind",
        "level",
        "status",
        "monetary_value_minor",
        "monetary_value_status",
        "currency",
        "external_ref",
        "place_id",
        "scheduled_start_at",
        "scheduled_end_at",
        "activity_status",
        "activity_locked",
        "booking_status",
        "booking_amount_minor",
        "booking_amount_status",
        "booking_currency",
        "booking_external_ref",
        "booking_provider_key",
    )
    def stable_reference(value: Any) -> Any:
        if not isinstance(value, str):
            return value
        parts = value.split(":")
        if parts[0] in {"mock-booking", "mock-payment"} and len(parts) >= 3:
            return f"{parts[0]}:<generated>:{parts[-1]}"
        return value

    normalized = []
    for item in items:
        row = {field: item.get(field) for field in fields}
        row["external_ref"] = stable_reference(row["external_ref"])
        row["booking_external_ref"] = stable_reference(row["booking_external_ref"])
        normalized.append(row)
    return sorted(normalized, key=lambda item: json.dumps(item, ensure_ascii=False, sort_keys=True, default=str))


class Harness:
    def __init__(
        self,
        run_dir: Path,
        scenario_id: str,
        replay_receipt: dict[str, Any] | None = None,
    ):
        self.run_dir = run_dir
        self.db_path = run_dir / "citynexus-harness.db"
        self.receipt_path = run_dir / "evidence.json"
        self.run_id = str(uuid.uuid4())
        self.actions: list[dict[str, Any]] = []
        self.transitions: list[dict[str, Any]] = []
        self.assertions: list[dict[str, Any]] = []
        self.scenario_id = scenario_id
        self.replay_receipt = replay_receipt
        self.replay_mode = replay_receipt is not None
        self.replay_source_run_id: str | None = None
        self.replay_source_semantic: dict[str, Any] | None = None
        self.client = None
        self.last_status: int | None = None
        self.ids: dict[str, Any] = {}
        self.input_payload = {
            "scenario_id": scenario_id,
            "candidate_count": 1,
            "event": {
                "event_type": "CLOSURE",
                "severity": "MAJOR",
                "occurred_at": "2026-10-10T13:25:00+08:00",
                "payload": {"reason": "harness isolated closure"},
            },
            "p7": False,
        }
        if scenario_id == C4_SCENARIO_ID:
            self.input_payload.update(
                {
                    "protected_activity_place": "place-river-cruise",
                    "mutable_activity_place": "place-tech-art",
                    "booking_provider": "mock-booking",
                    "payment_provider": "mock-payment",
                }
            )
        if scenario_id == CAPABILITY_SCENARIO_ID:
            self.input_payload.update(
                {
                    "capability": {
                        "code": "STEP_FREE_REQUIRED",
                        "severity": "HARD",
                        "scope": "JOURNEY",
                        "params": {"requirement": "step_free"},
                    },
                    "evidence_poor_state": "ACCESSIBILITY_UNVERIFIED",
                    "verified_evidence": {"step_free": True, "wheelchair_access": True},
                }
            )
        if replay_receipt is not None:
            self._validate_replay_receipt(replay_receipt)
            self.replay_source_run_id = replay_receipt["run_id"]
            self.replay_source_semantic = copy.deepcopy(replay_receipt["semantic_output"])
            self.input_payload = copy.deepcopy(replay_receipt["inputs"])
        self.semantic_output: dict[str, Any] = {}
        self.protected_commitments_before: list[dict[str, Any]] = []
        self.protected_commitments_after: list[dict[str, Any]] = []
        self.preserved_ids: list[str] = []
        self.changed_ids: list[str] = []
        self.allowed_changes: list[dict[str, Any]] = []
        self.illegal_changes: list[str] = []
        self.semantic_match: bool | None = None
        self.semantic_mismatches: list[dict[str, Any]] = []

    def _validate_replay_receipt(self, receipt: dict[str, Any]) -> None:
        required = ("run_id", "scenario_id", "inputs", "result", "semantic_output")
        missing = [key for key in required if key not in receipt]
        if missing:
            raise ValueError(f"replay receipt missing required fields: {missing}")
        if not isinstance(receipt["run_id"], str) or not receipt["run_id"]:
            raise ValueError("replay receipt run_id must be a non-empty string")
        if receipt["scenario_id"] != self.scenario_id:
            raise ValueError(
                f"replay scenario mismatch: expected {self.scenario_id}, got {receipt['scenario_id']}"
            )
        if receipt["result"] != "PASS":
            raise ValueError("replay source receipt must have result PASS")
        if not isinstance(receipt["inputs"], dict):
            raise TypeError("replay receipt inputs must be an object")
        if receipt["inputs"].get("scenario_id") != self.scenario_id:
            raise ValueError("replay receipt inputs do not identify the requested scenario")
        if not isinstance(receipt["semantic_output"], dict):
            raise TypeError("replay receipt semantic_output must be an object")

    def action(self, method: str, path: str, response: Any, payload: Any = None) -> Any:
        status = getattr(response, "status_code", None)
        self.last_status = status
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

    def _prepare_journey(self, *, start: bool = True) -> tuple[str, dict[str, Any], dict[str, Any] | None]:
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
        started = None
        if start:
            self.transition("EXECUTE:JOURNEY_STARTED")
            started = self.post(f"/api/v1/journeys/{journey_id}/start")
            self.record_assertion("journey_start_succeeds", started.get("projection_status") == "READY", started)
            self.record_assertion("p7_not_claimed", self.input_payload["p7"] is False, started)
        return journey_id, plan, started

    def _complete_before(self, journey_id: str, plan: dict[str, Any], target: dict[str, Any]) -> None:
        latest = None
        for activity in plan["activities"]:
            if activity["id"] == target["id"]:
                break
            latest = self.post(f"/api/v1/journeys/{journey_id}/activities/{activity['id']}/complete")
        self.record_assertion(
            "activity_completion_succeeds",
            latest is not None and latest.get("current_activity_id") == target["id"],
            latest,
        )

    def _protected_snapshot(self, journey_id: str) -> list[dict[str, Any]]:
        from app.db.models import Activity, Booking, Commitment
        from app.db.session import SessionLocal
        from sqlalchemy import select

        with SessionLocal() as session:
            commitments = list(
                session.scalars(
                    select(Commitment).where(
                        Commitment.journey_id == journey_id,
                        Commitment.level == "C4_Anchored",
                    )
                ).all()
            )
            result = []
            for commitment in commitments:
                activity = session.get(Activity, commitment.activity_id) if commitment.activity_id else None
                booking = session.scalar(
                    select(Booking).where(Booking.commitment_id == commitment.id)
                )
                result.append(
                    {
                        "commitment_id": commitment.id,
                        "booking_id": booking.id if booking else None,
                        "kind": commitment.kind,
                        "level": commitment.level,
                        "status": commitment.status,
                        "monetary_value_minor": commitment.monetary_value_minor,
                        "monetary_value_status": commitment.monetary_value_status,
                        "currency": commitment.currency,
                        "external_ref": commitment.external_ref,
                        "activity_id": activity.id if activity else None,
                        "activity_plan_version_id": activity.plan_version_id if activity else None,
                        "place_id": activity.place_id if activity else None,
                        "scheduled_start_at": activity.start_at if activity else None,
                        "scheduled_end_at": activity.end_at if activity else None,
                        "activity_status": activity.status if activity else None,
                        "activity_locked": activity.locked if activity else None,
                        "booking_status": booking.status if booking else None,
                        "booking_amount_minor": booking.amount_minor if booking else None,
                        "booking_amount_status": booking.amount_status if booking else None,
                        "booking_currency": booking.currency if booking else None,
                        "booking_external_ref": booking.external_ref if booking else None,
                        "booking_provider_key": booking.provider_key if booking else None,
                    }
                )
            return sorted(result, key=lambda item: item["commitment_id"])

    def _set_place_accessibility(self, evidence: dict[str, Any] | None) -> list[dict[str, Any]]:
        from app.db.models import Place
        from app.db.session import SessionLocal

        with SessionLocal() as session:
            places = list(session.query(Place).all())
            for place in places:
                metadata = json.loads(place.metadata_json or "{}")
                if evidence is None:
                    metadata.pop("accessibility", None)
                else:
                    metadata["accessibility"] = copy.deepcopy(evidence)
                place.metadata_json = json.dumps(metadata, ensure_ascii=False, sort_keys=True)
            session.commit()
        return self._place_evidence_states()

    def _place_evidence_states(self) -> list[dict[str, Any]]:
        from app.capabilities import evaluate_accessibility_requirement
        from app.db.models import Place
        from app.db.session import SessionLocal

        with SessionLocal() as session:
            rows = list(session.query(Place).order_by(Place.id).all())
            return [
                {
                    "place_id": place.id,
                    "state": evaluate_accessibility_requirement(
                        self.input_payload["capability"]["code"],
                        json.loads(place.metadata_json or "{}").get("accessibility") or {},
                    ),
                }
                for place in rows
            ]

    def _compare_commitments(self) -> None:
        before = {item["commitment_id"]: item for item in self.protected_commitments_before}
        after = {item["commitment_id"]: item for item in self.protected_commitments_after}
        self.preserved_ids = sorted(set(before) & set(after))
        self.changed_ids = sorted(
            key for key in self.preserved_ids if before[key] != after[key]
        )
        illegal: list[str] = []
        for key in sorted(set(before) - set(after)):
            illegal.append(f"missing_commitment:{key}")
        for key in sorted(set(after) - set(before)):
            illegal.append(f"unexpected_commitment:{key}")
        protected_fields = (
            "kind", "level", "status", "monetary_value_minor", "monetary_value_status", "currency",
            "external_ref", "place_id", "scheduled_start_at", "scheduled_end_at", "activity_status",
            "activity_locked", "booking_id", "booking_status", "booking_amount_minor", "booking_amount_status",
            "booking_currency", "booking_external_ref", "booking_provider_key",
        )
        allowed_rebind_fields = ("activity_id", "activity_plan_version_id")
        for key in self.preserved_ids:
            for field in protected_fields:
                if before[key].get(field) != after[key].get(field):
                    illegal.append(f"{key}.{field}: {before[key].get(field)!r} -> {after[key].get(field)!r}")
            for field in allowed_rebind_fields:
                if before[key].get(field) != after[key].get(field):
                    self.allowed_changes.append(
                        {
                            "commitment_id": key,
                            "field": field,
                            "before": before[key].get(field),
                            "after": after[key].get(field),
                            "classification": "ALLOWED_REPLAN_REBIND",
                        }
                    )
        self.illegal_changes = illegal

    def _run_journey_replan(self) -> None:
        journey_id, plan, _started = self._prepare_journey()
        activities = plan["activities"]
        target = next((a for a in activities if a.get("place_id") == "place-tech-art"), activities[0])
        self.transition("OBSERVE:EVENT_INJECTED", {"activity_place_id": target.get("place_id")})
        event_input = copy.deepcopy(self.input_payload["event"])
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
        hard_constraints = all(p.get("hard_constraints_passed") for p in matching)
        self.record_assertion("replan_preserves_hard_constraints", hard_constraints, matching)
        self.semantic_output = {
            "journey_lifecycle": ["RESET", "PLANNED", "ACTIVE"],
            "plan_activity_places": [a.get("place_id") for a in activities],
            "affected_activity_place": target.get("place_id"),
            "event_type": event.get("event_type"),
            "replan_exists": bool(matching),
            "hard_constraints_passed": hard_constraints,
            "protected_locked_places": sorted(a.get("place_id") for a in activities if a.get("locked")),
        }
        self.transition("ASSERT", self.semantic_output)
        self.transition("CAPTURE_EVIDENCE")
        self.transition("REPLAY_READY")

    def _run_c4_commitment(self) -> None:
        journey_id, plan, _started = self._prepare_journey(start=False)
        cruise = next(
            a for a in plan["activities"]
            if a.get("place_id") == self.input_payload["protected_activity_place"]
        )
        booking = self.post(
            f"/api/v1/journeys/{journey_id}/bookings",
            {"activity_id": cruise["id"], "provider_key": self.input_payload["booking_provider"]},
        )
        self.record_assertion("mock_booking_succeeds", bool(booking.get("id")), booking)
        capture = self.post(
            f"/api/v1/journeys/{journey_id}/transactions",
            {
                "booking_id": booking["id"],
                "transaction_type": "CAPTURE",
                "amount": booking["amount"],
            },
            headers={"Idempotency-Key": "h2-c4-capture-0001"},
        )
        self.record_assertion("mock_capture_succeeds", bool(capture.get("id")), capture)
        self.transition("EXECUTE:JOURNEY_STARTED")
        started = self.post(f"/api/v1/journeys/{journey_id}/start")
        self.record_assertion("journey_start_succeeds", started.get("projection_status") == "READY", started)
        self.record_assertion("p7_not_claimed", self.input_payload["p7"] is False, started)
        self.protected_commitments_before = self._protected_snapshot(journey_id)
        self.record_assertion("c4_commitment_exists_before", bool(self.protected_commitments_before), self.protected_commitments_before)
        tech = next(
            a for a in plan["activities"]
            if a.get("place_id") == self.input_payload["mutable_activity_place"]
        )
        self._complete_before(journey_id, plan, tech)
        self.transition("OBSERVE:EVENT_INJECTED", {"activity_place_id": tech.get("place_id")})
        event_input = copy.deepcopy(self.input_payload["event"])
        event_input["affected_activity_id"] = tech["id"]
        event = self.post(f"/api/v1/journeys/{journey_id}/events", event_input)
        self.record_assertion("event_injection_succeeds", bool(event.get("id")), event)
        self.transition("EXECUTE:REPLAN_GENERATED")
        proposal = self.post(
            f"/api/v1/journeys/{journey_id}/replans",
            {"trigger_event_id": event["id"], "candidate_count": 3},
        )
        self.record_assertion("replan_generation_succeeds", bool(proposal.get("id")), proposal)
        actual_hard_constraints_passed = proposal.get("hard_constraints_passed") is True
        actual_locked_commitments_preserved = proposal.get("locked_commitments_preserved") is True
        self.record_assertion(
            "c4_replan_reports_hard_constraints_passed",
            actual_hard_constraints_passed,
            proposal,
        )
        self.record_assertion(
            "c4_replan_reports_locked_commitments_preserved",
            actual_locked_commitments_preserved,
            proposal,
        )
        accepted = self.post(
            f"/api/v1/replans/{proposal['id']}/accept",
            headers={"Idempotency-Key": "h2-c4-accept-0001"},
        )
        self.record_assertion("replan_accept_succeeds", accepted.get("proposal", {}).get("status") == "ACCEPTED", accepted)
        self.protected_commitments_after = self._protected_snapshot(journey_id)
        self._compare_commitments()
        self.record_assertion("direct_c4_comparison_passes", not self.illegal_changes, self.illegal_changes)
        self.semantic_output = {
            "journey_lifecycle": ["RESET", "PLANNED", "ACTIVE"],
            "event_type": event.get("event_type"),
            "replan_exists": bool(proposal.get("id")),
            "replan_accepted": accepted.get("proposal", {}).get("status") == "ACCEPTED",
            "hard_constraints_passed": actual_hard_constraints_passed,
            "locked_commitments_preserved_claim": actual_locked_commitments_preserved,
            "protected_commitment_count": len(self.protected_commitments_before),
            "protected_commitment_outcome": not self.illegal_changes,
            "protected_commitment_semantics": _stable_commitment_semantics(self.protected_commitments_after),
        }
        self.transition("ASSERT", self.semantic_output)
        self.transition("CAPTURE_EVIDENCE")
        self.transition("REPLAY_READY")

    def _run_capability_fail_closed(self) -> None:
        self.transition("RESET")
        self.ids = self.post("/api/v1/demo/reset")
        self.record_assertion("reset_returns_journey", bool(self.ids.get("journey_id")), self.ids)
        journey_id = self.ids["journey_id"]
        self.transition("SEED", self.ids)
        capability = self.input_payload["capability"]
        capability_payload = [
            {
                "code": capability["code"],
                "severity": capability["severity"],
                "params": capability["params"],
            }
        ]
        before = self.get(f"/api/v1/journeys/{journey_id}/capabilities")
        self.transition("EXECUTE:CAPABILITY_CONFIRMED")
        confirmed = self.post(f"/api/v1/journeys/{journey_id}/capabilities/confirm", capability_payload)
        self.record_assertion("hard_capability_confirmation_succeeds", bool(confirmed.get("capabilities")), confirmed)
        after = self.get(f"/api/v1/journeys/{journey_id}/capabilities")
        self.transition("OBSERVE:EVIDENCE_POOR_CATALOG")
        evidence_poor = self._set_place_accessibility(None)
        self.record_assertion(
            "evidence_poor_catalog_is_unknown",
            bool(evidence_poor) and all(item["state"] == "ACCESSIBILITY_UNVERIFIED" for item in evidence_poor),
            evidence_poor,
        )
        self.transition("EXECUTE:FAIL_CLOSED_GENERATION")
        blocked = self.post(
            f"/api/v1/journeys/{journey_id}/plans/generate",
            {"candidate_count": self.input_payload["candidate_count"]},
        )
        blocked_status = self.last_status
        blocked_error = blocked.get("error", {}) if isinstance(blocked, dict) else {}
        blocked_message = str(blocked_error.get("message") or blocked)
        self.record_assertion(
            "unknown_evidence_blocks_plan",
            blocked_status == 422 and bool(blocked_error.get("code")) and not isinstance(blocked, list),
            {"status": blocked_status, "body": blocked, "product_reason": blocked_message},
        )
        self.record_assertion(
            "unknown_is_not_accessible",
            blocked_status == 422,
            blocked,
        )
        self.transition("EXECUTE:VERIFIED_EVIDENCE_GENERATION")
        verified_evidence = self._set_place_accessibility(self.input_payload["verified_evidence"])
        generated = self.post(
            f"/api/v1/journeys/{journey_id}/plans/generate",
            {"candidate_count": self.input_payload["candidate_count"]},
        )
        generated_status = self.last_status
        verified_plans = generated if isinstance(generated, list) else []
        verified_selectable = [bool(plan.get("selectable")) for plan in verified_plans]
        self.record_assertion(
            "verified_evidence_is_reported",
            all(item["state"] == "ACCESSIBILITY_VERIFIED" for item in verified_evidence),
            verified_evidence,
        )
        self.record_assertion(
            "verified_generation_is_product_truth",
            generated_status == 201 and bool(verified_plans) and all(verified_selectable),
            {"status": generated_status, "plans": verified_plans},
        )
        self.semantic_output = {
            "journey_lifecycle": ["RESET", "CAPABILITY_CONFIRMED"],
            "capability": {
                "code": capability["code"],
                "severity": capability["severity"],
                "scope": capability["scope"],
            },
            "evidence_poor_states": sorted({item["state"] for item in evidence_poor}),
            "blocked_generation_status": blocked_status,
            "blocked_product_reason": blocked_message,
            "blocked_is_fail_closed": blocked_status == 422,
            "verified_evidence_states": sorted({item["state"] for item in verified_evidence}),
            "verified_generation_status": generated_status,
            "verified_plan_count": len(verified_plans),
            "verified_selectable": verified_selectable,
        }
        self.transition("ASSERT", self.semantic_output)
        self.transition("CAPTURE_EVIDENCE", {"capabilities_before": before, "capabilities_after": after})
        self.transition("REPLAY_READY")

    def run(self) -> dict[str, Any]:
        started_at = _utc()
        result = "PASS"
        blocker = None
        try:
            self.bootstrap()
            if self.scenario_id == SCENARIO_ID:
                self._run_journey_replan()
            elif self.scenario_id == C4_SCENARIO_ID:
                self._run_c4_commitment()
            elif self.scenario_id == CAPABILITY_SCENARIO_ID:
                self._run_capability_fail_closed()
            else:
                raise ValueError(f"unsupported scenario: {self.scenario_id}")
        except Exception as exc:  # noqa: BLE001 - receipt must contain the exact blocker
            result = "FAIL"
            blocker = {
                "type": type(exc).__name__,
                "message": str(exc),
                "traceback": traceback.format_exc(),
            }

        if self.replay_mode and result == "PASS":
            self.semantic_match = self.semantic_output == self.replay_source_semantic
            if not self.semantic_match:
                self.semantic_mismatches = [
                    {
                        "field": key,
                        "source": self.replay_source_semantic.get(key),
                        "replay": self.semantic_output.get(key),
                    }
                    for key in sorted(set(self.replay_source_semantic) | set(self.semantic_output))
                    if self.replay_source_semantic.get(key) != self.semantic_output.get(key)
                ]
            self.assertions.append(
                {
                    "name": "receipt_semantic_match",
                    "passed": bool(self.semantic_match),
                    "details": self.semantic_mismatches,
                }
            )
            if not self.semantic_match:
                result = "FAIL"
                blocker = {"type": "SemanticMismatch", "message": "receipt-driven replay diverged", "mismatches": self.semantic_mismatches}

        if self.client is not None:
            self.client.close()

        environment = {
            "cwd": str(ROOT),
            "python": sys.version,
            "platform": platform.platform(),
            "mode": "isolated-test",
            "ports": [],
            "external_actions": False,
        }
        logical_db = _sqlite_logical_snapshot(self.db_path)
        sidecars = {}
        for suffix in ("", "-wal", "-shm"):
            part = Path(str(self.db_path) + suffix)
            if part.exists():
                sidecars[part.name] = {
                    "sha256": _file_sha256(part),
                    "size": part.stat().st_size,
                }
        declared_schema = BACKEND / "db" / "schema.sql"
        database = {
            "path": str(self.db_path),
            "identity": logical_db["logical_state_sha256"],
            "path_identity": hashlib.sha256(str(self.db_path).encode()).hexdigest()[:16],
            "state_sha256": logical_db["logical_state_sha256"],
            "logical_state_sha256": logical_db["logical_state_sha256"],
            "physical_components": sidecars,
            "schema_identity": logical_db["actual_schema_sha256"],
            "actual_schema_sha256": logical_db["actual_schema_sha256"],
            "declared_schema_sql_sha256": _file_sha256(declared_schema),
            "migration_identity": logical_db["migration_identity"],
            "table_row_counts": logical_db["table_row_counts"],
            "deterministic_seed_identity": _sha256_json(self.input_payload),
            "disposable": True,
            "exists": self.db_path.exists(),
        }
        replay = {
            "mode": "RECEIPT_DRIVEN" if self.replay_mode else "ORIGINAL",
            "source_run_id": self.replay_source_run_id,
            "semantic_match": self.semantic_match,
            "mismatches": self.semantic_mismatches,
            "command": f"python scripts/run_harness.py --scenario {self.scenario_id}",
            "historical_lineage": [
                "backend/tests/v191_harness.py",
                "backend/tests/v192_harness.py",
                "reports/product-v18-3/HARNESS_MERGE_DECISIONS.md",
            ],
        }
        receipt = {
            "run_id": self.run_id,
            "started_at": started_at,
            "finished_at": _utc(),
            "commit": _git_commit(),
            "scenario_id": self.scenario_id,
            "environment_identity": environment,
            "database_identity": database,
            "runtime_provider_identity": {
                "runtime": "CityNexus FastAPI in-process TestClient",
                "providers": {
                    "mobility": "SYNTHETIC_FIXTURE",
                    "mobility_provider": "mock-mobility",
                    "ai": "DISABLED",
                    "hermes": "NOT_CONFIGURED",
                },
                "p7": False,
            },
            "inputs": self.input_payload,
            "state_transitions": self.transitions,
            "api_tool_actions": self.actions,
            "assertions": self.assertions,
            "semantic_output": self.semantic_output,
            "protected_commitments_before": self.protected_commitments_before,
            "protected_commitments_after": self.protected_commitments_after,
            "preserved_ids": self.preserved_ids,
            "changed_ids": self.changed_ids,
            "allowed_changes": self.allowed_changes,
            "illegal_changes": self.illegal_changes,
            "result": result,
            "blocker": blocker,
            "artifact_log_paths": {"evidence": str(self.receipt_path)},
            "replay": replay,
        }
        self.receipt_path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding="utf-8")
        return receipt


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the isolated current CityNexus Harness")
    parser.add_argument("--scenario", choices=SCENARIOS, required=True)
    parser.add_argument("--replay", type=Path, help="load a previous receipt as replay input")
    parser.add_argument("--evidence-dir", type=Path, help="override the evidence output directory")
    args = parser.parse_args()
    replay = json.loads(args.replay.read_text(encoding="utf-8")) if args.replay else None
    run_id = str(uuid.uuid4())
    evidence_dir = args.evidence_dir or ROOT / "output" / "harness" / run_id
    receipt = Harness(evidence_dir, args.scenario, replay).run()
    print(json.dumps({"result": receipt["result"], "run_id": receipt["run_id"], "evidence": receipt["artifact_log_paths"]}, ensure_ascii=False))
    return 0 if receipt["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
