"""End-to-end probe of the LIVE phone preview through the public tunnel.

Nothing here is local: every request goes cloudflared -> :4782 -> :4781/:8693, which is the same
path a finger on the phone takes. Credentials are read from the local auth file and never printed.
"""

import base64
import json
import time
import urllib.error
import urllib.parse
import urllib.request

BASE = "https://fonts-facilities-hotel-installing.trycloudflare.com"
AUTH = r"D:\moodle\_qoder_preview_20260920\run\preview_auth.txt"
user, secret = open(AUTH, encoding="utf-8").read().strip().split("\t")
TOKEN = base64.b64encode(f"{user}:{secret}".encode()).decode()


def call(method, path, payload=None, timeout=60):
    req = urllib.request.Request(BASE + path, method=method)
    req.add_header("Authorization", "Basic " + TOKEN)
    data = None
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        req.add_header("Content-Type", "application/json")
    started = time.time()
    try:
        with urllib.request.urlopen(req, data, timeout=timeout) as resp:
            body = resp.read().decode("utf-8", "replace")
            return resp.status, body, round(time.time() - started, 2)
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8", "replace"), round(time.time() - started, 2)
    except Exception as exc:  # noqa: BLE001
        return type(exc).__name__, str(exc), round(time.time() - started, 2)


for step in range(6):
    status, body, secs = call("GET", "/api/v1/health")
    print(f"[try {step + 1}] health -> {status} ({secs}s)")
    if status == 200:
        break
    time.sleep(3)

for path in ("/api/v1/demo/scene", "/api/v1/places?city_code=CN-BEIJING"):
    status, body, secs = call("GET", path)
    if path.startswith("/api/v1/places"):
        try:
            payload = json.loads(body)
            items = payload.get("items") if isinstance(payload, dict) else payload
            print(f"places CN-BEIJING -> {status} ({secs}s) n={len(items or [])}"
                  f" names={[p.get('name') for p in (items or [])][:8]}")
        except Exception as exc:  # noqa: BLE001
            print("places parse failed", status, str(exc)[:120], body[:200])
    else:
        print(f"scene -> {status} ({secs}s) {body[:180]}")

for q in ("北京", "CN-BEIJING", "云和县", "上海"):
    status, body, secs = call("GET", f"/api/v1/destinations/capability?query={urllib.parse.quote(q)}")
    try:
        payload = json.loads(body)
        detail = payload.get("coverage", {})
        print(f"capability {q!r} -> {status} ({secs}s) {payload.get('capability')}"
              f" {payload.get('reason_code')} canonical={payload.get('canonical_destination_id')}"
              f" coverage={detail}")
    except Exception:  # noqa: BLE001
        print(f"capability {q!r} -> {status} {body[:200]}")
