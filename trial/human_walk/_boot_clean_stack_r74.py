"""Boot the clean-generation stack on :60362 / :14462 from the E-worktree, for #339.

Nothing here touches the working tree the other arms use: the code comes from
`E:/_cmdr_clean_1028` (tip read back below, zero dirty files), the database is a brand-new empty
file, and the Amap credential is inherited from the process environment only -- it is never
printed and never written.
"""
import io
import json
import os
import re
import secrets
import subprocess
import time
import urllib.request

ROOT = r"E:/_cmdr_clean_1028"
DATA = r"E:/_cmdr_clean_1028_data"
PORT = int(os.environ.get("CLEAN_BACKEND_PORT", "60362"))
DB = os.path.join(DATA, "citynexus_v3_clean_1028.db")
LOG = os.path.join(DATA, "clean_backend.log")
SHIM = r"C:/Users/仓鼠王/WorkBuddy/2026-09-15-15-47-27/wb2api/codex-shim/shim.mjs"
GATEWAY = "http://127.0.0.1:7863/v1/chat/completions"
MODEL = os.environ.get("HUMAN_MODEL", "cn:hy3")
PY = r"D:/moodle/CityNexus/.venv/Scripts/python.exe"


def sh(text: str) -> str:
    # The box reads subprocess output as GBK by default and git prints the CJK path -- that made
    # this instrument report an empty tip and then blame the worktree for being dirty.
    return subprocess.run(
        ["bash", "-lc", text], capture_output=True, text=True, timeout=120,
        encoding="utf-8", errors="replace",
    ).stdout.strip()


def listening(port: int) -> set[int]:
    pids = set()
    for line in subprocess.run(["netstat", "-ano", "-p", "tcp"], capture_output=True, text=True, timeout=60).stdout.splitlines():
        parts = line.split()
        if len(parts) >= 5 and parts[3] == "LISTENING" and parts[1].endswith(":%d" % port) and parts[4].isdigit():
            pids.add(int(parts[4]))
    return pids


os.makedirs(DATA, exist_ok=True)
tip = os.environ.get("CLEAN_TIP", "").strip() or sh("git -C %s rev-parse HEAD" % ROOT)
dirty = os.environ.get("CLEAN_DIRTY", "").strip() or sh("git -C %s status --porcelain=v1 | wc -l" % ROOT)
print("WORKTREE_TIP", tip)
print("WORKTREE_DIRTY_LINES", dirty)
if len(tip) != 40:
    raise SystemExit("ABORT: cannot read the worktree tip (instrument failure, not a dirty tree)")
if dirty != "0":
    raise SystemExit("ABORT: the clean worktree is not clean -- #339 needs a tree nobody is editing")

key = None
match = re.search(r"WB2API_KEY \|\| '([^']+)'", io.open(SHIM, encoding="utf-8").read())
if match:
    key = match.group(1)
amap_present = bool(os.environ.get("CITYNEXUS_AMAP_WEB_KEY"))
print("AMAP_KEY_INHERITED", amap_present, "gateway_key_found", bool(key))
if not amap_present:
    raise SystemExit("ABORT: no Amap key in the environment -- the live walk cannot start honest")

if listening(PORT):
    raise SystemExit("ABORT: port %d already owned by someone else" % PORT)

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

handle = io.open(LOG, "ab")
child = subprocess.Popen(
    [PY, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(PORT)],
    cwd=os.path.join(ROOT, "backend"), env=env, stdout=handle, stderr=subprocess.STDOUT,
    creationflags=0x00000008 | 0x00000200,
)
print("BACKEND_PID", child.pid, "new_database", os.path.exists(DB))
ok = "no"
for _ in range(140):
    try:
        with urllib.request.urlopen("http://127.0.0.1:%d/api/v1/health" % PORT, timeout=3) as response:
            if response.status == 200:
                ok = json.loads(response.read().decode("utf-8")).get("status", "unknown")
                break
    except Exception:
        time.sleep(1.0)
print("HEALTH", ok)
