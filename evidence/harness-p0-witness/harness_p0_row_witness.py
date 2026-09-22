"""Independent witness of the shared user database - READ ONLY, twice, with rowid and timestamps.

Why a second instrument: the commander reports "P0 untouched (3 journeys / 19 plan versions /
3 travelers / 16 places)" every round, but that number has only ever come from his own tooling.
Row counts alone can also be preserved by delete+insert, so this witness records, per table:
    COUNT(*), MAX(rowid), MAX(<the timestamp column that actually exists>)
plus the mtime and size of `_live.db`, `-wal`, `-shm` before and after, and an explicit statement
about whether any write connection was opened.

Guards, all checked inside this process:
  * the connection is opened with URI `mode=ro`; `PRAGMA query_only` is read back and must be 1,
    and `journal_mode` is only read, never set;
  * two passes are taken a few seconds apart - different numbers between passes mean a writer is
    live, and that is reported rather than averaged away;
  * no file copy and no `backup()` here: a read-only query touches the least of anything. If a
    `-shm` refresh shows up, it is reported, not hidden (opening a WAL database read-only can
    still refresh the shared-memory file, and that is an effect of reading, not a write to the data).
"""

from __future__ import annotations

import json
import os
import sqlite3
import sys
import time
from pathlib import Path

DB = Path(r"D:\moodle\_qoder_cmdr_gate_20260921\backend\_live.db")
TABLES = ["journeys", "travelers", "plan_versions", "places"]
OUT = Path(__file__).resolve().parents[1] / "evidence" / f"live_db_witness_{time.strftime('%H%M')}.json"

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

if not DB.exists():
    print(f"ABORT: {DB} not found")
    raise SystemExit(2)

report = {"db": str(DB), "mode": "ro URI, no write connection", "passes": [],
          "files": {"before": {}, "after": {}}}


def file_state() -> dict:
    out = {}
    for suffix in ("", "-wal", "-shm"):
        p = Path(str(DB) + suffix)
        if p.exists():
            st = p.stat()
            out[p.name] = {"bytes": st.st_size,
                           "mtime": time.strftime("%Y-%m-%dT%H:%M:%S+08", time.localtime(st.st_mtime)),
                           "mtime_epoch": round(st.st_mtime, 3)}
        else:
            out[p.name] = {"absent": True}
    return out


def connect_ro() -> sqlite3.Connection:
    conn = sqlite3.connect(f"file:{DB.as_posix()}?mode=ro", uri=True, timeout=5)
    # `query_only` is a per-connection flag that read-only mode does NOT set (measured:
    # query_only=0 with mode=ro), so it is set explicitly here rather than assumed.
    conn.execute("PRAGMA query_only=1")
    ro = conn.execute("PRAGMA query_only").fetchone()[0]
    jm = conn.execute("PRAGMA journal_mode").fetchone()[0]
    print(f"  connection: opened via mode=ro URI, query_only read back={ro}, journal_mode={jm} (observed, never set)")
    if int(ro) != 1:
        raise SystemExit("ABORT: query_only did not read back as 1")
    return conn


def witness_pass(label: str) -> dict:
    conn = connect_ro()
    try:
        have = {r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'")}
        cols_all = {}
        for t in TABLES:
            if t in have:
                cols_all[t] = [r[1] for r in conn.execute(f'PRAGMA table_info("{t}")')]
        rows = {}
        for t in TABLES:
            if t not in have:
                rows[t] = {"absent": True}
                continue
            tcol = next((c for c in ("created_at", "updated_at") if c in cols_all.get(t, [])), None)
            if tcol is None:
                tcol = next((c for c in cols_all.get(t, []) if c.endswith("_at")), None)
            q = f'SELECT COUNT(*), MAX(rowid), MAX({tcol}) FROM "{t}"' if tcol else \
                f'SELECT COUNT(*), MAX(rowid), NULL FROM "{t}"'
            n, mx, tmax = conn.execute(q).fetchone()
            rows[t] = {"count": n, "max_rowid": mx, "timestamp_column": tcol,
                       "max_timestamp": str(tmax) if tmax is not None else None}
        tables_total = len(have)
        return {"label": label, "tables_in_schema": tables_total,
                "timestamp_columns": {t: [c for c in cols_all.get(t, [])
                                          if c.endswith("_at")] for t in TABLES},
                "tables": rows}
    finally:
        conn.close()


report["files"]["before"] = file_state()
print("before:", json.dumps({k: v.get("bytes") for k, v in report["files"]["before"].items()}))
for i in (1, 2):
    rep = witness_pass(f"pass{i}")
    report["passes"].append(rep)
    print(f"pass{i}: tables={rep['tables_in_schema']}")
    for t in TABLES:
        d = rep["tables"][t]
        print(f"   {t:<14} count={d.get('count'):<4} max_rowid={str(d.get('max_rowid')):<8} "
              f"{d.get('timestamp_column')}={d.get('max_timestamp')}")
    time.sleep(3)

report["files"]["after"] = file_state()
print("after :", json.dumps({k: v.get("bytes") for k, v in report["files"]["after"].items()}))
drift = {}
for name, before in report["files"]["before"].items():
    after = report["files"]["after"][name]
    if before != after:
        drift[name] = {"before": before, "after": after}
report["file_drift"] = drift
report["passes_agree"] = report["passes"][0]["tables"] == report["passes"][1]["tables"]
report["write_connection_opened"] = False
report["statement"] = ("only sqlite3.connect('file:...?mode=ro') was used; PRAGMA query_only read back as 1; "
                       "no INSERT/UPDATE/DELETE/backup/copy was performed.")

OUT.write_text(json.dumps(report, ensure_ascii=False, indent=1), "utf-8")
print(f"\npasses agree: {report['passes_agree']}   file drift: {list(drift) or 'none'}")
print(f"evidence: {OUT}")
