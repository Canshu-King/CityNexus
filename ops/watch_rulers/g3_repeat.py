#!/usr/bin/env python3
"""How often does g3 (five concurrent hydrations of one county -> one operation_id) go red when
every process is given its own fresh database?

ORD-0211 removed the shared ./citynexus.db, so a red here can no longer be blamed on a
neighbour's rows or on run order.  The classification is computed from the observed counts.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

BACKEND = Path(r"D:/moodle/_qoder_cmdr_ref_20260921/v_ord0211_pinned/backend")
PYTHON = "D:/moodle/CityNexus/.venv/Scripts/python.exe"
NODE = ("tests/test_qoder_anywhere_gates.py::"
        "test_g3_five_concurrent_hydrations_of_one_county_converge_on_one_operation")
RUNS = 8
OUT = Path(r"D:/moodle/_qoder_cmdr_ref_20260921/live_checks/ord0211/g3_repeat.json")

UUID = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")


def main() -> int:
    for key in ("CITYNEXUS_DATABASE_URL", "DEEPSEEK_API_KEY", "CITYNEXUS_AI_ENABLED",
                "CITYNEXUS_DEMO_MODE", "DATABASE_URL"):
        os.environ.pop(key, None)
    rows = []
    for i in range(RUNS):
        proc = subprocess.run(
            [PYTHON, "-m", "pytest", NODE, "-p", "no:randomly", "--tb=line", "-rA"],
            cwd=str(BACKEND), capture_output=True, text=True, timeout=900,
        )
        blob = (proc.stdout or "") + (proc.stderr or "")
        red_assert = next((ln.strip() for ln in blob.splitlines() if "AssertionError" in ln), None)
        # The gate names the ids it saw inside its own failure message; count only that line.
        observed = len(set(UUID.findall(red_assert))) if red_assert else None
        rows.append({
            "run": i + 1,
            "exit": proc.returncode,
            "verdict": "red" if proc.returncode != 0 else "green",
            "temp_db": next((ln.split("resolved=", 1)[1].split("|", 1)[0].strip()
                             for ln in blob.splitlines() if "ORD-0211 test database" in ln), None),
            "summary": next((ln.strip() for ln in reversed(blob.splitlines())
                             if "passed" in ln or "failed" in ln), None),
            "operation_ids_named_by_the_gate": observed,
        })
        print(rows[-1], flush=True)

    reds = sum(1 for r in rows if r["verdict"] == "red")
    greens = len(rows) - reds
    if reds == 0:
        classification = f"STABLE_GREEN({greens}/{len(rows)})"
    elif greens == 0:
        classification = f"STABLE_RED({reds}/{len(rows)})"
    else:
        classification = f"FLAKY_RACE(red {reds}/{len(rows)}, green {greens}/{len(rows)})"
    receipt = {
        "tree": str(BACKEND),
        "sha_under_test": "0a4cb23 (pinned export, fresh temp DB per process)",
        "processes": len(rows),
        "red": reds,
        "green": greens,
        "classification": classification,
        "distinct_temp_dbs_observed": len({r["temp_db"] for r in rows}),
        "runs": rows,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n",
                   encoding="utf-8", newline="\n")
    print("\n" + json.dumps({k: v for k, v in receipt.items() if k != "runs"},
                            ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
