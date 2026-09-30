"""ORD-0511 step 1c: run the whole stay chain for real and read the store back.

Why a two-night CN-TIANJIN trip: the shipped city data (`data/v9/city_operations.json`) carries four
stays for CN-TIANJIN and one for CN-BEIJING, and `stay_mobility.city_fixture` reads exactly that file.
A one-day trip correctly answers NOT_APPLICABLE_ZERO_NIGHTS, so the demo trip in the copied preview
cannot show a candidate at all -- which is the server being honest, not the server being broken.

Each leg is measured, and the write leg is confirmed by querying the sqlite file rather than trusting
the response body.
"""
from __future__ import annotations

import json
import re
import sqlite3
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

BASE = "http://127.0.0.1:8018/api/v1"
DB = Path("D:/moodle/_qoder_n2b_ord0511_20260930/ord0511.db")
UUID_RE = re.compile(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}")
TZ = timezone(timedelta(hours=8))
log: dict = {}


def call(method: str, path: str, body: dict | None = None) -> tuple[int, str]:
    data = None if body is None else json.dumps(body).encode("utf-8")
    request = urllib.request.Request(
        f"{BASE}{path}",
        method=method,
        data=data,
        headers={"Content-Type": "application/json"} if data else {},
    )
    try:
        with urllib.request.urlopen(request, timeout=600) as response:
            return response.status, response.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as error:
        return error.code, error.read().decode("utf-8", "replace")


def rows(query: str, params: tuple = ()) -> list[tuple]:
    connection = sqlite3.connect(f"file:{DB.as_posix()}?mode=ro", uri=True)
    try:
        return connection.execute(query, params).fetchall()
    finally:
        connection.close()


status, text = call("POST", "/travelers", {"display_name": "ORD-0511 tianjin", "locale": "zh-CN", "timezone": "Asia/Shanghai"})
traveler_id = json.loads(text)["id"]

start = datetime(2026, 11, 6, 15, 0, tzinfo=TZ)
status, text = call(
    "POST",
    "/journeys",
    {
        "traveler_id": traveler_id,
        "title": "CNX-ORD0511 tianjin two nights",
        "city_code": "CN-TIANJIN",
        "timezone": "Asia/Shanghai",
        "start_at": start.isoformat(),
        "end_at": (start + timedelta(days=2, hours=6)).isoformat(),
        "budget": {"amount_minor": 200000, "currency": "CNY"},
        "planning_mode": "balanced",
    },
)
log["create_journey"] = {"http_status": status}
journey_id = json.loads(text)["id"]
log["journey_id_chars"] = len(journey_id)

# --- generate, then read the candidate list the door actually ranked
status, text = call("POST", f"/journeys/{journey_id}/stay-options/generate")
body = json.loads(text)
generation = body.get("generation") or {}
log["generate"] = {
    "http_status": status,
    "top_level_keys": sorted(body),
    "outcome": generation.get("outcome"),
    "offers_from_provider": generation.get("offers_from_provider"),
    "options_ranked": generation.get("options_ranked"),
    "rejections_by_reason": generation.get("rejections_by_reason"),
    "provider_attempts": generation.get("provider_attempts"),
    "uuid_hits_in_body": len(UUID_RE.findall(text)),
}

status, text = call("GET", f"/journeys/{journey_id}/stay-options")
read = json.loads(text)
options = read.get("options") or []
log["read_after_generate"] = {
    "http_status": status,
    "options_count": len(options),
    "offers_count": len(read.get("offers") or []),
    "selected_option_id": read.get("selected_option_id"),
    "first_option": {
        key: options[0].get(key)
        for key in ("rank", "status", "stay_total_minor", "walking_min", "protected_margin_min", "hard_constraints_passed", "materialized_plan_version_id")
    }
    if options
    else None,
    "first_option_stay_name": options[0]["stay"].get("property_name") if options else None,
    "days_of_first_option": options[0].get("days") if options else None,
}

# --- the write leg: select the top option, then prove it in the store
if options:
    option_id = options[0]["id"]
    status, text = call("POST", f"/journeys/{journey_id}/stay-options/{option_id}/select")
    entry = {"http_status": status, "uuid_hits_in_body": len(UUID_RE.findall(text))}
    try:
        parsed = json.loads(text)
        entry["top_level_keys"] = sorted(parsed)
        for key in (
            "journey_status",
            "deterministic_feasibility",
            "protected_commitments_preserved",
        ):
            entry[key] = parsed.get(key)
    except json.JSONDecodeError:
        entry["raw_head"] = text[:300]
    log["select"] = entry
    log["store_after_select"] = {
        "stay_journey_option_status": rows(
            "SELECT status, materialized_plan_version_id IS NOT NULL FROM stay_journey_options WHERE journey_id = ?",
            (journey_id,),
        ),
        "bookings": rows(
            "SELECT status, provider_key, amount_minor, amount_status, currency, commitment_id IS NOT NULL FROM bookings WHERE journey_id = ?",
            (journey_id,),
        ),
        "commitments_levels": rows(
            "SELECT kind, level, status, monetary_value_status, currency FROM commitments WHERE journey_id = ?",
            (journey_id,),
        ),
        "activities_locked": rows(
            "SELECT a.title, a.locked, c.level FROM activities a "
            "LEFT JOIN commitments c ON c.activity_id = a.id "
            "WHERE a.plan_version_id = (SELECT id FROM plan_versions WHERE journey_id = ? ORDER BY version_no DESC LIMIT 1)",
            (journey_id,),
        ),
        "plan_versions": rows(
            "SELECT version_no, status, source FROM plan_versions WHERE journey_id = ? ORDER BY version_no",
            (journey_id,),
        ),
    }

# --- refusal shapes, because the screen has to name them and not print an identifier
status, text = call("POST", f"/journeys/{journey_id}/stay-options/{'0' * 8 + '-0000-4000-8000-000000000000'}/select")
log["select_unknown_option"] = {
    "http_status": status,
    "body_head": text[:300],
    "has_reason_code": bool(re.search(r'"reason_code"', text)),
}

status, text = call("POST", f"/journeys/{journey_id}/stay-options/{journey_id}/select")
log["select_malformed_option"] = {"http_status": status, "body_head": text[:240]}

Path("D:/moodle/_qoder_n2b_ord0511_20260930/chain_r1.json").write_text(
    json.dumps(log, ensure_ascii=False, indent=1), encoding="utf-8"
)
print(json.dumps(log, ensure_ascii=False, indent=1)[:3200])
