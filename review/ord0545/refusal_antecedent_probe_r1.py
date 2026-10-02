"""Probe 2: does the traveller's own next step really get a named refusal?

Path (all product doors, no stub): POST /api/v1/journeys -> the created row has
active_plan_version_id = NULL (backend/app/main.py sets it None) -> parse the traveller's own pasted
text -> POST poi-import/add with a place id this city really has.

If the answer is 409 with error.reason_code == NO_ACTIVE_PLAN, then the panel's seventh family member
has a real route to the glass, and the e2e slice can read it off the screen.
"""
from __future__ import annotations

import json
import sqlite3
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

BASE = "http://127.0.0.1:4911/api/v1"
LANE_DB = Path("D:/moodle/_qoder_newlane_ord0533_data/_ord0533-lane_r9.db")
OUT = Path("D:/moodle/_qoder_newlane_ord0545_data/refusal_probe_r9_b.json")
OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def send(method: str, path: str, body: dict | None = None) -> tuple[int, dict, str]:
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(
        f"{BASE}{path}", data=data, method=method, headers={"Content-Type": "application/json"}
    )
    try:
        with OPENER.open(req, timeout=60) as resp:
            raw = resp.read().decode("utf-8", "replace")
            return resp.status, (json.loads(raw) if raw.strip() else {}), raw
    except urllib.error.HTTPError as err:
        raw = err.read().decode("utf-8", "replace")
        try:
            return err.code, json.loads(raw), raw
        except json.JSONDecodeError:
            return err.code, {}, raw


with sqlite3.connect(f"file:{LANE_DB.as_posix()}?mode=ro", uri=True) as conn:
    conn.row_factory = sqlite3.Row
    traveler = dict(conn.execute("select id, locale from travelers limit 1").fetchone())
    city = conn.execute(
        "select city_code, count(*) n from places where city_code='CNX-DEMO' group by city_code"
    ).fetchone()
    place = dict(
        conn.execute(
            "select id, name, city_code, category from places where city_code='CNX-DEMO' "
            "order by name limit 1"
        ).fetchone()
    )

now = datetime.now(timezone.utc)
created_status, created, _ = send("POST", "/journeys", {
    "traveler_id": traveler["id"],
    "title": "ORD-0545 slice 3 probe -- created, not yet planned",
    "city_code": "CNX-DEMO",
    "timezone": "Asia/Shanghai",
    "start_at": (now + timedelta(days=40)).isoformat(),
    "end_at": (now + timedelta(days=42)).isoformat(),
    "budget": {"amount_minor": 90000, "currency": "CNY"},
    "planning_mode": "balanced",
    "party_size": 2,
})
journey_id = created.get("id")
read_status, read_back, _ = send("GET", f"/journeys/{journey_id}")
parse_status, parsed, _ = send(
    "POST", f"/journeys/{journey_id}/poi-import/parse", {"text": f"{place['name']}"}
)
add_status, add_body, add_raw = send(
    "POST", f"/journeys/{journey_id}/poi-import/add", {"place_ids": [place["id"]]}
)

report = {
    "journey_created": {"status": created_status, "id": journey_id},
    "journey_read_back": {
        "status": read_status,
        "active_plan_version_id": read_back.get("active_plan_version_id"),
        "journey_status": read_back.get("status"),
    },
    "catalogue_row_used": {"id": place["id"], "name": place["name"], "city": place["city_code"],
                           "category": place["category"], "cn_demo_place_count": city["n"]},
    "parse": {
        "status": parse_status,
        "items": [{"title": i.get("title"), "status": i.get("status"),
                   "place_id": i.get("place_id")} for i in (parsed.get("items") or [])],
    },
    "add": {
        "status": add_status,
        "reason_code": (add_body.get("error") or {}).get("reason_code")
        if isinstance(add_body.get("error"), dict) else None,
        "message": (add_body.get("error") or {}).get("message")
        if isinstance(add_body.get("error"), dict) else None,
        "raw_head": add_raw[:200],
    },
    "measured_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
}
OUT.write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
print(str(OUT))
print(json.dumps(report["journey_read_back"], ensure_ascii=False))
print(json.dumps(report["add"], ensure_ascii=False)[:400])
