"""Which activity can 「建一个硬承诺」 actually be aimed at today?

ORD-0100 ① asks the panel to pick its default booking target from the server's own catalogue instead
of from the order of the plan array.  Two reads turned out to be in the way, and both are measured
here rather than assumed:

  1. `GET /city-services?city_code=` says which *places* carry a bookable/tradable service.
  2. `GET /city-services/{id}/booking-slots?start_at=&end_at=` says whether that service has a slot in
     the activity's own window -- and the frozen catalog refuses some activities even after (1) passes.

The row's default has to be an activity that survives both, otherwise the panel is still throwing a
422 at the teacher, just a better-explained one.  Each candidate is then asked for a real booking, so
the answer the row promises is the answer the server gives.

Own throwaway stack, own port, own DB; `backend/**` untouched.
"""

import json
import os
import socket
import subprocess
import sys
import time

import httpx

ROOT = "D:/moodle/_qoder_integration_20260919"
OUT = f"{ROOT}/review/bookable-target-shape.json"
RUN = f"bktarget{int(time.time()) % 100000:05d}"
ORDERABLE = {"bookable_experience", "tradable_food"}


def free_port(start: int) -> int:
    probe = socket.socket()
    probe.bind(("127.0.0.1", 0))
    port = int(probe.getsockname()[1])
    probe.close()
    return max(port, start)


PORT = free_port(8860)


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
report: dict = {"run": RUN, "port": PORT, "candidates": []}
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

    journey_id = client.post("/api/v1/demo/reset").json().get("journey_id")
    city_code = client.get(f"/api/v1/journeys/{journey_id}").json().get("city_code")
    report["journey_id"] = journey_id
    report["city_code"] = city_code
    prepared = client.post("/api/v1/demo/prepare-scenario").json()
    plan_id = prepared.get("plan_version_id")
    activities = client.get(f"/api/v1/plans/{plan_id}").json().get("activities", [])
    services = client.get("/api/v1/city-services", params={"city_code": city_code}).json()
    report["services"] = services

    by_place: dict = {}
    for row in services:
        if row.get("service_type") in ORDERABLE and row.get("place_id"):
            by_place.setdefault(row["place_id"], []).append(row)

    for activity in activities:
        place = activity.get("place_id")
        matched = by_place.get(place, [])
        entry: dict = {
            "title": activity.get("title"),
            "place_id": place,
            "status": activity.get("status"),
            "window": [activity.get("start_at"), activity.get("end_at")],
            "services_matching_catalogue_type": [
                {"id": s["id"], "type": s["service_type"]} for s in matched
            ],
        }
        for service in matched:
            slots = client.get(
                f"/api/v1/city-services/{service['id']}/booking-slots",
                params={"start_at": activity.get("start_at"), "end_at": activity.get("end_at")},
            )
            try:
                body = slots.json()
            except Exception:  # noqa: BLE001
                body = slots.text[:300]
            if isinstance(body, dict):
                inner = body.get("slots", body)
                count = len(inner) if isinstance(inner, list) else None
            else:
                count = len(body)
            entry.setdefault("slots", []).append(
                {
                    "service": service["id"],
                    "http": slots.status_code,
                    "count": count,
                    "body": body if count in (None, 0) or slots.status_code >= 400 else None,
                }
            )
        booked = client.post(
            f"/api/v1/journeys/{journey_id}/bookings",
            json={"activity_id": activity.get("id")},
        )
        try:
            payload = booked.json()
        except Exception:  # noqa: BLE001
            payload = booked.text[:200]
        error = payload.get("error") if isinstance(payload, dict) else None
        entry["booking"] = {
            "http": booked.status_code,
            "status": payload.get("status") if isinstance(payload, dict) else None,
            "message": error.get("message") if isinstance(error, dict) else None,
        }
        report["candidates"].append(entry)
        print(
            f"{str(entry['title'])[:24]:24s} place={str(place):22s} "
            f"catalogue_types={[s['type'] for s in entry['services_matching_catalogue_type']] or '-'} "
            f"slots={entry.get('slots')} booking={booked.status_code} "
            f"{entry['booking']['status'] or entry['booking']['message']}",
            flush=True,
        )

    orderable = [
        c
        for c in report["candidates"]
        if c["booking"]["http"] < 300
    ]
    report["verdict"] = {
        "array_order_first_activity": activities[0].get("title") if activities else None,
        "first_by_catalogue_type": next(
            (
                c["title"]
                for c in report["candidates"]
                if c["services_matching_catalogue_type"]
            ),
            None,
        ),
        "first_that_actually_books": orderable[0]["title"] if orderable else None,
        "how_many_book_now": len(orderable),
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
print(f"wrote {OUT}")
