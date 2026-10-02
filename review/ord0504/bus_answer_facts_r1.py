"""Numbers the answer message cites, each printed by a command the hub can re-run itself.

    python D:/moodle/_qoder_r_ord0465_20260929/wt/review/ord0504/bus_answer_facts_r1.py

Every figure this lane quotes on the bus comes out of here, so the message and the re-run agree by
construction rather than by memory.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

LEDGER = Path("D:/moodle/CITYNEXUS_AGENT_CONTROL.md")
TREE = Path("D:/moodle/_qoder_r_ord0465_20260929/wt")
INBOX = Path("D:/moodle/_qoder_ledger_inbox")

lines = LEDGER.read_text(encoding="utf-8", errors="replace").splitlines()
mine = [i for i, line in enumerate(lines, 1) if "da46954a" in line]
print("LEDGER_LINES %d" % len(lines))
print("LINES_NAMING_DA46954A %d" % len(mine))
print("LAST_LINE_NAMING_DA46954A %d" % (mine[-1] if mine else 0))
orders = [i for i, line in enumerate(lines, 1) if line.startswith("## ORDERS")]
print("ORDERS_SECTION_AT %s" % (orders[-1] if orders else 0))
window = lines[orders[-1]: orders[-1] + 120] if orders else []
print("ORDERS_WINDOW_LINES_NAMING_ME %d" % len([l for l in window if "da46954a" in l or "0504" in l]))

block = "ORD-0504 共享配方一手"
print("BLOCK_HITS_IN_LEDGER %d" % len([l for l in lines if block in l]))
pending = sorted(p.name for p in INBOX.glob("da46954a_*") if p.is_file())
print("PENDING_IN_INBOX %d" % len(pending))

arms = json.loads((TREE / "review/ord0504/spend_screen_shared_board_r1.json").read_text(encoding="utf-8"))
results = arms["results"]
passed = len([r for r in results if r["pass"]])
print("ARMS %d PASSED %d FAILED %d" % (len(results), passed, len(results) - passed))

doors = json.loads((TREE / "review/ord0504/shared_board_doors_r1.json").read_text(encoding="utf-8"))
demo = arms["journeys"]["active_with_money"]
wallet_commitment = None
raw = json.loads((TREE / "review/ord0504/spend_screen_shared_board_r1.json").read_text(encoding="utf-8"))
for record in raw["results"]:
    if record["arm"] == "counterexample_on_shared_shape/moving_the_commitment_moves_the_total":
        print("MINOR_BEFORE %d MINOR_AFTER %d" % (record["detail"]["minor_before"], record["detail"]["minor_after"]))
        print("TOTALS_BEFORE %s" % " / ".join(record["detail"]["before"]))
        print("TOTALS_AFTER %s" % " / ".join(record["detail"]["after"]))
print("ACTIVE_JOURNEY %s" % demo)
print("LEGS_ROWS_ON_ACTIVE %d" % doors[demo]["legs_rows"])
