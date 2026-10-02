"""ORD-0525 r3 -- make the new reachability arm prove that it bites.

The R3 arm answers a "zero hits on the glass" reading, so the only mutation worth running is the one
that recreates that reading: take the entry out of the itinerary header and require R3 to go red.  If
the arm stayed green with the button gone, it would be measuring nothing, and the block would be
reporting a reachability that no instrument checked.

The file is restored from the bytes read at the start and re-hashed, and the arm is run once more
expecting green, so the tree this receipt describes is the tree that ships.

    D:/moodle/CityNexus/.venv/Scripts/python.exe review/ord0525/probe_counterarm_r3.py
"""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import subprocess
import sys
from datetime import datetime, timezone

ROOT = pathlib.Path(__file__).resolve().parents[2]
FRONTEND = ROOT / "frontend"
PRODUCT = FRONTEND / "src/features/trip/TripItinerary.tsx"
CONFIG = "playwright.ord0525-calendar.config.ts"
ARM = "R3 手机竖屏"
DATA = pathlib.Path("D:/moodle/_qoder_newlane_ord0525_data")
TAG = os.environ.get("CITYNEXUS_ORD0525_TAG", "r3")
BASE_TIP = os.environ.get("CITYNEXUS_ORD0525_BASE_TIP", "")
assert len(BASE_TIP) == 40 and all(c in "0123456789abcdef" for c in BASE_TIP), (
    "set CITYNEXUS_ORD0525_BASE_TIP to the 40-hex tip this was measured on"
)
RECEIPT = DATA / f"probe_counterarm_{TAG}.json"

START = b'          <button\n            type="button"\n            className="v8-quiet-button"\n            data-testid="calendar-export"'
END = b"          </button>\n"


def run_arm() -> dict:
    env = dict(os.environ)
    env.pop("DEEPSEEK_API_KEY", None)
    env["CITYNEXUS_ORD0525_TAG"] = TAG
    env["CITYNEXUS_ORD0525_BASE_TIP"] = BASE_TIP
    finished = subprocess.run(
        ["node", "node_modules/@playwright/test/cli.js", "test", "-c", CONFIG, "--grep", ARM],
        cwd=FRONTEND, env=env, capture_output=True, text=True,
        encoding="utf-8", errors="replace", timeout=900,
    )
    output = finished.stdout + finished.stderr
    ran = next((line for line in output.splitlines() if line.startswith("Running ")), "")
    collected = int(ran.split()[1]) if ran.split()[1:2] and ran.split()[1].isdigit() else 0
    return {
        "rc": finished.returncode,
        "tests_collected": collected,
        "summary": next((l.strip() for l in reversed(output.splitlines())
                         if " passed" in l or " failed" in l), ""),
        # an arm that collects nothing exits 0 -- that is not a pass, so the count travels with the rc
        "arm_ran": collected >= 1,
        "calendar_word_in_failure": "calendar-export" in output,
    }


def main() -> int:
    DATA.mkdir(parents=True, exist_ok=True)
    original = PRODUCT.read_bytes()
    digest = hashlib.sha256(original).hexdigest()
    assert original.count(START) == 1, original.count(START)
    start = original.index(START)
    end = original.index(END, start) + len(END)

    mutated = original[:start] + original[end:]
    assert mutated != original and mutated.count(b"calendar-export") < original.count(b"calendar-export")
    PRODUCT.write_bytes(mutated)
    try:
        under_mutation = run_arm()
    finally:
        PRODUCT.write_bytes(original)
    restored = hashlib.sha256(PRODUCT.read_bytes()).hexdigest() == digest
    control = run_arm()

    killed = under_mutation["rc"] != 0 and under_mutation["arm_ran"]
    receipt = {
        "run_at": datetime.now(timezone.utc).isoformat(),
        "generation": {"tag": TAG, "base_tip": BASE_TIP},
        "product_file": str(PRODUCT.relative_to(ROOT)),
        "mutation": "the ORD-0525 button block removed from the itinerary header",
        "lines_removed": len(original[start:end].decode("utf-8").splitlines()),
        "under_mutation": under_mutation,
        "restored_byte_identical": restored,
        "control_after_restore": control,
        "killed": killed,
        "note": "the arm's own claim is 屏上零命中 -> red; keeping this receipt is what distinguishes "
                "a measurement from a tautology",
    }
    RECEIPT.write_text(json.dumps(receipt, indent=2, ensure_ascii=False) + "\n",
                       encoding="utf-8", newline="\n")
    print(f"receipt={RECEIPT}")
    print(f"under_mutation rc={under_mutation['rc']} collected={under_mutation['tests_collected']} "
          f"summary={under_mutation['summary']!r} | restored={restored} | "
          f"control rc={control['rc']} collected={control['tests_collected']} summary={control['summary']!r}")
    return 0 if killed and restored and control["rc"] == 0 and control["tests_collected"] >= 1 else 1


if __name__ == "__main__":
    sys.exit(main())
