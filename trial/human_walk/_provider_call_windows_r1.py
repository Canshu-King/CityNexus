"""Dump the AMap walking receipts around the two moments this slice turns on, into one readable file.

Line 1-6 are the burst inside one second that the card called "today's quota"; lines 8-13 are the freeze
after the fix, where a rate-limited hop is asked again about a second later and answers.
"""
import json
import sqlite3
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
DB = r"D:/moodle/_cmdr_v3_live_1022/citynexus_v3_human21_1022.db"
OUT = r"D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261022_v3_human_chrome/provider-call-receipts-1023.txt"
con = sqlite3.connect("file:" + DB + "?mode=ro", uri=True)
con.row_factory = sqlite3.Row
rows = list(con.execute(
    "select created_at, operation, status, response_json from provider_calls "
    "where operation like 'goal_amap_walking' order by created_at"))
lines = ["goal_amap_walking receipts, read from the running stack's own table, oldest first",
         "window A: the freeze that walk-88 reported as 4/5 (one second, five calls)",
         "window B: the freeze after the rate-limit split (one hop refused, then answered)"]
for row in rows:
    stamp = row["created_at"][11:23]
    reason = str(json.loads(row["response_json"] or "{}").get("reason_code"))
    route = "route=yes" if json.loads(row["response_json"] or "{}").get("route") else "route=no"
    window = "A" if row["created_at"].startswith("2026-10-23T10:14:2") else ("B" if row["created_at"].startswith("2026-10-23T10:46:0") else "-")
    lines.append("%s %s %s %s %s" % (window, stamp, row["status"], reason, route))
with open(OUT, "w", encoding="utf-8", newline="\n") as handle:
    handle.write("\n".join(lines) + "\n")
print("\n".join(lines[:3]))
print("rows:", len([l for l in lines if l.startswith(("A ", "B "))]))
for line in lines:
    if line.startswith(("A ", "B ")):
        print(line)
