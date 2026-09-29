"""ORD-0465 r2 - re-read the four states and the success screen off the door, on this base.

Written to a file rather than a shell one-liner because the reading is evidence: it is shipped into
`review/ord0465/` and a reviewer has to be able to re-run the same thing, not reconstruct my quoting.
"""
import json
import sys
import urllib.error
import urllib.request

OUT = sys.argv[1]
OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))
BACKEND = "http://127.0.0.1:8731/api/v1/shared/journeys/"
seed = json.load(open("D:/moodle/_qoder_r_ord0465_20260929/run/seed_report.json", encoding="utf-8"))

readings = {}
for name in ("valid", "revoked", "expired", "binned", "no_plan", "private"):
    token = seed["tokens"][name]
    try:
        with OPENER.open(BACKEND + token, timeout=20) as answer:
            body = json.loads(answer.read())
            readings[name] = {
                "http_status": answer.status,
                "plan_state": body["plan_state"],
                "stops": len((body.get("active_plan") or {}).get("stops", [])),
                "grant_scope": body["grant_scope"],
                "shared_plan_present": "shared_plan" in body,
            }
    except urllib.error.HTTPError as error:
        envelope = json.loads(error.read())["error"]
        readings[name] = {
            "http_status": error.code,
            "reason_code": envelope.get("reason_code"),
            "server_receipt": envelope.get("error_receipt_id") or "NOT-EMITTED",
        }

try:
    with OPENER.open(BACKEND + "z" * 32, timeout=20) as answer:
        readings["unknown_token"] = {"http_status": answer.status}
except urllib.error.HTTPError as error:
    envelope = json.loads(error.read())["error"]
    readings["unknown_token"] = {
        "http_status": error.code,
        "reason_code": envelope.get("reason_code"),
        "server_receipt": envelope.get("error_receipt_id") or "NOT-EMITTED",
    }

json.dump(readings, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
for key, value in readings.items():
    print(key, value)
