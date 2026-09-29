"""ORD-0460: reproduce the commander's counter-example on the tip, before touching any code.

Three instants go into the create door -- one in the past, one exactly now, one in the future.  The
claim to test is narrow: the past one is accepted with a token, and that token is dead at birth while
the read door answers `SHARE_GRANT_EXPIRED`.  Everything is created through the product's own doors.
"""
import io
import json
import os
import subprocess
import sys
import tempfile

WT = "D:/moodle/_qoder_rel_ord0460_wt"
DB = os.path.join(tempfile.mkdtemp(prefix="cnx_0460_"), "probe.db").replace("\\", "/")
OUT = sys.argv[1] if len(sys.argv) > 1 else "D:/moodle/_qoder_rel_ord0460_wk/repro_before_r1.json"

env = dict(os.environ)
env["CITYNEXUS_DATABASE_URL"] = "sqlite:///" + DB
env["CITYNEXUS_DEMO_MODE"] = "true"
for gone in ("CITYNEXUS_AI_ENABLED", "DEEPSEEK_API_KEY", "HTTP_PROXY", "HTTPS_PROXY"):
    env.pop(gone, None)

script = r"""
import json
from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient
import sys
sys.path.insert(0, "backend")
from app.main import app

client = TestClient(app)
moment = datetime.now(timezone.utc)

traveler = client.post("/api/v1/travelers", json={
    "display_name": "ORD-0460 probe", "locale": "en-GB", "timezone": "Asia/Shanghai"}).json()
journey = client.post("/api/v1/journeys", json={
    "traveler_id": traveler["id"], "title": "ORD-0460 probe trip", "city_code": "CN-TIANJIN",
    "timezone": "Asia/Shanghai", "start_at": (moment + timedelta(days=3)).isoformat(),
    "end_at": (moment + timedelta(days=5)).isoformat(),
    "budget": {"amount_minor": 120000, "currency": "CNY"}})
jid = journey.json()["id"]
print("journey_create_http=%d" % journey.status_code)

cases = {
    "past": (moment - timedelta(days=1)).isoformat(),
    "boundary_now": moment.isoformat(),
    "future": (moment + timedelta(days=1)).isoformat(),
}
answers = {}
for name, raw in cases.items():
    answer = client.post("/api/v1/journeys/%s/share-grants" % jid, json={
        "visibility": "LINK_READ", "created_by": "ord0460-probe", "expires_at": raw})
    body = answer.json() if (answer.headers.get("content-type") or "").startswith("application/json") else {}
    token = body.get("token")
    read = None
    if token:
        got = client.get("/api/v1/shared/journeys/%s" % token)
        read = {"http": got.status_code,
                "reason_code": (got.json().get("error") or {}).get("reason_code") if got.status_code != 200 else None}
    answers[name] = {"sent": raw, "http": answer.status_code,
                     "reason_code": (body.get("error") or {}).get("reason_code"),
                     "token_len": len(token) if token else 0, "token_read": read}

listed = client.get("/api/v1/journeys/%s/share-grants" % jid).json()
print(json.dumps({"cases": answers,
                  "grant_rows_the_server_stored": len(listed),
                  "tokens_issued": sum(1 for r in listed if r.get("token"))},
                 ensure_ascii=False, indent=1))
"""

run = subprocess.run([sys.executable, "-c", script], cwd=WT, env=env, capture_output=True, text=True,
                     encoding="utf-8", errors="replace")
text = run.stdout.strip() or (run.stderr.strip()[-1200:])
io.open(OUT, "w", encoding="utf-8").write(text + "\n")
print(text)
print("rc=%d" % run.returncode)
