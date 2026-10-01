"""ORD-0541 lane -- prove which bytes and which database each of the three generation listeners is
actually serving, before any arm is allowed to quote a number from it.

Same three readings per front that ORD-0528 settled on, and the third one is still named when it
cannot be taken:

  1. the entry asset's *name* comes out of the index.html this front serves, and that name is one of
     the files in the dist I built -- not a name I typed in;
  2. the bytes this front hands back for that asset hash to the same value as the bytes on disk, so
     "my bundle" is a byte claim rather than a port claim;
  3. the command line of the process holding the port, which is the only reading that can name the
     `--outDir` it was given. Not readable from the listener itself here, so the cell is written
     `NOT_AVAILABLE_BY_CMDR` and the two proofs above carry the claim.

Per api: a `places` row whose city code exists in no other store, read through the door -- and the
*other two* generations' city codes asked at the same door, which must answer nothing. Three APIs on
three ports answering 200 would prove nothing on their own; a marker that only my file carries does.
"""
import hashlib
import json
import subprocess
import urllib.error
import urllib.request

FRONTS = {
    "4980": ("candidate", "D:/moodle/_qoder_cmdr_ref_20260921/live_checks/_build_ord0541c/frontend/dist"),
    "4981": ("base", "D:/moodle/_qoder_cmdr_ref_20260921/live_checks/_build_ord0541b/frontend/dist"),
    "4982": ("mutant", "D:/moodle/_qoder_cmdr_ref_20260921/live_checks/_build_ord0541m/frontend/dist"),
    # The two fronts the landed orders are re-run against: the same candidate and base bytes, over
    # databases whose trip was lengthened through the product's own write doors, because ORD-0528's S3
    # and ORD-0542's D1 both count day blocks and the seeded trip has one.
    "4983": ("candidate over the lengthened trip", "D:/moodle/_qoder_cmdr_ref_20260921/live_checks/_build_ord0541c/frontend/dist"),
    "4984": ("base over the lengthened trip", "D:/moodle/_qoder_cmdr_ref_20260921/live_checks/_build_ord0541b/frontend/dist"),
}
APIS = {
    "8774": ("candidate", "CNX-ORD0541C"),
    "8775": ("base", "CNX-ORD0541B"),
    "8776": ("mutant", "CNX-ORD0541M"),
    "8777": ("candidate, lengthened trip", "CNX-ORD0541RC"),
    "8778": ("base, lengthened trip", "CNX-ORD0541RB"),
}
ALL_CITIES = ["CNX-ORD0541C", "CNX-ORD0541B", "CNX-ORD0541M", "CNX-ORD0541RC", "CNX-ORD0541RB"]
OUT = "D:/moodle/_qoder_e766b154_ord0528_20261001/run/stack_ord0541.json"


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
        rec = {
            "label": label,
            "dist": dist,
            "index_http_status": status,
            "entry_from_served_index": entry,
            "pid_on_port": listen_pid(port),
            "outDir_third_proof": "NOT_AVAILABLE_BY_CMDR",
        }
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
            rec["index_http_status_of_file_route"] = served_index_status
        report["fronts"][port] = rec

    for port, (label, marker_city) in APIS.items():
        status, body = get("http://127.0.0.1:%s/api/v1/places?city_code=%s" % (port, marker_city))
        mine = []
        if status == 200:
            try:
                mine = [r.get("city_code") for r in json.loads(body)]
            except Exception:  # noqa: BLE001
                mine = ["UNPARSEABLE"]
        others = {}
        for other_city in ALL_CITIES:
            if other_city == marker_city:
                continue
            other_status, other_body = get(
                "http://127.0.0.1:%s/api/v1/places?city_code=%s" % (port, other_city)
            )
            others[other_city] = {
                "http_status": other_status,
                "rows": len(json.loads(other_body)) if other_status == 200 else None,
            }
        report["apis"][port] = {
            "label": label,
            "marker_city": marker_city,
            "marker_http_status": status,
            "marker_rows": len(mine),
            "marker_row_city_codes": sorted(set(mine)),
            "other_generations_markers": others,
            "pid_on_port": listen_pid(port),
        }
    with open(OUT, "w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2, ensure_ascii=False)
    print(json.dumps(report, indent=2, ensure_ascii=False))

    fronts_ok = all(
        f.get("bytes_equal") and f.get("index_bytes_equal") and f.get("entry_from_served_index")
        for f in report["fronts"].values()
    )
    apis_ok = all(
        a["marker_rows"] == 1 and all(o["rows"] in (0, None) for o in a["other_generations_markers"].values())
        for a in report["apis"].values()
    )
    print("FRONTS_OWNED=%s APIS_OWNED=%s" % (fronts_ok, apis_ok))
    return 0 if (fronts_ok and apis_ok) else 1


if __name__ == "__main__":
    raise SystemExit(main())
