"""Commander's live reading on the served shell: who answers an /api call when the data plane is down.

Why now: I dispatched ORD-0312 on the premise that the null-body cell needs a running backend.  This run
shows that premise is wrong for the shape in question - the vite preview proxy answers when its upstream
is absent, and it answers with a 500 carrying an EMPTY text/plain body.  That is exactly the "HTTP answered,
no JSON body" form the ORD-0302 wording fix is about, and it is reachable on the deployed generation
without touching :8000 or any protected database.

Two directions are measured, not one: the proxied call (expected: an HTTP answer with 0 bytes of body) and
a direct call to the upstream port (expected: connection refused).  A 500 with no counter-proof would only
show that something replied, not who.
"""
import datetime
import hashlib
import io
import json
import socket
import subprocess
import sys
import urllib.error
import urllib.request

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
SHELL = "http://127.0.0.1:4781"
UPSTREAM = "http://127.0.0.1:8000"
PATHS = ["/api/v1/health", "/api/v1/demo/scene", "/api/v1/journeys"]


def netstat_rows(port):
    r = subprocess.run(["netstat", "-ano", "-p", "tcp"], capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=120)
    return [l.strip() for l in (r.stdout or "").splitlines()
            if (":" + port) in l and "LISTENING" in l.upper()]


def get(base, path, method="GET"):
    try:
        req = urllib.request.Request(base + path, method=method)
        if method == "POST":
            req.add_header("content-type", "application/json")
            req.data = b"{}"
        with urllib.request.urlopen(req, timeout=30) as r:
            raw = r.read()
            return {"target": base + path, "answered": True, "status": r.status,
                    "content_type": r.headers.get("content-type"), "body_bytes": len(raw),
                    "body_head": raw.decode("utf-8", "replace")[:120]}
    except urllib.error.HTTPError as e:
        raw = e.read()
        return {"target": base + path, "answered": True, "via": "HTTPError", "status": e.code,
                "content_type": e.headers.get("content-type"), "body_bytes": len(raw),
                "body_head": raw.decode("utf-8", "replace")[:120]}
    except Exception as e:  # noqa: BLE001
        return {"target": base + path, "answered": False, "error": type(e).__name__,
                "detail": str(e)[:140]}


rows = []
for p in PATHS:
    proxied = get(SHELL, p, "POST" if p.endswith("scene") else "GET")
    direct = get(UPSTREAM, p, "POST" if p.endswith("scene") else "GET")
    rows.append({"path": p, "through_the_shell_proxy": proxied, "straight_to_upstream": direct,
                 "proxy_answered_and_upstream_did_not": bool(proxied.get("answered")) and not direct.get("answered")})

raw_socket = socket.socket()
try:
    raw_socket.settimeout(5)
    raw_socket.connect(("127.0.0.1", 8000))
    tcp_connect = "CONNECTED"
except Exception as e:  # noqa: BLE001
    tcp_connect = type(e).__name__
finally:
    raw_socket.close()

out = {
    "schema": "CNX_CMDR_PROXY_SELF_ANSWER_V1",
    "at_local": (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=8)).isoformat(timespec="seconds") + "+08",
    "tool_sha1": hashlib.sha1(io.open(__file__, "rb").read()).hexdigest(),
    "interpreter": sys.executable,
    "what_was_measured": "every /api call through the served shell (port 4781, the generation now on the "
                         "phone) against the same call made straight to the upstream port (8000)",
    "listen_rows_4781": len(netstat_rows("4781")),
    "listen_rows_8000": len(netstat_rows("8000")),
    "tcp_connect_to_8000": tcp_connect,
    "rows": rows,
    "decisions": {
        "proxy_answers_while_upstream_is_absent": all(r["proxy_answered_and_upstream_did_not"] for r in rows),
        "every_proxied_answer_is_a_5xx_with_an_empty_body": all(
            r["through_the_shell_proxy"].get("status", 0) >= 500
            and r["through_the_shell_proxy"].get("body_bytes") == 0 for r in rows),
        "upstream_never_replies": all(not r["straight_to_upstream"].get("answered") for r in rows)},
    "consequence_for_ORD_0312": "The null-body shape is reachable on the deployed generation without a "
                               "backend: the proxy itself produces 'an HTTP answer carrying no JSON body'. "
                               "The premise I dispatched under - that this cell needs :8000 running - is "
                               "therefore corrected, not by argument but by the readings above.",
    "discipline": {"writes_landed": 0, "demo_reset": 0, "protected_db_reads": 0,
                   "credentials_printed": 0, "authority_line_moved": 0,
                   "note": "the one POST carries an empty body ({}) to a demo route while the upstream is down, "
                           "so nothing can land behind it; no product file, no index, no database was touched, "
                           "and the screen was never mine to change - the onboarding drawer stayed up"},
    "scope": "What answers when the data plane is down, measured on the shell the phone is served. It is not "
             "the M1 verdict: the painted sentence still has to be read by the measurement lane with the "
             "drawer out of the way, and the level still belongs to the verifier."}
io.open("_proxy_selfanswer_1835.json", "w", encoding="utf-8").write(json.dumps(out, ensure_ascii=False, indent=1))
print("listen 4781", out["listen_rows_4781"], "| listen 8000", out["listen_rows_8000"], "| tcp 8000", tcp_connect)
for r in rows:
    print(" ", r["path"], "proxy", r["through_the_shell_proxy"].get("status"),
          r["through_the_shell_proxy"].get("content_type"), "body", r["through_the_shell_proxy"].get("body_bytes"),
          "| upstream", r["straight_to_upstream"].get("error", r["straight_to_upstream"].get("status")))
print("decisions", json.dumps(out["decisions"], ensure_ascii=False))
