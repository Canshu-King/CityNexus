"""Does the LAN reach the demo session through Vite's proxy without a presenter key?

Stands up the exported Codex backend (loopback) plus a Vite dev server bound to 0.0.0.0 whose
proxy points at it, then asks `/api/v1/demo/session` three ways: direct loopback without Origin,
through the proxy from the LAN address without Origin, and through the proxy with a LAN Origin.
The presenter key never leaves this process's environment and is not printed.
"""
from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request

from _entry_banner_stack_r1 import (
    BACKEND, WORK, copy_db, start_backend, stop_isolated_backend, wait_healthy,
)

NODE = r"C:/Program Files/nodejs/node.exe"
FRONTEND = r"D:/moodle/_cmdr_rescue_v3_1022/frontend"
OUT = r"D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261022_v3_human_chrome/presenter-proxy-bypass-1.txt"
OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def lan_ipv4() -> str:
    probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        probe.connect(("8.8.8.8", 80))
        return probe.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        probe.close()


def ask(url: str, origin: str | None = None, timeout: int = 8) -> dict:
    headers = {"Accept": "application/json"}
    if origin:
        headers["Origin"] = origin
    request = urllib.request.Request(url, headers=headers)
    try:
        with OPENER.open(request, timeout=timeout) as answer:
            raw = answer.read().decode("utf-8", "replace")
            body = {}
            try:
                body = json.loads(raw)
            except ValueError:
                pass
            return {"status": answer.status,
                    "token_present": bool(body.get("access_token")),
                    "journey_id": body.get("journey_id"),
                    "head": raw[:100]}
    except urllib.error.HTTPError as error:
        return {"status": error.code, "head": error.read().decode("utf-8", "replace")[:100]}
    except Exception as error:  # noqa: BLE001
        return {"status": 0, "error": type(error).__name__ + ":" + str(error)[:80]}


def start_frontend(port: int, backend_port: int) -> subprocess.Popen:
    env = dict(os.environ)
    env["CITYNEXUS_BACKEND_PORT"] = str(backend_port)
    log = open(WORK + "/proxy_frontend.log", "wb")
    return subprocess.Popen(
        [NODE, "node_modules/vite/bin/vite.js", "--port", str(port), "--strictPort", "--host", "0.0.0.0"],
        cwd=FRONTEND, env=env, stdout=log, stderr=subprocess.STDOUT,
    )


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    target = os.path.join(WORK, "probe12_1025.db")
    stop_isolated_backend()
    time.sleep(2)
    copy_db(os.path.join(WORK, "probe6_1025.db"), target)
    presenter_key = "probe" + os.urandom(20).hex()
    backend = start_backend(target, presenter_key)
    frontend = None
    try:
        if not wait_healthy():
            print(json.dumps({"RAN": False, "reason": "backend not healthy"}))
            return 1
        frontend = start_frontend(14495, 60400)
        lan = lan_ipv4()
        deadline = time.time() + 60
        while time.time() < deadline:
            if ask("http://%s:14495/" % lan)["status"] == 200:
                break
            time.sleep(1)
        direct = ask("http://127.0.0.1:60400/api/v1/demo/session")
        via_lan = ask("http://%s:14495/api/v1/demo/session" % lan)
        via_lan_origin = ask("http://%s:14495/api/v1/demo/session" % lan,
                             origin="http://%s:14495" % lan)
        receipt = {
            "LAN": lan,
            "backend_direct_no_origin": direct,
            "vite_proxy_lan_no_origin": via_lan,
            "vite_proxy_lan_with_origin": via_lan_origin,
            "BYPASS_SUSPECTED": via_lan.get("status") == 200 and via_lan.get("token_present", False),
        }
        with open(OUT, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(receipt, ensure_ascii=False) + "\n")
        print(json.dumps(receipt, ensure_ascii=False))
        return 0
    finally:
        if frontend is not None:
            subprocess.run(["taskkill", "/PID", str(frontend.pid), "/T", "/F"], capture_output=True)
        stop_isolated_backend()


if __name__ == "__main__":
    raise SystemExit(main())
