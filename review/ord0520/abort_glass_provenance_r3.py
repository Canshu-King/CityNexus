"""ORD-0520 glass walk - prove the stack the arms ran on belongs to this run, in one batch.

Why this file exists: the cell it closes is "the sentence was never read off a screen", and the easy
way to fake that reading is a 200 from somebody else's backend under my port.  A shared preview has
been wiped twice this month by a lane that assumed its own port was its own.  So the run issues a
per-run id into the backend it starts, and the receipt below is only GREEN when all four of these
hold together:

  P1 the backend on the named port answers the run id this invocation issued, and names the database
     file this invocation created (``/api/v1/health`` echoes both only when CITYNEXUS_E2E_RUN_ID is
     set -- see ``backend/app/main.py`` health handler);
  P2 the same two answers arrive *through the frontend port*, which is what makes the dev server's
     proxy target this backend rather than a borrowed ``:8000``;
  P3 the module graph served on the frontend port resolves inside this tree: the request for
     ``src/features/abort/JourneyAbortPanel.tsx`` answers, and the bytes it answers carry a marker
     this component owns.  The served bytes are Vite's transform, so they are deliberately NOT
     compared to the disk file's sha1 -- both sha1s are recorded and the claim is only the marker;
  P4 the two PIDs holding those ports were started by this lane: the command line behind each port
     is read from the process table, not assumed from the port being free.

0 product bytes; it writes only its own receipt.
"""

from __future__ import annotations

# r3 of abort_glass_provenance_r1.py -- one guard added at the verdict site: all four P-checks must have produced a record; an empty failures list alone proves nothing

import hashlib
import json
import os
import subprocess
import sys
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
OUT = REPO / "review" / "ord0520" / (
    "ABORT_GLASS_PROVENANCE_%s.json" % os.environ.get("CITYNEXUS_E2E_RUN_ID", "unset_run_id")
)
SHARED_PORTS = (8000, 4781, 4782, 8693)


def refuse_unless_all_present(records, what: str) -> None:
    """Refuse unless every expected record is there, not merely unless none is.

    `refuse_when_empty` only catches the total absence of data.  A partial run -- one, two or three of the
    four checks recorded -- used to pass, which is the same defect one step in: the verdict was computed
    over a shorter set than the one it claims to cover.
    """

    missing = [i for i, item in enumerate(records) if not item]
    if missing:
        print("REFUSE: %s is missing %d of %d records (missing at %s), so a verdict over it would be "
              "computed over a shorter set than it claims" % (what, len(missing), len(records), missing))
        raise SystemExit(2)

def opener():
    """No proxy: a registry proxy would turn a live server into an unreachable one and back."""
    return urllib.request.build_opener(urllib.request.ProxyHandler({}))


def get_json(url: str) -> tuple[int, dict, int]:
    request = urllib.request.Request(url, headers={"Accept": "application/json"})
    with opener().open(request, timeout=20) as answer:
        raw = answer.read()
    return answer.status, json.loads(raw.decode("utf-8")), len(raw)


def text_at(url: str) -> tuple[int, bytes]:
    with opener().open(urllib.request.Request(url), timeout=30) as answer:
        return answer.status, answer.read()


def listener(pid_port: str) -> dict:
    """Which PID owns the port, and what it was started with."""
    probe = subprocess.run(
        ["netstat", "-ano", "-p", "TCP"], capture_output=True, text=True, errors="replace"
    )
    pid = None
    for line in probe.stdout.splitlines():
        if pid_port in line and "LISTENING" in line:
            pid = line.split()[-1]
            break
    if pid is None:
        return {"pid": None, "command_line": None}
    ps = (
        "Get-CimInstance Win32_Process -Filter \"ProcessId={pid}\" "
        "| ForEach-Object {{ $_.CommandLine }}".format(pid=pid)
    )
    read = subprocess.run(
        ["powershell", "-NoProfile", "-Command", ps], capture_output=True, text=True, errors="replace"
    )
    return {"pid": pid, "command_line": (read.stdout or "").strip()}


def main() -> int:
    run_id = os.environ.get("CITYNEXUS_E2E_RUN_ID", "")
    database_url = os.environ.get("CITYNEXUS_DATABASE_URL", "")
    frontend_port = os.environ.get("CITYNEXUS_ORD0520_PORT", "")
    backend_port = os.environ.get("CITYNEXUS_BACKEND_PORT", "")
    for name, value in [
        ("CITYNEXUS_E2E_RUN_ID", run_id),
        ("CITYNEXUS_DATABASE_URL", database_url),
        ("CITYNEXUS_ORD0520_PORT", frontend_port),
        ("CITYNEXUS_BACKEND_PORT", backend_port),
    ]:
        if not value:
            print("ABORT: %s is not set; this receipt names the run it belongs to" % name)
            return 2
    for port_name, port_value in [("frontend", frontend_port), ("backend", backend_port)]:
        if int(port_value) in SHARED_PORTS:
            print("ABORT: %s port %s is a shared port" % (port_name, port_value))
            return 2

    expected_db = database_url.replace("sqlite:///", "").split("/")[-1]
    backend_health_url = "http://127.0.0.1:%s/api/v1/health" % backend_port
    frontend_health_url = "http://127.0.0.1:%s/api/v1/health" % frontend_port
    module_url = "http://127.0.0.1:%s/src/features/abort/JourneyAbortPanel.tsx" % frontend_port

    p1 = {}
    p2 = {}
    p3 = {}
    p4 = {}
    failures: list[str] = []

    status, body, size = get_json(backend_health_url)
    p1 = {
        "url": backend_health_url,
        "http_status": status,
        "answer_bytes": size,
        "e2e_run_id": body.get("e2e_run_id", ""),
        "e2e_database_id": body.get("e2e_database_id", ""),
        "ai": body.get("ai", ""),
        "database": body.get("database", ""),
    }
    if p1["e2e_run_id"] != run_id:
        failures.append("P1 the backend on :%s answers run id %r, not this run's %r" % (backend_port, p1["e2e_run_id"], run_id))
    if p1["e2e_database_id"] != expected_db:
        failures.append("P1 the backend opened %r, not this run's %r" % (p1["e2e_database_id"], expected_db))
    if p1["ai"] != "disabled":
        failures.append("P1 external AI is not off: %r" % p1["ai"])

    status2, body2, size2 = get_json(frontend_health_url)
    p2 = {
        "url": frontend_health_url,
        "http_status": status2,
        "answer_bytes": size2,
        "e2e_run_id": body2.get("e2e_run_id", ""),
        "e2e_database_id": body2.get("e2e_database_id", ""),
        "same_run_id_as_direct_read": body2.get("e2e_run_id", "") == p1["e2e_run_id"],
        "same_database_as_direct_read": body2.get("e2e_database_id", "") == p1["e2e_database_id"],
    }
    if not (p2["same_run_id_as_direct_read"] and p2["same_database_as_direct_read"]):
        failures.append("P2 the frontend on :%s is proxying to a backend that is not this run's" % frontend_port)

    module_path = REPO / "frontend" / "src" / "features" / "abort" / "JourneyAbortPanel.tsx"
    disk_bytes = module_path.read_bytes()
    mstatus, served = text_at(module_url)
    marker = b'"journey-aborted-notice"'
    marker_found = marker in served or b"journey-aborted-notice" in served
    p3 = {
        "url": module_url,
        "http_status": mstatus,
        "served_bytes": len(served),
        "served_bytes_sha1": hashlib.sha1(served).hexdigest(),
        "disk_bytes": len(disk_bytes),
        "disk_bytes_sha1": hashlib.sha1(disk_bytes).hexdigest(),
        "marker": "journey-aborted-notice",
        "marker_in_served_module": bool(marker_found),
        "served_and_disk_bytes_equal": served == disk_bytes,
        "note": "the served bytes are Vite's transform of this file, so the two hashes differ by "
        "design; the claim is only that the module this tree holds answers on this port and carries "
        "the marker this component owns",
    }
    if mstatus != 200 or not p3["marker_in_served_module"]:
        failures.append("P3 the frontend on :%s did not serve this tree's abort component" % frontend_port)

    p4 = {
        "backend_port": listener(":%s " % backend_port),
        "frontend_port": listener(":%s " % frontend_port),
    }
    backend_line = str(p4["backend_port"].get("command_line") or "")
    frontend_line = str(p4["frontend_port"].get("command_line") or "")
    if "uvicorn" not in backend_line or "--port %s" % backend_port not in backend_line:
        failures.append("P4 the process behind :%s was not started by this lane: %r" % (backend_port, backend_line[:160]))
    if "vite" not in frontend_line or "--port %s" % frontend_port not in frontend_line:
        failures.append("P4 the process behind :%s was not started by this lane: %r" % (frontend_port, frontend_line[:160]))

    db_path = Path(database_url.replace("sqlite:///", ""))
    tables = None
    if db_path.exists():
        import sqlite3

        connection = sqlite3.connect("file:%s?mode=ro" % db_path.as_posix(), uri=True)
        try:
            tables = int(connection.execute("select count(*) from sqlite_master where type='table'").fetchone()[0])
        finally:
            connection.close()

    refuse_unless_all_present((p1, p2, p3, p4), "the four provenance checks")
    receipt = {
        "generated_by": "89f2e2d6",
        "order": "ORD-0520 glass walk",
        "run_id": run_id,
        "database_url": database_url,
        "database_bytes": db_path.stat().st_size if db_path.exists() else None,
        "database_tables": tables,
        "git_head": subprocess.run(
            ["git", "-C", str(REPO), "rev-parse", "HEAD"], capture_output=True, text=True
        ).stdout.strip(),
        "P1_backend_answers_this_run": p1,
        "P2_frontend_proxies_to_this_run": p2,
        "P3_frontend_serves_this_tree": p3,
        "P4_port_owners": p4,
        "failures": failures,
        "verdict": "PROVENANCE_OK" if not failures else "PROVENANCE_REFUSED",
    }
    OUT.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("verdict %s" % receipt["verdict"])
    print("receipt %s" % OUT)
    for line in failures:
        print("FAIL %s" % line)
    print("P1 run=%s db=%s ai=%s" % (p1["e2e_run_id"], p1["e2e_database_id"], p1["ai"]))
    print("P2 proxied run=%s same=%s" % (p2["e2e_run_id"], p2["same_run_id_as_direct_read"]))
    print("P3 served %d bytes disk %d bytes marker=%s" % (p3["served_bytes"], p3["disk_bytes"], p3["marker_in_served_module"]))
    print("P4 backend pid=%s frontend pid=%s" % (p4["backend_port"]["pid"], p4["frontend_port"]["pid"]))
    print("database tables=%s bytes=%s" % (tables, receipt["database_bytes"]))
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
