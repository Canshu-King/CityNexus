"""Commander recovery: put the user's own journeys back into the LIVE preview DB after the
second `demo/reset` wipe (measured 19:5x: journeys 6 -> 1, all user-created rows gone).

Rules honoured here:
  * additive only - we never delete or overwrite anything that exists now;
  * we only copy journeys whose id is absent from the live DB, plus the rows that hang off them
    (traveler, preferences, constraints) - no bookings/commitments are resurrected blindly,
    because a commitment whose provider row is gone would be a lie;
  * the live DB is snapshotted (WAL-consistent) before we touch it, and integrity is re-checked after.
Usage: python restore_user_journeys.py <backup.db> [--dry-run]
"""

from __future__ import annotations

import io
import json
import sqlite3
import sys
import time
from pathlib import Path

LIVE = Path(r"D:\moodle\_qoder_cmdr_gate_20260921\backend\_live.db")
SNAP_DIR = Path(r"D:\moodle\_qoder_cmdr_ref_20260921\live_snapshots")
DRY = "--dry-run" in sys.argv
BACKUP = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("--") else None
if not BACKUP:
    raise SystemExit("usage: restore_user_journeys.py <backup.db> [--dry-run]")

stamp = time.strftime("%H%M")
pre = SNAP_DIR / f"live_pre_restore_{stamp}.db"
src = sqlite3.connect(LIVE, timeout=45)
out = sqlite3.connect(pre)
src.backup(out)
out.commit()
out.close()
src.close()
print("live snapshot taken:", pre.name)

live = sqlite3.connect(LIVE, timeout=45)
live.execute("PRAGMA busy_timeout=45000")
old = sqlite3.connect(BACKUP)
old.row_factory = sqlite3.Row
live.row_factory = sqlite3.Row


def cols(table):
    return [r[1] for r in live.execute(f"PRAGMA table_info({table})")]


have = {r[0] for r in live.execute("SELECT id FROM journeys")}
print("live journeys now:", sorted(x[:8] for x in have))
todo = [dict(r) for r in old.execute("SELECT * FROM journeys") if r["id"] not in have]
print("journeys in backup missing from live:", [(t["id"][:8], t.get("city_code"), t.get("status")) for t in todo])

restored = {"journeys": 0, "travelers": 0, "preferences": 0, "constraints": 0, "skipped": []}
for j in todo:
    tid = j.get("traveler_id")
    tr = old.execute("SELECT * FROM travelers WHERE id=?", (tid,)).fetchone() if tid else None
    if tr and not live.execute("SELECT 1 FROM travelers WHERE id=?", (tr["id"],)).fetchone():
        data = dict(tr)
        keep = [c for c in data if c in cols("travelers")]
        if not DRY:
            live.execute(
                f"INSERT INTO travelers ({', '.join(keep)}) VALUES ({', '.join(':' + k for k in keep)})",
                {k: data[k] for k in keep},
            )
        restored["travelers"] += 1
    elif tr is None and tid:
        restored["skipped"].append((j["id"][:8], "no traveler row in backup"))
        continue

    keep = [c for c in j if c in cols("journeys")]
    if not DRY:
        live.execute(
            f"INSERT INTO journeys ({', '.join(keep)}) VALUES ({', '.join(':' + k for k in keep)})",
            {k: j[k] for k in keep},
        )
    restored["journeys"] += 1

    for table, key in (("preferences", "traveler_id"), ("constraints", "journey_id")):
        if table not in {r[0] for r in live.execute("SELECT name FROM sqlite_master WHERE type='table'")}:
            continue
        want = j["id"] if key == "journey_id" else tid
        for row in old.execute(f"SELECT * FROM {table} WHERE {key}=?", (want,)):
            data = dict(row)
            if live.execute(f"SELECT 1 FROM {table} WHERE id=?", (data["id"],)).fetchone():
                continue
            cols_ok = [c for c in data if c in cols(table)]
            if not DRY:
                live.execute(
                    f"INSERT INTO {table} ({', '.join(cols_ok)}) VALUES ({', '.join(':' + k for k in cols_ok)})",
                    {k: data[k] for k in cols_ok},
                )
            restored[table] += 1

    # plan versions / activities are deliberately NOT restored: their mobility evidence snapshot
    # ids may no longer exist, and a plan that cannot show its evidence would be a fake success.
    n_plans = old.execute("SELECT count(*) FROM plan_versions WHERE journey_id=?", (j["id"],)).fetchone()[0]
    if n_plans:
        restored["skipped"].append((j["id"][:8], f"{n_plans} plan version(s) not restored by design"))

if DRY:
    live.rollback()
    print("DRY RUN - nothing written")
else:
    for attempt in range(3):
        try:
            live.commit()
            break
        except sqlite3.OperationalError as exc:
            print("commit refused:", exc)
            time.sleep(2)
    else:
        raise SystemExit("could not commit - live DB stayed locked")

print("restored:", json.dumps(restored, ensure_ascii=False))
print("live journeys after:", live.execute("SELECT id, city_code, status FROM journeys ORDER BY created_at").fetchall())
print("integrity:", live.execute("PRAGMA integrity_check").fetchone()[0])
live.close()
old.close()
