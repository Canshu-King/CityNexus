"""ORD-0346 S4: the same server, three whole answers, so the coverage claim is read and not summarised.

Boots the identical stack as capability_reading_r1.py (this lane's own port, this lane's own
SQLite, resolver seam off) and writes the complete bodies for one city the catalog names, one the
vocabulary only names, and one nothing can name.
"""
import json
import os
import subprocess
import sys
import time

import httpx

WORK = os.path.dirname(os.path.abspath(__file__))
BACKEND = "D:/moodle/_qoder_ord0346_S4/backend"
DB = os.path.join(WORK, "ord0346_S4_r1.db")
PORT = int(os.environ.get("CNX_S4_PORT", "8847"))
PY = "D:/moodle/CityNexus/.venv/Scripts/python.exe"
QUERIES = ["北京", "厦门", "东京", "福州", "云和县"]

env = dict(os.environ)
env.update({
    "CITYNEXUS_DATABASE_URL": "sqlite:///" + DB.replace("\\", "/"),
    "CITYNEXUS_ANYWHERE_RESOLVER": "off",
    "CITYNEXUS_DEMO_MODE": "true",
    "CITYNEXUS_AI_ENABLED": "false",
    "CITYNEXUS_GUARDIAN_AUTORUN": "false",
    "PHOTON_BASE_URL": "http://127.0.0.1:9",
    "PYTHONPATH": BACKEND,
})
log = open(os.path.join(WORK, "server_r2.log"), "w", encoding="utf-8")
proc = subprocess.Popen(
    [PY, "-X", "utf8", "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1",
     "--port", str(PORT), "--log-level", "warning"],
    cwd=BACKEND, env=env, stdout=log, stderr=subprocess.STDOUT)
try:
    base = "http://127.0.0.1:%d" % PORT
    up = False
    for _ in range(80):
        try:
            if httpx.get(base + "/api/v1/health", timeout=2.0).status_code == 200:
                up = True
                break
        except Exception:
            pass
        time.sleep(0.5)
    if not up:
        raise SystemExit("NOT MEASURED: no /api/v1/health on %d\n%s" % (
            PORT, open(os.path.join(WORK, "server_r2.log"), encoding="utf-8",
                       errors="replace").read()[-2000:]))
    bodies = {}
    for q in QUERIES:
        r = httpx.get(base + "/api/v1/destinations/capability", params={"query": q}, timeout=20.0)
        bodies[q] = {"http_status": r.status_code, "content_type": r.headers.get("content-type"),
                     "body_bytes": len(r.content), "body": r.json()}
    out = {"at_local": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "port": PORT,
           "database_url": env["CITYNEXUS_DATABASE_URL"], "health_proved": up, "bodies": bodies}
    path = os.path.join(WORK, "capability_bodies_r2.json")
    json.dump(out, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("wrote", path, os.path.getsize(path), "bytes")
    for q in QUERIES:
        b = bodies[q]["body"]
        print("---", q, b.get("capability"), b.get("reason_code"), "places=%s" % b.get("place_count"))
        print("    coverage:", json.dumps(b.get("coverage"), ensure_ascii=False))
        print("    matched_label:", b.get("matched_label"), "| identity:", b.get("canonical_destination_id"))
finally:
    subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"], capture_output=True)
    log.close()
