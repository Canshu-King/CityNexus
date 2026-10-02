"""ORD-0543 · the widened leg, asked through the product's own doors.

Reads, in one batch on one private backend:

  1. hydrate CN-TIANJIN through `catalog-hydrations` (the registered offline source from ORD-0526);
  2. create a traveller and a two-day journey, then `plans/generate`;
  3. whether a plan version exists now, and if so the activity rows' `metadata_json.hours_basis`
     (the marker that keeps "scheduled inside the product's band" tellable from "stated hours");
  4. the doors that were waiting on a schedule: `calendar.ics`, a share grant, `checkins`.

Three ownership receipts are taken in the same batch, because every number here comes from a
backend this lane started.
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
TREE = Path(os.environ.get("TREE", "D:/moodle/_qoder_seed_ord0489/wt543"))
RUN = Path("D:/moodle/_qoder_seed_ord0489/run")
OUT = Path("D:/moodle/_qoder_seed_ord0489/evidence/ord0543")
PORT = os.environ.get("PORT", "8803")
DB = os.environ.get("DB", "_dayseq543")
JOURNEY_DAYS = os.environ.get("JOURNEY_DAYS", "2")
FORBIDDEN = ("8000", "4781", "4782", "4783", "4785", "4786", "4787", "8693")


def call(method, path, body=None, timeout=240, extra_headers=None):
    data = json.dumps(body, ensure_ascii=False).encode("utf-8") if body is not None else None
    headers = {"Content-Type": "application/json"}
    headers.update(extra_headers or {})
    req = urllib.request.Request(f"http://127.0.0.1:{PORT}{path}", data=data, method=method,
                                 headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", "replace")
            return resp.status, (json.loads(raw) if raw[:1] in "[{" else raw[:200])
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", "replace")
        try:
            return exc.code, json.loads(raw)
        except Exception:
            return exc.code, {"raw": raw[:200]}
    except Exception as exc:  # noqa: BLE001
        return -1, {"error": type(exc).__name__, "msg": str(exc)[:180]}


def sh(args):
    p = subprocess.run(args, capture_output=True, text=True, encoding="utf-8", errors="replace")
    return (p.stdout or "") + (p.stderr or "")


if PORT in FORBIDDEN:
    raise SystemExit(f"refusing to bind a forbidden port: {PORT}")
DB_PATH = RUN / f"{DB}.db"
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
report: dict = {"at": datetime.now(timezone.utc).isoformat(), "port": PORT, "db": str(DB_PATH),
                "tree": str(TREE), "tree_head": sh(["git", "-C", str(TREE), "rev-parse", "HEAD"]).strip(),
                "launcher_pid": proc.pid, "journey_days": JOURNEY_DAYS}
try:
    for _ in range(90):
        if call("GET", "/api/v1/health")[0] == 200:
            break
        time.sleep(1)

    st, job = call("POST", "/api/v1/catalog-hydrations", {"query": "天津"})
    oid = (job or {}).get("operation_id")
    terminal = None
    for _ in range(40):
        time.sleep(3)
        st_t, poll = call("GET", f"/api/v1/catalog-hydrations/{oid}")
        if st_t == 200 and (poll or {}).get("terminal"):
            terminal = poll
            break
    result = (terminal or {}).get("result") or {}
    report["hydration"] = {"operation_id": oid, "outcome": (terminal or {}).get("outcome"),
                           "survey": result.get("survey"),
                           "outcome_qualifier": result.get("outcome_qualifier")}

    st_trav, trav = call("POST", "/api/v1/travelers", {
        "display_name": "ORD-0543 日序腿", "email": "dayseq@example.invalid",
        "locale": "zh-CN", "timezone": "Asia/Shanghai"})
    start = (datetime.now(timezone.utc) + timedelta(days=7)).replace(
        hour=9, minute=0, second=0, microsecond=0)
    st_j, journey = call("POST", "/api/v1/journeys", {
        "traveler_id": trav["id"], "title": f"天津 · {JOURNEY_DAYS} 天（模板腿加宽后）",
        "city_code": "CN-TIANJIN", "timezone": "Asia/Shanghai",
        "start_at": start.isoformat(),
        "end_at": (start + timedelta(days=int(JOURNEY_DAYS))).isoformat(),
        "budget": {"currency": "CNY", "amount_minor": 600000},
        "planning_mode": "balanced", "party_size": 2,
        "arrival_anchor": {"at": start.isoformat(), "location": "Tianjin Station"}})
    jid = (journey or {}).get("id")
    report["journey"] = {"status": st_j, "id": jid}

    st_g, gen = call("POST", f"/api/v1/journeys/{jid}/plans/generate", {"candidate_count": 3})
    err = (gen or {}).get("error") if isinstance(gen, dict) else None
    details = (err or {}).get("details") if isinstance(err, dict) else None
    report["plans_generate"] = {
        "status": st_g,
        "candidates": len(gen) if isinstance(gen, list) else None,
        "reason_code": (err or {}).get("reason_code") if isinstance(err, dict) else None,
        "details": details,
        "first_plan": (gen[0] if isinstance(gen, list) and gen else None)}

    con = sqlite3.connect(f"file:{DB_PATH.as_posix()}?mode=ro", uri=True)
    plans = [list(r) for r in con.execute(
        "select id, status, utility_score from plan_versions where journey_id=? order by created_at",
        (jid,))]
    acts = [list(r) for r in con.execute(
        "select a.sequence_no, a.title, a.start_at, a.end_at, a.metadata_json "
        "from activities a join plan_versions p on p.id=a.plan_version_id "
        "where p.journey_id=? order by p.created_at, a.sequence_no", (jid,))]
    hours_json = [r[0] for r in con.execute(
        "select opening_hours_json from places where city_code='CN-TIANJIN'")]
    con.close()
    report["plan_versions"] = {"rows": len(plans), "detail": plans[:4]}
    report["activities"] = [
        {"seq": a[0], "title": a[1], "start": a[2][11:16], "end": a[3][11:16],
         "hours_basis": (json.loads(a[4] or "{}").get("hours_basis"))}
        for a in acts[:12]]
    report["store_hours_states"] = {
        "stated": sum(1 for h in hours_json if h and json.loads(h).get("open")),
        "unstated": sum(1 for h in hours_json if not (h and json.loads(h).get("open"))),
        "total": len(hours_json)}

    selected = None
    if isinstance(gen, list) and gen:
        pid = gen[0]["id"]
        st_sel, sel = call("POST", f"/api/v1/journeys/{jid}/plans/{pid}/select", {},
                           extra_headers={"Idempotency-Key": f"ord0543-{uuidlib.uuid4()}"})
        selected = {"status": st_sel, "asked_plan_version_id": pid,
                    "active_plan_version_id": (sel or {}).get("active_plan_version_id")
                    if isinstance(sel, dict) else None,
                    "refusal": None if st_sel in (200, 201, 204) else sel}
    report["select_plan"] = selected

    # `call` truncates a non-JSON body to 200 characters, which made the first pass of this driver
    # report the calendar as "200 bytes, 1 VEVENT" - an artefact of my own instrument. The .ics is
    # therefore fetched whole and counted, and the truncation is stated in the receipt.
    cal_refusal = None
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{PORT}/api/v1/journeys/{jid}/calendar.ics",
                                    timeout=60) as resp:
            raw_ics = resp.read().decode("utf-8", "replace")
            st_c = resp.status
    except urllib.error.HTTPError as exc:
        st_c = exc.code
        raw_ics = ""
        cal_refusal = json.loads(exc.read().decode("utf-8", "replace") or "{}")
    report["calendar_ics"] = {"status": st_c,
                              "bytes_whole_body": len(raw_ics.encode("utf-8")) if raw_ics else 0,
                              "vevent_count": raw_ics.count("BEGIN:VEVENT"),
                              "summary_lines": [line for line in raw_ics.splitlines()
                                                if line.startswith("SUMMARY")][:5],
                              "instrument_note": "counted from the whole body; `call` would have truncated it",
                              "refusal": cal_refusal}
    st_s, sg = call("POST", f"/api/v1/journeys/{jid}/share-grants",
                    {"visibility": "LINK_READ", "created_by": "lane-5a53846b"})
    report["share_grant"] = {"status": st_s,
                             "plan_version_id": (sg or {}).get("plan_version_id")
                             if isinstance(sg, dict) else None}

    listeners = sorted({l.split()[4] for l in sh(["netstat", "-ano", "-p", "TCP"]).splitlines()
                        if len(l.split()) >= 5 and l.split()[0].upper() == "TCP"
                        and l.split()[3].upper() == "LISTENING"
                        and l.split()[1].rsplit(":", 1)[-1] == str(PORT)})
    cmdlines = {pid: sh(["powershell", "-NoProfile", "-Command",
                         f'(Get-CimInstance Win32_Process -Filter "ProcessId={pid}").CommandLine'])
                for pid in listeners}
    st_fake, _ = call("GET", f"/api/v1/journeys/{uuidlib.uuid4()}")
    chain = {}
    for pid in listeners:
        links, cur = [], str(pid)
        for _ in range(8):
            txt = sh(["powershell", "-NoProfile", "-Command",
                      f'$p=Get-CimInstance Win32_Process -Filter "ProcessId={cur}";'
                      'if($p){"{0}|{1}|{2}" -f $p.ProcessId,$p.ParentProcessId,$p.Name}']).strip()
            if "|" not in txt:
                break
            links.append(txt)
            cur = txt.split("|")[1]
        chain[pid] = links
    report["ownership"] = {
        "P1_listener_pids": listeners,
        "P1_cmdline_names_tree_and_port": {
            pid: (TREE.name in txt and f"--port {PORT}" in txt) for pid, txt in cmdlines.items()},
        "P2_journey_echoed": st_j, "P2_fabricated_uuid": st_fake,
        "P3_listener_reaches_launcher": any(
            any(f"|{proc.pid}|" in f"{item}|" for item in links) for links in chain.values()),
        "P3_chains": chain,
    }
except BaseException as exc:  # noqa: BLE001 - an aborted run still has to land
    report["fatal"] = {"type": type(exc).__name__, "msg": str(exc)[:240]}
finally:
    subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"], capture_output=True)

OUT.mkdir(parents=True, exist_ok=True)
target = OUT / f"door_{DB}.json"
target.write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
print(json.dumps(report, ensure_ascii=False, indent=1)[:4200])
print("WROTE", target)
