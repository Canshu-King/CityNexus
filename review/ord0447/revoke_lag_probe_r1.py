"""ORD-0447: is a revocation visible to the very next read, or only to a later one?

The browser arms showed the sentence staying open after `revoke` answered 200, and showing the
revocation after a page navigation.  This asks the doors over one live HTTP connection set, reading
the list door twice in a row and the token door once, so the lag gets a number instead of a theory.
"""
import json
import urllib.request

BASE = "http://127.0.0.1:8111/api/v1"


def call(method, path, body=None):
    data = None if body is None else json.dumps(body).encode("utf-8")
    request = urllib.request.Request(
        BASE + path, data=data, method=method, headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(request) as response:
            return response.status, json.loads(response.read().decode("utf-8") or "null")
    except urllib.error.HTTPError as error:
        raw = error.read().decode("utf-8", errors="replace")
        try:
            return error.code, json.loads(raw or "{}")
        except ValueError:
            return error.code, {"raw": raw[:180]}


status, traveler = call("POST", "/travelers", {
    "display_name": "ORD-0447 lag probe", "locale": "en-GB", "timezone": "Asia/Shanghai",
})
status, journey = call("POST", "/journeys", {
    "traveler_id": traveler["id"], "title": "Lag probe trip", "city_code": "CN-TIANJIN",
    "timezone": "Asia/Shanghai",
    "start_at": "2026-10-09T18:00:00+08:00",
    "end_at": "2026-10-11T15:00:00+08:00",
    "budget": {"amount_minor": 120000, "currency": "CNY"},
})
if "id" not in journey:
    print("journey_create_failed=%s %s" % (status, json.dumps(journey, ensure_ascii=False)[:200]))
    raise SystemExit(1)
jid = journey["id"]
print("journey_http=%s" % status)

status, grant = call("POST", "/journeys/%s/share-grants" % jid,
                     {"visibility": "LINK_READ", "created_by": "lag-probe"})
token, gid = grant["token"], grant["id"]
print("create_http=%s revoked_at=%s" % (status, grant["revoked_at"]))

status, rows = call("GET", "/journeys/%s/share-grants" % jid)
print("list_before_revoke_http=%s standing=%s" % (status, [r["revoked_at"] for r in rows]))

status, answer = call("POST", "/journeys/%s/share-grants/%s/revoke" % (jid, gid))
print("revoke_http=%s already_revoked=%s revoked_at_in_answer=%s"
      % (status, answer.get("already_revoked"), answer.get("revoked_at")))

for attempt in (1, 2, 3):
    status, rows = call("GET", "/journeys/%s/share-grants" % jid)
    print("list_after_revoke_attempt_%d_http=%s revoked_at=%s"
          % (attempt, status, [r["revoked_at"] for r in rows]))

try:
    status, rows = call("GET", "/shared/journeys/%s" % token)
    print("token_read_after_revoke_http=%s" % status)
except urllib.error.HTTPError as error:
    payload = json.loads(error.read().decode("utf-8") or "{}")
    print("token_read_after_revoke_http=%s reason_code=%s"
          % (error.code, (payload.get("error") or {}).get("reason_code")))
