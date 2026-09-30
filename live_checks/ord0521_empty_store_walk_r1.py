"""ORD-0521 smoke walk: empty store -> one trip with a selected plan, or a named refusal.

Runs against a private sqlite file so the shared preview store is never touched.  Prints one line
per hop; the exit code is the verdict.
"""

import json
import os
import sqlite3
import sys

sys.path.insert(0, ".")
from fastapi.testclient import TestClient  # noqa: E402

import app.main as m  # noqa: E402

DB = os.environ["CITYNEXUS_DATABASE_URL"].split("///")[1]
TABLES = ("journeys", "places", "city_services", "travelers", "plan_versions", "idempotency_keys")


def census():
    con = sqlite3.connect(DB)
    out = {}
    for table in TABLES:
        try:
            out[table] = con.execute(f"select count(*) from {table}").fetchone()[0]
        except sqlite3.Error:
            out[table] = "ABSENT"
    con.close()
    return out


TOKEN = {"X-Demo-Scene-Token": os.environ["CITYNEXUS_DEMO_SCENE_TOKEN"]}
failures = []


def check(label, condition, evidence):
    print(f"[{'ok' if condition else 'RED'}] {label}: {evidence}")
    if not condition:
        failures.append(label)


with TestClient(m.app) as c:
    print("census before:", json.dumps(census()))
    r = c.post("/api/v1/demo/prepare-scenario")
    check("clean store refuses prepare-scenario by name", r.status_code == 409,
          f"http_status={r.status_code} code={r.json().get('error', {}).get('code')}")

    r = c.post("/api/v1/demo/scene/ensure", json={})
    check("no token refused", r.status_code == 403,
          f"http_status={r.status_code} reason={r.json().get('reason_code')}")
    r = c.post("/api/v1/demo/scene/ensure", headers=TOKEN, json={})
    check("no Idempotency-Key refused", r.status_code == 422, f"http_status={r.status_code}")

    r = c.post("/api/v1/demo/scene/ensure", headers={**TOKEN, "Idempotency-Key": "walk-1"}, json={})
    d = r.json()
    check("door answers 200 on an empty store", r.status_code == 200, f"http_status={r.status_code}")
    check("supply names its leg", d.get("supply", {}).get("supply_leg", "").startswith("builtin_fixture:"),
          d.get("supply", {}).get("supply_leg"))
    check("supply is additive", d.get("supply", {}).get("rows_deleted") == 0,
          f"installed={d.get('supply',{}).get('rows_installed')} already={d.get('supply',{}).get('rows_already_present')}")
    check("a plan exists on the trip", bool(d.get("plan_version_id")),
          f"state={d.get('state')} plan={d.get('plan_version_id')} status={d.get('journey_status')}")
    check("no refused hop", d.get("advance_refused_steps") == [],
          json.dumps(d.get("advance", {}).get("steps"), ensure_ascii=False))

    after = census()
    print("census after:", json.dumps(after))

    r = c.post("/api/v1/demo/prepare-scenario")
    p = r.json()
    refused = [s for s in p.get("advance", {}).get("steps", []) if "refused" in s]
    check("cell(1): prepare-scenario no longer refuses", r.status_code == 200 and not refused and p.get("plan_version_id"),
          f"http_status={r.status_code} refused={json.dumps(refused, ensure_ascii=False)[:120]} plan={p.get('plan_version_id')}")

    r = c.post("/api/v1/demo/scene/ensure", headers={**TOKEN, "Idempotency-Key": "walk-1"}, json={})
    check("same key replays the same trip", r.json().get("idempotency_replay") and
          r.json().get("plan_version_id") == d.get("plan_version_id"),
          f"http_status={r.status_code} replay={r.json().get('idempotency_replay')}")

    r = c.post("/api/v1/demo/scene/ensure", headers={**TOKEN, "Idempotency-Key": "walk-1"},
               json={"city_code": "CN-BEIJING"})
    check("same key, other body conflicts", r.status_code == 422,
          f"http_status={r.status_code} reason={r.json().get('reason_code')}")

    r = c.post("/api/v1/demo/scene/ensure", headers={**TOKEN, "Idempotency-Key": "tidy-9"},
               json={"city_code": "CN-TIDY"})
    body = r.json().get("error", {})
    check("cell(3): an unsupplied destination says so readably", r.status_code == 409 and
          "cannot obtain places" in str(body.get("message")) and body.get("details", {}).get("failed_hop"),
          f"http_status={r.status_code} reason={r.json().get('reason_code')} message={str(body.get('message'))[:110]}")

    print("census final:", json.dumps(census()))
    con = sqlite3.connect(DB)
    print("journeys:", con.execute("select rowid,id,city_code,status,active_plan_version_id from journeys order by rowid").fetchall())
    print("places leg:", con.execute("select rowid,provider_key,city_code,name from places order by rowid limit 2").fetchall())
    con.close()

print("VERDICT:", "GREEN" if not failures else f"RED {failures}")
sys.exit(0 if not failures else 1)
