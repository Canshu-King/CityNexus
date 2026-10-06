"""Name the single outbound call, so "1" cannot be misread as "a provider was asked"."""
import os, shutil, sys
from pathlib import Path
ROOT = Path(r"D:\moodle\_qoder_cmdr_ref_20260921")
WORK = ROOT / "live_snapshots" / "head_r10_urls.db"
shutil.copyfile(ROOT / "live_snapshots" / "live_pre_tip.db", WORK)
for suf in ("-wal", "-shm"):
    p = Path(str(WORK) + suf)
    if p.exists(): p.unlink()
os.environ["CITYNEXUS_DATABASE_URL"] = f"sqlite:///{WORK.as_posix()}"
os.environ["CITYNEXUS_DEMO_MODE"] = "true"
os.environ["CITYNEXUS_REAL_CITY_ENABLED"] = "true"
os.environ["CITYNEXUS_REAL_CITY_MODE"] = "live"
for k in ("DEEPSEEK_API_KEY","OPENAI_API_KEY","CITYNEXUS_AI_API_KEY","CITYNEXUS_AI_MODEL","CITYNEXUS_LIVE_VALHALLA_URL"):
    os.environ.pop(k, None)
sys.path.insert(0, str(ROOT / "tree_head" / "backend"))
import httpx
CALLS = []
_o = httpx.Client.request
def _r(self, method, url, *a, **k):
    CALLS.append(f"{method} {url}")
    return _o(self, method, url, *a, **k)
httpx.Client.request = _r
from fastapi.testclient import TestClient
from app.main import app
c = TestClient(app)
CALLS.clear(); r = c.get("/api/v1/destinations/capability", params={"query": "云和县"})
print("capability ->", r.status_code, "outbound:", CALLS)
CALLS.clear(); r = c.post("/api/v1/catalog-hydrations", json={"query": "云和县"})
print("hydration  ->", r.status_code, "outbound:", CALLS)
