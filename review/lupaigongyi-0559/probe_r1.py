"""ORD-0559 路牌工乙 probe: fire each of the nine doors for real and dump the reply shapes.

A readout instrument, not a test.  It declares the same environment `backend/tests/conftest.py`
declares (demo mode, an isolated temporary database, provider credentials cleared) so the shapes
below describe the same process the suite runs in.  Nothing here mocks anything inside the app.
"""

from __future__ import annotations

import json
import os
import pathlib
import sys
import tempfile
import uuid
from datetime import datetime, timedelta, timezone

BACKEND = pathlib.Path(__file__).resolve().parents[2] / "backend"
sys.path.insert(0, str(BACKEND))
sys.path.insert(0, str(BACKEND / "tests"))
sys.path.insert(0, str(BACKEND.parent))

_TEMP = pathlib.Path(tempfile.mkdtemp(prefix="cnx_probe_lpy_"))
os.environ["CITYNEXUS_DATABASE_URL"] = f"sqlite:///{(_TEMP / 'probe.db').as_posix()}"
os.environ["CITYNEXUS_DEMO_MODE"] = "true"
os.environ["CITYNEXUS_DEMO_RESET_TOKEN"] = uuid.uuid4().hex
for _name in (
    "DEEPSEEK_API_KEY", "OPENAI_API_KEY", "CITYNEXUS_AI_API_KEY", "CITYNEXUS_AI_ENABLED",
    "CITYNEXUS_HERMES_API_KEY", "CITYNEXUS_HERMES_API_SERVER_KEY",
):
    os.environ.pop(_name, None)

from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import select  # noqa: E402

from app.core.audit import record_audit  # noqa: E402
from app.db import models as M  # noqa: E402
from app.db.models import Base  # noqa: E402
from app.db.session import SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from demo_stage import demo_reset_headers  # noqa: E402

Base.metadata.create_all(engine)
client = TestClient(app, raise_server_exceptions=False)
NOW = datetime.now(timezone.utc)
MOMENT = NOW.isoformat()
START = (NOW + timedelta(days=210)).isoformat()
END = (NOW + timedelta(days=212)).isoformat()
CURSOR = (NOW - timedelta(hours=1)).isoformat()


def door(journey_id: str, tail: str = "") -> str:
    base = f"/api/v1/journeys/{journey_id}"
    return base if not tail else f"{base}/{tail}"


def show(label: str, response) -> None:
    print(f"\n=== {label} -> http_status={response.status_code}")
    ctype = response.headers.get("content-type", "")
    print(f"    content-type={ctype}")
    if "event-stream" in ctype:
        print("    body<<<")
        print(response.text[:1800])
        print("    >>>")
        return
    try:
        body = response.json()
    except Exception:
        print(f"    raw={response.text[:300]!r}")
        return
    if isinstance(body, dict):
        print(f"    keys={sorted(body)}")
    print("    body<<<")
    print(json.dumps(body, ensure_ascii=False, default=str)[:2200])
    print("    >>>")


def traveler(tag: str) -> str:
    ident = str(uuid.uuid4())
    with SessionLocal() as session:
        session.add(M.Traveler(id=ident, display_name=f"probe {tag}", email=None, locale="zh-CN",
                               timezone="Asia/Shanghai", created_at=MOMENT, updated_at=MOMENT))
        session.commit()
    return ident


def journey(tag: str, city: str = "CN-XIAMEN") -> tuple[str, str]:
    traveler_id = traveler(tag)
    ident = str(uuid.uuid4())
    with SessionLocal() as session:
        session.add(M.Journey(id=ident, traveler_id=traveler_id, title=f"probe {tag}",
                              city_code=city, timezone="Asia/Shanghai", start_at=START, end_at=END,
                              budget_amount_minor=120000, budget_currency="CNY", status="PLANNED",
                              created_at=MOMENT, updated_at=MOMENT))
        session.commit()
    return ident, traveler_id


print(f"PROBE_DATABASE={os.environ['CITYNEXUS_DATABASE_URL']}")

# ---- 1 GET outcomes ---------------------------------------------------------------
jid, tid = journey("outcomes")
show("outcomes empty", client.get(door(jid, "outcomes")))
with SessionLocal() as session:
    session.add(M.JourneyOutcomeEvent(
        id=str(uuid.uuid4()), journey_id=jid, activity_id=None, event_type="activity.completed",
        actor_type="USER", actor_id=tid, occurred_at_actual=(NOW - timedelta(days=1)).isoformat(),
        planned_start_at=START, planned_end_at=END, source="DOMAIN", related_proposal_id=None,
        related_agent_run_id=None, payload_json=json.dumps({"probe": True}), created_at=MOMENT))
    session.add(M.JourneyOutcomeEvent(
        id=str(uuid.uuid4()), journey_id=jid, activity_id=None, event_type="activity.skipped",
        actor_type="AGENT", actor_id=None, occurred_at_actual=NOW.isoformat(),
        planned_start_at=None, planned_end_at=None, source="MANUAL", related_proposal_id=None,
        related_agent_run_id=None, payload_json="{}", created_at=MOMENT))
    session.commit()
show("outcomes two rows", client.get(door(jid, "outcomes")))
show("outcomes unknown journey", client.get(door(str(uuid.uuid4()), "outcomes")))

# ---- 2 GET web-observations -------------------------------------------------------
jid2, _ = journey("web")
show("web-observations empty", client.get(door(jid2, "web-observations")))
with SessionLocal() as session:
    session.add(M.WebObservation(
        id=str(uuid.uuid4()), journey_id=jid2, query="厦门 周末 展览", url="https://example.org/a",
        domain="example.org", title="Exhibition", source_class="OPEN_WEB",
        provider_key="deepseek_responses", model_key="deepseek-v3", captured_at=MOMENT,
        evidence_fingerprint="f" * 16, content_excerpt="excerpt",
        authority_status="NON_AUTHORITATIVE", created_at=MOMENT))
    session.commit()
show("web-observations one row", client.get(door(jid2, "web-observations")))
show("web-observations unknown journey", client.get(door(str(uuid.uuid4()), "web-observations")))

# ---- 3 GET stay-mobility/providers ------------------------------------------------
jid3, _ = journey("providers")
show("stay-mobility/providers", client.get(door(jid3, "stay-mobility/providers")))
show("stay-mobility/providers unknown", client.get(door(str(uuid.uuid4()), "stay-mobility/providers")))

# ---- 4 POST stays/search ----------------------------------------------------------
jid4, _ = journey("stays-tj", "CN-TIANJIN")
show("stays/search tianjin with query", client.post(door(jid4, "stays/search"), json={"query": "probe stay"}))
jid4b, _ = journey("stays-tj2", "CN-TIANJIN")
show("stays/search tianjin empty body", client.post(door(jid4b, "stays/search"), json={}))
show("stays/search unknown journey", client.post(door(str(uuid.uuid4()), "stays/search"), json={}))

# ---- 5 GET operations/stream ------------------------------------------------------
jid5, _ = journey("stream")
with SessionLocal() as session:
    record_audit(session, action="trip_studio.accepted", entity_type="PlanVersion",
                 entity_id="probe-plan", journey_id=jid5, actor_type="USER", actor_id=jid5,
                 after={"summary": "probe summary", "new_plan_version_id": "probe-plan",
                        "reason_codes": ["PROBE"]})
    session.commit()
show("stream replay from cursor", client.get(door(jid5, "operations/stream") + f"?after={CURSOR}&timeout_seconds=0.6"))
show("stream heartbeat only", client.get(door(jid5, "operations/stream") + f"?after={END}&timeout_seconds=0.6"))
show("stream unknown journey", client.get(door(str(uuid.uuid4()), "operations/stream") + "?timeout_seconds=0.6"))
show("stream timeout out of range", client.get(door(jid5, "operations/stream") + "?timeout_seconds=999"))

# ---- 6 POST recovery/acknowledge --------------------------------------------------
jid6, _ = journey("recovery")
show("recovery/acknowledge no open event", client.post(door(jid6, "recovery/acknowledge")))
with SessionLocal() as session:
    session.add(M.Event(
        id=str(uuid.uuid4()), journey_id=jid6, event_type="USER_CHANGE",
        provider_key="citynexus-capability-recovery", status="DETECTED", severity="MAJOR",
        provenance="SIMULATED", occurred_at=MOMENT, detected_at=MOMENT, resolved_at=None,
        payload_json=json.dumps({"capability_code": "PROBE"}), created_at=MOMENT))
    session.commit()
show("recovery/acknowledge open event", client.post(door(jid6, "recovery/acknowledge")))
show("recovery/acknowledge twice", client.post(door(jid6, "recovery/acknowledge")))
show("recovery/acknowledge unknown journey", client.post(door(str(uuid.uuid4()), "recovery/acknowledge")))

# ---- 7 POST provider-mesh/discover ------------------------------------------------
jid7, _ = journey("mesh", "CN-TIANJIN")
show("provider-mesh/discover default body", client.post(door(jid7, "provider-mesh/discover"), json={}))
show("provider-mesh/discover unknown journey", client.post(
    door(str(uuid.uuid4()), "provider-mesh/discover"), json={"query": "probe"}))

# ---- 8 & 9 plans preview-reorder / accept-reorder ---------------------------------
try:
    from test_v12_authoritative_trip_execution import _journey_with_inputs  # type: ignore

    reset = client.post("/api/v1/demo/reset", headers=demo_reset_headers())
    print(f"\n=== demo/reset -> http_status={reset.status_code}")
    journey_id, place_ids, commitment_id = _journey_with_inputs()
    composed = client.post(door(journey_id, "authoritative-compose"),
                           json={"place_ids": place_ids, "candidate_count": 1,
                                 "reservation_id": commitment_id})
    print(f"=== authoritative-compose -> http_status={composed.status_code}")
    if composed.status_code >= 400:
        print(composed.text[:600])
    else:
        chosen = composed.json()["top_k"][0]
        activities = chosen["activities"]
        print(f"=== composed activities titles={[item['title'] for item in activities]}")
        selected = client.post(f"/api/v1/journeys/{journey_id}/plans/{chosen['id']}/select")
        print(f"=== select -> http_status={selected.status_code}")
        canonical = [item["id"] for item in activities]
        swapped = list(canonical)
        swapped[0], swapped[-1] = swapped[-1], swapped[0]
        show("preview-reorder canonical order", client.post(
            door(journey_id, "plans/preview-reorder"), json={"activity_ids": canonical}))
        preview = client.post(door(journey_id, "plans/preview-reorder"),
                              json={"activity_ids": swapped}).json()
        show("preview-reorder swapped order", client.post(
            door(journey_id, "plans/preview-reorder"), json={"activity_ids": swapped}))
        show("preview-reorder draft_order alias field", client.post(
            door(journey_id, "plans/preview-reorder"),
            json={"activity_ids": canonical, "draft_order": swapped}))
        show("accept-reorder swapped + preview id", client.post(
            door(journey_id, "plans/accept-reorder"),
            json={"activity_ids": swapped, "preview_id": preview.get("preview_id")}))
        show("accept-reorder stale preview id", client.post(
            door(journey_id, "plans/accept-reorder"),
            json={"activity_ids": canonical, "preview_id": str(uuid.uuid4())}))
        show("accept-reorder unknown journey", client.post(
            door(str(uuid.uuid4()), "plans/accept-reorder"), json={"activity_ids": canonical}))
        show("preview-reorder partial order", client.post(
            door(journey_id, "plans/preview-reorder"), json={"activity_ids": canonical[:1]}))
except Exception as exc:  # noqa: BLE001
    print(f"\n=== trip-studio probe failed: {type(exc).__name__}: {exc}")

print("\nPROBE DONE")
