"""ORD-0421 lane: prove the census stack answers from THIS lane's files, three ways, in one batch.

1. netstat says which pid holds the port;
2. that pid's own command line is this lane's launcher naming the same port;
3. the DB it reads is this lane's private copy: a marker row inserted only here is returned by the
   API, and an absent city returns nothing (the negative control).
The user's preview DB is only ever stat'ed, and its (mtime, size) is read twice around a request to
turn "I did not write it" into something checkable.
"""
import io
import json
import os
import re
import sqlite3
import subprocess
import time
import urllib.parse

PORT = 8726
MARK = "CNX-R0426-MARKER"
DB = "D:/moodle/_qoder_r_ord0426/run/_r_ord0426_8726.db"
PREVIEW = "D:/moodle/_qoder_preview_20260920/_preview.db"
OUT = "D:/moodle/_qoder_r_ord0426/wt/review/ord0426/PORT_OWNERSHIP_r1.json"


def listeners(port):
    out = subprocess.run(["netstat", "-ano", "-p", "TCP"], capture_output=True, text=True,
                         encoding="utf-8", errors="replace").stdout
    return sorted({l.split()[-1] for l in out.splitlines()
                   if f"127.0.0.1:{port}" in l and "LISTENING" in l})


def proc(pid):
    ps = subprocess.run(["powershell", "-NoProfile", "-Command",
                         'Get-CimInstance Win32_Process -Filter "ProcessId=%s" | '
                         "Select-Object ProcessId,CommandLine | ConvertTo-Json -Compress" % pid],
                        capture_output=True, text=True, encoding="utf-8", errors="replace").stdout
    try:
        return json.loads(ps)
    except Exception:
        return {}


def api(city):
    u = f"http://127.0.0.1:{PORT}/api/v1/places?city_code=" + urllib.parse.quote(city)
    body = subprocess.run(["curl", "-s", u], capture_output=True, text=True,
                          encoding="utf-8", errors="replace").stdout
    status = subprocess.run(["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}", u],
                            capture_output=True, text=True).stdout
    try:
        parsed = json.loads(body)
        n = len(parsed) if isinstance(parsed, list) else len(parsed.get("items", []))
    except Exception:
        n = -1
    return {"status": status, "rows": n}


con = sqlite3.connect(DB, timeout=10)
con.execute("delete from places where city_code=?", (MARK,))
con.execute("insert into places (id,provider_key,external_id,city_code,name,category,latitude,longitude,updated_at)"
            " values (?,?,?,?,?,?,?,?,datetime())",
            ("ord0421-marker-1", "qoder-lane", "ord0421-1", MARK, "census marker", "CENSUS", 39.1, 117.2))
con.commit()
rows_here = con.execute("select count(*) from places where city_code=?", (MARK,)).fetchone()[0]
con.close()

pid = (listeners(PORT) or [None])[0]
info = proc(pid) if pid else {}
p_before = (os.path.getmtime(PREVIEW), os.path.getsize(PREVIEW))
subprocess.run(["curl", "-s", "-o", "/dev/null",
                "http://127.0.0.1:%d/api/v1/journeys/22222222-2222-4222-8222-222222222222/experience" % PORT],
               capture_output=True, text=True, timeout=60)
p_after = (os.path.getmtime(PREVIEW), os.path.getsize(PREVIEW))
log = open("D:/moodle/_qoder_r_ord0426/run/backend_8726.log", encoding="utf-8", errors="replace").read()

receipt = {
    "lane_backend_port": PORT,
    "listening_pid": pid,
    "listening_pid_command_line_tail": (info.get("CommandLine") or "")[-58:],
    "server_pid_in_backend_log": re.findall(r"Started server process \[(\d+)\]", log),
    "lane_db_copy": DB,
    "sqlite_rows_for_marker_city_in_lane_copy": rows_here,
    "api_marker_city": api(MARK),
    "api_absent_city_negative_control": api("CNX-R0426-NOSUCH"),
    "users_preview_db_stat_before": p_before,
    "users_preview_db_stat_after": p_after,
    "users_preview_db_stat_unchanged": p_before == p_after,
    "shared_ports_not_touched": {p: listeners(p) for p in (8000, 4781, 4782, 8693, 4805)},
    "lane_backend_port_note": "lane-owned ports for this order only",
    "lane_front_ports": [4826, 4827],
    "lane_front_pids": {str(p): (listeners(p) or [None])[0] for p in (4826, 4827)},
}
os.makedirs(os.path.dirname(OUT), exist_ok=True)
with io.open(OUT, "w", encoding="utf-8", newline="\n") as fh:
    fh.write(json.dumps(receipt, ensure_ascii=False, indent=1))
print(json.dumps(receipt, ensure_ascii=False, indent=1))
