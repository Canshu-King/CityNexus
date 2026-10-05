"""Code-level cross-check of the served bundle, so the screen-name reading does not rest on one browser run.

The phone chain's static door answers again, and at 390x844 the four screens registered by ORD-0567 batch 2
still read "Today" in the top bar while `/v8/trips` correctly reads "Trips".  A browser can be lied to by a
service worker or a stale tab, so this asks the bundle itself: fetch the asset the page actually loaded, find
the registry object the shell uses to decide whether a route is a real screen, and report which of the six
route keys are present.  Independent of the browser, same question.
"""
import json
import os
import re
import urllib.request
from datetime import datetime

LANE = r"D:/moodle/_qoder_phone_ord0485_20260930"
BASE = "http://127.0.0.1:4783"
INDEX_PATH = "/index.html"
ROUTES = ("import", "footprints", "trash", "access", "trips", "hub")
# the shell decides the label from an inline object literal of route names; a minified build keeps the keys
KEY_RE = re.compile(r"[,{]\s*\"?([A-Za-z][A-Za-z0-9_]{2,20})\"?\s*:\s*1\b")


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "cnx-0afdb49b-bundle-check/1",
                                               "Cache-Control": "no-cache"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.status, r.read()


def main():
    status, html = fetch(BASE + INDEX_PATH)
    assets = re.findall(r'src="(/assets/[^"]+\.js)"', html.decode("utf-8", "replace"))
    if not assets:
        raise SystemExit("ABORT_NO_BUNDLE_LINKED status=%s" % status)
    a_status, a_bytes = fetch(BASE + assets[0])
    text = a_bytes.decode("utf-8", "replace")
    keys = set(KEY_RE.findall(text))
    present = {r: r in keys for r in ROUTES}
    windows = []
    for name in ("trips", "import", "trash"):
        m = re.search(r".{80}\b%s\b\s*:\s*1.{80}" % name, text)
        windows.append({"around": name, "found": bool(m), "window": (m.group(0)[:170] if m else "")})
    out = {"schema": "CNX_CHAIN_BUNDLE_REGISTRY_CHECK_V1", "tool": "chain_bundle_registry_check_r1",
           "took_local": datetime.now().astimezone().isoformat(), "index_status": status,
           "index_bytes": len(html), "bundle_src": assets[0], "bundle_status": a_status,
           "bundle_bytes": len(a_bytes), "registry_keys_found": len(keys),
           "route_keys_present": present, "missing_route_keys": sorted(k for k, v in present.items()
                                                                       if not v),
           "context_windows": windows, "served_dist_note": "asked over HTTP with Cache-Control: no-cache",
           "actions_taken": {"restarts": 0, "kills": 0, "rebinds": 0, "writes_to_other_lanes": 0}}
    dest = os.path.join(LANE, "evidence", "chain_bundle_registry_check_r1.json")
    json.dump(out, open(dest, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    print(json.dumps(out, ensure_ascii=False, indent=1))
    print("WROTE " + dest)


if __name__ == "__main__":
    main()
