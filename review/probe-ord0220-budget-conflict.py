"""ORD-0220 ④ — one black-box probe: does the server refuse "lodging 900 > total 450"?

The wizard sends both figures in the same currency on one POST (`V8Experience.tsx:898-905`), and HJ-P1
has now watched the pair pass silently three times.  This probe asks the service, not the code:

  1. read the service's own route list (`/openapi.json`) and print every `journeys` path with its
     methods -- so "there is no update entry point" is a reading, never a guess;
  2. POST a journey whose `budget` is 450 CNY and whose `stay_budget` is 900 CNY, exactly the shape
     the traveller's device sends;
  3. read the created journey back through the endpoint the Today hub actually uses, and print both
     numbers as stored.

Nothing here edits the backend, and nothing touches the commander's ports or `_live.db`: private
port, private throwaway database, `demo/reset` never called, no provider egress.

Run:  D:/moodle/CityNexus/.venv/Scripts/python.exe review/probe-ord0220-budget-conflict.py
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
PORT = 8732
RUN_ID = datetime.now().strftime("%H%M%S")
DB = BACKEND / f"_ord0220conflict{RUN_ID}.db"
BASE = f"http://127.0.0.1:{PORT}"


def call(path: str, body: dict | None = None, method: str | None = None):
    data = None if body is None else json.dumps(body).encode("utf-8")
    request = urllib.request.Request(
        f"{BASE}{path}",
        data=data,
        method=method or ("POST" if body is not None else "GET"),
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            return response.status, json.loads(response.read().decode("utf-8") or "{}")
    except urllib.error.HTTPError as error:
        raw = error.read().decode("utf-8", errors="replace")
        try:
            return error.code, json.loads(raw)
        except ValueError:
            return error.code, {"raw": raw[:400]}


def main() -> int:
    env = {
        **os.environ,
        "CITYNEXUS_DATABASE_URL": f"sqlite:///{DB.as_posix()}",
        "CITYNEXUS_E2E_RUN_ID": f"ord0220conflict{RUN_ID}",
        "CITYNEXUS_DEMO_MODE": "true",
        "CITYNEXUS_AI_ENABLED": "false",
    }
    log = open(ROOT / "review" / f"probe-ord0220-{RUN_ID}.log", "w", encoding="utf-8")
    server = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(PORT)],
        cwd=BACKEND,
        env=env,
        stdout=log,
        stderr=subprocess.STDOUT,
    )
    receipt: dict = {"db": str(DB), "port": PORT}
    try:
        for _ in range(60):
            try:
                if call("/api/v1/health")[1].get("status"):
                    break
            except (urllib.error.URLError, OSError):
                time.sleep(1)
        else:
            print("backend did not come up", file=sys.stderr)
            return 2

        # 1. the service's own surface: which journeys paths exist, and with which methods.
        status, spec = call("/openapi.json")
        paths = []
        if status == 200:
            for path, operations in sorted((spec.get("paths") or {}).items()):
                if "journey" in path:
                    paths.append({"path": path, "methods": sorted(k.upper() for k in operations)})
        receipt["openapi_status"] = status
        receipt["journey_paths"] = paths
        receipt["journey_write_methods"] = sorted(
            {m for entry in paths for m in entry["methods"] if m in {"POST", "PATCH", "PUT"}}
        )

        # 2. the contradiction, in the shape the wizard sends it.
        _, traveler = call(
            "/api/v1/travelers",
            {"display_name": "Ord0220 probe", "locale": "zh-CN", "timezone": "Asia/Shanghai"},
        )
        payload = {
            "traveler_id": traveler["id"],
            "title": "天津 · 冲突探针",
            "city_code": "CN-TIANJIN",
            "timezone": "Asia/Shanghai",
            "start_at": "2026-10-09T18:00:00+08:00",
            "end_at": "2026-10-11T15:00:00+08:00",
            "budget": {"amount_minor": 45000, "currency": "CNY"},
            "stay_budget": {"amount_minor": 90000, "currency": "CNY"},
            "party_size": 1,
            "occupancy": {"adults": 1, "rooms": 1},
            "arrival_anchor": {"at": "2026-10-09T18:00:00+08:00", "location": "天津站"},
            "departure_anchor": {"at": "2026-10-11T15:00:00+08:00", "location": "北京南站"},
        }
        created_status, created = call("/api/v1/journeys", payload)
        receipt["create"] = {
            "request": {"budget": payload["budget"], "stay_budget": payload["stay_budget"]},
            "status": created_status,
            "body_keys": sorted(created.keys()),
            "reason_code": created.get("reason_code") or created.get("code") or created.get("error"),
            "message": created.get("message") or created.get("detail"),
        }

        # 3. read it back through the endpoint the hub uses.
        journey_id = created.get("id")
        if journey_id:
            read_status, experience = call(f"/api/v1/journeys/{journey_id}/experience")
            trip = experience.get("trip") or {}
            receipt["readback"] = {
                "endpoint": f"/api/v1/journeys/{journey_id}/experience",
                "status": read_status,
                "budget": trip.get("budget_reference") or trip.get("budget"),
                "stay_budget": trip.get("stay_budget"),
                "journey_status": (experience.get("journey") or {}).get("status"),
            }
            # 4. the other entry the order names: the update route the route list showed as PATCH.
            patch_status, patched = call(
                f"/api/v1/journeys/{journey_id}",
                {"budget": {"amount_minor": 45000, "currency": "CNY"}, "stay_budget": {"amount_minor": 90000, "currency": "CNY"}},
                method="PATCH",
            )
            _, after = call(f"/api/v1/journeys/{journey_id}/experience")
            after_trip = after.get("trip") or {}
            receipt["update_entry"] = {
                "endpoint": f"PATCH /api/v1/journeys/{journey_id}",
                "status": patch_status,
                "reason_code": patched.get("reason_code") or patched.get("code") or patched.get("error"),
                "message": patched.get("message") or patched.get("detail"),
                "budget_after": after_trip.get("budget_reference") or after_trip.get("budget"),
                "stay_budget_after": after_trip.get("stay_budget"),
            }
        print(json.dumps(receipt, ensure_ascii=False, indent=2))
        out = ROOT / "review" / "evidence" / "ui-overnight"
        out.mkdir(parents=True, exist_ok=True)
        (out / "ord0220-budget-conflict-probe.json").write_text(
            json.dumps({"generatedBy": "e345b9d6", **receipt}, ensure_ascii=False, indent=2) + "\n", "utf-8"
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
