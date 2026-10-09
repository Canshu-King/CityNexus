# CMDR r31: calendar export (ORD-0496), demo board (ORD-0489) and member doors (ORD-0436/0461 shape) over real HTTP.
import json
import urllib.request as U

B = "http://127.0.0.1:4947"
R = {"arms": {}, "facts": {}}


def go(method, path, body=None, raw=False):
    data = json.dumps(body).encode() if body is not None else None
    req = U.Request(B + path, data=data, method=method,
                   headers={"Content-Type": "application/json"} if data else {})
    try:
        r = U.urlopen(req, timeout=25)
        t = r.read().decode("utf-8", "replace")
        code = r.status
    except U.HTTPError as e:
        t = e.read().decode("utf-8", "replace")
        code = e.code
    if raw:
        return code, t
    try:
        return code, json.loads(t)
    except Exception:
        return code, t


def note(label, code, payload, extra=None):
    o = {"http_status": code}
    if isinstance(payload, list):
        o["count"] = len(payload)
    elif isinstance(payload, dict) and "error" in payload:
        e = payload["error"]
        o["code"] = e.get("code")
        o["reason_code"] = e.get("reason_code")
        o["message_head"] = (e.get("message") or "")[:110]
        o["details_keys"] = list((e.get("details") or {}).keys())[:6] if e.get("details") else None
    elif isinstance(payload, str):
        o["chars"] = len(payload)
    elif isinstance(payload, dict):
        o["keys"] = list(payload.keys())[:8]
    R["arms"][label] = o if extra is None else {**o, **extra}
    return payload


# 1) the board
s, j = go("GET", "/api/v1/journeys")
note("journeys_list", s, j)
R["facts"]["journey_cities"] = [x.get("city_code") for x in j][:6] if isinstance(j, list) else None
R["facts"]["journey_statuses"] = [x.get("status") for x in j][:6] if isinstance(j, list) else None
journey_id = None
for x in (j if isinstance(j, list) else []):
    if x.get("status") in ("ACTIVE", "DRAFT") and x.get("id"):
        journey_id = x["id"]
        break
s, sc = go("GET", "/api/v1/demo/scene")
note("demo_scene", s, sc)
demo_id = sc.get("journey_id") if isinstance(sc, dict) else None
R["facts"]["demo_journey_id"] = demo_id

# 2) calendar export on the demo journey
for jid in [demo_id, journey_id]:
    if not jid:
        continue
    s, t = go("GET", "/api/v1/journeys/%s/calendar.ics" % jid, raw=True)
    ok = ("BEGIN:VCALENDAR" in t, "BEGIN:VEVENT" in t)
    note("calendar_%s" % ("demo" if jid == demo_id else "mine"), s, t,
         extra={"has_vcalendar": ok[0], "has_vevent": ok[1], "bytes": len(t.encode("utf-8"))})
    if jid == demo_id:
        R["facts"]["calendar_head"] = t[:200].replace("\r\n", " | ")
        R["facts"]["vevent_count"] = t.count("BEGIN:VEVENT")

# 3) refusals of the calendar door
s, t = go("GET", "/api/v1/journeys/22222222-2222-4222-8222-222222222223/calendar.ics", raw=True)
try:
    jerr = json.loads(t)
except Exception:
    jerr = t
note("calendar_unknown_journey", s, jerr)

if journey_id:
    s, d = go("DELETE", "/api/v1/journeys/%s" % journey_id)
    note("journey_delete_for_bin", s, d if isinstance(d, dict) else "")
    s, t = go("GET", "/api/v1/journeys/%s/calendar.ics" % journey_id, raw=True)
    try:
        jerr2 = json.loads(t)
    except Exception:
        jerr2 = t
    note("calendar_while_in_bin", s, jerr2)
    s, d = go("POST", "/api/v1/journeys/%s/undelete" % journey_id, body={})
    note("undelete_back", s, d if isinstance(d, dict) else "")

# 4) member doors as they exist today
s, mem = go("GET", "/api/v1/journeys/%s/members" % demo_id)
note("members_list_demo", s, mem)
s, tr = go("POST", "/api/v1/travelers", {"display_name": "CMDR r31 成员", "locale": "zh-CN", "timezone": "Asia/Shanghai"})
note("traveler_create", s, tr)
new_trav = tr.get("id") if isinstance(tr, dict) else None
if new_trav:
    s, addm = go("POST", "/api/v1/journeys/%s/members" % demo_id, {"traveler_id": new_trav, "role": "VIEWER"})
    note("member_add", s, addm)
    if isinstance(addm, dict) and addm.get("id"):
        s, wd = go("POST", "/api/v1/journeys/%s/members/%s/withdraw" % (demo_id, addm["id"]), body={})
        note("member_withdraw", s, wd)
        s, wd2 = go("POST", "/api/v1/journeys/%s/members/%s/withdraw" % (demo_id, addm["id"]), body={})
        note("member_withdraw_twice", s, wd2)
    s, bad = go("POST", "/api/v1/journeys/%s/members" % demo_id, {"traveler_id": new_trav, "role": "BOSS"})
    note("member_add_bad_role", s, bad)

print(json.dumps(R, ensure_ascii=False, indent=1))
