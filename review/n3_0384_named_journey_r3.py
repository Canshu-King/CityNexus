#!/usr/bin/env python3
"""ORD-0384 -- how far a journey this lane names can actually be driven, one route at a time.

r2 stopped honestly: `stay-options/generate` answered `NO_OFFERS_FROM_PROVIDER` with an empty `top_k`,
so there was no option to select and `selected_option_id` could not become non-null without inventing
data. This script records the whole answer of each route instead of asserting a hoped-for outcome, so
the delivery can say exactly which field blocks the with-data half and on whose authority.

Routes tried, in order, against my own journey on my own sqlite file:
  stay-options/generate -> stay-options -> plans/generate -> experience -> wallet
Nothing is patched and nothing is fabricated; a refusal is written down as a refusal.
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
PORT = int(sys.argv[2]) if len(sys.argv) > 2 else 5477
PREVIEW = r"D:/moodle/_qoder_preview_20260920/_preview.db"
OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))
steps = []


def log(step, **kw):
    rec = {"step": step}
    rec.update(kw)
    steps.append(rec)
    print(step, json.dumps({k: v for k, v in rec.items() if k != "step"}, ensure_ascii=False)[:200])


def call(method, path, body=None, headers=None, timeout=180):
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request("http://127.0.0.1:%d%s" % (PORT, path), data=data, method=method,
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


def db_journey():
    import sqlite3
    con = sqlite3.connect("file:" + DB.replace("\\", "/") + "?mode=ro", uri=True, timeout=10)
    try:
        return con.execute("select title, status, active_plan_version_id from journeys where id = ?",
                           (JOURNEY,)).fetchone()
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
logf = io.open(os.path.join(ROOT, "backend_r3.log"), "wb")
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
    log("backend_up", popen_pid=proc.pid, netstat_pid=pid, ownership_proved=True)
    row = db_journey()
    status_before, plan_before = row[1], row[2]
    log("journey_before", status=status_before, active_plan_version_id=plan_before)

    attempts = []
    for label, (m, p, b, h) in {
        "stay-options/generate": ("POST", "/api/v1/journeys/%s/stay-options/generate" % JOURNEY, {}, None),
        "stay-options": ("GET", "/api/v1/journeys/%s/stay-options" % JOURNEY, None, None),
        "plans/generate": ("POST", "/api/v1/journeys/%s/plans/generate" % JOURNEY, {},
                           {"Idempotency-Key": "n3-ord0384-r3-%s" % JOURNEY[:8]}),
    }.items():
        s, body = call(m, p, b, headers=h)
        txt = body.decode("utf-8", "replace")
        named = {}
        for token in ("NO_OFFERS_FROM_PROVIDER", "DEMO_MODE_REQUIRED", "PROVIDER", "outcome", "optimizer"):
            if re.search(r'"?%s"?' % token, txt):
                named[token] = True
        attempts.append({"route": "%s %s" % (m, p), "http_status": s, "body_bytes": len(body),
                         "body_head": txt[:400], "tokens_present": sorted(named)})
        log("attempt " + label, status=s, bytes=len(body), head=txt[:150])

    row = db_journey()
    log("journey_after", status=row[1], active_plan_version_id=row[2])
    reads = {}
    for name in ("experience", "wallet"):
        s, bb = call("GET", "/api/v1/journeys/%s/%s" % (JOURNEY, name))
        fn = "named3_%s.json" % name
        io.open(os.path.join(EV, fn), "wb").write(bb)
        reads[name] = {"endpoint": "/api/v1/journeys/{journeyId}/%s" % name, "http_status": s,
                       "body_bytes": len(bb), "sha256": hashlib.sha256(bb).hexdigest(), "saved_as": fn}
        log("GET " + reads[name]["endpoint"], status=s, body_bytes=len(bb))
    after = stat_preview()
    p = os.path.join(EV, "named_journey_r3.json")
    io.open(p, "w", encoding="utf-8").write(json.dumps(
        {"generated_by": os.path.basename(__file__), "order": "ORD-0384", "journey_id": JOURNEY,
         "port": PORT, "database_file": DB.replace("\\", "/"), "popen_pid": proc.pid,
         "netstat_pid": pid, "preview_db_untouched": after == before,
         "preview_db_before": before, "preview_db_after": after,
         "journey_status_before": status_before, "plan_version_before": plan_before,
         "journey_status_after": row[1], "plan_version_after": row[2],
         "attempts": attempts, "reads": reads, "steps": steps}, ensure_ascii=False, indent=1) + "\n")
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
