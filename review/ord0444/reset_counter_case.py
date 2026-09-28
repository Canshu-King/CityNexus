"""ORD-0444 -- the `demo/reset` counter-case: does the new container break the fixture door that
~140 test modules and the shared demo stage depend on?

`services.reset_all` (`backend/app/services.py:113`) deletes 52 named tables in a fixed order,
children first, precisely because `PRAGMA foreign_keys=ON` is set on every connection
(`backend/app/db/session.py:64`).  `collection_items.place_id` references `places(id)` with **no**
`ON DELETE` clause, so a shelf that holds a place is a child row of `places`.  This probe does not
reason about whether that breaks the door -- it drives the door and prints the answer.

Token handling: the reset route refuses without `X-Demo-Reset-Token` matching
`CITYNEXUS_DEMO_RESET_TOKEN`.  The value is read from `scratch/demo_reset_token.txt` and used in
memory; only its path, its length and the header/field names are written to the receipt.

Usage: `python reset_counter_case_r1.py <receipt-name>`.
"""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

BASE = "http://127.0.0.1:60148"
ROOT = Path("D:/moodle/_qoder_newlane_ord0444_20260929")
TOKEN_FILE = ROOT / "scratch/demo_reset_token.txt"
LOG = ROOT / "scratch/uvicorn_60148.log"
PLACE_ID = "place-beijing-houhai"
RECEIPT = ROOT / f"scratch/{sys.argv[1] if len(sys.argv) > 1 else 'reset_counter_r1.json'}"
OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))
token = TOKEN_FILE.read_text(encoding="utf-8").strip()

out: dict = {"base": BASE, "started_at_utc": datetime.now(timezone.utc).isoformat()}


def call(method: str, path: str, body: dict | None = None, headers: dict | None = None):
    data = None if body is None else json.dumps(body).encode("utf-8")
    merged = {"Content-Type": "application/json", **(headers or {})} if data else dict(headers or {})
    request = urllib.request.Request(f"{BASE}{path}", data=data, method=method, headers=merged)
    try:
        with OPENER.open(request, timeout=40) as response:
            text = response.read().decode("utf-8", "replace")
            return response.status, text
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8", "replace")


status, text = call("GET", "/api/v1/health")
out["0_health"] = {"http": status}

status, text = call("POST", "/api/v1/collections", {"name": "重置前的夹"})
shelf = json.loads(text) if status == 201 else {}
folder_id = shelf.get("id")
out["1_create_shelf"] = {"http": status, "id": folder_id}
assert folder_id, text

status, text = call(
    "POST", f"/api/v1/collections/{folder_id}/items", {"place_id": PLACE_ID, "note": "重置前写的"}
)
out["2_add_place"] = {"http": status, "item_id": (json.loads(text) or {}).get("id") if status == 201 else None}
assert status == 201, text

# The row is really there before the door is asked to empty the store.
status, text = call("GET", "/api/v1/collections")
shelves = json.loads(text)
mine = next((s for s in shelves if s.get("id") == folder_id), None)
out["3_shelf_holds_a_place_before_reset"] = {
    "http": status,
    "shelf_present": mine is not None,
    "item_count": (mine or {}).get("item_count"),
}

status, text = call("POST", "/api/v1/demo/reset", headers={"X-Demo-Reset-Token": token})
body = {}
try:
    body = json.loads(text)
except json.JSONDecodeError:
    body = {}
error = body.get("error") if isinstance(body, dict) else None
out["4_demo_reset_with_a_non_empty_shelf"] = {
    "http": status,
    "is_500": status == 500,
    "code": (error or {}).get("code") if isinstance(error, dict) else body.get("status"),
    "message_key": (error or {}).get("message_key") if isinstance(error, dict) else None,
    "reason_code": (error or {}).get("reason_code") if isinstance(error, dict) else None,
    "body_head": text[:220],
    "token_length_not_printed": len(token),
    "token_field": "CITYNEXUS_DEMO_RESET_TOKEN",
    "token_header": "X-Demo-Reset-Token",
}

# What the store looks like to the doors afterwards, whichever way the reset went.
status, text = call("GET", "/api/v1/collections")
out["5_collections_after_the_reset_attempt"] = {"http": status, "body_head": text[:200]}

log = LOG.read_text(encoding="utf-8", errors="replace")
out["6_server_log_attribution"] = {
    "integrity_error_lines": [line for line in log.splitlines() if "IntegrityError" in line],
    "foreign_key_lines": [line for line in log.splitlines() if "FOREIGN KEY" in line.upper()],
    "five_hundred_lines": [line for line in log.splitlines() if '" 500 ' in line],
}

out["finished_at_utc"] = datetime.now(timezone.utc).isoformat()
RECEIPT.write_text(json.dumps(out, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")
print(json.dumps(out, ensure_ascii=True, indent=1, sort_keys=True))
