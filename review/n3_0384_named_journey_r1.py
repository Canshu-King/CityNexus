#!/usr/bin/env python3
"""ORD-0384 -- build a journey this lane names, on a database this lane owns, and read it back.

Why: the phone chain's only remaining journey is `One Day in Nexus City` / `CNX-DEMO`, which exercises
`stay_budget_undeclared` and `stay_not_chosen` and nothing else. The checklist's other rules -- above all
`stay_chosen_but_unconfirmed`, the one that actually shows on Today -- need a journey that has a plan
and a selected option. The commander's order for this delivery is that the with-data half must be a
journey of my own naming, built with commands that are written into the delivery, and that nothing of
mine may point at :8693/:4781 or touch `_preview.db`.

Everything here runs against an export of the same commit the chain runs (`git archive`), on a port in
this lane's band, on a sqlite file under this lane's directory. `POST /api/v1/demo/reset` is called
against **that file only** -- it deletes 52 tables (`backend/app/main.py:2046`), which is exactly why it
is never pointed at a database anybody else reads.

Ownership is proven the way the shared-port rule requires: the pid this script started is the pid
netstat reports as listening, and the database file the server wrote is this script's own path.
"""
import hashlib
import io
import json
import os
import re
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request

REPO = r"D:/moodle/CityNexus"
SHA = sys.argv[1] if len(sys.argv) > 1 else "213750423d9bdc10672c0488f76f8b0963d88765"
VENV_PY = os.path.join(REPO, ".venv", "Scripts", "python.exe")
ROOT = r"D:/moodle/_qoder_n3_ord0384_live"
EV = r"D:/moodle/_qoder_n3_ord0357/review/evidence/ord0384"
DB = os.path.join(ROOT, "n3_ord0384_named.db")
TITLE = "N3-ORD0384 自建具名行程（有数据那一半）"
PORT = int(sys.argv[2]) if len(sys.argv) > 2 else 5475
OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))
steps = []


def log(step, **kw):
    rec = {"step": step}
    rec.update(kw)
    steps.append(rec)
    print(step, json.dumps({k: v for k, v in rec.items() if k != "step"}, ensure_ascii=False)[:240])


def call(method, path, body=None, timeout=90):
    url = "http://127.0.0.1:%d%s" % (PORT, path)
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, method=method,
                                 headers={"Accept": "application/json",
                                          **({"Content-Type": "application/json"} if data else {})})
    try:
        with OPENER.open(req, timeout=timeout) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()


def listening_pid(port):
    out = subprocess.run(["netstat", "-ano", "-p", "TCP"], capture_output=True, text=True,
                         errors="replace").stdout
    for line in out.splitlines():
        if ("127.0.0.1:%d " % port) in line and "LISTENING" in line:
            m = re.search(r"LISTENING\s+(\d+)", line)
            if m:
                return int(m.group(1))
    return None


def parent_chain(pid):
    """Walk ParentProcessId up from `pid`. The venv's python.exe starts the real interpreter as a
    child, so the listener is legitimately not the pid I spawned -- but it has to be under it."""
    chain = []
    cur = pid
    for _ in range(12):
        if not cur:
            break
        chain.append(int(cur))
        r = subprocess.run(["powershell.exe", "-NoProfile", "-Command",
                            "(Get-CimInstance Win32_Process -Filter 'ProcessId=%d').ParentProcessId" % int(cur)],
                           capture_output=True, text=True, errors="replace", timeout=60)
        nxt = re.search(r"\d+", r.stdout or "")
        cur = int(nxt.group(0)) if nxt else None
    return chain


def my_db_has_journey(db_path, journey_id):
    """Read-only open of the file this script named. A 200 on my port can be another process's answer;
    the row being in *my* file is what ties the response to the database I own."""
    import sqlite3
    uri = "file:" + db_path.replace("\\", "/").replace(" ", "%20") + "?mode=ro"
    con = sqlite3.connect(uri, uri=True, timeout=10)
    try:
        row = con.execute("select title, city_code from journeys where id = ?", (journey_id,)).fetchone()
    finally:
        con.close()
    return row


PREVIEW = r"D:/moodle/_qoder_preview_20260920/_preview.db"


def stat_preview():
    """`stat` only, never opened. This script calls a route that deletes 52 tables; the receipt has to
    show the somebody-else's-database case did not happen, not merely assert it did not."""
    try:
        st = os.stat(PREVIEW)
        return {"exists": True, "bytes": st.st_size, "mtime_ns": st.st_mtime_ns}
    except OSError as exc:
        return {"exists": False, "error": type(exc).__name__}


# 1. export the backend at the commit the chain runs, from git rather than from a working tree
if os.path.isdir(ROOT):
    subprocess.run(["cmd", "/c", "rmdir", "/s", "/q", ROOT.replace("/", "\\")], timeout=600)
os.makedirs(ROOT, exist_ok=True)
rc = subprocess.run('git -C "%s" archive %s backend data contracts tools scripts agent-mcp | tar -x -C "%s"'
                    % (REPO, SHA, ROOT), shell=True, capture_output=True, text=True, errors="replace")
assert rc.returncode == 0 and os.path.isdir(os.path.join(ROOT, "backend", "app")), "archive failed: " + rc.stderr[:200]
log("export", sha=SHA, root=ROOT.replace("\\", "/"), rc=rc.returncode)
preview_before = stat_preview()
log("preview_db_before", **preview_before)

# 2. start the backend on this lane's port, on this lane's database, with the AI keys dropped by name
env = dict(os.environ)
dropped = sorted(k for k in list(env) if re.search(r"(API_KEY|AUTH_TOKEN|SECRET)$|^OPENAI_|^DEEPSEEK_", k))
for k in dropped:
    env.pop(k, None)
env.update({
    "CITYNEXUS_DEMO_MODE": "true",
    "CITYNEXUS_AI_ENABLED": "false",
    "CITYNEXUS_DATABASE_URL": "sqlite:///" + DB.replace("\\", "/"),
    "PYTHONPATH": ROOT.replace("\\", "/"),
    "HTTP_PROXY": "", "HTTPS_PROXY": "", "NO_PROXY": "*",
})
main_py = os.path.join(ROOT, "backend", "app", "main.py")
log("backend_source", main_py_lines=len(io.open(main_py, encoding="utf-8").read().splitlines()),
    main_py_sha256_16=hashlib.sha256(io.open(main_py, "rb").read()).hexdigest()[:16],
    env_keys_dropped_names_only=dropped)
logf = io.open(os.path.join(ROOT, "backend_stdout.log"), "wb")
proc = subprocess.Popen([VENV_PY, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(PORT)],
                        cwd=os.path.join(ROOT, "backend"), env=env, stdout=logf, stderr=subprocess.STDOUT)
try:
    up = False
    for _ in range(90):
        try:
            s, _b = call("GET", "/api/v1/health", timeout=5)
            if s == 200:
                up = True
                break
        except Exception:
            pass
        time.sleep(1)
    assert up, "backend never answered on %d" % PORT
    pid = listening_pid(PORT)
    chain = parent_chain(pid) if pid else []
    owned = bool(pid) and (pid == proc.pid or proc.pid in chain)
    log("backend_up", port=PORT, popen_pid=proc.pid, netstat_pid=pid, parent_chain=chain,
        ownership_proved=owned, db_file=DB.replace("\\", "/"))
    assert owned, "the listener on my port is not a process I started"

    # 3. fixture door, on my own file only
    s, b = call("POST", "/api/v1/demo/reset", {})
    log("POST /api/v1/demo/reset", status=s, body=b.decode("utf-8", "replace")[:120])
    assert s == 200, "reset refused: %s" % b[:200]

    # 4. take the traveler the seed actually made, rather than assuming a literal
    s, b = call("GET", "/api/v1/demo/scene")
    scene = json.loads(b.decode("utf-8"))
    s2, b2 = call("GET", "/api/v1/journeys/%s" % scene["journey_id"])
    traveler = json.loads(b2.decode("utf-8")).get("traveler_id") if s2 == 200 else None
    if not traveler:
        s3, b3 = call("GET", "/api/v1/journeys/%s/experience" % scene["journey_id"])
        traveler = json.loads(b3.decode("utf-8"))["journey"]["traveler_id"]
    log("GET /api/v1/demo/scene", status=s, seeded_journey_id=scene.get("journey_id"))
    log("traveler_taken_from_seed", traveler_id=traveler, via_status=s2)

    # 5. the journey this lane names
    payload = {
        "traveler_id": traveler,
        "title": TITLE,
        "city_code": "CNX-DEMO",
        "timezone": "Asia/Shanghai",
        "start_at": "2026-11-05T15:00:00+08:00",
        "end_at": "2026-11-07T11:00:00+08:00",
        "budget": {"currency": "CNY", "amount_minor": 240000},
        "planning_mode": "balanced",
        "party_size": 2,
        "arrival_anchor": {"at": "2026-11-05T15:00:00+08:00", "location": "N3 自建 · 到达"},
        "departure_anchor": {"at": "2026-11-07T11:00:00+08:00", "location": "N3 自建 · 离开"},
    }
    s, b = call("POST", "/api/v1/journeys", payload)
    mine = json.loads(b.decode("utf-8")) if s in (200, 201) else {}
    my_id = mine.get("id") or mine.get("journey", {}).get("id")
    log("POST /api/v1/journeys", status=s, title=TITLE, journey_id=my_id,
        request_field_names=sorted(payload.keys()))
    assert my_id, "journey create refused: %s" % b[:300]
    row = my_db_has_journey(DB, my_id)
    log("journey_row_in_my_own_sqlite", table="journeys", id=my_id,
        title_in_file=row[0] if row else None, city_code_in_file=row[1] if row else None)
    assert row and row[0] == TITLE, "the server answered but the row is not in MY database file"

    # 6. put a plan on it: prepare-scenario picks the newest DRAFT journey, which is now mine
    s, b = call("POST", "/api/v1/demo/prepare-scenario", {}, timeout=180)
    log("POST /api/v1/demo/prepare-scenario", status=s, body=b.decode("utf-8", "replace")[:200])

    # 7. read the pair back, the same two routes the screen reads
    saved = {}
    for name in ("experience", "wallet"):
        s, b = call("GET", "/api/v1/journeys/%s/%s" % (my_id, name))
        fn = "named_%s.json" % name
        io.open(os.path.join(EV, fn), "wb").write(b)
        saved[name] = {"endpoint": "/api/v1/journeys/{journeyId}/%s" % name, "http_status": s,
                       "body_bytes": len(b), "sha256": hashlib.sha256(b).hexdigest(), "saved_as": fn}
        log("GET " + saved[name]["endpoint"], status=s, body_bytes=len(b))
    preview_after = stat_preview()
    log("preview_db_after", **preview_after)
    receipt = {"generated_by": os.path.basename(__file__), "order": "ORD-0384",
               "backend_sha": SHA, "port": PORT, "database_file": DB.replace("\\", "/"),
               "popen_pid": proc.pid, "title": TITLE, "journey_id": my_id,
               "preview_db_untouched": preview_after == preview_before,
               "preview_db_before": preview_before, "preview_db_after": preview_after,
               "create_payload": {k: v for k, v in payload.items() if k != "traveler_id"},
               "traveler_id": traveler, "reads": saved, "steps": steps}
    p = os.path.join(EV, "named_journey_r1.json")
    io.open(p, "w", encoding="utf-8").write(json.dumps(receipt, ensure_ascii=False, indent=1) + "\n")
    assert preview_after == preview_before, "the shared _preview.db moved while this script ran"
    print("journey_id=%s" % my_id)
    print("READING " + p.replace("\\", "/"))
finally:
    proc.terminate()
    try:
        proc.wait(timeout=30)
    except subprocess.TimeoutExpired:
        proc.kill()
    logf.close()
sys.exit(0)
