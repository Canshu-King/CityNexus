# -*- coding: utf-8 -*-
"""Third-generation private stack: the r6 branch tree, fresh empty store, its own ports.

Nothing is inherited from the second generation except the shape of this script. The tree is this lane's
re-cut branch head (the new authoritative tip plus this lane's two files), the store is created empty by
the app under a run id that has never been used, and the ports are ones nothing on this machine holds.
No seed copy, no demo/reset, nothing written to a store this lane does not own.
"""

import json
import os
import subprocess
import sys
import time
import urllib.request

WT = r"D:/moodle/_qoder_ord0568_r3_20261005/wt"
ROOT = r"D:/moodle/_ord0568_r3"
STAMP = time.strftime("%H%M%S")
RUN = "ORD0562prv4-" + STAMP
WORK = os.path.join(ROOT, "stack_" + RUN)
os.makedirs(WORK, exist_ok=True)
DB = os.path.join(WORK, RUN + ".db")
BACK, FRONT = 4772, 4771

if os.path.exists(DB):
    raise SystemExit("refusing to start: %s already exists, issue a fresh run id" % DB)

env = dict(os.environ)
env.update({
    "CITYNEXUS_DATABASE_URL": "sqlite:///" + DB.replace("\\", "/"),
    "CITYNEXUS_DEMO_MODE": "true",
    "CITYNEXUS_E2E_RUN_ID": RUN,
    "NO_PROXY": "*",
})
for gone in ("HTTP_PROXY", "HTTPS_PROXY", "DEEPSEEK_API_KEY"):
    env.pop(gone, None)

backend_log = open(os.path.join(WORK, "uvicorn.log"), "wb")
backend = subprocess.Popen(
    [r"D:/moodle/CityNexus/backend/.venv/Scripts/python.exe", "-m", "uvicorn", "app.main:app",
     "--host", "127.0.0.1", "--port", str(BACK)],
    cwd=os.path.join(WT, "backend"), env=env, stdout=backend_log, stderr=subprocess.STDOUT)

front_env = dict(env)
front_env["CITYNEXUS_BACKEND_PORT"] = str(BACK)
front_log = open(os.path.join(WORK, "front.log"), "wb")
front = subprocess.Popen(
    ["node", "node_modules/vite/bin/vite.js", "preview", "--port", str(FRONT), "--strictPort"],
    cwd=os.path.join(WT, "frontend"), env=front_env, stdout=front_log, stderr=subprocess.STDOUT, shell=False)


def wait(url, seconds=150):
    deadline = time.time() + seconds
    last = ""
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=3) as r:
                return r.status, r.read().decode("utf-8", "replace")
        except Exception as exc:  # noqa: BLE001 - readiness probe
            last = repr(exc)
        time.sleep(0.5)
    return None, "timeout " + last


health_status, health_body = wait("http://127.0.0.1:%d/api/v1/health" % BACK, 180)
front_status, _ = wait("http://localhost:%d/" % FRONT, 90)

receipt = {
    "run": RUN, "db": DB,
    "store_created_by": "the app, from an empty file (no seed copy, no demo/reset)",
    "tree": WT,
    "branch": subprocess.run(["git", "-C", WT, "rev-parse", "--abbrev-ref", "HEAD"],
                             capture_output=True).stdout.decode().strip(),
    "head": subprocess.run(["git", "-C", WT, "rev-parse", "HEAD"], capture_output=True).stdout.decode().strip(),
    "base_tip": "8996eee4fb9fb4e159588305223ef421728c4e72",
    "ports": {"backend": BACK, "front": FRONT},
    "health_status": health_status, "front_status": front_status,
    "health_body": (health_body or "")[:200],
    "bundle": sorted(f for f in os.listdir(os.path.join(WT, "frontend", "dist", "assets")) if f.startswith("index-")),
    "children": [{"pid": backend.pid, "role": "uvicorn"}, {"pid": front.pid, "role": "vite preview"}],
}
with open(os.path.join(WORK, "stack_receipt.json"), "w", encoding="utf-8") as fh:
    json.dump(receipt, fh, ensure_ascii=False, indent=1)
print(json.dumps(receipt, ensure_ascii=False, indent=1))
print("WORKDIR=" + WORK)
sys.exit(0 if health_status == 200 and front_status == 200 else 1)
