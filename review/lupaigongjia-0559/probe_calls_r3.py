"""ORD-0559 路牌工甲 probe r3: the arms probe r2 left open.

compose with a cost-bearing place, resilience refresh in live mode, capability confirm on an ACTIVE
journey, the owner self-exit refusal, the fixture state vocabulary refusal, and the timeline limit
refusal.
"""

from __future__ import annotations

import json
import os
import pathlib
import tempfile
import traceback
import uuid
from datetime import datetime, timedelta, timezone

_TMP = pathlib.Path(tempfile.mkdtemp(prefix="cnx_probe3_"))
os.environ["CITYNEXUS_DEMO_MODE"] = "true"
os.environ["CITYNEXUS_DATABASE_URL"] = f"sqlite:///{(_TMP / 'probe.db').as_posix()}"
os.environ["CITYNEXUS_DEMO_RESET_TOKEN"] = uuid.uuid4().hex

from app.db import models as M  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402
from app.main import app  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

NOW = datetime.now(timezone.utc)
MOMENT = NOW.isoformat()
client = TestClient(app, raise_server_exceptions=False)


def shape(value: object, depth: int = 0) -> str:
    if isinstance(value, dict):
        if depth >= 3:
            return "dict{" + ",".join(sorted(value)) + "}"
        return "{" + ", ".join(f"{k}={shape(v, depth + 1)}" for k, v in sorted(value.items())) + "}"
    if isinstance(value, list):
        return f"list(len={len(value)}" + (", " + shape(value[0], depth + 1) if value else "") + ")"
    if isinstance(value, str):
        return json.dumps(value[:60])
    return repr(value)


def call(label: str, method: str, url: str, body=None):
    r = client.request(method, url, json=body) if body is not None else client.request(method, url)
    try:
        payload = r.json()
    except Exception:
        payload = {"__text__": r.text[:160]}
    print(f"\n## {label} | {method} {url} -> http_status={r.status_code}")
    print("   " + shape(payload)[:1600])


T = str(uuid.uuid4())
with SessionLocal() as s:
    s.add(M.Traveler(id=T, display_name="probe3", email=None, locale="zh-CN",
                     timezone="Asia/Shanghai", created_at=MOMENT, updated_at=MOMENT))
    s.commit()


def journey(tag: str, status: str = "PLANNED") -> str:
    ident = str(uuid.uuid4())
    with SessionLocal() as s:
        s.add(M.Journey(id=ident, traveler_id=T, title=f"沿海一周 {tag}", city_code="CN-XIAMEN",
                        timezone="Asia/Shanghai", start_at=(NOW + timedelta(days=200)).isoformat(),
                        end_at=(NOW + timedelta(days=202)).isoformat(), budget_amount_minor=120000,
                        budget_currency="CNY", status=status, created_at=MOMENT, updated_at=MOMENT))
        s.commit()
    return ident


J = journey("compose")
places = []
with SessionLocal() as s:
    for n in range(4):
        pid = str(uuid.uuid4())
        places.append(pid)
        s.add(M.Place(id=pid, provider_key="probe", external_id=f"c{n}", city_code="CN-XIAMEN",
                      name=f"探针点 {n}", category="sight", latitude=24.45 + n * 0.02,
                      longitude=118.05 + n * 0.02, opening_hours_json="{}", tags_json="[]",
                      metadata_json=json.dumps({"cost_minor": 3000 + n * 500, "duration_min": 45,
                                               "cost_status": "KNOWN"}), updated_at=MOMENT))
    s.commit()
call("compose-with-cost", "POST", f"/api/v1/journeys/{J}/authoritative-compose",
     {"place_ids": places, "candidate_count": 2})
call("compose-free-known", "POST", f"/api/v1/journeys/{J}/authoritative-compose",
     {"place_ids": places[:2], "candidate_count": 1})

JL = journey("live")
call("refresh-mode-live", "POST", f"/api/v1/journeys/{JL}/guardian/resilience/refresh", {"mode": "live"})
call("refresh-mode-bogus", "POST", f"/api/v1/journeys/{JL}/guardian/resilience/refresh", {"mode": "sideways"})

JA = journey("active", status="ACTIVE")
call("capabilities-PUT-on-active", "PUT", f"/api/v1/journeys/{JA}/capabilities",
     [{"code": "MAX_WALKING_PER_LEG_M", "class": "CARE_REQUIREMENT", "severity": "SOFT",
       "params": {"meters": 400}}])
call("capabilities-confirm-hard-on-active", "POST", f"/api/v1/journeys/{JA}/capabilities/confirm",
     [{"code": "STEP_FREE_REQUIRED", "class": "HARD_ACCESSIBILITY_NEED", "severity": "HARD",
       "params": {}}])
call("capabilities-PUT-hard-without-confirm", "PUT", f"/api/v1/journeys/{J}/capabilities",
     [{"code": "STEP_FREE_REQUIRED", "class": "HARD_ACCESSIBILITY_NEED", "severity": "HARD",
       "params": {}}])
call("capabilities-confirm-unknown-code", "POST", f"/api/v1/journeys/{J}/capabilities/confirm",
     [{"code": "NO_SUCH_RULE", "class": "CARE_REQUIREMENT", "severity": "SOFT", "params": {}}])

JO = journey("owner-exit")
with SessionLocal() as s:
    s.add(M.JourneyMember(id=str(uuid.uuid4()), journey_id=JO, traveler_id=T, role="OWNER",
                          invited_by=T, expires_at=None, joined_at=MOMENT, removed_at=None,
                          created_at=MOMENT, updated_at=MOMENT))
    s.commit()
call("self-exit-owner", "POST", f"/api/v1/journeys/{JO}/members/self-exit", {"traveler_id": T})

call("fixture-bogus-state", "POST", f"/api/v1/journeys/{J}/guardian/signal-fixture",
     {"state": "SIDEWAYS", "payload": {}})
call("fixture-twice", "POST", f"/api/v1/journeys/{J}/guardian/signal-fixture",
     {"state": "OUTAGE", "payload": {"note": "second"}})

RUN = "run-probe3"
call("timeline-limit-zero", "GET", f"/api/v1/journeys/{J}/agent/hermes/runs/{RUN}/timeline?limit=0")
call("timeline-unknown-journey", "GET", f"/api/v1/journeys/{uuid.uuid4()}/agent/hermes/runs/{RUN}/timeline")
call("acl-roles", "GET", f"/api/v1/journeys/{J}/acl/roles")
with SessionLocal() as s:
    rows = s.query(M.JourneyRoleCapability).all()
    print("\n[store] role capability rows =", len(rows))
    print("[store] by role =", {r: sum(1 for x in rows if x.role == r) for r in sorted({x.role for x in rows})})
    print("[store] scope_message_key set =", sorted({x.scope_message_key for x in rows}))
    print("[store] capability vocabulary =", sorted({x.capability for x in rows})[:6])
print("\n[done] probe r3")
