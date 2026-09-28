"""ORD-0432, the leg a traveller never sees: does the agent surface carry the new word?

Re-opens the screen lane's sqlite (the run wrote a MAJOR CLOSURE through POST /events) and answers
the same journey through `POST /api/v1/agent/tools/inspect_twin`. The tool payload travels in
`content[].text`, so that is what gets parsed - not a field I hope exists.
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
TREE = Path(r"D:\moodle\_qoder_ai_ord0432_20260929\wt")
PY = Path(r"D:\moodle\CityNexus\.venv\Scripts\python.exe")
JID = "22222222-2222-4222-8222-222222222222"
OUT = LANE / "ORD0432_AGENT_LEG.json"


def free_port() -> int:
    import socket
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def main() -> int:
    port = int(os.environ.get("ORD0432_AGENT_PORT") or free_port())
    db = sorted(LANE.glob("_ord0432_screen_*.db"), key=lambda p: p.stat().st_mtime)[-1]
    report: dict = {"reused_db": str(db), "port": port}
    conn = sqlite3.connect(db)
    report["db_event_rows"] = conn.execute(
        "select id, event_type, severity, status from events where journey_id=?", (JID,)).fetchall()
    conn.close()
    srv = subprocess.Popen([str(PY), "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1",
                            "--port", str(port)], cwd=str(TREE / "backend"),
                            env={**os.environ, "PYTHONPATH": ".", "CITYNEXUS_DEMO_MODE": "true",
                                 "CITYNEXUS_DATABASE_URL": "sqlite:///" + str(db).replace("\\", "/")},
                            stdout=(LANE / "_agent_leg_backend.log").open("w", encoding="utf-8"),
                            stderr=subprocess.STDOUT)
    try:
        with httpx.Client(base_url=f"http://127.0.0.1:{port}", timeout=90, trust_env=False) as c:
            for _ in range(90):
                try:
                    if c.get("/api/v1/health").status_code == 200:
                        break
                except Exception:
                    pass
                time.sleep(1)
            http_twin = c.get(f"/api/v1/journeys/{JID}/twin").json()
            env_block = http_twin["context"]["feasibility_envelope"]
            report["http_twin"] = {"robust": env_block["robust"],
                                   "risk_reason_codes": env_block["risk_reason_codes"]}
            call = c.post("/api/v1/agent/tools/inspect_twin", json={
                "request_id": "ord0432-agent-leg", "journey_id": JID})
            report["agent_http"] = call.status_code
            body = call.json() if call.status_code < 500 else {}
            report["agent_top_keys"] = sorted(body.keys())[:10] if isinstance(body, dict) else None
            # Two shapes answer this door: the gateway's own object (top keys are recorded above)
            # and the MCP adapter's `content[].text`. Read whichever actually arrived.
            text = None
            for item in (body.get("content") or []) if isinstance(body, dict) else []:
                if isinstance(item, dict) and item.get("type") == "text":
                    text = item.get("text")
                    break
            report["agent_content_text_found"] = text is not None
            inner = json.loads(text) if text else body
            if isinstance(inner, dict) and inner.get("twin"):
                twin = inner["twin"]
                agent_env = (twin.get("context") or {}).get("feasibility_envelope") or {}
                report["agent_twin"] = {"robust": agent_env.get("robust"),
                                        "risk_reason_codes": agent_env.get("risk_reason_codes"),
                                        "latest_event_id": twin.get("latest_event_id")}
    finally:
        srv.terminate()
        try:
            srv.wait(timeout=20)
        except Exception:
            srv.kill()

    report["verdict_agent_sees_the_disruption"] = bool(
        report.get("agent_twin", {}).get("robust") is False
        and "DISRUPTION_MAJOR" in (report.get("agent_twin", {}).get("risk_reason_codes") or []))
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8", newline="\n")
    print(json.dumps(report, ensure_ascii=False, indent=1)[:1600])
    print("WROTE", OUT)
    return 0 if report["verdict_agent_sees_the_disruption"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
