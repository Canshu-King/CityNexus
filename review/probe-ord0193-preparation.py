"""ORD-0193 step 0 -- measure the destination-preparation path at runtime before building any UI.

The order says "不得发明新的后端真值" and my own lane rule is to measure before asserting a shape.
This asks a live throwaway backend three questions and prints the raw answers:

  1. is `GET /destinations/capability` reachable at all, and what does it answer for a destination
     this build has no catalogue for (the traveller's real case) -- and for one it does have;
  2. does `POST /catalog-hydrations` accept a request and what does its job record look like while
     it is open (the fields a waiting screen could honestly show);
  3. what does the same job read as once it reaches a terminal state, and is `abandon` idempotent.

Own instance, own empty database, own :85xx port.  Nothing here calls `demo/reset`; nothing touches
:4781/:4782/:8693 or the live preview database.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

for stream in (sys.stdout, sys.stderr):
    if hasattr(stream, "reconfigure"):
        stream.reconfigure(encoding="utf-8", errors="replace")

ROOT = "D:/moodle/_qoder_integration_20260919"
PORT = int(os.environ.get("PROBE_PORT", "8571"))
RUN_ID = f"prep{int(time.time()) % 1000000:06d}"
BASE = f"http://127.0.0.1:{PORT}/api/v1"


def call(method: str, path: str, body=None) -> tuple[int, object]:
    request = urllib.request.Request(
        f"{BASE}{path}",
        method=method,
        data=None if body is None else json.dumps(body).encode(),
        headers={"Content-Type": "application/json", "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            raw = response.read().decode("utf-8", "replace")
            try:
                return response.status, json.loads(raw)
            except json.JSONDecodeError:
                return response.status, raw[:400]
    except urllib.error.HTTPError as error:
        raw = error.read().decode("utf-8", "replace")
        try:
            return error.code, json.loads(raw)
        except json.JSONDecodeError:
            return error.code, raw[:400]
    except Exception as error:  # noqa: BLE001 - the probe records whatever it saw
        return 0, repr(error)


def main() -> int:
    env = dict(os.environ)
    env.update(
        {
            "CITYNEXUS_DEMO_MODE": "true",
            "CITYNEXUS_AI_ENABLED": "false",
            "CITYNEXUS_DATABASE_URL": f"sqlite:///{ROOT}/review/evidence/_{RUN_ID}.db",
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
    out: dict[str, object] = {"run": RUN_ID, "port": PORT}
    try:
        for _ in range(60):
            status, _ = call("GET", "/health")
            if status == 200:
                break
            time.sleep(1)
        else:
            print("backend never answered /health; nothing was measured")
            return 2

        # 1. capability for a destination this build has no catalogue for, then one it may have.
        for label, query in [
            ("unknown-place", "zzxqvw-不存在县"),
            ("county", "贡山独龙族怒族自治县"),
            ("seeded-city", "天津"),
        ]:
            status, body = call("GET", "/destinations/capability?query=" + urllib.parse.quote(query))
            out[f"capability.{label}"] = {"query": query, "status": status, "body": body}
            if isinstance(body, dict):
                print(
                    f"{status:>4} capability {label:<13} capability={body.get('capability')!r} "
                    f"reason={body.get('reason_code')!r} action={body.get('recommended_action')!r} "
                    f"state={body.get('destination_state')!r} places={body.get('place_count')} "
                    f"missing={body.get('missing_categories')}"
                )
            else:
                print(f"{status:>4} capability {label} -> {body}")

        # 2. start a hydration and read the job while it is open.
        status, job = call("POST", "/catalog-hydrations", {"query": "贡山独龙族怒族自治县"})
        out["hydration.create"] = {"status": status, "body": job}
        print(f"\n{status:>4} POST /catalog-hydrations -> {json.dumps(job, ensure_ascii=False)[:400]}")
        operation_id = job.get("operation_id") if isinstance(job, dict) else None

        if operation_id:
            snapshots = []
            for attempt in range(20):
                read_status, row = call("GET", f"/catalog-hydrations/{operation_id}")
                if isinstance(row, dict):
                    snapshots.append(
                        {
                            "t": attempt,
                            "status": row.get("status"),
                            "phase": row.get("phase"),
                            "outcome": row.get("outcome"),
                            "terminal": row.get("terminal"),
                            "elapsed_ms": row.get("elapsed_ms"),
                            "retryable": row.get("retryable"),
                            "has_progress_field": "progress" in row,
                            "error": row.get("error"),
                        }
                    )
                    print(
                        f"  t={attempt:<2} status={row.get('status'):<18} phase={str(row.get('phase')):<22} "
                        f"outcome={str(row.get('outcome')):<32} terminal={row.get('terminal')} "
                        f"elapsed_ms={row.get('elapsed_ms')}"
                    )
                    if row.get("terminal"):
                        break
                time.sleep(1.5)
            out["hydration.poll"] = snapshots
            # 3. abandon twice: idempotent?
            first = call("POST", f"/catalog-hydrations/{operation_id}/abandon")
            second = call("POST", f"/catalog-hydrations/{operation_id}/abandon")
            out["hydration.abandon"] = {"first": first[0], "second": second[0], "secondBody": second[1]}
            print(f"\n  abandon -> {first[0]} then {second[0]}")
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=20)
        except subprocess.TimeoutExpired:
            proc.kill()

    with open(f"{ROOT}/review/ord0193-prep-probe.json", "w", encoding="utf-8", newline="") as handle:
        handle.write(json.dumps(out, ensure_ascii=False, indent=2) + "\n")
    print(f"\nwrote review/ord0193-prep-probe.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
