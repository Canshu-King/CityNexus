"""Boot the classroom generation (88b891d22c) from a zero-dirty worktree on D, on a brand-new database.

E ran down to 0.13 GiB, and the launcher this arm used to share hard-codes E paths for both the tree and
the database - so this is the same boot with two changes and one new door:

  * ROOT/DATA point at D:/_cmdr_clean_1030 and its data directory, which is a fresh git worktree detached
    at the classroom tip, nothing more;
  * DATA must have more than FLOOR_GIB free before anything is written, and the measured number is printed
    rather than assumed - a stack that dies half-written is worse than one that never started;
  * the Amap credential is inherited from the process environment and is only ever reported as a boolean.

Nothing here resets or reuses an existing database, and nothing is written under D:/moodle.
"""

import io
import json
import os
import re
import secrets
import shutil
import socket
import subprocess
import sys
import time
import urllib.request

ROOT = os.environ.get("STACK_ROOT", r"D:/_cmdr_clean_1030")
DATA = os.environ.get("STACK_DATA", r"D:/_cmdr_clean_1030_data")
NODE_MODULES_DONOR = r"D:/moodle/CityNexus/frontend/node_modules"
PY = r"D:/moodle/CityNexus/.venv/Scripts/python.exe"
PORT = int(os.environ.get("CLEAN_BACKEND_PORT", "60362"))
DB = os.path.join(DATA, "citynexus_v3_clean_1030.db")
LOG = os.path.join(DATA, "clean_backend.log")
SHIM = r"C:/Users/仓鼠王/WorkBuddy/2026-09-15-15-47-27/wb2api/codex-shim/shim.mjs"
GATEWAY = "http://127.0.0.1:7863/v1/chat/completions"
MODEL = os.environ.get("HUMAN_MODEL", "cn:hy3")
FLOOR_GIB = 1.0
EXPECTED_TIP = "88b891d22c"


def sh(text):
    """Read subprocess output as UTF-8: git prints CJK paths and the default GBK read returns nothing.

    bash -lc turns out to answer an empty string for this path on this box, so the two facts this boot
    gates on are read by calling git directly and the raw return code is kept visible.
    """
    argv = ["git", "-C", ROOT] + text
    done = subprocess.run(argv, capture_output=True, text=True, timeout=120,
                          encoding="utf-8", errors="replace")
    if done.returncode != 0:
        print("GIT_FAIL rc=%d %s -> %s" % (done.returncode, " ".join(argv), done.stderr.strip()[:200]))
    return done.stdout.strip()


def listening(port):
    probe = socket.socket()
    probe.settimeout(0.5)
    return probe.connect_ex(("127.0.0.1", port)) == 0


def junction(target, link):
    """A Windows junction, created through _winapi so bash cannot mangle the path or the /J flag."""
    if os.path.isdir(link):
        return "already_present"
    import _winapi
    _winapi.CreateJunction(target, link)
    return "created"


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if not os.path.isdir(ROOT):
        raise SystemExit("ABORT no worktree at %s" % ROOT)
    tip = os.environ.get("STACK_TIP", "").strip() or sh(["rev-parse", "HEAD"])
    dirty = str(len([cell for cell in sh(["status", "--porcelain=v1"]).split("\n") if cell.strip()]))
    print("WORKTREE %s tip=%s dirty_lines=%s" % (ROOT, tip[:12] if len(tip) == 40 else repr(tip), dirty))
    if len(tip) != 40:
        raise SystemExit("ABORT cannot read the worktree tip - instrument failure, not a clean tree")
    if not tip.startswith(EXPECTED_TIP):
        raise SystemExit("ABORT the worktree reads %s, not the classroom generation %s"
                         % (tip[:12], EXPECTED_TIP))
    if dirty != "0":
        raise SystemExit("ABORT the tree is not zero-dirty, so a screen reading from it is not the "
                         "generation the ledger cites")

    os.makedirs(DATA, exist_ok=True)
    free = shutil.disk_usage(DATA).free / 1024 ** 3
    print("DISK_FREE_AT_DATA %.2f GiB (floor %.1f)" % (free, FLOOR_GIB))
    if free < FLOOR_GIB:
        raise SystemExit("ABORT only %.2f GiB free at %s, under the %.1f GiB this boot needs before it "
                         "writes a database" % (free, DATA, FLOOR_GIB))
    if os.path.exists(DB):
        raise SystemExit("ABORT %s already exists - this arm boots a brand-new database only" % DB)

    link = os.path.join(ROOT, "frontend", "node_modules")
    print("NODE_MODULES %s -> %s : %s" % (link, NODE_MODULES_DONOR,
                                          junction(NODE_MODULES_DONOR.replace("/", "\\"),
                                                   link.replace("/", "\\"))))

    amap = bool(os.environ.get("CITYNEXUS_AMAP_WEB_KEY"))
    print("AMAP_KEY_INHERITED", amap)
    if not amap:
        raise SystemExit("ABORT no Amap key in the environment - the live walk cannot start honest")
    if listening(PORT):
        raise SystemExit("ABORT port %d is already owned by someone else" % PORT)

    key = None
    if os.path.exists(SHIM):
        match = re.search(r"WB2API_KEY \|\| '([^']+)'", io.open(SHIM, encoding="utf-8").read())
        if match:
            key = match.group(1)
    print("GATEWAY_KEY_FOUND", bool(key))

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
    child = subprocess.Popen([PY, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1",
                              "--port", str(PORT)], cwd=os.path.join(ROOT, "backend"), env=env,
                             stdout=handle, stderr=subprocess.STDOUT,
                             creationflags=0x00000008 | 0x00000200)
    print("BACKEND_PID", child.pid)
    status = "no"
    for _ in range(140):
        try:
            with urllib.request.urlopen("http://127.0.0.1:%d/api/v1/health" % PORT, timeout=3) as response:
                if response.status == 200:
                    status = json.loads(response.read().decode("utf-8")).get("status", "unknown")
                    break
        except Exception:
            time.sleep(1.0)
    print("HEALTH", status)
    if status == "no":
        tail = io.open(LOG, encoding="utf-8", errors="replace").read().split("\n")[-12:]
        print("LOG_TAIL %s" % " | ".join(cell.strip() for cell in tail if cell.strip()))
        return 7
    print("DB_BYTES", os.path.getsize(DB), "DATA_FREE_AFTER %.2f GiB"
          % (shutil.disk_usage(DATA).free / 1024 ** 3))
    return 0


if __name__ == "__main__":
    sys.exit(main())
