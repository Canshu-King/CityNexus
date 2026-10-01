"""ORD-0505 - one real HTTP abort, read back out of this lane's own file.

Not a TestClient run: uvicorn is started by this script on a port this lane picks, against a
database file that did not exist before the attempt, and every call below goes over the wire.  The
last section opens the SAME file with sqlite and prints the row's own `rowid`, so the claim "the
reason is in the record" is checked against the record rather than against the response that wrote
it.  Names the database and the rowid because a durability claim that does not is unchecked.

Never touched: :8000, :4781, :4782, :8693 and D:/moodle/_qoder_preview_20260920/_preview.db.
Never called: POST /api/v1/demo/reset.
"""

from __future__ import annotations

import json
import os
import socket
import sqlite3
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[2] / "backend"
WORK = Path("D:/moodle/_ord0505")
PY = sys.executable


def pick_port() -> int:
    for candidate in range(4615, 4640):
        if candidate in {8000, 4781, 4782, 8693}:
            continue
        with socket.socket() as probe:
            try:
                probe.bind(("127.0.0.1", candidate))
                return candidate
            except OSError:
                continue
    raise SystemExit("no free lane port in the reserved band")


def call(port: int, method: str, path: str, payload: dict | None = None) -> tuple[int, dict]:
    body = json.dumps(payload).encode() if payload is not None else None
    request = urllib.request.Request(
        f"http://127.0.0.1:{port}{path}", data=body, method=method,
        headers={"Content-Type": "application/json"} if body else {},
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            return response.status, json.loads(response.read().decode("utf-8", "replace") or "{}")
    except urllib.error.HTTPError as error:
        return error.code, json.loads(error.read().decode("utf-8", "replace") or "{}")


def main() -> int:
    WORK.mkdir(parents=True, exist_ok=True)
    run_id = "ORD0505-" + time.strftime("%H%M%S")
    db = WORK / f"{run_id}.db"
    if db.exists():
        raise SystemExit(f"{db} already exists")
    port = pick_port()
    env = dict(os.environ)
    for drop in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy", "DEEPSEEK_API_KEY"):
        env.pop(drop, None)
    env["CITYNEXUS_DATABASE_URL"] = f"sqlite:///{db.as_posix()}"
    env["CITYNEXUS_E2E_RUN_ID"] = run_id
    log = (WORK / "uvicorn.log").open("w", encoding="utf-8")
    child = subprocess.Popen(
        [PY, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(port)],
        cwd=str(BACKEND), env=env, stdout=log, stderr=subprocess.STDOUT,
    )
    for _ in range(90):
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/v1/health", timeout=3):
                break
        except Exception:  # noqa: BLE001
            time.sleep(1)
    print(f"run_id={run_id} port=:{port} db={db} child={child.pid}")

    start = datetime.now(timezone.utc) + timedelta(days=3)
    s, traveler = call(port, "POST", "/api/v1/travelers",
                       {"display_name": f"ord0505-{run_id}", "locale": "zh-CN", "timezone": "Asia/Shanghai"})
    print(f"POST /api/v1/travelers -> http_status={s}")
    s, journey = call(port, "POST", "/api/v1/journeys", {
        "traveler_id": traveler["id"], "title": "ORD-0505 真HTTP中止", "city_code": "CN-TIANJIN",
        "timezone": "Asia/Shanghai", "start_at": start.isoformat(),
        "end_at": (start + timedelta(days=2)).isoformat(),
        "budget": {"amount_minor": 300000, "currency": "CNY"}})
    print(f"POST /api/v1/journeys -> http_status={s}")
    jid = journey["id"]

    s, before = call(port, "GET", f"/api/v1/journeys/{jid}")
    print(f"GET /api/v1/journeys/{{id}} -> http_status={s} status={before['status']} "
          f"cancelled_at={before['cancelled_at']} cancelled_reason={before['cancelled_reason']!r}")

    stranger = call(port, "POST", "/api/v1/travelers",
                    {"display_name": f"ord0505-x-{run_id}", "locale": "zh-CN", "timezone": "Asia/Shanghai"})[1]
    s, refused = call(port, "POST", f"/api/v1/journeys/{jid}/abort",
                      {"reason": "不该由别人中止", "requested_by": stranger["id"]})
    print(f"POST .../abort (not the traveller) -> http_status={s} reason_code="
          f"{refused.get('error', {}).get('reason_code')} error_code={refused.get('error', {}).get('code')}")
    missing = call(port, "POST", "/api/v1/journeys/00000000-0000-0000-0000-000000000000/abort",
                   {"reason": "路不存在也要有名", "requested_by": traveler["id"]})
    print(f"POST .../abort (no such trip) -> http_status={missing[0]} reason_code="
          f"{missing[1].get('error', {}).get('reason_code')}")

    s, done = call(port, "POST", f"/api/v1/journeys/{jid}/abort",
                   {"reason": "同行的人改期了", "requested_by": traveler["id"]})
    print(f"POST .../abort (the real write) -> http_status={s} status={done.get('status')} "
          f"cancelled_at={done.get('cancelled_at')} reason={done.get('cancelled_reason')!r}")

    s, again = call(port, "POST", f"/api/v1/journeys/{jid}/abort",
                    {"reason": "第二次不该覆盖第一次", "requested_by": traveler["id"]})
    print(f"POST .../abort (replayed) -> http_status={s} reason_code="
          f"{again.get('error', {}).get('reason_code')}")
    s, live = call(port, "GET", f"/api/v1/journeys/{jid}/experience")
    print(f"GET .../experience (live screen) -> http_status={s} reason_code="
          f"{live.get('error', {}).get('reason_code') if s >= 400 else 'served'}")
    s, listed = call(port, "GET", "/api/v1/journeys")
    print(f"GET /api/v1/journeys -> http_status={s} contains aborted trip: "
          f"{jid in [str(item['id']) for item in listed]}")

    conn = sqlite3.connect(db)
    row = conn.execute(
        "SELECT rowid, status, deleted_at, cancelled_at, cancelled_reason FROM journeys WHERE id = ?",
        (jid,),
    ).fetchone()
    tables = len([r for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
                  if not str(r[0]).startswith("sqlite_")])
    conn.close()
    print(f"READ BACK FROM {db.name}: rowid={row[0]} status={row[1]} deleted_at={row[2]!r} "
          f"cancelled_at={row[3]!r} cancelled_reason={row[4]!r} (tables in file: {tables})")
    child.terminate()
    return 0 if row[1] == "CANCELLED" and row[4] == "同行的人改期了" else 1


if __name__ == "__main__":
    sys.exit(main())
