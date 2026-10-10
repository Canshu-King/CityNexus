"""ORD-0559 路牌工甲 probe r4: what window makes authoritative-compose answer 201, plus two arms r3 left open."""

from __future__ import annotations

import json
import os
import pathlib
import tempfile
import uuid
from datetime import datetime, timedelta, timezone

_TMP = pathlib.Path(tempfile.mkdtemp(prefix="cnx_probe4_"))
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
        return json.dumps(value[:50])
    return repr(value)


T = str(uuid.uuid4())
with SessionLocal() as s:
    s.add(M.Traveler(id=T, display_name="probe4", email=None, locale="zh-CN",
                     timezone="Asia/Shanghai", created_at=MOMENT, updated_at=MOMENT))
    s.commit()

CASES = [
    ("three-day-evening", "2031-05-01T09:00:00+00:00", "2031-05-04T18:00:00+00:00", 4),
    ("two-day-evening", "2031-05-01T09:00:00+00:00", "2031-05-03T20:00:00+00:00", 3),
    ("one-day-evening", "2031-05-01T09:00:00+00:00", "2031-05-01T21:00:00+00:00", 2),
    ("one-day-wide", "2031-05-01T08:00:00+00:00", "2031-05-02T22:00:00+00:00", 2),
]

for tag, start_at, end_at, n_places in CASES:
    J = str(uuid.uuid4())
    with SessionLocal() as s:
        s.add(M.Journey(id=J, traveler_id=T, title=f"沿海一周 {tag}", city_code="CN-XIAMEN",
                        timezone="Asia/Shanghai", start_at=start_at, end_at=end_at,
                        budget_amount_minor=600000, budget_currency="CNY", status="PLANNED",
                        created_at=MOMENT, updated_at=MOMENT))
        s.commit()
    ids = []
    with SessionLocal() as s:
        for n in range(n_places):
            pid = str(uuid.uuid4())
            ids.append(pid)
            s.add(M.Place(id=pid, provider_key="probe", external_id=f"{tag}-{n}",
                          city_code="CN-XIAMEN", name=f"探针点 {n}", category="sight",
                          latitude=24.45 + n * 0.005, longitude=118.05 + n * 0.005,
                          opening_hours_json="{}", tags_json="[]",
                          metadata_json=json.dumps({"cost_minor": 2000, "duration_min": 45,
                                                   "cost_status": "KNOWN"}), updated_at=MOMENT))
        s.commit()
    r = client.post(f"/api/v1/journeys/{J}/authoritative-compose",
                    json={"place_ids": ids, "candidate_count": 2})
    try:
        payload = r.json()
    except Exception:
        payload = {"__text__": r.text[:120]}
    print(f"\n## compose {tag} places={n_places} -> http_status={r.status_code}")
    print("   " + shape(payload)[:1500])

# fixture revision increments on the same journey
J2 = str(uuid.uuid4())
with SessionLocal() as s:
    s.add(M.Journey(id=J2, traveler_id=T, title="沿海一周 revision", city_code="CN-XIAMEN",
                    timezone="Asia/Shanghai", start_at="2031-05-01T09:00:00+00:00",
                    end_at="2031-05-03T20:00:00+00:00", budget_amount_minor=120000,
                    budget_currency="CNY", status="PLANNED", created_at=MOMENT, updated_at=MOMENT))
    s.commit()
first = client.post(f"/api/v1/journeys/{J2}/guardian/signal-fixture",
                    json={"state": "NORMAL", "payload": {"note": "one"}}).json()
second = client.post(f"/api/v1/journeys/{J2}/guardian/signal-fixture",
                     json={"state": "RISK_FORECAST", "payload": {"note": "two"}}).json()
print("\n## fixture revisions ->", first.get("revision"), second.get("revision"),
      "| provider_key =", second.get("provider_key"))
with SessionLocal() as s:
    rows = s.query(M.AuditLog).filter(M.AuditLog.action == "city.signal.fixture.updated").all()
    print("   audit rows =", len(rows))
    print("   after_json =", repr(rows[-1].after_json[:220]) if rows else None)

# timeline for a run with no persisted events
J3 = J2
r = client.get(f"/api/v1/journeys/{J3}/agent/hermes/runs/run-never-seen/timeline")
print("\n## timeline-empty ->", r.status_code, shape(r.json())[:700])
print("\n[done] probe r4")
