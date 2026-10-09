"""CMDR private stack at the current tip (walkthrough of the modules landed today).

Same five-step recipe as _cmdr_stack_0418_r1.py, re-pointed:
  export  D:/moodle/_qoder_cmdr_tipnow        (git archive of the tip I am walking)
  db      fresh read-only backup of the shared preview DB -> my private file
  api     :8738   ui :4824 (the ui is started separately once the build is done)
No provider key is injected: the chat route on the local gateway is still unverified, and an
AI call with a key and no verified route would hang these probes.
"""
import io
import json
import os
import sqlite3
import subprocess
import time
import urllib.request

EXPORT = "D:/moodle/_qoder_cmdr_tipnow"
SHARED_SRC = "D:/moodle/_qoder_preview_20260920/_preview.db"
PRIV_DB = "D:/moodle/_qoder_cmdr_priv_tip.db"
VENV_PY = "D:/moodle/CityNexus/.venv/Scripts/python.exe"
API_PORT = 8738
LOG_DIR = "D:/moodle/_qoder_cmdr_ref_20260921/live_checks/_stack_tip"
DETACHED = 0x00000008 | 0x00000200
os.makedirs(LOG_DIR, exist_ok=True)
out = {}

if not os.path.exists(PRIV_DB):
    src = sqlite3.connect("file:%s?mode=ro" % SHARED_SRC.replace("\\", "/"), uri=True)
    dst = sqlite3.connect(PRIV_DB)
    src.backup(dst)
    dst.close()
    src.close()
out["priv_db_bytes"] = os.path.getsize(PRIV_DB)

env = dict(os.environ)
env.pop("HTTP_PROXY", None)
env.pop("HTTPS_PROXY", None)
env["CITYNEXUS_DATABASE_URL"] = "sqlite:///%s" % PRIV_DB.replace("\\", "/")
env["CITYNEXUS_DEMO_MODE"] = "true"
env["PYTHONPATH"] = EXPORT + "/backend" + os.pathsep + EXPORT

log = io.open(LOG_DIR + "/api.log", "w", encoding="utf-8", newline="\n")
api = subprocess.Popen([VENV_PY, "-m", "uvicorn", "backend.app.main:app", "--host", "127.0.0.1",
                        "--port", str(API_PORT)], stdout=log, stderr=subprocess.STDOUT,
                       cwd=EXPORT + "/backend", env=env, creationflags=DETACHED)
out["spawned_pid_api"] = str(api.pid)

ok = None
deadline = time.time() + 120
while time.time() < deadline:
    try:
        r = urllib.request.urlopen("http://127.0.0.1:%d/api/v1/journeys" % API_PORT, timeout=5)
        ok = (r.status, len(r.read()))
        break
    except Exception:
        time.sleep(3)
out["api_probe"] = ok

ns = subprocess.run(["netstat", "-ano", "-p", "TCP"], capture_output=True, text=True, errors="replace").stdout
owner = ""
for line in ns.splitlines():
    cols = line.split()
    if len(cols) >= 5 and cols[0].upper() == "TCP" and cols[3].upper() == "LISTENING" \
            and cols[1].endswith(":%d" % API_PORT):
        owner = cols[4]
out["netstat_pid_api"] = owner
out["pid_matches_netstat"] = owner == str(api.pid)

# which new routes are actually live on this backend?
probes = {}
for path in ("/api/v1/share/grants", "/api/v1/collections", "/api/v1/journeys/22222222-2222-4222-8222-222222222222/access",
             "/api/v1/pending-places", "/openapi.json"):
    try:
        r = urllib.request.urlopen("http://127.0.0.1:%d%s" % (API_PORT, path), timeout=8)
        body = r.read()
        probes[path] = (r.status, len(body))
    except Exception as exc:
        code = getattr(exc, "code", None)
        probes[path] = ("ERR", type(exc).__name__, code)
out["route_probes"] = probes
try:
    spec = json.loads(urllib.request.urlopen("http://127.0.0.1:%d/openapi.json" % API_PORT, timeout=10).read())
    paths = sorted(spec.get("paths", {}).keys())
    out["openapi_path_count"] = len(paths)
    out["new_paths"] = [p for p in paths if any(k in p for k in ("share", "collection", "access", "pending", "recycle", "undelete"))]
except Exception as exc:
    out["openapi_read"] = "NOT_READ_%s" % type(exc).__name__

print(json.dumps(out, ensure_ascii=False, indent=1))
