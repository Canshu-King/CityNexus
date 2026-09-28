"""ord0432_witness.py — is `feasibility_envelope.robust` blind to an unresolved MAJOR
disruption, or is the field just frozen?

Two events go through the *same* door (`POST /api/v1/journeys/{id}/events`) on an isolated
lane DB, and the twin is re-read after each:

  A. severity MAJOR, event_type CLOSURE, no `degraded_providers` in its payload.
     -> latest_event_id moves, but `robust` stays true and `risk_reason_codes` stays empty.
  B. severity INFO, event_type OTHER, payload `{"degraded_providers": [...]}`.
     -> `robust` flips false and `risk_reason_codes` names PROVIDER_DEGRADED.

B is the control that makes A mean something: it proves the loop at
`backend/app/main.py:6559-6575` is live and is on the same table, so A is "that loop opens
the row and keeps only one key", not "the value was never computed".

A third, unrelated door (PATCH /journeys/{id} with a 1-minor budget) is recorded verbatim
including its response body, because a refused write must not be reported as a silent pass.

usage: WITNESS_TREE=... python ord0432_witness.py
"""
from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import time
from pathlib import Path

import httpx

LANE = Path(r"D:\moodle\CityNexus-Hermes-Revival\evidence\0212")
TREE = Path(os.environ.get("WITNESS_TREE", r"D:\moodle\_qoder_ai_ord0432_20260929\wt"))
PY = Path(r"D:\moodle\CityNexus\.venv\Scripts\python.exe")
PORT = int(os.environ.get("WITNESS_PORT", "8612"))
BASE = f"http://127.0.0.1:{PORT}"
JID = "22222222-2222-4222-8222-222222222222"
db = LANE / f"_ord0432_{PORT}.db"


def envelope_of(client: httpx.Client) -> dict:
    r = client.get(f"/api/v1/journeys/{JID}/twin", timeout=60)
    r.raise_for_status()
    body = r.json()
    ctx = body.get("context") or {}
    env = ctx.get("feasibility_envelope") or {}
    return {
        "robust": env.get("robust"),
        "risk_reason_codes": env.get("risk_reason_codes"),
        "degraded_providers": env.get("degraded_providers"),
        "budget_remaining_minor": env.get("budget_remaining_minor"),
        "journey_end_slack_min": env.get("journey_end_slack_min"),
        "projection_status": body.get("projection_status"),
        "latest_event_id": body.get("latest_event_id"),
    }


def main() -> int:
    for suffix in ("", "-wal", "-shm"):
        Path(str(db) + suffix).unlink(missing_ok=True)
    subprocess.run([str(PY), str(LANE / "seed_lane_db.py")], check=True, capture_output=True,
                   text=True, env={**os.environ,
                                   "CITYNEXUS_DATABASE_URL": "sqlite:///" + str(db).replace("\\", "/"),
                                   "LANE_BACKEND_ROOT": str(TREE / "backend")})
    srv = subprocess.Popen([str(PY), "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(PORT)],
                           cwd=str(TREE / "backend"),
                           env={**os.environ, "PYTHONPATH": ".",
                                "CITYNEXUS_DATABASE_URL": "sqlite:///" + str(db).replace("\\", "/")},
                           stdout=LANE.joinpath(f"_ord0432_{PORT}_backend.log").open("w", encoding="utf-8"),
                           stderr=subprocess.STDOUT)
    out: dict = {"tree": str(TREE), "port": PORT, "db": str(db)}
    try:
        with httpx.Client(base_url=BASE, timeout=60) as c:
            for _ in range(90):
                try:
                    if c.get("/api/v1/health").status_code == 200:
                        break
                except Exception:
                    pass
                time.sleep(1)
            # the lane builder hardcodes :8513, so drive the same three calls here
            gen = c.post(f"/api/v1/journeys/{JID}/plans/generate", json={})
            if gen.status_code == 201 and gen.json():
                c.post(f"/api/v1/journeys/{JID}/plans/{gen.json()[0]['id']}/select")
                c.post(f"/api/v1/journeys/{JID}/start")

            out["1_baseline"] = envelope_of(c)

            conn = sqlite3.connect(db)
            acts = conn.execute(
                "select a.id, a.title from activities a join plan_versions p on a.plan_version_id=p.id "
                "where p.status='ACTIVE' order by a.start_at").fetchall()
            conn.close()
            target = acts[-1]

            major = c.post(f"/api/v1/journeys/{JID}/events", json={
                "event_type": "CLOSURE", "severity": "MAJOR", "affected_activity_id": target[0],
                "provenance": "SIMULATED",
                "payload": {"reason": "ORD-0432 witness: venue shut for the whole afternoon"}},
                timeout=60)
            out["2A_event_http"] = major.status_code
            out["2A_event_id"] = (major.json() or {}).get("id")
            a = envelope_of(c)
            out["2A_after_major_closure"] = a
            b = out["1_baseline"]
            out["W1_major_event_visible_in_twin"] = bool(a["latest_event_id"]) and a["latest_event_id"] != b["latest_event_id"]
            out["W2_robust_still_true"] = (b["robust"] is True and a["robust"] is True)
            out["W3_risk_codes_still_empty"] = (list(a["risk_reason_codes"] or []) == [])
            out["W3b_projection_status_still_READY"] = (a["projection_status"] == "READY")

            ctrl = c.post(f"/api/v1/journeys/{JID}/events", json={
                "event_type": "OTHER", "severity": "INFO", "affected_activity_id": target[0],
                "provenance": "SIMULATED",
                "payload": {"degraded_providers": ["ord0432-positive-control"]}},
                timeout=60)
            out["2B_control_event_http"] = ctrl.status_code
            out["2B_control_event_id"] = (ctrl.json() or {}).get("id")
            p = envelope_of(c)
            out["2B_after_control_event"] = p
            # the MAJOR row is still unresolved underneath, so the flip is the key's doing
            out["W4_control_robust_flipped_false"] = (p["robust"] is False)
            out["W5_control_risk_codes_named"] = (list(p["risk_reason_codes"] or []) == ["PROVIDER_DEGRADED"])

            conn = sqlite3.connect(db)
            out["3_event_rows_unresolved"] = conn.execute(
                "select id, event_type, severity, status from events where journey_id=? "
                "and status in ('DETECTED','ACKNOWLEDGED') order by detected_at", (JID,)).fetchall()
            conn.close()

            # secondary control, different door: tear the budget to 1 minor.  Record the body.
            patched = c.patch(f"/api/v1/journeys/{JID}", json={"budget": {"amount_minor": 1, "currency": "CNY"}})
            out["4_budget_patch_http"] = patched.status_code
            out["4_budget_patch_body"] = patched.text[:400]
    finally:
        srv.terminate()
        try:
            srv.wait(timeout=20)
        except Exception:
            srv.kill()

    out["VERDICT_envelope_blind_to_events"] = bool(
        out.get("W1_major_event_visible_in_twin") and out.get("W2_robust_still_true")
        and out.get("W3_risk_codes_still_empty") and out.get("W4_control_robust_flipped_false")
        and out.get("W5_control_risk_codes_named"))
    path = LANE / f"ORD0432_WITNESS_{PORT}.json"
    path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8", newline="\n")
    print(json.dumps({k: out[k] for k in sorted(out)
                      if k.startswith(("W", "VERDICT", "1_", "2_", "3_", "4_"))},
                     ensure_ascii=False, indent=1)[:2600])
    print("WROTE", path)
    return 0 if out["VERDICT_envelope_blind_to_events"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
