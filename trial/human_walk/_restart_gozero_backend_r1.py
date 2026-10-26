"""Restart only the gozero backend on :60361 so edited code is loaded.

The stack launcher deletes its database on boot, so it is not used here: this script keeps the
existing SQLite file and the browser-facing vite untouched, and rebuilds the same process
environment the launcher used. The gateway credential is read from the local shim into the child
environment; it is never printed or written anywhere.
"""
import io
import json
import os
import re
import secrets
import subprocess
import sys
import time
import urllib.request

ROOT = r"D:/moodle/_cmdr_rescue_v3_1022"
OUT = r"D:/moodle/_cmdr_v3_port_1022"
CANARY = r"D:/moodle/_cmdr_v3_live_1022"
PORT = int(os.environ.get("HUMAN_BACKEND_PORT", "60361"))
DB_NAME = os.environ.get("HUMAN_DB", "citynexus_v3_gozero_1026.db")
DB = os.path.join(CANARY, DB_NAME)
LOG = os.path.join(OUT, "gozero_backend_restart.log")
SHIM = r"C:/Users/仓鼠王/WorkBuddy/2026-09-15-15-47-27/wb2api/codex-shim/shim.mjs"
GATEWAY_CHAT_URL = "http://127.0.0.1:7863/v1/chat/completions"
MODEL = os.environ.get("HUMAN_MODEL", "cn:hy3")
PY = r"D:/moodle/CityNexus/.venv/Scripts/python.exe"


def gateway_key() -> str:
    match = re.search(r"WB2API_KEY \|\| '([^']+)'", io.open(SHIM, encoding="utf-8").read())
    if not match:
        raise SystemExit("gateway key not found in shim; refusing to restart the backend")
    return match.group(1)


def listening_pids(port: int) -> set[int]:
    answer = subprocess.run(
        ["netstat", "-ano", "-p", "tcp"], capture_output=True, text=True, timeout=30
    ).stdout
    pids = set()
    for line in answer.splitlines():
        parts = line.split()
        if len(parts) >= 5 and parts[3] == "LISTENING" and parts[1].endswith(":%d" % port):
            if parts[4].isdigit():
                pids.add(int(parts[4]))
    return pids


def stop(pids: set[int]) -> None:
    for pid in sorted(pids):
        subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], capture_output=True, timeout=30)


def healthy() -> tuple[bool, str]:
    try:
        with urllib.request.urlopen(
            "http://127.0.0.1:%d/api/v1/health" % PORT, timeout=3
        ) as response:
            return response.status == 200, "http_status=%d" % response.status
    except Exception as error:
        return False, type(error).__name__


if not os.path.exists(DB):
    raise SystemExit("database missing: refusing to boot on an empty file")

stale = listening_pids(PORT)
print("LISTENERS", sorted(stale))
if stale:
    stop(stale)
    for _ in range(20):
        if not listening_pids(PORT):
            break
        time.sleep(0.5)
    print("STOPPED", not listening_pids(PORT))

env = dict(os.environ)
env.update({
    "CITYNEXUS_DATABASE_URL": "sqlite:///" + DB.replace("\\", "/"),
    "CITYNEXUS_TRAVELER_AUTH_SECRET": secrets.token_hex(32),
    "CITYNEXUS_DEMO_MODE": "true",
    "CITYNEXUS_REAL_CITY_ENABLED": "true",
    "CITYNEXUS_REAL_CITY_MODE": "live",
    "CITYNEXUS_DEMO_DATABASE_PATH": DB,
    "CITYNEXUS_DEMO_RESET_TOKEN": secrets.token_hex(16),
    "CITYNEXUS_AI_ENABLED": "true",
    "CITYNEXUS_AI_PROVIDER": "deepseek",
    "CITYNEXUS_AI_MODEL": MODEL,
    "CITYNEXUS_AI_API_KEY": gateway_key(),
    "CITYNEXUS_DEEPSEEK_API_URL": "http://127.0.0.1:7864/v1/responses",
    "CITYNEXUS_DEEPSEEK_REASONING_EFFORT": "low",
    "CITYNEXUS_DEEPSEEK_WEB_SEARCH": "false",
    "CITYNEXUS_HERMES_API_URL": GATEWAY_CHAT_URL,
    "CITYNEXUS_HERMES_API_KEY": gateway_key(),
    "CITYNEXUS_HERMES_MODEL": MODEL,
    "PYTHONPATH": os.path.join(ROOT, "backend"),
    "PYTHONIOENCODING": "utf-8",
})

handle = io.open(LOG, "ab")
child = subprocess.Popen(
    [PY, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(PORT)],
    cwd=os.path.join(ROOT, "backend"), env=env, stdout=handle, stderr=subprocess.STDOUT,
    creationflags=0x00000008 | 0x00000200,
)
print("STARTED", child.pid)

for _ in range(120):
    ok, detail = healthy()
    if ok:
        print("HEALTH", detail, "pid", child.pid)
        break
    time.sleep(0.5)
else:
    print("HEALTH_FAILED last", detail)
