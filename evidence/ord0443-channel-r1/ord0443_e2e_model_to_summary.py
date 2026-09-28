"""ORD-0443 x ORD-0432: a model-parsed disruption all the way into the summary field.

One lane boot with the gateway channel wired. The traveller's sentence goes in through the product's
own copilot door; what comes back is read from the durable side - the event row the product created
and the twin's `feasibility_envelope` - because ORD-0432 is exactly the claim that an unresolved
MAJOR has to show up there. Bodies are stored redacted and truncated; the credential never appears.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
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
SHIM = "http://127.0.0.1:7864/v1/responses"
OUT = LANE / "ORD0443_E2E_MODEL_TO_SUMMARY.json"
SENTENCE = "The Nexus River Cruise venue is closed this afternoon, what should I do next?"


def redact(node, depth=0):
    secret_key = re.compile(r"key|token|secret|cookie|password|authorization|credential", re.I)
    if depth > 6:
        return "…depth…"
    if isinstance(node, dict):
        return {k: ("MASKED(len=%d)" % len(str(v))) if secret_key.search(str(k)) else redact(v, depth + 1)
                for k, v in node.items()}
    if isinstance(node, list):
        return [redact(v, depth + 1) for v in node[:8]]
    if isinstance(node, str):
        return node[:220]
    return node


def free_port() -> int:
    import socket
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def main() -> int:
    token = str(json.loads(CFG.read_text(encoding="utf-8")).get("api_key") or "")
    db = LANE / "_e2e.db"
    for suffix in ("", "-wal", "-shm"):
        Path(str(db) + suffix).unlink(missing_ok=True)
    subprocess.run([str(PY), str(SEED)], check=True, capture_output=True, text=True,
                   env={**os.environ, "CITYNEXUS_DATABASE_URL": "sqlite:///" + db.as_posix(),
                        "LANE_BACKEND_ROOT": str(TREE / "backend")})
    port = free_port()
    env = {**os.environ, "PYTHONPATH": ".", "CITYNEXUS_DATABASE_URL": "sqlite:///" + db.as_posix(),
           "CITYNEXUS_DEMO_MODE": "true", "CITYNEXUS_AI_ENABLED": "true",
           "CITYNEXUS_AI_PROVIDER": "deepseek", "CITYNEXUS_AI_MODEL": "global:glm-5.2",
           "CITYNEXUS_AI_API_KEY": token, "DEEPSEEK_API_KEY": token,
           "CITYNEXUS_DEEPSEEK_API_URL": SHIM}
    srv = subprocess.Popen([str(PY), "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1",
                            "--port", str(port)], cwd=str(TREE / "backend"), env=env,
                           stdout=(LANE / "_e2e_backend.log").open("w", encoding="utf-8"),
                           stderr=subprocess.STDOUT)
    report: dict = {"port": port, "db": str(db), "sentence": SENTENCE}
    try:
        with httpx.Client(base_url=f"http://127.0.0.1:{port}", timeout=180, trust_env=False) as c:
            for _ in range(90):
                try:
                    if c.get("/api/v1/health", timeout=4).status_code == 200:
                        break
                except Exception:
                    pass
                time.sleep(1)
            report["health_ai"] = redact(c.get("/api/v1/health").json())
            gen = c.post(f"/api/v1/journeys/{JID}/plans/generate", json={})
            if gen.status_code == 201 and gen.json():
                c.post(f"/api/v1/journeys/{JID}/plans/{gen.json()[0]['id']}/select")
                c.post(f"/api/v1/journeys/{JID}/start")
            before = c.get(f"/api/v1/journeys/{JID}/twin").json()["context"]["feasibility_envelope"]
            report["envelope_before"] = {"robust": before["robust"],
                                         "risk_reason_codes": before["risk_reason_codes"]}
            started = time.perf_counter()
            cmd = c.post(f"/api/v1/journeys/{JID}/agent/commands", json={"command": SENTENCE},
                         headers={"Idempotency-Key": "ord0443-e2e-1"})
            report["copilot"] = {"http": cmd.status_code, "bytes": len(cmd.content),
                                 "elapsed_s": round(time.perf_counter() - started, 2),
                                 "body_sha1": hashlib.sha1(cmd.content).hexdigest()[:16],
                                 "body": redact(cmd.json()) if cmd.status_code < 500 else None}
            events = c.get(f"/api/v1/journeys/{JID}/events").json()
            report["events_after"] = [{"event_type": e.get("event_type"), "severity": e.get("severity"),
                                       "status": e.get("status"), "provenance": e.get("provenance"),
                                       "affected_activity_id": bool(e.get("affected_activity_id"))}
                                      for e in events]
            after = c.get(f"/api/v1/journeys/{JID}/twin").json()["context"]["feasibility_envelope"]
            report["envelope_after"] = {"robust": after["robust"],
                                        "risk_reason_codes": after["risk_reason_codes"],
                                        "budget_remaining_minor": after["budget_remaining_minor"],
                                        "journey_end_slack_min": after["journey_end_slack_min"]}
    finally:
        srv.terminate()
        try:
            srv.wait(timeout=25)
        except Exception:
            srv.kill()

    opened = [e for e in report.get("events_after", []) if e["status"] in ("DETECTED", "ACKNOWLEDGED")]
    report["verdict_model_to_summary"] = bool(
        report["copilot"]["http"] == 200 and opened
        and report["envelope_after"]["risk_reason_codes"]
        and report["envelope_after"]["robust"] is not True)
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8", newline="\n")
    print(json.dumps({k: report[k] for k in ("health_ai", "copilot", "events_after",
                                             "envelope_before", "envelope_after",
                                             "verdict_model_to_summary")},
                     ensure_ascii=False, indent=1)[:2600])
    print("WROTE", OUT)
    return 0 if report["verdict_model_to_summary"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
