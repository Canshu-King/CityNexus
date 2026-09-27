#!/usr/bin/env python3
"""ORD-0384 -- put a plan and a chosen stay on the journey this lane named, then read the pair again.

r1 built `ffc69f42-...` and asked `POST /api/v1/demo/prepare-scenario` to plan it. prepare-scenario
answered with the *seeded* journey id instead of mine, so my journey kept its `no_active_plan` /
`stay_not_chosen` / `offline_pack_not_ready` reading. Rather than adopt the seeded journey as if it
were mine, this drives the same three routes prepare-scenario uses, against my own journey id:
`stay-options/generate` -> `stay-options/{id}/select` -> `plans/generate`.

Same rules as r1: this lane's sqlite file, this lane's port, ownership proven by the parent chain plus
a row read out of the file itself, and `_preview.db` stat-checked before and after so the receipt shows
the shared database did not move.
"""
import hashlib
import io
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request

ROOT = r"D:/moodle/_qoder_n3_ord0384_live"
DB = os.path.join(ROOT, "n3_ord0384_named.db")
EV = r"D:/moodle/_qoder_n3_ord0357/review/evidence/ord0384"
VENV_PY = r"D:/moodle/CityNexus/.venv/Scripts/python.exe"
JOURNEY = sys.argv[1]
PORT = int(sys.argv[2]) if len(sys.argv) > 2 else 5476
PREVIEW = r"D:/moodle/_qoder_preview_20260920/_preview.db"
OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))
steps = []


def log(step, **kw):
    rec = {"step": step}
    rec.update(kw)
    steps.append(rec)
    print(step, json.dumps({k: v for k, v in rec.items() if k != "step"}, ensure_ascii=False)[:220])


def call(method, path, body=None, headers=None, timeout=180):
    url = "http://127.0.0.1:%d%s" % (PORT, path)
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, method=method,
                                 headers={"Accept": "application/json",
                                          **({"Content-Type": "application/json"} if data else {}),
                                          **(headers or {})})
    try:
        with OPENER.open(req, timeout=timeout) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()


def stat_preview():
    try:
        st = os.stat(PREVIEW)
        return {"exists": True, "bytes": st.st_size, "mtime_ns": st.st_mtime_ns}
    except OSError as exc:
        return {"exists": False, "error": type(exc).__name__}


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
    chain, cur = [], pid
    for _ in range(12):
        if not cur:
            break
        chain.append(int(cur))
        r = subprocess.run(["powershell.exe", "-NoProfile", "-Command",
                            "(Get-CimInstance Win32_Process -Filter 'ProcessId=%d').ParentProcessId" % int(cur)],
                           capture_output=True, text=True, errors="replace", timeout=60)
        m = re.search(r"\d+", r.stdout or "")
        cur = int(m.group(0)) if m else None
    return chain


def db_journey(jid):
    import sqlite3
    con = sqlite3.connect("file:" + DB.replace("\\", "/") + "?mode=ro", uri=True, timeout=10)
    try:
        return con.execute("select title, status, active_plan_version_id from journeys where id = ?",
                           (jid,)).fetchone()
    finally:
        con.close()


before = stat_preview()
env = dict(os.environ)
for k in [k for k in list(env) if re.search(r"(API_KEY|AUTH_TOKEN|SECRET)$|^OPENAI_|^DEEPSEEK_", k)]:
    env.pop(k, None)
env.update({"CITYNEXUS_DEMO_MODE": "true", "CITYNEXUS_AI_ENABLED": "false",
            "CITYNEXUS_DATABASE_URL": "sqlite:///" + DB.replace("\\", "/"),
            "PYTHONPATH": ROOT.replace("\\", "/"),
            "HTTP_PROXY": "", "HTTPS_PROXY": "", "NO_PROXY": "*"})
log("attach", db=DB.replace("\\", "/"), journey_id=JOURNEY, port=PORT, preview_before=before)
logf = io.open(os.path.join(ROOT, "backend_r2.log"), "wb")
proc = subprocess.Popen([VENV_PY, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(PORT)],
                        cwd=os.path.join(ROOT, "backend"), env=env, stdout=logf, stderr=subprocess.STDOUT)
try:
    for _ in range(120):
        try:
            if call("GET", "/api/v1/health", timeout=5)[0] == 200:
                break
        except Exception:
            pass
        time.sleep(1)
    else:
        raise SystemExit("backend did not answer")
    pid = listening_pid(PORT)
    chain = parent_chain(pid) if pid else []
    assert pid and (pid == proc.pid or proc.pid in chain), "listener is not mine"
    log("backend_up", popen_pid=proc.pid, netstat_pid=pid, parent_chain=chain, ownership_proved=True)
    row = db_journey(JOURNEY)
    log("journey_in_my_file_before", title=row[0], status=row[1], active_plan_version_id=row[2])

    s, b = call("POST", "/api/v1/journeys/%s/stay-options/generate" % JOURNEY, {})
    log("POST stay-options/generate", status=s, body=b.decode("utf-8", "replace")[:180])
    s, b = call("GET", "/api/v1/journeys/%s/stay-options" % JOURNEY)
    opts = json.loads(b.decode("utf-8")) if s == 200 else []
    opts = opts if isinstance(opts, list) else (opts.get("options") or [])
    log("GET stay-options", status=s, returned=len(opts),
        first_option_id=(opts[0].get("id") if opts else None))
    assert opts, "no stay option was produced, so nothing can be selected"
    oid = opts[0].get("id")
    s, b = call("POST", "/api/v1/journeys/%s/stay-options/%s/select" % (JOURNEY, oid), {})
    log("POST stay-options/{id}/select", status=s, option_id=oid,
        body=b.decode("utf-8", "replace")[:160])
    s, b = call("POST", "/api/v1/journeys/%s/plans/generate" % JOURNEY, {},
                headers={"Idempotency-Key": "n3-ord0384-named-r2-%s" % JOURNEY[:8]})
    log("POST plans/generate", status=s, body=b.decode("utf-8", "replace")[:200])

    row = db_journey(JOURNEY)
    log("journey_in_my_file_after", title=row[0], status=row[1], active_plan_version_id=row[2])
    reads = {}
    for name in ("experience", "wallet"):
        s, bb = call("GET", "/api/v1/journeys/%s/%s" % (JOURNEY, name))
        fn = "named2_%s.json" % name
        io.open(os.path.join(EV, fn), "wb").write(bb)
        reads[name] = {"endpoint": "/api/v1/journeys/{journeyId}/%s" % name, "http_status": s,
                       "body_bytes": len(bb), "sha256": hashlib.sha256(bb).hexdigest(), "saved_as": fn}
        log("GET " + reads[name]["endpoint"], status=s, body_bytes=len(bb))
    after = stat_preview()
    receipt = {"generated_by": os.path.basename(__file__), "order": "ORD-0384",
               "journey_id": JOURNEY, "port": PORT, "database_file": DB.replace("\\", "/"),
               "popen_pid": proc.pid, "netstat_pid": pid,
               "preview_db_untouched": after == before,
               "preview_db_before": before, "preview_db_after": after,
               "reads": reads, "steps": steps}
    p = os.path.join(EV, "named_journey_r2.json")
    io.open(p, "w", encoding="utf-8").write(json.dumps(receipt, ensure_ascii=False, indent=1) + "\n")
    assert after == before, "the shared _preview.db moved while this script ran"
    print("READING " + p.replace("\\", "/"))
finally:
    proc.terminate()
    try:
        proc.wait(timeout=30)
    except subprocess.TimeoutExpired:
        proc.kill()
    logf.close()
sys.exit(0)
