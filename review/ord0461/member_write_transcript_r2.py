"""ORD-0461 r2: one readable line per member write, taken at the app's own ASGI boundary.

Every row prints what the server answered in its **body** (`reason_code=` and `details`), not just the
status, so the four named refusals the order asked for can be read off one file, on both doors.
Nothing here asserts; it records.
"""
import io
import subprocess
import sys

WT = "D:/moodle/_qoder_rel_ord0461_wt"
OUT = WT + "/review/ord0461/member_write_transcript_r2.txt"

script = r"""
import sys
from datetime import datetime, timedelta, timezone
from uuid import uuid4
from fastapi.testclient import TestClient
sys.path.insert(0, "backend")
from app.main import app
from app.db.models import JourneyRoleCapability, Traveler
from app.db.session import SessionLocal

client = TestClient(app, raise_server_exceptions=False)
now = datetime.now(timezone.utc)
MEMBERS = "/api/v1/journeys/%s/members"


def traveler(tag):
    tid = str(uuid4())
    with SessionLocal() as s:
        s.add(Traveler(id=tid, display_name=tag, email=None, locale="zh-CN",
                       timezone="Asia/Shanghai", created_at=now.isoformat(),
                       updated_at=now.isoformat()))
        s.commit()
    return tid


def journey():
    owner = traveler("ord0461-owner")
    r = client.post("/api/v1/journeys", json={
        "traveler_id": owner, "title": "ORD-0461 r2 transcript", "city_code": "CN-XIAMEN",
        "timezone": "Asia/Shanghai", "start_at": (now + timedelta(days=3)).isoformat(),
        "end_at": (now + timedelta(days=5)).isoformat(),
        "budget": {"amount_minor": 90000, "currency": "CNY"}, "planning_mode": "balanced"})
    return r.json()["id"], owner


def add(jid, tid, role):
    r = client.post(MEMBERS % jid, json={"traveler_id": tid, "role": role,
                                         "invited_by": "lane-rel"})
    assert r.status_code == 201, r.text
    return r.json()


def line(label, response):
    body = response.json() if response.content else {}
    err = body.get("error") or {}
    print("%-46s http=%s reason_code=%s details=%s"
          % (label, response.status_code, err.get("reason_code"),
             str(err.get("details"))[:118]))


def change(jid, mid, role, actor):
    return client.post(MEMBERS % jid + "/" + mid + "/role",
                       json={"role": role, "actor_traveler_id": actor})


def remove(jid, mid, actor):
    return client.delete(MEMBERS % jid + "/" + mid, params={"actor_traveler_id": actor})


jid, owner = journey()
admin = add(jid, owner, "OWNER")
target = add(jid, traveler("ord0461-target"), "COLLABORATOR")
collaborator = add(jid, traveler("ord0461-collab"), "COLLABORATOR")
stranger = traveler("ord0461-stranger")

print("-- 0. the set as the server lists it before any write --")
rows = client.get(MEMBERS % jid).json()
print("rows=%d roles=%s" % (len(rows), sorted(r["role"] for r in rows)))

print("-- 1. the actor is not in this journey's member set --")
line("unknown actor changes a role", change(jid, target["id"], "ADMIN", stranger))
line("unknown actor removes a member", remove(jid, target["id"], stranger))
line("blank actor changes a role", change(jid, target["id"], "ADMIN", ""))
left = add(jid, traveler("ord0461-gone"), "COLLABORATOR")
client.post(MEMBERS % jid + "/" + left["id"] + "/withdraw", json={})
line("a withdrawn member changes a role", change(jid, target["id"], "ADMIN",
                                                 left["traveler_id"]))

print("-- 2. the role carries no MEMBER_MANAGE in the table --")
line("COLLABORATOR changes a role", change(jid, target["id"], "ADMIN",
                                           collaborator["traveler_id"]))
line("COLLABORATOR removes a member", remove(jid, target["id"], collaborator["traveler_id"]))
with SessionLocal() as s:
    s.add(JourneyRoleCapability(role="COLLABORATOR", capability="MEMBER_MANAGE",
                                scope_message_key="member.scope.probe",
                                created_at=now.isoformat()))
    s.commit()
print("table_now_grants_COLLABORATOR_MEMBER_MANAGE=yes")
line("same actor, same request, one row later", change(jid, target["id"], "ADMIN",
                                                       collaborator["traveler_id"]))
line("role write that changes nothing", change(jid, target["id"], "ADMIN",
                                               owner))
with SessionLocal() as s:
    held = s.get(JourneyRoleCapability, ("COLLABORATOR", "MEMBER_MANAGE"))
    if held is not None:
        s.delete(held)
    s.commit()
print("table_row_removed=yes")

print("-- 3. the target id is not a member of this journey --")
line("unknown member id, role door", change(jid, str(uuid4()), "ADMIN", owner))
line("unknown member id, remove door", remove(jid, str(uuid4()), owner))
other_jid, other_owner = journey()
elsewhere = add(other_jid, traveler("ord0461-elsewhere"), "COLLABORATOR")
line("another journey's member id, role door", change(jid, elsewhere["id"], "ADMIN", owner))
line("another journey's member id, remove door", remove(jid, elsewhere["id"], owner))
print("other_journey_still_lists_its_member=%s"
      % (elsewhere["id"] in [r["id"] for r in client.get(MEMBERS % other_jid).json()]))

print("-- 4. the journey is in the recycle bin --")
binned_jid, binned_owner = journey()
binned_target = add(binned_jid, traveler("ord0461-bin-target"), "COLLABORATOR")
client.delete("/api/v1/journeys/" + binned_jid)
line("role change on a binned journey", change(binned_jid, binned_target["id"], "ADMIN",
                                               binned_owner))
line("remove on a binned journey", remove(binned_jid, binned_target["id"], binned_owner))
line("binned journey, actor also unknown", change(binned_jid, binned_target["id"], "ADMIN",
                                                  stranger))
after = client.get(MEMBERS % binned_jid).json()
print("binned_journey_still_lists_rows=%d" % len(after))

print("-- 5. the two granted writes --")
granted_change = change(jid, target["id"], "ADMIN", owner)
print("role_change http=%s answer_role=%s listed_role=%s"
      % (granted_change.status_code, (granted_change.json() or {}).get("role"),
         [r["role"] for r in client.get(MEMBERS % jid).json()
          if r["id"] == target["id"]][0]))
removed = remove(jid, collaborator["id"], owner)
ids_after = [r["id"] for r in client.get(MEMBERS % jid).json()]
print("remove http=%s body_bytes=%d removed_still_listed=%s other_rows_listed=%d"
      % (removed.status_code, len(removed.content), collaborator["id"] in ids_after,
         len(ids_after)))
withdrawn = client.post(MEMBERS % jid + "/" + target["id"] + "/withdraw", json={})
print("withdraw http=%s row_still_listed=%s state=%s"
      % (withdrawn.status_code, target["id"] in [r["id"] for r in client.get(MEMBERS % jid).json()],
         (withdrawn.json() or {}).get("member_state")))
"""

run = subprocess.run([sys.executable, "-c", script], cwd=WT, capture_output=True, text=True,
                     encoding="utf-8", errors="replace")
body = run.stdout.strip() or run.stderr.strip()[-1800:]
io.open(OUT, "w", encoding="utf-8", newline="\n").write(body + "\n")
sys.stdout.write(body + "\n")
sys.stdout.write("rc=%d\n" % run.returncode)
