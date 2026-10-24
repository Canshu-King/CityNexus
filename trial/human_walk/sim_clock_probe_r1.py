"""Read-only probe for the simulation clock: gate on, first read, +60, re-read, stale version."""
from __future__ import annotations

import io
import json
import sqlite3
import urllib.error
import urllib.request

DB = r"D:/moodle/_cmdr_v3_live_1022/citynexus_v3_play_1024.db"
API = "http://127.0.0.1:60361"
OUT = r"D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261022_v3_human_chrome/sim-clock-1.txt"
lines: list[str] = []


def note(value: str) -> None:
    lines.append(value)
    io.open(OUT, "w", encoding="utf-8", newline="\n").write("\n".join(lines) + "\n")


def call(method: str, path: str, body: dict | None = None) -> tuple[int, dict]:
    data = json.dumps(body).encode("utf-8") if body is not None else None
    request = urllib.request.Request(API + path, data=data, method=method)
    if data is not None:
        request.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(request, timeout=20) as answer:
            raw = answer.read().decode("utf-8")
            return answer.status, (json.loads(raw) if raw else {})
    except urllib.error.HTTPError as error:
        raw = error.read().decode("utf-8")
        try:
            payload = json.loads(raw) if raw else {}
        except ValueError:
            payload = {"raw": raw[:200]}
        return error.code, payload


connection = sqlite3.connect("file:" + DB + "?mode=ro", uri=True)
row = connection.execute(
    "select id from journeys where deleted_at is null order by created_at desc limit 1"
).fetchone()
journey_id = row[0]
note("JOURNEY " + journey_id)

status, first = call("GET", f"/api/v1/demo/simulation-clock/{journey_id}")
note("GET1 " + json.dumps({"status": status, "virtual_now": first.get("virtual_now"),
                           "version": first.get("version"), "persisted": first.get("persisted"),
                           "basis": first.get("basis"), "traveller": first.get("traveller"),
                           "activity": first.get("current_activity_title")}, ensure_ascii=False))

status, advanced = call("POST", f"/api/v1/demo/simulation-clock/{journey_id}/advance",
                        {"minutes": 60, "expected_version": first.get("version")})
note("ADVANCE " + json.dumps({"status": status, "virtual_now": advanced.get("virtual_now"),
                              "version": advanced.get("version"), "persisted": advanced.get("persisted")},
                             ensure_ascii=False))

status, reread = call("GET", f"/api/v1/demo/simulation-clock/{journey_id}")
note("GET2 " + json.dumps({"status": status, "virtual_now": reread.get("virtual_now"),
                           "version": reread.get("version")}, ensure_ascii=False))

status, stale = call("POST", f"/api/v1/demo/simulation-clock/{journey_id}/advance",
                     {"minutes": 60, "expected_version": first.get("version")})
note("STALE " + json.dumps({"status": status, "detail": str(stale)[:120]}, ensure_ascii=False))

status, bad = call("POST", f"/api/v1/demo/simulation-clock/{journey_id}/advance", {"minutes": 0})
note("RANGE " + json.dumps({"status": status, "detail": str(bad)[:120]}, ensure_ascii=False))
print("\n".join(lines))
