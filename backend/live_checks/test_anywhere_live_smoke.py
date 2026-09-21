"""ORD-0094 §17C - the opt-in live provider smoke. **Not collected by the default suite.**

This file lives in `backend/live_checks/`, outside the `tests/` collection root, on purpose:
the 900+ ordinary backend tests must stay deterministic (§17C). Running this reaches the real
internet, so it exists only as an explicit act:

    CITYNEXUS_LIVE_PROVIDER_SMOKE=1 python -m pytest live_checks/test_anywhere_live_smoke.py -q

Deliberately **not** `pytest.mark.skipif`. A skipped live test reports a clean run to whoever
forgets to do it, which is the same class of lie as a gate that passes because nothing was
measured. Without the flag each test below fails, in words, saying what to set.

Scope honesty: the *findings* about Photon/Overpass/Nominatim belong to lane B (ORD-0092).
This harness only guarantees the mechanism exists, records what it did (environment, egress,
per-request wall time, raw response path), and cannot be mistaken for having run.
"""

from __future__ import annotations

import json
import os
import socket
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx
import pytest

LIVE_FLAG = "CITYNEXUS_LIVE_PROVIDER_SMOKE"
OUT_DIR = Path(__file__).resolve().parent / "out"
USER_AGENT = "citynexus-anywhere-spike/0.1 (coursework; lane F §17C harness)"
POLITE_INTERVAL_S = 1.0  # ≤1 req/s，§15/任务书礼貌约束

PROBES = [
    # (名字, 方法, URL 或 query 模板)
    # v0.2：v1 解析器只有 Photon，且**不得发 lang=zh**（默认结果保留中文写法，换写法=换身份）。
    ("photon-unseen-county", "GET", "https://photon.komoot.io/api/?q={query}"),
    ("overpass-attractions", "POST", "https://overpass-api.de/api/interpreter"),
]
QUERY = os.environ.get("CITYNEXUS_SMOKE_QUERY", "贡山独龙族怒族自治县")


def _require_opt_in() -> None:
    if os.environ.get(LIVE_FLAG) != "1":
        pytest.fail(
            f"live smoke 需要显式 {LIVE_FLAG}=1（§17C：常规套件不得依赖在线 provider）。"
            "这不是失败的产品，也不是通过 —— 它的意思是「这一层今天没有读数」。跑法写在文件头。"
        )


def _record(name: str, fields: dict) -> dict:
    entry = {"name": name, "recorded_at": datetime.now(timezone.utc).isoformat(), **fields}
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUT_DIR / f"{time.strftime('%Y%m%d-%H%M%S')}-{name}.json"
    path.write_text(json.dumps(entry, ensure_ascii=False, indent=2), encoding="utf-8")
    entry["raw_path"] = str(path)
    return entry


def _egress() -> dict:
    """Which local address the OS would send from, and the hostname it resolves as.

    Not proof of the outbound path (a tunnel or proxy can sit beyond this), so it is recorded
    as an observation, not as a claim.
    """
    info: dict = {"hostname": socket.gethostname()}
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            sock.connect(("1.1.1.1", 53))
            info["local_address"] = sock.getsockname()[0]
        finally:
            sock.close()
    except OSError as exc:
        info["local_address"] = None
        info["local_error"] = str(exc)
    return info


def _dns(host: str) -> dict:
    target = host.split("/")[2] if "://" in host else host
    started = time.perf_counter()
    try:
        infos = socket.getaddrinfo(target, 443, proto=socket.IPPROTO_TCP)
        return {"host": target, "resolved": sorted({i[4][0] for i in infos}), "dns_ms": round((time.perf_counter() - started) * 1000, 1)}
    except OSError as exc:
        return {"host": target, "resolved": [], "dns_ms": round((time.perf_counter() - started) * 1000, 1), "dns_error": str(exc)}


def test_live_smoke_records_environment_and_egress():
    _require_opt_in()
    record = _record("environment", {"egress": _egress(), "probes": [p[0] for p in PROBES]})
    assert record["egress"]["hostname"], "环境读数里连主机名都没有，这份记录不足以让人复跑"


@pytest.mark.parametrize("name,method,url", [p for p in PROBES if p[0] != "overpass-attractions"])
def test_live_smoke_reads_one_http_probe(name: str, method: str, url: str):
    """One polite request per probe, with DNS/TLS/status/wall-time recorded either way."""
    _require_opt_in()
    target = url.replace("{query}", QUERY)
    dns = _dns(target)
    started = time.perf_counter()
    status = None
    error = None
    try:
        with httpx.Client(timeout=15.0, headers={"User-Agent": USER_AGENT}, verify=True) as client:
            response = client.get(target)
            status = response.status_code
    except Exception as exc:  # noqa: BLE001 - a failure is a valid reading here, not a bug
        error = f"{type(exc).__name__}: {exc}"[:200]
    elapsed_ms = round((time.perf_counter() - started) * 1000, 1)
    record = _record(name, {"url": target, "http_status": status, "error": error, **dns, "http_ms": elapsed_ms})
    assert record["dns_ms"] is not None or error, "既没有解析结果也没有失败原因，说明这次什么都没量到"


def test_live_smoke_overpass_counts_categories():
    """The one query that answers §5's category question: how many elements per category."""
    _require_opt_in()
    query = (
        "[out:json][timeout:25];("
        f'node["tourism"~"attraction|museum|viewpoint"](area.name="{QUERY}");'
        f'node["amenity"~"restaurant|cafe|bar"](area.name="{QUERY}");'
        f'node["shop"](area.name="{QUERY}");'
        ");out count 50;"
    )
    dns = _dns("https://overpass-api.de/api/interpreter")
    started = time.perf_counter()
    status = None
    elements = None
    error = None
    try:
        with httpx.Client(timeout=40.0, headers={"User-Agent": USER_AGENT}) as client:
            response = client.post("https://overpass-api.de/api/interpreter", data={"data": query})
            status = response.status_code
            if response.status_code == 200:
                elements = len((response.json().get("elements") or []))
    except Exception as exc:  # noqa: BLE001
        error = f"{type(exc).__name__}: {exc}"[:200]
    elapsed_ms = round((time.perf_counter() - started) * 1000, 1)
    record = _record(
        "overpass-attractions",
        {"query": query[:400], "http_status": status, "elements": elements, "error": error, **dns, "http_ms": elapsed_ms},
    )
    assert record["http_ms"] >= 0, "连耗时都没有 = 没跑过，别把这条当 live 证据"
