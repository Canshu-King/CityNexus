"""前置单 step 1 -- prove what the day15 front (:4783) is actually serving, and which backend its /api
proxy really talks to, before a single reading is attributed to "day15".

Two claims, two readings, both taken from the artifacts rather than from the ledger's prose:

  1. the bundle: the entry asset's name is read out of the served /v8 shell, and the bytes that name
     comes back with are compared to the bytes on disk in the day15 dist -- same for the CSS and for
     index.html itself. An equal pair says "these listeners serve the tree named here"; a 200 on a port
     says nothing of the sort.
  2. the backend behind the proxy: three endpoints are read through the front and directly on each of
     the candidate api ports, and byte-equality across the two is the only thing that can name which
     one answers. Where the readings cannot tell two listeners apart, the cell says so instead of
     picking one.

Nothing here writes, restarts, or opens another lane's database.
"""
import hashlib
import io
import json
import urllib.request

FRONT = 4783
APIS = (4787, 4781, 4785)
DIST = "D:/moodle/_qoder_cmdr_ref_20260921/live_checks/_build_day15/frontend/dist"
PROBE_PATHS = (
    "/api/v1/demo/scene",
    "/api/v1/journeys",
    "/openapi.json",
)


def get(port, path):
    request = urllib.request.Request("http://127.0.0.1:%d%s" % (port, path))
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            return response.status, response.read()
    except Exception as error:  # noqa: BLE001 - a dead or refusing listener is a reading
        return None, repr(error).encode()


def sha1(data):
    return hashlib.sha1(data).hexdigest()


def disk(path):
    with io.open("%s/%s" % (DIST, path), "rb") as handle:
        return handle.read()


def main():
    out = {"bundle": {}, "backend": {}}
    status, index = get(FRONT, "/v8")
    entry = None
    css = None
    if status == 200:
        text = index.decode("utf-8", "replace")
        for token in text.split('"'):
            if token.startswith("/assets/index-") and token.endswith(".js"):
                entry = token
            if token.startswith("/assets/index-") and token.endswith(".css"):
                css = token
    out["bundle"]["served_index_status"] = status
    out["bundle"]["entry_asset_named_by_served_shell"] = entry
    out["bundle"]["css_asset_named_by_served_shell"] = css
    for label, name in (("js", entry), ("css", css), ("index", "index.html")):
        if not name:
            out["bundle"][label] = "NOT_NAMED_BY_THE_SERVED_SHELL"
            continue
        asset_status, served = get(FRONT, name if name.startswith("/") else "/" + name)
        on_disk = disk(name.lstrip("/"))
        out["bundle"][label] = {
            "asset": name,
            "http_status": asset_status,
            "served_sha1": sha1(served),
            "disk_sha1": sha1(on_disk),
            "served_bytes": len(served),
            "disk_bytes": len(on_disk),
            "equal": served == on_disk,
        }

    for path in PROBE_PATHS:
        front_status, front_body = get(FRONT, path)
        row = {
            "front_status": front_status,
            "front_sha1": sha1(front_body),
            "front_bytes": len(front_body),
            "apis": {},
        }
        for port in APIS:
            status, body = get(port, path)
            row["apis"][str(port)] = {
                "http_status": status,
                "sha1": sha1(body),
                "bytes": len(body),
                "equals_front": status is not None and body == front_body,
            }
        matches = [port for port in APIS if row["apis"][str(port)]["equals_front"]]
        row["candidate_backends_by_this_reading"] = matches
        row["naming_power"] = "unique" if len(matches) == 1 else (
            "ambiguous" if len(matches) > 1 else "none_matched"
        )
        out["backend"][path] = row

    print(json.dumps(out, indent=1, ensure_ascii=False))
    with io.open("D:/moodle/_qoder_e766b154_ord0528_20261001/run/day15_stack_proof_r1.json",
                 "w", encoding="utf-8") as handle:
        json.dump(out, handle, indent=1, ensure_ascii=False)

    bundle_ok = all(
        isinstance(v, dict) and v.get("equal") for v in out["bundle"].values() if isinstance(v, dict)
    )
    print("BUNDLE_BYTES_MATCH_DAY15_DIST=%s" % bundle_ok)
    for path, row in out["backend"].items():
        print("  %s naming_power=%s matches=%s" % (path, row["naming_power"], row["candidate_backends_by_this_reading"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
