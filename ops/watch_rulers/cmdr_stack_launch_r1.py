"""CMDR private stack launcher r1 (this round: tip c0b16645).

Owns everything it touches: the shared preview DB is opened mode=ro and copied with the backup
API; the backend runs on its own port from its own export; ownership of both listeners is read
back off netstat plus the Win32_Process parent chain.
"""
import json
import os
import socket
import sqlite3
import subprocess
import sys
import time
import urllib.error
import urllib.request

SRC_DB = (os.environ.get("CMDR_STACK_SRC_DB")
              or r"D:\moodle\_qoder_preview_20260920\_preview.db")
BUILD = r"D:\moodle\_qoder_cmdr_ref_20260921\live_checks\_build_tip_c0b1664"
SNAP = r"D:\moodle\_qoder_cmdr_snap_tip_c0b1664"
WORK = (os.environ.get("CMDR_STACK_WORK")
              or r"D:\moodle\_qoder_cmdr_stack_seed")
PY = r"D:\moodle\CityNexus\.venv\Scripts\python.exe"
API_PORT = 8805
WEB_PORT = 49805
TIP = "c0b16645afc12aa1c5c5f68474ea9084b877618c"

DETACHED = 0x00000008 | 0x00000200

os.makedirs(WORK, exist_ok=True)
DST = os.path.join(WORK, "cmdr_stack_copy.db")
for suffix in ("", "-wal", "-shm"):
    p = DST + suffix
    if os.path.exists(p):
        os.remove(p)

src = sqlite3.connect("file:" + SRC_DB.replace("\\", "/") + "?mode=ro", uri=True)
dst = sqlite3.connect(DST)
src.backup(dst)
journeys = dst.execute("select count(*) from journeys").fetchone()[0]
with_legs = dst.execute(
    "select count(*) from journeys j where exists (select 1 from journey_legs l "
    "where l.journey_id = j.id)").fetchone()[0]
dst.close()
src.close()

env = dict(os.environ)
for k in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"):
    env.pop(k, None)
env["CITYNEXUS_DATABASE_URL"] = "sqlite:///" + DST.replace("\\", "/")
env["PYTHONPATH"] = SNAP
env["CITYNEXUS_DEMO_MODE"] = "true"
env["PYTHONIOENCODING"] = "utf-8"

api_log = open(os.path.join(WORK, "uvicorn.log"), "ab")
api = subprocess.Popen(
    [PY, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(API_PORT)],
    cwd=os.path.join(SNAP, "backend"), env=env, stdout=api_log, stderr=subprocess.STDOUT,
    stdin=subprocess.DEVNULL, creationflags=DETACHED, close_fds=True)

_proxy_env = dict(env)
_proxy_env["PYTHONPATH"] = ""
web_log = open(os.path.join(WORK, "static_proxy.log"), "ab")
web = subprocess.Popen(
    [PY, r"D:\moodle\_qoder_cmdr_ref_20260921\live_checks\cmdr_static_api_proxy_r1.py",
     "--dist", os.path.join(BUILD, "frontend", "dist"), "--port", str(WEB_PORT),
     "--api", str(API_PORT), "--log", os.path.join(WORK, "static_proxy_req.log")],
    cwd=WORK, env=_proxy_env, stdout=web_log, stderr=subprocess.STDOUT,
    stdin=subprocess.DEVNULL, creationflags=DETACHED, close_fds=True)

opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "cnx-cmdr-stack-launch",
                                               "Accept": "application/json"})
    try:
        with opener.open(req, timeout=30) as r:
            return r.status, len(r.read())
    except urllib.error.HTTPError as e:
        return e.code, len(e.read())
    except Exception as e:
        return None, type(e).__name__


api_ready = 0
for i in range(90):
    st, size = fetch("http://127.0.0.1:" + str(API_PORT) + "/api/v1/journeys")
    if st == 200:
        api_ready = i
        break
    time.sleep(1.0)

web_ready = 0
for i in range(45):
    st, size = fetch("http://127.0.0.1:" + str(WEB_PORT) + "/index.html")
    if st == 200:
        web_ready = i
        break
    time.sleep(1.0)

nstxt = subprocess.run(["netstat", "-ano", "-p", "TCP"], capture_output=True,
                       text=True, encoding="utf-8", errors="replace").stdout


def owner(port):
    for line in nstxt.splitlines():
        if (":" + str(port) + " ") in line and "LISTENING" in line.upper():
            pid = line.split()[-1]
            ps = ("Get-CimInstance Win32_Process -Filter 'ProcessId=" + pid +
                  "' | Select-Object ProcessId,ParentProcessId,Name | ConvertTo-Json -Compress")
            pr = subprocess.run(["powershell", "-NoProfile", "-Command", ps],
                                capture_output=True, text=True, timeout=90).stdout.strip()
            try:
                d = json.loads(pr)
            except Exception:
                d = {}
            return {"listener_pid": pid, "parent_pid": d.get("ParentProcessId"),
                    "name": d.get("Name")}
    return None


receipt = {"at": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "tip": TIP, "build": BUILD,
           "private_db": DST, "db_journeys": journeys, "db_journeys_with_items": with_legs,
           "api_port": API_PORT, "api_ready_after_s": api_ready, "api_child_pid": api.pid,
           "api_owner": owner(API_PORT),
           "web_port": WEB_PORT, "web_ready_after_s": web_ready, "web_child_pid": web.pid,
           "web_owner": owner(WEB_PORT),
           "api_journeys_probe": fetch("http://127.0.0.1:" + str(API_PORT) + "/api/v1/journeys"),
           "web_index_probe": fetch("http://127.0.0.1:" + str(WEB_PORT) + "/index.html")}
print(json.dumps(receipt, ensure_ascii=False, indent=1))
with open(os.path.join(WORK, "launch_receipt.json"), "w", encoding="utf-8") as f:
    json.dump(receipt, f, ensure_ascii=False, indent=1)
sys.exit(0 if api_ready and web_ready else 1)
