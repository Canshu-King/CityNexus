"""Build an isolated classroom stack whose run is genuinely stuck at
PAUSED_MODEL_UNAVAILABLE, so the console's "再请一次守护" button can be pressed
against a real backend instead of a mocked screen.

What is real here:
- a byte copy of the classroom database (sqlite backup, WAL included)
- the real backend and the real frontend, on 60400 / 14495
- the button's click calls the real POST /runs/{id}/guardian

What is injected (and disclosed):
- one extra CLOSURE event is copied into the copy, and the run's pending_event_id
  points at it, so the previous guardian attempt no longer matches this scene
- the run status is set to PAUSED_MODEL_UNAVAILABLE and the old proposal is
  withdrawn. This is failure setup, not fabricated success.

Nothing here touches the classroom database or its ports.
"""
import io
import json
import os
import re
import secrets
import shutil
import socket
import sqlite3
import subprocess
import sys
import time
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timezone

ROOT = r"D:/moodle/_cmdr_rescue_v3_1022"
BACKEND = os.path.join(ROOT, "backend")
FRONTEND = os.path.join(ROOT, "frontend")
OUT = r"D:/moodle/_cmdr_v3_port_1022"
LIVE = r"D:/moodle/_cmdr_v3_live_1022"
SRC = os.path.join(LIVE, "citynexus_v3_demo_1025.db")
DST = os.path.join(LIVE, "citynexus_v3_guardian_retry_1026.db")
PORT = 60400
WEB = 14495
PY = r"D:/moodle/CityNexus/.venv/Scripts/python.exe"
SHIM = r"C:/Users/仓鼠王/WorkBuddy/2026-09-15-15-47-27/wb2api/codex-shim/shim.mjs"
SECRET = secrets.token_hex(32)
PRESENTER_KEY = secrets.token_hex(24)
MODEL = "cn:hy3"
JOURNEY = "2e9cd67d-10ca-4ecd-920b-76c81a350c71"
TRAVELER = "9ac3c100-da78-4933-ba1b-cb79991fcb1e"


def gateway_key():
    match = re.search(r"WB2API_KEY \|\| '([^']+)'", io.open(SHIM, encoding="utf-8").read())
    if not match:
        raise SystemExit("no gateway key")
    return match.group(1)


def listens(port):
    for host in ("127.0.0.1", "::1"):
        probe = socket.socket(socket.AF_INET6 if ":" in host else socket.AF_INET)
        probe.settimeout(0.4)
        try:
            probe.connect((host, port))
            return True
        except OSError:
            continue
        finally:
            probe.close()
    return False


def call(method, path, body=None, token=None, key=None, timeout=60):
    data = json.dumps(body).encode() if body is not None else None
    request = urllib.request.Request("http://127.0.0.1:%d%s" % (PORT, path), data=data, method=method)
    if data is not None:
        request.add_header("Content-Type", "application/json")
    if token:
        request.add_header("Authorization", "Bearer " + token)
    if key:
        request.add_header("X-CityNexus-Presenter-Key", key)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as answer:
            raw = answer.read().decode("utf-8")
            return answer.status, (json.loads(raw) if raw else {})
    except urllib.error.HTTPError as error:
        raw = error.read().decode("utf-8")
        try:
            return error.code, (json.loads(raw) if raw else {})
        except ValueError:
            return error.code, {"raw": raw[:300]}


def copy_database():
    if os.path.exists(DST):
        os.remove(DST)
    source = sqlite3.connect(SRC)
    target = sqlite3.connect(DST)
    with target:
        source.backup(target)
    source.close()
    target.close()


def inject_stuck_state():
    db = sqlite3.connect(DST)
    db.row_factory = sqlite3.Row
    with db:
        original = db.execute(
            "select * from events where journey_id=? order by rowid desc limit 1", (JOURNEY,)
        ).fetchone()
        if original is None:
            raise SystemExit("no event to copy")
        new_id = str(uuid.uuid4())
        columns = [row[1] for row in db.execute("pragma table_info(events)")]
        values = []
        for column in columns:
            values.append(new_id if column == "id" else original[column])
        db.execute(
            "insert into events (%s) values (%s)"
            % (",".join(columns), ",".join("?" for _ in columns)),
            values,
        )
        run = db.execute(
            "select id, sequence, state_json, history_json from simulation_runs where journey_id=? order by rowid desc limit 1",
            (JOURNEY,),
        ).fetchone()
        if run is None:
            raise SystemExit("no run to point at the new event")
        state = json.loads(run["state_json"])
        state["pending_event_id"] = new_id
        history = json.loads(run["history_json"])
        template = next(
            (step for step in history if step.get("event") == "SIM_SCENE_INJECTED"), None
        )
        if template is None:
            raise SystemExit("no scene history to copy")
        injected = dict(template)
        injected["event_id"] = new_id
        injected["scene_id"] = "%s-retry108" % template.get("scene_id", "scene")
        injected["recorded_at"] = datetime.now(timezone.utc).isoformat()
        injected["sequence"] = int(run["sequence"] or 2) + 1
        history.append(injected)
        db.execute(
            "update simulation_runs set status='PAUSED_MODEL_UNAVAILABLE', state_json=?, history_json=? where id=?",
            (json.dumps(state), json.dumps(history), run["id"]),
        )
        db.execute(
            "update guardian_runs set proposal_id=NULL, action_status='UNRESOLVED' where journey_id=?",
            (JOURNEY,),
        )
        db.execute(
            "update replan_proposals set status='INVALIDATED' where journey_id=?",
            (JOURNEY,),
        )
    db.close()
    return {"event": new_id, "run": run["id"]}


def start_backend():
    env = dict(os.environ)
    env.update(
        {
            "CITYNEXUS_DATABASE_URL": "sqlite:///" + DST.replace("\\", "/"),
            "CITYNEXUS_TRAVELER_AUTH_SECRET": SECRET,
            "CITYNEXUS_TRAVELER_AUTH_TTL_SECONDS": "43200",
            "CITYNEXUS_DEMO_MODE": "true",
            "CITYNEXUS_DEMO_RESET_TOKEN": SECRET[:16],
            "CITYNEXUS_DEMO_PRESENTER_KEY": PRESENTER_KEY,
            "CITYNEXUS_DEMO_DATABASE_PATH": DST,
            "CITYNEXUS_SIMULATION_ENABLED": "true",
            "CITYNEXUS_AI_ENABLED": "true",
            "CITYNEXUS_AI_PROVIDER": "deepseek",
            "CITYNEXUS_AI_MODEL": MODEL,
            "CITYNEXUS_AI_API_KEY": gateway_key(),
            "CITYNEXUS_DEEPSEEK_API_URL": "http://127.0.0.1:7864/v1/responses",
            "CITYNEXUS_DEEPSEEK_REASONING_EFFORT": "low",
            "CITYNEXUS_DEEPSEEK_WEB_SEARCH": "false",
            "PYTHONIOENCODING": "utf-8",
        }
    )
    subprocess.Popen(
        [PY, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(PORT)],
        cwd=BACKEND,
        env=env,
        stdout=open(os.path.join(OUT, "uvicorn_guardian_retry_108.log"), "wb"),
        stderr=subprocess.STDOUT,
    )


def start_frontend():
    env = dict(os.environ)
    env["CITYNEXUS_BACKEND_PORT"] = str(PORT)
    subprocess.Popen(
        ["npm.cmd", "run", "dev", "--", "--port", str(WEB), "--strictPort"],
        cwd=FRONTEND,
        env=env,
        stdout=open(os.path.join(OUT, "vite_guardian_retry_108.log"), "wb"),
        stderr=subprocess.STDOUT,
    )


def wait_port(port, seconds):
    for _ in range(seconds * 4):
        if listens(port):
            return True
        time.sleep(0.25)
    return False


def port_pid(port):
    probe = subprocess.run(["netstat", "-ano"], capture_output=True, text=True, errors="replace")
    for line in probe.stdout.splitlines():
        fields = line.split()
        if len(fields) >= 5 and fields[0].upper() == "TCP" and fields[1].endswith(":%d" % port) \
                and fields[3].upper() == "LISTENING":
            return fields[4]
    return None


def release_port(port):
    pid = port_pid(port)
    if pid:
        subprocess.run(["taskkill", "/PID", pid, "/F"], capture_output=True)
        for _ in range(20):
            if not listens(port):
                return
            time.sleep(0.25)


def main():
    release_port(PORT)
    release_port(WEB)
    copy_database()
    injected = inject_stuck_state()
    start_backend()
    if not wait_port(PORT, 40):
        raise SystemExit("backend did not listen")
    os.environ["CITYNEXUS_TRAVELER_AUTH_SECRET"] = SECRET
    sys.path.insert(0, BACKEND)
    from app.traveler_principal import issue_traveler_token

    token = issue_traveler_token(TRAVELER, ttl_seconds=43200)
    deadline = time.time() + 20
    while True:
        try:
            status, _ = call("GET", "/openapi.json")
            if status == 200:
                break
        except Exception:
            pass
        if time.time() > deadline:
            raise SystemExit("backend openapi not ready")
        time.sleep(0.4)
    status, answer = call(
        "POST", "/api/v1/demo/pairing", {"journey_id": JOURNEY}, token=token, key=PRESENTER_KEY
    )
    if status not in (200, 201) or not answer.get("ticket"):
        raise SystemExit("pairing failed: %s %s" % (status, json.dumps(answer)[:200]))
    ticket = answer["ticket"]
    with io.open(os.path.join(LIVE, ".demo_pairing_ticket_108.json"), "w", encoding="utf-8") as handle:
        json.dump({"ticket": ticket, "journey_id": JOURNEY}, handle)
    start_frontend()
    if not wait_port(WEB, 60):
        raise SystemExit("frontend did not listen")
    print(json.dumps({
        "STACK": "ISOLATED_60400_14495",
        "INJECTED_EVENT": injected["event"],
        "RUN": injected["run"],
        "PORT": PORT, "WEB": WEB, "TICKET_LEN": len(ticket), "READY": True,
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
