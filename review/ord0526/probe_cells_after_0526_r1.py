"""ORD-0526 follow-up read (no product bytes): does the registered offline source give the four
screens a denominator?

The commander's ledger lists 长图/地图/日历/足迹 as "still without a denominator, waiting for
ORD-0526 to register a source". The source is on the line now, so this probe answers that with
readings instead of a claim: it hydrates a city through the door the source feeds, then asks each
of the doors those screens stand on, and writes down what the server actually says.

It also takes the three ownership receipts, because every number here comes from a backend this
lane started.
"""

from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import sys
import time
import urllib.error
import urllib.request
import uuid as uuidlib
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
PY = r"D:/moodle/CityNexus/.venv/Scripts/python.exe"
TREE = Path(os.environ.get("TREE", "D:/moodle/_qoder_seed_ord0489/wt_cells_514b"))
RUN = Path("D:/moodle/_qoder_seed_ord0489/run")
OUT = Path("D:/moodle/_qoder_seed_ord0489/evidence/ord0526")
PORT = os.environ.get("PORT", "8801")
DB = os.environ.get("DB", "_cells514b")
DB_PATH = RUN / f"{DB}.db"
JOURNEY_DAYS = int(os.environ.get("JOURNEY_DAYS", "2"))


def call(method, path, body=None, timeout=240):
    data = json.dumps(body, ensure_ascii=False).encode("utf-8") if body is not None else None
    req = urllib.request.Request(f"http://127.0.0.1:{PORT}{path}", data=data, method=method,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", "replace")
            return resp.status, (json.loads(raw) if raw[:1] in "[{" else raw[:240])
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", "replace")
        try:
            return exc.code, json.loads(raw)
        except Exception:
            return exc.code, {"raw": raw[:240]}
    except Exception as exc:  # noqa: BLE001
        return -1, {"error": type(exc).__name__, "msg": str(exc)[:200]}


def sh(args):
    p = subprocess.run(args, capture_output=True, text=True, encoding="utf-8", errors="replace")
    return (p.stdout or "") + (p.stderr or "")


for suf in ("", "-wal", "-shm"):
    f = Path(str(DB_PATH) + suf)
    if f.exists():
        f.unlink()
env = dict(os.environ)
env.update({
    "CITYNEXUS_DATABASE_URL": f"sqlite:///{DB_PATH.as_posix()}",
    "CITYNEXUS_REAL_CITY_ENABLED": "true",
    "CITYNEXUS_AI_ENABLED": "false",
    "CITYNEXUS_DEMO_MODE": "false",
    "CITYNEXUS_PROVIDER_NETWORK_MODE": "env_proxy",
    "PYTHONIOENCODING": "utf-8",
})
log = open(RUN / f"backend_{PORT}_{DB}.log", "ab")
proc = subprocess.Popen([PY, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", PORT,
                        "--app-dir", str(TREE / "backend"), "--log-level", "info"],
                        cwd=str(TREE / "backend"), env=env, stdout=log, stderr=subprocess.STDOUT)
report: dict = {"at": datetime.now(timezone.utc).isoformat(), "port": PORT, "tree": str(TREE),
                "tree_head": sh(["git", "-C", str(TREE), "rev-parse", "HEAD"]).strip(),
                "db": str(DB_PATH), "launcher_pid": proc.pid, "journey_days": JOURNEY_DAYS}
try:
    for _ in range(90):
        if call("GET", "/api/v1/health")[0] == 200:
            break
        time.sleep(1)

    # --- the door the registered source feeds ---
    st, job = call("POST", "/api/v1/catalog-hydrations", {"query": "天津"})
    oid = (job or {}).get("operation_id")
    terminal = None
    for _ in range(40):
        time.sleep(3)
        st_t, poll = call("GET", f"/api/v1/catalog-hydrations/{oid}")
        if st_t == 200 and (poll or {}).get("terminal"):
            terminal = poll
            break
    res = (terminal or {}).get("result") or {}
    report["hydration"] = {"operation_id": oid, "status": (terminal or {}).get("status"),
                           "outcome": (terminal or {}).get("outcome"),
                           "survey": res.get("survey"),
                           "coverage_after": res.get("coverage_after"),
                           "missing_categories": res.get("missing_categories"),
                           "offline_source_applied": {
                               k: (res.get("offline_source_applied") or {}).get(k)
                               for k in ("in_effect", "candidate_count", "places_written", "reason")}}
    st_p, places = call("GET", "/api/v1/places?city_code=CN-TIANJIN")
    report["places"] = {"status": st_p, "rows": len(places) if isinstance(places, list) else places}

    # --- a two-day journey, then the door every one of the four screens stands on ---
    st_trav, trav = call("POST", "/api/v1/travelers", {
        "display_name": "四格分母现读", "email": "cells514b@example.invalid",
        "locale": "zh-CN", "timezone": "Asia/Shanghai"})
    start = (datetime.now(timezone.utc) + timedelta(days=7)).replace(
        hour=9, minute=0, second=0, microsecond=0)
    st_j, journey = call("POST", "/api/v1/journeys", {
        "traveler_id": trav["id"], "title": f"天津 · {JOURNEY_DAYS} 天（离线源已登记）",
        "city_code": "CN-TIANJIN", "timezone": "Asia/Shanghai",
        "start_at": start.isoformat(), "end_at": (start + timedelta(days=JOURNEY_DAYS)).isoformat(),
        "budget": {"currency": "CNY", "amount_minor": 600000},
        "planning_mode": "balanced", "party_size": 2,
        "arrival_anchor": {"at": start.isoformat(), "location": "Tianjin Station"}})
    jid = (journey or {}).get("id")
    report["journey"] = {"status": st_j, "id": jid}
    if jid is None:
        raise SystemExit(f"journey door refused: {json.dumps(journey, ensure_ascii=False)[:300]}")

    st_g, gen = call("POST", f"/api/v1/journeys/{jid}/plans/generate", {"candidate_count": 3})
    err = (gen or {}).get("error") if isinstance(gen, dict) else None
    details = (err or {}).get("details") if isinstance(err, dict) else None
    report["plans_generate"] = {
        "status": st_g,
        "candidates_returned": len(gen) if isinstance(gen, list) else None,
        "reason_code": (err or {}).get("reason_code") if isinstance(err, dict) else None,
        "message_verbatim": (err or {}).get("message") if isinstance(err, dict) else None,
        "details": details}

    # --- the four screens' own doors, asked whether or not a plan exists ---
    st_cal, cal = call("GET", f"/api/v1/journeys/{jid}/calendar.ics")
    report["calendar_ics"] = {"status": st_cal,
                              "bytes": len(cal) if isinstance(cal, str) else None,
                              "body_head": (cal[:160] if isinstance(cal, str) else cal)}
    # the footprint door is `/checkins` (the route this build's footprint slice reads and stamps);
    # a made-up path would only prove that FastAPI answers 404, so the name is taken from the route
    # table, and the share door is asked with the field its own refusal names.
    st_fp, fp = call("GET", f"/api/v1/journeys/{jid}/checkins")
    report["checkins_footprint"] = {"status": st_fp, "rows": len(fp) if isinstance(fp, list) else None,
                                    "body": fp if not isinstance(fp, list) else fp[:2]}
    st_h, hist = call("GET", f"/api/v1/journeys/{jid}/history")
    report["history"] = {"status": st_h, "body": hist if not isinstance(hist, dict) else {
        k: hist.get(k) for k in list(hist)[:8]}}
    st_sg, sg = call("POST", f"/api/v1/journeys/{jid}/share-grants",
                     {"visibility": "LINK_READ", "created_by": "lane-5a53846b"})
    token = (sg or {}).get("token") if isinstance(sg, dict) else None
    report["share_grant"] = {"status": st_sg, "visibility_used": "LINK_READ",
                             "token_present": bool(token),
                             "body": {k: sg.get(k) for k in ("id", "journey_id", "visibility",
                                                              "plan_version_id", "revoked_at")}
                             if isinstance(sg, dict) else sg}
    if token:
        st_rc, rc = call("GET", f"/api/v1/shared/journeys/{token}")
        report["share_receive"] = {
            "status": st_rc,
            "body_keys": sorted(rc.keys())[:12] if isinstance(rc, dict) else None,
            "has_plan": bool((rc or {}).get("plan") or (rc or {}).get("active_plan"))
            if isinstance(rc, dict) else None,
            "note": "receiving works with no plan; the four plan-screens still have no denominator"}

    # --- three ownership receipts, in this same batch ---
    listeners = sorted({l.split()[4] for l in sh(["netstat", "-ano", "-p", "TCP"]).splitlines()
                        if len(l.split()) >= 5 and l.split()[0].upper() == "TCP"
                        and l.split()[3].upper() == "LISTENING"
                        and l.split()[1].rsplit(":", 1)[-1] == str(PORT)})
    cmdlines = {pid: sh(["powershell", "-NoProfile", "-Command",
                         f'(Get-CimInstance Win32_Process -Filter "ProcessId={pid}").CommandLine'])
                for pid in listeners}
    con = sqlite3.connect(f"file:{DB_PATH.as_posix()}?mode=ro", uri=True)
    db_places = int(con.execute(
        "select count(*) from places where city_code='CN-TIANJIN'").fetchone()[0])
    db_journey = int(con.execute("select count(*) from journeys where id=?", (jid,)).fetchone()[0])
    con.close()
    st_fake, _ = call("GET", f"/api/v1/journeys/{uuidlib.uuid4()}")
    report["ownership"] = {
        "P1_listener_cmdline_names_tree_and_port": {
            pid: (TREE.name in txt and f"--port {PORT}" in txt) for pid, txt in cmdlines.items()},
        "P2_api_rows_equal_my_file_count": (report["places"].get("rows") == db_places),
        "P2_journey_row_in_this_file": db_journey,
        "P2_fabricated_uuid_status": st_fake,
        "P3_launcher_pid": proc.pid, "P3_listener_pids": listeners,
    }
except BaseException as exc:  # noqa: BLE001 - an aborted probe still has to land on disk
    report["fatal"] = {"type": type(exc).__name__, "msg": str(exc)[:240]}
finally:
    subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"], capture_output=True)

OUT.mkdir(parents=True, exist_ok=True)
target = OUT / f"four_cells_{DB}.json"
target.write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
print(json.dumps(report, ensure_ascii=False, indent=1)[:3000])
print("WROTE", target)
