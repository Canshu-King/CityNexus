"""Private backend launcher r2: same safety as r1, but the export and the private DB are arguments.

The shared preview DB is opened read-only (`mode=ro`) and copied with sqlite's backup API; nothing here
writes to it.  r1 hardcoded an old export, which silently pointed a "fresh" backend at stale code.
Prints the child pid plus the port's netstat owner so port ownership can be proven, not assumed.
Usage: python _launch_priv_backend_r2.py --export <dir> --db <path> --port <n>
"""
import argparse, hashlib, json, os, sqlite3, subprocess, sys, time, urllib.request

SRC = r"D:/moodle/_qoder_preview_20260920/_preview.db"
PY = r"D:/moodle/CityNexus/.venv/Scripts/python.exe"


def netstat_owner(port):
    out = subprocess.run(["netstat", "-ano", "-p", "tcp"], capture_output=True, text=True).stdout
    owners = []
    for line in out.splitlines():
        f = line.split()
        if len(f) >= 5 and f[0].startswith("TCP") and f[3].upper() == "LISTENING" and f[1].endswith(":%d" % port):
            owners.append(f[4])
    return owners


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--export", required=True)
    ap.add_argument("--db", required=True)
    ap.add_argument("--port", type=int, required=True)
    ap.add_argument("--fresh", action="store_true", help="re-copy the private DB even if it already exists")
    ap.add_argument("--resolver", default="off", help="value for CITYNEXUS_ANYWHERE_RESOLVER, e.g. photon")
    a = ap.parse_args()

    if a.fresh and os.path.exists(a.db):
        os.remove(a.db)
    made_backup = False
    if not os.path.exists(a.db):
        src = sqlite3.connect("file:" + SRC + "?mode=ro", uri=True)
        dst = sqlite3.connect(a.db)
        src.backup(dst)
        dst.close()
        src.close()
        made_backup = True

    env = dict(os.environ)
    env["PYTHONPATH"] = a.export
    env["CITYNEXUS_DATABASE_URL"] = "sqlite:///" + a.db.replace("\\", "/")
    env["CITYNEXUS_DEMO_MODE"] = "true"
    # The discovery panel only paints candidates when the anywhere resolver can answer.  With the seam
    # left off, the screen honestly reports "not enough provider facts" and the batch bar is unreachable,
    # which is a stage-configuration limit, not a product defect -- so the seam is settable here.
    if getattr(a, "resolver", "off") != "off":
        env["CITYNEXUS_ANYWHERE_RESOLVER"] = a.resolver
    env.pop("DEEPSEEK_API_KEY", None)
    for k in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"):
        env.pop(k, None)

    log = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_uvicorn_%d.log" % a.port)
    child = subprocess.Popen([PY, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1",
                              "--port", str(a.port)], cwd=os.path.join(a.export, "backend"),
                             env=env, creationflags=0x208,
                             stdout=open(log, "a", encoding="utf-8"), stderr=subprocess.STDOUT)

    op = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    ready, last = False, ""
    for _ in range(45):
        time.sleep(2)
        try:
            r = op.open("http://127.0.0.1:%d/api/v1/demo/scene" % a.port, timeout=10)
            body = r.read()
            last = "%d %dB" % (r.status, len(body))
            if r.status == 200:
                ready = True
                break
        except Exception as e:
            last = type(e).__name__
    owners = netstat_owner(a.port)
    print(json.dumps({
        "port": a.port, "child_pid": child.pid, "ready": ready, "last_probe": last,
        "netstat_owners": owners, "pid_owns_port": str(child.pid) in owners,
        "db": a.db, "db_bytes": os.path.getsize(a.db),
        "db_sha256_head": hashlib.sha256(open(a.db, "rb").read()).hexdigest()[:16],
        "made_readonly_backup": made_backup, "export": a.export, "log": log,
    }, ensure_ascii=False))
    return 0 if ready else 1


if __name__ == "__main__":
    sys.exit(main())
