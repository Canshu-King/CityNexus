"""ORD-0399 acceptance readings on real product data, in a private copy.

The order asks for "同一枚副本库、同一条命令跑前后各一遍" for three readings: the list length
returns to its original value, the `journeys` row count does not move, and the `activities` row
count does not move.  A temporary store cannot give a non-zero activities count, because no door
in this build creates the first activity row without the seeded catalog.  So the readings are taken
on a copy made with SQLite's backup API from a read-only URI of the preview store - the same
method the commander used at 16:34 - and every write below goes to the copy.

Source: `file:<_preview.db>?mode=ro` (open_uri, immutable-ish, no ALTER, no lock upgrade).
Target: `D:/moodle/_qoder_lane_ord0399_restore/_scratch_probe/preview_copy.db`.
Nothing here calls `POST /api/v1/demo/reset`, and nothing here opens the running backend's store.
"""

from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path

SOURCE = Path("D:/moodle/_qoder_preview_20260920/_preview.db")
# The copy holds real user rows, so it goes under `_scratch_probe/`, which `.gitignore:45` (`_*/`)
# keeps out of the tree - never next to this file, where a `git add review/` could ship it.
COPY = Path(__file__).resolve().parents[2] / "_scratch_probe" / "preview_copy.db"
TABLES = ("journeys", "plan_versions", "activities", "commitments", "events", "travelers")


def counts(connection: sqlite3.Connection) -> dict[str, int]:
    return {
        table: int(connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
        for table in TABLES
    }


def main() -> int:
    if not SOURCE.exists():
        print(f"[source] MISSING {SOURCE}")
        return 2
    COPY.parent.mkdir(parents=True, exist_ok=True)

    source_ro_uri = f"file:{SOURCE.as_posix()}?mode=ro"
    src = sqlite3.connect(source_ro_uri, uri=True)
    before_source = counts(src)
    src_columns = [
        str(row[1]) for row in src.execute("PRAGMA table_info(journeys)").fetchall()
    ]
    print(f"[source] path={SOURCE} opened=mode=ro")
    print(f"[source] counts_before_copy={json.dumps(before_source, sort_keys=True)}")
    print(f"[source] journeys_has_deleted_at_column={'deleted_at' in src_columns}")

    if COPY.exists():
        COPY.unlink()
    dst = sqlite3.connect(COPY)
    src.backup(dst)
    dst.close()
    src.close()
    print(f"[copy] path={COPY}")

    os.environ["CITYNEXUS_DATABASE_URL"] = f"sqlite:///{COPY.as_posix()}"
    os.environ["CITYNEXUS_PROVIDER_NETWORK_MODE"] = "direct"
    # Imported after the env vars: `app.main` reads the store URL and runs ensure_schema() at
    # import time, which is the boot path being measured.
    from app.main import app
    from fastapi.testclient import TestClient

    client = TestClient(app, raise_server_exceptions=False)

    with sqlite3.connect(COPY) as connection:
        columns = [str(r[1]) for r in connection.execute("PRAGMA table_info(journeys)")]
        journey_id = str(
            connection.execute("SELECT id FROM journeys ORDER BY created_at LIMIT 1").fetchone()[0]
        )
    print(f"[boot] journeys_columns_after_ensure_schema={json.dumps(columns)}")
    print(f"[boot] deleted_at_added_by_boot={'deleted_at' in columns} journey_under_test={journey_id}")

    def reading(tag: str) -> dict[str, object]:
        with sqlite3.connect(COPY) as connection:
            stored = counts(connection)
            binned = int(
                connection.execute(
                    "SELECT COUNT(*) FROM journeys WHERE deleted_at IS NOT NULL"
                ).fetchone()[0]
            )
            rowid = connection.execute(
                "SELECT rowid FROM journeys WHERE id = ?", (journey_id,)
            ).fetchone()[0]
        listed = client.get("/api/v1/journeys")
        return {
            "tag": tag,
            "list_http_status": listed.status_code,
            "list_len": len(listed.json()) if listed.status_code == 200 else -1,
            "journeys_rows": stored["journeys"],
            "activities_rows": stored["activities"],
            "plan_versions_rows": stored["plan_versions"],
            "commitments_rows": stored["commitments"],
            "events_rows": stored["events"],
            "binned_rows": binned,
            "journey_under_test_rowid": int(rowid),
            "in_list": journey_id in [str(item["id"]) for item in listed.json()],
        }

    a = reading("before")
    delete = client.delete(f"/api/v1/journeys/{journey_id}")
    b = reading("binned")
    undelete = client.post(f"/api/v1/journeys/{journey_id}/undelete")
    c = reading("restored")
    print(f"[http] DELETE_status={delete.status_code} UNDELETE_status={undelete.status_code}")
    for row in (a, b, c):
        print("[reading] " + json.dumps(row, sort_keys=True))

    # ORD-0395's class, read on this door instead of only asserted about somebody else's.
    generated = sorted(
        app.openapi()["paths"]["/api/v1/journeys/{journey_id}/undelete"]["post"]["responses"]
    )
    print(f"[spec-gap] app_generated_spec_codes={json.dumps(generated)} hand_contract_codes="
          '["200", "404", "409"]  (grep -c "responses=" backend/app/main.py = 0, so the live spec '
          "cannot name the refusals until that mechanism exists)")

    with sqlite3.connect(f"file:{SOURCE.as_posix()}?mode=ro", uri=True) as after_src:
        after = counts(after_src)
    print(f"[source] counts_after_the_whole_run={json.dumps(after, sort_keys=True)}")
    print(f"[source] untouched={after == before_source}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
