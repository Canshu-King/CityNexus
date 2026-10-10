"""ORD-0559 route gap, `agent` group: four routes asserted on response fields.

Coverage: GET /api/v1/agent/tools/v2, GET /api/v1/agent/hermes/capabilities,
GET /api/v1/agent/hermes/runs/{run_id}, GET /api/v1/agent/hermes/runs/{run_id}/events.

The Hermes runs API is reached over a real loopback HTTP server started in this
module, so the route -> httpx -> TCP -> HTTP chain stays intact; nothing here
short-circuits the client with a mock transport.
"""

from __future__ import annotations

import json
import threading
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

import app.main as main_module
from app.agent.tool_catalog import RUNTIME_MCP_ALLOWLIST_V2
from app.db.models import AuditLog
from app.db.session import SessionLocal
from app.integrations.hermes import native_client as hermes

client = TestClient(main_module.app)

SERVER_KEY = "ord0559-loopback-server-key"
RUN_ID = f"run-0559-{uuid.uuid4().hex[:8]}"
MISSING_RUN_ID = f"{RUN_ID}-absent"
CAPABILITY_BODY = {
    "features": {"run_submission": True, "run_events_sse": True, "run_approval": True},
    "endpoints": {
        "run_events": {"path": "/v1/runs/{run_id}/events"},
        "run_approval": {"path": "/v1/runs/{run_id}/approval"},
    },
}
RUN_BODY = {
    "run_id": RUN_ID,
    "status": "running",
    "input": "Inspect this Journey.",
    "session_id": f"citynexus-{RUN_ID}",
    "metadata": {"tool_surface": "citynexus-mcp-only", "autonomy": "PLAN_ONLY"},
}
UPSTREAM_EVENT_FRAMES = (
    ("run.started", {"run_id": RUN_ID, "timestamp": "2026-10-10T00:00:00Z", "sequence": 1}),
    ("message.delta", {"run_id": RUN_ID, "text": "free-form model prose"}),
    (
        "tool.completed",
        {
            "run_id": RUN_ID,
            "event_id": "evt-0559-2",
            "tool_name": "inspect_journey",
            "sequence": 2,
            "duration": 0.25,
            "result": {"decision": "ALLOW_AUTO", "status": "ok"},
            "arguments": {"note": "raw Hermes arguments"},
        },
    ),
)


class _HermesHandler(BaseHTTPRequestHandler):
    def _record(self) -> dict[str, str]:
        entry = {
            "path": self.path,
            "authorization": self.headers.get("authorization", ""),
        }
        self.server.records.append(entry)  # type: ignore[attr-defined]
        return entry

    def _send(self, status: int, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("content-type", content_type)
        self.send_header("content-length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        self._record()
        if self.path == "/v1/capabilities":
            self._send(200, json.dumps(CAPABILITY_BODY).encode(), "application/json")
            return
        if self.path == f"/v1/runs/{RUN_ID}":
            self._send(200, json.dumps(RUN_BODY).encode(), "application/json")
            return
        if self.path == f"/v1/runs/{RUN_ID}/events":
            chunks = [
                f"event: {name}\ndata: {json.dumps(payload)}\n\n".encode()
                for name, payload in UPSTREAM_EVENT_FRAMES
            ]
            self.send_response(200)
            self.send_header("content-type", "text/event-stream")
            self.end_headers()
            for chunk in chunks:
                self.wfile.write(chunk)
            self.wfile.flush()
            return
        self._send(404, json.dumps({"error": "run_not_found"}).encode(), "application/json")

    def log_message(self, *args) -> None:
        return


@pytest.fixture()
def hermes_upstream(monkeypatch):
    server = ThreadingHTTPServer(("127.0.0.1", 0), _HermesHandler)
    server.records = []  # type: ignore[attr-defined]
    server.daemon_threads = True
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    monkeypatch.setattr(
        hermes,
        "settings",
        SimpleNamespace(
            hermes_native_api_url=f"http://127.0.0.1:{server.server_address[1]}",
            hermes_api_server_key=SERVER_KEY,
            impact_timeout_seconds=2.0,
            hermes_native_profile="citynexus",
            hermes_native_provider=None,
            hermes_native_model=None,
        ),
    )
    try:
        yield server
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def _sse_frames(body: str) -> list[tuple[str, dict[str, object]]]:
    frames: list[tuple[str, dict[str, object]]] = []
    for block in body.split("\n\n"):
        block = block.strip()
        if not block:
            continue
        name = None
        data = None
        for line in block.splitlines():
            if line.startswith("event:"):
                name = line[6:].strip()
            elif line.startswith("data:"):
                data = json.loads(line[5:].strip())
        assert name is not None and data is not None
        frames.append((name, data))
    return frames


def test_route_gap_tools_v2_descriptors_carry_every_contract_field():
    response = client.get("/api/v1/agent/tools/v2")
    assert response.status_code == 200
    items = response.json()
    assert isinstance(items, list)
    for item in items:
        assert set(item) == {
            "name",
            "action",
            "mutates_domain_truth",
            "changes_money",
            "changes_c4",
        }
    by_name = {item["name"]: item for item in items}
    assert set(by_name) == set(RUNTIME_MCP_ALLOWLIST_V2)
    assert by_name["inspect_journey"]["action"] == "INSPECT_JOURNEY"
    assert by_name["create_booking"]["action"] == "CREATE_BOOKING"
    assert by_name["create_booking"]["changes_money"] is True
    assert by_name["cancel_refundable_booking"]["changes_money"] is True
    assert by_name["request_commitment_change"]["changes_c4"] is True
    assert by_name["request_commitment_change"]["mutates_domain_truth"] is True
    assert by_name["search_city_services"]["mutates_domain_truth"] is False
    assert by_name["search_city_services"]["changes_money"] is False
    assert by_name["search_city_services"]["changes_c4"] is False


def test_route_gap_hermes_capabilities_unconfigured_shape():
    response = client.get("/api/v1/agent/hermes/capabilities")
    assert response.status_code == 200
    payload = response.json()
    assert set(payload) == {
        "configured",
        "reachable",
        "runs",
        "events",
        "approval",
        "stop",
        "ready",
        "profile",
        "provider",
        "model",
    }
    assert payload["configured"] is False
    assert payload["reachable"] is False
    assert payload["ready"] is False
    assert payload["runs"] is False
    assert payload["events"] is False
    assert payload["profile"] == "citynexus"
    assert payload["provider"] is None
    assert payload["model"] is None


def test_route_gap_hermes_capabilities_configured_shape(hermes_upstream):
    response = client.get("/api/v1/agent/hermes/capabilities")
    assert response.status_code == 200
    payload = response.json()
    assert payload["configured"] is True
    assert payload["reachable"] is True
    assert payload["runs"] is True
    assert payload["events"] is True
    assert payload["approval"] is True
    assert payload["stop"] is False
    assert payload["ready"] is True
    assert payload["profile"] == "citynexus"
    assert "loopback" not in json.dumps(payload)
    assert hermes_upstream.records[-1]["path"] == "/v1/capabilities"
    assert hermes_upstream.records[-1]["authorization"] == f"Bearer {SERVER_KEY}"


def test_route_gap_hermes_run_returns_upstream_fields_verbatim(hermes_upstream):
    response = client.get(f"/api/v1/agent/hermes/runs/{RUN_ID}")
    assert response.status_code == 200
    payload = response.json()
    assert payload["run_id"] == RUN_ID
    assert payload["status"] == "running"
    assert payload["session_id"] == f"citynexus-{RUN_ID}"
    assert payload["metadata"]["tool_surface"] == "citynexus-mcp-only"
    assert payload["metadata"]["autonomy"] == "PLAN_ONLY"
    assert "runtime_identity" not in payload
    assert hermes_upstream.records[-1]["path"] == f"/v1/runs/{RUN_ID}"
    assert hermes_upstream.records[-1]["authorization"] == f"Bearer {SERVER_KEY}"


def test_route_gap_hermes_run_unknown_run_returns_the_error_envelope(hermes_upstream):
    response = client.get(f"/api/v1/agent/hermes/runs/{MISSING_RUN_ID}")
    assert response.status_code == 502
    error = response.json()["error"]
    assert {"code", "message", "message_key", "trace_id", "details"} <= set(error)
    assert error["code"] == "REQUEST_ERROR"
    assert error["message"] == "native Hermes run status is unavailable"
    assert error["message_key"] == "error.request_error"
    assert error["details"] is None
    assert error["error_receipt_id"].startswith("CNX-")
    assert hermes_upstream.records[-1]["path"] == f"/v1/runs/{MISSING_RUN_ID}"


def test_route_gap_hermes_run_events_stream_normalized_frames(hermes_upstream):
    response = client.get(f"/api/v1/agent/hermes/runs/{RUN_ID}/events")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert response.headers["cache-control"] == "no-cache"
    assert response.headers["x-accel-buffering"] == "no"
    frames = _sse_frames(response.text)
    assert [name for name, _ in frames] == ["run.started", "tool.completed"]
    for _, data in frames:
        assert {"event_type", "run_id", "status", "source", "raw_event_type"} <= set(data)
        assert data["run_id"] == RUN_ID
    started = frames[0][1]
    assert started["event_type"] == "run.started"
    assert started["status"] == "started"
    assert started["sequence"] == 1
    assert started["friendly_label"] == "Hermes runtime"
    completed = frames[1][1]
    assert completed["event_type"] == "tool.completed"
    assert completed["status"] == "completed"
    assert completed["tool_name"] == "inspect_journey"
    assert completed["event_id"] == "evt-0559-2"
    assert completed["duration_ms"] == 250
    assert completed["result_summary"] == {"decision": "ALLOW_AUTO", "status": "ok"}
    assert completed["policy_decision"] == "ALLOW_AUTO"
    assert completed["friendly_label"] == "Inspect current Journey"
    assert completed["source"] == "HERMES_NATIVE"
    assert "raw Hermes arguments" not in response.text
    assert "free-form model prose" not in response.text
    assert hermes_upstream.records[-1]["path"] == f"/v1/runs/{RUN_ID}/events"


def test_route_gap_hermes_run_events_persist_audit_rows(hermes_upstream):
    response = client.get(f"/api/v1/agent/hermes/runs/{RUN_ID}/events")
    assert response.status_code == 200
    with SessionLocal() as session:
        rows = session.scalars(
            select(AuditLog).where(
                AuditLog.action == "agent.native_hermes.event",
                AuditLog.entity_id == RUN_ID,
            )
        ).all()
    assert len(rows) == 2
    stored = sorted(json.loads(row.after_json or "{}")["event_type"] for row in rows)
    assert stored == ["run.started", "tool.completed"]
    assert all(row.actor_id == "hermes-native" for row in rows)
