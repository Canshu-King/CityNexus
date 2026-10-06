"""Commander probe for DoD #4: can a never-seen county actually be hydrated from REAL providers?

Today Beijing plans because I seeded the *fixture* catalogue - that satisfies #15, not #4.
This runs the real path on a scratch copy of the preview database:
  CITYNEXUS_REAL_CITY_ENABLED=true + CITYNEXUS_REAL_CITY_MODE=live
  POST /api/v1/catalog-hydrations {"query": "云和县"}  -> poll the operation -> count what landed.

Nothing here touches `_live.db`; the DB is a copy. Providers are hit for real, so a failure with a
named reason is a legitimate result and is what the report must show.
"""

from __future__ import annotations

import json
import os
import shutil
import sqlite3
import sys
import time
from pathlib import Path

ROOT = Path(r"D:\moodle\_qoder_cmdr_ref_20260921")
WORK = ROOT / "live_snapshots" / "dod4_hydrate.db"
SRC = ROOT / "live_snapshots" / "live_pre_tip.db"
shutil.copyfile(SRC, WORK)
for suf in ("-wal", "-shm"):
    p = Path(str(WORK) + suf)
    if p.exists():
        p.unlink()

os.environ["CITYNEXUS_DATABASE_URL"] = f"sqlite:///{WORK.as_posix()}"
os.environ["CITYNEXUS_DEMO_MODE"] = "true"
os.environ["CITYNEXUS_REAL_CITY_ENABLED"] = "true"
os.environ["CITYNEXUS_REAL_CITY_MODE"] = "live"
os.environ["CITYNEXUS_REAL_CITY_TIMEOUT_SECONDS"] = "25"
for k in ("DEEPSEEK_API_KEY", "OPENAI_API_KEY", "CITYNEXUS_AI_API_KEY", "CITYNEXUS_AI_MODEL",
          "CITYNEXUS_LIVE_VALHALLA_URL"):
    os.environ.pop(k, None)
sys.path.insert(0, str(ROOT / "backend"))

from fastapi.testclient import TestClient  # noqa: E402
from app.main import app  # noqa: E402

client = TestClient(app)
QUERY = sys.argv[1] if len(sys.argv) > 1 else "云和县"

cap = client.get("/api/v1/destinations/capability", params={"query": QUERY})
print("capability before ->", cap.status_code, json.dumps(cap.json(), ensure_ascii=False)[:300])

t0 = time.time()
resp = client.post("/api/v1/catalog-hydrations", json={"query": QUERY})
body = resp.json()
print(f"POST catalog-hydrations -> {resp.status_code} ({time.time() - t0:.2f}s)",
      json.dumps(body, ensure_ascii=False)[:400])
op = body.get("operation_id") or body.get("id")
if not op:
    raise SystemExit("no operation id - the door did not accept the request")

state = None
for i in range(80):
    time.sleep(3.0)
    read = client.get(f"/api/v1/catalog-hydrations/{op}")
    rb = read.json()
    state = rb.get("state") or rb.get("status")
    phase = rb.get("phase")
    if i % 5 == 0 or state in ("SUCCEEDED", "FAILED", "PARTIAL", "COMPLETE"):
        print(f"[{(i + 1) * 3:>3}s] state={state} phase={phase} "
              f"provider={json.dumps(rb.get('provider_status'), ensure_ascii=False)} "
              f"outcome={json.dumps(rb.get('outcome'), ensure_ascii=False)[:220]}")
    if state in ("SUCCEEDED", "FAILED", "ABANDONED", "PARTIALLY_SUCCEEDED", "UNAVAILABLE", "READY"):
        break

con = sqlite3.connect(WORK)
print("places by city:", con.execute(
    "SELECT city_code, count(*) FROM places GROUP BY city_code").fetchall())
print("places by provider_key:", con.execute(
    "SELECT provider_key, count(*) FROM places GROUP BY provider_key").fetchall())
rows = con.execute(
    "SELECT id, city_code, name, provider_key, coordinate_system, source_coordinate_system"
    " FROM places WHERE provider_key != 'mock-city' LIMIT 8").fetchall()
for r in rows:
    print("   real row:", r)
cols = [r[1] for r in con.execute("PRAGMA table_info(stay_generation_operations)")]
print("op columns:", cols)
pick = [c for c in ("id", "fingerprint", "status", "phase", "outcome") if c in cols]
print("operations:", con.execute(
    f"SELECT {', '.join(pick)} FROM stay_generation_operations ORDER BY rowid DESC LIMIT 3").fetchall())
print("capability after ->", json.dumps(
    client.get("/api/v1/destinations/capability", params={"query": QUERY}).json(),
    ensure_ascii=False)[:600])
con.close()
