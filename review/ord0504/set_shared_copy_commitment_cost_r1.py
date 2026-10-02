"""ORD-0504 shared-recipe hand -- move one commitment's price inside THIS LANE'S COPY of the board.

The counterexample needs a real server number to change. The shared store is not this lane's to write,
so the mutation happens in `run/ord0504_shared_day25_copy.db` -- the copy this lane took from a
read-only connection -- and is restored to the value it held before the run.

    python set_shared_copy_commitment_cost_r1.py <db-path> <amount-minor>

Refuses anything but this lane's copy so a mistyped path cannot reach the shared board.
"""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

ALLOWED = {"ord0504_shared_day25_copy.db"}


def main() -> int:
    db, value = Path(sys.argv[1]), int(sys.argv[2])
    if db.name not in ALLOWED:
        raise SystemExit("REFUSE: %s is not one of this lane's copies (%s)" % (db, sorted(ALLOWED)))
    if not db.is_file():
        raise SystemExit("REFUSE: %s does not exist" % db)
    con = sqlite3.connect(str(db))
    try:
        rows = con.execute("SELECT id, monetary_value_minor, currency, monetary_value_status"
                           " FROM commitments WHERE monetary_value_minor IS NOT NULL").fetchall()
        if len(rows) != 1:
            raise SystemExit("REFUSE: expected exactly one priced commitment in the copy, saw %d" % len(rows))
        commitment_id, previous, currency, status = rows[0]
        con.execute("UPDATE commitments SET monetary_value_minor = ?, currency = ?,"
                    " monetary_value_status = 'KNOWN' WHERE id = ?", (value, currency, commitment_id))
        con.commit()
        read = con.execute("SELECT monetary_value_minor, monetary_value_status FROM commitments WHERE id = ?",
                           (commitment_id,)).fetchone()
        print("commitment", commitment_id[:8], "was", previous, "now", read[0], read[1],
              "currency", currency, "restored_value_on_next_call", previous)
        return 0
    finally:
        con.close()


if __name__ == "__main__":
    sys.exit(main())
