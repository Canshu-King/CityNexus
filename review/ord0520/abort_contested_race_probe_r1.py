#!/usr/bin/env python3
"""ORD-0520 -- `ABORT_WRITE_CONTESTED` over a socket, with no instrumentation at all.

The pytest arms next to this file force the interleaving by scheduling a committed UPDATE from a
second connection inside the door's read -> UPDATE window (that is how a 5-arm branch gets tested
deterministically, and how its three mutants were killed).  Forcing is a fair tool for a race, but
it leaves one question unanswered: does the branch ever get taken by *timeing alone*, on a real
server, with nothing but an ordinary second writer?

This probe answers that with a count.  It starts `app.main` under uvicorn on a port of its own,
creates one trip per round through the public door, then runs a writer that keeps flipping
`journeys.status` between DRAFT and PLANNED (never CANCELLED, never the bin, never `aborted_at`) in
its own committed transactions while taps call `POST /api/v1/journeys/{id}/abort`.  Every answer is
tallied by `error.reason_code`; the trip is then read back from the store, because a refusal that
still moved the row is not a refusal.

What it prints is a distribution, not a guarantee: on a run where no tap loses three attempts in a
row the honest output is `contested: 0`, and this script says so rather than forcing the branch.

Usage: python review/ord0520/abort_contested_race_probe_r1.py --out review/ord0520/ABORT_RACE_RECEIPT.json
"""
from __future__ import annotations

import argparse
import json
import os
import sqlite3
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

RUN_ID = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
HOST = "127.0.0.1"
PORT = 60521
BASE = f"http://{HOST}:{PORT}"
ROUNDS = 6
TAPS_PER_ROUND = 40
FLIPPERS = 3
OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def call(method: str, path: str, body: dict | None = None) -> tuple[int, dict]:
    data = None if body is None else json.dumps(body, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        f"{BASE}{path}", data=data, method=method,
        headers={"Content-Type": "application/json"} if data else {},
    )
    try:
        with OPENER.open(req, timeout=30) as response:
            raw = response.read()
            return response.status, (json.loads(raw.decode("utf-8")) if raw else {})
    except urllib.error.HTTPError as refused:
        raw = refused.read()
        return refused.code, (json.loads(raw.decode("utf-8")) if raw else {})


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=str(Path(__file__).resolve().parents[2]))
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    root = Path(args.root)
    backend = root / "backend"
    store = backend / f"ord0520_race_{RUN_ID}.db"
    log_path = Path(args.out).with_suffix(".uvicorn.log")
    env = dict(os.environ, PYTHONPATH=f"{backend};{root}",
               CITYNEXUS_DATABASE_URL=f"sqlite:///{store.as_posix()}")
    for name in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy", "DEEPSEEK_API_KEY"):
        env.pop(name, None)
    with log_path.open("wb") as log:
        child = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "app.main:app", "--host", HOST,
             "--port", str(PORT), "--log-level", "warning"],
            cwd=str(backend), env=env, stdout=log, stderr=subprocess.STDOUT,
        )
    receipt: dict = {"run_id": RUN_ID, "store": str(store.resolve()), "port": PORT,
                     "rounds": [], "rounds_configured": ROUNDS,
                     "taps_per_round_configured": TAPS_PER_ROUND, "flippers": FLIPPERS}
    try:
        deadline = time.time() + 90
        while time.time() < deadline:
            if child.poll() is not None:
                raise SystemExit(f"uvicorn exited rc={child.returncode}; see {log_path}")
            try:
                if call("GET", "/health")[0] == 200:
                    break
            except OSError:
                pass
            time.sleep(0.4)

        for round_no in range(1, ROUNDS + 1):
            traveler = call("POST", "/api/v1/travelers", {
                "display_name": f"ORD-0520 race {RUN_ID} r{round_no}",
                "locale": "zh-CN", "timezone": "Asia/Shanghai"})[1]
            journey = call("POST", "/api/v1/journeys", {
                "traveler_id": traveler["id"], "title": f"race r{round_no}",
                "city_code": "CN-XIAMEN", "timezone": "Asia/Shanghai",
                "start_at": "2027-05-06T09:00:00+08:00",
                "end_at": "2027-05-08T17:00:00+08:00",
                "budget": {"amount_minor": 70000, "currency": "CNY"},
                "planning_mode": "balanced"})[1]
            journey_id = journey["id"]
            stop = threading.Event()
            flips = [0]

            def flipper() -> None:
                with sqlite3.connect(store, timeout=60) as conn:
                    while not stop.is_set():
                        current = conn.execute(
                            "SELECT status FROM journeys WHERE id = ?", (journey_id,)
                        ).fetchone()[0]
                        conn.execute("UPDATE journeys SET status = ? WHERE id = ?",
                                     ("DRAFT" if current == "PLANNED" else "PLANNED", journey_id))
                        conn.commit()
                        flips[0] += 1

            writers = [threading.Thread(target=flipper, daemon=True) for _ in range(FLIPPERS)]
            for w in writers:
                w.start()
            tally: dict[str, int] = {}
            receipts: dict[str, str] = {}
            lock = threading.Lock()

            def tap(index: int) -> None:
                status, body = call("POST", f"/api/v1/journeys/{journey_id}/abort",
                                    {"reason": f"争抢读数 第 {index} 拍",
                                     "actor_traveler_id": traveler["id"]})
                reason = (body.get("error") or {}).get("reason_code") or f"http_{status}"
                with lock:
                    tally[reason] = tally.get(reason, 0) + 1
                    receipt = (body.get("error") or {}).get("error_receipt_id")
                    if reason == "ABORT_WRITE_CONTESTED" and receipt:
                        receipts.setdefault(reason, receipt)

            taps = [threading.Thread(target=tap, args=(i,)) for i in range(TAPS_PER_ROUND)]
            for t in taps:
                t.start()
            for t in taps:
                t.join()
            stop.set()
            for w in writers:
                w.join(timeout=5)
            with sqlite3.connect(store) as conn:
                conn.row_factory = sqlite3.Row
                row = dict(conn.execute(
                    "SELECT rowid, status, aborted_at, abort_reason FROM journeys WHERE id = ?",
                    (journey_id,)).fetchone())
                audits = [dict(a) for a in conn.execute(
                    "SELECT rowid, action FROM audit_logs WHERE entity_id = ? AND action = ?",
                    (journey_id, "journey.aborted")).fetchall()]
            receipt["rounds"].append({
                "round": round_no, "journey_id": journey_id, "flips_committed": flips[0],
                "answers_by_reason": tally, "contested_error_receipt_id": receipts.get(
                    "ABORT_WRITE_CONTESTED"),
                "row_after": row, "abort_audit_rows": len(audits),
            })
    finally:
        child.terminate()
        try:
            child.wait(timeout=30)
        except subprocess.TimeoutExpired:
            child.kill()
    contested = sum(r["answers_by_reason"].get("ABORT_WRITE_CONTESTED", 0) for r in receipt["rounds"])
    written_but_refused = [r["round"] for r in receipt["rounds"]
                           if r["answers_by_reason"].get("ABORT_WRITE_CONTESTED")
                           and (r["row_after"]["status"] == "CANCELLED")]
    receipt["totals"] = {
        "taps": sum(len(r["answers_by_reason"]) and sum(r["answers_by_reason"].values())
                    for r in receipt["rounds"]),
        "contested_answers": contested,
        "rounds_with_contested": sum(1 for r in receipt["rounds"]
                                     if r["answers_by_reason"].get("ABORT_WRITE_CONTESTED")),
        "flips_committed": sum(r["flips_committed"] for r in receipt["rounds"]),
        "invariant_rows_written_by_a_refused_tap": written_but_refused,
    }
    # The verdict is computed from the tallies above, never typed in.
    receipt["verdict_computed_from_the_rows_above"] = (
        "CONTESTED_OBSERVED_OVER_SOCKET" if contested else "NOT_OBSERVED_WITHOUT_INSTRUMENTATION"
    )
    if written_but_refused:
        receipt["verdict_computed_from_the_rows_above"] = "FAILED_A_REFUSED_TAP_WROTE_THE_ROW"
    Path(args.out).write_text(json.dumps(receipt, ensure_ascii=False, indent=2),
                              encoding="utf-8", newline="\n")
    print(json.dumps({"verdict": receipt["verdict_computed_from_the_rows_above"],
                      "taps": receipt["totals"]["taps"],
                      "contested": contested,
                      "flips": receipt["totals"]["flips_committed"]}, ensure_ascii=False))
    return 0 if contested else 3


if __name__ == "__main__":
    sys.exit(main())
