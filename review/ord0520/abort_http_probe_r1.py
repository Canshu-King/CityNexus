#!/usr/bin/env python3
"""ORD-0520 -- the abort door over real HTTP, and the row it wrote read back out of the store.

Why this exists rather than a TestClient arm: the order asks for a real HTTP write followed by the
row it produced, named by database and `rowid`.  A status code is not proof of a write, and
`fastapi.testclient` never opens a socket, so nothing in the pytest file proves this door is
reachable on a port the traveller's device could actually call.

Three proofs that the port answers from THIS tree and THIS store, all taken in the same run and
written into the receipt (`ownership`), because a 200 on a free port can be another lane's backend:
  1. the child process: its own command line, its own `CITYNEXUS_DATABASE_URL`, and its own log
     file, which has to show the bind;
  2. a marker row created through the door itself, with a title no other lane uses, read back over
     HTTP from the same port -- the answer carrying it is the proof of who owns the port;
  3. `GET /openapi.json` on that port naming `/api/v1/journeys/{journey_id}/abort`, which only
     exists in this generation's code.

No provider credential is read, printed or written here.  The proxy variables are dropped for every
request (`ProxyHandler({})`) because a `10061` from a dead local proxy is not an unreachable server.

Usage: python review/ord0520/abort_http_probe_r1.py --out review/ord0520/ABORT_HTTP_RECEIPT.json
"""
from __future__ import annotations

import argparse
import json
import os
import sqlite3
import subprocess
import sys
import time
import urllib.error
import urllib.request
import hashlib
import uuid
from datetime import datetime, timezone
from pathlib import Path

RUN_ID = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
HOST = "127.0.0.1"
PORT = 60520
BASE = f"http://{HOST}:{PORT}"
MARKER = f"ORD-0520 abort probe {RUN_ID}"
REASON = "家里临时有事，这趟先不去了（probe）"

opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def _sha1_of(path: Path) -> str:
    return hashlib.sha1(path.read_bytes()).hexdigest()


def request(method: str, path: str, body: dict | None = None) -> tuple[int, dict | None, int]:
    """One real HTTP call.  Returns (http_status, parsed json or None, bytes of the body read)."""
    data = None if body is None else json.dumps(body, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        f"{BASE}{path}",
        data=data,
        method=method,
        headers={"Content-Type": "application/json"} if data else {},
    )
    try:
        with opener.open(req) as response:
            raw = response.read()
    except urllib.error.HTTPError as refused:
        raw = refused.read()
        status = refused.code
        return status, (json.loads(raw.decode("utf-8")) if raw else None), len(raw)
    return response.status, (json.loads(raw.decode("utf-8")) if raw else None), len(raw)


def envelope_of(status: int, body: dict | None, size: int | None = None) -> dict:
    error = (body or {}).get("error") if isinstance(body, dict) else None
    if isinstance(error, dict):
        return {
            "http_status": status,
            "error_code": error.get("code"),
            "reason_code": error.get("reason_code"),
            "message_key": error.get("message_key"),
            "error_receipt_id": error.get("error_receipt_id"),
            "details_keys": sorted((error.get("details") or {}).keys()),
            "body_bytes_read": size,
        }
    return {
        "http_status": status,
        "error_code": None,
        "reason_code": None,
        "message_key": None,
        "error_receipt_id": None,
        "details_keys": [],
        "body_bytes_read": None,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[2]))
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    root = Path(args.root)
    backend = root / "backend"
    store = backend / f"ord0520_probe_{RUN_ID}.db"
    log_path = Path(args.out).with_suffix(".uvicorn.log")
    env = dict(
        os.environ,
        PYTHONPATH=f"{backend};{root}",
        CITYNEXUS_DATABASE_URL=f"sqlite:///{store.as_posix()}",
        PYTHONIOENCODING="utf-8",
    )
    for name in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy", "DEEPSEEK_API_KEY"):
        env.pop(name, None)
    log = log_path.open("wb")
    child = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "app.main:app",
            "--host",
            HOST,
            "--port",
            str(PORT),
            "--log-level",
            "info",
        ],
        cwd=str(backend),
        env=env,
        stdout=log,
        stderr=subprocess.STDOUT,
    )
    receipt: dict = {
        "run_id": RUN_ID,
        "interpreter": sys.executable,
        "tree_root": str(root),
        "store": {"path": str(store.resolve()), "declared_as": env["CITYNEXUS_DATABASE_URL"]},
        "server": {
            "pid": child.pid,
            "port": PORT,
            "command_line": None,
            "log": str(log_path),
            "bind_seen_in_log": False,
            "database_url_in_child_env": env["CITYNEXUS_DATABASE_URL"],
        },
    }
    try:
        # --- proof 1: the child is alive and its own log says it bound this port.
        deadline = time.time() + 60
        healthy = None
        while time.time() < deadline:
            if child.poll() is not None:
                raise SystemExit(f"uvicorn exited early with rc={child.returncode}; see {log_path}")
            try:
                healthy = request("GET", "/health")
                if healthy[0] == 200:
                    break
            except OSError:
                pass
            time.sleep(0.5)
        log.flush()
        log_text = log_path.read_text(encoding="utf-8", errors="replace")
        receipt["server"]["bind_seen_in_log"] = f"{HOST}:{PORT}" in log_text
        # The bind proof has to be produced by this probe, not pasted into the receipt afterwards:
        # the raw log is gitignored, so the lines the server itself printed (and the count and hash
        # of the file they came out of) are written into the receipt here or the evidence does not
        # exist for whoever re-runs this on a later generation.
        receipt["server"]["log_bytes"] = f"{log_path.stat().st_size} B"
        receipt["server"]["log_bytes_sha1_local_not_a_git_object"] = _sha1_of(log_path)
        receipt["server"]["log_excerpt_verbatim"] = [
            line for line in log_text.splitlines()
            if str(PORT) in line or "Uvicorn running" in line or "Application startup" in line
        ]
        receipt["server"]["health_http_status"] = healthy[0] if healthy else None
        try:
            ps = subprocess.run(
                [
                    "powershell",
                    "-NoProfile",
                    "-Command",
                    f"(Get-CimInstance Win32_Process -Filter 'ProcessId={child.pid}')"
                    ".CommandLine",
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            receipt["server"]["command_line"] = (ps.stdout or "").strip()
        except OSError as unreadable:
            receipt["server"]["command_line"] = f"NOT_AVAILABLE_BY_CMDR: {unreadable}"

        # --- proof 2 + the write itself.
        created_traveler = request(
            "POST",
            "/api/v1/travelers",
            {"display_name": f"ORD-0520 probe {RUN_ID}", "locale": "zh-CN", "timezone": "Asia/Shanghai"},
        )
        traveler_id = (created_traveler[1] or {}).get("id")
        created_journey = request(
            "POST",
            "/api/v1/journeys",
            {
                "traveler_id": traveler_id,
                "title": MARKER,
                "city_code": "CN-XIAMEN",
                "timezone": "Asia/Shanghai",
                "start_at": "2026-12-07T09:00:00+08:00",
                "end_at": "2026-12-09T17:00:00+08:00",
                "budget": {"amount_minor": 90000, "currency": "CNY"},
                "planning_mode": "balanced",
            },
        )
        journey_id = (created_journey[1] or {}).get("id")
        listed = request("GET", "/api/v1/journeys")
        mine = [item for item in (listed[1] or []) if item.get("id") == journey_id]
        receipt["ownership"] = {
            "marker_title": MARKER,
            "list_journeys_http_status": listed[0],
            "marker_rows_read_back_over_http": len(mine),
            "marker_live_view_over_http": (mine[0].get("live_view") if mine else None),
        }
        receipt["seed"] = {
            "POST /api/v1/travelers": envelope_of(*created_traveler),
            "POST /api/v1/journeys": envelope_of(*created_journey),
            "journey_id": journey_id,
            "traveler_id": traveler_id,
        }

        def row_from_store() -> dict:
            with sqlite3.connect(store.resolve()) as connection:
                connection.row_factory = sqlite3.Row
                row = connection.execute(
                    "SELECT rowid, id, traveler_id, status, title, created_at, updated_at,"
                    " deleted_at, aborted_at, abort_reason FROM journeys WHERE id = ?",
                    (journey_id,),
                ).fetchone()
                tables = connection.execute(
                    "SELECT COUNT(*) FROM sqlite_master WHERE type='table'"
                ).fetchone()[0]
            return {"row": dict(row) if row else None, "table_count_in_store": tables}

        receipt["before_write"] = row_from_store()

        ok = request(
            "POST", f"/api/v1/journeys/{journey_id}/abort", {"reason": REASON, "actor_traveler_id": traveler_id}
        )
        receipt["abort_200"] = envelope_of(*ok)
        receipt["abort_200"]["response_status"] = (ok[1] or {}).get("status")
        receipt["abort_200"]["response_abort_reason"] = (ok[1] or {}).get("abort_reason")
        receipt["abort_200"]["response_aborted_at"] = (ok[1] or {}).get("aborted_at")
        receipt["abort_200"]["response_live_view"] = (ok[1] or {}).get("live_view")
        receipt["abort_200"]["body_bytes_read"] = ok[2]

        receipt["after_write"] = row_from_store()
        # The row, named by store and rowid -- this is the格 the order asks for.
        experience = request("GET", f"/api/v1/journeys/{journey_id}/experience")
        receipt["experience_after"] = {
            "http_status": experience[0],
            "journey_live_view": (experience[1] or {}).get("journey", {}).get("live_view"),
            "journey_abort_reason": (experience[1] or {}).get("journey", {}).get("abort_reason"),
        }
        listed_after = request("GET", "/api/v1/journeys")
        still = [item for item in (listed_after[1] or []) if item.get("id") == journey_id]
        receipt["list_after"] = {
            "http_status": listed_after[0],
            "still_in_list": len(still) == 1,
            "live_view": still[0].get("live_view") if still else None,
            "abort_reason": still[0].get("abort_reason") if still else None,
        }
        bin_rows = request("GET", "/api/v1/recycle-bin/journeys")
        receipt["recycle_bin_after"] = {
            "http_status": bin_rows[0],
            "aborted_trip_appears_in_bin": any(
                item.get("id") == journey_id for item in (bin_rows[1] or [])
            ),
        }
        audit = None
        with sqlite3.connect(store.resolve()) as connection:
            connection.row_factory = sqlite3.Row
            rows = connection.execute(
                "SELECT rowid, action, actor_type, actor_id FROM audit_logs WHERE entity_id = ?",
                (journey_id,),
            ).fetchall()
            audit = [dict(item) for item in rows]
        receipt["audit_rows_for_this_journey"] = audit

        # --- the four refusals, each over real HTTP, each with its own name.
        refusals: dict = {}
        other = request(
            "POST",
            "/api/v1/travelers",
            {"display_name": f"ORD-0520 outsider {RUN_ID}", "locale": "zh-CN", "timezone": "Asia/Shanghai"},
        )[1]
        cases = {
            "JOURNEY_NOT_FOUND": (
                "POST",
                f"/api/v1/journeys/{uuid.uuid4()}/abort",
                {"reason": REASON, "actor_traveler_id": traveler_id},
            ),
            "ABORT_ACTOR_NOT_OWNER": (
                "POST",
                f"/api/v1/journeys/{journey_id}/abort",
                {"reason": REASON, "actor_traveler_id": (other or {}).get("id")},
            ),
            "JOURNEY_ALREADY_ABORTED": (
                "POST",
                f"/api/v1/journeys/{journey_id}/abort",
                {"reason": "换了个说法再点一次", "actor_traveler_id": traveler_id},
            ),
        }
        binned = request(
            "POST",
            "/api/v1/journeys",
            {
                "traveler_id": traveler_id,
                "title": f"ORD-0520 binned probe {RUN_ID}",
                "city_code": "CN-XIAMEN",
                "timezone": "Asia/Shanghai",
                "start_at": "2026-12-11T09:00:00+08:00",
                "end_at": "2026-12-12T17:00:00+08:00",
                "budget": {"amount_minor": 50000, "currency": "CNY"},
                "planning_mode": "balanced",
            },
        )[1]
        binned_id = (binned or {}).get("id")
        request("DELETE", f"/api/v1/journeys/{binned_id}")
        cases["ABORT_JOURNEY_IN_RECYCLE_BIN"] = (
            "POST",
            f"/api/v1/journeys/{binned_id}/abort",
            {"reason": REASON, "actor_traveler_id": traveler_id},
        )
        for name, (method, path, body) in cases.items():
            status, body_json, size = request(method, path, body)
            envelope = envelope_of(status, body_json)
            envelope["body_bytes_read"] = size
            refusals[name] = envelope
        receipt["refusals_over_http"] = refusals
        with sqlite3.connect(store.resolve()) as connection:
            connection.row_factory = sqlite3.Row
            receipt["binned_row_after_refusal"] = dict(
                connection.execute(
                    "SELECT rowid, status, deleted_at, aborted_at, abort_reason FROM journeys WHERE id = ?",
                    (binned_id,),
                ).fetchone()
            )

        # --- proof 3: the served document names the door (only this generation has it).
        served = request("GET", "/openapi.json")
        paths = (served[1] or {}).get("paths", {}) if isinstance(served[1], dict) else {}
        receipt["served_openapi"] = {
            "http_status": served[0],
            "abort_path_declared": "/api/v1/journeys/{journey_id}/abort" in paths,
            "methods": sorted((paths.get("/api/v1/journeys/{journey_id}/abort") or {})),
            "responses_declared": sorted(
                (paths.get("/api/v1/journeys/{journey_id}/abort") or {}).get("post", {}).get(
                    "responses", {}
                )
            ),
        }

        verdict = (
            receipt["abort_200"]["response_status"] == "CANCELLED"
            and receipt["after_write"]["row"]["status"] == "CANCELLED"
            and receipt["after_write"]["row"]["abort_reason"] == REASON
            and receipt["after_write"]["row"]["aborted_at"]
            and receipt["after_write"]["row"]["deleted_at"] is None
            and receipt["after_write"]["row"]["rowid"] == receipt["before_write"]["row"]["rowid"]
            and receipt["list_after"]["still_in_list"] is True
            and receipt["list_after"]["live_view"]["included"] is False
            and receipt["recycle_bin_after"]["aborted_trip_appears_in_bin"] is False
            and receipt["experience_after"]["journey_live_view"]["included"] is False
            and receipt["ownership"]["marker_rows_read_back_over_http"] == 1
            and receipt["server"]["bind_seen_in_log"] is True
            and receipt["served_openapi"]["abort_path_declared"] is True
            and all(refusals[name]["http_status"] in (403, 404, 409) for name in refusals)
            and all(refusals[name]["error_receipt_id"] for name in refusals)
        )
        receipt["verdict_computed_from_the_rows_above"] = "PASSED" if verdict else "FAILED"
        if not verdict:
            receipt["which_reading_did_not_match"] = {
                "abort_200": receipt["abort_200"],
                "after_write": receipt["after_write"],
                "list_after": receipt["list_after"],
                "experience_after": receipt["experience_after"],
                "ownership": receipt["ownership"],
            }
    finally:
        child.terminate()
        try:
            child.wait(timeout=20)
        except subprocess.TimeoutExpired:
            child.kill()
        log.close()
    receipt["server"]["exit_code_after_terminate"] = child.returncode
    Path(args.out).write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"verdict": receipt["verdict_computed_from_the_rows_above"],
                      "store": receipt["store"]["path"],
                      "rowid": receipt["after_write"]["row"]["rowid"] if receipt.get("after_write") else None},
                     ensure_ascii=False))
    return 0 if receipt["verdict_computed_from_the_rows_above"] == "PASSED" else 1


if __name__ == "__main__":
    sys.exit(main())
