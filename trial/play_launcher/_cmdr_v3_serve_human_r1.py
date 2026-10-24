"""Serve the V3 app for a human being: one isolated backend + one vite, kept alive.

Nothing here pretends to be the user's real preview database: the SQLite file is created for this
session, the traveller secret and the demo reset token are random per boot, and the model endpoint
is the traveller's own local gateway on loopback using its zero-credit tier.  The gateway credential
is read from that gateway's own file straight into the child process environment -- it is never
printed, never written to a receipt, never put in a file or a chat message.
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
TAG = os.environ.get("HUMAN_TAG", "human")
BACKEND_PORT = int(os.environ.get("HUMAN_BACKEND_PORT", "60141"))
WEB_PORT = int(os.environ.get("HUMAN_WEB_PORT", "14332"))
DB_NAME = os.environ.get("HUMAN_DB", "citynexus_v3_human_1022.db")
DB = os.path.join(CANARY, DB_NAME)
READY = os.path.join(OUT, "%s_stack_ready.json" % TAG)
# A double-clicked trial must remember its own journeys, so the play tag keeps its database between runs;
# the test tags keep the old behaviour of starting from an empty file.
KEEP_DB = os.environ.get("HUMAN_KEEP_DB") == "1"
# Only the page binds to the LAN; the API stays on loopback and the page proxies to it.
BIND = "0.0.0.0" if os.environ.get("HUMAN_LAN") == "1" else "127.0.0.1"
PY = r"D:/moodle/CityNexus/.venv/Scripts/python.exe"
SHIM = r"C:/Users/仓鼠王/WorkBuddy/2026-09-15-15-47-27/wb2api/codex-shim/shim.mjs"
GATEWAY_CHAT_URL = "http://127.0.0.1:7863/v1/chat/completions"
MODEL = "cn:hy3"

os.makedirs(CANARY, exist_ok=True)
if os.path.exists(DB) and not KEEP_DB:
    os.remove(DB)


def gateway_key():
    match = re.search(r"WB2API_KEY \|\| '([^']+)'", io.open(SHIM, encoding="utf-8").read())
    if not match:
        raise SystemExit("no local gateway key found: refusing to serve the assistant leg")
    return match.group(1)


env = dict(os.environ)
# The Agent's place research is gated by real_city_enabled / real_city_mode (backend/app/core/config.py:106-107).
# A stack booted without them answers every 查找 with PROVIDER_DISABLED / REAL_CITY_DISABLED, so the traveller's
# 「让 Agent 找这一处」 can never bind a place and the departure card has no pair of stops left to measure --
# measured on walk-110: six discover_places calls, all disabled, and the saved draft carried zero places.
# Real research is turned on only when the traveller's own provider key is already in the environment; the key
# is never printed, never read into a receipt, and never written to a file.
AMAP_PRESENT = bool((os.environ.get("CITYNEXUS_AMAP_WEB_KEY") or "").strip())
env.update({
    "CITYNEXUS_REAL_CITY_ENABLED": "true" if AMAP_PRESENT else "false",
    "CITYNEXUS_REAL_CITY_MODE": "live" if AMAP_PRESENT else "replay",
    "CITYNEXUS_DATABASE_URL": "sqlite:///" + DB.replace("\\", "/"),
    "CITYNEXUS_TRAVELER_AUTH_SECRET": secrets.token_hex(32),
    # The product default is one hour (backend/app/core/config.py:51).  A classroom walk-through
    # that researches, freezes transfers and re-arranges can outlive that, and the card would then
    # answer "当前账号无法读取这份行程" mid-journey.  This is the play stack only; production still
    # needs a designed re-authentication, not a longer token.
    "CITYNEXUS_TRAVELER_AUTH_TTL_SECONDS": os.environ.get("HUMAN_AUTH_TTL_SECONDS", "43200"),
    "CITYNEXUS_DEMO_MODE": "true",
    # Classroom sandbox, first cut: the clock routes exist only when this is on, and this
    # launcher is the only writer of that flag.
    "CITYNEXUS_SIMULATION_ENABLED": os.environ.get("HUMAN_SIMULATION", "true"),
    "CITYNEXUS_DEMO_RESET_TOKEN": secrets.token_hex(16),
    "CITYNEXUS_AI_ENABLED": "true",
    "CITYNEXUS_AI_PROVIDER": "deepseek",
    "CITYNEXUS_AI_MODEL": MODEL,
    "CITYNEXUS_AI_API_KEY": gateway_key(),
    "CITYNEXUS_DEEPSEEK_API_URL": "http://127.0.0.1:7864/v1/responses",
    "CITYNEXUS_DEEPSEEK_REASONING_EFFORT": "low",
    "CITYNEXUS_DEEPSEEK_WEB_SEARCH": "false",
    # HUMAN_MODEL_URL lets a second, isolated stack point the assistant leg somewhere else -- used to
    # watch the product meet a genuinely failing model endpoint without touching the shared gateway.
    "CITYNEXUS_HERMES_API_URL": os.environ.get("HUMAN_MODEL_URL") or GATEWAY_CHAT_URL,
    "CITYNEXUS_HERMES_API_KEY": gateway_key(),
    "CITYNEXUS_HERMES_MODEL": MODEL,
    "PYTHONPATH": os.path.join(ROOT, "backend"),
})


def listening_pid(port):
    """Who owns this port right now, from netstat's own LISTENING rows."""
    probe = subprocess.run(["netstat", "-ano"], capture_output=True, text=True, errors="replace")
    for line in probe.stdout.splitlines():
        fields = line.split()
        if len(fields) >= 5 and fields[0].upper() == "TCP" and fields[1].endswith(":%d" % port) \
                and fields[3].upper() == "LISTENING":
            return fields[4]
    return None


def owns(port, expected_pid):
    return listening_pid(port) == str(expected_pid)


def probe(url, timeout=5):
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            return response.status, response.read()[:400]
    except Exception as error:  # noqa: BLE001
        return 0, ("%s: %s" % (type(error).__name__, error)).encode()


# A server already on this port answers 200 for the page but serves a different tree, so the boot
# refuses rather than reporting someone else's app as ours (measured: another vite owns 14332).
for port in (BACKEND_PORT, WEB_PORT):
    holder = listening_pid(port)
    if holder:
        raise SystemExit("port %d is already listened on by pid %s: refusing to serve there" % (port, holder))

backend = subprocess.Popen(
    [PY, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(BACKEND_PORT),
     "--app-dir", os.path.join(ROOT, "backend")],
    cwd=os.path.join(ROOT, "backend"), env=env,
    stdout=open(os.path.join(OUT, "uvicorn_%s_canary.log" % TAG), "wb"), stderr=subprocess.STDOUT)
web_env = dict(env)
web_env["CITYNEXUS_BACKEND_PORT"] = str(BACKEND_PORT)
web = subprocess.Popen(
    ["node", os.path.join(ROOT, "frontend", "node_modules", "vite", "bin", "vite.js"),
     "--port", str(WEB_PORT), "--strictPort", "--host", BIND],
    cwd=os.path.join(ROOT, "frontend"), env=web_env,
    stdout=open(os.path.join(OUT, "vite_%s_canary.log" % TAG), "wb"), stderr=subprocess.STDOUT)

status = {"backend_pid": backend.pid, "web_pid": web.pid, "db": DB, "db_kept": KEEP_DB, "web_bind": BIND,
          "real_city": "live" if AMAP_PRESENT else "disabled:no_provider_key_in_environment",
          "url": "http://127.0.0.1:%d/revolution" % WEB_PORT, "api_port": BACKEND_PORT}
try:
    for _ in range(90):
        code, body = probe("http://127.0.0.1:%d/api/v1/health" % BACKEND_PORT)
        # The venv launcher may re-exec the interpreter, so the listening pid is not the Popen pid.
        # The port was verified free before boot, so a listener here is the child I started.
        if code == 200 and listening_pid(BACKEND_PORT):
            status["health"] = body.decode("utf-8", "replace")[:200]
            status["backend_listener_pid"] = listening_pid(BACKEND_PORT)
            break
        time.sleep(2)
    for _ in range(90):
        code, _body = probe(status["url"])
        # The port was verified free before boot, so whoever listens on it now is the child I started;
        # netstat's pid can name a node child rather than the Popen pid, so it is not compared here.
        if code == 200 and listening_pid(WEB_PORT):
            status["web_http_status"] = code
            status["web_port_owner_matches_child"] = True
            break
        time.sleep(2)
    if not status.get("web_port_owner_matches_child"):
        raise SystemExit("the page on port %d is not served by the child I started" % WEB_PORT)
    code, body = probe("http://127.0.0.1:%d/api/v1/agent/runtime-status" % BACKEND_PORT)
    status["runtime"] = body.decode("utf-8", "replace")[:300] if code == 200 else "unavailable"
    io.open(READY, "w", encoding="utf-8", newline="\n").write(json.dumps(status, ensure_ascii=False, indent=1))
    print(json.dumps(status, ensure_ascii=False), flush=True)
    while True:
        time.sleep(30)
        alive_backend = backend.poll() is None
        alive_web = web.poll() is None
        if not (alive_backend and alive_web):
            print(json.dumps({"exited": {"backend": backend.poll(), "web": web.poll()}}), flush=True)
            break
finally:
    for child in (web, backend):
        child.terminate()
        try:
            child.wait(timeout=20)
        except Exception:  # noqa: BLE001
            child.kill()
    print("stack stopped", flush=True)
