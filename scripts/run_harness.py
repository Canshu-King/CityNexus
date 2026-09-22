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
CAPABILITY_REVALIDATION_SCENARIO_ID = "capability-revalidation-replay"
ACTIVE_CAPABILITY_RECOVERY_SCENARIO_ID = "active-capability-recovery-replay"
RECOVERY_REPLACEMENT_SCENARIO_ID = "recovery-no-alternative-replacement-replay"
SCENARIOS = (
    SCENARIO_ID,
    C4_SCENARIO_ID,
    CAPABILITY_SCENARIO_ID,
    CAPABILITY_REVALIDATION_SCENARIO_ID,
    ACTIVE_CAPABILITY_RECOVERY_SCENARIO_ID,
    RECOVERY_REPLACEMENT_SCENARIO_ID,
)


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
        if scenario_id in {CAPABILITY_SCENARIO_ID, CAPABILITY_REVALIDATION_SCENARIO_ID, ACTIVE_CAPABILITY_RECOVERY_SCENARIO_ID, RECOVERY_REPLACEMENT_SCENARIO_ID}:
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
        self.findings: list[dict[str, Any]] = []

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
        # Reusing an evidence directory must still start from a genuinely clean
        # SQLite identity.  Removing only the main file can leave stale WAL/SHM
        # sidecars behind.
        for suffix in ("", "-wal", "-shm"):
            part = Path(str(self.db_path) + suffix)
            if part.exists():
                part.unlink()
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

    def _set_place_accessibility(
        self,
        evidence: dict[str, Any] | None,
        *,
        place_ids: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Apply a deterministic accessibility fixture inside the disposable DB.

        This is intentionally a HARNESS FIXTURE, not provider evidence.  The
        receipt must never describe this mutation as LIVE/provider-backed truth.
        """
        from app.db.models import Place
        from app.db.session import SessionLocal

        with SessionLocal() as session:
            query = session.query(Place)
            if place_ids:
                query = query.filter(Place.id.in_(list(dict.fromkeys(place_ids))))
            places = list(query.all())
            for place in places:
                metadata = json.loads(place.metadata_json or "{}")
                if evidence is None:
                    metadata.pop("accessibility", None)
                else:
                    metadata["accessibility"] = copy.deepcopy(evidence)
                place.metadata_json = json.dumps(metadata, ensure_ascii=False, sort_keys=True)
            session.commit()
        return self._place_evidence_states(place_ids=place_ids)

    def _place_evidence_states(
        self,
        *,
        place_ids: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        from app.capabilities import evaluate_accessibility_requirement
        from app.db.models import Place
        from app.db.session import SessionLocal

        with SessionLocal() as session:
            query = session.query(Place)
            if place_ids:
                query = query.filter(Place.id.in_(list(dict.fromkeys(place_ids))))
            rows = list(query.order_by(Place.id).all())
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

    @staticmethod
    def _confirmed_capability_semantics(payload: dict[str, Any], code: str) -> dict[str, Any]:
        items = payload.get("capabilities") if isinstance(payload, dict) else None
        items = items if isinstance(items, list) else []
        item = next((row for row in items if str(row.get("code") or "") == code), None)
        if not isinstance(item, dict):
            return {}
        return {
            "code": item.get("code"),
            "class": item.get("class"),
            "severity": item.get("severity"),
            "scope": item.get("scope"),
            "source": item.get("source"),
            "provenance": item.get("provenance"),
            "explicit": item.get("explicit"),
            "confirmed": item.get("confirmed"),
            "active": item.get("active"),
            "params": item.get("params"),
        }

    def _plan_status_snapshot(self, journey_id: str) -> list[dict[str, Any]]:
        """Read plan-version ownership truth from the disposable Harness DB."""
        from app.db.models import PlanVersion
        from app.db.session import SessionLocal
        from sqlalchemy import select

        with SessionLocal() as session:
            rows = list(
                session.scalars(
                    select(PlanVersion)
                    .where(PlanVersion.journey_id == journey_id)
                    .order_by(PlanVersion.version_no, PlanVersion.id)
                ).all()
            )
            return [
                {
                    "id": row.id,
                    "version_no": row.version_no,
                    "status": row.status,
                    "source": row.source,
                    "parent_plan_version_id": row.parent_plan_version_id,
                }
                for row in rows
            ]

    @staticmethod
    def _stable_plan_semantics(plan: dict[str, Any]) -> dict[str, Any]:
        """Normalize PlanVersion truth for no-silent-rewrite comparisons."""
        if not isinstance(plan, dict):
            return {}
        activity_fields = (
            "id",
            "sequence_no",
            "activity_type",
            "place_id",
            "city_service_id",
            "start_at",
            "end_at",
            "travel_from_prev_min",
            "estimated_cost",
            "currency",
            "status",
            "locked",
        )
        activities = []
        for item in plan.get("activities", []) or []:
            if isinstance(item, dict):
                activities.append({key: item.get(key) for key in activity_fields})
        return {
            "id": plan.get("id"),
            "journey_id": plan.get("journey_id"),
            "version_no": plan.get("version_no"),
            "planning_mode": plan.get("planning_mode"),
            "status": plan.get("status"),
            "source": plan.get("source"),
            "parent_plan_version_id": plan.get("parent_plan_version_id"),
            "total_cost": plan.get("total_cost"),
            "mobility_snapshot_id": plan.get("mobility_snapshot_id"),
            "activities": activities,
        }

    def _recovery_event_snapshot(self, journey_id: str) -> dict[str, Any] | None:
        """Read the durable recovery Event without changing product state."""
        from app.db.models import Event
        from app.db.session import SessionLocal
        from sqlalchemy import select

        with SessionLocal() as session:
            row = session.scalar(
                select(Event)
                .where(
                    Event.journey_id == journey_id,
                    Event.provider_key == "citynexus-capability-recovery",
                    Event.status.in_(("DETECTED", "ACKNOWLEDGED")),
                )
                .order_by(Event.detected_at.desc())
            )
            if row is None:
                return None
            try:
                payload = json.loads(row.payload_json or "{}")
            except json.JSONDecodeError:
                payload = {"__invalid_json__": row.payload_json}
            return {
                "id": row.id,
                "event_type": row.event_type,
                "provider_key": row.provider_key,
                "provenance": row.provenance,
                "severity": row.severity,
                "status": row.status,
                "detected_at": row.detected_at,
                "resolved_at": row.resolved_at,
                "payload": payload,
            }

    @staticmethod
    def _blocker_attribution(
        message: str,
        *,
        capability_code: str,
        place_ids: list[str],
    ) -> dict[str, Any]:
        """Measure only what the raw human-facing failure text actually says.

        The noun EVIDENCE inside a state such as NEEDS_LIVE_EVIDENCE is not a
        recovery action.  Actionability needs an action verb/phrase.
        """
        text = str(message or "")
        folded = text.casefold()
        names_capability = capability_code in text
        names_evidence_state = any(
            token in text
            for token in (
                "ACCESSIBILITY_UNVERIFIED",
                "ACCESSIBILITY_CONFLICT",
                "NEEDS_LIVE_EVIDENCE",
            )
        )
        named_places = sorted({place_id for place_id in place_ids if place_id and place_id in text})
        recovery_phrases = (
            "retry",
            "re-try",
            "revalidate",
            "re-validate",
            "verify ",
            "verify:",
            "refresh",
            "choose another",
            "choose a different",
            "replace ",
            "replan",
            "provide evidence",
            "supply evidence",
            "重试",
            "重新验证",
            "验证 ",
            "刷新",
            "重新规划",
            "更换",
            "另选",
            "提供证据",
        )
        has_recovery_action = any(token in folded for token in recovery_phrases)
        return {
            "names_capability": names_capability,
            "names_evidence_state": names_evidence_state,
            "named_place_ids": named_places,
            "has_recovery_action": has_recovery_action,
            "diagnosable": bool(
                names_capability
                and (names_evidence_state or named_places)
                and has_recovery_action
            ),
        }

    @classmethod
    def _structured_recovery_attribution(
        cls,
        failures: list[str],
        *,
        recovery: dict[str, Any] | None,
        capability_code: str,
        place_ids: list[str],
    ) -> dict[str, Any]:
        """Combine raw feasibility failures with the structured recovery contract.

        H5 already returns a machine recovery object containing capability_code
        and actions.  Do not falsely call that product contract unactionable
        merely because the raw failure strings are terse.
        """
        raw_text = " | ".join(str(item) for item in failures)
        raw = cls._blocker_attribution(
            raw_text,
            capability_code=capability_code,
            place_ids=place_ids,
        )
        recovery = recovery if isinstance(recovery, dict) else {}
        actions = [
            str(item)
            for item in recovery.get("actions", [])
            if str(item or "").strip()
        ]
        structured_capability = (
            str(recovery.get("capability_code") or "") == capability_code
        )
        structured_action = bool(actions)
        names_capability = bool(raw["names_capability"] or structured_capability)
        has_recovery_action = bool(raw["has_recovery_action"] or structured_action)
        diagnosable = bool(
            names_capability
            and (raw["names_evidence_state"] or raw["named_place_ids"])
            and has_recovery_action
        )
        return {
            **raw,
            "names_capability": names_capability,
            "has_recovery_action": has_recovery_action,
            "structured_capability_code": recovery.get("capability_code"),
            "structured_actions": actions,
            "structured_recovery_state": recovery.get("state"),
            "raw_text_diagnosable": raw["diagnosable"],
            "diagnosable": diagnosable,
        }

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
        actual_capability = self._confirmed_capability_semantics(after, capability["code"])
        self.record_assertion(
            "confirmed_capability_is_actual_hard_journey_truth",
            bool(actual_capability)
            and actual_capability.get("code") == capability["code"]
            and actual_capability.get("severity") == "HARD"
            and actual_capability.get("scope") == "JOURNEY"
            and actual_capability.get("confirmed") is True
            and actual_capability.get("active") is True,
            actual_capability,
        )

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
        self.record_assertion("unknown_is_not_accessible", blocked_status == 422, blocked)

        # Negative control: explicit inaccessibility must also fail closed.
        self.transition("EXECUTE:CONFLICT_EVIDENCE_GENERATION")
        conflict_evidence = self._set_place_accessibility(
            {"step_free": False, "wheelchair_access": False}
        )
        conflict = self.post(
            f"/api/v1/journeys/{journey_id}/plans/generate",
            {"candidate_count": self.input_payload["candidate_count"]},
        )
        conflict_status = self.last_status
        self.record_assertion(
            "conflicting_accessibility_blocks_plan",
            conflict_status == 422
            and bool(conflict_evidence)
            and all(item["state"] == "ACCESSIBILITY_CONFLICT" for item in conflict_evidence),
            {"status": conflict_status, "body": conflict, "states": conflict_evidence},
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
        generated_place_ids = sorted(
            {
                str(activity.get("place_id"))
                for plan in verified_plans
                for activity in plan.get("activities", [])
                if activity.get("place_id")
            }
        )
        verified_state_by_place = {item["place_id"]: item["state"] for item in verified_evidence}
        self.record_assertion(
            "generated_plan_places_have_verified_accessibility_fixture",
            bool(generated_place_ids)
            and all(
                verified_state_by_place.get(place_id) == "ACCESSIBILITY_VERIFIED"
                for place_id in generated_place_ids
            ),
            {"plan_place_ids": generated_place_ids, "states": verified_state_by_place},
        )

        attribution = self._blocker_attribution(
            blocked_message,
            capability_code=capability["code"],
            place_ids=[item["place_id"] for item in evidence_poor],
        )
        if not attribution["diagnosable"]:
            self.findings.append(
                {
                    "code": "CAPABILITY_BLOCKER_ATTRIBUTION_GAP",
                    "severity": "PRODUCT_RECOVERY_GAP",
                    "message": (
                        "Fail-closed behavior is correct, but the public blocker does not name "
                        "the HARD capability/evidence state/place plus a recovery action."
                    ),
                    "evidence": attribution,
                }
            )

        self.semantic_output = {
            "journey_lifecycle": ["RESET", "CAPABILITY_CONFIRMED"],
            "capability": actual_capability,
            "accessibility_evidence_mode": "SYNTHETIC_HARNESS_FIXTURE",
            "evidence_poor_states": sorted({item["state"] for item in evidence_poor}),
            "blocked_generation_status": blocked_status,
            "blocked_product_reason": blocked_message,
            "blocked_is_fail_closed": blocked_status == 422,
            "blocker_attribution": attribution,
            "conflict_evidence_states": sorted({item["state"] for item in conflict_evidence}),
            "conflict_generation_status": conflict_status,
            "verified_evidence_states": sorted({item["state"] for item in verified_evidence}),
            "verified_generation_status": generated_status,
            "verified_plan_count": len(verified_plans),
            "verified_selectable": verified_selectable,
            "verified_plan_place_ids": generated_place_ids,
        }
        self.transition(
            "CAPTURE_EVIDENCE",
            {
                "capabilities_before": before,
                "capabilities_after": after,
                "accessibility_evidence_mode": "SYNTHETIC_HARNESS_FIXTURE",
            },
        )
        self.transition("REPLAY_READY")

    def _run_capability_revalidation(self) -> None:
        """Prove HARD accessibility is revalidated beyond generation.

        A candidate that was feasible when generated must fail closed at
        selection/start if its currently-used place evidence becomes unknown.
        """
        self.transition("RESET")
        self.ids = self.post("/api/v1/demo/reset")
        self.record_assertion("reset_returns_journey", bool(self.ids.get("journey_id")), self.ids)
        journey_id = self.ids["journey_id"]
        capability = self.input_payload["capability"]
        payload = [
            {
                "code": capability["code"],
                "severity": capability["severity"],
                "params": capability["params"],
            }
        ]
        self.transition("EXECUTE:CAPABILITY_CONFIRMED")
        self.post(f"/api/v1/journeys/{journey_id}/capabilities/confirm", payload)
        after = self.get(f"/api/v1/journeys/{journey_id}/capabilities")
        actual_capability = self._confirmed_capability_semantics(after, capability["code"])
        self.record_assertion(
            "hard_capability_is_confirmed",
            bool(actual_capability)
            and actual_capability.get("severity") == "HARD"
            and actual_capability.get("scope") == "JOURNEY"
            and actual_capability.get("confirmed") is True,
            actual_capability,
        )

        self.transition("EXECUTE:GENERATE_WITH_VERIFIED_FIXTURE")
        self._set_place_accessibility(self.input_payload["verified_evidence"])
        plans = self.post(
            f"/api/v1/journeys/{journey_id}/plans/generate",
            {"candidate_count": self.input_payload["candidate_count"]},
        )
        generation_status = self.last_status
        self.record_assertion(
            "verified_candidate_generation_succeeds",
            generation_status == 201 and isinstance(plans, list) and bool(plans),
            plans,
        )
        plan = plans[0]
        plan_place_ids = sorted(
            {
                str(activity.get("place_id"))
                for activity in plan.get("activities", [])
                if activity.get("place_id")
            }
        )
        self.record_assertion("candidate_has_place_ids", bool(plan_place_ids), plan)
        journey_before_select = self.get(f"/api/v1/journeys/{journey_id}")
        plan_before_select = self.get(f"/api/v1/plans/{plan['id']}")

        # Invalidate exactly the concrete places consumed by this candidate,
        # not unrelated rows elsewhere in the fixture catalog.
        self.transition("MUTATE:USED_PLACE_EVIDENCE_UNKNOWN_BEFORE_SELECT")
        unknown_states = self._set_place_accessibility(None, place_ids=plan_place_ids)
        self.record_assertion(
            "used_places_are_now_unverified",
            bool(unknown_states)
            and all(item["state"] == "ACCESSIBILITY_UNVERIFIED" for item in unknown_states),
            unknown_states,
        )
        select_block = self.post(f"/api/v1/journeys/{journey_id}/plans/{plan['id']}/select")
        select_block_status = self.last_status
        journey_after_select_block = self.get(f"/api/v1/journeys/{journey_id}")
        plan_after_select_block = self.get(f"/api/v1/plans/{plan['id']}")
        self.record_assertion(
            "selection_revalidates_and_fails_closed",
            select_block_status in {409, 422}
            and journey_after_select_block.get("active_plan_version_id")
                == journey_before_select.get("active_plan_version_id")
            and journey_after_select_block.get("status") == journey_before_select.get("status")
            and plan_after_select_block.get("status") == plan_before_select.get("status")
            and plan_after_select_block.get("id") == plan_before_select.get("id"),
            {
                "status": select_block_status,
                "body": select_block,
                "before": journey_before_select,
                "after": journey_after_select_block,
                "journey_before": journey_before_select,
                "journey_after": journey_after_select_block,
                "plan_before": {"id": plan_before_select.get("id"), "status": plan_before_select.get("status")},
                "plan_after": {"id": plan_after_select_block.get("id"), "status": plan_after_select_block.get("status")},
            },
        )

        self.transition("RESTORE:USED_PLACE_EVIDENCE_BEFORE_SELECT")
        restored_select_states = self._set_place_accessibility(
            self.input_payload["verified_evidence"],
            place_ids=plan_place_ids,
        )
        selected = self.post(f"/api/v1/journeys/{journey_id}/plans/{plan['id']}/select")
        select_restore_status = self.last_status
        self.record_assertion(
            "selection_succeeds_after_evidence_restore",
            select_restore_status == 200
            and selected.get("active_plan_version_id") == plan["id"]
            and selected.get("status") == "PLANNED",
            selected,
        )

        journey_before_start = self.get(f"/api/v1/journeys/{journey_id}")
        plan_before_start = self.get(f"/api/v1/plans/{plan['id']}")
        self.transition("MUTATE:USED_PLACE_EVIDENCE_UNKNOWN_BEFORE_START")
        unknown_start_states = self._set_place_accessibility(None, place_ids=plan_place_ids)
        start_block = self.post(f"/api/v1/journeys/{journey_id}/start")
        start_block_status = self.last_status
        journey_after_start_block = self.get(f"/api/v1/journeys/{journey_id}")
        plan_after_start_block = self.get(f"/api/v1/plans/{plan['id']}")
        self.record_assertion(
            "start_revalidates_and_fails_closed",
            start_block_status in {409, 422}
            and journey_after_start_block.get("status") == journey_before_start.get("status")
            and journey_after_start_block.get("active_plan_version_id")
                == journey_before_start.get("active_plan_version_id")
            and journey_after_start_block.get("status") != "ACTIVE"
            and plan_after_start_block.get("status") == plan_before_start.get("status")
            and plan_after_start_block.get("id") == plan_before_start.get("id"),
            {
                "status": start_block_status,
                "body": start_block,
                "before": journey_before_start,
                "after": journey_after_start_block,
                "journey_before": journey_before_start,
                "journey_after": journey_after_start_block,
                "plan_before": {"id": plan_before_start.get("id"), "status": plan_before_start.get("status")},
                "plan_after": {"id": plan_after_start_block.get("id"), "status": plan_after_start_block.get("status")},
            },
        )

        self.transition("RESTORE:USED_PLACE_EVIDENCE_BEFORE_START")
        restored_start_states = self._set_place_accessibility(
            self.input_payload["verified_evidence"],
            place_ids=plan_place_ids,
        )
        started = self.post(f"/api/v1/journeys/{journey_id}/start")
        start_restore_status = self.last_status
        final_journey = self.get(f"/api/v1/journeys/{journey_id}")
        self.record_assertion(
            "start_succeeds_after_evidence_restore",
            start_restore_status == 200
            and started.get("projection_status") == "READY"
            and str((started.get("context") or {}).get("journey_status") or "") == "ACTIVE"
            and final_journey.get("status") == "ACTIVE"
            and final_journey.get("active_plan_version_id") == plan["id"],
            {"start": started, "journey": final_journey},
        )

        select_message = (
            str(select_block.get("error", {}).get("message") or select_block)
            if isinstance(select_block, dict)
            else str(select_block)
        )
        start_message = (
            str(start_block.get("error", {}).get("message") or start_block)
            if isinstance(start_block, dict)
            else str(start_block)
        )
        select_attribution = self._blocker_attribution(
            select_message, capability_code=capability["code"], place_ids=plan_place_ids
        )
        start_attribution = self._blocker_attribution(
            start_message, capability_code=capability["code"], place_ids=plan_place_ids
        )
        for stage, attribution, message in (
            ("SELECT", select_attribution, select_message),
            ("START", start_attribution, start_message),
        ):
            if not attribution.get("diagnosable"):
                self.findings.append(
                    {
                        "code": "CAPABILITY_LIFECYCLE_BLOCKER_ATTRIBUTION_GAP",
                        "severity": "PRODUCT_RECOVERY_GAP",
                        "stage": stage,
                        "message": "The lifecycle gate fails closed, but the blocker is not fully actionable for a user.",
                        "evidence": {"blocker": message, **attribution},
                    }
                )
        self.semantic_output = {
            "journey_lifecycle": ["RESET", "CAPABILITY_CONFIRMED", "CANDIDATE", "PLANNED", "ACTIVE"],
            "capability": actual_capability,
            "accessibility_evidence_mode": "SYNTHETIC_HARNESS_FIXTURE",
            "plan_place_ids": plan_place_ids,
            "generation_status": generation_status,
            "selection_unknown_states": sorted({item["state"] for item in unknown_states}),
            "selection_block_status": select_block_status,
            "selection_block_reason": select_message,
            "selection_block_attribution": select_attribution,
            "selection_restore_status": select_restore_status,
            "selection_restore_states": sorted({item["state"] for item in restored_select_states}),
            "start_unknown_states": sorted({item["state"] for item in unknown_start_states}),
            "start_block_status": start_block_status,
            "start_block_reason": start_message,
            "start_block_attribution": start_attribution,
            "start_restore_status": start_restore_status,
            "start_restore_states": sorted({item["state"] for item in restored_start_states}),
            "final_projection_status": started.get("projection_status"),
            "final_journey_status": final_journey.get("status"),
            "final_active_plan_version_id": final_journey.get("active_plan_version_id"),
        }
        self.transition("ASSERT", self.semantic_output)
        self.transition("CAPTURE_EVIDENCE")
        self.transition("REPLAY_READY")

    def _run_active_capability_recovery(self) -> None:
        """Prove a newly-confirmed HARD need invalidates an already-ACTIVE plan.

        H4 proves a known HARD capability is enforced at generate/select/start.
        H5 attacks a different stale-truth shape: the traveller changes their
        safety/accessibility requirement only after execution has begun.  The
        need must be accepted as truth, the current plan must be revalidated,
        durable recovery must open, acknowledgement must not resolve it, and a
        later evidence repair must close recovery only after revalidation.
        """
        self.transition("RESET")
        self.ids = self.post("/api/v1/demo/reset")
        self.record_assertion("reset_returns_journey", bool(self.ids.get("journey_id")), self.ids)
        journey_id = self.ids["journey_id"]
        capability = self.input_payload["capability"]

        # The negative arm must start without the HARD capability.  Keep the
        # fixture accessibility unknown so the active plan becomes infeasible
        # only when the traveller later confirms the requirement.
        initial_caps = self.get(f"/api/v1/journeys/{journey_id}/capabilities")
        initial_capability = self._confirmed_capability_semantics(initial_caps, capability["code"])
        self.record_assertion(
            "hard_capability_absent_before_execution",
            not bool(initial_capability),
            initial_caps,
        )
        initial_states = self._set_place_accessibility(None)
        self.record_assertion(
            "accessibility_unknown_before_execution",
            bool(initial_states)
            and all(item["state"] == "ACCESSIBILITY_UNVERIFIED" for item in initial_states),
            initial_states,
        )

        self.transition("EXECUTE:GENERATE_WITHOUT_HARD_CAPABILITY")
        plans = self.post(
            f"/api/v1/journeys/{journey_id}/plans/generate",
            {"candidate_count": self.input_payload["candidate_count"]},
        )
        generation_status = self.last_status
        self.record_assertion(
            "candidate_generation_without_hard_capability_succeeds",
            generation_status == 201 and isinstance(plans, list) and bool(plans),
            plans,
        )
        if not isinstance(plans, list) or not plans:
            raise RuntimeError("H5 requires one candidate before late capability confirmation")
        plan = plans[0]
        plan_id = str(plan["id"])
        plan_place_ids = sorted(
            {
                str(activity.get("place_id"))
                for activity in plan.get("activities", [])
                if activity.get("place_id")
            }
        )
        self.record_assertion("candidate_has_place_ids", bool(plan_place_ids), plan_place_ids)

        selected = self.post(f"/api/v1/journeys/{journey_id}/plans/{plan_id}/select")
        select_status = self.last_status
        self.record_assertion(
            "candidate_selects_before_late_hard_capability",
            select_status == 200
            and selected.get("status") == "PLANNED"
            and selected.get("active_plan_version_id") == plan_id,
            selected,
        )
        started = self.post(f"/api/v1/journeys/{journey_id}/start")
        start_status = self.last_status
        active_before = self.get(f"/api/v1/journeys/{journey_id}")
        plan_before = self.get(f"/api/v1/plans/{plan_id}")
        self.record_assertion(
            "journey_is_active_before_late_hard_capability",
            start_status == 200
            and started.get("projection_status") == "READY"
            and active_before.get("status") == "ACTIVE"
            and active_before.get("active_plan_version_id") == plan_id,
            {"start": started, "journey": active_before, "plan": plan_before},
        )

        self.transition("EXECUTE:CONFIRM_HARD_CAPABILITY_WHILE_ACTIVE")
        confirm_payload = [
            {
                "code": capability["code"],
                "severity": capability["severity"],
                "params": capability["params"],
            }
        ]
        confirmed = self.post(
            f"/api/v1/journeys/{journey_id}/capabilities/confirm", confirm_payload
        )
        confirm_status = self.last_status
        caps_after = self.get(f"/api/v1/journeys/{journey_id}/capabilities")
        actual_capability = self._confirmed_capability_semantics(caps_after, capability["code"])
        self.record_assertion(
            "late_hard_capability_is_accepted_and_persisted",
            confirm_status == 200
            and bool(actual_capability)
            and actual_capability.get("severity") == "HARD"
            and actual_capability.get("confirmed") is True
            and actual_capability.get("active") is True,
            {"confirm": confirmed, "persisted": actual_capability},
        )

        feasibility = confirmed.get("active_plan_feasibility") if isinstance(confirmed, dict) else None
        recovery = confirmed.get("recovery") if isinstance(confirmed, dict) else None
        failures = list(feasibility.get("failures") or []) if isinstance(feasibility, dict) else []
        failure_text = " | ".join(str(item) for item in failures)
        named_places = sorted({place_id for place_id in plan_place_ids if place_id in failure_text})
        self.record_assertion(
            "late_hard_capability_invalidates_active_plan",
            isinstance(feasibility, dict)
            and feasibility.get("passed") is False
            and str(feasibility.get("state") or "") == "REPLAN_REQUIRED"
            and bool(recovery)
            and "ACCESSIBILITY_UNVERIFIED" in failure_text
            and set(named_places) == set(plan_place_ids),
            {"feasibility": feasibility, "recovery": recovery, "named_place_ids": named_places},
        )

        active_after_confirm = self.get(f"/api/v1/journeys/{journey_id}")
        plan_after_confirm = self.get(f"/api/v1/plans/{plan_id}")
        self.record_assertion(
            "late_capability_does_not_silently_rewrite_active_plan",
            active_after_confirm.get("status") == active_before.get("status") == "ACTIVE"
            and active_after_confirm.get("active_plan_version_id") == plan_id
            and self._stable_plan_semantics(plan_after_confirm)
            == self._stable_plan_semantics(plan_before),
            {
                "journey_before": active_before,
                "journey_after": active_after_confirm,
                "plan_before": self._stable_plan_semantics(plan_before),
                "plan_after": self._stable_plan_semantics(plan_after_confirm),
            },
        )

        experience_open = self.get(f"/api/v1/journeys/{journey_id}/experience")
        flags_open = experience_open.get("experience_flags") if isinstance(experience_open, dict) else {}
        recovery_open = experience_open.get("recovery") if isinstance(experience_open, dict) else None
        self.record_assertion(
            "recovery_is_durable_and_user_visible",
            isinstance(flags_open, dict)
            and flags_open.get("needs_review") is True
            and flags_open.get("recovery_required") is True
            and bool(recovery_open),
            {"flags": flags_open, "recovery": recovery_open},
        )

        self.transition("EXECUTE:ACKNOWLEDGE_RECOVERY")
        acknowledged = self.post(f"/api/v1/journeys/{journey_id}/recovery/acknowledge")
        acknowledge_status = self.last_status
        experience_ack = self.get(f"/api/v1/journeys/{journey_id}/experience")
        flags_ack = experience_ack.get("experience_flags") if isinstance(experience_ack, dict) else {}
        recovery_ack = experience_ack.get("recovery") if isinstance(experience_ack, dict) else None
        self.record_assertion(
            "acknowledgement_does_not_resolve_infeasibility",
            acknowledge_status == 200
            and acknowledged.get("acknowledged") is True
            and acknowledged.get("resolved") is False
            and isinstance(flags_ack, dict)
            and flags_ack.get("needs_review") is True
            and flags_ack.get("recovery_required") is True
            and flags_ack.get("acknowledged") is True
            and bool(recovery_ack),
            {"acknowledge": acknowledged, "flags": flags_ack, "recovery": recovery_ack},
        )
        recovery_event_before_projection = self._recovery_event_snapshot(journey_id)

        self.transition("RESTORE:ACTIVE_PLAN_ACCESSIBILITY_EVIDENCE")
        restored_states = self._set_place_accessibility(
            self.input_payload["verified_evidence"], place_ids=plan_place_ids
        )
        # A projection read may observe that the plan is feasible again, but it
        # must not silently resolve the durable recovery event.  Resolution is
        # a transactional truth change, not a side effect of GET.
        experience_after_restore_before_reconfirm = self.get(
            f"/api/v1/journeys/{journey_id}/experience"
        )
        flags_before_reconfirm = (
            experience_after_restore_before_reconfirm.get("experience_flags")
            if isinstance(experience_after_restore_before_reconfirm, dict)
            else {}
        )
        recovery_before_reconfirm = (
            experience_after_restore_before_reconfirm.get("recovery")
            if isinstance(experience_after_restore_before_reconfirm, dict)
            else None
        )
        recovery_event_after_projection = self._recovery_event_snapshot(journey_id)
        self.record_assertion(
            "projection_read_does_not_resolve_durable_recovery",
            isinstance(flags_before_reconfirm, dict)
            and flags_before_reconfirm.get("needs_review") is True
            and flags_before_reconfirm.get("recovery_required") is True
            and bool(recovery_before_reconfirm)
            and recovery_event_before_projection is not None
            and recovery_event_after_projection == recovery_event_before_projection,
            {
                "flags": flags_before_reconfirm,
                "recovery": recovery_before_reconfirm,
                "event_before": recovery_event_before_projection,
                "event_after": recovery_event_after_projection,
            },
        )

        reconfirmed = self.post(
            f"/api/v1/journeys/{journey_id}/capabilities/confirm", confirm_payload
        )
        reconfirm_status = self.last_status
        restored_feasibility = (
            reconfirmed.get("active_plan_feasibility") if isinstance(reconfirmed, dict) else None
        )
        experience_resolved = self.get(f"/api/v1/journeys/{journey_id}/experience")
        flags_resolved = (
            experience_resolved.get("experience_flags")
            if isinstance(experience_resolved, dict)
            else {}
        )
        recovery_resolved = (
            experience_resolved.get("recovery")
            if isinstance(experience_resolved, dict)
            else None
        )
        final_journey = self.get(f"/api/v1/journeys/{journey_id}")
        self.record_assertion(
            "revalidation_resolves_recovery_only_after_evidence_restore",
            reconfirm_status == 200
            and isinstance(restored_feasibility, dict)
            and restored_feasibility.get("passed") is True
            and all(item["state"] == "ACCESSIBILITY_VERIFIED" for item in restored_states)
            and isinstance(flags_resolved, dict)
            and flags_resolved.get("needs_review") is False
            and flags_resolved.get("recovery_required") is False
            and (
                recovery_resolved is None
                or str((recovery_resolved or {}).get("state") or "").upper() == "RESOLVED"
            )
            and final_journey.get("status") == "ACTIVE"
            and final_journey.get("active_plan_version_id") == plan_id,
            {
                "reconfirm": reconfirmed,
                "flags": flags_resolved,
                "recovery": recovery_resolved,
                "journey": final_journey,
                "restored_states": restored_states,
            },
        )

        late_failure_attribution = self._structured_recovery_attribution(
            failures,
            recovery=recovery,
            capability_code=capability["code"],
            place_ids=plan_place_ids,
        )
        if not late_failure_attribution.get("diagnosable"):
            self.findings.append(
                {
                    "code": "ACTIVE_CAPABILITY_RECOVERY_ATTRIBUTION_GAP",
                    "severity": "PRODUCT_RECOVERY_GAP",
                    "message": "The active-plan recovery truth is correct, but its raw failure list is not a complete user recovery explanation.",
                    "evidence": {"failures": failures, **late_failure_attribution},
                }
            )

        self.semantic_output = {
            "journey_lifecycle": ["RESET", "CANDIDATE", "PLANNED", "ACTIVE", "RECOVERY_REQUIRED", "RECOVERY_ACKNOWLEDGED", "RECOVERY_RESOLVED"],
            "late_capability": actual_capability,
            "accessibility_evidence_mode": "SYNTHETIC_HARNESS_FIXTURE",
            "plan_place_ids": plan_place_ids,
            "generation_status": generation_status,
            "select_status": select_status,
            "start_status": start_status,
            "confirm_status": confirm_status,
            "active_plan_feasibility": {
                "passed": feasibility.get("passed") if isinstance(feasibility, dict) else None,
                "state": feasibility.get("state") if isinstance(feasibility, dict) else None,
                "failures": failures,
            },
            "late_failure_attribution": late_failure_attribution,
            "recovery_open": bool(recovery_open),
            "acknowledge_status": acknowledge_status,
            "acknowledged": bool(isinstance(flags_ack, dict) and flags_ack.get("acknowledged")),
            "read_after_restore_still_requires_recovery": bool(
                isinstance(flags_before_reconfirm, dict)
                and flags_before_reconfirm.get("recovery_required")
            ),
            "reconfirm_status": reconfirm_status,
            "restored_feasibility_passed": (
                restored_feasibility.get("passed")
                if isinstance(restored_feasibility, dict)
                else None
            ),
            "final_needs_review": (
                flags_resolved.get("needs_review") if isinstance(flags_resolved, dict) else None
            ),
            "final_recovery_required": (
                flags_resolved.get("recovery_required")
                if isinstance(flags_resolved, dict)
                else None
            ),
            "final_journey_status": final_journey.get("status"),
            "final_active_plan_version_id": final_journey.get("active_plan_version_id"),
        }
        self.transition("ASSERT", self.semantic_output)
        self.transition("CAPTURE_EVIDENCE")
        self.transition("REPLAY_READY")


    def _run_recovery_no_alternative_replacement(self) -> None:
        """Prove durable no-alternative truth and replacement-plan ownership.

        This scenario deliberately moves beyond H5's direct evidence restore.
        It forces an actual failed plan-generation attempt while recovery is
        open, then an actual feasible replacement generation/selection cycle.

        The load-bearing invariant is single authoritative plan ownership:
        changing recovery plans must never leave an old ACTIVE/SELECTED plan
        alongside the new authoritative plan.
        """
        self.transition("RESET")
        self.ids = self.post("/api/v1/demo/reset")
        self.record_assertion("reset_returns_journey", bool(self.ids.get("journey_id")), self.ids)
        journey_id = self.ids["journey_id"]
        capability = dict(self.input_payload["capability"])

        caps_before = self.get(f"/api/v1/journeys/{journey_id}/capabilities")
        self.record_assertion(
            "hard_capability_absent_before_execution",
            not any(
                str(item.get("code") or "") == capability["code"]
                and str(item.get("severity") or "").upper() == "HARD"
                for item in (caps_before.get("capabilities") or [])
            ),
            caps_before,
        )
        unknown_states = self._set_place_accessibility(None)
        self.record_assertion(
            "accessibility_unknown_before_execution",
            bool(unknown_states)
            and all(item["state"] == "ACCESSIBILITY_UNVERIFIED" for item in unknown_states),
            unknown_states,
        )

        initial_plans = self.post(
            f"/api/v1/journeys/{journey_id}/plans/generate",
            {"candidate_count": self.input_payload["candidate_count"]},
        )
        self.record_assertion(
            "initial_candidate_generation_succeeds_without_hard_capability",
            self.last_status == 201 and isinstance(initial_plans, list) and bool(initial_plans),
            initial_plans,
        )
        initial_plan = initial_plans[0]
        initial_plan_id = str(initial_plan["id"])
        used_place_ids = sorted(
            {
                str(activity.get("place_id"))
                for activity in initial_plan.get("activities", [])
                if activity.get("place_id")
            }
        )
        self.record_assertion("initial_candidate_has_place_ids", bool(used_place_ids), used_place_ids)

        selected = self.post(
            f"/api/v1/journeys/{journey_id}/plans/{initial_plan_id}/select"
        )
        self.record_assertion(
            "initial_candidate_selects",
            self.last_status == 200
            and selected.get("status") == "PLANNED"
            and selected.get("active_plan_version_id") == initial_plan_id,
            selected,
        )
        started = self.post(f"/api/v1/journeys/{journey_id}/start")
        active_before = self.get(f"/api/v1/journeys/{journey_id}")
        self.record_assertion(
            "initial_journey_is_active",
            self.last_status == 200
            and started.get("projection_status") == "READY"
            and active_before.get("status") == "ACTIVE"
            and active_before.get("active_plan_version_id") == initial_plan_id,
            {"start": started, "journey": active_before},
        )
        plans_before_recovery = self._plan_status_snapshot(journey_id)

        self.transition("EXECUTE:CONFIRM_HARD_CAPABILITY_WHILE_ACTIVE")
        confirm_payload = [
            {
                "code": capability["code"],
                "severity": capability["severity"],
                "params": capability["params"],
            }
        ]
        confirmed = self.post(
            f"/api/v1/journeys/{journey_id}/capabilities/confirm",
            confirm_payload,
        )
        feasibility = (
            confirmed.get("active_plan_feasibility")
            if isinstance(confirmed, dict)
            else None
        )
        recovery_open = confirmed.get("recovery") if isinstance(confirmed, dict) else None
        recovery_event_id = (
            str(recovery_open.get("event_id"))
            if isinstance(recovery_open, dict) and recovery_open.get("event_id")
            else ""
        )
        self.record_assertion(
            "late_hard_capability_opens_recovery",
            self.last_status == 200
            and isinstance(feasibility, dict)
            and feasibility.get("passed") is False
            and feasibility.get("state") == "REPLAN_REQUIRED"
            and isinstance(recovery_open, dict)
            and recovery_open.get("state") == "RECOVERY_REQUIRED"
            and bool(recovery_event_id),
            confirmed,
        )

        self.transition("EXECUTE:REPLAN_ATTEMPT_NO_ALTERNATIVE")
        failed_generation = self.post(
            f"/api/v1/journeys/{journey_id}/plans/generate",
            {"candidate_count": self.input_payload["candidate_count"]},
        )
        failed_generation_status = self.last_status
        experience_no_alt = self.get(
            f"/api/v1/journeys/{journey_id}/experience"
        )
        no_alt_recovery = (
            experience_no_alt.get("recovery")
            if isinstance(experience_no_alt, dict)
            else None
        )
        no_alt_flags = (
            experience_no_alt.get("experience_flags")
            if isinstance(experience_no_alt, dict)
            else {}
        )
        journey_no_alt = self.get(f"/api/v1/journeys/{journey_id}")
        plans_no_alt = self._plan_status_snapshot(journey_id)
        self.record_assertion(
            "failed_replan_attempt_persists_no_alternative_truth",
            failed_generation_status == 422
            and isinstance(no_alt_recovery, dict)
            and no_alt_recovery.get("event_id") == recovery_event_id
            and no_alt_recovery.get("state") == "RECOVERY_REQUIRED_NO_ALTERNATIVE"
            and no_alt_recovery.get("replan_attempted") is True
            and no_alt_recovery.get("no_alternative") is True
            and int(no_alt_recovery.get("candidate_plan_count") or 0) == 0
            and list(no_alt_recovery.get("candidate_plan_ids") or []) == []
            and isinstance(no_alt_flags, dict)
            and no_alt_flags.get("needs_review") is True
            and no_alt_flags.get("recovery_required") is True
            and journey_no_alt.get("status") == "ACTIVE"
            and journey_no_alt.get("active_plan_version_id") == initial_plan_id
            and plans_no_alt == plans_before_recovery,
            {
                "failed_generation": failed_generation,
                "recovery": no_alt_recovery,
                "flags": no_alt_flags,
                "journey": journey_no_alt,
                "plans": plans_no_alt,
            },
        )

        # Structured recovery attribution is the actual machine contract here.
        failures = list(no_alt_recovery.get("failures") or []) if isinstance(no_alt_recovery, dict) else []
        no_alt_attribution = self._structured_recovery_attribution(
            failures,
            recovery=no_alt_recovery,
            capability_code=capability["code"],
            place_ids=used_place_ids,
        )
        self.record_assertion(
            "no_alternative_recovery_contract_is_structurally_diagnosable",
            no_alt_attribution.get("diagnosable") is True,
            no_alt_attribution,
        )

        self.transition("RESTORE:ACCESSIBILITY_AND_GENERATE_REPLACEMENT")
        restored_states = self._set_place_accessibility(
            self.input_payload["verified_evidence"],
            place_ids=used_place_ids,
        )
        self.record_assertion(
            "used_places_restored_verified",
            bool(restored_states)
            and all(item["state"] == "ACCESSIBILITY_VERIFIED" for item in restored_states),
            restored_states,
        )
        replacement_plans = self.post(
            f"/api/v1/journeys/{journey_id}/plans/generate",
            {"candidate_count": self.input_payload["candidate_count"]},
        )
        replacement_generation_status = self.last_status
        self.record_assertion(
            "replacement_candidate_generation_succeeds",
            replacement_generation_status == 201
            and isinstance(replacement_plans, list)
            and bool(replacement_plans),
            replacement_plans,
        )
        replacement_plan = replacement_plans[0]
        replacement_plan_id = str(replacement_plan["id"])
        self.record_assertion(
            "replacement_candidate_is_new_plan",
            replacement_plan_id != initial_plan_id,
            {
                "initial_plan_id": initial_plan_id,
                "replacement_plan_id": replacement_plan_id,
            },
        )

        experience_candidate = self.get(
            f"/api/v1/journeys/{journey_id}/experience"
        )
        candidate_recovery = (
            experience_candidate.get("recovery")
            if isinstance(experience_candidate, dict)
            else None
        )
        candidate_flags = (
            experience_candidate.get("experience_flags")
            if isinstance(experience_candidate, dict)
            else {}
        )
        self.record_assertion(
            "candidate_availability_does_not_resolve_recovery_before_selection",
            isinstance(candidate_recovery, dict)
            and candidate_recovery.get("event_id") == recovery_event_id
            and candidate_recovery.get("state") == "RECOVERY_REQUIRED"
            and candidate_recovery.get("replan_attempted") is True
            and candidate_recovery.get("no_alternative") is False
            and replacement_plan_id in list(candidate_recovery.get("candidate_plan_ids") or [])
            and isinstance(candidate_flags, dict)
            and candidate_flags.get("recovery_required") is True
            and candidate_flags.get("needs_review") is True,
            {"recovery": candidate_recovery, "flags": candidate_flags},
        )

        self.transition("EXECUTE:SELECT_REPLACEMENT")
        selected_replacement = self.post(
            f"/api/v1/journeys/{journey_id}/plans/{replacement_plan_id}/select"
        )
        select_replacement_status = self.last_status
        journey_after_select = self.get(f"/api/v1/journeys/{journey_id}")
        plans_after_select = self._plan_status_snapshot(journey_id)
        experience_after_select = self.get(
            f"/api/v1/journeys/{journey_id}/experience"
        )
        flags_after_select = (
            experience_after_select.get("experience_flags")
            if isinstance(experience_after_select, dict)
            else {}
        )

        authoritative_statuses = [
            row for row in plans_after_select if row.get("status") in {"ACTIVE", "SELECTED"}
        ]
        referenced = next(
            (row for row in plans_after_select if row.get("id") == journey_after_select.get("active_plan_version_id")),
            None,
        )
        expected_status = (
            "ACTIVE"
            if journey_after_select.get("status") == "ACTIVE"
            else "SELECTED"
            if journey_after_select.get("status") == "PLANNED"
            else None
        )
        select_alignment_ok = bool(
            select_replacement_status == 200
            and journey_after_select.get("active_plan_version_id") == replacement_plan_id
            and journey_after_select.get("status") in {"PLANNED", "ACTIVE"}
            and isinstance(referenced, dict)
            and referenced.get("status") == expected_status
            and len(authoritative_statuses) == 1
            and authoritative_statuses[0].get("id") == replacement_plan_id
            and isinstance(flags_after_select, dict)
            and flags_after_select.get("recovery_required") is False
            and flags_after_select.get("needs_review") is False
        )
        self.assertions.append(
            {
                "name": "replacement_selection_has_single_authoritative_plan",
                "passed": select_alignment_ok,
                "details": _jsonable(
                    {
                        "selection": selected_replacement,
                        "journey": journey_after_select,
                        "plans": plans_after_select,
                        "authoritative_statuses": authoritative_statuses,
                        "experience_flags": flags_after_select,
                    }
                ),
            }
        )

        self.semantic_output = {
            "journey_lifecycle": [
                "RESET",
                "CANDIDATE",
                "PLANNED",
                "ACTIVE",
                "RECOVERY_REQUIRED",
                "RECOVERY_REQUIRED_NO_ALTERNATIVE",
                "RECOVERY_REQUIRED_WITH_CANDIDATE",
                "REPLACEMENT_SELECTED",
            ],
            "capability_code": capability["code"],
            "accessibility_evidence_mode": "SYNTHETIC_HARNESS_FIXTURE",
            "used_place_ids": used_place_ids,
            "failed_replan_status": failed_generation_status,
            "no_alternative_state": (
                no_alt_recovery.get("state")
                if isinstance(no_alt_recovery, dict)
                else None
            ),
            "no_alternative_replan_attempted": (
                no_alt_recovery.get("replan_attempted")
                if isinstance(no_alt_recovery, dict)
                else None
            ),
            "candidate_recovery_state": (
                candidate_recovery.get("state")
                if isinstance(candidate_recovery, dict)
                else None
            ),
            "candidate_plan_count": (
                candidate_recovery.get("candidate_plan_count")
                if isinstance(candidate_recovery, dict)
                else None
            ),
            "recovery_event_stable": bool(
                isinstance(candidate_recovery, dict)
                and candidate_recovery.get("event_id") == recovery_event_id
            ),
            "replacement_generation_status": replacement_generation_status,
            "replacement_select_status": select_replacement_status,
            "post_select_journey_status": journey_after_select.get("status"),
            "post_select_authoritative_plan_count": len(authoritative_statuses),
            "post_select_authoritative_statuses": [
                {
                    "version_no": row.get("version_no"),
                    "status": row.get("status"),
                    "is_replacement": row.get("id") == replacement_plan_id,
                }
                for row in authoritative_statuses
            ],
            "post_select_recovery_required": (
                flags_after_select.get("recovery_required")
                if isinstance(flags_after_select, dict)
                else None
            ),
        }
        self.transition("ASSERT:SELECT_OWNERSHIP", self.semantic_output)

        if not select_alignment_ok:
            raise AssertionError(
                "replacement_selection_has_single_authoritative_plan: "
                "replacement selection left stale ACTIVE/SELECTED plan ownership or unresolved recovery"
            )

        # A PLANNED replacement must be explicitly started; an implementation
        # that atomically keeps the Journey ACTIVE may skip this step.
        if journey_after_select.get("status") == "PLANNED":
            self.transition("EXECUTE:START_REPLACEMENT")
            replacement_start = self.post(
                f"/api/v1/journeys/{journey_id}/start"
            )
            self.record_assertion(
                "replacement_start_succeeds",
                self.last_status == 200
                and replacement_start.get("projection_status") == "READY",
                replacement_start,
            )

        final_journey = self.get(f"/api/v1/journeys/{journey_id}")
        final_plans = self._plan_status_snapshot(journey_id)
        final_authoritative = [
            row for row in final_plans if row.get("status") in {"ACTIVE", "SELECTED"}
        ]
        self.record_assertion(
            "final_active_plan_ownership_is_unique",
            final_journey.get("status") == "ACTIVE"
            and final_journey.get("active_plan_version_id") == replacement_plan_id
            and len(final_authoritative) == 1
            and final_authoritative[0].get("id") == replacement_plan_id
            and final_authoritative[0].get("status") == "ACTIVE",
            {
                "journey": final_journey,
                "plans": final_plans,
                "authoritative_statuses": final_authoritative,
            },
        )
        self.semantic_output["journey_lifecycle"].append("ACTIVE_REPLACEMENT")
        self.semantic_output["final_journey_status"] = final_journey.get("status")
        self.semantic_output["final_authoritative_plan_count"] = len(final_authoritative)
        self.semantic_output["final_authoritative_statuses"] = [
            {
                "version_no": row.get("version_no"),
                "status": row.get("status"),
                "is_replacement": row.get("id") == replacement_plan_id,
            }
            for row in final_authoritative
        ]
        self.transition("ASSERT:FINAL_OWNERSHIP", self.semantic_output)

        self.transition("CAPTURE_EVIDENCE")
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
            elif self.scenario_id == CAPABILITY_REVALIDATION_SCENARIO_ID:
                self._run_capability_revalidation()
            elif self.scenario_id == ACTIVE_CAPABILITY_RECOVERY_SCENARIO_ID:
                self._run_active_capability_recovery()
            elif self.scenario_id == RECOVERY_REPLACEMENT_SCENARIO_ID:
                self._run_recovery_no_alternative_replacement()
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
            "findings": self.findings,
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
