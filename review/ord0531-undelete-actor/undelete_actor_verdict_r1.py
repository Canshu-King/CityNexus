"""CMDR 02:45 cell 1 -- the 找回 door as a standalone judgment artifact (lane 6a150e1e).

What is being ruled on, stated as one measurable question: does `POST /api/v1/journeys/{journey_id}/undelete`
ask who is tapping? The neighbouring write door in the same family asks exactly that and refuses with a
name (`ABORT_ACTOR_NOT_OWNER`, 403, `field: actor_traveler_id`); this one has no field to put the claim in.

Four taps against this lane's own store, each one putting the row back into the bin it found it in, so
the world ends where it started:

  CTRL   the owner's own trip                                  -- the legitimate success, so the probe
                                                                 can tell a pass from an always-pass
  CE1    a trip owned by a traveller who has no seat anywhere  -- should be refused; recorded either way
  CE2    a trip whose only other member holds an ADMIN seat, which this very screen says cannot 找回
                                                                 -- should be refused; recorded either way
  CLAIM  the same tap as CE1 with a claimed `actor_traveler_id` in the body -- records whether the door
                                                                 can even receive a claim

Every case also reads the two scoped bin doors around the tap, so the consequence is said in the product's
own words and not only as a column flip: whose bin loses the row, whose bin never had it.
"""
from __future__ import annotations

import json
import sqlite3
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

BASE = "http://127.0.0.1:8021/api/v1"
DB = Path("D:/moodle/_qoder_6a_ord0531_20261001/ord0531_gen2.db")
SEED = json.loads(Path("D:/moodle/_qoder_6a_ord0531_20261001/seed_r1.json").read_text(encoding="utf-8"))
OUT = Path("D:/moodle/_qoder_6a_ord0531_20261001/undelete_actor_verdict_r1.json")
OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))
PEOPLE = SEED["travellers"]
TRIPS = SEED["trips"]


def http(method: str, path: str, body: dict | None = None) -> tuple[int, dict | str]:
    """Report the real status line: a 204, a 403 and a 422 must not be folded into one word."""
    data = None if body is None else json.dumps(body).encode("utf-8")
    request = urllib.request.Request(f"{BASE}{path}", method=method, data=data)
    if data:
        request.add_header("Content-Type", "application/json")
    try:
        with OPENER.open(request, timeout=60) as answer:
            raw = answer.read().decode("utf-8", "replace")
            status = answer.status
    except urllib.error.HTTPError as error:
        raw = error.read().decode("utf-8", "replace")
        status = error.code
    try:
        return status, json.loads(raw)
    except json.JSONDecodeError:
        return status, raw[:220]


def deleted_at(journey_id: str) -> str | None:
    connection = sqlite3.connect(f"file:{DB.as_posix()}?mode=ro", uri=True)
    try:
        row = connection.execute("SELECT deleted_at FROM journeys WHERE id = ?", (journey_id,)).fetchone()
    finally:
        connection.close()
    return row[0] if row else "NO_SUCH_ROW"


def bin_titles(traveller: str) -> list[str]:
    status, body = http("GET", f"/travelers/{traveller}/recycle-bin/journeys")
    if not isinstance(body, list):
        return [f"HTTP_{status}"]
    return sorted(item["title"] for item in body)


def ensure_binned(journey_id: str) -> str | None:
    if deleted_at(journey_id) is None:
        http("DELETE", f"/journeys/{journey_id}")
    return deleted_at(journey_id)


def tap(label: str, journey_id: str, owner: str, watcher: str, body: dict | None = None) -> dict:
    before_column = ensure_binned(journey_id)
    before_owner_bin = bin_titles(PEOPLE[owner])
    before_watcher_bin = bin_titles(PEOPLE[watcher])
    status, answer = http("POST", f"/journeys/{journey_id}/undelete", body)
    after_column = deleted_at(journey_id)
    row = {
        "case": label,
        "journey_id": journey_id,
        "actor_field_on_the_door": "none -- the route takes (journey_id, session) only",
        "before_deleted_at": before_column,
        "http_status": status,
        "after_deleted_at": after_column,
        "row_was_restored_by_this_tap": before_column not in (None, "NO_SUCH_ROW") and after_column is None,
        "owner_bin_before": before_owner_bin,
        "owner_bin_after": bin_titles(PEOPLE[owner]),
        "watcher_bin_before": before_watcher_bin,
        "watcher_bin_after": bin_titles(PEOPLE[watcher]),
        "answer_head": str(answer)[:200],
    }
    http("DELETE", f"/journeys/{journey_id}")  # put it back where the world found it
    row["restored_to_bin_deleted_at"] = deleted_at(journey_id)
    return row


rows = [
    tap("CTRL_owner_taps_their_own_trip", TRIPS["TA"], "A", "B"),
    tap("CE1_trip_of_a_traveller_with_no_seat_anywhere", TRIPS["TD"], "C", "B"),
    tap("CE2_admin_seat_that_this_screen_says_cannot_restore", TRIPS["TC"], "A", "B"),
    tap("CLAIM_a_claimed_actor_sent_anyway", TRIPS["TD"], "C", "B", {"actor_traveler_id": PEOPLE["B"]}),
]

receipt = {
    "measured_at": datetime.now(timezone.utc).isoformat(),
    "door": "POST /api/v1/journeys/{journey_id}/undelete  (main.py:3310)",
    "neighbour_that_does_ask": "POST cancel-abort door, main.py:3485: refuses 403 ABORT_ACTOR_NOT_OWNER "
                               "with field actor_traveler_id when the claimed actor is not the owner",
    "store": DB.as_posix(),
    "world": "this lane's ord0531 seed: A owns TA/TC, B owns TB and holds an ADMIN seat on TC, "
             "C owns TD and nobody else has any relationship to TD",
    "rows": rows,
    "screen_words_this_door_contradicts": "B's bin renders TC read-only with 「你在这条行程上有席位，"
                                          "但你那个角色不能把它找回来，所以这里只读。」",
}
OUT.write_text(json.dumps(receipt, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
for row in rows:
    print(f"{row['case']}: http={row['http_status']} restored={row['row_was_restored_by_this_tap']} "
          f"owner_bin {len(row['owner_bin_before'])} -> {len(row['owner_bin_after'])}")
print(f"receipt: {OUT}")
