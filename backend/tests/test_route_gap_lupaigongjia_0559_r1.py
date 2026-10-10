"""ORD-0559 路牌工甲: the journeys-family doors in the a-to-m slice, one field at a time.

Every arm below asserts response fields, not just status codes.  The field names come from the
handlers on the authoritative tip this branch was cut from (`backend/app/main.py` and the payload
helpers it calls), and the coordinates are listed route by route in the delivery block.

Two doors in this family reach outside the process: the native Hermes run doors talk to the
configured loopback Hermes (`backend/app/integrations/hermes/native_client.py:35`), so those arms
start a real HTTP server on 127.0.0.1 and let the product's own client make a real round trip --
nothing inside the app is stubbed out.  Nothing here calls `POST /api/v1/demo/reset`, and the
database is the one `backend/tests/conftest.py` resolved for this run.
"""

from __future__ import annotations

import json
import threading
import uuid
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db import models as M
from app.db.session import SessionLocal
from app.integrations.hermes import native_client as hermes
from app.main import MAX_ADMINISTRATORS_PER_JOURNEY, app

client = TestClient(app, raise_server_exceptions=False)
NOW = datetime.now(timezone.utc)
MOMENT = NOW.isoformat()
START = (NOW + timedelta(days=200)).isoformat()
END = (NOW + timedelta(days=202)).isoformat()

ACL_PATH = "/api/v1/journeys/{j}/acl/roles"
LIMITS_PATH = "/api/v1/journeys/{j}/member-role-limits"
EXIT_PATH = "/api/v1/journeys/{j}/members/self-exit"
MULTIDAY_PATH = "/api/v1/journeys/{j}/multiday"
INBOX_PATH = "/api/v1/journeys/{j}/inbox"
AUTOPILOT_PATH = "/api/v1/journeys/{j}/guardian/autopilot/status"
RESILIENCE_PATH = "/api/v1/journeys/{j}/guardian/resilience"
REFRESH_PATH = "/api/v1/journeys/{j}/guardian/resilience/refresh"
FIXTURE_PATH = "/api/v1/journeys/{j}/guardian/signal-fixture"
CAPABILITIES_PATH = "/api/v1/journeys/{j}/capabilities"
CONFIRM_PATH = "/api/v1/journeys/{j}/capabilities/confirm"
IMPACT_PATH = "/api/v1/journeys/{j}/events/{e}/impact"
COMPOSE_PATH = "/api/v1/journeys/{j}/authoritative-compose"
RUN_PATH = "/api/v1/journeys/{j}/agent/hermes/runs/{r}"
TIMELINE_PATH = RUN_PATH + "/timeline"
EVENTS_PATH = RUN_PATH + "/events"
STOP_PATH = RUN_PATH + "/stop"


def _traveler(tag: str) -> str:
    ident = str(uuid.uuid4())
    with SessionLocal() as session:
        session.add(M.Traveler(id=ident, display_name=f"ORD-0559 路牌工甲 {tag}", email=None,
                               locale="zh-CN", timezone="Asia/Shanghai", created_at=MOMENT,
                               updated_at=MOMENT))
        session.commit()
    return ident


def _journey(tag: str, status: str = "PLANNED", **overrides) -> tuple[str, str]:
    traveler_id = overrides.pop("traveler_id", None) or _traveler(tag)
    ident = str(uuid.uuid4())
    fields = {
        "id": ident, "traveler_id": traveler_id, "title": f"沿海一周 {tag}",
        "city_code": "CN-XIAMEN", "timezone": "Asia/Shanghai", "start_at": START, "end_at": END,
        "budget_amount_minor": 120000, "budget_currency": "CNY", "status": status,
        "created_at": MOMENT, "updated_at": MOMENT,
    }
    fields.update(overrides)
    with SessionLocal() as session:
        session.add(M.Journey(**fields))
        session.commit()
    return ident, traveler_id


def _member(journey_id: str, traveler_id: str, role: str, invited_by: str,
            removed_at: str | None = None) -> str:
    ident = str(uuid.uuid4())
    with SessionLocal() as session:
        session.add(M.JourneyMember(id=ident, journey_id=journey_id, traveler_id=traveler_id,
                                    role=role, invited_by=invited_by, expires_at=None,
                                    joined_at=MOMENT, removed_at=removed_at, created_at=MOMENT,
                                    updated_at=MOMENT))
        session.commit()
    return ident


def _error(body: dict) -> dict:
    return body.get("error") or {}


# --------------------------------------------------------------------------- native Hermes door
class _StubHandler(BaseHTTPRequestHandler):
    def log_message(self, *args) -> None:
        pass

    def _send(self, code: int, body: bytes, content_type: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _record(self) -> None:
        STATE = self.server.state
        STATE["requests"].append({
            "method": self.command,
            "path": self.path,
            "authorization": self.headers.get("Authorization"),
        })

    def do_GET(self) -> None:
        self._record()
        STATE = self.server.state
        if STATE["mode"] == "down":
            self._send(503, b"{}", "application/json")
            return
        if self.path.endswith("/events"):
            run_id = STATE["run_id"]
            frames = "".join(
                f"event: {name}\ndata: {json.dumps(payload)}\n\n"
                for name, payload in STATE["frames"](run_id)
            )
            self._send(200, frames.encode(), "text/event-stream")
            return
        self._send(200, json.dumps(STATE["run_status"](self.path)).encode(), "application/json")

    def do_POST(self) -> None:
        self._record()
        STATE = self.server.state
        if STATE["mode"] == "down":
            self._send(503, b"{}", "application/json")
            return
        self._send(200, json.dumps(STATE["stop_answer"](self.path)).encode(), "application/json")


@contextmanager
def _serve(state: dict):
    server = ThreadingHTTPServer(("127.0.0.1", 0), _StubHandler)
    server.state = state
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}"
    finally:
        server.shutdown()
        server.server_close()


def _run_status_terminal(path: str) -> dict:
    return {"run_id": path.rsplit("/", 1)[-1], "status": "completed",
            "last_event": "run.completed", "updated_at": MOMENT, "steps": 3}


def _default_frames(run_id: str):
    return [
        ("run.started", {"run_id": run_id, "status": "running", "source": "HERMES_NATIVE",
                         "timestamp": MOMENT}),
        ("tool.started", {"run_id": run_id, "status": "running", "source": "HERMES_NATIVE",
                          "tool_name": "probe.tool", "duration_ms": 120, "timestamp": MOMENT,
                          "result_summary": {"mission_id": "mission-probe"}}),
        ("run.completed", {"run_id": run_id, "status": "completed", "source": "HERMES_NATIVE",
                           "timestamp": MOMENT}),
    ]


# --------------------------------------------------------------------------- acl/roles
def test_acl_roles_answers_the_seeded_role_table_field_by_field():
    journey_id, _ = _journey("acl")
    with SessionLocal() as session:
        rows = session.scalars(select(M.JourneyRoleCapability).order_by(
            M.JourneyRoleCapability.role, M.JourneyRoleCapability.capability)).all()
    expected: dict[str, list[str]] = {}
    scope_keys: dict[str, str] = {}
    for row in rows:
        expected.setdefault(row.role, []).append(row.capability)
        scope_keys[row.role] = row.scope_message_key

    answer = client.get(ACL_PATH.format(j=journey_id))
    assert answer.status_code == 200, answer.text
    body = answer.json()
    assert isinstance(body, list)
    assert [item["role"] for item in body] == sorted(expected)
    for item in body:
        assert set(item) == {"role", "capabilities", "scope_message_key"}, sorted(item)
        assert item["capabilities"] == sorted(expected[item["role"]])
        assert item["scope_message_key"] == scope_keys[item["role"]]
        assert item["capabilities"], item


def test_acl_roles_on_an_unknown_journey_names_the_missing_resource():
    answer = client.get(ACL_PATH.format(j=str(uuid.uuid4())))
    assert answer.status_code == 404, answer.text
    error = _error(answer.json())
    assert error["code"] == "NOT_FOUND"
    assert error["message_key"] == "resource.not_found"
    assert error["error_receipt_id"], error
    assert "was not found" in error["message"], error["message"]


# --------------------------------------------------------------------------- member-role-limits
def test_member_role_limits_answers_the_same_cap_the_role_door_enforces():
    journey_id, owner = _journey("limits")
    answer = client.get(LIMITS_PATH.format(j=journey_id))
    assert answer.status_code == 200, answer.text
    body = answer.json()
    assert set(body) == {"max_administrators", "admin_count_in_force", "roles"}
    assert body["max_administrators"] == MAX_ADMINISTRATORS_PER_JOURNEY
    assert body["admin_count_in_force"] == 0
    assert body["roles"] == ["OWNER", "ADMIN", "COLLABORATOR"]

    _member(journey_id, _traveler("limits-admin"), "ADMIN", invited_by=owner)
    after = client.get(LIMITS_PATH.format(j=journey_id)).json()
    assert after["admin_count_in_force"] == 1
    assert after["max_administrators"] == body["max_administrators"]


def test_member_role_limits_counts_a_lapsed_seat_out():
    journey_id, owner = _journey("limits-lapsed")
    lapsed = (NOW - timedelta(days=2)).isoformat()
    _member(journey_id, _traveler("lapsed-admin"), "ADMIN", invited_by=owner, removed_at=None)
    with SessionLocal() as session:
        row = session.scalar(select(M.JourneyMember).where(
            M.JourneyMember.journey_id == journey_id))
        row.expires_at = lapsed
        session.commit()
    body = client.get(LIMITS_PATH.format(j=journey_id)).json()
    assert body["admin_count_in_force"] == 0, body


# --------------------------------------------------------------------------- members/self-exit
def test_self_exit_returns_the_row_read_back_and_writes_only_its_own_seat():
    journey_id, owner = _journey("exit")
    leaver = _traveler("leaver")
    member_id = _member(journey_id, leaver, "COLLABORATOR", invited_by=owner)
    owner_member_id = _member(journey_id, owner, "OWNER", invited_by=owner)

    answer = client.post(EXIT_PATH.format(j=journey_id), json={"traveler_id": leaver})
    assert answer.status_code == 200, answer.text
    body = answer.json()
    assert set(body) == {"id", "journey_id", "traveler_id", "role", "invited_by", "expires_at",
                         "joined_at", "removed_at", "created_at", "updated_at", "member_state"}
    assert body["id"] == member_id
    assert body["traveler_id"] == leaver
    assert body["role"] == "COLLABORATOR"
    assert body["invited_by"] == owner
    assert body["member_state"] == "MEMBER_WITHDRAWN"
    assert body["joined_at"] == MOMENT
    assert body["removed_at"] == body["updated_at"]

    with SessionLocal() as session:
        row = session.get(M.JourneyMember, member_id)
        assert row.removed_at == body["removed_at"]
        untouched_owner = session.get(M.JourneyMember, owner_member_id)
        assert untouched_owner.removed_at is None
        audit = session.scalars(select(M.AuditLog).where(
            M.AuditLog.action == "member.self_exited",
            M.AuditLog.entity_id == member_id)).all()
    assert len(audit) == 1
    assert json.loads(audit[0].after_json)["removed_at"] == body["removed_at"]


def test_self_exit_refusals_answer_with_their_own_reason_code_and_details():
    journey_id, owner = _journey("exit-refusals")
    stranger = str(uuid.uuid4())

    not_a_member = client.post(EXIT_PATH.format(j=journey_id), json={"traveler_id": stranger})
    assert not_a_member.status_code == 404, not_a_member.text
    error = _error(not_a_member.json())
    assert error["code"] == "NOT_FOUND"
    assert error["reason_code"] == "MEMBER_SELF_EXIT_NOT_A_MEMBER"
    assert error["details"] == {"field": "traveler_id", "journey_id": journey_id}

    owner_member_id = _member(journey_id, owner, "OWNER", invited_by=owner)
    owner_exit = client.post(EXIT_PATH.format(j=journey_id), json={"traveler_id": owner})
    assert owner_exit.status_code == 409, owner_exit.text
    owner_error = _error(owner_exit.json())
    assert owner_error["reason_code"] == "MEMBER_OWNER_CANNOT_LEAVE"
    assert owner_error["details"]["member_id"] == owner_member_id
    assert owner_error["details"]["journey_id"] == journey_id
    assert owner_error["message_key"] == "request.conflict"

    leaver = _traveler("twice-leaver")
    leaver_member = _member(journey_id, leaver, "ADMIN", invited_by=owner)
    first = client.post(EXIT_PATH.format(j=journey_id), json={"traveler_id": leaver})
    assert first.status_code == 200, first.text
    second = client.post(EXIT_PATH.format(j=journey_id), json={"traveler_id": leaver})
    assert second.status_code == 409, second.text
    again = _error(second.json())
    assert again["reason_code"] == "MEMBER_ALREADY_WITHDRAWN"
    assert again["details"]["member_id"] == leaver_member
    assert again["details"]["removed_at"] == first.json()["removed_at"]


def test_self_exit_body_takes_no_member_id_field():
    journey_id, owner = _journey("exit-shape")
    answer = client.post(EXIT_PATH.format(j=journey_id),
                         json={"traveler_id": owner, "member_id": str(uuid.uuid4())})
    assert answer.status_code == 422, answer.text
    error = _error(answer.json())
    assert error["code"] == "VALIDATION_ERROR"
    assert error["message_key"] == "request.invalid"
    locations = [tuple(item["loc"]) for item in error["details"]["errors"]]
    assert any("member_id" in loc for loc in locations), locations


# --------------------------------------------------------------------------- multiday
def test_multiday_places_the_window_and_the_day_count_the_pricer_uses():
    journey_id, traveler_id = _journey("multiday", start_at=START, end_at=END)
    answer = client.get(MULTIDAY_PATH.format(j=journey_id))
    assert answer.status_code == 200, answer.text
    body = answer.json()
    assert set(body) == {"active_plan", "journey", "mobility_facts", "offers", "options",
                         "provider_mesh", "selected_option_id", "traveler_twin", "trip"}
    journey = body["journey"]
    assert journey["id"] == journey_id
    assert journey["traveler_id"] == traveler_id
    assert journey["city_code"] == "CN-XIAMEN"
    assert journey["timezone"] == "Asia/Shanghai"
    assert journey["used_timezone"] == "Asia/Shanghai"
    assert journey["timezone_honoured"] is True
    assert journey["status"] == "PLANNED"
    assert journey["active_plan_version_id"] is None
    assert journey["budget"] == {"amount_minor": 120000, "currency": "CNY"}
    assert set(journey["temporal_shape"]) == {"day_count", "max_days", "min_days", "night_count",
                                             "semantics", "window_status"}
    assert journey["temporal_shape"]["day_count"] == 3
    assert body["active_plan"] is None
    assert body["selected_option_id"] is None
    assert body["offers"] == [] and body["options"] == [] and body["mobility_facts"] == []
    assert set(body["provider_mesh"]) == {"accommodation", "mobility"}
    assert body["traveler_twin"]["authority"] == "soft_planning_input_only"
    assert set(body["traveler_twin"]) == {"authority", "capability_summary", "explicit_capabilities",
                                         "explicit_dimensions", "learned_soft_dimensions"}
    assert body["trip"]["party_size"] == 1


def test_multiday_on_an_unknown_journey_is_a_named_absence():
    answer = client.get(MULTIDAY_PATH.format(j=str(uuid.uuid4())))
    assert answer.status_code == 404, answer.text
    error = _error(answer.json())
    assert error["code"] == "NOT_FOUND"
    assert error["message_key"] == "resource.not_found"


# --------------------------------------------------------------------------- inbox
def test_inbox_hands_back_the_draft_with_its_interpretation_split_out():
    journey_id, _ = _journey("inbox")
    empty = client.get(INBOX_PATH.format(j=journey_id))
    assert empty.status_code == 200, empty.text
    assert empty.json() == {"journey_id": journey_id, "drafts": []}

    draft_id = str(uuid.uuid4())
    extracted = {"anchor_role": "OUTBOUND", "anchor_role_confidence": 0.8,
                 "semantic_target": "Xiamen North", "payment_status": "PAID",
                 "reasoning_summary": "ord0559 probe", "smart_intake": {"channel": "text"}}
    with SessionLocal() as session:
        session.add(M.ExternalReservationDraft(
            id=draft_id, journey_id=journey_id, artifact_type="TRAIN_TICKET",
            raw_payload_json="{}", extracted_json=json.dumps(extracted),
            unresolved_fields_json=json.dumps(["date"]), extraction_mode="TEXT", status="DRAFT",
            created_at=MOMENT, confirmed_at=None))
        session.commit()

    answer = client.get(INBOX_PATH.format(j=journey_id))
    drafts = answer.json()["drafts"]
    assert len(drafts) == 1
    draft = drafts[0]
    assert set(draft) == {"id", "journey_id", "artifact_type", "extracted", "interpretation",
                          "smart_intake", "unresolved_fields", "extraction_mode", "status",
                          "created_at", "confirmed_at"}
    assert draft["id"] == draft_id
    assert draft["interpretation"] == {
        "anchor_role": "OUTBOUND", "anchor_role_confidence": 0.8,
        "semantic_target": "Xiamen North", "payment_status": "PAID",
        "reasoning_summary": "ord0559 probe"}
    assert draft["smart_intake"] == {"channel": "text"}
    assert draft["unresolved_fields"] == ["date"]
    assert draft["status"] == "DRAFT" and draft["confirmed_at"] is None
    assert draft["extracted"] == extracted


def test_inbox_keeps_drafts_of_this_journey_only():
    journey_id, _ = _journey("inbox-scope")
    other_id, _ = _journey("inbox-other")
    with SessionLocal() as session:
        session.add(M.ExternalReservationDraft(
            id=str(uuid.uuid4()), journey_id=other_id, artifact_type="HOTEL_VOUCHER",
            raw_payload_json="{}", extracted_json="{}", unresolved_fields_json="[]",
            extraction_mode="TEXT", status="DRAFT", created_at=MOMENT, confirmed_at=None))
        session.commit()
    body = client.get(INBOX_PATH.format(j=journey_id)).json()
    assert body["journey_id"] == journey_id
    assert body["drafts"] == []


# --------------------------------------------------------------------------- guardian autopilot
def test_autopilot_status_separates_the_enrollment_row_from_the_worker():
    from app.agent.autorun import autorun_status

    journey_id, _ = _journey("autopilot")
    naked = client.get(AUTOPILOT_PATH.format(j=journey_id))
    assert naked.status_code == 200, naked.text
    body = naked.json()
    assert body["enrollment"] is None
    assert body["journey_id"] == journey_id
    worker = autorun_status()
    assert set(body) == set(worker) | {"journey_id", "enrollment"}
    assert body["interval_seconds"] == worker["interval_seconds"]
    assert body["signal_provider"] == worker["signal_provider"]

    with SessionLocal() as session:
        session.add(M.AutopilotEnrollment(
            journey_id=journey_id, enabled=True, interval_seconds=45.0,
            provider_mesh_json=json.dumps({"mesh": "ord0559"}), last_pulse_at=MOMENT,
            last_error=None, created_at=MOMENT, updated_at=MOMENT))
        session.commit()

    enrolled = client.get(AUTOPILOT_PATH.format(j=journey_id)).json()
    assert set(enrolled["enrollment"]) == {"journey_id", "enabled", "interval_seconds",
                                          "provider_mesh", "last_pulse_at", "last_error"}
    assert enrolled["enrollment"]["journey_id"] == journey_id
    assert enrolled["enrollment"]["enabled"] is True
    assert enrolled["enrollment"]["interval_seconds"] == 45.0
    assert enrolled["enrollment"]["provider_mesh"] == {"mesh": "ord0559"}
    assert enrolled["enrollment"]["last_pulse_at"] == MOMENT
    assert enrolled["enrollment"]["last_error"] is None
    assert journey_id in enrolled["enrolled_journey_ids"]
    assert enrolled["interval_seconds"] != enrolled["enrollment"]["interval_seconds"]


# --------------------------------------------------------------------------- guardian resilience
def test_resilience_get_builds_once_and_then_answers_with_the_stored_snapshot():
    journey_id, _ = _journey("resilience")
    answer = client.get(RESILIENCE_PATH.format(j=journey_id))
    assert answer.status_code == 200, answer.text
    body = answer.json()
    assert set(body) == {"id", "journey_id", "score", "risk_score", "status", "captured_at",
                         "expires_at", "components", "activity_risks", "commitment_buffers",
                         "dominant_failure_modes", "preventive_recommendation",
                         "evidence_provenance", "fingerprint"}
    assert body["journey_id"] == journey_id
    assert body["score"] == body["risk_score"]
    assert set(body["components"]) == {"commitment_slack", "cost_headroom_minor", "forecast_risk",
                                      "mobility_sensitivity", "recovery_optionality",
                                      "route_geography_exposure", "single_point_of_failure",
                                      "weather_exposure"}
    assert set(body["preventive_recommendation"]) == {"action", "reason", "reversible",
                                                     "risk_reduction_meaningful",
                                                     "target_activity_id", "threshold"}
    assert body["fingerprint"]

    again = client.get(RESILIENCE_PATH.format(j=journey_id)).json()
    assert again["id"] == body["id"]
    assert again["captured_at"] == body["captured_at"]


def test_resilience_refresh_answers_the_snapshot_the_counterfactuals_were_run_against():
    journey_id, _ = _journey("refresh")
    answer = client.post(REFRESH_PATH.format(j=journey_id), json={"mode": "replay"})
    assert answer.status_code == 200, answer.text
    body = answer.json()
    assert set(body) == {"snapshot", "counterfactuals", "discovery"}
    assert body["discovery"] is None
    assert body["snapshot"]["journey_id"] == journey_id
    assert body["counterfactuals"], body
    for item in body["counterfactuals"]:
        assert set(item) >= {"id", "journey_id", "snapshot_id", "scenario_key", "scenario_type",
                             "parameters", "answered", "feasible", "c4_preserved",
                             "cost_delta_minor", "schedule_drift_min", "plan_changes", "evidence",
                             "created_at"}
        assert item["snapshot_id"] == body["snapshot"]["id"]
        assert item["journey_id"] == journey_id
    keys = [item["scenario_key"] for item in body["counterfactuals"]]
    assert len(keys) == len(set(keys))


def test_resilience_refresh_live_mode_reports_the_provider_answer_it_actually_got():
    journey_id, _ = _journey("refresh-live")
    answer = client.post(REFRESH_PATH.format(j=journey_id), json={"mode": "live"})
    assert answer.status_code == 200, answer.text
    discovery = answer.json()["discovery"]
    assert set(discovery) >= {"journey_id", "city_code", "mode", "provenance", "candidates",
                              "captured_at", "expires_at", "provider_status", "provider_evidence"}
    assert discovery["journey_id"] == journey_id
    assert discovery["mode"] == "live-unavailable"
    assert discovery["provenance"] == "LIVE_PROVIDER"
    assert discovery["candidates"] == []
    assert discovery["provider_status"]["fallback_reason"] == "REAL_CITY_DISABLED"
    assert discovery["provider_status"]["counts_as_supply"] is False
    assert discovery["provider_evidence"]["weather"] is None


def test_resilience_refresh_refuses_a_mode_the_product_does_not_have():
    journey_id, _ = _journey("refresh-bogus")
    answer = client.post(REFRESH_PATH.format(j=journey_id), json={"mode": "sideways"})
    assert answer.status_code == 422, answer.text
    error = _error(answer.json())
    assert error["code"] == "VALIDATION_ERROR"
    assert error["message_key"] == "request.invalid"
    first = error["details"]["errors"][0]
    assert tuple(first["loc"]) == ("body", "mode")
    assert first["message_key"], first


# --------------------------------------------------------------------------- signal fixture
def test_signal_fixture_writes_the_state_and_answers_the_revision_it_stored():
    journey_id, _ = _journey("fixture")
    first = client.post(FIXTURE_PATH.format(j=journey_id),
                        json={"state": "NORMAL", "payload": {"note": "one"}})
    assert first.status_code == 200, first.text
    body = first.json()
    assert set(body) == {"journey_id", "provider_key", "state", "revision", "payload",
                         "updated_at"}
    assert body["journey_id"] == journey_id
    assert body["provider_key"] == "city-signal-fixture"
    assert body["state"] == "NORMAL"
    assert body["revision"] == 1
    assert body["payload"] == {"note": "one"}

    second = client.post(FIXTURE_PATH.format(j=journey_id),
                         json={"state": "RISK_FORECAST", "payload": {"note": "two"}}).json()
    assert second["revision"] == 2
    assert second["state"] == "RISK_FORECAST"
    assert second["payload"] == {"note": "two"}

    with SessionLocal() as session:
        row = session.scalar(select(M.CitySignalFixture).where(
            M.CitySignalFixture.journey_id == journey_id))
        assert row.state == "RISK_FORECAST" and row.revision == 2
        audit = session.scalars(select(M.AuditLog).where(
            M.AuditLog.action == "city.signal.fixture.updated",
            M.AuditLog.journey_id == journey_id)).all()
    assert len(audit) == 2
    assert json.loads(audit[-1].after_json)["revision"] == 2


def test_signal_fixture_state_vocabulary_is_closed():
    journey_id, _ = _journey("fixture-bogus")
    answer = client.post(FIXTURE_PATH.format(j=journey_id), json={"state": "SIDEWAYS",
                                                                 "payload": {}})
    assert answer.status_code == 422, answer.text
    error = _error(answer.json())
    assert error["code"] == "VALIDATION_ERROR"
    assert tuple(error["details"]["errors"][0]["loc"]) == ("body", "state")


# --------------------------------------------------------------------------- capabilities doors
def test_capabilities_put_answers_the_row_summary_and_twin_it_just_wrote():
    journey_id, traveler_id = _journey("caps-put")
    answer = client.put(CAPABILITIES_PATH.format(j=journey_id), json=[
        {"code": "MAX_WALKING_PER_LEG_M", "class": "CARE_REQUIREMENT", "severity": "SOFT",
         "params": {"meters": 400}}])
    assert answer.status_code == 200, answer.text
    body = answer.json()
    assert set(body) == {"journey_id", "capabilities", "summary", "traveler_twin"}
    assert body["journey_id"] == journey_id
    assert len(body["capabilities"]) == 1
    row = body["capabilities"][0]
    assert row["code"] == "MAX_WALKING_PER_LEG_M"
    assert row["severity"] == "SOFT"
    assert row["scope"] == "JOURNEY"
    assert row["journey_id"] == journey_id
    assert row["traveler_id"] == traveler_id
    assert row["params"] == {"meters": 400}
    assert row["active"] is True and row["explicit"] is True
    assert set(body["summary"]) == {"items", "hard", "strong", "soft",
                                   "unknown_accessibility_is_not_accessible"}
    assert [item["code"] for item in body["summary"]["soft"]] == ["MAX_WALKING_PER_LEG_M"]
    assert body["summary"]["hard"] == [] and body["summary"]["strong"] == []
    assert body["summary"]["unknown_accessibility_is_not_accessible"] is True
    assert body["traveler_twin"]["traveler_id"] == traveler_id

    replaced_answer = client.put(CAPABILITIES_PATH.format(j=journey_id), json=[
        {"code": "QUIET_ENVIRONMENT", "class": "SOFT_PREFERENCE", "severity": "SOFT",
         "params": {}}])
    assert replaced_answer.status_code == 200, replaced_answer.text
    replaced = replaced_answer.json()
    assert [item["code"] for item in replaced["capabilities"]] == ["QUIET_ENVIRONMENT"]
    assert [item["code"] for item in replaced["summary"]["soft"]] == ["QUIET_ENVIRONMENT"]


def test_capabilities_put_refuses_a_hard_accessibility_class_declared_soft():
    journey_id, _ = _journey("caps-class")
    seed = client.put(CAPABILITIES_PATH.format(j=journey_id), json=[
        {"code": "MAX_WALKING_PER_LEG_M", "class": "CARE_REQUIREMENT", "severity": "SOFT",
         "params": {"meters": 600}}])
    assert seed.status_code == 200, seed.text

    answer = client.put(CAPABILITIES_PATH.format(j=journey_id), json=[
        {"code": "AVOID_STAIRS", "class": "HARD_ACCESSIBILITY_NEED", "severity": "SOFT",
         "params": {}}])
    assert answer.status_code == 409, answer.text
    error = _error(answer.json())
    assert error["code"] == "CONFLICT"
    assert "/confirm" in error["message"], error["message"]

    still = client.get(f"/api/v1/journeys/{journey_id}/capabilities").json()
    assert [item["code"] for item in still["capabilities"]] == ["MAX_WALKING_PER_LEG_M"]
    confirmed = client.post(CONFIRM_PATH.format(j=journey_id), json=[
        {"code": "AVOID_STAIRS", "class": "HARD_ACCESSIBILITY_NEED", "severity": "SOFT",
         "params": {}}])
    assert confirmed.status_code == 200, confirmed.text
    severities = {item["code"]: item["severity"] for item in confirmed.json()["capabilities"]}
    assert severities["AVOID_STAIRS"] == "HARD"


def test_capabilities_put_refuses_a_hard_row_that_was_never_confirmed():
    journey_id, _ = _journey("caps-hard")
    answer = client.put(CAPABILITIES_PATH.format(j=journey_id), json=[
        {"code": "STEP_FREE_REQUIRED", "class": "HARD_ACCESSIBILITY_NEED", "severity": "HARD",
         "params": {}}])
    assert answer.status_code == 409, answer.text
    error = _error(answer.json())
    assert error["code"] == "CONFLICT"
    assert error["message_key"] == "request.conflict"
    assert "/confirm" in error["message"], error["message"]
    still = client.get(f"/api/v1/journeys/{journey_id}/capabilities").json()
    assert still["capabilities"] == []


def test_capabilities_confirm_marks_the_hard_row_and_answers_the_feasibility_slot():
    journey_id, _ = _journey("caps-confirm")
    answer = client.post(CONFIRM_PATH.format(j=journey_id), json=[
        {"code": "STEP_FREE_REQUIRED", "class": "HARD_ACCESSIBILITY_NEED", "severity": "HARD",
         "params": {}}])
    assert answer.status_code == 200, answer.text
    body = answer.json()
    assert set(body) == {"journey_id", "capabilities", "summary", "traveler_twin",
                         "active_plan_feasibility", "recovery"}
    assert body["active_plan_feasibility"] is None
    assert body["recovery"] is None
    hard = body["summary"]["hard"]
    assert [item["code"] for item in hard] == ["STEP_FREE_REQUIRED"]
    assert hard[0]["confirmed"] is True
    assert hard[0]["severity"] == "HARD"


def test_capabilities_confirm_on_an_active_journey_without_a_plan_says_so_by_name():
    journey_id, _ = _journey("caps-active", status="ACTIVE")
    client.put(CAPABILITIES_PATH.format(j=journey_id), json=[
        {"code": "MAX_WALKING_PER_LEG_M", "class": "CARE_REQUIREMENT", "severity": "SOFT",
         "params": {"meters": 400}}])
    answer = client.post(CONFIRM_PATH.format(j=journey_id), json=[
        {"code": "STEP_FREE_REQUIRED", "class": "HARD_ACCESSIBILITY_NEED", "severity": "HARD",
         "params": {}}])
    assert answer.status_code == 200, answer.text
    body = answer.json()
    assert body["active_plan_feasibility"] == {"passed": None, "failures": [],
                                               "state": "NO_ACTIVE_PLAN"}
    assert body["recovery"] is None
    assert [item["code"] for item in body["summary"]["hard"]] == ["STEP_FREE_REQUIRED"]
    assert [item["code"] for item in body["summary"]["soft"]] == ["MAX_WALKING_PER_LEG_M"]


def test_capabilities_confirm_refuses_a_code_the_product_has_no_meaning_for():
    journey_id, _ = _journey("caps-unknown")
    answer = client.post(CONFIRM_PATH.format(j=journey_id), json=[
        {"code": "NO_SUCH_RULE", "class": "CARE_REQUIREMENT", "severity": "SOFT", "params": {}}])
    assert answer.status_code == 422, answer.text
    error = _error(answer.json())
    assert error["code"] == "VALIDATION_ERROR"
    first = error["details"]["errors"][0]
    assert tuple(first["loc"]) == ("body", 0), first["loc"]
    assert "UNKNOWN_RULE_CODE" in str(first["msg"]), first


# --------------------------------------------------------------------------- event impact
def _seed_event(journey_id: str, event_type: str = "SCHEDULE_DELAY") -> str:
    ident = str(uuid.uuid4())
    with SessionLocal() as session:
        session.add(M.Event(id=ident, journey_id=journey_id, provider_key="ord0559-provider",
                            provenance="PROVIDER_VERIFIED", event_type=event_type,
                            severity="MAJOR", status="DETECTED", occurred_at=MOMENT,
                            detected_at=MOMENT, resolved_at=None, payload_json="{}",
                            created_at=MOMENT))
        session.commit()
    return ident


def _seed_assessment(journey_id: str, event_id: str) -> str:
    ident = str(uuid.uuid4())
    with SessionLocal() as session:
        session.add(M.ImpactAssessment(
            id=ident, event_id=event_id, journey_id=journey_id,
            provider_key="ord0559-provider", model_key="ord0559-model", status="RESOLVED",
            maturity_stage="CORROBORATED",
            selected_corroboration_refs_json=json.dumps(["ref-one"]),
            independent_evidence_count=2, uncertain=False,
            candidates_json=json.dumps([{"activity_id": "activity-one"}]),
            validated_activity_ids_json=json.dumps(["activity-one"]),
            rejected_activity_ids_json=json.dumps(["activity-two"]),
            reason_codes_json=json.dumps(["SINGLE_SOURCE"]), semantic_reason="ord0559 reason",
            failure_code=None, created_at=MOMENT))
        session.commit()
    return ident


def test_event_impact_returns_the_assessment_row_field_by_field():
    journey_id, _ = _journey("impact")
    event_id = _seed_event(journey_id)
    assessment_id = _seed_assessment(journey_id, event_id)

    answer = client.get(IMPACT_PATH.format(j=journey_id, e=event_id))
    assert answer.status_code == 200, answer.text
    body = answer.json()
    assert set(body) == {"id", "event_id", "journey_id", "provider_key", "model_key", "status",
                         "maturity_stage", "selected_corroboration_refs",
                         "independent_evidence_count", "uncertain", "selected_activity_id",
                         "primary_recovery_target_id", "secondary_risk_activity_ids", "candidates",
                         "validated_activity_ids", "rejected_activity_ids", "reason_codes",
                         "semantic_reason", "failure_code", "created_at"}
    assert body["id"] == assessment_id
    assert body["event_id"] == event_id
    assert body["journey_id"] == journey_id
    assert body["provider_key"] == "ord0559-provider"
    assert body["model_key"] == "ord0559-model"
    assert body["status"] == "RESOLVED"
    assert body["maturity_stage"] == "CORROBORATED"
    assert body["selected_corroboration_refs"] == ["ref-one"]
    assert body["independent_evidence_count"] == 2
    assert body["uncertain"] is False
    assert body["candidates"] == [{"activity_id": "activity-one"}]
    assert body["validated_activity_ids"] == ["activity-one"]
    assert body["rejected_activity_ids"] == ["activity-two"]
    assert body["reason_codes"] == ["SINGLE_SOURCE"]
    assert body["semantic_reason"] == "ord0559 reason"
    assert body["failure_code"] is None
    assert body["selected_activity_id"] is None
    assert body["primary_recovery_target_id"] is None


def test_event_impact_keeps_the_two_absences_apart():
    journey_id, _ = _journey("impact-absences")
    unknown_event = client.get(IMPACT_PATH.format(j=journey_id, e=str(uuid.uuid4())))
    assert unknown_event.status_code == 404, unknown_event.text
    assert _error(unknown_event.json())["message"] == "Event was not found on this Journey"

    event_without_assessment = _seed_event(journey_id, event_type="WEATHER")
    unresolved = client.get(IMPACT_PATH.format(j=journey_id, e=event_without_assessment))
    assert unresolved.status_code == 404, unresolved.text
    unresolved_error = _error(unresolved.json())
    assert unresolved_error["message"] == "Impact assessment has not been resolved"
    assert unresolved_error["code"] == "NOT_FOUND"
    assert unresolved_error["message_key"] == "resource.not_found"


def test_event_impact_does_not_answer_for_another_journeys_event():
    journey_id, _ = _journey("impact-host")
    other_journey, _ = _journey("impact-foreign")
    event_id = _seed_event(journey_id)
    _seed_assessment(journey_id, event_id)
    answer = client.get(IMPACT_PATH.format(j=other_journey, e=event_id))
    assert answer.status_code == 404, answer.text
    assert _error(answer.json())["message"] == "Event was not found on this Journey"


# --------------------------------------------------------------------------- authoritative compose
def test_authoritative_compose_answers_the_candidate_plans_it_froze():
    journey_id, place_ids, _ = _compose_inputs("compose")
    answer = client.post(COMPOSE_PATH.format(j=journey_id),
                         json={"place_ids": place_ids[:4], "candidate_count": 2})
    assert answer.status_code == 201, answer.text
    body = answer.json()
    assert set(body) == {"optimizer", "complete_plan_count", "frozen_evidence_ids",
                         "stay_offer_id", "top_k"}
    assert isinstance(body["optimizer"], str) and body["optimizer"]
    assert body["complete_plan_count"] == len(body["top_k"])
    assert body["complete_plan_count"] >= 1
    assert body["stay_offer_id"] is None or isinstance(body["stay_offer_id"], str)
    assert body["frozen_evidence_ids"]
    assert all(isinstance(item, str) and item for item in body["frozen_evidence_ids"])
    assert isinstance(body["frozen_evidence_ids"], list)
    plan = body["top_k"][0]
    assert set(plan) >= {"id", "journey_id", "version_no", "is_current", "planning_mode",
                         "status", "source", "total_cost", "utility_score", "score_breakdown",
                         "activities", "stale", "selectable", "stale_reason", "created_at"}
    assert plan["journey_id"] == journey_id
    assert plan["is_current"] is False
    assert plan["version_no"] >= 1
    assert set(plan["total_cost"]) == {"amount_minor", "currency"}
    assert plan["total_cost"]["currency"] == "CNY"
    assert plan["activities"]
    assert all(isinstance(activity, dict) for activity in plan["activities"])

    unknown = client.post(COMPOSE_PATH.format(j=str(uuid.uuid4())),
                          json={"place_ids": place_ids[:2], "candidate_count": 1})
    assert unknown.status_code == 404, unknown.text
    assert _error(unknown.json())["code"] == "NOT_FOUND"


def test_authoritative_compose_names_the_poi_it_cannot_price():
    journey_id, place_ids, _ = _compose_inputs("compose-cost")
    with SessionLocal() as session:
        place = session.get(M.Place, place_ids[1])
        place.metadata_json = json.dumps({"cost_status": "UNKNOWN", "duration_min": 45})
        session.commit()
    answer = client.post(COMPOSE_PATH.format(j=journey_id),
                         json={"place_ids": place_ids[:2], "candidate_count": 1})
    assert answer.status_code == 422, answer.text
    error = _error(answer.json())
    assert error["code"] == "VALIDATION_ERROR"
    assert error["message"].startswith("V12_UNKNOWN_POI_COST:"), error["message"]
    assert place_ids[1] in error["message"], error["message"]


def _compose_inputs(tag: str) -> tuple[str, list[str], str]:
    traveler_id = _traveler(tag)
    journey_id = str(uuid.uuid4())
    start = "2031-05-01T08:00:00+00:00"
    end = "2031-05-04T22:00:00+00:00"
    with SessionLocal() as session:
        session.add(M.Journey(
            id=journey_id, traveler_id=traveler_id, title=f"沿海一周 {tag}",
            city_code="CN-TIANJIN", timezone="Asia/Shanghai", start_at=start, end_at=end,
            budget_amount_minor=100000, budget_currency="CNY", planning_mode="balanced",
            status="PLANNED", created_at=start, updated_at=start))
        session.flush()
        session.add(M.JourneyTripContext(
            journey_id=journey_id,
            arrival_anchor_json=json.dumps({"at": start, "location": "Tianjin West Station",
                                            "latitude": 39.14, "longitude": 117.18}),
            departure_anchor_json=json.dumps({"at": end, "location": "Tianjin Binhai Airport",
                                              "latitude": 39.12, "longitude": 117.35}),
            party_size=1, occupancy_json="{}", stay_budget_amount_minor=6000,
            stay_budget_currency="CNY", created_at=start, updated_at=start))
        commitment_id = str(uuid.uuid4())
        session.add(M.Commitment(
            id=commitment_id, journey_id=journey_id, activity_id=None, kind="BOOKING",
            level="C4_Anchored", status="ACTIVE", monetary_value_minor=12000,
            monetary_value_status="KNOWN", currency="CNY", external_ref=f"ORD0559-{tag}",
            policy_json=json.dumps({"semantic_node_key": "arrival-anchor",
                                    "scheduled_start_at": start,
                                    "source": "USER_CONFIRMED_EXTERNAL_RESERVATION"}),
            created_at=start, updated_at=start))
        place_ids = []
        for index, (name, latitude, longitude, category, cost) in enumerate([
            ("Italian Gallery", 39.1315, 117.2050, "arts_centre", 800),
            ("Design Library", 39.1226, 117.1964, "library", 0),
            ("Tea House", 39.1530, 117.1908, "cafe", 300),
            ("Five Avenues", 39.1160, 117.1910, "museum", 500),
            ("Water Park", 39.0840, 117.1710, "park", 200),
        ]):
            place_id = f"ord0559-{tag}-place-{index}"
            place_ids.append(place_id)
            session.add(M.Place(
                id=place_id, provider_key="ord0559", external_id=place_id,
                city_code="CN-TIANJIN", name=name, category=category, latitude=latitude,
                longitude=longitude,
                opening_hours_json=json.dumps({"status": "NORMALIZED", "open": "09:00",
                                               "close": "21:00"}),
                tags_json=json.dumps(["real_city", "captured_replay"]),
                metadata_json=json.dumps({
                    "cost_status": "KNOWN", "cost_minor": cost, "duration_min": 75,
                    "cost_evidence": {"status": "KNOWN", "amount_minor": cost, "currency": "CNY",
                                      "source": "captured_replay"}}),
                updated_at=start))
        session.commit()
    return journey_id, place_ids, commitment_id


# --------------------------------------------------------------------------- native Hermes doors
def test_hermes_run_detail_adds_the_journey_scoped_fields_to_what_hermes_answered(monkeypatch):
    journey_id, _ = _journey("hermes-run")
    with _native_door(monkeypatch) as state:
        answer = client.get(RUN_PATH.format(j=journey_id, r=state["run_id"]))
        assert answer.status_code == 200, answer.text
        body = answer.json()
        assert body["run_id"] == state["run_id"]
        assert body["status"] == "completed"
        assert body["steps"] == 3
        assert body["last_event"] == "run.completed"
        assert body["runtime_identity"] == "HERMES_NATIVE_MCP"
        assert body["journey_id"] == journey_id
        assert body["timeline_url"] == TIMELINE_PATH.format(j=journey_id, r=state["run_id"])
        sent = state["requests"][-1]
        assert sent["authorization"] == "Bearer loopback-ord0559-key"
        assert "loopback-ord0559-key" not in json.dumps(body)


def test_hermes_run_detail_names_the_upstream_that_did_not_answer(monkeypatch):
    journey_id, _ = _journey("hermes-down")
    with _native_door(monkeypatch, mode="down") as state:
        answer = client.get(RUN_PATH.format(j=journey_id, r=state["run_id"]))
        assert answer.status_code == 502, answer.text
        error = _error(answer.json())
        assert error["code"] == "REQUEST_ERROR"
        assert error["message"] == "native Hermes run status is unavailable"
        assert error["message_key"] == "error.request_error"
        assert error["error_receipt_id"]


def test_hermes_stop_hands_back_the_upstreams_answer_for_the_named_run(monkeypatch):
    journey_id, _ = _journey("hermes-stop")
    with _native_door(monkeypatch) as state:
        answer = client.post(STOP_PATH.format(j=journey_id, r=state["run_id"]), json={})
        assert answer.status_code == 200, answer.text
        body = answer.json()
        assert body["run_id"] == state["run_id"]
        assert body["status"] == "stopped"
        assert body["stopped_at"]
        assert state["requests"][-1]["path"].endswith("/stop")


def test_hermes_stop_names_the_upstream_that_did_not_answer(monkeypatch):
    journey_id, _ = _journey("hermes-stop-down")
    with _native_door(monkeypatch, mode="down") as state:
        answer = client.post(STOP_PATH.format(j=journey_id, r=state["run_id"]), json={})
        assert answer.status_code == 502, answer.text
        error = _error(answer.json())
        assert error["message"] == "native Hermes run stop is unavailable"
        assert error["code"] == "REQUEST_ERROR"


def test_hermes_events_stream_replays_frames_and_the_timeline_reads_them_back(monkeypatch):
    journey_id, _ = _journey("hermes-events")
    with _native_door(monkeypatch) as state:
        answer = client.get(EVENTS_PATH.format(j=journey_id, r=state["run_id"]))
        assert answer.status_code == 200, answer.text
        assert answer.headers["content-type"].startswith("text/event-stream")
        assert answer.headers["cache-control"] == "no-cache"
        assert answer.headers["x-accel-buffering"] == "no"
        frames = [json.loads(line[len("data:"):].strip())
                  for line in answer.text.splitlines() if line.startswith("data:")]
        assert [frame["event_type"] for frame in frames] == ["run.started", "tool.started",
                                                            "run.completed"]
        assert all(frame["run_id"] == state["run_id"] for frame in frames)
        assert all(frame["source"] == "HERMES_NATIVE" for frame in frames)
        assert frames[1]["tool_name"] == "probe.tool"
        assert frames[1]["duration_ms"] == 120
        assert frames[2]["status"] == "completed"

        with SessionLocal() as session:
            rows = session.scalars(select(M.AuditLog).where(
                M.AuditLog.action == "agent.native_hermes.event",
                M.AuditLog.entity_id == state["run_id"],
                M.AuditLog.journey_id == journey_id)).all()
        assert len(rows) == 3
        stored = [json.loads(row.after_json)["event_type"] for row in rows]
        assert stored == ["run.started", "tool.started", "run.completed"]

        timeline = client.get(TIMELINE_PATH.format(j=journey_id, r=state["run_id"]))
        assert timeline.status_code == 200, timeline.text
        body = timeline.json()
        assert body["run_id"] == state["run_id"]
        assert body["journey_id"] == journey_id
        assert body["runtime_identity"] == "HERMES_NATIVE_MCP"
        assert len(body["events"]) == 3
        observability = body["observability"]
        assert set(observability) == {"run_id", "runtime_identity", "current_mission",
                                      "tool_count", "current_tool", "completion_status",
                                      "gateway_decision", "guardian_decision",
                                      "total_duration_ms"}
        assert observability["tool_count"] == 1
        assert observability["current_tool"] == "probe.tool"
        assert observability["completion_status"] == "completed"
        assert observability["total_duration_ms"] == 120
        assert observability["current_mission"] is None


def test_hermes_timeline_hydrates_a_terminal_the_reconnect_missed(monkeypatch):
    journey_id, _ = _journey("hermes-hydrate")
    with _native_door(monkeypatch) as state:
        answer = client.get(TIMELINE_PATH.format(j=journey_id, r="run-never-streamed"))
        assert answer.status_code == 200, answer.text
        body = answer.json()
        assert body["run_id"] == "run-never-streamed"
        assert body["observability"]["completion_status"] == "completed"
        assert [item["event_type"] for item in body["events"]] == ["run.completed"]
        assert body["events"][0]["source"] == "HERMES_NATIVE"
        assert body["events"][0]["status"] == "completed"


def test_hermes_timeline_refuses_a_limit_the_query_rule_does_not_allow(monkeypatch):
    journey_id, _ = _journey("hermes-limit")
    with _native_door(monkeypatch) as state:
        answer = client.get(TIMELINE_PATH.format(j=journey_id, r=state["run_id"]) + "?limit=0")
        assert answer.status_code == 422, answer.text
        error = _error(answer.json())
        assert error["code"] == "VALIDATION_ERROR"
        assert tuple(error["details"]["errors"][0]["loc"]) == ("query", "limit")


def test_hermes_doors_all_require_a_journey_that_exists(monkeypatch):
    missing = str(uuid.uuid4())
    with _native_door(monkeypatch) as state:
        for method, url in (
            ("GET", RUN_PATH.format(j=missing, r=state["run_id"])),
            ("GET", TIMELINE_PATH.format(j=missing, r=state["run_id"])),
            ("GET", EVENTS_PATH.format(j=missing, r=state["run_id"])),
            ("POST", STOP_PATH.format(j=missing, r=state["run_id"])),
        ):
            answer = client.request(method, url, json={} if method == "POST" else None)
            assert answer.status_code == 404, f"{method} {url} -> {answer.status_code} {answer.text}"
            error = _error(answer.json())
            assert error["code"] == "NOT_FOUND"
            assert error["message_key"] == "resource.not_found"


def _native_door(monkeypatch, **extra):
    state = {
        "mode": "ok",
        "run_id": f"run-{uuid.uuid4().hex[:8]}",
        "run_status": _run_status_terminal,
        "stop_answer": lambda path: {"run_id": path.rsplit("/", 2)[-2], "status": "stopped",
                                     "stopped_at": MOMENT},
        "frames": _default_frames,
        "requests": [],
    }
    state.update(extra)

    @contextmanager
    def door():
        with _serve(state) as base_url:
            monkeypatch.setattr(hermes, "settings", SimpleNamespace(
                hermes_native_api_url=base_url, hermes_api_server_key="loopback-ord0559-key",
                impact_timeout_seconds=5, hermes_model="hermes-probe",
                hermes_native_profile="citynexus", hermes_native_provider=None,
                hermes_native_model=None))
            yield state

    return door()
