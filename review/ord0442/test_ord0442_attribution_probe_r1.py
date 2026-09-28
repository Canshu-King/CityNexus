"""ORD-0442 step 1 - attribution probes for the twelve named backend reds.

This file ships nothing and asserts almost nothing: it *measures* the facts that decide which of
the three named classes each red belongs to (真缺陷 / ENVIRONMENT_NOT_PRODUCIBLE_ON_LINE / 尺过期),
and writes them to one JSON receipt so the ruling can be checked without re-reading my reasoning.

Run it from a copy of the tree it is probing:

    cp review/ord0442/test_ord0442_attribution_probe_r1.py <tree>/backend/tests/
    PYTHONPATH=<tree> <CityNexus/.venv>/Scripts/python.exe -X utf8 -m pytest \
        backend/tests/test_ord0442_attribution_probe_r1.py -q --tb=line

It runs against the same private test database the suite already uses (conftest declares the
process a simulation stage); it never touches ports 8000/4781/4782/8693.
"""

from __future__ import annotations

import io
import json
import os
import re
import socket
import sys
import time
from pathlib import Path

import httpx
import pytest

TREE = Path(__file__).resolve().parents[2]
BACKEND = TREE / "backend"
OUT = Path(os.environ.get("ORD0442_PROBE_OUT", str(BACKEND / "ord0442_attribution_probe_r1.json")))

RESULTS: dict[str, object] = {
    "tree_root": str(TREE).replace("\\", "/"),
    "python": sys.version.split()[0],
    "python_exe": sys.executable.replace("\\", "/"),
    "proxy_env": {k: v for k, v in os.environ.items() if "PROXY" in k.upper()},
    "probes": {},
}


def record(name: str, payload: dict) -> None:
    RESULTS["probes"][name] = payload


# --------------------------------------------------------------------------------------- P1 matrix
def test_p1_matrix_shape_for_eleven_nodes(monkeypatch) -> None:
    """g14a / g14c: does an N=11 capture still send an oversized request?"""

    sys.path.insert(0, str(BACKEND / "tests"))
    import test_qoder_anywhere_matrix_truth as mt

    probe = mt.MatrixProbe()
    result = mt._capture(monkeypatch, probe, 11)
    reworded = mt.MatrixProbe(error_body={"error_code": 150, "status_code": 400, "error": "リクエストが大きすぎます"})
    second = mt._capture(monkeypatch, reworded, 11)
    twenty = mt.MatrixProbe()
    r20 = mt._capture(monkeypatch, twenty, 20)

    cells = [item["cells"] for item in probe.matrix_requests]
    record(
        "p1_matrix_shape",
        {
            "max_cells_setting": mt.MAX_CELLS,
            "n11_requests": len(cells),
            "n11_cells": cells,
            "n11_any_request_oversized": any(c > mt.MAX_CELLS for c in cells),
            "n11_status": result.get("status"),
            "n11_keys": sorted(result),
            "n11_has_error_type_key": "error_type" in result,
            "n11_reworded_status": second.get("status"),
            "n11_reworded_has_error_type_key": "error_type" in second,
            "n20_requests": len(twenty.matrix_requests),
            "n20_cells_max": max([i["cells"] for i in twenty.matrix_requests] or [0]),
            "n20_status": r20.get("status"),
            "n20_facts": len(r20.get("facts") or []),
        },
    )


# --------------------------------------------------------------------------- P2 hydration + egress
def test_p2_hydration_egress_and_capability_payload() -> None:
    """g9b / g10: did the product actually reach a provider, and what did the doors then read?"""

    from app.core.config import settings
    from app.main import app
    from fastapi.testclient import TestClient

    client = TestClient(app)

    attempts: list[dict] = []
    original = httpx.HTTPTransport.handle_request

    def spy(self, request, *args, **kwargs):  # noqa: ANN001
        host = str(request.url.host or "")
        try:
            response = original(self, request, *args, **kwargs)
            attempts.append({"host": host, "outcome": "answered", "status": response.status_code})
            return response
        except BaseException as exc:  # noqa: BLE001 - recording, then re-raising unchanged
            attempts.append({"host": host, "outcome": "raised", "error_type": type(exc).__name__,
                             "error_first_120": str(exc)[:120]})
            raise

    httpx.HTTPTransport.handle_request = spy
    try:
        reset = client.post("/api/v1/demo/reset", headers=_demo_headers())
        started = client.post("/api/v1/catalog-hydrations", json={"query": "贡山独龙族怒族自治县"})
        operation_id = started.json().get("operation_id") if _is_dict(started) else None
        body: dict = {}
        polls = 0
        deadline = time.perf_counter() + 45.0
        while operation_id and time.perf_counter() < deadline:
            poll = client.get(f"/api/v1/catalog-hydrations/{operation_id}")
            polls += 1
            body = poll.json() if _is_dict(poll) else {}
            if body.get("terminal") is True or body.get("status") in {
                "COMPLETED", "FAILED", "UNAVAILABLE", "ABANDONED"
            }:
                break
            time.sleep(0.2)
        listing = client.get("/api/v1/destinations/capability", params={"query": "贡山独龙族怒族自治县"})
        cap = listing.json() if _is_dict(listing) else {}
    finally:
        httpx.HTTPTransport.handle_request = original

    provider_hosts = sorted({a["host"] for a in attempts})
    gate_names = sorted(
        name for name in dir(settings)
        if re.search(r"photon|overpass|valhalla|nominatim|egress|live_|proxy", name, re.I)
    )
    record(
        "p2_hydration_egress",
        {
            "reset_status": reset.status_code,
            "hydration_accepted_status": started.status_code,
            "operation_id_present": bool(operation_id),
            "polls": polls,
            "operation_status": body.get("status"),
            "operation_keys": sorted(body),
            "operation_failure_fields": {
                k: str(v)[:200] for k, v in body.items()
                if re.search(r"reason|error|detail|stage", k, re.I)
            },
            "capability_status": listing.status_code,
            "capability_keys_all": sorted(cap),
            "capability_verdict": cap.get("capability"),
            "capability_reason_code": cap.get("reason_code"),
            "capability_places_len": len(cap.get("places") or []),
            "capability_candidates_len": len(cap.get("candidates") or []),
            "capability_malformed_candidates_len": len(cap.get("malformed_candidates") or []),
            "capability_hard_gaps": str(cap.get("hard_gaps"))[:200],
            "capability_provider_status": str(cap.get("provider_status"))[:200],
            "egress_attempts_total": len(attempts),
            "egress_hosts": provider_hosts,
            "egress_detail": attempts[:12],
            "settings_gate_names": gate_names,
            "settings_gate_values": {name: str(getattr(settings, name))[:80] for name in gate_names},
        },
    )


def _demo_headers() -> dict:
    sys.path.insert(0, str(BACKEND / "tests"))
    from demo_stage import demo_reset_headers

    return demo_reset_headers()


def _is_dict(response) -> bool:
    try:
        return isinstance(response.json(), dict)
    except Exception:  # noqa: BLE001
        return False


# ------------------------------------------------------------------------------------- P3 agent run
def test_p3_agent_command_run_shape() -> None:
    """g5: what does a no-op AI run actually leave behind, field by field?"""

    sys.path.insert(0, str(BACKEND / "tests"))
    import test_qoder_anywhere_gates as gt

    journey_id = gt._seeded_journey_id()
    response = gt.client.post(
        f"/api/v1/journeys/{journey_id}/agent/commands",
        json={"command": "帮我把这趟行程重新安排一下", "requested_autonomy": "PLAN_ONLY"},
    )
    body = response.json() if isinstance(response.json(), dict) else {}
    run = body.get("run") if isinstance(body, dict) else None
    run = run if isinstance(run, dict) else {}
    outcome = run.get("outcome")

    contract_hits: list[str] = []
    for path in sorted((TREE / "contracts").glob("*.yaml")):
        text = io.open(path, encoding="utf-8", errors="replace").read()
        hits = [line.strip()[:90] for line in text.splitlines() if re.search(r"\boutcome\b", line)]
        if hits:
            contract_hits.append(f"{path.name}:{len(hits)} -> {hits[:4]}")

    emitters: list[str] = []
    for path in sorted((BACKEND / "app").rglob("*.py")):
        for number, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            if re.search(r"[\"']outcome[\"']\s*:", line) or re.search(r"\.outcome\s*=", line):
                emitters.append(f"{path.relative_to(BACKEND).as_posix()}:{number}: {line.strip()[:100]}")

    record(
        "p3_agent_run",
        {
            "http_status": response.status_code,
            "top_level_keys": sorted(body),
            "run_keys": sorted(run),
            "run_status": run.get("status"),
            "run_failure_reason": str(run.get("failure_reason"))[:160],
            "run_outcome_type": type(outcome).__name__,
            "run_outcome_value": str(outcome)[:160],
            "outcome_required_statuses": sorted(getattr(gt, "OUTCOME_STATUSES", set())),
            "contracts_mention_outcome": contract_hits,
            "product_outcome_emitters": emitters[:12],
            "product_outcome_emitter_count": len(emitters),
        },
    )


# --------------------------------------------------------------------------- P4 failure reason codes
def test_p4_live_failure_reason_mapping() -> None:
    """city_failure_reasons: is 5xx really split from a malformed 2xx, and since when?"""

    from app.integrations.discovery import real_city

    def status_error(code: int):
        request = httpx.Request("GET", "https://provider.example/x")
        response = httpx.Response(code, request=request)
        return httpx.HTTPStatusError("shape", request=request, response=response)

    shapes = {
        "connect_timeout": httpx.ConnectTimeout("t"),
        "read_error": httpx.ReadError("x"),
        "status_429": status_error(429),
        "status_500": status_error(500),
        "status_502": status_error(502),
        "keyerror_lat": KeyError("lat"),
        "json_shape": ValueError(" Expecting value"),
        "runtime_no_anchor": RuntimeError("NO_JOURNEY_DERIVED_CITY_ANCHOR"),
        "internal_code": ValueError("RESOLVER_LABEL_CARRIES_INTERNAL_CODE"),
    }
    mapped = {name: real_city.live_failure_reason(exc) for name, exc in shapes.items()}
    record(
        "p4_live_failure_reasons",
        {
            "mapped": mapped,
            "declared_codes": sorted(real_city.LIVE_FAILURE_REASONS),
            "five_hundred_and_four_twenty_nine_differ": mapped["status_500"] != mapped["status_429"],
            "five_hundred_and_malformed_body_differ": mapped["status_500"] != mapped["keyerror_lat"],
        },
    )


# ------------------------------------------------------------------------------- P5 lock wait copies
def test_p5_lock_wait_single_source() -> None:
    """G4: does the extra module name carry a second inline copy, or a reference?"""

    needles = ("busy_timeout=30000", "busy_timeout = 30000", '"timeout": 30')
    offenders: dict[str, list[int]] = {}
    others: dict[str, list[str]] = {}
    literal_30000: list[str] = []
    for path in sorted((BACKEND / "app").rglob("*.py")):
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if any(needle in line for needle in needles):
                offenders.setdefault(path.relative_to(BACKEND).as_posix(), []).append(number)
            elif "busy_timeout" in line:
                others.setdefault(path.relative_to(BACKEND).as_posix(), []).append(line.strip()[:100])
            if re.search(r"busy_timeout\D{0,4}30000|30000\D{0,12}busy_timeout", line):
                literal_30000.append(f"{path.relative_to(BACKEND).as_posix()}:{number}")

    definition = (BACKEND / "app" / "db" / "write_deadline.py").read_text(encoding="utf-8")
    record(
        "p5_lock_wait",
        {
            "inline_copy_offenders": offenders,
            "mentioning_files": sorted(Path(key).name for key in others),
            "main_py_lines": others.get("app/main.py", []),
            "literal_30000_with_busy_timeout": literal_30000,
            "write_deadline_defines_busy_timeout_ms": bool(re.search(r"def busy_timeout_ms\(", definition)),
            "write_deadline_default_lines": [
                line.strip()[:110] for line in definition.splitlines()
                if re.search(r"busy_timeout|30000|DEFAULT", line)
            ][:8],
        },
    )


# ------------------------------------------------------------------------ P6 socket guard on offenders
def test_p6_flagged_lines_make_no_socket_connection(monkeypatch) -> None:
    """g8a: a hostname literal next to a call token is not the same fact as a socket."""

    connects: list[str] = []
    real_connect = socket.socket.connect

    def guard(self, address, *args, **kwargs):  # noqa: ANN001
        connects.append(str(address))
        raise AssertionError(f"期望：这一格不出网；实际有人想连 {address}")

    monkeypatch.setattr(socket.socket, "connect", guard)

    from app.integrations.discovery.provider_identity import HttpxTransport, build_httpx_client

    client = build_httpx_client(
        transport=httpx.MockTransport(lambda request: httpx.Response(200, json={"features": []}))
    )
    transport = HttpxTransport(client=client, timeout_s=5.0)
    try:
        status, _headers, body = transport.get("https://photon.komoot.io/api/", {"q": "x"})
    finally:
        client.close()

    seen: list[str] = []
    original = httpx.HTTPTransport.handle_request

    def spy(self, request, *a, **kw):  # noqa: ANN001
        host = str(request.url.host or "")
        seen.append(host)
        if host == "photon.komoot.io":
            raise AssertionError("期望：本笔范围内不出网；实际出网")
        return original(self, request, *a, **kw)

    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", spy)
    with pytest.raises(AssertionError, match="本笔范围内不出网"):
        httpx.get("https://photon.komoot.io/api/?q=instrument-selftest", timeout=1.0)

    monkeypatch.setattr(socket.socket, "connect", real_connect)
    record(
        "p6_socket_guard",
        {
            "mock_transport_status": status,
            "mock_transport_body_features": json.loads(body).get("features"),
            "spy_recorded_hosts": seen,
            "socket_connect_attempts": connects,
            "socket_connect_attempt_count": len(connects),
        },
    )


# --------------------------------------------------------------------------------------- write out
def test_p9_write_receipt() -> None:
    OUT.write_text(json.dumps(RESULTS, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print("ORD0442_PROBE_OUT", str(OUT).replace("\\", "/"), "probes", len(RESULTS["probes"]))
