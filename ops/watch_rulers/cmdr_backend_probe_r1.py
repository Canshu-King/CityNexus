import subprocess, sys, os, time, urllib.request, pathlib

SNAP = pathlib.PurePath("D:/moodle/_qoder_cmdr_backend_live_0350")
HERE = pathlib.PurePath("D:/moodle/_qoder_cmdr_ref_20260921/live_checks")
PORT = "8793"

env = dict(os.environ)
for k in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"):
    env.pop(k, None)
env["PYTHONPATH"] = str(SNAP / "backend")
env["CITYNEXUS_DATABASE_URL"] = "sqlite:///" + str(SNAP / "_probe_copy.db")

log = open(str(HERE / "_probe8793b.log"), "wb")
p = subprocess.Popen(["D:/moodle/CityNexus/.venv/Scripts/python.exe", "-m", "uvicorn", "app.main:app",
                      "--host", "127.0.0.1", "--port", PORT],
                     cwd=str(SNAP), env=env, stdout=log, stderr=subprocess.STDOUT)
op = urllib.request.build_opener(urllib.request.ProxyHandler({}))
res = None
last = ""
for _ in range(45):
    time.sleep(1.0)
    if p.poll() is not None:
        res = "DIED rc=%s" % p.poll()
        break
    try:
        r = op.open("http://127.0.0.1:%s/health" % PORT, timeout=3)
        res = "HTTP %s %s" % (r.status, r.read()[:60].decode("utf-8", "replace"))
        break
    except Exception as e:
        last = str(e)[:70]
else:
    res = "TIMEOUT " + last
print("PROBE:", res.encode("ascii", "replace").decode())

for url in ("/api/v1/discovery/real-city?city=Guangzhou",
            "/api/v1/discovery/real-city?city=Xiamen"):
    try:
        r = op.open("http://127.0.0.1:%s%s" % (PORT, url), timeout=15)
        body = r.read().decode("utf-8", "replace")
        i = body.find("provider_key")
        print("GET", url.split("?")[1], "->", r.status, "bytes", len(body),
              "| provider_key:", "provider_key" in body,
              "| coordinate_system:", "coordinate_system" in body)
        print("   ctx:", body[max(0, i - 40):i + 140].encode("ascii", "backslashreplace").decode()[:220])
    except Exception as e:
        print("GET", url, "ERR", str(e)[:140].encode("ascii", "replace").decode())

p.terminate()
print("terminated")
