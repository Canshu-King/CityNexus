"""ORD-0526 · drive the door end to end on a private backend and print the four values.

Nothing here is inferred: the hydration job is polled to its terminal state, the survey numbers are
taken from the job's own answer, the place count is re-read through `GET /api/v1/places`, and the
planner is then asked for the city so `places_in_catalog` comes from the door that refuses or
accepts, not from a count of my own.
"""

import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
PY = r"D:/moodle/CityNexus/.venv/Scripts/python.exe"
TREE = Path("D:/moodle/_qoder_seed_ord0489/wt526")
RUN = Path("D:/moodle/_qoder_seed_ord0489/run")
OUT = Path("D:/moodle/_qoder_seed_ord0489/evidence/ord0526")
OUT.mkdir(parents=True, exist_ok=True)
PORT = os.environ.get("PORT", "8798")
DB = os.environ.get("DB", "_live0526")
EXTRA = json.loads(os.environ.get("EXTRA_ENV", "{}"))


def call(base, method, path, body=None, timeout=180):
    data = json.dumps(body, ensure_ascii=False).encode("utf-8") if body is not None else None
    req = urllib.request.Request(base + path, data=data, method=method,
                                headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", "replace")
            return resp.status, (json.loads(raw) if raw else None)
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", "replace")
        try:
            return exc.code, json.loads(raw)
        except Exception:
            return exc.code, {"raw": raw[:400]}
    except Exception as exc:
        return -1, {"error": type(exc).__name__, "msg": str(exc)[:200]}


def main() -> int:
    for suf in ("", "-wal", "-shm"):
        p = RUN / f"{DB}.db{suf}"
        if p.exists():
            p.unlink()
    env = dict(os.environ)
    env.update({
        "CITYNEXUS_DATABASE_URL": f"sqlite:///{(RUN / (DB + '.db')).as_posix()}",
        "CITYNEXUS_REAL_CITY_ENABLED": "true",
        "CITYNEXUS_AI_ENABLED": "false",
        "CITYNEXUS_DEMO_MODE": "false",
        "CITYNEXUS_PROVIDER_NETWORK_MODE": "env_proxy",
        "CITYNEXUS_REAL_CITY_TIMEOUT_SECONDS": "60",
        "PYTHONIOENCODING": "utf-8",
    })
    env.update(EXTRA)
    log = open(RUN / f"backend_{PORT}_{DB}.log", "ab")
    proc = subprocess.Popen([PY, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1",
                             "--port", PORT, "--app-dir", str(TREE / "backend"),
                             "--log-level", "info"],
                            cwd=str(TREE / "backend"), env=env, stdout=log, stderr=subprocess.STDOUT)
    base = f"http://127.0.0.1:{PORT}"
    for _ in range(90):
        if call(base, "GET", "/api/v1/health")[0] == 200:
            break
        time.sleep(1)
    report: dict = {"port": PORT, "db": DB, "extra_env": EXTRA, "at": datetime.now(timezone.utc).isoformat()}
    try:
        st, job = call(base, "POST", "/api/v1/catalog-hydrations", {"query": "天津"})
        report["post_hydration"] = {"status": st, "operation_id": (job or {}).get("operation_id"),
                                    "canonical_destination_id": (job or {}).get("canonical_destination_id"),
                                    "keys": sorted((job or {}).keys())[:14]}
        oid = (job or {}).get("operation_id")
        terminal = None
        for _ in range(60):
            time.sleep(3)
            st_t, poll = call(base, "GET", f"/api/v1/catalog-hydrations/{oid}")
            if st_t == 200 and (poll or {}).get("terminal"):
                terminal = poll
                break
        # The four values live in the job's own `result` layer, not at the top level of the
        # projection: reading the top level returns nulls, so the receipt would report the outcome
        # without the numbers that produced it.
        result = (terminal or {}).get("result") or {}
        report["terminal"] = {
            "status": (terminal or {}).get("status"),
            "phase": (terminal or {}).get("phase"),
            "outcome": (terminal or {}).get("outcome"),
            "canonical_destination_id": (terminal or {}).get("canonical_destination_id"),
            "survey": result.get("survey"),
            "offline_source_applied": result.get("offline_source_applied"),
            "capability_after": result.get("capability_after"),
            "coverage_after": result.get("coverage_after"),
            "missing_categories": result.get("missing_categories"),
            "source_kinds": result.get("source_kinds"),
            "registry": result.get("registry"),
            "result_keys": sorted(result.keys()),
        }
        st_p, rows = call(base, "GET", "/api/v1/places?city_code=CN-TIANJIN")
        report["places_door"] = {
            "status": st_p,
            "rows": len(rows) if isinstance(rows, list) else rows,
            "provider_keys": sorted({r.get("provider_key") for r in rows}) if isinstance(rows, list) else None,
            # The marker every row must carry, per row, plus the columns that hold it: a count
            # alone could not show that no row is unlabelled.
            "per_row": [
                {k: r.get(k) for k in ("id", "name", "city_code", "provider_key", "source",
                                       "provenance", "place_type", "category")}
                for r in rows
            ] if isinstance(rows, list) else None,
            "row_keys": sorted(rows[0].keys()) if isinstance(rows, list) and rows else None,
        }
        st_trav, trav = call(base, "POST", "/api/v1/travelers", {
            "display_name": "ORD-0526 验收", "email": "ord0526@example.invalid",
            "locale": "zh-CN", "timezone": "Asia/Shanghai"})
        start = (datetime.now(timezone.utc) + timedelta(days=6)).replace(microsecond=0, second=0, minute=0, hour=9)
        st_j, journey = call(base, "POST", "/api/v1/journeys", {
            "traveler_id": trav["id"], "title": "天津 · 离线源验收", "city_code": "CN-TIANJIN",
            "timezone": "Asia/Shanghai", "start_at": start.isoformat(),
            "end_at": (start + timedelta(days=1)).isoformat(),
            "budget": {"currency": "CNY", "amount_minor": 600000},
            "planning_mode": "balanced", "party_size": 2,
            "arrival_anchor": {"at": start.isoformat(), "location": "Tianjin Station"}})
        report["journey"] = {"status": st_j, "id": (journey or {}).get("id")}
        st_g, gen = call(base, "POST", f"/api/v1/journeys/{journey['id']}/plans/generate",
                        {"candidate_count": 3}, )
        detail = ((gen or {}).get("error") or {}).get("details") if isinstance(gen, dict) else None
        report["plans_generate"] = {
            "status": st_g,
            "candidates_returned": len(gen) if isinstance(gen, list) else None,
            "reason_code": ((gen or {}).get("error") or {}).get("reason_code") if isinstance(gen, dict) else None,
            "message": ((gen or {}).get("error") or {}).get("message") if isinstance(gen, dict) else None,
            "places_in_catalog": (detail or {}).get("places_in_catalog") if isinstance(detail, dict) else None,
            "day_sequences_available": (detail or {}).get("day_sequences_available") if isinstance(detail, dict) else None,
        }
    finally:
        subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"], capture_output=True)
    target = OUT / f"door_{DB}.json"
    target.write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=1)[:2200])
    print("WROTE", target)
    return 0


if __name__ == "__main__":
    sys.exit(main())
