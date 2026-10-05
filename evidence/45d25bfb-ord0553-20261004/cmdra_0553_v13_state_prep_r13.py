"""ORD-0553 r13 -- put two private store copies into the same execution state, through non-destructive doors only.

Why this exists: the reading compares two bundle generations, so the only variable allowed is the bytes
being served.  A store that differs between the two legs would make the comparison meaningless, so both
backends get the identical call sequence here and the resulting server-answered statuses are recorded on
both -- including any difference, which is then reported rather than smoothed over.

`demo/reset` is never called by this file (the order forbids it absolutely; it deletes 52 tables).
"""
import json
import sys
import urllib.error
import urllib.request

op = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def call(port, method, path, data=None):
    body = json.dumps(data).encode() if data is not None else None
    req = urllib.request.Request("http://127.0.0.1:%d/api/v1%s" % (port, path), method=method,
                                 headers={"Content-Type": "application/json"})
    try:
        with op.open(req, timeout=60) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        raw = e.read()
        try:
            return e.code, json.loads(raw)
        except Exception:
            return e.code, {"non_json": raw[:160].decode("utf-8", "replace")}


def prep(port):
    out = {"port": port, "calls": []}
    code, scene = call(port, "GET", "/demo/scene")
    jid = scene.get("journey_id")
    out["journey_id"] = jid
    out["scene_demo_mode"] = scene.get("demo_mode")
    if not jid:
        out["abort"] = "NO_JOURNEY_ON_THIS_STORE"
        return out
    code, plans = call(port, "GET", "/journeys/%s/plans" % jid)
    active = [p for p in plans if p.get("status") == "ACTIVE"]
    out["calls"].append({"door": "plans", "http_status": code, "plan_count": len(plans),
                         "active_versions": [p.get("version_no") for p in active]})
    if not active:
        code, gen = call(port, "POST", "/journeys/%s/plans/generate" % jid, {"candidate_count": 1})
        out["calls"].append({"door": "generate", "http_status": code})
        if code < 400 and gen:
            code, sel = call(port, "POST",
                             "/journeys/%s/plans/%s/select" % (jid, gen[0].get("id")), {})
            out["calls"].append({"door": "select", "http_status": code})
            active = [p for p in call(port, "GET", "/journeys/%s/plans" % jid)[1]
                      if p.get("status") == "ACTIVE"]
    code, st = call(port, "POST", "/journeys/%s/start" % jid, {})
    out["calls"].append({"door": "start", "http_status": code,
                         "code_answered": (st.get("error", {}) or {}).get("code")
                         if code >= 400 and isinstance(st, dict) else None})
    code, twin = call(port, "GET", "/journeys/%s/twin" % jid)
    ex = (twin.get("context", {}) or {}).get("execution", {}) if isinstance(twin, dict) else {}
    out["twin"] = {"http_status": code, "now_state": ex.get("now_state"),
                   "next_state": ex.get("next_state")}
    code, plans = call(port, "GET", "/journeys/%s/plans" % jid)
    act = [p for p in plans if p.get("status") == "ACTIVE"]
    out["activities"] = [[a.get("sequence_no"), a.get("status")]
                         for a in (act[0].get("activities", []) if act else [])]
    out["journey_status"] = call(port, "GET", "/journeys/%s" % jid)[1].get("status")
    return out


res = {"ports": [int(x) for x in sys.argv[1:]], "legs": [prep(int(p)) for p in sys.argv[1:]]}
same = (res["legs"][0].get("activities") == res["legs"][1].get("activities")
        and res["legs"][0].get("twin", {}).get("now_state") == res["legs"][1].get("twin", {}).get("now_state"))
res["stores_in_same_execution_state"] = bool(same)
path = "D:/moodle/_qoder_cmdra_ord0553_20261003/_evidence/r13_state_prep.json"
open(path, "w", encoding="utf-8").write(json.dumps(res, ensure_ascii=False, indent=1))
print(json.dumps(res, ensure_ascii=False))
