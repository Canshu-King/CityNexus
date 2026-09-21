"""Does 「建一个硬承诺」 still mean something once the journey is ACTIVE?

The Commander asked (ORD-0090 residual 3) to grey the booking row out in the ACTIVE stage "with one
plain-words reason".  A reason has to be a fact, so this probe asks the server before the panel says
anything: same journey, same activity, one POST /bookings while it is PLANNED and one after
`start-scenario` has put it into execution, with the full envelope of each answer kept on disk.

Own throwaway stack on its own port and its own DB; nothing here touches the preview (`:4781/:4782/
:8781`, `_preview.db`) and no `backend/**` file is read for anything but the routes the panel calls.
"""

import json
import os
import socket
import subprocess
import sys
import time

import httpx

ROOT = "D:/moodle/_qoder_integration_20260919"
OUT = f"{ROOT}/review/booking-when-active.json"
RUN = f"bkact{int(time.time()) % 100000:05d}"


def free_port(start: int) -> int:
    """Ask the OS for a port: a fixed one plus `shell=True` once left an orphan uvicorn behind."""
    probe = socket.socket()
    probe.bind(("127.0.0.1", 0))
    port = int(probe.getsockname()[1])
    probe.close()
    return max(port, start)


PORT = free_port(8620)


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
    print(f"ABORT: :{PORT} is already listening; this probe would read someone else's stack")
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

report: dict = {"run": RUN, "port": PORT, "steps": []}


def note(name: str, **fields) -> None:
    report["steps"].append({"step": name, **fields})
    line = json.dumps(report["steps"][-1], ensure_ascii=False)
    print(line, flush=True)


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
    journey_id = reset.json().get("journey_id")
    note("demo/reset", http=reset.status_code, journey_id=journey_id)

    prepared = client.post("/api/v1/demo/prepare-scenario")
    prep = prepared.json()
    plan_id = prep.get("plan_version_id")
    note(
        "demo/prepare-scenario",
        http=prepared.status_code,
        journey_status=prep.get("journey_status"),
        plan_version_id=plan_id,
        error=prep.get("error"),
    )

    plan = client.get(f"/api/v1/plans/{plan_id}").json()
    activities = [
        a
        for a in plan.get("activities", [])
        if str(a.get("status")) not in ("COMPLETED", "SKIPPED", "CANCELLED")
    ]
    note(
        "plans/{id}",
        http=200,
        activities=[
            {
                "id": a.get("id"),
                "title": a.get("title"),
                "status": a.get("status"),
                "city_service_id": a.get("city_service_id"),
                "place_id": a.get("place_id"),
            }
            for a in activities
        ],
    )

    def book(label: str, activity: dict) -> dict:
        response = client.post(
            f"/api/v1/journeys/{journey_id}/bookings",
            json={"activity_id": activity.get("id")},
        )
        try:
            body = response.json()
        except Exception:  # noqa: BLE001
            body = response.text
        note(
            f"POST bookings [{label}] {activity.get('title')}",
            http=response.status_code,
            booking_id=body.get("id") if isinstance(body, dict) else None,
            status=body.get("status") if isinstance(body, dict) else None,
            error=body.get("error") if isinstance(body, dict) else None,
            body=body if not isinstance(body, dict) else None,
        )
        return {"http": response.status_code, "body": body}

    # Every still-open activity gets asked once, in PLANNED state, so the denominator is on disk.
    planned_results = {}
    for activity in activities:
        planned_results[str(activity.get("id"))] = book("PLANNED", activity)

    started = client.post("/api/v1/demo/start-scenario")
    start = started.json()
    note(
        "demo/start-scenario",
        http=started.status_code,
        journey_status=start.get("journey_status"),
        code=(start.get("error") or {}).get("message_key")
        if isinstance(start.get("error"), dict)
        else None,
        advance_total_ms=(start.get("advance") or {}).get("total_ms"),
    )

    twin = client.get(f"/api/v1/journeys/{journey_id}/twin").json()
    context = (twin.get("context") or {})
    note(
        "GET twin (after start)",
        current_activity_id=context.get("current_activity_id"),
        active_plan_version_id=context.get("active_plan_version_id"),
    )

    # The same question again, now that the journey is executing.
    active_results = {}
    for activity in activities:
        active_results[str(activity.get("id"))] = book("ACTIVE", activity)

    scene = client.get("/api/v1/demo/scene").json()
    note(
        "GET demo/scene (end)",
        journey_status=(scene.get("journey") or {}).get("status")
        if isinstance(scene.get("journey"), dict)
        else scene.get("journey_status"),
        raw_keys=sorted(scene.keys()),
    )

    wallet = client.get(f"/api/v1/journeys/{journey_id}/wallet").json() if client.get(
        f"/api/v1/journeys/{journey_id}/wallet"
    ).status_code == 200 else None
    note(
        "GET wallet",
        commitments=[
            {
                "kind": c.get("kind"),
                "ref": c.get("external_ref"),
                "status": c.get("status"),
                "level": c.get("commitment_level"),
            }
            for c in (wallet or {}).get("commitments", [])
        ]
        if isinstance(wallet, dict)
        else None,
    )

    flipped = [
        {
            "activity_id": aid,
            "planned_http": planned_results[aid]["http"],
            "active_http": active_results[aid]["http"],
            "planned_error": (planned_results[aid]["body"] or {}).get("error")
            if isinstance(planned_results[aid]["body"], dict)
            else None,
            "active_error": (active_results[aid]["body"] or {}).get("error")
            if isinstance(active_results[aid]["body"], dict)
            else None,
        }
        for aid in planned_results
        if planned_results[aid]["http"] != active_results[aid]["http"]
    ]
    note(
        "VERDICT",
        bookable_while_planned=sorted(
            [aid for aid, r in planned_results.items() if r["http"] < 300]
        ),
        bookable_while_active=sorted(
            [aid for aid, r in active_results.items() if r["http"] < 300]
        ),
        answers_that_changed=flipped,
    )
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
