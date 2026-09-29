"""ORD-0461: one readable line per membership write, taken at the app's own ASGI boundary.

Every row prints what the server answered in its **body** (`reason_code=`), not just the status, so the
five named refusals the order asked for can be read off one file.  Nothing here asserts; it records.
"""
import io
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from uuid import uuid4

WT = "D:/moodle/_qoder_rel_ord0461_wt"
OUT = WT + "/review/ord0461/two_way_transcript_r2.txt"

script = r"""
import json, sys
from datetime import datetime, timedelta, timezone
from uuid import uuid4
from fastapi.testclient import TestClient
sys.path.insert(0, "backend")
from app.main import app, JOURNEY_MEMBER_CAP
from app.db.models import Journey, Traveler
from app.db.session import SessionLocal

client = TestClient(app, raise_server_exceptions=False)
now = datetime.now(timezone.utc)

def traveler(tag):
    tid = str(uuid4())
    with SessionLocal() as s:
        s.add(Traveler(id=tid, display_name=tag, email=None, locale="zh-CN",
                       timezone="Asia/Shanghai", created_at=now.isoformat(), updated_at=now.isoformat()))
        s.commit()
    return tid

def journey(owner):
    r = client.post("/api/v1/journeys", json={
        "traveler_id": owner, "title": "ORD-0461 transcript", "city_code": "CN-XIAMEN",
        "timezone": "Asia/Shanghai", "start_at": (now + timedelta(days=3)).isoformat(),
        "end_at": (now + timedelta(days=5)).isoformat(),
        "budget": {"amount_minor": 90000, "currency": "CNY"}})
    assert r.status_code == 201, r.text
    return r.json()["id"]

def line(tag, response):
    try:
        body = response.json()
    except ValueError:
        body = {}
    reason = (body.get("error") or {}).get("reason_code") if isinstance(body, dict) else None
    details = (body.get("error") or {}).get("details") if isinstance(body, dict) else None
    print("%-46s http=%s reason_code=%s details=%s" % (tag, response.status_code, reason, json.dumps(details, ensure_ascii=False) if details else "-"))

def add(jid, tid, role="COLLABORATOR"):
    return client.post("/api/v1/journeys/%s/members" % jid,
                       json={"traveler_id": tid, "role": role, "invited_by": "ord0461"})

print("cap_constant=%d" % JOURNEY_MEMBER_CAP)
owner = traveler("ord0461 owner")
jid = journey(owner)
collab = traveler("ord0461 collaborator")
admin = traveler("ord0461 admin")
outsider = traveler("ord0461 outsider")

c_row = add(jid, collab, "COLLABORATOR").json()
a_row = add(jid, admin, "ADMIN").json()
print("members_added=%d" % len(client.get("/api/v1/journeys/%s/members" % jid).json()))

print("-- 1. permission, read off journey_role_capabilities --")
line("COLLABORATOR changes a role", client.post(
    "/api/v1/journeys/%s/members/%s/role" % (jid, a_row["id"]),
    params={"actor_traveler_id": collab}, json={"role": "ADMIN"}))
line("ADMIN changes a role (table grants it)", client.post(
    "/api/v1/journeys/%s/members/%s/role" % (jid, c_row["id"]),
    params={"actor_traveler_id": admin}, json={"role": "ADMIN"}))
line("creator changes a role", client.post(
    "/api/v1/journeys/%s/members/%s/role" % (jid, c_row["id"]),
    params={"actor_traveler_id": owner}, json={"role": "COLLABORATOR"}))
line("no actor named at all", client.post(
    "/api/v1/journeys/%s/members/%s/withdraw" % (jid, c_row["id"])))

print("-- 2. operating on someone already gone --")
gone = add(jid, traveler("ord0461 gone")).json()["id"]
line("withdraw the fresh row", client.post(
    "/api/v1/journeys/%s/members/%s/withdraw" % (jid, gone), params={"actor_traveler_id": owner}))
line("withdraw it a second time", client.post(
    "/api/v1/journeys/%s/members/%s/withdraw" % (jid, gone), params={"actor_traveler_id": owner}))
line("change the role of a removed member", client.post(
    "/api/v1/journeys/%s/members/%s/role" % (jid, gone), params={"actor_traveler_id": owner},
    json={"role": "ADMIN"}))
line("an unknown member id", client.post(
    "/api/v1/journeys/%s/members/%s/role" % (jid, "no-such-row"),
    params={"actor_traveler_id": owner}, json={"role": "ADMIN"}))

print("-- 3. leaving: the creator cannot, a stranger has nothing to leave --")
line("creator tries to leave", client.post("/api/v1/journeys/%s/members/leave" % jid,
                                          params={"actor_traveler_id": owner}))
line("non-member tries to leave", client.post("/api/v1/journeys/%s/members/leave" % jid,
                                             params={"actor_traveler_id": outsider}))
line("a member leaves on their own", client.post("/api/v1/journeys/%s/members/leave" % jid,
                                                params={"actor_traveler_id": admin}))
line("promoting a member to OWNER", client.post(
    "/api/v1/journeys/%s/members/%s/role" % (jid, c_row["id"]), params={"actor_traveler_id": owner},
    json={"role": "OWNER"}))
line("a role write that changes nothing", client.post(
    "/api/v1/journeys/%s/members/%s/role" % (jid, c_row["id"]), params={"actor_traveler_id": owner},
    json={"role": "COLLABORATOR"}))

print("-- 4. the cap --")
standing = len([r for r in client.get("/api/v1/journeys/%s/members" % jid).json()
                if r["member_state"] != "MEMBER_WITHDRAWN"])
for i in range(JOURNEY_MEMBER_CAP - standing):
    add(jid, traveler("ord0461 fill %d" % i))
after = client.get("/api/v1/journeys/%s/members" % jid).json()
print("%-46s standing=%d cap=%d" % ("set filled to the cap",
                                    len([r for r in after if r["member_state"] != "MEMBER_WITHDRAWN"]),
                                    JOURNEY_MEMBER_CAP))
line("one member past the cap", add(jid, traveler("ord0461 over")))

print("-- 5. a journey sitting in the recycle bin --")
bin_id = journey(traveler("ord0461 binned"))
line("delete the journey", client.delete("/api/v1/journeys/%s" % bin_id))
line("add a member to it", add(bin_id, traveler("ord0461 binned member")))
line("change a role in it", client.post("/api/v1/journeys/%s/members/x/role" % bin_id,
                                       params={"actor_traveler_id": owner}, json={"role": "ADMIN"}))
line("withdraw in it", client.post("/api/v1/journeys/%s/members/x/withdraw" % bin_id,
                                   params={"actor_traveler_id": owner}))
line("leave it", client.post("/api/v1/journeys/%s/members/leave" % bin_id,
                             params={"actor_traveler_id": owner}))

print("-- 6. the member door refuses a deadline it would already read as spent --")
m_jid = journey(traveler("ord0461 member expiry"))
past_instant = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
line("add with an hour-old expiry", client.post("/api/v1/journeys/%s/members" % m_jid, json={
    "traveler_id": traveler("ord0461 past"), "role": "COLLABORATOR", "invited_by": "ord0461",
    "expires_at": past_instant}))
line("add with the instant equal to now", client.post("/api/v1/journeys/%s/members" % m_jid, json={
    "traveler_id": traveler("ord0461 boundary"), "role": "COLLABORATOR", "invited_by": "ord0461",
    "expires_at": datetime.now(timezone.utc).isoformat()}))
line("add with tomorrow's expiry", client.post("/api/v1/journeys/%s/members" % m_jid, json={
    "traveler_id": traveler("ord0461 future"), "role": "COLLABORATOR", "invited_by": "ord0461",
    "expires_at": (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()}))
print("%-46s rows=%d states=%s" % ("the set the server lists after those three attempts",
      len(client.get("/api/v1/journeys/%s/members" % m_jid).json()),
      [r["member_state"] for r in client.get("/api/v1/journeys/%s/members" % m_jid).json()]))

print("-- and the set as the server still lists it --")
rows = client.get("/api/v1/journeys/%s/members" % jid).json()
print("listed_rows=%d withdrawn_rows=%d roles=%s"
      % (len(rows), len([r for r in rows if r["removed_at"]]),
         sorted({r["role"] for r in rows})))
"""

run = subprocess.run([sys.executable, "-c", script], cwd=WT, capture_output=True, text=True,
                     encoding="utf-8", errors="replace")
body = run.stdout.strip() or run.stderr.strip()[-1500:]
io.open(OUT, "w", encoding="utf-8", newline="\n").write(body + "\n")
print(body)
print("rc=%d" % run.returncode)
