"""ORD-0498: make the poster's second day with the product's own write doors, then read it back.

Rules this script obeys, in code rather than in prose:
  * no SQL writes and no `demo/reset` -- every mutation is an HTTP call a traveller could make;
  * the day count is only ever READ from `journey.temporal_shape.day_count`, which is the server's
    projection; nothing here asserts what the number "should" be, so a refusal stays a refusal;
  * if a write door refuses, the named reason code and the response body are recorded and the run
    stops -- the refusal IS the delivery in that case.
"""
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timedelta

API = "http://127.0.0.1:%s/api/v1" % (sys.argv[2] if len(sys.argv) > 2 else "8760")
JOURNEY = "22222222-2222-4222-8222-222222222222"
OUT = sys.argv[3] if len(sys.argv) > 3 else "D:/moodle/_qoder_e766b154_ord0501_20260930/run/write_route_walk.json"
MARKER_CITY = "CNX-ORD0472"

opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
steps = []


def call(method, path, body=None):
    url = API + path
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    if data:
        req.add_header("Content-Type", "application/json")
    try:
        with opener.open(req, timeout=90) as r:
            raw = r.read()
            return r.status, raw
    except urllib.error.HTTPError as e:
        return e.code, e.read()
    except Exception as e:  # a transport failure is named, never recorded as a refusal
        return "TRANSPORT_" + type(e).__name__, str(e).encode("utf-8")


def note(step, method, path, status, raw, extra=None):
    text = raw.decode("utf-8", "replace")
    try:
        parsed = json.loads(text)
    except Exception:
        parsed = None
    rec = {"step": step, "method": method, "path": path, "http": status,
           "body_bytes": len(raw), "body_head": text[:400]}
    if parsed is not None:
        if isinstance(parsed, dict) and "detail" in parsed:
            rec["detail"] = parsed["detail"]
        for key in ("reason_code", "code", "day", "day_source"):
            if isinstance(parsed, dict) and key in parsed:
                rec[key] = parsed[key]
    if extra:
        rec.update(extra)
    steps.append(rec)
    print("%-34s http=%s bytes=%s" % (step, status, len(raw)))
    if parsed is not None and isinstance(parsed, dict):
        for key in ("reason_code", "detail", "day", "day_source"):
            if key in parsed:
                print("      %s = %s" % (key, json.dumps(parsed[key], ensure_ascii=False)[:200]))
    return parsed


def shape_of(payload):
    journey = payload.get("journey") or {}
    shape = journey.get("temporal_shape") or {}
    plan = payload.get("active_plan") or {}
    acts = plan.get("activities") or []
    days = sorted({(a.get("start_at") or "")[:10] for a in acts})
    return {
        "day_count": shape.get("day_count"),
        "night_count": shape.get("night_count"),
        "semantics": shape.get("semantics"),
        "activities": len(acts),
        "distinct_activity_days": days,
    }


def main():
    # ownership first: the listener must be reading MY file
    status, raw = call("GET", "/places?city_code=" + MARKER_CITY)
    rows = json.loads(raw.decode()) if status == 200 else None
    print("marker rows answered=%s" % (len(rows) if rows is not None else status))
    if not rows:
        print("ABORT: this backend is not reading my database")
        return 2

    status, raw = call("GET", "/journeys/%s/experience" % JOURNEY)
    before = shape_of(json.loads(raw.decode()))
    print("before %s" % json.dumps(before, ensure_ascii=False))

    status, raw = call("GET", "/journeys/%s" % JOURNEY)
    journey = json.loads(raw.decode())
    start = datetime.fromisoformat(journey["start_at"])
    end = datetime.fromisoformat(journey["end_at"])
    print("anchors start=%s end=%s" % (journey["start_at"], journey["end_at"]))

    # Door 1: widen the trip by one calendar day through the journey PATCH.
    new_end = end + timedelta(days=1)
    status, raw = call("PATCH", "/journeys/%s" % JOURNEY, {"end_at": new_end.isoformat()})
    note("patch_journey_end_at_plus_one", "PATCH", "/journeys/%s" % JOURNEY, status, raw,
         {"sent_end_at": new_end.isoformat()})
    if status >= 300:
        dump()
        print("REFUSED AT DOOR 1 - stopping, refusal recorded above")
        return 3
    status, raw = call("GET", "/journeys/%s/experience" % JOURNEY)
    after_patch = shape_of(json.loads(raw.decode()))
    print("after patch %s" % json.dumps(after_patch, ensure_ascii=False))

    # Door 2: put a place on the second day with the import write the trips screen uses.
    second_day = (start + timedelta(days=1)).date().isoformat()
    status, raw = call("GET", "/places?city_code=%s" % journey["city_code"])
    places = json.loads(raw.decode())
    used = set()
    status, raw = call("GET", "/journeys/%s/experience" % JOURNEY)
    for act in (json.loads(raw.decode()).get("active_plan") or {}).get("activities") or []:
        if act.get("place_id"):
            used.add(act["place_id"])
    candidate = next((p for p in places if p["id"] not in used), None)
    if candidate is None:
        print("ABORT: every place in this city is already on the plan")
        dump()
        return 4
    print("candidate place=%s %s" % (candidate["id"], candidate["name"]))

    status, raw = call("POST", "/journeys/%s/poi-import/add" % JOURNEY,
                       {"place_ids": [candidate["id"]], "day": second_day})
    added = note("poi_import_add_second_day", "POST", "/journeys/%s/poi-import/add" % JOURNEY,
                 status, raw, {"sent_day": second_day})
    if status >= 300:
        dump()
        print("REFUSED AT DOOR 2 - stopping, refusal recorded above")
        return 3

    status, raw = call("GET", "/journeys/%s/experience" % JOURNEY)
    after_add = shape_of(json.loads(raw.decode()))
    print("after add %s" % json.dumps(after_add, ensure_ascii=False))

    dump()
    same = after_add["distinct_activity_days"]
    print("DISTINCT_DAYS=%d DAY_COUNT=%s" % (len(same), after_add["day_count"]))
    return 0 if len(same) >= 2 else 5


def dump():
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump({"journey": JOURNEY, "steps": steps}, fh, ensure_ascii=False, indent=1)
    print("receipt %s" % OUT)


if __name__ == "__main__":
    sys.exit(main())
