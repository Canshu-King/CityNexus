"""Keep a running receipt of the classroom stack so the demo does not silently rot.

Every fifteen minutes this runs the existing self-check (read-only, no scene change) and appends
one line to `D:/moodle/_cmdr_v3_live_1022/classroom_watch.log`.  It never restarts the stack on
its own: a reset mid-demo would be worse than the failure it repairs, so an unhealthy beat only
writes ALERT and leaves the decision to the operator.
"""
from __future__ import annotations

import json
import subprocess
import sys
import time
from datetime import datetime

PY = r"D:/moodle/CityNexus/.venv/Scripts/python.exe"
SELFCHECK = r"D:/moodle/_cmdr_rescue_v3_1022/trial/play_launcher/classroom_demo/classroom_demo_selfcheck_r1.py"
LOG = r"D:/moodle/_cmdr_v3_live_1022/classroom_watch.log"
INTERVAL_S = 900


def beat() -> str:
    try:
        run = subprocess.run([PY, SELFCHECK], capture_output=True, text=True, timeout=90)
        lines = [line for line in run.stdout.splitlines() if line.strip().startswith("{")]
        if not lines:
            return "ALERT selfcheck produced no json rc=%s" % run.returncode
        state = json.loads(lines[-1])
    except Exception as error:  # noqa: BLE001
        return "ALERT selfcheck failed: %s" % str(error)[:120]
    healthy = (
        state.get("DEMO_READY") is True
        and state.get("BACKEND_HEALTH") == 200
        and state.get("PAGE_LAN") == 200
        and state.get("JOURNEY_STATUS") == "ACTIVE"
    )
    clock = str(state.get("CLOCK") or "")
    proposal = str(state.get("PROPOSAL_WAITING") or "")
    fields = " ".join([
        "DEMO_READY=%s" % state.get("DEMO_READY"),
        "JOURNEY=%s" % state.get("JOURNEY_STATUS"),
        "ENTRY_DOOR=%s" % state.get("ENTRY_DOOR"),
        "SIM_CONSOLE=%s" % state.get("SIM_CONSOLE"),
        "CLOCK=%s" % (clock[:19] or "-"),
        "PROPOSAL=%s" % (proposal[:8] or "-"),
        "AI=%s" % state.get("AI_STATE"),
    ])
    return ("OK " if healthy else "ALERT ") + fields


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    while True:
        stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        line = "%s %s" % (stamp, beat())
        with open(LOG, "a", encoding="utf-8", newline="\n") as handle:
            handle.write(line + "\n")
        print(line, flush=True)
        time.sleep(INTERVAL_S)


if __name__ == "__main__":
    raise SystemExit(main())
