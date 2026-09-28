"""ORD-0443 end to end, and ORD-0432's field read through a real model.

Chain: patched shim (own OS-assigned port) <- product lane backend with the channel wired <- the
traveller's sentence sent through `POST /api/v1/journeys/{id}/agent/commands`. The durable read after
that is the event row the product created and the twin's `feasibility_envelope`, which is ORD-0432's
own claim: an unresolved MAJOR has to show up there.

The one knob this needs is time: `backend/app/agent/runtime.py:282` gives the agent's model client
`settings.impact_timeout_seconds` (default ten seconds), and a real answer measured 1.7-66.6 s, so
the run is repeated with `CITYNEXUS_IMPACT_TIMEOUT_SECONDS` raised. That is a measurement of the
borrowed-knob defect, not a product change: no product byte is edited here.

Credential: read from the gateway's config at runtime, passed only into child environments.
"""
from __future__ import annotations

import json
import os
import socket
import subprocess
import time
from pathlib import Path

import httpx

CFG = Path(r"C:\Users\仓鼠王\WorkBuddy\2026-09-15-15-47-27\wb2api\config.json")
LANE = Path(r"D:\moodle\CityNexus-Hermes-Revival\evidence\0443")
TREE = Path(r"D:\moodle\_qoder_ai_ord0432_20260929\wt")
SEED = Path(r"D:\moodle\CityNexus-Hermes-Revival\evidence\0212\seed_lane_db.py")
PY = Path(r"D:\moodle\CityNexus\.venv\Scripts\python.exe")
JID = "22222222-2222-4222-8222-222222222222"
SENTENCE = "The Nexus River Cruise venue is closed this afternoon, mark it as a major disruption and tell me what to do next."
MODEL = "global:glm-5.2"
OUT = LANE / "ORD0443_E2E_PATCHED.json"


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def run_case(token: str, impact_timeout: str) -> dict:
    shim_port = free_port()
    shim = subprocess.Popen(["node", str(LANE / "shim_patch" / "shim_r2.mjs")],
                            env={**os.environ, "WB2API_SHIM_PORT": str(shim_port),
                                 "WB2API_UPSTREAM": "http://127.0.0.1:7863/v1", "WB2API_KEY": token},
                            cwd=str(LANE / "shim_patch"),
                            stdout=(LANE / f"_shim_{impact_timeout}.log").open("w", encoding="utf-8"),
                            stderr=subprocess.STDOUT)
    db = LANE / f"_e2e_{impact_timeout}.db"
    for suffix in ("", "-wal", "-shm"):
        Path(str(db) + suffix).unlink(missing_ok=True)
    subprocess.run([str(PY), str(SEED)], check=True, capture_output=True, text=True,
                   env={**os.environ, "CITYNEXUS_DATABASE_URL": "sqlite:///" + db.as_posix(),
                        "LANE_BACKEND_ROOT": str(TREE / "backend")})
    lane_port = free_port()
    env = {**os.environ, "PYTHONPATH": ".", "CITYNEXUS_DATABASE_URL": "sqlite:///" + db.as_posix(),
           "CITYNEXUS_DEMO_MODE": "true", "CITYNEXUS_AI_ENABLED": "true",
           "CITYNEXUS_AI_PROVIDER": "deepseek", "CITYNEXUS_AI_MODEL": MODEL,
           "CITYNEXUS_AI_API_KEY": token, "DEEPSEEK_API_KEY": token,
           "CITYNEXUS_DEEPSEEK_API_URL": f"http://127.0.0.1:{shim_port}/v1/responses",
           "CITYNEXUS_IMPACT_TIMEOUT_SECONDS": impact_timeout}
    srv = subprocess.Popen([str(PY), "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1",
                            "--port", str(lane_port)], cwd=str(TREE / "backend"), env=env,
                           stdout=(LANE / f"_lane_{impact_timeout}.log").open("w", encoding="utf-8"),
                           stderr=subprocess.STDOUT)
    out: dict = {"impact_timeout_seconds": impact_timeout, "shim_port": shim_port,
                 "lane_port": lane_port, "db": str(db)}
    try:
        time.sleep(2)
        with httpx.Client(base_url=f"http://127.0.0.1:{lane_port}", timeout=240, trust_env=False) as c:
            for _ in range(120):
                try:
                    if c.get("/api/v1/health", timeout=4).status_code == 200:
                        break
                except Exception:
                    pass
                time.sleep(1)
            out["health"] = c.get("/api/v1/health").json()
            gen = c.post(f"/api/v1/journeys/{JID}/plans/generate", json={})
            if gen.status_code == 201 and gen.json():
                c.post(f"/api/v1/journeys/{JID}/plans/{gen.json()[0]['id']}/select")
                c.post(f"/api/v1/journeys/{JID}/start")
            before = c.get(f"/api/v1/journeys/{JID}/twin").json()["context"]["feasibility_envelope"]
            out["envelope_before"] = {"robust": before["robust"],
                                      "risk_reason_codes": before["risk_reason_codes"]}
            started = time.perf_counter()
            cmd = c.post(f"/api/v1/journeys/{JID}/agent/commands", json={"command": SENTENCE},
                         headers={"Idempotency-Key": f"ord0443-e2e-{impact_timeout}"})
            body = cmd.json() if cmd.status_code < 500 else {}
            mission = body.get("mission") or {}
            out["copilot"] = {"http": cmd.status_code, "bytes": len(cmd.content),
                              "elapsed_s": round(time.perf_counter() - started, 2),
                              "mission_status": mission.get("status"),
                              "failure_reason": mission.get("failure_reason"),
                              "ai_state": mission.get("ai_state"),
                              "assistant_text_head": str(mission.get("assistant_text")
                                                          or mission.get("summary") or "")[:160],
                              "steps": [str(step.get("tool_name") or step.get("operation"))[:34]
                                        for step in (mission.get("mission_plan") or {}).get("steps", [])][:8]}
            events = c.get(f"/api/v1/journeys/{JID}/events").json()
            out["events_after"] = [{"event_type": e.get("event_type"), "severity": e.get("severity"),
                                    "status": e.get("status"), "provenance": e.get("provenance"),
                                    "affected_activity": bool(e.get("affected_activity_id"))}
                                   for e in events]
            after = c.get(f"/api/v1/journeys/{JID}/twin").json()["context"]["feasibility_envelope"]
            out["envelope_after"] = {"robust": after["robust"],
                                     "risk_reason_codes": after["risk_reason_codes"]}
    finally:
        for proc in (srv, shim):
            proc.terminate()
            try:
                proc.wait(timeout=25)
            except Exception:
                proc.kill()
    out["verdict_this_case"] = bool(out["envelope_after"]["risk_reason_codes"]
                                    and out["envelope_after"]["robust"] is False)
    return out


def main() -> int:
    token = str(json.loads(CFG.read_text(encoding="utf-8")).get("api_key") or "")
    cases = [run_case(token, bad) for bad in ("10", "180")]
    report = {"model": MODEL, "sentence": SENTENCE, "key_length": len(token),
              "key_written_to_any_file": False, "cases": cases,
              "verdict_timeout_knob_is_the_blocker": bool(
                  not cases[0]["verdict_this_case"] and cases[1]["verdict_this_case"])}
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8", newline="\n")
    for c in cases:
        print("impact_timeout", c["impact_timeout_seconds"], "->", json.dumps(
            {k: c[k] for k in ("copilot", "events_after", "envelope_after", "verdict_this_case")},
            ensure_ascii=False)[:700])
    print("WROTE", OUT)
    return 0 if report["verdict_timeout_knob_is_the_blocker"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
