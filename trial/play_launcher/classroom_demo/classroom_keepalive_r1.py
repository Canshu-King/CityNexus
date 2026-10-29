"""Keep the classroom stack observable until tomorrow afternoon without touching a live show.

Every ten minutes: run the classroom self-check, append one JSON line to the log, and only
restart the stack when it is genuinely down (both page ports / health fail).  A show that is
merely paused, waiting for a proposal, or mid-run is healthy and is left alone.
"""
from __future__ import annotations

import io
import json
import os
import sqlite3
import subprocess
import sys
import time

ROOT = r"D:/moodle/_cmdr_rescue_v3_1022"
HERE = os.path.join(ROOT, "trial", "play_launcher", "classroom_demo")
SELF = os.path.join(HERE, "classroom_demo_selfcheck_r1.py")
PREP = os.path.join(HERE, "prepare_classroom_scene_r1.py")
LOG = r"D:/moodle/_cmdr_v3_port_1022/classroom_keepalive.log"
DB = r"D:/moodle/_cmdr_v3_live_1022/citynexus_v3_demo_1025.db"
BEATS = 48  # eight hours at ten-minute intervals


def city_identity() -> str | None:
    try:
        db = sqlite3.connect("file:" + DB + "?mode=ro", uri=True)
        try:
            row = db.execute("select provider_adcode from simulation_city_identities limit 1").fetchone()
        finally:
            db.close()
        return row[0] if row else None
    except sqlite3.Error:
        return "ERR"


def last_json(text: str) -> dict:
    for line in reversed((text or "").strip().splitlines()):
        line = line.strip()
        if line.startswith("{"):
            try:
                return json.loads(line)
            except ValueError:
                continue
    return {}


def main() -> None:
    for beat in range(BEATS):
        run = subprocess.run(
            [sys.executable, SELF], capture_output=True, text=True, encoding="utf-8", errors="replace"
        )
        body = last_json(run.stdout)
        backend = body.get("BACKEND_HEALTH")
        page = body.get("PAGE_LOOPBACK")
        healthy = body.get("STACK_HEALTHY") is True
        record = {
            "at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "beat": beat,
            "healthy": healthy,
            "backend": backend,
            "page": page,
            "session": body.get("SESSION_STATE"),
            "sim": body.get("SIM_CONSOLE"),
            "identity": city_identity() or "UNBOUND",
        }
        # Only a genuinely down stack is restarted; a paused show is not an outage.
        if not healthy and (backend != 200 or page != 200):
            restart = subprocess.run(
                [sys.executable, PREP], capture_output=True, text=True,
                encoding="utf-8", errors="replace", timeout=240,
            )
            record["restarted"] = restart.returncode == 0
        with io.open(LOG, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
        time.sleep(600)


if __name__ == "__main__":
    main()
