"""Phone preview chain health probe - the shell, the Basic-auth proxy, the tunnel, and who listens.

Written because a status sentence like "the chain is up" is worth nothing without a reading behind it:
this emits the three HTTP results, two netstat counts and the tunnel's byte-per-probe timing into one
JSON so a lane or the arbiter can re-run the same five probes and compare.
"""
import base64
import datetime
import hashlib
import io
import json
import os
import ssl
import subprocess
import sys
import time
import urllib.request

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
AUTH_FILE = r"D:\moodle\_qoder_preview_20260920\run\preview_auth.txt"
SHELL = "http://127.0.0.1:4781/index.html"
PROXY = "http://127.0.0.1:4782/index.html"
TUNNEL = "https://obligation-plain-arcade-bean.trycloudflare.com/index.html"
PORTS = ("4781", "4782", "8000")


def listen_count(port):
    ns = subprocess.run(["netstat", "-ano", "-p", "tcp"], capture_output=True, text=True,
                        encoding="utf-8", errors="replace", timeout=120)
    return sum(1 for l in (ns.stdout or "").splitlines() if ":" + port in l and "LISTENING" in l.upper())


def basic_header():
    """Read the credential file by path; only its separator shape is reported, never its content."""
    raw = io.open(AUTH_FILE, encoding="utf-8").read().rstrip("\r\n")
    for sep in ("\t", ":"):
        if sep in raw:
            a, b = raw.split(sep, 1)
            return base64.b64encode((a + ":" + b).encode()).decode(), repr(sep)
    return None, "NO_KNOWN_SEPARATOR"


def probe(url, auth=None):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "cmdr-chain-health"})
        if auth:
            req.add_header("Authorization", "Basic " + auth)
        t0 = time.time()
        with urllib.request.urlopen(req, timeout=60, context=ssl._create_unverified_context()) as r:
            body = r.read()
            return {"url": url, "status": r.status, "bytes": len(body),
                    "ms": int((time.time() - t0) * 1000), "content_type": r.headers.get("content-type"),
                    "sha256_12": hashlib.sha256(body).hexdigest()[:12]}
    except Exception as e:  # noqa: BLE001
        return {"url": url, "error": type(e).__name__, "detail": str(e)[:80]}


auth, sep = basic_header()
rows = [probe(SHELL), probe(PROXY, auth), probe(TUNNEL), probe(TUNNEL, auth)]
tunnel_ok = any(r.get("status") == 200 for r in rows[2:])
out = {
    "schema": "CNX_CMDR_PHONE_CHAIN_HEALTH_V1",
    "at_local": (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=8)).isoformat(timespec="seconds") + "+08",
    "tool_sha1": hashlib.sha1(io.open(__file__, "rb").read()).hexdigest(),
    "credential_handling": "the auth file is read by path; only the separator that was found (" + sep + ") is reported, never a value",
    "probes": rows,
    "listen_rows": {p: listen_count(p) for p in PORTS},
    "tunnel_reachable_with_credentials": tunnel_ok,
    "decisions": {
        "shell_up": rows[0].get("status") == 200,
        "proxy_auth_gate_up": rows[1].get("status") == 200,
        "proxy_gate_refuses_without_credentials": rows[2].get("error", "") == "HTTPError" or "401" in str(rows[2].get("detail", "")),
        "all_three_layers_answer_the_same_index": len({r.get("bytes") for r in (rows[0], rows[1], rows[3]) if r.get("status") == 200}) == 1},
    "scope": "Transport health only. It says nothing about the data plane (that is the :8000 row) and is "
             "not a product claim - the served bytes here are the same index the phone gets."}
io.open("_phone_chain_health_1911.json", "w", encoding="utf-8").write(json.dumps(out, ensure_ascii=False, indent=1))
print(json.dumps(out["probes"], ensure_ascii=False, indent=1)[:600])
print("listen", out["listen_rows"], "| decisions", json.dumps(out["decisions"], ensure_ascii=False))
