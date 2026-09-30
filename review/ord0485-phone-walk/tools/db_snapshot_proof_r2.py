"""ORD-0485 -- prove the shared preview DB is still untouched, and name the store this lane
actually wrote into.

db_snapshot_r1 printed its receipt to the console at 11:33 local and I did not save that
artifact, so this tool does not paraphrase it: it takes fresh readings of both files and lets
the numbers stand on their own.

The claim it can support: the shared file still carries the same size and the same mtime it had
when this lane copied it, so nothing this lane ran wrote there.
The claim it cannot support, and says so: a byte-for-byte diff against the 11:33 copy, because
the lane backend has since written marker / check-in / grant rows into its own file.
"""
import json
import os
import sqlite3
import sys
import time

SHARED = r"D:\moodle\_qoder_preview_20260920\_preview.db"
MINE = r"D:\moodle\_qoder_phone_ord0485_20260930\run\phone_ord0485.db"
OUT = r"D:\moodle\_qoder_phone_ord0485_20260930\evidence\db_snapshot_proof_r2.json"

TABLES = ["journeys", "travelers", "plan_versions", "journey_checkins", "journey_share_grants"]


def stamp(p):
    st = os.stat(p)
    return {"bytes": st.st_size, "mtime_ns": st.st_mtime_ns,
            "mtime_local": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(st.st_mtime))}


def counts(p):
    con = sqlite3.connect("file:%s?mode=ro" % p.replace("\\", "/"), uri=True)
    try:
        have = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        out = {}
        for t in TABLES:
            out[t] = con.execute("SELECT COUNT(*) FROM %s" % t).fetchone()[0] if t in have \
                else "TABLE_ABSENT"
        out["traveler_names"] = [r[0] for r in
                                 con.execute("SELECT display_name FROM travelers ORDER BY created_at")] \
            if "travelers" in have else None
        return out
    finally:
        con.close()


def main():
    result = {
        "tool": "db_snapshot_proof_r2",
        "took_local": time.strftime("%Y-%m-%d %H:%M:%S %z"),
        "shared_now": stamp(SHARED),
        "shared_at_copy_time_as_printed_by_db_snapshot_r1": {
            "bytes": 7213056, "mtime_local": "2026-09-29 09:20:27",
            "provenance": "the 11:33 run's own stdout line; the byte value and mtime are re-read "
                          "here, so this field is a claim being checked, not a quote trusted"},
        "shared_bytes_equal_to_copy_time": stamp(SHARED)["bytes"] == 7213056,
        "shared_mtime_equal_to_copy_time": stamp(SHARED)["mtime_local"] == "2026-09-29 09:20:27",
        "lane_copy": stamp(MINE),
        "shared_opened_read_only": True,
        "shared_counts_now": counts(SHARED),
        "lane_counts_now": counts(MINE),
        "byte_diff_to_the_1133_copy_supported": False,
        "why_no_byte_diff": "the lane backend wrote its marker traveller, one footprint and three "
                            "share grants into run/phone_ord0485.db after the copy, so a whole-file "
                            "comparison against the shared file is no longer a meaningful claim",
    }
    result["verdict_shared_untouched"] = bool(
        result["shared_bytes_equal_to_copy_time"] and result["shared_mtime_equal_to_copy_time"])
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result["verdict_shared_untouched"] else 3


if __name__ == "__main__":
    sys.exit(main())
