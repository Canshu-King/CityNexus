"""shape_probe.py — what shape does the product hand the MCP adapter, on each tree?

Boots one tree's backend, seeds it, builds an ACTIVE plan, fires one CLOSURE event, then
reads the SAME replan twice: (a) straight over HTTP from the agent endpoint, and (b) through
the MCP adapter. Comparing the two on the same body shows whether the adapter is validating
a full proposal or a four-field summary.

usage: PROBE_TREE=D:\\moodle\\... python shape_probe.py
"""
import json
import os
import sqlite3
import subprocess
import time
import uuid
from pathlib import Path

import httpx

LANE = Path(r"D:\moodle\CityNexus-Hermes-Revival\evidence\0212")
CAND = Path(os.environ["PROBE_TREE"])
PY = Path(r"D:\moodle\CityNexus\.venv\Scripts\python.exe")
PORT = int(os.environ.get("PROBE_PORT", "8521"))
BASE = f"http://127.0.0.1:{PORT}"
JID = "22222222-2222-4222-8222-222222222222"
db = LANE / f"_shapeprobe_{Path(str(CAND)).name}.db"
for s in ("", "-wal", "-shm"):
    Path(str(db) + s).unlink(missing_ok=True)

subprocess.run([str(PY), str(LANE / "seed_lane_db.py")], check=True, capture_output=True, text=True,
               env={**os.environ, "CITYNEXUS_DATABASE_URL": "sqlite:///" + str(db).replace("\\", "/"),
                    "LANE_BACKEND_ROOT": str(CAND / "backend")})
srv = subprocess.Popen([str(PY), "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(PORT)],
                       cwd=str(CAND / "backend"),
                       env={**os.environ, "PYTHONPATH": ".",
                            "CITYNEXUS_DATABASE_URL": "sqlite:///" + str(db).replace("\\", "/")},
                       stdout=open(LANE / f"_shapeprobe_{Path(str(CAND)).name}.log", "w", encoding="utf-8"),
                       stderr=subprocess.STDOUT)
for _ in range(60):
    try:
        if httpx.get(BASE + "/api/v1/health", timeout=2).status_code == 200:
            break
    except Exception:
        pass
    time.sleep(1)

plan = httpx.post(f"{BASE}/api/v1/journeys/{JID}/plans/generate", json={}, timeout=180)
pid = plan.json()[0]["id"]
httpx.post(f"{BASE}/api/v1/journeys/{JID}/plans/{pid}/select", timeout=60)
httpx.post(f"{BASE}/api/v1/journeys/{JID}/start", timeout=60)
c = sqlite3.connect(db)
tgt = [r[0] for r in c.execute("select a.id from activities a join plan_versions p on a.plan_version_id=p.id "
                               "where p.status='ACTIVE' and a.title like '%Tech Art%'").fetchall()]
c.close()
ev = httpx.post(f"{BASE}/api/v1/journeys/{JID}/events",
                json={"event_type": "CLOSURE", "severity": "MAJOR", "affected_activity_id": tgt[0],
                      "provenance": "SIMULATED", "payload": {"reason": "shape probe"}}, timeout=60).json()
eid = ev.get("id") or ev.get("event", {}).get("id")

body = {"request_id": str(uuid.uuid4()), "agent_id": "shape-probe", "journey_id": JID,
        "trigger_event_id": eid, "candidate_count": 3}
r = httpx.post(f"{BASE}/api/v1/agent/tools/request_replan", json=body, timeout=180)
print("TREE:", CAND)
print("HTTP request_replan ->", r.status_code)
o = r.json()
print("  top keys:", sorted(o.keys()))
if isinstance(o.get("proposal"), dict):
    print("  proposal keys(%d):" % len(o["proposal"]), sorted(o["proposal"].keys()))
if isinstance(o.get("proposals"), list) and o["proposals"]:
    print("  proposals[0] keys(%d):" % len(o["proposals"][0]), sorted(o["proposals"][0].keys()))

mcp = subprocess.Popen([str(PY), "-m", "citynexus_mcp.server", "--v2"],
                       stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                       cwd=str(CAND / "agent-mcp"), text=True, bufsize=1,
                       env={**os.environ, "PYTHONPATH": str(CAND / "agent-mcp"),
                            "CITYNEXUS_API_BASE_URL": BASE})


def send(x):
    mcp.stdin.write(json.dumps(x) + "\n"); mcp.stdin.flush()


def rid(w):
    while True:
        line = mcp.stdout.readline()
        if not line:
            return {}
        line = line.strip()
        if not line:
            continue
        try:
            m = json.loads(line)
        except json.JSONDecodeError:
            print("  mcp stderr/non-json:", line[:150])
            continue
        if m.get("id") == w:
            return m


send({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2024-11-05",
      "capabilities": {}, "clientInfo": {"name": "sp", "version": "1"}}})
rid(1)
send({"jsonrpc": "2.0", "method": "notifications/initialized"})
send({"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {"name": "request_replan", "arguments": {
    "request_id": str(uuid.uuid4()), "journey_id": JID, "trigger_event_id": eid, "candidate_count": 3}}})
res = rid(2)
txt = (res.get("result", {}).get("content") or [{}])[0].get("text", "")
print("MCP request_replan -> isError:", res.get("result", {}).get("isError"))
print("  head:", txt[:200].replace("\n", " "))
mcp.stdin.close(); mcp.terminate(); srv.terminate()
