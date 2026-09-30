"""ORD-0528 -- give the shared poster a second day, through the product's own write doors only.

Why this file exists: the shape this order has to distinguish is a poster with day blocks in it, and
the seeded trip is one calendar day. The day is therefore *made*, not asserted -- and made the way
ORD-0498 settled: `PATCH /journeys/{id}` to widen the trip, then `POST /journeys/{id}/poi-import/add`
to put a place on the new day. No SQL, no `demo/reset`, no seed file.

The day count is only ever read out of `journey.temporal_shape.day_count`, which is the server's own
projection. A refusal is the delivery in that case: the named reason code and the response body are
recorded and the run stops.

ownership first: the listener must be answering with this lane's marker row, or every number below
belongs to somebody else's database.
"""
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timedelta

API_PORT = sys.argv[1] if len(sys.argv) > 1 else "8768"
MARKER_CITY = sys.argv[2] if len(sys.argv) > 2 else "CNX-ORD0528"
API = "http://127.0.0.1:%s/api/v1" % API_PORT
JOURNEY = "22222222-2222-4222-8222-222222222222"
OUT_DIR = "D:/moodle/_qoder_e766b154_ord0528_20261001/run"
OUT = "%s/write_route_walk_%s_%s.json" % (OUT_DIR, API_PORT, MARKER_CITY)

opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
steps = []


def call(method, path, body=None):
    data = json.dumps(body).encode("utf-8") if body is not None else None
    request = urllib.request.Request(API + path, data=data, method=method)
    if data:
        request.add_header("Content-Type", "application/json")
    try:
        with opener.open(request, timeout=90) as response:
            return response.status, response.read()
    except urllib.error.HTTPError as error:
        return error.code, error.read()
    except Exception as error:  # noqa: BLE001 - a transport failure is not a refusal
        return "TRANSPORT_" + type(error).__name__, str(error).encode("utf-8")


def note(step, method, path, status, raw, extra=None):
    text = raw.decode("utf-8", "replace")
    try:
        parsed = json.loads(text)
    except Exception:  # noqa: BLE001
        parsed = None
    record = {"step": step, "method": method, "path": path, "http_status": status,
              "body_bytes": len(raw), "body_head": text[:400]}
    if isinstance(parsed, dict):
        for key in ("reason_code", "detail", "day", "day_source"):
            if key in parsed:
                record[key] = parsed[key]
    if extra:
        record.update(extra)
    steps.append(record)
    print("%-34s http_status=%s bytes=%s" % (step, status, len(raw)))
    return parsed


def shape_of(payload):
    journey = payload.get("journey") or {}
    shape = journey.get("temporal_shape") or {}
    acts = (payload.get("active_plan") or {}).get("activities") or []
    return {
        "day_count": shape.get("day_count"),
        "activities": len(acts),
        "distinct_activity_days": sorted({(a.get("start_at") or "")[:10] for a in acts}),
    }


def experience_shape():
    status, raw = call("GET", "/journeys/%s/experience" % JOURNEY)
    return status, shape_of(json.loads(raw.decode("utf-8")))


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    status, raw = call("GET", "/places?city_code=%s" % MARKER_CITY)
    rows = json.loads(raw.decode("utf-8")) if status == 200 else []
    print("marker_probe http_status=%s rows=%s" % (status, len(rows)))
    if not rows:
        print("ABORT: this backend is not reading this lane's database")
        return 2

    print("before %s" % json.dumps(experience_shape()[1], ensure_ascii=False))
    journey = json.loads(call("GET", "/journeys/%s" % JOURNEY)[1].decode("utf-8"))
    start = datetime.fromisoformat(journey["start_at"])
    end = datetime.fromisoformat(journey["end_at"])

    new_end = end + timedelta(days=1)
    status, raw = call("PATCH", "/journeys/%s" % JOURNEY, {"end_at": new_end.isoformat()})
    note("patch_journey_end_at_plus_one", "PATCH", "/journeys/%s" % JOURNEY, status, raw,
         {"sent_end_at": new_end.isoformat()})
    if status >= 300:
        dump()
        print("REFUSED AT DOOR 1 - refusal recorded, stopping")
        return 3

    second_day = (start + timedelta(days=1)).date().isoformat()
    places = json.loads(call("GET", "/places?city_code=%s" % journey["city_code"])[1].decode("utf-8"))
    used = {
        act.get("place_id")
        for act in (json.loads(call("GET", "/journeys/%s/experience" % JOURNEY)[1].decode("utf-8"))
                    .get("active_plan") or {}).get("activities") or []
        if act.get("place_id")
    }
    candidate = next((p for p in places if p["id"] not in used), None)
    if candidate is None:
        dump()
        print("ABORT: every place in this city is already on the plan")
        return 4

    status, raw = call("POST", "/journeys/%s/poi-import/add" % JOURNEY,
                       {"place_ids": [candidate["id"]], "day": second_day})
    note("poi_import_add_second_day", "POST", "/journeys/%s/poi-import/add" % JOURNEY, status, raw,
         {"sent_day": second_day, "sent_place_id": candidate["id"]})
    if status >= 300:
        dump()
        print("REFUSED AT DOOR 2 - refusal recorded, stopping")
        return 3

    after = experience_shape()[1]
    print("after %s" % json.dumps(after, ensure_ascii=False))
    dump()
    print("DISTINCT_DAYS=%s DAY_COUNT_SERVER_PROJECTION=%s"
          % (len(after["distinct_activity_days"]), after["day_count"]))
    return 0 if len(after["distinct_activity_days"]) >= 2 else 5


def dump():
    with open(OUT, "w", encoding="utf-8") as handle:
        json.dump({"api_port": API_PORT, "marker_city": MARKER_CITY, "journey": JOURNEY,
                   "steps": steps}, handle, ensure_ascii=False, indent=1)
    print("receipt %s" % OUT)


if __name__ == "__main__":
    sys.exit(main())
