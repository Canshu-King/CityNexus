"""Why does the panel's 「建一个硬承诺」 get 422 request.invalid?

The gate pressed it six times and got the same named validation refusal each time, while the backend
tests book the river cruise with the same body shape.  So either the id the panel sends is not the id
the server named, or the refusal is about a different field.  Measure it end to end on a throwaway
stack and print the body: `loc` decides the field, `message_key` decides the words.
"""

import json
import os
import subprocess
import sys
import time

import httpx

ROOT = "D:/moodle/_qoder_integration_20260919"
PORT = 8560
RUN = f"book{int(time.time()) % 100000:05d}"

env = dict(os.environ)
env.update(
    {
        "CITYNEXUS_DATABASE_URL": f"sqlite:///{ROOT}/review/evidence/_{RUN}.db",
        "CITYNEXUS_AI_ENABLED": "false",
        "CITYNEXUS_DEMO_MODE": "true",
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
findings = {"run": RUN}
try:
    base = f"http://127.0.0.1:{PORT}"
    for _ in range(90):
        try:
            if httpx.get(f"{base}/api/v1/health", timeout=2).status_code == 200:
                break
        except Exception:  # noqa: BLE001 - still booting
            pass
        time.sleep(1)
    client = httpx.Client(base_url=base, timeout=300)

    reset = client.post("/api/v1/demo/reset")
    findings["reset"] = {"status": reset.status_code, "journey_id": reset.json().get("journey_id")}
    journey_id = reset.json()["journey_id"]
    prepared = client.post("/api/v1/demo/prepare-scenario")
    body = prepared.json()
    findings["prepare"] = {
        "status": prepared.status_code,
        "journey_status": body.get("journey_status"),
        "plan_version_id": body.get("plan_version_id"),
        "code": (body.get("error") or {}).get("code") if not prepared.is_success else None,
    }
    plan_id = body.get("plan_version_id")
    scene = client.get("/api/v1/demo/scene").json()
    findings["scene"] = {
        "journey_status": scene.get("journey_status"),
        "plan_version_id": scene.get("plan_version_id"),
        "current_activity_id": scene.get("current_activity_id"),
    }
    plan = client.get(f"/api/v1/plans/{plan_id}").json()
    activities = plan.get("activities") or []
    findings["plan"] = {
        "activity_count": len(activities),
        "first_activity_keys": sorted(activities[0].keys()) if activities else [],
        "activities": [
            {
                "id": item.get("id"),
                "title": item.get("title"),
                "sequence_no": item.get("sequence_no"),
                "status": item.get("status"),
                "city_service_id": item.get("city_service_id"),
                "place_id": item.get("place_id"),
            }
            for item in activities
        ],
    }
    # Exactly what the panel sends: the first candidate in the plan's own order.
    for item in activities[:6]:
        answer = client.post(
            f"/api/v1/journeys/{journey_id}/bookings",
            json={"activity_id": item.get("id")},
        )
        findings.setdefault("bookings", []).append(
            {
                "activity_id": item.get("id"),
                "title": item.get("title"),
                "http": answer.status_code,
                "body": answer.json() if answer.headers.get("content-type", "").startswith("application/json") else answer.text[:200],
            }
        )
finally:
    server.terminate()
    time.sleep(2)

print(json.dumps(findings, ensure_ascii=False, indent=2)[:6000], flush=True)
with open(f"{ROOT}/review/bookings-{RUN}.json", "w", encoding="utf-8", newline="") as fh:
    json.dump(findings, fh, ensure_ascii=False, indent=2)
print(f"written review/bookings-{RUN}.json", flush=True)
