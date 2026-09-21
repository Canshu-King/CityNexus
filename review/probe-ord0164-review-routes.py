"""ORD-0164 / ORD-0146 ① -- is there any server-side review/promote route?  Asked of a live
backend, not of grep.

The commander's rule for this lane: prove a route at runtime (404 = no such path, 405 = the path
exists and answers other methods, 422/400 = it exists and wants a body).  A `grep` absence is not a
conclusion -- it has already been wrong once in this project when the wording differed.

Own instance, own fresh database, own :85xx port.  Nothing here calls `demo/reset`, nothing touches
:4781/:4782/:8693 or the live preview database.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request

for stream in (sys.stdout, sys.stderr):
    if hasattr(stream, "reconfigure"):
        stream.reconfigure(encoding="utf-8", errors="replace")

ROOT = "D:/moodle/_qoder_integration_20260919"
PORT = int(os.environ.get("PROBE_PORT", "8561"))
RUN_ID = f"probe{int(time.time()) % 1000000:06d}"
BASE = f"http://127.0.0.1:{PORT}/api/v1"
GHOST = "ca0f1ed1-485a-4d65-8c19-0087ce5e29fd"  # the commander's 21:30 sample: an id not in the db

# (label, method, path, body)
PROBES = [
    ("known-good health", "GET", "/health", None),
    ("known-good journey read (ghost id)", "GET", f"/journeys/{GHOST}/experience", None),
    ("inbox list (ghost id)", "GET", f"/journeys/{GHOST}/inbox", None),
    ("inbox confirm (ghost id)", "POST", f"/journeys/{GHOST}/inbox/00000000-0000-0000-0000-000000000001/confirm", {}),
    ("candidate review queue", "GET", "/journeys/00000000-0000-0000-0000-000000000001/inbox/pending", None),
    ("candidate approve", "POST", f"/journeys/{GHOST}/inbox/x/approve", {}),
    ("candidate reject", "POST", f"/journeys/{GHOST}/inbox/x/reject", {}),
    ("candidate promote", "POST", f"/journeys/{GHOST}/inbox/x/promote", {}),
    ("candidate review decision", "POST", f"/journeys/{GHOST}/reviews", {}),
    ("candidate delegation policy", "GET", "/delegations/policy", None),
    ("candidate commitments promote", "POST", "/commitments/promote", {}),
    ("OPTIONS on the real confirm path", "OPTIONS", f"/journeys/{GHOST}/inbox/x/confirm", None),
    ("OPTIONS on a nonexistent review path", "OPTIONS", f"/journeys/{GHOST}/inbox/x/review", None),
]


def call(method: str, path: str, body) -> tuple[int, str, dict]:
    request = urllib.request.Request(
        f"{BASE}{path}",
        method=method,
        data=None if body is None else json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            return response.status, response.read()[:200].decode("utf-8", "replace"), dict(response.headers)
    except urllib.error.HTTPError as error:
        return error.code, error.read()[:200].decode("utf-8", "replace"), dict(error.headers)
    except Exception as error:  # noqa: BLE001 - the point is to record what the probe saw
        return 0, repr(error), {}


def main() -> int:
    env = dict(os.environ)
    env.update(
        {
            "CITYNEXUS_DEMO_MODE": "true",
            "CITYNEXUS_AI_ENABLED": "false",
            "CITYNEXUS_DATABASE_URL": f"sqlite:///{ROOT}/review/evidence/_{RUN_ID}.db",
            "CITYNEXUS_PORT": str(PORT),
        }
    )
    for key in ("DEEPSEEK_API_KEY", "CITYNEXUS_AI_API_KEY"):
        env.pop(key, None)
    proc = subprocess.Popen(
        [
            "D:/moodle/CityNexus/.venv/Scripts/python.exe",
            "-m",
            "uvicorn",
            "app.main:app",
            "--host",
            "127.0.0.1",
            f"--port={PORT}",
        ],
        cwd=f"{ROOT}/backend",
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    rows = []
    try:
        for _ in range(60):
            status, _, _ = call("GET", "/health", None)
            if status == 200:
                break
            time.sleep(1)
        else:
            print("backend never answered /health; nothing was measured")
            return 2
        for label, method, path, body in PROBES:
            status, text, headers = call(method, path, body)
            rows.append(
                {
                    "label": label,
                    "method": method,
                    "path": path.replace(GHOST, "{ghost}"),
                    "status": status,
                    "allow": headers.get("allow") or headers.get("Allow"),
                    "body": text[:120],
                }
            )
            print(f"{status:>4}  {method:<7} {path.replace(GHOST, '{ghost}')[:60]:<62} allow={headers.get('allow') or headers.get('Allow') or '-'}  {text[:70]}", flush=True)
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=15)
        except subprocess.TimeoutExpired:
            proc.kill()

    verdict = {
        "reviewRoutesFound": [
            row for row in rows if row["status"] not in (404, 0) and "candidate" in row["label"]
        ],
        "confirmPathExists": any(
            row["label"].startswith("inbox confirm") and row["status"] in (404, 409, 422) and "not found" in row["body"].lower()
            for row in rows
        ),
    }
    print("\n== verdict ==", json.dumps(verdict, ensure_ascii=False, indent=2))
    with open(f"{ROOT}/review/ord0164-route-probe.json", "w", encoding="utf-8", newline="") as handle:
        handle.write(json.dumps({"run": RUN_ID, "port": PORT, "rows": rows, "verdict": verdict}, ensure_ascii=False, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
