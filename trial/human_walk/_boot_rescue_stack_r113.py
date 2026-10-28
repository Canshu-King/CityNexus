"""Boot a second canary stack from THIS rescue tree, so the new refusal sentence can be seen on a real screen.

Why a second stack instead of restarting :60362: the live clean stack's backend carries the traveller-auth
secret that was generated when it booted (trial/human_walk/_boot_clean_stack_r74.py:71 -- a fresh random
secret per boot), so restarting it invalidates every bearer in every browser profile, and the journeys that
already show the refused shape belong to travellers that a cold browser cannot list (that is #332, measured
twice: journey 3d9715f7 is in the DB, yet a reopened browser's trips tab shows CARDS 0).

This boots a brand-new empty database, a backend from D:/moodle/_cmdr_rescue_v3_1022/backend on
CLEAN_BACKEND_PORT (default 60363) and a vite on CLEAN_WEB_PORT (default 14463) pointing at it, exactly the
way the first stack was booted.  Nothing is seeded: the traveller's journey, draft and refusal must all come
from a real walk.  The Amap credential is inherited from the process environment only -- never printed,
never written to a file -- and the script refuses to start without it.

Usage: python _boot_rescue_stack_r113.py          # boot
       python _boot_rescue_stack_r113.py --check   # read health of both ports, start nothing
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

ROOT = os.environ.get("RESCUE_ROOT", r"D:/moodle/_cmdr_rescue_v3_1022").replace("\\", "/")
DATA = os.environ.get("RESCUE_DATA", r"E:/_cmdr_rescue_113_data")
BACKEND_PORT = int(os.environ.get("CLEAN_BACKEND_PORT", "60363"))
WEB_PORT = int(os.environ.get("CLEAN_WEB_PORT", "14463"))
DB = os.path.join(DATA, "citynexus_v3_rescue_113.db")
BLOG = os.path.join(DATA, "rescue_backend.log")
VLOG = os.path.join(DATA, "rescue_vite.log")
SHIM = r"C:/Users/仓鼠王/WorkBuddy/2026-09-15-15-47-27/wb2api/codex-shim/shim.mjs"
GATEWAY = "http://127.0.0.1:7863/v1/chat/completions"
MODEL = os.environ.get("HUMAN_MODEL", "cn:hy3")
PY = r"D:/moodle/CityNexus/.venv/Scripts/python.exe"
NODE = r"node"
VITE = os.path.join(ROOT, "frontend", "node_modules", "vite", "bin", "vite.js")


def listening(port: int) -> set:
    pids = set()
    for line in subprocess.run(["netstat", "-ano", "-p", "tcp"], capture_output=True, text=True,
                               timeout=60, encoding="utf-8", errors="replace").stdout.splitlines():
        parts = line.split()
        if len(parts) >= 5 and parts[3] == "LISTENING" and parts[1].endswith(":" + str(port)) and parts[4].isdigit():
            pids.add(int(parts[4]))
    return pids


def health(port: int) -> str:
    try:
        with urllib.request.urlopen("http://127.0.0.1:%d/api/v1/health" % port, timeout=3) as response:
            if response.status == 200:
                return json.loads(response.read().decode("utf-8")).get("status", "unknown")
    except Exception as error:  # noqa: BLE001 - a health probe that throws still answers the question
        return "unreachable " + type(error).__name__
    return "no status"


if "--check" in sys.argv:
    print("BACKEND_%d_HEALTH" % BACKEND_PORT, health(BACKEND_PORT), "listeners", sorted(listening(BACKEND_PORT)))
    print("WEB_%d" % WEB_PORT, "listeners", sorted(listening(WEB_PORT)))
    raise SystemExit(0)

os.makedirs(DATA, exist_ok=True)
tip = subprocess.run(["git", "-C", ROOT, "rev-parse", "HEAD"], capture_output=True, text=True,
                     timeout=60).stdout.strip()
print("TREE_TIP", tip)
if len(tip) != 40:
    raise SystemExit("ABORT: cannot read the tree tip -- instrument failure, not a clean answer")

key = None
match = re.search(r"WB2API_KEY \|\| '([^']+)'", io.open(SHIM, encoding="utf-8").read())
if match:
    key = match.group(1)
amap_present = bool(os.environ.get("CITYNEXUS_AMAP_WEB_KEY"))
print("AMAP_KEY_INHERITED", amap_present, "gateway_key_found", bool(key))
if not amap_present:
    raise SystemExit("ABORT: no Amap key in the environment -- a live walk cannot start honest")
for port, name in ((BACKEND_PORT, "backend"), (WEB_PORT, "vite")):
    if listening(port):
        raise SystemExit("ABORT: port %d (%s) already owned by %s" % (port, name, sorted(listening(port))))

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
    "CITYNEXUS_DEEPSEEK_API_URL": "http://127.0.0.1:7864/v1/responses",
    "CITYNEXUS_DEEPSEEK_REASONING_EFFORT": "low",
    "CITYNEXUS_DEEPSEEK_WEB_SEARCH": "false",
    "CITYNEXUS_HERMES_API_URL": GATEWAY,
    "CITYNEXUS_HERMES_MODEL": MODEL,
    "PYTHONPATH": os.path.join(ROOT, "backend"),
    "PYTHONIOENCODING": "utf-8",
})
if key:
    env["CITYNEXUS_AI_API_KEY"] = key
    env["CITYNEXUS_HERMES_API_KEY"] = key

blog = io.open(BLOG, "ab")
backend = subprocess.Popen(
    [PY, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(BACKEND_PORT)],
    cwd=os.path.join(ROOT, "backend"), env=env, stdout=blog, stderr=subprocess.STDOUT,
    creationflags=0x00000008 | 0x00000200,
)
ok = "no"
for _ in range(140):
    ok = health(BACKEND_PORT)
    if ok not in ("no status",) and not str(ok).startswith("unreachable"):
        break
    time.sleep(1.0)
print("BACKEND_PID", backend.pid, "HEALTH", ok, "new_database", os.path.exists(DB))

vout = io.open(VLOG, "ab")
web_env = dict(env)
web_env["CITYNEXUS_BACKEND_PORT"] = str(BACKEND_PORT)
vite = subprocess.Popen(
    [NODE, VITE, "--host", "127.0.0.1", "--port", str(WEB_PORT), "--strictPort"],
    cwd=os.path.join(ROOT, "frontend"), env=web_env, stdout=vout, stderr=subprocess.STDOUT,
    creationflags=0x00000008 | 0x00000200,
)
served = "no"
for _ in range(60):
    try:
        with urllib.request.urlopen("http://127.0.0.1:%d/revolution" % WEB_PORT, timeout=3) as response:
            served = response.status
            break
    except Exception:
        time.sleep(1.0)
print("VITE_PID", vite.pid, "SERVED", served, "BASE http://127.0.0.1:%d" % WEB_PORT)
