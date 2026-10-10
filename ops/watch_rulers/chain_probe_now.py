"""Phone-preview chain probe, read from the live coordinate file instead of a hardcoded URL.

Why this exists: `tunnel_probe.py` pins a `BASE` literal, and every quick-tunnel restart mints a NEW
random host, so the instrument silently kept probing a dead address - the same class of defect as a
16-hex prefix pretending to be a coordinate.  Here the base comes from `run/tunnel_url.txt`, the asset
name comes from the SERVED index bytes (not from disk, which would test a generation that is already
gone), and a LOCAL CONTROL ARM goes to :4782 over loopback so a public-side failure can never be
attributed to my layers, and vice versa.

Credentials come from `run/preview_auth.txt` (TAB separated) and are never printed.  Read-only: every
request is a GET, no database is touched by this process.
"""
import base64
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

RUN = r"D:\moodle\_qoder_preview_20260920\run"
AUTH_FILE = os.path.join(RUN, "preview_auth.txt")
URL_FILE = os.path.join(RUN, "tunnel_url.txt")
LOCAL = "http://127.0.0.1:4782"
ASSET_RE = re.compile(r"""["'](/assets/[^"']+\.js)["']""")
API_PATHS = ("/api/v1/health", "/api/v1/places?city_code=CN-BEIJING")


def auth_header():
    user, secret = open(AUTH_FILE, encoding="utf-8").read().strip().split("\t")
    return "Basic " + base64.b64encode((user + ":" + secret).encode()).decode()


def get(base, path, timeout=25, want_body=False):
    req = urllib.request.Request(base + path, headers={
        "Authorization": auth_header(),
        "User-Agent": "commander-chain-probe/1 (read-only)",
    })
    started = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read()
            return {"status": resp.status, "ctype": resp.headers.get("content-type", ""),
                    "bytes": len(body), "secs": round(time.time() - started, 2), "error": "",
                    "text": body.decode("utf-8", "replace") if want_body else ""}
    except urllib.error.HTTPError as exc:
        body = exc.read()
        return {"status": exc.code, "ctype": exc.headers.get("content-type", ""), "bytes": len(body),
                "secs": round(time.time() - started, 2), "error": "HTTPError",
                "text": body[:200].decode("utf-8", "replace")}
    except Exception as exc:  # noqa: BLE001  a dead tunnel is an exception, not a finding
        return {"status": None, "ctype": "", "bytes": 0, "secs": round(time.time() - started, 2),
                "error": type(exc).__name__ + ": " + str(exc)[:110], "text": ""}


def show(label, r):
    print(f"  {label:<44} status={str(r['status']):<5} {r['bytes']:>9} B {r['secs']:>7}s  "
          f"{r['ctype'][:32]:<32} {r['error']}")


def arm(name, base):
    """Returns (index_ok, asset_ok, api_ok) - three separate answers, never one blended verdict."""
    print(f"[{name}] {base}")
    idx = get(base, "/", want_body=True)
    show("GET / (served index)", idx)
    index_ok = idx["status"] == 200

    assets = ASSET_RE.findall(idx["text"]) if index_ok else []
    asset_ok = False
    if assets:
        r = get(base, assets[0])
        show("GET " + assets[0], r)
        is_html = "text/html" in r["ctype"]
        asset_ok = r["status"] == 200 and not is_html and r["bytes"] > 10_000
        if is_html:
            print("    -> a .js URL answered HTML: STALE_CLIENT_BREAKAGE_RISK (DEPLOY_BUNDLE_RETENTION)")
        else:
            print(f"    -> real JS bytes, named by the served index (names found: {len(assets)})")
    else:
        print("    -> no /assets/*.js named by the served index: cannot judge the asset leg")

    api_ok = True
    for path in API_PATHS:
        r = get(base, path, want_body=True)  # without this the body is dropped and every shape reads "unparsed"
        show("GET " + path, r)
        if r["status"] != 200:
            api_ok = False
        elif path.startswith("/api/v1/places"):
            # Read BOTH payload shapes: this route answers a BARE LIST today, and an `items` wrapper
            # would otherwise print "n=0" and read as an empty catalog - a false absence produced by
            # guessing a field name instead of looking at what came back.
            try:
                payload = json.loads(r["text"]) if r["text"] else None
            except Exception as exc:  # noqa: BLE001
                payload = None
                print(f"    -> places body unparseable: {str(exc)[:90]}")
            if isinstance(payload, list):
                items, shape = payload, "bare_list"
            elif isinstance(payload, dict):
                shape = ("dict/items" if "items" in payload
                         else "dict/keys=" + ",".join(sorted(payload)[:6]))
                items = payload.get("items", [])
            else:
                items, shape = [], "unparsed"
            names = [i.get("name") for i in items if isinstance(i, dict)][:5]
            print(f"    -> places n={len(items)} payload_shape={shape} first={names}")
    return index_ok, asset_ok, api_ok


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # GBK console would mangle place names
    except Exception:  # noqa: BLE001
        pass
    base = open(URL_FILE, encoding="utf-8").read().strip()
    print("public coordinate read from run/tunnel_url.txt:\n  " + base)
    pub = arm("PUBLIC (through cloudflared)", base)
    loc = arm("LOCAL CONTROL (loopback :4782, no tunnel)", LOCAL)
    print("attribution (per leg, not blended):")
    labels = ("index", "asset", "api")
    for label, p, l in zip(labels, pub, loc):
        print(f"  {label:<6} public={p!s:<5} local={l!s:<5} "
              + ("BOTH OK" if p and l else ("TUNNEL LEG IS THE FAILING ONE" if l and not p else
                                            "LOCAL CHAIN DOWN (a tunnel restart will not fix it)" if not l
                                            else "BOTH FAIL")))


if __name__ == "__main__":
    main()
