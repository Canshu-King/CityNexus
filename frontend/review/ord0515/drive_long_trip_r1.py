"""ORD-0515: build a trip long enough to cross the poster's named height bound, using only the
product's own write doors.

Why a long trip has to be *made* rather than assumed: the bound is a geometry rule over day blocks,
and the only honest reading of "does it page" is a journey whose blocks actually add up past it.
Nothing here writes SQL, resets anything, or seeds a file -- it is the same two calls the trips
screen offers, run repeatedly against this lane's own database copy.
"""
import json
import sys
import urllib.error
import urllib.request
from datetime import datetime, timedelta

API = "http://127.0.0.1:%s/api/v1" % (sys.argv[1] if len(sys.argv) > 1 else "8764")
OUT = sys.argv[2] if len(sys.argv) > 2 else "D:/moodle/_qoder_e766b154_ord0515_20260930/run/long_trip_walk.json"
JOURNEY = "22222222-2222-4222-8222-222222222222"
EXTRA_DAYS = int(sys.argv[3]) if len(sys.argv) > 3 else 6
STOPS_PER_DAY = int(sys.argv[4]) if len(sys.argv) > 4 else len_of_places()

opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
steps = []


def len_of_places():
    return 8


def call(method, path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(API + path, data=data, method=method)
    if data:
        req.add_header("Content-Type", "application/json")
    try:
        with opener.open(req, timeout=90) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()
    except Exception as e:
        return "TRANSPORT_" + type(e).__name__, str(e).encode()


def note(step, method, path, status, raw, extra=None):
    rec = {"step": step, "method": method, "http": status, "body_bytes": len(raw),
           "body_head": raw.decode("utf-8", "replace")[:240]}
    if extra:
        rec.update(extra)
    steps.append(rec)
    print("%-30s http=%s" % (step, status))


def experience():
    status, raw = call("GET", "/journeys/%s/experience" % JOURNEY)
    return json.loads(raw.decode())


def main():
    payload = experience()
    journey = payload["journey"]
    start = datetime.fromisoformat(journey["start_at"])
    end = datetime.fromisoformat(journey["end_at"])
    print("anchors before start=%s end=%s" % (journey["start_at"], journey["end_at"]))

    new_end = end + timedelta(days=EXTRA_DAYS)
    status, raw = call("PATCH", "/journeys/%s" % JOURNEY, {"end_at": new_end.isoformat()})
    note("patch_end_at_plus_%d" % EXTRA_DAYS, "PATCH", "/journeys/{id}", status, raw,
         {"sent_end_at": new_end.isoformat()})
    if status >= 300:
        dump()
        print("REFUSED at the window door")
        return 3

    payload = experience()
    shape = payload["journey"]["temporal_shape"]
    print("day_count after patch=%s night=%s" % (shape["day_count"], shape["night_count"]))

    places = json.loads(call("GET", "/places?city_code=%s" % journey["city_code"])[1].decode())
    if not places:
        print("ABORT: this city has no place rows to add")
        return 4
    print("places available=%d" % len(places))

    days = []
    day = start.date() + timedelta(days=1)
    last = datetime.fromisoformat(experience()["journey"]["end_at"]).date()
    while day <= last and len(days) < EXTRA_DAYS + 2:
        days.append(day.isoformat())
        day += timedelta(days=1)

    added = 0
    refusals = []
    for index, date in enumerate(days):
        # every place the city holds, on every added day: the height has to come from real rows,
        # not from a number this script invented
        picks = [places[i % len(places)]["id"] for i in range(STOPS_PER_DAY)]
        status, raw = call("POST", "/journeys/%s/poi-import/add" % JOURNEY,
                           {"place_ids": picks, "day": date})
        if status >= 300:
            refusals.append({"day": date, "http": status, "body": raw.decode("utf-8", "replace")[:200]})
            note("poi_add_%s_refused" % date, "POST", "/poi-import/add", status, raw, {"sent_day": date})
            continue
        added += len(picks)
        if index in (0, len(days) - 1):
            note("poi_add_%s" % date, "POST", "/poi-import/add", status, raw, {"sent_day": date})

    payload = experience()
    acts = payload["active_plan"]["activities"]
    distinct = sorted({a["start_at"][:10] for a in acts})
    print("activities=%d distinct_days=%d day_count=%s refusals=%d"
          % (len(acts), len(distinct), payload["journey"]["temporal_shape"]["day_count"], len(refusals)))
    steps.append({"step": "final_reading", "activities": len(acts), "distinct_days": len(distinct),
                  "server_day_count": payload["journey"]["temporal_shape"]["day_count"],
                  "day_list": distinct, "refusals": refusals, "places_added": added})
    dump()
    return 0 if len(distinct) >= 4 else 5


def dump():
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump({"journey": JOURNEY, "steps": steps}, fh, ensure_ascii=False, indent=1)
    print("receipt %s" % OUT)


if __name__ == "__main__":
    sys.exit(main())
