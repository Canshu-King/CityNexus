"""Which bundle and which store the recycle-bin reading answers from, and the journey id straight from the door.

Three proofs, same form as this lane's other ownership readings: the entry asset name is taken out of the
bytes the port serves, the served asset bytes are compared with that dist's disk file both ways by sha1,
and the listener's own command line names the `--dist` it was started with. The store is proved by a
marker city no other file carries. The journey id is read from `/api/v1/demo/scene` rather than typed, and
the two doors' baseline states are recorded BEFORE anything withdraws anything, so the later
"put it back" claim has something to be compared against.
"""
import hashlib
import io
import json
import re
import subprocess
import time
import urllib.request

EVID = "D:/moodle/_qoder_e766b154_ord0472_20260930/wt/frontend/review/journey-in-bin-real-door"
OUT = "%s/receipts/journey_in_bin_ownership_r1.json" % EVID
DIST = "D:/moodle/_qoder_cmdr_ref_20260921/live_checks/_build_day31e766/frontend/dist"
TIP = "6246876a3b9171f5c2d6ec948f43b35605262bee"
FRONT, API = 4997, 8795
MARKER = "CNX-DAY31-BIN"
OTHERS = ["CNX-DAY24-ZH", "CNX-DAY24-EN", "CNX-DAY24-FAKE", "CNX-DAY25-MUT", "CNX-DAY26-REAL"]


def get(url):
    request = urllib.request.Request(url, headers={"User-Agent": "e766b154-journeyinbin-ownership-r1"})
    with urllib.request.urlopen(request, timeout=30) as response:
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
                         encoding="utf-8", errors="replace", timeout=60).stdout
    return [int(l.split()[-1]) for l in out.splitlines()
            if ("127.0.0.1:%d " % port) in l and "LISTENING" in l]


def main():
    status, index_bytes = get("http://127.0.0.1:%d/" % FRONT)
    text = index_bytes.decode("utf-8", "replace")
    found = re.search(r"/assets/index-[A-Za-z0-9_-]+\.js", text)
    asset = found.group(0) if found else None
    _s, served = get("http://127.0.0.1:%d%s" % (FRONT, asset))
    disk_asset = open("%s%s" % (DIST, asset), "rb").read()
    disk_index = open("%s/index.html" % DIST, "rb").read()
    mine = len(json.loads(get("http://127.0.0.1:%d/api/v1/places?city_code=%s"
                              % (API, MARKER))[1].decode("utf-8")))
    others = {o: len(json.loads(get("http://127.0.0.1:%d/api/v1/places?city_code=%s"
                                    % (API, o))[1].decode("utf-8"))) for o in OTHERS}
    scene = json.loads(get("http://127.0.0.1:%d/api/v1/demo/scene" % API)[1].decode("utf-8"))
    journey = scene.get("journey_id")
    one_status = get("http://127.0.0.1:%d/api/v1/journeys/%s" % (API, journey))[0]
    bin_rows = json.loads(get("http://127.0.0.1:%d/api/v1/recycle-bin/journeys" % API)[1].decode("utf-8"))
    pids = pids_on(FRONT)
    body = {
        "taken_at_local": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "built_from_sha": TIP, "dist": DIST,
        "front": FRONT, "front_http_status": status, "front_pid": pids, "api": API,
        "entry_asset": asset, "entry_served_bytes": len(served), "entry_disk_bytes": len(disk_asset),
        "entry_served_sha1": sha1(served), "entry_disk_sha1": sha1(disk_asset),
        "entry_bytes_equal": served == disk_asset, "index_matches_disk": index_bytes == disk_index,
        "marker_city": MARKER, "marker_rows_own": mine, "marker_rows_others": others,
        "scene_journey_id": journey, "scene_journey_status": scene.get("journey_status"),
        "baseline_read_journey_status": one_status,
        "baseline_recycle_bin_rows": len(bin_rows) if isinstance(bin_rows, list) else -1,
        "baseline_journey_in_bin": bool(isinstance(bin_rows, list)
                                        and any(r.get("id") == journey for r in bin_rows)),
        "front_command_line_proof": cmd_line(pids[0]) if pids else "NOT_AVAILABLE_BY_CMDR",
    }
    body["command_line_names_this_dist"] = body["front_command_line_proof"].replace("\\", "/") \
        .find(DIST) >= 0
    body["every_proof"] = bool(body["entry_bytes_equal"] and body["index_matches_disk"]
                               and body["command_line_names_this_dist"] and mine > 0
                               and all(v == 0 for v in others.values())
                               and body["baseline_read_journey_status"] == 200
                               and body["baseline_journey_in_bin"] is False)
    with io.open(OUT, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(body, handle, indent=1, ensure_ascii=False)
    print(json.dumps({k: v for k, v in body.items() if k != "marker_rows_others"},
                     ensure_ascii=False, indent=1).encode("ascii", "replace").decode("ascii")[:1100])
    print("WROTE %s every_proof=%s" % (OUT, body["every_proof"]))
    return 0 if body["every_proof"] else 3


if __name__ == "__main__":
    raise SystemExit(main())
