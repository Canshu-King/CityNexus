#!/usr/bin/env python3
"""ORD-0407 -- print the receipt anchors the ledger block cites, so no line number is hand-typed.

The delivery block quotes measured numbers, and the write-gate (Q43) wants each of them to carry a
`path:line` on the same line.  Hand-counting line numbers inside a pretty-printed JSON receipt is how
stale anchors get published, so this script reads the receipt, finds the line a key is written on, and
writes the `path:line` strings the block pastes verbatim.

    python review/n3_0407_receipt_anchors_r1.py --dir review/n3_0407_evidence_r1 --run cmdr205716n3 \
        --out review/n3_0407_evidence_r1/LEDGER_ANCHORS_r1.md
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

# (receipt arm, top-level key path) -- dotted, list indices as numbers.
WANTED = [
    ("C1", "unlocatable_journey.journey_id"),
    ("C1", "unlocatable_journey.server_says.city_code"),
    ("C2", "per_locale.zh-CN.今天.text"),
    ("C2", "per_locale.en.今天.text"),
    ("C3", "denominators.contract_paths_seen_by_this_cell"),
    ("C3", "contract_paths_seen_by_this_cell"),
    ("C3", "location_door_http_status"),
    ("C3", "location_row_returned"),
    ("C3", "experience_inputs_unchanged"),
    ("C3", "cell_text_unchanged_after_sharing_location"),
    ("C4", "zh-CN.label"),
    ("C4", "zh-CN.centre"),
    ("C4", "zh-CN.box"),
    ("C4", "en.label"),
    ("C5", "controls"),
    ("C5", "live_controls_above_floor"),
    ("C6", "screens"),
    ("C7", "by_width"),
]

INSTRUMENTS = [
    "review/n3_0407_write_door_inventory_r1.py",
    "review/n3_0407_baseline_r1.py",
    "review/n3_0407_mutations_r1.py",
    "review/n3_0407_copy_pair_check_r1.py",
    "review/n3_0407_evidence_r1/write_doors_head.json",
    "review/n3_0407_evidence_r1/controls_before_79ca877c.json",
    "review/n3_0407_evidence_r1/mutations_r2.json",
    "review/n3_0407_evidence_r1/n3_0407_copy_pair_r1.json",
]


def find_line(lines: list[str], key: str, after: int = 0) -> int:
    """The 1-based line a JSON key is written on, searching from `after`."""
    pat = re.compile(rf'^\s*"{re.escape(key)}"\s*:')
    for i in range(after, len(lines)):
        if pat.match(lines[i]):
            return i + 1
    return 0


def resolve(arm: str, dotted: str, root: Path, run: str) -> str:
    parts = dotted.split(".")
    path = root / f"{run}__{arm}.json"
    if not path.is_file():
        return f"MISSING {path.name}"
    lines = path.read_text(encoding="utf-8").splitlines()
    cursor = 0
    for part in parts:
        line = find_line(lines, part, cursor)
        if not line:
            return f"NOT_FOUND {dotted} in {path.name}"
        cursor = line
    return f"{path.relative_to(root.parent.parent).as_posix()}:{line}"


def grep_line(root: Path, needle: str) -> int:
    for path in root.iterdir():
        if path.name == "write_doors_head.json":
            lines = path.read_text(encoding="utf-8").splitlines()
            for i, l in enumerate(lines):
                if needle in l:
                    return i + 1
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True)
    ap.add_argument("--run", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    root = Path(a.dir)

    out = [f"# ORD-0407 ledger anchors, generated (run `{a.run}`)\n"]
    out.append("## receipts\n")
    for arm, dotted in WANTED:
        out.append(f"- `{arm}` `{dotted}` -> {resolve(arm, dotted, root, a.run)}")

    doors = root / "write_doors_head.json"
    txt = doors.read_text(encoding="utf-8")
    den = json.loads(txt)["denominators"]
    out.append("\n## write-door inventory (review/n3_0407_evidence_r1/write_doors_head.json)\n")
    for k, v in den.items():
        line = next((i + 1 for i, l in enumerate(txt.splitlines()) if f'"{k}"' in l), 0)
        out.append(f"- `{k}={v}` -> write_doors_head.json:{line}")

    copy = root / "n3_0407_copy_pair_r1.json"
    ctext = copy.read_text(encoding="utf-8")
    out.append("\n## paired-copy check (review/n3_0407_evidence_r1/n3_0407_copy_pair_r1.json)\n")
    for k, v in json.loads(ctext)["denominators"].items():
        line = next((i + 1 for i, l in enumerate(ctext.splitlines()) if f'"{k}"' in l), 0)
        out.append(f"- `{k}={v}` -> n3_0407_copy_pair_r1.json:{line}")
    line = next((i + 1 for i, l in enumerate(ctext.splitlines()) if '"values_not_found"' in l), 0)
    out.append(f"- `values_not_found={json.loads(ctext)['values_not_found']}` -> n3_0407_copy_pair_r1.json:{line}")

    out.append("\n## instruments and product lines\n")
    for p in INSTRUMENTS:
        out.append(f"- {p}")
    Path(a.out).write_text("\n".join(out) + "\n", encoding="utf-8")
    print("\n".join(out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
