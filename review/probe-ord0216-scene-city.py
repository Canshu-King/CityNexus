"""ORD-0216 ④ — measure first: which journey does the server's /demo/scene actually name,
and does its city match the city the wizard's demo-entry button prints?

The defect HJ-P1 saw with her own eyes: the button says 「使用封存的天津演示」 while the
sealed journey on stage is the Guangzhou one.  Nothing in this probe touches the commander's
ports (:4781/:4782/:8693), `_live.db`, or `demo/reset`.  It starts its own backend on a
private port against its own throwaway `_*.db`, creates journeys through the product API
exactly the way the e2e seed does, and prints what `/demo/scene` answers.

Run:  ../CityNexus/.venv/Scripts/python.exe review/probe-ord0216-scene-city.py
"""
from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
PORT = 8731
RUN_ID = datetime.now().strftime("%H%M%S")
DB = BACKEND / f"_ord0216scene{RUN_ID}.db"
BASE = f"http://127.0.0.1:{PORT}"


def call(path: str, body: dict | None = None, method: str | None = None):
    data = None if body is None else json.dumps(body).encode("utf-8")
    request = urllib.request.Request(
        f"{BASE}{path}",
        data=data,
        method=method or ("POST" if body is not None else "GET"),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=120) as response:
        return json.loads(response.read().decode("utf-8") or "{}")


def rows() -> list[dict]:
    connection = sqlite3.connect(DB)
    connection.row_factory = sqlite3.Row
    try:
        return [
            {
                "id": row["id"],
                "title": row["title"],
                "city_code": row["city_code"],
                "status": row["status"],
                "active_plan_version_id": row["active_plan_version_id"],
                "created_at": row["created_at"],
            }
            for row in connection.execute(
                "SELECT id, title, city_code, status, active_plan_version_id, created_at"
                " FROM journeys ORDER BY created_at"
            )
        ]
    finally:
        connection.close()


def main() -> int:
    env = {
        **os.environ,
        "CITYNEXUS_DATABASE_URL": f"sqlite:///{DB.as_posix()}",
        "CITYNEXUS_E2E_RUN_ID": f"ord0216scene{RUN_ID}",
        "CITYNEXUS_DEMO_MODE": "true",
        "CITYNEXUS_AI_ENABLED": "false",
    }
    log = open(ROOT / "review" / f"probe-ord0216-scene-{RUN_ID}.log", "w", encoding="utf-8")
    server = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(PORT)],
        cwd=BACKEND,
        env=env,
        stdout=log,
        stderr=subprocess.STDOUT,
    )
    try:
        for _ in range(60):
            try:
                if call("/api/v1/health").get("status"):
                    break
            except (urllib.error.URLError, OSError):
                time.sleep(1)
        else:
            print("backend did not come up", file=sys.stderr)
            return 2

        receipt: dict = {"db": str(DB), "port": PORT}

        traveler = call("/api/v1/travelers", {"display_name": "Ord0216 probe", "locale": "en-GB", "timezone": "Asia/Shanghai"})
        tianjin = call(
            "/api/v1/journeys",
            {
                "traveler_id": traveler["id"],
                "title": "Tianjin · stay-aware weekend",
                "city_code": "CN-TIANJIN",
                "timezone": "Asia/Shanghai",
                "start_at": "2026-10-09T18:00:00+08:00",
                "end_at": "2026-10-11T15:00:00+08:00",
                "budget": {"amount_minor": 120000, "currency": "CNY"},
            },
        )
        # Same two calls the e2e seed makes after creating the journey -- whether they bind an
        # active plan is exactly what decides which journey /demo/scene can name.
        call(f"/api/v1/journeys/{tianjin['id']}/stay-options/generate", {})
        options = call(f"/api/v1/journeys/{tianjin['id']}/stay-options").get("options") or []
        if options:
            chosen = next((o for o in options if o.get("status") == "RECOMMENDED"), options[0])
            call(f"/api/v1/journeys/{tianjin['id']}/stay-options/{chosen['id']}/select", {})
        receipt["stay_options_after_seed"] = len(options)

        scene_after_tianjin = call("/api/v1/demo/scene")
        receipt["scene_after_tianjin"] = {
            "demo_mode": scene_after_tianjin.get("demo_mode"),
            "journey_id": scene_after_tianjin.get("journey_id"),
            "journey_status": scene_after_tianjin.get("journey_status"),
        }

        # A second, DIFFERENT sealed city, created through the same product API.
        guangzhou = call(
            "/api/v1/journeys",
            {
                "traveler_id": traveler["id"],
                "title": "广州 · 周末两晚",
                "city_code": "CN-GUANGZHOU",
                "timezone": "Asia/Shanghai",
                "start_at": "2026-10-16T18:00:00+08:00",
                "end_at": "2026-10-18T15:00:00+08:00",
                "budget": {"amount_minor": 120000, "currency": "CNY"},
            },
        )
        receipt["guangzhou_post_status"] = guangzhou.get("id") and "201/created"
        scene_after_guangzhou = call("/api/v1/demo/scene")
        receipt["scene_after_guangzhou"] = {
            "demo_mode": scene_after_guangzhou.get("demo_mode"),
            "journey_id": scene_after_guangzhou.get("journey_id"),
            "journey_status": scene_after_guangzhou.get("journey_status"),
        }
        by_id = {row["id"]: row for row in rows()}
        receipt["journeys_in_db"] = list(by_id.values())
        for key, scene in (("after_tianjin", scene_after_tianjin), ("after_guangzhou", scene_after_guangzhou)):
            named = by_id.get(scene.get("journey_id") or "")
            receipt[f"scene_city_{key}"] = named["city_code"] if named else None

        # Which city would a *fresh* stage (no second journey, no active plan) name?
        receipt["reader"] = "probe-ord0216-scene-city.py @e345b9d6"
        print(json.dumps(receipt, ensure_ascii=False, indent=2))
        out = ROOT / "review" / "evidence" / "ui-overnight"
        out.mkdir(parents=True, exist_ok=True)
        (out / "ord0216-scene-city.json").write_text(
            json.dumps({"generatedBy": "e345b9d6", **receipt}, ensure_ascii=False, indent=2) + "\n",
            "utf-8",
        )
        return 0
    finally:
        server.terminate()
        try:
            server.wait(timeout=20)
        except subprocess.TimeoutExpired:
            server.kill()
        log.close()


if __name__ == "__main__":
    raise SystemExit(main())
