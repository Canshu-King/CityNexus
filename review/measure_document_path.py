"""Measure the production-build document path so ORD-0036 (c) can quote a number instead
of picking one.

What this measures: loopback latency of the shipped bundle behind `vite preview`, cold and
warm, plus the same document through the preview's /api proxy.  What it does NOT measure:
a mobile carrier path or a public tunnel -- recorded as a limitation next to the value.
"""

import json
import statistics
import time
import urllib.error
import urllib.request

BACKEND = "http://127.0.0.1:8360"
FRONT = "http://127.0.0.1:4199"


def get(url, timeout=30):
    started = time.perf_counter()
    with urllib.request.urlopen(url, timeout=timeout) as response:
        body = response.read()
        status = response.status
    return status, len(body), (time.perf_counter() - started) * 1000, body


def wait_for(url, tries=60):
    for _ in range(tries):
        try:
            get(url, timeout=5)
            return True
        except Exception:
            time.sleep(0.5)
    return False


def post(url, payload=None):
    data = json.dumps(payload or {}).encode()
    request = urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/json"}, method="POST"
    )
    started = time.perf_counter()
    with urllib.request.urlopen(request, timeout=120) as response:
        body = response.read()
        status = response.status
    return status, (time.perf_counter() - started) * 1000, body


def stats(samples):
    ordered = sorted(samples)
    pick = lambda fraction: ordered[min(len(ordered) - 1, int(fraction * len(ordered)))]
    return {
        "n": len(ordered),
        "min_ms": round(ordered[0], 1),
        "p50_ms": round(pick(0.5), 1),
        "p95_ms": round(pick(0.95), 1),
        "max_ms": round(ordered[-1], 1),
    }


report = {"backend_up": wait_for(f"{BACKEND}/api/v1/health"), "preview_up": wait_for(f"{FRONT}/v8/live")}
if not (report["backend_up"] and report["preview_up"]):
    print(json.dumps(report, indent=2))
    raise SystemExit("servers never came up")

report["health"] = get(f"{BACKEND}/api/v1/health")[3].decode("utf-8", "replace")[:200]
status, ms, body = post(f"{BACKEND}/api/v1/demo/reset")
report["demo_reset"] = {"status": status, "ms": round(ms, 1), "bytes": len(body)}

document = f"{FRONT}/v8/live"
cold = []
warm = []
for index in range(15):
    hit = get(document)
    (cold if index == 0 else warm).append(hit[2])
    if index == 0:
        # The first response primes the preview's own file cache; sample the rest as warm.
        warm.append(get(document)[2])

report["document_cold_first_byte"] = round(cold[0], 1)
report["document_warm"] = stats(warm)

# The proxied API path is what a slow link really pays for on every screen.
api = []
for _ in range(10):
    api.append(get(f"{FRONT}/api/v1/health")[2])
report["api_through_preview_proxy"] = stats(api)

# And the heaviest read the shell makes before it can paint anything.  A 4xx is a valid
# answer to time; urlopen raises on it, so record the code instead of dying here.
try:
    journeys = get(f"{FRONT}/api/v1/journeys")
    report["journeys_through_proxy"] = {
        "status": journeys[0],
        "ms": round(journeys[2], 1),
        "bytes": journeys[1],
    }
except urllib.error.HTTPError as error:
    report["journeys_through_proxy"] = {"status": error.code, "note": "not a GET endpoint"}
except Exception as error:  # noqa: BLE001 - a probe failing must not lose the report
    report["journeys_through_proxy"] = {"error": str(error)[:120]}

print(json.dumps(report, indent=2))
