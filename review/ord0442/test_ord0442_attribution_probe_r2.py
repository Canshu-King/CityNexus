"""ORD-0442 step 1 - probes r2: the two doors whose premise needs the provider leg.

r1 measured the default suite (resolver seam off ⇒ zero egress). This file answers the two
questions that decide g9b and g10, and it can only be answered with the seam opted in, because
`anywhere_capability.anywhere_resolver_name()` is read per call (`app/anywhere_capability.py`):

* q1 - g9b: when a provider call really happens, is it inside an open write transaction *of the
  same connection*, or is the overlap only wall-clock against some other connection's window?
  The door's own predicate (`_overlaps`) compares clocks across every connection, so the two
  readings have different owners: a same-connection hold is a product ordering defect, a
  cross-connection overlap is the ruler measuring its own polling writes.
* q2 - g10: with the leg authorised, what does the capability payload actually return for the
  county the door asks about, and for a county that is known to resolve?
* q3 - the provider itself: what does the resolver answer from this machine (named, no bodies).

Run:
    cp review/ord0442/test_ord0442_attribution_probe_r2.py <tree>/backend/tests/
    ORD0442_PROBE_OUT=<lane>/review/n3_0442_evidence_r1/attribution_probe_r2.json \
    PYTHONPATH=<tree> CityNexus/.venv/Scripts/python.exe -X utf8 -m pytest \
        backend/tests/test_ord0442_attribution_probe_r2.py -q --tb=short
"""

from __future__ import annotations

import json
import os
import re
import sys
import threading
import time
from pathlib import Path

import httpx
import pytest
from sqlalchemy import event

TREE = Path(__file__).resolve().parents[2]
BACKEND = TREE / "backend"
OUT = Path(os.environ.get("ORD0442_PROBE_OUT", str(BACKEND / "ord0442_attribution_probe_r2.json")))

WRITE_VERB = re.compile(r"^\s*(insert|update|delete|replace|create|alter|drop)\b", re.IGNORECASE)
LIVE_HOSTS = (
    "photon.komoot.io",
    "overpass-api.de",
    "overpass.private.coffee",
    "overpass.kumi.systems",
    "nominatim.openstreetmap.org",
)

RESULTS: dict[str, object] = {
    "tree_root": str(TREE).replace("\\", "/"),
    "python_exe": sys.executable.replace("\\", "/"),
    "seam_env_at_start": os.environ.get("CITYNEXUS_ANYWHERE_RESOLVER"),
    "proxy_env": {k: v for k, v in os.environ.items() if "PROXY" in k.upper()},
    "probes": {},
}

WINDOWS: list[dict] = []
OPEN: dict[int, dict] = {}
CALLS: list[dict] = []
LOCK = threading.Lock()


def _install_engine_hooks(engine) -> None:
    @event.listens_for(engine, "begin")
    def _begin(conn):  # noqa: ANN001
        with LOCK:
            OPEN[id(conn)] = {
                "conn": id(conn),
                "engine_conn_repr": type(conn.connection.dbapi_connection).__name__
                if conn.connection is not None else "",
                "thread": threading.get_ident(),
                "started": time.perf_counter(),
                "write": False,
                "statements": [],
            }

    def _close(conn):  # noqa: ANN001
        with LOCK:
            entry = OPEN.pop(id(conn), None)
            if entry is not None:
                entry["ended"] = time.perf_counter()
                WINDOWS.append(entry)

    @event.listens_for(engine, "commit")
    def _commit(conn):  # noqa: ANN001
        _close(conn)

    @event.listens_for(engine, "rollback")
    def _rollback(conn):  # noqa: ANN001
        _close(conn)

    @event.listens_for(engine, "before_cursor_execute")
    def _execute(conn, cursor, statement, parameters, context, executemany):  # noqa: ANN001
        if not WRITE_VERB.match(statement or ""):
            return
        with LOCK:
            entry = OPEN.get(id(conn))
            if entry is not None:
                entry["write"] = True
                entry["statements"].append(re.sub(r"\s+", " ", statement)[:90])


def _install_transport_hooks() -> None:
    original = httpx.HTTPTransport.handle_request

    def patched(self, request, *args, **kwargs):  # noqa: ANN001
        started = time.perf_counter()
        host = str(request.url.host or "")
        try:
            response = original(self, request, *args, **kwargs)
            with LOCK:
                CALLS.append({"host": host, "started": started, "ended": time.perf_counter(),
                              "thread": threading.get_ident(), "outcome": "answered",
                              "status": response.status_code})
            return response
        except BaseException as exc:  # noqa: BLE001
            with LOCK:
                CALLS.append({"host": host, "started": started, "ended": time.perf_counter(),
                              "thread": threading.get_ident(), "outcome": "raised",
                              "error_type": type(exc).__name__})
            raise

    httpx.HTTPTransport.handle_request = patched


def _overlaps(call: dict, windows: list[dict]) -> list[dict]:
    out = []
    for w in windows:
        if w.get("ended") is None:
            continue
        if call["started"] < w["ended"] and call["ended"] > w["started"]:
            out.append(w)
    return out


def test_q1_g9b_overlap_ownership() -> None:
    from app.db.session import engine
    from app.main import app
    from fastapi.testclient import TestClient

    sys.path.insert(0, str(BACKEND / "tests"))
    from demo_stage import demo_reset_headers

    WINDOWS.clear(), OPEN.clear(), CALLS.clear()
    _install_engine_hooks(engine)
    _install_transport_hooks()

    os.environ["CITYNEXUS_ANYWHERE_RESOLVER"] = "photon"
    client = TestClient(app)
    reset = client.post("/api/v1/demo/reset", headers=demo_reset_headers())
    started = client.post("/api/v1/catalog-hydrations", json={"query": "贡山独龙族怒族自治县"})
    operation_id = started.json().get("operation_id")
    body: dict = {}
    deadline = time.perf_counter() + 45.0
    while operation_id and time.perf_counter() < deadline:
        poll = client.get(f"/api/v1/catalog-hydrations/{operation_id}")
        body = poll.json()
        if body.get("terminal") is True or body.get("status") in {
            "COMPLETED", "FAILED", "UNAVAILABLE", "ABANDONED"
        }:
            break
        time.sleep(0.2)

    with LOCK:
        windows = [dict(w) for w in WINDOWS]
        calls = [dict(c) for c in CALLS if c["host"] in LIVE_HOSTS]

    provider_calls = calls
    write_windows = [w for w in windows if w["write"]]
    per_call = []
    for call in provider_calls:
        hits = _overlaps(call, write_windows)
        per_call.append({
            "host": call["host"],
            "call_thread": call["thread"],
            "call_duration_ms": round((call["ended"] - call["started"]) * 1000, 1),
            "outcome": call["outcome"],
            "overlapping_write_window_count": len(hits),
            "write_window_conn_ids": sorted({h["conn"] for h in hits}),
            "same_thread_as_a_write_window": any(h["thread"] == call["thread"] for h in hits),
            "write_window_threads": sorted({h["thread"] for h in hits}),
            "write_window_statements": sorted({s for h in hits for s in h["statements"]})[:6],
            "overlap_ms_vs_call": [
                round((min(call["ended"], h["ended"]) - max(call["started"], h["started"])) * 1000, 1)
                for h in hits
            ],
        })

    RESULTS["probes"]["q1_g9b_overlap"] = {
        "reset_status": reset.status_code,
        "hydration_accepted_status": started.status_code,
        "operation_status": body.get("status"),
        "operation_error_code": str((body.get("error") or {}).get("code")),
        "write_window_total": len(write_windows),
        "provider_call_total": len(provider_calls),
        "test_main_thread": threading.get_ident(),
        "per_call": per_call,
    }
    assert provider_calls, "SETUP 失败：seam 已开但一次 provider 调用都没记录到"
    print("Q1 provider calls:", len(provider_calls), "write windows:", len(write_windows))


def test_q2_g10_capability_with_the_leg_authorised() -> None:
    from app.main import app
    from fastapi.testclient import TestClient

    os.environ["CITYNEXUS_ANYWHERE_RESOLVER"] = "photon"
    client = TestClient(app)
    out: dict = {}
    for label, query in (("unseen_county", "贡山独龙族怒族自治县"), ("yunhe", "云和县"), ("beijing", "Beijing")):
        accepted = client.post("/api/v1/catalog-hydrations", json={"query": query})
        operation_id = accepted.json().get("operation_id") if isinstance(accepted.json(), dict) else None
        body: dict = {}
        deadline = time.perf_counter() + 45.0
        while operation_id and time.perf_counter() < deadline:
            poll = client.get(f"/api/v1/catalog-hydrations/{operation_id}")
            body = poll.json()
            if body.get("terminal") is True or body.get("status") in {
                "COMPLETED", "FAILED", "UNAVAILABLE", "ABANDONED"
            }:
                break
            time.sleep(0.2)
        listing = client.get("/api/v1/destinations/capability", params={"query": query})
        cap = listing.json()
        out[label] = {
            "query": query,
            "hydration_status_code": accepted.status_code,
            "operation_status": body.get("status"),
            "operation_error_code": str((body.get("error") or {}).get("code")),
            "capability": cap.get("capability"),
            "reason_code": cap.get("reason_code"),
            "canonical_destination_id": cap.get("canonical_destination_id"),
            "destination_resolution": json.dumps(cap.get("destination_resolution"), ensure_ascii=False)[:220],
            "place_count": cap.get("place_count"),
            "places_len": len(cap.get("places") or []),
            "candidates_len": len(cap.get("candidates") or []),
            "malformed_candidates_len": len(cap.get("malformed_candidates") or []),
            "hard_gaps": str(cap.get("hard_gaps"))[:160],
            "provider_status": str(cap.get("provider_status"))[:160],
            "coverage": str(cap.get("coverage"))[:220],
            "provenance": str(cap.get("provenance"))[:160],
            "recommended_action": cap.get("recommended_action"),
        }
    RESULTS["probes"]["q2_g10_capability"] = out


def test_q3_provider_answers_from_this_machine() -> None:
    """The raw leg, named: what does the resolver say when the product is allowed to ask?"""

    attempts = []
    for url, params in (
        ("https://photon.komoot.io/api/", {"q": "云和县", "lang": "zh"}),
        ("https://overpass-api.de/api/interpreter", {"data": "[out:json][timeout:5];out count;"}),
    ):
        started = time.perf_counter()
        try:
            response = httpx.get(url, params=params, timeout=15.0,
                                 headers={"User-Agent": "CityNexus-lane-N3-attribution-probe/1"})
            attempts.append({"host": response.request.url.host, "http_status": response.status_code,
                             "bytes": len(response.content),
                             "ms": round((time.perf_counter() - started) * 1000, 1)})
        except BaseException as exc:  # noqa: BLE001
            attempts.append({"host": url.split("/")[2], "outcome": "raised",
                             "error_type": type(exc).__name__,
                             "ms": round((time.perf_counter() - started) * 1000, 1)})
    RESULTS["probes"]["q3_raw_provider_leg"] = {"attempts": attempts}


def test_q9_write_receipt() -> None:
    OUT.write_text(json.dumps(RESULTS, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print("ORD0442_PROBE_OUT", str(OUT).replace("\\", "/"))
