"""ORD-0559 路牌工甲 probe: call each claimed route for real and print the response shape.

Read-only against a temporary SQLite store; nothing here writes into the delivery tree.
"""

from __future__ import annotations

import json
import os
import pathlib
import tempfile
import threading
import uuid
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

_TMP = pathlib.Path(tempfile.mkdtemp(prefix="cnx_probe_"))
os.environ["CITYNEXUS_DEMO_MODE"] = "true"
os.environ["CITYNEXUS_DATABASE_URL"] = f"sqlite:///{(_TMP / 'probe.db').as_posix()}"
os.environ["CITYNEXUS_DEMO_RESET_TOKEN"] = uuid.uuid4().hex
for _k in (
    "DEEPSEEK_API_KEY", "OPENAI_API_KEY", "CITYNEXUS_AI_API_KEY", "CITYNEXUS_AI_ENABLED",
    "CITYNEXUS_HERMES_API_KEY", "CITYNEXUS_HERMES_API_SERVER_KEY", "CITYNEXUS_HERMES_MODEL",
):
    os.environ.pop(_k, None)

from app.db import models as M  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402
from app.main import app  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

NOW = datetime.now(timezone.utc)
MOMENT = NOW.isoformat()
client = TestClient(app, raise_server_exceptions=False)


def shape(value: object, depth: int = 0) -> str:
    if isinstance(value, dict):
        if depth >= 2:
            return "dict{" + ",".join(sorted(value)) + "}"
        inner = ", ".join(f"{k}={shape(v, depth + 1)}" for k, v in sorted(value.items()))
        return "{" + inner + "}"
    if isinstance(value, list):
        return f"list(len={len(value)}" + (", " + shape(value[0], depth + 1) if value else "") + ")"
    if isinstance(value, str):
        return json.dumps(value[:48])
    return repr(value)


def new_traveler(tag: str) -> str:
    ident = str(uuid.uuid4())
    with SessionLocal() as s:
        s.add(M.Traveler(id=ident, display_name=f"probe {tag}", email=None, locale="zh-CN",
                         timezone="Asia/Shanghai", created_at=MOMENT, updated_at=MOMENT))
        s.commit()
    return ident


def new_journey(traveler_id: str, tag: str, status: str = "PLANNED") -> str:
    ident = str(uuid.uuid4())
    with SessionLocal() as s:
        s.add(M.Journey(id=ident, traveler_id=traveler_id, title=f"沿海一周 {tag}",
                        city_code="CN-XIAMEN", timezone="Asia/Shanghai",
                        start_at=(NOW + timedelta(days=200)).isoformat(),
                        end_at=(NOW + timedelta(days=202)).isoformat(),
                        budget_amount_minor=120000, budget_currency="CNY", status=status,
                        created_at=MOMENT, updated_at=MOMENT))
        s.commit()
    return ident


def report(label: str, method: str, url: str, body: dict | None = None, headers: dict | None = None):
    if body is None:
        r = client.request(method, url, headers=headers)
    else:
        r = client.request(method, url, json=body, headers=headers)
    try:
        payload = r.json()
    except Exception:
        payload = {"__text__": r.text[:120]}
    print(f"\n## {label} | {method} {url} -> http_status={r.status_code}")
    print("   " + shape(payload)[:1400])
    return payload


# ---------------------------------------------------------------- seeded store
with SessionLocal() as s:
    role_rows = s.query(M.JourneyRoleCapability).count() if hasattr(s, "query") else 0
print(f"\n[store] JourneyRoleCapability rows present = {role_rows}")

T = new_traveler("owner")
J = new_journey(T, "plain")

report("acl/roles", "GET", f"/api/v1/journeys/{J}/acl/roles")
report("member-role-limits", "GET", f"/api/v1/journeys/{J}/member-role-limits")
report("multiday", "GET", f"/api/v1/journeys/{J}/multiday")
report("inbox-empty", "GET", f"/api/v1/journeys/{J}/inbox")
report("guardian-autopilot-status-naked", "GET", f"/api/v1/journeys/{J}/guardian/autopilot/status")
report("guardian-resilience", "GET", f"/api/v1/journeys/{J}/guardian/resilience")
report("guardian-resilience-refresh-replay", "POST", f"/api/v1/journeys/{J}/guardian/resilience/refresh", {"mode": "replay"})
report("guardian-signal-fixture", "POST", f"/api/v1/journeys/{J}/guardian/signal-fixture",
       {"state": "DISRUPTED", "payload": {"cause": "probe", "affected_lines": ["BRT-1"]}})
report("capabilities-PUT", "PUT", f"/api/v1/journeys/{J}/capabilities",
       [{"code": "MAX_WALKING_PER_LEG_M", "class": "CARE_REQUIREMENT", "severity": "SOFT",
         "params": {"meters": 500}}])
report("capabilities-confirm", "POST", f"/api/v1/journeys/{J}/capabilities/confirm",
       [{"code": "STEP_FREE_REQUIRED", "class": "HARD_ACCESSIBILITY_NEED", "severity": "HARD", "params": {}}])
report("journey-not-found-control", "GET", f"/api/v1/journeys/{uuid.uuid4()}/multiday")
report("validation-control-PUT-capabilities", "PUT", f"/api/v1/journeys/{J}/capabilities",
       [{"code": "NOT_A_RULE", "class": "CARE_REQUIREMENT"}])

# ---------------------------------------------------------------- draft seed
with SessionLocal() as s:
    s.add(M.ExternalReservationDraft(
        id=str(uuid.uuid4()), journey_id=J, artifact_type="TRAIN_TICKET", raw_payload_json="{}",
        extracted_json=json.dumps({"anchor_role": "OUTBOUND", "anchor_role_confidence": 0.8,
                                   "semantic_target": "Xiamen North", "payment_status": "PAID",
                                   "reasoning_summary": "probe", "smart_intake": {"channel": "probe"}}),
        unresolved_fields_json=json.dumps(["date"]), extraction_mode="TEXT", status="DRAFT",
        created_at=MOMENT, confirmed_at=None))
    s.commit()
report("inbox-with-draft", "GET", f"/api/v1/journeys/{J}/inbox")

# ---------------------------------------------------------------- member + self-exit
mate = new_traveler("mate")
member_id = str(uuid.uuid4())
with SessionLocal() as s:
    s.add(M.JourneyMember(id=member_id, journey_id=J, traveler_id=mate, role="COLLABORATOR",
                          invited_by=T, expires_at=None, joined_at=MOMENT, removed_at=None,
                          created_at=MOMENT, updated_at=MOMENT))
    s.commit()
report("members-self-exit", "POST", f"/api/v1/journeys/{J}/members/self-exit", {"traveler_id": mate})
report("members-self-exit-twice", "POST", f"/api/v1/journeys/{J}/members/self-exit", {"traveler_id": mate})
report("members-self-exit-owner", "POST", f"/api/v1/journeys/{J}/members/self-exit", {"traveler_id": T})
report("members-self-exit-stranger", "POST", f"/api/v1/journeys/{J}/members/self-exit",
       {"traveler_id": str(uuid.uuid4())})

# ---------------------------------------------------------------- event + impact
event_id, assessment_id = str(uuid.uuid4()), str(uuid.uuid4())
with SessionLocal() as s:
    s.add(M.Event(id=event_id, journey_id=J, provider_key="probe-provider", provenance="SIMULATED",
                  event_type="SERVICE_DISRUPTION", severity="HIGH", status="ACTIVE",
                  occurred_at=MOMENT, detected_at=MOMENT, resolved_at=None,
                  payload_json="{}", created_at=MOMENT))
    s.add(M.ImpactAssessment(
        id=assessment_id, event_id=event_id, journey_id=J, provider_key="probe-provider",
        model_key="probe-model", status="RESOLVED", maturity_stage="CORROBORATED",
        selected_corroboration_refs_json=json.dumps(["ref-1"]), independent_evidence_count=2,
        uncertain=False, selected_activity_id=None, primary_recovery_target_id=None,
        secondary_risk_activity_ids_json="[]", candidates_json=json.dumps([{"activity_id": "a1"}]),
        validated_activity_ids_json="[]", rejected_activity_ids_json="[]",
        reason_codes_json=json.dumps(["SINGLE_SOURCE"]), semantic_reason="probe reason",
        failure_code=None, response_hash=None, created_at=MOMENT))
    s.commit()
report("event-impact", "GET", f"/api/v1/journeys/{J}/events/{event_id}/impact")
report("event-impact-no-assessment", "GET", f"/api/v1/journeys/{J}/events/{str(uuid.uuid4())}/impact")

# ---------------------------------------------------------------- autopilot enrollment
with SessionLocal() as s:
    s.add(M.AutopilotEnrollment(journey_id=J, enabled=True, interval_seconds=45.0,
                                provider_mesh_json=json.dumps({"mesh": "probe"}),
                                last_pulse_at=MOMENT, last_error=None,
                                created_at=MOMENT, updated_at=MOMENT))
    s.commit()
report("guardian-autopilot-status-enrolled", "GET", f"/api/v1/journeys/{J}/guardian/autopilot/status")

# ---------------------------------------------------------------- places for compose
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
report("authoritative-compose", "POST", f"/api/v1/journeys/{J}/authoritative-compose",
       {"place_ids": place_ids, "candidate_count": 2})

# ---------------------------------------------------------------- hermes native
RUN = f"run-probe-{uuid.uuid4().hex[:8]}"
FRAMES = [
    "event: run.started\ndata: {\"run_id\": \"%s\", \"status\": \"running\", \"source\": \"HERMES_NATIVE\", \"timestamp\": \"%s\"}\n\n" % (RUN, MOMENT),
    "event: tool.started\ndata: {\"run_id\": \"%s\", \"status\": \"running\", \"source\": \"HERMES_NATIVE\", \"tool_name\": \"probe.tool\", \"timestamp\": \"%s\"}\n\n" % (RUN, MOMENT),
    "event: run.completed\ndata: {\"run_id\": \"%s\", \"status\": \"completed\", \"source\": \"HERMES_NATIVE\", \"timestamp\": \"%s\"}\n\n" % (RUN, MOMENT),
]


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
            payload = "".join(FRAMES).encode()
            self._send(200, payload, "text/event-stream")
            return
        if self.path.startswith("/v1/runs/"):
            self._send(200, json.dumps({
                "run_id": RUN, "status": "completed", "last_event": "run.completed",
                "updated_at": MOMENT, "steps": 3}).encode(), "application/json")
            return
        self._send(404, b"{}", "application/json")

    def do_POST(self):
        self._send(200, json.dumps({"run_id": RUN, "status": "stopped",
                                    "stopped_at": MOMENT}).encode(), "application/json")


server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
port = server.server_address[1]
threading.Thread(target=server.serve_forever, daemon=True).start()

from app.integrations.hermes import native_client as hermes  # noqa: E402
from types import SimpleNamespace  # noqa: E402

original_settings = hermes.settings
hermes.settings = SimpleNamespace(
    hermes_native_api_url=f"http://127.0.0.1:{port}", hermes_api_server_key="loopback-probe-key",
    impact_timeout_seconds=5, hermes_model="hermes-probe", hermes_native_profile="citynexus",
    hermes_native_provider=None, hermes_native_model=None,
)
report("hermes-run-detail", "GET", f"/api/v1/journeys/{J}/agent/hermes/runs/{RUN}")
report("hermes-timeline", "GET", f"/api/v1/journeys/{J}/agent/hermes/runs/{RUN}/timeline")
report("hermes-stop", "POST", f"/api/v1/journeys/{J}/agent/hermes/runs/{RUN}/stop", {})
report("hermes-events-sse", "GET", f"/api/v1/journeys/{J}/agent/hermes/runs/{RUN}/events")
raw = client.get(f"/api/v1/journeys/{J}/agent/hermes/runs/{RUN}/events")
print("\n## sse raw head:", repr(raw.text[:400]))
with SessionLocal() as s:
    print("   audit native rows =", s.query(M.AuditLog).filter(M.AuditLog.action == "agent.native_hermes.event").count())

hermes.settings = SimpleNamespace(hermes_native_api_url=None, hermes_api_server_key=None,
                                 impact_timeout_seconds=2)
report("hermes-run-detail-unconfigured", "GET", f"/api/v1/journeys/{J}/agent/hermes/runs/{RUN}")
report("hermes-stop-unconfigured", "POST", f"/api/v1/journeys/{J}/agent/hermes/runs/{RUN}/stop")
report("hermes-events-unconfigured", "GET", f"/api/v1/journeys/{J}/agent/hermes/runs/{RUN}/events")
hermes.settings = original_settings
server.shutdown()
print("\n[done] probe finished")
