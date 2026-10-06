# CMDR r33: ORD-0503 member write doors (role change + self exit) over real HTTP on the newest tip.
import json
import urllib.request as U

B = "http://127.0.0.1:4953"
OUT = {"arms": {}, "facts": {}}


def go(method, path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = U.Request(B + path, data=data, method=method,
                   headers={"Content-Type": "application/json"} if data else {})
    try:
        r = U.urlopen(req, timeout=25)
        code, text = r.status, r.read().decode("utf-8", "replace")
    except U.HTTPError as e:
        code, text = e.code, e.read().decode("utf-8", "replace")
    try:
        return code, json.loads(text)
    except Exception:
        return code, text


def note(label, code, payload):
    o = {"http_status": code}
    if isinstance(payload, list):
        o["count"] = len(payload)
    elif isinstance(payload, dict) and "error" in payload:
        e = payload["error"]
        o["code"] = e.get("code")
        o["reason_code"] = e.get("reason_code")
        o["message_head"] = (e.get("message") or "")[:120]
    elif isinstance(payload, dict):
        o["keys"] = list(payload.keys())[:8]
    OUT["arms"][label] = o
    return payload


s, sc = go("GET", "/api/v1/demo/scene")
jid = sc.get("journey_id") if isinstance(sc, dict) else None
note("demo_scene", s, sc)

s, t1 = go("POST", "/api/v1/travelers", {"display_name": "CMDR r33 主", "locale": "zh-CN", "timezone": "Asia/Shanghai"})
owner = note("traveler_owner", s, t1) or t1
s, t2 = go("POST", "/api/v1/travelers", {"display_name": "CMDR r33 伴", "locale": "zh-CN", "timezone": "Asia/Shanghai"})
mate = t2.get("id") if isinstance(t2, dict) else None
oid = owner.get("id") if isinstance(owner, dict) else None
OUT["facts"]["owner"] = oid
OUT["facts"]["mate"] = mate

# the demo journey has no members on a fresh store: add the owner as OWNER first
s, m1 = go("POST", "/api/v1/journeys/%s/members" % jid, {"traveler_id": oid, "role": "OWNER", "actor_traveler_id": oid})
note("member_add_owner", s, m1)
s, m2 = go("POST", "/api/v1/journeys/%s/members" % jid, {"traveler_id": mate, "role": "EDITOR", "actor_traveler_id": oid})
note("member_add_mate", s, m2)
mid = m2.get("id") if isinstance(m2, dict) else None
OUT["facts"]["member_id"] = mid

s, lst = go("GET", "/api/v1/journeys/%s/members" % jid)
note("members_list", s, lst)

if mid:
    s, r1 = go("POST", "/api/v1/journeys/%s/members/%s/role" % (jid, mid), {"role": "VIEWER", "actor_traveler_id": oid})
    note("role_change_ok", s, r1)
    s, r2 = go("POST", "/api/v1/journeys/%s/members/%s/role" % (jid, mid), {"role": "VIEWER", "actor_traveler_id": oid})
    note("role_change_unchanged", s, r2)
    s, r3 = go("POST", "/api/v1/journeys/%s/members/%s/role" % (jid, mid), {"role": "OWNER", "actor_traveler_id": mate})
    note("role_change_actor_not_owner", s, r3)
    s, r4 = go("POST", "/api/v1/journeys/%s/members/00000000-0000-4000-8000-000000000000/role" % jid,
              {"role": "VIEWER", "actor_traveler_id": oid})
    note("role_change_unknown_member", s, r4)
    s, r5 = go("POST", "/api/v1/journeys/%s/members/%s/role" % (jid, mid), {"role": "BOSS", "actor_traveler_id": oid})
    note("role_change_bad_role", s, r5)
    s, r6 = go("POST", "/api/v1/journeys/%s/members/%s/withdraw" % (jid, mid), {"traveler_id": mate})
    note("self_exit", s, r6)
    s, r7 = go("POST", "/api/v1/journeys/%s/members/%s/withdraw" % (jid, mid), {"traveler_id": mate})
    note("self_exit_twice", s, r7)
    s, lst2 = go("GET", "/api/v1/journeys/%s/members" % jid)
    note("members_list_after_exit", s, lst2)

print(json.dumps(OUT, ensure_ascii=False, indent=1))
