# CMDR r36: ORD-0503 member write doors with the shapes the schemas actually declare.
import json
import urllib.request as U

B = "http://127.0.0.1:4781"
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
        o["keys"] = list(payload.keys())[:9]
    OUT["arms"][label] = o
    return payload


s, sc = go("GET", "/api/v1/demo/scene")
jid = sc.get("journey_id") if isinstance(sc, dict) else None
s, t1 = go("POST", "/api/v1/travelers", {"display_name": "CMDR r36 主", "locale": "zh-CN", "timezone": "Asia/Shanghai"})
owner = t1.get("id") if isinstance(t1, dict) else None
s, t2 = go("POST", "/api/v1/travelers", {"display_name": "CMDR r36 伴", "locale": "zh-CN", "timezone": "Asia/Shanghai"})
mate = t2.get("id") if isinstance(t2, dict) else None
OUT["facts"] = {"journey": jid, "owner": owner, "mate": mate}

s, m1 = go("POST", "/api/v1/journeys/%s/members" % jid,
           {"traveler_id": owner, "role": "OWNER", "invited_by": "CMDR r36"})
note("member_add_owner", s, m1)
s, m2 = go("POST", "/api/v1/journeys/%s/members" % jid,
           {"traveler_id": mate, "role": "COLLABORATOR", "invited_by": "CMDR r36"})
mid = note("member_add_mate", s, m2)
mid = mid.get("id") if isinstance(mid, dict) else None
OUT["facts"]["member_id"] = mid
note("members_list", *go("GET", "/api/v1/journeys/%s/members" % jid))

if mid:
    note("role_change_ok", *go("POST", "/api/v1/journeys/%s/members/%s/role" % (jid, mid),
                              {"role": "ADMIN", "actor_traveler_id": owner}))
    note("role_change_unchanged", *go("POST", "/api/v1/journeys/%s/members/%s/role" % (jid, mid),
                                     {"role": "ADMIN", "actor_traveler_id": owner}))
    note("role_change_actor_not_owner", *go("POST", "/api/v1/journeys/%s/members/%s/role" % (jid, mid),
                                            {"role": "OWNER", "actor_traveler_id": mate}))
    note("role_change_unknown_member", *go("POST", "/api/v1/journeys/%s/members/00000000-0000-4000-8000-000000000000/role" % jid,
                                           {"role": "ADMIN", "actor_traveler_id": owner}))
    note("role_change_bad_role", *go("POST", "/api/v1/journeys/%s/members/%s/role" % (jid, mid),
                                     {"role": "BOGUS", "actor_traveler_id": owner}))
    note("self_exit", *go("POST", "/api/v1/journeys/%s/members/%s/withdraw" % (jid, mid), {"traveler_id": mate}))
    note("self_exit_twice", *go("POST", "/api/v1/journeys/%s/members/%s/withdraw" % (jid, mid), {"traveler_id": mate}))
    note("members_list_after_exit", *go("GET", "/api/v1/journeys/%s/members" % jid))

print(json.dumps(OUT, ensure_ascii=False, indent=1))
