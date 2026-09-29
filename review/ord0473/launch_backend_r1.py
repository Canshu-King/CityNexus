"""ORD-0473 lane N4 private stack: backend at :8745 on my own DB copy, launched detached.

Recipe copied from _cmdr_stack_tip_r1.py (the commander's five-step stack): read-only backup of the
shared preview DB into a private file, git-archive export as PYTHONPATH, and ownership proved by
netstat pid == spawned pid.
"""
import io
import json
import os
import sqlite3
import subprocess
import sys
import time
import urllib.request

REPO = "D:/moodle/CityNexus"
SHA = sys.argv[1]
EXPORT = "D:/moodle/_qoder_n4_ord0473_20260930/export"
SHARED_SRC = "D:/moodle/_qoder_preview_20260920/_preview.db"
PRIV_DB = "D:/moodle/_qoder_n4_ord0473_20260930/n4_ord0473.db"
VENV_PY = "D:/moodle/CityNexus/.venv/Scripts/python.exe"
API_PORT = 8745
LOG_DIR = "D:/moodle/_qoder_n4_ord0473_20260930/run"
DETACHED = 0x00000008 | 0x00000200
os.makedirs(LOG_DIR, exist_ok=True)
out = {"sha": SHA, "api_port": API_PORT}

# the export must carry the tip's bytes or the stack proves nothing about the line
for rel in ["backend/app/main.py", "backend/app/agent/ai_availability.py"]:
    want = subprocess.run(["git", "-C", REPO, "rev-parse", "%s:%s" % (SHA, rel)],
                          capture_output=True, text=True).stdout.strip()
    path = os.path.join(EXPORT, rel.replace("/", os.sep))
    have = ""
    if os.path.isfile(path):
        have = subprocess.run(["git", "-C", REPO, "hash-object", "--no-filters",
                               path.replace("/", "\\")], capture_output=True, text=True).stdout.strip()
    out.setdefault("export_blob_equality", {})[rel] = {
        "tip_blob": want or None, "export_blob": have or None, "identical": bool(want) and want == have}

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
deadline = time.time() + 150
while time.time() < deadline:
    try:
        r = urllib.request.urlopen("http://127.0.0.1:%d/api/v1/journeys" % API_PORT, timeout=5)
        ok = {"status": r.status, "bytes": len(r.read())}
        break
    except Exception as exc:
        last = repr(exc)[:160]
        time.sleep(3)
        ok = {"pending": last}
out["api_probe"] = ok

ns = subprocess.run(["netstat", "-ano", "-p", "TCP"], capture_output=True, text=True,
                    errors="replace").stdout
owner = ""
for line in ns.splitlines():
    cols = line.split()
    if len(cols) >= 5 and cols[0].upper() == "TCP" and cols[3].upper() == "LISTENING" \
            and cols[1].endswith(":%d" % API_PORT):
        owner = cols[4]
out["netstat_pid_api"] = owner
out["pid_matches_netstat"] = owner == str(api.pid)

with io.open("D:/moodle/_qoder_n4_ord0473_20260930/run/stack_backend.json", "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=1)
print(json.dumps(out, ensure_ascii=False)[:900])
