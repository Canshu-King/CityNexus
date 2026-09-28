"""ORD-0442 - is a write transaction really held across the provider call? (measured at SQLite)

g9b's verdict, and my first reproduction of it, both came from SQLAlchemy event bookkeeping that keys
windows by ``id(conn)`` - a scheme that can confuse a recycled connection object with a live window.
Agreement between two instruments that share one flaw is not confirmation, so this probe asks a source
that cannot be argued with: **SQLite's own locks**.

While a provider call is in flight, a *separate* connection to the same database file attempts
``BEGIN IMMEDIATE``. SQLite answers SQLITE_BUSY ("database is locked") only while another connection
already holds a write (RESERVED) lock, i.e. only if somebody wrote and has not committed. A transaction
that merely *read* leaves ``BEGIN IMMEDIATE`` free to succeed. So the reading separates the two claims:

  ok      -> whatever is open across the call is a read transaction, and g9b's window is bookkeeping
  BUSY    -> a write really is uncommitted while the network call runs: §6/§7 is broken in the product

Run:
    cp review/ord0442/test_ord0442_sqlite_lock_probe_r4.py <tree>/backend/tests/
    ORD0442_PROBE_OUT=<lane>/review/n3_0442_evidence_r1/sqlite_lock_probe_r4.json \
    CITYNEXUS_ANYWHERE_RESOLVER=photon PYTHONPATH=<tree> \
    CityNexus/.venv/Scripts/python.exe -X utf8 -m pytest \
        backend/tests/test_ord0442_sqlite_lock_probe_r4.py -q --tb=short
"""

from __future__ import annotations

import json
import os
import sqlite3
import sys
import threading
import time
from pathlib import Path

import httpx

TREE = Path(__file__).resolve().parents[2]
BACKEND = TREE / "backend"
OUT = Path(os.environ.get("ORD0442_PROBE_OUT", str(BACKEND / "sqlite_lock_probe_r4.json")))

LIVE_HOSTS = ("photon.komoot.io", "overpass-api.de", "nominatim.openstreetmap.org")
RESULTS: dict[str, object] = {"tree": str(TREE).replace("\\", "/"), "probes": {}}


def _write_lock_state(db_file: str) -> dict:
    """Ask SQLite, from its own process-independent lock view, whether a write is uncommitted."""

    started = time.perf_counter()
    try:
        connection = sqlite3.connect(db_file, timeout=0.0)
    except OSError as exc:
        return {"channel": "connect_failed", "error": type(exc).__name__}
    try:
        # autocommit mode, or the driver opens its own transaction and BEGIN IMMEDIATE never runs
        connection.isolation_level = None
        connection.execute("BEGIN IMMEDIATE")
        connection.execute("COMMIT")
        return {"locked": False, "channel": "BEGIN IMMEDIATE accepted",
                "ms": round((time.perf_counter() - started) * 1000, 1)}
    except sqlite3.OperationalError as exc:
        return {"locked": True, "channel": "sqlite3.OperationalError",
                "error": str(exc)[:90],
                "ms": round((time.perf_counter() - started) * 1000, 1)}
    finally:
        connection.close()


def test_q4_lock_state_during_each_provider_call() -> None:
    from app.db.session import engine
    from app.main import app
    from fastapi.testclient import TestClient

    sys.path.insert(0, str(BACKEND / "tests"))
    from demo_stage import demo_reset_headers

    db_file = str(engine.url.database)
    os.environ["CITYNEXUS_ANYWHERE_RESOLVER"] = "photon"
    readings: list[dict] = []
    original = httpx.HTTPTransport.handle_request

    def patched(self, request, *args, **kwargs):  # noqa: ANN001
        host = str(request.url.host or "")
        if host in LIVE_HOSTS:
            # sampled while the call is in flight, on this same thread, before the socket is served
            state = _write_lock_state(db_file)
            readings.append({"host": host, "during_call": state,
                             "thread": threading.get_ident()})
        return original(self, request, *args, **kwargs)

    httpx.HTTPTransport.handle_request = patched
    try:
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
    finally:
        httpx.HTTPTransport.handle_request = original

    RESULTS["probes"]["q4_sqlite_lock_during_provider_call"] = {
        "db_file": db_file.replace("\\", "/"),
        "reset_status": reset.status_code,
        "hydration_accepted_status": started.status_code,
        "operation_status": body.get("status"),
        "operation_error_code": str((body.get("error") or {}).get("code")),
        "provider_calls_sampled": len(readings),
        "calls_locked": sum(1 for r in readings if r["during_call"].get("locked")),
        "readings": readings,
    }


def test_q5_the_lock_probe_can_tell_a_write_from_a_read() -> None:
    """Control arm: the same probe must answer BUSY for an uncommitted write and ok for a read.

    Without this the q4 reading is worthless: a probe that always says "not locked" would exonerate
    the product, and a probe that always says "locked" would convict it.
    """

    from sqlalchemy import select, text

    from app.db.models import CatalogHydrationOperation
    from app.db.session import SessionLocal, engine

    db_file = str(engine.url.database)
    out: dict = {"write_control": None, "read_control": None, "idle": _write_lock_state(db_file)}

    # A scratch table, so the control arm's write cannot be an UPDATE that matched zero rows (which
    # would take no RESERVED lock and would fake an "unlocked" reading), and it touches no product row.
    scratch = SessionLocal()
    try:
        scratch.execute(text("DROP TABLE IF EXISTS ord0442_lock_scratch"))
        scratch.execute(text("CREATE TABLE ord0442_lock_scratch (x INTEGER)"))
        scratch.commit()
        scratch.execute(text("INSERT INTO ord0442_lock_scratch (x) VALUES (1)"))
        out["write_control"] = _write_lock_state(db_file)
        scratch.rollback()
        scratch.execute(text("DROP TABLE IF EXISTS ord0442_lock_scratch"))
        scratch.commit()
    finally:
        scratch.close()

    read_session = SessionLocal()
    try:
        read_session.execute(
            select(CatalogHydrationOperation.id).limit(1)
        ).all()
        out["read_control"] = _write_lock_state(db_file)
    finally:
        read_session.rollback()
        read_session.close()

    out["discriminator_holds"] = bool(
        (out["write_control"] or {}).get("locked") is True
        and (out["read_control"] or {}).get("locked") is False
    )
    RESULTS["probes"]["q5_lock_probe_control"] = out


def test_q9_write_receipt() -> None:
    OUT.write_text(json.dumps(RESULTS, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print("ORD0442_PROBE_OUT", str(OUT).replace("\\", "/"))
