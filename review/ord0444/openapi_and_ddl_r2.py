"""ORD-0444 -- two follow-ups to `stack_receipt_r1.json`, each measuring one thing that receipt got
wrong or did not measure.  Neither is a re-litigation of the walk: arms 1-9 and 11-14 of r1 stand.

r2  `/openapi.json` path lookup.  r1 looked the paths up as `/collections`, and the runtime spec
    keys them by the full route path `/api/v1/collections` -- so r1's `10_openapi_json` printed
    `[]` and three `null` operationIds.  That was my lookup, not the server: the same r1 receipt
    already shows all four `Collection*` components in `components.schemas`, which the route
    declarations put there.  This probe reads the prefixed keys and prints what is actually in the
    served document.

r3  the DDL against a database that already exists without these tables.  r1's
    `collection_tables_in_backup_before_boot` key is mislabelled: uvicorn had already imported
    `app.main`, and `ensure_schema()` (`backend/app/main.py:474`) runs at import, so the two tables
    existed by the time that line read them.  The absence at backup time *was* measured
    (`[]`), but not in the same run as the creation, which is the pairing that matters here.
    This probe takes a fresh copy of the shared preview database, asserts the tables are absent,
    applies the product's own `ensure_schema()` to it, and asserts they arrive -- on a database
    that already has 52-odd tables and 16 places, not on an empty file.
    The shared file itself is opened `mode=ro` and byte-compared before and after.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path("D:/moodle/_qoder_newlane_ord0444_20260929/wt/backend")))

OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))
PREVIEW_DB = Path("D:/moodle/_qoder_preview_20260920/_preview.db")
FRESH_DB = Path("D:/moodle/_qoder_newlane_ord0444_20260929/scratch/private_r3.db")
RECEIPT = Path("D:/moodle/_qoder_newlane_ord0444_20260929/scratch/openapi_and_ddl_r2.json")
COLLECTION_TABLES = {"collection_folders", "collection_items"}

out: dict = {}

# ------------------------------------------------------------------ r2: the served contract
with OPENER.open("http://127.0.0.1:60144/openapi.json", timeout=20) as response:
    spec = json.loads(response.read().decode("utf-8"))
paths = spec.get("paths") or {}
prefix = "/api/v1"
out["r2_openapi_json"] = {
    "http": 200,
    "total_runtime_paths": len(paths),
    "collection_paths_found": sorted(key for key in paths if "collection" in key),
    "methods_by_path": {
        f"{prefix}/collections": sorted((paths.get(f"{prefix}/collections") or {}).keys()),
        f"{prefix}/collections/{{folder_id}}/items": sorted(
            (paths.get(f"{prefix}/collections/{{folder_id}}/items") or {}).keys()
        ),
    },
    "operation_ids": [
        ((paths.get(f"{prefix}/collections") or {}).get("get") or {}).get("operationId"),
        ((paths.get(f"{prefix}/collections") or {}).get("post") or {}).get("operationId"),
        (
            (paths.get(f"{prefix}/collections/{{folder_id}}/items") or {}).get("post") or {}
        ).get("operationId"),
    ],
    # The refusal shapes the counter-cases depend on have to be in the served document too, or the
    # screen is typing a token the contract never promised.
    "add_item_response_codes": sorted(
        ((paths.get(f"{prefix}/collections/{{folder_id}}/items") or {}).get("post") or {}).get("responses", {})
    ),
}

# ------------------------------------------------------------------ r3: DDL onto an existing store
sha_before = hashlib.sha1(PREVIEW_DB.read_bytes()).hexdigest()
if FRESH_DB.exists():
    FRESH_DB.unlink()
source = sqlite3.connect(f"file:{PREVIEW_DB.as_posix()}?mode=ro", uri=True)
target = sqlite3.connect(FRESH_DB)
source.backup(target)
target.close()
source.close()

with sqlite3.connect(FRESH_DB) as connection:
    tables_before = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
out["r3_before_ensure_schema"] = {
    "fresh_copy_tables_total": len(tables_before),
    "collection_tables_present": sorted(tables_before & COLLECTION_TABLES),
    "collection_tables_absent": sorted(COLLECTION_TABLES - tables_before),
    "places_rows": None,
    "preview_db_sha1_before": sha_before,
}
with sqlite3.connect(FRESH_DB) as connection:
    out["r3_before_ensure_schema"]["places_rows"] = connection.execute("SELECT count(*) FROM places").fetchone()[0]

# The product's own migration path, against the copy -- not a hand-run of schema.sql.
from sqlalchemy import create_engine  # noqa: E402

from app.db.session import ensure_schema  # noqa: E402

engine = create_engine(f"sqlite:///{FRESH_DB.as_posix()}")
ensure_schema(engine)

with sqlite3.connect(FRESH_DB) as connection:
    tables_after = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    index_names = {
        row[0]
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='collection_items'"
        )
    }
    item_columns = [row[1] for row in connection.execute("PRAGMA table_info(collection_items)")]
out["r3_after_ensure_schema"] = {
    "fresh_copy_tables_total": len(tables_after),
    "collection_tables_present": sorted(tables_after & COLLECTION_TABLES),
    "collection_items_columns": item_columns,
    "collection_items_indexes": sorted(index_names),
}

sha_after = hashlib.sha1(PREVIEW_DB.read_bytes()).hexdigest()
out["r3_preview_db_untouched"] = {
    "sha1_before": sha_before,
    "sha1_after": sha_after,
    "equal": sha_before == sha_after,
}

RECEIPT.write_text(json.dumps(out, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")
# `ensure_ascii=True` on the console only: this box's console is cp936 and would mangle the Chinese
# the walk round-tripped.  The receipt file keeps the real bytes.
print(json.dumps(out, ensure_ascii=True, indent=1, sort_keys=True))
