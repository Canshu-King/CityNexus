"""ORD-0079 must 1-4: which mobility evidence does the replan path actually read?

Run:  python review/probe-ord79-mobility-evidence.py
Writes: D:/moodle/_qoder_ord30_evidence_20260920/ord79/mobility-evidence.json

The order was dispatched because two server answers disagreed:
`GET /route-evidence` says `fallback_reason=NO_FROZEN_MOBILITY_SNAPSHOT` while the very same
plan row carries a non-empty `mobility_evidence_json`.  Reading the code names three separate
supplies of "mobility evidence" (`plan.mobility_evidence_json`, the proposal's
`diff_json.verified_evidence.mobility.snapshot`, and the `MobilitySnapshot` rows), so the way
to settle it is to ask a running server, once, in the order the demo stage actually walks:

    reset -> prepare (generate+select) -> start -> scene -> route-evidence -> event -> replan

Every number below is read from that one process.  Nothing here fabricates evidence: the probe
only reads what the product's own endpoints and the plan row contain, and the /replans attempt
is retried a bounded number of times so the failure code *and* the retry count are both
reportable (must 3a).

Isolation, as usual for my probes: own throwaway database file, own ephemeral port, AI off,
provider credentials popped inside this process before uvicorn starts, and the running preview
instance (`:4781/:4782/:8781`, `_preview.db`) is never contacted.
"""

from __future__ import annotations

import json
import os
import socket
import sqlite3
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx

BACKEND = Path(r"D:\moodle\_qoder_integration_20260919\backend")
TREE = Path(r"D:\moodle\_qoder_integration_20260919")
PYTHON = Path(r"D:\moodle\CityNexus\.venv\Scripts\python.exe")
OUT_DIR = Path(r"D:\moodle\_qoder_ord30_evidence_20260920\ord79")
RUN_ID = os.environ.get("PROBE_RUN_ID", "ord79-ev")
DB_FILE = BACKEND / f"_{RUN_ID}.db"
TZ = timezone(timedelta(hours=8))
REPLAN_ATTEMPTS = 3


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def git(args: list[str]) -> str:
    try:
        return subprocess.run(
            ["git", *args], cwd=TREE, capture_output=True, text=True, timeout=20
        ).stdout.strip()
    except Exception as exc:  # pragma: no cover - diagnostics only
        return f"<git unavailable: {exc}>"


def read_plan_row(plan_id: str) -> dict[str, object]:
    """Read the plan the product itself wrote, straight from the throwaway database."""

    uri = f"file:{DB_FILE.as_posix()}?mode=ro"
    connection = sqlite3.connect(uri, uri=True, timeout=10)
    connection.row_factory = sqlite3.Row
    try:
        plan = connection.execute(
            "SELECT id, status, mobility_snapshot_id, mobility_evidence_json"
            " FROM plan_versions WHERE id = ?",
            (plan_id,),
        ).fetchone()
        if plan is None:
            return {"error": "plan row missing"}
        evidence = json.loads(plan["mobility_evidence_json"] or "{}")
        facts = evidence.get("facts") or []
        selected = evidence.get("selected_facts") or []

        def pairs(items: list[object]) -> list[dict[str, object]]:
            out = []
            for item in items:
                if isinstance(item, dict):
                    out.append(
                        {
                            "origin_key": item.get("origin_key"),
                            "destination_key": item.get("destination_key"),
                            "mode": item.get("mode"),
                            "minutes": item.get("minutes", item.get("duration_min")),
                            "fact_quality": item.get("fact_quality"),
                            "route_provenance": item.get("route_provenance"),
                            "has_geometry": bool(item.get("route_geometry")),
                        }
                    )
            return out

        activities = connection.execute(
            "SELECT id, sequence_no, place_id, city_service_id, title, start_at, status,"
            " travel_from_prev_min, metadata_json FROM activities WHERE plan_version_id = ?"
            " ORDER BY sequence_no",
            (plan_id,),
        ).fetchall()
        rows = []
        for activity in activities:
            try:
                metadata = json.loads(activity["metadata_json"] or "{}")
            except json.JSONDecodeError:
                metadata = {}
            rows.append(
                {
                    "id": activity["id"],
                    "sequence_no": activity["sequence_no"],
                    "title": activity["title"],
                    "place_id": activity["place_id"],
                    "city_service_id": activity["city_service_id"],
                    "semantic_key": metadata.get("semantic_key"),
                    "start_at": activity["start_at"],
                    "status": activity["status"],
                    "travel_from_prev_min": activity["travel_from_prev_min"],
                }
            )
        return {
            "id": plan["id"],
            "status": plan["status"],
            "column mobility_snapshot_id": plan["mobility_snapshot_id"],
            "evidence top-level keys": sorted(evidence),
            "evidence snapshot_id": evidence.get("snapshot_id"),
            "evidence source_provider": evidence.get("source_provider")
            or evidence.get("provider"),
            "evidence captured_at": evidence.get("captured_at"),
            "evidence expires_at": evidence.get("expires_at"),
            "evidence integrity_hash present": bool(evidence.get("integrity_hash")),
            "evidence facts count": len(facts),
            "evidence selected_facts count": len(selected),
            "evidence facts": pairs(facts),
            "evidence selected_facts": pairs(selected),
            "provider_evidence present": isinstance(evidence.get("provider_evidence"), dict),
            "activities": rows,
        }
    finally:
        connection.close()


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for suffix in ("", "-wal", "-shm"):
        candidate = Path(str(DB_FILE) + suffix)
        if candidate.exists():
            candidate.unlink()

    env = dict(os.environ)
    for credential in (
        "DEEPSEEK_API_KEY",
        "CITYNEXUS_AI_API_KEY",
        "CITYNEXUS_HERMES_API_KEY",
        "CITYNEXUS_HERMES_API_SERVER_KEY",
    ):
        env.pop(credential, None)
    env.update(
        {
            "CITYNEXUS_DATABASE_URL": f"sqlite:///./{DB_FILE.name}",
            "CITYNEXUS_DEMO_MODE": "true",
            "CITYNEXUS_AI_ENABLED": "false",
            "CITYNEXUS_GUARDIAN_AUTORUN": "false",
            "PYTHONIOENCODING": "utf-8",
        }
    )
    port = free_port()
    log_path = OUT_DIR.joinpath("uvicorn.log")
    with log_path.open("wb") as handle:
        server = subprocess.Popen(
            [str(PYTHON), "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1",
             "--port", str(port)],
            cwd=BACKEND,
            env=env,
            stdout=handle,
            stderr=handle,
        )
    base = f"http://127.0.0.1:{port}"
    report: dict[str, object] = {
        "measured_at": datetime.now(timezone.utc).isoformat(),
        "tree": str(TREE),
        "head": git(["rev-parse", "HEAD"]),
        "interpreter": str(PYTHON),
        "credentials": {
            "DEEPSEEK_API_KEY in server env": bool(env.get("DEEPSEEK_API_KEY")),
            "CITYNEXUS_AI_ENABLED": env["CITYNEXUS_AI_ENABLED"],
        },
        "server": {"pid": server.pid, "port": port, "database": DB_FILE.name},
        "live_valhalla_url": env.get("CITYNEXUS_LIVE_VALHALLA_URL"),
        "steps": [],
    }

    def step(name: str, method: str, path: str, **kwargs: object) -> httpx.Response:
        began = time.perf_counter()
        response = httpx.request(method, f"{base}{path}", timeout=180.0, **kwargs)
        elapsed = (time.perf_counter() - began) * 1000.0
        try:
            body = response.json()
        except Exception:
            body = {"_raw": response.text[:400]}
        report["steps"].append(
            {
                "step": name,
                "method": method,
                "path": path,
                "status_code": response.status_code,
                "ms": round(elapsed, 1),
                "body": body if not isinstance(body, list) else {"_list_len": len(body)},
            }
        )
        return response

    try:
        for _ in range(120):
            try:
                if httpx.get(f"{base}/health", timeout=2.0).status_code < 500:
                    break
            except Exception:
                pass
            time.sleep(0.5)
        else:
            report["fatal"] = "server never answered /health"
            return 2

        response = step("reset", "POST", "/api/v1/demo/reset")
        response = step("prepare", "POST", "/api/v1/demo/prepare-scenario")
        prepared = response.json()
        journey_id = prepared.get("journey_id")
        response = step("start", "POST", "/api/v1/demo/start-scenario")
        scene = step("scene", "GET", "/api/v1/demo/scene").json()
        plan_id = scene.get("plan_version_id")
        cursor_id = scene.get("current_activity_id")

        route_before = step(
            "route-evidence-before-replan", "GET", f"/api/v1/journeys/{journey_id}/route-evidence"
        ).json()
        report["route_evidence_before"] = {
            "snapshot_id": route_before.get("snapshot_id"),
            "provider": route_before.get("provider"),
            "frozen": route_before.get("frozen"),
            "fallback": route_before.get("fallback"),
            "old_route properties": (route_before.get("old_route") or {}).get("properties"),
        }

        # The plan row as the product wrote it: this is the half the order asked about.
        if plan_id:
            report["plan_row"] = read_plan_row(str(plan_id))

        # An event grounded on the cursor, both places the server is documented to read.
        event_body = {
            "event_type": "TRAFFIC_DELAY",
            "severity": "MAJOR",
            "provenance": "SIMULATED",
            "affected_activity_id": cursor_id,
            "payload": {"affected_activity_id": cursor_id, "delay_minutes": 25},
        }
        event_response = step("event", "POST", f"/api/v1/journeys/{journey_id}/events", json=event_body)
        event_id = None
        if event_response.status_code in (200, 201):
            event_id = event_response.json().get("id")
            report["twin_after_event"] = step(
                "twin-after-event", "GET", f"/api/v1/journeys/{journey_id}/twin"
            ).json().get("state", {}).get("execution", {})

        attempts: list[dict[str, object]] = []
        for index in range(REPLAN_ATTEMPTS):
            response = step(
                f"replan attempt {index + 1}",
                "POST",
                f"/api/v1/journeys/{journey_id}/replans",
                json={"trigger_event_id": event_id, "candidate_count": 2},
                headers={"Idempotency-Key": f"ord79-probe-{index + 1}"},
            )
            body = response.json()
            attempts.append(
                {
                    "attempt": index + 1,
                    "status_code": response.status_code,
                    "detail": body.get("detail") if "detail" in body else None,
                    "error": body.get("error"),
                    "has proposal id": "id" in body,
                }
            )
            if response.status_code in (200, 201):
                break
            time.sleep(1.0 + index)
        report["replan_attempts"] = attempts
        report["replan retry count"] = len(attempts)

        route_after = step(
            "route-evidence-after-replan", "GET", f"/api/v1/journeys/{journey_id}/route-evidence"
        ).json()
        report["route_evidence_after"] = {
            "snapshot_id": route_after.get("snapshot_id"),
            "provider": route_after.get("provider"),
            "frozen": route_after.get("frozen"),
            "old_route properties": (route_after.get("old_route") or {}).get("properties"),
        }
        report["scene_final"] = step("scene-final", "GET", "/api/v1/demo/scene").json()

        # Attribution: the pairs the replan path will ask for, recomputed the way
        # `main.py::_activity_location` + `_canonical_key` do it, diffed against the
        # pairs the sealed evidence actually carries.
        plan_row = report.get("plan_row") or {}
        activities = plan_row.get("activities") or []
        semantic_by_identity: dict[str, str] = {}
        for activity in activities:
            semantic = str(activity.get("semantic_key") or "").strip()
            if not semantic:
                continue
            for identity in (activity.get("place_id"), activity.get("city_service_id")):
                if identity:
                    semantic_by_identity.setdefault(str(identity), semantic)

        def canonical(value: object) -> str | None:
            if not value:
                return None
            text = str(value)
            return semantic_by_identity.get(text, text)

        needed: list[list[str]] = []
        for previous, current in zip(activities, activities[1:]):
            left = canonical(
                (previous.get("semantic_key") or previous.get("place_id") or previous.get("city_service_id"))
            )
            right = canonical(
                (current.get("semantic_key") or current.get("place_id") or current.get("city_service_id"))
            )
            if left and right and left != right:
                needed.append([str(left), str(right)])
        carried = {
            (str(item.get("origin_key")), str(item.get("destination_key")))
            for item in (plan_row.get("evidence facts") or []) + (plan_row.get("evidence selected_facts") or [])
        }
        hard_ok = {
            (str(item.get("origin_key")), str(item.get("destination_key")))
            for item in (plan_row.get("evidence facts") or []) + (plan_row.get("evidence selected_facts") or [])
            if item.get("fact_quality") in {"EXPLICIT_FROZEN_FIXTURE", "LIVE_PROVIDER_CAPTURE"}
        }
        report["attribution"] = {
            "legs the active plan walks": len(needed),
            "legs with any sealed fact": sum(1 for pair in needed if tuple(pair) in carried),
            "legs with a HARD-eligible fact": sum(1 for pair in needed if tuple(pair) in hard_ok),
            "missing pairs": [pair for pair in needed if tuple(pair) not in carried],
            "present but not hard-eligible": [
                pair for pair in needed if tuple(pair) in carried and tuple(pair) not in hard_ok
            ],
            "fact qualities seen": sorted(
                {
                    str(item.get("fact_quality"))
                    for item in (plan_row.get("evidence facts") or [])
                }
            ),
        }
        report["scene_evidence_state"] = scene.get("evidence_state")
        report["cursor_id"] = cursor_id
        report["journey_id"] = journey_id
        report["plan_version_id"] = plan_id
        return 0
    finally:
        OUT_DIR.joinpath("mobility-evidence.json").write_text(
            json.dumps(report, indent=2, ensure_ascii=False, default=str),
            encoding="utf-8",
            newline="\n",
        )
        server.terminate()
        try:
            server.wait(timeout=30)
        except Exception:
            server.kill()
        print("->", OUT_DIR / "mobility-evidence.json")


if __name__ == "__main__":
    raise SystemExit(main())
