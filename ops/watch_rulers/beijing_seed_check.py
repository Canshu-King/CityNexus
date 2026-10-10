"""Commander check: does the phone's data, upgraded to tip and given the Beijing
catalogue additively (no demo/reset, which deletes 52 tables), actually plan Beijing?

Runs against a COPY of the live preview database. Nothing here touches the live DB.
"""

from __future__ import annotations

import io
import json
import os
import shutil
import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(r"D:\moodle\_qoder_cmdr_ref_20260921")
SNAP = ROOT / "live_snapshots"
SRC = SNAP / "live_pre_tip.db"
WORK = SNAP / "live_pre_tip_seeded.db"
MOCK = ROOT / "data" / "mock"
TZ = timezone(timedelta(hours=8))

shutil.copyfile(SRC, WORK)
for suffix in ("-wal", "-shm"):
    if Path(str(WORK) + suffix).exists():
        Path(str(WORK) + suffix).unlink()

# ---- additive seed: exactly the rows seed_demo() would write for CN-BEIJING ----
con = sqlite3.connect(WORK)
cur = con.cursor()
before = dict(cur.execute("SELECT city_code, count(*) FROM places GROUP BY city_code").fetchall())

places = [p for p in json.load(io.open(MOCK / "places.json", encoding="utf-8"))
          if p["city_code"] == "CN-BEIJING"]
services = [s for s in json.load(io.open(MOCK / "city_services.json", encoding="utf-8"))
            if s["city_code"] == "CN-BEIJING"]
now = "2026-10-01T00:00:00+00:00"


def _columns(table: str) -> set[str]:
    return {row[1] for row in cur.execute(f"PRAGMA table_info({table})").fetchall()}


def _insert(table: str, payload: dict, *, fixed: dict) -> int:
    """Insert only the columns the table actually has — schema-relative on purpose."""

    cols = _columns(table)
    row: dict = {}
    for key, value in {**payload, **fixed}.items():
        if key not in cols:
            continue
        if isinstance(value, (dict, list)):
            value = json.dumps(value)
        row[key] = value
    if "id" not in row:
        raise RuntimeError(f"{table} row has no id: {payload}")
    if cur.execute(f"SELECT 1 FROM {table} WHERE id=?", (row["id"],)).fetchone():
        return 0
    names = ", ".join(row)
    marks = ", ".join(f":{k}" for k in row)
    cur.execute(f"INSERT INTO {table} ({names}) VALUES ({marks})", row)
    return 1


added_p = added_s = 0
for item in places:
    added_p += _insert(
        "places",
        {
            **item,
            "latitude": item["location"]["latitude"],
            "longitude": item["location"]["longitude"],
            "opening_hours_json": {"open": item["open"], "close": item["close"]},
            "tags_json": item["tags"],
            "metadata_json": {"duration_min": item["duration_min"], "cost_minor": item["cost_minor"]},
        },
        fixed={"created_at": now, "updated_at": now},
    )
for item in services:
    added_s += _insert(
        "city_services",
        {**item, "availability_json": item.get("availability", {})},
        fixed={"created_at": now, "updated_at": now, "metadata_json": {}},
    )
con.commit()
after = dict(cur.execute("SELECT city_code, count(*) FROM places GROUP BY city_code").fetchall())
svc = dict(cur.execute("SELECT city_code, count(*) FROM city_services GROUP BY city_code").fetchall())
journeys = cur.execute("SELECT id, title, city_code, status FROM journeys").fetchall()
print(f"seeded places +{added_p} services +{added_s}")
print("places by city:", after)
print("city_services by city:", svc)
print("journeys kept:", journeys)
con.close()

# ---- now exercise the tip app against that copy ----
os.environ["CITYNEXUS_DATABASE_URL"] = f"sqlite:///{WORK.as_posix()}"
for k in ("DEEPSEEK_API_KEY", "OPENAI_API_KEY", "CITYNEXUS_AI_KEY", "CITYNEXUS_AI_MODEL",
          "CITYNEXUS_AI_API_KEY", "CITYNEXUS_LIVE_VALHALLA_URL"):
    os.environ.pop(k, None)
sys.path.insert(0, str(ROOT / "backend"))

from fastapi.testclient import TestClient  # noqa: E402
from app.main import app  # noqa: E402

client = TestClient(app)
print("health ->", client.get("/api/v1/health").status_code)

def _candidates(body) -> list:
    """plans/generate answers a bare list here and an object elsewhere; normalise both."""

    if isinstance(body, list):
        return body
    if isinstance(body, dict):
        return body.get("candidates") or body.get("plans") or []
    return []


for q in ({"query": "CN-BEIJING"}, {"city_code": "CN-BEIJING"}):
    cap = client.get("/api/v1/destinations/capability", params=q)
    print(f"capability {q} ->", cap.status_code,
          json.dumps(cap.json(), ensure_ascii=False)[:600])

con = sqlite3.connect(WORK)
row = con.execute(
    "SELECT id, traveler_id, title, start_at, end_at, budget_amount_minor FROM journeys"
    " WHERE city_code='CN-BEIJING' ORDER BY created_at LIMIT 1"
).fetchone()
con.close()
if row is None:
    print("no CN-BEIJING journey in the copy — creating one")
    traveler_id = client.post("/api/v1/travelers", json={
        "display_name": "cmdr probe", "email": "cmdr@probe.local"}).json()["id"]
    r = client.post("/api/v1/journeys", json={
        "traveler_id": traveler_id,
        "title": "北京两日 · 指挥亲测",
        "city_code": "CN-BEIJING",
        "timezone": "Asia/Shanghai",
        "start_at": datetime(2026, 9, 22, 9, 0, tzinfo=TZ).isoformat(),
        "end_at": datetime(2026, 9, 23, 19, 0, tzinfo=TZ).isoformat(),
        "budget": {"amount_minor": 150_000, "currency": "CNY"},
        "planning_mode": "balanced",
    })
    if r.status_code >= 400:
        raise SystemExit(f"journey create failed {r.status_code}: {r.text[:400]}")
    jid = r.json()["id"]
else:
    jid, traveler_id, title, start_at, end_at, budget = row
    print(f"reusing the user's own journey {jid[:8]} title={title!r} "
          f"{start_at} → {end_at} budget={budget}")

gen = client.post(f"/api/v1/journeys/{jid}/plans/generate", json={})
body = gen.json()
print("default plans/generate ->", gen.status_code,
      "candidates:", len(_candidates(body)),
      json.dumps(body, ensure_ascii=False)[:400] if gen.status_code >= 400 else "")

places_resp = client.get("/api/v1/places", params={"city_code": "CN-BEIJING"})
payload = places_resp.json()
items = payload.get("items") if isinstance(payload, dict) else payload
if items is None:
    print("GET /places shape unexpected:", json.dumps(payload, ensure_ascii=False)[:300])
    items = []
ids = [p["id"] for p in items if str(p.get("city_code", "CN-BEIJING")) == "CN-BEIJING"]
print(f"GET /places CN-BEIJING -> {places_resp.status_code} {len(ids)} ids", ids[:3])
gen2 = client.post(f"/api/v1/journeys/{jid}/plans/generate", json={"place_ids": ids[:8]})
b2 = gen2.json()
print("explicit-place_ids plans/generate ->", gen2.status_code,
      "candidates:", len(_candidates(b2)),
      json.dumps(b2, ensure_ascii=False)[:400] if gen2.status_code >= 400 else "")
