"""ORD-0203 step 0 -- produce the real `NOT_ANSWERED` answer and print it verbatim.

The order says the cell exists in the backend and in the contract while `frontend/src` has zero
hits, and its first delivery is to render it.  Before writing any copy I need the shape the server
actually sends, from the *real* code path rather than from a fixture I invented: `RUNTIME_FAILURE`
becomes `NOT_ANSWERED` when the resolver is switched on and cannot answer
(`anywhere_capability.py:1380-1394`), which is reachable by pointing the Photon base URL at a closed
port.

Also prints the two neighbours so the screen's branching can be checked against the real vocabulary:
a named-but-empty city (`HYDRATABLE`) and an unnameable string (`UNAVAILABLE/NO_CANONICAL_IDENTITY`).

Own instance, own empty database, own :85xx port.  No `demo/reset`; nothing touches
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
PORT = int(os.environ.get("PROBE_PORT", "8581"))
RUN_ID = f"na{int(time.time()) % 1000000:06d}"
BASE = f"http://127.0.0.1:{PORT}/api/v1"
# A closed port on localhost: the resolver is switched on, so it really tries, and really fails.
DEAD_PHOTON = "http://127.0.0.1:9"


def call(method: str, path: str, body=None, timeout: int = 90) -> tuple[int, object]:
    request = urllib.request.Request(
        f"{BASE}{path}",
        method=method,
        data=None if body is None else json.dumps(body).encode(),
        headers={"Content-Type": "application/json", "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
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
    except Exception as error:  # noqa: BLE001 - the probe records what it saw
        return 0, repr(error)


def main() -> int:
    env = dict(os.environ)
    env.update(
        {
            "CITYNEXUS_DEMO_MODE": "true",
            "CITYNEXUS_AI_ENABLED": "false",
            "CITYNEXUS_DATABASE_URL": f"sqlite:///{ROOT}/review/evidence/_{RUN_ID}.db",
            # Switch the real resolver on and make it unreachable: this is what turns a runtime
            # failure into the cell the order is about.
            "CITYNEXUS_ANYWHERE_RESOLVER": "photon",
            "CITYNEXUS_PHOTON_BASE_URL": DEAD_PHOTON,
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
    out: dict[str, object] = {"run": RUN_ID, "port": PORT, "photon": DEAD_PHOTON}
    try:
        for _ in range(60):
            status, _ = call("GET", "/health")
            if status == 200:
                break
            time.sleep(1)
        else:
            print("backend never answered /health; nothing was measured")
            return 2

        for label, query in [
            ("resolver-down", "天津"),
            ("county", "贡山独龙族怒族自治县"),
            ("nonsense", "zzxqvw-不存在县"),
        ]:
            started = time.time()
            status, body = call("GET", "/destinations/capability?query=" + urllib.parse.quote(query))
            elapsed = round(time.time() - started, 2)
            out[f"capability.{label}"] = {"status": status, "elapsed_s": elapsed, "body": body}
            if isinstance(body, dict):
                print(
                    f"\n=== {label} ({query}) status={status} elapsed={elapsed}s ===\n"
                    f"  capability={body.get('capability')!r} reason_code={body.get('reason_code')!r}\n"
                    f"  recommended_action={body.get('recommended_action')!r} retryable={body.get('retryable')!r}\n"
                    f"  destination_state={body.get('destination_state')!r} resolution={body.get('destination_resolution')!r}\n"
                    f"  provider_status={json.dumps(body.get('provider_status'), ensure_ascii=False)}\n"
                    f"  pending_destination_label={body.get('pending_destination_label')!r} "
                    f"fidelity={body.get('pending_label_fidelity')!r}\n"
                    f"  missing_categories={body.get('missing_categories')}\n"
                    f"  keys={sorted(body.keys())}"
                )
            else:
                print(f"\n=== {label} status={status} -> {body}")
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=20)
        except subprocess.TimeoutExpired:
            proc.kill()

    with open(f"{ROOT}/review/ord0203-not-answered-probe.json", "w", encoding="utf-8", newline="") as handle:
        handle.write(json.dumps(out, ensure_ascii=False, indent=2) + "\n")
    print("\nwrote review/ord0203-not-answered-probe.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
