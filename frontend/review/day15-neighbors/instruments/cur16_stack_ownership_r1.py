"""当前线重跑 -- prove which bytes and which store each of the four neighbour listeners is serving.

Four fronts, one bundle (`_build_cur16`, archived from the authoritative tip the 包工头 named), and four
databases, one per neighbour, each carrying a `places` row whose city code exists in no other store.

Two readings per front, both taken from the artifact rather than from a port number: the entry asset's
*name* comes out of the served /v8 shell, and the bytes that name returns are compared to the bytes on
disk. Per api: my own marker city answers one row, and the other three neighbours' cities answer none.
The third proof a listener can be given -- the `--outDir` in its command line -- is named
`NOT_AVAILABLE_BY_CMDR` here too, because this proxy takes a `--dist` and does not echo it as an outDir.
"""
import hashlib
import io
import json
import subprocess
import sys
import urllib.error
import urllib.request

DIST = "D:/moodle/_qoder_cmdr_ref_20260921/live_checks/_build_cur16/frontend/dist"
FRONTS = {
    "4985": "ORD-0502 phone mainline",
    "4986": "ORD-0497 footprints on map",
    "4987": "ORD-0530 footprints by day",
    "4988": "ORD-0537 map toggle reach",
}
APIS = {
    "8780": ("ORD-0502 phone mainline", "CNX-CUR16-502"),
    "8781": ("ORD-0497 footprints on map", "CNX-CUR16-497"),
    "8782": ("ORD-0530 footprints by day", "CNX-CUR16-530"),
    "8783": ("ORD-0537 map toggle reach", "CNX-CUR16-537"),
}
ALL_CITIES = [city for _label, city in APIS.values()]
OUT = "D:/moodle/_qoder_e766b154_ord0472_20260930/wt/frontend/review/day15-neighbors/receipts/cur16_stack_ownership_r1.json"


def get(port, path):
    try:
        with urllib.request.urlopen("http://127.0.0.1:%d%s" % (int(port), path), timeout=20) as response:
            return response.status, response.read()
    except urllib.error.HTTPError as error:
        return error.code, error.read()
    except Exception as error:  # noqa: BLE001 - a dead listener is a reading, not a crash
        return None, repr(error).encode()


def listen_pid(port):
    out = subprocess.run(["netstat", "-ano", "-p", "TCP"], capture_output=True, text=True,
                         encoding="utf-8", errors="replace").stdout
    pids = []
    for line in out.splitlines():
        parts = [token for token in line.split() if token]
        if len(parts) >= 5 and parts[1] == "127.0.0.1:%s" % port and parts[3] == "LISTENING":
            pids.append(parts[4])
    return pids


def main():
    report = {"bundle_built_from_tip": "00b5f25e9b6b408fba8906ef3ffd49caa5eb84b9", "fronts": {}, "apis": {}}
    for port, label in FRONTS.items():
        status, shell = get(port, "/v8")
        entry = None
        for token in shell.decode("utf-8", "replace").split('"'):
            if token.startswith("/assets/index-") and token.endswith(".js"):
                entry = token
                break
        record = {
            "neighbour": label,
            "shell_http_status": status,
            "entry_from_served_shell": entry,
            "listeners_on_port": listen_pid(port),
            "outDir_third_proof": "NOT_AVAILABLE_BY_CMDR",
        }
        asset_status, served = get(port, entry or "/")
        with io.open("%s%s" % (DIST, entry or ""), "rb") as handle:
            on_disk = handle.read()
        record["asset_http_status"] = asset_status
        record["served_asset_bytes"] = len(served)
        record["disk_asset_bytes"] = len(on_disk)
        record["served_sha1"] = hashlib.sha1(served).hexdigest()
        record["disk_sha1"] = hashlib.sha1(on_disk).hexdigest()
        record["bytes_equal"] = bool(entry) and served == on_disk
        index_status, index_served = get(port, "/index.html")
        with io.open("%s/index.html" % DIST, "rb") as handle:
            record["index_bytes_equal"] = index_served == handle.read()
        report["fronts"][port] = record

    for port, (label, city) in APIS.items():
        status, body = get(port, "/api/v1/places?city_code=%s" % city)
        mine = []
        if status == 200:
            try:
                mine = json.loads(body)
            except ValueError:
                mine = ["UNPARSEABLE"]
        others = {}
        for other in ALL_CITIES:
            if other == city:
                continue
            other_status, other_body = get(port, "/api/v1/places?city_code=%s" % other)
            others[other] = {
                "http_status": other_status,
                "rows": len(json.loads(other_body)) if other_status == 200 else None,
            }
        report["apis"][port] = {
            "neighbour": label,
            "marker_city": city,
            "marker_http_status": status,
            "marker_rows": len(mine),
            "other_neighbours_markers": others,
            "listeners_on_port": listen_pid(port),
        }

    with io.open(OUT, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(report, handle, indent=1, ensure_ascii=False)

    fronts_ok = all(f["bytes_equal"] and f["index_bytes_equal"] and f["entry_from_served_shell"]
                    for f in report["fronts"].values())
    single_listener = all(len(f["listeners_on_port"]) == 1 for f in report["fronts"].values())
    apis_ok = all(
        a["marker_rows"] == 1 and all(o["rows"] == 0 for o in a["other_neighbours_markers"].values())
        for a in report["apis"].values()
    )
    print("CUR16_OWNERSHIP fronts_bytes=%s one_listener_per_port=%s apis_marker_only=%s"
          % (fronts_ok, single_listener, apis_ok))
    for port, record in sorted(report["fronts"].items()):
        print("  front %s entry=%s served_bytes=%d equal=%s"
              % (port, record["entry_from_served_shell"], record["served_asset_bytes"], record["bytes_equal"]))
    print("WROTE %s" % OUT)
    return 0 if (fronts_ok and single_listener and apis_ok) else 1


if __name__ == "__main__":
    sys.exit(main())
