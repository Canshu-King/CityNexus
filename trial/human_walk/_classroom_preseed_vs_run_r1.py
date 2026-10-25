"""Measure what a pre-seeded classroom proposal does to a SimulationRun guardian.

Copies the classroom database to a scratch file, starts the exported Codex backend on the
spare port, mints a pairing ticket, starts a run, injects one closure scene, asks the guardian
to look at it (no model wired), and reads the proposal table before and after.  The classroom
stack itself is never touched; no credential is printed.
"""
from __future__ import annotations

import json
import os
import sqlite3
import time
import urllib.error
import urllib.request
import uuid

from _entry_banner_stack_r1 import (
    BACKEND, WORK, start_backend, stop_isolated_backend, wait_healthy,
)

SOURCE_DB = r"D:/moodle/_cmdr_v3_live_1022/citynexus_v3_demo_1025.db"
TARGET_DB = WORK + "/probe9_1025.db"
JOURNEY = "2e9cd67d-10ca-4ecd-920b-76c81a350c71"
ACTIVE_PLAN = "e74a5edb-3f6d-40c3-910c-52e449619d40"
API = "http://127.0.0.1:60400"
OUT = r"D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261022_v3_human_chrome/classroom-preseed-vs-run-1.txt"
OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))
SIM_DDL = """
CREATE TABLE IF NOT EXISTS simulation_runs (
    id TEXT PRIMARY KEY,
    journey_id TEXT NOT NULL UNIQUE REFERENCES journeys(id),
    actor_id TEXT NOT NULL REFERENCES travelers(id),
    city_code TEXT NOT NULL,
    seed INTEGER NOT NULL,
    timezone TEXT NOT NULL,
    virtual_now TEXT NOT NULL,
    sequence INTEGER NOT NULL DEFAULT 0 CHECK(sequence >= 0),
    status TEXT NOT NULL,
    state_json TEXT NOT NULL DEFAULT '{}',
    history_json TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS simulation_commands (
    id TEXT PRIMARY KEY,
    journey_id TEXT NOT NULL REFERENCES journeys(id),
    run_id TEXT NOT NULL REFERENCES simulation_runs(id),
    actor_id TEXT NOT NULL REFERENCES travelers(id),
    idempotency_key TEXT NOT NULL,
    request_sha256 TEXT NOT NULL,
    result_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE(journey_id, actor_id, idempotency_key)
);
"""

lines: list[str] = []


def note(value) -> None:
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
    lines.append(text)
    with open(OUT, "w", encoding="utf-8", newline="\n") as handle:
        handle.write("\n".join(lines) + "\n")


def copy_db() -> None:
    for suffix in ("", "-wal", "-shm"):
        if os.path.exists(TARGET_DB + suffix):
            os.remove(TARGET_DB + suffix)
    source = sqlite3.connect("file:" + SOURCE_DB + "?mode=ro", uri=True)
    target = sqlite3.connect(TARGET_DB)
    try:
        source.backup(target)
        target.executescript(SIM_DDL)
        target.commit()
    finally:
        target.close()
        source.close()


def proposals() -> list[dict]:
    db = sqlite3.connect("file:" + TARGET_DB + "?mode=ro", uri=True)
    try:
        rows = [dict(zip(("id", "status", "source", "created_at"), r)) for r in db.execute(
            "select id,status,coalesce(source_agent_run_id,''),created_at from replan_proposals order by created_at"
        )]
    finally:
        db.close()
    return rows


def call(method: str, path: str, body: dict | None, token: str | None = None,
         key: str | None = None, presenter: str | None = None,
         timeout: int = 120) -> tuple[int, dict]:
    data = None if body is None else json.dumps(body).encode()
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = "Bearer " + token
    if key:
        headers["Idempotency-Key"] = key
    if presenter:
        headers["X-CityNexus-Presenter-Key"] = presenter
    request = urllib.request.Request(API + path, data=data, method=method, headers=headers)
    try:
        with OPENER.open(request, timeout=timeout) as answer:
            return answer.status, json.loads(answer.read().decode() or "{}")
    except urllib.error.HTTPError as error:
        try:
            return error.code, json.loads(error.read().decode() or "{}")
        except ValueError:
            return error.code, {}
    except (TimeoutError, urllib.error.URLError) as error:
        return 0, {"timeout": True, "detail": str(error)[:120]}


def main() -> int:
    stop_isolated_backend()
    time.sleep(2)
    copy_db()
    presenter_key = uuid.uuid4().hex + uuid.uuid4().hex[:12]
    process = start_backend(TARGET_DB, presenter_key)
    try:
        if not wait_healthy():
            note({"PRESEED_VS_RUN": False, "reason": "backend not healthy"})
            return 1
        status, issued = call("POST", "/api/v1/demo/pairing", {"journey_id": JOURNEY}, presenter=presenter_key)
        note({"pairing": status})
        if status != 201:
            return 1
        status, session = call("POST", "/api/v1/demo/pairing/redeem", {"ticket": issued["ticket"]})
        note({"redeem": status})
        if status != 200:
            return 1
        token = session["access_token"]

        before = proposals()
        note({"proposals_before": before})
        events_status, events = call("GET", f"/api/v1/journeys/{JOURNEY}/events", None, token=token)
        note({"events_before": events_status, "events": events})

        status, run = call("POST", f"/api/v1/journeys/{JOURNEY}/simulation/runs",
                           {"seed": 7}, token=token, key=str(uuid.uuid4()))
        note({"start_run": status, "run": {k: run.get(k) for k in ("id", "status", "sequence")} if status < 400 else run})
        if status not in (200, 201):
            return 1
        run_id, sequence = run["run_id"], run.get("sequence", 0)

        activity_id = (events[0] if isinstance(events, list) and events else {}).get("affected_activity_id")
        if not activity_id:
            note({"PRESEED_VS_RUN": False, "reason": "the classroom event carries no affected activity"})
            return 1

        status, scene = call("POST", f"/api/v1/journeys/{JOURNEY}/simulation/runs/{run_id}/scenes",
                             {"expected_sequence": sequence, "scene_id": "classroom-closure",
                              "event_type": "CLOSURE", "activity_id": activity_id},
                             token=token, key=str(uuid.uuid4()))
        note({"scene": status, "run": {k: scene.get(k) for k in ("status", "sequence")} if status < 400 else scene})
        if status not in (200, 201):
            return 1
        sequence = scene.get("sequence", sequence)

        started = time.time()
        status, guardian = call("POST", f"/api/v1/journeys/{JOURNEY}/simulation/runs/{run_id}/guardian",
                                {"expected_sequence": sequence, "model_consent": True},
                                token=token, key=str(uuid.uuid4()), timeout=90)
        elapsed = round(time.time() - started, 1)
        note({"guardian": status, "elapsed_s": elapsed,
              "run": {k: guardian.get(k) for k in ("status", "sequence")} if status < 400 else guardian})

        after = proposals()
        note({"proposals_after": after})
        note({"proposal_count_before": len(before), "proposal_count_after": len(after)})
        note({"PRESEED_VS_RUN": True, "backend_pid": process.pid})
        return 0
    finally:
        # Keep the spare backend running for follow-up reads; it is loopback-only.
        pass


if __name__ == "__main__":
    raise SystemExit(main())
