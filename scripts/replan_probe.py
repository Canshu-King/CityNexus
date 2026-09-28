"""replan_probe.py — is the empty replan product-side or model-side?

Seeds a fresh lane DB, builds the ACTIVE plan, creates a CLOSURE event, then calls
`request_replan` over MCP directly (no model in the loop) and prints what came back.
"""
import json
import os
import sqlite3
import subprocess
import sys
import time
import uuid
from pathlib import Path

LANE = Path(r"D:\moodle\CityNexus-Hermes-Revival\evidence\0212")
CAND = Path(os.environ.get("PROBE_TREE", r"D:\moodle\_qoder_dsh_listreplans_20260929\wt"))
PY = Path(r"D:\moodle\CityNexus\.venv\Scripts\python.exe")
PORT = 8517
BASE = f"http://127.0.0.1:{PORT}"
JID = "22222222-2222-4222-8222-222222222222"
db = LANE / "_replanprobe.db"
for s in ("", "-wal", "-shm"):
    Path(str(db) + s).unlink(missing_ok=True)

env = {**os.environ, "CITYNEXUS_DATABASE_URL": "sqlite:///" + str(db).replace("\\", "/"),
       "LANE_BACKEND_ROOT": str(CAND / "backend")}
subprocess.run([str(PY), str(LANE / "seed_lane_db.py")], env=env, check=True,
               capture_output=True, text=True)

benv = {**os.environ, "PYTHONPATH": ".", "CITYNEXUS_DATABASE_URL": "sqlite:///" + str(db).replace("\\", "/")}
srv = subprocess.Popen([str(PY), "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(PORT)],
                       cwd=str(CAND / "backend"), env=benv,
                       stdout=open(LANE / "_replanprobe_backend.log", "w", encoding="utf-8"),
                       stderr=subprocess.STDOUT)
import httpx
for _ in range(60):
    try:
        if httpx.get(BASE + "/api/v1/health", timeout=2).status_code == 200:
            break
    except Exception:
        pass
    time.sleep(1)

# build_active_plan.py hardcodes :8513, so drive the same calls here against our port.
# The lane builder does NOT call demo/reset: the seeded journey is already there, and it
# generates with an empty body.
plan = httpx.post(f"{BASE}/api/v1/journeys/{JID}/plans/generate", json={}, timeout=180)
print("generate ->", plan.status_code, "candidates:", len(plan.json()) if plan.status_code == 201 else plan.text[:120])
if plan.status_code == 201:
    pid = plan.json()[0]["id"]
    print("select ->", httpx.post(f"{BASE}/api/v1/journeys/{JID}/plans/{pid}/select", timeout=60).status_code)
    print("start  ->", httpx.post(f"{BASE}/api/v1/journeys/{JID}/start", timeout=60).status_code)

c = sqlite3.connect(db)
acts = [r[0] for r in c.execute("select a.id from activities a join plan_versions p on a.plan_version_id=p.id "
                                "where p.status='ACTIVE' order by a.start_at").fetchall()]
titles = {r[0]: r[1] for r in c.execute("select a.id, a.title from activities a join plan_versions p "
                                         "on a.plan_version_id=p.id where p.status='ACTIVE'").fetchall()}
c.close()
print("ACTIVE activities:", len(acts))

mcp = subprocess.Popen([str(PY), "-m", "citynexus_mcp.server", "--v2"],
                       stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                       cwd=str(CAND / "agent-mcp"), text=True, bufsize=1,
                       env={**os.environ, "PYTHONPATH": str(CAND / "agent-mcp"),
                            "CITYNEXUS_API_BASE_URL": BASE})


def send(o):
    mcp.stdin.write(json.dumps(o) + "\n"); mcp.stdin.flush()


def rid(w):
    while True:
        line = mcp.stdout.readline()
        if not line:
            return {}
        try:
            m = json.loads(line)
        except json.JSONDecodeError:
            continue
        if m.get("id") == w:
            return m


send({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2024-11-05",
      "capabilities": {}, "clientInfo": {"name": "rp", "version": "1"}}})
rid(1)
send({"jsonrpc": "2.0", "method": "notifications/initialized"})

# One CLOSURE per activity, oldest to newest: which trigger shapes actually yield a
# proposal, and which surface a malformed-proposal error instead of a decision.
ok = []
for idx, act in enumerate(acts):
    ev = httpx.post(f"{BASE}/api/v1/journeys/{JID}/events",
                    json={"event_type": "CLOSURE", "severity": "MAJOR", "affected_activity_id": act,
                          "payload": {"reason": "probe"}, "provenance": "SIMULATED"},
                    timeout=60)
    eid = ev.json().get("id") or ev.json().get("event", {}).get("id")
    send({"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {"name": "request_replan", "arguments": {
        "request_id": str(uuid.uuid4()), "journey_id": JID, "trigger_event_id": eid, "candidate_count": 3}}})
    r = rid(2)
    txt = (r.get("result", {}).get("content") or [{}])[0].get("text", "")
    try:
        o = json.loads(txt)
        prop = o.get("proposal") or {}
        line = f"[{idx}] {titles.get(act, act)[:26]:28s} decision={o.get('decision')} proposal_id={str(prop.get('id'))[:8]} status={prop.get('status')} score={prop.get('utility_score')}"
        if prop.get("id"):
            ok.append((eid, act, titles.get(act, "")))
    except Exception:
        line = f"[{idx}] {titles.get(act, act)[:26]:28s} TOOL_ERROR: {txt[:110]}"
    print(line)

print("usable_triggers:", json.dumps([{"event": e, "activity_title": t} for e, a, t in ok]))
mcp.stdin.close(); mcp.terminate(); srv.terminate()
