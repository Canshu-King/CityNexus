"""Commander re-measurement of ORD-0151's premise, on the exported HEAD tree (d26933c).

Two claims are on the table and both are checkable without a server:

  (1) MINE, told to the arbiter twice: "`capability` and `catalog-hydrations` each compute
      destination identity, two places give a hash".  If `catalog_hydration_operations` calls the
      same `app.anywhere_capability.resolve_destination`, the claim is false and I retract it.
  (2) LANE C's step-1 change: an unnamed destination now gets `pending:<raw text>` in
      `canonical_destination_id`.  The arbiter's R10 wording says canonical must be *null* for
      no-match and for runtime failure - and this column is NOT NULL and feeds the idempotency
      fingerprint, so "readable placeholder" and "canonical=null" cannot both be true as written.

A tripwire counts every outbound HTTP call during both endpoints, because the honest answer to
"is a resolver asked?" must be a number, not an adjective.
"""

from __future__ import annotations

import json
import os
import shutil
import sqlite3
import sys
from pathlib import Path

ROOT = Path(r"D:\moodle\_qoder_cmdr_ref_20260921")
TREE = ROOT / "tree_head"
SRC = ROOT / "live_snapshots" / "live_pre_tip.db"
WORK = ROOT / "live_snapshots" / "head_r10_recheck.db"
if WORK.exists():
    WORK.unlink()
shutil.copyfile(SRC, WORK)
for suf in ("-wal", "-shm"):
    p = Path(str(WORK) + suf)
    if p.exists():
        p.unlink()

os.environ["CITYNEXUS_DATABASE_URL"] = f"sqlite:///{WORK.as_posix()}"
os.environ["CITYNEXUS_DEMO_MODE"] = "true"
os.environ["CITYNEXUS_REAL_CITY_ENABLED"] = "true"
os.environ["CITYNEXUS_REAL_CITY_MODE"] = "live"
for k in ("DEEPSEEK_API_KEY", "OPENAI_API_KEY", "CITYNEXUS_AI_API_KEY", "CITYNEXUS_AI_MODEL",
          "CITYNEXUS_LIVE_VALHALLA_URL"):
    os.environ.pop(k, None)

sys.path.insert(0, str(TREE / "backend"))

# --- outbound tripwire: patch both HTTP stacks before the app imports them -------------------
CALLS: list[str] = []
import httpx  # noqa: E402

_orig_send = httpx.Client.send
_orig_asend = httpx.AsyncClient.send


def _send(self, request, *a, **k):  # noqa: ANN001
    CALLS.append(f"sync {request.method} {request.url}")
    return _orig_send(self, request, *a, **k)


async def _asend(self, request, *a, **k):  # noqa: ANN001
    CALLS.append(f"async {request.method} {request.url}")
    return await _orig_asend(self, request, *a, **k)


httpx.Client.send = _send
httpx.AsyncClient.send = _asend

from fastapi.testclient import TestClient  # noqa: E402

from app import anywhere_capability as AC  # noqa: E402
from app import catalog_hydration_operations as CHO  # noqa: E402
from app.main import app  # noqa: E402

print("== identity-owner check ==")
print("CHO.resolve_destination is AC.resolve_destination ->",
      CHO.resolve_destination is AC.resolve_destination)
print("CHO imported from ->", getattr(CHO.resolve_destination, "__module__", "?"))
src = (TREE / "backend" / "app" / "catalog_hydration_operations.py").read_text(encoding="utf-8")
lines = src.splitlines()
print("call sites in catalog_hydration_operations.py:",
      [(i + 1, l.strip()) for i, l in enumerate(lines) if "resolve_destination(" in l])
acsrc = (TREE / "backend" / "app" / "anywhere_capability.py").read_text(encoding="utf-8").splitlines()
print("anywhere_capability.py resolve_destination definition:",
      [(i + 1, l.strip()) for i, l in enumerate(acsrc) if "def resolve_destination" in l])
print("provider/geocoder mentions inside anywhere_capability.py:",
      [(i + 1, l.strip()) for i, l in enumerate(acsrc)
       if any(w in l.lower() for w in ("photon", "nominatim", "overpass", "geocoder"))][:10] or "NONE")

client = TestClient(app)
QUERIES = ["云和县", "贡山独龙族怒族自治县", "zzxqvw-不存在县"]
for q in QUERIES:
    CALLS.clear()
    cap = client.get("/api/v1/destinations/capability", params={"query": q})
    cb = cap.json()
    n_cap = len(CALLS)
    CALLS.clear()
    post = client.post("/api/v1/catalog-hydrations", json={"query": q})
    pb = post.json()
    n_hy = len(CALLS)
    print(f"\n== {q} ==")
    print(f"  capability {cap.status_code} canonical={cb.get('canonical_destination_id')!r} "
          f"resolution={cb.get('destination_resolution')} cap={cb.get('capability')} "
          f"reason={cb.get('reason_code')} action={cb.get('recommended_action')}")
    print(f"  hydration  {post.status_code} canonical={pb.get('canonical_destination_id')!r} "
          f"op={pb.get('operation_id') or pb.get('id')} reused={pb.get('reused')}")
    print(f"  outbound HTTP during capability = {n_cap}; during hydration admission = {n_hy}")

con = sqlite3.connect(WORK)
print("\n== persisted rows (catalog_hydration_operations) ==")
for row in con.execute(
        "SELECT canonical_destination_id, fingerprint, status, outcome "
        "FROM catalog_hydration_operations ORDER BY queued_at").fetchall():
    print("  ", row)
print("columns:", [r[1] for r in con.execute("PRAGMA table_info(catalog_hydration_operations)")])
print("places by city:", con.execute(
    "SELECT city_code, count(*) FROM places GROUP BY city_code").fetchall())
con.close()

print("\n== the third class the arbiter separated (runtime failure) ==")
print("TRANSIENT_REASONS:", sorted(getattr(AC, "TRANSIENT_REASONS", [])))
names = [n for n in dir(AC) if n.startswith("REASON_")]
print("REASON_* vocabulary:", sorted(names))
