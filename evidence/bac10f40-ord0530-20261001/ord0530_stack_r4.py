"""ORD-0530 r3 -- bring up this lane's private stack on a copy of the commander's denominator.

Nothing here touches a shared port or the original library:
  * the ports come from the OS (a fixed port once let a foreign backend answer me, and its
    openapi had no `checkins` path at all -- so the answer is proved, not assumed),
  * the database is a byte copy of `canary_56d20ec.db`; that file is only ever read,
  * ownership is proved by a note string that exists nowhere else, read back through the door.

The denominator needs two days of stamps and the door only accepts the server's *now*, so the
second day arrives as one direct row in my copy.  That is a bypass, not a fix, and the block says so.
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
from datetime import datetime, timedelta

ROOT = "D:/moodle/_qoder_ai_ord0387_20260928"
WT = ROOT + "/wt"
DB = ROOT + "/ord0530_denominator_r3.db"
JOURNEY = "22222222-2222-4222-8222-222222222222"
PY = "D:/moodle/CityNexus/.venv/Scripts/python.exe"
VITE = "D:/moodle/_qoder_ai_ord0387_20260928/node_modules/vite/bin/vite.js"
NODE = "C:/Program Files/nodejs/node.exe"
MARKER = "ORD-0530-r3 分母 · 昨天的第三枚"
ACTIVITIES = {
    "Old Town Gate": "1f2fb0b3-09ba-4f54-8d74-8c8ba381a9cf",
    "Riverside Museum": "9cbbaa92-b72c-4777-b3a7-74978b7c379a",
}


def env_extra(extra=None):
    e = dict(os.environ)
    for k in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "NO_PROXY",
              "DEEPSEEK_API_KEY", "CITYNEXUS_AI_API_KEY", "OPENAI_API_KEY"):
        e.pop(k, None)
    e["CITYNEXUS_AI_ENABLED"] = "false"
    e.update(extra or {})
    return e


def free_pair():
    ports = []
    for _ in range(2):
        s = socket.socket()
        s.bind(("127.0.0.1", 0))
        ports.append(s.getsockname()[1])
        s.close()
    return ports[0], ports[1]


def get(url, timeout=10):
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()
    except Exception as e:  # noqa: BLE001 - a refused connect is a reading, not a crash
        return None, repr(e)


def post_json(url, payload):
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"},
                                 method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")


backend_port, frontend_port = free_pair()
receipt = {"started_local": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
           "db_copy": DB, "journey": JOURNEY,
           "backend_port": backend_port, "frontend_port": frontend_port}

be = subprocess.Popen(
    [PY, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(backend_port),
     "--log-level", "info"],
    cwd=WT + "/backend", env=env_extra({"CITYNEXUS_DATABASE_URL": "sqlite:///" + DB}),
    stdout=open(ROOT + "/ord0530_backend_r3.log", "w", encoding="utf-8", newline="\n"),
    stderr=subprocess.STDOUT)

health = None
for _ in range(90):
    st, _b = get("http://127.0.0.1:%d/api/v1/health" % backend_port)
    if st == 200:
        health = st
        break
    time.sleep(1)
receipt["health"] = health
receipt["backend_alive"] = be.poll() is None

st, blob = get("http://127.0.0.1:%d/openapi.json" % backend_port)
doc = blob.decode("utf-8", "replace") if st == 200 else ""
receipt["openapi_status"] = st
receipt["openapi_has_checkins"] = "/api/v1/journeys/{journey_id}/checkins" in doc

stamped = []
for label, activity_id in ACTIVITIES.items():
    st, answer = post_json(
        "http://127.0.0.1:%d/api/v1/journeys/%s/checkins" % (backend_port, JOURNEY),
        {"activity_id": activity_id, "note": "ORD-0530 r3 真门打的 · " + label})
    stamped.append({"stop": label, "http_status": st,
                    "answer_head": json.dumps(answer, ensure_ascii=False)[:200]})
receipt["real_post_stamps"] = stamped

con = sqlite3.connect(DB)
cols = [r[1] for r in con.execute("pragma table_info(journey_checkins)")]
receipt["journey_checkins_columns"] = cols
probe = con.execute("select target_kind, source, stamped_at from journey_checkins"
                    " where journey_id=? order by stamped_at desc limit 1", (JOURNEY,)).fetchone()
receipt["shape_copied_from_the_door_own_row"] = list(probe)
target_kind, source, now = probe[0], probe[1], probe[2]
receipt["server_now_as_the_door_wrote_it"] = now
yesterday = (datetime.fromisoformat(now) - timedelta(days=1)).isoformat()
inserted = con.execute(
    "insert into journey_checkins (journey_id, target_kind, target_key, stamped_at, note, source)"
    " values (?,?,?,?,?,?)",
    (JOURNEY, target_kind, "7951eb3f-a41b-49f6-9218-37bbd65f7d85", yesterday, MARKER,
     source)).rowcount
con.commit()
receipt["third_row_written_directly"] = {
    "inserted": inserted, "stamped_at": yesterday, "note": MARKER,
    "why": "the door only stamps the server's now, and this order needs two days",
}

st, rows = get("http://127.0.0.1:%d/api/v1/journeys/%s/checkins" % (backend_port, JOURNEY))
payload = json.loads(rows.decode("utf-8")) if st == 200 else []
receipt["ownership_proof"] = {
    "door_http_status": st,
    "rows_read_back": len(payload),
    "marker_row_present": any(MARKER in (r.get("note") or "") for r in payload),
    "distinct_days": sorted({r["stamped_at"][:10] for r in payload}),
    "instants": [r["stamped_at"] for r in payload],
}

fe = subprocess.Popen(
    [NODE, VITE, "--port", str(frontend_port), "--strictPort", "--host", "127.0.0.1"],
    cwd=WT + "/frontend", env=env_extra({"CITYNEXUS_BACKEND_PORT": str(backend_port)}),
    stdout=open(ROOT + "/ord0530_vite_r3.log", "w", encoding="utf-8", newline="\n"),
    stderr=subprocess.STDOUT)

served = None
for _ in range(60):
    st, blob = get("http://127.0.0.1:%d/v8/footprints" % frontend_port)
    if st == 200:
        served = st
        break
    time.sleep(1)
mine = open(WT + "/frontend/index.html", "rb").read()
st2, entry = get("http://127.0.0.1:%d/index.html" % frontend_port)
receipt["frontend"] = {
    "status": served, "alive": fe.poll() is None,
    "entry_bytes_equal_my_disk": st2 == 200 and entry == mine,
    "proxy_backend_port": backend_port,
}
receipt["provenance_line"] = "this lane's private stack: frontend=:%d -> backend=:%d db=%s" % (
    frontend_port, backend_port, os.path.basename(DB))
receipt["ended_local"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")

dst = ROOT + "/ord0530_reads_r3/stack_receipt_r3.json"
os.makedirs(os.path.dirname(dst), exist_ok=True)
json.dump(receipt, open(dst, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(json.dumps(receipt, ensure_ascii=False, indent=1))
print("PIDS backend=%d frontend=%d" % (be.pid, fe.pid))
print("receipt", dst, os.path.getsize(dst), "B")
