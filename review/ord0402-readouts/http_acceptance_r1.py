"""ORD-0402 slice 1 - the bin door over real HTTP, on a private copy and a private uvicorn.

The commander's acceptance shape (18:50): private store copy + private uvicorn, real routes. The
hop1 backend still runs the 16:17 export and has neither the `deleted_at` column nor any of this
line's doors, so nothing here is evidence about the phone chain - that stays NOT-DEPLOYED-OBSERVED.

Three proofs are printed for the server, as this machine's rule requires: the PID netstat reports
as listening on my port, its ParentProcessId, and its command line - plus the SQLite file the
process actually opened.  Only the process started here is ever stopped, and it is stopped at the
end.  The source store is opened `mode=ro` for a backup copy and its row counts are read again
afterwards.
"""

from __future__ import annotations

import json
import os
import socket
import sqlite3
import subprocess
import time
import urllib.parse
from pathlib import Path

import httpx

REPO = Path(__file__).resolve().parents[2]
SOURCE = Path("D:/moodle/_qoder_preview_20260920/_preview.db")
COPY = REPO / "_scratch_probe" / "ord0402_http_copy.db"
TABLES = ("journeys", "plan_versions", "activities", "commitments", "events", "travelers")
PYTHON = Path("D:/moodle/CityNexus/.venv/Scripts/python.exe")


def counts(connection: sqlite3.Connection) -> dict[str, int]:
    return {t: int(connection.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]) for t in TABLES}


def free_port() -> int:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return int(probe.getsockname()[1])


def win(query: str) -> str:
    out = subprocess.run(
        ["powershell", "-NoProfile", "-Command", query],
        capture_output=True, text=True, encoding="utf-8", errors="replace", check=False,
    )
    return (out.stdout or "").strip()


def main() -> int:
    if not SOURCE.exists():
        print(f"[source] MISSING {SOURCE}")
        return 2
    COPY.parent.mkdir(parents=True, exist_ok=True)
    if COPY.exists():
        COPY.unlink()
    src = sqlite3.connect(f"file:{urllib.parse.quote(SOURCE.as_posix())}?mode=ro", uri=True)
    before = counts(src)
    columns = [str(r[1]) for r in src.execute("PRAGMA table_info(journeys)")]
    dst = sqlite3.connect(COPY)
    src.backup(dst)
    dst.close()
    src.close()
    print(f"[source] path={SOURCE} mode=ro counts={json.dumps(before, sort_keys=True)}")
    print(f"[source] journeys_had_deleted_at_column={'deleted_at' in columns}")
    print(f"[copy] path={COPY}")

    port = free_port()
    env = dict(os.environ)
    env["CITYNEXUS_DATABASE_URL"] = f"sqlite:///{COPY.as_posix()}"
    env["CITYNEXUS_PROVIDER_NETWORK_MODE"] = "direct"
    for key in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy"):
        env.pop(key, None)
    command = [str(PYTHON), "-X", "utf8", "-m", "uvicorn", "app.main:app",
               "--host", "127.0.0.1", "--port", str(port), "--log-level", "warning"]
    server = subprocess.Popen(command, cwd=str(REPO / "backend"), env=env,
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                              encoding="utf-8", errors="replace")
    print(f"[spawn] uvicorn_pid={server.pid} port={port} cwd={REPO / 'backend'}")
    base = f"http://127.0.0.1:{port}"
    up = False
    for _ in range(60):
        try:
            with httpx.Client(trust_env=False, timeout=2.0) as client:
                if client.get(base + "/api/v1/health").status_code == 200:
                    up = True
                    break
        except (httpx.TransportError, OSError):
            time.sleep(0.5)
    print(f"[up] answered_health={up}")
    if not up:
        server.kill()
        return 3

    # proof 1: who listens on my port; proof 2 and 3: that listener's parent and command line.
    # The listener is queried by its own pid, not assumed to equal the pid I spawned - a number
    # mismatch here is either an identity I have to name or a collision that voids the readings.
    listen = win(f"$c = Get-NetTCPConnection -LocalPort {port} -State Listen -EA SilentlyContinue;"
                 " if ($c) { $c | ForEach-Object { $_.OwningProcess } | Select-Object -Unique }")
    listener_row = win(f"$p = Get-CimInstance Win32_Process -Filter 'ProcessId={listen.split()[0]}'"
                       " -EA SilentlyContinue;"
                       " if ($p) { '' + $p.ProcessId + '|' + $p.ParentProcessId + '|' + $p.CommandLine }")
    parts = (listener_row or "").split("|", 2)
    listener_parent = parts[1].strip() if len(parts) > 1 else ""
    listener_command = parts[2] if len(parts) > 2 else ""
    is_me = str(server.pid) in str(listen).split()
    is_my_child = listener_parent == str(server.pid)
    same_line = ("app.main:app" in listener_command) and (f"--port {port}" in listener_command)
    print(f"[proof] port={port} listener_pid={listen or 'NONE'} spawned_pid={server.pid}")
    print(f"[proof] listener_parent_pid={listener_parent or 'NONE'} listener_command_carries_my_port"
          f"={same_line} spawned_command=-m uvicorn app.main:app --port {port}")
    print(f"[proof] listener_is_spawned={is_me} listener_is_child_of_spawned={is_my_child}")
    if not ((is_me or is_my_child) and same_line):
        print("[proof] ABORT - the port is not owned by a process I can name; the readings below "
              "would not be mine, so this run does not count")
        server.terminate()
        return 4
    db_open = COPY.exists() and sqlite3.connect(COPY).execute(
        "SELECT COUNT(*) FROM journeys").fetchone()[0]
    print(f"[proof] store_file_on_disk={COPY} journeys_readable={int(db_open)}")

    with httpx.Client(trust_env=False, timeout=10.0) as client:
        live_before = client.get(base + "/api/v1/journeys").json()
        bin_before = client.get(base + "/api/v1/recycle-bin/journeys")
        journey_id = str(live_before[0]["id"])
        print(f"[arm-empty] GET_recycle-bin status={bin_before.status_code} rows={len(bin_before.json())}")
        print(f"[arm-empty] list_rows={len(live_before)} journey_under_test={journey_id}")

        deleted = client.delete(f"{base}/api/v1/journeys/{journey_id}")
        live_after_delete = client.get(base + "/api/v1/journeys").json()
        bin_after_delete = client.get(base + "/api/v1/recycle-bin/journeys")
        rows = bin_after_delete.json()
        print(f"[arm-delete] DELETE_status={deleted.status_code} "
              f"list_rows={len(live_after_delete)} bin_status={bin_after_delete.status_code} "
              f"bin_rows={len(rows)}")
        if rows:
            print(f"[arm-delete] first_row id={rows[0]['id']} bin_state={rows[0]['bin_state']} "
                  f"deleted_at={rows[0]['deleted_at']} title_present={'title' in rows[0]}")

        restored = client.post(f"{base}/api/v1/journeys/{journey_id}/undelete")
        live_after_restore = client.get(base + "/api/v1/journeys").json()
        bin_after_restore = client.get(base + "/api/v1/recycle-bin/journeys").json()
        print(f"[arm-restore] UNDELETE_status={restored.status_code} "
              f"list_rows={len(live_after_restore)} bin_rows={len(bin_after_restore)}")

        repeat = client.post(f"{base}/api/v1/journeys/{journey_id}/undelete")
        print(f"[arm-repeat] second_UNDELETE_status={repeat.status_code} "
              f"reason_code={repeat.json().get('error', {}).get('reason_code')}")

    with sqlite3.connect(COPY) as copy_connection:
        after = counts(copy_connection)
    print(f"[copy-after] counts={json.dumps(after, sort_keys=True)}")
    print(f"[copy-after] activities_unchanged={after['activities'] == before['activities']} "
          f"journeys_unchanged={after['journeys'] == before['journeys']}")

    server.terminate()
    try:
        server.wait(timeout=15)
    except subprocess.TimeoutExpired:
        server.kill()
    gone = win(f"$c = Get-NetTCPConnection -LocalPort {port} -State Listen -EA SilentlyContinue;"
               " if ($c) { 'STILL_LISTENING' } else { 'RELEASED' }")
    print(f"[stop] uvicorn_returncode={server.returncode} port_state={gone}")

    with sqlite3.connect(f"file:{urllib.parse.quote(SOURCE.as_posix())}?mode=ro", uri=True) as src2:
        after_src = {t: int(src2.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]) for t in TABLES}
    print(f"[source] counts_at_the_end={json.dumps(after_src, sort_keys=True)}")
    print(f"[source] untouched={after_src == before}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
