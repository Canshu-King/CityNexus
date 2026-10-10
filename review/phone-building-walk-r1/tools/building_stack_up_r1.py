"""Bring up THIS lane's own phone stack for the building walk, on ports nobody else owns.

Ports: backend 8145, static 4881.  4783/4787 are the commander's static instrument and are NOT touched;
I check every port is free before binding and refuse to start if not, rather than reusing someone's.

Fresh private store every run: the shared preview DB is opened READ-ONLY and copied with sqlite's
backup(), because every step of this walk taps things and a shared file would let one run's stamps decide
the next run's first answer.  The shared file's bytes and mtime are re-stat'ed after the copy so the
receipt can prove it was never written.

The backend is started with DEMO_MODE on and AI off: the walk is about whether a person can finish the
flow, not about whether a provider answers.
"""
import json
import os
import sqlite3
import subprocess
import sys
import time
import urllib.request

LANE = r"D:/moodle/_qoder_phone_ord0485_20260930"
TREE = os.path.join(LANE, "build_walk")
PY = r"D:/moodle/CityNexus/.venv/Scripts/python.exe"
SHARED = r"D:\moodle\_qoder_preview_20260920\_preview.db"
DB = os.path.join(LANE, "run", "walk_phone.db")
BACKEND_PORT = 8145
STATIC_PORT = 4881
op = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def listener(port):
    out = subprocess.run(["netstat", "-ano", "-p", "tcp"], stdout=subprocess.PIPE,
                         timeout=30).stdout
    for line in out.decode("gbk", errors="replace").splitlines():
        q = line.split()
        if len(q) >= 5 and q[0].upper() == "TCP" and q[1].endswith(":%d" % port) \
                and q[3].upper() == "LISTENING":
            return q[4]
    return None


def fresh_store():
    for suffix in ("", "-wal", "-shm"):
        p = DB + suffix
        if os.path.exists(p):
            try:
                os.remove(p)
            except OSError:
                time.sleep(1)
                os.remove(p)
    before = os.stat(SHARED)
    src = sqlite3.connect("file:" + SHARED.replace("\\", "/") + "?mode=ro", uri=True)
    dst = sqlite3.connect(DB)
    src.backup(dst)
    dst.close()
    src.close()
    after = os.stat(SHARED)
    con = sqlite3.connect(DB)
    tables = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    counts = {}
    for t in ("journeys", "places", "journey_stops", "journey_checkins", "plans"):
        if t in tables:
            counts[t] = con.execute("SELECT COUNT(*) FROM %s" % t).fetchone()[0]
    con.close()
    return {"shared_bytes_before": before.st_size, "shared_mtime_before": before.st_mtime,
            "shared_bytes_after": after.st_size, "shared_mtime_after": after.st_mtime,
            "shared_untouched": (before.st_size == after.st_size and before.st_mtime == after.st_mtime),
            "private_store_bytes": os.path.getsize(DB), "counts": counts}


def boot_backend():
    log = os.path.join(LANE, "run", "walk_backend_%d.log" % BACKEND_PORT)
    open(log, "ab").close()
    ps = ("$env:HTTP_PROXY=''; $env:HTTPS_PROXY=''; $env:DEEPSEEK_API_KEY=''; "
          "$env:PYTHONPATH='%s'; $env:CITYNEXUS_DATABASE_URL='sqlite:///%s'; "
          "$env:CITYNEXUS_DEMO_MODE='true'; $env:CITYNEXUS_AI_ENABLED='false'; "
          "Start-Process -FilePath '%s' -ArgumentList '-m','uvicorn','app.main:app',"
          "'--host','127.0.0.1','--port','%d' -WorkingDirectory '%s' -WindowStyle Hidden "
          "-RedirectStandardOutput '%s' -RedirectStandardError '%s'"
          % (TREE, DB.replace("\\", "/"), PY, BACKEND_PORT,
             os.path.join(TREE, "backend"), log, log + ".err"))
    with open(os.path.join(LANE, "run", "walk_launcher.log"), "ab") as sink:
        subprocess.run(["powershell", "-NoProfile", "-Command", ps], stdout=sink, stderr=sink,
                       timeout=90)
    for _ in range(60):
        time.sleep(2)
        pid = listener(BACKEND_PORT)
        if not pid:
            continue
        try:
            with op.open("http://127.0.0.1:%d/api/v1/demo/scene" % BACKEND_PORT, timeout=10) as r:
                if r.status == 200:
                    scene = json.loads(r.read().decode("utf-8"))
                    return {"ready": True, "pid": pid, "scene": scene}
        except Exception:
            continue
    return {"ready": False, "ABORT": "BACKEND_NEVER_ANSWERED", "pid": listener(BACKEND_PORT),
            "log_tail": open(log, encoding="utf-8", errors="replace").read()[-800:],
            "err_tail": open(log + ".err", encoding="utf-8", errors="replace").read()[-800:]}


def main():
    out = {"backend_port": BACKEND_PORT, "static_port": STATIC_PORT}
    for p in (BACKEND_PORT, STATIC_PORT):
        out["port_%d_free" % p] = listener(p) is None
    if not all(out["port_%d_free" % p] for p in (BACKEND_PORT, STATIC_PORT)):
        print(json.dumps(out, indent=1))
        raise SystemExit("ABORT_PORT_TAKEN -- not reusing another lane's port")
    out["store"] = fresh_store()
    out["backend"] = boot_backend()
    print(json.dumps(out, indent=1, ensure_ascii=False))
    if not out["backend"].get("ready"):
        raise SystemExit("ABORT_BACKEND_NOT_READY")


if __name__ == "__main__":
    main()