"""One command that checks the classroom stack once Codex's ticket door is merged.

It refuses to run against the old backend on purpose: the probes below assume a pairing
ticket, and running them against `/demo/session` would prove the wrong door.  With the ticket
door present it runs the three read-only probes (ticketed entry, projector card, LAN path) and
prints a JSON receipt.  The rehearsal itself is left to the launcher's own bat because it
changes the scene twice.

Usage: python after_merge_check_r1.py
Exit 0 means "ran and every probe stayed green", or "correctly skipped: old backend".
"""
from __future__ import annotations

import json
import os
import subprocess
import sys

ROOT = r"D:/moodle/_cmdr_rescue_v3_1022"
PY = r"D:/moodle/CityNexus/.venv/Scripts/python.exe"
NODE = r"C:/Program Files/nodejs/node.exe"
SELFCHECK = ROOT + "/trial/play_launcher/classroom_demo/classroom_demo_selfcheck_r1.py"
OUT = ROOT + "/trial/results/20261022_v3_human_chrome/after-merge-check.txt"
TICKET_FILE = r"D:/moodle/_cmdr_v3_live_1022/.demo_pairing_ticket"
PROBES = [
    ("ticketed_entry", "_classroom_presenter_ticket_r30.mjs"),
    ("projector_card", "_classroom_desktop_card_r36.mjs"),
    ("lan_path", "_classroom_lan_path_r27.mjs"),
]


def selfcheck() -> dict:
    run = subprocess.run([PY, SELFCHECK], capture_output=True, text=True, timeout=120)
    lines = [line for line in run.stdout.splitlines() if line.strip().startswith("{")]
    return json.loads(lines[-1]) if lines else {}


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    state = selfcheck()
    door = state.get("ENTRY_DOOR")
    receipt: dict = {
        "ENTRY_DOOR": door,
        "DEMO_READY": state.get("DEMO_READY"),
        "SIM_CONSOLE": state.get("SIM_CONSOLE"),
    }
    if door != "PAIRING":
        receipt["RAN"] = False
        receipt["WHY"] = "ticket door not deployed; the probes below assume a pairing ticket"
        with open(OUT, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(receipt, ensure_ascii=False) + "\n")
        print(json.dumps(receipt, ensure_ascii=False))
        return 0

    tickets: list[str] = []
    try:
        raw = json.loads(open(TICKET_FILE, encoding="utf-8").read())
        import time
        if float(raw.get("expires_at", 0)) > time.time():
            values = raw.get("tickets") or ([raw["ticket"]] if raw.get("ticket") else [])
            tickets = [str(value) for value in values if value]
    except Exception:
        tickets = []
    receipt["ticket_file"] = bool(tickets)
    receipt["tickets"] = len(tickets)

    env = dict(os.environ)
    env["SIM_BASE"] = "http://127.0.0.1:14492"
    results = []
    for index, (name, probe) in enumerate(PROBES):
        if not tickets:
            results.append({"probe": name, "rc": -1, "note": "no live ticket file; rerun the launcher"})
            continue
        probe_env = dict(env)
        # One ticket per probe: a pairing ticket redeems exactly once.
        probe_env["PAIR_TICKET"] = tickets[index] if index < len(tickets) else ""
        run = subprocess.run([NODE, os.path.join(ROOT, "trial/human_walk", probe)],
                             capture_output=True, text=True, timeout=300, env=probe_env)
        results.append({"probe": name, "rc": run.returncode,
                        "stderr": run.stderr.strip()[-200:]})
    receipt["RAN"] = True
    receipt["probes"] = results
    receipt["all_green"] = all(item.get("rc") == 0 for item in results)
    with open(OUT, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(receipt, ensure_ascii=False) + "\n")
    print(json.dumps(receipt, ensure_ascii=False))
    return 0 if receipt["all_green"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
