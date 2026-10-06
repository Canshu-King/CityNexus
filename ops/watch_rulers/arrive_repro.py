"""Commander repro: is `POST /activities/{id}/arrive` 500 a lock race or a deterministic double-arrive?

HJ-P2 got 3/3 HTTP 500 on 推进当前活动「到达」against the live preview, on the *same* activity id my own
12:47 walk already advanced successfully (`3a58c470`, journey 22222222). Two candidate causes with very
different owners: (a) SQLite write contention — an environment/multi-lane effect; (b) arriving twice at
an already-arrived activity throws instead of answering a named 409 — a product defect any user can hit.

This runs on a COPY of the live database, with no other writer, so if the second call is 500 the cause
cannot be contention.
"""

import os
import shutil
import sqlite3
import sys
from pathlib import Path

ROOT = Path(r"D:\moodle\_qoder_cmdr_ref_20260921")
WORK = ROOT / "live_snapshots" / "arrive_repro.db"
SRC = ROOT / "live_snapshots" / "live_pre_tip.db"
shutil.copyfile(SRC, WORK)
for suf in ("-wal", "-shm"):
    p = Path(str(WORK) + suf)
    if p.exists():
        p.unlink()

con = sqlite3.connect(WORK)
con.row_factory = sqlite3.Row
J = "22222222-2222-4222-8222-222222222222"
AID = "3a58c470-524c-5854-aa39-6c37a350eb80"
print("journey", tuple(con.execute(
    "SELECT status, current_activity_id, active_plan_version_id FROM journeys WHERE id=?", (J,)).fetchone()))
for row in con.execute("SELECT * FROM activities WHERE id LIKE '3a58c470%'"):
    print("activity row:", {k: row[k] for k in row.keys() if k in
                            ("id", "status", "activity_type", "start_at", "end_at", "plan_version_id")})
# sandbox only: put the journey into the state the phone was in, so `arrive` runs the real path
con.execute("UPDATE journeys SET status='ACTIVE', current_activity_id=? WHERE id=?", (AID, J))
con.commit()
print("forced journey ->", tuple(con.execute(
    "SELECT status, current_activity_id FROM journeys WHERE id=?", (J,)).fetchone()))
con.close()

os.environ["CITYNEXUS_DATABASE_URL"] = f"sqlite:///{WORK.as_posix()}"
os.environ["CITYNEXUS_DEMO_MODE"] = "true"
for k in ("DEEPSEEK_API_KEY", "OPENAI_API_KEY", "CITYNEXUS_AI_API_KEY", "CITYNEXUS_AI_MODEL",
          "CITYNEXUS_LIVE_VALHALLA_URL"):
    os.environ.pop(k, None)
sys.path.insert(0, str(ROOT / "backend"))

from fastapi.testclient import TestClient  # noqa: E402
from app.main import app  # noqa: E402

client = TestClient(app)
AID = "3a58c470-524c-5854-aa39-6c37a350eb80"

print("\n-- scene --", client.get("/api/v1/demo/scene").json().get("journey_status"))
for attempt in (1, 2, 3):
    r = client.post(f"/api/v1/journeys/{J}/activities/{AID}/arrive", json={})
    body = (r.text or "")[:220].replace("\n", " ")
    print(f"arrive #{attempt} -> {r.status_code} {body}")
e = client.get(f"/api/v1/journeys/{J}/experience")
print("experience ->", e.status_code, (e.text or "")[:160].replace("\n", " "))
