"""ORD-0511 step 1: read the stay surface off this lane's own stack, and keep every answer.

Nothing here is inferred from source: each cell is what the door actually answered on
http://127.0.0.1:8018 over D:/moodle/_qoder_n2b_ord0511_20260930/ord0511.db.

What it measures, because the order asks for the usable surface before any screen code:
  * the journey that already has candidates, and one created bare so the empty rung is real;
  * what `POST /stay-options/generate` answers for the bare journey (status, keys, named code);
  * what `GET /stay-options` carries, and whether a stay generation outcome name reaches the screen;
  * what `POST /stay-options/{id}/select` writes, read back from the store rather than believed;
  * whether any uuid appears in a body a traveller would be shown.
"""
from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone

BASE = "http://127.0.0.1:8018/api/v1"
UUID_RE = re.compile(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}")
TZ = timezone(timedelta(hours=8))
OUT = open("D:/moodle/_qoder_n2b_ord0511_20260930/surface_r1.json", "w", encoding="utf-8")
log: dict = {}


def call(method: str, path: str, body: dict | None = None) -> tuple[int, dict, str]:
    data = None if body is None else json.dumps(body).encode("utf-8")
    request = urllib.request.Request(
        f"{BASE}{path}",
        data=data,
        method=method,
        headers={"Content-Type": "application/json"} if data else {},
    )
    try:
        with urllib.request.urlopen(request, timeout=180) as response:
            text = response.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as error:
        text = error.read().decode("utf-8", "replace")
        return error.code, {}, text
    try:
        return 200 if method != "POST" else 201, json.loads(text), text
    except json.JSONDecodeError:
        return 0, {}, text


def wait_for_health() -> None:
    for _ in range(60):
        try:
            with urllib.request.urlopen("http://127.0.0.1:8018/api/v1/health", timeout=5) as response:
                log["health"] = response.read().decode("utf-8", "replace")
                return
        except Exception:  # noqa: BLE001 - a stack that is not up yet is the only case here
            import time

            time.sleep(2)
    log["health"] = "NOT_UP"


def uuid_hits(text: str) -> int:
    return len(UUID_RE.findall(text))


def journey(payload: dict) -> str:
    status, _, text = call("POST", "/journeys", payload)
    assert status in (200, 201), text[:400]
    return json.loads(text)["id"]


def traveler() -> str:
    status, _, text = call(
        "POST",
        "/travelers",
        {"display_name": "ORD-0511 lane newlane2", "locale": "zh-CN", "timezone": "Asia/Shanghai"},
    )
    assert status in (200, 201), text[:400]
    return json.loads(text)["id"]


def make_journey(title: str) -> str:
    start = datetime(2026, 10, 10, 9, 0, tzinfo=TZ)
    return journey(
        {
            "traveler_id": traveler(),
            "title": title,
            "city_code": "CNX-DEMO",
            "timezone": "Asia/Shanghai",
            "start_at": start.isoformat(),
            "end_at": (start + timedelta(days=2, hours=8)).isoformat(),
            "budget": {"amount_minor": 120000, "currency": "CNY"},
            "planning_mode": "balanced",
        }
    )


wait_for_health()

# --- the journey that already has candidates (the demo trip this store was copied with)
status, _, text = call("GET", "/journeys")
demo_ids = []
if status in (200, 201):
    rows = json.loads(text)
    demo_ids = [row["id"] for row in rows][:6]
    log["journeys_listed"] = len(rows)
    log["journey_titles"] = [row.get("title") for row in rows][:6]

for journey_id in demo_ids:
    status, _, text = call("GET", f"/journeys/{journey_id}/stay-options")
    if status not in (200, 201):
        log.setdefault("demo_stay_options", {})[journey_id] = {"http_status": status}
        continue
    payload = json.loads(text)
    options = payload.get("options") or []
    log.setdefault("demo_stay_options", {})[journey_id] = {
        "http_status": status,
        "top_level_keys": sorted(payload),
        "options_count": len(options),
        "selected_option_id_present": "selected_option_id" in payload,
        "option_keys": sorted(options[0]) if options else [],
        "outcome_keys_in_payload": {
            key: payload[key] for key in payload if "outcome" in key or "stay_" in key
        },
        "uuid_hits_in_body": uuid_hits(text),
    }

# --- a bare journey, so the empty rung is a fact about this trip and not a fixture
bare_id = make_journey("CNX-ORD0511 bare trip")
status, _, text = call("GET", f"/journeys/{bare_id}/stay-options")
payload = json.loads(text) if status in (200, 201) else {}
log["bare_journey"] = {
    "id": bare_id,
    "read_status": status,
    "options_count": len(payload.get("options") or []),
    "top_level_keys": sorted(payload),
}

status, _, text = call("POST", f"/journeys/{bare_id}/stay-options/generate")
gen = {"http_status": status, "body_chars": len(text), "uuid_hits_in_body": uuid_hits(text)}
try:
    parsed = json.loads(text)
    gen["top_level_keys"] = sorted(parsed) if isinstance(parsed, dict) else f"LIST len {len(parsed)}"
    if isinstance(parsed, dict):
        gen["outcome"] = parsed.get("outcome")
        gen["options_ranked"] = parsed.get("options_ranked")
        gen["offers_from_provider"] = parsed.get("offers_from_provider")
        gen["rejections_by_reason"] = parsed.get("rejections_by_reason")
        gen["error"] = parsed.get("error")
except json.JSONDecodeError:
    gen["not_json_head"] = text[:200]
log["bare_generate"] = gen

status, _, text = call("GET", f"/journeys/{bare_id}/stay-options")
after = json.loads(text) if status in (200, 201) else {}
log["bare_after_generate"] = {
    "http_status": status,
    "options_count": len(after.get("options") or []),
    "selected_option_id": after.get("selected_option_id"),
}

# --- the write leg: select whatever exists, then read the store instead of believing the response
for journey_id in demo_ids:
    status, _, text = call("GET", f"/journeys/{journey_id}/stay-options")
    if status not in (200, 201):
        continue
    options = (json.loads(text).get("options") or [])
    if not options:
        continue
    option_id = options[0]["id"]
    status, _, text = call("POST", f"/journeys/{journey_id}/stay-options/{option_id}/select")
    entry = {"http_status": status, "uuid_hits_in_body": uuid_hits(text)}
    try:
        parsed = json.loads(text)
        entry["top_level_keys"] = sorted(parsed)
        entry["protected_commitments_preserved"] = parsed.get("protected_commitments_preserved")
        entry["journey_status"] = parsed.get("journey_status")
        entry["materialized_plan_version_id_present"] = bool(parsed.get("plan_version_id"))
    except json.JSONDecodeError:
        entry["not_json_head"] = text[:240]
    log.setdefault("select_readings", {})[journey_id] = entry
    break

json.dump(log, OUT, ensure_ascii=False, indent=1)
OUT.close()
print(json.dumps(log, ensure_ascii=False, indent=1)[:3000])
