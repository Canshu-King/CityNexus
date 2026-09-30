"""ORD-0489 · publish the read-only receipts the ledger block cites.

Two facts are written here and nowhere else: the five counts the order asked this lane to
reproduce, and the table inventory of the same store.  The connection is `mode=ro`, so producing
this file cannot alter the thing it measures; the byte size and mtime are recorded before and
after the reads for exactly that reason.
"""

import json
import os
import sqlite3
import sys
from datetime import datetime, timezone

SRC = "D:/moodle/_qoder_preview_20260920/_preview.db"
LANE_DB = "D:/moodle/_qoder_seed_ord0489/run/_seed_final.db"
OUT = "D:/moodle/_qoder_seed_ord0489/wt/review/ord0489/preview_store_readonly_receipt.json"

TABLES = ("journeys", "plan_versions", "activities", "places", "travelers", "city_services")
MISSING = ("journey_checkins", "journey_share_grants", "journey_members", "journey_role_capabilities")


def stat_pair(path):
    st = os.stat(path)
    return {
        "bytes": st.st_size,
        "mtime": int(st.st_mtime),
        "mtime_utc": datetime.fromtimestamp(st.st_mtime, timezone.utc).isoformat(),
    }


def read(path):
    con = sqlite3.connect("file:%s?mode=ro" % path.replace("\\", "/"), uri=True)
    out = {}
    for table in TABLES:
        out[table] = con.execute("select count(*) from %s" % table).fetchone()[0]
    out["by_city_code_places"] = {
        row[0]: row[1] for row in con.execute("select city_code, count(*) from places group by city_code")
    }
    out["by_city_code_journeys"] = {
        row[0]: row[1] for row in con.execute("select city_code, count(*) from journeys group by city_code")
    }
    names = {row[0] for row in con.execute("select name from sqlite_master where type='table'")}
    out["table_count"] = len(names)
    out["missing_tables"] = sorted(t for t in MISSING if t not in names)
    out["present_checked_tables"] = sorted(t for t in MISSING if t in names)
    con.close()
    return out


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    before = stat_pair(SRC)
    shared = read(SRC)
    after = stat_pair(SRC)
    lane_before = stat_pair(LANE_DB)
    lane = read(LANE_DB)
    lane_after = stat_pair(LANE_DB)
    receipt = {
        "order": "ORD-0489",
        "taken_at": datetime.now(timezone.utc).isoformat(),
        "how": "sqlite3 connect with URI mode=ro on both stores; no write statement exists in this file",
        "shared_preview": {
            "path": SRC,
            "stat_before_reads": before,
            "counts": shared,
            "stat_after_reads": after,
            "unchanged_across_reads": before == after,
        },
        "lane_store": {
            "path": LANE_DB,
            "stat_before_reads": lane_before,
            "counts": lane,
            "stat_after_reads": lane_after,
            "unchanged_across_reads": lane_before == lane_after,
        },
    }
    with open(OUT, "w", encoding="utf-8") as handle:
        json.dump(receipt, handle, ensure_ascii=False, indent=1)
    print(json.dumps(receipt, ensure_ascii=False, indent=1)[:2400])


if __name__ == "__main__":
    main()
