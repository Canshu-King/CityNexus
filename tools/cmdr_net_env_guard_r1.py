"""Bypass a configured HTTP(S) proxy that refuses connections, before any tool attributes a RED.

Why this exists: on this box HTTPS_PROXY has pointed at 127.0.0.1:7892 since the local proxy moved to
the mixed port 7897, and on 2026-09-26 that stale answer produced three separate false reds attributed
to the product or to the phone chain (a deploy-gate tunnel arm, the ledger mirror, and one probe).
A refused proxy port is an instrument fact, not a network fact, so the check is done once per process
and the decision is printed rather than applied silently.

Returns a dict describing what it did; callers that want strictness should print it into their receipt.
"""
import os
import socket


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


def ensure_proxy_usable(defaults=("HTTPS_PROXY", "HTTP_PROXY", "ALL_PROXY")):
    report = {"proxy_env_before": {}, "refused": [], "action": "KEEP_PROXY"}
    for key in defaults:
        value = os.environ.get(key)
        if not value:
            continue
        report["proxy_env_before"][key] = value
        port = _port_of(value)
        if port is None:
            continue
        probe = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        probe.settimeout(1.0)
        try:
            probe.connect(("127.0.0.1", port))
        except OSError:
            report["refused"].append("%s=127.0.0.1:%d" % (key, port))
        finally:
            probe.close()
    if report["refused"]:
        for key in defaults:
            if key in os.environ:
                del os.environ[key]
        os.environ["NO_PROXY"] = "*"
        report["action"] = "PROXY_CLEARED_AND_DIRECT"
    return report
