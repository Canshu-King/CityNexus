"""ORD-0402 cross-lane wire check - does slice 1's landed door answer what slice 2's panel asks?

Run at the tip `9b759cb3d7b5519a51decea244ee09723d36080d`, which contains BOTH halves: this lane's
read door (`backend/app/main.py:3058`) and lane Q's panel (`frontend/src/features/trash/journeyTrash.ts`).
Q wrote its read arm against a door that was not on the line yet, so this answers the one question
that decides whether the panel has to change: are the path, the row keys, the state word and the
refusal token the same on the wire as in the panel's own declarations?

Nothing here opens the shared store for writing (the source is a `mode=ro` backup), no
`demo/reset` is called, and only the uvicorn started here is ever stopped.
"""

from __future__ import annotations

import json
import os
import re
import socket
import sqlite3
import subprocess
import time
import urllib.parse
from pathlib import Path

import httpx

REPO = Path(__file__).resolve().parents[2]
SOURCE = Path("D:/moodle/_qoder_preview_20260920/_preview.db")
COPY = REPO / "_scratch_probe" / "cross_lane_copy.db"
PANEL = REPO / "frontend/src/features/trash/journeyTrash.ts"
PYTHON = Path("D:/moodle/CityNexus/.venv/Scripts/python.exe")
TABLES = ("journeys", "plan_versions", "activities", "commitments", "events", "travelers")


def counts(connection: sqlite3.Connection) -> dict[str, int]:
    return {t: int(connection.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]) for t in TABLES}


def free_port() -> int:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return int(probe.getsockname()[1])


def win(query: str) -> str:
    out = subprocess.run(["powershell", "-NoProfile", "-Command", query],
                         capture_output=True, text=True, encoding="utf-8", errors="replace",
                         check=False)
    return (out.stdout or "").strip()


def panel_contract() -> tuple[str, list[str], list[str], str]:
    """The path, the declared row keys, the undelete body keys and the expected state word."""
    text = PANEL.read_text(encoding="utf-8")
    path = re.search(r'TRASH_LIST_PATH = "([^"]+)"', text).group(1)
    block = re.search(r"export type DiscardedJourney = \{(.*?)\n\};", text, re.DOTALL).group(1)
    fields = [m.group(1) for m in re.finditer(r"^\s*(\w+)\??:", block, re.MULTILINE)]
    undelete = re.search(r"request<\{ (.*?) \}>\(", text).group(1)
    word = re.search(r"`(IN_[A-Z_]+)` is what this file expects", text).group(1)
    return path, fields, re.findall(r"(\w+):", undelete), word


def main() -> int:
    panel_path, panel_fields, undelete_fields, expected_word = panel_contract()
    print(f"[panel] path={panel_path} row_fields={json.dumps(panel_fields)} "
          f"undelete_body_fields={json.dumps(undelete_fields)} expected_bin_state={expected_word}")

    src = sqlite3.connect(f"file:{urllib.parse.quote(SOURCE.as_posix())}?mode=ro", uri=True)
    before = counts(src)
    if COPY.exists():
        COPY.unlink()
    dst = sqlite3.connect(COPY)
    src.backup(dst)
    dst.close()
    src.close()
    print(f"[store] source={SOURCE} mode=ro counts={json.dumps(before, sort_keys=True)}")
    print(f"[store] copy={COPY}")

    port = free_port()
    env = dict(os.environ)
    env["CITYNEXUS_DATABASE_URL"] = f"sqlite:///{COPY.as_posix()}"
    env["CITYNEXUS_PROVIDER_NETWORK_MODE"] = "direct"
    for key in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy"):
        env.pop(key, None)
    server = subprocess.Popen([str(PYTHON), "-X", "utf8", "-m", "uvicorn", "app.main:app",
                               "--host", "127.0.0.1", "--port", str(port), "--log-level", "warning"],
                              cwd=str(REPO / "backend"), env=env, stdout=subprocess.DEVNULL,
                              stderr=subprocess.DEVNULL)
    base = f"http://127.0.0.1:{port}"
    up = False
    for _ in range(60):
        try:
            with httpx.Client(trust_env=False, timeout=2.0) as probe:
                if probe.get(base + "/api/v1/health").status_code == 200:
                    up = True
                    break
        except (httpx.TransportError, OSError):
            time.sleep(0.5)
    listen = win(f"$c = Get-NetTCPConnection -LocalPort {port} -State Listen -EA SilentlyContinue;"
                 " if ($c) { $c | ForEach-Object { $_.OwningProcess } | Select-Object -Unique }")
    parts = (win(f"$p = Get-CimInstance Win32_Process -Filter 'ProcessId={listen.split()[0]}'"
                 " -EA SilentlyContinue; if ($p) { '' + $p.ProcessId + '|' + $p.ParentProcessId +"
                 " '|' + $p.CommandLine }")).split("|", 2)
    parent = parts[1].strip() if len(parts) > 1 else ""
    command = parts[2] if len(parts) > 2 else ""
    identity = (str(server.pid) in str(listen).split()) or (parent == str(server.pid))
    print(f"[server] spawned_pid={server.pid} listener_pid={listen or 'NONE'} "
          f"listener_parent_pid={parent or 'NONE'} health={up} "
          f"command_carries_my_port={'app.main:app' in command and f'--port {port}' in command}")
    print(f"[server] identity_proved={identity}")
    if not (up and identity):
        server.terminate()
        return 4

    failures: list[str] = []
    with httpx.Client(trust_env=False, timeout=15.0) as client:
        live = client.get(base + "/api/v1/journeys").json()
        journey_id = str(live[0]["id"])
        empty = client.get(base + f"/api/v1{panel_path}")
        print(f"[wire] GET {panel_path} before any delete: status={empty.status_code} "
              f"rows={len(empty.json())} is_list={isinstance(empty.json(), list)}")

        assert client.delete(f"{base}/api/v1/journeys/{journey_id}").status_code == 204
        row = client.get(base + f"/api/v1{panel_path}").json()
        keys = sorted(row[0].keys()) if row else []
        missing = [f for f in panel_fields if f not in keys]
        print(f"[wire] bin_rows={len(row)} server_row_keys={json.dumps(keys)}")
        print(f"[wire] panel_fields_missing_from_the_row={json.dumps(missing)} "
              f"bin_state={row[0].get('bin_state') if row else None} "
              f"deleted_at={row[0].get('deleted_at') if row else None}")
        if missing:
            failures.append(f"row missing {missing}")
        if row and str(row[0].get("bin_state")) != expected_word:
            failures.append(f"state word {row[0].get('bin_state')} != {expected_word}")

        restored = client.post(f"{base}/api/v1/journeys/{journey_id}/undelete")
        got = sorted(restored.json().keys()) if restored.status_code == 200 else []
        und_missing = [f for f in undelete_fields if f not in got]
        print(f"[wire] undelete status={restored.status_code} body_keys={json.dumps(got)} "
              f"panel_undelete_fields_missing={json.dumps(und_missing)}")
        if und_missing:
            failures.append(f"undelete body missing {und_missing}")

        refused = client.post(f"{base}/api/v1/journeys/{journey_id}/undelete")
        envelope = refused.json().get("error", {})
        print(f"[wire] repeat undelete status={refused.status_code} code={envelope.get('code')} "
              f"reason_code={envelope.get('reason_code')} "
              f"message_key={envelope.get('message_key')}")
        if envelope.get("reason_code") != "JOURNEY_NOT_DELETED":
            failures.append("the token slice 2 reads is not what the server answers")

        shadow = client.get(base + "/api/v1/journeys/discarded")
        detail = shadow.json().get("error", {})
        errors = (detail.get("details") or {}).get("errors") or []
        first_loc = errors[0]["loc"] if errors else None
        first_type = errors[0].get("type") if errors else None
        receipt = detail.get("error_receipt_id") or detail.get("trace_id")
        print(f"[wire] shadow probe GET /journeys/discarded: status={shadow.status_code} "
              f"code={detail.get('code')} message_key={detail.get('message_key')} "
              f"loc={json.dumps(first_loc)} type={first_type} receipt={receipt}")

    with sqlite3.connect(COPY) as copy_connection:
        after = counts(copy_connection)
    print(f"[store] copy_after counts={json.dumps(after, sort_keys=True)} "
          f"journeys_unchanged={after['journeys'] == before['journeys']} "
          f"activities_unchanged={after['activities'] == before['activities']}")
    server.terminate()
    try:
        server.wait(timeout=15)
    except subprocess.TimeoutExpired:
        server.kill()
    gone = win(f"$c = Get-NetTCPConnection -LocalPort {port} -State Listen -ErrorAction SilentlyContinue;"
               " if ($c) { 'STILL_LISTENING pid=' + (@($c)[0].OwningProcess) } else { 'RELEASED' }")
    print(f"[server] stop_state={gone}")
    print(f"[verdict] mismatches={json.dumps(failures) if failures else 'NONE'}")
    return 0 if not failures else 5


if __name__ == "__main__":
    raise SystemExit(main())
