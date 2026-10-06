"""Private backend launcher: detached uvicorn on its own port against a private sqlite copy.

Never touches the shared preview DB (opened mode=ro and copied via the backup API). Prints the
child pid so the caller can prove port ownership with netstat.
"""
import subprocess, sys, os, time, json, sqlite3, hashlib, urllib.request

EXPORT = r"D:/moodle/_qoder_cmdr_export_890b7cf"
DB = r"D:/moodle/_qoder_cmdr_priv_890b7cf.db"
SRC = r"D:/moodle/_qoder_preview_20260920/_preview.db"
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8725
PY = r"D:/moodle/CityNexus/.venv/Scripts/python.exe"
LOG = r"D:/moodle/_qoder_cmdr_ref_20260921/live_checks/_uvicorn_%d.log" % PORT

if not os.path.exists(DB):
    src = sqlite3.connect("file:" + SRC + "?mode=ro", uri=True)
    dst = sqlite3.connect(DB)
    src.backup(dst)
    dst.close()
    src.close()

env = dict(os.environ)
env["PYTHONPATH"] = EXPORT
env["CITYNEXUS_DATABASE_URL"] = "sqlite:///" + DB.replace("\\", "/")
env["CITYNEXUS_DEMO_MODE"] = "true"
env.pop("DEEPSEEK_API_KEY", None)
for k in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"):
    env.pop(k, None)

child = subprocess.Popen([PY, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1",
                          "--port", str(PORT)], cwd=os.path.join(EXPORT, "backend"),
                         env=env, creationflags=0x208,
                         stdout=open(LOG, "a", encoding="utf-8"),
                         stderr=subprocess.STDOUT)

ok = False
last = ""
for _ in range(45):
    time.sleep(2)
    try:
        op = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        r = op.open("http://127.0.0.1:%d/api/v1/demo/scene" % PORT, timeout=10)
        body = r.read()
        last = "%d %dB" % (r.status, len(body))
        if r.status == 200:
            ok = True
            break
    except Exception as e:
        last = type(e).__name__
print(json.dumps({"port": PORT, "pid": child.pid, "ready": ok, "last": last,
                  "db": DB, "db_bytes": os.path.getsize(DB),
                  "db_sha256": hashlib.sha256(open(DB, "rb").read()).hexdigest(),
                  "log": LOG}, ensure_ascii=False))
