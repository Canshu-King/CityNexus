"""ORD-0421 lane launcher: private uvicorn on its own port over a read-only snapshot of the DB.

The env is handed to the child through Popen(env=...) — the ORD-0410 lane wrote it into a dict it
never applied and got a backend that said demo_mode=false, so this shape is deliberate.
"""
import json
import os
import sqlite3
import subprocess
import sys
import time

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8726
WT = "D:/moodle/_qoder_r_ord0426/wt"
DB = f"D:/moodle/_qoder_r_ord0426/run/_r_ord0426_{PORT}.db"
SRC = "D:/moodle/_qoder_preview_20260920/_preview.db"
PY = "D:/moodle/CityNexus/.venv/Scripts/python.exe"
LOG = f"D:/moodle/_qoder_r_ord0426/run/backend_{PORT}.log"

if not os.path.exists(DB):
    src = sqlite3.connect("file:" + SRC + "?mode=ro", uri=True)
    dst = sqlite3.connect(DB)
    src.backup(dst)
    dst.close()
    src.close()

env = dict(os.environ)
for k in ("DEEPSEEK_API_KEY", "CITYNEXUS_AI_API_KEY", "HTTP_PROXY", "HTTPS_PROXY",
          "http_proxy", "https_proxy"):
    env.pop(k, None)
env["PYTHONPATH"] = WT
env["CITYNEXUS_DATABASE_URL"] = "sqlite:///" + DB.replace("\\", "/")
env["CITYNEXUS_DEMO_MODE"] = "true"
env["CITYNEXUS_AI_ENABLED"] = "false"

child = subprocess.Popen([PY, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1",
                          "--port", str(PORT)], cwd=os.path.join(WT, "backend"), env=env,
                         stdout=open(LOG, "a", encoding="utf-8"), stderr=subprocess.STDOUT,
                         creationflags=0x208)
print(json.dumps({"launched_pid": child.pid, "port": PORT, "db": DB,
                  "db_bytes": os.path.getsize(DB)}))
sys.stdout.flush()
