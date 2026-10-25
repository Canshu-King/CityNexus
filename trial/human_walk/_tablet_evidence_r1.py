"""Read-only evidence for the tablet check: were there non-loopback clients?

This cannot say "the owner operated a tablet"; it only counts what the classroom
backend saw in its current log cycle.  A human verdict still needs the owner's word,
but the external-client reading makes that verdict checkable instead of anecdotal.
"""
from __future__ import annotations

import json
import os
import re
import sqlite3
import time

LOG = r"D:/moodle/_cmdr_v3_port_1022/uvicorn_demo_classroom.log"
DB = r"D:/moodle/_cmdr_v3_live_1022/citynexus_v3_demo_1025.db"
SESSION = r"D:/moodle/_cmdr_v3_live_1022/.demo_presenter_session.json"
OUT_DIR = r"D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261022_v3_human_chrome"
LINE = re.compile(r'(?P<ip>\d+\.\d+\.\d+\.\d+):\d+ - "(?P<method>[A-Z]+) (?P<path>[^ ]+) HTTP[^"]*" (?P<status>\d{3})')


def log_reading() -> dict:
    if not os.path.exists(LOG):
        return {"exists": False}
    external: dict[tuple[str, str], int] = {}
    total = 0
    first = last = ""
    with open(LOG, encoding="utf-8", errors="replace") as handle:
        for line in handle:
            match = LINE.search(line)
            if not match:
                continue
            total += 1
            ip = match.group("ip")
            path = match.group("path")
            if ip in ("127.0.0.1", "::1"):
                continue
            key = (ip, path)
            external[key] = external.get(key, 0) + 1
            if not first:
                first = path
            last = path
    paths: dict[str, int] = {}
    for (_, path), count in external.items():
        paths[path] = paths.get(path, 0) + count
    return {"exists": True, "requests": total,
            "external_requests": sum(paths.values()), "external_paths": paths,
            "first_external_path": first, "last_external_path": last}


def run_reading() -> dict:
    if not os.path.exists(DB):
        return {"exists": False}
    con = sqlite3.connect("file:" + DB + "?mode=ro", uri=True)
    try:
        row = con.execute(
            "SELECT id,sequence,status,virtual_now,updated_at FROM simulation_runs "
            "WHERE journey_id='2e9cd67d-10ca-4ecd-920b-76c81a350c71'").fetchone()
        if not row:
            return {"exists": True, "run": None}
        return {"exists": True, "run": {"id": row[0], "sequence": row[1], "status": row[2],
                                        "virtual_now": row[3], "updated_at": row[4]}}
    finally:
        con.close()


def main() -> int:
    session_age = None
    if os.path.exists(SESSION):
        session_age = int(time.time() - os.path.getmtime(SESSION))
    reading = {
        "session_file_age_seconds": session_age,
        "log": log_reading(),
        "run": run_reading(),
    }
    external = reading["log"].get("external_requests", 0)
    reading["VERDICT"] = ("EXTERNAL_CLIENT_SEEN" if external else "NO_EXTERNAL_CLIENT")
    reading["NOTE"] = ("不等于 USER_VERIFIED：这只说明有非 loopback 客户端访问过；"
                       "是否为主人的平板、是否亲手点按，仍以主人确认为准。")
    stamp = time.strftime("%Y%m%d-%H%M%S")
    path = os.path.join(OUT_DIR, "tablet-evidence-%s.txt" % stamp)
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(reading, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(reading, ensure_ascii=True))
    print("WROTE", path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
