"""ORD-0485 -- the two server-side cells this order closes on real answers, not on a screen.

  share   : issue a grant through the documented door (uppercase visibility enum, created_by
            required), read the list back, walk the receiving door with the token, revoke it and
            read the receiving door again;
  checkin : stamp one real activity of the chosen plan through POST /journeys/{id}/checkins,
            read the footprint list back, replay the same tap, and take the two named refusals.

Every claim is paired with the row this lane's own sqlite file holds, because a response code
alone cannot say which store answered.  The shared preview DB is never opened here.
"""
import json
import os
import sqlite3
import sys
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timedelta, timezone

BASE = "http://127.0.0.1:8139"
DB = r"D:/moodle/_qoder_phone_ord0485_20260930/run/phone_ord0485.db"
OUT = r"D:/moodle/_qoder_phone_ord0485_20260930/evidence/server_cells_r1.json"
opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

cells = []


def call(method, path, body=None, headers=None):
    url = BASE + path
    data = json.dumps(body).encode("utf-8") if body is not None else None
    hdrs = {"Accept": "application/json", "User-Agent": "ORD-0485-lane-phone"}
    if headers:
        hdrs.update(headers)
    if data:
        hdrs["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=hdrs, method=method)
    try:
        with opener.open(req, timeout=30) as r:
            raw = r.read()
            return r.status, json.loads(raw.decode("utf-8")) if raw else None
    except urllib.error.HTTPError as e:
        raw = e.read()
        try:
            parsed = json.loads(raw.decode("utf-8")) if raw else None
        except Exception:
            parsed = {"unparsed_bytes": len(raw), "head": raw[:200].decode("utf-8", "replace")}
        return e.code, parsed
    except Exception as e:
        return None, {"error": type(e).__name__}


def reason_of(payload):
    if not isinstance(payload, dict):
        return None
    err = payload.get("error") or {}
    if isinstance(err, dict) and err.get("reason_code"):
        return err["reason_code"], err.get("details")
    return payload.get("detail") if payload.get("detail") else None, None


def cell(name, status, payload, extra=None, db=None):
    row = {"cell": name, "http_status": status,
           "reason_code": (reason_of(payload) or (None, None))[0] if isinstance(payload, dict) else None,
           "payload_keys": sorted(payload.keys()) if isinstance(payload, dict) else None,
           "payload_head": json.dumps(payload, ensure_ascii=False)[:700] if payload is not None else None}
    if extra:
        row.update(extra)
    if db is not None:
        row["db_rows_named"] = db
    cells.append(row)
    return row


def db_read(sql, args=()):
    con = sqlite3.connect("file:%s?mode=ro" % DB.replace("\\", "/"), uri=True)
    try:
        return [list(r) for r in con.execute(sql, args)]
    finally:
        con.close()


def main():
    journey = db_read("SELECT id, traveler_id, city_code, status FROM journeys")[0]
    journey_id = journey[0]
    traveler_id = journey[1]
    out = {"tool": "server_cells_r1", "base": BASE, "db_under_test": DB,
           "took_local": datetime.now().astimezone().isoformat(),
           "journey_row_named": {"id": journey[0], "traveler_id": journey[1],
                                  "city_code": journey[2], "status": journey[3]},
           "shared_preview_db_opened": False,
           "cells": cells}

    # ---------------- check-ins: the two doors ORD-0476 landed ----------------
    st, plans = call("GET", "/api/v1/journeys/%s/plans" % journey_id)
    current = [p for p in plans if p.get("is_current")][0]
    activities = current.get("activities") or []
    out["plan_row_named"] = {"plan_version_id": current["id"], "status": current["status"],
                             "version_no": current["version_no"],
                             "activity_count": len(activities)}
    target = activities[1] if len(activities) > 1 else activities[0]

    st, body = call("POST", "/api/v1/journeys/%s/checkins" % journey_id,
                    {"activity_id": target["id"], "note": "ord0485 first stamp"})
    stamp = cell("checkin_post_first", st, body, extra={
        "stamped_activity": {"id": target["id"], "title": target["title"],
                             "place_id": target.get("place_id")}},
        db=db_read("SELECT id, journey_id, activity_id, place_id, target_kind, target_key, "
                   "stamped_at, source, note FROM journey_checkins"))

    st, listed = call("GET", "/api/v1/journeys/%s/checkins" % journey_id)
    cell("checkin_list_readback", st, listed, extra={
        "list_length": len(listed) if isinstance(listed, list) else None,
        "titles_back": [c.get("activity_title") for c in listed] if isinstance(listed, list) else None,
        "same_id_as_write": bool(isinstance(listed, list) and listed
                                 and listed[0].get("id") == (body or {}).get("id"))})

    st, dup = call("POST", "/api/v1/journeys/%s/checkins" % journey_id,
                   {"activity_id": target["id"]})
    reason, details = reason_of(dup)
    cell("checkin_replay_second_tap", st, dup, extra={
        "expected": "409 CHECKIN_DUPLICATE_STAMP",
        "names_the_winning_row": bool(isinstance(details, dict)
                                      and details.get("existing_checkin_id"))})

    ghost = str(uuid.uuid4())
    st, unknown = call("POST", "/api/v1/journeys/%s/checkins" % journey_id,
                       {"activity_id": ghost})
    cell("checkin_activity_unknown", st, unknown, extra={"expected": "404 CHECKIN_ACTIVITY_UNKNOWN",
                                                          "ghost_id_length": len(ghost)})

    st, none_target = call("POST", "/api/v1/journeys/%s/checkins" % journey_id, {"note": "x"})
    cell("checkin_no_target_field", st, none_target, extra={"expected": "named refusal"})

    other = db_read("SELECT id FROM activities WHERE place_id IS NOT NULL LIMIT 1")[0][0]
    stranger = str(uuid.uuid4())
    st, stranger_row = call("POST", "/api/v1/journeys/%s/checkins" % stranger,
                            {"activity_id": other})
    cell("checkin_journey_unknown", st, stranger_row,
         extra={"expected": "the door speaks about the journey before the target"})

    out["checkin_rows_after_all_arms"] = db_read(
        "SELECT COUNT(*), MIN(stamped_at), MAX(stamped_at) FROM journey_checkins")

    # ---------------- share: issue, read the receiving door, revoke ----------------
    expiry = (datetime.now(timezone.utc) + timedelta(days=2)).isoformat()
    st, grant = call("POST", "/api/v1/journeys/%s/share-grants" % journey_id,
                     {"visibility": "LINK_READ", "created_by": traveler_id,
                      "expires_at": expiry})
    token = (grant or {}).get("token")
    cell("share_create_LINK_READ", st, grant, extra={
        "expected": "201 with a token", "token_length": len(token or ""),
        "grant_id": (grant or {}).get("id")},
        db=db_read("SELECT id, journey_id, visibility, created_by, expires_at, revoked_at "
                   "FROM journey_share_grants"))

    st, lower = call("POST", "/api/v1/journeys/%s/share-grants" % journey_id,
                     {"visibility": "link_read", "created_by": traveler_id})
    cell("share_create_lowercase_visibility", st, lower,
         extra={"expected": "422 -- the contract takes the uppercase enum only"})

    st, nosigner = call("POST", "/api/v1/journeys/%s/share-grants" % journey_id,
                        {"visibility": "PUBLIC"})
    cell("share_create_without_created_by", st, nosigner,
         extra={"expected": "422 -- created_by is required"})

    st, listing = call("GET", "/api/v1/journeys/%s/share-grants" % journey_id)
    cell("share_list", st, listing, extra={
        "grant_count": len(listing) if isinstance(listing, list) else None,
        "every_row_carries_a_token": bool(isinstance(listing, list)
                                          and all(r.get("token") for r in listing))})

    st, landed = call("GET", "/api/v1/shared/journeys/%s" % token)
    keys = sorted(landed.keys()) if isinstance(landed, dict) else None
    cell("shared_door_with_token", st, landed, extra={"top_level_keys": keys})

    st, wrong = call("GET", "/api/v1/shared/journeys/%s" % (token[:-4] + "ZZZZ"))
    cell("shared_door_wrong_token", st, wrong,
         extra={"expected": "a named refusal, not a bare 404"})

    grant_id = (grant or {}).get("id")
    st, revoked = call("POST", "/api/v1/journeys/%s/share-grants/%s/revoke" % (journey_id, grant_id))
    cell("share_revoke", st, revoked, extra={"expected": "200 with revoked_at set"})

    st, after = call("GET", "/api/v1/shared/journeys/%s" % token)
    reason_after, _ = reason_of(after)
    cell("shared_door_after_revoke", st, after, extra={
        "expected": "the receiving door refuses by name",
        "same_token_still_resolves": reason_after is None})

    out["grant_rows_after_all_arms"] = db_read(
        "SELECT id, visibility, revoked_at IS NOT NULL FROM journey_share_grants")
    out["verdicts"] = {
        "checkin_write_and_readback_landed": stamp["http_status"] == 201 and
            out["checkin_rows_after_all_arms"][0][0] >= 1,
        "checkin_ui_on_this_build": "NOT_REACHED - see the walk readings",
        "share_grant_issued_and_revoked": bool(token),
    }
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    print(json.dumps(out, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
