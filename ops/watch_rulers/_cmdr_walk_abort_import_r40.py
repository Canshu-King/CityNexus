# CMDR r40: prepared verification for ORD-0520 (journey abort) and ORD-0524 (POI batch import),
# to be run against whatever stack serves the tip where those orders land.
# usage: python _cmdr_walk_abort_import_r40.py <base-url> [journey_id]
import json
import sys
import urllib.request as U

B = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:4781"
J = sys.argv[2] if len(sys.argv) > 2 else None
OUT = {"base": B, "arms": {}, "facts": {}}


def go(method, path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = U.Request(B + path, data=data, method=method,
                    headers={"Content-Type": "application/json"} if data else {})
    try:
        r = U.urlopen(req, timeout=90)
        code, text = r.status, r.read().decode("utf-8", "replace")
    except U.HTTPError as e:
        code, text = e.code, e.read().decode("utf-8", "replace")
    try:
        return code, json.loads(text)
    except Exception:
        return code, text


def note(label, code, payload, extra=None):
    o = {"http_status": code}
    if isinstance(payload, list):
        o["count"] = len(payload)
    elif isinstance(payload, dict) and "error" in payload:
        e = payload["error"]
        o["code"] = e.get("code")
        o["reason_code"] = e.get("reason_code")
        o["message_head"] = (e.get("message") or "")[:130]
        o["receipt"] = bool(e.get("error_receipt_id"))
    elif isinstance(payload, dict):
        o["keys"] = list(payload.keys())[:9]
    OUT["arms"][label] = o if extra is None else {**o, **extra}
    return payload


if not J:
    s, jl = go("GET", "/api/v1/journeys")
    if isinstance(jl, list) and jl:
        J = jl[0].get("id")
    OUT["facts"]["journeys_list"] = {"http_status": s, "count": len(jl) if isinstance(jl, list) else None}
OUT["facts"]["journey"] = J

if J:
    # --- ORD-0520: the abort door (name may differ; probe the likely shapes and record what answers)
    for label, path, body in [
        ("abort_named_reason", "/api/v1/journeys/%s/abort" % J, {"reason": "CMDR r40 亲测中止"}),
        ("abort_no_reason", "/api/v1/journeys/%s/abort" % J, {}),
    ]:
        note(label, *go("POST", path, body))
    note("journey_after_abort", *go("GET", "/api/v1/journeys/%s" % J))
    note("recycle_bin_after_abort", *go("GET", "/api/v1/recycle-bin/journeys"))
    note("abort_again", *go("POST", "/api/v1/journeys/%s/abort" % J, {"reason": "again"}))
    note("abort_unknown_journey", *go("POST", "/api/v1/journeys/00000000-0000-4000-8000-000000000000/abort",
                                     {"reason": "x"}))

    # --- ORD-0524: the import batch door over HTTP (parse -> add), independent of the screen
    s, parsed = go("POST", "/api/v1/journeys/%s/poi-import/parse" % J,
                   {"text": "Old Town Gate\nRiverside Museum\nCentral Food Hall"})
    note("import_parse", s, parsed)
    ids = []
    if isinstance(parsed, dict):
        OUT["facts"]["parse_counts"] = parsed.get("counts")
        ids = [i.get("place_id") for i in parsed.get("items", []) if i.get("place_id")]
    OUT["facts"]["resolved_place_ids"] = ids
    if ids:
        note("import_add_all", *go("POST", "/api/v1/journeys/%s/poi-import/add" % J,
                                   {"place_ids": ids[:3]}))
        note("import_add_duplicate", *go("POST", "/api/v1/journeys/%s/poi-import/add" % J,
                                         {"place_ids": ids[:1]}))
    note("import_add_empty", *go("POST", "/api/v1/journeys/%s/poi-import/add" % J, {"place_ids": []}))
    note("import_add_unknown_place", *go("POST", "/api/v1/journeys/%s/poi-import/add" % J,
                                         {"place_ids": ["place-does-not-exist-cmdr"]}))

print(json.dumps(OUT, ensure_ascii=False, indent=1))
