"""ORD-0520 residual probe -- can a trip the traveller called off be put back on 实时行程?

What is on the line: `journey_live_view` (`backend/app/services.py`) decides liveness, and the doors
that read it are the ones a traveller stands on (`GET /journeys/{id}/experience`, `GET /journeys/{id}`,
`GET /journeys`).  A follow-up read of the writer side found three doors that move
`journeys.status` without reading it first -- plan select writes `"PLANNED"`
(`backend/app/main.py:7833`), and the two activity-advance doors write `"COMPLETED"`
(`backend/app/main.py:9372`, `backend/app/main.py:9456`) -- while `/start` does read it
(`backend/app/main.py:9184`).  So the question this probe answers with the product's own HTTP surface,
on this lane's own port and its own run-stamped database, is which of those doors actually reach a
cancelled row.

Everything here is a door call plus a read-only row read; 0 product bytes; no stub, no mock.
"""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import urllib.error
import urllib.request
from pathlib import Path

BASE = "http://127.0.0.1:%s/api/v1" % os.environ.get("CITYNEXUS_BACKEND_PORT", "4834")
RUN_ID = os.environ.get("CITYNEXUS_E2E_RUN_ID", "")
DB = Path(os.environ.get("CITYNEXUS_DATABASE_URL", "").replace("sqlite:///", ""))
OUT = Path(__file__).resolve().parent / "ABORT_RESURRECT_PROBE.json"
opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def call(method: str, path: str, body: dict | None = None) -> tuple[int, dict]:
    data = json.dumps(body).encode("utf-8") if body is not None else None
    request = urllib.request.Request(
        BASE + path, data=data, method=method, headers={"Content-Type": "application/json"}
    )
    try:
        with opener.open(request, timeout=240) as answer:
            raw = answer.read()
            status = answer.status
    except urllib.error.HTTPError as error:
        raw = error.read()
        status = error.code
    parsed = json.loads(raw.decode("utf-8")) if raw else {}
    return status, (parsed if isinstance(parsed, dict) else {"_list": parsed})


def row(journey_id: str) -> dict:
    connection = sqlite3.connect("file:" + DB.as_posix() + "?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    try:
        found = connection.execute(
            "select rowid, status, aborted_at, abort_reason, active_plan_version_id, deleted_at "
            "from journeys where id = ?",
            (journey_id,),
        ).fetchone()
        return dict(found) if found else {}
    finally:
        connection.close()


def live_view(journey_id: str) -> dict:
    status, body = call("GET", "/journeys/%s/experience" % journey_id)
    journey = body.get("journey", {}) if isinstance(body, dict) else {}
    return {
        "http_status": status,
        "status": journey.get("status"),
        "aborted_at": journey.get("aborted_at"),
        "abort_reason": journey.get("abort_reason"),
        "live_view": journey.get("live_view"),
    }


def main() -> int:
    if not RUN_ID or not DB.exists():
        print("ABORT: the probe names the run and the database it measured on")
        return 2

    _, traveler = call(
        "POST",
        "/travelers",
        {"display_name": "resurrect probe", "locale": "zh-CN", "timezone": "Asia/Shanghai"},
    )
    _, journey = call(
        "POST",
        "/journeys",
        {
            "traveler_id": traveler["id"],
            "title": "resurrect probe trip",
            "city_code": "CN-TIANJIN",
            "timezone": "Asia/Shanghai",
            "start_at": "2026-10-09T18:00:00+08:00",
            "end_at": "2026-10-11T15:00:00+08:00",
            "budget": {"amount_minor": 120000, "currency": "CNY"},
        },
    )
    journey_id = journey["id"]

    # Can this store produce a plan at all?  On an empty catalogue the answer is a named refusal,
    # and then the select door has nothing to select and cannot be walked here.
    generate_status, generate_body = call("POST", "/journeys/%s/plans/generate" % journey_id)
    _, plans_first = call("GET", "/journeys/%s/plans" % journey_id)
    rows_first = plans_first.get("_list") if "_list" in plans_first else plans_first.get("plans", [])
    rows_first = rows_first or []
    plan_a = rows_first[0]["id"] if rows_first else None
    select_a_status = select_a_body = None
    if plan_a:
        select_a_status, select_a_body = call(
            "POST", "/journeys/%s/plans/%s/select" % (journey_id, plan_a)
        )

    before_abort = live_view(journey_id)
    abort_status, aborted = call(
        "POST",
        "/journeys/%s/abort" % journey_id,
        {"reason": "resurrect probe reason", "actor_traveler_id": traveler["id"]},
    )
    after_abort = live_view(journey_id)
    row_after_abort = row(journey_id)

    # The doors that could move the row, tried one at a time, each answer recorded as it came back.
    start_status, start_body = call("POST", "/journeys/%s/start" % journey_id)
    after_start = row(journey_id)
    live_after_start = live_view(journey_id)

    plan_b = None
    select_b_status = None
    select_b_body = None
    after_select: dict = {}
    row_after_select: dict = {}
    if plan_a:
        call("POST", "/journeys/%s/plans/generate" % journey_id)
        _, plans_second = call("GET", "/journeys/%s/plans" % journey_id)
        rows_second = plans_second.get("_list") if "_list" in plans_second else plans_second.get("plans", [])
        candidates = [p for p in (rows_second or []) if p.get("status") == "CANDIDATE"]
        plan_b = candidates[0]["id"] if candidates else None
        if plan_b:
            # A *different* plan, so the door takes its writing branch instead of its idempotent
            # early return (re-selecting the plan already selected answers without touching the row).
            select_b_status, select_b_body = call(
                "POST", "/journeys/%s/plans/%s/select" % (journey_id, plan_b)
            )
            after_select = live_view(journey_id)
            row_after_select = row(journey_id)

    replay_status, replay_body = call(
        "POST",
        "/journeys/%s/abort" % journey_id,
        {"reason": "resurrect probe second reason", "actor_traveler_id": traveler["id"]},
    )

    resurrected = bool(
        plan_b
        and select_b_status in (200, 201)
        and str(row_after_select.get("status")) != "CANCELLED"
        and bool((after_select.get("live_view") or {}).get("included"))
    )
    verdict = (
        "RESURRECT_REACHABLE"
        if resurrected
        else ("SELECT_DOOR_UNREACHABLE_ON_THIS_STORE" if not plan_a else "RESURRECT_REFUSED")
    )

    receipt = {
        "generated_by": "89f2e2d6",
        "order": "ORD-0520 residual: which doors reach a cancelled row",
        "run_id": RUN_ID,
        "database_basename": DB.name,
        "database_bytes": DB.stat().st_size,
        "git_head": __import__("subprocess").run(
            ["git", "-C", str(Path(__file__).resolve().parents[2]), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
        ).stdout.strip(),
        "journey_id": journey_id,
        "traveler_id": traveler["id"],
        "generate_answer": {
            "http_status": generate_status,
            "reason_code": (generate_body.get("error") or {}).get("reason_code"),
            "error_receipt_id": (generate_body.get("error") or {}).get("error_receipt_id"),
            "places_in_catalog": ((generate_body.get("error") or {}).get("details") or {}).get(
                "places_in_catalog"
            ),
        },
        "plan_a": plan_a,
        "select_a": {"http_status": select_a_status},
        "before_abort": before_abort,
        "abort": {"http_status": abort_status},
        "after_abort": after_abort,
        "row_after_abort": row_after_abort,
        "start_after_abort": {
            "http_status": start_status,
            "answer": start_body.get("error") or start_body.get("detail") or "answered without an error",
            "row_status_after_the_attempt": after_start.get("status"),
            "aborted_at_still_on_row": bool(after_start.get("aborted_at")),
            "live_view_after_the_attempt": live_after_start.get("live_view"),
        },
        "second_select_after_abort": {
            "plan_b": plan_b,
            "http_status": select_b_status,
            "answer": (select_b_body or {}).get("error") if select_b_status not in (200, 201) else None,
            "row_after": row_after_select or None,
            "live_view_after": after_select.get("live_view") if after_select else None,
        },
        "abort_replay_after_the_walk": {
            "http_status": replay_status,
            "reason_code": (replay_body.get("error") or {}).get("reason_code"),
        },
        "resurrected_to_live": resurrected,
        "verdict": verdict,
    }
    OUT.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("verdict %s" % verdict)
    print("receipt %s" % OUT)
    print("receipt_sha1 %s" % hashlib.sha1(OUT.read_bytes()).hexdigest())
    for key in (
        "generate_answer",
        "after_abort",
        "start_after_abort",
        "second_select_after_abort",
        "abort_replay_after_the_walk",
    ):
        print("%s %s" % (key, json.dumps(receipt[key], ensure_ascii=False)[:260]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
