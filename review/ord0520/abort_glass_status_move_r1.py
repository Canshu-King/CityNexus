"""ORD-0520 glass walk, helper -- move `journeys.status` the way another door writes it.

The screen arms need a row in the state `POST /journeys/{id}/plans/{plan_version_id}/select`
produces after a trip was called off: `status = "PLANNED"` with `aborted_at` and `abort_reason`
still on it (`backend/app/main.py:7833` writes that value and never reads the journey's status
first).  This lane's stack cannot reach that door, because plan generation on its store answers
http_status=422 with `reason_code=CATALOG_EMPTY` (measured; see `ABORT_RESURRECT_PROBE.json`), so
the write is performed as the committed UPDATE that door performs -- one column, one value, from a
second connection.  Nothing in the product is replaced, stubbed or skipped.

Read-only by default: without --status it prints the row and writes nothing.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

# The console codepage on this box is GBK, and a CJK `abort_reason` printed through it reaches the
# caller as mojibake; the arm's assertions do not lean on that field, but the receipt records it, so
# the stream is pinned to UTF-8 rather than left to the terminal.
sys.stdout.reconfigure(encoding="utf-8")


def read_row(db: Path, journey_id: str) -> dict:
    connection = sqlite3.connect("file:" + db.as_posix() + "?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    try:
        row = connection.execute(
            "SELECT rowid, id, status, aborted_at, abort_reason, active_plan_version_id "
            "FROM journeys WHERE id = ?",
            (journey_id,),
        ).fetchone()
        return dict(row) if row else {}
    finally:
        connection.close()


def move_status(db: Path, journey_id: str, value: str) -> int:
    connection = sqlite3.connect(db)
    try:
        cursor = connection.execute(
            "UPDATE journeys SET status = ? WHERE id = ?", (value, journey_id)
        )
        connection.commit()
        return cursor.rowcount
    finally:
        connection.close()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", required=True)
    parser.add_argument("--journey", required=True)
    parser.add_argument("--status", default=None)
    args = parser.parse_args()

    db = Path(args.db)
    if not db.exists():
        print("ABORT: %s does not exist" % db)
        return 2

    before = read_row(db, args.journey)
    if not before:
        print("ABORT: no journeys row for %s in %s" % (args.journey, db))
        return 3

    written = 0
    if args.status:
        written = move_status(db, args.journey, args.status)
    after = read_row(db, args.journey)
    print(
        json.dumps(
            {
                "database": db.name,
                "database_bytes": db.stat().st_size,
                "rowid": after.get("rowid"),
                "before": before,
                "written_rows": written,
                "after": after,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
