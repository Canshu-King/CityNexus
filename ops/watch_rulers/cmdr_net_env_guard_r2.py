"""r2 of the proxy guard: a proxy that ACCEPTS the TCP connection and then kills the TLS handshake is
unusable, and the old guard called it usable.

What r1 checked, and why that was not enough: `ensure_proxy_usable()` did a bare TCP `connect()` to
127.0.0.1:<port>. On 2026-09-29 01:58+08 that answer was exactly wrong - the listener on 7892 accepted the
socket and then died mid-handshake (`ssl.SSLEOFError: EOF occurred in violation of protocol`), so r1 printed
`refused: [] / action: KEEP_PROXY` and the ledger mirror failed twice on a route that was never going to
work. The earlier failure mode of this same stale variable was a clean 10061 refusal, which r1 DID catch.
So the guard's blind spot is precisely "connectable but not transacting".

r2's rule: a proxy is usable only if it completes a real HTTPS request and returns a body. To keep a GitHub
outage from being mis-read as a proxy fault, the direct route is measured in the SAME run as a positive
control, and the verdict distinguishes the three states:
  PROXY_OK              - the proxy transacted; leave the environment alone
  PROXY_UNUSABLE        - direct works, proxy does not  => clear the proxy vars and go direct
  BOTH_ROUTES_FAIL      - neither works; that is a network fact, not an instrument fact, so nothing is
                          cleared and the caller must not attribute a RED to the product

Returns the whole decision as a dict so callers print it into their receipt.  Never raises.
"""
import json
import os
import socket
import urllib.error
import urllib.request

PROBE_URL = "https://api.github.com/meta"
TIMEOUT_SECS = 8


def _port_of(value):
    for scheme in ("http://", "https://"):
        if value.startswith(scheme):
            value = value[len(scheme):]
    value = value.split("/", 1)[0]
    if ":" in value:
        try:
            return int(value.rsplit(":", 1)[1])
        except ValueError:
            return None
    return None


def _tcp_open(host, port, timeout=1.0):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(timeout)
    try:
        s.connect((host, port))
        return True
    except OSError:
        return False
    finally:
        s.close()


def _https_works(proxies):
    """True only when a real GET completes and a body is read. A TCP handshake is not enough."""
    try:
        opener = urllib.request.build_opener(urllib.request.ProxyHandler(proxies))
        resp = opener.open(PROBE_URL, timeout=TIMEOUT_SECS)
        body = resp.read()
        json.loads(body.decode("utf-8", "replace"))
        return True, "%d %d B" % (getattr(resp, "status", 200), len(body))
    except urllib.error.HTTPError as e:
        # any HTTP answer at all means the TLS channel worked - that is what we are testing
        return True, "HTTP %d" % e.code
    except Exception as e:
        return False, "%s: %s" % (type(e).__name__, str(e)[:120])


def ensure_proxy_usable(defaults=("HTTPS_PROXY", "HTTP_PROXY", "ALL_PROXY"), verbose=False):
    report = {"guard": "cmdr_net_env_guard_r2", "proxy_env_before": {}, "proxy_endpoints": [],
              "proxy_ok": None, "direct_ok": None, "refused": [], "action": "KEEP_PROXY",
              "detail": {}}
    for key in defaults:
        value = os.environ.get(key)
        if not value:
            continue
        report["proxy_env_before"][key] = value
        port = _port_of(value)
        if port is not None and value.startswith("http://127.0.0.1") and _tcp_open("127.0.0.1", port):
            report["proxy_endpoints"].append("127.0.0.1:%d" % port)

    # positive control first: if the direct route is dead, a proxy failure is not our problem to fix
    direct_ok, direct_detail = _https_works({})
    report["direct_ok"] = direct_ok
    report["detail"]["direct"] = direct_detail

    if not report["proxy_env_before"]:
        report["action"] = "NO_PROXY_CONFIGURED"
        if verbose:
            print(json.dumps(report, ensure_ascii=False))
        return report

    # now ask the proxy the only question that matters
    proxies = {k.lower().split("_")[0]: v for k, v in report["proxy_env_before"].items()
               if k.lower() in ("https_proxy", "http_proxy")}
    if not proxies:
        proxies = {"https": report["proxy_env_before"].get("HTTPS_PROXY") or
                            report["proxy_env_before"].get("HTTP_PROXY")}
    proxy_ok, proxy_detail = _https_works(proxies)
    report["proxy_ok"] = proxy_ok
    report["detail"]["proxy"] = proxy_detail

    if proxy_ok:
        report["action"] = "PROXY_OK"
    elif direct_ok:
        # the proxy is the broken leg - drop it and continue direct, which we just proved works
        for key in list(os.environ):
            if key.upper() in defaults or key.upper() == "ALL_PROXY":
                del os.environ[key]
        os.environ["NO_PROXY"] = "*"
        report["refused"].append("proxy transacting failed while direct succeeded")
        report["action"] = "PROXY_UNUSABLE_CLEARED_AND_DIRECT"
    else:
        # do NOT clear anything: this is a network fact and must be reported, not worked around
        report["action"] = "BOTH_ROUTES_FAIL_NOT_A_PROXY_FAULT"
    if verbose:
        print(json.dumps(report, ensure_ascii=False))
    return report


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    r = ensure_proxy_usable(verbose=True)
    # exit non-zero when the guard had to intervene, so a caller can see it in `&&` chains
    raise SystemExit(0 if r["action"] in ("PROXY_OK", "NO_PROXY_CONFIGURED") else 3)
