"""CMDR private stack, generalized r1.

Same five-step recipe as _cmdr_stack_tip_r1.py, but parameterised so a fresh tip does not
require a new file (the old ones hardcoded one export dir and one port each).

  argv[1] = export dir (git archive of the tip I am walking; must contain backend/)
  argv[2] = api port (int; my own range, never 8000/4781/4782/8693)
  argv[3] = tag for the log/db names

Proofs collected here: api_probe, netstat owner == my spawned pid, and the openapi path
inventory. The UI identity proof (served entry name == my own index.html, served bytes sha1
== disk bytes sha1) is collected after cmdr_static_api_proxy_r1.py is up.

No provider key is injected: the AI route on the local gateway is unverified, and a key with an
unverified route would hang these probes.
"""
import io
import json
import os
import sqlite3
import subprocess
import sys
import time
import urllib.request

EXPORT = sys.argv[1].rstrip("/")
API_PORT = int(sys.argv[2])
TAG = sys.argv[3] if len(sys.argv) > 3 else "gen"
SHARED_SRC = "D:/moodle/_qoder_preview_20260920/_preview.db"
PRIV_DB = "D:/moodle/_qoder_cmdr_priv_%s.db" % TAG
VENV_PY = "D:/moodle/CityNexus/.venv/Scripts/python.exe"
LOG_DIR = "D:/moodle/_qoder_cmdr_ref_20260921/live_checks/_stack_%s" % TAG
DETACHED = 0x00000008 | 0x00000200
os.makedirs(LOG_DIR, exist_ok=True)
out = {"export": EXPORT, "api_port": API_PORT, "tag": TAG}

if not os.path.exists(PRIV_DB):
    # read-only open of the shared preview DB, copied into my own file; nothing writes to the shared one
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
deadline = time.time() + 150
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

try:
    spec = json.loads(urllib.request.urlopen("http://127.0.0.1:%d/openapi.json" % API_PORT, timeout=15).read())
    paths = sorted(spec.get("paths", {}).keys())
    out["openapi_path_count"] = len(paths)
    out["capability_paths"] = [p for p in paths if any(
        k in p for k in ("share", "collection", "access", "pending", "recycle", "undelete",
                         "import", "estimat", "member", "acl"))]
except Exception as exc:
    out["openapi_read"] = "NOT_READ_%s" % type(exc).__name__

io.open(LOG_DIR + "/stack_proofs.json", "w", encoding="utf-8", newline="\n").write(
    json.dumps(out, ensure_ascii=False, indent=1))
print(json.dumps(out, ensure_ascii=False, indent=1))
