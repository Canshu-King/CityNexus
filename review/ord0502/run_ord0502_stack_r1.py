"""ORD-0502 -- start THIS lane's private phone stack and walk the mainline in it.

Why a runner at all: the chain must be reproducible by the next lane, not remembered by me.

What it does, in order, with every reading kept:

  1. a brand-new SQLite file named by the run id, because `backend/app/db/session.py:31-53` refuses
     to open an existing file for a run-stamped process -- that guard is the reason "fresh per
     attempt" is enforceable rather than a habit;
  2. a uvicorn on this lane's backend port against exactly that file;
  3. ownership proved from BOTH sides before any browser opens: a journey created through the
     frontend origin (so the proxy target is shown to be this lane's server) and the same row read
     back out of this lane's own file (so the answer is shown to come from this lane's database).
     The shared preview store is only ever opened `mode=ro`, and never by this script;
  4. a static server on this lane's frontend port serving the bundle this tree just built, with an
     SPA fallback, and an identity line naming the bytes it serves;
  5. Playwright with `playwright.ord0502-Q.config.ts`; the report and the walk's per-cell readings
     land outside the tracked tree and are copied into `review/ord0502/` for delivery.

Never called: `POST /api/v1/demo/reset`. Never touched: :8000, :4781, :4782, :8693, and
`D:/moodle/_qoder_preview_20260920/_preview.db`.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import socket
import sqlite3
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

REPO = Path(__file__).resolve().parents[2]
FRONTEND = REPO / "frontend"
BACKEND = REPO / "backend"
WORK = Path("D:/moodle/_ord0502")
DIST = FRONTEND / "dist"
PY = sys.executable
FORBIDDEN_PORTS = {8000, 4781, 4782, 8693}


def log(line: str) -> None:
    print(line, flush=True)
    with (WORK / "stack.log").open("a", encoding="utf-8") as handle:
        handle.write(line + "\n")


def free_port(wanted: int, name: str) -> int:
    if wanted in FORBIDDEN_PORTS:
        raise SystemExit(f"refusing to use {name}={wanted}: that port belongs to another stack")
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", wanted))
    return wanted


def env_base(run_id: str, db: Path, backend_port: int) -> dict[str, str]:
    env = dict(os.environ)
    for drop in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy", "DEEPSEEK_API_KEY"):
        env.pop(drop, None)
    env["CITYNEXUS_DATABASE_URL"] = f"sqlite:///{db.as_posix()}"
    env["CITYNEXUS_E2E_RUN_ID"] = run_id
    env["CITYNEXUS_BACKEND_PORT"] = str(backend_port)
    return env


def wait_http(url: str, seconds: int = 120) -> tuple[bool, str]:
    deadline = time.time() + seconds
    last = ""
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=3) as response:
                body = response.read(400).decode("utf-8", "replace")
                return True, f"http_status={response.status} body={body}"
        except Exception as error:  # noqa: BLE001 - the point is to report what was seen
            last = repr(error)
            time.sleep(1.0)
    return False, last


class StaticHandler(BaseHTTPRequestHandler):
    """Serves the bundle this tree built, and forwards /api/v1 to this lane's backend."""

    backend_port = 0

    def _send(self, status: int, body: bytes, ctype: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
        if self.path.startswith("/api/v1"):
            request = urllib.request.Request(f"http://127.0.0.1:{self.backend_port}{self.path}")
            try:
                with urllib.request.urlopen(request, timeout=30) as response:
                    self._send(response.status, response.read(), response.headers.get("Content-Type", "application/json"))
            except Exception as error:  # noqa: BLE001
                self._send(502, f'{{"error":"proxy {error}"}}'.encode(), "application/json")
            return
        rel = urlparse(self.path).path.lstrip("/") or "index.html"
        target = (DIST / rel).resolve()
        if not str(target).startswith(str(DIST.resolve())):
            self._send(403, b"no", "text/plain")
            return
        if not target.is_file():
            # SPA fallback: a deep link must be answered by the shell, exactly as the product's own
            # static host does, otherwise /v8/footprints would only be reachable by clicking.
            target = DIST / "index.html"
        body = target.read_bytes()
        ctype = {".html": "text/html", ".js": "text/javascript", ".css": "text/css",
                 ".svg": "image/svg+xml", ".webmanifest": "application/manifest+json",
                 ".json": "application/json"}.get(target.suffix, "application/octet-stream")
        self._send(200, body, ctype)

    def _forward(self, method: str) -> None:
        length = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(length) if length else None
        request = urllib.request.Request(
            f"http://127.0.0.1:{self.backend_port}{self.path}",
            data=body,
            method=method,
            headers={"Content-Type": self.headers.get("Content-Type", "application/json")},
        )
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                self._send(response.status, response.read(),
                           response.headers.get("Content-Type", "application/json"))
        except urllib.error.HTTPError as error:
            self._send(error.code, error.read(), error.headers.get("Content-Type", "application/json"))
        except Exception as error:  # noqa: BLE001
            self._send(502, f'{{"error":"proxy {error}"}}'.encode(), "application/json")

    def do_POST(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
        self._forward("POST")

    def do_PATCH(self) -> None:  # noqa: N802
        self._forward("PATCH")

    def do_DELETE(self) -> None:  # noqa: N802
        self._forward("DELETE")

    def log_message(self, *_args: object) -> None:
        return


def main() -> int:
    WORK.mkdir(parents=True, exist_ok=True)
    (WORK / "stack.log").write_text("", encoding="utf-8")
    run_id = "ORD0502-" + time.strftime("%H%M%S")
    backend_port = free_port(int(os.environ.get("CITYNEXUS_ORD0502_BACKEND_PORT", "4611")), "backend")
    frontend_port = free_port(int(os.environ.get("CITYNEXUS_ORD0502_FRONT_PORT", "4612")), "frontend")
    db = WORK / f"{run_id}.db"
    if db.exists():
        raise SystemExit(f"{db} already exists; a run id is one per attempt")
    env = env_base(run_id, db, backend_port)
    log(f"[stack] run_id={run_id} backend=:{backend_port} frontend=:{frontend_port} db={db}")

    backend_log = (WORK / "uvicorn.log").open("w", encoding="utf-8")
    child = subprocess.Popen(
        [PY, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(backend_port)],
        cwd=str(BACKEND), env=env, stdout=backend_log, stderr=subprocess.STDOUT,
    )
    ok, reading = wait_http(f"http://127.0.0.1:{backend_port}/api/v1/health")
    log(f"[stack] backend direct /api/v1/health -> {reading} (child pid={child.pid} alive={child.poll() is None})")
    if not ok:
        child.terminate()
        return 2

    # 4. the static + proxy front.
    StaticHandler.backend_port = backend_port
    server = ThreadingHTTPServer(("127.0.0.1", frontend_port), StaticHandler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    index = (DIST / "index.html").read_bytes()
    log(f"[stack] front serves {len(index)} B of dist/index.html sha1={hashlib.sha1(index).hexdigest()}")

    # 3. ownership proved from both sides.
    marker = f"qoder-ord0502-{run_id}"
    opener = urllib.request.build_opener()

    def post(path: str, payload: dict) -> tuple[str, dict]:
        request = urllib.request.Request(
            f"http://127.0.0.1:{frontend_port}{path}",
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
        )
        try:
            with opener.open(request, timeout=60) as response:
                text = response.read().decode("utf-8", "replace")
                return f"http_status={response.status}", json.loads(text or "{}")
        except urllib.error.HTTPError as error:
            detail = error.read().decode("utf-8", "replace")[:300]
            return f"http_status={error.code}", {"error": detail}
        except Exception as error:  # noqa: BLE001
            return "http_status=NOT_SEEN", {"error": repr(error)[:200]}

    status, traveler = post("/api/v1/travelers", {"display_name": marker, "locale": "zh-CN", "timezone": "Asia/Shanghai"})

    def get(path: str) -> tuple[str, dict]:
        try:
            with opener.open(f"http://127.0.0.1:{frontend_port}{path}", timeout=60) as response:
                return f"http_status={response.status}", json.loads(response.read().decode("utf-8", "replace") or "{}")
        except urllib.error.HTTPError as error:
            return f"http_status={error.code}", {"error": error.read().decode("utf-8", "replace")[:200]}
        except Exception as error:  # noqa: BLE001
            return "http_status=NOT_SEEN", {"error": repr(error)[:160]}

    traveler_id = traveler.get("id")
    read_status, read_back = get(f"/api/v1/travelers/{traveler_id}") if traveler_id else ("http_status=NOT_SEEN", {})
    journey_id = None
    conn = sqlite3.connect(db)
    try:
        rows = conn.execute("SELECT COUNT(*) FROM travelers WHERE display_name = ?", (marker,)).fetchone()[0]
        places = conn.execute("SELECT COUNT(*) FROM places").fetchone()[0]
        tables = len([r for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
                      if not str(r[0]).startswith("sqlite_")])
    finally:
        conn.close()
    proven = rows == 1 and read_status == "http_status=200" and read_back.get("display_name") == marker
    log(f"[stack] ownership: POST /api/v1/travelers {status} id={traveler_id}; GET /api/v1/travelers/{{id}} "
        f"through the FRONTEND origin {read_status} display_name={read_back.get('display_name')!r}; "
        f"this lane's file holds {rows} marker row(s), {places} place row(s), {tables} tables -> "
        f"{'PROVEN' if proven else 'NOT PROVEN'}")
    if not proven:
        server.shutdown()
        child.terminate()
        return 3
    (WORK / "traveler_id").write_text(str(traveler_id), encoding="utf-8")

    report = WORK / f"report-{run_id}.json"
    penv = dict(env)
    penv.update({
        "CITYNEXUS_E2E_PORT": str(frontend_port),
        "CITYNEXUS_ORD0502_REPORT": str(report),
        "CITYNEXUS_ORD0502_OUT": str(WORK),
    })
    # `npm exec playwright test --config ...` hands --config to npm, not to Playwright (it answers
    # "Unknown npm config" and then runs the default config, which finds no tests). Call the CLI
    # itself so the argument reaches the tool that defines it.
    node = shutil.which("node")
    if not node:
        raise SystemExit("node is required to run the Playwright CLI")
    cli = FRONTEND / "node_modules" / "playwright" / "cli.js"
    if not cli.exists():
        raise SystemExit(f"Playwright CLI not found at {cli}; this lane borrows node_modules read-only")
    proc = subprocess.run(
        [node, str(cli), "test", "--config=playwright.ord0502-Q.config.ts"],
        cwd=str(FRONTEND), env=penv, capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    (WORK / "playwright.txt").write_text(proc.stdout + "\n" + proc.stderr, encoding="utf-8")
    log(f"[stack] playwright exit={proc.returncode}")
    for line in (proc.stdout or "").splitlines():
        if "[ord0502]" in line or "passed" in line or "failed" in line or "CHAIN" in line:
            log(f"[stack] {line.strip()}")

    server.shutdown()
    child.terminate()
    for src, dst in ((WORK / "stack.log", REPO / "review/ord0502/stack.log"),
                     (WORK / "playwright.txt", REPO / "review/ord0502/playwright.txt"),
                     (report, REPO / f"review/ord0502/report-{run_id}.json")):
        if src.exists():
            shutil.copyfile(src, dst)
    walk = WORK / f"walk-{run_id}.json"
    if walk.exists():
        shutil.copyfile(walk, REPO / f"review/ord0502/walk-{run_id}.json")
    return proc.returncode


if __name__ == "__main__":
    sys.exit(main())
