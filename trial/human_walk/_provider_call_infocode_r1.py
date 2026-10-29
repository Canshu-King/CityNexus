"""Read the provider receipts the running stack stored: which AMap infocode answered the refused hop.

Why: the card tells the traveller 「地图服务今天的查询次数已经用完，稍后再核实这一段」.  Daily quota
(10004/10021) and per-second throttling (10022) are different facts and need different words -- one is
"come back tomorrow", the other is "wait a moment".  The provider's own receipt is in this database.
"""
import json
import sqlite3
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
DB = r"D:/moodle/_cmdr_v3_live_1022/citynexus_v3_human21_1022.db"
con = sqlite3.connect("file:" + DB + "?mode=ro", uri=True)
con.row_factory = sqlite3.Row
cols = [r[1] for r in con.execute("pragma table_info(provider_calls)")]
print("provider_calls columns:", ",".join(cols))
rows = list(con.execute("select * from provider_calls order by rowid desc limit 12"))
print("newest rows:", len(rows))
for row in rows:
    blob = {}
    for c in cols:
        value = row[c]
        if isinstance(value, str) and value.strip().startswith(("{", "[")):
            try:
                blob[c] = json.loads(value)
            except Exception:
                pass
    codes = sorted({str(node.get("infocode")) for node in blob.values()
                    if isinstance(node, dict) and node.get("infocode")})
    shown = {c: str(row[c])[:40] for c in cols if c not in blob and row[c] is not None}
    print(json.dumps(shown, ensure_ascii=False)[:520])
    print("    infocode=" + (",".join(codes) or "?") + "  json_cols=" + ",".join(sorted(blob))
          + "  body=" + json.dumps(blob, ensure_ascii=False)[:420].replace("\n", " "))
