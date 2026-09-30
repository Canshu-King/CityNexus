"""ORD-0528 lane -- prove which bytes and which database each listener is actually serving.

Three readings per front, and the third one is named when it cannot be taken:

  1. the entry asset's *name* comes out of the index.html this front serves, and that name is one of
     the files in the dist I built -- not a name I typed in;
  2. the bytes this front hands back for that asset hash to the same value as the bytes on disk
     (`sha1` of the served body vs the file), so "my bundle" is a byte claim and not a port claim;
  3. the command line of the process holding the port, which is the only reading that can name the
     `--outDir` it was given. On this instrument it cannot be read from the listener itself, so the
     cell is written `NOT_AVAILABLE_BY_CMDR` and the two proofs above carry the claim.

Per api: a `places` row whose city code exists in no other store, read through the door -- which
answers "this listener is reading *my* file", not "something answered 200".
"""
import hashlib
import json
import subprocess
import sys
import urllib.error
import urllib.request

FRONTS = {
    "4974": ("candidate", "D:/moodle/_qoder_cmdr_ref_20260921/live_checks/_build_ord0528r2/frontend/dist"),
    "4975": ("base", "D:/moodle/_qoder_cmdr_ref_20260921/live_checks/_build_ord0528r2base/frontend/dist"),
    "4976": ("mutant-x2", "D:/moodle/_qoder_cmdr_ref_20260921/live_checks/_build_ord0528r2x2/frontend/dist"),
}
APIS = {"8770": ("candidate db", "CNX-ORD0528"), "8771": ("base db", "CNX-ORD0528B")}
OUT = "D:/moodle/_qoder_e766b154_ord0528_20261001/run/stack_r2.json"


def get(url):
    try:
        with urllib.request.urlopen(url, timeout=15) as response:
            return response.status, response.read()
    except urllib.error.HTTPError as error:
        return error.code, error.read()
    except Exception as error:  # noqa: BLE001 - a dead listener is a reading, not a crash
        return None, repr(error).encode()


def sha1(data):
    return hashlib.sha1(data).hexdigest()


def listen_pid(port):
    """netstat, read the way the runbook says: only a LISTENING line on this exact address counts."""
    out = subprocess.run(
        ["netstat", "-ano", "-p", "TCP"], capture_output=True, text=True, encoding="utf-8", errors="replace"
    ).stdout
    for line in out.splitlines():
        parts = line.split()
        if len(parts) >= 5 and parts[1] == "127.0.0.1:%s" % port and parts[3] == "LISTENING":
            return parts[4]
    return None


def main():
    report = {"fronts": {}, "apis": {}}
    for port, (label, dist) in FRONTS.items():
        status, body = get("http://127.0.0.1:%s/v8/" % port)
        entry = None
        if status == 200:
            text = body.decode("utf-8", "replace")
            for token in text.split('"'):
                if token.startswith("/assets/index-") and token.endswith(".js"):
                    entry = token
                    break
        rec = {"label": label, "dist": dist, "index_http_status": status, "entry_from_served_index": entry,
               "pid_on_port": listen_pid(port), "outDir_third_proof": "NOT_AVAILABLE_BY_CMDR"}
        if entry:
            served_status, served = get("http://127.0.0.1:%s%s" % (port, entry))
            with open("%s%s" % (dist, entry), "rb") as handle:
                on_disk = handle.read()
            rec["asset_http_status"] = served_status
            rec["served_asset_sha1"] = sha1(served)
            rec["disk_asset_sha1"] = sha1(on_disk)
            rec["served_asset_bytes"] = len(served)
            rec["disk_asset_bytes"] = len(on_disk)
            rec["bytes_equal"] = served == on_disk
        served_index_status, served_index = get("http://127.0.0.1:%s/index.html" % port)
        with open("%s/index.html" % dist, "rb") as handle:
            rec["index_bytes_equal"] = served_index == handle.read()
        report["fronts"][port] = rec
    for port, (label, marker_city) in APIS.items():
        status, body = get(
            "http://127.0.0.1:%s/api/v1/places?city_code=%s" % (port, marker_city)
        )
        rows = []
        if status == 200:
            try:
                rows = [r.get("city_code") for r in json.loads(body)]
            except Exception:  # noqa: BLE001
                rows = ["UNPARSEABLE"]
        other_city = "CNX-ORD0528B" if marker_city == "CNX-ORD0528" else "CNX-ORD0528"
        other_status, other_body = get(
            "http://127.0.0.1:%s/api/v1/places?city_code=%s" % (port, other_city)
        )
        other_rows = json.loads(other_body) if other_status == 200 else []
        report["apis"][port] = {
            "label": label,
            "marker_city": marker_city,
            "marker_http_status": status,
            "marker_rows": len(rows),
            "other_lanes_marker_rows": len(other_rows),
            "pid_on_port": listen_pid(port),
        }
    with open(OUT, "w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2, ensure_ascii=False)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    ok = all(f.get("bytes_equal") and f.get("index_bytes_equal") for f in report["fronts"].values())
    ok = ok and all(a["marker_rows"] == 1 and a["other_lanes_marker_rows"] == 0 for a in report["apis"].values())
    print("STACK_OWNERSHIP=%s" % ("GREEN" if ok else "RED"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
