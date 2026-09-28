"""ORD-0444 -- the acceptance walk, r4.  Supersedes `stack_receipt_r1.json`; r1's walk arms stand,
and this run exists for four reasons:

- the r1 key `collection_tables_in_backup_before_boot` was mislabelled: uvicorn had already imported
  `app.main`, whose `ensure_schema()` (`backend/app/main.py:474`) creates the tables, so by the time
  r1 read them they existed.  Here the pre-boot absence is read from `private_r4_state.json`, taken
  off the copy before the server was started at all, and the post-boot presence is read separately;
- the r1 `/openapi.json` lookup used `/collections`, and the served document keys routes by their
  full path (`/api/v1/collections`), so r1 printed three `null` operationIds.  That was my lookup,
  not the server;
- the served document listed only 201 and 422 on the add-item door until ORD-0444 attached
  `responses={404, 409}` to it, following ORD-0395's rule (`backend/app/main.py:2114`).  This run
  prints the codes the served document actually carries;
- the operationId divergence between the hand contract and the served spec is measured against two
  doors that shipped before this order, so a reader can see whether it is a new defect or the
  existing state of the two generators.

Nothing here writes `D:/moodle/_qoder_preview_20260920/_preview.db`: it is opened `mode=ro`, copied
with `src.backup()`, and byte-compared before and after.  `POST /api/v1/demo/reset` is never called.
Ports 8000 / 4781 / 4782 / 8693 are never contacted or restarted.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
import subprocess
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import yaml

BASE = "http://127.0.0.1:60144"
ROOT = Path("D:/moodle/_qoder_newlane_ord0444_20260929")
PRIVATE_DB = ROOT / "scratch/private_r4.db"
PREVIEW_DB = Path("D:/moodle/_qoder_preview_20260920/_preview.db")
RECEIPT = ROOT / "scratch/stack_receipt_r4.json"
STATE_BEFORE_BOOT = ROOT / "scratch/private_r4_state.json"
UVICORN_LOG = ROOT / "scratch/uvicorn_60144_r4.log"
TREE = ROOT / "wt"
PLACE_ID = "place-beijing-houhai"

# This box exports HTTP_PROXY/HTTPS_PROXY=127.0.0.1:7892 and nothing listens there, so a
# proxy-aware client reports a refused connection for a port that is answering.  Loopback is read
# with no proxy at all; "unreachable" must never be a verdict about a port nobody tried directly.
OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))

out: dict = {"started_at_utc": datetime.now(timezone.utc).isoformat(), "base": BASE}


def call(method: str, path: str, body: dict | None = None) -> tuple[int, dict, str]:
    data = None if body is None else json.dumps(body).encode("utf-8")
    request = urllib.request.Request(
        f"{BASE}{path}",
        data=data,
        method=method,
        headers={"Content-Type": "application/json"} if data else {},
    )
    try:
        with OPENER.open(request, timeout=25) as response:
            text = response.read().decode("utf-8")
            return response.status, _shape(text), text
    except urllib.error.HTTPError as exc:
        return exc.code, _shape(exc.read().decode("utf-8", "replace")), ""


def _shape(text: str) -> dict:
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {"_array": parsed}


def error_part(body: dict, key: str) -> object:
    error = body.get("error")
    return error.get(key) if isinstance(error, dict) else None


# ------------------------------------------------------ the store: absent before boot, present after
out["0_pre_boot_state_measured_before_the_server_ran"] = json.loads(
    STATE_BEFORE_BOOT.read_text(encoding="utf-8")
)

with sqlite3.connect(PRIVATE_DB) as connection:
    tables_now = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    item_columns = [row[1] for row in connection.execute("PRAGMA table_info(collection_items)")]
    folder_columns = [row[1] for row in connection.execute("PRAGMA table_info(collection_folders)")]
    indexes = sorted(
        row[0]
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='collection_items'"
        )
    )
out["1_post_boot_state"] = {
    "collection_tables_present": sorted(tables_now & {"collection_folders", "collection_items"}),
    "total_tables": len(tables_now),
    "collection_folder_columns": folder_columns,
    "collection_item_columns": item_columns,
    "collection_item_indexes": indexes,
}

# ------------------------------------------------------ the walk
status, _, empty_text = call("GET", "/api/v1/collections")
out["2_get_before_any_write"] = {"http": status, "bytes": len(empty_text), "is_literal_empty_array": empty_text.strip() == "[]"}

status, shelf, _ = call("POST", "/api/v1/collections", {"name": "默认收藏夹"})
folder_id = shelf.get("id")
out["3_post_collection"] = {
    "http": status,
    "id_is_uuid_shape": isinstance(folder_id, str) and len(folder_id) == 36,
    "name": shelf.get("name"),
    "name_round_trips_cjk": shelf.get("name") == "默认收藏夹",
    "item_count": shelf.get("item_count"),
    "items_len": len(shelf.get("items", [])),
    "created_equals_updated": shelf.get("created_at") == shelf.get("updated_at"),
}
assert isinstance(folder_id, str) and folder_id, "no shelf id came back -- the walk cannot continue"

status, added, _ = call(
    "POST", f"/api/v1/collections/{folder_id}/items", {"place_id": PLACE_ID, "note": "傍晚去，日落最好"}
)
with sqlite3.connect(PRIVATE_DB) as connection:
    row = connection.execute(
        "SELECT name, category, city_code, latitude, longitude, provider_key, coordinate_system FROM places WHERE id=?",
        (PLACE_ID,),
    ).fetchone()
place_columns = dict(
    zip(
        ("name", "category", "city_code", "latitude", "longitude", "provider_key", "coordinate_system"),
        row or (),
    )
)
resolved = all(added.get(key) == value for key, value in place_columns.items())
out["4_post_item"] = {
    "http": status,
    "id": added.get("id"),
    "place_id": added.get("place_id"),
    "note": added.get("note"),
    "every_place_field_resolved_from_the_places_row": resolved,
    "place_fields_compared": sorted(place_columns),
    "served_body_fields": sorted(k for k in added if k not in {"id", "folder_id", "note", "added_at"}),
    "no_address_key_served": "address" not in added,
}

status, listed, _ = call("GET", "/api/v1/collections")
shelves = listed.get("_array") or []
mine = next((s for s in shelves if s.get("id") == folder_id), None)
rows = (mine or {}).get("items") or []
out["5_get_after_write_server_side_readback"] = {
    "http": status,
    "shelf_count": len(shelves),
    "my_shelf_present": mine is not None,
    "item_count": (mine or {}).get("item_count"),
    "items_len": len(rows),
    "count_equals_array_length": (mine or {}).get("item_count") == len(rows),
    "row_place_name": rows[0].get("name") if rows else None,
    "row_note": rows[0].get("note") if rows else None,
}

# ------------------------------------------------------ counter-cases
missing = "00000000-0000-4000-8000-000000000444"
status, body, _ = call("POST", f"/api/v1/collections/{missing}/items", {"place_id": PLACE_ID})
out["6_counter_unknown_shelf"] = {
    "http": status,
    "reason_code": error_part(body, "reason_code"),
    "message_key": error_part(body, "message_key"),
    "receipt_field_present": bool(error_part(body, "error_receipt_id")),
    "is_500": status == 500,
}

status, body, _ = call("POST", "/api/v1/collections/zzz-not-a-shelf/items", {"place_id": PLACE_ID})
out["7_counter_non_uuid_shelf_id"] = {
    "http": status,
    "reason_code": error_part(body, "reason_code"),
    "message_key": error_part(body, "message_key"),
    "is_500": status == 500,
}

status, body, _ = call("POST", f"/api/v1/collections/{folder_id}/items", {"place_id": "place-not-here"})
out["8_counter_unknown_place"] = {
    "http": status,
    "reason_code": error_part(body, "reason_code"),
    "details": error_part(body, "details"),
    "is_500": status == 500,
}

status, body, _ = call("POST", f"/api/v1/collections/{folder_id}/items", {"place_id": PLACE_ID})
details = error_part(body, "details") or {}
out["9_counter_duplicate"] = {
    "http": status,
    "reason_code": error_part(body, "reason_code"),
    "existing_item_id_names_the_winning_row": details.get("existing_item_id") == added.get("id"),
    "existing_added_at_matches": details.get("existing_added_at") == added.get("added_at"),
    "is_500": status == 500,
}

status, listed, _ = call("GET", "/api/v1/collections")
mine = next((s for s in (listed.get("_array") or []) if s.get("id") == folder_id), None)
out["10_shelf_after_three_refusals"] = {
    "http": status,
    "item_count": (mine or {}).get("item_count"),
    "items_len": len((mine or {}).get("items") or []),
}

status, body, _ = call("POST", "/api/v1/collections", {"name": ""})
out["11_counter_empty_name"] = {
    "http": status,
    "code": error_part(body, "code"),
    "message_key": error_part(body, "message_key"),
    "is_500": status == 500,
}

# ------------------------------------------------------ the served contract
status, spec, spec_text = call("GET", "/openapi.json")
paths = spec.get("paths") or {}
P = "/api/v1"
add_door = (paths.get(f"{P}/collections/{{folder_id}}/items") or {}).get("post") or {}
out["12_openapi_json_visible"] = {
    "http": status,
    "bytes": len(spec_text),
    "collection_paths_found": sorted(key for key in paths if "collection" in key),
    "methods": {
        f"{P}/collections": sorted((paths.get(f"{P}/collections") or {}).keys()),
        f"{P}/collections/{{folder_id}}/items": sorted(
            (paths.get(f"{P}/collections/{{folder_id}}/items") or {}).keys()
        ),
    },
    "add_door_response_codes_served": sorted((add_door.get("responses") or {}).keys()),
    "add_door_response_codes_in_hand_contract": sorted(
        yaml.safe_load((TREE / "contracts/openapi.yaml").read_text(encoding="utf-8"))["paths"][
            "/collections/{folder_id}/items"
        ]["post"]["responses"]
    ),
    "collection_components_served": sorted(
        name for name in (spec.get("components") or {}).get("schemas", {}) if name.startswith("Collection")
    ),
}

# Hand contract vs served spec: field names of the two read shapes.
contract = yaml.safe_load((TREE / "contracts/openapi.yaml").read_text(encoding="utf-8"))
schemas_served = (spec.get("components") or {}).get("schemas") or {}
pairs = {}
for name in ("CollectionItem", "CollectionFolder", "CollectionItemCreate", "CollectionFolderCreate"):
    authored = sorted(((contract["components"]["schemas"].get(name) or {}).get("properties") or {}))
    served = sorted(((schemas_served.get(name) or {}).get("properties") or {}))
    pairs[name] = {"authored_yaml": authored, "served": served, "equal": authored == served}
out["13_contract_fields_match_served_spec"] = pairs

# operationId divergence, measured against doors that shipped before this order.
def opid(authored_path: str, method: str, served_path: str) -> dict:
    authored = ((contract["paths"].get(authored_path) or {}).get(method) or {}).get("operationId")
    served = ((paths.get(served_path) or {}).get(method) or {}).get("operationId")
    return {"authored_yaml": authored, "served": served, "equal": authored == served}


out["14_operationid_divergence_control"] = {
    "pre_existing_ORD0402_recycle_bin": opid("/recycle-bin/journeys", "get", f"{P}/recycle-bin/journeys"),
    "pre_existing_journeys_list": opid("/journeys", "get", f"{P}/journeys"),
    "mine_listCollections": opid("/collections", "get", f"{P}/collections"),
    "mine_createCollection": opid("/collections", "post", f"{P}/collections"),
    "mine_addCollectionItem": opid(
        "/collections/{folder_id}/items", "post", f"{P}/collections/{{folder_id}}/items"
    ),
}

# ------------------------------------------------------ ownership, three ways, plus the untouched source
with sqlite3.connect(PRIVATE_DB) as connection:
    folder_rows = connection.execute("SELECT id, name FROM collection_folders").fetchall()
    item_rows = connection.execute("SELECT id, folder_id, place_id FROM collection_items").fetchall()
probe = subprocess.run(["netstat", "-ano"], capture_output=True, text=True, timeout=60)
pids = sorted(
    {line.split()[-1] for line in probe.stdout.splitlines() if ":60144" in line and "LISTENING" in line.upper()}
)
log = UVICORN_LOG.read_text(encoding="utf-8", errors="replace")
out["15_ownership_three_ways"] = {
    "a_marker_row_in_my_sqlite_is_the_id_the_api_answered": any(r[0] == folder_id for r in folder_rows),
    "b_listener_pid_on_60144": pids,
    "c_my_log_holds_the_collection_requests": log.count("/api/v1/collections"),
    "c_log_500_lines": [line for line in log.splitlines() if '" 500 ' in line],
    "folder_rows": [list(r) for r in folder_rows],
    "item_rows": [list(r) for r in item_rows],
}

sha_after = hashlib.sha1(PREVIEW_DB.read_bytes()).hexdigest()
out["16_shared_preview_untouched"] = {
    "sha1_at_backup_time": json.loads(STATE_BEFORE_BOOT.read_text(encoding="utf-8"))["preview_sha1"],
    "sha1_now": sha_after,
    "equal": json.loads(STATE_BEFORE_BOOT.read_text(encoding="utf-8"))["preview_sha1"] == sha_after,
}

out["finished_at_utc"] = datetime.now(timezone.utc).isoformat()
RECEIPT.write_text(json.dumps(out, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")
print(json.dumps(out, ensure_ascii=True, indent=1, sort_keys=True))
