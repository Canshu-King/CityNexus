"""Live-server proof of the two Beijing paths, through the public tunnel.

Creates its OWN probe journey (the user's 94669bae is left alone) and asks the same question the
phone asks in each of its two shapes:

  A. the plain "生成方案" path  -> POST plans/generate {}
  B. the AI sheet path       -> POST plans/generate {place_ids: [...]} with the 8 ids the sheet
                                would put on the wire (GET /places?city_code=CN-BEIJING, slice 0..8)

Result of the run before this file existed (clean copy of the DB at tip, TestClient): A -> 3
candidates, B -> 422 PLACE_CLOSED on 5 of 8 places. This script asks whether the live preview
behaves the same, because the sheet is what the user actually taps.
"""

import base64
import json
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone

BASE = "https://fonts-facilities-hotel-installing.trycloudflare.com"
AUTH = r"D:\moodle\_qoder_preview_20260920\run\preview_auth.txt"
TZ = timezone(timedelta(hours=8))
user, secret = open(AUTH, encoding="utf-8").read().strip().split("\t")
TOKEN = base64.b64encode(f"{user}:{secret}".encode()).decode()


def call(method, path, payload=None, timeout=90):
    req = urllib.request.Request(BASE + path, method=method)
    req.add_header("Authorization", "Basic " + TOKEN)
    data = None
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        req.add_header("Content-Type", "application/json")
    started = time.time()
    try:
        with urllib.request.urlopen(req, data, timeout=timeout) as resp:
            return resp.status, resp.read().decode("utf-8", "replace"), round(time.time() - started, 2)
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8", "replace"), round(time.time() - started, 2)
    except Exception as exc:  # noqa: BLE001
        return type(exc).__name__, str(exc), round(time.time() - started, 2)


def candidates(body):
    try:
        payload = json.loads(body)
    except Exception:  # noqa: BLE001
        return None
    if isinstance(payload, list):
        return payload
    return payload.get("candidates") or payload.get("plans") or []


_, traveler_body, _ = call("GET", "/api/v1/demo/scene")
traveler_id = json.loads(traveler_body).get("traveler_id") or "11111111-1111-4111-8111-111111111111"
start = datetime(2026, 9, 26, 9, 0, tzinfo=TZ)
status, body, secs = call("POST", "/api/v1/journeys", {
    "traveler_id": traveler_id,
    "title": "指挥亲测 · 北京两日",
    "city_code": "CN-BEIJING",
    "timezone": "Asia/Shanghai",
    "start_at": start.isoformat(),
    "end_at": (start + timedelta(days=1, hours=10)).isoformat(),
    "budget": {"amount_minor": 300_000, "currency": "CNY"},
    "planning_mode": "balanced",
})
print(f"probe journey -> {status} ({secs}s)")
if status != 201:
    print(body[:400])
    raise SystemExit(1)
jid = json.loads(body)["id"]
print("probe journey id", jid)

status, body, secs = call("POST", f"/api/v1/journeys/{jid}/plans/generate", {})
cands = candidates(body)
print(f"A default path -> {status} ({secs}s) candidates={len(cands) if cands is not None else '?'}")
if cands:
    for item in cands[:3]:
        acts = item.get("activities") or item.get("items") or []
        print(f"   * {item.get('id', '?')[:8]} label={item.get('label') or item.get('name')}"
              f" activities={len(acts)} selectable={item.get('selectable', item.get('is_selectable'))}"
              f" cost={item.get('total_cost_minor') or item.get('cost_minor')}")
else:
    print("   ", body[:400])

status, body, secs = call("GET", "/api/v1/places?city_code=CN-BEIJING")
payload = json.loads(body)
items = payload.get("items") if isinstance(payload, dict) else payload
ids = [p["id"] for p in (items or [])][:8]
print(f"B sheet's id list -> {status} n={len(ids)}")
status, body, secs = call("POST", f"/api/v1/journeys/{jid}/plans/generate", {"place_ids": ids})
cands = candidates(body)
print(f"B explicit place_ids (8, exactly what the sheet sends) -> {status} ({secs}s)"
      f" candidates={len(cands) if cands is not None else '?'}")
print("   ", body[:420])

# and the same request one place smaller, to see whether the refusal is about size
status, body, secs = call("POST", f"/api/v1/journeys/{jid}/plans/generate", {"place_ids": ids[:5]})
cands = candidates(body)
print(f"B' explicit place_ids (5) -> {status} candidates={len(cands) if cands is not None else '?'}")
print("   ", body[:300] if not cands else "ok")
