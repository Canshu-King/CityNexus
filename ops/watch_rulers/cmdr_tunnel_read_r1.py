#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""cmdr_tunnel_read_r1.py -- one honest read of the phone chain from outside the box.

Why this exists: two lanes reported "the tunnel is unreachable" while the commander's swap receipt
showed the same URL answering.  Both readings were real.  The difference was that this box exports
HTTP(S)_PROXY pointing at 127.0.0.1:7892, which nothing listens on, so any client that honours the
environment gets CURLE_COULDNT_CONNECT and reports it as a dead tunnel.  The second trap is the
credential file: it stores `user<TAB>password`, which is NOT the `user:password` form curl -u wants,
so an authenticated probe silently sends a nonsense username and can hang on the retry.

This tool removes both traps: it clears proxy variables inside its own process (ProxyHandler({}),
so it never trusts inherited state), splits the credential file on TAB, and never prints a value it
read from that file.  Output is status, content type, byte count and elapsed seconds per path --
which is exactly the field set the standing UI-exposure ruling allows on screen anyway.

    python cmdr_tunnel_read_r1.py --base https://<host>.trycloudflare.com
    python cmdr_tunnel_read_r1.py --base http://127.0.0.1:4782 --paths / /api/v1/health
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

AUTH_FILE_DEFAULT = r"D:/moodle/_qoder_preview_20260920/run/preview_auth.txt"
ASSET_RE = re.compile(r"assets/index-[A-Za-z0-9_\-]+\.(?:js|css)")


def read_credential(path: str) -> tuple[str, str]:
    """Split the auth file on TAB. Never echo either half."""
    raw = open(path, "rb").read()
    if b"\t" not in raw:
        raise SystemExit(
            "REFUSED: %s has no TAB separator. This file is `user<TAB>password`; a `user:password`"
            " guess would produce a silently wrong credential rather than an error." % path
        )
    user, _, password = raw.decode("utf-8", "replace").partition("\t")
    user, password = user.strip(), password.strip()
    if not user or not password:
        raise SystemExit("REFUSED: one of the two credential fields in %s is empty" % path)
    return user, password


def probe(base: str, path: str, header: str | None, timeout: float) -> dict:
    req = urllib.request.Request(base.rstrip("/") + path)
    if header:
        req.add_header("Authorization", header)
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    started = time.time()
    try:
        with opener.open(req, timeout=timeout) as resp:
            body = resp.read()
            text = body.decode("utf-8", "replace")
            out = {
                "path": path,
                "http_status": resp.status,
                "content_type": resp.headers.get("content-type"),
                "body_bytes": len(body),
                "elapsed_ms": int((time.time() - started) * 1000),
                "served_as_html": bool(text.lstrip()[:15].lower().startswith("<!doctype html")),
            }
            refs = sorted(set(ASSET_RE.findall(text)))
            if refs:
                out["asset_refs"] = refs
            head = text[:120].replace("\n", " ")
            if "health" in path:
                try:
                    payload = json.loads(text)
                    out["ai_state"] = payload.get("ai_state")
                    out["status"] = payload.get("status")
                    out["database"] = payload.get("database")
                except Exception:
                    out["body_head_unparsed"] = head
            return out
    except urllib.error.HTTPError as exc:
        return {
            "path": path,
            "http_status": exc.code,
            "content_type": exc.headers.get("content-type") if exc.headers else None,
            "body_bytes": len(exc.read() or b""),
            "elapsed_ms": int((time.time() - started) * 1000),
            "error": "HTTPError",
        }
    except Exception as exc:
        return {
            "path": path,
            "elapsed_ms": int((time.time() - started) * 1000),
            "error": type(exc).__name__,
            "detail": str(exc)[:160],
        }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True)
    ap.add_argument("--auth-file", default=AUTH_FILE_DEFAULT)
    ap.add_argument("--paths", default="/,/api/v1/health")
    ap.add_argument("--timeout", type=float, default=40.0)
    ap.add_argument("--no-auth", action="store_true",
                    help="probe anonymously; a 401 here is the auth proxy working, not a failure")
    args = ap.parse_args()

    # Report what the environment claimed before this process fixed it, because that is the fact
    # the next reader needs in order to not repeat the two lanes' mistake.
    env_proxy = {k: os.environ.get(k) for k in
                 ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy", "NO_PROXY")
                 if os.environ.get(k)}
    header = None
    if not args.no_auth:
        user, password = read_credential(args.auth_file)
        header = "Basic " + base64.b64encode(f"{user}:{password}".encode()).decode()

    verdicts = []
    for path in [p for p in args.paths.split(",") if p]:
        verdicts.append(probe(args.base, path if path.startswith("/") else "/" + path,
                              header, args.timeout))

    print(json.dumps({
        "base": args.base,
        "authenticated": not args.no_auth,
        "proxy_env_before": env_proxy,
        "proxy_handling": "ProxyHandler({}) -- direct, ignores every *_proxy variable",
        "credential_note": "auth file split on TAB; neither field is ever printed",
        "probes": verdicts,
    }, indent=1))

    # A run where nothing answered at all is not a green report just because it printed JSON.
    answered = [v for v in verdicts if "http_status" in v]
    if not answered:
        print("VERDICT: NOTHING_ANSWERED -- the chain, not the client, must be re-checked",
              file=sys.stderr)
        return 1
    print("VERDICT: %d/%d probes answered with an HTTP status" % (len(answered), len(verdicts)),
          file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
