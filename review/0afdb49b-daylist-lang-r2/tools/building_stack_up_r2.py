"""Same job as building_stack_up_r1.py, pointed at a tree handed to it instead of a hardcoded one.

r1 hardcodes TREE = build_walk, and that tree no longer exists on disk, so calling it now aborts for a
reason that has nothing to do with the walk.  Instrument paths are never rewritten (standing ruling), so
this is a new generation whose only real change is that --tree is required and the ports it may bind are
checked against the listener table before anything starts.

The shared preview DB is opened READ-ONLY and copied with sqlite's backup(): every step of this walk taps
things, and a shared file would let one run's stamps decide the next run's first answer.  The shared file
is re-stat'ed after the copy so the receipt can prove it was never written to.

AI is off on purpose: the walk asks whether a person can finish the flow, not whether a provider answers.
"""
import argparse
import json
import os
import sqlite3
import subprocess
import time
import urllib.request

LANE = r"D:/moodle/_qoder_phone_ord0485_20260930"
PY = r"D:/moodle/CityNexus/.venv/Scripts/python.exe"
SHARED = r"D:\moodle\_qoder_preview_20260920\_preview.db"
op = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def listener(port):
    out = subprocess.run(["netstat", "-ano", "-p tcp"], stdout=subprocess.PIPE,
                         timeout=30).stdout
    for line in out.decode("gbk", errors="replace").splitlines():
        q = line.split()
        if len(q) >= 5 and q[0].upper() == "TCP" and q[1].endswith(":%d" % port) \
                and q[3].upper() == "LISTENING":
            return q[4]
    return None


def fresh_store(db):
    for suffix in ("", "-wal", "-shm"):
        p = db + suffix
        if os.path.exists(p):
            try:
                os.remove(p)
            except OSError:
                time.sleep(1)
                os.remove(p)
    before = os.stat(SHARED)
    src = sqlite3.connect("file:" + SHARED.replace("\\", "/") + "?mode=ro", uri=True)
    dst = sqlite3.connect(db)
    src.backup(dst)
    dst.close()
    src.close()
    after = os.stat(SHARED)
    con = sqlite3.connect(db)
    tables = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    counts = {}
    for t in ("journeys", "places", "journey_stops", "journey_checkins", "plans"):
        if t in tables:
            counts[t] = con.execute("SELECT COUNT(*) FROM %s" % t).fetchone()[0]
    con.close()
    return {"shared_bytes_before": before.st_size, "shared_mtime_before": before.st_mtime,
            "shared_bytes_after": after.st_size, "shared_mtime_after": after.st_mtime,
            "shared_untouched": (before.st_size == after.st_size and before.st_mtime == after.st_mtime),
            "private_store_bytes": os.path.getsize(db), "counts": counts}


def boot_backend(tree, db, port, tag):
    log = os.path.join(LANE, "run", "walk_backend_%s.log" % tag)
    open(log, "ab").close()
    ps = ("$env:HTTP_PROXY=''; $env:HTTPS_PROXY=''; $env:DEEPSEEK_API_KEY=''; "
          "$env:PYTHONPATH='%s'; $env:CITYNEXUS_DATABASE_URL='sqlite:///%s'; "
          "$env:CITYNEXUS_DEMO_MODE='true'; $env:CITYNEXUS_AI_ENABLED='false'; "
          "Start-Process -FilePath '%s' -ArgumentList '-m','uvicorn','app.main:app',"
          "'--host','127.0.0.1','--port','%d' -WorkingDirectory '%s' -WindowStyle Hidden "
          "-RedirectStandardOutput '%s' -RedirectStandardError '%s'"
          % (tree, db.replace("\\", "/"), PY, port, os.path.join(tree, "backend"), log, log + ".err"))
    with open(os.path.join(LANE, "run", "walk_launcher.log"), "ab") as sink:
        subprocess.run(["powershell", "-NoProfile", "-Command", ps], stdout=sink, stderr=sink,
                       timeout=90)
    for _ in range(45):
        time.sleep(2)
        pid = listener(port)
        if not pid:
            continue
        try:
            with op.open("http://127.0.0.1:%d/api/v1/demo/scene" % port, timeout=10) as r:
                if r.status == 200:
                    return {"ready": True, "pid": pid,
                            "scene": json.loads(r.read().decode("utf-8"))}
        except Exception:
            continue
    return {"ready": False, "ABORT": "BACKEND_NEVER_ANSWERED", "pid": listener(port),
            "err_tail": open(log + ".err", encoding="utf-8", errors="replace").read()[-900:]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tree", required=True)
    ap.add_argument("--backend-port", type=int, required=True)
    ap.add_argument("--db", required=True)
    ap.add_argument("--tag", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    tree = os.path.abspath(a.tree)
    if not os.path.isdir(os.path.join(tree, "backend")):
        raise SystemExit("ABORT_TREE_INCOMPLETE -- no backend/ under " + tree)
    out = {"tree": tree, "backend_port": a.backend_port, "started": time.strftime("%F %T")}
    out["port_free"] = listener(a.backend_port) is None
    if not out["port_free"]:
        raise SystemExit("ABORT_PORT_TAKEN pid=%s -- not reusing another lane's port"
                         % listener(a.backend_port))
    out["store"] = fresh_store(a.db)
    if not out["store"]["shared_untouched"]:
        raise SystemExit("ABORT_SHARED_DB_MOVED -- the read-only open did not stay read-only")
    out["backend"] = boot_backend(tree, a.db, a.backend_port, a.tag)
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    with open(a.out, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1, ensure_ascii=False)
    print(json.dumps(out, indent=1, ensure_ascii=False))
    if not out["backend"].get("ready"):
        raise SystemExit("ABORT_BACKEND_NOT_READY")


if __name__ == "__main__":
    main()
