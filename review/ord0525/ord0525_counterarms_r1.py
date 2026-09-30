"""ORD-0525 反件 -- the two things this gate must fail for, run for real.

An e2e suite that is green proves nothing about whether it would notice a defect.  Two mutations are
applied here, one to the product source and one to the data this lane owns, and each must turn the arm
that claims to guard it red:

K1 -- take the entry out.  The button block is deleted from `TripItinerary.tsx`.  If the entry arm
    stays green, that arm was never testing an entry.
K2 -- make the counts disagree.  One activity row in THIS LANE'S OWN COPY of the scheduled store gets
    a `start_at` with no clock (a bare date), which slice 1's rule legitimately skips: the file then
    holds five events while the screen still paints six stops.  If the comparison arm stays green, its
    "events = stops" claim is decoration.  Nothing is mocked and no row in anyone else's store moves;
    the original column value is written back and re-read.

After each mutation the original bytes are restored and re-hashed, and the same arm is run again
expecting green, so what ships is the tree that was measured, not a tree left mid-experiment.

    D:/moodle/CityNexus/.venv/Scripts/python.exe review/ord0525/ord0525_counterarms_r1.py
"""

from __future__ import annotations

import hashlib
import json
import os
import pathlib
import sqlite3
import subprocess
import sys
from datetime import datetime, timezone

ROOT = pathlib.Path(__file__).resolve().parents[2]
FRONTEND = ROOT / "frontend"
SCREEN = FRONTEND / "src/features/trip/TripItinerary.tsx"
DATA = pathlib.Path("D:/moodle/_qoder_newlane_ord0525_data")
DB = DATA / "_ord0525-lane.db"
RECEIPT = DATA / "ord0525_counterarms_receipt_r1.json"
ONE_DAY_TRIP = "22222222-2222-4222-8222-222222222222"  # 6 stops, one day
DAY_TRIP = "6cbdbc65-904a-40c7-a778-f981690f25d0"  # 8 stops across two days
CONFIG = "playwright.ord0525-calendar.config.ts"

BUTTON_BLOCK = """          <button
            type="button"
            className="v8-quiet-button"
            data-testid="calendar-export"
            disabled={calendarPending}
            onClick={() => void exportCalendar()}
          >
            {calendarPending ? t("calendar.busy") : t("calendar.export")}
          </button>
"""


def read(path: pathlib.Path) -> str:
    return path.read_bytes().decode("utf-8")


def write(path: pathlib.Path, text: str) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        handle.write(text)


def run_playwright(grep: str) -> dict:
    environment = dict(os.environ)
    environment.pop("DEEPSEEK_API_KEY", None)
    finished = subprocess.run(
        [
            "node", "node_modules/@playwright/test/cli.js", "test",
            "-c", CONFIG, "--grep", grep, "--reporter=list",
        ],
        cwd=FRONTEND,
        env=environment,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=900,
    )
    output = finished.stdout + finished.stderr
    titles = sorted(
        {
            line.split("›")[-1].strip()
            for line in output.splitlines()
            if line.strip().startswith(("x", "✘")) and "›" in line
        }
    )
    summary = [line.strip() for line in output.splitlines() if " passed" in line or " failed" in line]
    return {
        "rc": finished.returncode,
        "red_arm_titles": titles,
        "red_arm_count": len(titles),
        "summary": summary[-1] if summary else "",
    }


def main() -> int:
    original = read(SCREEN)
    original_sha = hashlib.sha256(original.encode("utf-8")).hexdigest()
    results: list[dict] = []

    # ---------------- K1: remove the entry
    assert original.count(BUTTON_BLOCK) == 1, original.count(BUTTON_BLOCK)
    write(SCREEN, original.replace(BUTTON_BLOCK, "", 1))
    try:
        mutated = run_playwright("A1")
    finally:
        write(SCREEN, original)
    restored_sha = hashlib.sha256(read(SCREEN).encode("utf-8")).hexdigest()
    # the control run only matters when the mutation actually reddened the arm
    after_restore = run_playwright("A1") if mutated["rc"] != 0 else None
    results.append(
        {
            "id": "K1_entry_removed",
            "claim": "没有入口时，入口臂必须红",
            "mutation_applied": True,
            "mutated_rc": mutated["rc"],
            "red_arm_count": mutated["red_arm_count"],
            "red_arm_titles": mutated["red_arm_titles"],
            "summary_after_mutation": mutated["summary"],
            "screen_restored_byte_identical": restored_sha == original_sha,
            "control_run_after_restore": after_restore,
            "killed": mutated["rc"] != 0 and mutated["red_arm_count"] > 0,
        }
    )

    # ---------------- K2: make the file's count disagree with the screen's stops
    with sqlite3.connect(DB) as connection:
        row = connection.execute(
            "SELECT a.id, a.start_at, a.sequence_no FROM activities a"
            " WHERE a.plan_version_id = ("
            "   SELECT active_plan_version_id FROM journeys WHERE id = ?)"
            " ORDER BY a.sequence_no DESC LIMIT 1",
            (ONE_DAY_TRIP,),
        ).fetchone()
        assert row is not None, "the one-day trip lost its plan rows in my own copy"
        activity_id, original_start, sequence_no = row
        connection.execute(
            "UPDATE activities SET start_at = ? WHERE id = ?", ("2026-10-10", activity_id)
        )
        connection.commit()
    mutated = None
    try:
        mutated = run_playwright("A3")
        a2 = run_playwright("A2")
    finally:
        with sqlite3.connect(DB) as connection:
            connection.execute(
                "UPDATE activities SET start_at = ? WHERE id = ?", (original_start, activity_id)
            )
            connection.commit()
            back = connection.execute(
                "SELECT start_at FROM activities WHERE id = ?", (activity_id,)
            ).fetchone()[0]
    results.append(
        {
            "id": "K2_counts_disagree",
            "claim": "事件数与屏上站点数不一致时，比对臂必须红",
            "store": str(DB),
            "row_mutated": {
                "activities.id": activity_id,
                "sequence_no": sequence_no,
                "start_at_before": original_start,
                "start_at_during": "2026-10-10",
            },
            "mutated_rc_A3": mutated["rc"],
            "red_arm_count_A3": mutated["red_arm_count"],
            "summary_after_mutation_A3": mutated["summary"],
            "mutated_rc_A2": a2["rc"],
            "red_arm_count_A2": a2["red_arm_count"],
            "summary_after_mutation_A2": a2["summary"],
            "row_restored_and_re_read": back == original_start,
            "killed": mutated["rc"] != 0 and mutated["red_arm_count"] > 0,
        }
    )

    # ---------------- K3: the same disagreement, inside the arm that compares DAY BY DAY.
    # K2 moved a row of the one-day trip, so the per-day arm (A2) was right to stay green: the fact it
    # judges did not change.  A2's own kill therefore needs a row of ITS denominator.
    with sqlite3.connect(DB) as connection:
        row = connection.execute(
            "SELECT a.id, a.start_at, a.sequence_no FROM activities a"
            " WHERE a.plan_version_id = ("
            "   SELECT active_plan_version_id FROM journeys WHERE id = ?)"
            " ORDER BY a.sequence_no LIMIT 1",
            (DAY_TRIP,),
        ).fetchone()
        assert row is not None, "the two-day trip lost its plan rows in my own copy"
        day_activity_id, day_original_start, day_sequence = row
        first_day = day_original_start[:10]
        connection.execute(
            "UPDATE activities SET start_at = ? WHERE id = ?", (first_day, day_activity_id)
        )
        connection.commit()
    day_mutated = None
    try:
        day_mutated = run_playwright("A2")
    finally:
        with sqlite3.connect(DB) as connection:
            connection.execute(
                "UPDATE activities SET start_at = ? WHERE id = ?", (day_original_start, day_activity_id)
            )
            connection.commit()
            day_back = connection.execute(
                "SELECT start_at FROM activities WHERE id = ?", (day_activity_id,)
            ).fetchone()[0]
    results.append(
        {
            "id": "K3_per_day_counts_disagree",
            "claim": "逐日那一臂：某一天少一枚事件时它必须红",
            "store": str(DB),
            "row_mutated": {
                "activities.id": day_activity_id,
                "sequence_no": day_sequence,
                "start_at_before": day_original_start,
                "start_at_during": first_day,
            },
            "mutated_rc_A2": day_mutated["rc"],
            "red_arm_count_A2": day_mutated["red_arm_count"],
            "red_arm_titles": day_mutated["red_arm_titles"],
            "summary_after_mutation_A2": day_mutated["summary"],
            "row_restored_and_re_read": day_back == day_original_start,
            "killed": day_mutated["rc"] != 0 and day_mutated["red_arm_count"] > 0,
        }
    )

    # ---------------- the whole gate, green, on the restored tree
    green = run_playwright("ORD-0525")
    receipt = {
        "run_at": datetime.now(timezone.utc).isoformat(),
        "interpreter": sys.executable,
        "command_shape": (
            f"node node_modules/@playwright/test/cli.js test -c {CONFIG} --grep <arm>"
        ),
        "screen_file_sha256_before_and_after": {
            "before": original_sha,
            "after": hashlib.sha256(read(SCREEN).encode("utf-8")).hexdigest(),
        },
        "counter_arms": results,
        "full_gate_on_restored_tree": green,
    }
    write(RECEIPT, json.dumps(receipt, indent=2, ensure_ascii=False))
    print(f"receipt={RECEIPT}")
    for item in results:
        red = next(
            (
                value
                for key, value in item.items()
                if key.startswith("red_arm_count") and value
            ),
            0,
        )
        restored = next(
            (
                value
                for key, value in item.items()
                if key.startswith(("screen_restored", "row_restored"))
            ),
            None,
        )
        print(f"{item['id']:28s} killed={item['killed']} red_arms={red} restored={restored}")
    print("full gate on the restored tree:", green["summary"], "rc=", green["rc"])
    failed = (
        not all(item["killed"] for item in results)
        or green["rc"] != 0
        or receipt["screen_file_sha256_before_and_after"]["before"]
        != receipt["screen_file_sha256_before_and_after"]["after"]
    )
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
