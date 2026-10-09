"""CMDR first-hand walk of the ORD-0399 找回 route over real HTTP.

Owns everything it touches: a private sqlite copy made with the read-only backup API from the
preview DB (the source is opened mode=ro and is never written), a private uvicorn on its own port,
and a pid-ownership proof taken from netstat in the same run.

Order of operations, each one read back from the server rather than assumed:
  L0 list -> D1 delete one trip -> L1 list (one fewer) -> U1 undelete -> L2 list (back)
  U2 replay (must be 409 JOURNEY_NOT_DELETED, not a second success)
  U3 unknown id (must be 404 JOURNEY_NOT_FOUND)
  A1 the durable audit row for the 找回 action
Nothing here calls demo/reset, and the shared preview DB file is never opened for writing.
"""
import json
import os
import shutil
import socket
import sqlite3
import subprocess
import sys
import time
import urllib.error
import urllib.request
import uuid

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SRC_DB = r"D:\moodle\_qoder_preview_20260920\_preview.db"
WORK = r"D:\moodle\_qoder_cmdr_0399_walk"
PORT = 8721
SNAP = r"D:\moodle\_qoder_cmdr_snap_0399"
PY = r"D:\moodle\CityNexus\.venv\Scripts\python.exe"
LINE = "refs/heads/mirror/integration-frontend-apple-pass1"

os.makedirs(WORK, exist_ok=True)
DST = os.path.join(WORK, "private_0399.db")
for suffix in ("-wal", "-shm"):
    p = DST + suffix
    if os.path.exists(p):
        os.remove(p)
if os.path.exists(DST):
    os.remove(DST)

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

child = subprocess.Popen(
    [PY, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(PORT)],
    cwd=os.path.join(SNAP, "backend"), env=env,
    stdout=open(os.path.join(WORK, "uvicorn.log"), "a", encoding="utf-8"),
    stderr=subprocess.STDOUT)

opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def http(method, path, body=None):
    data = None
    headers = {"User-Agent": "cnx-cmdr-0399-walk", "Accept": "application/json"}
    if body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request("http://127.0.0.1:%d%s" % (PORT, path), data=data,
                                 method=method, headers=headers)
    try:
        with opener.open(req, timeout=60) as r:
            raw = r.read().decode("utf-8", "replace")
            return r.status, raw
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")
    except Exception as e:  # named so a transport failure is never read as a product answer
        return None, "%s: %s" % (type(e).__name__, e)


ready = False
for _ in range(60):
    st, _body = http("GET", "/api/v1/journeys")
    if st == 200:
        ready = True
        break
    time.sleep(1.0)


def error_of(body):
    """Parse the server's own error payload; a transport answer is never a product answer."""
    try:
        return json.loads(body).get("error") or {}
    except Exception:
        return {"UNPARSED": body[:200]}


def reason_of(err):
    return err.get("reason_code") or (err.get("details") or {}).get("reason_code")

netstat = subprocess.run(["netstat", "-ano", "-p", "TCP"], capture_output=True, text=True)
listener = [ln.strip() for ln in netstat.stdout.splitlines()
            if (":%d " % PORT) in ln and "LISTENING" in ln.upper()]
listen_pid = listener[0].split()[-1] if listener else None
owner = None
if listen_pid and listen_pid.isdigit():
    ps = ("Get-CimInstance Win32_Process -Filter 'ProcessId=%s' | "
          "Select-Object ProcessId,ParentProcessId,CommandLine | ConvertTo-Json -Compress" % listen_pid)
    pr = subprocess.run(["powershell", "-NoProfile", "-Command", ps],
                        capture_output=True, text=True, timeout=90)
    owner = {"pid": listen_pid, "raw": pr.stdout.strip()[:400], "stderr": pr.stderr.strip()[:150]}

receipt = {"at": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "line": LINE,
           "src_db_read_only": SRC_DB, "private_db": DST,
           "journeys_rows_in_copy": rows_before, "child_pid": child.pid,
           "listener_lines": listener, "listener_pid": listen_pid,
           "listener_owner_probe": owner, "ready": ready}

try:
    st, body = http("GET", "/api/v1/journeys")
    listing = json.loads(body) if st == 200 else None
    items = listing if isinstance(listing, list) else (listing or {}).get("items") or []
    receipt["L0"] = {"status": st, "count": len(items)}
    chosen = None
    for it in items:
        jid = it.get("id") or it.get("journey_id")
        if jid:
            chosen = jid
            break
    st, body = http("DELETE", "/api/v1/journeys/%s" % chosen)
    receipt["D1_delete"] = {"journey_id": chosen, "status": st, "head": body[:200]}
    st, body = http("GET", "/api/v1/journeys")
    items1 = json.loads(body) if st == 200 else []
    items1 = items1 if isinstance(items1, list) else (items1 or {}).get("items") or []
    receipt["L1_after_delete"] = {"status": st, "count": len(items1),
                                  "chosen_still_listed": any((i.get("id") == chosen) for i in items1)}
    st, body = http("POST", "/api/v1/journeys/%s/undelete" % chosen)
    receipt["U1_undelete"] = {"status": st, "head": body[:220]}
    st, body = http("GET", "/api/v1/journeys")
    items2 = json.loads(body) if st == 200 else []
    items2 = items2 if isinstance(items2, list) else (items2 or {}).get("items") or []
    receipt["L2_after_undelete"] = {"status": st, "count": len(items2),
                                    "chosen_back": any((i.get("id") == chosen) for i in items2)}
    st, body = http("POST", "/api/v1/journeys/%s/undelete" % chosen)
    err2 = error_of(body)
    receipt["U2_replay"] = {"status": st, "head": body[:220], "reason_code": reason_of(err2),
                            "error": err2}
    bogus = str(uuid.uuid4())
    st, body = http("POST", "/api/v1/journeys/%s/undelete" % bogus)
    err3 = error_of(body)
    receipt["U3_unknown"] = {"status": st, "head": body[:220], "reason_code": reason_of(err3),
                             "error": err3}
    # durable state read straight off the private copy, not off an HTTP answer
    conn = sqlite3.connect(DST)
    conn.row_factory = sqlite3.Row
    jrow = conn.execute("select id, status, deleted_at from journeys where id=?", (chosen,)).fetchone()
    receipt["S1_journey_row"] = dict(jrow) if jrow else None
    arow = conn.execute("select action, entity_type, before_json, after_json from audit_logs "
                        "where entity_id=? and action='journey.undeleted' order by id desc limit 1",
                        (chosen,)).fetchone()
    receipt["A1_audit_row"] = dict(arow) if arow else None
    conn.close()
    verdicts = []
    verdicts.append(("deleted_at_cleared", bool(receipt.get("S1_journey_row")) and
                     receipt["S1_journey_row"]["deleted_at"] is None))
    verdicts.append(("listed_again", bool(receipt["L2_after_undelete"]["chosen_back"])))
    verdicts.append(("replay_refused_409", receipt["U2_replay"]["status"] == 409))
    verdicts.append(("replay_names_JOURNEY_NOT_DELETED",
                     receipt["U2_replay"]["reason_code"] == "JOURNEY_NOT_DELETED"))
    verdicts.append(("unknown_refused_404", receipt["U3_unknown"]["status"] == 404))
    verdicts.append(("unknown_names_JOURNEY_NOT_FOUND",
                     receipt["U3_unknown"]["reason_code"] == "JOURNEY_NOT_FOUND"))
    verdicts.append(("audit_row_written", receipt["A1_audit_row"] is not None))
    parent = None
    try:
        parent = json.loads(owner.get("raw") or "{}").get("ParentProcessId")
    except Exception:
        parent = None
    receipt["listener_parent_pid"] = parent
    # the uv python.exe shim re-execs, so ownership is: the listener IS my child, or my child is its
    # recorded parent. comparing the listener against the parent id alone was my own arm bug (r2).
    verdicts.append(("listener_owned_by_my_child",
                     bool(listen_pid) and (listen_pid == str(child.pid) or str(parent) == str(child.pid))))
    receipt["verdicts"] = dict(verdicts)
    receipt["overall"] = "GREEN" if all(v for _, v in verdicts) else "RED"
finally:
    child.terminate()
    try:
        child.wait(timeout=20)
    except Exception:
        child.kill()
    receipt["child_exit"] = child.returncode

out = os.path.join(WORK, "receipt_r3.json")
with open(out, "w", encoding="utf-8") as fh:
    json.dump(receipt, fh, ensure_ascii=False, indent=1)
print(json.dumps(receipt, ensure_ascii=False, indent=1)[:3000])
print("RECEIPT " + out)
