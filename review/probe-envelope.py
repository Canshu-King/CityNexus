"""Record the envelope the backend actually sends, so the gates freeze what arrives.

The ledger froze the contract on "the envelope that really arrives", not on the string the
server raises.  A ValueError that escapes a route becomes Starlette's generic 500 body, so
the code text may never reach the client at all -- which is exactly the difference between
a gate that asserts a nameable reason and a gate that asserts a fabricated one.
"""

import json
import os
import subprocess
import sys
import time

import httpx
from fastapi import FastAPI
from fastapi.testclient import TestClient

ROOT = "D:/moodle/_qoder_ui_overnight_20260920"
PORT = 8480
RUN = f"probe{int(time.time()) % 100000:05d}"

findings = {"run": RUN}

# 1. What does an *unhandled* exception leave on the wire?  The product registers handlers
#    only for RequestValidationError and HTTPException (main.py:395, :406), so anything that
#    escapes -- e.g. the temporal ValueError at stay_mobility.py:201 -- falls through to
#    Starlette's server-error middleware.  Measured here rather than assumed.
probe_app = FastAPI()


@probe_app.get("/raises")
def _raises():
    raise ValueError("V13_JOURNEY_DAYS_OUT_OF_BOUNDS:9")


probe_client = TestClient(probe_app, raise_server_exceptions=False)
raw = probe_client.get("/raises")
findings["unhandled_exception"] = {
    "status": raw.status_code,
    "content_type": raw.headers.get("content-type"),
    "body": raw.text[:200],
    "carries_raised_code_text": "V13_JOURNEY_DAYS_OUT_OF_BOUNDS" in raw.text,
    "starlette": __import__("starlette").__version__,
}
print(json.dumps(findings["unhandled_exception"], ensure_ascii=False), flush=True)

# 2. The real app: the anchor-blank 422 that the wizard currently dies on.
env = dict(os.environ)
env.update(
    {
        "CITYNEXUS_DATABASE_URL": f"sqlite:///{ROOT}/review/evidence/_{RUN}.db",
        "CITYNEXUS_AI_ENABLED": "false",
    }
)
env.pop("DEEPSEEK_API_KEY", None)
env.pop("CITYNEXUS_AI_API_KEY", None)
server = subprocess.Popen(
    f'"{sys.executable}" -m uvicorn app.main:app --host 127.0.0.1 --port {PORT}',
    cwd=f"{ROOT}/backend",
    env=env,
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL,
    shell=True,
)
try:
    base = f"http://127.0.0.1:{PORT}"
    for _ in range(60):
        try:
            if httpx.get(f"{base}/api/v1/health", timeout=2).status_code == 200:
                break
        except Exception:  # noqa: BLE001 - still booting
            pass
        time.sleep(1)

    client = httpx.Client(base_url=base, timeout=30)
    traveler = client.post(
        "/api/v1/travelers",
        json={"display_name": "Envelope probe", "locale": "en-GB", "timezone": "Asia/Shanghai"},
    ).json()["id"]

    def journey(start_at: str, end_at: str, arrival: str) -> dict:
        return {
            "traveler_id": traveler,
            "title": "Envelope probe trip",
            "city_code": "Tianjin",
            "timezone": "Asia/Shanghai",
            "start_at": start_at,
            "end_at": end_at,
            "budget": {"amount_minor": 120000, "currency": "CNY"},
            "stay_budget": {"amount_minor": 70000, "currency": "CNY"},
            "party_size": 2,
            "occupancy": {"adults": 2, "rooms": 1},
            "arrival_anchor": {"at": start_at, "location": arrival},
            "departure_anchor": {"at": end_at, "location": "Tianjin Binhai Airport"},
        }

    blank = client.post(
        "/api/v1/journeys",
        json=journey("2026-10-09T18:00:00+08:00", "2026-10-11T15:00:00+08:00", ""),
    )
    findings["blank_anchor_create"] = {"status": blank.status_code, "body": blank.json()}
    print(json.dumps(findings["blank_anchor_create"], ensure_ascii=False)[:700], flush=True)

    legal = client.post(
        "/api/v1/journeys",
        json=journey("2026-10-01T18:00:00+08:00", "2026-10-09T15:00:00+08:00", "Tianjin West Station"),
    )
    findings["nine_day_create"] = {"status": legal.status_code, "body": legal.text[:200]}
    print(json.dumps(findings["nine_day_create"], ensure_ascii=False)[:400], flush=True)
    if legal.status_code == 201:
        journey_id = legal.json()["id"]
        started = time.time()
        try:
            generated = client.post(
                f"/api/v1/journeys/{journey_id}/stay-options/generate", timeout=240
            )
            findings["nine_day_generate"] = {
                "status": generated.status_code,
                "seconds": round(time.time() - started, 2),
                "content_type": generated.headers.get("content-type"),
                "carries_raised_code_text": "V13_JOURNEY_DAYS_OUT_OF_BOUNDS" in generated.text,
                "body": generated.text[:300],
            }
        except Exception as exc:  # noqa: BLE001
            findings["nine_day_generate"] = {
                "status": "no answer",
                "seconds": round(time.time() - started, 2),
                "error": type(exc).__name__,
            }
        print(json.dumps(findings["nine_day_generate"], ensure_ascii=False)[:600], flush=True)
finally:
    server.terminate()
    time.sleep(1)

with open(f"{ROOT}/review/envelope-{RUN}.json", "w", encoding="utf-8", newline="") as fh:
    json.dump(findings, fh, ensure_ascii=False, indent=2)
print(f"written review/envelope-{RUN}.json", flush=True)
