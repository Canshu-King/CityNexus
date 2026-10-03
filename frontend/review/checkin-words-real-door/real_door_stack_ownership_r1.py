"""Which bundle and which store the real-door run is answering -- three proofs, one lane.

Same form as this lane's other ownership readings: the entry asset name is taken out of the bytes the
port serves (not from disk), the served asset bytes are compared with the disk file both ways by sha1,
and the listener's own command line is read to see which `--dist` it was started with. The store is
proved by a marker city that exists in no other file, and by asking the same api for the other lanes'
markers and getting zero rows back.
"""
import hashlib
import io
import json
import re
import subprocess
import time
import urllib.request

OUT = ("D:/moodle/_qoder_e766b154_ord0472_20260930/wt/frontend/review/checkin-words-real-door/"
       "receipts/real_door_stack_ownership_r1.json")
DIST = "D:/moodle/_qoder_cmdr_ref_20260921/live_checks/_build_day26e766/frontend/dist"
TIP = "bf4f776b0ba943b88817dfcc0cb3442d75fd9e21"
FRONT, API = 4996, 8794
MARKER = "CNX-DAY26-REAL"
OTHERS = ["CNX-DAY24-ZH", "CNX-DAY24-EN", "CNX-DAY24-FAKE", "CNX-DAY25-MUT"]


def get(url):
    request = urllib.request.Request(url, headers={"User-Agent": "e766b154-realdoor-ownership-r1"})
    with urllib.request.urlopen(request, timeout=25) as response:
        return response.status, response.read()


def sha1(data):
    return hashlib.sha1(data).hexdigest()


def cmd_line(pid):
    ps = ("Get-CimInstance Win32_Process -Filter 'ProcessId=%d' | Select-Object -ExpandProperty "
          "CommandLine" % pid)
    r = subprocess.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=60)
    line = (r.stdout or "").strip()
    return line if r.returncode == 0 and line else "NOT_AVAILABLE_BY_CMDR"


def pids_on(port):
    out = subprocess.run(["netstat", "-ano", "-p", "TCP"], capture_output=True, text=True,
                         encoding="utf-8", errors="replace").stdout
    return [int(l.split()[-1]) for l in out.splitlines()
            if ("127.0.0.1:%d " % port) in l and "LISTENING" in l]


def main():
    status, index_bytes = get("http://127.0.0.1:%d/" % FRONT)
    text = index_bytes.decode("utf-8", "replace")
    asset = (re.search(r"/assets/index-[A-Za-z0-9_-]+\.js", text) or [None])[0]
    with io.open("%s/index.html" % DIST, "rb") as handle:
        disk_index = handle.read()
    _s, served = get("http://127.0.0.1:%d%s" % (FRONT, asset))
    with io.open("%s%s" % (DIST, asset), "rb") as handle:
        disk_asset = handle.read()
    mine = len(json.loads(get("http://127.0.0.1:%d/api/v1/places?city_code=%s"
                              % (API, MARKER))[1].decode("utf-8")))
    others = {}
    for other in OTHERS:
        others[other] = len(json.loads(get("http://127.0.0.1:%d/api/v1/places?city_code=%s"
                                           % (API, other))[1].decode("utf-8")))
    pids = pids_on(FRONT)
    body = {
        "taken_at_local": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "built_from_sha": TIP, "dist": DIST,
        "front": FRONT, "front_http_status": status, "front_pid": pids,
        "api": API, "entry_asset": asset,
        "entry_served_bytes": len(served), "entry_disk_bytes": len(disk_asset),
        "entry_served_sha1": sha1(served), "entry_disk_sha1": sha1(disk_asset),
        "entry_bytes_equal": served == disk_asset, "index_matches_disk": index_bytes == disk_index,
        "marker_city": MARKER, "marker_rows_own": mine, "marker_rows_others": others,
        "front_command_line_proof": cmd_line(pids[0]) if pids else "NOT_AVAILABLE_BY_CMDR",
    }
    body["command_line_names_this_dist"] = body["front_command_line_proof"].replace("\\", "/") \
        .find(DIST) >= 0
    body["every_proof"] = bool(body["entry_bytes_equal"] and body["index_matches_disk"]
                               and body["command_line_names_this_dist"] and mine > 0
                               and all(v == 0 for v in others.values()))
    with io.open(OUT, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(body, handle, indent=1, ensure_ascii=False)
    printable = json.dumps(body, ensure_ascii=False).encode("ascii", "replace").decode("ascii")
    print(printable[:900])
    print("WROTE %s every_proof=%s" % (OUT, body["every_proof"]))
    return 0 if body["every_proof"] else 3


if __name__ == "__main__":
    raise SystemExit(main())
