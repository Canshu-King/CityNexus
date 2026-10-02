"""day24 lane stack ownership -- which bundle and which store each of my three fronts is answering.

Three proofs, taken in one run, per the standing form for a self-started static door:
  1. the entry asset name is taken out of the bytes the port serves (not from disk), then that asset is
     fetched and its served bytes compared with the disk file, sha1 both ways;
  2. the api behind each front answers a marker city that exists in no other store, and answers zero rows
     for the other two markers -- so "which file answered" is a reading, not a hope;
  3. the process command line, if Windows will hand it over; when it will not, the cell is named
     NOT_AVAILABLE_BY_CMDR rather than skipped.

Read-only against the stores (no SQL from here at all -- the doors do the talking), 0 processes started or
stopped by this file, and the commander's :4783/:4787 are only named as "not mine", never queried.
"""
import hashlib
import io
import json
import re
import subprocess
import time
import urllib.request

OUT = ("D:/moodle/_qoder_e766b154_ord0472_20260930/wt/frontend/review/checkin-words-day24/"
       "receipts/day24_stack_ownership_r1.json")
DIST = ("D:/moodle/_qoder_cmdr_ref_20260921/live_checks/_build_day24e766/frontend/dist")
TIP = "4fac49f371da0820393d038700bddddafd1176d1"
LANES = [
    {"front": 4990, "api": 8790, "store": "day24_zh_real", "marker": "CNX-DAY24-ZH", "purpose": "real zh"},
    {"front": 4991, "api": 8791, "store": "day24_en_real", "marker": "CNX-DAY24-EN", "purpose": "real en"},
    {"front": 4992, "api": 8792, "store": "day24_words_fake", "marker": "CNX-DAY24-FAKE",
     "purpose": "intercepted states"},
]


def get(url):
    request = urllib.request.Request(url, headers={"User-Agent": "e766b154-ownership-r1"})
    with urllib.request.urlopen(request, timeout=25) as response:
        return response.status, response.read(), response.headers.get("content-type")


def safe(value):
    return str(value).encode("ascii", "replace").decode("ascii")


def sha1(data):
    return hashlib.sha1(data).hexdigest()


def disk(name):
    with open("%s/%s" % (DIST, name.lstrip("/")), "rb") as handle:
        return handle.read()


def cmd_line(pid):
    ps = ("Get-CimInstance Win32_Process -Filter 'ProcessId=%d' | Select-Object -ExpandProperty "
          "CommandLine" % pid)
    result = subprocess.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True,
                            text=True, encoding="utf-8", errors="replace", timeout=60)
    line = (result.stdout or "").strip()
    return line if result.returncode == 0 and line else "NOT_AVAILABLE_BY_CMDR"


def pids_on(port):
    out = subprocess.run(["netstat", "-ano", "-p", "TCP"], capture_output=True, text=True,
                         encoding="utf-8", errors="replace").stdout
    found = []
    for line in out.splitlines():
        if ("127.0.0.1:%d " % port) in line and "LISTENING" in line:
            found.append(int(line.split()[-1]))
    return found


def main():
    body = {"taken_at_local": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "built_from_sha": TIP,
            "dist": DIST, "lanes": []}
    for lane in LANES:
        status, index_bytes, _ct = get("http://127.0.0.1:%d/" % lane["front"])
        text = index_bytes.decode("utf-8", "replace")
        entry = re.search(r"/assets/index-[A-Za-z0-9_-]+\.js", text)
        asset = entry.group(0) if entry else None
        row = dict(lane)
        row.update({"front_http_status": status, "front_pid": pids_on(lane["front"]),
                    "served_index_bytes": len(index_bytes),
                    "index_matches_disk": None, "entry_asset": asset,
                    "entry_served_bytes": None, "entry_disk_bytes": None,
                    "entry_served_sha1": None, "entry_disk_sha1": None})
        if asset:
            row["index_matches_disk"] = index_bytes == disk("index.html")
            _s, served, _c = get("http://127.0.0.1:%d%s" % (lane["front"], asset))
            on_disk = disk(asset)
            row.update({"entry_served_bytes": len(served), "entry_disk_bytes": len(on_disk),
                        "entry_served_sha1": sha1(served), "entry_disk_sha1": sha1(on_disk),
                        "entry_bytes_equal": served == on_disk})
        rows_own = get("http://127.0.0.1:%d/api/v1/places?city_code=%s"
                       % (lane["api"], lane["marker"]))[1]
        row["marker_rows_own"] = len(json.loads(rows_own.decode("utf-8", "replace")))
        others = {}
        for other in LANES:
            if other["marker"] == lane["marker"]:
                continue
            payload = get("http://127.0.0.1:%d/api/v1/places?city_code=%s"
                          % (lane["api"], other["marker"]))[1]
            others[other["marker"]] = len(json.loads(payload.decode("utf-8", "replace")))
        row["marker_rows_others"] = others
        scene = get("http://127.0.0.1:%d/api/v1/demo/scene" % lane["api"])[1]
        row["scene_journey_id"] = json.loads(scene.decode("utf-8", "replace")).get("journey_id")
        row["front_command_line_proof"] = cmd_line(row["front_pid"][0]) if row["front_pid"] \
            else "NOT_AVAILABLE_BY_CMDR"
        body["lanes"].append(row)
        print(safe("front %s api %s entry %s bytes_equal=%s index_matches_disk=%s marker_own=%s "
                   "others=%s" % (lane["front"], lane["api"], asset, row["entry_bytes_equal"],
                                  row["index_matches_disk"], row["marker_rows_own"], others)))
        print(safe("   cmd %s" % str(row["front_command_line_proof"])[:200]))

    body["all_lanes_distinct_markers"] = len({r["marker_rows_own"] for r in body["lanes"]}) > 0
    body["every_lane_proven"] = all(r["entry_bytes_equal"] and r["index_matches_disk"] and
                                   r["marker_rows_own"] > 0 and
                                   all(v == 0 for v in r["marker_rows_others"].values())
                                   for r in body["lanes"])
    with io.open(OUT, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(body, handle, indent=1, ensure_ascii=False)
    print("WROTE %s bytes=%d every_lane_proven=%s"
          % (OUT, len(json.dumps(body, ensure_ascii=False).encode("utf-8")), body["every_lane_proven"]))
    return 0 if body["every_lane_proven"] else 3


if __name__ == "__main__":
    raise SystemExit(main())
