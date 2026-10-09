"""Read-only row counts of the preview backend's DB (user data intactness after the reboot)."""
import sqlite3

DB = r"D:\moodle\_qoder_cmdr_gate_20260921\backend\_live.db"
con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
con.execute("PRAGMA query_only=1")
cur = con.cursor()
for t in ("journeys", "travelers", "plan_versions", "itinerary_items", "places", "catalog_hydration_operations"):
    try:
        cur.execute(f"SELECT COUNT(*) FROM {t}")
        print(f"{t}: {cur.fetchone()[0]}")
    except Exception as e:  # noqa: BLE001
        print(f"{t}: ERR {type(e).__name__} {e}")
cur.execute("SELECT id, city_code, status, updated_at FROM journeys ORDER BY updated_at DESC LIMIT 8")
for r in cur.fetchall():
    print("  journey", r[0][:8], r[1], r[2], r[3])
print("wal", __import__("os").path.getsize(DB + "-wal") if __import__("os").path.exists(DB + "-wal") else 0)
con.close()
