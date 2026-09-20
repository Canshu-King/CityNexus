"""ORD-0057 acceptance-latency measurement on a real server, with real provider work running.

Run:  python review/probe-ord57-acceptance-latency.py
Writes: D:/moodle/_qoder_ord30_evidence_20260920/ord57/acceptance-latency.json

Why a separate process instead of the test client: the gate the arbitration set is about
what a *request thread* costs ("受理 p95 ≤ 1s"), so it must be measured through uvicorn's
HTTP stack, with the accommodation chain actually running in the background - and against a
chain that is genuinely slow rather than a fake.  This machine has no campus-network egress,
so each cold-city attempt spends its full per-host timeout, which is exactly the shape of a
115s cold path.

Nothing here touches the running preview instance (`:4781/:4782/:8781`, `_preview.db`): own
ports, own throwaway database file, AI disabled, keys empty, no E2E run id.  The operations
are abandoned at the end, which is also the honest way to leave no chain behind.
"""

from __future__ import annotations

import json
import os
import socket
import statistics
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx

BACKEND = Path(r"D:\moodle\_qoder_integration_20260919\backend")
PYTHON = Path(r"D:\moodle\CityNexus\.venv\Scripts\python.exe")
OUT_DIR = Path(r"D:\moodle\_qoder_ord30_evidence_20260920\ord57")
RUN_ID = os.environ.get("PROBE_RUN_ID", "ord57-lat")
DB_FILE = BACKEND / f"_{RUN_ID}.db"
JOBS = 8
TZ = timezone(timedelta(hours=8))


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def percentile(values: list[float], pct: float) -> float:
    ordered = sorted(values)
    if not ordered:
        return 0.0
    index = min(len(ordered) - 1, max(0, int(round((pct / 100.0) * (len(ordered) - 1)))))
    return ordered[index]


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for suffix in ("", "-wal", "-shm"):
        candidate = Path(str(DB_FILE) + suffix)
        if candidate.exists():
            candidate.unlink()
    port = free_port()
    env = dict(os.environ)
    env.update(
        {
            "CITYNEXUS_DATABASE_URL": f"sqlite:///./{DB_FILE.name}",
            "CITYNEXUS_AI_ENABLED": "false",
            "DEEPSEEK_API_KEY": "",
            "CITYNEXUS_AI_API_KEY": "",
            "CITYNEXUS_PROVIDER_TIMING": "",
            "PYTHONIOENCODING": "utf-8",
        }
    )
    server_log = OUT_DIR.joinpath("uvicorn.log")
    with server_log.open("wb") as log_handle:
        server = subprocess.Popen(
            [str(PYTHON), "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(port)],
            cwd=BACKEND,
            env=env,
            stdout=log_handle,
            stderr=log_handle,
        )
    base = f"http://127.0.0.1:{port}"
    try:
        for _ in range(120):
            try:
                if httpx.get(f"{base}/health", timeout=2.0).status_code < 500:
                    break
            except Exception:
                pass
            time.sleep(0.5)
        else:
            print("server never answered /health", file=sys.stderr)
            return 2

        traveler = httpx.post(f"{base}/api/v1/demo/reset", timeout=60.0).json()["traveler_id"]
        start = datetime(2026, 11, 3, 9, 0, tzinfo=TZ)
        journey = httpx.post(
            f"{base}/api/v1/journeys",
            json={
                "traveler_id": traveler,
                "title": "acceptance latency",
                "city_code": "CN-XIAMEN",
                "timezone": "Asia/Shanghai",
                "start_at": start.isoformat(),
                "end_at": (start + timedelta(days=2, hours=8)).isoformat(),
                "budget": {"amount_minor": 90000, "currency": "CNY"},
                "planning_mode": "balanced",
            },
            timeout=60.0,
        ).json()
        journey_id = journey["id"]

        samples: list[float] = []
        operations: list[str] = []
        for index in range(JOBS):
            began = time.perf_counter()
            response = httpx.post(
                f"{base}/api/v1/journeys/{journey_id}/stay-generations",
                json={"candidate_count": 5 + index},  # a distinct question each time
                timeout=120.0,
            )
            samples.append((time.perf_counter() - began) * 1000.0)
            assert response.status_code == 202, response.text[:300]
            operations.append(response.json()["operation_id"])

        # Still open while these reads happen - which is the whole claim: the request is not
        # the thing carrying the provider chain any more.
        states = []
        for operation_id in operations:
            body = httpx.get(
                f"{base}/api/v1/journeys/{journey_id}/stay-generations/{operation_id}", timeout=30.0
            ).json()
            states.append((body["status"], body["phase"], body["elapsed_ms"]))
        still_running = sum(1 for status, _phase, _ms in states if status in {"QUEUED", "RUNNING"})

        # Leave nothing behind: abandon what is in flight, then stop the server.
        abandoned = []
        for operation_id in operations:
            body = httpx.post(
                f"{base}/api/v1/journeys/{journey_id}/stay-generations/{operation_id}/abandon",
                timeout=30.0,
            )
            abandoned.append(body.json().get("status"))

        report = {
            "measured_at": datetime.now(timezone.utc).isoformat(),
            "run_id": RUN_ID,
            "server": {"pid": server.pid, "port": port, "database": DB_FILE.name},
            "chain": "cold CN-XIAMEN through Photon -> 3 Overpass mirrors -> Nominatim",
            "submits": JOBS,
            "acceptance_ms": {
                "p50": round(percentile(samples, 50), 1),
                "p95": round(percentile(samples, 95), 1),
                "max": round(max(samples), 1),
                "all": [round(item, 1) for item in samples],
            },
            "over_1000ms": sum(1 for item in samples if item > 1000.0),
            "operations_still_in_flight_at_read": still_running,
            "states_at_read": states,
            "abandon_responses": abandoned,
            "caveats": [
                "Acceptance latency is the HTTP round trip against a local uvicorn on "
                "127.0.0.1; it excludes the phone's network path and the tunnel.",
                "This machine has no egress on the measured link, so each cold chain spends "
                "its full per-host timeout - the chain is slow, which is the condition the "
                "contract was designed for, not an idle one.",
                "The public preview instance was not used or modified: own port, own database.",
            ],
        }
        OUT_DIR.joinpath("acceptance-latency.json").write_text(
            json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8", newline="\n"
        )
        print(json.dumps(report["acceptance_ms"], ensure_ascii=False))
        print("in flight while read:", still_running, "/", JOBS, "abandon answers:", set(abandoned))
        print("->", OUT_DIR / "acceptance-latency.json")
        return 0
    finally:
        server.terminate()
        try:
            server.wait(timeout=30)
        except Exception:
            server.kill()


if __name__ == "__main__":
    raise SystemExit(main())
