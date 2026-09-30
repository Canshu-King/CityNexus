"""ORD-0530 r3 -- repair my own bypass row, then prove ownership through the door.

The first insert left `id` NULL, and the read door then answered 500: at
`backend/app/main.py:3904` (`activity_ids = [r.activity_id for r in rows if r.activity_id]`) the
ORM hands back a None for a row with no primary key, so the comprehension dereferences None.
That is my bypass's doing, not the product's -- the POST door always mints an id -- so the row is
rewritten with a real id and the 500 is reported as a named incident of this lane's own making.
"""
import json
import sqlite3
import time
import urllib.error
import urllib.request

ROOT = "D:/moodle/_qoder_ai_ord0387_20260928"
DB = ROOT + "/ord0530_denominator_r3.db"
JOURNEY = "22222222-2222-4222-8222-222222222222"
MARKER = "ORD-0530 r3 分母 · 昨天的第三枚"
THIRD = "7951eb3f-a41b-49f6-9218-37bbd65f7d85"
_rcpt = json.load(open(ROOT + "/ord0530_reads_r3/stack_receipt_r3.json", encoding="utf-8"))
BACKEND = _rcpt["backend_port"]
FRONTEND = _rcpt["frontend_port"]

con = sqlite3.connect(DB)
before = list(con.execute("select id, target_key, stamped_at, note from journey_checkins"
                          " where journey_id=? order by stamped_at", (JOURNEY,)))
con.execute("delete from journey_checkins where journey_id=? and id is null", (JOURNEY,))
from datetime import datetime, timedelta
rows = list(con.execute("select stamped_at from journey_checkins where journey_id=?", (JOURNEY,)))
now = max(r[0] for r in rows)
yesterday = (datetime.fromisoformat(now) - timedelta(days=1)).isoformat()
import uuid
con.execute("insert into journey_checkins (id, journey_id, activity_id, place_id, target_kind,"
            " target_key, stamped_at, note, source) values (?,?,?,?,?,?,?,?,?)",
            (str(uuid.uuid4()), JOURNEY, THIRD, None, "ACTIVITY", THIRD, yesterday, MARKER,
             "FOREGROUND_WEB"))
con.commit()
after = list(con.execute("select id, target_key, stamped_at, note from journey_checkins"
                         " where journey_id=? order by stamped_at", (JOURNEY,)))

try:
    with urllib.request.urlopen("http://127.0.0.1:%d/api/v1/journeys/%s/checkins"
                               % (BACKEND, JOURNEY), timeout=20) as r:
        status, body = r.status, json.loads(r.read().decode("utf-8"))
except urllib.error.HTTPError as e:
    status, body = e.code, e.read().decode("utf-8", "replace")

out = {
    "at_local": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    "rows_before_my_repair": [{"id": r[0], "target_key": r[1], "stamped_at": r[2]} for r in before],
    "rows_after_my_repair": [{"id": r[0], "target_key": r[1], "stamped_at": r[2]} for r in after],
    "null_id_rows_removed": len([r for r in before if r[0] is None]),
    "third_day_written_directly": yesterday,
    "door_read_after_repair": {
        "http_status": status,
        "rows": len(body) if isinstance(body, list) else None,
        "instants": [r["stamped_at"] for r in body] if isinstance(body, list) else None,
        "notes": [r.get("note") for r in body] if isinstance(body, list) else None,
        "marker_row_present": isinstance(body, list)
        and any(MARKER in (r.get("note") or "") for r in body),
        "distinct_days": sorted({r["stamped_at"][:10] for r in body}) if isinstance(body, list) else None,
    },
    "stack": "frontend=:%d -> backend=:%d db=ord0530_denominator_r3.db" % (FRONTEND, BACKEND),
}
dst = ROOT + "/ord0530_reads_r3/denominator_repair_r3.json"
json.dump(out, open(dst, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(json.dumps(out, ensure_ascii=False, indent=1))
print("receipt", dst, __import__("os").path.getsize(dst), "B")
