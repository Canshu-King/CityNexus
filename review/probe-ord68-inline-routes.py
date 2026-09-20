"""ORD-0068 measurement: do the two remaining inline routes really make a traveller wait?

`POST …/stay-options/{option_id}/weather` and `POST …/stay-autopilot/recover` still call
`generate_stay_options` in the request thread.  Whether that is a defect or a non-issue is
measured here, not reasoned about: the question is how long a traveller waits and what the
server is doing while they wait.

Three instruments, all read from outside the process so nothing is inferred:

* HTTP round trip in ms, per condition (cold city / frozen evidence already captured);
* whether provider work was actually contacted - read from `X-CityNexus-Phase-Ms` with
  `CITYNEXUS_PROVIDER_TIMING=1`, which lists `provider.photon` / `provider.overpass` spans
  only when a network call really ran;
* whether SQLite's single writer was held during the call: a separate connection tries
  `BEGIN IMMEDIATE` with `busy_timeout = 0` on a sample interval, which either works or does
  not, with no waiting and no guessing.

Isolation per the standing rules: own free port, own throwaway database file, AI disabled,
keys empty, no E2E run id, and the running preview instance is neither read nor touched.

Run:  python review/probe-ord68-inline-routes.py
Out:  D:/moodle/_qoder_ord30_evidence_20260920/ord68/inline-routes.json
"""

from __future__ import annotations

import json
import os
import socket
import sqlite3
import subprocess
import sys
import threading
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx

LF = chr(10)

BACKEND = Path(r"D:\moodle\_qoder_integration_20260919\backend")
PYTHON = Path(r"D:\moodle\CityNexus\.venv\Scripts\python.exe")
OUT_DIR = Path(r"D:\moodle\_qoder_ord30_evidence_20260920\ord68")
RUN_ID = os.environ.get("PROBE_RUN_ID", "ord68-inline")
DB_FILE = BACKEND / f"_{RUN_ID}.db"
TZ = timezone(timedelta(hours=8))
ROUTES = (
    ("weather", "POST", "/api/v1/journeys/{jid}/stay-options/{oid}/weather"),
    ("autopilot_recover", "POST", "/api/v1/journeys/{jid}/stay-options/{oid}/autopilot/recover"),
)


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


class LockSampler:
    """Asks, on its own connection, whether the database accepts a writer right now."""

    def __init__(self, path: Path, interval: float = 0.25) -> None:
        self.path = path
        self.interval = interval
        self.samples: list[dict[str, object]] = []
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)

    def _probe(self) -> bool:
        try:
            connection = sqlite3.connect(str(self.path), timeout=0.0)
        except sqlite3.Error:
            return False
        try:
            connection.execute("PRAGMA busy_timeout = 0")
            connection.execute("BEGIN IMMEDIATE")
            connection.rollback()
            return True
        except sqlite3.Error:
            return False
        finally:
            connection.close()

    def _run(self) -> None:
        while not self._stop.is_set():
            self.samples.append(
                {"at_ms": round(time.monotonic() * 1000), "writer_accepted": self._probe()}
            )
            self._stop.wait(self.interval)

    def __enter__(self) -> "LockSampler":
        self._thread.start()
        return self

    def __exit__(self, *_exc: object) -> None:
        self._stop.set()
        self._thread.join(timeout=2.0)


def provider_spans(header: str) -> dict[str, str]:
    return {
        item.split("=")[0]: item.split("=", 1)[1]
        for item in (header or "").split(",")
        if "=" in item
    }


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
            "CITYNEXUS_PROVIDER_TIMING": "1",
            "PYTHONIOENCODING": "utf-8",
        }
    )
    log_path = OUT_DIR / "uvicorn.log"
    with log_path.open("wb") as log_handle:
        server = subprocess.Popen(
            [str(PYTHON), "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(port)],
            cwd=BACKEND,
            env=env,
            stdout=log_handle,
            stderr=log_handle,
        )
    base = f"http://127.0.0.1:{port}"
    results: list[dict[str, object]] = []
    generation: dict[str, object] = {}
    try:
        for _ in range(120):
            try:
                if httpx.get(f"{base}/health", timeout=2.0).status_code < 500:
                    break
            except Exception:
                pass
            time.sleep(0.5)
        else:
            print(json.dumps({"fatal": "server never answered /health", "log": str(log_path)}))
            return 2

        traveler = httpx.post(f"{base}/api/v1/demo/reset", timeout=90.0).json()["traveler_id"]
        start = datetime(2026, 11, 3, 9, 0, tzinfo=TZ)
        journey_id = httpx.post(
            f"{base}/api/v1/journeys",
            json={
                "traveler_id": traveler,
                "title": "ORD-0068 inline routes",
                "city_code": "CN-XIAMEN",
                "timezone": "Asia/Shanghai",
                "start_at": start.isoformat(),
                "end_at": (start + timedelta(days=2, hours=8)).isoformat(),
                "budget": {"amount_minor": 90000, "currency": "CNY"},
                "planning_mode": "balanced",
            },
            timeout=90.0,
        ).json()["id"]

        def call(label: str, method: str, template: str, option_id: str | None) -> dict[str, object]:
            url = base + template.format(jid=journey_id, oid=option_id or "none")
            with LockSampler(DB_FILE) as sampler:
                began = time.perf_counter()
                try:
                    response = httpx.request(method, url, json={}, timeout=600.0)
                    status, header, text = (
                        response.status_code,
                        response.headers.get("X-CityNexus-Phase-Ms", ""),
                        response.text[:400],
                    )
                except Exception as exc:  # a timeout is a measurement, not a crash of the probe
                    status, header, text = 0, "", f"{type(exc).__name__}: {exc}"
                elapsed_ms = round((time.perf_counter() - began) * 1000.0, 1)
            spans = provider_spans(header)
            blocked = [item for item in sampler.samples if item["writer_accepted"] is False]
            return {
                "route": label,
                "status": status,
                "http_ms": elapsed_ms,
                "provider_calls_seen": sorted(name for name in spans if name.startswith("provider.")),
                "stay_generate_ms": spans.get("stay.generate"),
                "writer_blocked_samples": len(blocked),
                "writer_samples": len(sampler.samples),
                "body_head": text,
            }

        # Condition 1: nothing captured yet for this city - the cold case.
        for label, method, template in ROUTES:
            results.append({**call(label, method, template, None), "condition": "cold_city"})

        # Produce evidence the honest way, through the operation queue, then measure the same
        # two routes a second time with frozen evidence already in the library.
        operation = httpx.post(
            f"{base}/api/v1/journeys/{journey_id}/stay-generations", json={}, timeout=90.0
        ).json()
        operation_id = operation.get("operation_id")
        waited_ms = time.monotonic()
        state: dict[str, object] = {}
        polls = 0
        # A real deadline, not `time.monotonic() < 600`: this machine's monotonic clock is
        # already in the six figures, so that comparison was false on the first test, the
        # loop body never ran, and the report still looked like a completed measurement.
        deadline = time.monotonic() + 600
        while time.monotonic() < deadline:
            state = httpx.get(
                f"{base}/api/v1/journeys/{journey_id}/stay-generations/{operation_id}", timeout=30.0
            ).json()
            polls += 1
            if state.get("terminal"):
                break
            time.sleep(0.5)
        generation = {
            "operation_id": operation_id,
            "status": state.get("status"),
            "outcome": state.get("outcome"),
            "elapsed_ms": state.get("elapsed_ms"),
            "waited_ms": round((time.monotonic() - waited_ms) * 1000),
            "polls": polls,
        }
        option_ids = [item["id"] for item in (state.get("result") or {}).get("top_k", [])]

        # The instrument refuses rather than reports.  Zero polls, a non-terminal operation
        # or no ranked option means *this probe* never measured the second condition; going on
        # would emit `with_evidence` rows that timed a path which does not exist, and a reader
        # would file the resulting `status: null` as a product defect.  Standing rule
        # (CURRENT_GATES 11): a probe whose own instrument did not run must be loud, never
        # plausible-looking JSON.
        fatal = ""
        if polls == 0:
            fatal = "poll loop never executed"
        elif not state.get("terminal"):
            fatal = f"cold generation never reached a terminal state: {state.get('status')}"
        elif state.get("status") != "COMPLETED":
            fatal = f"cold generation ended as {state.get('status')}, not COMPLETED"
        elif not option_ids:
            # A real product observation, named as itself instead of papered over.
            fatal = "no_option_produced"
        if fatal:
            OUT_DIR.joinpath("inline-routes.json").write_text(
                json.dumps(
                    {
                        "fatal": fatal,
                        "no_option_produced": fatal if fatal == "no_option_produced" else None,
                        "cold_generation": generation,
                        "cold_results": results,
                        "log": str(log_path),
                    },
                    indent=2,
                    ensure_ascii=False,
                ),
                encoding="utf-8",
                newline=LF,
            )
            print(f"FATAL from this probe, not the product: {fatal}", file=sys.stderr)
            return 3
        print(f"with_evidence armed by {len(option_ids)} ranked option(s)")
        for label, method, template in ROUTES:
            row = {**call(label, method, template, option_ids[0]), "condition": "with_evidence"}
            row["option_available"] = True
            results.append(row)

        report = {
            "measured_at": datetime.now(timezone.utc).isoformat(),
            "run_id": RUN_ID,
            "server": {"pid": server.pid, "port": port, "database": DB_FILE.name},
            "journey_id": journey_id,
            "cold_generation": generation,
            "results": results,
            "caveats": [
                "No egress on this machine's measured link, so a provider call spends its full "
                "per-host timeout; that is the cold condition, not an idle one.",
                "writer_blocked_samples counts BEGIN IMMEDIATE attempts that SQLite refused "
                "outright (busy_timeout=0): >0 means the request held the single writer while "
                "it ran.",
                "The preview instance (:4781/:4782/:8781) and its database were not used.",
            ],
            "log": str(log_path),
        }
        OUT_DIR.joinpath("inline-routes.json").write_text(
            json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8", newline="\n"
        )
        for row in results:
            print(
                f"{row['condition']:15s} {row['route']:18s} status={row['status']} "
                f"{row['http_ms']}ms provider={row['provider_calls_seen']} "
                f"writer_blocked={row['writer_blocked_samples']}/{row['writer_samples']}"
            )
        print("->", OUT_DIR / "inline-routes.json")
        return 0
    finally:
        server.terminate()
        try:
            server.wait(timeout=30)
        except Exception:
            server.kill()


if __name__ == "__main__":
    raise SystemExit(main())
