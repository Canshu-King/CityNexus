"""CMDR first-hand HTTP walk of ORD-0402 slice 1 - the recycle-bin door.

Owns everything it touches: private sqlite copy via the read-only backup API (the shared preview DB is
opened mode=ro and never written), private uvicorn on its own port, and the ownership proof read off
netstat + the listener's own recorded parent in the same run.

Steps, each read back from the server:
  L0 list -> D1 bin one trip -> L1 list (one fewer) -> B1 bin listing (must show it, with its own moment)
  U1 找回 -> B2 bin listing (must be empty again, and still 200 - an empty bin is not a 404)
  O1 the app-generated /openapi.json must declare the door (the ORD-0395 lesson: hand-maintained
     contracts drift from what the running app actually answers)
"""
import json
import os
import sqlite3
import subprocess
import time
import urllib.error
import urllib.request
import uuid

sys_path_note = None
SRC_DB = r"D:\moodle\_qoder_preview_20260920\_preview.db"
WORK = r"D:\moodle\_qoder_cmdr_0402_walk"
PORT = 8723
SNAP = r"D:\moodle\_qoder_cmdr_snap_0402"
PY = r"D:\moodle\CityNexus\.venv\Scripts\python.exe"
LINE = "refs/heads/mirror/integration-frontend-apple-pass1"
TIP = "1e3f9479aa27270c4f497c90ef0d21e32694812c"

os.makedirs(WORK, exist_ok=True)
DST = os.path.join(WORK, "private_0402.db")
for suffix in ("", "-wal", "-shm"):
    p = DST + suffix
    if os.path.exists(p):
        os.remove(p)
src = sqlite3.connect("file:%s?mode=ro" % SRC_DB.replace("\\", "/"), uri=True)
dst = sqlite3.connect(DST)
src.backup(dst)
rows_before = dst.execute("select count(*) from journeys").fetchone()[0]
dst.close()
src.close()

env = dict(os.environ)
for k in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"):
    env.pop(k, None)
env["CITYNEXUS_DATABASE_URL"] = "sqlite:///" + DST.replace("\\", "/")
env["PYTHONPATH"] = SNAP
env["PYTHONIOENCODING"] = "utf-8"
child = subprocess.Popen([PY, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(PORT)],
                         cwd=os.path.join(SNAP, "backend"), env=env,
                         stdout=open(os.path.join(WORK, "uvicorn.log"), "a", encoding="utf-8"),
                         stderr=subprocess.STDOUT)
opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def http(method, path):
    req = urllib.request.Request("http://127.0.0.1:%d%s" % (PORT, path), method=method,
                                 headers={"User-Agent": "cnx-cmdr-0402-walk", "Accept": "application/json"})
    try:
        with opener.open(req, timeout=90) as r:
            return r.status, r.headers.get("Content-Type"), r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.headers.get("Content-Type"), e.read().decode("utf-8", "replace")
    except Exception as e:
        return None, None, "%s: %s" % (type(e).__name__, e)


ready = False
for _ in range(90):
    st, _ct, _b = http("GET", "/api/v1/journeys")
    if st == 200:
        ready = True
        break
    time.sleep(1.0)

ns = subprocess.run(["netstat", "-ano", "-p", "TCP"], capture_output=True, text=True)
listener = [l.strip() for l in ns.stdout.splitlines() if (":%d " % PORT) in l and "LISTENING" in l.upper()]
listen_pid = listener[0].split()[-1] if listener else None
parent = None
if listen_pid and listen_pid.isdigit():
    ps = ("Get-CimInstance Win32_Process -Filter 'ProcessId=%s' | "
          "Select-Object ProcessId,ParentProcessId,CommandLine | ConvertTo-Json -Compress" % listen_pid)
    pr = subprocess.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True, text=True, timeout=90)
    try:
        parent = json.loads(pr.stdout.strip()).get("ParentProcessId")
    except Exception:
        parent = None

receipt = {"at": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "line": LINE, "tip": TIP,
           "private_db": DST, "rows_before": rows_before, "child_pid": child.pid,
           "listener_pid": listen_pid, "listener_parent": parent, "ready": ready}
try:
    st, ct, body = http("GET", "/api/v1/journeys")
    items = json.loads(body) if st == 200 else []
    chosen = items[0]["id"] if items else None
    receipt["L0"] = {"status": st, "count": len(items), "chosen": chosen}

    st, ct, body = http("DELETE", "/api/v1/journeys/%s" % chosen)
    receipt["D1"] = {"status": st}
    st, ct, body = http("GET", "/api/v1/journeys")
    lst1 = json.loads(body) if st == 200 else []
    receipt["L1"] = {"status": st, "count": len(lst1), "still_listed": any(i["id"] == chosen for i in lst1)}

    st, ct, body = http("GET", "/api/v1/recycle-bin/journeys")
    bin_rows = json.loads(body) if st == 200 else []
    mine = [r for r in bin_rows if r.get("id") == chosen]
    receipt["B1"] = {"status": st, "content_type": ct, "count": len(bin_rows),
                     "shows_the_binned_trip": bool(mine),
                     "row": mine[0] if mine else None}

    st, ct, body = http("POST", "/api/v1/journeys/%s/undelete" % chosen)
    receipt["U1"] = {"status": st}
    st, ct, body = http("GET", "/api/v1/recycle-bin/journeys")
    after = json.loads(body) if st == 200 else []
    receipt["B2"] = {"status": st, "count": len(after),
                     "binned_trip_gone_from_bin": not any(r.get("id") == chosen for r in after)}

    st, ct, body = http("GET", "/openapi.json")
    spec_ok = False
    declared = None
    if st == 200:
        try:
            spec = json.loads(body)
            declared = "/api/v1/recycle-bin/journeys" in (spec.get("paths") or {})
            spec_ok = bool(declared)
        except Exception:
            declared = "UNPARSED"
    receipt["O1_openapi"] = {"status": st, "declares_the_door": declared}

    arms = {
        "list_shrank_after_delete": receipt["L1"]["count"] == receipt["L0"]["count"] - 1,
        "bin_answers_200": receipt["B1"]["status"] == 200,
        "bin_shows_the_trip": receipt["B1"]["shows_the_binned_trip"],
        "bin_row_carries_its_own_moment": bool(mine) and any(
            ("delet" in k.lower() or "moment" in k.lower()) for k in (mine[0] or {})),
        "empty_bin_is_200_not_404": receipt["B2"]["status"] == 200 and receipt["B2"]["binned_trip_gone_from_bin"],
        "undelete_returned_200": receipt["U1"]["status"] == 200,
        "app_generated_spec_declares_it": spec_ok,
        "listener_is_my_child": bool(listen_pid) and (listen_pid == str(child.pid) or str(parent) == str(child.pid)),
    }
    receipt["verdicts"] = arms
    receipt["overall"] = "GREEN" if all(arms.values()) else "RED"
finally:
    child.terminate()
    try:
        child.wait(timeout=20)
    except Exception:
        child.kill()
    receipt["child_exit"] = child.returncode

out = os.path.join(WORK, "receipt_r1.json")
with open(out, "w", encoding="utf-8") as fh:
    json.dump(receipt, fh, ensure_ascii=False, indent=1)
print(json.dumps(receipt, ensure_ascii=False, indent=1)[:2600])
print("RECEIPT " + out)
