"""Read-only census of the timestamp shapes the store actually holds for activities.

ORD-0496 slice 1 needed to know what "no usable clock" means against real rows rather than against
a guess, so this opens the commander's live database `mode=ro` and counts shapes.  It writes
nothing and is not a gate: its reading goes into the delivery block.
"""

from __future__ import annotations

import pathlib
import sqlite3

TARGETS = (
    pathlib.Path("D:/moodle/_qoder_cmdr_gate_20260921/backend/_live.db"),
    pathlib.Path("D:/moodle/_qoder_cmdr_gate_20260921/backend/_live_copy.db"),
)

SHAPES = {
    "total": "SELECT COUNT(*) FROM activities",
    "offset_plus": "SELECT COUNT(*) FROM activities WHERE start_at LIKE '%+%'",
    "offset_z": "SELECT COUNT(*) FROM activities WHERE start_at LIKE '%Z'",
    "date_only": "SELECT COUNT(*) FROM activities WHERE LENGTH(start_at) <= 10",
    "naive_with_clock": (
        "SELECT COUNT(*) FROM activities WHERE LENGTH(start_at) > 10 "
        "AND start_at NOT LIKE '%+%' AND start_at NOT LIKE '%Z'"
    ),
    "empty_start": "SELECT COUNT(*) FROM activities WHERE TRIM(start_at) = ''",
    "title_with_comma": "SELECT COUNT(*) FROM activities WHERE title LIKE '%,%'",
    "title_with_semicolon": "SELECT COUNT(*) FROM activities WHERE title LIKE '%;%'",
    "title_with_newline": "SELECT COUNT(*) FROM activities WHERE title LIKE '%' || char(10) || '%'",
    "place_name_with_comma": "SELECT COUNT(*) FROM places WHERE name LIKE '%,%'",
    "active_plan_pointer_null": "SELECT COUNT(*) FROM journeys WHERE active_plan_version_id IS NULL",
    "binned_journeys": "SELECT COUNT(*) FROM journeys WHERE deleted_at IS NOT NULL",
}

for target in TARGETS:
    if not target.is_file():
        print(f"MISSING {target}")
        continue
    connection = sqlite3.connect(f"file:{target.as_posix()}?mode=ro", uri=True)
    print(f"== {target.as_posix()}")
    for label, sql in SHAPES.items():
        try:
            print(f"   {label} = {connection.execute(sql).fetchone()[0]}")
        except sqlite3.Error as failure:  # a missing table is a fact, not a crash
            print(f"   {label} = QUERY_ERROR {failure}")
    try:
        sample = connection.execute(
            "SELECT start_at, end_at, updated_at FROM activities ORDER BY start_at LIMIT 3"
        ).fetchall()
    except sqlite3.Error as failure:
        sample = []
        print(f"   sample = QUERY_ERROR {failure}")
    for row in sample:
        print(f"   sample {row}")
    connection.close()
