"""ORD-0515 re-run lane -- prove which bytes and which database each listener is standing on.

Same three readings the poster family always uses, and the third is named when it cannot be taken:

  1. the entry asset's *name* is taken from the index.html this front serves, not typed here;
  2. the bytes served for that asset hash the same as the bytes on disk in the dist I built, so
     "this front serves the generation I claim" is a byte claim;
  3. the `--outDir` the proxy was given -- this instrument cannot read it off the listener, so the
     cell is written NOT_AVAILABLE_BY_CMDR rather than inferred.

Per api: the marker `places` row that exists in no other store answers through the door, which is how
":8770 is the one-day trip and :8771 is the seven-day one" is a reading and not a guess. The
`day_count` is read from the server's own projection, never counted here.
"""
import hashlib
import json
import subprocess
import sys
import urllib.error
import urllib.request

FRONTS = {
    "4974": ("SHORT / this line's bundle / unlengthened trip",
             "D:/moodle/_qoder_cmdr_ref_20260921/live_checks/_build_ord0515now/frontend/dist", "8770"),
    "4975": ("LONG / this line's bundle / seven-day trip",
             "D:/moodle/_qoder_cmdr_ref_20260921/live_checks/_build_ord0515now/frontend/dist", "8771"),
    "4976": ("UNBOUNDED / pre-bound bundle / same seven-day trip",
             "D:/moodle/_qoder_cmdr_ref_20260921/live_checks/_build_ord0515unb/frontend/dist", "8771"),
    "4977": ("WRITTEN / this line's bundle / two-day trip",
             "D:/moodle/_qoder_cmdr_ref_20260921/live_checks/_build_ord0515now/frontend/dist", "8772"),
}
JOURNEY = "22222222-2222-4222-8222-222222222222"
MARKER = "CNX-ORD0515RE"
OUT = sys.argv[1]


def get(url):
    try:
        with urllib.request.urlopen(url, timeout=20) as response:
            return response.status, response.read()
    except urllib.error.HTTPError as error:
        return error.code, error.read()
    except Exception as error:  # noqa: BLE001
        return None, repr(error).encode()


def listen_pid(port):
    out = subprocess.run(["netstat", "-ano", "-p", "TCP"], capture_output=True, text=True,
                         encoding="utf-8", errors="replace", timeout=60).stdout
    for line in out.splitlines():
        parts = line.split()
        if len(parts) >= 5 and parts[1] == "127.0.0.1:%s" % port and parts[3] == "LISTENING":
            return parts[4]
    return None


def sha1(data):
    return hashlib.sha1(data).hexdigest()


report = {"fronts": {}, "apis": {}}
for port, (label, dist, api) in FRONTS.items():
    status, body = get("http://127.0.0.1:%s/v8/" % port)
    entry = None
    if status == 200:
        text = body.decode("utf-8", "replace")
        entry = next((tok for tok in text.split('"')
                      if tok.startswith("/assets/index-") and tok.endswith(".js")), None)
    rec = {"label": label, "dist": dist, "index_http_status": status,
           "entry_from_served_index": entry, "pid_on_port": listen_pid(port),
           "outDir_third_proof": "NOT_AVAILABLE_BY_CMDR"}
    if entry:
        served_status, served = get("http://127.0.0.1:%s%s" % (port, entry))
        with open("%s%s" % (dist, entry), "rb") as handle:
            on_disk = handle.read()
        rec.update({"asset_http_status": served_status, "served_asset_sha1": sha1(served),
                    "disk_asset_sha1": sha1(on_disk), "served_asset_bytes": len(served),
                    "disk_asset_bytes": len(on_disk), "bytes_equal": served == on_disk})
    report["fronts"][port] = rec

for api in ("8770", "8771", "8772"):
    status, body = get("http://127.0.0.1:%s/api/v1/places?city_code=%s" % (api, MARKER))
    rows = len(json.loads(body)) if status == 200 else None
    estatus, ebody = get("http://127.0.0.1:%s/api/v1/journeys/%s/experience" % (api, JOURNEY))
    payload = json.loads(ebody) if estatus == 200 else {}
    report["apis"][api] = {
        "marker_http_status": status, "marker_rows": rows, "pid_on_port": listen_pid(api),
        "experience_http_status": estatus,
        "server_day_count": (payload.get("journey") or {}).get("temporal_shape", {}).get("day_count"),
        "activity_rows": len((payload.get("active_plan") or {}).get("activities") or []),
    }

with open(OUT, "w", encoding="utf-8", newline="\n") as handle:
    json.dump(report, handle, indent=1, ensure_ascii=False)
print(json.dumps(report, indent=1, ensure_ascii=False))
ok = all(f.get("bytes_equal") for f in report["fronts"].values())
ok = ok and all(a["marker_rows"] == 1 for a in report["apis"].values())
print("STACK_OWNERSHIP=%s" % ("GREEN" if ok else "RED"))
sys.exit(0 if ok else 1)
