"""What does the catalogue actually say is orderable on this journey?

ORD-0100 ① asks the booking row to pick its default target from the server instead of from the order
of the plan array.  Before the panel can filter on it, three things have to be read off a real stack:
the journey's own `city_code` (the argument the read needs), every row `GET /city-services` answers
for it with its `service_type` and `place_id`, and what the plan hands out per activity -- because the
claim under test is that `city_service_id` is null on all of them, which is what made the old
"services first" sort a no-op.

Own throwaway stack, own port, own DB. Nothing here touches the preview or `backend/**`.
"""

import json
import os
import socket
import subprocess
import sys
import time

import httpx

ROOT = "D:/moodle/_qoder_integration_20260919"
OUT = f"{ROOT}/review/city-services-shape.json"
RUN = f"csvc{int(time.time()) % 100000:05d}"
BOOKABLE_CLAIMED = {"bookable_experience", "tradable_food"}


def free_port(start: int) -> int:
    probe = socket.socket()
    probe.bind(("127.0.0.1", 0))
    port = int(probe.getsockname()[1])
    probe.close()
    return max(port, start)


PORT = free_port(8800)


def port_free(number: int) -> bool:
    probe = socket.socket()
    probe.settimeout(0.5)
    try:
        probe.bind(("127.0.0.1", number))
        return True
    except OSError:
        return False
    finally:
        probe.close()


if not port_free(PORT):
    print(f"ABORT: :{PORT} is already listening")
    sys.exit(2)

env = dict(os.environ)
db = f"{ROOT}/review/evidence/_{RUN}.db"
env.update(
    {
        "CITYNEXUS_DATABASE_URL": f"sqlite:///{db}",
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
report: dict = {"run": RUN, "port": PORT}
try:
    base = f"http://127.0.0.1:{PORT}"
    for _ in range(90):
        try:
            if httpx.get(f"{base}/api/v1/health", timeout=2).status_code == 200:
                break
        except Exception:  # noqa: BLE001
            pass
        time.sleep(1)
    client = httpx.Client(base_url=base, timeout=300)

    reset = client.post("/api/v1/demo/reset").json()
    journey_id = reset.get("journey_id")
    journey = client.get(f"/api/v1/journeys/{journey_id}").json()
    city_code = journey.get("city_code")
    report["journey"] = {
        "id": journey_id,
        "city_code": city_code,
        "status": journey.get("status"),
        "http_keys": sorted(journey.keys()),
    }
    print(f"journey={journey_id} city_code={city_code!r} status={journey.get('status')!r}")

    services = client.get("/api/v1/city-services", params={"city_code": city_code})
    rows = services.json() if services.status_code == 200 else None
    report["city_services"] = {
        "http": services.status_code,
        "count": len(rows) if isinstance(rows, list) else None,
        "rows": rows,
    }
    print(f"\nGET /city-services?city_code={city_code} -> {services.status_code}, {len(rows) if isinstance(rows, list) else '?'} rows")
    if isinstance(rows, list):
        for row in rows:
            mark = "BOOKABLE" if row.get("service_type") in BOOKABLE_CLAIMED else "        "
            print(f"  {mark} {row.get('id'):32s} {str(row.get('service_type')):22s} place={row.get('place_id')}")

    prepared = client.post("/api/v1/demo/prepare-scenario").json()
    plan_id = prepared.get("plan_version_id")
    plan = client.get(f"/api/v1/plans/{plan_id}").json()
    activities = plan.get("activities", [])
    bookable_places = {
        row.get("place_id")
        for row in (rows or [])
        if isinstance(row, dict) and row.get("service_type") in BOOKABLE_CLAIMED
    }
    report["plan"] = {
        "plan_version_id": plan_id,
        "journey_status": prepared.get("journey_status"),
        "activity_keys": sorted(activities[0].keys()) if activities else [],
        "activities": [
            {
                "title": a.get("title"),
                "place_id": a.get("place_id"),
                "city_service_id": a.get("city_service_id"),
                "status": a.get("status"),
                "place_is_bookable": a.get("place_id") in bookable_places,
            }
            for a in activities
        ],
    }
    print(f"\nGET /plans/{plan_id} -> {len(activities)} activities")
    for a in report["plan"]["activities"]:
        print(
            f"  {str(a['title'])[:26]:26s} place={str(a['place_id']):24s} "
            f"city_service_id={a['city_service_id']!r} bookable_by_place={a['place_is_bookable']}"
        )
    matched = [a for a in report["plan"]["activities"] if a["place_is_bookable"]]
    report["verdict"] = {
        "activities_matching_a_bookable_place": len(matched),
        "first_match": matched[0]["title"] if matched else None,
        "first_activity_in_array_order": activities[0].get("title") if activities else None,
        "city_service_id_non_null_count": sum(
            1 for a in activities if a.get("city_service_id")
        ),
    }
    print("\nVERDICT:", json.dumps(report["verdict"], ensure_ascii=False))
finally:
    subprocess.run(f"taskkill /PID {server.pid} /T /F", shell=True, capture_output=True)
    try:
        server.wait(timeout=20)
    except subprocess.TimeoutExpired:
        server.kill()
    try:
        os.remove(db)
    except OSError:
        pass

with open(OUT, "w", encoding="utf-8", newline="\n") as handle:
    json.dump(report, handle, ensure_ascii=False, indent=2)
print(f"\nwrote {OUT}")
