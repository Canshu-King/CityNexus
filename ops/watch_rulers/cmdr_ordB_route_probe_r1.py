import subprocess, os, time, json, urllib.request

SNAP = "D:/moodle/_qoder_cmdr_backend_live_0350"
env = dict(os.environ)
for k in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"):
    env.pop(k, None)
env["PYTHONPATH"] = SNAP + "/backend"
env["CITYNEXUS_DATABASE_URL"] = "sqlite:///" + SNAP + "/_probe_copy.db"
env["CITYNEXUS_DEMO_MODE"] = "true"
env["CITYNEXUS_AI_ENABLED"] = "false"
env["PYTHONIOENCODING"] = "utf-8"

log = open("D:/moodle/_qoder_cmdr_ref_20260921/live_checks/_probe8795.log", "wb")
p = subprocess.Popen(["D:/moodle/CityNexus/.venv/Scripts/python.exe", "-m", "uvicorn", "app.main:app",
                      "--host", "127.0.0.1", "--port", "8795"],
                     cwd=SNAP + "/backend", env=env, stdout=log, stderr=subprocess.STDOUT)
op = urllib.request.build_opener(urllib.request.ProxyHandler({}))
BASE = "http://127.0.0.1:8795"


def get(path):
    return op.open(BASE + path, timeout=20)


def post(path, obj):
    req = urllib.request.Request(BASE + path, data=json.dumps(obj).encode(),
                                 headers={"Content-Type": "application/json"}, method="POST")
    return op.open(req, timeout=60)


spec = None
for _ in range(45):
    time.sleep(1)
    try:
        spec = json.load(get("/openapi.json"))
        break
    except Exception:
        pass
if spec is None:
    print("NO SPEC - see _probe8795.log")
    p.terminate()
    raise SystemExit

jid = None
try:
    body = json.load(get("/api/v1/journeys"))
    items = body if isinstance(body, list) else (body.get("journeys") or body.get("items") or [])
    if items:
        jid = items[0].get("id") or items[0].get("journey_id")
    print("journeys:", len(items) if isinstance(items, list) else "n/a", "first id:", jid)
except Exception as e:
    print("journeys ERR", str(e)[:120].encode("ascii", "replace").decode())

if jid:
    for payload in ({"city_code": "Guangzhou"}, {"city": "Guangzhou"}, {}):
        try:
            r = post("/api/v1/journeys/%s/real-city/discover" % jid, payload)
            b = r.read().decode("utf-8", "replace")
            print("POST discover", json.dumps(payload), "->", r.status, "bytes", len(b),
                  "| provider_key:", b.count("provider_key"),
                  "| coordinate_system:", b.count("coordinate_system"))
            i = b.find("provider_key")
            print("   ctx:", b[max(0, i - 60):i + 200].encode("ascii", "backslashreplace").decode()[:260])
            break
        except Exception as e:
            print("POST", json.dumps(payload), "ERR", str(e)[:120].encode("ascii", "replace").decode())
else:
    print("NO JOURNEY ID in the copied DB - cannot exercise the route")

p.terminate()
print("terminated")
