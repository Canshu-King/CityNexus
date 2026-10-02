"""Which bundle each front is serving for the counter-arm run -- three dists, one store, three proofs.

The mutants are only worth anything if a reader can tell the three screens apart: each bundle has its own
entry asset name (vite hashes by content), so "served entry asset == that dist's disk bytes, sha1 both
ways" is what separates a red caused by the mutation from a red caused by reading the wrong generation.
The third proof is the process command line, which names the `--dist` the listener was started with.
"""
import hashlib
import io
import json
import re
import subprocess
import time
import urllib.request

OUT = ("D:/moodle/_qoder_e766b154_ord0472_20260930/wt/frontend/review/checkin-words-mutants-day25/"
       "receipts/mutant_stack_ownership_r1.json")
BUILD_ROOT = "D:/moodle/_qoder_cmdr_ref_20260921/live_checks"
API = 8793
MARKER = "CNX-DAY25-MUT"
LANES = [
    {"front": 4993, "dist": "%s/_build_day25e766/frontend/dist" % BUILD_ROOT, "generation": "base_tip"},
    {"front": 4994, "dist": "%s/_build_mut1e766/frontend/dist" % BUILD_ROOT,
     "generation": "mutant_M1_mapping_removed"},
    {"front": 4995, "dist": "%s/_build_mut2e766/frontend/dist" % BUILD_ROOT,
     "generation": "mutant_M2_rows_emptied"},
]


def get(url):
    request = urllib.request.Request(url, headers={"User-Agent": "e766b154-mutant-ownership-r1"})
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
    body = {"taken_at_local": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "api_port": API,
            "marker_city": MARKER, "lanes": []}
    for lane in LANES:
        dist = lane["dist"].replace("\\", "/")
        status, index_bytes = get("http://127.0.0.1:%d/" % lane["front"])
        text = index_bytes.decode("utf-8", "replace")
        found = re.search(r"/assets/index-[A-Za-z0-9_-]+\.js", text)
        asset = found.group(0) if found else None
        row = dict(lane)
        row["front_http_status"] = status
        row["front_pid"] = pids_on(lane["front"])
        row["entry_asset"] = asset
        if asset:
            _s, served = get("http://127.0.0.1:%d%s" % (lane["front"], asset))
            with open("%s%s" % (dist, asset), "rb") as handle:
                on_disk = handle.read()
            with open("%s/index.html" % dist, "rb") as handle:
                disk_index = handle.read()
            row.update({"entry_served_bytes": len(served), "entry_disk_bytes": len(on_disk),
                        "entry_served_sha1": sha1(served), "entry_disk_sha1": sha1(on_disk),
                        "entry_bytes_equal": served == on_disk,
                        "index_matches_disk": index_bytes == disk_index})
        _s, payload = get("http://127.0.0.1:%d/api/v1/places?city_code=%s" % (API, MARKER))
        row["marker_rows_on_this_api"] = len(json.loads(payload.decode("utf-8", "replace")))
        row["front_command_line_proof"] = cmd_line(row["front_pid"][0]) if row["front_pid"] \
            else "NOT_AVAILABLE_BY_CMDR"
        row["command_line_names_this_dist"] = row["front_command_line_proof"].replace("\\", "/") \
            .find(dist) >= 0
        body["lanes"].append(row)
        print(repr("front %s gen %s entry %s bytes_equal %s index_equal %s cmd_names_dist %s"
                   % (lane["front"], lane["generation"], asset, row.get("entry_bytes_equal"),
                      row.get("index_matches_disk"), row["command_line_names_this_dist"]))[1:-1])
    body["entry_assets_all_distinct"] = len({r["entry_asset"] for r in body["lanes"]}) == len(body["lanes"])
    body["every_lane_proven"] = all(r.get("entry_bytes_equal") and r.get("index_matches_disk")
                                   and r["command_line_names_this_dist"] for r in body["lanes"])
    with io.open(OUT, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(body, handle, indent=1, ensure_ascii=False)
    print("WROTE %s bytes=%d distinct_entries=%s every_lane_proven=%s"
          % (OUT, len(json.dumps(body, ensure_ascii=False).encode("utf-8")),
             body["entry_assets_all_distinct"], body["every_lane_proven"]))
    return 0 if (body["every_lane_proven"] and body["entry_assets_all_distinct"]) else 3


if __name__ == "__main__":
    raise SystemExit(main())
