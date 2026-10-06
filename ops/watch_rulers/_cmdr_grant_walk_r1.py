"""CMDR own-eyeball acceptance for ORD-0434 (share grants) against my private backend.

This is the cell I told the ledger I had not verified.  Every line below is an HTTP response
read from the running service -- not a test name, not a gate summary.  The interesting pairs are:
  live token vs revoked token,
  expired token vs a token that never existed,
  PRIVATE grant vs LINK_READ grant.
"""
import json
import io
import datetime
import urllib.request
import urllib.error

BASE = "http://127.0.0.1:8738"


def call(method, path, body=None, headers=None):
    url = BASE + path
    data = None
    hd = {"Content-Type": "application/json"}
    if headers:
        hd.update(headers)
    if body is not None:
        data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=hd, method=method)
    try:
        r = urllib.request.urlopen(req, timeout=15)
        raw = r.read()
        try:
            parsed = json.loads(raw)
        except Exception:
            parsed = None
        return r.status, len(raw), parsed
    except urllib.error.HTTPError as exc:
        raw = exc.read()
        try:
            parsed = json.loads(raw)
        except Exception:
            parsed = {"_head": raw[:120].decode("utf-8", "replace")}
        return exc.code, len(raw), parsed
    except Exception as exc:
        return "ERR", type(exc).__name__, str(exc)[:120]


out = {}
st, n, journeys = call("GET", "/api/v1/journeys")
rows = journeys if isinstance(journeys, list) else (journeys or {}).get("journeys") or []
out["journeys_http"] = st
jid = rows[0]["id"] if rows else None
out["journey_id"] = jid

past = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(minutes=5)).isoformat()
future = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=1)).isoformat()

st, n, link = call("POST", "/api/v1/journeys/%s/share-grants" % jid,
                   {"visibility": "LINK_READ", "created_by": "cmdr-priv-8738", "expires_at": future})
out["create_link_read"] = (st, n, link)
token = (link or {}).get("token") or (link or {}).get("grant_token") or (link or {}).get("share_token")

st, n, priv = call("POST", "/api/v1/journeys/%s/share-grants" % jid,
                   {"visibility": "PRIVATE", "created_by": "cmdr-priv-8738"})
out["create_private"] = (st, n, priv)

st, n, exp = call("POST", "/api/v1/journeys/%s/share-grants" % jid,
                  {"visibility": "LINK_READ", "created_by": "cmdr-priv-8738", "expires_at": past})
out["create_already_expired"] = (st, n, exp)
exp_token = (exp or {}).get("token") or (exp or {}).get("share_token")

if token:
    out["read_with_live_token"] = call("GET", "/api/v1/shared/journeys/%s" % token)
else:
    out["read_with_live_token"] = "NO_TOKEN_IN_CREATE_RESPONSE"

out["read_with_private_token"] = call("GET", "/api/v1/shared/journeys/%s" % ((priv or {}).get("token") or "none"))
out["read_with_expired_token"] = call("GET", "/api/v1/shared/journeys/%s" % exp_token) if exp_token else "NO_TOKEN"
out["read_with_nonsense_token"] = call("GET", "/api/v1/shared/journeys/not-a-real-token")

st, n, listing = call("GET", "/api/v1/journeys/%s/share-grants" % jid)
out["list_grants"] = (st, n, json.dumps(listing, ensure_ascii=False)[:300])

gid = None
if isinstance(listing, list) and listing:
    gid = listing[0].get("id") or listing[0].get("grant_id")
elif isinstance(listing, dict):
    items = listing.get("grants") or listing.get("items") or []
    if items:
        gid = items[0].get("id") or items[0].get("grant_id")
out["grant_id_found"] = bool(gid)

if gid:
    out["revoke"] = call("POST", "/api/v1/journeys/%s/share-grants/%s/revoke" % (jid, gid))
    out["read_after_revoke"] = call("GET", "/api/v1/shared/journeys/%s" % token)
else:
    out["revoke"] = "NO_GRANT_ID_IN_LIST"

io.open("D:/moodle/_qoder_cmdr_ref_20260921/live_checks/_grant_walk_r1.json", "w", encoding="utf-8").write(
    json.dumps(out, ensure_ascii=False, indent=1))
print("WROTE", len(json.dumps(out)))
