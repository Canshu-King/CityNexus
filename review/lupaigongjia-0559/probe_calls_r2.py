"""ORD-0559 路牌工甲 probe r2: the routes probe r1 did not reach (event impact, enrolled autopilot, authoritative-compose, native Hermes).

Same rules as r1: real HTTP over loopback against the product's own configured Hermes door, no
response mocking inside the app.
"""

from __future__ import annotations

import json
import os
import pathlib
import tempfile
import threading
import traceback
import uuid
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from types import SimpleNamespace

_TMP = pathlib.Path(tempfile.mkdtemp(prefix="cnx_probe2_"))
os.environ["CITYNEXUS_DEMO_MODE"] = "true"
os.environ["CITYNEXUS_DATABASE_URL"] = f"sqlite:///{(_TMP / 'probe.db').as_posix()}"
os.environ["CITYNEXUS_DEMO_RESET_TOKEN"] = uuid.uuid4().hex

from app.db import models as M  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402
from app.main import app  # noqa: E402
from app.integrations.hermes import native_client as hermes  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

NOW = datetime.now(timezone.utc)
MOMENT = NOW.isoformat()
client = TestClient(app, raise_server_exceptions=False)


def shape(value: object, depth: int = 0) -> str:
    if isinstance(value, dict):
        if depth >= 2:
            return "dict{" + ",".join(sorted(value)) + "}"
        return "{" + ", ".join(f"{k}={shape(v, depth + 1)}" for k, v in sorted(value.items())) + "}"
    if isinstance(value, list):
        return f"list(len={len(value)}" + (", " + shape(value[0], depth + 1) if value else "") + ")"
    if isinstance(value, str):
        return json.dumps(value[:40])
    return repr(value)


def call(label: str, method: str, url: str, body=None):
    try:
        r = client.request(method, url, json=body) if body is not None else client.request(method, url)
        try:
            payload = r.json()
        except Exception:
            payload = {"__text__": r.text[:200]}
        print(f"\n## {label} | {method} {url} -> http_status={r.status_code}")
        print("   " + shape(payload)[:1500])
    except Exception:
        print(f"\n## {label} | {method} {url} -> EXCEPTION")
        traceback.print_exc()


T = str(uuid.uuid4())
with SessionLocal() as s:
    s.add(M.Traveler(id=T, display_name="probe2", email=None, locale="zh-CN",
                     timezone="Asia/Shanghai", created_at=MOMENT, updated_at=MOMENT))
    s.commit()
J = str(uuid.uuid4())
with SessionLocal() as s:
    s.add(M.Journey(id=J, traveler_id=T, title="沿海一周 probe2", city_code="CN-XIAMEN",
                    timezone="Asia/Shanghai", start_at=(NOW + timedelta(days=200)).isoformat(),
                    end_at=(NOW + timedelta(days=202)).isoformat(), budget_amount_minor=120000,
                    budget_currency="CNY", status="PLANNED", created_at=MOMENT, updated_at=MOMENT))
    s.commit()

event_id, assessment_id = str(uuid.uuid4()), str(uuid.uuid4())
try:
    with SessionLocal() as s:
        s.add(M.Event(id=event_id, journey_id=J, provider_key="probe-provider",
                      provenance="PROVIDER_VERIFIED", event_type="SCHEDULE_DELAY", severity="MAJOR",
                      status="DETECTED", occurred_at=MOMENT, detected_at=MOMENT, resolved_at=None,
                      payload_json="{}", created_at=MOMENT))
        s.add(M.ImpactAssessment(id=assessment_id, event_id=event_id, journey_id=J,
                                 provider_key="probe-provider", model_key="probe-model",
                                 status="RESOLVED", maturity_stage="CORROBORATED",
                                 selected_corroboration_refs_json=json.dumps(["ref-1"]),
                                 independent_evidence_count=2, uncertain=False,
                                 candidates_json=json.dumps([{"activity_id": "a1"}]),
                                 reason_codes_json=json.dumps(["SINGLE_SOURCE"]),
                                 semantic_reason="probe reason", failure_code=None,
                                 created_at=MOMENT))
        s.commit()
    print("[seed] event + impact ok")
except Exception:
    traceback.print_exc()

call("event-impact", "GET", f"/api/v1/journeys/{J}/events/{event_id}/impact")
call("event-impact-unknown-event", "GET", f"/api/v1/journeys/{J}/events/{uuid.uuid4()}/impact")
with SessionLocal() as s:
    bare = str(uuid.uuid4())
    s.add(M.Event(id=bare, journey_id=J, provider_key="probe-provider", provenance="SIMULATED",
                  event_type="WEATHER", severity="MINOR", status="DETECTED", occurred_at=MOMENT,
                  detected_at=MOMENT, resolved_at=None, payload_json="{}", created_at=MOMENT))
    s.commit()
call("event-impact-no-assessment", "GET", f"/api/v1/journeys/{J}/events/{bare}/impact")

try:
    with SessionLocal() as s:
        s.add(M.AutopilotEnrollment(journey_id=J, enabled=True, interval_seconds=45.0,
                                    provider_mesh_json=json.dumps({"mesh": "probe"}),
                                    last_pulse_at=MOMENT, last_error=None,
                                    created_at=MOMENT, updated_at=MOMENT))
        s.commit()
except Exception:
    traceback.print_exc()
call("autopilot-status-enrolled", "GET", f"/api/v1/journeys/{J}/guardian/autopilot/status")

place_ids = []
with SessionLocal() as s:
    for n in range(3):
        pid = str(uuid.uuid4())
        place_ids.append(pid)
        s.add(M.Place(id=pid, provider_key="probe", external_id=f"p{n}", city_code="CN-XIAMEN",
                      name=f"探针点 {n}", category="sight", latitude=24.45 + n * 0.01,
                      longitude=118.05 + n * 0.01, opening_hours_json="{}", tags_json="[]",
                      metadata_json="{}", updated_at=MOMENT))
    s.commit()
call("authoritative-compose", "POST", f"/api/v1/journeys/{J}/authoritative-compose",
     {"place_ids": place_ids, "candidate_count": 2})
call("authoritative-compose-one-place", "POST", f"/api/v1/journeys/{J}/authoritative-compose",
     {"place_ids": place_ids[:1]})

RUN = f"run-probe-{uuid.uuid4().hex[:8]}"
FRAMES = (
    f"event: run.started\ndata: {{\"run_id\": \"{RUN}\", \"status\": \"running\", \"source\": \"HERMES_NATIVE\", \"timestamp\": \"{MOMENT}\"}}\n\n"
    f"event: tool.started\ndata: {{\"run_id\": \"{RUN}\", \"status\": \"running\", \"source\": \"HERMES_NATIVE\", \"tool_name\": \"probe.tool\", \"duration_ms\": 120, \"result_summary\": {{\"mission_id\": \"mission-probe\"}}, \"timestamp\": \"{MOMENT}\"}}\n\n"
    f"event: run.completed\ndata: {{\"run_id\": \"{RUN}\", \"status\": \"completed\", \"source\": \"HERMES_NATIVE\", \"timestamp\": \"{MOMENT}\"}}\n\n"
)


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, code: int, body: bytes, ctype: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path.endswith("/events"):
            self._send(200, FRAMES.encode(), "text/event-stream")
        elif self.path.startswith("/v1/runs/"):
            self._send(200, json.dumps({"run_id": RUN, "status": "completed",
                                        "last_event": "run.completed", "updated_at": MOMENT,
                                        "steps": 3}).encode(), "application/json")
        else:
            self._send(404, b"{}", "application/json")

    def do_POST(self):
        self._send(200, json.dumps({"run_id": RUN, "status": "stopped",
                                    "stopped_at": MOMENT}).encode(), "application/json")


server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
port = server.server_address[1]
threading.Thread(target=server.serve_forever, daemon=True).start()
original = hermes.settings
hermes.settings = SimpleNamespace(hermes_native_api_url=f"http://127.0.0.1:{port}",
                                  hermes_api_server_key="loopback-probe-key",
                                  impact_timeout_seconds=5, hermes_model="hermes-probe",
                                  hermes_native_profile="citynexus", hermes_native_provider=None,
                                  hermes_native_model=None)
call("hermes-run-detail", "GET", f"/api/v1/journeys/{J}/agent/hermes/runs/{RUN}")
call("hermes-timeline", "GET", f"/api/v1/journeys/{J}/agent/hermes/runs/{RUN}/timeline")
call("hermes-timeline-limit", "GET", f"/api/v1/journeys/{J}/agent/hermes/runs/{RUN}/timeline?limit=1")
call("hermes-stop", "POST", f"/api/v1/journeys/{J}/agent/hermes/runs/{RUN}/stop", {})
try:
    raw = client.get(f"/api/v1/journeys/{J}/agent/hermes/runs/{RUN}/events")
    print(f"\n## hermes-events-sse | GET .../events -> http_status={raw.status_code}")
    print("   content_type=" + str(raw.headers.get("content-type")))
    print("   cache_control=" + str(raw.headers.get("cache-control")))
    print("   body=" + repr(raw.text[:600]))
except Exception:
    traceback.print_exc()
with SessionLocal() as s:
    rows = s.query(M.AuditLog).filter(M.AuditLog.action == "agent.native_hermes.event").all()
    print("   audit native rows =", len(rows), "entity_ids =", sorted({r.entity_id for r in rows}))
    print("   after_json head =", repr(rows[0].after_json[:200]) if rows else None)
call("hermes-timeline-after-sse", "GET", f"/api/v1/journeys/{J}/agent/hermes/runs/{RUN}/timeline")

hermes.settings = SimpleNamespace(hermes_native_api_url=None, hermes_api_server_key=None,
                                  impact_timeout_seconds=2)
call("hermes-run-detail-unconfigured", "GET", f"/api/v1/journeys/{J}/agent/hermes/runs/{RUN}")
call("hermes-stop-unconfigured", "POST", f"/api/v1/journeys/{J}/agent/hermes/runs/{RUN}/stop", {})
call("hermes-events-unconfigured", "GET", f"/api/v1/journeys/{J}/agent/hermes/runs/{RUN}/events")
hermes.settings = original

# upstream answering 5xx -> the route's named 502
class DownHandler(Handler):
    def do_GET(self):
        self._send(503, b"{}", "application/json")

    def do_POST(self):
        self._send(503, b"{}", "application/json")


down = ThreadingHTTPServer(("127.0.0.1", 0), DownHandler)
down_port = down.server_address[1]
threading.Thread(target=down.serve_forever, daemon=True).start()
hermes.settings = SimpleNamespace(hermes_native_api_url=f"http://127.0.0.1:{down_port}",
                                  hermes_api_server_key="loopback-probe-key",
                                  impact_timeout_seconds=2, hermes_model="hermes-probe",
                                  hermes_native_profile="citynexus", hermes_native_provider=None,
                                  hermes_native_model=None)
call("hermes-run-detail-upstream-503", "GET", f"/api/v1/journeys/{J}/agent/hermes/runs/{RUN}")
call("hermes-stop-upstream-503", "POST", f"/api/v1/journeys/{J}/agent/hermes/runs/{RUN}/stop", {})
hermes.settings = original
server.shutdown()
down.shutdown()
print("\n[done] probe r2")
