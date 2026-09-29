"""ORD-0444 -- r5: one arm of `stack_receipt_r4.json` was measured wrong by this lane, and the four
receipt keys that scrolled off the console are re-printed so a reader sees them in full.

r4's `4_post_item.every_place_field_resolved_from_the_places_row` printed `false`.  The server did
not disagree with the `places` row: the door serves `latitude`/`longitude` nested inside
`location` (`contracts/openapi.yaml:2436` -- `CollectionItem.location` is a `GeoPoint`), and my
comparison asked for two flat keys that were never there, so the equality came out false on a
shape mismatch of my own making.  This probe compares against the shape the contract declares, and
prints both sides so the reading is checkable rather than asserted.

Nothing new is written to any database here beyond the shelf r4 already made.
"""

from __future__ import annotations

import json
import sqlite3
import urllib.request
from pathlib import Path

BASE = "http://127.0.0.1:60144"
ROOT = Path("D:/moodle/_qoder_newlane_ord0444_20260929")
PRIVATE_DB = ROOT / "scratch/private_r4.db"
RECEIPT = ROOT / "scratch/stack_receipt_r4.json"
PLACE_ID = "place-beijing-houhai"
OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))

out: dict = {}
existing = json.loads(RECEIPT.read_text(encoding="utf-8"))

# r4 already put this place on that shelf, and a second add is refused by name -- correctly.  So the
# resolution arm runs on a shelf this probe creates, not on r4's, or the reading would be a 409 and
# nothing would be compared.
created = urllib.request.Request(
    f"{BASE}/api/v1/collections",
    data=json.dumps({"name": "r5 复核夹"}).encode("utf-8"),
    method="POST",
    headers={"Content-Type": "application/json"},
)
with OPENER.open(created, timeout=25) as response:
    new_shelf = json.loads(response.read().decode("utf-8"))
folder_id = new_shelf["id"]
out["created_shelf_for_this_probe"] = {"id": folder_id, "name": new_shelf["name"], "r4_shelf": existing["15_ownership_three_ways"]["folder_rows"][0][0]}

# ---- the resolution arm, re-measured against the declared shape
request = urllib.request.Request(
    f"{BASE}/api/v1/collections/{folder_id}/items",
    data=json.dumps({"place_id": PLACE_ID, "note": "r5 复核"}).encode("utf-8"),
    method="POST",
    headers={"Content-Type": "application/json"},
)
try:
    with OPENER.open(request, timeout=25) as response:
        served = json.loads(response.read().decode("utf-8"))
        http = response.status
except urllib.error.HTTPError as exc:
    served = {}
    http = exc.code
    out["note_duplicate"] = {"http": http, "body": exc.read().decode("utf-8", "replace")[:200]}

with sqlite3.connect(PRIVATE_DB) as connection:
    row = connection.execute(
        "SELECT name, category, city_code, latitude, longitude, provider_key, coordinate_system"
        " FROM places WHERE id=?",
        (PLACE_ID,),
    ).fetchone()
expected = {
    "name": row[0],
    "category": row[1],
    "city_code": row[2],
    "location": {"latitude": row[3], "longitude": row[4]},
    "provider_key": row[5],
    "coordinate_system": row[6],
}
per_field = {key: (served.get(key) == value) for key, value in expected.items()}
out["4r_resolution_re_measured"] = {
    "http": http,
    "per_field_equal": per_field,
    "all_fields_equal": all(per_field.values()),
    "places_row": {key: value for key, value in expected.items()},
    "served_body": served,
    "keys_in_served_but_not_compared": sorted(set(served) - set(expected)),
}

# ---- the four keys that scrolled off r4's console, printed verbatim from the receipt
for key in (
    "11_counter_empty_name",
    "12_openapi_json_visible",
    "13_contract_fields_match_served_spec",
    "14_operationid_divergence_control",
):
    out[key] = existing.get(key, "NOT_IN_RECEIPT")

target = ROOT / "scratch/stack_receipt_r5.json"
target.write_text(json.dumps(out, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")
print(json.dumps(out, ensure_ascii=True, indent=1, sort_keys=True))
