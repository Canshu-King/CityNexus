"""ORD-0526 · three receipts that the listener on my port is MY backend, taken in one batch.

A 200 on a port is not identity: another lane's server can answer there.  So:

  P1 socket - the PID holding the port, and that PID's own command line naming my tree and `--port`
  P2 store  - a journey id created through my door, read back from the HTTP route *and* from the
              sqlite file that route was configured with; a fabricated uuid must 404
  P3 chain  - parent chain from the PID my launcher recorded up to the listener

Nothing here writes to the shared preview store, and nothing here is inferred from a port number.
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
from datetime import datetime, timezone
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
PY = r"D:/moodle/CityNexus/.venv/Scripts/python.exe"
TREE = Path(os.environ.get("TREE", "D:/moodle/_qoder_seed_ord0489/wt526"))
RUN = Path("D:/moodle/_qoder_seed_ord0489/run")
OUT = Path("D:/moodle/_qoder_seed_ord0489/evidence/ord0526")
PORT = os.environ.get("PORT", "8798")
DB = os.environ.get("DB", "_live0526")
DB_PATH = RUN / f"{DB}.db"
JOURNEY_ID = os.environ.get("JOURNEY_ID", "")
PLACE_NAMES = os.environ.get("PLACE_NAMES", "")


def sh(args: list[str]) -> str:
    p = subprocess.run(args, capture_output=True, text=True, encoding="utf-8", errors="replace")
    return (p.stdout or "") + (p.stderr or "")


def call(path: str, timeout: int = 30) -> tuple[int, object]:
    req = urllib.request.Request(f"http://127.0.0.1:{PORT}{path}", method="GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", "replace")
            return resp.status, json.loads(raw) if raw else None
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8", "replace")[:180]
    except Exception as exc:  # noqa: BLE001
        return -1, {"error": type(exc).__name__, "msg": str(exc)[:160]}


env = dict(os.environ)
env.update({
    "CITYNEXUS_DATABASE_URL": f"sqlite:///{DB_PATH.as_posix()}",
    "CITYNEXUS_REAL_CITY_ENABLED": "true",
    "CITYNEXUS_AI_ENABLED": "false",
    "CITYNEXUS_DEMO_MODE": "false",
    "CITYNEXUS_PROVIDER_NETWORK_MODE": "env_proxy",
    "PYTHONIOENCODING": "utf-8",
})
log = open(RUN / f"backend_{PORT}_prove.log", "ab")
proc = subprocess.Popen([PY, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1",
                         "--port", PORT, "--app-dir", str(TREE / "backend"), "--log-level", "info"],
                        cwd=str(TREE / "backend"), env=env, stdout=log, stderr=subprocess.STDOUT)
report: dict = {"at": datetime.now(timezone.utc).isoformat(), "port": PORT,
                "db_file": str(DB_PATH), "tree": str(TREE), "launcher_pid": proc.pid,
                "env_under_test": {k: env[k] for k in (
                    "CITYNEXUS_DATABASE_URL", "CITYNEXUS_PROVIDER_NETWORK_MODE",
                    "CITYNEXUS_CATALOG_OFFLINE_SOURCES") if k in env}}
try:
    for _ in range(90):
        if call("/api/v1/health")[0] == 200:
            break
        time.sleep(1)

    # P1 - the socket
    listeners = []
    for line in sh(["netstat", "-ano", "-p", "TCP"]).splitlines():
        cols = line.split()
        if len(cols) >= 5 and cols[0].upper() == "TCP" and cols[3].upper() == "LISTENING" \
                and cols[1].rsplit(":", 1)[-1] == str(PORT):
            listeners.append(cols[4])
    pids = sorted(set(listeners))
    cmdlines = {}
    for pid in pids:
        cmdlines[pid] = sh([
            "powershell", "-NoProfile", "-Command",
            f'(Get-CimInstance Win32_Process -Filter "ProcessId={pid}").CommandLine'])
    report["P1_socket"] = {
        "listener_pids": pids,
        "cmdline_names_my_tree": {pid: (str(TREE) in txt or "wt526" in txt)
                                  for pid, txt in cmdlines.items()},
        "cmdline_names_this_port": {pid: (f"--port {PORT}" in txt) for pid, txt in cmdlines.items()},
        "cmdline_raw": {pid: txt.strip()[:300] for pid, txt in cmdlines.items()},
    }

    # P2 - the store behind the answer
    st_j, journey = call(f"/api/v1/journeys/{JOURNEY_ID}") if JOURNEY_ID else (0, "not supplied")
    fake = str(uuidlib.uuid4())
    st_fake, _ = call(f"/api/v1/journeys/{fake}")
    st_p, rows = call("/api/v1/places?city_code=CN-TIANJIN")
    api_names = sorted(r["name"] for r in rows) if isinstance(rows, list) else rows
    con = sqlite3.connect(f"file:{DB_PATH.as_posix()}?mode=ro", uri=True)
    db_place_count = int(con.execute(
        "select count(*) from places where city_code='CN-TIANJIN'").fetchone()[0])
    db_provider = [r[0] for r in con.execute(
        "select distinct provider_key from places where city_code='CN-TIANJIN'")]
    # The row-level source marker, read out of the store the door wrote: a count without a label
    # per row is not "每行带来源标记".
    row_marks = [
        {
            "name": name,
            "provider_key": pk,
            "provenance": json.loads(meta or "{}").get("provenance"),
            "discovery_mode": json.loads(meta or "{}").get("discovery_mode"),
        }
        for name, pk, meta in con.execute(
            "select name, provider_key, metadata_json from places "
            "where city_code='CN-TIANJIN' order by name"
        )
    ]
    db_journey_present = int(con.execute(
        "select count(*) from journeys where id=?", (JOURNEY_ID,)).fetchone()[0]) if JOURNEY_ID else None
    db_hydration_rows = [list(r) for r in con.execute(
        "select outcome, canonical_destination_id from catalog_hydration_operations")]
    con.close()
    report["P2_store"] = {
        "journey_id_echoed_by_api": {"status": st_j,
                                     "id": (journey or {}).get("id") if isinstance(journey, dict) else journey},
        "fabricated_uuid_status": st_fake,
        "api_rows": len(api_names) if isinstance(api_names, list) else api_names,
        "db_count_same_file": db_place_count,
        "counts_agree": isinstance(api_names, list) and len(api_names) == db_place_count,
        "db_provider_keys": db_provider,
        "per_row_source_marks": row_marks,
        "every_row_marked_offline_snapshot": bool(row_marks) and all(
            r["provenance"] == "OFFLINE_SNAPSHOT" and r["provider_key"] == "openstreetmap-replay"
            for r in row_marks
        ),
        "journey_row_in_this_file": db_journey_present,
        "hydration_rows_in_this_file": db_hydration_rows,
    }

    # P3 - who started whom.  Walked UPWARD from the listener, because the listener is a *child* of
    # the PID my launcher recorded: a chain built from the launcher outwards can only ever reach
    # ancestors and would report "listener not in chain" while both facts are perfectly consistent.
    def ascend(start_pid: str) -> tuple[list[str], list[dict]]:
        links, odd, cur = [], [], str(start_pid)
        for _ in range(8):
            txt = sh([
                "powershell", "-NoProfile", "-Command",
                f'$p=Get-CimInstance Win32_Process -Filter "ProcessId={cur}";'
                'if($p){"{0}|{1}|{2}" -f $p.ProcessId,$p.ParentProcessId,$p.Name}']).strip()
            if not txt:
                break
            if "|" not in txt:
                odd.append({"from_pid": cur, "raw": txt[:220]})
                break
            links.append(txt)
            cur = txt.split("|")[1]
        return links, odd

    listener_links, odd = {}, []
    for pid in pids:
        listener_links[pid], bad = ascend(pid)
        odd.extend(bad)
    report["P3_chain"] = {
        "ascended_from_listener": listener_links,
        "unreadable_links": odd,
        "launcher_pid": str(proc.pid),
        "listener_reaches_launcher": any(
            any(f"|{proc.pid}|" in f"{item}|" for item in links) for links in listener_links.values()
        ),
    }
except BaseException as exc:  # noqa: BLE001 - an aborted proof must still land on disk
    report["fatal"] = {"type": type(exc).__name__, "msg": str(exc)[:240]}
finally:
    subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"], capture_output=True)

OUT.mkdir(parents=True, exist_ok=True)
target = OUT / f"ownership_{DB}.json"
target.write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
print(json.dumps(report, ensure_ascii=False, indent=1)[:2600])
print("WROTE", target)
